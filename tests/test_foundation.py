"""Foundation-phase tests: configuration, project hygiene, and tooling files."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from ops_pilot.config import Settings, get_settings

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_settings_defaults_are_safe_and_mocked() -> None:
    """Defaults must run without any API key or external services."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        openai_api_key=None,
        mock_llm=True,
    )
    assert settings.mock_llm is True
    assert settings.openai_api_key is None
    assert settings.external_notifications_enabled is False
    assert settings.environment in {"dev", "test", "prod"}
    assert "sqlite" in settings.database_url


@pytest.mark.unit
def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-test")
    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.setenv("INVESTIGATION_MAX_STEPS", "7")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.openai_model == "gpt-4o-test"
    assert settings.mock_llm is False
    assert settings.investigation_max_steps == 7


@pytest.mark.unit
def test_get_settings_is_cached_singleton() -> None:
    assert get_settings() is get_settings()


@pytest.mark.unit
def test_env_example_covers_all_settings_fields() -> None:
    """.env.example must document every configurable Settings field."""
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0].strip()
        for line in env_example.splitlines()
        if line.strip() and not line.startswith("#") and "=" in line
    }
    fields = {name.upper() for name in Settings.model_fields}
    # APP_NAME is documented too, matching Settings.app_name.
    missing = fields - documented
    assert not missing, f"Undocumented settings in .env.example: {sorted(missing)}"


@pytest.mark.unit
def test_env_file_is_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    # Normalize: strip comments/blank lines and trailing slashes (`dir/` == `dir`).
    patterns = {
        ln.strip().rstrip("/")
        for ln in gitignore.splitlines()
        if ln.strip() and not ln.startswith("#")
    }
    assert ".env" in patterns, ".env must be explicitly gitignored"
    assert ".venv" in patterns


@pytest.mark.unit
def test_no_hardcoded_openai_keys_in_repo() -> None:
    """No file may embed a real-looking API key."""
    # Assembled dynamically so this scanner file doesn't flag itself.
    needle = "sk" + "-" + "proj"
    skip_dirs = {".git", ".venv", "__pycache__", "node_modules"}
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or any(part in skip_dirs for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if needle in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Possible hardcoded API keys in: {offenders}"


@pytest.mark.unit
def test_makefile_has_required_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    targets = {"install", "up", "down", "test", "lint", "inject", "investigate", "eval", "clean"}
    declared = {
        line.split(":", 1)[0].strip()
        for line in makefile.splitlines()
        if line and not line.startswith(("\t", "#", " ")) and ":" in line
    }
    missing = targets - declared
    assert not missing, f"Missing Makefile targets: {sorted(missing)}"
    assert "SCENARIO=" in makefile, "make inject must accept SCENARIO=..."


@pytest.mark.unit
def test_compose_files_define_expected_services() -> None:
    base = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    override = yaml.safe_load(
        (REPO_ROOT / "docker-compose.override.yml").read_text(encoding="utf-8")
    )
    assert base["services"].keys() >= {"api", "postgres", "redis", "prometheus"}
    assert "otel-collector" in base["services"]
    assert override["services"].keys() <= base["services"].keys()
    # API must never be handed a secret through compose `environment` defaults.
    api_env = base["services"]["api"]["environment"]
    assert api_env["OPENAI_API_KEY"] == "${OPENAI_API_KEY:-}"


@pytest.mark.unit
def test_pyproject_declares_required_stack() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["requires-python"] == ">=3.12"
    deps = " ".join(data["project"]["dependencies"]).lower()
    for required in ("fastapi", "pydantic", "openai", "mcp", "prometheus-client", "opentelemetry"):
        assert required in deps, f"missing dependency: {required}"
    dev_deps = " ".join(data["project"]["optional-dependencies"]["dev"]).lower()
    for required in ("pytest", "ruff"):
        assert required in dev_deps, f"missing dev dependency: {required}"


@pytest.mark.unit
def test_health_endpoints_respond() -> None:
    from fastapi.testclient import TestClient

    from ops_pilot.main import app

    client = TestClient(app)
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").json()["status"] == "ready"
