"""Saving and reading zoning / building-control inputs (RULE-DATA-001)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, User, ZoningRecord
from .roles import ZONING_FIELDS
from .zoning_schema import VALUE_FIELDS, derive_status, validate_record


class ZoningError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ZoningValidationError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("invalid_zoning")
        self.errors = errors


def record_payload(field: str, row: ZoningRecord | None) -> dict:
    data = row.data if row else {}
    return {
        "field": field,
        "data": data,
        **derive_status(field, data),
        "version": row.version if row else 0,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


def get_zoning(session: Session, actor: User, project_id: uuid.UUID) -> list[dict]:
    authorize_project(session, actor, project_id, "project.view")
    query = select(ZoningRecord).where(ZoningRecord.project_id == project_id)
    rows = {row.field_key: row for row in session.scalars(query)}
    return [record_payload(field, rows.get(field)) for field in ZONING_FIELDS]


def save_record(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    field: str,
    data: dict,
    expected_version: int,
) -> dict:
    authorize_project(session, actor, project_id, "project.zoning.edit")
    if field not in VALUE_FIELDS:
        raise ZoningError("unknown_field")
    cleaned, errors = validate_record(field, data)
    if errors:
        raise ZoningValidationError(errors)

    row = session.scalar(
        select(ZoningRecord).where(
            ZoningRecord.project_id == project_id, ZoningRecord.field_key == field
        )
    )
    if expected_version != (row.version if row else 0):
        raise ZoningError("version_conflict")

    if row is None:
        row = ZoningRecord(
            project_id=project_id,
            field_key=field,
            data=cleaned,
            version=1,
            updated_by_user_id=actor.id,
        )
        session.add(row)
    else:
        row.data = cleaned
        row.version += 1
        row.updated_by_user_id = actor.id
    status = derive_status(field, cleaned)["status"]
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.zoning_saved",
            detail={"field": field, "status": status},
        )
    )
    session.commit()
    session.refresh(row)
    return record_payload(field, row)
