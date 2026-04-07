"""Bug 21 (2.1) regression: Stage 3 core sub-stage routing order.

Stage 3 must route through sub-stages in correct order:
stub_generation -> test_generation -> quality_gate_a -> red_run ->
implementation -> quality_gate_b -> green_run -> coverage_review ->
unit_completion.

SVP 2.2 adaptation:
- route() takes only project_root; state saved to disk via save_state
- Action block keys lowercase (action_type, agent_type, command)
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


def test_stub_generation_routes_to_command():
    """stub_generation routes to run_command for stub generation."""
    state = PipelineState(stage="3", sub_stage="stub_generation", current_unit=1, total_units=3)
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"


def test_test_generation_routes_to_agent():
    state = PipelineState(stage="3", sub_stage="test_generation", current_unit=1, total_units=3)
    action = _route_with_state(state)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "test_agent"


def test_implementation_routes_to_agent():
    state = PipelineState(stage="3", sub_stage="implementation", current_unit=1, total_units=3)
    action = _route_with_state(state)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "implementation_agent"


def test_coverage_review_routes_to_agent():
    state = PipelineState(stage="3", sub_stage="coverage_review", current_unit=1, total_units=3)
    action = _route_with_state(state)
    assert action["action_type"] == "invoke_agent"
    assert action.get("agent_type") == "coverage_review_agent"


def test_unit_completion_routes_to_run_command():
    """unit_completion sub-stage routes to run_command to finalize the unit."""
    state = PipelineState(stage="3", sub_stage="unit_completion", current_unit=1, total_units=3)
    action = _route_with_state(state)
    assert action["action_type"] == "run_command"
    assert "unit_completion" in action.get("command", "")
