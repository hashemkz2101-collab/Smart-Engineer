"""HTTP endpoints for project site / land data (SITE-001, SITE-002)."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import site_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["site"], dependencies=[Depends(check_origin)])


class SectionBody(BaseModel):
    data: dict
    version: int = Field(ge=0)


async def site_error_handler(request: Request, exc: site_service.SiteError) -> JSONResponse:
    status = {"unknown_section": 404, "version_conflict": 409}.get(exc.code, 400)
    message = {
        "unknown_section": "Not Found",
        "version_conflict": "This section was changed elsewhere. Reload it before saving.",
    }.get(exc.code, "Error")
    return JSONResponse(
        _envelope(exc.code, message, _correlation_id(request)), status_code=status
    )


async def site_validation_handler(
    request: Request, exc: site_service.SiteValidationError
) -> JSONResponse:
    details = [{"field": field, "reason": reason} for field, reason in exc.errors.items()]
    return JSONResponse(
        _envelope("invalid_site", "Some fields are not valid.", _correlation_id(request), details),
        status_code=422,
    )


@router.get("/projects/{project_id}/site")
def read_site(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"sections": site_service.get_site(db, current.user, project_id)}


@router.put("/projects/{project_id}/site/{section}")
def save_site_section(
    project_id: uuid.UUID,
    section: str,
    body: SectionBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return site_service.save_section(db, current.user, project_id, section, body.data, body.version)
