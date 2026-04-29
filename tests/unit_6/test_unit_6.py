"""Unit 6: State Transitions -- complete test suite.

Synthetic data assumptions:
- PipelineState is constructed via keyword arguments as defined in the Unit 5 stub.
- VALID_STAGES = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}.
- VALID_SUB_STAGES per the Unit 5 contract (stage-keyed sets).
- VALID_FIX_LADDER_POSITIONS = [None, "fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"].
- VALID_DEBUG_PHASES = {"triage", "repair", "regression_test", "lessons_learned", "reassembly", "stage3_reentry", "commit"}.
- Additional non-stage-bound sub-stages: "redo_profile_delivery", "redo_profile_blueprint",
  "pass_transition", "pass2_active", "targeted_spec_revision".
- A debug_session dict follows the schema: authorized (bool), bug_number (int|null),
  classification (str|null), affected_units (list[int]), phase (str),
  repair_retry_count (int), triage_refinement_count (int), ledger_path (str|null).
- Profile archetype E = "svp_language_extension", F = "svp_architectural".
- version_document copies files to a history/ directory; filesystem operations
  are validated via the tmp_path fixture.
- All transition functions return a deep copy; the original state is never mutated.
"""

import copy

import pytest

from pipeline_state import PipelineState
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


def _make_state(**overrides):
    """Build a minimal PipelineState with sane defaults for testing."""
    defaults = {
        "stage": "3",
        "sub_stage": "stub_generation",
        "current_unit": 1,
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
        "authorized": False,
        "bug_number": 1,
        "classification": None,
        "affected_units": [],
        "phase": "triage",
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    session.update(overrides)
    return session


# ===================================================================
# Immutability: every function must deep-copy, never mutate input
# ===================================================================


class TestImmutability:
    """All transition functions must return a new PipelineState without mutating the input."""

    def test_advance_stage_does_not_mutate_input(self):
        state = _make_state(stage="0", sub_stage="project_profile", current_unit=None)
        original = copy.deepcopy(state)
        advance_stage(state, "1")
        assert state.stage == original.stage
        assert state.sub_stage == original.sub_stage

    def test_advance_sub_stage_does_not_mutate_input(self):
        state = _make_state(stage="3", sub_stage="stub_generation")
        original_sub = state.sub_stage
        advance_sub_stage(state, "test_generation")
        assert state.sub_stage == original_sub

    def test_complete_unit_does_not_mutate_input(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=5,
            verified_units=[],
        )
        original_verified = list(state.verified_units)
        complete_unit(state)
        assert state.verified_units == original_verified

    def test_increment_red_run_retries_does_not_mutate_input(self):
        state = _make_state(red_run_retries=2)
        increment_red_run_retries(state)
        assert state.red_run_retries == 2

    def test_rollback_to_unit_does_not_mutate_input(self):
        state = _make_state(
            stage="3",
            current_unit=5,
            sub_stage="implementation",
            verified_units=[
                {"unit": 1},
                {"unit": 2},
                {"unit": 3},
                {"unit": 4},
            ],
        )
        original_verified_len = len(state.verified_units)
        rollback_to_unit(state, 3)
        assert len(state.verified_units) == original_verified_len

    def test_enter_debug_session_does_not_mutate_input(self):
        state = _make_state(debug_session=None)
        enter_debug_session(state, 42)
        assert state.debug_session is None


# ===================================================================
# advance_stage
# ===================================================================


class TestAdvanceStage:
    """advance_stage: sets stage, clears sub_stage/current_unit/fix_ladder, resets red_run_retries."""

    def test_advance_from_0_to_1(self):
        state = _make_state(stage="0", sub_stage="project_profile", current_unit=None)
        result = advance_stage(state, "1")
        assert result.stage == "1"
        assert result.sub_stage is None
        assert result.current_unit is None
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_advance_from_2_to_pre_stage_3(self):
        state = _make_state(
            stage="2", sub_stage="alignment_confirmed", current_unit=None
        )
        result = advance_stage(state, "pre_stage_3")
        assert result.stage == "pre_stage_3"
        assert result.sub_stage is None

    def test_advance_from_3_to_4(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=5,
            fix_ladder_position="fresh_impl",
            red_run_retries=3,
        )
        result = advance_stage(state, "4")
        assert result.stage == "4"
        assert result.sub_stage is None
        assert result.current_unit is None
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_advance_from_4_to_5(self):
        state = _make_state(
            stage="4", sub_stage="regression_adaptation", current_unit=None
        )
        result = advance_stage(state, "5")
        assert result.stage == "5"

    def test_advance_to_invalid_stage_raises_transition_error(self):
        state = _make_state(stage="0", sub_stage="hook_activation", current_unit=None)
        with pytest.raises(TransitionError):
            advance_stage(state, "99")

    def test_advance_to_empty_string_raises_transition_error(self):
        state = _make_state(stage="0", sub_stage="hook_activation", current_unit=None)
        with pytest.raises(TransitionError):
            advance_stage(state, "")

    def test_advance_preserves_unrelated_fields(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            alignment_iterations=3,
            primary_language="r",
        )
        result = advance_stage(state, "4")
        assert result.alignment_iterations == 3
        assert result.primary_language == "r"


# ===================================================================
# advance_sub_stage
# ===================================================================


class TestAdvanceSubStage:
    """advance_sub_stage: sets sub_stage, leaves other fields unchanged."""

    def test_advance_sub_stage_within_stage_3(self):
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = advance_sub_stage(state, "test_generation")
        assert result.sub_stage == "test_generation"
        assert result.stage == "3"

    def test_advance_sub_stage_to_implementation(self):
        state = _make_state(stage="3", sub_stage="test_generation")
        result = advance_sub_stage(state, "quality_gate_a")
        assert result.sub_stage == "quality_gate_a"

    def test_advance_sub_stage_stage_2(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog", current_unit=None)
        result = advance_sub_stage(state, "alignment_check")
        assert result.sub_stage == "alignment_check"

    def test_advance_sub_stage_preserves_current_unit(self):
        state = _make_state(stage="3", sub_stage="stub_generation", current_unit=7)
        result = advance_sub_stage(state, "test_generation")
        assert result.current_unit == 7

    def test_advance_sub_stage_additional_non_stage_bound(self):
        """Additional sub-stages like redo_profile_delivery are accepted."""
        state = _make_state(stage="3", sub_stage="implementation")
        result = advance_sub_stage(state, "redo_profile_delivery")
        assert result.sub_stage == "redo_profile_delivery"

    def test_advance_sub_stage_invalid_raises_transition_error(self):
        state = _make_state(stage="3", sub_stage="stub_generation")
        with pytest.raises(TransitionError):
            advance_sub_stage(state, "nonexistent_sub_stage")


# ===================================================================
# complete_unit
# ===================================================================


class TestCompleteUnit:
    """complete_unit: appends to verified_units, advances or finalizes."""

    def test_complete_unit_appends_verification_record(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=5,
            verified_units=[],
        )
        result = complete_unit(state)
        assert len(result.verified_units) == 1
        assert result.verified_units[0]["unit"] == 1 or "unit" in str(
            result.verified_units[0]
        )

    def test_complete_unit_increments_current_unit_when_more_remain(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=3,
            total_units=5,
            verified_units=[{"unit": 1}, {"unit": 2}],
        )
        result = complete_unit(state)
        assert result.current_unit == 4

    def test_complete_unit_resets_fix_ladder_and_retries(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=5,
            verified_units=[],
            fix_ladder_position="diagnostic",
            red_run_retries=2,
        )
        result = complete_unit(state)
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_complete_unit_sets_sub_stage_to_stub_generation_for_next_unit(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=5,
            verified_units=[],
        )
        result = complete_unit(state)
        assert result.sub_stage == "stub_generation"

    def test_complete_last_unit_sets_current_unit_none(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=5,
            total_units=5,
            verified_units=[{"unit": i} for i in range(1, 5)],
        )
        result = complete_unit(state)
        assert result.current_unit is None

    def test_complete_last_unit_sets_sub_stage_none(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=5,
            total_units=5,
            verified_units=[{"unit": i} for i in range(1, 5)],
        )
        result = complete_unit(state)
        assert result.sub_stage is None

    def test_complete_unit_precondition_current_unit_none_raises(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=None,
            total_units=5,
        )
        with pytest.raises(TransitionError):
            complete_unit(state)

    def test_complete_unit_precondition_wrong_sub_stage_raises(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            total_units=5,
        )
        with pytest.raises(TransitionError):
            complete_unit(state)


# ===================================================================
# advance_fix_ladder
# ===================================================================


class TestAdvanceFixLadder:
    """advance_fix_ladder: progression None -> fresh_impl -> diagnostic -> diagnostic_impl -> exhausted."""

    def test_none_to_fresh_impl(self):
        state = _make_state(fix_ladder_position=None, sub_stage="implementation")
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "fresh_impl"
        assert result.sub_stage == "implementation"

    def test_fresh_impl_to_diagnostic(self):
        state = _make_state(
            fix_ladder_position="fresh_impl", sub_stage="implementation"
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "diagnostic"
        # sub_stage is unchanged for "diagnostic" -- routing handles it

    def test_diagnostic_to_diagnostic_impl(self):
        state = _make_state(
            fix_ladder_position="diagnostic", sub_stage="implementation"
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "diagnostic_impl"
        assert result.sub_stage == "implementation"

    def test_diagnostic_impl_to_exhausted(self):
        state = _make_state(
            fix_ladder_position="diagnostic_impl", sub_stage="implementation"
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "exhausted"
        # sub_stage unchanged for "exhausted" -- routing presents gate_3_2

    def test_exhausted_raises_transition_error(self):
        """Cannot advance beyond exhausted."""
        state = _make_state(fix_ladder_position="exhausted", sub_stage="implementation")
        with pytest.raises(TransitionError):
            advance_fix_ladder(state)

    def test_invalid_position_raises_transition_error(self):
        state = _make_state(fix_ladder_position="bogus", sub_stage="implementation")
        with pytest.raises(TransitionError):
            advance_fix_ladder(state)

    def test_fresh_impl_sets_sub_stage_implementation(self):
        """When advancing to fresh_impl, sub_stage must become implementation."""
        state = _make_state(fix_ladder_position=None, sub_stage="quality_gate_a")
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "fresh_impl"
        assert result.sub_stage == "implementation"

    def test_diagnostic_impl_sets_sub_stage_implementation(self):
        """When advancing to diagnostic_impl, sub_stage must become implementation."""
        state = _make_state(
            fix_ladder_position="diagnostic", sub_stage="quality_gate_b"
        )
        result = advance_fix_ladder(state)
        assert result.fix_ladder_position == "diagnostic_impl"
        assert result.sub_stage == "implementation"


# ===================================================================
# increment_red_run_retries / reset_red_run_retries
# ===================================================================


class TestRedRunRetries:
    """increment_red_run_retries and reset_red_run_retries."""

    def test_increment_from_zero(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 1

    def test_increment_from_nonzero(self):
        state = _make_state(red_run_retries=3)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 4

    def test_increment_preserves_other_fields(self):
        state = _make_state(red_run_retries=1, stage="3", sub_stage="red_run")
        result = increment_red_run_retries(state)
        assert result.stage == "3"
        assert result.sub_stage == "red_run"

    def test_reset_from_nonzero(self):
        state = _make_state(red_run_retries=5)
        result = reset_red_run_retries(state)
        assert result.red_run_retries == 0

    def test_reset_from_zero_is_idempotent(self):
        state = _make_state(red_run_retries=0)
        result = reset_red_run_retries(state)
        assert result.red_run_retries == 0


# ===================================================================
# increment_alignment_iteration
# ===================================================================


class TestIncrementAlignmentIteration:
    """increment_alignment_iteration: increments alignment_iterations by 1."""

    def test_increment_from_zero(self):
        state = _make_state(alignment_iterations=0)
        result = increment_alignment_iteration(state)
        assert result.alignment_iterations == 1

    def test_increment_from_nonzero(self):
        state = _make_state(alignment_iterations=4)
        result = increment_alignment_iteration(state)
        assert result.alignment_iterations == 5

    def test_increment_preserves_other_fields(self):
        state = _make_state(
            alignment_iterations=2, stage="2", sub_stage="alignment_check"
        )
        result = increment_alignment_iteration(state)
        assert result.stage == "2"
        assert result.sub_stage == "alignment_check"


# ===================================================================
# rollback_to_unit
# ===================================================================


class TestRollbackToUnit:
    """rollback_to_unit: rewinds pipeline to specified unit number."""

    def test_rollback_sets_current_unit(self):
        state = _make_state(
            stage="3",
            current_unit=5,
            sub_stage="implementation",
            verified_units=[{"unit": i} for i in range(1, 5)],
        )
        result = rollback_to_unit(state, 3)
        assert result.current_unit == 3

    def test_rollback_sets_stage_to_3(self):
        state = _make_state(
            stage="4",
            current_unit=None,
            sub_stage=None,
            verified_units=[{"unit": i} for i in range(1, 11)],
            total_units=10,
        )
        result = rollback_to_unit(state, 5)
        assert result.stage == "3"

    def test_rollback_sets_sub_stage_to_stub_generation(self):
        state = _make_state(
            stage="3",
            current_unit=5,
            sub_stage="implementation",
            verified_units=[{"unit": i} for i in range(1, 5)],
        )
        result = rollback_to_unit(state, 3)
        assert result.sub_stage == "stub_generation"

    def test_rollback_removes_verified_units_at_or_above_target(self):
        verified = [{"unit": i} for i in range(1, 6)]
        state = _make_state(
            stage="3",
            current_unit=6,
            sub_stage="implementation",
            verified_units=verified,
        )
        result = rollback_to_unit(state, 3)
        for record in result.verified_units:
            assert record["unit"] < 3

    def test_rollback_preserves_verified_units_below_target(self):
        verified = [{"unit": i} for i in range(1, 6)]
        state = _make_state(
            stage="3",
            current_unit=6,
            sub_stage="implementation",
            verified_units=verified,
        )
        result = rollback_to_unit(state, 3)
        assert len(result.verified_units) == 2
        assert result.verified_units[0]["unit"] == 1
        assert result.verified_units[1]["unit"] == 2

    def test_rollback_resets_fix_ladder_and_retries(self):
        state = _make_state(
            stage="3",
            current_unit=5,
            sub_stage="implementation",
            verified_units=[{"unit": i} for i in range(1, 5)],
            fix_ladder_position="diagnostic",
            red_run_retries=3,
        )
        result = rollback_to_unit(state, 2)
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_rollback_to_unit_0_raises_transition_error(self):
        state = _make_state(stage="3", current_unit=3, sub_stage="implementation")
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 0)

    def test_rollback_beyond_total_units_raises_transition_error(self):
        state = _make_state(
            stage="3",
            current_unit=5,
            sub_stage="implementation",
            total_units=10,
        )
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 11)

    def test_rollback_to_unit_1_clears_all_verified(self):
        verified = [{"unit": i} for i in range(1, 4)]
        state = _make_state(
            stage="3",
            current_unit=4,
            sub_stage="implementation",
            verified_units=verified,
        )
        result = rollback_to_unit(state, 1)
        assert result.verified_units == []
        assert result.current_unit == 1


# ===================================================================
# restart_from_stage
# ===================================================================


class TestRestartFromStage:
    """restart_from_stage: resets to target stage with first sub-stage defaults."""

    def test_restart_to_stage_2_resets_alignment_iterations(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=5,
            alignment_iterations=4,
        )
        result = restart_from_stage(state, "2")
        assert result.stage == "2"
        assert result.alignment_iterations == 0

    def test_restart_to_stage_2_sets_first_sub_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        result = restart_from_stage(state, "2")
        # First sub-stage for stage 2 is "blueprint_dialog"
        assert result.sub_stage == "blueprint_dialog"

    def test_restart_clears_unit_and_ladder(self):
        state = _make_state(
            stage="3",
            current_unit=5,
            sub_stage="implementation",
            fix_ladder_position="diagnostic",
            red_run_retries=2,
        )
        result = restart_from_stage(state, "2")
        assert result.current_unit is None
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_restart_to_stage_0_sets_first_sub_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        result = restart_from_stage(state, "0")
        assert result.stage == "0"
        assert result.sub_stage == "hook_activation"

    def test_restart_to_stage_1(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        result = restart_from_stage(state, "1")
        assert result.stage == "1"

    def test_restart_invalid_stage_raises_transition_error(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        with pytest.raises(TransitionError):
            restart_from_stage(state, "invalid_stage")

    def test_restart_to_non_2_does_not_reset_alignment_iterations(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=5,
            alignment_iterations=3,
        )
        result = restart_from_stage(state, "1")
        # Only stage 2 restart resets alignment_iterations
        assert result.alignment_iterations == 3

    def test_restart_resets_assembly_retries(self):
        """Bug S3-153: assembly_retries (Stage 5 retry counter) must reset on
        restart for the same reason red_run_retries (Stage 3 retry counter)
        does — the work that produced the count is being thrown away. Without
        this, the gate_5_2 FIX BLUEPRINT and FIX SPEC handlers leave the
        counter at its limit, so the next assembly failure after the restart
        immediately re-emits gate_5_2 instead of giving the user the
        configured retry budget."""
        state = _make_state(
            stage="5",
            sub_stage="gate_5_2",
            current_unit=None,
            assembly_retries=3,
        )
        # Both restart targets used by gate_5_2 (stage 2 = FIX BLUEPRINT,
        # stage 1 = FIX SPEC) must clear the counter.
        for target in ("2", "1"):
            result = restart_from_stage(state, target)
            assert result.assembly_retries == 0, (
                f"restart_from_stage(state, {target!r}) failed to reset "
                f"assembly_retries; got {result.assembly_retries}"
            )


# ===================================================================
# version_document
# ===================================================================


class TestVersionDocument:
    """version_document: copies document + companions to history/, updates pass_history."""

    def test_version_document_creates_history_directory(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("spec content v1")
        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        history_dir = tmp_path / "history"
        assert history_dir.exists()

    def test_version_document_copies_file_with_version_suffix(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("spec content v1")
        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        versioned = tmp_path / "history" / "spec.md.v1"
        assert versioned.exists()
        assert versioned.read_text() == "spec content v1"

    def test_version_document_increments_version_number(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("spec v1")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        (history_dir / "spec.md.v1").write_text("old")
        state = _make_state(
            pass_history=[{"version": 1, "document": str(doc), "companions": []}],
        )
        result = version_document(state, str(doc))
        versioned = history_dir / "spec.md.v2"
        assert versioned.exists()

    def test_version_document_updates_pass_history(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("content")
        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        assert len(result.pass_history) == 1
        record = result.pass_history[0]
        assert record["version"] == 1
        assert record["document"] == str(doc)
        assert "timestamp" in record

    def test_version_document_with_companions(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("spec")
        companion = tmp_path / "appendix.md"
        companion.write_text("appendix")
        state = _make_state(pass_history=[])
        result = version_document(state, str(doc), companion_paths=[str(companion)])
        history_dir = tmp_path / "history"
        assert (history_dir / "spec.md.v1").exists()
        assert (history_dir / "appendix.md.v1").exists()
        assert result.pass_history[0]["companions"] == [str(companion)]

    def test_version_document_no_companions_default_empty_list(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("content")
        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        assert result.pass_history[0]["companions"] == []

    def test_version_document_timestamp_is_iso_8601(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("content")
        state = _make_state(pass_history=[])
        result = version_document(state, str(doc))
        ts = result.pass_history[0]["timestamp"]
        # ISO-8601 contains 'T' separator and ends with Z or +00:00
        assert "T" in ts


# ===================================================================
# enter_debug_session
# ===================================================================


class TestEnterDebugSession:
    """enter_debug_session: creates a fresh debug_session dict."""

    def test_creates_debug_session_with_correct_schema(self):
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, 42)
        ds = result.debug_session
        assert ds is not None
        assert ds["authorized"] is False
        assert ds["bug_number"] == 42
        assert ds["classification"] is None
        assert ds["affected_units"] == []
        assert ds["phase"] == "triage"
        assert ds["repair_retry_count"] == 0
        assert ds["triage_refinement_count"] == 0
        assert ds["ledger_path"] is None

    def test_raises_if_debug_session_already_active(self):
        existing_session = _make_debug_session()
        state = _make_state(debug_session=existing_session)
        with pytest.raises(TransitionError):
            enter_debug_session(state, 99)

    def test_preserves_debug_history(self):
        state = _make_state(debug_session=None, debug_history=[{"old": True}])
        result = enter_debug_session(state, 1)
        assert len(result.debug_history) == 1

    # Bug S3-186 (cycle G1 of Gate 6 break-glass inversion).

    def test_enter_debug_session_initializes_mode_to_None(self):
        """enter_debug_session initializes debug_session['mode'] to None
        regardless of bug_number. Mode is set later by gate_6_1
        mode classification dispatch."""
        # bug_number == 0 (human_authorize source).
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, 0)
        assert result.debug_session["mode"] is None
        # bug_number > 0 (bug_command source).
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, 5)
        assert result.debug_session["mode"] is None

    def test_enter_debug_session_sets_source_field(self):
        """enter_debug_session sets debug_session['source'] from
        bug_number provenance. bug_number > 0 -> 'bug_command';
        bug_number == 0 -> 'human_authorize'."""
        # bug_number > 0.
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, 5)
        assert result.debug_session["source"] == "bug_command"
        # bug_number == 0.
        state = _make_state(debug_session=None)
        result = enter_debug_session(state, 0)
        assert result.debug_session["source"] == "human_authorize"


# ===================================================================
# authorize_debug_session
# ===================================================================


class TestAuthorizeDebugSession:
    """authorize_debug_session: flips authorized to True."""

    def test_authorizes_session(self):
        state = _make_state(debug_session=_make_debug_session(authorized=False))
        result = authorize_debug_session(state)
        assert result.debug_session["authorized"] is True

    def test_raises_if_no_debug_session(self):
        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            authorize_debug_session(state)

    def test_raises_if_already_authorized(self):
        state = _make_state(debug_session=_make_debug_session(authorized=True))
        with pytest.raises(TransitionError):
            authorize_debug_session(state)


# ===================================================================
# complete_debug_session
# ===================================================================


class TestCompleteDebugSession:
    """complete_debug_session: moves debug_session to debug_history, clears session."""

    def test_appends_to_history_and_clears(self):
        session = _make_debug_session(authorized=True, bug_number=7)
        state = _make_state(debug_session=session, debug_history=[])
        result = complete_debug_session(state)
        assert result.debug_session is None
        assert len(result.debug_history) == 1
        assert result.debug_history[0]["bug_number"] == 7

    def test_raises_if_no_debug_session(self):
        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            complete_debug_session(state)

    def test_raises_if_not_authorized(self):
        state = _make_state(debug_session=_make_debug_session(authorized=False))
        with pytest.raises(TransitionError):
            complete_debug_session(state)

    def test_preserves_existing_history(self):
        old_entry = {"bug_number": 1, "authorized": True}
        session = _make_debug_session(authorized=True, bug_number=2)
        state = _make_state(debug_session=session, debug_history=[old_entry])
        result = complete_debug_session(state)
        assert len(result.debug_history) == 2


# ===================================================================
# abandon_debug_session
# ===================================================================


class TestAbandonDebugSession:
    """abandon_debug_session: moves to history with abandoned marker, clears session."""

    def test_abandons_and_clears_session(self):
        session = _make_debug_session(authorized=False, bug_number=5)
        state = _make_state(debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        assert result.debug_session is None
        assert len(result.debug_history) == 1

    def test_abandoned_marker_present(self):
        session = _make_debug_session()
        state = _make_state(debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        history_entry = result.debug_history[0]
        assert history_entry.get("abandoned") is True

    def test_raises_if_no_debug_session(self):
        state = _make_state(debug_session=None)
        with pytest.raises(TransitionError):
            abandon_debug_session(state)

    def test_can_abandon_authorized_session(self):
        session = _make_debug_session(authorized=True)
        state = _make_state(debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        assert result.debug_session is None


# ===================================================================
# update_debug_phase
# ===================================================================


class TestUpdateDebugPhase:
    """update_debug_phase: sets debug_session phase to a valid debug phase."""

    def test_updates_to_repair(self):
        session = _make_debug_session(phase="triage")
        state = _make_state(debug_session=session)
        result = update_debug_phase(state, "repair")
        assert result.debug_session["phase"] == "repair"

    def test_updates_to_regression_test(self):
        session = _make_debug_session(phase="repair")
        state = _make_state(debug_session=session)
        result = update_debug_phase(state, "regression_test")
        assert result.debug_session["phase"] == "regression_test"

    def test_updates_to_lessons_learned(self):
        session = _make_debug_session(phase="regression_test")
        state = _make_state(debug_session=session)
        result = update_debug_phase(state, "lessons_learned")
        assert result.debug_session["phase"] == "lessons_learned"

    def test_updates_to_commit(self):
        session = _make_debug_session(phase="lessons_learned")
        state = _make_state(debug_session=session)
        result = update_debug_phase(state, "commit")
        assert result.debug_session["phase"] == "commit"

    def test_invalid_phase_raises_transition_error(self):
        session = _make_debug_session()
        state = _make_state(debug_session=session)
        with pytest.raises(TransitionError):
            update_debug_phase(state, "invalid_phase")

    def test_all_valid_phases_accepted(self):
        valid_phases = {
            "triage",
            "repair",
            "regression_test",
            "lessons_learned",
            "reassembly",
            "stage3_reentry",
            "commit",
        }
        for phase in valid_phases:
            session = _make_debug_session()
            state = _make_state(debug_session=session)
            result = update_debug_phase(state, phase)
            assert result.debug_session["phase"] == phase


# ===================================================================
# set_debug_classification
# ===================================================================


class TestSetDebugClassification:
    """set_debug_classification: sets classification and affected_units."""

    def test_set_build_env(self):
        session = _make_debug_session()
        state = _make_state(debug_session=session)
        result = set_debug_classification(state, "build_env", [])
        assert result.debug_session["classification"] == "build_env"
        assert result.debug_session["affected_units"] == []

    def test_set_single_unit(self):
        session = _make_debug_session()
        state = _make_state(debug_session=session)
        result = set_debug_classification(state, "single_unit", [5])
        assert result.debug_session["classification"] == "single_unit"
        assert result.debug_session["affected_units"] == [5]

    def test_set_cross_unit(self):
        session = _make_debug_session()
        state = _make_state(debug_session=session)
        result = set_debug_classification(state, "cross_unit", [3, 7, 12])
        assert result.debug_session["classification"] == "cross_unit"
        assert result.debug_session["affected_units"] == [3, 7, 12]

    def test_invalid_classification_raises_transition_error(self):
        session = _make_debug_session()
        state = _make_state(debug_session=session)
        with pytest.raises(TransitionError):
            set_debug_classification(state, "invalid_class", [1])


# ===================================================================
# enter_redo_profile_revision / complete_redo_profile_revision
# ===================================================================


class TestRedoProfileRevision:
    """enter_redo_profile_revision and complete_redo_profile_revision."""

    def test_enter_redo_delivery_sets_sub_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        result = enter_redo_profile_revision(state, "delivery")
        assert result.sub_stage == "redo_profile_delivery"

    def test_enter_redo_blueprint_sets_sub_stage(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        result = enter_redo_profile_revision(state, "blueprint")
        assert result.sub_stage == "redo_profile_blueprint"

    def test_enter_redo_snapshots_current_state(self):
        state = _make_state(stage="3", sub_stage="implementation", current_unit=5)
        result = enter_redo_profile_revision(state, "delivery")
        assert result.redo_triggered_from is not None

    def test_enter_redo_invalid_type_raises_transition_error(self):
        state = _make_state()
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(state, "invalid_type")

    def test_complete_redo_restores_state(self):
        state = _make_state(
            stage="3",
            sub_stage="redo_profile_delivery",
            current_unit=5,
            redo_triggered_from={
                "stage": "3",
                "sub_stage": "implementation",
                "current_unit": 5,
            },
        )
        result = complete_redo_profile_revision(state)
        assert result.redo_triggered_from is None

    def test_complete_redo_raises_if_no_snapshot(self):
        state = _make_state(redo_triggered_from=None)
        with pytest.raises(TransitionError):
            complete_redo_profile_revision(state)


# ===================================================================
# enter_alignment_check / complete_alignment_check
# ===================================================================


class TestAlignmentCheck:
    """enter_alignment_check and complete_alignment_check."""

    def test_enter_alignment_check_sets_sub_stage(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog", current_unit=None)
        result = enter_alignment_check(state)
        assert result.sub_stage == "alignment_check"

    def test_complete_alignment_confirmed(self):
        state = _make_state(stage="2", sub_stage="alignment_check", current_unit=None)
        result = complete_alignment_check(state, "confirmed")
        assert result.sub_stage == "alignment_confirmed"

    def test_complete_alignment_blueprint_resets_to_dialog(self):
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            current_unit=None,
            alignment_iterations=1,
        )
        result = complete_alignment_check(state, "blueprint")
        assert result.sub_stage == "blueprint_dialog"
        assert result.alignment_iterations == 2

    def test_complete_alignment_spec_sets_targeted_revision(self):
        state = _make_state(stage="2", sub_stage="alignment_check", current_unit=None)
        result = complete_alignment_check(state, "spec")
        assert result.sub_stage == "targeted_spec_revision"

    def test_complete_alignment_invalid_result_raises_transition_error(self):
        state = _make_state(stage="2", sub_stage="alignment_check", current_unit=None)
        with pytest.raises(TransitionError):
            complete_alignment_check(state, "invalid_result")


# ===================================================================
# enter_quality_gate / advance_quality_gate_to_retry / quality_gate_pass / quality_gate_fail_to_ladder
# ===================================================================


class TestQualityGate:
    """Quality gate lifecycle: enter -> pass/retry/fail_to_ladder."""

    def test_enter_quality_gate_a(self):
        state = _make_state(stage="3", sub_stage="test_generation")
        result = enter_quality_gate(state, "quality_gate_a")
        assert result.sub_stage == "quality_gate_a"

    def test_enter_quality_gate_b(self):
        state = _make_state(stage="3", sub_stage="implementation")
        result = enter_quality_gate(state, "quality_gate_b")
        assert result.sub_stage == "quality_gate_b"

    def test_advance_gate_a_to_retry(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a")
        result = advance_quality_gate_to_retry(state)
        assert result.sub_stage == "quality_gate_a_retry"

    def test_advance_gate_b_to_retry(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b")
        result = advance_quality_gate_to_retry(state)
        assert result.sub_stage == "quality_gate_b_retry"

    def test_quality_gate_a_pass_advances_to_red_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a")
        result = quality_gate_pass(state)
        assert result.sub_stage == "red_run"

    def test_quality_gate_a_retry_pass_advances_to_red_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a_retry")
        result = quality_gate_pass(state)
        assert result.sub_stage == "red_run"

    def test_quality_gate_b_pass_advances_to_green_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b")
        result = quality_gate_pass(state)
        assert result.sub_stage == "green_run"

    def test_quality_gate_b_retry_pass_advances_to_green_run(self):
        state = _make_state(stage="3", sub_stage="quality_gate_b_retry")
        result = quality_gate_pass(state)
        assert result.sub_stage == "green_run"

    def test_quality_gate_fail_to_ladder_enters_fix_ladder(self):
        state = _make_state(stage="3", sub_stage="quality_gate_a")
        result = quality_gate_fail_to_ladder(state)
        # Enters fix ladder from current position
        assert (
            result.fix_ladder_position is not None
            or result.sub_stage != "quality_gate_a"
        )


# ===================================================================
# set_delivered_repo_path
# ===================================================================


class TestSetDeliveredRepoPath:
    """set_delivered_repo_path: sets delivered_repo_path on state."""

    def test_sets_path(self):
        state = _make_state(delivered_repo_path=None)
        result = set_delivered_repo_path(state, "/tmp/my_repo")
        assert result.delivered_repo_path == "/tmp/my_repo"

    def test_overwrites_existing_path(self):
        state = _make_state(delivered_repo_path="/old/path")
        result = set_delivered_repo_path(state, "/new/path")
        assert result.delivered_repo_path == "/new/path"

    def test_preserves_other_fields(self):
        state = _make_state(
            delivered_repo_path=None,
            stage="5",
            sub_stage="repo_test",
        )
        result = set_delivered_repo_path(state, "/tmp/repo")
        assert result.stage == "5"
        assert result.sub_stage == "repo_test"


# ===================================================================
# enter_pass_1 / enter_pass_2 / clear_pass
# ===================================================================


class TestPassLifecycle:
    """enter_pass_1 / enter_pass_2 / clear_pass lifecycle for E/F archetypes."""

    def test_enter_pass_1_sets_pass_to_1(self):
        """Assumes profile archetype is E or F -- test uses mock/patch if needed."""
        state = _make_state(pass_=None)
        # enter_pass_1 requires archetype E or F. If the implementation loads
        # profile internally, we mock it. If it checks state fields, we set them.
        # We attempt the call and verify the postcondition.
        result = enter_pass_1(state)
        assert result.pass_ == 1

    def test_enter_pass_2_sets_pass_to_2(self):
        state = _make_state(pass_=1)
        result = enter_pass_2(state, "/tmp/nested_session")
        assert result.pass_ == 2
        assert result.pass2_nested_session_path == "/tmp/nested_session"

    def test_enter_pass_2_precondition_not_in_pass_1_raises(self):
        state = _make_state(pass_=None)
        with pytest.raises(TransitionError):
            enter_pass_2(state, "/tmp/nested")

    def test_clear_pass_resets_pass_fields(self):
        state = _make_state(pass_=2, pass2_nested_session_path="/tmp/nested")
        result = clear_pass(state)
        assert result.pass_ is None
        assert result.pass2_nested_session_path is None

    def test_clear_pass_from_pass_1(self):
        state = _make_state(pass_=1, pass2_nested_session_path=None)
        result = clear_pass(state)
        assert result.pass_ is None


# ===================================================================
# mark_unit_deferred_broken / resolve_deferred_broken
# ===================================================================


class TestDeferredBroken:
    """mark_unit_deferred_broken and resolve_deferred_broken."""

    def test_mark_adds_unit_to_list(self):
        state = _make_state(deferred_broken_units=[])
        result = mark_unit_deferred_broken(state, 7)
        assert 7 in result.deferred_broken_units

    def test_mark_no_duplicates(self):
        state = _make_state(deferred_broken_units=[7])
        result = mark_unit_deferred_broken(state, 7)
        assert result.deferred_broken_units.count(7) == 1

    def test_mark_multiple_units(self):
        state = _make_state(deferred_broken_units=[])
        result = mark_unit_deferred_broken(state, 3)
        result = mark_unit_deferred_broken(result, 9)
        assert 3 in result.deferred_broken_units
        assert 9 in result.deferred_broken_units

    def test_resolve_removes_unit(self):
        state = _make_state(deferred_broken_units=[3, 7, 12])
        result = resolve_deferred_broken(state, 7)
        assert 7 not in result.deferred_broken_units
        assert 3 in result.deferred_broken_units
        assert 12 in result.deferred_broken_units

    def test_resolve_raises_if_unit_not_in_list(self):
        state = _make_state(deferred_broken_units=[3, 7])
        with pytest.raises(TransitionError):
            resolve_deferred_broken(state, 99)

    def test_resolve_on_empty_list_raises(self):
        state = _make_state(deferred_broken_units=[])
        with pytest.raises(TransitionError):
            resolve_deferred_broken(state, 1)


# ===================================================================
# Edge cases and cross-cutting concerns
# ===================================================================


class TestEdgeCases:
    """Cross-cutting edge case tests for transition functions."""

    def test_advance_fix_ladder_full_progression(self):
        """Walk through the entire fix ladder from None to exhausted."""
        state = _make_state(fix_ladder_position=None, sub_stage="quality_gate_a")
        positions = []
        for _ in range(4):
            state = advance_fix_ladder(state)
            positions.append(state.fix_ladder_position)
        assert positions == ["fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"]

    def test_complete_all_units_sequential(self):
        """Complete units 1 through 3 in sequence."""
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=3,
            verified_units=[],
        )
        result = complete_unit(state)
        assert result.current_unit == 2
        assert result.sub_stage == "stub_generation"

        result = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=2,
            total_units=3,
            verified_units=result.verified_units,
        )
        result = complete_unit(result)
        assert result.current_unit == 3

        result = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=3,
            total_units=3,
            verified_units=result.verified_units,
        )
        result = complete_unit(result)
        assert result.current_unit is None
        assert result.sub_stage is None
        assert len(result.verified_units) == 3

    def test_debug_session_full_lifecycle(self):
        """Enter -> authorize -> complete debug session lifecycle."""
        state = _make_state(debug_session=None, debug_history=[])
        state = enter_debug_session(state, 10)
        assert state.debug_session["authorized"] is False

        state = authorize_debug_session(state)
        assert state.debug_session["authorized"] is True

        state = update_debug_phase(state, "repair")
        assert state.debug_session["phase"] == "repair"

        state = set_debug_classification(state, "single_unit", [5])
        assert state.debug_session["classification"] == "single_unit"

        state = complete_debug_session(state)
        assert state.debug_session is None
        assert len(state.debug_history) == 1
        assert state.debug_history[0]["bug_number"] == 10

    def test_debug_session_abandon_lifecycle(self):
        """Enter -> abandon debug session lifecycle."""
        state = _make_state(debug_session=None, debug_history=[])
        state = enter_debug_session(state, 20)
        state = abandon_debug_session(state)
        assert state.debug_session is None
        assert len(state.debug_history) == 1
        assert state.debug_history[0].get("abandoned") is True

    def test_alignment_check_blueprint_loop(self):
        """Alignment check -> blueprint -> re-enter alignment check."""
        state = _make_state(
            stage="2",
            sub_stage="blueprint_dialog",
            current_unit=None,
            alignment_iterations=0,
        )
        state = enter_alignment_check(state)
        assert state.sub_stage == "alignment_check"

        state = complete_alignment_check(state, "blueprint")
        assert state.sub_stage == "blueprint_dialog"
        assert state.alignment_iterations == 1

        state = enter_alignment_check(state)
        assert state.sub_stage == "alignment_check"

        state = complete_alignment_check(state, "confirmed")
        assert state.sub_stage == "alignment_confirmed"

    def test_redo_profile_delivery_roundtrip(self):
        """Enter redo -> complete redo roundtrip preserves redo_triggered_from contract."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=5,
            redo_triggered_from=None,
        )
        state = enter_redo_profile_revision(state, "delivery")
        assert state.sub_stage == "redo_profile_delivery"
        assert state.redo_triggered_from is not None

        state = complete_redo_profile_revision(state)
        assert state.redo_triggered_from is None

    def test_rollback_after_multiple_completions(self):
        """Complete several units, then rollback partway."""
        verified = [{"unit": i} for i in range(1, 8)]
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=8,
            total_units=10,
            verified_units=verified,
            fix_ladder_position="diagnostic",
            red_run_retries=2,
        )
        result = rollback_to_unit(state, 5)
        assert result.current_unit == 5
        assert result.sub_stage == "stub_generation"
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0
        assert all(r["unit"] < 5 for r in result.verified_units)
        assert len(result.verified_units) == 4

    def test_pass_lifecycle_full(self):
        """enter_pass_1 -> enter_pass_2 -> clear_pass lifecycle."""
        state = _make_state(pass_=None, pass2_nested_session_path=None)
        state = enter_pass_1(state)
        assert state.pass_ == 1

        state = enter_pass_2(state, "/tmp/nested_path")
        assert state.pass_ == 2
        assert state.pass2_nested_session_path == "/tmp/nested_path"

        state = clear_pass(state)
        assert state.pass_ is None
        assert state.pass2_nested_session_path is None
