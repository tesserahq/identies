from app.models.mixins import SoftDeleteMixin, TimestampMixin
from sqlalchemy import (
    CheckConstraint,
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

import uuid

from app.constants.user_kinds import UserKind
from app.db import Base

NON_INTERACTIVE_KINDS = (UserKind.AGENT.value, UserKind.SERVICE_ACCOUNT.value)


class User(Base, TimestampMixin, SoftDeleteMixin):
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
            postgresql_where=text("external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        # Partial so a soft-deleted user does not block re-creating the same email.
        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "kind IN ('human', 'agent', 'service_account')", name="ck_users_kind"
        ),
        Index("idx_users_offboarding_scheduled_at", "offboarding_scheduled_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
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
    kind = Column(String(20), nullable=False)
    # Legacy physical column behind the computed ``service_account`` property below.
    # It is only written from kind (never read for behaviour) and is kept for one
    # release so a rolling deploy does not break; the column is dropped in #171.
    legacy_service_account = Column("service_account", Boolean, default=False)

    # Offboarding: set when an admin schedules a user for removal. Execution
    # (soft delete + IdP removal + user.deleted event) is handled by a
    # separate background job once offboarding_scheduled_at elapses.
    offboarding_scheduled_at = Column(DateTime, nullable=True)
    offboarding_scheduled_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    deleted_event_published_at = Column(DateTime, nullable=True)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user")
    external_accounts = relationship("ExternalAccount", back_populates="user")

    def __init__(self, **kwargs):
        # kind is required in the database. Callers that predate it only pass the
        # service_account flag, so derive kind from it instead of letting the insert
        # fail. An explicit kind always wins.
        flag = kwargs.pop("service_account", None)
        if kwargs.get("kind") is None:
            kwargs["kind"] = UserKind.SERVICE_ACCOUNT if flag else UserKind.HUMAN
        kwargs["kind"] = UserKind(kwargs["kind"]).value
        kwargs["legacy_service_account"] = kwargs["kind"] in NON_INTERACTIVE_KINDS
        super().__init__(**kwargs)

    @hybrid_property
    def service_account(self) -> bool:
        """True for non-interactive principals (agents and service accounts).

        Computed from ``kind`` so the two can never disagree. Prefer ``kind`` in new code.
        """
        return self.kind in NON_INTERACTIVE_KINDS

    @service_account.expression
    def service_account(cls):
        return cls.kind.in_(NON_INTERACTIVE_KINDS)

    def full_name(self) -> str:
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}"
