"""Projects, project members, and activity history (PRJ-001, PRJ-002, FLOW-001).

Every state change writes an ``ActivityEvent`` in the same transaction as the
change itself, so history can never disagree with the data. Functions commit
their own work, like the other services.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .access import authorize_org, authorize_project
from .auth_service import utcnow
from .db import ActivityEvent, Membership, Project, ProjectMember, User
from .roles import PROJECT_ROLES, PROJECT_TYPES
from .security import normalize_email


class ProjectError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _record(
    session: Session,
    project_id: uuid.UUID,
    actor: User,
    action: str,
    *,
    target_user_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> None:
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action=action,
            target_user_id=target_user_id,
            detail=detail,
        )
    )


def _clean_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 200:
        raise ProjectError("invalid_name")
    return name


def create_project(
    session: Session,
    actor: User,
    organization_id: uuid.UUID,
    *,
    name: str,
    project_type: str,
    description: str | None = None,
) -> Project:
    authorize_org(session, actor, organization_id, "org.projects.create")
    name = _clean_name(name)
    if project_type not in PROJECT_TYPES:
        raise ProjectError("invalid_project_type")
    project = Project(
        organization_id=organization_id,
        name=name,
        project_type=project_type,
        description=(description or "").strip() or None,
        created_by_user_id=actor.id,
    )
    session.add(project)
    session.flush()
    session.add(
        ProjectMember(
            project_id=project.id, user_id=actor.id, role="owner", added_by_user_id=actor.id
        )
    )
    _record(session, project.id, actor, "project.created", detail={"name": name})
    session.commit()
    return project


def list_projects(
    session: Session,
    actor: User,
    *,
    organization_id: uuid.UUID | None = None,
    archived: bool = False,
) -> list[Project]:
    """Only projects the caller may see (PRJ-001).

    Active list: projects where the caller has a project role. Archived list
    (DEC-016): archived projects the caller owns, plus every archived project of
    organizations where the caller is owner or admin.
    """
    status = "archived" if archived else "active"
    on_project = select(ProjectMember.project_id).where(ProjectMember.user_id == actor.id)
    statement = select(Project).where(Project.status == status)
    if archived:
        owned = select(ProjectMember.project_id).where(
            ProjectMember.user_id == actor.id, ProjectMember.role == "owner"
        )
        managed = select(Membership.organization_id).where(
            Membership.user_id == actor.id, Membership.org_role.in_(("owner", "admin"))
        )
        statement = statement.where(
            or_(Project.id.in_(owned), Project.organization_id.in_(managed))
        )
    else:
        statement = statement.where(Project.id.in_(on_project))
    if organization_id is not None:
        statement = statement.where(Project.organization_id == organization_id)
    return list(session.scalars(statement.order_by(Project.created_at.desc(), Project.id)))


def update_project(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    *,
    name: str | None = None,
    project_type: str | None = None,
    description: str | None = None,
) -> Project:
    project, _ = authorize_project(session, actor, project_id, "project.update")
    changed: list[str] = []
    if name is not None:
        new_name = _clean_name(name)
        if new_name != project.name:
            project.name = new_name
            changed.append("name")
    if project_type is not None:
        if project_type not in PROJECT_TYPES:
            raise ProjectError("invalid_project_type")
        if project_type != project.project_type:
            project.project_type = project_type
            changed.append("project_type")
    if description is not None:
        new_description = description.strip() or None
        if new_description != project.description:
            project.description = new_description
            changed.append("description")
    if changed:
        _record(session, project.id, actor, "project.updated", detail={"fields": changed})
        session.commit()
    return project


def archive_project(session: Session, actor: User, project_id: uuid.UUID) -> Project:
    project, _ = authorize_project(session, actor, project_id, "project.archive")
    project.status = "archived"
    project.archived_at = utcnow()
    project.archived_by_user_id = actor.id
    _record(session, project.id, actor, "project.archived")
    session.commit()
    return project


def restore_project(session: Session, actor: User, project_id: uuid.UUID) -> Project:
    project, _ = authorize_project(session, actor, project_id, "project.restore")
    if project.status != "archived":
        raise ProjectError("not_archived")
    project.status = "active"
    project.archived_at = None
    project.archived_by_user_id = None
    _record(session, project.id, actor, "project.restored")
    session.commit()
    return project


def list_project_members(
    session: Session, actor: User, project_id: uuid.UUID
) -> list[tuple[User, str]]:
    authorize_project(session, actor, project_id, "project.view")
    rows = session.execute(
        select(User, ProjectMember.role)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.email)
    ).all()
    return [(user, role) for user, role in rows]


def add_member(
    session: Session, actor: User, project_id: uuid.UUID, *, email: str, role: str
) -> ProjectMember:
    """Grant a project-scoped role to someone already in the project's organization."""
    project, _ = authorize_project(session, actor, project_id, "project.members.manage")
    if role not in PROJECT_ROLES:
        raise ProjectError("invalid_role")
    target = session.scalar(select(User).where(User.email == normalize_email(email)))
    in_org = target is not None and session.scalar(
        select(Membership.id).where(
            Membership.organization_id == project.organization_id,
            Membership.user_id == target.id,
        )
    )
    if not in_org:
        raise ProjectError("user_not_in_organization")
    if session.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == target.id
        )
    ):
        raise ProjectError("already_member")
    member = ProjectMember(
        project_id=project_id, user_id=target.id, role=role, added_by_user_id=actor.id
    )
    session.add(member)
    _record(
        session, project_id, actor, "project.member_added",
        target_user_id=target.id, detail={"role": role},
    )
    session.commit()
    return member


def _member(session: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectMember:
    member = session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    if member is None:
        raise ProjectError("not_found")
    return member


def _owner_count(session: Session, project_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id, ProjectMember.role == "owner")
    )


def change_member_role(
    session: Session, actor: User, project_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> ProjectMember:
    authorize_project(session, actor, project_id, "project.members.manage")
    if role not in PROJECT_ROLES:
        raise ProjectError("invalid_role")
    member = _member(session, project_id, user_id)
    if member.role == role:
        return member
    if member.role == "owner" and _owner_count(session, project_id) <= 1:
        raise ProjectError("last_owner")
    previous = member.role
    member.role = role
    _record(
        session, project_id, actor, "project.member_role_changed",
        target_user_id=user_id, detail={"from": previous, "to": role},
    )
    session.commit()
    return member


def remove_member(
    session: Session, actor: User, project_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    authorize_project(session, actor, project_id, "project.members.manage")
    member = _member(session, project_id, user_id)
    if member.role == "owner" and _owner_count(session, project_id) <= 1:
        raise ProjectError("last_owner")
    role = member.role
    session.delete(member)
    _record(
        session, project_id, actor, "project.member_removed",
        target_user_id=user_id, detail={"role": role},
    )
    session.commit()


def list_activity(
    session: Session, actor: User, project_id: uuid.UUID
) -> list[ActivityEvent]:
    authorize_project(session, actor, project_id, "project.view")
    return list(
        session.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.project_id == project_id)
            .order_by(ActivityEvent.id)
        )
    )
