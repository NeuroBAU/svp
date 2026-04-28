# R Architectural Primer — Coverage Review

## Purpose

This primer applies when the coverage_review agent is reviewing covr coverage reports for an R-archetype project (`primary_language: "r"` or `archetype: "mixed"`). The most common review-time error is to read low coverage as "missing tests" when in fact covr lost the attribution due to an architectural pattern in the test or the code. Adding more tests will not fix attribution-loss; only refactoring will. The patterns below let you distinguish "code is uncovered" from "covr lost the trace."

## Architectural rules

1. **Recognize the four covr attribution-loss vectors.** When coverage is unexpectedly low for a function that has tests targeting it, check for these patterns BEFORE concluding tests are missing:
   - **(a) `setwd()` in a test** — wd-dependent paths confuse covr's source-file map.
   - **(b) Dynamic `source()` of code-under-test inside a test** — covr already instrumented the package; `source()` loads a different copy from a different file path.
   - **(c) Subprocess invocations** (`system`, `system2`, `Rscript -e`, `callr::r`, `processx::run`) — covr instrumentation lives in the parent R process; subprocess code is uninstrumented.
   - **(d) Rmd/Rnw render-from-tempdir or knitr cache chains** — knitr copies source to a tempdir and renders the copy; covr sees the copy's path, not the package source's path. Caching compounds the loss.
   WHY: each vector silently moves execution to code that covr did not (or cannot) instrument.

2. **Refuse covr-aware special branches as a fix for low coverage.** If you see a PR adding `if (covr::in_covr()) ...` to make coverage numbers go up, REJECT it. WHY: that hack hides the architectural cause (one of the four vectors above). Find and fix the architectural cause; don't paint over the symptom.

3. **Coverage is signal, not goal.** Low coverage often signals a test-architecture problem, not a missing test. Diagnose first; require additional tests only after the four vectors are ruled out. WHY: adding tests on top of a broken attribution chain produces "more tests, same coverage number" — wasted effort and a false sense that the codebase is hard to test.

4. **Know the covr quirks that produce confusing reports.** Even with clean tests:
   - Parallel test execution (`future_lapply`, `parallel::mclapply` inside tests) breaks attribution because instrumented code runs in a forked process.
   - Rmd/Quarto compile chains, especially with cache, lose attribution as in 1(d).
   - Running covr from RStudio's Test button vs. CLI (`Rscript -e 'covr::package_coverage()'`) gives different results because the loading mechanism differs.
   When the report's numbers depend on the invocation environment, the project's covr setup itself is suspect — flag it as a separate finding.

## Anti-patterns to flag in review

```r
# FLAG: covr-aware special branch (rule 2)
my_function <- function(x) {
  if (covr::in_covr()) return(42)  # <- coverage hack, REJECT
  ...real implementation...
}
```

```r
# FLAG: dynamic source() inside a test (rule 1b)
test_that("works", {
  source("../../R/my_function.R")
  expect_equal(my_function(1), 1)
})
```

```r
# FLAG: subprocess invocation in a test (rule 1c)
test_that("end-to-end", {
  result <- system2("Rscript", "-e", "mypackage::run()", stdout = TRUE)
  expect_match(result, "OK")
})
```

## Refactor recommendations to issue

When a finding cites one of the four attribution-loss vectors, the recommendation should be to refactor the test or the implementation to eliminate the vector — NOT to add more tests, NOT to add covr ignore comments, NOT to add `if (covr::in_covr())` branches. Cite the rule from the test_agent or implementation_agent primer that the project's R code violates.

## Coverage caveat

A function with legitimately uncoverable bodies (e.g., wrapping an external subprocess) should be documented in the unit's blueprint contract with an explicit "coverage scope" note. The coverage_review's job is to verify the wrapper itself is covered, not to chase the subprocess body. When you see such a function and the wrapper is fully tested, accept the coverage profile.
