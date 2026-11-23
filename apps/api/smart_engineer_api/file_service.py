"""Uploading, listing, downloading and deleting project files (FILE-001, SEC-002)."""

import hashlib
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import ActivityEvent, ProjectFile, User
from .file_policy import (
    CONTENT_TYPES,
    MAX_BYTES_BY_TYPE,
    MAX_FILES_PER_PROJECT,
    MAX_UPLOAD_BYTES,
    builtin_scan,
    classify,
    clean_filename,
    extension_matches,
)
from .file_storage import FileStorage
from .roles import FILE_KINDS


class FileError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def file_payload(row: ProjectFile, uploader_name: str | None) -> dict:
    return {
        "id": str(row.id),
        "original_name": row.original_name,
        "kind": row.kind,
        "document_date": row.document_date.isoformat() if row.document_date else None,
        "ownership": row.ownership,
        "detected_type": row.detected_type,
        "content_type": CONTENT_TYPES[row.detected_type],
        "size_bytes": row.size_bytes,
        "sha256": row.sha256,
        "scan_status": row.scan_status,
        "scan_detail": row.scan_detail,
        "uploaded_by_user_id": str(row.uploaded_by_user_id),
        "uploaded_by_name": uploader_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "downloadable": row.scan_status == "clean",
    }


def _live_files(project_id: uuid.UUID):
    return select(ProjectFile).where(
        ProjectFile.project_id == project_id, ProjectFile.deleted_at.is_(None)
    )


def list_files(session: Session, actor: User, project_id: uuid.UUID) -> list[dict]:
    authorize_project(session, actor, project_id, "project.view")
    rows = session.scalars(_live_files(project_id).order_by(ProjectFile.created_at.desc())).all()
    names = {
        user.id: user.display_name
        for user in session.scalars(
            select(User).where(User.id.in_({row.uploaded_by_user_id for row in rows}))
        )
    }
    return [file_payload(row, names.get(row.uploaded_by_user_id)) for row in rows]


def upload_file(
    session: Session,
    storage: FileStorage,
    actor: User,
    project_id: uuid.UUID,
    *,
    filename: str,
    kind: str,
    document_date: str | None,
    ownership: str | None,
    content: bytes,
    builtin_scan_is_authoritative: bool,
) -> dict:
    authorize_project(session, actor, project_id, "project.files.upload")
    if kind not in FILE_KINDS:
        raise FileError("invalid_kind")
    parsed_date: date | None = None
    if document_date:
        try:
            parsed_date = date.fromisoformat(document_date)
        except ValueError:
            raise FileError("invalid_date") from None
    ownership = (ownership or "").strip() or None
    if ownership is not None and len(ownership) > 200:
        raise FileError("invalid_ownership")
    name = clean_filename(filename)
    if name is None:
        raise FileError("invalid_file_name")
    if not content:
        raise FileError("empty_file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise FileError("file_too_large")
    classified = classify(content)
    if classified.type is None:
        raise FileError(classified.reason or "unsupported_type")
    detected = classified.type
    if len(content) > MAX_BYTES_BY_TYPE[detected]:
        raise FileError("file_too_large")
    if not extension_matches(name, detected):
        raise FileError("extension_mismatch")
    count = session.scalar(select(func.count()).select_from(_live_files(project_id).subquery()))
    if count >= MAX_FILES_PER_PROJECT:
        raise FileError("too_many_files")

    scan = builtin_scan(content, detected)
    if scan.verdict == "quarantined":
        status = "quarantined"
    else:
        # The built-in scan is not authoritative in production: fail closed until a
        # real scanner is configured (DEC-023).
        status = "clean" if builtin_scan_is_authoritative else "pending"

    key = storage.new_key()
    storage.save(key, content)
    row = ProjectFile(
        project_id=project_id,
        original_name=name,
        kind=kind,
        document_date=parsed_date,
        ownership=ownership,
        detected_type=detected,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        storage_key=key,
        scan_status=status,
        scan_detail=scan.detail,
        uploaded_by_user_id=actor.id,
    )
    try:
        session.add(row)
        session.flush()
        session.add(
            ActivityEvent(
                project_id=project_id,
                actor_user_id=actor.id,
                action="project.file_uploaded",
                detail={"file_id": str(row.id), "kind": kind, "scan_status": status},
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        storage.delete(key)
        raise
    session.refresh(row)
    return file_payload(row, actor.display_name)


def _get_live(session: Session, project_id: uuid.UUID, file_id: uuid.UUID) -> ProjectFile:
    row = session.scalar(_live_files(project_id).where(ProjectFile.id == file_id))
    if row is None:
        raise FileError("not_found")
    return row


def download_file(
    session: Session,
    storage: FileStorage,
    actor: User,
    project_id: uuid.UUID,
    file_id: uuid.UUID,
) -> tuple[ProjectFile, bytes]:
    authorize_project(session, actor, project_id, "project.view")
    row = _get_live(session, project_id, file_id)
    if row.scan_status != "clean":
        # Quarantined or not-yet-scanned files are never served.
        raise FileError("not_available")
    return row, storage.read(row.storage_key)


def delete_file(
    session: Session,
    storage: FileStorage,
    actor: User,
    project_id: uuid.UUID,
    file_id: uuid.UUID,
) -> None:
    authorize_project(session, actor, project_id, "project.files.delete")
    row = _get_live(session, project_id, file_id)
    storage.delete(row.storage_key)
    row.deleted_at = datetime.now(UTC)
    row.deleted_by_user_id = actor.id
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.file_deleted",
            detail={"file_id": str(row.id), "kind": row.kind},
        )
    )
    session.commit()
