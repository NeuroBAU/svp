"""Bug 55 regression tests: rollback_to_unit wired to Gate 6.2 FIX UNIT,
set_debug_classification wired to bug_triage dispatch, build_env fast path,
phase-based debug routing in Stage 5.

Verifies:
- Gate 6.2 FIX UNIT calls rollback_to_unit with min(affected_units)
- Gate 6.2 FIX UNIT is a no-op when no debug session or no affected_units
- Gate 6.2 FIX UNIT clears last_status.txt
- Gate 6.2 FIX UNIT advances debug phase to stage3_reentry
- dispatch_agent_status for bug_triage calls set_debug_classification
- _read_triage_affected_units reads .svp/triage_result.json
- rollback_to_unit accepts stage 5 with active debug session
- rollback_to_unit rejects stage 5 without debug session
- build_env fast path routes to repair agent, not Gate 6.2
- rollback_to_unit deletes (not copies) invalidated source/test files
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on the path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))


def _make_state(**kwargs):
    """Create a PipelineState with sensible defaults for debug testing."""
    from pipeline_state import PipelineState, DebugSession

    defaults = {
        "stage": "5",
        "sub_stage": None,
        "current_unit": 10,
        "total_units": 10,
        "verified_units": [{"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)],
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "last_action": "",
        "delivered_repo_path": "/tmp/test-repo",
    }
    defaults.update(kwargs)

    # Handle debug_session dict -> DebugSession conversion
    ds = defaults.pop("debug_session", None)

    state = PipelineState.from_dict(defaults)
    if ds is not None:
        if isinstance(ds, dict):
            state.debug_session = DebugSession(**ds)
        else:
            state.debug_session = ds
    return state


def _make_debug_session(**kwargs):
    """Create a debug session dict with defaults for an authorized triage session."""
    defaults = {
        "bug_id": 1,
        "description": "test bug",
        "classification": None,
        "affected_units": [],
        "regression_test_path": None,
        "phase": "triage",
        "authorized": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------
# Gate 6.2 FIX UNIT dispatch tests
# ---------------------------------------------------------------


class TestGate62FixUnit:
    """Gate 6.2 FIX UNIT must call rollback_to_unit."""

    def test_fix_unit_calls_rollback(self, tmp_path):
        """FIX UNIT with active session and affected_units triggers rollback."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            affected_units=[5, 7],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)

        # Create marker files and source/test dirs to verify rollback
        markers = tmp_path / ".svp" / "markers"
        markers.mkdir(parents=True)
        for u in range(1, 11):
            (markers / f"unit_{u}_verified").write_text(f"VERIFIED: t{u}\n")
            (tmp_path / "src" / f"unit_{u}").mkdir(parents=True, exist_ok=True)
            (tmp_path / "src" / f"unit_{u}" / "stub.py").write_text("# stub")
            (tmp_path / "tests" / f"unit_{u}").mkdir(parents=True, exist_ok=True)

        # Create last_status.txt to verify it gets cleared
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: single_unit")

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )

        # Should transition to Stage 3 at the earliest affected unit
        assert result.stage == "3"
        assert result.current_unit == 5  # min([5, 7])
        assert result.sub_stage is None

    def test_fix_unit_no_session_noop(self, tmp_path):
        """FIX UNIT without debug session returns state unchanged."""
        from routing import dispatch_gate_response

        state = _make_state(debug_session=None)
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        assert result.stage == "5"
        assert result.sub_stage is None

    def test_fix_unit_empty_affected_noop(self, tmp_path):
        """FIX UNIT with empty affected_units returns state unchanged."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(affected_units=[])
        state = _make_state(debug_session=ds)
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        assert result.stage == "5"

    def test_fix_unit_clears_last_status(self, tmp_path):
        """FIX UNIT deletes .svp/last_status.txt."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(affected_units=[3])
        state = _make_state(debug_session=ds)

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        status_file = svp_dir / "last_status.txt"
        status_file.write_text("TRIAGE_COMPLETE: single_unit")
        (svp_dir / "markers").mkdir(parents=True, exist_ok=True)

        dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        assert not status_file.exists()

    def test_fix_unit_advances_debug_phase(self, tmp_path):
        """FIX UNIT advances debug phase to stage3_reentry."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(affected_units=[5], phase="triage")
        state = _make_state(debug_session=ds)

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "markers").mkdir(parents=True, exist_ok=True)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )
        assert result.debug_session is not None
        assert result.debug_session.phase == "stage3_reentry"


# ---------------------------------------------------------------
# dispatch_agent_status for bug_triage tests
# ---------------------------------------------------------------


class TestTriageDispatch:
    """dispatch_agent_status for bug_triage must call set_debug_classification."""

    def test_triage_dispatch_sets_classification(self, tmp_path):
        """TRIAGE_COMPLETE: single_unit sets classification on debug session."""
        from routing import dispatch_agent_status

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)

        # Write triage_result.json with affected_units
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "triage_result.json").write_text(
            json.dumps({"affected_units": [5, 7], "classification": "single_unit"})
        )

        result = dispatch_agent_status(
            state, "bug_triage", "TRIAGE_COMPLETE: single_unit",
            None, "debug", tmp_path
        )
        assert result.debug_session is not None
        assert result.debug_session.classification == "single_unit"
        assert result.debug_session.affected_units == [5, 7]

    def test_triage_dispatch_reads_affected_units(self, tmp_path):
        """_read_triage_affected_units parses .svp/triage_result.json."""
        from routing import _read_triage_affected_units

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "triage_result.json").write_text(
            json.dumps({"affected_units": [3, 8]})
        )

        result = _read_triage_affected_units(tmp_path)
        assert result == [3, 8]

    def test_triage_dispatch_missing_file_returns_empty(self, tmp_path):
        """_read_triage_affected_units returns [] when file is missing."""
        from routing import _read_triage_affected_units

        result = _read_triage_affected_units(tmp_path)
        assert result == []

    def test_triage_dispatch_cross_unit(self, tmp_path):
        """TRIAGE_COMPLETE: cross_unit sets classification correctly."""
        from routing import dispatch_agent_status

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "triage_result.json").write_text(
            json.dumps({"affected_units": [2, 9]})
        )

        result = dispatch_agent_status(
            state, "bug_triage", "TRIAGE_COMPLETE: cross_unit",
            None, "debug", tmp_path
        )
        assert result.debug_session is not None
        assert result.debug_session.classification == "cross_unit"
        assert result.debug_session.affected_units == [2, 9]


# ---------------------------------------------------------------
# rollback_to_unit from Stage 5 tests
# ---------------------------------------------------------------


class TestRollbackFromStage5:
    """rollback_to_unit must accept stage 5 with active debug session."""

    def test_rollback_from_stage5_debug(self, tmp_path):
        """Stage 5 with debug session: rollback transitions to Stage 3."""
        from state_transitions import rollback_to_unit

        ds = _make_debug_session(affected_units=[5])
        state = _make_state(debug_session=ds)

        (tmp_path / ".svp" / "markers").mkdir(parents=True, exist_ok=True)

        result = rollback_to_unit(state, 5, tmp_path)
        assert result.stage == "3"
        assert result.current_unit == 5
        assert result.sub_stage is None
        assert result.fix_ladder_position is None
        assert result.red_run_retries == 0

    def test_rollback_from_stage5_no_debug_raises(self, tmp_path):
        """Stage 5 without debug session: rollback raises TransitionError."""
        from state_transitions import rollback_to_unit, TransitionError

        state = _make_state(debug_session=None)

        with pytest.raises(TransitionError):
            rollback_to_unit(state, 5, tmp_path)

    def test_rollback_deletes_not_copies(self, tmp_path):
        """rollback_to_unit deletes source/test dirs, does not copy to logs/rollback/."""
        from state_transitions import rollback_to_unit

        ds = _make_debug_session(affected_units=[5])
        state = _make_state(
            stage="3",
            debug_session=ds,
            current_unit=10,
            verified_units=[
                {"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)
            ],
        )

        (tmp_path / ".svp" / "markers").mkdir(parents=True, exist_ok=True)
        for u in range(5, 11):
            (tmp_path / "src" / f"unit_{u}").mkdir(parents=True, exist_ok=True)
            (tmp_path / "src" / f"unit_{u}" / "stub.py").write_text("# code")
            (tmp_path / "tests" / f"unit_{u}").mkdir(parents=True, exist_ok=True)
            (tmp_path / "tests" / f"unit_{u}" / "test_stub.py").write_text("# test")

        rollback_to_unit(state, 5, tmp_path)

        # Verify files are deleted
        for u in range(5, 11):
            assert not (tmp_path / "src" / f"unit_{u}").exists()
            assert not (tmp_path / "tests" / f"unit_{u}").exists()

        # Verify no logs/rollback directory was created
        assert not (tmp_path / "logs" / "rollback").exists()

    def test_rollback_invalidates_verified_units(self, tmp_path):
        """rollback_to_unit removes verified_units >= target unit."""
        from state_transitions import rollback_to_unit

        ds = _make_debug_session()
        state = _make_state(
            debug_session=ds,
            verified_units=[
                {"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)
            ],
        )

        (tmp_path / ".svp" / "markers").mkdir(parents=True, exist_ok=True)

        result = rollback_to_unit(state, 5, tmp_path)
        remaining = [vu["unit"] for vu in result.verified_units]
        assert remaining == [1, 2, 3, 4]


# ---------------------------------------------------------------
# build_env fast path test
# ---------------------------------------------------------------


class TestBuildEnvFastPath:
    """TRIAGE_COMPLETE: build_env must NOT present Gate 6.2."""

    def test_build_env_routes_to_repair(self, tmp_path):
        """build_env fast path routes to repair agent, not Gate 6.2."""
        from routing import route

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: build_env")
        (svp_dir / "doc_sync_done").touch()

        action = route(state, tmp_path)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "repair_agent"

    def test_single_unit_presents_gate_62(self, tmp_path):
        """single_unit triage presents Gate 6.2."""
        from routing import route

        ds = _make_debug_session()
        state = _make_state(debug_session=ds)

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: single_unit")
        (svp_dir / "doc_sync_done").touch()

        action = route(state, tmp_path)
        assert action["ACTION"] == "human_gate"
        assert action["GATE_ID"] == "gate_6_2_debug_classification"


# ---------------------------------------------------------------
# Phase-based Stage 5 routing test
# ---------------------------------------------------------------


class TestPhaseBasedRouting:
    """Stage 5 routing with debug session must check phase."""

    def test_stage3_reentry_falls_through(self, tmp_path):
        """stage3_reentry phase falls through to normal Stage 5 routing."""
        from routing import route

        ds = _make_debug_session(phase="stage3_reentry")
        state = _make_state(debug_session=ds, sub_stage=None)

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)

        action = route(state, tmp_path)
        # Should fall through to normal Stage 5 routing (git_repo_agent)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "git_repo_agent"
