"""Tests for the CLI entry point (foundation stub)."""

from __future__ import annotations

import pytest

from opspilot.cli import build_parser, main


def test_parser_requires_a_command() -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args([])

    assert excinfo.value.code == 2


def test_inject_requires_a_scenario() -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["inject"])

    assert excinfo.value.code == 2


def test_inject_command_activates_known_scenario(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["inject", "--scenario", "bad_deployment"])
    assert exit_code == 0
    assert "activated bad_deployment" in capsys.readouterr().out


def test_reset_command_clears_scenarios(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["reset"]) == 0
    assert "simulator reset" in capsys.readouterr().out


def test_investigate_command_runs_mock_agent(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["investigate", "--incident", "bad_deployment"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"suspected_root_cause"' in output
    assert '"events"' in output


def test_eval_command_runs_default_suite(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["eval"])
    output = capsys.readouterr().out
    assert '"pass_rate"' in output
