# Blueprint Prose (Tier 1) -- gol-python-r

**Project:** Conway's Game of Life (Python/R Mixed)
**Archetype:** D (mixed, Python primary / R secondary)
**Blueprint version:** 1.0
**Date:** 2026-03-29
**Units:** 4

---

## File Tree

```
gol-python-r/
  R/
    engine.R           # Unit 1 -- R Engine
  bridge.py            # Unit 2 -- Python Bridge
  display.py           # Unit 3 -- Python Display
  main.py              # Unit 4 -- Python Main
  environment.yml      # Conda environment definition
  tests/
    test_engine.R      # Unit 1 tests (testthat)
    test_bridge.py     # Unit 2 tests (pytest, requires rpy2 + R)
    test_display.py    # Unit 3 tests (smoke tests only, GUI excluded from coverage)
    test_main.py       # Unit 4 tests
```

---

## Unit 1: R Engine (`R/engine.R`)

### Purpose

The R engine is the sole authority for all Game of Life computation. It
implements grid creation, neighbor counting with toroidal wrapping, generation
stepping under the B3/S23 rule set, and preset pattern management. Every
function is a pure R function operating on logical matrices. Python never
computes GoL logic directly; all simulation work is delegated to this unit
through the bridge (Unit 2). The engine is testable standalone in a pure R
session with no Python or rpy2 dependency.

### Responsibilities

- **Grid creation.** `create_grid` produces a logical matrix of the requested
  dimensions with all cells set to FALSE (dead). Default size is 30x30. Both
  dimensions must be integers >= 3. The matrix uses R's standard 1-based
  indexing with row 1 at the top and column 1 at the left.

- **Neighbor counting.** `count_neighbors` accepts a logical matrix and returns
  an integer matrix of the same dimensions. Each element contains the count of
  alive (TRUE) neighbors in the Moore neighborhood (8 surrounding cells).
  Boundary conditions are toroidal: the top row's upward neighbors are the
  bottom row, the leftmost column's left neighbors are the rightmost column.
  The implementation converts the logical grid to integer (0/1), then sums
  eight shifted copies using modular arithmetic on row and column indices. A
  cell's own value is never included in its neighbor count.

- **Step function.** `step_grid` accepts a logical matrix and returns a new
  logical matrix representing the next generation. It calls `count_neighbors`
  internally, then applies B3/S23 rules element-wise: a cell becomes TRUE if
  it has exactly 3 neighbors (birth) or if it is already TRUE and has exactly
  2 neighbors (survival). All other cells become FALSE. The input grid is never
  modified. All transitions are computed simultaneously from the old state.

- **Pattern catalogue.** `get_patterns` returns a named list of six preset
  patterns. Each element is a two-column integer matrix of (row_offset,
  col_offset) pairs in 1-based indexing relative to the pattern's top-left
  corner. The six patterns are: Blinker (1x3, 3 cells), Block (2x2, 4 cells),
  Beacon (4x4, 6 cells), Glider (3x3, 5 cells), Pulsar (13x13, 48 cells),
  and Gosper Glider Gun (9x36, 36 cells). Pattern names in the list use
  lowercase.

- **Pattern placement.** `place_pattern` accepts a logical matrix and a pattern
  name string. It clears the grid (all FALSE), computes centering offsets using
  `floor((nrow - height) / 2) + 1` and `floor((ncol - width) / 2) + 1`, adds
  these offsets to the pattern's relative coordinates, and sets the
  corresponding cells to TRUE. If the pattern bounding box exceeds either grid
  dimension, a `warning()` is issued and cells are placed using modular
  indexing for toroidal wrapping. Returns the new grid; the input is not
  modified.

### Design Rationale

Keeping the engine as pure R functions with no side effects (except the
optional warning on oversized patterns) makes it fully testable with testthat
without mocking. Using logical matrices as the canonical data type aligns with
R's vectorized operations and makes the B3/S23 rule application a single
element-wise expression. The toroidal wrapping uses modular arithmetic on index
vectors, avoiding explicit boundary branching.

### Dependencies

None. This unit depends only on base R.

### Key Constraints

- All functions must be pure: no assignment to the input, no global state, no
  I/O (except `warning()` in `place_pattern`).
- The grid is always a logical matrix. Functions must validate this where
  appropriate and call `stop()` on type violations.
- 1-based indexing throughout (R convention).
- Minimum grid dimensions: 3x3.
- Only base R is used; no external R packages at runtime.

---

## Unit 2: Python Bridge (`bridge.py`)

### Purpose

The bridge is the sole point of contact between Python and R. It loads the R
engine source file into an embedded R session via rpy2, exposes Python-callable
wrappers for every R engine function, and handles all data conversion between
Python lists and R matrices. No other module imports rpy2; the display and main
units interact only with the bridge's Python API.

### Responsibilities

- **R engine initialization.** `init_r_engine` receives the path to
  `R/engine.R` and sources it into the embedded R session using
  `rpy2.robjects.r.source()`. After sourcing, the R functions (`create_grid`,
  `count_neighbors`, `step_grid`, `get_patterns`, `place_pattern`) are
  available in the R global environment. If the R source file cannot be loaded,
  a `RuntimeError` is raised with a descriptive message. If rpy2 or R is
  unavailable, an `ImportError` is raised at import time.

- **Grid creation wrapper.** `r_create_grid` calls the R `create_grid`
  function with the given rows and cols, then converts the returned R logical
  matrix to a Python list of lists of booleans (row-major order). The
  dimensions of the Python structure match the R matrix exactly: `rows`
  sublists of length `cols`.

- **Step wrapper.** `r_step_grid` converts a Python grid (list of lists of
  bools) to an R logical matrix, calls R `step_grid`, and converts the result
  back to a Python list of lists. The conversion preserves dimensions and cell
  states exactly. TRUE maps to True, FALSE maps to False, and the round-trip
  is lossless.

- **Pattern placement wrapper.** `r_place_pattern` calls R `create_grid` with
  the given rows and cols, then calls R `place_pattern` with the resulting grid
  and the pattern name. The final R grid is converted to a Python list of lists
  and returned.

- **Pattern names wrapper.** `r_get_patterns` calls R `get_patterns` and
  extracts the names from the returned named list, returning a Python list of
  pattern name strings.

### Design Rationale

Centralizing all rpy2 usage in a single module prevents R-specific import
errors from propagating through the codebase and provides a clean abstraction
boundary. Converting R matrices to Python lists on every call (rather than
caching R objects) satisfies the spec requirement that no R objects are cached
across steps (FR-4.3.1). Each round-trip is self-contained: Python data goes
in, Python data comes out.

### Dependencies

- **Unit 1 (R Engine):** `init_r_engine` sources `R/engine.R`. All wrapper
  functions call the R functions defined in Unit 1.

### Key Constraints

- Only `bridge.py` imports rpy2. All other modules use the bridge's Python API.
- Conversion must preserve dimensions exactly: (rows, cols) in R yields `rows`
  sublists of length `cols` in Python.
- Conversion must preserve cell states exactly: TRUE -> True, FALSE -> False,
  with lossless round-trips.
- Every step is a complete round-trip. No R objects are cached across calls.
- If the R engine file cannot be loaded, raise `RuntimeError`.
- If rpy2/R is unavailable, raise `ImportError`.

---

## Unit 3: Python Display (`display.py`)

### Purpose

Provides the graphical user interface using tkinter. The `GameDisplay` class
owns the canvas, all control widgets, and the simulation run-loop. It delegates
all simulation logic to the bridge (Unit 2), which in turn delegates to the R
engine. The display never calls R functions directly and has no rpy2 dependency.

### Responsibilities

- **Construction.** `__init__` receives the tkinter root window and a bridge
  module reference. It creates the canvas sized to the grid dimensions (each
  cell is 12x12 pixels including grid lines), lays out the control panel
  (Start, Stop, Step, Reset buttons, speed slider with label, generation
  counter label, and pattern dropdown), and binds mouse click events on the
  canvas. The initial grid is obtained from `bridge.r_create_grid()` and
  stored as a Python list of lists.

- **Rendering.** `draw_grid` iterates over the grid and draws each cell as a
  filled rectangle -- black (#000000) for alive, white (#FFFFFF) for dead --
  with gray (#CCCCCC) grid lines. It also updates the generation counter label.

- **Cell interaction.** `on_cell_click` translates pixel coordinates from the
  mouse click into grid (row, col), toggles the cell in the local Python grid,
  and redraws immediately. Cell toggling modifies the Python grid directly; the
  modified grid is passed to R on the next step call.

- **Simulation controls.** `start` begins the auto-advance loop by scheduling
  `tick` via `root.after()`. It disables the Start button and enables the Stop
  button. `stop` cancels the scheduled callback and swaps button states.
  `step_once` calls `bridge.r_step_grid(grid)`, updates the local grid, and
  redraws without scheduling further ticks. `reset` stops the simulation,
  obtains a fresh empty grid from `bridge.r_create_grid()`, and redraws.

- **Speed control.** `update_speed` is the slider callback. It stores the new
  speed (steps per second) so the next `tick` uses the updated interval. The
  speed label text is updated immediately.

- **Pattern loading.** `load_pattern` stops the simulation, calls
  `bridge.r_place_pattern(rows, cols, name)`, stores the returned grid, resets
  the generation counter, and redraws.

- **Tick loop.** `tick` calls `bridge.r_step_grid(grid)`, stores the new grid,
  increments the generation counter, redraws, and schedules itself again after
  an interval derived from the current speed setting (`1000 / speed`
  milliseconds).

### Design Rationale

The display owns the generation counter as local state because the R engine is
stateless (pure functions on matrices). The counter increments in Python on
each step call and resets on reset or pattern load. The grid is stored in
Python as a list of lists to allow direct cell toggling without R round-trips.

### Dependencies

- **Unit 2 (Bridge):** All simulation calls go through the bridge:
  `r_create_grid`, `r_step_grid`, `r_place_pattern`, `r_get_patterns`.

### Key Constraints

- The display never imports rpy2 or calls R functions directly.
- The grid is stored as a Python list of lists of booleans.
- The generation counter is maintained in Python, not in R.
- Cell toggling is a Python-only operation on the local grid.
- All control actions (Start/Stop/Step/Reset/pattern load) go through bridge
  functions for any operation that requires R computation.

---

## Unit 4: Python Main (`main.py`)

### Purpose

Entry point. Parses command-line arguments, validates them, initializes the
bridge to load the R engine, constructs the display, optionally loads a startup
pattern, and enters the tkinter main loop.

### Responsibilities

- **Argument parsing.** `parse_args` uses `argparse` to define `--width`,
  `--height`, `--speed`, and `--pattern` with defaults from the spec (50, 50,
  10, None). Returns the parsed namespace.

- **Validation.** `validate_args` enforces constraints: width and height must
  each be >= 3; speed must be in 1..60; if pattern is given, it must be a
  recognized name (checked via `bridge.r_get_patterns()`). On any violation,
  the function prints a descriptive error to stderr and calls `sys.exit(1)`.
  For invalid pattern names, the error message lists the valid pattern names.

- **Main function.** `main` calls `parse_args` and `validate_args`, calls
  `bridge.init_r_engine()` with the path to `R/engine.R` (resolved relative to
  the script's own location), creates the tkinter root with title "Conway's
  Game of Life" and `resizable(False, False)`, creates a `GameDisplay` with the
  bridge and grid dimensions, optionally calls `load_pattern` if `--pattern`
  was given, sets the initial speed from `--speed`, and enters
  `root.mainloop()`.

### Design Rationale

The main function resolves the R engine path relative to its own file location
so the application works regardless of the working directory. Validation
happens before any GUI construction so errors exit cleanly on the command line.
The bridge is initialized before the display so R engine failures are caught
before the window appears.

### Dependencies

- **Unit 2 (Bridge):** `init_r_engine`, `r_get_patterns` (for validation).
- **Unit 3 (Display):** `GameDisplay`.

### Key Constraints

- The R engine must be initialized before any bridge calls.
- The R engine path is resolved relative to `main.py`'s location.
- Invalid arguments produce an error message to stderr and exit code 1.
- The window is non-resizable.
- `main.py` imports only the bridge and display modules, not rpy2 or R code.

---

## Dependency Graph

```
Unit 4 (Main)
  |
  +---> Unit 2 (Bridge)
  |       |
  |       +---> Unit 1 (R Engine)
  |
  +---> Unit 3 (Display)
          |
          +---> Unit 2 (Bridge)
                  |
                  +---> Unit 1 (R Engine)
```

Build order (leaves first): Unit 1 -> Unit 2 -> Unit 3 -> Unit 4.

---

*End of blueprint prose.*
