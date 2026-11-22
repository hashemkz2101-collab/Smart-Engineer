import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import environment_service, org_service, project_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.environment_schema import derive_status, validate_record
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

SOURCE = {
    "source_type": "meteorological_station",
    "source_title": "سالنامهٔ هواشناسی",
    "source_reference": "جدول ۱۲",
    "location_reference": "ایستگاه سینوپتیک تبریز",
    "source_date": "1403-12-01",
    "source_calendar": "jalali",
    "source_verified": True,
}
FIXTURE = {
    "climate": {"climate_zone": "سرد و نیمه‌خشک", "mean_annual_temperature_c": 12.3},
    "solar": {"solar_radiation_kwh_m2_day": 4.8, "sunshine_hours_per_year": 2800.0},
    "wind": {"prevailing_direction": "southwest", "mean_speed_ms": 3.4},
    "rainfall": {"annual_mm": 290.0, "max_daily_mm": 48.5},
    "design_temperature": {"summer_design_c": 36.0, "winter_design_c": -14.0,
                           "comfort_notes": "۲۰ تا ۲۶ درجه"},
    "hazards": {"flood_risk": "low", "landslide_risk": "none", "subsidence_risk": "medium",
                "other_hazards": "یخبندان"},
    "seismicity": {"seismic_zone": "خطر خیلی زیاد", "design_pga_g": 0.35, "nearest_fault_km": 4.5},
    "water": {"availability": "available", "connection_distance_m": 5.0},
    "electricity": {"availability": "available"},
    "gas": {"availability": "planned", "notes": "تا یک سال دیگر"},
    "sewer": {"availability": "not_available", "notes": "چاه جذبی"},
    "telecom": {"availability": "available"},
    "energy": {"energy_constraints": "سقف مصرف", "efficiency_requirements": "عایق حرارتی"},
}


class SchemaTests(unittest.TestCase):
    def test_every_category_round_trips_with_source_location_and_date(self) -> None:
        self.assertEqual(len(FIXTURE), 13)
        for field, values in FIXTURE.items():
            data = {**values, **SOURCE}
            cleaned, errors = validate_record(field, data)
            self.assertEqual(errors, {}, field)
            self.assertEqual(cleaned, data, field)
            self.assertEqual(derive_status(field, cleaned)["status"], "verified", field)

    def test_location_and_date_are_part_of_a_verified_source(self) -> None:
        bare = {"annual_mm": 290.0}
        self.assertEqual(derive_status("rainfall", {}), {"status": "unknown", "source_missing": []})
        self.assertEqual(derive_status("rainfall", dict(SOURCE))["status"], "unknown")
        self.assertEqual(
            derive_status("rainfall", bare),
            {"status": "needs_inquiry", "source_missing": [
                "source_type", "source_title_or_reference", "location_reference", "source_date"]},
        )
        for dropped, label in (("location_reference", "location_reference"), ("source_date", "source_date")):
            partial = {**bare, **{k: v for k, v in SOURCE.items() if k != dropped}}
            partial.pop("source_calendar", None) if dropped == "source_date" else None
            self.assertEqual(derive_status("rainfall", partial)["source_missing"], [label])
        unverified = {**bare, **SOURCE, "source_verified": False}
        self.assertEqual(derive_status("rainfall", unverified),
                         {"status": "needs_inquiry", "source_missing": []})

    def test_invalid_values_are_rejected_with_reasons(self) -> None:
        _, errors = validate_record("seismicity", {"design_pga_g": 9, "source_type": "guess",
                                                   "source_date": "1403-13-01", "source_calendar": "jalali"})
        self.assertEqual(errors, {"design_pga_g": "out_of_range", "source_type": "invalid_choice",
                                  "source_date": "invalid_date"})
        _, errors = validate_record("design_temperature", {"summer_design_c": 20, "winter_design_c": 25})
        self.assertEqual(errors, {"winter_design_c": "winter_above_summer"})
        _, errors = validate_record("water", {"availability": "maybe", "x": 1})
        self.assertEqual(errors, {"availability": "invalid_choice", "x": "unknown_field"})
        _, errors = validate_record("wind", {"source_date": "1403-01-01"})
        self.assertEqual(errors, {"source_calendar": "calendar_required"})

    def test_omitted_values_are_never_defaulted(self) -> None:
        cleaned, _ = validate_record("water", {"availability": "available", "notes": " "})
        self.assertEqual(cleaned, {"availability": "available"})


class EnvironmentChecks:
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

    def test_records_round_trip_and_unsourced_values_need_inquiry(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        for field, values in FIXTURE.items():
            saved = environment_service.save_record(
                self.session, owner, project.id, field, {**values, **SOURCE}, 0)
            self.assertEqual(saved["status"], "verified", field)
        environment_service.save_record(
            self.session, owner, project.id, "rainfall", {"annual_mm": 300}, 1)
        records = {r["field"]: r for r in environment_service.get_environment(
            self.session, owner, project.id)}
        self.assertEqual(records["wind"]["data"], {**FIXTURE["wind"], **SOURCE})
        self.assertEqual(records["rainfall"]["status"], "needs_inquiry")
        self.assertEqual(records["rainfall"]["data"], {"annual_mm": 300.0})
        self.assertEqual(list(records), list(FIXTURE))

    def test_untouched_categories_are_unknown(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        records = environment_service.get_environment(self.session, owner, project.id)
        self.assertEqual(len(records), 13)
        self.assertTrue(all(r["status"] == "unknown" and r["version"] == 0 and r["data"] == {}
                            for r in records))

    def test_invalid_save_stale_version_and_unknown_field(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        environment_service.save_record(self.session, owner, project.id, "wind",
                                        {"mean_speed_ms": 3}, 0)
        with self.assertRaises(environment_service.EnvironmentValidationError) as bad:
            environment_service.save_record(self.session, owner, project.id, "wind",
                                            {"mean_speed_ms": 900}, 1)
        self.assertEqual(bad.exception.errors, {"mean_speed_ms": "out_of_range"})
        with self.assertRaises(environment_service.EnvironmentError_) as stale:
            environment_service.save_record(self.session, owner, project.id, "wind", {}, 0)
        self.assertEqual(stale.exception.code, "version_conflict")
        with self.assertRaises(environment_service.EnvironmentError_) as unknown:
            environment_service.save_record(self.session, owner, project.id, "roof", {}, 0)
        self.assertEqual(unknown.exception.code, "unknown_field")
        stored = {r["field"]: r for r in environment_service.get_environment(
            self.session, owner, project.id)}["wind"]
        self.assertEqual((stored["data"], stored["version"]), ({"mean_speed_ms": 3.0}, 1))

    def test_engineers_edit_surveyor_reads_strangers_see_nothing_archive_read_only(self) -> None:
        owner, mep, qs, stranger = (self.user(n) for n in ("owner", "mep", "qs", "stranger"))
        project = self.project(owner)
        for person, role in ((mep, "mep_engineer"), (qs, "quantity_surveyor")):
            _, token = org_service.create_invitation(
                self.session, owner, self.org_of(owner), email=person.email, org_role="member")
            org_service.accept_invitation(self.session, person, token)
            project_service.add_member(self.session, owner, project.id, email=person.email, role=role)
        environment_service.save_record(
            self.session, mep, project.id, "water", {"availability": "available"}, 0)
        water = {r["field"]: r for r in environment_service.get_environment(
            self.session, qs, project.id)}["water"]
        self.assertEqual(water["data"], {"availability": "available"})
        with self.assertRaises(AccessDenied) as denied:
            environment_service.save_record(self.session, qs, project.id, "water", {}, 1)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            environment_service.get_environment(self.session, stranger, project.id)
        self.assertTrue(hidden.exception.hidden)

        last = project_service.list_activity(self.session, owner, project.id)[-1]
        self.assertEqual((last.action, last.detail),
                         ("project.environment_saved", {"field": "water", "status": "needs_inquiry"}))
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            environment_service.save_record(self.session, owner, project.id, "water", {}, 1)

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
        url = f"{V1}/projects/{pid}/environment"

        records = client.get(url).json()["records"]
        self.assertEqual(len(records), 13)
        self.assertEqual(records[0]["status"], "unknown")
        body = {"data": {"annual_mm": 290}, "version": 0}
        self.assertEqual(client.put(f"{url}/rainfall", json=body).status_code, 403)
        bad = client.put(f"{url}/rainfall", headers=headers, json={
            "data": {"source_date": "1403-01-01"}, "version": 0})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(bad.json()["error"]["code"], "invalid_environment")
        self.assertEqual(bad.json()["error"]["details"],
                         [{"field": "source_calendar", "reason": "calendar_required"}])
        ok = client.put(f"{url}/rainfall", headers=headers, json=body)
        self.assertEqual((ok.status_code, ok.json()["status"]), (200, "needs_inquiry"))
        self.assertEqual(ok.json()["source_missing"], [
            "source_type", "source_title_or_reference", "location_reference", "source_date"])
        stale = client.put(f"{url}/rainfall", headers=headers, json=body)
        self.assertEqual((stale.status_code, stale.json()["error"]["code"]), (409, "version_conflict"))
        self.assertEqual(client.put(f"{url}/roof", headers=headers,
                                    json={"data": {}, "version": 0}).status_code, 404)


class SqliteEnvironmentTests(EnvironmentChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresEnvironmentTests(EnvironmentChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
