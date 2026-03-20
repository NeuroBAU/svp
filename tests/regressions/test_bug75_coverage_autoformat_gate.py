"""Regression test for Bug 75: coverage_review auto-format quality gate dispatch.

When coverage_review produces COVERAGE_COMPLETE: tests added, routing emits a
run_quality_gate.py --gate gate_b command with POST phase=quality_gate.
But the state sub_stage is still coverage_review, not quality_gate_b.
dispatch_command_status for quality_gate must handle this case by advancing
to unit_completion directly, instead of calling quality_gate_pass() which
requires sub_stage to be a quality gate sub-stage.

Verifies that:
1. dispatch_command_status with phase=quality_gate and sub_stage=coverage_review
   advances to unit_completion on COMMAND_SUCCEEDED (not TransitionError)
2. dispatch_command_status with phase=quality_gate and sub_stage=coverage_review
   advances to unit_completion on COMMAND_FAILED (residuals deferred to Gate C)
3. Normal quality_gate_pass still works for quality_gate_b sub-stage
"""

import unittest
from pathlib import Path

from pipeline_state import PipelineState
from routing import dispatch_command_status


def _make_state(**overrides):
    defaults = {
        "stage": "3",
        "sub_stage": "coverage_review",
        "current_unit": 1,
        "total_units": 10,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test",
        "last_action": None,
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestBug75CoverageAutoFormatSuccess(unittest.TestCase):
    """quality_gate COMMAND_SUCCEEDED at coverage_review must advance to unit_completion."""

    def test_succeeds_without_transition_error(self):
        state = _make_state(sub_stage="coverage_review")
        result = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", 1, "quality_gate", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "unit_completion")

    def test_does_not_mutate_input(self):
        state = _make_state(sub_stage="coverage_review")
        result = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", 1, "quality_gate", Path("/tmp")
        )
        self.assertIsNot(result, state)
        self.assertEqual(state.sub_stage, "coverage_review")


class TestBug75CoverageAutoFormatFailure(unittest.TestCase):
    """quality_gate COMMAND_FAILED at coverage_review must also advance to unit_completion."""

    def test_failure_advances_to_unit_completion(self):
        state = _make_state(sub_stage="coverage_review")
        result = dispatch_command_status(
            state, "COMMAND_FAILED: exit code 1", 1, "quality_gate", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "unit_completion")


class TestBug75NormalGateBStillWorks(unittest.TestCase):
    """Normal quality_gate_b dispatch must still work."""

    def test_gate_b_pass_advances_to_green_run(self):
        state = _make_state(sub_stage="quality_gate_b")
        result = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", 1, "quality_gate", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "green_run")


if __name__ == "__main__":
    unittest.main()
