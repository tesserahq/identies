import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.db import on_commit
from app.schemas.user import UserUpdate
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.events.user_events import build_user_updated_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class UpdateUserCommand:
    """
    Command to update a user.
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

    def execute(self, user_id: UUID, user_update: UserUpdate) -> User:
        """
        Execute the command to update a user.

        Args:
            user_id: The ID of the user to update
            user_update: The update data containing fields to update

        Returns:
            User: The updated user

        Raises:
            Exception: If user update fails
        """
        # Update the user
        updated_user = self.user_service.update_user(user_id, user_update)

        if not updated_user:
            raise ResourceNotFoundError("User not found")

        self._publish_user_updated_event(updated_user, user_id)

        return updated_user

    def _publish_user_updated_event(self, user: User, user_id: UUID) -> None:
        """
        Publish a user updated event.

        Args:
            user: The updated user
            user_id: The ID of the user who was updated
        """
        event = build_user_updated_event(user, user_id)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing user-updated event to NATS: {event.model_dump_json()}"
            )
            publisher = self.nats_publisher

            def publish() -> None:
                try:
                    publisher.publish_sync(event, event.event_type)
                except Exception:  # pragma: no cover - defensive logging
                    self.logger.exception(
                        "Failed to publish user-updated event to NATS"
                    )

            # Dispatch only after the transaction commits; dropped on rollback.
            on_commit(publish)
