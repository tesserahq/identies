import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.api_key_service import ApiKeyService
from app.models.api_key import ApiKey
from app.events.api_key_events import build_api_key_updated_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class RevokeApiKeyCommand:
    """
    Command to revoke an API key.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.api_key_service = ApiKeyService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, api_key_id: UUID, user_id: UUID) -> ApiKey:
        """
        Execute the command to revoke an API key.

        Args:
            api_key_id: The ID of the API key to revoke
            user_id: The ID of the user (for security)

        Returns:
            ApiKey: The revoked API key

        Raises:
            Exception: If API key revocation fails
        """
        try:
            # Revoke the API key
            success = self.api_key_service.revoke_api_key(api_key_id, user_id)

            if not success:
                raise Exception("API key not found or not owned by user")

            # Get the updated API key for event publishing
            revoked_api_key = self.api_key_service.get_api_key_by_id(api_key_id)
            if not revoked_api_key:
                raise Exception("Failed to retrieve revoked API key")

            self._publish_api_key_updated_event(revoked_api_key, user_id)

            return revoked_api_key

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to revoke API key: {str(e)}")

    def _publish_api_key_updated_event(self, api_key: ApiKey, user_id: UUID) -> None:
        """
        Publish an API key updated event (for revocation).

        Args:
            api_key: The revoked API key
            user_id: The ID of the user who revoked the API key
        """
        event = build_api_key_updated_event(api_key, user_id)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing api_key-updated event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish api_key-updated event to NATS")
