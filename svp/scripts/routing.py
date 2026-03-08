"""Unit 10: Routing Script and Update State

The routing script reads pipeline_state.json and outputs the exact next action
as a structured key-value block (spec Section 17). The update_state script reads
.svp/last_status.txt and dispatches to the appropriate state transition.
The run_tests script wraps pytest execution and constructs command result status
lines. This unit also defines the canonical gate status string vocabulary
(Section 18.4) as a data constant used by both routing and dispatch logic.

Implements Bug 1 fix: the gate status string vocabulary ensures that human-typed
option text is the exact status string -- no translation, no prefix, no
reformatting. update_state.py dispatches based on exact string matching.

Dependencies:
  - Unit 1 (SVP Configuration): load_config, get_model_for_agent
  - Unit 2 (Pipeline State Schema): load_state, save_state, PipelineState,
    get_stage_display
  - Unit 3 (State Transition Engine): All transition functions, TransitionError
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import ast
import subprocess
import sys
import re
import argparse

# Upstream imports -- coded against blueprint contract interfaces
from pipeline_state import PipelineState, load_state, save_state, get_stage_display
from svp_config import load_config, get_model_for_agent
from state_transitions import (
    TransitionError,
    advance_stage,
    advance_sub_stage,
    complete_unit,
    advance_fix_ladder,
    reset_fix_ladder,
    increment_red_run_retries,
    reset_red_run_retries,
    increment_alignment_iteration,
    reset_alignment_iteration,
    record_pass_end,
    rollback_to_unit,
    restart_from_stage,
    version_document,
    enter_debug_session,
    authorize_debug_session,
    complete_debug_session,
    abandon_debug_session,
    update_debug_phase,
    set_debug_classification,
)

# Re-export TransitionError for consumers
__all__ = [
    "GATE_VOCABULARY",
    "AGENT_STATUS_LINES",
    "CROSS_AGENT_STATUS",
    "COMMAND_STATUS_PATTERNS",
    "route",
    "format_action_block",
    "derive_env_name_from_state",
    "dispatch_status",
    "dispatch_gate_response",
    "dispatch_agent_status",
    "dispatch_command_status",
    "run_pytest",
    "routing_main",
    "update_state_main",
    "run_tests_main",
    "TransitionError",
]


# --- Data contract: gate status string vocabulary (Bug 1 fix) ---

GATE_VOCABULARY: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": ["CONTEXT APPROVED", "CONTEXT REJECTED", "CONTEXT NOT READY"],
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

# --- Data contract: terminal status line vocabulary ---

AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": ["PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED"],
    "stakeholder_dialog": ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"],
    "stakeholder_reviewer": ["REVIEW_COMPLETE"],
    "blueprint_author": ["BLUEPRINT_DRAFT_COMPLETE"],
    "blueprint_checker": ["ALIGNMENT_CONFIRMED", "ALIGNMENT_FAILED: spec", "ALIGNMENT_FAILED: blueprint"],
    "blueprint_reviewer": ["REVIEW_COMPLETE"],
    "test_agent": ["TEST_GENERATION_COMPLETE"],
    "implementation_agent": ["IMPLEMENTATION_COMPLETE"],
    "coverage_review": ["COVERAGE_COMPLETE: no gaps", "COVERAGE_COMPLETE: tests added"],
    "diagnostic_agent": ["DIAGNOSIS_COMPLETE: implementation", "DIAGNOSIS_COMPLETE: blueprint", "DIAGNOSIS_COMPLETE: spec"],
    "integration_test_author": ["INTEGRATION_TESTS_COMPLETE"],
    "git_repo_agent": ["REPO_ASSEMBLY_COMPLETE"],
    "help_agent": ["HELP_SESSION_COMPLETE: no hint", "HELP_SESSION_COMPLETE: hint forwarded"],
    "hint_agent": ["HINT_ANALYSIS_COMPLETE"],
    "redo_agent": ["REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint", "REDO_CLASSIFIED: gate"],
    "bug_triage": ["TRIAGE_COMPLETE: build_env", "TRIAGE_COMPLETE: single_unit", "TRIAGE_COMPLETE: cross_unit", "TRIAGE_NEEDS_REFINEMENT", "TRIAGE_NON_REPRODUCIBLE"],
    "repair_agent": ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"],
    "reference_indexing": ["INDEXING_COMPLETE"],
}

# Cross-agent status (any agent receiving a hint)
CROSS_AGENT_STATUS: str = "HINT_BLUEPRINT_CONFLICT"

# Command result status line patterns
COMMAND_STATUS_PATTERNS: List[str] = [
    "TESTS_PASSED",    # "TESTS_PASSED: N passed"
    "TESTS_FAILED",    # "TESTS_FAILED: N passed, M failed"
    "TESTS_ERROR",     # "TESTS_ERROR: [error summary]"
    "COMMAND_SUCCEEDED",
    "COMMAND_FAILED",  # "COMMAND_FAILED: [exit code]"
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REMINDER_TEXT: str = (
    "REMINDER:\n"
    "- Execute the ACTION above exactly as specified.\n"
    "- When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt verbatim. "
    "Do not summarize, annotate, or rephrase.\n"
    "- Wait for the agent to produce its terminal status line before proceeding.\n"
    "- Write the agent's terminal status line to .svp/last_status.txt.\n"
    "- Run the POST command if one was specified.\n"
    "- Then re-run the routing script for the next action.\n"
    "- Do not improvise pipeline flow. Do not skip steps. Do not add steps.\n"
    "- If the human types during an autonomous sequence, acknowledge and defer: "
    "complete the current action first."
)

_VALID_ACTION_TYPES = (
    "invoke_agent", "run_command", "human_gate",
    "session_boundary", "pipeline_complete",
)


# ---------------------------------------------------------------------------
# Helper: POST command builder
# ---------------------------------------------------------------------------

def _post_cmd(phase: str, unit: Optional[int] = None,
              gate_id: Optional[str] = None) -> str:
    """Build the standard POST command string."""
    parts = ["python scripts/update_state.py"]
    if unit is not None:
        parts.append(f"--unit {unit}")
    if gate_id is not None:
        parts.append(f"--gate {gate_id}")
    parts.append(f"--phase {phase}")
    parts.append("--status-file .svp/last_status.txt")
    return " ".join(parts)


def _prepare_cmd(agent_or_gate: str, unit: Optional[int] = None,
                 extra: Optional[str] = None) -> str:
    """Build a PREPARE command string."""
    parts = ["python scripts/prepare_task.py"]
    if unit is not None:
        parts.append(f"--unit {unit}")
    parts.append(f"--agent {agent_or_gate}")
    parts.append("--project-root .")
    parts.append("--output .svp/task_prompt.md")
    if extra:
        parts.append(extra)
    return " ".join(parts)


def _gate_prepare_cmd(gate_id: str, unit: Optional[int] = None) -> str:
    """Build a PREPARE command for a gate prompt."""
    parts = ["python scripts/prepare_task.py"]
    if unit is not None:
        parts.append(f"--unit {unit}")
    parts.append(f"--gate {gate_id}")
    parts.append("--project-root .")
    parts.append("--output .svp/gate_prompt.md")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# derive_env_name_from_state
# ---------------------------------------------------------------------------

def derive_env_name_from_state(state: PipelineState) -> str:
    """Derive the conda environment name from the project name in state.

    Uses the canonical derivation (spec Section 4.3):
    project_name.lower().replace(" ", "_").replace("-", "_")
    """
    project_name = state.project_name or "svp_project"
    return project_name.lower().replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Context summary (spec Section 16.3)
# ---------------------------------------------------------------------------

def _generate_context_summary(state: PipelineState, project_root: Path) -> str:
    """Produce a human-readable context summary per spec Section 16.3."""
    parts: List[str] = []

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


def _describe_next_action(state: PipelineState) -> str:
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
        # Check for debug session
        if state.debug_session is not None:
            return "Continue debug session."
        return "Continue repository delivery."

    return "Continue pipeline."


# ---------------------------------------------------------------------------
# Dual-file synchronization check
# ---------------------------------------------------------------------------

def _extract_known_agent_types(filepath: Path) -> set:
    """Extract KNOWN_AGENT_TYPES from a Python file using AST parsing.

    Returns the set of agent type strings, or None if the file is missing
    or the constant cannot be parsed.
    """
    if not filepath.is_file():
        return None
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        # Handle both plain assignment and annotated assignment (e.g. X: List[str] = [...])
        name = None
        value = None
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                name = node.target.id
                value = node.value

        if name == "KNOWN_AGENT_TYPES" and isinstance(value, ast.List):
            elements = set()
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    elements.add(elt.value)
            return elements
    return None


def _check_scripts_sync(project_root: Path) -> None:
    """Compare KNOWN_AGENT_TYPES between canonical and runtime copies.

    Prints a warning to stderr if they differ. Non-blocking — never raises
    or changes exit code. Silently skips if either file is missing.
    """
    canonical = project_root / "src" / "unit_9" / "stub.py"
    runtime = project_root / "scripts" / "prepare_task.py"

    canonical_types = _extract_known_agent_types(canonical)
    runtime_types = _extract_known_agent_types(runtime)

    if canonical_types is None or runtime_types is None:
        return  # Files not yet present — early pipeline stages

    if canonical_types != runtime_types:
        only_canonical = canonical_types - runtime_types
        only_runtime = runtime_types - canonical_types
        parts = ["WARNING: KNOWN_AGENT_TYPES drift detected between "
                 "src/unit_9/stub.py (canonical) and scripts/prepare_task.py (runtime)."]
        if only_canonical:
            parts.append(f"  In canonical only: {sorted(only_canonical)}")
        if only_runtime:
            parts.append(f"  In runtime only: {sorted(only_runtime)}")
        parts.append("  Update scripts/prepare_task.py to match src/unit_9/stub.py.")
        print("\n".join(parts), file=sys.stderr)


# ---------------------------------------------------------------------------
# Core routing logic
# ---------------------------------------------------------------------------

def route(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Read pipeline state and determine the next action.

    Returns a dict with all fields needed for the action block:
    ACTION, AGENT, PREPARE, TASK_PROMPT_FILE, POST, COMMAND, GATE, UNIT,
    OPTIONS, PROMPT_FILE, MESSAGE.

    Handles all pipeline states including debug loop states.
    """
    assert project_root.is_dir(), "Project root must exist"

    # Check for active debug session first -- the debug session is handled
    # through the same mechanism as regular stage routing, just additional
    # state cases.
    if state.debug_session is not None:
        result = _route_debug(state, project_root)
    else:
        result = _route_stage(state, project_root)

    # Post-conditions
    assert "ACTION" in result, "Route output must contain ACTION"
    assert result["ACTION"] in _VALID_ACTION_TYPES, \
        f"ACTION must be a valid action type, got: {result['ACTION']}"

    return result


def _route_stage(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Dispatch to the appropriate routing handler based on stage."""
    stage = state.stage
    sub = state.sub_stage

    if stage == "0":
        return _route_stage_0(state, project_root)
    elif stage == "1":
        return _route_stage_1(state, project_root)
    elif stage == "2":
        return _route_stage_2(state, project_root)
    elif stage == "pre_stage_3":
        return _route_pre_stage_3(state, project_root)
    elif stage == "3":
        return _route_stage_3(state, project_root)
    elif stage == "4":
        return _route_stage_4(state, project_root)
    elif stage == "5":
        return _route_stage_5(state, project_root)
    else:
        raise ValueError(
            f"Unrecognized pipeline state: stage={stage}, sub_stage={sub}"
        )


# ---------------------------------------------------------------------------
# Action dict builders
# ---------------------------------------------------------------------------

def _invoke_agent_action(
    agent: str,
    message: str,
    unit: Optional[int] = None,
    prepare: Optional[str] = None,
    post: Optional[str] = None,
    task_prompt_file: str = ".svp/task_prompt.md",
) -> Dict[str, Any]:
    """Build an invoke_agent action dict."""
    return {
        "ACTION": "invoke_agent",
        "AGENT": agent,
        "PREPARE": prepare or _prepare_cmd(agent, unit=unit),
        "TASK_PROMPT_FILE": task_prompt_file,
        "POST": post,
        "COMMAND": None,
        "GATE": None,
        "UNIT": unit,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def _run_command_action(
    command: str,
    message: str,
    post: Optional[str] = None,
    unit: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a run_command action dict."""
    return {
        "ACTION": "run_command",
        "AGENT": None,
        "PREPARE": None,
        "TASK_PROMPT_FILE": None,
        "POST": post,
        "COMMAND": command,
        "GATE": None,
        "UNIT": unit,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def _human_gate_action(
    gate_id: str,
    message: str,
    unit: Optional[int] = None,
    prepare: Optional[str] = None,
    post: Optional[str] = None,
    prompt_file: str = ".svp/gate_prompt.md",
) -> Dict[str, Any]:
    """Build a human_gate action dict.

    The OPTIONS field is populated from GATE_VOCABULARY using the gate_id.
    This is the Bug 1 invariant: OPTIONS lists exactly the valid status strings.
    """
    options_list = list(GATE_VOCABULARY.get(gate_id, []))
    # Inject --gate into the POST command for gate response dispatch
    if post is not None:
        post = f"{post} --gate {gate_id}"
    return {
        "ACTION": "human_gate",
        "AGENT": None,
        "PREPARE": prepare or _gate_prepare_cmd(gate_id, unit=unit),
        "TASK_PROMPT_FILE": None,
        "POST": post,
        "COMMAND": None,
        "GATE": gate_id,
        "UNIT": unit,
        "OPTIONS": options_list,
        "PROMPT_FILE": prompt_file,
        "MESSAGE": message,
    }


def _session_boundary_action(message: str) -> Dict[str, Any]:
    """Build a session_boundary action dict."""
    return {
        "ACTION": "session_boundary",
        "AGENT": None,
        "PREPARE": None,
        "TASK_PROMPT_FILE": None,
        "POST": None,
        "COMMAND": None,
        "GATE": None,
        "UNIT": None,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def _pipeline_complete_action(message: str) -> Dict[str, Any]:
    """Build a pipeline_complete action dict."""
    return {
        "ACTION": "pipeline_complete",
        "AGENT": None,
        "PREPARE": None,
        "TASK_PROMPT_FILE": None,
        "POST": None,
        "COMMAND": None,
        "GATE": None,
        "UNIT": None,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


# ---------------------------------------------------------------------------
# Stage routing functions
# ---------------------------------------------------------------------------

def _route_stage_0(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Stage 0: Setup."""
    sub = state.sub_stage

    if sub == "hook_activation":
        return _human_gate_action(
            gate_id="gate_0_1_hook_activation",
            message=(
                "Welcome to SVP! Before we begin, Claude Code's hooks need to be "
                "activated. Please review and activate the hooks via Claude Code's "
                "/hooks menu, then confirm."
            ),
            post=_post_cmd("hook_activation"),
        )

    elif sub == "project_context":
        return _invoke_agent_action(
            agent="setup_agent",
            message=(
                "Starting project context creation. The setup agent will guide you "
                "through describing your project."
            ),
            post=_post_cmd("project_context"),
        )

    # Default: start with hook activation
    return _human_gate_action(
        gate_id="gate_0_1_hook_activation",
        message=(
            "Welcome to SVP! Before we begin, Claude Code's hooks need to be "
            "activated."
        ),
        post=_post_cmd("hook_activation"),
    )


def _route_stage_1(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Stage 1: Stakeholder Spec Authoring."""
    sub = state.sub_stage

    if sub in ("dialog", "stakeholder_dialog", None):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message=(
                "Continuing the stakeholder specification dialog. The agent will "
                "ask questions to understand your requirements."
            ),
            post=_post_cmd("stakeholder_dialog"),
        )

    elif sub in ("draft", "spec_draft"):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message="The stakeholder dialog agent is writing the specification draft.",
            post=_post_cmd("stakeholder_draft"),
            prepare=_prepare_cmd("stakeholder_dialog", extra="--mode draft"),
        )

    elif sub in ("approval", "approval_gate"):
        return _human_gate_action(
            gate_id="gate_1_1_spec_draft",
            message=(
                "The stakeholder specification draft is ready for your review. "
                "Please read the document and choose: APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=_post_cmd("spec_approval"),
        )

    elif sub in ("review", "review_request", "fresh_review"):
        return _invoke_agent_action(
            agent="stakeholder_reviewer",
            message=(
                "A fresh stakeholder spec reviewer agent is reading the document cold "
                "and producing a structured critique."
            ),
            post=_post_cmd("spec_review"),
        )

    elif sub in ("post_review", "post_review_gate"):
        return _human_gate_action(
            gate_id="gate_1_2_spec_post_review",
            message=(
                "The reviewer has produced a critique. Please review and choose: "
                "APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=_post_cmd("spec_post_review"),
        )

    elif sub in ("revision", "spec_revision"):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message=(
                "The stakeholder dialog agent will conduct a focused revision of the "
                "specification to address the identified issue."
            ),
            post=_post_cmd("spec_revision"),
            prepare=_prepare_cmd("stakeholder_dialog", extra="--revision-mode"),
        )

    # Default
    return _invoke_agent_action(
        agent="stakeholder_dialog",
        message="Continuing stakeholder spec authoring.",
        post=_post_cmd("stakeholder_dialog"),
    )


def _route_stage_2(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Stage 2: Blueprint Generation and Alignment."""
    sub = state.sub_stage

    if sub in ("dialog", "blueprint_dialog", None):
        return _invoke_agent_action(
            agent="blueprint_author",
            message=(
                "Continuing the blueprint decomposition dialog. The agent will discuss "
                "system structure with you."
            ),
            post=_post_cmd("blueprint_dialog"),
        )

    elif sub == "alignment_check":
        return _invoke_agent_action(
            agent="blueprint_checker",
            message="Running alignment check on the blueprint against the stakeholder spec.",
            post=_post_cmd("alignment_check"),
        )

    elif sub in ("approval", "approval_gate"):
        return _human_gate_action(
            gate_id="gate_2_1_blueprint_approval",
            message=(
                "The blueprint has passed alignment checking. Please review and choose: "
                "APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=_post_cmd("blueprint_approval"),
        )

    elif sub in ("review", "review_request", "fresh_review"):
        return _invoke_agent_action(
            agent="blueprint_reviewer",
            message=(
                "A fresh blueprint reviewer agent is reading the documents cold "
                "and producing a structured critique."
            ),
            post=_post_cmd("blueprint_review"),
        )

    elif sub in ("post_review", "post_review_gate"):
        return _human_gate_action(
            gate_id="gate_2_2_blueprint_post_review",
            message=(
                "The reviewer has produced a critique. Please review and choose: "
                "APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=_post_cmd("blueprint_post_review"),
        )

    elif sub == "iteration_limit":
        return _human_gate_action(
            gate_id="gate_2_3_alignment_exhausted",
            message=(
                f"The alignment loop has reached the iteration limit "
                f"({state.alignment_iteration} attempts). Please review the "
                f"diagnostic summary and decide how to proceed."
            ),
            post=_post_cmd("alignment_exhausted"),
        )

    elif sub in ("spec_revision", "spec_revision_stage2"):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message=(
                "Incorporating working notes and revisions into the stakeholder spec "
                "before the next blueprint iteration."
            ),
            post=_post_cmd("spec_revision_stage2"),
            prepare=_prepare_cmd("stakeholder_dialog", extra="--revision-mode"),
        )

    # Default
    return _invoke_agent_action(
        agent="blueprint_author",
        message="Continuing blueprint generation.",
        post=_post_cmd("blueprint_dialog"),
    )


def _route_pre_stage_3(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Pre-Stage-3: Infrastructure Setup."""
    return _run_command_action(
        command="python scripts/setup_infrastructure.py --project-root .",
        message=(
            "Running infrastructure setup: extracting dependencies, creating Conda "
            "environment, validating imports, and scaffolding project directories."
        ),
        post=_post_cmd("infrastructure_setup"),
    )


def _route_stage_3(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Stage 3: Unit-by-Unit Verification."""
    sub = state.sub_stage
    unit = state.current_unit
    fix = state.fix_ladder_position
    total = state.total_units or "?"

    if unit is None:
        # Default to unit 1 if none set
        unit = 1

    # Fix ladder positions take priority when set
    if fix is not None:
        return _route_fix_ladder(state, project_root, fix, unit)

    # Standard Stage 3 sub-stages
    if sub == "test_generation" or sub is None:
        return _invoke_agent_action(
            agent="test_agent",
            unit=unit,
            message=f"Starting test generation for Unit {unit} (of {total}).",
            post=_post_cmd("test_generation", unit=unit),
        )

    elif sub == "stub_generation":
        return _run_command_action(
            command=f"python scripts/generate_stubs.py --unit {unit}",
            message=f"Generating stubs for Unit {unit}.",
            post=_post_cmd("stub_generation", unit=unit),
            unit=unit,
        )

    elif sub == "red_run":
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=(
                f"PYTHONPATH=scripts python scripts/run_tests.py"
                f" --test-path tests/unit_{unit}/"
                f" --env-name {env_name}"
                f" --status-file .svp/last_status.txt"
                f" --project-root ."
            ),
            message=f"Running red validation for Unit {unit}. All tests must fail against stubs.",
            post=_post_cmd("red_run", unit=unit),
            unit=unit,
        )

    elif sub == "implementation":
        return _invoke_agent_action(
            agent="implementation_agent",
            unit=unit,
            message=f"Starting implementation generation for Unit {unit}.",
            post=_post_cmd("implementation", unit=unit),
        )

    elif sub == "green_run":
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=(
                f"PYTHONPATH=scripts python scripts/run_tests.py"
                f" --test-path tests/unit_{unit}/"
                f" --env-name {env_name}"
                f" --status-file .svp/last_status.txt"
                f" --project-root ."
            ),
            message=f"Running green validation for Unit {unit}. All tests must pass.",
            post=_post_cmd("green_run", unit=unit),
            unit=unit,
        )

    elif sub == "coverage_review":
        return _invoke_agent_action(
            agent="coverage_review",
            unit=unit,
            message=f"Running coverage review for Unit {unit}.",
            post=_post_cmd("coverage_review", unit=unit),
        )

    elif sub == "unit_completion":
        # Write COMMAND_SUCCEEDED to the status file first so that
        # update_state.py can read a valid status when dispatching.
        # This avoids the stale-status-file race condition where the
        # previous phase's status (e.g. COVERAGE_COMPLETE) would be
        # misinterpreted by the unit_completion dispatch path.
        return _run_command_action(
            command=(
                f"echo COMMAND_SUCCEEDED > .svp/last_status.txt &&"
                f" PYTHONPATH=scripts python scripts/update_state.py"
                f" --unit {unit} --phase unit_completion"
                f" --status-file .svp/last_status.txt --project-root ."
            ),
            message=f"Unit {unit} verified. Advancing pipeline.",
            post=None,
            unit=unit,
        )

    elif sub in ("test_validation", "test_validation_gate"):
        return _human_gate_action(
            gate_id="gate_3_1_test_validation",
            unit=unit,
            message=(
                f"A test failed for Unit {unit}. Please review the diagnostic analysis "
                f"and decide whether the test is correct."
            ),
            post=_post_cmd("test_validation", unit=unit),
        )

    elif sub == "diagnostic":
        return _invoke_agent_action(
            agent="diagnostic_agent",
            unit=unit,
            message=f"Running diagnostic analysis for Unit {unit} with three-hypothesis discipline.",
            post=_post_cmd("diagnostic", unit=unit),
        )

    elif sub in ("diagnostic_gate", "diagnostic_decision"):
        return _human_gate_action(
            gate_id="gate_3_2_diagnostic_decision",
            unit=unit,
            message=(
                f"Diagnostic analysis complete for Unit {unit}. Please review the "
                f"three-hypothesis analysis and decide how to proceed."
            ),
            post=_post_cmd("diagnostic_decision", unit=unit),
        )

    elif sub == "unit_verified":
        return _session_boundary_action(
            message=f"Unit {unit} verified. Preparing for the next unit."
        )

    elif sub in ("doc_revision", "restart_stage2"):
        return _session_boundary_action(
            message="Document revision complete. Restarting from Stage 2."
        )

    # Default: start test generation
    return _invoke_agent_action(
        agent="test_agent",
        unit=unit,
        message=f"Starting test generation for Unit {unit} (of {total}).",
        post=_post_cmd("test_generation", unit=unit),
    )


def _route_fix_ladder(
    state: PipelineState,
    project_root: Path,
    fix: str,
    unit: int,
) -> Dict[str, Any]:
    """Route fix ladder positions within Stage 3."""

    if fix == "fresh_test":
        return _invoke_agent_action(
            agent="test_agent",
            unit=unit,
            message=(
                f"Test fix ladder for Unit {unit}: fresh test agent generating "
                f"replacement tests with rejection context."
            ),
            post=_post_cmd("fresh_test", unit=unit),
            prepare=_prepare_cmd("test_agent", unit=unit, extra="--ladder-position fresh_test"),
        )

    elif fix == "hint_test":
        return _invoke_agent_action(
            agent="test_agent",
            unit=unit,
            message=(
                f"Test fix ladder for Unit {unit}: hint-assisted test agent generating "
                f"replacement tests with accumulated context and human hint."
            ),
            post=_post_cmd("hint_test", unit=unit),
            prepare=_prepare_cmd("test_agent", unit=unit, extra="--ladder-position hint_test"),
        )

    elif fix == "fresh_impl":
        return _invoke_agent_action(
            agent="implementation_agent",
            unit=unit,
            message=(
                f"Implementation fix ladder for Unit {unit}: fresh implementation agent "
                f"with diagnostic guidance."
            ),
            post=_post_cmd("fresh_impl", unit=unit),
            prepare=_prepare_cmd("implementation_agent", unit=unit, extra="--ladder-position fresh_impl"),
        )

    elif fix == "diagnostic":
        return _invoke_agent_action(
            agent="diagnostic_agent",
            unit=unit,
            message=(
                f"Diagnostic escalation for Unit {unit}: three-hypothesis analysis "
                f"of accumulated failures."
            ),
            post=_post_cmd("diagnostic_escalation", unit=unit),
            prepare=_prepare_cmd("diagnostic_agent", unit=unit, extra="--ladder-position diagnostic"),
        )

    elif fix == "diagnostic_impl":
        return _invoke_agent_action(
            agent="implementation_agent",
            unit=unit,
            message=(
                f"Diagnostic-guided implementation for Unit {unit}: fresh agent with "
                f"diagnostic guidance and optional human hint."
            ),
            post=_post_cmd("diagnostic_impl", unit=unit),
            prepare=_prepare_cmd("implementation_agent", unit=unit, extra="--ladder-position diagnostic_impl"),
        )

    raise ValueError(
        f"Unrecognized fix_ladder_position: {fix}"
    )


def _route_stage_4(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Stage 4: Integration Testing."""
    sub = state.sub_stage

    if sub == "integration_test_generation" or sub is None:
        return _invoke_agent_action(
            agent="integration_test_author",
            message="Generating integration tests covering cross-unit interactions.",
            post=_post_cmd("integration_test_generation"),
        )

    elif sub == "integration_run":
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=(
                f"PYTHONPATH=scripts python scripts/run_tests.py"
                f" --test-path tests/integration/"
                f" --env-name {env_name}"
                f" --status-file .svp/last_status.txt"
                f" --project-root ."
            ),
            message="Running integration tests.",
            post=_post_cmd("integration_run"),
        )

    elif sub in ("failure_gate", "integration_failure"):
        return _human_gate_action(
            gate_id="gate_4_1_integration_failure",
            message=(
                "Integration tests failed. Please review the diagnostic analysis "
                "and decide how to proceed."
            ),
            post=_post_cmd("integration_failure"),
        )

    elif sub == "assembly_fix":
        return _invoke_agent_action(
            agent="implementation_agent",
            message="Applying assembly fix for integration test failure.",
            post=_post_cmd("assembly_fix"),
            prepare=_prepare_cmd("implementation_agent", extra="--assembly-fix"),
        )

    elif sub == "assembly_exhausted":
        return _human_gate_action(
            gate_id="gate_4_2_assembly_exhausted",
            message=(
                "The assembly fix ladder is exhausted. Please decide how to proceed."
            ),
            post=_post_cmd("assembly_exhausted"),
        )

    elif sub == "stage_complete":
        return _session_boundary_action(
            message="Integration tests passed. Advancing to Stage 5 (Repository Delivery)."
        )

    # Default
    return _invoke_agent_action(
        agent="integration_test_author",
        message="Generating integration tests covering cross-unit interactions.",
        post=_post_cmd("integration_test_generation"),
    )


def _route_stage_5(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route Stage 5: Repository Delivery."""
    sub = state.sub_stage

    if sub in ("repo_assembly", None):
        return _invoke_agent_action(
            agent="git_repo_agent",
            message="Assembling the git repository.",
            post=_post_cmd("repo_assembly"),
        )

    elif sub == "test_gate":
        return _human_gate_action(
            gate_id="gate_5_1_repo_test",
            message=(
                "The repository has been assembled. Please run the tests in the "
                "delivered repository and report the result."
            ),
            post=_post_cmd("repo_test"),
        )

    elif sub == "fix_cycle":
        return _invoke_agent_action(
            agent="git_repo_agent",
            message="Fixing repository assembly issues.",
            post=_post_cmd("repo_fix"),
        )

    elif sub == "assembly_exhausted":
        return _human_gate_action(
            gate_id="gate_5_2_assembly_exhausted",
            message=(
                "Repository assembly fix cycle exhausted. Please decide how to proceed."
            ),
            post=_post_cmd("assembly_exhausted"),
        )

    elif sub == "complete":
        return _pipeline_complete_action(
            message=(
                "Pipeline complete! The repository has been delivered. "
                "Use /svp:bug for post-delivery bug investigation or "
                "/svp:clean to manage the workspace."
            )
        )

    # Default
    return _invoke_agent_action(
        agent="git_repo_agent",
        message="Assembling the git repository.",
        post=_post_cmd("repo_assembly"),
    )


# ---------------------------------------------------------------------------
# Debug loop routing
# ---------------------------------------------------------------------------

def _route_debug(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Route debug session states.

    The routing script handles debug loop states through the same mechanism as
    regular stage routing: reads pipeline_state.json, checks for debug_session,
    and emits appropriate action blocks. No special mechanism -- just additional
    state cases.
    """
    debug = state.debug_session
    if debug is None:
        return _route_stage(state, project_root)

    phase = debug.phase

    if phase == "triage_readonly":
        if not debug.authorized:
            # Present Gate 6.0: debug permission
            return _human_gate_action(
                gate_id="gate_6_0_debug_permission",
                message=(
                    "A bug has been reported. The triage agent has gathered initial "
                    "information. Do you want to authorize debug write permissions?"
                ),
                post=_post_cmd("debug_permission"),
            )
        # If already authorized somehow, move to triage
        return _invoke_agent_action(
            agent="bug_triage",
            message="Starting bug triage with the triage agent.",
            post=_post_cmd("bug_triage"),
        )

    elif phase == "triage":
        return _invoke_agent_action(
            agent="bug_triage",
            message="Continuing bug triage dialog.",
            post=_post_cmd("bug_triage"),
        )

    elif phase == "regression_test":
        # Route depends on sub-phase. Test generation then validation.
        sub = state.sub_stage
        if sub == "regression_test_validation":
            return _human_gate_action(
                gate_id="gate_6_1_regression_test",
                message=(
                    "A regression test has been written and confirmed to fail. "
                    "Please review the test assertion."
                ),
                post=_post_cmd("regression_test_validation"),
            )
        elif sub == "debug_classification":
            return _human_gate_action(
                gate_id="gate_6_2_debug_classification",
                message=(
                    "The regression test is confirmed. Please classify the fix type."
                ),
                post=_post_cmd("debug_classification"),
            )
        # Default: generate regression test
        return _invoke_agent_action(
            agent="test_agent",
            message="Generating regression test for the reported bug.",
            post=_post_cmd("regression_test_generation"),
        )

    elif phase == "stage3_reentry":
        # Re-enter Stage 3 for the affected unit
        return _route_stage_3(state, project_root)

    elif phase == "repair":
        sub = state.sub_stage
        if sub == "repair_exhausted":
            return _human_gate_action(
                gate_id="gate_6_3_repair_exhausted",
                message=(
                    "The repair agent has exhausted its fix cycle. "
                    "Please decide how to proceed."
                ),
                post=_post_cmd("repair_exhausted"),
            )
        return _invoke_agent_action(
            agent="repair_agent",
            message="Repair agent is applying the fix.",
            post=_post_cmd("repair"),
        )

    elif phase == "complete":
        return _pipeline_complete_action(
            message="Debug session complete. The fix has been applied and verified."
        )

    # Non-reproducible bug
    if state.sub_stage == "non_reproducible":
        return _human_gate_action(
            gate_id="gate_6_4_non_reproducible",
            message=(
                "The bug could not be reproduced. Please decide how to proceed."
            ),
            post=_post_cmd("non_reproducible"),
        )

    # Default: continue triage
    return _invoke_agent_action(
        agent="bug_triage",
        message="Continuing bug triage.",
        post=_post_cmd("bug_triage"),
    )


# ---------------------------------------------------------------------------
# format_action_block
# ---------------------------------------------------------------------------

def format_action_block(action: Dict[str, Any]) -> str:
    """Convert the action dict to the structured text format (spec Section 17).

    Includes the REMINDER block for invoke_agent, run_command, and human_gate.
    Omits REMINDER for session_boundary and pipeline_complete.
    """
    lines: List[str] = []
    action_type = action.get("ACTION", "")

    lines.append(f"ACTION: {action_type}")

    if action.get("AGENT") is not None:
        lines.append(f"AGENT: {action['AGENT']}")
    if action.get("PREPARE") is not None:
        lines.append(f"PREPARE: {action['PREPARE']}")
    if action.get("TASK_PROMPT_FILE") is not None:
        lines.append(f"TASK_PROMPT_FILE: {action['TASK_PROMPT_FILE']}")
    if action.get("COMMAND") is not None:
        lines.append(f"COMMAND: {action['COMMAND']}")
    if action.get("POST") is not None:
        lines.append(f"POST: {action['POST']}")
    if action.get("GATE") is not None:
        lines.append(f"GATE: {action['GATE']}")
    if action.get("UNIT") is not None:
        lines.append(f"UNIT: {action['UNIT']}")
    if action.get("PROMPT_FILE") is not None:
        lines.append(f"PROMPT_FILE: {action['PROMPT_FILE']}")
    if action.get("OPTIONS") is not None:
        opts = action["OPTIONS"]
        if isinstance(opts, list):
            lines.append(f"OPTIONS: {', '.join(opts)}")
        else:
            lines.append(f"OPTIONS: {opts}")

    lines.append(f"MESSAGE: {action.get('MESSAGE', '')}")

    # Add REMINDER for non-terminal action types
    if action_type in ("invoke_agent", "run_command", "human_gate"):
        lines.append(_REMINDER_TEXT)

    result = "\n".join(lines)

    # Post-condition
    assert "REMINDER:" in result or "session_boundary" in action_type or "pipeline_complete" in action_type, \
        "Non-terminal actions must include REMINDER block"

    return result


# ---------------------------------------------------------------------------
# Dispatch functions (update_state.py)
# ---------------------------------------------------------------------------

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
    # If a gate_id is provided, this is a gate response
    if gate_id is not None:
        return dispatch_gate_response(state, gate_id, status_line, project_root)

    # Check if it matches a command status pattern
    for pattern in COMMAND_STATUS_PATTERNS:
        if status_line.startswith(pattern):
            return dispatch_command_status(state, status_line, unit, phase, project_root)

    # Check if it matches the cross-agent status
    if status_line.startswith(CROSS_AGENT_STATUS):
        # HINT_BLUEPRINT_CONFLICT -- the main session should present
        # the conflict as a decision gate. For now, return state unchanged.
        return state

    # Try agent status dispatch
    return dispatch_agent_status(state, "", status_line, unit, phase, project_root)


def dispatch_gate_response(
    state: PipelineState,
    gate_id: str,
    response: str,
    project_root: Path,
) -> PipelineState:
    """Validate the response against GATE_VOCABULARY[gate_id] using exact
    string matching. If the response is not in the vocabulary, raises ValueError.

    Calls appropriate Unit 3 transition functions based on gate_id and response.
    """
    # Bug 1 invariant: validate gate_id is in vocabulary
    if gate_id not in GATE_VOCABULARY:
        raise ValueError(
            f"Invalid gate response '{response}' for gate {gate_id}. "
            f"Valid options: gate not found in vocabulary"
        )

    valid_options = GATE_VOCABULARY[gate_id]

    # Bug 1 invariant: validate response is in the vocabulary
    if response not in valid_options:
        options_str = ", ".join(valid_options)
        raise ValueError(
            f"Invalid gate response '{response}' for gate {gate_id}. "
            f"Valid options: {options_str}"
        )

    # Dispatch based on gate_id and response
    # Gate 0.1: Hook activation
    if gate_id == "gate_0_1_hook_activation":
        if response == "HOOKS ACTIVATED":
            return advance_sub_stage(state, "project_context", project_root)
        else:  # HOOKS FAILED
            # Stay in hook_activation state
            return state

    # Gate 0.2: Context approval
    elif gate_id == "gate_0_2_context_approval":
        if response == "CONTEXT APPROVED":
            return advance_stage(state, project_root)
        elif response == "CONTEXT REJECTED":
            # Restart project context creation
            return advance_sub_stage(state, "project_context", project_root)
        else:  # CONTEXT NOT READY
            # Pipeline pauses
            return state

    # Gate 1.1: Spec draft approval
    elif gate_id == "gate_1_1_spec_draft":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "revision", project_root)
        else:  # FRESH REVIEW
            return advance_sub_stage(state, "fresh_review", project_root)

    # Gate 1.2: Spec post-review
    elif gate_id == "gate_1_2_spec_post_review":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "revision", project_root)
        else:  # FRESH REVIEW
            return advance_sub_stage(state, "fresh_review", project_root)

    # Gate 2.1: Blueprint approval
    elif gate_id == "gate_2_1_blueprint_approval":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "blueprint_dialog", project_root)
        else:  # FRESH REVIEW
            return advance_sub_stage(state, "fresh_review", project_root)

    # Gate 2.2: Blueprint post-review
    elif gate_id == "gate_2_2_blueprint_post_review":
        if response == "APPROVE":
            return advance_stage(state, project_root)
        elif response == "REVISE":
            return advance_sub_stage(state, "blueprint_dialog", project_root)
        else:  # FRESH REVIEW
            return advance_sub_stage(state, "fresh_review", project_root)

    # Gate 2.3: Alignment exhausted
    elif gate_id == "gate_2_3_alignment_exhausted":
        if response == "REVISE SPEC":
            return advance_sub_stage(state, "spec_revision", project_root)
        elif response == "RESTART SPEC":
            return restart_from_stage(state, "1", "Full spec restart from alignment exhaustion", project_root)
        else:  # RETRY BLUEPRINT
            new_state = reset_alignment_iteration(state)
            return advance_sub_stage(new_state, "blueprint_dialog", project_root)

    # Gate 3.1: Test validation
    elif gate_id == "gate_3_1_test_validation":
        if response == "TEST CORRECT":
            # Test is correct, implementation needs fixing -> advance fix ladder
            return advance_fix_ladder(state, "fresh_impl")
        else:  # TEST WRONG
            # Test is wrong -> test fix ladder
            return advance_fix_ladder(state, "fresh_test")

    # Gate 3.2: Diagnostic decision
    elif gate_id == "gate_3_2_diagnostic_decision":
        if response == "FIX IMPLEMENTATION":
            return advance_fix_ladder(state, "diagnostic_impl")
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(state, "2", "Blueprint fix from diagnostic", project_root)
        else:  # FIX SPEC
            return restart_from_stage(state, "1", "Spec fix from diagnostic", project_root)

    # Gate 4.1: Integration failure
    elif gate_id == "gate_4_1_integration_failure":
        if response == "ASSEMBLY FIX":
            return advance_sub_stage(state, "assembly_fix", project_root)
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(state, "2", "Blueprint fix from integration failure", project_root)
        else:  # FIX SPEC
            return restart_from_stage(state, "1", "Spec fix from integration failure", project_root)

    # Gate 4.2: Assembly exhausted
    elif gate_id == "gate_4_2_assembly_exhausted":
        if response == "FIX BLUEPRINT":
            return restart_from_stage(state, "2", "Blueprint fix from assembly exhaustion", project_root)
        else:  # FIX SPEC
            return restart_from_stage(state, "1", "Spec fix from assembly exhaustion", project_root)

    # Gate 5.1: Repo test
    elif gate_id == "gate_5_1_repo_test":
        if response == "TESTS PASSED":
            return advance_sub_stage(state, "complete", project_root)
        else:  # TESTS FAILED
            return advance_sub_stage(state, "fix_cycle", project_root)

    # Gate 5.2: Assembly exhausted (repo)
    elif gate_id == "gate_5_2_assembly_exhausted":
        if response == "RETRY ASSEMBLY":
            return advance_sub_stage(state, "repo_assembly", project_root)
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(state, "2", "Blueprint fix from repo assembly exhaustion", project_root)
        else:  # FIX SPEC
            return restart_from_stage(state, "1", "Spec fix from repo assembly exhaustion", project_root)

    # Gate 6.0: Debug permission
    elif gate_id == "gate_6_0_debug_permission":
        if response == "AUTHORIZE DEBUG":
            return authorize_debug_session(state)
        else:  # ABANDON DEBUG
            return abandon_debug_session(state)

    # Gate 6.1: Regression test validation
    elif gate_id == "gate_6_1_regression_test":
        if response == "TEST CORRECT":
            return advance_sub_stage(state, "debug_classification", project_root)
        else:  # TEST WRONG
            # Return to triage
            return update_debug_phase(state, "triage")

    # Gate 6.2: Debug classification
    elif gate_id == "gate_6_2_debug_classification":
        if response == "FIX UNIT":
            return update_debug_phase(state, "stage3_reentry")
        elif response == "FIX BLUEPRINT":
            return restart_from_stage(state, "2", "Blueprint fix from debug classification", project_root)
        else:  # FIX SPEC
            return restart_from_stage(state, "1", "Spec fix from debug classification", project_root)

    # Gate 6.3: Repair exhausted
    elif gate_id == "gate_6_3_repair_exhausted":
        if response == "RETRY REPAIR":
            return update_debug_phase(state, "repair")
        elif response == "RECLASSIFY BUG":
            return update_debug_phase(state, "triage")
        else:  # ABANDON DEBUG
            return abandon_debug_session(state)

    # Gate 6.4: Non-reproducible
    elif gate_id == "gate_6_4_non_reproducible":
        if response == "RETRY TRIAGE":
            return update_debug_phase(state, "triage")
        else:  # ABANDON DEBUG
            return abandon_debug_session(state)

    # Should not reach here given the vocabulary validation above
    return state


def dispatch_agent_status(
    state: PipelineState,
    agent_type: str,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Parse the terminal status line and call appropriate Unit 3 transition
    functions.
    """
    # Validate the status line is known
    line_recognized = False

    # Check cross-agent status
    if status_line.startswith(CROSS_AGENT_STATUS):
        line_recognized = True

    # Check all agent status lines
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

    # Dispatch based on phase
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
    """Parse command result status lines and call appropriate Unit 3 transition
    functions.
    """
    # Validate the status line matches a known pattern
    matched = False
    for pattern in COMMAND_STATUS_PATTERNS:
        if status_line.startswith(pattern):
            matched = True
            break

    if not matched:
        raise ValueError(f"Unknown agent status line: {status_line}")

    # Dispatch based on phase
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


# ---------------------------------------------------------------------------
# Phase handlers
# ---------------------------------------------------------------------------

def _handle_test_generation(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle TEST_GENERATION_COMPLETE status."""
    return advance_sub_stage(state, "stub_generation", project_root)


def _handle_implementation(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle IMPLEMENTATION_COMPLETE status."""
    return advance_sub_stage(state, "green_run", project_root)


def _handle_coverage_review(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle COVERAGE_COMPLETE status."""
    if status.startswith("COVERAGE_COMPLETE: no gaps"):
        return advance_sub_stage(state, "unit_completion", project_root)
    elif status.startswith("COVERAGE_COMPLETE: tests added"):
        # Need to re-run green validation for the new tests
        return advance_sub_stage(state, "green_run", project_root)
    return advance_sub_stage(state, "unit_completion", project_root)


def _handle_diagnostic(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle DIAGNOSIS_COMPLETE status."""
    return advance_sub_stage(state, "diagnostic_gate", project_root)


def _handle_alignment_check(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    """Handle alignment check results."""
    if status.startswith("ALIGNMENT_CONFIRMED"):
        return advance_sub_stage(state, "approval", project_root)
    elif status.startswith("ALIGNMENT_FAILED: spec"):
        try:
            new_state = increment_alignment_iteration(state)
        except TransitionError:
            # Iteration limit reached
            return advance_sub_stage(state, "iteration_limit", project_root)
        return advance_sub_stage(new_state, "spec_revision_stage2", project_root)
    elif status.startswith("ALIGNMENT_FAILED: blueprint"):
        try:
            new_state = increment_alignment_iteration(state)
        except TransitionError:
            # Iteration limit reached
            return advance_sub_stage(state, "iteration_limit", project_root)
        return advance_sub_stage(new_state, "blueprint_dialog", project_root)
    return state


def _handle_stakeholder_dialog(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    """Handle stakeholder dialog status."""
    if status == "SPEC_DRAFT_COMPLETE":
        return advance_sub_stage(state, "approval", project_root)
    elif status == "SPEC_REVISION_COMPLETE":
        return advance_sub_stage(state, "approval", project_root)
    return state


def _handle_project_context(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    """Handle setup agent status."""
    if status == "PROJECT_CONTEXT_COMPLETE":
        return advance_stage(state, project_root)
    elif status == "PROJECT_CONTEXT_REJECTED":
        # Human not providing sufficient content; pipeline pauses
        return state
    return state


def _handle_red_run(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle red-run status."""
    if status.startswith("TESTS_FAILED:"):
        # Expected: tests correctly fail against stub
        new_state = reset_red_run_retries(state)
        return advance_sub_stage(new_state, "implementation", project_root)
    elif status.startswith("TESTS_PASSED:"):
        # Defective tests -- some passed against stub
        new_state = increment_red_run_retries(state)
        return advance_sub_stage(new_state, "test_generation", project_root)
    elif status.startswith("TESTS_ERROR:"):
        new_state = increment_red_run_retries(state)
        return advance_sub_stage(new_state, "test_generation", project_root)
    return state


def _handle_green_run(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle green-run status."""
    if status.startswith("TESTS_PASSED:"):
        return advance_sub_stage(state, "coverage_review", project_root)
    elif status.startswith("TESTS_FAILED:"):
        # Tests failed -> test validation gate
        return advance_sub_stage(state, "test_validation", project_root)
    elif status.startswith("TESTS_ERROR:"):
        return advance_sub_stage(state, "test_validation", project_root)
    return state


def _handle_infrastructure(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    """Handle infrastructure setup status."""
    if status.startswith("COMMAND_SUCCEEDED"):
        return advance_stage(state, project_root)
    elif status.startswith("COMMAND_FAILED:"):
        # Infrastructure failed -- need blueprint revision
        return state
    return state


def _handle_stub_generation(
    state: PipelineState, status: str, unit: Optional[int], project_root: Path
) -> PipelineState:
    """Handle stub generation status."""
    if status.startswith("COMMAND_SUCCEEDED"):
        return advance_sub_stage(state, "red_run", project_root)
    return state


def _handle_integration_run(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    """Handle integration test run status."""
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
    """Handle bug triage status."""
    if status.startswith("TRIAGE_COMPLETE: build_env"):
        new_state = set_debug_classification(state, "build_env", [])
        return update_debug_phase(new_state, "repair")
    elif status.startswith("TRIAGE_COMPLETE: single_unit"):
        return update_debug_phase(state, "regression_test")
    elif status.startswith("TRIAGE_COMPLETE: cross_unit"):
        return update_debug_phase(state, "regression_test")
    elif status == "TRIAGE_NEEDS_REFINEMENT":
        # Return to triage dialog
        return state
    elif status == "TRIAGE_NON_REPRODUCIBLE":
        return advance_sub_stage(state, "non_reproducible", project_root)
    return state


def _handle_repair(
    state: PipelineState, status: str, project_root: Path
) -> PipelineState:
    """Handle repair agent status."""
    if status == "REPAIR_COMPLETE":
        return update_debug_phase(state, "complete")
    elif status == "REPAIR_FAILED":
        return advance_sub_stage(state, "repair_exhausted", project_root)
    elif status == "REPAIR_RECLASSIFY":
        return update_debug_phase(state, "triage")
    return state


# ---------------------------------------------------------------------------
# run_pytest
# ---------------------------------------------------------------------------

def run_pytest(
    test_path: Path,
    env_name: str,
    project_root: Path,
) -> str:
    """Execute conda run -n {env_name} pytest {test_path} -v and construct
    the appropriate command result status line from the output.

    Never uses bare python or pytest.
    """
    cmd = ["conda", "run", "-n", env_name, "pytest", str(test_path), "-v"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return "TESTS_ERROR: Test execution timed out"
    except FileNotFoundError:
        return "TESTS_ERROR: conda not found"
    except Exception as e:
        return f"TESTS_ERROR: {str(e)}"

    stdout = result.stdout
    stderr = result.stderr
    output = stdout + "\n" + stderr

    if result.returncode == 0:
        # All tests passed
        passed_count = _parse_passed_count(output)
        return f"TESTS_PASSED: {passed_count} passed"
    else:
        # Check if this is a test failure or an error
        if _is_collection_error(output):
            error_summary = _extract_error_summary(output)
            return f"TESTS_ERROR: {error_summary}"
        else:
            passed_count = _parse_passed_count(output)
            failed_count = _parse_failed_count(output)
            return f"TESTS_FAILED: {passed_count} passed, {failed_count} failed"


def _parse_passed_count(output: str) -> int:
    """Parse the number of passed tests from pytest output."""
    match = re.search(r"(\d+) passed", output)
    if match:
        return int(match.group(1))
    return 0


def _parse_failed_count(output: str) -> int:
    """Parse the number of failed tests from pytest output."""
    match = re.search(r"(\d+) failed", output)
    if match:
        return int(match.group(1))
    return 0


def _is_collection_error(output: str) -> bool:
    """Check if the output indicates a collection/import error rather than
    a test failure."""
    error_indicators = [
        "ERROR collecting",
        "ImportError",
        "ModuleNotFoundError",
        "SyntaxError",
        "no tests ran",
    ]
    # Only count as collection error if there are no actual test failures
    has_failed = "failed" in output.lower() and re.search(r"\d+ failed", output)
    if has_failed:
        return False
    for indicator in error_indicators:
        if indicator in output:
            return True
    return False


def _extract_error_summary(output: str) -> str:
    """Extract a summary of the error from pytest output."""
    lines = output.strip().split("\n")
    for line in lines:
        line = line.strip()
        if any(keyword in line for keyword in ["ERROR", "ImportError", "ModuleNotFoundError", "SyntaxError"]):
            return line[:200]  # Truncate to reasonable length
    # Fall back to last non-empty line
    for line in reversed(lines):
        line = line.strip()
        if line:
            return line[:200]
    return "Unknown error"


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def routing_main() -> None:
    """CLI entry point for routing.py."""
    parser = argparse.ArgumentParser(description="SVP Routing Script")
    parser.add_argument("--project-root", type=str, default=".",
                        help="Path to project root")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    _check_scripts_sync(project_root)
    state = load_state(project_root)
    action = route(state, project_root)
    output = format_action_block(action)
    print(output)


def update_state_main() -> None:
    """CLI entry point for update_state.py."""
    parser = argparse.ArgumentParser(description="SVP State Update Script")
    parser.add_argument("--phase", type=str, required=True,
                        help="The phase that produced the status")
    parser.add_argument("--status-file", type=str, required=True,
                        help="Path to the status file")
    parser.add_argument("--unit", type=int, default=None,
                        help="Unit number (if applicable)")
    parser.add_argument("--gate", type=str, default=None,
                        help="Gate ID (if applicable)")
    parser.add_argument("--project-root", type=str, default=".",
                        help="Path to project root")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    state = load_state(project_root)

    status_file = Path(args.status_file)
    if status_file.exists():
        status_line = status_file.read_text(encoding="utf-8").strip()
        # Get the last non-empty line
        lines = [l.strip() for l in status_line.split("\n") if l.strip()]
        if lines:
            status_line = lines[-1]
        else:
            status_line = ""
    else:
        status_line = ""

    if status_line:
        new_state = dispatch_status(
            state,
            status_line,
            gate_id=args.gate,
            unit=args.unit,
            phase=args.phase,
            project_root=project_root,
        )
        save_state(new_state, project_root)
    else:
        # No status line -- save state unchanged
        save_state(state, project_root)


def run_tests_main() -> None:
    """CLI entry point for run_tests.py."""
    parser = argparse.ArgumentParser(description="SVP Test Runner")
    parser.add_argument("--test-path", type=str, required=True,
                        help="Path to test directory or file")
    parser.add_argument("--env-name", type=str, required=True,
                        help="Conda environment name")
    parser.add_argument("--status-file", type=str, default=None,
                        help="Path to write the status line")
    parser.add_argument("--project-root", type=str, default=".",
                        help="Path to project root")
    args = parser.parse_args()

    test_path = Path(args.test_path)
    project_root = Path(args.project_root)

    status_line = run_pytest(test_path, args.env_name, project_root)

    if args.status_file:
        status_path = Path(args.status_file)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(status_line + "\n", encoding="utf-8")

    print(status_line)


if __name__ == "__main__":
    routing_main()
