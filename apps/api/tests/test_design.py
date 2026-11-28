"""ARCH-003: editing the base design model; locks reject edits with an explicit reason."""

import copy
import tempfile
import unittest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from smart_engineer_api import (
    ai_design_service,
    design_service,
    design_version_service,
    layout_service,
    org_service,
    project_service,
    requirements_service,
    site_service,
    zoning_service,
)
from smart_engineer_api import auth_service as auth
from smart_engineer_api import space_schedule_service as schedules
from smart_engineer_api.ai_design import AiError
from smart_engineer_api.config import Settings
from smart_engineer_api.db import ActivityEvent, Base, DesignHistory, DesignModel, Membership
from smart_engineer_api.db.session import create_session_factory
from smart_engineer_api.design_compare import compare_models
from smart_engineer_api.design_model import (
    DesignError,
    apply_operations,
    empty_model,
    snap_value,
    wall_length,
)
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from tests.geometry_helpers import memory_engine
from tests.test_ai_design import ScriptedClient
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

    def test_lengths_are_converted_exactly_from_m_cm_and_mm(self):
        spec = {"type": "space", "kind": "living"}
        cm = apply_operations(empty_model(), [{"op": "add", "element": {
            **spec, "x": 150, "y": 33.3, "width": 400, "height": 250.5}}], unit="cm")
        mm = apply_operations(empty_model(), [{"op": "add", "element": {
            **spec, "x": 1500, "y": 333, "width": 4000, "height": 2505}}], unit="mm")
        metres = apply_operations(empty_model(), [{"op": "add", "element": {
            **spec, "x": 1.5, "y": 0.333, "width": 4, "height": 2.505}}])
        self.assertEqual(cm, mm)
        self.assertEqual(cm, metres)
        moved = apply_operations(metres, [{"op": "move", "id": "E-0001", "dx": 250, "dy": -10}],
                                 unit="cm")
        self.assertEqual((element(moved, "E-0001")["x"], element(moved, "E-0001")["y"]),
                         (4.0, 0.233))
        door = apply_operations(base(), [{"op": "move", "id": "E-0003", "along_m": 300}],
                                unit="cm")
        self.assertEqual(element(door, "E-0003")["offset_m"], 4.0)

    def test_rotation_degrees_are_not_scaled_by_the_length_unit(self):
        turned = apply_operations(base(), [{"op": "rotate", "id": "E-0001", "degrees": 90}],
                                  unit="mm")
        self.assertEqual(element(turned, "E-0001")["rotation_deg"], 90)

    def test_snap_rounds_changed_geometry_to_the_grid(self):
        model = apply_operations(empty_model(), [{"op": "add", "element": {
            "type": "space", "kind": "living", "x": 1.234, "y": -0.275, "width": 3.97,
            "height": 2.51}}], snap={"grid": 5, "unit": "cm"})
        space = element(model, "E-0001")
        self.assertEqual((space["x"], space["y"], space["width"], space["height"]),
                         (1.25, -0.3, 3.95, 2.5))
        coarse = apply_operations(model, [{"op": "move", "id": "E-0001", "dx": 0.04, "dy": 0}],
                                  snap={"grid": 0.5})
        self.assertEqual(element(coarse, "E-0001")["x"], 1.5)
        untouched = apply_operations(model, [{"op": "lock", "id": "E-0001"}], snap={"grid": 1})
        self.assertEqual(element(untouched, "E-0001")["x"], 1.25)
        rotated = apply_operations(model, [{"op": "rotate", "id": "E-0001", "degrees": 90}],
                                   snap={"grid": 1})
        self.assertEqual(element(rotated, "E-0001")["width"], 2.5)

    def test_snap_ties_round_away_from_zero_and_never_collapse_elements(self):
        for value, expected in ((0.125, 0.15), (-0.125, -0.15), (0.12, 0.1)):
            self.assertEqual(snap_value(value, Decimal("0.05")), expected)
        small = apply_operations(empty_model(), [{"op": "add", "element": SPACE}])
        with self.assertRaises(DesignError) as collapse:
            apply_operations(small, [{"op": "resize", "id": "E-0001", "width": 0.02,
                                      "height": 2}], snap={"grid": 10, "unit": "cm"})
        self.assertEqual((collapse.exception.code, collapse.exception.element_id),
                         ("snap_collapses_element", "E-0001"))
        with self.assertRaises(DesignError) as flat:
            apply_operations(base(), [{"op": "resize", "id": "E-0004", "width_m": 0.4}],
                             snap={"grid": 1})
        self.assertEqual((flat.exception.code, flat.exception.element_id),
                         ("snap_collapses_element", "E-0004"))
        for bad in ({"grid": 0.0001}, {"grid": 1000}, {"grid": "x"}, {"grid": True}, {}, 5):
            with self.assertRaises(DesignError) as invalid:
                apply_operations(small, [{"op": "lock", "id": "E-0001"}], snap=bad)
            self.assertEqual(invalid.exception.code, "invalid_snap", bad)
        with self.assertRaises(DesignError) as unit:
            apply_operations(small, [{"op": "lock", "id": "E-0001"}], unit="ft")
        self.assertEqual(unit.exception.code, "invalid_unit")

    def test_copying_a_floor_creates_new_stable_ids_and_keeps_geometry_and_relationships(self):
        model = base()
        element(model, "E-0001")["schedule_space_id"] = "SP-1"
        element(model, "E-0004")["locked"] = True
        copied = apply_operations(model, [
            {"op": "copy_floor", "from_floor": 1, "to_floors": [2, 3]}])
        self.assertEqual(copied["next_id"], 13)
        upper = [e for e in copied["elements"] if e["floor"] == 2]
        self.assertEqual(len(upper), 4)
        ids = [e["id"] for e in copied["elements"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({e["copied_from"] for e in upper},
                         {"E-0001", "E-0002", "E-0003", "E-0004"})
        by_source = {e["copied_from"]: e for e in upper}
        for source in ("E-0001", "E-0002"):
            original = element(model, source)
            for key in ("x", "y", "width", "height", "x1", "y1", "x2", "y2", "kind",
                        "thickness_m", "rotation_deg"):
                self.assertEqual(by_source[source].get(key), original.get(key))
        self.assertNotIn("schedule_space_id", by_source["E-0001"])
        wall_copy = by_source["E-0002"]["id"]
        self.assertEqual((by_source["E-0003"]["wall_id"], by_source["E-0003"]["offset_m"]),
                         (wall_copy, 1))
        self.assertEqual(by_source["E-0004"]["wall_id"], wall_copy)
        self.assertTrue(by_source["E-0004"]["locked"])
        self.assertEqual(element(copied, "E-0001"), element(model, "E-0001"))
        self.assertEqual(len([e for e in copied["elements"] if e["floor"] == 3]), 4)

    def test_copy_floor_never_overwrites_and_rejects_bad_requests(self):
        model = base()
        two = apply_operations(model, [{"op": "copy_floor", "from_floor": 1, "to_floors": [2]}])
        self.assertEqual(failure(two, [{"op": "copy_floor", "from_floor": 1, "to_floors": [2]}]),
                         ("floor_not_empty", 0, None))
        self.assertEqual(failure(model, [{"op": "copy_floor", "from_floor": 4, "to_floors": [5]}]),
                         ("unknown_floor", 0, None))
        for bad in ({"from_floor": 1, "to_floors": [1]}, {"from_floor": 1, "to_floors": [2, 2]},
                    {"from_floor": 1, "to_floors": []}, {"from_floor": 1, "to_floors": [99]},
                    {"from_floor": 1}, {"from_floor": 1, "to_floors": "2"}):
            self.assertEqual(failure(model, [{"op": "copy_floor", **bad}]),
                             ("invalid_value", 0, None), bad)
        self.assertEqual(failure(model, [{"op": "lock", "id": "E-0001"},
                                         {"op": "copy_floor", "from_floor": 1, "to_floors": [2]},
                                         {"op": "copy_floor", "from_floor": 1,
                                          "to_floors": [2]}]),
                         ("floor_not_empty", 2, None))

    def test_vertical_connections_must_point_at_floors_that_exist(self):
        model = apply_operations(base(), [
            {"op": "copy_floor", "from_floor": 1, "to_floors": [2]},
            {"op": "add", "element": {"type": "vertical", "kind": "stair", "floors": [1, 2],
                                      "x": 0, "y": 0, "width": 1, "height": 3}}])
        stair = model["elements"][-1]
        self.assertEqual((stair["floors"], stair["floor"], stair["locked"]), ([1, 2], 1, False))
        self.assertEqual(failure(model, [{"op": "set_floors", "id": stair["id"],
                                          "floors": [1, 3]}]),
                         ("vertical_invalid_level", 0, stair["id"]))
        self.assertEqual(failure(base(), [{"op": "add", "element": {
            "type": "vertical", "kind": "elevator", "floors": [1, 2], "x": 0, "y": 0,
            "width": 1, "height": 1}}]), ("vertical_invalid_level", 0, "E-0005"))
        for bad in ({"floors": [1]}, {"floors": [1, 1]}, {"floors": "12"},
                    {"floors": [1, 2], "kind": "ladder"}):
            spec = {"type": "vertical", "kind": "stair", "x": 0, "y": 0, "width": 1,
                    "height": 1, **bad}
            self.assertEqual(failure(model, [{"op": "add", "element": spec}]),
                             ("invalid_value", 0, None), bad)
        widened = apply_operations(model, [{"op": "set_floors", "id": stair["id"],
                                            "floors": [2, 1]}])
        self.assertEqual(element(widened, stair["id"])["floors"], [1, 2])
        moved = apply_operations(model, [{"op": "move", "id": stair["id"], "dx": 1, "dy": 0},
                                         {"op": "resize", "id": stair["id"], "width": 2,
                                          "height": 4}, {"op": "rotate", "id": stair["id"],
                                                         "degrees": 90}])
        turned = element(moved, stair["id"])
        self.assertEqual((turned["x"], turned["width"], turned["height"], turned["rotation_deg"]),
                         (0, 4, 2, 90))
        self.assertEqual(failure(model, [{"op": "set_floors", "id": "E-0001", "floors": [1, 2]}]),
                         ("operation_not_supported", 0, "E-0001"))

    def test_emptying_a_floor_that_a_vertical_connection_uses_is_rejected(self):
        model = apply_operations(base(), [
            {"op": "copy_floor", "from_floor": 1, "to_floors": [2]},
            {"op": "add", "element": {"type": "vertical", "kind": "shaft", "floors": [1, 2],
                                      "x": 0, "y": 0, "width": 1, "height": 1}}])
        upper = [e["id"] for e in model["elements"] if e["floor"] == 2 and e["type"] != "vertical"]
        deletions = [{"op": "delete", "id": item} for item in upper
                     if element(model, item)["type"] in ("space", "wall")]
        self.assertEqual(failure(model, deletions)[0], "vertical_invalid_level")
        self.assertIsNone(failure(model, [{"op": "lock", "id": "E-0001"}]))

    def test_compare_matches_elements_by_stable_id_and_lists_every_changed_field(self):
        before = base()
        after = apply_operations(before, [
            {"op": "move", "id": "E-0001", "dx": 1, "dy": 0},
            {"op": "lock", "id": "E-0001"},
            {"op": "delete", "id": "E-0002"},
            {"op": "add", "element": SPACE}])
        diff = compare_models(before, after)
        self.assertEqual(diff["summary"], {"added": 1, "removed": 3, "changed": 1})
        self.assertEqual({e["id"] for e in diff["removed"]}, {"E-0002", "E-0003", "E-0004"})
        self.assertEqual(diff["changed"][0]["id"], "E-0001")
        self.assertEqual({f["field"] for f in diff["changed"][0]["fields"]}, {"x", "locked"})
        self.assertEqual(compare_models(before, before)["summary"],
                         {"added": 0, "removed": 0, "changed": 0})
        self.assertEqual(compare_models(before, before)["unchanged"], 4)


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


    def import_and_edit(self):
        self.prepare_layouts()
        made = self.importing()
        first = made["data"]["elements"][0]["id"]
        return made, first

    def test_undo_then_redo_restores_the_exact_states(self):
        made, first = self.import_and_edit()
        self.assertEqual((made["can_undo"], made["can_redo"], made["history_position"]),
                         (False, False, 1))
        one = self.edit([{"op": "move", "id": first, "dx": 1, "dy": 0}], 1)
        two = self.edit([{"op": "lock", "id": first}], 2)
        self.assertEqual((two["can_undo"], two["can_redo"], two["history_position"]),
                         (True, False, 3))
        back = design_service.undo_design(self.session, self.owner, self.project.id,
                                          expected_version=3)
        self.assertEqual((back["data"], back["can_redo"], back["version"]),
                         (one["data"], True, 4))
        again = design_service.undo_design(self.session, self.owner, self.project.id,
                                           expected_version=4)
        self.assertEqual((again["data"], again["can_undo"]), (made["data"], False))
        with self.assertRaises(design_service.DesignServiceError) as floor:
            design_service.undo_design(self.session, self.owner, self.project.id,
                                       expected_version=5)
        self.assertEqual(floor.exception.code, "nothing_to_undo")
        forward = design_service.redo_design(self.session, self.owner, self.project.id,
                                             expected_version=5)
        last = design_service.redo_design(self.session, self.owner, self.project.id,
                                          expected_version=6)
        self.assertEqual((forward["data"], last["data"]), (one["data"], two["data"]))
        self.assertEqual((last["can_redo"], last["version"]), (False, 7))
        with self.assertRaises(design_service.DesignServiceError) as top:
            design_service.redo_design(self.session, self.owner, self.project.id,
                                       expected_version=7)
        self.assertEqual(top.exception.code, "nothing_to_redo")
        stored = self.session.scalar(select(DesignModel))
        self.assertEqual((stored.data, stored.head_seq), (two["data"], 3))

    def test_a_new_edit_after_undo_discards_the_redo_side(self):
        made, first = self.import_and_edit()
        self.edit([{"op": "move", "id": first, "dx": 1, "dy": 0}], 1)
        design_service.undo_design(self.session, self.owner, self.project.id, expected_version=2)
        branch = self.edit([{"op": "move", "id": first, "dx": 0, "dy": 2}], 3)
        self.assertEqual((branch["can_redo"], branch["history_position"],
                          branch["history_length"]), (False, 2, 2))
        sequence = [row.seq for row in self.session.scalars(
            select(DesignHistory).order_by(DesignHistory.seq))]
        self.assertEqual(sequence, [1, 2])

    def test_undo_redo_conflicts_roles_and_audit(self):
        qs = self.user("qs")
        _, token = org_service.create_invitation(
            self.session, self.owner, self.org, email=qs.email, org_role="member")
        org_service.accept_invitation(self.session, qs, token)
        project_service.add_member(self.session, self.owner, self.project.id,
                                   email=qs.email, role="quantity_surveyor")
        made, first = self.import_and_edit()
        self.edit([{"op": "lock", "id": first}], 1)
        with self.assertRaises(design_service.DesignServiceError) as stale:
            design_service.undo_design(self.session, self.owner, self.project.id,
                                       expected_version=1)
        self.assertEqual(stale.exception.code, "version_conflict")
        with self.assertRaises(AccessDenied):
            design_service.undo_design(self.session, qs, self.project.id, expected_version=2)
        done = design_service.undo_design(self.session, self.owner, self.project.id,
                                          expected_version=2)
        self.assertFalse(done["data"]["elements"][0]["locked"])
        actions = [e.action for e in self.session.scalars(select(ActivityEvent).order_by(
            ActivityEvent.created_at))]
        self.assertIn("project.design_undone", actions)
        history = design_service.design_history(self.session, qs, self.project.id)
        self.assertEqual((history["position"], [e["seq"] for e in history["entries"]],
                          [e["current"] for e in history["entries"]]),
                         (1, [2, 1], [False, True]))
        self.assertEqual(history["entries"][0]["summary"]["operations"],
                         [{"op": "lock", "id": first}])
        self.assertEqual(history["entries"][0]["actor"], "owner")

    def test_designs_without_history_get_a_baseline_and_old_entries_are_pruned(self):
        made, first = self.import_and_edit()
        self.session.query(DesignHistory).delete()
        row = self.session.scalar(select(DesignModel))
        row.head_seq = 0
        self.session.commit()
        legacy = design_service.get_design(self.session, self.owner, self.project.id)
        self.assertEqual((legacy["can_undo"], legacy["can_redo"]), (False, False))
        edited = self.edit([{"op": "lock", "id": first}], 1)
        self.assertEqual((edited["history_position"], edited["can_undo"]), (2, True))
        undone = design_service.undo_design(self.session, self.owner, self.project.id,
                                            expected_version=2)
        self.assertEqual(undone["data"], made["data"])
        original = design_service.HISTORY_LIMIT
        design_service.HISTORY_LIMIT = 3
        self.addCleanup(setattr, design_service, "HISTORY_LIMIT", original)
        version = undone["version"]
        for _ in range(5):
            version = self.edit([{"op": "move", "id": first, "dx": 1, "dy": 0}],
                                version)["version"]
        low = self.session.scalar(select(func.min(DesignHistory.seq)))
        high = self.session.scalar(select(func.max(DesignHistory.seq)))
        self.assertEqual((high - low + 1), 3)
        for expected in (version, version + 1):
            design_service.undo_design(self.session, self.owner, self.project.id,
                                       expected_version=expected)
        with self.assertRaises(design_service.DesignServiceError) as pruned:
            design_service.undo_design(self.session, self.owner, self.project.id,
                                       expected_version=version + 2)
        self.assertEqual(pruned.exception.code, "nothing_to_undo")

    def test_unit_and_snap_apply_to_stored_edits(self):
        made, first = self.import_and_edit()
        edited = design_service.edit_design(
            self.session, self.owner, self.project.id, expected_version=1, unit="cm",
            snap={"grid": 5, "unit": "cm"},
            operations=[{"op": "add", "element": {
                "type": "space", "kind": "storage", "x": 1234, "y": 5, "width": 197,
                "height": 251}}])
        added = edited["data"]["elements"][-1]
        self.assertEqual((added["x"], added["y"], added["width"], added["height"]),
                         (12.35, 0.05, 1.95, 2.5))
        entry = design_service.design_history(self.session, self.owner,
                                              self.project.id)["entries"][0]
        self.assertEqual((entry["summary"]["unit"], entry["summary"]["snap"]),
                         ("cm", {"grid": 5, "unit": "cm"}))

    def test_copying_floors_is_one_undoable_step_with_a_history_summary(self):
        made, first = self.import_and_edit()
        copied = self.edit([{"op": "copy_floor", "from_floor": 1, "to_floors": [2]}], 1)
        count = len(made["data"]["elements"])
        self.assertEqual(len(copied["data"]["elements"]), count * 2)
        entry = design_service.design_history(self.session, self.owner,
                                              self.project.id)["entries"][0]
        self.assertEqual(entry["summary"]["operations"], [{"op": "copy_floor", "id": None}])
        back = design_service.undo_design(self.session, self.owner, self.project.id,
                                          expected_version=2)
        self.assertEqual(back["data"], made["data"])
        again = design_service.redo_design(self.session, self.owner, self.project.id,
                                           expected_version=3)
        self.assertEqual(again["data"], copied["data"])
        with self.assertRaises(DesignError) as clash:
            self.edit([{"op": "copy_floor", "from_floor": 1, "to_floors": [2]}], 4)
        self.assertEqual(clash.exception.code, "floor_not_empty")

    def member(self, name, role):
        user = self.user(name)
        _, token = org_service.create_invitation(
            self.session, self.owner, self.org, email=user.email, org_role="member")
        org_service.accept_invitation(self.session, user, token)
        project_service.add_member(self.session, self.owner, self.project.id,
                                   email=user.email, role=role)
        return user

    def save(self, label, version, actor=None):
        return design_version_service.save_version(
            self.session, actor or self.owner, self.project.id, label=label,
            expected_version=version)

    def test_saved_versions_are_immutable_snapshots_with_author_and_label(self):
        qs = self.member("qs", "quantity_surveyor")
        with self.assertRaises(design_service.DesignServiceError) as none:
            self.save("x", 1)
        self.assertEqual(none.exception.code, "no_design")
        made, first = self.import_and_edit()
        one = self.save("  اولیه  ", 1)
        self.assertEqual((one["number"], one["label"], one["author"], one["element_count"]),
                         (1, "اولیه", "owner", len(made["data"]["elements"])))
        edited = self.edit([{"op": "move", "id": first, "dx": 1, "dy": 0}], 1)
        two = self.save("بعد از جابه‌جایی", edited["version"])
        self.assertEqual(two["number"], 2)
        stored = design_version_service.get_version(self.session, qs, self.project.id, 1)
        self.assertEqual(stored["data"], made["data"])
        names = [v["label"] for v in design_version_service.list_versions(
            self.session, qs, self.project.id)["versions"]]
        self.assertEqual(names, ["بعد از جابه‌جایی", "اولیه"])
        for bad in ("", "   ", "x" * 121):
            with self.assertRaises(design_service.DesignServiceError) as invalid:
                self.save(bad, edited["version"])
            self.assertEqual(invalid.exception.code, "invalid_value")
        with self.assertRaises(design_service.DesignServiceError) as stale:
            self.save("late", 1)
        self.assertEqual(stale.exception.code, "version_conflict")
        with self.assertRaises(AccessDenied):
            self.save("not allowed", edited["version"], actor=qs)
        with self.assertRaises(design_service.DesignServiceError) as unknown:
            design_version_service.get_version(self.session, qs, self.project.id, 9)
        self.assertEqual(unknown.exception.code, "unknown_version")
        self.assertIn("project.design_version_saved", [e.action for e in self.session.scalars(
            select(ActivityEvent))])

    def test_comparing_versions_identifies_added_removed_and_changed_elements(self):
        made, first = self.import_and_edit()
        self.save("v1", 1)
        second = self.edit([
            {"op": "move", "id": first, "dx": 2, "dy": 0},
            {"op": "add", "element": {"type": "space", "kind": "storage", "x": 50, "y": 50,
                                      "width": 2, "height": 2}},
            {"op": "delete", "id": made["data"]["elements"][1]["id"]}], 1)
        self.save("v2", second["version"])
        diff = design_version_service.compare_versions(
            self.session, self.owner, self.project.id, "1", "2")
        gone = made["data"]["elements"][1]["id"]
        self.assertEqual(diff["summary"], {"added": 1, "removed": 1, "changed": 1})
        self.assertEqual([e["id"] for e in diff["removed"]], [gone])
        self.assertEqual(diff["changed"][0]["id"], first)
        self.assertEqual([f["field"] for f in diff["changed"][0]["fields"]], ["x"])
        self.assertEqual((diff["from"]["number"], diff["to"]["number"]), (1, 2))
        self.assertEqual(design_version_service.compare_versions(
            self.session, self.owner, self.project.id, "2", "current")["summary"],
            {"added": 0, "removed": 0, "changed": 0})
        later = design_version_service.compare_versions(
            self.session, self.owner, self.project.id, "1", "current")
        self.assertEqual(later["to"]["number"], None)
        self.assertEqual(later["summary"], diff["summary"])
        for ref in ("7", "abc"):
            with self.assertRaises(design_service.DesignServiceError) as unknown:
                design_version_service.compare_versions(
                    self.session, self.owner, self.project.id, "1", ref)
            self.assertEqual(unknown.exception.code, "unknown_version")

    def test_comments_attach_to_a_version_and_an_existing_element_id(self):
        qs = self.member("qs", "quantity_surveyor")
        made, first = self.import_and_edit()
        self.save("v1", 1)
        edited = self.edit([{"op": "delete", "id": first}], 1)
        self.save("v2", edited["version"])
        comment = design_version_service.add_comment(
            self.session, qs, self.project.id, 1, body="  عرض کم است ", element_id=first)
        self.assertEqual((comment["author"], comment["element_id"], comment["version_number"],
                          comment["body"]), ("qs", first, 1, "عرض کم است"))
        # the element no longer exists in version 2, so a comment there is refused
        with self.assertRaises(design_service.DesignServiceError) as gone:
            design_version_service.add_comment(self.session, qs, self.project.id, 2,
                                               body="x", element_id=first)
        self.assertEqual(gone.exception.code, "unknown_element")
        whole = design_version_service.add_comment(self.session, self.owner, self.project.id,
                                                   2, body="کل طرح")
        self.assertIsNone(whole["element_id"])
        for bad in ("", "  ", "y" * 2001):
            with self.assertRaises(design_service.DesignServiceError) as invalid:
                design_version_service.add_comment(self.session, qs, self.project.id, 1, body=bad)
            self.assertEqual(invalid.exception.code, "invalid_value")
        with self.assertRaises(design_service.DesignServiceError) as unknown:
            design_version_service.add_comment(self.session, qs, self.project.id, 5, body="x")
        self.assertEqual(unknown.exception.code, "unknown_version")
        shown = design_version_service.get_version(self.session, qs, self.project.id, 1)
        self.assertEqual([c["body"] for c in shown["comments"]], ["عرض کم است"])
        other = design_version_service.get_version(self.session, qs, self.project.id, 2)
        self.assertEqual([c["body"] for c in other["comments"]], ["کل طرح"])
        counts = {v["number"]: v["comment_count"] for v in design_version_service.list_versions(
            self.session, qs, self.project.id)["versions"]}
        self.assertEqual(counts, {1: 1, 2: 1})
        outsider = self.user("outsider")
        with self.assertRaises(AccessDenied):
            design_version_service.add_comment(self.session, outsider, self.project.id, 1,
                                               body="hi")

    def test_versions_http_round_trip(self):
        self.prepare_layouts()
        client = TestClient(create_app(Settings(environment="test"),
                                       session_factory=self.sessions, auth_policy=POLICY))
        self.addCleanup(client.close)
        login = client.post("/api/v1/auth/login",
                            json={"email": self.owner.email, "password": PASSWORD})
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        url = f"/api/v1/projects/{self.project.id}/design"
        client.post(f"{url}/import-layout", headers=headers,
                    json={"alternative_id": "ALT-1", "version": 0})
        saved = client.post(f"{url}/versions", headers=headers, json={"version": 1, "label": "A"})
        self.assertEqual((saved.status_code, saved.json()["number"]), (201, 1))
        stale = client.post(f"{url}/versions", headers=headers, json={"version": 9, "label": "B"})
        self.assertEqual((stale.status_code, stale.json()["error"]["code"]),
                         (409, "version_conflict"))
        client.post(f"{url}/edit", headers=headers, json={"version": 1, "operations": [
            {"op": "lock", "id": "E-0001"}]})
        compared = client.get(f"{url}/compare", params={"a": "1", "b": "current"})
        self.assertEqual(compared.status_code, 200, compared.text)
        self.assertEqual(compared.json()["changed"][0]["fields"],
                         [{"field": "locked", "before": False, "after": True}])
        comment = client.post(f"{url}/versions/1/comments", headers=headers,
                              json={"body": "نکته", "element_id": "E-0001"})
        self.assertEqual((comment.status_code, comment.json()["element_id"]), (201, "E-0001"))
        detail = client.get(f"{url}/versions/1").json()
        self.assertEqual((detail["label"], len(detail["comments"])), ("A", 1))
        missing = client.get(f"{url}/versions/5")
        self.assertEqual((missing.status_code, missing.json()["error"]["code"]),
                         (404, "unknown_version"))
        bad = client.post(f"{url}/versions/1/comments", headers=headers,
                          json={"body": "x", "element_id": "E-9999"})
        self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (422, "unknown_element"))
        self.assertEqual(client.post(f"{url}/versions", json={"version": 1, "label": "C"})
                         .status_code, 403)

    def test_claude_proposals_are_advisory_dry_run_and_limited(self):
        qs = self.member("qs", "quantity_surveyor")
        made, first = self.import_and_edit()
        settings = Settings(environment="test", anthropic_api_key="sk-x")
        good = {"summary": "نشیمن را جابه‌جا کن",
                "operations": [{"op": "move", "id": first, "dx": 1, "dy": 0}]}
        bad = {"summary": "bad", "operations": [{"op": "move", "id": "E-9999", "dx": 1, "dy": 0}]}

        def ask(client, actor=None, instruction="بزرگ‌تر کن"):
            return ai_design_service.propose_design(
                self.session, actor or self.owner, self.project.id, client=client,
                settings=settings, instruction=instruction)

        with self.assertRaises(AiError) as off:
            ask(None)
        self.assertEqual(off.exception.code, "ai_not_configured")
        result = ask(ScriptedClient(good))
        self.assertEqual((result["valid"], result["base_version"], result["attempts"],
                          result["operations"], result["model"]),
                         (True, 1, 1, good["operations"], "claude-sonnet-5-5"))
        stored = self.session.scalar(select(DesignModel))
        self.assertEqual((stored.version, stored.data), (1, made["data"]))  # nothing applied
        retried = ask(ScriptedClient(bad, good))
        self.assertEqual((retried["valid"], retried["attempts"]), (True, 2))
        invalid = ask(ScriptedClient(bad, bad))
        self.assertEqual((invalid["valid"], invalid["error"]["code"]), (False, "unknown_element"))
        events = [e.detail for e in self.session.scalars(select(ActivityEvent).where(
            ActivityEvent.action == "project.design_ai_proposed"))]
        self.assertEqual([(d["valid"], d["attempts"]) for d in events],
                         [(True, 1), (True, 2), (False, 2)])
        with self.assertRaises(AccessDenied):
            ask(ScriptedClient(good), actor=qs)
        with self.assertRaises(design_service.DesignServiceError) as long:
            ask(ScriptedClient(good), instruction="x" * 1001)
        self.assertEqual(long.exception.code, "invalid_value")
        for _ in range(ai_design_service.DAILY_PROPOSAL_LIMIT - len(events)):
            self.session.add(ActivityEvent(
                project_id=self.project.id, actor_user_id=self.owner.id,
                action="project.design_ai_proposed", detail={}))
        self.session.commit()
        with self.assertRaises(AiError) as limited:
            ask(ScriptedClient(good))
        self.assertEqual(limited.exception.code, "ai_limit_reached")

    def test_claude_proposal_needs_an_imported_design(self):
        settings = Settings(environment="test", anthropic_api_key="sk-x")
        with self.assertRaises(design_service.DesignServiceError) as none:
            ai_design_service.propose_design(
                self.session, self.owner, self.project.id,
                client=ScriptedClient({"summary": "", "operations": []}),
                settings=settings, instruction="")
        self.assertEqual(none.exception.code, "no_design")

    def test_claude_proposal_http_round_trip_applies_only_through_edit(self):
        self.prepare_layouts()
        first = "E-0001"
        good = {"summary": "ok", "operations": [{"op": "lock", "id": first}]}
        client = ScriptedClient(good)
        app = create_app(Settings(environment="test", anthropic_api_key="sk-x"),
                         session_factory=self.sessions, auth_policy=POLICY, ai_client=client)
        http = TestClient(app)
        self.addCleanup(http.close)
        login = http.post("/api/v1/auth/login",
                          json={"email": self.owner.email, "password": PASSWORD})
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        url = f"/api/v1/projects/{self.project.id}/design"
        self.assertEqual(http.get(f"{url}/ai-status").json(),
                         {"enabled": True, "model": "claude-sonnet-5-5"})
        none = http.post(f"{url}/ai-proposal", headers=headers, json={"instruction": "x"})
        self.assertEqual((none.status_code, none.json()["error"]["code"]), (409, "no_design"))
        http.post(f"{url}/import-layout", headers=headers,
                  json={"alternative_id": "ALT-1", "version": 0})
        self.assertEqual(http.post(f"{url}/ai-proposal", json={}).status_code, 403)
        proposal = http.post(f"{url}/ai-proposal", headers=headers,
                             json={"instruction": "قفل کن"})
        self.assertEqual(proposal.status_code, 200, proposal.text)
        body = proposal.json()
        self.assertEqual((body["valid"], body["base_version"]), (True, 1))
        self.assertFalse(http.get(url).json()["data"]["elements"][0]["locked"])
        applied = http.post(f"{url}/edit", headers=headers, json={
            "version": body["base_version"], "operations": body["operations"]})
        self.assertEqual(applied.status_code, 200, applied.text)
        self.assertTrue(applied.json()["data"]["elements"][0]["locked"])
        self.assertEqual(http.post(f"{url}/undo", headers=headers, json={"version": 2})
                         .status_code, 200)
        self.assertNotIn("sk-x", proposal.text + http.get(f"{url}/ai-status").text)

    def test_claude_without_a_key_is_reported_as_not_configured(self):
        self.prepare_layouts()
        app = create_app(Settings(environment="test"), session_factory=self.sessions,
                         auth_policy=POLICY)
        http = TestClient(app)
        self.addCleanup(http.close)
        login = http.post("/api/v1/auth/login",
                          json={"email": self.owner.email, "password": PASSWORD})
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        url = f"/api/v1/projects/{self.project.id}/design"
        self.assertEqual(http.get(f"{url}/ai-status").json(), {"enabled": False, "model": None})
        refused = http.post(f"{url}/ai-proposal", headers=headers, json={})
        self.assertEqual((refused.status_code, refused.json()["error"]["code"]),
                         (503, "ai_not_configured"))

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

        scaled = client.post(f"{url}/edit", headers=headers, json={
            "version": 2, "unit": "cm", "snap": {"grid": 10},
            "operations": [{"op": "add", "element": {
                "type": "space", "kind": "storage", "x": 103, "y": 0, "width": 200,
                "height": 150}}]})
        self.assertEqual(scaled.status_code, 200, scaled.text)
        self.assertEqual([scaled.json()["data"]["elements"][-1][k]
                          for k in ("x", "width", "height")], [1.0, 2.0, 1.5])
        undone = client.post(f"{url}/undo", headers=headers, json={"version": 3})
        self.assertEqual((undone.status_code, undone.json()["can_redo"]), (200, True))
        redone = client.post(f"{url}/redo", headers=headers, json={"version": 4})
        self.assertEqual(redone.json()["data"], scaled.json()["data"])
        self.assertEqual(client.get(f"{url}/history").json()["position"], 3)
        nothing = client.post(f"{url}/redo", headers=headers, json={"version": 5})
        self.assertEqual((nothing.status_code, nothing.json()["error"]["code"]),
                         (409, "nothing_to_redo"))
        for payload, code in (({"unit": "ft"}, "validation_error"),
                              ({"snap": {"grid": 0}}, "validation_error")):
            bad = client.post(f"{url}/edit", headers=headers, json={
                "version": 5, "operations": [{"op": "lock", "id": "E-0001"}], **payload})
            self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (422, code))
        tiny = client.post(f"{url}/edit", headers=headers, json={
            "version": 5, "snap": {"grid": 0.0001},
            "operations": [{"op": "lock", "id": "E-0001"}]})
        self.assertEqual((tiny.status_code, tiny.json()["error"]["code"]),
                         (422, "invalid_snap"))


if __name__ == "__main__":
    unittest.main()
