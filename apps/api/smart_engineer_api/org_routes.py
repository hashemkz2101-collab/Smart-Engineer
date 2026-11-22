"""HTTP endpoints for organizations, members and invitations (IAM-002)."""

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import org_service
from .auth_routes import Authenticated, check_origin, csrf_protected, current_auth, get_db
from .errors import _correlation_id, _envelope
from .permissions import AccessDenied

ORG_STATUS_BY_CODE = {
    "invalid_role": 422,
    "invalid_email": 422,
    "already_member": 409,
    "invalid_token": 400,
    "not_found": 404,
    "cannot_remove_owner": 409,
    "owner_role_fixed": 409,
}
ORG_MESSAGE_BY_CODE = {
    "invalid_role": "The role is not valid.",
    "invalid_email": "The email address is not valid.",
    "already_member": "This user is already a member.",
    "invalid_token": "The invitation is invalid or has expired.",
    "not_found": "Not found.",
    "cannot_remove_owner": "The organization owner cannot be removed.",
    "owner_role_fixed": "The owner role cannot be changed.",
}


async def org_error_handler(request: Request, exc: org_service.OrgError) -> JSONResponse:
    message = ORG_MESSAGE_BY_CODE.get(exc.code, "Error")
    return JSONResponse(
        _envelope(exc.code, message, _correlation_id(request)),
        status_code=ORG_STATUS_BY_CODE.get(exc.code, 400),
    )


async def access_denied_handler(request: Request, exc: AccessDenied) -> JSONResponse:
    # Hidden denials look exactly like a missing resource.
    if exc.hidden:
        return JSONResponse(
            _envelope("http_404", "Not Found", _correlation_id(request)), status_code=404
        )
    return JSONResponse(
        _envelope("forbidden", "You do not have permission to do this.", _correlation_id(request)),
        status_code=403,
    )


class InviteBody(BaseModel):
    email: str = Field(max_length=320)
    org_role: str = Field(default="member", max_length=20)


class AcceptBody(BaseModel):
    token: str = Field(max_length=512)


class RoleBody(BaseModel):
    org_role: str = Field(max_length=20)


router = APIRouter(tags=["organizations"], dependencies=[Depends(check_origin)])


@router.get("/orgs")
def my_organizations(
    current: Authenticated = Depends(current_auth), db: Session = Depends(get_db)
) -> dict:
    rows = org_service.list_user_organizations(db, current.user)
    return {
        "organizations": [
            {"id": str(org.id), "name": org.name, "org_role": role} for org, role in rows
        ]
    }


@router.get("/orgs/{organization_id}/members")
def members(
    organization_id: uuid.UUID,
    current: Authenticated = Depends(current_auth),
    db: Session = Depends(get_db),
) -> dict:
    rows = org_service.list_members(db, current.user, organization_id)
    return {
        "members": [
            {
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "org_role": role,
            }
            for user, role in rows
        ]
    }


@router.post("/orgs/{organization_id}/invitations", status_code=201)
def invite(
    organization_id: uuid.UUID,
    body: InviteBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    invitation, token = org_service.create_invitation(
        db, current.user, organization_id, email=body.email, org_role=body.org_role
    )
    # The token is returned once so the inviter can share a link (no mailer yet).
    return {
        "invitation": {
            "id": str(invitation.id),
            "email": invitation.email,
            "org_role": invitation.org_role,
            "expires_at": invitation.expires_at.isoformat(),
        },
        "token": token,
    }


@router.delete("/orgs/{organization_id}/invitations/{invitation_id}", status_code=204)
def revoke(
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> Response:
    org_service.revoke_invitation(db, current.user, organization_id, invitation_id)
    return Response(status_code=204)


@router.post("/invitations/accept")
def accept(
    body: AcceptBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    membership, project_id = org_service.accept_invitation_scoped(db, current.user, body.token)
    return {
        "organization_id": str(membership.organization_id),
        "org_role": membership.org_role,
        "project_id": str(project_id) if project_id else None,
    }


@router.patch("/orgs/{organization_id}/members/{user_id}")
def change_role(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    body: RoleBody,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> dict:
    membership = org_service.change_member_role(
        db, current.user, organization_id, user_id, body.org_role
    )
    return {"user_id": str(user_id), "org_role": membership.org_role}


@router.delete("/orgs/{organization_id}/members/{user_id}", status_code=204)
def remove(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    current: Authenticated = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> Response:
    org_service.remove_member(db, current.user, organization_id, user_id)
    return Response(status_code=204)
