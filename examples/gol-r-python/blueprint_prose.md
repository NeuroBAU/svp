# Blueprint Prose (Tier 1) -- gol-r-python

**Project:** Conway's Game of Life (R/Python Mixed)
**Archetype:** D (mixed, R primary / Python secondary)
**Blueprint version:** 1.0
**Date:** 2026-03-29
**Units:** 4

---

## File Tree

```
gol-r-python/
  engine.py              # Unit 1 -- Python Engine
  R/
    bridge.R             # Unit 2 -- R Bridge (reticulate)
    display.R            # Unit 3 -- R Display (Shiny)
    main.R               # Unit 4 -- R Main
  inst/
    run_gol.R            # Unit 4 -- Rscript entry point
  environment.yml        # Conda environment definition
  tests/
    test_engine.py       # Unit 1 tests (pytest)
    test_bridge.R        # Unit 2 tests (testthat, requires reticulate + Python)
    test_display.R       # Unit 3 tests (smoke tests only, GUI excluded from coverage)
    test_main.R          # Unit 4 tests
```

---

## Unit 1: Python Engine (`engine.py`)

### Purpose

The Python engine is the sole authority for all Game of Life computation.
It implements grid creation, neighbor counting with toroidal wrapping,
generation stepping under the B3/S23 rule set, and preset pattern
management. Every function is a pure Python function operating on lists of
lists of booleans. R never computes GoL logic directly; all simulation work
is delegated to this unit through the bridge (Unit 2). The engine is
testable standalone in a pure Python session with no R or reticulate
dependency.

### Responsibilities

- **Grid creation.** `create_grid` produces a list of lists of booleans of
  the requested dimensions with all cells set to False (dead). Default size
  is 50x50. Both dimensions must be integers >= 3. The grid uses 0-based
  indexing with row 0 at the top and column 0 at the left.

- **Neighbor counting.** `count_neighbors` accepts a list of lists of
  booleans and returns a list of lists of integers of the same dimensions.
  Each element contains the count of alive (True) neighbors in the Moore
  neighborhood (8 surrounding cells). Boundary conditions are toroidal: the
  top row's upward neighbors are the bottom row, the leftmost column's left
  neighbors are the rightmost column. The implementation iterates over the
  8 directional offsets and uses modular arithmetic on row and column
  indices. A cell's own value is never included in its neighbor count.

- **Step function.** `step_grid` accepts a list of lists of booleans and
  returns a new list of lists representing the next generation. It calls
  `count_neighbors` internally, then applies B3/S23 rules element-wise: a
  cell becomes True if it has exactly 3 neighbors (birth) or if it is
  already True and has exactly 2 neighbors (survival). All other cells
  become False. The input grid is never modified. All transitions are
  computed simultaneously from the old state.

- **Pattern catalogue.** `get_patterns` returns a dict of six preset
  patterns. Each value is a list of (row, col) tuples using 0-based
  indexing relative to the pattern's top-left corner. The six patterns are:
  blinker (1x3, 3 cells), block (2x2, 4 cells), beacon (4x4, 6 cells),
  glider (3x3, 5 cells), pulsar (13x13, 48 cells), and gosper_glider_gun
  (9x36, 36 cells). Pattern keys are lowercase strings.

- **Pattern placement.** `place_pattern` accepts rows, cols, and a pattern
  name string. It creates a new grid (all False), computes centering
  offsets using `(rows - height) // 2` and `(cols - width) // 2`, adds
  these offsets to the pattern's relative coordinates, and sets the
  corresponding cells to True. If the pattern bounding box exceeds either
  grid dimension, cells are placed using modular indexing for toroidal
  wrapping. Returns the new grid.

### Design Rationale

Keeping the engine as pure Python functions with no side effects makes it
fully testable with pytest without mocking. Using lists of lists of
booleans as the canonical data type is the simplest representation that
maps cleanly to R logical matrices via reticulate. The toroidal wrapping
uses modular arithmetic on indices, avoiding explicit boundary branching.

### Dependencies

None. This unit depends only on the Python standard library.

### Key Constraints

- All functions must be pure: no mutation of the input, no global state,
  no I/O.
- The grid is always a list of lists of booleans. Functions must validate
  this where appropriate and raise appropriate exceptions on type violations.
- 0-based indexing throughout (Python convention).
- Minimum grid dimensions: 3x3.
- Only the Python standard library is used; no external packages at runtime.

---

## Unit 2: R Bridge (`R/bridge.R`)

### Purpose

The bridge is the sole point of contact between R and Python. It loads
the Python engine source file into the reticulate Python session, exposes
R-callable wrapper functions for every Python engine function, and handles
all data conversion between R matrices and Python lists. No other R module
imports reticulate; the display and main units interact only with the
bridge's R API.

### Responsibilities

- **Python engine initialization.** `bridge_init` receives the path to
  `engine.py` and sources it into the reticulate Python session using
  `reticulate::source_python()`. After sourcing, the Python functions
  (`create_grid`, `count_neighbors`, `step_grid`, `get_patterns`,
  `place_pattern`) are available via reticulate. If the Python source file
  cannot be loaded, `stop()` is called with a descriptive message. If
  reticulate or Python is unavailable, `stop()` is called.

- **Grid creation wrapper.** `bridge_create_grid` calls the Python
  `create_grid` function with the given rows and cols, then converts the
  returned Python list of lists to an R logical matrix. The conversion
  maps Python True to R TRUE and Python False to R FALSE. The dimensions
  of the R matrix match the Python grid exactly: `nrow == rows` and
  `ncol == cols`.

- **Step wrapper.** `bridge_step_grid` converts an R logical matrix to a
  Python list of lists of bools, calls Python `step_grid`, and converts
  the result back to an R logical matrix. The conversion preserves
  dimensions and cell states exactly. TRUE maps to True, FALSE maps to
  False, and the round-trip is lossless.

- **Pattern placement wrapper.** `bridge_place_pattern` calls Python
  `place_pattern` with the given rows, cols, and pattern name. The
  returned Python grid is converted to an R logical matrix and returned.

- **Pattern names wrapper.** `bridge_get_pattern_names` calls Python
  `get_patterns` and extracts the dict keys, returning an R character
  vector of pattern name strings.

### Design Rationale

Centralizing all reticulate usage in a single R module prevents
Python-specific import errors from propagating through the codebase and
provides a clean abstraction boundary. Converting Python lists to R
matrices on every call (rather than caching Python objects) satisfies the
spec requirement that no Python objects are cached across steps (FR-4.3.1).
Each round-trip is self-contained: R data goes in, R data comes out.

The bridge handles the 0-based (Python) to 1-based (R) index mapping
transparently through the matrix conversion. No other module needs to be
aware of the index mapping.

### Dependencies

- **Unit 1 (Python Engine):** `bridge_init` sources `engine.py`. All
  wrapper functions call the Python functions defined in Unit 1.

### Key Constraints

- Only `R/bridge.R` imports reticulate. All other R modules use the
  bridge's R API.
- Conversion must preserve dimensions exactly: Python grid with `rows`
  sublists of length `cols` yields an R matrix with `nrow == rows` and
  `ncol == cols`.
- Conversion must preserve cell states exactly: Python True -> R TRUE,
  Python False -> R FALSE, with lossless round-trips.
- Every step is a complete round-trip. No Python objects are cached across
  calls.
- If the Python engine file cannot be loaded, call `stop()`.
- If reticulate/Python is unavailable, call `stop()`.

---

## Unit 3: R Display (`R/display.R`)

### Purpose

Provides the graphical user interface using Shiny. The display module
defines both the UI layout (`gol_ui`) and the server logic (`gol_server`).
The server owns the reactive grid state, all control logic, and the
simulation tick loop. It delegates all simulation computation to the bridge
(Unit 2), which in turn delegates to the Python engine. The display never
calls Python functions directly and has no reticulate dependency.

### Responsibilities

- **UI definition.** `gol_ui` returns a Shiny `fluidPage` containing:
  a `titlePanel` with "Conway's Game of Life", a `plotOutput` for the grid
  display (with click handler), and a control panel with `actionButton`
  widgets for Start, Stop, Step, and Reset, a `sliderInput` for speed
  (range 1-60, default 10), a `textOutput` for the generation counter, and
  a `selectInput` for pattern selection. The UI accepts `rows` and `cols`
  parameters to size the plot output appropriately.

- **Server logic.** `gol_server` is a function accepting `input`, `output`,
  `session`, and a `bridge` parameter (the bridge module). It creates
  reactive values for the grid (logical matrix), generation counter
  (integer), and running state (logical). The initial grid is obtained from
  `bridge_create_grid()`.

- **Rendering.** An `output$grid_plot` render function uses base R
  `image()` to display the current grid state. Alive cells are black
  (#000000), dead cells are white (#FFFFFF). The plot is re-rendered
  whenever the reactive grid value changes.

- **Cell interaction.** An `observeEvent` on the plot click translates
  pixel coordinates into grid (row, col), toggles the cell in the reactive
  grid matrix, triggering a re-render. Cell toggling modifies the R matrix
  directly; the modified grid is passed to Python on the next step call.

- **Simulation controls.** Start begins the auto-advance loop using
  `invalidateLater()` in a reactive observer. Stop sets the running flag
  to FALSE. Step calls `bridge_step_grid(grid)`, updates the reactive
  grid, and increments the generation counter. Reset stops the simulation,
  obtains a fresh empty grid from `bridge_create_grid()`, resets the
  generation counter to 0.

- **Speed control.** The speed slider's value is read directly from
  `input$speed` in the tick observer. The `invalidateLater()` interval is
  computed as `1000 / input$speed` milliseconds.

- **Pattern loading.** When the pattern dropdown value changes, the server
  stops the simulation, calls `bridge_place_pattern(rows, cols, name)`,
  stores the returned grid in the reactive value, resets the generation
  counter, and triggers a re-render.

- **Tick loop.** A reactive observer checks `running()`. When TRUE, it
  calls `bridge_step_grid(grid())`, updates the reactive grid, increments
  the generation counter, and calls `invalidateLater(1000 / speed)` to
  schedule the next tick.

### Design Rationale

The display owns the generation counter as local reactive state because
the Python engine is stateless (pure functions on lists). The counter
increments in R on each step call and resets on reset or pattern load. The
grid is stored in R as a logical matrix in a `reactiveVal` to allow direct
cell toggling without Python round-trips and to leverage Shiny's reactive
invalidation for automatic re-rendering.

Using `image()` from base R for grid rendering avoids ggplot2 overhead and
keeps the dependency set minimal. The Shiny `invalidateLater()` mechanism
provides the tick loop without needing external timer packages.

### Dependencies

- **Unit 2 (Bridge):** All simulation calls go through the bridge:
  `bridge_create_grid`, `bridge_step_grid`, `bridge_place_pattern`,
  `bridge_get_pattern_names`.

### Key Constraints

- The display never imports reticulate or calls Python functions directly.
- The grid is stored as an R logical matrix in a `reactiveVal`.
- The generation counter is maintained in R, not in Python.
- Cell toggling is an R-only operation on the reactive grid matrix.
- All control actions (Start/Stop/Step/Reset/pattern load) go through
  bridge functions for any operation that requires Python computation.
- This is a plain Shiny app -- no golem, no rhino.

---

## Unit 4: R Main (`R/main.R` + `inst/run_gol.R`)

### Purpose

Entry point. Parses command-line arguments, validates them, initializes
the bridge to load the Python engine, constructs the Shiny app from the
display module's UI and server functions, optionally loads a startup
pattern, and launches the app via `shiny::runApp()`.

### Responsibilities

- **Argument parsing.** `parse_cli_args` accepts a character vector (from
  `commandArgs(trailingOnly = TRUE)`) and extracts `--width`, `--height`,
  `--speed`, and `--pattern` arguments. Returns a list with elements
  `width` (integer or NULL), `height` (integer or NULL), `speed` (integer
  or NULL), and `pattern` (character or NULL). NULL indicates the argument
  was not provided.

- **Validation.** `validate_cli_args` accepts the output of
  `parse_cli_args` and applies defaults and validation. Defaults: width =
  50L, height = 50L, speed = 10L, pattern = NULL. Validation rules: width
  and height must be integers >= 3; speed must be in 1..60; if pattern is
  given, it must be a recognized name (checked via
  `bridge_get_pattern_names()`). On any violation, `stop()` is called with
  a descriptive error message. For invalid pattern names, the error message
  lists the valid pattern names.

- **Main function.** `main` accepts an optional args parameter. It calls
  `parse_cli_args` and `validate_cli_args`, calls `bridge_init()` with the
  path to `engine.py` (resolved relative to the script's own location),
  constructs the Shiny app by passing `gol_ui` and `gol_server` (with the
  bridge and validated parameters) to `shiny::shinyApp()`, and launches it
  with `shiny::runApp()`.

- **Standalone script.** `inst/run_gol.R` sources the R files (bridge.R,
  display.R, main.R), calls `main()`, and handles `stop()` errors by
  printing the error message to stderr and calling `quit(status = 1)`.

### Design Rationale

The main function resolves the Python engine path relative to its own
file location so the application works regardless of the working directory.
Validation happens before any Shiny app construction so errors exit cleanly
on the command line. The bridge is initialized before the app is constructed
so Python engine failures are caught before the Shiny server starts.

### Dependencies

- **Unit 2 (Bridge):** `bridge_init`, `bridge_get_pattern_names` (for
  validation).
- **Unit 3 (Display):** `gol_ui`, `gol_server`.

### Key Constraints

- The Python engine must be initialized before any bridge calls.
- The Python engine path is resolved relative to the script's location.
- Invalid arguments produce an error message to stderr and exit with
  status 1.
- `R/main.R` sources only the bridge and display modules, not reticulate
  or Python code.
- The app is launched via `shiny::runApp()`, not via golem or rhino.

---

## Dependency Graph

```
Unit 4 (Main)
  |
  +---> Unit 2 (Bridge)
  |       |
  |       +---> Unit 1 (Python Engine)
  |
  +---> Unit 3 (Display)
          |
          +---> Unit 2 (Bridge)
                  |
                  +---> Unit 1 (Python Engine)
```

Build order (leaves first): Unit 1 -> Unit 2 -> Unit 3 -> Unit 4.

---

*End of blueprint prose.*
