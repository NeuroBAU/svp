"""Project Templates -- template files used during project bootstrap.

Defines the CLAUDE.md generator, the default svp_config.json, the initial
pipeline_state.json, the README_SVP.txt protection notice, and the bundled
Game of Life example project content.
"""

import json
from typing import Dict, Any
from pathlib import Path

# ---------------------------------------------------------------------------
# Template file paths
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_TEMPLATE: str = "templates/svp_config_default.json"
INITIAL_STATE_TEMPLATE: str = "templates/pipeline_state_initial.json"
README_SVP_TEMPLATE: str = "templates/readme_svp.txt"


# ---------------------------------------------------------------------------
# generate_claude_md
# ---------------------------------------------------------------------------

def generate_claude_md(project_name: str, project_root: Path) -> str:
    """Generate the complete CLAUDE.md file content for a new SVP project.

    Raises ValueError if project_name is empty.
    """
    if not project_name:
        raise ValueError("Project name must not be empty")

    return f"""# SVP-Managed Project: {project_name}

This project is managed by the **Stratified Verification Pipeline (SVP)**. You are the orchestration layer \u2014 the main session. Your behavior is fully constrained by deterministic scripts. Do not improvise pipeline flow.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and outputs a structured action block telling you exactly what to do next. Execute its output. Do not reason about what stage the pipeline is in or what should happen next.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated:

1. **Run the routing script** \u2192 receive a structured action block.
2. **Run the PREPARE command** (if present) \u2192 produces a task prompt or gate prompt file.
3. **Execute the ACTION** (invoke agent / run command / present gate).
4. **Write the result to `.svp/last_status.txt`** (agent terminal status line or constructed command status).
5. **Run the POST command** (if present) \u2192 updates pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps.

## Verbatim Task Prompt Relay

When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.

## Do Not Improvise

- Do not decide which state update to call.
- Do not construct arguments for state scripts.
- Do not evaluate agent outputs for correctness.
- Do not hold domain conversation history.
- Do not reason about pipeline flow.

The routing script makes every decision. You execute.

## Human Input During Autonomous Sequences

During autonomous sequences (agent invocations, command executions), defer human input. If the human types during an autonomous sequence, acknowledge briefly and defer: complete the current action cycle before engaging.

## Detailed Protocol

For the complete orchestration protocol \u2014 action type handling, status line construction, gate presentation rules, session boundary handling \u2014 refer to the **SVP orchestration skill** (`svp-orchestration`).
"""


# ---------------------------------------------------------------------------
# CLAUDE_MD_PY_CONTENT -- Python module with render_claude_md function
# ---------------------------------------------------------------------------

CLAUDE_MD_PY_CONTENT: str = '''"""CLAUDE.md template generator for SVP projects."""


def render_claude_md(project_name: str) -> str:
    """Render the CLAUDE.md content for a new SVP project.

    Parameters
    ----------
    project_name : str
        The name of the project to embed in the generated CLAUDE.md.

    Returns
    -------
    str
        The complete CLAUDE.md file content.
    """
    if not project_name:
        raise ValueError("Project name must not be empty")

    return f"""# SVP-Managed Project: {project_name}

This project is managed by the **Stratified Verification Pipeline (SVP)**. You are the orchestration layer \u2014 the main session. Your behavior is fully constrained by deterministic scripts. Do not improvise pipeline flow.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and outputs a structured action block telling you exactly what to do next. Execute its output. Do not reason about what stage the pipeline is in or what should happen next.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated:

1. **Run the routing script** \\u2192 receive a structured action block.
2. **Run the PREPARE command** (if present) \\u2192 produces a task prompt or gate prompt file.
3. **Execute the ACTION** (invoke agent / run command / present gate).
4. **Write the result to `.svp/last_status.txt`** (agent terminal status line or constructed command status).
5. **Run the POST command** (if present) \\u2192 updates pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps.

## Verbatim Task Prompt Relay

When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.

## Do Not Improvise

- Do not decide which state update to call.
- Do not construct arguments for state scripts.
- Do not evaluate agent outputs for correctness.
- Do not hold domain conversation history.
- Do not reason about pipeline flow.

The routing script makes every decision. You execute.

## Human Input During Autonomous Sequences

During autonomous sequences (agent invocations, command executions), defer human input. If the human types during an autonomous sequence, acknowledge briefly and defer: complete the current action cycle before engaging.

## Detailed Protocol

For the complete orchestration protocol \\u2014 action type handling, status line construction, gate presentation rules, session boundary handling \\u2014 refer to the **SVP orchestration skill** (`svp-orchestration`).
"""
'''


# ---------------------------------------------------------------------------
# SVP_CONFIG_DEFAULT_JSON_CONTENT -- matches Unit 1's DEFAULT_CONFIG
# ---------------------------------------------------------------------------

SVP_CONFIG_DEFAULT_JSON_CONTENT: str = json.dumps(
    {
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
    },
    indent=2,
) + "\n"


# ---------------------------------------------------------------------------
# PIPELINE_STATE_INITIAL_JSON_CONTENT -- matches Unit 2's create_initial_state
# with a placeholder for project_name
# ---------------------------------------------------------------------------

PIPELINE_STATE_INITIAL_JSON_CONTENT: str = json.dumps(
    {
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
        "created_at": None,
        "updated_at": None,
    },
    indent=2,
) + "\n"


# ---------------------------------------------------------------------------
# README_SVP_TXT_CONTENT -- protection notice for SVP-managed projects
# ---------------------------------------------------------------------------

README_SVP_TXT_CONTENT: str = """\
================================================================================
                        SVP-MANAGED PROJECT NOTICE
================================================================================

This project is managed by the Stratified Verification Pipeline (SVP).

IMPORTANT: Files in this project are protected by a two-layer write
authorization system:

  1. Pre-commit hooks prevent unauthorized modifications to pipeline-controlled
     files (pipeline_state.json, blueprint documents, verified source files).

  2. The SVP orchestration layer enforces write permissions at runtime,
     ensuring that only authorized pipeline operations can modify protected
     artifacts.

Do NOT manually edit pipeline-controlled files. All changes must flow through
the SVP pipeline to maintain verification integrity.

To interact with this project, use the `svp` command:

    svp start          Start or resume the pipeline
    svp status         Show current pipeline state
    svp restore        Restore example project files
    svp help           Show available commands

For more information about SVP, refer to the project documentation.

================================================================================
"""


# ---------------------------------------------------------------------------
# Bundled Game of Life example (carry-forward from v1.1)
# ---------------------------------------------------------------------------

GOL_STAKEHOLDER_SPEC_CONTENT: str = """\
# Game of Life -- Stakeholder Specification

## Overview

This project implements **Conway's Game of Life**, a cellular automaton devised
by the British mathematician John Horton Conway in 1970. The Game of Life is a
zero-player game: its evolution is determined by its initial state, requiring no
further input from the human.

## Requirements

### Core Simulation

1. The simulation operates on a two-dimensional grid of cells.
2. Each cell is either **alive** or **dead**.
3. The grid wraps around (toroidal topology) so that edges connect.
4. At each time step, the following rules apply simultaneously to every cell:
   - A live cell with fewer than 2 live neighbors dies (underpopulation).
   - A live cell with 2 or 3 live neighbors survives.
   - A live cell with more than 3 live neighbors dies (overpopulation).
   - A dead cell with exactly 3 live neighbors becomes alive (reproduction).

### Grid Management

5. The grid must support arbitrary rectangular dimensions (minimum 3x3).
6. Users can set the initial state by specifying live cell coordinates.
7. The simulation must support loading initial patterns from a simple text format.

### Display

8. The simulation must provide a text-based display of the grid state.
9. Live cells are displayed as `#` and dead cells as `.`.
10. The display must include a generation counter.

### Simulation Control

11. The simulation must support stepping forward one generation at a time.
12. The simulation must support running for a specified number of generations.
13. The simulation must detect when the grid reaches a stable state (no changes)
    and report this to the user.

### Well-Known Patterns

14. The implementation must include built-in patterns:
    - **Block** (still life, 2x2)
    - **Blinker** (oscillator, period 2)
    - **Glider** (spaceship)

## Non-Functional Requirements

- The implementation must be in pure Python (no external dependencies).
- The code must be well-documented with docstrings.
- All public functions must have type annotations.
"""


GOL_BLUEPRINT_CONTENT: str = """\
# Game of Life -- Blueprint

## Architecture Overview

The Game of Life implementation is decomposed into three units that handle grid
management, simulation rules, and display/control respectively.

## Unit 1: Grid

**Description:** Manages the two-dimensional grid data structure with toroidal
(wrapping) boundary conditions. Provides cell access, neighbor counting, and
pattern loading.

### Signatures

```python
from typing import List, Set, Tuple

class Grid:
    def __init__(self, width: int, height: int) -> None: ...
    def get(self, x: int, y: int) -> bool: ...
    def set(self, x: int, y: int, alive: bool) -> None: ...
    def count_neighbors(self, x: int, y: int) -> int: ...
    def get_live_cells(self) -> Set[Tuple[int, int]]: ...
    def load_pattern(self, pattern: str, offset_x: int = 0, offset_y: int = 0) -> None: ...
    def clear(self) -> None: ...
    @property
    def dimensions(self) -> Tuple[int, int]: ...
```

### Contracts

- Grid dimensions must be at least 3x3; raise ValueError otherwise.
- Coordinates wrap around using modular arithmetic (toroidal topology).
- `count_neighbors` returns the count of live cells among the 8 adjacent cells.
- `load_pattern` parses a text pattern where `#` = alive, `.` = dead, newlines
  separate rows.

## Unit 2: Simulation

**Description:** Implements Conway's Game of Life rules and simulation stepping.
Applies the four rules simultaneously to produce the next generation.

### Signatures

```python
from typing import Optional

class Simulation:
    def __init__(self, grid: "Grid") -> None: ...
    @property
    def generation(self) -> int: ...
    def step(self) -> bool: ...
    def run(self, generations: int) -> int: ...
    def is_stable(self) -> bool: ...
```

### Contracts

- `step()` applies all four rules simultaneously, increments generation counter,
  and returns True if the grid changed.
- `run(n)` calls step() up to n times, stopping early if stable. Returns the
  number of steps actually taken.
- `is_stable()` returns True if the last step produced no changes.

### Dependencies

- Unit 1 (Grid): Uses Grid for cell access and neighbor counting.

## Unit 3: Display and Patterns

**Description:** Provides text-based grid rendering and built-in pattern
definitions for well-known Game of Life configurations.

### Signatures

```python
from typing import Dict

def render(grid: "Grid") -> str: ...
def render_with_info(grid: "Grid", generation: int) -> str: ...

PATTERNS: Dict[str, str]
# Must include at minimum: "block", "blinker", "glider"
```

### Contracts

- `render()` produces a string with `#` for alive, `.` for dead, rows separated
  by newlines.
- `render_with_info()` prepends a `Generation: N` header line.
- `PATTERNS` dict maps pattern names to text patterns loadable by
  `Grid.load_pattern`.

### Dependencies

- Unit 1 (Grid): Uses Grid for cell access and dimensions.
"""


GOL_PROJECT_CONTEXT_CONTENT: str = """\
# Game of Life -- Project Context

## Project Description

This project implements Conway's Game of Life as a demonstration of the SVP
(Stratified Verification Pipeline) build process. The Game of Life is a classic
cellular automaton that serves as an excellent example for test-driven
development because it has well-defined rules and easily verifiable behavior.

## Technical Context

- **Language:** Python 3.10+
- **Dependencies:** None (pure Python)
- **Test Framework:** pytest
- **Build System:** SVP (Stratified Verification Pipeline)

## Domain Knowledge

Conway's Game of Life operates on an infinite two-dimensional grid of cells.
Each cell can be in one of two states: alive or dead. The state of every cell
changes simultaneously based on the states of its eight neighbors according to
four simple rules:

1. **Underpopulation:** A live cell with fewer than 2 live neighbors dies.
2. **Survival:** A live cell with 2 or 3 live neighbors survives.
3. **Overpopulation:** A live cell with more than 3 live neighbors dies.
4. **Reproduction:** A dead cell with exactly 3 live neighbors becomes alive.

For this implementation, we use a finite grid with toroidal (wrapping) boundary
conditions, meaning the grid's edges connect to the opposite side.

## Key Patterns Used in Testing

- **Block:** A 2x2 square of live cells. This is a \"still life\" -- it does
  not change from one generation to the next.
- **Blinker:** Three cells in a row. This is a period-2 oscillator -- it
  alternates between horizontal and vertical orientations.
- **Glider:** A five-cell pattern that translates diagonally across the grid,
  repeating its shape every 4 generations.

## File Structure

```
src/
  unit_1/stub.py    # Grid implementation
  unit_2/stub.py    # Simulation implementation
  unit_3/stub.py    # Display and patterns
tests/
  test_unit_1.py    # Grid tests
  test_unit_2.py    # Simulation tests
  test_unit_3.py    # Display and patterns tests
```

## Notes for Development

- The grid uses 0-based indexing with (x, y) coordinates where x is the column
  and y is the row.
- All coordinate wrapping must use modular arithmetic to implement toroidal
  boundary conditions.
- When loading patterns, `#` represents alive cells and `.` represents dead
  cells. Rows are separated by newlines.
"""
