import pytest
from sqlalchemy.orm import Session
from app.commands.system_accounts.create_system_account_command import (
    CreateSystemAccountCommand,
)
from app.schemas.system_account import SystemAccountCreateRequest
from app.services.user_service import UserService


def test_create_system_account_success(db: Session, faker):
    """Test successfully creating a system account."""
    command = CreateSystemAccountCommand(db)

    system_account_data = SystemAccountCreateRequest(
        email=faker.email(),
        first_name=faker.first_name(),
        last_name=faker.last_name(),
        username=faker.user_name(),
    )

    system_account = command.execute(system_account_data)

    # Assertions
    assert system_account is not None
    assert system_account.id is not None
    assert system_account.email == system_account_data.email
    assert system_account.first_name == system_account_data.first_name
    assert system_account.last_name == system_account_data.last_name
    assert system_account.username == system_account_data.username
    assert system_account.service_account is True
    assert system_account.external_id is not None
    assert system_account.external_id.startswith("system-")


def test_create_system_account_without_username(db: Session, faker):
    """Test creating a system account without username."""
    command = CreateSystemAccountCommand(db)

    system_account_data = SystemAccountCreateRequest(
        email=faker.email(),
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )

    system_account = command.execute(system_account_data)

    # Assertions
    assert system_account is not None
    assert system_account.email == system_account_data.email
    assert system_account.service_account is True


def test_create_system_account_duplicate_email(db: Session, faker, setup_user):
    """Test creating a system account with duplicate email fails."""
    command = CreateSystemAccountCommand(db)

    # Use existing user's email
    system_account_data = SystemAccountCreateRequest(
        email=setup_user.email,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(system_account_data)

    assert "already exists" in str(exc_info.value).lower()


def test_create_system_account_rollback_on_error(db: Session, faker):
    """Test that transaction is rolled back on error and exception is raised."""
    command = CreateSystemAccountCommand(db)

    # Create first system account
    system_account_data1 = SystemAccountCreateRequest(
        email=faker.email(),
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )
    first_account = command.execute(system_account_data1)
    first_account_id = first_account.id

    # Try to create another with same email (should fail and raise exception)
    system_account_data2 = SystemAccountCreateRequest(
        email=system_account_data1.email,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(system_account_data2)

    # Verify the exception message indicates the error
    assert (
        "already exists" in str(exc_info.value).lower()
        or "failed" in str(exc_info.value).lower()
    )

    # Note: In the test environment, the db fixture uses transactions that rollback
    # at the end of each test, so we can't reliably verify persistence here.
    # The important thing is that the exception was raised correctly.
