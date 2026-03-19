#!/usr/bin/env python3
"""Structural completeness checker -- project-agnostic AST scanner.

Performs four high-confidence, low-false-positive checks on any Python
codebase to detect declaration-vs-usage gaps:

1. Dict registry keys never dispatched
2. Enum values never matched
3. Exported functions never called
4. String dispatch gaps (registry-linked)

CLI interface:
    python scripts/structural_check.py --target <path> [--format json|text] [--strict]

Only stdlib imports (ast, json, pathlib, argparse, sys).
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# AST Helpers
# ---------------------------------------------------------------------------


def _collect_py_files(target: Path) -> List[Path]:
    """Collect all .py files under target, excluding __pycache__."""
    return sorted(
        p
        for p in target.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _parse_file(path: Path) -> Optional[ast.Module]:
    """Parse a Python file, returning None on failure."""
    try:
        source = path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def _source_text(path: Path) -> str:
    """Read file text, returning empty string on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


# ---------------------------------------------------------------------------
# Check 1: Dict registry keys never dispatched
# ---------------------------------------------------------------------------


def _find_module_level_dicts(tree: ast.Module) -> List[Tuple[str, List[str]]]:
    """Find module-level dict assignments with 3+ string keys.

    Returns list of (dict_name, [key_strings]).
    """
    results = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Dict):
                keys = []
                for k in node.value.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        keys.append(k.value)
                if len(keys) >= 3:
                    results.append((target.id, keys))
    return results


def check_dict_registry_gaps(
    target: Path, py_files: List[Path]
) -> List[Dict[str, Any]]:
    """Check 1: Find dict registry keys that are never referenced outside
    the dict definition itself."""
    findings = []

    for fpath in py_files:
        tree = _parse_file(fpath)
        if tree is None:
            continue

        dicts = _find_module_level_dicts(tree)
        if not dicts:
            continue

        # Build a text corpus from all OTHER files plus same file
        # (we check outside the dict definition)
        all_sources: Dict[Path, str] = {}
        for p in py_files:
            all_sources[p] = _source_text(p)

        for dict_name, keys in dicts:
            unused_keys = []
            for key in keys:
                # Search all files for references to this key value
                found = False
                for p, src in all_sources.items():
                    if p == fpath:
                        # In the defining file, look for usage outside
                        # the dict literal. Count occurrences -- if more
                        # than in the dict definition, it is used.
                        # Simple heuristic: search for the key as a
                        # quoted string in subscript/get/comparison context
                        patterns = [
                            f'["{key}"]',
                            f"['{key}']",
                            f'.get("{key}"',
                            f".get('{key}'",
                            f'"{key}" in ',
                            f"'{key}' in ",
                            f'== "{key}"',
                            f"== '{key}'",
                            f'"{key}":',
                            f"'{key}':",
                        ]
                        # Count dict-definition occurrences (key: patterns)
                        def_patterns = [f'"{key}":', f"'{key}':"]
                        def_count = sum(src.count(dp) for dp in def_patterns)
                        # Count all occurrences
                        all_count = sum(src.count(p) for p in patterns)
                        if all_count > def_count:
                            found = True
                            break
                    else:
                        # In other files, any reference counts
                        if (
                            f'"{key}"' in src
                            or f"'{key}'" in src
                        ):
                            found = True
                            break
                if not found:
                    unused_keys.append(key)

            if unused_keys:
                findings.append({
                    "file": str(fpath),
                    "dict_name": dict_name,
                    "unused_keys": unused_keys,
                })

    return findings


# ---------------------------------------------------------------------------
# Check 2: Enum values never matched
# ---------------------------------------------------------------------------


def _find_enum_classes(tree: ast.Module) -> List[Tuple[str, List[str]]]:
    """Find enum.Enum subclasses and their members."""
    results = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from Enum or a known Enum base
            is_enum = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in (
                    "Enum", "IntEnum", "StrEnum", "Flag", "IntFlag",
                ):
                    is_enum = True
                elif isinstance(base, ast.Attribute) and base.attr in (
                    "Enum", "IntEnum", "StrEnum", "Flag", "IntFlag",
                ):
                    is_enum = True
            if not is_enum:
                continue

            members = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for t in item.targets:
                        if isinstance(t, ast.Name) and not t.id.startswith("_"):
                            members.append(t.id)
            if members:
                results.append((node.name, members))
    return results


def check_enum_value_gaps(
    target: Path, py_files: List[Path]
) -> List[Dict[str, Any]]:
    """Check 2: Find enum members that are never referenced."""
    findings = []

    for fpath in py_files:
        tree = _parse_file(fpath)
        if tree is None:
            continue

        enums = _find_enum_classes(tree)
        if not enums:
            continue

        # Build text corpus
        all_sources = {p: _source_text(p) for p in py_files}

        for enum_name, members in enums:
            unused = []
            for member in members:
                found = False
                # Look for EnumClass.MEMBER or just MEMBER in comparisons
                pattern = f"{enum_name}.{member}"
                for p, src in all_sources.items():
                    if p == fpath:
                        # In defining file, check for usage beyond definition
                        count = src.count(pattern)
                        if count > 0:
                            found = True
                            break
                    else:
                        if pattern in src:
                            found = True
                            break
                if not found:
                    unused.append(member)
            if unused:
                findings.append({
                    "file": str(fpath),
                    "enum_name": enum_name,
                    "unused_members": unused,
                })

    return findings


# ---------------------------------------------------------------------------
# Check 3: Exported functions never called
# ---------------------------------------------------------------------------


def _find_public_functions(tree: ast.Module) -> Tuple[List[str], Optional[List[str]]]:
    """Find public functions in a module.

    Returns (public_functions, __all__).
    __all__ is None if not defined.
    """
    all_list: Optional[List[str]] = None
    functions: List[str] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                functions.append(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        all_list = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                all_list.append(elt.value)
    return functions, all_list


def check_unused_exports(
    target: Path, py_files: List[Path]
) -> List[Dict[str, Any]]:
    """Check 3: Find exported functions never imported or called from
    another module."""
    findings = []

    for fpath in py_files:
        tree = _parse_file(fpath)
        if tree is None:
            continue

        functions, all_list = _find_public_functions(tree)
        if not functions:
            continue

        # Determine exported set
        exported = set(all_list) if all_list is not None else set(functions)
        if not exported:
            continue

        # Check other files for imports and calls
        for func_name in sorted(exported):
            found = False
            for p in py_files:
                if p == fpath:
                    continue
                src = _source_text(p)
                # Check import statements and direct usage
                if func_name in src:
                    found = True
                    break
            if not found:
                findings.append({
                    "file": str(fpath),
                    "function_name": func_name,
                })

    return findings


# ---------------------------------------------------------------------------
# Check 4: String dispatch gaps (registry-linked)
# ---------------------------------------------------------------------------


def _find_string_dispatch_functions(
    tree: ast.Module,
) -> List[Tuple[str, str, Set[str]]]:
    """Find functions with 3+ branch if/elif chains comparing against
    string literals.

    Returns list of (function_name, compared_variable, handled_strings).
    """
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for child in ast.walk(node):
            if not isinstance(child, ast.If):
                continue

            # Count elif chain length
            handled: Set[str] = set()
            var_name: Optional[str] = None
            chain_len = 0
            current: Any = child

            while current is not None:
                cmp_var, cmp_val = _extract_string_comparison(current.test)
                if cmp_var is not None and cmp_val is not None:
                    if var_name is None:
                        var_name = cmp_var
                    if cmp_var == var_name:
                        handled.add(cmp_val)
                        chain_len += 1

                # Follow elif chain
                if (
                    current.orelse
                    and len(current.orelse) == 1
                    and isinstance(current.orelse[0], ast.If)
                ):
                    current = current.orelse[0]
                else:
                    break

            if chain_len >= 3 and var_name is not None:
                results.append((node.name, var_name, handled))

    return results


def _extract_string_comparison(
    test_node: ast.expr,
) -> Tuple[Optional[str], Optional[str]]:
    """Extract (variable_name, string_value) from a comparison like
    `x == "foo"` or `x.startswith("foo")`.
    """
    if isinstance(test_node, ast.Compare):
        if (
            len(test_node.ops) == 1
            and isinstance(test_node.ops[0], ast.Eq)
            and len(test_node.comparators) == 1
        ):
            left = test_node.left
            right = test_node.comparators[0]

            # x == "literal"
            if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and isinstance(right.value, str):
                return (left.id, right.value)
            # "literal" == x
            if isinstance(right, ast.Name) and isinstance(left, ast.Constant) and isinstance(left.value, str):
                return (right.id, left.value)

    # Also handle x.startswith("literal")
    if isinstance(test_node, ast.Call):
        if (
            isinstance(test_node.func, ast.Attribute)
            and test_node.func.attr == "startswith"
            and isinstance(test_node.func.value, ast.Name)
            and len(test_node.args) == 1
            and isinstance(test_node.args[0], ast.Constant)
            and isinstance(test_node.args[0].value, str)
        ):
            return (test_node.func.value.id, test_node.args[0].value)

    return (None, None)


def check_string_dispatch_gaps(
    target: Path, py_files: List[Path]
) -> List[Dict[str, Any]]:
    """Check 4: Find string values passed to dispatch functions that are
    not handled in the if/elif chain."""
    findings = []

    # First, find all dispatch functions across all files
    dispatch_info: List[Tuple[Path, str, str, Set[str]]] = []

    for fpath in py_files:
        tree = _parse_file(fpath)
        if tree is None:
            continue
        for func_name, var_name, handled in _find_string_dispatch_functions(tree):
            dispatch_info.append((fpath, func_name, var_name, handled))

    if not dispatch_info:
        return findings

    # For each dispatch function, find callers and the strings they pass
    all_sources = {p: _source_text(p) for p in py_files}

    for fpath, func_name, var_name, handled in dispatch_info:
        # Find callers across all files
        passed_values: Set[str] = set()
        for p in py_files:
            tree = _parse_file(p)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if this is a call to our function
                    callee_name = None
                    if isinstance(node.func, ast.Name):
                        callee_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        callee_name = node.func.attr

                    if callee_name == func_name:
                        # Extract string arguments
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                passed_values.add(arg.value)
                        for kw in node.keywords:
                            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                passed_values.add(kw.value.value)

        unhandled = sorted(passed_values - handled)
        if unhandled:
            findings.append({
                "file": str(fpath),
                "function": func_name,
                "unhandled": unhandled,
            })

    return findings


def check_stub_imports_in_tests(
    target: Path,
    py_files: List[Path],
) -> List[Dict[str, Any]]:
    """Bug 74: Check that test files import from real scripts, not stubs.

    Tests must target the real implementation modules (routing, pipeline_state,
    etc.), not the build-time stubs (src.unit_N.stub). Stubs are simplified
    implementations that may diverge from the real scripts, causing false-pass
    scenarios where tests pass but the deployed code is broken.

    This check scans all .py files under a tests/ directory for
    'from src.unit_' import patterns.
    """
    import re

    pattern = re.compile(r"from\s+src\.unit_\d+")
    findings: List[Dict[str, Any]] = []

    # Only scan test files (under any tests/ directory)
    test_files = [f for f in py_files if "/tests/" in str(f) or "\\tests\\" in str(f)]

    for fpath in test_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        in_docstring = False
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Track multi-line docstring boundaries
            if '"""' in stripped or "'''" in stripped:
                count = stripped.count('"""') + stripped.count("'''")
                if count == 1:
                    in_docstring = not in_docstring
                # If count >= 2, it's an open+close on same line
                continue
            if in_docstring:
                continue
            # Skip comments
            if stripped.startswith("#"):
                continue
            # Skip string literals containing the pattern
            if stripped.startswith(("'", '"', "assert")):
                if "from src.unit_" not in stripped.split("#")[0].split("import")[0]:
                    continue
            if pattern.search(line):
                findings.append({
                    "file": str(fpath.relative_to(target)),
                    "line": i,
                    "pattern": "stub_import",
                    "context": stripped,
                })

    return findings


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_checks(target: Path) -> Dict[str, Any]:
    """Run all five checks and return structured results."""
    py_files = _collect_py_files(target)

    dict_gaps = check_dict_registry_gaps(target, py_files)
    enum_gaps = check_enum_value_gaps(target, py_files)
    unused = check_unused_exports(target, py_files)
    dispatch_gaps = check_string_dispatch_gaps(target, py_files)
    stub_imports = check_stub_imports_in_tests(target, py_files)

    total = (
        len(dict_gaps) + len(enum_gaps) + len(unused)
        + len(dispatch_gaps) + len(stub_imports)
    )

    return {
        "status": "CLEAN" if total == 0 else "FINDINGS",
        "checks": {
            "dict_registry_gaps": dict_gaps,
            "enum_value_gaps": enum_gaps,
            "unused_exports": unused,
            "string_dispatch_gaps": dispatch_gaps,
            "stub_imports_in_tests": stub_imports,
        },
        "summary": {
            "total_findings": total,
            "files_scanned": len(py_files),
            "checks_run": 5,
        },
    }


def format_text(results: Dict[str, Any]) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"Structural Check: {results['status']}")
    lines.append(
        f"Files scanned: {results['summary']['files_scanned']}, "
        f"Checks run: {results['summary']['checks_run']}, "
        f"Findings: {results['summary']['total_findings']}"
    )
    lines.append("")

    checks = results["checks"]

    if checks["dict_registry_gaps"]:
        lines.append("== Dict Registry Gaps ==")
        for f in checks["dict_registry_gaps"]:
            lines.append(
                f"  {f['file']}: {f['dict_name']} -- "
                f"unused keys: {', '.join(f['unused_keys'])}"
            )
        lines.append("")

    if checks["enum_value_gaps"]:
        lines.append("== Enum Value Gaps ==")
        for f in checks["enum_value_gaps"]:
            lines.append(
                f"  {f['file']}: {f['enum_name']} -- "
                f"unused members: {', '.join(f['unused_members'])}"
            )
        lines.append("")

    if checks["unused_exports"]:
        lines.append("== Unused Exports ==")
        for f in checks["unused_exports"]:
            lines.append(f"  {f['file']}: {f['function_name']}")
        lines.append("")

    if checks["string_dispatch_gaps"]:
        lines.append("== String Dispatch Gaps ==")
        for f in checks["string_dispatch_gaps"]:
            lines.append(
                f"  {f['file']}: {f['function']} -- "
                f"unhandled: {', '.join(f['unhandled'])}"
            )
        lines.append("")

    if checks.get("stub_imports_in_tests"):
        lines.append("== Stub Imports in Tests (Bug 74) ==")
        for f in checks["stub_imports_in_tests"]:
            lines.append(
                f"  {f['file']}:{f['line']}: {f['context']}"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project-agnostic structural completeness checker"
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Path to the Python project to scan",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any findings are detected",
    )
    args = parser.parse_args()

    if not args.target.is_dir():
        print(f"Error: {args.target} is not a directory", file=sys.stderr)
        return 2

    results = run_checks(args.target)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))

    if args.strict and results["status"] == "FINDINGS":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
