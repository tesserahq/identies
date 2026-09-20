import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from tessera_sdk.infra.events.nats_router import NatsEventPublisher

from app.events.user_events import build_user_deleted_event
from app.exceptions.agent_error import AgentNotFoundError
from app.repositories.agent_claim_repository import AgentClaimRepository
from app.repositories.agent_repository import AgentRepository
from app.repositories.user_repository import UserRepository


class DeleteAgentCommand:
    """
    Command to delete an agent.

    Only agents can be deleted through this command: a human or a service account is
    reported as not found, so a caller cannot delete them by guessing an id. The agent
    is soft-deleted (the row stays as a tombstone for records that reference it) and
    its credentials and open claim codes stop working. Publishes ``user.deleted``.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.agents = AgentRepository(db)
        self.users = UserRepository(db)
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
            # Soft-deletes the user and revokes its API keys and clients in one commit.
            if not self.users.delete_user(agent_id):
                raise AgentNotFoundError()
        except AgentNotFoundError:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        self._publish(agent)

    def _publish(self, agent) -> None:
        event = build_user_deleted_event(agent, agent.id)
        if self.nats_publisher is not None:
            self.logger.info(f"Publishing {event.event_type} event to NATS")
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    f"Failed to publish {event.event_type} event to NATS"
                )
