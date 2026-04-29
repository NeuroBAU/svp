# Rust Architectural Primer — Blueprint Author

## Purpose

This primer applies when the blueprint_author agent is authoring a blueprint for a Rust-archetype project (`primary_language: "rust"`). It encodes architectural decisions that downstream tooling (`cargo`, `cargo-tarpaulin`, `cargo-llvm-cov`) requires to function correctly. Authoring blueprints that violate these conventions produces blueprints whose Stage-3 implementation cannot pass coverage review without an architectural redo.

NOTE: Rust support is a synthetic worked example for the SVP language-extension contract. Rust is NOT registered in `LANGUAGE_REGISTRY`. This primer exists as a template for future real Rust support.

## Architectural rules

1. **Mandate Cargo package layout.** Every Rust unit blueprint declares the unit's source under `src/lib.rs` (library crate) or `src/main.rs` (binary crate) plus optional submodules under `src/<module>.rs`. The blueprint's file-tree annotation MUST reflect this. WHY: cargo-tarpaulin (and cargo-llvm-cov) understand the standard Cargo layout (Cargo.toml + src/ + tests/); loose `.rs` files outside Cargo's manifest are invisible to coverage attribution.

2. **Distinguish unit tests vs integration tests.** Unit tests live inline as `#[cfg(test)] mod tests { ... }` inside the module they exercise; integration tests live as separate files under `tests/<name>.rs`. Blueprint-tier contracts that require fixtures or end-to-end exercise SHOULD specify integration tests under `tests/`. WHY: `cargo test` runs both, but they have different visibility — unit tests can call `pub(crate)` items, integration tests can only call the public API.

3. **Mandate `env!("CARGO_MANIFEST_DIR")` or `tempfile::tempdir()` for path resolution inside tests.** When a unit's contract specifies that a test reads or writes a file, paths MUST be expressed relative to `CARGO_MANIFEST_DIR` or under a `tempfile::tempdir()` scratch directory. Hard-coded absolute paths or `std::env::current_dir()` break under `cargo test` from arbitrary cwd. WHY: `CARGO_MANIFEST_DIR` is stable across invocation modes; `tempfile` auto-cleans.

## Anti-patterns

```rust
// ANTI-PATTERN: loose .rs files outside Cargo project
// my_function.rs                <- at project root, not inside any crate
// tests/test_something.rs       <- works only if Cargo.toml exists at root
```

```rust
// ANTI-PATTERN: hard-coded absolute path in test fixture lookup
#[test]
fn reads_fixture() {
    let data = std::fs::read_to_string("/Users/me/project/tests/fixtures/data.csv")
        .unwrap();
    assert!(!data.is_empty());
}
```

## Refactor patterns

```rust
// CORRECT: Cargo package layout
// Cargo.toml
// src/lib.rs
// src/my_module.rs
// tests/integration_test.rs        <- integration tests
```

```rust
// CORRECT: CARGO_MANIFEST_DIR resolves under all invocation modes
#[test]
fn reads_fixture() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let path = std::path::Path::new(manifest_dir).join("tests/fixtures/data.csv");
    let data = std::fs::read_to_string(&path).unwrap();
    assert!(!data.is_empty());
}
```

## Coverage caveat

When a blueprint contract describes code that must be reached only through a procedural macro expansion (proc-macros run at compile time), document the coverage trade-off explicitly: cargo-tarpaulin and cargo-llvm-cov attribute via debuginfo emitted by `rustc`, and proc-macro-expanded code is harder to attribute to its source location. The default for SVP-authored Rust blueprints is the standard Cargo package layout with conventional `#[cfg(test)]` modules; deviations require an explicit blueprint section justifying the trade-off.
