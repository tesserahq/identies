import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories.api_key_repository import ApiKeyRepository
from app.models.api_key import ApiKey
from app.models.user import User
from app.events.api_key_events import build_api_key_deleted_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class DeleteApiKeyCommand:
    """
    Command to delete an API key.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.api_key_service = ApiKeyRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, api_key_id: UUID, user_id: UUID, deleted_by: User) -> bool:
        """
        Execute the command to delete an API key.

        Args:
            api_key_id: The ID of the API key to delete
            user_id: The ID of the user (for security)
            deleted_by: The user deleting the API key

        Returns:
            bool: True if the API key was deleted successfully

        Raises:
            Exception: If API key deletion fails
        """
        try:
            # Get the API key before deletion for event publishing
            api_key = self.api_key_service.get_api_key_by_id(api_key_id)
            if not api_key:
                raise Exception("API key not found")

            if api_key.user_id != user_id:
                raise Exception("API key not owned by user")

            # Delete the API key
            success = self.api_key_service.delete_api_key(api_key_id, user_id)

            if not success:
                raise Exception("Failed to delete API key")

            self._publish_api_key_deleted_event(api_key, deleted_by)

            return success

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to delete API key: {str(e)}")

    def _publish_api_key_deleted_event(self, api_key: ApiKey, user: User) -> None:
        """
        Publish an API key deleted event.

        Args:
            api_key: The deleted API key
            user: The user who deleted the API key
        """
        event = build_api_key_deleted_event(api_key, user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing api_key-deleted event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish api_key-deleted event to NATS")
