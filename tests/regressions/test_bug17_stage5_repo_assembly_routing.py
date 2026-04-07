"""Bug 17 (2.1) Stage 5 regression: sub-stage routing order.

Stage 5 must route through sub-stages:
None -> git_repo_agent
repo_test -> gate_5_1_repo_test
compliance_scan -> run_command
repo_complete -> pipeline_complete

SVP 2.2 adaptation:
- route() takes only project_root; state saved to disk via save_state
- Action block keys lowercase (action_type, agent_type, gate_id, command)
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


def test_stage5_none_routes_to_git_repo_agent():
    """Stage 5 with no sub_stage must invoke git_repo_agent."""
    state = PipelineState(stage="5", sub_stage=None)
    action = _route_with_state(state)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "git_repo_agent"


def test_stage5_repo_test_routes_to_gate():
    """Stage 5 repo_test must present gate_5_1_repo_test."""
    state = PipelineState(stage="5", sub_stage="repo_test")
    action = _route_with_state(state)
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_5_1_repo_test"


def test_stage5_compliance_scan_routes_to_command():
    """Stage 5 compliance_scan must route to run_command."""
    state = PipelineState(stage="5", sub_stage="compliance_scan")
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "compliance_scan" in action.get("command", "")


def test_stage5_repo_complete_routes_to_pipeline_complete():
    """Stage 5 repo_complete must route to pipeline_complete."""
    state = PipelineState(stage="5", sub_stage="repo_complete")
    action = _route_with_state(state)
    assert action["action_type"] == "pipeline_complete"
