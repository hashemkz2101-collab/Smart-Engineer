"""Atomic writes for the five versioned project documents.

The caller adds its audit event and commits. A failed compare-and-swap rolls back
before raising the caller's domain error; rejected saves leave no audit event.
"""

import uuid
from collections.abc import Callable

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def write_document(
    session: Session,
    model: type,
    keys: dict,
    *,
    data: dict,
    actor_id: uuid.UUID,
    expected_version: int,
    conflict: Callable[[], Exception],
    complete: bool | None = None,
):
    predicates = [getattr(model, name) == value for name, value in keys.items()]
    values = {"data": data, "updated_by_user_id": actor_id}
    if complete is not None:
        values["complete"] = complete
    if expected_version == 0:
        row = model(**keys, **values, version=1)
        try:
            session.add(row)
            session.flush()
        except IntegrityError:
            session.rollback()
            # Only translate a duplicate document, not unrelated FK/CHECK errors.
            if session.scalar(select(model.id).where(*predicates)) is not None:
                raise conflict() from None
            raise
        return row
    if expected_version < 0:
        raise conflict()
    with session.no_autoflush:
        result = session.execute(
            update(model)
            .where(*predicates, model.version == expected_version)
            .values(**values, version=model.version + 1)
            .execution_options(synchronize_session=False)
        )
    if result.rowcount != 1:
        session.rollback()
        raise conflict()
    return session.scalar(
        select(model).where(*predicates).execution_options(populate_existing=True)
    )
