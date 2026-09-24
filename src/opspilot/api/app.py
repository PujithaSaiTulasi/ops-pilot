"""FastAPI application factory for the local OpsPilot control plane."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from prometheus_client.registry import CollectorRegistry
from starlette.responses import Response

from opspilot import __version__
from opspilot.config import Settings, get_settings
from opspilot.logging import configure_logging
from opspilot.observability.alerts import AlertStore
from opspilot.simulator.catalog import inject_scenario, load_scenario
from opspilot.simulator.models import InjectRequest
from opspilot.simulator.store import FaultStore


def create_app(settings: Settings | None = None, fault_store: FaultStore | None = None) -> FastAPI:
    """Create the OpsPilot ASGI application."""
    app_settings = settings or get_settings()
    configure_logging(level=app_settings.log_level, fmt=app_settings.log_format)

    store = fault_store or FaultStore(app_settings.redis_url, app_settings.simulator_state_path)
    registry = CollectorRegistry()
    alert_store = AlertStore()
    inject_counter = Counter(
        "opspilot_simulator_injections_total",
        "Number of simulator scenarios activated.",
        ["scenario"],
        registry=registry,
    )
    application = FastAPI(
        title=app_settings.app_name,
        version=__version__,
        description="Agentic incident-response platform control plane.",
    )
    application.state.fault_store = store
    application.state.metrics_registry = registry
    application.state.alert_store = alert_store

    @application.get("/healthz", tags=["ops"], summary="Liveness probe")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/version", tags=["ops"], summary="Build version and environment")
    def version() -> dict[str, str]:
        return {"version": __version__, "environment": app_settings.environment}

    @application.get("/metrics", tags=["ops"], summary="Prometheus metrics")
    def metrics() -> Response:
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @application.get("/simulate/scenarios", tags=["simulator"])
    def scenarios() -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for scenario_id in (
            "bad_deployment",
            "payment_timeout",
            "inventory_errors",
            "database_connection_exhaustion",
            "memory_pressure",
            "dependency_failure",
        ):
            values.append(load_scenario(scenario_id, app_settings.scenario_dir).model_dump())
        return values

    @application.post("/simulate/inject", tags=["simulator"])
    def inject(request: InjectRequest) -> dict[str, Any]:
        try:
            scenario = inject_scenario(request.scenario, store, app_settings.scenario_dir)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        inject_counter.labels(request.scenario).inc()
        return {"status": "active", "scenario": scenario.model_dump(mode="json")}

    @application.post("/simulate/reset", tags=["simulator"])
    def reset() -> dict[str, str]:
        store.clear_all()
        return {"status": "reset"}

    @application.get("/simulate/state", tags=["simulator"])
    def state() -> dict[str, Any]:
        return {"active_faults": [fault.model_dump(mode="json") for fault in store.active()]}

    @application.get("/alerts", tags=["observability"])
    def alerts() -> dict[str, Any]:
        generated = [
            {
                "status": "firing",
                "labels": {
                    "alertname": fault.scenario,
                    "service": fault.details.get("service", "unknown"),
                },
                "annotations": {"summary": fault.scenario.replace("_", " ")},
            }
            for fault in store.active()
        ]
        return {"active": generated, "received": alert_store.recent()}

    @application.post("/alerts/webhook", tags=["observability"])
    def alert_webhook(payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "recorded", "alert": alert_store.record(payload)}

    return application
