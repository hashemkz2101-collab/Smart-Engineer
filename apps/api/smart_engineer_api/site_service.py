"""Saving and reading project site / land data (SITE-001, SITE-002).

Same rules as the intake steps: a section is saved whole, invalid fields reject
the save with a reason per field path and nothing is written, and optimistic
``expected_version`` stops silent overwrites.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, SiteSection, User
from .roles import SITE_SECTIONS
from .site_schema import (
    SCHEMA,
    derive_parcel,
    missing_required,
    not_provided,
    validate_section,
)


class SiteError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SiteValidationError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("invalid_site")
        self.errors = errors


def section_payload(section: str, row: SiteSection | None) -> dict:
    data = row.data if row else {}
    payload = {
        "section": section,
        "data": data,
        "complete": bool(row.complete) if row else False,
        "missing": missing_required(section, data),
        "not_provided": not_provided(section, data),
        "version": row.version if row else 0,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }
    if section == "parcel":
        payload["derived"] = derive_parcel(data)
    return payload


def get_site(session: Session, actor: User, project_id: uuid.UUID) -> list[dict]:
    authorize_project(session, actor, project_id, "project.view")
    rows = {
        row.section_key: row
        for row in session.scalars(select(SiteSection).where(SiteSection.project_id == project_id))
    }
    return [section_payload(section, rows.get(section)) for section in SITE_SECTIONS]


def save_section(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    section: str,
    data: dict,
    expected_version: int,
) -> dict:
    authorize_project(session, actor, project_id, "project.site.edit")
    if section not in SCHEMA:
        raise SiteError("unknown_section")
    cleaned, errors = validate_section(section, data)
    if errors:
        raise SiteValidationError(errors)

    row = session.scalar(
        select(SiteSection).where(
            SiteSection.project_id == project_id, SiteSection.section_key == section
        )
    )
    if expected_version != (row.version if row else 0):
        raise SiteError("version_conflict")

    complete = not missing_required(section, cleaned)
    if row is None:
        row = SiteSection(
            project_id=project_id,
            section_key=section,
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
            action="project.site_saved",
            detail={"section": section, "complete": complete},
        )
    )
    session.commit()
    session.refresh(row)
    return section_payload(section, row)
