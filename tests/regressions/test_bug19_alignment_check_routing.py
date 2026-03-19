"""Bug 19 (2.1) regression: alignment_check sub-stage routing in Stage 2.

When stage == '2' and sub_stage == 'alignment_check', routing must
invoke blueprint_checker (not blueprint_author), and after completion
present a gate.
"""

from pathlib import Path

from routing import route
from pipeline_state import PipelineState


def test_alignment_check_routes_to_blueprint_checker(tmp_path):
    """Stage 2 alignment_check with no status must invoke blueprint_checker."""
    state = PipelineState(stage="2", sub_stage="alignment_check")
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "blueprint_checker"


def test_alignment_check_with_failure_status_routes_to_gate(tmp_path):
    """Stage 2 alignment_check with ALIGNMENT_FAILED status must present gate."""
    state = PipelineState(stage="2", sub_stage="alignment_check")
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "last_status.txt").write_text("ALIGNMENT_FAILED: spec")
    action = route(state, tmp_path)
    assert action["ACTION"] == "human_gate"
    assert action["GATE_ID"] == "gate_2_3_alignment_exhausted"


def test_stage2_default_routes_to_blueprint_author(tmp_path):
    """Stage 2 with no sub_stage must invoke blueprint_author."""
    state = PipelineState(stage="2", sub_stage=None)
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "blueprint_author"
