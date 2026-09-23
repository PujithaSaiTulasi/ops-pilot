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


@pytest.mark.parametrize(
    "argv",
    [
        ["inject", "--scenario", "bad_deployment"],
        ["investigate"],
        ["eval", "--suite", "default"],
    ],
)
def test_unimplemented_commands_exit_non_zero_with_guidance(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Until their phase lands, commands fail loudly instead of pretending to work."""
    exit_code = main(argv)

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "not implemented yet" in err
    assert "BUILD_STATUS.md" in err


def test_unimplemented_command_names_the_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["investigate"])

    assert "'investigate'" in capsys.readouterr().err
