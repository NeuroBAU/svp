# Game of Life -- Project Context

## Project Description

This project implements Conway's Game of Life as a demonstration of the SVP
(Stratified Verification Pipeline) build process. The Game of Life is a classic
cellular automaton that serves as an excellent example for test-driven
development because it has well-defined rules and easily verifiable behavior.

## Technical Context

- **Language:** Python 3.10+
- **Dependencies:** None (pure Python)
- **Test Framework:** pytest
- **Build System:** SVP (Stratified Verification Pipeline)

## Domain Knowledge

Conway's Game of Life operates on an infinite two-dimensional grid of cells.
Each cell can be in one of two states: alive or dead. The state of every cell
changes simultaneously based on the states of its eight neighbors according to
four simple rules:

1. **Underpopulation:** A live cell with fewer than 2 live neighbors dies.
2. **Survival:** A live cell with 2 or 3 live neighbors survives.
3. **Overpopulation:** A live cell with more than 3 live neighbors dies.
4. **Reproduction:** A dead cell with exactly 3 live neighbors becomes alive.

For this implementation, we use a finite grid with toroidal (wrapping) boundary
conditions, meaning the grid's edges connect to the opposite side.

## Key Patterns Used in Testing

- **Block:** A 2x2 square of live cells. This is a "still life" -- it does
  not change from one generation to the next.
- **Blinker:** Three cells in a row. This is a period-2 oscillator -- it
  alternates between horizontal and vertical orientations.
- **Glider:** A five-cell pattern that translates diagonally across the grid,
  repeating its shape every 4 generations.

## File Structure

```
src/
  unit_1/stub.py    # Grid implementation
  unit_2/stub.py    # Simulation implementation
  unit_3/stub.py    # Display and patterns
tests/
  test_unit_1.py    # Grid tests
  test_unit_2.py    # Simulation tests
  test_unit_3.py    # Display and patterns tests
```

## Notes for Development

- The grid uses 0-based indexing with (x, y) coordinates where x is the column
  and y is the row.
- All coordinate wrapping must use modular arithmetic to implement toroidal
  boundary conditions.
- When loading patterns, `#` represents alive cells and `.` represents dead
  cells. Rows are separated by newlines.
