# OpsPilot

**An agentic incident-response platform.** OpsPilot investigates simulated
production incidents end-to-end: an LLM agent reads live signals through MCP
tool servers, reasons about root cause, and proposes remediations — behind
guardrails, human approval, audit logs, structured observability, and
repeatable evaluations.

> **Status: core implementation complete.** The deterministic test suite,
> evaluation suite, lint/type checks, Compose validation, and local remediation
> demo all run without production credentials.

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
                     │ /healthz  /simulate/*  /alerts  /metrics        │
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
                 │ logs, deploys, │   │ restart, deploy,  │  │  JSONL audit    │
                 │ traces (free)  │   │ delete, notify    │  │    log          │
                 └────────────────┘   │ (approval-gated)  │  └─────────────────┘
                                      └───────────────────┘
   Observability across every layer: JSON logs · Prometheus · OpenTelemetry
```

**Investigation flow:**

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
| Local state    | JSON approval store + append-only JSONL audit log          |
| Shared state   | Redis-backed simulator with an in-memory test fallback     |
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
make up                # API, simulated services, Redis, and local observability
```

Open:

- API: <http://localhost:8000> (docs at `/docs`, probe at `/healthz`)
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- Jaeger: <http://localhost:16686>

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

`inject`, `investigate`, `eval`, and `demo` run in deterministic mock mode by
default, so the repository can be evaluated without credentials.

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
| `LOG_FORMAT`      | `json`                   | `json` for machines, `console` for humans  |
| `REQUIRE_APPROVAL_FOR` | rollback, restart, deploy, delete, notify | Approval-gated actions      |

## Repository layout

```
ops-pilot/
├── Makefile                  # install / up / down / test / lint / inject / ...
├── pyproject.toml            # deps, pytest, ruff, mypy, coverage config
├── docker-compose.yml        # API, simulated services, Redis, and observability
├── docker-compose.override.yml  # dev hot-reload
├── Dockerfile                # python:3.12-slim, non-root, healthcheck
├── .env.example              # every env var, no secrets
├── ops/                      # Prometheus, Grafana, OTEL, MCP registry
├── docs/                     # architecture, demo, and threat model
├── RESUME.md                 # resume bullet and interview talking points
├── scenarios/                # simulated incidents (YAML)
├── data/                     # runbooks plus local ignored runtime state
├── src/opspilot/
│   ├── config.py             # typed environment settings
│   ├── logging.py            # JSON structured logging
│   ├── cli.py                # CLI entry point
│   ├── api/                  # FastAPI app factory
│   ├── agent/                # investigation and remediation workflows
│   ├── mcp/                  # MCP server integrations
│   ├── guardrails/           # input, tool, and output policy checks
│   ├── approval/             # human-in-the-loop gate
│   ├── audit/                # append-only audit log
│   ├── llm/                  # OpenAI Responses + mock mode
│   ├── simulator/            # incident injection and shared state
│   ├── evals/                # deterministic evaluation suite
│   └── observability/        # metrics, alerts, and traces
└── tests/                    # pytest suite for every component
```

## Safety

- Simulated incidents only — no connections to real production systems.
- No credentials in the repo; secrets come from the environment.
- `.env` is gitignored and `.dockerignore` keeps it out of images.
- Approval gating and the audit log are structural requirements, not options.

## Roadmap

1. ✅ Foundation — structure, config, Compose, Makefile, tests.
2. ✅ Incident simulator + scenario schema.
3. ✅ MCP servers + typed tool registry.
4. ✅ LLM client with deterministic mock mode + investigation loop.
5. ✅ Guardrails + human approval gate + audit log.
6. ✅ Approval-gated remediation and independent recovery verification.
7. ✅ Prometheus, OpenTelemetry, Grafana, Jaeger, and alerts.
8. ✅ Evaluation suite with scenario scoring.
9. ✅ CI, architecture docs, threat model, demo guide, and resume notes.

## License

MIT — see [`LICENSE`](./LICENSE).
