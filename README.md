# OpsPilot

A portfolio-ready local incident-response agent for learning LangGraph, MCP
servers, structured tool calling, approval gates, guardrails, auditability, and
evaluation. Three small FastAPI services simulate checkout, payment, and
inventory incidents; the same MCP contracts can later be backed by real SRE
systems.

## What works today

- Six scenario fixtures and fault injection through the CLI or HTTP API.
- Five separately launchable MCP servers exposing simulator evidence,
  deployment fixtures, runbooks, remediation tools, and local incident records.
- A real LangGraph state graph with model, tool, and final-diagnosis nodes. The
  default mock model is deterministic; an optional OpenAI Responses adapter can
  select tools through the same discovered schemas.
- Structured MCP tool schemas and a selectable `stdio` transport. Unit tests
  use the in-process transport; `make mcp-discover` starts five child servers.
- Approval records bound to the exact action arguments, target, TTL, and
  one-time consumption, with low-level MCP enforcement on mutating tools.
- Hash-chained, redacted JSONL audit events and simulator-state sharing across
  separate MCP processes.
- Fifteen deterministic regression and safety cases covering diagnosis,
  injection blocking, approval misuse, expiry, audit integrity, MCP contracts,
  bounded execution, and approved recovery.
- Docker Compose configuration for services, Redis, Prometheus, Grafana,
  OpenTelemetry Collector, and Jaeger.

## Current limits

This is still a local portfolio system, not a production incident-response
service. The evidence backend is simulator-backed and the default model is a
deterministic offline model; live Prometheus, Loki, Jaeger, Kubernetes, and
identity integrations are intentionally left as adapter work. Recovery checks
the simulator state rather than a real SLO observation window. File-backed
approvals and audit logs are suitable for demos and tests, not multi-writer
production deployments.

The safety boundary is real inside the prototype: direct mutating MCP calls
validate the stored approval, exact arguments, expiry, and one-time use. The
evaluation metrics are calculated from traces, but they measure deterministic
fixtures and policy behavior—not general LLM accuracy.

See [architecture](docs/architecture.md) and the [threat model](docs/threat-model.md)
for the implemented boundaries and remaining work.

## Quickstart

Run from the repository root with Python 3.12:

```bash
make install
make test
make lint
make eval
MOCK_LLM=true REDIS_URL= OTEL_TRACES_EXPORTER=none make demo
```

The last command runs the local graph, injects the checkout fault, automatically
approves the local demo action, and checks the resulting simulator state. It
requires neither Docker nor an API key. It is not the manual approval path.

To see the separate MCP server processes and their schemas:

```bash
MCP_TRANSPORT=stdio REDIS_URL= OTEL_TRACES_EXPORTER=none make mcp-discover
MCP_TRANSPORT=stdio REDIS_URL= OTEL_TRACES_EXPORTER=none make demo
```

Optionally copy `.env.example` to `.env` for local settings. Keep an existing
`.env` and any credentials private; both Git and the Docker build ignore it.

For manual approval across separate CLI commands, start Redis first:

```bash
docker compose up -d redis
make inject SCENARIO=bad_deployment
make remediate INCIDENT=bad_deployment
# Replace APR-... below with the approval ID returned by remediate.
make approve APPROVAL_ID=APR-...
make resume APPROVAL_ID=APR-...
```

Redis shares faults across processes. Without a reachable Redis server, the
configured `SIMULATOR_STATE_PATH` JSON file shares faults across the local MCP
processes. Approvals and audit events are local files under `data/`.

## Local service stack

```bash
make up
```

| Service | Local address |
| --- | --- |
| API documentation | <http://localhost:8000/docs> |
| Checkout health | <http://localhost:8001/health> |
| Payment health | <http://localhost:8002/health> |
| Inventory health | <http://localhost:8003/health> |
| Prometheus | <http://localhost:9090> |
| Grafana | <http://localhost:3000> |
| Jaeger | <http://localhost:16686> |

The control API exposes `/healthz`, `/version`, `/metrics`, `/simulate/scenarios`,
`/simulate/inject`, `/simulate/reset`, `/simulate/state`, `/alerts`, and
`/alerts/webhook`. Receiving an alert records it; it does not start an investigation.
The agent and approvals are currently operated through the CLI.

Generate service traffic with `curl http://localhost:8001/checkout`. Prometheus
scrapes actual service metrics and the collector forwards service traces to
Jaeger. These dashboards are separate from the agent's fixture-based evidence.
See the [demo guide](docs/demo.md) for more commands.

## Configuration

Settings are declared in [config.py](src/opspilot/config.py); example environment
values are in [.env.example](.env.example).

| Setting | Purpose |
| --- | --- |
| `MOCK_LLM` | Defaults to `true`; uses the scripted model |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Needed for live tool selection; live calls can incur costs |
| `MCP_TRANSPORT` | `in_process` for tests or `stdio` for separate MCP child processes |
| `MCP_SERVERS_PATH` | MCP server process manifest |
| `REDIS_URL` | Shared simulator state; empty uses the configured JSON state file |
| `SIMULATOR_STATE_PATH` | Shared fallback state file for separate local processes |
| `MAX_INVESTIGATION_STEPS` | Enforced investigation loop limit |
| `APPROVAL_STORE_PATH` | Local JSON approval records with TTL and consumption state |
| `AUDIT_LOG_PATH` | Redacted, hash-chained local JSONL event log |
| `OTEL_TRACES_EXPORTER` | Set to `none` to disable trace export |

Compose uses its internal Redis and collector hostnames; the sample `.env`
localhost addresses are for commands running on your host. The per-step tool
count and metrics toggle remain intentionally reserved for future work.

## Repository layout

```text
src/opspilot/        Python package: API, services, simulator, MCP, agent,
                    approvals, guardrails, audit, model adapters, evaluations
tests/              Automated tests
scenarios/          YAML incident fixtures
data/runbooks/      Checked-in runbooks (runtime state in data/ is ignored)
evals/cases.json     Regression cases; generated results are ignored
ops/                Prometheus, Grafana, collector, and MCP launch configuration
docs/               Architecture, demo instructions, and threat model
.github/workflows/  CI verification
```

`make help` lists available commands. `make down` stops the stack while preserving
volumes. `make eval` fails below an 80% case pass rate. Use [RESUME.md](RESUME.md)
for an accurate project description and interview talking points.

MIT license; see [LICENSE](LICENSE).
