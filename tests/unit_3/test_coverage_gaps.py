"""
Additional coverage tests for Unit 3: State Transition Engine

These tests cover behavioral contracts from the blueprint that were not
exercised by the original test suite.

Gaps covered:
1. version_document diff file contains trigger_context and timestamp
2. rollback_to_unit moves generated code and tests to logs/rollback/
3. restart_from_stage records reached_unit in pass_history
4. restart_from_stage resets ALL stage-specific counters (fix_ladder,
   red_run_retries, alignment_iteration)
5. complete_debug_session preserves fix_summary in debug_history
6. abandon_debug_session raises when no active session
7. update_debug_phase raises when no active session
8. set_debug_classification raises when no active session
9. advance_stage resets sub_stage to None
10. rollback_to_unit resets fix_ladder_position and red_run_retries
11. complete_debug_session and abandon_debug_session preserve stage as "5"
12. complete_debug_session stores fix_summary in history record
13. record_pass_end records reached_unit in history
14. version_document diff file contains trigger_context string

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: Project roots are temporary directories created via
tmp_path, representing valid filesystem directories.

DATA ASSUMPTION: PipelineState objects are created using the real
PipelineState class from svp.scripts.pipeline_state, with stage values from
STAGES ("0"-"5", "pre_stage_3").

DATA ASSUMPTION: Unit numbers are small positive integers (1-5),
representing a typical project with a moderate number of blueprint units.

DATA ASSUMPTION: Total units is set to 5, representing a typical
small-to-medium project.

DATA ASSUMPTION: Fix ladder positions follow the blueprint sequence:
None -> fresh_test -> hint_test (test ladder) and
None -> fresh_impl -> diagnostic -> diagnostic_impl (impl ladder).

DATA ASSUMPTION: Debug session phases follow the exact string literals:
"triage_readonly", "triage", "regression_test", "stage3_reentry",
"repair", "complete".

DATA ASSUMPTION: Document content is simple markdown text, representing
typical spec/blueprint documents.

DATA ASSUMPTION: Diff summaries are short descriptive strings like
"Updated error handling section", representing typical version diffs.

DATA ASSUMPTION: Trigger contexts are strings like "Stage 2 alignment",
representing the pipeline context that triggered the document version.

DATA ASSUMPTION: Fix summaries are short strings like
"Fixed null reference in auth handler", representing typical fix notes.
==========================================================================
"""

import pytest
from pathlib import Path
from typing import List

from svp.scripts.pipeline_state import PipelineState, DebugSession

from svp.scripts.state_transitions import (
    TransitionError,
    advance_stage,
    advance_sub_stage,
    complete_unit,
    advance_fix_ladder,
    reset_fix_ladder,
    increment_red_run_retries,
    reset_red_run_retries,
    increment_alignment_iteration,
    reset_alignment_iteration,
    record_pass_end,
    rollback_to_unit,
    restart_from_stage,
    version_document,
    enter_debug_session,
    authorize_debug_session,
    complete_debug_session,
    abandon_debug_session,
    update_debug_phase,
    set_debug_classification,
    update_state_from_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**overrides) -> PipelineState:
    """Create a PipelineState with sensible defaults, overriding as needed.

    DATA ASSUMPTION: Defaults represent a state at Stage 3, Unit 1, with
    5 total units, no prior passes or verified units.
    """
    defaults = dict(
        stage="3",
        sub_stage=None,
        current_unit=1,
        total_units=5,
        fix_ladder_position=None,
        red_run_retries=0,
        alignment_iteration=0,
        verified_units=[],
        pass_history=[],
        log_references={},
        project_name="test_project",
        last_action=None,
        debug_session=None,
        debug_history=[],
        created_at="2025-01-15T10:00:00+00:00",
        updated_at="2025-01-15T10:00:00+00:00",
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


def _setup_markers_dir(project_root: Path) -> Path:
    """Create .svp/markers/ directory."""
    markers_dir = project_root / ".svp" / "markers"
    markers_dir.mkdir(parents=True, exist_ok=True)
    return markers_dir


def _write_unit_marker(project_root: Path, unit_number: int):
    """Write a verified marker file for a given unit."""
    markers_dir = _setup_markers_dir(project_root)
    marker_file = markers_dir / f"unit_{unit_number}_verified"
    marker_file.write_text(f"VERIFIED: 2025-01-15T10:00:00+00:00", encoding="utf-8")
    return marker_file


# ---------------------------------------------------------------------------
# Gap 1 & 9: version_document diff file contains trigger_context and timestamp
# ---------------------------------------------------------------------------

class TestVersionDocumentDiffContent:
    """Test that version_document diff file contains all required content:
    what changed, why, what stage triggered it, and a timestamp.

    Blueprint contract: 'writes a diff summary to history/{name}_v{N}_diff.md
    containing what changed, why, what stage triggered it, and a timestamp.'
    """

    def test_version_document_diff_contains_trigger_context(self, tmp_path):
        """Diff file must contain the trigger_context string."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Specification\nContent here.", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated error handling", "Stage 2 alignment"
        )
        diff_content = diff_file.read_text()
        assert "Stage 2 alignment" in diff_content

    def test_version_document_diff_contains_timestamp(self, tmp_path):
        """Diff file must contain a timestamp."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Specification\nContent here.", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated error handling", "Stage 2 alignment"
        )
        diff_content = diff_file.read_text()
        # Timestamps contain "T" separating date from time in ISO format
        # and typically contain a year like 202x
        assert "202" in diff_content  # Matches any 202x year in timestamp


# ---------------------------------------------------------------------------
# Gap 2: rollback_to_unit moves code and tests to logs/rollback/
# ---------------------------------------------------------------------------

class TestRollbackMovesToLogsRollback:
    """Test that rollback_to_unit moves generated code and tests to logs/rollback/.

    Blueprint contract: 'moves their generated code and tests to logs/rollback/'
    """

    def test_rollback_moves_source_to_logs_rollback(self, tmp_path):
        """rollback_to_unit copies source directories to logs/rollback/."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)

        # Create source directory for unit 2 to be rolled back
        src_dir = tmp_path / "src" / "unit_2"
        src_dir.mkdir(parents=True)
        (src_dir / "impl.py").write_text("# implementation", encoding="utf-8")

        result = rollback_to_unit(state, 2, tmp_path)

        # Source should have been copied to logs/rollback/
        rollback_dir = tmp_path / "logs" / "rollback"
        assert rollback_dir.exists()
        rollback_src = rollback_dir / "unit_2_src"
        assert rollback_src.exists()

    def test_rollback_moves_tests_to_logs_rollback(self, tmp_path):
        """rollback_to_unit copies test directories to logs/rollback/."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)

        # Create test directory for unit 2 to be rolled back
        test_dir = tmp_path / "tests" / "unit_2"
        test_dir.mkdir(parents=True)
        (test_dir / "test_impl.py").write_text("# tests", encoding="utf-8")

        result = rollback_to_unit(state, 2, tmp_path)

        # Tests should have been copied to logs/rollback/
        rollback_dir = tmp_path / "logs" / "rollback"
        assert rollback_dir.exists()
        rollback_tests = rollback_dir / "unit_2_tests"
        assert rollback_tests.exists()


# ---------------------------------------------------------------------------
# Gap 3: restart_from_stage records reached_unit in pass_history
# ---------------------------------------------------------------------------

class TestRestartFromStageReachedUnit:
    """Test that restart_from_stage records how far the pass reached.

    Blueprint contract: 'records the current pass in pass_history
    (how far it reached, why it ended)'
    """

    def test_restart_from_stage_records_reached_unit(self, tmp_path):
        """Pass history entry should contain reached_unit."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5, pass_history=[]
        )
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        latest = result.pass_history[-1]
        assert "reached_unit" in latest
        assert latest["reached_unit"] == 3


# ---------------------------------------------------------------------------
# Gap 4: restart_from_stage resets ALL stage-specific counters
# ---------------------------------------------------------------------------

class TestRestartFromStageFullCounterReset:
    """Test that restart_from_stage resets ALL stage-specific counters.

    Blueprint contract: 'resets stage-specific counters'
    This covers fix_ladder_position, red_run_retries, AND alignment_iteration.
    """

    def test_restart_from_stage_resets_fix_ladder_position(self, tmp_path):
        """fix_ladder_position must be reset to None."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            fix_ladder_position="fresh_test",
            red_run_retries=2,
            alignment_iteration=1,
        )
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert result.fix_ladder_position is None

    def test_restart_from_stage_resets_red_run_retries(self, tmp_path):
        """red_run_retries must be reset to 0."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            fix_ladder_position="fresh_test",
            red_run_retries=2,
            alignment_iteration=1,
        )
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert result.red_run_retries == 0

    def test_restart_from_stage_resets_alignment_iteration(self, tmp_path):
        """alignment_iteration must be reset to 0."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            fix_ladder_position="fresh_test",
            red_run_retries=2,
            alignment_iteration=1,
        )
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert result.alignment_iteration == 0


# ---------------------------------------------------------------------------
# Gap 5 & 12: complete_debug_session preserves fix_summary in debug_history
# ---------------------------------------------------------------------------

class TestCompleteDebugSessionFixSummary:
    """Test that complete_debug_session stores fix_summary in the history record.

    Blueprint contract: 'Moves the debug session record to debug_history'
    The fix_summary parameter should be preserved in the history record.
    """

    def test_complete_debug_session_records_fix_summary(self):
        """The debug_history entry should contain the fix_summary."""
        session = DebugSession(
            bug_id=1, description="Login crash", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = complete_debug_session(state, "Fixed null reference in auth handler")
        latest = result.debug_history[-1]
        assert latest.get("fix_summary") == "Fixed null reference in auth handler"


# ---------------------------------------------------------------------------
# Gap 6: abandon_debug_session raises when no active session
# ---------------------------------------------------------------------------

class TestAbandonDebugSessionNoSession:
    """Test that abandon_debug_session raises when there is no active session.

    Blueprint implies: abandon_debug_session requires an active session.
    """

    def test_abandon_debug_session_no_session_raises(self):
        """abandon_debug_session with no active session should raise."""
        state = _make_state(stage="5", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)):
            abandon_debug_session(state)


# ---------------------------------------------------------------------------
# Gap 7: update_debug_phase raises when no active session
# ---------------------------------------------------------------------------

class TestUpdateDebugPhaseNoSession:
    """Test that update_debug_phase raises when there is no active session.

    Blueprint contract: 'update_debug_phase validates phase transitions'
    - requires an active debug session.
    """

    def test_update_debug_phase_no_session_raises(self):
        """update_debug_phase with no active session should raise."""
        state = _make_state(stage="5", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)):
            update_debug_phase(state, "triage")


# ---------------------------------------------------------------------------
# Gap 8: set_debug_classification raises when no active session
# ---------------------------------------------------------------------------

class TestSetDebugClassificationNoSession:
    """Test that set_debug_classification raises when there is no active session.

    Blueprint contract: 'set_debug_classification sets the classification
    and affected units on the debug session' - requires an active session.
    """

    def test_set_debug_classification_no_session_raises(self):
        """set_debug_classification with no active session should raise."""
        state = _make_state(stage="5", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)):
            set_debug_classification(state, "single_unit", [3])


# ---------------------------------------------------------------------------
# Gap 10: advance_stage resets sub_stage to None
# ---------------------------------------------------------------------------

class TestAdvanceStageResetsSubStage:
    """Test that advance_stage clears sub_stage when advancing.

    Blueprint contract: 'advance_stage moves the state to the next stage'
    The sub_stage should be cleared/reset when moving to a new stage.
    """

    def test_advance_stage_clears_sub_stage(self, tmp_path):
        """sub_stage should be None after advancing stage."""
        state = _make_state(
            stage="0", sub_stage="hook_activation",
            current_unit=None, total_units=None
        )
        result = advance_stage(state, tmp_path)
        assert result.sub_stage is None


# ---------------------------------------------------------------------------
# Gap 11: rollback_to_unit resets fix_ladder and red_run_retries
# ---------------------------------------------------------------------------

class TestRollbackResetsCounters:
    """Test that rollback_to_unit resets fix_ladder_position and red_run_retries.

    Blueprint contract implies the rolled-back unit gets a fresh start,
    and implementation resets these counters.
    """

    def test_rollback_resets_fix_ladder_position(self, tmp_path):
        """fix_ladder_position should be None after rollback."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            fix_ladder_position="fresh_test",
            red_run_retries=2,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        result = rollback_to_unit(state, 2, tmp_path)
        assert result.fix_ladder_position is None

    def test_rollback_resets_red_run_retries(self, tmp_path):
        """red_run_retries should be 0 after rollback."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            fix_ladder_position="fresh_test",
            red_run_retries=2,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        result = rollback_to_unit(state, 2, tmp_path)
        assert result.red_run_retries == 0


# ---------------------------------------------------------------------------
# Gap 12: complete_debug_session and abandon_debug_session preserve stage "5"
# ---------------------------------------------------------------------------

class TestDebugSessionPreservesStage5:
    """Test that complete/abandon debug session returns the state to Stage 5.

    Blueprint contract:
    - complete_debug_session 'returns the state to Stage 5 complete'
    - abandon_debug_session 'returns the state to Stage 5 complete'
    """

    def test_complete_debug_session_state_remains_stage_5(self):
        """After completing a debug session, stage should remain '5'."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = complete_debug_session(state, "Fixed the bug")
        assert result.stage == "5"

    def test_abandon_debug_session_state_remains_stage_5(self):
        """After abandoning a debug session, stage should remain '5'."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        assert result.stage == "5"


# ---------------------------------------------------------------------------
# Gap 13: record_pass_end records reached_unit
# ---------------------------------------------------------------------------

class TestRecordPassEndReachedUnit:
    """Test that record_pass_end records the reached_unit in pass_history.

    Blueprint contract: pass_history should record how far the pass reached.
    """

    def test_record_pass_end_records_reached_unit(self):
        """Pass history entry should contain the current_unit as reached_unit."""
        state = _make_state(current_unit=3, pass_history=[])
        result = record_pass_end(state, "unit_failed")
        latest = result.pass_history[-1]
        assert "reached_unit" in latest
        assert latest["reached_unit"] == 3

    def test_record_pass_end_records_timestamp(self):
        """Pass history entry should contain a timestamp."""
        state = _make_state(current_unit=3, pass_history=[])
        result = record_pass_end(state, "unit_failed")
        latest = result.pass_history[-1]
        assert "timestamp" in latest
        assert latest["timestamp"] is not None


# ---------------------------------------------------------------------------
# Additional gap: update_debug_phase valid phase transition sequences
# ---------------------------------------------------------------------------

class TestUpdateDebugPhaseTransitions:
    """Test valid debug phase transition sequences beyond the basic test.

    Blueprint contract: 'update_debug_phase validates phase transitions
    and updates debug_session.phase.'

    The valid transitions are:
    triage_readonly -> triage
    triage -> regression_test, stage3_reentry
    regression_test -> stage3_reentry, repair
    stage3_reentry -> repair, complete
    repair -> complete
    """

    def test_update_debug_phase_triage_to_stage3_reentry(self):
        """Valid transition: triage -> stage3_reentry."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "stage3_reentry")
        assert result.debug_session.phase == "stage3_reentry"

    def test_update_debug_phase_regression_test_to_repair(self):
        """Valid transition: regression_test -> repair."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="regression_test"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "repair")
        assert result.debug_session.phase == "repair"

    def test_update_debug_phase_regression_test_to_stage3_reentry(self):
        """Valid transition: regression_test -> stage3_reentry."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="regression_test"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "stage3_reentry")
        assert result.debug_session.phase == "stage3_reentry"

    def test_update_debug_phase_stage3_reentry_to_repair(self):
        """Valid transition: stage3_reentry -> repair."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="stage3_reentry"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "repair")
        assert result.debug_session.phase == "repair"

    def test_update_debug_phase_stage3_reentry_to_complete(self):
        """Valid transition: stage3_reentry -> complete."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="stage3_reentry"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "complete")
        assert result.debug_session.phase == "complete"

    def test_update_debug_phase_repair_to_complete(self):
        """Valid transition: repair -> complete."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "complete")
        assert result.debug_session.phase == "complete"

    def test_update_debug_phase_backward_transition_raises(self):
        """Invalid backward transition: regression_test -> triage_readonly."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="regression_test"
        )
        state = _make_state(stage="5", debug_session=session)
        with pytest.raises((TransitionError, ValueError, AssertionError)):
            update_debug_phase(state, "triage_readonly")

    def test_update_debug_phase_complete_cannot_transition(self):
        """No transitions allowed from 'complete' phase."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="complete"
        )
        state = _make_state(stage="5", debug_session=session)
        with pytest.raises((TransitionError, ValueError, AssertionError)):
            update_debug_phase(state, "repair")
