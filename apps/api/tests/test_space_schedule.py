"""ARCH-001: the space schedule built from the program (counts, ranges, flags)."""

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import org_service, project_service, requirements_service
from smart_engineer_api import space_schedule_service as schedules
from smart_engineer_api.config import Settings
from smart_engineer_api.db import ActivityEvent, Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from smart_engineer_api.space_schedule import build_schedule
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

# Approved fixture: 12 spaces, exact ranges, and one flag per kind of unmet requirement.
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
        {"kind": "yard"},
        {"kind": "bedroom", "count": 1, "target_area_m2": 30.0,
         "area_min_m2": 10.0, "area_max_m2": 20.0},
    ],
}
SMALL = {"units_count": 1, "floors_count": 1, "rooms": []}


def codes(schedule: dict) -> list[tuple]:
    return [(f["code"], f.get("room_index")) for f in schedule["flags"]]


class BuilderTests(unittest.TestCase):
    def test_counts_ranges_and_flags_match_the_fixture_exactly(self) -> None:
        schedule = build_schedule(PROGRAM, 3)
        self.assertEqual(len(schedule["spaces"]), 4 + 1 + 2 + 1 + 2 + 1 + 1)
        self.assertEqual([s["id"] for s in schedule["spaces"]][:2], ["S-001", "S-002"])
        self.assertEqual(len({s["id"] for s in schedule["spaces"]}), 12)
        per_room = {}
        for space in schedule["spaces"]:
            per_room[space["room_index"]] = per_room.get(space["room_index"], 0) + 1
        self.assertEqual(per_room, {0: 4, 1: 1, 2: 2, 3: 1, 4: 2, 5: 1, 6: 1})
        master = schedule["spaces"][4]
        self.assertEqual(
            (master["kind"], master["area_min_m2"], master["area_max_m2"], "target_area_m2" in master),
            ("master_bedroom", 16.0, 22.0, False),
        )
        totals = schedule["totals"]
        self.assertEqual(
            (totals["rooms"], totals["spaces"], totals["spaces_with_area"],
             totals["spaces_without_area"], totals["bounds_complete"]),
            (7, 12, 9, 3, False),
        )
        # lower: 4*14 + 16 + 2*12 + 40 + 10; upper: 4*14 + 22 + 2*12 + 40 + 20
        self.assertEqual((totals["area_lower_m2"], totals["area_upper_m2"]), (146.0, 162.0))
        self.assertEqual(
            codes(schedule),
            [("multi_unit_counts_not_multiplied", None), ("area_not_given", 4),
             ("count_not_given", 5), ("area_not_given", 5), ("target_outside_range", 6)],
        )
        self.assertEqual(schedule["source"]["program_version"], 3)
        self.assertEqual(schedule["counts_basis"], "as_listed")

    def test_generation_is_deterministic_and_input_is_not_modified(self) -> None:
        before = repr(PROGRAM)
        self.assertEqual(build_schedule(PROGRAM, 1), build_schedule(PROGRAM, 1))
        self.assertEqual(repr(PROGRAM), before)

    def test_unmet_requirements_are_flagged_not_dropped(self) -> None:
        empty = build_schedule(SMALL, 1)
        self.assertEqual((empty["spaces"], codes(empty)), ([], [("no_rooms", None)]))
        over = build_schedule(
            {"units_count": 1, "floors_count": 1, "target_area_max_m2": 50.0,
             "rooms": [{"kind": "living", "count": 2, "area_min_m2": 30.0}]}, 1)
        self.assertEqual(codes(over), [("program_exceeds_target_area", None)])
        under = build_schedule(
            {"units_count": 1, "floors_count": 1, "target_area_min_m2": 200.0,
             "rooms": [{"kind": "living", "count": 1, "target_area_m2": 30.0}]}, 1)
        self.assertEqual((codes(under), under["totals"]["bounds_complete"]),
                         ([("program_below_target_area", None)], True))
        outside = build_schedule(
            {"units_count": 1, "floors_count": 1, "target_area_m2": 500.0,
             "target_area_max_m2": 400.0, "rooms": [{"kind": "bedroom", "count": 1, "target_area_m2": 9.0}]}, 1)
        self.assertEqual(codes(outside), [("program_target_outside_range", None)])

    def test_below_target_is_not_claimed_while_some_areas_are_unknown(self) -> None:
        schedule = build_schedule(
            {"units_count": 1, "floors_count": 1, "target_area_min_m2": 200.0,
             "rooms": [{"kind": "living", "count": 1, "target_area_m2": 30.0},
                       {"kind": "kitchen", "count": 1}]}, 1)
        self.assertNotIn("program_below_target_area", [f["code"] for f in schedule["flags"]])
        self.assertFalse(schedule["totals"]["bounds_complete"])


class ScheduleChecks:
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

    def save_program(self, owner, project, data, version):
        return requirements_service.save_section(
            self.session, owner, project.id, "program", data, version)

    def test_generate_persists_and_reads_back_unchanged(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        empty = schedules.get_schedule(self.session, owner, project.id)
        self.assertEqual((empty["exists"], empty["version"], empty["program_ready"]),
                         (False, 0, False))
        with self.assertRaises(schedules.ScheduleError) as missing:
            schedules.generate_schedule(self.session, owner, project.id, 0)
        self.assertEqual(missing.exception.code, "program_incomplete")
        self.save_program(owner, project, {"units_count": 1}, 0)
        with self.assertRaises(schedules.ScheduleError):
            schedules.generate_schedule(self.session, owner, project.id, 0)

        self.save_program(owner, project, PROGRAM, 1)
        made = schedules.generate_schedule(self.session, owner, project.id, 0)
        self.assertEqual((made["exists"], made["version"], made["stale"]), (True, 1, False))
        self.assertEqual(made["data"], build_schedule(PROGRAM, 2))
        again = schedules.get_schedule(self.session, owner, project.id)
        self.assertEqual(again["data"], made["data"])
        self.assertEqual(len(again["data"]["spaces"]), 12)
        last = project_service.list_activity(self.session, owner, project.id)[-1]
        self.assertEqual(
            (last.action, last.detail),
            ("project.space_schedule_generated", {"spaces": 12, "flags": 5, "program_version": 2}),
        )

    def test_stale_after_program_change_and_regenerate_needs_current_version(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        self.save_program(owner, project, PROGRAM, 0)
        schedules.generate_schedule(self.session, owner, project.id, 0)
        changed = dict(PROGRAM, rooms=PROGRAM["rooms"][:2])
        self.save_program(owner, project, changed, 1)
        stale = schedules.get_schedule(self.session, owner, project.id)
        self.assertEqual((stale["stale"], len(stale["data"]["spaces"])), (True, 12))
        with self.assertRaises(schedules.ScheduleError) as conflict:
            schedules.generate_schedule(self.session, owner, project.id, 0)
        self.assertEqual(conflict.exception.code, "version_conflict")
        events = self.session.scalars(
            select(ActivityEvent).where(ActivityEvent.action == "project.space_schedule_generated")
        ).all()
        self.assertEqual(len(events), 1)
        fresh = schedules.generate_schedule(self.session, owner, project.id, 1)
        self.assertEqual((fresh["version"], fresh["stale"], len(fresh["data"]["spaces"])),
                         (2, False, 5))

    def test_roles_and_archived_projects(self) -> None:
        owner, arch, qs, stranger = (self.user(n) for n in ("owner", "arch", "qs", "stranger"))
        project = self.project(owner)
        for person, role in ((arch, "architect"), (qs, "quantity_surveyor")):
            _, token = org_service.create_invitation(
                self.session, owner, self.org_of(owner), email=person.email, org_role="member")
            org_service.accept_invitation(self.session, person, token)
            project_service.add_member(self.session, owner, project.id, email=person.email, role=role)
        self.save_program(owner, project, PROGRAM, 0)
        self.assertTrue(schedules.generate_schedule(self.session, arch, project.id, 0)["exists"])
        self.assertTrue(schedules.get_schedule(self.session, qs, project.id)["exists"])
        with self.assertRaises(AccessDenied) as denied:
            schedules.generate_schedule(self.session, qs, project.id, 1)
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied) as hidden:
            schedules.get_schedule(self.session, stranger, project.id)
        self.assertTrue(hidden.exception.hidden)
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            schedules.generate_schedule(self.session, owner, project.id, 1)

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
        url = f"{V1}/projects/{pid}/space-schedule"

        self.assertEqual(client.get(url).json()["exists"], False)
        self.assertEqual(client.post(f"{url}/generate", json={"version": 0}).status_code, 403)
        blocked = client.post(f"{url}/generate", headers=headers, json={"version": 0})
        self.assertEqual((blocked.status_code, blocked.json()["error"]["code"]),
                         (409, "program_incomplete"))
        client.put(f"{V1}/projects/{pid}/requirements/program", headers=headers,
                   json={"data": PROGRAM, "version": 0})
        ok = client.post(f"{url}/generate", headers=headers, json={"version": 0})
        self.assertEqual((ok.status_code, len(ok.json()["data"]["spaces"])), (200, 12))
        again = client.post(f"{url}/generate", headers=headers, json={"version": 0})
        self.assertEqual((again.status_code, again.json()["error"]["code"]), (409, "version_conflict"))
        self.assertEqual(client.get(url).json()["data"], ok.json()["data"])


class SqliteScheduleTests(ScheduleChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresScheduleTests(ScheduleChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlScheduleTests(ScheduleChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
