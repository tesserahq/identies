"""Agent claim model: a short-lived, single-use code that turns an agent into a credential."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base
from app.models.mixins import TimestampMixin


class AgentClaim(Base, TimestampMixin):
    """
    A claim code for an agent user. The plaintext code (``ac_<claim_id>.<secret>``) is
    shown once when it is issued; only a hash of the secret is stored.

    A claim is usable once: it is open until it is claimed, invalidated (regenerated or
    locked after too many wrong secrets) or expired.
    """

    __tablename__ = "agent_claims"

    __table_args__ = (
        Index("uq_agent_claims_claim_id", "claim_id", unique=True),
        Index("idx_agent_claims_agent_user_id", "agent_user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    claim_id = Column(String, nullable=False)
    secret_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    invalidated_at = Column(DateTime(timezone=True), nullable=True)
    failed_attempts = Column(Integer, nullable=False, default=0)

    def is_open(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return (
            self.claimed_at is None
            and self.invalidated_at is None
            and self.expires_at > now
        )
