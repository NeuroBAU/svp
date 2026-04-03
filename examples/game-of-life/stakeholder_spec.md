# Stakeholder Specification: Conway's Game of Life (Python/tkinter)

**Project:** gol-python
**Archetype:** A (python_project)
**Version:** 1.0
**Date:** 2026-03-29

---

## 1. Overview

A desktop application implementing Conway's Game of Life using Python and
tkinter. The application provides an interactive grid where users can create
and observe cellular automaton patterns, control simulation speed, and load
preset patterns. The simulation uses the standard B3/S23 rule set on a
toroidal (wraparound) grid.

---

## 2. Definitions

- **Cell:** A single square on the grid. A cell is either alive or dead.
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

---

## 3. Functional Requirements

### 3.1 Grid Display

- **FR-3.1.1:** The application shall display a two-dimensional grid of cells
  rendered on a tkinter Canvas widget.
- **FR-3.1.2:** Each cell shall be rendered as a filled square. Alive cells
  shall be black (#000000). Dead cells shall be white (#FFFFFF).
- **FR-3.1.3:** Grid lines shall be drawn between cells in gray (#CCCCCC).
- **FR-3.1.4:** The default grid size shall be 50 columns by 50 rows.
- **FR-3.1.5:** The grid size shall be configurable at application startup
  (see Section 6).
- **FR-3.1.6:** The canvas shall size itself to fit the grid. Each cell shall
  be rendered at a fixed pixel size of 12x12 pixels (including the 1-pixel
  grid line on the right and bottom edges).

**Acceptance Criteria (Grid Display):**
- AC-3.1.A: On startup with default settings, a 50x50 grid is visible with
  all cells dead (white) and gray grid lines separating cells.
- AC-3.1.B: When the grid contains alive cells, those cells appear as black
  squares within the grid.

### 3.2 Cell Interaction

- **FR-3.2.1:** The user shall be able to click on any cell in the grid to
  toggle its state between alive and dead.
- **FR-3.2.2:** Cell toggling shall work when the simulation is stopped.
- **FR-3.2.3:** Cell toggling shall work when the simulation is running.
- **FR-3.2.4:** The visual state of the clicked cell shall update immediately
  upon click.

**Acceptance Criteria (Cell Interaction):**
- AC-3.2.A: Clicking a dead cell turns it alive (black). Clicking an alive
  cell turns it dead (white). The change is visible immediately.
- AC-3.2.B: Cell toggling functions both when the simulation is running and
  when it is stopped.

### 3.3 Simulation Controls

- **FR-3.3.1:** The application shall provide a **Start** button that begins
  continuous simulation, advancing one generation per tick.
- **FR-3.3.2:** The application shall provide a **Stop** button that pauses
  the simulation. The grid state is preserved.
- **FR-3.3.3:** The application shall provide a **Step** button that advances
  the simulation by exactly one generation and stops.
- **FR-3.3.4:** The application shall provide a **Reset** button that sets
  all cells to dead, resets the generation counter to 0, and stops the
  simulation if it is running.
- **FR-3.3.5:** When the simulation is running, the Start button shall be
  disabled (or visually indicate that the simulation is already running).
  When the simulation is stopped, the Stop button shall be disabled (or
  visually indicate that the simulation is already stopped).

**Acceptance Criteria (Simulation Controls):**
- AC-3.3.A: Pressing Start causes the grid to advance automatically.
  Pressing Stop halts advancement. The grid retains its state after Stop.
- AC-3.3.B: Pressing Step advances exactly one generation and does not
  continue automatically.
- AC-3.3.C: Pressing Reset clears the grid entirely and resets the
  generation counter to 0.
- AC-3.3.D: Start and Stop buttons reflect the current simulation state.

### 3.4 Speed Control

- **FR-3.4.1:** The application shall provide a horizontal slider (tkinter
  Scale widget) to control simulation speed.
- **FR-3.4.2:** The slider range shall be 1 to 60 steps per second.
- **FR-3.4.3:** The default slider position shall be 10 steps per second.
- **FR-3.4.4:** Changing the slider while the simulation is running shall
  take effect immediately (the next tick uses the new interval).
- **FR-3.4.5:** The current speed value shall be displayed as a label
  adjacent to the slider, showing the value in steps per second.

**Acceptance Criteria (Speed Control):**
- AC-3.4.A: Moving the slider to 1 results in approximately 1 generation
  per second. Moving it to 60 results in approximately 60 generations
  per second.
- AC-3.4.B: Changing the slider mid-simulation adjusts speed without
  stopping or restarting the simulation.

### 3.5 Generation Counter

- **FR-3.5.1:** The application shall display a generation counter showing
  the number of generations elapsed since the last reset.
- **FR-3.5.2:** The counter shall start at 0 on application startup and
  after each reset.
- **FR-3.5.3:** The counter shall increment by 1 each time a generation
  is computed (whether via Start or Step).
- **FR-3.5.4:** The counter shall be displayed as a label in the control
  area, formatted as "Generation: N" where N is the current count.

**Acceptance Criteria (Generation Counter):**
- AC-3.5.A: The counter reads "Generation: 0" on startup.
- AC-3.5.B: After pressing Step three times, the counter reads
  "Generation: 3".
- AC-3.5.C: Pressing Reset returns the counter to "Generation: 0".

### 3.6 Preset Patterns

- **FR-3.6.1:** The application shall provide a mechanism to load preset
  patterns onto the grid. This shall be a dropdown menu (tkinter
  OptionMenu or Combobox) listing available patterns by name.
- **FR-3.6.2:** Selecting a preset pattern shall clear the grid, place
  the pattern centered on the grid, reset the generation counter to 0,
  and stop the simulation if running.
- **FR-3.6.3:** The following preset patterns shall be available:

  | Name        | Type        | Bounding Box | Description                         |
  |-------------|-------------|--------------|-------------------------------------|
  | Blinker     | Oscillator  | 1x3          | Period-2 oscillator                 |
  | Block       | Still life  | 2x2          | Stable 2x2 square                  |
  | Beacon      | Oscillator  | 4x4          | Period-2 oscillator                 |
  | Glider      | Spaceship   | 3x3          | Travels diagonally                  |
  | Pulsar      | Oscillator  | 13x13        | Period-3 oscillator                 |
  | Gosper Glider Gun | Gun  | 36x9         | Emits a glider every 30 generations|

- **FR-3.6.4:** Each pattern shall be defined as a list of relative (row,
  column) offsets for alive cells, with (0, 0) as the pattern's top-left
  corner.
- **FR-3.6.5:** When placing a pattern, it shall be centered on the grid.
  If the grid is smaller than the pattern bounding box, the pattern shall
  still be placed (cells wrapping via toroidal rules) and a warning shall
  be printed to the console.

**Acceptance Criteria (Preset Patterns):**
- AC-3.6.A: Selecting "Blinker" from the dropdown clears the grid, places
  a 3-cell vertical or horizontal line in the center, and resets the
  generation counter.
- AC-3.6.B: Selecting "Gosper Glider Gun" places the gun pattern. After
  pressing Start, gliders are emitted approximately every 30 generations.
- AC-3.6.C: All six patterns are present in the dropdown and load
  correctly.

### 3.7 Simulation Rules

- **FR-3.7.1:** The simulation shall implement Conway's Game of Life with
  the B3/S23 rule set as defined in Section 2.
- **FR-3.7.2:** All cell state transitions within a single generation shall
  be computed simultaneously. No cell's new state shall influence another
  cell's computation within the same generation.
- **FR-3.7.3:** Neighbor counting shall use the Moore neighborhood (8
  neighbors per cell).
- **FR-3.7.4:** The grid shall use toroidal (wraparound) boundary
  conditions. A cell on the left edge considers cells on the right edge
  as neighbors, and similarly for top/bottom edges.

**Acceptance Criteria (Simulation Rules):**
- AC-3.7.A: A blinker oscillates between horizontal and vertical
  orientations every generation.
- AC-3.7.B: A block remains unchanged across generations.
- AC-3.7.C: A glider translates diagonally across the grid, wrapping
  around edges via toroidal boundary.
- AC-3.7.D: A Gosper Glider Gun produces its first glider within 30
  generations.

---

## 4. User Interface Layout

### 4.1 Window Structure

- **FR-4.1.1:** The application window title shall be "Conway's Game of Life".
- **FR-4.1.2:** The window shall contain two regions:
  - **Grid area:** The canvas displaying the cell grid, occupying the
    majority of the window.
  - **Control panel:** A horizontal bar below the grid containing all
    controls.
- **FR-4.1.3:** The control panel shall contain, from left to right:
  - Start button
  - Stop button
  - Step button
  - Reset button
  - Speed slider with label
  - Generation counter label
  - Pattern dropdown
- **FR-4.1.4:** The window shall not be resizable. Its size shall be
  determined by the grid dimensions and the control panel height.

**Acceptance Criteria (UI Layout):**
- AC-4.1.A: On startup, the window displays a grid above a row of controls.
  All controls listed in FR-4.1.3 are visible and labeled.
- AC-4.1.B: The window title bar reads "Conway's Game of Life".

---

## 5. Non-Functional Requirements

### 5.1 Performance

- **NFR-5.1.1:** The simulation engine shall compute one generation of a
  100x100 grid in under 33 milliseconds (to support 30 fps rendering).
- **NFR-5.1.2:** The display shall render a full 100x100 grid update in
  under 33 milliseconds.
- **NFR-5.1.3:** Combined (compute + render), the application shall sustain
  30 steps per second on a 100x100 grid without visible lag or dropped
  frames on a modern desktop machine.
- **NFR-5.1.4:** The application shall remain responsive to user input
  (clicks, button presses) while the simulation is running.

### 5.2 Compatibility

- **NFR-5.2.1:** The application shall run on Python 3.10 or later.
- **NFR-5.2.2:** The application shall use only the Python standard library
  (tkinter is included in the standard library on most distributions).
- **NFR-5.2.3:** The application shall run on macOS, Linux, and Windows
  without modification.

### 5.3 Code Quality

- **NFR-5.3.1:** The application shall pass pyright type checking with no
  errors at basic strictness.
- **NFR-5.3.2:** The application shall pass ruff linting with default rules.
- **NFR-5.3.3:** Unit tests shall achieve at minimum 90% line coverage on
  the simulation engine and pattern library (GUI components are excluded
  from coverage requirements).

---

## 6. Command-Line Interface

- **FR-6.1:** The application shall accept the following optional
  command-line arguments:

  | Argument      | Type | Default | Description                        |
  |---------------|------|---------|------------------------------------|
  | `--width`     | int  | 50      | Number of columns in the grid      |
  | `--height`    | int  | 50      | Number of rows in the grid         |
  | `--speed`     | int  | 10      | Initial simulation speed (1-60)    |
  | `--pattern`   | str  | (none)  | Name of preset pattern to load     |

- **FR-6.2:** If `--pattern` is provided, the named pattern shall be loaded
  and centered on the grid at startup (same behavior as selecting from the
  dropdown).
- **FR-6.3:** If an invalid pattern name is provided, the application shall
  print an error message listing valid pattern names and exit with code 1.
- **FR-6.4:** If `--width` or `--height` is less than 3, the application
  shall print an error message and exit with code 1.
- **FR-6.5:** If `--speed` is outside the range 1-60, the application shall
  print an error message and exit with code 1.

**Acceptance Criteria (CLI):**
- AC-6.A: Running `python main.py --width 80 --height 60` opens a window
  with an 80x60 grid.
- AC-6.B: Running `python main.py --pattern glider` opens with a glider
  centered on the default 50x50 grid.
- AC-6.C: Running `python main.py --pattern invalid_name` prints an error
  and exits with code 1.

---

## 7. Data Characteristics

### 7.1 Grid

- Minimum grid size: 3x3
- Maximum grid size: no hard limit, but performance targets (Section 5.1)
  are specified for 100x100.
- Default grid size: 50x50
- Total cells at default: 2,500
- Total cells at performance target: 10,000
- Cell state: boolean (alive or dead)

### 7.2 Pattern Data

Each preset pattern is defined as a name and a list of (row, column)
coordinate pairs relative to the pattern's top-left corner.

| Pattern           | Cell Count | Bounding Box (rows x cols) |
|-------------------|------------|---------------------------|
| Blinker           | 3          | 1 x 3                    |
| Block             | 4          | 2 x 2                    |
| Beacon            | 6          | 4 x 4                    |
| Glider            | 5          | 3 x 3                    |
| Pulsar            | 48         | 13 x 13                  |
| Gosper Glider Gun | 36         | 9 x 36                   |

### 7.3 Timing

- Speed range: 1 to 60 steps per second
- Corresponding tick interval: 1000ms to ~16.7ms
- Default speed: 10 steps per second (100ms interval)

---

## 8. Out of Scope

The following features are explicitly excluded from this specification:

- Saving/loading grid state to/from files
- Drag-to-paint (only single-cell click toggling)
- Zoom or pan on the grid
- Custom color themes
- Editing or creating new patterns within the application
- Network or multiplayer features
- Undo/redo
- Statistics beyond the generation counter (population count, etc.)
- Grid resizing after startup

---

## 9. Glossary

| Term             | Definition                                              |
|------------------|---------------------------------------------------------|
| B3/S23           | Birth with 3 neighbors, Survival with 2 or 3 neighbors |
| Moore neighborhood | The 8 cells surrounding a given cell                 |
| Toroidal grid    | A grid where opposite edges are connected               |
| Still life       | A pattern that does not change from one generation to the next |
| Oscillator       | A pattern that returns to its initial state after a fixed number of generations |
| Spaceship        | A pattern that translates across the grid               |
| Gun              | A pattern that periodically emits spaceships            |

---

*End of stakeholder specification.*
