"""Regression tests for Bug S3-15: oracle session lifecycle functions."""
import pytest

from pipeline_state import PipelineState
from state_transitions import (
    enter_oracle_session, complete_oracle_session, abandon_oracle_session, TransitionError
)


def _make_state(**overrides):
    defaults = dict(
        stage="5", sub_stage="repo_complete", current_unit=None, total_units=29,
        verified_units=[], fix_ladder_position=None, red_run_retries=0,
        alignment_iterations=0, pass_history=[], debug_session=None,
        debug_history=[], redo_triggered_from=None, delivered_repo_path=None,
        oracle_session_active=False, oracle_phase=None,
        oracle_test_project=None, oracle_run_count=0, oracle_nested_session_path=None,
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


def test_enter_oracle_session_activates():
    state = _make_state()
    new = enter_oracle_session(state, "docs/")
    assert new.oracle_session_active is True
    assert new.oracle_phase == "dry_run"
    assert new.oracle_test_project == "docs/"
    assert new.oracle_run_count == 1


def test_enter_oracle_session_increments_run_count():
    state = _make_state(oracle_run_count=3)
    new = enter_oracle_session(state, "docs/")
    assert new.oracle_run_count == 4


def test_enter_oracle_session_raises_if_already_active():
    state = _make_state(oracle_session_active=True)
    with pytest.raises(TransitionError):
        enter_oracle_session(state, "docs/")


def test_complete_oracle_session_deactivates():
    state = _make_state(oracle_session_active=True, oracle_phase="exit", oracle_test_project="docs/")
    new = complete_oracle_session(state, "all_clear")
    assert new.oracle_session_active is False
    assert new.oracle_phase is None
    assert new.oracle_test_project is None


def test_complete_oracle_session_raises_if_not_active():
    state = _make_state(oracle_session_active=False)
    with pytest.raises(TransitionError):
        complete_oracle_session(state, "all_clear")


def test_abandon_oracle_session_deactivates():
    state = _make_state(oracle_session_active=True, oracle_phase="gate_a")
    new = abandon_oracle_session(state)
    assert new.oracle_session_active is False


def test_abandon_oracle_session_raises_if_not_active():
    state = _make_state(oracle_session_active=False)
    with pytest.raises(TransitionError):
        abandon_oracle_session(state)


def test_enter_oracle_preserves_immutability():
    state = _make_state()
    new = enter_oracle_session(state, "docs/")
    assert state.oracle_session_active is False  # original unchanged
    assert new.oracle_session_active is True
