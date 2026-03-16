"""Regression test for Bug 44: dispatch_agent_status null sub_stage for test_agent.

Tests that dispatch_agent_status for test_agent with TEST_GENERATION_COMPLETE
advances state when sub_stage is None (not just when it equals "test_generation").
Stage 3 routing normalizes sub_stage=None to test_generation for routing purposes,
so dispatch must also accept None.
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
        "stage": "0",
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


class TestBug44NullSubstageDispatch(unittest.TestCase):
    """dispatch_agent_status must handle sub_stage=None for test_agent."""

    def test_test_agent_complete_with_null_substage_advances(self):
        """When sub_stage is None (normalized to test_generation by routing),
        TEST_GENERATION_COMPLETE should enter quality_gate_a, not return
        state unchanged."""
        from routing import dispatch_agent_status

        state = _make_state(stage="3", sub_stage=None)
        project_root = Path("/tmp/fake_project")

        with patch("routing.enter_quality_gate") as mock_enter:
            mock_enter.return_value = _make_state(
                stage="3", sub_stage="quality_gate_a"
            )
            result = dispatch_agent_status(
                state, "test_agent", "TEST_GENERATION_COMPLETE",
                unit=1, phase="test_generation", project_root=project_root,
            )
            mock_enter.assert_called_once_with(state, "quality_gate_a")
            self.assertEqual(result.sub_stage, "quality_gate_a")

    def test_test_agent_complete_with_explicit_substage_advances(self):
        """When sub_stage is explicitly 'test_generation',
        TEST_GENERATION_COMPLETE should also enter quality_gate_a."""
        from routing import dispatch_agent_status

        state = _make_state(stage="3", sub_stage="test_generation")
        project_root = Path("/tmp/fake_project")

        with patch("routing.enter_quality_gate") as mock_enter:
            mock_enter.return_value = _make_state(
                stage="3", sub_stage="quality_gate_a"
            )
            result = dispatch_agent_status(
                state, "test_agent", "TEST_GENERATION_COMPLETE",
                unit=1, phase="test_generation", project_root=project_root,
            )
            mock_enter.assert_called_once_with(state, "quality_gate_a")
            self.assertEqual(result.sub_stage, "quality_gate_a")


if __name__ == "__main__":
    unittest.main()
