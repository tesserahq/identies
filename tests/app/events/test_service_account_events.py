from datetime import datetime, timezone
from tessera_sdk.infra.events.event import event_type, event_source
from app.events.service_account_events import (
    build_service_account_created_event,
    build_service_account_updated_event,
    build_service_account_deleted_event,
    SERVICE_ACCOUNT_CREATED,
    SERVICE_ACCOUNT_UPDATED,
    SERVICE_ACCOUNT_DELETED,
)


def test_build_service_account_created_event(setup_service_account):
    """Test building a service account created event."""
    event = build_service_account_created_event(setup_service_account)

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(SERVICE_ACCOUNT_CREATED)
    assert event.source == event_source()
    assert event.subject == f"/service-accounts/{setup_service_account.id}"
    assert event.user_id == str(setup_service_account.id)

    # Verify event data contains system account information
    assert "service_account" in event.event_data
    service_account_data = event.event_data["service_account"]
    assert service_account_data["email"] == setup_service_account.email
    assert service_account_data["first_name"] == setup_service_account.first_name
    assert service_account_data["last_name"] == setup_service_account.last_name

    # Verify labels and tags
    assert "service_account_id" in event.labels
    assert event.labels["service_account_id"] == str(setup_service_account.id)
    assert "user_id" in event.labels
    assert event.labels["user_id"] == str(setup_service_account.id)
    assert f"service_account_id:{str(setup_service_account.id)}" in event.tags
    assert f"user_id:{str(setup_service_account.id)}" in event.tags


def test_build_service_account_updated_event(setup_service_account):
    """Test building a service account updated event."""
    # Update the service account
    setup_service_account.first_name = "Updated"
    setup_service_account.last_name = "Name"
    setup_service_account.theme_preference = "dark"

    event = build_service_account_updated_event(
        setup_service_account, setup_service_account.id
    )

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(SERVICE_ACCOUNT_UPDATED)
    assert event.source == event_source()
    assert event.subject == f"/service-accounts/{setup_service_account.id}"
    assert event.user_id == str(setup_service_account.id)

    # Verify event data contains updated system account information
    assert "service_account" in event.event_data
    service_account_data = event.event_data["service_account"]
    assert service_account_data["first_name"] == "Updated"
    assert service_account_data["last_name"] == "Name"
    assert service_account_data["theme_preference"] == "dark"

    # Verify labels and tags
    assert "service_account_id" in event.labels
    assert event.labels["service_account_id"] == str(setup_service_account.id)
    assert f"service_account_id:{str(setup_service_account.id)}" in event.tags


def test_build_service_account_deleted_event(setup_service_account):
    """Test building a service account deleted event."""
    event = build_service_account_deleted_event(
        setup_service_account, setup_service_account.id
    )

    # Verify event structure
    assert event is not None
    assert event.event_type == event_type(SERVICE_ACCOUNT_DELETED)
    assert event.source == event_source()
    assert event.subject == f"/service-accounts/{setup_service_account.id}"
    assert event.user_id == str(setup_service_account.id)

    # Verify event data contains system account information
    assert "service_account" in event.event_data
    service_account_data = event.event_data["service_account"]
    assert service_account_data["email"] == setup_service_account.email
    assert service_account_data["first_name"] == setup_service_account.first_name
    assert service_account_data["last_name"] == setup_service_account.last_name

    # Verify labels and tags
    assert "service_account_id" in event.labels
    assert event.labels["service_account_id"] == str(setup_service_account.id)
    assert f"service_account_id:{str(setup_service_account.id)}" in event.tags


def test_service_account_created_event_data_completeness(setup_service_account):
    """Test that service account created event contains all expected fields."""
    event = build_service_account_created_event(setup_service_account)
    service_account_data = event.event_data["service_account"]

    # Verify all expected fields are present
    assert "email" in service_account_data
    assert "first_name" in service_account_data
    assert "last_name" in service_account_data
    assert service_account_data["email"] == setup_service_account.email
    assert service_account_data["first_name"] == setup_service_account.first_name
    assert service_account_data["last_name"] == setup_service_account.last_name


def test_service_account_updated_event_with_different_user_id(
    setup_service_account, setup_another_service_account
):
    """Test that service account updated event uses the provided user_id."""
    event = build_service_account_updated_event(
        setup_service_account, setup_another_service_account.id
    )

    # Verify the user_id in the event matches the provided user_id
    assert event.user_id == str(setup_another_service_account.id)
    # But the service account data should still be from setup_service_account
    service_account_data = event.event_data["service_account"]
    assert service_account_data["email"] == setup_service_account.email


def test_service_account_deleted_event_with_different_user_id(
    setup_service_account, setup_another_service_account
):
    """Test that service account deleted event uses the provided user_id."""
    event = build_service_account_deleted_event(
        setup_service_account, setup_another_service_account.id
    )

    # Verify the user_id in the event matches the provided user_id
    assert event.user_id == str(setup_another_service_account.id)
    # But the service account data should still be from setup_service_account
    service_account_data = event.event_data["service_account"]
    assert service_account_data["email"] == setup_service_account.email


def test_service_account_event_json_serializable(setup_service_account):
    """Test that event data is JSON serializable."""
    event = build_service_account_created_event(setup_service_account)

    # Verify event can be serialized to JSON
    event_json = event.model_dump_json()
    assert event_json is not None
    assert len(event_json) > 0

    # Verify event_data is JSON serializable
    import json

    event_data_json = json.dumps(event.event_data)
    assert event_data_json is not None


def test_service_account_event_with_optional_fields(setup_service_account, db):
    """Test that service account events handle optional fields correctly."""
    # Update service account with optional fields
    setup_service_account.avatar_asset_id = "test-asset-id"
    setup_service_account.provider = "system"
    setup_service_account.theme_preference = "light"
    setup_service_account.verified = True
    setup_service_account.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(setup_service_account)

    event = build_service_account_updated_event(
        setup_service_account, setup_service_account.id
    )
    service_account_data = event.event_data["service_account"]

    # Verify optional fields are included
    assert service_account_data.get("avatar_asset_id") == "test-asset-id"
    assert service_account_data.get("provider") == "system"
    assert service_account_data.get("theme_preference") == "light"
    assert service_account_data.get("verified") is True
    assert service_account_data.get("verified_at") is not None


def test_service_account_event_different_from_user_event(setup_service_account):
    """Test that service account events are different from user events."""
    from app.events.user_events import build_user_created_event

    service_account_event = build_service_account_created_event(setup_service_account)
    user_event = build_user_created_event(setup_service_account)

    # Verify event types are different
    assert service_account_event.event_type != user_event.event_type
    assert service_account_event.event_type == event_type(SERVICE_ACCOUNT_CREATED)
    assert user_event.event_type == event_type("user.created")

    # Verify sources are different
    assert service_account_event.source == user_event.source

    # Verify subjects are different
    assert (
        service_account_event.subject == f"/service-accounts/{setup_service_account.id}"
    )
    assert user_event.subject == f"/users/{setup_service_account.id}"
