"""Reading, importing and editing the working design model (ARCH-003)."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import layout_service
from .access import authorize_project
from .db import ActivityEvent, DesignHistory, DesignModel, LayoutProposal, User
from .design_model import apply_operations, from_layout_alternative
from .versioned_documents import write_document

HISTORY_LIMIT = 200  # entries kept per project; older states can no longer be undone


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


def _bounds(session: Session, project_id: uuid.UUID) -> tuple[int, int]:
    low, high = session.execute(
        select(func.min(DesignHistory.seq), func.max(DesignHistory.seq)).where(
            DesignHistory.project_id == project_id
        )
    ).one()
    return (low or 0, high or 0)


def design_payload(
    session: Session, row: DesignModel | None, layout: LayoutProposal | None
) -> dict:
    if row is None:
        return {"exists": False, "data": None, "version": 0, "layout_changed": False,
                "can_undo": False, "can_redo": False, "history_position": 0,
                "history_length": 0, "updated_at": None}
    source = row.data.get("source") or {}
    changed = bool(source) and (layout is None or layout.version != source.get("layout_version"))
    low, high = _bounds(session, row.project_id)
    return {
        "exists": True,
        "data": row.data,
        "version": row.version,
        "layout_changed": changed,
        "can_undo": row.head_seq > low > 0,
        "can_redo": 0 < row.head_seq < high,
        "history_position": row.head_seq,
        "history_length": high,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _baseline(session: Session, row: DesignModel) -> None:
    """Designs saved before history existed get their current state as entry 1."""
    if row.head_seq == 0:
        session.add(
            DesignHistory(
                project_id=row.project_id,
                seq=1,
                data=row.data,
                summary={"action": "baseline"},
                actor_user_id=row.updated_by_user_id,
            )
        )
        row.head_seq = 1
        session.flush()


def _record(
    session: Session, row: DesignModel, model: dict, summary: dict, actor: User
) -> None:
    """Append a state after the current head, dropping any redo side, then prune."""
    head = row.head_seq
    session.execute(
        delete(DesignHistory).where(
            DesignHistory.project_id == row.project_id, DesignHistory.seq > head
        )
    )
    session.add(DesignHistory(project_id=row.project_id, seq=head + 1, data=model,
                              summary=summary, actor_user_id=actor.id))
    row.head_seq = head + 1
    session.execute(
        delete(DesignHistory).where(
            DesignHistory.project_id == row.project_id,
            DesignHistory.seq <= head + 1 - HISTORY_LIMIT,
        )
    )
    session.flush()


def get_design(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    return design_payload(session, _row(session, project_id), _layout_row(session, project_id))


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
    if existing is not None:
        _baseline(session, existing)
    row = write_document(
        session,
        DesignModel,
        {"project_id": project_id},
        data=model,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: DesignServiceError("version_conflict"),
    )
    _record(session, row, model, {"action": "import", "alternative_id": alternative["id"]}, actor)
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
    return design_payload(session, row, layout)


def edit_design(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    *,
    operations: list,
    expected_version: int,
    unit: str = "m",
    snap: dict | None = None,
) -> dict:
    authorize_project(session, actor, project_id, "project.design.edit")
    current = _row(session, project_id)
    if current is None:
        raise DesignServiceError("no_design")
    if current.version != expected_version:
        raise DesignServiceError("version_conflict")
    # DesignError leaves nothing written (validated before any change is flushed).
    model = apply_operations(current.data, operations, unit=unit, snap=snap)
    _baseline(session, current)
    row = write_document(
        session,
        DesignModel,
        {"project_id": project_id},
        data=model,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: DesignServiceError("version_conflict"),
    )
    summary = {
        "action": "edit",
        "operations": [
            {"op": op.get("op"), "id": op.get("id")} for op in operations if isinstance(op, dict)
        ],
        "unit": unit,
        "snap": snap,
    }
    _record(session, row, model, summary, actor)
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
    return design_payload(session, row, _layout_row(session, project_id))


def _step(
    session: Session, actor: User, project_id: uuid.UUID, expected_version: int, direction: int
) -> dict:
    authorize_project(session, actor, project_id, "project.design.edit")
    current = _row(session, project_id)
    if current is None:
        raise DesignServiceError("no_design")
    if current.version != expected_version:
        raise DesignServiceError("version_conflict")
    _baseline(session, current)
    target = session.scalar(
        select(DesignHistory).where(
            DesignHistory.project_id == project_id,
            DesignHistory.seq == current.head_seq + direction,
        )
    )
    if target is None:
        raise DesignServiceError("nothing_to_undo" if direction < 0 else "nothing_to_redo")
    seq, data = target.seq, target.data
    row = write_document(
        session,
        DesignModel,
        {"project_id": project_id},
        data=data,
        actor_id=actor.id,
        expected_version=expected_version,
        conflict=lambda: DesignServiceError("version_conflict"),
    )
    row.head_seq = seq
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.design_undone" if direction < 0 else "project.design_redone",
            detail={"position": seq},
        )
    )
    session.commit()
    session.refresh(row)
    return design_payload(session, row, _layout_row(session, project_id))


def undo_design(
    session: Session, actor: User, project_id: uuid.UUID, *, expected_version: int
) -> dict:
    return _step(session, actor, project_id, expected_version, -1)


def redo_design(
    session: Session, actor: User, project_id: uuid.UUID, *, expected_version: int
) -> dict:
    return _step(session, actor, project_id, expected_version, +1)


def design_history(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    row = _row(session, project_id)
    head = row.head_seq if row else 0
    entries = session.execute(
        select(DesignHistory, User.display_name)
        .join(User, User.id == DesignHistory.actor_user_id)
        .where(DesignHistory.project_id == project_id)
        .order_by(DesignHistory.seq.desc())
        .limit(50)
    ).all()
    return {
        "position": head,
        "entries": [
            {
                "seq": entry.seq,
                "summary": entry.summary,
                "actor": name,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "current": entry.seq == head,
            }
            for entry, name in entries
        ],
    }
