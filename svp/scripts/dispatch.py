"""Compatibility shim for dispatch functions."""

from svp_core.dispatch import (  # noqa: F401
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
    dispatch_status,
)

__all__ = [
    "dispatch_status",
    "dispatch_gate_response",
    "dispatch_agent_status",
    "dispatch_command_status",
]
