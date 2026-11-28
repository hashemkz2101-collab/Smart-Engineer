"""HTTP endpoints for the working design model (ARCH-003)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import design_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .design_model import DesignError
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["design"], dependencies=[Depends(check_origin)])

CONFLICT_CODES = {
    "element_locked", "hosted_element_locked", "version_conflict", "design_exists",
    "layout_stale", "no_layout", "no_design",
}
MESSAGES = {
    "element_locked": "The element is locked. Unlock it before editing.",
    "hosted_element_locked": "A door, window or opening on this wall is locked.",
    "version_conflict": "The design was changed elsewhere. Reload it before editing.",
    "design_exists": "A design with elements already exists. Confirm replacing it.",
    "layout_stale": "The layout options are out of date. Regenerate them first.",
    "no_layout": "There are no layout alternatives to import.",
    "no_design": "There is no design to edit yet. Import a layout option first.",
}


class ImportBody(BaseModel):
    alternative_id: str = Field(min_length=1, max_length=40)
    version: int = Field(ge=0)
    replace: bool = False


class EditBody(BaseModel):
    version: int = Field(ge=0)
    operations: list[dict[str, Any]] = Field(min_length=1, max_length=50)


async def design_error_handler(request: Request, exc: DesignError) -> JSONResponse:
    details = [{"operation_index": exc.index, "element_id": exc.element_id}]
    status = 409 if exc.code in CONFLICT_CODES else 422
    return JSONResponse(
        _envelope(exc.code, MESSAGES.get(exc.code, "The edit is not valid."),
                  _correlation_id(request), details),
        status_code=status,
    )


async def design_service_error_handler(
    request: Request, exc: design_service.DesignServiceError
) -> JSONResponse:
    status = 409 if exc.code in CONFLICT_CODES else 422
    return JSONResponse(
        _envelope(exc.code, MESSAGES.get(exc.code, "The request is not valid."),
                  _correlation_id(request)),
        status_code=status,
    )


@router.get("/projects/{project_id}/design")
def read_design(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return design_service.get_design(db, current.user, project_id)


@router.post("/projects/{project_id}/design/import-layout")
def import_layout(
    project_id: uuid.UUID,
    body: ImportBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return design_service.import_layout(
        db, current.user, project_id, alternative_id=body.alternative_id,
        expected_version=body.version, replace=body.replace,
    )


@router.post("/projects/{project_id}/design/edit")
def edit(
    project_id: uuid.UUID,
    body: EditBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return design_service.edit_design(
        db, current.user, project_id, operations=body.operations, expected_version=body.version
    )
