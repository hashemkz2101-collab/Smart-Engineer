"""New reference and integration checks for GEOM-001–004; no legacy suites rerun."""

import copy
import math
import tempfile
import unittest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import geometry_service, site_service, zoning_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import ActivityEvent, Base, Membership, SiteSection
from smart_engineer_api.db.session import create_session_factory
from smart_engineer_api.geometry import (
    ARC_ERROR_M,
    GeometryError,
    analyze,
    buildable_envelope,
    canonicalize,
    polygon_area,
)
from smart_engineer_api.main import create_app
from smart_engineer_api.project_service import archive_project, create_project
from smart_engineer_api.security import ScryptParams
from tests.geometry_helpers import memory_engine

RECT = {"shape": "rectangular", "width_m": 10, "depth_m": 20}
L_POINTS = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
TODAY = date(2026, 11, 25)
SOURCE = {
    "source_type": "municipality_letter", "source_title": "synthetic test fixture",
    "source_date": "2026-01-01", "source_calendar": "gregorian", "source_verified": True,
    "source_revision": "fixture-v1", "valid_from": "2026-01-01", "valid_until": "2027-12-31",
}
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=16))
PASSWORD = "correct horse battery"


def parcel(points):
    return {"shape": "polygon", "vertices": [{"x": x, "y": y} for x, y in points]}


def assigned(data, roles=None):
    out = copy.deepcopy(data)
    count = 4 if out["shape"] == "rectangular" else len(out["vertices"])
    roles = roles or ["front"] * count
    out["setback_edges"] = [{"edge_index": i, "role": role} for i, role in enumerate(roles)]
    return out


class GeometryReferenceTests(unittest.TestCase):
    def test_rectangle_metrics_and_explicit_unknown_north(self):
        result = analyze(RECT)
        self.assertEqual((result["area_m2"], result["perimeter_m"]), (200, 60))
        self.assertEqual(result["bounds_m"], [0, 0, 10, 20])
        self.assertEqual(result["orientation"], "counterclockwise")
        self.assertIsNone(result["edges"][0]["north_bearing_deg"])
        self.assertEqual(result["edges"][0]["local_bearing_deg"], 90)
        self.assertEqual(analyze(RECT, {"north_angle_deg": 30})["edges"][0]["north_bearing_deg"], 60)

    def test_triangle_concavity_translation_and_reversal(self):
        self.assertEqual(analyze(parcel([(0, 0), (4, 0), (0, 3)]))["area_m2"], 6)
        for points in (L_POINTS, list(reversed(L_POINTS)),
                       [(x + 6000000, y + 6000000) for x, y in L_POINTS]):
            result = analyze(parcel(points))
            self.assertEqual((result["area_m2"], result["perimeter_m"]), (75, 40))
        tiny = [(6000000, 6000000), (6000000.01, 6000000),
                (6000000.01, 6000000.01), (6000000, 6000000.01)]
        self.assertAlmostEqual(polygon_area(tiny), 0.0001, places=9)

    def test_units_produce_identical_canonical_geometry(self):
        for unit, multiple in (("m", 1), ("cm", 100), ("mm", 1000)):
            data = {"shape": "rectangular", "width_m": 10 * multiple, "depth_m": 20 * multiple,
                    "declared_area_m2": 200}
            result = analyze(canonicalize(data, unit))
            self.assertEqual((result["area_m2"], result["perimeter_m"]), (200, 60))
            poly = canonicalize(parcel([(x * multiple, y * multiple) for x, y in L_POINTS]), unit)
            self.assertEqual(analyze(poly)["area_m2"], 75)

    def test_no_implicit_projection_and_no_unit_guess(self):
        for data, unit, code in ((RECT, "feet", "unsupported_unit"),
                                 ({**RECT, "geometry_reference": "EPSG:4326"}, "m", "unsupported_reference")):
            with self.assertRaises(GeometryError) as raised:
                canonicalize(data, unit)
            self.assertEqual(raised.exception.code, code)

    def test_invalid_and_boundary_inputs_never_return_plausible_areas(self):
        cases = [([], "too_few_points"), ([(0, 0), (1, 0)], "too_few_points"),
                 ([(0, 0), (1, 0), (0, 0)], "duplicate_vertex"),
                 ([(0, 0), (1, 1), (2, 2)], "degenerate"),
                 ([(0, 0), (10, 10), (10, 0), (0, 8)], "self_intersecting"),
                 ([(0, 0), (1e-9, 0), (1, 1)], "zero_length_edge")]
        for points, code in cases:
            with self.subTest(code=code), self.assertRaises(GeometryError) as raised:
                analyze(parcel(points))
            self.assertEqual(raised.exception.code, code)
        for value in (math.inf, -math.inf, math.nan, True, "NaN"):
            with self.subTest(value=value), self.assertRaises(GeometryError):
                analyze({**RECT, "width_m": value})
        with self.assertRaises(GeometryError):
            analyze(parcel([(0, 0)] * 201))

    def test_discrepancy_classification_uses_unrounded_numbers(self):
        result = analyze({"shape": "rectangular", "width_m": 10.1004, "depth_m": 10,
                          "declared_area_m2": 100})
        self.assertEqual(result["area_status"], "discrepancy")
        self.assertGreater(result["difference_percent"], 1)

    def test_asymmetric_setbacks_match_hand_reference_conservatively(self):
        data = assigned(RECT, ["front", "right", "rear", "left"])
        result = buildable_envelope(data, {**SOURCE, "front_m": 2, "rear_m": 3,
                                          "left_m": 1, "right_m": 2}, today=TODAY)
        # (10-1-2)*(20-2-3) = 105 m², with <=1 mm conservative over-clearance.
        self.assertEqual(result["status"], "computed")
        self.assertLessEqual(result["area_m2"], 105)
        self.assertAlmostEqual(result["area_m2"], 105, delta=0.1)
        for x, y in result["polygons"][0]["exterior"]:
            self.assertTrue(1 <= x <= 8 and 2 <= y <= 17)

    def test_zero_is_explicit_empty_is_not_a_default(self):
        self.assertEqual(buildable_envelope(assigned(RECT), {**SOURCE, "front_m": 0}, today=TODAY)["area_m2"], 200)
        self.assertEqual(buildable_envelope(assigned(RECT), SOURCE, today=TODAY)["status"], "needs_inquiry")
        self.assertEqual(buildable_envelope(assigned(RECT), {**SOURCE, "front_m": 20}, today=TODAY)["status"], "empty")

    def test_sources_and_complete_edge_mapping_gate_envelope(self):
        valid = {**SOURCE, "front_m": 1}
        for change, expected in (({"source_verified": False}, "source_not_verified"),
                                 ({"source_revision": ""}, "source_revision"),
                                 ({"valid_from": "2024-01-01", "valid_until": "2025-12-31"}, "source_expired"),
                                 ({"valid_from": "2027-01-01"}, "source_not_yet_valid"),
                                 ({"correction_notes": "requires specialist"}, "correction_needs_human_review")):
            result = buildable_envelope(assigned(RECT), {**valid, **change}, today=TODAY)
            self.assertEqual(result["status"], "needs_inquiry")
            self.assertIn(expected, result["reasons"])
            self.assertIsNone(result["area_m2"])
        self.assertIn("edge_mapping_required", buildable_envelope(RECT, valid, today=TODAY)["reasons"])

    def test_concave_and_split_outputs_are_not_convex_hulls(self):
        result = buildable_envelope(assigned(parcel(L_POINTS)), {**SOURCE, "front_m": 1}, today=TODAY)
        self.assertEqual(result["status"], "computed")
        self.assertLess(result["area_m2"], 75)
        # A narrow bridge between two squares disappears under clearance.
        dumbbell = [(0, 0), (4, 0), (4, 1.5), (8, 1.5), (8, 0), (12, 0),
                    (12, 4), (8, 4), (8, 2.5), (4, 2.5), (4, 4), (0, 4)]
        split = buildable_envelope(assigned(parcel(dumbbell)), {**SOURCE, "front_m": 0.6}, today=TODAY)
        self.assertEqual(len(split["polygons"]), 2)
        self.assertLessEqual(split["max_arc_overclearance_m"], ARC_ERROR_M)

    def test_coverage_limit_needs_its_own_valid_source(self):
        data, setbacks = assigned(RECT), {**SOURCE, "front_m": 0}
        self.assertIsNone(buildable_envelope(data, setbacks, {"max_coverage_percent": 60}, today=TODAY)["max_footprint_m2"])
        self.assertEqual(buildable_envelope(data, setbacks, {**SOURCE, "max_coverage_percent": 60}, today=TODAY)["max_footprint_m2"], 120)


class GeometryApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.directory.cleanup)
        engine = memory_engine()
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.sessions = create_session_factory(engine)
        self.session = self.sessions()
        self.addCleanup(self.session.close)
        self.owner = auth.register(self.session, POLICY, email="geom@example.com", display_name="Geometry", password=PASSWORD)
        org_id = self.session.scalar(select(Membership.organization_id).where(Membership.user_id == self.owner.id))
        self.project = create_project(self.session, self.owner, org_id, name="Geometry fixture", project_type="other")
        self.app = create_app(Settings(environment="test"), session_factory=self.sessions, auth_policy=POLICY)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        login = self.client.post("/api/v1/auth/login", json={"email": self.owner.email, "password": PASSWORD})
        self.headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        self.url = f"/api/v1/projects/{self.project.id}"

    def test_preview_converts_without_writing_then_save_and_reload(self):
        count = self.session.scalar(select(func.count()).select_from(ActivityEvent))
        response = self.client.post(self.url + "/geometry/preview", headers=self.headers,
                                    json={"data": {**RECT, "width_m": 1000, "depth_m": 2000}, "unit": "cm"})
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()
        self.assertEqual(report["area_m2"], 200)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(SiteSection)), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ActivityEvent)), count)
        saved = self.client.put(self.url + "/site/parcel", headers=self.headers,
                                json={"data": report["canonical_data"], "version": 0})
        self.assertEqual(saved.status_code, 200, saved.text)
        read = self.client.get(self.url + "/geometry").json()
        self.assertEqual((read["area_m2"], read["source_versions"]["parcel"]), (200, 1))
        self.assertEqual(read["input_hash"], report["input_hash"])

    def test_permissions_csrf_archive_and_cross_tenant(self):
        self.assertEqual(self.client.post(self.url + "/geometry/preview", json={"data": RECT}).status_code, 403)
        anonymous = TestClient(self.app)
        self.addCleanup(anonymous.close)
        self.assertEqual(anonymous.get(self.url + "/geometry").status_code, 401)
        other = auth.register(self.session, POLICY, email="outside@example.com", display_name="Outside", password=PASSWORD)
        login = anonymous.post("/api/v1/auth/login", json={"email": other.email, "password": PASSWORD})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(anonymous.get(self.url + "/geometry").status_code, 404)
        archive_project(self.session, self.owner, self.project.id)
        self.assertEqual(self.client.get(self.url + "/geometry").status_code, 200)
        self.assertEqual(self.client.post(self.url + "/geometry/preview", headers=self.headers,
                                         json={"data": RECT}).status_code, 403)

    def test_source_change_is_visible_without_cached_envelope(self):
        site_service.save_section(self.session, self.owner, self.project.id, "parcel", assigned(RECT), 0)
        zoning_service.save_record(self.session, self.owner, self.project.id, "setbacks", {**SOURCE, "front_m": 0}, 0)
        first = geometry_service.get_geometry(self.session, self.owner, self.project.id)
        self.assertEqual(first["envelope"]["area_m2"], 200)
        zoning_service.save_record(self.session, self.owner, self.project.id, "setbacks", {**SOURCE, "front_m": 1}, 1)
        second = geometry_service.get_geometry(self.session, self.owner, self.project.id)
        self.assertEqual(second["source_versions"]["setbacks"], 2)
        self.assertLess(second["envelope"]["area_m2"], 200)

    def test_invalid_geometry_is_422_and_never_saved(self):
        response = self.client.post(self.url + "/geometry/preview", headers=self.headers,
                                    json={"data": parcel([(0, 0), (10, 10), (10, 0), (0, 8)])})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(SiteSection)), 0)
