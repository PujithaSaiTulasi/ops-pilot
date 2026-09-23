# Resume and interview notes

## Resume bullets

Built a LangGraph-based incident-response agent with five separately launchable
MCP servers, structured tool calling, deterministic observability fixtures, and
approval-gated remediation for simulated production incidents.

Implemented defense-in-depth safety controls including input and output
guardrails, exact-action approval binding, expiry and one-time consumption,
tool timeouts, redacted hash-chained audit events, and a 15-case evaluation
suite covering workflow quality and unauthorized-action prevention.

## What to explain in interviews

- The LangGraph state moves through model, tool, and final-diagnosis nodes with
  a hard step bound and tool deadlines.
- MCP servers expose typed contracts. The registry can use in-process servers
  for tests or start five independent stdio processes for the portfolio demo.
- The model can recommend a mutation, but it cannot authorize itself. The
  remediation server validates the stored approval again using the exact action
  arguments, target, expiry, and one-time consumption.
- The deterministic mock model makes regression tests reproducible without an
  API key. Its diagnosis is derived from evidence returned by tools; the
  simulator's declared answer is used by evals only as an oracle for checking.
- The simulator is a test backend. Production adapters would connect the same
  interfaces to Prometheus/Loki/Jaeger, Kubernetes/Argo CD, and an incident
  management system.
- Recovery verification is independent of the diagnosis, but currently checks
  simulator state rather than real traffic and SLOs.

## Honest scope statement

This is a portfolio-ready, production-shaped local system—not a production
incident-response service. It demonstrates the architecture and safety
boundaries, while transactional storage, SSO/RBAC, authenticated MCP gateways,
real observability adapters, restricted executors, and live SLO verification
remain the next implementation phase.
