"""HTTP endpoints for conceptual layout alternatives (ARCH-002)."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import layout_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["layouts"], dependencies=[Depends(check_origin)])


class GenerateBody(BaseModel):
    version: int = Field(ge=0)


async def layout_error_handler(request: Request, exc: layout_service.LayoutError) -> JSONResponse:
    return JSONResponse(
        _envelope(
            exc.code,
            "The layouts were changed elsewhere. Reload them before regenerating.",
            _correlation_id(request),
        ),
        status_code=409,
    )


@router.get("/projects/{project_id}/layouts")
def read_layouts(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return layout_service.get_layouts(db, current.user, project_id)


@router.post("/projects/{project_id}/layouts/generate")
def generate(
    project_id: uuid.UUID,
    body: GenerateBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return layout_service.generate_layouts(db, current.user, project_id, body.version)
