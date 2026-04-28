# SVP Toolchain Manifest Schema

This document is the canonical schema specification for SVP toolchain manifest files. Each archetype (python_project, r_project, etc.) has a manifest at `scripts/toolchain_defaults/<id>.json` conforming to this schema.

The reader is `scripts/toolchain_reader.py::load_toolchain` (derived from `src/unit_4/stub.py`).

## Top-level keys

| Key | Type | Required | Semantics |
|---|---|---|---|
| `toolchain_id` | string | yes | Unique identifier (e.g., "r_conda_testthat", "python_conda_pytest") |
| `language` | object | yes | Language metadata. See "language object" below. |
| `environment` | object | yes | Env tool, run_prefix, lifecycle commands. See "environment object" below. |
| `quality` | object | yes | Quality tooling config. See "quality object" below. |
| `testing` | object | yes | Test runner config. See "testing object" below. |
| `packaging` | object | optional | Build/packaging config (Python: pyproject.toml; R: DESCRIPTION). |
| `vcs` | object | optional | Version control commands. |
| `file_structure` | object | yes | Source/test directory + extension patterns. |
| `templated_helpers` | list[object] | optional | Files copied into project at infrastructure setup. See "templated_helpers" below. |
| `language_architecture_primers` | object | optional | **NEW IN 2.2 (S3-174)**. Per-agent primer paths for archetype-specific architectural guidance. See "language_architecture_primers" below. |

## language object

`{name: string, extension: string (e.g. ".R"), version_constraint: string (e.g. ">=4.3"), signature_parser?: string, stub_body?: string}`

The `name` field is the canonical language identifier (lowercase, e.g. `"python"`, `"r"`). The `extension` field includes the leading dot. Optional `signature_parser` and `stub_body` fields are dispatch-key references back into Unit 9 / Unit 10 dispatch tables.

## environment object

`{tool: "conda" | "venv" | "renv", run_prefix: string, create_command: string, install_command: string, install_dev?: string, cleanup_command: string, verify_commands?: list[string]}`

The `run_prefix` is the templated command prefix that wraps every other command run inside the env (e.g., `conda run -n {env_name}`). The `verify_commands` list is consumed by `verify_toolchain_ready` (Unit 4, S3-160) — see the verify_commands convention below.

`verify_commands` is **optional** for renv-path manifests where env verification is handled by the renv lifecycle itself. **Required** for conda-path manifests.

## quality object

`{formatter: object, linter: object, type_checker: object, packages: list[string], gate_a: list[string], gate_b: list[string], gate_c: list[string]}`

Each tool sub-object (`formatter`, `linter`, `type_checker`) carries `{tool: string, command_check?: string, command_fix?: string}`. The three gate lists (`gate_a`, `gate_b`, `gate_c`) are ordered lists of operation dicts consumed by `get_gate_composition`. Operation names are qualified with `"quality."` before resolution (Unit 15).

## testing object

`{tool: string, run_command: string, run_coverage: string, framework_packages: list[string], file_pattern?: string, ...}`

`run_command` is the test runner invocation; `run_coverage` is the coverage runner invocation. Both are templated and pass through `resolve_command`.

## file_structure object

`{source_dir_pattern: string, test_dir_pattern: string, source_extension: string, test_extension: string}`

Used by Unit 11 infrastructure setup and Unit 23 project assembly to construct source / test paths from blueprint Unit numbers.

## templated_helpers

A list of `{src: string, dest: string}` entries. Files are copied from `src` (relative to workspace root) into the target project at `dest` (project-relative path) during infrastructure setup.

**CONVENTION (LOCKED IN S3-174)**: `src` MUST live under `scripts/toolchain_defaults/templates/<helper_name>`. Centralized location; discoverable; version-tracked alongside the manifest.

Example:
```json
"templated_helpers": [
  { "src": "scripts/toolchain_defaults/templates/helper-svp.R", "dest": "tests/testthat/helper-svp.R" }
]
```

## language_architecture_primers (NEW IN 2.2 — S3-174)

An object mapping agent role to primer markdown file path. Used by:
- `prepare_task` helpers to conditionally append archetype-specific architectural guidance to agent task prompts (cycles E1-E4 wire this).
- Stage 5 delivery to embed the orchestrator primer in the delivered child project's generated CLAUDE.md (cycle E3).

Schema:
```json
"language_architecture_primers": {
  "blueprint_author": "scripts/primers/<archetype>/blueprint_author.md",
  "implementation_agent": "scripts/primers/<archetype>/implementation_agent.md",
  "test_agent": "scripts/primers/<archetype>/test_agent.md",
  "coverage_review": "scripts/primers/<archetype>/coverage_review.md",
  "orchestrator_break_glass": "scripts/primers/<archetype>/orchestrator_break_glass.md"
}
```

All five sub-keys are optional. When present, prepare_task appends the named primer's content to the corresponding agent's task prompt; when absent, no archetype-specific augmentation occurs (current behavior).

The `orchestrator_break_glass` primer is the diagnostic-flavored subset of the archetype's architectural rules — it guides the orchestrator (main session) when in break-glass mode investigating an archetype-specific bug. It is embedded in the child project's CLAUDE.md at Stage 5 delivery so the orchestrator inherits it on session boot.

## verify_commands convention (LOCKED IN S3-174)

Every command in `environment.verify_commands` MUST use `{run_prefix}` as a template prefix:

```json
"verify_commands": [
  "{run_prefix} R --version",
  "{run_prefix} Rscript -e 'library(testthat)'"
]
```

`resolve_command` substitutes `{run_prefix}` with the manifest's `environment.run_prefix` value (e.g., `conda run -n {env_name}`). This ensures verify commands run inside the same isolated environment as the rest of the toolchain. Raw shell commands without `{run_prefix}` are forbidden.

## Reader contract

`scripts/toolchain_reader.py::load_toolchain(project_root, language?)` reads either:
- Layer 1 (pipeline-level): `<project_root>/toolchain.json` if `language` is None.
- Layer 2 (language-specific default): `<project_root>/scripts/toolchain_defaults/<toolchain_file>` where `toolchain_file` is looked up from `LANGUAGE_REGISTRY` for the given language.

The function returns the manifest as `Dict[str, Any]` for downstream consumers.

`scripts/toolchain_reader.py::resolve_command` substitutes `{run_prefix}`, `{env_name}`, `{python_version}`, `{flags}`, `{target}` in single-pass order. Single substitution; no recursion.

## Existing manifests (as of S3-174)

Three manifests at `scripts/toolchain_defaults/`:
- `python_conda_pytest.json`
- `r_conda_testthat.json`
- `r_renv_testthat.json`

These were authored across multiple cycles (S3-160, S3-161, S3-119, etc.). Cycle A2 (S3-175) refactors them to fully conform to this schema and adds the `language_architecture_primers` field where applicable.

## Schema versioning

This schema is v1. Future versions add new fields additively (new optional keys; never remove or rename existing ones). Major version bumps require a deliberate cycle.

A1 (S3-174) was v1-draft; A2 (S3-175) corrections produce v1-stable. Future field additions are additive (new optional keys); breaking changes require deliberate version bump.

## Validator

The schema is enforced mechanically by `scripts/validate_toolchain_schema.py` (S3-175). Pure-Python (stdlib only); no external dependencies. Function signature:

`validate_manifest(manifest: Dict[str, Any]) -> List[str]` returns a list of human-readable error messages. Empty list means valid.

The validator performs 10 checks:
1. Top-level required keys: `toolchain_id`, `environment`, `quality`, `testing`, `language`, `file_structure`.
2. `environment` required nested: `tool`, `run_prefix`, `create_command`, `install_command`, `cleanup_command`.
3. `environment.verify_commands` (if present): non-empty list; every entry uses `{run_prefix}`.
4. `language` required nested: `name`, `extension`, `version_constraint`.
5. `testing` required nested: `tool`, `run_command`, `framework_packages` (list).
6. `quality.packages` is a list.
7. `file_structure` has all 4 required keys.
8. `templated_helpers` (if present): list of `{src, dest}`; each `src` MUST live under `scripts/toolchain_defaults/templates/`.
9. `language_architecture_primers` (if present): object with allowed sub-keys: `blueprint_author`, `implementation_agent`, `test_agent`, `coverage_review`, `orchestrator_break_glass`.
10. `toolchain_id` matches the filename stem (when validating from a known file path).

CLI invocation: `python scripts/validate_toolchain_schema.py` validates all manifests at `scripts/toolchain_defaults/*.json`; exits 0 on full conformance, 1 on any violations (with per-file error report).

## Cross-references

- S3-160 introduced `verify_commands` field.
- S3-161 changed R run_command/run_coverage to `devtools::test()` + `covr::environment_coverage()`.
- S3-174 (this) documents the schema and adds `language_architecture_primers`.
- S3-175 (cycle A2) refactors existing manifests to conform.
- S3-181..S3-184 (cycles E1-E4) author and wire the language architecture primers.
