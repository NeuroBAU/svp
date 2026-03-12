"""Regression tests for Bug 3: CLI Argument Mismatch.

routing.py generates CLI commands with specific flags. Consumer scripts
must accept all flags that routing generates. These tests verify
cross-unit CLI argument compatibility — the specific Bug 3 failure was
routing emitting --output but prepare_task.py not accepting it.
"""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "svp" / "scripts"
SRC_DIR = REPO_ROOT / "src"


# ── Helpers ───────────────────────────────────────────────────────────────


def _extract_argparse_flags(source: str) -> set[str]:
    """Extract all --flag names from add_argument() calls in source."""
    tree = ast.parse(source)
    flags: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"
        ):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith("--"):
                    flags.add(arg.value)
    return flags


def _extract_argparse_flags_from_function(source: str, func_name: str) -> set[str]:
    """Extract --flag names from add_argument() calls inside a specific function."""
    tree = ast.parse(source)
    flags: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == func_name):
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            if not (
                isinstance(child.func, ast.Attribute)
                and child.func.attr == "add_argument"
            ):
                continue
            for arg in child.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("--"):
                        flags.add(arg.value)
    return flags


def _flags_from_cmd(cmd: str) -> set[str]:
    """Extract all --flag tokens from a command string."""
    return set(re.findall(r"--[\w-]+", cmd))


def _get_prepare_task_flags() -> set[str]:
    """Get all flags accepted by prepare_task.py's argparse."""
    source = (SCRIPTS_DIR / "prepare_task.py").read_text(encoding="utf-8")
    return _extract_argparse_flags(source)


def _get_update_state_flags() -> set[str]:
    """Get all flags accepted by update_state_main() in routing.py."""
    source = (SCRIPTS_DIR / "routing.py").read_text(encoding="utf-8")
    return _extract_argparse_flags_from_function(source, "update_state_main")


def _import_routing():
    """Import routing module."""
    import importlib

    return importlib.import_module("routing")


# ── Tests ─────────────────────────────────────────────────────────────────


def test_prepare_cmd_flags_accepted_by_prepare_task():
    """All flags from _prepare_cmd() must be accepted by prepare_task.py."""
    routing = _import_routing()
    cmd = routing._prepare_cmd("test_agent", unit=1)
    generated = _flags_from_cmd(cmd)
    accepted = _get_prepare_task_flags()
    unaccepted = generated - accepted
    assert not unaccepted, (
        f"_prepare_cmd() generates flags not accepted by prepare_task.py: "
        f"{unaccepted}. Generated: {generated}, Accepted: {accepted}"
    )


def test_gate_prepare_cmd_flags_accepted():
    """All flags from _gate_prepare_cmd() must be accepted by prepare_task.py."""
    routing = _import_routing()
    cmd = routing._gate_prepare_cmd("spec_approval", unit=1)
    generated = _flags_from_cmd(cmd)
    accepted = _get_prepare_task_flags()
    unaccepted = generated - accepted
    assert not unaccepted, (
        f"_gate_prepare_cmd() generates flags not accepted by prepare_task.py: "
        f"{unaccepted}. Generated: {generated}, Accepted: {accepted}"
    )


def test_post_cmd_flags_accepted_by_update_state():
    """All flags from _post_cmd() must be accepted by update_state_main."""
    routing = _import_routing()
    cmd = routing._post_cmd("build", unit=1)
    generated = _flags_from_cmd(cmd)
    accepted = _get_update_state_flags()
    unaccepted = generated - accepted
    assert not unaccepted, (
        f"_post_cmd() generates flags not accepted by update_state_main: "
        f"{unaccepted}. Generated: {generated}, Accepted: {accepted}"
    )


def test_prepare_task_accepts_output_flag():
    """prepare_task.py must accept --output (the specific Bug 3 regression)."""
    accepted = _get_prepare_task_flags()
    assert "--output" in accepted, (
        f"prepare_task.py does not accept --output. "
        f"This was the specific Bug 3 failure. Accepted flags: {accepted}"
    )


def test_prepare_cmd_always_includes_output():
    """_prepare_cmd() must always include --output in its output."""
    routing = _import_routing()
    cmd = routing._prepare_cmd("test_agent", unit=1)
    assert "--output" in _flags_from_cmd(cmd), (
        f"_prepare_cmd() output missing --output: {cmd}"
    )


def test_all_referenced_scripts_exist():
    """All script filenames referenced in command_builders.py must exist on disk."""
    source = (SRC_DIR / "svp_host_claude" / "command_builders.py").read_text(
        encoding="utf-8"
    )
    script_refs = set(re.findall(r"python scripts/([\w_]+\.py)", source))
    assert script_refs, "Expected to find script references in command_builders.py"
    for script_name in script_refs:
        assert (SCRIPTS_DIR / script_name).exists(), (
            f"command_builders.py references 'scripts/{script_name}' but "
            f"{SCRIPTS_DIR / script_name} does not exist"
        )


def test_post_cmd_with_gate_id_generates_gate_flag():
    """_post_cmd(gate_id=...) must include --gate in its output."""
    routing = _import_routing()
    cmd = routing._post_cmd(
        "test_validation", unit=1, gate_id="gate_3_1_test_validation"
    )
    flags = _flags_from_cmd(cmd)
    assert "--gate" in flags, (
        f"_post_cmd() with gate_id did not generate --gate flag. Command: {cmd}"
    )
    assert "gate_3_1_test_validation" in cmd, (
        f"_post_cmd() gate_id value not found in command. Command: {cmd}"
    )


def test_post_cmd_without_gate_id_omits_gate_flag():
    """_post_cmd() without gate_id must NOT include --gate."""
    routing = _import_routing()
    cmd = routing._post_cmd("build", unit=1)
    flags = _flags_from_cmd(cmd)
    assert "--gate" not in flags, (
        f"_post_cmd() without gate_id should not generate --gate flag. Command: {cmd}"
    )


def test_post_cmd_gate_flag_accepted_by_update_state():
    """--gate flag from _post_cmd(gate_id=...) must be accepted by update_state_main."""
    routing = _import_routing()
    cmd = routing._post_cmd(
        "test_validation", unit=1, gate_id="gate_3_1_test_validation"
    )
    generated = _flags_from_cmd(cmd)
    accepted = _get_update_state_flags()
    unaccepted = generated - accepted
    assert not unaccepted, (
        f"_post_cmd(gate_id=...) generates flags not accepted by update_state_main: "
        f"{unaccepted}. Generated: {generated}, Accepted: {accepted}"
    )
