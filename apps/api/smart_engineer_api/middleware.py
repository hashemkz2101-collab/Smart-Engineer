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


_BASE_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
# The API only returns JSON and downloads, never pages, so it can forbid everything.
_API_ONLY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}
HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware:
    """Adds defensive response headers (SEC-001).

    Headers a route already set (for example a download's ``Cache-Control``) win.
    HSTS is sent only in production, where the service sits behind TLS; sending it
    during local HTTP development would pin browsers to HTTPS for no benefit.
    """

    def __init__(self, app, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_api = scope.get("path", "").startswith("/api/")

        async def send_with_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                wanted = dict(_BASE_SECURITY_HEADERS)
                if is_api:
                    wanted.update(_API_ONLY_HEADERS)
                if self.hsts:
                    wanted["Strict-Transport-Security"] = HSTS_VALUE
                for name, value in wanted.items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
