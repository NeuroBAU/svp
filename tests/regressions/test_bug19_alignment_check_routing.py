"""Bug 19 (2.1) regression: alignment_check sub-stage routing in Stage 2.

When stage == '2' and sub_stage == 'alignment_check', routing must
invoke blueprint_checker (not blueprint_author), and after completion
present a gate.

SVP 2.2 adaptation:
- route() takes only project_root; state saved to disk via save_state
- Action block keys lowercase (action_type, agent_type, gate_id)
- PipelineState from pipeline_state
"""

import tempfile
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import route


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


def test_alignment_check_routes_to_blueprint_checker():
    """Stage 2 alignment_check with no status must invoke blueprint_checker."""
    state = PipelineState(stage="2", sub_stage="alignment_check")
    action = _route_with_state(state)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "blueprint_checker"


def test_alignment_check_with_failure_status_routes_to_gate():
    """Stage 2 alignment_check with ALIGNMENT_FAILED status must present gate.

    SVP 2.2: gate_2_3_alignment_exhausted is only presented when
    alignment_iterations >= iteration_limit (default 3). With fewer
    iterations, route() recurses to re-invoke the checker.
    """
    state = PipelineState(stage="2", sub_stage="alignment_check", alignment_iterations=3)
    action = _route_with_state(state, "ALIGNMENT_FAILED: spec")
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_2_3_alignment_exhausted"


def test_stage2_default_routes_to_blueprint_author():
    """Stage 2 with no sub_stage must invoke blueprint_author."""
    state = PipelineState(stage="2", sub_stage=None)
    action = _route_with_state(state)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "blueprint_author"
