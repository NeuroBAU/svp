"""Bug 7 regression: Unit completion must write marker before state update.

complete_unit must write the marker file to disk (markers/unit_N_verified)
before returning the updated state, so the marker exists for any subsequent
state recovery.
"""

from pathlib import Path

from state_transitions import complete_unit
from pipeline_state import PipelineState


def test_marker_file_written_on_completion(tmp_path):
    """complete_unit must create the marker file."""
    markers_dir = tmp_path / ".svp" / "markers"
    markers_dir.mkdir(parents=True)

    state = PipelineState(
        stage="3",
        sub_stage="unit_completion",
        current_unit=1,
        total_units=3,
    )
    new_state = complete_unit(state, 1, tmp_path)
    marker = markers_dir / "unit_1_verified"
    assert marker.exists(), "Marker file must be written before state update returns"
    content = marker.read_text()
    assert "VERIFIED" in content
