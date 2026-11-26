import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import admin_service, org_service, project_service
from smart_engineer_api import auth_service as auth
from smart_engineer_api.config import Settings
from smart_engineer_api.db import AdminAuditEvent, Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"


class AdminChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.session = create_session_factory(self.engine)()
        self.addCleanup(self.session.close)

    def user(self, name: str):
        return auth.register(
            self.session, POLICY, email=f"{name}@example.com", display_name=name, password=PASSWORD
        )

    def admin(self, name: str = "root"):
        user = self.user(name)
        admin_service.grant_first_admin(self.session, user.email)
        return user

    def org_of(self, user):
        return self.session.scalar(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )

    def project(self, owner):
        return project_service.create_project(
            self.session, owner, self.org_of(owner), name="House", project_type="residential_house"
        )

    def join_org(self, owner, person) -> None:
        _, token = org_service.create_invitation(
            self.session, owner, self.org_of(owner), email=person.email, org_role="member"
        )
        org_service.accept_invitation(self.session, person, token)

    def audit_actions(self) -> list[str]:
        return list(
            self.session.scalars(select(AdminAuditEvent.action).order_by(AdminAuditEvent.id))
        )

    def test_non_admins_are_hidden_from_every_operation(self) -> None:
        ordinary, other = self.user("ordinary"), self.user("other")
        project = self.project(ordinary)
        calls = (
            lambda: admin_service.list_users(self.session, ordinary),
            lambda: admin_service.set_user_active(self.session, ordinary, other.id, False),
            lambda: admin_service.set_system_admin(self.session, ordinary, other.id, True),
            lambda: admin_service.list_projects(self.session, ordinary),
            lambda: admin_service.list_project_access(self.session, ordinary, project.id),
            lambda: admin_service.add_project_member(
                self.session, ordinary, project.id, email=other.email, role="architect"
            ),
            lambda: admin_service.list_audit(self.session, ordinary),
        )
        for call in calls:
            with self.assertRaises(AccessDenied) as denied:
                call()
            self.assertTrue(denied.exception.hidden)
        self.assertEqual(self.audit_actions(), [])

    def test_bootstrap_grants_once_and_is_audited(self) -> None:
        person = self.user("first")
        admin_service.grant_first_admin(self.session, "FIRST@example.com")
        admin_service.grant_first_admin(self.session, person.email)
        self.assertEqual(self.audit_actions(), ["admin.system_admin_granted"])
        event = self.session.scalar(select(AdminAuditEvent))
        self.assertEqual(event.detail, {"via": "command_line"})
        with self.assertRaises(admin_service.AdminError) as missing:
            admin_service.grant_first_admin(self.session, "nobody@example.com")
        self.assertEqual(missing.exception.code, "not_found")

    def test_deactivation_blocks_login_revokes_sessions_and_reactivation_restores(self) -> None:
        root, target = self.admin(), self.user("target")
        auth.login(self.session, POLICY, email=target.email, password=PASSWORD)
        admin_service.set_user_active(self.session, root, target.id, False)
        with self.assertRaises(Exception):  # noqa: B017 - inactive accounts are refused
            auth.login(self.session, POLICY, email=target.email, password=PASSWORD)
        admin_service.set_user_active(self.session, root, target.id, True)
        auth.login(self.session, POLICY, email=target.email, password=PASSWORD)
        self.assertEqual(
            self.audit_actions()[1:], ["admin.user_deactivated", "admin.user_activated"]
        )

    def test_self_change_and_last_admin_are_refused(self) -> None:
        root, second = self.admin("root"), self.admin("second")
        for call in (
            lambda: admin_service.set_user_active(self.session, root, root.id, False),
            lambda: admin_service.set_system_admin(self.session, root, root.id, False),
        ):
            with self.assertRaises(admin_service.AdminError) as refused:
                call()
            self.assertEqual(refused.exception.code, "cannot_change_self")
        admin_service.set_system_admin(self.session, root, second.id, False)
        with self.assertRaises(AccessDenied) as demoted:
            admin_service.set_system_admin(self.session, second, root.id, False)
        self.assertTrue(demoted.exception.hidden)
        # The last-admin guard is defence in depth: an acting admin is always active, so a
        # different target can never be the only active admin; the self rule covers the rest.
        self.assertEqual(
            admin_service.list_users(self.session, root, query="second")[0]["is_system_admin"],
            False,
        )

    def test_grant_requires_active_user_and_listing_filters(self) -> None:
        root, target = self.admin(), self.user("target")
        admin_service.set_user_active(self.session, root, target.id, False)
        with self.assertRaises(admin_service.AdminError) as inactive:
            admin_service.set_system_admin(self.session, root, target.id, True)
        self.assertEqual(inactive.exception.code, "user_inactive")
        found = admin_service.list_users(self.session, root, query="TARG")
        self.assertEqual([u["email"] for u in found], ["target@example.com"])
        self.assertFalse(found[0]["is_active"])

    def test_project_access_management_is_scoped_audited_and_keeps_an_owner(self) -> None:
        root, owner, arch, outsider = (
            self.admin(),
            self.user("owner"),
            self.user("arch"),
            self.user("out"),
        )
        project = self.project(owner)
        listed = admin_service.list_projects(self.session, root)
        self.assertEqual([(p["name"], p["member_count"]) for p in listed], [("House", 1)])
        self.assertNotIn("data", listed[0])
        with self.assertRaises(admin_service.AdminError) as cross:
            admin_service.add_project_member(
                self.session, root, project.id, email=outsider.email, role="architect"
            )
        self.assertEqual(cross.exception.code, "user_not_in_organization")
        self.join_org(owner, arch)
        admin_service.add_project_member(
            self.session, root, project.id, email=arch.email, role="architect"
        )
        with self.assertRaises(admin_service.AdminError) as twice:
            admin_service.add_project_member(
                self.session, root, project.id, email=arch.email, role="architect"
            )
        self.assertEqual(twice.exception.code, "already_member")
        with self.assertRaises(admin_service.AdminError) as bad_role:
            admin_service.change_project_member_role(
                self.session, root, project.id, arch.id, "emperor"
            )
        self.assertEqual(bad_role.exception.code, "invalid_role")
        admin_service.change_project_member_role(
            self.session, root, project.id, arch.id, "quantity_surveyor"
        )
        with self.assertRaises(admin_service.AdminError) as last_owner:
            admin_service.remove_project_member(self.session, root, project.id, owner.id)
        self.assertEqual(last_owner.exception.code, "last_owner")
        admin_service.remove_project_member(self.session, root, project.id, arch.id)
        access = admin_service.list_project_access(self.session, root, project.id)
        self.assertEqual([m["email"] for m in access], ["owner@example.com"])
        self.assertEqual(
            self.audit_actions()[1:],
            [
                "admin.project_member_added",
                "admin.project_member_role_changed",
                "admin.project_member_removed",
            ],
        )
        events = project_service.list_activity(self.session, owner, project.id)
        self.assertTrue(all(e.detail.get("by_platform_admin") for e in events[-3:]))

    def test_archived_project_access_is_read_only_and_unknown_ids_are_not_found(self) -> None:
        root, owner, arch = self.admin(), self.user("owner"), self.user("arch")
        project = self.project(owner)
        self.join_org(owner, arch)
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(admin_service.AdminError) as archived:
            admin_service.add_project_member(
                self.session, root, project.id, email=arch.email, role="architect"
            )
        self.assertEqual(archived.exception.code, "project_archived")
        with self.assertRaises(admin_service.AdminError) as unknown:
            admin_service.list_project_access(self.session, root, owner.id)
        self.assertEqual(unknown.exception.code, "not_found")

    def test_audit_lists_newest_first_with_emails_and_pages(self) -> None:
        root, target = self.admin(), self.user("target")
        admin_service.set_user_active(self.session, root, target.id, False)
        admin_service.set_user_active(self.session, root, target.id, True)
        events = admin_service.list_audit(self.session, root)
        self.assertEqual(
            [e["action"] for e in events],
            ["admin.user_activated", "admin.user_deactivated", "admin.system_admin_granted"],
        )
        self.assertEqual(events[0]["actor_email"], "root@example.com")
        self.assertEqual(events[0]["target_email"], "target@example.com")
        older = admin_service.list_audit(self.session, root, before_id=events[0]["id"], limit=1)
        self.assertEqual([e["id"] for e in older], [events[1]["id"]])

    def test_http_flow_and_hidden_for_ordinary_users(self) -> None:
        root, target = self.admin(), self.user("target")
        app = create_app(
            Settings(environment="test"),
            session_factory=create_session_factory(self.engine),
            auth_policy=POLICY,
        )
        client = TestClient(app)
        self.addCleanup(client.close)

        def sign_in(email: str) -> dict:
            token = client.post(
                f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
            ).json()["csrf_token"]
            return {"X-CSRF-Token": token}

        headers = sign_in(target.email)
        self.assertEqual(client.get(f"{V1}/admin/users").status_code, 404)
        self.assertEqual(client.get(f"{V1}/admin/audit").status_code, 404)
        client.post(f"{V1}/auth/logout", headers=headers)

        headers = sign_in(root.email)
        users = client.get(f"{V1}/admin/users").json()["users"]
        self.assertEqual({u["email"] for u in users}, {"root@example.com", "target@example.com"})
        self.assertEqual(
            client.put(f"{V1}/admin/users/{target.id}/active", json={"active": False}).status_code,
            403,
        )
        off = client.put(
            f"{V1}/admin/users/{target.id}/active", headers=headers, json={"active": False}
        )
        self.assertEqual((off.status_code, off.json()["user"]["is_active"]), (200, False))
        self_change = client.put(
            f"{V1}/admin/users/{root.id}/system-admin",
            headers=headers,
            json={"is_system_admin": False},
        )
        self.assertEqual(
            (self_change.status_code, self_change.json()["error"]["code"]),
            (409, "cannot_change_self"),
        )
        events = client.get(f"{V1}/admin/audit").json()["events"]
        self.assertEqual(events[0]["action"], "admin.user_deactivated")
        self.assertEqual(client.get(f"{V1}/admin/projects").json(), {"projects": []})


class SqliteAdminTests(AdminChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresAdminTests(AdminChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlAdminTests(AdminChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
