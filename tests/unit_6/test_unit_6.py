"""Unit 6: State Transitions -- Test Suite

Synthetic data assumptions:
- PipelineState is constructed using the dataclass from Unit 5 with known defaults.
- VALID_STAGES = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}.
- VALID_SUB_STAGES maps each stage to its valid sub-stages (from Unit 5 constants).
- VALID_FIX_LADDER_POSITIONS = [None, "fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"].
- VALID_DEBUG_PHASES = {"triage", "repair", "regression_test", "lessons_learned",
                        "reassembly", "stage3_reentry", "commit"}.
- All transition functions accept PipelineState and return a NEW PipelineState via deep copy.
- Input PipelineState is never mutated by any transition function.
- TransitionError is raised on precondition violations.
- For enter_pass_1, the contract states precondition "profile archetype is E or F". Since the
  stub signature takes only PipelineState (no profile argument), we test based on the function
  contract: calling it should eventually set pass_ = 1. For the stub, it will raise
  NotImplementedError regardless.
- version_document performs file I/O (copies files). Tests for version_document use tmp_path
  fixtures and create real files to verify the copy behavior and pass_history update.
- complete_alignment_check with result="spec" sets sub_stage="targeted_spec_revision".
"""

import copy
from dataclasses import asdict

import pytest

from pipeline_state import (
    VALID_DEBUG_PHASES,
    VALID_STAGES,
    VALID_SUB_STAGES,
    PipelineState,
)
from state_transitions import (
    TransitionError,
    abandon_debug_session,
    advance_fix_ladder,
    advance_quality_gate_to_retry,
    advance_stage,
    advance_sub_stage,
    authorize_debug_session,
    clear_pass,
    complete_alignment_check,
    complete_debug_session,
    complete_redo_profile_revision,
    complete_unit,
    enter_alignment_check,
    enter_debug_session,
    enter_pass_1,
    enter_pass_2,
    enter_quality_gate,
    enter_redo_profile_revision,
    increment_alignment_iteration,
    increment_red_run_retries,
    mark_unit_deferred_broken,
    quality_gate_fail_to_ladder,
    quality_gate_pass,
    reset_red_run_retries,
    resolve_deferred_broken,
    restart_from_stage,
    rollback_to_unit,
    set_debug_classification,
    set_delivered_repo_path,
    update_debug_phase,
    version_document,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> PipelineState:
    """Create a PipelineState with sensible defaults, applying overrides."""
    return PipelineState(**overrides)


def _snapshot(state: PipelineState) -> dict:
    """Return a deep-copy dict snapshot of a PipelineState for comparison."""
    return copy.deepcopy(asdict(state))


# ===================================================================
# TransitionError
# ===================================================================


class TestTransitionError:
    def test_transition_error_is_an_exception(self):
        assert issubclass(TransitionError, Exception)

    def test_transition_error_can_carry_message(self):
        err = TransitionError("something went wrong")
        assert str(err) == "something went wrong"


# ===================================================================
# advance_stage
# ===================================================================


class TestAdvanceStage:
    def test_advance_stage_sets_target_stage(self):
        state = _make_state(stage="0")
        result = advance_stage(state, "1")
        assert result.stage == "1"

    def test_advance_stage_resets_sub_stage_to_none(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = advance_stage(state, "3")
        assert result.sub_stage is None

    def test_advance_stage_resets_current_unit_to_none(self):
        state = _make_state(stage="3", sub_stage="stub_generation", current_unit=5)
        result = advance_stage(state, "4")
        assert result.current_unit is None

    def test_advance_stage_resets_fix_ladder_position_to_none(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            fix_ladder_position="fresh_impl",
        )
        result = advance_stage(state, "4")
        assert result.fix_ladder_position is None

    def test_advance_stage_resets_red_run_retries_to_zero(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=3
        )
        result = advance_stage(state, "4")
        assert result.red_run_retries == 0

    def test_advance_stage_does_not_mutate_input(self):
        state = _make_state(stage="1", sub_stage=None)
        snapshot = _snapshot(state)
        advance_stage(state, "2")
        assert _snapshot(state) == snapshot

    def test_advance_stage_returns_new_object(self):
        state = _make_state(stage="0")
        result = advance_stage(state, "1")
        assert result is not state

    def test_advance_stage_invalid_target_raises_transition_error(self):
        state = _make_state(stage="0")
        with pytest.raises(TransitionError):
            advance_stage(state, "99")

    def test_advance_stage_invalid_target_non_stage_string(self):
        state = _make_state(stage="0")
        with pytest.raises(TransitionError):
            advance_stage(state, "bogus")

    def test_advance_stage_all_valid_stages(self):
        """Every member of VALID_STAGES is accepted as target_stage."""
        for target in VALID_STAGES:
            state = _make_state(stage="0")
            result = advance_stage(state, target)
            assert result.stage == target


# ===================================================================
# advance_sub_stage
# ===================================================================


class TestAdvanceSubStage:
    def test_advance_sub_stage_sets_target(self):
        state = _make_state(stage="3", sub_stage=None)
        result = advance_sub_stage(state, "stub_generation")
        assert result.sub_stage == "stub_generation"

    def test_advance_sub_stage_does_not_mutate_input(self):
        state = _make_state(stage="3", sub_stage=None)
        snapshot = _snapshot(state)
        advance_sub_stage(state, "stub_generation")
        assert _snapshot(state) == snapshot

    def test_advance_sub_stage_returns_new_object(self):
        state = _make_state(stage="3", sub_stage=None)
        result = advance_sub_stage(state, "stub_generation")
        assert result is not state

    def test_advance_sub_stage_other_fields_unchanged(self):
        state = _make_state(
            stage="3", sub_stage=None, current_unit=2, red_run_retries=1
        )
        result = advance_sub_stage(state, "test_generation")
        assert result.current_unit == 2
        assert result.red_run_retries == 1
        assert result.stage == "3"

    def test_advance_sub_stage_invalid_sub_stage_raises_transition_error(self):
        state = _make_state(stage="0")
        with pytest.raises(TransitionError):
            advance_sub_stage(state, "totally_invalid_sub_stage")


# ===================================================================
# complete_unit
# ===================================================================


class TestCompleteUnit:
    def test_complete_unit_appends_to_verified_units(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=3,
            verified_units=[],
        )
        result = complete_unit(state)
        assert len(result.verified_units) == 1

    def test_complete_unit_increments_current_unit_when_more_remain(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=3,
            verified_units=[],
        )
        result = complete_unit(state)
        assert result.current_unit == 2

    def test_complete_unit_sets_sub_stage_to_stub_generation_when_more_remain(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=3,
            verified_units=[],
        )
        result = complete_unit(state)
        assert result.sub_stage == "stub_generation"

    def test_complete_unit_sets_current_unit_none_when_all_done(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=3,
            total_units=3,
            verified_units=[
                {"unit": 1},
                {"unit": 2},
            ],
        )
        result = complete_unit(state)
        assert result.current_unit is None

    def test_complete_unit_sets_sub_stage_none_when_all_done(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=3,
            total_units=3,
            verified_units=[{"unit": 1}, {"unit": 2}],
        )
        result = complete_unit(state)
        assert result.sub_stage is None

    def test_complete_unit_resets_fix_ladder_position(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=2,
            fix_ladder_position="fresh_impl",
        )
        result = complete_unit(state)
        assert result.fix_ladder_position is None

    def test_complete_unit_resets_red_run_retries(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=2,
            red_run_retries=3,
        )
        result = complete_unit(state)
        assert result.red_run_retries == 0

    def test_complete_unit_does_not_mutate_input(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=2,
        )
        snapshot = _snapshot(state)
        complete_unit(state)
        assert _snapshot(state) == snapshot

    def test_complete_unit_precondition_current_unit_none_raises(self):
        state = _make_state(
            stage="3", sub_stage="unit_completion", current_unit=None, total_units=2
        )
        with pytest.raises(TransitionError):
            complete_unit(state)

    def test_complete_unit_precondition_wrong_sub_stage_raises(self):
        state = _make_state(
            stage="3", sub_stage="implementation", current_unit=1, total_units=2
        )
        with pytest.raises(TransitionError):
            complete_unit(state)


# ===================================================================
# advance_fix_ladder
# ===================================================================


class TestAdvanceFixLadder:
    def test_advance_from_none_to_fresh_impl(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position=None,
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "fresh_impl"

    def test_advance_from_fresh_impl_to_diagnostic(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "diagnostic"

    def test_advance_from_diagnostic_to_diagnostic_impl(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position="diagnostic",
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "diagnostic_impl"

    def test_advance_from_diagnostic_impl_to_exhausted(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "exhausted"

    def test_advance_from_none_sets_sub_stage_to_implementation(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, fix_ladder_position=None
        )
        result = advance_fix_ladder(state)
        assert result.sub_stage == "implementation"

    def test_advance_from_fresh_impl_sub_stage_unchanged(self):
        """When advancing to 'diagnostic', sub_stage is not changed by this function."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        result = advance_fix_ladder(state)
        assert result.sub_stage == "implementation"

    def test_advance_from_diagnostic_sets_sub_stage_to_implementation(self):
        """Advancing to 'diagnostic_impl' sets sub_stage to implementation."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            fix_ladder_position="diagnostic",
        )
        result = advance_fix_ladder(state)
        assert result.sub_stage == "implementation"

    def test_advance_from_diagnostic_impl_sub_stage_unchanged(self):
        """Advancing to 'exhausted' does not change sub_stage."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        result = advance_fix_ladder(state)
        assert result.sub_stage == "implementation"

    def test_advance_from_exhausted_raises_transition_error(self):
        """Cannot advance past exhausted."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position="exhausted",
        )
        with pytest.raises(TransitionError):
            advance_fix_ladder(state)

    def test_advance_fix_ladder_does_not_mutate_input(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position=None,
        )
        snapshot = _snapshot(state)
        advance_fix_ladder(state)
        assert _snapshot(state) == snapshot

    def test_advance_fix_ladder_returns_new_object(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            fix_ladder_position=None,
        )
        result = advance_fix_ladder(state)
        assert result is not state

    def test_advance_fix_ladder_full_progression(self):
        """Walk through the full ladder progression."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            fix_ladder_position=None,
        )
        expected_positions = [
            "fresh_impl",
            "diagnostic",
            "diagnostic_impl",
            "exhausted",
        ]
        for expected_pos in expected_positions:
            result = advance_fix_ladder(state)
            assert result.fix_ladder_position == expected_pos
            state = result


# ===================================================================
# increment_red_run_retries
# ===================================================================


class TestIncrementRedRunRetries:
    def test_increment_red_run_retries_from_zero(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 1

    def test_increment_red_run_retries_from_nonzero(self):
        state = _make_state(red_run_retries=2)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 3

    def test_increment_red_run_retries_other_fields_unchanged(self):
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=1)
        result = increment_red_run_retries(state)
        assert result.stage == "3"
        assert result.sub_stage == "red_run"

    def test_increment_red_run_retries_does_not_mutate_input(self):
        state = _make_state(red_run_retries=0)
        snapshot = _snapshot(state)
        increment_red_run_retries(state)
        assert _snapshot(state) == snapshot

    def test_increment_red_run_retries_returns_new_object(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert result is not state


# ===================================================================
# reset_red_run_retries
# ===================================================================


class TestResetRedRunRetries:
    def test_reset_red_run_retries_sets_to_zero(self):
        state = _make_state(red_run_retries=5)
        result = reset_red_run_retries(state)
        assert result.red_run_retries == 0

    def test_reset_red_run_retries_already_zero(self):
        state = _make_state(red_run_retries=0)
        result = reset_red_run_retries(state)
        assert result.red_run_retries == 0

    def test_reset_red_run_retries_does_not_mutate_input(self):
        state = _make_state(red_run_retries=3)
        snapshot = _snapshot(state)
        reset_red_run_retries(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# increment_alignment_iteration
# ===================================================================


class TestIncrementAlignmentIteration:
    def test_increment_alignment_iteration_from_zero(self):
        state = _make_state(alignment_iterations=0)
        result = increment_alignment_iteration(state)
        assert result.alignment_iterations == 1

    def test_increment_alignment_iteration_from_nonzero(self):
        state = _make_state(alignment_iterations=4)
        result = increment_alignment_iteration(state)
        assert result.alignment_iterations == 5

    def test_increment_alignment_iteration_does_not_mutate_input(self):
        state = _make_state(alignment_iterations=0)
        snapshot = _snapshot(state)
        increment_alignment_iteration(state)
        assert _snapshot(state) == snapshot

    def test_increment_alignment_iteration_returns_new_object(self):
        state = _make_state(alignment_iterations=0)
        result = increment_alignment_iteration(state)
        assert result is not state


# ===================================================================
# rollback_to_unit
# ===================================================================


class TestRollbackToUnit:
    def test_rollback_sets_current_unit(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=5,
            total_units=10,
            verified_units=[{"unit": i} for i in range(1, 5)],
        )
        result = rollback_to_unit(state, 3)
        assert result.current_unit == 3

    def test_rollback_sets_sub_stage_to_stub_generation(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=5,
            total_units=10,
            verified_units=[{"unit": i} for i in range(1, 5)],
        )
        result = rollback_to_unit(state, 3)
        assert result.sub_stage == "stub_generation"

    def test_rollback_removes_verified_units_gte_target(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=5,
            total_units=10,
            verified_units=[
                {"unit": 1},
                {"unit": 2},
                {"unit": 3},
                {"unit": 4},
            ],
        )
        result = rollback_to_unit(state, 3)
        # Units 3 and 4 should be removed; only 1 and 2 remain
        for vu in result.verified_units:
            assert vu["unit"] < 3

    def test_rollback_resets_fix_ladder_position(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=3,
            total_units=5,
            fix_ladder_position="diagnostic",
        )
        result = rollback_to_unit(state, 2)
        assert result.fix_ladder_position is None

    def test_rollback_resets_red_run_retries(self):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=3,
            total_units=5,
            red_run_retries=2,
        )
        result = rollback_to_unit(state, 2)
        assert result.red_run_retries == 0

    def test_rollback_sets_stage_to_3(self):
        state = _make_state(stage="4", sub_stage=None, current_unit=None, total_units=5)
        result = rollback_to_unit(state, 1)
        assert result.stage == "3"

    def test_rollback_precondition_unit_less_than_1_raises(self):
        state = _make_state(stage="3", sub_stage="stub_generation", total_units=5)
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 0)

    def test_rollback_precondition_unit_greater_than_total_raises(self):
        state = _make_state(stage="3", sub_stage="stub_generation", total_units=5)
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 6)

    def test_rollback_does_not_mutate_input(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=3,
            total_units=5,
            verified_units=[{"unit": 1}, {"unit": 2}],
        )
        snapshot = _snapshot(state)
        rollback_to_unit(state, 1)
        assert _snapshot(state) == snapshot


# ===================================================================
# restart_from_stage
# ===================================================================


class TestRestartFromStage:
    def test_restart_sets_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=2)
        result = restart_from_stage(state, "1")
        assert result.stage == "1"

    def test_restart_sets_sub_stage_to_first_for_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=2)
        result = restart_from_stage(state, "0")
        # First sub-stage for stage 0 is one of {"hook_activation", "project_context", "project_profile"}
        assert result.sub_stage in VALID_SUB_STAGES["0"]

    def test_restart_resets_current_unit_to_none(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=2)
        result = restart_from_stage(state, "1")
        assert result.current_unit is None

    def test_restart_resets_fix_ladder_position(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            fix_ladder_position="fresh_impl",
        )
        result = restart_from_stage(state, "1")
        assert result.fix_ladder_position is None

    def test_restart_resets_red_run_retries(self):
        state = _make_state(
            stage="3", sub_stage="red_run", current_unit=1, red_run_retries=3
        )
        result = restart_from_stage(state, "1")
        assert result.red_run_retries == 0

    def test_restart_to_stage_2_resets_alignment_iterations(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            alignment_iterations=5,
        )
        result = restart_from_stage(state, "2")
        assert result.alignment_iterations == 0

    def test_restart_to_non_stage_2_preserves_alignment_iterations(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            alignment_iterations=5,
        )
        result = restart_from_stage(state, "1")
        assert result.alignment_iterations == 5

    def test_restart_invalid_stage_raises_transition_error(self):
        state = _make_state(stage="0")
        with pytest.raises(TransitionError):
            restart_from_stage(state, "invalid_stage")

    def test_restart_does_not_mutate_input(self):
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        snapshot = _snapshot(state)
        restart_from_stage(state, "0")
        assert _snapshot(state) == snapshot


# ===================================================================
# version_document
# ===================================================================


class TestVersionDocument:
    def test_version_document_updates_pass_history(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("content")
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        assert len(result.pass_history) == 1

    def test_version_document_pass_history_record_has_required_keys(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("content")
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        record = result.pass_history[0]
        assert "version" in record
        assert "document" in record
        assert "companions" in record
        assert "timestamp" in record

    def test_version_document_with_companions(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("main doc")
        companion = tmp_path / "companion.md"
        companion.write_text("companion content")
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        state = _make_state(pass_history=[])
        result = version_document(state, str(doc), companion_paths=[str(companion)])
        record = result.pass_history[0]
        assert len(record["companions"]) == 1

    def test_version_document_does_not_mutate_input(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("content")
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        state = _make_state(pass_history=[])
        snapshot = _snapshot(state)
        version_document(state, str(doc))
        assert _snapshot(state) == snapshot

    def test_version_document_returns_new_object(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("content")
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        assert result is not state

    def test_version_document_sequential_versions_increment(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("content")
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        state = _make_state(pass_history=[])
        result1 = version_document(state, str(doc))
        result2 = version_document(result1, str(doc))
        v1 = result1.pass_history[0]["version"]
        v2 = result2.pass_history[1]["version"]
        assert v2 > v1


# ===================================================================
# enter_debug_session
# ===================================================================


class TestEnterDebugSession:
    def test_enter_debug_session_sets_debug_session(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=42)
        assert result.debug_session is not None

    def test_enter_debug_session_sets_bug_number(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=42)
        assert result.debug_session["bug_number"] == 42

    def test_enter_debug_session_sets_authorized_false(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["authorized"] is False

    def test_enter_debug_session_sets_classification_none(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["classification"] is None

    def test_enter_debug_session_sets_empty_affected_units(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["affected_units"] == []

    def test_enter_debug_session_sets_phase_triage(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["phase"] == "triage"

    def test_enter_debug_session_sets_repair_retry_count_zero(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["repair_retry_count"] == 0

    def test_enter_debug_session_sets_triage_refinement_count_zero(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["triage_refinement_count"] == 0

    def test_enter_debug_session_sets_ledger_path_none(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, bug_number=1)
        assert result.debug_session["ledger_path"] is None

    def test_enter_debug_session_precondition_existing_session_raises(self):
        state = _make_state(
            debug_session={
                "authorized": False,
                "bug_number": 10,
                "classification": None,
                "affected_units": [],
                "phase": "triage",
                "repair_retry_count": 0,
                "triage_refinement_count": 0,
                "ledger_path": None,
            }
        )
        with pytest.raises(TransitionError):
            enter_debug_session(state, bug_number=42)

    def test_enter_debug_session_does_not_mutate_input(self):
        state = _make_state(debug_session=None)
        snapshot = _snapshot(state)
        enter_debug_session(state, bug_number=1)
        assert _snapshot(state) == snapshot


# ===================================================================
# authorize_debug_session
# ===================================================================


class TestAuthorizeDebugSession:
    def test_authorize_debug_session_sets_authorized_true(self):
        state = _make_state(
            debug_session={
                "authorized": False,
                "bug_number": 1,
                "classification": None,
                "affected_units": [],
                "phase": "triage",
                "repair_retry_count": 0,
                "triage_refinement_count": 0,
                "ledger_path": None,
            }
        )
        result = authorize_debug_session(state)
        assert result.debug_session["authorized"] is True

    def test_authorize_precondition_no_session_raises(self):
        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            authorize_debug_session(state)

    def test_authorize_precondition_already_authorized_raises(self):
        state = _make_state(
            debug_session={
                "authorized": True,
                "bug_number": 1,
                "classification": None,
                "affected_units": [],
                "phase": "triage",
                "repair_retry_count": 0,
                "triage_refinement_count": 0,
                "ledger_path": None,
            }
        )
        with pytest.raises(TransitionError):
            authorize_debug_session(state)

    def test_authorize_does_not_mutate_input(self):
        state = _make_state(
            debug_session={
                "authorized": False,
                "bug_number": 1,
                "classification": None,
                "affected_units": [],
                "phase": "triage",
                "repair_retry_count": 0,
                "triage_refinement_count": 0,
                "ledger_path": None,
            }
        )
        snapshot = _snapshot(state)
        authorize_debug_session(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# complete_debug_session
# ===================================================================


class TestCompleteDebugSession:
    def test_complete_debug_session_appends_to_history(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": "single_unit",
            "affected_units": [3],
            "phase": "commit",
            "repair_retry_count": 1,
            "triage_refinement_count": 0,
            "ledger_path": "/some/path",
        }
        state = _make_state(debug_session=session, debug_history=[])
        result = complete_debug_session(state)
        assert len(result.debug_history) == 1

    def test_complete_debug_session_clears_session(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": "single_unit",
            "affected_units": [3],
            "phase": "commit",
            "repair_retry_count": 1,
            "triage_refinement_count": 0,
            "ledger_path": "/some/path",
        }
        state = _make_state(debug_session=session)
        result = complete_debug_session(state)
        assert result.debug_session is None

    def test_complete_debug_session_precondition_no_session_raises(self):
        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            complete_debug_session(state)

    def test_complete_debug_session_precondition_not_authorized_raises(self):
        session = {
            "authorized": False,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        with pytest.raises(TransitionError):
            complete_debug_session(state)

    def test_complete_debug_session_does_not_mutate_input(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": "single_unit",
            "affected_units": [3],
            "phase": "commit",
            "repair_retry_count": 1,
            "triage_refinement_count": 0,
            "ledger_path": "/some/path",
        }
        state = _make_state(debug_session=session, debug_history=[])
        snapshot = _snapshot(state)
        complete_debug_session(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# abandon_debug_session
# ===================================================================


class TestAbandonDebugSession:
    def test_abandon_debug_session_appends_to_history_with_abandoned_marker(self):
        session = {
            "authorized": False,
            "bug_number": 5,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        assert len(result.debug_history) == 1
        assert result.debug_history[0].get("abandoned") is True

    def test_abandon_debug_session_clears_session(self):
        session = {
            "authorized": False,
            "bug_number": 5,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        result = abandon_debug_session(state)
        assert result.debug_session is None

    def test_abandon_debug_session_precondition_no_session_raises(self):
        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            abandon_debug_session(state)

    def test_abandon_debug_session_does_not_mutate_input(self):
        session = {
            "authorized": False,
            "bug_number": 5,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session, debug_history=[])
        snapshot = _snapshot(state)
        abandon_debug_session(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# update_debug_phase
# ===================================================================


class TestUpdateDebugPhase:
    def test_update_debug_phase_sets_phase(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        result = update_debug_phase(state, "repair")
        assert result.debug_session["phase"] == "repair"

    def test_update_debug_phase_all_valid_phases(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        for phase in VALID_DEBUG_PHASES:
            state = _make_state(debug_session=dict(session))
            result = update_debug_phase(state, phase)
            assert result.debug_session["phase"] == phase

    def test_update_debug_phase_invalid_raises_transition_error(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        with pytest.raises(TransitionError):
            update_debug_phase(state, "invalid_phase")

    def test_update_debug_phase_does_not_mutate_input(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        snapshot = _snapshot(state)
        update_debug_phase(state, "repair")
        assert _snapshot(state) == snapshot


# ===================================================================
# set_debug_classification
# ===================================================================


class TestSetDebugClassification:
    def test_set_debug_classification_sets_classification(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        result = set_debug_classification(state, "single_unit", [3])
        assert result.debug_session["classification"] == "single_unit"

    def test_set_debug_classification_sets_affected_units(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        result = set_debug_classification(state, "cross_unit", [1, 2, 5])
        assert result.debug_session["affected_units"] == [1, 2, 5]

    def test_set_debug_classification_all_valid_classifications(self):
        valid_classifications = {"build_env", "single_unit", "cross_unit"}
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        for cls in valid_classifications:
            state = _make_state(debug_session=dict(session))
            result = set_debug_classification(state, cls, [1])
            assert result.debug_session["classification"] == cls

    def test_set_debug_classification_invalid_raises_transition_error(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        with pytest.raises(TransitionError):
            set_debug_classification(state, "invalid_class", [1])

    def test_set_debug_classification_does_not_mutate_input(self):
        session = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(debug_session=session)
        snapshot = _snapshot(state)
        set_debug_classification(state, "build_env", [])
        assert _snapshot(state) == snapshot


# ===================================================================
# enter_redo_profile_revision
# ===================================================================


class TestEnterRedoProfileRevision:
    def test_enter_redo_delivery_sets_sub_stage(self):
        state = _make_state(stage="5", sub_stage="repo_complete")
        result = enter_redo_profile_revision(state, "delivery")
        assert result.sub_stage == "redo_profile_delivery"

    def test_enter_redo_blueprint_sets_sub_stage(self):
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = enter_redo_profile_revision(state, "blueprint")
        assert result.sub_stage == "redo_profile_blueprint"

    def test_enter_redo_snapshots_current_state(self):
        state = _make_state(stage="5", sub_stage="repo_complete")
        result = enter_redo_profile_revision(state, "delivery")
        assert result.redo_triggered_from is not None

    def test_enter_redo_invalid_type_raises_transition_error(self):
        state = _make_state(stage="5", sub_stage="repo_complete")
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(state, "invalid_type")

    def test_enter_redo_does_not_mutate_input(self):
        state = _make_state(stage="5", sub_stage="repo_complete")
        snapshot = _snapshot(state)
        enter_redo_profile_revision(state, "delivery")
        assert _snapshot(state) == snapshot


# ===================================================================
# complete_redo_profile_revision
# ===================================================================


class TestCompleteRedoProfileRevision:
    def test_complete_redo_clears_redo_triggered_from(self):
        redo_from = {"stage": "5", "sub_stage": "repo_complete"}
        state = _make_state(redo_triggered_from=redo_from)
        result = complete_redo_profile_revision(state)
        assert result.redo_triggered_from is None

    def test_complete_redo_precondition_no_redo_raises(self):
        state = _make_state(redo_triggered_from=None)
        with pytest.raises(TransitionError):
            complete_redo_profile_revision(state)

    def test_complete_redo_does_not_mutate_input(self):
        redo_from = {"stage": "5", "sub_stage": "repo_complete"}
        state = _make_state(redo_triggered_from=redo_from)
        snapshot = _snapshot(state)
        complete_redo_profile_revision(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# enter_alignment_check
# ===================================================================


class TestEnterAlignmentCheck:
    def test_enter_alignment_check_sets_sub_stage(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = enter_alignment_check(state)
        assert result.sub_stage == "alignment_check"

    def test_enter_alignment_check_does_not_mutate_input(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        snapshot = _snapshot(state)
        enter_alignment_check(state)
        assert _snapshot(state) == snapshot

    def test_enter_alignment_check_returns_new_object(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = enter_alignment_check(state)
        assert result is not state


# ===================================================================
# complete_alignment_check
# ===================================================================


class TestCompleteAlignmentCheck:
    def test_complete_alignment_check_confirmed_sets_alignment_confirmed(self):
        state = _make_state(stage="2", sub_stage="alignment_check")
        result = complete_alignment_check(state, "confirmed")
        assert result.sub_stage == "alignment_confirmed"

    def test_complete_alignment_check_blueprint_sets_blueprint_dialog(self):
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=0
        )
        result = complete_alignment_check(state, "blueprint")
        assert result.sub_stage == "blueprint_dialog"

    def test_complete_alignment_check_blueprint_increments_alignment_iterations(self):
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=2
        )
        result = complete_alignment_check(state, "blueprint")
        assert result.alignment_iterations == 3

    def test_complete_alignment_check_spec_sets_targeted_spec_revision(self):
        state = _make_state(stage="2", sub_stage="alignment_check")
        result = complete_alignment_check(state, "spec")
        assert result.sub_stage == "targeted_spec_revision"

    def test_complete_alignment_check_invalid_result_raises(self):
        state = _make_state(stage="2", sub_stage="alignment_check")
        with pytest.raises(TransitionError):
            complete_alignment_check(state, "invalid_result")

    def test_complete_alignment_check_does_not_mutate_input(self):
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=0
        )
        snapshot = _snapshot(state)
        complete_alignment_check(state, "confirmed")
        assert _snapshot(state) == snapshot


# ===================================================================
# enter_quality_gate
# ===================================================================


class TestEnterQualityGate:
    def test_enter_quality_gate_a_sets_sub_stage(self):
        state = _make_state(stage="3", sub_stage="test_generation", current_unit=1)
        result = enter_quality_gate(state, "quality_gate_a")
        assert result.sub_stage == "quality_gate_a"

    def test_enter_quality_gate_b_sets_sub_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=1)
        result = enter_quality_gate(state, "quality_gate_b")
        assert result.sub_stage == "quality_gate_b"

    def test_enter_quality_gate_does_not_mutate_input(self):
        state = _make_state(stage="3", sub_stage="test_generation", current_unit=1)
        snapshot = _snapshot(state)
        enter_quality_gate(state, "quality_gate_a")
        assert _snapshot(state) == snapshot


# ===================================================================
# advance_quality_gate_to_retry
# ===================================================================


class TestAdvanceQualityGateToRetry:
    def test_advance_gate_a_to_retry(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a", current_unit=1)
        result = advance_quality_gate_to_retry(state)
        assert result.sub_stage == "quality_gate_a_retry"

    def test_advance_gate_b_to_retry(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b", current_unit=1)
        result = advance_quality_gate_to_retry(state)
        assert result.sub_stage == "quality_gate_b_retry"

    def test_advance_quality_gate_to_retry_does_not_mutate_input(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a", current_unit=1)
        snapshot = _snapshot(state)
        advance_quality_gate_to_retry(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# quality_gate_pass
# ===================================================================


class TestQualityGatePass:
    def test_quality_gate_a_pass_advances_to_red_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a", current_unit=1)
        result = quality_gate_pass(state)
        assert result.sub_stage == "red_run"

    def test_quality_gate_a_retry_pass_advances_to_red_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a_retry", current_unit=1)
        result = quality_gate_pass(state)
        assert result.sub_stage == "red_run"

    def test_quality_gate_b_pass_advances_to_green_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b", current_unit=1)
        result = quality_gate_pass(state)
        assert result.sub_stage == "green_run"

    def test_quality_gate_b_retry_pass_advances_to_green_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b_retry", current_unit=1)
        result = quality_gate_pass(state)
        assert result.sub_stage == "green_run"

    def test_quality_gate_pass_does_not_mutate_input(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a", current_unit=1)
        snapshot = _snapshot(state)
        quality_gate_pass(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# quality_gate_fail_to_ladder
# ===================================================================


class TestQualityGateFailToLadder:
    def test_quality_gate_fail_enters_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
            fix_ladder_position=None,
        )
        result = quality_gate_fail_to_ladder(state)
        # Should trigger fix ladder entry from current position
        assert result is not state

    def test_quality_gate_fail_does_not_mutate_input(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
            fix_ladder_position=None,
        )
        snapshot = _snapshot(state)
        quality_gate_fail_to_ladder(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# set_delivered_repo_path
# ===================================================================


class TestSetDeliveredRepoPath:
    def test_set_delivered_repo_path_sets_path(self):
        state = _make_state(delivered_repo_path=None)
        result = set_delivered_repo_path(state, "/home/user/project")
        assert result.delivered_repo_path == "/home/user/project"

    def test_set_delivered_repo_path_overwrites_existing(self):
        state = _make_state(delivered_repo_path="/old/path")
        result = set_delivered_repo_path(state, "/new/path")
        assert result.delivered_repo_path == "/new/path"

    def test_set_delivered_repo_path_does_not_mutate_input(self):
        state = _make_state(delivered_repo_path=None)
        snapshot = _snapshot(state)
        set_delivered_repo_path(state, "/some/path")
        assert _snapshot(state) == snapshot

    def test_set_delivered_repo_path_returns_new_object(self):
        state = _make_state(delivered_repo_path=None)
        result = set_delivered_repo_path(state, "/some/path")
        assert result is not state


# ===================================================================
# enter_pass_1
# ===================================================================


class TestEnterPass1:
    def test_enter_pass_1_sets_pass_to_1(self):
        state = _make_state(pass_=None)
        result = enter_pass_1(state)
        assert result.pass_ == 1

    def test_enter_pass_1_does_not_mutate_input(self):
        state = _make_state(pass_=None)
        snapshot = _snapshot(state)
        enter_pass_1(state)
        assert _snapshot(state) == snapshot

    def test_enter_pass_1_returns_new_object(self):
        state = _make_state(pass_=None)
        result = enter_pass_1(state)
        assert result is not state


# ===================================================================
# enter_pass_2
# ===================================================================


class TestEnterPass2:
    def test_enter_pass_2_sets_pass_to_2(self):
        state = _make_state(pass_=1)
        result = enter_pass_2(state, "/nested/session/path")
        assert result.pass_ == 2

    def test_enter_pass_2_sets_nested_session_path(self):
        state = _make_state(pass_=1)
        result = enter_pass_2(state, "/nested/session/path")
        assert result.pass2_nested_session_path == "/nested/session/path"

    def test_enter_pass_2_precondition_pass_not_1_raises(self):
        state = _make_state(pass_=None)
        with pytest.raises(TransitionError):
            enter_pass_2(state, "/nested/session/path")

    def test_enter_pass_2_precondition_pass_2_raises(self):
        state = _make_state(pass_=2)
        with pytest.raises(TransitionError):
            enter_pass_2(state, "/nested/session/path")

    def test_enter_pass_2_does_not_mutate_input(self):
        state = _make_state(pass_=1)
        snapshot = _snapshot(state)
        enter_pass_2(state, "/nested/session/path")
        assert _snapshot(state) == snapshot


# ===================================================================
# clear_pass
# ===================================================================


class TestClearPass:
    def test_clear_pass_sets_pass_to_none(self):
        state = _make_state(pass_=2, pass2_nested_session_path="/some/path")
        result = clear_pass(state)
        assert result.pass_ is None

    def test_clear_pass_clears_nested_session_path(self):
        state = _make_state(pass_=2, pass2_nested_session_path="/some/path")
        result = clear_pass(state)
        assert result.pass2_nested_session_path is None

    def test_clear_pass_from_pass_1(self):
        state = _make_state(pass_=1, pass2_nested_session_path=None)
        result = clear_pass(state)
        assert result.pass_ is None
        assert result.pass2_nested_session_path is None

    def test_clear_pass_does_not_mutate_input(self):
        state = _make_state(pass_=2, pass2_nested_session_path="/some/path")
        snapshot = _snapshot(state)
        clear_pass(state)
        assert _snapshot(state) == snapshot

    def test_clear_pass_returns_new_object(self):
        state = _make_state(pass_=1)
        result = clear_pass(state)
        assert result is not state


# ===================================================================
# mark_unit_deferred_broken
# ===================================================================


class TestMarkUnitDeferredBroken:
    def test_mark_unit_deferred_broken_appends_unit(self):
        state = _make_state(deferred_broken_units=[])
        result = mark_unit_deferred_broken(state, 5)
        assert 5 in result.deferred_broken_units

    def test_mark_unit_deferred_broken_no_duplicates(self):
        state = _make_state(deferred_broken_units=[5])
        result = mark_unit_deferred_broken(state, 5)
        assert result.deferred_broken_units.count(5) == 1

    def test_mark_unit_deferred_broken_multiple_units(self):
        state = _make_state(deferred_broken_units=[])
        result = mark_unit_deferred_broken(state, 3)
        result = mark_unit_deferred_broken(result, 7)
        assert 3 in result.deferred_broken_units
        assert 7 in result.deferred_broken_units

    def test_mark_unit_deferred_broken_does_not_mutate_input(self):
        state = _make_state(deferred_broken_units=[])
        snapshot = _snapshot(state)
        mark_unit_deferred_broken(state, 5)
        assert _snapshot(state) == snapshot

    def test_mark_unit_deferred_broken_returns_new_object(self):
        state = _make_state(deferred_broken_units=[])
        result = mark_unit_deferred_broken(state, 5)
        assert result is not state


# ===================================================================
# resolve_deferred_broken
# ===================================================================


class TestResolveDeferredBroken:
    def test_resolve_deferred_broken_removes_unit(self):
        state = _make_state(deferred_broken_units=[3, 5, 7])
        result = resolve_deferred_broken(state, 5)
        assert 5 not in result.deferred_broken_units

    def test_resolve_deferred_broken_preserves_other_units(self):
        state = _make_state(deferred_broken_units=[3, 5, 7])
        result = resolve_deferred_broken(state, 5)
        assert 3 in result.deferred_broken_units
        assert 7 in result.deferred_broken_units

    def test_resolve_deferred_broken_precondition_not_present_raises(self):
        state = _make_state(deferred_broken_units=[3, 7])
        with pytest.raises(TransitionError):
            resolve_deferred_broken(state, 5)

    def test_resolve_deferred_broken_empty_list_raises(self):
        state = _make_state(deferred_broken_units=[])
        with pytest.raises(TransitionError):
            resolve_deferred_broken(state, 1)

    def test_resolve_deferred_broken_does_not_mutate_input(self):
        state = _make_state(deferred_broken_units=[3, 5])
        snapshot = _snapshot(state)
        resolve_deferred_broken(state, 5)
        assert _snapshot(state) == snapshot

    def test_resolve_deferred_broken_returns_new_object(self):
        state = _make_state(deferred_broken_units=[5])
        result = resolve_deferred_broken(state, 5)
        assert result is not state


# ===================================================================
# Cross-cutting immutability: spot-check on functions not yet covered
# ===================================================================


class TestImmutabilityInvariant:
    """All transition functions must return a new PipelineState via deep copy.
    The original input must never be mutated. These tests sample functions
    that were not individually tested for immutability above."""

    def test_increment_alignment_iteration_immutability(self):
        state = _make_state(alignment_iterations=2)
        snapshot = _snapshot(state)
        increment_alignment_iteration(state)
        assert _snapshot(state) == snapshot

    def test_reset_red_run_retries_immutability(self):
        state = _make_state(red_run_retries=5)
        snapshot = _snapshot(state)
        reset_red_run_retries(state)
        assert _snapshot(state) == snapshot

    def test_enter_quality_gate_immutability(self):
        state = _make_state(stage="3", sub_stage="test_generation", current_unit=1)
        snapshot = _snapshot(state)
        enter_quality_gate(state, "quality_gate_a")
        assert _snapshot(state) == snapshot

    def test_advance_quality_gate_to_retry_immutability(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b", current_unit=1)
        snapshot = _snapshot(state)
        advance_quality_gate_to_retry(state)
        assert _snapshot(state) == snapshot

    def test_quality_gate_pass_immutability(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b", current_unit=1)
        snapshot = _snapshot(state)
        quality_gate_pass(state)
        assert _snapshot(state) == snapshot

    def test_quality_gate_fail_to_ladder_immutability(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
            fix_ladder_position=None,
        )
        snapshot = _snapshot(state)
        quality_gate_fail_to_ladder(state)
        assert _snapshot(state) == snapshot

    def test_enter_alignment_check_immutability(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        snapshot = _snapshot(state)
        enter_alignment_check(state)
        assert _snapshot(state) == snapshot


# ===================================================================
# Deep copy verification: mutable nested structures
# ===================================================================


class TestDeepCopyBehavior:
    """Verify that returned states have independent mutable structures."""

    def test_advance_stage_verified_units_independent(self):
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
            verified_units=[{"unit": 1}],
        )
        result = advance_stage(state, "4")
        # Modifying result's verified_units should not affect original
        if result.verified_units:
            result.verified_units.append({"unit": 99})
        assert {"unit": 99} not in state.verified_units

    def test_enter_debug_session_debug_history_independent(self):
        state = _make_state(debug_session=None, debug_history=[{"old": True}])
        result = enter_debug_session(state, bug_number=1)
        result.debug_history.append({"new": True})
        assert len(state.debug_history) == 1

    def test_mark_unit_deferred_broken_list_independent(self):
        state = _make_state(deferred_broken_units=[1, 2])
        result = mark_unit_deferred_broken(state, 3)
        result.deferred_broken_units.append(99)
        assert 99 not in state.deferred_broken_units
