# Blueprint Prose (Tier 1) -- GoL R

**Project:** gol-r
**Archetype:** B (r_project)
**Blueprint version:** 1.0
**Units:** 4

---

## Unit 1: GoL Engine (`R/engine.R`)

### Purpose

The engine unit contains all pure functions that implement Conway's Game of
Life simulation logic. It owns the grid data structure (a logical matrix),
neighbor counting with toroidal wrapping, and the B3/S23 rule application.
Every function in this unit is a pure function: it accepts inputs, returns a
new value, and never modifies its arguments or any global state.

### Responsibilities

- **Grid creation.** `create_grid` produces an empty logical matrix of the
  requested dimensions, with all cells set to FALSE (dead). The matrix has
  `rows` rows and `cols` columns, matching R's standard matrix orientation
  where row 1 is the top and column 1 is the leftmost. Default size is
  30x30. Both dimensions must be integers >= 3.

- **Neighbor counting.** `count_neighbors` accepts a logical matrix and
  returns an integer matrix of the same dimensions. Each element contains
  the count of alive (TRUE) neighbors in the Moore neighborhood (8
  surrounding cells). Boundary conditions are toroidal: the top row's
  upward neighbors are in the bottom row, and the leftmost column's left
  neighbors are in the rightmost column. The implementation converts the
  logical grid to integer (0/1), then sums eight shifted copies of the
  grid using modular arithmetic on row and column indices. The original
  cell's value is not included in its own neighbor count.

- **Step function.** `step_grid` accepts a logical grid and returns a new
  logical grid representing the next generation. It calls `count_neighbors`
  internally, then applies B3/S23 rules element-wise: a cell becomes TRUE
  if it has exactly 3 neighbors (birth) or if it is already TRUE and has
  exactly 2 neighbors (survival). All other cells become FALSE. The input
  grid is never modified.

- **Cell toggling.** `toggle_cell` accepts a grid and a (row, col)
  coordinate pair (1-based), flips that single cell between TRUE and FALSE,
  and returns the modified grid. The original grid is not modified. If the
  coordinate is out of bounds, the function calls stop().

- **Grid clearing.** `clear_grid` accepts a grid and returns a new grid of
  the same dimensions with all cells set to FALSE. The original grid is not
  modified.

### Design Rationale

Keeping the engine as pure functions with no side effects makes it fully
testable without mocking I/O. The toroidal wrapping is implemented in
`count_neighbors` using modular arithmetic on index vectors, which avoids
explicit boundary case branching and is vectorizable in R.

### Dependencies

None. This unit depends only on base R.

### Key Constraints

- All functions must be pure: no assignment to the input, no global state,
  no I/O.
- The grid is always a logical matrix. Functions must validate this where
  appropriate and call stop() on type violations.
- 1-based indexing throughout (R convention).
- Minimum grid dimensions: 3x3.

---

## Unit 2: Pattern Library (`R/patterns.R`)

### Purpose

The pattern library defines five preset Game of Life patterns and provides
functions to retrieve and place them onto a grid. Patterns are stored as
two-column integer matrices of (row, col) offsets with 1-based indexing.
Placement centers a pattern on a grid and handles toroidal wrapping when
the grid is smaller than the pattern bounding box.

### Responsibilities

- **Pattern catalogue.** `get_patterns` returns a named list where each
  element is a two-column integer matrix. Column 1 contains row offsets and
  column 2 contains column offsets, both 1-based relative to the pattern's
  top-left corner. The five patterns are: blinker (1x3, 3 cells), block
  (2x2, 4 cells), beacon (4x4, 6 cells), glider (3x3, 5 cells), and
  pulsar (13x13, 48 cells).

- **Pattern name listing.** `get_pattern_names` returns a character vector
  of all available pattern names, sorted alphabetically. This is a
  convenience wrapper over `names(get_patterns())`.

- **Single pattern retrieval.** `get_pattern` accepts a pattern name
  (character scalar), matches it case-insensitively against available
  names, and returns the corresponding two-column matrix. If the name does
  not match any pattern, it calls stop() with an error message listing
  valid names.

- **Pattern placement.** `place_pattern` accepts a grid (logical matrix)
  and a pattern name (character scalar). It clears the grid (all FALSE),
  computes center offsets using floor((nrow - pattern_height) / 2) + 1 and
  floor((ncol - pattern_width) / 2) + 1, adds these offsets to the
  pattern's relative coordinates, wraps using modular arithmetic for
  toroidal placement, and sets the corresponding cells to TRUE. If the
  pattern bounding box exceeds either grid dimension, a warning() is issued
  before placement. Returns the new grid.

### Design Rationale

Patterns are defined as offset matrices rather than small logical grids
because offset matrices are sparse, composable, and trivially testable by
checking exact coordinate values. Centering arithmetic matches the spec's
formula exactly to ensure reproducible placement across all grid sizes.

### Dependencies

- **Unit 1 (Engine):** `place_pattern` calls `clear_grid` to reset the
  grid before placement.

### Key Constraints

- Pattern coordinates are 1-based integers.
- Pattern data is static and immutable; `get_patterns` always returns the
  same values.
- Toroidal wrapping on placement uses ((index - 1) %% dim) + 1 to convert
  any coordinate into a valid matrix index.
- The `place_pattern` function must not modify its input grid.

---

## Unit 3: Display (`R/display.R`)

### Purpose

The display unit handles all terminal I/O: rendering the grid as text,
parsing user commands, and running the interactive read-eval-print loop.
This is the only unit that performs side effects (cat, readline, Sys.sleep,
warning messages to the user).

### Responsibilities

- **Grid rendering.** `display_grid` accepts a logical matrix and an
  integer generation counter. It prints a blank line, then
  "Generation: N" (where N is the counter), then each grid row as a string
  of "#" (alive) and "." (dead) characters with no separating spaces,
  followed by the command prompt "> ". All output is via cat() with
  newlines. The function returns invisible(NULL).

- **Command parsing.** `parse_command` accepts a character scalar of raw
  user input. It trims leading/trailing whitespace, converts to lowercase,
  and splits on whitespace into a command word and optional arguments. It
  returns a list with two elements: `command` (character scalar, the first
  word) and `args` (character vector, remaining words; length-0 if none).
  Empty input (after trimming) returns list(command = "", args =
  character(0)).

- **Interactive loop.** `run_game` accepts rows (integer, default 30),
  cols (integer, default 30), pattern (character or NULL, default NULL),
  and delay (numeric, default 0.1). It creates the initial grid via
  `create_grid`, optionally loads a starting pattern via `place_pattern`,
  initializes the generation counter to 0, displays the grid, then enters
  a readline loop. Each iteration reads a line, parses it, dispatches to
  the appropriate handler:
  - **step [N]:** calls `step_grid` N times (default 1), increments
    counter by N, displays the grid once after all steps.
  - **run N:** loops N times, calling `step_grid` once per iteration,
    incrementing the counter, displaying the grid, and calling
    Sys.sleep(delay) between iterations.
  - **reset:** calls `clear_grid`, resets counter to 0, displays.
  - **load PATTERN:** calls `place_pattern`, resets counter to 0, displays.
  - **help:** prints command summary via cat().
  - **quit:** breaks the loop, returns the final grid via invisible().
  - **unknown:** prints "Unknown command. Type 'help' for available
    commands." via cat().
  - **invalid arguments:** prints a descriptive error via cat() without
    modifying the grid or counter.

### Design Rationale

Separating `parse_command` from the dispatch loop allows the parser to be
unit-tested without I/O. The interactive loop itself is excluded from
coverage requirements (per NFR-5.3.3) because it depends on readline,
which is inherently interactive.

### Dependencies

- **Unit 1 (Engine):** `create_grid`, `step_grid`, `clear_grid`.
- **Unit 2 (Patterns):** `place_pattern`, `get_pattern_names` (for help
  and error messages listing valid patterns).

### Key Constraints

- All terminal output is via cat(), never print().
- readline() is the input mechanism; it is only called inside run_game.
- The generation counter is local state within run_game, not global.
- The function must handle all error cases gracefully (invalid step count,
  unknown pattern, unknown command) without calling stop() -- errors are
  reported to the user via cat() and the loop continues.

---

## Unit 4: Main (`R/main.R` + `inst/run_gol.R`)

### Purpose

The main unit provides the command-line entry point and CLI argument
parsing. `R/main.R` defines the argument parsing and validation functions
exported by the package. `inst/run_gol.R` is a standalone Rscript-
executable script that calls these functions and launches the game.

### Responsibilities

- **CLI argument parsing.** `parse_cli_args` accepts a character vector
  (from commandArgs(trailingOnly = TRUE)) and extracts `--rows`, `--cols`,
  `--pattern`, and `--delay` arguments. It returns a list with elements
  `rows` (integer or NULL), `cols` (integer or NULL), `pattern` (character
  or NULL), and `delay` (numeric or NULL), where NULL indicates the
  argument was not provided. Unrecognized arguments are silently ignored.

- **CLI argument validation.** `validate_cli_args` accepts the output of
  `parse_cli_args` and applies defaults and validation. Default values:
  rows = 30L, cols = 30L, pattern = NULL, delay = 0.1. Validation rules:
  rows and cols must be integers >= 3; delay must be a positive number; if
  pattern is provided, it must be a recognized pattern name (checked via
  `get_pattern_names`). On any validation failure, the function calls
  stop() with a descriptive error message. On pattern validation failure,
  the error message includes the list of valid pattern names.

- **Entry point.** `main` accepts an optional args parameter (character
  vector, defaulting to commandArgs(trailingOnly = TRUE)). It calls
  `parse_cli_args`, then `validate_cli_args`, then `run_game` with the
  validated parameters.

- **Standalone script.** `inst/run_gol.R` loads the package (either via
  library(golr) or by sourcing the R files directly if not installed),
  calls `main()`, and handles stop() errors by printing the error message
  to stderr and calling quit(status = 1).

### Design Rationale

Separating parsing from validation makes both independently testable.
The `main` function accepts an args parameter so it can be tested without
manipulating commandArgs. The `inst/run_gol.R` script is a thin wrapper
that handles the top-level error-to-exit-code translation.

### Dependencies

- **Unit 1 (Engine):** indirectly via `run_game`.
- **Unit 2 (Patterns):** `get_pattern_names` for validation.
- **Unit 3 (Display):** `run_game`.

### Key Constraints

- `parse_cli_args` must handle the `--key value` format with space
  separation (standard R commandArgs style).
- `validate_cli_args` must call stop() on invalid input, not return error
  values. This enables the script wrapper to use tryCatch for clean exit
  code handling.
- `inst/run_gol.R` must exit with status 1 on any validation error and
  status 0 on normal quit.

---

## Dependency Graph

```
Unit 4 (Main)
  |
  +---> Unit 3 (Display)
  |       |
  |       +---> Unit 1 (Engine)
  |       +---> Unit 2 (Patterns)
  |                |
  |                +---> Unit 1 (Engine)
  +---> Unit 2 (Patterns)
```

Build order (leaves first): Unit 1 -> Unit 2 -> Unit 3 -> Unit 4.

---

*End of blueprint prose.*
