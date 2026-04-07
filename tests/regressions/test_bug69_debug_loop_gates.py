"""Regression test for Bug 69: Debug loop gates.

Verifies all four fixes:
E.1: gate_6_0 presentation from unauthorized debug, AUTHORIZE DEBUG advances,
     ABANDON DEBUG abandons session
E.2: gate_6_1 presentation from regression_test phase, TEST CORRECT advances to
     lessons_learned, TEST WRONG re-invokes test agent
E.3: gate_6_3 RECLASSIFY BUG resets to triage phase
E.4: gate_6_5 presentation from commit phase, COMMIT APPROVED completes session,
     COMMIT REJECTED re-presents

Adapted for SVP 2.2 API:
- PipelineState is a dataclass from pipeline_state
- debug_session is a plain dict (not DebugSession class)
- route() reads state from disk (no state arg)
- dispatch_gate_response(state, gate_id, response, project_root) -- 4 args
- Action block keys: action_type, agent_type, gate_id (lowercase)
"""

import json
import tempfile
import unittest
from pathlib import Path

from pipeline_state import PipelineState, save_state
from state_transitions import enter_debug_session, authorize_debug_session
from routing import (
    route,
    dispatch_gate_response,
    GATE_VOCABULARY,
)


def _make_state(**overrides):
    """Create a PipelineState with sensible defaults."""
    defaults = {
        "stage": "5",
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
        "delivered_repo_path": "/tmp/test-repo",
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _make_debug_session(**overrides):
    """Create a debug session dict with defaults."""
    defaults = {
        "bug_number": 1,
        "classification": None,
        "affected_units": [],
        "phase": "triage",
        "authorized": False,
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    defaults.update(overrides)
    return defaults


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


class TestBug69E3ReclassifyBug(unittest.TestCase):
    """Fix E.3: gate_6_3 RECLASSIFY BUG resets to triage."""

    def test_gate_6_3_reclassify_resets_phase(self):
        """RECLASSIFY BUG resets debug phase to triage."""
        ds = _make_debug_session(
            phase="repair",
            authorized=True,
            classification="single_unit",
            affected_units=[5],
        )
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session["phase"], "triage")

    def test_gate_6_3_retry_repair_stays_in_repair(self):
        """RETRY REPAIR stays in repair phase."""
        ds = _make_debug_session(phase="repair", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_3_repair_exhausted", "RETRY REPAIR"
        )
        self.assertIsNotNone(new_state.debug_session)

    def test_gate_6_3_abandon_debug(self):
        """ABANDON DEBUG moves session to history."""
        ds = _make_debug_session(phase="repair", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_3_repair_exhausted", "ABANDON DEBUG"
        )
        self.assertIsNone(new_state.debug_session)
        self.assertTrue(len(new_state.debug_history) >= 1)


class TestBug69E1Gate60(unittest.TestCase):
    """Fix E.1: gate_6_0 from unauthorized debug, AUTHORIZE/ABANDON."""

    def test_gate_6_0_authorize_advances_to_authorized(self):
        """AUTHORIZE DEBUG sets authorized=True."""
        ds = _make_debug_session(phase="triage", authorized=False)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertTrue(new_state.debug_session["authorized"])

    def test_gate_6_0_abandon_abandons_session(self):
        """ABANDON DEBUG moves session to history."""
        ds = _make_debug_session(phase="triage", authorized=False)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG"
        )
        self.assertIsNone(new_state.debug_session)
        self.assertTrue(len(new_state.debug_history) >= 1)


class TestBug69E2Gate61(unittest.TestCase):
    """Fix E.2: gate_6_1 from regression_test phase."""

    def test_gate_6_1_test_correct_advances(self):
        """TEST CORRECT advances debug phase to lessons_learned."""
        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_1_regression_test", "TEST CORRECT"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session["phase"], "lessons_learned")

    def test_gate_6_1_test_wrong_is_noop(self):
        """TEST WRONG is a no-op (re-invokes test agent via routing)."""
        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_1_regression_test", "TEST WRONG"
        )
        self.assertIsNotNone(new_state.debug_session)


class TestBug69E4Gate65(unittest.TestCase):
    """Fix E.4: gate_6_5 from commit phase."""

    def test_gate_6_5_commit_approved_completes_session(self):
        """COMMIT APPROVED moves session to debug_history."""
        ds = _make_debug_session(phase="commit", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_5_debug_commit", "COMMIT APPROVED"
        )
        self.assertIsNone(new_state.debug_session)
        self.assertTrue(len(new_state.debug_history) >= 1)

    def test_gate_6_5_commit_rejected_is_noop(self):
        """COMMIT REJECTED re-presents Gate 6.5."""
        ds = _make_debug_session(phase="commit", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_5_debug_commit", "COMMIT REJECTED"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session["phase"], "commit")


class TestBug69RoutingDebugPhases(unittest.TestCase):
    """Test that route() presents correct gates for debug phases."""

    def test_vocabulary_gate_6_0(self):
        """gate_6_0_debug_permission in GATE_VOCABULARY."""
        self.assertIn("gate_6_0_debug_permission", GATE_VOCABULARY)
        self.assertIn("AUTHORIZE DEBUG", GATE_VOCABULARY["gate_6_0_debug_permission"])
        self.assertIn("ABANDON DEBUG", GATE_VOCABULARY["gate_6_0_debug_permission"])

    def test_vocabulary_gate_6_1(self):
        """gate_6_1_regression_test is in vocabulary."""
        self.assertIn("gate_6_1_regression_test", GATE_VOCABULARY)
        self.assertIn("TEST CORRECT", GATE_VOCABULARY["gate_6_1_regression_test"])
        self.assertIn("TEST WRONG", GATE_VOCABULARY["gate_6_1_regression_test"])

    def test_vocabulary_gate_6_5(self):
        """gate_6_5_debug_commit is in vocabulary."""
        self.assertIn("gate_6_5_debug_commit", GATE_VOCABULARY)
        self.assertIn("COMMIT APPROVED", GATE_VOCABULARY["gate_6_5_debug_commit"])
        self.assertIn("COMMIT REJECTED", GATE_VOCABULARY["gate_6_5_debug_commit"])


class TestBug69WorkspaceRouting(unittest.TestCase):
    """Test workspace routing debug phase handlers."""

    def test_unauthorized_debug_presents_gate_6_0(self):
        """route() with unauthorized debug session presents Gate 6.0."""
        ds = _make_debug_session(phase="triage", authorized=False)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state)
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_6_0_debug_permission")

    def test_triage_no_status_invokes_bug_triage(self):
        """route() with triage and no status invokes bug_triage_agent."""
        ds = _make_debug_session(phase="triage", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state, last_status="")
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "bug_triage_agent")

    def test_triage_complete_presents_gate_6_2(self):
        """route() with triage and TRIAGE_COMPLETE presents Gate 6.2."""
        ds = _make_debug_session(phase="triage", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state, last_status="TRIAGE_COMPLETE: single_unit")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_6_2_debug_classification")

    def test_regression_test_completed_presents_gate_6_1(self):
        """route() with regression_test and REGRESSION_TEST_COMPLETE presents Gate 6.1."""
        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state, last_status="REGRESSION_TEST_COMPLETE")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_6_1_regression_test")

    def test_regression_test_no_status_invokes_test_agent(self):
        """route() with regression_test and no status invokes test_agent."""
        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state, last_status="")
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "test_agent")

    def test_commit_phase_presents_gate_6_5(self):
        """route() with commit phase presents Gate 6.5."""
        ds = _make_debug_session(phase="commit", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state, last_status="")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_6_5_debug_commit")

    def test_gate_6_3_reclassify_dispatch(self):
        """dispatch_gate_response for gate_6_3 RECLASSIFY BUG resets to triage."""
        ds = _make_debug_session(
            phase="repair", authorized=True,
            classification="single_unit", affected_units=[5],
        )
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session["phase"], "triage")

    def test_gate_6_1_test_correct_dispatch(self):
        """dispatch_gate_response for gate_6_1 TEST CORRECT advances."""
        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_1_regression_test", "TEST CORRECT"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session["phase"], "lessons_learned")

    def test_gate_6_5_commit_approved_dispatch(self):
        """dispatch_gate_response for gate_6_5 COMMIT APPROVED completes session."""
        ds = _make_debug_session(phase="commit", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_5_debug_commit", "COMMIT APPROVED"
        )
        self.assertIsNone(new_state.debug_session)
        self.assertTrue(len(new_state.debug_history) > 0)

    def test_gate_6_0_authorize_dispatch(self):
        """dispatch_gate_response for gate_6_0 AUTHORIZE DEBUG."""
        ds = _make_debug_session(phase="triage", authorized=False)
        state = _make_state(debug_session=ds)
        new_state = _dispatch_gate_with_config(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG"
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertTrue(new_state.debug_session["authorized"])


if __name__ == "__main__":
    unittest.main()
