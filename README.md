# OpsPilot

A local incident-response prototype for learning MCP tools, bounded agent
workflows, approval gates, and evaluation. Three small FastAPI services simulate
checkout, payment, and inventory incidents. No production integration is required.

## What works today

- Six scenario fixtures and fault injection through the CLI or HTTP API.
- Five MCP server modules exposing simulator evidence, deployment fixtures,
  runbooks, remediation tools, and local incident records.
- A bounded investigation loop with a scripted mock model by default and an
  optional OpenAI Responses adapter for tool selection.
- A manual approval workflow for the `bad_deployment` rollback demo, with a
  separate simulator-state recovery check and a JSONL audit trail.
- Ten deterministic regression cases, pytest, lint/type checks, and GitHub CI.
- Docker Compose configuration for services, Redis, Prometheus, Grafana,
  OpenTelemetry Collector, and Jaeger.

## Current limits

This is a prototype, not a production incident-response system. The investigation
currently fills the final diagnosis from the selected scenario's expected answer,
including in live-model mode. MCP evidence is generated from simulator state;
it does not query Prometheus or Jaeger. A passing evaluation therefore measures
fixture/workflow consistency, not independent LLM diagnosis accuracy.

Approval enforcement is in the remediation workflow. The low-level remediation
tools only require a nonempty approval ID and do not authenticate it themselves.
Recovery checks whether simulator faults remain; it does not measure post-fix
traffic or latency. The full remediation workflow supports `bad_deployment` only.
Deploy, delete, and notification tools are not implemented.

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

The last command runs entirely within one process, injects the checkout fault,
automatically approves the local demo action, and checks the resulting simulator
state. It requires neither Docker nor an API key. It is not the manual approval
path.

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

Redis shares faults across processes. Without a reachable Redis server, faults
fall back to memory and disappear when a CLI process exits. Approvals and audit
events are local files under `data/`.

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
| `REDIS_URL` | Shared simulator state; empty means process-local memory |
| `MAX_INVESTIGATION_STEPS` | Enforced investigation loop limit |
| `APPROVAL_STORE_PATH` | Local JSON approval records |
| `AUDIT_LOG_PATH` | Local JSONL event log |
| `OTEL_TRACES_EXPORTER` | Set to `none` to disable trace export |

Compose uses its internal Redis and collector hostnames; the sample `.env`
localhost addresses are for commands running on your host. Several settings are
still reserved and do not enforce behavior, as marked in `.env.example`.

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
