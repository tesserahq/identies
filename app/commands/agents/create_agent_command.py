import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from tessera_sdk.infra.events.nats_router import NatsEventPublisher

from app.config import get_settings
from app.constants.user_kinds import UserKind
from app.events.user_events import build_user_created_event
from app.models.user import User
from app.repositories.agent_claim_repository import AgentClaimRepository
from app.schemas.agent import AgentCreateRequest


class CreateAgentCommand:
    """
    Command to create an agent principal and its first claim code.

    An agent is a user with kind=agent: no password, a synthetic non-deliverable email,
    verified at creation, and only ever authenticated with an API key obtained through
    a claim. Identies models the principal only; which human is responsible for the
    agent is the calling product's concern and is not stored here.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.claims = AgentClaimRepository(db)
        self.settings = get_settings()
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, request: AgentCreateRequest) -> tuple[User, str, datetime]:
        """
        Returns:
            tuple[User, str, datetime]: the agent, the plaintext claim code (shown
            once) and the claim's expiry.
        """
        try:
            agent_id = uuid4()
            agent = User(
                id=agent_id,
                email=f"agent-{agent_id}@{self.settings.agent_email_domain}",
                first_name=request.name,
                last_name="Agent",
                external_id=f"agent-{secrets.token_urlsafe(16)}",
                verified=True,
                verified_at=datetime.now(timezone.utc),
                kind=UserKind.AGENT,
            )
            self.db.add(agent)
            self.db.flush()

            # Same transaction: an agent never exists without a way to claim it.
            claim, code = self.claims.create_claim(
                agent_id, self.settings.agent_claim_ttl_minutes, commit=False
            )
            self.db.commit()
            self.db.refresh(agent)
            self.db.refresh(claim)
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create agent: {str(e)}")

        self._publish_user_created_event(agent)
        return agent, code, claim.expires_at

    def _publish_user_created_event(self, user: User) -> None:
        event = build_user_created_event(user)

        if self.nats_publisher is not None:
            self.logger.info(f"Publishing {event.event_type} event to NATS")
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    f"Failed to publish {event.event_type} event to NATS"
                )
