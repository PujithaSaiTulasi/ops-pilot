"""Module-level ASGI entry point for Uvicorn and Docker."""

from __future__ import annotations

from opspilot.api.app import create_app
from opspilot.config import get_settings
from opspilot.observability.tracing import configure_tracing

configure_tracing(get_settings())
app = create_app()
