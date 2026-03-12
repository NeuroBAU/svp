"""Pipeline State Schema and Core Operations.

Defines the complete pipeline_state.json schema and provides creation,
reading, writing, structural validation, and state recovery from
completion markers.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import os
import tempfile
import re
from datetime import datetime, timezone

# --- Data contract: pipeline state schema ---

STAGES: List[str] = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

SUB_STAGES_STAGE_0: List[str] = ["hook_activation", "project_context"]

FIX_LADDER_POSITIONS: List[Optional[str]] = [
    None, "fresh_test", "hint_test",
    "fresh_impl", "diagnostic", "diagnostic_impl",
]


class DebugSession:
    """Debug session state for post-delivery bug investigation."""
    bug_id: int
    description: str
    classification: Optional[str]  # "build_env", "single_unit", "cross_unit"
    affected_units: List[int]
    regression_test_path: Optional[str]
    phase: str  # "triage_readonly", "triage", "regression_test", "stage3_reentry", "repair", "complete"
    authorized: bool  # True after AUTHORIZE DEBUG at Gate 6.0
    created_at: str

    def __init__(self, **kwargs: Any) -> None:
        self.bug_id = kwargs.get("bug_id", 0)
        self.description = kwargs.get("description", "")
        self.classification = kwargs.get("classification", None)
        self.affected_units = kwargs.get("affected_units", [])
        self.regression_test_path = kwargs.get("regression_test_path", None)
        self.phase = kwargs.get("phase", "triage_readonly")
        self.authorized = kwargs.get("authorized", False)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "description": self.description,
            "classification": self.classification,
            "affected_units": list(self.affected_units),
            "regression_test_path": self.regression_test_path,
            "phase": self.phase,
            "authorized": self.authorized,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugSession":
        return cls(
            bug_id=data.get("bug_id", 0),
            description=data.get("description", ""),
            classification=data.get("classification", None),
            affected_units=data.get("affected_units", []),
            regression_test_path=data.get("regression_test_path", None),
            phase=data.get("phase", "triage_readonly"),
            authorized=data.get("authorized", False),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class PipelineState:
    """Complete pipeline state. This is the schema contract."""
    stage: str
    sub_stage: Optional[str]
    current_unit: Optional[int]
    total_units: Optional[int]
    fix_ladder_position: Optional[str]
    red_run_retries: int
    alignment_iteration: int
    verified_units: List[Dict[str, Any]]
    pass_history: List[Dict[str, Any]]
    log_references: Dict[str, str]
    project_name: Optional[str]
    last_action: Optional[str]
    debug_session: Optional[DebugSession]
    debug_history: List[Dict[str, Any]]
    created_at: str
    updated_at: str

    def __init__(self, **kwargs: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.stage = kwargs.get("stage", "0")
        self.sub_stage = kwargs.get("sub_stage", None)
        self.current_unit = kwargs.get("current_unit", None)
        self.total_units = kwargs.get("total_units", None)
        self.fix_ladder_position = kwargs.get("fix_ladder_position", None)
        self.red_run_retries = kwargs.get("red_run_retries", 0)
        self.alignment_iteration = kwargs.get("alignment_iteration", 0)
        self.verified_units = kwargs.get("verified_units", [])
        self.pass_history = kwargs.get("pass_history", [])
        self.log_references = kwargs.get("log_references", {})
        self.project_name = kwargs.get("project_name", None)
        self.last_action = kwargs.get("last_action", None)
        self.debug_session = kwargs.get("debug_session", None)
        self.debug_history = kwargs.get("debug_history", [])
        self.created_at = kwargs.get("created_at", now)
        self.updated_at = kwargs.get("updated_at", now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "sub_stage": self.sub_stage,
            "current_unit": self.current_unit,
            "total_units": self.total_units,
            "fix_ladder_position": self.fix_ladder_position,
            "red_run_retries": self.red_run_retries,
            "alignment_iteration": self.alignment_iteration,
            "verified_units": [dict(v) for v in self.verified_units],
            "pass_history": [dict(p) for p in self.pass_history],
            "log_references": dict(self.log_references),
            "project_name": self.project_name,
            "last_action": self.last_action,
            "debug_session": self.debug_session.to_dict() if self.debug_session is not None else None,
            "debug_history": [dict(d) for d in self.debug_history],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState":
        debug_session_data = data.get("debug_session", None)
        debug_session = None
        if debug_session_data is not None:
            debug_session = DebugSession.from_dict(debug_session_data)

        return cls(
            stage=data.get("stage", "0"),
            sub_stage=data.get("sub_stage", None),
            current_unit=data.get("current_unit", None),
            total_units=data.get("total_units", None),
            fix_ladder_position=data.get("fix_ladder_position", None),
            red_run_retries=data.get("red_run_retries", 0),
            alignment_iteration=data.get("alignment_iteration", 0),
            verified_units=data.get("verified_units", []),
            pass_history=data.get("pass_history", []),
            log_references=data.get("log_references", {}),
            project_name=data.get("project_name", None),
            last_action=data.get("last_action", None),
            debug_session=debug_session,
            debug_history=data.get("debug_history", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


def create_initial_state(project_name: str) -> PipelineState:
    """Create a fresh PipelineState at stage 0, sub_stage hook_activation."""
    now = datetime.now(timezone.utc).isoformat()
    return PipelineState(
        stage="0",
        sub_stage="hook_activation",
        current_unit=None,
        total_units=None,
        fix_ladder_position=None,
        red_run_retries=0,
        alignment_iteration=0,
        verified_units=[],
        pass_history=[],
        log_references={},
        project_name=project_name,
        last_action=None,
        debug_session=None,
        debug_history=[],
        created_at=now,
        updated_at=now,
    )


def load_state(project_root: Path) -> PipelineState:
    """Load and validate pipeline state from pipeline_state.json.

    Raises FileNotFoundError if the file does not exist.
    Raises json.JSONDecodeError if the file is not valid JSON.
    Raises ValueError if the state fails structural validation.
    """
    assert project_root.is_dir(), "Project root must exist"

    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"State file not found at {state_path}")

    raw_text = state_path.read_text(encoding="utf-8")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        raise

    state = PipelineState.from_dict(data)

    errors = validate_state(state)
    if errors:
        raise ValueError(f"Invalid state: {'; '.join(errors)}")

    return state


def save_state(state: PipelineState, project_root: Path) -> None:
    """Atomically write the pipeline state to pipeline_state.json.

    Uses write-to-temp-then-rename for atomicity.
    Updates the updated_at timestamp before writing.
    """
    assert project_root.is_dir(), "Project root must exist"

    # Update the timestamp on every save
    state.updated_at = datetime.now(timezone.utc).isoformat()

    state_path = project_root / "pipeline_state.json"
    data = state.to_dict()
    content = json.dumps(data, indent=2) + "\n"

    # Atomic write: write to temp file in same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(project_root),
        prefix=".pipeline_state_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # Atomic rename on POSIX; best-effort on Windows
        os.replace(tmp_path, str(state_path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    assert state_path.exists(), "State file must exist after save"


def validate_state(state: PipelineState) -> list[str]:
    """Validate structural integrity of a PipelineState.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []

    # Valid stage
    if state.stage not in STAGES:
        errors.append(f"Invalid stage: {state.stage}")

    # Valid sub_stage for the current stage
    if state.stage == "0" and state.sub_stage is not None:
        if state.sub_stage not in SUB_STAGES_STAGE_0:
            errors.append(f"Invalid sub_stage for stage 0: {state.sub_stage}")

    # Valid fix_ladder_position
    if state.fix_ladder_position is not None:
        if state.fix_ladder_position not in FIX_LADDER_POSITIONS:
            errors.append(f"Invalid fix_ladder_position: {state.fix_ladder_position}")

    # Non-negative counters
    if state.red_run_retries < 0:
        errors.append("red_run_retries must be non-negative")
    if state.alignment_iteration < 0:
        errors.append("alignment_iteration must be non-negative")

    # verified_units entries have required fields
    for i, vu in enumerate(state.verified_units):
        if "unit" not in vu:
            errors.append(f"verified_units[{i}] missing required field: unit")
        if "timestamp" not in vu:
            errors.append(f"verified_units[{i}] missing required field: timestamp")

    # pass_history entries have required fields
    for i, ph in enumerate(state.pass_history):
        if "pass_number" not in ph:
            errors.append(f"pass_history[{i}] missing required field: pass_number")
        if "reached_unit" not in ph:
            errors.append(f"pass_history[{i}] missing required field: reached_unit")
        if "ended_reason" not in ph:
            errors.append(f"pass_history[{i}] missing required field: ended_reason")
        if "timestamp" not in ph:
            errors.append(f"pass_history[{i}] missing required field: timestamp")

    # debug_session is either None or a valid DebugSession
    if state.debug_session is not None:
        if not isinstance(state.debug_session, DebugSession):
            errors.append("debug_session must be a DebugSession instance or None")
        else:
            valid_classifications = [None, "build_env", "single_unit", "cross_unit"]
            if state.debug_session.classification not in valid_classifications:
                errors.append(f"debug_session.classification is invalid: {state.debug_session.classification}")
            valid_phases = [
                "triage_readonly", "triage", "regression_test",
                "stage3_reentry", "repair", "complete",
            ]
            if state.debug_session.phase not in valid_phases:
                errors.append(f"debug_session.phase is invalid: {state.debug_session.phase}")

    # debug_history entries have required fields
    for i, dh in enumerate(state.debug_history):
        if "bug_id" not in dh:
            errors.append(f"debug_history[{i}] missing required field: bug_id")

    return errors


def recover_state_from_markers(project_root: Path) -> Optional[PipelineState]:
    """Recover pipeline state from completion markers.

    Scans for:
    - <!-- SVP_APPROVED: ... --> in specs/stakeholder.md (indicates Stage 1 complete)
    - <!-- SVP_APPROVED: ... --> in blueprint/blueprint.md (indicates Stage 2 complete)
    - .svp/markers/unit_N_verified files (indicates units verified in Stage 3)

    Returns the most conservative valid state consistent with the markers found,
    or None if no markers are found at all.
    """
    assert project_root.is_dir(), "Project root must exist"

    stakeholder_approved = False
    blueprint_approved = False
    verified_unit_numbers: List[int] = []

    # Check stakeholder.md for SVP_APPROVED marker
    stakeholder_path = project_root / "specs" / "stakeholder.md"
    if stakeholder_path.exists():
        try:
            content = stakeholder_path.read_text(encoding="utf-8")
            if "<!-- SVP_APPROVED:" in content:
                stakeholder_approved = True
        except (OSError, UnicodeDecodeError):
            pass

    # Check blueprint.md for SVP_APPROVED marker
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        try:
            content = blueprint_path.read_text(encoding="utf-8")
            if "<!-- SVP_APPROVED:" in content:
                blueprint_approved = True
        except (OSError, UnicodeDecodeError):
            pass

    # Check for unit verified markers
    markers_dir = project_root / ".svp" / "markers"
    if markers_dir.exists() and markers_dir.is_dir():
        for entry in markers_dir.iterdir():
            match = re.match(r"unit_(\d+)_verified", entry.name)
            if match:
                verified_unit_numbers.append(int(match.group(1)))

    verified_unit_numbers.sort()

    # No markers at all -- return None
    if not stakeholder_approved and not blueprint_approved and not verified_unit_numbers:
        return None

    # Determine the most conservative state from the markers
    now = datetime.now(timezone.utc).isoformat()

    # Build verified_units list
    verified_units: List[Dict[str, Any]] = []
    for unit_num in verified_unit_numbers:
        verified_units.append({
            "unit": unit_num,
            "timestamp": now,
        })

    if verified_unit_numbers:
        # Units have been verified -> we are in Stage 3
        # The next unit to work on is the one after the highest verified
        max_verified = max(verified_unit_numbers)
        next_unit = max_verified + 1
        return PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=next_unit,
            total_units=None,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=verified_units,
            pass_history=[],
            log_references={},
            project_name=None,
            last_action="Recovered from markers",
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
    elif blueprint_approved:
        # Blueprint approved but no units verified -> pre_stage_3 or stage 3 unit 1
        return PipelineState(
            stage="pre_stage_3",
            sub_stage=None,
            current_unit=None,
            total_units=None,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name=None,
            last_action="Recovered from markers",
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
    elif stakeholder_approved:
        # Stakeholder approved but blueprint not -> Stage 2
        return PipelineState(
            stage="2",
            sub_stage=None,
            current_unit=None,
            total_units=None,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name=None,
            last_action="Recovered from markers",
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )

    # Should not reach here given the early None return, but be safe
    return None


def get_stage_display(state: PipelineState) -> str:
    """Return a human-readable string describing the current pipeline stage.

    Examples:
    - "Stage 0 (hook_activation)"
    - "Stage 3, Unit 4 of 11 (pass 2)"
    - "Stage 5"
    """
    stage = state.stage

    if stage == "pre_stage_3":
        return "Pre-Stage 3"

    stage_label = f"Stage {stage}"

    parts = [stage_label]

    # Add sub_stage info for stage 0
    if stage == "0" and state.sub_stage is not None:
        parts.append(f"({state.sub_stage})")
        return " ".join(parts)

    # Add unit info for stage 3
    if stage == "3" and state.current_unit is not None:
        unit_part = f"Unit {state.current_unit}"
        if state.total_units is not None:
            unit_part += f" of {state.total_units}"
        parts.append(unit_part)

        # Add pass number
        pass_number = len(state.pass_history) + 1
        parts_str = ", ".join(parts)
        return f"{parts_str} (pass {pass_number})"

    return stage_label
