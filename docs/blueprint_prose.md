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

## Key Concept: Socratic Question Format

**(NEW IN 2.2 — Bug S3-164, S3-165)** Every interactive question asked by `setup_agent` (Stage 0, all seven dialog areas) and `stakeholder_dialog` (Stage 1) MUST follow the Socratic Question Format: a top-level **Context** statement (one or two sentences orienting the human), a **Trade-offs** enumeration (two or more options with brief consequences), and a **Recommendation** (one option chosen with justification). Bare questions without all three sections are forbidden.

The mandate is encoded as a top-level system-prompt section in `SETUP_AGENT_DEFINITION` (Unit 18) and `STAKEHOLDER_DIALOG_DEFINITION` (Unit 20), not as a per-area instruction; it applies uniformly to binary yes/no questions and to multi-choice questions. The format reinforces the recommendation discipline (Rules 1-4 from Section 6.4) by making it structurally observable. The same format mandate is propagated to Stage 1's stakeholder dialog so the human experiences a consistent question shape across Stages 0 and 1.

The format is the entry-point for profile-flag-driven specialist behavior (Pattern P48): the human is given the orientation needed to make a deliberate choice rather than a vibe-based one, and the answer becomes a deterministic switch for the rest of the pipeline.

---

## Key Concept: Statistical Analysis Primer Chain

**(NEW IN 2.2 — Bug S3-163, S3-164, S3-165, S3-166, S3-167, S3-168)** When `project_profile.json::requires_statistical_analysis` is set true at Stage 0 (via the Area 6 mandatory question) and propagated to `pipeline_state.json::requires_statistical_analysis` by `gate_0_3_profile_approval`, the pipeline conditionally injects three statistical primers and dispatches one specialist reviewer:

- **Stage 1 (Stakeholder Dialog).** `_prepare_stakeholder_dialog` (Unit 13) appends `STAKEHOLDER_DIALOG_STATISTICAL_PRIMER` (Unit 20) covering 14 mandatory question categories (thresholds, formulas, fallbacks, multiple-comparisons policy, effect sizes, power/N, missing-data mechanism, distributional assumptions, sign conventions, NA-safety, bootstrap reproducibility, library/version pinning, decision-rule edge cases, degenerate-input handling).
- **Stage 2 (Blueprint Author).** `_prepare_blueprint_author` (Unit 13) appends `BLUEPRINT_AUTHOR_STATISTICAL_PRIMER` (Unit 20) covering 4 contract categories per unit + 5 anti-patterns + 5 pre-emission cross-checks.
- **Stage 2 (Blueprint Review, capstone dispatch).** `_route_stage_2 blueprint_review` in Unit 14 dispatches `statistical_correctness_reviewer` (Unit 20 definition; Unit 23 assembly) sequentially after the generalist `blueprint_reviewer` emits `REVIEW_COMPLETE`. Per-iteration tracking via `state.statistical_review_done` (Unit 5). Both reviewers share the `REVIEW_COMPLETE` terminal status; gate_2_2 fires after both complete. Gate 2.2 REVISE / FRESH REVIEW resets the flag.
- **Stage 3 (Test Agent).** `_prepare_test_agent` (Unit 13) appends `TEST_AGENT_STATISTICAL_PRIMER` (Unit 20) covering 11 mandatory test categories + floating-point tolerance policy. Stage 3 routing is UNCHANGED — content-only specialization.

All four sites read the centralized helper `_requires_statistical_analysis(state)` in Unit 5. When the flag is false, every site is byte-identical to baseline (regression-tested). The chain demonstrates Pattern P49/P50/P51/P52 — composable conditional-primer injection plus sequential specialist dispatch with per-iteration tracking.

---

## Key Concept: Standard Finding Block Format

**(NEW IN 2.2 — Bug S3-162)** All four review specialists — Stakeholder Spec Reviewer, Blueprint Reviewer, Blueprint Checker, Coverage Review Agent (and the Statistical Correctness Reviewer added by S3-163) — emit findings as a uniform 8-field block:

```
Finding: [one-sentence statement of what is wrong]
Severity: Critical | High | Medium | Low
Location: [file:line, slug, function name, or section identifier]
Violation: [which contract clause / spec rule / convention is broken]
Consequence: [what breaks downstream if unfixed]
Minimal Fix: [smallest concrete change that resolves the finding]
Confidence: Low | Medium | High
Open Questions: [what needs human clarification, or "none"]
```

The mandate appears verbatim in each agent's `*_DEFINITION` constant (Units 19/20). Agents that emit zero findings simply skip the blocks and proceed to terminal status. The format makes cross-agent collation and deduplication mechanical — multi-round reviews (e.g., the four-round blueprint-review pattern from fmrpqc) become tractable in a single human pass instead of requiring per-round re-tracing.

DIAGNOSTIC_AGENT and REDO_AGENT keep their separate `[STRUCTURED]` and `REDO_CLASSIFIED:` conventions — different downstream consumers parse different shapes; the 8-field block is for finding streams, not classification tokens.

---

## Key Concept: Audit Gate Enforcement

**(NEW IN 2.2 — Bug S3-158)** The `audit_blueprint_contracts(project_root)` function in Unit 28 is invoked from `dispatch_agent_status` (Unit 14) for `blueprint_author + BLUEPRINT_DRAFT_COMPLETE` and `BLUEPRINT_REVISION_COMPLETE` AFTER `validate_unit_heading_format` (Bug S3-116). The audit performs three deterministic checks that agent self-review reliably misses:

- **(a) DAG acyclicity** — DFS cycle detection on `**Dependencies:**` edges in `blueprint_contracts.md`. Forward references and cycles surface as Critical findings.
- **(c) Tier 2 signature implementation** — every Tier 2 signature in the blueprint must have a corresponding implementation in `src/unit_<N>/stub.py`. Orphan signatures surface as High findings.
- **(d) Phantom-call detection** — bare-name `Call` AST nodes in stubs that match a snake_case heuristic, are not in any Tier 2 set, and are not in a hard-coded stdlib/builtin allow-list. Phantom calls surface as Critical findings (likely `NameError` at green-run time).

Reciprocity check (b) — verifying Calls/Called-by encoding is reciprocal — is intentionally deferred (requires a blueprint format change before the check can be implemented).

The audit raises `ValueError` with a formatted multi-line report on violations, blocking BLUEPRINT_*_COMPLETE before Gate 2.1. False-positives are filterable via `.svp/audit_known_false_positives.md` (each non-comment line is a description-substring filter); the audit on the current SVP self-build blueprint surfaced five legitimate false positives, all documented. The discipline (Pattern P42) generalizes: every agent terminal-status branch in `dispatch_agent_status` should be reviewed for "what mechanical check would catch the failure mode if the agent gets it wrong?"

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

**(NEW IN 2.2 — Bug S3-164) `requires_statistical_analysis: bool` profile field.** `DEFAULT_PROFILE` carries a top-level `requires_statistical_analysis: bool` field (default `false`) populated by setup_agent's Area 6 mandatory question (Section 6.4). The field is a deterministic switch consumed by downstream specialist behavior — every primer chain, specialist reviewer dispatch, and test-agent rigor mode is keyed off this single named boolean (Pattern P48). Backward compat: profiles authored before S3-164 silently load with `false` via the deep-merge fallback in `load_profile`. The field is propagated to `pipeline_state.json::requires_statistical_analysis` by `gate_0_3_profile_approval` (Unit 14).

---

## Unit 4: Toolchain Reader

Unit 4 owns the toolchain file reading and command resolution logic. It provides `load_toolchain` (which reads a toolchain JSON file and validates its structure), `resolve_command` (which performs single-pass placeholder substitution on command templates), and `get_gate_composition` (which retrieves the ordered list of quality tool operations for a given gate identifier).

The three-layer toolchain separation (Section 3.25) is enforced here: `load_toolchain(language=None)` loads the pipeline toolchain (`toolchain.json`); `load_toolchain(language="python")` loads the language-specific build-time toolchain (`scripts/toolchain_defaults/python_conda_pytest.json`); delivery toolchain configuration is never read by this unit -- it comes from the profile (Unit 3). A structural regression test enforces that no function reads pipeline quality from the profile or delivery quality from the toolchain.

Placeholder resolution is single-pass: resolve `{run_prefix}` first (from `environment.run_prefix`), then substitute into all templates. `{env_name}` is resolved from `derive_env_name()` (Unit 1), `{python_version}` from the profile, `{flags}` from the appropriate flags key (unit_flags for Gates A/B, project_flags for Gate C), and `{target}` from the caller. After resolution, whitespace is normalized (collapsing multiple spaces, trimming).

**(Bug S3-174)** Toolchain manifest schema canonically documented at
`references/toolchain_manifest_schema.md` — covers all top-level keys,
the new `language_architecture_primers` field (cycles E1-E4 consume it),
and locks templated_helpers + verify_commands conventions.

**(Bug S3-175)** A pure-Python validator at `scripts/validate_toolchain_schema.py`
mechanically enforces the schema. Existing 3 manifests refactored additively
(language_architecture_primers placeholder added). Schema doc corrected:
framework_packages and quality_packages live under their natural parents
(testing, quality) — not top-level.

**(Bug S3-181)** The R archetype now ships five language_architecture_primer
markdown files at `scripts/primers/r/*.md` (one per agent role: blueprint_author,
implementation_agent, test_agent, coverage_review, orchestrator_break_glass).
Both R manifests (`r_conda_testthat.json`, `r_renv_testthat.json`) reference
those files via `language_architecture_primers`. The validator's primer check
now verifies that every non-null primer path resolves to an existing file
when invoked with a project_root. Cycle E1 ships authoring only; E2 wires
conditional injection at prepare_task. Sync_workspace.sh Step 1c propagates
`scripts/primers/<lang>/*` workspace ↔ repo (parallel to Step 1b for
toolchain_defaults). Python primers are deferred to E4.

**(Bug S3-184)** The Python archetype now ships its own five
language_architecture_primer markdown files at `scripts/primers/python/*.md`
(one per agent role, mirroring the R-side shape: blueprint_author,
implementation_agent, test_agent, coverage_review, orchestrator_break_glass).
The Python toolchain manifest (`python_conda_pytest.json`) references those
files via `language_architecture_primers`. Cycle E4 is content-only and rides
the existing E2/E3 dispatch wiring — no edits to dispatch helpers or to
`prepare_task_prompt` / `write_delivered_claude_md` are required because the
helpers already iterate over the manifest's `language_architecture_primers`
keys at lookup time. Both R archetype and Python archetype now ship
architectural primer files at `scripts/primers/<lang>/`. See Pattern P68
(second-archetype authoring rides existing wiring; cross-cycle test couplings
that asserted "python has no primers" are inverted to positive cross-archetype
dispatch correctness assertions).

**(Bug S3-185)** The toolchain manifest schema is the canonical extension
contract for archetype-specific behavior, documented at
`references/extending-languages.md` (~350 lines). The two-contract
architecture is intentional: the manifest schema (`scripts/toolchain_defaults/<archetype>.json`)
is the BEHAVIOR contract; `LANGUAGE_REGISTRY` (`scripts/language_registry.py`)
is the DISPATCH contract. A synthetic Rust archetype is included as a worked
example at `scripts/toolchain_defaults/rust_cargo_test.json` and
`scripts/primers/rust/` (5 primer files). The synthetic archetype is NOT
registered in `LANGUAGE_REGISTRY`; `load_toolchain(project_root, "rust")`
raises `KeyError` to document the dispatch-contract boundary. Real Rust
support would require implementing stub generator + test parser + quality
runner for Rust — out of F1 scope. After rounds A-E, adding a third language
archetype is content-only on the dispatch side: a single manifest file + 5
primer files + 1 `LANGUAGE_REGISTRY` entry, with zero dispatch-code edits.
See Pattern P69 (F1 cap-stone proof).

---

## Unit 5: Pipeline State

**Machinery unit.** This unit is tagged `machinery: true` in the blueprint extractor. Changes to this unit's contracts affect pipeline mechanisms and require `self_build_scope: "architectural"` for F-mode builds.

Unit 5 defines the `PipelineState` data structure, the `load_state` / `save_state` persistence functions, and the `VALID_STAGES`, `VALID_SUB_STAGES`, and related closed-set enumerations. The pipeline state file (`pipeline_state.json`) tracks: stage, sub_stage, current_unit, total_units, verified_units, alignment_iterations, fix_ladder_position, red_run_retries, pass_history, debug_session, debug_history, redo_triggered_from, delivered_repo_path, oracle session fields, pass/pass2 fields, deferred_broken_units, and state_hash.

SVP 2.2 adds: `primary_language`, `component_languages`, `secondary_language` (present when `archetype` is `"mixed"`, absent/None otherwise), `pass` (int or null: 1, 2, or null), `pass2_nested_session_path` (string or null), `deferred_broken_units` (array of int), `oracle_session_active`, `oracle_test_project`, `oracle_phase`, `oracle_run_count`, `oracle_nested_session_path`, `spec_revision_count` (int, default 0), and `state_hash`. **Specialist-dispatch fields (NEW IN 2.2 — Bug S3-160, S3-164, S3-168):** `toolchain_status: str` (default `"NOT_READY"`, set to `"READY"` by `infrastructure_setup` after `verify_toolchain_ready` succeeds); `requires_statistical_analysis: bool` (default `false`, propagated from profile by `gate_0_3_profile_approval`); `statistical_review_done: bool` (default `false`, per-iteration tracking flag for Stage 2 specialist reviewer dispatch — set True in `dispatch_agent_status` on `statistical_correctness_reviewer + REVIEW_COMPLETE`, reset False on Gate 2.2 REVISE / FRESH REVIEW). The centralized helper `_requires_statistical_analysis(state)` is the single read site for downstream branches (defensive `getattr(state, "requires_statistical_analysis", False)` fallback isolated here so a future profile-schema rename touches one site).

The `current_unit`/`sub_stage` co-invariant is enforced: when `current_unit` is non-null, `sub_stage` must be non-null. The `save_state` function computes and stores `state_hash` (SHA-256 of the file on disk after write) for build log chain validation.

Note: `pass1_workspace_path` is NOT a PipelineState field. Per the spec (Section 43.8), after Pass 2 completion, `pass1_workspace_path` and `pass2_nested_session_path` are cleared from state. The Pass 1 workspace path is derived at runtime from the project root and is not persisted in pipeline state.

---

## Unit 6: State Transitions

**Machinery unit.** This unit is tagged `machinery: true` in the blueprint extractor. Changes to this unit's contracts affect pipeline mechanisms and require `self_build_scope: "architectural"` for F-mode builds.

Unit 6 contains every state transition function in the pipeline. All functions accept a `PipelineState` and return a new `PipelineState` via deep copy -- the input state is never mutated. Each function validates preconditions before modifying state and raises `TransitionError` on invalid transitions.

Exported functions (complete list): `advance_stage`, `advance_sub_stage`, `complete_unit`, `advance_fix_ladder`, `increment_red_run_retries`, `reset_red_run_retries`, `increment_alignment_iteration`, `rollback_to_unit`, `restart_from_stage`, `version_document` (with `companion_paths` support), `enter_debug_session`, `authorize_debug_session`, `complete_debug_session`, `abandon_debug_session`, `update_debug_phase`, `set_debug_classification`, `enter_redo_profile_revision`, `complete_redo_profile_revision`, `enter_alignment_check`, `complete_alignment_check`, `enter_quality_gate`, `advance_quality_gate_to_retry`, `quality_gate_pass`, `quality_gate_fail_to_ladder`, `set_delivered_repo_path`, `enter_pass_1`, `enter_pass_2`, `clear_pass`, `mark_unit_deferred_broken`, `resolve_deferred_broken`.

Every function's postconditions specify which fields change and which are preserved. Every function has at least one call site in Unit 14 (routing) or another consumer unit.

**(NEW IN 2.2 — Bug S3-186, cycle G1 of Gate 6 inversion) Debug-session provenance + mode fields.** `enter_debug_session(state, bug_number)` initializes two additional fields inside the `debug_session` dict: `"mode"` (initially `None`; set later to `"bug"` or `"enhancement"` by `gate_6_1_mode_classification` dispatch) and `"source"` (set at entry to `"bug_command"` when `bug_number > 0`, or `"human_authorize"` when `bug_number == 0`). The `source` field is provenance for `_route_debug` dispatch — `bug_command` preserves the existing `bug_triage_agent → gate_6_2 → repair_agent → gate_6_3_regression_test` path bit-for-bit; `human_authorize` takes the new mode-classification + `invoke_break_glass` path. The fields are archived to `debug_history` along with the rest of the dict by `complete_debug_session` and `abandon_debug_session` — no schema change to those functions.

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

**(NEW IN 2.2 — Bug S3-160) Toolchain verification hook.** When `env_manager == "conda"` and a materialized `toolchain.json` is present, infrastructure_setup calls `verify_toolchain_ready(project_root, env_name)` (Unit 4) after `conda create -n {env_name}`. The function loads the language-specific manifest, substitutes `{run_prefix}` and `{env_name}` in each `environment.verify_commands` entry, runs them through subprocess, and returns `(success_bool, errors_list)`. Result populates `state.toolchain_status` (`"READY"` or `"NOT_READY"`) via `save_state`; on failure, infrastructure_setup raises `RuntimeError` carrying the joined verify-error messages, halting the pipeline before Stage 3 entry.

**(NEW IN 2.2 — Bug S3-161) helper-svp.R template generation.** Step 5 of infrastructure_setup, gated on `primary_language == "r" or archetype == "mixed"`, writes `tests/testthat/helper-svp.R` with a full namespace-walk body: `requireNamespace("devtools") → load_all(export_all = TRUE)`, then `read.dcf("DESCRIPTION") → asNamespace(pkg) → ls(ns, all.names = TRUE)` with each symbol assigned into `globalenv()`. The convention matches `devtools::test()` semantics encoded in the R toolchain manifest's `testing.run_command` (Pattern P45 — toolchain manifest conventions must match helper-generation conventions end-to-end). Replaces the placeholder `svp_source` stub from Bug S3-48.

**(NEW IN 2.2 — Bug S3-116) Unit heading validation.** `_count_unit_headings` and `validate_unit_heading_format` enforce the `## Unit N: <Name>` colon-separator grammar in both `blueprint_prose.md` and `blueprint_contracts.md`. Headings using em-dash, en-dash, hyphen, period, or any other separator are rejected. The validator runs as a safety net in Step 5 when `_count_unit_headings` returns 0 (the writing-side enforcement point lives in Unit 14's `dispatch_agent_status`).

**(NEW IN 2.2 — Bug S3-176) provision_only mode.** `run_infrastructure_setup` gains a `provision_only=False` parameter for Stage-0 provisioning: when True, the function runs only env-create (Step 4b, idempotent on existing envs) plus `verify_toolchain_ready` (Step 4c) and returns early. All blueprint-dependent steps (directory scaffolding, `helper-svp.R` templated copy, DAG validation, `total_units` derivation, regression test adaptation, build log creation) are skipped because the blueprint does not yet exist at Stage-0 close. The CLI flag `--provision-only` exposes the parameter to the `_route_stage_0 toolchain_provisioning` handler. `state.toolchain_status` is written to `pipeline_state.json` on completion (READY on verify success; NOT_READY on verify failure with a `RuntimeError` propagated to the orchestrator).

**(NEW IN 2.2 — Bug S3-180) pre_stage_3 dep-diff + delta-install modes.** Two new top-level functions and matching CLI mini-modes complement `run_infrastructure_setup`:

- `compute_dep_diff(project_root, env_name, runner=None)` — parses every `## Package Dependencies` block in `blueprint_contracts.md` via the helper `_parse_blueprint_package_deps`, unions the result with the language-specific manifest baseline (`testing.framework_packages` ∪ `quality.packages`), diffs against `conda list -n <env_name> --json`, partitions the delta into `delta_baseline` and `delta_blueprint_only`, and writes the result as JSON to `.svp/dep_diff_pending.json`. Returns the same dict the file contains. The `runner` parameter is an injection point for tests (defaults to `subprocess.run`).
- `install_dep_delta(project_root, env_name, runner=None)` — reads `.svp/dep_diff_pending.json`, runs `conda install -n <env_name> -y <pkgs>` for the union of partitions, then runs `verify_toolchain_ready`. On full success: sets `state.toolchain_status = "READY"`, removes the pending file, returns `(True, [])`. On failure (non-zero conda install exit, verify fails, or pending file missing/malformed): returns `(False, [errors])` with the pending file preserved so the operator can retry.

CLI: `main` accepts `--dep-diff` and `--install-delta` as mutually exclusive mini-modes that bypass the full 9-step flow. Each invokes the corresponding function and exits 0 on success / 1 on failure. The Unit 14 `_route_pre_stage_3` handler emits these as `run_command` action blocks for the `dep_diff` and `dep_diff_install` sub-stages respectively.

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

**(NEW IN 2.2 — Bug S3-159) Multi-mode mode/expected-status stamping.** The `_prepare_*` helpers for multi-mode agents (setup_agent, stakeholder_dialog, blueprint_author) stamp explicit `## Mode` and `## Expected Terminal Status` markdown blocks into the task prompt, sourced from the canonical `(agent_type, mode) -> valid_statuses` mapping in Unit 14. The agent reads its mode and constrained status set before authoring, eliminating cross-mode terminal-status emission.

**(NEW IN 2.2 — Bug S3-165, S3-166, S3-167) Conditional statistical primer injection.** Three `_prepare_*` helpers consult `_requires_statistical_analysis(state)` (Unit 5) and conditionally append a stage-specific primer constant (sibling of the agent definition in Unit 20):
- `_prepare_stakeholder_dialog` → `STAKEHOLDER_DIALOG_STATISTICAL_PRIMER` (14 question categories).
- `_prepare_blueprint_author` → `BLUEPRINT_AUTHOR_STATISTICAL_PRIMER` (4 contract categories + 5 anti-patterns + 5 cross-checks).
- `_prepare_test_agent` → `TEST_AGENT_STATISTICAL_PRIMER` (11 test categories + tolerance policy).

Each append is a single one-liner guarded on the centralized helper. When the flag is false, every prepare-helper is byte-identical to its pre-batch form (Pattern P49/P50/P51 — composable conditional-primer injection at task-prompt assembly time).

**(NEW IN 2.2 — Bug S3-168) Statistical correctness reviewer dispatch wiring.** `KNOWN_AGENT_TYPES` and `SELECTIVE_LOADING_MATRIX` include `statistical_correctness_reviewer` (loads spec, blueprint both files, project context, references, lessons learned). New helper `_prepare_statistical_correctness_reviewer` mirrors `_prepare_blueprint_reviewer`. `prepare_task_prompt` dispatches the new agent type. The specialist's terminal status is `REVIEW_COMPLETE` (shared with the generalist `blueprint_reviewer`).

**(NEW IN 2.2 — Bug S3-182) Per-archetype language-architecture primer dispatch.** A new module-level helper `_get_language_architecture_primer(project_root, state, agent_type)` reads `state.primary_language`, loads the toolchain manifest via `load_toolchain` (Unit 4), looks up `toolchain["language_architecture_primers"][agent_type]`, resolves the primer file path under `project_root`, and returns the file contents — or `None` at any failure point (missing state, missing language, missing manifest, missing field, missing key, missing file, unreadable file). Four `_prepare_<agent>()` helpers — `_prepare_blueprint_author`, `_prepare_implementation_agent`, `_prepare_test_agent`, `_prepare_coverage_review` — invoke `_get_language_architecture_primer` exactly once with the canonical agent_type key (`"blueprint_author"`, `"implementation_agent"`, `"test_agent"`, `"coverage_review"`) and append the result to their sections list when non-`None`. Defensive guards at every step ensure the append silently no-ops on any missing prerequisite — task-prompt assembly never crashes because of primer plumbing. The fifth manifest key (`orchestrator_break_glass`) is wired by E3 (S3-183) at child-project CLAUDE.md generation time, not at `prepare_task`. Composes with the per-flag statistical primer dispatch (S3-165/166/167) on the orthogonal archetype × flag axes — both append blocks fire from the same helper, both gated by their own conditionals (Pattern P66).

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

**(NEW IN 2.2 — Bug S3-154, S3-164) Gate 0.3 propagation.** `dispatch_gate_response` for `gate_0_3_profile_approval` on PROFILE APPROVED reads `project_profile.json`, extracts `language.primary` and `requires_statistical_analysis`, and assigns both to `state.primary_language` and `state.requires_statistical_analysis` BEFORE `advance_stage(state, "1")`. Defensive on missing file / missing field / malformed JSON: log a warning to stderr and leave the existing field unchanged.

**(NEW IN 2.2 — Bug S3-158) Mechanical audit gate.** `dispatch_agent_status` for `blueprint_author + BLUEPRINT_DRAFT_COMPLETE` and `BLUEPRINT_REVISION_COMPLETE` invokes `audit_blueprint_contracts(project_root)` (Unit 28) AFTER `validate_unit_heading_format` (Bug S3-116). The audit performs three deterministic checks (DAG acyclicity, Tier 2 signature implementation existence, phantom-call detection) and raises `ValueError` with a formatted multi-line audit report on violations. False-positives are filterable via `.svp/audit_known_false_positives.md`. See "Key Concept: Audit Gate Enforcement" above.

**(NEW IN 2.2 — Bug S3-159) Multi-mode dispatch hygiene.** `_make_action_block` accepts and emits an `expected_terminal_status` field (List[str]) populated from the canonical `(agent_type, mode) -> valid_statuses` mapping. `dispatch_agent_status` validates the agent's emitted status against the per-(agent, mode) valid set and raises a named `ValueError` on mismatch BEFORE any state transition or downstream validator runs. When `(agent_type, sub_stage) → mode` is ambiguous, dispatch falls back to the per-agent whitelist.

**(NEW IN 2.2 — Bug S3-155) R-archetype quality gate target.** `_cmd_quality_gate` branches on `state.primary_language` (or `_load_primary_language`): R targets the zero-padded `tests/testthat/test-unit-{N:02d}.R` file (registry-canonical pattern); Python and others target the `tests/unit_{N}` directory (unchanged). When `state.current_unit` is unset, the fallback is the language-appropriate root.

**(NEW IN 2.2 — Bug S3-168) Specialist reviewer sequential dispatch + per-iteration tracking flag reset.** `_route_stage_2 blueprint_review` branches on `(_requires_statistical_analysis(state) and not state.statistical_review_done)` to dispatch `statistical_correctness_reviewer` after the generalist `blueprint_reviewer`'s `REVIEW_COMPLETE`. `dispatch_agent_status` for the specialist's `REVIEW_COMPLETE` sets `state.statistical_review_done = True`; `dispatch_gate_response` for Gate 2.2 REVISE / FRESH REVIEW resets the flag to False so the next iteration repeats both reviewers (APPROVE preserves the flag — no next iteration follows). When the flag is false, `_route_stage_2 blueprint_review` is byte-identical to baseline (regression-tested).

**(NEW IN 2.2 — Bug S3-176) Stage-0 toolchain provisioning sub-stage.** New `sub_stage = "toolchain_provisioning"` (stage 0); new gate `gate_0_4_toolchain_provisioned` with responses `["PROCEED", "ABORT"]`. `gate_0_3` PROFILE APPROVED transitions into the new sub-stage instead of calling `advance_stage(state, "1")` directly (the field syncs from S3-154 `primary_language` and S3-164 `requires_statistical_analysis` are preserved). `_route_stage_0 toolchain_provisioning` handler emits `run_command(infrastructure_setup.py --provision-only ...)` while `state.toolchain_status != "READY"` (with `last_status != "COMMAND_FAILED"`), emits `pipeline_held` carrying `TOOLCHAIN_PROVISION_FAILED` when `last_status == "COMMAND_FAILED"`, and emits `human_gate(gate_0_4_toolchain_provisioned)` when READY. `dispatch_gate_response` for `gate_0_4` PROCEED calls `advance_stage(state, "1")` (the new place the stage-1 advance happens); ABORT resets `state.toolchain_status` to `"NOT_READY"` and returns to `sub_stage = "project_profile"` so the operator can revise the profile. `dispatch_command_status` accepts a new `command_type = "infrastructure_setup_provision_only"` (returns `_copy(state)` on either COMMAND_SUCCEEDED or COMMAND_FAILED — the command itself sets `state.toolchain_status` as a side effect; routing consults the flag on the next pass).

**(NEW IN 2.2 — Bug S3-186, cycle G1 of Gate 6 inversion) `gate_6_1_mode_classification` + `invoke_break_glass` action_type.** A new gate `gate_6_1_mode_classification` is inserted immediately after `gate_6_0_debug_permission` AUTHORIZE for human-sourced debug sessions. Valid responses: `["BUG", "ENHANCEMENT"]`. The Socratic dialog (BUG vs ENHANCEMENT explanation + four Socratic prompts) ships verbatim in the gate's `reminder` field — no constants in unit_20 or elsewhere. `dispatch_gate_response` for `gate_6_1_mode_classification` sets `state.debug_session["mode"]` to `"bug"` or `"enhancement"`; phase is NOT advanced. The next routing pass observes the mode field is set and emits a new `action_type` `"invoke_break_glass"` with structured payload `{"mode": <mode>}`. The action returns control to the orchestrator with the mode tag; the orchestrator follows the Manual Bug-Fixing Protocol in CLAUDE.md (mode-aware sub-flows ship in cycle G2). There is no POST command on `invoke_break_glass`; the orchestrator drives completion via the existing DEBUG_SESSION_COMPLETE terminal status path. The pre-existing /svp:bug auto-dispatch path (`bug_triage_agent → gate_6_2 → repair_agent → gate_6_3_regression_test`) is preserved bit-for-bit and selected when `state.debug_session["source"] == "bug_command"` (provenance set in `enter_debug_session` from `bug_number > 0`). The existing `gate_6_1_regression_test` is renamed to `gate_6_3_regression_test` (vocabulary-only rename — behavior unchanged) to free the gate_6_1 slot for mode classification semantically. **(EXTENDED IN 2.2 — Bug S3-187, cycle G2 of Gate 6 inversion.)** The gate vocabulary + dispatch shipped here is now backed by the Gate 6 Canonical Break-Glass Path content embedded in the delivered CLAUDE.md template (Unit 23 narrative + Unit 29 template constant): bug mode runs the 8-step cycle augmented by Layer-Triage L1-L5 in DIAGNOSE; Enhancement Mode runs the SPEC_AMENDMENT → BLUEPRINT_AMENDMENT → IMPLEMENTATION → TESTS → VERIFY → SYNC mini-pipeline.

**(NEW IN 2.2 — Bug S3-180) pre_stage_3 dep-diff + delta-install sub-stages.** Two new sub-stages within `stage = "pre_stage_3"`: `"dep_diff"` and `"dep_diff_install"`. New gate `gate_2_3_toolchain_verified` with responses `["PROCEED", "ABORT"]` (distinct from `gate_2_3_alignment_exhausted` which lives in stage 2). `gate_2_2_blueprint_post_review` APPROVE handler now also calls `advance_sub_stage(state, "dep_diff")` after `advance_stage(state, "pre_stage_3")` so the dep-diff state machine runs before the existing infrastructure-setup full flow. `_route_pre_stage_3` extended with branch logic on `state.sub_stage`: `"dep_diff"` emits `run_command(infrastructure_setup.py --dep-diff ...)` while `last_status != "COMMAND_SUCCEEDED"` (with `last_status != "COMMAND_FAILED"`), emits `pipeline_held` carrying `TOOLCHAIN_DEP_DIFF_FAILED` on `COMMAND_FAILED`, reads `.svp/dep_diff_pending.json` on `COMMAND_SUCCEEDED` and either advances `sub_stage` to `None` (empty delta) or emits `human_gate(gate_2_3_toolchain_verified)` with the package list in the reminder. `"dep_diff_install"` emits `run_command(infrastructure_setup.py --install-delta ...)` while `last_status != "COMMAND_SUCCEEDED"`, emits `pipeline_held` carrying `TOOLCHAIN_DELTA_INSTALL_FAILED` on `COMMAND_FAILED`, and advances `sub_stage` to `None` on `COMMAND_SUCCEEDED`. `sub_stage = None` falls through to the existing pre_stage_3 flow (advance_stage to "3", run_infrastructure_setup if total_units==0, etc.) — preserving the routing-safety invariant. `dispatch_gate_response` for `gate_2_3_toolchain_verified` PROCEED calls `advance_sub_stage(state, "dep_diff_install")`; ABORT sets `state.stage = "2"`, `state.sub_stage = "blueprint_dialog"` and removes `.svp/dep_diff_pending.json`. `dispatch_command_status` accepts two new `command_type` values: `"infrastructure_setup_dep_diff"` and `"infrastructure_setup_install_delta"` (both return `_copy(state)` on either `COMMAND_SUCCEEDED` or `COMMAND_FAILED` — the commands write side-effect artifacts and `state.toolchain_status`; routing consults state on the next pass).

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

**(NEW IN 2.2 — Bug S3-188, cycle G3 of Gate 6 inversion) DEBUG_SESSION_MODE-aware enhancement-mode permits.** `generate_write_authorization_sh()` extracts a new shell variable `DEBUG_SESSION_MODE` from `pipeline_state.json` `debug_session.mode` (initialized to `"none"` when no debug_session is active). Inside the existing `DEBUG_AUTHORIZED=true` block, when `DEBUG_SESSION_MODE = "enhancement"`, writes to upstream layers (`specs/`, `blueprint/`, `references/`, `.svp/`) are permitted on top of the existing bug-mode permits (`tests/regressions/`, `delivered_repo_path`, unit-specific dirs). Enhancement mode work legitimately needs to amend specs and blueprint contracts per the SPEC_AMENDMENT-first mini-pipeline; bug mode preserves the prior restrictive policy bit-for-bit (writes to `specs/`, `blueprint/`, `references/` remain DENIED under `mode=bug`). The branch is ADDITIVE — bug-mode permits still apply when mode=enhancement.

---

## Unit 18: Setup Agent Definition

Unit 18 produces the setup agent's agent definition markdown file (`setup_agent.md`). The system prompt contains Rules 1-4 verbatim (plain language explanations, best-option recommendations, sensible defaults, progressive disclosure) as numbered behavioral requirements. The definition includes the Area 0 language dialog flow (archetype selector with Options A-F), the six dialog areas (0-5), the profile schema with exact canonical field names, and the contradiction detection rules.

The setup agent operates in two modes (project context and project profile) within Stage 0, distinguished by the mode identifier injected by the preparation script. The agent uses a single ledger (`ledgers/setup_dialog.jsonl`) for both phases.

The dialog covers six areas (0-5): Area 0 (Language/Ecosystem), Area 1 (VCS), Area 2 (README/Docs), Area 3 (Testing), Area 4 (Licensing/Metadata), Area 5 (Quality). Area 0 determines the target language(s) and configures the build/test/quality toolchain; Areas 1-5 cover delivery preferences. Area 5 may be skipped if Area 0 already populated quality settings.

For Mode A (self-build), the definition includes Mode A default pre-population logic. For Option C (plugin), it includes the extended plugin interview (4 questions about external services, auth, hook events, and skills). For Option D (mixed-language), it includes the focused mixed-language dialog flow (3-4 questions): (1) "Which language owns the project structure?" -- sets `language.primary`, the other becomes `language.secondary`; (2) "What's the communication direction?" -- sets `language.communication` with bridge libraries (rpy2 for Python-to-R, reticulate for R-to-Python); (3) "Same tools as pipeline for [primary]?" -- fast-path populates primary delivery/quality with pipeline defaults, or enters detailed tool dialog; (4) "Default tools for [secondary]?" -- presents secondary language's registry defaults with opt-out. Hard constraints enforced: both `environment_recommendation` forced to `"conda"`, both `dependency_format` forced to `"environment.yml"`. Profile fields populated: `archetype: "mixed"`, `language.primary`, `language.secondary`, `language.communication`, and both `delivery` and `quality` sections for both languages. For Options E/F (self-build), plugin fields are auto-populated from SVP context.

**(NEW IN 2.2 — Bug S3-164) Socratic Question Format mandate + Area 6 mandatory question.** The setup agent system prompt includes a top-level Socratic Question Format section mandating that every question across all seven areas follow the Context + Trade-offs + Recommendation shape (see "Key Concept: Socratic Question Format" above). The mandate is not a per-area instruction; it applies uniformly to binary yes/no questions and to multi-choice questions. Area 6 adds a mandatory question demonstrating the format: "Does this project require statistical or scientific-correctness rigor (formulas, thresholds, fallbacks, decision rules, multiple-comparisons policy, effect sizes, power/N analyses)?". The answer populates `requires_statistical_analysis: bool` (Unit 3 default `false`) which becomes the deterministic switch for downstream specialist behavior (Pattern P48).

---

## Unit 19: Blueprint Checker Definition

Unit 19 produces the blueprint checker agent definition markdown file (`blueprint_checker.md`). The system prompt includes the mandatory alignment checklist: DAG acyclicity validation, profile preference validation (Layer 2), pattern catalog validation (P1-P13+), contract granularity verification (exported function coverage, per-gate-option dispatch contracts, call-site verification, re-entry path documentation), and language registry completeness validation.

The checker receives the Blueprint Alignment Checker Checklist (`.svp/alignment_checker_checklist.md`) and works through it item by item. It validates internal consistency between the prose and contracts files. It uses the "report most fundamental level" corollary: spec problems supersede blueprint problems.

**(NEW IN 2.2 — Bug S3-162) Standard 8-field finding block format.** `BLUEPRINT_CHECKER_DEFINITION` mandates the 8-field finding block (Finding / Severity / Location / Violation / Consequence / Minimal Fix / Confidence / Open Questions) — same format as STAKEHOLDER_REVIEWER, BLUEPRINT_REVIEWER, COVERAGE_REVIEW. See "Key Concept: Standard Finding Block Format" above. Collation across rounds becomes mechanical; cross-agent dedup becomes straightforward.

**(NEW IN 2.2 — Bug S3-158) Mechanical audit gate hand-off.** The blueprint checker's findings overlap with but do not subsume the deterministic `audit_blueprint_contracts()` (Unit 28) hooked into `dispatch_agent_status` for the blueprint_author. The audit catches DAG cycles, orphan signatures, and phantom calls before BLUEPRINT_*_COMPLETE propagates; the checker validates spec-fidelity and contract granularity at alignment time. Both layers are needed (Pattern P42).

---

## Unit 20: Construction Agent Definitions

Unit 20 produces the agent definition markdown files for all construction-phase agents: stakeholder dialog agent, stakeholder spec reviewer, blueprint author agent, blueprint reviewer, test agent, implementation agent, coverage review agent, and integration test author.

Each definition's system prompt references `LANGUAGE_CONTEXT` for language-conditional guidance. The test agent definition includes quality tool auto-format notification and the `testing.readable_test_names` profile preference. The implementation agent definition includes quality tool notification and the interface-boundary constraint for assembly fixes. The blueprint author definition includes Rules P1-P4 verbatim for preference capture.

The stakeholder spec reviewer definition includes the baked review checklist (Section 3.20). The blueprint reviewer definition includes the baked review checklist and the pattern catalog cross-reference requirement. The integration test author definition includes the registry-handler alignment test generation requirement and the per-language dispatch verification requirement.

**(NEW IN 2.2 — Bug S3-156) Blueprint author split-format mandate.** `BLUEPRINT_AUTHOR_DEFINITION` mandates split-format output: TWO files at `blueprint/blueprint_prose.md` and `blueprint/blueprint_contracts.md`, with explicit citation to `ARTIFACT_FILENAMES` (Unit 1) as the canonical source of truth. Unified single-file output is forbidden. The mandate appears in the Methodology section, not just in a delivered-file-tree appendix (Pattern P40 — agent prompts must be prescriptive about canonical paths).

**(NEW IN 2.2 — Bug S3-170) Per-function Calls citations.**
`BLUEPRINT_AUTHOR_DEFINITION` mandates a `## Calls` section in each
blueprint unit's Tier 3, listing per-function Calls citations (e.g.,
`- foo() in Unit 5`). The `## Called-by` section is NOT authored —
it will be mechanically derived from the global Calls graph by a
later audit-extension cycle.

**(Bug S3-171)** Migration of the 29 existing Units to include `## Calls`
sections completed; per-function citations now appear under each unit's
Tier 3. Subsequent revisions inherit the format by mandate. The companion
`## Called-by` section remains derived mechanically (cycle 3, S3-172).

**(Bug S3-177)** BLUEPRINT_AUTHOR_DEFINITION mandates a per-Unit
`## Package Dependencies` section in Tier 3 (parallel to S3-170's
`## Calls`). Lists external packages with canonical install-names.
Distinct from inline `**Dependencies:**` (inter-unit deps) and
`## Calls` (per-function call graph). Cycle C2 (S3-178) migrates
existing 29 units; cycle C3 (S3-179) ships the audit dep-reachability
check.

**(Bug S3-178)** Migration of the 29 existing Units to include
`## Package Dependencies` sections completed; per-Unit blocks now appear
under each Unit's Tier 3 (placed after `## Calls`, before
`**Dependencies:**`). All SVP units are stdlib-only — every block is
`None (stdlib only).`. Subsequent revisions inherit the format by mandate.

**(NEW IN 2.2 — Bug S3-157) Stakeholder dialog Cross-Reference Reconciliation.** `STAKEHOLDER_DIALOG_DEFINITION` includes a convention-agnostic Cross-Reference Reconciliation methodology step before terminal-status emission. The audit enumerates references and targets, verifies resolution, fixes unambiguous mismatches, and halts with structured error on ambiguous cases. Empirical evidence: in pipeline-authored multi-chunk specs without this step, ~45% of narrative cross-references pointed to wrong slug numbers (fmrpqc 19/42).

**(NEW IN 2.2 — Bug S3-162) Standard 8-field finding block format.** STAKEHOLDER_REVIEWER, BLUEPRINT_REVIEWER, and COVERAGE_REVIEW definitions mandate the uniform 8-field finding block (Finding / Severity / Location / Violation / Consequence / Minimal Fix / Confidence / Open Questions). See "Key Concept: Standard Finding Block Format" above.

**(NEW IN 2.2 — Bug S3-163) STATISTICAL_CORRECTNESS_REVIEWER agent definition.** Unit 20 adds `STATISTICAL_CORRECTNESS_REVIEWER_DEFINITION` — a domain-specialist with a narrow mandate (verify formulas, thresholds, fallbacks, decision rules, multiple-comparisons policy, effect sizes, power/N) and an explicit anti-mandate (MUST NOT flag architecture / naming / performance — those concerns belong to `blueprint_reviewer`). Emits findings using the standard 8-field block. Assembled into `svp/agents/statistical_correctness_reviewer.md` by Unit 23.

**(NEW IN 2.2 — Bug S3-165, S3-166, S3-167) Three statistical primer constants.** Unit 20 also defines three sibling primer constants:
- `STAKEHOLDER_DIALOG_STATISTICAL_PRIMER` (14 mandatory question categories) — appended to stakeholder_dialog prompts when `requires_statistical_analysis=true`.
- `BLUEPRINT_AUTHOR_STATISTICAL_PRIMER` (4 contract categories per unit + 5 anti-patterns + 5 cross-checks) — appended to blueprint_author prompts when the flag is true.
- `TEST_AGENT_STATISTICAL_PRIMER` (11 mandatory test categories + floating-point tolerance policy) — appended to test_agent prompts when the flag is true. Stage 3 routing UNCHANGED — content-only specialization.

The static agent definitions stay domain-agnostic; the conditional primers carry domain-specific guidance only when the profile flag warrants it. Unit 13's `_prepare_*` helpers append primers via `_requires_statistical_analysis(state)`. See "Key Concept: Statistical Analysis Primer Chain" above for the full chain.

**(NEW IN 2.2 — Bug S3-165) Stakeholder dialog Socratic mandate.** `STAKEHOLDER_DIALOG_DEFINITION` mandates the Socratic Question Format (Context + Trade-offs + Recommendation) for every question — parity with the same mandate on `setup_agent` (Unit 18, S3-164). The human experiences a consistent question shape across Stages 0 and 1.

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

**(NEW IN 2.2 — Bug S3-163) Statistical correctness reviewer assembly registration.** Unit 23's assembly path emits `svp/agents/statistical_correctness_reviewer.md` from Unit 20's `STATISTICAL_CORRECTNESS_REVIEWER_DEFINITION` constant, alongside the other Stage 2 review agents. The agent is registered as a discoverable Claude Code agent via the standard YAML frontmatter convention (Section 40.7.6). The dispatch wiring (Pattern P52) was deferred to S3-168 and lands in Unit 14 (`_route_stage_2`) and Unit 13 (`KNOWN_AGENT_TYPES` + `SELECTIVE_LOADING_MATRIX` + `_prepare_statistical_correctness_reviewer`).

**(NEW IN 2.2 — Bug S3-183) Orchestrator break-glass primer injection at Stage 5 delivery.** Unit 23 owns the dispatch surface for the 5th key in the toolchain manifest's `language_architecture_primers` field — `orchestrator_break_glass` — which the four other primer keys do NOT share. The four prepare-task primer keys (S3-182) are dispatched from Unit 13 because their consumers are subagents whose task prompts are assembled by `prepare_task_prompt`. The orchestrator is the main Claude Code session — it has no subagent task prompt; its effective "task prompt" is the on-disk CLAUDE.md loaded at session boot. So Unit 23's `write_delivered_claude_md` (S3-147) is extended in this cycle to read the manifest's `orchestrator_break_glass` field via the new module-level helper `_get_orchestrator_break_glass_primer_text(project_root, profile)` and, when the helper returns non-`None`, append the primer file's contents as a top-level `## Orchestrator Break-Glass Primer (Archetype-Specific)` section to the rendered child CLAUDE.md. Defensive at every step: missing `profile["language"]["primary"]`, missing manifest, missing field, missing key, missing file, and unreadable file each return `None` so Stage 5 delivery never fails because of primer plumbing. The function's signature gains an optional `project_root` parameter (default `None` for back-compat with existing callers and tests); the three assembler call sites (`assemble_python_project`, `assemble_r_project`, `assemble_plugin_project`) pass `project_root=project_root` through. The mixed assembler inherits via the primary assembler. The template constant `CLAUDE_MD_DELIVERED_REPO_TEMPLATE` (Unit 29) is unchanged — injection happens by string concatenation in Unit 23 after `.format(project_name=project_name)`.

**(NEW IN 2.2 — Bug S3-188, cycle G3 of Gate 6 inversion) Oracle Surrogate Human Protocol rewrite.** `ORACLE_AGENT_DEFINITION`'s "Surrogate Human Protocol" section is rewritten to describe the actual mechanism: when the oracle detects an issue during green-run that requires triage, repair, or diagnostic work, the oracle invokes the appropriate agent DIRECTLY as a Task subagent (`triage_agent` / `bug_triage_agent`, `repair_agent`, `diagnostic_agent`) and parses the agent's terminal status line. The oracle does NOT respond to gates on the human's behalf — gates ALWAYS go to the human, even during oracle sessions. Routing preserves `oracle_session_active` across debug sessions so the oracle green-run resumes after `DEBUG_SESSION_COMPLETE`. The prior "auto-respond at Gates 6.0/6.1/6.2" wording was documentation-only; routing has never implemented gate-surrogacy. G3 corrects the wording to match what was always true mechanically.

**(NEW IN 2.2 — Bug S3-187, cycle G2 of Gate 6 inversion) Gate 6 canonical-path content embedded in the delivered CLAUDE.md template.** The delivered child-template `CLAUDE_MD_DELIVERED_REPO_TEMPLATE` (Unit 29) carries a "## Gate 6 — Canonical Break-Glass Path" section that authoritatively encodes the orchestrator's mode-aware break-glass protocol: the DIAGNOSE step is structured as Layer-Triage L1-L5 (L1 Reproduce, L2 Spec, L3 Blueprint, L4 Code, L5 Test) so the orchestrator names the layer where the root cause lives before proposing a fix; bug mode runs the existing 8-step cycle (DIAGNOSE → PLAN → EXECUTE → EVALUATE → LESSONS → REGRESSION → VERIFY → SYNC + COMMIT) augmented only at the DIAGNOSE step; Enhancement Mode is a parallel mini-pipeline (SPEC_AMENDMENT → BLUEPRINT_AMENDMENT → IMPLEMENTATION → TESTS → VERIFY → SYNC) for changes that alter intended behavior — specs and contracts amend before code, per S3-169. The section closes with a "### Choosing the entry-point" subsection that names when to run break-glass directly versus call /svp:bug as a sub-tool versus accept an auto-dispatched /svp:bug. Both modes share Gate 6.0 authorization and the `DEBUG_SESSION_COMPLETE` terminal status from G1 (S3-186). The same content lives at workspace `CLAUDE.md` so the SVP self-build orchestrator and all delivered children share one protocol. The G1 single-paragraph addendum that previously registered the `invoke_break_glass` action_type is absorbed into the new section, not duplicated.

---

## Unit 24: Debug Loop Agent Definitions

Unit 24 produces the agent definition markdown files for the bug triage agent and the repair agent.

The triage agent definition includes the Socratic triage dialog, the three-hypothesis discipline, the classification outputs (`single_unit`, `cross_unit`, `build_env`, non-reproducible), `assembly_map.json` awareness for path correlation, bug number assignment logic, and the `triage_result.json` write requirement. The repair agent definition includes the narrow mandate for build/environment fixes, the `REPAIR_RECLASSIFY` escalation, and the interface-boundary constraint. Debug loop agents are language-aware: the triage agent receives the unit's language and relevant language-specific context; the repair agent generates fixes in the unit's language.

---

## Unit 25: Slash Command Files

Unit 25 produces the markdown command definition files for all SVP slash commands: `/svp:help`, `/svp:hint`, `/svp:ref`, `/svp:redo`, `/svp:bug`, `/svp:oracle`, `/svp:save`, `/svp:quit`, `/svp:status`, `/svp:clean`, and `/svp:visual-verify`.

Group A commands (save, quit, status, clean) invoke dedicated `cmd_*.py` scripts directly. Group B commands (help, hint, ref, redo, bug, oracle) include the complete action cycle: run `prepare_task.py`, spawn the agent, write terminal status to `last_status.txt`, run `update_state.py` with the correct `--phase` flag, re-run the routing script.

Each command definition specifies the correct `--phase` value. The `/svp:oracle` command includes the test project selection UX (numbered list from `docs/` and `examples/`).

**(NEW IN 2.2 — Bug S3-188, cycle G3 of Gate 6 inversion) /svp:bug Scope guard.** `BUG_COMMAND` (the `/svp:bug` markdown definition) ships a "Scope guard" section after the existing Notes that explicitly limits its appropriate scope to narrow contract-bounded fixes: the bug must be genuinely localized to a single unit; the relevant blueprint contract must be well-specified; the fix must be a mechanical alignment of code to contract. The Scope guard names four scope-creep signals (multiple units affected; spec questions arising; cross-layer interactions spec+blueprint+code or beyond; behavior intent unclear) and instructs the orchestrator to ABORT the /svp:bug flow and escalate to break-glass when any signal fires. Per CLAUDE.md "Choosing the entry-point" guidance, break-glass is the canonical default for human-initiated debug; /svp:bug is a narrow sub-tool. Auto-dispatched /svp:bug (routing-detected red runs) follows the same narrowness; the orchestrator MAY abort and escalate at any time.

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

**(NEW IN 2.2 — Bug S3-158) `audit_blueprint_contracts(project_root)` function.** Unit 28 owns the new mechanical audit gate invoked from Unit 14's `dispatch_agent_status` for `blueprint_author + BLUEPRINT_DRAFT_COMPLETE` / `BLUEPRINT_REVISION_COMPLETE` AFTER `validate_unit_heading_format` (Bug S3-116). The audit performs three deterministic checks on the contract surface: (a) DAG acyclicity via DFS cycle detection on `**Dependencies:**` edges; (c) Tier 2 signature implementation existence in `src/unit_<N>/stub.py`; (d) phantom-call detection (bare-name `Call` AST nodes that match a snake_case heuristic, are not in any Tier 2 set, and are not in a hard-coded stdlib/builtin allow-list). Reciprocity check (b) is intentionally deferred. Raises `ValueError` with a formatted multi-line audit report if violations remain after filtering against `.svp/audit_known_false_positives.md`. Findings carry `check`, `severity`, `location`, `description`. See "Key Concept: Audit Gate Enforcement" above for the discipline (Pattern P42).

**(Bug S3-172)** Audit gains per-function Calls resolution check;
consumes cycle-2 migration data; closes IMPROV-09 deferred
reciprocity check (b). Mechanical Called-by inversion computed
in-function; not materialized.

**(Bug S3-179)** Audit gains two new checks: package_resolution (declared
deps in universe) and undeclared_import (stub imports in blueprint).
Consumes cycle-C2 migration data. Closes round C of env provisioning
sub-project. SVP-self is stdlib-only — audit passes clean on day one;
real value materializes for future R/Python data-science archetypes.

The compliance-scan entries also gain audit-related compliance entries: the unit-heading grammar invariant (Bug S3-116), the audit_known_false_positives.md formatting rules, and the dispatch-time validation of unit headings BEFORE Gate 2.1.

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
