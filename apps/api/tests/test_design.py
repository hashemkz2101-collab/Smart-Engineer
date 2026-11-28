"""ARCH-003: editing the base design model; locks reject edits with an explicit reason."""

import copy
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import (
    design_service,
    layout_service,
    org_service,
    project_service,
    requirements_service,
    site_service,
    zoning_service,
)
from smart_engineer_api import space_schedule_service as schedules
from smart_engineer_api.config import Settings
from smart_engineer_api.db import ActivityEvent, Base, Membership
from smart_engineer_api.db.session import create_session_factory
from smart_engineer_api.design_model import (
    DesignError,
    apply_operations,
    empty_model,
    wall_length,
)
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from tests.geometry_helpers import memory_engine
from tests.test_layout import PASSWORD, POLICY, PROGRAM, RECT, SOURCE

SPACE = {"type": "space", "kind": "living", "x": 0, "y": 0, "width": 5, "height": 4}
WALL = {"type": "wall", "x1": 0, "y1": 0, "x2": 6, "y2": 0, "thickness_m": 0.2}


def base():
    return apply_operations(empty_model(), [
        {"op": "add", "element": SPACE},
        {"op": "add", "element": WALL},
        {"op": "add", "element": {"type": "door", "wall_id": "E-0002", "offset_m": 1,
                                  "width_m": 0.9}},
        {"op": "add", "element": {"type": "window", "wall_id": "E-0002", "offset_m": 3,
                                  "width_m": 1.2, "sill_m": 0.9, "height_m": 1.2}},
    ])


def element(model, element_id):
    return next(e for e in model["elements"] if e["id"] == element_id)


def failure(model, operations):
    with_error = None
    try:
        apply_operations(model, operations)
    except DesignError as error:
        with_error = (error.code, error.index, error.element_id)
    return with_error


class ModelTests(unittest.TestCase):
    def test_add_assigns_stable_ids_that_are_never_reused(self):
        model = base()
        self.assertEqual([e["id"] for e in model["elements"]],
                         ["E-0001", "E-0002", "E-0003", "E-0004"])
        after = apply_operations(model, [{"op": "delete", "id": "E-0004"},
                                         {"op": "add", "element": SPACE}])
        self.assertEqual(after["elements"][-1]["id"], "E-0005")
        self.assertEqual(element(after, "E-0001"), element(model, "E-0001"))

    def test_move_resize_rotate_a_space(self):
        model = apply_operations(base(), [
            {"op": "move", "id": "E-0001", "dx": 2, "dy": -1.5},
            {"op": "resize", "id": "E-0001", "width": 6, "height": 3},
        ])
        space = element(model, "E-0001")
        self.assertEqual((space["x"], space["y"], space["width"], space["height"]),
                         (2, -1.5, 6, 3))
        turned = apply_operations(model, [{"op": "rotate", "id": "E-0001", "degrees": 90}])
        space = element(turned, "E-0001")
        self.assertEqual((space["width"], space["height"], space["rotation_deg"]), (3, 6, 90))
        self.assertAlmostEqual(space["x"] + space["width"] / 2, 5.0)
        self.assertAlmostEqual(space["y"] + space["height"] / 2, 0.0)
        around = apply_operations(turned, [{"op": "rotate", "id": "E-0001", "degrees": 270}])
        self.assertEqual((element(around, "E-0001")["rotation_deg"],
                          element(around, "E-0001")["width"]), (0, 6))
        self.assertEqual(failure(model, [{"op": "rotate", "id": "E-0001", "degrees": 45}]),
                         ("rotation_must_be_multiple_of_90", 0, "E-0001"))

    def test_wall_edits_carry_hosted_openings_and_protect_their_fit(self):
        model = apply_operations(base(), [{"op": "move", "id": "E-0002", "dx": 1, "dy": 2}])
        wall = element(model, "E-0002")
        self.assertEqual((wall["x1"], wall["y1"], wall["x2"], wall["y2"]), (1, 2, 7, 2))
        self.assertEqual(element(model, "E-0003")["offset_m"], 1)
        longer = apply_operations(model, [{"op": "resize", "id": "E-0002", "length_m": 9}])
        self.assertAlmostEqual(wall_length(element(longer, "E-0002")), 9)
        self.assertEqual(failure(model, [{"op": "resize", "id": "E-0002", "length_m": 3}]),
                         ("hosted_opening_outside_wall", 0, "E-0004"))
        turned = apply_operations(model, [{"op": "rotate", "id": "E-0002", "degrees": 90}])
        self.assertAlmostEqual(wall_length(element(turned, "E-0002")), 6)
        self.assertAlmostEqual(element(turned, "E-0002")["x1"], element(turned, "E-0002")["x2"])
        gone = apply_operations(model, [{"op": "delete", "id": "E-0002"}])
        self.assertEqual([e["id"] for e in gone["elements"]], ["E-0001"])

    def test_openings_move_along_the_wall_and_stay_inside_it(self):
        moved = apply_operations(base(), [{"op": "move", "id": "E-0003", "along_m": 1.5},
                                          {"op": "resize", "id": "E-0004", "width_m": 2}])
        self.assertEqual((element(moved, "E-0003")["offset_m"], element(moved, "E-0004")["width_m"]),
                         (2.5, 2))
        self.assertEqual(failure(base(), [{"op": "move", "id": "E-0004", "along_m": 2}]),
                         ("opening_outside_wall", 0, "E-0004"))
        self.assertEqual(failure(base(), [{"op": "move", "id": "E-0003", "along_m": -2}]),
                         ("opening_outside_wall", 0, "E-0003"))
        self.assertEqual(failure(base(), [{"op": "rotate", "id": "E-0003", "degrees": 90}]),
                         ("operation_not_supported", 0, "E-0003"))
        self.assertEqual(failure(base(), [{"op": "add", "element": {
            "type": "door", "wall_id": "E-0001", "offset_m": 0, "width_m": 1}}]),
            ("wrong_host_type", 0, "E-0001"))
        self.assertEqual(failure(base(), [{"op": "add", "element": {
            "type": "opening", "wall_id": "E-0002", "offset_m": 5.5, "width_m": 1}}]),
            ("opening_outside_wall", 0, "E-0002"))

    def test_locked_elements_reject_every_edit_but_unlock_with_a_reason(self):
        locked = apply_operations(base(), [{"op": "lock", "id": "E-0001"}])
        self.assertTrue(element(locked, "E-0001")["locked"])
        for operation in (
            {"op": "move", "id": "E-0001", "dx": 1, "dy": 0},
            {"op": "resize", "id": "E-0001", "width": 2, "height": 2},
            {"op": "rotate", "id": "E-0001", "degrees": 90},
            {"op": "delete", "id": "E-0001"},
            {"op": "set", "id": "E-0001", "fields": {"name": "x"}},
        ):
            self.assertEqual(failure(locked, [operation]), ("element_locked", 0, "E-0001"))
        freed = apply_operations(locked, [{"op": "unlock", "id": "E-0001"},
                                          {"op": "move", "id": "E-0001", "dx": 1, "dy": 0}])
        self.assertEqual((element(freed, "E-0001")["locked"], element(freed, "E-0001")["x"]),
                         (False, 1))
        self.assertEqual(locked, apply_operations(locked, [{"op": "lock", "id": "E-0001"}]))

    def test_a_locked_opening_pins_its_wall(self):
        pinned = apply_operations(base(), [{"op": "lock", "id": "E-0003"}])
        for operation in (
            {"op": "move", "id": "E-0002", "dx": 1, "dy": 0},
            {"op": "rotate", "id": "E-0002", "degrees": 10},
            {"op": "delete", "id": "E-0002"},
        ):
            self.assertEqual(failure(pinned, [operation]), ("hosted_element_locked", 0, "E-0003"))

    def test_a_batch_is_atomic_and_inputs_are_not_modified(self):
        model = base()
        before = copy.deepcopy(model)
        self.assertEqual(
            failure(model, [{"op": "move", "id": "E-0001", "dx": 1, "dy": 0},
                            {"op": "move", "id": "E-9999", "dx": 1, "dy": 0}]),
            ("unknown_element", 1, "E-9999"))
        self.assertEqual(model, before)

    def test_invalid_values_are_rejected_not_clamped(self):
        for bad in (
            {**SPACE, "width": 0}, {**SPACE, "width": float("nan")}, {**SPACE, "x": 1e9},
            {**SPACE, "x": True}, {**SPACE, "kind": ""}, {**SPACE, "floor": 0},
            {**WALL, "x2": 0}, {**WALL, "thickness_m": 3}, {"type": "roof"}, "space",
        ):
            self.assertEqual(failure(empty_model(), [{"op": "add", "element": bad}])[0],
                             "invalid_value", bad)
        self.assertEqual(failure(empty_model(), [{"op": "explode"}])[0], "unknown_operation")
        self.assertEqual(failure(empty_model(), [])[0], "invalid_value")
        self.assertEqual(failure(empty_model(), [{"op": "noop"}] * 51)[0], "too_many_operations")

    def test_set_changes_only_allowed_text_fields(self):
        model = apply_operations(base(), [
            {"op": "set", "id": "E-0001", "fields": {"name": "اتاق نشیمن", "kind": "reception"}}])
        self.assertEqual((element(model, "E-0001")["name"], element(model, "E-0001")["kind"]),
                         ("اتاق نشیمن", "reception"))
        for fields in ({"x": 3}, {}, {"name": ""}):
            self.assertEqual(failure(model, [{"op": "set", "id": "E-0001", "fields": fields}])[0],
                             "invalid_value")


class DesignServiceTests(unittest.TestCase):
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
            self.session, self.owner, self.org, name="Design", project_type="residential_house")

    def user(self, name):
        return auth.register(self.session, POLICY, email=f"{name}@example.com",
                             display_name=name, password=PASSWORD)

    def prepare_layouts(self):
        pid = self.project.id
        site_service.save_section(self.session, self.owner, pid, "parcel", RECT, 0)
        zoning_service.save_record(self.session, self.owner, pid, "setbacks",
                                   {**SOURCE, "front_m": 0, "rear_m": 0}, 0)
        requirements_service.save_section(self.session, self.owner, pid, "program", PROGRAM, 0)
        schedules.generate_schedule(self.session, self.owner, pid, 0)
        return layout_service.generate_layouts(self.session, self.owner, pid, 0)

    def importing(self, version=0, alternative="ALT-1", replace=False, actor=None):
        return design_service.import_layout(
            self.session, actor or self.owner, self.project.id, alternative_id=alternative,
            expected_version=version, replace=replace)

    def edit(self, operations, version, actor=None):
        return design_service.edit_design(
            self.session, actor or self.owner, self.project.id, operations=operations,
            expected_version=version)

    def test_import_creates_stable_space_elements_linked_to_the_schedule(self):
        empty = design_service.get_design(self.session, self.owner, self.project.id)
        self.assertEqual((empty["exists"], empty["version"]), (False, 0))
        with self.assertRaises(design_service.DesignServiceError) as none:
            self.importing()
        self.assertEqual(none.exception.code, "no_layout")
        layouts = self.prepare_layouts()
        made = self.importing()
        alternative = layouts["data"]["alternatives"][0]
        placements = [p for f in alternative["floors"] for p in f["placements"]]
        elements = made["data"]["elements"]
        self.assertEqual(len(elements), len(placements))
        self.assertEqual([e["id"] for e in elements][:2], ["E-0001", "E-0002"])
        self.assertEqual([e["schedule_space_id"] for e in elements],
                         [p["space_id"] for p in placements])
        self.assertEqual(made["data"]["source"]["layout_version"], layouts["version"])
        self.assertEqual((made["version"], made["layout_changed"]), (1, False))
        self.assertEqual(design_service.get_design(self.session, self.owner,
                                                   self.project.id)["data"], made["data"])

    def test_edit_persists_and_failures_write_nothing(self):
        self.prepare_layouts()
        made = self.importing()
        first = made["data"]["elements"][0]["id"]
        edited = self.edit([{"op": "move", "id": first, "dx": 1, "dy": 1},
                            {"op": "lock", "id": first}], 1)
        self.assertEqual(edited["version"], 2)
        reread = design_service.get_design(self.session, self.owner, self.project.id)
        self.assertTrue(reread["data"]["elements"][0]["locked"])
        events = self.session.scalars(
            select(ActivityEvent).where(ActivityEvent.action == "project.design_edited")).all()
        self.assertEqual(len(events), 1)
        with self.assertRaises(DesignError) as locked:
            self.edit([{"op": "move", "id": first, "dx": 5, "dy": 0}], 2)
        self.assertEqual((locked.exception.code, locked.exception.element_id), ("element_locked", first))
        with self.assertRaises(design_service.DesignServiceError) as stale:
            self.edit([{"op": "unlock", "id": first}], 1)
        self.assertEqual(stale.exception.code, "version_conflict")
        after = design_service.get_design(self.session, self.owner, self.project.id)
        self.assertEqual((after["version"], after["data"]), (2, reread["data"]))
        self.assertEqual(len(self.session.scalars(select(ActivityEvent).where(
            ActivityEvent.action == "project.design_edited")).all()), 1)

    def test_import_needs_explicit_replace_and_follows_layout_staleness(self):
        self.prepare_layouts()
        self.importing()
        with self.assertRaises(design_service.DesignServiceError) as exists:
            self.importing(1, "ALT-2")
        self.assertEqual(exists.exception.code, "design_exists")
        with self.assertRaises(design_service.DesignServiceError) as missing:
            self.importing(1, "ALT-9", replace=True)
        self.assertEqual(missing.exception.code, "alternative_not_found")
        replaced = self.importing(1, "ALT-2", replace=True)
        self.assertEqual((replaced["version"], replaced["data"]["source"]["alternative_id"]),
                         (2, "ALT-2"))
        zoning_service.save_record(self.session, self.owner, self.project.id, "setbacks",
                                   {**SOURCE, "front_m": 1, "rear_m": 1}, 1)
        with self.assertRaises(design_service.DesignServiceError) as stale:
            self.importing(2, "ALT-1", replace=True)
        self.assertEqual(stale.exception.code, "layout_stale")
        layout_service.generate_layouts(self.session, self.owner, self.project.id, 1)
        self.assertTrue(design_service.get_design(self.session, self.owner,
                                                  self.project.id)["layout_changed"])

    def test_edit_without_a_design_and_role_checks(self):
        qs, stranger = self.user("qs"), self.user("stranger")
        _, token = org_service.create_invitation(
            self.session, self.owner, self.org, email=qs.email, org_role="member")
        org_service.accept_invitation(self.session, qs, token)
        project_service.add_member(self.session, self.owner, self.project.id,
                                   email=qs.email, role="quantity_surveyor")
        with self.assertRaises(design_service.DesignServiceError) as nothing:
            self.edit([{"op": "lock", "id": "E-0001"}], 0)
        self.assertEqual(nothing.exception.code, "no_design")
        self.prepare_layouts()
        self.importing()
        self.assertTrue(design_service.get_design(self.session, qs, self.project.id)["exists"])
        with self.assertRaises(AccessDenied) as denied:
            self.edit([{"op": "lock", "id": "E-0001"}], 1, actor=qs)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            design_service.get_design(self.session, stranger, self.project.id)
        self.assertTrue(hidden.exception.hidden)
        project_service.archive_project(self.session, self.owner, self.project.id)
        with self.assertRaises(AccessDenied):
            self.edit([{"op": "lock", "id": "E-0001"}], 1)

    def test_http_round_trip_with_explicit_lock_reason(self):
        self.prepare_layouts()
        client = TestClient(create_app(Settings(environment="test"),
                                       session_factory=self.sessions, auth_policy=POLICY))
        self.addCleanup(client.close)
        login = client.post("/api/v1/auth/login",
                            json={"email": self.owner.email, "password": PASSWORD})
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        url = f"/api/v1/projects/{self.project.id}/design"
        self.assertFalse(client.get(url).json()["exists"])
        self.assertEqual(client.post(f"{url}/edit", json={"version": 0, "operations": [
            {"op": "lock", "id": "E-0001"}]}).status_code, 403)
        nothing = client.post(f"{url}/edit", headers=headers, json={"version": 0, "operations": [
            {"op": "lock", "id": "E-0001"}]})
        self.assertEqual((nothing.status_code, nothing.json()["error"]["code"]), (409, "no_design"))
        made = client.post(f"{url}/import-layout", headers=headers,
                           json={"alternative_id": "ALT-1", "version": 0})
        self.assertEqual(made.status_code, 200, made.text)
        locked = client.post(f"{url}/edit", headers=headers, json={"version": 1, "operations": [
            {"op": "lock", "id": "E-0001"}]})
        self.assertEqual((locked.status_code, locked.json()["version"]), (200, 2))
        refused = client.post(f"{url}/edit", headers=headers, json={"version": 2, "operations": [
            {"op": "move", "id": "E-0001", "dx": 1, "dy": 0}]})
        error = refused.json()["error"]
        self.assertEqual((refused.status_code, error["code"]), (409, "element_locked"))
        self.assertEqual(error["details"], [{"operation_index": 0, "element_id": "E-0001"}])
        invalid = client.post(f"{url}/edit", headers=headers, json={"version": 2, "operations": [
            {"op": "resize", "id": "E-0002", "width": -1, "height": 1}]})
        self.assertEqual((invalid.status_code, invalid.json()["error"]["code"]),
                         (422, "invalid_value"))
        self.assertEqual(client.get(url).json()["version"], 2)


if __name__ == "__main__":
    unittest.main()
