# SVP 2.2 Blueprint -- Prose (Tier 1 Descriptions)

**Version:** 1.3
**Date:** 2026-03-26
**Spec version:** v9.0 (SVP 2.2)
**Build tool:** SVP 2.1
**Units:** 29

---

## Preamble: Delivered File Tree

The file tree below maps workspace unit implementations to their final paths in the delivered repository. Each `<- Unit N` annotation identifies the producing unit. The assembly map generator (`assembly_map.json`) parses these annotations to produce the bidirectional path mapping consumed by Stage 6 (triage) and Stage 7 (oracle).

```
svp-repo/                              <- repository root
|-- .claude-plugin/
|   +-- marketplace.json               <- Unit 28
|-- svp/                               <- plugin subdirectory
|   |-- .claude-plugin/
|   |   +-- plugin.json                <- Unit 28
|   |-- agents/
|   |   |-- setup_agent.md             <- Unit 18
|   |   |-- stakeholder_dialog.md      <- Unit 20
|   |   |-- stakeholder_reviewer.md    <- Unit 20
|   |   |-- blueprint_author.md        <- Unit 20
|   |   |-- blueprint_checker.md       <- Unit 19
|   |   |-- blueprint_reviewer.md      <- Unit 20
|   |   |-- test_agent.md              <- Unit 20
|   |   |-- implementation_agent.md    <- Unit 20
|   |   |-- coverage_review_agent.md   <- Unit 20
|   |   |-- diagnostic_agent.md        <- Unit 21
|   |   |-- redo_agent.md              <- Unit 21
|   |   |-- integration_test_author.md <- Unit 20
|   |   |-- git_repo_agent.md          <- Unit 23
|   |   |-- help_agent.md              <- Unit 22
|   |   |-- hint_agent.md              <- Unit 22
|   |   |-- reference_indexing.md      <- Unit 22
|   |   |-- bug_triage_agent.md        <- Unit 24
|   |   |-- repair_agent.md            <- Unit 24
|   |   |-- checklist_generation.md    <- Unit 23
|   |   |-- regression_adaptation.md   <- Unit 23
|   |   +-- oracle_agent.md            <- Unit 23
|   |-- commands/
|   |   |-- help.md                    <- Unit 25
|   |   |-- hint.md                    <- Unit 25
|   |   |-- ref.md                     <- Unit 25
|   |   |-- redo.md                    <- Unit 25
|   |   |-- bug.md                     <- Unit 25
|   |   |-- oracle.md                  <- Unit 25
|   |   |-- save.md                    <- Unit 25
|   |   |-- quit.md                    <- Unit 25
|   |   |-- status.md                  <- Unit 25
|   |   |-- clean.md                   <- Unit 25
|   |   +-- visual-verify.md           <- Unit 25
|   |-- hooks/
|   |   |-- hooks.json                 <- Unit 17
|   |   |-- write_authorization.sh     <- Unit 17
|   |   |-- non_svp_protection.sh      <- Unit 17
|   |   |-- stub_sentinel_check.sh     <- Unit 17
|   |   +-- monitoring_reminder.sh     <- Unit 17
|   |-- scripts/
|   |   |-- svp_config.py              <- Unit 1
|   |   |-- language_registry.py       <- Unit 2
|   |   |-- profile_schema.py          <- Unit 3
|   |   |-- toolchain_reader.py        <- Unit 4
|   |   |-- pipeline_state.py          <- Unit 5
|   |   |-- state_transitions.py       <- Unit 6
|   |   |-- ledger_manager.py          <- Unit 7
|   |   |-- blueprint_extractor.py     <- Unit 8
|   |   |-- signature_parser.py        <- Unit 9
|   |   |-- stub_generator.py          <- Unit 10
|   |   |-- infrastructure_setup.py    <- Unit 11
|   |   |-- hint_prompt_assembler.py   <- Unit 12
|   |   |-- prepare_task.py            <- Unit 13
|   |   |-- routing.py                 <- Unit 14
|   |   |-- run_tests.py               <- Unit 14
|   |   |-- quality_gate.py            <- Unit 15
|   |   |-- update_state.py            <- Unit 14
|   |   |-- cmd_save.py                (re-export wrapper for sync_debug_docs)
|   |   |-- cmd_quit.py                (CLI wrapper, imports from sync_debug_docs)
|   |   |-- cmd_status.py              (CLI wrapper, imports from sync_debug_docs)
|   |   |-- cmd_clean.py               (CLI wrapper, imports from sync_debug_docs)
|   |   |-- structural_check.py        <- Unit 28
|   |   |-- generate_assembly_map.py   <- Unit 23  (also provides 'regression-adapt' CLI subcommand)
|   |   |-- sync_debug_docs.py         <- Unit 16
|   |   |-- toolchain_defaults/
|   |   |   |-- python_conda_pytest.json  <- Unit 27
|   |   |   |-- r_renv_testthat.json      <- Unit 27
|   |   |   +-- ruff.toml                 <- Unit 27
|   |   |-- delivery_quality_templates/
|   |   |   |-- python/
|   |   |   |   |-- ruff.toml.template
|   |   |   |   |-- flake8.template
|   |   |   |   |-- mypy.ini.template
|   |   |   |   +-- pyproject_black.toml.template
|   |   |   +-- r/
|   |   |       |-- lintr.template
|   |   |       +-- styler.template
|   |   +-- svp_launcher.py            <- Unit 29
|   +-- skills/
|       +-- orchestration/
|           +-- SKILL.md               <- Unit 26
|-- src/                               <- SVP source code (Python)
|-- tests/
|   +-- regressions/                   <- carry-forward regression tests
|       |-- test_bug01_*.py .. test_bug73_*.py  <- 51 carry-forward files from SVP 2.1
|       |-- test_assembly_map_generation.py     <- Unit 28 (NEW IN 2.2)
|       |-- test_dispatch_exhaustiveness.py     <- Unit 28 (NEW IN 2.2)
|       |-- test_three_layer_separation.py      <- Unit 4 (NEW IN 2.2)
|       |-- test_profile_migration.py           <- Unit 3 (NEW IN 2.2)
|       |-- test_r_test_output_parsing.py       <- Unit 14 (NEW IN 2.2)
|       +-- test_behavioral_equivalence.py      <- Unit 14 (NEW IN 2.2)
+-- examples/
    |-- game-of-life/
    |-- gol-r/
    |-- gol-plugin/
    |-- gol-python-r/
    +-- gol-r-python/
```

---

## Unit 1: Core Configuration

Unit 1 provides the foundational configuration constants and utilities that every other unit depends on. It owns `svp_config.json` (the pipeline configuration file), the `ARTIFACT_FILENAMES` registry that maps logical artifact names to filesystem paths, and the `load_config` / `save_config` functions for reading and writing pipeline configuration. It also provides `derive_env_name` for deterministic conda environment naming and `get_blueprint_dir` for resolving the blueprint directory path from `ARTIFACT_FILENAMES`.

This unit is the single source of truth for all path constants, filename conventions, and shared configuration. No other unit hardcodes paths -- they read from Unit 1's constants. Profile default values and loading/validation logic live exclusively in Unit 3.

The `svp_config.json` schema includes `iteration_limit`, per-agent model overrides under `models.*`, `models.default`, `context_budget_override`, `context_budget_threshold`, `compaction_character_threshold`, `auto_save`, and `skip_permissions`. Model configuration precedence: `project_profile.json pipeline.agent_models` overrides `svp_config.json models.*` overrides `models.default`.

### Preferences

The project profile specifies `delivery.source_layout: "flat"` and `delivery.entry_points: true` with a CLI entry point named `svp`. The flat layout places modules directly under the package directory rather than under `src/packagename/`.

---

## Unit 2: Language Registry

Unit 2 owns the language provider framework's central data structure: the `LANGUAGE_REGISTRY`. This is a module-level dictionary mapping language identifiers (`"python"`, `"r"`, `"stan"`) to complete configuration dictionaries specifying how to build, test, lint, and deliver in that language. SVP 2.2 ships with two full-language entries (Python, R) and one component-only entry (Stan).

Each registry entry contains identity fields (`id`, `display_name`), filesystem fields (`file_extension`, `source_dir`, `test_dir`, `test_file_pattern`), build-time toolchain fields (`toolchain_file`, `environment_manager`, `test_framework`, `version_check_command`), code generation fields (`stub_sentinel`, `stub_generator_key`, `test_output_parser_key`, `quality_runner_key`), delivery defaults, validation sets, hook configuration, error detection indicators, component support fields (`is_component_only`, `compatible_hosts`, `required_dispatch_entries`), cross-language support (`bridge_libraries`), delivery structure fields, agent prompts, and non-source embedding conventions.

Unit 2 also defines the `TestResult` and `QualityResult` named tuple types consumed by dispatch table implementations across the pipeline, the `get_language_config()` function for runtime language config lookup, and validation guardrails (`validate_registry_entry`, `validate_component_entry`) that run at import time.

The `FULL_REQUIRED_KEYS` and `COMPONENT_REQUIRED_KEYS` constants enumerate the mandatory keys for full-language and component-language entries respectively. Dynamic registry extension loading from `language_registry_extensions.json` is supported as a placeholder for future use.

---

## Unit 3: Profile Schema

Unit 3 manages the language-keyed project profile schema and the profile loading/validation lifecycle. It owns `DEFAULT_PROFILE` (the canonical default values for every profile field, matching the schema from Section 6.4), `load_profile` (which reads `project_profile.json`, deep-merges with defaults, and detects SVP 2.1-format profiles for auto-migration), and `validate_profile` (which checks field types, validates tool choices against `LANGUAGE_REGISTRY` validation sets, and detects known contradictions).

The profile schema uses language-keyed sections for `delivery` and `quality` (e.g., `delivery.python.source_layout`, `quality.r.linter`). The `load_profile` function detects old-format profiles (where `delivery` and `quality` are flat, not language-keyed) and migrates them to the language-keyed format using the project's `language.primary` field.

Unit 3 also provides language-aware accessor functions (`get_delivery_config`, `get_quality_config`) that accept a language identifier and return the corresponding sub-dictionary from the profile, with defaults filled from the registry's `default_delivery` and `default_quality`.

---

## Unit 4: Toolchain Reader

Unit 4 owns the toolchain file reading and command resolution logic. It provides `load_toolchain` (which reads a toolchain JSON file and validates its structure), `resolve_command` (which performs single-pass placeholder substitution on command templates), and `get_gate_composition` (which retrieves the ordered list of quality tool operations for a given gate identifier).

The three-layer toolchain separation (Section 3.25) is enforced here: `load_toolchain(language=None)` loads the pipeline toolchain (`toolchain.json`); `load_toolchain(language="python")` loads the language-specific build-time toolchain (`scripts/toolchain_defaults/python_conda_pytest.json`); delivery toolchain configuration is never read by this unit -- it comes from the profile (Unit 3). A structural regression test enforces that no function reads pipeline quality from the profile or delivery quality from the toolchain.

Placeholder resolution is single-pass: resolve `{run_prefix}` first (from `environment.run_prefix`), then substitute into all templates. `{env_name}` is resolved from `derive_env_name()` (Unit 1), `{python_version}` from the profile, `{flags}` from the appropriate flags key (unit_flags for Gates A/B, project_flags for Gate C), and `{target}` from the caller. After resolution, whitespace is normalized (collapsing multiple spaces, trimming).

---

## Unit 5: Pipeline State

**Machinery unit.** This unit is tagged `machinery: true` in the blueprint extractor. Changes to this unit's contracts affect pipeline mechanisms and require `self_build_scope: "architectural"` for F-mode builds.

Unit 5 defines the `PipelineState` data structure, the `load_state` / `save_state` persistence functions, and the `VALID_STAGES`, `VALID_SUB_STAGES`, and related closed-set enumerations. The pipeline state file (`pipeline_state.json`) tracks: stage, sub_stage, current_unit, total_units, verified_units, alignment_iterations, fix_ladder_position, red_run_retries, pass_history, debug_session, debug_history, redo_triggered_from, delivered_repo_path, oracle session fields, pass/pass2 fields, deferred_broken_units, and state_hash.

SVP 2.2 adds: `primary_language`, `component_languages`, `secondary_language` (present when `archetype` is `"mixed"`, absent/None otherwise), `pass` (int or null: 1, 2, or null), `pass2_nested_session_path` (string or null), `deferred_broken_units` (array of int), `oracle_session_active`, `oracle_test_project`, `oracle_phase`, `oracle_run_count`, `oracle_nested_session_path`, `spec_revision_count` (int, default 0), and `state_hash`.

The `current_unit`/`sub_stage` co-invariant is enforced: when `current_unit` is non-null, `sub_stage` must be non-null. The `save_state` function computes and stores `state_hash` (SHA-256 of the file on disk after write) for build log chain validation.

Note: `pass1_workspace_path` is NOT a PipelineState field. Per the spec (Section 43.8), after Pass 2 completion, `pass1_workspace_path` and `pass2_nested_session_path` are cleared from state. The Pass 1 workspace path is derived at runtime from the project root and is not persisted in pipeline state.

---

## Unit 6: State Transitions

**Machinery unit.** This unit is tagged `machinery: true` in the blueprint extractor. Changes to this unit's contracts affect pipeline mechanisms and require `self_build_scope: "architectural"` for F-mode builds.

Unit 6 contains every state transition function in the pipeline. All functions accept a `PipelineState` and return a new `PipelineState` via deep copy -- the input state is never mutated. Each function validates preconditions before modifying state and raises `TransitionError` on invalid transitions.

Exported functions (complete list): `advance_stage`, `advance_sub_stage`, `complete_unit`, `advance_fix_ladder`, `increment_red_run_retries`, `reset_red_run_retries`, `increment_alignment_iteration`, `rollback_to_unit`, `restart_from_stage`, `version_document` (with `companion_paths` support), `enter_debug_session`, `authorize_debug_session`, `complete_debug_session`, `abandon_debug_session`, `update_debug_phase`, `set_debug_classification`, `enter_redo_profile_revision`, `complete_redo_profile_revision`, `enter_alignment_check`, `complete_alignment_check`, `enter_quality_gate`, `advance_quality_gate_to_retry`, `quality_gate_pass`, `quality_gate_fail_to_ladder`, `set_delivered_repo_path`, `enter_pass_1`, `enter_pass_2`, `clear_pass`, `mark_unit_deferred_broken`, `resolve_deferred_broken`.

Every function's postconditions specify which fields change and which are preserved. Every function has at least one call site in Unit 14 (routing) or another consumer unit.

---

## Unit 7: Ledger Management

Unit 7 provides the append-only conversation ledger system used by multi-turn agents (setup, stakeholder dialog, blueprint dialog, triage, help, hint). It owns `append_entry`, `read_ledger`, `compact_ledger`, `clear_ledger`, and `get_ledger_path`.

Compaction condenses exploratory exchanges while preserving all decisions, confirmed facts, `[HINT]` entries, and self-contained tagged lines (`[QUESTION]`, `[DECISION]`, `[CONFIRMED]`). The compaction uses a character threshold (configurable via `compaction_character_threshold` from Unit 1, default 200): tagged lines above the threshold have bodies deleted; those at or below keep bodies. No LLM involvement in compaction.

Ledger locations are deterministic: `ledgers/setup_dialog.jsonl`, `ledgers/stakeholder_dialog.jsonl`, `ledgers/blueprint_dialog.jsonl`, `ledgers/spec_revision_N.jsonl`, `ledgers/help_session.jsonl`, `ledgers/hint_session.jsonl`, `ledgers/bug_triage_N.jsonl`.

---

## Unit 8: Blueprint Extractor

Unit 8 provides functions to parse the two blueprint files and extract unit definitions, upstream contracts, and per-unit metadata. It owns `extract_units` (which parses `## Unit N:` headings from both files), `build_unit_context` (which assembles a single unit's context with optional Tier 1 inclusion), `UnitDefinition` (a data class with fields including the new `languages` field and the `machinery` boolean), and `detect_code_block_language` (which reads code fence tags from both files to populate `UnitDefinition.languages`).

The extractor uses `get_blueprint_dir()` from Unit 1 to resolve file paths. Code fence markers (opening ` ```language ` and closing ` ``` ` lines) are stripped before passing block content to signature parsers -- the parser receives raw code, not markdown. This stripping is the extractor's responsibility, not the parser's.

`detect_code_block_language` reads code fence tags: `python` maps to "python", `r` maps to "r", `stan` maps to "stan", untagged defaults to the project's primary language. Language detection is a metadata operation; it does not interact with `build_unit_context` or the `include_tier1` parameter.

---

## Unit 9: Signature Parser Dispatch

Unit 9 owns the `SIGNATURE_PARSERS` dispatch table -- the first of six per-language dispatch tables in SVP 2.2. Each entry maps a dispatch key to a function with signature `(source: str, language_config: Dict) -> Any`. The dispatch key for full languages is the language name itself (e.g., `"python"`, `"r"`). Component languages (e.g., Stan) and plugin artifact types bypass signature parsing entirely -- they do not have entries in `SIGNATURE_PARSERS` and are handled via alternative paths (template generation for components, fixed-template stubs for plugins).

SVP 2.2 ships with two entries: Python (wraps `ast.parse()` to produce an AST) and R (regex-based parser for R function assignment syntax). The `parse_signatures` entry point reads a raw code block (already stripped of markdown fences by Unit 8) and dispatches to the language-specific parser.

This unit also provides `main()` as a CLI entry point for direct invocation during stub generation (used by the routing script). CLI arguments: `--blueprint` (path to `blueprint_contracts.md`), `--unit` (unit number), `--language` (language identifier).

---

## Unit 10: Stub Generator Dispatch

Unit 10 owns the `STUB_GENERATORS` dispatch table -- the second per-language dispatch table. Each entry maps a dispatch key to a function with signature `(parsed_signatures: Any, language_config: Dict) -> str`. The stub generator produces importable stub modules from parsed signature ASTs.

For Python: every function body raises `NotImplementedError()`, every class body contains declared methods (each raising `NotImplementedError`) and class-level attributes set to `None`. Module-level `assert` statements are stripped. The language-specific stub sentinel (from `LANGUAGE_REGISTRY[language]["stub_sentinel"]`) is prepended as the first non-import statement.

For R: function bodies contain a single `stop("Not implemented")` call. The R-specific sentinel is prepended as a comment.

For Stan: a minimal model template with the sentinel as a comment. Component languages (like Stan) bypass signature parsing entirely -- their stub generators receive `None` as parsed signatures and produce fixed-template stubs directly.

The stub generator also generates upstream dependency stubs for each unit's dependencies. The forward-reference guard validates that every dependency has a lower unit number. CLI: `--blueprint`, `--unit`, `--output-dir`, `--upstream`.

The `STUB_GENERATORS` dispatch table also contains entries for plugin artifact types: `plugin_markdown`, `plugin_bash`, `plugin_json` -- these generate minimal valid stubs for non-Python artifact types used by the Claude Code plugin archetype. Plugin stub generators bypass signature parsing entirely: they do not consume parsed AST output but instead produce fixed-template stubs directly. The `generate_stub` entry point detects plugin dispatch keys and component language dispatch keys, and short-circuits to the template generator without calling `parse_signatures`.

---

## Unit 11: Infrastructure Setup

Unit 11 implements the Pre-Stage-3 deterministic setup: environment creation, quality tool installation, dependency extraction, import validation, directory scaffolding, DAG re-validation, and regression test import adaptation. It is the single entry point for all pre-build infrastructure. It provides `main()` as a CLI entry point with `--project-root` argument, invoked by the routing script during the `pre_stage_3` stage.

Environment creation dispatches via the language registry's `environment_manager` field. For Python: `conda create`. For R: dispatches through `delivery.r.environment_recommendation` (renv, conda, or packrat). For mixed archetype: a single conda environment with both languages and bridge libraries. Component packages are installed inside the host environment.

Quality tool installation reads packages from the language-specific toolchain file. Import validation is language-specific (Python: `python -c "import X"`, R: `Rscript -e "library(X)"`). The `total_units` value is derived from the blueprint during this step, not read from pipeline state.

If `regression_test_import_map.json` exists, `generate_assembly_map.py regression-adapt` runs on `tests/regressions/` to adapt carry-forward regression test imports. The build log (`.svp/build_log.jsonl`) is created during this step. **(CHANGED IN 2.2 — Bug S3-110, renamed from `adapt_regression_tests.py` to a subcommand of `generate_assembly_map.py`.)**

---

## Unit 12: Hint Prompt Assembler

Unit 12 wraps human-provided hints in context-dependent prompt blocks adapted to the receiving agent's type and the current fix ladder position. It is a deterministic template engine with no LLM involvement.

The assembler reads the hint text and metadata (agent type, ladder position, unit number, gate context) and produces a structured prompt block. Different templates exist for test agents vs. implementation agents, and for different ladder positions (fresh attempt, diagnostic-guided, exhaustion).

Hints are logged as `[HINT]` entries in the relevant ledger with full gate metadata. After injection into one agent invocation, the stored hint is cleared. The `[HINT]` ledger entry persists through compaction.

---

## Unit 13: Task Preparation

Unit 13 is the deterministic preparation script (`prepare_task.py`) that assembles task prompts and gate prompts for all agents. It is the largest and most cross-cutting deterministic component. It reads the blueprint, profile, toolchain, pipeline state, ledgers, and reference documents, then produces structured task prompt files (`.svp/task_prompt.md`) and gate prompt files (`.svp/gate_prompt.md`).

Key exports: `prepare_task_prompt` (the main entry point, dispatching by agent type and mode), `prepare_gate_prompt` (assembles gate-specific context including response options), `build_unit_context` (assembles a single unit's blueprint context with selective Tier 1 inclusion), `build_language_context` (injects language-specific agent guidance from the registry), `load_blueprint` / `load_blueprint_contracts_only` / `load_blueprint_prose_only` (selective blueprint loading per the who-reads-what matrix).

The `ALL_GATE_IDS` constant contains all 31 gate IDs. Set equality with `GATE_VOCABULARY` (Unit 14) is verified by a structural test.

The preparation script dispatches by agent type, with per-type blueprint loading per the `SELECTIVE_LOADING_MATRIX`. Per-agent-type dispatch detail:
- `setup_agent`: dispatches by mode (context / profile / redo_delivery / redo_blueprint). Loads profile schema, dialog areas, archetype rules. No blueprint loaded.
- `stakeholder_dialog`: dispatches by mode (draft / revision / targeted_revision). Loads spec context, revision feedback if applicable. Blueprint: not loaded.
- `stakeholder_reviewer`: loads spec, review checklist. Blueprint: not loaded.
- `blueprint_author`: dispatches by mode (draft / revision). Loads spec, profile, project context, reviewer feedback if revision. Blueprint: both files (revision mode).
- `blueprint_reviewer`: loads spec, blueprint (both files), review checklist.
- `blueprint_checker`: loads spec, blueprint (both files), alignment checklist.
- `checklist_generation`: loads approved spec, lessons learned, regression test inventory. Blueprint: not loaded.
- `test_agent`: dispatches by mode (normal / regression_test). Loads unit context (contracts only), upstream stubs, quality tool notification, lessons learned (filtered for current unit), hint context. Blueprint: contracts only.
- `implementation_agent`: loads unit context (contracts only), test output, quality tool notification, diagnostic report (if ladder position is diagnostic_impl), hint context. Blueprint: contracts only.
- `coverage_review_agent`: loads unit context (contracts only), test files, source files. Blueprint: contracts only.
- `diagnostic_agent`: loads unit context (both files), test output, implementation source. Blueprint: both files.
- `integration_test_author`: loads blueprint (contracts only), integration context, previous failure output if retry. Blueprint: contracts only.
- `regression_adaptation`: loads failing tests, blueprint file tree, module listing, assembly map, previous spec summary. Blueprint: not loaded (file tree only).
- `git_repo_agent`: loads blueprint (contracts only), assembly config, profile, fix context if retry. Blueprint: contracts only.
- `help_agent`: loads project summary, spec, blueprint (prose only), gate context if at gate. Blueprint: prose only.
- `hint_agent`: loads hint text (reactive) or ledger context (proactive), blueprint (both files), target agent context. Blueprint: both files.
- `reference_indexing`: loads reference document paths, indexing instructions. Blueprint: not loaded.
- `redo_agent`: loads state summary, error description, unit definition. Blueprint: not loaded (reads on demand).
- `bug_triage_agent`: loads spec, blueprint (both files), source, tests, ledger, assembly map, delivered repo path. Blueprint: both files.
- `repair_agent`: loads error diagnosis, environment state, blueprint (both files), affected unit context. Blueprint: both files.
- `oracle_agent`: loads run ledger, spec, blueprint (dry run: both files), bug catalog, regression tests, test project artifacts, nested session state, assembly map. Blueprint: both files (dry run only).

It also provides `KNOWN_AGENT_TYPES` for startup validation against the routing script's agent type registry.

CLI: `--unit`, `--agent`, `--project-root`, `--output`, `--gate`, `--context`, `--mode`.

---

## Unit 14: Routing and Test Execution

**Machinery unit.** This unit is tagged `machinery: true` in the blueprint extractor. Changes to this unit's contracts affect pipeline mechanisms and require `self_build_scope: "architectural"` for F-mode builds.

Unit 14 is the pipeline's central routing engine and test execution dispatcher. It owns the `route()` function (which reads `pipeline_state.json` and returns a structured action block), the `GATE_VOCABULARY` constant (all 31 gate IDs with their response options), the `dispatch_agent_status` function, the `dispatch_gate_response` function, the `dispatch_command_status` function, and the `TEST_OUTPUT_PARSERS` dispatch table (the third per-language dispatch table). The `route()` function's action block `action_type` vocabulary includes: `invoke_agent`, `run_command`, `human_gate`, `session_boundary`, `pipeline_complete`, `pipeline_held`, and `break_glass`. The `pipeline_held` action type is emitted when `PROJECT_CONTEXT_REJECTED` is detected (Section 3.6). The `break_glass` action type is emitted during E/F self-builds when known exhaustion conditions are met (Section 43.9). The routing script is aware of the Hard Stop Protocol (Section 41): during Pass 1, if a builder script bug is detected, the routing script emits appropriate diagnostic context for the orchestrator to follow the Hard Stop procedure.

The `route()` function implements the two-branch routing invariant for all gate-presenting, command-presenting, and state-advancing entries listed in Section 3.6. Every sub-stage has an explicit branch. The function reads `last_status.txt` to distinguish "agent not done" from "agent done" for every agent-to-gate transition. It persists intermediate state to disk before any recursive `route()` call (route-level state persistence invariant).

The `TEST_OUTPUT_PARSERS` dispatch table maps language dispatch keys to functions with signature `(stdout: str, stderr: str, returncode: int, language_config: Dict) -> TestResult`. Python parser: extracts pytest `N passed, M failed, K errors` summary. R parser: extracts testthat `OK:`, `Failed:`, `Warnings:` counts. Plugin parsers are also registered: `plugin_markdown` (parses markdown lint output), `plugin_bash` (parses `bash -n` syntax check output), `plugin_json` (parses JSON validation output). These return `TestResult` with simplified status mapping for non-code artifact validation. Stan does not have a test output parser -- Stan models are validated through the host language's test framework and through syntax checking in the quality runners.

The `route()` function includes per-oracle-phase routing dispatch: when `oracle_session_active` is True, `route()` dispatches on `oracle_phase` instead of normal stage/sub_stage. Phase routing: `dry_run` invokes the oracle agent; `gate_a` presents Gate 7.A (`gate_7_a_trajectory_review`); `green_run` invokes the oracle agent; `gate_b` presents Gate 7.B (`gate_7_b_fix_plan_review`); `exit` deactivates the oracle session (sets `oracle_session_active = False`, cleans up nested session). Oracle phase transitions: `dry_run` -> `gate_a` (on ORACLE_DRY_RUN_COMPLETE), `gate_a` -> `green_run` (on APPROVE TRAJECTORY), `green_run` -> `gate_b` (oracle internally presents fix plan -- routing sets phase), `gate_b` -> `exit` (on APPROVE FIX or ABORT), `green_run` -> `exit` (on ORACLE_ALL_CLEAR). The oracle agent invocation spans `green_run` + Gate B as a multi-turn session.

The `update_state.py` script is also produced by this unit. It reads `pipeline_state.json`, validates the `--phase` argument matches the current state, calls the appropriate transition function from Unit 6, writes the updated state, and appends a build log entry.

The `run_tests.py` script executes test commands from the toolchain and returns structured results. It dispatches through `TEST_OUTPUT_PARSERS` for output parsing and uses `collection_error_indicators` from the language registry for collection error detection.

The `_validate_stage3_completion()` function runs at the Stage 3/4 boundary as a routing-time precondition, checking unit count, build log sub-stage audit, red run validation, and green run validation.

### Preferences

The project uses `vcs.commit_style: "conventional"` with `vcs.issue_references: true`, `vcs.branch_strategy: "main-only"`, `vcs.tagging: "semver"`, and `vcs.changelog: "conventional_changelog"`. These preferences are encoded in the git repo agent's task prompt (assembled by Unit 13) and reflected in the delivered repository's commit history and changelog.

---

## Unit 15: Quality Gate Execution

**Machinery unit.** This unit is tagged `machinery: true` in the blueprint extractor. Changes to this unit's contracts affect pipeline mechanisms and require `self_build_scope: "architectural"` for F-mode builds.

Unit 15 owns the `QUALITY_RUNNERS` dispatch table (the fourth per-language dispatch table) and the quality gate execution script (`quality_gate.py`). Each entry maps a dispatch key to a function with signature `(target_path: Path, gate_id: str, language_config: Dict, toolchain_config: Dict) -> QualityResult`.

The quality gate script reads the gate composition from the language-specific toolchain file (via Unit 4's `get_gate_composition`), resolves each operation's command template, executes the commands in order, classifies the results (auto-fixed, residuals, errors), and returns a `QualityResult`. Gate operation names are qualified with `"quality."` before resolution (Section 6.5.1).

For languages where a quality tool is `"none"` (e.g., R has no type checker), the corresponding operation is skipped. The pipeline checks the toolchain value, not the language name.

CLI: `--target`, `--gate`, `--unit`, `--language`, `--project-root`.

---

## Unit 16: Command Logic Scripts

Unit 16 produces the four Group A command scripts: `cmd_save.py` (flush state, verify integrity, confirm), `cmd_quit.py` (save then exit), `cmd_status.py` (report pipeline state with pass history, profile summary, quality gate status), and `cmd_clean.py` (archive/delete/keep workspace after Stage 5). It also produces the `sync_debug_docs.py` script for documentation synchronization during the debug loop.

`cmd_clean.py` removes the build environment using the language-specific cleanup command from the toolchain. `cmd_status.py` includes the one-line profile summary format showing pipeline and delivery quality tools separately.

---

## Unit 17: Hook Enforcement

Unit 17 produces the hook configuration files and shell scripts that enforce write authorization. It generates `hooks.json` (conforming to Claude Code's schema with PreToolUse and PostToolUse entries), `write_authorization.sh` (validates writes against pipeline state, including stage-gated builder script protection, profile path protection, and debug session write rules), `non_svp_protection.sh` (blocks writes in non-SVP sessions), and `stub_sentinel_check.sh` (PostToolUse hook checking for stub sentinel in implementation files).

The write authorization hook reads the current stage before evaluating path-specific rules. Hook order: read stage, check `pipeline_state.json` protection, check builder script protection, check remaining path rules. Write paths for each language are read from `LANGUAGE_REGISTRY[language]["authorized_write_dirs"]`. The stub sentinel is read from the registry for language-specific detection. When a write to a builder script (`scripts/*.py`) is blocked during Stages 3-5, the hook message references the Hard Stop Protocol (Section 41), directing the orchestrator to save artifacts, produce bug analysis, and fix SVP N via `/svp:bug` rather than attempting a direct fix.

Oracle session write rules are included: `.svp/oracle_run_ledger.json` is always writable during oracle sessions; the nested session workspace is writable by the oracle agent.

For E/F self-builds (Section 43.10), Unit 17 also generates a PostToolUse hook entry on Agent tool returns that injects a monitoring reminder. When the orchestrator receives output from any subagent during an E/F self-build, the hook injects a brief reminder to verify the subagent output against the spec before proceeding. This supplements the six-step action cycle's oversight mechanisms with an automated prompt at each agent return boundary.

---

## Unit 18: Setup Agent Definition

Unit 18 produces the setup agent's agent definition markdown file (`setup_agent.md`). The system prompt contains Rules 1-4 verbatim (plain language explanations, best-option recommendations, sensible defaults, progressive disclosure) as numbered behavioral requirements. The definition includes the Area 0 language dialog flow (archetype selector with Options A-F), the six dialog areas (0-5), the profile schema with exact canonical field names, and the contradiction detection rules.

The setup agent operates in two modes (project context and project profile) within Stage 0, distinguished by the mode identifier injected by the preparation script. The agent uses a single ledger (`ledgers/setup_dialog.jsonl`) for both phases.

The dialog covers six areas (0-5): Area 0 (Language/Ecosystem), Area 1 (VCS), Area 2 (README/Docs), Area 3 (Testing), Area 4 (Licensing/Metadata), Area 5 (Quality). Area 0 determines the target language(s) and configures the build/test/quality toolchain; Areas 1-5 cover delivery preferences. Area 5 may be skipped if Area 0 already populated quality settings.

For Mode A (self-build), the definition includes Mode A default pre-population logic. For Option C (plugin), it includes the extended plugin interview (4 questions about external services, auth, hook events, and skills). For Option D (mixed-language), it includes the focused mixed-language dialog flow (3-4 questions): (1) "Which language owns the project structure?" -- sets `language.primary`, the other becomes `language.secondary`; (2) "What's the communication direction?" -- sets `language.communication` with bridge libraries (rpy2 for Python-to-R, reticulate for R-to-Python); (3) "Same tools as pipeline for [primary]?" -- fast-path populates primary delivery/quality with pipeline defaults, or enters detailed tool dialog; (4) "Default tools for [secondary]?" -- presents secondary language's registry defaults with opt-out. Hard constraints enforced: both `environment_recommendation` forced to `"conda"`, both `dependency_format` forced to `"environment.yml"`. Profile fields populated: `archetype: "mixed"`, `language.primary`, `language.secondary`, `language.communication`, and both `delivery` and `quality` sections for both languages. For Options E/F (self-build), plugin fields are auto-populated from SVP context.

---

## Unit 19: Blueprint Checker Definition

Unit 19 produces the blueprint checker agent definition markdown file (`blueprint_checker.md`). The system prompt includes the mandatory alignment checklist: DAG acyclicity validation, profile preference validation (Layer 2), pattern catalog validation (P1-P13+), contract granularity verification (exported function coverage, per-gate-option dispatch contracts, call-site verification, re-entry path documentation), and language registry completeness validation.

The checker receives the Blueprint Alignment Checker Checklist (`.svp/alignment_checker_checklist.md`) and works through it item by item. It validates internal consistency between the prose and contracts files. It uses the "report most fundamental level" corollary: spec problems supersede blueprint problems.

---

## Unit 20: Construction Agent Definitions

Unit 20 produces the agent definition markdown files for all construction-phase agents: stakeholder dialog agent, stakeholder spec reviewer, blueprint author agent, blueprint reviewer, test agent, implementation agent, coverage review agent, and integration test author.

Each definition's system prompt references `LANGUAGE_CONTEXT` for language-conditional guidance. The test agent definition includes quality tool auto-format notification and the `testing.readable_test_names` profile preference. The implementation agent definition includes quality tool notification and the interface-boundary constraint for assembly fixes. The blueprint author definition includes Rules P1-P4 verbatim for preference capture.

The stakeholder spec reviewer definition includes the baked review checklist (Section 3.20). The blueprint reviewer definition includes the baked review checklist and the pattern catalog cross-reference requirement. The integration test author definition includes the registry-handler alignment test generation requirement and the per-language dispatch verification requirement.

---

## Unit 21: Diagnostic and Redo Agent Definitions

Unit 21 produces the agent definition markdown files for the diagnostic agent and the redo agent.

The diagnostic agent definition includes the three-hypothesis discipline (implementation, blueprint, spec), the dual-format output requirement (prose + structured block), and the "report most fundamental level" corollary. The integration-test-failure directive instructs the agent to evaluate the blueprint hypothesis first with highest initial credence.

The redo agent definition includes the five classification outcomes (`spec`, `blueprint`, `gate`, `profile_delivery`, `profile_blueprint`) and the redo-triggered profile revision flow.

---

## Unit 22: Support Agent Definitions

Unit 22 produces the agent definition markdown files for the help agent, the hint agent, and the reference indexing agent.

The help agent definition includes the read-only constraint (tool access restricted to Read, Grep, Glob, and web search), the gate-invocation hint formulation workflow, and the hint forwarding mechanism. The hint agent definition includes the dual-mode behavior (single-shot reactive, ledger-based proactive) and the reactive/proactive mode determination logic. The reference indexing agent definition includes document and repository reference handling.

---

## Unit 23: Utility Agent Definitions and Assembly Dispatch

Unit 23 is a composite unit that produces the git repo agent definition, the checklist generation agent definition, the regression test adaptation agent definition, the oracle agent definition, and the `PROJECT_ASSEMBLERS` dispatch table (the fifth per-language dispatch table). Unit 23 produces a single script `generate_assembly_map.py` (derived from `src/unit_23/stub.py`) whose CLI exposes the `regression-adapt` subcommand for infrastructure setup step 8. **(CHANGED IN 2.2 — Bug S3-110, previously a standalone `adapt_regression_tests.py`; consolidated into the Unit 23 CLI to eliminate orphaned duplicate source files.)**

The `PROJECT_ASSEMBLERS` dispatch table maps language identifiers to functions with signature `(project_root: Path, profile: Dict, assembly_config: Dict) -> Path`. Python assembly produces `pyproject.toml`, proper module paths, `__init__.py` files, and layout-specific structure. R assembly produces `DESCRIPTION`, `NAMESPACE`, R package structure (with roxygen2 documentation if configured, Shiny variants if applicable).

Unit 23 also provides `generate_assembly_map(blueprint_dir, project_root)` which parses the file tree annotations in `blueprint_prose.md` (the `<- Unit N` markers in the Preamble) and produces `assembly_map.json` -- a bidirectional mapping between workspace paths (`src/unit_N/module.py`) and delivered repo paths (`svp/scripts/module.py`). This function is called during Stage 5 assembly and on every reassembly. The output is stored at `.svp/assembly_map.json`.

The git repo agent definition includes the assembly mapping rules, commit order, delivery compliance awareness, README generation, quality configuration generation, and the bounded fix cycle. The checklist generation agent produces two checklists for Stage 2 agents. The regression test adaptation agent handles import rewrites and behavioral change flagging. The oracle agent definition includes the dual-mode behavior (E-mode product testing, F-mode machinery testing), the four-phase structure, and the surrogate human protocol for internal `/svp:bug` calls. The oracle agent definition also specifies the diagnostic map entry schema (fields: `event_id`, `classification`, `observation`, `expected`, `affected_artifact`) and the run ledger entry schema (fields: `run_number`, `exit_reason`, `abort_phase`, `trajectory_summary`, `discoveries`, `fix_targets`, `root_causes_found`, `root_causes_resolved`).

The `generate_assembly_map.py regression-adapt` subcommand is the deterministic regression test import adapter that reads `regression_test_import_map.json` and applies text replacements for `from X import Y`, `import X`, `@patch("X.Y")`, and `patch("X.Y")` forms. It supports per-language import replacements based on file extension. The subcommand delegates to the `adapt_regression_tests_main()` function in `src/unit_23/stub.py`, preserving the original function API for direct Python invocation (Unit 23 tests) while consolidating the CLI entry point into a single script. **(CHANGED IN 2.2 — Bug S3-110.)**

---

## Unit 24: Debug Loop Agent Definitions

Unit 24 produces the agent definition markdown files for the bug triage agent and the repair agent.

The triage agent definition includes the Socratic triage dialog, the three-hypothesis discipline, the classification outputs (`single_unit`, `cross_unit`, `build_env`, non-reproducible), `assembly_map.json` awareness for path correlation, bug number assignment logic, and the `triage_result.json` write requirement. The repair agent definition includes the narrow mandate for build/environment fixes, the `REPAIR_RECLASSIFY` escalation, and the interface-boundary constraint. Debug loop agents are language-aware: the triage agent receives the unit's language and relevant language-specific context; the repair agent generates fixes in the unit's language.

---

## Unit 25: Slash Command Files

Unit 25 produces the markdown command definition files for all SVP slash commands: `/svp:help`, `/svp:hint`, `/svp:ref`, `/svp:redo`, `/svp:bug`, `/svp:oracle`, `/svp:save`, `/svp:quit`, `/svp:status`, `/svp:clean`, and `/svp:visual-verify`.

Group A commands (save, quit, status, clean) invoke dedicated `cmd_*.py` scripts directly. Group B commands (help, hint, ref, redo, bug, oracle) include the complete action cycle: run `prepare_task.py`, spawn the agent, write terminal status to `last_status.txt`, run `update_state.py` with the correct `--phase` flag, re-run the routing script.

Each command definition specifies the correct `--phase` value. The `/svp:oracle` command includes the test project selection UX (numbered list from `docs/` and `examples/`).

---

## Unit 26: Orchestration Skill

Unit 26 produces the orchestration skill file (`SKILL.md`) that defines the main session's behavioral constraints. It contains the six-step mechanical action cycle, the REMINDER block template, the three-layer model explanation (pipeline toolchain, build-time quality, delivery toolchain), language context flow guidance, per-stage orchestrator oversight checklist references, the Hard Stop Protocol reference (Section 41) for builder script bugs during Pass 1, the break-glass behavioral guidance (Section 43.9) for E/F self-build exhaustion conditions, and spec refresh behavior at major phase transitions.

Per-stage oversight checklist references enumerated in the skill: Stage 0 references the 3-gate mentor protocol (Section 6.9: gate-specific contextual guidance at Gates 0.1, 0.2, 0.3); Stage 1 references the 7 sub-protocols (Section 7.7: decision tracking, spec draft verification, feature parity, contradiction detection, staleness/redundancy, referential integrity, pipeline fidelity); Stage 2 references the 23-item checklist (Section 8.5: profile-blueprint alignment, contract granularity, DAG validation, pattern catalog, cross-language dispatch); Stage 3 references the 26-item checklist (Section 10.15: sub-stage routing, fix ladder progression, quality gate dispatch, coverage verification, language dispatch correctness); Stage 4 references the 6-item checklist (integration test coverage, assembly retry tracking, regression adaptation review); Stage 5/6 reference their respective checklists (Section 12.17: 10-item cross-artifact consistency and validation meta-oversight; Section 12.18.13: 9-item checkpoint-annotated debug loop oversight). Stage 7 (oracle) is itself an orchestrator-level construct and needs no separate oversight protocol.

Spec refresh behavior: the skill includes a dedicated section for E/F self-build spec refresh at phase transitions (Pass 1 start, Pass 1 to transition gate, Pass 2 start, Pass 2 to transition gate, oracle start). At each transition, the orchestrator re-reads the relevant spec sections for the upcoming phase, preventing stale context from the previous phase. The skill restates the three orchestrator rules at each refresh point.

The skill includes explicit guidance for the `break_glass` action type: the orchestrator's permitted actions (present diagnostics, write lessons-learned, mark unit deferred_broken, retry with human guidance, escalate to restart) and forbidden actions (fix code directly, modify spec/blueprint, skip stages). The Hard Stop Protocol reference instructs the orchestrator to save artifacts, produce bug analysis, switch to the SVP N workspace for `/svp:bug`, then restart from checkpoint.

The skill frontmatter follows the Claude Code schema: `name`, `description`, `argument-hint`, `allowed-tools`, `model`, `effort`, `context`.

---

## Unit 27: Project Templates

Unit 27 produces the language-specific toolchain default files, delivery quality templates, and bundled example projects. It owns the Python toolchain file (`python_conda_pytest.json`), the R toolchain file (`r_renv_testthat.json`), the pipeline `ruff.toml`, and the per-language delivery quality template files.

Template files use a simple substitution syntax (`{{variable_name}}`) for profile-driven customization during Stage 5 assembly. The variables are resolved from profile quality settings (linter, formatter, line_length, etc.) and the language registry's `quality_config_mapping`.

Bundled examples include the Game of Life (Python), GoL R, GoL Plugin, GoL Python-R (mixed), and GoL R-Python (mixed). Each example contains `project_context.md`, `stakeholder_spec.md`, blueprint documents, and `oracle_manifest.json` with trajectory configuration.

---

## Unit 28: Plugin Manifest, Structural Validation, and Compliance Scan

Unit 28 is a composite unit that produces the `plugin.json` manifest, the `marketplace.json` catalog, the `structural_check.py` script, the `COMPLIANCE_SCANNERS` dispatch table (the sixth per-language dispatch table), and the `validate_dispatch_exhaustiveness()` function.

The `plugin.json` manifest is validated against the full schema (Section 40.7.1): all 12 fields including `name`, `version`, `description`, `mcpServers`, `lspServers`, `hooks`, `skills`, `agents`, `tools`, `commands`, `settings`, `permissions`. The `marketplace.json` is validated per Section 40.7.8.

`structural_check.py` is a project-agnostic AST scanner with four checks: dict registry keys never dispatched, enum values never matched, exported functions never called, and string dispatch gaps. CLI: `--target`, `--format`, `--strict`.

The `COMPLIANCE_SCANNERS` dispatch table maps language identifiers to functions with signature `(src_dir: Path, tests_dir: Path, language_config: Dict, toolchain_config: Dict) -> List[Dict]`. Python compliance: AST-based scan for banned environment patterns. R compliance: regex-based scan for banned patterns.

`validate_dispatch_exhaustiveness()` verifies that every full language has entries in all six dispatch tables and every component language has entries in its `required_dispatch_entries` tables. Uses the correct keying strategy: language ID for assemblers and scanners, dispatch key for parsers and runners.

Additional validators: MCP config validation (Section 40.7.2), LSP config validation (Section 40.7.3), skill frontmatter validation (Section 40.7.4), hook definition validation (Section 40.7.5), agent definition frontmatter validation (Section 40.7.6), cross-reference integrity checking (skills-agents, MCP-hooks, commands-manifest).

---

## Unit 29: Launcher

Unit 29 produces the standalone SVP launcher (`svp_launcher.py`). The launcher provides three CLI modes: `svp new <project_name>`, bare `svp` (auto-detect and resume), and `svp restore <project_name> --spec --blueprint-dir --context --scripts-source --profile [--plugin-path] [--skip-to]`.

The pre-flight check sequence validates: Claude Code installed, SVP plugin loaded, API credentials valid, conda installed, Python >= 3.11, pytest importable, git installed, MCP server dependencies (plugin projects only), external service reachability (plugin projects, advisory). The `_find_plugin_root()` function searches the five standard locations after checking `SVP_PLUGIN_ROOT`.

The new project creation sequence performs: directory creation, script copying, toolchain copying, ruff.toml copying (set read-only), regression test copying, hook configuration copying with path rewriting, initial `pipeline_state.json`, `svp_config.json`, CLAUDE.md generation, filesystem permissions, and session launch.

Session launch uses `subprocess.run` with `cwd=project_root`, optional `--dangerously-skip-permissions`, positional prompt `"run the routing script"` (Bug S3-68: not a `--prompt` flag), and `SVP_PLUGIN_ACTIVE=1` in the subprocess environment. The restart loop checks for `.svp/restart_signal`.

The `--plugin-path` argument (for `svp restore`) sets `SVP_PLUGIN_ROOT` in the subprocess environment, enabling nested session isolation for the oracle and Pass 2. Language runtime pre-flight checks are derived from the language registry.

`parse_args` ensures `args.command` is never `None` after returning (bare `svp` defaults to resume mode internally).

---

*End of Tier 1 descriptions. See `blueprint_contracts.md` for Tier 2 signatures and Tier 3 behavioral contracts.*
