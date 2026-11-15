import unittest

from fastapi.testclient import TestClient

from smart_engineer_api.main import app


class ApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(set(response.json()), {"status"})

    def test_openapi_metadata_and_health_operation(self) -> None:
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(schema["info"]["title"], "Smart Engineer API")
        self.assertEqual(schema["info"]["version"], "0.1.0")
        self.assertIn("/health", schema["paths"])
        self.assertIn("get", schema["paths"]["/health"])

    def test_interactive_docs(self) -> None:
        response = self.client.get("/docs")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/html"))
        self.assertNotIn("Internal Server Error", response.text)


if __name__ == "__main__":
    unittest.main()
