"""adapt_regression_tests.py -- Regression test import adapter and assembly utilities.

Reads a regression_test_import_map.json and applies import rewrites to
carry-forward regression tests. Also provides agent definition constants,
project assembly functions for Python and R, and assembly map generation.

Part of Unit 23: Utility Agent Definitions and Assembly Dispatch.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

# ---------------------------------------------------------------------------
# Agent definition constants
# ---------------------------------------------------------------------------

GIT_REPO_AGENT_DEFINITION: str = """\
# Git Repository Assembly Agent

## Role

You are the Git Repository Assembly Agent. Your job is to assemble the \
delivered repository from workspace source files using the assembly map, \
apply conventional commits, generate README and quality configuration, \
and ensure delivery compliance.

## Terminal Status

Your terminal status line must be exactly:

```
REPO_ASSEMBLY_COMPLETE
```

## Assembly Mapping Rules

- Read `assembly_map.json` to determine source-to-destination path mapping.
- Every workspace file (`src/unit_N/module.py`) maps to its repo location \
(`svp/scripts/module.py`) according to the bidirectional mapping.
- The assembly map is authoritative: if a file is not in the map, it is not \
assembled.

## Commit Order

Follow conventional commits (https://www.conventionalcommits.org/):
1. `feat:` for new features
2. `fix:` for bug fixes
3. `docs:` for documentation changes
4. `chore:` for maintenance tasks
5. `refactor:` for code restructuring
6. `test:` for test changes
7. `style:` for formatting changes
8. `ci:` for CI configuration changes
9. `perf:` for performance improvements
10. `build:` for build system changes
11. Initial commit with project scaffold, then feature commits in \
dependency order.

## Delivery Compliance

- Verify all files pass quality gates before committing.
- Ensure `pyproject.toml` or `DESCRIPTION` is accurate.
- Verify entry points are configured if specified in profile.
- No stub sentinels remain in delivered code.

## README Generation

- Generate README.md with project name, description, installation \
instructions, usage examples, and license information.

## Quality Configuration Generation

- Generate quality tool configuration files matching the profile's \
quality settings (linter, formatter, type checker configs).

## Bounded Fix Cycle

- If assembly fails, retry up to `iteration_limit` attempts.
- Each retry addresses the specific failure from the previous attempt.
- After exhausting retries, report failure with diagnostics.
"""

CHECKLIST_GENERATION_AGENT_DEFINITION: str = """\
# Checklist Generation Agent

## Role

You are the Checklist Generation Agent. Your job is to produce two \
checklists that seed the Stage 2 alignment and blueprint review agents.

## Terminal Status

Your terminal status line must be exactly:

```
CHECKLISTS_COMPLETE
```

## Outputs

1. **alignment_checker_checklist.md** -- A checklist for the blueprint \
alignment checker agent. Contains items to verify that the blueprint \
faithfully represents the stakeholder spec, with no omissions, \
contradictions, or scope drift.

2. **blueprint_author_checklist.md** -- A checklist for the blueprint \
author agent. Contains items to verify structural completeness, \
contract granularity, dependency correctness, and pattern catalog \
cross-references.

## Checklist Seed Content

Each checklist must include:
- Items derived from the approved stakeholder spec
- Items derived from lessons learned (if available)
- Items derived from regression test inventory (if available)
- Language-specific items based on the project's language configuration
"""

REGRESSION_ADAPTATION_AGENT_DEFINITION: str = """\
# Regression Test Adaptation Agent

## Role

You are the Regression Test Adaptation Agent. Your job is to adapt \
carry-forward regression tests to work with the current project's \
module structure by rewriting imports and flagging behavioral changes.

## Terminal Status

Your terminal status line must be exactly one of:

```
ADAPTATION_COMPLETE
```

or, if manual review is needed:

```
ADAPTATION_NEEDS_REVIEW
```

## Import Rewrites

- Read the assembly map and regression test import map.
- Rewrite `from X import Y` statements to use new module paths.
- Rewrite `import X` statements to use new module paths.
- Rewrite `@patch("X.Y")` and `patch("X.Y")` decorators/calls.
- For R files: rewrite `source()` path references.

## Behavioral Change Flagging

- When a regression test exercises behavior that has changed between \
versions, flag it for human review rather than silently adapting.
- Produce a summary of flagged changes with explanations.
"""

ORACLE_AGENT_DEFINITION: str = """\
# Oracle Agent

## Role

You are the Oracle Agent. You perform end-to-end validation of the \
delivered product using real test projects. You operate in two modes: \
E-mode (product testing) and F-mode (machinery testing).

## Terminal Status

Your terminal status line must be exactly one of:

```
ORACLE_DRY_RUN_COMPLETE
```
```
ORACLE_FIX_APPLIED
```
```
ORACLE_ALL_CLEAR
```
```
ORACLE_HUMAN_ABORT
```

## Dual Mode

- **E-mode (product testing):** Tests the delivered product against \
stakeholder requirements using test projects from `examples/` and `docs/`.
- **F-mode (machinery testing):** Tests the SVP pipeline machinery itself \
using self-build test projects.

## Four-Phase Structure

1. **dry_run:** Analyze the test project, plan trajectory, identify risks. \
Produce diagnostic map entries. Status: `ORACLE_DRY_RUN_COMPLETE`.
2. **gate_a:** Human reviews the planned trajectory. Response: \
`APPROVE TRAJECTORY` or `MODIFY TRAJECTORY` or `ABORT`.
3. **green_run:** Execute the test project through the pipeline. Run tests, \
verify outputs, identify bugs. If bugs found, produce fix plan for Gate B. \
If no bugs: `ORACLE_ALL_CLEAR`.
4. **gate_b:** Human reviews the fix plan. Response: `APPROVE FIX` or \
`ABORT`. After fix: `ORACLE_FIX_APPLIED`. After abort: `ORACLE_HUMAN_ABORT`.

## Oracle Phase Transitions

- `dry_run` -> `gate_a`: on `ORACLE_DRY_RUN_COMPLETE`, routing sets \
`oracle_phase = "gate_a"`.
- `gate_a` -> `green_run`: on `APPROVE TRAJECTORY`, routing sets \
`oracle_phase = "green_run"`.
- `green_run` -> `gate_b`: oracle signals fix plan, routing sets \
`oracle_phase = "gate_b"`.
- `gate_b` -> `exit`: on `APPROVE FIX` or `ABORT`, routing sets \
`oracle_phase = "exit"`.
- `green_run` -> `exit`: on `ORACLE_ALL_CLEAR`, routing sets \
`oracle_phase = "exit"` directly.

## Multi-Turn Session

The oracle agent invocation spans `green_run` + Gate B as a multi-turn \
session: the oracle's green run invocation continues through the fix plan \
review gate, maintaining session state.

## Surrogate Human Protocol

For internal `/svp:bug` calls during green run:
- Auto-respond at Gate 6.0 (authorize debug session)
- Auto-respond at Gate 6.1 (triage confirmation)
- Auto-respond at Gate 6.2 (repair approval)

## Context Budget Management

- Selective analysis with reporting.
- Prioritize high-risk areas identified during dry run.

## Run Ledger

Cross-invocation memory stored at `.svp/oracle_run_ledger.json`. \
Each entry contains:
- `run_number` (int): sequential run number
- `exit_reason` (str): `"all_clear"`, `"fix_applied"`, or `"human_abort"`
- `abort_phase` (str or null): `"gate_a"` or `"gate_b"`, present only \
on abort
- `trajectory_summary` (str): compact description of planned trajectory
- `discoveries` (list of dicts): issues found with root causes, \
classifications, affected units
- `fix_targets` (list of str): units/files targeted for repair
- `root_causes_found` (list of str): root causes identified
- `root_causes_resolved` (list of str): root causes fixed and verified

## Diagnostic Map

Stored at `.svp/oracle_diagnostic_map.json`. Each entry contains:
- `event_id` (str): unique label, e.g. `"stage3.unit_foo.gate_a"`
- `classification` (str): `"PASS"`, `"FAIL"`, or `"WARN"`
- `observation` (str): what the oracle actually observed
- `expected` (str): what the spec says should happen
- `affected_artifact` (str): file path or artifact identifier affected

## Bounds

- Fix verification: 2 attempts max per bug.
- MODIFY TRAJECTORY: 3 per invocation.
"""


# ---------------------------------------------------------------------------
# Assembly helper functions
# ---------------------------------------------------------------------------


def _get_project_name(
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
    fallback: str = "",
) -> str:
    """Extract project name from profile or assembly config."""
    # Check assembly_config first for explicit project_name
    if "project_name" in assembly_config:
        return assembly_config["project_name"]
    # Check profile for name
    if "name" in profile:
        return profile["name"]
    # Check profile for project_name
    if "project_name" in profile:
        return profile["project_name"]
    return fallback


def _backup_existing(target: Path) -> None:
    """Rename existing directory to .bak.YYYYMMDD-HHMMSS."""
    if target.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{target.name}.bak.{timestamp}"
        backup_path = target.parent / backup_name
        target.rename(backup_path)


def _write_pyproject_toml(
    repo_dir: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
    project_name: str,
) -> None:
    """Generate pyproject.toml with project metadata and dependencies."""
    python_delivery = profile.get("delivery", {}).get("python", {})
    entry_points_enabled = python_delivery.get("entry_points", False)

    content_lines = [
        "[build-system]",
        'requires = ["setuptools>=61.0"]',
        'build-backend = "setuptools.backends._legacy:_Backend"',
        "",
        "[project]",
        f'name = "{project_name}"',
        'version = "0.1.0"',
        f'description = "{assembly_config.get("description", "")}"',
        'requires-python = ">=3.11"',
        "dependencies = []",
    ]

    if entry_points_enabled:
        content_lines.extend(
            [
                "",
                "[project.scripts]",
            ]
        )
        ep_config = python_delivery.get("entry_point_config", {})
        if ep_config:
            for name, target in ep_config.items():
                content_lines.append(f'{name} = "{target}"')
        else:
            content_lines.append(f'{project_name} = "{project_name}:main"')

    content_lines.append("")
    (repo_dir / "pyproject.toml").write_text("\n".join(content_lines))


def assemble_python_project(
    project_root: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
) -> Path:
    """Assemble a Python project repository.

    Creates target directory at {project_root.parent}/{project_name}-repo.
    Renames existing to .bak.YYYYMMDD-HHMMSS.
    Generates pyproject.toml with project metadata, dependencies, entry points.
    Source layout per profile["delivery"]["python"]["source_layout"].
    Returns path to created repository.
    """
    project_name = _get_project_name(profile, assembly_config, project_root.name)
    repo_dir = project_root.parent / f"{project_name}-repo"

    # Back up existing repo directory
    _backup_existing(repo_dir)

    # Create repo directory
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Read source layout from profile
    python_delivery = profile.get("delivery", {}).get("python", {})
    source_layout = python_delivery.get("source_layout", "conventional")

    # Create layout-specific structure
    package_name = project_name.replace("-", "_").replace(" ", "_")

    if source_layout == "conventional":
        # src/packagename/ layout
        src_pkg_dir = repo_dir / "src" / package_name
        src_pkg_dir.mkdir(parents=True, exist_ok=True)
        (src_pkg_dir / "__init__.py").write_text("")
    elif source_layout == "flat":
        # packagename/ layout
        pkg_dir = repo_dir / package_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "__init__.py").write_text("")
    elif source_layout == "svp_native":
        # scripts/ layout
        scripts_dir = repo_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Default to conventional
        src_pkg_dir = repo_dir / "src" / package_name
        src_pkg_dir.mkdir(parents=True, exist_ok=True)
        (src_pkg_dir / "__init__.py").write_text("")

    # Generate pyproject.toml
    _write_pyproject_toml(repo_dir, profile, assembly_config, project_name)

    return repo_dir


def assemble_r_project(
    project_root: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
) -> Path:
    """Assemble an R package repository.

    Creates R package structure: R/, man/, tests/testthat/.
    Generates DESCRIPTION, NAMESPACE.
    Returns path to created repository.
    """
    project_name = _get_project_name(profile, assembly_config, project_root.name)
    repo_dir = project_root.parent / f"{project_name}-repo"

    # Back up existing repo directory
    _backup_existing(repo_dir)

    # Create repo directory
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create R package directories
    (repo_dir / "R").mkdir(parents=True, exist_ok=True)
    (repo_dir / "man").mkdir(parents=True, exist_ok=True)
    (repo_dir / "tests" / "testthat").mkdir(parents=True, exist_ok=True)

    # Generate DESCRIPTION
    r_delivery = profile.get("delivery", {}).get("r", {})
    description_lines = [
        f"Package: {project_name.replace('-', '.')}",
        "Type: Package",
        f"Title: {assembly_config.get('description', project_name)}",
        "Version: 0.1.0",
        f"Author: {assembly_config.get('author', 'Unknown')}",
        f"Maintainer: {assembly_config.get('author', 'Unknown')} <unknown@example.com>",
        f"Description: {assembly_config.get('description', 'An R package.')}",
        "License: MIT + file LICENSE",
        "Encoding: UTF-8",
        "LazyData: true",
    ]

    # Add roxygen2 if configured
    r_quality = profile.get("quality", {}).get("r", {})
    if r_delivery.get("roxygen2", False) or assembly_config.get("roxygen2", False):
        description_lines.append("RoxygenNote: 7.2.3")

    description_lines.append("")
    (repo_dir / "DESCRIPTION").write_text("\n".join(description_lines))

    # Generate NAMESPACE
    namespace_content = (
        "# Generated by roxygen2: do not edit by hand\n\n"
        'exportPattern("^[[:alpha:]]")\n'
    )
    (repo_dir / "NAMESPACE").write_text(namespace_content)

    # Generate testthat.R in tests/
    pkg_r_name = project_name.replace("-", ".")
    testthat_r = (
        f'library(testthat)\nlibrary({pkg_r_name})\n\ntest_check("{pkg_r_name}")\n'
    )
    (repo_dir / "tests" / "testthat.R").write_text(testthat_r)

    return repo_dir


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

PROJECT_ASSEMBLERS: Dict[
    str, Callable[[Path, Dict[str, Any], Dict[str, Any]], Path]
] = {
    "python": assemble_python_project,
    "r": assemble_r_project,
}


# ---------------------------------------------------------------------------
# Assembly map generation
# ---------------------------------------------------------------------------


def _parse_file_tree_line(line: str):
    """Parse a single file tree line and return (depth, name, is_root) or None.

    Handles both pipe-tree format and space-indented format:
    - Pipe-tree: |   |-- filename.py
    - Space-indented:     filename.py
    - Root: dirname/
    """
    # Strip annotation if present
    path_part = line
    if "<-" in path_part:
        path_part = path_part[: path_part.index("<-")].rstrip()

    # Try pipe-tree format first: (|   )* [|+]-- name
    pipe_match = re.match(r"^([\s|]*)[|+]--\s+(.+)$", path_part)
    if pipe_match:
        indent = pipe_match.group(1)
        name = pipe_match.group(2).strip()
        # Calculate depth from the position of the connector
        connector_pos = path_part.index("+--" if "+--" in path_part else "|--")
        depth = connector_pos // 4 + 1
        return (depth, name, False)

    # Try space-indented format: leading spaces then name (file or dir/)
    stripped = path_part.rstrip()
    if not stripped:
        return None

    # Root line: no leading whitespace, ends with /
    lstripped = stripped.lstrip()
    leading_spaces = len(stripped) - len(lstripped)

    if leading_spaces == 0:
        # Root-level item
        if lstripped.endswith("/"):
            return (0, lstripped, True)
        return None

    # Indented item (space-indented format)
    # Calculate depth from indentation (2 spaces per level is common)
    name = lstripped
    if not name:
        return None

    # Determine indent unit: try to detect from context
    # Use 2-space indent as default for space-indented trees
    depth = leading_spaces // 2
    if depth < 1:
        depth = 1

    return (depth, name, False)


def generate_assembly_map(
    blueprint_dir: Path,
    project_root: Path,
) -> Dict[str, str]:
    """Parse blueprint file tree annotations and produce bidirectional mapping.

    Parses blueprint_prose.md from blueprint_dir for the Preamble file tree.
    Extracts every `<- Unit N` annotation line, parsing the indented path
    and the unit number.

    Produces a bidirectional mapping dict stored at .svp/assembly_map.json
    with two top-level keys:
    - "workspace_to_repo": maps src/unit_N/module.py -> repo path
    - "repo_to_workspace": the inverse mapping

    Bijectivity invariant: every workspace_to_repo entry has a corresponding
    repo_to_workspace entry, and vice versa.

    Returns the mapping dict (also written to disk).
    """
    blueprint_prose_path = blueprint_dir / "blueprint_prose.md"
    if not blueprint_prose_path.exists():
        raise FileNotFoundError(
            f"Blueprint prose file not found: {blueprint_prose_path}"
        )

    content = blueprint_prose_path.read_text()

    # Find the file tree in the Preamble section
    # The file tree is in a code block in the Preamble section
    preamble_match = re.search(
        r"## Preamble.*?```\n(.*?)```",
        content,
        re.DOTALL,
    )
    if not preamble_match:
        raise ValueError("Could not find Preamble file tree in blueprint_prose.md")

    file_tree_text = preamble_match.group(1)

    workspace_to_repo: Dict[str, str] = {}
    repo_to_workspace: Dict[str, str] = {}

    lines = file_tree_text.strip().split("\n")

    # Build a path stack to track the current directory context
    # path_stack[i] is the directory name at depth i
    path_stack: List[str] = []

    # Detect indent unit for space-indented trees
    indent_unit = _detect_indent_unit(lines)

    for line in lines:
        # Check for unit annotation
        annotation_match = re.search(r"<-\s*Unit\s+(\d+)", line)
        unit_number = int(annotation_match.group(1)) if annotation_match else None

        # Parse the line
        parsed = _parse_tree_line(line, indent_unit)
        if parsed is None:
            continue

        depth, name, is_root = parsed

        if is_root:
            # Root directory
            dir_name = name.rstrip("/")
            path_stack = [dir_name]
            continue

        is_dir = name.endswith("/")

        if is_dir:
            dir_name = name.rstrip("/")
            # Trim stack to parent depth, then set this level
            while len(path_stack) > depth:
                path_stack.pop()
            if len(path_stack) < depth:
                # Fill gaps (shouldn't normally happen)
                while len(path_stack) < depth:
                    path_stack.append("")
            path_stack.append(dir_name)
        else:
            # File entry
            # Trim stack to the parent directory depth
            while len(path_stack) > depth:
                path_stack.pop()

            if unit_number is not None:
                repo_path = "/".join(path_stack + [name])
                workspace_path = f"src/unit_{unit_number}/{name}"
                workspace_to_repo[workspace_path] = repo_path
                repo_to_workspace[repo_path] = workspace_path

    # Verify completeness: every <- Unit N annotation must have an entry
    annotation_pattern = re.compile(r"<-\s*Unit\s+(\d+)")
    all_annotations = annotation_pattern.findall(file_tree_text)
    if len(all_annotations) != len(workspace_to_repo):
        missing_count = len(all_annotations) - len(workspace_to_repo)
        raise ValueError(
            f"Assembly map incomplete: {missing_count} annotation(s) "
            f"could not be mapped. Found {len(all_annotations)} annotations "
            f"but only {len(workspace_to_repo)} mappings."
        )

    # Bijectivity invariant check
    for ws_path, rp_path in workspace_to_repo.items():
        if rp_path not in repo_to_workspace:
            raise ValueError(
                f"Bijectivity violation: workspace path {ws_path} maps to "
                f"repo path {rp_path} but reverse mapping is missing."
            )
    for rp_path, ws_path in repo_to_workspace.items():
        if ws_path not in workspace_to_repo:
            raise ValueError(
                f"Bijectivity violation: repo path {rp_path} maps to "
                f"workspace path {ws_path} but forward mapping is missing."
            )

    # Write to disk
    assembly_map = {
        "workspace_to_repo": workspace_to_repo,
        "repo_to_workspace": repo_to_workspace,
    }

    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    map_path = svp_dir / "assembly_map.json"
    map_path.write_text(json.dumps(assembly_map, indent=2) + "\n")

    return assembly_map


def _detect_indent_unit(lines: List[str]) -> int:
    """Detect the indentation unit used in a file tree.

    Returns the number of spaces per indentation level.
    Defaults to 2 if detection fails.
    """
    # Check if pipe-tree format is used
    for line in lines:
        if "|--" in line or "+--" in line:
            return 4  # Pipe-tree uses 4-char groups

    # For space-indented, find the smallest non-zero indent
    min_indent = None
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        # Skip lines that are annotations only
        if "<-" in stripped:
            stripped = stripped[: stripped.index("<-")].rstrip()
        lstripped = stripped.lstrip()
        leading = len(stripped) - len(lstripped)
        if leading > 0:
            if min_indent is None or leading < min_indent:
                min_indent = leading

    return min_indent if min_indent is not None else 2


def _parse_tree_line(line: str, indent_unit: int):
    """Parse a file tree line and return (depth, name, is_root) or None.

    Handles both pipe-tree format and space-indented format.
    """
    # Strip annotation if present
    path_part = line
    if "<-" in path_part:
        path_part = path_part[: path_part.index("<-")].rstrip()

    stripped = path_part.rstrip()
    if not stripped:
        return None

    # Try pipe-tree format: look for |-- or +--
    pipe_match = re.match(r"^([\s|]*)[|+]--\s+(.+)$", stripped)
    if pipe_match:
        name = pipe_match.group(2).strip()
        # Find the position of the connector to determine depth
        for connector in ("|--", "+--"):
            idx = stripped.find(connector)
            if idx >= 0:
                depth = idx // 4 + 1
                return (depth, name, False)

    # Space-indented format
    lstripped = stripped.lstrip()
    leading_spaces = len(stripped) - len(lstripped)

    if not lstripped:
        return None

    # Root-level item: no leading whitespace, name ends with /
    if leading_spaces == 0:
        if lstripped.endswith("/"):
            return (0, lstripped, True)
        # Could be a root-level file (unlikely in tree) -- skip
        return None

    # Indented item
    name = lstripped
    depth = leading_spaces // indent_unit
    if depth < 1:
        depth = 1

    return (depth, name, False)


# ---------------------------------------------------------------------------
# Regression test import adaptation CLI
# ---------------------------------------------------------------------------


def _apply_python_replacements(
    content: str,
    import_map: Dict[str, str],
) -> str:
    """Apply Python import replacements to file content."""
    for old_module, new_module in import_map.items():
        # Replace 'from X import Y' patterns
        content = re.sub(
            rf"from\s+{re.escape(old_module)}\s+import\s+",
            f"from {new_module} import ",
            content,
        )
        # Replace 'import X' patterns (full module import)
        content = re.sub(
            rf"^import\s+{re.escape(old_module)}\b",
            f"import {new_module}",
            content,
            flags=re.MULTILINE,
        )
        # Replace '@patch("X.Y")' and 'patch("X.Y")' patterns
        # Handle both decorator and inline forms
        content = re.sub(
            rf'@patch\(\s*"{re.escape(old_module)}\.([^"]+)"\s*\)',
            f'@patch("{new_module}.\\1")',
            content,
        )
        content = re.sub(
            rf'patch\(\s*"{re.escape(old_module)}\.([^"]+)"\s*\)',
            f'patch("{new_module}.\\1")',
            content,
        )
    return content


def _apply_r_replacements(
    content: str,
    import_map: Dict[str, str],
) -> str:
    """Apply R source() path replacements to file content."""
    for old_path, new_path in import_map.items():
        # Replace source("old_path") with source("new_path")
        content = re.sub(
            rf'source\(\s*"{re.escape(old_path)}"\s*\)',
            f'source("{new_path}")',
            content,
        )
        content = re.sub(
            rf"source\(\s*'{re.escape(old_path)}'\s*\)",
            f"source('{new_path}')",
            content,
        )
    return content


def adapt_regression_tests_main(argv: list = None) -> None:
    """CLI entry point for regression test import adaptation.

    Arguments:
        --map-file: path to regression_test_import_map.json
        --tests-dir: path to tests/regressions/
        --language: language identifier (optional)
    """
    parser = argparse.ArgumentParser(
        description="Adapt regression test imports.",
    )
    parser.add_argument(
        "--map-file",
        type=str,
        required=True,
        help="Path to regression_test_import_map.json",
    )
    parser.add_argument(
        "--tests-dir",
        type=str,
        required=True,
        help="Path to tests/regressions/ directory",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language identifier (optional, auto-detects from extension)",
    )

    args = parser.parse_args(argv)

    map_path = Path(args.map_file)
    tests_dir = Path(args.tests_dir)

    if not map_path.exists():
        print(f"Import map not found: {map_path}", file=sys.stderr)
        sys.exit(1)

    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}", file=sys.stderr)
        sys.exit(1)

    # Load the import map
    with open(map_path) as f:
        import_map = json.load(f)

    # Process each test file
    for test_file in sorted(tests_dir.iterdir()):
        if not test_file.is_file():
            continue

        # Determine language from file extension or --language flag
        language = args.language
        if language is None:
            if test_file.suffix == ".py":
                language = "python"
            elif test_file.suffix == ".R":
                language = "r"
            else:
                continue

        content = test_file.read_text()

        if language == "python":
            new_content = _apply_python_replacements(content, import_map)
        elif language == "r":
            new_content = _apply_r_replacements(content, import_map)
        else:
            continue

        # Only write if content changed (idempotent)
        if new_content != content:
            test_file.write_text(new_content)


if __name__ == "__main__":
    import sys

    adapt_regression_tests_main(sys.argv[1:])
