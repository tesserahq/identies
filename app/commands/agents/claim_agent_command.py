import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from tessera_sdk.infra.events.nats_router import NatsEventPublisher

from app.config import get_settings
from app.constants.user_kinds import UserKind
from app.events.client_events import build_client_created_event
from app.exceptions.agent_error import AgentClaimError
from app.models.client import Client
from app.repositories.agent_claim_repository import AgentClaimRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.client import ClientCreate
from app.utils.security import parse_agent_claim_code, secrets_match


class ClaimAgentCommand:
    """
    Command to exchange a claim code for the agent's OAuth client credentials.

    The claim row is locked while it is checked and consumed, so concurrent claims of
    the same code produce exactly one key. Every failure raises the same
    ``AgentClaimError`` (invalid, expired, already used or locked).
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.claims = AgentClaimRepository(db)
        self.users = UserRepository(db)
        self.clients = ClientRepository(db)
        self.settings = get_settings()
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, code: str) -> tuple[Client, str]:
        """
        Returns:
            tuple[Client, str]: the agent's OAuth client and its plaintext secret
            (shown once). The agent exchanges them for short-lived JWTs at /oauth/token.

        Raises:
            AgentClaimError: for any invalid, expired, used or locked claim.
        """
        try:
            claim_id, secret = parse_agent_claim_code(code)
        except ValueError:
            raise AgentClaimError()

        claim = self.claims.get_for_update(claim_id)
        if claim is None:
            raise AgentClaimError()

        now = datetime.now(timezone.utc)
        if not claim.is_open(now):
            self._reject()

        if not secrets_match(secret, claim.secret_hash):
            # Persist the attempt, and lock the claim after too many wrong secrets.
            claim.failed_attempts += 1
            if claim.failed_attempts >= self.settings.agent_claim_max_failed_attempts:
                claim.invalidated_at = now
            self.db.commit()
            raise AgentClaimError()

        agent = self.users.get_user(claim.agent_user_id)
        if agent is None or agent.kind != UserKind.AGENT.value:
            self._reject()

        try:
            claim.claimed_at = now
            # create_client commits, so consuming the claim and creating the client
            # happen in one transaction.
            client, client_secret = self.clients.create_client(
                ClientCreate(
                    name="Agent credentials",
                    owner_id=agent.id,
                    created_by_id=agent.id,
                    expires_at=now
                    + timedelta(days=self.settings.agent_client_secret_ttl_days),
                )
            )
        except Exception:
            self.db.rollback()
            raise

        self._publish_client_created_event(client, agent)
        return client, client_secret

    def _reject(self) -> None:
        """Release the claim row lock (nothing was changed) and fail generically."""
        self.db.commit()
        raise AgentClaimError()

    def _publish_client_created_event(self, client: Client, agent) -> None:
        event = build_client_created_event(client, agent)

        if self.nats_publisher is not None:
            self.logger.info(f"Publishing {event.event_type} event to NATS")
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    f"Failed to publish {event.event_type} event to NATS"
                )
