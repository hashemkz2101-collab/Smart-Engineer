"""Saving and reading project intake steps (INP-001, INP-002).

Any subset of a step's fields can be saved. Invalid fields are rejected with a
reason per field and nothing is written; previously saved data stays untouched.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, IntakeStep, User
from .intake_schema import SCHEMA, missing_required, validate_step
from .roles import INTAKE_STEPS


class IntakeError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class IntakeValidationError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("invalid_intake")
        self.errors = errors


def step_payload(step: str, row: IntakeStep | None) -> dict:
    data = row.data if row else {}
    return {
        "step": step,
        "data": data,
        "complete": bool(row.complete) if row else False,
        "missing": missing_required(step, data),
        "version": row.version if row else 0,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


def get_intake(session: Session, actor: User, project_id: uuid.UUID) -> list[dict]:
    authorize_project(session, actor, project_id, "project.view")
    rows = {
        row.step_key: row
        for row in session.scalars(select(IntakeStep).where(IntakeStep.project_id == project_id))
    }
    return [step_payload(step, rows.get(step)) for step in INTAKE_STEPS]


def save_step(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    step: str,
    data: dict,
    expected_version: int,
) -> dict:
    authorize_project(session, actor, project_id, "project.intake.edit")
    if step not in SCHEMA:
        raise IntakeError("unknown_step")
    cleaned, errors = validate_step(step, data)
    if errors:
        raise IntakeValidationError(errors)

    row = session.scalar(
        select(IntakeStep).where(
            IntakeStep.project_id == project_id, IntakeStep.step_key == step
        )
    )
    if expected_version != (row.version if row else 0):
        raise IntakeError("version_conflict")

    complete = not missing_required(step, cleaned)
    if row is None:
        row = IntakeStep(
            project_id=project_id,
            step_key=step,
            data=cleaned,
            complete=complete,
            version=1,
            updated_by_user_id=actor.id,
        )
        session.add(row)
    else:
        row.data = cleaned
        row.complete = complete
        row.version += 1
        row.updated_by_user_id = actor.id
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.intake_saved",
            detail={"step": step, "complete": complete},
        )
    )
    session.commit()
    session.refresh(row)
    return step_payload(step, row)
