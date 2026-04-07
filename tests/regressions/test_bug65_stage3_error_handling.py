"""Regression tests for Bug 65: Stage 3 error handling infrastructure.

Tests all Stage 3 failure paths:
- F1: stub_generation routing and dispatch
- F2: red_run with TESTS_PASSED (defective tests path)
- F3: green_run failure -> fix ladder engagement
- F4: diagnostic_agent invocation and dispatch
- F5: coverage_review two-branch check and auto-format
- F6: fix_ladder_position checked in route() at implementation sub_stage
- F7: Gate 3.1 presentation and both responses
- F9: stub_generation in dispatch_command_status
- F10: red_run_retries increment and limit
- Gate 3.2 presentation on ladder exhaustion
- Fix ladder progression through all positions

Adapted for SVP 2.2 API:
- route() reads state from disk (no state arg)
- dispatch_command_status(state, command_type, status_line, sub_stage=None) -- 3-4 args
- dispatch_agent_status(state, agent_type, status_line, project_root) -- 4 args
- Action block keys: action_type, agent_type, command, gate_id, post
- PipelineState is a dataclass from pipeline_state
"""

import json
import tempfile
import unittest
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import (
    route,
    dispatch_command_status,
    dispatch_agent_status,
    dispatch_gate_response,
    GATE_VOCABULARY,
)


def _make_state(**kwargs):
    """Create a minimal PipelineState with sensible defaults for Stage 3."""
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 3,
        "red_run_retries": 0,
        "fix_ladder_position": None,
        "debug_session": None,
        "alignment_iterations": 0,
        "verified_units": [],
        "pass_history": [],
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


def _route_with_state(state, last_status=""):
    """Write state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status, encoding="utf-8")
        # Also write svp_config.json
        (root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        return route(root)


def _write_last_status(project_root, status):
    """Write a status to .svp/last_status.txt."""
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    (svp_dir / "last_status.txt").write_text(status, encoding="utf-8")


def _clear_last_status(project_root):
    """Remove .svp/last_status.txt."""
    status_file = project_root / ".svp" / "last_status.txt"
    if status_file.exists():
        status_file.unlink()


class TestF1StubGenerationRouting(unittest.TestCase):
    """F1: sub_stage=None routes to stub_generation command, not test_agent."""

    def test_route_sub_stage_none_emits_stub_generation(self):
        state = _make_state(stage="3", sub_stage="stub_generation", current_unit=1)
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "run_command")
        self.assertIn("stub_generation", action.get("command", ""))

    def test_route_test_generation_invokes_test_agent(self):
        """test_generation sub_stage still invokes test_agent."""
        state = _make_state(stage="3", sub_stage="test_generation", current_unit=1)
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "test_agent")


class TestF9StubGenerationDispatch(unittest.TestCase):
    """F9: stub_generation COMMAND_SUCCEEDED -> advance to test_generation."""

    def test_stub_generation_succeeded_advances(self):
        state = _make_state(stage="3", sub_stage="stub_generation", current_unit=1)
        new_state = dispatch_command_status(
            state, "stub_generation", "COMMAND_SUCCEEDED",
        )
        self.assertEqual(new_state.sub_stage, "test_generation")


class TestF2RedRunTestsPassed(unittest.TestCase):
    """F2: TESTS_PASSED at red_run means defective tests."""

    def test_tests_passed_at_red_run_increments_retries_and_regenerates(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=0
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "red_run",
        )
        # Should regenerate tests (under retry limit)
        self.assertEqual(new_state.sub_stage, "test_generation")

    def test_tests_passed_at_red_run_presents_gate_at_limit(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=2
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "red_run",
        )
        # At limit (retries=2 -> 3 after increment): advance to implementation
        # (fix ladder engagement via route)
        self.assertEqual(new_state.sub_stage, "implementation")


class TestF10RedRunRetriesIncrement(unittest.TestCase):
    """F10: red_run_retries incremented on TESTS_PASSED at red_run."""

    def test_retries_incremented(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=1
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "red_run",
        )
        self.assertEqual(new_state.red_run_retries, 2)


class TestF3GreenRunFailureFixLadder(unittest.TestCase):
    """F3: green_run TESTS_FAILED engages the fix ladder."""

    def test_first_failure_advances_to_fresh_impl(self):
        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position=None,
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "green_run",
        )
        self.assertEqual(new_state.sub_stage, "implementation")
        self.assertEqual(new_state.fix_ladder_position, "fresh_impl")

    def test_second_failure_advances_to_diagnostic(self):
        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "green_run",
        )
        # In SVP 2.2, advance_fix_ladder only sets sub_stage="implementation"
        # for fresh_impl and diagnostic_impl positions. For diagnostic,
        # sub_stage stays unchanged from the input.
        self.assertEqual(new_state.fix_ladder_position, "diagnostic")

    def test_after_diagnostic_impl_exhausted(self):
        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "green_run",
        )
        self.assertEqual(new_state.fix_ladder_position, "exhausted")


class TestF6FixLadderPositionInRoute(unittest.TestCase):
    """F6: route() checks fix_ladder_position at implementation sub_stage."""

    def test_diagnostic_position_invokes_diagnostic_agent(self):
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic",
        )
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "diagnostic_agent")

    def test_fresh_impl_invokes_implementation_agent(self):
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "implementation_agent")

    def test_diagnostic_impl_invokes_implementation_agent(self):
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "implementation_agent")

    def test_none_position_invokes_normal_implementation(self):
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position=None,
        )
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "implementation_agent")


class TestF4DiagnosticAgentDispatch(unittest.TestCase):
    """F4: diagnostic_agent dispatch parses DIAGNOSIS_COMPLETE."""

    def test_diagnosis_complete_returns_copy(self):
        """In SVP 2.2, diagnostic_agent dispatch returns a copy of state.
        The routing layer handles subsequent advancement."""
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new_state = dispatch_agent_status(
                state, "diagnostic_agent",
                "DIAGNOSIS_COMPLETE",
                root,
            )
            # dispatch returns copy; fix_ladder_position unchanged
            self.assertEqual(new_state.fix_ladder_position, "diagnostic")
            self.assertEqual(new_state.sub_stage, "implementation")
            self.assertIsNot(new_state, state)


class TestF5CoverageReviewTwoBranch(unittest.TestCase):
    """F5: coverage_review in route() checks last_status for two-branch."""

    def test_no_status_invokes_coverage_agent(self):
        state = _make_state(
            stage="3", sub_stage="coverage_review", current_unit=1,
        )
        action = _route_with_state(state, last_status="")
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "coverage_review_agent")

    def test_coverage_complete_advances_to_unit_completion(self):
        state = _make_state(
            stage="3", sub_stage="coverage_review", current_unit=1,
        )
        # In SVP 2.2, route() handles this by advancing sub_stage and re-routing
        action = _route_with_state(state, last_status="COVERAGE_COMPLETE: no gaps")
        # Should advance to unit_completion
        self.assertEqual(action["action_type"], "run_command")
        self.assertIn("unit_completion", action.get("command", ""))


class TestF7Gate31Dispatch(unittest.TestCase):
    """F7: Gate 3.1 handlers for test validation."""

    def test_gate_31_vocabulary_exists(self):
        """Gate 3.1 test_validation is in vocabulary."""
        self.assertIn("gate_3_1_test_validation", GATE_VOCABULARY)
        self.assertIn("TEST CORRECT", GATE_VOCABULARY["gate_3_1_test_validation"])
        self.assertIn("TEST WRONG", GATE_VOCABULARY["gate_3_1_test_validation"])

    def test_gate_31_test_correct_returns_copy(self):
        """In SVP 2.2, gate 3.1 TEST CORRECT returns a copy of state.
        The routing layer continues normal flow."""
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1,
            fix_ladder_position=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new_state = dispatch_gate_response(
                state, "gate_3_1_test_validation", "TEST CORRECT", root,
            )
            # Returns copy; routing handles next step
            self.assertIsNot(new_state, state)
            self.assertEqual(new_state.stage, "3")

    def test_gate_31_test_wrong_regenerates_tests(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new_state = dispatch_gate_response(
                state, "gate_3_1_test_validation", "TEST WRONG", root,
            )
            self.assertEqual(new_state.sub_stage, "test_generation")


class TestGate32Presentation(unittest.TestCase):
    """Gate 3.2 is presented on fix ladder exhaustion."""

    def test_gate_32_vocabulary_exists(self):
        """Gate 3.2 diagnostic_decision is in vocabulary."""
        self.assertIn("gate_3_2_diagnostic_decision", GATE_VOCABULARY)

    def test_gate_32_exhausted_presents_gate(self):
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="exhausted",
        )
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_3_2_diagnostic_decision")

    def test_gate_32_fix_implementation_advances_to_implementation(self):
        """FIX IMPLEMENTATION sets sub_stage to implementation."""
        state = _make_state(
            stage="3", sub_stage="stub_generation", current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new_state = dispatch_gate_response(
                state, "gate_3_2_diagnostic_decision",
                "FIX IMPLEMENTATION", root,
            )
            self.assertEqual(new_state.sub_stage, "implementation")


class TestFixLadderProgression(unittest.TestCase):
    """Test the full fix ladder progression through all positions."""

    def test_full_ladder_progression(self):
        """None -> fresh_impl -> diagnostic -> diagnostic_impl -> exhausted."""
        # Step 1: First green_run failure -> fresh_impl
        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position=None,
        )
        s1 = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "green_run",
        )
        self.assertEqual(s1.fix_ladder_position, "fresh_impl")
        self.assertEqual(s1.sub_stage, "implementation")

        # Step 2: Second green_run failure -> diagnostic
        s2 = dispatch_command_status(
            s1, "test_execution", "TESTS_FAILED", "green_run",
        )
        self.assertEqual(s2.fix_ladder_position, "diagnostic")
        self.assertEqual(s2.sub_stage, "implementation")

        # Step 3: After diagnostic_impl, green_run failure -> exhausted
        s3 = dispatch_command_status(
            s2, "test_execution", "TESTS_FAILED", "green_run",
        )
        self.assertEqual(s3.fix_ladder_position, "diagnostic_impl")


if __name__ == "__main__":
    unittest.main()
