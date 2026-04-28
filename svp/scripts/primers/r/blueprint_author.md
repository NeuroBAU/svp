# R Architectural Primer — Blueprint Author

## Purpose

This primer applies when the blueprint_author agent is authoring a blueprint for an R-archetype project (`primary_language: "r"` or `archetype: "mixed"` with R as a side). The primer encodes architectural decisions that downstream tooling (devtools, testthat, covr) requires to function correctly. Authoring blueprints that violate these conventions produces blueprints whose Stage-3 implementation cannot pass coverage review without an architectural redo.

## Architectural rules

1. **Mandate package layout.** Every R unit blueprint declares the unit's source as proper R-package files under `R/` and tests under `tests/testthat/`. The blueprint's file-tree annotation MUST reflect this. WHY: covr understands package structure (DESCRIPTION + NAMESPACE + R/ + tests/testthat/); loose scripts confuse coverage attribution and require workarounds at the implementation stage.

2. **Mandate `testthat::test_path()` for any contract that resolves a file path inside tests.** When a unit's contract specifies that a test reads or writes a file (fixtures, golden outputs, helper data), the path MUST be expressed as `test_path("relative/path")`. Hard-coded absolute paths or paths constructed via `getwd()` break under `devtools::test()`, `R CMD check`, and CI. WHY: `test_path()` resolves relative to `tests/testthat/` under all invocation modes.

## Anti-patterns

```r
# ANTI-PATTERN: loose script layout (no DESCRIPTION, no R/ dir)
# tests/test_something.R     <- not under testthat/
# my_function.R              <- at project root, not under R/
```

```r
# ANTI-PATTERN: hard-coded path in test fixture lookup
test_that("reads fixture", {
  data <- read.csv("/Users/me/project/tests/testthat/fixtures/data.csv")
  expect_equal(nrow(data), 10)
})
```

## Refactor patterns

```r
# CORRECT: package layout
# R/my_function.R
# tests/testthat/test-my-function.R
# DESCRIPTION
# NAMESPACE
```

```r
# CORRECT: test_path() resolves under all invocation modes
test_that("reads fixture", {
  data <- read.csv(test_path("fixtures", "data.csv"))
  expect_equal(nrow(data), 10)
})
```

## Coverage caveat

When the blueprint contract demands a non-package layout (rare, e.g. a one-off analysis Quarto script with no R package wrapping), document the coverage trade-off explicitly: covr will see only the loaded package namespace, not loose scripts. The default for SVP-authored R projects is the package layout. Deviations require an explicit blueprint section justifying the trade-off.
