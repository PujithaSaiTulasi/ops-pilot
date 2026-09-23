"""OpsPilot command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from opspilot.agent.runtime import OpsPilotAgent
from opspilot.approval.store import ApprovalStore
from opspilot.config import get_settings
from opspilot.simulator.catalog import inject_scenario
from opspilot.simulator.store import FaultStore


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

    subparsers.add_parser("reset", help="Reset all simulated incidents")
    subparsers.add_parser("state", help="Show active simulated incidents")

    investigate = subparsers.add_parser("investigate", help="Run the agent investigation loop")
    investigate.add_argument("--incident", default="bad_deployment", help="Scenario/incident id")
    investigate.add_argument("--request", default=None, help="Optional investigation request")

    evaluate = subparsers.add_parser("eval", help="Run the evaluation suite")
    evaluate.add_argument("--suite", default="default", help="Evaluation suite to run")

    approve = subparsers.add_parser("approve", help="Approve a pending side effect")
    approve.add_argument("--approval-id", required=True)
    reject = subparsers.add_parser("reject", help="Reject a pending side effect")
    reject.add_argument("--approval-id", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    store = FaultStore(get_settings().redis_url)
    if args.command == "inject":
        try:
            scenario = inject_scenario(args.scenario, store, get_settings().scenario_dir)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"activated {scenario.scenario_id}: {scenario.title}")
        return 0
    if args.command == "reset":
        store.clear_all()
        print("simulator reset")
        return 0
    if args.command == "state":
        print({"active_faults": [fault.model_dump(mode="json") for fault in store.active()]})
        return 0
    if args.command == "investigate":
        try:
            diagnosis, events = OpsPilotAgent(get_settings(), store).investigate(
                args.incident, args.request
            )
        except (KeyError, RuntimeError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(
            json.dumps(
                {"diagnosis": diagnosis.model_dump(mode="json"), "events": len(events)}, indent=2
            )
        )
        return 0
    if args.command in {"approve", "reject"}:
        try:
            request = ApprovalStore(get_settings().approval_store_path).decide(
                args.approval_id, args.command == "approve"
            )
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps(request.model_dump(mode="json"), indent=2))
        return 0
    print(
        f"command '{args.command}' is not implemented yet — see BUILD_STATUS.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
