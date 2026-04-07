"""Bug 15 regression: Gate prepare flags must match gate IDs.

Every gate ID in GATE_VOCABULARY must be a valid gate that routing
can actually emit, and vice versa.

SVP 2.2 adaptation:
- GATE_VOCABULARY from routing
- route() takes only project_root; state saved to disk via save_state
- Action block keys lowercase (gate_id)
- PipelineState from pipeline_state
"""

import tempfile
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import GATE_VOCABULARY, route


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


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


def test_stage0_hook_activation_gate_matches_vocabulary():
    """Stage 0 hook_activation must route to a gate in GATE_VOCABULARY."""
    state = PipelineState(stage="0", sub_stage="hook_activation")
    action = _route_with_state(state)
    assert action["gate_id"] in GATE_VOCABULARY
