import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.api_key import ApiKeyCreate
from app.services.api_key_service import ApiKeyService
from app.models.api_key import ApiKey
from app.events.api_key_events import build_api_key_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreateApiKeyCommand:
    """
    Command to create a api_key.
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

    def execute(self, api_key_data: ApiKeyCreate) -> ApiKey:
        """
        Execute the command to create a api_key and optionally create a yearly reminder.

        Args:
            api_key_data: The api_key data to create
            account_id: The account ID to associate the api_key with

        Returns:
            ApiKey: The created api_key

        Raises:
            Exception: If api_key creation fails
        """
        try:
            # Create the api_key
            api_key, full_key = self.api_key_service.create_api_key(api_key_data)

            self._publish_api_key_created_event(api_key)

            return api_key, full_key

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to create api_key: {str(e)}")

    def _publish_api_key_created_event(self, api_key: ApiKey) -> None:
        """
        Publish a api_key created event.

        Args:
            api_key: The api_key to publish
        """
        event = build_api_key_created_event(api_key)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing api_key-created event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish api_key-created event to NATS")
