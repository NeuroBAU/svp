# Stakeholder Specification: Conway's Game of Life (R / Terminal)

**Project:** gol-r
**Archetype:** B (r_project)
**Version:** 1.0
**Date:** 2026-03-29

---

## 1. Overview

An R package implementing Conway's Game of Life with a terminal-based
interactive interface. The package provides a console display using cat()
to render the grid, an interactive command loop for controlling the
simulation, and preset patterns. The simulation uses the standard B3/S23
rule set on a toroidal (wraparound) grid. The package follows standard R
package structure (DESCRIPTION, NAMESPACE, R/ directory) and uses testthat
for testing.

---

## 2. Definitions

- **Cell:** A single position on the grid. A cell is either alive or dead.
- **Generation:** One discrete time step of the simulation. Each generation
  applies the B3/S23 rules simultaneously to all cells.
- **B3/S23 rules:** A dead cell with exactly 3 alive neighbors becomes alive
  (birth). An alive cell with 2 or 3 alive neighbors stays alive (survival).
  All other alive cells die.
- **Neighbor:** Each cell has exactly 8 neighbors (Moore neighborhood):
  the cells horizontally, vertically, and diagonally adjacent.
- **Toroidal grid:** The grid wraps around on all edges. The right edge
  connects to the left edge; the top edge connects to the bottom edge.
- **Preset pattern:** A named initial configuration of alive cells that
  can be loaded onto the grid.
- **Interactive mode:** A read-eval-print loop in the R console where the
  user types commands to control the simulation.

---

## 3. Functional Requirements

### 3.1 Grid Display

- **FR-3.1.1:** The package shall display the grid to the terminal using
  cat() to print each row as a string of characters.
- **FR-3.1.2:** Alive cells shall be displayed as "#". Dead cells shall be
  displayed as ".".
- **FR-3.1.3:** Each row of the grid shall be printed as a single line of
  characters with no spaces between cell characters.
- **FR-3.1.4:** The default grid size shall be 30 columns by 30 rows.
- **FR-3.1.5:** The grid size shall be configurable at startup (see
  Section 6).
- **FR-3.1.6:** Before printing the grid, the display function shall
  print a blank line separator followed by the generation counter line
  (see FR-3.5), then the grid rows.
- **FR-3.1.7:** After printing the grid, the display function shall print
  a command prompt line: "> " (greater-than followed by a space).

**Acceptance Criteria (Grid Display):**
- AC-3.1.A: On startup with default settings, a 30x30 grid is printed to the
  terminal with all cells dead (all ".") and the generation counter showing 0.
- AC-3.1.B: When the grid contains alive cells, those cells appear as "#"
  characters in the terminal output.
- AC-3.1.C: Each row is exactly 30 characters wide (at default size) with no
  trailing spaces beyond the cell characters.

### 3.2 Simulation Engine

- **FR-3.2.1:** The simulation shall implement Conway's Game of Life with
  the B3/S23 rule set as defined in Section 2.
- **FR-3.2.2:** All cell state transitions within a single generation shall
  be computed simultaneously. No cell's new state shall influence another
  cell's computation within the same generation.
- **FR-3.2.3:** Neighbor counting shall use the Moore neighborhood (8
  neighbors per cell).
- **FR-3.2.4:** The grid shall use toroidal (wraparound) boundary
  conditions. A cell on the left edge considers cells on the right edge
  as neighbors, and similarly for top/bottom edges.
- **FR-3.2.5:** The grid shall be represented as an R logical matrix where
  TRUE represents an alive cell and FALSE represents a dead cell.
- **FR-3.2.6:** The step function shall accept a grid matrix and return a
  new grid matrix representing the next generation. The input matrix shall
  not be modified.

**Acceptance Criteria (Simulation Engine):**
- AC-3.2.A: A blinker oscillates between horizontal and vertical
  orientations every generation.
- AC-3.2.B: A block remains unchanged across generations.
- AC-3.2.C: A glider translates diagonally across the grid, wrapping
  around edges via toroidal boundary.
- AC-3.2.D: A step on an all-dead grid returns an all-dead grid.
- AC-3.2.E: The input grid matrix is not modified by the step function
  (no side effects).

### 3.3 Interactive Commands

- **FR-3.3.1:** The package shall provide an interactive mode where the
  user enters commands at the "> " prompt.
- **FR-3.3.2:** Commands shall be case-insensitive. Leading and trailing
  whitespace shall be trimmed before parsing.
- **FR-3.3.3:** The following commands shall be supported:

  | Command         | Description                                          |
  |-----------------|------------------------------------------------------|
  | `step`          | Advance the simulation by exactly 1 generation       |
  | `step N`        | Advance the simulation by exactly N generations       |
  | `run N`         | Advance N generations, displaying the grid after each |
  | `reset`         | Set all cells to dead, reset generation counter to 0  |
  | `load PATTERN`  | Clear grid, load named pattern centered, reset counter|
  | `quit`          | Exit the interactive loop                             |
  | `help`          | Print a summary of available commands                 |

- **FR-3.3.4:** The `step` command (no argument) shall advance exactly 1
  generation and display the resulting grid.
- **FR-3.3.5:** The `step N` command shall advance exactly N generations
  and display the resulting grid once (the final state). N must be a
  positive integer.
- **FR-3.3.6:** The `run N` command shall advance N generations one at a
  time, displaying the grid after each generation. Between each generation,
  the function shall call Sys.sleep() with a configurable delay (default
  0.1 seconds) to create an animation effect. N must be a positive integer.
- **FR-3.3.7:** The `reset` command shall set all cells to dead, reset the
  generation counter to 0, and display the cleared grid.
- **FR-3.3.8:** The `load PATTERN` command shall clear the grid, place the
  named pattern centered on the grid, reset the generation counter to 0,
  and display the resulting grid. PATTERN is matched case-insensitively.
- **FR-3.3.9:** The `quit` command shall exit the interactive loop and
  return control to the R console. The function shall return the final
  grid state invisibly.
- **FR-3.3.10:** The `help` command shall print a list of all commands
  with brief descriptions.
- **FR-3.3.11:** If an unrecognized command is entered, the package shall
  print "Unknown command. Type 'help' for available commands." and
  redisplay the prompt.
- **FR-3.3.12:** If `step N` or `run N` is given a non-positive or
  non-integer argument, the package shall print an error message and
  redisplay the prompt without modifying the grid.
- **FR-3.3.13:** If `load PATTERN` is given an unrecognized pattern name,
  the package shall print an error message listing valid pattern names
  and redisplay the prompt without modifying the grid.

**Acceptance Criteria (Interactive Commands):**
- AC-3.3.A: Typing "step" advances one generation. The generation counter
  increments by 1.
- AC-3.3.B: Typing "step 5" advances 5 generations. The generation counter
  increments by 5. The grid is displayed once showing the final state.
- AC-3.3.C: Typing "run 10" displays the grid 10 times (once per
  generation) with a visible delay between frames.
- AC-3.3.D: Typing "reset" clears the grid and resets the counter to 0.
- AC-3.3.E: Typing "load glider" places a glider centered on the grid.
- AC-3.3.F: Typing "quit" exits the interactive loop.
- AC-3.3.G: Typing "STEP" (uppercase) is treated the same as "step".
- AC-3.3.H: Typing "foo" prints the unknown command message.

### 3.4 Generation Counter

- **FR-3.4.1:** The package shall maintain a generation counter tracking
  the number of generations elapsed since the last reset or load.
- **FR-3.4.2:** The counter shall start at 0 on startup and after each
  reset or load command.
- **FR-3.4.3:** The counter shall increment by 1 each time a generation
  is computed.
- **FR-3.4.4:** The counter shall be displayed above the grid, formatted
  as "Generation: N" where N is the current count.

**Acceptance Criteria (Generation Counter):**
- AC-3.4.A: The counter reads "Generation: 0" on startup.
- AC-3.4.B: After typing "step" three times, the counter reads
  "Generation: 3".
- AC-3.4.C: Typing "reset" returns the counter to "Generation: 0".

### 3.5 Preset Patterns

- **FR-3.5.1:** The package shall provide a function that returns a named
  list of preset patterns. Each element is a two-column matrix of (row,
  column) offsets for alive cells, with (1, 1) as the pattern's top-left
  corner (using R's 1-based indexing).
- **FR-3.5.2:** The following preset patterns shall be available:

  | Name        | Type        | Bounding Box | Description                         |
  |-------------|-------------|--------------|-------------------------------------|
  | blinker     | Oscillator  | 1x3          | Period-2 oscillator                 |
  | block       | Still life  | 2x2          | Stable 2x2 square                  |
  | beacon      | Oscillator  | 4x4          | Period-2 oscillator                 |
  | glider      | Spaceship   | 3x3          | Travels diagonally                  |
  | pulsar      | Oscillator  | 13x13        | Period-3 oscillator                 |

- **FR-3.5.3:** When placing a pattern, it shall be centered on the grid.
  Centering shall compute the row offset as
  floor((nrow - pattern_height) / 2) + 1 and the column offset as
  floor((ncol - pattern_width) / 2) + 1.
- **FR-3.5.4:** When placing a pattern, the grid shall first be cleared
  (all cells set to dead). Then the pattern cells shall be set to alive
  at their offset positions.
- **FR-3.5.5:** If the grid is smaller than the pattern bounding box,
  the pattern shall still be placed with cells wrapping via toroidal
  arithmetic (modular indexing). A warning shall be issued via warning().

**Acceptance Criteria (Preset Patterns):**
- AC-3.5.A: Loading "blinker" clears the grid, places a 3-cell horizontal
  line in the center, and resets the generation counter.
- AC-3.5.B: All five patterns are loadable via the "load" command.
- AC-3.5.C: Loading a pattern on a very small grid (e.g., 5x5) for pulsar
  issues a warning and still places cells using wraparound.

---

## 4. Package Structure

### 4.1 R Package Layout

- **FR-4.1.1:** The package shall follow standard R package structure:
  - `DESCRIPTION` file with package metadata
  - `NAMESPACE` file with exports
  - `R/` directory containing R source files
  - `tests/` directory containing testthat tests
  - `man/` directory for documentation (may be generated by roxygen2)

- **FR-4.1.2:** The package name shall be `golr`.

- **FR-4.1.3:** The package shall export the following functions:
  - `create_grid(rows, cols)` -- create an empty grid matrix
  - `step_grid(grid)` -- compute the next generation
  - `count_neighbors(grid)` -- count alive neighbors for all cells
  - `get_patterns()` -- return the named list of preset patterns
  - `place_pattern(grid, pattern_name)` -- place a pattern centered on grid
  - `display_grid(grid, generation)` -- print grid to terminal
  - `run_game(rows, cols, pattern, delay)` -- start interactive mode

- **FR-4.1.4:** The `run_game()` function shall be the primary entry point,
  launching the interactive command loop.

**Acceptance Criteria (Package Structure):**
- AC-4.1.A: The package passes `R CMD check` with no errors.
- AC-4.1.B: After `library(golr)`, calling `run_game()` starts the
  interactive loop with a 30x30 empty grid.
- AC-4.1.C: All functions listed in FR-4.1.3 are accessible after
  loading the package.

---

## 5. Non-Functional Requirements

### 5.1 Performance

- **NFR-5.1.1:** The simulation engine shall compute one generation of a
  100x100 grid in under 50 milliseconds.
- **NFR-5.1.2:** The display function shall render a 30x30 grid to the
  terminal in under 10 milliseconds.
- **NFR-5.1.3:** The `run` command shall sustain 10 steps per second on a
  30x30 grid at default delay without visible lag.

### 5.2 Compatibility

- **NFR-5.2.1:** The package shall be compatible with R 4.1.0 or later.
- **NFR-5.2.2:** The package shall use only base R and recommended packages.
  No CRAN dependencies shall be required at runtime.
- **NFR-5.2.3:** Test dependencies (testthat) and quality tools (lintr,
  styler) are development-only dependencies and shall not be required for
  runtime use.
- **NFR-5.2.4:** The package shall run on macOS, Linux, and Windows
  without modification.

### 5.3 Code Quality

- **NFR-5.3.1:** The package shall pass lintr checks using the default
  linters.
- **NFR-5.3.2:** The package source shall be formatted with styler.
- **NFR-5.3.3:** Unit tests shall achieve at minimum 90% line coverage on
  the simulation engine (step_grid, count_neighbors) and pattern library
  (get_patterns, place_pattern). The interactive loop (run_game) is
  excluded from coverage requirements.
- **NFR-5.3.4:** All exported functions shall have roxygen2 documentation
  with @param, @return, and @examples tags.

---

## 6. Command-Line Interface

- **FR-6.1:** The package shall include a script `inst/run_gol.R` that
  can be executed via `Rscript inst/run_gol.R` to launch the game.
- **FR-6.2:** The script shall accept the following optional command-line
  arguments via commandArgs():

  | Argument      | Type | Default | Description                        |
  |---------------|------|---------|------------------------------------|
  | `--rows`      | int  | 30      | Number of rows in the grid         |
  | `--cols`      | int  | 30      | Number of columns in the grid      |
  | `--pattern`   | str  | (none)  | Name of preset pattern to load     |
  | `--delay`     | num  | 0.1     | Delay in seconds between frames    |

- **FR-6.3:** If `--pattern` is provided, the named pattern shall be loaded
  and centered on the grid at startup.
- **FR-6.4:** If an invalid pattern name is provided, the script shall
  print an error message listing valid pattern names and exit with
  status 1.
- **FR-6.5:** If `--rows` or `--cols` is less than 3, the script shall
  print an error message and exit with status 1.
- **FR-6.6:** If `--delay` is not a positive number, the script shall
  print an error message and exit with status 1.

**Acceptance Criteria (CLI):**
- AC-6.A: Running `Rscript inst/run_gol.R --rows 20 --cols 40` starts the
  game with a 20x40 grid.
- AC-6.B: Running `Rscript inst/run_gol.R --pattern glider` starts with a
  glider centered on the default 30x30 grid.
- AC-6.C: Running `Rscript inst/run_gol.R --pattern invalid_name` prints
  an error listing valid names and exits with status 1.

---

## 7. Data Characteristics

### 7.1 Grid

- Minimum grid size: 3x3
- Maximum grid size: no hard limit, but performance targets (Section 5.1)
  are specified for 100x100.
- Default grid size: 30x30
- Total cells at default: 900
- Total cells at performance target: 10,000
- Cell representation: logical matrix (TRUE = alive, FALSE = dead)
- R matrices use 1-based indexing; row 1 is the top row, column 1 is the
  leftmost column.

### 7.2 Pattern Data

Each preset pattern is defined as a name and a two-column matrix of (row,
column) coordinate pairs relative to the pattern's top-left corner, using
1-based indexing.

| Pattern   | Cell Count | Bounding Box (rows x cols) |
|-----------|------------|---------------------------|
| blinker   | 3          | 1 x 3                     |
| block     | 4          | 2 x 2                     |
| beacon    | 6          | 4 x 4                     |
| glider    | 5          | 3 x 3                     |
| pulsar    | 48         | 13 x 13                   |

### 7.3 Timing

- Default delay between frames in `run` command: 0.1 seconds
- Configurable via `--delay` argument and the `delay` parameter of
  `run_game()`.

---

## 8. Target Blueprint Units

The implementation shall be organized into four units for the SVP
blueprint:

1. **Engine** -- Grid matrix creation, neighbor counting, step function.
   Files: `R/engine.R`
2. **Patterns** -- Preset pattern definitions, pattern placement function.
   Files: `R/patterns.R`
3. **Display** -- Terminal grid printer, command parser, interactive loop.
   Files: `R/display.R`
4. **Main** -- Entry point script, CLI argument parsing, package exports.
   Files: `R/main.R`, `inst/run_gol.R`

---

## 9. Out of Scope

The following features are explicitly excluded from this specification:

- Shiny or any GUI-based interface
- Saving/loading grid state to/from files
- Custom color themes or ANSI color output
- Editing or creating new patterns within the application
- Network or multiplayer features
- Undo/redo
- Population count or other statistics beyond the generation counter
- Grid resizing after startup
- Continuous (non-step) auto-run without explicit generation count
- Gosper Glider Gun or other large patterns (kept to 5 compact patterns)

---

## 10. Glossary

| Term             | Definition                                              |
|------------------|---------------------------------------------------------|
| B3/S23           | Birth with 3 neighbors, Survival with 2 or 3 neighbors |
| Moore neighborhood | The 8 cells surrounding a given cell                 |
| Toroidal grid    | A grid where opposite edges are connected               |
| Still life       | A pattern that does not change from one generation to the next |
| Oscillator       | A pattern that returns to its initial state after a fixed number of generations |
| Spaceship        | A pattern that translates across the grid               |
| Logical matrix   | An R matrix where every element is TRUE or FALSE        |

---

*End of stakeholder specification.*
