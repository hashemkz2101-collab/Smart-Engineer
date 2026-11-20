"""Resolve what a user may do on an organization or project (IAM-002)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Membership, Project, ProjectMember, User
from .permissions import AccessDenied, org_role_can, project_role_can

ARCHIVE_RECOVERY_ACTIONS = frozenset({"project.view", "project.restore"})


def org_role_of(session: Session, user: User, organization_id: uuid.UUID) -> str | None:
    return session.scalar(
        select(Membership.org_role).where(
            Membership.organization_id == organization_id, Membership.user_id == user.id
        )
    )


def project_role_of(session: Session, user: User, project_id: uuid.UUID) -> str | None:
    return session.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
        )
    )


def authorize_org(
    session: Session, user: User, organization_id: uuid.UUID, action: str
) -> str:
    """Return the caller's organization role or raise AccessDenied.

    Non-members get a hidden denial so other tenants cannot probe for existence.
    """
    role = org_role_of(session, user, organization_id)
    if role is None:
        raise AccessDenied(action, hidden=True)
    if not org_role_can(role, action):
        raise AccessDenied(action)
    return role


def authorize_project(
    session: Session, user: User, project_id: uuid.UUID, action: str
) -> tuple[Project, str]:
    """Return (project, caller's project role) or raise AccessDenied.

    A caller with no project role is denied as if the project did not exist, so
    other tenants and unassigned users cannot discover it. Organization owners
    and admins see an archived-projects list at the organization level, but they
    hold no project actions unless they are also project members.
    """
    project = session.get(Project, project_id)
    if project is None:
        raise AccessDenied(action, hidden=True)
    role = project_role_of(session, user, project_id)
    if (
        project.status == "archived"
        and action in ARCHIVE_RECOVERY_ACTIONS
        and org_role_of(session, user, project.organization_id) in ("owner", "admin")
    ):
        # Archive policy (DEC-016): organization owners/admins can retrieve and
        # restore archived projects even without a project role.
        return project, role or "org_admin"
    if role is None:
        raise AccessDenied(action, hidden=True)
    if not project_role_can(role, action):
        raise AccessDenied(action)
    if project.status == "archived" and action not in ARCHIVE_RECOVERY_ACTIONS:
        # Archived projects are read-only (DEC-016).
        raise AccessDenied(action)
    return project, role
