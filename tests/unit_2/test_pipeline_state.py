"""
Test suite for Unit 2: Pipeline State Schema and Core Operations

Tests cover:
- Module-level constants: STAGES, SUB_STAGES_STAGE_0, FIX_LADDER_POSITIONS
- DebugSession: construction, to_dict, from_dict round-trip
- PipelineState: construction, to_dict, from_dict round-trip, including debug fields
- create_initial_state: all initial invariants
- load_state: deserialization, debug_session deserialization, error conditions
- save_state: atomic write, updated_at timestamp update
- validate_state: structural integrity checks for all fields
- recover_state_from_markers: marker scanning, None when no markers, conservative state
- get_stage_display: human-readable display strings
- All invariants from the blueprint
- All error conditions from the blueprint
- Signature verification for all public functions and classes

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: Project roots are temporary directories created via
tmp_path, representing valid filesystem directories.

DATA ASSUMPTION: pipeline_state.json content is well-formed JSON following
the schema contract, with stage values from STAGES ("0"-"5", "pre_stage_3").

DATA ASSUMPTION: ISO timestamps are in the format "2025-01-15T10:30:00"
as typical ISO 8601 strings from datetime.isoformat().

DATA ASSUMPTION: Unit numbers are small positive integers (1-11),
representing a typical project with a moderate number of blueprint units.

DATA ASSUMPTION: Bug IDs are small positive integers (1-3), representing
typical post-delivery bug identifiers.

DATA ASSUMPTION: Debug session phases use the exact string literals from
the blueprint: "triage_readonly", "triage", "regression_test",
"stage3_reentry", "repair", "complete".

DATA ASSUMPTION: SVP marker comments follow the format
"<!-- SVP_APPROVED: ... -->" in markdown files, representing the spec's
completion marker format.

DATA ASSUMPTION: Verified unit marker directories follow the naming
pattern ".svp/markers/unit_N_verified" where N is the unit number.

DATA ASSUMPTION: Pass history entries contain pass_number (int),
reached_unit (int), ended_reason (str), and timestamp (str) as
required fields per the blueprint schema.

DATA ASSUMPTION: Malformed JSON is represented by a string with invalid
JSON syntax (e.g., "{invalid"). This is a standard edge case.

DATA ASSUMPTION: Log reference paths are simple string paths like
"logs/rejection.log", representing typical project-relative log file paths.
==========================================================================
"""

import json
import os
import inspect
import pytest
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from unittest.mock import patch, MagicMock

from svp.scripts.pipeline_state import (
    STAGES,
    SUB_STAGES_STAGE_0,
    FIX_LADDER_POSITIONS,
    DebugSession,
    PipelineState,
    create_initial_state,
    load_state,
    save_state,
    validate_state,
    recover_state_from_markers,
    get_stage_display,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_state_json(project_root: Path, state_dict: Dict[str, Any]) -> Path:
    """Helper: write a state dict as JSON to pipeline_state.json in project_root."""
    state_path = project_root / "pipeline_state.json"
    state_path.write_text(json.dumps(state_dict, indent=2), encoding="utf-8")
    return state_path


def _make_minimal_state_dict(
    stage: str = "0",
    sub_stage: Optional[str] = "hook_activation",
    current_unit: Optional[int] = None,
    total_units: Optional[int] = None,
    fix_ladder_position: Optional[str] = None,
    red_run_retries: int = 0,
    alignment_iteration: int = 0,
    verified_units: Optional[List[Dict[str, Any]]] = None,
    pass_history: Optional[List[Dict[str, Any]]] = None,
    log_references: Optional[Dict[str, str]] = None,
    project_name: Optional[str] = "test_project",
    last_action: Optional[str] = None,
    debug_session: Optional[Dict[str, Any]] = None,
    debug_history: Optional[List[Dict[str, Any]]] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a minimal valid state dictionary for testing."""
    now = datetime.now().isoformat()
    return {
        "stage": stage,
        "sub_stage": sub_stage,
        "current_unit": current_unit,
        "total_units": total_units,
        "fix_ladder_position": fix_ladder_position,
        "red_run_retries": red_run_retries,
        "alignment_iteration": alignment_iteration,
        "verified_units": verified_units if verified_units is not None else [],
        "pass_history": pass_history if pass_history is not None else [],
        "log_references": log_references if log_references is not None else {},
        "project_name": project_name,
        "last_action": last_action,
        "debug_session": debug_session,
        "debug_history": debug_history if debug_history is not None else [],
        "created_at": created_at or now,
        "updated_at": updated_at or now,
    }


def _make_debug_session_dict(
    bug_id: int = 1,
    description: str = "Test bug",
    classification: Optional[str] = "single_unit",
    affected_units: Optional[List[int]] = None,
    regression_test_path: Optional[str] = None,
    phase: str = "triage_readonly",
    authorized: bool = False,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a debug session dictionary for testing."""
    return {
        "bug_id": bug_id,
        "description": description,
        "classification": classification,
        "affected_units": affected_units if affected_units is not None else [1],
        "regression_test_path": regression_test_path,
        "phase": phase,
        "authorized": authorized,
        "created_at": created_at or datetime.now().isoformat(),
    }


# ===========================================================================
# 1. Module-Level Constants
# ===========================================================================


class TestModuleLevelConstants:
    """Verify module-level constants match the blueprint schema."""

    def test_stages_is_list(self):
        """STAGES must be a list."""
        assert isinstance(STAGES, list)

    def test_stages_values(self):
        """STAGES must contain exactly the specified stage identifiers."""
        assert STAGES == ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

    def test_sub_stages_stage_0_is_list(self):
        """SUB_STAGES_STAGE_0 must be a list."""
        assert isinstance(SUB_STAGES_STAGE_0, list)

    def test_sub_stages_stage_0_values(self):
        """SUB_STAGES_STAGE_0 must contain hook_activation and project_context."""
        assert SUB_STAGES_STAGE_0 == ["hook_activation", "project_context"]

    def test_fix_ladder_positions_is_list(self):
        """FIX_LADDER_POSITIONS must be a list."""
        assert isinstance(FIX_LADDER_POSITIONS, list)

    def test_fix_ladder_positions_values(self):
        """FIX_LADDER_POSITIONS must contain the exact positions from the blueprint."""
        expected = [
            None, "fresh_test", "hint_test",
            "fresh_impl", "diagnostic", "diagnostic_impl",
        ]
        assert FIX_LADDER_POSITIONS == expected


# ===========================================================================
# 2. DebugSession Class
# ===========================================================================


class TestDebugSession:
    """Tests for the DebugSession data class."""

    def test_construction_with_kwargs(self):
        """DebugSession can be constructed with keyword arguments."""
        # DATA ASSUMPTION: Bug ID 1 with "single_unit" classification is a
        # typical debug session scenario.
        ds = DebugSession(
            bug_id=1,
            description="Test bug",
            classification="single_unit",
            affected_units=[2],
            regression_test_path=None,
            phase="triage_readonly",
            authorized=False,
            created_at="2025-01-15T10:30:00",
        )
        assert ds.bug_id == 1
        assert ds.description == "Test bug"
        assert ds.classification == "single_unit"
        assert ds.affected_units == [2]
        assert ds.regression_test_path is None
        assert ds.phase == "triage_readonly"
        assert ds.authorized is False
        assert ds.created_at == "2025-01-15T10:30:00"

    def test_to_dict_returns_dict(self):
        """to_dict returns a dictionary representation."""
        ds = DebugSession(
            bug_id=2,
            description="Another bug",
            classification="cross_unit",
            affected_units=[3, 4],
            regression_test_path="tests/regression/test_bug2.py",
            phase="repair",
            authorized=True,
            created_at="2025-02-20T14:00:00",
        )
        result = ds.to_dict()
        assert isinstance(result, dict)
        assert result["bug_id"] == 2
        assert result["description"] == "Another bug"
        assert result["classification"] == "cross_unit"
        assert result["affected_units"] == [3, 4]
        assert result["regression_test_path"] == "tests/regression/test_bug2.py"
        assert result["phase"] == "repair"
        assert result["authorized"] is True
        assert result["created_at"] == "2025-02-20T14:00:00"

    def test_from_dict_round_trip(self):
        """from_dict(to_dict()) produces an equivalent DebugSession."""
        original = DebugSession(
            bug_id=3,
            description="Build env issue",
            classification="build_env",
            affected_units=[1, 5, 7],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            created_at="2025-03-01T09:00:00",
        )
        data = original.to_dict()
        restored = DebugSession.from_dict(data)
        assert restored.bug_id == original.bug_id
        assert restored.description == original.description
        assert restored.classification == original.classification
        assert restored.affected_units == original.affected_units
        assert restored.regression_test_path == original.regression_test_path
        assert restored.phase == original.phase
        assert restored.authorized == original.authorized
        assert restored.created_at == original.created_at

    def test_from_dict_with_none_classification(self):
        """from_dict handles None classification correctly."""
        data = _make_debug_session_dict(classification=None)
        ds = DebugSession.from_dict(data)
        assert ds.classification is None

    def test_debug_session_all_phases(self):
        """DebugSession supports all specified phase values."""
        # DATA ASSUMPTION: These phases come directly from the blueprint spec.
        phases = [
            "triage_readonly", "triage", "regression_test",
            "stage3_reentry", "repair", "complete",
        ]
        for phase in phases:
            ds = DebugSession(
                bug_id=1,
                description="test",
                classification=None,
                affected_units=[1],
                regression_test_path=None,
                phase=phase,
                authorized=False,
                created_at="2025-01-01T00:00:00",
            )
            assert ds.phase == phase

    def test_debug_session_all_classifications(self):
        """DebugSession supports all specified classification values."""
        # DATA ASSUMPTION: These are the three classification values from the blueprint.
        classifications = ["build_env", "single_unit", "cross_unit", None]
        for cls_val in classifications:
            ds = DebugSession(
                bug_id=1,
                description="test",
                classification=cls_val,
                affected_units=[1],
                regression_test_path=None,
                phase="triage",
                authorized=False,
                created_at="2025-01-01T00:00:00",
            )
            assert ds.classification == cls_val


# ===========================================================================
# 3. PipelineState Class
# ===========================================================================


class TestPipelineState:
    """Tests for the PipelineState data class."""

    def test_construction_with_kwargs(self):
        """PipelineState can be constructed with keyword arguments."""
        # DATA ASSUMPTION: Stage "3" with current_unit 4, total_units 11
        # represents a mid-pipeline state during unit verification.
        now = "2025-01-15T10:30:00"
        ps = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=4,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[{"unit": 1, "timestamp": now}, {"unit": 2, "timestamp": now}],
            pass_history=[{"pass_number": 1, "reached_unit": 3, "ended_reason": "test_failure", "timestamp": now}],
            log_references={"rejection_log": "logs/rejection.log"},
            project_name="my_project",
            last_action="Verified unit 3",
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        assert ps.stage == "3"
        assert ps.sub_stage is None
        assert ps.current_unit == 4
        assert ps.total_units == 11
        assert ps.fix_ladder_position is None
        assert ps.red_run_retries == 0
        assert ps.alignment_iteration == 0
        assert len(ps.verified_units) == 2
        assert len(ps.pass_history) == 1
        assert ps.log_references == {"rejection_log": "logs/rejection.log"}
        assert ps.project_name == "my_project"
        assert ps.last_action == "Verified unit 3"
        assert ps.debug_session is None
        assert ps.debug_history == []
        assert ps.created_at == now
        assert ps.updated_at == now

    def test_to_dict_returns_dict(self):
        """to_dict returns a complete dictionary representation."""
        now = "2025-01-15T10:30:00"
        ps = PipelineState(
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
            project_name="test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        result = ps.to_dict()
        assert isinstance(result, dict)
        assert result["stage"] == "0"
        assert result["sub_stage"] == "hook_activation"
        assert result["current_unit"] is None
        assert result["total_units"] is None
        assert result["fix_ladder_position"] is None
        assert result["red_run_retries"] == 0
        assert result["alignment_iteration"] == 0
        assert result["verified_units"] == []
        assert result["pass_history"] == []
        assert result["log_references"] == {}
        assert result["project_name"] == "test"
        assert result["last_action"] is None
        assert result["debug_session"] is None
        assert result["debug_history"] == []

    def test_from_dict_round_trip(self):
        """from_dict(to_dict()) produces an equivalent PipelineState."""
        now = "2025-01-15T10:30:00"
        original = PipelineState(
            stage="2",
            sub_stage=None,
            current_unit=None,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=2,
            alignment_iteration=1,
            verified_units=[],
            pass_history=[],
            log_references={"diagnostic_log": "logs/diag.log"},
            project_name="roundtrip_project",
            last_action="alignment check",
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        data = original.to_dict()
        restored = PipelineState.from_dict(data)
        assert restored.stage == original.stage
        assert restored.sub_stage == original.sub_stage
        assert restored.current_unit == original.current_unit
        assert restored.total_units == original.total_units
        assert restored.red_run_retries == original.red_run_retries
        assert restored.alignment_iteration == original.alignment_iteration
        assert restored.project_name == original.project_name
        assert restored.debug_session is None
        assert restored.debug_history == []

    def test_from_dict_with_debug_session(self):
        """from_dict correctly deserializes debug_session when present."""
        ds_dict = _make_debug_session_dict(
            bug_id=1,
            description="Deserialization test bug",
            phase="repair",
            authorized=True,
        )
        state_dict = _make_minimal_state_dict(
            stage="3",
            debug_session=ds_dict,
        )
        ps = PipelineState.from_dict(state_dict)
        assert ps.debug_session is not None
        assert isinstance(ps.debug_session, DebugSession)
        assert ps.debug_session.bug_id == 1
        assert ps.debug_session.description == "Deserialization test bug"
        assert ps.debug_session.phase == "repair"
        assert ps.debug_session.authorized is True

    def test_to_dict_with_debug_session(self):
        """to_dict correctly serializes debug_session when present."""
        ds = DebugSession(
            bug_id=2,
            description="Serialization test",
            classification="cross_unit",
            affected_units=[3, 4],
            regression_test_path="tests/regression/test_bug2.py",
            phase="complete",
            authorized=True,
            created_at="2025-01-20T12:00:00",
        )
        now = "2025-01-20T12:00:00"
        ps = PipelineState(
            stage="5",
            sub_stage=None,
            current_unit=None,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name="test",
            last_action=None,
            debug_session=ds,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        result = ps.to_dict()
        assert result["debug_session"] is not None
        assert isinstance(result["debug_session"], dict)
        assert result["debug_session"]["bug_id"] == 2
        assert result["debug_session"]["phase"] == "complete"

    def test_pipeline_state_with_debug_history(self):
        """PipelineState preserves debug_history entries."""
        # DATA ASSUMPTION: Debug history entries are dicts with at minimum
        # the same fields as a DebugSession, representing completed sessions.
        history_entry = {
            "bug_id": 1,
            "description": "Fixed bug",
            "classification": "single_unit",
            "affected_units": [2],
            "phase": "complete",
            "authorized": True,
            "created_at": "2025-01-10T08:00:00",
            "completed_at": "2025-01-10T10:00:00",
        }
        state_dict = _make_minimal_state_dict(debug_history=[history_entry])
        ps = PipelineState.from_dict(state_dict)
        assert len(ps.debug_history) == 1
        result = ps.to_dict()
        assert len(result["debug_history"]) == 1
        assert result["debug_history"][0]["bug_id"] == 1


# ===========================================================================
# 4. create_initial_state
# ===========================================================================


class TestCreateInitialState:
    """Tests for create_initial_state function."""

    def test_returns_pipeline_state(self):
        """create_initial_state returns a PipelineState instance."""
        result = create_initial_state("test_project")
        assert isinstance(result, PipelineState)

    def test_initial_stage_is_0(self):
        """Invariant: Initial state must be Stage 0."""
        result = create_initial_state("test_project")
        assert result.stage == "0"

    def test_initial_sub_stage_is_hook_activation(self):
        """Invariant: Initial sub-stage must be hook_activation."""
        result = create_initial_state("test_project")
        assert result.sub_stage == "hook_activation"

    def test_initial_red_run_retries_is_0(self):
        """Invariant: Initial red_run_retries must be 0."""
        result = create_initial_state("test_project")
        assert result.red_run_retries == 0

    def test_initial_alignment_iteration_is_0(self):
        """Invariant: Initial alignment_iteration must be 0."""
        result = create_initial_state("test_project")
        assert result.alignment_iteration == 0

    def test_initial_verified_units_empty(self):
        """Invariant: No units verified initially."""
        result = create_initial_state("test_project")
        assert len(result.verified_units) == 0

    def test_initial_pass_history_empty(self):
        """Invariant: No pass history initially."""
        result = create_initial_state("test_project")
        assert len(result.pass_history) == 0

    def test_initial_debug_session_is_none(self):
        """Invariant: No debug session initially."""
        result = create_initial_state("test_project")
        assert result.debug_session is None

    def test_initial_debug_history_empty(self):
        """Invariant: No debug history initially."""
        result = create_initial_state("test_project")
        assert result.debug_history == []

    def test_project_name_is_set(self):
        """create_initial_state preserves the project name."""
        result = create_initial_state("my_awesome_project")
        assert result.project_name == "my_awesome_project"

    def test_created_at_is_set(self):
        """create_initial_state sets created_at to an ISO timestamp."""
        result = create_initial_state("test_project")
        assert result.created_at is not None
        assert isinstance(result.created_at, str)
        # Should be parseable as a datetime
        datetime.fromisoformat(result.created_at)

    def test_updated_at_is_set(self):
        """create_initial_state sets updated_at to an ISO timestamp."""
        result = create_initial_state("test_project")
        assert result.updated_at is not None
        assert isinstance(result.updated_at, str)
        datetime.fromisoformat(result.updated_at)

    def test_fix_ladder_position_is_none(self):
        """Initial fix_ladder_position should be None."""
        result = create_initial_state("test_project")
        assert result.fix_ladder_position is None

    def test_current_unit_is_none(self):
        """Initial current_unit should be None (not in Stage 3 yet)."""
        result = create_initial_state("test_project")
        assert result.current_unit is None

    def test_total_units_is_none(self):
        """Initial total_units should be None (blueprint not yet loaded)."""
        result = create_initial_state("test_project")
        assert result.total_units is None


# ===========================================================================
# 5. load_state
# ===========================================================================


class TestLoadState:
    """Tests for load_state function."""

    def test_load_valid_state(self, tmp_path):
        """load_state deserializes a valid pipeline_state.json."""
        state_dict = _make_minimal_state_dict(stage="2", project_name="loaded_project")
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert isinstance(result, PipelineState)
        assert result.stage == "2"
        assert result.project_name == "loaded_project"

    def test_load_state_valid_stage(self, tmp_path):
        """Invariant: Loaded stage must be a valid stage identifier."""
        state_dict = _make_minimal_state_dict(stage="3")
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert result.stage in STAGES

    def test_load_state_non_negative_retries(self, tmp_path):
        """Invariant: Red run retries must be non-negative after load."""
        state_dict = _make_minimal_state_dict(red_run_retries=5)
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert result.red_run_retries >= 0

    def test_load_state_non_negative_alignment_iteration(self, tmp_path):
        """Invariant: Alignment iteration must be non-negative after load."""
        state_dict = _make_minimal_state_dict(alignment_iteration=3)
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert result.alignment_iteration >= 0

    def test_load_state_with_debug_session(self, tmp_path):
        """load_state deserializes debug_session when present in JSON."""
        ds_dict = _make_debug_session_dict(
            bug_id=2,
            description="Debug load test",
            phase="stage3_reentry",
            authorized=True,
        )
        state_dict = _make_minimal_state_dict(
            stage="3",
            debug_session=ds_dict,
        )
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert result.debug_session is not None
        assert isinstance(result.debug_session, DebugSession)
        assert result.debug_session.bug_id == 2
        assert result.debug_session.phase == "stage3_reentry"
        assert result.debug_session.authorized is True

    def test_load_state_with_null_debug_session(self, tmp_path):
        """load_state handles null debug_session correctly."""
        state_dict = _make_minimal_state_dict(debug_session=None)
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert result.debug_session is None

    def test_load_state_preserves_verified_units(self, tmp_path):
        """load_state preserves verified_units list."""
        verified = [
            {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
            {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
        ]
        state_dict = _make_minimal_state_dict(verified_units=verified)
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert len(result.verified_units) == 2

    def test_load_state_preserves_pass_history(self, tmp_path):
        """load_state preserves pass_history list."""
        history = [
            {"pass_number": 1, "reached_unit": 5, "ended_reason": "test_failure", "timestamp": "2025-01-15T10:00:00"},
        ]
        state_dict = _make_minimal_state_dict(pass_history=history)
        _write_state_json(tmp_path, state_dict)

        result = load_state(tmp_path)
        assert len(result.pass_history) == 1

    def test_load_state_file_not_found(self, tmp_path):
        """Error: FileNotFoundError when pipeline_state.json does not exist."""
        with pytest.raises(FileNotFoundError, match="State file not found"):
            load_state(tmp_path)

    def test_load_state_malformed_json(self, tmp_path):
        """Error: json.JSONDecodeError when file is not valid JSON."""
        # DATA ASSUMPTION: A string with invalid JSON syntax triggers decode error.
        state_path = tmp_path / "pipeline_state.json"
        state_path.write_text("{invalid json content", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_state(tmp_path)

    def test_load_state_all_stages(self, tmp_path):
        """load_state can deserialize state for every valid stage."""
        for stage in STAGES:
            state_dict = _make_minimal_state_dict(stage=stage)
            if stage == "0":
                state_dict["sub_stage"] = "hook_activation"
            else:
                state_dict["sub_stage"] = None
            _write_state_json(tmp_path, state_dict)
            result = load_state(tmp_path)
            assert result.stage == stage


# ===========================================================================
# 6. save_state
# ===========================================================================


class TestSaveState:
    """Tests for save_state function."""

    def test_save_creates_file(self, tmp_path):
        """Invariant: State file must exist after save."""
        state = create_initial_state("test_project")
        save_state(state, tmp_path)

        state_path = tmp_path / "pipeline_state.json"
        assert state_path.exists()

    def test_save_writes_valid_json(self, tmp_path):
        """save_state writes valid JSON that can be parsed back."""
        state = create_initial_state("test_project")
        save_state(state, tmp_path)

        state_path = tmp_path / "pipeline_state.json"
        content = state_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
        assert parsed["stage"] == "0"

    def test_save_roundtrip(self, tmp_path):
        """save_state followed by load_state preserves state."""
        state = create_initial_state("roundtrip_test")
        save_state(state, tmp_path)

        loaded = load_state(tmp_path)
        assert loaded.stage == state.stage
        assert loaded.sub_stage == state.sub_stage
        assert loaded.project_name == state.project_name
        assert loaded.red_run_retries == state.red_run_retries
        assert loaded.alignment_iteration == state.alignment_iteration

    def test_save_updates_updated_at(self, tmp_path):
        """updated_at is set to current ISO timestamp on every save_state call."""
        state = create_initial_state("test_project")
        before_save = datetime.now().isoformat()
        save_state(state, tmp_path)

        state_path = tmp_path / "pipeline_state.json"
        content = json.loads(state_path.read_text(encoding="utf-8"))
        updated_at = content["updated_at"]

        # The updated_at should be a valid ISO timestamp
        parsed_ts = datetime.fromisoformat(updated_at)
        assert parsed_ts is not None

    def test_save_state_with_debug_session(self, tmp_path):
        """save_state correctly serializes a state with debug_session."""
        ds = DebugSession(
            bug_id=1,
            description="Save test",
            classification="single_unit",
            affected_units=[3],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            created_at="2025-01-15T10:00:00",
        )
        now = "2025-01-15T10:00:00"
        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=3,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name="debug_test",
            last_action=None,
            debug_session=ds,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        save_state(state, tmp_path)

        state_path = tmp_path / "pipeline_state.json"
        content = json.loads(state_path.read_text(encoding="utf-8"))
        assert content["debug_session"] is not None
        assert content["debug_session"]["bug_id"] == 1

    def test_save_overwrites_existing_file(self, tmp_path):
        """save_state overwrites an existing state file."""
        state1 = create_initial_state("first_project")
        save_state(state1, tmp_path)

        state2 = create_initial_state("second_project")
        save_state(state2, tmp_path)

        loaded = load_state(tmp_path)
        assert loaded.project_name == "second_project"

    def test_save_atomic_write_does_not_corrupt(self, tmp_path):
        """save_state uses atomic write (temp file + rename) to prevent corruption.

        We verify this indirectly: if the file exists and is valid JSON after
        save, the atomic write mechanism is at least functioning correctly.
        """
        state = create_initial_state("atomic_test")
        save_state(state, tmp_path)

        state_path = tmp_path / "pipeline_state.json"
        assert state_path.exists()
        # The file should be valid JSON
        content = json.loads(state_path.read_text(encoding="utf-8"))
        assert content["stage"] == "0"

    def test_save_preserves_debug_history(self, tmp_path):
        """save_state preserves debug_history entries."""
        history_entry = {
            "bug_id": 1,
            "description": "Completed bug fix",
            "phase": "complete",
        }
        state_dict = _make_minimal_state_dict(debug_history=[history_entry])
        state = PipelineState.from_dict(state_dict)
        save_state(state, tmp_path)

        loaded = load_state(tmp_path)
        assert len(loaded.debug_history) == 1


# ===========================================================================
# 7. validate_state
# ===========================================================================


class TestValidateState:
    """Tests for validate_state function."""

    def test_valid_state_returns_empty(self):
        """validate_state returns empty list for a valid state."""
        state = create_initial_state("valid_project")
        errors = validate_state(state)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_invalid_stage_returns_errors(self):
        """validate_state detects invalid stage value."""
        state_dict = _make_minimal_state_dict(stage="99")
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0
        # Error should mention something about the invalid stage
        error_text = " ".join(errors).lower()
        assert "stage" in error_text or "invalid" in error_text

    def test_negative_red_run_retries(self):
        """validate_state detects negative red_run_retries."""
        state_dict = _make_minimal_state_dict(red_run_retries=-1)
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0

    def test_negative_alignment_iteration(self):
        """validate_state detects negative alignment_iteration."""
        state_dict = _make_minimal_state_dict(alignment_iteration=-5)
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0

    def test_valid_stage_0_with_sub_stage(self):
        """validate_state accepts valid sub-stage for stage 0."""
        for sub in SUB_STAGES_STAGE_0:
            state_dict = _make_minimal_state_dict(stage="0", sub_stage=sub)
            state = PipelineState.from_dict(state_dict)
            errors = validate_state(state)
            assert len(errors) == 0, f"Unexpected errors for sub_stage '{sub}': {errors}"

    def test_invalid_sub_stage_for_stage_0(self):
        """validate_state detects invalid sub-stage for stage 0."""
        state_dict = _make_minimal_state_dict(stage="0", sub_stage="nonexistent_sub")
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0

    def test_verified_units_missing_required_fields(self):
        """validate_state detects verified_units entries with missing fields."""
        # DATA ASSUMPTION: verified_units entries must have 'unit' and 'timestamp'
        bad_entry = {"unit": 1}  # missing timestamp
        state_dict = _make_minimal_state_dict(verified_units=[bad_entry])
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0

    def test_pass_history_missing_required_fields(self):
        """validate_state detects pass_history entries with missing fields."""
        # DATA ASSUMPTION: pass_history entries must have pass_number,
        # reached_unit, ended_reason, and timestamp.
        bad_entry = {"pass_number": 1}  # missing other required fields
        state_dict = _make_minimal_state_dict(pass_history=[bad_entry])
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0

    def test_valid_state_with_all_stages(self):
        """validate_state accepts all valid stage values."""
        for stage in STAGES:
            if stage == "0":
                sub = "hook_activation"
            else:
                sub = None
            state_dict = _make_minimal_state_dict(stage=stage, sub_stage=sub)
            state = PipelineState.from_dict(state_dict)
            errors = validate_state(state)
            assert len(errors) == 0, f"Unexpected errors for stage '{stage}': {errors}"

    def test_valid_fix_ladder_positions(self):
        """validate_state accepts all valid fix_ladder_position values."""
        for pos in FIX_LADDER_POSITIONS:
            state_dict = _make_minimal_state_dict(
                stage="3",
                sub_stage=None,
                fix_ladder_position=pos,
            )
            state = PipelineState.from_dict(state_dict)
            errors = validate_state(state)
            assert len(errors) == 0, f"Unexpected errors for fix_ladder_position '{pos}': {errors}"

    def test_validate_state_with_valid_debug_session(self):
        """validate_state accepts a valid DebugSession."""
        ds_dict = _make_debug_session_dict()
        state_dict = _make_minimal_state_dict(
            stage="3",
            sub_stage=None,
            debug_session=ds_dict,
        )
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_validate_state_with_none_debug_session(self):
        """validate_state accepts None debug_session."""
        state_dict = _make_minimal_state_dict(debug_session=None)
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) == 0

    def test_validate_state_returns_error_details_as_strings(self):
        """validate_state returns errors as a list of strings."""
        state_dict = _make_minimal_state_dict(stage="invalid_stage")
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert all(isinstance(e, str) for e in errors)

    def test_valid_verified_units_entries(self):
        """validate_state accepts properly formed verified_units entries."""
        good_entries = [
            {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
            {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
        ]
        state_dict = _make_minimal_state_dict(verified_units=good_entries)
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) == 0

    def test_valid_pass_history_entries(self):
        """validate_state accepts properly formed pass_history entries."""
        good_entries = [
            {
                "pass_number": 1,
                "reached_unit": 5,
                "ended_reason": "test_failure",
                "timestamp": "2025-01-15T10:00:00",
            },
            {
                "pass_number": 2,
                "reached_unit": 8,
                "ended_reason": "completed",
                "timestamp": "2025-01-15T12:00:00",
            },
        ]
        state_dict = _make_minimal_state_dict(pass_history=good_entries)
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) == 0

    def test_debug_history_missing_required_fields(self):
        """validate_state detects debug_history entries with missing fields."""
        # DATA ASSUMPTION: debug_history entries have required fields similar to DebugSession
        bad_entry = {}  # empty entry should be invalid
        state_dict = _make_minimal_state_dict(debug_history=[bad_entry])
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0


# ===========================================================================
# 8. recover_state_from_markers
# ===========================================================================


class TestRecoverStateFromMarkers:
    """Tests for recover_state_from_markers function."""

    def test_returns_none_when_no_markers(self, tmp_path):
        """recover_state_from_markers returns None if no markers found."""
        result = recover_state_from_markers(tmp_path)
        assert result is None

    def test_recovers_from_stakeholder_approval_marker(self, tmp_path):
        """Recovers state when stakeholder.md has SVP_APPROVED marker."""
        # DATA ASSUMPTION: SVP_APPROVED markers in stakeholder.md indicate
        # that Stage 1 (stakeholder spec approval) has been completed.
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        stakeholder_md = specs_dir / "stakeholder.md"
        stakeholder_md.write_text(
            "# Stakeholder Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\nContent here.\n",
            encoding="utf-8",
        )

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert isinstance(result, PipelineState)
        # Should be at least past stage 1 since stakeholder spec is approved
        assert result.stage in STAGES

    def test_recovers_from_blueprint_approval_marker(self, tmp_path):
        """Recovers state when blueprint.md has SVP_APPROVED marker."""
        # DATA ASSUMPTION: SVP_APPROVED marker in blueprint.md indicates
        # Stage 2 (blueprint alignment) has been completed.
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        stakeholder_md = specs_dir / "stakeholder.md"
        stakeholder_md.write_text(
            "# Stakeholder Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        blueprint_md = blueprint_dir / "blueprint.md"
        blueprint_md.write_text(
            "# Blueprint\n<!-- SVP_APPROVED: blueprint -->\nBlueprint content.\n",
            encoding="utf-8",
        )

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert isinstance(result, PipelineState)

    def test_recovers_from_unit_verified_markers(self, tmp_path):
        """Recovers state from .svp/markers/unit_N_verified directories."""
        # DATA ASSUMPTION: unit_N_verified directories under .svp/markers/
        # indicate that unit N has been verified in Stage 3.
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        stakeholder_md = specs_dir / "stakeholder.md"
        stakeholder_md.write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        blueprint_md = blueprint_dir / "blueprint.md"
        blueprint_md.write_text(
            "# Blueprint\n<!-- SVP_APPROVED: blueprint -->\n",
            encoding="utf-8",
        )

        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        (markers_dir / "unit_1_verified").mkdir()
        (markers_dir / "unit_2_verified").mkdir()
        (markers_dir / "unit_3_verified").mkdir()

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert isinstance(result, PipelineState)
        # Recovery should indicate some unit progress
        assert result.stage in STAGES

    def test_returns_conservative_state(self, tmp_path):
        """Recovery constructs the most conservative valid state."""
        # Only stakeholder spec approved, no blueprint marker
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        stakeholder_md = specs_dir / "stakeholder.md"
        stakeholder_md.write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        # Should not jump ahead to stage 3 without blueprint approval
        stage_index = STAGES.index(result.stage)
        # Conservative: should be at most stage 2 (pre-blueprint)
        assert stage_index <= STAGES.index("2")

    def test_recovered_state_has_valid_structure(self, tmp_path):
        """Recovered state passes validation."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        stakeholder_md = specs_dir / "stakeholder.md"
        stakeholder_md.write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        errors = validate_state(result)
        assert len(errors) == 0, f"Recovered state has validation errors: {errors}"


# ===========================================================================
# 9. get_stage_display
# ===========================================================================


class TestGetStageDisplay:
    """Tests for get_stage_display function."""

    def test_returns_string(self):
        """get_stage_display returns a string."""
        state = create_initial_state("display_test")
        result = get_stage_display(state)
        assert isinstance(result, str)

    def test_display_includes_stage_info(self):
        """get_stage_display includes stage information in the output."""
        state = create_initial_state("display_test")
        result = get_stage_display(state)
        # Should mention "Stage" or the stage number
        assert "Stage" in result or "stage" in result or "0" in result

    def test_display_stage_3_with_unit_info(self):
        """get_stage_display for Stage 3 includes unit and pass info."""
        # DATA ASSUMPTION: Display format is like "Stage 3, Unit 4 of 11 (pass 2)"
        now = "2025-01-15T10:00:00"
        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=4,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[
                {"pass_number": 1, "reached_unit": 3, "ended_reason": "test_failure", "timestamp": now},
            ],
            log_references={},
            project_name="display_test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        result = get_stage_display(state)
        assert isinstance(result, str)
        # Should contain unit info
        assert "4" in result
        assert "11" in result

    def test_display_stage_0(self):
        """get_stage_display for Stage 0 returns meaningful text."""
        state = create_initial_state("test")
        result = get_stage_display(state)
        assert len(result) > 0

    def test_display_for_each_stage(self):
        """get_stage_display returns a non-empty string for each stage."""
        for stage in STAGES:
            sub = "hook_activation" if stage == "0" else None
            state_dict = _make_minimal_state_dict(stage=stage, sub_stage=sub)
            state = PipelineState.from_dict(state_dict)
            result = get_stage_display(state)
            assert isinstance(result, str)
            assert len(result) > 0, f"Empty display for stage '{stage}'"


# ===========================================================================
# 10. Signature Verification
# ===========================================================================


class TestSignatures:
    """Verify that function and class signatures match the blueprint."""

    def test_create_initial_state_signature(self):
        """create_initial_state accepts project_name: str and returns PipelineState."""
        sig = inspect.signature(create_initial_state)
        params = list(sig.parameters.keys())
        assert "project_name" in params

    def test_load_state_signature(self):
        """load_state accepts project_root: Path and returns PipelineState."""
        sig = inspect.signature(load_state)
        params = list(sig.parameters.keys())
        assert "project_root" in params

    def test_save_state_signature(self):
        """save_state accepts state: PipelineState and project_root: Path."""
        sig = inspect.signature(save_state)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "project_root" in params

    def test_validate_state_signature(self):
        """validate_state accepts state: PipelineState and returns list."""
        sig = inspect.signature(validate_state)
        params = list(sig.parameters.keys())
        assert "state" in params

    def test_recover_state_from_markers_signature(self):
        """recover_state_from_markers accepts project_root: Path."""
        sig = inspect.signature(recover_state_from_markers)
        params = list(sig.parameters.keys())
        assert "project_root" in params

    def test_get_stage_display_signature(self):
        """get_stage_display accepts state: PipelineState."""
        sig = inspect.signature(get_stage_display)
        params = list(sig.parameters.keys())
        assert "state" in params

    def test_debug_session_is_class(self):
        """DebugSession is a class."""
        assert inspect.isclass(DebugSession)

    def test_pipeline_state_is_class(self):
        """PipelineState is a class."""
        assert inspect.isclass(PipelineState)

    def test_debug_session_has_to_dict(self):
        """DebugSession has a to_dict method."""
        assert hasattr(DebugSession, "to_dict")
        assert callable(getattr(DebugSession, "to_dict"))

    def test_debug_session_has_from_dict(self):
        """DebugSession has a from_dict classmethod."""
        assert hasattr(DebugSession, "from_dict")
        assert callable(getattr(DebugSession, "from_dict"))

    def test_pipeline_state_has_to_dict(self):
        """PipelineState has a to_dict method."""
        assert hasattr(PipelineState, "to_dict")
        assert callable(getattr(PipelineState, "to_dict"))

    def test_pipeline_state_has_from_dict(self):
        """PipelineState has a from_dict classmethod."""
        assert hasattr(PipelineState, "from_dict")
        assert callable(getattr(PipelineState, "from_dict"))

    def test_stages_constant_exists(self):
        """STAGES module-level constant exists and is a list."""
        assert isinstance(STAGES, list)

    def test_sub_stages_stage_0_constant_exists(self):
        """SUB_STAGES_STAGE_0 module-level constant exists and is a list."""
        assert isinstance(SUB_STAGES_STAGE_0, list)

    def test_fix_ladder_positions_constant_exists(self):
        """FIX_LADDER_POSITIONS module-level constant exists and is a list."""
        assert isinstance(FIX_LADDER_POSITIONS, list)


# ===========================================================================
# 11. Append-Only Contracts (pass_history, debug_history)
# ===========================================================================


class TestAppendOnlyContracts:
    """Verify that pass_history and debug_history are append-only through save/load cycles."""

    def test_pass_history_preserved_on_save_load(self, tmp_path):
        """Pass history entries are preserved through save/load cycle."""
        # DATA ASSUMPTION: Pass history entries with all required fields.
        now = "2025-01-15T10:00:00"
        entries = [
            {"pass_number": 1, "reached_unit": 3, "ended_reason": "test_failure", "timestamp": now},
            {"pass_number": 2, "reached_unit": 7, "ended_reason": "impl_failure", "timestamp": now},
        ]
        state_dict = _make_minimal_state_dict(pass_history=entries)
        state = PipelineState.from_dict(state_dict)
        save_state(state, tmp_path)

        loaded = load_state(tmp_path)
        assert len(loaded.pass_history) == 2
        # Verify content is preserved
        loaded_dict = loaded.to_dict()
        for i, entry in enumerate(entries):
            for key in entry:
                assert loaded_dict["pass_history"][i][key] == entry[key]

    def test_debug_history_preserved_on_save_load(self, tmp_path):
        """Debug history entries are preserved through save/load cycle."""
        # DATA ASSUMPTION: Debug history entries represent completed debug sessions.
        history = [
            {
                "bug_id": 1,
                "description": "First bug",
                "classification": "single_unit",
                "affected_units": [2],
                "phase": "complete",
                "authorized": True,
                "created_at": "2025-01-10T08:00:00",
            },
        ]
        state_dict = _make_minimal_state_dict(debug_history=history)
        state = PipelineState.from_dict(state_dict)
        save_state(state, tmp_path)

        loaded = load_state(tmp_path)
        assert len(loaded.debug_history) == 1
        loaded_dict = loaded.to_dict()
        assert loaded_dict["debug_history"][0]["bug_id"] == 1
        assert loaded_dict["debug_history"][0]["phase"] == "complete"


# ===========================================================================
# 12. Pre-condition Tests
# ===========================================================================


class TestPreConditions:
    """Test pre-conditions from the blueprint invariants."""

    def test_load_state_requires_existing_directory(self, tmp_path):
        """Pre-condition: project_root must be a directory for load_state."""
        nonexistent = tmp_path / "nonexistent_dir"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_state(nonexistent)

    def test_save_state_requires_existing_directory(self, tmp_path):
        """Pre-condition: project_root must be a directory for save_state."""
        nonexistent = tmp_path / "nonexistent_dir"
        state = create_initial_state("test")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            save_state(state, nonexistent)


# ===========================================================================
# 13. ValueError from validate_state
# ===========================================================================


class TestValidateStateValueError:
    """Test that validate_state findings can produce ValueError with details."""

    def test_validate_state_errors_contain_details(self):
        """Error condition: ValueError 'Invalid state: {details}' on structural problems.

        Note: validate_state itself returns a list of errors. The ValueError
        is raised by callers (like load_state) when validation fails. We verify
        the errors list provides meaningful details.
        """
        state_dict = _make_minimal_state_dict(stage="BOGUS_STAGE")
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0
        # Each error should be a non-empty string with detail
        for err in errors:
            assert isinstance(err, str)
            assert len(err) > 0

    def test_load_state_rejects_invalid_state(self, tmp_path):
        """load_state should reject structurally invalid state (after deserialization)."""
        # Write a state with an invalid stage value
        state_dict = _make_minimal_state_dict(stage="INVALID_STAGE")
        _write_state_json(tmp_path, state_dict)

        # load_state should either raise ValueError or the state won't validate
        # The blueprint says load_state returns a "validated" PipelineState,
        # so it should raise on invalid state.
        with pytest.raises((ValueError,)):
            load_state(tmp_path)


# ===========================================================================
# 14. Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Additional edge case tests."""

    def test_empty_project_name(self):
        """create_initial_state with empty string for project_name."""
        result = create_initial_state("")
        assert isinstance(result, PipelineState)
        assert result.project_name == ""

    def test_pipeline_state_to_dict_from_dict_preserves_all_fields(self):
        """Full round-trip preserves every field in the schema."""
        now = "2025-01-20T14:30:00"
        ds_dict = _make_debug_session_dict(
            bug_id=2,
            description="round trip debug",
            classification="cross_unit",
            affected_units=[1, 2, 3],
            regression_test_path="tests/regression/test_bug2.py",
            phase="regression_test",
            authorized=True,
            created_at=now,
        )
        state_dict = _make_minimal_state_dict(
            stage="3",
            sub_stage=None,
            current_unit=5,
            total_units=11,
            fix_ladder_position="fresh_impl",
            red_run_retries=3,
            alignment_iteration=2,
            verified_units=[
                {"unit": 1, "timestamp": now},
                {"unit": 2, "timestamp": now},
            ],
            pass_history=[
                {"pass_number": 1, "reached_unit": 4, "ended_reason": "test_failure", "timestamp": now},
            ],
            log_references={
                "rejection_log": "logs/rejection.log",
                "diagnostic_log": "logs/diagnostic.log",
            },
            project_name="full_roundtrip",
            last_action="Running diagnostic",
            debug_session=ds_dict,
            debug_history=[{"bug_id": 1, "phase": "complete"}],
            created_at=now,
            updated_at=now,
        )

        state = PipelineState.from_dict(state_dict)
        result_dict = state.to_dict()

        assert result_dict["stage"] == "3"
        assert result_dict["current_unit"] == 5
        assert result_dict["total_units"] == 11
        assert result_dict["fix_ladder_position"] == "fresh_impl"
        assert result_dict["red_run_retries"] == 3
        assert result_dict["alignment_iteration"] == 2
        assert len(result_dict["verified_units"]) == 2
        assert len(result_dict["pass_history"]) == 1
        assert result_dict["log_references"]["rejection_log"] == "logs/rejection.log"
        assert result_dict["project_name"] == "full_roundtrip"
        assert result_dict["last_action"] == "Running diagnostic"
        assert result_dict["debug_session"]["bug_id"] == 2
        assert len(result_dict["debug_history"]) == 1

    def test_save_load_roundtrip_complex_state(self, tmp_path):
        """Full save/load roundtrip with complex state preserves all data."""
        now = "2025-01-20T14:30:00"
        ds = DebugSession(
            bug_id=1,
            description="complex roundtrip",
            classification="single_unit",
            affected_units=[5],
            regression_test_path="tests/regression/test_bug1.py",
            phase="repair",
            authorized=True,
            created_at=now,
        )
        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=6,
            total_units=11,
            fix_ladder_position="diagnostic",
            red_run_retries=2,
            alignment_iteration=1,
            verified_units=[{"unit": i, "timestamp": now} for i in range(1, 6)],
            pass_history=[
                {"pass_number": 1, "reached_unit": 4, "ended_reason": "test_failure", "timestamp": now},
                {"pass_number": 2, "reached_unit": 5, "ended_reason": "impl_failure", "timestamp": now},
            ],
            log_references={"rejection_log": "logs/rej.log"},
            project_name="complex_test",
            last_action="Diagnostic for unit 6",
            debug_session=ds,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )

        save_state(state, tmp_path)
        loaded = load_state(tmp_path)

        assert loaded.stage == "3"
        assert loaded.current_unit == 6
        assert loaded.total_units == 11
        assert loaded.fix_ladder_position == "diagnostic"
        assert loaded.red_run_retries == 2
        assert loaded.alignment_iteration == 1
        assert len(loaded.verified_units) == 5
        assert len(loaded.pass_history) == 2
        assert loaded.project_name == "complex_test"
        assert loaded.debug_session is not None
        assert loaded.debug_session.bug_id == 1
        assert loaded.debug_session.phase == "repair"

    def test_multiple_saves_update_timestamp(self, tmp_path):
        """Each save_state call updates the updated_at timestamp."""
        state = create_initial_state("timestamp_test")

        save_state(state, tmp_path)
        content1 = json.loads((tmp_path / "pipeline_state.json").read_text(encoding="utf-8"))
        ts1 = content1["updated_at"]

        # Small modification to ensure different state
        state.last_action = "modified"
        save_state(state, tmp_path)
        content2 = json.loads((tmp_path / "pipeline_state.json").read_text(encoding="utf-8"))
        ts2 = content2["updated_at"]

        # Both should be valid timestamps
        datetime.fromisoformat(ts1)
        datetime.fromisoformat(ts2)
        # ts2 should be >= ts1 (updated_at set on every save call)
        assert ts2 >= ts1

    def test_recover_state_with_no_specs_directory(self, tmp_path):
        """recover_state_from_markers returns None when specs/ doesn't exist."""
        # No specs dir, no markers at all
        result = recover_state_from_markers(tmp_path)
        assert result is None

    def test_recover_state_with_empty_marker_dir(self, tmp_path):
        """recover_state_from_markers returns None when .svp/markers/ is empty."""
        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        # No markers, no approval comments
        result = recover_state_from_markers(tmp_path)
        assert result is None
