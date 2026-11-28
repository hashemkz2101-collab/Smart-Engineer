"""Reading and generating conceptual layout alternatives (ARCH-002).

Inputs are read from their single sources of truth: the parcel/access site sections, the
zoning setback and coverage records (through the geometry report) and the persisted
space schedule. The stored result lists the version of each, so a later change marks
it stale instead of silently disagreeing with its inputs.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import geometry_service
from .access import authorize_project
from .db import ActivityEvent, LayoutProposal, RequirementSection, SpaceSchedule, User
from .geometry import GeometryError, boundary
from .layout import generate_alternatives, infeasible
from .versioned_documents import write_document


class LayoutError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _inputs(session: Session, project_id: uuid.UUID) -> dict:
    site, zoning = geometry_service._records(session, project_id)
    parcel = site["parcel"].data if "parcel" in site else {}
    report = geometry_service._report(parcel, site, zoning)
    schedule = session.scalar(
        select(SpaceSchedule)
        .where(SpaceSchedule.project_id == project_id)
        .execution_options(populate_existing=True)
    )
    program = session.scalar(
        select(RequirementSection)
        .where(
            RequirementSection.project_id == project_id,
            RequirementSection.section_key == "program",
        )
        .execution_options(populate_existing=True)
    )
    versions = dict(report["source_versions"])
    versions["space_schedule"] = schedule.version if schedule else 0
    return {
        "parcel": parcel,
        "report": report,
        "schedule": schedule,
        "program": program,
        "versions": versions,
    }


def _front_segments(parcel: dict) -> list[tuple]:
    try:
        points = boundary(parcel)
    except GeometryError:
        return []
    mapping = parcel.get("setback_edges")
    if not isinstance(mapping, list):
        return []
    segments = []
    for item in mapping:
        if not isinstance(item, dict) or item.get("role") != "front":
            continue
        index = item.get("edge_index")
        if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(points):
            segments.append((points[index], points[(index + 1) % len(points)]))
    return segments


def _compute(inputs: dict) -> dict:
    report, schedule, program = inputs["report"], inputs["schedule"], inputs["program"]
    envelope = report.get("envelope")
    if envelope is None:
        return infeasible(["parcel_invalid_or_missing"])
    if schedule is None:
        return infeasible(["space_schedule_missing"])
    source = schedule.data.get("source", {})
    if source.get("program_version") != (program.version if program else 0):
        return infeasible(["space_schedule_stale"])
    floors = source.get("floors_count", 1)
    return generate_alternatives(
        envelope, schedule.data.get("spaces", []), floors, _front_segments(inputs["parcel"])
    )


def layout_payload(row: LayoutProposal | None, inputs: dict) -> dict:
    current = inputs["versions"]
    if row is None:
        return {"exists": False, "data": None, "version": 0, "stale": False,
                "current_sources": current, "updated_at": None}
    stored = row.data.get("sources", {}).get("versions", {})
    return {
        "exists": True,
        "data": row.data,
        "version": row.version,
        "stale": stored != current,
        "current_sources": current,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_layouts(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    row = session.scalar(select(LayoutProposal).where(LayoutProposal.project_id == project_id))
    return layout_payload(row, _inputs(session, project_id))


def generate_layouts(
    session: Session, actor: User, project_id: uuid.UUID, expected_version: int
) -> dict:
    authorize_project(session, actor, project_id, "project.requirements.edit")
    inputs = _inputs(session, project_id)
    result = _compute(inputs)
    envelope = inputs["report"].get("envelope") or {}
    if envelope.get("polygons"):
        result["envelope_polygons"] = [
            {"exterior": piece["exterior"], "holes": piece["holes"]}
            for piece in envelope["polygons"]
        ]
    result["sources"] = {
        "versions": inputs["versions"],
        "parcel_input_hash": inputs["report"].get("input_hash"),
        "envelope_as_of": (inputs["report"].get("envelope") or {}).get("as_of"),
    }
    row = write_document(
        session,
        LayoutProposal,
        {"project_id": project_id},
        data=result,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: LayoutError("version_conflict"),
    )
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.layouts_generated",
            detail={"status": result["status"], "alternatives": len(result["alternatives"])},
        )
    )
    session.commit()
    session.refresh(row)
    return layout_payload(row, inputs)
