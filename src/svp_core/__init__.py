"""svp_core - host-agnostic core business logic for SVP."""

from importlib import import_module


_EXPORTS = {
    # pipeline_state
    "STAGES": "svp_core.pipeline_state",
    "SUB_STAGES_STAGE_0": "svp_core.pipeline_state",
    "FIX_LADDER_POSITIONS": "svp_core.pipeline_state",
    "DebugSession": "svp_core.pipeline_state",
    "PipelineState": "svp_core.pipeline_state",
    "create_initial_state": "svp_core.pipeline_state",
    "load_state": "svp_core.pipeline_state",
    "save_state": "svp_core.pipeline_state",
    "validate_state": "svp_core.pipeline_state",
    "recover_state_from_markers": "svp_core.pipeline_state",
    "get_stage_display": "svp_core.pipeline_state",
    # ledger_manager
    "LedgerEntry": "svp_core.ledger_manager",
    "append_entry": "svp_core.ledger_manager",
    "read_ledger": "svp_core.ledger_manager",
    "clear_ledger": "svp_core.ledger_manager",
    "rename_ledger": "svp_core.ledger_manager",
    "get_ledger_size_chars": "svp_core.ledger_manager",
    "check_ledger_capacity": "svp_core.ledger_manager",
    "extract_tagged_lines": "svp_core.ledger_manager",
    "compact_ledger": "svp_core.ledger_manager",
    "write_hint_entry": "svp_core.ledger_manager",
    # action
    "ACTION_TYPES": "svp_core.action",
    "REMINDER_TEXT": "svp_core.action",
    "_invoke_agent_action": "svp_core.action",
    "_run_command_action": "svp_core.action",
    "_human_gate_action": "svp_core.action",
    "_session_boundary_action": "svp_core.action",
    "_pipeline_complete_action": "svp_core.action",
    "format_action_block": "svp_core.action",
    # vocabulary
    "GATE_VOCABULARY": "svp_core.vocabulary",
    "AGENT_STATUS_LINES": "svp_core.vocabulary",
    "CROSS_AGENT_STATUS": "svp_core.vocabulary",
    "COMMAND_STATUS_PATTERNS": "svp_core.vocabulary",
    # dispatch
    "dispatch_status": "svp_core.dispatch",
    "dispatch_gate_response": "svp_core.dispatch",
    "dispatch_agent_status": "svp_core.dispatch",
    "dispatch_command_status": "svp_core.dispatch",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module 'svp_core' has no attribute {name!r}")
    module = import_module(_EXPORTS[name])
    return getattr(module, name)
