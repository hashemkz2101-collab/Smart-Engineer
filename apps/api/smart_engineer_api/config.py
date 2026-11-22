"""Application settings read from the process environment.

Only non-secret operational settings live here. Secrets (API keys, database
credentials, payment keys) are not part of this module; their handling is
governed by SEC-005 and later decisions.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

ENVIRONMENTS = ("development", "test", "production")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
POSTGRESQL_URL_PREFIX = "postgresql+psycopg://"
SQLITE_URL_PREFIX = "sqlite://"


class ConfigurationError(ValueError):
    """Raised when an environment setting is present but invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"
    # May contain credentials, so it is excluded from repr() and never logged.
    database_url: str | None = field(default=None, repr=False)
    # Extra browser origins allowed to call state-changing endpoints (e.g. the web
    # dev server on another port). The API's own host is always allowed.
    allowed_origins: tuple[str, ...] = ()
    # Private directory for uploaded project files. Never served statically (SEC-002).
    file_storage_dir: str = "var/files"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env

        environment = source.get("SMART_ENGINEER_ENV", "development").strip().lower()
        if environment not in ENVIRONMENTS:
            raise ConfigurationError(
                "SMART_ENGINEER_ENV must be one of: " + ", ".join(ENVIRONMENTS)
            )

        log_level = source.get("SMART_ENGINEER_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in LOG_LEVELS:
            raise ConfigurationError(
                "SMART_ENGINEER_LOG_LEVEL must be one of: " + ", ".join(LOG_LEVELS)
            )

        database_url = source.get("SMART_ENGINEER_DATABASE_URL", "").strip() or None
        if database_url is not None:
            # The value is never echoed: it may contain a password.
            allowed = (POSTGRESQL_URL_PREFIX, SQLITE_URL_PREFIX)
            if not database_url.startswith(allowed):
                raise ConfigurationError(
                    "SMART_ENGINEER_DATABASE_URL must start with "
                    + " or ".join(allowed)
                )
            if environment == "production" and not database_url.startswith(
                POSTGRESQL_URL_PREFIX
            ):
                raise ConfigurationError(
                    "SMART_ENGINEER_DATABASE_URL must use PostgreSQL in production"
                )

        allowed_origins = tuple(
            origin.strip().rstrip("/")
            for origin in source.get("SMART_ENGINEER_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )

        return cls(
            environment=environment,
            log_level=log_level,
            database_url=database_url,
            allowed_origins=allowed_origins,
            file_storage_dir=source.get("SMART_ENGINEER_FILE_STORAGE_DIR", "").strip()
            or "var/files",
        )
