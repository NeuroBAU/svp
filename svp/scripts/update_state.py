"""update_state.py -- CLI entry point for pipeline state updates.

This is a thin wrapper that delegates to routing.update_state_main().
"""

import sys

from routing import update_state_main

if __name__ == "__main__":
    update_state_main(sys.argv[1:])
