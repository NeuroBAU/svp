"""Bug 41: Stage 1 routing must use two-branch pattern.

Check last_status before presenting gate: no status -> invoke agent,
SPEC_DRAFT_COMPLETE -> present human_gate for gate_1_1.
"""

import tempfile
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import _route_stage_1, route


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


def _call_route_stage_1(state, last_status=""):
    """Call _route_stage_1 directly with a temporary project root."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        return _route_stage_1(state, root, last_status)


def test_no_status_invokes_stakeholder_dialog():
    """With no last_status, Stage 1 must invoke stakeholder_dialog agent."""
    state = PipelineState(stage="1")
    action = _call_route_stage_1(state, "")
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "stakeholder_dialog"


def test_spec_draft_complete_presents_gate():
    """With SPEC_DRAFT_COMPLETE, Stage 1 must present gate_1_1_spec_draft."""
    state = PipelineState(stage="1")
    action = _call_route_stage_1(state, "SPEC_DRAFT_COMPLETE")
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_1_1_spec_draft"


def test_spec_revision_complete_presents_gate():
    """With SPEC_REVISION_COMPLETE, Stage 1 must present gate_1_1_spec_draft."""
    state = PipelineState(stage="1")
    action = _call_route_stage_1(state, "SPEC_REVISION_COMPLETE")
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_1_1_spec_draft"


def test_review_complete_presents_post_review_gate():
    """With REVIEW_COMPLETE, Stage 1 must present gate_1_2_spec_post_review."""
    state = PipelineState(stage="1")
    action = _call_route_stage_1(state, "REVIEW_COMPLETE")
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_1_2_spec_post_review"


def test_two_branch_via_full_route():
    """Full route() call must also respect the two-branch pattern for Stage 1."""
    state = PipelineState(stage="1")

    # No status -> agent
    action_no_status = _route_with_state(state, "")
    assert action_no_status["action_type"] == "invoke_agent"

    # With status -> gate
    action_with_status = _route_with_state(state, "SPEC_DRAFT_COMPLETE")
    assert action_with_status["action_type"] == "human_gate"
