"""
Coverage gap tests for Unit 2: Pipeline State Schema.

These tests close gaps identified by comparing the existing
109 tests against the blueprint contracts (Tier 2 signatures,
Tier 3 behavioral contracts, and Tier 3 error conditions).

Gaps addressed:
- validate_state: invalid fix_ladder_position detection
- load_state: ValueError on structural validation failure
- get_stage_display: sub_stage rendering in parens
- get_stage_display: fix_ladder_position rendering
- recover_state_from_markers: correct marker filenames
- recover_state_from_markers: no .svp directory
- PipelineState init: debug_session dict auto-conversion
- validate_state: valid fix_ladder_position (None, named)
- validate_state: stage 0 with None sub_stage is valid
- validate_state: pre_stage_3 sub_stage validation
"""

import json

import pytest


# ---------------------------------------------------------------
# validate_state: fix_ladder_position validation
# ---------------------------------------------------------------


class TestValidateFixLadderPosition:
    def test_invalid_fix_ladder_position_reported(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            total_units=11,
            fix_ladder_position="nonexistent_pos",
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
        assert any(
            "fix_ladder_position" in e for e in errors
        )

    def test_valid_fix_ladder_position_none(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
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

    def test_valid_fix_ladder_position_fresh_test(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            total_units=11,
            fix_ladder_position="fresh_test",
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

    def test_valid_fix_ladder_position_diagnostic(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            total_units=11,
            fix_ladder_position="diagnostic",
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

    def test_all_fix_ladder_positions_valid(self):
        from pipeline_state import (
            FIX_LADDER_POSITIONS,
            PipelineState,
            validate_state,
        )

        for pos in FIX_LADDER_POSITIONS:
            state = PipelineState(
                stage="3",
                sub_stage="implementation",
                current_unit=1,
                total_units=11,
                fix_ladder_position=pos,
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
                f"fix_ladder_position {pos} "
                f"should be valid"
            )


# ---------------------------------------------------------------
# load_state: ValueError on validation failure
# ---------------------------------------------------------------


class TestLoadStateValidationError:
    def test_load_invalid_stage_raises_value_error(
        self, tmp_path
    ):
        """load_state raises ValueError when structural
        validation fails."""
        state_file = tmp_path / "pipeline_state.json"
        data = {
            "stage": "99_invalid",
            "sub_stage": None,
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
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        state_file.write_text(json.dumps(data))

        from pipeline_state import load_state

        with pytest.raises(ValueError):
            load_state(tmp_path)

    def test_load_invalid_sub_stage_raises_value_error(
        self, tmp_path
    ):
        state_file = tmp_path / "pipeline_state.json"
        data = {
            "stage": "0",
            "sub_stage": "bogus_sub_stage",
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
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        state_file.write_text(json.dumps(data))

        from pipeline_state import load_state

        with pytest.raises(ValueError):
            load_state(tmp_path)


# ---------------------------------------------------------------
# get_stage_display: sub_stage and fix_ladder rendering
# ---------------------------------------------------------------


class TestGetStageDisplaySubStage:
    def test_display_includes_sub_stage_in_parens(self):
        from pipeline_state import (
            PipelineState,
            get_stage_display,
        )

        state = PipelineState(
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
        result = get_stage_display(state)
        assert "(hook_activation)" in result

    def test_display_no_sub_stage_no_parens(self):
        from pipeline_state import (
            PipelineState,
            get_stage_display,
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
        result = get_stage_display(state)
        assert "(" not in result


class TestGetStageDisplayFixLadder:
    def test_display_includes_fix_ladder_position(self):
        from pipeline_state import (
            PipelineState,
            get_stage_display,
        )

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            total_units=11,
            fix_ladder_position="fresh_impl",
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
        result = get_stage_display(state)
        assert "fix" in result.lower()
        assert "fresh_impl" in result

    def test_display_no_fix_ladder_when_none(self):
        from pipeline_state import (
            PipelineState,
            get_stage_display,
        )

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
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
        result = get_stage_display(state)
        assert "fix" not in result.lower()


class TestGetStageDisplayUnitOnly:
    def test_display_unit_without_total(self):
        from pipeline_state import (
            PipelineState,
            get_stage_display,
        )

        state = PipelineState(
            stage="3",
            sub_stage=None,
            current_unit=3,
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
        result = get_stage_display(state)
        assert "3" in result
        assert "Unit" in result


# ---------------------------------------------------------------
# recover_state_from_markers: correct marker filenames
# ---------------------------------------------------------------


class TestRecoverStateMarkersCorrect:
    def test_recover_with_complete_json_markers(
        self, tmp_path
    ):
        from pipeline_state import (
            recover_state_from_markers,
        )

        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        marker_data = {"unit": 1, "status": "complete"}
        (
            markers_dir / "unit_1_complete.json"
        ).write_text(json.dumps(marker_data))

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert hasattr(result, "stage")
        assert result.stage == "3"
        assert len(result.verified_units) == 1

    def test_recover_multiple_markers_uses_max_unit(
        self, tmp_path
    ):
        from pipeline_state import (
            recover_state_from_markers,
        )

        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        for i in [1, 2, 3]:
            data = {"unit": i, "status": "complete"}
            fname = f"unit_{i}_complete.json"
            (markers_dir / fname).write_text(
                json.dumps(data)
            )

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert result.current_unit == 4
        assert len(result.verified_units) == 3

    def test_recover_no_svp_dir_returns_none(
        self, tmp_path
    ):
        """When .svp directory does not exist, returns
        None."""
        from pipeline_state import (
            recover_state_from_markers,
        )

        result = recover_state_from_markers(tmp_path)
        assert result is None

    def test_recover_svp_dir_no_markers_dir(
        self, tmp_path
    ):
        """When .svp exists but markers dir does not,
        and no pipeline_state.json, returns None."""
        from pipeline_state import (
            recover_state_from_markers,
        )

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        result = recover_state_from_markers(tmp_path)
        assert result is None

    def test_recover_malformed_marker_skipped(
        self, tmp_path
    ):
        from pipeline_state import (
            recover_state_from_markers,
        )

        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True)
        # One valid, one malformed
        valid = {"unit": 2, "status": "complete"}
        (
            markers_dir / "unit_2_complete.json"
        ).write_text(json.dumps(valid))
        (
            markers_dir / "unit_3_complete.json"
        ).write_text("{bad json")

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert len(result.verified_units) == 1

    def test_recover_falls_back_to_load_state(
        self, tmp_path
    ):
        """When .svp exists but no markers, and a valid
        pipeline_state.json exists, load it."""
        from pipeline_state import (
            create_initial_state,
            recover_state_from_markers,
            save_state,
        )

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        state = create_initial_state("test")
        save_state(state, tmp_path)

        result = recover_state_from_markers(tmp_path)
        assert result is not None
        assert result.stage == "0"


# ---------------------------------------------------------------
# PipelineState: debug_session dict auto-conversion
# ---------------------------------------------------------------


class TestPipelineStateDebugSessionDict:
    def test_init_converts_dict_to_debug_session(self):
        from pipeline_state import (
            DebugSession,
            PipelineState,
        )

        ds_dict = {
            "bug_id": 10,
            "description": "auto-convert test",
            "classification": None,
            "affected_units": [],
            "regression_test_path": None,
            "phase": "triage",
            "authorized": False,
            "triage_refinement_count": 0,
            "repair_retry_count": 0,
            "created_at": "2025-01-01T00:00:00",
        }
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
            debug_session=ds_dict,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert isinstance(ps.debug_session, DebugSession)
        assert ps.debug_session.bug_id == 10
        assert ps.debug_session.description == (
            "auto-convert test"
        )


# ---------------------------------------------------------------
# validate_state: pre_stage_3 sub_stage validation
# ---------------------------------------------------------------


class TestValidatePreStage3:
    def test_pre_stage_3_none_sub_stage_valid(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

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

    def test_pre_stage_3_invalid_sub_stage(self):
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="pre_stage_3",
            sub_stage="test_generation",
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

    def test_pre_stage_3_redo_sub_stage_valid(self):
        """Redo profile sub-stages valid for any stage
        including pre_stage_3."""
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="pre_stage_3",
            sub_stage="redo_profile_delivery",
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


# ---------------------------------------------------------------
# validate_state: stage 0 with None sub_stage
# ---------------------------------------------------------------


class TestValidateStage0NoneSubStage:
    def test_stage_0_none_sub_stage_valid(self):
        """Stage 0 allows None sub_stage (initial entry)."""
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="0",
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


# ---------------------------------------------------------------
# validate_state: multiple errors at once
# ---------------------------------------------------------------


class TestValidateMultipleErrors:
    def test_multiple_validation_errors_reported(self):
        """When both counter and fix_ladder are invalid,
        both errors should be reported."""
        from pipeline_state import (
            PipelineState,
            validate_state,
        )

        state = PipelineState(
            stage="0",
            sub_stage="hook_activation",
            current_unit=None,
            total_units=None,
            fix_ladder_position="bogus_position",
            red_run_retries=-5,
            alignment_iteration=-3,
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
        assert len(errors) >= 3


# ---------------------------------------------------------------
# DebugSession: default values when created with no args
# ---------------------------------------------------------------


class TestDebugSessionDefaults:
    def test_debug_session_default_values(self):
        from pipeline_state import DebugSession

        ds = DebugSession()
        assert ds.bug_id == 0
        assert ds.description == ""
        assert ds.classification is None
        assert ds.affected_units == []
        assert ds.regression_test_path is None
        assert ds.phase == "triage"
        assert ds.authorized is False
        assert ds.triage_refinement_count == 0
        assert ds.repair_retry_count == 0
        assert isinstance(ds.created_at, str)


# ---------------------------------------------------------------
# save_state: no temp files left behind
# ---------------------------------------------------------------


class TestSaveStateNoTempFiles:
    def test_no_temp_files_after_save(self, tmp_path):
        """After save_state, no .pipeline_state_*.tmp
        files should remain."""
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test")
        save_state(state, tmp_path)
        tmp_files = list(
            tmp_path.glob(".pipeline_state_*.tmp")
        )
        assert len(tmp_files) == 0

    def test_save_state_file_ends_with_newline(
        self, tmp_path
    ):
        """Written JSON file should end with newline."""
        from pipeline_state import (
            create_initial_state,
            save_state,
        )

        state = create_initial_state("test")
        save_state(state, tmp_path)
        state_file = tmp_path / "pipeline_state.json"
        content = state_file.read_text()
        assert content.endswith("\n")
