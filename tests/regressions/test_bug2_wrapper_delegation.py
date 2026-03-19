"""Bug 2 regression: CLI wrapper scripts must delegate to canonical functions.

Wrapper scripts (cmd_clean.py, cmd_quit.py, cmd_status.py) must import
and call canonical functions from cmd_save.py rather than reimplementing
logic inline.
"""

import ast
from pathlib import Path


def _get_scripts_dir() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    d = root / "svp" / "scripts"
    if d.is_dir():
        return d
    return root / "scripts"


def test_cmd_clean_delegates_to_cmd_save():
    """cmd_clean.py must import from cmd_save."""
    source = (_get_scripts_dir() / "cmd_clean.py").read_text()
    tree = ast.parse(source)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    cmd_save_imports = [
        node
        for node in imports
        if isinstance(node, ast.ImportFrom) and node.module == "cmd_save"
    ]
    assert len(cmd_save_imports) > 0, "cmd_clean.py must import from cmd_save"


def test_cmd_quit_delegates_to_cmd_save():
    """cmd_quit.py must import from cmd_save."""
    source = (_get_scripts_dir() / "cmd_quit.py").read_text()
    tree = ast.parse(source)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "cmd_save"
    ]
    assert len(imports) > 0, "cmd_quit.py must import from cmd_save"


def test_cmd_status_delegates_to_cmd_save():
    """cmd_status.py must import from cmd_save."""
    source = (_get_scripts_dir() / "cmd_status.py").read_text()
    tree = ast.parse(source)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "cmd_save"
    ]
    assert len(imports) > 0, "cmd_status.py must import from cmd_save"
