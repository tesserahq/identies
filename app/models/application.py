"""Application model."""

import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Application(Base, TimestampMixin, SoftDeleteMixin):
    """Application model.

    Represents an application in the system with name, url, logo, and description.
    """

    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    url = Column(String, nullable=True)
    logo = Column(String, nullable=True)
    description = Column(String, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
