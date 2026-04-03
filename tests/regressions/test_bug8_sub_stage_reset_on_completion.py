"""Bug 8 regression: sub_stage must reset to None on unit completion.

When a unit is completed, the sub_stage must be reset to None for the
next unit, not carried forward from the previous unit.

SVP 2.2 adaptation:
- complete_unit(state) takes 1 arg (state must have sub_stage=unit_completion)
- PipelineState from src.unit_5.stub
- complete_unit from src.unit_6.stub
"""

from src.unit_5.stub import PipelineState
from src.unit_6.stub import complete_unit


def test_sub_stage_resets_on_unit_completion():
    """After complete_unit, sub_stage must be stub_generation for next unit."""
    state = PipelineState(
        stage="3",
        sub_stage="unit_completion",
        current_unit=1,
        total_units=3,
    )
    new_state = complete_unit(state)
    # SVP 2.2: after completing unit 1, next unit starts at stub_generation
    assert new_state.sub_stage == "stub_generation", (
        "sub_stage must be stub_generation for next unit after unit completion"
    )
    assert new_state.current_unit == 2, "current_unit must advance"
