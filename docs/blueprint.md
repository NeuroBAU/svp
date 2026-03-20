# SVP -- Stratified Verification Pipeline

## Technical Blueprint: Prose Descriptions (Tier 1)

**Date:** 2026-03-15
**Decomposes:** Stakeholder Specification v8.25
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
7. **Bug fixes:** Bug 17 (hook schema), Bug 21 (two-branch routing), Bug 22 (canonical filenames), Bug 23 (alignment check), Bug 24 (total_units), Bug 25 (Stage 3 routing), Bug 26 (Stage 5 routing), Bug 28 (commit count), Bug 30 (README carry-forward), Bug 31 (launcher flag), Bug 32 (CLI subcommands), Bug 33 (quality gate operations), Bug 34 (toolchain portability), Bug 35 (routing output resolution), Bug 36 (stub generation sub-stage), Bug 37 (repo sibling directory), Bug 38 (Group B commands), Bug 39 (skill slash-command cycle), Bug 41 (Stage 1 routing + gate ID consistency), Bug 42 (pre-Stage-3 state persistence), Bug 43 (universal two-branch routing compliance), Bug 44 (dispatch_agent_status null sub_stage for test_agent), Bug 45 (dispatch_command_status test_execution advancement), Bug 46 (dispatch_agent_status coverage_review advancement), Bug 47 (unit_completion COMMAND/POST separation).
8. **Repo collision avoidance:** Existing repo directories renamed before new assembly.

SVP 2.1 carries forward 22 regression tests from prior builds and adds 9 new ones (test_bug13_hook_schema_validation.py, test_bug22_repo_sibling_directory.py, test_bug23_stage1_spec_gate_routing.py, test_bug42_pre_stage3_state_persistence.py, test_bug43_stage2_blueprint_routing.py, test_bug44_null_substage_dispatch.py, test_bug45_test_execution_dispatch.py, test_bug46_coverage_dispatch.py, test_bug47_unit_completion_double_dispatch.py), totaling 31 regression test files.

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

---

## Unit 7: Dependency Extractor and Import Validator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 1 -- Description

Scans all machine-readable signature blocks across all units in the blueprint directory, extracts every external import statement, produces a complete dependency list, creates the Conda environment, installs all packages (including quality tool packages from `toolchain.json`), and validates that every extracted import resolves. The `extract_all_imports` function takes `blueprint_dir` (the path to the blueprint directory) as its parameter and uses `discover_blueprint_files` from Unit 1 to find all `.md` files, then parses Tier 2 signature blocks from the combined content. Tool commands are read from `toolchain.json` via Unit 1's toolchain reader. Implements spec Sections 9 (Pre-Stage-3 Infrastructure Setup).

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

Updated for selective blueprint loading (Bugs 60-62 fix): exports `load_blueprint_contracts_only()` and `load_blueprint_prose_only()` for per-agent selective loading per spec Section 3.16 matrix. `integration_test_author` and `git_repo_agent` use contracts-only; `help_agent` uses prose-only; `blueprint_checker`, `blueprint_reviewer`, `hint_agent`, and `bug_triage` receive both files. The internal `_get_unit_context` helper resolves the blueprint directory via `get_blueprint_dir()` (Bug 60 fix) and passes `include_tier1` through to `build_unit_context` (Bug 61 fix).

---

## Unit 10: Routing Script and Update State

**Artifact category:** Python script (library + 3 CLI wrappers)

### Tier 1 -- Description

Reads `pipeline_state.json` and outputs the exact next action as a structured key-value block. Handles every stage, sub-stage, gate, and agent transition in the pipeline. Includes `update_state_main` (CLI wrapper for POST commands), `run_tests_main` (CLI wrapper for test execution), and `run_quality_gate_main` (CLI wrapper for quality gate execution, NEW IN 2.1).

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

SVP 2.0 expansion: Setup agent gains project profile dialog (six areas), Gate 0.3, targeted revision mode.
SVP 2.1 expansion: Setup agent gains Area 5 (quality preferences) and changelog question in Area 1. Setup agent's system prompt must include all four UX behavioral rules (plain-language explanations, best-option recommendations, sensible defaults, progressive disclosure) as numbered requirements. Setup agent's system prompt must also embed the complete `project_profile.json` schema structure with exact canonical field names matching `DEFAULT_PROFILE` in Unit 1, so the agent's JSON output uses identical section and field names. Blueprint author receives `quality` profile section.
SVP 2.1.1 expansion: Setup agent gains Area 6 (agent model configuration -- opus/sonnet/haiku per agent), GitHub repository configuration (`vcs.github`) in Area 1, and README mode (`readme.mode`) in Area 2. The routing script emits a MODEL field in invoke_agent action blocks based on `pipeline.agent_models` in the profile. The git repo agent handles GitHub remote configuration based on `vcs.github` mode. The git repo agent uses existing README as base content when `readme.mode` is "update".

RFC-2 expansion: Blueprint author agent definition includes Rules P1-P4 for unit-level preference capture during the decomposition dialog. P1: ask at the unit level (after Tier 1, before contracts). P2: use domain language only. P3: progressive disclosure (one open question per unit). P4: conflict detection at capture time. Captured preferences are recorded as a `### Preferences` subsection within each unit's Tier 1 description in `blueprint_prose.md`. Absence means "no preferences." Authority hierarchy: spec > contracts > preferences.

---

## Unit 14: Review and Checker Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three review/checker agents: Stakeholder Spec Reviewer, Blueprint Checker, and Blueprint Reviewer. Single-shot agents that produce a critique or verdict. Implements spec Sections 7.4, 8.2, and "report most fundamental level."

SVP 2.0 expansion: Blueprint Checker gains Layer 2 preference coverage validation.
SVP 2.1 expansion: Blueprint Checker validates quality profile preferences (Layer 2), receives all blueprint files discovered from the blueprint directory (validates internal consistency -- every unit heading found across all files must have corresponding Tier 1, Tier 2, and Tier 3 content), and receives the pattern catalog section of `svp_2_1_lessons_learned.md` to produce an advisory risk section identifying structural features matching known failure patterns (P1-P8+). The risk section is advisory only -- it does not block alignment confirmation. The checker is agnostic to the number or names of blueprint files.

RFC-2 expansion: Blueprint Checker gains preference-contract consistency validation. For each unit that has a Preferences subsection in Tier 1, the checker verifies that no stated preference contradicts a Tier 2 signature or Tier 3 behavioral contract. Reported as a non-blocking warning (not an alignment failure), since preferences are non-binding.

Bug 57 expansion: All three review agents (stakeholder reviewer, blueprint checker, blueprint reviewer) gain mandatory review checklists baked into their agent definitions. The checklists require explicit verification of downstream dependency analysis, contract granularity, per-gate dispatch contracts, call-site traceability, and re-entry invalidation (spec Section 3.20).

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

SVP 2.0 expansion: structural validation includes `toolchain_defaults/`. SVP 2.1 expansion: structural validation includes `ruff.toml` in `toolchain_defaults/`; version bump to 2.1.0; validates `quality` section in toolchain; structural validation checks that `docs/` contains at least one blueprint `.md` file (discovered dynamically, not by hardcoded filenames); structural validation checks for `__SVP_STUB__` sentinel in delivered Python source files; commit count validation; tests-in-delivered-layout check; pytest path config check; README carry-forward check (Mode A).

---

## Unit 24: SVP Launcher

**Artifact category:** Python script (standalone CLI tool)

### Tier 1 -- Description

The standalone `svp` CLI tool that manages the complete SVP session lifecycle: prerequisite verification, project directory creation, script copying, CLAUDE.md generation, filesystem permission management, session cycling, and resume. The launcher runs before Claude Code starts and is not a plugin component. Delivered at `svp/scripts/svp_launcher.py` (entry point: `svp.scripts.svp_launcher:main`).

**Self-containment requirement:** The launcher must be a single, self-contained Python file with NO imports from other SVP units.

SVP 2.0 expansion: copies `toolchain.json` and regression tests. SVP 2.1 expansion: copies `ruff.toml` during project creation (set to read-only immediately after copying); `svp restore` accepts `--blueprint-dir` pointing to a directory containing one or more `.md` blueprint files (validates that the directory exists and contains at least one `.md` file before proceeding -- no assumption about the number or names of files). Implements the three CLI modes: `svp new <project_name>`, bare `svp` (auto-detect and resume), and `svp restore` with required arguments.

---

*End of blueprint prose.*
# SVP -- Stratified Verification Pipeline

## Technical Blueprint: Contracts (Tier 2 + Tier 3)

**Date:** 2026-03-15
**Decomposes:** Stakeholder Specification v8.25
**Companion File:** The other `.md` file(s) in this blueprint directory (Tier 1 descriptions)

---

## Unit 1: SVP Configuration

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import json

# ===========================================================================
# Section 0: Canonical Pipeline Artifact Filenames (Bug 22 fix -- NEW IN 2.1)
# ===========================================================================

ARTIFACT_FILENAMES: Dict[str, str] = {
    "stakeholder_spec": "stakeholder_spec.md",
    "blueprint_dir": "blueprint",
    "project_context": "project_context.md",
    "project_profile": "project_profile.json",
    "pipeline_state": "pipeline_state.json",
    "svp_config": "svp_config.json",
    "toolchain": "toolchain.json",
    "ruff_config": "ruff.toml",
    "docs_dir": "docs",
    "lessons_learned": "svp_2_1_lessons_learned.md",
}

def discover_blueprint_files(project_root: Path) -> List[Path]:
    """Discover all .md files in the blueprint directory, sorted by name."""
    ...

def load_blueprint_content(project_root: Path) -> str:
    """Load and concatenate all blueprint .md files from the blueprint directory."""
    ...

# ===========================================================================
# Section 1: SVP Configuration (svp_config.json)
# ===========================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "iteration_limit": 3,
    "models": {
        "test_agent": "claude-opus-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6",
    },
    "context_budget_override": None,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": True,
    "skip_permissions": True,
}

def load_config(project_root: Path) -> Dict[str, Any]: ...

def validate_config(config: Dict[str, Any]) -> list[str]: ...

def get_model_for_agent(config: Dict[str, Any], agent_role: str) -> str: ...

def get_effective_context_budget(config: Dict[str, Any]) -> int: ...

def write_default_config(project_root: Path) -> Path: ...

# ===========================================================================
# Section 2: Project Profile (project_profile.json)
# ===========================================================================

DEFAULT_PROFILE: Dict[str, Any] = {
    "pipeline_toolchain": "python_conda_pytest",
    "python_version": "3.11",
    "delivery": {
        "environment_recommendation": "conda",
        "dependency_format": "environment.yml",
        "source_layout": "conventional",
        "entry_points": False,
    },
    "vcs": {
        "commit_style": "conventional",
        "commit_template": None,
        "issue_references": False,
        "branch_strategy": "main-only",
        "tagging": "semver",
        "conventions_notes": None,
        "changelog": "none",
    },
    "readme": {
        "audience": "domain expert",
        "sections": [
            "Header", "What it does", "Who it's for", "Installation",
            "Configuration", "Usage", "Quick Tutorial", "Examples",
            "Project Structure", "License",
        ],
        "depth": "standard",
        "include_math_notation": False,
        "include_glossary": False,
        "include_data_formats": False,
        "include_code_examples": False,
        "code_example_focus": None,
        "custom_sections": None,
        "docstring_convention": "google",
        "citation_file": False,
        "contributing_guide": False,
    },
    "testing": {
        "coverage_target": None,
        "readable_test_names": True,
        "readme_test_scenarios": False,
    },
    "license": {
        "type": "MIT",
        "holder": "",
        "author": "",
        "year": "",
        "contact": None,
        "spdx_headers": False,
        "additional_metadata": {
            "citation": None,
            "funding": None,
            "acknowledgments": None,
        },
    },
    "quality": {
        "linter": "ruff",
        "formatter": "ruff",
        "type_checker": "none",
        "import_sorter": "ruff",
        "line_length": 88,
    },
    "fixed": {
        "language": "python",
        "pipeline_environment": "conda",
        "test_framework": "pytest",
        "build_backend": "setuptools",
        "vcs_system": "git",
        "source_layout_during_build": "svp_native",
        "pipeline_quality_tools": "ruff_mypy",
    },
    "created_at": "",
}

def load_profile(project_root: Path) -> Dict[str, Any]: ...

def validate_profile(profile: Dict[str, Any]) -> list[str]: ...

def get_profile_section(profile: Dict[str, Any], section: str) -> Dict[str, Any]: ...

def detect_profile_contradictions(profile: Dict[str, Any]) -> list[str]: ...

# ===========================================================================
# Section 3: Pipeline Toolchain (toolchain.json)
# ===========================================================================

def load_toolchain(project_root: Path) -> Dict[str, Any]: ...

def validate_toolchain(toolchain: Dict[str, Any]) -> list[str]: ...

def resolve_command(
    toolchain: Dict[str, Any],
    operation: str,
    params: Optional[Dict[str, str]] = None,
) -> str: ...

def resolve_run_prefix(toolchain: Dict[str, Any], env_name: str) -> str: ...

def get_framework_packages(toolchain: Dict[str, Any]) -> List[str]: ...

def get_quality_packages(toolchain: Dict[str, Any]) -> List[str]: ...

def get_collection_error_indicators(toolchain: Dict[str, Any]) -> List[str]: ...

def get_quality_gate_operations(
    toolchain: Dict[str, Any], gate: str
) -> List[str]: ...

def validate_python_version(
    python_version: str, version_constraint: str
) -> bool: ...

# ===========================================================================
# Section 4: Shared Utilities
# ===========================================================================

def derive_env_name(project_name: str) -> str: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert project_root.is_dir(), "Project root must be an existing directory"

# Post-conditions for load_config
assert isinstance(result, dict), "Config must be a dict"
assert "iteration_limit" in result, "Config must contain iteration_limit"
assert "models" in result, "Config must contain models section"
assert result["iteration_limit"] >= 1, "Iteration limit must be at least 1"
assert 0 < result["context_budget_threshold"] <= 100, "Budget threshold must be 1-100"
assert result["compaction_character_threshold"] >= 0, "Compaction threshold must be non-negative"
assert isinstance(result["skip_permissions"], bool), "skip_permissions must be a boolean"

# Post-conditions for load_profile
assert isinstance(result, dict), "Profile must be a dict"
assert "delivery" in result, "Profile must contain delivery section"
assert "vcs" in result, "Profile must contain vcs section"
assert "readme" in result, "Profile must contain readme section"
assert "testing" in result, "Profile must contain testing section"
assert "license" in result, "Profile must contain license section"
assert "quality" in result, "Profile must contain quality section"
assert "fixed" in result, "Profile must contain fixed section"

# Post-conditions for load_toolchain
assert isinstance(result, dict), "Toolchain must be a dict"
assert "environment" in result, "Toolchain must contain environment section"
assert "testing" in result, "Toolchain must contain testing section"
assert "packaging" in result, "Toolchain must contain packaging section"
assert "vcs" in result, "Toolchain must contain vcs section"
assert "language" in result, "Toolchain must contain language section"
assert "file_structure" in result, "Toolchain must contain file_structure section"
assert "quality" in result, "Toolchain must contain quality section"

# Post-conditions for resolve_command
assert isinstance(result, str), "Resolved command must be a string"
assert "{" not in result, "No unresolved placeholders in resolved command"

# Post-conditions for derive_env_name
assert result == project_name.lower().replace(" ", "_").replace("-", "_"), \
    "Env name must follow the canonical derivation"
assert " " not in result, "Env name must not contain spaces"
assert "-" not in result, "Env name must not contain hyphens"

# Artifact filename invariants (Bug 22, updated for directory-based blueprint discovery)
assert ARTIFACT_FILENAMES["stakeholder_spec"] == "stakeholder_spec.md"
assert ARTIFACT_FILENAMES["blueprint_dir"] == "blueprint"
assert "blueprint_prose" not in ARTIFACT_FILENAMES, "No hardcoded blueprint filenames"
assert "blueprint_contracts" not in ARTIFACT_FILENAMES, "No hardcoded blueprint filenames"
assert ARTIFACT_FILENAMES["project_context"] == "project_context.md"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Config file not found at {path}" -- when `svp_config.json` does not exist at project root. `load_config` returns defaults when file is absent (no error for missing file on first load).
- `json.JSONDecodeError`: "Config file is not valid JSON" -- when file exists but is malformed.
- `ValueError`: "Invalid config: {details}" -- when `validate_config` finds a structural problem.
- `RuntimeError`: "Project profile not found at {path}. Resume from Stage 0 or run /svp:redo to create it." -- when `load_profile` is called and `project_profile.json` does not exist.
- `RuntimeError`: "Toolchain file not found at {path}. Re-run svp new or reinstall the plugin." -- when `load_toolchain` is called and `toolchain.json` does not exist. No fallback to hardcoded values.
- `json.JSONDecodeError`: "Profile/Toolchain file is not valid JSON" -- when file exists but is malformed.
- `ValueError`: "Invalid profile: {details}" -- when `validate_profile` finds a structural problem.
- `ValueError`: "Invalid toolchain: {details}" -- when `validate_toolchain` finds a structural problem.
- `ValueError`: "Python version {version} does not satisfy constraint {constraint}" -- when `validate_python_version` fails.
- `ValueError`: "Unresolved placeholder in command template: {placeholder}" -- when `resolve_command` encounters a placeholder it cannot resolve.
- `ValueError`: "Unknown quality gate: {gate}" -- when `get_quality_gate_operations` receives an unrecognized gate identifier.
- `FileNotFoundError`: "Blueprint directory not found: {path}" -- when `discover_blueprint_files` is called and the blueprint directory does not exist.
- `FileNotFoundError`: "No .md files found in blueprint directory: {path}" -- when `discover_blueprint_files` finds the directory but it contains no `.md` files.

### Tier 3 -- Behavioral Contracts

**Config loader (unchanged from v1.0):**
- `load_config` returns the merged result of file content over defaults -- missing keys in the file are filled from `DEFAULT_CONFIG`.
- `load_config` on a non-existent file returns a copy of `DEFAULT_CONFIG` without error.
- `validate_config` returns an empty list when config is valid, a list of human-readable error strings for each violation found.
- `get_model_for_agent` returns the agent-specific model if configured, otherwise the `models.default` value.
- `get_effective_context_budget` returns the `context_budget_override` when set and non-null, otherwise computes from the smallest model context window minus 20,000 tokens overhead.
- `write_default_config` writes `DEFAULT_CONFIG` as formatted JSON to `{project_root}/svp_config.json` and returns the path.
- Config changes made by the human take effect on next load -- no caching across invocations.

**Profile loader (CHANGED IN 2.1):**
- `load_profile` reads `project_profile.json` from `project_root`, validates fields it uses against expected types. Unknown fields are ignored (forward compatibility). Missing fields are filled from `DEFAULT_PROFILE` via `_deep_merge` -- a recursive merge that fills missing keys at all nesting levels. Raises `RuntimeError` if the file is missing or fails JSON parsing.
- `validate_profile` checks structural integrity: all required sections present, correct types for each field, `delivery.environment_recommendation` is one of `"conda"`, `"pyenv"`, `"venv"`, `"poetry"`, `"none"`, `delivery.source_layout` is one of `"conventional"`, `"flat"`, `"svp_native"`, `vcs.commit_style` is one of `"conventional"`, `"freeform"`, `"custom"`, `vcs.changelog` is one of `"keep_a_changelog"`, `"conventional_changelog"`, `"none"`, `readme.depth` is one of `"minimal"`, `"standard"`, `"comprehensive"`, `testing.coverage_target` is null or integer 0-100, `quality.linter` is one of `"ruff"`, `"flake8"`, `"pylint"`, `"none"`, `quality.formatter` is one of `"ruff"`, `"black"`, `"none"`, `quality.type_checker` is one of `"mypy"`, `"pyright"`, `"none"`, `quality.import_sorter` is one of `"ruff"`, `"isort"`, `"none"`, `quality.line_length` is a positive integer. Returns empty list when valid, list of error strings otherwise.
- `get_profile_section` returns a specific top-level section of the profile. Raises `KeyError` if the section does not exist.
- `detect_profile_contradictions` checks for known contradictory combinations (spec Section 6.4). Returns list of contradiction descriptions.

**Toolchain reader (CHANGED IN 2.1):**
- `load_toolchain` reads `toolchain.json` from `project_root`. Raises `RuntimeError` if missing or malformed. No fallback to hardcoded values.
- `validate_toolchain` checks structural integrity: all required sections present including the `quality` section (`formatter`, `linter`, `type_checker`, `packages`, `gate_a`, `gate_b`, `gate_c`), command templates contain only recognized placeholders, and `linter.unused_exports` key exists (Bug 56 fix). Returns empty list when valid.
- `resolve_command` performs single-pass placeholder resolution. The recognized placeholder vocabulary is a closed set: `{env_name}`, `{python_version}`, `{run_prefix}`, `{target}`, `{flags}`, `{packages}`, `{files}`, `{message}`, `{module}`, `{test_path}`. Resolution order: first resolves `environment.run_prefix` by substituting `{env_name}` internally, then substitutes the resolved `run_prefix` value into all templates referencing `{run_prefix}`. **The canonical placeholder for file/directory paths is `{target}`, not `{path}` (Bug 33 fix).** No recursive resolution. Raises `ValueError` if any placeholder remains unresolved after substitution.
- `resolve_run_prefix` is a convenience function: resolves `environment.run_prefix` template with the given `env_name`.
- `get_framework_packages` returns `testing.framework_packages` from the toolchain.
- `get_quality_packages` returns `quality.packages` from the toolchain.
- `get_collection_error_indicators` returns `testing.collection_error_indicators` from the toolchain.
- `get_quality_gate_operations` returns the operation list for the given gate identifier (`"gate_a"`, `"gate_b"`, or `"gate_c"`) from the toolchain's `quality` section. Gate C includes `"linter.unused_exports"` for dead code detection (Bug 56 fix).
- `validate_python_version` checks whether a version string satisfies the constraint. Returns True if satisfied, False otherwise.
- **Behavioral equivalence:** Every resolved command from the existing sections must produce identical behavior to SVP 1.2's hardcoded commands. The `quality` section is purely additive.

**Shared utilities:**
- `derive_env_name` applies the canonical derivation: `project_name.lower().replace(" ", "_").replace("-", "_")`. This is the single canonical implementation used by Units 7, 10, 11, and 24.

**Artifact filenames (NEW IN 2.1 -- Bug 22 fix, updated for directory-based blueprint discovery):**
- `ARTIFACT_FILENAMES` is a dict mapping logical artifact names to their canonical filenames or directory names. All components that produce or consume pipeline artifacts must import and use these constants. The `blueprint_dir` entry points to the blueprint directory (not individual files). Individual blueprint filenames are NOT listed in `ARTIFACT_FILENAMES` -- they are discovered dynamically by `discover_blueprint_files`.
- `discover_blueprint_files(project_root)` returns a sorted list of `Path` objects for all `.md` files in `project_root / ARTIFACT_FILENAMES["blueprint_dir"]`. Raises `FileNotFoundError` if the blueprint directory does not exist or contains no `.md` files -- a missing blueprint directory is an error condition, not an empty result. Sorting is alphabetical by filename to ensure deterministic ordering.
- `load_blueprint_content(project_root)` calls `discover_blueprint_files`, reads each file, and concatenates their contents separated by `\n\n---\n\n`. Raises `FileNotFoundError` if the blueprint directory does not exist or contains no `.md` files. This function is the single entry point for loading blueprint content -- all consumers use it instead of hardcoded file paths.
- **Backward compatibility:** A single `blueprint.md` file in the blueprint directory is handled correctly -- `discover_blueprint_files` returns it as the sole entry. Multiple files (e.g., `blueprint_contracts.md` and `blueprint_prose.md`) are also handled. The system makes no assumption about the number or names of blueprint files.
- **Spec v8.25 filename convention:** While the discovery mechanism is filename-agnostic at the code level (any `.md` files in the blueprint directory are discovered and loaded), spec v8.25 constrains this build to use `blueprint_prose.md` and `blueprint_contracts.md` as the actual blueprint filenames. These names appear in the project file tree, the bundled Game of Life example, and the `svp restore` workflow. The code must not hardcode these names, but the project's blueprint directory will contain exactly these two files.

**DEFAULT_PROFILE key path regression test (spec Section 30):**
- A Unit 1 unit test (in `tests/unit_1/`) must verify that every key path in `DEFAULT_PROFILE` matches the canonical profile schema defined in spec Section 6.4. This is a unit test of Unit 1's data contract, not a separate regression file.

### Tier 3 -- Dependencies

None. This is the most foundational unit.

---

## Unit 2: Pipeline State Schema and Core Operations

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

# --- Data contract: pipeline state schema ---

STAGES: List[str] = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

SUB_STAGES_STAGE_0: List[str] = ["hook_activation", "project_context", "project_profile"]

STAGE_1_SUB_STAGES: List[Optional[str]] = [None]

STAGE_2_SUB_STAGES: List[Optional[str]] = [None, "blueprint_dialog", "alignment_check"]

STAGE_3_SUB_STAGES: List[Optional[str]] = [
    None,
    "stub_generation",
    "test_generation",
    "quality_gate_a",
    "quality_gate_a_retry",
    "red_run",
    "implementation",
    "quality_gate_b",
    "quality_gate_b_retry",
    "green_run",
    "coverage_review",
    "unit_completion",
]

STAGE_4_SUB_STAGES: List[Optional[str]] = [None]

STAGE_5_SUB_STAGES: List[Optional[str]] = [None, "repo_test", "compliance_scan", "repo_complete"]

QUALITY_GATE_SUB_STAGES: List[str] = [
    "quality_gate_a", "quality_gate_b",
    "quality_gate_a_retry", "quality_gate_b_retry",
]

REDO_PROFILE_SUB_STAGES: List[str] = ["redo_profile_delivery", "redo_profile_blueprint"]

FIX_LADDER_POSITIONS: List[Optional[str]] = [
    None, "fresh_test", "hint_test",
    "fresh_impl", "diagnostic", "diagnostic_impl",
]

class DebugSession:
    """Debug session state for post-delivery bug investigation."""
    bug_id: int
    description: str
    classification: Optional[str]
    affected_units: List[int]
    regression_test_path: Optional[str]
    phase: str
    authorized: bool
    triage_refinement_count: int
    repair_retry_count: int
    created_at: str
    def __init__(self, **kwargs: Any) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugSession": ...

class PipelineState:
    """Complete pipeline state. This is the schema contract."""
    stage: str
    sub_stage: Optional[str]
    current_unit: Optional[int]
    total_units: Optional[int]
    fix_ladder_position: Optional[str]
    red_run_retries: int
    alignment_iteration: int
    verified_units: List[Dict[str, Any]]
    pass_history: List[Dict[str, Any]]
    log_references: Dict[str, str]
    project_name: Optional[str]
    last_action: Optional[str]
    debug_session: Optional[DebugSession]
    debug_history: List[Dict[str, Any]]
    redo_triggered_from: Optional[Dict[str, Any]]
    delivered_repo_path: Optional[str]
    created_at: str
    updated_at: str
    def __init__(self, **kwargs: Any) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState": ...

def create_initial_state(project_name: str) -> PipelineState: ...

def load_state(project_root: Path) -> PipelineState: ...

def save_state(state: PipelineState, project_root: Path) -> None: ...

def validate_state(state: PipelineState) -> list[str]: ...

def recover_state_from_markers(project_root: Path) -> Optional[PipelineState]: ...

def get_stage_display(state: PipelineState) -> str: ...
```

### Tier 2 — Invariants

```python
assert project_root.is_dir(), "Project root must exist"

assert result.stage == "0", "Initial state must be Stage 0"
assert result.sub_stage == "hook_activation", "Initial sub-stage must be hook_activation"
assert result.red_run_retries == 0
assert result.alignment_iteration == 0
assert len(result.verified_units) == 0
assert len(result.pass_history) == 0
assert result.debug_session is None
assert result.debug_history == []
assert result.redo_triggered_from is None
assert result.delivered_repo_path is None

assert result.stage in STAGES, "Stage must be a valid stage identifier"
assert result.red_run_retries >= 0
assert result.alignment_iteration >= 0

assert (project_root / "pipeline_state.json").exists(), "State file must exist after save"

assert all(s in QUALITY_GATE_SUB_STAGES for s in ["quality_gate_a", "quality_gate_b",
    "quality_gate_a_retry", "quality_gate_b_retry"])
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "State file not found at {path}" -- when `load_state` is called and `pipeline_state.json` does not exist.
- `json.JSONDecodeError`: "State file is not valid JSON" -- when file is malformed.
- `ValueError`: "Invalid state: {details}" -- when `validate_state` finds structural problems.

### Tier 3 -- Behavioral Contracts

- `create_initial_state` returns a `PipelineState` at `stage: "0"`, `sub_stage: "hook_activation"` with all counters at zero, `debug_session: None`, `debug_history: []`, `redo_triggered_from: None`, and `delivered_repo_path: None`.
- `load_state` deserializes `pipeline_state.json` and returns a validated `PipelineState`, including deserialization of `debug_session`, `redo_triggered_from`, and `delivered_repo_path`. Missing fields filled with defaults.
- `save_state` atomically writes the state (write to temp file, rename).
- `validate_state` checks structural integrity: valid stage, valid sub-stage for the stage (Stage 0 from `SUB_STAGES_STAGE_0`, Stage 1 from `STAGE_1_SUB_STAGES` which is `[None]` only, Stage 2 from `STAGE_2_SUB_STAGES`, Stage 3 from `STAGE_3_SUB_STAGES`, Stage 4 from `STAGE_4_SUB_STAGES`, Stage 5 from `STAGE_5_SUB_STAGES`, and redo profile sub-stages from `REDO_PROFILE_SUB_STAGES` for any stage), non-negative counters, valid debug_session, valid redo_triggered_from snapshot, delivered_repo_path is either None or a non-empty string.
- `recover_state_from_markers` scans for `<!-- SVP_APPROVED: ... -->` markers and `.svp/markers/unit_N_verified` files. Uses `ARTIFACT_FILENAMES` from Unit 1.
- `get_stage_display` returns a human-readable string like "Stage 3, Unit 4 of 11 (pass 2)".
- The `updated_at` field is set to current ISO timestamp on every `save_state` call.
- Pass history and debug history entries are append-only.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Uses `ARTIFACT_FILENAMES` for canonical filenames in `recover_state_from_markers`.

---

## Unit 3: State Transition Engine

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from pipeline_state import PipelineState, DebugSession

class TransitionError(Exception):
    """Raised when a state transition's preconditions are not met."""
    ...

def advance_stage(state: PipelineState, project_root: Path) -> PipelineState: ...
def advance_sub_stage(state: PipelineState, sub_stage: str, project_root: Path) -> PipelineState: ...
def complete_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState: ...
def advance_fix_ladder(state: PipelineState, new_position: str) -> PipelineState: ...
def increment_red_run_retries(state: PipelineState) -> PipelineState: ...
def reset_red_run_retries(state: PipelineState) -> PipelineState: ...
def increment_alignment_iteration(state: PipelineState) -> PipelineState: ...
def rollback_to_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState: ...
def restart_from_stage(state: PipelineState, target_stage: str, reason: str, project_root: Path) -> PipelineState: ...

def version_document(
    doc_path: Path, history_dir: Path, diff_summary: str, trigger_context: str,
    companion_paths: Optional[List[Path]] = None,
) -> Tuple[Path, Path]: ...

def enter_debug_session(state: PipelineState, bug_description: str) -> PipelineState: ...
def authorize_debug_session(state: PipelineState) -> PipelineState: ...
def complete_debug_session(state: PipelineState, fix_summary: str) -> PipelineState: ...
def abandon_debug_session(state: PipelineState) -> PipelineState: ...
def update_debug_phase(state: PipelineState, phase: str) -> PipelineState: ...
def set_debug_classification(state: PipelineState, classification: str, affected_units: List[int]) -> PipelineState: ...

def enter_redo_profile_revision(state: PipelineState, classification: str) -> PipelineState: ...
def complete_redo_profile_revision(state: PipelineState) -> PipelineState: ...

def enter_alignment_check(state: PipelineState) -> PipelineState: ...
def complete_alignment_check(state: PipelineState, project_root: Path) -> PipelineState: ...

def enter_quality_gate(state: PipelineState, gate: str) -> PipelineState: ...
def advance_quality_gate_to_retry(state: PipelineState) -> PipelineState: ...
def quality_gate_pass(state: PipelineState) -> PipelineState: ...
def _ladder_has_room(state: PipelineState) -> bool: ...
def quality_gate_fail_to_ladder(state: PipelineState) -> PipelineState: ...

def set_delivered_repo_path(state: PipelineState, repo_path: str) -> PipelineState: ...

```

### Tier 2 — Invariants

```python
# Pre-conditions for complete_unit
assert state.stage == "3"
assert state.current_unit == unit_number

# Pre-conditions for advance_stage
assert state.stage in ("0", "1", "2", "pre_stage_3", "3", "4"), "Cannot advance past Stage 5"

# Pre-conditions for rollback_to_unit (Bug 55: accepts Stage 5 with active debug session)
assert state.stage in ("3", "5"), "Rollback applies during Stage 3 or Stage 5 with active debug session"
assert state.stage != "5" or state.debug_session is not None, "Stage 5 rollback requires active debug session"
assert unit_number >= 1
assert unit_number <= (state.current_unit or 0)

# Pre-conditions for enter_debug_session
assert state.stage == "5"
assert state.debug_session is None

# Pre-conditions for enter_alignment_check (Bug 23 fix)
assert state.stage == "2"

# Pre-conditions for complete_alignment_check (Bug 23 fix)
assert state.stage == "2"
assert state.sub_stage == "alignment_check"

# Pre-conditions for enter_quality_gate
assert state.stage == "3"
assert gate in ("quality_gate_a", "quality_gate_b")

# Pre-conditions for set_delivered_repo_path
assert state.stage == "5"
assert len(repo_path.strip()) > 0

# Post-conditions for complete_unit
assert result.fix_ladder_position is None
assert result.red_run_retries == 0
assert result.sub_stage is None

# Post-conditions for enter_quality_gate
assert result.sub_stage == gate

# Post-conditions for advance_quality_gate_to_retry
assert result.sub_stage.endswith("_retry")

# Post-conditions for quality_gate_pass
assert result.sub_stage not in ("quality_gate_a", "quality_gate_b",
    "quality_gate_a_retry", "quality_gate_b_retry")

# Post-conditions for set_delivered_repo_path
assert result.delivered_repo_path == repo_path
```

### Tier 3 -- Error Conditions

- `TransitionError`: "Cannot advance from stage {X}: preconditions not met -- {details}"
- `TransitionError`: "Cannot complete unit {N}: tests have not passed"
- `TransitionError`: "Cannot advance fix ladder to {position}: current position {current} does not permit this transition"
- `TransitionError`: "Alignment iteration limit reached ({limit})"
- `TransitionError`: "Cannot enter debug session: pipeline is not at Stage 5"
- `TransitionError`: "Cannot enter alignment check: not in Stage 2"
- `TransitionError`: "Cannot complete alignment check: not in alignment_check sub-stage"
- `TransitionError`: "Cannot enter quality gate {gate}: not in Stage 3"
- `FileNotFoundError`: "Document to version not found: {path}"

### Tier 3 -- Behavioral Contracts

- `advance_stage` moves the state to the next stage. Resets `sub_stage` to `None`. Validates exit criteria per stage (Stage 2 to Pre-Stage-3 requires `ALIGNMENT_CONFIRMED` and `alignment_check` sub-stage -- Bug 23 fix).
- `complete_unit` writes marker file, updates `verified_units`, resets fix ladder, red_run_retries, and sub_stage to `None`. Advances `current_unit`. When `current_unit` exceeds `total_units`, advances to Stage 4.
- `version_document` copies document to history, writes diff summary. **When `companion_paths` is not None and non-empty (used for the blueprint directory -- the caller passes all discovered `.md` files), all files are versioned together atomically: produces versioned copies (e.g., `blueprint_prose_vN.md`, `blueprint_contracts_vN.md`) and diff summaries for each file. The files share a version number. When `companion_paths` is None, only the primary `doc_path` file is versioned. The caller (Unit 10's routing/update logic) uses `discover_blueprint_files` from Unit 1 to determine which files to pass as companions.**
- `enter_alignment_check` sets `sub_stage` to `"alignment_check"`. Called after Gate 2.1 APPROVE.
- `complete_alignment_check` calls `advance_stage` to transition Stage 2 to Pre-Stage-3.
- `enter_quality_gate` sets `sub_stage` to the quality gate sub-stage.
- `advance_quality_gate_to_retry` transitions from `quality_gate_a` to `quality_gate_a_retry` or `quality_gate_b` to `quality_gate_b_retry`.
- `quality_gate_pass` advances past quality gate: from `quality_gate_a`/`quality_gate_a_retry` to `"red_run"`; from `quality_gate_b`/`quality_gate_b_retry` to `"green_run"`.
- `quality_gate_fail_to_ladder` calls `advance_fix_ladder` internally. If ladder has room, sets `sub_stage` to `None`. If exhausted, preserves sub_stage for routing to present exhaustion gate.
- `set_delivered_repo_path` records the absolute path to the delivered repository.
- All transition functions return a new `PipelineState` -- they do not mutate the input.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads `iteration_limit` for alignment loop cap, reads `auto_save`.
- **Unit 2 (Pipeline State Schema):** Uses `PipelineState` and `DebugSession` classes. Uses `save_state` after transitions.

---

## Unit 4: Ledger Manager

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json

class LedgerEntry:
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]]
    def __init__(self, role: str, content: str, timestamp: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry": ...

def append_entry(ledger_path: Path, entry: LedgerEntry) -> None: ...
def read_ledger(ledger_path: Path) -> List[LedgerEntry]: ...
def clear_ledger(ledger_path: Path) -> None: ...
def rename_ledger(ledger_path: Path, new_name: str) -> Path: ...
def get_ledger_size_chars(ledger_path: Path) -> int: ...
def check_ledger_capacity(ledger_path: Path, max_chars: int) -> Tuple[float, Optional[str]]: ...
def compact_ledger(ledger_path: Path, character_threshold: int = 200) -> int: ...
def write_hint_entry(ledger_path: Path, hint_content: str, gate_id: str,
    unit_number: Optional[int], stage: str, decision: str) -> None: ...
def extract_tagged_lines(content: str) -> List[Tuple[str, str]]: ...
```

### Tier 2 — Invariants

```python
assert ledger_path.suffix == ".jsonl"
assert ledger_path.exists(), "Ledger file must exist after append"
assert result >= 0, "Compaction must report non-negative bytes saved"
assert all(isinstance(e, LedgerEntry) for e in result)
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Ledger file not found: {path}" -- when `compact_ledger` is called on a non-existent file.
- `json.JSONDecodeError`: "Malformed JSONL entry at line {N}"
- `ValueError`: "Invalid ledger entry: missing required field '{field}'"

### Tier 3 -- Behavioral Contracts

- `append_entry` appends a single JSONL line. Creates the file if it does not exist.
- `read_ledger` returns an empty list for a non-existent or empty file.
- `compact_ledger` implements the compaction algorithm: tagged lines above threshold have bodies deleted; at or below, bodies preserved. `[HINT]` entries always preserved. Returns characters saved.
- `write_hint_entry` creates a system-level `[HINT]` entry with full gate metadata.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Indirect dependency. `compact_ledger` accepts `character_threshold` as a parameter (default 200); the caller reads `compaction_character_threshold` from Unit 1's config and passes it as an argument. Unit 4 does not import from Unit 1 directly.

---

## Unit 5: Blueprint Extractor

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path

class UnitDefinition:
    unit_number: int
    unit_name: str
    artifact_category: str
    description: str
    signatures: str
    invariants: str
    error_conditions: str
    behavioral_contracts: str
    dependencies: List[int]
    def __init__(self, **kwargs: Any) -> None: ...

def parse_blueprint(
    blueprint_dir: Path,
    include_tier1: bool = True,
) -> List[UnitDefinition]: ...

def extract_unit(
    blueprint_dir: Path, unit_number: int,
    include_tier1: bool = True,
) -> UnitDefinition: ...

def extract_upstream_contracts(
    blueprint_dir: Path, unit_number: int,
    include_tier1: bool = True,
) -> List[Dict[str, Any]]: ...

def build_unit_context(
    blueprint_dir: Path, unit_number: int,
    include_tier1: bool = True,
) -> str: ...
```

### Tier 2 — Invariants

```python
assert blueprint_dir.is_dir(), "Blueprint directory must exist"
assert unit_number >= 1
assert len(result) > 0, "Blueprint must contain at least one unit"
assert result.unit_number == unit_number
assert len(result.signatures) > 0
assert len(result) > 0, "Unit context must be non-empty"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Blueprint directory not found: {path}"
- `FileNotFoundError`: "No .md files found in blueprint directory: {path}"
- `ValueError`: "Unit {N} not found in blueprint"
- `ValueError`: "Blueprint has no parseable unit definitions"

### Tier 3 -- Behavioral Contracts

- All Unit 5 functions accept a `blueprint_dir: Path` parameter. Internally, they find blueprint files by globbing `blueprint_dir / "*.md"` (sorted alphabetically by filename for deterministic ordering). There is no named discovery function in Unit 5 -- callers that need discovery as a standalone operation use `discover_blueprint_files` from Unit 1. Unit 5 raises `FileNotFoundError` if `blueprint_dir` does not exist or contains no `.md` files.
- `parse_blueprint` globs `blueprint_dir` for all `.md` files, reads and concatenates them, and parses all unit definitions from the combined content. Tier identification is content-based: `### Tier 1` headings denote Tier 1 (description), `### Tier 2` headings denote Tier 2 (signatures/invariants), `### Tier 3` headings denote Tier 3 (error conditions/behavioral contracts). Content may be spread across multiple files or contained in a single file -- the parser is agnostic to file boundaries. Splits on `## Unit N:` heading patterns.
- `extract_unit` returns a single unit's definition. When `include_tier1=False`, the `description` field of the returned `UnitDefinition` is set to an empty string.
- `extract_upstream_contracts` returns Tier 2 signatures for upstream dependencies. When `include_tier1=False`, description content is excluded.
- `build_unit_context` produces a formatted string for task prompt inclusion. When `include_tier1=False`, Tier 1 description content is omitted from the formatted output.
- **Tier identification is content-based, not filename-based.** The parser determines which content is Tier 1 vs Tier 2/3 by matching `### Tier N` sub-heading patterns within each unit section. The blueprint uses em-dash (`—`) for Tier 2 headings and double-dash (`--`) for Tier 1 and Tier 3 headings; parsing matches on the `### Tier N` prefix only, so the dash style after the tier label is irrelevant to extraction correctness. This means `include_tier1=False` works correctly regardless of whether Tier 1 content lives in a separate file or the same file as Tier 2/3.
- **Backward compatibility:** A single `blueprint.md` file in the directory is handled identically to the split-file case.

### Tier 3 -- Dependencies

None.

---

## Unit 6: Stub Generator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 2 — Signatures

```python
import ast
from typing import Optional, Dict, Any, List
from pathlib import Path

def parse_signatures(signature_block: str) -> ast.Module: ...
def generate_stub_source(parsed_ast: ast.Module) -> str: ...
def strip_module_level_asserts(tree: ast.Module) -> ast.Module: ...
def generate_upstream_mocks(upstream_contracts: List[Dict[str, Any]]) -> Dict[str, str]: ...
def write_stub_file(unit_number: int, signature_block: str, output_dir: Path) -> Path: ...
def write_upstream_stubs(upstream_contracts: List[Dict[str, Any]], output_dir: Path) -> List[Path]: ...

# CLI wrapper (generate_stubs.py)
def main() -> None: ...
```

### Tier 2 — Invariants

```python
assert len(signature_block.strip()) > 0
assert isinstance(result, ast.Module)
assert "NotImplementedError" in result
assert "__SVP_STUB__" in result, "Stub source must contain stub sentinel"
assert result.exists()
assert result.suffix == ".py"
```

### Tier 3 -- Error Conditions

- `SyntaxError`: "Blueprint signature block is not valid Python: {details}"
- `FileNotFoundError`: "Output directory does not exist: {path}"

### Tier 3 -- Behavioral Contracts

- `parse_signatures` calls `ast.parse()` on the signature block and returns the AST.
- `generate_stub_source` transforms the AST: replaces all function bodies with `raise NotImplementedError()`, preserves import statements and class definitions, strips module-level `assert` statements. **Must prepend `__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP` as the first non-import statement (NEW IN 2.1 -- stub sentinel).**
- `strip_module_level_asserts` removes all `ast.Assert` nodes at the module level.
- `write_stub_file` combines parsing, stripping, and stub generation to produce a stub file at `{output_dir}/stub.py`.
- The generated stub must be importable without error (importability invariant).
- The CLI wrapper `main()` emits `COMMAND_SUCCEEDED` on success or `COMMAND_FAILED: [details]` on failure.

### Tier 3 -- Dependencies

- **Unit 5 (Blueprint Extractor):** Uses `extract_upstream_contracts` to obtain upstream contract signatures.

---

## Unit 7: Dependency Extractor and Import Validator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 2 — Signatures

```python
import ast
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

def extract_all_imports(blueprint_dir: Path) -> List[str]: ...
def classify_import(import_stmt: str) -> str: ...
def map_imports_to_packages(imports: List[str]) -> Dict[str, str]: ...
def create_conda_environment(env_name: str, packages: Dict[str, str],
    python_version: str = "3.11", toolchain: Optional[Dict[str, Any]] = None) -> bool: ...
def validate_imports(env_name: str, imports: List[str],
    toolchain: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str]]: ...
def create_project_directories(project_root: Path, total_units: int) -> None: ...
def validate_dependency_dag(blueprint_dir: Path) -> List[str]: ...
def derive_total_units(blueprint_dir: Path) -> int: ...
def run_infrastructure_setup(project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None) -> None: ...

# CLI wrapper (setup_infrastructure.py)
def main() -> None: ...
```

### Tier 2 — Invariants

```python
assert blueprint_dir.is_dir(), "Blueprint directory must exist"
assert all(isinstance(s, str) for s in result)
assert result > 0, "total_units must be a positive integer, never None or zero"
assert isinstance(total_units, int) and total_units > 0, \
    "total_units must be a positive integer -- never None (Bug 24 guard)"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Blueprint directory not found: {path}"
- `FileNotFoundError`: "No .md files found in blueprint directory: {path}"
- `ValueError`: "No signature blocks found in blueprint"
- `RuntimeError`: "Conda environment creation failed: {details}"
- `RuntimeError`: "Import validation failed for: {import_list}"
- `ValueError`: "DAG validation failed: forward dependency detected -- {details}"
- `TypeError`: "total_units must be a positive integer, got {type}" (Bug 24 guard)

### Tier 3 -- Behavioral Contracts

- `extract_all_imports` takes `blueprint_dir` (the path to the blueprint directory) and uses `discover_blueprint_files` from Unit 1 to find all `.md` files, then reads and concatenates their content and parses every `### Tier 2 — Signatures` code block from the combined content. This replaces the prior approach of taking a single `contracts_path`. Uses `discover_blueprint_files` from Unit 1 (not independent globbing) for consistency with `derive_total_units` and `validate_dependency_dag` -- see design rationale below.
- `create_conda_environment` creates the environment and installs packages. Always installs `testing.framework_packages` and `quality.packages` unconditionally (NEW IN 2.1). Always replaces any prior environment.
- `create_project_directories` validates that `total_units` is a positive integer before use (Bug 24 fix).
- `validate_dependency_dag` takes the blueprint directory path and uses `discover_blueprint_files` from Unit 1 to find all `.md` files, then reads and concatenates their content, parses each unit's dependency list, builds graph, verifies no forward edges, no cycles, all referenced units exist. Uses `discover_blueprint_files` from Unit 1 (not independent globbing) for consistency with `extract_all_imports` and `derive_total_units` -- see design rationale below.
- `derive_total_units` takes the blueprint directory path and uses `discover_blueprint_files` from Unit 1 to find all `.md` files, then reads and concatenates their content and counts `## Unit N:` headings. This is the canonical source for `total_units`. The function is agnostic to how many files exist or what they are named. Uses `discover_blueprint_files` from Unit 1 (not independent globbing) for consistency with `extract_all_imports` and `validate_dependency_dag` -- see design rationale below.
- `run_infrastructure_setup` orchestrates the full setup: validate DAG, extract imports, map packages, create environment, validate imports, derive `total_units` from blueprint directory (Bug 24 fix), create directories, write `total_units` to state. Uses `ARTIFACT_FILENAMES["blueprint_dir"]` to locate the blueprint directory.
- The CLI wrapper emits `COMMAND_SUCCEEDED` or `COMMAND_FAILED: [details]`.
- **Blueprint discovery design rationale:** Unit 7 uses `discover_blueprint_files` from Unit 1 (rather than globbing independently like Unit 5) because Unit 7 already depends on Unit 1 for `derive_env_name`, `load_toolchain`, `resolve_command`, `get_framework_packages`, `get_quality_packages`, etc. All three blueprint-reading functions in Unit 7 (`extract_all_imports`, `derive_total_units`, `validate_dependency_dag`) use `discover_blueprint_files` from Unit 1 for consistency. Unit 5, by contrast, globs independently to maintain its zero-dependency status -- Unit 5 has no dependencies on any other unit.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Calls `derive_env_name`, `load_toolchain`, `resolve_command`, `get_framework_packages`, `get_quality_packages`, `discover_blueprint_files`.

---

## Unit 8: Hint Prompt Assembler

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any
from pathlib import Path

def assemble_hint_prompt(hint_content: str, gate_id: str, agent_type: str,
    ladder_position: Optional[str] = None, unit_number: Optional[int] = None,
    stage: str = "") -> str: ...
def get_agent_type_framing(agent_type: str) -> str: ...
def get_ladder_position_framing(ladder_position: Optional[str]) -> str: ...
```

### Tier 2 — Invariants

```python
assert len(hint_content.strip()) > 0
assert agent_type in ("test", "implementation", "blueprint_author", "stakeholder_dialog", "diagnostic", "other")
assert "## Human Domain Hint (via Help Agent)" in result
assert hint_content in result
```

### Tier 3 -- Error Conditions

- `ValueError`: "Empty hint content"
- `ValueError`: "Unknown agent type: {type}"

### Tier 3 -- Behavioral Contracts

- `assemble_hint_prompt` produces the complete hint section using deterministic templates.
- The output is pure text -- a Markdown section ready for inclusion in a task prompt.

### Tier 3 -- Dependencies

None.

---

## Unit 9: Preparation Script

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path

KNOWN_AGENT_TYPES: List[str] = [
    "setup_agent", "stakeholder_dialog", "stakeholder_reviewer",
    "blueprint_author", "blueprint_checker", "blueprint_reviewer",
    "test_agent", "implementation_agent", "coverage_review",
    "diagnostic_agent", "integration_test_author", "git_repo_agent",
    "help_agent", "hint_agent", "redo_agent",
    "bug_triage", "repair_agent", "reference_indexing",
]

ALL_GATE_IDS: List[str] = [
    "gate_0_1_hook_activation", "gate_0_2_context_approval",
    "gate_0_3_profile_approval", "gate_0_3r_profile_revision",
    "gate_1_1_spec_draft", "gate_1_2_spec_post_review",
    "gate_2_1_blueprint_approval", "gate_2_2_blueprint_post_review",
    "gate_2_3_alignment_exhausted",
    "gate_3_1_test_validation", "gate_3_2_diagnostic_decision",
    "gate_4_1_integration_failure", "gate_4_2_assembly_exhausted",
    "gate_5_1_repo_test", "gate_5_2_assembly_exhausted",
    "gate_5_3_unused_functions",
    "gate_6_0_debug_permission", "gate_6_1_regression_test",
    "gate_6_2_debug_classification", "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible", "gate_6_5_debug_commit",
    "gate_hint_conflict",
]

def prepare_agent_task(project_root: Path, agent_type: str,
    unit_number: Optional[int] = None, ladder_position: Optional[str] = None,
    hint_content: Optional[str] = None, gate_id: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
    revision_mode: Optional[str] = None) -> Path: ...

def prepare_gate_prompt(project_root: Path, gate_id: str,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None) -> Path: ...

def load_stakeholder_spec(project_root: Path) -> str: ...
def load_blueprint(project_root: Path) -> str: ...
def load_reference_summaries(project_root: Path) -> str: ...
def load_project_context(project_root: Path) -> str: ...
def load_ledger_content(project_root: Path, ledger_name: str) -> str: ...
def load_profile_sections(project_root: Path, sections: List[str]) -> str: ...
def load_full_profile(project_root: Path) -> str: ...
def load_quality_report(project_root: Path, gate: str) -> str: ...
def load_lessons_learned_for_unit(project_root: Path, unit_number: int) -> str: ...
def get_blueprint_dir(project_root: Path) -> Path: ...

def build_task_prompt_content(agent_type: str, sections: Dict[str, str],
    hint_block: Optional[str] = None) -> str: ...

# CLI entry point
def main() -> None: ...
```

### Tier 2 — Invariants

```python
assert project_root.is_dir()
assert agent_type or gate_id
assert result.exists(), "Task prompt file must exist after preparation"
assert result.stat().st_size > 0
# Bug 22: all artifact path construction must use ARTIFACT_FILENAMES from Unit 1
# Bug 41: ALL_GATE_IDS must contain every gate ID in the pipeline
```

### Tier 3 -- Error Conditions

- `ValueError`: "Unknown agent type: {type}"
- `ValueError`: "Unknown gate ID: {gate_id}"
- `FileNotFoundError`: "Required document not found: {path}"
- `ValueError`: "Unit number required for agent type {type}"

### Tier 3 -- Behavioral Contracts

- `prepare_agent_task` assembles the task prompt file for the given agent type. **Blueprint directory discovery:** uses `get_blueprint_dir` to obtain the blueprint directory path, then passes it to `build_unit_context` (Unit 5). Passes `include_tier1=False` for `test_agent` and `implementation_agent`; passes `include_tier1=True` for all other agents.
- `load_blueprint` uses `load_blueprint_content` from Unit 1 (which internally calls `discover_blueprint_files`) to load all blueprint files from the blueprint directory. No hardcoded blueprint filenames.
- `get_blueprint_dir` returns `project_root / ARTIFACT_FILENAMES["blueprint_dir"]`. This is the single function that resolves the blueprint directory path from the artifact filename contract.
- **Proactive lessons learned (NEW IN 2.1):** `load_lessons_learned_for_unit` reads the bug catalog from `svp_2_1_lessons_learned.md`, filters entries matching the current unit by unit number or pattern classification, and returns the filtered text. If no matches, returns empty string. Called during test agent task prompt assembly -- matched entries appended under heading "Historical failure patterns for this unit -- write tests that probe these behaviors."
- `prepare_gate_prompt` assembles the gate prompt file. Raises `ValueError` for unrecognized gate IDs.
- **Gate ID consistency (Bug 41 fix):** `ALL_GATE_IDS` must be identical to the set of gate IDs in `GATE_RESPONSES` in Unit 10. A structural test must verify this.
- Profile sections extracted for agent task prompts: blueprint_author receives `readme`, `vcs`, `delivery`, `quality` sections.
- Quality report loading for agent re-pass prompts (NEW IN 2.1): when agent type is `test_agent` or `implementation_agent` and `extra_context` contains a quality report path, loads and appends it.
- All artifact paths constructed using `ARTIFACT_FILENAMES` from Unit 1 (Bug 22 fix). Blueprint paths use `ARTIFACT_FILENAMES["blueprint_dir"]` (directory), not individual filenames.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** `ARTIFACT_FILENAMES`, `load_profile`, `load_toolchain`.
- **Unit 2 (Pipeline State Schema):** `load_state` for pipeline context.
- **Unit 4 (Ledger Manager):** `read_ledger` for dialog agents.
- **Unit 5 (Blueprint Extractor):** `extract_unit`, `extract_upstream_contracts`, `build_unit_context`.
- **Unit 8 (Hint Prompt Assembler):** `assemble_hint_prompt` for hint injection.

---

## Unit 10: Routing Script and Update State

**Artifact category:** Python script (library + 3 CLI wrappers)

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path
from pipeline_state import PipelineState

# --- Agent status line vocabulary ---
AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": ["PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED", "PROFILE_COMPLETE"],
    "stakeholder_dialog": ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"],
    "stakeholder_reviewer": ["REVIEW_COMPLETE"],
    "blueprint_author": ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"],
    "blueprint_checker": ["ALIGNMENT_CONFIRMED", "ALIGNMENT_FAILED: spec", "ALIGNMENT_FAILED: blueprint"],
    "blueprint_reviewer": ["REVIEW_COMPLETE"],
    "test_agent": ["TEST_GENERATION_COMPLETE", "REGRESSION_TEST_COMPLETE"],
    "implementation_agent": ["IMPLEMENTATION_COMPLETE"],
    "coverage_review": ["COVERAGE_COMPLETE: no gaps", "COVERAGE_COMPLETE: tests added"],
    "diagnostic_agent": ["DIAGNOSIS_COMPLETE: implementation", "DIAGNOSIS_COMPLETE: blueprint", "DIAGNOSIS_COMPLETE: spec"],
    "integration_test_author": ["INTEGRATION_TESTS_COMPLETE"],
    "git_repo_agent": ["REPO_ASSEMBLY_COMPLETE"],
    "help_agent": ["HELP_SESSION_COMPLETE: no hint", "HELP_SESSION_COMPLETE: hint forwarded"],
    "hint_agent": ["HINT_ANALYSIS_COMPLETE"],
    "redo_agent": ["REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint", "REDO_CLASSIFIED: gate",
                   "REDO_CLASSIFIED: profile_delivery", "REDO_CLASSIFIED: profile_blueprint"],
    "bug_triage": ["TRIAGE_COMPLETE: build_env", "TRIAGE_COMPLETE: single_unit", "TRIAGE_COMPLETE: cross_unit",
                   "TRIAGE_NEEDS_REFINEMENT", "TRIAGE_NON_REPRODUCIBLE"],
    "repair_agent": ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"],
    "reference_indexing": ["INDEXING_COMPLETE"],
}

# Cross-agent status line (not tied to a specific agent type)
CROSS_AGENT_STATUS_LINES: Dict[str, str] = {
    "HINT_BLUEPRINT_CONFLICT": "gate_hint_conflict",
}

COMMAND_STATUS_PATTERNS: List[str] = [
    "TESTS_PASSED", "TESTS_FAILED", "TESTS_ERROR",
    "COMMAND_SUCCEEDED", "COMMAND_FAILED",
]

GATE_RESPONSES: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": ["CONTEXT APPROVED", "CONTEXT REJECTED", "CONTEXT NOT READY"],
    "gate_0_3_profile_approval": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_0_3r_profile_revision": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_1_1_spec_draft": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_1_2_spec_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_1_blueprint_approval": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_2_blueprint_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_3_alignment_exhausted": ["REVISE SPEC", "RESTART SPEC", "RETRY BLUEPRINT"],
    "gate_3_1_test_validation": ["TEST CORRECT", "TEST WRONG"],
    "gate_3_2_diagnostic_decision": ["FIX IMPLEMENTATION", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_1_integration_failure": ["ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_2_assembly_exhausted": ["FIX BLUEPRINT", "FIX SPEC"],
    "gate_5_1_repo_test": ["TESTS PASSED", "TESTS FAILED"],
    "gate_5_2_assembly_exhausted": ["RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_5_3_unused_functions": ["FIX SPEC", "OVERRIDE CONTINUE"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_2_debug_classification": ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_3_repair_exhausted": ["RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
    "gate_6_5_debug_commit": ["COMMIT APPROVED", "COMMIT REJECTED"],
    "gate_hint_conflict": ["BLUEPRINT CORRECT", "HINT CORRECT"],
}

def route(state: PipelineState, project_root: Path) -> Dict[str, str]: ...

def dispatch_agent_status(state: PipelineState, agent_type: str,
    status: str, project_root: Path) -> PipelineState: ...

def dispatch_command_status(state: PipelineState, command_type: str,
    status: str, project_root: Path) -> PipelineState: ...

def dispatch_gate_response(state: PipelineState, gate_id: str,
    response: str, project_root: Path) -> PipelineState: ...

def read_last_status(project_root: Path) -> str: ...

# CLI wrappers
def update_state_main(argv: Optional[List[str]] = None) -> None: ...
def run_tests_main(argv: Optional[List[str]] = None) -> None: ...
def run_quality_gate_main(argv: Optional[List[str]] = None) -> None: ...
```

### Tier 2 — Invariants

```python
# route() must return a dict with at least ACTION and MESSAGE keys
assert "ACTION" in result
assert "MESSAGE" in result
assert result["ACTION"] in ("invoke_agent", "run_command", "human_gate", "session_boundary", "pipeline_complete", "pipeline_held")

# All COMMAND and POST fields must be fully resolved (Bug 35 fix)
# No {env_name}, {N}, or other placeholders in emitted commands
for key in ("COMMAND", "POST", "PREPARE"):
    if key in result:
        assert "{" not in result[key], f"Unresolved placeholder in {key}"

# Gate ID consistency invariant (Bug 41 fix)
assert set(GATE_RESPONSES.keys()) == set(ALL_GATE_IDS), \
    "GATE_RESPONSES keys must match ALL_GATE_IDS"

# Two-branch routing invariant: for every sub-stage with an agent-to-gate transition,
# route() must check last_status.txt to distinguish agent-not-done from agent-done

# Exhaustive dispatch_agent_status invariant (Bug 44, 46 fix):
# dispatch_agent_status for test_agent must handle sub_stage in (None, "test_generation")
# dispatch_agent_status for coverage_review must advance sub_stage to "unit_completion"

# Exhaustive dispatch_command_status invariant (Bug 45 fix):
# dispatch_command_status for test_execution at red_run must advance to implementation on TESTS_FAILED
# dispatch_command_status for test_execution at green_run must advance to coverage_review on TESTS_PASSED

# COMMAND/POST separation invariant (Bug 47 fix):
# No COMMAND field may contain "update_state.py" -- state updates are POST-only
```

### Tier 3 -- Error Conditions

- `ValueError`: "Unknown agent status: {status}" -- when `dispatch_agent_status` receives an unrecognized status line.
- `ValueError`: "Unknown gate response: {response} for gate {gate_id}" -- when `dispatch_gate_response` receives an invalid response.
- `ValueError`: "Unknown command status: {status}" -- when `dispatch_command_status` receives an unrecognized command result.

### Tier 3 -- Behavioral Contracts

**Two-branch routing invariant (Bug 21 generalized fix).** `route()` must check `last_status.txt` for every sub-stage with an agent-to-gate transition. This is a structural invariant, not a per-stage fix. The complete list follows, in two groups distinguished by what the "done" branch emits.

**Gate-presenting entries** -- the "done" branch emits a `human_gate` action:
- Stage 0, `project_context`: check for `PROJECT_CONTEXT_COMPLETE` before presenting `gate_0_2_context_approval`
- Stage 0, `project_profile`: check for `PROFILE_COMPLETE` before presenting `gate_0_3_profile_approval`
- Stage 1, `sub_stage=None` (spec authoring): check for `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE` before presenting `gate_1_1_spec_draft` (Bug 41 fix)
- Stage 1, `sub_stage=None` (reviewer completion): check for `REVIEW_COMPLETE` before presenting `gate_1_2_spec_post_review`. Disambiguation from dialog agent status is by prefix: `REVIEW_COMPLETE` routes to Gate 1.2, while `SPEC_DRAFT_COMPLETE`/`SPEC_REVISION_COMPLETE` route to Gate 1.1
- Stage 2, `blueprint_dialog` (author completion): check for `BLUEPRINT_DRAFT_COMPLETE` or `BLUEPRINT_REVISION_COMPLETE` before presenting `gate_2_1_blueprint_approval`
- Stage 2, `blueprint_dialog` (reviewer completion): check for `REVIEW_COMPLETE` before presenting `gate_2_2_blueprint_post_review`. Disambiguation from blueprint author status is by prefix: `REVIEW_COMPLETE` routes to Gate 2.2, while `BLUEPRINT_DRAFT_COMPLETE`/`BLUEPRINT_REVISION_COMPLETE` route to Gate 2.1. Stage-level disambiguation (Stage 1 vs Stage 2) uses the current stage number from `pipeline_state.json`
- Stage 2, `alignment_check`: check for `ALIGNMENT_CONFIRMED` or `ALIGNMENT_FAILED:*` before dispatching alignment outcome. `ALIGNMENT_CONFIRMED` presents `gate_2_2_blueprint_post_review`. `ALIGNMENT_FAILED` increments iteration counter and re-enters blueprint dialog (or presents `gate_2_3_alignment_exhausted` on counter exhaustion).
- Stage 5, `sub_stage=None`: check for `REPO_ASSEMBLY_COMPLETE` before advancing to `gate_5_1_repo_test`. When `REPO_ASSEMBLY_COMPLETE` is detected, `dispatch_agent_status` advances `sub_stage` to `"repo_test"`; the gate is presented on the next `route()` call at `sub_stage="repo_test"`
- Stage 3, `fix_ladder_position == "diagnostic"`: check for `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec` before presenting `gate_3_2_diagnostic_decision`. Diagnostic escalation is not keyed on a named sub-stage value; it is triggered when `fix_ladder_position` reaches `"diagnostic"`. The sub-stage may remain at `"green_run"` or `"implementation"` during the fix ladder; `route()` must check `fix_ladder_position` to determine whether the diagnostic agent should be invoked. When the diagnostic agent completes, the routing script must present Gate 3.2, not re-invoke the diagnostic agent.
- Post-delivery debug loop, triage agent (reproducible): check for `TRIAGE_COMPLETE: single_unit` or `TRIAGE_COMPLETE: cross_unit` before presenting `gate_6_2_debug_classification`. Note: `TRIAGE_COMPLETE: build_env` does NOT present Gate 6.2 -- it routes directly to the build/environment repair agent via the fast path.
- Post-delivery debug loop, triage agent (non-reproducible): check for `TRIAGE_NON_REPRODUCIBLE` before presenting `gate_6_4_non_reproducible`
- Post-delivery debug loop, repair agent: check for `REPAIR_COMPLETE`, `REPAIR_RECLASSIFY`, or `REPAIR_FAILED` (with retries exhausted) before dispatching the repair outcome. `REPAIR_COMPLETE` routes to the success path (reassembly and debug completion) -- it does NOT present Gate 6.3. `REPAIR_RECLASSIFY` and `REPAIR_FAILED` (with retries exhausted) present `gate_6_3_repair_exhausted`.
- Post-delivery debug loop, test agent (regression test mode): check for `REGRESSION_TEST_COMPLETE` before presenting `gate_6_1_regression_test`
- Redo profile sub-stages (`redo_profile_delivery`): check for `PROFILE_COMPLETE` before presenting `gate_0_3r_profile_revision`
- Redo profile sub-stages (`redo_profile_blueprint`): check for `PROFILE_COMPLETE` before presenting `gate_0_3r_profile_revision`

**Command-presenting entries** -- the "done" branch emits a `run_command` action (a deterministic tool invocation, not a human gate):
- Stage 3, `quality_gate_a_retry`: check for `TEST_GENERATION_COMPLETE` before re-running Gate A tools. If the test agent has not yet completed, re-invoke it; if it has, run the quality gate deterministic check.
- Stage 3, `quality_gate_b_retry`: check for `IMPLEMENTATION_COMPLETE` before re-running Gate B tools. Same two-branch structure as Gate A retry.
- Stage 3, `coverage_review`: check for `COVERAGE_COMPLETE` (either `no gaps` or `tests added`) before dispatching the coverage review completion flow. If the agent has not yet completed, invoke it; if it has completed with `tests added`, run auto-format commands; if `no gaps`, advance to `unit_completion`.
- Stage 4, `sub_stage=None`: check for `INTEGRATION_TESTS_COMPLETE` before running the integration test suite. If the agent has not yet completed, re-invoke it; if it has, run the test command.

**Gates NOT governed by the two-branch invariant.** Nine gate IDs are intentionally absent from the lists above: `gate_0_1_hook_activation` (presented unconditionally at session start), `gate_6_5_debug_commit` (presented after deterministic commit preparation), `gate_hint_conflict` (presented by hint system on conflict detection), `gate_2_3_alignment_exhausted` (presented on counter exhaustion after `ALIGNMENT_FAILED`), `gate_3_1_test_validation` (presented after deterministic test run command), `gate_4_1_integration_failure` (presented after integration test command fails), `gate_4_2_assembly_exhausted` (presented on retry counter exhaustion), `gate_5_2_assembly_exhausted` (presented on Stage 5 retry exhaustion), and `gate_6_0_debug_permission` (entry gate for debug loop via `/svp:bug`).

**Stage 3 core sub-stage routing (Bug 25 fix).** `route()` must emit a distinct action for each sub-stage:
- `None` or `stub_generation`: `run_command` (stub generator script)
- `test_generation`: `invoke_agent` (test agent) -- `dispatch_agent_status` handles the transition to `quality_gate_a` automatically on `TEST_GENERATION_COMPLETE`; no two-branch check needed (not in Section 3.6 exhaustive list)
- `quality_gate_a`: `run_command` (Gate A tools)
- `quality_gate_a_retry`: `invoke_agent` or `run_command` -- two-branch applies
- `red_run`: `run_command` (pytest, expect failure)
- `implementation`: `invoke_agent` (implementation agent) -- `dispatch_agent_status` handles the transition to `quality_gate_b` automatically on `IMPLEMENTATION_COMPLETE`; no two-branch check needed (not in Section 3.6 exhaustive list)
- `quality_gate_b`: `run_command` (Gate B tools)
- `quality_gate_b_retry`: `invoke_agent` or `run_command` -- two-branch applies
- `green_run`: `run_command` (pytest, expect pass)
- `coverage_review`: `invoke_agent` (coverage review agent) -- two-branch applies: `route()` reads `last_status.txt`. If no coverage status, invokes the coverage review agent. If `COVERAGE_COMPLETE: no gaps`, advances directly to `unit_completion`. If `COVERAGE_COMPLETE: tests added`, `dispatch_agent_status` handles the auto-format-then-advance flow within a single action cycle: it emits a compound `run_command` action that executes the Gate A quality tool operations (`ruff format`, `ruff check --select E,F,I --fix`, resolved from toolchain `gate_a` ops) on the new test files, then advances `sub_stage` to `"red_run"` for red-green re-validation. The auto-format commands execute within the `coverage_review` sub-stage's completion flow inside `dispatch_agent_status` -- they do NOT require separate action cycles or multiple sequential routing calls. After auto-format, the next `route()` call sees `sub_stage == "red_run"` and emits the red-run command.
- `unit_completion`: `run_command` (complete_unit) + session boundary

**Stage 5 full sub-stage routing (Bug 26 fix).**
- `sub_stage=None`: uses the two-branch routing invariant. `route()` reads `last_status.txt`. If it contains `REPO_ASSEMBLY_COMPLETE`, this status was already processed by `dispatch_agent_status` which advanced `sub_stage` to `"repo_test"` -- so this branch is only reached when no relevant status exists, in which case it invokes `git_repo_agent`.
- `sub_stage="repo_test"`: present `gate_5_1_repo_test`
- `sub_stage="compliance_scan"`: run compliance scan script
- `sub_stage="gate_5_3"`: present `gate_5_3_unused_functions` (Bug 67 fix)
- `sub_stage="repo_complete"`: return `pipeline_complete`

**`dispatch_agent_status` for `setup_agent` -- `PROJECT_CONTEXT_REJECTED` handling:** When `dispatch_agent_status` receives `PROJECT_CONTEXT_REJECTED` from the setup agent, it does NOT advance the pipeline. The next `route()` call reads `PROJECT_CONTEXT_REJECTED` from `last_status.txt` and emits a `pipeline_held` action. This is distinct from `PROJECT_CONTEXT_COMPLETE`, which advances to the context approval gate. `pipeline_held` signals that the human cannot provide sufficient project context and the pipeline holds until the human re-engages (e.g., via a new session or by providing context externally and resuming).

**Stage 0 routing.** `route()` dispatches on `sub_stage`:
- `sub_stage == "hook_activation"`: emits a `human_gate` action for `gate_0_1_hook_activation`. Gate 0.1 may auto-approve (if hooks are already activated) or require manual activation. On `HOOKS ACTIVATED`, POST advances `sub_stage` to `"project_context"`. On `HOOKS FAILED`, presents error guidance.
- `sub_stage == "project_context"`: uses the two-branch routing invariant. `route()` reads `last_status.txt`. If it contains `PROJECT_CONTEXT_COMPLETE`, emits a `human_gate` action for `gate_0_2_context_approval`. If it contains `PROJECT_CONTEXT_REJECTED`, emits a `pipeline_held` action (human cannot provide sufficient context; pipeline holds and awaits re-engagement). Otherwise, emits an `invoke_agent` action for the setup agent. Gate 0.2 dispatch: `CONTEXT APPROVED` advances `sub_stage` to `"project_profile"`. `CONTEXT REJECTED` re-invokes the setup agent (clears `last_status.txt`, deletes current `project_context.md`, keeps `sub_stage`). `CONTEXT NOT READY` re-invokes the setup agent for further dialog (clears `last_status.txt`, keeps `sub_stage`).
- `sub_stage == "project_profile"`: uses the two-branch routing invariant. `route()` reads `last_status.txt`. If it contains `PROFILE_COMPLETE`, emits a `human_gate` action for `gate_0_3_profile_approval`. If not, emits an `invoke_agent` action for the setup agent. Gate 0.3 dispatch: `PROFILE APPROVED` calls `advance_stage` to transition to Stage 1. `PROFILE REJECTED` re-invokes the setup agent (clears `last_status.txt`, keeps `sub_stage`).

**Stage 1 routing (Bug 41 fix).** Stage 1 uses `sub_stage: None` throughout -- the two-branch routing invariant uses `last_status.txt` for dispatch, not named sub-stages.
- `sub_stage == None`: `route()` reads `last_status.txt`. If it contains `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`, emits a `human_gate` action for `gate_1_1_spec_draft`. If it contains `REVIEW_COMPLETE` (from stakeholder spec reviewer), emits a `human_gate` action for `gate_1_2_spec_post_review`. Otherwise (no relevant status), emits an `invoke_agent` action for the `stakeholder_dialog` agent.
- Gate 1.1 (`gate_1_1_spec_draft`) dispatch: `APPROVE` finalizes the spec (writes completion marker) and calls `advance_stage` to transition to Stage 2. `REVISE` re-invokes the stakeholder dialog agent in revision mode (clears `last_status.txt`, keeps `sub_stage` at `None`). `FRESH REVIEW` invokes the stakeholder spec reviewer agent; after `REVIEW_COMPLETE`, the next `route()` call reads `last_status.txt` and presents `gate_1_2_spec_post_review`.
- Gate 1.2 (`gate_1_2_spec_post_review`) dispatch: `APPROVE` finalizes the spec and calls `advance_stage` to Stage 2. `REVISE` re-invokes the stakeholder dialog agent in revision mode (incorporates the reviewer's critique). `FRESH REVIEW` re-invokes the stakeholder spec reviewer for another cold review.

**Stage 2 routing (Bug 23 fix).**
- When `stage == "2"` and `sub_stage` is `None` or `"blueprint_dialog"`: uses the two-branch routing invariant. `route()` reads `last_status.txt`:
  - If `last_status.txt` contains `BLUEPRINT_DRAFT_COMPLETE` or `BLUEPRINT_REVISION_COMPLETE`: emits a `human_gate` action for `gate_2_1_blueprint_approval`. Both statuses map to Gate 2.1 -- Gate 2.2 is only presented after a blueprint reviewer completes.
  - If `last_status.txt` contains `REVIEW_COMPLETE` (from blueprint reviewer): emits a `human_gate` action for `gate_2_2_blueprint_post_review`.
  - Otherwise (no relevant status): emits an `invoke_agent` action for the blueprint author.
- Gate 2.1 (`gate_2_1_blueprint_approval`) dispatch: `APPROVE` calls `enter_alignment_check` (Unit 3) to transition `sub_stage` to `"alignment_check"` -- does NOT call `advance_stage`. `REVISE` resets `sub_stage` to `None` for fresh blueprint dialog. `FRESH REVIEW` invokes the blueprint reviewer; after `REVIEW_COMPLETE`, presents `gate_2_2_blueprint_post_review`.
- When `stage == "2"` and `sub_stage == "alignment_check"`: uses the two-branch routing invariant. `route()` reads `last_status.txt`:
  - If it contains `ALIGNMENT_CONFIRMED`: emits a `human_gate` action for `gate_2_2_blueprint_post_review` (human reviews alignment outcome). POST command for APPROVE calls `complete_alignment_check` (Unit 3) which calls `advance_stage` to Pre-Stage-3.
  - If it contains `ALIGNMENT_FAILED: spec` or `ALIGNMENT_FAILED: blueprint`: checks alignment iteration count. If under limit, increments `alignment_iteration` and resets `sub_stage` to `None` (re-enter blueprint dialog). If at limit, presents `gate_2_3_alignment_exhausted`.
  - Otherwise (no status yet): emits an `invoke_agent` action for the `blueprint_checker`.
- Gate 2.2 (`gate_2_2_blueprint_post_review`) dispatch: `APPROVE` calls `complete_alignment_check` to advance to Pre-Stage-3. `REVISE` resets `sub_stage` to `None` for fresh blueprint dialog. `FRESH REVIEW` invokes the blueprint reviewer.
- Gate 2.3 (`gate_2_3_alignment_exhausted`) dispatch: `RETRY BLUEPRINT` resets `alignment_iteration` and `sub_stage` to `None` (re-enter blueprint dialog). `REVISE SPEC` initiates targeted spec revision, then `restart_from_stage` to Stage 2. `RESTART SPEC` calls `restart_from_stage` to Stage 1.

**Post-delivery debug loop routing.** When `stage == "5"` and `debug_session is not None`, `route()` dispatches on `debug_session.phase`:
- **`triage_readonly`:** Emits an `invoke_agent` action for `bug_triage` in read-only mode. After triage agent completes, uses two-branch pattern: reads `last_status.txt`. If it contains `TRIAGE_COMPLETE: build_env`, `TRIAGE_COMPLETE: single_unit`, `TRIAGE_COMPLETE: cross_unit`, `TRIAGE_NON_REPRODUCIBLE`, or `TRIAGE_NEEDS_REFINEMENT`: runs `sync_debug_docs.py` as a `run_command` action (Bug 87 doc sync -- gated by `.svp/doc_sync_done` marker, idempotent), then presents `gate_6_0_debug_permission` for authorization. If it contains `TRIAGE_NEEDS_REFINEMENT`, re-invokes the triage agent with refinement context (bounded by `triage_refinement_count` in `debug_session`, default limit 2; if limit reached, presents `gate_6_4_non_reproducible`). `TRIAGE_NEEDS_REFINEMENT` is not governed by the two-branch invariant -- it triggers same-agent re-invocation. If it contains `TRIAGE_NON_REPRODUCIBLE`, presents `gate_6_4_non_reproducible`.
- Gate 6.0 (`gate_6_0_debug_permission`) dispatch: `AUTHORIZE DEBUG` calls `authorize_debug_session` (Unit 3), advances phase to `"triage"`, activates debug write rules (delivered repo path, lessons learned writable). `ABANDON DEBUG` calls `abandon_debug_session` (Unit 3), returns to "Stage 5 complete."
- **`triage`:** After authorization, triage agent runs with write access. After classification status: first runs `sync_debug_docs.py` as a `run_command` action if not already done (Bug 87 doc sync -- gated by `.svp/doc_sync_done` marker). Then uses two-branch pattern: if `last_status.txt` contains `TRIAGE_COMPLETE: single_unit` or `TRIAGE_COMPLETE: cross_unit`, presents `gate_6_2_debug_classification`. If `TRIAGE_COMPLETE: build_env`, enters build/env fast path (repair agent, phase `"repair"`).
- Gate 6.2 (`gate_6_2_debug_classification`) dispatch: `FIX UNIT` calls `set_debug_classification`, then `update_debug_phase("stage3_reentry")`, then `rollback_to_unit(state, N)` where N is the lowest affected unit -- this invalidates all verified units >= N, deletes their source/test files, sets stage to "3" with sub_stage None, and clears `last_status.txt` to prevent stale re-trigger after rebuild. `FIX BLUEPRINT` initiates targeted blueprint revision, restarts from Stage 2 (full pipeline re-entry). `FIX SPEC` initiates targeted spec revision, restarts from Stage 1.
- **`stage3_reentry` phase routing:** When `debug_session.phase == "stage3_reentry"`, Gate 6.2 FIX UNIT has already called `rollback_to_unit` which set `stage: "3"`, `current_unit: N`, `sub_stage: None`, and invalidated all verified units >= N (removing them from `verified_units` and deleting their source/test files). The `route()` function falls through to normal Stage 5 routing (which now sees stage "3") and the pipeline rebuilds from unit N forward through all remaining units. Quality Gates A and B run normally during re-entry. After all units complete, `route()` transitions to the repair success path: reassembly and debug completion (Section 12.17.6), which runs all tests (unit, regression, integration), performs full Stage 5 repo reassembly, updates lessons learned, and presents `gate_6_5_debug_commit`. (Bug 55 correction: the original description incorrectly stated that verified_units was not modified and only the affected unit was reprocessed. The correct behavior is full rollback and rebuild from unit N forward.)
- **`repair`:** Emits an `invoke_agent` action for `repair_agent`. After agent completes, uses two-branch pattern: if `last_status.txt` contains `REPAIR_COMPLETE`, routes to the success path -- reassembly and debug completion (Section 12.17.6), which runs all tests (unit, regression, integration), performs full Stage 5 repo reassembly, updates lessons learned, and then presents `gate_6_5_debug_commit` for commit approval. `REPAIR_COMPLETE` does NOT present Gate 6.3. If `REPAIR_FAILED`, checks repair attempt count -- if under limit, re-invokes repair agent; if exhausted, presents `gate_6_3_repair_exhausted`. If `REPAIR_RECLASSIFY`, presents `gate_6_3_repair_exhausted` for the human to decide (RETRY REPAIR, RECLASSIFY BUG, or ABANDON DEBUG).
- Gate 6.3 (`gate_6_3_repair_exhausted`) dispatch: `RETRY REPAIR` resets repair counter and re-invokes repair agent. `RECLASSIFY BUG` presents `gate_6_2_debug_classification` for reclassification. `ABANDON DEBUG` calls `abandon_debug_session`, returns to "Stage 5 complete."
- Gate 6.4 (`gate_6_4_non_reproducible`) dispatch: `RETRY TRIAGE` re-invokes triage agent. `ABANDON DEBUG` calls `abandon_debug_session`, returns to "Stage 5 complete."
- **`regression_test`:** Uses two-branch routing invariant. Reads `last_status.txt`: if it does not contain `REGRESSION_TEST_COMPLETE`, emits an `invoke_agent` action for test agent in regression test mode. If it contains `REGRESSION_TEST_COMPLETE`, emits a `human_gate` action for `gate_6_1_regression_test`.
- Gate 6.1 (`gate_6_1_regression_test`) dispatch: `TEST CORRECT` proceeds to lessons learned update and commit preparation. `TEST WRONG` re-invokes test agent to rewrite the regression test.
- Gate 6.5 (`gate_6_5_debug_commit`) dispatch: `COMMIT APPROVED` proceeds with commit and push, then calls `complete_debug_session`. `COMMIT REJECTED` allows human to edit or abort the commit.

**Redo profile sub-stage routing (Bug 43 fix).** When `sub_stage` is `"redo_profile_delivery"` or `"redo_profile_blueprint"`, `route()` uses the two-branch routing invariant. Reads `last_status.txt`: if it contains `PROFILE_COMPLETE`, emits a `human_gate` action for `gate_0_3r_profile_revision`. Otherwise, emits an `invoke_agent` action for the setup agent in targeted revision mode. Gate 0.3r dispatch: `PROFILE APPROVED` calls `complete_redo_profile_revision` (Unit 3) -- for `redo_profile_delivery`, restores snapshot position; for `redo_profile_blueprint`, restarts from Stage 2. `PROFILE REJECTED` re-invokes setup agent (clears `last_status.txt`, keeps sub_stage).

**Gate ID consistency (Bug 41 fix).** The set of gate IDs in `GATE_RESPONSES` must be identical to `ALL_GATE_IDS` in Unit 9. A structural regression test must verify this. **Terminology note:** The spec uses the term `GATE_VOCABULARY` (Section 3.6, Bug 43) to refer to the routing module's gate dispatch table. In the blueprint and implementation, this is `GATE_RESPONSES`. These are the same artifact -- `GATE_VOCABULARY` is the spec-level name and `GATE_RESPONSES` is the implementation-level name. The universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`) verifies cross-unit consistency using `GATE_RESPONSES` (from Unit 10) and `ALL_GATE_IDS` (from Unit 9).

**Cross-agent status handling (`HINT_BLUEPRINT_CONFLICT`).** Any agent that receives a human domain hint may return `HINT_BLUEPRINT_CONFLICT: [details]` instead of its normal terminal status line. This is a cross-agent status -- it is not listed under any specific agent type in `AGENT_STATUS_LINES` but is recognized by `dispatch_agent_status` via prefix matching against `CROSS_AGENT_STATUS_LINES`. When detected, `dispatch_agent_status` does NOT perform a normal agent-type-specific transition. Instead, the next `route()` call reads `HINT_BLUEPRINT_CONFLICT` from `last_status.txt` and emits a `human_gate` action for `gate_hint_conflict`. Gate dispatch: `BLUEPRINT CORRECT` discards the hint and re-invokes the original agent (clears `last_status.txt`, preserves current pipeline position). `HINT CORRECT` initiates targeted document revision and restart.

**Routing output resolution (Bug 35 fix).** All COMMAND, PREPARE, and POST fields must be fully resolved -- no placeholders.

**Quality gate execution.** `run_quality_gate_main` reads the gate identifier (`gate_a`, `gate_b`, or `gate_c`) from CLI args, reads operations from toolchain, resolves each operation with `"quality."` prefix, executes sequentially. Emits `COMMAND_SUCCEEDED` or `COMMAND_FAILED: quality residuals`.

**Repo collision avoidance (NEW IN 2.1).** When Stage 5 routing prepares the git repo agent invocation, the routing script must check if `delivered_repo_path` exists in `pipeline_state.json` and if that directory exists on disk. If the directory exists, it is renamed to `projectname-repo.bak.YYYYMMDD-HHMMSS` (using the current UTC timestamp) before the agent runs. This applies on every Stage 5 entry regardless of whether the current pass is the first pass or a redo pass. The `delivered_repo_path` persists in `pipeline_state.json` across redo restarts and is always checked. After rename, the git repo agent receives a clean target path. The `delivered_repo_path` in state is updated after successful assembly to reflect the new canonical path (`projectname-repo/`).

**`dispatch_agent_status` null sub_stage handling for test_agent (Bug 44 fix).** `dispatch_agent_status` for `test_agent` must handle `sub_stage in (None, "test_generation")` when the status line is `TEST_GENERATION_COMPLETE`. Stage 3 routing normalizes `sub_stage=None` to `test_generation` for routing purposes, but the test agent may complete while `sub_stage` is still `None`. The dispatch must accept both values and produce the same state transition (advancing to `quality_gate_a`). If the dispatch only checks `sub_stage == "test_generation"` and ignores `None`, the pipeline loops indefinitely re-invoking the test agent. A regression test (`test_bug44_null_substage_dispatch.py`) must verify that `dispatch_agent_status` for `test_agent` produces a state transition when `sub_stage` is `None` and the status line is `TEST_GENERATION_COMPLETE`.

**`dispatch_command_status` for test_execution state advancement (Bug 45 fix).** `dispatch_command_status` for `test_execution` must advance `sub_stage` for each expected status/sub_stage combination:
- At `sub_stage == "red_run"`, `TESTS_FAILED` must advance `sub_stage` to `"implementation"`. A no-op return is invalid -- it causes an infinite loop re-running the red run.
- At `sub_stage == "green_run"`, `TESTS_PASSED` must advance `sub_stage` to `"coverage_review"`. A no-op return is invalid -- it causes an infinite loop re-running the green run.
- `TESTS_ERROR` at any sub_stage triggers the error handling flow (regeneration or diagnostic escalation, depending on retry count).
A regression test (`test_bug45_test_execution_dispatch.py`) must verify both advancement transitions.

**`dispatch_agent_status` for coverage_review state advancement (Bug 46 fix).** `dispatch_agent_status` for `coverage_review` must advance `sub_stage` to `"unit_completion"` when `COVERAGE_COMPLETE` is received (either `COVERAGE_COMPLETE: no gaps` or `COVERAGE_COMPLETE: tests added`, after any post-completion auto-formatting). A bare `return state` is invalid -- it causes an infinite loop re-invoking the coverage review agent. This is an instance of the exhaustive dispatch_agent_status invariant (Section 3.6). A regression test (`test_bug46_coverage_dispatch.py`) must verify this advancement.

**COMMAND/POST separation invariant (Bug 47 fix).** The `unit_completion` routing action's COMMAND field must not embed `update_state.py` calls or any other state update invocations. State updates are exclusively the responsibility of POST commands. If both COMMAND and POST invoke `update_state.py` for the same phase, the state update runs twice: the first call advances `current_unit`, and the second call raises `TransitionError` because the unit is no longer current. The COMMAND should only write the completion marker and status; the POST command handles the state transition via `update_state.py --phase unit_completion`. This invariant applies to all routing action blocks, not just `unit_completion` -- no COMMAND field may embed state update calls. A regression test (`test_bug47_unit_completion_double_dispatch.py`) must verify that the `unit_completion` routing action's COMMAND field does not contain `update_state.py` or any state update invocation, and that state updates are exclusively in the POST command.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** `derive_env_name`, `load_config`, `load_toolchain`, `resolve_command`, `get_quality_gate_operations`, `ARTIFACT_FILENAMES`.
- **Unit 2 (Pipeline State Schema):** `load_state`, `save_state`, `PipelineState`.
- **Unit 3 (State Transition Engine):** All transition functions.

---

## Unit 11: Command Logic Scripts

**Artifact category:** Python script

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any
from pathlib import Path

# cmd_save.py
def cmd_save_main(project_root: Path) -> None: ...

# cmd_quit.py
def cmd_quit_main(project_root: Path) -> None: ...

# cmd_status.py
def cmd_status_main(project_root: Path) -> None: ...

# cmd_clean.py
def cmd_clean_main(project_root: Path) -> None: ...
```

### Tier 2 — Invariants

```python
assert project_root.is_dir()
```

### Tier 3 -- Error Conditions

- `RuntimeError`: "Cannot clean: workspace not found at {path}"
- `RuntimeError`: "Cannot clean: Stage 5 not complete"

### Tier 3 -- Behavioral Contracts

- `cmd_save_main` flushes state, verifies integrity, confirms.
- `cmd_quit_main` runs save, then exits.
- `cmd_status_main` reports: project name, pipeline toolchain, quality summary (pipeline and delivery), delivery summary, current stage/sub-stage/unit, pass history. Quality summary format: "Quality: ruff + mypy (pipeline), {profile_linter} + {profile_type_checker} (delivery)" (NEW IN 2.1).
- `cmd_clean_main` offers archive, delete, or keep. Removes conda environment. Never touches delivered repo.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** `load_config`, `load_profile`, `derive_env_name`.
- **Unit 2 (Pipeline State Schema):** `load_state`.
- **Unit 4 (Ledger Manager):** For save operations.

---

## Unit 12: Hook Configurations

**Artifact category:** JSON + Shell scripts (non-Python deliverables)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List
import json

HOOKS_JSON_SCHEMA: Dict[str, Any] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Write",
                "hooks": [{"type": "command", "command": ".claude/scripts/write_authorization.sh"}]
            },
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": ".claude/scripts/non_svp_protection.sh"}]
            },
        ],
        "PostToolUse": [
            {
                "matcher": "Write",
                "hooks": [{"type": "command", "command": ".claude/scripts/stub_sentinel_check.sh"}]
            },
        ]
    }
}

def check_write_authorization(tool_name: str, file_path: str, pipeline_state_path: str) -> int: ...
def check_svp_session(env_var_name: str) -> int: ...
def check_stub_sentinel(file_path: str) -> int: ...

SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

HOOKS_JSON_CONTENT: str
WRITE_AUTHORIZATION_SH_CONTENT: str
NON_SVP_PROTECTION_SH_CONTENT: str
STUB_SENTINEL_CHECK_SH_CONTENT: str
```

### Tier 2 — Invariants

```python
assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"
assert "hooks" in HOOKS_JSON_SCHEMA

hooks_parsed = json.loads(HOOKS_JSON_CONTENT)
assert "hooks" in hooks_parsed
for entry in hooks_parsed["hooks"]["PreToolUse"]:
    assert "matcher" in entry
    assert "hooks" in entry
    for handler in entry["hooks"]:
        assert handler["type"] == "command"
        assert "command" in handler

# PostToolUse stub sentinel hook (NEW IN 2.1)
assert "PostToolUse" in hooks_parsed["hooks"]

assert WRITE_AUTHORIZATION_SH_CONTENT.startswith("#!/")
assert NON_SVP_PROTECTION_SH_CONTENT.startswith("#!/")
assert STUB_SENTINEL_CHECK_SH_CONTENT.startswith("#!/")
assert SVP_ENV_VAR in NON_SVP_PROTECTION_SH_CONTENT
assert "__SVP_STUB__" in STUB_SENTINEL_CHECK_SH_CONTENT

assert "project_profile.json" in WRITE_AUTHORIZATION_SH_CONTENT
assert "toolchain.json" in WRITE_AUTHORIZATION_SH_CONTENT
assert "ruff.toml" in WRITE_AUTHORIZATION_SH_CONTENT
assert "delivered_repo_path" in WRITE_AUTHORIZATION_SH_CONTENT
```

### Tier 3 -- Error Conditions

- Exit code 2 from `write_authorization.sh`: blocks the write.
- Exit code 2 from `non_svp_protection.sh`: blocks bash execution.
- Exit code 2 from `stub_sentinel_check.sh`: "Write blocked: stub sentinel detected in implementation file {path}. Re-read the blueprint Tier 2 signatures and write the implementation, not the stub."

### Tier 3 -- Behavioral Contracts

- `hooks.json` uses the correct Claude Code hook configuration schema (Bug 17 fix). Note: `.claude/scripts/` paths in hook command fields are runtime paths after the launcher copies hooks from the plugin source at `svp/hooks/scripts/` into the project workspace.
- `write_authorization.sh` implements two-tier path authorization with all SVP 2.1 additions: `ruff.toml` permanently read-only, delivered repo path writable during authorized debug sessions, lessons learned document writable during authorized debug sessions.
- **Stub sentinel hook (NEW IN 2.1):** `PostToolUse` command hook. Matcher: Write tool calls. Handler: `stub_sentinel_check.sh`. The script checks if the written file is under `src/unit_N/` and is a `.py` file. If so, greps for `__SVP_STUB__`. If found, exits with code 2 and error message. This fires on `PostToolUse` (not `PreToolUse`) because it validates content that was written.
- `non_svp_protection.sh` checks for `SVP_PLUGIN_ACTIVE`.
- **Dual write-path:** Hooks only control agent writes through Claude Code's Write tool. Quality tool auto-fix and assembly scripts modify files via subprocess and bypass hooks. This is correct by design.

### Tier 3 -- Dependencies

- **Unit 2 (Pipeline State Schema):** `write_authorization.sh` reads `pipeline_state.json`.

---

## Unit 13: Dialog Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

SETUP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "setup_agent", "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}
STAKEHOLDER_DIALOG_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "stakeholder_dialog_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}
BLUEPRINT_AUTHOR_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_author_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

SETUP_AGENT_STATUS: List[str] = ["PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED", "PROFILE_COMPLETE"]
STAKEHOLDER_DIALOG_STATUS: List[str] = ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"]
BLUEPRINT_AUTHOR_STATUS: List[str] = ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"]

SETUP_AGENT_MD_CONTENT: str
STAKEHOLDER_DIALOG_AGENT_MD_CONTENT: str
BLUEPRINT_AUTHOR_AGENT_MD_CONTENT: str
```

### Tier 2 — Invariants

```python
# Setup Agent UX rules (spec Section 6.4)
assert "Rule 1" in SETUP_AGENT_MD_CONTENT and "Plain-language" in SETUP_AGENT_MD_CONTENT
assert "Rule 2" in SETUP_AGENT_MD_CONTENT and "recommendation" in SETUP_AGENT_MD_CONTENT.lower()
assert "Rule 3" in SETUP_AGENT_MD_CONTENT and "defaults" in SETUP_AGENT_MD_CONTENT.lower()
assert "Rule 4" in SETUP_AGENT_MD_CONTENT and "Progressive disclosure" in SETUP_AGENT_MD_CONTENT

# Setup Agent must embed complete profile schema with canonical field names (spec Section 30)
assert "delivery" in SETUP_AGENT_MD_CONTENT
assert "environment_recommendation" in SETUP_AGENT_MD_CONTENT
assert "quality" in SETUP_AGENT_MD_CONTENT

# Blueprint Author Rules P1-P4 (RFC-2, spec Section 8.1)
assert "Rule P1" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
assert "Rule P2" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
assert "Rule P3" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
assert "Rule P4" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT

# All *_MD_CONTENT must be valid Claude Code agent definitions
```

### Tier 3 -- Behavioral Contracts

- **Setup Agent:** Operates in project context mode, project profile mode, and targeted revision mode. Profile dialog covers six areas including Area 5 (quality preferences, NEW IN 2.1), Area 6 (agent model configuration, NEW IN 2.1.1), GitHub repository configuration in Area 1 (NEW IN 2.1.1), and README mode in Area 2 (NEW IN 2.1.1). Writes files using `ARTIFACT_FILENAMES` constants. System prompt must include Rules 1-4 verbatim as numbered behavioral requirements. `SETUP_AGENT_MD_CONTENT` must embed the complete `project_profile.json` schema structure with exact canonical field names matching `DEFAULT_PROFILE` in Unit 1 (including `pipeline.agent_models`, `vcs.github`, `readme.mode`, and `readme.existing_path`), so the agent's JSON output uses identical section and field names.
- **Blueprint Author Agent:** Receives profile sections (`readme`, `vcs`, `delivery`, `quality`). Produces blueprint files in the `blueprint/` directory (currently `blueprint_prose.md` and `blueprint_contracts.md` as paired output, but the system is agnostic to the exact filenames). Encodes tool preferences as behavioral contracts (Layer 1). **Unit-level preference capture (RFC-2):** The blueprint author agent definition includes Rules P1-P4 for capturing domain preferences during the decomposition dialog: P1 (ask at the unit level), P2 (domain language only), P3 (progressive disclosure), P4 (conflict detection at capture time). Captured preferences are recorded as a `### Preferences` subsection within each unit's Tier 1 description. Absence means "no preferences." Authority: spec > contracts > preferences.

### Tier 3 -- Dependencies

- **Unit 4 (Ledger Manager):** Dialog agents operate on conversation ledgers.
- **Unit 9 (Preparation Script):** Task prompt content is assembled by Unit 9.

---

## Unit 14: Review and Checker Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

STAKEHOLDER_REVIEWER_FRONTMATTER: Dict[str, Any] = {
    "name": "stakeholder_reviewer", "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}
BLUEPRINT_CHECKER_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_checker", "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}
BLUEPRINT_REVIEWER_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_reviewer", "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

STAKEHOLDER_REVIEWER_STATUS: List[str] = ["REVIEW_COMPLETE"]
BLUEPRINT_CHECKER_STATUS: List[str] = ["ALIGNMENT_CONFIRMED", "ALIGNMENT_FAILED: spec", "ALIGNMENT_FAILED: blueprint"]
BLUEPRINT_REVIEWER_STATUS: List[str] = ["REVIEW_COMPLETE"]

STAKEHOLDER_REVIEWER_MD_CONTENT: str
BLUEPRINT_CHECKER_MD_CONTENT: str
BLUEPRINT_REVIEWER_MD_CONTENT: str
```

### Tier 2 — Invariants

```python
# Blueprint Checker must validate internal consistency of prose/contracts split:
# every unit in prose must have a corresponding contracts entry and vice versa
```

### Tier 3 -- Behavioral Contracts

- **Blueprint Checker (EXPANDED for SVP 2.1):** Receives all blueprint files discovered from the blueprint directory (via Unit 9's task prompt assembly, which uses `discover_blueprint_files` from Unit 1). Validates internal consistency: every `## Unit N:` heading found across all files must have corresponding Tier 1, Tier 2, and Tier 3 content somewhere in the discovered files. Validates alignment, DAG acyclicity, Layer 2 preference coverage (including quality preferences). **Receives pattern catalog section of `svp_2_1_lessons_learned.md` -- produces advisory risk section identifying structural features matching known failure patterns (P1-P8+). Advisory only -- does not block approval.** The checker is agnostic to the number or names of blueprint files -- it validates the combined content. **Preference-contract consistency (RFC-2):** For each unit that has a Preferences subsection in Tier 1, verify that no stated preference contradicts a Tier 2 signature or Tier 3 behavioral contract. Report as a non-blocking warning (not an alignment failure), since preferences are non-binding.
- **Stakeholder Spec Reviewer:** Unchanged.
- **Blueprint Reviewer:** Unchanged.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** Task prompt content is assembled by Unit 9.

---

## Unit 15: Construction Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

TEST_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "test_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Bash", "Glob", "Grep"],
}
IMPLEMENTATION_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "implementation_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Bash", "Glob", "Grep"],
}
COVERAGE_REVIEW_FRONTMATTER: Dict[str, Any] = {
    "name": "coverage_review_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Bash", "Glob", "Grep"],
}

TEST_AGENT_STATUS: List[str] = ["TEST_GENERATION_COMPLETE", "REGRESSION_TEST_COMPLETE"]
IMPLEMENTATION_AGENT_STATUS: List[str] = ["IMPLEMENTATION_COMPLETE"]
COVERAGE_REVIEW_STATUS: List[str] = ["COVERAGE_COMPLETE: no gaps", "COVERAGE_COMPLETE: tests added"]

TEST_AGENT_MD_CONTENT: str
IMPLEMENTATION_AGENT_MD_CONTENT: str
COVERAGE_REVIEW_AGENT_MD_CONTENT: str
```

### Tier 3 -- Behavioral Contracts

- **Test Agent:** Receives blueprint content with `include_tier1=False` (no Tier 1 descriptions -- only Tier 2 signatures and Tier 3 contracts). System prompt states quality tools will auto-format output. Receives historical failure patterns for current unit when available.
- **Implementation Agent:** Receives blueprint content with `include_tier1=False` (no Tier 1 descriptions -- only Tier 2 signatures and Tier 3 contracts). System prompt states quality tools will auto-format, lint, and type-check output.
- **Coverage Review Agent:** Unchanged.

### Tier 3 -- Dependencies

- **Unit 6 (Stub Generator):** Stub generation produces files test agents write tests against.
- **Unit 9 (Preparation Script):** Task prompt content assembled by Unit 9.

---

## Unit 16: Diagnostic and Classification Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

DIAGNOSTIC_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "diagnostic_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}
REDO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "redo_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}

DIAGNOSTIC_AGENT_STATUS: List[str] = [
    "DIAGNOSIS_COMPLETE: implementation", "DIAGNOSIS_COMPLETE: blueprint", "DIAGNOSIS_COMPLETE: spec",
]
REDO_AGENT_STATUS: List[str] = [
    "REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint", "REDO_CLASSIFIED: gate",
    "REDO_CLASSIFIED: profile_delivery", "REDO_CLASSIFIED: profile_blueprint",
]

DIAGNOSTIC_AGENT_MD_CONTENT: str
REDO_AGENT_MD_CONTENT: str
```

### Tier 3 -- Behavioral Contracts

- **Diagnostic Agent:** Three-hypothesis discipline. Dual-format output. Unchanged.
- **Redo Agent:** Five classifications including `profile_delivery` and `profile_blueprint`. Unchanged from v2.0.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** Task prompt content assembled by Unit 9.

---

## Unit 17: Support Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

HELP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "help_agent", "model": "claude-sonnet-4-6",
    "tools": ["Read", "Glob", "Grep", "WebSearch"],
}
HINT_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "hint_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}

HELP_AGENT_STATUS: List[str] = ["HELP_SESSION_COMPLETE: no hint", "HELP_SESSION_COMPLETE: hint forwarded"]
HINT_AGENT_STATUS: List[str] = ["HINT_ANALYSIS_COMPLETE"]

HELP_AGENT_MD_CONTENT: str
HINT_AGENT_MD_CONTENT: str
```

### Tier 3 -- Behavioral Contracts

- **Help Agent:** Read-only. Uses `claude-sonnet-4-6`. Unchanged.
- **Hint Agent:** Reactive and proactive modes. Unchanged.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** Task prompt content assembled by Unit 9.

---

## Unit 18: Utility Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

REFERENCE_INDEXING_FRONTMATTER: Dict[str, Any] = {
    "name": "reference_indexing_agent", "model": "claude-sonnet-4-6",
    "tools": ["Read", "Glob", "Grep"],
}
INTEGRATION_TEST_AUTHOR_FRONTMATTER: Dict[str, Any] = {
    "name": "integration_test_author", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Bash", "Glob", "Grep"],
}
GIT_REPO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "git_repo_agent", "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

REFERENCE_INDEXING_STATUS: List[str] = ["INDEXING_COMPLETE"]
INTEGRATION_TEST_AUTHOR_STATUS: List[str] = ["INTEGRATION_TESTS_COMPLETE"]
GIT_REPO_AGENT_STATUS: List[str] = ["REPO_ASSEMBLY_COMPLETE"]

REFERENCE_INDEXING_MD_CONTENT: str
INTEGRATION_TEST_AUTHOR_MD_CONTENT: str
GIT_REPO_AGENT_MD_CONTENT: str
```

### Tier 2 — Invariants

```python
# GIT_REPO_AGENT_MD_CONTENT must contain:
assert "Repository Location" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must contain Repository Location section"
assert "sibling" in GIT_REPO_AGENT_MD_CONTENT.lower() or "same level" in GIT_REPO_AGENT_MD_CONTENT.lower(), \
    "Must specify sibling directory creation"
assert "11" in GIT_REPO_AGENT_MD_CONTENT or "eleven" in GIT_REPO_AGENT_MD_CONTENT.lower(), \
    "Must specify 11 sequential commits"
assert "blueprint" in GIT_REPO_AGENT_MD_CONTENT.lower(), \
    "Must reference blueprint directory discovery for docs/ delivery"
assert "discover" in GIT_REPO_AGENT_MD_CONTENT.lower() or "glob" in GIT_REPO_AGENT_MD_CONTENT.lower() or "*.md" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must instruct discovery-based blueprint file delivery"
assert "project_context.md" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must reference project_context.md for docs/ delivery"
assert "stakeholder_spec.md" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must reference stakeholder_spec.md for docs/ delivery"
assert "docs/history/" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must reference docs/history/ for version history delivery"
assert "docs/references/" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must reference docs/references/ for reference delivery"
assert "pyproject.toml" in GIT_REPO_AGENT_MD_CONTENT
assert "pythonpath" in GIT_REPO_AGENT_MD_CONTENT.lower(), \
    "Must specify pytest path configuration"
assert "__SVP_STUB__" in GIT_REPO_AGENT_MD_CONTENT, \
    "Must include stub sentinel validation instruction"
assert "src.unit_" in GIT_REPO_AGENT_MD_CONTENT or "cross-unit import" in GIT_REPO_AGENT_MD_CONTENT.lower(), \
    "Must include cross-unit import rewrite instruction"
```

### Tier 3 -- Behavioral Contracts

- **Git Repo Agent (EXPANDED for SVP 2.1):** Creates the delivered git repository in `{project_name}-repo/` at the **same level as the project workspace** (sibling directory). The agent definition must contain a "Repository Location" section with this instruction: "`projectname-repo/` is created at the same level as the project workspace directory, not inside it. Working directory during assembly is the project workspace root -- the agent must construct the repo path as `../projectname-repo/` or as an absolute path derived from the workspace root's parent."

  **11 sequential commits in order:** (1) Conda environment file, dependency list, directory structure. (2) Stakeholder spec. (3) Blueprint (all `.md` files discovered from the `blueprint/` directory). (4) Each unit with implementation and tests (sequential, topological). (5) Integration tests. (6) Project configuration (entry point, README). (7) Document version history (`docs/history/`). (8) Reference documents and summaries (`docs/references/`). (9) Project context (`docs/project_context.md`). (10) Quality tool configuration files. (11) Changelog (if `vcs.changelog` is not `"none"`).

  **All `docs/` deliverables explicitly:** Deliver `stakeholder_spec.md` to `docs/stakeholder_spec.md`. Deliver all blueprint `.md` files from `blueprint/` to `docs/` (discovered dynamically -- e.g., `blueprint_prose.md` to `docs/blueprint_prose.md`, `blueprint_contracts.md` to `docs/blueprint_contracts.md`, or whatever files exist). Deliver version history to `docs/history/`. Deliver `project_context.md` to `docs/project_context.md`. Deliver references to `docs/references/`.

  **Pytest path configuration:** The delivered `pyproject.toml` must contain `[tool.pytest.ini_options]` with appropriate `pythonpath` configuration.

  **Cross-unit import rewrite:** Rewrite all cross-unit imports from `src.unit_N` form to final module paths as specified in the blueprint file tree.

  **Stub sentinel validation:** After assembly, scan all Python source files for `__SVP_STUB__`. Any match is an immediate structural validation failure.

  **Quality Gate C:** Runs during structural validation. `ruff format --check`, `ruff check`, `mypy` (without `--ignore-missing-imports`), then unused exported function detection via `ruff check --select F811` (Bug 56 fix). If unused exported functions are found, presents human gate `gate_5_3_unused_functions` with options FIX SPEC (strongly recommended) or OVERRIDE CONTINUE. Format/lint/type issues enter the bounded fix cycle as before.

  **Delivered quality configuration:** Generates quality tool config from profile `quality` section. Changelog from `vcs.changelog`. Commit style from `vcs.commit_style`. README per profile preferences with carry-forward for Mode A (Bug 30 fix).

  **Records `delivered_repo_path`:** `dispatch_agent_status` for `git_repo_agent` calls `set_delivered_repo_path`.

  **Commit style and quality preferences** are encoded in the agent definition string as behavioral contracts (Layer 1 preference enforcement).

  **Environment name derivation (Bug 27 fix):** Environment name in delivered `environment.yml` and `README.md` must use canonical `derive_env_name()` from Unit 1, not independent derivation.

- **Integration Test Author (CHANGED IN 2.1):** Must cover all 11 integration test requirements including quality gate chains.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** Task prompt content assembled by Unit 9.

---

## Unit 19: Debug Loop Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

BUG_TRIAGE_FRONTMATTER: Dict[str, Any] = {
    "name": "bug_triage_agent", "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Bash", "Glob", "Grep"],
}
REPAIR_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "repair_agent", "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

BUG_TRIAGE_STATUS: List[str] = [
    "TRIAGE_COMPLETE: build_env", "TRIAGE_COMPLETE: single_unit", "TRIAGE_COMPLETE: cross_unit",
    "TRIAGE_NEEDS_REFINEMENT", "TRIAGE_NON_REPRODUCIBLE",
]
REPAIR_AGENT_STATUS: List[str] = ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"]

BUG_TRIAGE_AGENT_MD_CONTENT: str
REPAIR_AGENT_MD_CONTENT: str
```

### Tier 2 — Invariants

```python
# Bug Triage Agent must contain Step 7 commit instructions (spec Section 12.17.4)
assert "[SVP-DEBUG]" in BUG_TRIAGE_AGENT_MD_CONTENT, \
    "Must contain debug commit format"
assert "COMMIT APPROVED" in BUG_TRIAGE_AGENT_MD_CONTENT, \
    "Must contain commit gate response option"
assert "COMMIT REJECTED" in BUG_TRIAGE_AGENT_MD_CONTENT, \
    "Must contain commit gate response option"
assert "delivered_repo_path" in BUG_TRIAGE_AGENT_MD_CONTENT.lower() or \
    "delivered repo" in BUG_TRIAGE_AGENT_MD_CONTENT.lower(), \
    "Must reference delivered repo path"
```

### Tier 3 -- Behavioral Contracts

- **Bug Triage Agent (CHANGED IN 2.1):** Seven-step workflow. Receives `delivered_repo_path` from task prompt. Step 7 -- update lessons learned: agent writes only to `docs/svp_2_1_lessons_learned.md` in the delivered repository (the authoritative copy). Agent must NOT write separately to `docs/references/` -- a deterministic post-triage sync script (`sync_debug_docs.py`, Bug 87) handles copy propagation. Step 8 -- commit and push: prepares commit using fixed debug commit message format (`[SVP-DEBUG] Bug NNN: <summary>` with structured body) regardless of `vcs.commit_style`. Presents to human for approval. Gate response options: **COMMIT APPROVED** or **COMMIT REJECTED**. The `BUG_TRIAGE_AGENT_MD_CONTENT` must contain Step 7 and Step 8 instructions verbatim.
- **Repair Agent:** Unchanged.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** Task prompt content assembled by Unit 9.

---

## Unit 20: Slash Command Files

**Artifact category:** Markdown (command .md files)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

COMMAND_FILES: Dict[str, str] = {
    "save": "save.md", "quit": "quit.md", "help": "help.md",
    "hint": "hint.md", "status": "status.md", "ref": "ref.md",
    "redo": "redo.md", "bug": "bug.md", "clean": "clean.md",
}

SAVE_MD_CONTENT: str
QUIT_MD_CONTENT: str
HELP_MD_CONTENT: str
HINT_MD_CONTENT: str
STATUS_MD_CONTENT: str
REF_MD_CONTENT: str
REDO_MD_CONTENT: str
BUG_MD_CONTENT: str
CLEAN_MD_CONTENT: str
```

### Tier 2 — Invariants

```python
# Group B commands must include the complete action cycle (Bug 38 fix)
for cmd_content in [HELP_MD_CONTENT, HINT_MD_CONTENT, REF_MD_CONTENT, REDO_MD_CONTENT, BUG_MD_CONTENT]:
    assert "prepare_task.py" in cmd_content, "Must reference prepare_task.py"
    assert "last_status.txt" in cmd_content, "Must reference status file"
    assert "update_state.py" in cmd_content, "Must reference update_state.py"
    assert "--phase" in cmd_content, "Must include --phase argument"
    assert "routing" in cmd_content.lower(), "Must reference routing script"
```

### Tier 3 -- Behavioral Contracts

- Group A commands (`save`, `quit`, `status`, `clean`) instruct the main session to run `cmd_*.py` directly.
- Group B commands (`help`, `hint`, `ref`, `redo`, `bug`) instruct the main session to complete the full action cycle with the correct `--phase` values: `help`, `hint`, `reference_indexing`, `redo`, `bug_triage`.
- Prohibited scripts: `cmd_help.py`, `cmd_hint.py`, `cmd_ref.py`, `cmd_redo.py`, `cmd_bug.py` must NOT exist.

### Tier 3 -- Dependencies

- **Unit 10 (Routing Script):** Command files reference the routing script.
- **Unit 11 (Command Logic Scripts):** Group A commands delegate to `cmd_*.py`.

---

## Unit 21: Orchestration Skill

**Artifact category:** Markdown (SKILL.md)

### Tier 2 — Signatures

```python
from typing import Dict, Any

SKILL_MD_CONTENT: str
```

### Tier 2 — Invariants

```python
assert len(SKILL_MD_CONTENT) > 500
# Must include slash-command action cycle section (Bug 39 fix)
assert "slash" in SKILL_MD_CONTENT.lower() or "Group B" in SKILL_MD_CONTENT, \
    "Must include slash-command-initiated action cycle guidance"
assert "--phase" in SKILL_MD_CONTENT, "Must reference --phase values for Group B commands"
```

### Tier 3 -- Behavioral Contracts

- `SKILL_MD_CONTENT` contains the complete orchestration protocol: six-step action cycle, action type handling, status line construction, gate presentation rules, session boundary handling.
- **Slash-command-initiated action cycles (Bug 39 fix):** Includes a section explaining that Group B commands bypass the routing script -- the command definition substitutes for the routing script's action block. The skill explains that the same six-step cycle applies, with the command definition providing the PREPARE command, agent type, and POST command.

### Tier 3 -- Dependencies

- **Unit 10 (Routing Script):** The skill's protocol is designed around the routing script's output format.

---

## Unit 22: Project Templates

**Artifact category:** Python script + JSON + TOML + Markdown templates

### Tier 2 — Signatures

```python
from typing import Dict, Any
from pathlib import Path

def generate_claude_md(project_name: str, project_root: Path) -> str: ...

DEFAULT_CONFIG_TEMPLATE: str = "templates/svp_config_default.json"
INITIAL_STATE_TEMPLATE: str = "templates/pipeline_state_initial.json"
README_SVP_TEMPLATE: str = "templates/readme_svp.txt"
TOOLCHAIN_DEFAULT_TEMPLATE: str = "toolchain_defaults/python_conda_pytest.json"
RUFF_CONFIG_TEMPLATE: str = "toolchain_defaults/ruff.toml"

CLAUDE_MD_PY_CONTENT: str
SVP_CONFIG_DEFAULT_JSON_CONTENT: str
PIPELINE_STATE_INITIAL_JSON_CONTENT: str
README_SVP_TXT_CONTENT: str
TOOLCHAIN_DEFAULT_JSON_CONTENT: str
RUFF_CONFIG_TOML_CONTENT: str

GOL_STAKEHOLDER_SPEC_CONTENT: str
GOL_BLUEPRINT_PROSE_CONTENT: str
GOL_BLUEPRINT_CONTRACTS_CONTENT: str
GOL_PROJECT_CONTEXT_CONTENT: str
```

### Tier 2 — Invariants

```python
assert "def generate_claude_md" in CLAUDE_MD_PY_CONTENT
assert '"stage"' in PIPELINE_STATE_INITIAL_JSON_CONTENT
assert '"skip_permissions"' in SVP_CONFIG_DEFAULT_JSON_CONTENT
assert "SVP-MANAGED" in README_SVP_TXT_CONTENT
assert '"quality"' in TOOLCHAIN_DEFAULT_JSON_CONTENT
assert '"gate_a"' in TOOLCHAIN_DEFAULT_JSON_CONTENT
assert '"gate_b"' in TOOLCHAIN_DEFAULT_JSON_CONTENT
assert '"gate_c"' in TOOLCHAIN_DEFAULT_JSON_CONTENT
assert '"unused_exports"' in TOOLCHAIN_DEFAULT_JSON_CONTENT  # Bug 56: Gate C dead code detection
assert "line-length" in RUFF_CONFIG_TOML_CONTENT
assert "[lint]" in RUFF_CONFIG_TOML_CONTENT
assert '"delivered_repo_path"' in PIPELINE_STATE_INITIAL_JSON_CONTENT
# Bug 34 fix: run_prefix must not contain version-specific flags
```

### Tier 3 -- Behavioral Contracts

- `generate_claude_md` produces a complete CLAUDE.md with the six-step action cycle.
- Default config template matches `DEFAULT_CONFIG` from Unit 1 (verified by structural test).
- Initial state template matches `create_initial_state` from Unit 2 (verified by structural test).
- `TOOLCHAIN_DEFAULT_JSON_CONTENT` matches complete toolchain schema including `quality` section.
- `RUFF_CONFIG_TOML_CONTENT` specifies `line-length = 88` and uses default ruff rule set.
- `GOL_BLUEPRINT_PROSE_CONTENT` and `GOL_BLUEPRINT_CONTRACTS_CONTENT` -- carry-forward artifacts updated for the two-file split.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Default config template must match Unit 1's `DEFAULT_CONFIG`.
- **Unit 2 (Pipeline State Schema):** Initial state template must match Unit 2's `create_initial_state`.
- **Unit 10 (Routing Script):** CLAUDE.md references the routing script.

---

## Unit 23: Plugin Manifest, Structural Validation, and Compliance Scan

**Artifact category:** JSON + Python script (compliance_scan.py)

### Tier 2 — Signatures

```python
from typing import Dict, Any, List
from pathlib import Path

PLUGIN_JSON: Dict[str, Any] = {
    "name": "svp", "version": "2.1.0",
    "description": "Stratified Verification Pipeline - deterministically orchestrated software development",
}
MARKETPLACE_JSON: Dict[str, Any] = {
    "name": "svp", "owner": {"name": "SVP"},
    "plugins": [{"name": "svp", "source": "./svp", "version": "2.1.0",
        "description": "Stratified Verification Pipeline", "author": {"name": "SVP"}}]
}

def validate_plugin_structure(repo_root: Path) -> List[str]: ...

PLUGIN_JSON_CONTENT: str
MARKETPLACE_JSON_CONTENT: str

def run_compliance_scan(project_root: Path, delivered_src_dir: Path,
    delivered_tests_dir: Path, profile: Dict[str, Any]) -> List[Dict[str, Any]]: ...
def _get_banned_patterns(environment_recommendation: str) -> List[Dict[str, str]]: ...
def _scan_file_ast(file_path: Path, banned_patterns: List[Dict[str, str]]) -> List[Dict[str, Any]]: ...
def compliance_scan_main() -> None: ...
```

### Tier 2 — Invariants

```python
assert (repo_root / ".claude-plugin" / "marketplace.json").exists()
assert (repo_root / "svp" / ".claude-plugin" / "plugin.json").exists()
for component in ["agents", "commands", "hooks", "scripts", "skills"]:
    assert (repo_root / "svp" / component).is_dir()
assert (repo_root / "svp" / "scripts" / "toolchain_defaults" / "ruff.toml").exists()
# Structural validation must check that docs/ contains at least one blueprint .md file
assert any((repo_root / "docs").glob("*.md")), "docs/ must contain at least one .md file (blueprint files are discovered, not hardcoded by name)"
# Stub sentinel check
# No delivered Python source file may contain __SVP_STUB__
```

### Tier 3 -- Behavioral Contracts

- `validate_plugin_structure` checks all structural requirements including `toolchain_defaults/` directory, `quality` section in toolchain JSON, at least one blueprint `.md` file in `docs/` (discovered dynamically, not by hardcoded filenames), no `__SVP_STUB__` sentinel in delivered source, commit count validation, tests pass in delivered layout, pytest path config present, README carry-forward (Mode A).
- `run_compliance_scan` scans delivered Python source for preference violations.
- `compliance_scan_main` emits `COMMAND_SUCCEEDED` or `COMMAND_FAILED: {count} violations found`.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads profile via `load_profile`.
- All preceding units (for structural validation).

---

## Unit 24: SVP Launcher

**Artifact category:** Python script (standalone CLI tool)

### Tier 2 — Signatures

```python
#!/usr/bin/env python3
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import subprocess, sys, argparse, shutil, os, json, stat, time

RESTART_SIGNAL_FILE: str = ".svp/restart_signal"
STATE_FILE: str = "pipeline_state.json"
CONFIG_FILE: str = "svp_config.json"
TOOLCHAIN_FILE: str = "toolchain.json"
RUFF_CONFIG_FILE: str = "ruff.toml"
SVP_DIR: str = ".svp"
MARKERS_DIR: str = ".svp/markers"
CLAUDE_MD_FILE: str = "CLAUDE.md"
README_SVP_FILE: str = "README_SVP.txt"
SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"
PROFILE_FILE: str = "project_profile.json"

_DEFAULT_PROFILE: Dict[str, Any] = { ... }  # same structure as Unit 1 DEFAULT_PROFILE

PROJECT_DIRS: List[str] = [
    ".svp", ".svp/markers", ".claude", "scripts", "ledgers",
    "logs", "logs/rollback", "specs", "specs/history",
    "blueprint", "blueprint/history", "references", "references/index",
    "src", "tests", "tests/regressions", "data",
]

def _find_plugin_root() -> Optional[Path]: ...
def _is_svp_plugin_dir(path: Path) -> bool: ...
def _print_header(text: str) -> None: ...
def _print_status(name: str, passed: bool, message: str) -> None: ...
def _print_transition(message: str) -> None: ...
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace: ...

def check_claude_code() -> Tuple[bool, str]: ...
def check_svp_plugin() -> Tuple[bool, str]: ...
def check_api_credentials() -> Tuple[bool, str]: ...
def check_conda() -> Tuple[bool, str]: ...
def check_python() -> Tuple[bool, str]: ...
def check_pytest() -> Tuple[bool, str]: ...
def check_git() -> Tuple[bool, str]: ...
def check_network() -> Tuple[bool, str]: ...
def run_all_prerequisites() -> List[Tuple[str, bool, str]]: ...

def create_project_directory(project_name: str, parent_dir: Path) -> Path: ...
def copy_scripts_to_workspace(plugin_root: Path, project_root: Path) -> None: ...
def copy_toolchain_default(plugin_root: Path, project_root: Path) -> None: ...
def copy_ruff_config(plugin_root: Path, project_root: Path) -> None: ...
def copy_regression_tests(plugin_root: Path, project_root: Path) -> None: ...
def copy_hooks(plugin_root: Path, project_root: Path) -> None: ...
def generate_claude_md(project_root: Path, project_name: str) -> None: ...
def _generate_claude_md_fallback(project_name: str) -> str: ...
def write_initial_state(project_root: Path, project_name: str) -> None: ...
def write_default_config(project_root: Path) -> None: ...
def write_readme_svp(project_root: Path) -> None: ...

def set_filesystem_permissions(project_root: Path, read_only: bool) -> None: ...
def _load_launch_config(project_root: Path) -> Dict[str, Any]: ...

def launch_claude_code(project_root: Path, plugin_dir: Path) -> int: ...
def detect_restart_signal(project_root: Path) -> Optional[str]: ...
def clear_restart_signal(project_root: Path) -> None: ...
def run_session_loop(project_root: Path, plugin_dir: Path) -> int: ...

def detect_existing_project(directory: Path) -> bool: ...
def resume_project(project_root: Path, plugin_dir: Path) -> int: ...

def _handle_new_project(args: argparse.Namespace, plugin_dir: Path) -> int: ...
def _handle_restore(args: argparse.Namespace, plugin_dir: Path) -> int: ...

def main(argv: Optional[List[str]] = None) -> int: ...
```

### Tier 2 — Invariants

```python
assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"
assert len(run_all_prerequisites()) == 8
assert ".svp" in PROJECT_DIRS
assert "scripts" in PROJECT_DIRS
assert "tests/regressions" in PROJECT_DIRS
# Self-containment: no imports from other SVP modules
# SVP_PLUGIN_ACTIVE must be set in subprocess environment, never on launcher's own os.environ
```

### Tier 3 -- Error Conditions

- `FileExistsError`: "Project directory already exists: {path}"
- `RuntimeError`: "Plugin scripts directory not found at {path}"
- `RuntimeError`: "Ruff config file not found at {path}" (NEW IN 2.1)
- `RuntimeError`: "Session launch failed: Claude Code executable not found"
- `RuntimeError`: "Session launch failed: {details}"

### Tier 3 -- Behavioral Contracts

**Plugin discovery:** `_find_plugin_root()` checks `SVP_PLUGIN_ROOT` env var first, then searches 5 paths. `_is_svp_plugin_dir` validates by reading `.claude-plugin/plugin.json` and checking `name == "svp"`. Must NOT rely on directory-existence checks alone.

**CLI parsing (Bug 32 fix):** Two subcommands: `new` and `restore`. No `resume` subcommand. `svp restore` accepts `--blueprint-dir` pointing to a directory containing one or more `.md` blueprint files; validates that the directory exists and contains at least one `.md` file before proceeding. No assumption about the number or names of blueprint files. Running `svp` with no arguments auto-detects existing project.

**Project setup:** `copy_ruff_config` copies `ruff.toml` and sets read-only via `os.chmod`.

**Session lifecycle (Bug 31, 34 fix):** `launch_claude_code` uses `subprocess.run` with `cwd=str(project_root)`, `env` with `SVP_PLUGIN_ACTIVE=1`, `--prompt "run the routing script"`. No `--project-dir` flag.

**Restore mode:** `_handle_restore` copies all `.md` files from `--blueprint-dir` into the project's `blueprint/` directory, preserving their original filenames. Writes minimal `project_profile.json` using `_DEFAULT_PROFILE`. Writes state at `pre_stage_3`. No assumption about the number or names of blueprint files -- all `.md` files in the source directory are copied.

**`_DEFAULT_PROFILE` structural match invariant:** `_DEFAULT_PROFILE` in Unit 24 must have the same key structure (all nested keys at all levels) as `DEFAULT_PROFILE` in Unit 1. Because Unit 24 is self-contained (no imports from other SVP units), it maintains its own copy. A Unit 24 unit test must verify that the key paths of `_DEFAULT_PROFILE` match the key paths of Unit 1's `DEFAULT_PROFILE`. Any structural divergence between the two is a contract violation.

### Tier 3 -- Dependencies

- **Unit 12 (Hook Configurations):** Copies hook files. `SVP_PLUGIN_ACTIVE` must match.
- **Unit 22 (Project Templates):** Template files loaded from `scripts/templates/` and `scripts/toolchain_defaults/`.

Note: Unit 24 does NOT depend on Units 2 or 3 at the Python import level (self-containment invariant).

---

*End of blueprint contracts.*
