import os
import tempfile
import unittest
import re
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, select
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex, CreateTable

from smart_engineer_api.config import ConfigurationError, Settings
from smart_engineer_api.db import BackgroundJob, Base, FeatureFlag
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from tests.helpers import API_ROOT, alembic_config

EXPECTED_TABLES = {
    "feature_flags",
    "background_jobs",
    "users",
    "organizations",
    "memberships",
    "projects",
    "project_members",
    "auth_sessions",
    "auth_tokens",
    "login_failures",
    "invitations",
    "activity_events",
    "intake_steps",
    "site_sections",
    "zoning_records",
    "requirement_sections",
    "environment_records",
    "project_files",
    "admin_audit_events",
}
POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")


class MigrationChecks:
    """Behaviour every supported database must satisfy. Subclasses set ``url``."""

    url: str

    def tables(self) -> set[str]:
        engine = create_db_engine(self.url)
        try:
            return set(inspect(engine).get_table_names()) - {"alembic_version"}
        finally:
            engine.dispose()

    def test_upgrade_creates_expected_tables(self) -> None:
        command.upgrade(alembic_config(self.url), "head")

        self.assertEqual(self.tables(), EXPECTED_TABLES)

    def test_downgrade_removes_tables_and_upgrade_is_repeatable(self) -> None:
        config = alembic_config(self.url)
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        self.assertEqual(self.tables(), set())

        command.upgrade(config, "head")
        self.assertEqual(self.tables(), EXPECTED_TABLES)

    def test_migrated_schema_matches_models(self) -> None:
        command.upgrade(alembic_config(self.url), "head")

        engine = create_db_engine(self.url)
        try:
            with engine.connect() as connection:
                context = MigrationContext.configure(connection, opts={"compare_type": True})
                differences = compare_metadata(context, Base.metadata)
        finally:
            engine.dispose()

        self.assertEqual(differences, [])

    def test_models_work_against_migrated_schema(self) -> None:
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        try:
            sessions = create_session_factory(engine)
            job_id = uuid.uuid4()
            with sessions.begin() as session:
                session.add(FeatureFlag(key="demo"))
                session.add(
                    BackgroundJob(id=job_id, job_type="noop", payload={"a": 1})
                )

            with sessions() as session:
                flag = session.get(FeatureFlag, "demo")
                stored = session.get(BackgroundJob, job_id)
                self.assertFalse(flag.enabled)
                self.assertEqual(stored.status, "queued")
                self.assertEqual(stored.attempts, 0)
                self.assertEqual(stored.payload, {"a": 1})
                self.assertIsNotNone(stored.created_at)
                self.assertEqual(len(session.scalars(select(FeatureFlag)).all()), 1)
        finally:
            engine.dispose()

    def test_invalid_job_status_is_rejected_by_the_database(self) -> None:
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        try:
            sessions = create_session_factory(engine)
            with self.assertRaises(IntegrityError):
                with sessions.begin() as session:
                    session.add(BackgroundJob(job_type="noop", status="exploded"))
        finally:
            engine.dispose()

    def test_duplicate_feature_flag_key_is_rejected(self) -> None:
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        try:
            sessions = create_session_factory(engine)
            with sessions.begin() as session:
                session.add(FeatureFlag(key="dup"))
            with self.assertRaises(IntegrityError):
                with sessions.begin() as session:
                    session.add(FeatureFlag(key="dup"))
        finally:
            engine.dispose()


    def test_timestamps_are_stored_in_utc_and_read_back_aware(self) -> None:
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        try:
            sessions = create_session_factory(engine)
            exact = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)
            local = datetime(2026, 1, 2, 6, 34, 5, 123456, tzinfo=timezone(timedelta(hours=3.5)))
            with sessions.begin() as session:
                first = BackgroundJob(job_type="noop", created_at=exact)
                second = BackgroundJob(job_type="noop", created_at=local)
                third = BackgroundJob(job_type="noop")
                session.add_all([first, second, third])
                session.flush()
                ids = (first.id, second.id, third.id)
            with sessions() as session:
                one, two, three = (session.get(BackgroundJob, key) for key in ids)
                # Microseconds survive, and a +03:30 value is the same instant in UTC.
                self.assertEqual(one.created_at, exact)
                self.assertEqual(two.created_at, exact)
                self.assertEqual(one.created_at.utcoffset(), timedelta(0))
                # The database's own default clock is UTC too, whatever the server zone is.
                self.assertLess(abs(datetime.now(UTC) - three.created_at), timedelta(minutes=5))
        finally:
            engine.dispose()

    def test_text_keys_are_case_sensitive_like_postgresql(self) -> None:
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        try:
            sessions = create_session_factory(engine)
            with sessions.begin() as session:
                session.add_all([FeatureFlag(key="Case"), FeatureFlag(key="case")])
            with sessions() as session:
                self.assertEqual(len(session.scalars(select(FeatureFlag)).all()), 2)
                self.assertIsNone(session.get(FeatureFlag, "CASE"))
        finally:
            engine.dispose()

    def test_persian_text_round_trips(self) -> None:
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        try:
            sessions = create_session_factory(engine)
            text_value = "پروژه ساختمانی \u200cمهندس 😀"
            with sessions.begin() as session:
                session.add(BackgroundJob(job_type="noop", payload={"name": text_value}))
            with sessions() as session:
                job = session.scalars(select(BackgroundJob)).one()
                self.assertEqual(job.payload, {"name": text_value})
        finally:
            engine.dispose()


class SqliteMigrationTests(MigrationChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.directory.cleanup)
        self.url = f"sqlite:///{Path(self.directory.name, 'test.db').as_posix()}"


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresMigrationTests(MigrationChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        self.addCleanup(self.reset)
        self.reset()

    def reset(self) -> None:
        command.downgrade(alembic_config(self.url), "base")


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlMigrationTests(MigrationChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        self.addCleanup(self.reset)
        self.reset()

    def reset(self) -> None:
        command.downgrade(alembic_config(self.url), "base")


class MysqlCompatibilityTests(unittest.TestCase):
    """Rules MySQL imposes that need no running server to check."""

    def test_constraint_and_index_names_fit_the_64_character_limit(self) -> None:
        dialect = mysql.dialect()
        names: list[str] = []
        for table in Base.metadata.sorted_tables:
            names += re.findall(r"CONSTRAINT\s+`?(\w+)`?", str(CreateTable(table).compile(dialect=dialect)))
            for index in table.indexes:
                names += re.findall(r"INDEX\s+`?(\w+)`?", str(CreateIndex(index).compile(dialect=dialect)))
        self.assertTrue(names)
        self.assertEqual([name for name in names if len(name) > 64], [])

    def test_timestamps_get_microsecond_precision_on_mysql_only(self) -> None:
        table = Base.metadata.tables["background_jobs"]
        mysql_sql = str(CreateTable(table).compile(dialect=mysql.dialect()))
        self.assertIn("created_at DATETIME(6)", mysql_sql)
        self.assertIn("CURRENT_TIMESTAMP(6)", mysql_sql)


class DatabaseSettingsTests(unittest.TestCase):
    def test_database_url_defaults_to_none(self) -> None:
        self.assertIsNone(Settings.from_env({}).database_url)

    def test_postgresql_mysql_and_sqlite_urls_are_accepted(self) -> None:
        urls = (
            "postgresql+psycopg://u:p@localhost/db",
            "mysql+pymysql://u:p@localhost:3306/db",
            "sqlite:///x.db",
        )
        for url in urls:
            with self.subTest(url=url):
                settings = Settings.from_env({"SMART_ENGINEER_DATABASE_URL": url})
                self.assertEqual(settings.database_url, url)

    def test_unknown_scheme_is_rejected_without_echoing_the_value(self) -> None:
        secret = "mysql://user:hunter2@host/db"  # secret-scan:allow (test fixture)

        with self.assertRaises(ConfigurationError) as context:
            Settings.from_env({"SMART_ENGINEER_DATABASE_URL": secret})

        self.assertNotIn("hunter2", str(context.exception))

    def test_sqlite_is_rejected_in_production(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env(
                {
                    "SMART_ENGINEER_ENV": "production",
                    "SMART_ENGINEER_DATABASE_URL": "sqlite:///x.db",
                }
            )

    def test_production_accepts_postgresql_and_mysql(self) -> None:
        for url in ("postgresql+psycopg://u:p@h/db", "mysql+pymysql://u:p@h/db"):
            with self.subTest(url=url):
                settings = Settings.from_env(
                    {"SMART_ENGINEER_ENV": "production", "SMART_ENGINEER_DATABASE_URL": url}
                )
                self.assertEqual(settings.database_url, url)

    def test_mysql_repr_and_errors_hide_the_password(self) -> None:
        self.assertNotIn("hunter2", repr(Settings(database_url="mysql+pymysql://u:hunter2@h/db")))

    def test_repr_hides_the_database_url(self) -> None:
        settings = Settings(database_url="postgresql+psycopg://u:hunter2@h/db")

        self.assertNotIn("hunter2", repr(settings))

    def test_importing_the_app_does_not_require_a_database(self) -> None:
        from smart_engineer_api.main import create_app

        create_app(Settings(environment="test"))

    def test_migrations_fail_clearly_without_a_url(self) -> None:
        config = Config(str(API_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(API_ROOT / "migrations"))
        saved = os.environ.pop("SMART_ENGINEER_DATABASE_URL", None)
        try:
            with self.assertRaises(RuntimeError) as context:
                command.upgrade(config, "head")
        finally:
            if saved is not None:
                os.environ["SMART_ENGINEER_DATABASE_URL"] = saved

        self.assertIn("SMART_ENGINEER_DATABASE_URL", str(context.exception))


if __name__ == "__main__":
    unittest.main()
