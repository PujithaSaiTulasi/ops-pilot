# OpsPilot architecture

OpsPilot is a local, production-shaped incident-response agent. It deliberately
keeps the evidence and remediation backends deterministic so the workflow can
be demonstrated and evaluated without access to a real production account.

## Request path

```text
simulated alert
      |
      v
LangGraph: model -> MCP tools -> model -> diagnosis
      |
      v
policy and approval gate
      |
      v
approval-bound remediation MCP tool
      |
      v
independent simulator recovery check + audit event
```

The investigation graph is implemented in
`src/opspilot/agent/runtime.py`. Its state contains the incident, user request,
observations, model decisions, tool events, and final diagnosis. The graph has
three explicit nodes:

| Node | Responsibility |
| --- | --- |
| `model` | Ask the deterministic mock model or the optional Responses adapter what to do next |
| `tool` | Validate the structured call, enforce timeout and approval policy, then call MCP |
| `finalize` | Build an evidence-backed typed diagnosis and apply output guardrails |

The graph is bounded by `MAX_INVESTIGATION_STEPS`; tool calls also have a
`TOOL_TIMEOUT_SECONDS` deadline.

## MCP boundary

`MCPToolRegistry` supports two transports:

- `in_process`: server objects are used directly for fast unit tests.
- `stdio`: the manifest in `ops/mcp/servers.json` starts five independent MCP
  child processes using the official Python SDK client.

The servers are:

| Server | Purpose | Mutation policy |
| --- | --- | --- |
| Observability | Metrics, logs, alerts, traces, baselines | Read-only |
| Deployments | Versions, deployment history, changed files | Read-only |
| Runbooks | Local runbook and incident guidance search | Read-only |
| Remediation | Rollback, restart, and recovery verification | Mutations require approval |
| Incidents | Local incident record operations | Writes require approval |

Each server exposes typed schemas discovered at runtime. The model receives
those schemas for tool calling; it does not receive shell access.

## Approval and guardrails

The agent applies request, argument, and diagnosis guardrails before or after
model interaction. Mutating MCP tools enforce the policy again at the server
boundary. An approval is bound to:

- the exact action name;
- the exact canonical tool arguments;
- the incident context;
- an expiry time; and
- one-time consumption.

This means a valid approval for `deploy-001` cannot be reused for `deploy-000`
or for another action. The local JSON store is intentionally a teaching
implementation; production would replace it with transactional storage and
identity-aware RBAC.

## Audit trail

`AuditLogger` writes redacted JSONL events containing an event ID, timestamp,
previous hash, and record hash. `verify_chain()` detects edits or reordered
records. This is useful for local demonstrations and tests; a production
deployment should write to an access-controlled, append-only store with
retention and multi-writer semantics.

## Simulator and future adapters

The simulator stores active faults in Redis and maintains a versioned JSON state
file as a durable mirror. Mutations write the file first and then refresh Redis;
if Redis is unavailable, later reads continue from the file, and when Redis
recovers the newest revision is copied back into it. This prevents an empty or
stale Redis instance from silently hiding or resurrecting a local incident.
Processes must use the same Redis instance and state-file path. The
observability server currently reads simulator state. The intended adapter seams are:

- `ObservabilityBackend` -> Prometheus, Loki, Tempo/Jaeger, and Alertmanager;
- `DeploymentBackend` -> Kubernetes, Argo CD, or a deployment API;
- `IncidentBackend` -> PagerDuty, Jira, or an incident platform;
- `RemediationBackend` -> a restricted executor with short-lived credentials.

The simulator implementations remain the deterministic test doubles for those
future integrations.

## Evaluation boundary

`evals/cases.json` contains fifteen cases. They measure evidence-derived
diagnosis fields, tool selection, injection blocking, unsupported arguments,
approval rejection, exact-target mismatch, expiry, audit integrity, MCP schema
contracts, bounded execution, and approved recovery. `make eval` calculates
case pass rate and safety metrics from the results. These are regression and
policy metrics, not claims of general LLM accuracy.
