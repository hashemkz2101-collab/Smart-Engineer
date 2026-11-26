"""Saving and reading client requirements (REQ-001, REQ-002, REQ-003).

Same rules as the intake steps: a section is saved whole, invalid fields reject
the save with a reason per field path and nothing is written, and optimistic
``expected_version`` stops silent overwrites.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, RequirementSection, User
from .requirements_schema import SCHEMA, missing_required, not_provided, validate_section
from .roles import REQUIREMENT_SECTIONS
from .versioned_documents import write_document


class RequirementsError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RequirementsValidationError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("invalid_requirements")
        self.errors = errors


def section_payload(section: str, row: RequirementSection | None) -> dict:
    data = row.data if row else {}
    return {
        "section": section,
        "data": data,
        "complete": bool(row.complete) if row else False,
        "missing": missing_required(section, data),
        "not_provided": not_provided(section, data),
        "version": row.version if row else 0,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


def get_requirements(session: Session, actor: User, project_id: uuid.UUID) -> list[dict]:
    authorize_project(session, actor, project_id, "project.view")
    query = select(RequirementSection).where(RequirementSection.project_id == project_id)
    rows = {row.section_key: row for row in session.scalars(query)}
    return [section_payload(section, rows.get(section)) for section in REQUIREMENT_SECTIONS]


def save_section(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    section: str,
    data: dict,
    expected_version: int,
) -> dict:
    authorize_project(session, actor, project_id, "project.requirements.edit")
    if section not in SCHEMA:
        raise RequirementsError("unknown_section")
    cleaned, errors = validate_section(section, data)
    if errors:
        raise RequirementsValidationError(errors)

    complete = not missing_required(section, cleaned)
    row = write_document(
        session, RequirementSection, {"project_id": project_id, "section_key": section},
        data=cleaned, actor_id=actor.id, expected_version=expected_version,
        complete=complete, conflict=lambda: RequirementsError("version_conflict"),
    )
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.requirements_saved",
            detail={"section": section, "complete": complete},
        )
    )
    session.commit()
    session.refresh(row)
    return section_payload(section, row)
