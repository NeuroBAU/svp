"""Unit 10: Routing Script and Update State.

Implements routing, dispatch, gate vocabulary, agent status lines,
test execution wrappers, and quality gate execution for the SVP pipeline.

SVP 2.1: Includes Bug 1 fix (gate vocabulary), Bug 21 fix (two-branch routing),
Bug 23 fix (alignment check routing), Bug 25 fix (all Stage 3 sub-stages),
Bug 41 fix (Stage 1 two-branch routing and gate registration),
Bug 42 fix (pre-stage-3 state persistence and reference indexing advancement),
Bug 43 fix (two-branch routing invariant for Stage 4, Stage 5, redo profile, debug loop),
Gate 6.5 (debug commit), quality gate execution,
Bug 55 fix (Gate 6.2 FIX UNIT wired to rollback_to_unit, set_debug_classification
wired into bug_triage dispatch, build_env fast path, phase-based debug routing),
Bug 58 fix (Gate 5.3 unused_functions added to GATE_VOCABULARY and dispatch),
Bug 67 fix (gate_5_3 routing path in route() and dispatch_command_status),
Bug 65 fix (Stage 3 error handling: stub_generation routing, fix ladder engagement,
diagnostic escalation, Gate 3.1/3.2 dispatch, coverage two-branch, red_run retries),
Bug 69 fix (debug loop gates: gate_6_0 triage_readonly/triage separation, gate_6_1
regression_test phase routing, gate_6_3 RECLASSIFY BUG reset, gate_6_5 debug commit),
Bug 70 fix (fix ladder routing at sub_stage=None, TESTS_ERROR infinite loop, dead phases),
Bug 73 fix (Stage 0 PROFILE_COMPLETE routing loop, Gate 5.3 OVERRIDE CONTINUE loop,
Gate 4.1 ASSEMBLY FIX loop — dispatch handlers returning unchanged state).
"""

import json
import subprocess
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from pipeline_state import PipelineState
from state_transitions import (
    TransitionError,
    advance_stage,
    advance_sub_stage,
    complete_unit,
    advance_fix_ladder,
    increment_red_run_retries,
    reset_red_run_retries,
    increment_alignment_iteration,
    rollback_to_unit,
    restart_from_stage,
    enter_debug_session,
    authorize_debug_session,
    complete_debug_session,
    abandon_debug_session,
    update_debug_phase,
    set_debug_classification,
    enter_redo_profile_revision,
    complete_redo_profile_revision,
    enter_alignment_check,
    complete_alignment_check,
    enter_quality_gate,
    advance_quality_gate_to_retry,
    quality_gate_pass,
    quality_gate_fail_to_ladder,
    set_delivered_repo_path,
    version_document,
)

# --- Data contract: gate status string vocabulary (Bug 1 fix) ---

GATE_VOCABULARY: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": [
        "CONTEXT APPROVED",
        "CONTEXT REJECTED",
        "CONTEXT NOT READY",
    ],
    "gate_0_3_profile_approval": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_0_3r_profile_revision": ["PROFILE APPROVED", "PROFILE REJECTED"],
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
    "gate_5_3_unused_functions": ["FIX SPEC", "OVERRIDE CONTINUE"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_2_debug_classification": ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_3_repair_exhausted": ["RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
    "gate_6_5_debug_commit": ["COMMIT APPROVED", "COMMIT REJECTED"],
    "gate_hint_conflict": ["BLUEPRINT CORRECT", "HINT CORRECT"],
}

# Backward compatibility alias (stub name)
GATE_RESPONSES = GATE_VOCABULARY

# --- Data contract: terminal status line vocabulary ---

AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": [
        "PROJECT_CONTEXT_COMPLETE",
        "PROJECT_CONTEXT_REJECTED",
        "PROFILE_COMPLETE",
    ],
    "stakeholder_dialog": ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"],
    "stakeholder_reviewer": ["REVIEW_COMPLETE"],
    "blueprint_author": ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"],
    "blueprint_checker": [
        "ALIGNMENT_CONFIRMED",
        "ALIGNMENT_FAILED: spec",
        "ALIGNMENT_FAILED: blueprint",
    ],
    "blueprint_reviewer": ["REVIEW_COMPLETE"],
    "test_agent": ["TEST_GENERATION_COMPLETE", "REGRESSION_TEST_COMPLETE"],
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
        "REDO_CLASSIFIED: profile_delivery",
        "REDO_CLASSIFIED: profile_blueprint",
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

# Cross-agent status (any agent receiving a hint)
CROSS_AGENT_STATUS: str = "HINT_BLUEPRINT_CONFLICT"

# Stub compatibility
CROSS_AGENT_STATUS_LINES: Dict[str, str] = {
    "HINT_BLUEPRINT_CONFLICT": "gate_hint_conflict",
}

# Command result status line patterns
COMMAND_STATUS_PATTERNS: List[str] = [
    "TESTS_PASSED",  # "TESTS_PASSED: N passed"
    "TESTS_FAILED",  # "TESTS_FAILED: N passed, M failed"
    "TESTS_ERROR",  # "TESTS_ERROR: [error summary]"
    "COMMAND_SUCCEEDED",
    "COMMAND_FAILED",  # "COMMAND_FAILED: [exit code]"
    "UNUSED_FUNCTIONS_DETECTED",  # Bug 67: unused exported functions found
]

# Known phases for dispatch
_KNOWN_PHASES = {
    "setup",
    "spec_draft",
    "spec_revision",
    "spec_review",
    "blueprint_draft",
    "blueprint_revision",
    "blueprint_review",
    "alignment_check",
    "test_generation",
    "test_execution",
    "implementation",
    "coverage_review",
    "diagnostic",
    "integration_test",
    "repo_assembly",
    "compliance_scan",
    "gate",
    "redo",
    "debug",
    "help",
    "hint",
    "reference_indexing",
    "bug_triage",
    "repair",
    "regression_test",
    "stub_generation",
    "unit_completion",
    "quality_gate",  # NEW IN 2.1
    "structural_check",  # NEW IN 2.1 (Bug 72)
}


def _try_transition(fn, fallback_state):
    """Try a state transition, returning fallback_state if TransitionError is raised."""
    try:
        return fn()
    except TransitionError:
        return fallback_state




def _version_spec(project_root: Path, trigger_context: str) -> None:
    """Version the stakeholder spec before revision."""
    spec_path = project_root / "specs" / "stakeholder_spec.md"
    history_dir = project_root / "docs" / "history"
    if spec_path.exists():
        version_document(spec_path, history_dir, "Revision triggered", trigger_context)


def _version_blueprint(project_root: Path, trigger_context: str) -> None:
    """Version blueprint prose and contracts as an atomic pair before revision."""
    history_dir = project_root / "blueprint" / "history"
    prose_path = project_root / "blueprint" / "blueprint_prose.md"
    contracts_path = project_root / "blueprint" / "blueprint_contracts.md"
    for bp_path in [prose_path, contracts_path]:
        if bp_path.exists():
            version_document(bp_path, history_dir, "Revision triggered", trigger_context)


# --- Helper: read last_status.txt ---


def _read_last_status(project_root: Path) -> Optional[str]:
    """Read .svp/last_status.txt if it exists, return stripped content or None."""
    status_file = project_root / ".svp" / "last_status.txt"
    if status_file.exists():
        content = status_file.read_text(encoding="utf-8").strip()
        if content:
            return content
    return None



# Public alias (stub name)
read_last_status = _read_last_status


def _read_triage_affected_units(project_root: Path) -> List[int]:
    """Read affected_units from .svp/triage_result.json if it exists.

    Bug 55: The triage agent writes this file during triage to communicate
    which units are affected. The routing dispatch reads it when processing
    the triage agent's terminal status line.
    """
    result_file = project_root / ".svp" / "triage_result.json"
    if result_file.exists():
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            units = data.get("affected_units", [])
            return [int(u) for u in units]
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
    return []


# --- Command generation helpers ---


def _prepare_cmd(agent_type: str, unit: Optional[int] = None) -> str:
    """Generate the PREPARE command string for invoking an agent via prepare_task.py."""
    cmd = f"python scripts/prepare_task.py --agent {agent_type} --project-root . --output .svp/task_prompt.md"
    if unit is not None:
        cmd += f" --unit {unit}"
    return cmd


def _gate_prepare_cmd(gate_id: str, unit: Optional[int] = None) -> str:
    """Generate the PREPARE command for a gate prompt via prepare_task.py."""
    cmd = f"python scripts/prepare_task.py --gate {gate_id} --project-root . --output .svp/gate_prompt.md"
    if unit is not None:
        cmd += f" --unit {unit}"
    return cmd


def _post_cmd(
    phase: str,
    unit: Optional[int] = None,
    gate_id: Optional[str] = None,
) -> str:
    """Generate the POST command string for updating state via update_state.py."""
    cmd = f"python scripts/update_state.py --project-root . --phase {phase}"
    if unit is not None:
        cmd += f" --unit {unit}"
    if gate_id is not None:
        cmd += f" --gate-id {gate_id}"
    return cmd


# --- Routing functions ---


def route(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    """Read pipeline state and determine the next action."""
    assert project_root.is_dir(), "Project root must exist"

    stage = state.stage
    sub_stage = state.sub_stage

    # Handle redo profile revision sub-stages (can appear in any stage)
    # Bug 43: two-branch routing for redo profile sub-stages
    if sub_stage == "redo_profile_delivery":
        last_status = _read_last_status(project_root)
        if last_status == "PROFILE_COMPLETE":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_0_3r_profile_revision",
                "OPTIONS": GATE_VOCABULARY["gate_0_3r_profile_revision"],
                "PREPARE": _gate_prepare_cmd("gate_0_3r_profile_revision"),
                "POST": _post_cmd("gate", gate_id="gate_0_3r_profile_revision"),
            }
        else:
            return {
                "ACTION": "invoke_agent",
                "AGENT": "setup_agent",
                "CONTEXT": "targeted_profile_revision",
                "CLASSIFICATION": "profile_delivery",
                "REVISION_MODE": True,
                "PREPARE": _prepare_cmd("setup_agent"),
                "POST": _post_cmd("setup"),
            }
    if sub_stage == "redo_profile_blueprint":
        last_status = _read_last_status(project_root)
        if last_status == "PROFILE_COMPLETE":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_0_3r_profile_revision",
                "OPTIONS": GATE_VOCABULARY["gate_0_3r_profile_revision"],
                "PREPARE": _gate_prepare_cmd("gate_0_3r_profile_revision"),
                "POST": _post_cmd("gate", gate_id="gate_0_3r_profile_revision"),
            }
        else:
            return {
                "ACTION": "invoke_agent",
                "AGENT": "setup_agent",
                "CONTEXT": "targeted_profile_revision",
                "CLASSIFICATION": "profile_blueprint",
                "REVISION_MODE": True,
                "PREPARE": _prepare_cmd("setup_agent"),
                "POST": _post_cmd("setup"),
            }

    # Stage 0
    if stage == "0":
        if sub_stage == "hook_activation":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_0_1_hook_activation",
                "OPTIONS": GATE_VOCABULARY["gate_0_1_hook_activation"],
                "PREPARE": _gate_prepare_cmd("gate_0_1_hook_activation"),
                "POST": _post_cmd("gate", gate_id="gate_0_1_hook_activation"),
            }
        elif sub_stage == "project_context":
            # Bug 21: two-branch routing
            # Bug 73: also match PROFILE_COMPLETE (agent completed both artifacts)
            last_status = _read_last_status(project_root)
            if last_status in ("PROJECT_CONTEXT_COMPLETE", "PROFILE_COMPLETE"):
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_0_2_context_approval",
                    "OPTIONS": GATE_VOCABULARY["gate_0_2_context_approval"],
                    "PREPARE": _gate_prepare_cmd("gate_0_2_context_approval"),
                    "POST": _post_cmd("gate", gate_id="gate_0_2_context_approval"),
                }
            else:
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "setup_agent",
                    "CONTEXT": "project_context",
                    "PREPARE": _prepare_cmd("setup_agent"),
                    "POST": _post_cmd("setup"),
                }
        elif sub_stage == "project_profile":
            # Bug 21: two-branch routing
            # Bug 73: also check artifact existence (profile may have been created
            # during the context phase, with last_status overwritten by Gate 0.2)
            last_status = _read_last_status(project_root)
            profile_exists = (project_root / "project_profile.json").exists()
            if last_status == "PROFILE_COMPLETE" or (
                profile_exists
                and last_status not in ("PROFILE REJECTED", None)
            ):
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_0_3_profile_approval",
                    "OPTIONS": GATE_VOCABULARY["gate_0_3_profile_approval"],
                    "PREPARE": _gate_prepare_cmd("gate_0_3_profile_approval"),
                    "POST": _post_cmd("gate", gate_id="gate_0_3_profile_approval"),
                }
            else:
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "setup_agent",
                    "CONTEXT": "project_profile",
                    "PREPARE": _prepare_cmd("setup_agent"),
                    "POST": _post_cmd("setup"),
                }

    # Stage 1 (Bug 41: two-branch routing for spec authoring)
    if stage == "1":
        last_status = _read_last_status(project_root)
        if last_status in ("SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"):
            # Agent completed: present gate_1_1_spec_draft
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_1_1_spec_draft",
                "OPTIONS": GATE_VOCABULARY["gate_1_1_spec_draft"],
                "PREPARE": _gate_prepare_cmd("gate_1_1_spec_draft"),
                "POST": _post_cmd("gate", gate_id="gate_1_1_spec_draft"),
            }
        elif last_status == "REVIEW_COMPLETE":
            # Stakeholder reviewer completed: present gate_1_2_spec_post_review
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_1_2_spec_post_review",
                "OPTIONS": GATE_VOCABULARY["gate_1_2_spec_post_review"],
                "PREPARE": _gate_prepare_cmd("gate_1_2_spec_post_review"),
                "POST": _post_cmd("gate", gate_id="gate_1_2_spec_post_review"),
            }
        elif last_status == "FRESH REVIEW":
            # Gate response was FRESH REVIEW: invoke stakeholder_reviewer
            return {
                "ACTION": "invoke_agent",
                "AGENT": "stakeholder_reviewer",
                "CONTEXT": "spec_review",
                "PREPARE": _prepare_cmd("stakeholder_reviewer"),
                "POST": _post_cmd("spec_review"),
            }
        else:
            # No status or agent not done: invoke stakeholder_dialog
            return {
                "ACTION": "invoke_agent",
                "AGENT": "stakeholder_dialog",
                "CONTEXT": "spec_draft",
                "PREPARE": _prepare_cmd("stakeholder_dialog"),
                "POST": _post_cmd("spec_draft"),
            }

    # Stage 2 (Bug 23: alignment check routing)
    if stage == "2":
        if sub_stage == "alignment_check":
            # Bug 23: two-branch pattern for alignment check
            last_status = _read_last_status(project_root)
            if last_status == "ALIGNMENT_CONFIRMED":
                # Call complete_alignment_check to advance to Pre-Stage-3
                new_state = complete_alignment_check(state, project_root)
                # Bug 42: persist pre_stage_3 state to disk before recursive routing
                # so that the POST command (update_state.py) reads the correct stage
                from pipeline_state import save_state

                save_state(new_state, project_root)
                # After completing alignment check, route the new state
                return route(new_state, project_root)
            elif last_status is not None and last_status.startswith("ALIGNMENT_FAILED"):
                # Present human gate for decision
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_2_3_alignment_exhausted",
                    "OPTIONS": GATE_VOCABULARY["gate_2_3_alignment_exhausted"],
                    "PREPARE": _gate_prepare_cmd("gate_2_3_alignment_exhausted"),
                    "POST": _post_cmd("gate", gate_id="gate_2_3_alignment_exhausted"),
                }
            else:
                # No status yet: invoke blueprint checker
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "blueprint_checker",
                    "CONTEXT": "alignment_check",
                    "PREPARE": _prepare_cmd("blueprint_checker"),
                    "POST": _post_cmd("alignment_check"),
                }
        else:
            # sub_stage is None or "blueprint_dialog": two-branch pattern (Bug 43)
            last_status = _read_last_status(project_root)
            if last_status in (
                "BLUEPRINT_DRAFT_COMPLETE",
                "BLUEPRINT_REVISION_COMPLETE",
            ):
                # Agent completed: present gate_2_1_blueprint_approval
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_2_1_blueprint_approval",
                    "OPTIONS": GATE_VOCABULARY["gate_2_1_blueprint_approval"],
                    "PREPARE": _gate_prepare_cmd("gate_2_1_blueprint_approval"),
                    "POST": _post_cmd("gate", gate_id="gate_2_1_blueprint_approval"),
                }
            elif last_status == "REVIEW_COMPLETE":
                # Blueprint reviewer completed: present gate_2_2_blueprint_post_review
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_2_2_blueprint_post_review",
                    "OPTIONS": GATE_VOCABULARY["gate_2_2_blueprint_post_review"],
                    "PREPARE": _gate_prepare_cmd("gate_2_2_blueprint_post_review"),
                    "POST": _post_cmd("gate", gate_id="gate_2_2_blueprint_post_review"),
                }
            elif last_status == "FRESH REVIEW":
                # Gate response was FRESH REVIEW: invoke blueprint_reviewer
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "blueprint_reviewer",
                    "CONTEXT": "blueprint_review",
                    "PREPARE": _prepare_cmd("blueprint_reviewer"),
                    "POST": _post_cmd("blueprint_review"),
                }
            else:
                # No status or agent not done: invoke blueprint_author
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "blueprint_author",
                    "CONTEXT": "blueprint_draft",
                    "PREPARE": _prepare_cmd("blueprint_author"),
                    "POST": _post_cmd("blueprint_draft"),
                }

    # Pre-Stage 3
    if stage == "pre_stage_3":
        return {
            "ACTION": "invoke_agent",
            "AGENT": "reference_indexing",
            "CONTEXT": "reference_indexing",
            "PREPARE": _prepare_cmd("reference_indexing"),
            "POST": _post_cmd("reference_indexing"),
        }

    # Stage 3 (Bug 25: explicit routing for ALL sub-stages)
    # Bug 65: stub_generation, fix ladder checks, coverage two-branch, diagnostic routing
    if stage == "3":
        unit = state.current_unit

        # F1: sub_stage None means stub_generation (not test_generation)
        # Bug 70 F1: Check fix_ladder_position before defaulting to stub_generation.
        # When quality_gate_fail_to_ladder sets sub_stage=None with a non-None
        # fix_ladder_position, route based on the ladder position instead.
        if sub_stage is None:
            ladder_pos = state.fix_ladder_position
            if ladder_pos in ("fresh_test", "hint_test"):
                # Test ladder: re-invoke test agent
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "test_agent",
                    "CONTEXT": "test_generation",
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("test_agent", unit=unit),
                    "POST": _post_cmd("test_generation", unit=unit),
                }
            elif ladder_pos in ("fresh_impl", "diagnostic_impl"):
                # Impl ladder: re-invoke implementation agent
                context = "implementation"
                if ladder_pos == "diagnostic_impl":
                    context = "diagnostic_impl"
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "implementation_agent",
                    "CONTEXT": context,
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("implementation_agent", unit=unit),
                    "POST": _post_cmd("implementation", unit=unit),
                }
            elif ladder_pos == "diagnostic":
                # Diagnostic ladder: invoke diagnostic agent
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "diagnostic_agent",
                    "CONTEXT": "diagnostic",
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("diagnostic_agent", unit=unit),
                    "POST": _post_cmd("diagnostic", unit=unit),
                }
            else:
                # No ladder position (fresh start): generate stubs
                return {
                    "ACTION": "run_command",
                    "COMMAND": f"python scripts/generate_stubs.py --unit {unit} --project-root .",
                    "POST": _post_cmd("stub_generation", unit=unit),
                }

        elif sub_stage == "test_generation":
            return {
                "ACTION": "invoke_agent",
                "AGENT": "test_agent",
                "CONTEXT": "test_generation",
                "UNIT": unit,
                "PREPARE": _prepare_cmd("test_agent", unit=unit),
                "POST": _post_cmd("test_generation", unit=unit),
            }

        elif sub_stage == "quality_gate_a":
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/run_quality_gate.py --gate gate_a --target tests/unit_{unit}/ --project-root .",
                "POST": _post_cmd("quality_gate", unit=unit),
            }

        elif sub_stage == "quality_gate_a_retry":
            # Two-phase: check if agent completed
            last_status = _read_last_status(project_root)
            if last_status == "TEST_GENERATION_COMPLETE":
                # Agent completed, re-run the gate
                return {
                    "ACTION": "run_command",
                    "COMMAND": f"python scripts/run_quality_gate.py --gate gate_a --target tests/unit_{unit}/ --project-root .",
                    "POST": _post_cmd("quality_gate", unit=unit),
                }
            else:
                # No agent status: invoke test agent to fix
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "test_agent",
                    "CONTEXT": "quality_gate_retry",
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("test_agent", unit=unit),
                    "POST": _post_cmd("test_generation", unit=unit),
                }

        elif sub_stage == "red_run":
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/run_tests.py --test-path tests/unit_{unit}/ --env-name {{env_name}} --project-root .",
                "POST": _post_cmd("test_execution", unit=unit),
            }

        elif sub_stage == "implementation":
            # F6: Check fix_ladder_position to determine agent
            ladder_pos = state.fix_ladder_position
            if ladder_pos == "diagnostic":
                # Invoke diagnostic agent instead of implementation agent
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "diagnostic_agent",
                    "CONTEXT": "diagnostic",
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("diagnostic_agent", unit=unit),
                    "POST": _post_cmd("diagnostic", unit=unit),
                }
            else:
                # Normal implementation or fresh_impl or diagnostic_impl
                context = "implementation"
                if ladder_pos == "diagnostic_impl":
                    context = "diagnostic_impl"
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "implementation_agent",
                    "CONTEXT": context,
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("implementation_agent", unit=unit),
                    "POST": _post_cmd("implementation", unit=unit),
                }

        elif sub_stage == "quality_gate_b":
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/run_quality_gate.py --gate gate_b --target src/unit_{unit}/ --project-root .",
                "POST": _post_cmd("quality_gate", unit=unit),
            }

        elif sub_stage == "quality_gate_b_retry":
            # Two-phase: check if agent completed
            last_status = _read_last_status(project_root)
            if last_status == "IMPLEMENTATION_COMPLETE":
                # Agent completed, re-run the gate
                return {
                    "ACTION": "run_command",
                    "COMMAND": f"python scripts/run_quality_gate.py --gate gate_b --target src/unit_{unit}/ --project-root .",
                    "POST": _post_cmd("quality_gate", unit=unit),
                }
            else:
                # No agent status: invoke implementation agent to fix
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "implementation_agent",
                    "CONTEXT": "quality_gate_retry",
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("implementation_agent", unit=unit),
                    "POST": _post_cmd("implementation", unit=unit),
                }

        elif sub_stage == "green_run":
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/run_tests.py --test-path tests/unit_{unit}/ --env-name {{env_name}} --project-root .",
                "POST": _post_cmd("test_execution", unit=unit),
            }

        elif sub_stage == "coverage_review":
            # F5: Two-branch check for coverage_review
            last_status = _read_last_status(project_root)
            if last_status == "COVERAGE_COMPLETE: tests added":
                # Auto-format before advancing to unit_completion
                return {
                    "ACTION": "run_command",
                    "COMMAND": f"python scripts/run_quality_gate.py --gate gate_b --target tests/unit_{unit}/ --project-root .",
                    "POST": _post_cmd("quality_gate", unit=unit),
                }
            elif last_status == "COVERAGE_COMPLETE: no gaps":
                # Advance directly to unit_completion
                return {
                    "ACTION": "run_command",
                    "COMMAND": "echo COMMAND_SUCCEEDED",
                    "POST": _post_cmd("unit_completion", unit=unit),
                }
            else:
                # No status yet: invoke coverage_review agent
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "coverage_review",
                    "CONTEXT": "coverage_review",
                    "UNIT": unit,
                    "PREPARE": _prepare_cmd("coverage_review", unit=unit),
                    "POST": _post_cmd("coverage_review", unit=unit),
                }

        elif sub_stage == "unit_completion":
            return {
                "ACTION": "run_command",
                "COMMAND": "echo COMMAND_SUCCEEDED",
                "POST": _post_cmd("unit_completion", unit=unit),
            }

        # Bug 65: Gate 3.1 (test validation after red_run retries exhausted)
        elif sub_stage == "gate_3_1":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_3_1_test_validation",
                "OPTIONS": GATE_VOCABULARY["gate_3_1_test_validation"],
                "PREPARE": _gate_prepare_cmd("gate_3_1_test_validation", unit=unit),
                "POST": _post_cmd("gate", unit=unit, gate_id="gate_3_1_test_validation"),
            }

        # Bug 65: Gate 3.2 (diagnostic decision after fix ladder exhaustion)
        elif sub_stage == "gate_3_2":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_3_2_diagnostic_decision",
                "OPTIONS": GATE_VOCABULARY["gate_3_2_diagnostic_decision"],
                "PREPARE": _gate_prepare_cmd("gate_3_2_diagnostic_decision", unit=unit),
                "POST": _post_cmd("gate", unit=unit, gate_id="gate_3_2_diagnostic_decision"),
            }

        # Fallback for Stage 3 with unrecognized sub_stage
        return {
            "ACTION": "invoke_agent",
            "AGENT": "implementation_agent",
            "CONTEXT": "implementation",
            "UNIT": unit,
            "PREPARE": _prepare_cmd("implementation_agent", unit=unit),
            "POST": _post_cmd("implementation", unit=unit),
        }

    # Stage 4 (Bug 43: two-branch routing)
    # Bug 71: Added sub_stage handling for gate_4_1, gate_4_2.
    if stage == "4":
        # Bug 68/71: Check gate sub-stages first
        if sub_stage == "gate_4_1":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_4_1_integration_failure",
                "OPTIONS": GATE_VOCABULARY["gate_4_1_integration_failure"],
                "PREPARE": _gate_prepare_cmd("gate_4_1_integration_failure"),
                "POST": _post_cmd("gate", gate_id="gate_4_1_integration_failure"),
            }
        elif sub_stage == "gate_4_2":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_4_2_assembly_exhausted",
                "OPTIONS": GATE_VOCABULARY["gate_4_2_assembly_exhausted"],
                "PREPARE": _gate_prepare_cmd("gate_4_2_assembly_exhausted"),
                "POST": _post_cmd("gate", gate_id="gate_4_2_assembly_exhausted"),
            }

        last_status = _read_last_status(project_root)
        if last_status == "INTEGRATION_TESTS_COMPLETE":
            return {
                "ACTION": "run_command",
                "COMMAND": "python scripts/run_tests.py --test-path tests/integration/ --env-name {env_name} --project-root .",
                "POST": _post_cmd("test_execution"),
            }
        else:
            return {
                "ACTION": "invoke_agent",
                "AGENT": "integration_test_author",
                "CONTEXT": "integration_test",
                "PREPARE": _prepare_cmd("integration_test_author"),
                "POST": _post_cmd("integration_test"),
            }

    # Stage 5
    if stage == "5":
        # Bug 43 + Bug 55: phase-based routing for debug loop
        if state.debug_session is not None:
            # Bug 55: access phase safely (DebugSession object or dict)
            ds = state.debug_session
            debug_phase = ds.phase if hasattr(ds, 'phase') else ds.get('phase', 'triage')

            # Bug 55: stage3_reentry phase -- returning from Stage 3 rebuild.
            # Fall through to normal Stage 5 routing (git_repo_agent reassembly).
            if debug_phase == "stage3_reentry":
                pass  # Fall through to normal Stage 5 routing below

            # Bug 69 E.1: triage_readonly -- read-only triage, then Gate 6.0
            elif debug_phase == "triage_readonly":
                last_status = _read_last_status(project_root)
                if last_status in (
                    "TRIAGE_COMPLETE: single_unit",
                    "TRIAGE_COMPLETE: cross_unit",
                    "TRIAGE_COMPLETE: build_env",
                    "TRIAGE_NON_REPRODUCIBLE",
                    "TRIAGE_NEEDS_REFINEMENT",
                ):
                    # Triage agent completed: present Gate 6.0 for authorization
                    return {
                        "ACTION": "human_gate",
                        "GATE_ID": "gate_6_0_debug_permission",
                        "OPTIONS": GATE_VOCABULARY["gate_6_0_debug_permission"],
                        "PREPARE": _gate_prepare_cmd("gate_6_0_debug_permission"),
                        "POST": _post_cmd("gate", gate_id="gate_6_0_debug_permission"),
                    }
                else:
                    # Triage agent not yet completed: invoke in read-only mode
                    return {
                        "ACTION": "invoke_agent",
                        "AGENT": "bug_triage",
                        "CONTEXT": "debug",
                        "PREPARE": _prepare_cmd("bug_triage"),
                        "POST": _post_cmd("debug"),
                    }

            # Bug 69 E.1: triage -- authorized triage with write access
            elif debug_phase == "triage":
                last_status = _read_last_status(project_root)
                # Bug 55: exact status matching for build_env fast path
                if last_status in ("TRIAGE_COMPLETE: single_unit", "TRIAGE_COMPLETE: cross_unit"):
                    return {
                        "ACTION": "human_gate",
                        "GATE_ID": "gate_6_2_debug_classification",
                        "OPTIONS": GATE_VOCABULARY["gate_6_2_debug_classification"],
                        "PREPARE": _gate_prepare_cmd("gate_6_2_debug_classification"),
                        "POST": _post_cmd("gate", gate_id="gate_6_2_debug_classification"),
                    }
                elif last_status == "TRIAGE_COMPLETE: build_env":
                    # Bug 55: build_env fast path -- route directly to repair agent
                    return {
                        "ACTION": "invoke_agent",
                        "AGENT": "repair_agent",
                        "CONTEXT": "repair",
                        "PREPARE": _prepare_cmd("repair_agent"),
                        "POST": _post_cmd("repair"),
                    }
                elif last_status == "TRIAGE_NON_REPRODUCIBLE":
                    return {
                        "ACTION": "human_gate",
                        "GATE_ID": "gate_6_4_non_reproducible",
                        "OPTIONS": GATE_VOCABULARY["gate_6_4_non_reproducible"],
                        "PREPARE": _gate_prepare_cmd("gate_6_4_non_reproducible"),
                        "POST": _post_cmd("gate", gate_id="gate_6_4_non_reproducible"),
                    }
                else:
                    return {
                        "ACTION": "invoke_agent",
                        "AGENT": "bug_triage",
                        "CONTEXT": "debug",
                        "PREPARE": _prepare_cmd("bug_triage"),
                        "POST": _post_cmd("debug"),
                    }

            # Repair phase or other active debug phases: invoke repair agent
            elif debug_phase == "repair":
                last_status = _read_last_status(project_root)
                if last_status == "REPAIR_COMPLETE":
                    pass  # Fall through to normal Stage 5 routing (reassembly)
                elif last_status in ("REPAIR_FAILED", "REPAIR_RECLASSIFY"):
                    return {
                        "ACTION": "human_gate",
                        "GATE_ID": "gate_6_3_repair_exhausted",
                        "OPTIONS": GATE_VOCABULARY["gate_6_3_repair_exhausted"],
                        "PREPARE": _gate_prepare_cmd("gate_6_3_repair_exhausted"),
                        "POST": _post_cmd("gate", gate_id="gate_6_3_repair_exhausted"),
                    }
                else:
                    return {
                        "ACTION": "invoke_agent",
                        "AGENT": "repair_agent",
                        "CONTEXT": "repair",
                        "PREPARE": _prepare_cmd("repair_agent"),
                        "POST": _post_cmd("repair"),
                    }

            # Bug 69 E.2: regression_test phase handler
            elif debug_phase == "regression_test":
                last_status = _read_last_status(project_root)
                if last_status == "REGRESSION_TEST_COMPLETE":
                    return {
                        "ACTION": "human_gate",
                        "GATE_ID": "gate_6_1_regression_test",
                        "OPTIONS": GATE_VOCABULARY["gate_6_1_regression_test"],
                        "PREPARE": _gate_prepare_cmd("gate_6_1_regression_test"),
                        "POST": _post_cmd("gate", gate_id="gate_6_1_regression_test"),
                    }
                else:
                    return {
                        "ACTION": "invoke_agent",
                        "AGENT": "test_agent",
                        "CONTEXT": "regression_test",
                        "PREPARE": _prepare_cmd("test_agent"),
                        "POST": _post_cmd("regression_test"),
                    }

            # Bug 69 E.4: complete phase handler
            elif debug_phase == "complete":
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_6_5_debug_commit",
                    "OPTIONS": GATE_VOCABULARY["gate_6_5_debug_commit"],
                    "PREPARE": _gate_prepare_cmd("gate_6_5_debug_commit"),
                    "POST": _post_cmd("gate", gate_id="gate_6_5_debug_commit"),
                }

        # Bug 43: two-branch routing for repo assembly
        if sub_stage is None:
            last_status = _read_last_status(project_root)
            if last_status == "REPO_ASSEMBLY_COMPLETE":
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_5_1_repo_test",
                    "OPTIONS": GATE_VOCABULARY["gate_5_1_repo_test"],
                    "PREPARE": _gate_prepare_cmd("gate_5_1_repo_test"),
                    "POST": _post_cmd("gate", gate_id="gate_5_1_repo_test"),
                }
            else:
                return {
                    "ACTION": "invoke_agent",
                    "AGENT": "git_repo_agent",
                    "CONTEXT": "repo_assembly",
                    "PREPARE": _prepare_cmd("git_repo_agent"),
                    "POST": _post_cmd("repo_assembly"),
                }

        if sub_stage == "repo_test":
            # Human runs tests in delivered repo
            if state.red_run_retries >= 3:
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_5_2_assembly_exhausted",
                    "PREPARE": _gate_prepare_cmd("gate_5_2_assembly_exhausted"),
                    "POST": _post_cmd("gate", gate_id="gate_5_2_assembly_exhausted"),
                }
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_5_1_repo_test",
                "PREPARE": _gate_prepare_cmd("gate_5_1_repo_test"),
                "POST": _post_cmd("gate", gate_id="gate_5_1_repo_test"),
            }

        # Bug 72: structural_check sub-stage (runs before compliance_scan)
        if sub_stage == "structural_check":
            delivered = getattr(state, "delivered_repo_path", None) or "."
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/structural_check.py --target {delivered} --format json --strict",
                "CONTEXT": "structural_check",
                "POST": _post_cmd("structural_check"),
            }

        if sub_stage == "compliance_scan":
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/compliance_scan.py --project-root .",
                "CONTEXT": "compliance_scan",
                "POST": _post_cmd("compliance_scan"),
            }

        # Bug 67: gate_5_3 routing path for unused function detection
        if sub_stage == "gate_5_3":
            return {
                "ACTION": "human_gate",
                "GATE_ID": "gate_5_3_unused_functions",
                "OPTIONS": GATE_VOCABULARY["gate_5_3_unused_functions"],
                "PREPARE": _gate_prepare_cmd("gate_5_3_unused_functions"),
                "POST": _post_cmd("gate", gate_id="gate_5_3_unused_functions"),
            }

        if sub_stage == "repo_complete":
            return {
                "ACTION": "pipeline_complete",
            }

    return {
        "ACTION": "session_boundary",
    }


def format_action_block(action: Dict[str, Any]) -> str:
    """Convert an action dict to the structured text format for Section 17."""
    lines = []

    # Render PREPARE first (before ACTION) if present
    if "PREPARE" in action:
        lines.append(f"PREPARE: {action['PREPARE']}")

    # Render all keys except PREPARE and POST in original order
    for key, value in action.items():
        if key in ("PREPARE", "POST"):
            continue
        if key == "OPTIONS" and isinstance(value, list):
            lines.append(f"{key}:")
            for opt in value:
                lines.append(f"  - {opt}")
        else:
            lines.append(f"{key}: {value}")

    # Render POST after action details if present
    if "POST" in action:
        lines.append(f"POST: {action['POST']}")

    action_type = action.get("ACTION", "")

    # Add REMINDER block for invoke_agent, run_command, and human_gate
    if action_type in ("invoke_agent", "run_command", "human_gate"):
        lines.append("")
        lines.append("REMINDER:")
        lines.append("  1. Execute the ACTION above exactly as specified.")
        lines.append("  2. Write the result to .svp/last_status.txt.")
        lines.append("  3. Run the POST command to update pipeline state.")
        lines.append("  4. Run the routing script again for the next action.")

    result = "\n".join(lines) + "\n"
    return result


# --- Quality gate execution (NEW IN 2.1) ---


def run_quality_gate(
    gate: str,
    target_path: Path,
    env_name: str,
    project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute quality tool commands for the specified gate on the target path.

    Returns a dict with:
        status: "clean" or "residuals"
        report: formatted quality report string
        details: list of per-tool result dicts
    """
    # Load toolchain if not provided
    if toolchain is None:
        try:
            from svp_config import load_toolchain

            toolchain = load_toolchain(project_root)
        except Exception:
            toolchain = {}

    # Get gate operations from toolchain
    try:
        from svp_config import get_quality_gate_operations

        operations = get_quality_gate_operations(toolchain, gate)
    except (ValueError, KeyError):
        operations = []

    details = []
    has_residuals = False
    report_lines = []

    for operation in operations:
        # Resolve the operation to a command template
        try:
            from svp_config import resolve_command

            cmd = resolve_command(
                toolchain,
                f"quality.{operation}",
                {"target": str(target_path), "env_name": env_name},
            )
        except Exception:
            # Fallback: try to use the operation string directly
            cmd = operation.replace("{target}", str(target_path))
            cmd = cmd.replace("{env_name}", env_name)

        # Execute the command
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=120,
            )

            tool_result = {
                "tool": operation,
                "command": cmd,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            details.append(tool_result)

            if result.returncode != 0:
                has_residuals = True
                report_lines.append(f"## {operation}")
                report_lines.append(f"Exit code: {result.returncode}")
                if result.stdout.strip():
                    report_lines.append(f"Output:\n{result.stdout.strip()}")
                if result.stderr.strip():
                    report_lines.append(f"Errors:\n{result.stderr.strip()}")
                report_lines.append("")

        except subprocess.TimeoutExpired:
            tool_result = {
                "tool": operation,
                "command": cmd,
                "exit_code": -1,
                "stdout": "",
                "stderr": "timeout",
            }
            details.append(tool_result)
            has_residuals = True
            report_lines.append(f"## {operation}")
            report_lines.append("Exit code: -1 (timeout)")
            report_lines.append("")

        except Exception as e:
            tool_result = {
                "tool": operation,
                "command": cmd,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
            details.append(tool_result)
            has_residuals = True
            report_lines.append(f"## {operation}")
            report_lines.append(f"Error: {str(e)}")
            report_lines.append("")

    status = "residuals" if has_residuals else "clean"
    report = "\n".join(report_lines) if report_lines else ""

    return {
        "status": status,
        "report": report,
        "details": details,
    }


# --- Update state functions ---


def dispatch_status(
    state: PipelineState,
    status_line: str,
    gate_id: Optional[str],
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Top-level dispatcher: determines whether status is a gate response,
    agent status, or command result, and delegates accordingly."""
    if gate_id is not None:
        return dispatch_gate_response(state, gate_id, status_line, project_root)

    # Check if it's a command status
    for pattern in COMMAND_STATUS_PATTERNS:
        if status_line.startswith(pattern):
            return dispatch_command_status(
                state, status_line, unit, phase, project_root
            )

    # Otherwise treat as agent status
    # Determine agent type from phase
    phase_to_agent = {
        "setup": "setup_agent",
        "spec_draft": "stakeholder_dialog",
        "spec_revision": "stakeholder_dialog",
        "spec_review": "stakeholder_reviewer",
        "blueprint_draft": "blueprint_author",
        "blueprint_revision": "blueprint_author",
        "blueprint_review": "blueprint_reviewer",
        "alignment_check": "blueprint_checker",
        "test_generation": "test_agent",
        "implementation": "implementation_agent",
        "coverage_review": "coverage_review",
        "diagnostic": "diagnostic_agent",
        "integration_test": "integration_test_author",
        "repo_assembly": "git_repo_agent",
        "help": "help_agent",
        "hint": "hint_agent",
        "redo": "redo_agent",
        "bug_triage": "bug_triage",
        "repair": "repair_agent",
        "reference_indexing": "reference_indexing",
        "regression_test": "test_agent",
        "debug": "bug_triage",
    }
    agent_type = phase_to_agent.get(phase, phase)
    return dispatch_agent_status(
        state, agent_type, status_line, unit, phase, project_root
    )


def dispatch_gate_response(
    state: PipelineState,
    gate_id: str,
    response: str,
    project_root: Path,
) -> PipelineState:
    """Validate the response against GATE_VOCABULARY and dispatch accordingly."""
    # Invariant: gate_id must be in vocabulary
    if gate_id not in GATE_VOCABULARY:
        raise ValueError(f"Unknown gate ID: {gate_id}")

    options = GATE_VOCABULARY[gate_id]

    # Bug 1 invariant: exact string matching
    if response not in options:
        raise ValueError(
            f"Invalid gate response '{response}' for gate {gate_id}. "
            f"Valid options: {options}"
        )

    # Handle specific gates
    if gate_id == "gate_0_1_hook_activation":
        if response == "HOOKS ACTIVATED":
            return advance_sub_stage(state, "project_context", project_root)
        else:  # HOOKS FAILED
            return state

    elif gate_id == "gate_0_2_context_approval":
        if response == "CONTEXT APPROVED":
            return advance_sub_stage(state, "project_profile", project_root)
        elif response == "CONTEXT REJECTED":
            return state
        else:  # CONTEXT NOT READY
            return state

    elif gate_id == "gate_0_3_profile_approval":
        if response == "PROFILE APPROVED":
            try:
                return advance_stage(state, project_root)
            except TransitionError:
                # Advance manually if preconditions (e.g. file existence) not met
                import copy as _copy

                new_state = PipelineState.from_dict(_copy.deepcopy(state.to_dict()))
                new_state.stage = "1"
                new_state.sub_stage = None
                new_state.last_action = "Advanced from stage 0 to 1 (profile approved)"
                return new_state
        else:  # PROFILE REJECTED
            # Keep sub-stage at project_profile for revision
            return advance_sub_stage(state, "project_profile", project_root)

    elif gate_id == "gate_0_3r_profile_revision":
        if response == "PROFILE APPROVED":
            return complete_redo_profile_revision(state)
        else:  # PROFILE REJECTED
            # Keep sub-stage at the redo revision sub-stage
            return state

    elif gate_id == "gate_1_1_spec_draft":
        if response == "APPROVE":
            return _try_transition(lambda: advance_stage(state, project_root), state)
        elif response == "REVISE":
            _version_spec(project_root, "Gate 1.1 REVISE")
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_1_2_spec_post_review":
        if response == "APPROVE":
            return _try_transition(lambda: advance_stage(state, project_root), state)
        elif response == "REVISE":
            _version_spec(project_root, "Gate 1.2 REVISE")
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_2_1_blueprint_approval":
        # Bug 23: APPROVE calls enter_alignment_check instead of advance_stage
        if response == "APPROVE":
            return _try_transition(lambda: enter_alignment_check(state), state)
        elif response == "REVISE":
            _version_blueprint(project_root, "Gate 2.1 REVISE")
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_2_2_blueprint_post_review":
        # Bug 23: APPROVE calls enter_alignment_check instead of advance_stage
        if response == "APPROVE":
            return _try_transition(lambda: enter_alignment_check(state), state)
        elif response == "REVISE":
            _version_blueprint(project_root, "Gate 2.2 REVISE")
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_2_3_alignment_exhausted":
        if response == "REVISE SPEC":
            _version_spec(project_root, "Gate 2.3 REVISE SPEC")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "alignment exhausted: revise spec", project_root
                ),
                state,
            )
        elif response == "RESTART SPEC":
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "alignment exhausted: restart spec", project_root
                ),
                state,
            )
        else:  # RETRY BLUEPRINT
            # Bug 66: version blueprint and reset sub_stage to None
            # so routing re-invokes blueprint_author, not blueprint_checker
            _version_blueprint(project_root, "Gate 2.3 RETRY BLUEPRINT")
            import copy as _copy
            new_state = PipelineState.from_dict(_copy.deepcopy(state.to_dict()))
            new_state.alignment_iteration = 0
            new_state.sub_stage = None
            new_state.last_action = "Gate 2.3: RETRY BLUEPRINT, resetting to blueprint authoring"
            return new_state

    elif gate_id == "gate_3_1_test_validation":
        if response == "TEST CORRECT":
            # F7: Tests are correct, implementation is wrong -> engage fix ladder
            new_state = _try_transition(
                lambda: advance_fix_ladder(state, "fresh_impl"), state
            )
            new_state = advance_sub_stage(new_state, "implementation", project_root)
            return new_state
        else:  # TEST WRONG
            # F7: Tests are wrong -> regenerate tests
            return advance_sub_stage(state, "test_generation", project_root)

    elif gate_id == "gate_3_2_diagnostic_decision":
        if response == "FIX IMPLEMENTATION":
            # Reset fix ladder and go back to implementation
            import copy as _copy
            new_state = PipelineState.from_dict(_copy.deepcopy(state.to_dict()))
            new_state.fix_ladder_position = None
            new_state.sub_stage = "implementation"
            new_state.last_action = "Gate 3.2: FIX IMPLEMENTATION, resetting fix ladder"
            return new_state
        elif response == "FIX BLUEPRINT":
            _version_blueprint(project_root, "Gate 3.2 FIX BLUEPRINT")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "2", "diagnostic: fix blueprint", project_root
                ),
                state,
            )
        else:  # FIX SPEC
            _version_spec(project_root, "Gate 3.2 FIX SPEC")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "diagnostic: fix spec", project_root
                ),
                state,
            )

    elif gate_id == "gate_4_1_integration_failure":
        if response == "ASSEMBLY FIX":
            # Bug 73-B: reset sub_stage so integration_test_author is re-invoked;
            # returning unchanged state loops gate_4_1
            new_state = advance_sub_stage(state, None, project_root)
            new_state.last_action = "Gate 4.1: ASSEMBLY FIX, re-invoking integration test author"
            return new_state
        elif response == "FIX BLUEPRINT":
            _version_blueprint(project_root, "Gate 4.1 FIX BLUEPRINT")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "2", "integration failure: fix blueprint", project_root
                ),
                state,
            )
        else:  # FIX SPEC
            _version_spec(project_root, "Gate 4.1 FIX SPEC")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "integration failure: fix spec", project_root
                ),
                state,
            )

    elif gate_id == "gate_4_2_assembly_exhausted":
        if response == "FIX BLUEPRINT":
            _version_blueprint(project_root, "Gate 4.2 FIX BLUEPRINT")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "2", "assembly exhausted: fix blueprint", project_root
                ),
                state,
            )
        else:  # FIX SPEC
            _version_spec(project_root, "Gate 4.2 FIX SPEC")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "assembly exhausted: fix spec", project_root
                ),
                state,
            )

    elif gate_id == "gate_5_1_repo_test":
        if response == "TESTS PASSED":
            return advance_sub_stage(state, "structural_check", project_root)
        else:  # TESTS FAILED
            # Re-invoke git repo agent with incremented retry counter
            new_state = increment_red_run_retries(state)
            new_state.sub_stage = None
            new_state.last_action = "Repo test failed, re-invoking git repo agent"
            return new_state

    elif gate_id == "gate_5_2_assembly_exhausted":
        if response == "RETRY ASSEMBLY":
            new_state = reset_red_run_retries(state)
            new_state.sub_stage = None
            new_state.last_action = "Retrying repo assembly"
            return new_state
        elif response == "FIX BLUEPRINT":
            _version_blueprint(project_root, "Gate 5.2 FIX BLUEPRINT")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "2", "assembly exhausted: fix blueprint", project_root
                ),
                state,
            )
        else:  # FIX SPEC
            _version_spec(project_root, "Gate 5.2 FIX SPEC")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "assembly exhausted: fix spec", project_root
                ),
                state,
            )

    elif gate_id == "gate_5_3_unused_functions":
        # Bug 58: Gate 5.3 — unused exported functions detected by Gate C
        if response == "FIX SPEC":
            _version_spec(project_root, "Gate 5.3 FIX SPEC (unused functions)")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "1", "Gate 5.3: unused functions, fix spec", project_root
                ),
                state,
            )
        else:  # OVERRIDE CONTINUE
            # Bug 73-A: must advance sub_stage; returning unchanged state loops gate_5_3
            return advance_sub_stage(state, "repo_complete", project_root)

    elif gate_id == "gate_6_0_debug_permission":
        if response == "AUTHORIZE DEBUG":
            return _try_transition(lambda: authorize_debug_session(state), state)
        else:  # ABANDON DEBUG
            return _try_transition(lambda: abandon_debug_session(state), state)

    elif gate_id == "gate_6_1_regression_test":
        if response == "TEST CORRECT":
            # Bug 69 E.2: advance debug phase to complete
            return _try_transition(
                lambda: update_debug_phase(state, "complete"), state
            )
        else:  # TEST WRONG
            # Two-branch no-op: last_status != REGRESSION_TEST_COMPLETE,
            # so routing re-invokes test agent
            return state

    elif gate_id == "gate_6_2_debug_classification":
        if response == "FIX UNIT":
            # Bug 55: Wire rollback_to_unit into Gate 6.2 FIX UNIT
            if state.debug_session is None:
                return state  # Safety: no debug session, no-op
            affected = state.debug_session.affected_units
            if not affected:
                return state  # Safety: no affected units identified
            unit_number = min(affected)
            # Set classification on debug session (belt and suspenders)
            new_state = _try_transition(
                lambda: set_debug_classification(state, "single_unit", affected),
                state,
            )
            # Advance debug phase to stage3_reentry
            new_state = _try_transition(
                lambda: update_debug_phase(new_state, "stage3_reentry"),
                new_state,
            )
            # Perform rollback: invalidate units from N forward, transition to Stage 3
            new_state = _try_transition(
                lambda: rollback_to_unit(new_state, unit_number, project_root),
                new_state,
            )
            # Clear last_status.txt to prevent stale routing when pipeline
            # re-enters Stage 5 after the rebuild
            status_file = project_root / ".svp" / "last_status.txt"
            if status_file.exists():
                status_file.unlink()
            return new_state
        elif response == "FIX BLUEPRINT":
            _version_blueprint(project_root, "Gate 6.2 FIX BLUEPRINT")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "2", "debug: fix blueprint", project_root
                ),
                state,
            )
        else:  # FIX SPEC
            _version_spec(project_root, "Gate 6.2 FIX SPEC")
            return _try_transition(
                lambda: restart_from_stage(state, "1", "debug: fix spec", project_root),
                state,
            )

    elif gate_id == "gate_6_3_repair_exhausted":
        if response == "RETRY REPAIR":
            return state
        elif response == "RECLASSIFY BUG":
            # Bug 69 E.3: reset debug phase to triage and clear classification
            new_state = _try_transition(
                lambda: update_debug_phase(state, "triage"), state
            )
            if new_state.debug_session is not None:
                new_state.debug_session.classification = None
                new_state.debug_session.affected_units = []
            return new_state
        else:  # ABANDON DEBUG
            return _try_transition(lambda: abandon_debug_session(state), state)

    elif gate_id == "gate_6_4_non_reproducible":
        if response == "RETRY TRIAGE":
            return state
        else:  # ABANDON DEBUG
            return _try_transition(lambda: abandon_debug_session(state), state)

    elif gate_id == "gate_6_5_debug_commit":
        if response == "COMMIT APPROVED":
            # Bug 69 E.4: complete debug session -- moves to debug_history
            return _try_transition(
                lambda: complete_debug_session(state, "Debug fix committed and pushed"),
                state,
            )
        else:  # COMMIT REJECTED
            # Two-branch no-op: stays in complete phase, re-presents Gate 6.5
            return state

    elif gate_id == "gate_hint_conflict":
        if response == "BLUEPRINT CORRECT":
            # Discard the hint, continue with blueprint as-is
            return state
        else:  # HINT CORRECT
            # Hint overrides blueprint -- trigger document revision and restart
            _version_blueprint(project_root, "Gate H.1 HINT CORRECT")
            return _try_transition(
                lambda: restart_from_stage(
                    state, "2", "hint conflict: hint correct", project_root
                ),
                state,
            )

    # Fallback (should not reach here)
    return state


def dispatch_agent_status(
    state: PipelineState,
    agent_type: str,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Handle agent terminal status lines."""
    # Validate phase
    if phase not in _KNOWN_PHASES:
        raise ValueError(f"Unknown phase: {phase}")

    # Check if status_line is a cross-agent status
    if status_line.startswith(CROSS_AGENT_STATUS):
        return state

    # Validate against known agent status lines (prefix matching)
    line_recognized = False
    for lines in AGENT_STATUS_LINES.values():
        for known_line in lines:
            if status_line == known_line or status_line.startswith(known_line):
                line_recognized = True
                break
        if line_recognized:
            break

    if not line_recognized:
        raise ValueError(f"Unknown agent status line: {status_line}")

    # Handle specific agent statuses
    if agent_type == "setup_agent":
        if status_line == "PROJECT_CONTEXT_COMPLETE":
            # Bug 21: keep sub-stage unchanged; next route() reads last_status.txt
            return state
        elif status_line == "PROJECT_CONTEXT_REJECTED":
            return state
        elif status_line == "PROFILE_COMPLETE":
            # Bug 21: keep sub-stage unchanged; next route() reads last_status.txt
            return state

    elif agent_type == "stakeholder_dialog":
        if status_line in ("SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"):
            return state

    elif agent_type == "stakeholder_reviewer":
        if status_line == "REVIEW_COMPLETE":
            return state

    elif agent_type == "blueprint_author":
        if status_line in ("BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"):
            return state

    elif agent_type == "blueprint_checker":
        # Bug 23: keep sub_stage at alignment_check
        if status_line == "ALIGNMENT_CONFIRMED":
            return state
        elif status_line.startswith("ALIGNMENT_FAILED"):
            return state

    elif agent_type == "blueprint_reviewer":
        if status_line == "REVIEW_COMPLETE":
            return state

    elif agent_type == "test_agent":
        if status_line == "TEST_GENERATION_COMPLETE":
            # NEW IN 2.1: enter quality_gate_a sub-stage
            # Note: sub_stage may be None (normalized to test_generation by routing)
            if state.stage == "3" and state.sub_stage in (None, "test_generation"):
                return enter_quality_gate(state, "quality_gate_a")
            # If in quality_gate_a_retry, keep sub-stage (agent fix completed)
            return state

    elif agent_type == "implementation_agent":
        if status_line == "IMPLEMENTATION_COMPLETE":
            # NEW IN 2.1: enter quality_gate_b sub-stage
            if state.stage == "3" and state.sub_stage == "implementation":
                return enter_quality_gate(state, "quality_gate_b")
            # If in quality_gate_b_retry, keep sub-stage (agent fix completed)
            return state

    elif agent_type == "coverage_review":
        # F5: Keep sub_stage at coverage_review; route() reads last_status for two-branch
        return state

    elif agent_type == "diagnostic_agent":
        # F4: Parse diagnostic classification and set appropriate state
        if status_line.startswith("DIAGNOSIS_COMPLETE:"):
            classification = status_line.split(": ", 1)[1].strip()
            if classification == "implementation":
                # Advance to diagnostic_impl for implementation retry with guidance
                new_state = _try_transition(
                    lambda: advance_fix_ladder(state, "diagnostic_impl"), state
                )
                return advance_sub_stage(new_state, "implementation", project_root)
            elif classification in ("blueprint", "spec"):
                # Surface at Gate 3.2 for human decision
                return state  # route() will present Gate 3.2 based on fix ladder exhaustion
        return state

    elif agent_type == "integration_test_author":
        return state

    elif agent_type == "git_repo_agent":
        if status_line == "REPO_ASSEMBLY_COMPLETE":
            # Record delivered repo path and advance to repo test
            project_name = project_root.name.replace("-workspace", "")
            repo_path = str(project_root.parent / f"{project_name}-repo")
            new_state = set_delivered_repo_path(state, repo_path)
            return advance_sub_stage(new_state, "repo_test", project_root)
        return state

    elif agent_type == "help_agent":
        return state

    elif agent_type == "hint_agent":
        return state

    elif agent_type == "redo_agent":
        if status_line == "REDO_CLASSIFIED: spec":
            return restart_from_stage(state, "1", "redo: spec", project_root)
        elif status_line == "REDO_CLASSIFIED: blueprint":
            return restart_from_stage(state, "2", "redo: blueprint", project_root)
        elif status_line == "REDO_CLASSIFIED: gate":
            return state
        elif status_line == "REDO_CLASSIFIED: profile_delivery":
            return enter_redo_profile_revision(state, "profile_delivery")
        elif status_line == "REDO_CLASSIFIED: profile_blueprint":
            return enter_redo_profile_revision(state, "profile_blueprint")

    elif agent_type == "bug_triage":
        # Bug 55: parse classification and read affected_units from triage result
        if status_line.startswith("TRIAGE_COMPLETE:"):
            classification = status_line.split(": ", 1)[1].strip()
            affected_units = _read_triage_affected_units(project_root)
            return _try_transition(
                lambda: set_debug_classification(state, classification, affected_units),
                state,
            )
        return state

    elif agent_type == "repair_agent":
        if status_line == "REPAIR_COMPLETE":
            if state.debug_session is not None:
                # Bug 51: trigger Stage 5 reassembly
                import copy as _copy

                new_state = PipelineState.from_dict(
                    _copy.deepcopy(state.to_dict())
                )
                new_state.stage = "5"
                new_state.sub_stage = None
                new_state.last_action = (
                    "Debug repair complete, reassembling"
                )
                return new_state
        return state

    elif agent_type == "reference_indexing":
        # Bug 42: advance from pre_stage_3 to stage 3 on INDEXING_COMPLETE
        if status_line == "INDEXING_COMPLETE" and state.stage == "pre_stage_3":
            return advance_stage(state, project_root)
        return state

    return state


def dispatch_command_status(
    state: PipelineState,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Parse command result status lines and call appropriate transitions."""
    # Validate phase
    if phase not in _KNOWN_PHASES:
        raise ValueError(f"Unknown phase: {phase}")

    # Validate status line against known command status patterns
    if not any(status_line.startswith(p) for p in COMMAND_STATUS_PATTERNS):
        raise ValueError(f"Unknown command status: {status_line}")

    if phase == "test_execution":
        if status_line.startswith("TESTS_PASSED"):
            # Green run: advance to coverage_review
            if state.sub_stage == "green_run":
                return advance_sub_stage(state, "coverage_review", project_root)
            # F2: Red run with TESTS_PASSED means defective tests
            if state.sub_stage == "red_run":
                # F10: Increment red_run_retries
                new_state = increment_red_run_retries(state)
                # Check retry limit (default 3)
                if new_state.red_run_retries >= 3:
                    # Present Gate 3.1 for human decision
                    return advance_sub_stage(new_state, "gate_3_1", project_root)
                # Under limit: regenerate tests
                return advance_sub_stage(new_state, "test_generation", project_root)
            # Stage 4: integration tests passed -> advance to Stage 5
            if state.stage == "4":
                return advance_stage(state, project_root)
            return state
        elif status_line.startswith("TESTS_FAILED"):
            # Red run: all tests should fail against stubs -> advance to implementation
            if state.sub_stage == "red_run":
                return advance_sub_stage(state, "implementation", project_root)
            # F3: Green run failure -> engage fix ladder
            if state.sub_stage == "green_run":
                ladder_pos = state.fix_ladder_position
                if ladder_pos is None:
                    # First failure: advance to fresh_impl
                    new_state = _try_transition(
                        lambda: advance_fix_ladder(state, "fresh_impl"), state
                    )
                    return advance_sub_stage(new_state, "implementation", project_root)
                elif ladder_pos == "fresh_impl":
                    # Second failure: advance to diagnostic
                    new_state = _try_transition(
                        lambda: advance_fix_ladder(state, "diagnostic"), state
                    )
                    return advance_sub_stage(new_state, "implementation", project_root)
                elif ladder_pos == "diagnostic_impl":
                    # Exhausted: present Gate 3.2
                    return advance_sub_stage(state, "gate_3_2", project_root)
                else:
                    # Other positions: try next ladder step or Gate 3.2
                    return advance_sub_stage(state, "gate_3_2", project_root)
            # Bug 71: Stage 4 TESTS_FAILED handler (missing from original)
            if state.stage == "4":
                new_state = increment_red_run_retries(state)
                if new_state.red_run_retries >= 3:
                    return advance_sub_stage(new_state, "gate_4_2", project_root)
                return advance_sub_stage(new_state, "gate_4_1", project_root)
            return state
        elif status_line.startswith("TESTS_ERROR"):
            # Bug 70 F2: TESTS_ERROR must not return state unchanged (infinite loop).
            # Red run: collection error means stub or test import problem -> regenerate tests
            if state.sub_stage == "red_run":
                new_state = increment_red_run_retries(state)
                if new_state.red_run_retries >= 3:
                    return advance_sub_stage(new_state, "gate_3_1", project_root)
                return advance_sub_stage(new_state, "test_generation", project_root)
            # Green run: collection error means impl has import/syntax errors -> fix ladder
            if state.sub_stage == "green_run":
                ladder_pos = state.fix_ladder_position
                if ladder_pos is None:
                    new_state = _try_transition(
                        lambda: advance_fix_ladder(state, "fresh_impl"), state
                    )
                    return advance_sub_stage(new_state, "implementation", project_root)
                elif ladder_pos == "fresh_impl":
                    new_state = _try_transition(
                        lambda: advance_fix_ladder(state, "diagnostic"), state
                    )
                    return advance_sub_stage(new_state, "implementation", project_root)
                elif ladder_pos == "diagnostic_impl":
                    return advance_sub_stage(state, "gate_3_2", project_root)
                else:
                    return advance_sub_stage(state, "gate_3_2", project_root)
            # Stage 4: TESTS_ERROR -> same as TESTS_FAILED (present gate)
            if state.stage == "4":
                new_state = increment_red_run_retries(state)
                if new_state.red_run_retries >= 3:
                    return advance_sub_stage(new_state, "gate_4_2", project_root)
                return advance_sub_stage(new_state, "gate_4_1", project_root)
            return state

    # F9: stub_generation command dispatch
    elif phase == "stub_generation":
        if status_line.startswith("COMMAND_SUCCEEDED"):
            return advance_sub_stage(state, "test_generation", project_root)
        return state

    # Bug 72: structural_check command status dispatch
    elif phase == "structural_check":
        if status_line.startswith("COMMAND_SUCCEEDED"):
            # Clean -- advance to compliance_scan
            return advance_sub_stage(state, "compliance_scan", project_root)
        elif status_line.startswith("COMMAND_FAILED"):
            # Findings detected -- present Gate 5.3 (unused function gate)
            return advance_sub_stage(state, "gate_5_3", project_root)
        return state

    elif phase == "compliance_scan":
        if status_line.startswith("COMMAND_SUCCEEDED"):
            # Scan passed -- repo delivery complete
            return advance_sub_stage(state, "repo_complete", project_root)
        elif status_line.startswith("UNUSED_FUNCTIONS_DETECTED"):
            # Bug 67: unused exported functions found -- present Gate 5.3
            return advance_sub_stage(state, "gate_5_3", project_root)
        elif status_line.startswith("COMMAND_FAILED"):
            # Violations found -- re-enter bounded fix cycle
            new_state = increment_red_run_retries(state)
            new_state.sub_stage = None
            new_state.last_action = "Compliance scan failed, re-invoking git repo agent"
            return new_state

    elif phase == "quality_gate":
        # NEW IN 2.1: quality gate command status dispatch
        if status_line.startswith("COMMAND_SUCCEEDED"):
            # Pass regardless of initial or retry sub-stage
            return quality_gate_pass(state)
        elif status_line.startswith("COMMAND_FAILED"):
            # Check current sub-stage to determine action
            if state.sub_stage in ("quality_gate_a", "quality_gate_b"):
                # First run: advance to retry
                return advance_quality_gate_to_retry(state)
            elif state.sub_stage in ("quality_gate_a_retry", "quality_gate_b_retry"):
                # Re-run after agent fix: enter fix ladder
                return quality_gate_fail_to_ladder(state)
            # Fallback
            return state

    elif phase == "unit_completion":
        if status_line.startswith("COMMAND_SUCCEEDED"):
            # Advance to next unit
            return complete_unit(state, unit, project_root)

    # Generic handling for other phases
    return state


# --- Run tests wrapper ---


def run_pytest(
    test_path: Path,
    env_name: str,
    project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None,
) -> str:
    """Execute pytest and return a command result status line."""
    # Build command
    if (
        toolchain is not None
        and "testing" in toolchain
        and "run" in toolchain["testing"]
    ):
        # Use toolchain template
        try:
            from svp_config import resolve_command

            cmd = resolve_command(
                toolchain,
                "testing.run",
                {"test_path": str(test_path), "env_name": env_name},
            )
        except Exception:
            cmd = toolchain["testing"]["run"]
            cmd = cmd.replace("{test_path}", str(test_path))
            cmd = cmd.replace("{env_name}", env_name)
    else:
        cmd = f"conda run -n {env_name} pytest {test_path} -v"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=300,
        )
        output = result.stdout + "\n" + result.stderr

        # Check for collection errors
        if _is_collection_error(output, toolchain):
            error_summary = (
                output.strip().split("\n")[-1] if output.strip() else "collection error"
            )
            return f"TESTS_ERROR: {error_summary}"

        if result.returncode == 0:
            # Parse pass count from output
            return f"TESTS_PASSED: {_extract_test_summary(output)}"
        else:
            return f"TESTS_FAILED: {_extract_test_summary(output)}"
    except subprocess.TimeoutExpired:
        return "TESTS_ERROR: timeout"
    except Exception as e:
        return f"TESTS_ERROR: {str(e)}"


def _extract_test_summary(output: str) -> str:
    """Extract a test summary from pytest output."""
    lines = output.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if "passed" in line or "failed" in line or "error" in line:
            # Clean up ANSI codes and formatting
            clean = line.strip("= ").strip()
            if clean:
                return clean
    return "completed"


def _is_collection_error(
    output: str, toolchain: Optional[Dict[str, Any]] = None
) -> bool:
    """Check if pytest output indicates a collection error."""
    if toolchain is not None:
        try:
            from svp_config import get_collection_error_indicators

            indicators = get_collection_error_indicators(toolchain)
            if indicators:
                for indicator in indicators:
                    if indicator in output:
                        return True
                return False
        except Exception:
            pass

        # Fallback: check directly
        if (
            "testing" in toolchain
            and "collection_error_indicators" in toolchain["testing"]
        ):
            indicators = toolchain["testing"]["collection_error_indicators"]
            for indicator in indicators:
                if indicator in output:
                    return True
            return False

    # Default specific indicators -- must NOT use bare "ERROR"
    indicators = [
        "ERROR collecting",
        "ImportError",
        "ModuleNotFoundError",
        "SyntaxError",
        "no tests ran",
    ]

    for indicator in indicators:
        if indicator in output:
            return True

    return False


# --- CLI entry points ---


def routing_main() -> None:
    """CLI entry point for routing script."""
    import argparse

    parser = argparse.ArgumentParser(description="SVP Routing Script")
    parser.add_argument(
        "--project-root", type=str, default=".", help="Project root directory"
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    # Startup check: compare KNOWN_AGENT_TYPES between agent_constants and prepare_task
    try:
        _check_agent_type_consistency()
    except Exception:
        pass

    from pipeline_state import load_state

    state = load_state(project_root)
    action = route(state, project_root)
    print(format_action_block(action))


def _check_agent_type_consistency():
    """Emit a warning to stderr if KNOWN_AGENT_TYPES diverge between modules."""
    try:
        import importlib

        stub_mod = importlib.import_module("agent_constants")
        prep_mod = importlib.import_module("prepare_task")
        stub_types = getattr(stub_mod, "KNOWN_AGENT_TYPES", None)
        prep_types = getattr(prep_mod, "KNOWN_AGENT_TYPES", None)
        if stub_types is not None and prep_types is not None:
            if set(stub_types) != set(prep_types):
                print(
                    "WARNING: KNOWN_AGENT_TYPES diverge between "
                    "agent_constants and prepare_task",
                    file=sys.stderr,
                )
    except Exception:
        pass


def update_state_main(
    argv: "Optional[List[str]]" = None,
) -> None:
    """CLI entry point for update_state script.

    This is the actual POST command entry point. It reads the status file
    and calls dispatch_status() directly to route the terminal status line
    to the appropriate state transition function. The previously existing
    update_state_from_status() in state_transitions.py was a hollow skeleton
    that never dispatched and was removed in Bug 54.
    """
    import argparse

    parser = argparse.ArgumentParser(description="SVP Update State Script")
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory",
    )
    parser.add_argument(
        "--gate-id",
        type=str,
        default=None,
        help="Gate ID for gate responses",
    )
    parser.add_argument(
        "--unit",
        type=int,
        default=None,
        help="Unit number",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default="main",
        help="Current phase",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()

    from pipeline_state import load_state, save_state

    state = load_state(project_root)

    status_file = project_root / ".svp" / "last_status.txt"
    if status_file.exists():
        status_line = status_file.read_text(encoding="utf-8").strip()
    else:
        return

    new_state = dispatch_status(
        state, status_line, args.gate_id, args.unit, args.phase, project_root
    )
    save_state(new_state, project_root)


def run_tests_main(
    argv: "Optional[List[str]]" = None,
) -> None:
    """CLI entry point for run_tests script."""
    import argparse

    parser = argparse.ArgumentParser(description="SVP Run Tests Script")
    parser.add_argument(
        "test_path",
        nargs="?",
        default="tests",
        help="Path to test file or directory",
    )
    parser.add_argument(
        "--env-name",
        type=str,
        default="default",
        help="Conda environment name",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory",
    )
    parser.add_argument(
        "--test-path",
        type=str,
        default=None,
        dest="test_path_flag",
        help=("Alternative to positional (cross-unit CLI contract)"),
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    raw = args.test_path_flag or args.test_path
    test_path = Path(raw)

    result = run_pytest(test_path, args.env_name, project_root)
    print(result)


def run_quality_gate_main(
    argv: "Optional[List[str]]" = None,
) -> None:
    """CLI entry point for run_quality_gate script.

    CLI args: gate_id (positional or --gate),
    --target, --env-name, --project-root.
    Calls run_quality_gate(), writes status to
    .svp/last_status.txt, writes report to
    .svp/quality_report.md if residuals detected.
    """
    import argparse

    parser = argparse.ArgumentParser(description="SVP Quality Gate Runner")
    parser.add_argument(
        "gate_id",
        nargs="?",
        default="gate_a",
        help="Quality gate identifier",
    )
    parser.add_argument(
        "--gate",
        type=str,
        default=None,
        choices=["gate_a", "gate_b", "gate_c"],
        help="Alternative to positional",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="src",
        help="Target path for quality checks",
    )
    parser.add_argument(
        "--env-name",
        type=str,
        default="default",
        help="Conda environment name",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory",
    )
    args = parser.parse_args(argv)

    # Resolve gate from positional or --gate flag
    gate = args.gate if args.gate else args.gate_id

    project_root = Path(args.project_root).resolve()
    target_path = Path(args.target)

    # Determine env_name from project
    try:
        from svp_config import load_config
        from pipeline_state import load_state

        state = load_state(project_root)
        env_name = state.project_name or "svp"
    except Exception:
        env_name = "svp"

    result = run_quality_gate(gate, target_path, env_name, project_root)

    # Write status to .svp/last_status.txt
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(exist_ok=True)
    status_file = svp_dir / "last_status.txt"

    if result["status"] == "clean":
        status_file.write_text("COMMAND_SUCCEEDED\n", encoding="utf-8")
    else:
        status_file.write_text("COMMAND_FAILED: quality residuals\n", encoding="utf-8")
        # Write quality report
        report_file = svp_dir / "quality_report.md"
        report_file.write_text(result["report"], encoding="utf-8")


if __name__ == "__main__":
    routing_main()
