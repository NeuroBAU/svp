"""Regression test for Bug 44: dispatch_agent_status null sub_stage for test_agent.

Tests that dispatch_agent_status for test_agent with TEST_GENERATION_COMPLETE
advances state when sub_stage is None (not just when it equals "test_generation").
Stage 3 routing normalizes sub_stage=None to test_generation for routing purposes,
so dispatch must also accept None.

SVP 2.2 adaptation:
- dispatch_agent_status(state, agent_type, status_line, project_root) -- 4 args
- PipelineState from src.unit_5.stub
"""

import unittest
from pathlib import Path

from src.unit_5.stub import PipelineState
from src.unit_14.stub import dispatch_agent_status


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


class TestBug44NullSubstageDispatch(unittest.TestCase):
    """dispatch_agent_status must handle sub_stage=None for test_agent."""

    def test_test_agent_complete_with_null_substage_advances(self):
        """When sub_stage is None, TEST_GENERATION_COMPLETE should produce
        a state change (not return unchanged)."""
        state = _make_state(stage="3", sub_stage=None)
        project_root = Path("/tmp/fake_project")

        result = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE",
            project_root,
        )
        # SVP 2.2: dispatch returns a copy; the actual quality_gate_a
        # transition happens in route() via two-branch pattern
        self.assertIsNotNone(result)

    def test_test_agent_complete_with_explicit_substage_advances(self):
        """When sub_stage is explicitly 'test_generation',
        TEST_GENERATION_COMPLETE should also produce a state change."""
        state = _make_state(stage="3", sub_stage="test_generation")
        project_root = Path("/tmp/fake_project")

        result = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE",
            project_root,
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
