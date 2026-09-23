"""Tests that the project version is declared exactly once."""

from __future__ import annotations

import tomllib
from pathlib import Path

import opspilot

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())


def test_package_version_matches_pyproject() -> None:
    assert _pyproject()["project"]["version"] == opspilot.__version__


def test_requires_python_is_3_12() -> None:
    assert _pyproject()["project"]["requires-python"] == ">=3.12"
