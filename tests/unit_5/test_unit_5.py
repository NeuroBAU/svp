"""
Test suite for Unit 5: Pipeline State.

Synthetic data assumptions:
- Project roots are created as temporary directories via tmp_path fixtures.
- pipeline_state.json files are written with known JSON content for load/save tests.
- The ARTIFACT_FILENAMES["pipeline_state"] value from Unit 1 is used for file
  resolution; tests access it via the Unit 1 stub import.
- PipelineState field values use synthetic but contract-compliant data:
  stages drawn from VALID_STAGES, sub-stages from VALID_SUB_STAGES, etc.
- A "minimal valid state" fixture provides all required fields at their simplest
  contract-compliant values (stage "0", sub_stage "hook_activation", etc.).
- A "full state" fixture exercises every field with non-default values.
- SHA-256 hashes in save_state tests are computed over the raw bytes of the
  previous pipeline_state.json file, per the contract (Bug S3-1, S3-5 clarification).
- The "pass" JSON key is renamed to "pass_" in Python per the blueprint contract.
- debug_session dicts use synthetic but schema-compliant keys and values.
- Oracle fields use synthetic values within VALID_ORACLE_PHASES constraints.
- deferred_broken_units uses small integer lists representing unit indices.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from svp_config import ARTIFACT_FILENAMES
from pipeline_state import (
    VALID_DEBUG_PHASES,
    VALID_FIX_LADDER_POSITIONS,
    VALID_ORACLE_PHASES,
    VALID_STAGES,
    VALID_SUB_STAGES,
    PipelineState,
    load_state,
    save_state,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state_path(project_root: Path) -> Path:
    """Return the canonical pipeline_state.json path for a project root."""
    return project_root / ARTIFACT_FILENAMES["pipeline_state"]


def _minimal_state_dict() -> Dict[str, Any]:
    """A minimal valid state dict with all required fields."""
    return {
        "stage": "0",
        "sub_stage": "hook_activation",
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }


def _full_state_dict() -> Dict[str, Any]:
    """A state dict exercising every field with non-default/non-None values."""
    return {
        "stage": "3",
        "sub_stage": "implementation",
        "current_unit": 5,
        "total_units": 29,
        "verified_units": [
            {"unit": 1, "status": "passed"},
            {"unit": 2, "status": "passed"},
        ],
        "alignment_iterations": 3,
        "fix_ladder_position": "diagnostic",
        "red_run_retries": 2,
        "pass_history": [
            {"pass": 1, "units_completed": 20},
        ],
        "debug_session": {
            "authorized": True,
            "bug_number": 42,
            "classification": "single_unit",
            "affected_units": [5],
            "phase": "repair",
            "repair_retry_count": 1,
            "triage_refinement_count": 0,
            "ledger_path": "/tmp/ledger.json",
        },
        "debug_history": [
            {"bug_number": 10, "resolution": "fixed"},
        ],
        "redo_triggered_from": {"stage": "2", "reason": "profile_change"},
        "delivered_repo_path": "/tmp/delivered_repo",
        "primary_language": "rust",
        "component_languages": ["python", "javascript"],
        "secondary_language": "python",
        "oracle_session_active": True,
        "oracle_test_project": "/tmp/oracle_project",
        "oracle_phase": "gate_a",
        "oracle_run_count": 3,
        "oracle_nested_session_path": "/tmp/oracle_session",
        "state_hash": "abc123def456",
        "spec_revision_count": 2,
        "pass": 2,
        "pass2_nested_session_path": "/tmp/pass2_session",
        "deferred_broken_units": [7, 12],
    }


def _write_state_file(project_root: Path, state_dict: Dict[str, Any]) -> Path:
    """Write a pipeline_state.json file and return its path."""
    path = _state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state_dict, indent=2))
    return path


def _stage3_with_unit_dict() -> Dict[str, Any]:
    """A state dict in Stage 3 with current_unit set (co-invariant valid)."""
    d = _minimal_state_dict()
    d["stage"] = "3"
    d["sub_stage"] = "stub_generation"
    d["current_unit"] = 1
    return d


# ---------------------------------------------------------------------------
# VALID_STAGES
# ---------------------------------------------------------------------------


class TestValidStages:
    """Tests for the VALID_STAGES module-level constant."""

    def test_valid_stages_is_a_set(self):
        assert isinstance(VALID_STAGES, set)

    def test_valid_stages_contains_stage_0(self):
        assert "0" in VALID_STAGES

    def test_valid_stages_contains_stage_1(self):
        assert "1" in VALID_STAGES

    def test_valid_stages_contains_stage_2(self):
        assert "2" in VALID_STAGES

    def test_valid_stages_contains_pre_stage_3(self):
        assert "pre_stage_3" in VALID_STAGES

    def test_valid_stages_contains_stage_3(self):
        assert "3" in VALID_STAGES

    def test_valid_stages_contains_stage_4(self):
        assert "4" in VALID_STAGES

    def test_valid_stages_contains_stage_5(self):
        assert "5" in VALID_STAGES

    def test_valid_stages_exact_membership(self):
        expected = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}
        assert VALID_STAGES == expected

    def test_valid_stages_all_elements_are_strings(self):
        for stage in VALID_STAGES:
            assert isinstance(stage, str)


# ---------------------------------------------------------------------------
# VALID_SUB_STAGES
# ---------------------------------------------------------------------------


class TestValidSubStages:
    """Tests for the VALID_SUB_STAGES module-level constant."""

    def test_valid_sub_stages_is_a_dict(self):
        assert isinstance(VALID_SUB_STAGES, dict)

    def test_valid_sub_stages_keys_match_valid_stages(self):
        assert set(VALID_SUB_STAGES.keys()) == VALID_STAGES

    def test_valid_sub_stages_stage_0_values(self):
        expected = {
            "hook_activation",
            "project_context",
            "project_profile",
            "toolchain_provisioning",
        }
        assert VALID_SUB_STAGES["0"] == expected

    def test_valid_sub_stages_includes_toolchain_provisioning(self):
        """Bug S3-176: Stage 0 sub_stages MUST include the new
        'toolchain_provisioning' sub_stage that hosts env-create + verify
        between gate_0_3 PROFILE APPROVED and Stage 1."""
        assert "toolchain_provisioning" in VALID_SUB_STAGES["0"]

    def test_valid_sub_stages_stage_1_values(self):
        expected = {None, "checklist_generation"}
        assert VALID_SUB_STAGES["1"] == expected

    def test_valid_sub_stages_stage_2_values(self):
        expected = {"blueprint_dialog", "alignment_check", "alignment_confirmed"}
        assert VALID_SUB_STAGES["2"] == expected

    def test_valid_sub_stages_pre_stage_3_values(self):
        expected = {None}
        assert VALID_SUB_STAGES["pre_stage_3"] == expected

    def test_valid_sub_stages_stage_3_values(self):
        expected = {
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
        }
        assert VALID_SUB_STAGES["3"] == expected

    def test_valid_sub_stages_stage_4_values(self):
        expected = {None, "regression_adaptation", "gate_4_1", "gate_4_1a", "gate_4_2"}
        assert VALID_SUB_STAGES["4"] == expected

    def test_valid_sub_stages_stage_5_values(self):
        expected = {None, "repo_test", "compliance_scan", "repo_complete", "gate_5_2", "gate_5_3"}
        assert VALID_SUB_STAGES["5"] == expected

    def test_valid_sub_stages_values_are_sets(self):
        for stage, sub_stages in VALID_SUB_STAGES.items():
            assert isinstance(sub_stages, set), (
                f"Sub-stages for stage '{stage}' is not a set"
            )


# ---------------------------------------------------------------------------
# VALID_FIX_LADDER_POSITIONS
# ---------------------------------------------------------------------------


class TestValidFixLadderPositions:
    """Tests for the VALID_FIX_LADDER_POSITIONS module-level constant."""

    def test_valid_fix_ladder_positions_is_a_list(self):
        assert isinstance(VALID_FIX_LADDER_POSITIONS, list)

    def test_valid_fix_ladder_positions_exact_values(self):
        expected = [None, "fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"]
        assert VALID_FIX_LADDER_POSITIONS == expected

    def test_valid_fix_ladder_positions_first_is_none(self):
        assert VALID_FIX_LADDER_POSITIONS[0] is None

    def test_valid_fix_ladder_positions_last_is_exhausted(self):
        assert VALID_FIX_LADDER_POSITIONS[-1] == "exhausted"

    def test_valid_fix_ladder_positions_length_is_five(self):
        assert len(VALID_FIX_LADDER_POSITIONS) == 5


# ---------------------------------------------------------------------------
# VALID_DEBUG_PHASES
# ---------------------------------------------------------------------------


class TestValidDebugPhases:
    """Tests for the VALID_DEBUG_PHASES module-level constant."""

    def test_valid_debug_phases_is_a_set(self):
        assert isinstance(VALID_DEBUG_PHASES, set)

    def test_valid_debug_phases_exact_membership(self):
        expected = {
            "triage",
            "repair",
            "regression_test",
            "lessons_learned",
            "reassembly",
            "stage3_reentry",
            "stage3_rebuild_active",
            "commit",
        }
        assert VALID_DEBUG_PHASES == expected

    def test_valid_debug_phases_contains_triage(self):
        assert "triage" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_contains_repair(self):
        assert "repair" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_contains_regression_test(self):
        assert "regression_test" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_contains_lessons_learned(self):
        assert "lessons_learned" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_contains_reassembly(self):
        assert "reassembly" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_contains_stage3_reentry(self):
        assert "stage3_reentry" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_contains_commit(self):
        assert "commit" in VALID_DEBUG_PHASES

    def test_valid_debug_phases_all_elements_are_strings(self):
        for phase in VALID_DEBUG_PHASES:
            assert isinstance(phase, str)


# ---------------------------------------------------------------------------
# VALID_ORACLE_PHASES
# ---------------------------------------------------------------------------


class TestValidOraclePhases:
    """Tests for the VALID_ORACLE_PHASES module-level constant."""

    def test_valid_oracle_phases_is_a_set(self):
        assert isinstance(VALID_ORACLE_PHASES, set)

    def test_valid_oracle_phases_exact_membership(self):
        expected = {None, "dry_run", "gate_a", "green_run", "gate_b", "exit"}
        assert VALID_ORACLE_PHASES == expected

    def test_valid_oracle_phases_contains_none(self):
        assert None in VALID_ORACLE_PHASES

    def test_valid_oracle_phases_contains_dry_run(self):
        assert "dry_run" in VALID_ORACLE_PHASES

    def test_valid_oracle_phases_contains_gate_a(self):
        assert "gate_a" in VALID_ORACLE_PHASES

    def test_valid_oracle_phases_contains_green_run(self):
        assert "green_run" in VALID_ORACLE_PHASES

    def test_valid_oracle_phases_contains_gate_b(self):
        assert "gate_b" in VALID_ORACLE_PHASES

    def test_valid_oracle_phases_contains_exit(self):
        assert "exit" in VALID_ORACLE_PHASES


# ---------------------------------------------------------------------------
# PipelineState — class structure
# ---------------------------------------------------------------------------


class TestPipelineStateClassStructure:
    """Tests for PipelineState class field existence and types."""

    def test_pipeline_state_has_stage_attribute(self):
        state = PipelineState()
        assert hasattr(state, "stage")

    def test_pipeline_state_has_sub_stage_attribute(self):
        state = PipelineState()
        assert hasattr(state, "sub_stage")

    def test_pipeline_state_has_current_unit_attribute(self):
        state = PipelineState()
        assert hasattr(state, "current_unit")

    def test_pipeline_state_has_total_units_attribute(self):
        state = PipelineState()
        assert hasattr(state, "total_units")

    def test_pipeline_state_has_verified_units_attribute(self):
        state = PipelineState()
        assert hasattr(state, "verified_units")

    def test_pipeline_state_has_alignment_iterations_attribute(self):
        state = PipelineState()
        assert hasattr(state, "alignment_iterations")

    def test_pipeline_state_has_fix_ladder_position_attribute(self):
        state = PipelineState()
        assert hasattr(state, "fix_ladder_position")

    def test_pipeline_state_has_red_run_retries_attribute(self):
        state = PipelineState()
        assert hasattr(state, "red_run_retries")

    def test_pipeline_state_has_pass_history_attribute(self):
        state = PipelineState()
        assert hasattr(state, "pass_history")

    def test_pipeline_state_has_debug_session_attribute(self):
        state = PipelineState()
        assert hasattr(state, "debug_session")

    def test_pipeline_state_has_debug_history_attribute(self):
        state = PipelineState()
        assert hasattr(state, "debug_history")

    def test_pipeline_state_has_redo_triggered_from_attribute(self):
        state = PipelineState()
        assert hasattr(state, "redo_triggered_from")

    def test_pipeline_state_has_delivered_repo_path_attribute(self):
        state = PipelineState()
        assert hasattr(state, "delivered_repo_path")

    def test_pipeline_state_has_primary_language_attribute(self):
        state = PipelineState()
        assert hasattr(state, "primary_language")

    def test_pipeline_state_has_component_languages_attribute(self):
        state = PipelineState()
        assert hasattr(state, "component_languages")

    def test_pipeline_state_has_secondary_language_attribute(self):
        state = PipelineState()
        assert hasattr(state, "secondary_language")

    def test_pipeline_state_has_oracle_session_active_attribute(self):
        state = PipelineState()
        assert hasattr(state, "oracle_session_active")

    def test_pipeline_state_has_oracle_test_project_attribute(self):
        state = PipelineState()
        assert hasattr(state, "oracle_test_project")

    def test_pipeline_state_has_oracle_phase_attribute(self):
        state = PipelineState()
        assert hasattr(state, "oracle_phase")

    def test_pipeline_state_has_oracle_run_count_attribute(self):
        state = PipelineState()
        assert hasattr(state, "oracle_run_count")

    def test_pipeline_state_has_oracle_nested_session_path_attribute(self):
        state = PipelineState()
        assert hasattr(state, "oracle_nested_session_path")

    def test_pipeline_state_has_state_hash_attribute(self):
        state = PipelineState()
        assert hasattr(state, "state_hash")

    def test_pipeline_state_has_spec_revision_count_attribute(self):
        state = PipelineState()
        assert hasattr(state, "spec_revision_count")

    def test_pipeline_state_has_pass_underscore_attribute(self):
        state = PipelineState()
        assert hasattr(state, "pass_")

    def test_pipeline_state_has_pass2_nested_session_path_attribute(self):
        state = PipelineState()
        assert hasattr(state, "pass2_nested_session_path")

    def test_pipeline_state_has_deferred_broken_units_attribute(self):
        state = PipelineState()
        assert hasattr(state, "deferred_broken_units")


# ---------------------------------------------------------------------------
# PipelineState — pass_ field serialization
# ---------------------------------------------------------------------------


class TestPipelineStatePassFieldSerialization:
    """Tests that the pass_ field serializes as 'pass' in JSON and deserializes
    back to pass_ in Python."""

    def test_pass_field_valid_values_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["pass"] = None
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.pass_ is None

    def test_pass_field_valid_value_1(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["pass"] = 1
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.pass_ == 1

    def test_pass_field_valid_value_2(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["pass"] = 2
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.pass_ == 2

    def test_pass_field_round_trip_serialization(self, tmp_path):
        """Load a state with pass=2, save it, and verify the JSON uses 'pass' key."""
        state_dict = _minimal_state_dict()
        state_dict["pass"] = 2
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.pass_ == 2
        save_state(tmp_path, state)
        raw = json.loads(_state_path(tmp_path).read_text())
        assert "pass" in raw
        assert raw["pass"] == 2
        # The Python attribute name "pass_" should NOT appear in JSON
        assert "pass_" not in raw


# ---------------------------------------------------------------------------
# load_state — basic behavior
# ---------------------------------------------------------------------------


class TestLoadStateBasic:
    """Tests for load_state reading pipeline_state.json and constructing PipelineState."""

    def test_load_state_returns_pipeline_state(self, tmp_path):
        _write_state_file(tmp_path, _minimal_state_dict())
        result = load_state(tmp_path)
        assert isinstance(result, PipelineState)

    def test_load_state_reads_from_artifact_filenames_path(self, tmp_path):
        """load_state must use ARTIFACT_FILENAMES['pipeline_state'] for file path."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.stage == "0"

    def test_load_state_raises_file_not_found_when_absent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_state(tmp_path)

    def test_load_state_stage_field(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["stage"] = "3"
        state_dict["sub_stage"] = "implementation"
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.stage == "3"

    def test_load_state_sub_stage_field(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.sub_stage == "hook_activation"

    def test_load_state_current_unit_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.current_unit is None

    def test_load_state_current_unit_set(self, tmp_path):
        state_dict = _stage3_with_unit_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.current_unit == 1

    def test_load_state_total_units(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["total_units"] = 29
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.total_units == 29

    def test_load_state_verified_units_empty_list(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.verified_units == []

    def test_load_state_verified_units_with_entries(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["verified_units"] = [{"unit": 1, "status": "passed"}]
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert len(result.verified_units) == 1
        assert result.verified_units[0]["unit"] == 1

    def test_load_state_alignment_iterations(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["alignment_iterations"] = 5
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.alignment_iterations == 5

    def test_load_state_fix_ladder_position_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.fix_ladder_position is None

    def test_load_state_fix_ladder_position_set(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["fix_ladder_position"] = "diagnostic"
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.fix_ladder_position == "diagnostic"

    def test_load_state_red_run_retries(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["red_run_retries"] = 3
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.red_run_retries == 3

    def test_load_state_pass_history(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["pass_history"] = [{"pass": 1, "summary": "done"}]
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert len(result.pass_history) == 1

    def test_load_state_debug_session_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.debug_session is None

    def test_load_state_debug_session_populated(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.debug_session is not None
        assert result.debug_session["authorized"] is True
        assert result.debug_session["bug_number"] == 42

    def test_load_state_debug_history(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert len(result.debug_history) == 1

    def test_load_state_redo_triggered_from_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.redo_triggered_from is None

    def test_load_state_redo_triggered_from_populated(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.redo_triggered_from is not None
        assert result.redo_triggered_from["stage"] == "2"

    def test_load_state_delivered_repo_path(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.delivered_repo_path == "/tmp/delivered_repo"

    def test_load_state_primary_language(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.primary_language == "rust"

    def test_load_state_component_languages(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.component_languages == ["python", "javascript"]

    def test_load_state_secondary_language(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.secondary_language == "python"

    def test_load_state_oracle_session_active(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_session_active is True

    def test_load_state_oracle_test_project(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_test_project == "/tmp/oracle_project"

    def test_load_state_oracle_phase(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_phase == "gate_a"

    def test_load_state_oracle_run_count(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_run_count == 3

    def test_load_state_oracle_nested_session_path(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_nested_session_path == "/tmp/oracle_session"

    def test_load_state_state_hash(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.state_hash == "abc123def456"

    def test_load_state_spec_revision_count(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.spec_revision_count == 2

    def test_load_state_pass2_nested_session_path(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.pass2_nested_session_path == "/tmp/pass2_session"

    def test_load_state_deferred_broken_units(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.deferred_broken_units == [7, 12]


# ---------------------------------------------------------------------------
# load_state — SVP 2.2 field defaults for missing keys
# ---------------------------------------------------------------------------


class TestLoadStateDefaults:
    """Tests that load_state applies correct defaults for missing SVP 2.2 fields."""

    def _legacy_state_dict(self) -> Dict[str, Any]:
        """A state dict missing all SVP 2.2 fields (simulating a legacy file)."""
        return {
            "stage": "1",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
        }

    def test_default_primary_language_is_python(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.primary_language == "python"

    def test_default_component_languages_is_empty_list(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.component_languages == []

    def test_default_secondary_language_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.secondary_language is None

    def test_default_oracle_session_active_is_false(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.oracle_session_active is False

    def test_default_oracle_test_project_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.oracle_test_project is None

    def test_default_oracle_phase_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.oracle_phase is None

    def test_default_oracle_run_count_is_0(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.oracle_run_count == 0

    def test_default_oracle_nested_session_path_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.oracle_nested_session_path is None

    def test_default_state_hash_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.state_hash is None

    def test_default_spec_revision_count_is_0(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.spec_revision_count == 0

    def test_default_pass_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.pass_ is None

    def test_default_pass2_nested_session_path_is_none(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.pass2_nested_session_path is None

    def test_default_deferred_broken_units_is_empty_list(self, tmp_path):
        _write_state_file(tmp_path, self._legacy_state_dict())
        result = load_state(tmp_path)
        assert result.deferred_broken_units == []

    def test_explicit_values_override_defaults(self, tmp_path):
        """When fields are present in JSON, their values must not be overridden
        by defaults."""
        state_dict = self._legacy_state_dict()
        state_dict["primary_language"] = "rust"
        state_dict["oracle_run_count"] = 5
        state_dict["spec_revision_count"] = 3
        state_dict["deferred_broken_units"] = [1, 2]
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.primary_language == "rust"
        assert result.oracle_run_count == 5
        assert result.spec_revision_count == 3
        assert result.deferred_broken_units == [1, 2]


# ---------------------------------------------------------------------------
# load_state — full round-trip with all fields
# ---------------------------------------------------------------------------


class TestLoadStateFullRoundTrip:
    """Tests that load_state correctly reads every field from a fully-populated file."""

    def test_load_full_state_all_fields_match(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.stage == "3"
        assert result.sub_stage == "implementation"
        assert result.current_unit == 5
        assert result.total_units == 29
        assert len(result.verified_units) == 2
        assert result.alignment_iterations == 3
        assert result.fix_ladder_position == "diagnostic"
        assert result.red_run_retries == 2
        assert len(result.pass_history) == 1
        assert result.debug_session["bug_number"] == 42
        assert len(result.debug_history) == 1
        assert result.redo_triggered_from["stage"] == "2"
        assert result.delivered_repo_path == "/tmp/delivered_repo"
        assert result.primary_language == "rust"
        assert result.component_languages == ["python", "javascript"]
        assert result.secondary_language == "python"
        assert result.oracle_session_active is True
        assert result.oracle_test_project == "/tmp/oracle_project"
        assert result.oracle_phase == "gate_a"
        assert result.oracle_run_count == 3
        assert result.oracle_nested_session_path == "/tmp/oracle_session"
        assert result.state_hash == "abc123def456"
        assert result.spec_revision_count == 2
        assert result.pass_ == 2
        assert result.pass2_nested_session_path == "/tmp/pass2_session"
        assert result.deferred_broken_units == [7, 12]


# ---------------------------------------------------------------------------
# save_state — basic behavior
# ---------------------------------------------------------------------------


class TestSaveStateBasic:
    """Tests for save_state writing pipeline_state.json."""

    def test_save_state_creates_file(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        assert _state_path(tmp_path).exists()

    def test_save_state_returns_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        result = save_state(tmp_path, state)
        assert result is None

    def test_save_state_writes_valid_json(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        content = _state_path(tmp_path).read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_save_state_writes_formatted_json(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        content = _state_path(tmp_path).read_text()
        assert "\n" in content

    def test_save_state_preserves_stage(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["stage"] = "2"
        state_dict["sub_stage"] = "blueprint_dialog"
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["stage"] == "2"

    def test_save_state_preserves_all_fields(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["stage"] == "3"
        assert raw["sub_stage"] == "implementation"
        assert raw["current_unit"] == 5
        assert raw["total_units"] == 29
        assert raw["primary_language"] == "rust"
        assert raw["component_languages"] == ["python", "javascript"]
        assert raw["secondary_language"] == "python"
        assert raw["oracle_session_active"] is True
        assert raw["oracle_phase"] == "gate_a"
        assert raw["oracle_run_count"] == 3
        assert raw["spec_revision_count"] == 2
        assert raw["pass"] == 2
        assert raw["deferred_broken_units"] == [7, 12]

    def test_save_state_overwrites_existing_file(self, tmp_path):
        state_dict_v1 = _minimal_state_dict()
        state_dict_v1["stage"] = "0"
        state_dict_v1["sub_stage"] = "hook_activation"
        _write_state_file(tmp_path, state_dict_v1)
        state_v1 = load_state(tmp_path)

        # Mutate and save
        state_v1.stage = "1"
        state_v1.sub_stage = None
        state_v1.current_unit = None
        save_state(tmp_path, state_v1)

        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["stage"] == "1"

    def test_save_state_pass_field_serialized_as_pass_not_pass_underscore(
        self, tmp_path
    ):
        state_dict = _minimal_state_dict()
        state_dict["pass"] = 1
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        raw = json.loads(_state_path(tmp_path).read_text())
        assert "pass" in raw
        assert "pass_" not in raw


# ---------------------------------------------------------------------------
# save_state — current_unit/sub_stage co-invariant
# ---------------------------------------------------------------------------


class TestSaveStateCoInvariant:
    """Tests for the current_unit/sub_stage co-invariant validation in save_state.
    When current_unit is non-null, sub_stage must be non-null."""

    def test_save_state_raises_value_error_when_current_unit_set_and_sub_stage_none(
        self, tmp_path
    ):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        state.current_unit = 1
        state.sub_stage = None
        with pytest.raises(ValueError):
            save_state(tmp_path, state)

    def test_save_state_allows_current_unit_none_with_sub_stage_none(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["stage"] = "1"
        state_dict["sub_stage"] = None
        state_dict["current_unit"] = None
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        # Should not raise
        save_state(tmp_path, state)

    def test_save_state_allows_current_unit_set_with_sub_stage_set(self, tmp_path):
        state_dict = _stage3_with_unit_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        # Should not raise
        save_state(tmp_path, state)

    def test_save_state_allows_current_unit_none_with_sub_stage_set(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["stage"] = "0"
        state_dict["sub_stage"] = "hook_activation"
        state_dict["current_unit"] = None
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        # Should not raise: current_unit is None, so co-invariant is trivially satisfied
        save_state(tmp_path, state)

    def test_save_state_co_invariant_error_message_is_descriptive(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        state.current_unit = 5
        state.sub_stage = None
        with pytest.raises(ValueError) as exc_info:
            save_state(tmp_path, state)
        # The error message should be descriptive (not empty)
        assert len(str(exc_info.value)) > 0


# ---------------------------------------------------------------------------
# save_state — state_hash (SHA-256 of previous file)
# ---------------------------------------------------------------------------


class TestSaveStateHash:
    """Tests for save_state computing state_hash as SHA-256 of the previous file."""

    def test_first_save_state_hash_is_none(self, tmp_path):
        """If no prior file exists, state_hash should be None after save."""
        state = PipelineState()
        state.stage = "0"
        state.sub_stage = "hook_activation"
        state.current_unit = None
        state.total_units = 10
        state.verified_units = []
        state.alignment_iterations = 0
        state.fix_ladder_position = None
        state.red_run_retries = 0
        state.pass_history = []
        state.debug_session = None
        state.debug_history = []
        state.redo_triggered_from = None
        state.delivered_repo_path = None
        state.primary_language = "python"
        state.component_languages = []
        state.secondary_language = None
        state.oracle_session_active = False
        state.oracle_test_project = None
        state.oracle_phase = None
        state.oracle_run_count = 0
        state.oracle_nested_session_path = None
        state.state_hash = None
        state.spec_revision_count = 0
        state.pass_ = None
        state.pass2_nested_session_path = None
        state.deferred_broken_units = []

        # Ensure no prior file exists
        state_path = _state_path(tmp_path)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        assert not state_path.exists()

        save_state(tmp_path, state)
        raw = json.loads(state_path.read_text())
        assert raw["state_hash"] is None

    def test_second_save_state_hash_is_sha256_of_first_file(self, tmp_path):
        """After saving twice, the second file's state_hash should be
        the SHA-256 hex digest of the first file's raw bytes."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)

        # Read the raw bytes of the current file BEFORE save
        first_file_bytes = _state_path(tmp_path).read_bytes()
        expected_hash = hashlib.sha256(first_file_bytes).hexdigest()

        save_state(tmp_path, state)
        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["state_hash"] == expected_hash

    def test_state_hash_changes_when_file_content_changes(self, tmp_path):
        """Two successive saves with different content should yield different hashes."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)

        # Read hash from first save
        raw_after_first = json.loads(_state_path(tmp_path).read_text())
        hash_after_first = raw_after_first["state_hash"]

        # Modify state and save again
        state_after_first = load_state(tmp_path)
        state_after_first.alignment_iterations = 99
        save_state(tmp_path, state_after_first)

        raw_after_second = json.loads(_state_path(tmp_path).read_text())
        hash_after_second = raw_after_second["state_hash"]

        # Hashes should differ because the underlying file content changed
        assert hash_after_first != hash_after_second

    def test_state_hash_is_hex_string(self, tmp_path):
        """state_hash should be a valid hex string (SHA-256 = 64 hex chars)."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)

        raw = json.loads(_state_path(tmp_path).read_text())
        state_hash = raw["state_hash"]
        assert isinstance(state_hash, str)
        assert len(state_hash) == 64
        # Should be valid hex
        int(state_hash, 16)

    def test_state_hash_is_of_previous_file_not_current(self, tmp_path):
        """The hash stored in the file is of the previous file, not self-referential.
        Verify by computing hash of the file before save and comparing."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)

        pre_save_bytes = _state_path(tmp_path).read_bytes()
        expected_hash = hashlib.sha256(pre_save_bytes).hexdigest()

        state = load_state(tmp_path)
        save_state(tmp_path, state)

        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["state_hash"] == expected_hash

        # Also verify it is NOT the hash of the current file content
        current_bytes = _state_path(tmp_path).read_bytes()
        current_hash = hashlib.sha256(current_bytes).hexdigest()
        assert raw["state_hash"] != current_hash

    def test_state_hash_stored_in_pipeline_state_object_after_save(self, tmp_path):
        """After save_state, the state object's state_hash should reflect the
        hash that was written (i.e., the hash of the previous file)."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)

        pre_save_bytes = _state_path(tmp_path).read_bytes()
        expected_hash = hashlib.sha256(pre_save_bytes).hexdigest()

        state = load_state(tmp_path)
        save_state(tmp_path, state)

        # After save, state.state_hash should be the hash we computed
        assert state.state_hash == expected_hash


# ---------------------------------------------------------------------------
# save_state + load_state — round-trip integrity
# ---------------------------------------------------------------------------


class TestSaveLoadRoundTrip:
    """Tests that save_state then load_state preserves all field values."""

    def test_round_trip_minimal_state(self, tmp_path):
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)

        assert reloaded.stage == state.stage
        assert reloaded.sub_stage == state.sub_stage
        assert reloaded.current_unit == state.current_unit
        assert reloaded.total_units == state.total_units
        assert reloaded.verified_units == state.verified_units
        assert reloaded.alignment_iterations == state.alignment_iterations
        assert reloaded.fix_ladder_position == state.fix_ladder_position
        assert reloaded.red_run_retries == state.red_run_retries
        assert reloaded.pass_history == state.pass_history
        assert reloaded.debug_session == state.debug_session
        assert reloaded.debug_history == state.debug_history
        assert reloaded.redo_triggered_from == state.redo_triggered_from
        assert reloaded.delivered_repo_path == state.delivered_repo_path
        assert reloaded.primary_language == state.primary_language
        assert reloaded.component_languages == state.component_languages
        assert reloaded.secondary_language == state.secondary_language
        assert reloaded.oracle_session_active == state.oracle_session_active
        assert reloaded.oracle_test_project == state.oracle_test_project
        assert reloaded.oracle_phase == state.oracle_phase
        assert reloaded.oracle_run_count == state.oracle_run_count
        assert reloaded.oracle_nested_session_path == state.oracle_nested_session_path
        assert reloaded.spec_revision_count == state.spec_revision_count
        assert reloaded.pass_ == state.pass_
        assert reloaded.pass2_nested_session_path == state.pass2_nested_session_path
        assert reloaded.deferred_broken_units == state.deferred_broken_units

    def test_round_trip_full_state(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)

        assert reloaded.stage == state.stage
        assert reloaded.sub_stage == state.sub_stage
        assert reloaded.current_unit == state.current_unit
        assert reloaded.total_units == state.total_units
        assert reloaded.verified_units == state.verified_units
        assert reloaded.alignment_iterations == state.alignment_iterations
        assert reloaded.fix_ladder_position == state.fix_ladder_position
        assert reloaded.red_run_retries == state.red_run_retries
        assert reloaded.pass_history == state.pass_history
        assert reloaded.debug_session == state.debug_session
        assert reloaded.debug_history == state.debug_history
        assert reloaded.redo_triggered_from == state.redo_triggered_from
        assert reloaded.delivered_repo_path == state.delivered_repo_path
        assert reloaded.primary_language == state.primary_language
        assert reloaded.component_languages == state.component_languages
        assert reloaded.secondary_language == state.secondary_language
        assert reloaded.oracle_session_active == state.oracle_session_active
        assert reloaded.oracle_test_project == state.oracle_test_project
        assert reloaded.oracle_phase == state.oracle_phase
        assert reloaded.oracle_run_count == state.oracle_run_count
        assert reloaded.oracle_nested_session_path == state.oracle_nested_session_path
        assert reloaded.spec_revision_count == state.spec_revision_count
        assert reloaded.pass_ == state.pass_
        assert reloaded.pass2_nested_session_path == state.pass2_nested_session_path
        assert reloaded.deferred_broken_units == state.deferred_broken_units

    def test_round_trip_debug_session_schema_preserved(self, tmp_path):
        """Verify all debug_session schema fields survive a round-trip."""
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)

        ds = reloaded.debug_session
        assert ds["authorized"] is True
        assert ds["bug_number"] == 42
        assert ds["classification"] == "single_unit"
        assert ds["affected_units"] == [5]
        assert ds["phase"] == "repair"
        assert ds["repair_retry_count"] == 1
        assert ds["triage_refinement_count"] == 0
        assert ds["ledger_path"] == "/tmp/ledger.json"


# ---------------------------------------------------------------------------
# debug_session schema
# ---------------------------------------------------------------------------


class TestDebugSessionSchema:
    """Tests for the debug_session dict schema as defined in contracts."""

    def test_debug_session_authorized_field(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert isinstance(state.debug_session["authorized"], bool)

    def test_debug_session_bug_number_field_int(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert isinstance(state.debug_session["bug_number"], int)

    def test_debug_session_bug_number_can_be_null(self, tmp_path):
        state_dict = _full_state_dict()
        state_dict["debug_session"]["bug_number"] = None
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.debug_session["bug_number"] is None

    def test_debug_session_classification_valid_values(self, tmp_path):
        valid_classifications = {"build_env", "single_unit", "cross_unit", None}
        for classification in valid_classifications:
            state_dict = _full_state_dict()
            state_dict["debug_session"]["classification"] = classification
            _write_state_file(tmp_path, state_dict)
            state = load_state(tmp_path)
            assert state.debug_session["classification"] in valid_classifications

    def test_debug_session_affected_units_is_list(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert isinstance(state.debug_session["affected_units"], list)

    def test_debug_session_affected_units_contains_ints(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        for unit in state.debug_session["affected_units"]:
            assert isinstance(unit, int)

    def test_debug_session_phase_in_valid_debug_phases(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.debug_session["phase"] in VALID_DEBUG_PHASES

    def test_debug_session_repair_retry_count_is_non_negative_int(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert isinstance(state.debug_session["repair_retry_count"], int)
        assert state.debug_session["repair_retry_count"] >= 0

    def test_debug_session_triage_refinement_count_is_non_negative_int(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert isinstance(state.debug_session["triage_refinement_count"], int)
        assert state.debug_session["triage_refinement_count"] >= 0

    def test_debug_session_ledger_path_is_string_or_null(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        ledger = state.debug_session["ledger_path"]
        assert isinstance(ledger, str) or ledger is None

    def test_debug_session_ledger_path_null(self, tmp_path):
        state_dict = _full_state_dict()
        state_dict["debug_session"]["ledger_path"] = None
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.debug_session["ledger_path"] is None

    def test_debug_session_all_required_keys_present(self, tmp_path):
        state_dict = _full_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        required_keys = {
            "authorized",
            "bug_number",
            "classification",
            "affected_units",
            "phase",
            "repair_retry_count",
            "triage_refinement_count",
            "ledger_path",
        }
        assert required_keys == set(state.debug_session.keys())

    def test_debug_session_each_phase_loads_correctly(self, tmp_path):
        """Test that each valid debug phase loads correctly from JSON."""
        for phase in VALID_DEBUG_PHASES:
            state_dict = _full_state_dict()
            state_dict["debug_session"]["phase"] = phase
            _write_state_file(tmp_path, state_dict)
            state = load_state(tmp_path)
            assert state.debug_session["phase"] == phase


# ---------------------------------------------------------------------------
# load_state uses ARTIFACT_FILENAMES for path resolution
# ---------------------------------------------------------------------------


class TestLoadStatePathResolution:
    """Tests that load_state uses ARTIFACT_FILENAMES['pipeline_state'] for file path."""

    def test_load_state_reads_from_correct_artifact_path(self, tmp_path):
        """The file must be at project_root / ARTIFACT_FILENAMES['pipeline_state']."""
        state_dict = _minimal_state_dict()
        artifact_path = tmp_path / ARTIFACT_FILENAMES["pipeline_state"]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(state_dict, indent=2))
        result = load_state(tmp_path)
        assert result.stage == "0"

    def test_save_state_writes_to_correct_artifact_path(self, tmp_path):
        """save_state must write to project_root / ARTIFACT_FILENAMES['pipeline_state']."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        expected_path = tmp_path / ARTIFACT_FILENAMES["pipeline_state"]
        assert expected_path.exists()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for load_state and save_state."""

    def test_load_state_with_empty_verified_units(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["verified_units"] = []
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.verified_units == []

    def test_load_state_with_empty_debug_history(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["debug_history"] = []
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.debug_history == []

    def test_load_state_with_empty_pass_history(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["pass_history"] = []
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.pass_history == []

    def test_load_state_with_empty_component_languages(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["component_languages"] = []
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.component_languages == []

    def test_load_state_with_empty_deferred_broken_units(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["deferred_broken_units"] = []
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.deferred_broken_units == []

    def test_save_state_with_multiple_deferred_broken_units(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["deferred_broken_units"] = [1, 3, 7, 15]
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)
        assert reloaded.deferred_broken_units == [1, 3, 7, 15]

    def test_save_state_with_multiple_component_languages(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["component_languages"] = ["python", "rust", "go"]
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)
        assert reloaded.component_languages == ["python", "rust", "go"]

    def test_load_state_preserves_list_ordering_in_verified_units(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["verified_units"] = [
            {"unit": 3, "status": "passed"},
            {"unit": 1, "status": "passed"},
            {"unit": 2, "status": "passed"},
        ]
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.verified_units[0]["unit"] == 3
        assert result.verified_units[1]["unit"] == 1
        assert result.verified_units[2]["unit"] == 2

    def test_save_state_co_invariant_validates_before_write(self, tmp_path):
        """Ensure the co-invariant check happens before any file modification."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        original_content = _state_path(tmp_path).read_text()

        state = load_state(tmp_path)
        state.current_unit = 5
        state.sub_stage = None

        with pytest.raises(ValueError):
            save_state(tmp_path, state)

        # File should not have been modified
        assert _state_path(tmp_path).read_text() == original_content

    def test_load_state_with_all_oracle_fields_populated(self, tmp_path):
        state_dict = _minimal_state_dict()
        state_dict["oracle_session_active"] = True
        state_dict["oracle_test_project"] = "/tmp/test_proj"
        state_dict["oracle_phase"] = "exit"
        state_dict["oracle_run_count"] = 10
        state_dict["oracle_nested_session_path"] = "/tmp/nested"
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_session_active is True
        assert result.oracle_test_project == "/tmp/test_proj"
        assert result.oracle_phase == "exit"
        assert result.oracle_run_count == 10
        assert result.oracle_nested_session_path == "/tmp/nested"

    def test_save_state_then_load_preserves_none_values(self, tmp_path):
        """Fields that are None should remain None through save/load cycle."""
        state_dict = _minimal_state_dict()
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)

        assert reloaded.current_unit is None
        assert reloaded.fix_ladder_position is None
        assert reloaded.debug_session is None
        assert reloaded.redo_triggered_from is None
        assert reloaded.delivered_repo_path is None
        assert reloaded.secondary_language is None
        assert reloaded.oracle_test_project is None
        assert reloaded.oracle_phase is None
        assert reloaded.oracle_nested_session_path is None
        assert reloaded.pass_ is None
        assert reloaded.pass2_nested_session_path is None

    def test_load_state_each_stage_loads_correctly(self, tmp_path):
        """Test that every valid stage string loads correctly."""
        for stage in VALID_STAGES:
            state_dict = _minimal_state_dict()
            state_dict["stage"] = stage
            # Set a valid sub_stage for this stage
            valid_subs = VALID_SUB_STAGES[stage]
            state_dict["sub_stage"] = next(iter(valid_subs))
            state_dict["current_unit"] = None
            _write_state_file(tmp_path, state_dict)
            result = load_state(tmp_path)
            assert result.stage == stage

    def test_load_state_each_fix_ladder_position_loads_correctly(self, tmp_path):
        """Test that every valid fix_ladder_position value loads correctly."""
        for position in VALID_FIX_LADDER_POSITIONS:
            state_dict = _minimal_state_dict()
            state_dict["fix_ladder_position"] = position
            _write_state_file(tmp_path, state_dict)
            result = load_state(tmp_path)
            assert result.fix_ladder_position == position

    def test_load_state_each_oracle_phase_loads_correctly(self, tmp_path):
        """Test that every valid oracle phase value loads correctly."""
        for phase in VALID_ORACLE_PHASES:
            state_dict = _minimal_state_dict()
            state_dict["oracle_phase"] = phase
            _write_state_file(tmp_path, state_dict)
            result = load_state(tmp_path)
            assert result.oracle_phase == phase

    def test_spec_revision_count_default_is_zero(self, tmp_path):
        """spec_revision_count defaults to 0, not None."""
        state_dict = _minimal_state_dict()
        del state_dict["spec_revision_count"]
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.spec_revision_count == 0
        assert isinstance(result.spec_revision_count, int)

    def test_oracle_run_count_default_is_zero(self, tmp_path):
        """oracle_run_count defaults to 0, not None."""
        state_dict = _minimal_state_dict()
        del state_dict["oracle_run_count"]
        _write_state_file(tmp_path, state_dict)
        result = load_state(tmp_path)
        assert result.oracle_run_count == 0
        assert isinstance(result.oracle_run_count, int)

    def test_multiple_save_cycles_hash_chain(self, tmp_path):
        """Three successive saves should form a hash chain:
        save1 hash = None (no prior), save2 hash = sha256(save1), save3 hash = sha256(save2)."""
        state = PipelineState()
        state.stage = "0"
        state.sub_stage = "hook_activation"
        state.current_unit = None
        state.total_units = 10
        state.verified_units = []
        state.alignment_iterations = 0
        state.fix_ladder_position = None
        state.red_run_retries = 0
        state.pass_history = []
        state.debug_session = None
        state.debug_history = []
        state.redo_triggered_from = None
        state.delivered_repo_path = None
        state.primary_language = "python"
        state.component_languages = []
        state.secondary_language = None
        state.oracle_session_active = False
        state.oracle_test_project = None
        state.oracle_phase = None
        state.oracle_run_count = 0
        state.oracle_nested_session_path = None
        state.state_hash = None
        state.spec_revision_count = 0
        state.pass_ = None
        state.pass2_nested_session_path = None
        state.deferred_broken_units = []

        state_path = _state_path(tmp_path)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # Save 1: no prior file
        save_state(tmp_path, state)
        raw1 = json.loads(state_path.read_text())
        assert raw1["state_hash"] is None

        # Save 2: hash of save 1
        bytes_after_save1 = state_path.read_bytes()
        expected_hash2 = hashlib.sha256(bytes_after_save1).hexdigest()
        state2 = load_state(tmp_path)
        state2.alignment_iterations = 1
        save_state(tmp_path, state2)
        raw2 = json.loads(state_path.read_text())
        assert raw2["state_hash"] == expected_hash2

        # Save 3: hash of save 2
        bytes_after_save2 = state_path.read_bytes()
        expected_hash3 = hashlib.sha256(bytes_after_save2).hexdigest()
        state3 = load_state(tmp_path)
        state3.alignment_iterations = 2
        save_state(tmp_path, state3)
        raw3 = json.loads(state_path.read_text())
        assert raw3["state_hash"] == expected_hash3
        assert raw3["state_hash"] != raw2["state_hash"]


# ---------------------------------------------------------------------------
# toolchain_status field (Bug S3-160)
# ---------------------------------------------------------------------------


class TestToolchainStatusField:
    """Tests for PipelineState.toolchain_status (Bug S3-160 / IMPROV-19)."""

    def test_pipeline_state_has_toolchain_status_field_default_not_ready(
        self, tmp_path
    ):
        """Default state has toolchain_status == 'NOT_READY'."""
        # Direct dataclass construction
        state = PipelineState()
        assert state.toolchain_status == "NOT_READY"

    def test_pipeline_state_loads_toolchain_status_default_when_missing(
        self, tmp_path
    ):
        """load_state applies default 'NOT_READY' when JSON omits the field."""
        state_dict = _minimal_state_dict()
        # Ensure the field is omitted (default-injection path)
        state_dict.pop("toolchain_status", None)
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.toolchain_status == "NOT_READY"

    def test_pipeline_state_persists_toolchain_status(self, tmp_path):
        """Save state with toolchain_status='READY'; reload still 'READY'."""
        # Seed a minimal state file first.
        _write_state_file(tmp_path, _minimal_state_dict())
        state = load_state(tmp_path)
        state.toolchain_status = "READY"
        save_state(tmp_path, state)

        reloaded = load_state(tmp_path)
        assert reloaded.toolchain_status == "READY"

        # And the JSON-on-disk shape carries the field as a top-level key.
        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["toolchain_status"] == "READY"

    def test_pipeline_state_toolchain_status_round_trip_not_ready(self, tmp_path):
        """Explicit NOT_READY round-trips identically."""
        _write_state_file(tmp_path, _minimal_state_dict())
        state = load_state(tmp_path)
        state.toolchain_status = "NOT_READY"
        save_state(tmp_path, state)
        reloaded = load_state(tmp_path)
        assert reloaded.toolchain_status == "NOT_READY"


# ---------------------------------------------------------------------------
# requires_statistical_analysis field + _requires_statistical_analysis helper
# (Bug S3-164)
# ---------------------------------------------------------------------------


class TestRequiresStatisticalAnalysisField:
    """Tests for PipelineState.requires_statistical_analysis (Bug S3-164)."""

    def test_pipeline_state_has_requires_statistical_analysis_field_default_false(
        self,
    ):
        """Default state has requires_statistical_analysis == False."""
        state = PipelineState()
        assert state.requires_statistical_analysis is False

    def test_requires_statistical_analysis_helper_returns_state_value(self):
        """_requires_statistical_analysis helper reads the flag from state.

        Covers True, False, and the backward-compat fallback for state objects
        that pre-date the field (synthesized via SimpleNamespace -- without
        the attribute, getattr should default to False).
        """
        from pipeline_state import _requires_statistical_analysis

        state_true = PipelineState(requires_statistical_analysis=True)
        assert _requires_statistical_analysis(state_true) is True

        state_false = PipelineState(requires_statistical_analysis=False)
        assert _requires_statistical_analysis(state_false) is False

        # Synthesize an object lacking the attribute (simulates pre-S3-164
        # state objects) -- backward-compat path falls through to False.
        from types import SimpleNamespace

        legacy = SimpleNamespace(stage="0")
        assert _requires_statistical_analysis(legacy) is False

    def test_pipeline_state_persists_requires_statistical_analysis(self, tmp_path):
        """save_state with requires_statistical_analysis=True; reload still True."""
        _write_state_file(tmp_path, _minimal_state_dict())
        state = load_state(tmp_path)
        state.requires_statistical_analysis = True
        save_state(tmp_path, state)

        reloaded = load_state(tmp_path)
        assert reloaded.requires_statistical_analysis is True

        # And the JSON-on-disk shape carries the field as a top-level key.
        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["requires_statistical_analysis"] is True

    def test_pipeline_state_loads_requires_statistical_analysis_default_when_missing(
        self, tmp_path
    ):
        """load_state applies default False when JSON omits the field."""
        state_dict = _minimal_state_dict()
        state_dict.pop("requires_statistical_analysis", None)
        _write_state_file(tmp_path, state_dict)
        state = load_state(tmp_path)
        assert state.requires_statistical_analysis is False


# ---------------------------------------------------------------------------
# statistical_review_done field (Bug S3-168)
# ---------------------------------------------------------------------------


class TestStatisticalReviewDoneField:
    """Tests for PipelineState.statistical_review_done (Bug S3-168).

    Per-blueprint-review-iteration tracking flag. Default False.
    Set True by dispatch_agent_status on
    statistical_correctness_reviewer + REVIEW_COMPLETE; reset False on
    gate_2_2_blueprint_post_review REVISE / FRESH REVIEW outcomes.
    """

    def test_pipeline_state_has_statistical_review_done_field_default_false(
        self,
    ):
        """Default state has statistical_review_done == False."""
        state = PipelineState()
        assert state.statistical_review_done is False

    def test_pipeline_state_persists_statistical_review_done(self, tmp_path):
        """save_state with statistical_review_done=True; reload; still True."""
        _write_state_file(tmp_path, _minimal_state_dict())
        state = load_state(tmp_path)
        state.statistical_review_done = True
        save_state(tmp_path, state)

        reloaded = load_state(tmp_path)
        assert reloaded.statistical_review_done is True

        # And the JSON-on-disk shape carries the field as a top-level key.
        raw = json.loads(_state_path(tmp_path).read_text())
        assert raw["statistical_review_done"] is True
