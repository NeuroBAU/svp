# Blueprint Prose (Tier 1) -- gol-python

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
    test_display.py  # Unit 3 tests (smoke tests only, GUI excluded from coverage)
    test_main.py     # Unit 4 tests
```

---

## Unit 1: GoL Engine (`engine.py`)

**Purpose.** Encapsulates all simulation logic for Conway's Game of Life. This
unit owns the grid state and exposes a pure-logic API for advancing generations,
querying cell states, and mutating individual cells. It has zero GUI
dependencies, making it fully testable in isolation.

**Grid representation.** The engine stores the grid as a set of `(row, col)`
tuples representing alive cells. This sparse representation is efficient for
typical Game of Life patterns where most cells are dead. The grid dimensions
(rows, cols) are fixed at construction time and define the toroidal boundary.

**Core simulation.** The `step()` method computes one generation according to
the B3/S23 rule set. It iterates over every alive cell and its neighbors,
tallies neighbor counts, and produces the next generation's alive set in a
single pass. The old state is not mutated until the new state is fully computed,
guaranteeing simultaneous application of rules (FR-3.7.2).

**Neighbor counting.** The `count_neighbors()` method returns the number of
alive neighbors for a given cell using the Moore neighborhood (8 surrounding
cells). Coordinates wrap toroidally: a cell at column 0 considers column
`cols-1` as its left neighbor, and likewise for rows (FR-3.7.4).

**Mutation.** `toggle_cell()` flips a single cell between alive and dead.
`clear()` removes all alive cells and resets the generation counter.
`get_alive_cells()` returns the current set of alive coordinates for rendering
or inspection.

**Generation counter.** The engine maintains an integer generation counter that
starts at 0, increments by 1 on each `step()` call, and resets to 0 on
`clear()`. This counter is the single source of truth for the generation
display (FR-3.5).

**Dependencies.** None. This unit is a leaf in the dependency graph.

---

## Unit 2: Pattern Library (`patterns.py`)

**Purpose.** Provides a catalog of named preset patterns and a helper to place
them onto an engine grid. This unit is a pure data module plus a single
placement function; it carries no mutable state of its own.

**Pattern data.** The module defines a `PATTERNS` dictionary mapping pattern
names (strings) to lists of `(row, col)` offset tuples. Offsets are relative to
the pattern's top-left corner, with `(0, 0)` as the origin. All six patterns
from the spec are included: Blinker, Block, Beacon, Glider, Pulsar, and Gosper
Glider Gun. Pattern names in the dictionary use title case as they appear in the
spec (FR-3.6.3).

**Querying.** `get_pattern_names()` returns a sorted list of available pattern
name strings. `get_pattern(name)` retrieves the offset list for a given name,
performing a case-insensitive lookup. It raises `KeyError` if the name is not
found, enabling callers to produce clear error messages (FR-6.3).

**Placement.** `place_pattern(engine, name, center_row, center_col)` clears the
engine, looks up the named pattern, computes the absolute grid coordinates by
centering the pattern's bounding box on the given center point, and toggles the
resulting cells to alive. Coordinates that fall outside the grid wrap toroidally
via the engine's own modular arithmetic. If the pattern's bounding box exceeds
the grid dimensions, a warning is printed to the console (FR-3.6.5). After
placement, the generation counter is at 0 because `clear()` was called.

**Dependencies.** Unit 1 (engine) -- `place_pattern` calls `engine.clear()` and
`engine.toggle_cell()`.

---

## Unit 3: Display (`display.py`)

**Purpose.** Provides the graphical user interface using tkinter. The
`GameDisplay` class owns the canvas, all control widgets, and the simulation
run-loop. It delegates all state logic to the engine (Unit 1) and all pattern
data to the pattern library (Unit 2).

**Construction.** `__init__` receives the tkinter root window, an engine
instance, and the patterns module. It creates the canvas sized to the engine's
grid dimensions (each cell is 12x12 pixels including grid lines), lays out the
control panel (Start, Stop, Step, Reset buttons, speed slider with label,
generation counter label, and pattern dropdown), and binds mouse click events on
the canvas (FR-4.1).

**Rendering.** `draw_grid()` iterates over the canvas and draws each cell as a
filled rectangle -- black for alive, white for dead -- with gray grid lines
(FR-3.1.2, FR-3.1.3). It also updates the generation counter label.

**Cell interaction.** `on_cell_click(event)` translates pixel coordinates from
the mouse click into grid `(row, col)`, calls `engine.toggle_cell()`, and
redraws the grid immediately (FR-3.2).

**Simulation controls.** `start()` begins the auto-advance loop by scheduling
`tick()` via `root.after()`. It disables the Start button and enables the Stop
button. `stop()` cancels the scheduled callback and swaps button states.
`step_once()` calls `engine.step()` and redraws, without scheduling further
ticks. `reset()` stops the simulation, calls the engine's `clear()`, and
redraws (FR-3.3).

**Speed control.** `update_speed(value)` is the slider callback. It stores the
new speed (steps per second) so the next `tick()` uses the updated interval.
The speed label text is updated immediately (FR-3.4).

**Pattern loading.** `load_pattern(name)` stops the simulation, calls
`place_pattern(engine, name, center_row, center_col)` with the grid's center
coordinates, and redraws (FR-3.6.2).

**Tick loop.** `tick()` calls `engine.step()`, redraws the grid, and schedules
itself again after an interval derived from the current speed setting
(`1000 / speed` milliseconds). This is the heartbeat of the running simulation.

**Dependencies.** Unit 1 (engine), Unit 2 (patterns), tkinter (stdlib).

---

## Unit 4: Main (`main.py`)

**Purpose.** Entry point. Parses command-line arguments, validates them,
constructs the engine and display, optionally loads a startup pattern, and
enters the tkinter main loop.

**Argument parsing.** `parse_args()` uses `argparse` to define `--width`,
`--height`, `--speed`, and `--pattern` with defaults from the spec (50, 50, 10,
None). Returns the parsed namespace (FR-6.1).

**Validation.** `validate_args(args)` enforces constraints: width and height
must each be >= 3 (FR-6.4); speed must be in 1..60 (FR-6.5); if pattern is
given, it must be a recognized name (FR-6.3). On any violation, the function
prints a descriptive error to stderr and calls `sys.exit(1)`.

**Main function.** `main()` calls `parse_args()` and `validate_args()`,
constructs an `Engine(rows=height, cols=width)`, creates the tkinter root with
title "Conway's Game of Life" (FR-4.1.1), creates a `GameDisplay`, optionally
calls `load_pattern` if `--pattern` was given, sets the initial speed from
`--speed`, and enters `root.mainloop()`. The window is set to non-resizable
(FR-4.1.4).

**Dependencies.** Unit 1 (engine), Unit 2 (patterns), Unit 3 (display),
argparse (stdlib), sys (stdlib), tkinter (stdlib).

---

*End of blueprint prose.*
