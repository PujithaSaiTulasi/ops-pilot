"""Module-level ASGI entry point for Uvicorn and Docker."""

from __future__ import annotations

from opspilot.api.app import create_app

app = create_app()
