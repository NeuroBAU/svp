# SVP 2.1 — Lessons Learned

**Date:** 2026-03-15
**Source material:** Regression tests from `tests/regressions/`, unit test suites, and build tool observations across SVP 1.0 through 2.0. Bugs 17-25 discovered during SVP 2.1 pre-build inspection and early build. Bugs 26-30 discovered post-delivery (assembly and carry-forward regressions). Bugs 31-32 discovered during rebuild preparation (plugin discovery regression, CLI vocabulary regression). Bugs 33-36 discovered during SVP 2.1 rebuild (bootstrapping: SVP 2.1 building itself). Bugs 37-41 discovered post-delivery during SVP 2.1 rebuild (repo location, command definitions, skill guidance, artifact synchronization, Stage 1 routing). Bug 42 discovered post-delivery (pre-stage-3 state persistence and reference indexing advancement). Bug 43 discovered post-delivery during SVP 2.1 rebuild (Stage 2 blueprint routing missing two-branch check). Bugs 44-47 discovered post-delivery (SVP 2.1 build: Stage 3 dispatch and unit_completion routing). Bug 48 discovered post-delivery (launcher CLI contract loss). Bug 49 discovered post-delivery (systemic bare argparse stubs across 5 units). Bug 50 discovered post-delivery (insufficient contract specificity and boundary violations in blueprint). Bug 51 discovered post-delivery (debug loop missing reassembly routing after repair). Bug 54 discovered post-delivery (orphaned hollow function update_state_from_status). Bug 55 discovered post-delivery (rollback_to_unit and set_debug_classification never wired into dispatch). Bug 56 discovered post-delivery (spec structural gaps: downstream dependency analysis and contract granularity rules). Bug 57 discovered post-delivery (review enforcement: baked dependency and contract checklists into reviewer agent definitions). Bug 58 discovered post-delivery (Gate 5.3 missing from GATE_VOCABULARY; comprehensive summary document update). Bug 59 discovered post-delivery (stale blueprints/ directory, critical implementation bugs, stakeholder spec gaps). Bug 60 discovered post-delivery (broken _get_unit_context path and stale fallback ARTIFACT_FILENAMES). Bug 61 discovered post-delivery (missing include_tier1 parameter in _get_unit_context and build_unit_context). Bug 62 discovered post-delivery (selective blueprint loading not wired per agent matrix). Bug 63 discovered post-delivery (documentation retrofit for Bugs 60-62). Bug 64 discovered post-delivery (11 unit test failures from stale assertions after Bugs 59-62 code changes). Bug 65 discovered post-delivery (Stage 3 error-handling infrastructure entirely unimplemented: 9 findings covering stub_generation routing, fix ladder engagement, diagnostic escalation, Gate 3.1/3.2 dispatch, coverage two-branch, red_run retries). Bug 71 discovered post-delivery (structural completeness test suite automating 14 systematic bug-finding techniques; found Stage 4 gate routing gap and TESTS_FAILED dispatch gap). Bug 72 discovered post-delivery (generalized structural completeness checking: four-layer defense system with project-agnostic AST scanner, agent prompt updates, and routing integration).
**Document status:** Living document. Updated by the bug triage agent during post-delivery debug sessions (Section 12.17, Step 6).

---

## Purpose

This document converts debugging knowledge into forward-looking guidance for the blueprint author. Each bug is analyzed for its root cause pattern. Each pattern produces concrete prevention rules.

The blueprint author should consult this document during unit design. The blueprint checker should use the pattern catalog to anticipate failure modes.

This document is updated during post-delivery debug sessions. When `/svp:bug` resolves a logic bug, the triage agent appends a new entry to the bug catalog (Part 1), updates the pattern catalog (Part 2) if a new pattern is identified, and updates the regression test file mapping. The format of new entries must match the established catalog structure: bug number, caught-by, test file, description, root cause pattern, and prevention rule.

---

## Part 1: Unified Bug Catalog (Bugs 1-80)

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
**Instances:** Bugs 1, 3, 5, 6, 7, 8, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 28, 29, 31, 33, 37, 38, 40, 41, 43, 44, 47, 48, 49, 51, 52, 53, 54, 55, 56, 58, 64, 65, 66, 67, 68, 69 (42 of 80 bugs).
Two units must agree on something. The implementation agent misses the detail. **Prevention:** Structural (AST-based) tests at every cross-unit boundary.

### P2 — State Management Assumptions
**Instances:** Bugs 2, 11, 12, 20, 42.
A transition function assumes a precondition or forgets a reset. **Prevention:** Exhaustive post-conditions for ALL fields. Multi-step sequence tests.

### P3 — Implicit Resolution Assumption
**Instances:** Bugs 13, 24, 29, 33, 35, 60, 61.
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
**Instances:** Bugs 15, 28, 30, 32, 34, 36, 38, 39, 41, 43, 48, 49, 50, 62, 65 (15 of 80 bugs).
Spec enumeration is incomplete or terminology is undefined; implementation faithfully follows the gap. **Prevention:** Structural tests verify enumerations. Path coverage checks. Validation steps must cover all prescribed structural properties, including commit ordering. Terms like "carry-forward" must be defined operationally, not assumed.

### P8 — Version Upgrade Regression
**Instances:** Bug 31.
A function is rewritten during a version upgrade and loses edge cases, search paths, or validation logic from the previous version. The implementation agent generates fresh code without consulting the prior implementation. **Prevention:** When a blueprint says "unchanged from vN," the blueprint must enumerate the actual contract (paths, values, validation rules) so the implementation agent cannot independently reinvent a reduced version. The prior version's implementation should be included in the task prompt for any function marked as "unchanged" or "carried forward."

### P9 — Spec Structural Gap
**Instances:** Bugs 56, 57, 65, 66, 67, 68, 69.
The spec provides a principle but not the granularity rules needed to operationalize it. Reviewers and checkers have no structural criteria to verify, so they cannot catch the gap. **Prevention:** Spec principles must be accompanied by enumerated verification criteria. Review agents must carry mandatory checklists derived from these criteria.

### P10 — Error-Path Contract Omission (NEW — Bug 65, EXPANDED — Bugs 66-69)
**Instances:** Bugs 65, 66, 67, 68, 69.
Happy-path transitions are contracted and tested; error paths are described in spec prose but never converted to enumerable blueprint Tier 3 contracts. The implementation agent faithfully implements the contracted happy paths and produces no-op stubs for the uncontracted error paths, resulting in infinite loops on any failure. **Prevention:** Every dispatch function's (phase, sub_stage, status) combination must have a contracted behavior -- including error cases. Per-gate-option dispatch contracts must be applied strictly. Regression tests must cover error-path dispatch completeness.

---

## Part 3: General Principles

1. **Every cross-unit interface needs a structural test.** P1 is the most common pattern (42 of 80 bugs). AST-based tests are the primary defense.
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

20. **Error-path dispatch contracts must be as exhaustive as happy-path contracts.** Every (phase, sub_stage, status) combination in `dispatch_command_status` and `dispatch_agent_status` must have a contracted behavior. A `return state` for a status that requires pipeline advancement is a bug. Per-gate-option dispatch contracts must specify the exact state transition for every response option -- no-ops are valid only when the gate response genuinely does not change pipeline state.

21. **Every gate in GATE_VOCABULARY must be route()-reachable, and every response must produce a state transition.** Bugs 65-69 demonstrated that every stage independently had dead gates or no-op dispatches (P10 pattern). The spec now requires a gate reachability invariant: structural tests must verify that every gate is reachable from route() for at least one valid pipeline state, and every response option produces a distinct state transition or is documented as an intentional two-branch no-op. The blueprint checker and reviewer checklists must verify this during authoring.

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

| 43 | `test_bug43_stage2_blueprint_routing.py` | Post-delivery (debug loop) |
| 44 | `test_bug44_null_substage_dispatch.py` | Post-delivery (debug loop) |
| 45 | `test_bug45_test_execution_dispatch.py` | Post-delivery (debug loop) |
| 46 | `test_bug46_coverage_dispatch.py` | Post-delivery (debug loop) |
| 47 | `test_bug47_unit_completion_double_dispatch.py` | Post-delivery (debug loop) |
| 48 | `test_bug48_launcher_cli_contract.py` | Post-delivery (debug loop) |
| 49 | `test_bug49_argparse_enumeration.py` | Post-delivery (debug loop) |
| 50 | `test_bug50_contract_sufficiency.py` | Post-delivery (debug loop) |
| 51 | `test_bug51_debug_reassembly.py` | Post-delivery (debug loop) |
| 52 | `test_bug52_version_document_wiring.py` | Post-delivery (debug loop) |
| 53 | `test_bug53_orphaned_functions.py` | Post-delivery (debug loop) |
| 54 | `test_bug54_orphaned_update_state_from_status.py` | Post-delivery (debug loop) |
| 55 | `test_bug55_rollback_gate62_wiring.py` | Post-delivery (debug loop) |
| 56 | (structural validation) | Post-delivery (debug loop) |
| 57 | (structural validation) | Post-delivery (debug loop) |
| 58 | `test_bug58_gate_5_3_unused_functions.py` | Post-delivery (debug loop) |
| 59 | `test_bug59_blueprint_path_and_gates.py` | Post-delivery (debug loop) |
| 60 | `test_bug60_unit_context_blueprint_path.py` | Post-delivery (debug loop) |
| 61 | `test_bug61_include_tier1_parameter.py` | Post-delivery (debug loop) |
| 62 | `test_bug62_selective_blueprint_loading.py` | Post-delivery (debug loop) |
| 63 | (no dedicated regression test file -- documentation only) | Post-delivery (debug loop) |
| 64 | (existing unit tests: invariant tests in unit_10, unit tests in unit_1/unit_3) | Post-delivery (debug loop) |
| bug65 | 65 | `test_bug65_stage3_error_handling.py` | Post-delivery (debug loop) |

| 66 |  | Post-delivery (debug loop) |
| 67 |  | Post-delivery (debug loop) |
| 68 |  | Post-delivery (debug loop) |
| 69 |  | Post-delivery (debug loop) |

Note: Regression test file names (test_bug2 through test_bug62) use either the original post-delivery numbering or the unified catalog numbering. This document's unified Bug 1-64 numbering includes blueprint-era, post-delivery, and rebuild preparation bugs chronologically. The mapping table provides the cross-reference.

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

### Bug 48 — Launcher CLI contract loss across spec-blueprint-implementation boundary

**Caught:** Post-delivery (SVP 2.1 build, Stage 5 QC). **Test:** `tests/regressions/test_bug48_launcher_cli_contract.py`

The delivered launcher had three defects: (1) bare `svp` with no subcommand produced "Unknown command: None" instead of auto-detecting resume mode, (2) `--profile` argument missing from restore mode despite being required by the spec, (3) `--blueprint` (file) used instead of `--blueprint-dir` (directory) despite spec and blueprint both specifying directory semantics.

**Root cause:** The blueprint's Tier 2 signatures listed `parse_args` as a bare stub (`def parse_args(argv): ...`) without enumerating the argparse arguments. The spec defined 6 restore mode arguments in a single dense paragraph (Section 6.1.1), but the blueprint translated this into two sentences, losing `--profile` and the exact argument names. The test for bare `svp` mode accepted `None` (the broken state) instead of asserting `"resume"` (the correct post-default state). The implementation agent had no way to know what arguments to add.

**Pattern:** P1 (Cross-unit contract drift) + P7 (Spec completeness). CLI argument contracts require explicit enumeration in Tier 2 signatures, not prose descriptions in Tier 3.

**Prevention:** (1) Blueprint Tier 2 for any function using argparse must enumerate every `add_argument` call with name, type, required/optional status. (2) Tests must assert post-fix state, not accept pre-fix broken state. (3) Blueprint checker should verify every CLI argument name from the spec appears in the blueprint. New structural invariant: **CLI argument enumeration invariant** — any Tier 2 function that accepts `argv` and uses `argparse` must have its arguments enumerated in the signature block or invariants.

### Bug 49 — Systemic bare argparse stubs across 5 units

**Caught:** Post-delivery (SVP 2.1 QC audit). **Test:** `tests/regressions/test_bug49_argparse_enumeration.py`

Following Bug 48 (launcher CLI contract loss), an audit found that 5 additional units (6, 7, 9, 10, 23) had the same pattern: bare `main() -> None: ...` stubs in the blueprint's Tier 2 signatures with no argparse argument enumeration. Unit 10 was the worst offender with THREE CLI wrappers (`update_state_main`, `run_tests_main`, `run_quality_gate_main`) each having complex argument signatures. The implementations happen to be correct in this build because the implementation agents inferred arguments from context, but a future rebuild from the blueprint alone would likely produce incorrect CLI interfaces.

**Root cause:** Bug 48's prevention rule (CLI argument enumeration invariant) was applied only to Unit 24 (the immediate fix target). The systemic application to all units with argparse was not performed. This is the same piecemeal-fix pattern as Bug 43 (two-branch routing applied to one stage, not all).

**Pattern:** P1 (Cross-unit contract drift) + P7 (Spec completeness). The CLI argument enumeration invariant must be applied universally, not incrementally.

**Prevention:** (1) The blueprint checker must verify that EVERY `main()` or `*_main()` function with `argv` parameter has argparse arguments enumerated in Tier 2. (2) A structural regression test must scan all Tier 2 signatures for functions accepting `argv` and verify they have corresponding argument enumerations. (3) The spec must mandate universal application, not per-unit application.

---

### Bug 50 — Insufficient contract specificity and boundary violations in blueprint

**Caught:** Post-delivery (SVP 2.1 QC audit). **Test:** `tests/regressions/test_bug50_contract_sufficiency.py`

A systematic audit of the blueprint contracts found 16 functions across 6 units where the Tier 3 behavioral contracts were too vague for deterministic reimplementation, and several internal helper functions that had leaked into Tier 2 signatures where they don't belong. The two-sided problem:

**Under-specification (bare stubs with vague contracts):**
Functions where the implementation depends on specific data values, lookup tables, validation sets, or algorithm parameters that the contract doesn't mention. A fresh implementation agent reading only the contract would have to guess these values. Examples:
- Unit 1 `get_effective_context_budget`: depends on `_MODEL_CONTEXT_WINDOWS` mapping (model name -> token count), fallback default of 200000, and overhead constant of 20000 -- none specified in contract
- Unit 1 `validate_profile`: depends on 6+ enum validation sets (`_VALID_LINTERS = {"ruff", "flake8", "pylint", "none"}`, etc.) -- none enumerated
- Unit 1 `detect_profile_contradictions`: checks 3 specific patterns -- none listed
- Unit 1 `validate_toolchain`: uses recursive tree-walk with recognized placeholder set -- set not listed
- Unit 3 `rollback_to_unit`: creates backups in `logs/rollback/` -- backup mechanism not mentioned
- Unit 6 `generate_stub_source`: uses `ast.unparse()` and specific sentinel prepending format -- not specified
- Unit 9 `prepare_agent_task`: conditional document loading per agent type, lessons learned filtering -- strategy not described
- Unit 10 `dispatch_agent_status`: 7+ agent types with hardcoded state transitions -- transitions not listed per agent
- Unit 24 `copy_hooks`: sets executable permissions on hook scripts -- not mentioned
- Unit 24 `set_filesystem_permissions`: entirely undocumented function
- Unit 24 `launch_claude_code`: skip_permissions conditional logic not described

**Over-specification (internal helpers in Tier 2):**
Functions that are implementation choices, not cross-unit contracts, appearing in blueprint Tier 2 signatures:
- Unit 1 `_deep_merge` -- internal helper, merge BEHAVIOR should be in Tier 3 for `load_config`/`load_profile`
- Unit 3 `_clone_state` -- internal helper, immutability INVARIANT should be cross-cutting in Tier 3
- Unit 6 `_replace_function_bodies` -- internal AST manipulation helper
- Unit 3 `version_document` with `companion_paths` -- complex but was absent from Tier 2 entirely (opposite problem)

**Root cause:** The spec gave the blueprint author no guidance on what level of detail is required in each tier, or where the boundary lies between contracts and implementation details. The blueprint author made reasonable but inconsistent choices.

**Pattern:** P7 (Spec completeness). Two new invariants needed: contract sufficiency ("could an agent implement this from the contract alone?") and contract boundary ("observable behavior and critical data IN, internal helpers OUT").

**Prevention:** (1) Contract sufficiency invariant in spec Section 3.16. (2) Contract boundary rule in spec Section 3.16. (3) Blueprint checker verifies that every public function with non-trivial behavior has sufficient detail for deterministic reimplementation. (4) Regression test verifying critical data values and behavioral details are correct.

---

### Bug 51 — Debug loop missing reassembly routing after repair completion

**Caught:** Post-delivery (SVP 2.1 QC audit). **Test:** `tests/regressions/test_bug51_debug_reassembly.py`

After a successful repair in the debug loop, the triage agent's Step 6 instructs "fix workspace, then Stage 5 reassembly." But `dispatch_agent_status` for `repair_agent` with `REPAIR_COMPLETE` returned `state` unchanged — no routing to re-enter Stage 5. The workspace fix was never propagated to the delivered repo through the pipeline. In practice, fixes were applied directly to the delivered repo, bypassing the canonical workspace-then-reassemble flow and creating potential drift between workspace and delivered repo.

**Root cause:** The triage agent definition documented the intent (Step 6), but the routing script had no corresponding state transition. The agent's behavioral instructions and the routing dispatch were not synchronized.

**Pattern:** P1 (Cross-unit contract drift). The agent definition (Unit 19) described a workflow step that the routing script (Unit 10) did not implement.

**Prevention:** Every workflow step described in an agent definition that requires a state transition must have a corresponding dispatch handler in Unit 10. A structural test should verify that every agent terminal status line has a non-trivial dispatch handler (not bare `return state`) for main-pipeline agents.

---

### Bug 53 -- Orphaned functions: reset_fix_ladder, reset_alignment_iteration, record_pass_end

**Caught:** Post-delivery (SVP 2.1 QC audit). **Test:** `tests/regressions/test_bug53_orphaned_functions.py`

Three functions in `state_transitions.py` were implemented, tested, and imported (by `routing.py`) but never actually called by any pipeline code. Their behavior -- resetting fix_ladder_position, resetting alignment_iteration, and recording pass history -- was already performed inline by `restart_from_stage` and `complete_unit`. The functions were dead code that inflated the public API surface and created a false impression of coverage.

**Root cause:** During implementation, the blueprint specified these as standalone transition functions. Later, `restart_from_stage` was designed to handle all counter resets and pass history recording as part of its atomic restart operation. The standalone functions were never removed because they had passing tests and no caller verified they were needed.

**Pattern:** P1 (Dead code from superseded design). Functions implemented per an early blueprint version survived because they had tests, but the higher-level function that subsumed their behavior was never cross-referenced to identify the redundancy.

**Prevention:** (1) When a higher-level function performs the same state mutations as a lower-level function, the lower-level function should be removed or the blueprint should document why both exist. (2) Unused-import linting (ruff F401) should be enforced in CI to catch imported-but-never-called functions. (3) Periodic dead code audits should verify that every exported function has at least one non-test caller.

---

### Bug 54 -- Orphaned hollow function update_state_from_status

**Caught:** Post-delivery (SVP 2.1 QC audit). **Test:** `tests/regressions/test_bug54_orphaned_update_state_from_status.py`

`update_state_from_status` in `state_transitions.py` was the blueprint-specified "entry point called by POST commands" but its body was a hollow skeleton: it read the status file, parsed the status line, set `last_action` to an echo string, and returned state unchanged. It never dispatched to any transition function. The actual POST command entry point is `update_state_main()` in `routing.py`, which calls `dispatch_status()` directly -- completely bypassing `update_state_from_status`. The function was never called by any pipeline script, never imported by routing.py, and tested only for surface immutability.

**Root cause:** Same pattern as Bug 53. The blueprint specified this function as the dispatch entry point, but `update_state_main` was later designed in `routing.py` to call `dispatch_status` directly. The hollow function survived because it had passing tests (testing only that it returned a new state without mutating the input -- trivially satisfied by a function that does nothing).

**Pattern:** P1 (Dead code from superseded design). A function specified in the blueprint was never connected to the actual dispatch path. Tests verified structural properties (immutability, clone behavior) but not behavioral ones (actual dispatch).

**Prevention:** (1) Tests for dispatch entry points must verify actual dispatch behavior, not just structural properties. (2) Dead code audits should verify that functions documented as "entry points" are actually called from the expected call site. (3) When a function's docstring claims it is "the entry point called by POST commands," there should be a test that verifies POST commands actually invoke it.

---

### Bug 55 -- rollback_to_unit never called, Gate 6.2 FIX UNIT is a no-op

**Caught:** Post-delivery (SVP 2.1 debug loop testing). **Test:** `tests/regressions/test_bug55_rollback_gate62_wiring.py`

`rollback_to_unit` and `set_debug_classification` were implemented in `state_transitions.py` but never wired into the dispatch paths in `routing.py`. Gate 6.2 FIX UNIT returned state unchanged (`return state`). The bug_triage agent dispatch also returned state unchanged, discarding the triage classification and affected_units. Additionally, `rollback_to_unit` had a precondition requiring Stage 3, but Gate 6.2 fires during Stage 5. The function also copied invalidated files to `logs/rollback/` instead of deleting them, which would cause stale code to persist.

**Root cause:** P1 (Cross-unit contract drift). The functions were specified in the blueprint and implemented in Unit 3 (state_transitions), but the dispatch logic in Unit 10 (routing) was never updated to call them. The triage agent (Unit 19) had no mechanism to communicate affected_units back to the pipeline.

**Pattern:** P1 (Cross-unit contract drift). Functions implemented but never called from their intended call sites. The gap between "function exists" and "function is wired into the dispatch path" went undetected because tests only verified the function in isolation, not its integration into the pipeline.

**Spec/blueprint corrected:** The spec (Section 12.17.4) originally stated that FIX UNIT sets `sub_stage: "implementation"` and `verified_units` is not modified. This was wrong. The correct behavior is `rollback_to_unit(N)` which invalidates verified_units >= N, deletes source/test files, sets stage="3", sub_stage=None, and rebuilds from unit N forward. The blueprint (Unit 3 contracts, Unit 10 routing) and reference blueprint were updated to match.

**Prevention:** (1) Every state transition function must have an integration test verifying it is called from the correct dispatch path. (2) Gate dispatch handlers that return `state` unchanged should be flagged as suspicious -- they likely need wiring. (3) When a function has preconditions (e.g., "Stage 3 only"), the call site must be checked for compatibility. (4) Triage agents must write structured output (`.svp/triage_result.json`) to communicate results to the pipeline, not rely on the terminal status line alone.

**Changes:** (a) `state_transitions.py`: relaxed `rollback_to_unit` precondition to accept Stage 5 with active debug session, changed copytree to rmtree (delete not backup), added stage 5->3 transition. (b) `routing.py`: wired Gate 6.2 FIX UNIT to call rollback_to_unit, wired bug_triage dispatch to call set_debug_classification, added build_env fast path to repair_agent, added phase-based Stage 5 debug routing. (c) `debug_agents.py` / `unit_19/stub.py`: added structured output section for `.svp/triage_result.json`. (d) `hook_configurations.py` / `hooks.py`: authorized triage_result.json writes during triage phases.

---

### Bug 56 -- Spec structural gaps: downstream dependency analysis and contract granularity rules

**Caught:** Post-delivery (SVP 2.1 debug session, compound analysis of Bugs 52-55). **Test:** N/A (documentation and spec-level fix; prevention is structural).

Bugs 52-55 shared two root causes that were not addressed by individual bug fixes:

**RC1: Missing downstream dependency analysis for re-entry paths.** The spec's FIX UNIT description (Section 12.17.4) originally stated that `verified_units` was not modified during Stage 3 re-entry. This was wrong: when unit N's implementation changes, all units >= N are potentially stale because they were generated and verified against unit N's original implementation. Bug 55 fixed FIX UNIT specifically, but the general principle was never stated: ALL re-entry paths must analyze downstream dependency impact. The spec now contains the Downstream Dependency Invariant (Section 3.18) requiring this analysis for every re-entry path.

**RC2: Missing contract granularity rules.** The contract sufficiency invariant (Section 3.16, added after Bug 50) required contracts to be "sufficient for deterministic reimplementation" but did not mandate: (a) that every Tier 2 function has a Tier 3 behavioral contract, (b) that every gate response option has a per-gate-option dispatch contract, or (c) that every transition function has a documented call site. Bugs 52-55 all involved functions that were implemented but never wired into the dispatch path -- a pattern that per-gate-option dispatch contracts would have caught during blueprint alignment. The spec now contains Contract Granularity Rules (Section 3.19) mandating all three.

**Additional fix: Gate C unused function detection.** Gate C (Stage 5 assembly quality check) now includes a dead code detection step (`linter.unused_exports`) that catches exported functions defined but never called. If unused functions are found, the pipeline presents a human gate (`gate_5_3_unused_functions`) that strongly recommends `/svp:redo` to fix the spec/blueprint, but allows the human to override and continue. This is a human-gated last line of defense against the Bugs 52-55 pattern -- not an automatic failure.

**Pattern:** Compound P1 (Cross-unit contract drift) + new pattern P9 (Spec structural gap). The spec provided the principle (contract sufficiency) but not the granularity rules needed to operationalize it. The blueprint checker had no structural criteria to verify, so it could not catch the gap.

**Prevention:** (1) Section 3.18 (Downstream Dependency Invariant) requires every re-entry path to document downstream impact. (2) Section 3.19 (Contract Granularity Rules) requires Tier 3 contracts for every Tier 2 function, per-gate-option dispatch contracts, and call-site verification. (3) Section 8.2 updated to require the blueprint checker to verify all three rules. (4) Gate C enhanced with unused function detection (human-gated via `gate_5_3_unused_functions`, not automatic failure). (5) README checklist extended with a ninth advisory question covering these structural checks.

---

### Bug 57 -- Review enforcement: baked dependency and contract checklists into reviewer agent definitions

**Caught:** Post-delivery (SVP 2.1 debug session, preventive hardening after Bugs 52-56). **Test:** N/A (agent definition and spec-level fix; prevention is structural).

Bugs 52-55 were all caused by functions or dispatch paths that existed in the blueprint but were never wired into the codebase. Bug 56 added structural rules (Sections 3.18-3.19) and a Gate C dead-code detection step (Gate 5.3). However, both of these are late-stage defenses: they catch symptoms at assembly time or provide rules the blueprint author might not consult. The missing piece was authoring-time enforcement -- making the LLM reviewers themselves check for the patterns that caused Bugs 52-55.

Bug 57 adds a second, complementary defense layer: mandatory review checklists baked directly into the agent definitions for the stakeholder reviewer (Unit 14), blueprint checker (Unit 14), and blueprint reviewer (Unit 14). These checklists require each reviewer to explicitly verify downstream dependency analysis, Tier 3 contract coverage, per-gate-option dispatch contracts, call-site traceability, and re-entry path invalidation. Because the checklist text is part of the agent's system prompt, it cannot be forgotten or skipped.

**Two-tier defense model:** (1) LLM-driven review catches root causes at authoring time (Bug 57). (2) Gate C deterministic check catches symptoms at assembly time (Bug 56). Together they provide defense in depth.

**Pattern:** P9 (Spec structural gap) -- the spec required review but did not specify what reviewers must check for. The review agents had no structural checklist, so they could not systematically catch the patterns that caused Bugs 52-55.

**Prevention:** (1) Section 3.20 (Review Enforcement) added to spec, requiring mandatory checklists in all reviewer agent definitions. (2) Stakeholder reviewer, blueprint checker, and blueprint reviewer agent definitions updated with explicit checklist items. (3) Blueprint Tier 1/Tier 3 contracts updated to reflect Bug 57 expansion. (4) Two-tier defense model documented: LLM-driven review (authoring time) + Gate C deterministic check (assembly time).

**Changes:** (a) `review_agents.py` / `unit_14/stub.py`: added mandatory review checklist items to all three agent definitions. (b) `stakeholder_spec.md`: added Section 3.20 (Review Enforcement -- Baked Checklists). (c) `blueprint.md` and `blueprint_contracts.md`: updated Unit 14 descriptions and behavioral contracts.


---

### Bug 58 -- Gate 5.3 missing from GATE_VOCABULARY; comprehensive summary document update

**Caught:** Post-delivery (SVP 2.1 debug session, audit of routing.py against spec/blueprint). **Test:** `tests/regressions/test_bug58_gate_5_3_unused_functions.py`.

Gate 5.3 (`gate_5_3_unused_functions`) was specified in the stakeholder spec (Section 12.2), both blueprint files (GATE_VOCABULARY and ALL_GATE_IDS), and the summary gate table, but was never added to routing.py's `GATE_VOCABULARY` dict or prepare_task.py's `ALL_GATE_IDS` list. The gate could not actually be presented by the pipeline. Additionally, the `dispatch_gate_response` function had no handler for the gate's two responses (FIX SPEC, OVERRIDE CONTINUE).

**Pattern:** P1 (Cross-unit contract drift). The spec and blueprint defined the gate; the implementation never received it. The existing gate ID consistency test (`test_bug43`) would have caught this if the gate had been added to one of the two registries but not the other -- but since it was missing from both, the sets remained equal and the test passed.

**Prevention:** (1) When adding a new gate to the spec/blueprint, a checklist must verify it is added to GATE_VOCABULARY, ALL_GATE_IDS, dispatch_gate_response, and the existing test expected sets. (2) A structural test should verify that every gate ID in the spec's gate vocabulary table appears in GATE_VOCABULARY (spec-to-code consistency, not just code-to-code).

**Changes:** (a) `routing.py`: added `gate_5_3_unused_functions` to GATE_VOCABULARY, added dispatch handler (FIX SPEC restarts from Stage 1, OVERRIDE CONTINUE proceeds). (b) `prepare_task.py`: added `gate_5_3_unused_functions` to ALL_GATE_IDS. (c) `svp_2_1_summary.md`: 21 gaps fixed (triage_result.json, build_env fast path, phase-based debug routing, Downstream Dependency Invariant, Contract Granularity Rules, Review Enforcement, version_document mechanism, regression test table, Gate 5.3 in Stage 5 diagram, set_debug_classification, pattern catalog entries, glossary additions).

### Bug 59 -- Stale blueprints/ Directory, Critical Implementation Bugs, and Spec Gaps

**Caught:** Post-delivery (spec audit, code review). **Test:** `test_bug59_blueprint_path_and_gates.py`.

Multiple related issues discovered during comprehensive audit:

1. **Stale `blueprints/` directory:** A prior-iteration directory diverging architecturally from canonical `blueprint/` (singular). Removed entirely.
2. **`_version_blueprint` hardcoded wrong path:** Used `blueprints/` instead of `blueprint/`. Fixed to use `blueprint/`.
3. **`advance_stage` checked old single-file format:** Checked for `blueprint/blueprint.md` instead of `blueprint_prose.md` and `blueprint_contracts.md`. Fixed to use two-file format.
4. **`load_blueprint` used old format:** Referenced `ARTIFACT_FILENAMES["blueprint"]` mapping to `"blueprint.md"`. Fixed to load both prose and contracts files.
5. **`ALL_GATE_IDS` missing `gate_hint_conflict`:** Added. Now synchronized with `GATE_VOCABULARY`.
6. **`AGENT_STATUS_LINES["test_agent"]` missing `REGRESSION_TEST_COMPLETE`:** Added.
7. **`GATE_VOCABULARY` missing `gate_hint_conflict`:** Added with responses `["BLUEPRINT CORRECT", "HINT CORRECT"]`.
8. **`ARTIFACT_FILENAMES` in Unit 1:** Replaced individual `blueprint_prose`/`blueprint_contracts` keys with `blueprint_dir: "blueprint"`.
9. **`DebugSession` missing fields:** Added `triage_refinement_count` and `repair_retry_count` (both `int`, default 0).
10. **`version_document` missing `companion_paths`:** Added parameter for atomic multi-file versioning.
11. **`_FIX_LADDER_TRANSITIONS` cross-branch error:** `hint_test` incorrectly allowed transition to `fresh_impl`. Fixed to `[]`.
12. **Undocumented `investigation` phase:** Removed from `_DEBUG_PHASE_TRANSITIONS`.
13. **Spec gaps:** Multiple sections updated (triage_result.json, Gate 5.3 FIX SPEC trigger, DebugSession schema, regression test table, gate_hint_conflict resolution, P1-P9, Section 24 failure modes).

**Pattern:** P9 (Accumulated drift). Multiple small mismatches accumulated across spec, blueprint, and implementation without triggering any single test failure. Each was individually minor; together they represented significant architectural inconsistency.

**Prevention:** Periodic comprehensive audit comparing spec gate/status/schema definitions against implementation registries. Automated structural tests should verify bidirectional consistency between all three document layers (spec, blueprint, code).

---


### Bug 60 -- Broken _get_unit_context and Stale Fallback ARTIFACT_FILENAMES

**Caught:** Post-delivery (code review). **Test:** `test_bug60_unit_context_blueprint_path.py`.

Two related issues in `scripts/prepare_task.py` (Unit 9):

1. **Fallback `ARTIFACT_FILENAMES` stale key:** The fallback dict still had `"blueprint": "blueprint.md"` instead of `"blueprint_dir": "blueprint"`. After Bug 59 changed Unit 1 to use `blueprint_dir`, this fallback was never updated.
2. **`_get_unit_context` wrong path construction:** Line 317 used `project_root / "blueprint" / ARTIFACT_FILENAMES["blueprint"]` which resolved to `blueprint/blueprint.md` (a file that does not exist in the two-file split format). This caused `build_unit_context` to fail silently, returning the placeholder `"(Unit N context not available.)"` for ALL agents that use unit context (test_agent, implementation_agent, coverage_review, diagnostic_agent, redo_agent).

**Impact:** All agents receiving unit context were silently getting no blueprint information, operating without knowledge of the unit they were supposed to work on.

**Fix:** Changed fallback key to `"blueprint_dir": "blueprint"`. Changed `_get_unit_context` to use `project_root / ARTIFACT_FILENAMES.get("blueprint_dir", "blueprint")`, passing the directory (not a file) to `build_unit_context`.

**Pattern:** P3 (Stale cross-unit reference). Bug 59 updated Unit 1 ARTIFACT_FILENAMES but did not propagate the key rename to Unit 9 prepare_task.py fallback dict and _get_unit_context.

**Prevention:** When renaming keys in shared dictionaries (ARTIFACT_FILENAMES), grep all consumers in the codebase and update them atomically. Add regression tests that verify consumers can actually resolve the paths they construct.

---

### Bug 61 -- Missing include_tier1 Parameter in _get_unit_context and build_unit_context

**Caught:** Post-delivery (code review against spec Section 3.16). **Test:** `test_bug61_include_tier1_parameter.py`.

Two related issues across Unit 5 (blueprint_extractor.py) and Unit 9 (prepare_task.py):

1. **`build_unit_context` (Unit 5) missing `include_tier1` parameter:** The function always included Tier 1 prose descriptions in the output. The stub correctly defined `include_tier1: bool = True`, but the deployed script never implemented it.
2. **`_get_unit_context` (Unit 9) missing `include_tier1` parameter:** The function had no way to pass `include_tier1` through to `build_unit_context`. The test_agent and implementation_agent call sites always received full content including Tier 1 prose, wasting tokens on every invocation.

**Impact:** test_agent and implementation_agent (the two most frequently called agents) received unnecessary Tier 1 prose descriptions in every task prompt, wasting context budget. This is exactly what the two-file blueprint split (spec Section 3.16) was designed to prevent.

**Fix:** Added `include_tier1: bool = True` parameter to both `build_unit_context` (blueprint_extractor.py) and `_get_unit_context` (prepare_task.py). Changed test_agent and implementation_agent call sites to pass `include_tier1=False`. Left coverage_review and diagnostic_agent at default `True` since they need full context per spec.

**Pattern:** P3 (Stale cross-unit reference). The stubs correctly specified the `include_tier1` parameter but the deployed implementations were never updated to match.

**Prevention:** After implementing a stub, diff the stub against the deployed script to verify all parameters are wired through. Automated structural tests should verify that deployed function signatures match their stub specifications.

---

### Bug 62 -- Selective Blueprint Loading Not Wired Per Agent Matrix

**Caught:** Post-delivery (code review against spec Section 3.16). **Test:** `test_bug62_selective_blueprint_loading.py`.

Spec Section 3.16 defines a per-agent loading matrix for the two-file blueprint split. Three agents were receiving the full blueprint (prose + contracts concatenated) when they should receive only one file:

1. **integration_test_author** received both files via `_safe_load_blueprint`. Spec says contracts only.
2. **git_repo_agent** received both files via `_safe_load_blueprint`. Spec says contracts for assembly mapping.
3. **help_agent** received both files via `_safe_load_blueprint`. Spec says prose primary.

**Impact:** Agents received unnecessary content in their task prompts, wasting context budget. This defeats the purpose of the two-file blueprint split (spec Section 3.16).

**Fix:** Added `load_blueprint_contracts_only()` and `load_blueprint_prose_only()` functions to both `scripts/prepare_task.py` and `src/unit_9/stub.py`. Wired integration_test_author and git_repo_agent to use contracts-only, help_agent to use prose-only. Left blueprint_checker, blueprint_reviewer, hint_agent, and bug_triage with full loading.

**Pattern:** P2 (Incomplete spec implementation). The spec defined the agent matrix but the implementation used the same full loader for all agents.

**Prevention:** When a spec defines a matrix of agent-specific behaviors, create a checklist and verify each agent individually. Regression tests should verify each agent receives exactly the content the spec prescribes.

### Bug 63 -- Documentation Retrofit for Bugs 60-62

**Caught:** Post-delivery (documentation review). **Test:** (no dedicated regression test file -- documentation only).

Bugs 60-62 made code changes (blueprint path fix, include_tier1 parameter, selective blueprint loading) but did not update the stakeholder spec, blueprint, lessons learned, summary, CHANGELOG, or README to reflect those changes.

**Impact:** Documentation was out of sync with code. Stakeholder spec Section 3.16 did not reflect the implemented selective loading functions. Regression test table stopped at Bug 59. Lessons learned catalog range was stale.

**Fix:** Updated stakeholder spec (v8.31), blueprint prose, lessons learned (catalog range, pattern counts, regression test mapping), summary document, CHANGELOG, and README.

**Pattern:** (Documentation maintenance -- no code pattern).

**Prevention:** Every code-change bug must include a documentation update pass as part of the fix. The debug commit checklist should include "docs updated" verification.

---

### Bug 64 -- 11 Unit Test Failures from Stale Assertions After Bugs 59-62

**Caught:** Post-delivery (test suite run). **Test:** (existing unit tests -- no dedicated regression test file needed).

After Bugs 59-62 correctly updated source code (ARTIFACT_FILENAMES keys, fix ladder transitions, debug phase transitions, gate IDs), 11 unit tests still asserted the old behavior:
- 3 tests in unit_1 expected `blueprint_prose`/`blueprint_contracts` keys instead of `blueprint_dir`
- 3 tests in unit_10 detected that `gate_5_3_unused_functions` was in GATE_RESPONSES but missing from ALL_GATE_IDS
- 1 test in unit_3 expected `hint_test -> fresh_impl` transition (removed -- hint_test is now terminal)
- 4 tests in unit_3 expected `triage -> investigation` debug phase transition (replaced by `triage -> regression_test`)

**Impact:** 11 test failures in the workspace test suite. The cross-unit gate ID mismatch (unit_9 ALL_GATE_IDS vs unit_10 GATE_RESPONSES) would cause runtime failures if gate_5_3 were triggered.

**Fix:** Added `gate_5_3_unused_functions` to ALL_GATE_IDS in unit_9 and added prepare_gate_prompt handler. Updated unit_1 tests for blueprint_dir. Updated unit_3 tests for current fix ladder and debug phase transitions. Updated unit_9 tests for new gate count (23).

**Pattern:** P1 (Cross-Unit Contract Drift). The gate_5_3 ID was added to unit_10's GATE_RESPONSES but not to unit_9's ALL_GATE_IDS.

**Prevention:** When adding a new gate to any module, verify it exists in ALL registries (ALL_GATE_IDS, GATE_RESPONSES, GATE_VOCABULARY, prepare_gate_prompt handler). Structural invariant tests catch this -- they were working correctly by failing.

---

### Bug 65 -- Stage 3 Error-Handling Infrastructure Entirely Unimplemented (Compound)

**Caught:** Post-delivery (bug triage agent). **Test:** `test_bug65_stage3_error_handling.py`

The entire Stage 3 error-handling infrastructure was dead code. Only the happy path worked (test_generation -> Gate A -> red_run -> implementation -> Gate B -> green_run -> coverage_review -> unit_completion). All failure paths, fix ladders, gates, and diagnostic escalation were unimplemented at the routing level. Nine findings:

1. **F1 (stub_generation missing from routing):** `route()` treated `sub_stage is None` as `test_generation` instead of `stub_generation`. The stub generator script was never invoked.
2. **F2 (TESTS_PASSED at red_run -> infinite loop):** When tests PASS against stubs (red_run), the spec says those tests are defective. `dispatch_command_status` had no handler for this case.
3. **F3 (green_run failure -> infinite loop, no fix ladder):** When `TESTS_FAILED` at `green_run`, `dispatch_command_status` returned state unchanged with no fix ladder engagement.
4. **F4 (diagnostic_agent dispatch is bare no-op):** `dispatch_agent_status` for `diagnostic_agent` was `return state` with no parsing of DIAGNOSIS_COMPLETE classification.
5. **F5 (coverage_review missing two-branch check):** `route()` always re-invoked the coverage_review agent without checking `last_status.txt`.
6. **F6 (fix_ladder_position never checked in route()):** `route()` at `implementation` sub_stage always invoked implementation_agent, ignoring `fix_ladder_position`.
7. **F7 (Gate 3.1 dispatch handlers are no-ops):** Both `TEST CORRECT` and `TEST WRONG` for `gate_3_1_test_validation` returned state unchanged.
8. **F9 (stub_generation not in dispatch_command_status):** No handler for `stub_generation` phase in `dispatch_command_status`.
9. **F10 (red_run_retries never incremented):** `increment_red_run_retries` was never called when tests passed at red_run.

**Impact:** Every Stage 3 failure path was broken. Any unit that experienced a test failure, fix ladder escalation, diagnostic escalation, or defective test detection would loop infinitely.

**Fix:** Implemented all 9 findings in routing.py (workspace and delivered repo). Updated unit_10 stub.py to mirror. Updated test_bug46 and test_bug50 for new coverage_review dispatch behavior. 24 new regression tests cover all failure paths.

**Pattern:** Compound P7 + P9 + P1. P7 (Spec Completeness): the spec described error paths in prose (Sections 10.4, 10.9, 10.10, 10.11) but the blueprint Tier 3 contracts covered only happy-path transitions. P9 (Spec Structural Gap): error-path dispatch was described in prose but never appeared as enumerable contracts. P1 (Cross-Unit Contract Drift): the routing script and state_transitions had matching function signatures but no wiring.

**Prevention:** (1) Exhaustive dispatch_command_status tables for ALL (phase, sub_stage, status) combinations -- silence is not a valid contract outcome. (2) Per-gate-option dispatch contracts applied strictly: every gate response option must produce a distinct state transition. (3) Regression tests for error-path dispatch completeness: every reachable (phase, sub_stage, status) combination must be tested, not just happy paths.

**New pattern candidate: "Error-Path Contract Omission" (P10).** Happy path is contracted and tested; error paths exist only in spec prose and are never converted to enumerable blueprint contracts. The implementation agent correctly implements the contracted paths and silently ignores the uncontracted error paths, producing code that compiles but loops on any failure.

---
### Bug 67 -- gate_5_3_unused_functions Has No Routing Path in route()

**Caught:** Post-delivery (debug loop audit). **Test:** `test_bug67_gate_5_3_routing.py`

Bug 58 added `gate_5_3_unused_functions` to GATE_VOCABULARY, ALL_GATE_IDS, and dispatch_gate_response. However, no code path in `route()` ever presents this gate. There is no `sub_stage == "gate_5_3"` branch in Stage 5 routing, `gate_5_3` is not in STAGE_5_SUB_STAGES, there is no `UNUSED_FUNCTIONS_DETECTED` command status pattern, and dispatch_command_status for compliance_scan has no handler to advance to gate_5_3.

**Impact:** The gate exists in the vocabulary and dispatch tables but can never be presented to the human. If the compliance scan detects unused functions, it falls through to the generic COMMAND_FAILED handler, re-entering the bounded fix cycle instead of presenting the human gate.

**Fix:** (1) Added `gate_5_3` to STAGE_5_SUB_STAGES in unit_2/stub.py and all unit_2_mock.py files. (2) Added `gate_5_3` routing branch in route() to present gate_5_3_unused_functions. (3) Added `UNUSED_FUNCTIONS_DETECTED` to COMMAND_STATUS_PATTERNS. (4) Added compliance_scan dispatch handler for UNUSED_FUNCTIONS_DETECTED that advances to gate_5_3 sub-stage. Mirrored in unit_10/stub.py and delivered repo.

**Pattern:** P1 (Cross-Unit Contract Drift). The gate vocabulary and dispatch handlers were added but the routing path, state constants, and command status patterns were not updated to connect them.

**Prevention:** When adding a new gate, verify the full chain: (1) GATE_VOCABULARY entry, (2) ALL_GATE_IDS entry, (3) dispatch_gate_response handler, (4) STAGE_N_SUB_STAGES entry, (5) route() branch, (6) command status pattern if gate is triggered by a command result, (7) dispatch_command_status handler, (8) prepare_gate_prompt handler.

---

### Bug 66 -- gate_2_3 RETRY BLUEPRINT Is a No-Op Causing Routing Loop

**Caught:** Post-delivery (debug loop audit). **Test:** `test_bug66_gate_2_3_retry_blueprint.py`

`dispatch_gate_response` for `gate_2_3_alignment_exhausted` with response `RETRY BLUEPRINT` returned `state` unchanged. The sub_stage remained `alignment_check`, so on the next routing cycle, `route()` re-invoked the blueprint_checker instead of the blueprint_author. The human's intent to retry the blueprint dialog was silently ignored.

**Fix:** Version the blueprint via `_version_blueprint`, reset `alignment_iteration` to 0 and `sub_stage` to `None` so routing invokes blueprint_author for a fresh dialog. Mirrored in `src/unit_10/stub.py`.

**Pattern:** P10 (Error-Path Contract Omission). The blueprint contracts already specified the correct behavior (reset alignment_iteration and sub_stage); the implementation simply never followed it. The gate dispatch handler was a bare `return state`.

**Prevention:** Every gate dispatch branch must produce a distinct state transition. A `return state` in a gate handler is almost always a bug unless explicitly documented as an intentional two-branch no-op.

---

### Bug 68 -- Stage 4 Failure Handling: Gates 4.1 and 4.2 Dead, ASSEMBLY FIX No-Op

**Caught:** Post-delivery (debug loop audit). **Test:** `test_bug68_stage4_failure_handling.py`

Stage 4 routing only implemented the happy path (integration_test_author -> run tests -> advance to Stage 5). Three failure-path defects: (1) no `gate_4_1` or `gate_4_2` sub-stage routing in `route()`, so gates could never be presented; (2) no `TESTS_FAILED` handler in `dispatch_command_status` for Stage 4, so integration test failures were silently swallowed; (3) `gate_4_1` `ASSEMBLY FIX` dispatch was a bare `return state` no-op instead of resetting sub_stage for re-assembly.

**Fix:** Added `gate_4_1` and `gate_4_2` to `STAGE_4_SUB_STAGES`. Added gate routing branches in `route()`. Added Stage 4 `TESTS_FAILED` handler in `dispatch_command_status` with retry counting and exhaustion escalation. Fixed `gate_4_1` `ASSEMBLY FIX` dispatch to reset `sub_stage` to `None`. 14 regression tests.

**Pattern:** P10 (Error-Path Contract Omission). Same disease as Bugs 65/66/67 -- the entire failure-handling side of a routing block was left as dead code or bare no-ops.

**Prevention:** When implementing a new stage's routing, always verify that every gate in the GATE_VOCABULARY for that stage is reachable from `route()` via some `dispatch_command_status` or `dispatch_gate_response` transition.

---

### Bug 69 -- Debug Loop Gates: Dead Gates and No-Op Dispatches (Compound Fix)

**Caught:** Post-delivery (debug loop audit). **Test:** `test_bug69_debug_loop_gates.py`

Four interrelated debug loop gates were either never presented by `route()` or had no-op dispatch handlers. E.1: Gate 6.0 (debug permission) -- `route()` treated `triage_readonly` and `triage` identically, so Gate 6.0 was never presented. E.2: Gate 6.1 (regression test) -- `regression_test` debug phase had no handler in `route()`. E.3: Gate 6.3 `RECLASSIFY BUG` -- dispatch was bare `return state`. E.4: Gate 6.5 (debug commit) -- `complete` debug phase had no handler in `route()`.

**Fix:** E.1: Separated `triage_readonly` (presents Gate 6.0 on completion) from `triage` (presents Gate 6.2). E.2: Added `regression_test` phase handler; wired TEST CORRECT to advance to `complete` phase. E.3: RECLASSIFY BUG resets phase to `triage` and clears classification. Added `repair->triage` and `regression_test->complete` to `_DEBUG_PHASE_TRANSITIONS`. E.4: Added `complete` phase handler; wired COMMIT APPROVED to `complete_debug_session`. 23 regression tests.

**Pattern:** P10 (Error-Path Contract Omission). Same recurring pattern as Bugs 65-68 -- gate vocabulary entries and dispatch handlers exist but routing never presents them and dispatch returns state unchanged.

**Prevention:** For every gate in GATE_VOCABULARY, verify: (1) route() has a path that returns that gate, (2) every response option in dispatch produces a distinct state change, (3) regression tests exercise both routing and dispatch for each response.

---

### Bugs 65-69 P10 Root Cause Fix -- Spec Strengthened

**Date:** 2026-03-19

Bugs 65-69 all share the same root cause: P10 (Error-Path Contract Omission). The spec described gate behaviors in prose (Sections 10-12) but did not require exhaustive dispatch contracts for ALL gates and ALL (phase, sub_stage, status) combinations. Happy paths were contracted; error paths were described in prose only. Each stage independently had the same disease.

**Spec fix:** Added "Gate reachability and dispatch exhaustiveness invariant" to Section 3.6: every gate in GATE_VOCABULARY must have a reachable code path in `route()`; every response option must produce a meaningful state transition or be documented as an intentional two-branch no-op. Added structural test requirement for gate reachability. Added gate reachability check to Section 3.20 blueprint checker and reviewer checklists.

**Blueprint fix:** Updated Unit 10 Tier 3 dispatch contracts for Gates 6.1, 6.3, 6.5 to reflect actual implementations. Added phase transition table to Unit 3 documenting all valid transitions including Bug 69 additions. Added gate reachability check to Unit 14 blueprint checker and reviewer checklists.

**Pattern:** This is the meta-fix -- strengthening the spec and blueprint to prevent the P10 pattern from recurring in future builds. The individual bug fixes (65-69) addressed the symptoms; this fix addresses the root cause in the specification.

---

### Bug 70 -- Fix Ladder Routing Gap at sub_stage=None, TESTS_ERROR Infinite Loop, Dead Phases

**Caught:** Post-delivery (systematic technique analysis). **Test:** `test_bug70_ladder_routing_tests_error.py`

Three findings from systematic analysis of routing.py dispatch coverage:

**F1: Fix ladder position not checked when sub_stage=None in Stage 3 routing.** When `quality_gate_fail_to_ladder` sets `sub_stage=None` with a non-None `fix_ladder_position` (e.g., `"fresh_test"` after Gate A retry fails), `route()` hit the `sub_stage is None` branch and unconditionally routed to stub_generation. This is wrong -- it should route based on the ladder position: test ladder positions to test_generation, impl ladder positions to implementation, diagnostic to diagnostic_agent.

**F2: TESTS_ERROR at test_execution returned state unchanged -- infinite retry loop.** `dispatch_command_status` had a bare `return state` for TESTS_ERROR, causing the pipeline to re-run the same test command forever. Fixed: red_run TESTS_ERROR increments retries and regenerates tests (or presents Gate 3.1 on exhaustion). Green_run TESTS_ERROR engages fix ladder (same as TESTS_FAILED). Stage 4 TESTS_ERROR presents gate (same as TESTS_FAILED).

**F3: Dead phase values in _KNOWN_PHASES.** `"test"` and `"infrastructure_setup"` were in `_KNOWN_PHASES` but never emitted as `--phase` arguments and never mapped in `phase_to_agent`. Removed as vocabulary cruft.

**Pattern:** P10 (Error-Path Contract Omission) for F1 and F2. P5 (Vocabulary Cruft) for F3. The pattern continues: routing blocks implement the happy path but leave error/alternate paths as no-ops or bare returns.

**Prevention:** For every state transition function that sets `sub_stage=None`, verify that `route()` handles the resulting state correctly by examining ALL state fields (not just `sub_stage`). For every command status pattern in COMMAND_STATUS_PATTERNS, verify that dispatch produces a distinct state change for every (phase, sub_stage) combination where that status can occur.

---

### Bug 71 -- Structural Completeness Test Suite (14 Automated Guards)

**Caught:** Post-delivery (systematic technique analysis). **Test:** `test_bug71_structural_completeness.py`

Wrote 163 automated tests across 14 test classes, each automating one of the systematic bug-finding techniques that discovered Bugs 52-70. The test suite acts as a permanent regression guard against declaration-vs-usage bugs.

**Findings during test development:**

**F1: Stage 4 gate_4_1/gate_4_2 unreachable from route().** The route() function for Stage 4 had no sub_stage handling -- it only checked last_status for INTEGRATION_TESTS_COMPLETE vs. invoking the agent. When dispatch_command_status set sub_stage to "gate_4_1" or "gate_4_2", route() did not present the corresponding human gates. Fixed by adding sub_stage checks at the top of Stage 4 routing.

**F2: Stage 4 TESTS_FAILED not handled in dispatch_command_status.** The TESTS_FAILED branch in dispatch_command_status checked sub_stage == "red_run" and sub_stage == "green_run" but had no stage == "4" fallback. TESTS_ERROR had the Stage 4 handler but TESTS_FAILED did not. Fixed by adding a stage == "4" check after the green_run block.

**14 technique tests implemented:**
1. Gate Vocabulary vs Route Reachability (AST analysis)
2. Response Options vs Dispatch Handlers (parametrized over all gate/response pairs)
3. Exported Functions vs Call Sites (no orphaned public functions)
4. Stub vs Script Synchronization (7 constant comparison tests)
5. (Skipped -- narrative-vs-contract not automatable)
6. Per-Agent Loading Matrix (prepare_task.py agent handling)
7. Agent Status Lines vs Dispatch (parametrized over all agent/status pairs)
8. Known Agent Types vs Route Invocations (AST analysis)
9. Debug Phase Transitions vs Route Handlers (all debug phases)
10. Sub-Stages vs Route Branches (Stage 3/4/5 parametrized)
11. Fix Ladder Positions vs Route Context (7 ladder/context combinations)
12. Command Status Patterns vs Phase Handlers (12 critical combinations)
13. Phase-to-Agent Map vs Known Phases
14. Debug Phase Transitions vs Known Phases (stub vs script sync)

**Pattern:** P10 (Error-Path Contract Omission) for both findings. The structural tests would have caught these at build time if they had existed during the original build.

**Prevention:** Run the structural completeness test suite after every delivery. Any new gate, agent type, status line, sub-stage, or debug phase that is declared but not wired will be caught automatically.

---
### Bug 72 -- Generalized Structural Completeness Checking (Four-Layer Defense)

**Caught:** Post-delivery (proactive feature addition). **Test:** `test_bug72_structural_check.py`

Built a project-agnostic structural completeness checking system that works for any Python project SVP builds, not just SVP itself. Four complementary layers:

**Layer 1 (Blueprint checker):** Added mandatory registry completeness checklist item to blueprint checker agent definition. The checker must identify every registry, vocabulary, enum, or dispatch table and verify handler coverage.

**Layer 2 (Integration test author):** Added requirement to generate registry-handler alignment tests using AST analysis of registries and dispatch logic.

**Layer 3 (Deterministic script):** Created `scripts/structural_check.py` -- a project-agnostic AST scanner performing five checks: (1) dict registry keys never dispatched, (2) enum values never matched, (3) exported functions never called, (4) string dispatch gaps, (5) stub imports in test files (Bug 74). Only stdlib imports. Added as Stage 5 `structural_check` sub-stage between `repo_test` and `compliance_scan`.

**Layer 4 (Triage agent):** Added Step 0 structural pre-check and Registry Diagnosis Recipe to bug triage agent. Task prompt assembly pre-computes structural check results against the delivered repo.

**Pattern:** P11 (Structural Completeness Gap) -- new pattern. The system lacked a generalized, project-agnostic mechanism for detecting declaration-vs-usage gaps. The existing Bug 71 test suite was SVP-specific; the four-layer defense generalizes this to any project.

**Prevention:** Every new registry, dispatch table, or enum-like constant introduced in any project should be detectable by the structural check script. The four layers ensure coverage at authoring time (L1), test time (L2), assembly time (L3), and debug time (L4).

---

### Bug 73: Routing/dispatch loops from unchanged state returns (compound fix)

**Date:** 2026-03-19
**Classification:** single_unit (routing.py)
**Root cause:** P10 (Error-Path Contract Omission) -- Three dispatch handlers returned state unchanged, causing routing to loop back to the same action indefinitely.

**Findings (3 fixes):**
- Bug 73: Stage 0 project_context routing only checked `PROJECT_CONTEXT_COMPLETE`. If the setup agent completed both artifacts in one session and wrote `PROFILE_COMPLETE`, the else branch re-invoked the setup agent. Additionally, after Gate 0.2 overwrites last_status with "CONTEXT APPROVED", the project_profile branch couldn't detect the already-created profile. Fixed by: (a) expanding the project_context check to also match PROFILE_COMPLETE, (b) adding artifact-existence fallback in the project_profile branch.
- Bug 73-A: Gate 5.3 `OVERRIDE CONTINUE` returned state unchanged with sub_stage still "gate_5_3". Routing re-presented the same gate. Fixed by advancing sub_stage to "repo_complete".
- Bug 73-B: Gate 4.1 `ASSEMBLY FIX` returned state unchanged with sub_stage still "gate_4_1". Routing re-presented the same gate. Fixed by resetting sub_stage to None via advance_sub_stage.

**Pattern:** Every `return state` in a dispatch handler is suspect. The returned state, when fed back into `route()`, must produce a *different* action than the one that just completed. If it produces the same action, the pipeline loops. This is the 7th occurrence of this pattern.

**Prevention:** Exhaustive checklist for every dispatch handler: trace the returned state through `route()` and verify it produces a different action. No `return state` without explicit sub_stage advancement.

---

### Bug 74: Regression tests testing stubs instead of real implementation

**Date:** 2026-03-19
**Classification:** structural (test infrastructure)
**Root cause:** P12 (Test Target Mismatch) -- Eight workspace regression test files imported from `src.unit_N.stub` instead of the real implementation modules. Stubs may diverge from the real scripts, causing false-pass scenarios.

**Pattern:** When a build pipeline uses both stubs and real scripts, regression tests must always target the real scripts. Stubs are intermediate artifacts; the real scripts are what gets delivered.

**Prevention:** (1) `pyproject.toml` pythonpath config for direct script imports. (2) Blueprint checker must verify no `from src.unit_` imports in regression tests. (3) Blueprint reviewer must include this check in its review checklist.

---

### Bug 75: Coverage review auto-format quality gate TransitionError

**Date:** 2026-03-20
**Classification:** single_unit (routing.py)
**Root cause:** P10 (Error-Path Contract Omission) — Coverage review auto-format path emits `run_quality_gate.py --gate gate_b` with POST `phase=quality_gate`, but `sub_stage` is `"coverage_review"`, not `"quality_gate_b"`. `quality_gate_pass()` raises `TransitionError`.

**Fix:** `dispatch_command_status` for `quality_gate` phase handles `sub_stage == "coverage_review"` by advancing directly to `unit_completion` (both success and failure — residuals deferred to Gate C).

**Prevention:** Every `run_quality_gate.py` command emitted by `route()` must verify the POST dispatch path can handle the current `sub_stage`.

---

### Bug 76: Pre-Stage-3 routing skipped infrastructure setup

**Date:** 2026-03-20
**Classification:** single_unit (routing.py)
**Root cause:** P10 (Error-Path Contract Omission) — `route()` for `stage == "pre_stage_3"` invoked `reference_indexing` agent without first running `setup_infrastructure.py`. Conda env never created, quality packages never installed.

**Fix:** Sub-stage handling: `None` → run infrastructure command; `"reference_indexing"` → invoke agent.

### Bug 77: `--no-banner` flag incompatible with conda ≥25.x

**Date:** 2026-03-20
**Classification:** toolchain configuration
**Root cause:** `run_prefix` in toolchain defaults used `--no-banner` which is not supported in conda 25.x+. Removed the flag.

---

### Bug 78: Reference indexing agent missing Write tool

**Date:** 2026-03-20
**Classification:** agent definition
**Root cause:** Agent definition listed only Read, Glob, Grep tools. Cannot produce `references/summaries.md`. Downstream agents receive no reference context.

**Fix:** Added Write to tool list. Clarified "read-only" applies to input documents, not output.

### Bug 79: Reference indexing task prompt feeds agent its own output

**Date:** 2026-03-20
**Classification:** single_unit (prepare_task.py)
**Root cause:** The `reference_indexing` case in `_assemble_sections_for_agent` called `_safe_load_reference_summaries()` which reads `references/summaries.md` — the file the agent is supposed to produce. Before the agent has run, the file doesn't exist, so the agent gets "(No reference documents available.)" instead of the raw reference documents it needs to index.

**Fix:** Changed to scan `references/` directory for raw files (excluding `summaries.md`) and include their content in the task prompt.

### Bug 80: Blueprint author agent missing output path specification

**Date:** 2026-03-20
**Classification:** agent definition
**Root cause:** The blueprint author agent definition never specified where to write output. The pipeline expects `blueprint/blueprint_prose.md` and `blueprint/blueprint_contracts.md`, but without explicit instructions the agent wrote to `docs/` instead. Additionally, `git_repo_agent.md` referenced the old single-file `blueprint/blueprint.md` instead of the two-file format.

**Pattern:** Every agent that produces files must have exact output paths in its definition. Without them, the agent guesses based on conventions and often guesses wrong.

**Fix:** Added explicit output paths to blueprint author agent definition and constraints. Fixed stale `blueprint.md` reference in git_repo_agent to `blueprint_prose.md` and `blueprint_contracts.md`.

---

*End of lessons learned.*
