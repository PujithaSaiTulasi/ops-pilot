"""Scenario catalog and injection helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from opspilot.simulator.models import ScenarioDefinition
from opspilot.simulator.store import FaultStore

DEFAULT_SCENARIOS: dict[str, dict[str, Any]] = {
    "bad_deployment": {
        "title": "Checkout latency after a bad deployment",
        "description": "A new checkout release introduces a latency regression.",
        "affected_services": ["checkout-api"],
        "symptoms": ["checkout p95 latency is elevated", "deployment occurred recently"],
        "root_cause": "checkout version 1.1.0 introduced a latency regression",
        "safe_remediation": "rollback checkout-api to version 1.0.0",
        "verification": ["checkout p95 latency below 300ms", "active version is 1.0.0"],
        "fault_details": {"service": "checkout-api", "version": "1.1.0", "latency_ms": 750},
    },
    "payment_timeout": {
        "title": "Payment dependency timeout",
        "description": "The payment service starts timing out requests.",
        "affected_services": ["payment-service", "checkout-api"],
        "symptoms": ["payment timeout rate is elevated", "checkout errors increase"],
        "root_cause": "payment-service dependency timeout",
        "safe_remediation": "restore payment-service timeout behavior",
        "verification": ["payment timeout rate is zero", "checkout succeeds"],
        "fault_details": {"service": "payment-service", "timeout_ms": 3000},
    },
    "inventory_errors": {
        "title": "Inventory dependency errors",
        "description": "The inventory service returns intermittent errors.",
        "affected_services": ["inventory-service", "checkout-api"],
        "symptoms": ["inventory error rate is elevated", "checkout returns dependency errors"],
        "root_cause": "inventory-service is rejecting reservation requests",
        "safe_remediation": "restore inventory-service responses",
        "verification": ["inventory errors return to baseline", "checkout succeeds"],
        "fault_details": {"service": "inventory-service", "error_rate": 1.0},
    },
    "database_connection_exhaustion": {
        "title": "Database connection pool exhaustion",
        "description": "The checkout service cannot obtain a database connection.",
        "affected_services": ["checkout-api"],
        "symptoms": ["database connection usage is saturated", "checkout returns 503"],
        "root_cause": "checkout database connection pool exhausted",
        "safe_remediation": "restore database connection capacity",
        "verification": ["database pool usage below 80%", "checkout succeeds"],
        "fault_details": {"service": "checkout-api", "pool_usage": 1.0},
    },
    "memory_pressure": {
        "title": "Checkout memory pressure",
        "description": "Checkout memory usage grows above the alert threshold.",
        "affected_services": ["checkout-api"],
        "symptoms": ["memory usage is elevated", "latency is increasing"],
        "root_cause": "checkout-api memory pressure",
        "safe_remediation": "restart checkout-api after approval",
        "verification": ["memory usage below 80%"],
        "fault_details": {"service": "checkout-api", "memory_usage": 0.95},
    },
    "dependency_failure": {
        "title": "External dependency failure",
        "description": "A simulated downstream dependency is unavailable.",
        "affected_services": ["checkout-api"],
        "symptoms": ["dependency requests fail", "checkout errors increase"],
        "root_cause": "downstream dependency unavailable",
        "safe_remediation": "restore downstream dependency",
        "verification": ["dependency errors return to baseline"],
        "fault_details": {"service": "checkout-api", "dependency": "external"},
    },
}


def load_scenario(scenario_id: str, scenario_dir: Path | None = None) -> ScenarioDefinition:
    """Load a YAML scenario when available, with a safe built-in fallback."""
    path = (scenario_dir or Path("scenarios")) / f"{scenario_id}.yaml"
    data: dict[str, Any]
    if path.exists():
        parsed = yaml.safe_load(path.read_text()) or {}
        data = dict(parsed)
    else:
        data = dict(DEFAULT_SCENARIOS.get(scenario_id, {}))
    if not data:
        raise KeyError(f"unknown scenario: {scenario_id}")
    data["scenario_id"] = scenario_id
    return ScenarioDefinition.model_validate(data)


def inject_scenario(
    scenario_id: str, store: FaultStore, scenario_dir: Path | None = None
) -> ScenarioDefinition:
    """Activate a known scenario in the shared simulator state."""
    scenario = load_scenario(scenario_id, scenario_dir)
    store.activate(scenario_id, scenario.fault_details)
    return scenario
