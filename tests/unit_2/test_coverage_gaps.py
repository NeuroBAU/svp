"""
Coverage gap tests for Unit 2: Pipeline State Schema and Core Operations

These tests fill coverage gaps identified by comparing the blueprint's
behavioral contracts against the existing test suite.

Gaps covered:
- get_stage_display pass number in Stage 3 display string
- validate_state with invalid fix_ladder_position
- validate_state with invalid debug_session phase
- validate_state with invalid debug_session classification
- load_state ValueError message format includes "Invalid state:"
- recover_state_from_markers recovered stage for blueprint-only approval
- recover_state_from_markers recovered state with unit markers sets current_unit
- create_initial_state log_references and last_action initial values
- save_state atomic write leaves no temp files behind

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

DATA ASSUMPTION: Pass history entries contain pass_number (int),
reached_unit (int), ended_reason (str), and timestamp (str) as
required fields per the blueprint schema.
==========================================================================
"""

import json
import os
import pytest
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

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
# Helpers (duplicated from main test file for independence)
# ---------------------------------------------------------------------------

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


def _write_state_json(project_root: Path, state_dict: Dict[str, Any]) -> Path:
    """Helper: write a state dict as JSON to pipeline_state.json in project_root."""
    state_path = project_root / "pipeline_state.json"
    state_path.write_text(json.dumps(state_dict, indent=2), encoding="utf-8")
    return state_path


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
# Gap 1: get_stage_display pass number in Stage 3 output
# ===========================================================================


class TestGetStageDisplayPassNumber:
    """Verify get_stage_display includes pass number for Stage 3."""

    def test_display_stage_3_includes_pass_number(self):
        """Blueprint: get_stage_display returns 'Stage 3, Unit 4 of 11 (pass 2)'.

        The pass number should be derived from pass_history length + 1.
        With 1 entry in pass_history, the current pass is 2.
        """
        # DATA ASSUMPTION: A state at Stage 3 with 1 pass history entry means
        # we are on pass 2.
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
        # The blueprint example is "Stage 3, Unit 4 of 11 (pass 2)"
        assert "pass" in result.lower() or "Pass" in result
        assert "2" in result

    def test_display_stage_3_pass_1_no_history(self):
        """With empty pass_history, current pass is 1."""
        now = "2025-01-15T10:00:00"
        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=1,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name="display_test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        result = get_stage_display(state)
        # Should indicate pass 1
        assert "1" in result

    def test_display_stage_3_includes_unit_keyword(self):
        """Stage 3 display should include the word 'Unit'."""
        now = "2025-01-15T10:00:00"
        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=7,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name="display_test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            created_at=now,
            updated_at=now,
        )
        result = get_stage_display(state)
        assert "Unit" in result or "unit" in result


# ===========================================================================
# Gap 2: validate_state with invalid fix_ladder_position
# ===========================================================================


class TestValidateStateInvalidFixLadder:
    """Verify validate_state detects invalid fix_ladder_position values."""

    def test_invalid_fix_ladder_position_returns_errors(self):
        """validate_state should flag a fix_ladder_position not in FIX_LADDER_POSITIONS."""
        state_dict = _make_minimal_state_dict(
            stage="3",
            sub_stage=None,
            fix_ladder_position="nonexistent_position",
        )
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0
        error_text = " ".join(errors).lower()
        assert "fix_ladder" in error_text or "invalid" in error_text


# ===========================================================================
# Gap 3: validate_state with invalid debug_session phase/classification
# ===========================================================================


class TestValidateStateInvalidDebugSession:
    """Verify validate_state detects invalid DebugSession field values."""

    def test_invalid_debug_session_phase(self):
        """validate_state should flag an invalid phase on the debug_session."""
        ds_dict = _make_debug_session_dict(phase="totally_bogus_phase")
        state_dict = _make_minimal_state_dict(
            stage="3",
            sub_stage=None,
            debug_session=ds_dict,
        )
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0
        error_text = " ".join(errors).lower()
        assert "phase" in error_text or "debug_session" in error_text

    def test_invalid_debug_session_classification(self):
        """validate_state should flag an invalid classification on debug_session."""
        ds_dict = _make_debug_session_dict(classification="unknown_classification")
        state_dict = _make_minimal_state_dict(
            stage="3",
            sub_stage=None,
            debug_session=ds_dict,
        )
        state = PipelineState.from_dict(state_dict)
        errors = validate_state(state)
        assert len(errors) > 0
        error_text = " ".join(errors).lower()
        assert "classification" in error_text or "debug_session" in error_text


# ===========================================================================
# Gap 4: load_state ValueError message format
# ===========================================================================


class TestLoadStateValueErrorFormat:
    """Verify load_state ValueError message includes 'Invalid state:' prefix."""

    def test_load_state_valueerror_message_contains_invalid_state(self, tmp_path):
        """Blueprint: ValueError 'Invalid state: {details}' on structural problems.

        The load_state function should raise ValueError with a message
        starting with or containing 'Invalid state:'.
        """
        state_dict = _make_minimal_state_dict(stage="COMPLETELY_INVALID")
        _write_state_json(tmp_path, state_dict)

        with pytest.raises(ValueError, match="Invalid state"):
            load_state(tmp_path)


# ===========================================================================
# Gap 5: recover_state_from_markers - stage for blueprint-only approval
# ===========================================================================


class TestRecoverStateStageValues:
    """Verify recovered state has the correct stage for different marker combinations."""

    def test_blueprint_approval_recovers_to_pre_stage_3_or_later(self, tmp_path):
        """With both stakeholder + blueprint approved, stage should be at least pre_stage_3.

        Blueprint says recovery constructs the most conservative state consistent
        with the markers found. Blueprint approval indicates Stage 2 is complete.
        """
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

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        # Blueprint approved means at least past stage 2
        stage_index = STAGES.index(result.stage)
        assert stage_index >= STAGES.index("pre_stage_3")

    def test_unit_markers_recovers_to_stage_3(self, tmp_path):
        """With unit verified markers, stage should be '3'."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder.md").write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text(
            "# Blueprint\n<!-- SVP_APPROVED: blueprint -->\n",
            encoding="utf-8",
        )

        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        (markers_dir / "unit_1_verified").mkdir()
        (markers_dir / "unit_2_verified").mkdir()

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert result.stage == "3"

    def test_unit_markers_sets_current_unit_to_next(self, tmp_path):
        """With units 1-3 verified, current_unit should be 4 (next unit to work on).

        Blueprint: recovery constructs the most conservative valid state
        consistent with markers found.
        """
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder.md").write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text(
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
        assert result.stage == "3"
        # Next unit after highest verified (3) should be 4
        assert result.current_unit == 4

    def test_unit_markers_populates_verified_units(self, tmp_path):
        """Recovered state's verified_units should contain all verified unit markers."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder.md").write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text(
            "# Blueprint\n<!-- SVP_APPROVED: blueprint -->\n",
            encoding="utf-8",
        )

        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        (markers_dir / "unit_1_verified").mkdir()
        (markers_dir / "unit_2_verified").mkdir()

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        # Should have 2 verified units
        assert len(result.verified_units) == 2
        unit_numbers = [vu["unit"] for vu in result.verified_units]
        assert 1 in unit_numbers
        assert 2 in unit_numbers


# ===========================================================================
# Gap 6: create_initial_state log_references and last_action defaults
# ===========================================================================


class TestCreateInitialStateDefaults:
    """Verify create_initial_state sets log_references and last_action correctly."""

    def test_initial_log_references_empty(self):
        """create_initial_state should set log_references to an empty dict."""
        result = create_initial_state("test_project")
        assert result.log_references == {}

    def test_initial_last_action_is_none(self):
        """create_initial_state should set last_action to None."""
        result = create_initial_state("test_project")
        assert result.last_action is None


# ===========================================================================
# Gap 7: save_state atomic write - no temp files left behind
# ===========================================================================


class TestSaveStateAtomicWrite:
    """Verify save_state uses atomic write pattern (temp file + rename)."""

    def test_no_temp_files_left_after_save(self, tmp_path):
        """After a successful save_state, no temporary files should remain.

        Blueprint: save_state atomically writes (write to temp file, rename).
        After success, only pipeline_state.json should exist from the save.
        """
        state = create_initial_state("atomic_test")
        save_state(state, tmp_path)

        # List all files in tmp_path
        files = list(tmp_path.iterdir())
        file_names = [f.name for f in files]

        # pipeline_state.json should exist
        assert "pipeline_state.json" in file_names

        # No leftover temp files (files starting with .pipeline_state_ or ending in .tmp)
        temp_files = [f for f in file_names if f.startswith(".pipeline_state_") or f.endswith(".tmp")]
        assert len(temp_files) == 0, f"Temp files left behind: {temp_files}"


# ===========================================================================
# Gap 8: stakeholder-only recovery stage constraint
# ===========================================================================


class TestRecoverStakeholderOnlyStage:
    """Verify stakeholder-only recovery sets an appropriate stage."""

    def test_stakeholder_only_recovers_to_stage_2(self, tmp_path):
        """With only stakeholder approved, recovery should be at stage 2.

        Blueprint: conservative state -- stakeholder approval means stage 1
        is done, so the conservative next stage is 2.
        """
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder.md").write_text(
            "# Spec\n<!-- SVP_APPROVED: stakeholder_spec -->\n",
            encoding="utf-8",
        )

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert result.stage == "2"
