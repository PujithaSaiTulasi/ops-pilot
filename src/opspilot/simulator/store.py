"""Shared simulator state with an in-memory fallback for tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import redis
from redis.exceptions import RedisError

from opspilot.simulator.models import FaultState


class FaultStore:
    """Store active faults in Redis when configured, otherwise in memory."""

    KEY = "opspilot:simulator:faults"

    def __init__(self, redis_url: str | None = None) -> None:
        self._memory: dict[str, dict[str, Any]] = {}
        self._redis = None
        if redis_url:
            try:
                client = redis.Redis.from_url(redis_url, decode_responses=True)
                client.ping()
                self._redis = client
            except (RedisError, OSError):
                self._redis = None

    def _read(self) -> dict[str, dict[str, Any]]:
        if self._redis is not None:
            try:
                raw = self._redis.get(self.KEY)
                return json.loads(raw) if raw else {}
            except (RedisError, TypeError, ValueError):
                pass
        return dict(self._memory)

    def _write(self, value: Mapping[str, Mapping[str, Any]]) -> None:
        payload = {key: dict(item) for key, item in value.items()}
        if self._redis is not None:
            try:
                self._redis.set(self.KEY, json.dumps(payload, default=str))
                return
            except RedisError:
                pass
        self._memory = payload

    def activate(self, scenario: str, details: Mapping[str, Any] | None = None) -> FaultState:
        """Activate one scenario and return its stored state."""
        state = FaultState(scenario=scenario, details=dict(details or {}))
        current = self._read()
        current[scenario] = state.model_dump(mode="json")
        self._write(current)
        return state

    def get(self, scenario: str) -> FaultState | None:
        """Return one active fault, if present."""
        raw = self._read().get(scenario)
        return FaultState.model_validate(raw) if raw else None

    def active(self) -> list[FaultState]:
        """Return active faults in deterministic order."""
        return [FaultState.model_validate(value) for _, value in sorted(self._read().items())]

    def clear(self, scenario: str) -> bool:
        """Clear one scenario and report whether it was active."""
        current = self._read()
        existed = scenario in current
        current.pop(scenario, None)
        self._write(current)
        return existed

    def clear_all(self) -> None:
        """Clear every active scenario."""
        self._write({})
