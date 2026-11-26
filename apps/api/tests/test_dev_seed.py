import tempfile
import unittest
from pathlib import Path

from alembic import command
from sqlalchemy import func, select

from smart_engineer_api import auth_service, dev_seed, manage
from smart_engineer_api.config import ConfigurationError, Settings
from smart_engineer_api.db import Project, ProjectMember, User
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

FAST = auth_service.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))


class DemoSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name) / 'demo.db'}"
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.sessions = create_session_factory(self.engine)

    def test_seed_creates_loginable_demo_accounts_and_projects_once(self) -> None:
        with self.sessions() as session:
            emails = dev_seed.seed(session, FAST)
            self.assertEqual(len(emails), 5)
            self.assertTrue(all(email.endswith(".test") for email in emails))
            logged_in = auth_service.login(
                session, FAST, email=dev_seed.email_for("owner"), password=dev_seed.DEMO_PASSWORD
            )
            self.assertIsNotNone(logged_in)
            admin = session.scalar(select(User).where(User.email == dev_seed.email_for("admin")))
            self.assertTrue(admin.is_system_admin)
            self.assertEqual(session.scalar(select(func.count()).select_from(Project)), 2)
            # owner + architect + structural engineer + quantity surveyor per project
            self.assertEqual(session.scalar(select(func.count()).select_from(ProjectMember)), 8)

            dev_seed.seed(session, FAST)  # running again changes nothing
            self.assertEqual(session.scalar(select(func.count()).select_from(User)), 5)
            self.assertEqual(session.scalar(select(func.count()).select_from(Project)), 2)

    def test_seed_refuses_production_and_databases_on_other_machines(self) -> None:
        with self.assertRaises(ConfigurationError):
            dev_seed.ensure_local_demo_database(
                Settings(environment="production", database_url="postgresql+psycopg://u:p@h/db")
            )
        with self.assertRaises(ConfigurationError):
            dev_seed.ensure_local_demo_database(
                Settings(database_url="postgresql+psycopg://u:p@db.example.com/db")
            )
        with self.assertRaises(ConfigurationError):
            dev_seed.ensure_local_demo_database(Settings())
        for url in (
            "postgresql+psycopg://u:p@127.0.0.1:5432/db",
            "mysql+pymysql://u:p@localhost/db",
            "sqlite:///x.db",
        ):
            dev_seed.ensure_local_demo_database(Settings(database_url=url))

    def test_command_refuses_a_remote_database_without_touching_it(self) -> None:
        settings = Settings(database_url="postgresql+psycopg://u:p@db.example.com/db")
        self.assertEqual(manage._seed_demo(settings), 2)


if __name__ == "__main__":
    unittest.main()
