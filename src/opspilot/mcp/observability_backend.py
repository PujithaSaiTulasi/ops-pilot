"""Deterministic observability adapter used by the local MCP server."""

from __future__ import annotations

from typing import Any

from opspilot.simulator.store import FaultStore


class ObservabilityBackend:
    """Expose metrics, logs, alerts, and traces from simulator state."""

    def __init__(self, store: FaultStore | None = None) -> None:
        self.store = store or FaultStore()

    def metrics(self, service: str, window_minutes: int = 5) -> dict[str, Any]:
        faults = {fault.scenario: fault for fault in self.store.active()}
        result: dict[str, Any] = {
            "service": service,
            "window_minutes": window_minutes,
            "request_rate_per_second": 12.0,
            "p95_latency_ms": 120.0,
            "error_rate": 0.0,
            "version": "1.0.0",
        }
        if "bad_deployment" in faults and service == "checkout-api":
            result.update(p95_latency_ms=750.0, error_rate=0.08, version="1.1.0")
        if "payment_timeout" in faults and service == "payment-service":
            result.update(p95_latency_ms=3000.0, error_rate=1.0)
        if "inventory_errors" in faults and service == "inventory-service":
            result.update(p95_latency_ms=500.0, error_rate=1.0)
        if "database_connection_exhaustion" in faults and service == "checkout-api":
            result.update(error_rate=1.0, database_pool_usage=1.0)
        if "memory_pressure" in faults and service == "checkout-api":
            result.update(p95_latency_ms=400.0, memory_usage=0.95)
        return result

    def logs(
        self, query: str = "", service: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for fault in self.store.active():
            affected = str(fault.details.get("service", "checkout-api"))
            if service and service != affected:
                continue
            records.append(
                {
                    "service": affected,
                    "level": "ERROR" if fault.scenario != "bad_deployment" else "WARN",
                    "message": f"simulated incident: {fault.scenario}",
                    "scenario": fault.scenario,
                }
            )
        if query:
            records = [record for record in records if query.lower() in str(record).lower()]
        return records[: max(1, min(limit, 100))]

    def alerts(self) -> list[dict[str, Any]]:
        return [
            {
                "status": "firing",
                "alertname": fault.scenario,
                "service": fault.details.get("service", "unknown"),
                "summary": fault.scenario.replace("_", " "),
            }
            for fault in self.store.active()
        ]

    def trace_summary(
        self, trace_id: str | None = None, service: str = "checkout-api"
    ) -> dict[str, Any]:
        spans = [{"service": service, "duration_ms": self.metrics(service)["p95_latency_ms"]}]
        if service == "checkout-api":
            spans.extend(
                [
                    {"service": "payment-service", "duration_ms": 25.0},
                    {"service": "inventory-service", "duration_ms": 18.0},
                ]
            )
        return {"trace_id": trace_id or "simulated-trace", "service": service, "spans": spans}

    def baseline(self, service: str) -> dict[str, Any]:
        current = self.metrics(service)
        baseline = {"p95_latency_ms": 120.0, "error_rate": 0.0}
        return {
            "service": service,
            "current": current,
            "baseline": baseline,
            "delta": {
                "p95_latency_ms": current["p95_latency_ms"] - baseline["p95_latency_ms"],
                "error_rate": current["error_rate"] - baseline["error_rate"],
            },
        }
