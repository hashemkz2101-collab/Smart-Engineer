"""ARCH-002: conceptual layout alternatives (distinct options or a specific infeasibility)."""

import copy
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import (
    layout_service,
    org_service,
    project_service,
    requirements_service,
    site_service,
    zoning_service,
)
from smart_engineer_api import space_schedule_service as schedules
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Base, Membership
from smart_engineer_api.db.session import create_session_factory
from smart_engineer_api.layout import EPS, _overlaps, generate_alternatives
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from smart_engineer_api.space_schedule import build_schedule
from tests.geometry_helpers import memory_engine

POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=16))
PASSWORD = "correct horse battery"
SOURCE = {
    "source_type": "municipality_letter", "source_title": "synthetic test fixture",
    "source_date": "2026-01-01", "source_calendar": "gregorian", "source_verified": True,
    "source_revision": "fixture-v1", "valid_from": "2026-01-01", "valid_until": "2099-12-31",
}
RECT = {"shape": "rectangular", "width_m": 16, "depth_m": 10,
        "setback_edges": [{"edge_index": i, "role": "front" if i == 0 else "rear"}
                          for i in range(4)]}
PROGRAM = {
    "units_count": 1, "floors_count": 2,
    "rooms": [
        {"kind": "living", "count": 1, "target_area_m2": 30.0},
        {"kind": "reception", "count": 1, "target_area_m2": 40.0},
        {"kind": "kitchen", "count": 1, "target_area_m2": 14.0},
        {"kind": "bedroom", "count": 2, "target_area_m2": 14.0},
        {"kind": "master_bedroom", "count": 1, "area_min_m2": 16.0, "area_max_m2": 24.0},
        {"kind": "bathroom", "count": 2, "target_area_m2": 6.0},
        {"kind": "yard", "count": 1, "target_area_m2": 50.0},
        {"kind": "parking", "count": 1},
        {"kind": "office", "count": 1},
    ],
}
ENVELOPE = {"status": "computed", "reasons": [], "max_footprint_m2": None,
            "polygons": [{"exterior": [[0, 0], [16, 0], [16, 10], [0, 10]], "holes": []}]}
SPACES = build_schedule(PROGRAM, 1)["spaces"]
FRONT = [((0, 0), (16, 0))]


def rects(alternative):
    return [
        [(p["x"], p["y"], p["x"] + p["width"], p["y"] + p["height"]) for p in f["placements"]]
        for f in alternative["floors"]
    ]


class GeneratorTests(unittest.TestCase):
    def test_two_or_more_distinct_alternatives_with_criteria_and_limits(self):
        result = generate_alternatives(ENVELOPE, SPACES, 2, FRONT)
        self.assertEqual((result["status"], result["reasons"]), ("alternatives", []))
        alternatives = result["alternatives"]
        self.assertGreaterEqual(len(alternatives), 2)
        self.assertEqual(len({a["strategy"] for a in alternatives}), len(alternatives))
        for alt in alternatives:
            self.assertTrue(alt["criteria"] and alt["limitations"] and alt["not_evaluated"])
            self.assertIn("regulation_compliance", alt["not_evaluated"])

    def test_every_space_is_placed_or_reported_with_a_reason(self):
        result = generate_alternatives(ENVELOPE, SPACES, 2, FRONT)
        wanted = sorted(s["id"] for s in SPACES)
        for alt in result["alternatives"]:
            placed = [p["space_id"] for f in alt["floors"] for p in f["placements"]]
            unplaced = {u["space_id"]: u["reason"] for u in alt["unplaced"]}
            self.assertEqual(sorted(placed + list(unplaced)), wanted)
            self.assertEqual(
                sorted(set(unplaced.values())),
                ["area_not_given", "outdoor_space_not_modelled", "parking_not_modelled"],
            )

    def test_blocks_stay_inside_the_envelope_and_never_overlap(self):
        for alt in generate_alternatives(ENVELOPE, SPACES, 2, FRONT)["alternatives"]:
            for floor in rects(alt):
                for i, a in enumerate(floor):
                    self.assertTrue(a[0] >= -1e-6 and a[1] >= -1e-6)
                    self.assertTrue(a[2] <= 16 + 1e-6 and a[3] <= 10 + 1e-6)
                    for b in floor[i + 1:]:
                        self.assertFalse(_overlaps(a, b))
            for floor in alt["floors"]:
                for p in floor["placements"]:
                    self.assertAlmostEqual(p["width"] * p["height"], p["area_m2"], places=6)

    def test_area_basis_is_recorded_and_ranges_use_their_midpoint(self):
        alt = generate_alternatives(ENVELOPE, SPACES, 2, FRONT)["alternatives"][0]
        placed = {p["kind"]: p for f in alt["floors"] for p in f["placements"]}
        self.assertEqual((placed["master_bedroom"]["area_m2"], placed["master_bedroom"]["area_basis"]),
                         (20.0, "range_midpoint"))
        self.assertEqual(placed["living"]["area_basis"], "target")

    def test_privacy_strategy_puts_public_rooms_nearer_the_front_than_bedrooms(self):
        alt = next(a for a in generate_alternatives(ENVELOPE, SPACES, 1, FRONT)["alternatives"]
                   if a["strategy"] == "privacy_bands")
        ground = alt["floors"][0]["placements"]

        def mean_y(kind):
            ys = [p["y"] + p["height"] / 2 for p in ground if p["kind"] == kind]
            return sum(ys) / len(ys)

        self.assertLess(mean_y("living"), mean_y("bedroom"))
        self.assertEqual(alt["assumptions"], [])
        unknown = generate_alternatives(ENVELOPE, SPACES, 2, [])["alternatives"][0]
        self.assertEqual(unknown["assumptions"], ["front_edge_not_identified_lowest_y_used"])

    def test_generation_is_deterministic_and_does_not_change_inputs(self):
        spaces, envelope = copy.deepcopy(SPACES), copy.deepcopy(ENVELOPE)
        self.assertEqual(generate_alternatives(envelope, spaces, 2, FRONT),
                         generate_alternatives(ENVELOPE, SPACES, 2, FRONT))
        self.assertEqual((spaces, envelope), (SPACES, ENVELOPE))

    def test_specific_infeasibility_results(self):
        blocked = {"status": "needs_inquiry", "reasons": ["front_m_required"], "polygons": []}
        self.assertEqual(generate_alternatives(blocked, SPACES, 1, [])["reasons"],
                         ["envelope_not_computed", "front_m_required"])
        empty = {"status": "empty", "reasons": [], "polygons": []}
        self.assertEqual(generate_alternatives(empty, SPACES, 1, [])["reasons"], ["envelope_empty"])
        self.assertEqual(generate_alternatives(ENVELOPE, [], 1, [])["reasons"],
                         ["no_spaces_in_schedule"])
        outdoor = [{"id": "S-001", "kind": "yard", "target_area_m2": 40.0}]
        self.assertEqual(generate_alternatives(ENVELOPE, outdoor, 1, [])["reasons"],
                         ["no_placeable_spaces"])
        big = [{"id": "S-001", "kind": "living", "target_area_m2": 500.0}]
        result = generate_alternatives(ENVELOPE, big, 2, [])
        self.assertEqual((result["status"], result["reasons"]),
                         ("infeasible", ["required_area_exceeds_capacity"]))
        self.assertEqual((result["details"]["required_area_m2"], result["details"]["capacity_m2"]),
                         (500.0, 320.0))
        many = [{"id": f"S-{i:03d}", "kind": "storage", "target_area_m2": 1.0} for i in range(121)]
        self.assertEqual(generate_alternatives(ENVELOPE, many, 1, [])["reasons"],
                         ["too_many_spaces_for_conceptual_layout"])

    def test_one_block_alternatives_are_not_called_distinct(self):
        square = {**ENVELOPE, "polygons": [
            {"exterior": [[0, 0], [10, 0], [10, 10], [0, 10]], "holes": []}]}
        single = [{"id": "S-001", "kind": "living", "target_area_m2": 100.0}]
        result = generate_alternatives(square, single, 1, [])
        self.assertEqual((result["status"], result["reasons"]),
                         ("infeasible", ["fewer_than_two_distinct_alternatives"]))
        self.assertEqual(len(result["alternatives"]), 1)

    def test_coverage_limit_caps_net_area_per_floor_and_leftovers_are_reported(self):
        capped = {**ENVELOPE, "max_footprint_m2": 60.0}
        too_small = generate_alternatives(capped, SPACES, 2, FRONT)
        self.assertEqual(too_small["reasons"], ["required_area_exceeds_capacity"])
        result = generate_alternatives(capped, SPACES, 3, FRONT)
        self.assertTrue(result["alternatives"])
        for alt in result["alternatives"]:
            self.assertTrue(all(f["used_area_m2"] <= 60.0 + EPS for f in alt["floors"]))
            self.assertGreaterEqual(alt["metrics"]["floors_used"], 3 - (0 if alt["metrics"]["fully_placed"] else 1))


class LayoutServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.directory.cleanup)
        engine = memory_engine()
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.sessions = create_session_factory(engine)
        self.session = self.sessions()
        self.addCleanup(self.session.close)
        self.owner = self.user("owner")
        self.org = self.session.scalar(
            select(Membership.organization_id).where(Membership.user_id == self.owner.id))
        self.project = project_service.create_project(
            self.session, self.owner, self.org, name="Layouts", project_type="residential_house")

    def user(self, name):
        return auth.register(self.session, POLICY, email=f"{name}@example.com",
                             display_name=name, password=PASSWORD)

    def prepare(self, *, parcel=True, setbacks=True, schedule=True):
        pid = self.project.id
        if parcel:
            site_service.save_section(self.session, self.owner, pid, "parcel", RECT, 0)
        if setbacks:
            zoning_service.save_record(self.session, self.owner, pid, "setbacks",
                                       {**SOURCE, "front_m": 0, "rear_m": 0}, 0)
        requirements_service.save_section(self.session, self.owner, pid, "program", PROGRAM, 0)
        if schedule:
            schedules.generate_schedule(self.session, self.owner, pid, 0)

    def generate(self, version=0, actor=None):
        return layout_service.generate_layouts(
            self.session, actor or self.owner, self.project.id, version)

    def test_missing_inputs_give_specific_persisted_infeasibility(self):
        empty = layout_service.get_layouts(self.session, self.owner, self.project.id)
        self.assertEqual((empty["exists"], empty["version"]), (False, 0))
        first = self.generate()
        self.assertEqual((first["data"]["status"], first["data"]["reasons"]),
                         ("infeasible", ["parcel_invalid_or_missing"]))
        self.assertEqual(first["version"], 1)
        self.prepare(schedule=False)
        again = self.generate(1)
        self.assertEqual(again["data"]["reasons"], ["space_schedule_missing"])
        self.prepare_schedule_only()

    def prepare_schedule_only(self):
        schedules.generate_schedule(self.session, self.owner, self.project.id, 0)
        done = self.generate(2)
        self.assertEqual(done["data"]["status"], "alternatives", done["data"])

    def test_full_chain_records_sources_and_goes_stale_when_inputs_change(self):
        self.prepare()
        made = self.generate()
        data = made["data"]
        self.assertEqual((data["status"], made["stale"]), ("alternatives", False))
        self.assertGreaterEqual(len(data["alternatives"]), 2)
        self.assertEqual(data["sources"]["versions"],
                         {"parcel": 1, "access": 0, "setbacks": 1, "coverage": 0,
                          "space_schedule": 1})
        self.assertEqual(layout_service.get_layouts(self.session, self.owner,
                                                    self.project.id)["data"], data)
        zoning_service.save_record(self.session, self.owner, self.project.id, "setbacks",
                                   {**SOURCE, "front_m": 1, "rear_m": 1}, 1)
        self.assertTrue(layout_service.get_layouts(self.session, self.owner,
                                                   self.project.id)["stale"])
        with self.assertRaises(layout_service.LayoutError) as conflict:
            self.generate(0)
        self.assertEqual(conflict.exception.code, "version_conflict")
        fresh = self.generate(1)
        self.assertEqual((fresh["version"], fresh["stale"]), (2, False))

    def test_stale_schedule_is_refused_rather_than_used(self):
        self.prepare()
        requirements_service.save_section(
            self.session, self.owner, self.project.id, "program",
            {**PROGRAM, "floors_count": 3}, 1)
        self.assertEqual(self.generate()["data"]["reasons"], ["space_schedule_stale"])

    def test_roles_archive_and_activity(self):
        qs, stranger = self.user("qs"), self.user("stranger")
        _, token = org_service.create_invitation(
            self.session, self.owner, self.org, email=qs.email, org_role="member")
        org_service.accept_invitation(self.session, qs, token)
        project_service.add_member(self.session, self.owner, self.project.id,
                                   email=qs.email, role="quantity_surveyor")
        self.prepare()
        self.generate()
        self.assertTrue(layout_service.get_layouts(self.session, qs, self.project.id)["exists"])
        with self.assertRaises(AccessDenied) as denied:
            self.generate(1, actor=qs)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            layout_service.get_layouts(self.session, stranger, self.project.id)
        self.assertTrue(hidden.exception.hidden)
        last = project_service.list_activity(self.session, self.owner, self.project.id)[-1]
        self.assertEqual((last.action, last.detail["status"]), ("project.layouts_generated",
                                                                "alternatives"))
        project_service.archive_project(self.session, self.owner, self.project.id)
        with self.assertRaises(AccessDenied):
            self.generate(1)

    def test_http_round_trip(self):
        self.prepare()
        app = create_app(Settings(environment="test"), session_factory=self.sessions,
                         auth_policy=POLICY)
        client = TestClient(app)
        self.addCleanup(client.close)
        login = client.post("/api/v1/auth/login",
                            json={"email": self.owner.email, "password": PASSWORD})
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        url = f"/api/v1/projects/{self.project.id}/layouts"
        self.assertFalse(client.get(url).json()["exists"])
        self.assertEqual(client.post(f"{url}/generate", json={"version": 0}).status_code, 403)
        ok = client.post(f"{url}/generate", headers=headers, json={"version": 0})
        self.assertEqual((ok.status_code, ok.json()["data"]["status"]), (200, "alternatives"))
        again = client.post(f"{url}/generate", headers=headers, json={"version": 0})
        self.assertEqual((again.status_code, again.json()["error"]["code"]),
                         (409, "version_conflict"))
        self.assertEqual(client.get(url).json()["data"], ok.json()["data"])


if __name__ == "__main__":
    unittest.main()
