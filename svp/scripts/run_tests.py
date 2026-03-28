"""run_tests.py -- CLI entry point for test execution.

This is a thin wrapper that delegates to routing.run_tests_main().
"""

import sys

from routing import run_tests_main

if __name__ == "__main__":
    run_tests_main(sys.argv[1:])
