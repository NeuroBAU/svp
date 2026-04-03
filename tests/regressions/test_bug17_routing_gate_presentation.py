"""Bug 17 (2.1) regression: Two-branch routing for agent status and gates.

After an agent completes (last_status is set), routing must present
a human gate rather than re-invoking the agent. This prevents infinite
agent re-invocation loops.

SVP 2.2 adaptation:
- route() takes only project_root; state saved to disk via save_state
- Action block keys lowercase (action_type, agent_type, gate_id)
- PipelineState from src.unit_5.stub
"""

import tempfile
from pathlib import Path

from src.unit_5.stub import PipelineState, save_state
from src.unit_14.stub import route


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


def _make_status_file(tmp_path, content="SOME_STATUS"):
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "last_status.txt").write_text(content)


def test_stage0_context_agent_then_gate():
    """Stage 0 project_context: no status -> agent, with status -> gate."""
    state = PipelineState(stage="0", sub_stage="project_context")

    # No last_status -> invoke agent
    action_no_status = _route_with_state(state, "")
    assert action_no_status["action_type"] == "invoke_agent"

    # With last_status -> present gate
    action_with_status = _route_with_state(state, "PROJECT_CONTEXT_COMPLETE")
    assert action_with_status["action_type"] == "human_gate"


def test_stage1_dialog_then_gate():
    """Stage 1 (Bug 41): two-branch routing for spec authoring.

    No last_status -> invoke stakeholder_dialog agent.
    With SPEC_DRAFT_COMPLETE status -> present human_gate.
    """
    state = PipelineState(stage="1")

    action_no_status = _route_with_state(state, "")
    assert action_no_status["action_type"] == "invoke_agent"
    assert action_no_status["agent_type"] == "stakeholder_dialog"

    action_with_status = _route_with_state(state, "SPEC_DRAFT_COMPLETE")
    assert action_with_status["action_type"] == "human_gate"
    assert action_with_status["gate_id"] == "gate_1_1_spec_draft"
