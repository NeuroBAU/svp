# Rust Architectural Primer — Implementation Agent

## Purpose

This primer applies when the implementation_agent is writing Rust code for a Rust-archetype project. The primer encodes the architectural decisions that the test runner (`cargo test`) and coverage tools (`cargo-tarpaulin`, `cargo-llvm-cov`) require to attribute coverage correctly to the source files you author. Code that violates these patterns may produce passing tests with zero or wrong coverage.

NOTE: Rust support is a synthetic worked example for the SVP language-extension contract. Rust is NOT registered in `LANGUAGE_REGISTRY`. This primer exists as a template for future real Rust support.

## Architectural rules

1. **Author functions inside a Cargo crate (`src/lib.rs` or `src/main.rs` plus modules).** The unit's code lives at `src/<module>.rs` referenced by `mod <module>;` declarations from `lib.rs`, not as loose scripts. WHY: cargo-tarpaulin instruments compiled binaries via debuginfo emitted by `rustc`; only files that are part of a Cargo build target produce debuginfo and are therefore attributable.

2. **Tests run in-process via `cargo test`, not via subprocess `cargo` invocations.** The implementation must NOT use `std::process::Command::new("cargo")` to recursively invoke `cargo test` from inside a test or from production code that tests reach. WHY: a child `cargo` process compiles a separate copy of the crate; coverage instrumentation in the parent process does not see the child's executions, so coverage is silently lost.

3. **Use `env!("CARGO_MANIFEST_DIR")` for paths the implementation needs to resolve relative to the crate root.** Don't hardcode `std::env::current_dir()`-relative paths inside the implementation. WHY: `CARGO_MANIFEST_DIR` is set by Cargo at compile time and is stable across `cargo test`, `cargo run`, and downstream consumers' invocations; `current_dir()` varies by invocation site.

4. **Tests will be invoked via `cargo test`.** Author your code so it compiles and runs cleanly under `cargo test --workspace` (or `--lib` / `--all-targets` as appropriate). Don't rely on a particular crate-feature flag being on by default in tests unless the manifest enables it. WHY: cargo-tarpaulin runs `cargo test` with whatever feature flags it computes from `Cargo.toml`; if your code only compiles under a non-default feature, the coverage build skips it.

## Anti-patterns

```rust
// ANTI-PATTERN: subprocess invocation of cargo from test-reachable code
fn run_pipeline(input: &str) -> String {
    let output = std::process::Command::new("cargo")
        .args(["test", "--", "compute"])
        .output()
        .unwrap();
    String::from_utf8(output.stdout).unwrap()
}
```

```rust
// ANTI-PATTERN: cwd-relative path in implementation
fn load_config() -> String {
    let cwd = std::env::current_dir().unwrap();
    std::fs::read_to_string(cwd.join("config.toml")).unwrap()
}
```

## Refactor patterns

```rust
// CORRECT: in-process function, accessible via module path
// File: src/pipeline.rs
pub fn run_pipeline(input: &str) -> String {
    compute(input)
}
```

```rust
// CORRECT: caller passes resolved path; implementation accepts a Path
// File: src/loader.rs
use std::path::Path;

pub fn load_config(path: &Path) -> String {
    std::fs::read_to_string(path).unwrap()
}

// File: tests/integration.rs
#[test]
fn loads() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let path = std::path::Path::new(manifest_dir).join("tests/fixtures/config.toml");
    let result = mycrate::load_config(&path);
    assert!(!result.is_empty());
}
```

## Coverage caveat

If the implementation legitimately must invoke a subprocess (e.g., calling an external compiled binary), the subprocess work is OUT OF SCOPE for cargo-tarpaulin. Document this in the unit contract; the coverage_review agent will not flag missing coverage for the subprocess body but expects coverage of the wrapper that constructs the subprocess command. Tests for the wrapper should NOT fork another `cargo` process to drive end-to-end behavior.
