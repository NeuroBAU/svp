"""SVP application layer - host-agnostic operations.

This module exposes stable operations that can be used by any host
(Claude Code, MCP server, Gemini CLI, OpenCode, etc.) without depending
on CLI wrappers or host-specific adapters.
"""

from svp_core import (
    load_state,
    save_state,
    create_initial_state,
    validate_state,
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
    format_action_block,
    PipelineState,
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    COMMAND_STATUS_PATTERNS,
)
from svp_core.router import route

from svp.scripts.svp_launcher import (
    create_project_directory,
    write_initial_state,
    write_default_config,
    set_filesystem_permissions,
)

__all__ = [
    # State
    "PipelineState",
    "load_state",
    "save_state",
    "create_initial_state",
    "validate_state",
    # Routing
    "route",
    "dispatch_status",
    "dispatch_gate_response",
    "dispatch_agent_status",
    "dispatch_command_status",
    "format_action_block",
    # Vocabulary
    "GATE_VOCABULARY",
    "AGENT_STATUS_LINES",
    "COMMAND_STATUS_PATTERNS",
    # Project setup
    "create_project_directory",
    "write_initial_state",
    "write_default_config",
    "set_filesystem_permissions",
]
