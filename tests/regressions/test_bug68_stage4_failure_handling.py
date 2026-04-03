"""Regression test for Bug 68: Stage 4 failure handling.

Verifies that:
1. Stage 4 valid sub-stages include regression_adaptation
2. route() handles Stage 4 sub-stages correctly
3. dispatch_command_status routes TESTS_FAILED at Stage 4 (increments retries)
4. dispatch_command_status routes TESTS_PASSED at Stage 4 to regression_adaptation
5. dispatch_gate_response for gate_4_1 ASSEMBLY FIX returns state copy
6. dispatch_gate_response for gate_4_1 FIX BLUEPRINT restarts to Stage 2
7. dispatch_gate_response for gate_4_1 FIX SPEC restarts to Stage 1
8. dispatch_gate_response for gate_4_2 FIX BLUEPRINT restarts to Stage 2
9. dispatch_gate_response for gate_4_2 FIX SPEC restarts to Stage 1

Adapted for SVP 2.2 API:
- PipelineState is a dataclass from src.unit_5.stub
- VALID_SUB_STAGES replaces STAGE_4_SUB_STAGES
- route() reads state from disk (no state arg)
- dispatch_command_status(state, command_type, status_line, sub_stage=None) -- 3-4 args
- dispatch_gate_response(state, gate_id, response, project_root) -- 4 args
- Action block keys: action_type, agent_type, gate_id (lowercase)
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.unit_5.stub import PipelineState, VALID_SUB_STAGES, save_state
from src.unit_14.stub import (
    route,
    dispatch_command_status,
    dispatch_gate_response,
)


def _make_state(**overrides):
    defaults = {
        "stage": "4",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iterations": 0,
        "verified_units": [],
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _route_with_state(state, last_status=""):
    """Write state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status, encoding="utf-8")
        (root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        return route(root)


def _dispatch_gate_with_config(state, gate_id, response):
    """Call dispatch_gate_response with a temp project root containing config."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        return dispatch_gate_response(state, gate_id, response, root)


class TestStage4SubStages(unittest.TestCase):
    """regression_adaptation must be a valid Stage 4 sub-stage."""

    def test_regression_adaptation_in_stage_4_sub_stages(self):
        self.assertIn(
            "regression_adaptation",
            VALID_SUB_STAGES["4"],
            "regression_adaptation missing from Stage 4 valid sub-stages",
        )

    def test_none_in_stage_4_sub_stages(self):
        self.assertIn(
            None,
            VALID_SUB_STAGES["4"],
            "None missing from Stage 4 valid sub-stages",
        )


class TestStage4Routing(unittest.TestCase):
    """route() must handle Stage 4 correctly."""

    def test_route_no_status_invokes_integration_test_author(self):
        state = _make_state(sub_stage=None)
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "integration_test_author")

    def test_route_integration_tests_complete_runs_tests(self):
        state = _make_state(sub_stage=None)
        action = _route_with_state(state, "INTEGRATION_TESTS_COMPLETE")
        self.assertEqual(action["action_type"], "run_command")
        self.assertIn("test_execution", action.get("command", ""))


class TestStage4TestsFailedDispatch(unittest.TestCase):
    """dispatch_command_status must handle TESTS_FAILED at Stage 4."""

    def test_tests_failed_increments_retries(self):
        """Each failure increments red_run_retries."""
        state = _make_state(red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED",
        )
        self.assertEqual(result.red_run_retries, 1)

    def test_tests_failed_increments_again(self):
        """Second failure increments again."""
        state = _make_state(red_run_retries=1)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED",
        )
        self.assertEqual(result.red_run_retries, 2)

    def test_tests_failed_third_time(self):
        """Third failure."""
        state = _make_state(red_run_retries=2)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED",
        )
        self.assertEqual(result.red_run_retries, 3)


class TestStage4TestsPassedDispatch(unittest.TestCase):
    """dispatch_command_status must advance on TESTS_PASSED at Stage 4."""

    def test_tests_passed_advances_to_regression_adaptation(self):
        state = _make_state()
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED",
        )
        self.assertEqual(result.sub_stage, "regression_adaptation")


class TestGate41AssemblyFixDispatch(unittest.TestCase):
    """gate_4_1 ASSEMBLY FIX returns state copy."""

    def test_assembly_fix_returns_state(self):
        state = _make_state()
        result = _dispatch_gate_with_config(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX"
        )
        # Should return a copy (retry assembly)
        self.assertIsNotNone(result)
        self.assertEqual(result.stage, "4")


class TestGate41FixBlueprintDispatch(unittest.TestCase):
    """gate_4_1 FIX BLUEPRINT must restart to Stage 2."""

    def test_fix_blueprint_restarts_to_stage_2(self):
        state = _make_state()
        result = _dispatch_gate_with_config(
            state, "gate_4_1_integration_failure", "FIX BLUEPRINT"
        )
        self.assertEqual(result.stage, "2")


class TestGate41FixSpecDispatch(unittest.TestCase):
    """gate_4_1 FIX SPEC must restart to Stage 1."""

    def test_fix_spec_restarts_to_stage_1(self):
        state = _make_state()
        result = _dispatch_gate_with_config(
            state, "gate_4_1_integration_failure", "FIX SPEC"
        )
        self.assertEqual(result.stage, "1")


class TestGate42FixBlueprintDispatch(unittest.TestCase):
    """gate_4_2 FIX BLUEPRINT must restart to Stage 2."""

    def test_fix_blueprint_restarts_to_stage_2(self):
        state = _make_state()
        result = _dispatch_gate_with_config(
            state, "gate_4_2_assembly_exhausted", "FIX BLUEPRINT"
        )
        self.assertEqual(result.stage, "2")


class TestGate42FixSpecDispatch(unittest.TestCase):
    """gate_4_2 FIX SPEC must restart to Stage 1."""

    def test_fix_spec_restarts_to_stage_1(self):
        state = _make_state()
        result = _dispatch_gate_with_config(
            state, "gate_4_2_assembly_exhausted", "FIX SPEC"
        )
        self.assertEqual(result.stage, "1")


if __name__ == "__main__":
    unittest.main()
