"""HTTP endpoints for project files (FILE-001, SEC-002).

Uploads are raw request bodies (metadata in the query string), so no multipart
dependency is needed. Nothing is served publicly: bytes leave only through the
authenticated, authorized download endpoint.
"""

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import file_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope
from .file_policy import CONTENT_TYPES, MAX_UPLOAD_BYTES
from .file_storage import FileStorage

router = APIRouter(tags=["files"], dependencies=[Depends(check_origin)])

_STATUS = {
    "not_found": 404,
    "file_too_large": 413,
    "unsupported_type": 415,
    "macro_not_allowed": 415,
    "unsafe_archive": 415,
    "not_available": 409,
    "too_many_files": 409,
}
_MESSAGES = {
    "not_found": "Not Found",
    "file_too_large": "The file is larger than the allowed size.",
    "unsupported_type": "This file type is not allowed.",
    "macro_not_allowed": "Files with macros are not allowed.",
    "unsafe_archive": "The file structure is not allowed.",
    "extension_mismatch": "The file extension does not match the file content.",
    "empty_file": "The file is empty.",
    "invalid_kind": "Unknown file kind.",
    "invalid_date": "The document date is not valid.",
    "invalid_file_name": "The file name is not valid.",
    "invalid_ownership": "The ownership text is too long.",
    "too_many_files": "This project has reached the file count limit.",
    "not_available": "This file is not available for download.",
}


async def file_error_handler(request: Request, exc: file_service.FileError) -> JSONResponse:
    return JSONResponse(
        _envelope(exc.code, _MESSAGES.get(exc.code, "Error"), _correlation_id(request)),
        status_code=_STATUS.get(exc.code, 422),
    )


def get_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


@router.get("/projects/{project_id}/files")
def list_project_files(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"files": file_service.list_files(db, current.user, project_id)}


@router.post("/projects/{project_id}/files", status_code=201)
async def upload_project_file(
    project_id: uuid.UUID,
    request: Request,
    filename: str,
    kind: str,
    document_date: str | None = None,
    ownership: str | None = None,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> dict:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise file_service.FileError("file_too_large")
    received = bytearray()
    async for chunk in request.stream():
        received.extend(chunk)
        if len(received) > MAX_UPLOAD_BYTES:
            raise file_service.FileError("file_too_large")
    return file_service.upload_file(
        db,
        storage,
        current.user,
        project_id,
        filename=filename,
        kind=kind,
        document_date=document_date,
        ownership=ownership,
        content=bytes(received),
        builtin_scan_is_authoritative=request.app.state.settings.environment != "production",
    )


@router.get("/projects/{project_id}/files/{file_id}/download")
def download_project_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> Response:
    row, content = file_service.download_file(db, storage, current.user, project_id, file_id)
    return Response(
        content,
        media_type=CONTENT_TYPES[row.detected_type],
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.original_name)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/projects/{project_id}/files/{file_id}", status_code=204)
def delete_project_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> Response:
    file_service.delete_file(db, storage, current.user, project_id, file_id)
    return Response(status_code=204)
