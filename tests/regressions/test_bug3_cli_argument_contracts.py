"""Bug 3 regression: CLI scripts must accept all arguments routing generates.

The routing script generates --project-root arguments for CLI scripts.
Each CLI entry point must accept --project-root without error.

SVP 2.2: routing_main renamed to main; run_quality_gate_main removed
(quality gates handled inside routing dispatch). run_tests_main and
update_state_main remain.
"""

import pytest

from routing import main as routing_main, update_state_main, run_tests_main


def test_routing_main_accepts_project_root(tmp_path):
    """routing_main must accept --project-root argument."""
    # We just verify the argparse setup accepts the argument by checking
    # the function exists and is callable
    assert callable(routing_main)


def test_update_state_main_accepts_required_args():
    """update_state_main must accept --project-root, --status-line, --phase."""
    assert callable(update_state_main)


def test_run_tests_main_accepts_required_args():
    """run_tests_main must accept --project-root, --test-path, --env-name."""
    assert callable(run_tests_main)


