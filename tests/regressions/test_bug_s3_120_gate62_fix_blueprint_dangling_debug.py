"""Bug S3-120 regression tests: Gate 6.2 FIX BLUEPRINT / FIX SPEC must
abandon the debug session and delete triage_result.json, otherwise
debug_session.phase=triage dangles and the routing priority in route()
re-invokes the triage agent infinitely.

Spec authority: §12.18.13 Debug Phase Transition Summary Table.
Blueprint: dispatch_gate_response contract list for gate_6_2_debug_classification.
Code: src/unit_14/stub.py dispatch_gate_response.
"""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline_state import PipelineState, save_state
from routing import route, dispatch_gate_response


def _make_state(**kwargs):
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


def _write_config(root: Path) -> None:
    (root / "svp_config.json").write_text(
        json.dumps({"iteration_limit": 3}), encoding="utf-8"
    )


def _dispatch(state, response, tmp_path, gate_id="gate_6_2_debug_classification"):
    _write_config(tmp_path)
    return dispatch_gate_response(state, gate_id, response, tmp_path)


# ---------------------------------------------------------------
# FIX BLUEPRINT — abandon debug session
# ---------------------------------------------------------------


class TestFixBlueprintAbandonsDebugSession:

    def test_fix_blueprint_with_active_session_nulls_debug_session(self, tmp_path):
        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX BLUEPRINT", tmp_path)
        assert result.debug_session is None, (
            "FIX BLUEPRINT must null debug_session to prevent routing priority "
            "from re-entering _route_debug with phase=triage"
        )

    def test_fix_blueprint_appends_to_debug_history(self, tmp_path):
        ds = _make_debug_session(phase="triage", bug_number=42)
        state = _make_state(debug_session=ds, debug_history=[])
        result = _dispatch(state, "FIX BLUEPRINT", tmp_path)
        assert len(result.debug_history) == 1
        assert result.debug_history[0].get("bug_number") == 42

    def test_fix_blueprint_restarts_from_stage_2(self, tmp_path):
        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX BLUEPRINT", tmp_path)
        assert result.stage == "2"
        assert result.sub_stage == "blueprint_dialog"


# ---------------------------------------------------------------
# FIX BLUEPRINT — triage_result.json deletion
# ---------------------------------------------------------------


class TestFixBlueprintDeletesTriageResult:

    def test_fix_blueprint_deletes_triage_result_file(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        triage_path = svp_dir / "triage_result.json"
        triage_path.write_text(
            json.dumps({"affected_units": [5], "classification": "single_unit"}),
            encoding="utf-8",
        )
        assert triage_path.exists()

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        _dispatch(state, "FIX BLUEPRINT", tmp_path)

        assert not triage_path.exists(), (
            "FIX BLUEPRINT must delete .svp/triage_result.json per spec §12.18.13"
        )

    def test_fix_blueprint_missing_triage_file_is_tolerated(self, tmp_path):
        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX BLUEPRINT", tmp_path)
        assert result.stage == "2"


# ---------------------------------------------------------------
# FIX BLUEPRINT — no session tolerance
# ---------------------------------------------------------------


class TestFixBlueprintNoSession:

    def test_fix_blueprint_no_session_still_restarts(self, tmp_path):
        state = _make_state(debug_session=None)
        result = _dispatch(state, "FIX BLUEPRINT", tmp_path)
        assert result.stage == "2"
        assert result.debug_session is None


# ---------------------------------------------------------------
# Canonical infinite-loop guard
# ---------------------------------------------------------------


class TestInfiniteLoopBroken:
    """The original bug: after FIX BLUEPRINT, re-running route() re-invokes
    the triage agent because debug_session.phase=triage still dangles.
    """

    def test_fix_blueprint_then_route_does_not_reenter_triage(self, tmp_path):
        _write_config(tmp_path)
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("", encoding="utf-8")

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)

        dispatched = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX BLUEPRINT", tmp_path
        )
        save_state(tmp_path, dispatched)

        action = route(tmp_path)

        is_triage_reinvoke = (
            action.get("action_type") == "invoke_agent"
            and action.get("agent_type") == "bug_triage_agent"
        )
        assert not is_triage_reinvoke, (
            f"Infinite loop: route() re-invoked bug_triage_agent after "
            f"FIX BLUEPRINT. action={action}"
        )

    def test_fix_spec_then_route_does_not_reenter_triage(self, tmp_path):
        _write_config(tmp_path)
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("", encoding="utf-8")

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)

        dispatched = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX SPEC", tmp_path
        )
        save_state(tmp_path, dispatched)

        action = route(tmp_path)

        is_triage_reinvoke = (
            action.get("action_type") == "invoke_agent"
            and action.get("agent_type") == "bug_triage_agent"
        )
        assert not is_triage_reinvoke, (
            f"Infinite loop: route() re-invoked bug_triage_agent after "
            f"FIX SPEC. action={action}"
        )


# ---------------------------------------------------------------
# FIX SPEC — symmetric
# ---------------------------------------------------------------


class TestFixSpec:

    def test_fix_spec_with_active_session_nulls_debug_session(self, tmp_path):
        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX SPEC", tmp_path)
        assert result.debug_session is None

    def test_fix_spec_restarts_from_stage_1(self, tmp_path):
        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX SPEC", tmp_path)
        assert result.stage == "1"

    def test_fix_spec_deletes_triage_result_file(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        triage_path = svp_dir / "triage_result.json"
        triage_path.write_text(
            json.dumps({"affected_units": [5], "classification": "single_unit"}),
            encoding="utf-8",
        )

        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        _dispatch(state, "FIX SPEC", tmp_path)

        assert not triage_path.exists()


# ---------------------------------------------------------------
# Over-correction guards — FIX UNIT and FIX IN PLACE must still
# preserve debug_session.
# ---------------------------------------------------------------


class TestOverCorrectionGuard:
    """Ensure the fix did not accidentally cause other response branches
    to abandon the debug session.
    """

    def test_fix_unit_preserves_debug_session(self, tmp_path):
        ds = _make_debug_session(affected_units=[5], phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX UNIT", tmp_path)
        assert result.debug_session is not None, (
            "FIX UNIT must NOT abandon debug_session; it only advances phase"
        )
        assert result.debug_session["phase"] == "stage3_reentry"

    def test_fix_in_place_preserves_debug_session(self, tmp_path):
        ds = _make_debug_session(phase="triage")
        state = _make_state(debug_session=ds)
        result = _dispatch(state, "FIX IN PLACE", tmp_path)
        assert result.debug_session is not None
        assert result.debug_session["phase"] == "repair"
