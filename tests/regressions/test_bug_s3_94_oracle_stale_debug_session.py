"""Regression tests for Bug S3-94: Oracle session exit must clear stale debug_session.

complete_oracle_session and abandon_oracle_session must clear any existing
debug_session (appending to debug_history with abandoned=True) so that
subsequent enter_debug_session calls do not raise TransitionError.
"""

import pytest

from pipeline_state import PipelineState
from state_transitions import (
    abandon_oracle_session,
    complete_oracle_session,
    enter_debug_session,
    enter_oracle_session,
    TransitionError,
)


def _make_state(**overrides):
    defaults = {
        "stage": "5",
        "sub_stage": "pass_transition",
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "oracle_modification_count": 0,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _oracle_state_with_debug():
    """Create state mimicking gate_7_b APPROVE FIX: oracle active + debug_session."""
    state = _make_state(
        oracle_session_active=True,
        oracle_test_project="examples/gol-plugin/",
        oracle_phase="green_run",
        oracle_run_count=7,
    )
    state = enter_debug_session(state, 7)
    return state


class TestCompleteOracleSessionClearsDebugSession:
    """complete_oracle_session must clear any existing debug_session."""

    def test_clears_debug_session(self):
        state = _oracle_state_with_debug()
        assert state.debug_session is not None
        new = complete_oracle_session(state, "all_clear")
        assert new.debug_session is None

    def test_appends_to_debug_history(self):
        state = _oracle_state_with_debug()
        assert len(state.debug_history) == 0
        new = complete_oracle_session(state, "all_clear")
        assert len(new.debug_history) == 1
        assert new.debug_history[0]["abandoned"] is True
        assert new.debug_history[0]["bug_number"] == 7

    def test_clears_oracle_fields(self):
        state = _oracle_state_with_debug()
        new = complete_oracle_session(state, "all_clear")
        assert new.oracle_session_active is False
        assert new.oracle_phase is None
        assert new.oracle_test_project is None
        assert new.oracle_nested_session_path is None


class TestAbandonOracleSessionClearsDebugSession:
    """abandon_oracle_session must clear any existing debug_session."""

    def test_clears_debug_session(self):
        state = _oracle_state_with_debug()
        assert state.debug_session is not None
        new = abandon_oracle_session(state)
        assert new.debug_session is None

    def test_appends_to_debug_history(self):
        state = _oracle_state_with_debug()
        new = abandon_oracle_session(state)
        assert len(new.debug_history) == 1
        assert new.debug_history[0]["abandoned"] is True

    def test_clears_oracle_fields(self):
        state = _oracle_state_with_debug()
        new = abandon_oracle_session(state)
        assert new.oracle_session_active is False
        assert new.oracle_phase is None


class TestOracleExitWithoutDebugSessionUnchanged:
    """Oracle exit functions work correctly when no debug_session exists."""

    def test_complete_no_debug_session(self):
        state = _make_state(
            oracle_session_active=True,
            oracle_test_project="examples/game-of-life/",
            oracle_phase="green_run",
            oracle_run_count=1,
        )
        assert state.debug_session is None
        new = complete_oracle_session(state, "all_clear")
        assert new.debug_session is None
        assert new.oracle_session_active is False
        assert len(new.debug_history) == 0

    def test_abandon_no_debug_session(self):
        state = _make_state(
            oracle_session_active=True,
            oracle_test_project="examples/game-of-life/",
            oracle_phase="green_run",
            oracle_run_count=1,
        )
        assert state.debug_session is None
        new = abandon_oracle_session(state)
        assert new.debug_session is None
        assert new.oracle_session_active is False
        assert len(new.debug_history) == 0


class TestFIXBUGSAfterOracleWithFixApplied:
    """End-to-end: after oracle exit with stale debug, FIX BUGS must succeed."""

    def test_enter_debug_after_complete_oracle(self):
        """complete_oracle_session clears debug, then enter_debug_session succeeds."""
        state = _oracle_state_with_debug()
        state = complete_oracle_session(state, "all_clear")
        assert state.debug_session is None
        # This should NOT raise
        new = enter_debug_session(state, 0)
        assert new.debug_session is not None
        assert new.debug_session["bug_number"] == 0

    def test_enter_debug_after_abandon_oracle(self):
        """abandon_oracle_session clears debug, then enter_debug_session succeeds."""
        state = _oracle_state_with_debug()
        state = abandon_oracle_session(state)
        assert state.debug_session is None
        new = enter_debug_session(state, 0)
        assert new.debug_session is not None

    def test_without_fix_would_raise(self):
        """Verify the original bug: without cleanup, enter_debug_session raises."""
        # Simulate the pre-fix behavior by manually constructing stale state
        state = _make_state(
            oracle_session_active=False,
            oracle_phase=None,
            oracle_test_project=None,
            debug_session={
                "authorized": False,
                "bug_number": 7,
                "classification": None,
                "affected_units": [],
                "phase": "triage",
                "repair_retry_count": 0,
                "triage_refinement_count": 0,
                "ledger_path": None,
            },
        )
        with pytest.raises(TransitionError, match="already active"):
            enter_debug_session(state, 0)
