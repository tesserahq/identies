from sqlalchemy import Column
from datetime import datetime, timezone
from app.models.types import UTCNaiveDateTime


class TimestampMixin:
    created_at = Column(
        UTCNaiveDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        UTCNaiveDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin to add soft delete functionality to models using deleted_at timestamp."""

    deleted_at = Column(UTCNaiveDateTime(), nullable=True, index=True)
