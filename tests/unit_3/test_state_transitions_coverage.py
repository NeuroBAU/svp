"""
Additional coverage tests for Unit 3: State Transition Engine.

These tests close gaps between the blueprint contracts
(Tier 2 and Tier 3) and the existing test suite. Each
test class is named after the gap it addresses.

Synthetic data generation assumptions:
- Same as test_state_transitions.py.
- All file I/O tests use pytest tmp_path.
- PipelineState instances use the same _make_state
  helper with identical defaults.
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------
# Helpers (duplicated from main test file for isolation)
# ---------------------------------------------------------------


def _make_state(**overrides):
    """Build a synthetic PipelineState with defaults."""
    from src.unit_2.stub import PipelineState

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
    from src.unit_2.stub import DebugSession

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
# complete_unit: marker file creation
# ---------------------------------------------------------------


class TestCompleteUnitMarker:
    """Blueprint contract: complete_unit writes marker."""

    def test_creates_marker_file(self, tmp_path):
        from src.unit_3.stub import complete_unit

        state = _make_state(
            current_unit=1,
            total_units=5,
        )
        complete_unit(state, 1, tmp_path)
        marker = (
            tmp_path
            / ".svp"
            / "markers"
            / "unit_1_verified"
        )
        assert marker.exists()

    def test_marker_contains_verified(self, tmp_path):
        from src.unit_3.stub import complete_unit

        state = _make_state(
            current_unit=1,
            total_units=5,
        )
        complete_unit(state, 1, tmp_path)
        marker = (
            tmp_path
            / ".svp"
            / "markers"
            / "unit_1_verified"
        )
        content = marker.read_text()
        assert "VERIFIED" in content

    def test_marker_already_exists_raises(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            complete_unit,
        )

        marker_dir = (
            tmp_path / ".svp" / "markers"
        )
        marker_dir.mkdir(parents=True)
        marker = marker_dir / "unit_1_verified"
        marker.write_text("already")
        state = _make_state(
            current_unit=1,
            total_units=5,
        )
        with pytest.raises(TransitionError):
            complete_unit(state, 1, tmp_path)

    def test_wrong_unit_number_raises(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            complete_unit,
        )

        state = _make_state(
            current_unit=1,
            total_units=5,
        )
        with pytest.raises(TransitionError):
            complete_unit(state, 2, tmp_path)

    def test_not_stage_3_raises(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            complete_unit,
        )

        state = _make_state(
            stage="2",
            current_unit=1,
            total_units=5,
        )
        with pytest.raises(TransitionError):
            complete_unit(state, 1, tmp_path)


# ---------------------------------------------------------------
# advance_stage: error conditions and missing paths
# ---------------------------------------------------------------


class TestAdvanceStageErrors:
    """Blueprint: advance_stage raises TransitionError
    on precondition violation."""

    def test_cannot_advance_past_5(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            advance_stage,
        )

        state = _make_state(stage="5")
        with pytest.raises(TransitionError):
            advance_stage(state, tmp_path)

    def test_advances_from_3_to_4(self, tmp_path):
        from src.unit_3.stub import advance_stage

        state = _make_state(stage="3")
        result = advance_stage(state, tmp_path)
        assert result.stage == "4"

    def test_resets_sub_stage_to_none(self, tmp_path):
        from src.unit_3.stub import advance_stage

        state = _make_state(
            stage="0",
            sub_stage="something",
        )
        result = advance_stage(state, tmp_path)
        assert result.sub_stage is None

    def test_sets_last_action(self, tmp_path):
        from src.unit_3.stub import advance_stage

        state = _make_state(stage="0")
        result = advance_stage(state, tmp_path)
        assert result.last_action is not None
        assert "0" in result.last_action
        assert "1" in result.last_action


# ---------------------------------------------------------------
# rollback_to_unit: preconditions and behavior
# ---------------------------------------------------------------


class TestRollbackToUnitPreconditions:
    """Blueprint: rollback_to_unit precondition errors
    and state reset behavior."""

    def test_not_stage_3_raises(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            rollback_to_unit,
        )

        state = _make_state(
            stage="2",
            current_unit=3,
        )
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 1, tmp_path)

    def test_unit_less_than_1_raises(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            rollback_to_unit,
        )

        state = _make_state(current_unit=3)
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 0, tmp_path)

    def test_future_unit_raises(self, tmp_path):
        from src.unit_3.stub import (
            TransitionError,
            rollback_to_unit,
        )

        state = _make_state(current_unit=2)
        with pytest.raises(TransitionError):
            rollback_to_unit(state, 5, tmp_path)

    def test_invalidates_verified_units(self, tmp_path):
        from src.unit_3.stub import rollback_to_unit

        verified = [
            {"unit": 1, "timestamp": "t1"},
            {"unit": 2, "timestamp": "t2"},
            {"unit": 3, "timestamp": "t3"},
        ]
        state = _make_state(
            current_unit=4,
            verified_units=verified,
        )
        result = rollback_to_unit(state, 2, tmp_path)
        remaining = [
            v["unit"]
            for v in result.verified_units
        ]
        assert 1 in remaining
        assert 2 not in remaining
        assert 3 not in remaining

    def test_resets_fix_ladder(self, tmp_path):
        from src.unit_3.stub import rollback_to_unit

        state = _make_state(
            current_unit=3,
            fix_ladder_position="fresh_test",
        )
        result = rollback_to_unit(state, 1, tmp_path)
        assert result.fix_ladder_position is None

    def test_resets_red_run_retries(self, tmp_path):
        from src.unit_3.stub import rollback_to_unit

        state = _make_state(
            current_unit=3,
            red_run_retries=5,
        )
        result = rollback_to_unit(state, 1, tmp_path)
        assert result.red_run_retries == 0


# ---------------------------------------------------------------
# restart_from_stage: pass_history and counter resets
# ---------------------------------------------------------------


class TestRestartFromStageBehavior:
    """Blueprint: restart_from_stage records pass_history
    and resets counters."""

    def test_records_pass_history(self, tmp_path):
        from src.unit_3.stub import restart_from_stage

        state = _make_state(
            stage="3",
            pass_history=[],
        )
        result = restart_from_stage(
            state, "2", "redo", tmp_path
        )
        assert len(result.pass_history) == 1

    def test_pass_history_contains_reason(self, tmp_path):
        from src.unit_3.stub import restart_from_stage

        state = _make_state(
            stage="3",
            pass_history=[],
        )
        result = restart_from_stage(
            state, "2", "redo request", tmp_path
        )
        entry = result.pass_history[0]
        assert entry["reason"] == "redo request"

    def test_resets_fix_ladder(self, tmp_path):
        from src.unit_3.stub import restart_from_stage

        state = _make_state(
            stage="3",
            fix_ladder_position="hint_test",
        )
        result = restart_from_stage(
            state, "2", "redo", tmp_path
        )
        assert result.fix_ladder_position is None

    def test_resets_red_run_retries(self, tmp_path):
        from src.unit_3.stub import restart_from_stage

        state = _make_state(
            stage="3",
            red_run_retries=4,
        )
        result = restart_from_stage(
            state, "2", "redo", tmp_path
        )
        assert result.red_run_retries == 0

    def test_resets_alignment_iteration(self, tmp_path):
        from src.unit_3.stub import restart_from_stage

        state = _make_state(
            stage="3",
            alignment_iteration=2,
        )
        result = restart_from_stage(
            state, "2", "redo", tmp_path
        )
        assert result.alignment_iteration == 0

    def test_resets_sub_stage_to_none(self, tmp_path):
        from src.unit_3.stub import restart_from_stage

        state = _make_state(
            stage="3",
            sub_stage="red_run",
        )
        result = restart_from_stage(
            state, "2", "redo", tmp_path
        )
        assert result.sub_stage is None

    def test_clears_verified_units_for_early_stage(
        self, tmp_path
    ):
        from src.unit_3.stub import restart_from_stage

        verified = [
            {"unit": 1, "timestamp": "t1"},
        ]
        state = _make_state(
            stage="3",
            verified_units=verified,
        )
        result = restart_from_stage(
            state, "1", "redo", tmp_path
        )
        assert result.verified_units == []


# ---------------------------------------------------------------
# enter_debug_session: preconditions
# ---------------------------------------------------------------


class TestEnterDebugSessionPreconditions:
    """Blueprint: enter_debug_session preconditions."""

    def test_not_stage_5_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            enter_debug_session,
        )

        state = _make_state(stage="3")
        with pytest.raises(TransitionError):
            enter_debug_session(state, "bug")

    def test_session_already_active_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            enter_debug_session,
        )

        ds = _make_debug_session()
        state = _make_state(
            stage="5",
            debug_session=ds,
        )
        with pytest.raises(TransitionError):
            enter_debug_session(state, "another bug")

    def test_initial_phase_is_triage_readonly(self):
        from src.unit_3.stub import (
            enter_debug_session,
        )

        state = _make_state(
            stage="5",
            debug_session=None,
        )
        result = enter_debug_session(
            state, "test bug"
        )
        assert (
            result.debug_session.phase
            == "triage_readonly"
        )

    def test_initial_authorized_is_false(self):
        from src.unit_3.stub import (
            enter_debug_session,
        )

        state = _make_state(
            stage="5",
            debug_session=None,
        )
        result = enter_debug_session(
            state, "test bug"
        )
        assert (
            result.debug_session.authorized is False
        )

    def test_assigns_incremental_bug_id(self):
        from src.unit_3.stub import (
            enter_debug_session,
        )

        history = [{"bug_id": 3}]
        state = _make_state(
            stage="5",
            debug_session=None,
            debug_history=history,
        )
        result = enter_debug_session(
            state, "new bug"
        )
        assert result.debug_session.bug_id == 4


# ---------------------------------------------------------------
# authorize_debug_session: already authorized
# ---------------------------------------------------------------


class TestAuthorizeDebugSessionErrors:
    """Blueprint: authorize already-authorized raises."""

    def test_already_authorized_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            authorize_debug_session,
        )

        ds = _make_debug_session(authorized=True)
        state = _make_state(debug_session=ds)
        with pytest.raises(TransitionError):
            authorize_debug_session(state)

    def test_advances_phase_to_triage(self):
        from src.unit_3.stub import (
            authorize_debug_session,
        )

        ds = _make_debug_session(
            authorized=False,
            phase="triage_readonly",
        )
        state = _make_state(debug_session=ds)
        result = authorize_debug_session(state)
        assert (
            result.debug_session.phase == "triage"
        )


# ---------------------------------------------------------------
# complete_debug_session: not authorized
# ---------------------------------------------------------------


class TestCompleteDebugSessionErrors:
    """Blueprint: complete unauthorized session raises."""

    def test_not_authorized_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            complete_debug_session,
        )

        ds = _make_debug_session(authorized=False)
        state = _make_state(debug_session=ds)
        with pytest.raises(TransitionError):
            complete_debug_session(state, "fix")

    def test_records_fix_summary(self):
        from src.unit_3.stub import (
            complete_debug_session,
        )

        ds = _make_debug_session(authorized=True)
        state = _make_state(
            debug_session=ds,
            debug_history=[],
        )
        result = complete_debug_session(
            state, "patched the issue"
        )
        entry = result.debug_history[0]
        assert (
            entry["fix_summary"]
            == "patched the issue"
        )


# ---------------------------------------------------------------
# abandon_debug_session: appends to debug_history
# ---------------------------------------------------------------


class TestAbandonDebugSessionHistory:
    """Blueprint: abandon appends to debug_history."""

    def test_appends_to_history(self):
        from src.unit_3.stub import (
            abandon_debug_session,
        )

        ds = _make_debug_session()
        state = _make_state(
            debug_session=ds,
            debug_history=[],
        )
        result = abandon_debug_session(state)
        assert len(result.debug_history) == 1

    def test_history_entry_has_abandoned_status(self):
        from src.unit_3.stub import (
            abandon_debug_session,
        )

        ds = _make_debug_session()
        state = _make_state(
            debug_session=ds,
            debug_history=[],
        )
        result = abandon_debug_session(state)
        entry = result.debug_history[0]
        assert entry.get("status") == "abandoned"


# ---------------------------------------------------------------
# update_debug_phase: valid/invalid transitions
# ---------------------------------------------------------------


class TestUpdateDebugPhaseValidation:
    """Blueprint: update_debug_phase validates phase
    transitions per _DEBUG_PHASE_TRANSITIONS."""

    def test_triage_to_investigation(self):
        from src.unit_3.stub import (
            update_debug_phase,
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = update_debug_phase(
            state, "investigation"
        )
        assert (
            result.debug_session.phase
            == "investigation"
        )

    def test_invalid_transition_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            update_debug_phase,
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        with pytest.raises(TransitionError):
            update_debug_phase(state, "complete")

    def test_triage_to_regression_test(self):
        from src.unit_3.stub import (
            update_debug_phase,
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = update_debug_phase(
            state, "regression_test"
        )
        assert (
            result.debug_session.phase
            == "regression_test"
        )

    def test_repair_to_complete(self):
        from src.unit_3.stub import (
            update_debug_phase,
        )

        ds = _make_debug_session(phase="repair")
        state = _make_state(debug_session=ds)
        result = update_debug_phase(
            state, "complete"
        )
        assert (
            result.debug_session.phase == "complete"
        )


# ---------------------------------------------------------------
# enter_quality_gate: preconditions
# ---------------------------------------------------------------


class TestEnterQualityGatePreconditions:
    """Blueprint: enter_quality_gate requires Stage 3."""

    def test_not_stage_3_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            enter_quality_gate,
        )

        state = _make_state(stage="2")
        with pytest.raises(TransitionError):
            enter_quality_gate(
                state, "quality_gate_a"
            )

    def test_invalid_gate_name_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            enter_quality_gate,
        )

        state = _make_state(stage="3")
        with pytest.raises(TransitionError):
            enter_quality_gate(
                state, "quality_gate_c"
            )


# ---------------------------------------------------------------
# enter_redo_profile_revision: behavioral contracts
# ---------------------------------------------------------------


class TestEnterRedoProfileRevisionBehavior:
    """Blueprint: enter_redo_profile_revision sets
    sub_stage and stores snapshot."""

    def test_sets_sub_stage_delivery(self):
        from src.unit_3.stub import (
            enter_redo_profile_revision,
        )

        state = _make_state(stage="3")
        result = enter_redo_profile_revision(
            state, "delivery"
        )
        assert (
            result.sub_stage
            == "redo_profile_delivery"
        )

    def test_sets_sub_stage_blueprint(self):
        from src.unit_3.stub import (
            enter_redo_profile_revision,
        )

        state = _make_state(stage="3")
        result = enter_redo_profile_revision(
            state, "blueprint"
        )
        assert (
            result.sub_stage
            == "redo_profile_blueprint"
        )

    def test_stores_redo_snapshot(self):
        from src.unit_3.stub import (
            enter_redo_profile_revision,
        )

        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=2,
        )
        result = enter_redo_profile_revision(
            state, "delivery"
        )
        snap = result.redo_triggered_from
        assert snap is not None
        assert snap["stage"] == "3"
        assert snap["sub_stage"] == "red_run"
        assert snap["current_unit"] == 2

    def test_invalid_classification_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            enter_redo_profile_revision,
        )

        state = _make_state(stage="3")
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(
                state, "invalid_class"
            )

    def test_already_in_redo_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            enter_redo_profile_revision,
        )

        state = _make_state(
            stage="3",
            sub_stage="redo_profile_delivery",
        )
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(
                state, "delivery"
            )


# ---------------------------------------------------------------
# complete_redo_profile_revision: behavior
# ---------------------------------------------------------------


class TestCompleteRedoProfileRevisionBehavior:
    """Blueprint: complete_redo_profile_revision restores
    snapshot for delivery, restarts for blueprint."""

    def test_delivery_restores_snapshot(self):
        from src.unit_3.stub import (
            complete_redo_profile_revision,
        )

        snapshot = {
            "stage": "3",
            "sub_stage": "red_run",
            "current_unit": 2,
            "fix_ladder_position": None,
            "red_run_retries": 1,
        }
        state = _make_state(
            sub_stage="redo_profile_delivery",
            redo_triggered_from=snapshot,
        )
        result = complete_redo_profile_revision(
            state
        )
        assert result.stage == "3"
        assert result.sub_stage == "red_run"
        assert result.current_unit == 2
        assert result.redo_triggered_from is None

    def test_blueprint_restarts_from_stage_2(self):
        from src.unit_3.stub import (
            complete_redo_profile_revision,
        )

        state = _make_state(
            sub_stage="redo_profile_blueprint",
        )
        result = complete_redo_profile_revision(
            state
        )
        assert result.stage == "2"
        assert result.sub_stage is None
        assert result.redo_triggered_from is None

    def test_blueprint_resets_counters(self):
        from src.unit_3.stub import (
            complete_redo_profile_revision,
        )

        state = _make_state(
            sub_stage="redo_profile_blueprint",
            fix_ladder_position="hint_test",
            red_run_retries=3,
            alignment_iteration=2,
        )
        result = complete_redo_profile_revision(
            state
        )
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0
        assert result.alignment_iteration == 0

    def test_blueprint_records_pass_history(self):
        from src.unit_3.stub import (
            complete_redo_profile_revision,
        )

        state = _make_state(
            sub_stage="redo_profile_blueprint",
            pass_history=[],
        )
        result = complete_redo_profile_revision(
            state
        )
        assert len(result.pass_history) == 1

    def test_not_in_redo_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            complete_redo_profile_revision,
        )

        state = _make_state(
            sub_stage="test_generation",
        )
        with pytest.raises(TransitionError):
            complete_redo_profile_revision(state)


# ---------------------------------------------------------------
# increment_alignment_iteration: limit check
# ---------------------------------------------------------------


class TestIncrementAlignmentIterationLimit:
    """Blueprint: exceeding iteration_limit raises
    TransitionError."""

    def test_exceeds_limit_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            increment_alignment_iteration,
        )

        state = _make_state(
            alignment_iteration=100,
        )
        with pytest.raises(TransitionError):
            increment_alignment_iteration(state)


# ---------------------------------------------------------------
# set_delivered_repo_path: empty path
# ---------------------------------------------------------------


class TestSetDeliveredRepoPathErrors:
    """Blueprint: empty path raises TransitionError."""

    def test_empty_path_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            set_delivered_repo_path,
        )

        state = _make_state()
        with pytest.raises(TransitionError):
            set_delivered_repo_path(state, "")

    def test_whitespace_only_path_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            set_delivered_repo_path,
        )

        state = _make_state()
        with pytest.raises(TransitionError):
            set_delivered_repo_path(state, "   ")


# ---------------------------------------------------------------
# update_state_from_status: edge cases
# ---------------------------------------------------------------


class TestUpdateStateFromStatusEdgeCases:
    """Blueprint: update_state_from_status handles
    missing file and empty content."""

    def test_missing_file_returns_clone(self, tmp_path):
        from src.unit_3.stub import (
            update_state_from_status,
        )

        state = _make_state()
        missing = tmp_path / "nonexistent.txt"
        result = update_state_from_status(
            state,
            missing,
            unit=1,
            phase="test",
            project_root=tmp_path,
        )
        assert result is not state

    def test_empty_file_returns_clone(self, tmp_path):
        from src.unit_3.stub import (
            update_state_from_status,
        )

        state = _make_state()
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        result = update_state_from_status(
            state,
            empty,
            unit=1,
            phase="test",
            project_root=tmp_path,
        )
        assert result is not state


# ---------------------------------------------------------------
# version_document: file creation behavior
# ---------------------------------------------------------------


class TestVersionDocumentBehavior:
    """Blueprint: version_document creates versioned copy
    and diff file in history_dir."""

    def test_versioned_copy_exists(self, tmp_path):
        from src.unit_3.stub import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("original content")
        history = tmp_path / "history"
        history.mkdir()
        versioned, diff = version_document(
            doc, history, "changes", "trigger"
        )
        assert versioned.exists()

    def test_diff_file_exists(self, tmp_path):
        from src.unit_3.stub import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("original content")
        history = tmp_path / "history"
        history.mkdir()
        versioned, diff = version_document(
            doc, history, "changes", "trigger"
        )
        assert diff.exists()

    def test_versioned_copy_matches_original(
        self, tmp_path
    ):
        from src.unit_3.stub import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("original content")
        history = tmp_path / "history"
        history.mkdir()
        versioned, _ = version_document(
            doc, history, "changes", "trigger"
        )
        assert (
            versioned.read_text()
            == "original content"
        )

    def test_diff_contains_summary(self, tmp_path):
        from src.unit_3.stub import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("content")
        history = tmp_path / "history"
        history.mkdir()
        _, diff = version_document(
            doc,
            history,
            "added section X",
            "trigger",
        )
        content = diff.read_text()
        assert "added section X" in content

    def test_version_increments(self, tmp_path):
        from src.unit_3.stub import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("content")
        history = tmp_path / "history"
        history.mkdir()
        v1, _ = version_document(
            doc, history, "first", "trigger"
        )
        v2, _ = version_document(
            doc, history, "second", "trigger"
        )
        assert "v1" in v1.name
        assert "v2" in v2.name

    def test_creates_history_dir_if_missing(
        self, tmp_path
    ):
        from src.unit_3.stub import version_document

        doc = tmp_path / "spec.md"
        doc.write_text("content")
        history = tmp_path / "new_history"
        version_document(
            doc, history, "changes", "trigger"
        )
        assert history.exists()


# ---------------------------------------------------------------
# advance_fix_ladder: None -> fresh_impl (alt branch)
# ---------------------------------------------------------------


class TestAdvanceFixLadderImplBranch:
    """Blueprint: fix ladder allows None -> fresh_impl
    (implementation branch)."""

    def test_none_to_fresh_impl(self):
        from src.unit_3.stub import (
            advance_fix_ladder,
        )

        state = _make_state(
            fix_ladder_position=None,
        )
        result = advance_fix_ladder(
            state, "fresh_impl"
        )
        assert (
            result.fix_ladder_position
            == "fresh_impl"
        )

    def test_same_position_raises(self):
        from src.unit_3.stub import (
            TransitionError,
            advance_fix_ladder,
        )

        state = _make_state(
            fix_ladder_position="fresh_test",
        )
        with pytest.raises(TransitionError):
            advance_fix_ladder(
                state, "fresh_test"
            )


# ---------------------------------------------------------------
# Immutability: remaining functions not in Section 18
# ---------------------------------------------------------------


class TestImmutabilityAdditional:
    """Blueprint: all transition functions do not mutate
    input -- covering functions missing from the
    original immutability section."""

    def test_rollback_to_unit_immutable(
        self, tmp_path
    ):
        from src.unit_3.stub import rollback_to_unit

        state = _make_state(current_unit=3)
        old_dict = state.to_dict()
        rollback_to_unit(state, 1, tmp_path)
        assert state.to_dict() == old_dict

    def test_restart_from_stage_immutable(
        self, tmp_path
    ):
        from src.unit_3.stub import (
            restart_from_stage,
        )

        state = _make_state(stage="3")
        old_dict = state.to_dict()
        restart_from_stage(
            state, "2", "redo", tmp_path
        )
        assert state.to_dict() == old_dict

    def test_increment_red_run_retries_immutable(
        self,
    ):
        from src.unit_3.stub import (
            increment_red_run_retries,
        )

        state = _make_state(red_run_retries=1)
        old_dict = state.to_dict()
        increment_red_run_retries(state)
        assert state.to_dict() == old_dict

    def test_reset_red_run_retries_immutable(self):
        from src.unit_3.stub import (
            reset_red_run_retries,
        )

        state = _make_state(red_run_retries=3)
        old_dict = state.to_dict()
        reset_red_run_retries(state)
        assert state.to_dict() == old_dict

    def test_increment_alignment_immutable(self):
        from src.unit_3.stub import (
            increment_alignment_iteration,
        )

        state = _make_state(
            alignment_iteration=0,
        )
        old_dict = state.to_dict()
        increment_alignment_iteration(state)
        assert state.to_dict() == old_dict

    def test_reset_alignment_immutable(self):
        from src.unit_3.stub import (
            reset_alignment_iteration,
        )

        state = _make_state(
            alignment_iteration=2,
        )
        old_dict = state.to_dict()
        reset_alignment_iteration(state)
        assert state.to_dict() == old_dict

    def test_reset_fix_ladder_immutable(self):
        from src.unit_3.stub import (
            reset_fix_ladder,
        )

        state = _make_state(
            fix_ladder_position="fresh_test",
        )
        old_dict = state.to_dict()
        reset_fix_ladder(state)
        assert state.to_dict() == old_dict

    def test_authorize_debug_immutable(self):
        from src.unit_3.stub import (
            authorize_debug_session,
        )

        ds = _make_debug_session(
            authorized=False,
        )
        state = _make_state(debug_session=ds)
        old_dict = state.to_dict()
        authorize_debug_session(state)
        assert state.to_dict() == old_dict

    def test_complete_debug_immutable(self):
        from src.unit_3.stub import (
            complete_debug_session,
        )

        ds = _make_debug_session(authorized=True)
        state = _make_state(
            debug_session=ds,
            debug_history=[],
        )
        old_dict = state.to_dict()
        complete_debug_session(state, "fix")
        assert state.to_dict() == old_dict

    def test_abandon_debug_immutable(self):
        from src.unit_3.stub import (
            abandon_debug_session,
        )

        ds = _make_debug_session()
        state = _make_state(
            debug_session=ds,
            debug_history=[],
        )
        old_dict = state.to_dict()
        abandon_debug_session(state)
        assert state.to_dict() == old_dict

    def test_update_debug_phase_immutable(self):
        from src.unit_3.stub import (
            update_debug_phase,
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        old_dict = state.to_dict()
        update_debug_phase(state, "investigation")
        assert state.to_dict() == old_dict

    def test_set_debug_classification_immutable(
        self,
    ):
        from src.unit_3.stub import (
            set_debug_classification,
        )

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        old_dict = state.to_dict()
        set_debug_classification(
            state, "single_unit", [1]
        )
        assert state.to_dict() == old_dict

    def test_enter_quality_gate_immutable(self):
        from src.unit_3.stub import (
            enter_quality_gate,
        )

        state = _make_state(stage="3")
        old_dict = state.to_dict()
        enter_quality_gate(
            state, "quality_gate_a"
        )
        assert state.to_dict() == old_dict

    def test_enter_quality_gate_retry_immutable(
        self,
    ):
        from src.unit_3.stub import (
            enter_quality_gate_retry,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        old_dict = state.to_dict()
        enter_quality_gate_retry(
            state, "quality_gate_a_retry"
        )
        assert state.to_dict() == old_dict

    def test_advance_from_quality_gate_immutable(
        self,
    ):
        from src.unit_3.stub import (
            advance_from_quality_gate,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
        )
        old_dict = state.to_dict()
        advance_from_quality_gate(
            state, "red_run"
        )
        assert state.to_dict() == old_dict

    def test_fail_quality_gate_to_ladder_immutable(
        self,
    ):
        from src.unit_3.stub import (
            fail_quality_gate_to_ladder,
        )

        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
        )
        old_dict = state.to_dict()
        fail_quality_gate_to_ladder(
            state, "fresh_test"
        )
        assert state.to_dict() == old_dict

    def test_enter_redo_profile_immutable(self):
        from src.unit_3.stub import (
            enter_redo_profile_revision,
        )

        state = _make_state(stage="3")
        old_dict = state.to_dict()
        enter_redo_profile_revision(
            state, "delivery"
        )
        assert state.to_dict() == old_dict

    def test_complete_redo_profile_immutable(self):
        from src.unit_3.stub import (
            complete_redo_profile_revision,
        )

        state = _make_state(
            sub_stage="redo_profile_delivery",
        )
        old_dict = state.to_dict()
        complete_redo_profile_revision(state)
        assert state.to_dict() == old_dict

    def test_update_state_from_status_immutable(
        self, tmp_path
    ):
        from src.unit_3.stub import (
            update_state_from_status,
        )

        state = _make_state()
        status = tmp_path / "status.txt"
        status.write_text("DONE")
        old_dict = state.to_dict()
        update_state_from_status(
            state,
            status,
            unit=1,
            phase="test",
            project_root=tmp_path,
        )
        assert state.to_dict() == old_dict
