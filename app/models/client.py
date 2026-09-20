import uuid

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Client(Base, TimestampMixin, SoftDeleteMixin):
    """OAuth 2.0 client (machine-to-machine application credential)."""

    __tablename__ = "clients"

    __table_args__ = (
        Index("uq_clients_client_id", "client_id", unique=True),
        Index("idx_clients_owner_id", "owner_id"),
        Index("idx_clients_created_by_id", "created_by_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String, unique=True, nullable=False)
    secret_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", foreign_keys=[owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= datetime.now(
            timezone.utc
        )

    def is_valid(self) -> bool:
        return not self.revoked and self.deleted_at is None and not self.is_expired()
