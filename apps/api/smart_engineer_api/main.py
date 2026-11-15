from fastapi import FastAPI

from .config import Settings
from .errors import register_exception_handlers
from .logging_config import configure_logging
from .middleware import CorrelationIdMiddleware
from .routes import operational_router, v1_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Smart Engineer API",
        version="0.1.0",
        description="Smart Engineer backend API.",
    )
    app.state.settings = settings
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(operational_router)
    app.include_router(v1_router)
    return app


app = create_app()
