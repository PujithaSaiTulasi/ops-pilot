"""Application configuration.

Every runtime knob is read from environment variables (optionally via a local
`.env` file that is gitignored). No secrets are ever hardcoded here — defaults
are safe for local, simulated use.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, environment-driven configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_name: str = "OpsPilot"
    environment: str = Field(default="dev", pattern="^(dev|test|prod)$")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # LLM — empty key + mock_llm=true means deterministic tests, no API calls.
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    mock_llm: bool = True

    # Storage
    database_url: str = "sqlite+aiosqlite:///./var/opspilot.db"
    postgres_user: str = "opspilot"
    postgres_password: SecretStr = SecretStr("opspilot")
    postgres_db: str = "opspilot"
    redis_url: str = "redis://localhost:6379/0"

    # Simulator / investigation controls
    scenario_dir: str = "./scenarios"
    investigation_max_steps: int = Field(default=25, ge=1, le=200)
    approval_timeout_seconds: int = Field(default=900, ge=1)

    # Observability
    otel_enabled: bool = True
    otel_service_name: str = "opspilot"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    prometheus_enabled: bool = True

    # Guardrails
    external_notifications_enabled: bool = False

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (process-wide singleton)."""
    return Settings()
