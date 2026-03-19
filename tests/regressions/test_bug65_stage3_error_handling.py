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
"""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _make_state(**kwargs):
    """Create a minimal mock PipelineState."""
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 3,
        "red_run_retries": 0,
        "fix_ladder_position": None,
        "debug_session": None,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test",
        "last_action": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
    }
    defaults.update(kwargs)
    state = SimpleNamespace(**defaults)
    state.to_dict = lambda: {k: getattr(state, k) for k in defaults}
    return state


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
        from routing import route

        state = _make_state(stage="3", sub_stage=None, current_unit=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "run_command")
            self.assertIn("generate_stubs", action["COMMAND"])
            self.assertIn("stub_generation", action["POST"])

    def test_route_test_generation_invokes_test_agent(self):
        """test_generation sub_stage still invokes test_agent."""
        from routing import route

        state = _make_state(stage="3", sub_stage="test_generation", current_unit=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "test_agent")


class TestF9StubGenerationDispatch(unittest.TestCase):
    """F9: stub_generation COMMAND_SUCCEEDED -> advance to test_generation."""

    def test_stub_generation_succeeded_advances(self):
        from routing import dispatch_command_status

        state = _make_state(stage="3", sub_stage=None, current_unit=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "COMMAND_SUCCEEDED", unit=1,
                phase="stub_generation", project_root=root,
            )
            self.assertEqual(new_state.sub_stage, "test_generation")


class TestF2RedRunTestsPassed(unittest.TestCase):
    """F2: TESTS_PASSED at red_run means defective tests."""

    def test_tests_passed_at_red_run_increments_retries_and_regenerates(self):
        from routing import dispatch_command_status

        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=0
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "TESTS_PASSED: 5 passed", unit=1,
                phase="test_execution", project_root=root,
            )
            # Should regenerate tests (under retry limit)
            self.assertEqual(new_state.sub_stage, "test_generation")

    def test_tests_passed_at_red_run_presents_gate_31_at_limit(self):
        from routing import dispatch_command_status

        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=2
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "TESTS_PASSED: 5 passed", unit=1,
                phase="test_execution", project_root=root,
            )
            # At limit (retries=2 -> 3 after increment): present Gate 3.1
            self.assertEqual(new_state.sub_stage, "gate_3_1")


class TestF10RedRunRetriesIncrement(unittest.TestCase):
    """F10: red_run_retries incremented on TESTS_PASSED at red_run."""

    def test_retries_incremented(self):
        from routing import dispatch_command_status

        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=1
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "TESTS_PASSED: 5 passed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(new_state.red_run_retries, 2)


class TestF3GreenRunFailureFixLadder(unittest.TestCase):
    """F3: green_run TESTS_FAILED engages the fix ladder."""

    def test_first_failure_advances_to_fresh_impl(self):
        from routing import dispatch_command_status

        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "TESTS_FAILED: 3 passed, 2 failed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(new_state.sub_stage, "implementation")
            self.assertEqual(new_state.fix_ladder_position, "fresh_impl")

    def test_second_failure_advances_to_diagnostic(self):
        from routing import dispatch_command_status

        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "TESTS_FAILED: 3 passed, 2 failed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(new_state.sub_stage, "implementation")
            self.assertEqual(new_state.fix_ladder_position, "diagnostic")

    def test_after_diagnostic_impl_presents_gate_32(self):
        from routing import dispatch_command_status

        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_command_status(
                state, "TESTS_FAILED: 3 passed, 2 failed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(new_state.sub_stage, "gate_3_2")


class TestF6FixLadderPositionInRoute(unittest.TestCase):
    """F6: route() checks fix_ladder_position at implementation sub_stage."""

    def test_diagnostic_position_invokes_diagnostic_agent(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "diagnostic_agent")

    def test_fresh_impl_invokes_implementation_agent(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "implementation_agent")

    def test_diagnostic_impl_invokes_implementation_agent_with_context(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "implementation_agent")
            self.assertEqual(action["CONTEXT"], "diagnostic_impl")

    def test_none_position_invokes_normal_implementation(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "implementation_agent")
            self.assertEqual(action["CONTEXT"], "implementation")


class TestF4DiagnosticAgentDispatch(unittest.TestCase):
    """F4: diagnostic_agent dispatch parses DIAGNOSIS_COMPLETE."""

    def test_diagnosis_implementation_advances_to_diagnostic_impl(self):
        from routing import dispatch_agent_status

        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_agent_status(
                state, "diagnostic_agent",
                "DIAGNOSIS_COMPLETE: implementation",
                unit=1, phase="diagnostic", project_root=root,
            )
            self.assertEqual(new_state.fix_ladder_position, "diagnostic_impl")
            self.assertEqual(new_state.sub_stage, "implementation")

    def test_diagnosis_blueprint_returns_state_for_gate(self):
        from routing import dispatch_agent_status

        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1,
            fix_ladder_position="diagnostic",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_agent_status(
                state, "diagnostic_agent",
                "DIAGNOSIS_COMPLETE: blueprint",
                unit=1, phase="diagnostic", project_root=root,
            )
            # Should remain at current state for Gate 3.2 presentation
            self.assertEqual(new_state.sub_stage, "implementation")


class TestF5CoverageReviewTwoBranch(unittest.TestCase):
    """F5: coverage_review in route() checks last_status for two-branch."""

    def test_no_status_invokes_coverage_agent(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="coverage_review", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            _clear_last_status(root)
            action = route(state, root)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "coverage_review")

    def test_no_gaps_advances_to_unit_completion(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="coverage_review", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_last_status(root, "COVERAGE_COMPLETE: no gaps")
            action = route(state, root)
            self.assertEqual(action["ACTION"], "run_command")
            self.assertIn("unit_completion", action["POST"])

    def test_tests_added_emits_auto_format(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="coverage_review", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_last_status(root, "COVERAGE_COMPLETE: tests added")
            action = route(state, root)
            self.assertEqual(action["ACTION"], "run_command")
            self.assertIn("quality_gate", action["COMMAND"])


class TestF7Gate31Dispatch(unittest.TestCase):
    """F7: Gate 3.1 handlers engage fix ladder or regenerate tests."""

    def test_gate_31_presents_on_sub_stage(self):
        """Gate 3.1 is presented when sub_stage is gate_3_1."""
        from routing import route

        state = _make_state(
            stage="3", sub_stage="gate_3_1", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "human_gate")
            self.assertEqual(action["GATE_ID"], "gate_3_1_test_validation")

    def test_gate_31_test_correct_engages_fix_ladder(self):
        from routing import dispatch_gate_response

        state = _make_state(
            stage="3", sub_stage="gate_3_1", current_unit=1,
            fix_ladder_position=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_gate_response(
                state, "gate_3_1_test_validation", "TEST CORRECT", root,
            )
            self.assertEqual(new_state.sub_stage, "implementation")
            self.assertEqual(new_state.fix_ladder_position, "fresh_impl")

    def test_gate_31_test_wrong_regenerates_tests(self):
        from routing import dispatch_gate_response

        state = _make_state(
            stage="3", sub_stage="gate_3_1", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_gate_response(
                state, "gate_3_1_test_validation", "TEST WRONG", root,
            )
            self.assertEqual(new_state.sub_stage, "test_generation")


class TestGate32Presentation(unittest.TestCase):
    """Gate 3.2 is presented on fix ladder exhaustion."""

    def test_gate_32_presents_on_sub_stage(self):
        from routing import route

        state = _make_state(
            stage="3", sub_stage="gate_3_2", current_unit=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp").mkdir()
            action = route(state, root)
            self.assertEqual(action["ACTION"], "human_gate")
            self.assertEqual(action["GATE_ID"], "gate_3_2_diagnostic_decision")

    def test_gate_32_fix_implementation_resets_ladder(self):
        from routing import dispatch_gate_response

        state = _make_state(
            stage="3", sub_stage="gate_3_2", current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            new_state = dispatch_gate_response(
                state, "gate_3_2_diagnostic_decision",
                "FIX IMPLEMENTATION", root,
            )
            self.assertIsNone(new_state.fix_ladder_position)
            self.assertEqual(new_state.sub_stage, "implementation")


class TestFixLadderProgression(unittest.TestCase):
    """Test the full fix ladder progression through all positions."""

    def test_full_ladder_progression(self):
        """None -> fresh_impl -> diagnostic -> diagnostic_impl -> gate_3_2."""
        from routing import dispatch_command_status

        # Step 1: First green_run failure -> fresh_impl
        state = _make_state(
            stage="3", sub_stage="green_run", current_unit=1,
            fix_ladder_position=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            s1 = dispatch_command_status(
                state, "TESTS_FAILED: 0 passed, 5 failed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(s1.fix_ladder_position, "fresh_impl")
            self.assertEqual(s1.sub_stage, "implementation")

            # Step 2: Second green_run failure -> diagnostic
            s1.sub_stage = "green_run"
            s2 = dispatch_command_status(
                s1, "TESTS_FAILED: 0 passed, 5 failed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(s2.fix_ladder_position, "diagnostic")
            self.assertEqual(s2.sub_stage, "implementation")

            # Step 3: After diagnostic_impl, green_run failure -> gate_3_2
            s2.fix_ladder_position = "diagnostic_impl"
            s2.sub_stage = "green_run"
            s3 = dispatch_command_status(
                s2, "TESTS_FAILED: 0 passed, 5 failed", unit=1,
                phase="test_execution", project_root=root,
            )
            self.assertEqual(s3.sub_stage, "gate_3_2")


if __name__ == "__main__":
    unittest.main()
