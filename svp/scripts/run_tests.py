"""
run_tests.py — Thin CLI wrapper that delegates to routing.run_tests_main().

The canonical implementation lives in routing.py (from unit_10). This wrapper
exists so that the routing script can emit commands of the form:
    python scripts/run_tests.py --test-path PATH --env-name NAME --status-file PATH ...

Usage:
    python scripts/run_tests.py --test-path PATH --env-name NAME
        [--status-file PATH] [--project-root PATH]
"""

import sys
from pathlib import Path


def main() -> None:
    # Ensure scripts/ is on the import path so bare imports resolve
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from routing import run_tests_main
    run_tests_main()


if __name__ == "__main__":
    main()
