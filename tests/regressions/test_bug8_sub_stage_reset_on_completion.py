"""Bug 8 regression: sub_stage must reset to None on unit completion.

When a unit is completed, the sub_stage must be reset to None for the
next unit, not carried forward from the previous unit.
"""

from pathlib import Path

from state_transitions import complete_unit
from pipeline_state import PipelineState


def test_sub_stage_resets_on_unit_completion(tmp_path):
    """After complete_unit, sub_stage must be None for next unit."""
    markers_dir = tmp_path / ".svp" / "markers"
    markers_dir.mkdir(parents=True)

    state = PipelineState(
        stage="3",
        sub_stage="unit_completion",
        current_unit=1,
        total_units=3,
    )
    new_state = complete_unit(state, 1, tmp_path)
    assert new_state.sub_stage is None, "sub_stage must reset to None after unit completion"
    assert new_state.current_unit == 2, "current_unit must advance"
