"""Bug 2 regression: CLI wrapper scripts must delegate to canonical functions.

Wrapper scripts (cmd_clean.py, cmd_quit.py, cmd_status.py) must import
and call canonical functions from sync_debug_docs.py rather than
reimplementing logic inline.

Updated for Bug S3-98: cmd_save.py was a full duplicate of sync_debug_docs.py.
All Unit 16 functions now live in sync_debug_docs.py (derived from stub.py).
Wrappers import from sync_debug_docs, and cmd_save.py re-exports for
backward compatibility.
"""

import ast
from pathlib import Path


def _get_scripts_dir() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    d = root / "svp" / "scripts"
    if d.is_dir():
        return d
    return root / "scripts"


def _has_import_from(source: str, module: str) -> bool:
    """Check if source imports from the given module."""
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.ImportFrom) and node.module == module
        for node in ast.walk(tree)
    )


def test_cmd_clean_delegates_to_sync_debug_docs():
    """cmd_clean.py must import from sync_debug_docs."""
    source = (_get_scripts_dir() / "cmd_clean.py").read_text()
    assert _has_import_from(source, "sync_debug_docs"), (
        "cmd_clean.py must import from sync_debug_docs"
    )


def test_cmd_quit_delegates_to_sync_debug_docs():
    """cmd_quit.py must import from sync_debug_docs."""
    source = (_get_scripts_dir() / "cmd_quit.py").read_text()
    assert _has_import_from(source, "sync_debug_docs"), (
        "cmd_quit.py must import from sync_debug_docs"
    )


def test_cmd_status_delegates_to_sync_debug_docs():
    """cmd_status.py must import from sync_debug_docs."""
    source = (_get_scripts_dir() / "cmd_status.py").read_text()
    assert _has_import_from(source, "sync_debug_docs"), (
        "cmd_status.py must import from sync_debug_docs"
    )


def test_cmd_save_reexports_from_sync_debug_docs():
    """cmd_save.py must re-export from sync_debug_docs (backward compat wrapper)."""
    source = (_get_scripts_dir() / "cmd_save.py").read_text()
    assert _has_import_from(source, "sync_debug_docs"), (
        "cmd_save.py must re-export from sync_debug_docs"
    )
