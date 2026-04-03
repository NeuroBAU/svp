# Stakeholder Specification: Conway's Game of Life (Python/R Mixed)

**Project:** gol-python-r
**Archetype:** D (mixed, Python primary / R secondary)
**Version:** 1.0
**Date:** 2026-03-29

---

## 1. Overview

A desktop application implementing Conway's Game of Life using Python for the
GUI and application layer, with the simulation engine implemented in R. Python
provides the tkinter-based graphical interface, entry point, and orchestration
logic. R provides the core computational engine (grid creation, neighbor
counting, generation stepping) using matrix operations. The two languages are
bridged by rpy2, which allows Python to call R functions directly and convert
data between Python lists and R matrices. The simulation uses the standard
B3/S23 rule set on a toroidal (wraparound) grid.

This project is a mixed-archetype test case for SVP 2.2, exercising
dual-language dispatch, cross-language bridge testing, and two-phase assembly
composition.

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
- **Bridge:** The rpy2-based layer translating between Python and R.

---

## 3. Functional Requirements

### 3.1 R Simulation Engine

The engine is implemented entirely in R and is the sole authority for grid
state computation. Python never computes GoL logic directly.

- **FR-3.1.1:** `create_grid(rows, cols)` -- returns a logical matrix with
  all cells FALSE (dead).
- **FR-3.1.2:** `count_neighbors(grid)` -- returns an integer matrix of
  alive-neighbor counts (0-8) per cell, using toroidal boundaries.
- **FR-3.1.3:** `step_grid(grid)` -- accepts a logical matrix, returns a new
  logical matrix for the next generation under B3/S23. Input is not modified.
  All transitions computed simultaneously.
- **FR-3.1.4:** `get_patterns()` -- returns a named list of preset patterns,
  each a two-column matrix of (row, col) offsets in 1-based indexing.
- **FR-3.1.5:** `place_pattern(grid, pattern_name)` -- clears grid, centers
  the named pattern, returns the result. Centering:
  row_offset = floor((nrow - height) / 2) + 1,
  col_offset = floor((ncol - width) / 2) + 1.
  If grid is smaller than pattern, wrap via modular indexing and issue
  warning().
- **FR-3.1.6:** Implemented in a single file `R/engine.R` using only base R.

**Acceptance Criteria (R Engine):**
- AC-3.1.A: `create_grid(50, 50)` returns a 50x50 logical matrix of FALSE.
- AC-3.1.B: Blinker oscillates, block is stable, glider translates with
  toroidal wrap -- all via `step_grid()`.
- AC-3.1.C: Input grid is not modified by `step_grid()`.
- AC-3.1.D: `get_patterns()` returns all six required patterns.

### 3.2 Python Bridge

The bridge translates between Python data structures and R objects and
manages the rpy2 connection.

- **FR-3.2.1:** Load `R/engine.R` into the embedded R session via rpy2.
- **FR-3.2.2:** `create_grid(rows, cols)` -- calls R function, converts
  returned logical matrix to Python list of lists of booleans (row-major).
- **FR-3.2.3:** `step_grid(grid)` -- converts Python grid to R logical
  matrix, calls R `step_grid()`, converts result back to Python.
- **FR-3.2.4:** `place_pattern(rows, cols, pattern_name)` -- calls R
  `create_grid()` then `place_pattern()`, returns Python list-of-lists.
- **FR-3.2.5:** `get_pattern_names()` -- calls R `get_patterns()`, returns
  Python list of name strings.
- **FR-3.2.6:** Conversion preserves dimensions exactly: (rows, cols) in R
  yields `rows` sublists of length `cols` in Python.
- **FR-3.2.7:** Conversion preserves cell states exactly. TRUE maps to True,
  FALSE to False. Round-trip is lossless.
- **FR-3.2.8:** If R engine file cannot be loaded, raise RuntimeError. If
  rpy2/R unavailable, raise ImportError. Both with descriptive messages.

**Acceptance Criteria (Bridge):**
- AC-3.2.A: `create_grid(50, 50)` returns 50 lists of 50 False values.
- AC-3.2.B: Round-tripped grid matches direct R engine output for known
  GoL states.
- AC-3.2.C: Dimensions and cell states preserved exactly through conversion.
- AC-3.2.D: Missing `R/engine.R` raises RuntimeError.

### 3.3 Python Display and Controls (tkinter)

The GUI matches the gol-python specification. Key requirements restated here;
refer to the gol-python stakeholder spec for full visual and interaction
details.

- **FR-3.3.1:** Canvas-rendered grid. Alive = black (#000000), dead = white
  (#FFFFFF), grid lines gray (#CCCCCC). Cell size 12x12 px. Default 50x50.
- **FR-3.3.2:** Click any cell to toggle alive/dead (running or stopped).
- **FR-3.3.3:** Start, Stop, Step, Reset buttons. Start/Stop reflect state.
  All simulation calls go through `bridge.step_grid()` or
  `bridge.create_grid()`.
- **FR-3.3.4:** Speed slider: 1-60 steps/sec, default 10. Label shows value.
  Changes take effect immediately.
- **FR-3.3.5:** Generation counter: "Generation: N", starts at 0, increments
  per step, resets on Reset or pattern load.
- **FR-3.3.6:** Pattern dropdown populated from `bridge.get_pattern_names()`.
  Selection calls `bridge.place_pattern()`, resets counter, stops simulation.
- **FR-3.3.7:** Window title "Conway's Game of Life". Not resizable. Grid
  area above control panel. Controls left-to-right: Start, Stop, Step,
  Reset, speed slider + label, generation label, pattern dropdown.

**Acceptance Criteria (Display and Controls):**
- AC-3.3.A: Startup shows 50x50 empty grid with controls visible.
- AC-3.3.B: Start advances via R engine; Stop halts; Step does one generation.
- AC-3.3.C: Reset clears grid and counter. Pattern selection loads correctly.

### 3.4 Preset Patterns

- **FR-3.4.1:** The following patterns shall be defined in the R engine:

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
gol-python-r/
  R/
    engine.R         # Pure R simulation engine
  bridge.py          # rpy2 integration, data conversion
  display.py         # tkinter GUI
  main.py            # Entry point, CLI, wiring
  environment.yml    # Conda environment
```

### 4.2 Language Boundaries

- **FR-4.2.1:** All GoL computation in R. Python contains no GoL logic.
- **FR-4.2.2:** All GUI/interaction in Python. R contains no display logic.
- **FR-4.2.3:** Only `bridge.py` imports rpy2. Display and main depend only
  on the bridge's Python API.
- **FR-4.2.4:** `R/engine.R` has no awareness of rpy2 or Python. Testable
  standalone in a pure R session.

### 4.3 Data Flow

Per-generation cycle:

1. Display holds grid as Python list-of-lists of booleans.
2. Display calls `bridge.step_grid(grid)`.
3. Bridge converts to R logical matrix, calls R `step_grid()`.
4. R computes next generation, returns new logical matrix.
5. Bridge converts back to Python list-of-lists.
6. Display redraws canvas.

- **FR-4.3.1:** Every step is a complete round-trip. No R objects cached
  across steps.
- **FR-4.3.2:** Cell toggling modifies the Python grid directly. The
  modified grid is passed to R on the next step call.

### 4.4 Environment

- **FR-4.4.1:** `environment.yml` defines conda environment `gol-python-r`
  with: Python >= 3.10, R >= 4.1, rpy2, tkinter.
- **FR-4.4.2:** No R packages beyond base R required at runtime. testthat
  is a dev-only dependency.

---

## 5. Non-Functional Requirements

### 5.1 Performance

- **NFR-5.1.1:** R engine: < 50ms per generation on 100x100 grid.
- **NFR-5.1.2:** Bridge round-trip (conversion + computation): < 100ms per
  generation on 100x100 grid.
- **NFR-5.1.3:** Display render: < 33ms for full 50x50 grid update.
- **NFR-5.1.4:** Combined: sustain 10 steps/sec on 50x50 without lag.
- **NFR-5.1.5:** UI remains responsive during simulation.

### 5.2 Compatibility

- **NFR-5.2.1:** Python 3.10+, R 4.1+, rpy2 3.5+.
- **NFR-5.2.2:** macOS and Linux. Windows best-effort.

### 5.3 Code Quality

- **NFR-5.3.1:** Python: pyright basic, ruff default rules.
- **NFR-5.3.2:** R: lintr default linters.
- **NFR-5.3.3:** R engine tests (testthat): >= 90% line coverage.
- **NFR-5.3.4:** Bridge tests (pytest, requires rpy2+R): verify conversion
  correctness and R invocation.
- **NFR-5.3.5:** GUI (display.py) excluded from coverage requirements.

---

## 6. Command-Line Interface

- **FR-6.1:** Launch via `python main.py`.
- **FR-6.2:** Optional arguments:

  | Argument    | Type | Default | Description                    |
  |-------------|------|---------|--------------------------------|
  | `--width`   | int  | 50      | Grid columns                   |
  | `--height`  | int  | 50      | Grid rows                      |
  | `--speed`   | int  | 10      | Initial speed (1-60 steps/sec) |
  | `--pattern` | str  | (none)  | Preset pattern to load         |

- **FR-6.3:** `--pattern` loads via `bridge.place_pattern()` at startup.
- **FR-6.4:** Invalid pattern name: print valid names, exit code 1.
- **FR-6.5:** Width or height < 3: error message, exit code 1.
- **FR-6.6:** Speed outside 1-60: error message, exit code 1.

**Acceptance Criteria (CLI):**
- AC-6.A: `python main.py --width 80 --height 60` opens 80x60 grid.
- AC-6.B: `python main.py --pattern glider` opens with centered glider.
- AC-6.C: `python main.py --pattern invalid_name` errors and exits.

---

## 7. Data Characteristics

- Grid: 3x3 minimum, 50x50 default, 2,500 cells at default.
- R representation: logical matrix, 1-based indexing.
- Python representation: list of lists of bool, 0-based indexing.
- Index mapping: R[i, j] = Python[i-1][j-1].
- Speed: 1-60 steps/sec (1000ms-16.7ms interval), default 10 (100ms).
- Bridge overhead included in tick scheduling.

---

## 8. Target Blueprint Units

1. **R Engine** (`R/engine.R`) -- Language: R. Grid creation, neighbor
   counting, step function, pattern definitions, pattern placement.
   Tested standalone with testthat.
2. **Python Bridge** (`bridge.py`) -- Language: Python. rpy2 integration,
   R engine loading, Python API for all R functions, data conversion.
   Tested with pytest (requires R + rpy2).
3. **Python Display** (`display.py`) -- Language: Python. tkinter GUI,
   canvas rendering, controls, slider, counter, pattern dropdown.
   Consumes bridge API only.
4. **Python Main** (`main.py`) -- Language: Python. Entry point, CLI
   argument parsing, bridge init, display wiring, main loop.

---

## 9. Out of Scope

- Save/load grid state to files
- Drag-to-paint (click toggle only)
- Zoom, pan, resize, custom colors
- Pattern editor, undo/redo
- Network/multiplayer
- Statistics beyond generation counter
- R package structure (DESCRIPTION/NAMESPACE) -- R code is a script
- Shiny or R-based GUI
- R-to-Python callbacks (data flows Python-to-R-to-Python only)

---

## 10. Glossary

| Term               | Definition                                            |
|--------------------|-------------------------------------------------------|
| B3/S23             | Birth/3 neighbors, Survival/2-3 neighbors             |
| Moore neighborhood | 8 cells surrounding a given cell                      |
| Toroidal grid      | Grid with opposite edges connected                    |
| rpy2               | Python package for calling R functions and exchanging data |
| Bridge             | Python module mediating Python-R communication        |
| Logical matrix     | R matrix where every element is TRUE or FALSE         |

---

*End of stakeholder specification.*
