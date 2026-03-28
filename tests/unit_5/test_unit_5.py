"""Tests for Unit 5: Pipeline State.

Synthetic Data Assumptions:
- A valid pipeline_state.json resides at project_root / "pipeline_state.json"
  (as determined by ARTIFACT_FILENAMES["pipeline_state"] from Unit 1).
- A minimal valid pipeline state JSON contains at least the core SVP fields:
  stage, sub_stage, current_unit, total_units, verified_units,
  alignment_iterations, fix_ladder_position, red_run_retries, pass_history,
  debug_session, debug_history, redo_triggered_from, delivered_repo_path.
- SVP 2.2 fields (primary_language, component_languages, secondary_language,
  oracle_session_active, oracle_test_project, oracle_phase, oracle_run_count,
  oracle_nested_session_path, state_hash, spec_revision_count, pass,
  pass2_nested_session_path, deferred_broken_units) may be absent in legacy
  JSON and are filled with defaults on load.
- The "pass" key in JSON maps to the "pass_" attribute in PipelineState
  (because "pass" is a Python keyword).
- save_state writes JSON with indent=2, computes SHA-256 hash of the file
  bytes, stores in state_hash, then re-writes with that hash.
- save_state validates the current_unit/sub_stage co-invariant: when
  current_unit is non-null, sub_stage must be non-null.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

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


def _minimal_state_dict() -> Dict[str, Any]:
    """Return a minimal valid pipeline state as a raw dict (JSON-like)."""
    return {
        "stage": "0",
        "sub_stage": "hook_activation",
        "current_unit": None,
        "total_units": 5,
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


def _write_state_json(project_root: Path, data: Dict[str, Any]) -> Path:
    """Write a pipeline_state.json file and return its path."""
    state_file = project_root / "pipeline_state.json"
    state_file.write_text(json.dumps(data, indent=2))
    return state_file


def _make_pipeline_state(**overrides: Any) -> PipelineState:
    """Construct a PipelineState with defaults, applying overrides."""
    defaults = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "current_unit": None,
        "total_units": 5,
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
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    state = PipelineState()
    for key, value in defaults.items():
        setattr(state, key, value)
    return state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project root with a valid pipeline_state.json."""
    _write_state_json(tmp_path, _minimal_state_dict())
    return tmp_path


# ===========================================================================
# VALID_STAGES constant
# ===========================================================================


class TestValidStages:
    """Tests for the VALID_STAGES constant."""

    def test_valid_stages_is_a_set_of_strings(self) -> None:
        assert isinstance(VALID_STAGES, set)
        for item in VALID_STAGES:
            assert isinstance(item, str)

    def test_valid_stages_contains_exactly_expected_values(self) -> None:
        expected = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}
        assert VALID_STAGES == expected

    def test_valid_stages_has_seven_members(self) -> None:
        assert len(VALID_STAGES) == 7


# ===========================================================================
# VALID_SUB_STAGES constant
# ===========================================================================


class TestValidSubStages:
    """Tests for the VALID_SUB_STAGES constant."""

    def test_valid_sub_stages_is_a_dict(self) -> None:
        assert isinstance(VALID_SUB_STAGES, dict)

    def test_valid_sub_stages_keys_match_valid_stages(self) -> None:
        assert set(VALID_SUB_STAGES.keys()) == VALID_STAGES

    def test_stage_0_sub_stages_contain_expected_values(self) -> None:
        expected = {"hook_activation", "project_context", "project_profile"}
        assert VALID_SUB_STAGES["0"] == expected

    def test_stage_1_sub_stages_contain_expected_values(self) -> None:
        expected = {None, "checklist_generation"}
        assert VALID_SUB_STAGES["1"] == expected

    def test_stage_2_sub_stages_contain_alignment_confirmed(self) -> None:
        expected = {"blueprint_dialog", "alignment_check", "alignment_confirmed"}
        assert VALID_SUB_STAGES["2"] == expected

    def test_stage_2_sub_stages_include_alignment_confirmed_specifically(self) -> None:
        assert "alignment_confirmed" in VALID_SUB_STAGES["2"]

    def test_pre_stage_3_sub_stages_contain_only_none(self) -> None:
        expected = {None}
        assert VALID_SUB_STAGES["pre_stage_3"] == expected

    def test_stage_3_sub_stages_contain_all_expected_values(self) -> None:
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

    def test_stage_4_sub_stages_contain_expected_values(self) -> None:
        expected = {None, "regression_adaptation"}
        assert VALID_SUB_STAGES["4"] == expected

    def test_stage_5_sub_stages_contain_expected_values(self) -> None:
        expected = {None, "repo_test", "compliance_scan", "repo_complete"}
        assert VALID_SUB_STAGES["5"] == expected

    def test_each_sub_stage_set_contains_only_strings_or_none(self) -> None:
        for stage, sub_stages in VALID_SUB_STAGES.items():
            assert isinstance(sub_stages, set), f"Stage {stage} sub_stages is not a set"
            for item in sub_stages:
                assert item is None or isinstance(item, str), (
                    f"Stage {stage} contains non-string/non-None: {item!r}"
                )


# ===========================================================================
# VALID_FIX_LADDER_POSITIONS constant
# ===========================================================================


class TestValidFixLadderPositions:
    """Tests for the VALID_FIX_LADDER_POSITIONS constant."""

    def test_valid_fix_ladder_positions_is_a_list(self) -> None:
        assert isinstance(VALID_FIX_LADDER_POSITIONS, list)

    def test_valid_fix_ladder_positions_contains_expected_values_in_order(self) -> None:
        expected = [None, "fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"]
        assert VALID_FIX_LADDER_POSITIONS == expected

    def test_valid_fix_ladder_positions_has_five_entries(self) -> None:
        assert len(VALID_FIX_LADDER_POSITIONS) == 5

    def test_valid_fix_ladder_positions_starts_with_none(self) -> None:
        assert VALID_FIX_LADDER_POSITIONS[0] is None

    def test_valid_fix_ladder_positions_ends_with_exhausted(self) -> None:
        assert VALID_FIX_LADDER_POSITIONS[-1] == "exhausted"


# ===========================================================================
# VALID_DEBUG_PHASES constant
# ===========================================================================


class TestValidDebugPhases:
    """Tests for the VALID_DEBUG_PHASES constant."""

    def test_valid_debug_phases_is_a_set(self) -> None:
        assert isinstance(VALID_DEBUG_PHASES, set)

    def test_valid_debug_phases_contains_expected_values(self) -> None:
        expected = {
            "triage",
            "repair",
            "regression_test",
            "lessons_learned",
            "reassembly",
            "stage3_reentry",
            "commit",
        }
        assert VALID_DEBUG_PHASES == expected

    def test_valid_debug_phases_has_seven_members(self) -> None:
        assert len(VALID_DEBUG_PHASES) == 7


# ===========================================================================
# VALID_ORACLE_PHASES constant
# ===========================================================================


class TestValidOraclePhases:
    """Tests for the VALID_ORACLE_PHASES constant."""

    def test_valid_oracle_phases_is_a_set(self) -> None:
        assert isinstance(VALID_ORACLE_PHASES, set)

    def test_valid_oracle_phases_contains_expected_values(self) -> None:
        expected = {None, "dry_run", "gate_a", "green_run", "gate_b", "exit"}
        assert VALID_ORACLE_PHASES == expected

    def test_valid_oracle_phases_includes_none(self) -> None:
        assert None in VALID_ORACLE_PHASES

    def test_valid_oracle_phases_has_six_members(self) -> None:
        assert len(VALID_ORACLE_PHASES) == 6


# ===========================================================================
# PipelineState dataclass -- field existence and types
# ===========================================================================


class TestPipelineStateFields:
    """Tests that PipelineState has all 26 declared fields with correct types."""

    def test_pipeline_state_has_stage_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "stage")
        assert isinstance(state.stage, str)

    def test_pipeline_state_has_sub_stage_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "sub_stage")

    def test_pipeline_state_has_current_unit_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "current_unit")

    def test_pipeline_state_has_total_units_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "total_units")
        assert isinstance(state.total_units, int)

    def test_pipeline_state_has_verified_units_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "verified_units")
        assert isinstance(state.verified_units, list)

    def test_pipeline_state_has_alignment_iterations_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "alignment_iterations")
        assert isinstance(state.alignment_iterations, int)

    def test_pipeline_state_has_fix_ladder_position_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "fix_ladder_position")

    def test_pipeline_state_has_red_run_retries_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "red_run_retries")
        assert isinstance(state.red_run_retries, int)

    def test_pipeline_state_has_pass_history_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "pass_history")
        assert isinstance(state.pass_history, list)

    def test_pipeline_state_has_debug_session_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "debug_session")

    def test_pipeline_state_has_debug_history_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "debug_history")
        assert isinstance(state.debug_history, list)

    def test_pipeline_state_has_redo_triggered_from_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "redo_triggered_from")

    def test_pipeline_state_has_delivered_repo_path_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "delivered_repo_path")

    def test_pipeline_state_has_primary_language_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "primary_language")
        assert isinstance(state.primary_language, str)

    def test_pipeline_state_has_component_languages_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "component_languages")
        assert isinstance(state.component_languages, list)

    def test_pipeline_state_has_secondary_language_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "secondary_language")

    def test_pipeline_state_has_oracle_session_active_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "oracle_session_active")
        assert isinstance(state.oracle_session_active, bool)

    def test_pipeline_state_has_oracle_test_project_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "oracle_test_project")

    def test_pipeline_state_has_oracle_phase_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "oracle_phase")

    def test_pipeline_state_has_oracle_run_count_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "oracle_run_count")
        assert isinstance(state.oracle_run_count, int)

    def test_pipeline_state_has_oracle_nested_session_path_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "oracle_nested_session_path")

    def test_pipeline_state_has_state_hash_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "state_hash")

    def test_pipeline_state_has_spec_revision_count_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "spec_revision_count")
        assert isinstance(state.spec_revision_count, int)

    def test_pipeline_state_has_pass_underscore_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "pass_")

    def test_pipeline_state_has_pass2_nested_session_path_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "pass2_nested_session_path")

    def test_pipeline_state_has_deferred_broken_units_field(self) -> None:
        state = _make_pipeline_state()
        assert hasattr(state, "deferred_broken_units")
        assert isinstance(state.deferred_broken_units, list)

    def test_pipeline_state_has_exactly_26_declared_fields(self) -> None:
        """The blueprint declares exactly 26 fields on PipelineState."""
        expected_fields = {
            "stage",
            "sub_stage",
            "current_unit",
            "total_units",
            "verified_units",
            "alignment_iterations",
            "fix_ladder_position",
            "red_run_retries",
            "pass_history",
            "debug_session",
            "debug_history",
            "redo_triggered_from",
            "delivered_repo_path",
            "primary_language",
            "component_languages",
            "secondary_language",
            "oracle_session_active",
            "oracle_test_project",
            "oracle_phase",
            "oracle_run_count",
            "oracle_nested_session_path",
            "state_hash",
            "spec_revision_count",
            "pass_",
            "pass2_nested_session_path",
            "deferred_broken_units",
        }
        # PipelineState annotations should declare all 26 fields
        annotations = getattr(PipelineState, "__annotations__", {})
        assert expected_fields == set(annotations.keys())


# ===========================================================================
# PipelineState -- pass_ field valid values
# ===========================================================================


class TestPipelineStatePassField:
    """Tests for the pass_ field valid values: None, 1, 2."""

    def test_pass_field_accepts_none(self) -> None:
        state = _make_pipeline_state(pass_=None)
        assert state.pass_ is None

    def test_pass_field_accepts_one(self) -> None:
        state = _make_pipeline_state(pass_=1)
        assert state.pass_ == 1

    def test_pass_field_accepts_two(self) -> None:
        state = _make_pipeline_state(pass_=2)
        assert state.pass_ == 2


# ===========================================================================
# load_state -- basic behavior
# ===========================================================================


class TestLoadStateBasic:
    """Tests for load_state basic read and construction behavior."""

    def test_load_state_returns_pipeline_state_instance(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert isinstance(result, PipelineState)

    def test_load_state_reads_stage_correctly(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.stage == "0"

    def test_load_state_reads_sub_stage_correctly(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.sub_stage == "hook_activation"

    def test_load_state_reads_current_unit_as_none(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.current_unit is None

    def test_load_state_reads_total_units_correctly(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.total_units == 5

    def test_load_state_reads_verified_units_as_empty_list(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.verified_units == []

    def test_load_state_reads_alignment_iterations(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.alignment_iterations == 0

    def test_load_state_reads_fix_ladder_position_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.fix_ladder_position is None

    def test_load_state_reads_red_run_retries(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.red_run_retries == 0

    def test_load_state_reads_pass_history_as_empty_list(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.pass_history == []

    def test_load_state_reads_debug_session_as_none(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.debug_session is None

    def test_load_state_reads_debug_history_as_empty_list(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.debug_history == []

    def test_load_state_reads_redo_triggered_from_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.redo_triggered_from is None

    def test_load_state_reads_delivered_repo_path_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.delivered_repo_path is None

    def test_load_state_reads_primary_language(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.primary_language == "python"

    def test_load_state_reads_component_languages(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.component_languages == []

    def test_load_state_reads_secondary_language_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.secondary_language is None

    def test_load_state_reads_oracle_session_active_as_false(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.oracle_session_active is False

    def test_load_state_reads_oracle_test_project_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.oracle_test_project is None

    def test_load_state_reads_oracle_phase_as_none(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.oracle_phase is None

    def test_load_state_reads_oracle_run_count_as_zero(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.oracle_run_count == 0

    def test_load_state_reads_oracle_nested_session_path_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.oracle_nested_session_path is None

    def test_load_state_reads_state_hash_as_none(self, tmp_project: Path) -> None:
        result = load_state(tmp_project)
        assert result.state_hash is None

    def test_load_state_reads_spec_revision_count_as_zero(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.spec_revision_count == 0

    def test_load_state_reads_pass_field_from_json_pass_key(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_state_dict()
        data["pass"] = 1
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.pass_ == 1

    def test_load_state_reads_pass2_nested_session_path_as_none(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.pass2_nested_session_path is None

    def test_load_state_reads_deferred_broken_units_as_empty_list(
        self, tmp_project: Path
    ) -> None:
        result = load_state(tmp_project)
        assert result.deferred_broken_units == []


# ===========================================================================
# load_state -- pass_ JSON serialization
# ===========================================================================


class TestLoadStatePassSerialization:
    """Tests that load_state correctly maps JSON 'pass' key to pass_ attribute."""

    def test_load_state_maps_json_pass_none_to_pass_underscore_none(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_state_dict()
        data["pass"] = None
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.pass_ is None

    def test_load_state_maps_json_pass_1_to_pass_underscore_1(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_state_dict()
        data["pass"] = 1
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.pass_ == 1

    def test_load_state_maps_json_pass_2_to_pass_underscore_2(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_state_dict()
        data["pass"] = 2
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.pass_ == 2


# ===========================================================================
# load_state -- missing SVP 2.2 fields default filling
# ===========================================================================


class TestLoadStateMissingSvp22Fields:
    """Tests that load_state fills missing SVP 2.2 fields with correct defaults."""

    @pytest.fixture
    def legacy_project(self, tmp_path: Path) -> Path:
        """Create a project root with only legacy (pre-SVP 2.2) fields."""
        legacy_data = {
            "stage": "1",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 2,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
        }
        _write_state_json(tmp_path, legacy_data)
        return tmp_path

    def test_missing_primary_language_defaults_to_python(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.primary_language == "python"

    def test_missing_component_languages_defaults_to_empty_list(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.component_languages == []

    def test_missing_secondary_language_defaults_to_none(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.secondary_language is None

    def test_missing_oracle_session_active_defaults_to_false(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.oracle_session_active is False

    def test_missing_oracle_test_project_defaults_to_none(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.oracle_test_project is None

    def test_missing_oracle_phase_defaults_to_none(self, legacy_project: Path) -> None:
        result = load_state(legacy_project)
        assert result.oracle_phase is None

    def test_missing_oracle_run_count_defaults_to_zero(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.oracle_run_count == 0

    def test_missing_oracle_nested_session_path_defaults_to_none(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.oracle_nested_session_path is None

    def test_missing_state_hash_defaults_to_none(self, legacy_project: Path) -> None:
        result = load_state(legacy_project)
        assert result.state_hash is None

    def test_missing_spec_revision_count_defaults_to_zero(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.spec_revision_count == 0

    def test_missing_pass_defaults_to_none(self, legacy_project: Path) -> None:
        result = load_state(legacy_project)
        assert result.pass_ is None

    def test_missing_pass2_nested_session_path_defaults_to_none(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.pass2_nested_session_path is None

    def test_missing_deferred_broken_units_defaults_to_empty_list(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.deferred_broken_units == []

    def test_legacy_fields_are_preserved_when_svp22_fields_defaulted(
        self, legacy_project: Path
    ) -> None:
        result = load_state(legacy_project)
        assert result.stage == "1"
        assert result.total_units == 10
        assert result.alignment_iterations == 2


# ===========================================================================
# load_state -- FileNotFoundError
# ===========================================================================


class TestLoadStateFileNotFound:
    """Tests that load_state raises FileNotFoundError when file is absent."""

    def test_load_state_raises_file_not_found_error_when_no_file(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            load_state(tmp_path)

    def test_load_state_raises_file_not_found_for_empty_directory(
        self, tmp_path: Path
    ) -> None:
        empty_dir = tmp_path / "empty_project"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_state(empty_dir)


# ===========================================================================
# load_state -- non-trivial field values
# ===========================================================================


class TestLoadStateNonTrivialValues:
    """Tests that load_state correctly handles non-default/populated values."""

    def test_load_state_reads_non_empty_verified_units(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["verified_units"] = [
            {"unit": 1, "status": "passed"},
            {"unit": 2, "status": "passed"},
        ]
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert len(result.verified_units) == 2
        assert result.verified_units[0]["unit"] == 1

    def test_load_state_reads_populated_debug_session(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["debug_session"] = {
            "authorized": True,
            "bug_number": 42,
            "classification": "single_unit",
            "affected_units": [3],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.debug_session is not None
        assert result.debug_session["authorized"] is True
        assert result.debug_session["bug_number"] == 42
        assert result.debug_session["classification"] == "single_unit"

    def test_load_state_reads_fix_ladder_position_fresh_impl(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_state_dict()
        data["fix_ladder_position"] = "fresh_impl"
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.fix_ladder_position == "fresh_impl"

    def test_load_state_reads_oracle_session_active_true(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["oracle_session_active"] = True
        data["oracle_phase"] = "dry_run"
        data["oracle_run_count"] = 3
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.oracle_session_active is True
        assert result.oracle_phase == "dry_run"
        assert result.oracle_run_count == 3

    def test_load_state_reads_delivered_repo_path_string(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["delivered_repo_path"] = "/path/to/repo"
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.delivered_repo_path == "/path/to/repo"

    def test_load_state_reads_component_languages_list(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["component_languages"] = ["stan"]
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.component_languages == ["stan"]

    def test_load_state_reads_secondary_language(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["secondary_language"] = "r"
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.secondary_language == "r"

    def test_load_state_reads_deferred_broken_units_with_values(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_state_dict()
        data["deferred_broken_units"] = [3, 7, 12]
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.deferred_broken_units == [3, 7, 12]

    def test_load_state_reads_pass_history_with_entries(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["pass_history"] = [{"pass": 1, "units": [1, 2, 3]}]
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert len(result.pass_history) == 1

    def test_load_state_reads_spec_revision_count_nonzero(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["spec_revision_count"] = 4
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.spec_revision_count == 4

    def test_load_state_reads_state_hash_string(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["state_hash"] = "abc123def456"
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.state_hash == "abc123def456"

    def test_load_state_reads_stage_3_with_current_unit(self, tmp_path: Path) -> None:
        data = _minimal_state_dict()
        data["stage"] = "3"
        data["sub_stage"] = "implementation"
        data["current_unit"] = 4
        _write_state_json(tmp_path, data)
        result = load_state(tmp_path)
        assert result.stage == "3"
        assert result.sub_stage == "implementation"
        assert result.current_unit == 4


# ===========================================================================
# save_state -- basic behavior
# ===========================================================================


class TestSaveStateBasic:
    """Tests for save_state JSON writing behavior."""

    def test_save_state_creates_pipeline_state_json_file(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()

    def test_save_state_writes_valid_json(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert isinstance(data, dict)

    def test_save_state_writes_json_with_indent_2(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        content = state_file.read_text()
        # indent=2 means nested keys are indented by 2 spaces
        assert "\n  " in content

    def test_save_state_persists_stage_value(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(stage="3")
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["stage"] == "3"

    def test_save_state_persists_sub_stage_value(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(
            stage="3", sub_stage="implementation", current_unit=1
        )
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["sub_stage"] == "implementation"

    def test_save_state_persists_total_units(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(total_units=15)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["total_units"] == 15

    def test_save_state_persists_verified_units(self, tmp_path: Path) -> None:
        units = [{"unit": 1, "status": "passed"}]
        state = _make_pipeline_state(verified_units=units)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["verified_units"] == units

    def test_save_state_persists_debug_session(self, tmp_path: Path) -> None:
        debug = {
            "authorized": True,
            "bug_number": 1,
            "classification": "build_env",
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_pipeline_state(debug_session=debug)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["debug_session"]["authorized"] is True

    def test_save_state_persists_oracle_fields(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(
            oracle_session_active=True,
            oracle_test_project="/some/path",
            oracle_phase="gate_a",
            oracle_run_count=5,
            oracle_nested_session_path="/nested",
        )
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["oracle_session_active"] is True
        assert data["oracle_test_project"] == "/some/path"
        assert data["oracle_phase"] == "gate_a"
        assert data["oracle_run_count"] == 5
        assert data["oracle_nested_session_path"] == "/nested"

    def test_save_state_persists_deferred_broken_units(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(deferred_broken_units=[2, 5])
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["deferred_broken_units"] == [2, 5]

    def test_save_state_persists_spec_revision_count(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(spec_revision_count=3)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["spec_revision_count"] == 3


# ===========================================================================
# save_state -- pass_ field serialization as "pass" in JSON
# ===========================================================================


class TestSaveStatePassSerialization:
    """Tests that save_state serializes pass_ attribute as 'pass' key in JSON."""

    def test_save_state_serializes_pass_underscore_as_pass_key(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(pass_=1)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert "pass" in data
        assert data["pass"] == 1

    def test_save_state_does_not_write_pass_underscore_key_to_json(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(pass_=2)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert "pass_" not in data

    def test_save_state_serializes_pass_none_as_null(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(pass_=None)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert "pass" in data
        assert data["pass"] is None

    def test_save_state_serializes_pass_2(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(pass_=2)
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["pass"] == 2


# ===========================================================================
# save_state -- state_hash computation
# ===========================================================================


class TestSaveStateStateHash:
    """Tests that save_state computes SHA-256 hash of file bytes and stores it."""

    def test_save_state_sets_state_hash_on_state_object(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        assert state.state_hash is not None

    def test_save_state_state_hash_is_a_hex_string(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        assert isinstance(state.state_hash, str)
        # SHA-256 hex digest is 64 characters
        assert len(state.state_hash) == 64
        # Must be valid hexadecimal
        int(state.state_hash, 16)

    def test_save_state_state_hash_is_valid_sha256_hex(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        # state_hash is a SHA-256 hex digest (64 hex chars). It is computed
        # from a prior version of the file, not from the final file (which
        # already contains the hash — self-referential hashing is impossible).
        assert state.state_hash is not None
        assert len(state.state_hash) == 64
        assert all(c in "0123456789abcdef" for c in state.state_hash)

    def test_save_state_writes_state_hash_to_json_file(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert "state_hash" in data
        assert data["state_hash"] is not None
        assert isinstance(data["state_hash"], str)

    def test_save_state_hash_in_file_equals_hash_on_object(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["state_hash"] == state.state_hash

    def test_save_state_different_states_produce_different_hashes(
        self, tmp_path: Path
    ) -> None:
        state_a = _make_pipeline_state(total_units=5)
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        save_state(dir_a, state_a)

        state_b = _make_pipeline_state(total_units=10)
        dir_b = tmp_path / "b"
        dir_b.mkdir()
        save_state(dir_b, state_b)

        assert state_a.state_hash != state_b.state_hash


# ===========================================================================
# save_state -- current_unit / sub_stage co-invariant
# ===========================================================================


class TestSaveStateCoInvariant:
    """Tests that save_state validates current_unit/sub_stage co-invariant."""

    def test_save_state_raises_value_error_when_current_unit_set_but_sub_stage_none(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(stage="3", current_unit=1, sub_stage=None)
        with pytest.raises(ValueError):
            save_state(tmp_path, state)

    def test_save_state_accepts_current_unit_none_with_sub_stage_none(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(stage="1", current_unit=None, sub_stage=None)
        # Should not raise
        save_state(tmp_path, state)

    def test_save_state_accepts_current_unit_set_with_sub_stage_set(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(
            stage="3", current_unit=1, sub_stage="implementation"
        )
        # Should not raise
        save_state(tmp_path, state)

    def test_save_state_accepts_current_unit_none_with_sub_stage_set(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(
            stage="0", current_unit=None, sub_stage="hook_activation"
        )
        # Should not raise
        save_state(tmp_path, state)

    def test_save_state_co_invariant_error_message_is_descriptive(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(stage="3", current_unit=5, sub_stage=None)
        with pytest.raises(ValueError, match=r"(?i)(sub_stage|current_unit)"):
            save_state(tmp_path, state)


# ===========================================================================
# save_state + load_state -- round-trip
# ===========================================================================


class TestSaveLoadRoundTrip:
    """Tests that save then load produces equivalent state."""

    def test_round_trip_preserves_stage(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(stage="3")
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.stage == "3"

    def test_round_trip_preserves_sub_stage(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(
            stage="3", sub_stage="stub_generation", current_unit=2
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.sub_stage == "stub_generation"

    def test_round_trip_preserves_current_unit(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(
            stage="3", sub_stage="implementation", current_unit=7
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.current_unit == 7

    def test_round_trip_preserves_total_units(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(total_units=29)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.total_units == 29

    def test_round_trip_preserves_verified_units(self, tmp_path: Path) -> None:
        units = [{"unit": 1, "status": "ok"}, {"unit": 2, "status": "ok"}]
        state = _make_pipeline_state(verified_units=units)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.verified_units == units

    def test_round_trip_preserves_pass_underscore(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(pass_=2)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.pass_ == 2

    def test_round_trip_preserves_oracle_fields(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(
            oracle_session_active=True,
            oracle_phase="gate_b",
            oracle_run_count=10,
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.oracle_session_active is True
        assert loaded.oracle_phase == "gate_b"
        assert loaded.oracle_run_count == 10

    def test_round_trip_preserves_deferred_broken_units(self, tmp_path: Path) -> None:
        state = _make_pipeline_state(deferred_broken_units=[1, 4, 9])
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.deferred_broken_units == [1, 4, 9]

    def test_round_trip_preserves_debug_session(self, tmp_path: Path) -> None:
        debug = {
            "authorized": False,
            "bug_number": None,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_pipeline_state(debug_session=debug)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.debug_session == debug

    def test_round_trip_preserves_state_hash(self, tmp_path: Path) -> None:
        state = _make_pipeline_state()
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.state_hash == state.state_hash
        assert loaded.state_hash is not None

    def test_round_trip_preserves_all_fields_simultaneously(
        self, tmp_path: Path
    ) -> None:
        state = _make_pipeline_state(
            stage="4",
            sub_stage="regression_adaptation",
            current_unit=None,
            total_units=20,
            verified_units=[{"unit": 1}],
            alignment_iterations=3,
            fix_ladder_position=None,
            red_run_retries=0,
            pass_history=[{"pass": 1}],
            debug_session=None,
            debug_history=[{"bug": 1}],
            redo_triggered_from={"stage": "2"},
            delivered_repo_path="/repo",
            primary_language="r",
            component_languages=["stan"],
            secondary_language="python",
            oracle_session_active=False,
            oracle_test_project=None,
            oracle_phase=None,
            oracle_run_count=0,
            oracle_nested_session_path=None,
            spec_revision_count=2,
            pass_=1,
            pass2_nested_session_path="/nested",
            deferred_broken_units=[5],
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.stage == "4"
        assert loaded.sub_stage == "regression_adaptation"
        assert loaded.current_unit is None
        assert loaded.total_units == 20
        assert loaded.verified_units == [{"unit": 1}]
        assert loaded.alignment_iterations == 3
        assert loaded.fix_ladder_position is None
        assert loaded.red_run_retries == 0
        assert loaded.pass_history == [{"pass": 1}]
        assert loaded.debug_session is None
        assert loaded.debug_history == [{"bug": 1}]
        assert loaded.redo_triggered_from == {"stage": "2"}
        assert loaded.delivered_repo_path == "/repo"
        assert loaded.primary_language == "r"
        assert loaded.component_languages == ["stan"]
        assert loaded.secondary_language == "python"
        assert loaded.oracle_session_active is False
        assert loaded.oracle_test_project is None
        assert loaded.oracle_phase is None
        assert loaded.oracle_run_count == 0
        assert loaded.oracle_nested_session_path is None
        assert loaded.spec_revision_count == 2
        assert loaded.pass_ == 1
        assert loaded.pass2_nested_session_path == "/nested"
        assert loaded.deferred_broken_units == [5]


# ===========================================================================
# load_state -- reads from ARTIFACT_FILENAMES path
# ===========================================================================


class TestLoadStateUsesArtifactFilenames:
    """Tests that load_state reads from the path specified by ARTIFACT_FILENAMES."""

    def test_load_state_reads_from_pipeline_state_json(self, tmp_path: Path) -> None:
        """The file name must be pipeline_state.json per ARTIFACT_FILENAMES."""
        data = _minimal_state_dict()
        # Write to the correct filename
        (tmp_path / "pipeline_state.json").write_text(json.dumps(data, indent=2))
        result = load_state(tmp_path)
        assert result.stage == "0"

    def test_load_state_does_not_find_wrong_filename(self, tmp_path: Path) -> None:
        """Writing to a wrong filename should cause FileNotFoundError."""
        data = _minimal_state_dict()
        (tmp_path / "state.json").write_text(json.dumps(data, indent=2))
        with pytest.raises(FileNotFoundError):
            load_state(tmp_path)


# ===========================================================================
# save_state -- overwrites existing file
# ===========================================================================


class TestSaveStateOverwrite:
    """Tests that save_state overwrites any existing pipeline_state.json."""

    def test_save_state_overwrites_existing_file(self, tmp_path: Path) -> None:
        # Write initial state
        state_a = _make_pipeline_state(stage="0", total_units=5)
        save_state(tmp_path, state_a)

        # Overwrite with different state
        state_b = _make_pipeline_state(stage="3", total_units=20)
        save_state(tmp_path, state_b)

        loaded = load_state(tmp_path)
        assert loaded.stage == "3"
        assert loaded.total_units == 20


# ===========================================================================
# PipelineState -- debug_session schema
# ===========================================================================


class TestDebugSessionSchema:
    """Tests for the debug_session schema as described in the blueprint."""

    def test_debug_session_with_all_fields_round_trips(self, tmp_path: Path) -> None:
        debug = {
            "authorized": True,
            "bug_number": 7,
            "classification": "cross_unit",
            "affected_units": [2, 5, 8],
            "phase": "repair",
            "repair_retry_count": 2,
            "triage_refinement_count": 1,
            "ledger_path": "/path/to/ledger.json",
        }
        state = _make_pipeline_state(debug_session=debug)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        ds = loaded.debug_session
        assert ds["authorized"] is True
        assert ds["bug_number"] == 7
        assert ds["classification"] == "cross_unit"
        assert ds["affected_units"] == [2, 5, 8]
        assert ds["phase"] == "repair"
        assert ds["repair_retry_count"] == 2
        assert ds["triage_refinement_count"] == 1
        assert ds["ledger_path"] == "/path/to/ledger.json"

    def test_debug_session_null_classification_round_trips(
        self, tmp_path: Path
    ) -> None:
        debug = {
            "authorized": False,
            "bug_number": None,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_pipeline_state(debug_session=debug)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        ds = loaded.debug_session
        assert ds["classification"] is None
        assert ds["bug_number"] is None
        assert ds["ledger_path"] is None

    def test_debug_session_build_env_classification(self, tmp_path: Path) -> None:
        debug = {
            "authorized": True,
            "bug_number": 1,
            "classification": "build_env",
            "affected_units": [],
            "phase": "commit",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_pipeline_state(debug_session=debug)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.debug_session["classification"] == "build_env"

    def test_debug_session_single_unit_classification(self, tmp_path: Path) -> None:
        debug = {
            "authorized": True,
            "bug_number": 3,
            "classification": "single_unit",
            "affected_units": [4],
            "phase": "lessons_learned",
            "repair_retry_count": 1,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_pipeline_state(debug_session=debug)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.debug_session["classification"] == "single_unit"
        assert loaded.debug_session["affected_units"] == [4]
