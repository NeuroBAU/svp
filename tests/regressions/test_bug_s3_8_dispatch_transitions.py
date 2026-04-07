"""Regression tests for Bug S3-8: Unit 14 dispatch must use Unit 6 transition functions.

Verifies that dispatch_gate_response and dispatch_agent_status call the
appropriate Unit 6 transition functions instead of setting state fields directly.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline_state import PipelineState
from routing import (
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
)


def _make_state(**overrides):
    """Build a minimal PipelineState with defaults."""
    defaults = {
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
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _make_debug_session(**overrides):
    """Build a minimal debug_session dict with defaults."""
    session = {
        "authorized": True,
        "bug_number": 1,
        "classification": None,
        "affected_units": [3],
        "phase": "triage",
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    session.update(overrides)
    return session


# ---------------------------------------------------------------------------
# dispatch_gate_response: advance_stage usage
# ---------------------------------------------------------------------------


class TestGateResponseCallsAdvanceStage:
    """Bug S3-8: gates that change stage+sub_stage+current_unit+fix_ladder+red_run
    must call advance_stage instead of setting fields directly."""

    @patch("routing.advance_stage")
    def test_gate_0_3_profile_approved_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="1")
        state = _make_state(stage="0", sub_stage="project_profile")
        dispatch_gate_response(state, "gate_0_3_profile_approval", "PROFILE APPROVED", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "1")

    @patch("routing.advance_stage")
    def test_gate_2_2_approve_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="pre_stage_3")
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        dispatch_gate_response(state, "gate_2_2_blueprint_post_review", "APPROVE", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "pre_stage_3")

    @patch("routing.advance_stage")
    def test_gate_2_3_restart_spec_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="1")
        state = _make_state(stage="2", sub_stage="alignment_check")
        dispatch_gate_response(state, "gate_2_3_alignment_exhausted", "RESTART SPEC", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "1")

    @patch("routing.advance_stage")
    def test_gate_3_2_fix_spec_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="1")
        state = _make_state(stage="3", sub_stage="implementation", current_unit=1)
        dispatch_gate_response(state, "gate_3_2_diagnostic_decision", "FIX SPEC", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "1")

    @patch("routing.advance_stage")
    def test_gate_3_completion_force_advance_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="4")
        state = _make_state(stage="3", current_unit=None, sub_stage=None)
        dispatch_gate_response(state, "gate_3_completion_failure", "FORCE ADVANCE", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "4")

    @patch("routing.advance_stage")
    def test_gate_4_3_accept_adaptations_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="5")
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        dispatch_gate_response(state, "gate_4_3_adaptation_review", "ACCEPT ADAPTATIONS", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "5")

    @patch("routing.advance_stage")
    def test_gate_5_3_fix_spec_calls_advance_stage(self, mock_advance):
        mock_advance.return_value = _make_state(stage="1")
        state = _make_state(stage="5", sub_stage="compliance_scan")
        dispatch_gate_response(state, "gate_5_3_unused_functions", "FIX SPEC", Path("/tmp"))
        mock_advance.assert_called_once_with(state, "1")


# ---------------------------------------------------------------------------
# dispatch_gate_response: restart_from_stage usage
# ---------------------------------------------------------------------------


class TestGateResponseCallsRestartFromStage:
    """Bug S3-8: gates that restart to stage 2 (with alignment reset)
    must call restart_from_stage."""

    @patch("routing.restart_from_stage")
    def test_gate_3_2_fix_blueprint_calls_restart_from_stage(self, mock_restart):
        mock_restart.return_value = _make_state(stage="2", sub_stage="blueprint_dialog")
        state = _make_state(stage="3", sub_stage="implementation", current_unit=1)
        dispatch_gate_response(state, "gate_3_2_diagnostic_decision", "FIX BLUEPRINT", Path("/tmp"))
        mock_restart.assert_called_once_with(state, "2")

    @patch("routing.restart_from_stage")
    def test_gate_4_1_fix_blueprint_calls_restart_from_stage(self, mock_restart):
        mock_restart.return_value = _make_state(stage="2", sub_stage="blueprint_dialog")
        state = _make_state(stage="4")
        dispatch_gate_response(state, "gate_4_1_integration_failure", "FIX BLUEPRINT", Path("/tmp"))
        mock_restart.assert_called_once_with(state, "2")

    @patch("routing.restart_from_stage")
    def test_gate_5_2_fix_blueprint_calls_restart_from_stage(self, mock_restart):
        mock_restart.return_value = _make_state(stage="2", sub_stage="blueprint_dialog")
        state = _make_state(stage="5")
        dispatch_gate_response(state, "gate_5_2_assembly_exhausted", "FIX BLUEPRINT", Path("/tmp"))
        mock_restart.assert_called_once_with(state, "2")


# ---------------------------------------------------------------------------
# dispatch_gate_response: rollback_to_unit usage
# ---------------------------------------------------------------------------


class TestGateResponseCallsRollbackToUnit:
    """Bug S3-8: gate_6_2 FIX UNIT must call rollback_to_unit."""

    @patch("routing.rollback_to_unit")
    @patch("routing.update_debug_phase")
    @patch("routing.set_debug_classification")
    def test_gate_6_2_fix_unit_calls_rollback_to_unit(
        self, mock_classify, mock_phase, mock_rollback
    ):
        ds = _make_debug_session(affected_units=[3])
        state = _make_state(stage="3", current_unit=5, debug_session=ds)

        mock_classify.return_value = state
        mock_phase.return_value = state
        mock_rollback.return_value = _make_state(stage="3", current_unit=3)

        dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", Path("/tmp")
        )
        mock_rollback.assert_called_once_with(state, 3)


# ---------------------------------------------------------------------------
# dispatch_gate_response: debug session transition functions
# ---------------------------------------------------------------------------


class TestGateResponseCallsDebugTransitions:
    """Bug S3-8: debug gates must call Unit 6 debug transition functions."""

    @patch("routing.authorize_debug_session")
    def test_gate_6_0_authorize_calls_authorize_debug_session(self, mock_auth):
        ds = _make_debug_session(authorized=False)
        state = _make_state(debug_session=ds)
        mock_auth.return_value = _make_state(debug_session=_make_debug_session(authorized=True))
        dispatch_gate_response(state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", Path("/tmp"))
        mock_auth.assert_called_once_with(state)

    @patch("routing.abandon_debug_session")
    def test_gate_6_0_abandon_calls_abandon_debug_session(self, mock_abandon):
        ds = _make_debug_session(authorized=False)
        state = _make_state(debug_session=ds)
        mock_abandon.return_value = _make_state(debug_session=None)
        dispatch_gate_response(state, "gate_6_0_debug_permission", "ABANDON DEBUG", Path("/tmp"))
        mock_abandon.assert_called_once_with(state)

    @patch("routing.update_debug_phase")
    def test_gate_6_1_test_correct_calls_update_debug_phase(self, mock_phase):
        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        mock_phase.return_value = _make_state(debug_session=_make_debug_session(phase="lessons_learned"))
        dispatch_gate_response(state, "gate_6_1_regression_test", "TEST CORRECT", Path("/tmp"))
        mock_phase.assert_called_once_with(state, "lessons_learned")

    @patch("routing.complete_debug_session")
    def test_gate_6_5_commit_approved_calls_complete_debug_session(self, mock_complete):
        ds = _make_debug_session(authorized=True)
        state = _make_state(debug_session=ds)
        mock_complete.return_value = _make_state(debug_session=None)
        dispatch_gate_response(state, "gate_6_5_debug_commit", "COMMIT APPROVED", Path("/tmp"))
        mock_complete.assert_called_once_with(state)

    @patch("routing.enter_debug_session")
    def test_gate_3_completion_investigate_calls_enter_debug_session(self, mock_enter):
        state = _make_state(stage="3", debug_session=None)
        mock_enter.return_value = _make_state(
            debug_session=_make_debug_session(authorized=False, bug_number=0)
        )
        dispatch_gate_response(state, "gate_3_completion_failure", "INVESTIGATE", Path("/tmp"))
        mock_enter.assert_called_once_with(state, 0)


# ---------------------------------------------------------------------------
# dispatch_agent_status: transition function usage
# ---------------------------------------------------------------------------


class TestAgentStatusCallsTransitions:
    """Bug S3-8: agent dispatch must call Unit 6 transition functions."""

    @patch("routing.increment_alignment_iteration")
    def test_blueprint_checker_alignment_failed_calls_increment(self, mock_incr):
        mock_incr.return_value = _make_state(stage="2", alignment_iterations=1)
        state = _make_state(stage="2", sub_stage="alignment_check")
        dispatch_agent_status(state, "blueprint_checker", "ALIGNMENT_FAILED: blueprint", Path("/tmp"))
        mock_incr.assert_called_once_with(state)

    @patch("routing.restart_from_stage")
    def test_redo_classified_blueprint_calls_restart_from_stage(self, mock_restart):
        mock_restart.return_value = _make_state(stage="2", sub_stage="blueprint_dialog")
        state = _make_state(stage="3", current_unit=1)
        dispatch_agent_status(state, "redo_agent", "REDO_CLASSIFIED: blueprint", Path("/tmp"))
        mock_restart.assert_called_once_with(state, "2")

    @patch("routing.enter_redo_profile_revision")
    def test_redo_classified_profile_delivery_calls_enter_redo(self, mock_redo):
        mock_redo.return_value = _make_state(sub_stage="redo_profile_delivery")
        state = _make_state(stage="3", current_unit=1)
        dispatch_agent_status(state, "redo_agent", "REDO_CLASSIFIED: profile_delivery", Path("/tmp"))
        mock_redo.assert_called_once_with(state, "delivery")

    @patch("routing.update_debug_phase")
    def test_bug_triage_build_env_calls_update_debug_phase(self, mock_phase):
        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        mock_phase.return_value = _make_state(debug_session=_make_debug_session(phase="repair"))
        dispatch_agent_status(state, "bug_triage_agent", "TRIAGE_COMPLETE: build_env", Path("/tmp"))
        mock_phase.assert_called_once_with(state, "repair")


# ---------------------------------------------------------------------------
# dispatch_command_status: transition function usage
# ---------------------------------------------------------------------------


class TestCommandStatusCallsTransitions:
    """Bug S3-8: command dispatch must call Unit 6 transition functions."""

    @patch("routing.increment_red_run_retries")
    def test_red_run_tests_passed_calls_increment_red_run_retries(self, mock_incr):
        mock_incr.return_value = _make_state(stage="3", sub_stage="red_run", red_run_retries=1, current_unit=1)
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        dispatch_command_status(state, "test_execution", "TESTS_PASSED", sub_stage="red_run")
        mock_incr.assert_called_once_with(state)

    @patch("routing.advance_fix_ladder")
    def test_green_run_tests_failed_calls_advance_fix_ladder(self, mock_ladder):
        mock_ladder.return_value = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="fresh_impl", current_unit=1
        )
        state = _make_state(stage="3", sub_stage="green_run", current_unit=1)
        dispatch_command_status(state, "test_execution", "TESTS_FAILED", sub_stage="green_run")
        mock_ladder.assert_called_once_with(state)

    @patch("routing.complete_unit")
    def test_unit_completion_succeeded_calls_complete_unit(self, mock_complete):
        mock_complete.return_value = _make_state(
            stage="3", sub_stage="stub_generation", current_unit=2
        )
        state = _make_state(stage="3", sub_stage="unit_completion", current_unit=1)
        dispatch_command_status(state, "unit_completion", "COMMAND_SUCCEEDED", sub_stage="unit_completion")
        mock_complete.assert_called_once_with(state)

    @patch("routing.advance_fix_ladder")
    def test_quality_gate_a_retry_failed_calls_advance_fix_ladder(self, mock_ladder):
        mock_ladder.return_value = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="fresh_impl", current_unit=1
        )
        state = _make_state(stage="3", sub_stage="quality_gate_a_retry", current_unit=1)
        dispatch_command_status(state, "quality_gate", "COMMAND_FAILED", sub_stage="quality_gate_a_retry")
        mock_ladder.assert_called_once_with(state)
