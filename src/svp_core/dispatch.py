"""Dispatch functions for SVP state updates."""

from pathlib import Path
from typing import Optional

from svp_core.pipeline_state import PipelineState

# Import state_transitions from svp/scripts (to be extracted in future PR)
from svp.scripts.state_transitions import (
    TransitionError,
    advance_stage,
    advance_sub_stage,
    complete_unit,
    advance_fix_ladder,
    reset_alignment_iteration,
    increment_alignment_iteration,
    increment_red_run_retries,
    reset_red_run_retries,
    restart_from_stage,
    authorize_debug_session,
    abandon_debug_session,
    update_debug_phase,
    set_debug_classification,
)
from svp_core.vocabulary import (
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
)


def dispatch_status(
    state: PipelineState,
    status_line: str,
    gate_id: Optional[str],
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Top-level dispatcher: determines whether the status line is a gate
    response, agent status, or command result, and delegates accordingly.
    """
    if gate_id is not None:
        return dispatch_gate_response(state, gate_id, status_line, project_root)

    for pattern in COMMAND_STATUS_PATTERNS:
        if status_line.startswith(pattern):
            return dispatch_command_status(
                state, status_line, unit, phase, project_root
            )

    if status_line.startswith(CROSS_AGENT_STATUS):
        return state

    return dispatch_agent_status(state, "", status_line, unit, phase, project_root)


def dispatch_gate_response(
    state: PipelineState,
    gate_id: str,
    response: str,
    project_root: Path,
) -> PipelineState:
    """Validate the response against GATE_VOCABULARY[gate_id] using exact
    string matching. If the response is not in the vocabulary, raises ValueError.
    """
    if gate_id not in GATE_VOCABULARY:
        raise ValueError(
            f"Invalid gate response '{response}' for gate {gate_id}. "
            f"Valid options: gate not found in vocabulary"
        )

    valid_options = GATE_VOCABULARY[gate_id]

    if response not in valid_options:
        options_str = ", ".join(valid_options)
        raise ValueError(
            f"Invalid gate response '{response}' for gate {gate_id}. "
            f"Valid options: {options_str}"
        )

    if gate_id == "gate_0_1_hook_activation":
        if response == "HOOKS ACTIVATED":
            return advance_sub_stage(state, "project_context", project_root)
        else:
            return state

    elif gate_id == "gate_0_2_context_approval":
        if response == "CONTEXT APPROVED":
            return advance_stage(state, project_root)
        elif response == "CONTEXT REJECTED":
            return advance_sub_stage(state, "project_context", project_root)
        else:
            return state

    elif gate_id == "gate_1_1_spec_draft":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "revision", project_root)
        else:
            return advance_sub_stage(state, "fresh_review", project_root)

    elif gate_id == "gate_1_2_spec_post_review":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "revision", project_root)
        else:
            return advance_sub_stage(state, "fresh_review", project_root)

    elif gate_id == "gate_2_1_blueprint_approval":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "blueprint_revision", project_root)
        else:
            return advance_sub_stage(state, "fresh_review", project_root)

    elif gate_id == "gate_2_2_blueprint_post_review":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "blueprint_revision", project_root)
        else:
            return advance_sub_stage(state, "fresh_review", project_root)

    elif gate_id == "gate_2_3_alignment_exhausted":
        if response == "REVISE SPEC":
            return advance_sub_stage(state, "spec_revision", project_root)
        elif response == "RESTART SPEC":
            return restart_from_stage(
                state, "1", "Full spec restart from alignment exhaustion", project_root
            )
        else:
            new_state = reset_alignment_iteration(state)
            return advance_sub_stage(new_state, "blueprint_dialog", project_root)

    elif gate_id == "gate_3_1_test_validation":
        if response == "TEST CORRECT":
            return advance_fix_ladder(state, "fresh_impl")
        else:
            return advance_fix_ladder(state, "fresh_test")

    elif gate_id == "gate_3_2_diagnostic_decision":
        if response == "FIX IMPLEMENTATION":
            return advance_fix_ladder(state, "diagnostic_impl")
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(
                state, "2", "Blueprint fix from diagnostic", project_root
            )
        else:
            return restart_from_stage(
                state, "1", "Spec fix from diagnostic", project_root
            )

    elif gate_id == "gate_4_1_integration_failure":
        if response == "ASSEMBLY FIX":
            return advance_sub_stage(state, "assembly_fix", project_root)
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(
                state, "2", "Blueprint fix from integration failure", project_root
            )
        else:
            return restart_from_stage(
                state, "1", "Spec fix from integration failure", project_root
            )

    elif gate_id == "gate_4_2_assembly_exhausted":
        if response == "FIX BLUEPRINT":
            return restart_from_stage(
                state, "2", "Blueprint fix from assembly exhaustion", project_root
            )
        else:
            return restart_from_stage(
                state, "1", "Spec fix from assembly exhaustion", project_root
            )

    elif gate_id == "gate_5_1_repo_test":
        if response == "TESTS PASSED":
            return advance_sub_stage(state, "complete", project_root)
        else:
            return advance_sub_stage(state, "fix_cycle", project_root)

    elif gate_id == "gate_5_2_assembly_exhausted":
        if response == "RETRY ASSEMBLY":
            return advance_sub_stage(state, "repo_assembly", project_root)
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(
                state, "2", "Blueprint fix from repo assembly exhaustion", project_root
            )
        else:
            return restart_from_stage(
                state, "1", "Spec fix from repo assembly exhaustion", project_root
            )

    elif gate_id == "gate_6_0_debug_permission":
        if response == "AUTHORIZE DEBUG":
            return authorize_debug_session(state)
        else:
            return abandon_debug_session(state)

    elif gate_id == "gate_6_1_regression_test":
        if response == "TEST CORRECT":
            return advance_sub_stage(state, "debug_classification", project_root)
        else:
            return update_debug_phase(state, "triage")

    elif gate_id == "gate_6_2_debug_classification":
        if response == "FIX UNIT":
            return update_debug_phase(state, "stage3_reentry")
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(
                state, "2", "Blueprint fix from debug classification", project_root
            )
        else:
            return restart_from_stage(
                state, "1", "Spec fix from debug classification", project_root
            )

    elif gate_id == "gate_6_3_repair_exhausted":
        if response == "RETRY REPAIR":
            return update_debug_phase(state, "repair")
        elif response == "RECLASSIFY BUG":
            return update_debug_phase(state, "triage")
        else:
            return abandon_debug_session(state)

    elif gate_id == "gate_6_4_non_reproducible":
        if response == "RETRY TRIAGE":
            return update_debug_phase(state, "triage")
        else:
            return abandon_debug_session(state)

    return state


def dispatch_agent_status(
    state: PipelineState,
    agent_type: str,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Parse the terminal status line and call appropriate transition functions."""
    line_recognized = False

    if status_line.startswith(CROSS_AGENT_STATUS):
        line_recognized = True

    if not line_recognized:
        for agent, lines in AGENT_STATUS_LINES.items():
            for known_line in lines:
                if status_line == known_line or status_line.startswith(known_line):
                    line_recognized = True
                    break
            if line_recognized:
                break

    if not line_recognized:
        raise ValueError(f"Unknown agent status line: {status_line}")

    if phase == "test_generation":
        return _handle_test_generation(state, status_line, unit, project_root)
    elif phase == "implementation":
        return _handle_implementation(state, status_line, unit, project_root)
    elif phase == "coverage_review":
        return _handle_coverage_review(state, status_line, unit, project_root)
    elif phase == "diagnostic":
        return _handle_diagnostic(state, status_line, unit, project_root)
    elif phase == "alignment_check":
        return _handle_alignment_check(state, status_line, project_root)
    elif phase == "stakeholder_dialog":
        return _handle_stakeholder_dialog(state, status_line, project_root)
    elif phase == "stakeholder_draft":
        return advance_sub_stage(state, "approval", project_root)
    elif phase == "spec_review":
        return advance_sub_stage(state, "post_review", project_root)
    elif phase == "spec_revision":
        return advance_sub_stage(state, "approval", project_root)
    elif phase == "spec_revision_stage2":
        return advance_sub_stage(state, "blueprint_dialog", project_root)
    elif phase == "blueprint_dialog":
        return advance_sub_stage(state, "alignment_check", project_root)
    elif phase == "blueprint_revision":
        return advance_sub_stage(state, "alignment_check", project_root)
    elif phase == "blueprint_review":
        return advance_sub_stage(state, "post_review", project_root)
    elif phase == "setup":
        return _handle_project_context(state, status_line, project_root)
    elif phase == "project_context":
        return _handle_project_context(state, status_line, project_root)
    elif phase == "hook_activation":
        return advance_sub_stage(state, "project_context", project_root)
    elif phase == "repo_assembly":
        return advance_sub_stage(state, "test_gate", project_root)
    elif phase == "repo_fix":
        return advance_sub_stage(state, "test_gate", project_root)
    elif phase == "integration_test_generation":
        return advance_sub_stage(state, "integration_run", project_root)
    elif phase == "bug_triage":
        return _handle_bug_triage(state, status_line, project_root)
    elif phase == "repair":
        return _handle_repair(state, status_line, project_root)
    elif phase == "fresh_test":
        return _handle_test_generation(state, status_line, unit, project_root)
    elif phase == "hint_test":
        return _handle_test_generation(state, status_line, unit, project_root)
    elif phase == "fresh_impl":
        return _handle_implementation(state, status_line, unit, project_root)
    elif phase == "diagnostic_impl":
        return _handle_implementation(state, status_line, unit, project_root)
    elif phase == "diagnostic_escalation":
        return _handle_diagnostic(state, status_line, unit, project_root)
    elif phase == "assembly_fix":
        return _handle_implementation(state, status_line, unit, project_root)
    elif phase == "regression_test_generation":
        return advance_sub_stage(state, "regression_test_validation", project_root)
    else:
        raise ValueError(f"Unknown phase: {phase}")


def dispatch_command_status(
    state: PipelineState,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Parse command result status lines and call appropriate transition functions."""
    matched = False
    for pattern in COMMAND_STATUS_PATTERNS:
        if status_line.startswith(pattern):
            matched = True
            break

    if not matched:
        raise ValueError(f"Unknown agent status line: {status_line}")

    if phase == "red_run":
        return _handle_red_run(state, status_line, unit, project_root)
    elif phase == "green_run":
        return _handle_green_run(state, status_line, unit, project_root)
    elif phase == "infrastructure_setup":
        return _handle_infrastructure(state, status_line, project_root)
    elif phase == "stub_generation":
        return _handle_stub_generation(state, status_line, unit, project_root)
    elif phase == "integration_run":
        return _handle_integration_run(state, status_line, project_root)
    elif phase == "unit_completion":
        if unit is not None:
            return complete_unit(state, unit, project_root)
        return state
    else:
        raise ValueError(f"Unknown phase: {phase}")


def _handle_test_generation(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    return advance_sub_stage(state, "stub_generation", project_root)


def _handle_implementation(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    return advance_sub_stage(state, "green_run", project_root)


def _handle_coverage_review(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    if status.startswith("COVERAGE_COMPLETE: no gaps"):
        return advance_sub_stage(state, "unit_completion", project_root)
    elif status.startswith("COVERAGE_COMPLETE: tests added"):
        return advance_sub_stage(state, "green_run", project_root)
    return advance_sub_stage(state, "unit_completion", project_root)


def _handle_diagnostic(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    return advance_sub_stage(state, "diagnostic_gate", project_root)


def _handle_alignment_check(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("ALIGNMENT_CONFIRMED"):
        return advance_sub_stage(state, "approval", project_root)
    elif status.startswith("ALIGNMENT_FAILED: spec"):
        try:
            new_state = increment_alignment_iteration(state)
        except TransitionError:
            return advance_sub_stage(state, "iteration_limit", project_root)
        return advance_sub_stage(new_state, "spec_revision_stage2", project_root)
    elif status.startswith("ALIGNMENT_FAILED: blueprint"):
        try:
            new_state = increment_alignment_iteration(state)
        except TransitionError:
            return advance_sub_stage(state, "iteration_limit", project_root)
        return advance_sub_stage(new_state, "blueprint_dialog", project_root)
    return state


def _handle_stakeholder_dialog(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("SPEC_DRAFT_COMPLETE"):
        return advance_sub_stage(state, "approval", project_root)
    elif status.startswith("SPEC_REVISION_COMPLETE"):
        return advance_sub_stage(state, "approval", project_root)
    return state


def _handle_project_context(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("PROJECT_CONTEXT_COMPLETE"):
        return advance_stage(state, project_root)
    elif status.startswith("PROJECT_CONTEXT_REJECTED"):
        return state
    return state


def _handle_red_run(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    if status.startswith("TESTS_FAILED:"):
        new_state = reset_red_run_retries(state)
        return advance_sub_stage(new_state, "implementation", project_root)
    elif status.startswith("TESTS_PASSED:"):
        new_state = increment_red_run_retries(state)
        return advance_sub_stage(new_state, "test_generation", project_root)
    elif status.startswith("TESTS_ERROR:"):
        new_state = increment_red_run_retries(state)
        return advance_sub_stage(new_state, "test_generation", project_root)
    return state


def _handle_green_run(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    if status.startswith("TESTS_PASSED:"):
        return advance_sub_stage(state, "coverage_review", project_root)
    elif status.startswith("TESTS_FAILED:"):
        return advance_sub_stage(state, "test_validation", project_root)
    elif status.startswith("TESTS_ERROR:"):
        return advance_sub_stage(state, "test_validation", project_root)
    return state


def _handle_infrastructure(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("COMMAND_SUCCEEDED"):
        return advance_stage(state, project_root)
    elif status.startswith("COMMAND_FAILED:"):
        return state
    return state


def _handle_stub_generation(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    if status.startswith("COMMAND_SUCCEEDED"):
        return advance_sub_stage(state, "red_run", project_root)
    return state


def _handle_integration_run(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("TESTS_PASSED:"):
        return advance_stage(state, project_root)
    elif status.startswith("TESTS_FAILED:"):
        return advance_sub_stage(state, "failure_gate", project_root)
    elif status.startswith("TESTS_ERROR:"):
        return advance_sub_stage(state, "failure_gate", project_root)
    return state


def _handle_bug_triage(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("TRIAGE_COMPLETE: build_env"):
        new_state = set_debug_classification(state, "build_env", [])
        return update_debug_phase(new_state, "repair")
    elif status.startswith("TRIAGE_COMPLETE: single_unit"):
        return update_debug_phase(state, "regression_test")
    elif status.startswith("TRIAGE_COMPLETE: cross_unit"):
        return update_debug_phase(state, "regression_test")
    elif status.startswith("TRIAGE_NEEDS_REFINEMENT"):
        return state
    elif status.startswith("TRIAGE_NON_REPRODUCIBLE"):
        return advance_sub_stage(state, "non_reproducible", project_root)
    return state


def _handle_repair(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    if status.startswith("REPAIR_COMPLETE"):
        return update_debug_phase(state, "complete")
    elif status.startswith("REPAIR_FAILED"):
        return advance_sub_stage(state, "repair_exhausted", project_root)
    elif status.startswith("REPAIR_RECLASSIFY"):
        return update_debug_phase(state, "triage")
    return state
