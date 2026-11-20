"""Role/permission matrix for Phase 1 (IAM-002, ROLE-001).

Decisions are made on the backend only; the UI may hide controls but never
decides. Project actions depend on the user's role *on that project*; the system
administrator is a platform flag and has no implicit project rights. Organization
actions depend on the organization role (owner / admin / member).
"""

PROJECT_ACTION_ROLES: dict[str, frozenset[str]] = {
    "project.view": frozenset(
        {"owner", "architect", "structural_engineer", "mep_engineer", "quantity_surveyor"}
    ),
    "project.update": frozenset({"owner", "architect"}),
    "project.archive": frozenset({"owner"}),
    "project.restore": frozenset({"owner"}),
    "project.members.manage": frozenset({"owner"}),
    "project.intake.edit": frozenset({"owner"}),
    "project.architect_input.edit": frozenset({"architect"}),
    "project.space_review": frozenset({"architect"}),
    "project.structural_input.edit": frozenset({"structural_engineer"}),
    "project.mep_input.edit": frozenset({"mep_engineer"}),
    "project.estimate.edit": frozenset({"quantity_surveyor"}),
}

ORG_ACTION_ROLES: dict[str, frozenset[str]] = {
    "org.view": frozenset({"owner", "admin", "member"}),
    "org.projects.create": frozenset({"owner", "admin", "member"}),
    "org.archived_projects.view": frozenset({"owner", "admin"}),
    "org.members.view": frozenset({"owner", "admin", "member"}),
    "org.members.invite": frozenset({"owner", "admin"}),
    "org.members.remove": frozenset({"owner", "admin"}),
    "org.members.change_role": frozenset({"owner"}),
    "org.data.export": frozenset({"owner"}),
    "org.data.delete": frozenset({"owner"}),
}

# Platform-level actions available only through the is_system_admin flag.
PLATFORM_ACTIONS = frozenset({"platform.users.view", "platform.feature_flags.manage"})


class AccessDenied(Exception):
    """The caller may not perform the action.

    ``hidden`` means the caller must not even learn the resource exists (the
    HTTP layer then answers 404 instead of 403).
    """

    def __init__(self, action: str, hidden: bool = False) -> None:
        super().__init__(action)
        self.action = action
        self.hidden = hidden


def project_role_can(role: str | None, action: str) -> bool:
    return role is not None and role in PROJECT_ACTION_ROLES.get(action, frozenset())


def org_role_can(org_role: str | None, action: str) -> bool:
    return org_role is not None and org_role in ORG_ACTION_ROLES.get(action, frozenset())


def platform_can(is_system_admin: bool, action: str) -> bool:
    return is_system_admin and action in PLATFORM_ACTIONS
