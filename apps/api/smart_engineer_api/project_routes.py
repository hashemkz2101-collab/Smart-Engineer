"""HTTP endpoints for projects, project members and activity (PRJ-001/002)."""

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import project_service
from .access import ARCHIVE_RECOVERY_ACTIONS, authorize_project
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope
from .permissions import PROJECT_ACTION_ROLES, project_role_can

STATUS_BY_CODE = {
    "invalid_name": 422,
    "invalid_project_type": 422,
    "invalid_role": 422,
    "user_not_in_organization": 422,
    "already_member": 409,
    "last_owner": 409,
    "not_archived": 409,
    "not_found": 404,
}
MESSAGE_BY_CODE = {
    "invalid_name": "The project name is required and must be at most 200 characters.",
    "invalid_project_type": "The project type is not valid.",
    "invalid_role": "The role is not valid.",
    "user_not_in_organization": "The user is not a member of this organization.",
    "already_member": "This user already has a role on the project.",
    "last_owner": "A project must keep at least one owner.",
    "not_archived": "The project is not archived.",
    "not_found": "Not found.",
}


async def project_error_handler(
    request: Request, exc: project_service.ProjectError
) -> JSONResponse:
    message = MESSAGE_BY_CODE.get(exc.code, "Error")
    return JSONResponse(
        _envelope(exc.code, message, _correlation_id(request)),
        status_code=STATUS_BY_CODE.get(exc.code, 400),
    )


class CreateBody(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(max_length=200)
    project_type: str = Field(max_length=30)
    description: str | None = Field(default=None, max_length=5000)


class UpdateBody(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    project_type: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=5000)


class AddMemberBody(BaseModel):
    email: str = Field(max_length=320)
    role: str = Field(max_length=30)


class RoleBody(BaseModel):
    role: str = Field(max_length=30)


def project_payload(project) -> dict:
    return {
        "id": str(project.id),
        "organization_id": str(project.organization_id),
        "name": project.name,
        "project_type": project.project_type,
        "status": project.status,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
        "archived_at": project.archived_at.isoformat() if project.archived_at else None,
    }


def allowed_actions(project, role: str) -> list[str]:
    """Actions the UI may offer; the backend still re-checks every request."""
    actions = [a for a in PROJECT_ACTION_ROLES if project_role_can(role, a)]
    if role == "org_admin":
        actions = sorted(ARCHIVE_RECOVERY_ACTIONS)
    elif project.status == "archived":
        actions = [a for a in actions if a in ARCHIVE_RECOVERY_ACTIONS]
    return actions


router = APIRouter(tags=["projects"], dependencies=[Depends(check_origin)])


@router.post("/projects", status_code=201)
def create(
    body: CreateBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    project = project_service.create_project(
        db,
        current.user,
        body.organization_id,
        name=body.name,
        project_type=body.project_type,
        description=body.description,
    )
    return {"project": project_payload(project)}


@router.get("/projects")
def list_all(
    organization_id: uuid.UUID | None = Query(default=None),
    archived: bool = Query(default=False),
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    projects = project_service.list_projects(
        db, current.user, organization_id=organization_id, archived=archived
    )
    return {"projects": [project_payload(p) for p in projects]}


@router.get("/projects/{project_id}")
def read(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    project, role = authorize_project(db, current.user, project_id, "project.view")
    return {
        "project": project_payload(project),
        "my_role": role,
        "permissions": allowed_actions(project, role),
    }


@router.patch("/projects/{project_id}")
def update(
    project_id: uuid.UUID,
    body: UpdateBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    project = project_service.update_project(
        db,
        current.user,
        project_id,
        name=body.name,
        project_type=body.project_type,
        description=body.description,
    )
    return {"project": project_payload(project)}


@router.post("/projects/{project_id}/archive")
def archive(
    project_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    project = project_service.archive_project(db, current.user, project_id)
    return {"project": project_payload(project)}


@router.post("/projects/{project_id}/restore")
def restore(
    project_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    project = project_service.restore_project(db, current.user, project_id)
    return {"project": project_payload(project)}


@router.get("/projects/{project_id}/members")
def members(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    rows = project_service.list_project_members(db, current.user, project_id)
    return {
        "members": [
            {
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "role": role,
            }
            for user, role in rows
        ]
    }


@router.post("/projects/{project_id}/members", status_code=201)
def add_member(
    project_id: uuid.UUID,
    body: AddMemberBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    member = project_service.add_member(
        db, current.user, project_id, email=body.email, role=body.role
    )
    return {"user_id": str(member.user_id), "role": member.role}


@router.patch("/projects/{project_id}/members/{user_id}")
def change_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    body: RoleBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    member = project_service.change_member_role(db, current.user, project_id, user_id, body.role)
    return {"user_id": str(member.user_id), "role": member.role}


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> Response:
    project_service.remove_member(db, current.user, project_id, user_id)
    return Response(status_code=204)


@router.get("/projects/{project_id}/activity")
def activity(
    project_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    events = project_service.list_activity(db, current.user, project_id)
    return {
        "events": [
            {
                "id": event.id,
                "action": event.action,
                "actor_user_id": str(event.actor_user_id),
                "target_user_id": str(event.target_user_id) if event.target_user_id else None,
                "detail": event.detail,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
    }
