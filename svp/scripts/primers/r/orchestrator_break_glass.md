# R Architectural Primer — Orchestrator Break-Glass

## Purpose

This primer applies when the orchestrator (main session) enters break-glass mode on an R-archetype child project (`primary_language: "r"` or `archetype: "mixed"`). It is the diagnostic-flavored subset of the R coverage-architecture knowledge: enough to recognize the attribution-loss patterns when triaging a covr report or a flaky test, without the full anti-pattern catalog the test_agent and implementation_agent carry. Use this primer to diagnose; delegate the fix to the appropriate agent.

## Diagnostic rules

1. **Before adding tests, confirm covr's attribution chain is intact.** When a covr report shows surprisingly low coverage on a function that has tests, four vectors silently break attribution:
   - **(a) `setwd()` inside a test** — covr's source-file map gets confused.
   - **(b) Dynamic `source()` of code-under-test inside a test** — covr already loaded the package; `source()` makes a second copy from a different file path; assertions hit the second copy.
   - **(c) Subprocess invocation** (`system`, `system2`, `Rscript -e`, `callr::r`, `processx::run`) — covr instruments only the parent R process.
   - **(d) Rmd / knitr render-from-tempdir** — knitr copies source to a tempdir before rendering; covr sees the copy path, not the package path. Caching compounds.
   When triaging, grep the test file for `setwd`, `source(`, `system(`, `system2(`, `Rscript`, `callr`, `processx` BEFORE asking the test_agent for more coverage.

2. **Reject covr-aware special branches as a fix.** If diagnosis surfaces `if (covr::in_covr()) ...` branches in implementation code, do NOT pass them through. They hide architectural bugs from rule 1. Open a bug to refactor the underlying test or implementation; cite the relevant rule from the test_agent or implementation_agent primer.

3. **Coverage is signal, not goal.** Resist the urge to "just write more tests" when a covr number looks low. A low number often signals a covr attribution-chain break (rule 1) — adding tests on top will not raise the number, and you will diagnose the symptom twice. Do the architectural diagnosis first; route the fix to test_agent or implementation_agent based on which side carries the violation.

## Diagnostic workflow

```
covr report shows low coverage on <function>
   |
   v
Step 1: grep tests/ for the four attribution-loss vectors
   - setwd, source(, system(, system2(, Rscript, callr, processx
   |
   +---- match found ----> Architectural cause. Route to test_agent (test side) or
   |                       implementation_agent (impl side) for refactor.
   |                       Do NOT add tests.
   |
   v
Step 2: confirm tests reach the function via package namespace (devtools::load_all)
   - is the function exported via NAMESPACE, or available as pkg:::fn?
   |
   +---- not reachable ----> blueprint_author / implementation_agent issue.
   |                         Function should be authored under R/ in the package.
   |
   v
Step 3: only after steps 1-2 rule out attribution-loss and reachability,
        consider that tests are genuinely missing. Route to test_agent.
```

## What to delegate, not solve in-place

The orchestrator's role in break-glass on an R project is to recognize the architectural pattern and dispatch the fix to the correct subagent. Do NOT edit R source files in-place to silence a covr report. Do NOT add `nolint` or covr-ignore comments. Do route a finding like "test file `tests/testthat/test-foo.R` calls `setwd()` at line 12; refactor to `withr::local_dir(tempdir())`" to the test_agent and let it carry the fix through the unit's normal cycle.

## When the report itself is suspect

If the same covr invocation produces different numbers on different machines (RStudio Test button vs CLI `Rscript -e 'covr::package_coverage()'`), the project's coverage setup is itself the bug — flag it as a separate finding rather than treating either number as ground truth. Cite the coverage_review primer rule on covr quirks for the contributor reading the bug entry.
