"""Bug 17 (2.1) Stage 5 regression: sub-stage routing order.

Stage 5 must route through sub-stages:
None -> git_repo_agent
repo_test -> gate_5_1_repo_test
compliance_scan -> run_command
repo_complete -> pipeline_complete
"""

from pathlib import Path

from routing import route
from pipeline_state import PipelineState


def test_stage5_none_routes_to_git_repo_agent(tmp_path):
    """Stage 5 with no sub_stage must invoke git_repo_agent."""
    state = PipelineState(stage="5", sub_stage=None)
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "git_repo_agent"


def test_stage5_repo_test_routes_to_gate(tmp_path):
    """Stage 5 repo_test must present gate_5_1_repo_test."""
    state = PipelineState(stage="5", sub_stage="repo_test")
    action = route(state, tmp_path)
    assert action["ACTION"] == "human_gate"
    assert action["GATE_ID"] == "gate_5_1_repo_test"


def test_stage5_compliance_scan_routes_to_command(tmp_path):
    """Stage 5 compliance_scan must route to run_command."""
    state = PipelineState(stage="5", sub_stage="compliance_scan")
    action = route(state, tmp_path)
    assert action["ACTION"] == "run_command"
    assert "compliance_scan" in action["COMMAND"]


def test_stage5_repo_complete_routes_to_pipeline_complete(tmp_path):
    """Stage 5 repo_complete must route to pipeline_complete."""
    state = PipelineState(stage="5", sub_stage="repo_complete")
    action = route(state, tmp_path)
    assert action["ACTION"] == "pipeline_complete"
