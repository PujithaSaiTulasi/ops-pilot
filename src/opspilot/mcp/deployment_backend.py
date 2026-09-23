"""Deployment history adapter for the simulated repository."""

from __future__ import annotations

from typing import Any

from opspilot.simulator.store import FaultStore


class DeploymentBackend:
    """Expose deterministic deployment metadata and changed files."""

    def __init__(self, store: FaultStore | None = None) -> None:
        self.store = store or FaultStore()

    def active_version(self, service: str) -> str:
        if service == "checkout-api" and self.store.get("bad_deployment"):
            return "1.1.0"
        return "1.0.0"

    def deployments(self) -> list[dict[str, Any]]:
        return [
            {
                "deployment_id": "deploy-001",
                "service": "checkout-api",
                "version": "1.1.0",
                "previous_version": "1.0.0",
                "status": "active" if self.store.get("bad_deployment") else "superseded",
                "deployed_at": "2026-09-22T18:00:00Z",
            },
            {
                "deployment_id": "deploy-000",
                "service": "checkout-api",
                "version": "1.0.0",
                "previous_version": "0.9.0",
                "status": "healthy",
                "deployed_at": "2026-09-20T12:00:00Z",
            },
        ]

    def details(self, deployment_id: str) -> dict[str, Any]:
        for deployment in self.deployments():
            if deployment["deployment_id"] == deployment_id:
                return {**deployment, "changed_files": self.changed_files(deployment_id)}
        raise KeyError(f"unknown deployment: {deployment_id}")

    def changed_files(self, deployment_id: str) -> list[str]:
        if deployment_id == "deploy-001":
            return ["services/checkout/latency.py", "services/checkout/config.py"]
        if deployment_id == "deploy-000":
            return ["services/checkout/routes.py"]
        raise KeyError(f"unknown deployment: {deployment_id}")
