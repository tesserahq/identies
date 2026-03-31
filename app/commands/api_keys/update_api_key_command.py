import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.schemas.api_key import ApiKeyUpdateRequest
from app.repositories.api_key_repository import ApiKeyRepository
from app.models.api_key import ApiKey
from app.models.user import User
from app.events.api_key_events import build_api_key_updated_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class UpdateApiKeyCommand:
    """
    Command to update an API key.
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

    def execute(
        self,
        api_key_id: UUID,
        user_id: UUID,
        update_data: ApiKeyUpdateRequest,
        updated_by: User,
    ) -> ApiKey:
        """
        Execute the command to update an API key.

        Args:
            api_key_id: The ID of the API key to update
            user_id: The ID of the user (for security)
            update_data: The update data containing name and/or revoked fields
            updated_by: The user updating the API key

        Returns:
            ApiKey: The updated API key

        Raises:
            Exception: If API key update fails
        """
        try:
            # Update the API key
            updated_api_key = self.api_key_service.update_api_key(
                api_key_id,
                user_id,
                name=update_data.name,
                revoked=update_data.revoked,
            )

            if not updated_api_key:
                raise Exception("API key not found or not owned by user")

            self._publish_api_key_updated_event(updated_api_key, updated_by)

            return updated_api_key

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to update API key: {str(e)}")

    def _publish_api_key_updated_event(self, api_key: ApiKey, user: User) -> None:
        """
        Publish an API key updated event.

        Args:
            api_key: The updated API key
            user: The user who updated the API key
        """
        event = build_api_key_updated_event(api_key, user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing api_key-updated event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish api_key-updated event to NATS")
