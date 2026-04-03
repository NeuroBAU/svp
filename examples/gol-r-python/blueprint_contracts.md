# Blueprint Contracts (Tier 2 + Tier 3) -- gol-r-python

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
    test_display.R       # Unit 3 tests (smoke tests only)
    test_main.R          # Unit 4 tests
```

---

## Unit 1: Python Engine (`engine.py`)

### Tier 2 -- Signatures

```python
def create_grid(rows: int = 50, cols: int = 50) -> list[list[bool]]: ...

def count_neighbors(grid: list[list[bool]]) -> list[list[int]]: ...

def step_grid(grid: list[list[bool]]) -> list[list[bool]]: ...

def get_patterns() -> dict[str, list[tuple[int, int]]]: ...

def place_pattern(rows: int, cols: int, pattern_name: str) -> list[list[bool]]: ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

**create_grid:**

Parameters:

| Name | Type | Default | Description                  |
|------|------|---------|------------------------------|
| rows | int  | 50      | Number of rows (>= 3)       |
| cols | int  | 50      | Number of columns (>= 3)    |

Returns: `list[list[bool]]` -- `rows` sublists each of length `cols`, all False.

- PRE-1: isinstance(rows, int) and rows >= 3
- PRE-2: isinstance(cols, int) and cols >= 3
- POST-1: len(result) == rows
- POST-2: all(len(row) == cols for row in result)
- POST-3: all(cell is False for row in result for cell in row)
- ERR-1: rows < 3 or cols < 3 -> ValueError("Grid dimensions must be at least 3x3")
- ERR-2: not isinstance(rows, int) or not isinstance(cols, int) -> TypeError("rows and cols must be integers")

Spec refs: FR-3.1.1, FR-3.1.6

**count_neighbors:**

Parameters:

| Name | Type              | Default | Description                |
|------|-------------------|---------|----------------------------|
| grid | list[list[bool]]  | (none)  | Current grid state         |

Returns: `list[list[int]]` of same dimensions as `grid`. Each element
contains the count (0--8) of True neighbors in the Moore neighborhood
with toroidal wrapping.

- PRE-1: grid is a rectangular list of lists of booleans
- PRE-2: len(grid) >= 3 and len(grid[0]) >= 3
- POST-1: len(result) == len(grid) and len(result[0]) == len(grid[0])
- POST-2: all(0 <= result[r][c] <= 8 for all valid r, c)
- POST-3: For an all-False grid, all(result[r][c] == 0 for all r, c)
- POST-4: For a grid with a single True cell at [r, c], the result has exactly 1 at each of the 8 toroidal neighbors of [r, c] and 0 elsewhere (including [r, c] itself).
- POST-5: The input grid is not modified (no side effects).
- ERR-1: grid is not a list of lists of bools -> TypeError("grid must be a list of lists of booleans")

Spec refs: FR-3.1.2

**step_grid:**

Parameters:

| Name | Type              | Default | Description                |
|------|-------------------|---------|----------------------------|
| grid | list[list[bool]]  | (none)  | Current generation grid    |

Returns: `list[list[bool]]` of same dimensions -- the next generation
after applying B3/S23 rules.

- PRE-1: grid is a rectangular list of lists of booleans
- PRE-2: len(grid) >= 3 and len(grid[0]) >= 3
- POST-1: len(result) == len(grid) and len(result[0]) == len(grid[0])
- POST-2: For every cell [r, c] with n = count_neighbors(grid)[r][c]: result[r][c] is True iff (n == 3) or (grid[r][c] and n == 2)
- POST-3: The input grid is not modified (no side effects).
- POST-4: An all-False grid returns an all-False grid.
- POST-5: A blinker oscillates: step_grid(step_grid(blinker_grid)) == blinker_grid.
- POST-6: A block is stable: step_grid(block_grid) == block_grid.
- POST-7: A glider translates: after 4 steps the glider pattern is offset by (1, 1) with toroidal wrapping.
- ERR-1: grid is not a list of lists of bools -> TypeError("grid must be a list of lists of booleans")

Spec refs: FR-3.1.3, AC-3.1.B, AC-3.1.C

**get_patterns:**

Parameters: None.

Returns: `dict[str, list[tuple[int, int]]]` with 6 entries. Each value
is a list of (row, col) tuples using 0-based indexing relative to the
pattern's top-left corner. Keys: "beacon", "blinker", "block", "glider",
"gosper_glider_gun", "pulsar" (alphabetical, lowercase).

- PRE: (none -- no arguments)
- POST-1: isinstance(result, dict) and len(result) == 6
- POST-2: sorted(result.keys()) == ["beacon", "blinker", "block", "glider", "gosper_glider_gun", "pulsar"]
- POST-3: For each key k, result[k] is a list of 2-tuples of non-negative ints.
- POST-4: result["blinker"] has 3 cells, bounding box 1x3.
- POST-5: result["block"] has 4 cells, bounding box 2x2.
- POST-6: result["beacon"] has 6 cells, bounding box 4x4.
- POST-7: result["glider"] has 5 cells, bounding box 3x3.
- POST-8: result["pulsar"] has 48 cells, bounding box 13x13.
- POST-9: result["gosper_glider_gun"] has 36 cells, bounding box 9x36.
- POST-10: Successive calls return identical results (immutable data).
- ERR: (none -- function cannot fail)

Spec refs: FR-3.1.4, FR-3.4.1, AC-3.1.D

**place_pattern:**

Parameters:

| Name         | Type | Default | Description                                  |
|--------------|------|---------|----------------------------------------------|
| rows         | int  | (none)  | Grid rows (>= 3)                            |
| cols         | int  | (none)  | Grid columns (>= 3)                         |
| pattern_name | str  | (none)  | Pattern name (case-insensitive)              |

Returns: `list[list[bool]]` -- grid with pattern centered.

- PRE-1: isinstance(rows, int) and rows >= 3
- PRE-2: isinstance(cols, int) and cols >= 3
- PRE-3: pattern_name.lower() in get_patterns()
- POST-1: len(result) == rows and len(result[0]) == cols
- POST-2: The grid was initialized to all False before pattern placement.
- POST-3: Pattern is centered: row_offset = (rows - height) // 2, col_offset = (cols - width) // 2, where height = max(r for r, c in pattern) + 1 and width = max(c for r, c in pattern) + 1.
- POST-4: Number of True cells == len(pattern_coords), unless toroidal wrapping causes overlapping offsets.
- POST-5: If height > rows or width > cols, cells placed using (index % dim) toroidal wrapping.
- ERR-1: Unknown pattern name -> ValueError with message containing "Unknown pattern" and listing valid names.
- ERR-2: rows < 3 or cols < 3 -> ValueError("Grid dimensions must be at least 3x3")

Spec refs: FR-3.1.5, AC-3.1.B

---

## Unit 2: R Bridge (`R/bridge.R`)

### Tier 2 -- Signatures

```r
bridge_init <- function(engine_path) { ... }

bridge_create_grid <- function(rows, cols) { ... }

bridge_step_grid <- function(grid) { ... }

bridge_place_pattern <- function(rows, cols, pattern_name) { ... }

bridge_get_pattern_names <- function() { ... }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** **Unit 1** (create_grid, count_neighbors, step_grid, get_patterns, place_pattern).

**bridge_init:**

Parameters:

| Name        | Type      | Default | Description                              |
|-------------|-----------|---------|------------------------------------------|
| engine_path | character | (none)  | Filesystem path to `engine.py`           |

Returns: invisible(NULL). Side effect: sources the Python file into the
reticulate session.

- PRE-1: is.character(engine_path) && length(engine_path) == 1L
- PRE-2: engine_path points to an existing file.
- POST-1: After return, the Python functions `create_grid`, `count_neighbors`, `step_grid`, `get_patterns`, and `place_pattern` are callable via reticulate.
- POST-2: Subsequent calls to `bridge_create_grid`, `bridge_step_grid`, `bridge_place_pattern`, and `bridge_get_pattern_names` will succeed.
- ERR-1: If the file at engine_path does not exist or cannot be sourced, stop() with a descriptive message including the path.
- ERR-2: If reticulate is not installed or Python is not available, stop() with a descriptive message.

Spec refs: FR-3.2.1, FR-3.2.8

**bridge_create_grid:**

Parameters:

| Name | Type    | Default | Description                  |
|------|---------|---------|------------------------------|
| rows | integer | (none)  | Number of rows (>= 3)       |
| cols | integer | (none)  | Number of columns (>= 3)    |

Returns: logical matrix of dimensions `rows x cols`, all FALSE.

- PRE-1: bridge_init has been called successfully.
- PRE-2: is.numeric(rows) && rows >= 3 && is.numeric(cols) && cols >= 3
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == as.integer(rows) && ncol(result) == as.integer(cols)
- POST-3: all(result == FALSE)
- POST-4: The result is an R matrix (not a Python object). No Python objects are retained.
- ERR-1: Python-side errors (e.g., invalid dimensions) propagate as R errors via reticulate.

Spec refs: FR-3.2.2, FR-3.2.6, FR-3.2.7, AC-3.2.A

**bridge_step_grid:**

Parameters:

| Name | Type           | Default | Description                          |
|------|----------------|---------|--------------------------------------|
| grid | logical matrix | (none)  | Current generation as R matrix       |

Returns: logical matrix -- next generation grid.

- PRE-1: bridge_init has been called successfully.
- PRE-2: is.matrix(grid) && is.logical(grid) && nrow(grid) >= 3 && ncol(grid) >= 3
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == nrow(grid) && ncol(result) == ncol(grid)
- POST-3: Cell states reflect one application of B3/S23 rules as computed by Python step_grid.
- POST-4: Conversion preserves cell states exactly: Python True -> R TRUE, Python False -> R FALSE.
- POST-5: Round-trip is lossless: converting an R matrix to Python and back yields the original values.
- POST-6: The input grid is not modified.
- POST-7: No Python objects are cached; the Python list is created, used, and discarded within the call.

Spec refs: FR-3.2.3, FR-3.2.6, FR-3.2.7, FR-4.3.1, AC-3.2.B, AC-3.2.C

**bridge_place_pattern:**

Parameters:

| Name         | Type      | Default | Description                              |
|--------------|-----------|---------|------------------------------------------|
| rows         | integer   | (none)  | Grid rows                                |
| cols         | integer   | (none)  | Grid columns                             |
| pattern_name | character | (none)  | Pattern name (case-insensitive)          |

Returns: logical matrix -- grid with pattern centered.

- PRE-1: bridge_init has been called successfully.
- PRE-2: is.numeric(rows) && rows >= 3 && is.numeric(cols) && cols >= 3
- PRE-3: pattern_name is a recognized pattern name (case-insensitive).
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == as.integer(rows) && ncol(result) == as.integer(cols)
- POST-3: The grid was cleared before pattern placement (all non-pattern cells are FALSE).
- POST-4: The pattern is centered using Python's centering formula.
- POST-5: Conversion preserves cell states exactly.
- ERR-1: Unknown pattern name causes a Python-side ValueError which propagates as an R error.

Spec refs: FR-3.2.4, AC-3.2.C

**bridge_get_pattern_names:**

Parameters: None.

Returns: character vector of pattern name strings.

- PRE-1: bridge_init has been called successfully.
- POST-1: is.character(result)
- POST-2: length(result) == 6L
- POST-3: Each element is a lowercase pattern name string.
- POST-4: The vector contains: "beacon", "blinker", "block", "glider", "gosper_glider_gun", "pulsar" (not necessarily in this order).

Spec refs: FR-3.2.5

---

## Unit 3: R Display (`R/display.R`)

### Tier 2 -- Signatures

```r
CELL_SIZE <- 12L     # pixels per cell for plot sizing
COLOR_ALIVE <- "#000000"
COLOR_DEAD <- "#FFFFFF"

gol_ui <- function(rows, cols, pattern_choices) { ... }

gol_server <- function(input, output, session, bridge, rows, cols,
                       initial_speed, initial_pattern) { ... }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** **Unit 2** (bridge_create_grid, bridge_step_grid, bridge_place_pattern, bridge_get_pattern_names).

**CELL_SIZE, COLOR_ALIVE, COLOR_DEAD:**

- INVARIANT-1: CELL_SIZE == 12L.
- INVARIANT-2: COLOR_ALIVE == "#000000", COLOR_DEAD == "#FFFFFF".

**gol_ui:**

Parameters:

| Name            | Type      | Default | Description                                 |
|-----------------|-----------|---------|---------------------------------------------|
| rows            | integer   | (none)  | Grid rows (for sizing plot output)          |
| cols            | integer   | (none)  | Grid columns (for sizing plot output)       |
| pattern_choices | character | (none)  | Character vector of pattern names           |

Returns: A Shiny `fluidPage` UI definition.

- PRE-1: is.numeric(rows) && rows >= 3
- PRE-2: is.numeric(cols) && cols >= 3
- PRE-3: is.character(pattern_choices) && length(pattern_choices) >= 1L
- POST-1: The returned UI contains a titlePanel with text "Conway's Game of Life".
- POST-2: The UI contains a plotOutput with id "grid_plot" and click handler enabled (click = "grid_click").
- POST-3: The plot output height is rows * CELL_SIZE pixels, width is cols * CELL_SIZE pixels (as character strings for Shiny).
- POST-4: The UI contains actionButtons with ids "start_btn", "stop_btn", "step_btn", "reset_btn".
- POST-5: The UI contains a sliderInput with id "speed", min = 1, max = 60, value = 10.
- POST-6: The UI contains a textOutput with id "generation_text".
- POST-7: The UI contains a selectInput with id "pattern_select" populated with pattern_choices.

Spec refs: FR-3.3.1, FR-3.3.3, FR-3.3.4, FR-3.3.5, FR-3.3.6, FR-3.3.7

**gol_server:**

Parameters:

| Name            | Type     | Default | Description                                      |
|-----------------|----------|---------|--------------------------------------------------|
| input           | list     | (none)  | Shiny input object                               |
| output          | list     | (none)  | Shiny output object                              |
| session         | Session  | (none)  | Shiny session object                             |
| bridge          | environment | (none) | Bridge module (exposes bridge_* functions)      |
| rows            | integer  | (none)  | Grid rows                                        |
| cols            | integer  | (none)  | Grid columns                                     |
| initial_speed   | integer  | 10L     | Starting speed (steps/sec)                       |
| initial_pattern | character or NULL | NULL | Pattern to load at startup             |

Returns: None (Shiny server function, runs reactively).

- PRE-1: bridge_init has been called; bridge exposes bridge_create_grid, bridge_step_grid, bridge_place_pattern.
- PRE-2: rows >= 3 && cols >= 3.

**Server reactive state initialization:**

- POST-1: A reactiveVal `grid_rv` is initialized via bridge_create_grid(rows, cols).
- POST-2: A reactiveVal `generation_rv` is initialized to 0L.
- POST-3: A reactiveVal `running_rv` is initialized to FALSE.
- POST-4: If initial_pattern is non-NULL, bridge_place_pattern(rows, cols, initial_pattern) is called and grid_rv is set to the result.

**Server output -- grid_plot (renderPlot):**

- POST-5: output$grid_plot renders the current grid_rv() as a base R image. Alive cells (TRUE) are displayed in COLOR_ALIVE, dead cells (FALSE) in COLOR_DEAD.
- POST-6: The plot axes are suppressed (no axis labels, ticks, or frame).
- POST-7: The plot re-renders whenever grid_rv() changes (reactive dependency).

**Server output -- generation_text (renderText):**

- POST-8: output$generation_text renders as "Generation: N" where N == generation_rv().

**Server observer -- grid_click (observeEvent on input$grid_click):**

- POST-9: Translates click coordinates (input$grid_click$x, input$grid_click$y) to grid (row, col) using floor() and accounting for image() coordinate mapping.
- POST-10: Toggles grid_rv()[row, col]: TRUE becomes FALSE, FALSE becomes TRUE.
- POST-11: generation_rv() is unchanged.

Spec refs: FR-3.3.2, FR-4.3.2

**Server observer -- start_btn (observeEvent on input$start_btn):**

- POST-12: running_rv() is set to TRUE.

Spec refs: FR-3.3.3

**Server observer -- stop_btn (observeEvent on input$stop_btn):**

- POST-13: running_rv() is set to FALSE.

Spec refs: FR-3.3.3

**Server observer -- step_btn (observeEvent on input$step_btn):**

- POST-14: grid_rv() is updated to bridge_step_grid(grid_rv()).
- POST-15: generation_rv() is incremented by exactly 1.
- POST-16: running_rv() is unchanged.

Spec refs: FR-3.3.3

**Server observer -- reset_btn (observeEvent on input$reset_btn):**

- POST-17: If running_rv() is TRUE, running_rv() is set to FALSE.
- POST-18: grid_rv() is replaced with bridge_create_grid(rows, cols) (all cells dead).
- POST-19: generation_rv() is set to 0L.

Spec refs: FR-3.3.3, FR-3.3.5

**Server observer -- pattern_select (observeEvent on input$pattern_select):**

- POST-20: If running_rv() is TRUE, running_rv() is set to FALSE.
- POST-21: grid_rv() is replaced with bridge_place_pattern(rows, cols, input$pattern_select).
- POST-22: generation_rv() is set to 0L.

Spec refs: FR-3.3.6

**Server observer -- tick loop (observe with running_rv() dependency):**

- POST-23: When running_rv() is TRUE: grid_rv() is updated to bridge_step_grid(grid_rv()), generation_rv() is incremented by 1, and invalidateLater(1000L %/% input$speed) is called.
- POST-24: When running_rv() is FALSE, the observer does nothing (no invalidateLater call).
- POST-25: The interval is derived from the current speed slider value: 1000 %/% input$speed milliseconds.

Spec refs: FR-3.3.3, FR-3.3.4, FR-3.3.5

---

## Unit 4: R Main (`R/main.R` + `inst/run_gol.R`)

### Tier 2 -- Signatures

```r
parse_cli_args <- function(args = commandArgs(trailingOnly = TRUE)) { ... }

validate_cli_args <- function(parsed, bridge) { ... }

main <- function(args = commandArgs(trailingOnly = TRUE)) { ... }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** **Unit 2** (bridge_init, bridge_get_pattern_names), **Unit 3** (gol_ui, gol_server).

**parse_cli_args:**

Parameters:

| Name | Type      | Default                          | Description           |
|------|-----------|----------------------------------|-----------------------|
| args | character | commandArgs(trailingOnly = TRUE)  | CLI argument vector   |

Returns: list with elements: `width` (integer or NULL), `height` (integer
or NULL), `speed` (integer or NULL), `pattern` (character or NULL). NULL
means the argument was not provided.

- PRE-1: is.character(args)
- POST-1: is.list(result)
- POST-2: names(result) contains "width", "height", "speed", "pattern"
- POST-3: parse_cli_args(c("--width", "80", "--height", "60")) -> list(width = 80L, height = 60L, speed = NULL, pattern = NULL)
- POST-4: parse_cli_args(c("--pattern", "glider")) -> list(width = NULL, height = NULL, speed = NULL, pattern = "glider")
- POST-5: parse_cli_args(c("--speed", "20")) -> list(width = NULL, height = NULL, speed = 20L, pattern = NULL)
- POST-6: parse_cli_args(character(0)) -> list(width = NULL, height = NULL, speed = NULL, pattern = NULL)
- POST-7: Unrecognized arguments (e.g., "--foo", "bar") are silently ignored.
- POST-8: "--width" expects the next element to be the value; if missing or not convertible to integer, result$width remains NULL.
- ERR: (none -- malformed args produce NULL values, validation is separate)

Spec refs: FR-6.2

**validate_cli_args:**

Parameters:

| Name   | Type        | Default | Description                                    |
|--------|-------------|---------|------------------------------------------------|
| parsed | list        | (none)  | Output of parse_cli_args                       |
| bridge | environment | (none)  | Bridge module (for pattern name validation)    |

Returns: list with elements: `width` (integer), `height` (integer),
`speed` (integer), `pattern` (character or NULL). All non-NULL values
are validated; NULLs replaced with defaults.

- PRE-1: is.list(parsed)
- PRE-2: names(parsed) contains "width", "height", "speed", "pattern"
- POST-1: result$width is integer, >= 3. Default: 50L.
- POST-2: result$height is integer, >= 3. Default: 50L.
- POST-3: result$speed is integer, >= 1 and <= 60. Default: 10L.
- POST-4: result$pattern is NULL or a valid pattern name (tolower(result$pattern) %in% bridge_get_pattern_names()).
- ERR-1: parsed$width is non-NULL and (not integer-like or < 3) -> stop("--width must be an integer >= 3")
- ERR-2: parsed$height is non-NULL and (not integer-like or < 3) -> stop("--height must be an integer >= 3")
- ERR-3: parsed$speed is non-NULL and (not integer-like or < 1 or > 60) -> stop("--speed must be an integer between 1 and 60")
- ERR-4: parsed$pattern is non-NULL and not in bridge_get_pattern_names() -> stop() with message containing "Unknown pattern" and listing valid pattern names (comma-separated)

Spec refs: FR-6.4, FR-6.5, FR-6.6, AC-6.C

**main:**

Parameters:

| Name | Type      | Default                          | Description           |
|------|-----------|----------------------------------|-----------------------|
| args | character | commandArgs(trailingOnly = TRUE)  | CLI argument vector   |

Returns: None (launches Shiny app, does not return normally).

- PRE-1: is.character(args)
- POST-1: Calls parse_cli_args(args).
- POST-2: Resolves engine.py path relative to the script's own location.
- POST-3: Calls bridge_init(engine_path).
- POST-4: Calls validate_cli_args(parsed, bridge) with the parsed args.
- POST-5: Constructs a Shiny app via shiny::shinyApp(ui = gol_ui(height, width, pattern_names), server = ...).
- POST-6: The server function wraps gol_server with the bridge, rows = height, cols = width, initial_speed = speed, initial_pattern = pattern.
- POST-7: Launches the app via shiny::runApp().
- ERR-1: Validation failures propagate stop() from validate_cli_args.
- ERR-2: Bridge initialization failures propagate stop() from bridge_init.

Spec refs: FR-6.1, FR-6.2, FR-6.3, AC-6.A, AC-6.B

**inst/run_gol.R (script, not a function):**

Standalone Rscript entry point. Not an exported function.

Pseudocode:

```r
# inst/run_gol.R
tryCatch(
  {
    source("R/bridge.R")
    source("R/display.R")
    source("R/main.R")
    main()
  },
  error = function(e) {
    message(conditionMessage(e))
    quit(status = 1, save = "no")
  }
)
```

- POST-1: On success (app runs and user closes it), exits with status 0.
- POST-2: On validation error (bad args), prints error message to stderr via message() and exits with status 1.
- POST-3: Error message for unknown pattern includes list of valid names.
- ERR: All errors caught by tryCatch; none propagate to the R session.

Spec refs: FR-6.1, FR-6.4, FR-6.5, FR-6.6

---

## Cross-Unit Contract Summary

### Dependency Contracts

| Consumer                | Provider                  | Contract                                                      |
|-------------------------|---------------------------|---------------------------------------------------------------|
| bridge_init             | engine.py (Unit 1)        | Sources file; all 5 Python functions available via reticulate  |
| bridge_create_grid      | create_grid (Unit 1)      | rows >= 3, cols >= 3 -> list of lists, converted to R matrix  |
| bridge_step_grid        | step_grid (Unit 1)        | Valid list of lists in -> valid list of lists out, converted   |
| bridge_place_pattern    | place_pattern (Unit 1)    | Valid dims + valid name -> centered pattern grid, converted    |
| bridge_get_pattern_names| get_patterns (Unit 1)     | Returns dict, bridge extracts key strings                     |
| gol_server (init)       | bridge_create_grid (Unit 2)| Creates initial empty grid as R matrix                       |
| gol_server (tick)       | bridge_step_grid (Unit 2) | Advances grid one generation                                  |
| gol_server (reset)      | bridge_create_grid (Unit 2)| Creates fresh empty grid                                     |
| gol_server (pattern)    | bridge_place_pattern (Unit 2) | Places named pattern on grid                             |
| gol_ui (init)           | bridge_get_pattern_names (Unit 2) | Populates pattern dropdown                           |
| validate_cli_args       | bridge_get_pattern_names (Unit 2) | Validates --pattern argument                         |
| main                    | bridge_init (Unit 2)      | Initializes Python engine before any bridge calls             |
| main                    | gol_ui (Unit 3)           | Constructs UI with grid dimensions and pattern list           |
| main                    | gol_server (Unit 3)       | Constructs server with bridge and validated parameters        |

### Shared Invariants

1. **Grid type invariant (Python side).** Every grid passed to or returned
   from Python functions is a `list[list[bool]]` with `len(grid) >= 3`
   and `len(grid[0]) >= 3`.

2. **Grid type invariant (R side).** Every grid in R is a logical matrix
   with `nrow >= 3` and `ncol >= 3`.

3. **Dimension preservation invariant.** Python grid dimensions (rows, cols)
   map exactly to R matrix dimensions: `nrow(matrix) == rows`,
   `ncol(matrix) == cols`.

4. **Cell state preservation invariant.** Python True maps to R TRUE,
   Python False maps to R FALSE. The mapping is bijective and lossless.

5. **No cached Python objects invariant.** No Python list or Python object
   is retained across bridge function calls. Every call is a complete
   R-to-Python-to-R round-trip.

6. **Immutability invariant (Python side).** No Python function modifies
   its input grid. All grid-returning functions produce a new list of lists.

7. **Pattern name invariant.** Pattern names are compared
   case-insensitively. The canonical form in Python is lowercase.

8. **0-based / 1-based indexing boundary.** Python uses 0-based indexing;
   R uses 1-based indexing. The bridge handles this transparently:
   Python[i][j] corresponds to R[i+1, j+1]. No other module needs to be
   aware of the index mapping.

9. **Toroidal wrapping formula (Python side).** Wherever toroidal wrapping
   is applied in Python, the formula is `index % dim`, converting any
   integer coordinate to a valid 0-based index.

---

*End of blueprint contracts.*
