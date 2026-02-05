from app.models.mixins import SoftDeleteMixin, TimestampMixin
from sqlalchemy import Column, String, Index
from sqlalchemy.dialects.postgresql import UUID

import uuid

from app.db import Base


class AccessRule(Base, TimestampMixin, SoftDeleteMixin):
    """User model for the application.
    This model represents a user in the system and includes fields for
    personal information, authentication, and relationships with other models.
    """

    __tablename__ = "access_rules"

    __table_args__ = (
        Index(
            "uq_access_rules_kind_value",
            "kind",
            "value",
            unique=True,
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String, nullable=False)
    value = Column(String, nullable=False)
    note = Column(String, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
