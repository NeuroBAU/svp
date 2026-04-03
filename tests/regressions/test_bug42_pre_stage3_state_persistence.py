"""Bug 42: State transition to pre_stage_3 preserves alignment fields.

advance_stage to pre_stage_3 must preserve alignment_iterations (not reset it).
"""

from src.unit_5.stub import PipelineState
from src.unit_6.stub import advance_stage


def _make_state(**kw):
    defaults = dict(
        stage="2",
        sub_stage="alignment_confirmed",
        current_unit=None,
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


def test_advance_to_pre_stage3_preserves_alignment_iterations():
    """alignment_iterations must survive transition to pre_stage_3."""
    state = _make_state(alignment_iterations=3)
    new = advance_stage(state, "pre_stage_3")
    assert new.alignment_iterations == 3, (
        f"Expected alignment_iterations=3, got {new.alignment_iterations}"
    )


def test_advance_to_pre_stage3_preserves_zero_iterations():
    """alignment_iterations=0 must also be preserved (not accidentally set)."""
    state = _make_state(alignment_iterations=0)
    new = advance_stage(state, "pre_stage_3")
    assert new.alignment_iterations == 0


def test_advance_to_pre_stage3_sets_stage():
    """advance_stage must set stage to 'pre_stage_3'."""
    state = _make_state()
    new = advance_stage(state, "pre_stage_3")
    assert new.stage == "pre_stage_3"


def test_advance_to_pre_stage3_resets_sub_stage():
    """advance_stage resets sub_stage to None."""
    state = _make_state(sub_stage="alignment_confirmed")
    new = advance_stage(state, "pre_stage_3")
    assert new.sub_stage is None


def test_advance_to_pre_stage3_preserves_verified_units():
    """verified_units must survive transition to pre_stage_3."""
    verified = [{"unit": 1, "timestamp": "2025-01-01T00:00:00Z"}]
    state = _make_state(verified_units=verified)
    new = advance_stage(state, "pre_stage_3")
    assert new.verified_units == verified


def test_advance_to_pre_stage3_preserves_total_units():
    """total_units must survive transition to pre_stage_3."""
    state = _make_state(total_units=7)
    new = advance_stage(state, "pre_stage_3")
    assert new.total_units == 7


def test_advance_to_pre_stage3_does_not_mutate_original():
    """advance_stage must return a new state, not mutate the original."""
    state = _make_state(alignment_iterations=3)
    _ = advance_stage(state, "pre_stage_3")
    assert state.stage == "2", "Original state was mutated"
