"""Unit 10: Routing Script and Update State.

Implements routing, dispatch, gate vocabulary, agent status lines,
test execution wrappers, and quality gate execution for the SVP pipeline.

SVP 2.1: Includes Bug 1 fix (gate vocabulary), Bug 21 fix (two-branch routing),
Bug 23 fix (alignment check routing), Bug 25 fix (all Stage 3 sub-stages),
Bug 41 fix (Stage 1 two-branch routing and gate registration),
Bug 42 fix (pre-stage-3 state persistence and reference indexing advancement),
Bug 43 fix (two-branch routing invariant for Stage 4, Stage 5, redo profile, debug loop),
Gate 6.5 (debug commit), and quality gate execution.
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
    reset_fix_ladder,
    increment_red_run_retries,
    reset_red_run_retries,
    increment_alignment_iteration,
    reset_alignment_iteration,
    record_pass_end,
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
)

# --- Data contract: gate status string vocabulary (Bug 1 fix) ---

GATE_VOCABULARY: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": ["CONTEXT APPROVED", "CONTEXT REJECTED", "CONTEXT NOT READY"],
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
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_2_debug_classification": ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_3_repair_exhausted": ["RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
    "gate_6_5_debug_commit": ["COMMIT APPROVED", "COMMIT REJECTED"],
}

# --- Data contract: terminal status line vocabulary ---

AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": [
        "PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED",
        "PROFILE_COMPLETE",
    ],
    "stakeholder_dialog": ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"],
    "stakeholder_reviewer": ["REVIEW_COMPLETE"],
    "blueprint_author": ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"],
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
    "redo_agent": [
        "REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint", "REDO_CLASSIFIED: gate",
        "REDO_CLASSIFIED: profile_delivery", "REDO_CLASSIFIED: profile_blueprint",
    ],
    "bug_triage": ["TRIAGE_COMPLETE: build_env", "TRIAGE_COMPLETE: single_unit", "TRIAGE_COMPLETE: cross_unit", "TRIAGE_NEEDS_REFINEMENT", "TRIAGE_NON_REPRODUCIBLE"],
    "repair_agent": ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"],
    "reference_indexing": ["INDEXING_COMPLETE"],
}

# Cross-agent status (any agent receiving a hint)
CROSS_AGENT_STATUS: str = "HINT_BLUEPRINT_CONFLICT"

# Alias: GATE_RESPONSES mirrors GATE_VOCABULARY (same data, backward-compatible name)
GATE_RESPONSES: Dict[str, List[str]] = GATE_VOCABULARY

# Alias: CROSS_AGENT_STATUS_LINES maps status string to gate_id
CROSS_AGENT_STATUS_LINES: Dict[str, str] = {
    "HINT_BLUEPRINT_CONFLICT": "gate_hint_conflict",
}

# Command result status line patterns
COMMAND_STATUS_PATTERNS: List[str] = [
    "TESTS_PASSED",    # "TESTS_PASSED: N passed"
    "TESTS_FAILED",    # "TESTS_FAILED: N passed, M failed"
    "TESTS_ERROR",     # "TESTS_ERROR: [error summary]"
    "COMMAND_SUCCEEDED",
    "COMMAND_FAILED",  # "COMMAND_FAILED: [exit code]"
]

# Known phases for dispatch
_KNOWN_PHASES = {
    "setup", "spec_draft", "spec_revision", "spec_review",
    "blueprint_draft", "blueprint_revision", "blueprint_review",
    "alignment_check", "test_generation", "test_execution", "test",
    "implementation", "coverage_review", "diagnostic",
    "integration_test", "repo_assembly", "compliance_scan",
    "gate", "redo", "debug", "help", "hint", "reference_indexing",
    "bug_triage", "repair", "regression_test",
    "infrastructure_setup", "stub_generation", "unit_completion",
    "quality_gate",  # NEW IN 2.1
}


def _try_transition(fn, fallback_state):
    """Try a state transition, returning fallback_state if TransitionError is raised."""
    try:
        return fn()
    except TransitionError:
        return fallback_state


# --- Helper: read last_status.txt ---

def _read_last_status(project_root: Path) -> Optional[str]:
    """Read .svp/last_status.txt if it exists, return stripped content or None."""
    status_file = project_root / ".svp" / "last_status.txt"
    if status_file.exists():
        content = status_file.read_text(encoding="utf-8").strip()
        if content:
            return content
    return None


# Public alias: read_last_status exposes _read_last_status as a public function
def read_last_status(project_root: Path) -> str:
    """Read and return content of last_status.txt (public alias)."""
    status_file = project_root / ".svp" / "last_status.txt"
    if not status_file.exists():
        return ""
    return status_file.read_text(encoding="utf-8").strip()


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
            last_status = _read_last_status(project_root)
            if last_status == "PROJECT_CONTEXT_COMPLETE":
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
            last_status = _read_last_status(project_root)
            if last_status == "PROFILE_COMPLETE":
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
            if last_status in ("BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"):
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
    if stage == "3":
        unit = state.current_unit

        if sub_stage is None or sub_stage == "test_generation":
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
            return {
                "ACTION": "invoke_agent",
                "AGENT": "implementation_agent",
                "CONTEXT": "implementation",
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
    if stage == "4":
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
        # Bug 43: two-branch routing for debug loop triage
        if state.debug_session is not None:
            last_status = _read_last_status(project_root)
            if last_status is not None and last_status.startswith("TRIAGE_COMPLETE"):
                return {
                    "ACTION": "human_gate",
                    "GATE_ID": "gate_6_2_debug_classification",
                    "OPTIONS": GATE_VOCABULARY["gate_6_2_debug_classification"],
                    "PREPARE": _gate_prepare_cmd("gate_6_2_debug_classification"),
                    "POST": _post_cmd("gate", gate_id="gate_6_2_debug_classification"),
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

        if sub_stage == "compliance_scan":
            return {
                "ACTION": "run_command",
                "COMMAND": f"python scripts/compliance_scan.py --project-root .",
                "CONTEXT": "compliance_scan",
                "POST": _post_cmd("compliance_scan"),
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
            return dispatch_command_status(state, status_line, unit, phase, project_root)

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
    return dispatch_agent_status(state, agent_type, status_line, unit, phase, project_root)


def dispatch_gate_response(
    state: PipelineState,
    gate_id: str,
    response: str,
    project_root: Path,
) -> PipelineState:
    """Validate the response against GATE_VOCABULARY and dispatch accordingly."""
    # Invariant: gate_id must be in vocabulary
    if gate_id not in GATE_VOCABULARY:
        raise ValueError(
            f"Unknown gate ID: {gate_id}"
        )

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
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_1_2_spec_post_review":
        if response == "APPROVE":
            return _try_transition(lambda: advance_stage(state, project_root), state)
        elif response == "REVISE":
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_2_1_blueprint_approval":
        # Bug 23: APPROVE calls enter_alignment_check instead of advance_stage
        if response == "APPROVE":
            return _try_transition(lambda: enter_alignment_check(state), state)
        elif response == "REVISE":
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_2_2_blueprint_post_review":
        # Bug 23: APPROVE calls enter_alignment_check instead of advance_stage
        if response == "APPROVE":
            return _try_transition(lambda: enter_alignment_check(state), state)
        elif response == "REVISE":
            return state
        else:  # FRESH REVIEW
            return state

    elif gate_id == "gate_2_3_alignment_exhausted":
        if response == "REVISE SPEC":
            return _try_transition(lambda: restart_from_stage(state, "1", "alignment exhausted: revise spec", project_root), state)
        elif response == "RESTART SPEC":
            return _try_transition(lambda: restart_from_stage(state, "1", "alignment exhausted: restart spec", project_root), state)
        else:  # RETRY BLUEPRINT
            return state

    elif gate_id == "gate_3_1_test_validation":
        if response == "TEST CORRECT":
            return state
        else:  # TEST WRONG
            return state

    elif gate_id == "gate_3_2_diagnostic_decision":
        if response == "FIX IMPLEMENTATION":
            return state
        elif response == "FIX BLUEPRINT":
            return _try_transition(lambda: restart_from_stage(state, "2", "diagnostic: fix blueprint", project_root), state)
        else:  # FIX SPEC
            return _try_transition(lambda: restart_from_stage(state, "1", "diagnostic: fix spec", project_root), state)

    elif gate_id == "gate_4_1_integration_failure":
        if response == "ASSEMBLY FIX":
            return state
        elif response == "FIX BLUEPRINT":
            return _try_transition(lambda: restart_from_stage(state, "2", "integration failure: fix blueprint", project_root), state)
        else:  # FIX SPEC
            return _try_transition(lambda: restart_from_stage(state, "1", "integration failure: fix spec", project_root), state)

    elif gate_id == "gate_4_2_assembly_exhausted":
        if response == "FIX BLUEPRINT":
            return _try_transition(lambda: restart_from_stage(state, "2", "assembly exhausted: fix blueprint", project_root), state)
        else:  # FIX SPEC
            return _try_transition(lambda: restart_from_stage(state, "1", "assembly exhausted: fix spec", project_root), state)

    elif gate_id == "gate_5_1_repo_test":
        if response == "TESTS PASSED":
            return advance_sub_stage(state, "compliance_scan", project_root)
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
            return _try_transition(lambda: restart_from_stage(state, "2", "assembly exhausted: fix blueprint", project_root), state)
        else:  # FIX SPEC
            return _try_transition(lambda: restart_from_stage(state, "1", "assembly exhausted: fix spec", project_root), state)

    elif gate_id == "gate_6_0_debug_permission":
        if response == "AUTHORIZE DEBUG":
            return _try_transition(lambda: authorize_debug_session(state), state)
        else:  # ABANDON DEBUG
            return _try_transition(lambda: abandon_debug_session(state), state)

    elif gate_id == "gate_6_1_regression_test":
        if response == "TEST CORRECT":
            return state
        else:  # TEST WRONG
            return state

    elif gate_id == "gate_6_2_debug_classification":
        if response == "FIX UNIT":
            return state
        elif response == "FIX BLUEPRINT":
            return _try_transition(lambda: restart_from_stage(state, "2", "debug: fix blueprint", project_root), state)
        else:  # FIX SPEC
            return _try_transition(lambda: restart_from_stage(state, "1", "debug: fix spec", project_root), state)

    elif gate_id == "gate_6_3_repair_exhausted":
        if response == "RETRY REPAIR":
            return state
        elif response == "RECLASSIFY BUG":
            return state
        else:  # ABANDON DEBUG
            return _try_transition(lambda: abandon_debug_session(state), state)

    elif gate_id == "gate_6_4_non_reproducible":
        if response == "RETRY TRIAGE":
            return state
        else:  # ABANDON DEBUG
            return _try_transition(lambda: abandon_debug_session(state), state)

    elif gate_id == "gate_6_5_debug_commit":
        if response == "COMMIT APPROVED":
            # Proceed with commit
            return state
        else:  # COMMIT REJECTED
            # Allow human edit or abort
            return state

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
        if status_line.startswith("COVERAGE_COMPLETE"):
            if state.stage == "3" and state.sub_stage == "coverage_review":
                return advance_sub_stage(state, "unit_completion", project_root)
        return state

    elif agent_type == "diagnostic_agent":
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
        return state

    elif agent_type == "repair_agent":
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
            # Stage 4: integration tests passed -> advance to Stage 5
            if state.stage == "4":
                return advance_stage(state, project_root)
            return state
        elif status_line.startswith("TESTS_FAILED"):
            # Red run: all tests should fail against stubs -> advance to implementation
            if state.sub_stage == "red_run":
                return advance_sub_stage(state, "implementation", project_root)
            # Green run failure: stay at green_run for retry/fix ladder
            return state
        elif status_line.startswith("TESTS_ERROR"):
            return state

    elif phase == "compliance_scan":
        if status_line.startswith("COMMAND_SUCCEEDED"):
            # Scan passed -- repo delivery complete
            return advance_sub_stage(state, "repo_complete", project_root)
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
    if toolchain is not None and "testing" in toolchain and "run" in toolchain["testing"]:
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
            error_summary = output.strip().split("\n")[-1] if output.strip() else "collection error"
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


def _is_collection_error(output: str, toolchain: Optional[Dict[str, Any]] = None) -> bool:
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
        if "testing" in toolchain and "collection_error_indicators" in toolchain["testing"]:
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
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
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


def update_state_main() -> None:
    """CLI entry point for update_state script."""
    import argparse
    parser = argparse.ArgumentParser(description="SVP Update State Script")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    parser.add_argument("--gate-id", type=str, default=None, help="Gate ID for gate responses")
    parser.add_argument("--unit", type=int, default=None, help="Unit number")
    parser.add_argument("--phase", type=str, required=True, help="Current phase")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    from pipeline_state import load_state, save_state
    state = load_state(project_root)

    status_file = project_root / ".svp" / "last_status.txt"
    if status_file.exists():
        status_line = status_file.read_text(encoding="utf-8").strip()
    else:
        return

    new_state = dispatch_status(state, status_line, args.gate_id, args.unit, args.phase, project_root)
    save_state(new_state, project_root)


def run_tests_main() -> None:
    """CLI entry point for run_tests script."""
    import argparse
    parser = argparse.ArgumentParser(description="SVP Run Tests Script")
    parser.add_argument("--test-path", type=str, required=True, help="Path to test file or directory")
    parser.add_argument("--env-name", type=str, required=True, help="Conda environment name")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    test_path = Path(args.test_path)

    result = run_pytest(test_path, args.env_name, project_root)
    print(result)


def run_quality_gate_main() -> None:
    """CLI entry point for run_quality_gate script.

    CLI args: --gate (gate_a|gate_b|gate_c), --target (path), --project-root (path)
    Calls run_quality_gate(), writes status to .svp/last_status.txt,
    writes report to .svp/quality_report.md if residuals detected.
    """
    import argparse
    parser = argparse.ArgumentParser(description="SVP Quality Gate Runner")
    parser.add_argument("--gate", type=str, required=True,
                        choices=["gate_a", "gate_b", "gate_c"],
                        help="Quality gate to run")
    parser.add_argument("--target", type=str, required=True,
                        help="Target path for quality checks")
    parser.add_argument("--project-root", type=str, default=".",
                        help="Project root directory")
    args = parser.parse_args()

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

    result = run_quality_gate(args.gate, target_path, env_name, project_root)

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
