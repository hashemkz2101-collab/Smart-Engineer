"""Read saved geometry and preview a draft without writing (GEOM-001–004)."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import geometry_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope
from .geometry import GeometryError

router = APIRouter(tags=["geometry"], dependencies=[Depends(check_origin)])


class PreviewBody(BaseModel):
    data: dict
    unit: str = Field(default="m", max_length=10)


async def geometry_error_handler(request: Request, exc: GeometryError) -> JSONResponse:
    return JSONResponse(
        _envelope("invalid_geometry", "The boundary is not valid for this calculation.",
                  _correlation_id(request), [{"field": exc.field, "reason": exc.code}]),
        status_code=422,
    )


@router.get("/projects/{project_id}/geometry")
def read_geometry(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return geometry_service.get_geometry(db, current.user, project_id)


@router.post("/projects/{project_id}/geometry/preview")
def preview_geometry(
    project_id: uuid.UUID,
    body: PreviewBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return geometry_service.preview_geometry(db, current.user, project_id, body.data, body.unit)
