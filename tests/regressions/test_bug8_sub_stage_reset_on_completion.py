"""Regression tests for Bug 8: sub_stage not reset when completing a unit.

complete_unit must reset sub_stage to None when advancing to the next unit.
Without this reset, the next unit inherits sub_stage="unit_completion" from
the previous unit, causing routing to immediately re-complete the new unit
without building it (no test_generation, no stubs, no implementation).

DATA ASSUMPTION: PipelineState is constructed synthetically. Marker files
are written to tmp_path to satisfy complete_unit's preconditions.
"""

import pytest
from pathlib import Path

from svp.scripts.state_transitions import complete_unit, TransitionError
from svp.scripts.pipeline_state import PipelineState


def _make_state(**overrides) -> PipelineState:
    """Create a PipelineState in Stage 3 with sensible defaults."""
    defaults = dict(
        stage="3",
        sub_stage="unit_completion",
        current_unit=1,
        total_units=3,
        fix_ladder_position=None,
        red_run_retries=0,
        alignment_iteration=0,
        verified_units=[],
        pass_history=[],
        log_references={},
        project_name="test_project",
        last_action="Green run passed",
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestSubStageResetOnCompletion:
    """Bug 8: complete_unit must reset sub_stage to None."""

    def test_sub_stage_reset_to_none_after_completion(self, tmp_path):
        """After completing unit 1, sub_stage must be None, not 'unit_completion'."""
        state = _make_state(current_unit=1)
        new_state = complete_unit(state, 1, tmp_path)

        assert new_state.sub_stage is None, (
            "sub_stage must be reset to None after unit completion. "
            f"Got: {new_state.sub_stage!r}"
        )

    def test_current_unit_advances(self, tmp_path):
        """After completing unit 1, current_unit should be 2."""
        state = _make_state(current_unit=1)
        new_state = complete_unit(state, 1, tmp_path)

        assert new_state.current_unit == 2

    def test_sub_stage_reset_on_middle_unit(self, tmp_path):
        """sub_stage reset works for middle units (not just first or last)."""
        state = _make_state(
            current_unit=2,
            verified_units=[{"unit": 1, "timestamp": "2026-01-01T00:00:00"}],
        )
        new_state = complete_unit(state, 2, tmp_path)

        assert new_state.sub_stage is None
        assert new_state.current_unit == 3

    def test_sub_stage_reset_on_final_unit(self, tmp_path):
        """When completing the final unit, sub_stage is also reset."""
        state = _make_state(
            current_unit=3,
            total_units=3,
            verified_units=[
                {"unit": 1, "timestamp": "2026-01-01T00:00:00"},
                {"unit": 2, "timestamp": "2026-01-01T01:00:00"},
            ],
        )
        new_state = complete_unit(state, 3, tmp_path)

        assert new_state.sub_stage is None

    def test_fix_ladder_also_reset(self, tmp_path):
        """fix_ladder_position is reset alongside sub_stage."""
        state = _make_state(current_unit=1, fix_ladder_position="fresh_impl")
        new_state = complete_unit(state, 1, tmp_path)

        assert new_state.fix_ladder_position is None

    def test_red_run_retries_also_reset(self, tmp_path):
        """red_run_retries is reset alongside sub_stage."""
        state = _make_state(current_unit=1, red_run_retries=2)
        new_state = complete_unit(state, 1, tmp_path)

        assert new_state.red_run_retries == 0


class TestMultiUnitSequence:
    """Verify that completing units in sequence maintains correct sub_stage."""

    def test_sequential_completion_resets_sub_stage_each_time(self, tmp_path):
        """Completing units 1, 2, 3 in sequence always resets sub_stage."""
        state = _make_state(current_unit=1, total_units=3)

        # Complete unit 1
        state = complete_unit(state, 1, tmp_path)
        assert state.sub_stage is None, "sub_stage not reset after unit 1"
        assert state.current_unit == 2

        # Simulate processing unit 2 (set sub_stage back to unit_completion)
        state.sub_stage = "unit_completion"

        # Complete unit 2
        state = complete_unit(state, 2, tmp_path)
        assert state.sub_stage is None, "sub_stage not reset after unit 2"
        assert state.current_unit == 3

        # Simulate processing unit 3
        state.sub_stage = "unit_completion"

        # Complete unit 3 (final)
        state = complete_unit(state, 3, tmp_path)
        assert state.sub_stage is None, "sub_stage not reset after final unit"
