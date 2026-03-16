# Unit 2: Pipeline State Schema and Core Operations
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import os
import tempfile
from datetime import datetime, timezone

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
    "stub_generation",       # stub generation phase
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

# Map stage to valid sub-stages for validation
_STAGE_SUB_STAGES: Dict[str, List[Optional[str]]] = {
    "0": [None] + SUB_STAGES_STAGE_0,  # type: ignore[list-item]
    "1": STAGE_1_SUB_STAGES,
    "2": STAGE_2_SUB_STAGES,
    "pre_stage_3": [None],
    "3": STAGE_3_SUB_STAGES,
    "4": STAGE_4_SUB_STAGES,
    "5": STAGE_5_SUB_STAGES,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DebugSession:
    """Debug session state for post-delivery bug investigation."""
    bug_id: int
    description: str
    classification: Optional[str]  # "build_env", "single_unit", "cross_unit"
    affected_units: List[int]
    regression_test_path: Optional[str]
    phase: str  # "triage_readonly", "triage", "regression_test", "stage3_reentry", "repair", "complete"
    authorized: bool  # True after AUTHORIZE DEBUG at Gate 6.0
    triage_refinement_count: int
    repair_retry_count: int
    created_at: str

    def __init__(self, **kwargs: Any) -> None:
        self.bug_id = kwargs.get("bug_id", 0)
        self.description = kwargs.get("description", "")
        self.classification = kwargs.get("classification", None)
        self.affected_units = kwargs.get("affected_units", [])
        self.regression_test_path = kwargs.get("regression_test_path", None)
        self.phase = kwargs.get("phase", "triage")
        self.authorized = kwargs.get("authorized", False)
        self.triage_refinement_count = kwargs.get("triage_refinement_count", 0)
        self.repair_retry_count = kwargs.get("repair_retry_count", 0)
        self.created_at = kwargs.get("created_at", _now_iso())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "description": self.description,
            "classification": self.classification,
            "affected_units": list(self.affected_units),
            "regression_test_path": self.regression_test_path,
            "phase": self.phase,
            "authorized": self.authorized,
            "triage_refinement_count": self.triage_refinement_count,
            "repair_retry_count": self.repair_retry_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugSession":
        return cls(**data)


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
        ds = kwargs.get("debug_session", None)
        if isinstance(ds, dict):
            self.debug_session = DebugSession.from_dict(ds)
        else:
            self.debug_session = ds
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


def validate_state(
    state: PipelineState,
) -> list[str]:
    errors: list[str] = []

    # Check valid stage
    if state.stage not in STAGES:
        errors.append(f"Invalid stage: {state.stage}")
        return errors

    # Check valid sub_stage for the stage
    valid_subs = _STAGE_SUB_STAGES.get(state.stage, [None])
    # Also allow redo profile sub-stages for any stage
    all_valid = list(valid_subs) + list(REDO_PROFILE_SUB_STAGES)
    if state.sub_stage not in all_valid:
        errors.append(
            f"Invalid sub_stage '{state.sub_stage}' for stage '{state.stage}'"
        )

    # Non-negative counters
    if state.red_run_retries < 0:
        errors.append("red_run_retries must be non-negative")
    if state.alignment_iteration < 0:
        errors.append("alignment_iteration must be non-negative")

    # fix_ladder_position validity
    if (
        state.fix_ladder_position is not None
        and state.fix_ladder_position not in FIX_LADDER_POSITIONS
    ):
        errors.append(f"Invalid fix_ladder_position: {state.fix_ladder_position}")

    # delivered_repo_path must be None or non-empty str
    if state.delivered_repo_path is not None:
        if not isinstance(state.delivered_repo_path, str):
            errors.append(
                "delivered_repo_path must be None or str"
            )
        elif state.delivered_repo_path == "":
            errors.append(
                "delivered_repo_path must not be empty"
            )

    return errors


def recover_state_from_markers(
    project_root: Path,
) -> Optional[PipelineState]:
    """Scan for completion markers and construct
    the most conservative valid state."""
    # Look for verified unit markers
    svp_dir = project_root / ".svp"
    if not svp_dir.exists():
        return None

    verified: List[Dict[str, Any]] = []
    markers_dir = svp_dir / "markers"
    if markers_dir.exists():
        for marker_file in sorted(markers_dir.glob("unit_*_complete.json")):
            try:
                data = json.loads(marker_file.read_text(encoding="utf-8"))
                verified.append(data)
            except (
                json.JSONDecodeError,
                OSError,
            ):
                continue

    if not verified:
        # No markers found; return initial state
        state_file = project_root / "pipeline_state.json"
        if state_file.exists():
            try:
                return load_state(project_root)
            except (ValueError, json.JSONDecodeError):
                pass
        return None

    # Construct conservative state from markers
    max_unit = max(v.get("unit", 0) for v in verified)
    state = PipelineState(
        stage="3",
        sub_stage=None,
        current_unit=max_unit + 1,
        verified_units=verified,
    )
    return state


def get_stage_display(state: PipelineState) -> str:
    """Return a human-readable display of the
    current pipeline position."""
    parts: list[str] = []
    parts.append(f"Stage {state.stage}")

    if state.sub_stage is not None:
        parts.append(f"({state.sub_stage})")

    if state.current_unit is not None:
        unit_str = f"Unit {state.current_unit}"
        if state.total_units is not None:
            unit_str += f"/{state.total_units}"
        parts.append(unit_str)

    if state.fix_ladder_position is not None:
        parts.append(f"[fix: {state.fix_ladder_position}]")

    return " ".join(parts)
