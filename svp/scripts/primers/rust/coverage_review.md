# Rust Architectural Primer — Coverage Review

## Purpose

This primer applies when the coverage_review agent is reviewing cargo-tarpaulin (or cargo-llvm-cov) coverage reports for a Rust-archetype project. The most common review-time error is to read low coverage as "missing tests" when in fact the tooling lost the attribution due to an architectural pattern in the test or the code. Adding more tests will not fix attribution-loss; only refactoring will. The patterns below let you distinguish "code is uncovered" from "the coverage tool lost the trace."

NOTE: Rust support is a synthetic worked example for the SVP language-extension contract. Rust is NOT registered in `LANGUAGE_REGISTRY`. This primer exists as a template for future real Rust support.

## Architectural rules

1. **Recognize the four cargo-tarpaulin / cargo-llvm-cov attribution-loss vectors.** When coverage is unexpectedly low for a function that has tests targeting it, check for these patterns BEFORE concluding tests are missing:
   - **(a) `std::env::set_current_dir()` inside tests** — interferes with parallel test execution and the source-file map.
   - **(b) Subprocess invocations of cargo / rustc / the test binary** (`Command::new("cargo")`, `Command::new("rustc")`, `Command::new("./target/.../<bin>")`) — coverage instrumentation lives in the parent process binary; subprocesses recompile or re-execute uninstrumented copies.
   - **(c) Procedural macros (`#[proc_macro]`, `#[proc_macro_derive]`, `#[proc_macro_attribute]`)** — proc-macros expand at compile time into AST nodes whose source location maps back to the macro invocation site, not the macro body. Coverage of the macro body itself is generally unattributable; you must test the macro by exercising expanded output, not by counting body lines.
   - **(d) Conditional compilation (`#[cfg(...)]`)** — `#[cfg(not(test))]` and feature-gated `#[cfg(feature = "...")]` blocks are excluded from the test build at compile time. Lines inside excluded blocks are not "uncovered" — they were never compiled into the test binary.
   WHY: each vector silently moves execution out of the binary the coverage tool instrumented (or never compiled it in the first place).

2. **Refuse coverage-aware special branches as a fix for low coverage.** If you see a PR adding `#[cfg(coverage)]` or `if cfg!(coverage) { return ...; }` to make coverage numbers go up, REJECT it. WHY: that hack hides the architectural cause (one of the four vectors above). Find and fix the architectural cause; don't paint over the symptom.

3. **Coverage is signal, not goal.** Low coverage often signals a test-architecture problem, not a missing test. Diagnose first; require additional tests only after the four vectors are ruled out. WHY: adding tests on top of a broken attribution chain produces "more tests, same coverage number" — wasted effort and a false sense that the codebase is hard to test.

4. **Know the cargo-tarpaulin / cargo-llvm-cov quirks that produce confusing reports.** Even with clean tests:
   - cargo-tarpaulin is Linux-only by upstream policy; running the same crate on macOS or Windows requires cargo-llvm-cov, and the two tools' line counts can differ by a few percent on identical code because they account for branch coverage differently.
   - Inlined functions (`#[inline]`, `#[inline(always)]`) may attribute coverage to the call site rather than the inlinee body — both tools handle this differently.
   - LTO (link-time optimization) builds collapse cross-crate calls and can shift attribution; coverage runs MUST disable LTO (`profile.test.lto = false` in Cargo.toml).
   When the report's numbers depend on the build profile or platform, the project's coverage setup itself is suspect — flag it as a separate finding.

## Anti-patterns to flag in review

```rust
// FLAG: coverage-aware special branch (rule 2)
pub fn my_function(x: i32) -> i32 {
    if cfg!(coverage) { return 42; }   // <- coverage hack, REJECT
    // ...real implementation...
    x * 2
}
```

```rust
// FLAG: subprocess invocation in a test (rule 1b)
#[test]
fn runs_end_to_end() {
    let out = std::process::Command::new("cargo")
        .args(["run"])
        .output()
        .unwrap();
    assert!(out.status.success());
}
```

```rust
// FLAG: set_current_dir in a test (rule 1a)
#[test]
fn writes_output() {
    std::env::set_current_dir("/tmp").unwrap();
    // ...
}
```

## Refactor recommendations to issue

When a finding cites one of the four attribution-loss vectors, the recommendation should be to refactor the test or the implementation to eliminate the vector — NOT to add more tests, NOT to add `#[cfg(not(coverage))]` ignore comments, NOT to add `if cfg!(coverage)` branches. Cite the rule from the test_agent or implementation_agent primer that the project's Rust code violates.

## Coverage caveat

A function with legitimately uncoverable bodies (e.g., wrapping an external subprocess, or a proc-macro definition body) should be documented in the unit's blueprint contract with an explicit "coverage scope" note. The coverage_review's job is to verify the wrapper itself is covered (or the macro's expanded output is exercised), not to chase the subprocess body or the macro body lines. When you see such a function and the wrapper is fully tested, accept the coverage profile.
