# OpsPilot threat model

OpsPilot treats model output, incident text, logs, and runbooks as untrusted
inputs. The local simulator is trusted test infrastructure; the control plane
and MCP servers are not yet hardened for internet exposure.

| Threat | Current control | Remaining limitation |
| --- | --- | --- |
| Prompt injection in a request | Input length limit and injection-pattern rejection | Detection is heuristic and request-focused |
| Prompt injection in evidence | Evidence is kept as structured tool output and is not executable | Production adapters need content classification and provenance rules |
| Unsafe tool arguments | Schema discovery, service allowlist, length/token checks | Production needs per-tenant policy and network allowlists |
| Unauthorized mutation | Tool-level approval validation, exact argument matching, TTL, one-time consumption | Local approval identity is a demo user; no SSO/RBAC |
| Approval replay or retargeting | Consumed status and canonical argument hash | JSON file has no transactional multi-writer locking |
| Unbounded agent loop | LangGraph step limit and tool timeout | Per-step call budget remains future work |
| Sensitive data in audit | Recursive redaction of sensitive keys | Production needs field classification, encryption, retention, and access control |
| Audit tampering | Hash-linked JSONL records and chain verification | Local file is not an append-only production ledger |
| False recovery | Independent simulator-state verification after remediation | No real traffic, latency, SLO window, or rollback health check |
| MCP process compromise | Separate stdio processes and no shell tool exposed to the model | No mTLS, process sandbox, container isolation, or service identity |

The `demo` command auto-approves its own local action so the complete flow can
run unattended. Use the manual approval flow in the demo guide to inspect the
pause/approve/resume boundary.

For production, the next security steps are SSO/RBAC, short-lived credentials,
transactional approval storage, authenticated MCP gateways, restricted
executors, encrypted audit storage, signed images, and adversarial replay tests.
