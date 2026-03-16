# SVP 2.1 — Lessons Learned

**Date:** 2026-03-15
**Source material:** Regression tests from `tests/regressions/`, unit test suites, and build tool observations across SVP 1.0 through 2.0. Bugs 17-25 discovered during SVP 2.1 pre-build inspection and early build. Bugs 26-30 discovered post-delivery (assembly and carry-forward regressions). Bugs 31-32 discovered during rebuild preparation (plugin discovery regression, CLI vocabulary regression). Bugs 33-36 discovered during SVP 2.1 rebuild (bootstrapping: SVP 2.1 building itself). Bugs 37-41 discovered post-delivery during SVP 2.1 rebuild (repo location, command definitions, skill guidance, artifact synchronization, Stage 1 routing). Bug 42 discovered post-delivery (pre-stage-3 state persistence and reference indexing advancement). Bug 43 discovered post-delivery during SVP 2.1 rebuild (Stage 2 blueprint routing missing two-branch check). Bugs 44-47 discovered post-delivery (SVP 2.1 build: Stage 3 dispatch and unit_completion routing).
**Document status:** Living document. Updated by the bug triage agent during post-delivery debug sessions (Section 12.17, Step 6).

---

## Purpose

This document converts debugging knowledge into forward-looking guidance for the blueprint author. Each bug is analyzed for its root cause pattern. Each pattern produces concrete prevention rules.

The blueprint author should consult this document during unit design. The blueprint checker should use the pattern catalog to anticipate failure modes.

This document is updated during post-delivery debug sessions. When `/svp:bug` resolves a logic bug, the triage agent appends a new entry to the bug catalog (Part 1), updates the pattern catalog (Part 2) if a new pattern is identified, and updates the regression test file mapping. The format of new entries must match the established catalog structure: bug number, caught-by, test file, description, root cause pattern, and prevention rule.

---

## Part 1: Unified Bug Catalog (Bugs 1-47)

Bugs are numbered sequentially in chronological order of discovery. Each entry notes how it was caught (blueprint-era or post-delivery) and where its test lives (unit test assertions or regression test file).

---

### Bug 1 — Gate Status String Mismatch

**Caught:** Blueprint-era fix (SVP 1.2 design). **Test:** Unit test assertions.

The orchestration layer wrote "GATE_APPROVED" while update_state.py checked s.startswith("APPROVE"). Neither matched, producing a routing loop. Fixed by defining gate status vocabulary as a shared data constant with exact matching.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Gate status strings must be a shared canonical vocabulary. Tests verify both routing output and dispatcher reference the same constant.

---

### Bug 2 — Hook Permission Freeze After Stage 5

**Caught:** Blueprint-era fix (SVP 1.2 design). **Test:** Unit test assertions.

After Stage 5, hooks blocked all writes. The debug loop needs write access. Fixed by adding debug_session.authorized to pipeline state; the hook checks it.

**Pattern:** P2 (State management assumptions). **Prevention:** Security enforcement must account for every legitimate write path. When a new write-permitted state is added, hook authorization must be updated in the same blueprint.

---

### Bug 3 — SVP_PLUGIN_ACTIVE Environment Variable

**Caught:** Blueprint-era fix (SVP 1.1 hardening). **Test:** Unit test assertions.

Hooks and launcher used different detection mechanisms for SVP sessions. Fixed by defining canonical env var SVP_PLUGIN_ACTIVE shared between both.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Shared detection mechanisms must be defined as shared constants, not independently invented.

---

### Bug 4 — skip_permissions Hardcoded

**Caught:** Blueprint-era fix (SVP 1.1 hardening). **Test:** Unit test assertions.

Claude Code permission bypass flag was hardcoded. Fixed by making it configurable via svp_config.json.

**Prevention:** Any launch flag affecting security posture should be configurable, not hardcoded.

---

### Bug 5 — Command Group A/B Confusion

**Caught:** Blueprint-era fix (SVP 1.1 hardening). **Test:** Unit test assertions and prohibited-script checks.

Group B commands (help, hint, ref, redo, bug) were implemented as Group A scripts (cmd_help.py, etc.) — the most costly bug in SVP 1.1. Fixed by enforcing prohibition: those cmd_*.py files must never exist.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When two execution paths exist, the blueprint must state which commands use which path. Tests verify prohibited files do not exist.

---

### Bug 6 — CLI Wrapper Drift

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug2_wrapper_delegation.py`

update_state.py and run_tests.py reimplemented routing logic inline (200-500 lines) instead of delegating to routing.py. When routing.py changed, wrappers diverged silently. Fixed by rewriting as thin delegators under 50 lines.

**Test details:** AST-based: wrappers import from routing, define no non-main functions, are under 50 lines, don't import subprocess or argparse.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Blueprint must state wrappers are thin delegators with zero domain logic. Specify exact imports. Include AST-based structural tests.

---

### Bug 7 — CLI Argument Mismatch

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug3_cli_argument_contracts.py`

routing.py generated --output flag; prepare_task.py didn't accept it. Exit code 2. Fixed by adding --output. Rule: when routing adds a flag, consumer argparse updated same commit.

**Test details:** Extracts --flags from routing via AST, extracts accepted flags from consumers, verifies generated is subset of accepted.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Cross-unit CLI contracts documented as explicit dependencies in both units. Consumer tests verify all generated flags accepted.

---

### Bug 8 — Status Line Vocabulary Mismatch

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug4_status_line_contracts.py`

setup_infrastructure.py printed INFRASTRUCTURE_SETUP_COMPLETE — not in COMMAND_STATUS_PATTERNS. ValueError from dispatcher. Fixed by using COMMAND_SUCCEEDED/COMMAND_FAILED only.

**Test details:** AST extraction of print() constants from run-command scripts, verified against vocabulary. Dispatcher rejects custom strings.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Status vocabulary as importable data constant. Every emitting script tested against the vocabulary.

---

### Bug 9 — Framework Dependencies Missing

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug5_pytest_framework_deps.py`

create_conda_environment installed only blueprint-extracted packages. pytest not in domain signatures. Every test run failed. Fixed by unconditional install from testing.framework_packages.

**Test details:** Mocks subprocess.run, verifies pytest in pip calls with empty package dict.

**Pattern:** P4 (Framework dependency completeness). **Prevention:** Distinguish extracted from framework dependencies. Toolchain package lists authoritative. Test with empty dicts.

---

### Bug 10 — Collection Error Misclassification

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug6_collection_error_classification.py`

_is_collection_error() used bare "ERROR" substring. Fixture NotImplementedError during red runs contains "ERROR at setup" — misclassified as collection error. Fixed with specific indicators from toolchain.

**Test details:** Fixture errors return False; real collection errors (ERROR collecting, ImportError, SyntaxError, no tests ran) return True.

**Pattern:** P5 (Error classification precision). **Prevention:** Enumerate positive indicators explicitly. Include true positives and true negatives. Toolchain indicator list authoritative.

---

### Bug 11 — Stale Status File on Unit Completion

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug7_unit_completion_status_file.py`

Unit completion COMMAND called update_state.py which reads last_status.txt. File still had COVERAGE_COMPLETE from previous phase — not in COMMAND_STATUS_PATTERNS. Fixed by writing COMMAND_SUCCEEDED before invoking update_state.py.

**Test details:** Verifies COMMAND_SUCCEEDED appears before update_state.py in command string. Verifies dispatch handles it correctly.

**Pattern:** P2 (State management assumptions). **Prevention:** Any routing action where POST reads status file must write valid status first. Tests verify write-before-read ordering.

---

### Bug 12 — Sub-Stage Not Reset on Unit Completion

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug8_sub_stage_reset_on_completion.py`

complete_unit() advanced current_unit but didn't reset sub_stage. Next unit started at "unit_completion" — routing dispatched completion immediately, skipping all verification. Fixed by resetting sub_stage, fix_ladder_position, and red_run_retries.

**Test details:** Verifies all three fields reset for first, middle, and final units in sequence.

**Pattern:** P2 (State management assumptions). **Prevention:** Every transition function must have explicit post-conditions for ALL fields. Tests verify multi-step sequences. Tier 2 invariants enumerate every reset.

---

### Bug 13 — Hook Path Resolution

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug9_hook_path_resolution.py`

HOOKS_JSON_CONTENT had "bash scripts/write_authorization.sh". Hooks fire from project root — scripts/ resolves to pipeline scripts, not .claude/scripts/ where shell scripts live. Both security hooks silently failed (exit 127). Fixed by using .claude/scripts/ paths and rewriting during copy.

**Test details:** Verifies content/schema use correct paths. Verifies _copy_hooks rewrites bare paths.

**Pattern:** P3 (Path resolution fragility). **Prevention:** Path-containing content must document resolution context. Tests verify actual path strings. Copy operations tested with rewriting scenarios.

---

### Bug 14 — Agent Status Line Exact Matching

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug10_agent_status_prefix_matching.py`

dispatch_command_status used startswith() (prefix). dispatch_agent_status used exact match. "TEST_GENERATION_COMPLETE: 45 tests" didn't match "TEST_GENERATION_COMPLETE". Fixed by making both use prefix matching.

**Test details:** Exact matches work (baseline), trailing context accepted (fix), unknown lines rejected.

**Pattern:** P6 (Status line matching inconsistency). **Prevention:** Same data format requires same matching strategy. Blueprint must specify agents MAY append trailing context. Tests include with/without trailing.

---

### Bug 15 — Missing Documentation Artifacts in Delivered Repo

**Caught:** Post-delivery, human inspection. **Test:** `test_bug11_delivered_repo_artifacts.py`

Spec enumerated artifacts but omitted doc/stakeholder.md and doc/blueprint.md. Git repo agent correctly implemented incomplete spec. First spec-level bug. Fixed by amending spec to require all documentation in delivered repo.

**Test details:** Verifies delivered repo contains doc/ with both files (non-empty) and examples/game-of-life/.

**Pattern:** P7 (Spec completeness). **Prevention:** Spec enumerations verified by structural tests. Every path in directory structure must appear in assembly unit's contracts. Blueprint checker should verify path coverage.

---

### Bug 16 — Missing __main__ Guards in Group A Scripts

**Caught:** Post-delivery, Gate 6. **Test:** `test_bug12_cmd_main_guards.py`

Three of four cmd_* scripts had no if __name__ == "__main__" guard. Slash commands invoke python scripts/cmd_X.py — without guard, functions defined but never called. Silent success, no output. Fixed by adding guards with argparse and print.

**Test details:** AST verification of guard presence, --project-root flag, and print() in guard block for all four scripts.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Blueprint must state __main__ guard as structural contract. AST tests verify. When scripts share a pattern, define once and reference.

---

### Bug 17 — Hook Configuration Schema Mismatch

**Caught:** Post-delivery, human inspection (plugin load failure). **Test:** `test_bug13_hook_schema_validation.py`

Plugin `hooks.json` used wrong field names and structure: `type: "bash"` instead of `type: "command"`, `script` instead of `command`, and placed handler fields directly on the matcher object instead of inside a nested `hooks` array. Claude Code requires each `PreToolUse` entry to have a `matcher` string and a `hooks` array containing handler objects with `type` and `command` fields. The plugin failed to load entirely — Claude Code reported "Hook load failed" with schema validation errors. Both security hooks (write authorization and non-SVP session protection) were silently non-functional since delivery. Layer 2 of universal write authorization was never active.

Fixed by restructuring to the correct schema: each matcher entry contains a `hooks` array of handler objects with `type: "command"` and `command` fields.

**Test details:** Validates hook JSON structure: top-level `hooks` key, `PreToolUse` array entries each have `matcher` (string) and `hooks` (array). Each handler in the nested `hooks` array has `type: "command"` and `command` (string starting with `.claude/scripts/`). Validates that `type: "bash"` and `script` field names are absent. Validates plugin loads without schema errors.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Hook configuration schema must be specified as an explicit structural contract in the spec with the exact JSON shape. Tests validate the schema against Claude Code's actual requirements. Hook configurations must be tested for successful plugin load, not just structural correctness.

---

### Bug 18 — Routing Script Missing PREPARE and POST Command Emission

**Caught:** During SVP 2.1 build, Gate 0.1. **Test:** `test_bug14_routing_action_block_commands.py`

The spec (Section 17) defines action blocks with explicit `PREPARE` and `POST` fields containing exact commands. `routing.py` had helper functions `_prepare_cmd()`, `_post_cmd()`, and `_gate_prepare_cmd()` that generate the correct commands, but `route()` never included them in action dicts and `format_action_block()` never emitted them. All three helpers existed as dead code. The REMINDER block told the main session "Run the POST command" without specifying what command — forcing the orchestration layer to guess script names and arguments. The main session improvised `post_action.py`, which doesn't exist (exit code 2). This directly violates the "do not improvise pipeline flow" principle (Section 3.6).

Fixed by wiring `_prepare_cmd()`, `_post_cmd()`, and `_gate_prepare_cmd()` into `route()` action dicts and emitting `PREPARE` and `POST` fields from `format_action_block()`. Fix applied to canonical source (`src/unit_10/stub.py`) first, then copied to `scripts/routing.py` per the dual-file synchronization contract (Section 6.1).

**Test details:** AST-based: verify `format_action_block()` emits `PREPARE:` and `POST:` fields when present in the action dict. Verify `route()` returns action dicts with `POST_COMMAND` keys for every state that requires a post-action. Verify `_prepare_cmd()`, `_post_cmd()`, and `_gate_prepare_cmd()` are called (not dead code) by checking call sites via AST. Verify emitted POST commands reference `update_state.py` (not `post_action.py` or other non-existent scripts).

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When the spec defines an output format with required fields, tests must verify the implementation emits every required field. Dead code detection: helpers that exist but are never called from the main code path should be caught by structural tests verifying call site connectivity.

---

### Bug 19 — Gate Prepare Flag Mismatch

**Caught:** During SVP 2.1 build, Gate 0.1. **Test:** `test_bug15_gate_prepare_flag_mismatch.py`

`_gate_prepare_cmd()` in `routing.py` generated `--agent gate_{context}` instead of `--gate {gate_id}`. This sent gate preparation requests through the agent codepath in `prepare_task.py`, which rejected it with `ValueError: Unknown agent type: gate_hook_activation`. Additionally, `gate_0_1_hook_activation` was missing from `ALL_GATE_IDS` in `prepare_task.py` and had no handler in `prepare_gate_prompt()`. Two-sided contract mismatch: the producer sent the wrong flag and the consumer's registry was incomplete.

Fixed by changing `_gate_prepare_cmd()` to use `--gate {gate_id}`, updating the call site to pass the full gate ID, adding `gate_0_1_hook_activation` to `ALL_GATE_IDS`, and adding a gate prompt handler.

**Test details:** Verify `_gate_prepare_cmd()` emits `--gate` flag (not `--agent`). Verify all gate IDs referenced in `route()` action dicts are present in `ALL_GATE_IDS`. Verify `prepare_gate_prompt()` handles every gate ID in the registry. Verify the generated PREPARE command for hook activation resolves to a valid gate prompt.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When two units share a CLI interface (flags, argument values), both sides must be tested together. Gate ID registries must be validated for completeness against all gate IDs referenced in routing.

---

### Bug 20 — SameFileError on Output Path Match

**Caught:** During SVP 2.1 build, Gate 0.1. **Test:** `test_bug16_same_file_copy_guard.py`

`prepare_agent_task()` writes to `.svp/task_prompt.md` internally. When the CLI is invoked with `--output .svp/task_prompt.md`, `main()` calls `shutil.copy2(result, output_path)`, which raises `SameFileError` because source and destination resolve to the same file. Missing defensive guard.

Fixed by adding a `resolve()` check: skip the copy when source and destination are the same path.

**Test details:** Verify no error when `--output` matches internal write path. Verify copy succeeds when `--output` differs. Verify result path is correct in both cases.

**Pattern:** P2 (State management assumptions). **Prevention:** File operations that copy from an internal path to a user-specified path must guard against same-file collision. Test with both matching and non-matching paths.

---

### Bug 21 — Routing Script Missing Gate Presentation After Agent Completion

**Caught:** During SVP 2.1 build, Stage 0 (setup). **Test:** `test_bug17_routing_gate_presentation.py`

In `routing.py`, when the setup agent returns `PROFILE_COMPLETE` (or `PROJECT_CONTEXT_COMPLETE`), `update_state_main()` intentionally keeps state at the same sub-stage (`project_profile` or `project_context`) so that the next `route()` call presents the corresponding gate (Gate 0.3 or Gate 0.2). However, `route()` for these sub-stages always returns the setup agent invocation with no conditional branch checking whether the agent has already completed. The pipeline loops indefinitely re-invoking the agent after the output file is already written. The same structural pattern as Bug 18: `route()` must handle all reachable states within a sub-stage, not just the initial entry.

Fixed by adding a two-branch check in `route()`: read `last_status.txt` and, if it contains the agent's terminal status, emit a `human_gate` action instead of `invoke_agent`. Applied to both `project_context` (Gate 0.2) and `project_profile` (Gate 0.3) sub-stages.

**Test details:** Verify `route()` returns `human_gate` action for `gate_0_2_context_approval` when `last_status.txt` contains `PROJECT_CONTEXT_COMPLETE` and sub-stage is `project_context`. Verify `route()` returns `human_gate` action for `gate_0_3_profile_approval` when `last_status.txt` contains `PROFILE_COMPLETE` and sub-stage is `project_profile`. Verify `route()` returns `invoke_agent` when `last_status.txt` does not contain the terminal status (agent not yet done). Verify the pattern holds for both sub-stages symmetrically.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When `update_state` intentionally holds a sub-stage steady to trigger a gate on the next routing call, `route()` must have a conditional branch for the post-completion state. Tests must verify both branches (agent-not-done and agent-done) for every sub-stage that uses this two-phase protocol.

---

### Bug 22 — Stakeholder Spec Filename Mismatch Between Setup Agent and Prepare Script

**Caught:** During SVP 2.1 build, Stage 2 entry. **Test:** `test_bug18_stakeholder_spec_filename.py`

The setup agent placed the stakeholder spec at `specs/stakeholder.md`. The `prepare_task.py` script hardcoded the path `specs/stakeholder_spec.md`. At the Stage 1-to-2 boundary, `prepare_task.py` crashed with `FileNotFoundError` when assembling the blueprint author's task prompt. There was no single source of truth for the canonical filename -- each component independently chose its own convention.

Fixed by defining the canonical stakeholder spec filename (`stakeholder_spec.md`) as a shared constant referenced by both the setup agent's file placement logic and the preparation script's file loading logic. The file was renamed to `stakeholder_spec.md` to match the more descriptive convention.

**Test details:** Verify the filename constant used by the file writer (setup agent / stakeholder dialog agent) matches the filename constant used by the file reader (prepare_task.py). AST-based test verifies both components import from the same shared constant rather than hardcoding independent strings. Verify `FileNotFoundError` does not occur when the pipeline transitions from Stage 1 to Stage 2.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Pipeline artifact filenames must be defined as shared constants in one location. No component may hardcode an artifact filename independently. Structural tests should verify that producers and consumers reference the same constant. This generalizes to all cross-component path references.

---

### Bug 23 — Alignment Check Skipped in Stage Progression

**Caught:** During SVP 2.1 build, Stage 2 to Pre-Stage-3 transition. **Test:** `test_bug19_alignment_check_routing.py`

After Gate 2.1 blueprint approval (APPROVE), `advance_stage` jumped directly to `pre_stage_3`, completely skipping the blueprint checker (alignment check). The blueprint checker agent exists, the `alignment_check` phase exists, and the gate vocabulary includes `gate_2_3_alignment_exhausted` -- but the routing script has no path that leads to the blueprint checker. Stage 2 routes only to `blueprint_author` (for drafting) and implicitly to `blueprint_reviewer` (via FRESH REVIEW). The alignment check is defined in the vocabulary but never wired into the execution flow. The pipeline proceeded to test generation with an unvalidated blueprint.

Fixed by adding an `alignment_check` sub-stage to Stage 2. After Gate 2.1 APPROVE, the state transitions to `alignment_check` instead of advancing to Pre-Stage-3. The routing script invokes the blueprint checker at this sub-stage. On `ALIGNMENT_CONFIRMED`, the pipeline presents Gate 2.2 -- the human always decides when to advance to Pre-Stage-3. On Gate 2.2 APPROVE, the pipeline advances to Pre-Stage-3. On `ALIGNMENT_FAILED`, the appropriate gate is presented per the checker's classification (spec problem or blueprint problem).

**Test details:** Verify that after Gate 2.1 APPROVE, `advance_stage` transitions to `alignment_check` sub-stage (not directly to `pre_stage_3`). Verify `route()` returns an `invoke_agent` action for `blueprint_checker` when sub-stage is `alignment_check`. Verify `ALIGNMENT_CONFIRMED` presents Gate 2.2 (not direct advance to Pre-Stage-3). Verify Gate 2.2 APPROVE advances to Pre-Stage-3. Verify `ALIGNMENT_FAILED: spec` and `ALIGNMENT_FAILED: blueprint` trigger the correct downstream gates and state transitions. Verify the alignment loop iteration counter is tracked correctly across multiple check-and-revise cycles.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When a vocabulary defines an agent, phase, and gate, the routing script and state transition logic must have explicit paths that invoke them. Structural tests should verify that every agent type in the vocabulary has at least one routing path that leads to its invocation. Dead vocabulary entries (defined but never routed to) should be caught by the same connectivity checks that catch dead helper functions (General Principle 10).

---

### Bug 24 — `total_units` Read as None During Infrastructure Setup

**Caught:** During SVP 2.1 build, Pre-Stage 3. **Test:** `test_bug20_total_units_derivation.py`

`run_infrastructure_setup` reads `total_units` from pipeline state using `state.get("total_units", 1)`. At Pre-Stage 3, `total_units` is `null` (explicitly set to `null` in the initial state, not missing as a key). Since the key exists with value `None`, `dict.get()` returns `None` instead of the default `1`. This `None` propagates to `create_project_directories` which does `range(1, total_units + 1)`, producing `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`.

The deeper issue is a producer/consumer inversion: infrastructure setup is the component that should **derive** `total_units` from the blueprint (by counting extracted units) and **write** it to state. Instead, the code reads it from state before blueprint extraction -- a chicken-and-egg dependency.

Fixed by restructuring `run_infrastructure_setup` to: (1) extract units from the blueprint first, (2) derive `total_units` from the extraction count, (3) validate the count is a positive integer, (4) use it for directory creation, (5) write it to pipeline state. Additionally, `create_project_directories` validates that `total_units` is a positive integer, rejecting `None`.

**Test details:** Verify infrastructure setup derives `total_units` from the blueprint, not from state. Run with `total_units: null` in state and a valid blueprint: no crash, correct count derived, count written to state as positive integer. Verify `create_project_directories` raises a clear error when `total_units` is `None` or non-positive. Verify `dict.get("total_units", default)` is not used (or if used, is guarded against explicit `None`).

**Pattern:** P3 (Implicit resolution assumption). **Prevention:** When a value is derived during a pipeline step, the deriving function must produce the value before any consumer reads it. Functions receiving state values must validate against `None`, not rely on `dict.get()` defaults (which do not trigger when the key exists with an explicit `null` value). Producer/consumer roles for state fields should be documented: which step writes each field, and which steps may read it.

---

### Bug 25 — Stage 3 Core Sub-Stage Routing Unspecified

**Caught:** During SVP 2.1 build, Stage 3 Unit 1. **Test:** `test_bug21_stage3_sub_stage_routing.py`

SVP 2.0's `route()` function for Stage 3 only checks for `sub_stage == "unit_completion"` and defaults to returning `implementation_agent` for everything else. There is no routing path for `test_generation`, `red_run`, `green_run`, `coverage_review`, or the initial `None` sub-stage. The pipeline skips the full test→red_run→implement→green_run→coverage_review cycle and jumps directly to implementation for every unit.

The SVP 2.1 blueprint had the same gap: `STAGE_3_SUB_STAGES` defines the full cycle (Unit 2), dispatch contracts describe transitions between sub-stages (Unit 10), but the routing contracts never specified what action to emit for each core sub-stage. The quality gate sub-stage routing was fully specified, but the six core sub-stages that form the backbone of Stage 3 were not.

Fixed by adding explicit routing contracts to Unit 10 for every core Stage 3 sub-stage: `None`/`test_generation` → `invoke_agent` for `test_agent`; `red_run` → `run_command` for pytest (expect failure); `implementation` → `invoke_agent` for `implementation_agent`; `green_run` → `run_command` for pytest (expect pass); `coverage_review` → `invoke_agent` for `coverage_review`; `unit_completion` → `complete_unit()` and `session_boundary`.

**Test details:** Verify `route()` returns distinct action types for each Stage 3 sub-stage. Verify `test_agent` is invoked at `test_generation`/`None`, `implementation_agent` at `implementation`, `coverage_review` at `coverage_review`. Verify `run_command` with pytest is emitted at `red_run` and `green_run`. Verify no two non-equivalent sub-stages produce identical routing output. Verify the default case does NOT silently return `implementation_agent`.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When a state schema defines a list of sub-stages, the routing function must have an explicit branch for every sub-stage. Structural tests should verify routing coverage: every sub-stage in the schema must appear as a condition in the routing function. This is the same principle as Bug 23 (vocabulary defined but routing wiring absent) applied to Stage 3 instead of Stage 2.

---

### Bug 26 — Stage 5 Repo Assembly Routing Missing

**Caught:** Post-delivery, human inspection (no repo directory created). **Test:** `test_bug17_stage5_repo_assembly_routing.py`

The `route()` function in Unit 10 (`routing.py`, lines 450-462) was missing the entire Stage 5 repo assembly workflow. When the pipeline reached Stage 5 with no active debug session, `route()` immediately returned `pipeline_complete` without ever invoking the git repo agent. The git repo agent was never called, so no repository directory was created — only the working directory existed.

All Stage 5 infrastructure was defined but unreachable: gate vocabulary entries (`gate_5_1_repo_test`, `gate_5_2_assembly_exhausted`), phase-to-agent mapping (`repo_assembly -> git_repo_agent`), known phases (`repo_assembly`, `compliance_scan`). Additionally, `dispatch_agent_status` for `git_repo_agent` was a no-op (`return state`), and `dispatch_gate_response` for `gate_5_1_repo_test` was also a no-op for both responses. `dispatch_command_status` for `compliance_scan` returned `state` unchanged on success.

Fixed by adding full sub-stage routing to Stage 5: `sub_stage=None` invokes git_repo_agent; `repo_test` presents gate_5_1; `compliance_scan` runs the scan; `repo_complete` returns pipeline_complete. Fixed `dispatch_agent_status` for git_repo_agent to record `delivered_repo_path` and advance to `repo_test`. Fixed gate_5_1 to advance to `compliance_scan` on TESTS PASSED and re-invoke assembly on TESTS FAILED. Fixed compliance_scan dispatch to advance to `repo_complete` on success.

**Test details:** AST-based structural verification: (1) `route()` returns an `invoke_agent` action for `git_repo_agent`; (2) git_repo_agent action includes PREPARE and POST keys; (3) `repo_assembly` phase referenced in route(); (4) `gate_5_1` and `gate_5_2` reachable from route() or dispatch functions; (5) `dispatch_agent_status` for git_repo_agent is not a bare `return state`; (6) Stage 5 references git_repo_agent or repo_assembly before pipeline_complete.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** When a vocabulary defines gates, phases, and agent mappings for a stage, routing must have explicit paths that invoke them. Structural tests should verify that every stage's infrastructure (gates, phases, agents) is reachable from route(). This is the same principle as Bugs 23 and 25: vocabulary defined but routing wiring absent.

---

### Bug 27 — Environment Name Derivation Mismatch in Delivered Repository

**Caught:** Post-delivery, human test execution (conda environment not found). **Test:** (manual verification)

The git repo agent (Unit 18) generated `environment.yml` and `README.md` with environment name `svp2_1`, replacing the dot in `svp2.1` with an underscore. The canonical `derive_env_name()` function in Unit 1 (`svp_config.py`) only replaces spaces and hyphens with underscores, preserving dots: `svp2.1` → `svp2.1`. The actual conda environment created during infrastructure setup was `svp2.1`. When the user ran `conda run -n svp2_1 python -m pytest tests/`, conda reported `EnvironmentLocationNotFound`.

The git repo agent independently derived the environment name using a broader replacement rule (dots → underscores) instead of calling or replicating the canonical `derive_env_name()` logic.

Fixed by correcting `environment.yml` and `README.md` in the delivered repo to use `svp2.1`.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** Environment name derivation must use the canonical `derive_env_name()` function from Unit 1 or exactly replicate its rules. The git repo agent's task prompt should include the canonical env name (derived from `derive_env_name(project_name)`) so the agent does not need to derive it independently. Tests should verify the delivered `environment.yml` name matches `derive_env_name(project_name)`.

---

### Bug 28 — Git Repo Agent Single-Commit Assembly Instead of Prescribed Commit Order

**Caught:** Post-delivery, human inspection (git log showed 1 commit instead of 11). **Test:** (manual verification)

The spec (Section 12.1) prescribes 11 sequential commits in a specific order: (1) conda environment file, dependency list, directory structure; (2) stakeholder spec; (3) blueprint; (4) each unit sequentially in topological order; (5) integration tests; (6) project configuration files; (7) document version history; (8) reference documents and summaries; (9) project context; (10) quality tool configuration files; (11) changelog. The git repo agent dumped all files into a single "feat: initial delivery of SVP 2.1" commit, violating the prescribed commit structure entirely.

Additionally, `docs/references/` and `docs/history/` directories were not created, meaning reference documents (lessons learned, summary, baseline, roadmap) and version history were absent from the delivered repo.

**Root cause:** The git repo agent's task prompt describes the commit order, but the agent chose to create a single monolithic commit instead. This is an agent behavioral compliance issue — the agent understood the instruction but took a shortcut. The task prompt does not include structural enforcement mechanisms (e.g., a post-assembly validation that checks commit count and order).

**Detection:** Manual inspection of `git log --oneline` in the delivered repo. Future prevention: a structural validation step should verify commit count and content against the prescribed order. The bounded fix cycle's test command should include `git log --oneline | wc -l` as a minimum check.

**Recovery:** Re-invoke the git_repo_agent with explicit emphasis on the commit order requirement. The agent must create separate commits for each prescribed step.

**Pattern:** P7 (Spec completeness) + P1 (Cross-unit contract drift). The spec defines the commit order, but there is no automated validation that the agent followed it. The structural validation step (Section 12.3) checks file existence, import resolution, and quality gates, but not commit structure. **Prevention:** Add commit structure validation to the structural validation checklist. The git repo agent's task prompt should state the commit order as a hard requirement with validation criteria, not just a description.

---

### Bug 29 — Multiple Assembly Defects in Delivered Repository

**Caught:** Post-delivery, test execution during Gate 5.1. **Test:** (existing regression tests caught issues in delivered repo)

During Gate 5.1 repo test, 8 tests failed in the delivered repository revealing 5 distinct defects:

1. **Stale integration test** (`test_stage_5_no_debug_returns_pipeline_complete`): Expected old Stage 5 behavior (immediate `pipeline_complete`). Needed update for Bug 26 fix — Stage 5 now invokes `git_repo_agent` first.

2. **Incomplete gate ID registry** (`test_all_route_gate_ids_in_registry`): `ALL_GATE_IDS` in `prepare_task.py` contained only 4 gate IDs, but `route()` references 6 gate IDs in its `GATE_ID` fields (`gate_0_2_context_approval`, `gate_2_3_alignment_exhausted`, `gate_5_1_repo_test`, `gate_5_2_assembly_exhausted`). Additionally, `prepare_gate_prompt()` had no handlers for the missing gates.

3. **Unit completion command missing status write** (`test_unit_completion_command_writes_status_first`): Per Bug 11, the `unit_completion` `run_command` must write `COMMAND_SUCCEEDED` to `.svp/last_status.txt` before invoking `update_state.py`. The command was missing the `echo COMMAND_SUCCEEDED > .svp/last_status.txt &&` prefix.

4. **Hook schema test using pre-Bug-17 field names** (`test_hooks_json_schema_write_auth_path`, `test_hooks_json_schema_non_svp_path`): Tests accessed `entry["script"]` but Bug 17 changed the schema to nested `entry["hooks"][0]["command"]`.

5. **Game of Life template path resolution** (`test_gol_*`): `_load_gol()` resolved paths relative to `_REPO_ROOT` (parent of scripts dir). In workspace layout this is `src/unit_22/../examples/`. In delivered layout this is `svp/scripts/../` = `svp/`, but examples are at the repo root. Path resolution needed a fallback to `_REPO_ROOT.parent`.

**Pattern:** P1 (Cross-unit contract drift) + P3 (Path resolution fragility). **Prevention:** Tests must be run in the delivered repo layout during assembly validation, not just the workspace layout. Path resolution in modules that are relocated during assembly must account for both layouts. Gate ID registries must be kept in sync with route() — the existing Bug 19 regression test caught this.

---

### Bug 30 — README Carry-Forward Content Lost During Assembly

**Caught:** Post-delivery, human inspection of delivered README. **Test:** `test_bug18_readme_carry_forward.py`

The git repo agent rewrote the README from scratch instead of preserving the previous version's content. The SVP 2.0 README (166 lines, `references/README_v2.0.md`) was the carry-forward base. The delivered README (295 lines) was entirely rewritten — different structure, different installation instructions (cp instead of marketplace), missing configuration fields (`context_budget_override`, `compaction_character_threshold`), wrong license (Apache instead of MIT), inaccurate history descriptions.

The spec (Section 12.7) said "carry-forward artifact" for Mode A but did not explicitly define what carry-forward means: that the previous version's README is the base document, preserved in full, with only new-version sections added.

**Root cause:** The task prompt for the git repo agent did not include the reference README with explicit preserve-and-extend instructions. The agent treated README generation as a fresh authoring task rather than an incremental update.

**Fix:** (1) Fixed the delivered README to carry forward SVP 2.0 content. (2) Updated spec Section 12.7 to define carry-forward semantics explicitly. (3) Updated blueprint Unit 18 and Unit 9 to include the carry-forward rule. (4) Added General Principle 13.

**Pattern:** P7 (Spec completeness). The spec used the term "carry-forward" without defining what it means operationally. The agent faithfully followed a vague instruction by generating from scratch. **Prevention:** Carry-forward semantics must be defined explicitly: "preserve full content, add only new sections." Task prompts must include the reference artifact with explicit instructions. Regression test verifies reference content lines and headings are preserved.

---

### Bug 31 — Plugin Discovery Missing Cache Directory and JSON Validation

**Caught:** Post-delivery, human testing (launcher fails with "SVP plugin not found"). **Test:** `test_bug19_plugin_discovery_paths.py`

`_find_plugin_root()` was rewritten for SVP 2.0/2.1 and lost the marketplace cache directory scan (`~/.claude/plugins/cache/svp/svp/*/`), system-wide paths (`/usr/local/share/claude/plugins/svp/`, `/usr/share/claude/plugins/svp/`), and JSON-based validation. The 2.0/2.1 version only checked 2 locations (vs. 6 in 1.2.1). Additionally, `_is_svp_plugin_dir()` was changed from reading `plugin.json` and checking `name == "svp"` to a simple directory-existence check requiring `.claude-plugin` and `scripts` directories — both less correct (no content validation) and more restrictive (requires `scripts` at discovery time).

When the plugin is installed via the Claude Code marketplace, it lives at `~/.claude/plugins/cache/svp/svp/<version>/`, which was not searched. The launcher failed immediately with "SVP plugin not found" for all marketplace installations.

Fixed by restoring all search paths from 1.2.1 and JSON content validation. Updated stakeholder spec and blueprint to explicitly enumerate the required search paths and validation logic (previously stated as "unchanged from v1.0" without specifying the actual contract).

**Test details:** Validates `_is_svp_plugin_dir()` accepts valid plugin.json, rejects wrong name, rejects missing JSON, rejects nonexistent dirs, rejects dirs with `.claude-plugin` + `scripts` but no valid JSON. Validates `_find_plugin_root()` finds plugins in cache directory, env var takes precedence, direct install preferred over cache, returns None when no plugin found.

**Pattern:** P1 (Cross-unit contract drift) + P8 (Version upgrade regression). **Prevention:** When rewriting a function during a version upgrade, the implementation agent must consult the previous version's implementation to preserve all edge cases and search paths. Blueprint behavioral contracts must enumerate concrete values (search paths, validation rules), not just say "unchanged from vN." Specs must define plugin discovery paths explicitly so implementation agents cannot independently invent a reduced set.

### Bug 32 — Unnecessary `resume` Subcommand Regression

**Caught:** Post-delivery, human noticed UI change from v1.2.1. **Test:** (no dedicated regression test file)

The launcher introduced an explicit `svp resume` subcommand that did not exist in SVP 1.2.1. In the previous version, running `svp` with no arguments in a project directory auto-detected and resumed the project. The new `resume` subcommand added unnecessary UI complexity and broke the established workflow.

**Root cause:** The blueprint specified `_handle_resume` as a separate command handler. The spec did not explicitly define the CLI subcommand vocabulary, leaving the blueprint free to introduce new subcommands without constraint.

Fixed by removing the `resume` subcommand. Running `svp` with no arguments now auto-detects an existing project in the current directory (via `pipeline_state.json` presence) and resumes it. The spec now fixes the CLI vocabulary in Section 6.1.1: exactly three modes (`svp new`, bare `svp`, `svp restore`). No other subcommands may be introduced.

**Test details:** No dedicated regression test file. The fix is a spec-level constraint (CLI vocabulary is fixed) that prevents the blueprint from introducing additional subcommands.

**Pattern:** P7 (Spec completeness). **Prevention:** When a user-facing CLI surface exists, the spec must explicitly enumerate the complete subcommand vocabulary as a spec-level constraint. Without this, the blueprint author is free to invent new subcommands. Structural tests cannot catch this — the subcommand works correctly, it just should not exist.

---

### Bug 33 — Quality Gate Operation Path Not Qualified

**Caught:** Rebuild (SVP 2.1 building itself), Stage 3 Unit 1 Quality Gate A. **Test:** (no dedicated regression test file yet)

`run_quality_gate` in routing.py calls `resolve_command(toolchain, operation, params)` where `operation` is a relative path like `"formatter.check"` from the gate array. But `resolve_command` navigates from the toolchain root, so it looks for `toolchain["formatter"]["check"]` which doesn't exist — the actual path is `toolchain["quality"]["formatter"]["check"]`. The caller must prepend `"quality."` to produce the fully qualified path `"quality.formatter.check"`. Additionally, the params dict passed `"path"` as the key but the toolchain templates use `{target}` as the placeholder, causing a second resolution failure. The fallback `except` block then ran the operation string (`"formatter.check"`) as a literal shell command, producing `command not found`.

**Root cause:** The behavioral contract for `get_quality_gate_operations` says operations are "dotted paths that resolve to a command template within the quality section" but doesn't specify that the caller must qualify them before passing to `resolve_command`. The placeholder name mismatch (`{path}` vs `{target}`) is a cross-unit contract drift between the routing code and the toolchain schema.

**Pattern:** P1 (Cross-unit contract drift) + P3 (Implicit resolution assumption). **Prevention:** The spec must explicitly state: (1) gate operations are relative to the `quality` section and the caller must prepend `"quality."` before passing to `resolve_command`, or alternatively the operations in toolchain.json must be stored as fully qualified paths; (2) the placeholder vocabulary (`{target}`, `{env_name}`, etc.) must be a shared constant between the toolchain schema and all callers. Structural tests should verify that every gate operation, when qualified, resolves to a valid template in the toolchain.

---

### Bug 34 — Toolchain `--no-banner` Flag Incompatible with Conda 25.x

**Caught:** Rebuild (SVP 2.1 building itself), Stage 3 Unit 1 Quality Gate A. **Test:** (no dedicated regression test file yet)

The toolchain.json `run_prefix` template included `--no-banner` which was a conda flag removed in conda 25.x. Every command using `{run_prefix}` failed with `unrecognized arguments: --no-banner`.

**Root cause:** The toolchain template was written for an older conda version and never validated against the target environment. No version compatibility check exists for toolchain commands.

**Pattern:** P7 (Spec completeness). **Prevention:** The toolchain.json templates should not include version-specific flags that may not be portable. The spec should note that `run_prefix` must use only universally supported conda flags. Alternatively, a toolchain validation step could test-run the `run_prefix` against the actual environment.

---

### Bug 35 — Routing Script Emits Unresolved `{env_name}` in COMMAND Output

**Caught:** Rebuild (SVP 2.1 building itself), Stage 3 Unit 1 test execution. **Test:** (no dedicated regression test file yet)

The routing script outputs `COMMAND: python scripts/run_tests.py --test-path tests/unit_1/ --env-name {env_name} --project-root .` with the literal placeholder `{env_name}` unresolved. The orchestration layer must then guess or hardcode the value. The routing script has access to `pipeline_state.project_name` and `derive_env_name` but doesn't use them to resolve the placeholder before emitting the command.

**Root cause:** The COMMAND template in the routing function uses `{env_name}` as a placeholder but the `route()` function doesn't perform placeholder resolution on its output before returning it to the orchestration layer.

**Pattern:** P3 (Implicit resolution assumption). **Prevention:** The spec must state that routing output must contain only fully resolved values — no placeholders may appear in the ACTION or COMMAND fields returned to the orchestration layer. The routing function must resolve `{env_name}` via `derive_env_name(state.project_name)` before emitting the command string. Structural tests should verify that routing output contains no unresolved `{...}` placeholders.

---

### Bug 36 — Stub Generation Missing from Stage 3 Routing Cycle

**Caught:** Rebuild (SVP 2.1 building itself), Stage 3 Unit 1 red run attempt. **Test:** (no dedicated regression test file yet)

The Stage 3 per-unit cycle in Section 10.0 lists steps 1 (test generation) through 10 (unit completion) but does not include stub generation as a step. Section 10.2 describes stub generation (deterministic script, reads Tier 2 signatures, generates `raise NotImplementedError` bodies), and Unit 6 in the blueprint implements the Stub Generator. However, stub generation was never wired into the routing cycle. The sub-stage sequence goes directly from `test_generation` to `quality_gate_a` to `red_run` with no `stub_generation` sub-stage.

Without stubs, the red run fails with `ModuleNotFoundError` (collection error) instead of test failures, because the test file imports from `src/unit_N/stub.py` which doesn't exist. During the rebuild, stubs had to be created manually.

**Root cause:** Section 10.0's cycle overview omits stub generation. Section 10.2 describes it as a concept but the cycle overview, routing sub-stage sequence, and routing script all skip it. The routing script has `"stub_generation"` in its valid phases set but never routes to it.

**Pattern:** P7 (Spec completeness). **Prevention:** The spec's cycle overview (Section 10.0) must be the authoritative and complete sequence. Every operation described in Sections 10.1 through 10.13 must appear as a numbered step in the overview. The routing sub-stage sequence must include every step from the overview. Structural tests must verify that the routing script handles every sub-stage listed in the cycle overview.

---

## Part 2: Pattern Catalog

### P1 — Cross-Unit Contract Drift
**Instances:** Bugs 1, 3, 5, 6, 7, 8, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 28, 29, 31, 33, 37, 38, 40, 41, 43 (25 of 43 bugs).
Two units must agree on something. The implementation agent misses the detail. **Prevention:** Structural (AST-based) tests at every cross-unit boundary.

### P2 — State Management Assumptions
**Instances:** Bugs 2, 11, 12, 20, 42.
A transition function assumes a precondition or forgets a reset. **Prevention:** Exhaustive post-conditions for ALL fields. Multi-step sequence tests.

### P3 — Implicit Resolution Assumption
**Instances:** Bugs 13, 24, 29, 33, 35.
A value (path, state field, configuration) is assumed to resolve correctly in a context where it does not. Bug 13: a path resolves in one context but not another. Bug 24: a state field is assumed to be set, but the current step is the producer, not a consumer. **Prevention:** Document resolution context for paths. Document producer/consumer roles for state fields. Validate values against `None` explicitly, not via `dict.get()` defaults. Test with the actual state that exists at each pipeline step.

### P4 — Framework Dependency Completeness
**Instances:** Bug 9.
Extraction handles common case but misses always-needed packages. **Prevention:** Separate extracted from framework deps. Toolchain lists authoritative. Test with empty inputs.

### P5 — Error Classification Precision
**Instances:** Bug 10.
Broad indicator matches both target and expected conditions. **Prevention:** Enumerate positive indicators. Include true negatives in tests.

### P6 — Status Line Matching Inconsistency
**Instances:** Bug 14.
Two dispatchers use different matching strategies for the same format. **Prevention:** Specify strategy as cross-cutting contract. Test with/without trailing context.

### P7 — Spec Completeness
**Instances:** Bugs 15, 28, 30, 32, 34, 36, 38, 39, 41, 43 (10 of 43 bugs).
Spec enumeration is incomplete or terminology is undefined; implementation faithfully follows the gap. **Prevention:** Structural tests verify enumerations. Path coverage checks. Validation steps must cover all prescribed structural properties, including commit ordering. Terms like "carry-forward" must be defined operationally, not assumed.

### P8 — Version Upgrade Regression
**Instances:** Bug 31.
A function is rewritten during a version upgrade and loses edge cases, search paths, or validation logic from the previous version. The implementation agent generates fresh code without consulting the prior implementation. **Prevention:** When a blueprint says "unchanged from vN," the blueprint must enumerate the actual contract (paths, values, validation rules) so the implementation agent cannot independently reinvent a reduced version. The prior version's implementation should be included in the task prompt for any function marked as "unchanged" or "carried forward."

---

## Part 3: General Principles

1. **Every cross-unit interface needs a structural test.** P1 is the most common pattern (24 of 42 bugs). AST-based tests are the primary defense.
2. **State transitions need exhaustive post-conditions.** Not just the primary field but every secondary field that should reset.
3. **Error classifiers need negative test cases.** Expected-during-normal-operation patterns are the most dangerous false positives.
4. **Path strings must be verified against resolution context.** Works in dev, fails at runtime.
5. **Vocabulary constants must be shared, not duplicated.** Single source of truth for any string two components agree on.
6. **Spec enumerations must be verified by structural tests.** The spec can be wrong too.
7. **Spec-level bugs are the hardest to catch.** Everything downstream faithfully implements omissions.
8. **Shared structural patterns must be defined once.** Inconsistent application across scripts is a leading cause of drift.
9. **Platform integration schemas must be tested against the platform's actual validator.** A configuration that looks structurally reasonable can fail silently if field names or nesting don't match the host platform's expectations. Test for successful load, not just structural plausibility.
10. **Dead code adjacent to a gap is a diagnostic signal.** When helper functions exist but are never called from the main code path, they likely represent intended-but-unconnected functionality. Structural tests should verify call site connectivity for all non-test helper functions.
11. **State field producer/consumer roles must be explicit.** When a pipeline step derives a value and writes it to state, that step is the producer. No step should read a state field before its producer has run. `dict.get(key, default)` does not guard against explicit `None` values -- validate against `None` explicitly.
12. **Canonical derivation functions must not be reimplemented independently.** When a function exists to derive a value (e.g., `derive_env_name`), all components that need that value must use the canonical function or receive the pre-derived value in their inputs. Agents that independently re-derive values will drift from the canonical logic.
13. **Carry-forward artifacts must be preserved, not rewritten.**
14. **Dual-copy artifacts must be synchronized as part of every fix.** When an artifact exists in both the workspace and the delivered repository, any fix that modifies one copy must propagate to the other. The formal debug loop handles this via Stage 5 reassembly, but direct fixes bypass the loop. The spec must enumerate all dual-copy artifacts and require sync verification.
15. **"Unchanged from vN" must enumerate the actual contract.** When a blueprint marks a behavioral contract as "unchanged," it must still specify the concrete values (search paths, validation logic, error handling). Saying "unchanged" without enumeration allows implementation agents to independently reinvent a reduced version that drops edge cases. The prior version's implementation should be provided as reference material for any function carried forward across versions. When a previous version's artifact (README, config, etc.) is provided as a reference, the agent must use it as the base document and add only new content. Rewriting from scratch loses accumulated detail — installation instructions, configuration fields, command descriptions, history — that was refined over multiple releases. The task prompt must explicitly state "preserve and extend" rather than "generate."
16. **Stub files must carry a machine-detectable sentinel.** Every stub generated by the stub generator must contain `__SVP_STUB__ = True` as a module-level constant. Structural validation must scan for this sentinel in all delivered files. A stub delivered to the final repository is a silent failure — it passes all structural checks except a sentinel scan, and only fails when the human runs tests. The sentinel converts a late-detected failure into an early-detected one with zero token cost.
17. **Accumulated failure knowledge must feed upstream prevention, not only reactive triage.**
18. **Gate registrations must be consistent across all modules.** Every gate ID that appears in routing dispatch tables (`GATE_RESPONSES`) must also appear in gate preparation registries (`ALL_GATE_IDS`). Every stage's routing function must implement the two-branch pattern (check `last_status.txt` before re-invoking an agent). Structural tests must verify both invariants — a gate that exists in one registry but not the other is a silent failure that only surfaces when the gate is actually needed. The lessons learned pattern catalog (P1-P8+) represents the highest-value architectural knowledge in the SVP system. Feeding it to the blueprint checker (advisory risk assessment at Stage 2) and to the test agent (unit-specific historical failure context at Stage 3) converts reactive debugging records into proactive design guidance. The filtering must be deterministic — no LLM involvement in deciding which entries are relevant.

19. **In-memory state transitions must be persisted before crossing action cycle boundaries.** When `route()` calls a state transition function and then recursively routes to produce an action block, the intermediate state exists only in memory. The POST command (`update_state.py`) loads state from disk independently. If the intermediate state is not saved to disk before the action block is returned, the POST command will operate on stale state. Every in-memory state transition in `route()` that precedes a recursive call or action block return must be followed by `save_state()`.

---

## Regression Test File Mapping

| Bug | Regression Test File | Category |
|-----|---------------------|----------|
| 1 | (unit test assertions) | Blueprint-era |
| 2 | (unit test assertions) | Blueprint-era |
| 3 | (unit test assertions) | Blueprint-era |
| 4 | (unit test assertions) | Blueprint-era |
| 5 | (unit test assertions) | Blueprint-era |
| 6 | `test_bug2_wrapper_delegation.py` | Post-delivery |
| 7 | `test_bug3_cli_argument_contracts.py` | Post-delivery |
| 8 | `test_bug4_status_line_contracts.py` | Post-delivery |
| 9 | `test_bug5_pytest_framework_deps.py` | Post-delivery |
| 10 | `test_bug6_collection_error_classification.py` | Post-delivery |
| 11 | `test_bug7_unit_completion_status_file.py` | Post-delivery |
| 12 | `test_bug8_sub_stage_reset_on_completion.py` | Post-delivery |
| 13 | `test_bug9_hook_path_resolution.py` | Post-delivery |
| 14 | `test_bug10_agent_status_prefix_matching.py` | Post-delivery |
| 15 | `test_bug11_delivered_repo_artifacts.py` | Post-delivery |
| 16 | `test_bug12_cmd_main_guards.py` | Post-delivery |
| 17 | `test_bug13_hook_schema_validation.py` | Post-delivery |
| 18 | `test_bug14_routing_action_block_commands.py` | Build-time |
| 19 | `test_bug15_gate_prepare_flag_mismatch.py` | Build-time |
| 20 | `test_bug16_same_file_copy_guard.py` | Build-time |
| 21 | `test_bug17_routing_gate_presentation.py` | Build-time |
| 22 | `test_bug18_stakeholder_spec_filename.py` | Build-time |
| 23 | `test_bug19_alignment_check_routing.py` | Build-time |
| 24 | `test_bug20_total_units_derivation.py` | Build-time |
| 25 | `test_bug21_stage3_sub_stage_routing.py` | Build-time |
| 26 | `test_bug17_stage5_repo_assembly_routing.py` | Post-delivery |
| 27 | (manual verification) | Post-delivery |
| 28 | (manual verification) | Post-delivery |
| 29 | (existing regression tests) | Post-delivery |
| 30 | `test_bug18_readme_carry_forward.py` | Post-delivery |
| 31 | `test_bug19_plugin_discovery_paths.py` | Post-delivery |
| 32 | (no dedicated regression test file) | Rebuild preparation |
| 33 | (unit test: Unit 10 `run_quality_gate`) | Rebuild |
| 34 | (unit test: Unit 22 toolchain template) | Rebuild |
| 35 | (unit test: Unit 10 `route()` output) | Rebuild |
| 36 | (unit test: Unit 10 `route()` dispatch) | Rebuild |
| 37 | `test_bug22_repo_sibling_directory.py` | Post-delivery (2.1 rebuild) |
| 38 | (structural test required) | Post-delivery (2.1 rebuild) |
| 39 | (structural test required) | Post-delivery (2.1 rebuild) |
| 40 | (structural test required) | Post-delivery (2.1 rebuild) |
| 41 | `test_bug23_stage1_spec_gate_routing.py` | Post-delivery (2.1 rebuild) |

| 42 | `test_bug42_pre_stage3_state_persistence.py` | Post-delivery (2.1 rebuild) |

Note: Regression test file names (test_bug2 through test_bug42) use either the original post-delivery numbering or the unified catalog numbering. This document's unified Bug 1-42 numbering includes blueprint-era, post-delivery, and rebuild preparation bugs chronologically. The mapping table provides the cross-reference.

---

### Bug 37 — Delivered Repo Created Inside Workspace Instead of as Sibling

**Caught:** Post-delivery, human Gate 5.1 review. **Test:** `test_bug22_repo_sibling_directory.py`

The git repo agent created the delivered repository inside the project workspace (`projectname/projectname-repo/`) instead of as a sibling directory (`projectname-repo/` alongside the workspace). Spec Section 12.1 explicitly states "at the same level as the project workspace," but this instruction was never relayed to the agent definition.

The `GIT_REPO_AGENT_MD_CONTENT` string in Unit 18 contained no instruction about where to create the repository. The agent defaulted to creating it relative to the current working directory (the workspace root), placing it inside the workspace.

Fixed by adding a "Repository Location" section to the git repo agent definition (`GIT_REPO_AGENT_MD_CONTENT` in Unit 18) explicitly instructing the agent to create the repo as a sibling directory. Updated the blueprint's Unit 18 Tier 3 behavioral contract to include the location requirement.

**Pattern:** P1 (Cross-unit contract drift). The spec had the correct requirement (Section 12.1), but the agent definition in Unit 18 — the behavioral instructions that the agent actually reads — omitted it. The spec and the agent definition must agree on delivery requirements; agents do not read the spec directly.

**Prevention:** Agent definition review should check every spec requirement that falls within the agent's scope and verify it appears in the agent's behavioral instructions. The git repo agent definition is the "last mile" for delivery requirements — any delivery instruction in the spec that is not in the agent definition will be lost.

---

### Bug 38 — Group B Command Definitions Missing Action Cycle Steps

**Caught:** Post-delivery, human invocation of `/svp:redo`. **Test:** (structural test required)

All five Group B slash command definitions (`help.md`, `hint.md`, `ref.md`, `redo.md`, `bug.md`) stopped after step 2 (spawn the agent). Steps 3-5 were missing: write the agent's terminal status to `.svp/last_status.txt`, run `update_state.py --phase <phase>` with the correct phase, re-run the routing script. The main session had no source for the correct `--phase` value and failed with `ValueError: Unknown phase: redo_agent` after guessing wrong.

**Root cause:** The spec (Section 13) defined Group B as "invoke prepare_task.py then spawn subagent" but did not require the command definitions to include the remaining action cycle steps. The blueprint's Unit 20 Tier 3 contract said "instruct the main session to run prepare_task.py, then spawn the appropriate subagent" — matching the spec's incomplete description. The implementation faithfully reproduced the incomplete contract.

**Pattern:** P1 (Cross-unit contract drift) + P7 (Spec completeness). The spec defined the action cycle in Section 3.6 but did not connect it to the Group B command definitions in Section 13. The blueprint replicated the gap. **Prevention:** Command definitions are action blocks — they must include the complete cycle. Structural tests must verify that every Group B `*_MD_CONTENT` string contains `update_state.py --phase` with a valid phase value.

---

### Bug 39 — Orchestration Skill Missing Slash-Command Cycle Guidance

**Caught:** Post-delivery, concurrent with Bug 38. **Test:** (structural test required)

The orchestration skill (`SKILL.md`) described only the routing-script-driven action cycle. It did not explain that Group B slash commands bypass the routing script and the command definition substitutes for the action block. When Bug 38's incomplete command definitions left the main session without explicit instructions, the skill provided no fallback guidance for slash-command-initiated cycles.

**Root cause:** The blueprint's Unit 21 Tier 3 contract listed "six-step action cycle, action type handling, status line construction, gate presentation rules, session boundary handling" but did not include slash-command-initiated cycles as a required topic. The skill was complete for routing-script-driven operations but silent on human-initiated commands.

**Pattern:** P7 (Spec completeness). **Prevention:** The orchestration skill must cover every entry point into the action cycle, not just the routing script. Group B commands are an alternative entry point that follows the same cycle with different initialization.

---

### Bug 40 — Artifact Synchronization Not Enforced Between Workspace and Delivered Repo

**Caught:** Post-delivery, during Bug 38/39 fix application. **Test:** (structural test required)

When Bugs 38 and 39 were fixed by editing workspace files (`src/unit_20/stub.py`, `scripts/orchestration_skill.py`, spec, and ancillary docs), the corresponding copies in the delivered repository were not automatically updated. The delivered repo had stale versions of: `svp/scripts/slash_command_files.py`, `svp/scripts/orchestration_skill.py`, `svp/skills/orchestration/SKILL.md`, `docs/stakeholder_spec.md`, `docs/blueprint_prose.md`, `docs/blueprint_contracts.md`, `docs/references/svp_2_1_summary.md`, `docs/references/svp_2_1_baseline.md`, `docs/references/svp_2_1_lessons_learned.md`. The drift was only caught because the human explicitly asked "is all the rest in sync?"

**Root cause:** The spec (Section 12.17.6) prescribes "full Stage 5 repo reassembly" as the sync mechanism after a debug fix, but this only applies to the formal agent-driven debug loop. When fixes are applied directly by the main session outside the formal loop, there is no mechanism — no checklist, no structural test, no hook — that enforces synchronization of dual-copy artifacts. The spec did not enumerate which artifacts have dual copies or require the main session to propagate changes.

**Pattern:** P1 (Cross-unit contract drift). **Prevention:** The spec must enumerate all dual-copy artifacts and require synchronization as part of every fix, regardless of whether the formal reassembly pipeline runs. A structural test should verify that workspace source files and their delivered counterparts are identical (or that delivered `.md` files match their `*_CONTENT` constants).

---

### Bug 41 — Stage 1 Routing Missing Two-Branch Check and Gate Registration

**Caught:** Post-delivery, during `/svp:redo` spec revision. **Test:** `test_bug23_stage1_spec_gate_routing.py`

Stage 1 routing unconditionally invokes `stakeholder_dialog` with no two-branch check on `last_status.txt`. When the stakeholder dialog agent completes (`SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`), the next routing call re-invokes the agent instead of presenting Gate 1.1 for human approval. Additionally, `gate_1_1_spec_draft` and `gate_1_2_spec_post_review` exist in `GATE_RESPONSES` (routing.py) but are not registered in `ALL_GATE_IDS` (prepare_task.py), so `prepare_gate_prompt()` raises `ValueError: Unknown gate ID` when the gate is manually triggered.

**Root cause:** The spec's two-branch routing invariant (Section 3.6, Constraint 9) explicitly lists Stage 1 as requiring this pattern, but the blueprint and implementation did not apply it to Stage 1. The `ALL_GATE_IDS` list in prepare_task.py was incomplete — it included Stage 0, 2, 5, and 6 gates but omitted Stage 1 and Stage 2 pre-alignment gates. The routing code for Stage 1 (unlike Stages 0, 2, 3, 5) had no sub-stage tracking and no `last_status.txt` check.

**Pattern:** P7 (Spec completeness) + P1 (Cross-unit contract drift). The spec defined the two-branch invariant correctly and even enumerated Stage 1 as covered, but no structural test verified that Stage 1 routing actually implemented the pattern (P7). The `ALL_GATE_IDS` gap between routing.py's `GATE_RESPONSES` and prepare_task.py's `ALL_GATE_IDS` is a classic cross-unit contract drift (P1).

**Prevention:** A structural test must verify: (1) every gate ID in `GATE_RESPONSES` is also in `ALL_GATE_IDS`; (2) every stage's routing function checks `last_status.txt` before re-invoking an agent (the two-branch pattern). The spec must explicitly require that Stage 1 uses sub-stages (`stakeholder_spec_authoring`, `spec_review`) with the same two-branch pattern as Stage 0.

---

### Bug 42 — Pre-Stage-3 Reference Indexing Overwrites Alignment Status

**Caught:** Post-delivery, during alignment-to-stage-3 transition. **Test:** `test_bug42_pre_stage3_state_persistence.py`

After the blueprint checker confirms alignment (`ALIGNMENT_CONFIRMED`), the pipeline presents Gate 2.2 to the human. When the human selects APPROVE at Gate 2.2, `route()` calls `complete_alignment_check()` to advance the in-memory state to `pre_stage_3`, then recursively calls `route()` which returns the reference indexing action block. However, the intermediate `pre_stage_3` state is never saved to disk. When the reference indexing agent completes and `update_state.py` runs, it loads the old state from disk (`stage=2, sub_stage=alignment_check`). The agent's `INDEXING_COMPLETE` status overwrites the previous status in `last_status.txt`. On the next routing call, the alignment check branch falls into the `else` branch and re-invokes the blueprint checker -- creating an infinite loop.

Additionally, `dispatch_agent_status` for `reference_indexing` unconditionally returned `state` without advancing the pipeline from `pre_stage_3` to stage 3.

**Root cause:** Two state management gaps: (1) `route()` performed an in-memory state transition via `complete_alignment_check()` (triggered by Gate 2.2 APPROVE) but relied on the recursive action block's POST command (`update_state.py`) to persist the result -- but `update_state.py` loads state from disk independently, so the in-memory transition was lost. (2) `dispatch_agent_status` for `reference_indexing` was a no-op (`return state`), so even if the state had been persisted correctly, the pipeline would never advance from `pre_stage_3` to stage 3.

**Pattern:** P2 (State Management Assumptions). The routing function assumed that an in-memory state transition would survive across the action cycle boundary (agent invocation, POST command execution), but `update_state.py` loads state from disk -- it does not receive the in-memory state object. The dispatch handler assumed some other component would advance the state from `pre_stage_3`, but no component did.

**Prevention:** (1) Any `route()` branch that performs an in-memory state transition and then recursively routes must persist the intermediate state to disk before returning the action block. Structural tests should verify that every `complete_*` or `advance_*` call in `route()` is followed by a `save_state()` call. (2) Every agent type in `dispatch_agent_status` must explicitly handle its success status line with a state transition -- a bare `return state` is only valid when the agent's completion does not require a stage/sub-stage change.

---

### Bug 43 — Systemic Two-Branch Routing Invariant Violation Across Multiple Stages

**Caught:** Post-delivery, during Stage 2 blueprint draft cycle. Subsequent audit revealed the same bug in Stage 4, Stage 5, redo profile sub-stages, and the debug loop. **Test:** `test_bug43_stage2_blueprint_routing.py`

The two-branch routing invariant (spec Section 3.6) was only applied to Stages 0, 1, and the Stage 2 alignment check. Every other agent-to-gate transition was missing the `last_status.txt` check:

1. **Stage 2, blueprint dialog** (`sub_stage=None`): Always re-invoked `blueprint_author` instead of presenting Gate 2.1 after `BLUEPRINT_DRAFT_COMPLETE`.
2. **Stage 4**: Always invoked `integration_test_author` instead of running the integration test suite after `INTEGRATION_TESTS_COMPLETE`.
3. **Stage 5** (`sub_stage=None`): Always invoked `git_repo_agent` instead of presenting Gate 5.1 after `REPO_ASSEMBLY_COMPLETE`.
4. **Redo profile sub-stages** (`redo_profile_delivery`, `redo_profile_blueprint`): Always invoked `setup_agent` instead of presenting Gate 0.3r after `PROFILE_COMPLETE`.
5. **Debug loop triage**: Always invoked `bug_triage` instead of presenting Gate 6.2 after `TRIAGE_COMPLETE` or Gate 6.4 after `TRIAGE_NON_REPRODUCIBLE`.

Additionally, 9 gate IDs were missing from `ALL_GATE_IDS` in `prepare_task.py` and had no gate prompt handlers: `gate_2_1_blueprint_approval`, `gate_2_2_blueprint_post_review`, `gate_3_1_test_validation`, `gate_3_2_diagnostic_decision`, `gate_4_1_integration_failure`, `gate_4_2_assembly_exhausted`, `gate_6_0_debug_permission`, `gate_6_1_regression_test`, `gate_6_2_debug_classification`, `gate_6_3_repair_exhausted`, `gate_6_4_non_reproducible`.

**Root cause:** The two-branch routing invariant was applied incrementally as bugs were discovered (Bug 21 for Stage 0, Bug 41 for Stage 1) rather than universally. Each fix addressed only the stage where the bug was observed, leaving all other stages unprotected. The spec defined the invariant with an exhaustive enumeration of all affected sub-stages, but the implementation applied it piecemeal.

**Pattern:** P7 (Spec completeness) + P1 (Cross-unit contract drift). The spec correctly enumerated all affected sub-stages in Section 3.6, but no structural test verified universal compliance. The `ALL_GATE_IDS` list was never validated against the complete `GATE_VOCABULARY` in routing.py, allowing 11 gate IDs to exist in routing but not in preparation.

**Prevention:** (1) A structural regression test must verify that EVERY entry in Section 3.6's exhaustive list has a corresponding two-branch check in `route()`. The test must fail if a new gate-presenting or command-presenting entry is added to the spec without a routing-level check. (2) A cross-unit consistency test must verify that every key in `GATE_VOCABULARY` (routing.py) appears in `ALL_GATE_IDS` (prepare_task.py) and has a gate prompt handler. The regression test `test_bug43_stage2_blueprint_routing.py` covers both requirements with 17 tests.

---

### Bug 44 — dispatch_agent_status null sub_stage for test_agent

**Caught:** Post-delivery (SVP 2.1 build). **Test:** `tests/regressions/test_bug44_null_substage_dispatch.py`

Stage 3 routing normalizes `sub_stage=None` to `test_generation` for routing purposes, but `dispatch_agent_status` for `test_agent` only checked `state.sub_stage == "test_generation"`. When the test agent completed with `TEST_GENERATION_COMPLETE` and `sub_stage` was still `None`, the dispatch didn't match, causing an infinite routing loop re-invoking the test agent.

**Root cause:** The routing function and the dispatch function had different assumptions about sub_stage normalization. Routing treated `None` as equivalent to `test_generation`, but dispatch required the literal string.

**Pattern:** P1 (Cross-unit contract drift). The routing and dispatch functions are in the same file but have inconsistent null-handling contracts.

**Prevention:** Dispatch handlers must accept the same sub_stage values that routing normalizes to. When routing treats `None` as equivalent to a named sub_stage, the dispatch must also handle `None`.

---

### Bug 45 — dispatch_command_status for test_execution doesn't advance sub_stage

**Caught:** Post-delivery (SVP 2.1 build). **Test:** `tests/regressions/test_bug45_test_execution_dispatch.py`

`dispatch_command_status` for phase `test_execution` returned `state` unchanged for all three status lines (`TESTS_PASSED`, `TESTS_FAILED`, `TESTS_ERROR`). After the red run (sub_stage `red_run`), `TESTS_FAILED` should advance to `implementation`. After the green run (sub_stage `green_run`), `TESTS_PASSED` should advance to `coverage_review`. Without these transitions, the routing script kept re-running tests in an infinite loop.

**Root cause:** The dispatch was a no-op placeholder that was never filled in with actual state transitions.

**Pattern:** P2 (State management assumptions). The dispatch assumed routing would handle advancement, but routing delegates to dispatch via update_state.py.

**Prevention:** Every dispatch handler must produce a state transition for the expected outcome. No-op returns are only valid for slash-command agents.

---

### Bug 46 — dispatch_agent_status for coverage_review doesn't advance to unit_completion

**Caught:** Post-delivery (SVP 2.1 build). **Test:** `tests/regressions/test_bug46_coverage_dispatch.py`

`dispatch_agent_status` for `coverage_review` returned `state` unchanged. After `COVERAGE_COMPLETE`, the sub_stage should advance to `unit_completion`. Without this, routing re-invoked the coverage review agent infinitely.

**Root cause:** Same as Bug 45 — the dispatch was a no-op placeholder.

**Pattern:** P2 (State management assumptions). Same as Bug 45.

**Prevention:** Same as Bug 45. The exhaustive dispatch invariant (spec Section 3.6) should have caught this — every main-pipeline agent type must explicitly advance state.

---

### Bug 47 — unit_completion action embeds state update in COMMAND causing double dispatch

**Caught:** Post-delivery (SVP 2.1 build). **Test:** `tests/regressions/test_bug47_unit_completion_double_dispatch.py`

The `unit_completion` routing action embedded `python scripts/update_state.py --phase unit_completion --unit N` inside the COMMAND string, AND also had a POST command that called `update_state.py --phase unit_completion --unit N`. This caused `complete_unit(N)` to be called twice — the first call advanced `current_unit` to N+1, and the second call raised `TransitionError` because unit N was no longer the current unit.

**Root cause:** The COMMAND was designed as a compound shell command that both wrote the status file AND ran the state update, but the POST was also generated as normal. The two mechanisms conflict.

**Pattern:** P1 (Cross-unit contract drift). The COMMAND and POST fields have overlapping responsibilities.

**Prevention:** COMMAND should never embed state update calls. State updates are exclusively the responsibility of POST commands. The COMMAND should only produce output/status; POST handles state transitions.

---

*End of lessons learned.*
