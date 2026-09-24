"""Shared simulator state with versioned Redis/file reconciliation."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import redis
from redis.exceptions import RedisError

from opspilot.simulator.models import FaultState


class FaultStore:
    """Store active faults and keep Redis and the disk mirror consistent."""

    KEY = "opspilot:simulator:faults"

    def __init__(self, redis_url: str | None = None, state_path: Path | None = None) -> None:
        self._memory: dict[str, dict[str, Any]] = {}
        self._redis_url = redis_url
        self._state_path = state_path
        self._redis: Any = None
        self._revision = 0
        if redis_url:
            self._connect_redis()

    def _connect_redis(self) -> None:
        if not self._redis_url:
            return
        try:
            client = redis.Redis.from_url(self._redis_url, decode_responses=True)
            client.ping()
            self._redis = client
        except (RedisError, OSError):
            self._redis = None

    def _ensure_redis(self) -> None:
        if self._redis is None:
            self._connect_redis()

    def _read_redis_snapshot(self) -> tuple[int, dict[str, dict[str, Any]]] | None:
        self._ensure_redis()
        if self._redis is None:
            return None
        try:
            self._redis.ping()
            raw = self._redis.get(self.KEY)
            return self._snapshot(json.loads(raw)) if raw else (0, {})
        except (RedisError, OSError, TypeError, ValueError):
            self._redis = None
            return None

    def _write_redis_snapshot(self, encoded: str) -> None:
        self._ensure_redis()
        if self._redis is None:
            return
        try:
            self._redis.ping()
            self._redis.set(self.KEY, encoded)
        except (RedisError, OSError):
            self._redis = None

    @staticmethod
    def _snapshot(value: Any) -> tuple[int, dict[str, dict[str, Any]]]:
        if not isinstance(value, dict):
            return 0, {}
        if isinstance(value.get("faults"), dict):
            revision = value.get("revision", 0)
            return (revision if isinstance(revision, int) else 0), value["faults"]
        # Accept state files written by the previous flat-dictionary format.
        return 0, value

    @staticmethod
    def _envelope(revision: int, faults: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "version": 1,
            "revision": revision,
            "faults": {key: dict(item) for key, item in faults.items()},
        }

    def _read_file_snapshot(self) -> tuple[int, dict[str, dict[str, Any]]] | None:
        if self._state_path is None or not self._state_path.exists():
            return None
        try:
            return self._snapshot(json.loads(self._state_path.read_text()))
        except (OSError, TypeError, ValueError):
            return None

    def _write_snapshot(
        self,
        revision: int,
        faults: Mapping[str, Mapping[str, Any]],
        *,
        file_only: bool = False,
        redis_only: bool = False,
    ) -> None:
        encoded = json.dumps(self._envelope(revision, faults), default=str, indent=2)
        if not redis_only and self._state_path is not None:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            # Replace the snapshot atomically so a process never reads a
            # half-written JSON document.
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._state_path.parent, delete=False
            ) as temporary:
                temporary.write(encoded)
                temporary_path = temporary.name
            os.replace(temporary_path, self._state_path)
        if not file_only:
            self._write_redis_snapshot(encoded)

    def _read(self) -> dict[str, dict[str, Any]]:
        """Return the newest snapshot and repair the older backend."""
        if self._redis_url is None and self._state_path is None:
            return dict(self._memory)
        file_snapshot = self._read_file_snapshot()
        redis_snapshot = self._read_redis_snapshot()
        if file_snapshot is None and redis_snapshot is None:
            return dict(self._memory)
        if file_snapshot is None:
            revision, faults = redis_snapshot  # type: ignore[misc]
            self._revision = revision
            if self._state_path is not None:
                self._write_snapshot(revision, faults, file_only=True)
            return dict(faults)
        if redis_snapshot is None:
            revision, faults = file_snapshot
            self._revision = revision
            return dict(faults)
        file_revision, file_faults = file_snapshot
        redis_revision, redis_faults = redis_snapshot
        if file_revision >= redis_revision:
            self._revision = file_revision
            if file_revision > redis_revision or file_faults != redis_faults:
                self._write_snapshot(file_revision, file_faults, redis_only=True)
            return dict(file_faults)
        self._revision = redis_revision
        if file_revision < redis_revision or file_faults != redis_faults:
            self._write_snapshot(redis_revision, redis_faults, file_only=True)
        return dict(redis_faults)

    def _write(self, value: Mapping[str, Mapping[str, Any]]) -> None:
        payload = {key: dict(item) for key, item in value.items()}
        if self._redis_url is None and self._state_path is None:
            self._revision += 1
            self._memory = payload
            return
        self._revision += 1
        self._write_snapshot(self._revision, payload)
        if self._redis is None and self._state_path is None:
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
