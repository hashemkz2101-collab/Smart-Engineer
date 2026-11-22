"""HTTP endpoints for platform administration (ADMIN-001).

All routes live under ``/admin`` and answer 404 to anyone who is not an active system
administrator, so they cannot be discovered by other users.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import admin_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(check_origin)])

_STATUS = {
    "not_found": 404,
    "user_not_found": 422,
    "invalid_role": 422,
    "user_not_in_organization": 422,
    "user_inactive": 422,
    "already_member": 409,
    "last_owner": 409,
    "last_system_admin": 409,
    "cannot_change_self": 409,
    "project_archived": 409,
}
_MESSAGES = {
    "not_found": "Not found.",
    "user_not_found": "No active user has this email address.",
    "invalid_role": "The role is not valid.",
    "user_not_in_organization": "The user is not a member of the project's organization.",
    "user_inactive": "The user account is deactivated.",
    "already_member": "This user already has a role on the project.",
    "last_owner": "A project must keep at least one owner.",
    "last_system_admin": "The platform must keep at least one active system administrator.",
    "cannot_change_self": "Administrators cannot change their own account state here.",
    "project_archived": "Archived projects are read-only.",
}


async def admin_error_handler(request: Request, exc: admin_service.AdminError) -> JSONResponse:
    return JSONResponse(
        _envelope(exc.code, _MESSAGES.get(exc.code, "Error"), _correlation_id(request)),
        status_code=_STATUS.get(exc.code, 400),
    )


class ActiveBody(BaseModel):
    active: bool


class AdminFlagBody(BaseModel):
    is_system_admin: bool


class MemberBody(BaseModel):
    email: str = Field(max_length=320)
    role: str = Field(max_length=30)


class RoleBody(BaseModel):
    role: str = Field(max_length=30)


@router.get("/users")
def users(
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"users": admin_service.list_users(db, current.user, query=q, limit=limit)}


@router.put("/users/{user_id}/active")
def set_active(
    user_id: uuid.UUID,
    body: ActiveBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return {"user": admin_service.set_user_active(db, current.user, user_id, body.active)}


@router.put("/users/{user_id}/system-admin")
def set_system_admin(
    user_id: uuid.UUID,
    body: AdminFlagBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return {"user": admin_service.set_system_admin(db, current.user, user_id, body.is_system_admin)}


@router.get("/projects")
def projects(
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"projects": admin_service.list_projects(db, current.user, query=q, limit=limit)}


@router.get("/projects/{project_id}/members")
def project_members(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"members": admin_service.list_project_access(db, current.user, project_id)}


@router.post("/projects/{project_id}/members", status_code=201)
def add_member(
    project_id: uuid.UUID,
    body: MemberBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "member": admin_service.add_project_member(
            db, current.user, project_id, email=body.email, role=body.role
        )
    }


@router.patch("/projects/{project_id}/members/{user_id}")
def change_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    body: RoleBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "member": admin_service.change_project_member_role(
            db, current.user, project_id, user_id, body.role
        )
    }


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> Response:
    admin_service.remove_project_member(db, current.user, project_id, user_id)
    return Response(status_code=204)


@router.get("/audit")
def audit(
    limit: int = Query(default=100, ge=1, le=500),
    before_id: int | None = Query(default=None, ge=1),
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    return {"events": admin_service.list_audit(db, current.user, limit=limit, before_id=before_id)}
