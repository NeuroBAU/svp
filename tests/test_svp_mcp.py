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
