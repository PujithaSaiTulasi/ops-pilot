# OpsPilot demo

Run everything from the repository root.

```bash
make install
make test
make lint
make eval
```

## Complete local demo

```bash
MOCK_LLM=true REDIS_URL= OTEL_TRACES_EXPORTER=none make demo
```

The demo injects `bad_deployment`, investigates it through MCP, creates an
approval request, approves the request as an explicit local demo action,
executes the simulated rollback, and checks that simulator faults were cleared.
Diagnosis fields come from the fixture's expected answer. This is a workflow
demonstration, not an evaluation of live-model reasoning or live service recovery.

## Manual approval flow

```bash
docker compose up -d redis
make inject SCENARIO=bad_deployment
make remediate INCIDENT=bad_deployment
make approve APPROVAL_ID=APR-...
make resume APPROVAL_ID=APR-...
```

Replace `APR-...` with the ID printed by `remediate`. This multi-command flow
requires Redis on the configured `REDIS_URL`; the memory fallback does not
persist faults across processes. The current remediation workflow supports
`bad_deployment`. To reject its action, use `make reject APPROVAL_ID=APR-...`.

To start the observability stack:

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
