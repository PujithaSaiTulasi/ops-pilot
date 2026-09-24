"""Scenario catalog and injection helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from opspilot.simulator.models import ScenarioDefinition
from opspilot.simulator.store import FaultStore


def load_scenario(scenario_id: str, scenario_dir: Path | None = None) -> ScenarioDefinition:
    """Load and validate one scenario YAML file."""
    path = (scenario_dir or Path("scenarios")) / f"{scenario_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"scenario '{scenario_id}' was not found; expected YAML file at {path}"
        )
    parsed = yaml.safe_load(path.read_text()) or {}
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError(f"scenario YAML file is empty or invalid: {path}")
    data = dict(parsed)
    data["scenario_id"] = scenario_id
    return ScenarioDefinition.model_validate(data)


def inject_scenario(
    scenario_id: str, store: FaultStore, scenario_dir: Path | None = None
) -> ScenarioDefinition:
    """Activate a known scenario in the shared simulator state."""
    scenario = load_scenario(scenario_id, scenario_dir)
    store.activate(scenario_id, scenario.fault_details)
    return scenario
