"""Bug 18: Every run_command action block must have a 'post' field.

Tests that route() returns action blocks with a 'post' key whenever
action_type is 'run_command', for all sub-stages that produce them.
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


def test_stub_generation_has_post():
    """stub_generation run_command must include a post field."""
    state = PipelineState(
        stage="3", sub_stage="stub_generation", current_unit=1, total_units=3
    )
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "stub_generation run_command missing 'post' key"


def test_quality_gate_a_has_post():
    """quality_gate_a run_command must include a post field."""
    state = PipelineState(
        stage="3", sub_stage="quality_gate_a", current_unit=1, total_units=3
    )
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "quality_gate_a run_command missing 'post' key"


def test_test_execution_red_run_has_post():
    """red_run test_execution run_command must include a post field."""
    state = PipelineState(
        stage="3", sub_stage="red_run", current_unit=1, total_units=3
    )
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "red_run run_command missing 'post' key"


def test_test_execution_green_run_has_post():
    """green_run test_execution run_command must include a post field."""
    state = PipelineState(
        stage="3", sub_stage="green_run", current_unit=1, total_units=3
    )
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "green_run run_command missing 'post' key"


def test_unit_completion_has_post():
    """unit_completion run_command must include a post field."""
    state = PipelineState(
        stage="3", sub_stage="unit_completion", current_unit=1, total_units=3
    )
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "unit_completion run_command missing 'post' key"


def test_quality_gate_b_has_post():
    """quality_gate_b run_command must include a post field."""
    state = PipelineState(
        stage="3", sub_stage="quality_gate_b", current_unit=1, total_units=3
    )
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "quality_gate_b run_command missing 'post' key"


def test_compliance_scan_has_post():
    """Stage 5 compliance_scan run_command must include a post field."""
    state = PipelineState(stage="5", sub_stage="compliance_scan")
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "post" in action, "compliance_scan run_command missing 'post' key"
