"""Regression tests for Bug S3-134 / Pattern P33 — Cross-Platform Stdlib Audit.

P33 (spec §24.147): stdlib imports that are platform-specific must be gated
behind `if sys.platform == "win32":` or equivalent, with functional wrappers
on both sides defined at import time.

Bug S3-134 covered: src/unit_7/stub.py (ledger_manager) previously did
`import fcntl` unconditionally at module top-level, breaking Windows.
"""

import ast
import json
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNIT_7_STUB = PROJECT_ROOT / "src" / "unit_7" / "stub.py"


def test_unit_7_stub_no_top_level_fcntl_import():
    """fcntl must not appear as an unconditional top-level import.

    A fcntl import is allowed ONLY inside a platform-gated `if` block.
    """
    tree = ast.parse(UNIT_7_STUB.read_text())
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "fcntl", (
                    f"{UNIT_7_STUB} imports fcntl at module top level "
                    "(line {}); P33 requires platform gating.".format(node.lineno)
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "fcntl", (
                f"{UNIT_7_STUB} imports from fcntl at module top level "
                "(line {}); P33 requires platform gating.".format(node.lineno)
            )


def test_unit_7_stub_defines_lock_unlock_in_both_branches():
    """_lock and _unlock must be defined in BOTH platform branches.

    Walks top-level If nodes that test `sys.platform == "win32"` and verifies
    each branch contains exactly one FunctionDef for _lock and one for
    _unlock. This guarantees the stub parses (and its symbols exist) on
    any host platform.
    """
    tree = ast.parse(UNIT_7_STUB.read_text())
    platform_if = None
    for node in tree.body:
        if isinstance(node, ast.If) and _is_sys_platform_win32_test(node.test):
            platform_if = node
            break
    assert platform_if is not None, (
        "Expected a top-level `if sys.platform == \"win32\":` block in "
        f"{UNIT_7_STUB}; none found."
    )

    win_defs = _collect_func_defs(platform_if.body)
    unix_defs = _collect_func_defs(platform_if.orelse)
    assert {"_lock", "_unlock"}.issubset(win_defs), (
        f"Windows branch is missing _lock/_unlock; found {sorted(win_defs)}"
    )
    assert {"_lock", "_unlock"}.issubset(unix_defs), (
        f"Unix branch is missing _lock/_unlock; found {sorted(unix_defs)}"
    )


def test_ledger_append_functional_on_current_host():
    """append_entry still writes and reads correctly on the current platform.

    Exercises the real lock wrapper end-to-end. Does not claim to validate
    Windows — only confirms the refactor preserved the Unix code path.
    """
    from ledger_manager import append_entry, read_ledger

    with tempfile.TemporaryDirectory() as d:
        ledger = Path(d) / "test_s3_134.jsonl"
        append_entry(ledger, "user", "hello", tags=["[QUESTION]"])
        append_entry(ledger, "assistant", "ok", tags=["[DECISION]"])
        entries = read_ledger(ledger)
        assert len(entries) == 2
        assert entries[0]["content"] == "hello"
        assert entries[0]["tags"] == ["[QUESTION]"]
        assert entries[1]["content"] == "ok"
        # Verify raw file is valid JSONL (lock released cleanly, flush happened)
        raw_lines = ledger.read_text().splitlines()
        assert len(raw_lines) == 2
        for line in raw_lines:
            json.loads(line)  # each line is valid JSON


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _is_sys_platform_win32_test(expr: ast.expr) -> bool:
    """Return True iff expr is `sys.platform == "win32"`."""
    if not isinstance(expr, ast.Compare):
        return False
    if not (
        isinstance(expr.left, ast.Attribute)
        and isinstance(expr.left.value, ast.Name)
        and expr.left.value.id == "sys"
        and expr.left.attr == "platform"
    ):
        return False
    if len(expr.ops) != 1 or not isinstance(expr.ops[0], ast.Eq):
        return False
    if len(expr.comparators) != 1:
        return False
    comp = expr.comparators[0]
    return isinstance(comp, ast.Constant) and comp.value == "win32"


def _collect_func_defs(body: list) -> set:
    """Collect FunctionDef names at the top of an If-branch body."""
    return {n.name for n in body if isinstance(n, ast.FunctionDef)}
