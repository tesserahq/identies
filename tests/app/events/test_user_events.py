from datetime import datetime, timezone
from tessera_sdk.events.event import event_type, event_source
from app.events.user_events import (
    build_user_created_event,
    build_user_updated_event,
    build_user_deleted_event,
    USER_CREATED,
    USER_UPDATED,
    USER_DELETED,
)


def test_build_user_created_event(setup_user):
    """Test building a user created event."""
    event = build_user_created_event(setup_user)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(USER_CREATED)
    assert event.source == event_source()
    assert event.subject == f"/users/{setup_user.id}"
    assert event.user_id == str(setup_user.id)

    # Verify event data contains user information
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["email"] == setup_user.email
    assert user_data["first_name"] == setup_user.first_name
    assert user_data["last_name"] == setup_user.last_name
    assert user_data["username"] == setup_user.username

    # Verify labels and tags
    assert "user_id" in event.labels
    assert event.labels["user_id"] == str(setup_user.id)
    assert f"user_id:{str(setup_user.id)}" in event.tags


def test_build_user_updated_event(setup_user):
    """Test building a user updated event."""
    # Update the user
    setup_user.first_name = "Updated"
    setup_user.last_name = "Name"
    setup_user.theme_preference = "dark"

    event = build_user_updated_event(setup_user, setup_user.id)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(USER_UPDATED)
    assert event.source == event_source()
    assert event.subject == f"/users/{setup_user.id}"
    assert event.user_id == str(setup_user.id)

    # Verify event data contains updated user information
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["first_name"] == "Updated"
    assert user_data["last_name"] == "Name"
    assert user_data["theme_preference"] == "dark"

    # Verify labels and tags
    assert "user_id" in event.labels
    assert event.labels["user_id"] == str(setup_user.id)
    assert f"user_id:{str(setup_user.id)}" in event.tags


def test_build_user_deleted_event(setup_user):
    """Test building a user deleted event."""
    event = build_user_deleted_event(setup_user, setup_user.id)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(USER_DELETED)
    assert event.source == event_source()
    assert event.subject == f"/users/{setup_user.id}"
    assert event.user_id == str(setup_user.id)

    # Verify event data contains user information
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["email"] == setup_user.email
    assert user_data["first_name"] == setup_user.first_name
    assert user_data["last_name"] == setup_user.last_name

    # Verify labels and tags
    assert "user_id" in event.labels
    assert event.labels["user_id"] == str(setup_user.id)
    assert f"user_id:{str(setup_user.id)}" in event.tags


def test_user_created_event_data_completeness(setup_user):
    """Test that user created event contains all expected fields."""
    event = build_user_created_event(setup_user)
    user_data = event.event_data["user"]

    # Verify all expected fields are present
    assert "email" in user_data
    assert "first_name" in user_data
    assert "last_name" in user_data
    assert "username" in user_data
    assert user_data["email"] == setup_user.email
    assert user_data["first_name"] == setup_user.first_name
    assert user_data["last_name"] == setup_user.last_name


def test_user_updated_event_with_different_user_id(setup_user, setup_another_user):
    """Test that user updated event uses the provided user_id."""
    event = build_user_updated_event(setup_user, setup_another_user.id)

    # Verify the user_id in the event matches the provided user_id
    assert event.user_id == str(setup_another_user.id)
    # But the user data should still be from setup_user
    user_data = event.event_data["user"]
    assert user_data["email"] == setup_user.email


def test_user_deleted_event_with_different_user_id(setup_user, setup_another_user):
    """Test that user deleted event uses the provided user_id."""
    event = build_user_deleted_event(setup_user, setup_another_user.id)

    # Verify the user_id in the event matches the provided user_id
    assert event.user_id == str(setup_another_user.id)
    # But the user data should still be from setup_user
    user_data = event.event_data["user"]
    assert user_data["email"] == setup_user.email


def test_user_event_json_serializable(setup_user):
    """Test that event data is JSON serializable."""
    event = build_user_created_event(setup_user)

    # Verify event can be serialized to JSON
    event_json = event.model_dump_json()
    assert event_json is not None
    assert len(event_json) > 0

    # Verify event_data is JSON serializable
    import json

    event_data_json = json.dumps(event.event_data)
    assert event_data_json is not None


def test_user_event_with_optional_fields(setup_user, db):
    """Test that user events handle optional fields correctly."""
    # Update user with optional fields
    setup_user.avatar_asset_id = "test-asset-id"
    setup_user.provider = "google"
    setup_user.theme_preference = "light"
    setup_user.verified = True
    setup_user.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(setup_user)

    event = build_user_updated_event(setup_user, setup_user.id)
    user_data = event.event_data["user"]

    # Verify optional fields are included
    assert user_data.get("avatar_asset_id") == "test-asset-id"
    assert user_data.get("provider") == "google"
    assert user_data.get("theme_preference") == "light"
    assert user_data.get("verified") is True
    assert user_data.get("verified_at") is not None
