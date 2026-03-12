"""MCP server for SVP using the official MCP Python SDK."""

from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from svp_app import (
    load_state,
    validate_state,
    route,
    dispatch_status,
    format_action_block,
)

mcp = FastMCP("SVP")


@mcp.tool()
def load_state_tool(project_root: str) -> dict:
    """Load the current SVP pipeline state.

    Args:
        project_root: Path to the project root directory.

    Returns:
        Dictionary representation of the pipeline state.
    """
    state = load_state(Path(project_root))
    return state.model_dump(mode="json")


@mcp.tool()
def validate_state_tool(project_root: str) -> dict:
    """Validate the current SVP pipeline state.

    Args:
        project_root: Path to the project root directory.

    Returns:
        Dictionary with 'valid' boolean and 'errors' list.
    """
    state = load_state(Path(project_root))
    errors = validate_state(state)
    return {"valid": len(errors) == 0, "errors": errors}


@mcp.tool()
def route_tool(project_root: str) -> dict:
    """Determine the next action for the current pipeline state.

    Args:
        project_root: Path to the project root directory.

    Returns:
        Action dictionary with ACTION, AGENT, MESSAGE, etc.
    """
    state = load_state(Path(project_root))
    action = route(state, Path(project_root))
    return action


@mcp.tool()
def dispatch_status_tool(
    project_root: str,
    status_line: str,
    phase: str,
    unit: Optional[int] = None,
    gate_id: Optional[str] = None,
) -> dict:
    """Dispatch a status line and return the new pipeline state.

    Args:
        project_root: Path to the project root directory.
        status_line: The status line from agent output.
        phase: The phase that produced the status.
        unit: Unit number if applicable.
        gate_id: Gate ID if applicable.

    Returns:
        Dictionary representation of the new pipeline state.
    """
    state = load_state(Path(project_root))
    new_state = dispatch_status(
        state,
        status_line,
        phase=phase,
        unit=unit,
        gate_id=gate_id,
        project_root=Path(project_root),
    )
    return new_state.model_dump(mode="json")


@mcp.tool()
def format_action_block_tool(action: dict) -> str:
    """Format an action dictionary as the SVP action block text.

    Args:
        action: Action dictionary with ACTION, AGENT, MESSAGE, etc.

    Returns:
        Formatted action block string.
    """
    return format_action_block(action)


if __name__ == "__main__":
    mcp.run()
