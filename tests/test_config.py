"""Tests for environment-driven configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from opspilot.config import DEFAULT_APPROVAL_ACTIONS, Settings

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Keys in `.env.example` consumed by Docker Compose interpolation rather than
#: by `Settings` itself.
COMPOSE_ONLY_KEYS = {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_PORT"}

REQUIRED_ENV_KEYS = {
    "OPENAI_API_KEY",
    "MOCK_LLM",
    "DATABASE_URL",
    "REDIS_URL",
    "PAYMENT_URL",
    "INVENTORY_URL",
    "SERVICE_VERSION",
    "ENVIRONMENT",
    "LOG_FORMAT",
}


def _env_example_keys() -> list[str]:
    keys: list[str] = []
    for raw_line in (REPO_ROOT / ".env.example").read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.append(line.split("=", 1)[0])
    return keys


def test_defaults_enable_deterministic_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock mode is the default: no API key and no network are required."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)  # tests run with ENVIRONMENT=test

    settings = Settings(_env_file=None)

    assert settings.mock_llm is True
    assert settings.openai_api_key is None
    assert settings.environment == "development"
    assert settings.app_name == "OpsPilot"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key-not-a-real-secret")
    monkeypatch.setenv("API_PORT", "9001")

    settings = Settings(_env_file=None)

    assert settings.mock_llm is False
    assert settings.api_port == 9001
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "unit-test-key-not-a-real-secret"


def test_secret_is_never_rendered_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key-not-a-real-secret")

    settings = Settings(_env_file=None)

    assert "unit-test-key-not-a-real-secret" not in repr(settings)
    assert "unit-test-key-not-a-real-secret" not in str(settings.model_dump())


def test_invalid_api_port_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "70000")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_side_effecting_actions_require_approval() -> None:
    """Rollback, restart, deploy, delete, and notify are approval-gated."""
    settings = Settings(_env_file=None)

    assert set(settings.require_approval_for) == set(DEFAULT_APPROVAL_ACTIONS)
    assert set(DEFAULT_APPROVAL_ACTIONS) == {"rollback", "restart", "deploy", "delete", "notify"}
    assert settings.approval_timeout_seconds > 0


def test_env_example_covers_every_documented_setting() -> None:
    keys = _env_example_keys()
    settings_env_names = {name.upper() for name in Settings.model_fields}

    unknown = set(keys) - settings_env_names - COMPOSE_ONLY_KEYS

    assert not unknown, f".env.example documents unknown keys: {sorted(unknown)}"
    assert REQUIRED_ENV_KEYS <= set(keys), ".env.example is missing required keys"
    assert len(keys) == len(set(keys)), ".env.example contains duplicate keys"


def test_env_example_parses_into_settings() -> None:
    """The shipped `.env.example` must be valid configuration as-is."""
    settings = Settings(_env_file=REPO_ROOT / ".env.example")

    assert settings.max_investigation_steps == 12
    assert settings.approval_timeout_seconds == 300
    assert str(settings.approval_store_path) == "data/approvals.json"
    assert str(settings.audit_log_path) == "data/audit.jsonl"
    assert set(settings.require_approval_for) == set(DEFAULT_APPROVAL_ACTIONS)
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    assert api_key in (None, ""), "`.env.example` must not contain a real API key"
