"""Link token model for external account linking flow."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db import Base
from app.models.mixins import TimestampMixin


class LinkToken(Base, TimestampMixin):
    """
    Short-lived, single-use token for linking an external platform account
    to the current user. Bound to platform + external_id + optional data.
    """

    __tablename__ = "link_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, nullable=False, index=True)
    platform = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    data = Column(JSONB, nullable=False, default=dict)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    def __init__(self, **kwargs):
        if kwargs.get("data") is None:
            kwargs["data"] = {}
        super().__init__(**kwargs)
