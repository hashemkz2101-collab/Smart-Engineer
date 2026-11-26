"""Application settings read from the process environment.

Only non-secret operational settings live here. Secrets (API keys, database
credentials, payment keys) are not part of this module; their handling is
governed by SEC-005 and later decisions.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

ENVIRONMENTS = ("development", "test", "production")
SMTP_SECURITY_MODES = ("starttls", "ssl", "none")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
POSTGRESQL_URL_PREFIX = "postgresql+psycopg://"
MYSQL_URL_PREFIX = "mysql+pymysql://"
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
    # Email delivery (DEC-010: account confirmation and recovery go through email).
    # Any SMTP provider works; nothing here is provider specific. The password is
    # excluded from repr() and never logged.
    public_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = field(default=None, repr=False)
    smtp_security: str = "starttls"
    mail_from: str | None = None

    @property
    def mail_configured(self) -> bool:
        return bool(self.smtp_host and self.mail_from and self.public_url)

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
            allowed = (POSTGRESQL_URL_PREFIX, MYSQL_URL_PREFIX, SQLITE_URL_PREFIX)
            if not database_url.startswith(allowed):
                raise ConfigurationError(
                    "SMART_ENGINEER_DATABASE_URL must start with "
                    + ", ".join(allowed[:-1])
                    + " or "
                    + allowed[-1]
                    + " (the plain mysql:// scheme is not supported; use mysql+pymysql://)"
                )
            if environment == "production" and database_url.startswith(SQLITE_URL_PREFIX):
                raise ConfigurationError(
                    "SMART_ENGINEER_DATABASE_URL must use PostgreSQL or MySQL in production"
                )

        allowed_origins = tuple(
            origin.strip().rstrip("/")
            for origin in source.get("SMART_ENGINEER_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )

        smtp_security = source.get("SMART_ENGINEER_SMTP_SECURITY", "starttls").strip().lower()
        if smtp_security not in SMTP_SECURITY_MODES:
            raise ConfigurationError(
                "SMART_ENGINEER_SMTP_SECURITY must be one of: " + ", ".join(SMTP_SECURITY_MODES)
            )
        try:
            smtp_port = int(source.get("SMART_ENGINEER_SMTP_PORT", "").strip() or 587)
        except ValueError:
            raise ConfigurationError("SMART_ENGINEER_SMTP_PORT must be a number") from None
        if not 1 <= smtp_port <= 65535:
            raise ConfigurationError("SMART_ENGINEER_SMTP_PORT must be between 1 and 65535")
        public_url = source.get("SMART_ENGINEER_PUBLIC_URL", "").strip().rstrip("/") or None
        if public_url is not None and not public_url.startswith(("http://", "https://")):
            raise ConfigurationError("SMART_ENGINEER_PUBLIC_URL must start with http:// or https://")
        smtp_host = source.get("SMART_ENGINEER_SMTP_HOST", "").strip() or None
        mail_from = source.get("SMART_ENGINEER_MAIL_FROM", "").strip() or None
        if smtp_host and not (mail_from and public_url):
            raise ConfigurationError(
                "SMART_ENGINEER_SMTP_HOST also needs SMART_ENGINEER_MAIL_FROM "
                "and SMART_ENGINEER_PUBLIC_URL (links in emails)"
            )

        return cls(
            environment=environment,
            public_url=public_url,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=source.get("SMART_ENGINEER_SMTP_USERNAME", "").strip() or None,
            smtp_password=source.get("SMART_ENGINEER_SMTP_PASSWORD", "") or None,
            smtp_security=smtp_security,
            mail_from=mail_from,
            log_level=log_level,
            database_url=database_url,
            allowed_origins=allowed_origins,
            file_storage_dir=source.get("SMART_ENGINEER_FILE_STORAGE_DIR", "").strip()
            or "var/files",
        )
