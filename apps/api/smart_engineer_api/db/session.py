"""Engine and session helpers. Nothing connects until an engine is used."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str, **engine_options) -> Engine:
    if database_url.startswith("mysql"):
        # Persian text needs utf8mb4; MySQL's own "utf8" is only three bytes per character.
        engine_options.setdefault("connect_args", {}).setdefault("charset", "utf8mb4")
    engine = create_engine(database_url, pool_pre_ping=True, **engine_options)
    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys unless asked; PostgreSQL and MySQL always enforce them.
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    elif engine.dialect.name == "mysql":
        # Same behavior on MySQL and MariaDB regardless of the server's defaults: every
        # timestamp in UTC, strict value checking (no silent truncation), InnoDB tables.
        @event.listens_for(engine, "connect")
        def _configure_mysql_session(dbapi_connection, _record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET time_zone = '+00:00'")
            cursor.execute("SET SESSION sql_mode = CONCAT(@@sql_mode, ',STRICT_ALL_TABLES')")
            cursor.execute("SET SESSION default_storage_engine = InnoDB")
            cursor.close()

        @event.listens_for(engine, "handle_error")
        def _check_violations_are_integrity_errors(context):
            # PostgreSQL and SQLite report a failed CHECK as an integrity error; MySQL
            # (3819) and MariaDB (4025) use a generic code. Make them the same so callers
            # and tests do not care which database is behind the engine.
            args = getattr(context.original_exception, "args", ())
            if args and args[0] in (3819, 4025):
                return IntegrityError(
                    context.statement, context.parameters, context.original_exception
                )
            return None

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
