"""Regression tests for Bug 2: Wrapper Drift.

CLI wrapper scripts must delegate to canonical modules rather than
reimplementing logic. These AST-based tests structurally detect
reimplementation patterns that caused dual-file sync drift.
"""

import ast
import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "svp" / "scripts"

# Thin wrappers that must delegate entirely to routing.py
THIN_WRAPPERS = ["update_state.py", "run_tests.py"]


def _parse_script(filename: str) -> ast.Module:
    """Parse a script file and return its AST."""
    source = (SCRIPTS_DIR / filename).read_text(encoding="utf-8")
    return ast.parse(source, filename=filename)


def _read_lines(filename: str) -> list[str]:
    """Read a script file and return its lines."""
    return (SCRIPTS_DIR / filename).read_text(encoding="utf-8").splitlines()


# ── Tests for thin wrappers (update_state.py, run_tests.py) ──────────────


def test_thin_wrappers_import_from_canonical_module():
    """Thin wrappers must contain 'from routing import ...'."""
    for wrapper in THIN_WRAPPERS:
        tree = _parse_script(wrapper)
        routing_imports = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "routing"
        ]
        assert routing_imports, (
            f"{wrapper} must contain 'from routing import ...' "
            f"but found no ImportFrom nodes referencing 'routing'"
        )


def test_thin_wrappers_have_no_domain_functions():
    """Thin wrappers must not define functions other than main()."""
    for wrapper in THIN_WRAPPERS:
        tree = _parse_script(wrapper)
        non_main = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name != "main"
        ]
        assert not non_main, (
            f"{wrapper} defines non-main functions: {non_main}. "
            f"Thin wrappers must only define main()."
        )


def test_thin_wrappers_are_small():
    """Thin wrappers must be under 50 lines (reimplementations were 200-500)."""
    for wrapper in THIN_WRAPPERS:
        lines = _read_lines(wrapper)
        assert len(lines) < 50, (
            f"{wrapper} has {len(lines)} lines (limit: 50). "
            f"Large size indicates reimplementation."
        )


def test_thin_wrappers_no_subprocess_or_argparse():
    """Thin wrappers must not import subprocess or argparse."""
    forbidden = {"subprocess", "argparse"}
    for wrapper in THIN_WRAPPERS:
        tree = _parse_script(wrapper)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        violations = imported & forbidden
        assert not violations, (
            f"{wrapper} imports {violations}. "
            f"Thin wrappers must not import subprocess or argparse."
        )


# ── Tests for other wrapper scripts ──────────────────────────────────────


def test_dependency_extractor_calls_canonical_api():
    """dependency_extractor.py must define canonical Unit 7 API functions."""
    tree = _parse_script("dependency_extractor.py")
    defined = {
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    required = {"extract_all_imports", "map_imports_to_packages", "create_conda_environment"}
    missing = required - defined
    assert not missing, (
        f"dependency_extractor.py is missing canonical API functions: {missing}"
    )


def test_generate_stubs_uses_high_level_api():
    """generate_stubs.py must import write_stub_file and write_upstream_stubs."""
    tree = _parse_script("generate_stubs.py")
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
    required = {"write_stub_file", "write_upstream_stubs"}
    missing = required - imported_names
    assert not missing, (
        f"generate_stubs.py must import {required} from stub_generator, "
        f"missing: {missing}"
    )
    assert "generate_unit_stubs" not in imported_names, (
        "generate_stubs.py imports nonexistent 'generate_unit_stubs' — "
        "must use write_stub_file and write_upstream_stubs instead"
    )


def test_no_script_imports_nonexistent_names():
    """All wrapper scripts must import at module level without ImportError."""
    scripts = ["update_state", "run_tests", "generate_stubs", "dependency_extractor"]
    for name in scripts:
        saved = sys.modules.pop(name, None)
        try:
            importlib.import_module(name)
        except ImportError as exc:
            raise AssertionError(
                f"Importing {name} raised ImportError: {exc}"
            ) from exc
        finally:
            if saved is not None:
                sys.modules[name] = saved
