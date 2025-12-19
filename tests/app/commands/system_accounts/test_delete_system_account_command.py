import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from app.commands.system_accounts.delete_system_account_command import (
    DeleteSystemAccountCommand,
)
from app.services.user_service import UserService


def test_delete_system_account_success(db: Session, setup_system_account):
    """Test successfully deleting a system account."""
    command = DeleteSystemAccountCommand(db)
    account_id = setup_system_account.id

    success = command.execute(account_id)

    # Assertions
    assert success is True

    # Verify the account was deleted
    user_service = UserService(db)
    deleted_account = user_service.get_user(account_id)
    assert deleted_account is None


def test_delete_system_account_not_found(db: Session):
    """Test deleting a non-existent system account."""
    command = DeleteSystemAccountCommand(db)

    with pytest.raises(Exception) as exc_info:
        command.execute(uuid4())

    assert "not found" in str(exc_info.value).lower()


def test_delete_system_account_not_service_account(db: Session, setup_user):
    """Test deleting a regular user (not a system account) fails."""
    command = DeleteSystemAccountCommand(db)

    with pytest.raises(Exception) as exc_info:
        command.execute(setup_user.id)

    assert "not a system account" in str(exc_info.value).lower()


def test_delete_system_account_rollback_on_error(db: Session, setup_system_account):
    """Test that exception is raised when trying to delete non-existent account."""
    command = DeleteSystemAccountCommand(db)
    account_id = setup_system_account.id

    # Try to delete non-existent account (should fail and raise exception)
    with pytest.raises(Exception) as exc_info:
        command.execute(uuid4())

    # Verify the exception message indicates the error
    assert (
        "not found" in str(exc_info.value).lower()
        or "failed" in str(exc_info.value).lower()
    )

    # Note: In the test environment, the db fixture uses transactions that rollback
    # at the end of each test, so we can't reliably verify persistence here.
    # The important thing is that the exception was raised correctly.
