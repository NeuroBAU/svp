"""Regression test for Bug 76: Pre-Stage-3 must run infrastructure setup.

The routing for stage=pre_stage_3 must first run setup_infrastructure.py
(deterministic command) before invoking the reference_indexing agent.
Without this step, the conda environment is never created and quality
packages (ruff, mypy) are never installed.

Verifies that:
1. route() at pre_stage_3 with sub_stage=None emits run_command for infrastructure
2. route() at pre_stage_3 with sub_stage=reference_indexing invokes agent
3. dispatch_command_status for infrastructure COMMAND_SUCCEEDED advances to reference_indexing
4. dispatch_command_status for infrastructure COMMAND_FAILED restarts from Stage 2
"""

import tempfile
import unittest
from pathlib import Path

from pipeline_state import PipelineState
from routing import route, dispatch_command_status


def _make_state(**overrides):
    defaults = {
        "stage": "pre_stage_3",
        "sub_stage": None,
        "current_unit": None,
        "total_units": None,
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


class TestBug76InfrastructureRouting(unittest.TestCase):
    """pre_stage_3 with sub_stage=None must run infrastructure setup."""

    def test_none_substage_runs_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".svp").mkdir()

            state = _make_state(sub_stage=None)
            result = route(state, project_root)

            self.assertEqual(result["ACTION"], "run_command")
            self.assertIn("setup_infrastructure", result["COMMAND"])

    def test_reference_indexing_substage_invokes_agent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".svp").mkdir()

            state = _make_state(sub_stage="reference_indexing")
            result = route(state, project_root)

            self.assertEqual(result["ACTION"], "invoke_agent")
            self.assertEqual(result["AGENT"], "reference_indexing")


class TestBug76InfrastructureDispatch(unittest.TestCase):
    """Infrastructure command dispatch must advance or restart."""

    def test_success_advances_to_reference_indexing(self):
        state = _make_state(sub_stage=None)
        result = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", None, "infrastructure", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "reference_indexing")

    def test_failure_restarts_from_stage_2(self):
        state = _make_state(sub_stage=None)
        result = dispatch_command_status(
            state, "COMMAND_FAILED: exit code 1", None, "infrastructure", Path("/tmp")
        )
        self.assertEqual(result.stage, "2")


if __name__ == "__main__":
    unittest.main()
