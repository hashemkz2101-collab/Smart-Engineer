import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient

from smart_engineer_api import auth_service as auth
from smart_engineer_api.config import Settings
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.main import create_app
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
BASE = "/api/v1/auth"
CREDENTIALS = {"email": "ali@example.com", "password": PASSWORD}


class HttpChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        self.mailer = auth.OutboxMailer()
        self.make_client()
        self.client = self.new_client()
        self.addCleanup(self.client.close)
        self.factory = create_session_factory(engine)

    def make_client(self, settings: Settings | None = None, policy=POLICY) -> None:
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        self.app = create_app(
            settings or Settings(environment="test"),
            session_factory=create_session_factory(engine),
            auth_policy=policy,
            mailer=self.mailer,
        )

    def new_client(self) -> TestClient:
        return TestClient(self.app)

    def signup(self, client=None):
        client = client or self.client
        return client.post(
            f"{BASE}/register",
            json={"email": "ali@example.com", "display_name": "Ali", "password": PASSWORD},
        )

    def login(self, client=None):
        client = client or self.client
        return client.post(f"{BASE}/login", json=CREDENTIALS)

    def test_register_then_login_sets_a_hardened_cookie_and_returns_csrf(self) -> None:
        self.assertEqual(self.signup().status_code, 201)
        response = self.login()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["user"]["email"], "ali@example.com")
        self.assertNotIn("password", str(body))
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("se_session=", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertNotIn("secure", cookie)  # not production
        me = self.client.get(f"{BASE}/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["csrf_token"], body["csrf_token"])

    def test_cookie_is_secure_in_production(self) -> None:
        self.make_client(Settings(environment="production"))
        client = self.new_client()
        self.signup(client)
        response = self.login(client)
        self.assertIn("secure", response.headers["set-cookie"].lower())

    def test_protected_routes_require_a_session(self) -> None:
        self.assertEqual(self.client.get(f"{BASE}/me").status_code, 401)
        self.assertEqual(self.client.post(f"{BASE}/logout").status_code, 401)

    def test_logout_needs_the_csrf_token_and_then_ends_the_session(self) -> None:
        self.signup()
        csrf = self.login().json()["csrf_token"]

        self.assertEqual(self.client.post(f"{BASE}/logout").status_code, 403)
        self.assertEqual(
            self.client.post(f"{BASE}/logout", headers={"X-CSRF-Token": "wrong"}).status_code, 403
        )
        self.assertEqual(self.client.get(f"{BASE}/me").status_code, 200)
        done = self.client.post(f"{BASE}/logout", headers={"X-CSRF-Token": csrf})
        self.assertEqual(done.status_code, 204)
        self.assertEqual(self.client.get(f"{BASE}/me").status_code, 401)

    def test_login_failures_use_one_safe_envelope_and_lock_the_account(self) -> None:
        self.signup()
        bad = {"email": "ali@example.com", "password": "wrong password!"}
        unknown = {"email": "nobody@example.com", "password": "wrong password!"}
        first = self.client.post(f"{BASE}/login", json=bad)
        second = self.client.post(f"{BASE}/login", json=unknown)
        self.assertEqual((first.status_code, second.status_code), (401, 401))
        self.assertEqual(first.json()["error"]["code"], "invalid_credentials")
        self.assertEqual(first.json()["error"]["message"], second.json()["error"]["message"])
        self.assertIn("correlation_id", first.json()["error"])

        for _ in range(POLICY.max_failures):
            self.client.post(f"{BASE}/login", json=bad)
        locked = self.login()
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked.json()["error"]["code"], "account_locked")

    def test_registration_errors(self) -> None:
        self.signup()
        self.assertEqual(self.signup().status_code, 409)
        weak = self.client.post(
            f"{BASE}/register",
            json={"email": "b@example.com", "display_name": "B", "password": "short"},
        )
        self.assertEqual(weak.status_code, 422)
        self.assertEqual(weak.json()["error"]["code"], "weak_password")
        self.assertNotIn("short", str(weak.json()["error"]["message"]))
        missing = self.client.post(f"{BASE}/register", json={"email": "x@example.com"})
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.json()["error"]["code"], "validation_error")

    def test_foreign_origin_is_rejected_but_same_host_and_allowed_origins_pass(self) -> None:
        self.signup()
        foreign = self.client.post(
            f"{BASE}/login", json=CREDENTIALS, headers={"Origin": "https://evil.example"}
        )
        self.assertEqual(foreign.status_code, 403)
        same = self.client.post(
            f"{BASE}/login", json=CREDENTIALS, headers={"Origin": "http://testserver"}
        )
        self.assertEqual(same.status_code, 200)

        self.make_client(
            Settings(environment="test", allowed_origins=("http://localhost:3000",))
        )
        allowed = self.new_client().post(
            f"{BASE}/login", json=CREDENTIALS, headers={"Origin": "http://localhost:3000"}
        )
        self.assertEqual(allowed.status_code, 200)

    def test_change_password_keeps_this_session_and_drops_others(self) -> None:
        self.signup()
        csrf = self.login().json()["csrf_token"]
        other = self.new_client()
        self.login(other)

        new_password = "a brand new passphrase"
        headers = {"X-CSRF-Token": csrf}
        denied = self.client.post(
            f"{BASE}/change-password",
            json={"current_password": PASSWORD, "new_password": new_password},
        )
        self.assertEqual(denied.status_code, 403)
        done = self.client.post(
            f"{BASE}/change-password",
            json={"current_password": PASSWORD, "new_password": new_password},
            headers=headers,
        )
        self.assertEqual(done.status_code, 204)
        self.assertEqual(self.client.get(f"{BASE}/me").status_code, 200)
        self.assertEqual(other.get(f"{BASE}/me").status_code, 401)
        relogin = self.client.post(
            f"{BASE}/login", json={"email": "ali@example.com", "password": new_password}
        )
        self.assertEqual(relogin.status_code, 200)

    def test_password_recovery_flow_does_not_reveal_accounts(self) -> None:
        self.signup()
        unknown = self.client.post(f"{BASE}/password-reset/request", json={"email": "no@example.com"})
        known = self.client.post(f"{BASE}/password-reset/request", json={"email": "ali@example.com"})
        self.assertEqual((unknown.status_code, known.status_code), (202, 202))
        self.assertEqual(unknown.json(), known.json())
        self.assertEqual(len(self.mailer.password_resets), 1)

        token = self.mailer.password_resets[0][1]
        bad = self.client.post(
            f"{BASE}/password-reset/confirm",
            json={"token": "nope", "new_password": "reset to this phrase"},
        )
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            f"{BASE}/password-reset/confirm",
            json={"token": token, "new_password": "reset to this phrase"},
        )
        self.assertEqual(ok.status_code, 204)
        login = self.client.post(
            f"{BASE}/login", json={"email": "ali@example.com", "password": "reset to this phrase"}
        )
        self.assertEqual(login.status_code, 200)

    def test_without_a_database_the_auth_routes_report_unavailable(self) -> None:
        client = TestClient(create_app(Settings(environment="test")))
        response = client.post(f"{BASE}/login", json=CREDENTIALS)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "http_503")


class SqliteHttpTests(HttpChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresHttpTests(HttpChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


class AllowedOriginsSettingTests(unittest.TestCase):
    def test_origins_are_parsed_trimmed_and_default_empty(self) -> None:
        self.assertEqual(Settings.from_env({}).allowed_origins, ())
        parsed = Settings.from_env(
            {"SMART_ENGINEER_ALLOWED_ORIGINS": " http://localhost:3000/ , https://app.example "}
        )
        self.assertEqual(parsed.allowed_origins, ("http://localhost:3000", "https://app.example"))


if __name__ == "__main__":
    unittest.main()
