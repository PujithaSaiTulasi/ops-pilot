"""OpsPilot command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from opspilot.agent.runtime import OpsPilotAgent
from opspilot.agent.workflow import RemediationWorkflow
from opspilot.approval.store import ApprovalStore
from opspilot.config import get_settings
from opspilot.evals.runner import run_suite
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

    remediate = subparsers.add_parser("remediate", help="Prepare an approval-gated remediation")
    remediate.add_argument("--incident", default="bad_deployment")
    remediate.add_argument(
        "--approve", action="store_true", help="Approve immediately for a local demo"
    )
    resume = subparsers.add_parser("resume", help="Resume an approved remediation")
    resume.add_argument("--approval-id", required=True)
    demo = subparsers.add_parser("demo", help="Run the complete local investigation demo")
    demo.add_argument("--incident", default="bad_deployment")

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
    if args.command == "remediate":
        workflow = RemediationWorkflow(get_settings(), store)
        result = workflow.prepare(args.incident)
        if args.approve and result.approval_id:
            ApprovalStore(get_settings().approval_store_path).decide(result.approval_id, True)
            result = workflow.resume(result.approval_id)
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0
    if args.command == "resume":
        result = RemediationWorkflow(get_settings(), store).resume(args.approval_id)
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0
    if args.command == "demo":
        inject_scenario(args.incident, store, get_settings().scenario_dir)
        workflow = RemediationWorkflow(get_settings(), store)
        prepared = workflow.prepare(args.incident)
        assert prepared.approval_id is not None
        ApprovalStore(get_settings().approval_store_path).decide(prepared.approval_id, True)
        result = workflow.resume(prepared.approval_id)
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0
    if args.command == "eval":
        eval_result = run_suite()
        print(
            json.dumps(
                {key: eval_result[key] for key in ("total", "passed", "pass_rate")}, indent=2
            )
        )
        return (
            0
            if eval_result["pass_rate"] >= 0.8 and eval_result["unauthorized_action_rate"] == 0
            else 1
        )
    print(
        f"command '{args.command}' is not implemented yet — see BUILD_STATUS.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
