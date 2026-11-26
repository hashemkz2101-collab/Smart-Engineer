"""Reading and generating the space schedule (ARCH-001)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, RequirementSection, SpaceSchedule, User
from .space_schedule import build_schedule
from .versioned_documents import write_document


class ScheduleError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _program_row(session: Session, project_id: uuid.UUID) -> RequirementSection | None:
    return session.scalar(
        select(RequirementSection).where(
            RequirementSection.project_id == project_id,
            RequirementSection.section_key == "program",
        )
    )


def schedule_payload(row: SpaceSchedule | None, program: RequirementSection | None) -> dict:
    program_version = program.version if program else 0
    if row is None:
        return {
            "exists": False,
            "data": None,
            "version": 0,
            "stale": False,
            "program_version": program_version,
            "program_ready": bool(program and program.complete),
            "updated_at": None,
        }
    return {
        "exists": True,
        "data": row.data,
        "version": row.version,
        "stale": row.data.get("source", {}).get("program_version") != program_version,
        "program_version": program_version,
        "program_ready": bool(program and program.complete),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_schedule(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    row = session.scalar(select(SpaceSchedule).where(SpaceSchedule.project_id == project_id))
    return schedule_payload(row, _program_row(session, project_id))


def generate_schedule(
    session: Session, actor: User, project_id: uuid.UUID, expected_version: int
) -> dict:
    authorize_project(session, actor, project_id, "project.requirements.edit")
    program = _program_row(session, project_id)
    if program is None or not program.complete:
        raise ScheduleError("program_incomplete")
    data = build_schedule(program.data, program.version)
    row = write_document(
        session,
        SpaceSchedule,
        {"project_id": project_id},
        data=data,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: ScheduleError("version_conflict"),
    )
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.space_schedule_generated",
            detail={
                "spaces": data["totals"]["spaces"],
                "flags": len(data["flags"]),
                "program_version": program.version,
            },
        )
    )
    session.commit()
    session.refresh(row)
    return schedule_payload(row, program)
