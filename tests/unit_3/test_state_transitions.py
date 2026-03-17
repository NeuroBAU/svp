"""
Tests for Unit 3: State Transition Engine.

Synthetic data generation assumptions:
- PipelineState and DebugSession are imported from
  src.unit_2.stub (the stub module for Unit 2).
- TransitionError is imported from src.unit_3.stub.
- All transition functions are imported from src.unit_3.stub.
- All file I/O tests use pytest tmp_path to avoid filesystem
  side effects.
- PipelineState instances are constructed with synthetic
  defaults: stage="3", sub_stage="test_generation",
  current_unit=1, total_units=5 unless otherwise specified.
- ISO timestamp strings use "2025-01-01T00:00:00" as a
  synthetic default.
- Fix ladder positions follow the sequence:
  [None, "fresh_test", "hint_test", "fresh_impl",
   "diagnostic", "diagnostic_impl"].
- Debug sessions use synthetic bug_id=1,
  description="test bug", phase="triage".
- version_document tests create temp files with known
  content in tmp_path.
- project_root is set to tmp_path for all functions that
  require it.
- redo_triggered_from uses a synthetic dict with
  {"stage": "3", "unit": 1} as default.
- Quality gate sub-stages include "quality_gate_a",
  "quality_gate_b", "quality_gate_a_retry",
  "quality_gate_b_retry".
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------
# Helpers: synthetic PipelineState construction
# ---------------------------------------------------------------


def _make_state(**overrides):
    """Build a synthetic PipelineState with sensible defaults."""
    from pipeline_state import PipelineState

    defaults = {
        "stage": "3",
        "sub_stage": "test_generation",
        "current_unit": 1,
        "total_units": 5,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test-project",
        "last_action": None,
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _make_debug_session(**overrides):
    """Build a synthetic DebugSession."""
    from pipeline_state import DebugSession

    defaults = {
        "bug_id": 1,
        "description": "test bug",
        "classification": None,
        "affected_units": [],
        "regression_test_path": None,
        "phase": "triage",
        "authorized": False,
        "created_at": "2025-01-01T00:00:00",
    }
    defaults.update(overrides)
    return DebugSession(**defaults)


# ---------------------------------------------------------------
# Section 1: TransitionError
# ---------------------------------------------------------------


class TestTransitionError:
    def test_is_exception(self):
        from state_transitions import TransitionError

        assert issubclass(TransitionError, Exception)

    def test_can_be_raised(self):
        from state_transitions import TransitionError

        with pytest.raises(TransitionError):
            raise TransitionError("precondition failed")

    def test_message_preserved(self):
        from state_transitions import TransitionError

        err = TransitionError("bad transition")
        assert str(err) == "bad transition"


# ---------------------------------------------------------------
# Section 2: advance_stage
# ---------------------------------------------------------------


class TestAdvanceStage:
    def test_returns_new_state(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="0")
        result = advance_stage(state, tmp_path)
        assert result is not state

    def test_does_not_mutate_input(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="0")
        original_stage = state.stage
        advance_stage(state, tmp_path)
        assert state.stage == original_stage

    def test_advances_from_0_to_1(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="0")
        result = advance_stage(state, tmp_path)
        assert result.stage == "1"

    def test_advances_from_1_to_2(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="1")
        result = advance_stage(state, tmp_path)
        assert result.stage == "2"

    def test_advances_from_2_to_pre_stage_3(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="2")
        result = advance_stage(state, tmp_path)
        assert result.stage == "pre_stage_3"

    def test_advances_from_pre_stage_3_to_3(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="pre_stage_3")
        result = advance_stage(state, tmp_path)
        assert result.stage == "3"

    def test_advances_from_4_to_5(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="4")
        result = advance_stage(state, tmp_path)
        assert result.stage == "5"


# ---------------------------------------------------------------
# Section 3: advance_sub_stage
# ---------------------------------------------------------------


class TestAdvanceSubStage:
    def test_returns_new_state(self, tmp_path):
        from state_transitions import advance_sub_stage

        state = _make_state(stage="3", sub_stage="test_generation")
        result = advance_sub_stage(state, "red_run", tmp_path)
        assert result is not state

    def test_sets_sub_stage(self, tmp_path):
        from state_transitions import advance_sub_stage

        state = _make_state(stage="3", sub_stage="test_generation")
        result = advance_sub_stage(state, "red_run", tmp_path)
        assert result.sub_stage == "red_run"

    def test_does_not_mutate_input(self, tmp_path):
        from state_transitions import advance_sub_stage

        state = _make_state(stage="3", sub_stage="test_generation")
        advance_sub_stage(state, "red_run", tmp_path)
        assert state.sub_stage == "test_generation"


# ---------------------------------------------------------------
# Section 4: complete_unit
# ---------------------------------------------------------------


class TestCompleteUnit:
    def test_returns_new_state(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(current_unit=1, total_units=5)
        result = complete_unit(state, 1, tmp_path)
        assert result is not state

    def test_does_not_mutate_input(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(current_unit=1, total_units=5)
        original_unit = state.current_unit
        complete_unit(state, 1, tmp_path)
        assert state.current_unit == original_unit

    def test_updates_verified_units(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(
            current_unit=1,
            total_units=5,
            verified_units=[],
        )
        result = complete_unit(state, 1, tmp_path)
        unit_nums = [v.get("unit_number", v.get("unit")) for v in result.verified_units]
        assert 1 in unit_nums

    def test_resets_sub_stage_to_none(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(
            current_unit=1,
            total_units=5,
            sub_stage="unit_completion",
        )
        result = complete_unit(state, 1, tmp_path)
        assert result.sub_stage is None

    def test_resets_fix_ladder_position(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(
            current_unit=1,
            total_units=5,
            fix_ladder_position="fresh_test",
        )
        result = complete_unit(state, 1, tmp_path)
        assert result.fix_ladder_position is None

    def test_resets_red_run_retries(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(
            current_unit=1,
            total_units=5,
            red_run_retries=3,
        )
        result = complete_unit(state, 1, tmp_path)
        assert result.red_run_retries == 0

    def test_advances_current_unit(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(current_unit=1, total_units=5)
        result = complete_unit(state, 1, tmp_path)
        assert result.current_unit == 2

    def test_advances_stage_when_last_unit(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(current_unit=5, total_units=5)
        result = complete_unit(state, 5, tmp_path)
        assert result.stage == "4"


# ---------------------------------------------------------------
# Section 5: advance_fix_ladder
# ---------------------------------------------------------------


class TestAdvanceFixLadder:
    def test_returns_new_state(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_test")
        assert result is not state

    def test_does_not_mutate_input(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position=None)
        advance_fix_ladder(state, "fresh_test")
        assert state.fix_ladder_position is None

    def test_none_to_fresh_test(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_test")
        assert result.fix_ladder_position == "fresh_test"

    def test_fresh_test_to_hint_test(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position="fresh_test")
        result = advance_fix_ladder(state, "hint_test")
        assert result.fix_ladder_position == "hint_test"

    def test_hint_test_to_fresh_impl(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position="hint_test")
        result = advance_fix_ladder(state, "fresh_impl")
        assert result.fix_ladder_position == "fresh_impl"

    def test_fresh_impl_to_diagnostic(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position="fresh_impl")
        result = advance_fix_ladder(state, "diagnostic")
        assert result.fix_ladder_position == "diagnostic"

    def test_diagnostic_to_diagnostic_impl(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position="diagnostic")
        result = advance_fix_ladder(state, "diagnostic_impl")
        assert result.fix_ladder_position == "diagnostic_impl"

    def test_invalid_transition_raises(self):
        from state_transitions import (
            TransitionError,
            advance_fix_ladder,
        )

        state = _make_state(fix_ladder_position=None)
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "diagnostic")

    def test_skip_ladder_raises(self):
        from state_transitions import (
            TransitionError,
            advance_fix_ladder,
        )

        state = _make_state(fix_ladder_position="fresh_test")
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "diagnostic_impl")

    def test_backward_transition_raises(self):
        from state_transitions import (
            TransitionError,
            advance_fix_ladder,
        )

        state = _make_state(fix_ladder_position="hint_test")
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "fresh_test")


# ---------------------------------------------------------------
# Section 7: increment/reset red_run_retries
# ---------------------------------------------------------------


class TestIncrementRedRunRetries:
    def test_returns_new_state(self):
        from state_transitions import (
            increment_red_run_retries,
        )

        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert result is not state

    def test_increments_by_one(self):
        from state_transitions import (
            increment_red_run_retries,
        )

        state = _make_state(red_run_retries=2)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 3

    def test_does_not_mutate_input(self):
        from state_transitions import (
            increment_red_run_retries,
        )

        state = _make_state(red_run_retries=1)
        increment_red_run_retries(state)
        assert state.red_run_retries == 1


class TestResetRedRunRetries:
    def test_returns_new_state(self):
        from state_transitions import (
            reset_red_run_retries,
        )

        state = _make_state(red_run_retries=3)
        result = reset_red_run_retries(state)
        assert result is not state

    def test_resets_to_zero(self):
        from state_transitions import (
            reset_red_run_retries,
        )

        state = _make_state(red_run_retries=5)
        result = reset_red_run_retries(state)
        assert result.red_run_retries == 0

    def test_does_not_mutate_input(self):
        from state_transitions import (
            reset_red_run_retries,
        )

        state = _make_state(red_run_retries=3)
        reset_red_run_retries(state)
        assert state.red_run_retries == 3


# ---------------------------------------------------------------
# Section 8: increment/reset alignment_iteration
# ---------------------------------------------------------------


class TestIncrementAlignmentIteration:
    def test_returns_new_state(self):
        from state_transitions import (
            increment_alignment_iteration,
        )

        state = _make_state(alignment_iteration=0)
        result = increment_alignment_iteration(state)
        assert result is not state

    def test_increments_by_one(self):
        from state_transitions import (
            increment_alignment_iteration,
        )

        state = _make_state(alignment_iteration=1)
        result = increment_alignment_iteration(state)
        assert result.alignment_iteration == 2

    def test_does_not_mutate_input(self):
        from state_transitions import (
            increment_alignment_iteration,
        )

        state = _make_state(alignment_iteration=0)
        increment_alignment_iteration(state)
        assert state.alignment_iteration == 0



# ---------------------------------------------------------------
# Section 10: rollback_to_unit
# ---------------------------------------------------------------


class TestRollbackToUnit:
    def test_returns_new_state(self, tmp_path):
        from state_transitions import rollback_to_unit

        state = _make_state(current_unit=3)
        result = rollback_to_unit(state, 1, tmp_path)
        assert result is not state

    def test_sets_current_unit(self, tmp_path):
        from state_transitions import rollback_to_unit

        state = _make_state(current_unit=3)
        result = rollback_to_unit(state, 1, tmp_path)
        assert result.current_unit == 1

    def test_does_not_mutate_input(self, tmp_path):
        from state_transitions import rollback_to_unit

        state = _make_state(current_unit=3)
        rollback_to_unit(state, 1, tmp_path)
        assert state.current_unit == 3


# ---------------------------------------------------------------
# Section 11: restart_from_stage
# ---------------------------------------------------------------


class TestRestartFromStage:
    def test_returns_new_state(self, tmp_path):
        from state_transitions import restart_from_stage

        state = _make_state(stage="3")
        result = restart_from_stage(state, "2", "redo request", tmp_path)
        assert result is not state

    def test_sets_target_stage(self, tmp_path):
        from state_transitions import restart_from_stage

        state = _make_state(stage="3")
        result = restart_from_stage(state, "2", "redo request", tmp_path)
        assert result.stage == "2"

    def test_does_not_mutate_input(self, tmp_path):
        from state_transitions import restart_from_stage

        state = _make_state(stage="3")
        restart_from_stage(state, "2", "redo request", tmp_path)
        assert state.stage == "3"


# ---------------------------------------------------------------
# Section 12: version_document
# ---------------------------------------------------------------


class TestVersionDocument:
    def test_returns_tuple_of_two_paths(self, tmp_path):
        from state_transitions import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("content")
        history = tmp_path / "history"
        history.mkdir()
        result = version_document(doc, history, "changes", "trigger")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], Path)

    def test_raises_file_not_found(self, tmp_path):
        from state_transitions import version_document

        doc = tmp_path / "nonexistent.md"
        history = tmp_path / "history"
        history.mkdir()
        with pytest.raises(FileNotFoundError):
            version_document(doc, history, "changes", "trigger")


# ---------------------------------------------------------------
# Section 13: Debug session transitions
# ---------------------------------------------------------------


class TestEnterDebugSession:
    def test_returns_new_state(self):
        from state_transitions import (
            enter_debug_session,
        )

        state = _make_state(stage="5")
        result = enter_debug_session(state, "something is broken")
        assert result is not state

    def test_sets_debug_session(self):
        from state_transitions import (
            enter_debug_session,
        )

        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "something is broken")
        assert result.debug_session is not None

    def test_debug_description(self):
        from state_transitions import (
            enter_debug_session,
        )

        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "button does not work")
        assert result.debug_session.description == "button does not work"

    def test_does_not_mutate_input(self):
        from state_transitions import (
            enter_debug_session,
        )

        state = _make_state(stage="5", debug_session=None)
        enter_debug_session(state, "bug")
        assert state.debug_session is None


class TestAuthorizeDebugSession:
    def test_returns_new_state(self):
        from state_transitions import (
            authorize_debug_session,
        )

        ds = _make_debug_session(authorized=False)
        state = _make_state(debug_session=ds)
        result = authorize_debug_session(state)
        assert result is not state

    def test_sets_authorized_true(self):
        from state_transitions import (
            authorize_debug_session,
        )

        ds = _make_debug_session(authorized=False)
        state = _make_state(debug_session=ds)
        result = authorize_debug_session(state)
        assert result.debug_session.authorized is True

    def test_raises_without_session(self):
        from state_transitions import (
            TransitionError,
            authorize_debug_session,
        )

        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            authorize_debug_session(state)


class TestCompleteDebugSession:
    def test_returns_new_state(self):
        from state_transitions import (
            complete_debug_session,
        )

        ds = _make_debug_session(authorized=True)
        state = _make_state(debug_session=ds)
        result = complete_debug_session(state, "fixed the bug")
        assert result is not state

    def test_clears_debug_session(self):
        from state_transitions import (
            complete_debug_session,
        )

        ds = _make_debug_session(authorized=True)
        state = _make_state(debug_session=ds, debug_history=[])
        result = complete_debug_session(state, "fixed")
        assert result.debug_session is None

    def test_appends_to_debug_history(self):
        from state_transitions import (
            complete_debug_session,
        )

        ds = _make_debug_session(authorized=True)
        state = _make_state(debug_session=ds, debug_history=[])
        result = complete_debug_session(state, "fixed")
        assert len(result.debug_history) == 1

    def test_raises_without_session(self):
        from state_transitions import (
            TransitionError,
            complete_debug_session,
        )

        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            complete_debug_session(state, "fix")


class TestAbandonDebugSession:
    def test_returns_new_state(self):
        from state_transitions import (
            abandon_debug_session,
        )

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        result = abandon_debug_session(state)
        assert result is not state

    def test_clears_debug_session(self):
        from state_transitions import (
            abandon_debug_session,
        )

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        result = abandon_debug_session(state)
        assert result.debug_session is None

    def test_raises_without_session(self):
        from state_transitions import (
            TransitionError,
            abandon_debug_session,
        )

        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            abandon_debug_session(state)


class TestUpdateDebugPhase:
    def test_returns_new_state(self):
        from state_transitions import (
            update_debug_phase,
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = update_debug_phase(state, "investigation")
        assert result is not state

    def test_sets_phase(self):
        from state_transitions import (
            update_debug_phase,
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = update_debug_phase(state, "investigation")
        assert result.debug_session.phase == "investigation"

    def test_raises_without_session(self):
        from state_transitions import (
            TransitionError,
            update_debug_phase,
        )

        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            update_debug_phase(state, "investigation")


class TestSetDebugClassification:
    def test_returns_new_state(self):
        from state_transitions import (
            set_debug_classification,
        )

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        result = set_debug_classification(state, "single_unit", [3])
        assert result is not state

    def test_sets_classification(self):
        from state_transitions import (
            set_debug_classification,
        )

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        result = set_debug_classification(state, "cross_unit", [1, 2])
        assert result.debug_session.classification == "cross_unit"

    def test_sets_affected_units(self):
        from state_transitions import (
            set_debug_classification,
        )

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        result = set_debug_classification(state, "single_unit", [5])
        assert result.debug_session.affected_units == [5]

    def test_raises_without_session(self):
        from state_transitions import (
            TransitionError,
            set_debug_classification,
        )

        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            set_debug_classification(state, "single_unit", [1])


# ---------------------------------------------------------------
# Section 14: set_delivered_repo_path
# ---------------------------------------------------------------


class TestSetDeliveredRepoPath:
    def test_returns_new_state(self):
        from state_transitions import (
            set_delivered_repo_path,
        )

        state = _make_state(stage="5", delivered_repo_path=None)
        result = set_delivered_repo_path(state, "/tmp/delivered-repo")
        assert result is not state

    def test_sets_path(self):
        from state_transitions import (
            set_delivered_repo_path,
        )

        state = _make_state(delivered_repo_path=None)
        result = set_delivered_repo_path(state, "/tmp/delivered-repo")
        assert result.delivered_repo_path == "/tmp/delivered-repo"

    def test_does_not_mutate_input(self):
        from state_transitions import (
            set_delivered_repo_path,
        )

        state = _make_state(delivered_repo_path=None)
        set_delivered_repo_path(state, "/tmp/delivered-repo")
        assert state.delivered_repo_path is None


# ---------------------------------------------------------------
# Section 15: Quality gate transitions
# ---------------------------------------------------------------


class TestEnterQualityGate:
    def test_returns_new_state(self):
        from state_transitions import enter_quality_gate

        state = _make_state(
            stage="3",
            sub_stage="test_generation",
        )
        result = enter_quality_gate(state, "quality_gate_a")
        assert result is not state

    def test_sets_sub_stage(self):
        from state_transitions import enter_quality_gate

        state = _make_state(
            stage="3",
            sub_stage="test_generation",
        )
        result = enter_quality_gate(state, "quality_gate_a")
        assert result.sub_stage == "quality_gate_a"

    def test_quality_gate_b(self):
        from state_transitions import enter_quality_gate

        state = _make_state(
            stage="3",
            sub_stage="implementation",
        )
        result = enter_quality_gate(state, "quality_gate_b")
        assert result.sub_stage == "quality_gate_b"

    def test_does_not_mutate_input(self):
        from state_transitions import enter_quality_gate

        state = _make_state(
            stage="3",
            sub_stage="test_generation",
        )
        enter_quality_gate(state, "quality_gate_a")
        assert state.sub_stage == "test_generation"


class TestAdvanceFromQualityGate:
    def test_returns_new_state(self):
        from state_transitions import (
            advance_from_quality_gate,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        result = advance_from_quality_gate(state, "red_run")
        assert result is not state

    def test_gate_a_to_red_run(self):
        from state_transitions import (
            advance_from_quality_gate,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        result = advance_from_quality_gate(state, "red_run")
        assert result.sub_stage == "red_run"

    def test_gate_b_to_green_run(self):
        from state_transitions import (
            advance_from_quality_gate,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
        )
        result = advance_from_quality_gate(state, "green_run")
        assert result.sub_stage == "green_run"

    def test_does_not_mutate_input(self):
        from state_transitions import (
            advance_from_quality_gate,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        advance_from_quality_gate(state, "red_run")
        assert state.sub_stage == "quality_gate_a"


class TestEnterQualityGateRetry:
    def test_returns_new_state(self):
        from state_transitions import (
            enter_quality_gate_retry,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        result = enter_quality_gate_retry(state, "quality_gate_a_retry")
        assert result is not state

    def test_sets_retry_sub_stage_a(self):
        from state_transitions import (
            enter_quality_gate_retry,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        result = enter_quality_gate_retry(state, "quality_gate_a_retry")
        assert result.sub_stage == "quality_gate_a_retry"

    def test_sets_retry_sub_stage_b(self):
        from state_transitions import (
            enter_quality_gate_retry,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
        )
        result = enter_quality_gate_retry(state, "quality_gate_b_retry")
        assert result.sub_stage == "quality_gate_b_retry"

    def test_does_not_mutate_input(self):
        from state_transitions import (
            enter_quality_gate_retry,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        enter_quality_gate_retry(state, "quality_gate_a_retry")
        assert state.sub_stage == "quality_gate_a"


class TestFailQualityGateToLadder:
    def test_returns_new_state(self):
        from state_transitions import (
            fail_quality_gate_to_ladder,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
        )
        result = fail_quality_gate_to_ladder(state, "fresh_test")
        assert result is not state

    def test_gate_a_failure_enters_test_ladder(self):
        from state_transitions import (
            fail_quality_gate_to_ladder,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
        )
        result = fail_quality_gate_to_ladder(state, "fresh_test")
        assert result.fix_ladder_position == "fresh_test"

    def test_gate_b_failure_enters_impl_ladder(self):
        from state_transitions import (
            fail_quality_gate_to_ladder,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b_retry",
        )
        result = fail_quality_gate_to_ladder(state, "fresh_impl")
        assert result.fix_ladder_position == "fresh_impl"

    def test_does_not_mutate_input(self):
        from state_transitions import (
            fail_quality_gate_to_ladder,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            fix_ladder_position=None,
        )
        fail_quality_gate_to_ladder(state, "fresh_test")
        assert state.fix_ladder_position is None


# ---------------------------------------------------------------
# Section 16: Redo profile revision transitions
# ---------------------------------------------------------------


class TestEnterRedoProfileRevision:
    def test_returns_new_state(self):
        from state_transitions import (
            enter_redo_profile_revision,
        )

        state = _make_state(stage="3")
        result = enter_redo_profile_revision(state, "delivery")
        assert result is not state

    def test_does_not_mutate_input(self):
        from state_transitions import (
            enter_redo_profile_revision,
        )

        state = _make_state(stage="3")
        original_sub = state.sub_stage
        enter_redo_profile_revision(state, "delivery")
        assert state.sub_stage == original_sub


class TestCompleteRedoProfileRevision:
    def test_returns_new_state(self):
        from state_transitions import (
            complete_redo_profile_revision,
        )

        state = _make_state(sub_stage="redo_profile_delivery")
        result = complete_redo_profile_revision(state)
        assert result is not state

    def test_does_not_mutate_input(self):
        from state_transitions import (
            complete_redo_profile_revision,
        )

        state = _make_state(sub_stage="redo_profile_delivery")
        complete_redo_profile_revision(state)
        assert state.sub_stage == "redo_profile_delivery"

# ---------------------------------------------------------------
# Section 18: Immutability invariant (all functions)
# ---------------------------------------------------------------


class TestImmutabilityInvariant:
    """All transition functions return new PipelineState
    and do not mutate the input."""

    def test_advance_stage_immutable(self, tmp_path):
        from state_transitions import advance_stage

        state = _make_state(stage="0")
        old_dict = state.to_dict()
        advance_stage(state, tmp_path)
        assert state.to_dict() == old_dict

    def test_advance_sub_stage_immutable(self, tmp_path):
        from state_transitions import advance_sub_stage

        state = _make_state(
            stage="3",
            sub_stage="test_generation",
        )
        old_dict = state.to_dict()
        advance_sub_stage(state, "red_run", tmp_path)
        assert state.to_dict() == old_dict

    def test_complete_unit_immutable(self, tmp_path):
        from state_transitions import complete_unit

        state = _make_state(current_unit=1, total_units=5)
        old_dict = state.to_dict()
        complete_unit(state, 1, tmp_path)
        assert state.to_dict() == old_dict

    def test_advance_fix_ladder_immutable(self):
        from state_transitions import advance_fix_ladder

        state = _make_state(fix_ladder_position=None)
        old_dict = state.to_dict()
        advance_fix_ladder(state, "fresh_test")
        assert state.to_dict() == old_dict

    def test_enter_debug_session_immutable(self):
        from state_transitions import (
            enter_debug_session,
        )

        state = _make_state(stage="5", debug_session=None)
        old_dict = state.to_dict()
        enter_debug_session(state, "bug")
        assert state.to_dict() == old_dict


    def test_set_delivered_repo_path_immutable(self):
        from state_transitions import (
            set_delivered_repo_path,
        )

        state = _make_state(delivered_repo_path=None)
        old_dict = state.to_dict()
        set_delivered_repo_path(state, "/tmp/repo")
        assert state.to_dict() == old_dict
