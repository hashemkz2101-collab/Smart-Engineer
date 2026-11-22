"""Platform administration: users, system-admin flag, project access, audit (ADMIN-001).

Every function authorizes the caller as an active system administrator for one
specific platform action, and every change writes an ``AdminAuditEvent`` in the same
transaction. A system administrator has no implicit project rights: this module only
touches metadata and project *access* (who holds which role), never project content.
Non-administrators get a hidden denial, so the endpoints look absent to them.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .auth_service import _revoke_sessions, utcnow
from .db import (
    ActivityEvent,
    AdminAuditEvent,
    Membership,
    Organization,
    Project,
    ProjectMember,
    User,
)
from .permissions import AccessDenied, platform_can
from .roles import PROJECT_ROLES
from .security import normalize_email


class AdminError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def authorize_platform(actor: User, action: str) -> None:
    if not actor.is_active or not actor.is_system_admin:
        raise AccessDenied(action, hidden=True)
    if not platform_can(True, action):
        raise AccessDenied(action)


def _audit(
    session: Session,
    actor: User,
    action: str,
    *,
    target_user_id: uuid.UUID | None = None,
    target_project_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> None:
    session.add(
        AdminAuditEvent(
            actor_user_id=actor.id,
            action=action,
            target_user_id=target_user_id,
            target_project_id=target_project_id,
            detail=detail,
        )
    )


def _user(session: Session, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise AdminError("not_found")
    return user


def _active_admin_count(session: Session) -> int:
    return session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.is_system_admin.is_(True), User.is_active.is_(True))
    )


def user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "is_system_admin": user.is_system_admin,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def list_users(
    session: Session, actor: User, *, query: str | None = None, limit: int = 100
) -> list[dict]:
    authorize_platform(actor, "platform.users.view")
    statement = select(User).order_by(User.email).limit(max(1, min(limit, 500)))
    if query and query.strip():
        pattern = f"%{query.strip().lower()}%"
        statement = statement.where(
            or_(func.lower(User.email).like(pattern), func.lower(User.display_name).like(pattern))
        )
    return [user_payload(user) for user in session.scalars(statement)]


def set_user_active(session: Session, actor: User, user_id: uuid.UUID, active: bool) -> dict:
    authorize_platform(actor, "platform.users.manage")
    target = _user(session, user_id)
    if target.id == actor.id:
        raise AdminError("cannot_change_self")
    if target.is_active == active:
        return user_payload(target)
    if not active and target.is_system_admin and _active_admin_count(session) <= 1:
        raise AdminError("last_system_admin")
    target.is_active = active
    if not active:
        # A deactivated account must stop working immediately.
        _revoke_sessions(session, target.id, utcnow())
    _audit(
        session,
        actor,
        "admin.user_activated" if active else "admin.user_deactivated",
        target_user_id=target.id,
    )
    session.commit()
    return user_payload(target)


def set_system_admin(session: Session, actor: User, user_id: uuid.UUID, value: bool) -> dict:
    authorize_platform(actor, "platform.admins.manage")
    target = _user(session, user_id)
    if target.id == actor.id:
        raise AdminError("cannot_change_self")
    if target.is_system_admin == value:
        return user_payload(target)
    if value and not target.is_active:
        raise AdminError("user_inactive")
    if not value and target.is_active and _active_admin_count(session) <= 1:
        raise AdminError("last_system_admin")
    target.is_system_admin = value
    _audit(
        session,
        actor,
        "admin.system_admin_granted" if value else "admin.system_admin_revoked",
        target_user_id=target.id,
    )
    session.commit()
    return user_payload(target)


def grant_first_admin(session: Session, email: str) -> dict:
    """Command-line bootstrap: mark an existing active user as system administrator.

    There is no other way to create the first administrator. The action is audited with
    the user as both actor and target and ``via: command_line``.
    """
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        raise AdminError("not_found")
    if not user.is_active:
        raise AdminError("user_inactive")
    if not user.is_system_admin:
        user.is_system_admin = True
        _audit(
            session,
            user,
            "admin.system_admin_granted",
            target_user_id=user.id,
            detail={"via": "command_line"},
        )
        session.commit()
    return user_payload(user)


def _project_payload(project: Project, organization_name: str, member_count: int) -> dict:
    return {
        "id": str(project.id),
        "name": project.name,
        "project_type": project.project_type,
        "status": project.status,
        "organization_id": str(project.organization_id),
        "organization_name": organization_name,
        "member_count": member_count,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def list_projects(
    session: Session, actor: User, *, query: str | None = None, limit: int = 100
) -> list[dict]:
    """Project metadata only: no project content is exposed to the platform role."""
    authorize_platform(actor, "platform.projects.view")
    members = (
        select(ProjectMember.project_id, func.count().label("members"))
        .group_by(ProjectMember.project_id)
        .subquery()
    )
    statement = (
        select(Project, Organization.name, func.coalesce(members.c.members, 0))
        .join(Organization, Organization.id == Project.organization_id)
        .outerjoin(members, members.c.project_id == Project.id)
        .order_by(Project.created_at.desc(), Project.name)
        .limit(max(1, min(limit, 500)))
    )
    if query and query.strip():
        statement = statement.where(func.lower(Project.name).like(f"%{query.strip().lower()}%"))
    return [
        _project_payload(project, org_name, count)
        for project, org_name, count in session.execute(statement)
    ]


def _manageable_project(session: Session, project_id: uuid.UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise AdminError("not_found")
    if project.status == "archived":
        raise AdminError("project_archived")
    return project


def list_project_access(session: Session, actor: User, project_id: uuid.UUID) -> list[dict]:
    authorize_platform(actor, "platform.projects.view")
    if session.get(Project, project_id) is None:
        raise AdminError("not_found")
    rows = session.execute(
        select(User, ProjectMember.role)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.email)
    ).all()
    return [
        {
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": role,
        }
        for user, role in rows
    ]


def _owner_count(session: Session, project_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id, ProjectMember.role == "owner")
    )


def _project_member(session: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectMember:
    member = session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    if member is None:
        # Also what a member id from a different project looks like: not found here.
        raise AdminError("not_found")
    return member


def _record_project_event(
    session: Session, project_id: uuid.UUID, actor: User, action: str, target_user_id, detail
) -> None:
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action=action,
            target_user_id=target_user_id,
            detail={**detail, "by_platform_admin": True},
        )
    )


def add_project_member(
    session: Session, actor: User, project_id: uuid.UUID, *, email: str, role: str
) -> dict:
    authorize_platform(actor, "platform.projects.manage_access")
    project = _manageable_project(session, project_id)
    if role not in PROJECT_ROLES:
        raise AdminError("invalid_role")
    target = session.scalar(select(User).where(User.email == normalize_email(email)))
    if target is None or not target.is_active:
        raise AdminError("user_not_found")
    in_org = session.scalar(
        select(Membership.id).where(
            Membership.organization_id == project.organization_id,
            Membership.user_id == target.id,
        )
    )
    if not in_org:
        # Access never crosses tenants: the user must already belong to the organization.
        raise AdminError("user_not_in_organization")
    if session.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == target.id
        )
    ):
        raise AdminError("already_member")
    session.add(
        ProjectMember(
            project_id=project_id, user_id=target.id, role=role, added_by_user_id=actor.id
        )
    )
    _record_project_event(
        session, project_id, actor, "project.member_added", target.id, {"role": role}
    )
    _audit(
        session,
        actor,
        "admin.project_member_added",
        target_user_id=target.id,
        target_project_id=project_id,
        detail={"role": role},
    )
    session.commit()
    return {"user_id": str(target.id), "email": target.email, "role": role}


def change_project_member_role(
    session: Session, actor: User, project_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> dict:
    authorize_platform(actor, "platform.projects.manage_access")
    _manageable_project(session, project_id)
    if role not in PROJECT_ROLES:
        raise AdminError("invalid_role")
    member = _project_member(session, project_id, user_id)
    if member.role != role:
        if member.role == "owner" and _owner_count(session, project_id) <= 1:
            raise AdminError("last_owner")
        previous = member.role
        member.role = role
        _record_project_event(
            session,
            project_id,
            actor,
            "project.member_role_changed",
            user_id,
            {"from": previous, "to": role},
        )
        _audit(
            session,
            actor,
            "admin.project_member_role_changed",
            target_user_id=user_id,
            target_project_id=project_id,
            detail={"from": previous, "to": role},
        )
        session.commit()
    return {"user_id": str(user_id), "role": role}


def remove_project_member(
    session: Session, actor: User, project_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    authorize_platform(actor, "platform.projects.manage_access")
    _manageable_project(session, project_id)
    member = _project_member(session, project_id, user_id)
    if member.role == "owner" and _owner_count(session, project_id) <= 1:
        raise AdminError("last_owner")
    role = member.role
    session.delete(member)
    _record_project_event(
        session, project_id, actor, "project.member_removed", user_id, {"role": role}
    )
    _audit(
        session,
        actor,
        "admin.project_member_removed",
        target_user_id=user_id,
        target_project_id=project_id,
        detail={"role": role},
    )
    session.commit()


def list_audit(
    session: Session, actor: User, *, limit: int = 100, before_id: int | None = None
) -> list[dict]:
    authorize_platform(actor, "platform.audit.view")
    statement = select(AdminAuditEvent).order_by(AdminAuditEvent.id.desc())
    if before_id is not None:
        statement = statement.where(AdminAuditEvent.id < before_id)
    rows = list(session.scalars(statement.limit(max(1, min(limit, 500)))))
    ids = {row.actor_user_id for row in rows} | {
        row.target_user_id for row in rows if row.target_user_id
    }
    emails = {user.id: user.email for user in session.scalars(select(User).where(User.id.in_(ids)))}
    return [
        {
            "id": row.id,
            "action": row.action,
            "actor_user_id": str(row.actor_user_id),
            "actor_email": emails.get(row.actor_user_id),
            "target_user_id": str(row.target_user_id) if row.target_user_id else None,
            "target_email": emails.get(row.target_user_id) if row.target_user_id else None,
            "target_project_id": str(row.target_project_id) if row.target_project_id else None,
            "detail": row.detail,
            "created_at": _iso(row.created_at),
        }
        for row in rows
    ]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
