"""ARCH-003: editing the base design model; locks reject edits with an explicit reason."""

import copy
import tempfile
import unittest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

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
from smart_engineer_api.db import ActivityEvent, Base, DesignHistory, DesignModel, Membership
from smart_engineer_api.db.session import create_session_factory
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
