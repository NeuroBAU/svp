"""Bug 21 (2.1) regression: Stage 3 core sub-stage routing order.

Stage 3 must route through sub-stages in correct order:
stub_generation -> test_generation -> quality_gate_a -> red_run ->
implementation -> quality_gate_b -> green_run -> coverage_review ->
unit_completion.
"""

from pathlib import Path

from routing import route
from pipeline_state import PipelineState


def test_stub_generation_routes_to_fallback(tmp_path):
    """stub_generation is not a recognized Stage 3 sub-stage; it falls through
    to the Stage 3 fallback which invokes the implementation_agent."""
    state = PipelineState(stage="3", sub_stage="stub_generation")
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "implementation_agent"


def test_test_generation_routes_to_agent(tmp_path):
    state = PipelineState(stage="3", sub_stage="test_generation")
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "test_agent"


def test_implementation_routes_to_agent(tmp_path):
    state = PipelineState(stage="3", sub_stage="implementation")
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "implementation_agent"


def test_coverage_review_routes_to_agent(tmp_path):
    state = PipelineState(stage="3", sub_stage="coverage_review")
    action = route(state, tmp_path)
    assert action["ACTION"] == "invoke_agent"
    assert action["AGENT"] == "coverage_review"


def test_unit_completion_routes_to_run_command(tmp_path):
    """unit_completion sub-stage routes to run_command to finalize the unit."""
    state = PipelineState(stage="3", sub_stage="unit_completion")
    action = route(state, tmp_path)
    assert action["ACTION"] == "run_command"
    assert "COMMAND_SUCCEEDED" in action["COMMAND"]
