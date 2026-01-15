import pytest
from datetime import datetime, timezone, timedelta
from tessera_sdk.events.event import event_type, event_source
from app.events.api_key_events import (
    build_api_key_created_event,
    build_api_key_updated_event,
    build_api_key_deleted_event,
    API_KEY_CREATED,
    API_KEY_UPDATED,
    API_KEY_DELETED,
)
from app.models.api_key import ApiKey
from app.utils.security import generate_api_key, hash_secret, parse_api_key


@pytest.fixture
def sample_api_key(db, setup_user):
    """Create a sample API key for testing."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    api_key = ApiKey(
        user_id=setup_user.id,
        key_id=key_id_part,
        secret_hash=hash_secret(secret_part),
        name="Test API Key",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def test_build_api_key_created_event(sample_api_key, setup_user):
    """Test building an API key created event."""
    event = build_api_key_created_event(sample_api_key, setup_user)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(API_KEY_CREATED)
    assert event.source == event_source(f"/api_keys/{sample_api_key.id}")
    assert event.subject == f"/api_key/{sample_api_key.id}"
    assert event.user_id == str(sample_api_key.user_id)

    # Verify event data contains API key and user information
    assert "api_key" in event.event_data
    assert "user" in event.event_data
    api_key_data = event.event_data["api_key"]
    user_data = event.event_data["user"]
    assert api_key_data["name"] == sample_api_key.name
    assert api_key_data["user_id"] == str(sample_api_key.user_id)
    assert api_key_data["expires_at"] is not None
    assert user_data["id"] == str(setup_user.id)
    assert user_data["email"] == setup_user.email

    # Verify labels and tags
    assert "api_key_id" in event.labels
    assert event.labels["api_key_id"] == str(sample_api_key.id)
    assert f"api_key_id:{str(sample_api_key.id)}" in event.tags


def test_build_api_key_updated_event(sample_api_key, setup_user):
    """Test building an API key updated event."""
    # Update the API key
    sample_api_key.name = "Updated API Key"
    sample_api_key.revoked = True

    event = build_api_key_updated_event(sample_api_key, setup_user)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(API_KEY_UPDATED)
    assert event.source == event_source(f"/api_keys/{sample_api_key.id}")
    assert event.subject == f"/api_key/{sample_api_key.id}"
    assert event.user_id == str(setup_user.id)

    # Verify event data contains updated API key and user information
    assert "api_key" in event.event_data
    assert "user" in event.event_data
    api_key_data = event.event_data["api_key"]
    user_data = event.event_data["user"]
    assert api_key_data["name"] == "Updated API Key"
    assert api_key_data["user_id"] == str(sample_api_key.user_id)
    assert user_data["id"] == str(setup_user.id)
    assert user_data["email"] == setup_user.email

    # Verify labels and tags
    assert "api_key_id" in event.labels
    assert event.labels["api_key_id"] == str(sample_api_key.id)
    assert f"api_key_id:{str(sample_api_key.id)}" in event.tags


def test_build_api_key_deleted_event(sample_api_key, setup_user):
    """Test building an API key deleted event."""
    event = build_api_key_deleted_event(sample_api_key, setup_user)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(API_KEY_DELETED)
    assert event.source == event_source(f"/api_keys/{sample_api_key.id}")
    assert event.subject == f"/api_key/{sample_api_key.id}"
    assert event.user_id == str(setup_user.id)

    # Verify event data contains API key and user information
    assert "api_key" in event.event_data
    assert "user" in event.event_data
    api_key_data = event.event_data["api_key"]
    user_data = event.event_data["user"]
    assert api_key_data["name"] == sample_api_key.name
    assert api_key_data["user_id"] == str(sample_api_key.user_id)
    assert user_data["id"] == str(setup_user.id)
    assert user_data["email"] == setup_user.email

    # Verify labels and tags
    assert "api_key_id" in event.labels
    assert event.labels["api_key_id"] == str(sample_api_key.id)
    assert f"api_key_id:{str(sample_api_key.id)}" in event.tags


def test_api_key_created_event_data_completeness(sample_api_key, setup_user):
    """Test that API key created event contains all expected fields."""
    event = build_api_key_created_event(sample_api_key, setup_user)
    api_key_data = event.event_data["api_key"]
    user_data = event.event_data["user"]

    # Verify all expected fields are present
    assert "name" in api_key_data
    assert "user_id" in api_key_data
    assert "expires_at" in api_key_data
    assert api_key_data["name"] == sample_api_key.name
    assert api_key_data["user_id"] == str(sample_api_key.user_id)
    assert "id" in user_data
    assert "email" in user_data
    assert user_data["id"] == str(setup_user.id)


def test_api_key_updated_event_with_different_user_id(
    sample_api_key, setup_another_user
):
    """Test that API key updated event uses the provided user, not the API key's user_id."""
    event = build_api_key_updated_event(sample_api_key, setup_another_user)

    # Verify the user_id in the event matches the provided user, not the API key's user_id
    assert event.user_id == str(setup_another_user.id)
    assert event.user_id != str(sample_api_key.user_id)
    # Verify the user data in event_data matches the provided user
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["id"] == str(setup_another_user.id)
    assert user_data["email"] == setup_another_user.email


def test_api_key_deleted_event_with_different_user_id(
    sample_api_key, setup_another_user
):
    """Test that API key deleted event uses the provided user."""
    event = build_api_key_deleted_event(sample_api_key, setup_another_user)

    # Verify the user_id in the event matches the provided user
    assert event.user_id == str(setup_another_user.id)
    # Verify the user data in event_data matches the provided user
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["id"] == str(setup_another_user.id)
    assert user_data["email"] == setup_another_user.email


def test_api_key_event_json_serializable(sample_api_key, setup_user):
    """Test that event data is JSON serializable."""
    event = build_api_key_created_event(sample_api_key, setup_user)

    # Verify event can be serialized to JSON
    event_json = event.model_dump_json()
    assert event_json is not None
    assert len(event_json) > 0

    # Verify event_data is JSON serializable
    import json

    event_data_json = json.dumps(event.event_data)
    assert event_data_json is not None
    # Verify both api_key and user are in the serialized data
    event_data = json.loads(event_data_json)
    assert "api_key" in event_data
    assert "user" in event_data
