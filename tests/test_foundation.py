"""Foundation tests: repository layout, Makefile, Compose, and safety rails."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.override.yml",
    "ops/prometheus/prometheus.yml",
    "ops/otel-collector/config.yaml",
    "ops/prometheus/alerts.yml",
    "ops/grafana/provisioning/datasources/datasource.yml",
    "ops/grafana/provisioning/dashboards/dashboard.yml",
    "ops/grafana/dashboards/opspilot.json",
    "LICENSE",
]

REQUIRED_MAKE_TARGETS = {
    "install",
    "up",
    "down",
    "test",
    "lint",
    "inject",
    "investigate",
    "eval",
    "clean",
}

REQUIRED_COMPOSE_SERVICES = {
    "api",
    "checkout",
    "payment",
    "inventory",
    "redis",
    "prometheus",
    "otel-collector",
    "grafana",
    "jaeger",
}

#: Patterns that must never appear in source code.
FORBIDDEN_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),  # OpenAI-style live key
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def test_required_files_exist() -> None:
    missing = [path for path in REQUIRED_FILES if not (REPO_ROOT / path).exists()]

    assert not missing, f"missing foundation files: {missing}"


def _makefile_targets() -> set[str]:
    targets: set[str] = set()
    for line in (REPO_ROOT / "Makefile").read_text().splitlines():
        if not line or line.startswith(("\t", ".")) or ":" not in line:
            continue
        targets.add(line.split(":", 1)[0].strip())
    return targets


def test_makefile_exposes_required_targets() -> None:
    missing = REQUIRED_MAKE_TARGETS - _makefile_targets()

    assert not missing, f"Makefile is missing targets: {sorted(missing)}"


def test_makefile_is_phony_and_has_help() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert ".PHONY:" in makefile
    phony_line = next(line for line in makefile.splitlines() if line.startswith(".PHONY:"))
    declared = {name.strip() for name in phony_line.split(":", 1)[1].split()}

    assert REQUIRED_MAKE_TARGETS <= declared
    assert "help" in declared


def test_env_file_is_gitignored() -> None:
    lines = {
        line.strip()
        for line in (REPO_ROOT / ".gitignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert ".env" in lines, ".env must be gitignored"
    assert "!.env.example" in lines, ".env.example must remain committable"


def test_compose_defines_the_full_stack() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    services = compose["services"]

    assert REQUIRED_COMPOSE_SERVICES <= set(services)
    assert "build" in services["api"]
    assert services["redis"].get("healthcheck"), "redis needs a healthcheck"
    assert set(compose["volumes"]) >= {"promdata"}


def test_compose_override_enables_dev_reload() -> None:
    override = yaml.safe_load((REPO_ROOT / "docker-compose.override.yml").read_text())
    command = " ".join(str(part) for part in override["services"]["api"]["command"])

    assert "--reload" in command


def test_prometheus_scrapes_the_api() -> None:
    config = yaml.safe_load((REPO_ROOT / "ops/prometheus/prometheus.yml").read_text())
    jobs = config["scrape_configs"]

    targets = [
        target for job in jobs for host in job["static_configs"] for target in host["targets"]
    ]
    assert "api:8000" in targets


def test_otel_collector_exports_locally_only() -> None:
    config = yaml.safe_load((REPO_ROOT / "ops/otel-collector/config.yaml").read_text())
    exporters = set(config["service"]["pipelines"]["traces"]["exporters"])

    assert exporters <= {"debug", "logging", "otlphttp/jaeger"}, "traces must stay local"


def test_dockerfile_runs_as_non_root_with_healthcheck() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()

    assert "HEALTHCHECK" in dockerfile
    assert "\nUSER " in dockerfile, "container must not run as root"
    assert "python:3.12" in dockerfile
    assert "COPY scenarios ./scenarios" in dockerfile
    assert "COPY data/runbooks ./data/runbooks" in dockerfile


def test_legacy_scaffold_is_absent() -> None:
    assert not (REPO_ROOT / "src/ops_pilot").exists()
    assert not (REPO_ROOT / "prometheus").exists()
    assert not (REPO_ROOT / "otelcol").exists()


def test_no_hardcoded_credentials_in_source() -> None:
    violations: list[str] = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        text = path.read_text()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                violations.append(f"{path.relative_to(REPO_ROOT)}: {pattern.pattern}")

    assert not violations, f"hardcoded credentials found: {violations}"


def test_env_example_has_no_real_keys() -> None:
    for line in (REPO_ROOT / ".env.example").read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        for pattern in FORBIDDEN_PATTERNS:
            assert not pattern.search(value), f"possible secret for {key.strip()} in .env.example"
        if key.strip() == "OPENAI_API_KEY":
            assert value.strip() == "", "OPENAI_API_KEY must be empty in .env.example"
