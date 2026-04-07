"""Regression test for Bug 46: dispatch_agent_status for coverage_review.

Bug 65 update: coverage_review dispatch no longer advances sub_stage directly.
Instead, route() uses two-branch pattern to check last_status and determine next action.
The dispatch just returns state unchanged so route() can read last_status.txt.

SVP 2.2 adaptation:
- dispatch_agent_status(state, agent_type, status_line, project_root) -- 4 args
- PipelineState from src.unit_5.stub
"""

import unittest
from pathlib import Path

from pipeline_state import PipelineState
from routing import dispatch_agent_status


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


class TestBug46CoverageDispatch(unittest.TestCase):
    """Bug 65: dispatch_agent_status for coverage_review returns state unchanged.
    Two-branch logic is now in route()."""

    def test_coverage_complete_returns_state_unchanged(self):
        """After COVERAGE_COMPLETE, dispatch should return state copy.
        Route() handles the two-branch check via last_status.txt."""
        state = _make_state(stage="3", sub_stage="coverage_review")
        project_root = Path("/tmp/fake_project")

        result = dispatch_agent_status(
            state, "coverage_review_agent", "COVERAGE_COMPLETE: no gaps",
            project_root,
        )
        # Bug 65: dispatch returns state copy; route() reads last_status
        self.assertEqual(result.sub_stage, "coverage_review")

    def test_coverage_complete_no_advance_wrong_substage(self):
        """If sub_stage is not coverage_review, should not advance."""
        state = _make_state(stage="3", sub_stage="implementation")
        project_root = Path("/tmp/fake_project")

        result = dispatch_agent_status(
            state, "coverage_review_agent", "COVERAGE_COMPLETE: no gaps",
            project_root,
        )
        # Should return state unchanged
        self.assertEqual(result.sub_stage, "implementation")


if __name__ == "__main__":
    unittest.main()
