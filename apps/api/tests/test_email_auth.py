import os
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest import mock

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api.config import ConfigurationError, Settings
from smart_engineer_api.db import User
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.mail import SmtpMailer
from smart_engineer_api.main import create_app
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1), require_email_verification=True)
PASSWORD = "correct horse battery"
BASE = "/api/v1/auth"
MAIL_ENV = {
    "SMART_ENGINEER_SMTP_HOST": "smtp.example.com",
    "SMART_ENGINEER_MAIL_FROM": "no-reply@example.com",
    "SMART_ENGINEER_PUBLIC_URL": "https://app.example.com/",
}


class EmailAuthChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.session = create_session_factory(self.engine)()
        self.addCleanup(self.session.close)
        self.mailer = auth.OutboxMailer()

    def signup(self, email: str = "ali@example.com"):
        return auth.register(
            self.session, POLICY, email=email, display_name="Ali", password=PASSWORD
        )

    def test_verification_confirms_once_and_unlocks_login(self) -> None:
        self.signup()
        auth.request_email_verification(self.session, POLICY, self.mailer, email="ALI@example.com")
        self.assertEqual(len(self.mailer.email_verifications), 1)
        email, token = self.mailer.email_verifications[0]
        self.assertEqual(email, "ali@example.com")
        with self.assertRaises(auth.AuthError) as before:
            auth.login(self.session, POLICY, email=email, password=PASSWORD)
        self.assertEqual(before.exception.code, "email_not_verified")

        auth.confirm_email(self.session, token=token)
        auth.login(self.session, POLICY, email=email, password=PASSWORD)
        user = self.session.scalar(select(User).where(User.email == email))
        self.assertIsNotNone(user.email_verified_at)
        with self.assertRaises(auth.AuthError) as reused:
            auth.confirm_email(self.session, token=token)
        self.assertEqual(reused.exception.code, "invalid_token")

    def test_unknown_verified_and_inactive_accounts_send_nothing(self) -> None:
        user = self.signup()
        auth.request_email_verification(self.session, POLICY, self.mailer, email="no@example.com")
        user.is_active = False
        self.session.commit()
        auth.request_email_verification(self.session, POLICY, self.mailer, email=user.email)
        user.is_active = True
        user.email_verified_at = auth.utcnow()
        self.session.commit()
        auth.request_email_verification(self.session, POLICY, self.mailer, email=user.email)
        self.assertEqual(self.mailer.email_verifications, [])

    def test_resend_has_a_cooldown_and_replaces_the_old_link(self) -> None:
        self.signup()
        start = auth.utcnow()
        send = lambda moment: auth.request_email_verification(  # noqa: E731
            self.session, POLICY, self.mailer, email="ali@example.com", now=moment
        )
        send(start)
        send(start + timedelta(seconds=10))
        self.assertEqual(len(self.mailer.email_verifications), 1)
        send(start + timedelta(seconds=90))
        self.assertEqual(len(self.mailer.email_verifications), 2)
        old, new = (t for _, t in self.mailer.email_verifications)
        with self.assertRaises(auth.AuthError):
            auth.confirm_email(self.session, token=old, now=start + timedelta(seconds=91))
        auth.confirm_email(self.session, token=new, now=start + timedelta(seconds=91))

    def test_expired_wrong_purpose_and_unknown_tokens_are_invalid(self) -> None:
        self.signup()
        start = auth.utcnow()
        auth.request_email_verification(
            self.session, POLICY, self.mailer, email="ali@example.com", now=start
        )
        token = self.mailer.email_verifications[0][1]
        with self.assertRaises(auth.AuthError):
            auth.confirm_email(self.session, token=token, now=start + timedelta(hours=25))
        with self.assertRaises(auth.AuthError):
            auth.confirm_email(self.session, token="unknown")
        auth.request_password_reset(self.session, POLICY, self.mailer, email="ali@example.com")
        reset_token = self.mailer.password_resets[0][1]
        with self.assertRaises(auth.AuthError):
            auth.confirm_email(self.session, token=reset_token)

    def test_http_flow(self) -> None:
        app = create_app(
            Settings(environment="test"),
            session_factory=create_session_factory(self.engine),
            auth_policy=POLICY,
            mailer=self.mailer,
        )
        client = TestClient(app)
        self.addCleanup(client.close)
        signup = client.post(
            f"{BASE}/register",
            json={"email": "ali@example.com", "display_name": "Ali", "password": PASSWORD},
        )
        self.assertEqual((signup.status_code, signup.json()["verification_required"]), (201, True))
        self.assertEqual(len(self.mailer.email_verifications), 1)
        credentials = {"email": "ali@example.com", "password": PASSWORD}
        refused = client.post(f"{BASE}/login", json=credentials)
        self.assertEqual((refused.status_code, refused.json()["error"]["code"]), (403, "email_not_verified"))

        unknown = client.post(f"{BASE}/email-verification/request", json={"email": "no@example.com"})
        known = client.post(f"{BASE}/email-verification/request", json={"email": "ali@example.com"})
        self.assertEqual((unknown.status_code, known.status_code), (202, 202))
        self.assertEqual(unknown.json(), known.json())

        token = self.mailer.email_verifications[0][1]
        bad = client.post(f"{BASE}/email-verification/confirm", json={"token": "nope"})
        self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (400, "invalid_token"))
        ok = client.post(f"{BASE}/email-verification/confirm", json={"token": token})
        self.assertEqual(ok.status_code, 204)
        self.assertEqual(client.post(f"{BASE}/login", json=credentials).status_code, 200)


class SqliteEmailAuthTests(EmailAuthChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresEmailAuthTests(EmailAuthChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlEmailAuthTests(EmailAuthChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


class FakeSmtp:
    instances: list = []

    def __init__(self, host, port, timeout=None, context=None) -> None:
        self.host, self.port, self.calls, self.sent = host, port, [], []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def starttls(self, context=None) -> None:
        self.calls.append("starttls")

    def login(self, user, password) -> None:
        self.calls.append(("login", user, password))

    def send_message(self, message) -> None:
        self.sent.append(message)


class SmtpMailerTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeSmtp.instances = []

    def settings(self, **extra) -> Settings:
        env = {**MAIL_ENV, "SMART_ENGINEER_SMTP_USERNAME": "user",
               "SMART_ENGINEER_SMTP_PASSWORD": "p@ss", **extra}
        return Settings.from_env(env)

    def test_messages_carry_a_persian_body_and_a_link_on_the_public_url(self) -> None:
        mailer = SmtpMailer(self.settings(), background=False)
        with mock.patch("smart_engineer_api.mail.smtplib.SMTP", FakeSmtp):
            mailer.send_email_verification("ali@example.com", "a/b c")
            mailer.send_password_reset("ali@example.com", "tok")
        verification, reset = (i.sent[0] for i in FakeSmtp.instances)
        self.assertEqual(verification["To"], "ali@example.com")
        self.assertEqual(verification["From"], "no-reply@example.com")
        body = verification.get_content()
        self.assertIn("https://app.example.com/verify-email?token=a%2Fb%20c", body)
        self.assertIn("تأیید", verification["Subject"])
        self.assertIn("https://app.example.com/reset-password?token=tok", reset.get_content())
        self.assertEqual(
            FakeSmtp.instances[0].calls, ["starttls", ("login", "user", "p@ss")]
        )

    def test_ssl_mode_uses_implicit_tls_and_none_skips_it(self) -> None:
        with mock.patch("smart_engineer_api.mail.smtplib.SMTP_SSL", FakeSmtp):
            SmtpMailer(self.settings(SMART_ENGINEER_SMTP_SECURITY="ssl"), background=False
                       ).send_password_reset("a@example.com", "t")
        self.assertEqual(FakeSmtp.instances[0].calls, [("login", "user", "p@ss")])
        FakeSmtp.instances = []
        with mock.patch("smart_engineer_api.mail.smtplib.SMTP", FakeSmtp):
            SmtpMailer(self.settings(SMART_ENGINEER_SMTP_SECURITY="none"), background=False
                       ).send_password_reset("a@example.com", "t")
        self.assertNotIn("starttls", FakeSmtp.instances[0].calls)

    def test_a_delivery_failure_is_logged_without_secrets_and_never_raised(self) -> None:
        class Broken(FakeSmtp):
            def send_message(self, message) -> None:
                raise OSError("boom ali@example.com tok-secret")

        mailer = SmtpMailer(self.settings(), background=False)
        with mock.patch("smart_engineer_api.mail.smtplib.SMTP", Broken), self.assertLogs(
            "smart_engineer_api.mail", level="ERROR"
        ) as logs:
            mailer.send_password_reset("ali@example.com", "tok-secret")
        text = " ".join(logs.output) + str([r.__dict__ for r in logs.records])
        self.assertNotIn("tok-secret", text)
        self.assertNotIn("ali@example.com", text)
        self.assertEqual(logs.records[0].error_type, "OSError")

    def test_a_mailer_needs_complete_configuration(self) -> None:
        with self.assertRaises(ValueError):
            SmtpMailer(Settings())


class MailConfigTests(unittest.TestCase):
    def test_mail_settings_are_read_and_the_password_is_hidden(self) -> None:
        settings = Settings.from_env(
            {**MAIL_ENV, "SMART_ENGINEER_SMTP_PORT": "465", "SMART_ENGINEER_SMTP_SECURITY": "SSL",
             "SMART_ENGINEER_SMTP_PASSWORD": "hunter-two"}
        )
        self.assertTrue(settings.mail_configured)
        self.assertEqual(
            (settings.smtp_port, settings.smtp_security, settings.public_url),
            (465, "ssl", "https://app.example.com"),
        )
        self.assertNotIn("hunter-two", repr(settings))

    def test_invalid_or_incomplete_mail_settings_are_rejected(self) -> None:
        cases = (
            {"SMART_ENGINEER_SMTP_HOST": "smtp.example.com"},
            {**MAIL_ENV, "SMART_ENGINEER_SMTP_PORT": "abc"},
            {**MAIL_ENV, "SMART_ENGINEER_SMTP_PORT": "70000"},
            {**MAIL_ENV, "SMART_ENGINEER_SMTP_SECURITY": "magic"},
            {**MAIL_ENV, "SMART_ENGINEER_PUBLIC_URL": "app.example.com"},
        )
        for env in cases:
            with self.assertRaises(ConfigurationError, msg=str(env)):
                Settings.from_env(env)

    def test_production_without_a_mail_server_refuses_to_start(self) -> None:
        with self.assertRaises(ConfigurationError):
            create_app(Settings(environment="production"))
        configured = replace(
            Settings(environment="production"),
            smtp_host="smtp.example.com",
            mail_from="no-reply@example.com",
            public_url="https://app.example.com",
        )
        app = create_app(configured)
        self.assertIsInstance(app.state.mailer, SmtpMailer)
        self.assertIsInstance(create_app(Settings(environment="test")).state.mailer, auth.OutboxMailer)


if __name__ == "__main__":
    unittest.main()
