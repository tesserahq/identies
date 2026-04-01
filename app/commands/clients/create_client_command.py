import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.events.client_events import build_client_created_event
from app.models.client import Client
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class CreateClientCommand:
    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.client_repository = ClientRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self, client_data: ClientCreate, created_by: User
    ) -> tuple[Client, str]:
        client, client_secret = self.client_repository.create_client(client_data)
        self._publish_event(client, created_by)
        return client, client_secret

    def _publish_event(self, client: Client, user: User) -> None:
        event = build_client_created_event(client, user)
        try:
            self.nats_publisher.publish_sync(event, event.event_type)
        except Exception:  # pragma: no cover
            self.logger.exception("Failed to publish client.created event to NATS")
