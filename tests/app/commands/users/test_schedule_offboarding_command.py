from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.commands.users.schedule_offboarding_command import (
    DEFAULT_OFFBOARDING_GRACE_PERIOD,
    ScheduleOffboardingCommand,
)
from app.exceptions.offboarding_error import OffboardingAlreadyScheduledError
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.exceptions.service_account_error import ServiceAccountError


def test_schedule_offboarding_defaults_to_24h(
    db: Session, setup_user, setup_another_user
):
    command = ScheduleOffboardingCommand(db)

    before = datetime.now(timezone.utc)
    updated_user = command.execute(setup_user.id, setup_another_user)
    after = datetime.now(timezone.utc)

    assert updated_user.offboarding_scheduled_at is not None
    scheduled_at = updated_user.offboarding_scheduled_at.replace(tzinfo=timezone.utc)
    assert before + DEFAULT_OFFBOARDING_GRACE_PERIOD <= scheduled_at
    assert scheduled_at <= after + DEFAULT_OFFBOARDING_GRACE_PERIOD
    assert updated_user.offboarding_scheduled_by == setup_another_user.id


def test_schedule_offboarding_with_explicit_time(
    db: Session, setup_user, setup_another_user
):
    command = ScheduleOffboardingCommand(db)
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=7)

    updated_user = command.execute(
        setup_user.id, setup_another_user, scheduled_at=scheduled_at
    )

    assert (
        updated_user.offboarding_scheduled_at.replace(tzinfo=timezone.utc)
        == scheduled_at
    )


def test_schedule_offboarding_user_not_found(db: Session, setup_another_user):
    command = ScheduleOffboardingCommand(db)

    with pytest.raises(ResourceNotFoundError):
        command.execute(uuid4(), setup_another_user)


def test_schedule_offboarding_rejects_service_account(
    db: Session, setup_service_account, setup_another_user
):
    command = ScheduleOffboardingCommand(db)

    with pytest.raises(ServiceAccountError):
        command.execute(setup_service_account.id, setup_another_user)


def test_schedule_offboarding_rejects_already_scheduled(
    db: Session, setup_user, setup_another_user
):
    command = ScheduleOffboardingCommand(db)
    command.execute(setup_user.id, setup_another_user)

    with pytest.raises(OffboardingAlreadyScheduledError):
        command.execute(setup_user.id, setup_another_user)
