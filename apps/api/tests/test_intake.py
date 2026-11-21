import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import intake_service, org_service, project_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.intake_schema import missing_required, validate_step
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

# A fixture covering INP-002: identity, location (with geolocation), people, legal notes.
FIXTURE = {
    "identity": {"project_code": "P-1405-01", "purpose": "residence"},
    "location": {
        "province": "تهران",
        "city": "تهران",
        "address": "خیابان نمونه، پلاک ۱۲",
        "latitude": 35.6892,
        "longitude": 51.389,
    },
    "people": {
        "client": "شرکت نمونه",
        "owner": "علی رضایی",
        "responsible_engineer": "مهندس احمدی",
        "team_notes": "معمار و سازه",
    },
    "legal": {
        "ownership_status": "owned",
        "deed_status": "has_deed",
        "restrictions": "حریم رودخانه (ادعای کاربر)",
        "notes": "سند تک‌برگ",
    },
}


class SchemaTests(unittest.TestCase):
    def test_valid_data_is_cleaned_and_empty_fields_are_dropped(self) -> None:
        cleaned, errors = validate_step(
            "people", {"client": "  شرکت ", "owner": "   ", "team_notes": None}
        )
        self.assertEqual((cleaned, errors), ({"client": "شرکت"}, {}))

    def test_each_invalid_field_reports_its_own_reason(self) -> None:
        _, errors = validate_step(
            "location",
            {
                "province": 5,
                "city": "x" * 101,
                "latitude": 91,
                "longitude": "abc",
                "colour": "red",
            },
        )
        self.assertEqual(
            errors,
            {
                "province": "not_text",
                "city": "too_long",
                "latitude": "out_of_range",
                "longitude": "not_a_number",
                "colour": "unknown_field",
            },
        )
        _, choice = validate_step("identity", {"purpose": "castle"})
        self.assertEqual(choice, {"purpose": "invalid_choice"})
        _, flags = validate_step("location", {"latitude": True})
        self.assertEqual(flags, {"latitude": "not_a_number"})

    def test_coordinates_must_come_as_a_pair(self) -> None:
        _, errors = validate_step("location", {"latitude": 35.7})
        self.assertEqual(errors, {"longitude": "coordinates_need_both"})
        cleaned, errors = validate_step("location", {"latitude": "35.7", "longitude": "51.4"})
        self.assertEqual((cleaned, errors), ({"latitude": 35.7, "longitude": 51.4}, {}))

    def test_missing_required_fields_are_listed(self) -> None:
        self.assertEqual(missing_required("identity", {}), ["purpose"])
        self.assertEqual(missing_required("location", {"city": "x"}), ["province"])
        self.assertEqual(missing_required("legal", {}), [])


class IntakeChecks:
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

    def project(self, owner):
        return project_service.create_project(
            self.session, owner, self.org_of(owner), name="House", project_type="residential_house"
        )

    def test_a_project_fixture_round_trips_every_intake_field(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        for step, data in FIXTURE.items():
            saved = intake_service.save_step(self.session, owner, project.id, step, data, 0)
            self.assertTrue(saved["complete"], step)

        steps = {s["step"]: s for s in intake_service.get_intake(self.session, owner, project.id)}
        for step, data in FIXTURE.items():
            self.assertEqual(steps[step]["data"], data)
            self.assertEqual(steps[step]["version"], 1)

    def test_partial_data_is_saved_and_survives_a_later_failed_save(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        first = intake_service.save_step(
            self.session, owner, project.id, "location", {"city": "تهران"}, 0
        )
        self.assertEqual((first["complete"], first["missing"]), (False, ["province"]))

        with self.assertRaises(intake_service.IntakeValidationError) as context:
            intake_service.save_step(
                self.session, owner, project.id, "location",
                {"city": "تبریز", "latitude": 500, "longitude": 51}, 1,
            )
        self.assertEqual(context.exception.errors, {"latitude": "out_of_range"})

        stored = intake_service.get_intake(self.session, owner, project.id)[1]
        self.assertEqual((stored["data"], stored["version"]), ({"city": "تهران"}, 1))

        done = intake_service.save_step(
            self.session, owner, project.id, "location", {"city": "تهران", "province": "تهران"}, 1
        )
        self.assertEqual((done["complete"], done["version"]), (True, 2))

    def test_stale_versions_are_rejected(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        intake_service.save_step(self.session, owner, project.id, "people", {"client": "A"}, 0)
        for stale in (0, 5):
            with self.assertRaises(intake_service.IntakeError) as context:
                intake_service.save_step(
                    self.session, owner, project.id, "people", {"client": "B"}, stale
                )
            self.assertEqual(context.exception.code, "version_conflict")

    def test_unknown_step_and_empty_state(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        with self.assertRaises(intake_service.IntakeError) as context:
            intake_service.save_step(self.session, owner, project.id, "roof", {}, 0)
        self.assertEqual(context.exception.code, "unknown_step")
        steps = intake_service.get_intake(self.session, owner, project.id)
        self.assertEqual([s["step"] for s in steps], ["identity", "location", "people", "legal"])
        self.assertTrue(all(s["version"] == 0 and not s["complete"] for s in steps))

    def test_only_the_owner_edits_members_read_and_strangers_see_nothing(self) -> None:
        owner, arch, stranger = self.user("owner"), self.user("arch"), self.user("stranger")
        _, token = org_service.create_invitation(
            self.session, owner, self.org_of(owner), email=arch.email, org_role="member"
        )
        org_service.accept_invitation(self.session, arch, token)
        project = self.project(owner)
        project_service.add_member(self.session, owner, project.id, email=arch.email, role="architect")
        intake_service.save_step(self.session, owner, project.id, "people", {"client": "A"}, 0)

        self.assertEqual(
            intake_service.get_intake(self.session, arch, project.id)[2]["data"], {"client": "A"}
        )
        with self.assertRaises(AccessDenied) as denied:
            intake_service.save_step(self.session, arch, project.id, "people", {"client": "B"}, 1)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            intake_service.get_intake(self.session, stranger, project.id)
        self.assertTrue(hidden.exception.hidden)

    def test_archived_projects_are_read_only_and_saves_are_logged(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        intake_service.save_step(self.session, owner, project.id, "identity", {"purpose": "sale"}, 0)
        events = project_service.list_activity(self.session, owner, project.id)
        self.assertEqual(events[-1].action, "project.intake_saved")
        self.assertEqual(events[-1].detail, {"step": "identity", "complete": True})

        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            intake_service.save_step(self.session, owner, project.id, "identity", {"purpose": "rent"}, 1)
        self.assertEqual(
            intake_service.get_intake(self.session, owner, project.id)[0]["data"],
            {"purpose": "sale"},
        )

    def test_http_round_trip_field_errors_conflict_and_csrf(self) -> None:
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        app = create_app(
            Settings(environment="test"),
            session_factory=create_session_factory(engine),
            auth_policy=POLICY,
        )
        client = TestClient(app)
        self.addCleanup(client.close)
        client.post(f"{V1}/auth/register", json={
            "email": "http@example.com", "display_name": "Http", "password": PASSWORD})
        csrf = client.post(f"{V1}/auth/login", json={
            "email": "http@example.com", "password": PASSWORD}).json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        org = client.get(f"{V1}/orgs").json()["organizations"][0]["id"]
        pid = client.post(f"{V1}/projects", headers=headers, json={
            "organization_id": org, "name": "P", "project_type": "other"}).json()["project"]["id"]
        url = f"{V1}/projects/{pid}/intake"

        self.assertEqual(client.get(url).json()["steps"][0]["version"], 0)
        no_csrf = client.put(f"{url}/people", json={"data": {"client": "A"}, "version": 0})
        self.assertEqual(no_csrf.status_code, 403)

        bad = client.put(f"{url}/location", headers=headers,
                         json={"data": {"latitude": 95, "longitude": 10}, "version": 0})
        self.assertEqual(bad.status_code, 422)
        body = bad.json()["error"]
        self.assertEqual(body["code"], "invalid_intake")
        self.assertEqual(body["details"], [{"field": "latitude", "reason": "out_of_range"}])

        ok = client.put(f"{url}/people", headers=headers,
                        json={"data": {"client": "شرکت"}, "version": 0})
        self.assertEqual((ok.status_code, ok.json()["complete"], ok.json()["version"]), (200, True, 1))
        stale = client.put(f"{url}/people", headers=headers,
                           json={"data": {"client": "x"}, "version": 0})
        self.assertEqual((stale.status_code, stale.json()["error"]["code"]), (409, "version_conflict"))
        self.assertEqual(client.put(f"{url}/roof", headers=headers,
                                    json={"data": {}, "version": 0}).status_code, 404)
        reloaded = client.get(url).json()["steps"][2]
        self.assertEqual(reloaded["data"], {"client": "شرکت"})


class SqliteIntakeTests(IntakeChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresIntakeTests(IntakeChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
