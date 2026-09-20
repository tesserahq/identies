import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from tessera_sdk.infra.events.nats_router import NatsEventPublisher

from app.config import get_settings
from app.events.client_events import build_client_rotated_event
from app.exceptions.agent_error import AgentNotClaimedError, AgentNotFoundError
from app.models.client import Client
from app.repositories.agent_repository import AgentRepository
from app.repositories.client_repository import ClientRepository


class RotateAgentCredentialsCommand:
    """
    Command to replace an agent's client secret.

    The client id stays the same. The old secret stops working immediately, a revoked
    client is restored (revoke has no separate pause state, so rotating is how access is
    restored) and the expiry restarts. Tokens already minted stay valid until they expire.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.agents = AgentRepository(db)
        self.clients = ClientRepository(db)
        self.settings = get_settings()
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, agent_id: UUID) -> tuple[Client, str]:
        """
        Returns:
            tuple[Client, str]: the client and its new plaintext secret (shown once).

        Raises:
            AgentNotFoundError: no active agent with this id
            AgentNotClaimedError: the agent has no credentials yet
        """
        agent = self.agents.get_agent(agent_id)
        if agent is None:
            raise AgentNotFoundError()

        try:
            # Lock the client so concurrent rotations serialize.
            client = self.clients.get_latest_client_for_owner(agent_id, for_update=True)
            if client is None:
                # Nothing was changed; commit only to release the lock.
                self.db.commit()
                raise AgentNotClaimedError()
            secret = self.clients.rotate_secret(
                client, self.settings.agent_client_secret_ttl_days
            )
        except AgentNotClaimedError:
            raise
        except Exception:
            self.db.rollback()
            raise

        self._publish(client, agent)
        return client, secret

    def _publish(self, client: Client, agent) -> None:
        event = build_client_rotated_event(client, agent)
        if self.nats_publisher is not None:
            self.logger.info(f"Publishing {event.event_type} event to NATS")
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    f"Failed to publish {event.event_type} event to NATS"
                )
