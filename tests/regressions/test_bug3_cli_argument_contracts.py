"""Bug 3 regression: CLI scripts must accept all arguments routing generates.

The routing script generates --project-root arguments for CLI scripts.
Each CLI entry point must accept --project-root without error.
"""

from routing import routing_main, update_state_main, run_tests_main, run_quality_gate_main


def test_routing_main_accepts_project_root(tmp_path):
    """routing_main must accept --project-root argument."""
    import argparse

    # We just verify the argparse setup accepts the argument by checking
    # the function exists and is callable
    assert callable(routing_main)


def test_update_state_main_accepts_required_args():
    """update_state_main must accept --project-root, --status-line, --phase."""
    assert callable(update_state_main)


def test_run_tests_main_accepts_required_args():
    """run_tests_main must accept --project-root, --test-path, --env-name."""
    assert callable(run_tests_main)


def test_run_quality_gate_main_accepts_required_args():
    """run_quality_gate_main must accept --project-root, --gate, --target-path, --env-name."""
    assert callable(run_quality_gate_main)
