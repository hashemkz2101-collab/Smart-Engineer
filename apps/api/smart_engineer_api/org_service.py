"""Organization membership and invitations (IAM-002, DEC-017).

Like auth_service, functions commit their own work. Authorization failures raise
``AccessDenied``; business-rule failures raise ``OrgError``.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .access import authorize_org
from .auth_service import EMAIL_PATTERN, aware, utcnow
from .db import Invitation, Membership, Organization, Project, ProjectMember, User
from .permissions import AccessDenied
from .roles import INVITABLE_ORG_ROLES
from .security import new_token, normalize_email, token_digest

INVITATION_TTL = timedelta(days=7)


class OrgError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def list_user_organizations(session: Session, user: User) -> list[tuple[Organization, str]]:
    rows = session.execute(
        select(Organization, Membership.org_role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id, Organization.archived_at.is_(None))
        .order_by(Organization.created_at, Organization.id)
    ).all()
    return [(organization, role) for organization, role in rows]


def list_members(
    session: Session, actor: User, organization_id: uuid.UUID
) -> list[tuple[User, str]]:
    authorize_org(session, actor, organization_id, "org.members.view")
    rows = session.execute(
        select(User, Membership.org_role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == organization_id)
        .order_by(User.email)
    ).all()
    return [(user, role) for user, role in rows]


def create_invitation(
    session: Session,
    actor: User,
    organization_id: uuid.UUID,
    *,
    email: str,
    org_role: str,
    now: datetime | None = None,
) -> tuple[Invitation, str]:
    """Return the invitation and its one-time token (shown as a link; no mailer yet)."""
    now = now or utcnow()
    actor_role = authorize_org(session, actor, organization_id, "org.members.invite")
    if org_role not in INVITABLE_ORG_ROLES:
        raise OrgError("invalid_role")
    if org_role == "admin" and actor_role != "owner":
        raise AccessDenied("org.members.change_role")
    email = normalize_email(email)
    if not EMAIL_PATTERN.match(email) or len(email) > 320:
        raise OrgError("invalid_email")
    existing = session.scalar(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == organization_id, User.email == email)
    )
    if existing is not None:
        raise OrgError("already_member")

    session.execute(
        update(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    token = new_token()
    invitation = Invitation(
        organization_id=organization_id,
        email=email,
        org_role=org_role,
        invited_by_user_id=actor.id,
        token_hash=token_digest(token),
        created_at=now,
        expires_at=now + INVITATION_TTL,
    )
    session.add(invitation)
    session.commit()
    return invitation, token


def revoke_invitation(
    session: Session,
    actor: User,
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
    now: datetime | None = None,
) -> None:
    now = now or utcnow()
    authorize_org(session, actor, organization_id, "org.members.invite")
    invitation = session.get(Invitation, invitation_id)
    if invitation is None or invitation.organization_id != organization_id:
        raise OrgError("not_found")
    if invitation.accepted_at is None and invitation.revoked_at is None:
        invitation.revoked_at = now
        session.commit()


def accept_invitation(
    session: Session, user: User, token: str, now: datetime | None = None
) -> Membership:
    """Join the organization. Wrong account, expired and used tokens look the same."""
    now = now or utcnow()
    invitation = session.scalar(
        select(Invitation).where(Invitation.token_hash == token_digest(token))
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or aware(invitation.expires_at) <= now
        or invitation.email != user.email
    ):
        raise OrgError("invalid_token")
    already = session.scalar(
        select(Membership.id).where(
            Membership.organization_id == invitation.organization_id,
            Membership.user_id == user.id,
        )
    )
    if already is not None:
        raise OrgError("already_member")
    membership = Membership(
        organization_id=invitation.organization_id,
        user_id=user.id,
        org_role=invitation.org_role,
    )
    invitation.accepted_at = now
    session.add(membership)
    session.commit()
    return membership


def _membership(session: Session, organization_id: uuid.UUID, user_id: uuid.UUID) -> Membership:
    membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id, Membership.user_id == user_id
        )
    )
    if membership is None:
        raise OrgError("not_found")
    return membership


def change_member_role(
    session: Session,
    actor: User,
    organization_id: uuid.UUID,
    target_user_id: uuid.UUID,
    new_role: str,
) -> Membership:
    authorize_org(session, actor, organization_id, "org.members.change_role")
    if new_role not in INVITABLE_ORG_ROLES:
        raise OrgError("invalid_role")
    membership = _membership(session, organization_id, target_user_id)
    if membership.org_role == "owner":
        raise OrgError("owner_role_fixed")
    membership.org_role = new_role
    session.commit()
    return membership


def remove_member(
    session: Session, actor: User, organization_id: uuid.UUID, target_user_id: uuid.UUID
) -> None:
    """Remove a member and every project role they hold in this organization."""
    actor_role = authorize_org(session, actor, organization_id, "org.members.remove")
    membership = _membership(session, organization_id, target_user_id)
    if membership.org_role == "owner":
        raise OrgError("cannot_remove_owner")
    if membership.org_role == "admin" and actor_role != "owner":
        raise AccessDenied("org.members.remove")
    project_ids = select(Project.id).where(Project.organization_id == organization_id)
    session.execute(
        delete(ProjectMember).where(
            ProjectMember.user_id == target_user_id, ProjectMember.project_id.in_(project_ids)
        )
    )
    session.delete(membership)
    session.commit()
