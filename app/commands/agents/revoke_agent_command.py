import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from tessera_sdk.infra.events.nats_router import NatsEventPublisher

from app.events.client_events import build_client_revoked_event
from app.exceptions.agent_error import AgentNotFoundError
from app.repositories.agent_claim_repository import AgentClaimRepository
from app.repositories.agent_repository import AgentRepository
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.client_repository import ClientRepository


class RevokeAgentCommand:
    """
    Command to cut off an agent's access.

    Revokes every credential the agent has (OAuth clients and any API keys) and
    invalidates open claim codes, so it can no longer mint tokens or be claimed. Tokens
    already minted stay valid until they expire (at most 15 minutes). Idempotent.
    Rotating the credentials is how access is restored.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.agents = AgentRepository(db)
        self.clients = ClientRepository(db)
        self.api_keys = ApiKeyRepository(db)
        self.claims = AgentClaimRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, agent_id: UUID) -> None:
        """
        Raises:
            AgentNotFoundError: no active agent with this id
        """
        agent = self.agents.get_agent(agent_id)
        if agent is None:
            raise AgentNotFoundError()

        try:
            self.claims.invalidate_open_claims(agent_id)
            self.db.commit()
            self.api_keys.revoke_all_for_user(agent_id)
            revoked = self.clients.revoke_all_for_owner(agent_id)
        except Exception:
            self.db.rollback()
            raise

        for client in revoked:
            self._publish(client, agent)

    def _publish(self, client, agent) -> None:
        event = build_client_revoked_event(client, agent)
        if self.nats_publisher is not None:
            self.logger.info(f"Publishing {event.event_type} event to NATS")
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    f"Failed to publish {event.event_type} event to NATS"
                )
