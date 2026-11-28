"""Reading, importing and editing the working design model (ARCH-003)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import layout_service
from .access import authorize_project
from .db import ActivityEvent, DesignModel, LayoutProposal, User
from .design_model import apply_operations, from_layout_alternative
from .versioned_documents import write_document


class DesignServiceError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _row(session: Session, project_id: uuid.UUID) -> DesignModel | None:
    return session.scalar(
        select(DesignModel)
        .where(DesignModel.project_id == project_id)
        .execution_options(populate_existing=True)
    )


def _layout_row(session: Session, project_id: uuid.UUID) -> LayoutProposal | None:
    return session.scalar(select(LayoutProposal).where(LayoutProposal.project_id == project_id))


def design_payload(row: DesignModel | None, layout: LayoutProposal | None) -> dict:
    if row is None:
        return {"exists": False, "data": None, "version": 0, "layout_changed": False,
                "updated_at": None}
    source = row.data.get("source") or {}
    changed = bool(source) and (layout is None or layout.version != source.get("layout_version"))
    return {
        "exists": True,
        "data": row.data,
        "version": row.version,
        "layout_changed": changed,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_design(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    return design_payload(_row(session, project_id), _layout_row(session, project_id))


def import_layout(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    *,
    alternative_id: str,
    expected_version: int,
    replace: bool,
) -> dict:
    authorize_project(session, actor, project_id, "project.design.edit")
    layout = _layout_row(session, project_id)
    if layout is None or layout.data.get("status") != "alternatives":
        raise DesignServiceError("no_layout")
    if layout_service.get_layouts(session, actor, project_id)["stale"]:
        raise DesignServiceError("layout_stale")
    alternative = next(
        (a for a in layout.data["alternatives"] if a["id"] == alternative_id), None
    )
    if alternative is None:
        raise DesignServiceError("alternative_not_found")
    existing = _row(session, project_id)
    if existing is not None and existing.data.get("elements") and not replace:
        raise DesignServiceError("design_exists")
    model = from_layout_alternative(
        alternative,
        {
            "kind": "layout",
            "layout_version": layout.version,
            "alternative_id": alternative["id"],
            "strategy": alternative["strategy"],
        },
    )
    row = write_document(
        session,
        DesignModel,
        {"project_id": project_id},
        data=model,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: DesignServiceError("version_conflict"),
    )
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.design_imported",
            detail={"alternative": alternative["id"], "elements": len(model["elements"])},
        )
    )
    session.commit()
    session.refresh(row)
    return design_payload(row, layout)


def edit_design(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    *,
    operations: list,
    expected_version: int,
) -> dict:
    authorize_project(session, actor, project_id, "project.design.edit")
    current = _row(session, project_id)
    if current is None:
        raise DesignServiceError("no_design")
    if current.version != expected_version:
        raise DesignServiceError("version_conflict")
    model = apply_operations(current.data, operations)  # DesignError leaves nothing written
    row = write_document(
        session,
        DesignModel,
        {"project_id": project_id},
        data=model,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: DesignServiceError("version_conflict"),
    )
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.design_edited",
            detail={"operations": len(operations), "elements": len(model["elements"])},
        )
    )
    session.commit()
    session.refresh(row)
    return design_payload(row, _layout_row(session, project_id))
