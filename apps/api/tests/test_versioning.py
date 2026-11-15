import unittest

from fastapi.testclient import TestClient

from smart_engineer_api.config import Settings
from smart_engineer_api.main import create_app


class VersionedRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(Settings(environment="test")))

    def test_v1_health_matches_operational_health(self) -> None:
        versioned = self.client.get("/api/v1/health")
        operational = self.client.get("/health")

        self.assertEqual(versioned.status_code, 200)
        self.assertEqual(versioned.json(), {"status": "ok"})
        self.assertEqual(versioned.json(), operational.json())

    def test_openapi_lists_versioned_and_operational_health(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]

        self.assertIn("/api/v1/health", paths)
        self.assertIn("/health", paths)

    def test_unknown_api_version_is_not_found(self) -> None:
        response = self.client.get("/api/v2/health")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "http_404")


if __name__ == "__main__":
    unittest.main()
