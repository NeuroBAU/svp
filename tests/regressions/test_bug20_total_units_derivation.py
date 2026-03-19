"""Bug 20 (2.1) regression: total_units must be derived from blueprint.

total_units is stored in pipeline state and used for completion checks.
It must be set from the blueprint extraction, not hardcoded or assumed.
The state schema must support total_units as Optional[int].
"""

from pipeline_state import PipelineState


def test_total_units_defaults_to_none():
    """PipelineState.total_units must default to None."""
    state = PipelineState(stage="3")
    assert state.total_units is None


def test_total_units_can_be_set():
    """total_units must be settable to an integer."""
    state = PipelineState(stage="3", total_units=24)
    assert state.total_units == 24


def test_total_units_roundtrips_through_dict():
    """total_units must survive to_dict/from_dict roundtrip."""
    state = PipelineState(stage="3", total_units=15)
    data = state.to_dict()
    assert data["total_units"] == 15
    restored = PipelineState.from_dict(data)
    assert restored.total_units == 15
