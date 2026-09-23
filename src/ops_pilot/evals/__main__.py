"""`python -m ops_pilot.evals` entrypoint.

Not implemented yet — the evaluation harness lands in a later phase.
Fails loudly (non-zero exit) so it can never be mistaken for a passing run.
"""

import sys


def main() -> int:
    print(
        "ops_pilot.evals: NOT IMPLEMENTED yet (see BUILD_STATUS.md, Phase 5).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
