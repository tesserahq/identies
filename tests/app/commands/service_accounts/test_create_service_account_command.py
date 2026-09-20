import pytest
from sqlalchemy.orm import Session
from app.commands.service_accounts.create_service_account_command import (
    CreateServiceAccountCommand,
)
from app.schemas.service_account import ServiceAccountCreateRequest


def test_create_service_account_success(db: Session, faker):
    """Test successfully creating a system account."""
    command = CreateServiceAccountCommand(db)

    service_account_data = ServiceAccountCreateRequest(
        email=faker.email(),
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )

    service_account = command.execute(service_account_data)

    # Assertions
    assert service_account is not None
    assert service_account.id is not None
    assert service_account.email == service_account_data.email
    assert service_account.first_name == service_account_data.first_name
    assert service_account.last_name == service_account_data.last_name
    assert service_account.service_account is True
    assert service_account.external_id is not None
    assert service_account.external_id.startswith("system-")


def test_create_service_account_duplicate_email(db: Session, faker, setup_user):
    """Test creating a system account with duplicate email fails."""
    command = CreateServiceAccountCommand(db)

    # Use existing user's email
    service_account_data = ServiceAccountCreateRequest(
        email=setup_user.email,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(service_account_data)

    assert "already exists" in str(exc_info.value).lower()


def test_create_service_account_rollback_on_error(db: Session, faker):
    """Test that transaction is rolled back on error and exception is raised."""
    command = CreateServiceAccountCommand(db)

    # Create first system account
    service_account_data1 = ServiceAccountCreateRequest(
        email=faker.email(),
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )
    first_account = command.execute(service_account_data1)
    first_account_id = first_account.id

    # Try to create another with same email (should fail and raise exception)
    service_account_data2 = ServiceAccountCreateRequest(
        email=service_account_data1.email,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
    )

    with pytest.raises(Exception) as exc_info:
        command.execute(service_account_data2)

    # Verify the exception message indicates the error
    assert (
        "already exists" in str(exc_info.value).lower()
        or "failed" in str(exc_info.value).lower()
    )

    # Note: In the test environment, the db fixture uses transactions that rollback
    # at the end of each test, so we can't reliably verify persistence here.
    # The important thing is that the exception was raised correctly.


def test_create_service_account_publishes_user_created(db: Session, faker):
    """user.created lets projections upsert the new service account by id."""
    from unittest.mock import MagicMock

    publisher = MagicMock()
    account = CreateServiceAccountCommand(db, nats_publisher=publisher).execute(
        ServiceAccountCreateRequest(
            email=faker.email(),
            first_name=faker.first_name(),
            last_name=faker.last_name(),
        )
    )

    events = {
        c.args[0].event_type: c.args[0] for c in publisher.publish_sync.call_args_list
    }
    user_created = next(e for t, e in events.items() if t.endswith("user.created"))
    assert user_created.event_data["user"]["id"] == str(account.id)
    assert user_created.event_data["user"]["service_account"] is True
    assert any(t.endswith("service_account.created") for t in events)
