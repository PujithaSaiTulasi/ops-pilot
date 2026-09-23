# OpsPilot demo

Run everything from the repository root.

```bash
cp .env.example .env
make install
make test
make lint
make eval
```

## Complete local demo

```bash
make demo
```

The demo injects `bad_deployment`, investigates it through MCP, creates an
approval request, approves the request as an explicit local demo action,
executes the simulated rollback, and independently verifies recovery.

## Manual approval flow

```bash
make inject SCENARIO=bad_deployment
make remediate INCIDENT=bad_deployment
make approve APPROVAL_ID=APR-...
make resume APPROVAL_ID=APR-...
```

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
