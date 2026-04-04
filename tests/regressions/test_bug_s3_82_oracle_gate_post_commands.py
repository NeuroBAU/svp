"""Regression tests for Bug S3-82: Oracle gate action blocks missing POST commands.

All four oracle gate action blocks must include a `post` field so that the
orchestrator can invoke `dispatch_gate_response()` to advance `oracle_phase`.
"""

import copy
from pathlib import Path

import pytest

from routing import (
    GATE_VOCABULARY,
    _route_oracle,
    dispatch_command_status,
    dispatch_gate_response,
    load_state,
    save_state,
)
from pipeline_state import PipelineState
from state_transitions import enter_oracle_session


def _oracle_state(**overrides):
    """Create a PipelineState with an active oracle session."""
    base = {
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
        "delivered_repo_path": "/tmp/test-repo",
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": True,
        "oracle_test_project": "docs/",
        "oracle_phase": "dry_run",
        "oracle_run_count": 1,
        "oracle_nested_session_path": None,
        "oracle_modification_count": 0,
        "state_hash": "abc",
        "spec_revision_count": 0,
        "pass_": 2,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    base.update(overrides)
    return PipelineState(**base)


class TestOracleGatePostCommands:
    """All oracle gate action blocks must include a `post` field (Bug S3-82)."""

    def test_dry_run_gate_7a_has_post(self, tmp_path):
        """Gate 7.A from dry_run phase must have a post command."""
        state = _oracle_state(oracle_phase="dry_run")
        save_state(tmp_path, state)
        action = _route_oracle(state, tmp_path, "ORACLE_DRY_RUN_COMPLETE", 3)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_7_a_trajectory_review"
        assert "post" in action, "Missing post field on gate_7_a (dry_run phase)"
        assert "oracle_gate_7a" in action["post"]

    def test_gate_a_phase_has_post(self, tmp_path):
        """Gate 7.A from gate_a phase must have a post command."""
        state = _oracle_state(oracle_phase="gate_a")
        save_state(tmp_path, state)
        action = _route_oracle(state, tmp_path, "", 3)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_7_a_trajectory_review"
        assert "post" in action, "Missing post field on gate_7_a (gate_a phase)"
        assert "oracle_gate_7a" in action["post"]

    def test_green_run_gate_7b_has_post(self, tmp_path):
        """Gate 7.B from green_run phase (ORACLE_FIX_APPLIED) must have a post command."""
        state = _oracle_state(
            oracle_phase="green_run",
            oracle_nested_session_path=str(tmp_path / "nested"),
        )
        (tmp_path / "nested").mkdir()
        save_state(tmp_path, state)
        action = _route_oracle(state, tmp_path, "ORACLE_FIX_APPLIED", 3)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_7_b_fix_plan_review"
        assert "post" in action, "Missing post field on gate_7_b (green_run phase)"
        assert "oracle_gate_7b" in action["post"]

    def test_gate_b_phase_has_post(self, tmp_path):
        """Gate 7.B from gate_b phase must have a post command."""
        state = _oracle_state(oracle_phase="gate_b")
        save_state(tmp_path, state)
        action = _route_oracle(state, tmp_path, "", 3)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_7_b_fix_plan_review"
        assert "post" in action, "Missing post field on gate_7_b (gate_b phase)"
        assert "oracle_gate_7b" in action["post"]


class TestOracleGateCommandDispatch:
    """dispatch_command_status handles oracle_gate_7a and oracle_gate_7b (Bug S3-82)."""

    def test_oracle_gate_7a_approve(self, tmp_path):
        """oracle_gate_7a with APPROVE TRAJECTORY sets oracle_phase to green_run."""
        state = _oracle_state(oracle_phase="dry_run")
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "oracle_gate_7a", "APPROVE TRAJECTORY", project_root=tmp_path
        )
        assert new.oracle_phase == "green_run"

    def test_oracle_gate_7a_modify(self, tmp_path):
        """oracle_gate_7a with MODIFY TRAJECTORY stays in dry_run."""
        state = _oracle_state(oracle_phase="dry_run")
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "oracle_gate_7a", "MODIFY TRAJECTORY", project_root=tmp_path
        )
        assert new.oracle_phase == "dry_run"
        assert new.oracle_modification_count == 1

    def test_oracle_gate_7a_abort(self, tmp_path):
        """oracle_gate_7a with ABORT abandons oracle session."""
        state = _oracle_state(oracle_phase="dry_run")
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "oracle_gate_7a", "ABORT", project_root=tmp_path
        )
        assert new.oracle_session_active is False

    def test_oracle_gate_7b_approve(self, tmp_path):
        """oracle_gate_7b with APPROVE FIX enters debug session."""
        state = _oracle_state(oracle_phase="green_run")
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "oracle_gate_7b", "APPROVE FIX", project_root=tmp_path
        )
        assert new.debug_session is not None

    def test_oracle_gate_7b_abort(self, tmp_path):
        """oracle_gate_7b with ABORT abandons oracle session."""
        state = _oracle_state(oracle_phase="green_run")
        save_state(tmp_path, state)
        new = dispatch_command_status(
            state, "oracle_gate_7b", "ABORT", project_root=tmp_path
        )
        assert new.oracle_session_active is False

    def test_oracle_gate_7a_invalid_response(self, tmp_path):
        """oracle_gate_7a with invalid response raises ValueError."""
        state = _oracle_state(oracle_phase="dry_run")
        save_state(tmp_path, state)
        with pytest.raises(ValueError, match="Invalid response"):
            dispatch_command_status(
                state, "oracle_gate_7a", "INVALID", project_root=tmp_path
            )


class TestOracleGateRoundTrip:
    """Full round-trip: gate presented → response written → POST processed → state advanced."""

    def test_gate_7a_round_trip(self, tmp_path):
        """Simulate the full orchestrator cycle for Gate 7.A."""
        # Step 1: Route oracle — get the gate action block
        state = _oracle_state(oracle_phase="dry_run")
        save_state(tmp_path, state)
        action = _route_oracle(state, tmp_path, "ORACLE_DRY_RUN_COMPLETE", 3)
        assert action["action_type"] == "human_gate"
        assert "post" in action

        # Step 2: Simulate human writing response to last_status.txt
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("APPROVE TRAJECTORY")

        # Step 3: Process via dispatch_command_status (simulating POST command)
        new = dispatch_command_status(
            state, "oracle_gate_7a", "APPROVE TRAJECTORY", project_root=tmp_path
        )

        # Step 4: Verify state advanced
        assert new.oracle_phase == "green_run"

    def test_gate_7b_round_trip(self, tmp_path):
        """Simulate the full orchestrator cycle for Gate 7.B."""
        state = _oracle_state(
            oracle_phase="green_run",
            oracle_nested_session_path=str(tmp_path / "nested"),
        )
        (tmp_path / "nested").mkdir()
        save_state(tmp_path, state)
        action = _route_oracle(state, tmp_path, "ORACLE_FIX_APPLIED", 3)
        assert action["action_type"] == "human_gate"
        assert "post" in action

        new = dispatch_command_status(
            state, "oracle_gate_7b", "APPROVE FIX", project_root=tmp_path
        )
        assert new.debug_session is not None
