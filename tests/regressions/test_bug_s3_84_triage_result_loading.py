"""Regression tests for Bug S3-84: Triage result not loaded into debug session.

dispatch_agent_status for TRIAGE_COMPLETE must load triage_result.json
into debug_session.classification and debug_session.affected_units.
"""

import json
from pathlib import Path

import pytest

from routing import dispatch_agent_status, dispatch_gate_response, save_state
from pipeline_state import PipelineState
from state_transitions import enter_debug_session, authorize_debug_session


def _make_state(**overrides):
    defaults = {
        "stage": "5",
        "sub_stage": "pass_transition",
        "current_unit": None,
        "total_units": 29,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "oracle_modification_count": 0,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": 2,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _state_with_debug(tmp_path, bug_number=1):
    """Create a state with an authorized debug session and triage_result.json."""
    state = _make_state()
    state = enter_debug_session(state, bug_number)
    state = authorize_debug_session(state)
    return state


class TestTriageResultLoading:
    """dispatch_agent_status must load triage_result.json into debug_session (Bug S3-84)."""

    def test_triage_complete_loads_affected_units(self, tmp_path):
        """TRIAGE_COMPLETE: single_unit populates debug_session.affected_units."""
        state = _state_with_debug(tmp_path)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "triage_result.json").write_text(
            json.dumps({"classification": "single_unit", "affected_units": [14], "bug_number": 1})
        )
        new = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", tmp_path
        )
        assert new.debug_session["affected_units"] == [14]

    def test_triage_complete_loads_classification(self, tmp_path):
        """TRIAGE_COMPLETE: cross_unit populates debug_session.classification."""
        state = _state_with_debug(tmp_path)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "triage_result.json").write_text(
            json.dumps({"classification": "cross_unit", "affected_units": [5, 6], "bug_number": 1})
        )
        new = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: cross_unit", tmp_path
        )
        assert new.debug_session["classification"] == "cross_unit"
        assert new.debug_session["affected_units"] == [5, 6]

    def test_triage_complete_without_result_file(self, tmp_path):
        """When triage_result.json is missing, affected_units stays empty."""
        state = _state_with_debug(tmp_path)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        # No triage_result.json
        new = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", tmp_path
        )
        assert new.debug_session["affected_units"] == []

    def test_triage_complete_fallback_classification(self, tmp_path):
        """When triage_result.json lacks classification, extract from status line."""
        state = _state_with_debug(tmp_path)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "triage_result.json").write_text(
            json.dumps({"affected_units": [14]})
        )
        new = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", tmp_path
        )
        assert new.debug_session["classification"] == "single_unit"


class TestGate62WithAffectedUnits:
    """Gate 6.2 FIX UNIT with populated affected_units calls rollback_to_unit (Bug S3-84)."""

    def test_fix_unit_with_affected_units_sets_stage_3(self, tmp_path):
        """Full round-trip: triage loads units → Gate 6.2 FIX UNIT → stage is '3'."""
        state = _state_with_debug(tmp_path)
        save_state(tmp_path, state)

        # Simulate triage completion loading affected_units
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "triage_result.json").write_text(
            json.dumps({"classification": "single_unit", "affected_units": [14], "bug_number": 1})
        )
        state = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", tmp_path
        )
        assert state.debug_session["affected_units"] == [14]

        # Now Gate 6.2 FIX UNIT should call rollback_to_unit
        new = dispatch_gate_response(state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path)
        assert new.stage == "3", f"Expected stage '3' after FIX UNIT, got '{new.stage}'"
        assert new.current_unit == 14
        assert new.sub_stage == "stub_generation"
