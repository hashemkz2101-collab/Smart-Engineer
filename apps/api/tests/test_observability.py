import json
import logging
import re
import sys
import unittest

from fastapi.testclient import TestClient

from smart_engineer_api.config import Settings
from smart_engineer_api.logging_config import (
    LOGGER_NAME,
    JsonFormatter,
    configure_logging,
)
from smart_engineer_api.main import create_app

SECRET_DETAIL = "secret-internal-detail-7731"  # secret-scan:allow (test fixture)


def build_client() -> TestClient:
    app = create_app(Settings(environment="test", log_level="INFO"))

    def boom() -> None:
        raise RuntimeError(SECRET_DETAIL)

    def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    app.add_api_route("/test-boom", boom, methods=["GET"])
    app.add_api_route("/test-items/{item_id}", get_item, methods=["GET"])
    return TestClient(app, raise_server_exceptions=False)


class CorrelationIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()

    def test_generated_when_absent(self) -> None:
        response = self.client.get("/health")

        self.assertRegex(response.headers["x-correlation-id"], r"^[0-9a-f]{32}$")

    def test_valid_incoming_id_is_echoed(self) -> None:
        response = self.client.get("/health", headers={"X-Correlation-ID": "abc-123_X.y"})

        self.assertEqual(response.headers["x-correlation-id"], "abc-123_X.y")

    def test_invalid_incoming_ids_are_replaced(self) -> None:
        for bad in ("bad id!", "x" * 65, "a;b"):
            with self.subTest(value=bad):
                response = self.client.get("/health", headers={"X-Correlation-ID": bad})

                returned = response.headers["x-correlation-id"]
                self.assertNotEqual(returned, bad)
                self.assertRegex(returned, r"^[0-9a-f]{32}$")

    def test_each_request_gets_a_distinct_id(self) -> None:
        first = self.client.get("/health").headers["x-correlation-id"]
        second = self.client.get("/health").headers["x-correlation-id"]

        self.assertNotEqual(first, second)


class AccessLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()

    def test_access_log_has_request_fields_and_correlation_id(self) -> None:
        with self.assertLogs(f"{LOGGER_NAME}.access", level="INFO") as captured:
            response = self.client.get("/health")

        record = captured.records[0]
        self.assertEqual(record.method, "GET")
        self.assertEqual(record.path, "/health")
        self.assertEqual(record.status_code, 200)
        self.assertGreaterEqual(record.duration_ms, 0)
        self.assertEqual(record.correlation_id, response.headers["x-correlation-id"])

    def test_query_string_is_never_logged(self) -> None:
        with self.assertLogs(f"{LOGGER_NAME}.access", level="INFO") as captured:
            self.client.get("/health?token=query-secret-value")

        for record in captured.records:
            self.assertNotIn("query-secret-value", record.getMessage())
            self.assertNotIn("query-secret-value", record.path)


class SafeErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = build_client()

    def test_unhandled_error_is_logged_with_correlation_id_and_response_is_safe(self) -> None:
        with self.assertLogs(f"{LOGGER_NAME}.errors", level="ERROR") as captured:
            response = self.client.get("/test-boom")

        self.assertEqual(response.status_code, 500)
        body = response.json()
        correlation_id = response.headers["x-correlation-id"]
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertEqual(body["error"]["correlation_id"], correlation_id)
        for leaked in (SECRET_DETAIL, "Traceback", "RuntimeError", ".py"):
            self.assertNotIn(leaked, response.text)

        record = captured.records[0]
        self.assertEqual(record.correlation_id, correlation_id)
        self.assertIsNotNone(record.exc_info)
        server_side = JsonFormatter().format(record)
        self.assertIn(SECRET_DETAIL, server_side)
        self.assertIn(correlation_id, server_side)

    def test_not_found_uses_the_envelope(self) -> None:
        response = self.client.get("/does-not-exist")

        self.assertEqual(response.status_code, 404)
        error = response.json()["error"]
        self.assertEqual(error["code"], "http_404")
        self.assertEqual(error["correlation_id"], response.headers["x-correlation-id"])

    def test_method_not_allowed_keeps_allow_header(self) -> None:
        response = self.client.post("/health")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"]["code"], "http_405")
        self.assertIn("GET", response.headers["allow"])

    def test_validation_error_does_not_echo_input(self) -> None:
        response = self.client.get("/test-items/not-a-number-8842")

        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "validation_error")
        self.assertEqual(error["details"][0]["loc"], ["path", "item_id"])
        self.assertNotIn("not-a-number-8842", response.text)


class LoggingConfigurationTests(unittest.TestCase):
    def test_json_formatter_emits_expected_fields(self) -> None:
        record = logging.LogRecord(
            LOGGER_NAME, logging.INFO, __file__, 1, "hello %s", ("world",), None
        )
        record.correlation_id = "cid-1"
        record.status_code = 204

        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["message"], "hello world")
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["correlation_id"], "cid-1")
        self.assertEqual(payload["status_code"], 204)
        self.assertTrue(re.match(r"\d{4}-\d{2}-\d{2}T", payload["timestamp"]))

    def test_json_formatter_includes_exception_text_for_server_logs(self) -> None:
        try:
            raise ValueError("kaput")
        except ValueError:
            record = logging.LogRecord(
                LOGGER_NAME, logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
            )

        payload = json.loads(JsonFormatter().format(record))

        self.assertIn("ValueError: kaput", payload["exception"])

    def test_configure_logging_is_idempotent(self) -> None:
        configure_logging("INFO")
        configure_logging("DEBUG")

        handlers = [
            h
            for h in logging.getLogger(LOGGER_NAME).handlers
            if getattr(h, "_smart_engineer", False)
        ]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(logging.getLogger(LOGGER_NAME).level, logging.DEBUG)
        configure_logging("INFO")


if __name__ == "__main__":
    unittest.main()
