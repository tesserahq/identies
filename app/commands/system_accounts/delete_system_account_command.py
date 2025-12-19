import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.models.user import User
from app.events.system_account_events import build_system_account_deleted_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class DeleteSystemAccountCommand:
    """
    Command to delete a system account.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.user_service = UserService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, system_account_id: UUID) -> bool:
        """
        Execute the command to delete a system account.

        Args:
            system_account_id: The ID of the system account to delete

        Returns:
            bool: True if the system account was deleted successfully

        Raises:
            Exception: If system account deletion fails
        """
        try:
            # Verify it's a system account
            user = self.user_service.get_user(system_account_id)
            if not user:
                raise Exception("System account not found")

            if not user.service_account:
                raise Exception("User is not a system account")

            # Store user data for event before deletion
            user_data = user

            # Delete the system account
            success = self.user_service.delete_user(system_account_id)

            if not success:
                raise Exception("Failed to delete system account")

            self._publish_system_account_deleted_event(user_data, system_account_id)

            return True

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to delete system account: {str(e)}")

    def _publish_system_account_deleted_event(self, user: User, user_id: UUID) -> None:
        """
        Publish a system account deleted event.

        Args:
            user: The deleted system account
            user_id: The ID of the system account that was deleted
        """
        event = build_system_account_deleted_event(user, user_id)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing system-account-deleted event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish system-account-deleted event to NATS"
                )
