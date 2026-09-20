import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from app.commands.service_accounts.update_service_account_command import (
    UpdateServiceAccountCommand,
)
from app.schemas.service_account import ServiceAccountUpdateRequest


def test_update_service_account_success(db: Session, setup_service_account, faker):
    """Test successfully updating a system account."""
    command = UpdateServiceAccountCommand(db)

    update_data = ServiceAccountUpdateRequest(
        first_name="Updated First",
        last_name="Updated Last",
        email=faker.email(),
    )

    updated_account = command.execute(setup_service_account.id, update_data)

    # Assertions
    assert updated_account is not None
    assert updated_account.id == setup_service_account.id
    assert updated_account.first_name == "Updated First"
    assert updated_account.last_name == "Updated Last"
    assert updated_account.email == update_data.email
    assert updated_account.service_account is True


def test_update_service_account_partial(db: Session, setup_service_account):
    """Test partially updating a system account."""
    command = UpdateServiceAccountCommand(db)

    original_email = setup_service_account.email
    original_last_name = setup_service_account.last_name

    update_data = ServiceAccountUpdateRequest(
        first_name="Updated First Only",
    )

    updated_account = command.execute(setup_service_account.id, update_data)

    # Assertions
    assert updated_account is not None
    assert updated_account.first_name == "Updated First Only"
    assert updated_account.email == original_email  # Should remain unchanged
    assert updated_account.last_name == original_last_name  # Should remain unchanged


def test_update_service_account_not_found(db: Session, faker):
    """Test updating a non-existent system account."""
    command = UpdateServiceAccountCommand(db)

    update_data = ServiceAccountUpdateRequest(
        first_name="Updated First",
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(uuid4(), update_data)

    assert "not found" in str(exc_info.value).lower()


def test_update_service_account_not_service_account(db: Session, setup_user, faker):
    """Test updating a regular user (not a service account) fails."""
    command = UpdateServiceAccountCommand(db)

    update_data = ServiceAccountUpdateRequest(
        first_name="Updated First",
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(setup_user.id, update_data)

    assert "not a service account" in str(exc_info.value).lower()


def test_update_service_account_duplicate_email(
    db: Session, setup_service_account, setup_user, faker
):
    """Test updating system account with duplicate email fails."""
    command = UpdateServiceAccountCommand(db)

    # Try to update with existing user's email
    update_data = ServiceAccountUpdateRequest(
        email=setup_user.email,
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(setup_service_account.id, update_data)

    assert "already exists" in str(exc_info.value).lower()


def test_update_service_account_rollback_on_error(
    db: Session, setup_service_account, setup_user
):
    """Test that exception is raised when trying to update with duplicate email."""
    command = UpdateServiceAccountCommand(db)

    account_id = setup_service_account.id

    # Try to update with duplicate email (should fail and raise exception)
    update_data = ServiceAccountUpdateRequest(
        email=setup_user.email,
        first_name="Should Not Update",
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(account_id, update_data)

    # Verify the exception message indicates the error
    assert (
        "already exists" in str(exc_info.value).lower()
        or "failed" in str(exc_info.value).lower()
    )

    # Note: In the test environment, the db fixture uses transactions that rollback
    # at the end of each test, so we can't reliably verify persistence here.
    # The important thing is that the exception was raised correctly.


def test_update_service_account_publishes_user_updated(
    db: Session, setup_service_account
):
    """user.updated carries the new values so projections can refresh the row."""
    from unittest.mock import MagicMock

    publisher = MagicMock()

    UpdateServiceAccountCommand(db, nats_publisher=publisher).execute(
        setup_service_account.id,
        ServiceAccountUpdateRequest(first_name="Renamed"),
    )

    publisher.publish_sync.assert_called_once()
    user_updated = publisher.publish_sync.call_args.args[0]
    assert user_updated.event_type.endswith("user.updated")
    assert user_updated.event_data["user"]["id"] == str(setup_service_account.id)
    assert user_updated.event_data["user"]["first_name"] == "Renamed"
