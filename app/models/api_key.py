from app.models.mixins import TimestampMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db import Base


class ApiKey(Base, TimestampMixin):
    """API Key model for the application.
    This model represents an API key that can be used for authentication.
    """

    __tablename__ = "api_keys"

    __table_args__ = (
        Index("uq_api_keys_key_id", "key_id", unique=True),
        Index("idx_api_keys_user_id", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_id = Column(String, unique=True, nullable=False)
    secret_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False, nullable=False)

    # Relationship
    user = relationship("User", back_populates="api_keys")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        from datetime import datetime, timezone

        # Handle both timezone-aware and timezone-naive datetimes
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at

        # If expires_at is timezone-naive, assume it's UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return now > expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (not revoked and not expired)."""
        return not self.revoked and not self.is_expired()
