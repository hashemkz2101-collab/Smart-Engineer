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


def file_payload(
    row: ProjectFile, uploader_name: str | None, latest_version: int | None = None
) -> dict:
    latest = latest_version if latest_version is not None else row.version_number
    return {
        "id": str(row.id),
        "series_id": str(row.series_id),
        "version_number": row.version_number,
        "is_latest": row.version_number >= latest,
        "is_basis": row.is_basis,
        # The takeoff basis is outdated once a newer version of the same file exists:
        # earlier quantities may no longer match the drawing.
        "basis_outdated": row.is_basis and row.version_number < latest,
        "restored_from_file_id": str(row.restored_from_file_id)
        if row.restored_from_file_id
        else None,
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
    latest: dict[uuid.UUID, int] = {}
    for row in rows:
        latest[row.series_id] = max(latest.get(row.series_id, 0), row.version_number)
    return [
        file_payload(row, names.get(row.uploaded_by_user_id), latest[row.series_id])
        for row in rows
    ]


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
    new_version_of: uuid.UUID | None = None,
    restored_from: ProjectFile | None = None,
) -> dict:
    authorize_project(session, actor, project_id, "project.files.upload")
    series_id = uuid.uuid4()
    version_number = 1
    if new_version_of is not None:
        previous = _get_live(session, project_id, new_version_of)
        series_id = previous.series_id
        version_number = (
            session.scalar(
                select(func.max(ProjectFile.version_number)).where(
                    ProjectFile.series_id == series_id
                )
            )
            or 0
        ) + 1
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
        series_id=series_id,
        version_number=version_number,
        restored_from_file_id=restored_from.id if restored_from else None,
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
                action="project.file_restored" if restored_from else "project.file_uploaded",
                detail={
                    "file_id": str(row.id),
                    "kind": kind,
                    "scan_status": status,
                    "series_id": str(series_id),
                    "version_number": version_number,
                },
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        storage.delete(key)
        raise
    session.refresh(row)
    return file_payload(row, actor.display_name, row.version_number)


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
    row.is_basis = False
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.file_deleted",
            detail={"file_id": str(row.id), "kind": row.kind},
        )
    )
    session.commit()


def restore_version(
    session: Session,
    storage: FileStorage,
    actor: User,
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    *,
    builtin_scan_is_authoritative: bool,
) -> dict:
    """Make an earlier version current again as a *new* version (nothing is overwritten)."""
    authorize_project(session, actor, project_id, "project.files.upload")
    row = _get_live(session, project_id, file_id)
    if row.scan_status != "clean":
        raise FileError("not_available")
    return upload_file(
        session,
        storage,
        actor,
        project_id,
        filename=row.original_name,
        kind=row.kind,
        document_date=row.document_date.isoformat() if row.document_date else None,
        ownership=row.ownership,
        content=storage.read(row.storage_key),
        builtin_scan_is_authoritative=builtin_scan_is_authoritative,
        new_version_of=row.id,
        restored_from=row,
    )


def set_basis(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    *,
    is_basis: bool,
) -> dict:
    """Record (or clear) which version of a file takeoff and estimate work is based on."""
    authorize_project(session, actor, project_id, "project.files.set_basis")
    row = _get_live(session, project_id, file_id)
    if is_basis and row.scan_status != "clean":
        raise FileError("not_available")
    if row.is_basis != is_basis:
        if is_basis:
            for other in session.scalars(
                _live_files(project_id).where(
                    ProjectFile.series_id == row.series_id, ProjectFile.id != row.id
                )
            ):
                other.is_basis = False
        row.is_basis = is_basis
        session.add(
            ActivityEvent(
                project_id=project_id,
                actor_user_id=actor.id,
                action="project.file_basis_set" if is_basis else "project.file_basis_cleared",
                detail={
                    "file_id": str(row.id),
                    "series_id": str(row.series_id),
                    "version_number": row.version_number,
                },
            )
        )
        session.commit()
        session.refresh(row)
    latest = session.scalar(
        select(func.max(ProjectFile.version_number)).where(
            ProjectFile.series_id == row.series_id, ProjectFile.deleted_at.is_(None)
        )
    )
    uploader = session.get(User, row.uploaded_by_user_id)
    return file_payload(row, uploader.display_name if uploader else None, latest)


def compare_versions(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    other_id: uuid.UUID,
) -> dict:
    """Compare two versions of one file by their recorded facts.

    Content-level comparison needs per-type extraction (FILE-003) and is not done here.
    """
    authorize_project(session, actor, project_id, "project.view")
    first = _get_live(session, project_id, file_id)
    second = _get_live(session, project_id, other_id)
    if first.series_id != second.series_id:
        raise FileError("different_series")
    names = {
        user.id: user.display_name
        for user in session.scalars(
            select(User).where(User.id.in_({first.uploaded_by_user_id, second.uploaded_by_user_id}))
        )
    }
    latest = session.scalar(
        select(func.max(ProjectFile.version_number)).where(
            ProjectFile.project_id == project_id,
            ProjectFile.series_id == first.series_id,
            ProjectFile.deleted_at.is_(None),
        )
    )
    return {
        "from": file_payload(first, names.get(first.uploaded_by_user_id), latest),
        "to": file_payload(second, names.get(second.uploaded_by_user_id), latest),
        "identical_content": first.sha256 == second.sha256,
        "size_delta_bytes": second.size_bytes - first.size_bytes,
        "type_changed": first.detected_type != second.detected_type,
        "name_changed": first.original_name != second.original_name,
        "document_date_changed": first.document_date != second.document_date,
        "ownership_changed": first.ownership != second.ownership,
    }
