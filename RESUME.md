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

## Challenges and architectural decisions

- **Redis and disk storage:** “I found a problem in the way the simulator saved
  its active incidents. Redis was the main place we used, and the JSON file on
  disk was only used when Redis was unavailable. That meant the two copies could
  become different. For example, if I cleared an incident while Redis was down,
  the file would show that it was cleared, but Redis could still contain the old
  incident. When Redis came back, that old incident might appear again. The
  opposite could happen too: Redis might be empty even though the disk file
  still had an active incident.

  I fixed this by treating the disk file as a proper backup copy instead of a
  last-minute fallback. Every change is saved to the file first, and then copied
  to Redis. Each copy has a revision number, so when the application reads the
  state it can tell which copy is newer and update the older one. The containers
  also use the same persistent file, so they all see the same backup. This makes
  Redis recovery predictable and prevents incidents from disappearing or coming
  back because the two copies disagreed. It is still a simple local solution;
  handling many simultaneous writers would need a transactional database or a
  stronger locking mechanism.”

## Honest scope statement

This is a portfolio-ready, production-shaped local system—not a production
incident-response service. It demonstrates the architecture and safety
boundaries, while transactional storage, SSO/RBAC, authenticated MCP gateways,
real observability adapters, restricted executors, and live SLO verification
remain the next implementation phase.
