import json

from tessera_sdk.infra.events.event import event_source, event_type

from app.events.access_rule_events import (
    ACCESS_RULE_CREATED,
    ACCESS_RULE_DELETED,
    ACCESS_RULE_UPDATED,
    build_access_rule_created_event,
    build_access_rule_deleted_event,
    build_access_rule_updated_event,
)


def test_build_access_rule_created_event(setup_access_rule, setup_user):
    """Test building an access rule created event."""
    event = build_access_rule_created_event(setup_access_rule, setup_user)

    assert event is not None
    assert event.event_type == event_type(ACCESS_RULE_CREATED)
    assert event.source == event_source()
    assert event.subject == f"/access-rules/{setup_access_rule.id}"
    assert event.user_id == str(setup_user.id)

    assert "access_rule" in event.event_data
    assert "user" in event.event_data
    access_rule_data = event.event_data["access_rule"]
    user_data = event.event_data["user"]
    assert access_rule_data["kind"] == setup_access_rule.kind
    assert access_rule_data["value"] == setup_access_rule.value
    assert access_rule_data["note"] == setup_access_rule.note
    assert user_data["id"] == str(setup_user.id)
    assert user_data["email"] == setup_user.email

    assert "access_rule_id" in event.labels
    assert event.labels["access_rule_id"] == str(setup_access_rule.id)
    assert f"access_rule_id:{str(setup_access_rule.id)}" in event.tags


def test_build_access_rule_updated_event(setup_access_rule, setup_user):
    """Test building an access rule updated event."""
    setup_access_rule.note = "Updated note"

    event = build_access_rule_updated_event(setup_access_rule, setup_user)

    assert event is not None
    assert event.event_type == event_type(ACCESS_RULE_UPDATED)
    assert event.source == event_source()
    assert event.subject == f"/access-rules/{setup_access_rule.id}"
    assert event.user_id == str(setup_user.id)

    assert "access_rule" in event.event_data
    assert "user" in event.event_data
    access_rule_data = event.event_data["access_rule"]
    user_data = event.event_data["user"]
    assert access_rule_data["note"] == "Updated note"
    assert user_data["id"] == str(setup_user.id)
    assert user_data["email"] == setup_user.email

    assert "access_rule_id" in event.labels
    assert event.labels["access_rule_id"] == str(setup_access_rule.id)
    assert f"access_rule_id:{str(setup_access_rule.id)}" in event.tags


def test_build_access_rule_deleted_event(setup_access_rule, setup_user):
    """Test building an access rule deleted event."""
    event = build_access_rule_deleted_event(setup_access_rule, setup_user)

    assert event is not None
    assert event.event_type == event_type(ACCESS_RULE_DELETED)
    assert event.source == event_source()
    assert event.subject == f"/access-rules/{setup_access_rule.id}"
    assert event.user_id == str(setup_user.id)

    assert "access_rule" in event.event_data
    assert "user" in event.event_data
    access_rule_data = event.event_data["access_rule"]
    user_data = event.event_data["user"]
    assert access_rule_data["kind"] == setup_access_rule.kind
    assert access_rule_data["value"] == setup_access_rule.value
    assert user_data["id"] == str(setup_user.id)
    assert user_data["email"] == setup_user.email

    assert "access_rule_id" in event.labels
    assert event.labels["access_rule_id"] == str(setup_access_rule.id)
    assert f"access_rule_id:{str(setup_access_rule.id)}" in event.tags


def test_access_rule_created_event_data_completeness(setup_access_rule, setup_user):
    """Test that access rule created event contains all expected fields."""
    event = build_access_rule_created_event(setup_access_rule, setup_user)
    access_rule_data = event.event_data["access_rule"]
    user_data = event.event_data["user"]

    assert "id" in access_rule_data
    assert "kind" in access_rule_data
    assert "value" in access_rule_data
    assert "note" in access_rule_data
    assert "created_at" in access_rule_data
    assert "updated_at" in access_rule_data
    assert access_rule_data["id"] == str(setup_access_rule.id)
    assert "id" in user_data
    assert "email" in user_data
    assert user_data["id"] == str(setup_user.id)


def test_access_rule_updated_event_with_different_user(
    setup_access_rule, setup_another_user
):
    """Test that access rule updated event uses the provided user."""
    event = build_access_rule_updated_event(setup_access_rule, setup_another_user)

    assert event.user_id == str(setup_another_user.id)
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["id"] == str(setup_another_user.id)
    assert user_data["email"] == setup_another_user.email


def test_access_rule_deleted_event_with_different_user(
    setup_access_rule, setup_another_user
):
    """Test that access rule deleted event uses the provided user."""
    event = build_access_rule_deleted_event(setup_access_rule, setup_another_user)

    assert event.user_id == str(setup_another_user.id)
    assert "user" in event.event_data
    user_data = event.event_data["user"]
    assert user_data["id"] == str(setup_another_user.id)
    assert user_data["email"] == setup_another_user.email


def test_access_rule_event_json_serializable(setup_access_rule, setup_user):
    """Test that event data is JSON serializable."""
    event = build_access_rule_created_event(setup_access_rule, setup_user)

    event_json = event.model_dump_json()
    assert event_json is not None
    assert len(event_json) > 0

    event_data_json = json.dumps(event.event_data)
    assert event_data_json is not None
    event_data = json.loads(event_data_json)
    assert "access_rule" in event_data
    assert "user" in event_data
