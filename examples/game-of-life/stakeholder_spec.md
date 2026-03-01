# Game of Life -- Stakeholder Specification

## Overview

This project implements **Conway's Game of Life**, a cellular automaton devised
by the British mathematician John Horton Conway in 1970. The Game of Life is a
zero-player game: its evolution is determined by its initial state, requiring no
further input from the human.

## Requirements

### Core Simulation

1. The simulation operates on a two-dimensional grid of cells.
2. Each cell is either **alive** or **dead**.
3. The grid wraps around (toroidal topology) so that edges connect.
4. At each time step, the following rules apply simultaneously to every cell:
   - A live cell with fewer than 2 live neighbors dies (underpopulation).
   - A live cell with 2 or 3 live neighbors survives.
   - A live cell with more than 3 live neighbors dies (overpopulation).
   - A dead cell with exactly 3 live neighbors becomes alive (reproduction).

### Grid Management

5. The grid must support arbitrary rectangular dimensions (minimum 3x3).
6. Users can set the initial state by specifying live cell coordinates.
7. The simulation must support loading initial patterns from a simple text format.

### Display

8. The simulation must provide a text-based display of the grid state.
9. Live cells are displayed as `#` and dead cells as `.`.
10. The display must include a generation counter.

### Simulation Control

11. The simulation must support stepping forward one generation at a time.
12. The simulation must support running for a specified number of generations.
13. The simulation must detect when the grid reaches a stable state (no changes)
    and report this to the user.

### Well-Known Patterns

14. The implementation must include built-in patterns:
    - **Block** (still life, 2x2)
    - **Blinker** (oscillator, period 2)
    - **Glider** (spaceship)

## Non-Functional Requirements

- The implementation must be in pure Python (no external dependencies).
- The code must be well-documented with docstrings.
- All public functions must have type annotations.
