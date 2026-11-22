"""HTTP endpoints for environmental inputs (ENV-001)."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import environment_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["environment"], dependencies=[Depends(check_origin)])


class RecordBody(BaseModel):
    data: dict
    version: int = Field(ge=0)


async def environment_error_handler(
    request: Request, exc: environment_service.EnvironmentError_
) -> JSONResponse:
    status = {"unknown_field": 404, "version_conflict": 409}.get(exc.code, 400)
    message = {
        "unknown_field": "Not Found",
        "version_conflict": "This record was changed elsewhere. Reload it before saving.",
    }.get(exc.code, "Error")
    return JSONResponse(_envelope(exc.code, message, _correlation_id(request)), status_code=status)


async def environment_validation_handler(
    request: Request, exc: environment_service.EnvironmentValidationError
) -> JSONResponse:
    details = [{"field": field, "reason": reason} for field, reason in exc.errors.items()]
    return JSONResponse(
        _envelope(
            "invalid_environment", "Some fields are not valid.", _correlation_id(request), details
        ),
        status_code=422,
    )


@router.get("/projects/{project_id}/environment")
def read_environment(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"records": environment_service.get_environment(db, current.user, project_id)}


@router.put("/projects/{project_id}/environment/{field}")
def save_environment_record(
    project_id: uuid.UUID,
    field: str,
    body: RecordBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return environment_service.save_record(
        db, current.user, project_id, field, body.data, body.version
    )
