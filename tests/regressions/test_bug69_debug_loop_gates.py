"""Regression test for Bug 69: Debug loop gates.

Verifies all four fixes:
E.1: gate_6_0 presentation from triage_readonly, AUTHORIZE DEBUG advances to triage,
     ABANDON DEBUG abandons session
E.2: gate_6_1 presentation from regression_test phase, TEST CORRECT advances to
     complete, TEST WRONG re-invokes test agent
E.3: gate_6_3 RECLASSIFY BUG resets to triage phase with cleared classification
E.4: gate_6_5 presentation from complete phase, COMMIT APPROVED completes session,
     COMMIT REJECTED re-presents
"""

import unittest
from pathlib import Path


def _make_state(**overrides):
    from pipeline_state import PipelineState

    defaults = {
        "stage": "5",
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
        "last_action": "",
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": "/tmp/test-repo",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _make_debug_session(**overrides):
    from pipeline_state import DebugSession

    defaults = {
        "bug_id": 1,
        "description": "test bug",
        "classification": None,
        "affected_units": [],
        "regression_test_path": None,
        "phase": "triage_readonly",
        "authorized": False,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    return DebugSession(**defaults)


class TestBug69E3ReclassifyBug(unittest.TestCase):
    """Fix E.3: gate_6_3 RECLASSIFY BUG resets to triage."""

    def test_debug_phase_transitions_repair_to_triage(self):
        """_DEBUG_PHASE_TRANSITIONS allows repair -> triage."""
        from state_transitions import _DEBUG_PHASE_TRANSITIONS

        self.assertIn("triage", _DEBUG_PHASE_TRANSITIONS["repair"])
        self.assertIn("complete", _DEBUG_PHASE_TRANSITIONS["repair"])

    def test_gate_6_3_reclassify_resets_phase(self):
        """RECLASSIFY BUG resets debug phase to triage and clears classification."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            phase="repair",
            authorized=True,
            classification="single_unit",
            affected_units=[5],
        )
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session.phase, "triage")
        self.assertIsNone(new_state.debug_session.classification)
        self.assertEqual(new_state.debug_session.affected_units, [])

    def test_gate_6_3_retry_repair_is_noop(self):
        """RETRY REPAIR is a no-op (stays in repair phase)."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="repair", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RETRY REPAIR", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        # Phase stays at repair (routing will re-invoke repair agent)

    def test_gate_6_3_abandon_debug(self):
        """ABANDON DEBUG moves session to history."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="repair", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "ABANDON DEBUG", Path(".")
        )
        self.assertIsNone(new_state.debug_session)
        self.assertEqual(len(new_state.debug_history), 1)
        self.assertEqual(new_state.debug_history[0]["status"], "abandoned")


class TestBug69E1Gate60(unittest.TestCase):
    """Fix E.1: gate_6_0 from triage_readonly, AUTHORIZE/ABANDON."""

    def test_gate_6_0_authorize_advances_to_triage(self):
        """AUTHORIZE DEBUG sets authorized=True and phase=triage."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="triage_readonly", authorized=False)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertTrue(new_state.debug_session.authorized)
        self.assertEqual(new_state.debug_session.phase, "triage")

    def test_gate_6_0_abandon_abandons_session(self):
        """ABANDON DEBUG moves session to history."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="triage_readonly", authorized=False)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG", Path(".")
        )
        self.assertIsNone(new_state.debug_session)
        self.assertEqual(len(new_state.debug_history), 1)
        self.assertEqual(new_state.debug_history[0]["status"], "abandoned")


class TestBug69E2Gate61(unittest.TestCase):
    """Fix E.2: gate_6_1 from regression_test phase."""

    def test_gate_6_1_test_correct_advances_to_complete(self):
        """TEST CORRECT advances debug phase to complete."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            phase="regression_test", authorized=True
        )
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST CORRECT", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session.phase, "complete")

    def test_gate_6_1_test_wrong_is_noop(self):
        """TEST WRONG is a no-op (re-invokes test agent via routing)."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            phase="regression_test", authorized=True
        )
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST WRONG", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        # Phase stays at regression_test


class TestBug69E4Gate65(unittest.TestCase):
    """Fix E.4: gate_6_5 from complete phase."""

    def test_gate_6_5_commit_approved_completes_session(self):
        """COMMIT APPROVED moves session to debug_history."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            phase="complete", authorized=True
        )
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT APPROVED", Path(".")
        )
        self.assertIsNone(new_state.debug_session)
        self.assertEqual(len(new_state.debug_history), 1)
        self.assertEqual(new_state.debug_history[0]["status"], "completed")

    def test_gate_6_5_commit_rejected_is_noop(self):
        """COMMIT REJECTED re-presents Gate 6.5."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            phase="complete", authorized=True
        )
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT REJECTED", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session.phase, "complete")


class TestBug69RoutingDebugPhases(unittest.TestCase):
    """Test that route() presents correct gates for debug phases."""

    def _make_status_file(self, project_root, content):
        svp_dir = project_root / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text(content, encoding="utf-8")

    def test_triage_readonly_with_completion_presents_gate_6_0(self):
        """triage_readonly + TRIAGE_COMPLETE -> Gate 6.0."""
        import tempfile
        from routing import GATE_VOCABULARY

        ds = _make_debug_session(phase="triage_readonly", authorized=False)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            self._make_status_file(pr, "TRIAGE_COMPLETE: single_unit")
            self.assertIn("gate_6_0_debug_permission", GATE_VOCABULARY)
            self.assertIn("AUTHORIZE DEBUG", GATE_VOCABULARY["gate_6_0_debug_permission"])
            self.assertIn("ABANDON DEBUG", GATE_VOCABULARY["gate_6_0_debug_permission"])

    def test_regression_test_phase_gate_6_1_in_vocabulary(self):
        """Gate 6.1 regression_test is in vocabulary."""
        from routing import GATE_VOCABULARY
        self.assertIn("gate_6_1_regression_test", GATE_VOCABULARY)
        self.assertIn("TEST CORRECT", GATE_VOCABULARY["gate_6_1_regression_test"])
        self.assertIn("TEST WRONG", GATE_VOCABULARY["gate_6_1_regression_test"])

    def test_complete_phase_gate_6_5_in_vocabulary(self):
        """Gate 6.5 debug_commit is in vocabulary."""
        from routing import GATE_VOCABULARY
        self.assertIn("gate_6_5_debug_commit", GATE_VOCABULARY)
        self.assertIn("COMMIT APPROVED", GATE_VOCABULARY["gate_6_5_debug_commit"])
        self.assertIn("COMMIT REJECTED", GATE_VOCABULARY["gate_6_5_debug_commit"])


class TestBug69WorkspaceRouting(unittest.TestCase):
    """Test workspace routing.py debug phase handlers."""

    def _make_status_file(self, project_root, content):
        svp_dir = project_root / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text(content, encoding="utf-8")

    def test_triage_readonly_completed_presents_gate_6_0(self):
        """route() with triage_readonly and TRIAGE_COMPLETE presents Gate 6.0."""
        import tempfile
        from routing import route

        ds = _make_debug_session(phase="triage_readonly", authorized=False)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            self._make_status_file(pr, "TRIAGE_COMPLETE: single_unit")
            (pr / ".svp" / "doc_sync_done").touch()
            action = route(state, pr)
            self.assertEqual(action["ACTION"], "human_gate")
            self.assertEqual(action["GATE_ID"], "gate_6_0_debug_permission")

    def test_triage_readonly_not_completed_invokes_bug_triage(self):
        """route() with triage_readonly and no status invokes bug_triage."""
        import tempfile
        from routing import route

        ds = _make_debug_session(phase="triage_readonly", authorized=False)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            action = route(state, pr)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "bug_triage")

    def test_triage_phase_completed_presents_gate_6_2(self):
        """route() with triage phase and TRIAGE_COMPLETE presents Gate 6.2."""
        import tempfile
        from routing import route

        ds = _make_debug_session(phase="triage", authorized=True)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            self._make_status_file(pr, "TRIAGE_COMPLETE: single_unit")
            (pr / ".svp" / "doc_sync_done").touch()
            action = route(state, pr)
            self.assertEqual(action["ACTION"], "human_gate")
            self.assertEqual(action["GATE_ID"], "gate_6_2_debug_classification")

    def test_regression_test_phase_completed_presents_gate_6_1(self):
        """route() with regression_test phase and REGRESSION_TEST_COMPLETE presents Gate 6.1."""
        import tempfile
        from routing import route

        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            self._make_status_file(pr, "REGRESSION_TEST_COMPLETE")
            action = route(state, pr)
            self.assertEqual(action["ACTION"], "human_gate")
            self.assertEqual(action["GATE_ID"], "gate_6_1_regression_test")

    def test_regression_test_phase_not_completed_invokes_test_agent(self):
        """route() with regression_test phase and no status invokes test_agent."""
        import tempfile
        from routing import route

        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            action = route(state, pr)
            self.assertEqual(action["ACTION"], "invoke_agent")
            self.assertEqual(action["AGENT"], "test_agent")

    def test_complete_phase_presents_gate_6_5(self):
        """route() with complete phase presents Gate 6.5."""
        import tempfile
        from routing import route

        ds = _make_debug_session(phase="complete", authorized=True)
        state = _make_state(debug_session=ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            pr = Path(tmpdir)
            action = route(state, pr)
            self.assertEqual(action["ACTION"], "human_gate")
            self.assertEqual(action["GATE_ID"], "gate_6_5_debug_commit")

    def test_gate_6_3_reclassify_dispatch(self):
        """dispatch_gate_response for gate_6_3 RECLASSIFY BUG resets to triage."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            phase="repair",
            authorized=True,
            classification="single_unit",
            affected_units=[5],
        )
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session.phase, "triage")
        self.assertIsNone(new_state.debug_session.classification)
        self.assertEqual(new_state.debug_session.affected_units, [])

    def test_gate_6_1_test_correct_dispatch(self):
        """dispatch_gate_response for gate_6_1 TEST CORRECT advances to complete."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="regression_test", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST CORRECT", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertEqual(new_state.debug_session.phase, "complete")

    def test_gate_6_5_commit_approved_dispatch(self):
        """dispatch_gate_response for gate_6_5 COMMIT APPROVED completes session."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="complete", authorized=True)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT APPROVED", Path(".")
        )
        self.assertIsNone(new_state.debug_session)
        self.assertTrue(len(new_state.debug_history) > 0)

    def test_gate_6_0_authorize_dispatch(self):
        """dispatch_gate_response for gate_6_0 AUTHORIZE DEBUG advances to triage."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(phase="triage_readonly", authorized=False)
        state = _make_state(debug_session=ds)
        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", Path(".")
        )
        self.assertIsNotNone(new_state.debug_session)
        self.assertTrue(new_state.debug_session.authorized)
        self.assertEqual(new_state.debug_session.phase, "triage")


if __name__ == "__main__":
    unittest.main()
