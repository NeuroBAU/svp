# Blueprint Contracts (Tier 2 + Tier 3) -- gol-python-r

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
    test_display.py    # Unit 3 tests (smoke tests only)
    test_main.py       # Unit 4 tests
```

---

## Unit 1: R Engine (`R/engine.R`)

### Tier 2 — Signatures

```r
create_grid <- function(rows = 30L, cols = 30L) { ... }
count_neighbors <- function(grid) { ... }
step_grid <- function(grid) { ... }
get_patterns <- function() { ... }
place_pattern <- function(grid, pattern_name) { ... }
```

### Tier 3 — Behavioral Contracts

**Dependencies:** None.

**create_grid:**

Parameters:

| Name | Type    | Default | Description                  |
|------|---------|---------|------------------------------|
| rows | integer | 30L     | Number of rows (>= 3)       |
| cols | integer | 30L     | Number of columns (>= 3)    |

Returns: logical matrix of dimensions `rows x cols`, all FALSE.

- PRE-1: is.numeric(rows) && length(rows) == 1 && rows >= 3
- PRE-2: is.numeric(cols) && length(cols) == 1 && cols >= 3
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == as.integer(rows) && ncol(result) == as.integer(cols)
- POST-3: all(result == FALSE)
- ERR-1: rows < 3 || cols < 3 -> stop("Grid dimensions must be at least 3x3")
- ERR-2: !is.numeric(rows) || !is.numeric(cols) -> stop("rows and cols must be numeric")

Spec refs: FR-3.1.1, FR-3.1.6

**count_neighbors:**

Parameters:

| Name | Type           | Default | Description                |
|------|----------------|---------|----------------------------|
| grid | logical matrix | (none)  | Current grid state         |

Returns: integer matrix of same dimensions as `grid`. Each element
contains the count (0--8) of TRUE neighbors in the Moore neighborhood
with toroidal wrapping.

- PRE-1: is.matrix(grid) && is.logical(grid)
- PRE-2: nrow(grid) >= 3 && ncol(grid) >= 3
- POST-1: is.matrix(result) && is.integer(result)
- POST-2: nrow(result) == nrow(grid) && ncol(result) == ncol(grid)
- POST-3: all(result >= 0L) && all(result <= 8L)
- POST-4: For an all-FALSE grid, all(result == 0L)
- POST-5: For a grid with a single TRUE cell at [r, c], the result has exactly 1 at each of the 8 toroidal neighbors of [r, c] and 0 elsewhere (including [r, c] itself).
- POST-6: grid is not modified (no side effects).
- ERR-1: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.1.2

**step_grid:**

Parameters:

| Name | Type           | Default | Description                |
|------|----------------|---------|----------------------------|
| grid | logical matrix | (none)  | Current generation grid    |

Returns: logical matrix of same dimensions -- the next generation
after applying B3/S23 rules.

- PRE-1: is.matrix(grid) && is.logical(grid)
- PRE-2: nrow(grid) >= 3 && ncol(grid) >= 3
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == nrow(grid) && ncol(result) == ncol(grid)
- POST-3: For every cell [r, c] with neighbors == count_neighbors(grid)[r, c]: result[r, c] == TRUE iff (neighbors == 3) || (grid[r, c] && neighbors == 2)
- POST-4: grid is not modified (no side effects).
- POST-5: An all-FALSE grid returns an all-FALSE grid.
- POST-6: A blinker oscillates: step_grid(step_grid(blinker_grid)) == blinker_grid.
- POST-7: A block is stable: step_grid(block_grid) == block_grid.
- POST-8: A glider translates: after 4 steps the glider pattern is offset by (1, 1) with toroidal wrapping.
- ERR-1: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.1.3, AC-3.1.B, AC-3.1.C

**get_patterns:**

Parameters: None.

Returns: named list of 6 elements. Each element is a two-column
integer matrix with columns representing (row_offset, col_offset),
1-based. Names: "beacon", "blinker", "block", "glider",
"gosper_glider_gun", "pulsar" (alphabetical, lowercase).

- PRE: (none -- no arguments)
- POST-1: is.list(result) && length(result) == 6L
- POST-2: identical(sort(names(result)), c("beacon", "blinker", "block", "glider", "gosper_glider_gun", "pulsar"))
- POST-3: For each element m in result: is.matrix(m) && is.integer(m) && ncol(m) == 2L && nrow(m) >= 1L
- POST-4: For each element m, all(m >= 1L) (all offsets are 1-based positive)
- POST-5: result$blinker has 3 rows (3 cells), bounding box 1x3.
- POST-6: result$block has 4 rows (4 cells), bounding box 2x2.
- POST-7: result$beacon has 6 rows (6 cells), bounding box 4x4.
- POST-8: result$glider has 5 rows (5 cells), bounding box 3x3.
- POST-9: result$pulsar has 48 rows (48 cells), bounding box 13x13.
- POST-10: result$gosper_glider_gun has 36 rows (36 cells), bounding box 9x36.
- POST-11: Successive calls return identical results (immutable data).
- ERR: (none -- function cannot fail)

Spec refs: FR-3.1.4, FR-3.4.1, AC-3.1.D

**place_pattern:**

Parameters:

| Name         | Type           | Default | Description                             |
|--------------|----------------|---------|-----------------------------------------|
| grid         | logical matrix | (none)  | Grid to place the pattern on            |
| pattern_name | character      | (none)  | Pattern name (case-insensitive)         |

Returns: logical matrix with grid cleared and pattern placed centered.

- PRE-1: is.matrix(grid) && is.logical(grid)
- PRE-2: is.character(pattern_name) && length(pattern_name) == 1L
- PRE-3: tolower(pattern_name) %in% names(get_patterns())
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == nrow(grid) && ncol(result) == ncol(grid)
- POST-3: sum(result) == nrow(pattern_data) (number of alive cells equals pattern cell count, unless toroidal wrapping causes overlapping offsets)
- POST-4: Pattern is centered: row_offset = floor((nrow(grid) - pattern_height) / 2) + 1, col_offset = floor((ncol(grid) - pattern_width) / 2) + 1, where pattern_height = max(pattern[, 1]) and pattern_width = max(pattern[, 2])
- POST-5: All non-pattern cells are FALSE (grid was cleared first).
- POST-6: grid is not modified (no side effects).
- WARN-1: If pattern_height > nrow(grid) || pattern_width > ncol(grid) -> warning() issued containing "pattern" and "grid" in the message; cells placed using ((index - 1) %% dim) + 1 toroidal wrapping.
- ERR-1: Unknown pattern name -> stop() with message containing "Unknown pattern" and listing valid names.
- ERR-2: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.1.5, AC-3.1.B

---

## Unit 2: Python Bridge (`bridge.py`)

### Tier 2 — Signatures

```python
def init_r_engine(r_source_path: str) -> None: ...

def r_create_grid(rows: int, cols: int) -> list[list[bool]]: ...

def r_step_grid(grid: list[list[bool]]) -> list[list[bool]]: ...

def r_place_pattern(rows: int, cols: int, pattern_name: str) -> list[list[bool]]: ...

def r_get_patterns() -> list[str]: ...
```

### Tier 3 — Behavioral Contracts

**Dependencies:** **Unit 1** (create_grid, count_neighbors, step_grid, get_patterns, place_pattern).

**init_r_engine:**

Parameters:

| Name          | Type | Default | Description                                  |
|---------------|------|---------|----------------------------------------------|
| r_source_path | str  | (none)  | Filesystem path to `R/engine.R`              |

Returns: None. Side effect: sources the R file into the embedded R session.

- PRE-1: `r_source_path` is a valid filesystem path string.
- POST-1: After return, the R global environment contains the functions `create_grid`, `count_neighbors`, `step_grid`, `get_patterns`, and `place_pattern`.
- POST-2: Subsequent calls to `r_create_grid`, `r_step_grid`, `r_place_pattern`, and `r_get_patterns` will succeed.
- ERR-1: If the file at `r_source_path` does not exist or cannot be sourced, raises `RuntimeError` with a descriptive message including the path.
- ERR-2: If rpy2 is not installed or R is not available, raises `ImportError` with a descriptive message (this occurs at module import time, not at function call time).

Spec refs: FR-3.2.1, FR-3.2.8

**r_create_grid:**

Parameters:

| Name | Type | Default | Description                  |
|------|------|---------|------------------------------|
| rows | int  | (none)  | Number of rows (>= 3)       |
| cols | int  | (none)  | Number of columns (>= 3)    |

Returns: `list[list[bool]]` -- `rows` sublists each of length `cols`, all False.

- PRE-1: `init_r_engine` has been called successfully.
- PRE-2: `rows >= 3` and `cols >= 3`.
- POST-1: `len(result) == rows`.
- POST-2: For each sublist: `len(sublist) == cols`.
- POST-3: All values are `False`.
- POST-4: The result is a Python list (not an R object). No R objects are retained.
- ERR-1: R-side errors (e.g., invalid dimensions) propagate as `rpy2.rinterface_lib.embedded.RRuntimeError` or equivalent.

Spec refs: FR-3.2.2, FR-3.2.6, FR-3.2.7, AC-3.2.A

**r_step_grid:**

Parameters:

| Name | Type              | Default | Description                          |
|------|-------------------|---------|--------------------------------------|
| grid | list[list[bool]]  | (none)  | Current generation as Python grid    |

Returns: `list[list[bool]]` -- next generation grid.

- PRE-1: `init_r_engine` has been called successfully.
- PRE-2: `grid` is a rectangular list of lists of booleans with dimensions >= 3x3.
- POST-1: `len(result) == len(grid)` and `len(result[0]) == len(grid[0])`.
- POST-2: Cell states reflect one application of B3/S23 rules as computed by R `step_grid`.
- POST-3: Conversion preserves cell states exactly: R TRUE -> Python True, R FALSE -> Python False.
- POST-4: Round-trip is lossless: converting a Python grid to R and back yields the original values.
- POST-5: The input `grid` is not modified.
- POST-6: No R objects are cached; the R matrix is created, used, and discarded within the call.

Spec refs: FR-3.2.3, FR-3.2.6, FR-3.2.7, FR-4.3.1, AC-3.2.B, AC-3.2.C

**r_place_pattern:**

Parameters:

| Name         | Type | Default | Description                                  |
|--------------|------|---------|----------------------------------------------|
| rows         | int  | (none)  | Grid rows                                    |
| cols         | int  | (none)  | Grid columns                                 |
| pattern_name | str  | (none)  | Pattern name (case-insensitive)              |

Returns: `list[list[bool]]` -- grid with pattern centered.

- PRE-1: `init_r_engine` has been called successfully.
- PRE-2: `rows >= 3` and `cols >= 3`.
- PRE-3: `pattern_name` is a recognized pattern name (case-insensitive).
- POST-1: `len(result) == rows` and `len(result[0]) == cols`.
- POST-2: The grid was cleared before pattern placement (all non-pattern cells are False).
- POST-3: The pattern is centered using R's centering formula.
- POST-4: Conversion preserves cell states exactly.
- ERR-1: Unknown pattern name causes an R-side stop() which propagates as an R runtime error.

Spec refs: FR-3.2.4, AC-3.2.C

**r_get_patterns:**

Parameters: None.

Returns: `list[str]` -- list of pattern name strings.

- PRE-1: `init_r_engine` has been called successfully.
- POST-1: Returns a Python list of strings.
- POST-2: `len(result) == 6`.
- POST-3: Each element is a lowercase pattern name string.
- POST-4: The list contains exactly: "beacon", "blinker", "block", "glider", "gosper_glider_gun", "pulsar" (not necessarily in this order).

Spec refs: FR-3.2.5

---

## Unit 3: Python Display (`display.py`)

### Tier 2 — Signatures

```python
import tkinter as tk

CELL_SIZE: int  # 12 pixels (including 1-pixel grid line)
COLOR_ALIVE: str  # "#000000"
COLOR_DEAD: str  # "#FFFFFF"
COLOR_GRID: str  # "#CCCCCC"

class GameDisplay:
    root: tk.Tk
    bridge: object
    grid: list[list[bool]]
    canvas: tk.Canvas
    running: bool
    speed: int
    generation: int
    after_id: str | None

    def __init__(
        self,
        root: tk.Tk,
        bridge: object,
        rows: int,
        cols: int,
    ) -> None: ...

    def draw_grid(self) -> None: ...

    def on_cell_click(self, event: tk.Event) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def step_once(self) -> None: ...

    def reset(self) -> None: ...

    def update_speed(self, value: str) -> None: ...

    def load_pattern(self, name: str) -> None: ...

    def tick(self) -> None: ...
```

### Tier 3 — Behavioral Contracts

**Dependencies:** **Unit 2** (r_create_grid, r_step_grid, r_place_pattern, r_get_patterns).

**CELL_SIZE, COLOR_ALIVE, COLOR_DEAD, COLOR_GRID:**

- INVARIANT-1: `CELL_SIZE == 12`.
- INVARIANT-2: `COLOR_ALIVE == "#000000"`, `COLOR_DEAD == "#FFFFFF"`, `COLOR_GRID == "#CCCCCC"`.

**GameDisplay.__init__:**

Parameters:

| Name   | Type    | Default | Description                                    |
|--------|---------|---------|------------------------------------------------|
| root   | tk.Tk   | (none)  | Tkinter root window                            |
| bridge | object  | (none)  | Bridge module exposing r_create_grid, etc.     |
| rows   | int     | (none)  | Grid rows                                      |
| cols   | int     | (none)  | Grid columns                                   |

Returns: None (constructor).

- PRE-1: `root` is a `tk.Tk` instance. `bridge` exposes `r_create_grid`, `r_step_grid`, `r_place_pattern`, `r_get_patterns`.
- POST-1: `self.bridge` is set to `bridge`.
- POST-2: `self.grid` is initialized via `bridge.r_create_grid(rows, cols)`.
- POST-3: `self.running == False`.
- POST-4: `self.speed == 10` (default speed, may be overridden by caller).
- POST-5: `self.generation == 0`.
- POST-6: A `tk.Canvas` is created with width `cols * CELL_SIZE` and height `rows * CELL_SIZE`, packed into `root`.
- POST-7: Control panel is created below the canvas containing: Start button, Stop button, Step button, Reset button, speed slider (range 1-60, default 10), speed label, generation counter label ("Generation: 0"), and pattern dropdown populated from `bridge.r_get_patterns()`.
- POST-8: Mouse `<Button-1>` click on the canvas is bound to `on_cell_click`.
- POST-9: `draw_grid()` has been called (initial render).

Spec refs: FR-3.3.1, FR-3.3.7

**GameDisplay.draw_grid:**

- PRE: None.
- POST-1: The canvas displays the current `self.grid` state. Each alive cell is drawn as a `CELL_SIZE x CELL_SIZE` filled rectangle in `COLOR_ALIVE`. Each dead cell is drawn in `COLOR_DEAD`. Grid lines are drawn in `COLOR_GRID`.
- POST-2: The generation counter label text is updated to `"Generation: {self.generation}"`.

Spec refs: FR-3.3.1

**GameDisplay.on_cell_click:**

Parameters:

| Name  | Type     | Default | Description                            |
|-------|----------|---------|----------------------------------------|
| event | tk.Event | (none)  | Mouse click event with .x, .y pixels  |

- PRE: `event` is a tkinter mouse event with `.x` and `.y` pixel coordinates within the canvas.
- POST-1: Pixel coordinates are translated to grid `(row, col)` as `row = event.y // CELL_SIZE`, `col = event.x // CELL_SIZE`.
- POST-2: `self.grid[row][col]` is toggled: True becomes False, False becomes True.
- POST-3: `draw_grid()` has been called (immediate visual update).
- POST-4: `self.generation` is unchanged.

Spec refs: FR-3.3.2, FR-4.3.2

**GameDisplay.start:**

- PRE: None.
- POST-1: `self.running == True`.
- POST-2: `tick()` is scheduled via `root.after()`.
- POST-3: The Start button is disabled; the Stop button is enabled.

Spec refs: FR-3.3.3

**GameDisplay.stop:**

- PRE: None.
- POST-1: `self.running == False`.
- POST-2: Any pending `after()` callback is cancelled.
- POST-3: The Stop button is disabled; the Start button is enabled.

Spec refs: FR-3.3.3

**GameDisplay.step_once:**

- PRE: None.
- POST-1: `self.grid` is updated to `bridge.r_step_grid(self.grid)`.
- POST-2: `self.generation` has increased by exactly 1.
- POST-3: `draw_grid()` has been called.
- POST-4: `self.running` is unchanged (no auto-advance is scheduled).

Spec refs: FR-3.3.3

**GameDisplay.reset:**

- PRE: None.
- POST-1: If the simulation was running, `stop()` has been called.
- POST-2: `self.grid` is replaced with `bridge.r_create_grid(rows, cols)` (all cells dead).
- POST-3: `self.generation == 0`.
- POST-4: `draw_grid()` has been called.
- POST-5: The generation counter label reads `"Generation: 0"`.

Spec refs: FR-3.3.3, FR-3.3.5

**GameDisplay.update_speed:**

Parameters:

| Name  | Type | Default | Description                                      |
|-------|------|---------|--------------------------------------------------|
| value | str  | (none)  | String representation of speed (from slider)     |

- PRE: `value` is a string representation of a number (from the slider callback).
- POST-1: `self.speed` is set to `int(float(value))`.
- POST-2: The speed label text is updated to show the new speed value.
- POST-3: If the simulation is running, the new speed takes effect on the next `tick()` scheduling (no restart required).

Spec refs: FR-3.3.4

**GameDisplay.load_pattern:**

Parameters:

| Name | Type | Default | Description                  |
|------|------|---------|------------------------------|
| name | str  | (none)  | Pattern name string          |

- PRE: `name` is a string pattern name.
- POST-1: If the simulation was running, `stop()` has been called.
- POST-2: `self.grid` is replaced with `bridge.r_place_pattern(rows, cols, name)`.
- POST-3: `self.generation == 0`.
- POST-4: `draw_grid()` has been called.

Spec refs: FR-3.3.6

**GameDisplay.tick:**

- PRE: `self.running == True` (only called when simulation is active).
- POST-1: `self.grid` is updated to `bridge.r_step_grid(self.grid)`.
- POST-2: `self.generation` has increased by exactly 1.
- POST-3: `draw_grid()` has been called.
- POST-4: `tick()` is scheduled again via `root.after()` with interval `1000 // self.speed` milliseconds.

Spec refs: FR-3.3.3, FR-3.3.4, FR-3.3.5

---

## Unit 4: Python Main (`main.py`)

### Tier 2 — Signatures

```python
import argparse

def parse_args(argv: list[str] | None = None) -> argparse.Namespace: ...

def validate_args(args: argparse.Namespace) -> None: ...

def main(argv: list[str] | None = None) -> None: ...
```

### Tier 3 — Behavioral Contracts

**Dependencies:** **Unit 2** (init_r_engine, r_get_patterns), **Unit 3** (GameDisplay).

**parse_args:**

Parameters:

| Name | Type              | Default | Description                                  |
|------|-------------------|---------|----------------------------------------------|
| argv | list[str] or None | None    | CLI args excluding program name, or None     |

Returns: `argparse.Namespace` with attributes `width`, `height`, `speed`, `pattern`.

- PRE: `argv` is a list of strings or `None` (reads from `sys.argv`).
- POST-1: `result.width` is `int`, default `50`.
- POST-2: `result.height` is `int`, default `50`.
- POST-3: `result.speed` is `int`, default `10`.
- POST-4: `result.pattern` is `str | None`, default `None`.
- POST-5: Unrecognized arguments cause argparse to print usage and exit.

Spec refs: FR-6.1, FR-6.2

**validate_args:**

Parameters:

| Name | Type               | Default | Description                         |
|------|--------------------|---------|-------------------------------------|
| args | argparse.Namespace | (none)  | Parsed args from parse_args         |

Returns: None if all constraints pass.

- PRE: `args` is an `argparse.Namespace` as returned by `parse_args()`.
- ERR-1: If `args.width < 3` or `args.height < 3`, prints an error message to stderr and calls `sys.exit(1)`.
- ERR-2: If `args.speed < 1` or `args.speed > 60`, prints an error message to stderr and calls `sys.exit(1)`.
- ERR-3: If `args.pattern` is not `None` and does not match any pattern name returned by `bridge.r_get_patterns()` (case-insensitive), prints an error message to stderr listing valid pattern names and calls `sys.exit(1)`.

Spec refs: FR-6.4, FR-6.5, FR-6.6, AC-6.C

**main:**

Parameters:

| Name | Type              | Default | Description                                  |
|------|-------------------|---------|----------------------------------------------|
| argv | list[str] or None | None    | CLI args excluding program name, or None     |

Returns: None (enters mainloop, never returns normally).

- PRE: `argv` is an optional list of CLI argument strings, or `None`.
- POST-1: Calls `parse_args(argv)` followed by `validate_args()`.
- POST-2: Resolves `R/engine.R` path relative to `main.py`'s location.
- POST-3: Calls `bridge.init_r_engine(r_source_path)`.
- POST-4: Creates a `tk.Tk` root with title `"Conway's Game of Life"` and `resizable(False, False)`.
- POST-5: Creates a `GameDisplay(root, bridge, rows=args.height, cols=args.width)`.
- POST-6: Sets the display speed to `args.speed`.
- POST-7: If `args.pattern` is not `None`, calls `display.load_pattern(args.pattern)`.
- POST-8: Calls `root.mainloop()`.

Spec refs: FR-6.1, FR-6.2, FR-6.3, AC-6.A, AC-6.B

---

## Cross-Unit Contract Summary

### Dependency Contracts

| Consumer              | Provider              | Contract                                                      |
|-----------------------|-----------------------|---------------------------------------------------------------|
| init_r_engine         | R/engine.R (Unit 1)   | Sources file; all 5 R functions available in global env       |
| r_create_grid         | create_grid (Unit 1)  | rows >= 3, cols >= 3 -> logical matrix, converted to Python   |
| r_step_grid           | step_grid (Unit 1)    | Valid logical matrix in -> valid logical matrix out, converted |
| r_place_pattern       | create_grid (Unit 1)  | Creates grid, then places pattern centered                    |
| r_place_pattern       | place_pattern (Unit 1)| Valid grid + valid name -> centered pattern grid              |
| r_get_patterns        | get_patterns (Unit 1) | Returns named list, bridge extracts name strings              |
| GameDisplay.__init__  | r_create_grid (Unit 2)| Creates initial empty grid                                    |
| GameDisplay.tick      | r_step_grid (Unit 2)  | Advances grid one generation                                  |
| GameDisplay.reset     | r_create_grid (Unit 2)| Creates fresh empty grid                                      |
| GameDisplay.load_pattern | r_place_pattern (Unit 2) | Places named pattern on grid                            |
| GameDisplay.__init__  | r_get_patterns (Unit 2)| Populates pattern dropdown                                   |
| validate_args         | r_get_patterns (Unit 2)| Validates --pattern argument                                 |
| main                  | init_r_engine (Unit 2)| Initializes R engine before any bridge calls                  |
| main                  | GameDisplay (Unit 3)  | Creates display with bridge and dimensions                    |

### Shared Invariants

1. **Grid type invariant (R side).** Every grid passed to or returned from R
   functions is a logical matrix with nrow >= 3 and ncol >= 3.

2. **Grid type invariant (Python side).** Every grid in Python is a
   `list[list[bool]]` with `len(grid) >= 3` and `len(grid[0]) >= 3`.

3. **Dimension preservation invariant.** R matrix dimensions (rows, cols) map
   exactly to Python list dimensions: `len(grid) == rows`,
   `len(grid[i]) == cols` for all `i`.

4. **Cell state preservation invariant.** R TRUE maps to Python True, R FALSE
   maps to Python False. The mapping is bijective and lossless.

5. **No cached R objects invariant.** No R matrix or R object is retained
   across bridge function calls. Every call is a complete Python-to-R-to-Python
   round-trip.

6. **Immutability invariant (R side).** No R function modifies its input grid.
   All grid-returning functions produce a new matrix.

7. **Pattern name invariant.** Pattern names are compared case-insensitively.
   The canonical form in R is lowercase.

8. **1-based / 0-based indexing boundary.** R uses 1-based indexing; Python
   uses 0-based indexing. The bridge handles this transparently: R[i, j]
   corresponds to Python[i-1][j-1]. No other module needs to be aware of the
   index mapping.

9. **Toroidal wrapping formula (R side).** Wherever toroidal wrapping is
   applied in R, the formula is ((index - 1) %% dim) + 1, converting any
   integer coordinate to a valid 1-based index.

---

*End of blueprint contracts.*
