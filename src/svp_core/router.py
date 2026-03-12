"""Stage routing logic for SVP pipeline."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from svp_core.pipeline_state import PipelineState
from svp_core.action import (
    ACTION_TYPES,
    _invoke_agent_action,
    _run_command_action,
    _human_gate_action,
    _session_boundary_action,
    _pipeline_complete_action,
)
from svp_core.vocabulary import GATE_VOCABULARY


@dataclass(frozen=True)
class RouterCommandBuilders:
    """Immutable config carrying command builder callables for the router.

    This allows the host to inject host-specific command builders while
    keeping the router logic host-agnostic.
    """

    post_cmd: Callable[..., str]
    prepare_cmd: Callable[..., str]
    gate_prepare_cmd: Callable[..., str]


def derive_env_name_from_state(state: PipelineState) -> str:
    """Derive the conda environment name from the project name in state.

    Uses the canonical derivation (spec Section 4.3):
    project_name.lower().replace(" ", "_").replace("-", "_")
    """
    project_name = state.project_name or "svp_project"
    return project_name.lower().replace(" ", "_").replace("-", "_")


def route(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Read pipeline state and determine the next action.

    Returns a dict with all fields needed for the action block:
    ACTION, AGENT, PREPARE, TASK_PROMPT_FILE, POST, COMMAND, GATE, UNIT,
    OPTIONS, PROMPT_FILE, MESSAGE.

    Handles all pipeline states including debug loop states.
    """
    assert project_root.is_dir(), "Project root must exist"

    if state.debug_session is not None:
        result = _route_debug(state, project_root, cmd_builders)
    else:
        result = _route_stage(state, project_root, cmd_builders)

    assert "ACTION" in result, "Route output must contain ACTION"
    assert result["ACTION"] in ACTION_TYPES, (
        f"ACTION must be a valid action type, got: {result['ACTION']}"
    )

    return result


def _route_stage(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Dispatch to the appropriate routing handler based on stage."""
    stage = state.stage
    sub = state.sub_stage

    if stage == "0":
        return _route_stage_0(state, project_root, cmd_builders)
    elif stage == "1":
        return _route_stage_1(state, project_root, cmd_builders)
    elif stage == "2":
        return _route_stage_2(state, project_root, cmd_builders)
    elif stage == "pre_stage_3":
        return _route_pre_stage_3(state, project_root, cmd_builders)
    elif stage == "3":
        return _route_stage_3(state, project_root, cmd_builders)
    elif stage == "4":
        return _route_stage_4(state, project_root, cmd_builders)
    elif stage == "5":
        return _route_stage_5(state, project_root, cmd_builders)
    else:
        raise ValueError(f"Unrecognized pipeline state: stage={stage}, sub_stage={sub}")


def _route_stage_0(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route Stage 0: Setup."""
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None

    if sub == "hook_activation":
        return _human_gate_action(
            gate_id="gate_0_1_hook_activation",
            message=(
                "Welcome to SVP! Before we begin, Claude Code's hooks need to be "
                "activated. Please review and activate the hooks via Claude Code's "
                "/hooks menu, then confirm."
            ),
            post=post_fn("hook_activation") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "project_context":
        return _invoke_agent_action(
            agent="setup_agent",
            message=(
                "Starting project context creation. The setup agent will guide you "
                "through describing your project."
            ),
            post=post_fn("project_context") if post_fn else None,
            prepare_cmd_builder=cmd_builders.prepare_cmd if cmd_builders else None,
            post_cmd_builder=post_fn,
        )

    return _human_gate_action(
        gate_id="gate_0_1_hook_activation",
        message=(
            "Welcome to SVP! Before we begin, Claude Code's hooks need to be activated."
        ),
        post=post_fn("hook_activation") if post_fn else None,
        gate_vocabulary=GATE_VOCABULARY,
        gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
        if cmd_builders
        else None,
        post_cmd_builder=post_fn,
    )


def _route_stage_1(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route Stage 1: Stakeholder Spec Authoring."""
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None
    prep_fn = cmd_builders.prepare_cmd if cmd_builders else None

    if sub in ("dialog", "stakeholder_dialog", None):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message=(
                "Continuing the stakeholder specification dialog. The agent will "
                "ask questions to understand your requirements."
            ),
            post=post_fn("stakeholder_dialog") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub in ("draft", "spec_draft"):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message="The stakeholder dialog agent is writing the specification draft.",
            post=post_fn("stakeholder_draft") if post_fn else None,
            prepare=lambda: (
                prep_fn("stakeholder_dialog", extra="--mode draft") if prep_fn else None
            ),
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub in ("approval", "approval_gate"):
        return _human_gate_action(
            gate_id="gate_1_1_spec_draft",
            message=(
                "The stakeholder specification draft is ready for your review. "
                "Please read the document and choose: APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=post_fn("spec_approval") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("review", "review_request", "fresh_review"):
        return _invoke_agent_action(
            agent="stakeholder_reviewer",
            message=(
                "A fresh stakeholder spec reviewer agent is reading the document cold "
                "and producing a structured critique."
            ),
            post=post_fn("spec_review") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub in ("post_review", "post_review_gate"):
        return _human_gate_action(
            gate_id="gate_1_2_spec_post_review",
            message=(
                "The reviewer has produced a critique. Please review and choose: "
                "APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=post_fn("spec_post_review") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("revision", "spec_revision"):
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message=(
                "The stakeholder dialog agent will conduct a focused revision of the "
                "specification to address the identified issue."
            ),
            post=post_fn("spec_revision") if post_fn else None,
            prepare=lambda: (
                prep_fn("stakeholder_dialog", extra="--revision-mode")
                if prep_fn
                else None
            ),
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    return _invoke_agent_action(
        agent="stakeholder_dialog",
        message="Continuing stakeholder spec authoring.",
        post=post_fn("stakeholder_dialog") if post_fn else None,
        prepare_cmd_builder=prep_fn,
        post_cmd_builder=post_fn,
    )


def _route_stage_2(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route Stage 2: Blueprint Authoring."""
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None
    prep_fn = cmd_builders.prepare_cmd if cmd_builders else None

    if sub in ("dialog", "blueprint_dialog", None):
        return _invoke_agent_action(
            agent="blueprint_author",
            message="Continuing blueprint generation.",
            post=post_fn("blueprint_dialog") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "alignment_check":
        return _invoke_agent_action(
            agent="blueprint_checker",
            message="Running alignment check on the blueprint.",
            post=post_fn("alignment_check") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub in ("approval", "approval_gate"):
        return _human_gate_action(
            gate_id="gate_2_1_blueprint_approval",
            message=(
                "The blueprint is ready for your review. "
                "Please read the document and choose: APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=post_fn("blueprint_approval") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "review":
        return _invoke_agent_action(
            agent="blueprint_reviewer",
            message="Running blueprint review.",
            post=post_fn("blueprint_review") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "post_review":
        return _human_gate_action(
            gate_id="gate_2_2_blueprint_post_review",
            message=(
                "The blueprint reviewer has produced a critique. "
                "Please choose: APPROVE, REVISE, or FRESH REVIEW."
            ),
            post=post_fn("blueprint_post_review") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("revision", "blueprint_revision"):
        return _invoke_agent_action(
            agent="blueprint_author",
            message="Continuing blueprint revision.",
            post=post_fn("blueprint_revision") if post_fn else None,
            prepare=lambda: (
                prep_fn("blueprint_author", extra="--revision-mode")
                if prep_fn
                else None
            ),
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "iteration_limit":
        return _human_gate_action(
            gate_id="gate_2_3_alignment_exhausted",
            message=(
                "Alignment check has reached the iteration limit. "
                "Please choose: REVISE SPEC, RESTART SPEC, or RETRY BLUEPRINT."
            ),
            post=post_fn("alignment_exhausted") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "spec_revision_stage2":
        return _invoke_agent_action(
            agent="stakeholder_dialog",
            message="Spec revision from alignment failure.",
            post=post_fn("spec_revision_stage2") if post_fn else None,
            prepare=lambda: (
                prep_fn("stakeholder_dialog", extra="--revision-mode")
                if prep_fn
                else None
            ),
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    return _invoke_agent_action(
        agent="blueprint_author",
        message="Continuing blueprint generation.",
        post=post_fn("blueprint_dialog") if post_fn else None,
        prepare_cmd_builder=prep_fn,
        post_cmd_builder=post_fn,
    )


def _route_pre_stage_3(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route pre-Stage 3: Infrastructure setup."""
    post_fn = cmd_builders.post_cmd if cmd_builders else None

    env_name = derive_env_name_from_state(state)
    command = f"conda run -n {env_name} python scripts/setup_infrastructure.py"

    return _run_command_action(
        command=command,
        message="Setting up project infrastructure (environment, directories).",
        post=post_fn("infrastructure_setup") if post_fn else None,
        post_cmd_builder=post_fn,
    )


def _route_stage_3(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route Stage 3: Unit Implementation and Test."""
    sub = state.sub_stage
    unit = state.current_unit
    post_fn = cmd_builders.post_cmd if cmd_builders else None
    prep_fn = cmd_builders.prepare_cmd if cmd_builders else None

    if state.fix_ladder_position is not None:
        return _route_fix_ladder(state, project_root, cmd_builders)

    if sub in ("dialog", "test_generation", None):
        return _invoke_agent_action(
            agent="test_agent",
            message=f"Generating tests for Unit {unit}.",
            unit=unit,
            post=post_fn("test_generation", unit=unit) if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "stub_generation":
        return _invoke_agent_action(
            agent="implementation_agent",
            message=f"Generating stubs for Unit {unit}.",
            unit=unit,
            post=post_fn("stub_generation", unit=unit) if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "red_run":
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=f"conda run -n {env_name} pytest --collect-only -q",
            message=f"Running red validation for Unit {unit}.",
            unit=unit,
            post=post_fn("red_run", unit=unit) if post_fn else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "implementation":
        return _invoke_agent_action(
            agent="implementation_agent",
            message=f"Generating implementation for Unit {unit}.",
            unit=unit,
            post=post_fn("implementation", unit=unit) if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "green_run":
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=f"conda run -n {env_name} pytest -v",
            message=f"Running green validation for Unit {unit}.",
            unit=unit,
            post=post_fn("green_run", unit=unit) if post_fn else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "coverage_review":
        return _invoke_agent_action(
            agent="coverage_review",
            message=f"Running coverage review for Unit {unit}.",
            unit=unit,
            post=post_fn("coverage_review", unit=unit) if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub in ("test_validation", "test_validation_gate"):
        return _human_gate_action(
            gate_id="gate_3_1_test_validation",
            message=(
                f"Tests for Unit {unit} are complete. "
                "Please choose: TEST CORRECT or TEST WRONG."
            ),
            unit=unit,
            post=post_fn("test_validation", unit=unit) if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("diagnostic", "diagnostic_gate"):
        return _invoke_agent_action(
            agent="diagnostic_agent",
            message=f"Running diagnostic for Unit {unit}.",
            unit=unit,
            post=post_fn("diagnostic", unit=unit) if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "diagnostic_decision":
        return _human_gate_action(
            gate_id="gate_3_2_diagnostic_decision",
            message=(
                f"Diagnostic for Unit {unit} is complete. "
                "Please choose: FIX IMPLEMENTATION, FIX BLUEPRINT, or FIX SPEC."
            ),
            unit=unit,
            post=post_fn("diagnostic_decision", unit=unit) if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "unit_completion":
        return _run_command_action(
            command=(
                "echo COMMAND_SUCCEEDED > .svp/last_status.txt &&"
                " PYTHONPATH=scripts python scripts/update_state.py"
                f" --unit {unit} --phase unit_completion"
                " --status-file .svp/last_status.txt --project-root ."
            ),
            message=f"Unit {unit} verified. Advancing pipeline.",
            post=None,
            unit=unit,
        )

    elif sub == "unit_verified":
        return _session_boundary_action(
            message=f"Unit {unit} verified. Preparing for the next unit."
        )

    elif sub in ("doc_revision", "restart_stage2"):
        return _session_boundary_action(
            message="Document revision complete. Restarting from Stage 2."
        )

    return _invoke_agent_action(
        agent="test_agent",
        message=f"Continuing Stage 3 for Unit {unit}.",
        unit=unit,
        post=post_fn("test_generation", unit=unit) if post_fn else None,
        prepare_cmd_builder=prep_fn,
        post_cmd_builder=post_fn,
    )


def _route_fix_ladder(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route fix ladder positions within Stage 3."""
    fix = state.fix_ladder_position
    unit = state.current_unit
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None
    prep_fn = cmd_builders.prepare_cmd if cmd_builders else None

    if fix == "fresh_test":
        return _invoke_agent_action(
            agent="test_agent",
            unit=unit,
            message=(
                f"Test fix ladder for Unit {unit}: fresh test agent generating "
                f"replacement tests with rejection context."
            ),
            post=post_fn("fresh_test", unit=unit) if post_fn else None,
            prepare=prep_fn(
                "test_agent", unit=unit, extra="--ladder-position fresh_test"
            )
            if prep_fn
            else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif fix == "hint_test":
        return _invoke_agent_action(
            agent="test_agent",
            unit=unit,
            message=(
                f"Test fix ladder for Unit {unit}: hint-assisted test agent generating "
                f"replacement tests with accumulated context and human hint."
            ),
            post=post_fn("hint_test", unit=unit) if post_fn else None,
            prepare=prep_fn(
                "test_agent", unit=unit, extra="--ladder-position hint_test"
            )
            if prep_fn
            else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif fix == "fresh_impl":
        return _invoke_agent_action(
            agent="implementation_agent",
            unit=unit,
            message=(
                f"Implementation fix ladder for Unit {unit}: fresh agent with "
                f"rejection context from test failure."
            ),
            post=post_fn("fresh_impl", unit=unit) if post_fn else None,
            prepare=prep_fn(
                "implementation_agent", unit=unit, extra="--ladder-position fresh_impl"
            )
            if prep_fn
            else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif fix == "diagnostic":
        return _invoke_agent_action(
            agent="diagnostic_agent",
            unit=unit,
            message=(
                f"Diagnostic escalation for Unit {unit}: three-hypothesis analysis "
                f"of accumulated failures."
            ),
            post=post_fn("diagnostic_escalation", unit=unit) if post_fn else None,
            prepare=prep_fn(
                "diagnostic_agent", unit=unit, extra="--ladder-position diagnostic"
            )
            if prep_fn
            else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif fix == "diagnostic_impl":
        return _invoke_agent_action(
            agent="implementation_agent",
            unit=unit,
            message=(
                f"Diagnostic-guided implementation for Unit {unit}: fresh agent with "
                f"diagnostic guidance and optional human hint."
            ),
            post=post_fn("diagnostic_impl", unit=unit) if post_fn else None,
            prepare=prep_fn(
                "implementation_agent",
                unit=unit,
                extra="--ladder-position diagnostic_impl",
            )
            if prep_fn
            else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    raise ValueError(f"Unrecognized fix_ladder_position: {fix}")


def _route_stage_4(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route Stage 4: Integration Testing."""
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None
    prep_fn = cmd_builders.prepare_cmd if cmd_builders else None

    if sub in ("dialog", "integration_test_generation", None):
        return _invoke_agent_action(
            agent="integration_test_author",
            message="Generating integration tests.",
            post=post_fn("integration_test_generation") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub in ("run", "integration_run"):
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=f"conda run -n {env_name} pytest -v",
            message="Running integration tests.",
            post=post_fn("integration_run") if post_fn else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("failure_gate", "failure"):
        return _human_gate_action(
            gate_id="gate_4_1_integration_failure",
            message=(
                "Integration tests failed. "
                "Please choose: ASSEMBLY FIX, FIX BLUEPRINT, or FIX SPEC."
            ),
            post=post_fn("integration_failure") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "assembly_fix":
        return _invoke_agent_action(
            agent="implementation_agent",
            message="Implementing assembly fix.",
            post=post_fn("assembly_fix") if post_fn else None,
            prepare=lambda: (
                prep_fn("implementation_agent", extra="--assembly-fix")
                if prep_fn
                else None
            ),
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "fix_cycle":
        return _invoke_agent_action(
            agent="implementation_agent",
            message="Continuing integration fix cycle.",
            post=post_fn("integration_test_generation") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif sub == "iteration_limit":
        return _human_gate_action(
            gate_id="gate_4_2_assembly_exhausted",
            message=(
                "Integration assembly has reached the iteration limit. "
                "Please choose: FIX BLUEPRINT or FIX SPEC."
            ),
            post=post_fn("assembly_exhausted") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    return _invoke_agent_action(
        agent="integration_test_author",
        message="Continuing integration testing.",
        post=post_fn("integration_test_generation") if post_fn else None,
        prepare_cmd_builder=prep_fn,
        post_cmd_builder=post_fn,
    )


def _route_stage_5(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route Stage 5: Repository Assembly and Delivery."""
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None

    if sub == "repo_assembly":
        return _invoke_agent_action(
            agent="git_repo_agent",
            message="Assembling repository.",
            post=post_fn("repo_assembly") if post_fn else None,
            prepare_cmd_builder=cmd_builders.prepare_cmd if cmd_builders else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("test_gate", "repo_test"):
        env_name = derive_env_name_from_state(state)
        return _run_command_action(
            command=f"conda run -n {env_name} pytest -v",
            message="Running final repository tests.",
            post=post_fn("repo_test") if post_fn else None,
            post_cmd_builder=post_fn,
        )

    elif sub in ("repo_fix",):
        return _invoke_agent_action(
            agent="implementation_agent",
            message="Fixing repository issues.",
            post=post_fn("repo_fix") if post_fn else None,
            prepare_cmd_builder=cmd_builders.prepare_cmd if cmd_builders else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "fix_cycle":
        return _invoke_agent_action(
            agent="git_repo_agent",
            message="Continuing repository fix cycle.",
            post=post_fn("repo_assembly") if post_fn else None,
            prepare_cmd_builder=cmd_builders.prepare_cmd if cmd_builders else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "iteration_limit":
        return _human_gate_action(
            gate_id="gate_5_2_assembly_exhausted",
            message=(
                "Repository assembly has reached the iteration limit. "
                "Please choose: RETRY ASSEMBLY, FIX BLUEPRINT, or FIX SPEC."
            ),
            post=post_fn("assembly_exhausted") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    elif sub == "complete":
        return _pipeline_complete_action(
            message="Pipeline complete -- offer workspace cleanup."
        )

    return _invoke_agent_action(
        agent="git_repo_agent",
        message="Continuing repository assembly.",
        post=post_fn("repo_assembly") if post_fn else None,
        prepare_cmd_builder=cmd_builders.prepare_cmd if cmd_builders else None,
        post_cmd_builder=post_fn,
    )


def _route_debug(
    state: PipelineState,
    project_root: Path,
    cmd_builders: Optional[RouterCommandBuilders] = None,
) -> Dict[str, Any]:
    """Route debug session within Stage 5."""
    debug = state.debug_session
    if debug is None:
        return _route_stage(state, project_root, cmd_builders)

    phase = debug.phase
    sub = state.sub_stage
    post_fn = cmd_builders.post_cmd if cmd_builders else None
    prep_fn = cmd_builders.prepare_cmd if cmd_builders else None

    if phase == "triage_readonly":
        if not debug.authorized:
            return _human_gate_action(
                gate_id="gate_6_0_debug_permission",
                message=(
                    "A bug has been reported. The triage agent has gathered initial "
                    "information. Do you want to authorize debug write permissions?"
                ),
                post=post_fn("debug_permission") if post_fn else None,
                gate_vocabulary=GATE_VOCABULARY,
                gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
                if cmd_builders
                else None,
                post_cmd_builder=post_fn,
            )
        return _invoke_agent_action(
            agent="bug_triage",
            message="Starting bug triage with the triage agent.",
            post=post_fn("bug_triage") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif phase == "triage":
        return _invoke_agent_action(
            agent="bug_triage",
            message="Continuing bug triage dialog.",
            post=post_fn("bug_triage") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif phase == "regression_test":
        if sub == "regression_test_validation":
            return _human_gate_action(
                gate_id="gate_6_1_regression_test",
                message=(
                    "A regression test has been written and confirmed to fail. "
                    "Please review the test assertion."
                ),
                post=post_fn("regression_test_validation") if post_fn else None,
                gate_vocabulary=GATE_VOCABULARY,
                gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
                if cmd_builders
                else None,
                post_cmd_builder=post_fn,
            )
        elif sub == "debug_classification":
            return _human_gate_action(
                gate_id="gate_6_2_debug_classification",
                message=(
                    "The regression test is confirmed. Please classify the fix type."
                ),
                post=post_fn("debug_classification") if post_fn else None,
                gate_vocabulary=GATE_VOCABULARY,
                gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
                if cmd_builders
                else None,
                post_cmd_builder=post_fn,
            )
        return _invoke_agent_action(
            agent="test_agent",
            message="Generating regression test for the reported bug.",
            post=post_fn("regression_test_generation") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif phase == "stage3_reentry":
        return _route_stage_3(state, project_root, cmd_builders)

    elif phase == "repair":
        if sub == "repair_exhausted":
            return _human_gate_action(
                gate_id="gate_6_3_repair_exhausted",
                message=(
                    "The repair agent has exhausted its fix cycle. "
                    "Please decide how to proceed."
                ),
                post=post_fn("repair_exhausted") if post_fn else None,
                gate_vocabulary=GATE_VOCABULARY,
                gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
                if cmd_builders
                else None,
                post_cmd_builder=post_fn,
            )
        return _invoke_agent_action(
            agent="repair_agent",
            message="Repair agent is applying the fix.",
            post=post_fn("repair") if post_fn else None,
            prepare_cmd_builder=prep_fn,
            post_cmd_builder=post_fn,
        )

    elif phase == "complete":
        return _pipeline_complete_action(
            message="Debug session complete. The fix has been applied and verified."
        )

    if sub == "non_reproducible":
        return _human_gate_action(
            gate_id="gate_6_4_non_reproducible",
            message="The bug could not be reproduced. Please decide how to proceed.",
            post=post_fn("non_reproducible") if post_fn else None,
            gate_vocabulary=GATE_VOCABULARY,
            gate_prepare_cmd_builder=cmd_builders.gate_prepare_cmd
            if cmd_builders
            else None,
            post_cmd_builder=post_fn,
        )

    return _invoke_agent_action(
        agent="bug_triage",
        message="Continuing bug triage.",
        post=post_fn("bug_triage") if post_fn else None,
        prepare_cmd_builder=prep_fn,
        post_cmd_builder=post_fn,
    )
