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
from svp_core.action import (
    _invoke_agent_action as _base_invoke_agent_action,
    _run_command_action as _base_run_command_action,
    _human_gate_action as _base_human_gate_action,
    _session_boundary_action as _base_session_boundary_action,
    _pipeline_complete_action as _base_pipeline_complete_action,
    format_action_block as _base_format_action_block,
    REMINDER_TEXT,
)
from svp_core.action import ACTION_TYPES  # noqa: F401

# Re-export vocabulary constants from svp_core
from svp_core.vocabulary import (  # noqa: F401
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
    _describe_next_action,
    _generate_context_summary,
)

# Re-export dispatch functions from svp_core
from svp_core.dispatch import (  # noqa: F401
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
)

# Re-export router from svp_core
from svp_core.router import (  # noqa: F401
    route as _core_route,
    RouterCommandBuilders,
)
from svp_host_claude.command_builders import (
    gate_prepare_cmd as _gate_prepare_cmd,
    post_cmd as _post_cmd,
    prepare_cmd as _prepare_cmd,
)

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
        parts = [
            "WARNING: KNOWN_AGENT_TYPES drift detected between "
            "src/unit_9/stub.py (canonical) and scripts/prepare_task.py (runtime)."
        ]
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
    cmd_builders = RouterCommandBuilders(
        post_cmd=_post_cmd,
        prepare_cmd=_prepare_cmd,
        gate_prepare_cmd=_gate_prepare_cmd,
    )
    return _core_route(state, project_root, cmd_builders)


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
    return _base_invoke_agent_action(
        agent=agent,
        message=message,
        unit=unit,
        prepare=prepare,
        post=post,
        task_prompt_file=task_prompt_file,
        prepare_cmd_builder=lambda a, unit=unit: _prepare_cmd(a, unit=unit),
        post_cmd_builder=lambda phase, unit=unit: _post_cmd(phase, unit=unit),
    )


def _run_command_action(
    command: str,
    message: str,
    post: Optional[str] = None,
    unit: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a run_command action dict."""
    return _base_run_command_action(
        command=command,
        message=message,
        post=post,
        unit=unit,
    )


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
    return _base_human_gate_action(
        gate_id=gate_id,
        message=message,
        unit=unit,
        prepare=prepare,
        post=post,
        prompt_file=prompt_file,
        gate_vocabulary=GATE_VOCABULARY,
        gate_prepare_cmd_builder=lambda g, unit=unit: _gate_prepare_cmd(g, unit=unit),
    )


def _session_boundary_action(message: str) -> Dict[str, Any]:
    """Build a session_boundary action dict."""
    return _base_session_boundary_action(message=message)


def _pipeline_complete_action(message: str) -> Dict[str, Any]:
    """Build a pipeline_complete action dict."""
    return _base_pipeline_complete_action(message=message)


# ---------------------------------------------------------------------------
# CLI entry points
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
            "Welcome to SVP! Before we begin, Claude Code's hooks need to be activated."
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

    elif sub in ("revision", "blueprint_revision"):
        # Blueprint revision triggered by REVISE at approval/post-review gate
        return _invoke_agent_action(
            agent="blueprint_author",
            message=(
                "The blueprint author agent will conduct a focused revision of the "
                "blueprint to address the identified issues."
            ),
            post=_post_cmd("blueprint_revision"),
            prepare=_prepare_cmd("blueprint_author", extra="--revision-mode"),
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
            prepare=_prepare_cmd(
                "test_agent", unit=unit, extra="--ladder-position fresh_test"
            ),
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
            prepare=_prepare_cmd(
                "test_agent", unit=unit, extra="--ladder-position hint_test"
            ),
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
            prepare=_prepare_cmd(
                "implementation_agent", unit=unit, extra="--ladder-position fresh_impl"
            ),
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
            prepare=_prepare_cmd(
                "diagnostic_agent", unit=unit, extra="--ladder-position diagnostic"
            ),
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
            prepare=_prepare_cmd(
                "implementation_agent",
                unit=unit,
                extra="--ladder-position diagnostic_impl",
            ),
        )

    raise ValueError(f"Unrecognized fix_ladder_position: {fix}")


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
            message=("The bug could not be reproduced. Please decide how to proceed."),
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
    return _base_format_action_block(action=action, reminder_text=_REMINDER_TEXT)


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
        if any(
            keyword in line
            for keyword in [
                "ERROR",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
            ]
        ):
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
    parser.add_argument(
        "--project-root", type=str, default=".", help="Path to project root"
    )
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
    parser.add_argument(
        "--phase", type=str, required=True, help="The phase that produced the status"
    )
    parser.add_argument(
        "--status-file", type=str, required=True, help="Path to the status file"
    )
    parser.add_argument(
        "--unit", type=int, default=None, help="Unit number (if applicable)"
    )
    parser.add_argument(
        "--gate", type=str, default=None, help="Gate ID (if applicable)"
    )
    parser.add_argument(
        "--project-root", type=str, default=".", help="Path to project root"
    )
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
    parser.add_argument(
        "--test-path", type=str, required=True, help="Path to test directory or file"
    )
    parser.add_argument(
        "--env-name", type=str, required=True, help="Conda environment name"
    )
    parser.add_argument(
        "--status-file", type=str, default=None, help="Path to write the status line"
    )
    parser.add_argument(
        "--project-root", type=str, default=".", help="Path to project root"
    )
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
