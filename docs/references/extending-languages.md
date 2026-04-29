# Extending SVP with a New Language Archetype

This document is the canonical extension contract for adding a new language archetype to SVP. It describes the **two-contract architecture** that emerged from rounds A-E of the env-provisioning + language-architecture-primers sub-project (S3-174 through S3-184) and demonstrates each contract via the synthetic Rust archetype shipped at `scripts/toolchain_defaults/rust_cargo_test.json` and `scripts/primers/rust/`.

Reference patterns: P58 (schema-as-extension-contract), P65/P66/P67/P68 (primer authoring + dispatch), P69 (F1 cap-stone proof, S3-185).

## Overview: the two-contract architecture

SVP separates archetype-specific knowledge into two orthogonal contracts:

1. **Manifest schema (BEHAVIOR contract).** A JSON manifest at `scripts/toolchain_defaults/<archetype>.json` declares what the archetype *does* — environment tooling, package lists, primer paths, file-structure patterns, command templates, and quality-gate compositions. The schema is documented at `references/toolchain_manifest_schema.md` and enforced mechanically by `scripts/validate_toolchain_schema.py` (10 checks; pure-Python; stdlib only).

2. **`LANGUAGE_REGISTRY` (DISPATCH contract).** A Python dict in `scripts/language_registry.py` maps the language id to a registry entry that declares what the archetype *dispatches to* — the stub generator, the test-output parser, the quality runner, the agent prompts. Dispatch keys (`stub_generator_key`, `test_output_parser_key`, `quality_runner_key`) reference per-language implementations elsewhere in the codebase.

After rounds A-E, adding a new language archetype to SVP requires:

- **1 toolchain manifest file** (the BEHAVIOR contract instance)
- **5 primer markdown files** (optional but recommended; one per agent role)
- **1 `LANGUAGE_REGISTRY` entry** (the DISPATCH contract instance)
- **0 dispatch-code edits** in `prepare_task` or `write_delivered_claude_md` — the E2/E3 helpers (`_get_language_architecture_primer`, `_get_orchestrator_break_glass_primer_text`) iterate the manifest's `language_architecture_primers` keys at lookup time and pick up any populated archetype automatically.
- **0 audit-code edits** — the C3 dep-reachability check (`audit_blueprint_contracts`) is generic and uses the manifest's package list as the baseline.

The synthetic Rust archetype at `scripts/primers/rust/` and `scripts/toolchain_defaults/rust_cargo_test.json` exercises the SCHEMA half end-to-end. F1 does NOT register Rust in `LANGUAGE_REGISTRY` — registering it would require implementing a stub generator, test parser, and quality runner for Rust, which is out of scope. The schema-conformance test at `tests/regressions/test_s3_185_synthetic_rust_archetype.py` documents this dispatch boundary explicitly.

## The manifest schema (BEHAVIOR contract)

Field-by-field semantics live in `references/toolchain_manifest_schema.md`. Summary:

**Required top-level keys:**
- `toolchain_id` — string; MUST equal the filename stem (e.g., `"rust_cargo_test"` for `rust_cargo_test.json`). Caught by validator check 10.
- `language` — object: `name`, `extension`, `version_constraint` (all required); optional `signature_parser`, `stub_body`.
- `environment` — object: `tool`, `run_prefix`, `create_command`, `install_command`, `cleanup_command` (all required); optional `install_dev`, `verify_commands`. When `verify_commands` is present, every entry MUST use `{run_prefix}` as a template prefix (validator check 3).
- `quality` — object: `formatter` / `linter` / `type_checker` (each carrying tool-name and command templates), `packages` (list of strings), `gate_a` / `gate_b` / `gate_c` (lists of operation references resolved by `get_gate_composition`).
- `testing` — object: `tool`, `run_command`, `framework_packages` (list, required); commonly also `run_coverage`, `file_pattern`, `unit_flags`, `project_flags`, `pass_fail_pattern`, `collection_error_indicators`.
- `file_structure` — object: `source_dir_pattern`, `test_dir_pattern`, `source_extension`, `test_extension`.

**Optional top-level keys:**
- `packaging` — object describing build/packaging tooling.
- `vcs` — object describing version-control commands.
- `templated_helpers` — list of `{src, dest}` entries; `src` MUST live under `scripts/toolchain_defaults/templates/` (validator check 8).
- `language_architecture_primers` — object mapping agent role to primer markdown file path. Allowed sub-keys: `blueprint_author`, `implementation_agent`, `test_agent`, `coverage_review`, `orchestrator_break_glass`. Per-key null is allowed; non-null paths are checked for on-disk existence by validator check 9 when invoked with a `project_root`.

**Validator invocation.** Run from the workspace root:

```
python scripts/validate_toolchain_schema.py
```

This validates every manifest under `scripts/toolchain_defaults/*.json` and exits 0 on full conformance, 1 on any violations. The `--manifests-dir` flag points at an alternative directory (used by tests that author bogus manifests into a temp directory).

## The `LANGUAGE_REGISTRY` entry (DISPATCH contract)

The registry lives at `scripts/language_registry.py`. Each entry is a complete dispatch specification. Required keys for a full-language entry (see `FULL_REQUIRED_KEYS` in the registry source):

- **Identity:** `id`, `display_name`, `file_extension`
- **Filesystem:** `source_dir`, `test_dir`, `test_file_pattern`
- **Build-time toolchain:** `toolchain_file` (points back at the manifest filename), `environment_manager`, `test_framework`, `version_check_command`
- **Code generation:** `stub_sentinel`, `stub_generator_key`, `test_output_parser_key`, `quality_runner_key`
- **Component support:** `is_component_only`, `compatible_hosts`, `bridge_libraries`
- **Error detection:** `collection_error_indicators`
- **Hooks:** `authorized_write_dirs`
- **Delivery defaults:** `default_delivery`, `default_quality`
- **Validation sets:** `valid_linters`, `valid_formatters`, `valid_type_checkers`, `valid_source_layouts`
- **Delivery structure:** `environment_file_name`, `project_manifest_file`, `gitignore_patterns`, `entry_point_mechanism`, `quality_config_mapping`, `non_source_embedding`
- **Agent prompts:** `agent_prompts` (keyed by agent type)

The existing `python` and `r` entries are templates. Component-only entries (e.g., `stan`) use a smaller schema controlled by `COMPONENT_REQUIRED_KEYS`.

The dispatch keys (`stub_generator_key`, `test_output_parser_key`, `quality_runner_key`) reference dispatch tables distributed across the pipeline units. A full-language registration requires implementing entries in those tables; a component-only registration declares `required_dispatch_entries` listing only the dispatch keys the component needs.

## The five primers (per archetype)

The toolchain manifest's `language_architecture_primers` field maps the five agent roles to markdown files:

```json
"language_architecture_primers": {
  "blueprint_author":         "scripts/primers/<archetype>/blueprint_author.md",
  "implementation_agent":     "scripts/primers/<archetype>/implementation_agent.md",
  "test_agent":               "scripts/primers/<archetype>/test_agent.md",
  "coverage_review":          "scripts/primers/<archetype>/coverage_review.md",
  "orchestrator_break_glass": "scripts/primers/<archetype>/orchestrator_break_glass.md"
}
```

**Per-key null is allowed.** A manifest may declare some roles and leave others null; the dispatch helpers no-op on null. This permits role-by-role partial rollout.

**Dispatch.** Two helpers consume the field:

- `_get_language_architecture_primer(project_root, state, agent_type)` — invoked at `prepare_task_prompt` time (Unit 13) for the four task-prompt-bound agents (`blueprint_author`, `implementation_agent`, `test_agent`, `coverage_review`). E2 (S3-182) wires this.
- `_get_orchestrator_break_glass_primer_text(project_root, profile)` — invoked at Stage 5 child CLAUDE.md generation (Unit 23) for the orchestrator role. E3 (S3-183) wires this.

Both helpers iterate the manifest's keys at lookup time and pick up any populated archetype automatically. Adding a primer set for a new archetype requires zero edits to the helpers. See P66 (per-archetype prepare_task dispatch), P67 (orchestrator primer at Stage 5 delivery), and P68 (second-archetype authoring rides existing wiring).

## Worked example: Rust (synthetic, NOT registered)

The synthetic Rust archetype demonstrates the SCHEMA contract end-to-end. It is intentionally NOT registered in `LANGUAGE_REGISTRY` — the demonstration is content-only.

**Manifest:** `scripts/toolchain_defaults/rust_cargo_test.json`. Schema-conformant. Realistic Rust tooling: `cargo`, `cargo-tarpaulin`, `rustfmt`, `clippy`. The full content is reproduced below.

```json
{
  "toolchain_id": "rust_cargo_test",
  "environment": {
    "tool": "rustup",
    "run_prefix": "",
    "create_command": "rustup toolchain install {rust_version}",
    "install_command": "cargo build",
    "install_dev": "cargo build --all-features",
    "cleanup_command": "cargo clean",
    "verify_commands": [
      "{run_prefix} cargo --version",
      "{run_prefix} rustc --version"
    ]
  },
  "quality": {
    "formatter": {
      "tool": "rustfmt",
      "format": "{run_prefix} cargo fmt {target}",
      "check": "{run_prefix} cargo fmt --check {target}"
    },
    "linter": {
      "tool": "clippy",
      "light": "{run_prefix} cargo clippy {target} -- -W clippy::all",
      "heavy": "{run_prefix} cargo clippy {target} -- -D warnings",
      "check": "{run_prefix} cargo clippy {target} -- -D warnings"
    },
    "type_checker": {
      "tool": "rustc",
      "check": "{run_prefix} cargo check {target}"
    },
    "packages": ["rustfmt", "clippy", "cargo-tarpaulin"],
    "gate_a": ["formatter.format", "linter.light"],
    "gate_b": ["formatter.format", "linter.heavy", "type_checker.check"],
    "gate_c": ["formatter.check", "linter.check", "type_checker.check"]
  },
  "testing": {
    "tool": "cargo-test",
    "run_command": "{run_prefix} cargo test {test_path}",
    "run_coverage": "{run_prefix} cargo tarpaulin --out Json --output-dir target/tarpaulin",
    "framework_packages": ["cargo-tarpaulin"]
  },
  "language": {
    "name": "rust",
    "extension": ".rs",
    "version_constraint": ">=1.70",
    "stub_body": "unimplemented!()"
  },
  "file_structure": {
    "source_dir_pattern": "src/unit_{n}",
    "test_dir_pattern": "tests/unit_{n}",
    "source_extension": ".rs",
    "test_extension": ".rs"
  },
  "language_architecture_primers": {
    "blueprint_author":         "scripts/primers/rust/blueprint_author.md",
    "implementation_agent":     "scripts/primers/rust/implementation_agent.md",
    "test_agent":               "scripts/primers/rust/test_agent.md",
    "coverage_review":          "scripts/primers/rust/coverage_review.md",
    "orchestrator_break_glass": "scripts/primers/rust/orchestrator_break_glass.md"
  }
}
```

(Some optional fields have been elided for brevity; the on-disk file is the source of truth.)

**Primers:** `scripts/primers/rust/blueprint_author.md`, `implementation_agent.md`, `test_agent.md`, `coverage_review.md`, `orchestrator_break_glass.md`. Each is ~40-80 lines following the same five-section structure as the R and Python primers (Purpose / Architectural rules / Anti-patterns / Refactor patterns / Coverage caveat). Each opens with the distinctive header `# Rust Architectural Primer — <Role>`.

The Rust primers cover:

- **Cargo package layout** (`Cargo.toml`, `src/lib.rs` vs `src/main.rs`, multi-crate workspaces).
- **Test placement** (`#[cfg(test)] mod tests` for unit tests vs `tests/<name>.rs` for integration tests; `cargo test` runs both with different visibility rules).
- **Test invocation** (`cargo test` is canonical; `cargo nextest` is faster but coverage attribution differs).
- **Path resolution** (`env!("CARGO_MANIFEST_DIR")` for stable paths; `tempfile::tempdir()` for scratch space).
- **Coverage tooling** (`cargo-tarpaulin` Linux-only; `cargo-llvm-cov` cross-platform; both attribute via debuginfo, not via in-source instrumentation, so the attribution-loss vectors differ from R's covr or Python's coverage.py).
- **Anti-patterns** (`#[cfg(coverage)]` macro hacks, subprocess `Command::new("cargo")` recursion, `std::env::set_current_dir()`).
- **Coverage attribution-loss vectors** specific to Rust: subprocess (cargo invoking child cargo), proc-macros (procedural macros expand at compile time, mapping coverage to invocation sites rather than macro body lines), conditional compilation (`#[cfg(not(test))]` and feature gates exclude code at compile time).

**Test:** `tests/regressions/test_s3_185_synthetic_rust_archetype.py` — 8 tests covering manifest validation, primer existence, distinctive header marker, dispatch-contract boundary, validator's bogus-path rejection, and doc existence.

**The dispatch boundary.** The schema-conformance test contains:

```python
def test_rust_is_not_in_language_registry():
    from scripts.language_registry import LANGUAGE_REGISTRY
    assert "rust" not in LANGUAGE_REGISTRY

def test_load_toolchain_raises_keyerror_for_rust():
    from scripts.toolchain_reader import load_toolchain
    with pytest.raises(KeyError):
        load_toolchain(workspace_root, "rust")
```

These two assertions document the dispatch-contract boundary: the manifest exists and conforms to the schema, but `LANGUAGE_REGISTRY` does not know about Rust, so `load_toolchain(root, "rust")` raises `KeyError("Unknown language: rust")`. Real Rust support would require:

1. Implementing a stub generator for Rust (parses signatures from `.rs` source via `syn` or equivalent; emits stubs with `unimplemented!()` bodies).
2. Implementing a test-output parser that recognizes `cargo test` output (the `pass_fail_pattern` regex captures the count, but the parser also needs to classify collection errors via `collection_error_indicators`).
3. Implementing a quality runner that invokes `cargo fmt`, `cargo clippy`, and `cargo check` per the manifest's `quality.gate_*` compositions.
4. Adding the registry entry with `stub_generator_key: "rust"`, `test_output_parser_key: "rust"`, `quality_runner_key: "rust"`, plus the full set of `FULL_REQUIRED_KEYS` from `language_registry.py`.

None of those four implementations is in F1 scope. F1 ships the SCHEMA half only.

## Step-by-step: adding a real new archetype

When you want to add a new archetype that ships as real (not synthetic), follow these seven steps:

1. **Author the manifest** at `scripts/toolchain_defaults/<archetype>.json`. Use the synthetic Rust manifest at `scripts/toolchain_defaults/rust_cargo_test.json` or one of the existing `python_conda_pytest.json` / `r_conda_testthat.json` manifests as a starting template. Set `toolchain_id` to the filename stem.

2. **Run the schema validator** to confirm structural conformance:

   ```
   python scripts/validate_toolchain_schema.py
   ```

   This catches missing required keys, malformed `verify_commands` templates, misplaced `templated_helpers.src`, unknown `language_architecture_primers` sub-keys, and `toolchain_id` mismatches with filename stem.

3. **Author the 5 primer markdown files** at `scripts/primers/<lang>/<role>.md`. Each ~25-80 lines following the five-section structure (Purpose / Architectural rules / Anti-patterns / Refactor patterns / Coverage caveat). Each MUST start with `# <Lang> Architectural Primer — <Role>`. Mirror the existing R primers at `scripts/primers/r/` and Python primers at `scripts/primers/python/`.

4. **Re-run the validator** with primer-existence checks now active. The validator's CLI walks up from the manifests directory to locate the project root and invokes `validate_manifest(..., project_root=...)`, which checks that every non-null primer path resolves to an existing file. Bogus paths surface as a structured error naming the missing path.

5. **Add the `LANGUAGE_REGISTRY` entry** in `scripts/language_registry.py`. Use the existing `python` or `r` entries as templates. Set the dispatch keys to references your unit implementations will provide. Set `compatible_hosts: []` for full languages and a non-empty list for component-only entries.

6. **Implement the dispatch keys** in their respective units: signature parser (Unit 9), stub generator (Unit 10), test-output parser (Unit 17), quality runner (Unit 14), project assembler (Unit 23). Each must be registered in its dispatch table keyed by `stub_generator_key` / `test_output_parser_key` / `quality_runner_key` / etc. from your registry entry.

7. **Run pytest** from the workspace AND the repo to confirm zero regressions:

   ```
   pytest -x
   ```

   Both invocations must report 0 fail / 0 skip. Failures in one but not the other indicate stale test files or a sync issue.

## References

- `references/toolchain_manifest_schema.md` — field-by-field schema specification (canonical).
- `scripts/validate_toolchain_schema.py` — pure-Python schema validator (10 checks).
- `scripts/language_registry.py` — dispatch contract (`LANGUAGE_REGISTRY`).
- `scripts/toolchain_reader.py::load_toolchain` — runtime entry point that reads a manifest by language id.
- `scripts/primers/rust/` — the synthetic Rust archetype's 5 primer files (worked example).
- `scripts/toolchain_defaults/rust_cargo_test.json` — the synthetic Rust archetype's manifest (worked example).
- `tests/regressions/test_s3_185_synthetic_rust_archetype.py` — the schema-conformance test that demonstrates manifest validation and the dispatch-contract boundary.
- Pattern P58 — schema-as-extension-contract.
- Pattern P65 — Language-Archetype-Specific Architectural Knowledge In Primer Files External To Agent Definitions (S3-181).
- Pattern P66 — Per-Archetype × Per-Agent Primer Dispatch Centralizes Through The Toolchain Manifest (S3-182).
- Pattern P67 — The Orchestrator Primer Wires Through Stage 5 Delivery, Not prepare_task (S3-183).
- Pattern P68 — Adding A Second Archetype Primer Set Is A Content-Only Cycle Once Dispatch Is Wired (S3-184).
- Pattern P69 — F1 cap-stone proof: schema half is content-only on dispatch side; dispatch half (stub generator + test parser + quality runner) is its own implementation effort (S3-185).

## Common pitfalls

- **`toolchain_id` does not match the filename stem.** Validator check 10 catches this. The most common cause is renaming the file without updating the JSON, or copy-pasting from a template manifest and forgetting to edit the id.

- **A primer path string is set but the file does not exist.** Validator check 9 (when `project_root` is supplied) catches this. The most common cause is a typo in the path or a forgotten `git add` for the primer file. The CLI auto-supplies `project_root` by walking up from the manifests directory; the test framework also exercises the `project_root=None` mode for unit-test isolation.

- **Forgetting to register the language in `LANGUAGE_REGISTRY`.** The manifest can validate clean and the primers can exist, but `load_toolchain(root, "<lang>")` raises `KeyError` because the registry entry is missing. The synthetic Rust archetype intentionally lives in this state as a worked example of the dispatch-contract boundary; real archetypes must add the registry entry.

- **Half-implementing the dispatch keys.** A registry entry that names `stub_generator_key: "<lang>"` but lacks the corresponding entry in the stub-generator dispatch table fails at Stage 3 setup. Catch this by running pytest before merging — the registry self-validation on import (`_validate_registry_at_import` in `language_registry.py`) catches missing required keys, but does not chase dispatch-table entries; downstream unit tests do.

- **`environment.verify_commands` entries that don't use `{run_prefix}`.** Validator check 3 catches this. Every entry must template `{run_prefix}` so commands run inside the isolated environment, not on the host shell.

- **`templated_helpers.src` paths that don't live under `scripts/toolchain_defaults/templates/`.** Validator check 8 catches this. The convention was locked in S3-174 to keep all helper template files discoverable in one place.
