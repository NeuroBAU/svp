# Rust Architectural Primer — Orchestrator Break-Glass

## Purpose

This primer applies when the orchestrator (main session) enters break-glass mode on a Rust-archetype child project. It is the diagnostic-flavored subset of the Rust coverage-architecture knowledge: enough to recognize the attribution-loss patterns when triaging a cargo-tarpaulin report or a flaky test, without the full anti-pattern catalog the test_agent and implementation_agent carry. Use this primer to diagnose; delegate the fix to the appropriate agent.

NOTE: Rust support is a synthetic worked example for the SVP language-extension contract. Rust is NOT registered in `LANGUAGE_REGISTRY`. This primer exists as a template for future real Rust support.

## Diagnostic rules

1. **Before adding tests, confirm the coverage tool's attribution chain is intact.** When a cargo-tarpaulin or cargo-llvm-cov report shows surprisingly low coverage on a function that has tests, four vectors silently break attribution:
   - **(a) `std::env::set_current_dir()` inside a test** — confuses parallel-test cwd state and the source-file map.
   - **(b) Subprocess invocations of cargo / rustc / the built test binary** (`Command::new("cargo")`, `Command::new("./target/...")`) — coverage lives in the parent process binary; subprocesses run uninstrumented copies.
   - **(c) Procedural macros** — proc-macro bodies expand at compile time; coverage attribution maps to invocation sites, not macro body lines. Coverage of the macro body itself is generally unattributable.
   - **(d) Conditional compilation** — `#[cfg(not(test))]` and feature-gated `#[cfg(feature = "...")]` blocks not enabled by the coverage build are excluded at compile time, not "uncovered."
   When triaging, grep test files and `Cargo.toml` for `set_current_dir`, `Command::new("cargo")`, `Command::new("rustc")`, `proc_macro`, and `#[cfg(` BEFORE asking the test_agent for more coverage.

2. **Reject coverage-aware special branches as a fix.** If diagnosis surfaces `#[cfg(coverage)]` or `if cfg!(coverage)` branches in implementation code, do NOT pass them through. They hide architectural bugs from rule 1. Open a bug to refactor the underlying test or implementation; cite the relevant rule from the test_agent or implementation_agent primer.

3. **Coverage is signal, not goal.** Resist the urge to "just write more tests" when a tarpaulin number looks low. A low number often signals an attribution-chain break (rule 1) — adding tests on top will not raise the number, and you will diagnose the symptom twice. Do the architectural diagnosis first; route the fix to test_agent or implementation_agent based on which side carries the violation.

## Diagnostic workflow

```
cargo-tarpaulin report shows low coverage on <function>
   |
   v
Step 1: grep tests/ + src/ for the four attribution-loss vectors
   - set_current_dir, Command::new("cargo"), Command::new("rustc"),
     proc_macro, #[cfg(
   |
   +---- match found ----> Architectural cause. Route to test_agent (test side) or
   |                       implementation_agent (impl side) for refactor.
   |                       Do NOT add tests.
   |
   v
Step 2: confirm tests reach the function via the crate's public API or pub(crate)
   - is the function reachable via `mycrate::function` or via a same-module
     #[cfg(test)] mod tests { ... }?
   |
   +---- not reachable ----> blueprint_author / implementation_agent issue.
   |                         Function should be authored under src/<module>.rs
   |                         and exposed at the appropriate visibility.
   |
   v
Step 3: only after steps 1-2 rule out attribution-loss and reachability,
        consider that tests are genuinely missing. Route to test_agent.
```

## What to delegate, not solve in-place

The orchestrator's role in break-glass on a Rust project is to recognize the architectural pattern and dispatch the fix to the correct subagent. Do NOT edit Rust source files in-place to silence a tarpaulin report. Do NOT add `#[cfg(not(coverage))]` annotations or `// tarpaulin:: skip` directives. Do route a finding like "test file `tests/integration.rs` calls `set_current_dir` at line 12; refactor to `tempfile::tempdir()` with explicit path passing" to the test_agent and let it carry the fix through the unit's normal cycle.

## When the report itself is suspect

If the same coverage invocation produces different numbers across platforms (cargo-tarpaulin on Linux vs cargo-llvm-cov on macOS), build profiles (LTO on vs off), or feature-flag combinations, the project's coverage setup is itself the bug — flag it as a separate finding rather than treating any one number as ground truth. Cite the coverage_review primer rule on cargo-tarpaulin / cargo-llvm-cov quirks for the contributor reading the bug entry.
