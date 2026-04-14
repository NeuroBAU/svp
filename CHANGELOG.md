# Changelog

All notable changes to SVP are documented in this file.

The format follows [Conventional Changelog](https://www.conventionalcommits.org/) conventions.

---

## [2.2.2] - 2026-04-14

### fix: Bug S3-123 — project-scoped plugin activation

SVP now writes `<project_root>/.claude/settings.json` during `svp new`, `svp resume`, `svp restore`, and during oracle nested session bootstrap, so the plugin loads only in directories where an SVP pipeline is active. Previously, SVP relied on user-scope enablement (`~/.claude/settings.json`), which caused `/svp:*` commands and all 21 SVP agents to appear in every Claude Code session on the machine regardless of cwd.

- Added `ensure_project_settings(project_root, plugin_root)` to Unit 29 (launcher). Idempotent, non-destructive, self-healing, corrupt-JSON-recoverable, atomic write.
- Wired into all four entry points: `svp_launcher.py main()` for `new`/`resume`/`restore`, and `_bootstrap_oracle_nested_session` in the routing module.
- Added Section 4.4 "Plugin Loading Architecture and Project-Scoped Activation" to the stakeholder spec — documents the Claude Code enablement model, the helper's contract, and the common-mistakes checklist. Closes the upstream cause (no written platform contract for plugin loading).
- 23-test regression suite in `tests/regressions/test_bug_s3_123_project_settings.py` covering correctness, idempotency, self-heal, preservation of unrelated keys, corrupt-JSON recovery, atomic write, AST checks that all four call sites exist, and an integration fixture.

**Migration (opt-in for existing users):** see the "Migration" section in README.md. Users with user-scope SVP keep working unchanged; to opt in, run `claude plugin uninstall svp@svp --scope user` and then run `svp` (or `svp new`/`svp restore`) in each pipeline directory to trigger the helper.

Credit: cross-project advisory from `debrief` BUG-AUDIT-8 (third in a series: S3-121, S3-122, S3-123) with reference implementation.

---

## [2.2.1] - 2026-04-07

### fix: Bugs S3-100 to S3-103

- **S3-100:** `run_tests_main` read wrong toolchain keys (`test.command` instead of `testing.run_command`), causing all Stage 3 test execution to return TESTS_ERROR
- **S3-101:** `helper-svp.R` used wrong path resolution (`file.path("R", ...)` instead of `testthat::test_path()` navigation)
- **S3-102:** Oracle task prompt embedded only test project path, not artifact contents
- **S3-103:** Sync protocol redesign (see below)

### refactor: sync protocol redesign (Bug S3-103)

- Workspace is single source of truth; repo is derived artifact
- `sync_workspace.sh` performs one-way sync (workspace → repo) with safety warnings if repo files are newer
- Removed bidirectional mtime-based sync logic
- Repo paths stored in `.svp/sync_config.json` (portable, written by `restore_project()`)
- `restore_project()` auto-discovers artifacts from repo's `docs/` directory
- All agent definition units (17-27) added to `derive_scripts_from_stubs.py` derivation map

### refactor: repo docs consolidation

- All documentation consolidated into `docs/` — eliminated `specs/`, `blueprint/`, `references/` at repo root
- `CLAUDE.md` and `project_context.md` moved from repo root to `docs/` (restore-only artifacts)
- Root `blueprint_contracts.md` stray copy removed

### refactor: test import standardization

- All 46 test files converted from stub imports (`from src.unit_N.stub import ...`) to flat module imports (`from module_name import ...`)
- Spec rule P3 and TEST_AGENT_DEFINITION updated to mandate flat module imports
- Tests now work identically whether run from workspace or delivered repo

---

## [2.2.0] - 2026-03-26

### feat: multi-language support via language provider framework

- Add `language_registry.py` with full Python and R language entries and Stan as a component language
- Add `profile_schema.py` with language-keyed profile sections (`delivery.python.*`, `quality.python.*`, `delivery.r.*`, `quality.r.*`) and auto-migration from SVP 2.1 flat format
- Add `toolchain_reader.py` enforcing three-layer toolchain separation (pipeline / build-time / delivery)
- Add six per-language dispatch tables: `SIGNATURE_PARSERS`, `STUB_GENERATORS`, `TEST_OUTPUT_PARSERS`, `QUALITY_RUNNERS`, `PROJECT_ASSEMBLERS`, `COMPLIANCE_SCANNERS`

### feat: archetype system with Options A-F in setup agent

- Add setup agent Area 0 with archetypes: Python (A), R (B), Claude Code plugin (C), mixed-language (D), SVP language extension self-build (E), SVP architectural self-build (F)
- Add mixed-language dialog flow (3-4 questions) with hard constraint enforcement (both languages forced to conda + environment.yml)
- Add plugin interview (4 questions: external services, auth, hook events, skills)
- Add Options E/F auto-population from SVP context

### feat: oracle agent for systematic post-delivery analysis

- Add oracle agent with four-phase protocol: dry_run -> gate_a -> green_run -> gate_b -> exit
- Add `/svp:oracle` slash command with test project selection UX
- Add oracle session state fields in `pipeline_state.py`: `oracle_session_active`, `oracle_phase`, `oracle_run_count`, `oracle_nested_session_path`
- Add oracle phase routing dispatch in `routing.py`

### feat: Pass 1 / Pass 2 bootstrap protocol for SVP self-builds

- Add `enter_pass_1`, `enter_pass_2`, `clear_pass` state transitions in `state_transitions.py`
- Add `pass`, `pass2_nested_session_path` fields to PipelineState
- Add break_glass action type in routing for E/F exhaustion conditions
- Add Hard Stop Protocol reference in orchestration skill and hook enforcement

### feat: assembly map generation and regression test adaptation

- Add `generate_assembly_map.py` for bidirectional workspace-to-repo path mapping
- Add `adapt_regression_tests.py` for import rewriting in carry-forward regression tests
- Add `regression_test_import_map.json` for module rename tracking across SVP versions

### feat: structural validation and dispatch exhaustiveness

- Add `structural_check.py` with four AST-based checks (dict keys never dispatched, enum values never matched, exported functions never called, string dispatch gaps)
- Add `validate_dispatch_exhaustiveness()` for cross-dispatch-table coverage validation
- Add `COMPLIANCE_SCANNERS` dispatch table (sixth per-language dispatch table)

### feat: plugin manifest and marketplace catalog

- Add `plugin.json` manifest with all 12 required fields
- Add `marketplace.json` catalog entry
- Add cross-reference integrity checking (skills-agents, MCP-hooks, commands-manifest)

### feat: deferred broken units and spec revision tracking

- Add `deferred_broken_units`, `mark_unit_deferred_broken`, `resolve_deferred_broken` to pipeline state and transitions
- Add `spec_revision_count` field to PipelineState
- Add `state_hash` (SHA-256 chain validation) to save_state

### feat: new slash commands

- Add `/svp:oracle` command for oracle agent invocation
- Add `/svp:visual-verify` command for visual verification utility

### feat: bundled example projects

- Add `examples/game-of-life/` (Python GoL)
- Add `examples/gol-r/` (R GoL)
- Add `examples/gol-plugin/` (Claude Code plugin GoL)
- Add `examples/gol-python-r/` (mixed Python-R GoL)
- Add `examples/gol-r-python/` (mixed R-Python GoL)

### feat: delivery quality templates

- Add `svp/scripts/delivery_quality_templates/python/` with ruff, flake8, mypy, and black templates
- Add `svp/scripts/delivery_quality_templates/r/` with lintr and styler templates

### build: upgrade from 22 units (SVP 2.1.1) to 29 units

- Unit 1: Core Configuration (enhanced with model precedence)
- Unit 2: Language Registry (new - LANGUAGE_REGISTRY with Python, R, Stan entries)
- Unit 3: Profile Schema (new - language-keyed profile with auto-migration)
- Unit 4: Toolchain Reader (new - three-layer separation enforcement)
- Units 5-16: Ported from SVP 2.1.1 with language-aware updates
- Units 17-26: Updated agent definitions for multi-language awareness
- Unit 27: Project Templates (new - toolchain defaults + delivery quality templates)
- Unit 28: Plugin Manifest + Structural Validation + Compliance Scan (new)
- Unit 29: Launcher (new - three CLI modes: new / resume / restore)

---

## [2.1.1] - 2026-01-15

### feat: unit-level preference capture (RFC-2, Rules P1-P4)

- Blueprint author captures domain preferences at unit level during Stage 2
- Preferences stored as `### Preferences` subsection in `blueprint_prose.md`
- Blueprint checker validates preference-contract consistency

### feat: structural completeness checking

- Add `structural_check.py` with project-agnostic AST scanner
- 14 automated declaration-vs-usage techniques
- 163 structural tests (Bugs 71-72)

### feat: configurable agent models

- Add `pipeline.agent_models` in `project_profile.json` for per-agent model selection
- Model precedence: profile > svp_config.json > default

### feat: GitHub repository configuration

- Add `vcs.github` in profile with modes: new, existing_force, existing_branch, none

### feat: README mode

- Add `readme.mode` in profile: generate or update existing README

### fix: 39 bug fixes (Bugs 52-91)

- Full Stage 3 error handling
- Stage 4 failure paths
- Debug loop gates
- Selective blueprint loading
- Routing dispatch loops (Bug 73)
- Test target invariant (Bug 74)
- Regression test import adaptation (Bug 85)

---

## [2.1.0] - 2025-10-01

### feat: pipeline quality gates A, B, C

- Gate A: post-test-generation ruff format + light lint
- Gate B: post-implementation ruff format + heavy lint + mypy
- Gate C: Stage 5 assembly full ruff + mypy + cross-unit check

### feat: delivered quality configuration

- `project_profile.json` quality section drives delivered `pyproject.toml`

### feat: blueprint prose/contracts split

- `blueprint_prose.md` (Tier 1 descriptions) and `blueprint_contracts.md` (Tier 2/3 contracts)
- Token-efficient selective loading per agent

### fix: 51 bug fixes (Bugs 17-58)

---

## [2.0.0] - 2025-07-01

### feat: project profile

- `project_profile.json` captures delivery preferences via setup agent Socratic dialog

### feat: pipeline toolchain abstraction

- `toolchain.json` externalizes all pipeline build commands

---

## [1.2.1] - 2025-05-01

### fix: robustness improvements

---

## [1.2.0] - 2025-04-01

### fix: Bug 1 (gate status string vocabulary), Bug 2 (hook permission reset after debug session)

---

## [1.1.0] - 2025-03-01

### feat: post-delivery debug loop

- Gate 6 (post-delivery)
- `/svp:bug` command
- Triage and repair agent workflows

---

## [1.0.0] - 2025-01-01

### feat: initial release

- Six-stage pipeline: Setup, Stakeholder Spec, Blueprint, Unit Verification, Integration Testing, Repository Delivery
- Deterministic routing engine
- Multi-agent cross-checking (test agent, implementation agent, coverage review)
- Human decision gates
- Claude Code plugin with hooks, agents, skills, and slash commands
