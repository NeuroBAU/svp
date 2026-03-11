"""Vocabulary constants and text helpers for SVP routing."""

from typing import Dict, List


GATE_VOCABULARY: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": [
        "CONTEXT APPROVED",
        "CONTEXT REJECTED",
        "CONTEXT NOT READY",
    ],
    "gate_1_1_spec_draft": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_1_2_spec_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_1_blueprint_approval": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_2_blueprint_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_3_alignment_exhausted": ["REVISE SPEC", "RESTART SPEC", "RETRY BLUEPRINT"],
    "gate_3_1_test_validation": ["TEST CORRECT", "TEST WRONG"],
    "gate_3_2_diagnostic_decision": ["FIX IMPLEMENTATION", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_1_integration_failure": ["ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_2_assembly_exhausted": ["FIX BLUEPRINT", "FIX SPEC"],
    "gate_5_1_repo_test": ["TESTS PASSED", "TESTS FAILED"],
    "gate_5_2_assembly_exhausted": ["RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_2_debug_classification": ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_3_repair_exhausted": ["RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
}

AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": ["PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED"],
    "stakeholder_dialog": ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"],
    "stakeholder_reviewer": ["REVIEW_COMPLETE"],
    "blueprint_author": ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"],
    "blueprint_checker": [
        "ALIGNMENT_CONFIRMED",
        "ALIGNMENT_FAILED: spec",
        "ALIGNMENT_FAILED: blueprint",
    ],
    "blueprint_reviewer": ["REVIEW_COMPLETE"],
    "test_agent": ["TEST_GENERATION_COMPLETE"],
    "implementation_agent": ["IMPLEMENTATION_COMPLETE"],
    "coverage_review": ["COVERAGE_COMPLETE: no gaps", "COVERAGE_COMPLETE: tests added"],
    "diagnostic_agent": [
        "DIAGNOSIS_COMPLETE: implementation",
        "DIAGNOSIS_COMPLETE: blueprint",
        "DIAGNOSIS_COMPLETE: spec",
    ],
    "integration_test_author": ["INTEGRATION_TESTS_COMPLETE"],
    "git_repo_agent": ["REPO_ASSEMBLY_COMPLETE"],
    "help_agent": [
        "HELP_SESSION_COMPLETE: no hint",
        "HELP_SESSION_COMPLETE: hint forwarded",
    ],
    "hint_agent": ["HINT_ANALYSIS_COMPLETE"],
    "redo_agent": [
        "REDO_CLASSIFIED: spec",
        "REDO_CLASSIFIED: blueprint",
        "REDO_CLASSIFIED: gate",
    ],
    "bug_triage": [
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_NEEDS_REFINEMENT",
        "TRIAGE_NON_REPRODUCIBLE",
    ],
    "repair_agent": ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"],
    "reference_indexing": ["INDEXING_COMPLETE"],
}

CROSS_AGENT_STATUS: str = "HINT_BLUEPRINT_CONFLICT"

COMMAND_STATUS_PATTERNS: List[str] = [
    "TESTS_PASSED",
    "TESTS_FAILED",
    "TESTS_ERROR",
    "COMMAND_SUCCEEDED",
    "COMMAND_FAILED",
]


def _describe_next_action(state) -> str:
    """Derive a short description of what happens next from state."""
    stage = state.stage
    sub = state.sub_stage

    if stage == "0":
        if sub == "hook_activation":
            return "Activate hooks via Claude Code's /hooks menu."
        elif sub == "project_context":
            return "Create the project context document with the setup agent."
        return "Continue Stage 0 setup."

    if stage == "1":
        return "Continue stakeholder spec authoring."

    if stage == "2":
        if sub == "alignment_check":
            return "Run alignment check on the blueprint."
        elif sub in ("approval", "approval_gate"):
            return "Review and approve the blueprint."
        return "Continue blueprint generation."

    if stage == "pre_stage_3":
        return "Run infrastructure setup (environment, directories)."

    if stage == "3":
        unit = state.current_unit
        fix = state.fix_ladder_position
        if fix:
            return f"Continue fix ladder for Unit {unit} (position: {fix})."
        if sub == "test_generation":
            return f"Generate tests for Unit {unit}."
        elif sub == "stub_generation":
            return f"Generate stubs for Unit {unit}."
        elif sub == "red_run":
            return f"Run red validation for Unit {unit}."
        elif sub == "implementation":
            return f"Generate implementation for Unit {unit}."
        elif sub == "green_run":
            return f"Run green validation for Unit {unit}."
        elif sub == "coverage_review":
            return f"Run coverage review for Unit {unit}."
        return f"Continue Stage 3, Unit {unit}."

    if stage == "4":
        return "Continue integration testing."

    if stage == "5":
        if sub == "complete":
            return "Pipeline complete -- offer workspace cleanup."
        if state.debug_session is not None:
            return "Continue debug session."
        return "Continue repository delivery."

    return "Continue pipeline."


def _generate_context_summary(state, project_root) -> str:
    """Produce a human-readable context summary per spec Section 16.3."""
    from svp_core.pipeline_state import get_stage_display

    parts = []

    project_name = state.project_name or project_root.name
    parts.append(f"Project: {project_name}")

    stage_display = get_stage_display(state)
    parts.append(f"Current position: {stage_display}")

    if state.last_action:
        parts.append(f"What just happened: {state.last_action}")

    next_action = _describe_next_action(state)
    parts.append(f"What happens next: {next_action}")

    if state.pass_history and len(state.pass_history) > 0:
        current_pass = len(state.pass_history) + 1
        history_lines = [f"This is pass {current_pass}."]
        for entry in state.pass_history:
            pass_num = entry.get("pass_number", "?")
            reached = entry.get("reached_unit", "?")
            reason = entry.get("ended_reason", "unknown")
            history_lines.append(
                f"Pass {pass_num} reached Unit {reached} before ending: {reason}."
            )
        parts.append(" ".join(history_lines))

    return "\n".join(parts)
