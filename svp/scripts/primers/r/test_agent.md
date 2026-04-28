# R Architectural Primer — Test Agent

## Purpose

This primer applies when the test_agent is authoring testthat tests for an R-archetype project (`primary_language: "r"` or `archetype: "mixed"`). The test runner is `devtools::test()` and coverage is observed by `covr::environment_coverage()` against the loaded namespace. The patterns below preserve that observation chain. Tests that violate them may pass while reporting zero coverage on the function they exercised, which gets misread as "code uncovered" downstream.

## Architectural rules

1. **Tests run in-process under `devtools::test()`.** Do not author tests that fork a separate R process via `Rscript -e`, `system()`, `system2()`, or `callr::r()`. WHY: covr instrumentation lives in the parent R process only. Code reached only via subprocess is silently uncovered.

2. **Never call `setwd()` inside a test.** WHY: `setwd()` changes covr's reference frame and can break source-file attribution. If the test must run with a different working directory, use `withr::local_dir(tempdir())` (or any other directory) — `withr::local_dir` is properly scoped (auto-reverts at test exit) and is the canonical R idiom for temporary cwd changes.

3. **Reach functions through the package namespace, not via dynamic `source()`.** Do not write `source("R/my_function.R")` at the top of a test file. WHY: covr already instrumented the package at `load_all` time; `source()` loads a SECOND copy from a different file path, and the assertion runs against the second copy — so the original (instrumented) copy shows zero coverage. The function should be reachable as `mypackage:::my_function` (private) or `my_function` (exported via NAMESPACE).

## Anti-patterns

```r
# ANTI-PATTERN: setwd() in a test
test_that("processes data", {
  setwd(tempdir())              # <- breaks covr attribution
  write.csv(mtcars, "out.csv")
  expect_true(file.exists("out.csv"))
})
```

```r
# ANTI-PATTERN: dynamic source() of code under test
test_that("computes total", {
  source("../../R/compute_total.R")   # <- second copy, covr sees nothing
  expect_equal(compute_total(c(1, 2, 3)), 6)
})
```

```r
# ANTI-PATTERN: subprocess invocation
test_that("runs end-to-end", {
  out <- system2("Rscript", c("-e", "mypackage::run_pipeline()"), stdout = TRUE)
  expect_match(out, "OK")
})
```

## Refactor patterns

```r
# CORRECT: withr::local_dir for scoped cwd
test_that("processes data", {
  tmp <- withr::local_tempdir()
  withr::local_dir(tmp)
  write.csv(mtcars, "out.csv")
  expect_true(file.exists("out.csv"))
})
```

```r
# CORRECT: namespace-reached function, no source()
# devtools::load_all() (run by devtools::test() implicitly) makes the function
# available; no source() needed
test_that("computes total", {
  expect_equal(compute_total(c(1, 2, 3)), 6)
})
```

```r
# CORRECT: in-process call, no subprocess
test_that("runs end-to-end", {
  result <- run_pipeline()
  expect_equal(result$status, "OK")
})
```

## Coverage caveat

If the implementation under test legitimately uses a subprocess (e.g., an external compiled binary), the subprocess body is OUT OF SCOPE for covr by construction. Tests should exercise the wrapper that constructs the subprocess command (which IS in-process) and assert on its return value, NOT fork another R process to drive end-to-end behavior.
