"""Tests for MCP server tools."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestInitializeStateTool:
    """Tests for initialize_state_tool."""

    @patch("svp_mcp.server.create_initial_state")
    def test_success(self, mock_create_initial_state):
        """initialize_state_tool should return initial state dict."""
        from svp_mcp.server import initialize_state_tool

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "stage": "0",
            "sub_stage": "hook_activation",
            "project_name": "demo",
        }
        mock_create_initial_state.return_value = mock_state

        result = initialize_state_tool("demo")

        assert result["ok"] is True
        assert result["state"]["stage"] == "0"
        mock_create_initial_state.assert_called_once_with("demo")

    @patch("svp_mcp.server.create_initial_state")
    def test_failure(self, mock_create_initial_state):
        """initialize_state_tool should return ok=False on error."""
        from svp_mcp.server import initialize_state_tool

        mock_create_initial_state.side_effect = ValueError("bad project name")

        result = initialize_state_tool("")

        assert result["ok"] is False
        assert "bad project name" in result["error"]
        assert result["error_type"] == "ValueError"


class TestCreateProjectTool:
    """Tests for create_project_tool."""

    def test_success(self, tmp_path):
        """create_project_tool should create root and .svp scaffolding."""
        from svp_mcp.server import create_project_tool

        project_root = tmp_path / "demo_project"
        result = create_project_tool(str(project_root))

        assert result["ok"] is True
        assert result["project_root"] == str(project_root)
        assert project_root.is_dir()
        assert (project_root / ".svp").is_dir()
        assert (project_root / ".svp" / "markers").is_dir()
        assert str(project_root / ".svp") in result["created_paths"]

    def test_failure_when_project_exists(self, tmp_path):
        """create_project_tool should fail if project directory already exists."""
        from svp_mcp.server import create_project_tool

        project_root = tmp_path / "demo_project"
        project_root.mkdir()

        result = create_project_tool(str(project_root))

        assert result["ok"] is False
        assert result["error_type"] == "FileExistsError"
        assert "already exists" in result["error"]


class TestLoadStateTool:
    """Tests for load_state_tool."""

    @patch("svp_mcp.server.load_state")
    def test_returns_state_as_dict(self, mock_load_state):
        """load_state_tool should return state as dictionary."""
        from svp_mcp.server import load_state_tool

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {"stage": "0", "sub_stage": None}
        mock_load_state.return_value = mock_state

        result = load_state_tool("/tmp/project")

        assert result == {"stage": "0", "sub_stage": None}
        mock_load_state.assert_called_once_with(Path("/tmp/project"))


class TestValidateStateTool:
    """Tests for validate_state_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.validate_state")
    def test_valid_state(self, mock_validate, mock_load_state):
        """validate_state_tool should return valid=True for valid state."""
        from svp_mcp.server import validate_state_tool

        mock_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_validate.return_value = []

        result = validate_state_tool("/tmp/project")

        assert result["valid"] is True
        assert result["errors"] == []

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.validate_state")
    def test_invalid_state(self, mock_validate, mock_load_state):
        """validate_state_tool should return valid=False for invalid state."""
        from svp_mcp.server import validate_state_tool

        mock_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_validate.return_value = ["error1", "error2"]

        result = validate_state_tool("/tmp/project")

        assert result["valid"] is False
        assert result["errors"] == ["error1", "error2"]


class TestRouteTool:
    """Tests for route_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    def test_returns_action_dict(self, mock_route, mock_load_state):
        """route_tool should return action as dictionary."""
        from svp_mcp.server import route_tool

        mock_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_route.return_value = {"ACTION": "human_gate", "GATE": "gate_0_1"}

        result = route_tool("/tmp/project")

        assert result == {"ACTION": "human_gate", "GATE": "gate_0_1"}
        mock_route.assert_called_once_with(mock_state, Path("/tmp/project"))


class TestDispatchStatusTool:
    """Tests for dispatch_status_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_status")
    def test_returns_new_state(self, mock_dispatch, mock_load_state):
        """dispatch_status_tool should return new state as dictionary."""
        from svp_mcp.server import dispatch_status_tool

        mock_state = MagicMock()
        mock_new_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_dispatch.return_value = mock_new_state
        mock_new_state.to_dict.return_value = {"stage": "1", "sub_stage": "dialog"}

        result = dispatch_status_tool(
            "/tmp/project", "IMPLEMENTATION_COMPLETE", "implementation_dialog"
        )

        assert result == {"stage": "1", "sub_stage": "dialog"}
        mock_dispatch.assert_called_once()
        args, kwargs = mock_dispatch.call_args
        assert args[0] == mock_state
        assert args[1] == "IMPLEMENTATION_COMPLETE"
        assert kwargs["phase"] == "implementation_dialog"


class TestFormatActionBlockTool:
    """Tests for format_action_block_tool."""

    @patch("svp_mcp.server.format_action_block")
    def test_returns_formatted_string(self, mock_format):
        """format_action_block_tool should return formatted string."""
        from svp_mcp.server import format_action_block_tool

        mock_format.return_value = "ACTION: human_gate\nGATE: gate_0_1\nMESSAGE: test"

        action = {"ACTION": "human_gate", "GATE": "gate_0_1", "MESSAGE": "test"}
        result = format_action_block_tool(action)

        assert result == "ACTION: human_gate\nGATE: gate_0_1\nMESSAGE: test"
        mock_format.assert_called_once_with(action)


class TestSaveStateTool:
    """Tests for save_state_tool."""

    @patch("svp_mcp.server.save_state")
    def test_success(self, mock_save):
        """save_state_tool should return ok=True on success."""
        from svp_mcp.server import save_state_tool
        from svp_core import PipelineState

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {"stage": "0"}

        with patch.object(PipelineState, "from_dict", return_value=mock_state):
            state_dict = {"stage": "0", "sub_stage": "hook_activation"}
            result = save_state_tool("/tmp/project", state_dict)

        assert result["ok"] is True
        assert result["state"] == state_dict

    @patch("svp_mcp.server.save_state")
    def test_failure(self, mock_save):
        """save_state_tool should return ok=False on failure."""
        from svp_mcp.server import save_state_tool
        from svp_core import PipelineState

        mock_state = MagicMock()
        mock_save.side_effect = IOError("Permission denied")

        with patch.object(PipelineState, "from_dict", return_value=mock_state):
            state_dict = {"stage": "0"}
            result = save_state_tool("/tmp/project", state_dict)

        assert result["ok"] is False
        assert "Permission denied" in result["error"]
        assert result["error_type"] == "OSError"


class TestDispatchGateResponseTool:
    """Tests for dispatch_gate_response_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_gate_response")
    def test_success(self, mock_dispatch, mock_load_state):
        """dispatch_gate_response_tool should return ok=True on success."""
        from svp_mcp.server import dispatch_gate_response_tool

        mock_state = MagicMock()
        mock_new_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_dispatch.return_value = mock_new_state
        mock_new_state.to_dict.return_value = {"stage": "1"}

        result = dispatch_gate_response_tool("/tmp/project", "gate_0_1", "APPROVE")

        assert result["ok"] is True
        assert result["state"] == {"stage": "1"}

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_gate_response")
    def test_failure(self, mock_dispatch, mock_load_state):
        """dispatch_gate_response_tool should return ok=False on error."""
        from svp_mcp.server import dispatch_gate_response_tool

        mock_dispatch.side_effect = ValueError("Invalid gate response")

        result = dispatch_gate_response_tool("/tmp/project", "gate_0_1", "INVALID")

        assert result["ok"] is False
        assert "Invalid gate response" in result["error"]
        assert result["error_type"] == "ValueError"


class TestDispatchAgentStatusTool:
    """Tests for dispatch_agent_status_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_agent_status")
    def test_success(self, mock_dispatch, mock_load_state):
        """dispatch_agent_status_tool should return ok=True on success."""
        from svp_mcp.server import dispatch_agent_status_tool

        mock_state = MagicMock()
        mock_new_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_dispatch.return_value = mock_new_state
        mock_new_state.to_dict.return_value = {"stage": "2"}

        result = dispatch_agent_status_tool(
            "/tmp/project",
            "implementation_agent",
            "IMPLEMENTATION_COMPLETE",
            "implementation",
        )

        assert result["ok"] is True
        assert result["state"] == {"stage": "2"}

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_agent_status")
    def test_failure(self, mock_dispatch, mock_load_state):
        """dispatch_agent_status_tool should return ok=False on error."""
        from svp_mcp.server import dispatch_agent_status_tool

        mock_dispatch.side_effect = ValueError("Unknown status")

        result = dispatch_agent_status_tool(
            "/tmp/project", "test", "UNKNOWN_STATUS", "test"
        )

        assert result["ok"] is False
        assert "Unknown status" in result["error"]
        assert result["error_type"] == "ValueError"


class TestDispatchCommandStatusTool:
    """Tests for dispatch_command_status_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_command_status")
    def test_success(self, mock_dispatch, mock_load_state):
        """dispatch_command_status_tool should return ok=True on success."""
        from svp_mcp.server import dispatch_command_status_tool

        mock_state = MagicMock()
        mock_new_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_dispatch.return_value = mock_new_state
        mock_new_state.to_dict.return_value = {"stage": "3"}

        result = dispatch_command_status_tool(
            "/tmp/project", "COMMAND_SUCCEEDED", "test"
        )

        assert result["ok"] is True
        assert result["state"] == {"stage": "3"}

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.dispatch_command_status")
    def test_failure(self, mock_dispatch, mock_load_state):
        """dispatch_command_status_tool should return ok=False on error."""
        from svp_mcp.server import dispatch_command_status_tool

        mock_dispatch.side_effect = ValueError("Unknown command status")

        result = dispatch_command_status_tool("/tmp/project", "UNKNOWN_COMMAND", "test")

        assert result["ok"] is False
        assert "Unknown command status" in result["error"]
        assert result["error_type"] == "ValueError"


class TestExplainNextActionTool:
    """Tests for explain_next_action_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    def test_explain_human_gate(self, mock_route, mock_load_state):
        """explain_next_action_tool should explain human gate with valid responses."""
        from svp_mcp.server import explain_next_action_tool

        mock_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "human_gate",
            "GATE": "gate_0_1_hook_activation",
            "MESSAGE": "Welcome to SVP!",
        }

        result = explain_next_action_tool("/tmp/project")

        assert result["action_type"] == "human_gate"
        assert result["target"] == "gate_0_1_hook_activation"
        assert result["recommended_tool"] == "dispatch_gate_response_tool"
        assert len(result["valid_responses"]) > 0
        assert "guidance" in result

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    def test_explain_invoke_agent(self, mock_route, mock_load_state):
        """explain_next_action_tool should explain invoke_agent with status lines."""
        from svp_mcp.server import explain_next_action_tool

        mock_state = MagicMock()
        mock_state.sub_stage = "stakeholder_dialog"
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "invoke_agent",
            "AGENT": "stakeholder_dialog",
            "PHASE": "stakeholder_dialog",
            "MESSAGE": "Starting stakeholder dialog",
        }

        result = explain_next_action_tool("/tmp/project")

        assert result["action_type"] == "invoke_agent"
        assert result["target"] == "stakeholder_dialog"
        assert result["phase"] == "stakeholder_dialog"
        assert result["recommended_tool"] == "dispatch_agent_status_tool"
        assert len(result["valid_responses"]) > 0
        assert "stakeholder_dialog" in result["guidance"]
        assert "phase='stakeholder_dialog'" in result["guidance"]

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    def test_explain_run_command(self, mock_route, mock_load_state):
        """explain_next_action_tool should explain run_command."""
        from svp_mcp.server import explain_next_action_tool

        mock_state = MagicMock()
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "run_command",
            "COMMAND": "pytest tests/",
            "MESSAGE": "Running tests",
        }

        result = explain_next_action_tool("/tmp/project")

        assert result["action_type"] == "run_command"
        assert result["target"] == "pytest tests/"
        assert result["recommended_tool"] == "dispatch_command_status_tool"
        assert result["valid_responses"] == [
            "TESTS_PASSED",
            "TESTS_FAILED",
            "TESTS_ERROR",
            "COMMAND_SUCCEEDED",
            "COMMAND_FAILED",
        ]
        assert "guidance" in result


class TestApplyNextActionTool:
    """Tests for apply_next_action_tool."""

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    @patch("svp_mcp.server.dispatch_gate_response")
    def test_apply_human_gate_success(
        self, mock_dispatch_gate, mock_route, mock_load_state
    ):
        """apply_next_action_tool should dispatch human gate response."""
        from svp_mcp.server import apply_next_action_tool

        mock_state = MagicMock()
        mock_state.sub_stage = "hook_activation"
        mock_state.stage = "0"
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "human_gate",
            "GATE": "gate_0_1_hook_activation",
            "UNIT": None,
        }

        mock_new_state = MagicMock()
        mock_new_state.to_dict.return_value = {
            "stage": "0",
            "sub_stage": "project_context",
        }
        mock_dispatch_gate.return_value = mock_new_state

        result = apply_next_action_tool(
            "/tmp/project",
            response="HOOKS ACTIVATED",
        )

        assert result["ok"] is True
        assert result["applied_action_type"] == "human_gate"
        assert result["used_tool"] == "dispatch_gate_response_tool"
        assert result["phase"] == "hook_activation"
        assert result["response"] == "HOOKS ACTIVATED"
        assert result["state"] == {"stage": "0", "sub_stage": "project_context"}

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    @patch("svp_mcp.server.dispatch_agent_status")
    def test_apply_invoke_agent_success_with_phase_fallback(
        self, mock_dispatch_agent, mock_route, mock_load_state
    ):
        """apply_next_action_tool should infer phase for invoke_agent when sub_stage is None."""
        from svp_mcp.server import apply_next_action_tool

        mock_state = MagicMock()
        mock_state.sub_stage = None
        mock_state.stage = "1"
        mock_state.debug_session = None
        mock_state.fix_ladder_position = None
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "invoke_agent",
            "AGENT": "stakeholder_dialog",
            "UNIT": None,
        }

        mock_new_state = MagicMock()
        mock_new_state.to_dict.return_value = {"stage": "1", "sub_stage": "approval"}
        mock_dispatch_agent.return_value = mock_new_state

        result = apply_next_action_tool(
            "/tmp/project",
            response="SPEC_DRAFT_COMPLETE",
        )

        assert result["ok"] is True
        assert result["applied_action_type"] == "invoke_agent"
        assert result["used_tool"] == "dispatch_agent_status_tool"
        assert result["phase"] == "stakeholder_dialog"
        assert result["response"] == "SPEC_DRAFT_COMPLETE"
        assert result["state"] == {"stage": "1", "sub_stage": "approval"}
        mock_dispatch_agent.assert_called_once()
        args = mock_dispatch_agent.call_args[0]
        assert args[1] == "stakeholder_dialog"
        assert args[2] == "SPEC_DRAFT_COMPLETE"
        assert args[4] == "stakeholder_dialog"

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    @patch("svp_mcp.server.dispatch_command_status")
    def test_apply_run_command_success(
        self, mock_dispatch_command, mock_route, mock_load_state
    ):
        """apply_next_action_tool should dispatch run_command response."""
        from svp_mcp.server import apply_next_action_tool

        mock_state = MagicMock()
        mock_state.sub_stage = "infrastructure_setup"
        mock_state.stage = "pre_stage_3"
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "run_command",
            "COMMAND": "conda run -n test python scripts/setup_infrastructure.py",
            "UNIT": None,
        }

        mock_new_state = MagicMock()
        mock_new_state.to_dict.return_value = {"stage": "3", "sub_stage": None}
        mock_dispatch_command.return_value = mock_new_state

        result = apply_next_action_tool(
            "/tmp/project",
            response="COMMAND_SUCCEEDED",
        )

        assert result["ok"] is True
        assert result["applied_action_type"] == "run_command"
        assert result["used_tool"] == "dispatch_command_status_tool"
        assert result["phase"] == "infrastructure_setup"
        assert result["response"] == "COMMAND_SUCCEEDED"
        assert result["state"] == {"stage": "3", "sub_stage": None}

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    @patch("svp_mcp.server.dispatch_command_status")
    def test_apply_run_command_invalid_response(
        self, mock_dispatch_command, mock_route, mock_load_state
    ):
        """apply_next_action_tool should reject invalid run_command responses."""
        from svp_mcp.server import apply_next_action_tool

        mock_state = MagicMock()
        mock_state.sub_stage = "infrastructure_setup"
        mock_state.stage = "pre_stage_3"
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "run_command",
            "COMMAND": "conda run -n test python scripts/setup_infrastructure.py",
            "UNIT": None,
        }

        result = apply_next_action_tool(
            "/tmp/project",
            response="NOT_A_VALID_STATUS",
        )

        assert result["ok"] is False
        assert result["expected_action_type"] == "run_command"
        assert result["phase"] == "infrastructure_setup"
        assert "TESTS_PASSED" in result["valid_responses"]
        assert "COMMAND_SUCCEEDED" in result["valid_responses"]
        mock_dispatch_command.assert_not_called()

    @patch("svp_mcp.server.load_state")
    @patch("svp_mcp.server.route")
    def test_apply_action_type_mismatch(self, mock_route, mock_load_state):
        """apply_next_action_tool should fail when expected_action_type mismatches."""
        from svp_mcp.server import apply_next_action_tool

        mock_state = MagicMock()
        mock_state.sub_stage = "hook_activation"
        mock_state.stage = "0"
        mock_load_state.return_value = mock_state
        mock_route.return_value = {
            "ACTION": "human_gate",
            "GATE": "gate_0_1_hook_activation",
            "UNIT": None,
        }

        result = apply_next_action_tool(
            "/tmp/project",
            response="HOOKS ACTIVATED",
            expected_action_type="invoke_agent",
        )

        assert result["ok"] is False
        assert result["error_type"] == "ActionTypeMismatch"
        assert result["expected_action_type"] == "human_gate"
