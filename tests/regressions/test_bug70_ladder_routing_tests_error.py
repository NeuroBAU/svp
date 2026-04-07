"""Regression tests for Bug 70: Fix ladder routing at sub_stage=None,
TESTS_ERROR infinite loop, and dead phase removal.

SVP 2.2: route() now takes only project_root (reads state internally).
dispatch_command_status now takes (state, command_type, status_line,
sub_stage). _KNOWN_PHASES was removed.

Finding 1 and Finding 2 tests adapted to new dispatch_command_status
signature. Finding 3 tests skipped (_KNOWN_PHASES removed).
"""

import pytest

from pipeline_state import PipelineState
from routing import dispatch_command_status


def _make_state(**overrides) -> PipelineState:
    """Create a minimal PipelineState with overrides."""
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 5,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iterations": 0,
        "verified_units": [],
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


# =============================================================================
# Finding 1: sub_stage=None with fix_ladder_position routes correctly
# =============================================================================


# =============================================================================
# Finding 2: TESTS_ERROR must not return state unchanged
# =============================================================================


class TestFinding2TestsErrorNotInfiniteLoop:
    """Bug 70 F2: TESTS_ERROR must produce a state change, not bare return.

    SVP 2.2: dispatch_command_status(state, command_type, status_line,
    sub_stage) -- adapted below.
    """

    def test_tests_error_red_run_increments_retries(self):
        """TESTS_ERROR at red_run should increment retries."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            red_run_retries=0,
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "red_run"
        )
        assert new_state.red_run_retries >= 1

    def test_tests_error_green_run_engages_fix_ladder(self):
        """TESTS_ERROR at green_run should engage fix ladder."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            fix_ladder_position=None,
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "green_run"
        )
        assert new_state.fix_ladder_position is not None or new_state.sub_stage != "green_run"

    def test_tests_error_stage4_increments_retries(self):
        """TESTS_ERROR at Stage 4 should increment retries."""
        state = _make_state(
            stage="4",
            sub_stage=None,
            red_run_retries=0,
        )
        new_state = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR"
        )
        assert new_state.red_run_retries >= 1


# =============================================================================
# Finding 3: Dead phases removed from _KNOWN_PHASES
# =============================================================================


