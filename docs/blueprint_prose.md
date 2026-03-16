# SVP -- Stratified Verification Pipeline

## Technical Blueprint: Prose Descriptions (Tier 1)

**Date:** 2026-03-15
**Decomposes:** Stakeholder Specification v8.28
**Artifact Type:** Claude Code Plugin + Standalone Launcher
**Companion File:** The other `.md` file(s) in this blueprint directory (Tier 2 signatures + Tier 3 contracts)

---

## Preamble: Architecture Overview

SVP is a Claude Code plugin composed of mixed artifact types. The repository structure is:

```
svp-repo/                      <- repository root
|-- .claude-plugin/
|   +-- marketplace.json          <- marketplace catalog (repo root level)
|-- svp/                       <- plugin subdirectory
|   |-- .claude-plugin/
|   |   +-- plugin.json           <- plugin manifest
|   |-- skills/
|   |   +-- orchestration/
|   |       +-- SKILL.md          <- Unit 21
|   |-- agents/
|   |   |-- setup_agent.md               <- Unit 13
|   |   |-- stakeholder_dialog_agent.md  <- Unit 13
|   |   |-- blueprint_author_agent.md    <- Unit 13
|   |   |-- stakeholder_reviewer.md      <- Unit 14
|   |   |-- blueprint_checker.md         <- Unit 14
|   |   |-- blueprint_reviewer.md        <- Unit 14
|   |   |-- test_agent.md                <- Unit 15
|   |   |-- implementation_agent.md      <- Unit 15
|   |   |-- coverage_review_agent.md     <- Unit 15
|   |   |-- diagnostic_agent.md          <- Unit 16
|   |   |-- redo_agent.md                <- Unit 16
|   |   |-- help_agent.md                <- Unit 17
|   |   |-- hint_agent.md                <- Unit 17
|   |   |-- reference_indexing_agent.md  <- Unit 18
|   |   |-- integration_test_author.md   <- Unit 18
|   |   |-- git_repo_agent.md            <- Unit 18
|   |   |-- bug_triage_agent.md          <- Unit 19
|   |   +-- repair_agent.md              <- Unit 19
|   |-- commands/
|   |   |-- save.md                      <- Unit 20
|   |   |-- quit.md                      <- Unit 20
|   |   |-- help.md                      <- Unit 20
|   |   |-- hint.md                      <- Unit 20
|   |   |-- status.md                    <- Unit 20
|   |   |-- ref.md                       <- Unit 20
|   |   |-- redo.md                      <- Unit 20
|   |   |-- bug.md                       <- Unit 20
|   |   +-- clean.md                     <- Unit 20
|   |-- hooks/
|   |   |-- hooks.json                   <- Unit 12
|   |   +-- scripts/
|   |       |-- write_authorization.sh   <- Unit 12
|   |       |-- non_svp_protection.sh    <- Unit 12
|   |       +-- stub_sentinel_check.sh   <- Unit 12 (NEW IN 2.1)
|   |-- scripts/
|   |   |-- svp_config.py                <- Unit 1
|   |   |-- pipeline_state.py            <- Unit 2
|   |   |-- state_transitions.py         <- Unit 3
|   |   |-- ledger_manager.py            <- Unit 4
|   |   |-- blueprint_extractor.py       <- Unit 5
|   |   |-- stub_generator.py            <- Unit 6 (library)
|   |   |-- generate_stubs.py            <- Unit 6 (CLI wrapper)
|   |   |-- dependency_extractor.py      <- Unit 7 (library)
|   |   |-- setup_infrastructure.py      <- Unit 7 (CLI wrapper)
|   |   |-- hint_prompt_assembler.py     <- Unit 8
|   |   |-- prepare_task.py              <- Unit 9
|   |   |-- routing.py                   <- Unit 10
|   |   |-- update_state.py              <- Unit 10 (CLI wrapper)
|   |   |-- run_tests.py                 <- Unit 10 (CLI wrapper)
|   |   |-- run_quality_gate.py          <- Unit 10 (CLI wrapper, NEW IN 2.1)
|   |   |-- compliance_scan.py           <- Unit 23 (CLI wrapper)
|   |   |-- cmd_save.py                  <- Unit 11
|   |   |-- cmd_quit.py                  <- Unit 11
|   |   |-- cmd_status.py                <- Unit 11
|   |   |-- cmd_clean.py                 <- Unit 11
|   |   |-- svp_launcher.py              <- Unit 24
|   |   |-- toolchain_defaults/          <- Unit 22
|   |   |   |-- python_conda_pytest.json
|   |   |   +-- ruff.toml               <- NEW IN 2.1
|   |   +-- templates/                   <- Unit 22
|   |       |-- claude_md.py
|   |       |-- svp_config_default.json
|   |       |-- pipeline_state_initial.json
|   |       +-- readme_svp.txt
|   +-- README.md
|-- docs/                        <- Delivered documentation (spec Section 12.1)
|   |-- stakeholder_spec.md
|   |-- *.md                        <- blueprint files (discovered from blueprint/ directory)
|   |-- project_context.md
|   |-- history/                 <- Document version history
|   +-- references/              <- Reference documents and summaries
|-- tests/
|   +-- regressions/              <- carry-forward regression tests (copied by launcher)
|       |-- test_bug2_wrapper_delegation.py
|       |-- test_bug3_cli_argument_contracts.py
|       |-- test_bug4_status_line_contracts.py
|       |-- test_bug5_pytest_framework_deps.py
|       |-- test_bug6_collection_error_classification.py
|       |-- test_bug7_unit_completion_status_file.py
|       |-- test_bug8_sub_stage_reset_on_completion.py
|       |-- test_bug9_hook_path_resolution.py
|       |-- test_bug10_agent_status_prefix_matching.py
|       |-- test_bug11_delivered_repo_artifacts.py
|       |-- test_bug12_cmd_main_guards.py
|       |-- test_bug13_hook_schema_validation.py
|       |-- test_bug14_routing_action_block_commands.py
|       |-- test_bug15_gate_prepare_flag_mismatch.py
|       |-- test_bug16_same_file_copy_guard.py
|       |-- test_bug17_routing_gate_presentation.py
|       |-- test_bug18_stakeholder_spec_filename.py
|       |-- test_bug19_alignment_check_routing.py
|       |-- test_bug20_total_units_derivation.py
|       |-- test_bug21_stage3_sub_stage_routing.py
|       |-- test_bug17_stage5_repo_assembly_routing.py
|       |-- test_bug18_readme_carry_forward.py
|       |-- test_bug19_plugin_discovery_paths.py
|       |-- test_bug22_repo_sibling_directory.py
|       |-- test_bug23_stage1_spec_gate_routing.py  (unified Bug 41 -- filename uses post-delivery numbering)
|       |-- test_bug42_pre_stage3_state_persistence.py  (unified Bug 42 -- filename uses post-delivery numbering)
|       |-- test_bug43_stage2_blueprint_routing.py  (unified Bug 43 -- universal two-branch compliance)
|       |-- test_bug44_null_substage_dispatch.py  (Bug 44 -- dispatch_agent_status null sub_stage for test_agent)
|       |-- test_bug45_test_execution_dispatch.py  (Bug 45 -- dispatch_command_status test_execution advancement)
|       |-- test_bug46_coverage_dispatch.py  (Bug 46 -- dispatch_agent_status coverage_review advancement)
|       +-- test_bug47_unit_completion_double_dispatch.py  (Bug 47 -- COMMAND/POST separation)
|       +-- test_bug48_launcher_cli_contract.py           (Bug 48 -- launcher CLI contract)
|       +-- test_bug49_argparse_enumeration.py            (Bug 49 -- argparse enumeration)
|       +-- test_bug50_contract_sufficiency.py            (Bug 50 -- contract sufficiency)
|-- examples/                    <- Bundled example (SVP self-build only)
|   +-- game-of-life/            <- Unit 22
|       |-- stakeholder_spec.md
|       |-- blueprint_prose.md
|       |-- blueprint_contracts.md
|       +-- project_context.md
|-- src/                          <- SVP Python source code
+-- tests/                        <- SVP test suite
```

**Critical structural rules (learned from SVP 1.1 implementation):**
- All plugin component directories (`agents/`, `commands/`, `skills/`, `hooks/`, `scripts/`) must be at the `svp/` subdirectory root -- not at the repository root, and not nested inside `.claude-plugin/`.
- `plugin.json` is the only file inside `svp/.claude-plugin/`.
- `marketplace.json` lives in a separate `.claude-plugin/` directory at the **repository root** -- not inside the plugin subdirectory.
- `hooks/hooks.json` within the plugin requires a top-level `"hooks"` wrapper key (see Unit 12).

The SVP launcher (`svp` CLI tool, Unit 24) is distributed at `svp/scripts/svp_launcher.py` in the delivered repository. Although it is not a plugin component (it runs before Claude Code starts), it lives inside the plugin's `scripts/` directory. The `pyproject.toml` entry point references it as `svp.scripts.svp_launcher:main`.

**Critical assembly rule (learned from SVP 1.2 implementation):** During Stage 5 assembly, unit implementations must be relocated from their workspace paths (`src/unit_N/`) to their final paths as shown in this file tree. The file tree annotations (`<- Unit N`) are the authoritative mapping. The workspace `src/unit_N/stub.py` structure is never reproduced in the delivered repository. All imports referencing `src.unit_N` or `stub` must be rewritten to use final module paths -- but scripts delivered to `svp/scripts/` must use **bare imports** (e.g., `from pipeline_state import load_state`), NOT package imports (e.g., `from svp.scripts.pipeline_state import load_state`), because the launcher copies these scripts to project workspaces where they run with `PYTHONPATH=scripts`. The `svp.scripts.X` form is used ONLY in `pyproject.toml` entry points. Every script that is invoked directly via `python scripts/X.py` must include an `if __name__ == "__main__"` guard. See spec Section 12.1.1.

**Scripts synchronization rule:** Six units exist as both a canonical `src/unit_N/stub.py` and a runtime `scripts/` copy: Unit 1 (`svp_config.py`), Unit 2 (`pipeline_state.py`), Unit 4 (`ledger_manager.py`), Unit 5 (`blueprint_extractor.py`), Unit 8 (`hint_prompt_assembler.py`), and Unit 9 (`prepare_task.py`). The `src/unit_N/stub.py` is always canonical; the `scripts/` copy must match. When a canonical stub changes -- especially exported constants like `KNOWN_AGENT_TYPES` or public assembler functions -- the corresponding `scripts/` file must be updated in the same commit. The routing script checks `KNOWN_AGENT_TYPES` between `src/unit_9/stub.py` and `scripts/prepare_task.py` at startup and emits a stderr warning if they diverge.

**CLI wrapper rule (learned from SVP 1.2.1 bug triage):** Four units produce both a library module and one or more CLI wrapper scripts: Unit 6 (`stub_generator.py` + `generate_stubs.py`), Unit 7 (`dependency_extractor.py` + `setup_infrastructure.py`), Unit 10 (`routing.py` + `update_state.py` + `run_tests.py` + `run_quality_gate.py`), Unit 23 (`compliance_scan.py`), and no others. CLI wrapper scripts must be **thin wrappers that delegate to the canonical functions** defined in the library module -- they must NOT reimplement dispatch logic, test execution, or infrastructure orchestration inline.

**Cross-unit CLI contract (learned from SVP 1.2.1 bug triage):** Unit 10 (routing script) generates PREPARE and POST command strings that are executed as shell commands. The argument syntax in these commands constitutes a cross-unit contract: the receiving script (Unit 9 for PREPARE, Unit 10's own `update_state_main` for POST) must accept every argument that Unit 10 generates.

**CLI wrapper status line contract (learned from SVP 1.2.1 bug triage):** CLI wrapper scripts invoked as `run_command` actions must emit status lines from the vocabulary defined in Unit 10's `COMMAND_STATUS_PATTERNS`: `COMMAND_SUCCEEDED` on success, `COMMAND_FAILED: [details]` on failure. Quality gate wrappers (`run_quality_gate.py`) emit `COMMAND_SUCCEEDED` when all tools pass clean and `COMMAND_FAILED: quality residuals` when any tool reports issues after auto-fix.

**Mixed-artifact unit convention:** Units whose artifact category includes Markdown, JSON, shell scripts, or other non-Python deliverables must produce the complete content of each deliverable file as a Python string constant in their `src/unit_N/stub.py` implementation. The naming convention is `{FILENAME_UPPER}_CONTENT: str`. The git repo agent extracts these string constants during assembly and writes them as files to the paths specified in the blueprint file tree.

**Canonical pipeline artifact filenames (Bug 22 fix -- NEW IN 2.1):** All pipeline artifact filenames are defined as shared constants in Unit 1 (`ARTIFACT_FILENAMES`). Every component that produces or consumes a pipeline artifact must reference these constants -- never hardcode filenames independently. The canonical entries include: `stakeholder_spec.md`, `blueprint_dir` (directory name `blueprint`), `project_context.md`, `project_profile.json`, `pipeline_state.json`, `svp_config.json`, `toolchain.json`, `ruff.toml`, `svp_2_1_lessons_learned.md`. Blueprint files are NOT individually listed in `ARTIFACT_FILENAMES` -- the `blueprint_dir` entry points to the directory, and `discover_blueprint_files` dynamically finds all `.md` files within it. This supports both the single-file format (SVP 2.0 `blueprint.md`) and the split-file format (SVP 2.1 `blueprint_prose.md` + `blueprint_contracts.md`) without hardcoded assumptions.

**Dual write-path awareness (NEW IN 2.1):** Two independent write paths exist in the pipeline: agent writes (through Claude Code's Write tool, validated by `PreToolUse` hooks) and pipeline subprocess writes (quality auto-fix, assembly scripts, executed via `subprocess.run` from deterministic scripts). Hooks control the first path; they do not intercept the second. This is correct by design.

**Contract sufficiency invariant (Bug 50 fix):** Every Tier 3 behavioral contract must be sufficient for deterministic reimplementation -- if behavior depends on specific values (lookup tables, enum sets, magic numbers), those values must appear in Tier 2 invariants or Tier 3 contracts. See spec Section 3.16.

**Contract boundary rule (Bug 50 fix):** Internal helpers (underscore-prefixed, not imported cross-unit) must NOT appear in Tier 2 signatures. Observable behavioral details (lookup table values, validation sets, algorithm parameters) MUST appear in Tier 3 contracts. See spec Section 3.16.

### Dependency Graph

```
Unit 1:  SVP Configuration                               (no deps)
Unit 2:  Pipeline State Schema                            depends on: 1
Unit 3:  State Transition Engine                          depends on: 1, 2
Unit 4:  Ledger Manager                                   depends on: 1 (indirect -- caller passes config value)
Unit 5:  Blueprint Extractor                              (no deps)
Unit 6:  Stub Generator                                   depends on: 5
Unit 7:  Dependency Extractor and Import Validator         depends on: 1
Unit 8:  Hint Prompt Assembler                            (no deps)
Unit 9:  Preparation Script                               depends on: 1, 2, 4, 5, 8
Unit 10: Routing Script and Update State                  depends on: 1, 2, 3
Unit 11: Command Logic Scripts                            depends on: 1, 2, 4
Unit 12: Hook Configurations                              depends on: 2
Unit 13: Dialog Agent Definitions                         depends on: 4, 9
Unit 14: Review and Checker Agent Definitions             depends on: 9
Unit 15: Construction Agent Definitions                   depends on: 6, 9
Unit 16: Diagnostic and Classification Agent Definitions  depends on: 9
Unit 17: Support Agent Definitions                        depends on: 9
Unit 18: Utility Agent Definitions                        depends on: 9
Unit 19: Debug Loop Agent Definitions                     depends on: 9
Unit 20: Slash Command Files                              depends on: 10, 11
Unit 21: Orchestration Skill                              depends on: 10
Unit 22: Project Templates                                depends on: 1, 2, 10
Unit 23: Plugin Manifest, Structural Validation, and Compliance Scan  depends on: 1, (all preceding)
Unit 24: SVP Launcher                                     depends on: 12, 22
```

### SVP 2.1 Scope

SVP 2.1 adds quality gates, delivered quality configuration, changelog support, blueprint prose/contracts split, stub sentinel, proactive lessons learned use, and several bug fixes to the complete SVP 2.0 baseline:

1. **Pipeline Quality Guarantee (quality gates A, B, C):** Deterministic quality tool execution at defined points in the verification cycle. Auto-fix first, agent escalation for residuals. Four new sub-stages. Gate composition data-driven from `toolchain.json`.
2. **Delivered Quality Configuration:** The git repo agent generates quality tool configuration for the delivered project based on the human's preferences from the profile.
3. **Changelog Support:** Configurable changelog generation (Keep a Changelog or Conventional Changelog).
4. **Blueprint Directory Discovery (NEW):** Blueprint files are discovered dynamically from the `blueprint/` directory rather than hardcoded by name. The system supports any number of `.md` files (single `blueprint.md` for SVP 2.0 backward compatibility, or split `blueprint_prose.md` + `blueprint_contracts.md`, or any other arrangement). Affects Units 1, 3, 5, 7, 9, 14, 18, 23, 24.
5. **Stub Sentinel (NEW):** `__SVP_STUB__` marker in stub files. Affects Units 6, 12, and structural validation.
6. **Proactive Lessons Learned (NEW):** Test agent receives filtered historical failure patterns. Affects Units 9, 14.
7. **Bug fixes:** Bug 17 (hook schema), Bug 21 (two-branch routing), Bug 22 (canonical filenames), Bug 23 (alignment check), Bug 24 (total_units), Bug 25 (Stage 3 routing), Bug 26 (Stage 5 routing), Bug 28 (commit count), Bug 30 (README carry-forward), Bug 31 (launcher flag), Bug 32 (CLI subcommands), Bug 33 (quality gate operations), Bug 34 (toolchain portability), Bug 35 (routing output resolution), Bug 36 (stub generation sub-stage), Bug 37 (repo sibling directory), Bug 38 (Group B commands), Bug 39 (skill slash-command cycle), Bug 41 (Stage 1 routing + gate ID consistency), Bug 42 (pre-Stage-3 state persistence), Bug 43 (universal two-branch routing compliance), Bug 44 (dispatch_agent_status null sub_stage for test_agent), Bug 45 (dispatch_command_status test_execution advancement), Bug 46 (dispatch_agent_status coverage_review advancement), Bug 47 (unit_completion COMMAND/POST separation), Bug 48 (launcher CLI contract loss), Bug 49 (systemic bare argparse stubs), Bug 50 (contract sufficiency and boundary violations).
8. **Repo collision avoidance:** Existing repo directories renamed before new assembly.

SVP 2.1 carries forward 22 regression tests from prior builds and adds 12 new ones (test_bug13_hook_schema_validation.py, test_bug22_repo_sibling_directory.py, test_bug23_stage1_spec_gate_routing.py, test_bug42_pre_stage3_state_persistence.py, test_bug43_stage2_blueprint_routing.py, test_bug44_null_substage_dispatch.py, test_bug45_test_execution_dispatch.py, test_bug46_coverage_dispatch.py, test_bug47_unit_completion_double_dispatch.py, test_bug48_launcher_cli_contract.py, test_bug49_argparse_enumeration.py, test_bug50_contract_sufficiency.py), totaling 34 regression test files.

---

## Unit Definitions

---

## Unit 1: SVP Configuration

**Artifact category:** Python script

### Tier 1 -- Description

Defines three foundational data contracts and provides functions for loading, validating, and accessing all tunable parameters and tool commands. This unit manages: (1) `svp_config.json` -- the pipeline configuration schema, (2) `project_profile.json` -- the human's delivery preferences, and (3) `toolchain.json` -- the pipeline's build command templates. It also provides the canonical `derive_env_name` function used by all units that need environment name derivation, and the canonical `ARTIFACT_FILENAMES` dict that defines all pipeline artifact filenames (Bug 22 fix). The `ARTIFACT_FILENAMES` dict uses a `blueprint_dir` entry pointing to the blueprint directory (not individual filenames) -- blueprint files are discovered dynamically by `discover_blueprint_files` and loaded by `load_blueprint_content`. This discovery-based approach supports both the single-file format (SVP 2.0) and the split-file format (SVP 2.1) without hardcoded assumptions about the number or names of blueprint files. The `DEFAULT_PROFILE` includes the `quality` section with fields for linter, formatter, type_checker, import_sorter, and line_length. Implements spec Sections 6.4 (profile schema), 6.5 (toolchain schema), 7.5 (canonical filenames), 22.1, and 24.17.

---

## Unit 2: Pipeline State Schema and Core Operations

**Artifact category:** Python script

### Tier 1 -- Description

Defines the complete `pipeline_state.json` schema and provides creation, reading, writing, structural validation, and state recovery from completion markers. This is the single source of truth for deterministic routing, session recovery, and status reporting. Implements spec Sections 22.4 (state), 6.7 (resume/recovery), and 22.5 (resume behavior).

The state schema includes Stage 0 sub-stages (`hook_activation`, `project_context`, `project_profile`), Stage 1 sub-stages (`None` only -- routing uses `last_status.txt` for two-branch dispatch), Stage 2 sub-stages (`None`, `blueprint_dialog`, `alignment_check`) for the Bug 23 fix, where `None` is the valid initial sub-stage before the first blueprint dialog begins, quality gate sub-stages (`quality_gate_a`, `quality_gate_b`, `quality_gate_a_retry`, `quality_gate_b_retry`), Stage 4 sub-stages (`None` only), Stage 5 sub-stages (`None`, `repo_test`, `compliance_scan`, `repo_complete`) for the Bug 26 fix, the `debug_session` object for the debug permission reset (Bug 2 fix), redo-triggered profile revision sub-stages (`redo_profile_delivery`, `redo_profile_blueprint`) with snapshot capture, and `delivered_repo_path` for post-delivery operations.

---

## Unit 3: State Transition Engine

**Artifact category:** Python script

### Tier 1 -- Description

Validates preconditions and executes all state transitions: stage advancement, unit completion, fix ladder progression, pass history recording, unit-level rollback, document versioning (copy to history, write diff summary), debug session lifecycle (enter, authorize, exit), redo-triggered profile revision lifecycle (enter, snapshot, restore/discard), Stage 2 alignment check transitions (Bug 23 fix), quality gate state transitions (enter gate, advance to retry, fail-to-ladder), and delivered repo path recording. This unit contains the most complex business logic among the deterministic scripts -- it is the primary stage-gating mechanism.

Document versioning (Section 23) is included here because it is always triggered as part of a state transition, never independently. The `version_document` function accepts an optional `companion_paths` parameter (a list of `Path` objects). When `companion_paths` is not None and non-empty (used for the blueprint directory -- all discovered `.md` files are passed as companions), all files are versioned together atomically: it produces versioned copies and diff summaries for each file, treating them as a group sharing the same version number. When `companion_paths` is None (used for single-file documents like the stakeholder spec), only the primary file is versioned. The caller uses `discover_blueprint_files` from Unit 1 to determine which files to version.

Implements spec Sections 3.6 (state management), 10.13 (unit completion), 13 (`/svp:redo` rollback), 23 (document version tracking), 8.3 (alignment loop iteration tracking), 13.1 (redo profile revision state machine), 12.17.1 (debug permission reset), 10.12 (quality gate mechanism), 12.1 (delivered_repo_path), and 24.18 (alignment check failure mode).

---

## Unit 4: Ledger Manager

**Artifact category:** Python script

### Tier 1 -- Description

Manages JSONL conversation ledgers: append entries, read full ledger, compact, clear, and monitor size. Implements the compaction algorithm from spec Section 3.3 and the structured response format validation from spec Section 15.1. Also writes system-level `[HINT]` entries per Section 15.1. Unchanged from v1.0.

---

## Unit 5: Blueprint Extractor

**Artifact category:** Python script

### Tier 1 -- Description

Extracts a single unit's definition and upstream contract signatures from the blueprint for context-isolated agent invocations. The extracted content becomes part of the task prompt for the relevant subagent. This is a deterministic operation -- no LLM involvement. Implements spec Section 10.14.

Updated for directory-based blueprint discovery: `parse_blueprint`, `extract_unit`, `extract_upstream_contracts`, and `build_unit_context` accept a `blueprint_dir` parameter (the path to the blueprint directory) instead of individual file paths. These functions internally glob `blueprint_dir / "*.md"` to find all `.md` files in the directory, read and concatenate them, and parse units from the combined content. Unit 5 does not define its own discovery function -- standalone discovery is provided by `discover_blueprint_files` in Unit 1. Tier identification is content-based (`### Tier N` headings), not filename-based -- a single `blueprint.md` file works identically to multiple split files. The `include_tier1: bool` parameter (default `True`) controls whether Tier 1 description content is included. When `False`, Tier 1 content is excluded from the returned context, enabling token-efficient task prompts for the test and implementation agents. The `UnitDefinition` dataclass is unchanged -- it continues to carry all tiers; the parameter controls what is included in assembled context strings.

---

## Unit 6: Stub Generator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 1 -- Description

Parses machine-readable signatures from the blueprint using Python's `ast` module and produces Python stub files with `NotImplementedError` bodies. Also generates stubs or mocks for upstream dependencies based on their contract signatures. Implements spec Section 10.2, including the importability invariant (module-level `assert` statements are stripped) and the forward-reference guard.

Updated for stub sentinel: `generate_stub_source` must prepend `__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP` as the first non-import statement in every generated stub file. This sentinel is a machine-detectable marker whose absence from stub output is a Unit 6 contract violation.

Per the CLI argument enumeration invariant (Bug 49 fix), `main()` accepts `--blueprint`, `--unit`, `--output-dir`, and `--upstream` via argparse. See Tier 2 for full enumeration.

---

## Unit 7: Dependency Extractor and Import Validator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 1 -- Description

Scans all machine-readable signature blocks across all units in the blueprint directory, extracts every external import statement, produces a complete dependency list, creates the Conda environment, installs all packages (including quality tool packages from `toolchain.json`), and validates that every extracted import resolves. The `extract_all_imports` function takes `blueprint_dir` (the path to the blueprint directory) as its parameter and uses `discover_blueprint_files` from Unit 1 to find all `.md` files, then parses Tier 2 signature blocks from the combined content. Tool commands are read from `toolchain.json` via Unit 1's toolchain reader. Implements spec Sections 9 (Pre-Stage-3 Infrastructure Setup).

Per the CLI argument enumeration invariant (Bug 49 fix), `main()` accepts `--project-root` via argparse. See Tier 2 for full enumeration.

SVP 2.1 changes: installs `quality.packages` from `toolchain.json` alongside `testing.framework_packages`. Bug 24 fix: `total_units` is derived from the blueprint during infrastructure setup, not read from state. `derive_total_units` takes the blueprint directory path, uses `discover_blueprint_files` from Unit 1 to find all `.md` files, reads and concatenates their content, and counts `## Unit N:` headings. The function is agnostic to the number or names of blueprint files. All three blueprint-reading functions in Unit 7 (`extract_all_imports`, `derive_total_units`, `validate_dependency_dag`) use `discover_blueprint_files` from Unit 1 rather than globbing independently, because Unit 7 already depends on Unit 1 for `derive_env_name`, `load_toolchain`, and other configuration functions. This contrasts with Unit 5, which globs independently to preserve its zero-dependency status.

---

## Unit 8: Hint Prompt Assembler

**Artifact category:** Python script

### Tier 1 -- Description

Takes the raw hint content from a help agent's terminal output, the gate metadata, the receiving agent type, and the ladder position, and produces a wrapped `## Human Domain Hint (via Help Agent)` section for inclusion in the task prompt. Uses deterministic templates with variable substitution -- no LLM involvement. Implements spec Section 14.4. Unchanged from v1.0.

---

## Unit 9: Preparation Script

**Artifact category:** Python script

### Tier 1 -- Description

Assembles task prompt files for agent invocations and gate prompt files for human decision gates. Takes the agent type (or gate identifier), unit number, ladder position, and other parameters as input and produces a ready-to-use file at a specified path. This is the most complex deterministic script and requires elevated test coverage (spec Section 26). Implements spec Section 3.7 (explicit context loading) and Section 17.1 (PREPARE command).

SVP 2.0 expansion: extracts profile sections for agent task prompts. SVP 2.1 expansion: includes quality report in agent re-pass prompts; adds `quality` to blueprint author profile sections; references `ARTIFACT_FILENAMES` from Unit 1 for all artifact paths (Bug 22 fix).

Updated for directory-based blueprint discovery: task prompt assembly uses `get_blueprint_dir` (which returns `project_root / ARTIFACT_FILENAMES["blueprint_dir"]`) to locate the blueprint directory, then passes this directory path to `build_unit_context` (Unit 5). For test agent and implementation agent invocations, passes `include_tier1=False` (excluding Tier 1 descriptions). For diagnostic agent, help agent, and blueprint checker, passes `include_tier1=True`. The `load_blueprint` function uses `load_blueprint_content` from Unit 1 to discover and concatenate all blueprint files. No hardcoded blueprint filenames.

Updated for proactive lessons learned: when assembling the test agent's task prompt, filters the lessons learned document for entries relevant to the current unit. Filtering is deterministic -- pure text matching by unit number and pattern classification. Matched entries are appended under a heading: "Historical failure patterns for this unit -- write tests that probe these behaviors." If no matches, this section is omitted.

Updated for gate ID consistency (Bug 41 fix): `ALL_GATE_IDS` must include every gate ID in the pipeline -- including `gate_1_1_spec_draft` and `gate_1_2_spec_post_review`. The set of gate IDs in `ALL_GATE_IDS` must be identical to the set in `GATE_RESPONSES` in Unit 10.

Per the CLI argument enumeration invariant (Bug 49 fix), `main()` accepts `--project-root`, `--agent`, `--gate`, `--unit`, `--output`, `--ladder`, `--revision-mode`, `--quality-report` via argparse. See Tier 2 for full enumeration.

---

## Unit 10: Routing Script and Update State

**Artifact category:** Python script (library + 3 CLI wrappers)

### Tier 1 -- Description

Reads `pipeline_state.json` and outputs the exact next action as a structured key-value block. Handles every stage, sub-stage, gate, and agent transition in the pipeline. Includes `update_state_main` (CLI wrapper for POST commands), `run_tests_main` (CLI wrapper for test execution), and `run_quality_gate_main` (CLI wrapper for quality gate execution, NEW IN 2.1).

Per the CLI argument enumeration invariant (Bug 49 fix), all three CLI wrappers (`update_state_main`, `run_tests_main`, `run_quality_gate_main`) have argparse arguments enumerated in Tier 2.

This is the heaviest-change unit in SVP 2.1. It must implement the two-branch routing invariant for every sub-stage with an agent-to-gate transition (Section 3.6), full Stage 0 sub-stage routing (hook activation, project context, project profile) including `PROJECT_CONTEXT_REJECTED` to `pipeline_held`, full Stage 1 two-branch routing with Gates 1.1 and 1.2 (Bug 41 fix), full Stage 2 routing with blueprint dialog, alignment check, and Gates 2.1/2.2/2.3 (Bug 23 fix), full Stage 3 sub-stage routing including diagnostic escalation two-branch check (fix ladder `"diagnostic"` to Gate 3.2), coverage_review two-branch check with auto-format flow (Bug 25 fix), full Stage 4 two-branch routing (Bug 43 fix), full Stage 5 sub-stage routing (Bug 26 fix), quality gate routing paths, redo profile sub-stage routing for both `redo_profile_delivery` and `redo_profile_blueprint` (Bug 43 fix), post-delivery debug loop routing (Gates 6.0 through 6.5) including `stage3_reentry` phase routing for FIX UNIT path, cross-agent `HINT_BLUEPRINT_CONFLICT` status detection and `gate_hint_conflict` dispatch, gate ID consistency with Unit 9 (Bug 41 fix -- `GATE_RESPONSES` is the implementation name for the spec's `GATE_VOCABULARY`), repo collision avoidance on Stage 5 entry, routing output resolution (Bug 35 fix), and Stage 3 dispatch completeness (Bugs 44-47 fix): `dispatch_agent_status` for `test_agent` must handle `sub_stage in (None, "test_generation")` (Bug 44), `dispatch_command_status` for `test_execution` must advance `red_run` to `implementation` on `TESTS_FAILED` and `green_run` to `coverage_review` on `TESTS_PASSED` (Bug 45), `dispatch_agent_status` for `coverage_review` must advance to `unit_completion` on `COVERAGE_COMPLETE` (Bug 46), and `unit_completion` COMMAND must not embed state update calls (Bug 47). Implements spec Sections 3.6, 6, 7, 8, 10.11, 10.13, 12.17, 13, 14.4, 17, 18, and 22.4.

---

## Unit 11: Command Logic Scripts

**Artifact category:** Python script

### Tier 1 -- Description

Implements the four Group A utility command scripts: `cmd_save.py`, `cmd_quit.py`, `cmd_status.py`, and `cmd_clean.py`. These are invoked directly by slash commands without subagent involvement. Implements spec Section 13.1. The `cmd_status.py` now includes one-line profile summary and active quality gate status (NEW IN 2.1).

---

## Unit 12: Hook Configurations

**Artifact category:** JSON + Shell scripts (non-Python deliverables)

### Tier 1 -- Description

Defines the Claude Code hook configuration files: `hooks.json` (hook declarations), `write_authorization.sh` (state-gated write control), `non_svp_protection.sh` (non-SVP session protection), and `stub_sentinel_check.sh` (PostToolUse stub sentinel hook, NEW IN 2.1). Implements spec Sections 19 and 4.2.

The stub sentinel hook is a `PostToolUse` command hook that matches Write tool calls to Python source files under `src/unit_N/` paths. The handler greps the written file content for `__SVP_STUB__`. If found, the hook exits with code 2 and emits an explanatory message blocking the write. This is a second enforcement point for stub sentinel detection, before structural validation.

SVP 2.1 additions: `ruff.toml` permanently read-only, delivered repo path writable during authorized debug sessions, lessons learned document writable during authorized debug sessions, `PostToolUse` stub sentinel hook.

---

## Unit 13: Dialog Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three dialog agents: Setup Agent, Stakeholder Dialog Agent, and Blueprint Author Agent. Each file is a Markdown document with YAML frontmatter that becomes the agent's system prompt. These agents use the ledger-based multi-turn interaction pattern. Implements spec Sections 6.3, 6.4, 7.3, 7.4, 7.6, and 8.1.

SVP 2.0 expansion: Setup agent gains project profile dialog (five areas), Gate 0.3, targeted revision mode.
SVP 2.1 expansion: Setup agent gains Area 5 (quality preferences) and changelog question in Area 1. Setup agent's system prompt must include all four UX behavioral rules (plain-language explanations, best-option recommendations, sensible defaults, progressive disclosure) as numbered requirements. Setup agent's system prompt must also embed the complete `project_profile.json` schema structure with exact canonical field names matching `DEFAULT_PROFILE` in Unit 1, so the agent's JSON output uses identical section and field names. Blueprint author receives `quality` profile section.

---

## Unit 14: Review and Checker Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three review/checker agents: Stakeholder Spec Reviewer, Blueprint Checker, and Blueprint Reviewer. Single-shot agents that produce a critique or verdict. Implements spec Sections 7.4, 8.2, and "report most fundamental level."

SVP 2.0 expansion: Blueprint Checker gains Layer 2 preference coverage validation.
SVP 2.1 expansion: Blueprint Checker validates quality profile preferences (Layer 2), receives all blueprint files discovered from the blueprint directory (validates internal consistency -- every unit heading found across all files must have corresponding Tier 1, Tier 2, and Tier 3 content), and receives the pattern catalog section of `svp_2_1_lessons_learned.md` to produce an advisory risk section identifying structural features matching known failure patterns (P1-P8+). The risk section is advisory only -- it does not block alignment confirmation. The checker is agnostic to the number or names of blueprint files.

---

## Unit 15: Construction Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines agent definition files for the three construction agents: Test Agent, Implementation Agent, and Coverage Review Agent. Single-shot agents that generate tests, implementations, or coverage reviews. Implements spec Sections 10.1, 10.5, and 10.8.

SVP 2.1 expansion: Test and implementation agents told quality tools will auto-format/lint/type-check their output. Test agent receives blueprint content with `include_tier1=False` (no Tier 1 descriptions). Implementation agent receives blueprint content with `include_tier1=False` (no Tier 1 descriptions). The content filtering is based on `### Tier N` heading patterns, not on which file the content comes from.

---

## Unit 16: Diagnostic and Classification Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines agent definition files for the Diagnostic Agent and Redo Agent. The diagnostic agent applies the three-hypothesis discipline. The redo agent classifies rollback requests. Implements spec Sections 10.11, 13 (`/svp:redo`).

Unchanged from v2.0. The redo agent's `profile_delivery` and `profile_blueprint` classifications remain as specified in SVP 2.0.

---

## Unit 17: Support Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines agent definition files for the Help Agent and Hint Agent. The help agent is read-only with web search access. The hint agent provides diagnostic analysis. Implements spec Sections 14 and 13. Unchanged from v1.0.

---

## Unit 18: Utility Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines agent definition files for the Reference Indexing Agent, Integration Test Author, and Git Repo Agent. Implements spec Sections 7.2, 11, and 12.

SVP 2.0 expansion: Git repo agent reads full profile for delivery preferences.
SVP 2.1 expansion: Git repo agent generates delivered quality configs, changelog, delivers all discovered blueprint files and project context and references to `docs/` (Bug 11/34 fix), records `delivered_repo_path`, runs Gate C. Git repo agent definition must include a "Repository Location" section stating that the delivered repository is created as a sibling directory of the project workspace. Repo collision avoidance: existing repo directories are renamed before new assembly. Integration test author covers quality gate chains.

The git repo agent must create exactly 11 sequential commits in the prescribed order. Its behavioral contract must enumerate all `docs/` deliverables explicitly. The `pyproject.toml` must contain `[tool.pytest.ini_options]` with appropriate `pythonpath` configuration. All cross-unit imports must be rewritten from `src.unit_N` form to final module paths.

---

## Unit 19: Debug Loop Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines agent definition files for the Bug Triage Agent and Repair Agent. Implements spec Section 12.17. The triage agent receives `delivered_repo_path` in task prompt (NEW IN 2.1). The triage agent's definition (`BUG_TRIAGE_AGENT_MD_CONTENT`) must include Step 7 commit instructions verbatim: human permission is required before committing or pushing, using the fixed `[SVP-DEBUG]` format regardless of `vcs.commit_style`. Gate response options at the commit gate: **COMMIT APPROVED** or **COMMIT REJECTED**.

---

## Unit 20: Slash Command Files

**Artifact category:** Markdown (command .md files)

### Tier 1 -- Description

Defines the slash command files for all SVP commands: `/svp:save`, `/svp:quit`, `/svp:help`, `/svp:hint`, `/svp:status`, `/svp:ref`, `/svp:redo`, `/svp:bug`, `/svp:clean`. Implements spec Section 13.

Group B command definitions (`help`, `hint`, `ref`, `redo`, `bug`) must include the complete action cycle: (1) run `prepare_task.py`, (2) spawn the agent, (3) write the agent's terminal status line to `.svp/last_status.txt`, (4) run `update_state.py --phase <phase>` with the correct phase value, (5) re-run the routing script. A command definition that stops after "spawn the agent" is incomplete (Bug 38 fix).

---

## Unit 21: Orchestration Skill

**Artifact category:** Markdown (SKILL.md)

### Tier 1 -- Description

Defines the orchestration skill file (`SKILL.md`) that contains the complete behavioral protocol for the main session. This is the Claude Code skill that governs the orchestration layer's behavior. Implements spec Section 3.6 (Layer 1 -- CLAUDE.md and Layer 2 -- routing script REMINDER).

`SKILL_MD_CONTENT` must include a section on slash-command-initiated action cycles explaining that Group B commands bypass the routing script -- the command definition substitutes for the routing script's action block. The skill must explain that the same six-step cycle applies, with the command definition providing the PREPARE command, agent type, and POST command (including the correct `--phase` value) (Bug 39 fix).

---

## Unit 22: Project Templates

**Artifact category:** Python script + JSON + TOML + Markdown templates

### Tier 1 -- Description

Provides all project-level template files: `claude_md.py` (CLAUDE.md generator), `svp_config_default.json`, `pipeline_state_initial.json`, `readme_svp.txt`, `toolchain_defaults/python_conda_pytest.json`, `toolchain_defaults/ruff.toml` (NEW IN 2.1), and the bundled Game of Life example. Implements spec Sections 6.1, 6.5, and 6.6.

SVP 2.0 expansion: toolchain default JSON. SVP 2.1 expansion: `ruff.toml` quality tool configuration; `quality` section in toolchain default JSON. The Game of Life example includes blueprint files in its `blueprint/` directory (currently `blueprint_prose.md` and `blueprint_contracts.md`).

---

## Unit 23: Plugin Manifest, Structural Validation, and Compliance Scan

**Artifact category:** JSON + Python script (compliance_scan.py)

### Tier 1 -- Description

Defines the `plugin.json` manifest for the SVP plugin subdirectory and the `marketplace.json` catalog at the repository root. Includes structural validation logic for the plugin directory layout. Also includes the delivery compliance scan (Layer 3 of preference enforcement). Implements spec Sections 1.4, 11.1, and 12.3.

Per the CLI argument enumeration invariant (Bug 49 fix), `compliance_scan_main()` accepts `--project-root`, `--src-dir`, `--tests-dir` via argparse. See Tier 2 for full enumeration.

SVP 2.0 expansion: structural validation includes `toolchain_defaults/`. SVP 2.1 expansion: structural validation includes `ruff.toml` in `toolchain_defaults/`; version bump to 2.1.0; validates `quality` section in toolchain; structural validation checks that `docs/` contains at least one blueprint `.md` file (discovered dynamically, not by hardcoded filenames); structural validation checks for `__SVP_STUB__` sentinel in delivered Python source files; commit count validation; tests-in-delivered-layout check; pytest path config check; README carry-forward check (Mode A).

---

## Unit 24: SVP Launcher

**Artifact category:** Python script (standalone CLI tool)

### Tier 1 -- Description

The standalone `svp` CLI tool that manages the complete SVP session lifecycle: prerequisite verification, project directory creation, script copying, CLAUDE.md generation, filesystem permission management, session cycling, and resume. The launcher runs before Claude Code starts and is not a plugin component. Delivered at `svp/scripts/svp_launcher.py` (entry point: `svp.scripts.svp_launcher:main`).

**Self-containment requirement:** The launcher must be a single, self-contained Python file with NO imports from other SVP units.

SVP 2.0 expansion: copies `toolchain.json` and regression tests. SVP 2.1 expansion: copies `ruff.toml` during project creation (set to read-only immediately after copying); `svp restore` accepts `--blueprint-dir` pointing to a directory containing one or more `.md` blueprint files (validates that the directory exists and contains at least one `.md` file before proceeding -- no assumption about the number or names of files). Implements the three CLI modes: `svp new <project_name>`, bare `svp` (auto-detect and resume), and `svp restore` with required arguments. Per the CLI argument enumeration invariant (Bug 48 fix), all argparse arguments are enumerated in Tier 2 invariants.

---

*End of blueprint prose.*
