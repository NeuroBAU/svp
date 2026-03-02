# Game of Life -- Blueprint

## Architecture Overview

The Game of Life implementation is decomposed into three units that handle grid
management, simulation rules, and display/control respectively.

## Unit 1: Grid

**Description:** Manages the two-dimensional grid data structure with toroidal
(wrapping) boundary conditions. Provides cell access, neighbor counting, and
pattern loading.

### Tier 2 — Signatures

```python
from typing import List, Set, Tuple

class Grid:
    def __init__(self, width: int, height: int) -> None: ...
    def get(self, x: int, y: int) -> bool: ...
    def set(self, x: int, y: int, alive: bool) -> None: ...
    def count_neighbors(self, x: int, y: int) -> int: ...
    def get_live_cells(self) -> Set[Tuple[int, int]]: ...
    def load_pattern(self, pattern: str, offset_x: int = 0, offset_y: int = 0) -> None: ...
    def clear(self) -> None: ...
    @property
    def dimensions(self) -> Tuple[int, int]: ...
```

### Contracts

- Grid dimensions must be at least 3x3; raise ValueError otherwise.
- Coordinates wrap around using modular arithmetic (toroidal topology).
- `count_neighbors` returns the count of live cells among the 8 adjacent cells.
- `load_pattern` parses a text pattern where `#` = alive, `.` = dead, newlines
  separate rows.

## Unit 2: Simulation

**Description:** Implements Conway's Game of Life rules and simulation stepping.
Applies the four rules simultaneously to produce the next generation.

### Tier 2 — Signatures

```python
from typing import Optional

class Simulation:
    def __init__(self, grid: "Grid") -> None: ...
    @property
    def generation(self) -> int: ...
    def step(self) -> bool: ...
    def run(self, generations: int) -> int: ...
    def is_stable(self) -> bool: ...
```

### Contracts

- `step()` applies all four rules simultaneously, increments generation counter,
  and returns True if the grid changed.
- `run(n)` calls step() up to n times, stopping early if stable. Returns the
  number of steps actually taken.
- `is_stable()` returns True if the last step produced no changes.

### Dependencies

- Unit 1 (Grid): Uses Grid for cell access and neighbor counting.

## Unit 3: Display and Patterns

**Description:** Provides text-based grid rendering and built-in pattern
definitions for well-known Game of Life configurations.

### Tier 2 — Signatures

```python
from typing import Dict

def render(grid: "Grid") -> str: ...
def render_with_info(grid: "Grid", generation: int) -> str: ...

PATTERNS: Dict[str, str]
# Must include at minimum: "block", "blinker", "glider"
```

### Contracts

- `render()` produces a string with `#` for alive, `.` for dead, rows separated
  by newlines.
- `render_with_info()` prepends a `Generation: N` header line.
- `PATTERNS` dict maps pattern names to text patterns loadable by
  `Grid.load_pattern`.

### Dependencies

- Unit 1 (Grid): Uses Grid for cell access and dimensions.
