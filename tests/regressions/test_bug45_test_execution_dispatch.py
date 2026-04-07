"""Regression test for Bug 45: dispatch_command_status for test_execution doesn't advance sub_stage.

Tests that dispatch_command_status for test_execution:
- With TESTS_FAILED and sub_stage == "red_run": advances to implementation
- With TESTS_PASSED and sub_stage == "green_run": advances to coverage_review

SVP 2.2 adaptation:
- dispatch_command_status(state, command_type, status_line, sub_stage=None) -- 3-4 args
- PipelineState from pipeline_state
"""

import unittest
from pathlib import Path

from pipeline_state import PipelineState
from routing import dispatch_command_status


def _make_state(**kwargs):
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 10,
        "red_run_retries": 0,
        "fix_ladder_position": None,
        "alignment_iterations": 0,
        "debug_session": None,
        "debug_history": [],
        "verified_units": [],
        "pass_history": [],
        "delivered_repo_path": None,
        "redo_triggered_from": None,
    }
    defaults.update(kwargs)
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


class TestBug45TestExecutionDispatch(unittest.TestCase):
    """dispatch_command_status must advance sub_stage for test_execution."""

    def test_red_run_tests_failed_advances_to_implementation(self):
        """After red run, TESTS_FAILED should advance sub_stage to implementation."""
        state = _make_state(stage="3", sub_stage="red_run")

        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "red_run"
        )
        self.assertEqual(result.sub_stage, "implementation")

    def test_green_run_tests_passed_advances_to_coverage_review(self):
        """After green run, TESTS_PASSED should advance sub_stage to coverage_review."""
        state = _make_state(stage="3", sub_stage="green_run")

        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "green_run"
        )
        self.assertEqual(result.sub_stage, "coverage_review")


if __name__ == "__main__":
    unittest.main()
