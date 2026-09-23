"""Local OpenTelemetry setup for the simulator and control plane."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opspilot.config import Settings

_configured = False


def configure_tracing(settings: Settings, service_name: str | None = None) -> None:
    """Configure a local OTLP exporter once per Python process."""
    global _configured
    if _configured or settings.otel_traces_exporter == "none":
        return
    resource = Resource.create(
        {
            "service.name": service_name or settings.otel_service_name,
            "deployment.environment": settings.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.environment == "test":
        trace.set_tracer_provider(provider)
        _configured = True
        return
    if settings.otel_traces_exporter == "otlp":
        exporter = OTLPSpanExporter(
            endpoint=f"{settings.otel_exporter_otlp_endpoint.rstrip('/')}/v1/traces"
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _configured = True
