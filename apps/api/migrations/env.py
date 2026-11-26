"""Alembic environment.

The URL is taken from the Alembic ``sqlalchemy.url`` option when set (used by
tests) and otherwise from ``SMART_ENGINEER_DATABASE_URL``. The URL is never
printed because it may contain credentials.
"""

from alembic import context
from sqlalchemy import pool, text

from smart_engineer_api.config import Settings
from smart_engineer_api.db import Base
from smart_engineer_api.db.session import create_db_engine

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    url = config.get_main_option("sqlalchemy.url") or Settings.from_env().database_url
    if not url:
        raise RuntimeError(
            "No database URL: set SMART_ENGINEER_DATABASE_URL to run migrations."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _use_binary_collation(connection) -> None:
    """MySQL compares text case-insensitively by default, PostgreSQL does not.

    New tables inherit the database default, so make it binary (case-sensitive) before any
    table is created. This keeps unique keys, the lowercase-email check and token lookups
    identical on both engines. If the account may not alter the database, say so instead
    of failing the migration.
    """
    name = connection.execute(text("SELECT DATABASE()")).scalar()
    connection.commit()  # end the implicit transaction so Alembic starts its own
    if not name or "`" in name:
        return
    try:
        connection.execute(
            text(f"ALTER DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        )
    except Exception:  # noqa: BLE001 - only the type is reported; the message may hold secrets
        print(
            "Warning: could not set the database collation to utf8mb4_bin. Create the "
            "database with that collation or text comparisons will ignore case."
        )
    connection.commit()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            if connection.dialect.name == "mysql":
                _use_binary_collation(connection)
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
