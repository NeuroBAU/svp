# GoL Plugin Blueprint -- Contracts (Tier 2 Signatures + Tier 3 Behavioral Contracts)

**Version:** 1.0
**Date:** 2026-03-29
**Spec version:** 1.0
**Archetype:** Claude Code Plugin (archetype C)
**Units:** 4

---

## Unit 1: GoL Strategies

### Tier 2 -- Signatures

```python
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import time

# Type aliases
Grid = List[List[int]]           # N x N grid of 0s and 1s
CellSet = Set[Tuple[int, int]]   # set of (row, col) alive coordinates
BenchmarkResult = Dict[str, Any] # result dict from benchmark()

class QuadNode:
    """Immutable quadtree node for hashlife."""
    nw: "QuadNode"
    ne: "QuadNode"
    sw: "QuadNode"
    se: "QuadNode"
    level: int
    population: int
    result: Optional["QuadNode"]  # cached RESULT for this node

    def __init__(
        self,
        nw: "QuadNode",
        ne: "QuadNode",
        sw: "QuadNode",
        se: "QuadNode",
    ) -> None: ...

    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...

# Module-level memo table
_memo: Dict[Tuple, "QuadNode"]

def clear_memo() -> None: ...

# --- Step functions ---

def naive_step(grid: Grid) -> Grid: ...

def hashlife_step(node: QuadNode) -> QuadNode: ...

def sparse_step(alive: CellSet) -> CellSet: ...

# --- Conversion ---

def grid_to_sparse(grid: Grid) -> CellSet: ...

def sparse_to_grid(alive: CellSet, n: int) -> Grid: ...

# --- Quadtree construction helpers ---

def make_leaf(alive: bool) -> QuadNode: ...

def grid_to_quadtree(grid: Grid) -> QuadNode: ...

def quadtree_to_grid(node: QuadNode) -> Grid: ...

# --- Benchmarking ---

def make_rpentomino_grid(n: int) -> Grid: ...

def make_rpentomino_sparse() -> CellSet: ...

def benchmark(
    strategy_fn: Callable,
    grid_size: int,
    generations: int,
    strategy_name: str,
) -> BenchmarkResult: ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None (root unit).

**QuadNode:**
- Immutable after construction. Fields are set in `__init__` and never modified.
- `level`: 0 for leaf nodes (single cell), increases by 1 per tree level.
- `population`: number of alive cells in the region. Leaf: 0 or 1. Internal: sum of children's populations.
- `result`: lazily computed. Initially `None`. Set once by `hashlife_step` and cached thereafter.
- `__hash__`: based on `id(nw), id(ne), id(sw), id(se)`. Enables hash-consing.
- `__eq__`: identity comparison (`self is other`). Two nodes with the same children are the same object (enforced by memo table).

**_memo:**
- Maps `(id(nw), id(ne), id(sw), id(se))` tuples to `QuadNode` instances.
- All `QuadNode` construction goes through a `_get_or_create` helper that checks memo first.
- `clear_memo()` resets `_memo` to empty dict and resets leaf singletons.

**naive_step:**
- Input: N x N grid (list of N lists, each of length N, containing 0 or 1).
- Output: new N x N grid representing the next generation.
- Algorithm: for each cell (r, c), count alive neighbors among the 8 adjacent cells (clamped to grid bounds). Apply B3/S23 rules. Write result to a fresh grid.
- Does not modify the input grid.
- Boundary: cells outside [0, N) are treated as dead.

**hashlife_step:**
- Input: `QuadNode` of level >= 2.
- Output: `QuadNode` representing the central region advanced by 2^(level-2) generations.
- If `node.result` is not None, returns cached result immediately.
- For level-2 nodes: evaluates all 16 cells directly using B3/S23 rules, returns a level-1 node.
- For level > 2: recursively computes 9 overlapping sub-results, combines them into 4 quadrants, recurses on those to produce the final result.
- Stores result in `node.result` before returning.
- Never modifies existing nodes (creates new nodes or returns cached ones).

**sparse_step:**
- Input: set of (row, col) tuples representing alive cells.
- Output: new set of (row, col) tuples representing the next generation.
- Algorithm: for each alive cell, add the cell and its 8 neighbors to a candidate set. For each candidate, count alive neighbors in the input set. Apply B3/S23 rules.
- Neighbor counting is order-independent (set lookup).
- Does not modify the input set.
- No boundary constraints (coordinates are arbitrary integers).

**grid_to_sparse:**
- Input: N x N grid.
- Output: set of (row, col) for all cells with value 1.

**sparse_to_grid:**
- Input: set of (row, col), integer `n` (grid dimension).
- Output: N x N grid. Cells in the set are 1; all others are 0.
- Coordinates outside [0, n) are silently dropped.

**make_leaf:**
- `alive=True`: returns a level-0 QuadNode with population 1.
- `alive=False`: returns a level-0 QuadNode with population 0.
- Uses singleton pattern: only two leaf nodes exist.

**grid_to_quadtree:**
- Input: N x N grid where N is a power of 2.
- If N is not a power of 2: pads to the next power of 2 with dead cells.
- Recursively divides the grid into quadrants.
- Returns a QuadNode of level log2(N).

**quadtree_to_grid:**
- Input: QuadNode.
- Output: 2^level x 2^level grid reconstructed from the tree.

**make_rpentomino_grid:**
- Input: integer `n` (grid size, must be >= 5).
- Output: N x N grid with R-pentomino centered.
- R-pentomino pattern (5 cells): (r-1, c), (r-1, c+1), (r, c-1), (r, c), (r+1, c), where r = n//2, c = n//2.
- All other cells are 0.

**make_rpentomino_sparse:**
- Returns: set of 5 tuples representing the R-pentomino centered at (0, 0).
- Pattern: {(-1, 0), (-1, 1), (0, -1), (0, 0), (1, 0)}.

**benchmark:**
- Constructs initial configuration: for `strategy_name` in `("naive", "hashlife")`, uses `make_rpentomino_grid(grid_size)`. For `"sparse"`, uses `make_rpentomino_sparse()`.
- For `"naive"`: calls `naive_step` in a loop for `generations` iterations, feeding each output as next input.
- For `"hashlife"`: converts grid to quadtree via `grid_to_quadtree`. Pads quadtree to sufficient level. Calls `hashlife_step`. Converts result back.
- For `"sparse"`: calls `sparse_step` in a loop for `generations` iterations.
- Timing: `time.perf_counter()` before and after the generation loop. Configuration construction is not included in timing.
- Computes `final_alive_count`: for grid-based strategies, counts cells with value 1. For sparse, length of the set.
- Returns: `{"strategy": strategy_name, "grid_size": grid_size, "generations": generations, "elapsed_seconds": <float>, "final_alive_count": <int>}`.
- Calls `clear_memo()` before hashlife runs to ensure clean memoization state.

**Correctness invariant:** For identical `grid_size` and `generations`, all three strategies must produce the same `final_alive_count`. This is verifiable post-benchmark.

---

## Unit 2: Plugin Infrastructure

### Tier 2 -- Signatures

```python
from typing import Any, Dict

# Plugin manifest (serialized to JSON during assembly)
PLUGIN_MANIFEST: Dict[str, Any]

# Agent definition markdown (string constants)
GENERATE_AGENT_DEF: str
EVALUATE_AGENT_DEF: str
REPORT_AGENT_DEF: str

# Skill definition markdown (string constant)
ORCHESTRATION_SKILL_DEF: str
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None (string constants).

**PLUGIN_MANIFEST:**
- Required fields: `name` ("gol-plugin"), `description` ("Game of Life implementation generator and benchmarking suite"), `version` ("1.0.0").
- `commands` field: list of 3 entries, each with `name` and `file` keys. Names: `"gol:generate"`, `"gol:evaluate"`, `"gol:report"`. Files: relative paths to command markdown files in `commands/`.
- `agents` field: list of 3 entries, each with `name` and `file` keys. Names: `"generator"`, `"evaluator"`, `"reporter"`. Files: relative paths to agent markdown files in `agents/`.
- `skills` field: list of 1 entry with `name` ("gol-orchestration") and `path` ("skills/orchestration").
- No `hooks`, `mcpServers`, `lspServers`, `tools`, or `outputStyles` fields.

**GENERATE_AGENT_DEF:**
- Frontmatter fields: `name` ("generator"), `description` ("Generates a Game of Life implementation using a specified strategy"), `model` (any), `allowed-tools` (Bash, Write, Read).
- Body instructions: accept strategy name parameter, produce a standalone Python file containing the selected step function plus a `main()` demo, include docstrings explaining the algorithm's complexity.
- Terminal status line: `GENERATION_COMPLETE`.

**EVALUATE_AGENT_DEF:**
- Frontmatter fields: `name` ("evaluator"), `description` ("Benchmarks a Game of Life implementation"), `model` (any), `allowed-tools` (Bash, Read, Write).
- Body instructions: import the strategy module at the given path, run `benchmark()` with each grid size (default: 50, 100, 200) and generation count (default: 100), write results to `<strategy>_benchmark.json`.
- Terminal status line: `EVALUATION_COMPLETE`.

**REPORT_AGENT_DEF:**
- Frontmatter fields: `name` ("reporter"), `description` ("Produces a ranked comparison of Game of Life benchmarks"), `model` (any), `allowed-tools` (Bash, Read, Write).
- Body instructions: read all `*_benchmark.json` files in the working directory, produce a markdown report with a table ranked by elapsed time per grid size, include performance ratio analysis (relative to fastest), include a recommendation paragraph, verify `final_alive_count` agreement across strategies.
- Terminal status line: `REPORT_COMPLETE`.

**ORCHESTRATION_SKILL_DEF:**
- Frontmatter fields: `name` ("gol-orchestration"), `description` ("Orchestrates the full Game of Life generate-evaluate-report workflow"), `argument-hint` ("Run the full GoL benchmark pipeline"), `allowed-tools` (Bash, Read, Write, agent invocations).
- Body: three-phase workflow:
  1. Generate phase: invoke generator agent 3 times (naive, hashlife, sparse).
  2. Evaluate phase: invoke evaluator agent 3 times (one per generated file).
  3. Report phase: invoke reporter agent once.
- Passes output file paths from generate to evaluate. No conditional logic -- all three strategies are always generated and evaluated.

---

## Unit 3: Command Definitions

### Tier 2 -- Signatures

```python
# Command definition markdown (string constants)
GENERATE_CMD_DEF: str
EVALUATE_CMD_DEF: str
REPORT_CMD_DEF: str
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None (string constants).

**GENERATE_CMD_DEF:**
- Command name: `gol:generate`.
- Description: "Generate a Game of Life implementation using a specified strategy."
- Arguments: `--strategy <naive|hashlife|sparse>` (required).
- Execution: invokes the `generator` agent, passing the strategy name.
- Usage example: `/gol:generate --strategy naive`.

**EVALUATE_CMD_DEF:**
- Command name: `gol:evaluate`.
- Description: "Benchmark a Game of Life implementation."
- Arguments: `--file <path>` (required), `--grid-sizes <comma-separated ints>` (optional, default "50,100,200"), `--generations <int>` (optional, default 100).
- Execution: invokes the `evaluator` agent, passing file path and parameters.
- Usage example: `/gol:evaluate --file naive_gol.py`.

**REPORT_CMD_DEF:**
- Command name: `gol:report`.
- Description: "Produce a ranked comparison of all Game of Life benchmarks."
- Arguments: none required.
- Execution: invokes the `reporter` agent.
- Usage example: `/gol:report`.

---

## Unit 4: Assembly

### Tier 2 -- Signatures

```python
from typing import Any, Dict
from pathlib import Path
import json
import shutil

class AssemblyError(Exception):
    """Raised when plugin assembly fails validation."""
    pass

def assemble_plugin(output_dir: Path) -> Path: ...

def _write_file(path: Path, content: str) -> None: ...

def _write_json(path: Path, data: Dict[str, Any]) -> None: ...

def _validate_assembly(plugin_root: Path) -> None: ...

def _copy_strategies(plugin_root: Path) -> None: ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** Unit 1, Unit 2, Unit 3.

**AssemblyError:**
- Custom exception. Carries a descriptive message identifying the validation failure.

**assemble_plugin:**
- Input: `output_dir` -- the target directory for the assembled plugin.
- Creates directory structure: `output_dir/.claude-plugin/`, `output_dir/agents/`, `output_dir/commands/`, `output_dir/skills/orchestration/`, `output_dir/strategies/`.
- Writes `plugin.json` via `_write_json(output_dir / ".claude-plugin" / "plugin.json", PLUGIN_MANIFEST)`.
- Writes agent definition files: `generator.md`, `evaluator.md`, `reporter.md` from `GENERATE_AGENT_DEF`, `EVALUATE_AGENT_DEF`, `REPORT_AGENT_DEF` respectively, into `output_dir/agents/`.
- Writes command definition files: `gol_generate.md`, `gol_evaluate.md`, `gol_report.md` from `GENERATE_CMD_DEF`, `EVALUATE_CMD_DEF`, `REPORT_CMD_DEF` respectively, into `output_dir/commands/`.
- Writes skill file: `SKILL.md` from `ORCHESTRATION_SKILL_DEF` into `output_dir/skills/orchestration/`.
- Copies strategies: calls `_copy_strategies(output_dir)`.
- Validates: calls `_validate_assembly(output_dir)`.
- Returns `output_dir` (as resolved Path).
- If `output_dir` exists, overwrites all contents (does not delete unrecognized files).
- Idempotent: running twice produces identical results.

**_write_file:**
- Writes `content` to `path` as UTF-8 text.
- Creates parent directories if needed.
- Atomic write: writes to a temporary file in the same directory, then renames.

**_write_json:**
- Serializes `data` to JSON with 2-space indent and trailing newline.
- Delegates to `_write_file` for the actual write.

**_validate_assembly:**
- Reads `plugin.json`, verifies it parses as valid JSON.
- Verifies required fields present: `name`, `description`, `version`.
- For each entry in `commands`, `agents`, `skills`: verifies the referenced file exists relative to `plugin_root`.
- Compiles `strategies/strategies.py` with `compile(source, filename, "exec")` to verify syntax.
- On any failure: raises `AssemblyError` with descriptive message.

**_copy_strategies:**
- Locates `strategies.py` source file (Unit 1) relative to the assembly module's location.
- Copies it to `plugin_root/strategies/strategies.py`.
- Preserves file content exactly (no transformation).
