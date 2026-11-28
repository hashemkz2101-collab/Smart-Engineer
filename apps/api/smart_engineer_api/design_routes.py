"""HTTP endpoints for the working design model (ARCH-003)."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import ai_design_service, design_service, design_version_service
from .access import authorize_project
from .ai_design import MAX_INSTRUCTION_LENGTH, AiError
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .design_model import DesignError
from .errors import _correlation_id, _envelope

router = APIRouter(tags=["design"], dependencies=[Depends(check_origin)])

CONFLICT_CODES = {
    "nothing_to_undo", "nothing_to_redo",
    "element_locked", "hosted_element_locked", "version_conflict", "design_exists",
    "layout_stale", "no_layout", "no_design", "floor_not_empty",
}
MESSAGES = {
    "nothing_to_undo": "There is no earlier state to return to.",
    "nothing_to_redo": "There is no later state to return to.",
    "element_locked": "The element is locked. Unlock it before editing.",
    "hosted_element_locked": "A door, window or opening on this wall is locked.",
    "version_conflict": "The design was changed elsewhere. Reload it before editing.",
    "design_exists": "A design with elements already exists. Confirm replacing it.",
    "layout_stale": "The layout options are out of date. Regenerate them first.",
    "no_layout": "There are no layout alternatives to import.",
    "no_design": "There is no design to edit yet. Import a layout option first.",
    "floor_not_empty": "A target floor already has elements; copying never overwrites.",
    "unknown_version": "There is no such saved version.",
    "too_many_versions": "The project has reached the maximum number of saved versions.",
    "too_many_comments": "This version has reached the maximum number of comments.",
    "unknown_element": "The element is not part of this version.",
    "unknown_floor": "The source floor has no elements to copy.",
    "vertical_invalid_level": "A vertical connection points at a floor that has no elements.",
}


class ImportBody(BaseModel):
    alternative_id: str = Field(min_length=1, max_length=40)
    version: int = Field(ge=0)
    replace: bool = False


class SnapBody(BaseModel):
    grid: float = Field(gt=0)
    unit: Literal["m", "cm", "mm"] | None = None


class EditBody(BaseModel):
    version: int = Field(ge=0)
    operations: list[dict[str, Any]] = Field(min_length=1, max_length=50)
    unit: Literal["m", "cm", "mm"] = "m"
    snap: SnapBody | None = None


class StepBody(BaseModel):
    version: int = Field(ge=1)


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
    status = 404 if exc.code == "unknown_version" else 409 if exc.code in CONFLICT_CODES else 422
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
    snap = body.snap.model_dump(exclude_none=True) if body.snap else None
    return design_service.edit_design(
        db, current.user, project_id, operations=body.operations,
        expected_version=body.version, unit=body.unit, snap=snap,
    )


@router.post("/projects/{project_id}/design/undo")
def undo(
    project_id: uuid.UUID,
    body: StepBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return design_service.undo_design(db, current.user, project_id, expected_version=body.version)


@router.post("/projects/{project_id}/design/redo")
def redo(
    project_id: uuid.UUID,
    body: StepBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return design_service.redo_design(db, current.user, project_id, expected_version=body.version)


@router.get("/projects/{project_id}/design/history")
def history(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return design_service.design_history(db, current.user, project_id)


class VersionBody(BaseModel):
    version: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=120)


class CommentBody(BaseModel):
    body: str = Field(min_length=1, max_length=design_version_service.MAX_COMMENT_LENGTH)
    element_id: str | None = Field(default=None, max_length=20)


@router.get("/projects/{project_id}/design/versions")
def list_versions(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return design_version_service.list_versions(db, current.user, project_id)


@router.post("/projects/{project_id}/design/versions", status_code=201)
def save_version(
    project_id: uuid.UUID,
    body: VersionBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return design_version_service.save_version(
        db, current.user, project_id, label=body.label, expected_version=body.version
    )


@router.get("/projects/{project_id}/design/compare")
def compare_versions(
    project_id: uuid.UUID,
    a: str = Query(max_length=12),
    b: str = Query(max_length=12),
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return design_version_service.compare_versions(db, current.user, project_id, a, b)


@router.get("/projects/{project_id}/design/versions/{number}")
def read_version(
    project_id: uuid.UUID,
    number: int,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return design_version_service.get_version(db, current.user, project_id, number)


@router.post("/projects/{project_id}/design/versions/{number}/comments", status_code=201)
def add_comment(
    project_id: uuid.UUID,
    number: int,
    body: CommentBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return design_version_service.add_comment(
        db, current.user, project_id, number, body=body.body, element_id=body.element_id
    )


AI_STATUS = {
    "ai_not_configured": 503,
    "ai_auth": 502,
    "ai_unavailable": 502,
    "ai_bad_response": 502,
    "ai_rate_limited": 429,
    "ai_limit_reached": 429,
}
AI_MESSAGES = {
    "ai_not_configured": "Claude is not set up on this server (no API key).",
    "ai_auth": "The Claude API key was rejected.",
    "ai_unavailable": "The Claude service could not be reached. Try again later.",
    "ai_bad_response": "Claude returned an answer that could not be understood.",
    "ai_rate_limited": "The Claude service is busy. Try again in a minute.",
    "ai_limit_reached": "The daily limit of Claude proposals for this project was reached.",
}


async def ai_error_handler(request: Request, exc: AiError) -> JSONResponse:
    return JSONResponse(
        _envelope(exc.code, AI_MESSAGES.get(exc.code, "The request failed."),
                  _correlation_id(request)),
        status_code=AI_STATUS.get(exc.code, 502),
    )


class AiProposalBody(BaseModel):
    instruction: str = Field(default="", max_length=MAX_INSTRUCTION_LENGTH)


@router.get("/projects/{project_id}/design/ai-status")
def ai_status(
    request: Request,
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    authorize_project(db, current.user, project_id, "project.view")
    return ai_design_service.ai_status(request.app.state.settings, request.app.state.ai_client)


@router.post("/projects/{project_id}/design/ai-proposal")
def ai_proposal(
    request: Request,
    project_id: uuid.UUID,
    body: AiProposalBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return ai_design_service.propose_design(
        db, current.user, project_id, client=request.app.state.ai_client,
        settings=request.app.state.settings, instruction=body.instruction,
    )
