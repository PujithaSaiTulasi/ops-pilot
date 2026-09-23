"""Run OpsPilot evaluations as ``python -m opspilot.evals``."""

from opspilot.evals.runner import run_suite

if __name__ == "__main__":
    result = run_suite()
    print(f"passed {result['passed']}/{result['total']} ({result['pass_rate']:.0%})")
    raise SystemExit(0 if result["pass_rate"] >= 0.8 else 1)
