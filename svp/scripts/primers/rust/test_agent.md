# Rust Architectural Primer — Test Agent

## Purpose

This primer applies when the test_agent is authoring tests for a Rust-archetype project. The test runner is `cargo test`; coverage is observed by `cargo-tarpaulin` (Linux-only) or `cargo-llvm-cov` (cross-platform), which attribute via debuginfo emitted by `rustc` rather than via in-source instrumentation. The patterns below preserve that attribution chain. Tests that violate them may pass while reporting zero coverage on the function they exercised, which gets misread as "code uncovered" downstream.

NOTE: Rust support is a synthetic worked example for the SVP language-extension contract. Rust is NOT registered in `LANGUAGE_REGISTRY`. This primer exists as a template for future real Rust support.

## Architectural rules

1. **Tests run in-process under `cargo test`.** Do not author tests that fork a separate cargo / rustc process via `std::process::Command::new("cargo")` or `Command::new("rustc")`. WHY: cargo-tarpaulin instruments the compiled test binary in the parent process; child cargo processes recompile and run a separate, uninstrumented copy of the code, so executions reached only via subprocess are silently uncovered.

2. **Never call `std::env::set_current_dir()` inside a test.** WHY: changing the process cwd while tests run in parallel breaks subsequent path-resolution assumptions and can interact poorly with cargo-tarpaulin's source-file map. If the test must run with a different working directory, scope the change locally with a temporary directory created by `tempfile::tempdir()` and pass paths explicitly to the function under test rather than mutating global cwd.

3. **Reach functions through the crate's public API (or `pub(crate)` for unit tests in the same module), not via dynamic loading.** Do not write code that uses `libloading` or `dlopen` to load the crate's `.so` / `.dylib` from a test. WHY: cargo-tarpaulin already instrumented the compiled crate; loading a separately-built dynamic library (even built from the same source) produces a second copy whose executions are unattributed.

## Anti-patterns

```rust
// ANTI-PATTERN: set_current_dir() in a test
#[test]
fn processes_data() {
    std::env::set_current_dir("/tmp").unwrap();   // <- breaks cwd for other parallel tests
    std::fs::write("out.csv", "a,b\n1,2\n").unwrap();
    assert!(std::path::Path::new("out.csv").exists());
}
```

```rust
// ANTI-PATTERN: subprocess invocation of cargo from a test
#[test]
fn runs_end_to_end() {
    let output = std::process::Command::new("cargo")
        .args(["run", "--", "--input", "test.txt"])
        .output()
        .unwrap();
    assert!(output.status.success());
}
```

```rust
// ANTI-PATTERN: dynamic load of the crate's .so / .dylib from a test
#[test]
fn loads_dynamically() {
    let lib = unsafe { libloading::Library::new("target/release/libmycrate.dylib") }.unwrap();
    let func: libloading::Symbol<unsafe extern fn() -> i32> = unsafe { lib.get(b"compute") }.unwrap();
    assert_eq!(unsafe { func() }, 42);
}
```

## Refactor patterns

```rust
// CORRECT: tempfile::tempdir for scoped scratch space, paths passed explicitly
#[test]
fn processes_data() {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("out.csv");
    std::fs::write(&out, "a,b\n1,2\n").unwrap();
    assert!(out.exists());
}
```

```rust
// CORRECT: in-process call, no subprocess
#[test]
fn runs_end_to_end() {
    let result = mycrate::run_pipeline("test.txt");
    assert_eq!(result.status, "OK");
}
```

```rust
// CORRECT: reach the function via the crate's public API
#[test]
fn computes_total() {
    assert_eq!(mycrate::compute_total(&[1, 2, 3]), 6);
}
```

## Coverage caveat

If the implementation under test legitimately uses a subprocess (e.g., an external compiled binary), the subprocess body is OUT OF SCOPE for cargo-tarpaulin by construction. Tests should exercise the wrapper that constructs the subprocess command (which IS in-process) and assert on its return value, NOT fork another `cargo` process to drive end-to-end behavior.
