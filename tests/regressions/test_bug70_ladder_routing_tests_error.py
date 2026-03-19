"""Regression tests for Bug 70: Fix ladder routing at sub_stage=None,
TESTS_ERROR infinite loop, and dead phase removal.

Finding 1: When quality_gate_fail_to_ladder sets sub_stage=None with a
non-None fix_ladder_position, route() must route based on ladder position
instead of defaulting to stub_generation.

Finding 2: TESTS_ERROR at test_execution must not return state unchanged
(infinite loop). Red run -> increment retries + regenerate. Green run ->
engage fix ladder. Stage 4 -> present gate.

Finding 3: "test" and "infrastructure_setup" are dead phases in _KNOWN_PHASES.
"""

import copy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts/ to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pipeline_state import PipelineState
from routing import (
    _KNOWN_PHASES,
    dispatch_command_status,
    route,
)


def _make_state(**overrides) -> PipelineState:
    """Create a minimal PipelineState with overrides."""
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 5,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test",
        "last_action": "",
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    defaults.update(overrides)
    return PipelineState.from_dict(defaults)


# =============================================================================
# Finding 1: sub_stage=None with fix_ladder_position routes correctly
# =============================================================================


class TestFinding1SubStageNoneLadderRouting:
    """Bug 70 F1: sub_stage=None with fix_ladder_position must not default
    to stub_generation."""

    def test_fresh_test_routes_to_test_generation(self, tmp_path):
        """fix_ladder_position='fresh_test' should route to test agent."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=2,
            fix_ladder_position="fresh_test",
        )
        result = route(state, tmp_path)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "test_agent"

    def test_hint_test_routes_to_test_generation(self, tmp_path):
        """fix_ladder_position='hint_test' should route to test agent."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=2,
            fix_ladder_position="hint_test",
        )
        result = route(state, tmp_path)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "test_agent"

    def test_fresh_impl_routes_to_implementation(self, tmp_path):
        """fix_ladder_position='fresh_impl' should route to impl agent."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=2,
            fix_ladder_position="fresh_impl",
        )
        result = route(state, tmp_path)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "implementation_agent"

    def test_diagnostic_routes_to_diagnostic_agent(self, tmp_path):
        """fix_ladder_position='diagnostic' should route to diagnostic agent."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=2,
            fix_ladder_position="diagnostic",
        )
        result = route(state, tmp_path)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "diagnostic_agent"

    def test_diagnostic_impl_routes_to_implementation(self, tmp_path):
        """fix_ladder_position='diagnostic_impl' should route to impl agent."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=2,
            fix_ladder_position="diagnostic_impl",
        )
        result = route(state, tmp_path)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "implementation_agent"

    def test_none_ladder_routes_to_stub_generation(self, tmp_path):
        """fix_ladder_position=None should route to stub_generation (default)."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=2,
            fix_ladder_position=None,
        )
        result = route(state, tmp_path)
        assert result["ACTION"] == "run_command"
        assert "generate_stubs" in result["COMMAND"]


# =============================================================================
# Finding 2: TESTS_ERROR must not return state unchanged
# =============================================================================


class TestFinding2TestsErrorNotInfiniteLoop:
    """Bug 70 F2: TESTS_ERROR must produce a state change, not bare return."""

    def test_tests_error_red_run_increments_retries(self, tmp_path):
        """TESTS_ERROR at red_run should increment retries and regenerate tests."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            red_run_retries=0,
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: import error", 1, "test_execution", tmp_path
        )
        assert new_state.red_run_retries == 1
        assert new_state.sub_stage == "test_generation"

    def test_tests_error_red_run_exhausted_presents_gate(self, tmp_path):
        """TESTS_ERROR at red_run with retries=2 should present Gate 3.1."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            red_run_retries=2,
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: syntax error", 1, "test_execution", tmp_path
        )
        assert new_state.red_run_retries == 3
        assert new_state.sub_stage == "gate_3_1"

    def test_tests_error_green_run_engages_fix_ladder(self, tmp_path):
        """TESTS_ERROR at green_run should engage fix ladder (fresh_impl)."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            fix_ladder_position=None,
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: import error", 1, "test_execution", tmp_path
        )
        assert new_state.fix_ladder_position == "fresh_impl"
        assert new_state.sub_stage == "implementation"

    def test_tests_error_green_run_ladder_at_fresh_impl(self, tmp_path):
        """TESTS_ERROR at green_run with fresh_impl -> diagnostic."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            fix_ladder_position="fresh_impl",
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: syntax error", 1, "test_execution", tmp_path
        )
        assert new_state.fix_ladder_position == "diagnostic"
        assert new_state.sub_stage == "implementation"

    def test_tests_error_green_run_ladder_exhausted(self, tmp_path):
        """TESTS_ERROR at green_run with diagnostic_impl -> Gate 3.2."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            fix_ladder_position="diagnostic_impl",
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: crash", 1, "test_execution", tmp_path
        )
        assert new_state.sub_stage == "gate_3_2"

    def test_tests_error_stage4_presents_gate(self, tmp_path):
        """TESTS_ERROR at Stage 4 should present gate (same as TESTS_FAILED)."""
        state = _make_state(
            stage="4",
            sub_stage=None,
            red_run_retries=0,
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: timeout", 1, "test_execution", tmp_path
        )
        assert new_state.red_run_retries == 1
        assert new_state.sub_stage in ("gate_4_1", "gate_4_2")

    def test_tests_error_stage4_exhausted(self, tmp_path):
        """TESTS_ERROR at Stage 4 with retries=2 -> Gate 4.2."""
        state = _make_state(
            stage="4",
            sub_stage=None,
            red_run_retries=2,
        )
        new_state = dispatch_command_status(
            state, "TESTS_ERROR: crash", 1, "test_execution", tmp_path
        )
        assert new_state.red_run_retries == 3
        assert new_state.sub_stage == "gate_4_2"


# =============================================================================
# Finding 3: Dead phases removed from _KNOWN_PHASES
# =============================================================================


class TestFinding3DeadPhasesRemoved:
    """Bug 70 F3: 'test' and 'infrastructure_setup' should not be in
    _KNOWN_PHASES."""

    def test_dead_phase_test_not_in_known_phases(self):
        """'test' must not be in _KNOWN_PHASES."""
        assert "test" not in _KNOWN_PHASES

    def test_dead_phase_infrastructure_setup_not_in_known_phases(self):
        """'infrastructure_setup' must not be in _KNOWN_PHASES."""
        assert "infrastructure_setup" not in _KNOWN_PHASES

    def test_test_execution_still_in_known_phases(self):
        """'test_execution' must still be in _KNOWN_PHASES (not accidentally removed)."""
        assert "test_execution" in _KNOWN_PHASES

    def test_test_generation_still_in_known_phases(self):
        """'test_generation' must still be in _KNOWN_PHASES."""
        assert "test_generation" in _KNOWN_PHASES
