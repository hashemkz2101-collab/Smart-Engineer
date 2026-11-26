import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import org_service, project_service, requirements_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.requirements_schema import missing_required, not_provided, validate_section
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

PROGRAM = {
    "units_count": 2,
    "floors_count": 3,
    "target_area_m2": 320.0,
    "target_area_min_m2": 300.0,
    "target_area_max_m2": 350.0,
    "rooms": [
        {"kind": "bedroom", "count": 4, "target_area_m2": 14.0},
        {"kind": "master_bedroom", "count": 1, "area_min_m2": 16.0, "area_max_m2": 22.0},
        {"kind": "kitchen", "count": 2, "target_area_m2": 12.0},
        {"kind": "reception", "count": 1, "target_area_m2": 40.0},
        {"kind": "living", "count": 2},
        {"kind": "bathroom", "count": 4},
        {"kind": "storage", "count": 1},
        {"kind": "laundry", "count": 1},
        {"kind": "special", "name": "اتاق مطالعه", "notes": "ساکت"},
        {"kind": "parking", "count": 2},
        {"kind": "yard"},
        {"kind": "terrace"},
        {"kind": "balcony", "count": 3},
        {"kind": "roof_garden"},
        {"kind": "green_space"},
    ],
}
PREFERENCES = {
    "accessibility": "older_occupants",
    "accessibility_notes": "بدون پله در طبقهٔ همکف",
    "privacy_level": "high",
    "public_private_separation": "required",
    "style": "مدرن",
    "quality_level": "high",
    "material_level": "standard",
    "budget_amount": 12000000000.0,
    "budget_currency": "toman",
    "budget_flexibility": "flexible",
    "priorities": [{"item": "نورگیری", "rank": 1}, {"item": "پارکینگ", "rank": 2}],
    "constraints": [
        {"level": "mandatory", "description": "آسانسور"},
        {"level": "preferred", "description": "حیاط خلوت"},
        {"level": "unacceptable", "description": "پنجرهٔ مشرف به همسایه"},
    ],
    "future_expansion": "افزودن طبقهٔ چهارم",
    "change_of_use": "تبدیل طبقهٔ همکف به مطب",
}
REFERENCES = {
    "items": [
        {"label": "نمای آجری", "explanation": "نمای مورد علاقه", "kind": "image",
         "url": "https://example.com/a.jpg"},
        {"label": "پلان باز", "explanation": "ارتباط آشپزخانه و نشیمن"},
    ]
}
FIXTURES = (("program", PROGRAM), ("preferences", PREFERENCES), ("references", REFERENCES))


class SchemaTests(unittest.TestCase):
    def test_every_fixture_validates_unchanged(self) -> None:
        for section, data in FIXTURES:
            cleaned, errors = validate_section(section, data)
            self.assertEqual(errors, {}, section)
            self.assertEqual(cleaned, data, section)

    def test_ranges_and_dependent_fields_are_checked(self) -> None:
        _, errors = validate_section("program", {
            "units_count": 1, "floors_count": 1, "target_area_min_m2": 400, "target_area_max_m2": 300,
            "rooms": [{"kind": "bedroom", "area_min_m2": 20, "area_max_m2": 10}, {"count": 2}]})
        self.assertEqual(errors, {"target_area_max_m2": "range_inverted",
                                  "rooms[0].area_max_m2": "range_inverted",
                                  "rooms[1].kind": "required"})
        _, errors = validate_section("preferences", {"budget_amount": 100})
        self.assertEqual(errors, {"budget_currency": "currency_required"})
        _, errors = validate_section("preferences", {
            "constraints": [{"level": "must", "description": ""}], "priorities": [{"rank": 1}]})
        self.assertEqual(errors, {"constraints[0].level": "invalid_choice",
                                  "constraints[0].description": "required",
                                  "priorities[0].item": "required"})
        _, errors = validate_section("references", {"items": [{"label": "x", "url": "ftp://a"}]})
        self.assertEqual(errors, {"items[0].url": "invalid_url"})
        _, errors = validate_section("program", {"units_count": 1.5, "rooms": [{"kind": "x"}]})
        self.assertEqual(errors, {"units_count": "not_an_integer", "rooms[0].kind": "invalid_choice"})

    def test_required_and_not_provided_are_reported_without_defaults(self) -> None:
        self.assertEqual(missing_required("program", {}), ["units_count", "floors_count", "rooms"])
        self.assertEqual(missing_required("program", {"rooms": []}), ["units_count", "floors_count"])
        self.assertEqual(missing_required("references", {"items": []}), [])
        cleaned, _ = validate_section("preferences", {"style": "مدرن"})
        self.assertIn("budget_amount", not_provided("preferences", cleaned))
        self.assertNotIn("style", not_provided("preferences", cleaned))
        self.assertEqual(cleaned, {"style": "مدرن"})


class RequirementsChecks:
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

    def test_fixtures_round_trip_and_stay_with_their_project(self) -> None:
        owner = self.user("owner")
        project, other = self.project(owner), self.project(owner)
        for section, data in FIXTURES:
            saved = requirements_service.save_section(self.session, owner, project.id, section, data, 0)
            self.assertTrue(saved["complete"], section)
        sections = {s["section"]: s for s in requirements_service.get_requirements(
            self.session, owner, project.id)}
        for section, data in FIXTURES:
            self.assertEqual(sections[section]["data"], data, section)
        untouched = requirements_service.get_requirements(self.session, owner, other.id)
        self.assertTrue(all(s["version"] == 0 and s["data"] == {} for s in untouched))

    def test_partial_program_reports_missing_and_invalid_save_changes_nothing(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        first = requirements_service.save_section(
            self.session, owner, project.id, "program", {"units_count": 1}, 0)
        self.assertEqual((first["complete"], first["missing"]), (False, ["floors_count", "rooms"]))
        with self.assertRaises(requirements_service.RequirementsValidationError) as bad:
            requirements_service.save_section(
                self.session, owner, project.id, "program", {"units_count": 0}, 1)
        self.assertEqual(bad.exception.errors, {"units_count": "out_of_range"})
        with self.assertRaises(requirements_service.RequirementsError) as stale:
            requirements_service.save_section(self.session, owner, project.id, "program", {}, 0)
        self.assertEqual(stale.exception.code, "version_conflict")
        with self.assertRaises(requirements_service.RequirementsError) as unknown:
            requirements_service.save_section(self.session, owner, project.id, "roof", {}, 0)
        self.assertEqual(unknown.exception.code, "unknown_section")
        stored = requirements_service.get_requirements(self.session, owner, project.id)[0]
        self.assertEqual((stored["data"], stored["version"]), ({"units_count": 1}, 1))

    def test_architect_edits_others_read_strangers_see_nothing_archive_read_only(self) -> None:
        owner, arch, qs, stranger = (self.user(n) for n in ("owner", "arch", "qs", "stranger"))
        project = self.project(owner)
        for person, role in ((arch, "architect"), (qs, "quantity_surveyor")):
            _, token = org_service.create_invitation(
                self.session, owner, self.org_of(owner), email=person.email, org_role="member")
            org_service.accept_invitation(self.session, person, token)
            project_service.add_member(self.session, owner, project.id, email=person.email, role=role)
        requirements_service.save_section(
            self.session, arch, project.id, "preferences", {"style": "کلاسیک"}, 0)
        self.assertEqual(requirements_service.get_requirements(self.session, qs, project.id)[1]["data"],
                         {"style": "کلاسیک"})
        with self.assertRaises(AccessDenied) as denied:
            requirements_service.save_section(self.session, qs, project.id, "preferences", {}, 1)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            requirements_service.get_requirements(self.session, stranger, project.id)
        self.assertTrue(hidden.exception.hidden)

        last = project_service.list_activity(self.session, owner, project.id)[-1]
        self.assertEqual((last.action, last.detail), ("project.requirements_saved",
                                                      {"section": "preferences", "complete": True}))
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            requirements_service.save_section(self.session, owner, project.id, "preferences", {}, 1)

    def test_http_round_trip(self) -> None:
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        app = create_app(Settings(environment="test"),
                         session_factory=create_session_factory(engine), auth_policy=POLICY)
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
        url = f"{V1}/projects/{pid}/requirements"

        sections = client.get(url).json()["sections"]
        self.assertEqual([s["section"] for s in sections], ["program", "preferences", "references"])
        self.assertEqual(client.put(f"{url}/program", json={"data": PROGRAM, "version": 0}).status_code, 403)
        bad = client.put(f"{url}/preferences", headers=headers,
                         json={"data": {"budget_amount": 5}, "version": 0})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(bad.json()["error"]["code"], "invalid_requirements")
        self.assertEqual(bad.json()["error"]["details"],
                         [{"field": "budget_currency", "reason": "currency_required"}])
        ok = client.put(f"{url}/program", headers=headers, json={"data": PROGRAM, "version": 0})
        self.assertEqual((ok.status_code, ok.json()["complete"]), (200, True))
        stale = client.put(f"{url}/program", headers=headers, json={"data": PROGRAM, "version": 0})
        self.assertEqual((stale.status_code, stale.json()["error"]["code"]), (409, "version_conflict"))
        self.assertEqual(client.get(url).json()["sections"][0]["data"], PROGRAM)
        self.assertEqual(client.put(f"{url}/roof", headers=headers,
                                    json={"data": {}, "version": 0}).status_code, 404)


class SqliteRequirementsTests(RequirementsChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresRequirementsTests(RequirementsChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlRequirementsTests(RequirementsChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
