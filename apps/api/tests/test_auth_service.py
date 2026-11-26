import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from sqlalchemy import func, select

from smart_engineer_api import auth_service as auth
from smart_engineer_api.db import (
    AuthSession,
    AuthToken,
    LoginFailure,
    Membership,
    Organization,
    User,
)
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
MYSQL_URL = os.environ.get("SMART_ENGINEER_TEST_MYSQL_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
T0 = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
PASSWORD = "correct horse battery"


class AuthChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.session = create_session_factory(self.engine)()
        self.addCleanup(self.session.close)
        self.mailer = auth.OutboxMailer()

    def register(self, email: str = "ali@example.com") -> User:
        return auth.register(
            self.session, POLICY, email=email, display_name="Ali Rezaei", password=PASSWORD
        )

    def login(self, email="ali@example.com", password=PASSWORD, now=T0):
        return auth.login(self.session, POLICY, email=email, password=password, now=now)

    def code(self, func, *args, **kwargs) -> str:
        with self.assertRaises(auth.AuthError) as context:
            func(*args, **kwargs)
        return context.exception.code

    # registration -------------------------------------------------------
    def test_register_creates_user_personal_organization_and_owner_membership(self) -> None:
        user = self.register("Ali@Example.com ")

        self.assertEqual(user.email, "ali@example.com")
        self.assertNotIn(PASSWORD, user.password_hash)
        membership = self.session.scalar(select(Membership))
        self.assertEqual((membership.user_id, membership.org_role), (user.id, "owner"))
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Organization)), 1)

    def test_register_rejects_duplicates_bad_email_and_weak_passwords(self) -> None:
        self.register()
        self.assertEqual(self.code(self.register, "ALI@example.com"), "email_taken")
        self.assertEqual(self.code(self.register, "not-an-email"), "invalid_email")
        weak = self.code(
            auth.register, self.session, POLICY,
            email="b@example.com", display_name="B", password="short",
        )
        self.assertEqual(weak, "weak_password")
        blank = self.code(
            auth.register, self.session, POLICY,
            email="c@example.com", display_name="  ", password=PASSWORD,
        )
        self.assertEqual(blank, "invalid_display_name")

    # login and sessions ------------------------------------------------
    def test_login_issues_a_session_stored_only_as_a_hash(self) -> None:
        self.register()
        issued = self.login()

        stored = self.session.scalar(select(AuthSession))
        self.assertNotEqual(stored.token_hash, issued.token)
        self.assertNotIn(issued.token, stored.token_hash)
        found = auth.authenticate(self.session, POLICY, issued.token, now=T0)
        self.assertEqual(found[1].id, issued.user.id)
        self.assertIsNone(auth.authenticate(self.session, POLICY, "forged", now=T0))
        self.assertTrue(auth.csrf_matches(stored, issued.csrf_token))
        self.assertFalse(auth.csrf_matches(stored, "wrong"))
        self.assertFalse(auth.csrf_matches(stored, None))

    def test_wrong_password_and_unknown_email_look_identical(self) -> None:
        self.register()
        self.assertEqual(self.code(self.login, password="wrong password!"), "invalid_credentials")
        self.assertEqual(self.code(self.login, email="nobody@example.com"), "invalid_credentials")

    def test_inactive_user_cannot_log_in(self) -> None:
        user = self.register()
        user.is_active = False
        self.session.commit()
        self.assertEqual(self.code(self.login), "invalid_credentials")

    def test_sessions_expire_when_idle_or_past_the_absolute_limit(self) -> None:
        self.register()
        issued = self.login()
        later = T0 + timedelta(hours=23)
        self.assertIsNotNone(auth.authenticate(self.session, POLICY, issued.token, now=later))
        # Activity moved last_seen forward, so 23h later is still inside the idle window.
        self.assertIsNotNone(
            auth.authenticate(self.session, POLICY, issued.token, now=later + timedelta(hours=23))
        )
        idle = later + timedelta(hours=23, days=2)
        self.assertIsNone(auth.authenticate(self.session, POLICY, issued.token, now=idle))

        again = self.login(now=T0)
        keep_alive = T0
        while keep_alive < T0 + timedelta(days=14):
            keep_alive += timedelta(hours=20)
            result = auth.authenticate(self.session, POLICY, again.token, now=keep_alive)
            if keep_alive >= T0 + timedelta(days=14):
                self.assertIsNone(result)
            else:
                self.assertIsNotNone(result)

    def test_logout_revokes_the_session(self) -> None:
        self.register()
        issued = self.login()
        auth.logout(self.session, issued.token, now=T0)
        self.assertIsNone(auth.authenticate(self.session, POLICY, issued.token, now=T0))

    # lockout -------------------------------------------------------------
    def test_account_locks_after_repeated_failures_then_recovers(self) -> None:
        self.register()
        for _ in range(POLICY.max_failures):
            self.assertEqual(self.code(self.login, password="wrong password!"), "invalid_credentials")
        # Even the right password is refused while locked.
        self.assertEqual(self.code(self.login), "account_locked")
        soon = T0 + timedelta(minutes=5)
        self.assertEqual(self.code(self.login, now=soon), "account_locked")
        later = T0 + POLICY.failure_window + timedelta(seconds=1)
        self.assertIsNotNone(self.login(now=later))

    def test_successful_login_clears_failure_counter(self) -> None:
        self.register()
        for _ in range(POLICY.max_failures - 1):
            self.code(self.login, password="wrong password!")
        self.login()
        self.assertEqual(self.session.scalar(select(func.count()).select_from(LoginFailure)), 0)

    def test_email_verification_can_be_required(self) -> None:
        strict = auth.AuthPolicy(
            scrypt=POLICY.scrypt, require_email_verification=True
        )
        user = self.register()
        self.assertEqual(
            self.code(auth.login, self.session, strict, email=user.email, password=PASSWORD, now=T0),
            "email_not_verified",
        )
        user.email_verified_at = T0
        self.session.commit()
        auth.login(self.session, strict, email=user.email, password=PASSWORD, now=T0)

    # password change -----------------------------------------------------
    def test_changing_password_revokes_other_sessions_only(self) -> None:
        user = self.register()
        current = self.login()
        other = self.login()
        keep = auth.authenticate(self.session, POLICY, current.token, now=T0)[0]

        auth.change_password(
            self.session, POLICY, user,
            current_password=PASSWORD, new_password="a brand new passphrase",
            keep_session_id=keep.id, now=T0,
        )

        self.assertIsNotNone(auth.authenticate(self.session, POLICY, current.token, now=T0))
        self.assertIsNone(auth.authenticate(self.session, POLICY, other.token, now=T0))
        self.assertEqual(self.code(self.login), "invalid_credentials")
        self.login(password="a brand new passphrase")

    def test_change_password_requires_current_password_and_a_strong_new_one(self) -> None:
        user = self.register()
        args = (self.session, POLICY, user)
        self.assertEqual(
            self.code(auth.change_password, *args, current_password="nope nope nope",
                      new_password="a brand new passphrase"),
            "invalid_credentials",
        )
        self.assertEqual(
            self.code(auth.change_password, *args, current_password=PASSWORD, new_password="short"),
            "weak_password",
        )

    # password recovery ---------------------------------------------------
    def test_reset_request_never_reveals_whether_the_email_exists(self) -> None:
        self.register()
        auth.request_password_reset(self.session, POLICY, self.mailer, email="nobody@example.com", now=T0)
        self.assertEqual(self.mailer.password_resets, [])
        auth.request_password_reset(self.session, POLICY, self.mailer, email="ALI@example.com", now=T0)
        self.assertEqual(len(self.mailer.password_resets), 1)

    def reset_token(self, now=T0) -> str:
        auth.request_password_reset(self.session, POLICY, self.mailer, email="ali@example.com", now=now)
        return self.mailer.password_resets[-1][1]

    def test_reset_sets_new_password_revokes_sessions_and_is_single_use(self) -> None:
        self.register()
        issued = self.login()
        token = self.reset_token()
        stored = self.session.scalar(select(AuthToken))
        self.assertNotEqual(stored.token_hash, token)

        auth.reset_password(self.session, POLICY, token=token, new_password="reset to this phrase", now=T0)

        self.assertIsNone(auth.authenticate(self.session, POLICY, issued.token, now=T0))
        self.login(password="reset to this phrase")
        again = self.code(auth.reset_password, self.session, POLICY,
                          token=token, new_password="another new phrase!", now=T0)
        self.assertEqual(again, "invalid_token")

    def test_reset_token_expires(self) -> None:
        self.register()
        token = self.reset_token()
        late = T0 + POLICY.reset_ttl + timedelta(seconds=1)
        code = self.code(auth.reset_password, self.session, POLICY,
                         token=token, new_password="reset to this phrase", now=late)
        self.assertEqual(code, "invalid_token")
        self.assertEqual(
            self.code(auth.reset_password, self.session, POLICY,
                      token="garbage", new_password="reset to this phrase", now=T0),
            "invalid_token",
        )

    def test_new_request_invalidates_the_previous_token(self) -> None:
        self.register()
        first = self.reset_token()
        second = self.reset_token()
        self.assertEqual(
            self.code(auth.reset_password, self.session, POLICY,
                      token=first, new_password="reset to this phrase", now=T0),
            "invalid_token",
        )
        auth.reset_password(self.session, POLICY, token=second, new_password="reset to this phrase", now=T0)

    def test_weak_reset_password_does_not_consume_the_token(self) -> None:
        self.register()
        token = self.reset_token()
        self.assertEqual(
            self.code(auth.reset_password, self.session, POLICY,
                      token=token, new_password="short", now=T0),
            "weak_password",
        )
        auth.reset_password(self.session, POLICY, token=token, new_password="reset to this phrase", now=T0)


class SqliteAuthTests(AuthChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresAuthTests(AuthChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


@unittest.skipUnless(MYSQL_URL, "SMART_ENGINEER_TEST_MYSQL_DATABASE_URL is not set")
class MysqlAuthTests(AuthChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = MYSQL_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


class PasswordSecurityTests(unittest.TestCase):
    def test_hash_roundtrip_and_malformed_hashes(self) -> None:
        from smart_engineer_api.security import hash_password, verify_password

        stored = hash_password("some long passphrase", POLICY.scrypt)
        self.assertTrue(verify_password("some long passphrase", stored))
        self.assertFalse(verify_password("other", stored))
        for bad in ("", "garbage", "bcrypt$1$2$3$4$5", "scrypt$x$y$z$a$b"):
            self.assertFalse(verify_password("anything", bad))

    def test_policy_rejects_short_long_common_and_email_derived_passwords(self) -> None:
        from smart_engineer_api.security import password_problems

        self.assertIn("too_short", password_problems("short"))
        self.assertIn("too_long", password_problems("x" * 129))
        self.assertIn("too_common", password_problems("password1"))
        self.assertIn("contains_email", password_problems("bobsmith2026!", "bobsmith@x.com"))
        self.assertEqual(password_problems("a perfectly fine phrase", "bob@x.com"), [])


if __name__ == "__main__":
    unittest.main()
