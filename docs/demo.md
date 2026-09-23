# OpsPilot demo

Run everything from the repository root.

```bash
make install
make test
make lint
make eval
```

## In-process demo

```bash
MOCK_LLM=true REDIS_URL= OTEL_TRACES_EXPORTER=none make demo
```

This runs the LangGraph investigation, discovers the MCP contracts, gathers
simulated evidence, creates an approval, auto-approves the local demo action,
executes the simulated rollback, and verifies recovery. The diagnosis is
derived from the collected evidence by the deterministic offline model.

## Separate MCP server demo

```bash
MCP_TRANSPORT=stdio REDIS_URL= OTEL_TRACES_EXPORTER=none make mcp-discover
MCP_TRANSPORT=stdio REDIS_URL= OTEL_TRACES_EXPORTER=none make demo
```

The first command starts five independent MCP child processes and prints the
discovered tools and approval metadata. The second runs the end-to-end workflow
over those processes. When Redis is empty, `SIMULATOR_STATE_PATH` is the shared
fallback used by the parent and child processes.

## Manual approval flow

```bash
docker compose up -d redis
make inject SCENARIO=bad_deployment
make remediate INCIDENT=bad_deployment
make approve APPROVAL_ID=APR-...
make resume APPROVAL_ID=APR-...
```

Replace `APR-...` with the ID printed by `remediate`. The mutating MCP tool
validates that the approval is approved, unexpired, intended for the exact
deployment, and unused. To reject the action, use `make reject APPROVAL_ID=APR-...`.

## Local service stack

```bash
make up
```

Then open:

- API: <http://localhost:8000/docs>
- Checkout: <http://localhost:8001/health>
- Payment: <http://localhost:8002/health>
- Inventory: <http://localhost:8003/health>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- Jaeger: <http://localhost:16686>

The local services emit Prometheus metrics and OpenTelemetry traces. The
current MCP observability backend remains simulator-backed; replacing it with
Prometheus/Loki/Jaeger adapters is the next production-oriented phase.
