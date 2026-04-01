import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.events.client_events import build_client_deleted_event
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class DeleteClientCommand:
    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.client_repository = ClientRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, client_id: UUID, deleted_by: User) -> bool:
        client = self.client_repository.get_client_by_id(client_id)
        if not client:
            raise Exception("Client not found")

        success = self.client_repository.delete_client(client_id)
        if success:
            self._publish_event(client, deleted_by)
        return success

    def _publish_event(self, client, user: User) -> None:
        event = build_client_deleted_event(client, user)
        try:
            self.nats_publisher.publish_sync(event, event.event_type)
        except Exception:  # pragma: no cover
            self.logger.exception("Failed to publish client.deleted event to NATS")
