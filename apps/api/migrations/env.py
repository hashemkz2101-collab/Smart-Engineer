"""Alembic environment.

The URL is taken from the Alembic ``sqlalchemy.url`` option when set (used by
tests) and otherwise from ``SMART_ENGINEER_DATABASE_URL``. The URL is never
printed because it may contain credentials.
"""

from alembic import context
from sqlalchemy import create_engine, pool

from smart_engineer_api.config import Settings
from smart_engineer_api.db import Base

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


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
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
