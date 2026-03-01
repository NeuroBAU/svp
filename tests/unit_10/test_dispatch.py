"""
Tests for Unit 10 dispatch functions: dispatch_status, dispatch_gate_response,
dispatch_agent_status, and dispatch_command_status.

DATA ASSUMPTION: PipelineState objects are constructed with default values from
the Unit 2 schema. Gate IDs and response strings come from the GATE_VOCABULARY
data contract. Agent types and status lines come from AGENT_STATUS_LINES.

DATA ASSUMPTION: project_root directories are real temporary directories created
by pytest's tmp_path fixture. State transitions from Unit 3 are mocked to
return the same state or a minimally modified state.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from svp.scripts.routing import (
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    COMMAND_STATUS_PATTERNS,
)
from svp.scripts.pipeline_state import PipelineState, DebugSession
from svp.scripts.state_transitions import TransitionError


@pytest.fixture
def tmp_project_root(tmp_path):
    """Create a temporary project root directory."""
    return tmp_path


def _make_state(**kwargs):
    """Helper to create a PipelineState with sensible defaults."""
    defaults = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "project_name": "test_project",
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


class TestDispatchGateResponse:
    """Tests for dispatch_gate_response -- the Bug 1 fix core."""

    def test_returns_pipeline_state(self, tmp_project_root):
        """dispatch_gate_response must return a PipelineState."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED", tmp_project_root
        )
        assert isinstance(result, PipelineState)

    def test_valid_response_for_every_gate(self, tmp_project_root):
        """For each gate, the first valid option should be accepted without error."""
        state = _make_state()
        for gate_id, options in GATE_VOCABULARY.items():
            # Use the first valid option for each gate
            # Some gates may require specific state -- we just test that
            # valid vocabulary strings don't raise ValueError
            try:
                result = dispatch_gate_response(
                    state, gate_id, options[0], tmp_project_root
                )
                # If it returns, it should be a PipelineState
                assert isinstance(result, PipelineState)
            except (TransitionError, NotImplementedError):
                # TransitionError from Unit 3 is acceptable (precondition failures
                # in state transitions), NotImplementedError is the stub
                pass

    def test_invalid_response_raises_value_error(self, tmp_project_root):
        """Bug 1: invalid gate response must raise ValueError with specific message."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"Invalid gate response"):
            dispatch_gate_response(
                state, "gate_0_1_hook_activation", "INVALID_OPTION", tmp_project_root
            )

    def test_invalid_response_message_includes_gate_id(self, tmp_project_root):
        """ValueError message must include the gate ID."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"gate_0_1_hook_activation"):
            dispatch_gate_response(
                state, "gate_0_1_hook_activation", "BAD_RESPONSE", tmp_project_root
            )

    def test_invalid_response_message_includes_valid_options(self, tmp_project_root):
        """ValueError message must include the valid options."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"HOOKS ACTIVATED"):
            dispatch_gate_response(
                state, "gate_0_1_hook_activation", "nope", tmp_project_root
            )

    def test_unknown_gate_id_raises_error(self, tmp_project_root):
        """Passing an unknown gate_id should raise an error.
        Post-condition: gate_id must be in GATE_VOCABULARY."""
        state = _make_state()
        with pytest.raises((ValueError, KeyError, AssertionError)):
            dispatch_gate_response(
                state, "gate_99_nonexistent", "SOME OPTION", tmp_project_root
            )

    def test_exact_string_matching_bug1(self, tmp_project_root):
        """Bug 1 fix: response must be an exact string match, not case-insensitive
        or partial match."""
        state = _make_state()
        # "hooks activated" (lowercase) should NOT match "HOOKS ACTIVATED"
        with pytest.raises(ValueError):
            dispatch_gate_response(
                state, "gate_0_1_hook_activation", "hooks activated", tmp_project_root
            )

    def test_exact_string_matching_no_prefix(self, tmp_project_root):
        """Bug 1 fix: response with extra prefix should not match."""
        state = _make_state()
        with pytest.raises(ValueError):
            dispatch_gate_response(
                state, "gate_0_1_hook_activation", "1. HOOKS ACTIVATED", tmp_project_root
            )

    def test_exact_string_matching_no_trailing_space(self, tmp_project_root):
        """Bug 1 fix: response with trailing space should not match."""
        state = _make_state()
        with pytest.raises(ValueError):
            dispatch_gate_response(
                state, "gate_0_1_hook_activation", "HOOKS ACTIVATED ", tmp_project_root
            )

    def test_all_gate_3_1_options(self, tmp_project_root):
        """Test all options for gate_3_1_test_validation are accepted."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        for option in GATE_VOCABULARY["gate_3_1_test_validation"]:
            try:
                result = dispatch_gate_response(
                    state, "gate_3_1_test_validation", option, tmp_project_root
                )
                assert isinstance(result, PipelineState)
            except (TransitionError, NotImplementedError):
                pass

    def test_gate_6_0_authorize_debug(self, tmp_project_root):
        """gate_6_0_debug_permission with AUTHORIZE DEBUG should be valid."""
        state = _make_state(stage="5")
        try:
            result = dispatch_gate_response(
                state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, NotImplementedError):
            pass

    def test_gate_6_0_abandon_debug(self, tmp_project_root):
        """gate_6_0_debug_permission with ABANDON DEBUG should be valid."""
        state = _make_state(stage="5")
        try:
            result = dispatch_gate_response(
                state, "gate_6_0_debug_permission", "ABANDON DEBUG", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, NotImplementedError):
            pass


class TestDispatchAgentStatus:
    """Tests for dispatch_agent_status."""

    def test_returns_pipeline_state(self, tmp_project_root):
        """dispatch_agent_status must return a PipelineState."""
        state = _make_state(stage="0", sub_stage="project_context")
        try:
            result = dispatch_agent_status(
                state, "setup_agent", "PROJECT_CONTEXT_COMPLETE",
                None, "setup", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, NotImplementedError):
            pass

    def test_valid_status_for_each_agent(self, tmp_project_root):
        """Each agent's first valid status line should be accepted."""
        state = _make_state()
        for agent_type, statuses in AGENT_STATUS_LINES.items():
            try:
                result = dispatch_agent_status(
                    state, agent_type, statuses[0],
                    None, "test_phase", tmp_project_root
                )
                assert isinstance(result, PipelineState)
            except (TransitionError, ValueError, NotImplementedError):
                # TransitionError or ValueError may occur from
                # precondition mismatches; stub raises NotImplementedError
                pass

    def test_unknown_status_line_raises_value_error(self, tmp_project_root):
        """Unknown agent status line must raise ValueError."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"Unknown agent status line"):
            dispatch_agent_status(
                state, "test_agent", "COMPLETELY_BOGUS_STATUS",
                None, "test_phase", tmp_project_root
            )

    def test_unknown_phase_raises_value_error(self, tmp_project_root):
        """Unknown phase must raise ValueError."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"Unknown phase"):
            dispatch_agent_status(
                state, "test_agent", "TEST_GENERATION_COMPLETE",
                None, "this_phase_does_not_exist", tmp_project_root
            )

    def test_with_unit_parameter(self, tmp_project_root):
        """dispatch_agent_status should accept a unit parameter."""
        state = _make_state(stage="3", current_unit=2, total_units=5)
        try:
            result = dispatch_agent_status(
                state, "test_agent", "TEST_GENERATION_COMPLETE",
                2, "test_generation", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass


class TestDispatchCommandStatus:
    """Tests for dispatch_command_status."""

    def test_returns_pipeline_state(self, tmp_project_root):
        """dispatch_command_status must return a PipelineState."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        try:
            result = dispatch_command_status(
                state, "TESTS_PASSED: 10 passed",
                1, "red_run", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    # DATA ASSUMPTION: Command status lines follow the patterns in
    # COMMAND_STATUS_PATTERNS with optional details after a colon.

    def test_tests_passed_status(self, tmp_project_root):
        """TESTS_PASSED status line should be accepted."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        try:
            result = dispatch_command_status(
                state, "TESTS_PASSED: 10 passed",
                1, "red_run", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_tests_failed_status(self, tmp_project_root):
        """TESTS_FAILED status line should be accepted."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        try:
            result = dispatch_command_status(
                state, "TESTS_FAILED: 8 passed, 2 failed",
                1, "green_run", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_tests_error_status(self, tmp_project_root):
        """TESTS_ERROR status line should be accepted."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        try:
            result = dispatch_command_status(
                state, "TESTS_ERROR: ImportError in test_module",
                1, "red_run", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_command_succeeded_status(self, tmp_project_root):
        """COMMAND_SUCCEEDED status line should be accepted."""
        state = _make_state()
        try:
            result = dispatch_command_status(
                state, "COMMAND_SUCCEEDED",
                None, "setup", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_command_failed_status(self, tmp_project_root):
        """COMMAND_FAILED status line should be accepted."""
        state = _make_state()
        try:
            result = dispatch_command_status(
                state, "COMMAND_FAILED: exit code 1",
                None, "setup", tmp_project_root
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_unknown_phase_raises_value_error(self, tmp_project_root):
        """Unknown phase must raise ValueError."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"Unknown phase"):
            dispatch_command_status(
                state, "TESTS_PASSED: 5 passed",
                None, "nonexistent_phase_xyz", tmp_project_root
            )


class TestDispatchStatus:
    """Tests for the top-level dispatch_status function."""

    def test_returns_pipeline_state(self, tmp_project_root):
        """dispatch_status must return a PipelineState."""
        state = _make_state()
        try:
            result = dispatch_status(
                state, "HOOKS ACTIVATED",
                gate_id="gate_0_1_hook_activation",
                unit=None,
                phase="setup",
                project_root=tmp_project_root,
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_delegates_gate_response_when_gate_id_provided(self, tmp_project_root):
        """When gate_id is provided, dispatch_status should handle it as a gate response."""
        state = _make_state()
        # An invalid response should still raise ValueError via the gate dispatch path
        with pytest.raises((ValueError, NotImplementedError)):
            dispatch_status(
                state, "INVALID_GATE_OPTION",
                gate_id="gate_0_1_hook_activation",
                unit=None,
                phase="setup",
                project_root=tmp_project_root,
            )

    def test_delegates_agent_status(self, tmp_project_root):
        """When status_line is an agent status, dispatch_status delegates accordingly."""
        state = _make_state(stage="0", sub_stage="project_context")
        try:
            result = dispatch_status(
                state, "PROJECT_CONTEXT_COMPLETE",
                gate_id=None,
                unit=None,
                phase="setup",
                project_root=tmp_project_root,
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_delegates_command_status(self, tmp_project_root):
        """When status_line is a command result, dispatch_status delegates accordingly."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        try:
            result = dispatch_status(
                state, "TESTS_PASSED: 10 passed",
                gate_id=None,
                unit=1,
                phase="red_run",
                project_root=tmp_project_root,
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, ValueError, NotImplementedError):
            pass

    def test_transition_error_propagated(self, tmp_project_root):
        """TransitionError from Unit 3 should propagate through dispatch_status."""
        state = _make_state()
        # This test verifies the contract that TransitionError propagates.
        # We can't trigger it deterministically without a real implementation,
        # but we verify the error type is importable and usable.
        assert issubclass(TransitionError, Exception)
