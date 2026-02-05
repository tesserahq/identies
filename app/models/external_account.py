from app.models.mixins import TimestampMixin
from sqlalchemy import Column, String, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

import uuid

from app.db import Base


class ExternalAccount(Base, TimestampMixin):
    """User model for the application.
    This model represents a user in the system and includes fields for
    personal information, authentication, and relationships with other models.
    """

    __tablename__ = "external_accounts"

    __table_args__ = (
        Index(
            "uq_external_accounts_external_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)

    # Relationships
    user = relationship("User", back_populates="external_accounts")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
