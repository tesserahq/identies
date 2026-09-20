from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent_claim import AgentClaim
from app.utils.security import generate_agent_claim_code, hash_secret


class AgentClaimRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_claim(
        self, agent_user_id: UUID, ttl_minutes: int, commit: bool = True
    ) -> tuple[AgentClaim, str]:
        """Create a claim for an agent and return it with the plaintext code.

        Any previously open claim for the agent is invalidated first, so at most one
        claim is usable at a time.
        """
        self.invalidate_open_claims(agent_user_id)

        code, claim_id, secret = generate_agent_claim_code()
        claim = AgentClaim(
            agent_user_id=agent_user_id,
            claim_id=claim_id,
            secret_hash=hash_secret(secret),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )
        self.db.add(claim)
        if commit:
            self.db.commit()
            self.db.refresh(claim)
        else:
            self.db.flush()
        return claim, code

    def invalidate_open_claims(self, agent_user_id: UUID) -> None:
        self.db.query(AgentClaim).filter(
            AgentClaim.agent_user_id == agent_user_id,
            AgentClaim.claimed_at.is_(None),
            AgentClaim.invalidated_at.is_(None),
        ).update(
            {"invalidated_at": datetime.now(timezone.utc)}, synchronize_session=False
        )

    def get_for_update(self, claim_id: str) -> Optional[AgentClaim]:
        """Load a claim by its public id, locking the row so concurrent claims serialize."""
        return (
            self.db.query(AgentClaim)
            .filter(AgentClaim.claim_id == claim_id)
            .with_for_update()
            .first()
        )

    def has_been_claimed(self, agent_user_id: UUID) -> bool:
        return (
            self.db.query(AgentClaim)
            .filter(
                AgentClaim.agent_user_id == agent_user_id,
                AgentClaim.claimed_at.is_not(None),
            )
            .first()
            is not None
        )
