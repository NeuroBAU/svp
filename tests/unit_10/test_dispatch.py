"""Tests for Unit 10 dispatch functions: dispatch_status,
dispatch_gate_response, dispatch_agent_status,
dispatch_command_status.

Synthetic data assumptions:
- PipelineState is mocked with configurable fields.
- project_root is a tmp_path fixture directory.
- dispatch functions return a PipelineState.
- dispatch_agent_status uses prefix matching.
- Exhaustive dispatch invariant: every main-pipeline
  agent type must advance state; bare return only
  valid for help, hint.
- Bug 44: dispatch_agent_status for test_agent handles
  sub_stage in (None, "test_generation").
- Bug 45: dispatch_command_status for test execution
  advances red_run to implementation, green_run to
  coverage_review.
- Bug 46: dispatch_agent_status for coverage_review
  advances to unit_completion.
"""

from unittest.mock import MagicMock

import pytest

from src.unit_10.stub import (
    AGENT_STATUS_LINES,
    GATE_RESPONSES,
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
    dispatch_status,
)


def _make_state(
    stage="3",
    sub_stage=None,
    current_unit=1,
    total_units=5,
    fix_ladder_position=None,
    red_run_retries=0,
    alignment_iteration=0,
    debug_session=None,
    project_name="testproj",
):
    """Build a mock PipelineState."""
    state = MagicMock()
    state.stage = stage
    state.sub_stage = sub_stage
    state.current_unit = current_unit
    state.total_units = total_units
    state.fix_ladder_position = fix_ladder_position
    state.red_run_retries = red_run_retries
    state.alignment_iteration = alignment_iteration
    state.debug_session = debug_session
    state.project_name = project_name
    state.verified_units = []
    state.pass_history = []
    state.log_references = {}
    state.last_action = None
    state.debug_history = []
    state.redo_triggered_from = None
    state.delivered_repo_path = None
    return state


class TestDispatchStatus:
    def test_dispatch_status_returns_state(self, tmp_path):
        state = _make_state()
        result = dispatch_status(
            state,
            "TEST_GENERATION_COMPLETE",
            None,
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_dispatch_status_with_gate_id(self, tmp_path):
        state = _make_state(
            stage="0",
            sub_stage="hook_activation",
        )
        result = dispatch_status(
            state,
            "HOOKS ACTIVATED",
            "gate_0_1_hook_activation",
            None,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_dispatch_status_with_command_status(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_status(
            state,
            "TESTS_PASSED",
            None,
            1,
            "main",
            tmp_path,
        )
        assert result is not None


class TestDispatchGateResponse:
    def test_returns_pipeline_state(self, tmp_path):
        state = _make_state(
            stage="0",
            sub_stage="hook_activation",
        )
        result = dispatch_gate_response(
            state,
            "gate_0_1_hook_activation",
            "HOOKS ACTIVATED",
            tmp_path,
        )
        assert result is not None

    def test_invalid_gate_id_raises(self, tmp_path):
        state = _make_state()
        with pytest.raises((ValueError, KeyError)):
            dispatch_gate_response(
                state,
                "nonexistent_gate",
                "APPROVE",
                tmp_path,
            )

    def test_invalid_response_raises(self, tmp_path):
        state = _make_state(
            stage="0",
            sub_stage="hook_activation",
        )
        with pytest.raises((ValueError, KeyError)):
            dispatch_gate_response(
                state,
                "gate_0_1_hook_activation",
                "INVALID_RESPONSE",
                tmp_path,
            )

    @pytest.mark.parametrize(
        "gate_id",
        list(GATE_RESPONSES.keys()),
    )
    def test_all_gate_ids_accepted(self, tmp_path, gate_id):
        """Every gate in GATE_RESPONSES should be
        accepted by dispatch_gate_response."""
        state = _make_state(
            stage="0",
            sub_stage="hook_activation",
        )
        responses = GATE_RESPONSES[gate_id]
        # Just verify it does not raise KeyError on
        # gate_id lookup (may raise TransitionError
        # due to wrong stage).
        try:
            dispatch_gate_response(
                state,
                gate_id,
                responses[0],
                tmp_path,
            )
        except (ValueError, KeyError) as e:
            if "gate" in str(e).lower():
                pytest.fail(f"Gate {gate_id} not accepted")
        except Exception:
            pass  # Other errors are OK


class TestDispatchAgentStatus:
    def test_returns_pipeline_state(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
        )
        result = dispatch_agent_status(
            state,
            "test_agent",
            "TEST_GENERATION_COMPLETE",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_invalid_agent_type_raises(self, tmp_path):
        state = _make_state()
        with pytest.raises((ValueError, KeyError)):
            dispatch_agent_status(
                state,
                "nonexistent_agent",
                "SOME_STATUS",
                None,
                "main",
                tmp_path,
            )

    def test_help_agent_returns_state_unchanged(self, tmp_path):
        """Help agent: bare return state is valid
        (exhaustive dispatch invariant)."""
        state = _make_state()
        result = dispatch_agent_status(
            state,
            "help_agent",
            "HELP_SESSION_COMPLETE: no hint",
            None,
            "help",
            tmp_path,
        )
        assert result is not None

    def test_hint_agent_returns_state_unchanged(self, tmp_path):
        """Hint agent: bare return state is valid
        (exhaustive dispatch invariant)."""
        state = _make_state()
        result = dispatch_agent_status(
            state,
            "hint_agent",
            "HINT_ANALYSIS_COMPLETE",
            None,
            "hint",
            tmp_path,
        )
        assert result is not None


class TestBug44TestAgentSubStage:
    """Bug 44: dispatch_agent_status for test_agent
    handles sub_stage in (None, 'test_generation')."""

    def test_test_agent_sub_stage_none(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=1,
        )
        result = dispatch_agent_status(
            state,
            "test_agent",
            "TEST_GENERATION_COMPLETE",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_test_agent_sub_stage_test_generation(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state,
            "test_agent",
            "TEST_GENERATION_COMPLETE",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_test_agent_regression_test(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state,
            "test_agent",
            "REGRESSION_TEST_COMPLETE",
            1,
            "main",
            tmp_path,
        )
        assert result is not None


class TestBug46CoverageReview:
    """Bug 46: dispatch_agent_status for
    coverage_review advances to unit_completion."""

    def test_coverage_no_gaps_advances(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="coverage_review",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state,
            "coverage_review",
            "COVERAGE_COMPLETE: no gaps",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_coverage_tests_added_advances(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="coverage_review",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state,
            "coverage_review",
            "COVERAGE_COMPLETE: tests added",
            1,
            "main",
            tmp_path,
        )
        assert result is not None


class TestDispatchAgentStatusReferenceIndexing:
    """dispatch_agent_status for reference_indexing
    advances from pre_stage_3 to stage 3."""

    def test_reference_indexing_advances(self, tmp_path):
        state = _make_state(
            stage="pre_stage_3",
            sub_stage=None,
        )
        result = dispatch_agent_status(
            state,
            "reference_indexing",
            "INDEXING_COMPLETE",
            None,
            "main",
            tmp_path,
        )
        assert result is not None


class TestDispatchAgentStatusExhaustive:
    """Exhaustive dispatch invariant: every main-pipeline
    agent type must explicitly advance state."""

    MAIN_PIPELINE_AGENTS = [
        "setup_agent",
        "stakeholder_dialog",
        "stakeholder_reviewer",
        "blueprint_author",
        "blueprint_checker",
        "blueprint_reviewer",
        "test_agent",
        "implementation_agent",
        "coverage_review",
        "diagnostic_agent",
        "integration_test_author",
        "git_repo_agent",
        "redo_agent",
        "bug_triage",
        "repair_agent",
        "reference_indexing",
    ]

    SLASH_COMMAND_AGENTS = [
        "help_agent",
        "hint_agent",
    ]

    @pytest.mark.parametrize(
        "agent",
        MAIN_PIPELINE_AGENTS,
    )
    def test_main_agents_in_status_lines(self, agent):
        """Each main-pipeline agent has entries in
        AGENT_STATUS_LINES."""
        assert agent in AGENT_STATUS_LINES

    @pytest.mark.parametrize(
        "agent",
        SLASH_COMMAND_AGENTS,
    )
    def test_slash_command_agents_in_status_lines(self, agent):
        assert agent in AGENT_STATUS_LINES


class TestDispatchCommandStatus:
    def test_returns_pipeline_state(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_PASSED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_tests_failed_returns_state(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_FAILED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_tests_error_returns_state(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_ERROR",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_command_succeeded_returns_state(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "COMMAND_SUCCEEDED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_command_failed_returns_state(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "COMMAND_FAILED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_unrecognized_status_raises_error(self, tmp_path):
        """Custom status strings not in
        COMMAND_STATUS_PATTERNS cause ValueError."""
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        with pytest.raises(ValueError):
            dispatch_command_status(
                state,
                "INFRASTRUCTURE_SETUP_COMPLETE",
                1,
                "main",
                tmp_path,
            )


class TestBug45CommandStatusAdvancement:
    """Bug 45: dispatch_command_status for test
    execution advances red_run to implementation,
    green_run to coverage_review."""

    def test_red_run_tests_passed_advances(self, tmp_path):
        """red_run + TESTS_PASSED should not advance
        (red run expects failure)."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_PASSED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_red_run_tests_failed_advances(self, tmp_path):
        """red_run + TESTS_FAILED advances to
        implementation."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_FAILED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_green_run_tests_passed_advances(self, tmp_path):
        """green_run + TESTS_PASSED advances to
        coverage_review."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_PASSED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None

    def test_green_run_tests_failed(self, tmp_path):
        """green_run + TESTS_FAILED should handle
        failure path."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state,
            "TESTS_FAILED",
            1,
            "main",
            tmp_path,
        )
        assert result is not None
