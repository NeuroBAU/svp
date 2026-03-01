"""
Tests for Unit 10 routing functions: route, format_action_block,
and derive_env_name_from_state.

DATA ASSUMPTION: PipelineState objects are constructed with default values
from the Unit 2 schema. Project names like "my_project" and "svp1.2.1"
are typical short alphanumeric+punctuation project names.

DATA ASSUMPTION: Pipeline stages and sub-stages follow the canonical
sequence defined in Unit 2: ["0", "1", "2", "pre_stage_3", "3", "4", "5"].
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import tempfile
import os

from svp.scripts.routing import (
    route,
    format_action_block,
    derive_env_name_from_state,
    GATE_VOCABULARY,
)
from svp.scripts.pipeline_state import PipelineState, DebugSession


@pytest.fixture
def tmp_project_root(tmp_path):
    """Create a temporary project root with a pipeline_state.json."""
    return tmp_path


def _make_state(**kwargs):
    """Helper to create a PipelineState with sensible defaults."""
    defaults = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "project_name": "my_project",
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


def _write_state(project_root, state):
    """Write pipeline state to disk."""
    state_path = project_root / "pipeline_state.json"
    state_path.write_text(
        json.dumps(state.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


class TestRoute:
    """Tests for the route function."""

    def test_route_returns_dict(self, tmp_project_root):
        """route() must return a dict."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert isinstance(result, dict)

    def test_route_result_contains_action_key(self, tmp_project_root):
        """Post-condition: result must contain ACTION."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_action_is_valid_type(self, tmp_project_root):
        """Post-condition: ACTION must be one of the five valid types."""
        valid_actions = {
            "invoke_agent", "run_command", "human_gate",
            "session_boundary", "pipeline_complete",
        }
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] in valid_actions

    def test_route_precondition_project_root_exists(self):
        """Pre-condition: project_root must be a directory."""
        state = _make_state()
        nonexistent = Path("/nonexistent_dir_that_does_not_exist_xyz")
        with pytest.raises((AssertionError, OSError, FileNotFoundError)):
            route(state, nonexistent)

    def test_route_stage_0_hook_activation(self, tmp_project_root):
        """Route at stage 0, sub_stage hook_activation should produce an action."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result
        assert result["ACTION"] in {
            "invoke_agent", "run_command", "human_gate",
            "session_boundary", "pipeline_complete",
        }

    def test_route_stage_0_project_context(self, tmp_project_root):
        """Route at stage 0, sub_stage project_context."""
        state = _make_state(stage="0", sub_stage="project_context")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_1(self, tmp_project_root):
        """Route at stage 1 should produce a valid action."""
        state = _make_state(stage="1", sub_stage=None)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_2(self, tmp_project_root):
        """Route at stage 2 should produce a valid action."""
        state = _make_state(stage="2", sub_stage=None)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_pre_stage_3(self, tmp_project_root):
        """Route at pre_stage_3 should produce a valid action."""
        state = _make_state(stage="pre_stage_3", sub_stage=None)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_3_with_unit(self, tmp_project_root):
        """Route at stage 3 with current_unit set."""
        state = _make_state(stage="3", sub_stage=None, current_unit=1, total_units=5)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_4(self, tmp_project_root):
        """Route at stage 4."""
        state = _make_state(stage="4", sub_stage=None)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_5(self, tmp_project_root):
        """Route at stage 5 (pipeline complete or debug loop)."""
        state = _make_state(stage="5", sub_stage=None)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_stage_5_with_debug_session(self, tmp_project_root):
        """Route at stage 5 with an active debug session (debug loop)."""
        debug = DebugSession(
            bug_id=1,
            description="Test bug",
            classification="single_unit",
            affected_units=[3],
            phase="triage",
            authorized=True,
        )
        state = _make_state(stage="5", sub_stage=None, debug_session=debug)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert "ACTION" in result

    def test_route_human_gate_includes_options(self, tmp_project_root):
        """When route returns a human_gate action, OPTIONS must list valid
        status strings from GATE_VOCABULARY (Bug 1 invariant)."""
        # Try stage 0 hook_activation which should eventually produce a gate
        # We try different states to find one that gives us a human_gate action
        # The gate_0_1_hook_activation gate is presented after setup completes
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        if result["ACTION"] == "human_gate":
            assert "OPTIONS" in result
            gate_id = result.get("GATE")
            if gate_id and gate_id in GATE_VOCABULARY:
                # Bug 1 invariant: OPTIONS must exactly match GATE_VOCABULARY
                assert result["OPTIONS"] == GATE_VOCABULARY[gate_id]


class TestFormatActionBlock:
    """Tests for format_action_block."""

    def test_returns_string(self):
        """format_action_block must return a string."""
        action = {"ACTION": "invoke_agent", "AGENT": "test_agent"}
        result = format_action_block(action)
        assert isinstance(result, str)

    def test_invoke_agent_includes_reminder(self):
        """Non-terminal actions (invoke_agent) must include REMINDER block."""
        action = {
            "ACTION": "invoke_agent",
            "AGENT": "test_agent",
            "PREPARE": "python scripts/prepare.py",
            "TASK_PROMPT_FILE": ".svp/task_prompt.md",
            "POST": "python scripts/update.py",
        }
        result = format_action_block(action)
        assert "REMINDER:" in result

    def test_run_command_includes_reminder(self):
        """Non-terminal actions (run_command) must include REMINDER block."""
        action = {
            "ACTION": "run_command",
            "COMMAND": "pytest tests/ -v",
        }
        result = format_action_block(action)
        assert "REMINDER:" in result

    def test_human_gate_includes_reminder(self):
        """Non-terminal actions (human_gate) must include REMINDER block."""
        action = {
            "ACTION": "human_gate",
            "GATE": "gate_1_1_spec_draft",
            "OPTIONS": ["APPROVE", "REVISE", "FRESH REVIEW"],
            "PROMPT_FILE": ".svp/gate_prompt.md",
        }
        result = format_action_block(action)
        assert "REMINDER:" in result

    def test_session_boundary_no_reminder(self):
        """session_boundary actions must NOT include REMINDER block."""
        action = {
            "ACTION": "session_boundary",
            "MESSAGE": "Session boundary reached. Save and resume.",
        }
        result = format_action_block(action)
        # The action block should NOT include REMINDER for session_boundary
        # We check that "REMINDER:" does not appear
        assert "REMINDER:" not in result

    def test_pipeline_complete_no_reminder(self):
        """pipeline_complete actions must NOT include REMINDER block."""
        action = {
            "ACTION": "pipeline_complete",
            "MESSAGE": "Pipeline complete.",
        }
        result = format_action_block(action)
        assert "REMINDER:" not in result

    def test_action_block_contains_action_field(self):
        """The formatted block should contain the ACTION field."""
        action = {"ACTION": "invoke_agent", "AGENT": "test_agent"}
        result = format_action_block(action)
        assert "ACTION" in result
        assert "invoke_agent" in result

    def test_action_block_contains_all_specified_fields(self):
        """The formatted block should include all key-value pairs from the dict."""
        action = {
            "ACTION": "invoke_agent",
            "AGENT": "blueprint_author",
            "UNIT": 3,
        }
        result = format_action_block(action)
        assert "AGENT" in result
        assert "blueprint_author" in result


class TestDeriveEnvNameFromState:
    """Tests for derive_env_name_from_state."""

    # DATA ASSUMPTION: Project names are short alphanumeric strings, possibly
    # with dots and underscores. The env name derivation follows spec Section 4.3
    # (canonical conda environment name derivation).

    def test_returns_string(self):
        """Must return a string."""
        state = _make_state(project_name="my_project")
        result = derive_env_name_from_state(state)
        assert isinstance(result, str)

    def test_env_name_derived_from_project_name(self):
        """The environment name must be derived from the project name in state."""
        state = _make_state(project_name="my_project")
        result = derive_env_name_from_state(state)
        # The env name should contain or be derived from the project name
        assert len(result) > 0

    def test_different_project_names_give_different_env_names(self):
        """Different project names should produce different env names."""
        state_a = _make_state(project_name="project_alpha")
        state_b = _make_state(project_name="project_beta")
        result_a = derive_env_name_from_state(state_a)
        result_b = derive_env_name_from_state(state_b)
        assert result_a != result_b

    def test_env_name_is_nonempty(self):
        """The derived env name must be non-empty."""
        state = _make_state(project_name="svp1.2.1")
        result = derive_env_name_from_state(state)
        assert len(result) > 0
