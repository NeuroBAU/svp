# Changelog

All notable changes to SVP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.1] - 2026-03-19

### Added

- RFC-2: Unit-level preference capture in blueprint dialog (Rules P1-P4)
- Generalized structural completeness checking -- four-layer defense system (Bug 72)
- 163 structural completeness tests automating 14 declaration-vs-usage techniques (Bug 71)
- Stage 3 full error handling: fix ladder, diagnostic escalation, Gates 3.1/3.2 (Bug 65)
- Stage 4 failure handling: Gates 4.1/4.2, ASSEMBLY FIX dispatch (Bug 68)
- Debug loop gates: Gate 6.0 (permission), Gate 6.1 (regression test), Gate 6.5 (commit) (Bug 69)
- Selective blueprint loading per agent type per spec Section 3.16 (Bugs 60-62)
- Gate C unused function detection with Gate 5.3 human gate (Bugs 56-58)
- Gate C stub import detection in test files (Bug 74) -- 5th structural check
- Regression test import adaptation script (Bug 85) -- `adapt_regression_tests.py` with JSON mapping
- **Configurable Agent Models**: `pipeline.agent_models` in `project_profile.json` -- human chooses opus/sonnet/haiku per agent during Setup Area 6. Routing emits MODEL field in invoke_agent action blocks. Claude Code maps short names to latest model versions automatically.
- **GitHub Repository Configuration**: `vcs.github` in `project_profile.json` -- four modes (new, existing_force, existing_branch, none). Setup agent validates `gh` CLI installation and authentication. Git repo agent handles each mode during Stage 5.
- **README Mode**: `readme.mode` in `project_profile.json` -- generate (new) or update (preserve existing). Setup agent collects existing README via @ command when update mode selected. Git repo agent uses existing README as base in update mode.

### Fixed

- 34 bugs (52-85) spanning orphaned functions, dead gates, no-op dispatch handlers, routing loops, test infrastructure, quality gate state mismatch, skipped infrastructure setup, agent tool permissions, toolchain compatibility, spec structural gaps, blueprint split compliance
- Bug 73: Three routing/dispatch loops from unchanged state returns (Stage 0 PROFILE_COMPLETE, Gate 5.3 OVERRIDE CONTINUE, Gate 4.1 ASSEMBLY FIX)
- Bug 74: Regression tests must test real scripts, not stubs (test target invariant added to checker/reviewer checklists)
- Bug 75: Coverage review auto-format quality gate TransitionError (sub_stage=coverage_review vs quality_gate_b mismatch)
- Bug 76: Pre-Stage-3 routing skipped infrastructure setup (conda env creation, quality package install)
- Bug 77: `--no-banner` flag in toolchain.json incompatible with conda ≥25.x
- Bug 78: Reference indexing agent missing Write tool — cannot produce summaries.md
- Bug 79: Reference indexing task prompt loaded summaries.md (own output) instead of raw reference docs (input)
- Bug 80: Blueprint author agent missing output path — wrote to docs/ instead of blueprint/; also fixed stale blueprint.md reference in git_repo_agent
- Bug 81: No env-existence guard in run_quality_gate / run_pytest — missing conda env silently treated as quality/test failure
- Bug 82: Toolchain defaults schema drift — missing linter.unused_exports and Gate C unused_exports check
- Bug 84: Lessons learned not injected into Stage 2 or Stage 3 agent task prompts (dead code functions never called)
- Bug 85: Carry-forward regression tests break when SVP N+1 reorganizes modules — added adapt_regression_tests.py with JSON import mapping
- Gate 5.3 routing path (Bug 67)
- gate_2_3 RETRY BLUEPRINT routing loop (Bug 66)
- gate_6_3 RECLASSIFY BUG dispatch (Bug 69)
- Fix ladder routing at sub_stage=None (Bug 70)
- TESTS_ERROR infinite loop (Bug 70)
- Stale blueprints/ directory removed (Bug 59)
- All 11 unit test failures from code modernization (Bug 64)

### Changed

- Spec sections 3.18-3.22 added (downstream dependency invariant, contract granularity, review enforcement, structural completeness)
- Pattern catalog expanded: P10 (Error-Path Contract Omission), P11 (Structural Completeness Gap), P12 (Test Target Mismatch)
- Pre-green-run test import switch requirement: tests must target real scripts before green run (Bug 74)
- Structural check expanded from 4 to 5 checks (Bug 74: stub import detection)
- Blueprint checker and reviewer checklists: added regression test target verification (Bug 74)
- rollback_to_unit: delete instead of copy-to-backup (Bug 55)
- Setup agent dialog expanded from five areas to six areas (Area 6: agent model configuration)
- Profile schema gains `pipeline.agent_models`, `vcs.github`, `readme.mode`, and `readme.existing_path` fields
- Bug count: 88 total bugs cataloged across SVP 1.0 through 2.1.1
- Spec version: v8.31 -> v8.33

## [2.1.0] - 2026-03-16

### Added

- **Pipeline Quality Gates (A, B, C)**: Mandatory deterministic quality checkpoints at post-test generation (Gate A), post-implementation (Gate B), and Stage 5 assembly (Gate C). Gate composition is data-driven from `toolchain.json`.
- **Delivered Quality Configuration**: `project_profile.json` gains a `quality` section (linter, formatter, type_checker, import_sorter, line_length). The git repo agent generates corresponding configuration in `pyproject.toml`.
- **Changelog Support**: `vcs.changelog` field in profile. Generates `CHANGELOG.md` in Keep a Changelog or Conventional Changelog format.
- **Blueprint Prose/Contracts Split**: Blueprint is now two files (`blueprint_prose.md` + `blueprint_contracts.md`). Enables token-efficient context loading for test and implementation agents.
- **Stub Sentinel**: `__SVP_STUB__ = True` marker in all generated stub files. Presence in delivered Python source is a structural validation failure.
- **Proactive Lessons Learned**: Test agent receives filtered historical failure patterns relevant to the current unit.
- **`delivered_repo_path`**: Recorded in `pipeline_state.json` at Stage 5 completion. Used by post-delivery debug loop.
- **`ruff.toml`**: Copied to project root at creation, permanently read-only.
- **`svp restore` subcommand**: Restore a project from backed-up documents.
- **Quality packages in Pre-Stage-3**: `ruff` and `mypy` installed alongside `pytest` and `pytest-cov`.
- **Repo collision avoidance**: Existing repo directory renamed to timestamped backup before new assembly.
- **Two-branch routing invariant**: Applied universally to all agent-to-gate and agent-to-command sub-stage transitions.
- **Gate ID consistency invariant**: `ALL_GATE_IDS` synchronized with `GATE_VOCABULARY` across preparation and routing modules.
- **Stage 2 alignment check sub-stage**: `alignment_check` added as explicit sub-stage after `blueprint_dialog`.
- **`stub_generation` sub-stage**: Added as step 1 in the per-unit cycle.
- **Coverage review auto-format**: Auto-formatting of newly added coverage test files within coverage_review completion flow.
- **`/svp:status` quality line**: One-line quality gate status in status output.
- **`PostToolUse` stub sentinel hook**: Shell script that checks for `__SVP_STUB__` in written files and exits 2 if found.

### Changed

- **Setup agent dialog**: Area 5 (delivered quality preferences) added. Area 1 gains changelog question. Four UX behavioral rules (plain-language, recommendation, defaults, progressive disclosure) now verbatim requirements.
- **Blueprint checker**: Validates quality profile preferences (Layer 2). Receives pattern catalog section of lessons learned document.
- **Blueprint extractor**: Accepts `include_tier1` parameter. Supports directory-based blueprint discovery.
- **`svp` CLI**: Exact three subcommands — `svp new`, bare `svp` (auto-detect resume), `svp restore`. No `svp resume`.
- **Launcher pre-flight**: Eight ordered checks with specific diagnostic messages and remediation guidance.
- **Session launch**: Via `subprocess.run` with `cwd`, `SVP_PLUGIN_ACTIVE` env variable, restart-signal loop.
- **Profile schema**: Gains `quality` section and `vcs.changelog` field. Canonical naming invariant enforced.
- **Toolchain schema**: Gains `quality` section with gate composition lists and quality package names.
- **`dispatch_agent_status`**: All main-pipeline agents must advance state; no-op `return state` invalid.
- **`dispatch_command_status`**: `test_execution` must advance `red_run`→`implementation` and `green_run`→`coverage_review`.
- **`unit_completion` action**: COMMAND must not embed `update_state.py`; state updates exclusively in POST.

### Fixed

- Bug 17: Hook configuration schema (type: "command", nested hooks array)
- Bug 21: Two-branch routing for Stage 0 sub-stages
- Bug 22: Canonical pipeline artifact filenames as shared constants
- Bug 23: Alignment check sub-stage wiring in Stage 2
- Bug 24: `total_units` derived from blueprint, not read from state
- Bug 25: Stage 3 routing: all sub-stages have explicit branches
- Bug 26: Stage 5 routing: full sub-stage flow implemented
- Bug 28: Commit structure validated: one commit per prescribed step
- Bug 29: Tests pass in delivered repository layout, not just workspace
- Bug 30: README carry-forward: content preserved and extended
- Bug 31: Launcher removes `--project-dir` flag (no such Claude Code CLI flag)
- Bug 32: CLI subcommand vocabulary fixed (no `svp resume`)
- Bug 33: Quality gate operation names qualified with `"quality."` prefix
- Bug 34: `run_prefix` has no version-specific flags
- Bug 35: Routing output fully resolved (no unresolved placeholders)
- Bug 36: Stub generation as routing sub-stage before test generation
- Bug 37: Delivered repo created as sibling directory, not inside workspace
- Bug 38: Group B command definitions include complete action cycle
- Bug 39: Orchestration skill includes slash-command-initiated action cycle guidance
- Bug 41: Stage 1 two-branch routing + gate ID consistency (gate_1_1, gate_1_2 registered)
- Bug 42: Pre-Stage-3 state persistence after alignment confirmation
- Bug 43: Universal two-branch routing compliance (all entries in exhaustive list)
- Bug 44: `dispatch_agent_status` for `test_agent` handles `sub_stage=None`
- Bug 45: `dispatch_command_status` for `test_execution` advances state
- Bug 46: `dispatch_agent_status` for `coverage_review` advances to `unit_completion`
- Bug 47: `unit_completion` COMMAND/POST separation (no double dispatch)
- Bug 48: Launcher CLI contract loss — restored `svp new`, bare `svp`, `svp restore` three-mode vocabulary
- Bug 49: Systemic bare argparse stubs — CLI argument enumeration enforced across 5 units
- Bug 50: Insufficient contract specificity — boundary violations in blueprint Tier 2/3
- Bug 51: Debug loop missing reassembly routing after repair completion
- Bug 52: Wired `version_document()` into `dispatch_gate_response` REVISE branches — document version tracking (spec Section 23) was non-functional
- Bug 53: Removed orphaned dead-code functions (`reset_fix_ladder`, `reset_alignment_iteration`, `record_pass_end`)
- Bug 54: Removed orphaned hollow function `update_state_from_status` — blueprint-specified entry point that was never implemented or called; `update_state_main` → `dispatch_status` is the actual dispatch path
- Bug 55: Wired `rollback_to_unit` into Gate 6.2 FIX UNIT dispatch — corrected spec's incorrect "verified_units not modified" to invalidate-and-rebuild semantics; fixed build_env fast path; added triage_result.json structured output; added phase-based Stage 5 debug routing; changed rollback from copy-to-backup to delete
- Bug 56: Added Downstream Dependency Invariant (Section 3.18), Contract Granularity Rules (Section 3.19), Gate C unused exported function detection, Gate 5.3 human gate for unused function findings
- Bug 57: Baked mandatory review checklists into stakeholder reviewer, blueprint reviewer, and blueprint checker agent definitions
- Bug 58: Added Gate 5.3 (`gate_5_3_unused_functions`) to GATE_VOCABULARY, ALL_GATE_IDS, and dispatch_gate_response; comprehensive summary document update (21 gaps)

## [2.0.0] - 2025-12-01

### Added

- Project Profile (`project_profile.json`): Socratic dialog captures delivery preferences.
- Pipeline Toolchain Abstraction (`toolchain.json`): Build commands externalized from scripts.
- Profile-driven Stage 5 delivery: README, source layout, dependency format, entry points.
- Delivery compliance scan (Layer 3 of preference enforcement).
- `/svp:redo profile_delivery` and `/svp:redo profile_blueprint` classifications.
- Blueprint author and checker receive profile for preference validation.

## [1.2.1] - 2025-10-15

### Fixed

- Miscellaneous bug fixes and robustness improvements.

## [1.2.0] - 2025-09-01

### Fixed

- Gate status string vocabulary (Bug 1).
- Hook permission reset after debug session entry (Bug 2).

## [1.1.0] - 2025-07-15

### Added

- Gate 6: Post-delivery debug loop.
- `/svp:bug` command: triage and repair agent workflows.

## [1.0.0] - 2025-06-01

### Added

- Initial release. Six-stage pipeline with deterministic state management.
- Multi-agent cross-checking (separate test and implementation agents).
- Human decision gates at every critical point.
- Stateless agents with ledger-based multi-turn conversations.

[Unreleased]: https://github.com/wilya7/svp/compare/v2.1.1...HEAD
[2.1.1]: https://github.com/wilya7/svp/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/wilya7/svp/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/wilya7/svp/compare/v1.2.1...v2.0.0
[1.2.1]: https://github.com/wilya7/svp/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/wilya7/svp/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/wilya7/svp/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/wilya7/svp/releases/tag/v1.0.0
