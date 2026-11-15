"""Route registration.

``/health`` is the unversioned operational liveness probe documented in the
README. Product API routes live under the versioned prefix ``/api/v1``.
"""

from fastapi import APIRouter

API_V1_PREFIX = "/api/v1"


def health() -> dict[str, str]:
    return {"status": "ok"}


operational_router = APIRouter()
operational_router.add_api_route("/health", health, methods=["GET"])

v1_router = APIRouter(prefix=API_V1_PREFIX)
v1_router.add_api_route("/health", health, methods=["GET"])
