import os
import tempfile
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from sqlalchemy import text

from smart_engineer_api import feature_flags, jobs
from smart_engineer_api.db import BackgroundJob, FeatureFlag
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")


class ServiceChecks:
    """Flag and job behaviour on a migrated database. Subclasses set ``url``."""

    url: str

    def setUp(self) -> None:
        self.config = alembic_config(self.url)
        command.upgrade(self.config, "head")
        self.engine = create_db_engine(self.url)
        self.sessions = create_session_factory(self.engine)
        self.addCleanup(self.engine.dispose)

    # --- feature flags -------------------------------------------------

    def test_unknown_flag_is_off_and_default_can_be_overridden(self) -> None:
        with self.sessions.begin() as session:
            self.assertFalse(feature_flags.is_enabled(session, "does-not-exist"))
            self.assertTrue(feature_flags.is_enabled(session, "does-not-exist", default=True))

    def test_flag_can_be_turned_on_and_off(self) -> None:
        with self.sessions.begin() as session:
            feature_flags.set_flag(session, "new-viewer", True, description="Preview")
        with self.sessions.begin() as session:
            self.assertTrue(feature_flags.is_enabled(session, "new-viewer"))
            feature_flags.set_flag(session, "new-viewer", False)
        with self.sessions.begin() as session:
            self.assertFalse(feature_flags.is_enabled(session, "new-viewer"))
            self.assertEqual(session.get(FeatureFlag, "new-viewer").description, "Preview")

    def test_invalid_flag_keys_are_rejected(self) -> None:
        with self.sessions.begin() as session:
            for key in ("", "Upper", "1starts-with-digit", "has space", "x" * 101):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    feature_flags.is_enabled(session, key)

    # --- jobs ----------------------------------------------------------

    def test_successful_job_records_version_result_and_times(self) -> None:
        start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        with self.sessions.begin() as session:
            job = jobs.create_job(session, "geometry.demo", {"n": 3}, input_version=2)
            job_id = job.id
            self.assertEqual(job.status, "queued")
            jobs.start_job(session, job, now=start)
            jobs.succeed_job(session, job, {"area": 9}, now=start + timedelta(seconds=5))

        with self.sessions() as session:
            stored = session.get(BackgroundJob, job_id)
            self.assertEqual(stored.status, "succeeded")
            self.assertEqual(stored.input_version, 2)
            self.assertEqual(stored.payload, {"n": 3})
            self.assertEqual(stored.result, {"area": 9})
            self.assertEqual(stored.attempts, 1)
            self.assertIsNone(stored.last_error)
            self.assertEqual((stored.finished_at - stored.started_at).total_seconds(), 5)

    def test_failed_job_records_error_and_can_be_retried(self) -> None:
        with self.sessions.begin() as session:
            job = jobs.create_job(session, "geometry.demo")
            job_id = job.id
            jobs.start_job(session, job)
            jobs.fail_job(session, job, "x" * 5000)
        with self.sessions.begin() as session:
            job = session.get(BackgroundJob, job_id)
            self.assertEqual(job.status, "failed")
            self.assertEqual(len(job.last_error), jobs.MAX_ERROR_LENGTH)
            self.assertIsNotNone(job.finished_at)
            jobs.retry_job(session, job)
            self.assertEqual(job.status, "queued")
            self.assertIsNone(job.finished_at)
            jobs.start_job(session, job)
            self.assertEqual(job.attempts, 2)
            self.assertIsNone(job.last_error)

    def test_invalid_transitions_are_rejected(self) -> None:
        with self.sessions.begin() as session:
            job = jobs.create_job(session, "geometry.demo")
            with self.assertRaises(InvalidTransition):
                jobs.succeed_job(session, job)  # queued -> succeeded
            jobs.start_job(session, job)
            jobs.succeed_job(session, job)
            for action in (jobs.start_job, jobs.cancel_job, jobs.retry_job):
                with self.subTest(action=action.__name__), self.assertRaises(InvalidTransition):
                    action(session, job)  # succeeded is terminal

    def test_cancelled_job_is_terminal(self) -> None:
        with self.sessions.begin() as session:
            job = jobs.create_job(session, "geometry.demo")
            jobs.cancel_job(session, job)
            self.assertEqual(job.status, "cancelled")
            with self.assertRaises(InvalidTransition):
                jobs.start_job(session, job)

    def test_create_job_validates_input(self) -> None:
        with self.sessions.begin() as session:
            with self.assertRaises(ValueError):
                jobs.create_job(session, "")
            with self.assertRaises(ValueError):
                jobs.create_job(session, "demo", input_version=0)

    # --- migration forward/back with data ------------------------------

    def test_existing_rows_keep_data_across_0001_to_0002_and_back(self) -> None:
        command.downgrade(self.config, "base")
        command.upgrade(self.config, "0001")
        job_id = uuid.uuid4()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO background_jobs (id, job_type, status, payload, attempts) "
                    "VALUES (:id, 'legacy', 'queued', '{}', 0)"
                ),
                {"id": job_id.hex if self.engine.dialect.name == "sqlite" else job_id},
            )

        command.upgrade(self.config, "0002")
        with self.sessions() as session:
            migrated = session.get(BackgroundJob, job_id)
            self.assertEqual(migrated.input_version, 1)
            self.assertIsNone(migrated.result)
            self.assertEqual(migrated.job_type, "legacy")

        command.downgrade(self.config, "0001")
        with self.engine.connect() as connection:
            columns = {
                row[0]
                for row in connection.execute(
                    text("SELECT name FROM pragma_table_info('background_jobs')")
                )
            } if self.engine.dialect.name == "sqlite" else {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'background_jobs'"
                    )
                )
            }
        self.assertNotIn("input_version", columns)
        self.assertNotIn("result", columns)
        self.assertIn("job_type", columns)


InvalidTransition = jobs.InvalidJobTransition


class SqliteServiceTests(ServiceChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'svc.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresServiceTests(ServiceChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(command.downgrade, alembic_config(self.url), "base")
        super().setUp()


if __name__ == "__main__":
    unittest.main()
