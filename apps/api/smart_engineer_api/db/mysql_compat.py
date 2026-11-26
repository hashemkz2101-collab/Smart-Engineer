"""MySQL/MariaDB compilation rules shared by the models and every migration.

Imported by ``smart_engineer_api.db`` so that Alembic (which imports it too) and the
application emit the same DDL. PostgreSQL and SQLite output is not affected.
"""

from sqlalchemy import DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions


@compiles(DateTime, "mysql")
def _datetime_with_microseconds(type_, compiler, **kw) -> str:  # noqa: ANN001, ARG001
    # Plain MySQL DATETIME keeps whole seconds and rounds the rest, which would make
    # token expiry and event ordering differ from PostgreSQL.
    return "DATETIME(6)"


@compiles(functions.now, "mysql")
def _now_with_microseconds(element, compiler, **kw) -> str:  # noqa: ANN001, ARG001
    # Must match the DATETIME(6) precision of the column it defaults.
    return "CURRENT_TIMESTAMP(6)"
