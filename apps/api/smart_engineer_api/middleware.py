"""Correlation-ID and access-log middleware (pure ASGI)."""

import logging
import re
import time
import uuid

from starlette.datastructures import MutableHeaders

from .logging_config import LOGGER_NAME, correlation_id_var

CORRELATION_HEADER = "X-Correlation-ID"
_VALID_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

access_logger = logging.getLogger(f"{LOGGER_NAME}.access")


def _incoming_correlation_id(scope) -> str:
    wanted = CORRELATION_HEADER.lower().encode("latin-1")
    for name, value in scope.get("headers", []):
        if name == wanted:
            candidate = value.decode("latin-1")
            if _VALID_ID.fullmatch(candidate):
                return candidate
            break
    return uuid.uuid4().hex


class CorrelationIdMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        correlation_id = _incoming_correlation_id(scope)
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_header(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[CORRELATION_HEADER] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            # Only the path is logged; query strings may carry sensitive values.
            access_logger.info(
                "request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            correlation_id_var.reset(token)
