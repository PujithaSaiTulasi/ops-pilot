# OpsPilot

**An agentic incident-response platform.** OpsPilot investigates simulated
production incidents end-to-end: an LLM agent reads live signals through MCP
tool servers, reasons about root cause, and proposes remediations — behind
guardrails, human approval, audit logs, structured observability, and
repeatable evaluations.

> **Status: simulator phase complete; MCP and agent phases are next.**
> Progress, test runs, and remaining work live in [`BUILD_STATUS.md`](./BUILD_STATUS.md).
> Nothing described here is claimed to work until it appears under "Tests run"
> in that file.

## Principles

- **Read-only vs. side-effecting tools are separated.** Observability tools can
  run freely; anything that mutates state (rollback, restart, deploy, delete,
  notify) passes through an approval gate.
- **Humans approve the dangerous parts.** No rollback, restart, deployment,
  deletion, or external notification happens without explicit human approval.
- **Every action is auditable.** Decisions, tool calls, approvals, and denials
  are recorded in an append-only audit log.
- **Deterministic by default.** Mock LLM mode gives reproducible agent
  behaviour with no API key and no network — CI never needs credentials.
- **No production credentials, ever.** All configuration comes from
  environment variables (`.env.example` documents every variable; `.env` is
  gitignored).

## Architecture

```
                     ┌─────────────────────────────────────────────────┐
                     │            OpsPilot API (FastAPI)              │
                     │     /healthz  /incidents  /approvals  /audit   │
                     └───────────────┬─────────────────────────────────┘
                                     │
        ┌────────────────────────────┼──────────────────────────────┐
        │                            │                              │
┌───────▼────────┐         ┌─────────▼──────────┐         ┌─────────▼─────────┐
│   Incident     │ inject  │    Agent Core      │ request │  Approval Gate    │
│   Simulator    ├────────▶│  (investigation    ├────────▶│ (human-in-the-    │
│  (scenarios/)  │         │   loop + LLM/mock) │  danger │  loop)            │
└────────────────┘         └───┬────────────┬───┘         └─────────┬─────────┘
                               │            │                       │
                    read-only  │            │ side-effecting        │ approved?
                    tools      │            │ tools                 │
                 ┌─────────────▼──┐   ┌─────▼─────────────┐  ┌──────▼──────────┐
                 │ MCP: metrics,  │   │ MCP: rollback,    │  │  Audit Log      │
                 │ logs, deploys, │   │ restart, deploy,  │  │ (PostgreSQL /   │
                 │ traces (free)  │   │ delete, notify    │  │  SQLite)        │
                 └────────────────┘   │ (approval-gated)  │  └─────────────────┘
                                      └───────────────────┘
   Observability across every layer: JSON logs · Prometheus · OpenTelemetry
```

**Investigation flow (planned):**

1. `make inject SCENARIO=bad_deployment` seeds a deterministic incident.
2. `make investigate` runs the agent loop: plan → tool calls → observations.
3. Read-only tools execute freely; side-effecting tools pause for approval.
4. Every step is written to the audit log and emitted as structured logs/traces.
5. `make eval` scores the resulting investigation against the scenario's ground
   truth (root cause, signals cited, remediation correctness).

## Tech stack

| Layer          | Choice                                                    |
| -------------- | --------------------------------------------------------- |
| Runtime        | Python 3.12                                               |
| API            | FastAPI + Uvicorn                                         |
| Schemas        | Pydantic v2 (typed schemas for every tool and payload)    |
| Agent I/O      | Official MCP Python SDK + official OpenAI Python SDK      |
| Storage        | SQLite (default/tests) · PostgreSQL (Compose stack)       |
| Shared state   | Redis (simulator/approval state across processes)         |
| Metrics        | Prometheus + `/metrics`                                   |
| Traces         | OpenTelemetry → local OTLP collector                      |
| Logs           | JSON structured logging (stdlib, one object per line)     |
| Tests          | pytest + pytest-cov                                       |
| Lint/type      | ruff (lint + format) + mypy                               |
| Packaging      | Docker + Docker Compose                                   |

## Quickstart

```bash
cp .env.example .env   # mock mode is ON by default — no API key needed
make install           # Python 3.12 venv + dependencies
make test              # run the test-suite with coverage
make lint              # ruff lint, ruff format check, mypy
make up                # api + postgres + redis + prometheus + otel-collector
```

Open:

- API: <http://localhost:8000> (docs at `/docs`, probe at `/healthz`)
- Prometheus: <http://localhost:9090>

To inject and inspect a deterministic incident locally:

```bash
make inject SCENARIO=bad_deployment
make state
make reset
```

To use a real model instead of mock mode, set `MOCK_LLM=false` and provide
`OPENAI_API_KEY` in `.env` (never commit it).

## Make targets

| Command                          | What it does                                            |
| -------------------------------- | ------------------------------------------------------- |
| `make install`                   | Create `.venv` (Python 3.12) and install `.[dev]`       |
| `make up`                        | Build and start the full Compose stack                  |
| `make down`                      | Stop the stack (volumes preserved)                      |
| `make test`                      | pytest with coverage                                    |
| `make lint`                      | ruff check, ruff format check, mypy                     |
| `make inject SCENARIO=bad_deployment` | Inject a simulated incident                        |
| `make investigate`               | Run the agent investigation loop                        |
| `make eval`                      | Run the evaluation suite                                |
| `make clean`                     | Remove caches/build artifacts (keeps `.venv` and data)  |

> `inject`, `investigate`, and `eval` are wired to the CLI but intentionally
> exit non-zero until their implementation phases land — see `BUILD_STATUS.md`.

## Configuration

All settings are typed in [`src/opspilot/config.py`](src/opspilot/config.py)
and read from environment variables. Every variable is documented in
[`.env.example`](.env.example); tests assert that file stays valid and
secret-free.

Key switches:

| Variable          | Default                  | Purpose                                    |
| ----------------- | ------------------------ | ------------------------------------------ |
| `MOCK_LLM`        | `true`                   | Deterministic agent, no API key/network    |
| `OPENAI_API_KEY`  | *(empty)*                | Only needed when `MOCK_LLM=false`          |
| `DATABASE_URL`    | SQLite file              | Swap to PostgreSQL for the Compose stack   |
| `LOG_FORMAT`      | `json`                   | `json` for machines, `console` for humans  |
| `REQUIRE_APPROVAL_FOR` | rollback, restart, deploy, delete, notify | Approval-gated actions      |

## Repository layout

```
ops-pilot/
├── Makefile                  # install / up / down / test / lint / inject / ...
├── pyproject.toml            # deps, pytest, ruff, mypy, coverage config
├── docker-compose.yml        # base stack: api, db, redis, prometheus, otel
├── docker-compose.override.yml  # dev hot-reload
├── Dockerfile                # python:3.12-slim, non-root, healthcheck
├── .env.example              # every env var, no secrets
├── ops/                      # prometheus + otel-collector configs
├── scenarios/                # simulated incidents (YAML)
├── data/                     # local SQLite state (gitignored)
├── src/opspilot/
│   ├── config.py             # typed environment settings
│   ├── logging.py            # JSON structured logging
│   ├── cli.py                # CLI entry point
│   ├── api/                  # FastAPI app factory
│   ├── agent/                # investigation loop          (planned)
│   ├── mcp/                  # MCP server integrations     (planned)
│   ├── tools/                # read-only vs side-effecting (planned)
│   ├── guardrails/           # budgets and policy checks   (planned)
│   ├── approval/             # human-in-the-loop gate      (planned)
│   ├── audit/                # append-only audit log       (planned)
│   ├── llm/                  # OpenAI SDK + mock mode      (planned)
│   ├── simulator/            # incident injection          (planned)
│   ├── evals/                # evaluation suites           (planned)
│   └── observability/        # metrics + traces            (planned)
└── tests/                    # pytest suite for every component
```

## Safety

- Simulated incidents only — no connections to real production systems.
- No credentials in the repo; secrets come from the environment.
- `.env` is gitignored and `.dockerignore` keeps it out of images.
- Approval gating and the audit log are structural requirements, not options.

## Roadmap

1. ✅ Foundation — structure, config, Compose, Makefile, tests.
2. Incident simulator + scenario schema.
3. MCP servers (read-only observability tools) + typed tool registry.
4. LLM client with deterministic mock mode + investigation agent loop.
5. Guardrails + human approval gate.
6. Audit log (SQLite/PostgreSQL) + API endpoints.
7. Observability: Prometheus metrics + OpenTelemetry traces.
8. Evaluation suite + scenario scoring.
9. End-to-end hardening: docs, seed data, final test pass.

## License

MIT — see [`LICENSE`](./LICENSE).
