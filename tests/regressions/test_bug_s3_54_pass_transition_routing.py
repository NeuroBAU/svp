"""Regression tests for Bug S3-54: Stage 5 pass_transition not routed.

Verifies that _route_stage_5() handles sub_stage="pass_transition" by
presenting the appropriate human gate, instead of falling through to
the default git_repo_agent invocation.
"""

from pathlib import Path

import pytest

from src.unit_5.stub import PipelineState
from src.unit_14.stub import _route_stage_5


def _make_state(**overrides):
    """Build a minimal PipelineState with defaults."""
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
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestS3_54_PassTransitionRouting:
    """Bug S3-54: _route_stage_5 must handle pass_transition sub-stage."""

    def test_pass1_presents_post_pass1_gate(self):
        """pass_transition with pass=1 presents gate_pass_transition_post_pass1."""
        state = _make_state(pass_=1)
        result = _route_stage_5(state, Path("/tmp"), "", 3)
        assert result["action_type"] == "human_gate"
        assert result["gate_id"] == "gate_pass_transition_post_pass1"

    def test_pass2_presents_post_pass2_gate(self):
        """pass_transition with pass=2 presents gate_pass_transition_post_pass2."""
        state = _make_state(pass_=2)
        result = _route_stage_5(state, Path("/tmp"), "", 3)
        assert result["action_type"] == "human_gate"
        assert result["gate_id"] == "gate_pass_transition_post_pass2"

    def test_no_pass_returns_pipeline_complete(self):
        """pass_transition without pass number returns pipeline_complete."""
        state = _make_state(pass_=None)
        result = _route_stage_5(state, Path("/tmp"), "", 3)
        assert result["action_type"] == "pipeline_complete"

    def test_does_not_fall_through_to_git_repo_agent(self):
        """pass_transition must NOT fall through to git_repo_agent."""
        for pass_val in (1, 2, None):
            state = _make_state(pass_=pass_val)
            result = _route_stage_5(state, Path("/tmp"), "", 3)
            assert result.get("agent_type") != "git_repo_agent", (
                f"pass_transition with pass={pass_val} fell through to git_repo_agent"
            )

    def test_pass_transition_not_in_stage_3_only(self):
        """pass_transition handling exists in Stage 5 routing, not just Stage 3."""
        # Verify _route_stage_5 handles pass_transition directly
        # without needing to fall through to _route_stage_3
        state = _make_state(stage="5", sub_stage="pass_transition", pass_=2)
        result = _route_stage_5(state, Path("/tmp"), "", 3)
        # Must be handled in Stage 5 — if it fell through to git_repo_agent,
        # that means the pass_transition handler is missing
        assert result["action_type"] == "human_gate"
        assert "pass_transition" in result["gate_id"]
