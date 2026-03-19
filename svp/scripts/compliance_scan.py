"""Plugin Manifest and Structural Validation.

Defines the plugin.json manifest, marketplace.json catalog, structural
validation logic, and delivery compliance scan.
"""

import ast
import json
from typing import Dict, Any, List
from pathlib import Path


# ===========================================================================
# Plugin manifest schema
# ===========================================================================

PLUGIN_JSON: Dict[str, Any] = {
    "name": "svp",
    "version": "2.1.1",
    "description": "Stratified Verification Pipeline - deterministically orchestrated software development",
}

# ===========================================================================
# Marketplace catalog schema
# ===========================================================================

MARKETPLACE_JSON: Dict[str, Any] = {
    "name": "svp",
    "owner": {"name": "SVP"},
    "plugins": [
        {
            "name": "svp",
            "source": "./svp",
            "description": "Stratified Verification Pipeline -- deterministically orchestrated, sequentially gated development for domain experts",
            "version": "2.1.1",
            "author": {"name": "SVP"},
        }
    ],
}

# ===========================================================================
# Deliverable content constants (populated by Stage 5 assembly)
# ===========================================================================

PLUGIN_JSON_CONTENT: str = json.dumps(PLUGIN_JSON, indent=2)
MARKETPLACE_JSON_CONTENT: str = json.dumps(MARKETPLACE_JSON, indent=2)


# ===========================================================================
# Structural validation
# ===========================================================================


def validate_plugin_structure(repo_root: Path) -> List[str]:
    """Validate the plugin directory structure.

    Returns a list of validation error strings. Empty list means valid.
    Raises ValueError if violations are found.
    """
    errors: List[str] = []

    # Check marketplace.json at repo root
    if not (repo_root / ".claude-plugin" / "marketplace.json").exists():
        errors.append("Missing .claude-plugin/marketplace.json at repo root")

    # Check plugin.json under svp/
    if not (repo_root / "svp" / ".claude-plugin" / "plugin.json").exists():
        errors.append("Missing svp/.claude-plugin/plugin.json")

    # Check component directories under svp/
    for component in ["agents", "commands", "hooks", "scripts", "skills"]:
        if not (repo_root / "svp" / component).is_dir():
            errors.append(f"Missing svp/{component}/ directory")
        if (repo_root / component).is_dir():
            errors.append(
                f"Component directory '{component}' found at repo root (should be under svp/)"
            )

    # Check toolchain_defaults directory
    td_dir = repo_root / "svp" / "scripts" / "toolchain_defaults"
    if not td_dir.is_dir():
        errors.append("Missing svp/scripts/toolchain_defaults/ directory")
    else:
        if not (td_dir / "python_conda_pytest.json").exists():
            errors.append(
                "Missing svp/scripts/toolchain_defaults/python_conda_pytest.json"
            )
        else:
            # Validate toolchain JSON is valid JSON
            try:
                json.loads((td_dir / "python_conda_pytest.json").read_text())
            except (json.JSONDecodeError, OSError):
                errors.append("Invalid toolchain JSON file")

        if not (td_dir / "ruff.toml").exists():
            errors.append("Missing svp/scripts/toolchain_defaults/ruff.toml")

    return errors


# ===========================================================================
# Delivery compliance scan
# ===========================================================================

_CONDA_BANNED = [
    {"pattern": "pip install"},
    {"pattern": "pip "},
    {"pattern": "pip3 install"},
    {"pattern": "python "},
    {"pattern": "pytest "},
]

_NON_CONDA_BANNED = [
    {"pattern": "conda create"},
    {"pattern": "conda run"},
    {"pattern": "conda install"},
    {"pattern": "conda env"},
]


def _get_banned_patterns(
    environment_recommendation: str,
) -> List[Dict[str, str]]:
    """Return banned pattern set for the given environment recommendation."""
    if environment_recommendation == "conda":
        return list(_CONDA_BANNED)
    elif environment_recommendation in ("pyenv", "venv", "poetry"):
        return list(_NON_CONDA_BANNED)
    elif environment_recommendation == "none":
        return list(_CONDA_BANNED) + list(_NON_CONDA_BANNED)
    else:
        return []


def _scan_file_ast(
    file_path: Path,
    banned_patterns: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """Parse a Python file's AST and inspect subprocess calls for banned patterns."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations: List[Dict[str, Any]] = []

    # Check for __SVP_STUB__ sentinel (always, regardless of banned_patterns)
    if "__SVP_STUB__" in source:
        violations.append(
            {
                "file": str(file_path),
                "line": 0,
                "issue": "__SVP_STUB__ sentinel found",
            }
        )

    if not banned_patterns:
        return violations

    # Functions we consider as executable subprocess calls
    SUBPROCESS_FUNCS = {
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
        "os.system",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Determine function name
        func_name = _get_call_name(node)
        if func_name not in SUBPROCESS_FUNCS:
            continue

        # Extract the command string from the first argument
        if not node.args:
            continue

        cmd_str = _extract_string(node.args[0])
        if cmd_str is None:
            continue

        # Check against banned patterns
        for bp in banned_patterns:
            pattern = bp["pattern"]
            if _is_pattern_violation(cmd_str, pattern):
                violations.append(
                    {
                        "file": file_path,
                        "line": node.lineno,
                        "pattern": pattern,
                        "context": cmd_str,
                        "issue": f"Banned pattern '{pattern}' found",
                    }
                )

    return violations


def _get_call_name(node: ast.Call) -> str:
    """Extract the dotted function name from a Call node."""
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _extract_string(node: ast.expr) -> str | None:
    """Extract a string constant from an AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # f-string: try to extract string parts
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        return "".join(parts) if parts else None
    return None


def _is_pattern_violation(cmd_str: str, pattern: str) -> bool:
    """Check if a command string violates a banned pattern.

    For conda-banned patterns (pip, python, pytest), the pattern is NOT
    a violation if preceded by 'conda run -n' in the command string.
    """
    if pattern not in cmd_str:
        return False

    # If the command is prefixed with conda run, it's not a violation
    # for pip/python/pytest patterns
    if pattern in ("pip install", "pip ", "pip3 install", "python ", "pytest "):
        if "conda run -n" in cmd_str:
            # Check that conda run appears before the pattern
            conda_pos = cmd_str.find("conda run -n")
            pattern_pos = cmd_str.find(pattern)
            if conda_pos < pattern_pos:
                return False

    return True


def run_compliance_scan(
    project_root: Path,
    delivered_src_dir: Path,
    delivered_tests_dir: Path,
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Scan delivered source files for preference violations.

    Returns a list of violation dicts with keys: file, line, pattern, context.
    """
    env_rec = profile["delivery"]["environment_recommendation"]
    banned = _get_banned_patterns(env_rec)

    if not banned:
        return []

    violations: List[Dict[str, Any]] = []

    # Scan both source and test directories
    for scan_dir in [delivered_src_dir, delivered_tests_dir]:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            file_violations = _scan_file_ast(py_file, banned)
            violations.extend(file_violations)

    return violations


def compliance_scan_main() -> None:
    """CLI entry point for the compliance scan."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="SVP Delivery Compliance Scan")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=None,
        help="Delivered source directory",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=None,
        help="Delivered tests directory",
    )
    args = parser.parse_args()

    project_root = args.project_root
    # Load profile via Unit 1
    from svp_config import load_profile

    profile = load_profile(project_root)

    # Determine delivered repo paths if not provided
    if args.src_dir is not None:
        src_dir = args.src_dir
    else:
        project_name = json.loads(
            (project_root / "pipeline_state.json").read_text()
        ).get("project_name", "project")
        delivered_root = project_root.parent / f"{project_name}-repo"
        src_dir = delivered_root / "src"

    if args.tests_dir is not None:
        tests_dir = args.tests_dir
    else:
        project_name = json.loads(
            (project_root / "pipeline_state.json").read_text()
        ).get("project_name", "project")
        delivered_root = project_root.parent / f"{project_name}-repo"
        tests_dir = delivered_root / "tests"

    violations = run_compliance_scan(project_root, src_dir, tests_dir, profile)

    if not violations:
        print("COMMAND_SUCCEEDED")
    else:
        print(f"COMMAND_FAILED: {len(violations)} violations found")
        for v in violations:
            print(f"  {v['file']}:{v['line']} - {v['pattern']} in: {v['context']}")
        sys.exit(1)


if __name__ == "__main__":
    compliance_scan_main()
