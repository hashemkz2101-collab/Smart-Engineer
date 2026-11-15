"""Consistent, safe error responses.

Every error response uses one envelope and never includes exception text,
stack traces, request input, or internal paths. Full detail is logged
server-side together with the correlation identifier.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_config import LOGGER_NAME, correlation_id_var
from .middleware import CORRELATION_HEADER

error_logger = logging.getLogger(f"{LOGGER_NAME}.errors")


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None) or correlation_id_var.get()


def _envelope(
    code: str, message: str, correlation_id: str | None, details: list | None = None
) -> dict:
    error: dict = {"code": code, "message": message, "correlation_id": correlation_id}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = "Error"
    return JSONResponse(
        _envelope(f"http_{exc.status_code}", message, _correlation_id(request)),
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Report only where and what failed; never echo the submitted input.
    details = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        _envelope(
            "validation_error",
            "The request is not valid.",
            _correlation_id(request),
            details,
        ),
        status_code=422,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    correlation_id = _correlation_id(request)
    error_logger.error(
        "unhandled exception",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
    headers = {CORRELATION_HEADER: correlation_id} if correlation_id else None
    return JSONResponse(
        _envelope(
            "internal_error",
            "An internal error occurred. Quote the correlation ID when reporting it.",
            correlation_id,
        ),
        status_code=500,
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
