"""Common service application factory for the simulated production system."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from prometheus_client.registry import CollectorRegistry

from opspilot.config import Settings
from opspilot.observability.tracing import configure_tracing
from opspilot.simulator.store import FaultStore

LOGGER = logging.getLogger("opspilot.simulator.service")


class ServiceMetrics:
    """Per-process Prometheus metrics to keep tests isolated."""

    def __init__(self, service_name: str) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "opspilot_service_requests_total",
            "Requests handled by a simulated service.",
            ["service", "route", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "opspilot_service_request_duration_seconds",
            "Request duration for a simulated service.",
            ["service", "route"],
            registry=self.registry,
        )
        self.service_name = service_name


def create_service_app(
    service_name: str,
    route: str,
    version: str,
    settings: Settings | None = None,
    store: FaultStore | None = None,
    downstreams: dict[str, str] | None = None,
) -> FastAPI:
    """Create a small service with health, metrics, and fault-aware traffic."""
    app_settings = settings or Settings()
    configure_tracing(app_settings, service_name)
    tracer = trace.get_tracer(f"opspilot.simulator.{service_name}")
    fault_store = store or FaultStore(app_settings.redis_url, app_settings.simulator_state_path)
    metrics = ServiceMetrics(service_name)
    app = FastAPI(title=service_name)
    app.state.fault_store = fault_store
    app.state.metrics = metrics
    app.state.service_name = service_name
    app.state.version = version

    @app.middleware("http")
    async def observe(request: Request, call_next: Callable[[Request], Any]) -> Response:
        started = time.perf_counter()
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        status = 500
        try:
            with tracer.start_as_current_span(f"{service_name} {request.url.path}") as span:
                span.set_attribute("service.name", service_name)
                span.set_attribute("http.route", request.url.path)
                response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request_id
            response.headers["x-service-version"] = app.state.version
            return response
        finally:
            duration = time.perf_counter() - started
            metrics.requests.labels(service_name, request.url.path, str(status)).inc()
            metrics.latency.labels(service_name, request.url.path).observe(duration)
            LOGGER.info(
                "service request",
                extra={
                    "service": service_name,
                    "route": request.url.path,
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id,
                    "version": app.state.version,
                },
            )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": service_name, "version": app.state.version}

    @app.get("/metrics")
    def metrics_endpoint() -> Response:
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/faults")
    def faults() -> list[dict[str, Any]]:
        return [fault.model_dump(mode="json") for fault in fault_store.active()]

    @app.get(route)
    async def traffic() -> dict[str, Any]:
        active = {fault.scenario: fault for fault in fault_store.active()}
        if service_name == "checkout-api":
            bad_deployment = active.get("bad_deployment")
            if bad_deployment:
                await _sleep_ms(int(bad_deployment.details.get("latency_ms", 750)))
            if "database_connection_exhaustion" in active:
                raise HTTPException(status_code=503, detail="database connection pool exhausted")
            if "memory_pressure" in active:
                await _sleep_ms(250)
            if downstreams:
                await _call_dependency(downstreams.get("payment", ""), "/charge", tracer)
                await _call_dependency(downstreams.get("inventory", ""), "/reserve", tracer)
            return {"status": "ok", "service": service_name, "version": app.state.version}
        if service_name == "payment-service" and "payment_timeout" in active:
            await _sleep_ms(int(active["payment_timeout"].details.get("timeout_ms", 3000)))
            raise HTTPException(status_code=504, detail="payment dependency timeout")
        if service_name == "inventory-service" and "inventory_errors" in active:
            raise HTTPException(status_code=503, detail="inventory reservation failed")
        return {"status": "ok", "service": service_name, "version": app.state.version}

    return app


async def _sleep_ms(milliseconds: int) -> None:
    import asyncio

    await asyncio.sleep(max(0, milliseconds) / 1000)


async def _call_dependency(base_url: str, path: str, tracer: trace.Tracer) -> None:
    if not base_url:
        return
    try:
        with tracer.start_as_current_span(f"dependency {path}") as span:
            span.set_attribute("dependency.url", f"{base_url.rstrip('/')}{path}")
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{base_url.rstrip('/')}{path}")
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"dependency failed: {path}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"dependency unavailable: {path}") from exc
