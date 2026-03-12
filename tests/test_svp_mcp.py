"""Tests for MCP server tools."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestLoadStateTool:
    """Tests for load_state_tool."""

    @patch("svp_mcp.server.load_state")
    def test_returns_state_as_dict(self, mock_load_state):
        """load_state_tool should return state as dictionary."""
        from svp_mcp.server import load_state_tool

        mock_state = MagicMock()
        mock_state.model_dump.return_value = {"stage": "0", "sub_stage": None}
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
        mock_new_state.model_dump.return_value = {"stage": "1", "sub_stage": "dialog"}

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
        mock_state.model_dump.return_value = {"stage": "0"}

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
        mock_new_state.model_dump.return_value = {"stage": "1"}

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
        mock_new_state.model_dump.return_value = {"stage": "2"}

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
        mock_new_state.model_dump.return_value = {"stage": "3"}

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
