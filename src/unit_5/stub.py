"""Unit 5: Pipeline State -- full implementation."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.unit_1.stub import ARTIFACT_FILENAMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STAGES: Set[str] = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}

VALID_SUB_STAGES: Dict[str, Set[Optional[str]]] = {
    "0": {
        "hook_activation",
        "project_context",
        "project_profile",
        "toolchain_provisioning",
    },
    "1": {None, "checklist_generation"},
    "2": {"blueprint_dialog", "alignment_check", "alignment_confirmed"},
    "pre_stage_3": {None, "dep_diff", "dep_diff_install"},
    "3": {
        None,
        "stub_generation",
        "test_generation",
        "quality_gate_a",
        "quality_gate_a_retry",
        "red_run",
        "implementation",
        "quality_gate_b",
        "quality_gate_b_retry",
        "green_run",
        "coverage_review",
        "unit_completion",
    },
    "4": {None, "regression_adaptation", "gate_4_1", "gate_4_1a", "gate_4_2"},
    "5": {None, "repo_test", "compliance_scan", "repo_complete", "gate_5_2", "gate_5_3"},
}

VALID_FIX_LADDER_POSITIONS: List[Optional[str]] = [
    None,
    "fresh_impl",
    "diagnostic",
    "diagnostic_impl",
    "exhausted",
]

VALID_DEBUG_PHASES: Set[str] = {
    "triage",
    "repair",
    "regression_test",
    "lessons_learned",
    "reassembly",
    "stage3_reentry",
    "stage3_rebuild_active",
    "commit",
}

VALID_ORACLE_PHASES: Set[Optional[str]] = {
    None,
    "dry_run",
    "gate_a",
    "green_run",
    "gate_b",
    "exit",
}


# ---------------------------------------------------------------------------
# PipelineState dataclass
# ---------------------------------------------------------------------------


@dataclass
class PipelineState:
    """Represents the full mutable state of the SVP pipeline."""

    stage: str = "0"
    sub_stage: Optional[str] = None
    current_unit: Optional[int] = None
    total_units: int = 0
    verified_units: List[Dict[str, Any]] = field(default_factory=list)
    alignment_iterations: int = 0
    fix_ladder_position: Optional[str] = None
    red_run_retries: int = 0
    # Bug S3-149: bounds the Stage 5 repo-assembly retry loop. Incremented
    # by dispatch_gate_response::gate_5_1_repo_test on TESTS FAILED; reset
    # to 0 by gate_5_2_assembly_exhausted on RETRY ASSEMBLY. At the
    # iteration_limit (default 3) the dispatch transitions to gate_5_2.
    assembly_retries: int = 0
    pass_history: List[Dict[str, Any]] = field(default_factory=list)
    debug_session: Optional[Dict[str, Any]] = None
    debug_history: List[Dict[str, Any]] = field(default_factory=list)
    redo_triggered_from: Optional[Dict[str, Any]] = None
    delivered_repo_path: Optional[str] = None
    primary_language: str = "python"
    component_languages: List[str] = field(default_factory=list)
    secondary_language: Optional[str] = None
    oracle_session_active: bool = False
    oracle_test_project: Optional[str] = None
    oracle_phase: Optional[str] = None
    oracle_run_count: int = 0
    oracle_nested_session_path: Optional[str] = None
    oracle_modification_count: int = 0
    state_hash: Optional[str] = None
    spec_revision_count: int = 0
    pass_: Optional[int] = None  # serialized as "pass" in JSON
    pass2_nested_session_path: Optional[str] = None
    deferred_broken_units: List[int] = field(default_factory=list)
    # Bug S3-160: tracks env readiness after infrastructure_setup runs
    # verify_toolchain_ready (Unit 4). Values: "READY" | "NOT_READY".
    toolchain_status: str = "NOT_READY"
    # Bug S3-164: project-level capability flag (mirrors profile field of the
    # same name). When True, Stage 1 stakeholder dialog, Stage 2 blueprint
    # author, Stage 2 reviewer dispatch, and Stage 3 test agent are primed
    # for statistical / data-analysis rigor. Default False keeps the pipeline
    # lean for non-statistical projects. gate_0_3_profile_approval syncs the
    # value from project_profile.json into this field.
    requires_statistical_analysis: bool = False
    # Bug S3-168: per-blueprint-review-iteration flag tracking whether the
    # STATISTICAL_CORRECTNESS_REVIEWER specialist has emitted REVIEW_COMPLETE
    # for the current blueprint iteration. Set True by dispatch_agent_status
    # when the specialist emits REVIEW_COMPLETE; reset False on gate_2_2
    # REVISE / FRESH REVIEW outcomes (next iteration repeats both reviewers).
    # Used by _route_stage_2 blueprint_review to decide whether to dispatch
    # the specialist after blueprint_reviewer completes. With flag=False
    # baseline (state.requires_statistical_analysis=False), routing flow is
    # byte-identical to pre-S3-168 behavior.
    statistical_review_done: bool = False


# ---------------------------------------------------------------------------
# Field defaults for missing SVP 2.2 fields during load
# ---------------------------------------------------------------------------

_SVP22_FIELD_DEFAULTS: Dict[str, Any] = {
    "primary_language": "python",
    "component_languages": [],
    "secondary_language": None,
    "oracle_session_active": False,
    "oracle_test_project": None,
    "oracle_phase": None,
    "oracle_run_count": 0,
    "oracle_nested_session_path": None,
    "oracle_modification_count": 0,
    "state_hash": None,
    "spec_revision_count": 0,
    "pass": None,
    "pass2_nested_session_path": None,
    "deferred_broken_units": [],
    "toolchain_status": "NOT_READY",
    "requires_statistical_analysis": False,
    "statistical_review_done": False,
}


# ---------------------------------------------------------------------------
# Centralized accessor for the requires_statistical_analysis flag (S3-164)
# ---------------------------------------------------------------------------


def _requires_statistical_analysis(state: PipelineState) -> bool:
    """Centralized read of the requires_statistical_analysis flag.

    Single source of truth for routing and prepare_task helpers that branch
    on whether the project requires statistical / data-analysis support.
    """
    return getattr(state, "requires_statistical_analysis", False)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_state(project_root: Path) -> PipelineState:
    """Load pipeline state from pipeline_state.json in *project_root*.

    Raises ``FileNotFoundError`` if the file is absent.
    """
    state_path = project_root / ARTIFACT_FILENAMES["pipeline_state"]
    with open(state_path, "r") as f:
        data = json.load(f)

    # Apply defaults for missing SVP 2.2 fields
    for key, default_val in _SVP22_FIELD_DEFAULTS.items():
        if key not in data:
            if isinstance(default_val, list):
                data[key] = list(default_val)
            else:
                data[key] = default_val

    # Map JSON "pass" key to Python "pass_" attribute
    pass_val = data.pop("pass", None)

    # Build PipelineState from the data dict
    state = PipelineState(
        stage=data.get("stage", "0"),
        sub_stage=data.get("sub_stage", None),
        current_unit=data.get("current_unit", None),
        total_units=data.get("total_units", 0),
        verified_units=data.get("verified_units", []),
        alignment_iterations=data.get("alignment_iterations", 0),
        fix_ladder_position=data.get("fix_ladder_position", None),
        red_run_retries=data.get("red_run_retries", 0),
        assembly_retries=data.get("assembly_retries", 0),
        pass_history=data.get("pass_history", []),
        debug_session=data.get("debug_session", None),
        debug_history=data.get("debug_history", []),
        redo_triggered_from=data.get("redo_triggered_from", None),
        delivered_repo_path=data.get("delivered_repo_path", None),
        primary_language=data.get("primary_language", "python"),
        component_languages=data.get("component_languages", []),
        secondary_language=data.get("secondary_language", None),
        oracle_session_active=data.get("oracle_session_active", False),
        oracle_test_project=data.get("oracle_test_project", None),
        oracle_phase=data.get("oracle_phase", None),
        oracle_run_count=data.get("oracle_run_count", 0),
        oracle_nested_session_path=data.get("oracle_nested_session_path", None),
        oracle_modification_count=data.get("oracle_modification_count", 0),
        state_hash=data.get("state_hash", None),
        spec_revision_count=data.get("spec_revision_count", 0),
        pass_=pass_val,
        pass2_nested_session_path=data.get("pass2_nested_session_path", None),
        deferred_broken_units=data.get("deferred_broken_units", []),
        toolchain_status=data.get("toolchain_status", "NOT_READY"),
        requires_statistical_analysis=data.get(
            "requires_statistical_analysis", False
        ),
        statistical_review_done=data.get("statistical_review_done", False),
    )

    return state


def _state_to_json_dict(state: PipelineState) -> Dict[str, Any]:
    """Convert PipelineState to a JSON-serializable dict.

    Preserves key ordering from the dataclass, but renames pass_ to pass
    in the correct position.
    """
    data = asdict(state)
    # Rename pass_ -> pass, preserving key order
    result = {}
    for key, value in data.items():
        if key == "pass_":
            result["pass"] = value
        else:
            result[key] = value
    return result


def save_state(project_root: Path, state: PipelineState) -> None:
    """Validate and persist *state* as formatted JSON, computing state_hash.

    The state_hash is the SHA-256 hex digest of the *previous* file on disk
    (before the current write). If no prior file exists, state_hash is None.
    This avoids self-referential hashing (Bug S3-1, S3-5 clarification).
    """
    # Validate current_unit/sub_stage co-invariant BEFORE any file I/O
    if state.current_unit is not None and state.sub_stage is None:
        raise ValueError(
            "current_unit is set but sub_stage is None; "
            "sub_stage must be non-null when current_unit is set"
        )

    state_path = project_root / ARTIFACT_FILENAMES["pipeline_state"]

    # Compute state_hash from the previous file's raw bytes (if it exists)
    if state_path.exists():
        previous_bytes = state_path.read_bytes()
        hash_hex = hashlib.sha256(previous_bytes).hexdigest()
    else:
        hash_hex = None

    # Store the computed hash in the state object
    state.state_hash = hash_hex

    # Convert to JSON dict and write
    data = _state_to_json_dict(state)

    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    json_text = json.dumps(data, indent=2)
    state_path.write_text(json_text, encoding="utf-8")
