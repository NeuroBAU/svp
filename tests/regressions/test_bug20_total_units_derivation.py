"""Bug 20 (2.1) regression: total_units must be derived from blueprint.

total_units is stored in pipeline state and used for completion checks.
It must be set from the blueprint extraction, not hardcoded or assumed.
The state schema must support total_units as int (default 0).

SVP 2.2 adaptation:
- PipelineState from src.unit_5.stub
- total_units defaults to 0 (not None) in SVP 2.2
- No to_dict/from_dict; use dataclasses.asdict for serialization
"""

from dataclasses import asdict

from src.unit_5.stub import PipelineState


def test_total_units_defaults_to_zero():
    """PipelineState.total_units must default to 0."""
    state = PipelineState(stage="3")
    assert state.total_units == 0


def test_total_units_can_be_set():
    """total_units must be settable to an integer."""
    state = PipelineState(stage="3", total_units=24)
    assert state.total_units == 24


def test_total_units_roundtrips_through_dict():
    """total_units must survive asdict roundtrip."""
    state = PipelineState(stage="3", total_units=15)
    data = asdict(state)
    assert data["total_units"] == 15
    restored = PipelineState(**{k: v for k, v in data.items() if k != "pass_"})
    assert restored.total_units == 15
