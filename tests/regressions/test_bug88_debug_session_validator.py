"""Debug session structure validation via Unit 6 transition functions.

Bug 88 equivalent: enter_debug_session must produce a well-formed dict,
authorize_debug_session must set authorized=True,
complete_debug_session must clear the session.
"""

from src.unit_5.stub import PipelineState
from src.unit_6.stub import (
    authorize_debug_session,
    complete_debug_session,
    enter_debug_session,
)


def _make_state(**kw):
    defaults = dict(
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=5,
        verified_units=[],
        alignment_iterations=0,
        fix_ladder_position=None,
        red_run_retries=0,
        pass_history=[],
        debug_session=None,
        debug_history=[],
        redo_triggered_from=None,
        delivered_repo_path=None,
        primary_language="python",
        component_languages=[],
        secondary_language=None,
        oracle_session_active=False,
        oracle_test_project=None,
        oracle_phase=None,
        oracle_run_count=0,
        oracle_nested_session_path=None,
        state_hash=None,
        spec_revision_count=0,
        pass_=None,
        pass2_nested_session_path=None,
        deferred_broken_units=[],
    )
    defaults.update(kw)
    return PipelineState(**defaults)


def test_enter_debug_produces_valid_dict():
    """enter_debug_session must produce a dict with all required keys."""
    state = _make_state()
    new = enter_debug_session(state, 1)
    session = new.debug_session
    assert isinstance(session, dict)
    for key in (
        "authorized",
        "bug_number",
        "classification",
        "affected_units",
        "phase",
        "repair_retry_count",
        "triage_refinement_count",
        "ledger_path",
    ):
        assert key in session, f"Missing key '{key}' in debug_session"


def test_enter_debug_sets_bug_number():
    """debug_session.bug_number must match the argument."""
    state = _make_state()
    new = enter_debug_session(state, 42)
    assert new.debug_session["bug_number"] == 42


def test_enter_debug_starts_unauthorized():
    """debug_session.authorized must be False initially."""
    state = _make_state()
    new = enter_debug_session(state, 1)
    assert new.debug_session["authorized"] is False


def test_enter_debug_starts_in_triage():
    """debug_session.phase must be 'triage' initially."""
    state = _make_state()
    new = enter_debug_session(state, 1)
    assert new.debug_session["phase"] == "triage"


def test_authorize_sets_flag():
    """authorize_debug_session must set authorized=True."""
    state = _make_state()
    new = enter_debug_session(state, 1)
    authorized = authorize_debug_session(new)
    assert authorized.debug_session["authorized"] is True


def test_complete_clears_session():
    """complete_debug_session must set debug_session to None."""
    state = _make_state()
    new = enter_debug_session(state, 1)
    new = authorize_debug_session(new)
    done = complete_debug_session(new)
    assert done.debug_session is None


def test_complete_archives_to_history():
    """complete_debug_session must append session to debug_history."""
    state = _make_state()
    new = enter_debug_session(state, 5)
    new = authorize_debug_session(new)
    done = complete_debug_session(new)
    assert len(done.debug_history) == 1
    assert done.debug_history[0]["bug_number"] == 5


def test_enter_debug_does_not_mutate_original():
    """enter_debug_session must return a new state, not mutate the original."""
    state = _make_state()
    assert state.debug_session is None
    _ = enter_debug_session(state, 1)
    assert state.debug_session is None, "Original state was mutated"
