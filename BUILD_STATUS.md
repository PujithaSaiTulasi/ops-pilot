# OpsPilot — Build Status

**Last updated:** 2026-09-22 · **Current phase:** Phase 1 — Foundation ✅ complete

> Rule of record: nothing is listed as "done" unless its tests/commands were
> actually run and their results recorded under "Tests run".

---

## Phase 1 — Foundation

### Completed

- Repository initialised; src-layout package under `src/opspilot/` + `tests/`.
- `pyproject.toml`: Python 3.12 (`requires-python = ">=3.12"`), runtime + dev
  dependencies, pytest, coverage, ruff (lint/format), mypy config. Version
  `0.1.0`, single-sourced against `opspilot.__version__` (tested).
- Typed environment settings (`src/opspilot/config.py`, pydantic-settings):
  - mock LLM mode **on by default** (`MOCK_LLM=true`) — no API key needed;
  - secrets modelled as `SecretStr`, never rendered in `repr`;
  - approval-gated action list hardwired to
    `rollback, restart, deploy, delete, notify` (rule 9);
  - validation on ports, budgets, and timeouts.
- JSON structured logging (`src/opspilot/logging.py`): one JSON object per
  line, structured extras preserved, exceptions captured, idempotent handler.
- FastAPI application factory (`/healthz`, `/version`, `/docs`, `/openapi.json`).
- CLI entry point (`opspilot.cli`) with `inject` / `investigate` / `eval`
  subcommands, wired to the Makefile; each currently exits non-zero with an
  explicit "not implemented yet" message (no fake success).
- `.env.example` documents **every** setting (tested for validity, uniqueness,
  and absence of secrets); `.env` + `.env.*` gitignored with `!.env.example`
  (verified via `git check-ignore`); `.dockerignore` keeps local config out of
  images.
- `Dockerfile`: `python:3.12-slim`, non-root user, bytecode disabled,
  `HEALTHCHECK` against `/healthz`.
- `docker-compose.yml`: `api`, `db` (postgres:16, healthcheck), `redis`
  (healthcheck), `prometheus`, `otel-collector`, named volumes; optional
  `.env` loading (`required: false`).
- `docker-compose.override.yml`: dev hot-reload (`uvicorn --reload`, read-only
  `./src` mount).
- Ops configs: `ops/prometheus/prometheus.yml` (scrapes `api:8000/metrics`),
  `ops/otel-collector/config.yaml` (OTLP in, **local debug exporter only** —
  no external exports).
- `Makefile` with all required targets: `install`, `up`, `down`, `test`,
  `lint`, `inject` (`SCENARIO=`), `investigate`, `eval`, `clean`, plus `help`.
- Docs & meta: `README.md` (architecture, quickstart, layout, safety),
  `LICENSE` (MIT), `scenarios/README.md`, `data/.gitkeep`, `.dockerignore`.
- Placeholder packages for planned components: `agent`, `mcp`, `tools`,
  `guardrails`, `approval`, `audit`, `llm`, `simulator`, `evals`,
  `observability`.

### Tests run

All commands executed from the repo root on 2026-09-22:

| Command                            | Result                                                                 |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `make install`                     | OK — `.venv` (CPython 3.12.14), editable install, dev extras           |
| `make test`                        | **35 passed, 0 failed** (0.5 s); coverage **97%** (105 stmts, 12 branches) |
| `make lint`                        | OK — `ruff check` clean, `ruff format --check` 29 files clean, `mypy` no issues in 22 files |
| `docker compose config -q`         | OK — base + override Compose files valid                               |
| `make help`                        | OK — all targets listed with descriptions                              |
| `make clean`                       | OK — caches removed; `make test` re-run afterwards: still 35 passed    |
| `make inject SCENARIO=bad_deployment` | Exits non-zero with documented "not implemented yet" message        |
| `make investigate` / `make eval`   | Exits non-zero with documented "not implemented yet" message           |
| `git check-ignore .env`            | Ignored by `.gitignore:2`; `.env.example` remains committable          |

Test breakdown by module: `test_config` (8), `test_logging` (6), `test_app` (3),
`test_cli` (6), `test_foundation` (11), `test_version` (2), + fixture-driven
isolation (`tests/conftest.py` forces mock mode, strips credentials, clears the
settings cache per test).

**Fixed during this phase:** one failing assertion (conftest forces
`ENVIRONMENT=test`; defaults test now clears it first), one ruff `B010`
(`setattr` → marked `_OpspilotHandler` subclass), and `ruff format` applied to
5 files.

### Remaining (Phase 1 follow-ups)

- **`docker build` / `make up` not executed** — the Docker daemon is not
  running on this machine (Docker Desktop not started). Compose files were
  validated statically with `docker compose config -q`; first runtime
  verification (image build, container healthcheck, Prometheus/OTel startup)
  is deferred to the next phase.
- `/metrics` endpoint does not exist yet — Prometheus will report the `api`
  target down until Phase 7.
- No git commit made yet (working tree staged, awaiting first commit).
- Application logic not built (by design this phase): simulator, MCP servers,
  tool registry, agent loop, guardrails, approval flow, audit log, evaluations.

---

## Phase 2 — Incident simulator _(not started)_

## Phase 3 — MCP servers + typed tool registry _(not started)_

## Phase 4 — LLM client (mock mode) + investigation agent loop _(not started)_

## Phase 5 — Guardrails + human approval gate _(not started)_

## Phase 6 — Audit log + API endpoints _(not started)_

## Phase 7 — Observability (Prometheus + OpenTelemetry) _(not started)_

## Phase 8 — Evaluation suite _(not started)_

## Phase 9 — End-to-end hardening _(not started)_
