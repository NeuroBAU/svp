# Unit 22: Project Templates
"""Templates for CLAUDE.md, config, state, toolchain,
ruff, readme, and Game of Life examples."""

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_TEMPLATE: str = "templates/svp_config_default.json"
INITIAL_STATE_TEMPLATE: str = "templates/pipeline_state_initial.json"
README_SVP_TEMPLATE: str = "templates/readme_svp.txt"
TOOLCHAIN_DEFAULT_TEMPLATE: str = "toolchain_defaults/python_conda_pytest.json"
RUFF_CONFIG_TEMPLATE: str = "toolchain_defaults/ruff.toml"


def generate_claude_md(project_name: str, project_root: Path) -> str:
    """Generate CLAUDE.md content for a project."""
    if not project_name:
        raise ValueError("Project name must not be empty")
    return f"""\
# SVP-Managed Project: {project_name}

This project is managed by the Stratified Verification
Pipeline (SVP). You are the orchestration layer.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and
outputs a structured action block telling you exactly
what to do next. Execute its output.
"""


_DEFAULT_CONFIG: Dict[str, Any] = {
    "iteration_limit": 3,
    "models": {
        "test_agent": "claude-opus-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6",
    },
    "context_budget_override": None,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": True,
    "skip_permissions": True,
}

SVP_CONFIG_DEFAULT_JSON_CONTENT: str = json.dumps(_DEFAULT_CONFIG, indent=2)

_INITIAL_STATE: Dict[str, Any] = {
    "stage": "0",
    "sub_stage": "hook_activation",
    "current_unit": None,
    "total_units": None,
    "fix_ladder_position": None,
    "red_run_retries": 0,
    "alignment_iteration": 0,
    "verified_units": [],
    "pass_history": [],
    "log_references": {},
    "project_name": None,
    "last_action": None,
    "debug_session": None,
    "debug_history": [],
    "redo_triggered_from": None,
    "delivered_repo_path": None,
    "created_at": "",
    "updated_at": "",
}

PIPELINE_STATE_INITIAL_JSON_CONTENT: str = json.dumps(_INITIAL_STATE, indent=2)

README_SVP_TXT_CONTENT: str = """\
SVP -- Stratified Verification Pipeline

This project workspace is managed by SVP 2.1.

Do not edit pipeline infrastructure files manually.
Use the SVP slash commands (/save, /quit, /status,
/help, /hint, /ref, /redo, /bug, /clean) to interact
with the pipeline.

For more information, see the SVP documentation.
"""

_TOOLCHAIN_DEFAULT: Dict[str, Any] = {
    "environment": {
        "type": "conda",
        "run_prefix": "conda run -n {env_name}",
        "create": ("conda create -n {env_name} python={python_version} -y"),
        "install": ("conda run -n {env_name} pip install {packages}"),
    },
    "testing": {
        "framework": "pytest",
        "run": ("{run_prefix} python -m pytest {target} {flags}"),
        "framework_packages": ["pytest"],
        "collection_error_indicators": [
            "ModuleNotFoundError",
            "ImportError",
            "SyntaxError",
            "no tests ran",
        ],
    },
    "packaging": {
        "backend": "setuptools",
        "build": "{run_prefix} python -m build",
    },
    "vcs": {
        "system": "git",
        "init": "git init",
        "add": "git add .",
        "commit": 'git commit -m "{message}"',
    },
    "language": {
        "name": "python",
        "version": "{python_version}",
    },
    "file_structure": {
        "source_dir": "src",
        "test_dir": "tests",
        "docs_dir": "docs",
    },
    "quality": {
        "formatter": {
            "format": ("{run_prefix} ruff format {target}"),
            "check": ("{run_prefix} ruff format --check {target}"),
        },
        "linter": {
            "light": ("{run_prefix} ruff check --fix {target}"),
            "heavy": ("{run_prefix} ruff check {target}"),
            "check": ("{run_prefix} ruff check {target}"),
        },
        "type_checker": {
            "check": ("{run_prefix} mypy {target} {flags}"),
            "unit_flags": "--ignore-missing-imports",
            "project_flags": "",
        },
        "packages": ["ruff", "mypy"],
        "gate_a": [
            "linter.light",
            "formatter.format",
        ],
        "gate_b": [
            "linter.light",
            "formatter.format",
        ],
        "gate_c": [
            "linter.check",
            "formatter.check",
        ],
    },
}

TOOLCHAIN_DEFAULT_JSON_CONTENT: str = json.dumps(_TOOLCHAIN_DEFAULT, indent=2)

RUFF_CONFIG_TOML_CONTENT: str = """\
line-length = 88

[lint]
select = ["E", "F", "W", "I"]
ignore = []

[format]
quote-style = "double"
indent-style = "space"
"""

CLAUDE_MD_PY_CONTENT: str = """\
\"\"\"Template for generating CLAUDE.md files.\"\"\"

from pathlib import Path


def generate(project_name: str, project_root: Path):
    \"\"\"Return CLAUDE.md content for project.\"\"\"
    return f\"\"\"\\
# SVP-Managed Project: {project_name}

This project is managed by SVP.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```
\"\"\"
"""

GOL_STAKEHOLDER_SPEC_CONTENT: str = """\
# Game of Life -- Stakeholder Specification

## Overview
Conway's Game of Life cellular automaton.

## Functional Requirements
1. Initialize grid from patterns or random state.
2. Step simulation forward by one generation.
3. Display grid state as text output.
4. Detect stable/oscillating states.

## Non-Functional Requirements
- Pure Python, no external dependencies.
- Grid size configurable up to 100x100.
"""

GOL_BLUEPRINT_PROSE_CONTENT: str = """\
# Game of Life -- Blueprint Prose

## Unit 1: Grid Module
Manages the 2D grid data structure. Provides
create, get, set, and neighbors operations.

## Unit 2: Rules Engine
Implements Conway's rules: birth, survival, death.

## Unit 3: Simulation Controller
Steps the simulation and detects termination.

## Unit 4: Display
Renders the grid as text output.
"""

GOL_BLUEPRINT_CONTRACTS_CONTENT: str = """\
# Game of Life -- Blueprint Contracts

## Unit 1: Grid Module
```python
def create_grid(rows: int, cols: int) -> list: ...
def get_cell(grid, row, col) -> int: ...
def set_cell(grid, row, col, value) -> None: ...
def get_neighbors(grid, row, col) -> list: ...
```

## Unit 2: Rules Engine
```python
def apply_rules(cell, neighbor_count) -> int: ...
def step(grid) -> list: ...
```
"""

GOL_PROJECT_CONTEXT_CONTENT: str = """\
# Game of Life -- Project Context

## Purpose
Educational implementation of Conway's Game of Life.

## Target Users
Students learning cellular automata and Python.

## Constraints
- Python 3.11+
- No external dependencies
- CLI interface only
"""
