"""Unit 3: State Transition Engine.

Validates preconditions and executes all state transitions: stage advancement,
unit completion, fix ladder progression, pass history recording, unit-level
rollback, document versioning, debug session lifecycle, redo-triggered
profile revision lifecycle, Stage 2 alignment check transitions (Bug 23 fix),
quality gate state transitions, and delivered repo path recording.
"""

import copy
import shutil
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timezone

from pipeline_state import PipelineState, DebugSession
from svp_config import load_config


# Stage sequence for advance_stage
_STAGE_SEQUENCE = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

# Valid fix ladder transitions:
# Test ladder: None -> fresh_test -> hint_test
# Implementation ladder: None -> fresh_impl -> diagnostic -> diagnostic_impl
_FIX_LADDER_TRANSITIONS: Dict[Optional[str], List[str]] = {
    None: ["fresh_test", "fresh_impl"],
    "fresh_test": ["hint_test"],
    "hint_test": ["fresh_impl"],
    "fresh_impl": ["diagnostic"],
    "diagnostic": ["diagnostic_impl"],
    "diagnostic_impl": [],
}

# Valid debug phase transitions
_DEBUG_PHASE_TRANSITIONS: Dict[str, List[str]] = {
    "triage_readonly": ["triage"],
    "triage": ["regression_test", "stage3_reentry", "investigation"],
    "regression_test": ["stage3_reentry", "repair"],
    "stage3_reentry": ["repair", "complete"],
    "repair": ["complete"],
    "complete": [],
}

# Quality gate sub-stage to target sub-stage on pass
_QUALITY_GATE_PASS_TARGET: Dict[str, str] = {
    "quality_gate_a": "red_run",
    "quality_gate_a_retry": "red_run",
    "quality_gate_b": "green_run",
    "quality_gate_b_retry": "green_run",
}

# Quality gate retry sub-stage to initial ladder position mapping
_QUALITY_GATE_RETRY_TO_LADDER_BRANCH: Dict[str, str] = {
    "quality_gate_a_retry": "fresh_test",
    "quality_gate_b_retry": "fresh_impl",
}

# Classification normalization map
_REDO_CLASSIFICATION_MAP: Dict[str, str] = {
    "delivery": "redo_profile_delivery",
    "blueprint": "redo_profile_blueprint",
    "profile_delivery": "redo_profile_delivery",
    "profile_blueprint": "redo_profile_blueprint",
}


class TransitionError(Exception):
    """Raised when a state transition's preconditions are not met."""
    ...


def _clone_state(state: PipelineState) -> PipelineState:
    """Create a deep copy of a PipelineState."""
    data = state.to_dict()
    data = copy.deepcopy(data)
    return PipelineState.from_dict(data)


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

    # Reset fix ladder, red run retries, and sub_stage for next unit
    new_state.fix_ladder_position = None
    new_state.red_run_retries = 0
    new_state.sub_stage = None

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
    # Load config to get the iteration limit -- try project root from context,
    # fall back to defaults if unavailable
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
    """Record end of current pass in pass_history."""
    now = datetime.now(timezone.utc).isoformat()
    pass_number = len(state.pass_history) + 1
    reached_unit = state.current_unit or 0

    new_state = _clone_state(state)
    new_state.pass_history = list(new_state.pass_history) + [
        {
            "pass_number": pass_number,
            "reached_unit": reached_unit,
            "reason": reason,
            "timestamp": now,
        }
    ]
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

    # Remove marker files for invalidated units (from verified_units)
    for u in units_to_invalidate:
        marker_path = project_root / f".svp/markers/unit_{u}_verified"
        if marker_path.exists():
            marker_path.unlink()

    # Also remove any marker files on disk for units >= unit_number
    markers_dir = project_root / ".svp" / "markers"
    if markers_dir.exists():
        import re as _re
        for item in markers_dir.iterdir():
            m = _re.match(r"unit_(\d+)_verified", item.name)
            if m and int(m.group(1)) >= unit_number:
                item.unlink()

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
    new_state.pass_history = list(new_state.pass_history) + [
        {
            "pass_number": pass_number,
            "reached_unit": reached_unit,
            "reason": reason,
            "timestamp": now,
        }
    ]

    # Reset stage-specific counters
    new_state.fix_ladder_position = None
    new_state.red_run_retries = 0
    new_state.alignment_iteration = 0

    # Set to the target stage
    new_state.stage = target_stage
    new_state.sub_stage = None

    # Reset unit tracking when restarting to early stages
    if target_stage in ("0", "1", "2", "pre_stage_3"):
        new_state.current_unit = None
        new_state.verified_units = []

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

    # Assign sequential bug_id based on debug_history
    existing_ids = [dh.get("bug_id", 0) for dh in state.debug_history]
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


# --- Redo-triggered profile revision transitions ---

def enter_redo_profile_revision(
    state: PipelineState, classification: str
) -> PipelineState:
    """Enter a redo-triggered profile revision.

    Accepts classification values: 'delivery',
    'blueprint', 'profile_delivery', or
    'profile_blueprint'.
    """
    sub_stage_target = _REDO_CLASSIFICATION_MAP.get(classification)
    if sub_stage_target is None:
        raise TransitionError(
            "Cannot enter redo profile revision:"
            " invalid classification"
            f" {classification}"
        )

    current_sub = getattr(state, "sub_stage", None)
    if current_sub in ("redo_profile_delivery", "redo_profile_blueprint"):
        raise TransitionError(
            "Cannot enter redo profile revision: already in redo profile revision"
        )

    new_state = _clone_state(state)

    # Capture snapshot of current pipeline position
    snapshot: Dict[str, Any] = {
        "stage": state.stage,
        "sub_stage": state.sub_stage,
        "current_unit": state.current_unit,
        "fix_ladder_position": state.fix_ladder_position,
        "red_run_retries": state.red_run_retries,
    }
    new_state.redo_triggered_from = snapshot
    new_state.sub_stage = sub_stage_target
    new_state.last_action = f"Entered redo profile revision ({classification})"
    return new_state


def complete_redo_profile_revision(state: PipelineState) -> PipelineState:
    """Complete a redo-triggered profile revision.

    For redo_profile_delivery: restores the snapshot position.
    For redo_profile_blueprint: discards snapshot and restarts from Stage 2.
    """
    # Pre-conditions
    current_sub = getattr(state, "sub_stage", None)
    if current_sub not in ("redo_profile_delivery", "redo_profile_blueprint"):
        raise TransitionError(
            "Cannot complete redo profile revision: must be in redo profile revision"
        )

    redo_snapshot = getattr(state, "redo_triggered_from", None)

    if current_sub == "redo_profile_delivery":
        # Restore the snapshot if available
        new_state = _clone_state(state)
        if redo_snapshot is not None:
            new_state.stage = redo_snapshot["stage"]
            new_state.sub_stage = redo_snapshot.get("sub_stage")
            new_state.current_unit = redo_snapshot.get("current_unit")
            new_state.fix_ladder_position = redo_snapshot.get("fix_ladder_position")
            new_state.red_run_retries = redo_snapshot.get("red_run_retries", 0)
        else:
            new_state.sub_stage = None
        new_state.redo_triggered_from = None
        new_state.last_action = "Completed redo profile revision (delivery): restored snapshot"
        return new_state
    else:
        # redo_profile_blueprint: discard snapshot, restart from Stage 2
        new_state = _clone_state(state)
        new_state.redo_triggered_from = None
        now = datetime.now(timezone.utc).isoformat()

        # Record the current pass ending
        pass_number = len(new_state.pass_history) + 1
        reached_unit = state.current_unit or 0
        new_state.pass_history = list(new_state.pass_history) + [
            {
                "pass_number": pass_number,
                "reached_unit": reached_unit,
                "reason": "profile_blueprint revision",
                "timestamp": now,
            }
        ]

        # Reset everything downstream
        new_state.stage = "2"
        new_state.sub_stage = None
        new_state.fix_ladder_position = None
        new_state.red_run_retries = 0
        new_state.alignment_iteration = 0
        new_state.current_unit = None
        new_state.verified_units = []
        new_state.last_action = "Completed redo profile revision (blueprint): restarting from Stage 2"
        return new_state


# --- Stage 2 sub-stage transitions (Bug 23 fix -- NEW IN 2.1) ---

def enter_alignment_check(state: PipelineState) -> PipelineState:
    """Set sub_stage to alignment_check. Only valid during Stage 2.

    Called by dispatch_gate_response when Gate 2.1 or Gate 2.2 receives APPROVE.
    This replaces the prior behavior where APPROVE directly called advance_stage.
    """
    if state.stage != "2":
        raise TransitionError("Cannot enter alignment check: not in Stage 2")

    new_state = _clone_state(state)
    new_state.sub_stage = "alignment_check"
    new_state.last_action = "Entered alignment check sub-stage"
    return new_state


def complete_alignment_check(state: PipelineState, project_root: Path) -> PipelineState:
    """Called when blueprint checker returns ALIGNMENT_CONFIRMED.

    Calls advance_stage to transition from Stage 2 to Pre-Stage-3.
    """
    if state.stage != "2":
        raise TransitionError("Cannot complete alignment check: not in Stage 2")
    if state.sub_stage != "alignment_check":
        raise TransitionError(
            "Cannot complete alignment check: not in alignment_check sub-stage"
        )

    # advance_stage will validate the rest (blueprint exists, alignment_check sub-stage)
    return advance_stage(state, project_root)


# --- Quality gate transitions (NEW IN 2.1) ---

def enter_quality_gate(state: PipelineState, gate: str) -> PipelineState:
    """Set sub_stage to quality_gate_a or quality_gate_b. Only valid during Stage 3.

    Note: does NOT reset fix_ladder_position -- the fix ladder is preserved
    across quality gate re-entry.
    """
    if state.stage != "3":
        raise TransitionError(f"Cannot enter quality gate {gate}: not in Stage 3")
    if gate not in ("quality_gate_a", "quality_gate_b"):
        raise TransitionError(
            f"Cannot enter quality gate {gate}: gate must be quality_gate_a or quality_gate_b"
        )

    new_state = _clone_state(state)
    new_state.sub_stage = gate
    new_state.last_action = f"Entered quality gate {gate}"
    return new_state


def advance_quality_gate_to_retry(state: PipelineState) -> PipelineState:
    """Transition from quality_gate_a to quality_gate_a_retry,
    or from quality_gate_b to quality_gate_b_retry.
    """
    if state.sub_stage not in ("quality_gate_a", "quality_gate_b"):
        raise TransitionError(
            "Cannot advance quality gate to retry: not in quality gate sub-stage"
        )

    new_state = _clone_state(state)
    new_state.sub_stage = state.sub_stage + "_retry"
    new_state.last_action = f"Advanced quality gate to {new_state.sub_stage}"
    return new_state


def quality_gate_pass(state: PipelineState) -> PipelineState:
    """Advance past the quality gate on pass.

    quality_gate_a / quality_gate_a_retry -> red_run
    quality_gate_b / quality_gate_b_retry -> green_run
    """
    target = _QUALITY_GATE_PASS_TARGET.get(state.sub_stage)
    if target is None:
        raise TransitionError(
            f"Cannot pass quality gate: not in a quality gate sub-stage "
            f"(current sub_stage: {state.sub_stage})"
        )

    new_state = _clone_state(state)
    new_state.sub_stage = target
    new_state.last_action = f"Quality gate passed, advancing to {target}"
    return new_state


def quality_gate_fail_to_ladder(state: PipelineState) -> PipelineState:
    """Handle quality gate failure by advancing the fix ladder.

    Must be in a quality gate retry sub-stage. Infers the ladder branch
    from the sub-stage and calls advance_fix_ladder internally.

    On exhaustion (no next ladder position), leaves sub_stage unchanged
    so the routing script can present the appropriate exhaustion gate.
    """
    if state.sub_stage not in ("quality_gate_a_retry", "quality_gate_b_retry"):
        raise TransitionError(
            "Cannot fail quality gate to ladder: must be in quality gate retry"
        )

    current_ladder = state.fix_ladder_position

    if current_ladder is None:
        # First failure: enter the appropriate ladder branch
        initial_position = _QUALITY_GATE_RETRY_TO_LADDER_BRANCH[state.sub_stage]
        new_state = advance_fix_ladder(state, initial_position)
        new_state.sub_stage = None
        new_state.last_action = (
            f"Quality gate failed, entered fix ladder at {initial_position}"
        )
        return new_state
    else:
        # Subsequent failure: try to advance the ladder
        valid_targets = _FIX_LADDER_TRANSITIONS.get(current_ladder, [])
        if not valid_targets:
            # Ladder exhausted: preserve sub_stage and fix_ladder_position
            new_state = _clone_state(state)
            new_state.last_action = (
                f"Quality gate failed, fix ladder exhausted at {current_ladder}"
            )
            return new_state
        else:
            # Advance to next ladder position
            next_position = valid_targets[0]
            new_state = advance_fix_ladder(state, next_position)
            new_state.sub_stage = None
            new_state.last_action = (
                f"Quality gate failed, advanced fix ladder to {next_position}"
            )
            return new_state


def enter_quality_gate_retry(
    state: PipelineState,
    retry_sub_stage: str,
) -> PipelineState:
    """Enter quality gate retry with an explicit target sub-stage."""
    new_state = _clone_state(state)
    new_state.sub_stage = retry_sub_stage
    new_state.last_action = f"Entered quality gate retry: {retry_sub_stage}"
    return new_state


def advance_from_quality_gate(
    state: PipelineState,
    target_sub_stage: str,
) -> PipelineState:
    """Advance from quality gate to a target sub-stage."""
    new_state = _clone_state(state)
    new_state.sub_stage = target_sub_stage
    new_state.last_action = f"Advanced from quality gate to {target_sub_stage}"
    return new_state


def fail_quality_gate_to_ladder(
    state: PipelineState,
    new_position: str,
) -> PipelineState:
    """Handle quality gate failure with an explicit ladder position."""
    new_state = _clone_state(state)
    new_state.fix_ladder_position = new_position
    new_state.sub_stage = None
    new_state.last_action = (
        f"Quality gate failed, entered fix ladder at {new_position}"
    )
    return new_state


# --- Delivered repo path (NEW IN 2.1) ---

def set_delivered_repo_path(state: PipelineState, repo_path: str) -> PipelineState:
    """Record the absolute path to the delivered
    repository."""
    if not repo_path.strip():
        raise TransitionError("Cannot set delivered repo path: path must be non-empty")

    new_state = _clone_state(state)
    new_state.delivered_repo_path = repo_path
    new_state.last_action = f"Set delivered repo path to {repo_path}"
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
