"""Unit 5: Pipeline State -- full implementation."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from svp_config import ARTIFACT_FILENAMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STAGES: Set[str] = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}

VALID_SUB_STAGES: Dict[str, Set[Optional[str]]] = {
    "0": {"hook_activation", "project_context", "project_profile"},
    "1": {None, "checklist_generation"},
    "2": {"blueprint_dialog", "alignment_check", "alignment_confirmed"},
    "pre_stage_3": {None},
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
}


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
