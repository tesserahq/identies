"""SQLAlchemy types for timestamps stored without a database timezone."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCNaiveDateTime(TypeDecorator[datetime]):
    """Store aware timestamps as UTC in a timezone-naive column.

    PostgreSQL otherwise interprets an aware value according to the connection
    timezone when it is written to ``TIMESTAMP WITHOUT TIME ZONE``.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
