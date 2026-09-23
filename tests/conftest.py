"""Shared pytest fixtures for the OpsPilot test-suite.

Tests are deterministic and offline: mock LLM mode is forced, credentials are
removed from the environment, and the settings cache is cleared around every
test so no test can observe another test's configuration.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from opspilot.config import get_settings


@pytest.fixture(autouse=True)
def _deterministic_test_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    """Force mock mode, drop credentials, and isolate storage per test.

    Tests must never require a real ``OPENAI_API_KEY`` or network access.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
    monkeypatch.setenv("APPROVAL_STORE_PATH", str(tmp_path / "approvals.json"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
