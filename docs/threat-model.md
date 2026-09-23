# OpsPilot threat model

## Assets

- Incident evidence and operational logs.
- Deployment metadata.
- Approval records.
- Simulator state and audit history.
- Model inputs and tool outputs.

## Threats and controls

| Threat | Control |
| --- | --- |
| Prompt injection in a log or runbook | Treat external text as evidence; structured tool schemas; input guardrail |
| Unauthorized rollback or restart | Side-effecting tool classification; approval store; approval id required |
| Tool argument escaping | Pydantic/MCP schemas, service allowlist, path and shell-token rejection |
| Secret leakage in logs | Environment-only secrets and recursive audit redaction |
| Excessive investigation loop | Maximum investigation steps and tool-call budgets |
| Incorrect diagnosis | Evidence requirement, confidence validation, replayable evals |
| False recovery claim | Independent verification after remediation |
| Remote MCP compromise | Local-only servers in the portfolio demo; allowlisted registry; no production credentials |
| Data loss in the demo | Simulator only; audit and approval data are local and ignored by Git |

## Residual risk

Guardrails reduce risk but do not prove that an LLM is safe in every context.
The production version would require identity-aware authorization, secret
management, network isolation, rate limits, durable audit storage, and a formal
change-management integration.
