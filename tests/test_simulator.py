"""Tests for the deterministic production simulator."""

from __future__ import annotations

from fastapi.testclient import TestClient

from opspilot.config import Settings
from opspilot.services.common import create_service_app
from opspilot.simulator.catalog import inject_scenario, load_scenario
from opspilot.simulator.store import FaultStore


def test_scenario_catalog_loads_ground_truth() -> None:
    scenario = load_scenario("bad_deployment")

    assert scenario.scenario_id == "bad_deployment"
    assert scenario.root_cause.startswith("checkout version")
    assert scenario.fault_details["latency_ms"] == 750


def test_fault_store_activates_and_clears() -> None:
    store = FaultStore()

    state = store.activate("bad_deployment", {"version": "1.1.0"})
    assert state.scenario == "bad_deployment"
    assert store.get("bad_deployment") is not None
    assert store.clear("bad_deployment") is True
    assert store.active() == []


def test_service_reports_active_fault_and_health() -> None:
    store = FaultStore()
    app = create_service_app(
        "payment-service",
        "/charge",
        "1.0.0",
        settings=Settings(_env_file=None, environment="test"),
        store=store,
    )
    client = TestClient(app)
    store.activate("payment_timeout", {"timeout_ms": 1})

    response = client.get("/faults")
    assert response.status_code == 200
    assert response.json()[0]["scenario"] == "payment_timeout"
    assert client.get("/health").json()["service"] == "payment-service"


def test_bad_deployment_adds_latency_to_checkout() -> None:
    store = FaultStore()
    app = create_service_app(
        "checkout-api",
        "/checkout",
        "1.0.0",
        settings=Settings(_env_file=None, environment="test"),
        store=store,
    )
    client = TestClient(app)
    store.activate("bad_deployment", {"latency_ms": 1})

    response = client.get("/checkout")
    assert response.status_code == 200
    assert response.headers["x-service-version"] == "1.0.0"


def test_inject_scenario_uses_explicit_store() -> None:
    store = FaultStore()

    scenario = inject_scenario("payment_timeout", store)

    assert scenario.scenario_id == "payment_timeout"
    assert store.get("payment_timeout") is not None
