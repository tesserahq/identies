from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.commands.users.cancel_offboarding_command import CancelOffboardingCommand
from app.commands.users.schedule_offboarding_command import ScheduleOffboardingCommand
from app.exceptions.offboarding_error import OffboardingNotScheduledError
from app.exceptions.resource_not_found_error import ResourceNotFoundError


def test_cancel_offboarding_clears_schedule(
    db: Session, setup_user, setup_another_user
):
    ScheduleOffboardingCommand(db).execute(setup_user.id, setup_another_user)

    updated_user = CancelOffboardingCommand(db).execute(setup_user.id)

    assert updated_user.offboarding_scheduled_at is None
    assert updated_user.offboarding_scheduled_by is None


def test_cancel_offboarding_allows_rescheduling(
    db: Session, setup_user, setup_another_user
):
    command = ScheduleOffboardingCommand(db)
    command.execute(setup_user.id, setup_another_user)
    CancelOffboardingCommand(db).execute(setup_user.id)

    # Should not raise OffboardingAlreadyScheduledError now that it's cancelled
    updated_user = command.execute(setup_user.id, setup_another_user)
    assert updated_user.offboarding_scheduled_at is not None


def test_cancel_offboarding_user_not_found(db: Session):
    with pytest.raises(ResourceNotFoundError):
        CancelOffboardingCommand(db).execute(uuid4())


def test_cancel_offboarding_not_scheduled(db: Session, setup_user):
    with pytest.raises(OffboardingNotScheduledError):
        CancelOffboardingCommand(db).execute(setup_user.id)
