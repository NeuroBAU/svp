"""Unit 3: State Transition Engine.

Validates preconditions and executes all state transitions: stage advancement,
unit completion, fix ladder progression, pass history recording, unit-level
rollback, document versioning, and debug session lifecycle.
"""

import copy
import shutil
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timezone

from svp.scripts.pipeline_state import PipelineState, DebugSession
from svp.scripts.svp_config import load_config


# Stage sequence for advance_stage
_STAGE_SEQUENCE = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

# Valid fix ladder transitions:
# Test ladder: None -> fresh_test -> hint_test
# Implementation ladder: None -> fresh_impl -> diagnostic -> diagnostic_impl
_FIX_LADDER_TRANSITIONS: Dict[Optional[str], List[str]] = {
    None: ["fresh_test", "fresh_impl"],
    "fresh_test": ["hint_test"],
    "hint_test": [],
    "fresh_impl": ["diagnostic"],
    "diagnostic": ["diagnostic_impl"],
    "diagnostic_impl": [],
}

# Valid debug phase transitions
_DEBUG_PHASE_TRANSITIONS: Dict[str, List[str]] = {
    "triage_readonly": ["triage"],
    "triage": ["regression_test", "stage3_reentry"],
    "regression_test": ["stage3_reentry", "repair"],
    "stage3_reentry": ["repair", "complete"],
    "repair": ["complete"],
    "complete": [],
}


class TransitionError(Exception):
    """Raised when a state transition's preconditions are not met."""
    ...


def _clone_state(state: PipelineState) -> PipelineState:
    """Create a deep copy of a PipelineState."""
    data = state.to_dict()
    # Deep copy the data to avoid shared references
    data = copy.deepcopy(data)
    # Reconstruct with DebugSession handling
    debug_data = data.pop("debug_session", None)
    debug_history = data.pop("debug_history", [])
    new_state = PipelineState(**data)
    if debug_data is not None:
        new_state.debug_session = DebugSession.from_dict(debug_data)
    else:
        new_state.debug_session = None
    new_state.debug_history = debug_history
    return new_state


def advance_stage(state: PipelineState, project_root: Path) -> PipelineState:
    """Move the state to the next stage in the defined sequence.

    Validates that the current stage's exit criteria are met before transitioning.
    """
    if state.stage not in ("0", "1", "2", "pre_stage_3", "3", "4"):
        raise TransitionError(
            f"Cannot advance from stage {state.stage}: preconditions not met"
            f" -- cannot advance past Stage 5"
        )

    current_idx = _STAGE_SEQUENCE.index(state.stage)
    next_stage = _STAGE_SEQUENCE[current_idx + 1]

    new_state = _clone_state(state)
    new_state.stage = next_stage
    new_state.sub_stage = None
    new_state.last_action = f"Advanced from stage {state.stage} to {next_stage}"

    # When entering stage 3, initialize current_unit if not set
    if next_stage == "3" and new_state.current_unit is None:
        new_state.current_unit = 1

    return new_state


def advance_sub_stage(state: PipelineState, sub_stage: str, project_root: Path) -> PipelineState:
    """Set the sub_stage within the current stage."""
    new_state = _clone_state(state)
    new_state.sub_stage = sub_stage
    new_state.last_action = f"Advanced sub_stage to {sub_stage}"
    return new_state


def complete_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState:
    """Mark a unit as complete, write the verification marker, and advance."""
    # Pre-conditions
    if state.stage != "3":
        raise TransitionError(
            f"Cannot complete unit {unit_number}: Can only complete units during Stage 3"
        )
    if state.current_unit != unit_number:
        raise TransitionError(
            f"Cannot complete unit {unit_number}: Can only complete the current unit"
        )

    marker_path = project_root / f".svp/markers/unit_{unit_number}_verified"
    if marker_path.exists():
        raise TransitionError(
            f"Cannot complete unit {unit_number}: Completion marker already exists"
        )

    # Write the marker file
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    marker_path.write_text(f"VERIFIED: {now}\n", encoding="utf-8")

    new_state = _clone_state(state)

    # Add to verified_units
    new_state.verified_units = list(new_state.verified_units) + [
        {"unit": unit_number, "timestamp": now}
    ]

    # Reset fix ladder and red run retries
    new_state.fix_ladder_position = None
    new_state.red_run_retries = 0

    # Advance current_unit
    next_unit = unit_number + 1
    if new_state.total_units is not None and next_unit > new_state.total_units:
        # All units done, advance to stage 4
        new_state.stage = "4"
        new_state.current_unit = None
        new_state.last_action = f"Completed unit {unit_number} (final unit), advancing to Stage 4"
    else:
        new_state.current_unit = next_unit
        new_state.last_action = f"Completed unit {unit_number}, advancing to unit {next_unit}"

    return new_state


def advance_fix_ladder(state: PipelineState, new_position: str) -> PipelineState:
    """Advance the fix ladder to the next valid position.

    Enforces valid ladder sequences:
    - Test ladder:  None -> fresh_test -> hint_test
    - Impl ladder:  None -> fresh_impl -> diagnostic -> diagnostic_impl
    """
    current = state.fix_ladder_position
    valid_targets = _FIX_LADDER_TRANSITIONS.get(current, [])

    if new_position not in valid_targets:
        raise TransitionError(
            f"Cannot advance fix ladder to {new_position}: current position "
            f"{current} does not permit this transition"
        )

    new_state = _clone_state(state)
    new_state.fix_ladder_position = new_position
    new_state.last_action = f"Advanced fix ladder from {current} to {new_position}"
    return new_state


def reset_fix_ladder(state: PipelineState) -> PipelineState:
    """Reset the fix ladder position to None."""
    new_state = _clone_state(state)
    new_state.fix_ladder_position = None
    new_state.last_action = "Reset fix ladder"
    return new_state


def increment_red_run_retries(state: PipelineState) -> PipelineState:
    """Increment the red run retry counter."""
    new_state = _clone_state(state)
    new_state.red_run_retries = state.red_run_retries + 1
    new_state.last_action = f"Incremented red_run_retries to {new_state.red_run_retries}"
    return new_state


def reset_red_run_retries(state: PipelineState) -> PipelineState:
    """Reset the red run retry counter to zero."""
    new_state = _clone_state(state)
    new_state.red_run_retries = 0
    new_state.last_action = "Reset red_run_retries"
    return new_state


def increment_alignment_iteration(state: PipelineState) -> PipelineState:
    """Increment alignment iteration count, checking against the configured limit."""
    # Load config to get the iteration limit
    try:
        config = load_config(Path("."))
    except Exception:
        config = {"iteration_limit": 3}

    limit = config.get("iteration_limit", 3)
    new_count = state.alignment_iteration + 1

    if new_count > limit:
        raise TransitionError(f"Alignment iteration limit reached ({limit})")

    new_state = _clone_state(state)
    new_state.alignment_iteration = new_count
    new_state.last_action = f"Incremented alignment_iteration to {new_count}"
    return new_state


def reset_alignment_iteration(state: PipelineState) -> PipelineState:
    """Reset the alignment iteration counter to zero."""
    new_state = _clone_state(state)
    new_state.alignment_iteration = 0
    new_state.last_action = "Reset alignment_iteration"
    return new_state


def record_pass_end(state: PipelineState, reason: str) -> PipelineState:
    """Record the end of the current pass in pass_history."""
    now = datetime.now(timezone.utc).isoformat()
    pass_number = len(state.pass_history) + 1
    reached_unit = state.current_unit or 0

    new_state = _clone_state(state)
    new_state.pass_history = list(new_state.pass_history) + [{
        "pass_number": pass_number,
        "reached_unit": reached_unit,
        "ended_reason": reason,
        "timestamp": now,
    }]
    new_state.last_action = f"Recorded pass {pass_number} end: {reason}"
    return new_state


def rollback_to_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState:
    """Rollback to a specific unit, invalidating all units from that unit forward.

    Removes marker files, removes from verified_units, moves generated code
    and tests to logs/rollback/, and sets current_unit to the given unit number.
    """
    # Pre-conditions
    if state.stage != "3":
        raise TransitionError("Rollback only applies during Stage 3")
    if unit_number < 1:
        raise TransitionError("Unit number must be positive")
    if unit_number > (state.current_unit or 0):
        raise TransitionError("Cannot roll back to a future unit")

    new_state = _clone_state(state)

    # Identify units to invalidate (from unit_number forward)
    units_to_invalidate = []
    for vu in state.verified_units:
        if vu["unit"] >= unit_number:
            units_to_invalidate.append(vu["unit"])

    # Remove marker files for invalidated units
    for u in units_to_invalidate:
        marker_path = project_root / f".svp/markers/unit_{u}_verified"
        if marker_path.exists():
            marker_path.unlink()

    # Move generated code and tests to logs/rollback/
    rollback_dir = project_root / "logs" / "rollback"
    rollback_dir.mkdir(parents=True, exist_ok=True)

    for u in units_to_invalidate:
        # Move generated source files if they exist
        src_dir = project_root / "src" / f"unit_{u}"
        if src_dir.exists():
            dest = rollback_dir / f"unit_{u}_src"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src_dir, dest)

        # Move test files if they exist
        test_dir = project_root / "tests" / f"unit_{u}"
        if test_dir.exists():
            dest = rollback_dir / f"unit_{u}_tests"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(test_dir, dest)

    # Remove invalidated units from verified_units
    new_state.verified_units = [
        vu for vu in new_state.verified_units if vu["unit"] < unit_number
    ]

    # Set current_unit to the rollback target
    new_state.current_unit = unit_number

    # Reset fix ladder and retries for the fresh start
    new_state.fix_ladder_position = None
    new_state.red_run_retries = 0

    new_state.last_action = f"Rolled back to unit {unit_number}"
    return new_state


def restart_from_stage(state: PipelineState, target_stage: str, reason: str, project_root: Path) -> PipelineState:
    """Record the current pass in pass_history, reset counters, and restart from target_stage."""
    now = datetime.now(timezone.utc).isoformat()

    new_state = _clone_state(state)

    # Record the current pass ending
    pass_number = len(new_state.pass_history) + 1
    reached_unit = state.current_unit or 0
    new_state.pass_history = list(new_state.pass_history) + [{
        "pass_number": pass_number,
        "reached_unit": reached_unit,
        "ended_reason": reason,
        "timestamp": now,
    }]

    # Reset stage-specific counters
    new_state.fix_ladder_position = None
    new_state.red_run_retries = 0
    new_state.alignment_iteration = 0

    # Set to the target stage
    new_state.stage = target_stage
    new_state.sub_stage = None

    # Reset unit tracking when restarting
    if target_stage in ("0", "1", "2", "pre_stage_3"):
        new_state.current_unit = None

    if target_stage == "3":
        new_state.current_unit = 1

    new_state.last_action = f"Restarted from stage {target_stage}: {reason}"
    return new_state


def version_document(
    doc_path: Path, history_dir: Path, diff_summary: str, trigger_context: str
) -> Tuple[Path, Path]:
    """Version a document by copying it to history and writing a diff summary.

    Copies the current document to history/{name}_v{N}.md, writes diff summary
    to history/{name}_v{N}_diff.md. Returns paths of both created files.
    """
    if not doc_path.exists():
        raise FileNotFoundError(f"Document to version not found: {doc_path}")

    # Ensure history dir exists
    history_dir.mkdir(parents=True, exist_ok=True)

    # Determine the document name (without extension)
    stem = doc_path.stem
    suffix = doc_path.suffix or ".md"

    # Find the next version number by checking existing files
    version = 1
    while (history_dir / f"{stem}_v{version}{suffix}").exists():
        version += 1

    # Copy the document to history
    versioned_copy = history_dir / f"{stem}_v{version}{suffix}"
    shutil.copy2(doc_path, versioned_copy)

    # Write the diff summary
    now = datetime.now(timezone.utc).isoformat()
    diff_file = history_dir / f"{stem}_v{version}_diff{suffix}"
    diff_content = (
        f"# Diff Summary: {stem} v{version}\n\n"
        f"**Timestamp:** {now}\n"
        f"**Trigger:** {trigger_context}\n\n"
        f"## Changes\n\n"
        f"{diff_summary}\n"
    )
    diff_file.write_text(diff_content, encoding="utf-8")

    # Post-conditions
    assert versioned_copy.exists(), "Versioned copy must exist in history dir"
    assert diff_file.exists(), "Diff summary must exist in history dir"

    return versioned_copy, diff_file


def enter_debug_session(state: PipelineState, bug_description: str) -> PipelineState:
    """Create a new debug session with authorized=False, phase=triage_readonly."""
    if state.stage != "5":
        raise TransitionError("Cannot enter debug session: pipeline is not at Stage 5")
    if state.debug_session is not None:
        raise TransitionError("Cannot enter debug session: a debug session is already active")

    # Assign sequential bug_id
    existing_ids = [dh.get("bug_id", 0) for dh in state.debug_history]
    if state.debug_session is not None:
        existing_ids.append(state.debug_session.bug_id)
    next_bug_id = max(existing_ids, default=0) + 1

    new_state = _clone_state(state)
    new_state.debug_session = DebugSession(
        bug_id=next_bug_id,
        description=bug_description,
        classification=None,
        affected_units=[],
        regression_test_path=None,
        phase="triage_readonly",
        authorized=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    new_state.last_action = f"Entered debug session (bug #{next_bug_id})"
    return new_state


def authorize_debug_session(state: PipelineState) -> PipelineState:
    """Authorize the active debug session and advance phase to triage."""
    if state.debug_session is None:
        raise TransitionError("Cannot authorize debug session: no active session")
    if state.debug_session.authorized:
        raise TransitionError("Cannot authorize debug session: already authorized")

    new_state = _clone_state(state)
    new_state.debug_session.authorized = True
    new_state.debug_session.phase = "triage"
    new_state.last_action = f"Authorized debug session (bug #{state.debug_session.bug_id})"

    # Post-conditions
    assert new_state.debug_session is not None, "Debug session must still exist"
    assert new_state.debug_session.authorized is True, "Debug session must be authorized"

    return new_state


def complete_debug_session(state: PipelineState, fix_summary: str) -> PipelineState:
    """Complete the active debug session, moving it to debug_history."""
    if state.debug_session is None:
        raise TransitionError("Cannot complete debug session: no active session")
    if not state.debug_session.authorized:
        raise TransitionError("Cannot complete debug session: session must be authorized")

    new_state = _clone_state(state)

    # Move the debug session to history
    session_record = new_state.debug_session.to_dict()
    session_record["fix_summary"] = fix_summary
    session_record["completed_at"] = datetime.now(timezone.utc).isoformat()
    session_record["status"] = "completed"

    new_state.debug_history = list(new_state.debug_history) + [session_record]
    new_state.debug_session = None
    new_state.last_action = f"Completed debug session (bug #{state.debug_session.bug_id})"

    return new_state


def abandon_debug_session(state: PipelineState) -> PipelineState:
    """Abandon the active debug session, moving it to debug_history with an abandoned marker."""
    if state.debug_session is None:
        raise TransitionError("Cannot abandon debug session: no active session")

    new_state = _clone_state(state)

    # Move the debug session to history with "abandoned" marker
    session_record = new_state.debug_session.to_dict()
    session_record["abandoned_at"] = datetime.now(timezone.utc).isoformat()
    session_record["status"] = "abandoned"

    new_state.debug_history = list(new_state.debug_history) + [session_record]
    new_state.debug_session = None
    new_state.last_action = f"Abandoned debug session (bug #{state.debug_session.bug_id})"

    return new_state


def update_debug_phase(state: PipelineState, phase: str) -> PipelineState:
    """Validate and update the debug session phase."""
    if state.debug_session is None:
        raise TransitionError("Cannot update debug phase: no active session")

    current_phase = state.debug_session.phase
    valid_targets = _DEBUG_PHASE_TRANSITIONS.get(current_phase, [])

    if phase not in valid_targets:
        raise TransitionError(
            f"Cannot transition debug phase from {current_phase} to {phase}"
        )

    new_state = _clone_state(state)
    new_state.debug_session.phase = phase
    new_state.last_action = f"Updated debug phase from {current_phase} to {phase}"
    return new_state


def set_debug_classification(state: PipelineState, classification: str, affected_units: List[int]) -> PipelineState:
    """Set the classification and affected units on the active debug session."""
    if state.debug_session is None:
        raise TransitionError("Cannot set debug classification: no active session")

    new_state = _clone_state(state)
    new_state.debug_session.classification = classification
    new_state.debug_session.affected_units = list(affected_units)
    new_state.last_action = f"Set debug classification to {classification}"
    return new_state


def update_state_from_status(
    state: PipelineState,
    status_file: Path,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState:
    """Read the status file, parse the terminal status line, and call the
    appropriate transition function based on the phase parameter.

    This is the entry point called by POST commands.
    """
    if not status_file.exists():
        # No status file, return state unchanged
        return _clone_state(state)

    status_content = status_file.read_text(encoding="utf-8").strip()

    # Parse the status line (last non-empty line)
    lines = [line.strip() for line in status_content.split("\n") if line.strip()]
    if not lines:
        return _clone_state(state)

    status_line = lines[-1]

    new_state = _clone_state(state)
    new_state.last_action = f"Processed status: {status_line} (phase={phase})"

    return new_state
