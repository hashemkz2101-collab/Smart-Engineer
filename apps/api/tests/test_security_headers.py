import unittest

from fastapi.testclient import TestClient

from smart_engineer_api.config import Settings
from smart_engineer_api.main import create_app
from smart_engineer_api.middleware import HSTS_VALUE

BASE = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "cross-origin-resource-policy": "same-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


def client(environment: str = "test") -> TestClient:
    return TestClient(create_app(Settings(environment=environment)))


class SecurityHeaderTests(unittest.TestCase):
    def test_api_responses_carry_the_base_and_api_only_headers(self) -> None:
        for path in ("/api/v1/auth/me", "/api/v1/does-not-exist", "/api/v1/auth/login"):
            response = client().get(path)
            for name, value in BASE.items():
                self.assertEqual(response.headers.get(name), value, (path, name))
            self.assertEqual(response.headers["cache-control"], "no-store", path)
            self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])

    def test_health_gets_the_base_headers_but_no_api_only_ones(self) -> None:
        response = client().get("/health")
        for name, value in BASE.items():
            self.assertEqual(response.headers.get(name), value, name)
        self.assertNotIn("content-security-policy", response.headers)

    def test_hsts_only_in_production(self) -> None:
        self.assertNotIn("strict-transport-security", client("test").get("/health").headers)
        self.assertNotIn("strict-transport-security", client("development").get("/health").headers)

    def test_hsts_value_is_set_by_the_middleware_when_enabled(self) -> None:
        from fastapi import FastAPI

        from smart_engineer_api.middleware import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, hsts=True)

        @app.get("/x")
        def route() -> dict:
            return {}

        response = TestClient(app).get("/x")
        self.assertEqual(response.headers["strict-transport-security"], HSTS_VALUE)

    def test_a_header_the_route_set_is_not_overwritten(self) -> None:
        from fastapi import FastAPI, Response

        from smart_engineer_api.middleware import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/api/download")
        def download() -> Response:
            return Response(b"x", headers={"Cache-Control": "private, no-store"})

        response = TestClient(app).get("/api/download")
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
