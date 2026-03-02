"""
update_state.py — Thin CLI wrapper that delegates to routing.update_state_main().

The canonical implementation lives in routing.py (from unit_10). This wrapper
exists so that the routing script can emit POST commands of the form:
    python scripts/update_state.py --phase PHASE --status-file PATH ...

Usage:
    python scripts/update_state.py --phase PHASE --status-file PATH
                                   [--unit N] [--gate GATE] [--project-root PATH]
"""

import sys
from pathlib import Path


def main() -> None:
    # Ensure scripts/ is on the import path so bare imports resolve
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from routing import update_state_main
    update_state_main()


if __name__ == "__main__":
    main()
