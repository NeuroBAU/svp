"""Regression test for Bug 46: dispatch_agent_status for coverage_review doesn't advance to unit_completion.

Tests that dispatch_agent_status for coverage_review with COVERAGE_COMPLETE
and sub_stage == "coverage_review" advances to unit_completion.
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


class TestBug46CoverageDispatch(unittest.TestCase):
    """dispatch_agent_status must advance coverage_review to unit_completion."""

    def test_coverage_complete_advances_to_unit_completion(self):
        """After COVERAGE_COMPLETE with sub_stage=coverage_review,
        should advance to unit_completion."""
        from routing import dispatch_agent_status

        state = _make_state(stage="3", sub_stage="coverage_review")
        project_root = Path("/tmp/fake_project")

        with patch("routing.advance_sub_stage") as mock_advance:
            mock_advance.return_value = _make_state(
                stage="3", sub_stage="unit_completion"
            )
            result = dispatch_agent_status(
                state, "coverage_review", "COVERAGE_COMPLETE: no gaps",
                unit=1, phase="coverage_review", project_root=project_root,
            )
            mock_advance.assert_called_once_with(
                state, "unit_completion", project_root
            )
            self.assertEqual(result.sub_stage, "unit_completion")

    def test_coverage_complete_no_advance_wrong_substage(self):
        """If sub_stage is not coverage_review, should not advance."""
        from routing import dispatch_agent_status

        state = _make_state(stage="3", sub_stage="implementation")
        project_root = Path("/tmp/fake_project")

        result = dispatch_agent_status(
            state, "coverage_review", "COVERAGE_COMPLETE: no gaps",
            unit=1, phase="coverage_review", project_root=project_root,
        )
        # Should return state unchanged
        self.assertEqual(result.sub_stage, "implementation")


if __name__ == "__main__":
    unittest.main()
