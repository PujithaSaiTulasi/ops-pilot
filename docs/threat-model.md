# OpsPilot threat model

This prototype assumes a trusted developer and a local simulator. Its HTTP and
MCP entry points are not designed for untrusted or production access.

| Area | Implemented behavior | Remaining limitation |
| --- | --- | --- |
| Input | Rejects selected injection phrases and oversized user requests | Does not inspect every log/runbook tool result for injection |
| Tool arguments | Agent checks service names, string lengths, and selected unsafe tokens | Direct MCP calls bypass the agent's checks |
| Approval | Workflow checks a persisted approval decision before rollback | Direct tools accept any nonempty ID; no identity, expiry, or replay enforcement |
| Investigation limits | Maximum iteration count | Tool timeout and per-step budget settings are currently unused |
| Audit | Appends selected events to JSONL and redacts sensitive dictionary fields | Not tamper-proof, complete, or safe for concurrent writers; not all embedded secrets are detected |
| Diagnosis | Requires evidence entries and flags risky recommendations | Root cause is copied from scenario ground truth, not independently inferred |
| Recovery | Separate tool reads remaining simulator faults | No live health/latency verification and no service-specific fault filter |
| Storage | Runtime records are excluded from Git and Docker images | Local files have no access-control or multi-writer transaction layer |

The `demo` command explicitly auto-approves its own local action. Use the manual
approval sequence in the demo guide to inspect the pause/approve/resume path.

Production adapters would require authenticated tool-level authorization tied to
the exact action, approval expiry and consumption, protected audit storage,
untrusted-evidence handling, live telemetry-based diagnosis and verification,
and regression cases measuring those properties. Existing eval pass rates should
not be described as proof of production safety.
