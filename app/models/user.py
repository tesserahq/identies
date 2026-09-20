from app.models.mixins import TimestampMixin
from sqlalchemy import CheckConstraint, Column, String, Boolean, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

import uuid

from app.constants.user_kinds import UserKind
from app.db import Base


class User(Base, TimestampMixin):
    """User model for the application.
    This model represents a user in the system and includes fields for
    personal information, authentication, and relationships with other models.
    """

    __tablename__ = "users"

    __table_args__ = (
        Index(
            "uq_users_external_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        CheckConstraint(
            "kind IN ('human', 'agent', 'service_account')", name="ck_users_kind"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    avatar_asset_id = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    preferred_name = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    external_id = Column(String, nullable=True)
    theme_preference = Column(String, default="system", nullable=True)
    # Kept for compatibility; prefer kind. Existing checks (e.g. /me, user lists) still read it.
    service_account = Column(Boolean, default=False)
    kind = Column(String(20), nullable=False)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user")
    external_accounts = relationship("ExternalAccount", back_populates="user")

    def __init__(self, **kwargs):
        # kind is required in the database. Callers that predate it only set the
        # service_account flag, so derive it instead of letting the insert fail.
        if kwargs.get("kind") is None:
            kwargs["kind"] = (
                UserKind.SERVICE_ACCOUNT
                if kwargs.get("service_account")
                else UserKind.HUMAN
            )
        kwargs["kind"] = UserKind(kwargs["kind"]).value
        super().__init__(**kwargs)

    def full_name(self) -> str:
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}"
