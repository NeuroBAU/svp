# R Architectural Primer — Implementation Agent

## Purpose

This primer applies when the implementation_agent is writing R code for an R-archetype project (`primary_language: "r"` or `archetype: "mixed"`). The primer encodes the architectural decisions that the test runner (`devtools::test()`) and coverage tool (`covr`) require to attribute coverage correctly to the source files you author. Code that violates these patterns may produce passing tests with zero or wrong coverage.

## Architectural rules

1. **Author functions in `R/` files of an R package.** The unit's code lives at `R/<module>.R` (one or more files), not as loose scripts. WHY: covr instruments package source files at namespace load; loose-script files are not part of any namespace and are therefore unattributable.

2. **Tests run in-process, not via subprocess.** The implementation must NOT use `system()`, `system2()`, `Rscript -e`, `processx`, or `callr::r()` to invoke logic that the tests are supposed to cover. WHY: covr instrumentation lives in the parent R process only; subprocesses execute uninstrumented copies of the code, so coverage is silently lost.

3. **Use `test_path()` for any path the implementation needs to resolve relative to the test directory.** If the implementation reads bundled fixtures or seed data from `tests/testthat/`, expose a function that takes a path argument and let the test pass `test_path(...)` in. Don't hardcode `getwd()`-relative paths inside the implementation. WHY: the implementation function may run under `devtools::test()`, `R CMD check`, CI, or an interactive session — only `test_path()` (in the caller) resolves correctly under all of them.

4. **Tests will be invoked via `devtools::test()`.** Author your code so it loads cleanly under `devtools::load_all(".", export_all = TRUE)`. Don't rely on the user having `library(yourpackage)`'d the package before running tests. WHY: `devtools::test()` calls `load_all` first; covr observes the loaded namespace. Behavior under `library()` only is irrelevant to the coverage pipeline.

## Anti-patterns

```r
# ANTI-PATTERN: subprocess invocation of code under test
my_function <- function(x) {
  result <- system2("Rscript", args = c("-e", paste0("compute(", x, ")")), stdout = TRUE)
  as.numeric(result)
}
```

```r
# ANTI-PATTERN: loose script path with absolute reference
# (lives at /home/user/project/scripts/my_func.R; tests cannot find it)
my_function <- function() {
  source("/home/user/project/data/setup.R")
  ...
}
```

## Refactor patterns

```r
# CORRECT: in-process function, package-namespaced
# File: R/my_function.R
my_function <- function(x) {
  compute(x)
}
```

```r
# CORRECT: caller passes resolved path; implementation accepts a path
# File: R/my_function.R
load_data <- function(path) {
  read.csv(path)
}

# File: tests/testthat/test-my-function.R
test_that("loads", {
  result <- load_data(test_path("fixtures", "data.csv"))
  expect_equal(nrow(result), 10)
})
```

## Coverage caveat

If the implementation legitimately must invoke a subprocess (e.g., calling an external compiled binary), the subprocess work is OUT OF SCOPE for covr. Document this in the unit contract; the coverage_review agent will not flag missing coverage for the subprocess body, but expects coverage of the wrapper that constructs the subprocess command. Tests for the wrapper should not fork another R process.
