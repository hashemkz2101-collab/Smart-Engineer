from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from . import auth_service
from .auth_routes import auth_error_handler
from .auth_routes import router as auth_router
from .config import Settings
from .db.session import create_db_engine, create_session_factory
from .errors import register_exception_handlers
from .intake_routes import intake_error_handler, intake_validation_handler
from .intake_routes import router as intake_router
from .intake_service import IntakeError, IntakeValidationError
from .site_routes import router as site_router
from .site_routes import site_error_handler, site_validation_handler
from .site_service import SiteError, SiteValidationError
from .logging_config import configure_logging
from .middleware import CorrelationIdMiddleware
from .org_routes import access_denied_handler, org_error_handler
from .org_routes import router as org_router
from .org_service import OrgError
from .permissions import AccessDenied
from .project_routes import project_error_handler
from .project_routes import router as project_router
from .project_service import ProjectError
from .routes import API_V1_PREFIX, operational_router, v1_router


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
    auth_policy: auth_service.AuthPolicy | None = None,
    mailer: auth_service.Mailer | None = None,
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
    # Real email delivery is blocked on DEC-010; the outbox only keeps messages in memory.
    app.state.mailer = mailer or auth_service.OutboxMailer()
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.add_exception_handler(auth_service.AuthError, auth_error_handler)
    app.add_exception_handler(OrgError, org_error_handler)
    app.add_exception_handler(AccessDenied, access_denied_handler)
    app.add_exception_handler(ProjectError, project_error_handler)
    app.add_exception_handler(IntakeError, intake_error_handler)
    app.add_exception_handler(IntakeValidationError, intake_validation_handler)
    app.add_exception_handler(SiteError, site_error_handler)
    app.add_exception_handler(SiteValidationError, site_validation_handler)
    app.include_router(operational_router)
    app.include_router(v1_router)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    app.include_router(org_router, prefix=API_V1_PREFIX)
    app.include_router(project_router, prefix=API_V1_PREFIX)
    app.include_router(intake_router, prefix=API_V1_PREFIX)
    app.include_router(site_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
