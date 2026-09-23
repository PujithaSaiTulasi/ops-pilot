"""Tests for the FastAPI application skeleton."""

from __future__ import annotations

from fastapi.testclient import TestClient

from opspilot import __version__
from opspilot.api.app import create_app
from opspilot.config import Settings


def _client() -> TestClient:
    settings = Settings(_env_file=None, environment="test")
    return TestClient(create_app(settings))


def test_healthz_returns_ok() -> None:
    response = _client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_reports_build_and_environment() -> None:
    response = _client().get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": __version__, "environment": "test"}


def test_openapi_document_is_generated() -> None:
    response = _client().get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert document["info"]["title"] == "OpsPilot"
    assert "/healthz" in document["paths"]
