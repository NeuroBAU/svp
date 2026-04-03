# GoL Plugin -- Stakeholder Specification

**Version:** 1.0
**Date:** 2026-03-29
**Archetype:** Claude Code Plugin (archetype C)

---

## 1. Purpose and Scope

GoL Plugin is a Claude Code plugin that generates, benchmarks, and compares three implementations of Conway's Game of Life. It demonstrates the Claude Code plugin archetype with mixed artifact types: Python computation code, plugin manifest JSON, and plugin markdown definitions for agents, skills, and commands.

The plugin targets developers who want to explore algorithmic trade-offs in cellular automata without writing boilerplate. The three strategies span a wide performance range: naive grid scan (simple, slow), hashlife (complex, fast for large patterns), and sparse set (moderate complexity, fast for sparse patterns).

### 1.1 What Success Looks Like

A user installs the plugin, runs `/gol:generate` three times (once per strategy), runs `/gol:evaluate` on each, and runs `/gol:report` to see a ranked comparison table. The entire workflow can also be driven by the orchestration skill in a single invocation.

### 1.2 Out of Scope

- Visualization or graphical rendering of Game of Life grids.
- Custom rule sets (only standard B3/S23 rules).
- Distributed or GPU-accelerated implementations.
- Persistent storage of benchmark results across sessions.

---

## 2. Game of Life Rules

Conway's Game of Life operates on an infinite two-dimensional grid of cells, each either alive (1) or dead (0). Each cell has eight neighbors (horizontal, vertical, diagonal). The rules applied simultaneously to every cell each generation:

1. **Underpopulation:** A live cell with fewer than 2 live neighbors dies.
2. **Survival:** A live cell with 2 or 3 live neighbors survives.
3. **Overpopulation:** A live cell with more than 3 live neighbors dies.
4. **Reproduction:** A dead cell with exactly 3 live neighbors becomes alive.

All implementations must produce identical results for the same initial configuration after the same number of generations. This is the correctness invariant.

---

## 3. Strategy Descriptions

### 3.1 Naive Grid Scan

The simplest implementation. Allocates an N x N grid, iterates over every cell each generation, counts neighbors by examining the 8 adjacent cells with boundary clamping.

- **Time complexity:** O(N^2) per generation, where N is the grid dimension.
- **Space complexity:** O(N^2) for two grid copies (current and next).
- **Boundary handling:** Cells outside the grid are treated as dead (fixed boundary).
- **Strengths:** Trivial to understand and verify. No data structure overhead.
- **Weaknesses:** Cost is proportional to grid area regardless of live cell count. Unusable for large sparse grids.

### 3.2 Hashlife

A recursive memoized quadtree algorithm. The grid is represented as a tree of nested quadrants. Each node stores its four children (NW, NE, SW, SE) and caches the result of advancing by 2^(level-2) generations. Identical sub-patterns share nodes via a hash-consing memo table.

- **Time complexity:** O(k log k) amortized for k unique sub-patterns. Sub-linear in grid area for repetitive patterns.
- **Space complexity:** O(k) for k unique quadtree nodes, plus memo table overhead.
- **Boundary handling:** The quadtree expands as needed; effectively infinite grid.
- **Strengths:** Dramatically faster for large grids with repetitive structure (e.g., spaceships, oscillators).
- **Weaknesses:** High constant overhead. Slower than naive for small grids or random configurations. Complex implementation.

### 3.3 Sparse Set

Tracks only alive cells as a set of (row, column) coordinate tuples. Each generation, collects all cells that could change state (alive cells and their neighbors), evaluates the rules for each candidate, and produces the new alive set.

- **Time complexity:** O(a) per generation, where a is the number of alive cells (each alive cell contributes at most 9 candidates).
- **Space complexity:** O(a) for the alive set plus O(a) for the candidate set.
- **Boundary handling:** No boundary -- coordinates are unbounded integers.
- **Strengths:** Fast for sparse configurations. Memory proportional to alive cells, not grid area.
- **Weaknesses:** Slower than naive when the grid is densely populated (most cells alive). Set operations have hash overhead.

---

## 4. Benchmarking Methodology

### 4.1 Benchmark Function

A single `benchmark` function wraps any strategy function. It accepts the strategy callable, a grid size (integer side length), and a generation count. It constructs a deterministic initial configuration, runs the strategy for the specified number of generations, and records wall-clock elapsed time using `time.perf_counter`.

### 4.2 Initial Configuration

The benchmark uses a deterministic seed pattern: an R-pentomino centered in the grid. The R-pentomino is a well-known methuselah that produces complex long-lived evolution from five initial cells. The pattern is:

```
.X.
XX.
.X.
```

For the sparse strategy, the initial configuration is a set of five coordinate tuples. For grid-based strategies, the pattern is placed at the center of the N x N grid.

### 4.3 Measurement Protocol

Each benchmark run:

1. Constructs the initial configuration for the given grid size.
2. Converts the configuration to the strategy's native representation.
3. Records start time (`time.perf_counter`).
4. Runs the strategy for the specified number of generations.
5. Records end time.
6. Returns a result dict: `{"strategy": <name>, "grid_size": <N>, "generations": <G>, "elapsed_seconds": <float>, "final_alive_count": <int>}`.

The `final_alive_count` field enables correctness cross-checking: all strategies must agree on the alive count for the same inputs.

### 4.4 Default Benchmark Parameters

- Grid sizes: 50, 100, 200.
- Generations: 100.
- These are defaults; the `/gol:evaluate` command accepts overrides.

---

## 5. Plugin Structure

### 5.1 Delivered Directory Layout

```
gol-plugin/
|-- .claude-plugin/
|   +-- plugin.json
|-- agents/
|   |-- generator.md
|   |-- evaluator.md
|   +-- reporter.md
|-- commands/
|   |-- gol_generate.md
|   |-- gol_evaluate.md
|   +-- gol_report.md
|-- skills/
|   +-- orchestration/
|       +-- SKILL.md
+-- strategies/
    +-- strategies.py
```

### 5.2 Plugin Manifest (plugin.json)

The plugin manifest follows the Claude Code plugin schema:

- **name:** `"gol-plugin"`
- **description:** `"Game of Life implementation generator and benchmarking suite"`
- **version:** `"1.0.0"`
- **commands:** References to the three `/gol:*` command definition files.
- **agents:** References to the three agent definition files.
- **skills:** Reference to the orchestration skill.

No hooks, MCP servers, LSP servers, or tools are required.

### 5.3 Agent Definitions

Three agents, each producing a different artifact:

**Generator Agent** (`agents/generator.md`):
- Accepts a strategy name parameter (naive, hashlife, or sparse).
- Produces a standalone Python file implementing the selected GoL strategy.
- The produced file includes the step function, a `main()` that runs a demo, and docstrings explaining the algorithm.
- Terminal status: `GENERATION_COMPLETE`.

**Evaluator Agent** (`agents/evaluator.md`):
- Accepts a path to a previously generated strategy file and optional benchmark parameters (grid sizes, generation count).
- Imports the strategy module, runs the benchmark function with each grid size, and writes results to a JSON file.
- Terminal status: `EVALUATION_COMPLETE`.

**Reporter Agent** (`agents/reporter.md`):
- Reads all benchmark result JSON files in the working directory.
- Produces a markdown report with a ranked comparison table (sorted by elapsed time per grid size), performance ratio analysis, and a recommendation paragraph.
- Terminal status: `REPORT_COMPLETE`.

### 5.4 Orchestration Skill

The orchestration skill (`skills/orchestration/SKILL.md`) coordinates the full workflow:

1. Generate all three implementations (invoke generator agent three times).
2. Evaluate each implementation (invoke evaluator agent three times).
3. Produce the comparison report (invoke reporter agent once).

The skill handles sequencing and passes output paths between steps. It does not make algorithmic decisions -- it is purely mechanical coordination.

### 5.5 Slash Commands

**`/gol:generate`** (`commands/gol_generate.md`):
- Argument: `--strategy <naive|hashlife|sparse>` (required).
- Invokes the generator agent with the selected strategy.
- Writes the generated file to the current working directory.

**`/gol:evaluate`** (`commands/gol_evaluate.md`):
- Argument: `--file <path>` (required). Path to a generated strategy file.
- Optional: `--grid-sizes <comma-separated ints>`, `--generations <int>`.
- Invokes the evaluator agent.
- Writes benchmark results to `<strategy>_benchmark.json`.

**`/gol:report`** (`commands/gol_report.md`):
- No required arguments. Reads all `*_benchmark.json` files in the current directory.
- Invokes the reporter agent.
- Writes the report to `gol_report.md`.

---

## 6. Correctness Requirements

### 6.1 Strategy Equivalence

For any initial configuration and generation count, all three strategies must produce the same set of alive cells. The benchmark's `final_alive_count` field provides a lightweight check; the evaluator agent performs a full cell-set comparison when multiple strategies have been benchmarked with identical parameters.

### 6.2 Determinism

All strategies must be fully deterministic. No randomness, no floating-point nondeterminism, no dependency on iteration order of unordered collections (the sparse strategy must sort candidates or use an order-independent algorithm).

### 6.3 Edge Cases

- **Empty grid:** Zero alive cells. All strategies must return an empty grid / empty set after any number of generations.
- **Single cell:** Dies immediately (underpopulation). All strategies must return empty after one generation.
- **Still life (block):** A 2x2 block of alive cells. Must remain unchanged indefinitely.
- **Oscillator (blinker):** Three horizontal cells. Must alternate between horizontal and vertical orientation with period 2.

---

## 7. Performance Expectations

These are not hard requirements but expected orderings for the default benchmark parameters:

- **Grid 50x50, 100 generations:** Naive and sparse comparable; hashlife slower due to overhead.
- **Grid 200x200, 100 generations:** Sparse fastest (R-pentomino is sparse); naive slowest; hashlife intermediate.
- **Very large grids (1000+):** Hashlife dominates for structured patterns; sparse dominates for sparse patterns; naive unusable.

The report should note when observed performance deviates from these expectations and explain why.

---

## 8. Assembly Requirements

### 8.1 Assembly Function

The `assemble_plugin` function in `assembly.py` creates the delivered plugin directory structure from the implementation units. It:

1. Creates the output directory and all subdirectories (`.claude-plugin/`, `agents/`, `commands/`, `skills/orchestration/`, `strategies/`).
2. Writes `plugin.json` from the `PLUGIN_MANIFEST` constant.
3. Writes each agent definition file from the corresponding `*_AGENT_DEF` constant.
4. Writes each command definition file from the corresponding `*_CMD_DEF` constant.
5. Writes the orchestration skill from the `ORCHESTRATION_SKILL_DEF` constant.
6. Copies `strategies.py` source code into `strategies/`.

### 8.2 Idempotency

Running `assemble_plugin` twice with the same output directory produces identical results. If the output directory already exists, its contents are overwritten.

### 8.3 Validation

After assembly, the function verifies:
- `plugin.json` is valid JSON and contains required fields.
- All files referenced in `plugin.json` exist at their expected paths.
- `strategies.py` is syntactically valid Python (`compile()` succeeds).

Assembly returns the path to the created plugin directory on success, or raises `AssemblyError` with a descriptive message on failure.
