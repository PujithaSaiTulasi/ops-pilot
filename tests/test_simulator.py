"""Tests for the deterministic production simulator."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from opspilot.config import Settings
from opspilot.services.common import create_service_app
from opspilot.simulator.catalog import inject_scenario, load_scenario
from opspilot.simulator.store import FaultStore


class _FakeRedis:
    def __init__(self) -> None:
        self.value: str | None = None
        self.available = True

    def ping(self) -> bool:
        if not self.available:
            raise OSError("Redis unavailable")
        return True

    def get(self, _key: str) -> str | None:
        return self.value

    def set(self, _key: str, value: str) -> None:
        self.value = value


def test_scenario_catalog_loads_ground_truth() -> None:
    scenario = load_scenario("bad_deployment")

    assert scenario.scenario_id == "bad_deployment"
    assert scenario.root_cause.startswith("checkout version")
    assert scenario.fault_details["latency_ms"] == 750


def test_missing_scenario_yaml_fails_clearly(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="expected YAML file"):
        load_scenario("does_not_exist", tmp_path)


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


def test_file_snapshot_repairs_empty_redis(tmp_path) -> None:
    path = tmp_path / "simulator.json"
    file_store = FaultStore(state_path=path)
    file_store.activate("bad_deployment", {"latency_ms": 750})

    redis = _FakeRedis()
    recovered_store = FaultStore(state_path=path)
    recovered_store._redis = redis
    recovered_store._redis_url = "redis://test"

    assert recovered_store.get("bad_deployment") is not None
    assert '"bad_deployment"' in (redis.value or "")


def test_file_wins_after_redis_outage_and_is_replayed_on_recovery(tmp_path) -> None:
    path = tmp_path / "simulator.json"
    redis = _FakeRedis()
    store = FaultStore(state_path=path)
    store._redis = redis
    store._redis_url = "redis://test"
    store.activate("bad_deployment", {"latency_ms": 750})

    redis.available = False
    store.clear_all()
    assert store.active() == []

    redis.available = True
    store._redis = redis
    assert store.active() == []
    assert '"faults": {}' in (redis.value or "")
