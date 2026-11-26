"""Isolated shared-memory SQLite for new tests, including API worker threads."""

import uuid

from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool


def memory_engine():
    engine = create_engine(
        f"sqlite:///file:geometry-{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False}, poolclass=QueuePool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    return engine
