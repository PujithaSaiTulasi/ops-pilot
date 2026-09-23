"""Environment-driven configuration for OpsPilot.

All runtime configuration comes from environment variables (optionally loaded
from a ``.env`` file — see ``.env.example``). Secrets are never hardcoded in
the repository, and mock mode is the default so that no API key is required
for development or tests.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Side-effecting actions that always require explicit human approval.
DEFAULT_APPROVAL_ACTIONS: tuple[str, ...] = (
    "rollback",
    "restart",
    "deploy",
    "delete",
    "notify",
)


class Settings(BaseSettings):
    """Typed, environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Core ────────────────────────────────────────────────────────────────
    app_name: str = "OpsPilot"
    environment: Literal["development", "test", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # ── Logging ─────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # ── LLM ─────────────────────────────────────────────────────────────────
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    #: Deterministic mock mode: scripted agent behaviour, no network, no key.
    mock_llm: bool = True
    mock_llm_seed: int = 7

    # ── Storage ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/opspilot.db"
    redis_url: str = "redis://localhost:6379/0"
    payment_url: str = "http://localhost:8002"
    inventory_url: str = "http://localhost:8003"
    service_version: str = "1.0.0"

    # ── Incident simulator ──────────────────────────────────────────────────
    scenario_dir: Path = Path("scenarios")

    # ── Agent guardrails ────────────────────────────────────────────────────
    max_investigation_steps: int = Field(default=12, ge=1, le=100)
    max_tool_calls_per_step: int = Field(default=8, ge=1, le=50)
    tool_timeout_seconds: float = Field(default=10.0, gt=0)

    # ── Human approval ──────────────────────────────────────────────────────
    #: Actions that may never execute without an explicit human approval.
    require_approval_for: list[str] = Field(default_factory=lambda: list(DEFAULT_APPROVAL_ACTIONS))
    approval_timeout_seconds: int = Field(default=300, ge=1)
    approval_store_path: Path = Path("data/approvals.json")
    audit_log_path: Path = Path("data/audit.jsonl")

    # ── Observability ───────────────────────────────────────────────────────
    enable_metrics: bool = True
    otel_service_name: str = "opspilot"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_traces_exporter: Literal["otlp", "console", "none"] = "otlp"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()
