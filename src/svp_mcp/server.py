"""MCP server for SVP using the official MCP Python SDK."""

from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from svp_app import (
    load_state,
    save_state,
    validate_state,
    route,
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
    format_action_block,
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
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
    return state.to_dict()


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
    return new_state.to_dict()


@mcp.tool()
def format_action_block_tool(action: dict) -> str:
    """Format an action dictionary as the SVP action block text.

    Args:
        action: Action dictionary with ACTION, AGENT, MESSAGE, etc.

    Returns:
        Formatted action block string.
    """
    return format_action_block(action)


@mcp.tool()
def save_state_tool(project_root: str, state: dict) -> dict:
    """Save the pipeline state to disk.

    Args:
        project_root: Path to the project root directory.
        state: Pipeline state dictionary (from to_dict()).

    Returns:
        Success: {"ok": true, "state": {...}}
        Failure: {"ok": false, "error": "...", "error_type": "..."}
    """
    try:
        from svp_core import PipelineState

        state_obj = PipelineState.from_dict(state)
        save_state(state_obj, Path(project_root))
        return {"ok": True, "state": state}
    except Exception as e:
        return {"ok": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def dispatch_gate_response_tool(
    project_root: str,
    gate_id: str,
    response: str,
) -> dict:
    """Dispatch a human gate response.

    Args:
        project_root: Path to the project root directory.
        gate_id: The gate identifier (e.g., "gate_0_1_hook_activation").
        response: The human's response (must be in GATE_VOCABULARY).

    Returns:
        Success: {"ok": true, "state": {...}}
        Failure: {"ok": false, "error": "...", "error_type": "..."}
    """
    try:
        state = load_state(Path(project_root))
        new_state = dispatch_gate_response(
            state,
            gate_id,
            response,
            Path(project_root),
        )
        return {"ok": True, "state": new_state.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def dispatch_agent_status_tool(
    project_root: str,
    agent_type: str,
    status_line: str,
    phase: str,
    unit: Optional[int] = None,
) -> dict:
    """Dispatch an agent status line.

    Args:
        project_root: Path to the project root directory.
        agent_type: The agent type that produced the status.
        status_line: The status line from agent output.
        phase: The phase that produced the status.
        unit: Unit number if applicable.

    Returns:
        Success: {"ok": true, "state": {...}}
        Failure: {"ok": false, "error": "...", "error_type": "..."}
    """
    try:
        state = load_state(Path(project_root))
        new_state = dispatch_agent_status(
            state,
            agent_type,
            status_line,
            unit,
            phase,
            Path(project_root),
        )
        return {"ok": True, "state": new_state.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def dispatch_command_status_tool(
    project_root: str,
    status_line: str,
    phase: str,
    unit: Optional[int] = None,
) -> dict:
    """Dispatch a command status line.

    Args:
        project_root: Path to the project root directory.
        status_line: The status line from command output.
        phase: The phase that produced the status.
        unit: Unit number if applicable.

    Returns:
        Success: {"ok": true, "state": {...}}
        Failure: {"ok": false, "error": "...", "error_type": "..."}
    """
    try:
        state = load_state(Path(project_root))
        new_state = dispatch_command_status(
            state,
            status_line,
            unit,
            phase,
            Path(project_root),
        )
        return {"ok": True, "state": new_state.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def explain_next_action_tool(project_root: str) -> dict:
    """Explain the next action in plain language.

    Provides user-friendly guidance including:
    - action type (invoke_agent, human_gate, run_command)
    - target (agent or gate)
    - phase for dispatch tool
    - post command if available
    - recommended dispatch tool
    - valid status lines or gate responses
    - plain-language guidance

    Args:
        project_root: Path to the project root directory.

    Returns:
        Dictionary with action explanation.
    """
    try:
        state = load_state(Path(project_root))
        action = route(state, Path(project_root))

        action_type = action.get("ACTION", "unknown")
        target = action.get("AGENT") or action.get("GATE") or action.get("COMMAND")
        post_cmd = action.get("POST")
        phase = state.sub_stage  # Get phase from state, not action

        valid_responses = []
        recommended_tool = None
        guidance = None

        if action_type == "human_gate":
            gate_id = action.get("GATE")
            valid_responses = GATE_VOCABULARY.get(gate_id, [])
            recommended_tool = "dispatch_gate_response_tool"
            guidance = (
                f"Waiting for human decision on gate '{gate_id}'. "
                f"Valid responses: {', '.join(valid_responses)}. "
                f"Use dispatch_gate_response_tool with gate_id='{gate_id}' and one of these responses."
            )

        elif action_type == "invoke_agent":
            agent = action.get("AGENT")
            valid_responses = AGENT_STATUS_LINES.get(agent, [])
            recommended_tool = "dispatch_agent_status_tool"
            phase_hint = f" phase='{phase}'" if phase else ""
            guidance = (
                f"Run the {agent} agent. After it completes, "
                f"use dispatch_agent_status_tool with agent_type='{agent}'{phase_hint}. "
                f"Valid status lines: {', '.join(valid_responses)}."
            )

        elif action_type == "run_command":
            cmd = action.get("COMMAND", "")
            recommended_tool = "dispatch_command_status_tool"
            guidance = (
                f"Run command: {cmd}. "
                f"After it completes, use dispatch_command_status_tool."
            )

        elif action_type == "session_boundary":
            guidance = (
                "Session boundary reached. Use route_tool again to get the next action."
            )

        elif action_type == "pipeline_complete":
            guidance = "Pipeline is complete. No further actions."

        else:
            guidance = f"Unknown action type: {action_type}"

        return {
            "action_type": action_type,
            "target": target,
            "phase": phase,
            "post_command": post_cmd,
            "recommended_tool": recommended_tool,
            "valid_responses": valid_responses,
            "guidance": guidance,
        }
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


if __name__ == "__main__":
    main()


def main():
    """Entry point for the SVP MCP server."""
    mcp.run()
