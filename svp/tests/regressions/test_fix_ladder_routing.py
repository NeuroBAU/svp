"""Regression: the Stage 3 fix ladder must route every rung.

Audit 2026-07-06 (P2): advance_fix_ladder set sub_stage="implementation"
only for fresh_impl/diagnostic_impl, so the "diagnostic" and "exhausted"
rungs left sub_stage on the failing command — the diagnostic agent and
gate_3_2 were unreachable, and the ladder crashed with TransitionError
after ~3 green-run failures. gate_3_2 FIX IMPLEMENTATION never reset the
ladder position, looping the gate or the diagnostic agent.
"""

import pytest

from tests.regressions.helpers import make_state, write_status

from pipeline_state import PipelineState, save_state
from routing import dispatch_command_status, dispatch_gate_response, route
from state_transitions import TransitionError, advance_fix_ladder


def test_green_failure_advances_every_rung_with_implementation_sub_stage():
    state = PipelineState(
        stage="3", sub_stage="green_run", current_unit=1, total_units=1
    )
    expected = ["fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"]
    for rung in expected:
        state = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
        )
        assert state.fix_ladder_position == rung
        assert state.sub_stage == "implementation"


def test_diagnostic_rung_dispatches_diagnostic_agent(project_root):
    make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
        fix_ladder_position="diagnostic",
    )
    write_status(project_root, "")

    action = route(project_root)

    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "diagnostic_agent"


def test_exhausted_rung_presents_gate_3_2_without_crashing(project_root):
    make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
        fix_ladder_position="exhausted",
    )
    write_status(project_root, "")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_3_2_diagnostic_decision"


def test_advance_from_exhausted_still_raises_as_invariant():
    state = PipelineState(stage="3", fix_ladder_position="exhausted")
    with pytest.raises(TransitionError):
        advance_fix_ladder(state)


def test_gate_3_2_fix_implementation_reinvokes_implementation_agent(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
        fix_ladder_position="exhausted",
    )

    new = dispatch_gate_response(
        state, "gate_3_2_diagnostic_decision", "FIX IMPLEMENTATION", project_root
    )

    assert new.fix_ladder_position == "diagnostic_impl"
    assert new.sub_stage == "implementation"
    save_state(project_root, new)
    action = route(project_root)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "implementation_agent"


def test_gate_3_2_fix_spec_uses_restart_semantics(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
        fix_ladder_position="diagnostic",
        red_run_retries=2,
    )

    new = dispatch_gate_response(
        state, "gate_3_2_diagnostic_decision", "FIX SPEC", project_root
    )

    assert new.stage == "1"
    assert new.current_unit is None
    assert new.fix_ladder_position is None
    assert new.red_run_retries == 0
