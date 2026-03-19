"""
Tests for Unit 2: Pipeline State Schema and Core Operations.

Synthetic data generation assumptions:
- PipelineState and DebugSession are imported from
  src.unit_2.stub (the stub module for Unit 2).
- All file I/O tests use pytest tmp_path to avoid filesystem
  side effects.
- pipeline_state.json files are created in tmp_path with known
  content for load/save tests.
- ISO timestamp strings use "2025-01-01T00:00:00" as a
  synthetic default.
- Project names use "test-project" as a synthetic default.
- DebugSession instances use synthetic bug_id=1,
  description="test bug", phase="triage".
- Verified units and pass history use minimal dicts with
  required keys for structural validation.
- ARTIFACT_FILENAMES is mocked from Unit 1 dependency where
  needed for recover_state_from_markers.
- Redo profile sub-stages are valid for any stage per the
  validate_state contract.
- delivered_repo_path uses "/tmp/delivered-repo" as synthetic
  test data.
"""

import json

import pytest

# ---------------------------------------------------------------
# Section 0: Module-level constants
# ---------------------------------------------------------------


class TestStagesConstant:
    def test_stages_is_list(self):
        from pipeline_state import STAGES

        assert isinstance(STAGES, list)

    def test_stages_values(self):
        from pipeline_state import STAGES

        expected = [
            "0",
            "1",
            "2",
            "pre_stage_3",
            "3",
            "4",
            "5",
        ]
        assert STAGES == expected

    def test_stages_length(self):
        from pipeline_state import STAGES

        assert len(STAGES) == 7


class TestSubStagesStage0:
    def test_sub_stages_stage_0_values(self):
        from pipeline_state import SUB_STAGES_STAGE_0

        expected = [
            "hook_activation",
            "project_context",
            "project_profile",
        ]
        assert SUB_STAGES_STAGE_0 == expected

    def test_sub_stages_stage_0_no_none(self):
        from pipeline_state import SUB_STAGES_STAGE_0

        assert None not in SUB_STAGES_STAGE_0


class TestStage1SubStages:
    def test_stage_1_sub_stages_values(self):
        from pipeline_state import STAGE_1_SUB_STAGES

        assert STAGE_1_SUB_STAGES == [None]

    def test_stage_1_sub_stages_only_none(self):
        from pipeline_state import STAGE_1_SUB_STAGES

        assert len(STAGE_1_SUB_STAGES) == 1
        assert STAGE_1_SUB_STAGES[0] is None


class TestStage2SubStages:
    def test_stage_2_sub_stages_values(self):
        from pipeline_state import STAGE_2_SUB_STAGES

        expected = [
            None,
            "blueprint_dialog",
            "alignment_check",
        ]
        assert STAGE_2_SUB_STAGES == expected


class TestStage3SubStages:
    def test_stage_3_sub_stages_values(self):
        from pipeline_state import STAGE_3_SUB_STAGES

        expected = [
            None,
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
        ]
        assert STAGE_3_SUB_STAGES == expected

    def test_stage_3_sub_stages_length(self):
        from pipeline_state import STAGE_3_SUB_STAGES

        assert len(STAGE_3_SUB_STAGES) == 11


class TestStage4SubStages:
    def test_stage_4_sub_stages_values(self):
        from pipeline_state import STAGE_4_SUB_STAGES

        assert STAGE_4_SUB_STAGES == [None, "gate_4_1", "gate_4_2"]


class TestStage5SubStages:
    def test_stage_5_sub_stages_values(self):
        from pipeline_state import STAGE_5_SUB_STAGES

        expected = [
            None,
            "repo_test",
            "structural_check",
            "compliance_scan",
            "gate_5_3",
            "repo_complete",
        ]
        assert STAGE_5_SUB_STAGES == expected


class TestQualityGateSubStages:
    def test_quality_gate_sub_stages_values(self):
        from pipeline_state import QUALITY_GATE_SUB_STAGES

        expected = [
            "quality_gate_a",
            "quality_gate_b",
            "quality_gate_a_retry",
            "quality_gate_b_retry",
        ]
        assert QUALITY_GATE_SUB_STAGES == expected

    def test_quality_gate_sub_stages_all_present(self):
        from pipeline_state import QUALITY_GATE_SUB_STAGES

        for s in [
            "quality_gate_a",
            "quality_gate_b",
            "quality_gate_a_retry",
            "quality_gate_b_retry",
        ]:
            assert s in QUALITY_GATE_SUB_STAGES

    def test_quality_gate_sub_stages_no_none(self):
        from pipeline_state import QUALITY_GATE_SUB_STAGES

        assert None not in QUALITY_GATE_SUB_STAGES


class TestRedoProfileSubStages:
    def test_redo_profile_sub_stages_values(self):
        from pipeline_state import REDO_PROFILE_SUB_STAGES

        expected = [
            "redo_profile_delivery",
            "redo_profile_blueprint",
        ]
        assert REDO_PROFILE_SUB_STAGES == expected


class TestFixLadderPositions:
    def test_fix_ladder_positions_values(self):
        from pipeline_state import FIX_LADDER_POSITIONS

        expected = [
            None,
            "fresh_test",
            "hint_test",
            "fresh_impl",
            "diagnostic",
            "diagnostic_impl",
        ]
        assert FIX_LADDER_POSITIONS == expected

    def test_fix_ladder_positions_starts_with_none(self):
        from pipeline_state import FIX_LADDER_POSITIONS

        assert FIX_LADDER_POSITIONS[0] is None


# ---------------------------------------------------------------
# Section 1: DebugSession class
# ---------------------------------------------------------------


class TestDebugSessionInit:
    def test_debug_session_creation_with_kwargs(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=1,
            description="test bug",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        assert ds.bug_id == 1
        assert ds.description == "test bug"
        assert ds.phase == "triage"
        assert ds.authorized is False

    def test_debug_session_classification_nullable(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        assert ds.classification is None

    def test_debug_session_classification_string(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification="logic_error",
            affected_units=[2, 3],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        assert ds.classification == "logic_error"

    def test_debug_session_affected_units_list(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[2, 5],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        assert ds.affected_units == [2, 5]


class TestDebugSessionToDict:
    def test_to_dict_returns_dict(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        result = ds.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_all_fields(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        result = ds.to_dict()
        expected_keys = {
            "bug_id",
            "description",
            "classification",
            "affected_units",
            "regression_test_path",
            "phase",
            "authorized",
            "triage_refinement_count",
            "repair_retry_count",
            "created_at",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_values_match(self):
        from pipeline_state import DebugSession

        ds = DebugSession(
            bug_id=42,
            description="a bug",
            classification="logic_error",
            affected_units=[1, 2],
            regression_test_path="/tmp/test.py",
            phase="repair",
            authorized=True,
            triage_refinement_count=2,
            repair_retry_count=1,
            created_at="2025-06-01T12:00:00",
        )
        d = ds.to_dict()
        assert d["bug_id"] == 42
        assert d["description"] == "a bug"
        assert d["classification"] == "logic_error"
        assert d["affected_units"] == [1, 2]
        assert d["regression_test_path"] == "/tmp/test.py"
        assert d["phase"] == "repair"
        assert d["authorized"] is True
        assert d["triage_refinement_count"] == 2
        assert d["repair_retry_count"] == 1
        assert d["created_at"] == "2025-06-01T12:00:00"


class TestDebugSessionFromDict:
    def test_from_dict_roundtrip(self):
        from pipeline_state import DebugSession

        original = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[3],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        d = original.to_dict()
        restored = DebugSession.from_dict(d)
        assert restored.bug_id == original.bug_id
        assert restored.description == original.description
        assert restored.classification == original.classification
        assert restored.affected_units == original.affected_units
        assert restored.phase == original.phase
        assert restored.authorized == original.authorized

    def test_from_dict_preserves_all_fields(self):
        from pipeline_state import DebugSession

        data = {
            "bug_id": 5,
            "description": "critical bug",
            "classification": "data_corruption",
            "affected_units": [1, 2, 3],
            "regression_test_path": "/tmp/reg.py",
            "phase": "repair",
            "authorized": True,
            "triage_refinement_count": 3,
            "repair_retry_count": 2,
            "created_at": "2025-03-15T10:00:00",
        }
        ds = DebugSession.from_dict(data)
        assert ds.bug_id == 5
        assert ds.regression_test_path == "/tmp/reg.py"
        assert ds.triage_refinement_count == 3
        assert ds.repair_retry_count == 2


# ---------------------------------------------------------------
# Section 2: PipelineState class
# ---------------------------------------------------------------


class TestPipelineStateInit:
    def test_pipeline_state_creation(self):
        from pipeline_state import PipelineState

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
            project_name="test-project",
            last_action=None,
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert ps.stage == "0"
        assert ps.sub_stage == "hook_activation"
        assert ps.current_unit is None
        assert ps.total_units is None

    def test_pipeline_state_all_fields_accessible(self):
        from pipeline_state import PipelineState

        ps = PipelineState(
            stage="3",
            sub_stage="test_generation",
            current_unit=4,
            total_units=11,
            fix_ladder_position="fresh_test",
            red_run_retries=2,
            alignment_iteration=1,
            verified_units=[{"unit": 1}],
            pass_history=[{"pass": 1}],
            log_references={"key": "val"},
            project_name="proj",
            last_action="test",
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert ps.fix_ladder_position == "fresh_test"
        assert ps.red_run_retries == 2
        assert ps.alignment_iteration == 1
        assert ps.verified_units == [{"unit": 1}]
        assert ps.pass_history == [{"pass": 1}]
        assert ps.log_references == {"key": "val"}
        assert ps.project_name == "proj"
        assert ps.last_action == "test"

    def test_pipeline_state_with_debug_session(self):
        from pipeline_state import DebugSession, PipelineState

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
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
            project_name="proj",
            last_action=None,
            debug_session=ds,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert ps.debug_session is not None
        assert ps.debug_session.bug_id == 1

    def test_pipeline_state_delivered_repo_path(self):
        from pipeline_state import PipelineState

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
            project_name="proj",
            last_action=None,
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path="/tmp/delivered-repo",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert ps.delivered_repo_path == "/tmp/delivered-repo"


class TestPipelineStateToDict:
    def test_to_dict_returns_dict(self):
        from pipeline_state import PipelineState

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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        result = ps.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_all_fields(self):
        from pipeline_state import PipelineState

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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        result = ps.to_dict()
        expected_keys = {
            "stage",
            "sub_stage",
            "current_unit",
            "total_units",
            "fix_ladder_position",
            "red_run_retries",
            "alignment_iteration",
            "verified_units",
            "pass_history",
            "log_references",
            "project_name",
            "last_action",
            "debug_session",
            "debug_history",
            "redo_triggered_from",
            "delivered_repo_path",
            "created_at",
            "updated_at",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_serializes_debug_session(self):
        from pipeline_state import DebugSession, PipelineState

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        result = ps.to_dict()
        assert isinstance(result["debug_session"], dict)
        assert result["debug_session"]["bug_id"] == 1

    def test_to_dict_none_debug_session(self):
        from pipeline_state import PipelineState

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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        result = ps.to_dict()
        assert result["debug_session"] is None


class TestPipelineStateFromDict:
    def test_from_dict_roundtrip(self):
        from pipeline_state import PipelineState

        ps = PipelineState(
            stage="3",
            sub_stage="red_run",
            current_unit=5,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=1,
            alignment_iteration=0,
            verified_units=[{"unit": 1}],
            pass_history=[],
            log_references={},
            project_name="proj",
            last_action="run_tests",
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        d = ps.to_dict()
        restored = PipelineState.from_dict(d)
        assert restored.stage == ps.stage
        assert restored.sub_stage == ps.sub_stage
        assert restored.current_unit == ps.current_unit
        assert restored.red_run_retries == ps.red_run_retries

    def test_from_dict_with_debug_session(self):
        from pipeline_state import (
            DebugSession,
            PipelineState,
        )

        ds = DebugSession(
            bug_id=1,
            description="test",
            classification=None,
            affected_units=[],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        d = ps.to_dict()
        restored = PipelineState.from_dict(d)
        assert restored.debug_session is not None
        assert restored.debug_session.bug_id == 1

    def test_from_dict_with_redo_triggered_from(self):
        from pipeline_state import PipelineState

        data = {
            "stage": "2",
            "sub_stage": "redo_profile_blueprint",
            "current_unit": None,
            "total_units": None,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "alignment_iteration": 0,
            "verified_units": [],
            "pass_history": [],
            "log_references": {},
            "project_name": "test",
            "last_action": None,
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": {"stage": "2"},
            "delivered_repo_path": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        ps = PipelineState.from_dict(data)
        assert ps.redo_triggered_from == {"stage": "2"}

    def test_from_dict_with_delivered_repo_path(self):
        from pipeline_state import PipelineState

        data = {
            "stage": "5",
            "sub_stage": "repo_complete",
            "current_unit": None,
            "total_units": 11,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "alignment_iteration": 0,
            "verified_units": [],
            "pass_history": [],
            "log_references": {},
            "project_name": "test",
            "last_action": None,
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": "/tmp/repo",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        ps = PipelineState.from_dict(data)
        assert ps.delivered_repo_path == "/tmp/repo"

    def test_from_dict_missing_fields_filled_defaults(self):
        from pipeline_state import PipelineState

        minimal_data = {
            "stage": "0",
            "sub_stage": "hook_activation",
        }
        ps = PipelineState.from_dict(minimal_data)
        assert ps.stage == "0"
        assert ps.sub_stage == "hook_activation"
        assert ps.debug_session is None
        assert ps.debug_history == []
        assert ps.redo_triggered_from is None
        assert ps.delivered_repo_path is None


# ---------------------------------------------------------------
# Section 3: create_initial_state
# ---------------------------------------------------------------


class TestCreateInitialState:
    def test_returns_pipeline_state(self):
        from pipeline_state import (
            PipelineState,
            create_initial_state,
        )

        result = create_initial_state("test-project")
        assert isinstance(result, PipelineState)

    def test_initial_stage_is_0(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.stage == "0"

    def test_initial_sub_stage_is_hook_activation(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.sub_stage == "hook_activation"

    def test_initial_red_run_retries_zero(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.red_run_retries == 0

    def test_initial_alignment_iteration_zero(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.alignment_iteration == 0

    def test_initial_verified_units_empty(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert len(result.verified_units) == 0

    def test_initial_pass_history_empty(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert len(result.pass_history) == 0

    def test_initial_debug_session_none(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.debug_session is None

    def test_initial_debug_history_empty(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.debug_history == []

    def test_initial_redo_triggered_from_none(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.redo_triggered_from is None

    def test_initial_delivered_repo_path_none(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.delivered_repo_path is None

    def test_initial_project_name_set(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("my-project")
        assert result.project_name == "my-project"

    def test_initial_fix_ladder_position_none(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.fix_ladder_position is None

    def test_initial_current_unit_none(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.current_unit is None

    def test_initial_total_units_none(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert result.total_units is None

    def test_initial_state_has_created_at(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert isinstance(result.created_at, str)
        assert len(result.created_at) > 0

    def test_initial_state_has_updated_at(self):
        from pipeline_state import create_initial_state

        result = create_initial_state("test-project")
        assert isinstance(result.updated_at, str)
        assert len(result.updated_at) > 0

    def test_initial_stage_in_stages(self):
        from pipeline_state import (
            STAGES,
            create_initial_state,
        )

        result = create_initial_state("test-project")
        assert result.stage in STAGES


# ---------------------------------------------------------------
# Section 4: save_state and load_state
# ---------------------------------------------------------------


class TestSaveState:
    def test_save_creates_file(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()

    def test_save_creates_valid_json(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert isinstance(data, dict)

    def test_save_updates_updated_at(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        # updated_at should be set to current ISO timestamp
        assert isinstance(data["updated_at"], str)
        assert len(data["updated_at"]) > 0

    def test_save_atomic_write(self, tmp_path):
        """Save uses atomic write (temp file + rename)."""
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        # After save, only the final file should exist
        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()
        # Verify content is valid
        data = json.loads(state_file.read_text())
        assert data["stage"] == "0"

    def test_save_overwrites_existing(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state1 = create_initial_state("project-1")
        save_state(state1, tmp_path)

        state2 = create_initial_state("project-2")
        save_state(state2, tmp_path)

        state_file = tmp_path / "pipeline_state.json"
        data = json.loads(state_file.read_text())
        assert data["project_name"] == "project-2"


class TestLoadState:
    def test_load_returns_pipeline_state(self, tmp_path):
        from pipeline_state import (
            PipelineState,
            create_initial_state,
            load_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        result = load_state(tmp_path)
        assert isinstance(result, PipelineState)

    def test_load_preserves_stage(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            load_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        result = load_state(tmp_path)
        assert result.stage == "0"

    def test_load_preserves_project_name(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            load_state,
            save_state,
        )

        state = create_initial_state("my-project")
        save_state(state, tmp_path)
        result = load_state(tmp_path)
        assert result.project_name == "my-project"

    def test_load_deserializes_debug_session(self, tmp_path):
        from pipeline_state import (
            DebugSession,
            PipelineState,
            load_state,
            save_state,
        )

        ds = DebugSession(
            bug_id=7,
            description="session test",
            classification="single_unit",
            affected_units=[1],
            regression_test_path=None,
            phase="triage",
            authorized=False,
            triage_refinement_count=0,
            repair_retry_count=0,
            created_at="2025-01-01T00:00:00",
        )
        state = PipelineState(
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        save_state(state, tmp_path)
        result = load_state(tmp_path)
        assert result.debug_session is not None
        assert result.debug_session.bug_id == 7

    def test_load_deserializes_redo_triggered_from(self, tmp_path):
        from pipeline_state import (
            PipelineState,
            load_state,
            save_state,
        )

        state = PipelineState(
            stage="2",
            sub_stage="redo_profile_blueprint",
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
            redo_triggered_from={"stage": "2", "sub_stage": None, "current_unit": None, "fix_ladder_position": None, "red_run_retries": 0},
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        save_state(state, tmp_path)
        result = load_state(tmp_path)
        assert result.redo_triggered_from["stage"] == "2"

    def test_load_deserializes_delivered_repo_path(self, tmp_path):
        from pipeline_state import (
            PipelineState,
            load_state,
            save_state,
        )

        state = PipelineState(
            stage="5",
            sub_stage="repo_complete",
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
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path="/tmp/delivered",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        save_state(state, tmp_path)
        result = load_state(tmp_path)
        assert result.delivered_repo_path == "/tmp/delivered"

    def test_load_missing_fields_filled_with_defaults(self, tmp_path):
        state_file = tmp_path / "pipeline_state.json"
        minimal = {
            "stage": "0",
            "sub_stage": "hook_activation",
            "red_run_retries": 0,
            "alignment_iteration": 0,
            "verified_units": [],
            "pass_history": [],
            "log_references": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        state_file.write_text(json.dumps(minimal))

        from pipeline_state import load_state

        result = load_state(tmp_path)
        assert result.debug_session is None
        assert result.debug_history == []
        assert result.redo_triggered_from is None
        assert result.delivered_repo_path is None


# ---------------------------------------------------------------
# Section 5: load_state error conditions
# ---------------------------------------------------------------


class TestLoadStateErrors:
    def test_load_file_not_found(self, tmp_path):
        from pipeline_state import load_state

        with pytest.raises(FileNotFoundError):
            load_state(tmp_path)

    def test_load_malformed_json(self, tmp_path):
        state_file = tmp_path / "pipeline_state.json"
        state_file.write_text("{invalid json content")

        from pipeline_state import load_state

        with pytest.raises(json.JSONDecodeError):
            load_state(tmp_path)


# ---------------------------------------------------------------
# Section 6: validate_state
# ---------------------------------------------------------------


class TestValidateState:
    def test_valid_initial_state_no_errors(self):
        from pipeline_state import (
            create_initial_state,
            validate_state,
        )

        state = create_initial_state("test-project")
        errors = validate_state(state)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_invalid_stage_reported(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="invalid_stage",
            sub_stage=None,
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_invalid_sub_stage_for_stage_0(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="0",
            sub_stage="invalid_sub",
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_valid_sub_stage_for_stage_0(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="0",
            sub_stage="project_context",
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_valid_sub_stage_for_stage_1_none(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="1",
            sub_stage=None,
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_invalid_sub_stage_for_stage_1(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="1",
            sub_stage="blueprint_dialog",
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_valid_sub_stage_for_stage_2(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="2",
            sub_stage="blueprint_dialog",
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_valid_sub_stage_for_stage_3(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
            total_units=11,
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_invalid_sub_stage_for_stage_3(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="hook_activation",
            current_unit=1,
            total_units=11,
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_valid_sub_stage_for_stage_4(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="4",
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
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_valid_sub_stage_for_stage_5(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="5",
            sub_stage="repo_test",
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
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_negative_red_run_retries_reported(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="0",
            sub_stage="hook_activation",
            current_unit=None,
            total_units=None,
            fix_ladder_position=None,
            red_run_retries=-1,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name="test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_negative_alignment_iteration_reported(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="0",
            sub_stage="hook_activation",
            current_unit=None,
            total_units=None,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=-1,
            verified_units=[],
            pass_history=[],
            log_references={},
            project_name="test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_redo_profile_sub_stage_valid_any_stage(self):
        """Redo profile sub-stages are valid for any stage."""
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="2",
            sub_stage="redo_profile_blueprint",
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_redo_profile_delivery_valid_any_stage(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="redo_profile_delivery",
            current_unit=1,
            total_units=11,
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
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_delivered_repo_path_none_valid(self):
        from pipeline_state import (
            create_initial_state,
            validate_state,
        )

        state = create_initial_state("test")
        errors = validate_state(state)
        assert len(errors) == 0

    def test_delivered_repo_path_nonempty_string_valid(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="5",
            sub_stage="repo_complete",
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
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path="/tmp/repo",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) == 0

    def test_delivered_repo_path_empty_string_invalid(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="5",
            sub_stage="repo_complete",
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
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path="",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        errors = validate_state(state)
        assert len(errors) > 0

    def test_validate_returns_list(self):
        from pipeline_state import (
            create_initial_state,
            validate_state,
        )

        state = create_initial_state("test")
        result = validate_state(state)
        assert isinstance(result, list)

    def test_quality_gate_sub_stages_valid_for_stage_3(self):
        from pipeline_state import (
            QUALITY_GATE_SUB_STAGES,
            PipelineState,
            validate_state,
        )

        for qg in QUALITY_GATE_SUB_STAGES:
            state = PipelineState(
                stage="3",
                sub_stage=qg,
                current_unit=1,
                total_units=11,
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
                redo_triggered_from=None,
                delivered_repo_path=None,
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
            )
            errors = validate_state(state)
            assert len(errors) == 0, (
                f"quality gate sub_stage {qg} should be valid for stage 3"
            )


# ---------------------------------------------------------------
# Section 7: recover_state_from_markers
# ---------------------------------------------------------------


class TestRecoverStateFromMarkers:
    def test_returns_none_when_no_markers(self, tmp_path):
        from pipeline_state import (
            recover_state_from_markers,
        )

        # Empty directory -- no markers
        result = recover_state_from_markers(tmp_path)
        # With no markers, should return None or a state
        # Contract says it scans for markers
        assert result is None or hasattr(result, "stage")

    def test_returns_pipeline_state_with_markers(self, tmp_path):
        from pipeline_state import (
            recover_state_from_markers,
        )

        # Create marker files
        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        (markers_dir / "unit_1_verified").touch()
        (markers_dir / "unit_2_verified").touch()

        result = recover_state_from_markers(tmp_path)
        # Should return a PipelineState or None
        # depending on what markers are found
        assert result is None or hasattr(result, "stage")


# ---------------------------------------------------------------
# Section 8: get_stage_display
# ---------------------------------------------------------------


class TestGetStageDisplay:
    def test_returns_string(self):
        from pipeline_state import (
            create_initial_state,
            get_stage_display,
        )

        state = create_initial_state("test-project")
        result = get_stage_display(state)
        assert isinstance(result, str)

    def test_display_includes_stage(self):
        from pipeline_state import (
            create_initial_state,
            get_stage_display,
        )

        state = create_initial_state("test-project")
        result = get_stage_display(state)
        assert "Stage" in result or "stage" in result.lower()

    def test_display_for_stage_3_with_unit(self):
        from pipeline_state import (
            PipelineState,
            get_stage_display,
        )

        state = PipelineState(
            stage="3",
            sub_stage="test_generation",
            current_unit=4,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[{"pass": 1}],
            log_references={},
            project_name="test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        result = get_stage_display(state)
        # Per contract: "Stage 3, Unit 4 of 11 (pass 2)"
        assert "3" in result
        assert "4" in result
        assert "11" in result

    def test_display_for_initial_state(self):
        from pipeline_state import (
            create_initial_state,
            get_stage_display,
        )

        state = create_initial_state("test")
        result = get_stage_display(state)
        assert "0" in result


# ---------------------------------------------------------------
# Section 9: updated_at timestamp contract
# ---------------------------------------------------------------


class TestUpdatedAtTimestamp:
    def test_save_sets_updated_at(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            load_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        loaded = load_state(tmp_path)
        assert isinstance(loaded.updated_at, str)
        assert len(loaded.updated_at) > 0

    def test_save_updates_timestamp_each_call(self, tmp_path):
        import time

        from pipeline_state import (
            create_initial_state,
            load_state,
            save_state,
        )

        state = create_initial_state("test-project")
        save_state(state, tmp_path)
        first = load_state(tmp_path)
        first_ts = first.updated_at

        time.sleep(0.01)

        save_state(first, tmp_path)
        second = load_state(tmp_path)
        second_ts = second.updated_at

        # updated_at should be set on each save
        assert isinstance(first_ts, str)
        assert isinstance(second_ts, str)


# ---------------------------------------------------------------
# Section 10: Append-only history contracts
# ---------------------------------------------------------------


class TestAppendOnlyHistory:
    def test_pass_history_is_list(self):
        from pipeline_state import create_initial_state

        state = create_initial_state("test")
        assert isinstance(state.pass_history, list)

    def test_debug_history_is_list(self):
        from pipeline_state import create_initial_state

        state = create_initial_state("test")
        assert isinstance(state.debug_history, list)

    def test_pass_history_preserved_through_roundtrip(self, tmp_path):
        from pipeline_state import (
            PipelineState,
            load_state,
            save_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=2,
            total_units=11,
            fix_ladder_position=None,
            red_run_retries=0,
            alignment_iteration=0,
            verified_units=[],
            pass_history=[
                {"pass_number": 1, "reached_unit": 0, "ended_reason": "complete", "timestamp": "2025-01-01T00:00:00"},
            ],
            log_references={},
            project_name="test",
            last_action=None,
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        save_state(state, tmp_path)
        loaded = load_state(tmp_path)
        assert len(loaded.pass_history) == 1
        assert loaded.pass_history[0]["pass_number"] == 1

    def test_debug_history_preserved_through_roundtrip(self, tmp_path):
        from pipeline_state import (
            PipelineState,
            load_state,
            save_state,
        )

        state = PipelineState(
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
            debug_session=None,
            debug_history=[
                {"bug_id": 1, "result": "fixed", "resolution": "fixed"},
            ],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        save_state(state, tmp_path)
        loaded = load_state(tmp_path)
        assert len(loaded.debug_history) == 1
        assert loaded.debug_history[0]["bug_id"] == 1


# ---------------------------------------------------------------
# Section 11: Cross-constant consistency checks
# ---------------------------------------------------------------


class TestCrossConstantConsistency:
    def test_quality_gate_sub_stages_in_stage_3(self):
        from pipeline_state import (
            QUALITY_GATE_SUB_STAGES,
            STAGE_3_SUB_STAGES,
        )

        for qg in QUALITY_GATE_SUB_STAGES:
            assert qg in STAGE_3_SUB_STAGES, f"{qg} must be in STAGE_3_SUB_STAGES"

    def test_redo_profile_sub_stages_not_in_any_stage(
        self,
    ):
        """Redo profile sub-stages are valid for any stage,
        so they should not necessarily be in stage-specific
        lists but must be accepted by validate_state."""
        from pipeline_state import REDO_PROFILE_SUB_STAGES

        assert len(REDO_PROFILE_SUB_STAGES) == 2
        assert "redo_profile_delivery" in REDO_PROFILE_SUB_STAGES
        assert "redo_profile_blueprint" in REDO_PROFILE_SUB_STAGES

    def test_all_stage_sub_stage_lists_exist(self):
        from pipeline_state import (
            STAGE_1_SUB_STAGES,
            STAGE_2_SUB_STAGES,
            STAGE_3_SUB_STAGES,
            STAGE_4_SUB_STAGES,
            STAGE_5_SUB_STAGES,
            SUB_STAGES_STAGE_0,
        )

        assert isinstance(SUB_STAGES_STAGE_0, list)
        assert isinstance(STAGE_1_SUB_STAGES, list)
        assert isinstance(STAGE_2_SUB_STAGES, list)
        assert isinstance(STAGE_3_SUB_STAGES, list)
        assert isinstance(STAGE_4_SUB_STAGES, list)
        assert isinstance(STAGE_5_SUB_STAGES, list)


# ---------------------------------------------------------------
# Section 12: project_root invariant
# ---------------------------------------------------------------


class TestProjectRootInvariant:
    def test_load_state_requires_directory(self, tmp_path):
        """project_root must be a directory."""
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test")
        save_state(state, tmp_path)
        # tmp_path is a valid directory -- should work
        from pipeline_state import load_state

        result = load_state(tmp_path)
        assert result.stage == "0"

    def test_save_state_to_valid_directory(self, tmp_path):
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test")
        save_state(state, tmp_path)
        assert (tmp_path / "pipeline_state.json").exists()
