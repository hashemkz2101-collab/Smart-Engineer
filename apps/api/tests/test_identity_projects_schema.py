import os
import tempfile
import unittest
import uuid
from pathlib import Path

from alembic import command
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from smart_engineer_api.db import (
    BackgroundJob,
    Membership,
    Organization,
    Project,
    ProjectMember,
    User,
)
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")


class SchemaChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.sessions = create_session_factory(self.engine)

    def seed(self, session) -> tuple[User, Organization]:
        user = User(email=f"{uuid.uuid4().hex}@example.com", display_name="A", password_hash="x")
        org = Organization(name="Org")
        session.add_all([user, org])
        session.flush()
        return user, org

    def make_project(self, session, user, org, **overrides) -> Project:
        values = {
            "organization_id": org.id,
            "name": "P",
            "project_type": "residential_house",
            "created_by_user_id": user.id,
        }
        values.update(overrides)
        project = Project(**values)
        session.add(project)
        session.flush()
        return project

    def rejected(self, build) -> None:
        with self.assertRaises(IntegrityError):
            with self.sessions.begin() as session:
                build(session)

    def test_defaults_and_relationships_work(self) -> None:
        with self.sessions.begin() as session:
            user, org = self.seed(session)
            session.add(Membership(organization_id=org.id, user_id=user.id, org_role="owner"))
            project = self.make_project(session, user, org)
            session.add(
                ProjectMember(
                    project_id=project.id, user_id=user.id, role="owner",
                    added_by_user_id=user.id,
                )
            )
            project_id = project.id
        with self.sessions() as session:
            stored = session.get(Project, project_id)
            self.assertEqual(stored.status, "active")
            self.assertIsNone(stored.archived_at)
            self.assertEqual(len(session.scalars(select(ProjectMember)).all()), 1)

    def test_email_must_be_lowercase_and_unique(self) -> None:
        self.rejected(lambda s: s.add(User(email="Mixed@Example.com", display_name="A",
                                           password_hash="x")))
        with self.sessions.begin() as session:
            session.add(User(email="a@example.com", display_name="A", password_hash="x"))
        self.rejected(lambda s: s.add(User(email="a@example.com", display_name="B",
                                           password_hash="x")))

    def test_invalid_enumerations_are_rejected(self) -> None:
        def bad_org_role(session):
            user, org = self.seed(session)
            session.add(Membership(organization_id=org.id, user_id=user.id, org_role="boss"))

        def bad_type(session):
            user, org = self.seed(session)
            self.make_project(session, user, org, project_type="spaceship")

        def bad_member_role(session):
            user, org = self.seed(session)
            project = self.make_project(session, user, org)
            session.add(ProjectMember(project_id=project.id, user_id=user.id,
                                      role="system_admin", added_by_user_id=user.id))

        for build in (bad_org_role, bad_type, bad_member_role):
            with self.subTest(build=build.__name__):
                self.rejected(build)

    def test_archive_state_must_be_consistent(self) -> None:
        def archived_without_time(session):
            user, org = self.seed(session)
            self.make_project(session, user, org, status="archived")

        def active_with_time(session):
            user, org = self.seed(session)
            self.make_project(session, user, org, archived_at=text("CURRENT_TIMESTAMP"))

        self.rejected(archived_without_time)
        self.rejected(active_with_time)

    def test_duplicate_memberships_are_rejected(self) -> None:
        with self.sessions.begin() as session:
            user, org = self.seed(session)
            session.add(Membership(organization_id=org.id, user_id=user.id, org_role="owner"))
            ids = (org.id, user.id)
        self.rejected(lambda s: s.add(
            Membership(organization_id=ids[0], user_id=ids[1], org_role="member")))

    def test_foreign_keys_are_enforced_and_deletes_restricted(self) -> None:
        self.rejected(lambda s: s.add(
            Membership(organization_id=uuid.uuid4(), user_id=uuid.uuid4(), org_role="owner")))
        with self.sessions.begin() as session:
            user, org = self.seed(session)
            self.make_project(session, user, org)
            org_id = org.id
        with self.assertRaises(IntegrityError):
            with self.sessions.begin() as session:
                session.delete(session.get(Organization, org_id))


class SqliteSchemaTests(SchemaChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresSchemaTests(SchemaChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlSchemaTests(SchemaChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


class UpgradePreservesDataTests(unittest.TestCase):
    def test_0002_to_0003_keeps_existing_jobs(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            url = f"sqlite:///{Path(directory, 'test.db').as_posix()}"
            config = alembic_config(url)
            command.upgrade(config, "0002")
            engine = create_db_engine(url)
            try:
                sessions = create_session_factory(engine)
                job_id = uuid.uuid4()
                with sessions.begin() as session:
                    session.execute(
                        text("INSERT INTO background_jobs (id, job_type, status, attempts, "
                             "payload, input_version) VALUES (:i, 'noop', 'queued', 0, "
                             "'{}', 1)"),
                        {"i": job_id.hex},
                    )
                command.upgrade(config, "head")
                command.downgrade(config, "0002")
                with sessions() as session:
                    self.assertIsNotNone(session.get(BackgroundJob, job_id))
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
