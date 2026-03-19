"""Bug 17 (2.1) regression: Two-branch routing for agent status and gates.

After an agent completes (last_status is set), routing must present
a human gate rather than re-invoking the agent. This prevents infinite
agent re-invocation loops.
"""

from pathlib import Path

from routing import route
from pipeline_state import PipelineState


def _make_status_file(tmp_path, content="SOME_STATUS"):
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "last_status.txt").write_text(content)


def test_stage0_context_agent_then_gate(tmp_path):
    """Stage 0 project_context: no status -> agent, with status -> gate."""
    state = PipelineState(stage="0", sub_stage="project_context")

    # No last_status -> invoke agent
    action_no_status = route(state, tmp_path)
    assert action_no_status["ACTION"] == "invoke_agent"

    # With last_status -> present gate
    _make_status_file(tmp_path, "PROJECT_CONTEXT_COMPLETE")
    action_with_status = route(state, tmp_path)
    assert action_with_status["ACTION"] == "human_gate"


def test_stage1_dialog_then_gate(tmp_path):
    """Stage 1 (Bug 41): two-branch routing for spec authoring.

    No last_status -> invoke stakeholder_dialog agent.
    With SPEC_DRAFT_COMPLETE status -> present human_gate.
    """
    state = PipelineState(stage="1")

    action_no_status = route(state, tmp_path)
    assert action_no_status["ACTION"] == "invoke_agent"
    assert action_no_status["AGENT"] == "stakeholder_dialog"

    _make_status_file(tmp_path, "SPEC_DRAFT_COMPLETE")
    action_with_status = route(state, tmp_path)
    assert action_with_status["ACTION"] == "human_gate"
    assert action_with_status["GATE_ID"] == "gate_1_1_spec_draft"
