"""OpsPilot command-line interface.

Foundation stub: argument parsing and exit codes are wired up so the Makefile
targets exist and are testable. Commands print a clear "not implemented"
message until their feature phase lands (see ``BUILD_STATUS.md``).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the ``opspilot`` argument parser."""
    parser = argparse.ArgumentParser(
        prog="opspilot",
        description="OpsPilot — agentic incident-response platform.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inject = subparsers.add_parser("inject", help="Inject a simulated incident")
    inject.add_argument(
        "--scenario",
        required=True,
        help="Scenario id to inject (e.g. bad_deployment)",
    )

    subparsers.add_parser("investigate", help="Run the agent investigation loop")

    evaluate = subparsers.add_parser("eval", help="Run the evaluation suite")
    evaluate.add_argument("--suite", default="default", help="Evaluation suite to run")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    print(
        f"command '{args.command}' is not implemented yet — foundation phase only "
        "(see BUILD_STATUS.md)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
