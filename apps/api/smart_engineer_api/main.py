from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from . import auth_service
from .admin_routes import admin_error_handler
from .admin_routes import router as admin_router
from .admin_service import AdminError
from .auth_routes import auth_error_handler
from .auth_routes import router as auth_router
from .config import ConfigurationError, Settings
from .db.session import create_db_engine, create_session_factory
from .environment_routes import environment_error_handler, environment_validation_handler
from .environment_routes import router as environment_router
from .environment_service import EnvironmentError_, EnvironmentValidationError
from .errors import register_exception_handlers
from .file_routes import file_error_handler
from .file_routes import router as file_router
from .file_service import FileError
from .file_storage import FileStorage
from .intake_routes import intake_error_handler, intake_validation_handler
from .intake_routes import router as intake_router
from .intake_service import IntakeError, IntakeValidationError
from .logging_config import configure_logging
from .mail import SmtpMailer
from .scanner import ClamdScanner, ContentScanner
from .middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from .org_routes import access_denied_handler, org_error_handler
from .org_routes import router as org_router
from .org_service import OrgError
from .permissions import AccessDenied
from .project_routes import project_error_handler
from .project_routes import router as project_router
from .project_service import ProjectError
from .requirements_routes import requirements_error_handler, requirements_validation_handler
from .requirements_routes import router as requirements_router
from .requirements_service import RequirementsError, RequirementsValidationError
from .routes import API_V1_PREFIX, operational_router, v1_router
from .site_routes import router as site_router
from .site_routes import site_error_handler, site_validation_handler
from .site_service import SiteError, SiteValidationError
from .zoning_routes import router as zoning_router
from .zoning_routes import zoning_error_handler, zoning_validation_handler
from .zoning_service import ZoningError, ZoningValidationError


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
    auth_policy: auth_service.AuthPolicy | None = None,
    mailer: auth_service.Mailer | None = None,
    file_storage: FileStorage | None = None,
    scanner: ContentScanner | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Smart Engineer API",
        version="0.1.0",
        description="Smart Engineer backend API.",
    )
    app.state.settings = settings
    if session_factory is None and settings.database_url:
        # Creating an engine does not connect; the first request does.
        session_factory = create_session_factory(create_db_engine(settings.database_url))
    app.state.session_factory = session_factory
    app.state.auth_policy = auth_policy or auth_service.AuthPolicy(
        require_email_verification=settings.environment == "production"
    )
    if mailer is None:
        if settings.mail_configured:
            mailer = SmtpMailer(settings)
        elif settings.environment == "production":
            # Production requires verified emails, so without a mail server nobody could
            # sign in. Fail at startup rather than lock everyone out.
            raise ConfigurationError(
                "Production needs SMART_ENGINEER_SMTP_HOST, SMART_ENGINEER_MAIL_FROM "
                "and SMART_ENGINEER_PUBLIC_URL"
            )
        else:
            # Development and tests: messages are only kept in memory.
            mailer = auth_service.OutboxMailer()
    app.state.mailer = mailer
    app.state.file_storage = file_storage or FileStorage(settings.file_storage_dir)
    if scanner is None and settings.clamav_configured:
        scanner = ClamdScanner(
            host=settings.clamav_host,
            port=settings.clamav_port,
            socket_path=settings.clamav_socket,
            timeout=settings.clamav_timeout,
        )
    app.state.scanner = scanner
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.environment == "production")
    register_exception_handlers(app)
    app.add_exception_handler(auth_service.AuthError, auth_error_handler)
    app.add_exception_handler(OrgError, org_error_handler)
    app.add_exception_handler(AccessDenied, access_denied_handler)
    app.add_exception_handler(ProjectError, project_error_handler)
    app.add_exception_handler(IntakeError, intake_error_handler)
    app.add_exception_handler(IntakeValidationError, intake_validation_handler)
    app.add_exception_handler(SiteError, site_error_handler)
    app.add_exception_handler(SiteValidationError, site_validation_handler)
    app.add_exception_handler(AdminError, admin_error_handler)
    app.add_exception_handler(FileError, file_error_handler)
    app.add_exception_handler(EnvironmentError_, environment_error_handler)
    app.add_exception_handler(EnvironmentValidationError, environment_validation_handler)
    app.add_exception_handler(RequirementsError, requirements_error_handler)
    app.add_exception_handler(RequirementsValidationError, requirements_validation_handler)
    app.add_exception_handler(ZoningError, zoning_error_handler)
    app.add_exception_handler(ZoningValidationError, zoning_validation_handler)
    app.include_router(operational_router)
    app.include_router(v1_router)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    app.include_router(org_router, prefix=API_V1_PREFIX)
    app.include_router(project_router, prefix=API_V1_PREFIX)
    app.include_router(intake_router, prefix=API_V1_PREFIX)
    app.include_router(site_router, prefix=API_V1_PREFIX)
    app.include_router(admin_router, prefix=API_V1_PREFIX)
    app.include_router(file_router, prefix=API_V1_PREFIX)
    app.include_router(environment_router, prefix=API_V1_PREFIX)
    app.include_router(requirements_router, prefix=API_V1_PREFIX)
    app.include_router(zoning_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
