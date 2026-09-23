# Incident scenarios

This directory holds **simulated** production incidents used by the incident
injector (`make inject SCENARIO=bad_deployment`).

Scenarios are plain YAML files named `<scenario>.yaml`. Each scenario describes:

- a stable scenario id (e.g. `bad_deployment`)
- the signal fingerprints it produces (metric deltas, log patterns, trace errors)
- the expected root cause and remediation
- which side-effecting actions (if any) a correct investigation should propose

> **Status:** scenario schema and loading are not implemented yet (see
> `BUILD_STATUS.md`). This README documents the intended contract.
