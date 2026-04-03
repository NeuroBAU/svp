"""Bug 11: complete_unit must update verified_units and reset current_unit."""

from src.unit_5.stub import PipelineState
from src.unit_6.stub import complete_unit


def _make_state(**kw):
    defaults = dict(
        stage="3",
        sub_stage="unit_completion",
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


def test_complete_unit_adds_to_verified():
    """Completing a unit must add a record with the unit number to verified_units."""
    state = _make_state(current_unit=3)
    new = complete_unit(state)
    assert any(v["unit"] == 3 for v in new.verified_units), (
        f"Expected unit 3 in verified_units, got {new.verified_units}"
    )


def test_complete_unit_resets_current_when_last():
    """After completing the last unit, current_unit must be None."""
    state = _make_state(current_unit=5, total_units=5)
    new = complete_unit(state)
    assert new.current_unit is None


def test_complete_unit_advances_to_next():
    """After completing a non-last unit, current_unit advances to next."""
    state = _make_state(current_unit=3, total_units=5)
    new = complete_unit(state)
    assert new.current_unit == 4


def test_complete_unit_resets_fix_ladder():
    """complete_unit must reset fix_ladder_position to None."""
    state = _make_state(current_unit=2, fix_ladder_position="fresh_impl")
    new = complete_unit(state)
    assert new.fix_ladder_position is None


def test_complete_unit_resets_red_run_retries():
    """complete_unit must reset red_run_retries to 0."""
    state = _make_state(current_unit=2, red_run_retries=3)
    new = complete_unit(state)
    assert new.red_run_retries == 0


def test_complete_unit_does_not_mutate_original():
    """complete_unit must return a new state, not mutate the original."""
    state = _make_state(current_unit=3)
    original_unit = state.current_unit
    _ = complete_unit(state)
    assert state.current_unit == original_unit, "Original state was mutated"
