import unittest

from smart_engineer_api.permissions import (
    org_role_can,
    platform_can,
    project_role_can,
)

PROJECT_ROLES = ("owner", "architect", "structural_engineer", "mep_engineer", "quantity_surveyor")
ROLES = (*PROJECT_ROLES, "system_admin")

# Literal expectation, written independently of the implementation (ROLE-001).
EXPECTED_PROJECT_ALLOWED = {
    "project.view": set(PROJECT_ROLES),
    "project.update": {"owner", "architect"},
    "project.archive": {"owner"},
    "project.restore": {"owner"},
    "project.members.manage": {"owner"},
    "project.intake.edit": {"owner"},
    "project.site.edit": {"owner", "architect"},
    "project.zoning.edit": {"owner", "architect"},
    "project.requirements.edit": {"owner", "architect"},
    "project.design.edit": {"owner", "architect"},
    "project.environment.edit": {"owner", "architect", "structural_engineer", "mep_engineer"},
    "project.files.upload": {"owner", "architect", "structural_engineer", "mep_engineer"},
    "project.files.set_basis": {"owner", "quantity_surveyor"},
    "project.files.delete": {"owner", "architect"},
    "project.architect_input.edit": {"architect"},
    "project.space_review": {"architect"},
    "project.structural_input.edit": {"structural_engineer"},
    "project.mep_input.edit": {"mep_engineer"},
    "project.estimate.edit": {"quantity_surveyor"},
}
EXPECTED_ORG_ALLOWED = {
    "org.view": {"owner", "admin", "member"},
    "org.projects.create": {"owner", "admin", "member"},
    "org.archived_projects.view": {"owner", "admin"},
    "org.members.view": {"owner", "admin", "member"},
    "org.members.invite": {"owner", "admin"},
    "org.members.remove": {"owner", "admin"},
    "org.members.change_role": {"owner"},
    "org.data.export": {"owner"},
    "org.data.delete": {"owner"},
}


class PermissionMatrixTests(unittest.TestCase):
    def test_every_role_and_project_action_matches_the_recorded_matrix(self) -> None:
        for action, allowed in EXPECTED_PROJECT_ALLOWED.items():
            for role in ROLES:
                with self.subTest(action=action, role=role):
                    self.assertEqual(project_role_can(role, action), role in allowed)

    def test_system_admin_has_no_implicit_project_rights(self) -> None:
        for action in EXPECTED_PROJECT_ALLOWED:
            self.assertFalse(project_role_can("system_admin", action))
        self.assertTrue(platform_can(True, "platform.users.view"))
        self.assertFalse(platform_can(False, "platform.users.view"))
        self.assertFalse(platform_can(True, "project.view"))
        for action in (
            "platform.users.manage",
            "platform.admins.manage",
            "platform.projects.view",
            "platform.projects.manage_access",
            "platform.audit.view",
        ):
            self.assertTrue(platform_can(True, action), action)
            self.assertFalse(platform_can(False, action), action)
        # The platform role never gains project content rights.
        self.assertFalse(platform_can(True, "project.requirements.edit"))

    def test_unassigned_and_unknown_are_denied(self) -> None:
        for action in EXPECTED_PROJECT_ALLOWED:
            self.assertFalse(project_role_can(None, action))
        self.assertFalse(project_role_can("owner", "project.unknown"))
        self.assertFalse(org_role_can(None, "org.view"))

    def test_organization_matrix(self) -> None:
        for action, allowed in EXPECTED_ORG_ALLOWED.items():
            for role in ("owner", "admin", "member"):
                with self.subTest(action=action, role=role):
                    self.assertEqual(org_role_can(role, action), role in allowed)


if __name__ == "__main__":
    unittest.main()
