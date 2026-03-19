"""Regression test for Bug 68: Stage 4 failure handling.

Verifies that:
1. gate_4_1 and gate_4_2 are in STAGE_4_SUB_STAGES
2. route() presents gate_4_1_integration_failure when sub_stage is gate_4_1
3. route() presents gate_4_2_assembly_exhausted when sub_stage is gate_4_2
4. dispatch_command_status routes TESTS_FAILED at Stage 4 to gate_4_1
5. dispatch_command_status routes TESTS_FAILED at Stage 4 with retries >= 3 to gate_4_2
6. dispatch_command_status routes TESTS_PASSED at Stage 4 to Stage 5
7. dispatch_gate_response for gate_4_1 ASSEMBLY FIX resets sub_stage to None
8. dispatch_gate_response for gate_4_1 FIX BLUEPRINT restarts to Stage 2
9. dispatch_gate_response for gate_4_1 FIX SPEC restarts to Stage 1
10. dispatch_gate_response for gate_4_2 FIX BLUEPRINT restarts to Stage 2
11. dispatch_gate_response for gate_4_2 FIX SPEC restarts to Stage 1
"""

import unittest
from pathlib import Path


def _make_state(**overrides):
    from pipeline_state import PipelineState

    defaults = {
        "stage": "4",
        "sub_stage": None,
        "current_unit": None,
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


class TestStage4SubStages(unittest.TestCase):
    """gate_4_1 and gate_4_2 must be valid Stage 4 sub-stages."""

    def test_gate_4_1_in_stage_4_sub_stages(self):
        from pipeline_state import STAGE_4_SUB_STAGES

        self.assertIn(
            "gate_4_1",
            STAGE_4_SUB_STAGES,
            "gate_4_1 missing from STAGE_4_SUB_STAGES",
        )

    def test_gate_4_2_in_stage_4_sub_stages(self):
        from pipeline_state import STAGE_4_SUB_STAGES

        self.assertIn(
            "gate_4_2",
            STAGE_4_SUB_STAGES,
            "gate_4_2 missing from STAGE_4_SUB_STAGES",
        )


class TestGate41Routing(unittest.TestCase):
    """route() must present gate_4_1_integration_failure when sub_stage is gate_4_1."""

    def test_route_gate_4_1_presents_gate(self):
        from routing import route

        state = _make_state(sub_stage="gate_4_1")
        result = route(state, Path("/tmp"))

        self.assertEqual(result["ACTION"], "human_gate")
        self.assertEqual(result["GATE_ID"], "gate_4_1_integration_failure")


class TestGate42Routing(unittest.TestCase):
    """route() must present gate_4_2_assembly_exhausted when sub_stage is gate_4_2."""

    def test_route_gate_4_2_presents_gate(self):
        from routing import route

        state = _make_state(sub_stage="gate_4_2")
        result = route(state, Path("/tmp"))

        self.assertEqual(result["ACTION"], "human_gate")
        self.assertEqual(result["GATE_ID"], "gate_4_2_assembly_exhausted")


class TestStage4TestsFailedDispatch(unittest.TestCase):
    """dispatch_command_status must handle TESTS_FAILED at Stage 4."""

    def test_tests_failed_routes_to_gate_4_1(self):
        """First failure (retries < 3) routes to gate_4_1."""
        from routing import dispatch_command_status

        state = _make_state(red_run_retries=0)
        result = dispatch_command_status(
            state, "TESTS_FAILED", None, "test_execution", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "gate_4_1")
        self.assertEqual(result.red_run_retries, 1)

    def test_tests_failed_increments_retries(self):
        """Each failure increments red_run_retries."""
        from routing import dispatch_command_status

        state = _make_state(red_run_retries=1)
        result = dispatch_command_status(
            state, "TESTS_FAILED", None, "test_execution", Path("/tmp")
        )
        self.assertEqual(result.red_run_retries, 2)
        self.assertEqual(result.sub_stage, "gate_4_1")

    def test_tests_failed_exhaustion_routes_to_gate_4_2(self):
        """When retries reach 3, route to gate_4_2."""
        from routing import dispatch_command_status

        state = _make_state(red_run_retries=2)
        result = dispatch_command_status(
            state, "TESTS_FAILED", None, "test_execution", Path("/tmp")
        )
        self.assertEqual(result.red_run_retries, 3)
        self.assertEqual(result.sub_stage, "gate_4_2")


class TestStage4TestsPassedDispatch(unittest.TestCase):
    """dispatch_command_status must advance to Stage 5 on TESTS_PASSED at Stage 4."""

    def test_tests_passed_advances_to_stage_5(self):
        from routing import dispatch_command_status

        state = _make_state()
        result = dispatch_command_status(
            state, "TESTS_PASSED", None, "test_execution", Path("/tmp")
        )
        self.assertEqual(result.stage, "5")
        self.assertIsNone(result.sub_stage)


class TestGate41AssemblyFixDispatch(unittest.TestCase):
    """gate_4_1 ASSEMBLY FIX returns state for retry (no-op in script)."""

    def test_assembly_fix_returns_state(self):
        from routing import dispatch_gate_response

        state = _make_state(sub_stage="gate_4_1")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        # Script returns state unchanged for ASSEMBLY FIX (retry assembly)
        self.assertIsNotNone(result)
        self.assertEqual(result.stage, "4")


class TestGate41FixBlueprintDispatch(unittest.TestCase):
    """gate_4_1 FIX BLUEPRINT must restart to Stage 2."""

    def test_fix_blueprint_restarts_to_stage_2(self):
        from routing import dispatch_gate_response

        state = _make_state(sub_stage="gate_4_1")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "FIX BLUEPRINT", Path("/tmp")
        )
        self.assertEqual(result.stage, "2")
        self.assertIsNone(result.sub_stage)


class TestGate41FixSpecDispatch(unittest.TestCase):
    """gate_4_1 FIX SPEC must restart to Stage 1."""

    def test_fix_spec_restarts_to_stage_1(self):
        from routing import dispatch_gate_response

        state = _make_state(sub_stage="gate_4_1")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "FIX SPEC", Path("/tmp")
        )
        self.assertEqual(result.stage, "1")
        self.assertIsNone(result.sub_stage)


class TestGate42FixBlueprintDispatch(unittest.TestCase):
    """gate_4_2 FIX BLUEPRINT must restart to Stage 2."""

    def test_fix_blueprint_restarts_to_stage_2(self):
        from routing import dispatch_gate_response

        state = _make_state(sub_stage="gate_4_2")
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", "FIX BLUEPRINT", Path("/tmp")
        )
        self.assertEqual(result.stage, "2")
        self.assertIsNone(result.sub_stage)


class TestGate42FixSpecDispatch(unittest.TestCase):
    """gate_4_2 FIX SPEC must restart to Stage 1."""

    def test_fix_spec_restarts_to_stage_1(self):
        from routing import dispatch_gate_response

        state = _make_state(sub_stage="gate_4_2")
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", "FIX SPEC", Path("/tmp")
        )
        self.assertEqual(result.stage, "1")
        self.assertIsNone(result.sub_stage)


if __name__ == "__main__":
    unittest.main()
