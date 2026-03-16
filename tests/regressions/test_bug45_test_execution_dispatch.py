"""Regression test for Bug 45: dispatch_command_status for test_execution doesn't advance sub_stage.

Tests that dispatch_command_status for phase test_execution:
- With TESTS_FAILED and sub_stage == "red_run": advances to implementation
- With TESTS_PASSED and sub_stage == "green_run": advances to coverage_review
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Path setup: ensure scripts/ is importable
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _make_state(**kwargs):
    """Create a minimal mock PipelineState with sensible defaults."""
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "red_run_retries": 0,
        "debug_session": None,
        "alignment_iteration": 0,
        "fix_ladder": None,
        "pass_number": 1,
        "quality_gate": None,
        "delivered_repo_path": None,
        "redo_profile_revision": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestBug45TestExecutionDispatch(unittest.TestCase):
    """dispatch_command_status must advance sub_stage for test_execution."""

    def test_red_run_tests_failed_advances_to_implementation(self):
        """After red run, TESTS_FAILED should advance sub_stage to implementation."""
        from routing import dispatch_command_status

        state = _make_state(stage="3", sub_stage="red_run")
        project_root = Path("/tmp/fake_project")

        with patch("routing.advance_sub_stage") as mock_advance:
            mock_advance.return_value = _make_state(
                stage="3", sub_stage="implementation"
            )
            result = dispatch_command_status(
                state, "TESTS_FAILED", unit=1, phase="test_execution",
                project_root=project_root,
            )
            mock_advance.assert_called_once_with(state, "implementation", project_root)
            self.assertEqual(result.sub_stage, "implementation")

    def test_green_run_tests_passed_advances_to_coverage_review(self):
        """After green run, TESTS_PASSED should advance sub_stage to coverage_review."""
        from routing import dispatch_command_status

        state = _make_state(stage="3", sub_stage="green_run")
        project_root = Path("/tmp/fake_project")

        with patch("routing.advance_sub_stage") as mock_advance:
            mock_advance.return_value = _make_state(
                stage="3", sub_stage="coverage_review"
            )
            result = dispatch_command_status(
                state, "TESTS_PASSED", unit=1, phase="test_execution",
                project_root=project_root,
            )
            mock_advance.assert_called_once_with(state, "coverage_review", project_root)
            self.assertEqual(result.sub_stage, "coverage_review")


if __name__ == "__main__":
    unittest.main()
