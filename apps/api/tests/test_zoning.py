import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import org_service, project_service, zoning_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from smart_engineer_api.zoning_schema import derive_status, validate_record
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

SOURCE = {
    "source_type": "municipality_letter",
    "source_title": "نامهٔ شهرداری منطقه ۲",
    "source_reference": "شماره ۱۲۳/ب",
    "source_date": "1405-02-10",
    "source_calendar": "jalali",
    "source_verified": True,
}
FIXTURE = {
    "land_use": {"zone_name": "مسکونی ۲", "land_use": "مسکونی"},
    "coverage": {"max_coverage_percent": 60.0},
    "density": {"max_density_percent": 120.0, "max_floor_area_m2": 360.0},
    "floors_height": {"max_floors": 4, "max_height_m": 13.5},
    "setbacks": {"front_m": 3.0, "rear_m": 2.0, "left_m": 0.0, "right_m": 1.5,
                 "correction_notes": "عقب‌نشینی ۲ متر برای اصلاحی"},
    "parking_access": {"min_parking_spaces": 2, "access_notes": "ورودی از جنوب"},
    "daylight_openings": {"daylight_notes": "نورگیر ۶ متر مربع", "courtyard_notes": "حیاط ۱۵٪"},
    "circulation": {"elevator": "required", "stair_notes": "پلهٔ فرار", "exit_notes": "دو خروج"},
    "local_constraints": {"constraints": "ارتفاع نما مطابق ضوابط محله"},
}


class SchemaTests(unittest.TestCase):
    def test_every_category_round_trips_with_a_source_and_is_verified(self) -> None:
        for field, values in FIXTURE.items():
            data = {**values, **SOURCE}
            cleaned, errors = validate_record(field, data)
            self.assertEqual(errors, {}, field)
            self.assertEqual(cleaned, data, field)
            self.assertEqual(derive_status(field, cleaned)["status"], "verified", field)

    def test_status_unknown_needs_inquiry_or_verified(self) -> None:
        self.assertEqual(derive_status("coverage", {}), {"status": "unknown", "source_missing": []})
        # A source alone does not make a value known.
        self.assertEqual(derive_status("coverage", dict(SOURCE))["status"], "unknown")
        bare = {"max_coverage_percent": 60.0}
        self.assertEqual(
            derive_status("coverage", bare),
            {"status": "needs_inquiry",
             "source_missing": ["source_type", "source_date", "source_title_or_reference"]},
        )
        unverified = {**bare, **SOURCE, "source_verified": False}
        self.assertEqual(derive_status("coverage", unverified),
                         {"status": "needs_inquiry", "source_missing": []})
        partial = {**bare, "source_type": "other", "source_reference": "x"}
        self.assertEqual(derive_status("coverage", partial)["source_missing"], ["source_date"])

    def test_invalid_values_and_dates_are_rejected_with_reasons(self) -> None:
        _, errors = validate_record("coverage", {
            "max_coverage_percent": 150, "source_date": "2026-02-30", "source_calendar": "gregorian",
            "source_type": "magic", "nope": 1})
        self.assertEqual(errors, {"max_coverage_percent": "out_of_range", "source_date": "invalid_date",
                                  "source_type": "invalid_choice", "nope": "unknown_field"})
        _, errors = validate_record("coverage", {"source_date": "1405-02-10"})
        self.assertEqual(errors, {"source_calendar": "calendar_required"})
        _, errors = validate_record("coverage", {"source_date": "1405-07-31", "source_calendar": "jalali"})
        self.assertEqual(errors, {"source_date": "invalid_date"})
        _, errors = validate_record("floors_height", {"max_floors": 2.5, "source_verified": "yes"})
        self.assertEqual(errors, {"max_floors": "not_an_integer", "source_verified": "not_a_boolean"})

    def test_omitted_values_are_never_defaulted(self) -> None:
        cleaned, _ = validate_record("setbacks", {"front_m": 3, "rear_m": " "})
        self.assertEqual(cleaned, {"front_m": 3.0})


class ZoningChecks:
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

    def test_records_round_trip_and_unverified_values_show_needs_inquiry(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        for field, values in FIXTURE.items():
            saved = zoning_service.save_record(
                self.session, owner, project.id, field, {**values, **SOURCE}, 0)
            self.assertEqual(saved["status"], "verified", field)
        zoning_service.save_record(
            self.session, owner, project.id, "coverage", {"max_coverage_percent": 50}, 1)

        records = {r["field"]: r for r in zoning_service.get_zoning(self.session, owner, project.id)}
        self.assertEqual(records["setbacks"]["data"], {**FIXTURE["setbacks"], **SOURCE})
        self.assertEqual(records["coverage"]["status"], "needs_inquiry")
        self.assertEqual(records["coverage"]["data"], {"max_coverage_percent": 50.0})
        self.assertEqual(records["coverage"]["version"], 2)
        self.assertEqual(list(records), ["land_use", "coverage", "density", "floors_height",
                                         "setbacks", "parking_access", "daylight_openings",
                                         "circulation", "local_constraints"])

    def test_untouched_categories_are_unknown(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        records = zoning_service.get_zoning(self.session, owner, project.id)
        self.assertTrue(all(r["status"] == "unknown" and r["version"] == 0 and r["data"] == {}
                            for r in records))

    def test_invalid_save_stale_version_and_unknown_field(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        zoning_service.save_record(self.session, owner, project.id, "coverage",
                                   {"max_coverage_percent": 40}, 0)
        with self.assertRaises(zoning_service.ZoningValidationError) as bad:
            zoning_service.save_record(self.session, owner, project.id, "coverage",
                                       {"max_coverage_percent": 400}, 1)
        self.assertEqual(bad.exception.errors, {"max_coverage_percent": "out_of_range"})
        with self.assertRaises(zoning_service.ZoningError) as stale:
            zoning_service.save_record(self.session, owner, project.id, "coverage", {}, 0)
        self.assertEqual(stale.exception.code, "version_conflict")
        with self.assertRaises(zoning_service.ZoningError) as unknown:
            zoning_service.save_record(self.session, owner, project.id, "roof", {}, 0)
        self.assertEqual(unknown.exception.code, "unknown_field")
        stored = zoning_service.get_zoning(self.session, owner, project.id)[1]
        self.assertEqual((stored["data"], stored["version"]), ({"max_coverage_percent": 40.0}, 1))

    def test_architect_edits_others_read_strangers_see_nothing_archive_read_only(self) -> None:
        owner, arch, qs, stranger = (self.user(n) for n in ("owner", "arch", "qs", "stranger"))
        project = self.project(owner)
        for person, role in ((arch, "architect"), (qs, "quantity_surveyor")):
            _, token = org_service.create_invitation(
                self.session, owner, self.org_of(owner), email=person.email, org_role="member")
            org_service.accept_invitation(self.session, person, token)
            project_service.add_member(self.session, owner, project.id, email=person.email, role=role)
        zoning_service.save_record(self.session, arch, project.id, "land_use", {"zone_name": "A"}, 0)
        self.assertEqual(zoning_service.get_zoning(self.session, qs, project.id)[0]["data"],
                         {"zone_name": "A"})
        with self.assertRaises(AccessDenied) as denied:
            zoning_service.save_record(self.session, qs, project.id, "land_use", {}, 1)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            zoning_service.get_zoning(self.session, stranger, project.id)
        self.assertTrue(hidden.exception.hidden)

        last = project_service.list_activity(self.session, owner, project.id)[-1]
        self.assertEqual((last.action, last.detail),
                         ("project.zoning_saved", {"field": "land_use", "status": "needs_inquiry"}))
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            zoning_service.save_record(self.session, owner, project.id, "land_use", {}, 1)

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
        url = f"{V1}/projects/{pid}/zoning"

        records = client.get(url).json()["records"]
        self.assertEqual(len(records), 9)
        self.assertEqual(records[0]["status"], "unknown")
        body = {"data": {"max_coverage_percent": 60}, "version": 0}
        self.assertEqual(client.put(f"{url}/coverage", json=body).status_code, 403)
        bad = client.put(f"{url}/coverage", headers=headers, json={
            "data": {"source_date": "1405-02-10"}, "version": 0})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(bad.json()["error"]["code"], "invalid_zoning")
        self.assertEqual(bad.json()["error"]["details"],
                         [{"field": "source_calendar", "reason": "calendar_required"}])
        ok = client.put(f"{url}/coverage", headers=headers, json=body)
        self.assertEqual((ok.status_code, ok.json()["status"]), (200, "needs_inquiry"))
        self.assertEqual(ok.json()["source_missing"],
                         ["source_type", "source_date", "source_title_or_reference"])
        stale = client.put(f"{url}/coverage", headers=headers, json=body)
        self.assertEqual((stale.status_code, stale.json()["error"]["code"]), (409, "version_conflict"))
        self.assertEqual(client.put(f"{url}/roof", headers=headers,
                                    json={"data": {}, "version": 0}).status_code, 404)


class SqliteZoningTests(ZoningChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresZoningTests(ZoningChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
