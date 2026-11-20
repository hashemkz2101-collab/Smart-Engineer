import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import access, org_service, project_service
from smart_engineer_api import auth_service as auth
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.project_service import ProjectError
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"


class ProjectChecks:
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

    def org_of(self, user):
        return self.session.scalar(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )

    def join(self, owner, user, role="member"):
        _, token = org_service.create_invitation(
            self.session, owner, self.org_of(owner), email=user.email, org_role=role
        )
        org_service.accept_invitation(self.session, user, token)

    def make(self, owner, **overrides):
        values = {"name": "House", "project_type": "residential_house"}
        values.update(overrides)
        return project_service.create_project(self.session, owner, self.org_of(owner), **values)

    def actions(self, user, project):
        return [e.action for e in project_service.list_activity(self.session, user, project.id)]

    def denied(self, func, *args, **kwargs) -> AccessDenied:
        with self.assertRaises(AccessDenied) as context:
            func(*args, **kwargs)
        return context.exception

    def code(self, func, *args, **kwargs) -> str:
        with self.assertRaises(ProjectError) as context:
            func(*args, **kwargs)
        return context.exception.code

    # creation and listing ------------------------------------------------
    def test_create_makes_the_creator_owner_and_records_activity(self) -> None:
        owner = self.user("owner")
        project = self.make(owner, description="  two floors ")

        self.assertEqual((project.status, project.description), ("active", "two floors"))
        self.assertEqual(access.project_role_of(self.session, owner, project.id), "owner")
        self.assertEqual(self.actions(owner, project), ["project.created"])

    def test_create_validates_input_and_organization_access(self) -> None:
        owner, stranger = self.user("owner"), self.user("stranger")
        self.assertEqual(self.code(self.make, owner, name="   "), "invalid_name")
        self.assertEqual(self.code(self.make, owner, project_type="castle"), "invalid_project_type")
        error = self.denied(
            project_service.create_project, self.session, stranger, self.org_of(owner),
            name="X", project_type="other",
        )
        self.assertTrue(error.hidden)

    def test_lists_show_only_the_callers_authorized_projects(self) -> None:
        owner, colleague, stranger = self.user("owner"), self.user("colleague"), self.user("stranger")
        self.join(owner, colleague)
        mine = self.make(owner)
        theirs = self.make(colleague, name="Colleague house")
        lists = project_service.list_projects

        self.assertEqual({p.id for p in lists(self.session, owner)}, {mine.id})
        self.assertEqual({p.id for p in lists(self.session, colleague)}, {theirs.id})
        self.assertEqual(lists(self.session, stranger), [])

    def test_archived_projects_leave_the_active_list_and_follow_the_archive_policy(self) -> None:
        owner, admin, member = self.user("owner"), self.user("admin"), self.user("member")
        self.join(owner, admin, "admin")
        self.join(owner, member)
        project = self.make(member)  # created by a plain member, who becomes project owner
        project_service.archive_project(self.session, member, project.id)
        lists = project_service.list_projects

        self.assertEqual(lists(self.session, member), [])
        self.assertEqual([p.id for p in lists(self.session, member, archived=True)], [project.id])
        self.assertEqual([p.id for p in lists(self.session, admin, archived=True)], [project.id])
        self.assertEqual([p.id for p in lists(self.session, owner, archived=True)], [project.id])
        other = self.make(owner, name="Active one")
        self.assertEqual([p.id for p in lists(self.session, owner)], [other.id])

    # update --------------------------------------------------------------
    def test_update_is_role_checked_and_recorded_without_noise(self) -> None:
        owner, arch, qs = self.user("owner"), self.user("arch"), self.user("qs")
        for member in (arch, qs):
            self.join(owner, member)
        project = self.make(owner)
        project_service.add_member(self.session, owner, project.id, email=arch.email, role="architect")
        project_service.add_member(
            self.session, owner, project.id, email=qs.email, role="quantity_surveyor"
        )

        project_service.update_project(self.session, arch, project.id, name="Villa")
        project_service.update_project(self.session, arch, project.id, name="Villa")  # no change
        self.denied(project_service.update_project, self.session, qs, project.id, name="Hack")
        self.assertEqual(self.code(project_service.update_project, self.session, arch, project.id,
                                   project_type="castle"), "invalid_project_type")
        events = project_service.list_activity(self.session, owner, project.id)
        updates = [e for e in events if e.action == "project.updated"]
        self.assertEqual(len(updates), 1)
        self.assertEqual((updates[0].actor_user_id, updates[0].detail), (arch.id, {"fields": ["name"]}))

    # archive -------------------------------------------------------------
    def test_archive_is_owner_only_read_only_and_restorable(self) -> None:
        owner, arch, admin = self.user("owner"), self.user("arch"), self.user("admin")
        self.join(owner, arch)
        self.join(owner, admin, "admin")
        project = self.make(owner)
        project_service.add_member(self.session, owner, project.id, email=arch.email, role="architect")

        self.denied(project_service.archive_project, self.session, arch, project.id)
        project_service.archive_project(self.session, owner, project.id)
        self.denied(project_service.update_project, self.session, owner, project.id, name="Nope")
        self.denied(project_service.add_member, self.session, owner, project.id,
                    email=admin.email, role="architect")
        access.authorize_project(self.session, arch, project.id, "project.view")  # still readable

        # An organization admin without a project role may retrieve and restore it.
        access.authorize_project(self.session, admin, project.id, "project.view")
        self.denied(project_service.update_project, self.session, admin, project.id, name="Nope")
        restored = project_service.restore_project(self.session, admin, project.id)
        self.assertEqual((restored.status, restored.archived_at), ("active", None))
        self.assertEqual(self.code(project_service.restore_project, self.session, owner, project.id),
                         "not_archived")
        events = project_service.list_activity(self.session, owner, project.id)
        self.assertEqual([e.action for e in events][-2:], ["project.archived", "project.restored"])
        self.assertEqual(events[-1].actor_user_id, admin.id)

    # members -------------------------------------------------------------
    def test_member_changes_follow_the_rules_and_are_recorded(self) -> None:
        owner, arch, outsider = self.user("owner"), self.user("arch"), self.user("outsider")
        self.join(owner, arch)
        project = self.make(owner)
        add = project_service.add_member

        self.assertEqual(self.code(add, self.session, owner, project.id, email=outsider.email,
                                   role="architect"), "user_not_in_organization")
        self.assertEqual(self.code(add, self.session, owner, project.id, email="ghost@example.com",
                                   role="architect"), "user_not_in_organization")
        self.assertEqual(self.code(add, self.session, owner, project.id, email=arch.email,
                                   role="system_admin"), "invalid_role")
        add(self.session, owner, project.id, email=arch.email, role="architect")
        self.assertEqual(self.code(add, self.session, owner, project.id, email=arch.email,
                                   role="mep_engineer"), "already_member")
        self.denied(add, self.session, arch, project.id, email=owner.email, role="owner")

        project_service.change_member_role(self.session, owner, project.id, arch.id, "mep_engineer")
        project_service.remove_member(self.session, owner, project.id, arch.id)
        self.assertTrue(self.denied(access.authorize_project, self.session, arch, project.id,
                                    "project.view").hidden)
        events = project_service.list_activity(self.session, owner, project.id)
        self.assertEqual(
            [(e.action, e.actor_user_id, e.target_user_id, e.detail) for e in events[1:]],
            [
                ("project.member_added", owner.id, arch.id, {"role": "architect"}),
                ("project.member_role_changed", owner.id, arch.id,
                 {"from": "architect", "to": "mep_engineer"}),
                ("project.member_removed", owner.id, arch.id, {"role": "mep_engineer"}),
            ],
        )

    def test_a_project_always_keeps_an_owner(self) -> None:
        owner, second = self.user("owner"), self.user("second")
        self.join(owner, second)
        project = self.make(owner)
        change, remove = project_service.change_member_role, project_service.remove_member

        self.assertEqual(self.code(change, self.session, owner, project.id, owner.id, "architect"),
                         "last_owner")
        self.assertEqual(self.code(remove, self.session, owner, project.id, owner.id), "last_owner")
        project_service.add_member(self.session, owner, project.id, email=second.email, role="owner")
        project_service.remove_member(self.session, owner, project.id, owner.id)

    # activity ------------------------------------------------------------
    def test_activity_is_ordered_and_only_readable_by_project_members(self) -> None:
        owner, colleague = self.user("owner"), self.user("colleague")
        self.join(owner, colleague)
        project = self.make(owner)
        for name in ("A", "B", "C"):
            project_service.update_project(self.session, owner, project.id, name=name)

        events = project_service.list_activity(self.session, owner, project.id)
        ids = [e.id for e in events]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(self.actions(owner, project), ["project.created", *["project.updated"] * 3])
        self.assertTrue(self.denied(project_service.list_activity, self.session, colleague,
                                    project.id).hidden)


class HttpProjectChecks:
    def signed_in(self, name: str):
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        app = create_app(
            Settings(environment="test"),
            session_factory=create_session_factory(engine),
            auth_policy=POLICY,
        )
        client = TestClient(app)
        self.addCleanup(client.close)
        email = f"{name}@example.com"
        client.post(f"{V1}/auth/register",
                    json={"email": email, "display_name": name, "password": PASSWORD})
        csrf = client.post(f"{V1}/auth/login",
                           json={"email": email, "password": PASSWORD}).json()["csrf_token"]
        org = client.get(f"{V1}/orgs").json()["organizations"][0]["id"]
        return client, {"X-CSRF-Token": csrf}, org

    def test_project_lifecycle_over_http(self) -> None:
        client, headers, org = self.signed_in("owner")
        created = client.post(
            f"{V1}/projects",
            json={"organization_id": org, "name": "Villa", "project_type": "residential_house"},
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        pid = created.json()["project"]["id"]

        self.assertEqual(client.post(f"{V1}/projects/{pid}/archive").status_code, 403)  # CSRF
        read = client.get(f"{V1}/projects/{pid}").json()
        self.assertEqual(read["my_role"], "owner")
        self.assertIn("project.archive", read["permissions"])
        patched = client.patch(f"{V1}/projects/{pid}", json={"name": "Villa 2"}, headers=headers)
        self.assertEqual(patched.json()["project"]["name"], "Villa 2")

        self.assertEqual(client.post(f"{V1}/projects/{pid}/archive", headers=headers).status_code, 200)
        self.assertEqual(client.get(f"{V1}/projects").json()["projects"], [])
        archived = client.get(f"{V1}/projects", params={"archived": "true"}).json()["projects"]
        self.assertEqual([p["id"] for p in archived], [pid])
        blocked = client.patch(f"{V1}/projects/{pid}", json={"name": "No"}, headers=headers)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(
            client.get(f"{V1}/projects/{pid}").json()["permissions"],
            ["project.view", "project.restore"],
        )
        self.assertEqual(client.post(f"{V1}/projects/{pid}/restore", headers=headers).status_code, 200)

        actions = [e["action"] for e in client.get(f"{V1}/projects/{pid}/activity").json()["events"]]
        self.assertEqual(
            actions,
            ["project.created", "project.updated", "project.archived", "project.restored"],
        )

    def test_other_tenants_and_anonymous_callers_learn_nothing(self) -> None:
        owner, headers, org = self.signed_in("owner")
        stranger, stranger_h, _ = self.signed_in("stranger")
        pid = owner.post(
            f"{V1}/projects",
            json={"organization_id": org, "name": "Villa", "project_type": "other"},
            headers=headers,
        ).json()["project"]["id"]

        for path in (f"/projects/{pid}", f"/projects/{pid}/members", f"/projects/{pid}/activity"):
            self.assertEqual(stranger.get(f"{V1}{path}").status_code, 404, path)
        self.assertEqual(
            stranger.patch(f"{V1}/projects/{pid}", json={"name": "x"}, headers=stranger_h).status_code,
            404,
        )
        self.assertEqual(stranger.get(f"{V1}/projects").json()["projects"], [])
        denied_create = stranger.post(
            f"{V1}/projects",
            json={"organization_id": org, "name": "Mine", "project_type": "other"},
            headers=stranger_h,
        )
        self.assertEqual(denied_create.status_code, 404)
        anonymous, _, _ = self.signed_in("anon")
        anonymous.cookies.clear()
        self.assertEqual(anonymous.get(f"{V1}/projects").status_code, 401)

    def test_adding_a_member_over_http_is_recorded_with_actor_and_target(self) -> None:
        owner, headers, org = self.signed_in("owner")
        guest, guest_h, _ = self.signed_in("guest")
        token = owner.post(
            f"{V1}/orgs/{org}/invitations", json={"email": "guest@example.com"}, headers=headers
        ).json()["token"]
        guest.post(f"{V1}/invitations/accept", json={"token": token}, headers=guest_h)
        pid = owner.post(
            f"{V1}/projects",
            json={"organization_id": org, "name": "Villa", "project_type": "commercial"},
            headers=headers,
        ).json()["project"]["id"]

        added = owner.post(
            f"{V1}/projects/{pid}/members",
            json={"email": "guest@example.com", "role": "structural_engineer"},
            headers=headers,
        )
        self.assertEqual(added.status_code, 201)
        self.assertEqual(guest.get(f"{V1}/projects/{pid}").json()["my_role"], "structural_engineer")
        forbidden = guest.post(
            f"{V1}/projects/{pid}/members",
            json={"email": "owner@example.com", "role": "architect"},
            headers=guest_h,
        )
        self.assertEqual(forbidden.status_code, 403)
        event = owner.get(f"{V1}/projects/{pid}/activity").json()["events"][-1]
        self.assertEqual(event["action"], "project.member_added")
        self.assertEqual(event["detail"], {"role": "structural_engineer"})
        self.assertIsNotNone(event["target_user_id"])


class SqliteProjectTests(ProjectChecks, HttpProjectChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresProjectTests(ProjectChecks, HttpProjectChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
