"""Saved design versions, comparison and comments (ARCH-006)."""

import copy
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, DesignComment, DesignModel, DesignVersion, User
from .design_compare import compare_models
from .design_service import DesignServiceError

MAX_VERSIONS = 200
MAX_COMMENTS_PER_VERSION = 500
MAX_COMMENT_LENGTH = 2000


def _model_row(session: Session, project_id: uuid.UUID) -> DesignModel | None:
    return session.scalar(
        select(DesignModel)
        .where(DesignModel.project_id == project_id)
        .execution_options(populate_existing=True)
    )


def _version(session: Session, project_id: uuid.UUID, number: int) -> DesignVersion:
    row = session.scalar(
        select(DesignVersion).where(
            DesignVersion.project_id == project_id, DesignVersion.number == number
        )
    )
    if row is None:
        raise DesignServiceError("unknown_version")
    return row


def _names(session: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = session.execute(select(User.id, User.display_name).where(User.id.in_(ids))).all()
    return {user_id: name for user_id, name in rows}


def _meta(row: DesignVersion, names: dict, comments: int = 0) -> dict:
    return {
        "number": row.number,
        "label": row.label,
        "model_version": row.model_version,
        "element_count": len(row.data.get("elements", [])),
        "author": names.get(row.created_by),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "comment_count": comments,
    }


def save_version(
    session: Session, actor: User, project_id: uuid.UUID, *, label: str, expected_version: int
) -> dict:
    authorize_project(session, actor, project_id, "project.design.edit")
    label = label.strip() if isinstance(label, str) else ""
    if not label or len(label) > 120:
        raise DesignServiceError("invalid_value")
    current = _model_row(session, project_id)
    if current is None or not current.data.get("elements"):
        raise DesignServiceError("no_design")
    if current.version != expected_version:
        raise DesignServiceError("version_conflict")
    top, count = session.execute(
        select(func.max(DesignVersion.number), func.count(DesignVersion.id)).where(
            DesignVersion.project_id == project_id
        )
    ).one()
    if count >= MAX_VERSIONS:
        raise DesignServiceError("too_many_versions")
    row = DesignVersion(
        project_id=project_id,
        number=(top or 0) + 1,
        label=label,
        data=copy.deepcopy(current.data),
        model_version=current.version,
        created_by=actor.id,
    )
    session.add(row)
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.design_version_saved",
            detail={"number": row.number, "label": label},
        )
    )
    session.commit()
    session.refresh(row)
    return _meta(row, {actor.id: actor.display_name})


def list_versions(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    rows = session.scalars(
        select(DesignVersion)
        .where(DesignVersion.project_id == project_id)
        .order_by(DesignVersion.number.desc())
    ).all()
    counts = dict(
        session.execute(
            select(DesignComment.version_id, func.count(DesignComment.id))
            .where(DesignComment.project_id == project_id)
            .group_by(DesignComment.version_id)
        ).all()
    )
    names = _names(session, {row.created_by for row in rows})
    return {"versions": [_meta(row, names, counts.get(row.id, 0)) for row in rows]}


def _comments(session: Session, row: DesignVersion) -> list[dict]:
    comments = session.scalars(
        select(DesignComment)
        .where(DesignComment.version_id == row.id)
        .order_by(DesignComment.created_at, DesignComment.id)
    ).all()
    names = _names(session, {c.author_user_id for c in comments})
    return [
        {
            "id": str(c.id),
            "element_id": c.element_id,
            "body": c.body,
            "author": names.get(c.author_user_id),
            "version_number": row.number,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]


def get_version(session: Session, actor: User, project_id: uuid.UUID, number: int) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    row = _version(session, project_id, number)
    comments = _comments(session, row)
    return {
        **_meta(row, _names(session, {row.created_by}), len(comments)),
        "data": row.data,
        "comments": comments,
    }


def _side(session: Session, project_id: uuid.UUID, ref: str) -> tuple[dict, dict]:
    if ref == "current":
        current = _model_row(session, project_id)
        if current is None:
            raise DesignServiceError("no_design")
        return current.data, {"number": None, "label": None, "model_version": current.version}
    try:
        number = int(ref)
    except (TypeError, ValueError):
        raise DesignServiceError("unknown_version") from None
    row = _version(session, project_id, number)
    return row.data, {"number": row.number, "label": row.label, "model_version": row.model_version}


def compare_versions(
    session: Session, actor: User, project_id: uuid.UUID, first: str, second: str
) -> dict:
    """Compare two saved versions, or a saved version with the working model (``current``)."""
    authorize_project(session, actor, project_id, "project.view")
    data_a, meta_a = _side(session, project_id, first)
    data_b, meta_b = _side(session, project_id, second)
    return {"from": meta_a, "to": meta_b, **compare_models(data_a, data_b)}


def add_comment(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    number: int,
    *,
    body: str,
    element_id: str | None = None,
) -> dict:
    authorize_project(session, actor, project_id, "project.design.comment")
    row = _version(session, project_id, number)
    body = body.strip() if isinstance(body, str) else ""
    if not body or len(body) > MAX_COMMENT_LENGTH:
        raise DesignServiceError("invalid_value")
    if element_id is not None and element_id not in {
        e["id"] for e in row.data.get("elements", [])
    }:
        raise DesignServiceError("unknown_element")
    existing = session.scalar(
        select(func.count(DesignComment.id)).where(DesignComment.version_id == row.id)
    )
    if existing >= MAX_COMMENTS_PER_VERSION:
        raise DesignServiceError("too_many_comments")
    comment = DesignComment(
        project_id=project_id,
        version_id=row.id,
        element_id=element_id,
        body=body,
        author_user_id=actor.id,
    )
    session.add(comment)
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.design_commented",
            detail={"version": row.number, "element_id": element_id},
        )
    )
    session.commit()
    session.refresh(comment)
    return {
        "id": str(comment.id),
        "element_id": element_id,
        "body": body,
        "author": actor.display_name,
        "version_number": row.number,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }
