"""Column types that behave the same on PostgreSQL, MySQL/MariaDB and SQLite.

Time policy: every timestamp is stored in UTC and read back as a timezone-aware UTC
``datetime``. PostgreSQL has a native ``timestamptz``; MySQL and SQLite do not, so this
type converts on the way in and attaches UTC on the way out.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        # A naive value is taken to be UTC already (the application only creates UTC).
        aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return aware if dialect.name == "postgresql" else aware.replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
