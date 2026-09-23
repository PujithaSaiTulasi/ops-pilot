# BUILD_STATUS

Single source of truth for what is built, what has been tested, and what is left.
**Nothing is considered done until its tests pass.**

---

## Phase 0 — Foundation ✅ (complete)

### Completed

- [x] Repository inspection (empty git repo, no prior files to preserve)
- [x] `README.md` — overview, architecture sketch, quickstart, tool policy
- [x] `pyproject.toml` — Python 3.12, runtime + dev deps, pytest & ruff config
- [x] `.env.example` — every config knob documented; `.env` gitignored
- [x] `.gitignore` — `.env`, venvs, caches, local DBs, logs
- [x] `Makefile` — `install`, `up`, `down`, `test`, `lint`, `inject SCENARIO=…`,
      `investigate`, `eval`, `clean`
- [x] `Dockerfile` — Python 3.12-slim, non-root user, healthcheck
- [x] `docker-compose.yml` — api, postgres, redis, prometheus, otel-collector
      (healthchecked dependencies, no hardcoded secrets)
- [x] `docker-compose.override.yml` — local dev reload + source mount
- [x] `prometheus/prometheus.yml`, `otelcol/config.yaml`
- [x] Typed settings module (`src/ops_pilot/config.py`), env-var driven, mock
      mode default (`MOCK_LLM=true`, no API key required)
- [x] Placeholder FastAPI app (`src/ops_pilot/main.py`) with `/healthz`, `/readyz`
- [x] Honest failing placeholder for `make eval` (`ops_pilot.evals`, exit 2)

### Tests run

- `make install` — package + dev extras installed into `.venv` (Python 3.12)
- `make test` — **10 passed** (`tests/test_foundation.py`):
  settings defaults & env parsing, settings singleton,
  `.env.example` completeness vs. settings fields, `.env` gitignored,
  no hardcoded API keys anywhere in the repo, required Makefile targets,
  compose services + no inline secrets, pyproject stack assertions,
  health endpoints
- `make lint` — ruff check + format check pass

### Remaining (later phases)

- Phase 1: package skeleton (schemas, tools, storage, logging) + `make up` smoke test
- Phase 2: MCP servers (read-only vs side-effecting tools, typed schemas)
- Phase 3: agent loop (OpenAI SDK + deterministic mock mode)
- Phase 4: guardrails, human approval workflow, audit log
- Phase 5: simulator (`make inject` / `make investigate`), metrics/traces/JSON logs
- Phase 6: evaluation harness (`make eval`) + integration tests
- Phase 7: docs polish, full CI pass

---

_Legend: ✅ complete · 🟡 in progress · ⬜ not started_
