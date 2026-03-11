"""svp_core - Host-agnostic core business logic for SVP."""

from svp_core.pipeline_state import (
    STAGES,
    SUB_STAGES_STAGE_0,
    FIX_LADDER_POSITIONS,
    DebugSession,
    PipelineState,
    create_initial_state,
    load_state,
    save_state,
    validate_state,
    recover_state_from_markers,
    get_stage_display,
)

from svp_core.ledger_manager import (
    LedgerEntry,
    append_entry,
    read_ledger,
    clear_ledger,
    rename_ledger,
    get_ledger_size_chars,
    check_ledger_capacity,
    extract_tagged_lines,
    compact_ledger,
    write_hint_entry,
)

from svp_core.action import (
    ACTION_TYPES,
    REMINDER_TEXT,
    _invoke_agent_action,
    _run_command_action,
    _human_gate_action,
    _session_boundary_action,
    _pipeline_complete_action,
    format_action_block,
)

from svp_core.vocabulary import (
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
)

from svp_core.dispatch import (
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
)

__all__ = [
    # pipeline_state
    "STAGES",
    "SUB_STAGES_STAGE_0",
    "FIX_LADDER_POSITIONS",
    "DebugSession",
    "PipelineState",
    "create_initial_state",
    "load_state",
    "save_state",
    "validate_state",
    "recover_state_from_markers",
    "get_stage_display",
    # ledger_manager
    "LedgerEntry",
    "append_entry",
    "read_ledger",
    "clear_ledger",
    "rename_ledger",
    "get_ledger_size_chars",
    "check_ledger_capacity",
    "extract_tagged_lines",
    "compact_ledger",
    "write_hint_entry",
    # action
    "ACTION_TYPES",
    "REMINDER_TEXT",
    "_invoke_agent_action",
    "_run_command_action",
    "_human_gate_action",
    "_session_boundary_action",
    "_pipeline_complete_action",
    "format_action_block",
    # vocabulary
    "GATE_VOCABULARY",
    "AGENT_STATUS_LINES",
    "CROSS_AGENT_STATUS",
    "COMMAND_STATUS_PATTERNS",
    # dispatch
    "dispatch_status",
    "dispatch_gate_response",
    "dispatch_agent_status",
    "dispatch_command_status",
]
