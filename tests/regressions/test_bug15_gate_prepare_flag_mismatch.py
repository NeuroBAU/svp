"""Bug 15 regression: Gate prepare flags must match gate IDs.

Every gate ID in GATE_VOCABULARY must be a valid gate that routing
can actually emit, and vice versa.
"""

from routing import GATE_VOCABULARY, route
from pipeline_state import PipelineState


def test_gate_vocabulary_keys_are_strings():
    """All gate IDs must be strings."""
    for key in GATE_VOCABULARY:
        assert isinstance(key, str), f"Gate ID must be a string, got {type(key)}"


def test_gate_vocabulary_values_are_lists():
    """All gate options must be lists of strings."""
    for gate_id, options in GATE_VOCABULARY.items():
        assert isinstance(options, list), f"Gate {gate_id} options must be a list"
        for opt in options:
            assert isinstance(opt, str), f"Gate {gate_id} option must be a string"


def test_stage0_hook_activation_gate_matches_vocabulary(tmp_path):
    """Stage 0 hook_activation must route to a gate in GATE_VOCABULARY."""
    state = PipelineState(stage="0", sub_stage="hook_activation")
    # Create a minimal project root
    (tmp_path / ".svp").mkdir()
    action = route(state, tmp_path)
    assert action["GATE_ID"] in GATE_VOCABULARY
