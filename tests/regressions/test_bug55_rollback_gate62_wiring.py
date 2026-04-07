"""Bug 55 regression tests: rollback_to_unit wired to Gate 6.2 FIX UNIT,
dispatch_agent_status for bug_triage, build_env fast path,
phase-based debug routing.

Adapted for SVP 2.2 API:
- PipelineState is a dataclass from src.unit_5.stub
- debug_session is a plain dict (not DebugSession class)
- rollback_to_unit(state, unit_number) -- 2 args (no project_root)
- dispatch_gate_response(state, gate_id, response, project_root) -- 4 args
- dispatch_agent_status(state, agent_type, status_line, project_root) -- 4 args
- route() reads state from disk (no state arg)
- Action block keys: action_type, agent_type, gate_id (lowercase)
- TransitionError from src.unit_6.stub
"""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline_state import PipelineState, save_state
from state_transitions import rollback_to_unit, TransitionError
from routing import (
    route,
    dispatch_gate_response,
    dispatch_agent_status,
)


def _make_state(**kwargs):
    """Create a PipelineState with sensible defaults for debug testing."""
    defaults = {
        "stage": "5",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "verified_units": [{"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)],
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iterations": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": "/tmp/test-repo",
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


def _make_debug_session(**kwargs):
    """Create a debug session dict with defaults for an authorized triage session."""
    defaults = {
        "bug_number": 1,
        "classification": None,
        "affected_units": [],
        "phase": "triage",
        "authorized": True,
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    defaults.update(kwargs)
    return defaults


def _route_with_state(state, last_status=""):
    """Write state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status, encoding="utf-8")
        (root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        return route(root)


def _dispatch_gate_with_config(state, gate_id, response, tmp_path=None):
    """Call dispatch_gate_response with a temp project root containing config."""
    if tmp_path is None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            return dispatch_gate_response(state, gate_id, response, root)
    else:
        if not (tmp_path / "svp_config.json").exists():
            (tmp_path / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
        return dispatch_gate_response(state, gate_id, response, tmp_path)


# ---------------------------------------------------------------
# Gate 6.2 FIX UNIT dispatch tests
# ---------------------------------------------------------------


class TestGate62FixUnit:
    """Gate 6.2 FIX UNIT must call rollback_to_unit."""

    def test_fix_unit_calls_rollback(self, tmp_path):
        """FIX UNIT with active session and affected_units triggers rollback."""
        ds = _make_debug_session(
            affected_units=[5, 7],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)
        result = _dispatch_gate_with_config(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        # Should transition to Stage 3 at the earliest affected unit
        assert result.stage == "3"
        assert result.current_unit == 5  # min([5, 7]) after rollback
        assert result.sub_stage == "stub_generation"

    def test_fix_unit_no_session_returns_copy(self, tmp_path):
        """FIX UNIT without debug session returns copy of state."""
        state = _make_state(debug_session=None)
        result = _dispatch_gate_with_config(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        assert result.stage == "5"

    def test_fix_unit_empty_affected_returns_copy(self, tmp_path):
        """FIX UNIT with empty affected_units returns copy."""
        ds = _make_debug_session(affected_units=[])
        state = _make_state(debug_session=ds)
        result = _dispatch_gate_with_config(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        # No rollback when affected_units is empty
        assert result.debug_session is not None

    def test_fix_unit_advances_debug_phase(self, tmp_path):
        """FIX UNIT advances debug phase to stage3_reentry."""
        ds = _make_debug_session(affected_units=[5], phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch_gate_with_config(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        assert result.debug_session is not None
        assert result.debug_session["phase"] == "stage3_reentry"


# ---------------------------------------------------------------
# dispatch_agent_status for bug_triage tests
# ---------------------------------------------------------------


class TestTriageDispatch:
    """dispatch_agent_status for bug_triage_agent returns state copy."""

    def test_triage_dispatch_returns_state(self, tmp_path):
        """TRIAGE_COMPLETE: single_unit returns copy of state
        (two-branch routing presents gate)."""
        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        (tmp_path / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", tmp_path,
        )
        # In SVP 2.2, dispatch returns copy; route handles gate presentation
        assert result is not state

    def test_triage_dispatch_cross_unit(self, tmp_path):
        """TRIAGE_COMPLETE: cross_unit returns copy."""
        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        (tmp_path / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: cross_unit", tmp_path,
        )
        assert result is not state

    def test_triage_dispatch_build_env_enters_repair(self, tmp_path):
        """TRIAGE_COMPLETE: build_env fast path sets phase to repair."""
        ds = _make_debug_session()
        state = _make_state(debug_session=ds)
        (tmp_path / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: build_env", tmp_path,
        )
        assert result.debug_session is not None
        assert result.debug_session["phase"] == "repair"


# ---------------------------------------------------------------
# rollback_to_unit from Stage 5 tests
# ---------------------------------------------------------------


class TestRollbackFromStage5:
    """rollback_to_unit must work from any stage."""

    def test_rollback_transitions_to_stage3(self):
        """Rollback transitions to Stage 3."""
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=10,
        )
        result = rollback_to_unit(state, 5)
        assert result.stage == "3"
        assert result.current_unit == 5
        assert result.sub_stage == "stub_generation"
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_rollback_invalidates_verified_units(self):
        """rollback_to_unit removes verified_units >= target unit."""
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=10,
            verified_units=[
                {"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)
            ],
        )
        result = rollback_to_unit(state, 5)
        remaining = [vu["unit"] for vu in result.verified_units]
        assert remaining == [1, 2, 3, 4]


# ---------------------------------------------------------------
# build_env fast path test
# ---------------------------------------------------------------


class TestBuildEnvFastPath:
    """TRIAGE_COMPLETE: build_env must NOT present Gate 6.2."""

    def test_build_env_routes_to_repair(self):
        """build_env fast path routes to repair agent, not Gate 6.2."""
        ds = _make_debug_session(phase="triage", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state, last_status="TRIAGE_COMPLETE: build_env")
        assert action["action_type"] == "invoke_agent"
        assert action["agent_type"] == "repair_agent"

    def test_single_unit_presents_gate_62(self):
        """single_unit triage presents Gate 6.2."""
        ds = _make_debug_session(phase="triage", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(
            state, last_status="TRIAGE_COMPLETE: single_unit"
        )
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_6_2_debug_classification"


# ---------------------------------------------------------------
# Phase-based routing test
# ---------------------------------------------------------------


class TestPhaseBasedRouting:
    """Debug session routing must check phase."""

    def test_stage3_reentry_routes_correctly(self):
        """stage3_reentry phase routes to stage3_reentry command."""
        ds = _make_debug_session(phase="stage3_reentry", authorized=True)
        state = _make_state(debug_session=ds)
        action = _route_with_state(state)
        assert action["action_type"] == "run_command"
        assert action["command"] == "stage3_reentry"
