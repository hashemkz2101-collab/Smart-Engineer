"""Application settings read from the process environment.

Only non-secret operational settings live here. Secrets (API keys, database
credentials, payment keys) are not part of this module; their handling is
governed by SEC-005 and later decisions.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

ENVIRONMENTS = ("development", "test", "production")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class ConfigurationError(ValueError):
    """Raised when an environment setting is present but invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
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

        return cls(environment=environment, log_level=log_level)
