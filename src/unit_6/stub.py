"""Unit 6: State Transitions -- full implementation."""

import copy
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.unit_5.stub import (
    VALID_DEBUG_PHASES,
    VALID_FIX_LADDER_POSITIONS,
    VALID_STAGES,
    VALID_SUB_STAGES,
    PipelineState,
)

# ---------------------------------------------------------------------------
# Additional sub-stages that are not bound to a specific stage
# ---------------------------------------------------------------------------

ADDITIONAL_SUB_STAGES = {
    "redo_profile_delivery",
    "redo_profile_blueprint",
    "pass_transition",
    "pass2_active",
    "targeted_spec_revision",
    "spec_review",
    "blueprint_review",
}

# ---------------------------------------------------------------------------
# Mapping from stage to its "first" sub-stage (for restart_from_stage)
# ---------------------------------------------------------------------------

_FIRST_SUB_STAGE: Dict[str, Optional[str]] = {
    "0": "hook_activation",
    "1": None,
    "2": "blueprint_dialog",
    "pre_stage_3": None,
    "3": None,
    "4": None,
    "5": None,
}


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class TransitionError(Exception):
    """Raised when a state transition precondition is violated."""


# ---------------------------------------------------------------------------
# Helper: deep-copy state
# ---------------------------------------------------------------------------


def _copy_state(state: PipelineState) -> PipelineState:
    """Return a deep copy of the given PipelineState. Never mutate the input."""
    return copy.deepcopy(state)


# ---------------------------------------------------------------------------
# Transition functions
# ---------------------------------------------------------------------------


def advance_stage(state: PipelineState, target_stage: str) -> PipelineState:
    """Advance the pipeline to *target_stage*, resetting per-stage fields."""
    if target_stage not in VALID_STAGES:
        raise TransitionError(
            f"Invalid target stage: {target_stage!r}. "
            f"Must be one of {sorted(VALID_STAGES)}"
        )
    new = _copy_state(state)
    new.stage = target_stage
    new.sub_stage = None
    new.current_unit = None
    new.fix_ladder_position = None
    new.red_run_retries = 0
    return new


def advance_sub_stage(state: PipelineState, target_sub_stage: str) -> PipelineState:
    """Set sub_stage to *target_sub_stage* after validation."""
    valid_for_stage = VALID_SUB_STAGES.get(state.stage, set())
    if (
        target_sub_stage not in valid_for_stage
        and target_sub_stage not in ADDITIONAL_SUB_STAGES
    ):
        raise TransitionError(
            f"Invalid sub-stage {target_sub_stage!r} for stage {state.stage!r}"
        )
    new = _copy_state(state)
    new.sub_stage = target_sub_stage
    return new


def complete_unit(state: PipelineState) -> PipelineState:
    """Complete the current unit: record it, advance to the next or finish."""
    if state.current_unit is None:
        raise TransitionError("current_unit is None; cannot complete unit")
    if state.sub_stage != "unit_completion":
        raise TransitionError(
            f"sub_stage must be 'unit_completion' to complete a unit, "
            f"got {state.sub_stage!r}"
        )

    new = _copy_state(state)

    # Append completion record
    record: Dict[str, Any] = {
        "unit": new.current_unit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    new.verified_units.append(record)

    # Reset per-unit state
    new.fix_ladder_position = None
    new.red_run_retries = 0

    # Advance to next unit or mark done
    next_unit = new.current_unit + 1
    if next_unit <= new.total_units:
        new.current_unit = next_unit
        new.sub_stage = "stub_generation"
    else:
        new.current_unit = None
        new.sub_stage = None

    return new


def advance_fix_ladder(state: PipelineState) -> PipelineState:
    """Progress the fix ladder to the next rung."""
    current_pos = state.fix_ladder_position

    if current_pos not in VALID_FIX_LADDER_POSITIONS:
        raise TransitionError(f"Invalid fix_ladder_position: {current_pos!r}")

    # If already at exhausted, cannot advance further
    if current_pos == "exhausted":
        raise TransitionError("Cannot advance fix ladder: already at 'exhausted'")

    # Determine the current index and next position
    current_idx = VALID_FIX_LADDER_POSITIONS.index(current_pos)
    next_pos = VALID_FIX_LADDER_POSITIONS[current_idx + 1]

    new = _copy_state(state)
    new.fix_ladder_position = next_pos

    # Set sub_stage to "implementation" for fresh_impl and diagnostic_impl
    if next_pos in ("fresh_impl", "diagnostic_impl"):
        new.sub_stage = "implementation"

    return new


def increment_red_run_retries(state: PipelineState) -> PipelineState:
    """Increment the red_run_retries counter by 1."""
    new = _copy_state(state)
    new.red_run_retries += 1
    return new


def reset_red_run_retries(state: PipelineState) -> PipelineState:
    """Reset red_run_retries to 0."""
    new = _copy_state(state)
    new.red_run_retries = 0
    return new


def increment_alignment_iteration(state: PipelineState) -> PipelineState:
    """Increment alignment_iterations by 1."""
    new = _copy_state(state)
    new.alignment_iterations += 1
    return new


def rollback_to_unit(state: PipelineState, unit_number: int) -> PipelineState:
    """Roll back to a specific unit, removing later verified units."""
    if unit_number < 1:
        raise TransitionError(f"unit_number must be >= 1, got {unit_number}")
    if unit_number > state.total_units:
        raise TransitionError(
            f"unit_number {unit_number} exceeds total_units {state.total_units}"
        )

    new = _copy_state(state)
    new.stage = "3"
    new.current_unit = unit_number
    new.sub_stage = "stub_generation"
    new.verified_units = [
        vu for vu in new.verified_units if vu.get("unit", 0) < unit_number
    ]
    new.fix_ladder_position = None
    new.red_run_retries = 0
    return new


def restart_from_stage(state: PipelineState, target_stage: str) -> PipelineState:
    """Restart the pipeline from *target_stage*, resetting relevant fields."""
    if target_stage not in VALID_STAGES:
        raise TransitionError(
            f"Invalid target stage: {target_stage!r}. "
            f"Must be one of {sorted(VALID_STAGES)}"
        )

    new = _copy_state(state)
    new.stage = target_stage
    new.sub_stage = _FIRST_SUB_STAGE.get(target_stage)
    new.current_unit = None
    new.fix_ladder_position = None
    new.red_run_retries = 0

    # Reset alignment_iterations when restarting at stage 2
    if target_stage == "2":
        new.alignment_iterations = 0

    return new


def version_document(
    state: PipelineState,
    document_path: str,
    companion_paths: Optional[List[str]] = None,
) -> PipelineState:
    """Copy document (and optional companions) to versioned history location."""
    new = _copy_state(state)

    # Determine base directory and history directory from document_path
    base_dir = os.path.dirname(document_path)
    history_dir = os.path.join(base_dir, "history") if base_dir else "history"
    os.makedirs(history_dir, exist_ok=True)

    # Determine the next version number by inspecting existing history files
    filename = os.path.basename(document_path)
    version = 1
    # Scan history directory for existing versions of this file
    if os.path.isdir(history_dir):
        for entry in os.listdir(history_dir):
            # Pattern: {filename}.v{N}
            prefix = filename + ".v"
            if entry.startswith(prefix):
                try:
                    n = int(entry[len(prefix) :])
                    if n >= version:
                        version = n + 1
                except ValueError:
                    pass

    # Copy main document
    dest = os.path.join(history_dir, f"{filename}.v{version}")
    if os.path.isfile(document_path):
        shutil.copy2(document_path, dest)

    # Copy companions with same version number
    companions = companion_paths or []
    for comp_path in companions:
        comp_filename = os.path.basename(comp_path)
        comp_dest = os.path.join(history_dir, f"{comp_filename}.v{version}")
        if os.path.isfile(comp_path):
            shutil.copy2(comp_path, comp_dest)

    # Update pass_history
    record: Dict[str, Any] = {
        "version": version,
        "document": document_path,
        "companions": companions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    new.pass_history.append(record)

    return new


def enter_debug_session(state: PipelineState, bug_number: int) -> PipelineState:
    """Enter a new debug session."""
    if state.debug_session is not None:
        raise TransitionError("A debug session is already active")

    new = _copy_state(state)
    new.debug_session = {
        "authorized": False,
        "bug_number": bug_number,
        "classification": None,
        "affected_units": [],
        "phase": "triage",
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    return new


def authorize_debug_session(state: PipelineState) -> PipelineState:
    """Authorize the current debug session."""
    if state.debug_session is None:
        raise TransitionError("No debug session to authorize")
    if state.debug_session.get("authorized") is not False:
        raise TransitionError("Debug session is already authorized")

    new = _copy_state(state)
    new.debug_session["authorized"] = True
    return new


def complete_debug_session(state: PipelineState) -> PipelineState:
    """Complete and archive the current debug session."""
    if state.debug_session is None:
        raise TransitionError("No debug session to complete")
    if not state.debug_session.get("authorized"):
        raise TransitionError("Debug session is not authorized; cannot complete")

    new = _copy_state(state)
    new.debug_history.append(new.debug_session)
    new.debug_session = None
    return new


def abandon_debug_session(state: PipelineState) -> PipelineState:
    """Abandon the current debug session, marking it as abandoned."""
    if state.debug_session is None:
        raise TransitionError("No debug session to abandon")

    new = _copy_state(state)
    session = dict(new.debug_session)
    session["abandoned"] = True
    new.debug_history.append(session)
    new.debug_session = None
    return new


def update_debug_phase(state: PipelineState, phase: str) -> PipelineState:
    """Update the debug session phase."""
    if phase not in VALID_DEBUG_PHASES:
        raise TransitionError(
            f"Invalid debug phase: {phase!r}. "
            f"Must be one of {sorted(VALID_DEBUG_PHASES)}"
        )
    if state.debug_session is None:
        raise TransitionError("No debug session active")

    new = _copy_state(state)
    new.debug_session["phase"] = phase
    return new


def set_debug_classification(
    state: PipelineState,
    classification: str,
    affected_units: List[int],
) -> PipelineState:
    """Set the classification and affected units for the current debug session."""
    valid_classifications = {"build_env", "single_unit", "cross_unit"}
    if classification not in valid_classifications:
        raise TransitionError(
            f"Invalid classification: {classification!r}. "
            f"Must be one of {sorted(valid_classifications)}"
        )
    if state.debug_session is None:
        raise TransitionError("No debug session active")

    new = _copy_state(state)
    new.debug_session["classification"] = classification
    new.debug_session["affected_units"] = affected_units
    return new


def enter_redo_profile_revision(
    state: PipelineState,
    redo_type: str,
) -> PipelineState:
    """Enter a redo profile revision, snapshotting current state."""
    valid_redo_types = {"delivery", "blueprint"}
    if redo_type not in valid_redo_types:
        raise TransitionError(
            f"Invalid redo_type: {redo_type!r}. "
            f"Must be one of {sorted(valid_redo_types)}"
        )

    new = _copy_state(state)

    # Snapshot current state (before modifications)
    new.redo_triggered_from = {
        "stage": state.stage,
        "sub_stage": state.sub_stage,
        "current_unit": state.current_unit,
    }

    # Set sub_stage based on redo_type
    if redo_type == "delivery":
        new.sub_stage = "redo_profile_delivery"
    else:
        new.sub_stage = "redo_profile_blueprint"

    return new


def complete_redo_profile_revision(state: PipelineState) -> PipelineState:
    """Complete redo profile revision, restoring state from snapshot."""
    if state.redo_triggered_from is None:
        raise TransitionError("No redo_triggered_from snapshot; cannot complete redo")

    new = _copy_state(state)

    # Restore state fields from snapshot
    snapshot = new.redo_triggered_from
    new.stage = snapshot.get("stage", new.stage)
    new.sub_stage = snapshot.get("sub_stage", new.sub_stage)
    new.current_unit = snapshot.get("current_unit", new.current_unit)

    # Clear the snapshot
    new.redo_triggered_from = None

    return new


def enter_alignment_check(state: PipelineState) -> PipelineState:
    """Set sub_stage to 'alignment_check'."""
    new = _copy_state(state)
    new.sub_stage = "alignment_check"
    return new


def complete_alignment_check(
    state: PipelineState,
    result: str,
) -> PipelineState:
    """Complete alignment check with the given result."""
    valid_results = {"confirmed", "spec", "blueprint"}
    if result not in valid_results:
        raise TransitionError(
            f"Invalid alignment check result: {result!r}. "
            f"Must be one of {sorted(valid_results)}"
        )

    new = _copy_state(state)

    if result == "confirmed":
        new.sub_stage = "alignment_confirmed"
    elif result == "blueprint":
        new.sub_stage = "blueprint_dialog"
        new.alignment_iterations += 1
    elif result == "spec":
        new.sub_stage = "targeted_spec_revision"

    return new


def enter_quality_gate(
    state: PipelineState,
    gate_id: str,
) -> PipelineState:
    """Enter a quality gate by setting sub_stage to *gate_id*."""
    new = _copy_state(state)
    new.sub_stage = gate_id
    return new


def advance_quality_gate_to_retry(state: PipelineState) -> PipelineState:
    """Advance quality gate to its retry variant."""
    sub = state.sub_stage
    if sub == "quality_gate_a":
        target = "quality_gate_a_retry"
    elif sub == "quality_gate_b":
        target = "quality_gate_b_retry"
    else:
        raise TransitionError(
            f"Cannot advance to retry from sub_stage {sub!r}; "
            f"expected 'quality_gate_a' or 'quality_gate_b'"
        )

    new = _copy_state(state)
    new.sub_stage = target
    return new


def quality_gate_pass(state: PipelineState) -> PipelineState:
    """Quality gate passed; advance to next sub-stage after gate."""
    sub = state.sub_stage
    if sub in ("quality_gate_a", "quality_gate_a_retry"):
        target = "red_run"
    elif sub in ("quality_gate_b", "quality_gate_b_retry"):
        target = "green_run"
    else:
        raise TransitionError(f"Cannot pass quality gate from sub_stage {sub!r}")

    new = _copy_state(state)
    new.sub_stage = target
    return new


def quality_gate_fail_to_ladder(state: PipelineState) -> PipelineState:
    """Quality gate failed; enter fix ladder from current position."""
    new = _copy_state(state)
    # Enter fix ladder -- advance from current fix_ladder_position
    new = advance_fix_ladder(new)
    return new


def set_delivered_repo_path(state: PipelineState, path: str) -> PipelineState:
    """Set the delivered repository path."""
    new = _copy_state(state)
    new.delivered_repo_path = path
    return new


def enter_pass_1(state: PipelineState) -> PipelineState:
    """Enter pass 1 for E/F archetype self-builds."""
    new = _copy_state(state)
    new.pass_ = 1
    return new


def enter_pass_2(state: PipelineState, nested_session_path: str) -> PipelineState:
    """Enter pass 2."""
    if state.pass_ != 1:
        raise TransitionError(
            f"Cannot enter pass 2: pass_ must be 1, got {state.pass_!r}"
        )

    new = _copy_state(state)
    new.pass_ = 2
    new.pass2_nested_session_path = nested_session_path
    return new


def clear_pass(state: PipelineState) -> PipelineState:
    """Clear pass state."""
    new = _copy_state(state)
    new.pass_ = None
    new.pass2_nested_session_path = None
    return new


def mark_unit_deferred_broken(state: PipelineState, unit_number: int) -> PipelineState:
    """Mark a unit as deferred/broken (no duplicates)."""
    new = _copy_state(state)
    if unit_number not in new.deferred_broken_units:
        new.deferred_broken_units.append(unit_number)
    return new


def resolve_deferred_broken(state: PipelineState, unit_number: int) -> PipelineState:
    """Resolve a deferred/broken unit."""
    if unit_number not in state.deferred_broken_units:
        raise TransitionError(f"Unit {unit_number} is not in deferred_broken_units")

    new = _copy_state(state)
    new.deferred_broken_units.remove(unit_number)
    return new


# ---------------------------------------------------------------------------
# Oracle session transitions (Bug S3-63)
# ---------------------------------------------------------------------------


def enter_oracle_session(state: PipelineState, test_project: str) -> PipelineState:
    """Enter an oracle session for pipeline acceptance testing.

    Precondition: oracle_session_active is False.
    Postcondition: oracle_session_active=True, oracle_phase="dry_run",
                   oracle_test_project=test_project, oracle_run_count incremented.
    """
    if state.oracle_session_active:
        raise TransitionError("Cannot enter oracle session: session already active")
    new = _copy_state(state)
    new.oracle_session_active = True
    new.oracle_phase = "dry_run"
    new.oracle_test_project = test_project
    new.oracle_run_count = (state.oracle_run_count or 0) + 1
    new.oracle_modification_count = 0
    return new


def complete_oracle_session(state: PipelineState, exit_reason: str) -> PipelineState:
    """Complete an oracle session normally.

    Precondition: oracle_session_active is True.
    Postcondition: oracle_session_active=False, oracle_phase=None,
                   oracle_test_project=None, oracle_nested_session_path=None,
                   debug_session=None (Bug S3-94).
    """
    if not state.oracle_session_active:
        raise TransitionError("Cannot complete oracle session: no active session")
    new = _copy_state(state)
    new.oracle_session_active = False
    new.oracle_phase = None
    new.oracle_test_project = None
    new.oracle_nested_session_path = None
    if new.debug_session is not None:
        session = dict(new.debug_session)
        session["abandoned"] = True
        new.debug_history.append(session)
        new.debug_session = None
    return new


def abandon_oracle_session(state: PipelineState) -> PipelineState:
    """Abandon an oracle session (human abort).

    Precondition: oracle_session_active is True.
    Postcondition: oracle_session_active=False, oracle_phase=None,
                   oracle_test_project=None, oracle_nested_session_path=None,
                   debug_session=None (Bug S3-94).
    """
    if not state.oracle_session_active:
        raise TransitionError("Cannot abandon oracle session: no active session")
    new = _copy_state(state)
    new.oracle_session_active = False
    new.oracle_phase = None
    new.oracle_test_project = None
    new.oracle_nested_session_path = None
    if new.debug_session is not None:
        session = dict(new.debug_session)
        session["abandoned"] = True
        new.debug_history.append(session)
        new.debug_session = None
    return new
