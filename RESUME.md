# Resume and interview notes

## Resume bullet

Built a local incident-response prototype with Python/FastAPI, five MCP server
modules, a bounded tool-calling workflow, a manual rollback approval flow,
JSONL audit events, Prometheus/OpenTelemetry integration, and ten deterministic
workflow and safety regression cases with GitHub Actions verification.

## What to explain in interviews

- How simulator faults provide repeatable incident demonstrations.
- How the agent discovers typed tool schemas from MCP server objects.
- The difference between this in-process SDK dispatcher and a networked MCP client.
- How the checkout rollback pauses for approval and resumes from a stored decision.
- Why a workflow gate also needs tool-level authorization before production use.
- Why simulator-state verification differs from measuring real service recovery.
- How mock mode makes regression checks reproducible without API credentials.

## Claims to avoid

The final diagnosis currently uses the scenario's expected answer, even when the
live adapter selects the tools. Do not describe the eval pass rate as measured
LLM root-cause accuracy. An earlier unauthorized-action-rate field was a constant
and has been removed; do not use it as a resume metric. The model adapter is
present, but the offline checks do not validate live-model behavior.

Describe this as a working local prototype. Future work includes live telemetry
adapters, diagnoses independent of scenario answers, authorization at each
mutating tool, and evaluations on previously unseen incidents.
