import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.events.service_account_events import build_service_account_deleted_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class DeleteServiceAccountCommand:
    """
    Command to delete a service account.
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

    def execute(self, service_account_id: UUID) -> bool:
        """
        Execute the command to delete a service account.

        Args:
            service_account_id: The ID of the service account to delete

        Returns:
            bool: True if the service account was deleted successfully

        Raises:
            Exception: If service account deletion fails
        """
        try:
            # Verify it's a service account
            user = self.user_service.get_user(service_account_id)
            if not user:
                raise Exception("Service account not found")

            if not user.service_account:
                raise Exception("User is not a service account")

            # Store user data for event before deletion
            user_data = user

            # Delete the service account
            success = self.user_service.delete_user(service_account_id)

            if not success:
                raise Exception("Failed to delete service account")

            self._publish_service_account_deleted_event(user_data, service_account_id)

            return True

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to delete service account: {str(e)}")

    def _publish_service_account_deleted_event(self, user: User, user_id: UUID) -> None:
        """
        Publish a service account deleted event.

        Args:
            user: The deleted service account
            user_id: The ID of the service account that was deleted
        """
        event = build_service_account_deleted_event(user, user_id)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing service-account-deleted event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish service-account-deleted event to NATS"
                )
