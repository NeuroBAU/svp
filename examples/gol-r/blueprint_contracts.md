# Blueprint Contracts (Tier 2 + Tier 3) -- GoL R

**Project:** gol-r
**Archetype:** B (r_project)
**Blueprint version:** 1.0
**Units:** 4

---

## Unit 1: GoL Engine (`R/engine.R`)

### Tier 2 — Signatures

```r
create_grid <- function(rows = 30L, cols = 30L) { ... }
count_neighbors <- function(grid) { ... }
step_grid <- function(grid) { ... }
toggle_cell <- function(grid, row, col) { ... }
clear_grid <- function(grid) { ... }
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

Spec refs: FR-3.1.4, FR-3.2.5, FR-4.1.3, Section 7.1

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

Spec refs: FR-3.2.3, FR-3.2.4, FR-3.2.5

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
- ERR-1: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.2.1, FR-3.2.2, FR-3.2.6, AC-3.2.A through AC-3.2.E

**toggle_cell:**

Parameters:

| Name | Type           | Default | Description                |
|------|----------------|---------|----------------------------|
| grid | logical matrix | (none)  | Current grid state         |
| row  | integer        | (none)  | Row index (1-based)        |
| col  | integer        | (none)  | Column index (1-based)     |

Returns: logical matrix with cell [row, col] flipped (TRUE <-> FALSE).

- PRE-1: is.matrix(grid) && is.logical(grid)
- PRE-2: is.numeric(row) && length(row) == 1 && row >= 1 && row <= nrow(grid)
- PRE-3: is.numeric(col) && length(col) == 1 && col >= 1 && col <= ncol(grid)
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: result[row, col] == !grid[row, col]
- POST-3: For all [i, j] where !(i == row && j == col): result[i, j] == grid[i, j]
- POST-4: grid is not modified (no side effects).
- ERR-1: row < 1 || row > nrow(grid) || col < 1 || col > ncol(grid) -> stop("Cell coordinates out of bounds")
- ERR-2: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: (internal utility, supports interactive toggle if extended)

**clear_grid:**

Parameters:

| Name | Type           | Default | Description                |
|------|----------------|---------|----------------------------|
| grid | logical matrix | (none)  | Grid to clear              |

Returns: logical matrix of same dimensions, all FALSE.

- PRE-1: is.matrix(grid) && is.logical(grid)
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == nrow(grid) && ncol(result) == ncol(grid)
- POST-3: all(result == FALSE)
- POST-4: grid is not modified (no side effects).
- ERR-1: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.3.7, FR-3.5.4

---

## Unit 2: Pattern Library (`R/patterns.R`)

### Tier 2 — Signatures

```r
get_patterns <- function() { ... }
get_pattern_names <- function() { ... }
get_pattern <- function(name) { ... }
place_pattern <- function(grid, name) { ... }
```

### Tier 3 — Behavioral Contracts

**Dependencies:** **Unit 1** (clear_grid).

**get_patterns:**

Parameters: None.

Returns: named list of 5 elements. Each element is a two-column
integer matrix with columns representing (row_offset, col_offset),
1-based. Names: "beacon", "blinker", "block", "glider", "pulsar"
(alphabetical).

- PRE: (none -- no arguments)
- POST-1: is.list(result) && length(result) == 5L
- POST-2: identical(sort(names(result)), c("beacon", "blinker", "block", "glider", "pulsar"))
- POST-3: For each element m in result: is.matrix(m) && is.integer(m) && ncol(m) == 2L && nrow(m) >= 1L
- POST-4: For each element m, all(m >= 1L) (all offsets are 1-based positive)
- POST-5: result$blinker has 3 rows (3 cells), bounding box 1x3.
- POST-6: result$block has 4 rows (4 cells), bounding box 2x2.
- POST-7: result$beacon has 6 rows (6 cells), bounding box 4x4.
- POST-8: result$glider has 5 rows (5 cells), bounding box 3x3.
- POST-9: result$pulsar has 48 rows (48 cells), bounding box 13x13.
- POST-10: Successive calls return identical results (immutable data).
- ERR: (none -- function cannot fail)

Spec refs: FR-3.5.1, FR-3.5.2, Section 7.2

**get_pattern_names:**

Parameters: None.

Returns: character vector of pattern names, sorted alphabetically.

- PRE: (none)
- POST-1: is.character(result)
- POST-2: identical(result, sort(names(get_patterns())))
- POST-3: length(result) == 5L
- ERR: (none)

Spec refs: FR-4.1.3 (indirectly, for help/error messages)

**get_pattern:**

Parameters:

| Name | Type      | Default | Description                      |
|------|-----------|---------|----------------------------------|
| name | character | (none)  | Pattern name (case-insensitive)  |

Returns: two-column integer matrix of (row_offset, col_offset) for the
named pattern.

- PRE-1: is.character(name) && length(name) == 1L
- POST-1: is.matrix(result) && is.integer(result) && ncol(result) == 2L
- POST-2: identical(result, get_patterns()[[tolower(name)]])
- POST-3: Case-insensitive: get_pattern("GLIDER") == get_pattern("glider")
- ERR-1: tolower(name) not in names(get_patterns()) -> stop() with message containing "Unknown pattern" and listing valid names
- ERR-2: !is.character(name) || length(name) != 1L -> stop("name must be a single character string")

Spec refs: FR-3.3.8, FR-3.3.13

**place_pattern:**

Parameters:

| Name | Type           | Default | Description                             |
|------|----------------|---------|----------------------------------------|
| grid | logical matrix | (none)  | Grid to place the pattern on           |
| name | character      | (none)  | Pattern name (case-insensitive)        |

Returns: logical matrix with grid cleared and pattern placed centered.

- PRE-1: is.matrix(grid) && is.logical(grid)
- PRE-2: is.character(name) && length(name) == 1L
- PRE-3: tolower(name) %in% get_pattern_names()
- POST-1: is.matrix(result) && is.logical(result)
- POST-2: nrow(result) == nrow(grid) && ncol(result) == ncol(grid)
- POST-3: sum(result) == nrow(get_pattern(name)) (number of alive cells equals pattern cell count, unless toroidal wrapping causes overlapping offsets)
- POST-4: Pattern is centered: row_offset = floor((nrow(grid) - pattern_height) / 2) + 1, col_offset = floor((ncol(grid) - pattern_width) / 2) + 1, where pattern_height = max(pattern[, 1]) and pattern_width = max(pattern[, 2])
- POST-5: All non-pattern cells are FALSE (grid was cleared first).
- POST-6: grid is not modified (no side effects).
- WARN-1: If pattern_height > nrow(grid) || pattern_width > ncol(grid) -> warning() issued containing "pattern" and "grid" in the message; cells placed using ((index - 1) %% dim) + 1 toroidal wrapping.
- ERR-1: Unknown pattern name -> stop() via get_pattern (delegates error)
- ERR-2: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.5.3, FR-3.5.4, FR-3.5.5, AC-3.5.A through AC-3.5.C

---

## Unit 3: Display (`R/display.R`)

### Tier 2 — Signatures

```r
display_grid <- function(grid, generation) { ... }
parse_command <- function(input) { ... }
run_game <- function(rows = 30L, cols = 30L, pattern = NULL, delay = 0.1) { ... }
```

### Tier 3 — Behavioral Contracts

**Dependencies:** **Unit 1** (create_grid, step_grid, clear_grid), **Unit 2** (place_pattern, get_pattern_names).

**display_grid:**

Parameters:

| Name       | Type           | Default | Description                  |
|------------|----------------|---------|------------------------------|
| grid       | logical matrix | (none)  | Grid to display              |
| generation | integer        | (none)  | Current generation count     |

Returns: invisible(NULL). Side effect: prints to terminal via cat().

- PRE-1: is.matrix(grid) && is.logical(grid)
- PRE-2: is.numeric(generation) && length(generation) == 1 && generation >= 0
- POST-1: Output starts with a blank line ("\n").
- POST-2: Second line is "Generation: N\n" where N == generation.
- POST-3: Following nrow(grid) lines each contain ncol(grid) characters, where TRUE cells are "#" and FALSE cells are ".".
- POST-4: No spaces between cell characters within a row.
- POST-5: Final line is "> " (prompt, no trailing newline -- use cat()).
- POST-6: Returns invisible(NULL).
- ERR-1: !is.matrix(grid) || !is.logical(grid) -> stop("grid must be a logical matrix")

Spec refs: FR-3.1.1 through FR-3.1.7, FR-3.4.4

**parse_command:**

Parameters:

| Name  | Type      | Default | Description                          |
|-------|-----------|---------|--------------------------------------|
| input | character | (none)  | Raw user input string                |

Returns: list with two elements: `command` (character scalar, lowercase)
and `args` (character vector, possibly length 0).

- PRE-1: is.character(input) && length(input) == 1L
- POST-1: is.list(result)
- POST-2: "command" %in% names(result) && "args" %in% names(result)
- POST-3: is.character(result$command) && length(result$command) == 1L
- POST-4: is.character(result$args)
- POST-5: result$command == tolower(trimws(first_word))
- POST-6: result$args contains remaining words after splitting on whitespace, all lowercase.
- POST-7: parse_command("  STEP  5  ") -> list(command = "step", args = "5")
- POST-8: parse_command("quit") -> list(command = "quit", args = character(0))
- POST-9: parse_command("  ") -> list(command = "", args = character(0))
- POST-10: parse_command("LOAD  Glider") -> list(command = "load", args = "glider")
- ERR-1: !is.character(input) -> stop("input must be a character string")

Spec refs: FR-3.3.1, FR-3.3.2

**run_game:**

Parameters:

| Name    | Type              | Default | Description                       |
|---------|-------------------|---------|-----------------------------------|
| rows    | integer           | 30L     | Grid rows                         |
| cols    | integer           | 30L     | Grid columns                      |
| pattern | character or NULL | NULL    | Initial pattern name, or NULL     |
| delay   | numeric           | 0.1     | Seconds between frames in `run`   |

Returns: invisible(grid) -- the final grid state when the user quits.

- PRE-1: is.numeric(rows) && rows >= 3
- PRE-2: is.numeric(cols) && cols >= 3
- PRE-3: is.null(pattern) || (is.character(pattern) && length(pattern) == 1L)
- PRE-4: is.numeric(delay) && delay > 0
- POST-1: On entry, creates a grid via create_grid(rows, cols).
- POST-2: If pattern is non-NULL, calls place_pattern(grid, pattern).
- POST-3: Initializes generation counter to 0.
- POST-4: Calls display_grid to show initial state.
- POST-5: Enters readline loop; each iteration: a. Reads input via readline(""). b. Parses via parse_command. c. Dispatches: "step" [N]: calls step_grid N times (default 1), increments counter by N, displays once. "run" N: loops N times {step_grid, increment, display, Sys.sleep(delay)}. "reset": clear_grid, counter = 0, display. "load" P: place_pattern(grid, P), counter = 0, display. "help": cat() summary of commands. "quit": break loop. "": no-op (redisplay prompt only). other: cat("Unknown command. Type 'help' for available commands.\n")
- POST-6: Returns invisible(grid) after loop exits.
- POST-7: "step N" / "run N" with non-positive or non-integer N -> cat() error message, no grid/counter change.
- POST-8: "load UNKNOWN" -> cat() error message listing valid patterns, no grid/counter change.
- ERR-1: Invalid rows/cols/delay -> stop() (pre-condition violation).

Spec refs: FR-3.3.1 through FR-3.3.13, FR-3.4.1 through FR-3.4.3,
FR-4.1.4, AC-3.3.A through AC-3.3.H

---

## Unit 4: Main (`R/main.R` + `inst/run_gol.R`)

### Tier 2 — Signatures

```r
parse_cli_args <- function(args = commandArgs(trailingOnly = TRUE)) { ... }
validate_cli_args <- function(parsed) { ... }
main <- function(args = commandArgs(trailingOnly = TRUE)) { ... }
```

### Tier 3 — Behavioral Contracts

**Dependencies:** **Unit 2** (get_pattern_names), **Unit 3** (run_game).

**parse_cli_args:**

Parameters:

| Name | Type      | Default                          | Description           |
|------|-----------|----------------------------------|-----------------------|
| args | character | commandArgs(trailingOnly = TRUE)  | CLI argument vector   |

Returns: list with elements: `rows` (integer or NULL), `cols` (integer
or NULL), `pattern` (character or NULL), `delay` (numeric or NULL). NULL
means the argument was not provided.

- PRE-1: is.character(args)
- POST-1: is.list(result)
- POST-2: names(result) contains "rows", "cols", "pattern", "delay"
- POST-3: parse_cli_args(c("--rows", "20", "--cols", "40")) -> list(rows = 20L, cols = 40L, pattern = NULL, delay = NULL)
- POST-4: parse_cli_args(c("--pattern", "glider")) -> list(rows = NULL, cols = NULL, pattern = "glider", delay = NULL)
- POST-5: parse_cli_args(c("--delay", "0.5")) -> list(rows = NULL, cols = NULL, pattern = NULL, delay = 0.5)
- POST-6: parse_cli_args(character(0)) -> list(rows = NULL, cols = NULL, pattern = NULL, delay = NULL)
- POST-7: Unrecognized arguments (e.g., "--foo", "bar") are silently ignored.
- POST-8: "--rows" expects the next element to be the value; if missing or not convertible to integer, result$rows remains NULL.
- ERR: (none -- malformed args produce NULL values, validation is separate)

Spec refs: FR-6.2

**validate_cli_args:**

Parameters:

| Name   | Type | Default | Description                         |
|--------|------|---------|-------------------------------------|
| parsed | list | (none)  | Output of parse_cli_args            |

Returns: list with elements: `rows` (integer), `cols` (integer),
`pattern` (character or NULL), `delay` (numeric). All non-NULL values
are validated; NULLs replaced with defaults.

- PRE-1: is.list(parsed)
- PRE-2: names(parsed) contains "rows", "cols", "pattern", "delay"
- POST-1: result$rows is integer, >= 3. Default: 30L.
- POST-2: result$cols is integer, >= 3. Default: 30L.
- POST-3: result$delay is numeric, > 0. Default: 0.1.
- POST-4: result$pattern is NULL or a valid pattern name (tolower(result$pattern) %in% get_pattern_names()).
- ERR-1: parsed$rows is non-NULL and (not integer-like or < 3) -> stop("--rows must be an integer >= 3")
- ERR-2: parsed$cols is non-NULL and (not integer-like or < 3) -> stop("--cols must be an integer >= 3")
- ERR-3: parsed$delay is non-NULL and (not numeric or <= 0) -> stop("--delay must be a positive number")
- ERR-4: parsed$pattern is non-NULL and not in get_pattern_names() -> stop() with message containing "Unknown pattern" and listing valid pattern names (comma-separated)

Spec refs: FR-6.3 through FR-6.6, AC-6.A through AC-6.C

**main:**

Parameters:

| Name | Type      | Default                          | Description           |
|------|-----------|----------------------------------|-----------------------|
| args | character | commandArgs(trailingOnly = TRUE)  | CLI argument vector   |

Returns: invisible(grid) -- the return value of run_game.

- PRE-1: is.character(args)
- POST-1: Calls parse_cli_args(args).
- POST-2: Calls validate_cli_args on the result.
- POST-3: Calls run_game(rows, cols, pattern, delay) with validated args.
- POST-4: Returns invisible(result of run_game).
- ERR-1: Validation failures propagate stop() from validate_cli_args.

Spec refs: FR-6.1, FR-4.1.4

**inst/run_gol.R (script, not a function):**

Standalone Rscript entry point. Not an exported function.

Pseudocode:

```r
# inst/run_gol.R
tryCatch(
  {
    library(golr)
    main()
  },
  error = function(e) {
    message(conditionMessage(e))
    quit(status = 1, save = "no")
  }
)
```

- POST-1: On success (user types "quit"), exits with status 0.
- POST-2: On validation error (bad args), prints error message to stderr via message() and exits with status 1.
- POST-3: Error message for unknown pattern includes list of valid names.
- ERR: All errors caught by tryCatch; none propagate to the R session.

Spec refs: FR-6.1, FR-6.4, FR-6.5, FR-6.6

---

## Cross-Unit Contract Summary

### Dependency Contracts

| Consumer            | Provider            | Contract                                    |
|---------------------|---------------------|---------------------------------------------|
| place_pattern       | clear_grid          | Receives valid logical matrix, returns same dims all FALSE |
| place_pattern       | get_pattern         | Receives valid name, returns 2-col integer matrix |
| run_game            | create_grid         | rows >= 3, cols >= 3 -> valid logical matrix |
| run_game            | step_grid           | Valid logical matrix in -> valid logical matrix out |
| run_game            | clear_grid          | Valid logical matrix in -> same-dims all-FALSE out |
| run_game            | place_pattern       | Valid grid + valid name -> centered pattern grid |
| run_game            | display_grid        | Valid grid + generation >= 0 -> cat() output |
| run_game            | get_pattern_names   | Returns character vector of valid names     |
| validate_cli_args   | get_pattern_names   | Returns character vector of valid names     |
| main                | parse_cli_args      | Character vector -> parsed list             |
| main                | validate_cli_args   | Parsed list -> validated list or stop()     |
| main                | run_game            | Validated args -> interactive session       |

### Shared Invariants

1. **Grid type invariant.** Every grid passed between functions is a
   logical matrix with nrow >= 3 and ncol >= 3. No function may return
   a grid that violates this.

2. **Immutability invariant.** No function modifies its input grid
   argument. All grid-returning functions produce a new matrix.

3. **Pattern name invariant.** Pattern names are always compared
   case-insensitively (via tolower). The canonical form is lowercase.

4. **1-based indexing invariant.** All row/column coordinates throughout
   the codebase are 1-based, following R convention.

5. **Toroidal wrapping formula.** Wherever toroidal wrapping is applied,
   the formula is ((index - 1) %% dim) + 1, converting any integer
   coordinate to a valid 1-based index.

---

*End of blueprint contracts.*
