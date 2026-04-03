# Blueprint Contracts (Tier 2 + Tier 3) -- gol-python

**Project:** Conway's Game of Life (Python/tkinter)
**Blueprint version:** 1.0
**Date:** 2026-03-29
**Units:** 4

---

## File Tree

```
gol-python/
  engine.py          # Unit 1 -- GoL Engine
  patterns.py        # Unit 2 -- Pattern Library
  display.py         # Unit 3 -- Display
  main.py            # Unit 4 -- Main
  tests/
    test_engine.py   # Unit 1 tests
    test_patterns.py # Unit 2 tests
    test_display.py  # Unit 3 tests
    test_main.py     # Unit 4 tests
```

---

## Unit 1: GoL Engine (`engine.py`)

### Tier 2 -- Signatures

```python
class Engine:
    rows: int
    cols: int
    alive_cells: set[tuple[int, int]]
    generation: int

    def __init__(self, rows: int = 50, cols: int = 50) -> None: ...

    def count_neighbors(self, row: int, col: int) -> int: ...

    def step(self) -> None: ...

    def toggle_cell(self, row: int, col: int) -> None: ...

    def clear(self) -> None: ...

    def get_alive_cells(self) -> set[tuple[int, int]]: ...

    def is_alive(self, row: int, col: int) -> bool: ...
```

### Tier 3 -- Behavioral Contracts

#### `Engine.__init__(self, rows, cols)`

- **PRE:** `rows >= 3` and `cols >= 3`.
- **POST:** `self.rows == rows` and `self.cols == cols`.
- **POST:** `self.alive_cells` is an empty set.
- **POST:** `self.generation == 0`.
- **ERR:** Raises `ValueError` if `rows < 3` or `cols < 3`.

#### `Engine.count_neighbors(self, row, col)`

- **PRE:** `0 <= row < self.rows` and `0 <= col < self.cols`.
- **POST:** Returns an `int` in range `[0, 8]`.
- **POST:** The returned count equals the number of cells in the Moore
  neighborhood (8 surrounding cells) of `(row, col)` that are in
  `self.alive_cells`, using toroidal wrapping for edge cells.
- **POST:** `self.alive_cells` is unchanged (read-only operation).
- **TOROIDAL:** For row `r` and col `c`, neighbors include
  `((r + dr) % self.rows, (c + dc) % self.cols)` for each
  `(dr, dc)` in `{-1, 0, 1} x {-1, 0, 1}` excluding `(0, 0)`.

#### `Engine.step(self)`

- **PRE:** None (valid in any state).
- **POST:** `self.generation` has increased by exactly 1.
- **POST:** `self.alive_cells` reflects one application of B3/S23 rules:
  - A dead cell with exactly 3 alive neighbors becomes alive.
  - An alive cell with 2 or 3 alive neighbors stays alive.
  - All other alive cells become dead.
- **POST:** Rules are applied simultaneously: the new state is computed
  entirely from the old state before any mutation occurs.

#### `Engine.toggle_cell(self, row, col)`

- **PRE:** `0 <= row < self.rows` and `0 <= col < self.cols`.
- **POST:** If `(row, col)` was in `self.alive_cells` before the call, it is
  not in `self.alive_cells` after the call, and vice versa.
- **POST:** No other cell's state is changed.
- **POST:** `self.generation` is unchanged.

#### `Engine.clear(self)`

- **PRE:** None.
- **POST:** `self.alive_cells` is an empty set.
- **POST:** `self.generation == 0`.
- **POST:** `self.rows` and `self.cols` are unchanged.

#### `Engine.get_alive_cells(self)`

- **PRE:** None.
- **POST:** Returns a `set[tuple[int, int]]` equal to `self.alive_cells`.
- **POST:** The returned set is a copy; mutating it does not affect the engine.

#### `Engine.is_alive(self, row, col)`

- **PRE:** `0 <= row < self.rows` and `0 <= col < self.cols`.
- **POST:** Returns `True` if `(row, col)` is in `self.alive_cells`, else
  `False`.
- **POST:** `self.alive_cells` is unchanged.

---

## Unit 2: Pattern Library (`patterns.py`)

### Tier 2 -- Signatures

```python
PATTERNS: dict[str, list[tuple[int, int]]]

def get_pattern_names() -> list[str]: ...

def get_pattern(name: str) -> list[tuple[int, int]]: ...

def place_pattern(
    engine: "Engine",
    name: str,
    center_row: int,
    center_col: int,
) -> None: ...
```

### Tier 3 -- Behavioral Contracts

#### `PATTERNS`

- **INVARIANT:** A module-level dict mapping pattern name strings to lists of
  `(row, col)` offset tuples.
- **INVARIANT:** Contains exactly these keys (title case): `"Blinker"`,
  `"Block"`, `"Beacon"`, `"Glider"`, `"Pulsar"`, `"Gosper Glider Gun"`.
- **INVARIANT:** All offsets use `(0, 0)` as the pattern's top-left corner.
  All row and col values are >= 0.
- **INVARIANT:** Cell counts match the spec: Blinker=3, Block=4, Beacon=6,
  Glider=5, Pulsar=48, Gosper Glider Gun=36.

#### `get_pattern_names()`

- **PRE:** None.
- **POST:** Returns a `list[str]` containing all keys of `PATTERNS`, sorted
  alphabetically.
- **POST:** The returned list has exactly 6 elements.

#### `get_pattern(name)`

- **PRE:** `name` is a string.
- **POST:** Performs case-insensitive lookup against `PATTERNS` keys.
- **POST:** Returns the list of `(row, col)` offset tuples for the matched
  pattern.
- **ERR:** Raises `KeyError` if no pattern matches `name` (case-insensitive).
  The exception message includes the unrecognized name.

#### `place_pattern(engine, name, center_row, center_col)`

- **PRE:** `engine` is an `Engine` instance. `name` resolves via
  `get_pattern()`. `center_row` and `center_col` are valid grid coordinates.
- **POST:** `engine.clear()` has been called (all cells dead, generation = 0).
- **POST:** The pattern's cells are placed on the grid centered at
  `(center_row, center_col)`. Centering means the midpoint of the pattern's
  bounding box aligns with the center point.
- **POST:** For each offset `(r, c)` in the pattern data, the absolute
  coordinate `((center_row - bh//2 + r) % engine.rows,
  (center_col - bw//2 + c) % engine.cols)` is alive, where `bh` and `bw`
  are the pattern's bounding box height and width.
- **POST:** If the pattern bounding box exceeds the grid dimensions in either
  axis, a warning is printed to the console (via `print()`).
- **ERR:** Raises `KeyError` (propagated from `get_pattern()`) if `name` is
  not recognized.

---

## Unit 3: Display (`display.py`)

### Tier 2 -- Signatures

```python
import tkinter as tk
from engine import Engine

CELL_SIZE: int  # 12 pixels (including 1-pixel grid line)
COLOR_ALIVE: str  # "#000000"
COLOR_DEAD: str  # "#FFFFFF"
COLOR_GRID: str  # "#CCCCCC"

class GameDisplay:
    root: tk.Tk
    engine: Engine
    canvas: tk.Canvas
    running: bool
    speed: int
    after_id: str | None

    def __init__(
        self,
        root: tk.Tk,
        engine: Engine,
        patterns_module: object,
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

### Tier 3 -- Behavioral Contracts

#### `CELL_SIZE`, `COLOR_ALIVE`, `COLOR_DEAD`, `COLOR_GRID`

- **INVARIANT:** `CELL_SIZE == 12`.
- **INVARIANT:** `COLOR_ALIVE == "#000000"`, `COLOR_DEAD == "#FFFFFF"`,
  `COLOR_GRID == "#CCCCCC"`.

#### `GameDisplay.__init__(self, root, engine, patterns_module)`

- **PRE:** `root` is a `tk.Tk` instance. `engine` is an `Engine` instance.
  `patterns_module` exposes `get_pattern_names()` and `place_pattern()`.
- **POST:** `self.engine` is set to `engine`.
- **POST:** `self.running == False`.
- **POST:** `self.speed == 10` (default speed, may be overridden by caller).
- **POST:** A `tk.Canvas` is created with width `engine.cols * CELL_SIZE` and
  height `engine.rows * CELL_SIZE`, packed into `root`.
- **POST:** Control panel is created below the canvas containing: Start button,
  Stop button, Step button, Reset button, speed slider (range 1-60, default
  10), speed label, generation counter label ("Generation: 0"), and pattern
  dropdown populated from `get_pattern_names()`.
- **POST:** Mouse `<Button-1>` click on the canvas is bound to
  `on_cell_click`.
- **POST:** `draw_grid()` has been called (initial render).

#### `GameDisplay.draw_grid(self)`

- **PRE:** None.
- **POST:** The canvas displays the current engine state. Each alive cell is
  drawn as a `CELL_SIZE x CELL_SIZE` filled rectangle in `COLOR_ALIVE`. Each
  dead cell is drawn in `COLOR_DEAD`. Grid lines are drawn in `COLOR_GRID`.
- **POST:** The generation counter label text is updated to
  `"Generation: {engine.generation}"`.

#### `GameDisplay.on_cell_click(self, event)`

- **PRE:** `event` is a tkinter mouse event with `.x` and `.y` pixel
  coordinates within the canvas.
- **POST:** The pixel coordinates are translated to grid `(row, col)` as
  `row = event.y // CELL_SIZE`, `col = event.x // CELL_SIZE`.
- **POST:** `engine.toggle_cell(row, col)` has been called.
- **POST:** `draw_grid()` has been called (immediate visual update).

#### `GameDisplay.start(self)`

- **PRE:** None.
- **POST:** `self.running == True`.
- **POST:** `tick()` is scheduled via `root.after()`.
- **POST:** The Start button is disabled; the Stop button is enabled.

#### `GameDisplay.stop(self)`

- **PRE:** None.
- **POST:** `self.running == False`.
- **POST:** Any pending `after()` callback is cancelled.
- **POST:** The Stop button is disabled; the Start button is enabled.

#### `GameDisplay.step_once(self)`

- **PRE:** None.
- **POST:** `engine.step()` has been called exactly once.
- **POST:** `draw_grid()` has been called.
- **POST:** `self.running` is unchanged (no auto-advance is scheduled).

#### `GameDisplay.reset(self)`

- **PRE:** None.
- **POST:** If the simulation was running, `stop()` has been called.
- **POST:** `engine.clear()` has been called.
- **POST:** `draw_grid()` has been called.
- **POST:** The generation counter label reads `"Generation: 0"`.

#### `GameDisplay.update_speed(self, value)`

- **PRE:** `value` is a string representation of a number (from the slider
  callback).
- **POST:** `self.speed` is set to `int(float(value))`.
- **POST:** The speed label text is updated to show the new speed value.
- **POST:** If the simulation is running, the new speed takes effect on the
  next `tick()` scheduling (no restart required).

#### `GameDisplay.load_pattern(self, name)`

- **PRE:** `name` is a string pattern name.
- **POST:** If the simulation was running, `stop()` has been called.
- **POST:** `place_pattern(engine, name, engine.rows // 2, engine.cols // 2)`
  has been called.
- **POST:** `draw_grid()` has been called.

#### `GameDisplay.tick(self)`

- **PRE:** `self.running == True` (only called when simulation is active).
- **POST:** `engine.step()` has been called exactly once.
- **POST:** `draw_grid()` has been called.
- **POST:** `tick()` is scheduled again via `root.after()` with interval
  `1000 // self.speed` milliseconds.

---

## Unit 4: Main (`main.py`)

### Tier 2 -- Signatures

```python
import argparse

def parse_args(argv: list[str] | None = None) -> argparse.Namespace: ...

def validate_args(args: argparse.Namespace) -> None: ...

def main(argv: list[str] | None = None) -> None: ...
```

### Tier 3 -- Behavioral Contracts

#### `parse_args(argv)`

- **PRE:** `argv` is a list of strings (command-line arguments excluding the
  program name), or `None` to read from `sys.argv`.
- **POST:** Returns an `argparse.Namespace` with attributes:
  - `width`: `int`, default `50`.
  - `height`: `int`, default `50`.
  - `speed`: `int`, default `10`.
  - `pattern`: `str | None`, default `None`.
- **POST:** Unrecognized arguments cause argparse to print usage and exit.

#### `validate_args(args)`

- **PRE:** `args` is an `argparse.Namespace` as returned by `parse_args()`.
- **POST:** Returns `None` if all constraints pass.
- **ERR:** If `args.width < 3` or `args.height < 3`, prints an error message
  to stderr and calls `sys.exit(1)`.
- **ERR:** If `args.speed < 1` or `args.speed > 60`, prints an error message
  to stderr and calls `sys.exit(1)`.
- **ERR:** If `args.pattern` is not `None` and does not match any known pattern
  name (case-insensitive via `get_pattern()`), prints an error message to
  stderr listing valid pattern names and calls `sys.exit(1)`.

#### `main(argv)`

- **PRE:** `argv` is an optional list of CLI argument strings, or `None`.
- **POST:** Calls `parse_args(argv)` followed by `validate_args()`.
- **POST:** Creates an `Engine(rows=args.height, cols=args.width)`.
- **POST:** Creates a `tk.Tk` root with title `"Conway's Game of Life"` and
  `resizable(False, False)`.
- **POST:** Creates a `GameDisplay(root, engine, patterns_module)`.
- **POST:** Sets the display speed to `args.speed`.
- **POST:** If `args.pattern` is not `None`, calls
  `display.load_pattern(args.pattern)`.
- **POST:** Calls `root.mainloop()`.

---

*End of blueprint contracts.*
