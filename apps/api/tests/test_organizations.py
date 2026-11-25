import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import access, org_service
from smart_engineer_api import auth_service as auth
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Invitation, Membership, Project, ProjectMember
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
T0 = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


class OrgChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.factory = create_session_factory(self.engine)
        self.session = self.factory()
        self.addCleanup(self.session.close)

    def user(self, name: str):
        return auth.register(
            self.session, POLICY, email=f"{name}@example.com", display_name=name, password=PASSWORD
        )

    def org_of(self, user):
        return self.session.scalar(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )

    def join(self, owner, user, role="member"):
        _, token = org_service.create_invitation(
            self.session, owner, self.org_of(owner), email=user.email, org_role=role, now=T0
        )
        org_service.accept_invitation(self.session, user, token, now=T0)

    def project(self, owner, roles: dict | None = None, status="active") -> Project:
        project = Project(
            organization_id=self.org_of(owner),
            name="P",
            project_type="residential_house",
            created_by_user_id=owner.id,
            status=status,
            archived_at=T0 if status == "archived" else None,
        )
        self.session.add(project)
        self.session.flush()
        self.session.add(
            ProjectMember(
                project_id=project.id, user_id=owner.id, role="owner", added_by_user_id=owner.id
            )
        )
        for member, role in (roles or {}).items():
            self.session.add(
                ProjectMember(
                    project_id=project.id, user_id=member.id, role=role, added_by_user_id=owner.id
                )
            )
        self.session.commit()
        return project

    def denied(self, func, *args, **kwargs) -> AccessDenied:
        with self.assertRaises(AccessDenied) as context:
            func(*args, **kwargs)
        return context.exception

    def code(self, func, *args, **kwargs) -> str:
        with self.assertRaises(org_service.OrgError) as context:
            func(*args, **kwargs)
        return context.exception.code

    # project authorization ---------------------------------------------
    def test_project_access_follows_the_assigned_role(self) -> None:
        owner, arch, qs = self.user("owner"), self.user("arch"), self.user("qs")
        for member in (arch, qs):
            self.join(owner, member)
        project = self.project(owner, {arch: "architect", qs: "quantity_surveyor"})

        found, role = access.authorize_project(self.session, arch, project.id, "project.update")
        self.assertEqual((found.id, role), (project.id, "architect"))
        error = self.denied(access.authorize_project, self.session, qs, project.id, "project.update")
        self.assertFalse(error.hidden)  # a member learns the action is not allowed
        access.authorize_project(self.session, qs, project.id, "project.estimate.edit")

    def test_unassigned_users_and_other_tenants_cannot_see_the_project(self) -> None:
        owner, colleague, stranger = self.user("owner"), self.user("colleague"), self.user("stranger")
        self.join(owner, colleague)  # same organization, not on the project
        project = self.project(owner)

        for caller in (colleague, stranger):
            error = self.denied(
                access.authorize_project, self.session, caller, project.id, "project.view"
            )
            self.assertTrue(error.hidden)
        self.assertTrue(
            self.denied(
                access.authorize_project, self.session, owner, org_service.uuid.uuid4(), "project.view"
            ).hidden
        )

    def test_archived_projects_are_read_only_but_can_be_restored_by_the_owner(self) -> None:
        owner = self.user("owner")
        project = self.project(owner, status="archived")

        access.authorize_project(self.session, owner, project.id, "project.view")
        access.authorize_project(self.session, owner, project.id, "project.restore")
        for action in ("project.update", "project.intake.edit", "project.archive"):
            self.denied(access.authorize_project, self.session, owner, project.id, action)

    def test_organization_actions_require_membership_and_role(self) -> None:
        owner, member, stranger = self.user("owner"), self.user("member"), self.user("stranger")
        self.join(owner, member)
        org = self.org_of(owner)

        self.assertEqual(access.authorize_org(self.session, owner, org, "org.members.invite"), "owner")
        self.assertFalse(
            self.denied(access.authorize_org, self.session, member, org, "org.members.invite").hidden
        )
        self.assertTrue(
            self.denied(access.authorize_org, self.session, stranger, org, "org.view").hidden
        )

    # invitations -------------------------------------------------------
    def test_invitation_token_is_stored_hashed_and_is_single_use(self) -> None:
        owner, guest = self.user("owner"), self.user("guest")
        org = self.org_of(owner)
        invitation, token = org_service.create_invitation(
            self.session, owner, org, email="GUEST@example.com", org_role="member", now=T0
        )
        self.assertNotEqual(invitation.token_hash, token)

        membership = org_service.accept_invitation(self.session, guest, token, now=T0)
        self.assertEqual((membership.organization_id, membership.org_role), (org, "member"))
        self.assertEqual(self.code(org_service.accept_invitation, self.session, guest, token, now=T0),
                         "invalid_token")

    def test_invitation_rejects_wrong_account_expiry_and_garbage(self) -> None:
        owner, guest, other = self.user("owner"), self.user("guest"), self.user("other")
        org = self.org_of(owner)
        _, token = org_service.create_invitation(
            self.session, owner, org, email=guest.email, org_role="member", now=T0
        )
        accept = org_service.accept_invitation
        self.assertEqual(self.code(accept, self.session, other, token, now=T0), "invalid_token")
        late = T0 + org_service.INVITATION_TTL + timedelta(seconds=1)
        self.assertEqual(self.code(accept, self.session, guest, token, now=late), "invalid_token")
        self.assertEqual(self.code(accept, self.session, guest, "garbage", now=T0), "invalid_token")

    def test_inviting_rules(self) -> None:
        owner, admin, member = self.user("owner"), self.user("admin"), self.user("member")
        self.join(owner, admin, "admin")
        self.join(owner, member, "member")
        org = self.org_of(owner)
        create = org_service.create_invitation

        self.assertEqual(self.code(create, self.session, owner, org, email=member.email,
                                   org_role="member", now=T0), "already_member")
        self.assertEqual(self.code(create, self.session, owner, org, email="x@example.com",
                                   org_role="owner", now=T0), "invalid_role")
        self.assertEqual(self.code(create, self.session, owner, org, email="bad",
                                   org_role="member", now=T0), "invalid_email")
        create(self.session, admin, org, email="new@example.com", org_role="member", now=T0)
        self.denied(create, self.session, admin, org, email="n2@example.com",
                    org_role="admin", now=T0)
        self.denied(create, self.session, member, org, email="n3@example.com",
                    org_role="member", now=T0)

    def test_new_invitation_and_revocation_invalidate_earlier_tokens(self) -> None:
        owner, guest = self.user("owner"), self.user("guest")
        org = self.org_of(owner)
        _, first = org_service.create_invitation(
            self.session, owner, org, email=guest.email, org_role="member", now=T0
        )
        invitation, second = org_service.create_invitation(
            self.session, owner, org, email=guest.email, org_role="member", now=T0
        )
        accept = org_service.accept_invitation
        self.assertEqual(self.code(accept, self.session, guest, first, now=T0), "invalid_token")
        org_service.revoke_invitation(self.session, owner, org, invitation.id, now=T0)
        self.assertEqual(self.code(accept, self.session, guest, second, now=T0), "invalid_token")
        self.assertEqual(len(self.session.scalars(select(Invitation)).all()), 2)

    # roles and removal -------------------------------------------------
    def test_only_the_owner_changes_roles_and_ownership_is_fixed(self) -> None:
        owner, admin, member = self.user("owner"), self.user("admin"), self.user("member")
        self.join(owner, admin, "admin")
        self.join(owner, member)
        org = self.org_of(owner)

        changed = org_service.change_member_role(self.session, owner, org, member.id, "admin")
        self.assertEqual(changed.org_role, "admin")
        self.denied(org_service.change_member_role, self.session, admin, org, member.id, "member")
        self.assertEqual(
            self.code(org_service.change_member_role, self.session, owner, org, owner.id, "member"),
            "owner_role_fixed",
        )
        self.assertEqual(
            self.code(org_service.change_member_role, self.session, owner, org, member.id, "owner"),
            "invalid_role",
        )

    def test_removing_a_member_also_removes_their_project_roles(self) -> None:
        owner, arch = self.user("owner"), self.user("arch")
        self.join(owner, arch)
        project = self.project(owner, {arch: "architect"})
        org = self.org_of(owner)

        org_service.remove_member(self.session, owner, org, arch.id)

        self.assertIsNone(access.project_role_of(self.session, arch, project.id))
        self.assertIsNone(access.org_role_of(self.session, arch, org))
        self.assertTrue(
            self.denied(access.authorize_project, self.session, arch, project.id, "project.view").hidden
        )

    def test_owner_cannot_be_removed_and_admins_cannot_remove_admins(self) -> None:
        owner, admin, other_admin = self.user("owner"), self.user("admin"), self.user("admin2")
        self.join(owner, admin, "admin")
        self.join(owner, other_admin, "admin")
        org = self.org_of(owner)

        self.assertEqual(self.code(org_service.remove_member, self.session, admin, org, owner.id),
                         "cannot_remove_owner")
        self.denied(org_service.remove_member, self.session, admin, org, other_admin.id)
        org_service.remove_member(self.session, owner, org, other_admin.id)
        self.assertEqual(self.code(org_service.remove_member, self.session, owner, org, other_admin.id),
                         "not_found")

    def test_listing_is_scoped_to_the_callers_organizations(self) -> None:
        owner, stranger = self.user("owner"), self.user("stranger")
        org = self.org_of(owner)
        self.assertEqual([o.id for o, _ in org_service.list_user_organizations(self.session, owner)],
                         [org])
        self.assertEqual([u.id for u, _ in org_service.list_members(self.session, owner, org)],
                         [owner.id])
        self.assertTrue(self.denied(org_service.list_members, self.session, stranger, org).hidden)


class HttpOrgChecks:
    def http_client(self) -> TestClient:
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        app = create_app(
            Settings(environment="test"),
            session_factory=create_session_factory(engine),
            auth_policy=POLICY,
        )
        client = TestClient(app)
        self.addCleanup(client.close)
        return client

    def signed_in(self, name: str):
        client = self.http_client()
        email = f"{name}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "display_name": name, "password": PASSWORD},
        )
        csrf = client.post(
            "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
        ).json()["csrf_token"]
        orgs = client.get("/api/v1/orgs").json()["organizations"]
        return client, {"X-CSRF-Token": csrf}, orgs[0]["id"]

    def test_invite_accept_and_permission_flow_over_http(self) -> None:
        owner, owner_h, org = self.signed_in("owner")
        guest, guest_h, guest_org = self.signed_in("guest")

        invited = owner.post(
            f"/api/v1/orgs/{org}/invitations",
            json={"email": "guest@example.com", "org_role": "member"},
            headers=owner_h,
        )
        self.assertEqual(invited.status_code, 201)
        token = invited.json()["token"]

        self.assertEqual(
            guest.post("/api/v1/invitations/accept", json={"token": token}).status_code, 403
        )  # no CSRF header
        accepted = guest.post(
            "/api/v1/invitations/accept", json={"token": token}, headers=guest_h
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(len(guest.get("/api/v1/orgs").json()["organizations"]), 2)

        # A plain member can list members but may not invite.
        self.assertEqual(guest.get(f"/api/v1/orgs/{org}/members").status_code, 200)
        denied = guest.post(
            f"/api/v1/orgs/{org}/invitations",
            json={"email": "x@example.com"},
            headers=guest_h,
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["code"], "forbidden")
        self.assertNotEqual(guest_org, org)

    def test_other_tenants_and_anonymous_callers_get_no_information(self) -> None:
        owner, _, org = self.signed_in("owner")
        stranger, stranger_h, _ = self.signed_in("stranger")
        anonymous = self.http_client()

        self.assertEqual(anonymous.get(f"/api/v1/orgs/{org}/members").status_code, 401)
        self.assertEqual(stranger.get(f"/api/v1/orgs/{org}/members").status_code, 404)
        probe = stranger.post(
            f"/api/v1/orgs/{org}/invitations", json={"email": "a@example.com"}, headers=stranger_h
        )
        self.assertEqual(probe.status_code, 404)
        self.assertEqual(owner.get(f"/api/v1/orgs/{org}/members").status_code, 200)


class SqliteOrgTests(OrgChecks, HttpOrgChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresOrgTests(OrgChecks, HttpOrgChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlOrgTests(OrgChecks, HttpOrgChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
