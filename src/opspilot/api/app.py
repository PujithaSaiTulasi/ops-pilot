"""FastAPI application factory (foundation skeleton)."""

from __future__ import annotations

from fastapi import FastAPI

from opspilot import __version__
from opspilot.config import Settings, get_settings
from opspilot.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the OpsPilot ASGI application."""
    app_settings = settings or get_settings()
    configure_logging(level=app_settings.log_level, fmt=app_settings.log_format)

    application = FastAPI(
        title=app_settings.app_name,
        version=__version__,
        description="Agentic incident-response platform (foundation skeleton).",
    )

    @application.get("/healthz", tags=["ops"], summary="Liveness probe")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/version", tags=["ops"], summary="Build version and environment")
    def version() -> dict[str, str]:
        return {"version": __version__, "environment": app_settings.environment}

    return application
