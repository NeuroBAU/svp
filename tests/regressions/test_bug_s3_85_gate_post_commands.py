"""Regression tests for Bug S3-85: All human gates must have POST commands.

Every human_gate action block must include a post field with the gate_id
as the command type. dispatch_command_status handles any GATE_VOCABULARY
key via the generic catch-all.
"""

import json
from pathlib import Path

import pytest

from routing import (
    GATE_VOCABULARY,
    dispatch_command_status,
    dispatch_gate_response,
    route,
    save_state,
    _route_debug,
    _route_stage_0,
)
from pipeline_state import PipelineState
from state_transitions import enter_debug_session, authorize_debug_session


def _make_state(**overrides):
    defaults = {
        "stage": "0",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
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
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestGenericGateDispatch:
    """dispatch_command_status catch-all handles any GATE_VOCABULARY key (Bug S3-85)."""

    def test_catchall_dispatches_gate_0_1(self, tmp_path):
        """Generic dispatch handles gate_0_1_hook_activation."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("HOOKS ACTIVATED")
        new = dispatch_command_status(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED",
            project_root=tmp_path,
        )
        assert new.sub_stage == "project_context"

    def test_catchall_dispatches_gate_6_0(self, tmp_path):
        """Generic dispatch handles gate_6_0_debug_permission."""
        state = _make_state(stage="5", sub_stage="pass_transition")
        state = enter_debug_session(state, 1)
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG",
            project_root=tmp_path,
        )
        assert new.debug_session["authorized"] is True

    def test_catchall_dispatches_gate_6_2(self, tmp_path):
        """Generic dispatch handles gate_6_2_debug_classification FIX IN PLACE."""
        state = _make_state(stage="5", sub_stage="pass_transition")
        state = enter_debug_session(state, 1)
        state = authorize_debug_session(state)
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "gate_6_2_debug_classification", "FIX IN PLACE",
            project_root=tmp_path,
        )
        assert new.debug_session["phase"] == "repair"

    def test_catchall_rejects_invalid_response(self, tmp_path):
        """Generic dispatch raises ValueError for invalid gate response."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        save_state(tmp_path, state)
        with pytest.raises(ValueError, match="Invalid response"):
            dispatch_command_status(
                state, "gate_0_1_hook_activation", "INVALID RESPONSE",
                project_root=tmp_path,
            )

    def test_all_gate_ids_are_dispatchable(self):
        """Every GATE_VOCABULARY key is a valid command_type for the catch-all."""
        for gate_id in GATE_VOCABULARY:
            assert gate_id in GATE_VOCABULARY, f"{gate_id} not in GATE_VOCABULARY"


class TestAllGatesHavePost:
    """Every human_gate action block must include a post field (Bug S3-85)."""

    def test_gate_0_1_has_post(self, tmp_path):
        """gate_0_1_hook_activation has post field."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("")
        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_0_1_hook_activation"
        assert "post" in action, "gate_0_1 missing post field"
        assert "gate_0_1_hook_activation" in action["post"]

    def test_debug_gate_6_0_has_post(self, tmp_path):
        """gate_6_0_debug_permission has post field."""
        state = _make_state(stage="5", sub_stage="pass_transition")
        state = enter_debug_session(state, 1)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("")
        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_6_0_debug_permission"
        assert "post" in action, "gate_6_0 missing post field"
        assert "gate_6_0_debug_permission" in action["post"]


class TestGate60RoundTrip:
    """Full round-trip: gate presented → response → POST → state advanced (Bug S3-85)."""

    def test_gate_6_0_authorize_round_trip(self, tmp_path):
        """Gate 6.0 AUTHORIZE DEBUG advances debug session via POST dispatch."""
        # Step 1: Create state with unauthorized debug session
        state = _make_state(stage="5", sub_stage="pass_transition")
        state = enter_debug_session(state, 1)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("")

        # Step 2: Route presents gate
        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert "post" in action

        # Step 3: Human writes response, POST processes it
        new = dispatch_command_status(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG",
            project_root=tmp_path,
        )
        assert new.debug_session["authorized"] is True

        # Step 4: Save and re-route — should NOT loop back to gate_6_0
        save_state(tmp_path, new)
        (tmp_path / ".svp" / "last_status.txt").write_text("AUTHORIZE DEBUG")
        action2 = route(tmp_path)
        assert action2.get("gate_id") != "gate_6_0_debug_permission", \
            "Gate 6.0 should not loop after authorization"
