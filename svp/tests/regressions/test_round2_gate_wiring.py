"""Regression: round-2 wiring of the previously dead gates (audit
2026-07-06, P3).

gate_3_1 (vacuous-test escalation), gate_4_1a (stage-4 escalation ladder),
repo_test (state-driven gate_5_1), gate_5_3 (strict compliance findings),
and CONTEXT NOT READY (hold, not redo) all had presenters or handlers but
no setters — or setters but no consumers.
"""

import pytest

from tests.regressions.helpers import (
    make_state,
    read_state_dict,
    write_profile,
    write_status,
)

from pipeline_state import PipelineState, save_state
from routing import (
    _cmd_compliance_scan,
    dispatch_command_status,
    dispatch_gate_response,
    route,
)


# --- R1: gate_3_1 vacuous-test escalation --------------------------------


def test_red_run_vacuous_passes_escalate_to_gate_3_1_at_limit():
    state = PipelineState(
        stage="3", sub_stage="red_run", current_unit=1, total_units=1
    )
    for expected_sub in ("test_generation", "test_generation", "gate_3_1"):
        state.sub_stage = "red_run"
        state = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", sub_stage="red_run"
        )
        assert state.sub_stage == expected_sub
    assert state.red_run_retries == 3


def test_gate_3_1_is_presented(project_root):
    make_state(
        project_root,
        stage="3",
        sub_stage="gate_3_1",
        current_unit=1,
        total_units=1,
        red_run_retries=3,
    )
    write_status(project_root, "")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_3_1_test_validation"


def test_gate_3_1_test_correct_proceeds_to_implementation(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="gate_3_1",
        current_unit=1,
        total_units=1,
        red_run_retries=3,
    )

    new = dispatch_gate_response(
        state, "gate_3_1_test_validation", "TEST CORRECT", project_root
    )

    assert new.sub_stage == "implementation"
    assert new.red_run_retries == 0


def test_gate_3_1_test_wrong_regenerates_with_fresh_budget(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="gate_3_1",
        current_unit=1,
        total_units=1,
        red_run_retries=3,
    )

    new = dispatch_gate_response(
        state, "gate_3_1_test_validation", "TEST WRONG", project_root
    )

    assert new.sub_stage == "test_generation"
    assert new.red_run_retries == 0


# --- R2: gate_4_1a stage-4 escalation ladder ------------------------------


def test_stage_4_failures_escalate_through_gate_4_1a():
    state = PipelineState(stage="4", sub_stage=None, red_run_retries=1)
    state = dispatch_command_status(state, "test_execution", "TESTS_FAILED")
    assert state.sub_stage == "gate_4_1"  # retries now 2, below limit

    state.sub_stage = None
    state = dispatch_command_status(state, "test_execution", "TESTS_FAILED")
    assert state.sub_stage == "gate_4_1a"  # retries now 3, at limit


def test_gate_4_1a_escalate_reaches_gate_4_2(project_root):
    state = make_state(
        project_root, stage="4", sub_stage="gate_4_1a", red_run_retries=3
    )

    new = dispatch_gate_response(state, "gate_4_1a", "ESCALATE", project_root)

    assert new.sub_stage == "gate_4_2"


# --- R3: repo_test is state-driven ----------------------------------------


def test_repo_assembly_complete_sets_repo_test_sub_stage(project_root):
    write_profile(project_root, archetype="python_project", name="proj")
    (project_root.parent / "proj-repo").mkdir()
    make_state(project_root, stage="5", sub_stage=None)
    write_status(project_root, "REPO_ASSEMBLY_COMPLETE")

    action = route(project_root)
    assert action["gate_id"] == "gate_5_1_repo_test"
    assert read_state_dict(project_root)["sub_stage"] == "repo_test"

    # Gate presentation survives a clobbered last_status now.
    write_status(project_root, "SOMETHING_ELSE_ENTIRELY")
    action = route(project_root)
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_5_1_repo_test"


# --- R4: gate_5_3 via strict compliance scan -------------------------------


def test_compliance_scan_command_is_strict(project_root):
    write_profile(project_root, archetype="python_project")
    state = PipelineState(stage="5", sub_stage="compliance_scan")

    cmd = _cmd_compliance_scan(state, project_root)

    assert "--strict" in cmd


def test_compliance_failure_presents_gate_5_3(project_root):
    state = PipelineState(stage="5", sub_stage="compliance_scan")

    new = dispatch_command_status(
        state, "compliance_scan", "COMMAND_FAILED", project_root=project_root
    )

    assert new.sub_stage == "gate_5_3"
    save_state(project_root, new)
    write_status(project_root, "")
    action = route(project_root)
    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_5_3_unused_functions"


def test_gate_5_3_override_continue_reaches_repo_complete(project_root):
    state = make_state(project_root, stage="5", sub_stage="gate_5_3")

    new = dispatch_gate_response(
        state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", project_root
    )

    assert new.sub_stage == "repo_complete"


def test_gate_5_3_fix_spec_restarts_stage_1(project_root):
    state = make_state(
        project_root, stage="5", sub_stage="gate_5_3", red_run_retries=2
    )

    new = dispatch_gate_response(
        state, "gate_5_3_unused_functions", "FIX SPEC", project_root
    )

    assert new.stage == "1"
    assert new.red_run_retries == 0


# --- R6: CONTEXT NOT READY holds instead of redoing ------------------------


def test_context_not_ready_holds_pipeline(project_root):
    state = make_state(project_root, stage="0", sub_stage="project_context")
    write_status(project_root, "CONTEXT NOT READY")

    new = dispatch_gate_response(
        state, "gate_0_2_context_approval", "CONTEXT NOT READY", project_root
    )
    save_state(project_root, new)

    action = route(project_root)
    assert action["action_type"] == "pipeline_held"

    # Clearing the status resumes the setup agent.
    write_status(project_root, "")
    action = route(project_root)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "setup_agent"


# --- R7: gate_7a limit error names the remaining valid responses -----------


def test_gate_7a_modify_at_limit_raises_with_guidance(project_root):
    state = make_state(
        project_root,
        stage="5",
        sub_stage=None,
        oracle_session_active=True,
        oracle_phase="dry_run",
        oracle_modification_count=3,
    )

    with pytest.raises(ValueError) as exc:
        dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY", project_root
        )

    assert "APPROVE TRAJECTORY" in str(exc.value)
    assert "ABORT" in str(exc.value)
