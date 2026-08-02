"""Run every check this project has, in one command.

    python3 test_all.py            # everything: smoke, learning, tuning
    python3 test_all.py --quick    # smoke + each suite's fast half

This runner exists because of a specific failure. The tuning suite carries a
guard whose whole purpose is that a constant added to simulation.py cannot
silently go missing from the screen that claims to show every number - and when
cultural transmission added two constants, the guard would have caught the
omission on its first run. It was not run: the commit exercised test_learning
and test_smoke, and nobody thought of test_tuning. A guard you have to remember
to invoke, suite by suite, is a guard that fires only when you already suspect
the answer. One command, no choosing.

Suites run as subprocesses, each with its own interpreter, so a crashed suite
cannot take the others down and every suite starts from clean module state.
Output streams through as it happens; the summary at the end names anything
that failed. Exit code is 0 only if every suite passed.
"""

import argparse
import os
import subprocess
import sys
import time

# Suites live beside this file, and are run from there. Resolving them against
# the current directory instead meant `python3 thronglets/test_all.py` from the
# repo root reported all three suites FAILED with exit code 2 - file not found -
# which reads exactly like a real failure. A runner that cries wolf when invoked
# from the wrong directory is worse than no runner.
HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    ("smoke", ["test_smoke.py"], ["test_smoke.py"]),
    ("learning", ["test_learning.py"], ["test_learning.py", "--quick"]),
    ("tuning", ["test_tuning.py"], ["test_tuning.py", "--quick"]),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true",
                    help="use each suite's fast mode where it has one")
    args = ap.parse_args()

    results = []
    for name, full, quick in SUITES:
        cmd = [sys.executable, "-u"] + [os.path.join(HERE, a) if a.endswith(".py") else a
                                        for a in (quick if args.quick else full)]
        print(f"\n{'=' * 74}\n{name}: {' '.join(cmd[1:])}\n{'=' * 74}", flush=True)
        t0 = time.time()
        code = subprocess.run(cmd, cwd=HERE).returncode
        results.append((name, code, time.time() - t0))

    print(f"\n{'=' * 74}")
    failed = [n for n, code, _ in results if code != 0]
    for name, code, dt in results:
        print(f"  {name:<10} {'OK' if code == 0 else f'FAILED ({code})':<12} {dt:6.1f}s")
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        sys.exit(1)
    print("\nOK: every suite passed.")


if __name__ == "__main__":
    main()
