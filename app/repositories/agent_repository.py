from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.constants.user_kinds import UserKind
from app.models.agent_claim import AgentClaim
from app.models.client import Client
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository

AgentState = Literal["unclaimed", "active", "revoked", "expired"]


@dataclass(frozen=True)
class AgentStatus:
    agent: User
    state: AgentState
    client: Optional[Client]
    claim_expires_at: Optional[datetime]
    """When the open claim code expires (only while the agent is unclaimed)."""


class AgentRepository:
    """Lookups for agent principals. Deleted users and non-agents are never returned."""

    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.clients = ClientRepository(db)

    def get_agent(self, agent_id: UUID) -> Optional[User]:
        user = self.users.get_user(agent_id)
        if user is None or user.kind != UserKind.AGENT.value:
            return None
        return user

    def get_status(self, agent: User) -> AgentStatus:
        client = self.clients.get_latest_client_for_owner(agent.id)
        if client is None:
            now = datetime.now(timezone.utc)
            open_claims = (
                self.db.query(AgentClaim)
                .filter(
                    AgentClaim.agent_user_id == agent.id,
                    AgentClaim.claimed_at.is_(None),
                    AgentClaim.invalidated_at.is_(None),
                    AgentClaim.expires_at > now,
                )
                .order_by(AgentClaim.expires_at.desc())
                .first()
            )
            return AgentStatus(
                agent=agent,
                state="unclaimed",
                client=None,
                claim_expires_at=open_claims.expires_at if open_claims else None,
            )

        if client.revoked:
            state: AgentState = "revoked"
        elif client.is_expired():
            state = "expired"
        else:
            state = "active"
        return AgentStatus(
            agent=agent, state=state, client=client, claim_expires_at=None
        )
