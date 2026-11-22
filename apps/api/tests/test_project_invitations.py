import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import org_service, project_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Invitation, Membership, ProjectMember
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"


class InvitationChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.session = create_db_session(self.engine)
        self.addCleanup(self.session.close)

    def user(self, name: str):
        return auth.register(
            self.session, POLICY, email=f"{name}@example.com", display_name=name, password=PASSWORD
        )

    def org_of(self, user):
        return self.session.scalar(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )

    def project(self, owner):
        return project_service.create_project(
            self.session, owner, self.org_of(owner), name="House", project_type="residential_house"
        )

    def actions(self, owner, project) -> list[str]:
        return [e.action for e in project_service.list_activity(self.session, owner, project.id)]

    def test_invitee_has_no_access_until_accepting_then_gets_exactly_the_role(self) -> None:
        owner, guest = self.user("owner"), self.user("guest")
        project = self.project(owner)
        invitation, token = project_service.invite_to_project(
            self.session, owner, project.id, email="Guest@Example.com", role="architect"
        )
        self.assertEqual((invitation.project_role, invitation.org_role), ("architect", "member"))
        with self.assertRaises(AccessDenied) as before:
            project_service.list_activity(self.session, guest, project.id)
        self.assertTrue(before.exception.hidden)

        _, project_id = org_service.accept_invitation_scoped(self.session, guest, token)
        self.assertEqual(project_id, project.id)
        role = self.session.scalar(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project.id, ProjectMember.user_id == guest.id
            )
        )
        self.assertEqual(role, "architect")
        org_role = self.session.scalar(
            select(Membership.org_role).where(
                Membership.organization_id == project.organization_id,
                Membership.user_id == guest.id,
            )
        )
        self.assertEqual(org_role, "member")
        # The architect can read the project but cannot manage members.
        project_service.list_activity(self.session, guest, project.id)
        with self.assertRaises(AccessDenied):
            project_service.invite_to_project(
                self.session, guest, project.id, email="x@example.com", role="architect"
            )
        self.assertEqual(
            self.actions(owner, project),
            ["project.created", "project.invitation_created", "project.invitation_accepted"],
        )
        accepted = project_service.list_activity(self.session, owner, project.id)[-1]
        self.assertEqual(
            (accepted.actor_user_id, accepted.target_user_id, accepted.detail["role"]),
            (guest.id, guest.id, "architect"),
        )
        with self.assertRaises(org_service.OrgError) as reused:
            org_service.accept_invitation_scoped(self.session, guest, token)
        self.assertEqual(reused.exception.code, "invalid_token")

    def test_wrong_account_revoked_expired_and_archived_all_look_invalid(self) -> None:
        owner, guest, other = self.user("owner"), self.user("guest"), self.user("other")
        project = self.project(owner)
        _, token = project_service.invite_to_project(
            self.session, owner, project.id, email=guest.email, role="quantity_surveyor"
        )
        with self.assertRaises(org_service.OrgError):
            org_service.accept_invitation_scoped(self.session, other, token)

        pending = project_service.list_project_invitations(self.session, owner, project.id)
        self.assertEqual(
            [(i.email, i.project_role) for i in pending], [(guest.email, "quantity_surveyor")]
        )
        project_service.revoke_project_invitation(self.session, owner, project.id, pending[0].id)
        with self.assertRaises(org_service.OrgError):
            org_service.accept_invitation_scoped(self.session, guest, token)
        self.assertEqual(
            project_service.list_project_invitations(self.session, owner, project.id), []
        )

        _, fresh = project_service.invite_to_project(
            self.session, owner, project.id, email=guest.email, role="architect"
        )
        later = auth.utcnow() + timedelta(days=8)
        with self.assertRaises(org_service.OrgError):
            org_service.accept_invitation_scoped(self.session, guest, fresh, now=later)
        self.assertEqual(
            project_service.list_project_invitations(self.session, owner, project.id, now=later), []
        )

        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(org_service.OrgError):
            org_service.accept_invitation_scoped(self.session, guest, fresh)
        self.assertIsNone(
            self.session.scalar(select(ProjectMember.id).where(ProjectMember.user_id == guest.id))
        )

    def test_a_new_invitation_replaces_the_old_one_and_validation_is_enforced(self) -> None:
        owner, guest, member = self.user("owner"), self.user("guest"), self.user("member")
        project = self.project(owner)
        _, first = project_service.invite_to_project(
            self.session, owner, project.id, email=guest.email, role="architect"
        )
        _, second = project_service.invite_to_project(
            self.session, owner, project.id, email=guest.email, role="mep_engineer"
        )
        with self.assertRaises(org_service.OrgError):
            org_service.accept_invitation_scoped(self.session, guest, first)
        org_service.accept_invitation_scoped(self.session, guest, second)
        role = self.session.scalar(
            select(ProjectMember.role).where(ProjectMember.user_id == guest.id)
        )
        self.assertEqual(role, "mep_engineer")
        for email, role_name, code in (
            ("nope", "architect", "invalid_email"),
            ("new@example.com", "emperor", "invalid_role"),
            (member.email, "architect", "already_in_organization"),
        ):
            with self.assertRaises(project_service.ProjectError) as bad:
                project_service.invite_to_project(
                    self.session, owner, project.id, email=email, role=role_name
                )
            self.assertEqual(bad.exception.code, code)

    def test_org_invitation_does_not_revoke_a_project_invitation_and_cannot_cross_projects(
        self,
    ) -> None:
        owner, guest, stranger = self.user("owner"), self.user("guest"), self.user("stranger")
        project, other = self.project(owner), self.project(stranger)
        _, token = project_service.invite_to_project(
            self.session, owner, project.id, email=guest.email, role="architect"
        )
        org_service.create_invitation(
            self.session, owner, self.org_of(owner), email=guest.email, org_role="member"
        )
        org_service.accept_invitation_scoped(self.session, guest, token)
        with self.assertRaises(AccessDenied) as foreign:
            project_service.invite_to_project(
                self.session, owner, other.id, email="a@example.com", role="architect"
            )
        self.assertTrue(foreign.exception.hidden)
        pending = project_service.list_project_invitations(self.session, owner, project.id)
        self.assertEqual(pending, [])
        with self.assertRaises(project_service.ProjectError) as wrong_project:
            project_service.revoke_project_invitation(
                self.session,
                stranger,
                other.id,
                self.session.scalar(select(Invitation.id)),
            )
        self.assertEqual(wrong_project.exception.code, "not_found")

    def test_http_flow(self) -> None:
        guest = self.user("guest")
        app = create_app(
            Settings(environment="test"),
            session_factory=create_session_factory(self.engine),
            auth_policy=POLICY,
        )
        owner_client, guest_client = TestClient(app), TestClient(app)
        self.addCleanup(owner_client.close)
        self.addCleanup(guest_client.close)
        owner_client.post(
            f"{V1}/auth/register",
            json={"email": "http@example.com", "display_name": "Http", "password": PASSWORD},
        )
        csrf = owner_client.post(
            f"{V1}/auth/login", json={"email": "http@example.com", "password": PASSWORD}
        ).json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        org = owner_client.get(f"{V1}/orgs").json()["organizations"][0]["id"]
        pid = owner_client.post(
            f"{V1}/projects",
            headers=headers,
            json={"organization_id": org, "name": "P", "project_type": "other"},
        ).json()["project"]["id"]
        url = f"{V1}/projects/{pid}/invitations"

        no_csrf = owner_client.post(url, json={"email": guest.email, "role": "architect"})
        self.assertEqual(no_csrf.status_code, 403)
        bad = owner_client.post(url, headers=headers, json={"email": guest.email, "role": "x"})
        self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (422, "invalid_role"))
        created = owner_client.post(
            url, headers=headers, json={"email": guest.email, "role": "architect"}
        )
        self.assertEqual(created.status_code, 201)
        token = created.json()["token"]
        listed = owner_client.get(url).json()["invitations"]
        self.assertEqual([(i["email"], i["role"]) for i in listed], [(guest.email, "architect")])
        self.assertNotIn("token", listed[0])

        guest_csrf = guest_client.post(
            f"{V1}/auth/login", json={"email": guest.email, "password": PASSWORD}
        ).json()["csrf_token"]
        self.assertEqual(guest_client.get(f"{V1}/projects/{pid}").status_code, 404)
        self.assertEqual(guest_client.get(url).status_code, 404)
        accepted = guest_client.post(
            f"{V1}/invitations/accept", headers={"X-CSRF-Token": guest_csrf}, json={"token": token}
        )
        self.assertEqual((accepted.status_code, accepted.json()["project_id"]), (200, pid))
        self.assertEqual(guest_client.get(f"{V1}/projects/{pid}").json()["my_role"], "architect")
        self.assertEqual(guest_client.get(url).status_code, 403)

        again = owner_client.post(
            url, headers=headers, json={"email": guest.email, "role": "architect"}
        )
        self.assertEqual(
            (again.status_code, again.json()["error"]["code"]), (409, "already_in_organization")
        )


def create_db_session(engine):
    return create_session_factory(engine)()


class SqliteInvitationTests(InvitationChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresInvitationTests(InvitationChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
