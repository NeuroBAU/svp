# GoL Plugin Blueprint -- Prose (Tier 1 Descriptions)

**Version:** 1.0
**Date:** 2026-03-29
**Spec version:** 1.0
**Archetype:** Claude Code Plugin (archetype C)
**Units:** 4

---

## Preamble: Delivered File Tree

The file tree below maps workspace unit implementations to their final paths in the delivered plugin.

```
gol-plugin/                            <- plugin root
|-- .claude-plugin/
|   +-- plugin.json                    <- Unit 2
|-- agents/
|   |-- generator.md                   <- Unit 2
|   |-- evaluator.md                   <- Unit 2
|   +-- reporter.md                    <- Unit 2
|-- commands/
|   |-- gol_generate.md               <- Unit 3
|   |-- gol_evaluate.md               <- Unit 3
|   +-- gol_report.md                 <- Unit 3
|-- skills/
|   +-- orchestration/
|       +-- SKILL.md                   <- Unit 2
+-- strategies/
    +-- strategies.py                  <- Unit 1
```

---

## Unit 1: GoL Strategies

Unit 1 contains the pure computational core: three Game of Life step functions implementing distinct algorithms, plus a benchmarking wrapper. This unit has no dependency on plugin infrastructure -- it is standalone Python that can be imported, tested, and benchmarked independently.

The three step functions share a common contract: given a grid state, produce the next generation according to Conway's B3/S23 rules. They differ in representation and algorithmic approach:

- `naive_step` operates on a 2D list-of-lists grid, scanning every cell each generation. It is O(N^2) in grid dimension and serves as the reference implementation for correctness.
- `hashlife_step` uses a recursive memoized quadtree. The grid is represented as a tree of `QuadNode` objects, each caching the result of advancing its region. Identical sub-patterns share nodes through a hash-consing memo table. For repetitive patterns this achieves sub-linear amortized time; for random configurations the overhead dominates.
- `sparse_step` tracks only alive cells as a `set` of `(row, col)` tuples. Each generation it collects candidates (alive cells and their neighbors), evaluates rules for each, and produces the new alive set. Cost is proportional to alive cell count, not grid area.

The `benchmark` function wraps any step function: it constructs a deterministic R-pentomino initial configuration, converts it to the strategy's native representation, runs the specified number of generations, and returns a result dict with timing and alive-count data. It uses `time.perf_counter` for wall-clock measurement.

A `grid_to_sparse` conversion function translates between the grid representation (used by naive and hashlife) and the sparse representation (used by sparse_step), enabling correctness cross-checking.

### Preferences

- All functions are module-level (no classes except `QuadNode`).
- `QuadNode` is a lightweight data class (or named tuple) with fields: `nw`, `ne`, `sw`, `se`, `level`, `population`, `result` (cached).
- The memo table for hashlife is a module-level dict, clearable via `clear_memo()`.
- No external dependencies. Standard library only (`time`, `typing`, `collections`).

---

## Unit 2: Plugin Infrastructure

Unit 2 defines the plugin's structural identity and agent/skill definitions as string constants. These are not executable code -- they are the markdown and JSON content that will be written to files during assembly.

The `PLUGIN_MANIFEST` constant holds the complete JSON content for `plugin.json`, declaring the plugin's name, description, version, and references to its commands, agents, and skills.

The three agent definition constants (`GENERATE_AGENT_DEF`, `EVALUATE_AGENT_DEF`, `REPORT_AGENT_DEF`) each contain a complete Claude Code agent definition markdown file. These define the agent's name, description, model requirements, allowed tools, and behavioral instructions.

The `ORCHESTRATION_SKILL_DEF` constant contains the complete skill markdown file for the generate-evaluate-report workflow. The skill's frontmatter specifies its name, description, allowed tools, and invocation pattern. The body describes the three-phase workflow: generate all strategies, evaluate each, produce comparison report.

### Preferences

- String constants use triple-quoted Python strings with proper markdown formatting inside.
- The manifest JSON is stored as a Python dict constant (`PLUGIN_MANIFEST`) that is serialized to JSON during assembly.
- Agent definitions follow Claude Code agent markdown schema: frontmatter with `name`, `description`, `model`, `allowed-tools`, followed by behavioral instructions in the body.
- The skill definition follows Claude Code skill markdown schema: frontmatter with `name`, `description`, `argument-hint`, `allowed-tools`, followed by workflow instructions.

---

## Unit 3: Command Definitions

Unit 3 defines the three slash command markdown files as string constants. Each constant holds a complete Claude Code command definition that specifies the command's name, description, argument schema, and execution instructions.

Commands are the user-facing entry points. Each command definition instructs Claude Code to invoke the corresponding agent from Unit 2 with the appropriate arguments.

The three commands are:
- `GENERATE_CMD_DEF` for `/gol:generate` -- accepts a `--strategy` argument and invokes the generator agent.
- `EVALUATE_CMD_DEF` for `/gol:evaluate` -- accepts a `--file` argument (and optional benchmark parameters) and invokes the evaluator agent.
- `REPORT_CMD_DEF` for `/gol:report` -- takes no required arguments and invokes the reporter agent.

### Preferences

- Command definitions follow Claude Code command markdown schema.
- Each command definition includes a usage example.
- Argument validation instructions are embedded in the command markdown (the agent enforces them, not a schema validator).

---

## Unit 4: Assembly

Unit 4 owns the `assemble_plugin` function that constructs the complete plugin directory from the constants and source code defined in Units 1-3. It is the only unit that performs filesystem operations.

The assembly function creates the directory tree specified in the Preamble, writes each file from its corresponding constant, and validates the result. It handles directory creation, file writing, and post-assembly verification in a single deterministic pass.

The validation step confirms structural integrity: `plugin.json` parses as valid JSON with required fields, all referenced files exist, and `strategies.py` compiles without syntax errors.

### Preferences

- Uses `pathlib.Path` throughout.
- Creates directories with `mkdir(parents=True, exist_ok=True)`.
- Writes files atomically where possible (write to temp, rename).
- Raises `AssemblyError` (a custom exception defined in this unit) on validation failure.
- Returns the `Path` to the assembled plugin root directory.

---

## Dependency Graph

```
Unit 1 (strategies.py)     -- no dependencies
Unit 2 (plugin infra)      -- no dependencies (string constants)
Unit 3 (command defs)       -- no dependencies (string constants)
Unit 4 (assembly.py)        -- depends on Unit 1, Unit 2, Unit 3
```

Unit 4 imports constants from Units 2 and 3, and copies the source file from Unit 1. Units 1, 2, and 3 are mutually independent.
