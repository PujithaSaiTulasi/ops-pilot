# Resume and interview notes

## Resume bullet

Built OpsPilot, an agentic incident-response platform using Python, FastAPI,
MCP servers, OpenAI tool calling, structured guardrails, approval-gated
remediation, OpenTelemetry, and deterministic evaluations; replayed 10 incident
and safety cases with a 100% pass rate and 0% unauthorized-action rate.

## What to discuss in interviews

- Why read-only evidence tools and side-effecting tools are separate.
- How MCP tool discovery differs from directly wiring one function into an app.
- Why logs are untrusted evidence and must not become instructions.
- Why human approval is required before rollback or restart.
- Why recovery is verified independently instead of trusting the remediation result.
- How mock mode makes agent tests deterministic and CI-safe.
- Which evaluation metrics matter: root-cause accuracy, tool selection, evidence,
  approval compliance, and prompt-injection resistance.
- How the local simulator can later be replaced with production adapters without
  changing the agent policy layer.
