"""Regression tests for Bug 4: Status Line Contract Mismatch.

CLI wrapper scripts invoked as run_command actions must emit status lines
from COMMAND_STATUS_PATTERNS. Custom status strings (e.g.
INFRASTRUCTURE_SETUP_COMPLETE, STUB_GENERATION_COMPLETE) are not recognized
by dispatch_command_status() and cause a ValueError.

These AST-based tests structurally verify that all print() calls emitting
terminal status lines use the approved vocabulary.
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "svp" / "scripts"

# Status line patterns that dispatch_command_status() recognizes
VALID_COMMAND_STATUS_PREFIXES = {
    "COMMAND_SUCCEEDED",
    "COMMAND_FAILED",
    "TESTS_PASSED",
    "TESTS_FAILED",
    "TESTS_ERROR",
}

# Scripts invoked as run_command actions and the status prefixes they may emit
RUN_COMMAND_SCRIPTS = {
    "setup_infrastructure.py": {"COMMAND_SUCCEEDED", "COMMAND_FAILED"},
    "generate_stubs.py": {"COMMAND_SUCCEEDED", "COMMAND_FAILED"},
}


def _extract_print_string_constants(filename: str) -> list[str]:
    """Extract all string constants from print() calls in a script.

    Returns only simple string-literal arguments to print(), e.g.
    print("COMMAND_SUCCEEDED") -> "COMMAND_SUCCEEDED".
    Ignores f-strings, variables, and stderr prints.
    """
    source = (SCRIPTS_DIR / filename).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=filename)
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match print(...) calls
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "print"):
            continue
        # Skip stderr prints: print(..., file=sys.stderr)
        is_stderr = any(
            isinstance(kw.value, ast.Attribute)
            and isinstance(kw.value.value, ast.Name)
            and kw.value.value.id == "sys"
            and kw.value.attr == "stderr"
            for kw in node.keywords
            if kw.arg == "file"
        )
        if is_stderr:
            continue
        # Extract simple string constants
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            results.append(node.args[0].value)
    return results


def _looks_like_status_line(s: str) -> bool:
    """Heuristic: a string that is ALL_CAPS_WITH_UNDERSCORES looks like a status line."""
    import re
    return bool(re.match(r'^[A-Z][A-Z_]+$', s))


def test_run_command_scripts_emit_valid_status_lines():
    """CLI wrappers invoked as run_command must only emit recognized status prefixes."""
    for script, allowed in RUN_COMMAND_SCRIPTS.items():
        printed = _extract_print_string_constants(script)
        # Filter to strings that look like status lines (ALL_CAPS)
        status_like = [s for s in printed if _looks_like_status_line(s)]
        for s in status_like:
            assert s in allowed, (
                f"{script} prints '{s}' which is not in the allowed status vocabulary "
                f"{allowed}. run_command scripts must use COMMAND_SUCCEEDED/COMMAND_FAILED."
            )


def test_no_custom_complete_status_strings():
    """No run_command script should emit *_COMPLETE as a status line."""
    for script in RUN_COMMAND_SCRIPTS:
        printed = _extract_print_string_constants(script)
        complete_strings = [s for s in printed if s.endswith("_COMPLETE")]
        assert not complete_strings, (
            f"{script} emits custom *_COMPLETE status strings: {complete_strings}. "
            f"Use COMMAND_SUCCEEDED instead."
        )


def test_command_status_patterns_includes_required_patterns():
    """COMMAND_STATUS_PATTERNS in routing.py must include all required patterns."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from routing import COMMAND_STATUS_PATTERNS
    finally:
        sys.path.pop(0)

    required = {"COMMAND_SUCCEEDED", "COMMAND_FAILED", "TESTS_PASSED", "TESTS_FAILED", "TESTS_ERROR"}
    actual = set(COMMAND_STATUS_PATTERNS)
    missing = required - actual
    assert not missing, (
        f"COMMAND_STATUS_PATTERNS is missing required patterns: {missing}"
    )


def test_dispatch_command_status_rejects_custom_strings():
    """dispatch_command_status must reject strings not in COMMAND_STATUS_PATTERNS."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from routing import dispatch_command_status
        from pipeline_state import PipelineState
    finally:
        sys.path.pop(0)

    state = PipelineState.from_dict({
        "stage": "2",
        "sub_stage": "infrastructure_setup",
        "current_unit": None,
        "total_units": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test",
        "last_action": "",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })

    import pytest
    # These custom strings must be rejected
    bad_statuses = [
        "INFRASTRUCTURE_SETUP_COMPLETE",
        "STUB_GENERATION_COMPLETE",
        "SETUP_DONE",
        "CUSTOM_STATUS",
    ]
    for bad in bad_statuses:
        with pytest.raises(ValueError, match="Unknown.*status"):
            dispatch_command_status(state, bad, None, "infrastructure_setup", Path("."))
