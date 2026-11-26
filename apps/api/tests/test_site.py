import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import org_service, project_service, site_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from smart_engineer_api.site_schema import (
    derive_parcel,
    is_simple_polygon,
    missing_required,
    not_provided,
    polygon_area,
    validate_section,
)
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

RECTANGLE = {
    "shape": "rectangular",
    "width_m": 10.0,
    "depth_m": 20.0,
    "declared_area_m2": 200.0,
    "sides": [
        {"label": "شمال", "length_m": 10.0},
        {"label": "شرق", "length_m": 20.0},
        {"label": "جنوب", "length_m": 10.0},
        {"label": "غرب", "length_m": 20.0},
    ],
    "survey_reference": "نقشه برداری شماره ۱۲",
    "coordinate_system": "UTM 39N",
    "survey_points": [{"label": "A", "x": 500000.5, "y": 3950000.25}],
}
# L-shaped irregular parcel: 10x10 square with a 5x5 corner removed = 75 m2.
IRREGULAR = {
    "shape": "irregular",
    "vertices": [
        {"x": 0.0, "y": 0.0},
        {"x": 10.0, "y": 0.0},
        {"x": 10.0, "y": 5.0},
        {"x": 5.0, "y": 5.0},
        {"x": 5.0, "y": 10.0},
        {"x": 0.0, "y": 10.0},
    ],
    "declared_area_m2": 80.0,
}
ACCESS = {
    "north_angle_deg": 12.5,
    "street_direction": "south",
    "frontage_length_m": 10.0,
    "road_width_m": 12.0,
    "access_fronts": 2,
}
TERRAIN = {
    "topography": "gentle_slope",
    "slope_percent": 4.5,
    "level_difference_m": -1.2,
    "elevation_m": 1190.0,
}
SURROUNDINGS = {
    "neighbors": [
        {"side": "east", "kind": "building", "shared_wall": True, "barrier": "wall"},
        {"side": "west", "kind": "vacant_land", "shared_wall": False, "barrier": "fence"},
    ],
    "trees": [{"description": "چنار", "notes": "قطر ۴۰ سانت"}],
    "wells": [],
    "channels": [{"description": "جوی آب"}],
    "existing_utilities": [{"description": "کنتور برق", "utility": "electricity"}],
    "easements": [{"description": "حریم خط انتقال"}],
}
SOIL = {"soil_type": "clay", "bearing_capacity_kpa": 180.0}


class ParcelMathTests(unittest.TestCase):
    def test_polygon_area_and_simplicity(self) -> None:
        l_shape = [(v["x"], v["y"]) for v in IRREGULAR["vertices"]]
        self.assertEqual(polygon_area(l_shape), 75.0)
        self.assertTrue(is_simple_polygon(l_shape))
        bow_tie = [(0, 0), (10, 10), (10, 0), (0, 8)]
        self.assertFalse(is_simple_polygon(bow_tie))

    def test_rectangle_matches_its_declared_area(self) -> None:
        derived = derive_parcel(validate_section("parcel", RECTANGLE)[0])
        self.assertEqual(derived["computed_area_m2"], 200.0)
        self.assertEqual((derived["status"], derived["difference_m2"]), ("match", 0.0))
        self.assertEqual(derived["area_source"], "width_x_depth")

    def test_irregular_discrepancy_is_reported_explicitly(self) -> None:
        cleaned, errors = validate_section("parcel", IRREGULAR)
        self.assertEqual(errors, {})
        derived = derive_parcel(cleaned)
        self.assertEqual(derived["computed_area_m2"], 75.0)
        self.assertEqual(derived["declared_area_m2"], 80.0)
        self.assertEqual(derived["difference_m2"], -5.0)
        self.assertEqual(derived["difference_percent"], 6.25)
        self.assertEqual(derived["status"], "discrepancy")
        self.assertEqual(derived["computed_side_lengths_m"], [10.0, 5.0, 5.0, 5.0, 5.0, 10.0])

    def test_statuses_when_nothing_to_compare(self) -> None:
        self.assertEqual(derive_parcel({"shape": "polygon"})["status"], "not_computable")
        no_declared = derive_parcel({"shape": "rectangular", "width_m": 4, "depth_m": 5})
        self.assertEqual((no_declared["status"], no_declared["computed_area_m2"]), ("no_declared_area", 20.0))

    def test_small_difference_within_tolerance_is_a_match(self) -> None:
        derived = derive_parcel(
            {"shape": "rectangular", "width_m": 10, "depth_m": 20, "declared_area_m2": 201.5}
        )
        self.assertEqual(derived["status"], "match")
        self.assertEqual(derived["difference_percent"], 0.74)

    def test_invalid_geometry_is_rejected(self) -> None:
        two = {"shape": "polygon", "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]}
        self.assertEqual(validate_section("parcel", two)[1], {"vertices": "too_few_points"})
        line = {"shape": "polygon", "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 2, "y": 2}]}
        self.assertEqual(validate_section("parcel", line)[1], {"vertices": "degenerate"})
        bow = {"shape": "polygon", "vertices": [
            {"x": 0, "y": 0}, {"x": 10, "y": 10}, {"x": 10, "y": 0}, {"x": 0, "y": 8}]}
        self.assertEqual(validate_section("parcel", bow)[1], {"vertices": "self_intersecting"})


class SiteSchemaTests(unittest.TestCase):
    def test_every_fixture_validates_unchanged(self) -> None:
        for section, data in (
            ("parcel", RECTANGLE), ("parcel", IRREGULAR), ("access", ACCESS),
            ("terrain", TERRAIN), ("surroundings", SURROUNDINGS), ("soil", SOIL),
        ):
            cleaned, errors = validate_section(section, data)
            self.assertEqual(errors, {}, section)
            self.assertEqual(cleaned, data, section)

    def test_field_errors_carry_paths(self) -> None:
        _, errors = validate_section("access", {"access_fronts": 2.5, "road_width_m": -3,
                                                "street_direction": "up", "extra": 1})
        self.assertEqual(errors, {"access_fronts": "not_an_integer", "road_width_m": "out_of_range",
                                  "street_direction": "invalid_choice", "extra": "unknown_field"})
        _, errors = validate_section("surroundings", {
            "neighbors": [{"kind": "building", "shared_wall": "yes"}],
            "trees": [{"notes": "x"}], "wells": "none"})
        self.assertEqual(errors, {
            "neighbors[0].shared_wall": "not_a_boolean", "neighbors[0].side": "required",
            "trees[0].description": "required", "wells": "not_a_list"})

    def test_soil_omissions_are_reported_not_defaulted(self) -> None:
        cleaned, _ = validate_section("soil", {"soil_type": "sand"})
        self.assertEqual(cleaned, {"soil_type": "sand"})
        self.assertEqual(
            not_provided("soil", cleaned),
            ["bearing_capacity_kpa", "groundwater_depth_m", "report_reference"],
        )
        empty, _ = validate_section("soil", {"bearing_capacity_kpa": "  "})
        self.assertEqual(empty, {})
        self.assertEqual(len(not_provided("soil", empty)), 4)

    def test_required_depends_on_shape_and_features_are_distinct_fields(self) -> None:
        self.assertEqual(missing_required("parcel", {}), ["shape"])
        self.assertEqual(missing_required("parcel", {"shape": "rectangular", "width_m": 3}), ["depth_m"])
        self.assertEqual(missing_required("parcel", {"shape": "polygon"}), ["vertices"])
        self.assertEqual(missing_required("surroundings", {}),
                         ["neighbors", "trees", "wells", "channels", "existing_utilities", "easements"])
        # An explicit empty list means "none", which is different from not stated.
        self.assertEqual(missing_required("surroundings", {k: [] for k in SURROUNDINGS}), [])


class SiteChecks:
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

    def test_fixtures_round_trip_and_report_derived_values(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        for section, data in (("parcel", IRREGULAR), ("access", ACCESS), ("terrain", TERRAIN),
                              ("surroundings", SURROUNDINGS), ("soil", SOIL)):
            saved = site_service.save_section(self.session, owner, project.id, section, data, 0)
            self.assertTrue(saved["complete"], section)
        sections = {s["section"]: s for s in site_service.get_site(self.session, owner, project.id)}
        self.assertEqual(sections["parcel"]["data"], IRREGULAR)
        self.assertEqual(sections["parcel"]["derived"]["status"], "discrepancy")
        self.assertEqual(sections["surroundings"]["data"], SURROUNDINGS)
        self.assertEqual(sections["soil"]["data"], SOIL)
        self.assertEqual(sections["soil"]["not_provided"],
                         ["groundwater_depth_m", "report_reference"])

    def test_invalid_save_changes_nothing_and_stale_versions_conflict(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        site_service.save_section(self.session, owner, project.id, "terrain", {"topography": "flat"}, 0)
        with self.assertRaises(site_service.SiteValidationError) as bad:
            site_service.save_section(
                self.session, owner, project.id, "terrain", {"slope_percent": 400}, 1)
        self.assertEqual(bad.exception.errors, {"slope_percent": "out_of_range"})
        with self.assertRaises(site_service.SiteError) as stale:
            site_service.save_section(self.session, owner, project.id, "terrain", {}, 0)
        self.assertEqual(stale.exception.code, "version_conflict")
        with self.assertRaises(site_service.SiteError) as unknown:
            site_service.save_section(self.session, owner, project.id, "roof", {}, 0)
        self.assertEqual(unknown.exception.code, "unknown_section")
        terrain = site_service.get_site(self.session, owner, project.id)[2]
        self.assertEqual((terrain["data"], terrain["version"]), ({"topography": "flat"}, 1))

    def test_architect_edits_others_read_and_strangers_see_nothing(self) -> None:
        owner, arch, qs, stranger = (self.user(n) for n in ("owner", "arch", "qs", "stranger"))
        project = self.project(owner)
        for person, role in ((arch, "architect"), (qs, "quantity_surveyor")):
            _, token = org_service.create_invitation(
                self.session, owner, self.org_of(owner), email=person.email, org_role="member")
            org_service.accept_invitation(self.session, person, token)
            project_service.add_member(self.session, owner, project.id, email=person.email, role=role)
        site_service.save_section(self.session, arch, project.id, "soil", {"soil_type": "rock"}, 0)
        self.assertEqual(site_service.get_site(self.session, qs, project.id)[4]["data"],
                         {"soil_type": "rock"})
        with self.assertRaises(AccessDenied) as denied:
            site_service.save_section(self.session, qs, project.id, "soil", {}, 1)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            site_service.get_site(self.session, stranger, project.id)
        self.assertTrue(hidden.exception.hidden)

    def test_archived_projects_are_read_only_and_saves_are_logged(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        site_service.save_section(self.session, owner, project.id, "access", ACCESS, 0)
        last = project_service.list_activity(self.session, owner, project.id)[-1]
        self.assertEqual((last.action, last.detail), ("project.site_saved",
                                                      {"section": "access", "complete": True}))
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            site_service.save_section(self.session, owner, project.id, "access", ACCESS, 1)

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
        url = f"{V1}/projects/{pid}/site"

        sections = client.get(url).json()["sections"]
        self.assertEqual([s["section"] for s in sections],
                         ["parcel", "access", "terrain", "surroundings", "soil"])
        self.assertEqual(sections[0]["derived"]["status"], "not_computable")
        self.assertEqual(client.put(f"{url}/parcel", json={"data": IRREGULAR, "version": 0}).status_code, 403)
        bad = client.put(f"{url}/parcel", headers=headers, json={
            "data": {"shape": "polygon", "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]}, "version": 0})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(bad.json()["error"]["details"],
                         [{"field": "vertices", "reason": "too_few_points"}])
        ok = client.put(f"{url}/parcel", headers=headers, json={"data": IRREGULAR, "version": 0})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["derived"]["difference_m2"], -5.0)
        stale = client.put(f"{url}/parcel", headers=headers, json={"data": IRREGULAR, "version": 0})
        self.assertEqual((stale.status_code, stale.json()["error"]["code"]), (409, "version_conflict"))
        self.assertEqual(client.put(f"{url}/roof", headers=headers,
                                    json={"data": {}, "version": 0}).status_code, 404)


class SqliteSiteTests(SiteChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresSiteTests(SiteChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlSiteTests(SiteChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
