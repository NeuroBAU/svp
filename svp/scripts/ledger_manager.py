"""Re-export shim for ledger_manager - imports from svp_core.

This module re-exports all symbols from svp_core.ledger_manager for
backward compatibility with both package imports (tests) and bare imports
(project workspaces).
"""

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

__all__ = [
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
]
