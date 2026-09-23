import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.events.user_events import build_user_offboarding_scheduled_event
from app.exceptions.offboarding_error import OffboardingAlreadyScheduledError
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.exceptions.service_account_error import ServiceAccountError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from tessera_sdk.infra.events.nats_router import NatsEventPublisher

DEFAULT_OFFBOARDING_GRACE_PERIOD = timedelta(hours=24)


class ScheduleOffboardingCommand:
    """
    Command to schedule a user for offboarding.

    Scheduling only records intent (publishing user.offboarding_scheduled) -
    it does not touch the identity provider or soft-delete the user. That
    happens later, when a background job executes the offboarding once
    offboarding_scheduled_at elapses.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.user_service = UserRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        user_id: UUID,
        scheduled_by: User,
        scheduled_at: Optional[datetime] = None,
    ) -> User:
        try:
            user = self.user_service.get_user(user_id)
            if not user:
                raise ResourceNotFoundError("User not found")

            if user.service_account:
                raise ServiceAccountError(
                    "Service accounts cannot be offboarded through this flow"
                )

            if user.offboarding_scheduled_at is not None:
                raise OffboardingAlreadyScheduledError(
                    "User already has a pending offboarding scheduled"
                )

            effective_scheduled_at = (
                scheduled_at
                if scheduled_at is not None
                else datetime.now(timezone.utc) + DEFAULT_OFFBOARDING_GRACE_PERIOD
            )

            updated_user = self.user_service.schedule_offboarding(
                user_id, effective_scheduled_at, scheduled_by.id
            )
            if not updated_user:
                raise ResourceNotFoundError("User not found")

            self._publish_offboarding_scheduled_event(updated_user, scheduled_by.id)

            return updated_user

        except (
            ResourceNotFoundError,
            ServiceAccountError,
            OffboardingAlreadyScheduledError,
        ):
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to schedule offboarding: {str(e)}")

    def _publish_offboarding_scheduled_event(
        self, user: User, scheduled_by: UUID
    ) -> None:
        event = build_user_offboarding_scheduled_event(user, scheduled_by)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing user-offboarding-scheduled event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish user-offboarding-scheduled event to NATS"
                )
