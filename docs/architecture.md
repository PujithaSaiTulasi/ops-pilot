# OpsPilot architecture

OpsPilot has a local simulator, a CLI investigation workflow, and a separate
observability stack. They share scenario state, but the agent does not yet read
live telemetry from the observability stack.

## Investigation and remediation

1. The CLI or `/simulate/inject` activates a scenario in Redis, or in process-local
   memory when Redis is unavailable.
2. `MCPToolRegistry` constructs five server objects in-process, discovers their
   schemas, and calls their SDK tool methods. `ops/mcp/servers.json` describes
   standalone stdio entry points; the agent does not load that file or connect to
   external MCP processes.
3. The mock model follows a scripted evidence-gathering sequence. The optional
   Responses adapter selects tools using a model. Both modes currently construct
   the final diagnosis from scenario ground truth rather than model reasoning.
4. `RemediationWorkflow` prepares a checkout rollback and persists a pending
   approval. It checks the stored decision before invoking the rollback tool.
   This workflow is specific to `bad_deployment`.
5. The rollback clears the simulated deployment fault. A separate verification
   tool checks whether any simulator faults remain; it does not probe service
   traffic, deployment versions, or latency.
6. Audit events append to JSONL; approvals and incident records use JSON files.
   These stores have no database backend or multi-writer locking.

## MCP modules

| Server | Tools |
| --- | --- |
| Observability | Fixture metrics, logs, alerts, trace summaries, baseline comparison |
| Deployments | Fixture versions, deployment history, changed files |
| Runbooks | Local runbooks and past-incident guidance |
| Remediation | Rollback plan, simulated rollback/restart, simulator-state verification |
| Incidents | Read/create/update local records and add comments |

The agent classifies read-only and mutating tools. Direct calls to server objects
do not pass through agent guardrails. In particular, remediation tools only check
that an approval ID is present; they do not validate a stored approval themselves.

## Services and telemetry

The checkout service calls payment and inventory over HTTP. The services emit
Prometheus request metrics and OpenTelemetry spans; Prometheus scrapes them and
the collector exports spans to local Jaeger. Grafana uses the Prometheus data.
MCP observability tools instead synthesize evidence from `FaultStore`.

The control API manages simulator state and receives alert payloads. It has no
investigation, approval, or audit-history HTTP endpoints. Alert receipt does not
launch the agent, and automatic Prometheus-to-webhook delivery is not configured.

## Evaluation boundaries

The ten regression cases test fixture diagnosis fields, selected tools, presence
of evidence, request-text rejection, unsupported services, rejected approval
records, and loop termination. These are deterministic workflow tests. They do
not measure diagnosis accuracy on unseen incidents or an unauthorized-action
rate. The result JSON records the mock mode and scenario-fixture diagnosis source.
