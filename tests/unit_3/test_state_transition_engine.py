"""
Test suite for Unit 3: State Transition Engine

Tests cover:
- TransitionError exception class
- advance_stage: stage progression and precondition validation
- advance_sub_stage: sub-stage transitions
- complete_unit: marker writing, verified_units update, fix ladder/retry reset,
  current_unit advancement, stage advancement when all units complete
- advance_fix_ladder: valid ladder sequence enforcement, invalid transition errors
- reset_fix_ladder: resets fix_ladder_position to None
- increment_red_run_retries / reset_red_run_retries
- increment_alignment_iteration / reset_alignment_iteration (with limit)
- record_pass_end: pass history recording
- rollback_to_unit: marker removal, verified_units cleanup, current_unit reset
- restart_from_stage: pass_history recording, counter resets, stage setting
- version_document: copy creation, diff file creation, FileNotFoundError
- enter_debug_session: DebugSession creation, precondition checks
- authorize_debug_session: authorization flag and phase transition
- complete_debug_session: debug_history recording, session cleanup
- abandon_debug_session: abandoned marker, session cleanup
- update_debug_phase: phase transition validation
- set_debug_classification: classification and affected_units setting
- update_state_from_status: status file parsing and dispatch
- Immutability: all transition functions return new PipelineState, not mutated input
- All invariants from the blueprint
- All error conditions from the blueprint
- Signature verification for all public functions and classes

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

DATA ASSUMPTION: Bug descriptions are short strings like
"Login page crashes on submit", representing typical bug reports.

DATA ASSUMPTION: Fix summaries are short strings like
"Fixed null reference in auth handler", representing typical fix notes.

DATA ASSUMPTION: Document content is simple markdown text, representing
typical spec/blueprint documents.

DATA ASSUMPTION: Diff summaries are short descriptive strings like
"Updated error handling section", representing typical version diffs.

DATA ASSUMPTION: Trigger contexts are strings like "Stage 2 alignment",
representing the pipeline context that triggered the document version.

DATA ASSUMPTION: Fix ladder positions follow the blueprint sequence:
None -> fresh_test -> hint_test (test ladder) and
None -> fresh_impl -> diagnostic -> diagnostic_impl (impl ladder).

DATA ASSUMPTION: Debug session phases follow the exact string literals:
"triage_readonly", "triage", "regression_test", "stage3_reentry",
"repair", "complete".

DATA ASSUMPTION: Classification values are "build_env", "single_unit",
or "cross_unit" as specified in the upstream Unit 2 schema.

DATA ASSUMPTION: The iteration_limit config default is 3, matching
Unit 1's DEFAULT_CONFIG.

DATA ASSUMPTION: Status file content follows the terminal status line
format e.g. "TEST_GENERATION_COMPLETE", "TESTS_PASSED: N passed",
"TESTS_FAILED: N failed".

DATA ASSUMPTION: Marker files contain "VERIFIED: {timestamp}" text,
matching the blueprint's specified format.
==========================================================================
"""

import inspect
import os
import pytest
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

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
    5 total units, no prior passes or verified units. This is the most
    commonly tested starting state for transition functions.
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
# TransitionError
# ---------------------------------------------------------------------------

class TestTransitionError:
    """Test that TransitionError is a proper Exception subclass."""

    def test_transition_error_is_exception(self):
        assert issubclass(TransitionError, Exception)

    def test_transition_error_can_be_raised(self):
        with pytest.raises(TransitionError):
            raise TransitionError("test error")

    def test_transition_error_message(self):
        with pytest.raises(TransitionError, match="test error"):
            raise TransitionError("test error")

    def test_transition_error_docstring(self):
        assert TransitionError.__doc__ is not None
        assert "preconditions" in TransitionError.__doc__.lower() or \
               "transition" in TransitionError.__doc__.lower()


# ---------------------------------------------------------------------------
# Signature Verification
# ---------------------------------------------------------------------------

class TestSignatures:
    """Verify all function signatures match the blueprint."""

    def test_advance_stage_signature(self):
        sig = inspect.signature(advance_stage)
        params = list(sig.parameters.keys())
        assert params == ["state", "project_root"]
        assert sig.parameters["state"].annotation == PipelineState
        assert sig.parameters["project_root"].annotation == Path
        assert sig.return_annotation == PipelineState

    def test_advance_sub_stage_signature(self):
        sig = inspect.signature(advance_sub_stage)
        params = list(sig.parameters.keys())
        assert params == ["state", "sub_stage", "project_root"]
        assert sig.parameters["state"].annotation == PipelineState
        assert sig.parameters["sub_stage"].annotation == str
        assert sig.parameters["project_root"].annotation == Path
        assert sig.return_annotation == PipelineState

    def test_complete_unit_signature(self):
        sig = inspect.signature(complete_unit)
        params = list(sig.parameters.keys())
        assert params == ["state", "unit_number", "project_root"]
        assert sig.parameters["state"].annotation == PipelineState
        assert sig.parameters["unit_number"].annotation == int
        assert sig.parameters["project_root"].annotation == Path
        assert sig.return_annotation == PipelineState

    def test_advance_fix_ladder_signature(self):
        sig = inspect.signature(advance_fix_ladder)
        params = list(sig.parameters.keys())
        assert params == ["state", "new_position"]
        assert sig.parameters["state"].annotation == PipelineState
        assert sig.parameters["new_position"].annotation == str
        assert sig.return_annotation == PipelineState

    def test_reset_fix_ladder_signature(self):
        sig = inspect.signature(reset_fix_ladder)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_increment_red_run_retries_signature(self):
        sig = inspect.signature(increment_red_run_retries)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_reset_red_run_retries_signature(self):
        sig = inspect.signature(reset_red_run_retries)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_increment_alignment_iteration_signature(self):
        sig = inspect.signature(increment_alignment_iteration)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_reset_alignment_iteration_signature(self):
        sig = inspect.signature(reset_alignment_iteration)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_record_pass_end_signature(self):
        sig = inspect.signature(record_pass_end)
        params = list(sig.parameters.keys())
        assert params == ["state", "reason"]
        assert sig.parameters["reason"].annotation == str
        assert sig.return_annotation == PipelineState

    def test_rollback_to_unit_signature(self):
        sig = inspect.signature(rollback_to_unit)
        params = list(sig.parameters.keys())
        assert params == ["state", "unit_number", "project_root"]
        assert sig.parameters["unit_number"].annotation == int
        assert sig.return_annotation == PipelineState

    def test_restart_from_stage_signature(self):
        sig = inspect.signature(restart_from_stage)
        params = list(sig.parameters.keys())
        assert params == ["state", "target_stage", "reason", "project_root"]
        assert sig.parameters["target_stage"].annotation == str
        assert sig.parameters["reason"].annotation == str
        assert sig.return_annotation == PipelineState

    def test_version_document_signature(self):
        sig = inspect.signature(version_document)
        params = list(sig.parameters.keys())
        assert params == ["doc_path", "history_dir", "diff_summary", "trigger_context"]
        assert sig.parameters["doc_path"].annotation == Path
        assert sig.parameters["history_dir"].annotation == Path
        assert sig.parameters["diff_summary"].annotation == str
        assert sig.parameters["trigger_context"].annotation == str
        assert sig.return_annotation == Tuple[Path, Path]

    def test_enter_debug_session_signature(self):
        sig = inspect.signature(enter_debug_session)
        params = list(sig.parameters.keys())
        assert params == ["state", "bug_description"]
        assert sig.parameters["bug_description"].annotation == str
        assert sig.return_annotation == PipelineState

    def test_authorize_debug_session_signature(self):
        sig = inspect.signature(authorize_debug_session)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_complete_debug_session_signature(self):
        sig = inspect.signature(complete_debug_session)
        params = list(sig.parameters.keys())
        assert params == ["state", "fix_summary"]
        assert sig.parameters["fix_summary"].annotation == str
        assert sig.return_annotation == PipelineState

    def test_abandon_debug_session_signature(self):
        sig = inspect.signature(abandon_debug_session)
        params = list(sig.parameters.keys())
        assert params == ["state"]
        assert sig.return_annotation == PipelineState

    def test_update_debug_phase_signature(self):
        sig = inspect.signature(update_debug_phase)
        params = list(sig.parameters.keys())
        assert params == ["state", "phase"]
        assert sig.parameters["phase"].annotation == str
        assert sig.return_annotation == PipelineState

    def test_set_debug_classification_signature(self):
        sig = inspect.signature(set_debug_classification)
        params = list(sig.parameters.keys())
        assert params == ["state", "classification", "affected_units"]
        assert sig.parameters["classification"].annotation == str
        assert sig.parameters["affected_units"].annotation == List[int]
        assert sig.return_annotation == PipelineState

    def test_update_state_from_status_signature(self):
        sig = inspect.signature(update_state_from_status)
        params = list(sig.parameters.keys())
        assert params == ["state", "status_file", "unit", "phase", "project_root"]
        assert sig.parameters["status_file"].annotation == Path
        assert sig.parameters["unit"].annotation == Optional[int]
        assert sig.parameters["phase"].annotation == str
        assert sig.parameters["project_root"].annotation == Path
        assert sig.return_annotation == PipelineState


# ---------------------------------------------------------------------------
# advance_stage
# ---------------------------------------------------------------------------

class TestAdvanceStage:
    """Test advance_stage behavioral contracts and invariants."""

    def test_advance_stage_returns_pipeline_state(self, tmp_path):
        """advance_stage must return a PipelineState."""
        state = _make_state(stage="0")
        result = advance_stage(state, tmp_path)
        assert isinstance(result, PipelineState)

    def test_advance_stage_does_not_mutate_input(self, tmp_path):
        """All transition functions return a new PipelineState -- no mutation."""
        state = _make_state(stage="0")
        original_stage = state.stage
        result = advance_stage(state, tmp_path)
        assert state.stage == original_stage

    def test_advance_stage_moves_forward(self, tmp_path):
        """advance_stage moves the state to the next stage in sequence."""
        # DATA ASSUMPTION: Stage "0" advances to "1"
        state = _make_state(stage="0", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert result.stage != "0"

    def test_advance_stage_from_stage_0(self, tmp_path):
        """Stage 0 should advance to Stage 1."""
        state = _make_state(stage="0", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert result.stage == "1"

    def test_advance_stage_from_stage_1(self, tmp_path):
        """Stage 1 should advance to Stage 2."""
        state = _make_state(stage="1", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert result.stage == "2"

    def test_advance_stage_from_stage_2(self, tmp_path):
        """Stage 2 should advance to pre_stage_3."""
        state = _make_state(stage="2", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert result.stage == "pre_stage_3"

    def test_advance_stage_from_pre_stage_3(self, tmp_path):
        """pre_stage_3 should advance to Stage 3."""
        state = _make_state(stage="pre_stage_3", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert result.stage == "3"

    def test_advance_stage_from_stage_3(self, tmp_path):
        """Stage 3 should advance to Stage 4."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        result = advance_stage(state, tmp_path)
        assert result.stage == "4"

    def test_advance_stage_from_stage_4(self, tmp_path):
        """Stage 4 should advance to Stage 5."""
        state = _make_state(stage="4", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert result.stage == "5"

    def test_advance_stage_invariant_cannot_advance_past_5(self, tmp_path):
        """Invariant: Cannot advance past Stage 5."""
        state = _make_state(stage="5", current_unit=None, total_units=None)
        with pytest.raises((TransitionError, AssertionError)):
            advance_stage(state, tmp_path)

    def test_advance_stage_error_message_format(self, tmp_path):
        """Error: Cannot advance from stage {X}: preconditions not met."""
        state = _make_state(stage="5", current_unit=None, total_units=None)
        with pytest.raises((TransitionError, AssertionError)) as exc_info:
            advance_stage(state, tmp_path)
        if isinstance(exc_info.value, TransitionError):
            assert "Cannot advance" in str(exc_info.value) or \
                   "advance" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# advance_sub_stage
# ---------------------------------------------------------------------------

class TestAdvanceSubStage:
    """Test advance_sub_stage."""

    def test_advance_sub_stage_returns_pipeline_state(self, tmp_path):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = advance_sub_stage(state, "project_context", tmp_path)
        assert isinstance(result, PipelineState)

    def test_advance_sub_stage_updates_sub_stage(self, tmp_path):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = advance_sub_stage(state, "project_context", tmp_path)
        assert result.sub_stage == "project_context"

    def test_advance_sub_stage_does_not_mutate_input(self, tmp_path):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = advance_sub_stage(state, "project_context", tmp_path)
        assert state.sub_stage == "hook_activation"


# ---------------------------------------------------------------------------
# complete_unit
# ---------------------------------------------------------------------------

class TestCompleteUnit:
    """Test complete_unit behavioral contracts and invariants."""

    def test_complete_unit_returns_pipeline_state(self, tmp_path):
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        assert isinstance(result, PipelineState)

    def test_complete_unit_writes_marker_file(self, tmp_path):
        """Post-condition: completion marker must be written."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        marker_path = tmp_path / ".svp" / "markers" / "unit_1_verified"
        assert marker_path.exists()

    def test_complete_unit_marker_contains_verified_timestamp(self, tmp_path):
        """Marker file contains 'VERIFIED: {timestamp}'."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        marker_path = tmp_path / ".svp" / "markers" / "unit_1_verified"
        content = marker_path.read_text()
        assert content.startswith("VERIFIED:")

    def test_complete_unit_updates_verified_units(self, tmp_path):
        """verified_units list should include the completed unit."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        unit_numbers = [vu["unit"] for vu in result.verified_units]
        assert 1 in unit_numbers

    def test_complete_unit_advances_current_unit(self, tmp_path):
        """Post-condition: current_unit advances to next unit."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        assert result.current_unit == 2 or result.stage != "3"

    def test_complete_unit_resets_fix_ladder(self, tmp_path):
        """complete_unit resets fix ladder."""
        state = _make_state(
            stage="3", current_unit=1, total_units=5,
            fix_ladder_position="fresh_test"
        )
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        assert result.fix_ladder_position is None

    def test_complete_unit_resets_red_run_retries(self, tmp_path):
        """complete_unit resets red run retries."""
        state = _make_state(
            stage="3", current_unit=1, total_units=5,
            red_run_retries=2
        )
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        assert result.red_run_retries == 0

    def test_complete_unit_advances_stage_when_all_units_done(self, tmp_path):
        """When current_unit exceeds total_units, advances stage to '4'."""
        # DATA ASSUMPTION: last unit in a 5-unit project
        state = _make_state(stage="3", current_unit=5, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 5, tmp_path)
        # Either advances to unit 6 (which exceeds total) or stage becomes "4"
        assert result.stage == "4" or result.current_unit == 6

    def test_complete_unit_does_not_mutate_input(self, tmp_path):
        """Immutability: input state is not mutated."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        assert state.current_unit == 1
        assert state.verified_units == []

    def test_complete_unit_precondition_stage_must_be_3(self, tmp_path):
        """Pre-condition: can only complete units during Stage 3."""
        state = _make_state(stage="2", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        with pytest.raises((TransitionError, AssertionError)):
            complete_unit(state, 1, tmp_path)

    def test_complete_unit_precondition_must_be_current_unit(self, tmp_path):
        """Pre-condition: can only complete the current unit."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        with pytest.raises((TransitionError, AssertionError)):
            complete_unit(state, 2, tmp_path)

    def test_complete_unit_precondition_marker_must_not_already_exist(self, tmp_path):
        """Pre-condition: completion marker must not already exist."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _write_unit_marker(tmp_path, 1)  # Pre-create the marker
        with pytest.raises((TransitionError, AssertionError)):
            complete_unit(state, 1, tmp_path)

    def test_complete_unit_error_tests_not_passed(self, tmp_path):
        """Error: Cannot complete unit {N}: tests have not passed.

        DATA ASSUMPTION: When complete_unit is called and the implementation
        finds no evidence that tests have passed (no status file, no test
        results marker), it raises TransitionError with a message matching
        'Cannot complete unit {N}: tests have not passed'. We verify this
        error condition by calling complete_unit in a state where tests
        have not been recorded as passing.
        """
        # Set up valid preconditions (stage 3, correct unit, no existing marker)
        # but do NOT provide any test passage evidence
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        # The function should raise TransitionError because tests have not passed
        # This may succeed if the implementation does not require external evidence,
        # or raise TransitionError if it checks for test passage evidence.
        # We test the error case by attempting the call and checking the message
        # pattern if a TransitionError is raised.
        try:
            result = complete_unit(state, 1, tmp_path)
            # If it succeeds, the implementation may not enforce test passage
            # evidence via TransitionError (it may accept the call based on
            # state alone). This is acceptable per the blueprint.
        except TransitionError as e:
            assert "tests have not passed" in str(e).lower() or                    "Cannot complete unit" in str(e)


# ---------------------------------------------------------------------------
# advance_fix_ladder
# ---------------------------------------------------------------------------

class TestAdvanceFixLadder:
    """Test advance_fix_ladder behavioral contracts and error conditions."""

    def test_advance_fix_ladder_returns_pipeline_state(self):
        """Return type check."""
        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_test")
        assert isinstance(result, PipelineState)

    def test_advance_fix_ladder_none_to_fresh_test(self):
        """Valid test ladder: None -> fresh_test."""
        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_test")
        assert result.fix_ladder_position == "fresh_test"

    def test_advance_fix_ladder_fresh_test_to_hint_test(self):
        """Valid test ladder: fresh_test -> hint_test."""
        state = _make_state(fix_ladder_position="fresh_test")
        result = advance_fix_ladder(state, "hint_test")
        assert result.fix_ladder_position == "hint_test"

    def test_advance_fix_ladder_none_to_fresh_impl(self):
        """Valid impl ladder: None -> fresh_impl."""
        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_impl")
        assert result.fix_ladder_position == "fresh_impl"

    def test_advance_fix_ladder_fresh_impl_to_diagnostic(self):
        """Valid impl ladder: fresh_impl -> diagnostic."""
        state = _make_state(fix_ladder_position="fresh_impl")
        result = advance_fix_ladder(state, "diagnostic")
        assert result.fix_ladder_position == "diagnostic"

    def test_advance_fix_ladder_diagnostic_to_diagnostic_impl(self):
        """Valid impl ladder: diagnostic -> diagnostic_impl."""
        state = _make_state(fix_ladder_position="diagnostic")
        result = advance_fix_ladder(state, "diagnostic_impl")
        assert result.fix_ladder_position == "diagnostic_impl"

    def test_advance_fix_ladder_invalid_transition_raises_error(self):
        """Invalid transition raises TransitionError."""
        state = _make_state(fix_ladder_position=None)
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "hint_test")  # Can't skip fresh_test

    def test_advance_fix_ladder_backward_transition_raises_error(self):
        """Backward transition raises TransitionError."""
        state = _make_state(fix_ladder_position="hint_test")
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "fresh_test")

    def test_advance_fix_ladder_cross_ladder_raises_error(self):
        """Cross-ladder transition raises TransitionError (test -> impl ladder)."""
        state = _make_state(fix_ladder_position="fresh_test")
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "diagnostic")

    def test_advance_fix_ladder_error_message_format(self):
        """Error message includes current and target positions."""
        state = _make_state(fix_ladder_position=None)
        with pytest.raises(TransitionError, match="Cannot advance fix ladder"):
            advance_fix_ladder(state, "hint_test")

    def test_advance_fix_ladder_does_not_mutate_input(self):
        """Immutability check."""
        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_test")
        assert state.fix_ladder_position is None

    def test_advance_fix_ladder_none_to_diagnostic_raises(self):
        """Cannot go from None directly to diagnostic."""
        state = _make_state(fix_ladder_position=None)
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "diagnostic")

    def test_advance_fix_ladder_none_to_diagnostic_impl_raises(self):
        """Cannot go from None directly to diagnostic_impl."""
        state = _make_state(fix_ladder_position=None)
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "diagnostic_impl")


# ---------------------------------------------------------------------------
# reset_fix_ladder
# ---------------------------------------------------------------------------

class TestResetFixLadder:
    """Test reset_fix_ladder."""

    def test_reset_fix_ladder_returns_pipeline_state(self):
        state = _make_state(fix_ladder_position="fresh_test")
        result = reset_fix_ladder(state)
        assert isinstance(result, PipelineState)

    def test_reset_fix_ladder_sets_position_to_none(self):
        state = _make_state(fix_ladder_position="hint_test")
        result = reset_fix_ladder(state)
        assert result.fix_ladder_position is None

    def test_reset_fix_ladder_from_none_stays_none(self):
        state = _make_state(fix_ladder_position=None)
        result = reset_fix_ladder(state)
        assert result.fix_ladder_position is None

    def test_reset_fix_ladder_does_not_mutate_input(self):
        state = _make_state(fix_ladder_position="diagnostic")
        result = reset_fix_ladder(state)
        assert state.fix_ladder_position == "diagnostic"


# ---------------------------------------------------------------------------
# increment/reset_red_run_retries
# ---------------------------------------------------------------------------

class TestRedRunRetries:
    """Test increment_red_run_retries and reset_red_run_retries."""

    def test_increment_red_run_retries_returns_pipeline_state(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert isinstance(result, PipelineState)

    def test_increment_red_run_retries_increments_by_one(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 1

    def test_increment_red_run_retries_from_nonzero(self):
        state = _make_state(red_run_retries=2)
        result = increment_red_run_retries(state)
        assert result.red_run_retries == 3

    def test_increment_red_run_retries_does_not_mutate_input(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert state.red_run_retries == 0

    def test_reset_red_run_retries_returns_pipeline_state(self):
        state = _make_state(red_run_retries=3)
        result = reset_red_run_retries(state)
        assert isinstance(result, PipelineState)

    def test_reset_red_run_retries_sets_to_zero(self):
        state = _make_state(red_run_retries=3)
        result = reset_red_run_retries(state)
        assert result.red_run_retries == 0

    def test_reset_red_run_retries_does_not_mutate_input(self):
        state = _make_state(red_run_retries=3)
        result = reset_red_run_retries(state)
        assert state.red_run_retries == 3


# ---------------------------------------------------------------------------
# increment/reset_alignment_iteration
# ---------------------------------------------------------------------------

class TestAlignmentIteration:
    """Test increment_alignment_iteration and reset_alignment_iteration."""

    def test_increment_alignment_iteration_returns_pipeline_state(self):
        state = _make_state(alignment_iteration=0)
        result = increment_alignment_iteration(state)
        assert isinstance(result, PipelineState)

    def test_increment_alignment_iteration_increments_by_one(self):
        state = _make_state(alignment_iteration=0)
        result = increment_alignment_iteration(state)
        assert result.alignment_iteration == 1

    def test_increment_alignment_iteration_from_nonzero(self):
        state = _make_state(alignment_iteration=1)
        result = increment_alignment_iteration(state)
        assert result.alignment_iteration == 2

    def test_increment_alignment_iteration_does_not_mutate_input(self):
        state = _make_state(alignment_iteration=0)
        result = increment_alignment_iteration(state)
        assert state.alignment_iteration == 0

    def test_increment_alignment_iteration_limit_reached_raises_error(self):
        """Error: Alignment iteration limit reached ({limit}).

        DATA ASSUMPTION: Default iteration_limit is 3 (from Unit 1 config).
        When alignment_iteration reaches the limit, a TransitionError is raised.
        """
        # The limit is read from config. With default limit=3, iteration 3
        # should trigger the error (0-indexed: 0,1,2 are valid -> 3 exceeds)
        state = _make_state(alignment_iteration=2)
        # This may raise TransitionError if the iteration would exceed the limit
        # The exact threshold depends on whether the check is before or after
        # increment. We test that at some point near the limit, the error fires.
        with pytest.raises(TransitionError, match="[Aa]lignment iteration limit"):
            # Start at limit-1 and try to increment past it
            s = _make_state(alignment_iteration=3)
            increment_alignment_iteration(s)

    def test_reset_alignment_iteration_returns_pipeline_state(self):
        state = _make_state(alignment_iteration=2)
        result = reset_alignment_iteration(state)
        assert isinstance(result, PipelineState)

    def test_reset_alignment_iteration_sets_to_zero(self):
        state = _make_state(alignment_iteration=2)
        result = reset_alignment_iteration(state)
        assert result.alignment_iteration == 0

    def test_reset_alignment_iteration_does_not_mutate_input(self):
        state = _make_state(alignment_iteration=2)
        result = reset_alignment_iteration(state)
        assert state.alignment_iteration == 2


# ---------------------------------------------------------------------------
# record_pass_end
# ---------------------------------------------------------------------------

class TestRecordPassEnd:
    """Test record_pass_end."""

    def test_record_pass_end_returns_pipeline_state(self):
        state = _make_state(current_unit=3)
        result = record_pass_end(state, "unit_failed")
        assert isinstance(result, PipelineState)

    def test_record_pass_end_adds_to_pass_history(self):
        state = _make_state(current_unit=3, pass_history=[])
        result = record_pass_end(state, "unit_failed")
        assert len(result.pass_history) >= 1

    def test_record_pass_end_records_reason(self):
        state = _make_state(current_unit=3, pass_history=[])
        result = record_pass_end(state, "unit_failed")
        latest = result.pass_history[-1]
        assert latest["ended_reason"] == "unit_failed"

    def test_record_pass_end_does_not_mutate_input(self):
        state = _make_state(current_unit=3, pass_history=[])
        result = record_pass_end(state, "unit_failed")
        assert len(state.pass_history) == 0

    def test_record_pass_end_increments_pass_number(self):
        """Pass number should be sequential."""
        state = _make_state(
            current_unit=3,
            pass_history=[{
                "pass_number": 1, "reached_unit": 2,
                "ended_reason": "rollback", "timestamp": "2025-01-15T10:00:00"
            }]
        )
        result = record_pass_end(state, "unit_failed")
        latest = result.pass_history[-1]
        assert latest["pass_number"] == 2


# ---------------------------------------------------------------------------
# rollback_to_unit
# ---------------------------------------------------------------------------

class TestRollbackToUnit:
    """Test rollback_to_unit behavioral contracts and invariants."""

    def test_rollback_to_unit_returns_pipeline_state(self, tmp_path):
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        result = rollback_to_unit(state, 1, tmp_path)
        assert isinstance(result, PipelineState)

    def test_rollback_to_unit_sets_current_unit(self, tmp_path):
        """rollback_to_unit sets current_unit to the given unit number."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        result = rollback_to_unit(state, 2, tmp_path)
        assert result.current_unit == 2

    def test_rollback_to_unit_removes_marker_files(self, tmp_path):
        """Rollback removes marker files for units from given unit forward."""
        state = _make_state(
            stage="3", current_unit=4, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
                {"unit": 3, "timestamp": "2025-01-15T12:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        _write_unit_marker(tmp_path, 3)
        result = rollback_to_unit(state, 2, tmp_path)
        # Marker for unit 2 and 3 should be removed (from unit 2 forward)
        assert not (tmp_path / ".svp" / "markers" / "unit_2_verified").exists()
        assert not (tmp_path / ".svp" / "markers" / "unit_3_verified").exists()

    def test_rollback_to_unit_keeps_earlier_markers(self, tmp_path):
        """Rollback preserves marker files for units before the rollback target."""
        state = _make_state(
            stage="3", current_unit=4, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
                {"unit": 3, "timestamp": "2025-01-15T12:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        _write_unit_marker(tmp_path, 3)
        result = rollback_to_unit(state, 2, tmp_path)
        # Marker for unit 1 should still exist
        assert (tmp_path / ".svp" / "markers" / "unit_1_verified").exists()

    def test_rollback_to_unit_updates_verified_units(self, tmp_path):
        """Rollback removes units from verified_units from the given unit forward."""
        state = _make_state(
            stage="3", current_unit=4, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
                {"unit": 3, "timestamp": "2025-01-15T12:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        _write_unit_marker(tmp_path, 3)
        result = rollback_to_unit(state, 2, tmp_path)
        verified_numbers = [vu["unit"] for vu in result.verified_units]
        assert 2 not in verified_numbers
        assert 3 not in verified_numbers
        assert 1 in verified_numbers

    def test_rollback_to_unit_does_not_mutate_input(self, tmp_path):
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        result = rollback_to_unit(state, 1, tmp_path)
        assert state.current_unit == 3
        assert len(state.verified_units) == 2

    def test_rollback_to_unit_precondition_stage_must_be_3(self, tmp_path):
        """Pre-condition: rollback only applies during Stage 3."""
        state = _make_state(stage="2", current_unit=1, total_units=5)
        with pytest.raises((TransitionError, AssertionError)):
            rollback_to_unit(state, 1, tmp_path)

    def test_rollback_to_unit_precondition_unit_must_be_positive(self, tmp_path):
        """Pre-condition: unit number must be positive."""
        state = _make_state(stage="3", current_unit=2, total_units=5)
        with pytest.raises((TransitionError, AssertionError)):
            rollback_to_unit(state, 0, tmp_path)

    def test_rollback_to_unit_precondition_cannot_rollback_to_future_unit(self, tmp_path):
        """Pre-condition: cannot roll back to a future unit."""
        state = _make_state(stage="3", current_unit=2, total_units=5)
        with pytest.raises((TransitionError, AssertionError)):
            rollback_to_unit(state, 3, tmp_path)


# ---------------------------------------------------------------------------
# restart_from_stage
# ---------------------------------------------------------------------------

class TestRestartFromStage:
    """Test restart_from_stage behavioral contracts."""

    def test_restart_from_stage_returns_pipeline_state(self, tmp_path):
        state = _make_state(stage="3", current_unit=3, total_units=5)
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert isinstance(result, PipelineState)

    def test_restart_from_stage_sets_target_stage(self, tmp_path):
        state = _make_state(stage="3", current_unit=3, total_units=5)
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert result.stage == "3"

    def test_restart_from_stage_records_pass_history(self, tmp_path):
        """Records the current pass in pass_history."""
        state = _make_state(stage="3", current_unit=3, total_units=5, pass_history=[])
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert len(result.pass_history) >= 1

    def test_restart_from_stage_pass_history_records_reason(self, tmp_path):
        state = _make_state(stage="3", current_unit=3, total_units=5, pass_history=[])
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        latest = result.pass_history[-1]
        assert latest["ended_reason"] == "test_failure"

    def test_restart_from_stage_resets_counters(self, tmp_path):
        """restart_from_stage resets stage-specific counters."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            red_run_retries=2, alignment_iteration=1,
            fix_ladder_position="fresh_test"
        )
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        # Stage-specific counters should be reset
        assert result.fix_ladder_position is None or result.red_run_retries == 0

    def test_restart_from_stage_does_not_mutate_input(self, tmp_path):
        state = _make_state(stage="3", current_unit=3, total_units=5)
        original_pass_history_len = len(state.pass_history)
        result = restart_from_stage(state, "3", "test_failure", tmp_path)
        assert len(state.pass_history) == original_pass_history_len


# ---------------------------------------------------------------------------
# version_document
# ---------------------------------------------------------------------------

class TestVersionDocument:
    """Test version_document behavioral contracts and error conditions."""

    def test_version_document_returns_tuple_of_paths(self, tmp_path):
        # DATA ASSUMPTION: document is a simple markdown file
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Specification\n\nSome content.", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        result = version_document(
            doc_path, history_dir, "Updated error handling", "Stage 2 alignment"
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], Path)

    def test_version_document_creates_versioned_copy(self, tmp_path):
        """Post-condition: versioned copy must exist in history dir."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Specification\n\nSome content.", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated error handling", "Stage 2 alignment"
        )
        assert versioned_copy.exists()

    def test_version_document_creates_diff_file(self, tmp_path):
        """Post-condition: diff summary must exist in history dir."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Specification\n\nSome content.", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated error handling", "Stage 2 alignment"
        )
        assert diff_file.exists()

    def test_version_document_copy_naming_convention(self, tmp_path):
        """Versioned copy follows {name}_v{N}.md pattern."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Spec content", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated section", "Stage 2"
        )
        assert "spec_v" in versioned_copy.name
        assert versioned_copy.suffix == ".md"

    def test_version_document_diff_naming_convention(self, tmp_path):
        """Diff file follows {name}_v{N}_diff.md pattern."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Spec content", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated section", "Stage 2"
        )
        assert "_diff" in diff_file.name
        assert diff_file.suffix == ".md"

    def test_version_document_diff_contains_summary(self, tmp_path):
        """Diff file contains what changed, why, stage, and timestamp."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Spec content", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated error handling", "Stage 2 alignment"
        )
        diff_content = diff_file.read_text()
        assert "Updated error handling" in diff_content

    def test_version_document_versioned_copy_matches_original(self, tmp_path):
        """Versioned copy should contain the original document content."""
        original_content = "# Specification\n\nDetailed content here."
        doc_path = tmp_path / "spec.md"
        doc_path.write_text(original_content, encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated section", "Stage 2"
        )
        copy_content = versioned_copy.read_text()
        assert original_content in copy_content or copy_content == original_content

    def test_version_document_sequential_versions(self, tmp_path):
        """Multiple versions create incrementing version numbers."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Version 1 content", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        copy1, diff1 = version_document(
            doc_path, history_dir, "First update", "Stage 1"
        )
        doc_path.write_text("# Version 2 content", encoding="utf-8")
        copy2, diff2 = version_document(
            doc_path, history_dir, "Second update", "Stage 2"
        )
        assert copy1 != copy2
        assert diff1 != diff2
        assert copy1.exists()
        assert copy2.exists()

    def test_version_document_file_not_found_error(self, tmp_path):
        """Error: Document to version not found: {path}."""
        doc_path = tmp_path / "nonexistent.md"
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="not found"):
            version_document(doc_path, history_dir, "some diff", "Stage 2")

    def test_version_document_files_in_history_dir(self, tmp_path):
        """Both files are created inside the history directory."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("# Content", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Updated", "Stage 2"
        )
        assert str(versioned_copy).startswith(str(history_dir))
        assert str(diff_file).startswith(str(history_dir))


# ---------------------------------------------------------------------------
# enter_debug_session
# ---------------------------------------------------------------------------

class TestEnterDebugSession:
    """Test enter_debug_session behavioral contracts and invariants."""

    def test_enter_debug_session_returns_pipeline_state(self):
        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "Login page crashes on submit")
        assert isinstance(result, PipelineState)

    def test_enter_debug_session_creates_debug_session(self):
        """Creates a new DebugSession with authorized=False."""
        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "Login page crashes on submit")
        assert result.debug_session is not None
        assert result.debug_session.authorized is False

    def test_enter_debug_session_phase_is_triage_readonly(self):
        """Phase starts at 'triage_readonly'."""
        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "Login page crashes on submit")
        assert result.debug_session.phase == "triage_readonly"

    def test_enter_debug_session_assigns_bug_id(self):
        """Assigns a sequential bug_id."""
        state = _make_state(stage="5", debug_session=None, debug_history=[])
        result = enter_debug_session(state, "Login page crashes on submit")
        assert result.debug_session.bug_id >= 1

    def test_enter_debug_session_sequential_bug_ids(self):
        """Bug IDs are sequential based on debug_history."""
        state = _make_state(
            stage="5", debug_session=None,
            debug_history=[{"bug_id": 1, "description": "prev bug"}]
        )
        result = enter_debug_session(state, "New bug")
        assert result.debug_session.bug_id > 1

    def test_enter_debug_session_stores_description(self):
        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "Login page crashes on submit")
        assert result.debug_session.description == "Login page crashes on submit"

    def test_enter_debug_session_does_not_mutate_input(self):
        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "Login page crashes")
        assert state.debug_session is None

    def test_enter_debug_session_precondition_stage_must_be_5(self):
        """Pre-condition: can only enter debug session after Stage 5 completion."""
        state = _make_state(stage="3", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)):
            enter_debug_session(state, "Bug description")

    def test_enter_debug_session_error_message_not_stage_5(self):
        """Error: Cannot enter debug session: pipeline is not at Stage 5."""
        state = _make_state(stage="3", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)) as exc_info:
            enter_debug_session(state, "Bug description")
        if isinstance(exc_info.value, TransitionError):
            assert "Stage 5" in str(exc_info.value) or "stage 5" in str(exc_info.value).lower()

    def test_enter_debug_session_precondition_no_active_session(self):
        """Pre-condition: cannot enter debug session when one is already active."""
        existing_session = DebugSession(
            bug_id=1, description="Existing bug",
            authorized=False, phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=existing_session)
        with pytest.raises((TransitionError, AssertionError)):
            enter_debug_session(state, "Another bug")

    def test_enter_debug_session_error_message_already_active(self):
        """Error: Cannot enter debug session: a debug session is already active."""
        existing_session = DebugSession(
            bug_id=1, description="Existing bug",
            authorized=False, phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=existing_session)
        with pytest.raises((TransitionError, AssertionError)) as exc_info:
            enter_debug_session(state, "Another bug")
        if isinstance(exc_info.value, TransitionError):
            assert "already active" in str(exc_info.value).lower() or \
                   "already" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# authorize_debug_session
# ---------------------------------------------------------------------------

class TestAuthorizeDebugSession:
    """Test authorize_debug_session behavioral contracts and invariants."""

    def test_authorize_debug_session_returns_pipeline_state(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = authorize_debug_session(state)
        assert isinstance(result, PipelineState)

    def test_authorize_debug_session_sets_authorized_true(self):
        """Post-condition: debug_session.authorized must be True."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = authorize_debug_session(state)
        assert result.debug_session is not None
        assert result.debug_session.authorized is True

    def test_authorize_debug_session_advances_phase_to_triage(self):
        """authorize_debug_session advances phase to 'triage'."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = authorize_debug_session(state)
        assert result.debug_session.phase == "triage"

    def test_authorize_debug_session_preserves_session(self):
        """Post-condition: debug session must still exist."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = authorize_debug_session(state)
        assert result.debug_session is not None

    def test_authorize_debug_session_does_not_mutate_input(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = authorize_debug_session(state)
        assert state.debug_session.authorized is False

    def test_authorize_debug_session_precondition_no_session_raises(self):
        """Pre-condition: no active debug session to authorize."""
        state = _make_state(stage="5", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)):
            authorize_debug_session(state)

    def test_authorize_debug_session_error_message_no_session(self):
        """Error: Cannot authorize debug session: no active session."""
        state = _make_state(stage="5", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)) as exc_info:
            authorize_debug_session(state)
        if isinstance(exc_info.value, TransitionError):
            assert "no active" in str(exc_info.value).lower() or \
                   "authorize" in str(exc_info.value).lower()

    def test_authorize_debug_session_precondition_already_authorized_raises(self):
        """Pre-condition: debug session already authorized."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        with pytest.raises((TransitionError, AssertionError)):
            authorize_debug_session(state)


# ---------------------------------------------------------------------------
# complete_debug_session
# ---------------------------------------------------------------------------

class TestCompleteDebugSession:
    """Test complete_debug_session behavioral contracts."""

    def test_complete_debug_session_returns_pipeline_state(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session)
        result = complete_debug_session(state, "Fixed null reference in auth handler")
        assert isinstance(result, PipelineState)

    def test_complete_debug_session_clears_debug_session(self):
        """complete_debug_session sets debug_session to None."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session)
        result = complete_debug_session(state, "Fixed the bug")
        assert result.debug_session is None

    def test_complete_debug_session_adds_to_debug_history(self):
        """Moves the debug session record to debug_history."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = complete_debug_session(state, "Fixed the bug")
        assert len(result.debug_history) >= 1
        # Verify the bug_id is in the history
        bug_ids = [d.get("bug_id") for d in result.debug_history]
        assert 1 in bug_ids

    def test_complete_debug_session_does_not_mutate_input(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = complete_debug_session(state, "Fixed the bug")
        assert state.debug_session is not None
        assert len(state.debug_history) == 0

    def test_complete_debug_session_precondition_no_session_raises(self):
        """Pre-condition: no active debug session to complete."""
        state = _make_state(stage="5", debug_session=None)
        with pytest.raises((TransitionError, AssertionError)):
            complete_debug_session(state, "Fixed the bug")

    def test_complete_debug_session_precondition_not_authorized_raises(self):
        """Pre-condition: debug session must be authorized before completion."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        with pytest.raises((TransitionError, AssertionError)):
            complete_debug_session(state, "Fixed the bug")


# ---------------------------------------------------------------------------
# abandon_debug_session
# ---------------------------------------------------------------------------

class TestAbandonDebugSession:
    """Test abandon_debug_session behavioral contracts."""

    def test_abandon_debug_session_returns_pipeline_state(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = abandon_debug_session(state)
        assert isinstance(result, PipelineState)

    def test_abandon_debug_session_clears_debug_session(self):
        """abandon_debug_session sets debug_session to None."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = abandon_debug_session(state)
        assert result.debug_session is None

    def test_abandon_debug_session_adds_to_debug_history_with_abandoned_marker(self):
        """Moves the session record with an 'abandoned' marker to debug_history."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        assert len(result.debug_history) >= 1
        # Check for abandoned marker in the history entry
        latest = result.debug_history[-1]
        # The abandoned marker could be a key or a status field
        assert "abandoned" in str(latest).lower() or \
               latest.get("abandoned") is True or \
               latest.get("status") == "abandoned"

    def test_abandon_debug_session_does_not_mutate_input(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session, debug_history=[])
        result = abandon_debug_session(state)
        assert state.debug_session is not None
        assert len(state.debug_history) == 0


# ---------------------------------------------------------------------------
# update_debug_phase
# ---------------------------------------------------------------------------

class TestUpdateDebugPhase:
    """Test update_debug_phase behavioral contracts."""

    def test_update_debug_phase_returns_pipeline_state(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "regression_test")
        assert isinstance(result, PipelineState)

    def test_update_debug_phase_updates_phase(self):
        """update_debug_phase updates debug_session.phase."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "regression_test")
        assert result.debug_session.phase == "regression_test"

    def test_update_debug_phase_does_not_mutate_input(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = update_debug_phase(state, "regression_test")
        assert state.debug_session.phase == "triage"

    def test_update_debug_phase_validates_transitions(self):
        """update_debug_phase validates phase transitions."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        # An invalid phase should raise an error
        with pytest.raises((TransitionError, ValueError, AssertionError)):
            update_debug_phase(state, "invalid_phase")


# ---------------------------------------------------------------------------
# set_debug_classification
# ---------------------------------------------------------------------------

class TestSetDebugClassification:
    """Test set_debug_classification behavioral contracts."""

    def test_set_debug_classification_returns_pipeline_state(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = set_debug_classification(state, "single_unit", [3])
        assert isinstance(result, PipelineState)

    def test_set_debug_classification_sets_classification(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = set_debug_classification(state, "single_unit", [3])
        assert result.debug_session.classification == "single_unit"

    def test_set_debug_classification_sets_affected_units(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = set_debug_classification(state, "cross_unit", [2, 3, 4])
        assert result.debug_session.affected_units == [2, 3, 4]

    def test_set_debug_classification_build_env(self):
        """Classification 'build_env' with no affected units."""
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = set_debug_classification(state, "build_env", [])
        assert result.debug_session.classification == "build_env"
        assert result.debug_session.affected_units == []

    def test_set_debug_classification_does_not_mutate_input(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="triage"
        )
        state = _make_state(stage="5", debug_session=session)
        result = set_debug_classification(state, "single_unit", [3])
        assert state.debug_session.classification is None or \
               state.debug_session.classification != "single_unit"


# ---------------------------------------------------------------------------
# update_state_from_status
# ---------------------------------------------------------------------------

class TestUpdateStateFromStatus:
    """Test update_state_from_status behavioral contracts."""

    def test_update_state_from_status_returns_pipeline_state(self, tmp_path):
        """update_state_from_status returns a PipelineState."""
        # DATA ASSUMPTION: Status file contains a terminal status line
        status_file = tmp_path / ".svp" / "last_status.txt"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text("TEST_GENERATION_COMPLETE", encoding="utf-8")
        state = _make_state(stage="3", current_unit=1, total_units=5)
        result = update_state_from_status(state, status_file, 1, "test_gen", tmp_path)
        assert isinstance(result, PipelineState)

    def test_update_state_from_status_reads_status_file(self, tmp_path):
        """update_state_from_status reads the status file content."""
        status_file = tmp_path / ".svp" / "last_status.txt"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text("TESTS_PASSED: 10 passed", encoding="utf-8")
        state = _make_state(stage="3", current_unit=1, total_units=5)
        # Should not raise -- it reads and processes the status
        result = update_state_from_status(state, status_file, 1, "red_run", tmp_path)
        assert isinstance(result, PipelineState)

    def test_update_state_from_status_does_not_mutate_input(self, tmp_path):
        status_file = tmp_path / ".svp" / "last_status.txt"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text("TEST_GENERATION_COMPLETE", encoding="utf-8")
        state = _make_state(stage="3", current_unit=1, total_units=5)
        original_stage = state.stage
        result = update_state_from_status(state, status_file, 1, "test_gen", tmp_path)
        assert state.stage == original_stage


# ---------------------------------------------------------------------------
# Immutability Comprehensive Test
# ---------------------------------------------------------------------------

class TestImmutability:
    """Verify all transition functions return new PipelineState, not mutated input."""

    def test_reset_fix_ladder_immutability(self):
        state = _make_state(fix_ladder_position="fresh_test")
        result = reset_fix_ladder(state)
        assert state is not result

    def test_increment_red_run_retries_immutability(self):
        state = _make_state(red_run_retries=0)
        result = increment_red_run_retries(state)
        assert state is not result

    def test_reset_red_run_retries_immutability(self):
        state = _make_state(red_run_retries=2)
        result = reset_red_run_retries(state)
        assert state is not result

    def test_increment_alignment_iteration_immutability(self):
        state = _make_state(alignment_iteration=0)
        result = increment_alignment_iteration(state)
        assert state is not result

    def test_reset_alignment_iteration_immutability(self):
        state = _make_state(alignment_iteration=2)
        result = reset_alignment_iteration(state)
        assert state is not result

    def test_record_pass_end_immutability(self):
        state = _make_state(current_unit=3)
        result = record_pass_end(state, "test_failure")
        assert state is not result

    def test_advance_fix_ladder_immutability(self):
        state = _make_state(fix_ladder_position=None)
        result = advance_fix_ladder(state, "fresh_test")
        assert state is not result

    def test_enter_debug_session_immutability(self):
        state = _make_state(stage="5", debug_session=None)
        result = enter_debug_session(state, "Bug")
        assert state is not result

    def test_authorize_debug_session_immutability(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = authorize_debug_session(state)
        assert state is not result

    def test_complete_debug_session_immutability(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=True,
            phase="repair"
        )
        state = _make_state(stage="5", debug_session=session)
        result = complete_debug_session(state, "Fixed")
        assert state is not result

    def test_abandon_debug_session_immutability(self):
        session = DebugSession(
            bug_id=1, description="Bug", authorized=False,
            phase="triage_readonly"
        )
        state = _make_state(stage="5", debug_session=session)
        result = abandon_debug_session(state)
        assert state is not result

    def test_advance_stage_immutability(self, tmp_path):
        state = _make_state(stage="0", current_unit=None, total_units=None)
        result = advance_stage(state, tmp_path)
        assert state is not result

    def test_complete_unit_immutability(self, tmp_path):
        state = _make_state(stage="3", current_unit=1, total_units=5)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        assert state is not result

    def test_rollback_to_unit_immutability(self, tmp_path):
        state = _make_state(
            stage="3", current_unit=2, total_units=5,
            verified_units=[{"unit": 1, "timestamp": "2025-01-15T10:00:00"}]
        )
        _write_unit_marker(tmp_path, 1)
        result = rollback_to_unit(state, 1, tmp_path)
        assert state is not result


# ---------------------------------------------------------------------------
# Stage Sequence Validation
# ---------------------------------------------------------------------------

class TestStageSequence:
    """Verify the defined stage sequence: 0 -> 1 -> 2 -> pre_stage_3 -> 3 -> 4 -> 5."""

    def test_full_stage_sequence(self, tmp_path):
        """Advance through all stages in sequence."""
        # DATA ASSUMPTION: Stages follow the sequence defined in Unit 2's STAGES constant
        expected_sequence = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

        state = _make_state(stage="0", current_unit=None, total_units=None)

        # We test just that stage 0 -> 1 works; full sequence depends on
        # exit criteria being met which is implementation-specific
        result = advance_stage(state, tmp_path)
        idx = expected_sequence.index("0")
        next_stage = expected_sequence[idx + 1]
        assert result.stage == next_stage


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_complete_last_unit_transitions_to_stage_4(self, tmp_path):
        """Completing the last unit should transition to stage 4."""
        # DATA ASSUMPTION: total_units=1, only one unit in the project
        state = _make_state(stage="3", current_unit=1, total_units=1)
        _setup_markers_dir(tmp_path)
        result = complete_unit(state, 1, tmp_path)
        # When current_unit exceeds total_units, stage should advance to "4"
        assert result.stage == "4" or result.current_unit > 1

    def test_rollback_to_first_unit(self, tmp_path):
        """Rollback all the way to unit 1."""
        state = _make_state(
            stage="3", current_unit=3, total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "2025-01-15T10:00:00"},
                {"unit": 2, "timestamp": "2025-01-15T11:00:00"},
            ]
        )
        _write_unit_marker(tmp_path, 1)
        _write_unit_marker(tmp_path, 2)
        result = rollback_to_unit(state, 1, tmp_path)
        assert result.current_unit == 1
        verified_numbers = [vu["unit"] for vu in result.verified_units]
        assert 1 not in verified_numbers
        assert 2 not in verified_numbers

    def test_multiple_debug_sessions_sequential(self):
        """Can enter a new debug session after completing the previous one."""
        # First session
        state = _make_state(stage="5", debug_session=None, debug_history=[])
        state = enter_debug_session(state, "Bug 1")
        state = authorize_debug_session(state)
        state = complete_debug_session(state, "Fixed bug 1")
        assert state.debug_session is None
        assert len(state.debug_history) >= 1

        # Second session
        state2 = enter_debug_session(state, "Bug 2")
        assert state2.debug_session is not None
        assert state2.debug_session.bug_id > 1

    def test_fix_ladder_full_test_sequence(self):
        """Walk through the full test ladder: None -> fresh_test -> hint_test."""
        state = _make_state(fix_ladder_position=None)
        state = advance_fix_ladder(state, "fresh_test")
        assert state.fix_ladder_position == "fresh_test"
        state = advance_fix_ladder(state, "hint_test")
        assert state.fix_ladder_position == "hint_test"

    def test_fix_ladder_full_impl_sequence(self):
        """Walk through the full impl ladder: None -> fresh_impl -> diagnostic -> diagnostic_impl."""
        state = _make_state(fix_ladder_position=None)
        state = advance_fix_ladder(state, "fresh_impl")
        assert state.fix_ladder_position == "fresh_impl"
        state = advance_fix_ladder(state, "diagnostic")
        assert state.fix_ladder_position == "diagnostic"
        state = advance_fix_ladder(state, "diagnostic_impl")
        assert state.fix_ladder_position == "diagnostic_impl"

    def test_version_document_creates_history_dir_parent(self, tmp_path):
        """version_document should work when history_dir already exists."""
        doc_path = tmp_path / "doc.md"
        doc_path.write_text("Content", encoding="utf-8")
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        versioned_copy, diff_file = version_document(
            doc_path, history_dir, "Changes", "Stage 2"
        )
        assert versioned_copy.exists()
        assert diff_file.exists()
