# Unit 2: Pipeline State Schema and Core Operations
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import os
import tempfile
from datetime import datetime, timezone

from svp_config import ARTIFACT_FILENAMES

STAGES: List[str] = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

SUB_STAGES_STAGE_0: List[str] = ["hook_activation", "project_context", "project_profile"]

# Stage 1 sub-stages: spec authoring cycle
STAGE_1_SUB_STAGES: List[Optional[str]] = [None]

# Stage 2 sub-stages (Bug 23 fix -- NEW IN 2.1)
# blueprint_dialog: blueprint authoring and review cycle (default)
# alignment_check: blueprint checker verifying spec-blueprint alignment
STAGE_2_SUB_STAGES: List[Optional[str]] = [None, "blueprint_dialog", "alignment_check"]

# Stage 3 sub-stages: unit build cycle phases
STAGE_3_SUB_STAGES: List[Optional[str]] = [
    None,                    # default: no sub-stage (unit entry)
    "test_generation",       # test agent is generating tests
    "quality_gate_a",        # quality gate A running on tests
    "quality_gate_a_retry",  # agent fixing quality gate A residuals
    "red_run",               # tests running against stub (expect failure)
    "implementation",        # implementation agent is implementing
    "quality_gate_b",        # quality gate B running on implementation
    "quality_gate_b_retry",  # agent fixing quality gate B residuals
    "green_run",             # tests running against implementation (expect pass)
    "coverage_review",       # coverage review agent checking gaps
    "unit_completion",       # unit verified, about to advance
]

# Stage 4 sub-stages: integration testing phase
STAGE_4_SUB_STAGES: List[Optional[str]] = [None]

# Stage 5 sub-stages: repo assembly phase
STAGE_5_SUB_STAGES: List[Optional[str]] = [
    None,
    "repo_test",
    "compliance_scan",
    "repo_complete",
]

# Quality gate sub-stages (subset of STAGE_3_SUB_STAGES, NEW IN 2.1)
QUALITY_GATE_SUB_STAGES: List[str] = [
    "quality_gate_a", "quality_gate_b",
    "quality_gate_a_retry", "quality_gate_b_retry",
]

# Redo-triggered profile revision sub-stages (can appear in any stage)
REDO_PROFILE_SUB_STAGES: List[str] = ["redo_profile_delivery", "redo_profile_blueprint"]

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
            created_at=data.get("created_at", ""),
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
    redo_triggered_from: Optional[Dict[str, Any]]
    delivered_repo_path: Optional[str]  # absolute path to delivered repo (NEW IN 2.1)
    created_at: str
    updated_at: str

    def __init__(self, **kwargs: Any) -> None:
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
        self.redo_triggered_from = kwargs.get("redo_triggered_from", None)
        self.delivered_repo_path = kwargs.get("delivered_repo_path", None)
        now = datetime.now(timezone.utc).isoformat()
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
            "verified_units": list(self.verified_units),
            "pass_history": list(self.pass_history),
            "log_references": dict(self.log_references),
            "project_name": self.project_name,
            "last_action": self.last_action,
            "debug_session": (self.debug_session.to_dict() if isinstance(self.debug_session, DebugSession) else self.debug_session) if self.debug_session is not None else None,
            "debug_history": list(self.debug_history),
            "redo_triggered_from": dict(self.redo_triggered_from) if self.redo_triggered_from is not None else None,
            "delivered_repo_path": self.delivered_repo_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState":
        debug_session = None
        if data.get("debug_session") is not None:
            debug_session = DebugSession.from_dict(data["debug_session"])

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
            redo_triggered_from=data.get("redo_triggered_from", None),
            delivered_repo_path=data.get("delivered_repo_path", None),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


def create_initial_state(project_name: str) -> PipelineState:
    """Create and return a fresh PipelineState at Stage 0, hook_activation."""
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
        redo_triggered_from=None,
        delivered_repo_path=None,
        created_at=now,
        updated_at=now,
    )


def load_state(project_root: Path) -> PipelineState:
    """Deserialize pipeline_state.json and return a validated PipelineState."""
    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"State file not found at {state_path}")

    text = state_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise json.JSONDecodeError("State file is not valid JSON", text, 0)

    state = PipelineState.from_dict(data)

    errors = validate_state(state)
    if errors:
        raise ValueError(f"Invalid state: {'; '.join(errors)}")

    return state


def save_state(state: PipelineState, project_root: Path) -> None:
    """Atomically write the state to pipeline_state.json."""
    state.updated_at = datetime.now().isoformat()
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
        os.replace(tmp_path, str(state_path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def validate_state(state: PipelineState) -> list[str]:
    """Check structural integrity of a PipelineState. Returns list of error strings."""
    errors: list[str] = []

    # Valid stage
    if state.stage not in STAGES:
        errors.append(f"Invalid stage: {state.stage}")

    # Valid sub_stage for the stage
    if state.sub_stage is not None:
        # Redo profile sub-stages can appear in any stage
        if state.sub_stage in REDO_PROFILE_SUB_STAGES:
            pass  # valid in any stage
        elif state.stage == "0":
            if state.sub_stage not in SUB_STAGES_STAGE_0:
                errors.append(f"Invalid sub_stage '{state.sub_stage}' for stage 0")
        elif state.stage == "2":
            if state.sub_stage not in STAGE_2_SUB_STAGES:
                errors.append(f"Invalid sub_stage '{state.sub_stage}' for stage 2")
        elif state.stage == "3":
            if state.sub_stage not in STAGE_3_SUB_STAGES:
                errors.append(f"Invalid sub_stage '{state.sub_stage}' for stage 3")

    # Non-negative counters
    if state.red_run_retries < 0:
        errors.append("red_run_retries must be non-negative")
    if state.alignment_iteration < 0:
        errors.append("alignment_iteration must be non-negative")

    # fix_ladder_position must be valid
    if state.fix_ladder_position is not None and state.fix_ladder_position not in FIX_LADDER_POSITIONS:
        errors.append(f"Invalid fix_ladder_position: {state.fix_ladder_position}")

    # verified_units entries must have required fields
    for i, vu in enumerate(state.verified_units):
        if "unit" not in vu:
            errors.append(f"verified_units[{i}] missing 'unit' field")
        if "timestamp" not in vu:
            errors.append(f"verified_units[{i}] missing 'timestamp' field")

    # pass_history entries must have required fields
    for i, ph in enumerate(state.pass_history):
        if "pass_number" not in ph:
            errors.append(f"pass_history[{i}] missing 'pass_number' field")
        if "reached_unit" not in ph:
            errors.append(f"pass_history[{i}] missing 'reached_unit' field")
        if "ended_reason" not in ph:
            errors.append(f"pass_history[{i}] missing 'ended_reason' field")
        if "timestamp" not in ph:
            errors.append(f"pass_history[{i}] missing 'timestamp' field")

    # debug_session must be None or a valid DebugSession with required fields
    if state.debug_session is not None:
        if not isinstance(state.debug_session, DebugSession):
            errors.append("debug_session must be a DebugSession instance or None")
        else:
            ds = state.debug_session
            if not ds.description:
                errors.append("debug_session missing 'description'")
            if ds.classification is None:
                errors.append("debug_session missing 'classification'")
            if not ds.affected_units:
                errors.append("debug_session missing 'affected_units'")

    # debug_history entries have required fields
    debug_history_required = ["bug_id", "resolution"]
    for i, dh in enumerate(state.debug_history):
        for field in debug_history_required:
            if field not in dh:
                errors.append(f"debug_history[{i}] missing '{field}' field")

    # redo_triggered_from validation
    if state.redo_triggered_from is not None:
        required_redo_keys = ["stage", "sub_stage", "current_unit", "fix_ladder_position", "red_run_retries"]
        for key in required_redo_keys:
            if key not in state.redo_triggered_from:
                errors.append(f"redo_triggered_from missing '{key}' field")

    # delivered_repo_path validation: None or non-empty string
    if state.delivered_repo_path is not None:
        if not isinstance(state.delivered_repo_path, str) or state.delivered_repo_path == "":
            errors.append("delivered_repo_path must be None or a non-empty string")

    return errors


def recover_state_from_markers(project_root: Path) -> Optional[PipelineState]:
    """Scan for completion markers and construct the most conservative valid state."""
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project root not found: {project_root}")
    markers_found = False

    # Check for spec approval marker
    spec_approved = False
    spec_path = project_root / "specs" / ARTIFACT_FILENAMES["stakeholder_spec"]
    if spec_path.exists():
        content = spec_path.read_text(encoding="utf-8")
        if "<!-- SVP_APPROVED:" in content:
            spec_approved = True
            markers_found = True

    # Check for blueprint approval marker
    blueprint_approved = False
    blueprint_path = project_root / "blueprint" / ARTIFACT_FILENAMES["blueprint"]
    if blueprint_path.exists():
        content = blueprint_path.read_text(encoding="utf-8")
        if "<!-- SVP_APPROVED:" in content:
            blueprint_approved = True
            markers_found = True

    # Check for unit verification markers
    verified_units: List[Dict[str, Any]] = []
    markers_dir = project_root / ".svp" / "markers"
    if markers_dir.exists():
        for item in sorted(markers_dir.iterdir()):
            name = item.name
            if name.startswith("unit_") and name.endswith("_verified"):
                try:
                    unit_num = int(name.replace("unit_", "").replace("_verified", ""))
                    verified_units.append({
                        "unit": unit_num,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    markers_found = True
                except ValueError:
                    continue

    if not markers_found:
        return None

    # Construct the most conservative valid state
    now = datetime.now(timezone.utc).isoformat()

    if verified_units:
        # We have verified units, so we're in Stage 3
        max_unit = max(vu["unit"] for vu in verified_units)
        total_units = max_unit  # conservative: at least this many
        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=max_unit + 1,
            total_units=total_units,
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
            redo_triggered_from=None,
            created_at=now,
            updated_at=now,
        )
    elif blueprint_approved:
        # Blueprint is approved, so we're at pre_stage_3
        state = PipelineState(
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
            redo_triggered_from=None,
            created_at=now,
            updated_at=now,
        )
    elif spec_approved:
        # Spec is approved, so we're at Stage 2
        state = PipelineState(
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
            redo_triggered_from=None,
            created_at=now,
            updated_at=now,
        )
    else:
        return None

    return state


def get_stage_display(state: PipelineState) -> str:
    """Return a human-readable string describing the current pipeline position."""
    stage_names: Dict[str, str] = {
        "0": "Stage 0",
        "1": "Stage 1",
        "2": "Stage 2",
        "pre_stage_3": "Pre-Stage 3",
        "3": "Stage 3",
        "4": "Stage 4",
        "5": "Stage 5",
    }

    display = stage_names.get(state.stage, f"Stage {state.stage}")

    if state.stage == "3" and state.current_unit is not None and state.total_units is not None:
        display += f", Unit {state.current_unit} of {state.total_units}"
        # Add pass number if there's pass history
        if state.pass_history:
            pass_number = len(state.pass_history) + 1
            display += f" (pass {pass_number})"

    if state.stage == "0" and state.sub_stage is not None:
        display += f" ({state.sub_stage})"

    if state.sub_stage in REDO_PROFILE_SUB_STAGES:
        display += f" [{state.sub_stage}]"

    if state.fix_ladder_position is not None:
        display += f" [fix: {state.fix_ladder_position}]"

    return display
