# SVP 2.1 — Specification Summary and Glossary

**Date:** 2026-03-15
**Companion to:** Stakeholder Specification v8.29 (Document 2)
**Pipeline role:** Reference document. Available to blueprint checker as cross-check.
**Bug count:** 59 bugs cataloged across SVP 1.0 through SVP 2.1 (see `svp_2_1_lessons_learned.md`).

---

## Part 1: Behavioral Contract Summary

Each line is a verifiable contract. Section numbers reference Document 2.

### Pipeline Structure (§5)

- Six stages (0-5) plus one transitional phase (Pre-Stage-3), for a total of seven sequential phases.
- Each stage completes before the next begins.
- Document-level problems trigger ruthless restart from the appropriate stage.
- Post-Stage-5 re-entry via /svp:bug for debug loop.

### Stage 0: Setup (§6)

- Sub-stages: hook_activation → project_context → project_profile.
- **Launcher CLI:** Three modes: `svp new <name>` (create), bare `svp` (auto-detect resume), `svp restore <name> --spec --blueprint-dir --context --scripts-source --profile` (restore from backed-up documents; `--blueprint-dir` points to directory containing both `blueprint_prose.md` and `blueprint_contracts.md`; `--profile` points to a valid `project_profile.json`). Restore requires a valid profile before Pre-Stage-3 begins.
- **Launcher pre-flight checks (ordered, fail-fast):** (1) Claude Code installed, (2) SVP plugin found, (3) API credentials valid, (4) Conda installed, (5) Python >= 3.11, (6) pytest available, (7) Git installed, (8) network access. Each failure prints specific diagnostic with remediation.
- **Launcher new-project sequence:** creates directory structure, copies scripts/toolchain.json/ruff.toml/regression tests/hooks, writes pipeline_state.json + svp_config.json + CLAUDE.md, sets permissions, launches Claude Code.
- **Launcher session launch:** `subprocess.run` with `cwd=str(project_root)` (no `--project-dir` flag -- Bug 31 fix). `SVP_PLUGIN_ACTIVE=1` set in subprocess env only (never in launcher process). `--dangerously-skip-permissions` if `skip_permissions` is true. `--prompt "run the routing script"`. Restart signal loop: launcher checks for `.svp/restart_signal` after each session, relaunches if present.
- ruff.toml copied to project root and set read-only immediately. Permanently read-only thereafter.
- Hook activation requires human review via /hooks menu.
- Setup agent creates project_context.md through Socratic dialog.
- Setup agent creates project_profile.json through five-area dialog.
- **Setup agent UX rules (§6.4):** Four behavioral requirements for all five dialog areas: (1) plain-language explanations for every choice -- no jargon without definition, (2) best-option recommendation for every choice -- clearly marked, (3) sensible defaults that always produce a correct project, (4) progressive disclosure -- lead with recommendation, details only on request. Area-level fast path: one accept/decline per area.
- **Two-branch routing invariant (§3.6):** Applies universally to every sub-stage with an agent-to-gate or agent-to-command transition across all stages. route() checks last_status.txt to distinguish "agent not yet done" (invoke agent) from "agent done" (present gate or run command). Without this check, routing loops indefinitely. Structural invariant, not a per-stage fix (generalized Bug 21 fix). Must be applied universally in a single implementation pass, not incrementally as bugs are discovered (Bug 43 fix). Two sub-lists:
  - **Gate-presenting entries** (done branch emits human_gate): Stage 0 (project_context, project_profile), Stage 1 (stakeholder_spec_authoring), Stage 2 (blueprint_dialog, alignment_check), Stage 5, post-delivery debug loop (triage agent to Gate 6.2/6.4, repair agent to Gate 6.3, test agent in regression mode to Gate 6.1), redo profile sub-stages (redo_profile_delivery, redo_profile_blueprint).
  - **Command-presenting entries** (done branch emits run_command): Stage 3 quality_gate_a_retry (check for TEST_GENERATION_COMPLETE before re-running Gate A tools), Stage 3 quality_gate_b_retry (check for IMPLEMENTATION_COMPLETE before re-running Gate B tools), Stage 4 (check for INTEGRATION_TESTS_COMPLETE before running integration test suite).
- **Universal compliance requirement (§3.6, Bug 43 fix):** A single structural regression test (`test_bug43_stage2_blueprint_routing.py`) must verify that EVERY entry in the exhaustive two-branch list has a corresponding check in `route()`, and that every gate ID in `GATE_VOCABULARY` (routing) appears in `ALL_GATE_IDS` (preparation) with a handler, and vice versa. This is the definitive structural test for the two-branch invariant.
- **Gate ID consistency invariant (§3.6, Bug 41 fix):** Every gate ID in routing dispatch tables (GATE_RESPONSES) must also be in gate preparation registries (ALL_GATE_IDS), and vice versa. A structural test must verify the sets are identical. Prevents `ValueError: Unknown gate ID` when a gate is triggered but not registered in the preparation script.
- **Route-level state persistence invariant (§3.6, Bug 42 fix):** Any `route()` branch that performs an in-memory state transition (via `complete_*` or `advance_*`) and then recursively routes must persist state to disk via `save_state()` before returning the action block. Without this, `update_state.py` loads stale state from disk and overwrites the in-memory transition. Structural tests must verify every `complete_*`/`advance_*` call in `route()` is followed by `save_state()`.
- **Exhaustive dispatch_agent_status invariant (§3.6, Bug 42 fix, Bugs 44/46 fix):** Every main-pipeline agent type in `dispatch_agent_status` must explicitly advance pipeline state (modify stage, sub_stage, or a state flag). A bare `return state` is only valid for slash-command-initiated agents (help, hint). Structural tests must verify main-pipeline handlers are not no-ops. Routing and dispatch must have consistent null-handling for sub_stage (Bug 44).
- **Exhaustive dispatch_command_status invariant (§3.6, Bug 45 fix):** Every `dispatch_command_status` handler for `test_execution` must produce a state transition for the expected outcome at each sub_stage. No-op returns are invalid for `red_run` (TESTS_FAILED -> implementation) and `green_run` (TESTS_PASSED -> coverage_review).
- **COMMAND/POST separation invariant (§3.6, Bug 47 fix):** COMMAND fields must never embed state update calls (`update_state.py`). State updates are exclusively the responsibility of POST commands. Embedding updates in both causes double dispatch and TransitionError.
- **CLI argument enumeration invariant (§3.6, Bug 48 fix, STRENGTHENED Bug 49 fix):** Any blueprint Tier 2 function signature that accepts `argv` and uses `argparse` internally must enumerate every `add_argument` call (argument name, type, required/optional) in the Tier 2 invariants section. Prose-only descriptions in Tier 3 are insufficient for CLI contracts. This invariant applies to ALL units with CLI entry points: Unit 6 (`main`), Unit 7 (`main`), Unit 9 (`main`), Unit 10 (`update_state_main`, `run_tests_main`, `run_quality_gate_main`), Unit 23 (`compliance_scan_main`), Unit 24 (`parse_args`). A structural regression test (`test_bug49_argparse_enumeration.py`) verifies compliance.
- **Contract sufficiency invariant (§3.16, Bug 50 fix):** A Tier 3 behavioral contract is sufficient if and only if an implementation agent reading ONLY the Tier 2 signature and Tier 3 contract could produce a correct implementation. If behavior depends on specific values (lookup tables, enum validation sets, magic numbers, algorithm parameters, file paths for side effects), those values must appear in Tier 2 invariants or Tier 3 contract.
- **Contract boundary rule (§3.16, Bug 50 fix):** The blueprint MUST NOT include internal helper function signatures in Tier 2. Internal helpers (underscore-prefixed, not imported cross-unit, replaceable without affecting tests) belong in implementation, not contracts. Observable behavioral details (lookup table values, validation sets, algorithm parameters) MUST appear in Tier 3 contracts.
- **Downstream Dependency Invariant (§3.18, Bug 56 fix):** If unit N’s implementation changes during any re-entry path (FIX UNIT, FIX BLUEPRINT, FIX SPEC), all units >= N must be invalidated and rebuilt. Units generated and verified against unit N’s original implementation are potentially stale. This applies to every re-entry path, not just FIX UNIT.
- **Contract Granularity Rules (§3.19, Bug 56 fix):** Three mandatory rules: (1) Every Tier 2 function must have a Tier 3 behavioral contract. (2) Every gate response option must have a per-gate-option dispatch contract specifying the exact state transition and next routing action. (3) Every transition function must have a documented call site — at least one place in the codebase where it is invoked. The blueprint checker verifies all three rules.
- **Review Enforcement — Baked Checklists (§3.20, Bug 57 fix):** Mandatory review checklists are baked directly into the agent definitions for the stakeholder reviewer, blueprint checker, and blueprint reviewer. Each checklist requires explicit verification of downstream dependency analysis, Tier 3 contract coverage, per-gate-option dispatch contracts, call-site traceability, and re-entry path invalidation. Two-tier defense model: LLM-driven review catches root causes at authoring time (Bug 57); Gate C deterministic check catches symptoms at assembly time (Bug 56).
- **Profile canonical naming invariant (§6.4):** Schema defines exact canonical section/field names. `DEFAULT_PROFILE`, setup agent output, and all consumers must use identical names. Mismatches (e.g., `licensing` vs `license`, `readme.target_audience` vs `readme.audience`) cause silent merge conflicts in `_deep_merge`.
- **Document versioning (§23):** Before any spec or blueprint revision (REVISE response at Gates 1.1, 1.2, 2.1, 2.2), the current document is archived to `docs/history/` via `version_document(project_root, doc_path, trigger_context)`. Archive filename includes incrementing version number and trigger context. Diff summary appended to archive. History directory created on first use. `dispatch_gate_response` calls `version_document` / `_version_spec` / `_version_blueprint` before invoking `restart_from_stage` on all REVISE/FIX branches (Bug 52 fix).
- Profile is immutable after Gate 0.3. Changes via /svp:redo only.
- toolchain.json is permanently read-only.
- ruff.toml is permanently read-only.

### Stage 1: Stakeholder Spec (§7)

- Sub-stage flow (Bug 41 fix): `stakeholder_spec_authoring (sub_stage=None)` -> `[SPEC_DRAFT_COMPLETE/SPEC_REVISION_COMPLETE]` -> Gate 1.1 -> APPROVE (advance to Stage 2) / REVISE (re-invoke dialog) / FRESH REVIEW (invoke reviewer -> Gate 1.2).
- Stage 1 uses `sub_stage: None` throughout; the two-branch routing invariant uses `last_status.txt` for the routing branch.
- Socratic dialog via ledger-based multi-turn.
- One question at a time, consensus before advancing.
- Reference documents indexed on ingestion, summaries available to agents.
- Draft-review-approve cycle: APPROVE, REVISE, FRESH REVIEW.
- **Two-branch routing (§7.4):** When last_status.txt contains SPEC_DRAFT_COMPLETE or SPEC_REVISION_COMPLETE, route() must emit human_gate for gate_1_1_spec_draft, not re-invoke the stakeholder dialog agent. When last_status.txt contains REVIEW_COMPLETE (from spec reviewer), route() must emit human_gate for gate_1_2_spec_post_review (not gate_1_1). Same pattern applies in Stage 2 for blueprint reviewer's REVIEW_COMPLETE routing to Gate 2.2. Governed by the universal two-branch routing invariant (§3.6). Regression test: `test_bug23_stage1_spec_gate_routing.py` (Bug 41 fix).
- **Gate ID consistency (§3.6):** `gate_1_1_spec_draft` and `gate_1_2_spec_post_review` must be registered in both `GATE_RESPONSES` (routing) and `ALL_GATE_IDS` (preparation). Structural test verifies registry synchronization.
- Completion marker appended to approved spec.
- Canonical filename: `stakeholder_spec.md`. Defined as shared constant; both setup agent (writer) and prepare script (reader) must reference the same constant (Bug 22 fix).
- Revision modes: working notes (during blueprint dialog), targeted revision, full restart.

### Stage 2: Blueprint (§8)

- Blueprint author receives profile (readme, vcs, delivery, quality sections).
- Three-tier unit format: description, machine-readable signatures, contracts.
- Backward-only dependency invariant enforced by checker (DAG validation).
- Blueprint checker validates: signatures parseable, types imported, context budget, DAG acyclicity, profile preference coverage (Layer 2).
- **Two-branch routing for blueprint_dialog (§8.1):** When last_status.txt contains BLUEPRINT_DRAFT_COMPLETE or BLUEPRINT_REVISION_COMPLETE, route() must emit human_gate for gate_2_1_blueprint_approval, not re-invoke the blueprint author agent. Governed by the universal two-branch routing invariant (§3.6).
- Sub-stages: blueprint_dialog → alignment_check (Bug 23 fix). After Gate 2.1 APPROVE, routing must transition to alignment_check sub-stage and invoke blueprint checker -- not advance directly to Pre-Stage-3. On ALIGNMENT_CONFIRMED, present Gate 2.2 (the human always decides when to advance to Pre-Stage-3). On Gate 2.2 APPROVE, advance to Pre-Stage-3. On ALIGNMENT_FAILED, present appropriate gate. The Gate 2.2 APPROVE transition to Pre-Stage-3 must persist state to disk before returning the Pre-Stage-3 action block (route-level state persistence invariant, Bug 42 fix). `dispatch_agent_status` for `reference_indexing` must advance from `pre_stage_3` to stage 3 (exhaustive dispatch invariant, Bug 42 fix).
- Blueprint author produces two files: `blueprint_prose.md` and `blueprint_contracts.md`. Both submitted at every gate. Checker receives both and validates internal consistency (no unit present in one file but absent from the other).
- **Selective blueprint loading (Bugs 60-62 fix, now implemented):** Per Section 3.16 agent matrix, Unit 9 exports `load_blueprint_contracts_only()` and `load_blueprint_prose_only()` for per-agent loading. `test_agent` and `implementation_agent` receive contracts-only via `build_unit_context(include_tier1=False)`. `integration_test_author` and `git_repo_agent` use `load_blueprint_contracts_only()`. `help_agent` uses `load_blueprint_prose_only()`. `blueprint_checker`, `blueprint_reviewer`, `hint_agent`, and `bug_triage` receive both files. Internal `_get_unit_context` resolves blueprint directory via `get_blueprint_dir()` (Bug 60 fix) and passes `include_tier1` through (Bug 61 fix).
- Checker receives pattern catalog from `svp_2_1_lessons_learned.md`. The preparation script extracts Part 2 of the lessons learned document verbatim and includes it in the checker's task prompt. Produces advisory risk section identifying structural features matching known failure patterns (P1-P9). Does not block approval.
- Alignment loop: configurable iteration limit (default 3).

### Pre-Stage-3: Infrastructure (§9)

- Extract imports from all blueprint signature blocks.
- Install: extracted packages + testing.framework_packages + quality.packages.
- Validate all imports resolve in conda environment.
- Re-validate DAG before creating directories.
- Derive total_units from blueprint extraction (count of units), not from state (Bug 24 fix). Infrastructure setup is the producer of total_units, not a consumer. Validate as positive integer before use; dict.get() does not guard against explicit null.

### Stage 3: Unit Verification (§10)

Per-unit cycle (11 steps, Bug 36 fix adds stub generation):
1. Stub generation: deterministic script generates stub from blueprint Tier 2 signatures.
2. Prepare test agent task prompt.
3. Test agent generates tests.
4. Quality Gate A: format + light lint (E, F, I rules). No type check on tests.
5. Red run: all tests must fail against stub.
6. Prepare implementation agent task prompt.
7. Implementation agent writes code.
8. Quality Gate B: format + heavy lint + mypy (--ignore-missing-imports).
9. Green run: all tests must pass.
10. Coverage review: newly added test code receives auto-formatting (ruff format + light lint auto-fix, same as Gate A auto-fix subset) before red-green validation. No full gate cycle, no agent re-pass, no type check.
11. Unit completion: marker written, sub_stage/fix_ladder/retries reset.

- Quality gates: auto-fix first, 1 agent re-pass if residuals, then fix ladder.
- Quality gate retry budget separate from fix ladder budget.
- Stub generator strips module-level asserts, refuses forward references.
- Red run retries tracked, default limit 3.
- Test validation gate: TEST CORRECT or TEST WRONG.
- Implementation fix ladder: fresh_impl → diagnostic → diagnostic_impl → exhausted.
- Three-hypothesis discipline: implementation, blueprint, or spec level.
- Context isolation: each unit sees only its definition + upstream contracts.
- Test agent and implementation agent receive `blueprint_contracts.md` only (`include_tier1=False`). Tier 1 prose excluded from these task prompts to reduce token cost.
- Test agent task prompt includes filtered lessons learned entries for the current unit (unit number match or pattern classification match). Filtering is deterministic in Unit 9. Section omitted when no matches.
- Stub generator writes `__SVP_STUB__ = True` sentinel as first non-import statement in every stub file.
- Routing script must emit a distinct action for each Stage 3 sub-stage (Bug 25 fix, updated for Bug 36): `None`/`stub_generation` → stub generator `run_command`, `test_generation` → test_agent, `red_run` → pytest (expect fail), `implementation` → implementation_agent, `green_run` → pytest (expect pass), `coverage_review` → coverage_review agent, `unit_completion` → complete_unit + session_boundary.

### Stage 4: Integration Testing (§11)

- **Two-branch routing (§3.6, §11.1):** When last_status.txt contains INTEGRATION_TESTS_COMPLETE, route() must emit run_command to execute the integration test suite, not re-invoke the integration test author agent. This is a command-presenting entry per the universal two-branch routing invariant (§3.6).
- **Three-state post-execution dispatch (§11.2.1, §22.4):** After the integration test `run_command` completes, routing performs three-state dispatch: (1) tests passed (TESTS_PASSED) → advance to Stage 5; (2) tests failed (TESTS_FAILED) → present diagnostic gate (§11.4, Gate 4.1); (3) assembly fix ladder exhausted (retries >= 3) → present Gate 4.2. The two-branch routing invariant governs the transition *before* the integration test command runs (agent done vs. not done). The three-state dispatch governs the transition *after* the integration test command completes (pass vs. fail vs. exhausted). These are sequential, independent dispatch points.
- Tests cover cross-unit interactions, data flow, error propagation.
- At least one end-to-end domain-meaningful test.
- Must cover all SVP 2.0/2.1 cross-unit paths (11 specific coverage items).
- Failure: three-hypothesis with inverted prior (blueprint-level likely).
- Assembly fix ladder: 3 attempts, then Gate 4.2.

### Stage 5: Repository Delivery (§12)

- Sub-stages (Bug 26 fix): `None` (initial entry) → `repo_test` → `compliance_scan` → `repo_complete`.
- **Two-branch routing (§12.1, Bug 43 fix):** When last_status.txt contains REPO_ASSEMBLY_COMPLETE, route() must emit human_gate for gate_5_1_repo_test, not re-invoke the git repo agent. Governed by the universal two-branch routing invariant (§3.6).
- Routing: `sub_stage=None` invokes git_repo_agent; `repo_test` presents gate_5_1 (or gate_5_2 if retries >= 3); `compliance_scan` runs compliance scan; `repo_complete` returns pipeline_complete.
- Git repo agent assembles repository with prescribed commit order.
- Assembly mapping: workspace src/unit_N/ → blueprint file tree paths.
- Environment name in delivered `environment.yml` and `README.md` must use canonical `derive_env_name()` from Unit 1, not independent derivation (Bug 27 fix).
- Quality Gate C: format check + full lint + full mypy (cross-unit, no --ignore-missing-imports). Includes unused exported function detection (`linter.unused_exports`); if unused functions are found, presents Gate 5.3 (Bug 56).
- Structural validation includes Gate C and compliance scan.
- Bounded fix cycle: 3 attempts, then Gate 5.2.
- Compliance scan (Layer 3): AST-based, subprocess calls only, delivery environment rules.
- README generated from profile (Mode A: carry-forward — previous version's README preserved in full, only new-version sections added; Mode B: from template, but if a reference README is provided, preserve and extend it).
- Source layout per delivery.source_layout.
- Dependency format per delivery.dependency_format.
- Delivered quality config per quality profile section.
- Changelog per vcs.changelog.
- Scan all delivered Python source files for `__SVP_STUB__` sentinel. Any match is an immediate structural validation failure identifying the offending file.
- Both `blueprint_prose.md` and `blueprint_contracts.md` present in `docs/`.
- All project documents delivered: docs/stakeholder_spec.md, docs/blueprint_prose.md, docs/blueprint_contracts.md, docs/project_context.md, docs/references/.
- Pipeline artifacts excluded: toolchain.json, project_profile.json, ruff.toml (workspace root), pipeline_state.json, svp_config.json.
- Mode A exception: plugin contains toolchain_defaults/ as blueprint-specified artifacts.
- Debug loop (7-step workflow): prompt human → investigate (three-hypothesis) → fix workspace then reassemble repo → evaluate spec/blueprint → write regression tests → update lessons learned → commit/push (human permission gate).
- **Triage result mechanism (Bug 55 fix):** Triage agent writes `.svp/triage_result.json` with `{affected_units: [N, ...]}`. Routing reads it via `_read_triage_affected_units()` when processing TRIAGE_COMPLETE status. `set_debug_classification(state, classification, affected_units)` records classification and affected_units on the debug session before presenting Gate 6.2.
- **build_env fast path (Bug 55 fix):** TRIAGE_COMPLETE: build_env routes directly to repair_agent, bypassing Gate 6.2. No classification gate needed for environment issues.
- **Phase-based Stage 5 debug routing (Bug 55 fix):** When debug_session is active, routing is governed by `debug_session.phase`: `triage_readonly` → `triage` (invoke triage agent) → `regression_test` (test agent in regression mode) → `stage3_reentry` (normal Stage 3 routing for rebuild) → `repair` (invoke repair agent) → `complete` (commit gate). Each phase has explicit routing logic in `route()`.
- **Two-branch routing for debug loop agents (§12.17.4, Bug 43 fix):** Triage agent to Gate 6.2 (check TRIAGE_COMPLETE: single_unit or TRIAGE_COMPLETE: cross_unit -- note: TRIAGE_COMPLETE: build_env routes to fast path, not Gate 6.2), triage agent to Gate 6.4 (check TRIAGE_NON_REPRODUCIBLE), repair agent to Gate 6.3 (check REPAIR_COMPLETE/REPAIR_RECLASSIFY), test agent to Gate 6.1 (check REGRESSION_TEST_COMPLETE). All governed by the universal two-branch routing invariant (§3.6). TRIAGE_NEEDS_REFINEMENT triggers bounded re-invocation of the triage agent (not governed by two-branch invariant). REPAIR_FAILED triggers bounded retry of the repair agent, presenting Gate 6.3 when retries are exhausted (not governed by two-branch invariant for the retry branch).
- Artifact synchronization invariant: every artifact with dual copies (workspace + delivered repo) must be kept in sync. Applies to Python source, command .md files, skill files, agent definitions, hooks, and documentation. Formal debug loop uses Stage 5 reassembly; direct fixes require manual propagation.
- Repo collision avoidance: if `projectname-repo/` already exists (e.g., from a previous pass before `/svp:redo`), it is renamed to `projectname-repo.bak.YYYYMMDD-HHMMSS` before creating the new repo. Rename performed by preparation script, not agent. `delivered_repo_path` always points to canonical `projectname-repo/`.
- Delivered repo created as sibling directory (`projectname-repo/` at same level as workspace, not inside it).
- Delivered repo path recorded in pipeline_state.json at Stage 5 completion. Triage agent receives path in task prompt.
- Debug commits use fixed format regardless of vcs.commit_style.

### Human Commands (§13)

- Group A (script): /svp:save, /svp:quit, /svp:status, /svp:clean.
- Group B (agent): /svp:help, /svp:hint, /svp:ref, /svp:redo, /svp:bug. Each command definition must include the complete action cycle: prepare, spawn agent, write status, run update_state.py with correct --phase, re-run routing. Phase values: help, hint, reference_indexing, redo, bug_triage.
- Prohibited: cmd_help.py, cmd_hint.py, cmd_ref.py, cmd_redo.py, cmd_bug.py.
- /svp:redo classifications: spec, blueprint, gate, profile_delivery, profile_blueprint. All classifications that cause re-entry to Stage 5 are subject to repo collision avoidance (§12.1): existing repo renamed to timestamped backup before new delivery.
- **Two-branch routing for redo profile sub-stages (§13, Bug 43 fix):** Both `redo_profile_delivery` and `redo_profile_blueprint` sub-stages: when last_status.txt contains PROFILE_COMPLETE, route() must emit human_gate for gate_0_3r_profile_revision, not re-invoke the setup agent. Governed by the universal two-branch routing invariant (§3.6).

### Quality Gates (§10.3, §10.6, §10.12, §12.2)

- Gate A: post-test, pre-red-run. Format + light lint (E, F, I). No mypy.
- Gate B: post-impl, pre-green-run. Format + heavy lint + mypy --ignore-missing-imports.
- Gate C: Stage 5 assembly. Format check + full lint + full mypy (cross-unit, no --ignore-missing-imports). All gate_c operations use `{target}` resolved to assembled project source directory (layout-dependent: `src/packagename/` for conventional, `packagename/` for flat, `src/` for SVP-native). `{flags}` resolves to empty string (type_checker.project_flags) -- absence of --ignore-missing-imports is intentional.
- All gates mandatory. No opt-out.
- Auto-fix first. 1 re-pass on residuals. Then fix ladder.
- Gate retry does NOT consume fix ladder retry.
- Gate composition data-driven from toolchain.json (gate_a, gate_b, gate_c lists).
- Gate operations are relative to quality section; caller prepends "quality." before resolve_command (Bug 33 fix).
- Placeholder for target path in quality templates is `{target}`, not `{path}` (Bug 33 fix).
- Quality tools modify files via subprocess, bypass hooks (correct by design).
- Toolchain run_prefix must not include version-specific flags (e.g., no `--no-banner` — Bug 34 fix).
- Routing output COMMAND field must be fully resolved — no `{env_name}` or other placeholders (Bug 35 fix).
- Launcher validates profile `python_version` against toolchain `language.version_constraint` during pre-flight checks (§6.1.3, §6.5).

### Write Authorization (§19)

- Layer 1: filesystem permissions (read-only between sessions).
- Layer 2: PreToolUse command hooks with exit code 2 provide hard enforcement against pipeline state.
- Infrastructure paths always writable: .svp/, pipeline_state.json, ledgers/, logs/.
- Artifact paths state-gated: src/, tests/, specs/, blueprint/, references/.
- project_profile.json: writable during project_profile sub-stage and redo profile sub-stages only.
- toolchain.json: permanently read-only.
- ruff.toml: permanently read-only.
- Debug writes: only after AUTHORIZE DEBUG at Gate 6.0. Includes delivered repo path, lessons learned document, and `.svp/triage_result.json` (authorized during triage phases, Bug 55 fix).
- Non-SVP sessions: bash tool blocked by hook.
- Dual write-path: agent writes go through hooks; quality tool/assembly subprocess writes bypass hooks (correct by design).

### Session Management (§16)

- Boundaries fire at every major transition.
- Mechanism: restart signal file → launcher detects → relaunch.
- Post-restart context summary: project, stage, what happened, what's next.

---

## Part 2: Gate Status Vocabulary

| Gate | ID | Valid Responses |
|---|---|---|
| 0.1 | gate_0_1_hook_activation | HOOKS ACTIVATED, HOOKS FAILED |
| 0.2 | gate_0_2_context_approval | CONTEXT APPROVED, CONTEXT REJECTED, CONTEXT NOT READY (holds at Gate 0.2, re-invokes setup agent for project context phase) |
| 0.3 | gate_0_3_profile_approval | PROFILE APPROVED, PROFILE REJECTED |
| 0.3r | gate_0_3r_profile_revision | PROFILE APPROVED, PROFILE REJECTED |
| 1.1 | gate_1_1_spec_draft | APPROVE, REVISE, FRESH REVIEW |
| 1.2 | gate_1_2_spec_post_review | APPROVE, REVISE, FRESH REVIEW |
| 2.1 | gate_2_1_blueprint_approval | APPROVE, REVISE, FRESH REVIEW |
| 2.2 | gate_2_2_blueprint_post_review | APPROVE, REVISE, FRESH REVIEW |
| 2.3 | gate_2_3_alignment_exhausted | REVISE SPEC, RESTART SPEC, RETRY BLUEPRINT |
| 3.1 | gate_3_1_test_validation | TEST CORRECT, TEST WRONG |
| 3.2 | gate_3_2_diagnostic_decision | FIX IMPLEMENTATION, FIX BLUEPRINT, FIX SPEC |
| 4.1 | gate_4_1_integration_failure | ASSEMBLY FIX, FIX BLUEPRINT, FIX SPEC |
| 4.2 | gate_4_2_assembly_exhausted | FIX BLUEPRINT, FIX SPEC |
| 5.1 | gate_5_1_repo_test | TESTS PASSED, TESTS FAILED |
| 5.2 | gate_5_2_assembly_exhausted | RETRY ASSEMBLY, FIX BLUEPRINT, FIX SPEC |
| 5.3 | gate_5_3_unused_functions | FIX SPEC, OVERRIDE CONTINUE |
| 6.0 | gate_6_0_debug_permission | AUTHORIZE DEBUG, ABANDON DEBUG |
| 6.1 | gate_6_1_regression_test | TEST CORRECT, TEST WRONG |
| 6.2 | gate_6_2_debug_classification | FIX UNIT, FIX BLUEPRINT, FIX SPEC |
| 6.3 | gate_6_3_repair_exhausted | RETRY REPAIR, RECLASSIFY BUG, ABANDON DEBUG |
| 6.4 | gate_6_4_non_reproducible | RETRY TRIAGE, ABANDON DEBUG |
| 6.5 | gate_6_5_debug_commit | COMMIT APPROVED, COMMIT REJECTED |
| H.1 | gate_hint_conflict | BLUEPRINT CORRECT, HINT CORRECT |

---

## Part 3: Agent Terminal Status Lines

**Setup Agent:** PROJECT_CONTEXT_COMPLETE, PROJECT_CONTEXT_REJECTED, PROFILE_COMPLETE.

**Stakeholder Dialog Agent:** SPEC_DRAFT_COMPLETE, SPEC_REVISION_COMPLETE.

**Stakeholder Spec Reviewer:** REVIEW_COMPLETE.

**Blueprint Author Agent:** BLUEPRINT_DRAFT_COMPLETE, BLUEPRINT_REVISION_COMPLETE.

**Blueprint Checker Agent:** ALIGNMENT_CONFIRMED, ALIGNMENT_FAILED: spec, ALIGNMENT_FAILED: blueprint.

**Blueprint Reviewer Agent:** REVIEW_COMPLETE.

**Test Agent:** TEST_GENERATION_COMPLETE, REGRESSION_TEST_COMPLETE.

**Implementation Agent:** IMPLEMENTATION_COMPLETE.

**Coverage Review Agent:** COVERAGE_COMPLETE: no gaps, COVERAGE_COMPLETE: tests added.

**Diagnostic Agent:** DIAGNOSIS_COMPLETE: implementation, DIAGNOSIS_COMPLETE: blueprint, DIAGNOSIS_COMPLETE: spec.

**Integration Test Author:** INTEGRATION_TESTS_COMPLETE.

**Git Repo Agent:** REPO_ASSEMBLY_COMPLETE.

**Help Agent:** HELP_SESSION_COMPLETE: no hint, HELP_SESSION_COMPLETE: hint forwarded.

**Hint Agent:** HINT_ANALYSIS_COMPLETE.

**Redo Agent:** REDO_CLASSIFIED: spec, REDO_CLASSIFIED: blueprint, REDO_CLASSIFIED: gate, REDO_CLASSIFIED: profile_delivery, REDO_CLASSIFIED: profile_blueprint.

**Bug Triage Agent:** TRIAGE_COMPLETE: build_env, TRIAGE_COMPLETE: single_unit, TRIAGE_COMPLETE: cross_unit, TRIAGE_NEEDS_REFINEMENT, TRIAGE_NON_REPRODUCIBLE.

**Repair Agent:** REPAIR_COMPLETE, REPAIR_FAILED, REPAIR_RECLASSIFY.

**Reference Indexing Agent:** INDEXING_COMPLETE.

**Cross-agent:** HINT_BLUEPRINT_CONFLICT: [details].

**Command results:** TESTS_PASSED: N passed, TESTS_FAILED: N passed M failed, TESTS_ERROR: [summary], COMMAND_SUCCEEDED, COMMAND_FAILED: [exit code].

**Matching rule:** All dispatchers use prefix matching (startswith). Agents may append trailing context.

---

## Part 4: Configuration Schemas (Compact)

### project_profile.json
```
pipeline_toolchain, python_version, delivery{environment_recommendation,
dependency_format, source_layout, entry_points}, vcs{commit_style,
commit_template, issue_references, branch_strategy, tagging,
conventions_notes, changelog}, readme{audience, sections, depth,
include_math_notation, include_glossary, include_data_formats,
include_code_examples, code_example_focus, custom_sections,
docstring_convention, citation_file, contributing_guide},
testing{coverage_target, readable_test_names, readme_test_scenarios},
license{type, holder, author, year, contact, spdx_headers,
additional_metadata{citation, funding, acknowledgments}},
quality{linter, formatter, type_checker, import_sorter, line_length},
fixed{language, pipeline_environment, test_framework, build_backend,
vcs_system, source_layout_during_build, pipeline_quality_tools},
created_at
```

### toolchain.json
```
toolchain_id, environment{tool, create, run_prefix, install, install_dev,
remove}, testing{tool, run, run_coverage, framework_packages, file_pattern,
collection_error_indicators, pass_fail_pattern}, packaging{tool,
manifest_file, build_backend, validate_command}, vcs{tool, commands{init,
add, commit, status}}, language{name, extension, version_constraint,
signature_parser, stub_body}, file_structure{source_dir_pattern,
test_dir_pattern, source_extension, test_extension},
quality{formatter{tool, format, check}, linter{tool, light, heavy, check},
type_checker{tool, check, unit_flags, project_flags}, packages,
gate_a, gate_b, gate_c}
```

### pipeline_state.json
```
stage, sub_stage, current_unit, total_units, fix_ladder_position,
red_run_retries, alignment_iteration, verified_units[], pass_history[],
log_references{}, project_name, last_action, debug_session{bug_id,
description, classification, affected_units, regression_test_path,
phase, authorized, created_at}, debug_history[], redo_triggered_from{},
delivered_repo_path, created_at, updated_at
```

**triage_result.json (debug artifact)**
```
affected_units[]
```
Written by triage agent to `.svp/triage_result.json`. Read by routing via `_read_triage_affected_units()` during TRIAGE_COMPLETE dispatch. Authorized for write during triage phases (Bug 55 fix).

**Sub-stages:** hook_activation, project_context, project_profile, blueprint_dialog, alignment_check, stub_generation (Bug 36 fix), quality_gate_a, quality_gate_b, quality_gate_a_retry, quality_gate_b_retry, redo_profile_delivery, redo_profile_blueprint, unit_completion, test_generation, red_run, implementation, green_run, coverage_review, repo_test, compliance_scan, repo_complete (Bug 26 fix), plus fix ladder positions.

**Stage 1 sub-stage note:** Stage 1 uses `sub_stage: None` throughout. The two-branch routing invariant (§3.6) uses `last_status.txt` to distinguish "dialog in progress" from "draft complete, present gate" -- no named sub-stage needed. The routing must still implement the full draft-review-approve cycle: Gate 1.1 (spec draft approval) and Gate 1.2 (spec post-review) must be reachable. Gate IDs must be registered in both routing dispatch and gate preparation registries (Bug 41 fix). **Reviewer status routing:** `route()` must distinguish `REVIEW_COMPLETE` (from the spec reviewer, routes to Gate 1.2) from `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` (from the dialog agent, routes to Gate 1.1).

**Gate C sub-stage note:** Gate C (assembly quality check) does not have a dedicated sub-stage. It runs within the git repo agent's assembly cycle as part of structural validation, unlike Gates A/B which are routing-level checkpoints between agent invocations. Gate C uses the same deterministic quality gate script as Gates A/B, invoked during structural validation (Section 12.3) with `"gate_c"` as the gate identifier.

**Fix ladder positions:** None → fresh_test → hint_test (test ladder). None → fresh_impl → diagnostic → diagnostic_impl (implementation ladder).

---

## Part 5: State Machine Transitions

### Stage Progression
```
0 → 1 → 2 → pre_stage_3 → 3 → 4 → 5
```

### Stage 0 Sub-Stage Progression
```
hook_activation → [Gate 0.1] → project_context → [Gate 0.2] → project_profile → [Gate 0.3] → Stage 1
```

### Stage 1 Sub-Stage Progression (Bug 41 fix)
```
stakeholder_spec_authoring (sub_stage=None) → [SPEC_DRAFT_COMPLETE / SPEC_REVISION_COMPLETE] → Gate 1.1
  Gate 1.1 APPROVE → finalize spec → Stage 2
  Gate 1.1 REVISE → re-invoke stakeholder dialog agent
  Gate 1.1 FRESH REVIEW → invoke spec reviewer → [REVIEW_COMPLETE] → Gate 1.2
    Gate 1.2 APPROVE → finalize spec → Stage 2
    Gate 1.2 REVISE → re-invoke dialog agent in revision mode
    Gate 1.2 FRESH REVIEW → re-invoke spec reviewer
```

### Stage 2 Sub-Stage Progression (Bug 23 fix)
```
blueprint_dialog → [Gate 2.1]
  Gate 2.1 APPROVE → alignment_check → [ALIGNMENT_CONFIRMED] → Gate 2.2
                                      → [ALIGNMENT_FAILED: spec → targeted spec revision → restart]
                                      → [ALIGNMENT_FAILED: blueprint → fresh blueprint dialog]
  Gate 2.1 REVISE → re-invoke blueprint author agent
  Gate 2.1 FRESH REVIEW → invoke blueprint reviewer → [REVIEW_COMPLETE] → Gate 2.2
    Gate 2.2 (reached via two paths: (1) alignment confirmed by checker, (2) fresh review completed by reviewer)
    Path-context mechanism: preparation script reads last_status.txt — ALIGNMENT_CONFIRMED includes alignment report; REVIEW_COMPLETE includes reviewer critique.
    Gate 2.2 APPROVE → Pre-Stage-3
    Gate 2.2 REVISE → re-invoke blueprint author agent in revision mode
    Gate 2.2 FRESH REVIEW → re-invoke blueprint reviewer
```

### Stage 5 Sub-Stage Progression (Bug 26 fix)
```
None (invoke git_repo_agent) → [REPO_ASSEMBLY_COMPLETE] → repo_test → [Gate 5.1: TESTS PASSED] → compliance_scan → [COMMAND_SUCCEEDED] → repo_complete → pipeline_complete
                                                           repo_test → [Gate 5.1: TESTS FAILED] → None (re-invoke, retries++)
                                                           repo_test (retries >= 3) → [Gate 5.2: RETRY ASSEMBLY] → None (reset retries)
                                                           repo_test (retries >= 3) → [Gate 5.2: FIX BLUEPRINT/SPEC] → restart
                                                           Gate C unused exports → [Gate 5.3: FIX SPEC] → restart from Stage 1
                                                           Gate C unused exports → [Gate 5.3: OVERRIDE CONTINUE] → proceed
                                                           compliance_scan → [COMMAND_FAILED] → None (re-enter fix cycle, retries++)
```

### Stage 3 Per-Unit Cycle
```
stub_generation → test_generation → [quality_gate_a] → red_run → implementation → [quality_gate_b] → green_run → coverage_review → unit_completion → (next unit or Stage 4)
```

### Quality Gate Decision Tree
```
Gate runs tools (auto-fix)
├── All clean → continue (no agent involvement)
└── Residuals remain
    ├── Re-invoke producing agent (1 re-pass)
    │   ├── Clean after re-pass → continue
    │   └── Still residuals → enter fix ladder
    │       ├── Gate A residuals → test fix ladder
    │       └── Gate B residuals → implementation fix ladder
    └── (gate retry budget is separate from fix ladder budget)
```

### Redo Profile Revision
```
/svp:redo → redo agent classifies
├── profile_delivery → redo_profile_delivery sub-stage → setup agent targeted revision → [PROFILE_COMPLETE] → two-branch check → Gate 0.3r → restore snapshot
└── profile_blueprint → redo_profile_blueprint sub-stage → setup agent targeted revision → [PROFILE_COMPLETE] → two-branch check → Gate 0.3r → restart from Stage 2
```
Note: Both redo profile sub-stages are governed by the two-branch routing invariant (Bug 43 fix). When last_status.txt contains PROFILE_COMPLETE, route() presents Gate 0.3r instead of re-invoking the setup agent.

### Post-Delivery Debug Loop (Logic Bug Path)
```
/svp:bug → [Gate 6.0: AUTHORIZE DEBUG] →
  Step 1: Prompt human for directions (Socratic triage)
  Step 2: Investigate (three-hypothesis discipline)
  Step 3: Fix workspace → reassemble to delivered repo
    ├── [Gate 6.2: FIX UNIT] → rollback_to_unit(N): invalidate verified_units >= N, delete src/tests, set stage:3, current_unit:N, sub_stage:None, fix_ladder_position:null, red_run_retries:0; rebuild from unit N forward
    ├── [Gate 6.2: FIX BLUEPRINT] → targeted revision, restart
    └── [Gate 6.2: FIX SPEC] → spec revision, restart
  Step 4: Evaluate spec/blueprint for latent gaps
  Step 5: Write regression test → [Gate 6.1: TEST CORRECT / TEST WRONG]
  Step 6: Update lessons learned (Doc 4)
  Step 7: Commit/push → [Gate 6.5: COMMIT APPROVED / COMMIT REJECTED]
```

---

## Part 5b: Regression Test File Mapping

| Bug | Test File | Description |
|---|---|---|
| 43 | `test_bug43_stage2_blueprint_routing.py` | Two-branch routing invariant, gate ID consistency |
| 44 | `test_bug44_null_substage_dispatch.py` | Null sub_stage dispatch handling |
| 45 | `test_bug45_test_execution_dispatch.py` | test_execution dispatch state transitions |
| 46 | `test_bug46_coverage_dispatch.py` | Coverage review dispatch advancement |
| 47 | `test_bug47_unit_completion_double_dispatch.py` | COMMAND/POST separation, no double dispatch |
| 48 | `test_bug48_launcher_cli_contract.py` | Launcher CLI argument contract |
| 49 | `test_bug49_argparse_enumeration.py` | Argparse enumeration in Tier 2 signatures |
| 50 | `test_bug50_contract_sufficiency.py` | Contract sufficiency, rollback behavior |
| 51 | `test_bug51_debug_reassembly.py` | Debug loop reassembly routing |
| 52 | `test_bug52_version_document_wiring.py` | version_document wired into dispatch |
| 53 | `test_bug53_orphaned_functions.py` | Orphaned dead-code function removal |
| 54 | `test_bug54_orphaned_update_state_from_status.py` | Orphaned update_state_from_status removal |
| 58 | `test_bug58_gate_5_3_unused_functions.py` | Gate 5.3 vocabulary, dispatch, routing |

All regression tests live in `tests/regressions/`. Bugs 55–57 are documentation/spec fixes with no dedicated regression test files.

---

## Part 6: Glossary

### Pipeline Architecture

- **SVP (Stratified Verification Pipeline):** Deterministically orchestrated, sequentially gated development system. Domain expert authors requirements; LLM agents generate, verify, and deliver a working Python project.
- **Stage:** One of six numbered stages (0-5) plus one transitional phase (Pre-Stage-3), for a total of seven sequential phases: Stage 0 (Setup), Stage 1 (Stakeholder Spec), Stage 2 (Blueprint), Pre-Stage-3 (Infrastructure), Stage 3 (Unit Verification), Stage 4 (Integration Testing), Stage 5 (Repository Delivery).
- **Gate:** A human decision point with explicit response options. Identified by stage number and sequence (e.g., Gate 3.1). Responses written to .svp/last_status.txt as exact strings.
- **Fix Ladder:** Bounded escalation sequence. Implementation: None → fresh_impl → diagnostic → diagnostic_impl → exhausted. Test: None → fresh_test → hint_test → exhausted. Position-aware advancement only.
- **Ruthless Restart:** Document-level problem triggers complete forward restart. No surgical repair of downstream artifacts.
- **Pass History:** Record of pipeline passes through Stage 3+. Tracks reach, reason ended, timestamp.
- **Session Boundary:** Point where launcher cycles the Claude Code session to prevent context degradation.
- **Binary Decision Logic:** Every diagnostic failure produces: implementation problem (fix locally) or document problem (fix document, restart). No third option.
- **Pattern Catalog:** Part 2 of `svp_2_1_lessons_learned.md`. Named failure patterns (P1–P9) with instance lists and prevention rules. Blueprint checker receives the catalog for advisory risk analysis.
- **Pattern P9 (Spec Structural Gap):** The spec provides a principle but not the granularity rules needed to operationalize it. Reviewers and checkers have no structural criteria to verify. Introduced in Bug 56.
- **Two-Tier Defense Model (Bugs 56–57):** (1) LLM-driven review catches root causes at authoring time via mandatory checklists baked into reviewer agent definitions. (2) Gate C deterministic check catches symptoms at assembly time via unused function detection. Together they provide defense in depth against the Bugs 52–55 pattern (functions implemented but never wired into dispatch).

### Four-Layer Orchestration

- **Layer 1 — CLAUDE.md:** Session-level identity and orchestration protocol. Loaded at session start. Influence degrades with context.
- **Layer 2 — REMINDER Block:** Behavioral reinforcement at point of highest recency in every routing script output.
- **Layer 3 — Terminal Status Lines:** Structured agent output constraining main session interpretation. Prefix-matched.
- **Layer 4 — Hooks:** Enforcement at boundaries. Write authorization and session protection. Can block but not direct.

### Three-Layer Preference Enforcement

- **Layer 1 — Blueprint Contracts:** Profile preferences translated into explicit behavioral contracts in affected units.
- **Layer 2 — Blueprint Checker Validation:** Checker verifies every profile preference covered by at least one unit's contracts.
- **Layer 3 — Delivery Compliance Scan:** Deterministic AST-based script scans delivered source for banned patterns.

### Quality Gates

- **Quality Gate:** Deterministic pre-processing step running formatting, linting, and/or type checking. Not a stage. Not a fix ladder position.
- **Quality Gate A:** Post-test, pre-red-run. Format + light lint (E, F, I). No type check on tests.
- **Quality Gate B:** Post-implementation, pre-green-run. Format + heavy lint + mypy --ignore-missing-imports.
- **Quality Gate C:** Stage 5 structural validation. Format check + full lint + full mypy (cross-unit, no --ignore-missing-imports). Includes unused exported function detection (`linter.unused_exports`); if unused functions are found, presents Gate 5.3 (`gate_5_3_unused_functions`) with FIX SPEC (strongly recommended) or OVERRIDE CONTINUE. Uses `{target}` resolved to assembled project source directory (target resolution is layout-dependent).
- **Gate Composition:** Operations each gate runs, from toolchain.json gate_a/gate_b/gate_c lists. Data-driven.
- **Auto-fix:** Deterministic in-place file modification (formatting, import sorting, simple lint). Runs before agent involvement.
- **Quality Residual:** Issue auto-fix cannot resolve. Triggers one agent re-pass. Then fix ladder.
- **Pipeline Quality Guarantee:** Every SVP 2.1 project is formatted, linted, and type-checked. Mandatory, no opt-out.
- **Coverage Review Auto-Formatting:** Newly added test code from coverage review receives Gate A auto-fix operations (format + light lint) before red-green validation. Auto-formatting is performed by the routing script as a deterministic `run_command` immediately after coverage review completion, before advancing to the next sub-stage. No full gate cycle, no agent re-pass, no type check. Formatting residuals are silently accepted at this stage (they do not affect correctness and are deferred to Gate C at assembly, where the Stage 5 bounded fix cycle catches and fixes them). Deferred residuals will consume bounded fix cycle attempts in Stage 5; this is acceptable because formatting fixes are trivial for the git repo agent.

### Commands

- **Group A (Utility):** /svp:save, /svp:quit, /svp:status, /svp:clean. Invoke cmd_*.py directly. No subagent.
- **Group B (Agent-Driven):** /svp:help, /svp:hint, /svp:ref, /svp:redo, /svp:bug. Complete action cycle: invoke prepare_task.py, spawn subagent, write status to last_status.txt, run update_state.py --phase <phase>, re-run routing. Phase values: help, hint, reference_indexing, redo, bug_triage.

### Forking Points

- **Tier A (Pipeline-Fixed):** Python, Conda, pytest, setuptools, Git, SVP-native layout during build, ruff + mypy during build. In profile fixed section.
- **Tier B (Delivery-Configurable):** Five dialog areas. Captured in profile. Acted on by git repo agent.
- **Unsupported Preferences:** Setup agent acknowledges but does not track. Human handles manually after delivery.

### Documents

- **Stakeholder Spec:** First-tier document. Natural language requirements. Single source of truth for intent. Always clean — working notes absorbed at iteration boundaries.
- **Blueprint:** Two paired files: `blueprint_prose.md` (Tier 1) and `blueprint_contracts.md` (Tier 2 + Tier 3). Atomic pair — versioned together, submitted together, checked together. Single source of truth for implementation structure.
- **Unit:** Smallest independently testable code. Three tiers: description, machine-readable signatures, behavioral contracts.
- **Tier 1 (Unit Description):** High-level prose description of a unit's purpose, responsibilities, and role in the pipeline. Lives in `blueprint_prose.md`.
- **Tier 2 (Function Signatures):** Complete list of exported functions with their parameter names, types, return types, and default values. Defines the unit's public API surface. Lives in `blueprint_contracts.md`.
- **Tier 3 (Behavioral Contracts):** Discrete, testable behavioral claims for each exported function — preconditions, postconditions, error conditions, state mutations, and dependencies. Must be sufficient for deterministic reimplementation by an agent reading only the Tier 2 signature and Tier 3 contract. Lives in `blueprint_contracts.md`.
- **Machine-Readable Signatures:** Python ast-parseable signatures with type annotations and imports.
- **Contract:** Explicit interface definition between units. Behavioral claims + type signatures.
- **Invariant:** Condition holding before and after execution. Python assert statements in Tier 2.
- **Topological Order:** Dependency-driven build sequence. First unit = first domain logic. Last unit = entry point. Backward-only dependencies.
- **DAG (Directed Acyclic Graph):** Unit dependency structure. No forward edges, no cycles. Validated at Stage 2 (checker), Pre-Stage-3 (infrastructure), and Stage 3 (stub generator).

### Configuration Files

- **Project Profile (project_profile.json):** Delivery preferences. Human-approved at Gate 0.3. Immutable. Changes via /svp:redo. Canonical naming invariant: exact section/field names defined in schema (§6.4) are authoritative; DEFAULT_PROFILE, setup agent output, and all consumers must match.
- **Toolchain File (toolchain.json):** Pipeline build commands. Copied from plugin. Permanently read-only. Placeholder resolution: single-pass. Resolution function strips extra whitespace from resolved commands (prevents double-space artifacts when placeholders resolve to empty strings).
- **Blueprint Prose (`blueprint_prose.md`):** Tier 1 unit descriptions. Human-readable intent. Read by blueprint author, checker, diagnostic, and help agents. Paired with `blueprint_contracts.md` — must be versioned atomically together.
- **Blueprint Contracts (`blueprint_contracts.md`):** Tier 2 signatures + Tier 3 contracts. Machine-readable precision. Read by test agent, implementation agent, stub generator, and git repo agent. Paired with `blueprint_prose.md`.
- **Quality Config (ruff.toml):** Quality tool configuration. Copied from plugin. Permanently read-only.
- **SVP Config (svp_config.json):** Tunable parameters. Human-editable anytime. Models, limits, budget.
- **Lessons Learned (`svp_2_1_lessons_learned.md`):** Living document (Doc 4). Bug catalog, pattern catalog, prevention rules. Updated by triage agent during debug sessions (Section 12.17.4 Step 6). Blueprint checker receives pattern catalog for advisory risk analysis. Test agent receives filtered entries for current unit.
- **Pipeline State (pipeline_state.json):** Progress tracking. Updated by deterministic scripts only.
- **Command Template:** String with {placeholders} resolved at runtime from toolchain.json.
- **Behavioral Equivalence:** Resolved commands identical to SVP 1.2 hardcoded commands. Applies to existing toolchain sections only; quality section is additive.

### Agents

- **Main Session:** Top-level Claude instance. Orchestration layer. Six-step mechanical action cycle.
- **Subagent:** Isolated Claude instance. Fresh context window. Cannot spawn further subagents.
- **Task Prompt:** Project-specific content from preparation script for each invocation.
- **Routing Script:** Deterministic script outputting next action as structured block. Five action types.

### Claude Code Ecosystem

- **Claude Code:** Anthropic's CLI-based AI agent. Runtime environment for SVP.
- **SVP Launcher:** Standalone CLI tool. Three modes: `svp new`, bare `svp` (resume), `svp restore`. Ordered pre-flight checks (8 checks, fail-fast). Session launch via subprocess.run with cwd, SVP_PLUGIN_ACTIVE env, restart signal loop. Not a plugin component.
- **Plugin:** Distributable bundle of skills, agents, commands, hooks, configuration.
- **Skill (SKILL.md):** Directory loaded on demand by description matching. SVP uses one orchestration skill. Includes slash-command-initiated action cycle guidance for Group B commands.
- **Custom Agent (AGENT.md):** Markdown defining subagent. System prompt + tool restrictions + model.
- **Slash Command:** Markdown in commands/ directory. Injected into conversation on invocation.
- **Hook:** Event-driven automation at lifecycle points. SVP uses `PreToolUse` for write authorization and bash blocking, and `PostToolUse` for stub sentinel detection. Plugin format requires top-level "hooks" wrapper key.
- **CLAUDE.md:** Project-level persistent context.
- **MCP:** Standard for LLM-external-tool connection. SVP uses for optional GitHub read access.

### Delivery

- **Pipeline Toolchain:** Conda, pytest, setuptools, Git, ruff, mypy. Fixed for SVP 2.1 (terminal release).
- **Delivery Toolchain:** What the delivered project presents to end users. Configurable through profile.
- **Delivery Compliance Scan:** Layer 3 enforcement. AST-based scan of delivered source against profile preferences.
- **Mode A (Self-Build):** SVP building itself. README is carry-forward: previous version's README preserved in full, only new-version sections added. Toolchain defaults are plugin artifacts.
- **Mode B (General Project):** SVP building any other software. README generated from profile.
- **Language-Directed Variant:** Separate product (SVP-R, SVP-elisp, SVP-bash) sharing pipeline architecture with language-specific tooling. Built by SVP 2.1 as Python projects.

---

*End of specification summary.*
