import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db import on_commit
from app.schemas.user import UserOnboard
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.events.user_events import build_user_created_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class OnboardUserCommand:
    """
    Command to onboard a new user.
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

    def execute(self, user_onboard: UserOnboard) -> User:
        """
        Execute the command to onboard a user.

        Args:
            user_onboard: The user onboarding data

        Returns:
            User: The onboarded user

        Raises:
            Exception: If user onboarding fails
        """
        # Onboard the user
        user = self.user_service.onboard_user(user_onboard)

        if not user:
            raise RuntimeError("Failed to onboard user")

        self._publish_user_created_event(user)

        return user

    def _publish_user_created_event(self, user: User) -> None:
        """
        Publish a user created event.

        Args:
            user: The onboarded user
        """
        event = build_user_created_event(user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing user-created event to NATS: {event.event_type}"
            )
            publisher = self.nats_publisher

            def publish() -> None:
                try:
                    publisher.publish_sync(event, event.event_type)
                except Exception:  # pragma: no cover - defensive logging
                    self.logger.exception(
                        "Failed to publish user-created event to NATS"
                    )

            # Dispatch only after the transaction commits; dropped on rollback.
            on_commit(publish)
