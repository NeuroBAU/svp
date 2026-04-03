# Stakeholder Specification: Conway's Game of Life (R/Python Mixed)

**Project:** gol-r-python
**Archetype:** D (mixed, R primary / Python secondary)
**Version:** 1.0
**Date:** 2026-03-29

---

## 1. Overview

A desktop application implementing Conway's Game of Life using R for the
GUI and application layer (Shiny), with the simulation engine implemented
in Python. R provides the Shiny-based graphical interface, entry point,
and orchestration logic. Python provides the core computational engine
(grid creation, neighbor counting, generation stepping) as pure Python
functions. The two languages are bridged by reticulate, which allows R to
call Python functions directly and convert data between R matrices and
Python lists. The simulation uses the standard B3/S23 rule set on a
toroidal (wraparound) grid.

This is a plain Shiny app -- not golem or rhino. The project uses a
single conda environment containing both R and Python.

This project is a mixed-archetype test case for SVP 2.2, exercising
dual-language dispatch, cross-language bridge testing, and two-phase
assembly composition. It is the reverse of gol-python-r: R is primary
and Python is secondary.

---

## 2. Definitions

- **Cell:** A single square on the grid, either alive or dead.
- **Generation:** One discrete time step applying B3/S23 rules simultaneously.
- **B3/S23 rules:** Dead cell with exactly 3 alive neighbors is born. Alive
  cell with 2 or 3 alive neighbors survives. All other alive cells die.
- **Moore neighborhood:** The 8 cells adjacent horizontally, vertically, and
  diagonally to a given cell.
- **Toroidal grid:** Edges wrap: right connects to left, top to bottom.
- **Preset pattern:** A named initial configuration of alive cells.
- **Bridge:** The reticulate-based R layer translating between R and Python.
- **Shiny:** R web application framework providing the GUI.
- **Reactive value:** A Shiny construct that triggers UI updates when changed.

---

## 3. Functional Requirements

### 3.1 Python Simulation Engine

The engine is implemented entirely in Python and is the sole authority for
grid state computation. R never computes GoL logic directly.

- **FR-3.1.1:** `create_grid(rows, cols)` -- returns a list of lists of
  booleans with all cells False (dead). Default size 50x50.
- **FR-3.1.2:** `count_neighbors(grid)` -- returns a list of lists of
  integers containing alive-neighbor counts (0-8) per cell, using toroidal
  boundaries. The grid is treated as row-major: grid[row][col].
- **FR-3.1.3:** `step_grid(grid)` -- accepts a list of lists of booleans,
  returns a new list of lists for the next generation under B3/S23. Input
  is not modified. All transitions computed simultaneously.
- **FR-3.1.4:** `get_patterns()` -- returns a dict of preset patterns,
  each a list of (row, col) tuples using 0-based indexing relative to the
  pattern's top-left corner.
- **FR-3.1.5:** `place_pattern(rows, cols, pattern_name)` -- creates a
  new grid of the given dimensions, centers the named pattern, and returns
  the result. Centering: row_offset = (rows - height) // 2,
  col_offset = (cols - width) // 2. If the grid is smaller than the
  pattern, wrap via modular indexing.
- **FR-3.1.6:** Implemented in a single file `engine.py` using only the
  Python standard library.

**Acceptance Criteria (Python Engine):**
- AC-3.1.A: `create_grid(50, 50)` returns 50 lists of 50 False values.
- AC-3.1.B: Blinker oscillates, block is stable, glider translates with
  toroidal wrap -- all via `step_grid()`.
- AC-3.1.C: Input grid is not modified by `step_grid()`.
- AC-3.1.D: `get_patterns()` returns all six required patterns.

### 3.2 R Bridge (reticulate)

The bridge translates between R data structures and Python objects and
manages the reticulate connection to the Python engine.

- **FR-3.2.1:** Load `engine.py` into the reticulate Python session via
  `reticulate::source_python()`.
- **FR-3.2.2:** `bridge_create_grid(rows, cols)` -- calls Python
  `create_grid()`, converts the returned Python list of lists to an R
  logical matrix (row-major). TRUE for alive, FALSE for dead.
- **FR-3.2.3:** `bridge_step_grid(grid)` -- converts R logical matrix to
  Python list of lists of booleans, calls Python `step_grid()`, converts
  result back to R logical matrix.
- **FR-3.2.4:** `bridge_place_pattern(rows, cols, pattern_name)` -- calls
  Python `place_pattern()`, converts result to R logical matrix.
- **FR-3.2.5:** `bridge_get_pattern_names()` -- calls Python
  `get_patterns()`, extracts the dict keys, returns an R character vector
  of pattern name strings.
- **FR-3.2.6:** Conversion preserves dimensions exactly: Python grid with
  `rows` sublists of length `cols` yields an R matrix with `nrow == rows`
  and `ncol == cols`.
- **FR-3.2.7:** Conversion preserves cell states exactly. Python True maps
  to R TRUE, Python False to R FALSE. Round-trip is lossless.
- **FR-3.2.8:** If Python engine file cannot be loaded, call stop() with a
  descriptive message. If reticulate or Python is unavailable, call stop().

**Acceptance Criteria (Bridge):**
- AC-3.2.A: `bridge_create_grid(50, 50)` returns a 50x50 logical matrix
  of FALSE.
- AC-3.2.B: Round-tripped grid matches direct Python engine output for
  known GoL states.
- AC-3.2.C: Dimensions and cell states preserved exactly through conversion.
- AC-3.2.D: Missing `engine.py` causes stop() with descriptive message.

### 3.3 R Display and Controls (Shiny)

The GUI is a plain Shiny app providing grid visualization and interactive
controls. It delegates all simulation logic to the bridge (Section 3.2),
which in turn delegates to the Python engine.

- **FR-3.3.1:** Grid display using base R plot (image() or equivalent).
  Alive = black (#000000), dead = white (#FFFFFF). Default 50x50. The
  plot output is rendered via `renderPlot()`.
- **FR-3.3.2:** Click on the plot area to toggle a cell alive/dead
  (running or stopped). Clicking is handled via Shiny's `click` argument
  on `plotOutput()`, translating pixel coordinates to grid (row, col).
- **FR-3.3.3:** Start, Stop, Step, Reset action buttons. Start/Stop
  reflect simulation state. All simulation calls go through the bridge.
- **FR-3.3.4:** Speed slider: 1-60 steps/sec, default 10. Implemented
  as `sliderInput()`. Changes take effect immediately on the next tick.
- **FR-3.3.5:** Generation counter: "Generation: N" displayed as
  `textOutput()`. Starts at 0, increments per step, resets on Reset or
  pattern load.
- **FR-3.3.6:** Pattern dropdown: `selectInput()` populated from
  `bridge_get_pattern_names()`. Selection calls `bridge_place_pattern()`,
  resets counter, stops simulation.
- **FR-3.3.7:** App title "Conway's Game of Life" via `titlePanel()`.
  Layout: title at top, grid plot in main panel, controls in sidebar or
  below. Controls: Start, Stop, Step, Reset buttons, speed slider,
  generation counter, pattern dropdown.

**Acceptance Criteria (Display and Controls):**
- AC-3.3.A: Startup shows 50x50 empty grid with controls visible.
- AC-3.3.B: Start advances via Python engine; Stop halts; Step does one
  generation.
- AC-3.3.C: Reset clears grid and counter. Pattern selection loads
  correctly.

### 3.4 Preset Patterns

- **FR-3.4.1:** The following patterns shall be defined in the Python engine:

  | Name              | Type       | Bounding Box | Cells |
  |-------------------|------------|--------------|-------|
  | Blinker           | Oscillator | 1x3          | 3     |
  | Block             | Still life | 2x2          | 4     |
  | Beacon            | Oscillator | 4x4          | 6     |
  | Glider            | Spaceship  | 3x3          | 5     |
  | Pulsar            | Oscillator | 13x13        | 48    |
  | Gosper Glider Gun | Gun        | 9x36         | 36    |

---

## 4. Architecture and Cross-Language Integration

### 4.1 File Structure

```
gol-r-python/
  engine.py            # Unit 1 -- Python Engine
  R/
    bridge.R           # Unit 2 -- R Bridge (reticulate)
    display.R          # Unit 3 -- R Display (Shiny app)
    main.R             # Unit 4 -- R Main (entry point)
  inst/
    run_gol.R          # Unit 4 -- Rscript entry point
  environment.yml      # Conda environment definition
```

### 4.2 Language Boundaries

- **FR-4.2.1:** All GoL computation in Python. R contains no GoL logic.
- **FR-4.2.2:** All GUI/interaction in R (Shiny). Python contains no
  display logic.
- **FR-4.2.3:** Only `R/bridge.R` imports reticulate. Display and main
  depend only on the bridge's R API.
- **FR-4.2.4:** `engine.py` has no awareness of reticulate or R. Testable
  standalone in a pure Python session.

### 4.3 Data Flow

Per-generation cycle:

1. Shiny server holds grid as R logical matrix in a reactive value.
2. Tick/step calls `bridge_step_grid(grid)`.
3. Bridge converts R logical matrix to Python list of lists of booleans,
   calls Python `step_grid()`.
4. Python computes next generation, returns new list of lists.
5. Bridge converts back to R logical matrix.
6. Shiny reactive value is updated, triggering re-render of the plot.

- **FR-4.3.1:** Every step is a complete round-trip. No Python objects
  cached across steps.
- **FR-4.3.2:** Cell toggling modifies the R matrix directly via the
  reactive value. The modified grid is passed to Python on the next step
  call.

### 4.4 Environment

- **FR-4.4.1:** `environment.yml` defines conda environment `gol-r-python`
  with: R >= 4.1, Python >= 3.10, r-shiny, r-reticulate.
- **FR-4.4.2:** No Python packages beyond the standard library required at
  runtime. pytest is a dev-only dependency.

---

## 5. Non-Functional Requirements

### 5.1 Performance

- **NFR-5.1.1:** Python engine: < 50ms per generation on 100x100 grid.
- **NFR-5.1.2:** Bridge round-trip (conversion + computation): < 100ms per
  generation on 100x100 grid.
- **NFR-5.1.3:** Display render: < 100ms for full 50x50 grid re-plot.
- **NFR-5.1.4:** Combined: sustain 10 steps/sec on 50x50 without lag.
- **NFR-5.1.5:** Shiny UI remains responsive during simulation.

### 5.2 Compatibility

- **NFR-5.2.1:** R 4.1+, Python 3.10+, reticulate 1.28+, shiny 1.7+.
- **NFR-5.2.2:** macOS and Linux. Windows best-effort.

### 5.3 Code Quality

- **NFR-5.3.1:** Python: pyright basic, ruff default rules.
- **NFR-5.3.2:** R: lintr default linters.
- **NFR-5.3.3:** Python engine tests (pytest): >= 90% line coverage.
- **NFR-5.3.4:** Bridge tests (testthat, requires reticulate + Python):
  verify conversion correctness and Python invocation.
- **NFR-5.3.5:** GUI (display.R) excluded from coverage requirements.

---

## 6. Command-Line Interface

- **FR-6.1:** Launch via `Rscript inst/run_gol.R`.
- **FR-6.2:** Optional arguments:

  | Argument    | Type | Default | Description                    |
  |-------------|------|---------|--------------------------------|
  | `--width`   | int  | 50      | Grid columns                   |
  | `--height`  | int  | 50      | Grid rows                      |
  | `--speed`   | int  | 10      | Initial speed (1-60 steps/sec) |
  | `--pattern` | str  | (none)  | Preset pattern to load         |

- **FR-6.3:** `--pattern` loads via `bridge_place_pattern()` at startup.
- **FR-6.4:** Invalid pattern name: print valid names, exit with status 1.
- **FR-6.5:** Width or height < 3: error message, exit with status 1.
- **FR-6.6:** Speed outside 1-60: error message, exit with status 1.

**Acceptance Criteria (CLI):**
- AC-6.A: `Rscript inst/run_gol.R --width 80 --height 60` opens 80x60
  grid.
- AC-6.B: `Rscript inst/run_gol.R --pattern glider` opens with centered
  glider.
- AC-6.C: `Rscript inst/run_gol.R --pattern invalid_name` errors and exits.

---

## 7. Data Characteristics

- Grid: 3x3 minimum, 50x50 default, 2,500 cells at default.
- Python representation: list of lists of bool, 0-based indexing.
- R representation: logical matrix, 1-based indexing.
- Index mapping: Python[i][j] = R[i+1, j+1].
- Speed: 1-60 steps/sec (1000ms-16.7ms interval), default 10 (100ms).
- Bridge overhead included in tick scheduling.

---

## 8. Target Blueprint Units

1. **Python Engine** (`engine.py`) -- Language: Python. Grid creation,
   neighbor counting, step function, pattern definitions, pattern
   placement. Tested standalone with pytest.
2. **R Bridge** (`R/bridge.R`) -- Language: R. reticulate integration,
   Python engine loading, R API for all Python functions, data conversion.
   Tested with testthat (requires reticulate + Python).
3. **R Display** (`R/display.R`) -- Language: R. Plain Shiny app (ui +
   server), plot rendering, controls, slider, counter, pattern dropdown.
   Consumes bridge API only.
4. **R Main** (`R/main.R` + `inst/run_gol.R`) -- Language: R. Entry point,
   CLI argument parsing, bridge init, Shiny app launch.

---

## 9. Out of Scope

- Save/load grid state to files
- Drag-to-paint (click toggle only)
- Zoom, pan, resize, custom colors
- Pattern editor, undo/redo
- Network/multiplayer
- Statistics beyond generation counter
- golem or rhino framework -- this is a plain Shiny app
- R package structure (DESCRIPTION/NAMESPACE) -- R code is scripts
- Python-to-R callbacks (data flows R-to-Python-to-R only)
- tkinter or any Python-based GUI

---

## 10. Glossary

| Term               | Definition                                            |
|--------------------|-------------------------------------------------------|
| B3/S23             | Birth/3 neighbors, Survival/2-3 neighbors             |
| Moore neighborhood | 8 cells surrounding a given cell                      |
| Toroidal grid      | Grid with opposite edges connected                    |
| reticulate         | R package for calling Python functions and exchanging data |
| Bridge             | R module mediating R-Python communication             |
| Logical matrix     | R matrix where every element is TRUE or FALSE         |
| Shiny              | R web application framework for interactive apps      |
| Reactive value     | Shiny object that triggers UI updates on change       |

---

*End of stakeholder specification.*
