"""HTTP endpoints for the space schedule (ARCH-001)."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import space_schedule_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["space-schedule"], dependencies=[Depends(check_origin)])


class GenerateBody(BaseModel):
    version: int = Field(ge=0)


async def schedule_error_handler(
    request: Request, exc: space_schedule_service.ScheduleError
) -> JSONResponse:
    status = {"program_incomplete": 409, "version_conflict": 409}.get(exc.code, 400)
    message = {
        "program_incomplete": "Save the complete program (units, floors and rooms) first.",
        "version_conflict": "The schedule was changed elsewhere. Reload it before regenerating.",
    }.get(exc.code, "Error")
    return JSONResponse(_envelope(exc.code, message, _correlation_id(request)), status_code=status)


@router.get("/projects/{project_id}/space-schedule")
def read_schedule(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return space_schedule_service.get_schedule(db, current.user, project_id)


@router.post("/projects/{project_id}/space-schedule/generate")
def generate(
    project_id: uuid.UUID,
    body: GenerateBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return space_schedule_service.generate_schedule(db, current.user, project_id, body.version)
