"""Regression test for Bug 46: dispatch_agent_status for coverage_review.

Bug 65 update: coverage_review dispatch no longer advances sub_stage directly.
Instead, route() uses two-branch pattern to check last_status and determine next action.
The dispatch just returns state unchanged so route() can read last_status.txt.
"""

import sys
import unittest
from pathlib import Path
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
    """Bug 65: dispatch_agent_status for coverage_review returns state unchanged.
    Two-branch logic is now in route()."""

    def test_coverage_complete_returns_state_unchanged(self):
        """After COVERAGE_COMPLETE, dispatch should return state unchanged.
        Route() handles the two-branch check via last_status.txt."""
        from routing import dispatch_agent_status

        state = _make_state(stage="3", sub_stage="coverage_review")
        project_root = Path("/tmp/fake_project")

        result = dispatch_agent_status(
            state, "coverage_review", "COVERAGE_COMPLETE: no gaps",
            unit=1, phase="coverage_review", project_root=project_root,
        )
        # Bug 65: dispatch returns state unchanged; route() reads last_status
        self.assertEqual(result.sub_stage, "coverage_review")

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
