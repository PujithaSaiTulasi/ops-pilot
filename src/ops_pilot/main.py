"""Placeholder FastAPI application (foundation phase).

Only health endpoints exist for now — incident-response logic arrives in
later phases (see BUILD_STATUS.md).
"""

from typing import Any

from fastapi import FastAPI

from ops_pilot import __version__

app = FastAPI(
    title="OpsPilot",
    version=__version__,
    description="Agentic incident-response platform (foundation scaffold).",
)


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, Any]:
    """Liveness probe."""
    return {"status": "ok", "service": "opspilot", "version": __version__}


@app.get("/readyz", tags=["health"])
def readyz() -> dict[str, Any]:
    """Readiness probe (deep dependency checks arrive in later phases)."""
    return {"status": "ready", "checks": {}}
