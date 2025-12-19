import pytest
from datetime import datetime, timezone
from tessera_sdk.events.event import event_type, event_source
from app.events.system_account_events import (
    build_system_account_created_event,
    build_system_account_updated_event,
    build_system_account_deleted_event,
    SYSTEM_ACCOUNT_CREATED,
    SYSTEM_ACCOUNT_UPDATED,
    SYSTEM_ACCOUNT_DELETED,
)


def test_build_system_account_created_event(setup_system_account):
    """Test building a system account created event."""
    event = build_system_account_created_event(setup_system_account)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(SYSTEM_ACCOUNT_CREATED)
    assert event.source == event_source(f"/system-accounts/{setup_system_account.id}")
    assert event.subject == f"/system-account/{setup_system_account.id}"
    assert event.user_id == str(setup_system_account.id)

    # Verify event data contains system account information
    assert "system_account" in event.event_data
    system_account_data = event.event_data["system_account"]
    assert system_account_data["email"] == setup_system_account.email
    assert system_account_data["first_name"] == setup_system_account.first_name
    assert system_account_data["last_name"] == setup_system_account.last_name
    assert system_account_data["username"] == setup_system_account.username

    # Verify labels and tags
    assert "system_account_id" in event.labels
    assert event.labels["system_account_id"] == str(setup_system_account.id)
    assert "user_id" in event.labels
    assert event.labels["user_id"] == str(setup_system_account.id)
    assert f"system_account_id:{str(setup_system_account.id)}" in event.tags
    assert f"user_id:{str(setup_system_account.id)}" in event.tags


def test_build_system_account_updated_event(setup_system_account):
    """Test building a system account updated event."""
    # Update the system account
    setup_system_account.first_name = "Updated"
    setup_system_account.last_name = "Name"
    setup_system_account.theme_preference = "dark"

    event = build_system_account_updated_event(
        setup_system_account, setup_system_account.id
    )

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(SYSTEM_ACCOUNT_UPDATED)
    assert event.source == event_source(f"/system-accounts/{setup_system_account.id}")
    assert event.subject == f"/system-account/{setup_system_account.id}"
    assert event.user_id == str(setup_system_account.id)

    # Verify event data contains updated system account information
    assert "system_account" in event.event_data
    system_account_data = event.event_data["system_account"]
    assert system_account_data["first_name"] == "Updated"
    assert system_account_data["last_name"] == "Name"
    assert system_account_data["theme_preference"] == "dark"

    # Verify labels and tags
    assert "system_account_id" in event.labels
    assert event.labels["system_account_id"] == str(setup_system_account.id)
    assert f"system_account_id:{str(setup_system_account.id)}" in event.tags


def test_build_system_account_deleted_event(setup_system_account):
    """Test building a system account deleted event."""
    event = build_system_account_deleted_event(
        setup_system_account, setup_system_account.id
    )

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(SYSTEM_ACCOUNT_DELETED)
    assert event.source == event_source(f"/system-accounts/{setup_system_account.id}")
    assert event.subject == f"/system-account/{setup_system_account.id}"
    assert event.user_id == str(setup_system_account.id)

    # Verify event data contains system account information
    assert "system_account" in event.event_data
    system_account_data = event.event_data["system_account"]
    assert system_account_data["email"] == setup_system_account.email
    assert system_account_data["first_name"] == setup_system_account.first_name
    assert system_account_data["last_name"] == setup_system_account.last_name

    # Verify labels and tags
    assert "system_account_id" in event.labels
    assert event.labels["system_account_id"] == str(setup_system_account.id)
    assert f"system_account_id:{str(setup_system_account.id)}" in event.tags


def test_system_account_created_event_data_completeness(setup_system_account):
    """Test that system account created event contains all expected fields."""
    event = build_system_account_created_event(setup_system_account)
    system_account_data = event.event_data["system_account"]

    # Verify all expected fields are present
    assert "email" in system_account_data
    assert "first_name" in system_account_data
    assert "last_name" in system_account_data
    assert system_account_data["email"] == setup_system_account.email
    assert system_account_data["first_name"] == setup_system_account.first_name
    assert system_account_data["last_name"] == setup_system_account.last_name


def test_system_account_updated_event_with_different_user_id(
    setup_system_account, setup_another_system_account
):
    """Test that system account updated event uses the provided user_id."""
    event = build_system_account_updated_event(
        setup_system_account, setup_another_system_account.id
    )

    # Verify the user_id in the event matches the provided user_id
    assert event.user_id == str(setup_another_system_account.id)
    # But the system account data should still be from setup_system_account
    system_account_data = event.event_data["system_account"]
    assert system_account_data["email"] == setup_system_account.email


def test_system_account_deleted_event_with_different_user_id(
    setup_system_account, setup_another_system_account
):
    """Test that system account deleted event uses the provided user_id."""
    event = build_system_account_deleted_event(
        setup_system_account, setup_another_system_account.id
    )

    # Verify the user_id in the event matches the provided user_id
    assert event.user_id == str(setup_another_system_account.id)
    # But the system account data should still be from setup_system_account
    system_account_data = event.event_data["system_account"]
    assert system_account_data["email"] == setup_system_account.email


def test_system_account_event_json_serializable(setup_system_account):
    """Test that event data is JSON serializable."""
    event = build_system_account_created_event(setup_system_account)

    # Verify event can be serialized to JSON
    event_json = event.model_dump_json()
    assert event_json is not None
    assert len(event_json) > 0

    # Verify event_data is JSON serializable
    import json

    event_data_json = json.dumps(event.event_data)
    assert event_data_json is not None


def test_system_account_event_with_optional_fields(setup_system_account, db):
    """Test that system account events handle optional fields correctly."""
    # Update system account with optional fields
    setup_system_account.avatar_asset_id = "test-asset-id"
    setup_system_account.provider = "system"
    setup_system_account.theme_preference = "light"
    setup_system_account.verified = True
    setup_system_account.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(setup_system_account)

    event = build_system_account_updated_event(
        setup_system_account, setup_system_account.id
    )
    system_account_data = event.event_data["system_account"]

    # Verify optional fields are included
    assert system_account_data.get("avatar_asset_id") == "test-asset-id"
    assert system_account_data.get("provider") == "system"
    assert system_account_data.get("theme_preference") == "light"
    assert system_account_data.get("verified") is True
    assert system_account_data.get("verified_at") is not None


def test_system_account_event_different_from_user_event(setup_system_account):
    """Test that system account events are different from user events."""
    from app.events.user_events import build_user_created_event

    system_account_event = build_system_account_created_event(setup_system_account)
    user_event = build_user_created_event(setup_system_account)

    # Verify event types are different
    assert system_account_event.event_type != user_event.event_type
    assert system_account_event.event_type == event_type(SYSTEM_ACCOUNT_CREATED)
    assert user_event.event_type == event_type("user.created")

    # Verify sources are different
    assert system_account_event.source != user_event.source
    assert "/system-accounts/" in system_account_event.source
    assert "/users/" in user_event.source

    # Verify subjects are different
    assert system_account_event.subject != user_event.subject
    assert "/system-account/" in system_account_event.subject
    assert "/user/" in user_event.subject

    # Verify event data keys are different
    assert "system_account" in system_account_event.event_data
    assert "user" in user_event.event_data
