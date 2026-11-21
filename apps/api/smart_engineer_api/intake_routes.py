"""HTTP endpoints for the project intake steps (INP-001, INP-002)."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import intake_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["intake"], dependencies=[Depends(check_origin)])


class StepBody(BaseModel):
    data: dict
    version: int = Field(ge=0)


async def intake_error_handler(request: Request, exc: intake_service.IntakeError) -> JSONResponse:
    status = {"unknown_step": 404, "version_conflict": 409}.get(exc.code, 400)
    message = {
        "unknown_step": "Not Found",
        "version_conflict": "This step was changed elsewhere. Reload it before saving.",
    }.get(exc.code, "Error")
    return JSONResponse(
        _envelope(exc.code, message, _correlation_id(request)), status_code=status
    )


async def intake_validation_handler(
    request: Request, exc: intake_service.IntakeValidationError
) -> JSONResponse:
    details = [{"field": field, "reason": reason} for field, reason in exc.errors.items()]
    message = "Some fields are not valid."
    return JSONResponse(
        _envelope("invalid_intake", message, _correlation_id(request), details),
        status_code=422,
    )


@router.get("/projects/{project_id}/intake")
def read_intake(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"steps": intake_service.get_intake(db, current.user, project_id)}


@router.put("/projects/{project_id}/intake/{step}")
def save_intake_step(
    project_id: uuid.UUID,
    step: str,
    body: StepBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return intake_service.save_step(db, current.user, project_id, step, body.data, body.version)
