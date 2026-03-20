# SVP — Stratified Verification Pipeline

## Stakeholder Specification v8.33 (SVP 2.1)

**Date:** 2026-03-17
**Supersedes:** v8.32 (SVP 2.1)
**Build Tool:** SVP 2.0

---

## How to Read This Document

This is the complete, self-contained stakeholder specification for SVP 2.1. It contains every behavioral requirement and every architectural constraint needed to produce a correct blueprint. The blueprint author reads this one document.

**Part II** contains all behavioral requirements — what the system must do. **Part III** contains architectural strategy — how the blueprint should be structured. The blueprint author needs both parts. Other agents (checker, diagnostic, redo) primarily need Part II.

**Change markers.** Sections unchanged from v6.0/v7.0 carry no marker. Sections modified by SVP 2.0 carry **(CHANGED IN 2.0)**. Sections modified or added by SVP 2.1 carry **(CHANGED IN 2.1)** or **(NEW IN 2.1)**. These markers are a scanning convenience — the full text is authoritative regardless.

**Separation of concerns with the blueprint.** This document describes behavior — what the human sees, what agents produce, what files the pipeline reads and writes. It does not prescribe function signatures, class hierarchies, or module boundaries. Where this spec must constrain the blueprint, it says so explicitly.

---

# PART II — BEHAVIORAL REQUIREMENTS

---

## 1. Purpose and Scope

SVP is a deterministically orchestrated, sequentially gated development system where a domain expert authors software requirements in natural language, and LLM agents generate, verify, and deliver a working Python project. The pipeline's state transitions, routing logic, and stage gating are controlled by deterministic scripts; the LLM agents that operate within this framework are not themselves deterministic, but are maximally constrained by a four-layer architecture of behavioral instruction, recency-reinforced reminders, structured agent output, and hook-based enforcement (see Section 3.6). The human never writes code. The system compensates for the human's inability to evaluate generated code through multi-agent cross-checking, forced diagnostic discipline, and human decision gates concentrated where domain expertise — not engineering skill — is the deciding factor.

This document is the stakeholder specification for building SVP itself. It describes what SVP must do, for whom, under what constraints, and what constitutes success or failure. It is written with awareness of the Claude Code ecosystem in which SVP operates, and specifically with awareness of that ecosystem's actual capabilities and constraints.

### 1.1 When SVP Is Appropriate

SVP is designed for projects where at least two of the following conditions hold:

- The human cannot evaluate the generated code for correctness.
- The system is complex enough that errors can cascade silently between components.
- The cost of undetected errors is high relative to the cost of slower development.

SVP is not appropriate when the human can competently evaluate the output, when the project is small enough that manual testing suffices, or when speed matters more than defensive depth.

### 1.2 Language and Environment Constraints (CHANGED IN 2.0)

- All generated code is Python.
- All tests use pytest.
- All environments are managed with Conda.
- All version control uses Git.
- The system runs inside Claude Code's terminal interface as a Claude Code plugin.
- The human interacts through typed conversation and explicit commands.

These constraints are fixed for the 2.x line. Pipeline tool commands are read from `toolchain.json` rather than hardcoded; the existing section commands are identical to SVP 1.2, and the `quality` section is purely additive (NEW IN 2.1). Future language support is delivered as separate products (see Section 27).

### 1.3 Project Size Constraint

SVP is designed for projects where the full blueprint fits within the effective context budget. The effective context budget is derived from the available context window of the active models, minus approximately 20,000 tokens overhead per subagent invocation. The budget defaults to the smallest usable context among all configured models and is configurable via override in `svp_config.json`. Projects exceeding this limit are out of scope.

### 1.4 Delivery Form (CHANGED IN 2.1)

SVP is delivered as a Claude Code plugin containing: skill files, agent definitions, slash commands, hooks, deterministic scripts, a configuration file, and a test suite for the deterministic components. SVP is also accompanied by a standalone `svp` launcher CLI tool.

The repository containing SVP has the following top-level structure:

```
svp-repo/                  <- repository root
|-- .claude-plugin/
|   +-- marketplace.json      <- marketplace catalog
|-- svp/                   <- the plugin subdirectory
|   |-- .claude-plugin/
|   |   +-- plugin.json       <- plugin manifest
|   |-- agents/
|   |-- commands/
|   |-- hooks/
|   |-- scripts/
|   |   |-- svp_launcher.py  <- standalone launcher
|   |   +-- toolchain_defaults/
|   |       |-- python_conda_pytest.json
|   |       +-- ruff.toml    <- quality tool configuration (NEW IN 2.1)
|   +-- skills/
|-- src/                      <- SVP source code (Python)
|-- tests/
|   +-- regressions/          <- carry-forward regression tests
+-- examples/
    +-- game-of-life/         <- bundled example
```

The SVP launcher lives at `svp/scripts/svp_launcher.py` and is referenced by the `pyproject.toml` entry point as `svp.scripts.svp_launcher:main`.

**Plugin discovery (CHANGED IN 2.1).** The launcher's `_find_plugin_root()` function must search the following locations, in order, after checking the `SVP_PLUGIN_ROOT` environment variable:

1. `~/.claude/plugins/svp/` — direct install
2. `~/.claude/plugins/cache/svp/svp/*/` — marketplace-installed versioned directories (all version subdirectories, sorted)
3. `~/.config/claude/plugins/svp/` — XDG config location
4. `/usr/local/share/claude/plugins/svp/` — system-wide (local)
5. `/usr/share/claude/plugins/svp/` — system-wide

A directory is a valid SVP plugin if it contains `.claude-plugin/plugin.json` whose `name` field equals `"svp"`. Validation must read and parse the JSON content — checking for directory existence alone is not sufficient.

The `marketplace.json` at the repository root registers the plugin for installation. Its schema requires a top-level `name`, `owner` (object with `name`), and `plugins` array. Each plugin entry requires `name`, `source` (relative path prefixed with `./`), `description`, `version`, and `author`.

The plugin subdirectory (`svp/`) contains all Claude Code plugin components at its root level: `commands/`, `agents/`, `skills/`, `hooks/`, and `scripts/`, with a `.claude-plugin/plugin.json` manifest. All component directories must be at the plugin subdirectory root level — not nested inside `.claude-plugin/`, and not at the repository root level.

SVP 2.1 ships with `toolchain_defaults/python_conda_pytest.json` containing the pipeline toolchain configuration and `toolchain_defaults/ruff.toml` containing the quality tool configuration. Both are copied to the project workspace during project creation.

**`ruff.toml` path indirection.** The `ruff.toml` file exists at two paths in the SVP repository: the plugin-relative source path (`svp/scripts/toolchain_defaults/ruff.toml`) and the workspace-relative destination path (`ruff.toml` at project root). The blueprint author must document both paths: the source path (used by the launcher during copy) and the destination path (used by quality gate scripts at runtime). The same file is also delivered as a plugin artifact at `svp/scripts/toolchain_defaults/ruff.toml` in Mode A self-build (see Section 12.13).

---

## 2. Target User Profile

The primary user is a domain expert with the following characteristics:

- Deep knowledge of their professional field (e.g., neuroscience, climate science, finance, logistics).
- Conceptual understanding of programming: knows what functions, classes, variables, loops, and conditionals are.
- Cannot author code in any specific language, or has only tutorial-level experience.
- Can read code and roughly follow its logic when guided, but cannot independently evaluate correctness.
- Can judge whether a test's assertion makes domain sense when explained in plain language.
- Can follow terminal instructions precisely but cannot troubleshoot environment problems independently.
- Has the statistical or quantitative literacy typical of their field.

SVP is domain-agnostic — the domain expertise enters through the stakeholder spec, not through the system's design.

---

## 3. Design Principles

These principles govern every design decision in SVP. When in doubt, refer to these.

### 3.1 Ruthless Restart

Any problem traced to a document — the stakeholder spec or the blueprint — triggers a fix to the document followed by a complete forward restart from the appropriate stage. No surgical repair of downstream artifacts. No blast radius analysis. Ruthless restart applies to what comes *after* the revised document — everything downstream is regenerated from scratch. It does not require redoing the work that came *before* the problem.

**Corollary — report most fundamental level.** When any agent identifies problems at multiple levels of the document hierarchy, it reports only the deepest problem. Spec problems supersede blueprint problems, which supersede implementation problems.

### 3.2 Binary Decision Logic

At every diagnostic failure point, the diagnosis produces a binary outcome: **implementation problem** (fix locally, continue) or **document problem** (fix document, restart). No third option. Binary decision logic applies to diagnostic gates. Approval gates support three or more options as appropriate.

### 3.3 Stateless Agents

Every agent invocation is a fresh instance with no memory of prior invocations. Where multi-turn conversation is required, conversation history is maintained through an append-only conversation ledger — a structured JSONL file. On each turn, the agent is freshly invoked with the full ledger as context.

Ledger growth is bounded. When a ledger approaches the context limit, the system warns the human. Compaction condenses exploratory exchanges while preserving all decisions, confirmed facts, `[HINT]` entries, and self-contained tagged lines. Agents produce tagged closing lines (`[QUESTION]`, `[DECISION]`, `[CONFIRMED]`) that must be self-contained — carrying their own rationale and context. The compaction script uses a character threshold (configurable, default 200): tagged lines above the threshold have bodies deleted; those at or below keep bodies as insurance. No LLM involvement in compaction.

### 3.4 Agent Separation

Different agents handle different roles. No agent both writes code and writes the tests for that code. No agent both authors and checks a document. The test agent and the implementation agent are always separate invocations with no shared context — the implementation agent never sees the tests. Both use `claude-opus-4-6` by default.

### 3.5 Human Judgment at Decision Gates

The human makes pipeline decisions at gates designed around their domain expertise: Is this spec correct? Does this test assertion make domain sense? Are we stuck because the spec is wrong? Decision gates present explicit response options. If the human's response does not match any option, the main session re-presents the options.

**Hint-blueprint conflicts.** When an agent receives a human domain hint that contradicts the blueprint contract, the agent returns `HINT_BLUEPRINT_CONFLICT: [details]`. The routing script presents a binary gate: blueprint correct (discard hint) or hint correct (document revision, restart).

The human is not limited to domain-only observations. At any decision gate, the human may collaborate with the Help Agent (Section 14) to formulate engineering-level suggestions. These suggestions are a signal, not a command — the receiving agent evaluates the hint alongside the blueprint contract, diagnostic analysis, and its own judgment.

### 3.6 Maximally Constrained Orchestration

The main session acts as the orchestration layer, constrained through a four-layer architecture:

**Layer 1 — CLAUDE.md.** Loaded at session start. Identifies the project as SVP-managed and defines the orchestration protocol. Influence degrades as context accumulates.

**Layer 2 — Routing script REMINDER.** Every routing script output includes a mandatory REMINDER block at the end, reinforcing critical behavioral constraints at the point of highest context recency:

```
REMINDER:
- Execute the ACTION above exactly as specified.
- When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt verbatim. Do not summarize, annotate, or rephrase.
- Wait for the agent to produce its terminal status line before proceeding.
- Write the agent's terminal status line to .svp/last_status.txt.
- Run the POST command if one was specified.
- Then re-run the routing script for the next action.
- Do not improvise pipeline flow. Do not skip steps. Do not add steps.
- If the human types during an autonomous sequence, acknowledge and defer: complete the current action first.
```

**Layer 3 — Agent terminal status lines.** Every subagent produces a structured terminal status line as its final output. The routing script recognizes these and dispatches accordingly.

**Layer 4 — Hooks and universal write authorization.** Enforcement at boundaries, blocking unauthorized actions regardless of what the main session attempts.

No single layer is sufficient. Together, they provide defense in depth.

**The six-step mechanical action cycle:**

1. Run the routing script → receive a structured action block.
2. Run the PREPARE command (if present) → produces a task prompt or gate prompt file.
3. Execute the ACTION (invoke agent / run command / present gate).
4. Write the result to `.svp/last_status.txt`.
5. Run the POST command (if present) → updates pipeline state.
6. Go to step 1.

The main session never decides which state update to call, never constructs arguments for state scripts, and never reasons about what should happen next.

**Status file state invariant.** `.svp/last_status.txt` contains the result of the most recently completed action. Commands reading this file during their own execution are reading the *previous* action cycle's result.

**Two-branch routing invariant (NEW IN 2.1 — generalized Bug 21 fix).** Every sub-stage where an agent completion should trigger a different action (gate presentation or deterministic command) rather than re-invocation has two reachable states: (1) the agent has not yet been invoked or has not yet completed, and (2) the agent has completed (indicated by its terminal status line in `last_status.txt`). The `route()` function must distinguish these two states for every such sub-stage. In state (1), it emits an `invoke_agent` action. In state (2), it emits the appropriate next action — typically a `human_gate` for the corresponding gate, or a `run_command` for a deterministic check (as in quality gate retry sub-stages). If `route()` always returns the agent invocation without checking `last_status.txt`, the pipeline loops indefinitely re-invoking the agent after its work is already done.

This is a structural invariant, not a per-stage fix. The complete list of sub-stages governed by this invariant follows, in two groups distinguished by what the "done" branch emits:

**Gate-presenting entries** — the "done" branch emits a `human_gate` action:

- **Stage 0, `project_context`:** check for `PROJECT_CONTEXT_COMPLETE` before presenting `gate_0_2_context_approval` (Section 6.3).
- **Stage 0, `project_profile`:** check for `PROFILE_COMPLETE` before presenting `gate_0_3_profile_approval` (Section 6.4).
- **Stage 1, `stakeholder_spec_authoring` (sub_stage=None):** check for `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE` before presenting `gate_1_1_spec_draft` (Section 7.4). Note: `stakeholder_spec_authoring` is a descriptive label for this routing branch, not a literal sub-stage value; Stage 1 uses `sub_stage: None` throughout (see Section 22.4).
- **Stage 1, reviewer completion (sub_stage=None):** check for `REVIEW_COMPLETE` before presenting `gate_1_2_spec_post_review` (Section 7.4). When the stakeholder spec reviewer agent (invoked via FRESH REVIEW at Gate 1.1 or Gate 1.2) completes, `route()` must present Gate 1.2, not re-invoke the reviewer. Disambiguation from the dialog agent's status is by prefix: `REVIEW_COMPLETE` routes to Gate 1.2, while `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` route to Gate 1.1 (see Section 18.1, `REVIEW_COMPLETE` disambiguation).
- **Stage 2, `blueprint_dialog`:** check for `BLUEPRINT_DRAFT_COMPLETE` or `BLUEPRINT_REVISION_COMPLETE` before presenting `gate_2_1_blueprint_approval` (Section 8.1).
- **Stage 2, reviewer completion (`blueprint_dialog` sub-stage):** check for `REVIEW_COMPLETE` before presenting `gate_2_2_blueprint_post_review` (Section 8.2). When the blueprint reviewer agent (invoked via FRESH REVIEW at Gate 2.1 or Gate 2.2) completes, `route()` must present Gate 2.2, not re-invoke the reviewer. Disambiguation from the blueprint author's status is by prefix: `REVIEW_COMPLETE` routes to Gate 2.2, while `BLUEPRINT_DRAFT_COMPLETE` / `BLUEPRINT_REVISION_COMPLETE` route to Gate 2.1. Stage-level disambiguation (Stage 1 vs Stage 2) uses the current stage number from `pipeline_state.json` (see Section 18.1, `REVIEW_COMPLETE` disambiguation).
- **Stage 2, `alignment_check`:** check for `ALIGNMENT_CONFIRMED` or `ALIGNMENT_FAILED:*` before dispatching the alignment outcome (Gate 2.2 on confirmation, restart on failure) (Section 8.2).
- **Stage 5:** check for `REPO_ASSEMBLY_COMPLETE` before presenting `gate_5_1_repo_test` (Section 12.1).
- **Post-delivery debug loop, triage agent (reproducible):** check for `TRIAGE_COMPLETE: single_unit` or `TRIAGE_COMPLETE: cross_unit` before presenting Gate 6.2 (`gate_6_2_debug_classification`) (Section 12.17.4 Steps 1-2). Note: `TRIAGE_COMPLETE: build_env` does NOT present Gate 6.2 -- it routes directly to the build/environment repair agent via the fast path (Section 12.17.3).
- **Post-delivery debug loop, triage agent (non-reproducible):** check for `TRIAGE_NON_REPRODUCIBLE` before presenting Gate 6.4 (`gate_6_4_non_reproducible`) (Section 12.17.7).
- **Post-delivery debug loop, repair agent:** check for `REPAIR_COMPLETE`, `REPAIR_RECLASSIFY`, or `REPAIR_FAILED` (with retries exhausted) before dispatching the repair outcome (Sections 12.17.3, 12.17.6, 12.17.8, 18.1). `REPAIR_COMPLETE` routes to the success path: reassembly and debug completion (Section 12.17.6) -- it does NOT present Gate 6.3. `REPAIR_RECLASSIFY` and `REPAIR_FAILED` (with retries exhausted) present Gate 6.3 (`gate_6_3_repair_exhausted`) for the human to decide: RETRY REPAIR, RECLASSIFY BUG, or ABANDON DEBUG. Note: `REPAIR_FAILED` with retries remaining triggers re-invocation of the repair agent (not governed by this invariant -- see Section 18.1).
- **Post-delivery debug loop, test agent (regression test mode):** check for `REGRESSION_TEST_COMPLETE` before presenting Gate 6.1 (`gate_6_1_regression_test`) (Section 12.17.4 Step 5).
- **Redo profile sub-stages, `redo_profile_delivery`:** check for `PROFILE_COMPLETE` before presenting Gate 0.3r (`gate_0_3r_profile_revision`) (Section 13, `/svp:redo`).
- **Redo profile sub-stages, `redo_profile_blueprint`:** check for `PROFILE_COMPLETE` before presenting Gate 0.3r (`gate_0_3r_profile_revision`) (Section 13, `/svp:redo`).
- **Stage 3, diagnostic escalation (triggered by `fix_ladder_position: "diagnostic"`):** check for `DIAGNOSIS_COMPLETE` before presenting Gate 3.2 (`gate_3_2_diagnostic_decision`) (Section 10.11). Diagnostic escalation is not keyed on a named sub-stage value; it is triggered when the fix ladder position reaches `"diagnostic"` (see Section 10.10, ladder progression: `None -> fresh_impl -> diagnostic -> diagnostic_impl -> exhausted`). The sub-stage remains at `"green_run"` or `"implementation"` during the fix ladder; `route()` must check `fix_ladder_position` to determine whether the diagnostic agent should be invoked. When the diagnostic agent completes with `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec`, the routing script must present Gate 3.2 for the human to confirm the fix direction, not re-invoke the diagnostic agent.

**Gates not governed by the two-branch invariant.** Nine gate IDs from Section 18.4 are intentionally absent from the exhaustive list above: `gate_0_1_hook_activation` (Gate 0.1 is presented unconditionally at session start, not after an agent completion), `gate_6_5_debug_commit` (Gate 6.5 is presented after a deterministic commit preparation step, not after an agent completion), `gate_hint_conflict` (Gate H.1 is presented by the hint system when a conflict is detected, not as part of an agent-to-gate routing transition; it IS present in `GATE_VOCABULARY` and `ALL_GATE_IDS` because it has defined response options, but it is exempt from the two-branch routing pattern), `gate_2_3_alignment_exhausted` (Gate 2.3 is presented when the alignment iteration counter is exhausted after an `ALIGNMENT_FAILED` result -- the counter-based dispatch is deterministic and handled within `dispatch_agent_status`, not as a separate routing branch requiring a `last_status.txt` two-branch check), `gate_3_1_test_validation` (Gate 3.1 is presented after a deterministic test run command completes, not after an agent completion), `gate_4_1_integration_failure` (Gate 4.1 is presented after integration tests fail via a deterministic test command, not after an agent completion -- see Section 11.2.1 three-state dispatch), `gate_4_2_assembly_exhausted` (Gate 4.2 is presented when the assembly fix ladder retry counter is exhausted, not after an agent completion), `gate_5_2_assembly_exhausted` (Gate 5.2 is presented when Stage 5 assembly retries are exhausted, not after an agent completion), and `gate_6_0_debug_permission` (Gate 6.0 is presented when a `/svp:bug` command is issued, not after an agent completion -- it is an entry gate for the debug loop). These gates do not follow the agent-completion/gate-presentation pattern and therefore do not require a two-branch `last_status.txt` check in `route()`.

**Command-presenting entries** — the "done" branch emits a `run_command` action (a deterministic tool invocation, not a human gate):

- **Stage 3, `quality_gate_a_retry`:** check for `TEST_GENERATION_COMPLETE` before re-running Gate A tools (Section 10.12). If the test agent has not yet completed, re-invoke it; if it has, run the quality gate deterministic check.
- **Stage 3, `quality_gate_b_retry`:** check for `IMPLEMENTATION_COMPLETE` before re-running Gate B tools (Section 10.12). Same two-branch structure as Gate A retry.
- **Stage 3, `coverage_review`:** check for `COVERAGE_COMPLETE` (either `COVERAGE_COMPLETE: no gaps` or `COVERAGE_COMPLETE: tests added`) before dispatching the coverage review completion flow (Section 10.8). If the coverage review agent has not yet completed, invoke it; if it has completed with `COVERAGE_COMPLETE: tests added`, run the auto-format `run_command` actions within the `coverage_review` sub-stage before advancing to red-green validation; if it has completed with `COVERAGE_COMPLETE: no gaps`, advance directly to `unit_completion`. The auto-format commands execute within the `coverage_review` sub-stage's completion flow (Section 10.8), so `route()` must distinguish "agent not done" from "agent done" while the sub-stage is still `coverage_review`.
- **Stage 4:** check for `INTEGRATION_TESTS_COMPLETE` before running the integration test suite (Section 11.1). If the agent has not yet completed, re-invoke it; if it has, run the integration test command.

The blueprint must implement `route()` such that adding a new agent-to-gate sub-stage automatically requires a two-branch check. Regression tests must verify both branches (agent-not-done and agent-done) for every sub-stage in this list. A regression test that only verifies the agent invocation branch is incomplete.

**Universal compliance requirement (NEW IN 2.1 — Bug 43 fix).** The two-branch routing invariant must be applied universally in a single implementation pass, not incrementally as bugs are discovered in individual stages. Bugs 21, 41, and 43 demonstrated that applying the invariant piecemeal -- fixing only the stage where the bug was observed and leaving other stages unprotected -- leads to the same bug recurring in every unprotected stage. A universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`) must verify that EVERY entry in the exhaustive list above has a corresponding two-branch check in `route()`. The test must fail if a new gate-presenting or command-presenting entry is added to the spec without a routing-level check. Additionally, the test must verify cross-unit consistency: every key in `GATE_VOCABULARY` (routing module) appears in `ALL_GATE_IDS` (preparation module) and has a gate prompt handler. The test covers both the gate-presenting and command-presenting categories. This is the definitive structural test for the two-branch invariant -- it supersedes per-stage regression tests as the primary compliance mechanism, though per-stage tests remain as defense in depth.

**Gate ID consistency invariant (NEW IN 2.1 — Bug 41 fix).** Every gate ID that appears in routing dispatch tables (e.g., `GATE_RESPONSES` in the routing script) must also be registered in gate preparation registries (e.g., `ALL_GATE_IDS` in the preparation script). Conversely, every gate ID in a preparation registry should have a corresponding entry in the routing dispatch table. If a gate ID exists in the routing dispatch but not in the preparation registry, `prepare_gate_prompt()` raises a `ValueError` when the gate is triggered. If a gate ID exists in the preparation registry but not in the routing dispatch, the gate is never reachable. Both conditions are bugs. A structural test must verify that the set of gate IDs in `GATE_RESPONSES` is identical to the set of gate IDs in `ALL_GATE_IDS`. This test must be a carry-forward regression test. The complete gate ID vocabulary is enumerated in Section 18.4.

**Gate reachability and dispatch exhaustiveness invariant (NEW IN 2.1 -- Bugs 65-69 fix, P10 root cause).** Every gate in GATE_VOCABULARY must have a reachable code path in `route()` that presents it. Every response option in every gate must produce a meaningful state transition in `dispatch_gate_response` (not a bare `return state`), unless the response is an intentional two-branch no-op where the gate response written to `last_status.txt` drives the next routing decision. Intentional two-branch no-ops must be explicitly documented as such in the Tier 3 contract. This invariant applies across ALL pipeline stages (Stages 0-5 and the debug loop) -- not just the stage where a particular bug was discovered. Bugs 65-69 demonstrated that the same disease (P10: Error-Path Contract Omission) affected every stage independently. A structural regression test must verify that every gate in GATE_VOCABULARY is reachable from `route()` for at least one valid pipeline state. Gates that are intentionally triggered by external mechanisms (e.g., `gate_hint_conflict` triggered by the orchestration layer, `gate_0_1_hook_activation` presented unconditionally at session start) must be documented as exceptions in the test.

**Route-level state persistence invariant (NEW IN 2.1 — Bug 42 fix).** Any `route()` branch that performs an in-memory state transition (via a `complete_*` or `advance_*` helper function) and then recursively calls `route()` or returns an action block for a different sub-stage must persist the intermediate state to disk (via `save_state()`) before returning the action block. Without persistence, the POST command of the returned action block loads stale state from disk via `update_state.py`, losing the in-memory transition. This creates an invisible state rollback: the action block executes against the new state, but `update_state.py` overwrites it with the old state, and subsequent routing calls see the old state — potentially creating infinite loops. Structural tests must verify that every `complete_*` or `advance_*` call in `route()` is followed by a `save_state()` call before any recursive `route()` call or action block return.

**Exhaustive dispatch_agent_status invariant (NEW IN 2.1 — Bug 42 fix, CHANGED IN 2.1 — Bugs 44, 46 fix).** Every agent type registered in `dispatch_agent_status` must explicitly handle its success status line with a state transition that advances the pipeline (modifying at least one of `stage`, `sub_stage`, or a state flag). A bare `return state` (no field changes) is only valid when the agent's completion genuinely does not require a stage/sub-stage change — for example, slash-command-initiated agents (help, hint) whose completion returns control to the current pipeline position. For agents on the main pipeline path (reference indexing, git repo agent, blueprint checker, triage agent, repair agent, test agent, coverage review agent, etc.), a bare `return state` is a bug — it leaves the pipeline stuck at the current position with no mechanism to advance. A structural test must verify that every main-pipeline agent type in `dispatch_agent_status` modifies at least one state field in its success handler. The routing function and dispatch function must have consistent null-handling for `sub_stage`: when routing treats `None` as equivalent to a named sub_stage (e.g., `test_generation`), the dispatch must also accept `None` for that agent type (Bug 44 fix).

**Exhaustive dispatch_command_status invariant (NEW IN 2.1 — Bug 45 fix, CHANGED IN 2.1 — Bug 65 fix).** Every `dispatch_command_status` handler for `test_execution` must produce a state transition for the expected outcome at each sub-stage. No-op returns (`return state`) are invalid for `red_run` (`TESTS_FAILED` must advance to `implementation`) and `green_run` (`TESTS_PASSED` must advance to `coverage_review`). A `dispatch_command_status` handler that returns state unchanged for a status line that requires advancement is a bug — it leaves the pipeline stuck re-running the same command indefinitely. A structural test must verify that `dispatch_command_status` for `test_execution` advances `sub_stage` for each expected status/sub_stage combination.

**Extended exhaustive dispatch table (Bug 65 fix).** The invariant above covers only two happy-path cases. The complete dispatch table for ALL (phase, sub_stage, status) combinations in Stage 3 is:

| Phase | Sub-stage | Status | Required transition |
|-------|-----------|--------|-------------------|
| `stub_generation` | `None` / `stub_generation` | `COMMAND_SUCCEEDED` | advance to `test_generation` |
| `test_execution` | `red_run` | `TESTS_FAILED` | advance to `implementation` |
| `test_execution` | `red_run` | `TESTS_PASSED` | increment `red_run_retries`; if < limit: regenerate tests (`test_generation`); if >= limit: present Gate 3.1 (`gate_3_1`) |
| `test_execution` | `green_run` | `TESTS_PASSED` | advance to `coverage_review` |
| `test_execution` | `green_run` | `TESTS_FAILED` | advance fix ladder: `None` -> `fresh_impl` (implementation); `fresh_impl` -> `diagnostic` (implementation); `diagnostic_impl` -> exhausted (`gate_3_2`) |
| `quality_gate` | `quality_gate_a` / `quality_gate_b` | `COMMAND_SUCCEEDED` | advance to next sub-stage (`red_run` / `green_run`) |
| `quality_gate` | `quality_gate_a` / `quality_gate_b` | `COMMAND_FAILED` | advance to retry sub-stage |
| `unit_completion` | `unit_completion` | `COMMAND_SUCCEEDED` | complete unit, advance to next |

Silence (bare `return state`) is not a valid contract outcome for any entry in this table. Every cell must produce a distinct state transition.

**COMMAND/POST separation invariant (NEW IN 2.1 — Bug 47 fix).** COMMAND fields in routing action blocks must never embed state update calls (`update_state.py`). State updates are exclusively the responsibility of POST commands. If a COMMAND embeds a state update call and a POST command also invokes `update_state.py` for the same phase, the state update runs twice, causing a `TransitionError` on the second invocation. The COMMAND should only produce output, write status files, or execute deterministic tool commands; the POST command handles state transitions. This applies to all routing action blocks, not just `unit_completion` (though Bug 47 was discovered there).

**CLI argument enumeration invariant (NEW IN 2.1 — Bug 48 fix, STRENGTHENED — Bug 49 fix).** Any blueprint Tier 2 function signature that accepts `argv` and uses `argparse` internally must enumerate every `add_argument` call (argument name, type, required/optional) in the Tier 2 invariants section. Prose-only descriptions in Tier 3 are insufficient for CLI contracts. Without explicit enumeration, the implementation agent has no way to determine which arguments to implement, leading to missing arguments, incorrect names, or wrong semantics. This invariant applies to ALL units that produce CLI entry points, not just Unit 24. The blueprint checker must verify compliance across all units. Units with CLI entry points as of SVP 2.1: Unit 6 (`main`), Unit 7 (`main`), Unit 9 (`main`), Unit 10 (`update_state_main`, `run_tests_main`, `run_quality_gate_main`), Unit 23 (`compliance_scan_main`), Unit 24 (`parse_args`). A structural regression test (`test_bug49_argparse_enumeration.py`) verifies that every CLI entry point accepts its documented arguments.

**Session cycling.** The SVP launcher manages automatic session cycling at every major pipeline transition. The mechanism: the main session writes a restart signal file and exits; the launcher detects it and relaunches Claude Code. The new session reads CLAUDE.md, runs the routing script, and picks up from the state file. See Section 16.

**State management.** The routing script predetermines the POST command at the time it specifies the action. State-update scripts validate preconditions before writing new state. This makes the scripts — not the hooks and not the LLM — the primary stage-gating mechanism.

### 3.7 Explicit Context Loading

Every agent invocation has an explicit context loading protocol:

- **Role context (system prompt):** Static behavioral instructions from the agent definition file.
- **Task context (task prompt):** Dynamic project-specific content assembled by a deterministic preparation script.
- **On-demand context (disk reads):** Files the agent reads from the workspace during execution when full content is too large for the task prompt.

The preparation scripts are deterministic with no LLM involvement.

### 3.8 Transparency on Demand

During autonomous work, the human sees minimal output. When the pipeline needs the human, it presents a clear summary. The human can request detailed explanations through the help agent at any time.

### 3.9 Speed-Correctness Tradeoff

SVP chooses the path that requires less LLM judgment and more human involvement. The value proposition is making coding possible for people who could not do it at all, not making it fast.

### 3.10 Always Clean Spec

Working notes are absorbed into the spec body at every iteration boundary. The stakeholder spec is never a patched document with appended addenda.

### 3.11 Human at Readiness Boundary

The pipeline refuses to proceed if the human has not provided sufficient context. If after multiple attempts the human cannot provide substantive answers, the pipeline suggests they return when they have thought more about their requirements.

### 3.12 Universal Write Authorization

SVP-managed projects are protected by a two-layer write authorization system: filesystem permissions managed by the launcher, and hooks that validate every write against the current pipeline state. The complete specification is in Section 19.

### 3.13 Explicit Delivery Intent (CHANGED IN 2.0)

The human's preferences about how their project should be delivered are first-class inputs captured during setup. They are not inferred, not defaulted silently, and not hardcoded. The setup agent asks. The human answers. The answers are recorded in `project_profile.json`. Downstream agents read the profile and act accordingly.

### 3.14 Pipeline Toolchain as Data (CHANGED IN 2.0)

SVP's own tool commands are read from `toolchain.json` rather than hardcoded. The file is not a plugin system, provider registry, or class hierarchy. It is a flat JSON file read with `json.load()`.

### 3.15 Three-Layer Preference Enforcement (CHANGED IN 2.0)

The human's tool preferences must be respected by the delivered code. SVP enforces preferences through three layers:

**Layer 1 — Blueprint contracts.** The blueprint author translates profile preferences into explicit behavioral contracts.

**Layer 2 — Blueprint checker validation.** The checker verifies that every profile preference is reflected as an explicit contract in at least one unit.

**Layer 3 — Delivery compliance scan.** A deterministic script reads the profile and scans delivered Python source files for banned patterns.

### 3.16 Blueprint Prose/Contracts Split (NEW IN 2.1)

The blueprint is split into two files that together constitute a single logical document:

- **`blueprint_prose.md`** — Tier 1 descriptions only. Free prose defining the purpose, inputs, outputs, and role of each unit. Read by agents that need to understand what a unit does: the blueprint author, the blueprint checker, the diagnostic agent, and the help agent.

- **`blueprint_contracts.md`** — Tier 2 machine-readable signatures plus Tier 3 error conditions, behavioral contracts, and dependency lists. Read by agents that need to implement or test a unit: the test agent, the implementation agent, the stub generator, and the git repo agent during assembly.

The two files are an atomic pair. They must always be versioned together. A version of the blueprint is a version of both files simultaneously — a change to one file without a corresponding update to the other is a blueprint-level integrity failure. The blueprint author produces both files in every draft and revision. The blueprint checker receives both files and validates their internal consistency as part of the alignment check.

**Who reads what (CHANGED IN 2.1 -- Bugs 60-62 fix, now implemented):**
- Blueprint author agent: both files (authoring)
- Blueprint checker agent: both files (alignment validation)
- Blueprint reviewer agent: both files (review)
- Test agent: `blueprint_contracts.md` only (via `build_unit_context` with `include_tier1=False`)
- Implementation agent: `blueprint_contracts.md` only (via `build_unit_context` with `include_tier1=False`)
- Diagnostic agent: both files (via `build_unit_context` with `include_tier1=True`)
- Help agent: `blueprint_prose.md` primary (via `load_blueprint_prose_only`)
- Hint agent: both files (full context for domain hints)
- Integration test author: `blueprint_contracts.md` only (via `load_blueprint_contracts_only`)
- Git repo agent: `blueprint_contracts.md` for assembly mapping (via `load_blueprint_contracts_only`)
- Bug triage agent: both files (full context for diagnosis)
- Repair agent: both files (full context for fix)

**Selective loading implementation (Bugs 60-62 fix).** Unit 9 (`prepare_task.py`) exports three loader functions: `load_blueprint()` (both files concatenated), `load_blueprint_contracts_only()` (contracts file only), and `load_blueprint_prose_only()` (prose file only). Unit context assembly via `build_unit_context` (Unit 5) respects the `include_tier1` parameter to exclude Tier 1 descriptions. The `_get_unit_context` internal helper in Unit 9 passes `include_tier1` through to `build_unit_context` and resolves the blueprint directory via `get_blueprint_dir()` (which reads `ARTIFACT_FILENAMES["blueprint_dir"]` from Unit 1).

**Context budget impact:** This split is a token reduction measure. The Tier 1 descriptions are excluded from the task prompts of the two most frequently invoked agents (test and implementation). The saving compounds across all units, passes, and retries. No information is lost to any agent that needs it.

**Contract sufficiency invariant (NEW IN 2.1 -- Bug 50 fix).** A Tier 3 behavioral contract is sufficient if and only if an implementation agent reading ONLY the Tier 2 signature and Tier 3 contract (with no access to the spec, prior implementations, or context) could produce a correct implementation. If the function's behavior depends on specific values (lookup tables, enum validation sets, magic numbers, algorithm parameters, file paths for side effects), those values must appear in the Tier 2 invariants or Tier 3 contract. The test: "remove the spec and all prior code -- can the contract alone produce a correct implementation?"

**Contract boundary rule (NEW IN 2.1 -- Bug 50 fix).** The blueprint MUST NOT include internal helper function signatures in Tier 2. Internal helpers are functions that: (a) are prefixed with underscore, (b) are not imported by any other unit, and (c) could be replaced by a different implementation without affecting any test. The blueprint MUST include in Tier 3 any behavioral detail that affects observable correctness -- including specific values for lookup tables, validation sets, and algorithm parameters. The boundary test: "if changing an implementation detail would cause a test to fail, that detail must be contracted; if changing it would not affect any observable behavior, it must not be contracted."

### 3.17 Pipeline Quality Guarantee (NEW IN 2.1)

Every project built by SVP 2.1 is automatically formatted, linted, and type-checked during the build. Quality is a pipeline guarantee, not an opt-out feature. Deterministic quality tools run at defined points in the verification cycle:

- After test generation, before the red run (format + light lint).
- After implementation, before the green run (format + heavy lint + type check).
- During Stage 5 assembly, before delivery (cross-unit format check + full lint + type check).

Quality tools auto-fix mechanically resolvable issues (formatting, import sorting, simple lint violations). Issues that tools cannot auto-fix are escalated to the producing agent for one re-pass. If residuals persist after the re-pass, the quality gate fails and enters the existing fix ladder. Quality gate retries are separate from the fix ladder retry budget.

### 3.18 Downstream Dependency Invariant for Re-entry Paths (NEW IN 2.1 -- Bug 56 fix)

For every pipeline re-entry path that modifies a unit's implementation -- including FIX UNIT (Gate 6.2), fix ladder retry, and any stage restart that targets a specific unit -- the pipeline must analyze whether downstream units remain valid. If unit N's implementation changes, all units >= N must be invalidated and rebuilt. No surgical repair of downstream artifacts. No assumption that units N+1 through M remain correct after unit N changes.

This extends the Ruthless Restart principle (Section 3.1) from document-level restart to implementation-level re-entry. Section 3.1 requires that document changes trigger complete forward restart from the appropriate stage. Section 3.18 requires that implementation changes trigger complete forward rebuild from the affected unit. The reasoning is identical: downstream artifacts were generated from upstream artifacts. If an upstream artifact changes, all downstream artifacts are potentially stale.

**Scope.** This invariant applies to:
- **FIX UNIT** at Gate 6.2: calls `rollback_to_unit(N)`, which invalidates all verified units >= N and rebuilds from N forward.
- **Fix ladder retry:** re-runs the current unit's implementation; downstream units are not yet verified, so no invalidation needed (the pipeline has not advanced past the current unit).
- **Stage restart** (`restart_from_stage`): already destroys all downstream state by resetting to the target stage. No additional analysis needed.

The spec author, when defining any new re-entry path, must explicitly state what happens to downstream units. The blueprint checker must verify that every re-entry path in the blueprint either invalidates downstream units or documents why invalidation is unnecessary.

### 3.19 Contract Granularity Rules (NEW IN 2.1 -- Bug 56 fix)

The contract sufficiency invariant (Section 3.16) requires that Tier 3 behavioral contracts be sufficient for deterministic reimplementation. This section strengthens that requirement with explicit granularity rules:

1. **Exported function coverage.** Every function listed in a unit's Tier 2 machine-readable signatures MUST have a corresponding Tier 3 behavioral contract. A Tier 2 signature without a Tier 3 contract is a blueprint alignment failure. The contract must specify: preconditions, postconditions, side effects, error conditions, and the relationship between inputs and outputs.

2. **Per-gate-option dispatch contracts.** Every gate response option in `GATE_VOCABULARY` MUST have a Tier 3 dispatch contract in the routing unit (Unit 10) specifying the exact state transition that occurs when the human selects that option. A gate option without a dispatch contract is a blueprint alignment failure. The contract must specify: which transition functions are called, in what order, with what arguments, and what the resulting state looks like.

3. **Call-site verification.** Every state transition function defined in the state transitions unit (Unit 3) MUST have at least one call site in the routing unit (Unit 10) or another unit that invokes it. A function with no call site is dead code and must be removed or wired. The blueprint checker must verify that every exported function has a documented call site.

**Blueprint checker requirements.** The blueprint checker (Section 8.2) MUST verify all three rules as alignment conditions during the alignment check. Violations are unconditional alignment failures, not warnings.

### 3.20 Review Enforcement — Baked Checklists (NEW IN 2.1 -- Bug 57 fix)

The downstream dependency invariant (Section 3.18) and contract granularity rules (Section 3.19) are enforced through two complementary mechanisms:

1. **Deterministic check at Gate C (assembly time).** Gate C's unused function detection (`linter.unused_exports`) catches the symptom -- functions defined but never called -- in assembled code. This is a machine check that runs at Stage 5. If findings exist, Gate 5.3 presents them to the human.

2. **LLM-driven review checks at Gates 1.1/1.2 and 2.1/2.2 (authoring time).** The stakeholder spec reviewer, blueprint checker, and blueprint reviewer agents each have mandatory review checklists baked into their agent definitions. These checklists require the review agents to explicitly verify downstream dependency analysis, contract granularity, per-gate dispatch contracts, call-site traceability, re-entry invalidation, and gate reachability (for every gate in GATE_VOCABULARY, verify there exists a route() code path that presents it; for every gate response option, verify dispatch_gate_response produces a state transition or is documented as an intentional two-branch no-op -- Bugs 65-69 P10 fix). The checklists are part of the agent's system prompt and run automatically during every spec review and blueprint review -- no human action required to activate them.

The two mechanisms are complementary: the review checklists catch the root cause (spec/blueprint gaps) at authoring time; the Gate C check catches the symptom (dead code) at assembly time. Neither alone is sufficient. The review checklists are LLM-driven and advisory (the review agent flags issues but does not block progress mechanically); the Gate C check is deterministic and presents a human gate.

### 3.21 Structural Completeness Test Suite (NEW IN 2.1 -- Bug 71 fix)

The regression test file `tests/regressions/test_bug71_structural_completeness.py` provides a third enforcement layer: 14 automated guard tests that verify declaration-vs-usage consistency across the pipeline's constants, dispatch tables, routing functions, and state transitions. These tests run as part of the standard pytest suite and catch classes of bugs that neither LLM review nor Gate C can detect (e.g., a gate declared in GATE_VOCABULARY but missing from route(), or a status line declared in AGENT_STATUS_LINES but not handled by dispatch).

The 14 techniques are: (1) gate vocabulary vs route reachability, (2) response options vs dispatch handlers, (3) exported functions vs call sites, (4) stub vs script constant synchronization, (5) skipped (narrative-only), (6) per-agent loading matrix, (7) agent status lines vs dispatch, (8) known agent types vs route invocations, (9) debug phase transitions vs route handlers, (10) sub-stages vs route branches, (11) fix ladder positions vs route context, (12) command status patterns vs phase handlers, (13) phase-to-agent map vs known phases, (14) debug phase transitions vs known phases.

This suite must be maintained as the pipeline evolves: any new gate, agent type, status line, sub-stage, debug phase, or fix ladder position must be reflected in the corresponding stub constants, script constants, and structural tests.


### 3.22 Generalized Structural Completeness Checking -- Four-Layer Defense (NEW IN 2.1 -- Bug 72 fix)

SVP employs a four-layer defense system for structural completeness that works for any Python project, not just SVP itself:

**Layer 1 -- Blueprint checker prompt update.** The blueprint checker agent definition includes a mandatory registry completeness checklist item. The checker must identify every registry, vocabulary, enum, or dispatch table declared in the blueprint and verify that every declared value has a corresponding handler/branch contract in at least one unit. A registry value with no handler contract is an alignment failure.

**Layer 2 -- Integration test author prompt update.** The integration test author agent definition includes a requirement to generate registry-handler alignment tests. For every registry, dispatch table, vocabulary, and enum-like constant in the codebase, the integration test author generates a pytest test that collects all declared values via AST, collects all values handled in the corresponding dispatch logic, and asserts bidirectional coverage.

**Layer 3 -- Deterministic structural check script.** `scripts/structural_check.py` is a project-agnostic AST scanner that performs four high-confidence, low-false-positive checks: (1) dict registry keys never dispatched, (2) enum values never matched, (3) exported functions never called, (4) string dispatch gaps (registry-linked). The script uses only stdlib imports (ast, json, pathlib, argparse, sys) and has no project-specific knowledge. It runs as a Stage 5 sub-stage (`structural_check`) between `repo_test` and `compliance_scan`. CLI: `python scripts/structural_check.py --target <path> [--format json|text] [--strict]`. In `--strict` mode, any findings produce exit code 1.

**Layer 4 -- Triage agent pre-computation.** The bug triage agent task prompt includes structural check results (pre-computed by `prepare_task.py` running `structural_check.py` against the delivered repo). The triage agent reviews these results in Step 0 before reproducing the bug. If a structural finding directly explains the reported symptom, the agent classifies immediately. The triage agent definition also includes a Registry Diagnosis Recipe for manual investigation.

The four layers are complementary: Layer 1 catches gaps at blueprint authoring time (LLM-driven), Layer 2 generates persistent regression guards (test-driven), Layer 3 catches gaps at assembly time (deterministic), and Layer 4 accelerates post-delivery debugging (diagnostic).

---

## 4. Platform Constraints

SVP operates within Claude Code's architecture, which imposes constraints that are inherent properties of the platform.

### 4.1 Task Prompt Relay Fidelity

Task prompt content must transit through the main session's context window to reach the Task tool. The main session may transform the content.

**Mitigations:** CLAUDE.md instructs verbatim relay. The REMINDER reinforces this. Routing script output specifies TASK_PROMPT_FILE path, not content. Preparation scripts produce bounded, structured content.

### 4.2 Agent Tool Restriction Enforcement (CHANGED IN 2.1)

Agent tool restrictions specified in AGENT.md are reinforced by Claude Code's hook system. `PreToolUse` command hooks with exit code 2 provide hard enforcement — the operation is blocked before execution, not merely discouraged.

**Defense in depth remains the design posture.** The help agent's read-only guarantee is supported by three independent layers: the AGENT.md tool whitelist, the `PreToolUse` command hooks (which definitively block unauthorized writes via exit code 2), and the universal write authorization system (Section 19). No single layer is relied upon exclusively, even though the hook layer alone now provides hard enforcement.

### 4.3 Cross-Platform Portability

SVP runs on any platform where Claude Code and conda are available. All deterministic scripts must be OS-agnostic.

**Constraints:**
- No hardcoded OS-specific paths or conda installation directories.
- All subprocess invocations targeting the project environment must use `conda run -n {env_name} <command>`.
- Environment name derived deterministically: `project_name.lower().replace(" ", "_").replace("-", "_")`.
- File path separators must use `pathlib.Path` — never string concatenation.

---

## 5. Pipeline Overview

SVP proceeds through six stages (0-5) plus one transitional phase (Pre-Stage-3), for a total of seven sequential phases. Each phase must complete before the next begins. If a document-level problem is discovered at any phase, the pipeline restarts from the appropriate earlier stage.

```
Stage 0: Setup
Stage 1: Stakeholder Spec Authoring
Stage 2: Blueprint Generation and Alignment
Pre-Stage-3: Infrastructure Setup
Stage 3: Unit-by-Unit Verification
Stage 4: Integration Testing
Stage 5: Repository Delivery
```

After Stage 5 completion, the pipeline supports re-entry via `/svp:bug` for post-delivery bug investigation (see Section 12.17).

### 5.1 What to Expect: Best Case and Worst Case

**Best case (everything works).** The human describes their requirements clearly. The Socratic dialog produces a complete spec on the first draft. The blueprint decomposes the problem cleanly. Each unit's tests pass the red run, the implementation passes the green run, and coverage is complete — no human intervention needed. Integration tests pass. The repository is delivered. Total human decisions: roughly 5-10 approvals.

**Worst case (everything fails).** Multiple spec revisions. Blueprint fails alignment three times, hitting the iteration limit. Unit tests are wrong. Implementation fix ladders and diagnostic escalation fail, forcing document revision and restart. Multiple full restarts. The pipeline eventually converges and delivers a correct repository, but only after several passes. Total human decisions: potentially dozens.

The pipeline is designed so that the worst case still terminates correctly — every escalation path has a bounded endpoint, and every restart produces a cleaner foundation. The cost of the worst case is time and compute, not correctness.

---

## 6. Stage 0: Setup (CHANGED IN 2.0, CHANGED IN 2.1)

Stage 0 is split between the SVP launcher (deterministic, runs before Claude Code) and the setup agent (runs within Claude Code).

Full Stage 0 sub-stage progression:

```
hook_activation → [Gate 0.1] → project_context → [Gate 0.2] → project_profile → [Gate 0.3] → Stage 1
```

### 6.1 Launcher Pre-Flight (CHANGED IN 2.1)

The SVP launcher runs before Claude Code launches and performs all prerequisite checking and environment setup. The launcher is a standalone Python script at `svp/scripts/svp_launcher.py`, registered as a CLI entry point via `pyproject.toml`.

**6.1.1 CLI Subcommand Vocabulary (NEW IN 2.1 — Bug 32 fix)**

The launcher CLI supports exactly three invocation modes:

- `svp new <project_name>` — create a new project. Runs the full pre-flight, directory creation, and session launch sequence.
- Bare `svp` with no arguments — auto-detect an existing project in the current directory via `pipeline_state.json` presence and resume it. If no project is detected, the launcher prints an error directing the user to `svp new <project_name>`.
- `svp restore <project_name> --spec <path> --blueprint-dir <path> --context <path> --scripts-source <path> --profile <path>` — restore a project from backed-up documents. Creates a new project directory, copies in the deterministic scripts from `--scripts-source`, places the spec, blueprint files, and project context in their expected locations (`specs/stakeholder_spec.md`, `blueprint/blueprint_prose.md`, `blueprint/blueprint_contracts.md`, `project_context.md`). The `--blueprint-dir` argument points to a directory containing both `blueprint_prose.md` and `blueprint_contracts.md`; the launcher validates that both files exist before proceeding. Initializes the pipeline state to begin from Pre-Stage-3 (Stages 0-2 are considered complete), and launches Claude Code. This mode enables: (a) resuming from a previous SVP project's documents without re-running the Socratic dialogs, and (b) running the bundled Game of Life example as an installation verification test. The `--scripts-source` argument points to the plugin's `scripts/` directory. **Profile handling:** `svp restore` requires `--profile <path>` as a required argument pointing to a valid `project_profile.json` file from the backed-up project. The launcher validates that the file exists and is valid JSON before proceeding. A valid `project_profile.json` must be present before Pre-Stage-3 begins, because infrastructure setup reads the profile to derive the conda environment name and install quality packages. The restore sequence performs the same pre-flight checks as `svp new` (Section 6.1.2), except that checks dependent on an existing project directory (e.g., directory already exists) are skipped. The restore sequence copies scripts, places documents, places the profile at `project_profile.json`, copies `toolchain.json` and `ruff.toml` (set read-only), copies regression tests, writes initial pipeline state (stage: `"pre_stage_3"`, sub_stage: `None`), and launches Claude Code.

No other subcommands exist. The blueprint must not introduce additional subcommands (e.g., `svp resume`, `svp status`) beyond these three modes. This vocabulary is a spec-level constraint — the blueprint author may decompose the internal handler structure freely, but the user-facing CLI surface is fixed.

The launcher's `parse_args` function must implement all arguments listed above. Bare `svp` (no subcommand) must default to resume mode internally — `args.command` must never be `None` after `parse_args` returns (Bug 48 fix).

**6.1.2 Pre-Flight Check Sequence**

The launcher performs the following checks in order. Each check produces a pass/fail result. On any failure, the launcher prints a specific diagnostic message with remediation guidance and exits with a nonzero exit code. The launcher does not continue to subsequent checks after a failure.

1. **Claude Code installed.** Verify the `claude` CLI is on PATH and executable. Failure message: "Claude Code is not installed or not on PATH. Install from https://docs.claude.com."
2. **SVP plugin loaded.** Call `_find_plugin_root()` (see Section 1.4 for discovery order) to locate a valid SVP plugin directory. Failure message: "SVP plugin not found. Run: claude plugin install svp@svp."
3. **API credentials valid.** Verify that an Anthropic API key is configured and reachable. Failure message: "API credentials not configured or invalid. See Claude Code documentation for API key setup."
4. **Conda installed.** Verify `conda` is on PATH and executable. Failure message: "Conda is not installed or not on PATH. Install from https://docs.conda.io/en/latest/miniconda.html."
5. **Python version compatible.** Verify Python >= 3.11 is available. Failure message: "Python 3.11+ is required. Found: {version}."
6. **pytest available.** Verify pytest is importable in the base environment (verifies the human's development environment can run SVP's own regression tests during project creation). Failure message: "pytest is not installed. Run: pip install pytest."
7. **Git installed.** Verify `git` is on PATH. Failure message: "Git is not installed. Install from https://git-scm.com/."
8. **Network access.** Verify basic network connectivity (required for API calls). Failure message: "Network access check failed. SVP requires network access for API calls."

**6.1.3 New Project Creation Sequence (`svp new`)**

After pre-flight checks pass, the launcher performs the following steps in order for a new project:

1. Creates the project directory structure (see Section 6.6).
2. Copies deterministic scripts from the SVP plugin into the project workspace's `scripts/` directory.
3. Copies `toolchain_defaults/python_conda_pytest.json` to `toolchain.json` at the project root.
4. Copies `toolchain_defaults/ruff.toml` to the project root. The copied `ruff.toml` is set to read-only (`chmod a-w`) immediately after copying. It is permanently read-only — no agent, session, or command may modify it (see Section 19.2). **(NEW IN 2.1)**
5. Copies regression tests from `tests/regressions/` in the plugin to `tests/regressions/` in the workspace. The complete carry-forward regression test inventory is listed in Section 6.8.
6. Copies hook configuration files, rewriting script paths to `.claude/scripts/`.
7. Writes the initial `pipeline_state.json` with `stage: 0, sub_stage: hook_activation`.
8. Writes the SVP configuration file (`svp_config.json`) with defaults (see Section 22.1).
9. Generates the project's CLAUDE.md.
10. Sets filesystem permissions (see Section 19).
11. Launches Claude Code via `subprocess.run` (see Section 6.1.5).

**6.1.4 Resume Sequence (bare `svp`)**

After pre-flight checks pass, the launcher performs the following steps for an existing project:

1. Reads `pipeline_state.json` to verify it is valid JSON and contains the expected schema. If missing or corrupt, attempts state recovery from completion markers (see Section 6.7). If recovery fails, prints an error and exits.
2. Restores write permissions on the workspace (reversing the read-only lock set at session end; see Section 19.1).
3. Launches Claude Code via `subprocess.run` (see Section 6.1.5).

**6.1.5 Session Launch Mechanism**

The launcher launches Claude Code using `subprocess.run` with the following configuration:

- **Working directory:** `cwd=str(project_root)`. Claude Code uses the working directory as the project root. No `--project-dir` flag exists in the Claude Code CLI; the launcher must not pass it (Bug 31 fix — see Section 24.26).
- **Permissions flag:** `--dangerously-skip-permissions` is passed if `skip_permissions` is true in `svp_config.json` (default: true). The hook-based write authorization system (Section 19) remains active regardless of this setting.
- **Initial prompt:** `"run the routing script"` — passed via the `--prompt` flag so the new session immediately enters the action cycle.
- **Environment variable:** `SVP_PLUGIN_ACTIVE=1` is set in the subprocess environment only, via the `env` parameter of `subprocess.run`. The launcher must never set this variable in its own process environment. Agents and hooks check this variable to distinguish SVP sessions from non-SVP sessions (see Section 19.3).
- **No shell wrapping:** The command is passed as a list, not a string. No `shell=True`.

After `subprocess.run` returns, the launcher checks for a restart signal file (`.svp/restart_signal`). If present, the launcher deletes it, sets filesystem permissions, and relaunches Claude Code. This loop continues until no restart signal is found, at which point the launcher exits.

**6.1.6 Error Handling Summary**

| Failure | Behavior |
|---------|----------|
| Pre-flight check fails | Print specific diagnostic with remediation, exit nonzero |
| `pipeline_state.json` missing on resume | Attempt marker-based recovery; if fails, print error, exit nonzero |
| `pipeline_state.json` corrupt on resume | Attempt marker-based recovery; if fails, print error, exit nonzero |
| Project directory already exists on `svp new` | Print error directing user to resume with bare `svp`, exit nonzero |
| Plugin root not found | Print error with installation instructions, exit nonzero |
| `subprocess.run` returns nonzero (Claude Code crash) | Print error suggesting `svp` to resume, exit with Claude Code's exit code |
| Restore mode: missing `--spec`, `--blueprint-dir`, `--context`, `--scripts-source`, or `--profile` | Print usage error listing required arguments, exit nonzero |
| Restore mode: specified file does not exist | Print error identifying the missing file, exit nonzero |

**Dual-file synchronization contract.** Six units maintain both a canonical implementation under `src/unit_N/stub.py` and a runtime copy under `scripts/`: Unit 1 (`svp_config.py`), Unit 2 (`pipeline_state.py`), Unit 4 (`ledger_manager.py`), Unit 5 (`blueprint_extractor.py`), Unit 8 (`hint_prompt_assembler.py`), and Unit 9 (`prepare_task.py`). The `src/unit_N/stub.py` copy is always canonical — it is the version under test and the source of truth. The `scripts/` copy must match. The routing script performs a startup check comparing `KNOWN_AGENT_TYPES` between `src/unit_9/stub.py` and `scripts/prepare_task.py` and emits a warning to stderr if they differ.

### 6.2 Hook Activation

**Sub-stage:** `stage: "0", sub_stage: "hook_activation"`.

The routing script outputs a `human_gate` action that instructs the main session to guide the human through reviewing and activating hooks via Claude Code's `/hooks` menu. The gate response options are **HOOKS ACTIVATED** and **HOOKS FAILED**. The POST command advances state to `sub_stage: project_context`.

### 6.3 Setup Agent: Project Context

**Sub-stage:** `stage: "0", sub_stage: "project_context"`.

The setup agent asks the human for a brief domain description (1-3 sentences) and conducts a structured conversation to refine it into a well-written `project_context.md` with sections: Domain, Problem Statement, Key Terminology, Data Characteristics, Intended Users, and Success Criteria.

The setup agent's role is active rewriting — transforming whatever the human says into well-structured, LLM-optimized context that downstream agents can work with effectively.

**Quality gate.** The setup agent evaluates whether each section contains substantive content. If any section is hollow or tautological, the agent pushes back with specific questions. If after multiple attempts the human cannot provide sufficient content, the setup agent refuses to advance.

The agent presents the draft `project_context.md` to the human for approval. Gate response options: **CONTEXT APPROVED**, **CONTEXT REJECTED**, **CONTEXT NOT READY**. On approval, pipeline advances to `project_profile` sub-stage (not directly to Stage 1). On **CONTEXT REJECTED**, the pipeline deletes the current `project_context.md`, clears `last_status.txt`, and re-invokes the setup agent for the project context phase from scratch -- the human can start over with a fresh context dialog. On **CONTEXT NOT READY**, the pipeline holds at Gate 0.2 and re-invokes the setup agent for the project context phase -- the human can continue working with the setup agent to provide more context. For both **CONTEXT REJECTED** and **CONTEXT NOT READY**, `last_status.txt` is cleared so the two-branch routing invariant (Section 3.6) routes back to the setup agent invocation rather than re-presenting the gate.

**Two-branch routing requirement (NEW IN 2.1 — Bug 21 fix).** The `project_context` sub-stage has two reachable states: (1) the setup agent has not yet been invoked or has not yet completed, and (2) the setup agent has completed (indicated by `PROJECT_CONTEXT_COMPLETE` in `last_status.txt`). The routing script must distinguish these two states. In state (1), it emits an `invoke_agent` action for the setup agent. In state (2), it emits a `human_gate` action for Gate 0.2 (`gate_0_2_context_approval`). If `route()` always returns the agent invocation without checking `last_status.txt`, the pipeline loops indefinitely re-invoking the setup agent after the context is already written. This is a generalization of the routing action block pattern (see `test_bug14_routing_action_block_commands.py`): the routing function must handle all reachable states within a sub-stage, not just the initial entry. The same two-branch pattern applies to the `project_profile` sub-stage and Gate 0.3 (see Section 6.4). A regression test must verify that `route()` returns a gate action (not an agent invocation) when `last_status.txt` contains the agent's terminal status for both sub-stages.

### 6.4 Setup Agent: Project Profile (CHANGED IN 2.0, CHANGED IN 2.1)

After project context approval, the setup agent conducts a second Socratic dialog to capture delivery preferences. Output: `project_profile.json`.

**Sub-stage:** `stage: "0", sub_stage: "project_profile"`.

**Two-branch routing requirement (NEW IN 2.1 — Bug 21 fix).** The same two-branch routing pattern described in Section 6.3 applies here. When `last_status.txt` contains `PROFILE_COMPLETE`, `route()` must emit a `human_gate` action for Gate 0.3 (`gate_0_3_profile_approval`), not re-invoke the setup agent.

**Interaction pattern:** Ledger-based multi-turn on the same ledger (`ledgers/setup_dialog.jsonl`), continuing from the project context conversation.

**Experience-aware dialog (CHANGED IN 2.1).** The setup agent is mindful that the human is a domain expert, not a software engineer. The following four rules govern every question the setup agent asks across all five dialog areas. These are not guidelines — they are behavioral requirements for the setup agent's system prompt.

**Rule 1: Plain-language explanations required.** For every choice presented, the setup agent must explain what each alternative means in non-technical language that a domain expert can understand. No jargon without explanation. If a term is technical (e.g., "linter," "type checker," "semantic versioning," "docstring convention"), the agent must define it in one sentence before presenting it as an option. Example — wrong: "Docstring convention: Google, NumPy, or Sphinx?" Example — correct: "Docstrings are the help text inside your code that explain what each function does. There are different formatting styles — I recommend Google style, which is the most widely used and the easiest to read. Would you like to use that, or would you like to hear about the alternatives?"

**Rule 2: Best-option recommendation required.** For every choice, the setup agent must recommend the best option with a brief rationale. The recommendation must be clearly marked (e.g., "Recommended: ...") so the user can simply accept it without evaluating alternatives. The recommendation should be the most common, most broadly compatible, and most well-supported choice. Example — wrong: "Would you like ruff, flake8, or pylint for linting?" Example — correct: "For checking your code for common problems, I recommend ruff — it's the fastest and most modern tool, and it's what the pipeline already uses internally. Should I go with that?"

**Rule 3: Sensible defaults that always produce a correct project.** If the user has no preference and accepts every recommendation, the result must be a correct, well-configured project with no gaps or inconsistencies. The defaults are not placeholders — they are the setup agent's best judgment for a general-purpose project by a domain expert.

**Rule 4: Progressive disclosure.** Lead with the recommendation and a one-sentence explanation. Only provide detailed comparisons between alternatives if the user asks for more information or explicitly declines the recommendation. Do not front-load the user with a multi-option menu and expect them to evaluate unfamiliar alternatives. The fast path through any area is: agent recommends, human accepts.

**Testability requirement.** The setup agent's agent definition (AGENT.md) must contain Rules 1-4 verbatim as numbered behavioral requirements in its system prompt. The blueprint checker validates that the setup agent's AGENT.md includes all four rules. This makes rule presence structurally testable — an AST or text-based test can verify that the agent definition contains the required rule text.

**Area-level fast path.** Every area offers an area-level fast path in addition to per-question recommendations: "I can use sensible defaults for version control. Would you like to accept them, or would you prefer to go through the options?" A human who accepts all area-level defaults faces roughly five decisions (one per area). A human with detailed requirements can dive into any area. The per-question recommendations (Rules 1-2) apply only when the human enters an area — they do not apply when the human accepts the area-level default.

**Mode A awareness.** When the build type is Mode A (self-build), the setup agent pre-populates the profile with Mode A defaults: the 12-section README structure, conventional commits, Apache 2.0 license, `entry_points: true`, `source_layout: "conventional"`, `depth: "comprehensive"`, `audience: "developer"`. For Area 5, Mode A defaults are `quality.linter: "ruff"`, `quality.formatter: "ruff"`, `quality.type_checker: "mypy"`, `quality.import_sorter: "ruff"`, `quality.line_length: 88` — matching the pipeline tools, because SVP contributors should use the same quality tools the pipeline uses **(NEW IN 2.1)**. The human reviews and approves rather than answering from scratch. It only asks questions that are genuinely open even for a self-build — license holder name, author name, author contact.

**Dialog areas.** The setup agent covers five areas. Each area corresponds to a set of forking points from the comprehensive enumeration (see Part III, Section 31).

**Area 1: Version Control Preferences.**
- Commit message style: Conventional Commits (default), free-form, or custom template. When "custom" is chosen, the human provides a `commit_template`.
- Whether commit messages should reference issue numbers.
- Branch strategy: main-only (default) or other.
- Tagging convention: semantic versioning (default), calendar versioning, or none.
- Team-specific conventions (free-text).
- Changelog format: Keep a Changelog, Conventional Changelog, or none (default) **(NEW IN 2.1)**.

**Area 2: README and Documentation Preferences.**
- Target audience: domain expert (default), developer, both, or custom description.
- Section list: the agent presents the default list (Header, What it does, Who it's for, Installation, Configuration, Usage, Quick Tutorial, Examples, Project Structure, License) and asks for additions, removals, or reordering.
- Documentation depth: minimal, standard (default), or comprehensive.
- Optional content: mathematical notation, glossary, data format descriptions, code examples. When `include_code_examples` is true, a follow-up asks what the examples should demonstrate.
- Custom sections with human-provided descriptions.
- Docstring convention: Google style (default, recommended), NumPy style, or no preference. The agent must explain what docstrings are ("the help text inside your code that explains what each function does") and recommend Google style ("the most widely used and easiest to read") rather than presenting bare format names.
- Citation file (`CITATION.cff`) for academic projects.
- Contributing guide.

**Cross-area dependency:** If `testing.readme_test_scenarios` is set to true in Area 3, the setup agent automatically adds a Testing section to `readme.sections` if one is not already present.

**Area 3: Test and Quality Preferences.**
- Coverage target: the agent explains code coverage and asks for a threshold (valid range: 0-100, or null for no explicit target). Default: no explicit target.
- Readable test names: yes (default) or no.
- Test scenarios mentioned in README: yes or no.

**Area 4: Licensing, Metadata, and Packaging.**
- License type: Apache 2.0 (default, recommended), MIT, GPL v3, BSD 2-Clause, BSD 3-Clause, or other. The agent must explain what a software license is ("it tells people what they're allowed to do with your code") and recommend Apache 2.0 with rationale ("it's a well-established permissive license that includes an explicit patent grant — anyone can use your code, and it provides clearer legal protection than simpler licenses"). One-sentence explanation of each alternative only if the human asks.
- SPDX license headers: conditional follow-up when warranted (e.g., Apache 2.0 default includes headers). Default: true for Apache 2.0, false for MIT/BSD.
- Copyright holder and year.
- Author name (may differ from copyright holder for academic projects).
- Author contact.
- Additional metadata (citation, funding, acknowledgments) — asked conditionally.
- Entry points: "Does your project have a command-line tool?" Populates `delivery.entry_points`.

**Area 5: Delivered Code Quality Preferences. (NEW IN 2.1)**

The agent introduces this area with a plain-language framing: "Your project's code will be automatically formatted and checked for common problems during the build — that's a pipeline guarantee. For the delivered project, I can also include configuration so you or your contributors can run these same checks locally. I recommend including the same tools the pipeline uses. Should I set that up with the standard configuration, or would you like to go through the options?"

If the human enters the detailed options, each tool category must be explained before choices are presented (per Rule 1). For example, "A linter is a tool that checks your code for common mistakes and style problems — think of it like a spell-checker for code. I recommend ruff, which is fast and catches the most issues."

- Linter for delivered project: ruff (default, recommended), flake8, pylint, or none.
- Formatter for delivered project: ruff (default, recommended), black, or none.
- Type checker for delivered project: mypy, pyright, or none (default, recommended — "type checking catches a specific kind of bug but requires extra annotations in the code; if you don't plan to maintain the code yourself, you can skip this").
- Import sorter for delivered project: ruff (default, recommended), isort, or none.
- Line length: integer (default: 88, recommended — "this is the most common standard; it controls how wide lines of code are allowed to be").

**Note on defaults:** The pipeline always uses ruff + mypy internally (the quality gate guarantee). The delivery defaults match the pipeline for formatter and linter (ruff) but default type checker to "none" because the end user may not want to maintain type annotations. The setup agent explains this distinction.

**What the setup agent does NOT ask in SVP 2.1.** The following are pipeline-fixed (Tier A) and are not presented as choices:

- Programming language (Python only).
- Environment manager for the pipeline (Conda only).
- Test framework (pytest only).
- Package format for the pipeline build (setuptools only).
- Source layout during build (`src/unit_N/` — SVP-native).
- VCS system (Git only).
- Quality tools for the pipeline (ruff + mypy — fixed) **(NEW IN 2.1)**.

If the human asks about these, the agent explains they are fixed for the pipeline but the delivery can differ.

**What the setup agent DOES ask that affects delivery packaging.**

- Delivered environment recommendation: conda (default), pyenv, venv, Poetry, or "no environment instructions in README."
- Dependency specification in delivered repo: `environment.yml` (default if conda), `requirements.txt`, `pyproject.toml` dependencies, or multiple formats.
- Delivered source layout: conventional `src/packagename/` (default), flat, or SVP-native.

**Unsupported preferences.** If the human volunteers a preference that SVP 2.1 does not support, the setup agent acknowledges the request, explains the limitation honestly, and tells the human it will not be tracked — they will need to handle it manually after delivery. Nothing is recorded in the profile.

**Output: `project_profile.json`.** Strongly-typed, flat JSON. Schema:

```
project_profile.json
├── pipeline_toolchain: "python_conda_pytest"  (fixed, informational)
├── python_version: string
├── delivery:
│   ├── environment_recommendation: "conda" | "pyenv" | "venv" | "poetry" | "none"
│   ├── dependency_format: "environment.yml" | "requirements.txt" | "pyproject.toml" | list
│   ├── source_layout: "conventional" | "flat" | "svp_native"
│   └── entry_points: boolean
├── vcs:
│   ├── commit_style: "conventional" | "freeform" | "custom"
│   ├── commit_template: string | null
│   ├── issue_references: boolean
│   ├── branch_strategy: "main-only" | string
│   ├── tagging: "semver" | "calver" | "none"
│   ├── conventions_notes: string | null
│   └── changelog: "keep_a_changelog" | "conventional_changelog" | "none"  (NEW IN 2.1)
├── readme:
│   ├── audience: string
│   ├── sections: list of strings
│   ├── depth: "minimal" | "standard" | "comprehensive"
│   ├── include_math_notation: boolean
│   ├── include_glossary: boolean
│   ├── include_data_formats: boolean
│   ├── include_code_examples: boolean
│   ├── code_example_focus: string | null
│   ├── custom_sections: list of {name, description} | null
│   ├── docstring_convention: "google" | "numpy" | "none"
│   ├── citation_file: boolean
│   └── contributing_guide: boolean
├── testing:
│   ├── coverage_target: integer (0-100) | null
│   ├── readable_test_names: boolean
│   └── readme_test_scenarios: boolean
├── license:
│   ├── type: "Apache-2.0" | "MIT" | "GPL-3.0" | "BSD-2-Clause" | "BSD-3-Clause" | string
│   ├── holder: string
│   ├── author: string
│   ├── year: string
│   ├── contact: string | null
│   ├── spdx_headers: boolean
│   └── additional_metadata:
│       ├── citation: string | null
│       ├── funding: string | null
│       ├── acknowledgments: string | null
│       └── (additional free-form keys preserved)
├── quality:                                          (NEW IN 2.1)
│   │   (Delivery configuration only. All fields in the quality section
│   │    configure the delivered project's quality tools, not the pipeline's.
│   │    The pipeline always uses ruff + mypy via toolchain.json regardless
│   │    of these settings. See Section 12.13.)
│   ├── linter: "ruff" | "flake8" | "pylint" | "none"
│   ├── formatter: "ruff" | "black" | "none"
│   ├── type_checker: "mypy" | "pyright" | "none"
│   ├── import_sorter: "ruff" | "isort" | "none"
│   └── line_length: integer
├── fixed:
│   ├── language: "python"
│   ├── pipeline_environment: "conda"
│   ├── test_framework: "pytest"
│   ├── build_backend: "setuptools"
│   ├── vcs_system: "git"
│   ├── source_layout_during_build: "svp_native"
│   └── pipeline_quality_tools: "ruff_mypy"           (NEW IN 2.1)
└── created_at: ISO timestamp
```

The `fixed` section records Tier A values for transparency. No agent reads `fixed` at runtime — the pipeline reads `toolchain.json`.

**Schema constraint:** Every field has a defined default. The setup agent always writes a fully populated `project_profile.json` with every field explicitly present. No downstream consumer needs a defaults table.

**Canonical naming invariant (NEW IN 2.1).** The schema above defines the exact canonical section names and field names for `project_profile.json`. These names are authoritative. Every component that produces or consumes profile data must use exactly these names:

- Top-level sections are: `pipeline_toolchain`, `python_version`, `delivery` (not `packaging`), `vcs`, `readme`, `testing`, `license` (not `licensing`), `quality`, `fixed`, `created_at`.
- Within `readme`: the audience field is `audience` (not `target_audience`).
- Within `delivery`: the environment field is `environment_recommendation` (not `environment`).
- Within `license`: metadata is under `additional_metadata` (not `metadata`).

This invariant applies to three components that must agree on names:

1. **`DEFAULT_PROFILE` in the config reader** (`svp_config.py` / Unit 1): the hardcoded default profile used as the merge base in `load_profile()`. Its section names and field names must exactly match this schema.
2. **The setup agent's output**: the `project_profile.json` file written during Stage 0. The setup agent's system prompt must reference this schema. The agent must use these exact names when constructing the JSON output.
3. **Every downstream consumer** (preparation scripts, blueprint checker, git repo agent, compliance scan, redo agent): field access must use these exact names.

If any component uses a different name (e.g., `licensing` instead of `license`, `readme.target_audience` instead of `readme.audience`), the `_deep_merge` in `load_profile()` will not override the default — both the default value and the misnamed value will coexist in the merged result, producing silent conflicts. This is not a validation-catchable error; the merge succeeds but the semantics are wrong.

**Enforcement mechanism.** The canonical field names must be defined as constants in a single shared location (Unit 1's schema definition). The setup agent's system prompt must include the complete schema with exact field names. A regression test must verify that every key in `DEFAULT_PROFILE` appears in the schema definition, and that the setup agent's output (for a representative dialog) uses only keys present in `DEFAULT_PROFILE`. No component may invent profile field names independently.

**Contradiction detection.** The setup agent checks for known contradictory combinations during the dialog and asks the human to resolve them before writing the profile. Known contradictions include:

- `readme.depth: "minimal"` with more than 5 sections or any custom sections.
- `readme.include_code_examples: true` with `readme.depth: "minimal"`.
- `delivery.entry_points: true` with no identifiable CLI module in the stakeholder spec.
- `delivery.source_layout: "flat"` with more than approximately 10 units.
- `vcs.commit_style: "custom"` with `vcs.commit_template: null`.
- Mismatched delivery environment and dependency format.

The profile is not written until detected contradictions are resolved.

**Determinism constraint:** The setup agent records what the human said. It does not generate creative content for the profile.

**Immutability.** Once approved at Gate 0.3, `project_profile.json` is a blessed document. Changes require `/svp:redo` (see Section 13).

**Read-time validation.** Every script and agent that reads `project_profile.json` must validate the fields it uses against expected types. Unknown fields are ignored (forward compatibility). Missing fields are filled from defaults. Type mismatches produce a clear error message.

**Integrity requirement.** If `project_profile.json` is missing or fails JSON parsing when a script or agent attempts to read it, the reader raises a `RuntimeError` directing the human to resume from Stage 0 or re-run `/svp:redo`.

**Gate 0.3 (project profile approval).** The setup agent presents a formatted summary (not raw JSON). Gate response options: **PROFILE APPROVED**, **PROFILE REJECTED**. On rejection, the agent asks which areas need revision — the human may specify multiple areas. The agent handles all specified areas in one pass, then re-presents the full summary once. There is no iteration limit on Gate 0.3 rejections.

### 6.5 Toolchain Configuration File (CHANGED IN 2.0, CHANGED IN 2.1)

On project creation, the launcher copies `toolchain.json` to the project root from `toolchain_defaults/python_conda_pytest.json`. This is the pipeline's own toolchain — the commands SVP uses to build and test. It is never modified.

The `{env_name}` placeholder in all templates is resolved via `derive_env_name()` (Section 4.3). The file maps abstract operation names to concrete command templates:

```
toolchain.json
├── toolchain_id: "python_conda_pytest"
├── environment:
│   ├── tool: "conda"
│   ├── create: "conda create -n {env_name} python={python_version} -y"
│   ├── run_prefix: "conda run -n {env_name}"
│   ├── install: "conda run -n {env_name} pip install {packages}"
│   ├── install_dev: "conda run -n {env_name} pip install -e ."
│   └── remove: "conda env remove -n {env_name} --yes"
├── testing:
│   ├── tool: "pytest"
│   ├── run: "{run_prefix} pytest {test_path} -v"
│   ├── run_coverage: "{run_prefix} pytest --cov={module} {test_path}"
│   ├── framework_packages: ["pytest", "pytest-cov"]
│   ├── file_pattern: "test_*.py"
│   ├── collection_error_indicators: ["ERROR collecting", "ImportError", "ModuleNotFoundError", "SyntaxError", "no tests ran"]
│   │   Note: "no tests ran" applies only when test files exist but pytest reports
│   │   no tests collected. An empty test directory (no test files present) is a
│   │   different condition and should not be classified as a collection error.
│   └── pass_fail_pattern: "Parses pytest summary line."
├── packaging:
│   ├── tool: "setuptools"
│   ├── manifest_file: "pyproject.toml"
│   ├── build_backend: "setuptools.build_meta"
│   └── validate_command: "{run_prefix} pip install -e ."
├── vcs:
│   ├── tool: "git"
│   └── commands:
│       ├── init: "git init"
│       ├── add: "git add {files}"
│       ├── commit: "git commit -m \"{message}\""
│       └── status: "git status"
├── language:
│   ├── name: "python"
│   ├── extension: ".py"
│   ├── version_constraint: ">=3.10"
│   ├── signature_parser: "python_ast"
│   └── stub_body: "raise NotImplementedError()"
├── file_structure:
│   ├── source_dir_pattern: "src/unit_{n}/"
│   ├── test_dir_pattern: "tests/unit_{n}/"
│   ├── source_extension: ".py"
│   └── test_extension: ".py"
└── quality:                                          (NEW IN 2.1)
    ├── formatter:
    │   ├── tool: "ruff"
    │   ├── format: "{run_prefix} ruff format {target}"
    │   └── check: "{run_prefix} ruff format --check {target}"
    ├── linter:
    │   ├── tool: "ruff"
    │   ├── light: "{run_prefix} ruff check --select E,F,I --fix {target}"
    │   ├── heavy: "{run_prefix} ruff check --fix {target}"
    │   └── check: "{run_prefix} ruff check {target}"
    ├── type_checker:
    │   ├── tool: "mypy"
    │   ├── check: "{run_prefix} mypy {flags} {target}"
    │   ├── unit_flags: "--ignore-missing-imports"
    │   └── project_flags: ""
    ├── packages: ["ruff", "mypy"]
    ├── gate_a: ["formatter.format", "linter.light"]
    ├── gate_b: ["formatter.format", "linter.heavy", "type_checker.check"]
    └── gate_c: ["formatter.check", "linter.check", "type_checker.check"]
```

**Placeholder resolution.** Single-pass: resolve `environment.run_prefix` first, then substitute into all templates referencing `{run_prefix}`. `{python_version}` resolved from profile. `{env_name}` resolved from `derive_env_name()`. `{flags}` in `type_checker.check` resolved from `type_checker.unit_flags` (Gates A/B) or `type_checker.project_flags` (Gate C) — the quality gate script receives the gate identifier (e.g., `"gate_a"`, `"gate_b"`, `"gate_c"`) as a parameter from the routing script's COMMAND, and selects the appropriate flags value accordingly. For Gate C, `{flags}` resolves to `type_checker.project_flags`, which is explicitly set to an empty string `""`. This means no flags are passed to mypy, and in particular `--ignore-missing-imports` is absent. The empty value is intentional: at Gate C the full project is assembled, so all imports must resolve without suppression. No recursive resolution. **Whitespace normalization:** after all placeholders are resolved, the resolution function must strip extra whitespace from the resulting command string (collapsing multiple consecutive spaces to a single space and trimming leading/trailing whitespace). This prevents double-space artifacts when a placeholder like `{flags}` resolves to an empty string.

**Toolchain portability (Bug 34 fix — NEW IN 2.1).** Command templates in `toolchain.json` must use only flags that are stable across supported versions of the underlying tool. Specifically, `environment.run_prefix` must not include version-specific flags (e.g., `--no-banner` was removed in conda 25.x). The canonical `run_prefix` for conda is `"conda run -n {env_name}"` with no additional flags.

**Python version validation.** The toolchain reader validates that `{python_version}` satisfies `language.version_constraint`. The launcher performs this validation during pre-flight checks (Section 6.1.3): it reads the profile's `python_version` field and validates it against the toolchain's `language.version_constraint` (e.g., `>=3.10`). If the profile specifies a Python version that does not satisfy the toolchain constraint, the launcher fails with a clear error message before environment creation begins.

**Behavioral equivalence.** Every resolved command in the existing sections (`environment`, `testing`, `packaging`, `vcs`, `language`, `file_structure`) must produce identical behavior to SVP 1.2's hardcoded commands. The `quality` section is purely additive — no equivalence requirement.

**Integrity requirement.** If `toolchain.json` is missing or fails JSON parsing, the reader raises a `RuntimeError` directing the human to re-run `svp new`. No fallback to hardcoded values.

**Human visibility.** The human never edits or sees `toolchain.json`. The pipeline toolchain is reflected in `project_profile.json`'s `fixed` section.

**Quality gate composition (NEW IN 2.1).** The `gate_a`, `gate_b`, and `gate_c` lists define which operations run at each quality gate. This makes gate composition data-driven. The routing script reads these lists and executes the referenced operations in order.

**6.5.1 Quality Gate Operation Resolution (Bug 33 fix — NEW IN 2.1).** Gate operation names in the `gate_a`, `gate_b`, and `gate_c` lists are relative paths within the `quality` section (e.g., `"formatter.check"` refers to `quality.formatter.check`). Before passing an operation to `resolve_command`, the caller must prepend `"quality."` to produce the fully qualified dotted path. The placeholder vocabulary for quality command templates is: `{run_prefix}`, `{target}`, `{env_name}`, `{flags}` (used only in `type_checker.check`; resolved from `type_checker.unit_flags` for Gates A/B or `type_checker.project_flags` for Gate C). The `{target}` placeholder receives the file or directory path to check. Callers must not use `{path}` — the canonical placeholder name is `{target}`. Structural tests must verify that every operation in every gate list, when qualified with `"quality."`, resolves to a valid string template in the toolchain.

### 6.6 Directory Structure (CHANGED IN 2.0, CHANGED IN 2.1)

```
parent/
|-- projectname/                  <- pipeline workspace
|   |-- .claude/
|   |   |-- hooks.json
|   |   |-- scripts/              <- hook shell scripts
|   |   +-- settings.json
|   |-- .svp/
|   |   |-- task_prompt.md
|   |   |-- gate_prompt.md
|   |   |-- last_status.txt
|   |   |-- restart_signal
|   |   +-- markers/
|   |-- CLAUDE.md
|   |-- pipeline_state.json
|   |-- svp_config.json
|   |-- project_context.md
|   |-- project_profile.json      <- delivery preferences (Stage 0)
|   |-- toolchain.json            <- pipeline toolchain commands
|   |-- ruff.toml                 <- quality tool config (NEW IN 2.1)
|   |-- logs/
|   |   +-- rollback/
|   |-- ledgers/
|   |-- specs/
|   |   |-- stakeholder_spec.md
|   |   +-- history/
|   |-- blueprint/
|   |   |-- blueprint_prose.md
|   |   |-- blueprint_contracts.md
|   |   +-- history/
|   |-- references/
|   |   |-- index/
|   |   |-- repos.json
|   |   +-- (original documents)
|   |-- scripts/
|   |-- src/
|   |-- tests/
|   |   +-- regressions/          <- carry-forward regression tests
|   +-- data/
+-- projectname-repo/             <- clean git repo (final deliverable)
```

The workspace is the build environment. The repo is the deliverable.

### 6.7 Resume Mode and Optional Integrations

**Resume mode.** When the launcher detects a valid project directory, it reads the pipeline state file and launches Claude Code directly. If the state file is missing or corrupt, recovery uses deterministic file-presence checking: completion markers on approved documents and unit marker files. No LLM inference. If reconstruction fails, start fresh.

**Optional integrations.** During bootstrap, the setup agent asks about GitHub MCP (read-only access to external repositories). Configuration flow: PAT creation guidance, `claude mcp add-json`, connection verification. The token is stored only in `~/.claude.json`, never in any SVP file.

### 6.8 Carry-Forward Regression Test Inventory (NEW IN 2.1)

The following table lists every bug in the unified catalog (Bugs 1-69) with its coverage mechanism. Dedicated regression test files are carried forward from the previous build -- copied from the SVP plugin's `tests/regressions/` directory into the project workspace during project creation. All dedicated regression test files must pass in both the workspace layout and the delivered repository layout.

This table is the single authoritative reference for the dual numbering scheme. The "Filename Bug #" column shows the number used in the test filename prefix (`test_bugNN_*`). The "Unified Bug #" column shows the canonical bug number in the unified catalog (Bugs 1-69). Where these differ, it is due to historical naming (see naming collision note below).

| Filename Bug # | Unified Bug # | Coverage | File / Location | What It Tests |
|----------------|---------------|----------|----------------|---------------|
| -- | 1-5 | Unit tests | Blueprint-era unit assertions | Blueprint-era fixes (no standalone files) |
| bug2 | 6 | Dedicated file | `test_bug2_wrapper_delegation.py` | Wrapper function delegation |
| bug3 | 7 | Dedicated file | `test_bug3_cli_argument_contracts.py` | CLI argument contracts |
| bug4 | 8 | Dedicated file | `test_bug4_status_line_contracts.py` | Status line contracts |
| bug5 | 9 | Dedicated file | `test_bug5_pytest_framework_deps.py` | Framework dependency completeness |
| bug6 | 10 | Dedicated file | `test_bug6_collection_error_classification.py` | Collection error classification |
| bug7 | 11 | Dedicated file | `test_bug7_unit_completion_status_file.py` | Unit completion status write ordering |
| bug8 | 12 | Dedicated file | `test_bug8_sub_stage_reset_on_completion.py` | Sub-stage reset on unit completion |
| bug9 | 13 | Dedicated file | `test_bug9_hook_path_resolution.py` | Hook path resolution |
| bug10 | 14 | Dedicated file | `test_bug10_agent_status_prefix_matching.py` | Agent status prefix matching |
| bug11 | 15 | Dedicated file | `test_bug11_delivered_repo_artifacts.py` | Delivered repo artifact completeness |
| bug12 | 16 | Dedicated file | `test_bug12_cmd_main_guards.py` | Command script main guards |
| bug13 | 17 | Dedicated file | `test_bug13_hook_schema_validation.py` | Hook configuration schema |
| bug14 | 18 | Dedicated file | `test_bug14_routing_action_block_commands.py` | Routing action block PREPARE/POST emission |
| bug15 | 19 | Dedicated file | `test_bug15_gate_prepare_flag_mismatch.py` | Gate prepare flag correctness |
| bug16 | 20 | Dedicated file | `test_bug16_same_file_copy_guard.py` | Same-file copy guard |
| bug17 | 21 | Dedicated file | `test_bug17_routing_gate_presentation.py` | Two-branch routing gate presentation |
| bug18 | 22 | Dedicated file | `test_bug18_stakeholder_spec_filename.py` | Stakeholder spec filename contract |
| bug19 | 23 | Dedicated file | `test_bug19_alignment_check_routing.py` | Alignment check routing |
| bug20 | 24 | Dedicated file | `test_bug20_total_units_derivation.py` | total_units derivation from blueprint |
| bug21 | 25 | Dedicated file | `test_bug21_stage3_sub_stage_routing.py` | Stage 3 core sub-stage routing |
| bug17 | 26 | Dedicated file | `test_bug17_stage5_repo_assembly_routing.py` | Stage 5 repo assembly routing |
| -- | 27 | Integration test | Stage 4 toolchain resolution chain | `derive_env_name()` consistency |
| -- | 28 | Structural validation | Section 12.3 commit structure check | Commit count and per-step files |
| -- | 29 | Existing regression tests | Covered by Bugs 15, 26, others | Assembly defect overlap |
| bug18 | 30 | Dedicated file | `test_bug18_readme_carry_forward.py` | README carry-forward preservation |
| bug19 | 31 | Dedicated file | `test_bug19_plugin_discovery_paths.py` | Plugin discovery paths and JSON validation |
| -- | 32 | Structural validation | Section 12.3 | CLI subcommand vocabulary |
| -- | 33 | Unit test | Unit 10: `run_quality_gate` | `"quality."` prefix + `{target}` placeholder |
| -- | 34 | Unit test | Unit 22: toolchain template | `run_prefix` has no version-specific flags |
| -- | 35 | Unit test | Unit 10: `route()` output | No unresolved placeholders in routing output |
| -- | 36 | Unit test | Unit 10: `route()` dispatch | `stub_generation` sub-stage + `None` equivalence |
| bug22 | 37 | Dedicated file | `test_bug22_repo_sibling_directory.py` | Delivered repo created as sibling directory |
| -- | 38 | Structural test | Unit 20: Group B `*_MD_CONTENT` | Complete action cycle in command definitions |
| -- | 39 | Structural test | Unit 21: `SKILL_MD_CONTENT` | Slash-command cycle guidance |
| -- | 40 | Structural test | Workspace/delivered parity | Artifact synchronization |
| bug23 | 41 | Dedicated file | `test_bug23_stage1_spec_gate_routing.py` | Stage 1 two-branch routing and gate ID consistency |
| bug42 | 42 | Dedicated file | `test_bug42_pre_stage3_state_persistence.py` | Pre-Stage-3 state persistence after alignment (note: check (1) enforces the route-level state persistence invariant globally across all `complete_*`/`advance_*` calls, not just the Bug 42 scenario) |
| bug43 | 43 | Dedicated file | `test_bug43_stage2_blueprint_routing.py` | Universal two-branch routing compliance and gate ID consistency (note: covers ALL entries in the Section 3.6 exhaustive list, not just Stage 2; also verifies cross-unit gate ID synchronization between `GATE_VOCABULARY` and `ALL_GATE_IDS`) |
| bug44 | 44 | Dedicated file | `test_bug44_null_substage_dispatch.py` | dispatch_agent_status null sub_stage handling for test_agent |
| bug45 | 45 | Dedicated file | `test_bug45_test_execution_dispatch.py` | dispatch_command_status test_execution state advancement |
| bug46 | 46 | Dedicated file | `test_bug46_coverage_dispatch.py` | dispatch_agent_status coverage_review state advancement |
| bug47 | 47 | Dedicated file | `test_bug47_unit_completion_double_dispatch.py` | unit_completion COMMAND/POST separation (no embedded state update) |
| bug48 | 48 | Dedicated file | `test_bug48_launcher_cli_contract.py` | Launcher CLI contract: bare svp default, --blueprint-dir, --profile |
| bug49 | 49 | Dedicated file | `test_bug49_argparse_enumeration.py` | CLI argument enumeration for Units 6, 7, 9, 10, 23 |
| bug50 | 50 | Dedicated file | `test_bug50_contract_sufficiency.py` | Contract sufficiency for Units 1, 3, 6, 10, 24 |
| bug51 | 51 | Dedicated file | `test_bug51_debug_reassembly.py` | Debug loop reassembly after repair completion |
| bug52 | 52 | Dedicated file | `test_bug52_version_document_wiring.py` | version_document wired at every REVISE/FIX gate |
| bug53 | 53 | Dedicated file | `test_bug53_orphaned_functions.py` | Orphaned functions without call sites |
| bug54 | 54 | Dedicated file | `test_bug54_orphaned_update_state_from_status.py` | Orphaned hollow function update_state_from_status |
| -- | 55 | Structural validation | Gate 6.2 FIX UNIT dispatch | rollback_to_unit and set_debug_classification wiring |
| -- | 56 | Structural validation | Blueprint checker | Downstream dependency and contract granularity rules |
| -- | 57 | Structural validation | Reviewer agent definitions | Baked dependency and contract checklists |
| bug58 | 58 | Dedicated file | `test_bug58_gate_5_3_unused_functions.py` | Gate 5.3 unused_functions in GATE_VOCABULARY and dispatch |
| bug59 | 59 | Dedicated file | `test_bug59_blueprint_path_and_gates.py` | Blueprint path resolution, gate registration, and implementation fixes |
| bug60 | 60 | Dedicated file | `test_bug60_unit_context_blueprint_path.py` | _get_unit_context blueprint directory resolution and ARTIFACT_FILENAMES key |
| bug61 | 61 | Dedicated file | `test_bug61_include_tier1_parameter.py` | include_tier1 parameter wiring in build_unit_context and _get_unit_context |
| bug62 | 62 | Dedicated file | `test_bug62_selective_blueprint_loading.py` | Selective blueprint loading per agent matrix (contracts-only, prose-only) |

**Naming note: collisions and deviations.** Two distinct issues exist in the filename-to-bug mapping, both due to historical naming:

*Prefix collisions* occur when the same `test_bugNN_` prefix is shared by two files covering different unified bugs: `test_bug17_*` (Bugs 21 and 26), `test_bug18_*` (Bugs 22 and 30), `test_bug19_*` (Bugs 23 and 31). Each pair is disambiguated by the suffix. Downstream agents must use the full filename, not just the prefix.

*Prefix deviations* occur when a file's `test_bugNN_` prefix does not match its unified bug number: `test_bug23_stage1_spec_gate_routing.py` covers Bug 41 (not Bug 23) because it was authored during the Bug 23 debug session when the Stage 1 routing gap was discovered as a related issue.

The mapping table above is authoritative for resolving both collisions and deviations.

| bug65 | 65 | Dedicated file | `test_bug65_stage3_error_handling.py` | Stage 3 error-handling: stub_generation, fix ladder, diagnostic escalation, Gate 3.1/3.2, coverage two-branch, red_run retries (24 tests) |
| bug67 | 67 | Dedicated file | `test_bug67_gate_5_3_routing.py` | gate_5_3 routing path, UNUSED_FUNCTIONS_DETECTED dispatch, STAGE_5_SUB_STAGES |

**Regression test count.** There are 45 distinct regression test file entries in the table above (40 unique filenames): 15 carry-forward from SVP 2.0, 7 carry-forward from SVP 2.1 prior builds, and 22 newly authored in this build. Three `test_bugNN_` filename prefixes are reused across different bugs (`test_bug17_*`, `test_bug18_*`, `test_bug19_*` -- see naming note above), but each table entry corresponds to a distinct file with a unique full filename. The 22 newly authored files are: `test_bug13_hook_schema_validation.py` (Bug 17), `test_bug22_repo_sibling_directory.py` (Bug 37), `test_bug23_stage1_spec_gate_routing.py` (Bug 41), `test_bug42_pre_stage3_state_persistence.py` (Bug 42), `test_bug43_stage2_blueprint_routing.py` (Bug 43), `test_bug44_null_substage_dispatch.py` (Bug 44), `test_bug45_test_execution_dispatch.py` (Bug 45), `test_bug46_coverage_dispatch.py` (Bug 46), `test_bug47_unit_completion_double_dispatch.py` (Bug 47), `test_bug48_launcher_cli_contract.py` (Bug 48), `test_bug49_argparse_enumeration.py` (Bug 49), `test_bug50_contract_sufficiency.py` (Bug 50), `test_bug51_debug_reassembly.py` (Bug 51), `test_bug52_version_document_wiring.py` (Bug 52), `test_bug53_orphaned_functions.py` (Bug 53), `test_bug54_orphaned_update_state_from_status.py` (Bug 54), `test_bug55_rollback_gate62_wiring.py` (Bug 55), `test_bug58_gate_5_3_unused_functions.py` (Bug 58), `test_bug59_blueprint_path_and_gates.py` (Bug 59), `test_bug60_unit_context_blueprint_path.py` (Bug 60), `test_bug61_include_tier1_parameter.py` (Bug 61), and `test_bug62_selective_blueprint_loading.py` (Bug 62). All other files are carried forward unchanged.

**New regression test naming convention.** Newly authored regression tests in this build use the unified catalog number: `test_bugNN_descriptive_suffix.py` where NN is the unified bug number. The `test_bug13_hook_schema_validation.py` file for unified Bug 17 uses a pre-unified filename prefix (`bug13`) because Bug 17 was catalogued before the unified numbering convention was established. Despite being newly authored in this build, its filename uses the old numbering for backward compatibility: the SVP 2.0 regression test inventory already allocated the `test_bug13` prefix slot, and existing tooling and documentation reference this filename. Changing it would break the established carry-forward contract. The filename is treated as a fixed historical artifact.

**Test filename note for Bug 43.** The test file `test_bug43_stage2_blueprint_routing.py` carries "stage2_blueprint" in its suffix because the bug was originally discovered in Stage 2's blueprint dialog routing. However, the test's scope is universal -- it verifies two-branch compliance for ALL entries in the Section 3.6 exhaustive list and cross-unit gate ID consistency. The suffix is a historical artifact of the discovery context, not a scope limitation.

---

## 7. Stage 1: Stakeholder Spec Authoring (CHANGED IN 2.1)

Full Stage 1 sub-stage progression **(NEW IN 2.1 — Bug 41 fix)**:

```
stakeholder_spec_authoring (sub_stage=None) → [SPEC_DRAFT_COMPLETE or SPEC_REVISION_COMPLETE] → Gate 1.1 (spec draft approval)
  Gate 1.1 APPROVE → finalize spec, advance to Stage 2
  Gate 1.1 REVISE → re-invoke stakeholder dialog agent (sub_stage=None, clear last_status.txt)
  Gate 1.1 FRESH REVIEW → invoke stakeholder spec reviewer → [REVIEW_COMPLETE] → Gate 1.2 (spec post-review)
    Gate 1.2 APPROVE → finalize spec, advance to Stage 2
    Gate 1.2 REVISE → re-invoke stakeholder dialog agent in revision mode
    Gate 1.2 FRESH REVIEW → re-invoke stakeholder spec reviewer
```

Stage 1 uses `sub_stage: None` throughout — the two-branch routing invariant (Section 3.6) uses `last_status.txt` to distinguish "dialog in progress" from "draft complete, present gate." The sub-stage flow above describes the routing logic, not literal sub-stage values. Gate 1.1 (`gate_1_1_spec_draft`) and Gate 1.2 (`gate_1_2_spec_post_review`) must be registered in both routing dispatch tables and gate preparation registries (see gate ID consistency invariant, Section 3.6).

### 7.1 Entry Point

The pipeline begins with a welcome message explaining what SVP is, the rules of engagement for both agent and human, the available commands (`/svp:save`, `/svp:quit`, `/svp:help`, `/svp:hint`, `/svp:status`, `/svp:ref`), and the ability to provide reference documents.

### 7.2 Reference Documents

At any point during the stakeholder dialog, the human can provide reference documents: methods papers, lab protocols, grant proposals, technical specs, algorithm descriptions, or colleague code repositories (via GitHub MCP). Supported formats: PDF, markdown, plain text, and URLs.

When a reference document is added:

1. The document is copied to the `references/` directory.
2. A subagent reads it and produces a structured summary (what it is, topics, key terms, relevant sections) saved to `references/index/`.
3. The summary is available as context to subsequent agents. The full document is accessible on demand.

For GitHub repositories, the same pattern applies via GitHub MCP: a subagent explores the repo structure, key modules, and APIs, and produces a summary.

Reference documents supplement the Socratic dialog — they do not replace it. The stakeholder spec remains the single source of truth for intent.

### 7.3 Socratic Dialog

The stakeholder dialog agent conducts a structured conversation via conversation ledger (`ledgers/stakeholder_dialog.jsonl`). Each turn is a fresh agent invocation with the full ledger as context.

Its behavior:

- As one of its first questions, asks about reference documents.
- Asks one question at a time. Waits for an answer before proceeding.
- When consensus on a topic is reached, explicitly confirms and moves on.
- Actively surfaces contradictions, edge cases, and unstated assumptions.
- Probes adversarial scenarios: malformed input, unavailable resources, unexpected data.
- Draws on reference summaries; retrieves full documents on demand. Always confirms interpretations with the human.
- Does not make technical architecture decisions — those belong in the blueprint.

### 7.4 Draft-Review-Approve Cycle

**Two-branch routing requirement (NEW IN 2.1 — routing invariant, CHANGED IN 2.1 — Bug 41 fix).** Stage 1 is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`, `route()` must emit a `human_gate` action for Gate 1.1 (`gate_1_1_spec_draft`), not re-invoke the stakeholder dialog agent. If `route()` unconditionally re-invokes the agent without checking `last_status.txt`, the pipeline loops indefinitely after the spec draft is already written. A regression test (`test_bug23_stage1_spec_gate_routing.py`) must verify that `route()` returns a gate action (not an agent invocation) when `last_status.txt` contains the agent's terminal status for this sub-stage. The test must also verify that `gate_1_1_spec_draft` and `gate_1_2_spec_post_review` are registered in both `GATE_RESPONSES` (routing dispatch) and `ALL_GATE_IDS` (gate preparation registry) per the gate ID consistency invariant (Section 3.6).

**Reviewer status routing.** When `last_status.txt` contains `REVIEW_COMPLETE` (from the stakeholder spec reviewer agent, invoked via the FRESH REVIEW option), `route()` must distinguish this from the dialog agent's `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` and route to Gate 1.2 (`gate_1_2_spec_post_review`), not Gate 1.1. The same pattern applies in Stage 2: when the blueprint reviewer produces `REVIEW_COMPLETE`, routing must present Gate 2.2 (`gate_2_2_blueprint_post_review`), not Gate 2.1. In both stages, `route()` must check the specific status prefix to select the correct gate.

When all topics have been discussed:

1. The agent asks for permission to write the initial draft.
2. The agent produces the complete stakeholder spec document.
3. The human reads the document (this is a stated human duty, not optional).
4. The human chooses: **APPROVE**, **REVISE**, or **FRESH REVIEW**.
5. If **APPROVE**: the spec is finalized with a completion marker (`<!-- SVP_APPROVED: timestamp -->`) and the pipeline advances to Stage 2.
6. If **REVISE**: the human may invoke `/svp:help` to formulate a hint. The agent incorporates revisions and presents the revised draft. The cycle repeats.
7. If **FRESH REVIEW**: a distinct stakeholder spec reviewer agent receives only the document, project context, and reference summaries — no dialog ledger. It reads the document cold and produces a structured critique. The pipeline then presents Gate 1.2 (`gate_1_2_spec_post_review`). The human reads the critique and chooses: **APPROVE** (accept the spec as-is despite the critique), **REVISE** (take the critique to revision — the stakeholder dialog agent incorporates the critique), or **FRESH REVIEW** (request another cold review). Review cycles are unbounded.

**Scenarios — Gates 1.1/1.2.**
*Best case:* Thorough dialog, complete draft, human approves. One draft, one approval.
*Worst case:* Gaps and misinterpretations. Multiple reviews and revisions, with Help Agent sessions to formulate hints. In the most extreme case, a full spec restart.

### 7.5 Output

An approved `stakeholder_spec.md` file with completion marker. Pipeline state updated to record Stage 1 completion. Session boundary fires.

**Canonical filename (NEW IN 2.1 — Bug 22 fix, CHANGED IN 2.1).** The stakeholder spec filename is `stakeholder_spec.md`. This name must be defined as a shared constant referenced by both the setup agent's file placement logic and the preparation script's file loading logic. No component may hardcode an alternative name (e.g., `stakeholder.md`). This is a cross-unit contract: the setup agent (which writes the file) and the preparation script (which reads it) must agree on the exact filename through a single source of truth. The same principle applies to any pipeline artifact referenced by path across multiple components. The complete set of canonical filenames that must be defined as shared constants includes: `stakeholder_spec.md`, `blueprint_prose.md`, `blueprint_contracts.md`, `project_context.md`, `project_profile.json`, `toolchain.json`, `ruff.toml`, `pipeline_state.json`, `svp_config.json`, and `svp_2_1_lessons_learned.md` (the lessons learned document, at workspace-relative path `references/svp_2_1_lessons_learned.md`, referenced by the debug loop's Step 6).

### 7.6 Spec Revision Modes

The stakeholder spec may need modification after initial approval. SVP distinguishes two modes plus a temporary mechanism:

**Working notes (during blueprint dialog only).** When the blueprint dialog surfaces a narrow spec ambiguity, the human provides a short answer. The answer is appended as a working note with provenance marker. The blueprint dialog continues without interruption. Working notes are incorporated into the spec body at every iteration boundary — the spec is never left with appended patches.

**Targeted spec revision.** Triggered by the blueprint checker, diagnostic agent, or `/svp:redo`. The stakeholder dialog agent operates in revision mode: receives the current spec plus a specific critique, conducts a Socratic dialog about just that issue, and produces an amendment. Unrevised portions are untouched. The agent produces `SPEC_REVISION_COMPLETE` as its terminal status line. The pipeline restarts from Stage 2. Uses its own ledger (`ledgers/spec_revision_N.jsonl`).

**Full spec restart.** Complete redo of the Socratic dialog, producing a new spec from scratch. Rare and always human-initiated. Reserved for cases where the spec is fundamentally wrong or the human's understanding has changed substantially.

---

## 8. Stage 2: Blueprint Generation and Alignment (CHANGED IN 2.0, CHANGED IN 2.1)

Full Stage 2 sub-stage progression **(CHANGED IN 2.1 — Bug 23 fix)**:

```
blueprint_dialog → [Gate 2.1]
  Gate 2.1 APPROVE → alignment_check → [on ALIGNMENT_CONFIRMED] → Gate 2.2
                                      → [on ALIGNMENT_FAILED: spec → targeted spec revision → restart]
                                      → [on ALIGNMENT_FAILED: blueprint → fresh blueprint dialog]
  Gate 2.1 REVISE → re-invoke blueprint author agent
  Gate 2.1 FRESH REVIEW → invoke blueprint reviewer → [REVIEW_COMPLETE] → Gate 2.2
    Gate 2.2 (reached via two paths: (1) alignment confirmed by checker, (2) fresh review completed by reviewer)
    Gate 2.2 APPROVE → Pre-Stage-3
    Gate 2.2 REVISE → re-invoke blueprint author agent in revision mode
    Gate 2.2 FRESH REVIEW → re-invoke blueprint reviewer
```

The alignment check is the final validation step of Stage 2, not a separate stage. After the human approves the blueprint at Gate 2.1, the pipeline must invoke the blueprint checker before advancing to Pre-Stage-3. Without this step, the pipeline would proceed to test generation with an unvalidated blueprint.

### 8.1 Blueprint Dialog

**Two-branch routing requirement (NEW IN 2.1 — routing invariant).** The `blueprint_dialog` sub-stage is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `BLUEPRINT_DRAFT_COMPLETE` or `BLUEPRINT_REVISION_COMPLETE`, `route()` must emit a `human_gate` action for Gate 2.1 (`gate_2_1_blueprint_approval`), not re-invoke the blueprint author agent. A regression test must verify both branches.

A blueprint author agent conducts a Socratic dialog with the human about system decomposition, then generates the blueprint. The agent asks domain-level questions about conceptual phases, data flow, and boundaries — never about implementation details. When the dialog surfaces a spec ambiguity, the agent distinguishes between clarification (working note) and contradiction (targeted spec revision). Stateless across iterations — each alignment loop iteration starts a fresh dialog.

The blueprint author agent receives `project_profile.json` content (the `readme`, `vcs`, `delivery`, and `quality` sections) as task prompt context **(CHANGED IN 2.0, CHANGED IN 2.1)**. This allows the blueprint author to:

- Structure the delivery unit with awareness of the human's README preferences and source layout choice.
- Encode tool preferences as explicit behavioral contracts in affected units (Layer 1 of preference enforcement).
- Include commit style in the git repo agent's behavioral contract.
- Include quality tool preferences in the delivery unit's contracts **(NEW IN 2.1)**.
- Include changelog format in the delivery unit's contracts **(NEW IN 2.1)**.

**Constraint:** The profile is context, not instruction override. Discrepancies between profile and spec are surfaced through normal alignment.

The blueprint must produce units in the three-tier format:

- **Tier 1 — Description:** free prose describing purpose, inputs, outputs, role. May optionally include a `### Preferences` subsection (see below).
- **Tier 2 — Machine-readable signatures:** valid Python parseable by `ast`. Import statements declaring all types, followed by type-annotated function and class signatures with ellipsis bodies. Also includes invariants as Python `assert` statements.
- **Tier 3 — Error conditions, behavioral contracts, dependencies:** structured text. Error conditions as exception types with messages. Behavioral contracts as discrete testable claims. Dependencies as upstream unit references (backward-only).

**Unit-level Preferences subsection (NEW IN 2.1 — RFC-2).** Each unit's Tier 1 description in `blueprint_prose.md` may optionally include a `### Preferences` subsection. This subsection captures domain conventions, output appearance choices, and domain-specific decisions that are not requirements but matter to the human. The format is a `### Preferences` heading within the unit's Tier 1 block, followed by free prose describing the preferences.

- **Absence means "no preferences."** If a unit has no `### Preferences` subsection, no explicit "no preferences" marker is needed.
- **Authority hierarchy:** spec > contracts > preferences. Preferences are non-binding guidance that operates within the space that contracts leave open. A preference never overrides a behavioral contract or a spec requirement.
- **No new artifacts.** Preferences travel inside Tier 1 descriptions. Agents that receive Tier 1 (via `build_unit_context` with `include_tier1=True`) automatically receive any Preferences subsections. No changes to `prepare_task.py` are needed.

The blueprint author agent captures preferences during the decomposition dialog using Rules P1-P4 (see Unit 13 agent definition). The blueprint checker validates preference-contract consistency as a non-blocking warning (see Unit 14 agent definition).

**Unit granularity.** A unit is the smallest piece of code that can be independently tested against its blueprint contract without requiring any other unit's implementation to exist. Unit boundaries must be clean interfaces — if unit B depends on unit A, unit B's tests mock unit A based on its contract, never its implementation.

**Unit ordering.** Units are ordered by dependency in topological order. The first unit is the first piece of domain logic. The entry point is the last unit. No circular dependencies by construction.

**Backward-only dependency invariant.** This is a foundational structural constraint — the entire verification cycle, context isolation, stub generation, and fix ladder depend on it. Every unit's Tier 3 dependency list must reference only units with lower unit numbers. Unit 5 may depend on Units 1-4. It may never depend on Units 6 or higher. The blueprint author agent is explicitly instructed to enforce this in its system prompt. The blueprint checker validates it structurally (see Section 8.2). The infrastructure setup validates it again before creating directories (see Section 9). The stub generator refuses to generate stubs for forward-referenced units. A forward dependency is a blueprint-level failure — if detected at any stage, the pipeline returns to Stage 2.

The blueprint author produces two files: `blueprint_prose.md` containing all Tier 1 descriptions, and `blueprint_contracts.md` containing all Tier 2 signatures, invariants, and Tier 3 contracts. Both files use the same unit heading structure (`## Unit N: Name`) so that the blueprint extractor can parse them independently. The files are a pair — they must be submitted together at every gate and revised together in every alignment loop iteration.

**Context budget validation.** The blueprint must fit within the effective context budget and support selective extraction (a single unit's definition plus upstream contracts without loading the full blueprint).

### 8.2 Blueprint Alignment Check (CHANGED IN 2.0, CHANGED IN 2.1)

**Sub-stage:** `stage: "2", sub_stage: "alignment_check"` **(NEW IN 2.1 — Bug 23 fix)**.

**Routing requirement.** After Gate 2.1 APPROVE, the routing script must transition to the `alignment_check` sub-stage and invoke the blueprint checker agent — not advance directly to Pre-Stage-3. This is the same two-branch pattern as Bug 21: `route()` must check the current sub-stage and dispatch accordingly. The alignment check agent, phase, and gate vocabulary all exist in the system; the routing script must wire them into the execution path. A regression test must verify that after Gate 2.1 APPROVE, the next action is a blueprint checker invocation (not a stage advance to Pre-Stage-3).

**State persistence requirement (NEW IN 2.1 — Bug 42 fix).** When Gate 2.2 APPROVE triggers the transition from `alignment_check` to `pre_stage_3`, the `route()` function must persist the intermediate state to disk before returning the Pre-Stage-3 action block. If `route()` performs the transition in memory and then recursively routes to produce the Pre-Stage-3 action block without saving, the POST command of the returned action block will load stale state from disk and overwrite the transition. Note: `ALIGNMENT_CONFIRMED` itself presents Gate 2.2 (a human gate) and does not directly advance to Pre-Stage-3 -- the advance occurs only when the human selects APPROVE at Gate 2.2. This is governed by the route-level state persistence invariant (Section 3.6). Additionally, `dispatch_agent_status` for `reference_indexing` must advance the pipeline from `pre_stage_3` to stage 3 — it must not be a bare `return state` (exhaustive dispatch_agent_status invariant, Section 3.6).

A fresh blueprint checker agent receives the stakeholder spec (including working notes), both `blueprint_prose.md` and `blueprint_contracts.md`, reference summaries, and the project profile **(CHANGED IN 2.0, CHANGED IN 2.1)**. The checker verifies internal consistency: every unit present in the prose file must have a corresponding contracts entry, and every unit in the contracts file must have a corresponding prose entry. A unit present in one file but absent from the other is an unconditional alignment failure. It also verifies alignment and validates structural requirements: machine-readable signatures are parseable, all types have imports, per-unit context budget is within threshold, selective extraction works, working notes are consistent with spec text.

**DAG acyclicity validation.** The checker must parse every unit's Tier 3 dependency list, build the dependency graph, and verify: (1) no unit references a unit with a higher number (no forward edges), (2) no cycles exist, (3) every referenced unit number exists in the blueprint. This is a deterministic structural check on the blueprint text — no LLM judgment required. A forward edge or cycle is an unconditional blueprint failure, regardless of alignment status.

**Profile preference validation (Layer 2) (CHANGED IN 2.0, CHANGED IN 2.1).** The checker verifies that every profile preference — including documentation, metadata, commit style, delivery packaging, and quality tool configuration — is reflected as an explicit contract in at least one unit. A profile that says "conda, no bare pip" with no unit mentioning conda usage is an alignment failure. A profile that says "comprehensive README for developers" with no unit specifying audience and depth is also an alignment failure. A profile with `quality.linter: "ruff"` with no unit contracting ruff configuration generation is an alignment failure **(NEW IN 2.1)**.

**Pattern catalog validation (NEW IN 2.1).** The blueprint checker receives the pattern catalog section (Part 2) of the lessons learned document (`svp_2_1_lessons_learned.md`) as an additional input. The preparation script extracts Part 2 of the lessons learned document verbatim and includes it in the checker's task prompt. The checker cross-references the structural characteristics of the new blueprint against each known failure pattern (P1-P9 and any extensions). For each pattern, the checker asks: does this blueprint have structural features that have historically produced this pattern? A positive finding is reported as a blueprint risk (not an unconditional failure) with a specific description of the structural feature and the historical pattern it resembles. The human reviews these risks at Gate 2.2. This is advisory — it does not block blueprint approval — but it must be surfaced.

The lessons learned document is accessed via its workspace-relative path `references/svp_2_1_lessons_learned.md`. The basename `svp_2_1_lessons_learned.md` is the canonical filename constant in Unit 1's `ARTIFACT_FILENAMES`; the `references/` directory prefix is the standard location for reference documents (see Section 6.6 directory structure).

**Contract granularity verification (NEW IN 2.1 -- Bug 56 fix).** The blueprint checker MUST verify the following as alignment conditions (unconditional failures, not warnings):
- Every function in Tier 2 has a Tier 3 behavioral contract (Section 3.19, rule 1).
- Every gate response option has a per-gate-option dispatch contract in the routing unit (Section 3.19, rule 2).
- Every state transition function has a documented call site (Section 3.19, rule 3).
- Every re-entry path documents downstream dependency impact (Section 3.18).

**Report most fundamental level.** When the checker identifies problems at multiple levels, it reports only the deepest problem. Spec problems supersede blueprint problems.

Three outcomes:

- **Spec is the problem:** The checker identifies a gap or contradiction in the spec. Produces a precise critique. Working notes are absorbed into the spec, then targeted revision addresses the issue. Fresh blueprint dialog from scratch.
- **Blueprint is the problem:** The checker identifies a deviation, omission, or structural issue. Working notes are absorbed. Fresh blueprint author restarts with critique as context.
- **Alignment is confirmed:** The checker blesses the blueprint. The pipeline presents Gate 2.2 (`gate_2_2_blueprint_post_review`). The human chooses: **APPROVE** (advance to Pre-Stage-3), **REVISE**, or **FRESH REVIEW**. The human always decides when to advance -- `ALIGNMENT_CONFIRMED` never directly advances to Pre-Stage-3. If **FRESH REVIEW**: a distinct blueprint reviewer agent reads the documents cold and produces a critique. Review cycles are unbounded.

**Gate 2.2 dual entry paths.** Gate 2.2 (`gate_2_2_blueprint_post_review`) is reached via two distinct paths: (1) alignment confirmed by the blueprint checker (the "alignment is confirmed" outcome above — `ALIGNMENT_CONFIRMED` presents Gate 2.2), and (2) fresh review completed by the blueprint reviewer (the "FRESH REVIEW" option from either Gate 2.1 or Gate 2.2 itself — `REVIEW_COMPLETE` presents Gate 2.2). Both paths present the same gate with the same response options (**APPROVE**, **REVISE**, **FRESH REVIEW**). **APPROVE** at Gate 2.2 is the only path that advances to Pre-Stage-3 — the human always controls this transition. The routing script must handle both entry paths identically at Gate 2.2. **Path-context mechanism:** The preparation script for Gate 2.2 reads `last_status.txt` to distinguish the two paths: if `last_status.txt` contains `ALIGNMENT_CONFIRMED`, the path was checker to Gate 2.2, and the preparation script includes the alignment report (checker output) as gate context; if `last_status.txt` contains `REVIEW_COMPLETE`, the path was reviewer to Gate 2.2, and the preparation script includes the reviewer critique as gate context. This ensures the human sees the appropriate analysis at Gate 2.2 regardless of which path reached it.

**Gate naming rationale.** Gate 2.1 (`gate_2_1_blueprint_approval`) is the human's initial approval before machine validation — an alignment check has not yet run. Gate 2.2 (`gate_2_2_blueprint_post_review`) is the human's final approval after machine validation has confirmed alignment. The naming follows the same pattern as Stage 1: `gate_1_2_spec_post_review` is presented after the spec checker has validated the artifact, just as `gate_2_2_blueprint_post_review` is presented after the blueprint checker has validated the artifact.

**Scenarios — Gates 2.1/2.2.**
*Best case:* Checker confirms alignment first attempt. Human approves. Advances to Pre-Stage-3.
*Worst case:* Multiple failures — spec problems, then blueprint problems. Several fresh dialogs and spec revisions before alignment converges.

### 8.3 Alignment Loop

The blueprint generation and checking cycle may iterate. On each iteration:

- Working notes from the previous iteration are incorporated into the spec body.
- A fresh author agent conducts a new decomposition dialog (never resumes a prior dialog).
- A fresh checker agent evaluates alignment.
- Rejection reasons are logged.

**Iteration limit:** configurable, default 3. After the limit, the system generates a diagnostic summary explaining why alignment is not converging. Gate response options: **REVISE SPEC**, **RESTART SPEC**, **RETRY BLUEPRINT**.

**Scenarios — Gate 2.3.**
*Best case:* Never reached. Alignment converges within 1-2 attempts.
*Worst case:* Three attempts fail. The human uses the Help Agent to identify the root cause, revises the spec, and restarts.

### 8.4 Output

Blessed `blueprint_prose.md` and `blueprint_contracts.md` files with completion marker. Pipeline state updated. Session boundary fires.

---

## 9. Pre-Stage-3: Infrastructure Setup (CHANGED IN 2.0, CHANGED IN 2.1)

Before any unit verification begins, a deterministic infrastructure step prepares the build environment. This step is fully mechanical — no LLM involvement.

### 9.1 Dependency Extraction and Environment Creation

1. A deterministic script scans all machine-readable signature blocks across all units in the blueprint, extracting every external import statement.
2. The script produces a complete dependency list from the extracted imports.
3. The script creates the Conda environment and installs all packages.
4. The test framework packages from `toolchain.json` (`testing.framework_packages`: pytest, pytest-cov) must be installed unconditionally — test code uses pytest but it doesn't appear in blueprint signature blocks.
5. The quality tool packages from `toolchain.json` (`quality.packages`: ruff, mypy) must be installed unconditionally **(NEW IN 2.1)**.

Scripts read tool commands from `toolchain.json` instead of hardcoding them: `environment.create`, `environment.run_prefix`, `environment.install`, `testing.framework_packages`, `quality.packages` **(CHANGED IN 2.0, CHANGED IN 2.1)**.

Pre-Stage-3 always creates the Conda environment from scratch, regardless of whether an environment from a prior pass exists. If a prior environment exists with the same name, it is replaced.

### 9.2 Import Validation

After environment creation, the script validates that every extracted import resolves in the created environment:

```bash
conda run -n {env_name} python -c "from scipy.signal import ShortTimeFFT"
```

If any import fails to resolve, this is a blueprint problem — the pipeline returns to blueprint revision.

### 9.3 Directory Structure, Scaffolding, and DAG Validation

The script creates the source and test directory structure based on the blueprint's unit definitions: `src/unit_N/` and `tests/unit_N/` for each unit.

**DAG re-validation.** Before creating directories, the infrastructure script re-validates the dependency graph by parsing each unit's dependency list from the blueprint. If any forward edge or cycle is detected, the script fails with a clear error identifying the violating units. This is a belt-and-suspenders check — the blueprint checker should have caught this at Stage 2, but a corrupted or manually edited blueprint could reintroduce violations. This check is deterministic with no LLM involvement.

### 9.4 Output

A working Conda environment with all dependencies, framework packages, and quality tools installed and validated. A complete project directory structure. The pipeline state is updated to record pre-Stage-3 completion, including setting `total_units` to the number of units in the blueprint. Session boundary fires.

**`total_units` invariant (CHANGED IN 2.1 — Bug 24 fix):** `total_units` must be **derived from the blueprint** during infrastructure setup — by counting extracted units from the blueprint file. The infrastructure setup script is the **producer** of `total_units`, not a consumer. It must never read `total_units` from pipeline state (which is `null` at this point). The derivation sequence is: (1) extract units from the blueprint, (2) count them, (3) validate the count is a positive integer, (4) use the count for directory creation, (5) write the count to pipeline state. Any function that receives `total_units` as a parameter must validate it is a positive integer, not `None` — `dict.get("total_units", 1)` does not guard against an explicit `null` value (key exists with value `None`, so the default is not used). Required by unit completion logic to determine when Stage 4 should begin.

---

## 10. Stage 3: Unit-by-Unit Verification (CHANGED IN 2.0, CHANGED IN 2.1)

Units are processed in topological order as defined by the blueprint. No unit begins until the previous unit is fully verified.

### 10.0 Stage 3 Cycle Overview (CHANGED IN 2.1)

The complete per-unit cycle in SVP 2.1:

```
  1. STUB GENERATION → deterministic script (not an agent) generates stub from blueprint signatures
  2. PREPARE         → test agent task prompt
  3. INVOKE          → test agent generates tests
  4. QUALITY GATE A  → format + light lint on test files         (NEW IN 2.1)
  5. RED RUN         → run tests against stub (expect failure)
  6. PREPARE         → implementation agent task prompt
  7. INVOKE          → implementation agent writes code
  8. QUALITY GATE B  → format + heavy lint + type check          (NEW IN 2.1)
  9. GREEN RUN       → run tests against implementation (expect pass)
 10. COVERAGE REVIEW → verify coverage
 11. UNIT COMPLETION → marker, advance
```

**Stub generation (step 1) must precede test generation (step 2).** The test agent's generated tests import from the stub module. Without the stub, test collection fails with `ModuleNotFoundError` — a collection error, not a test failure. The stub also provides the test agent with the exact import paths and function signatures (Bug 36 fix).

If any step fails, the fix ladder engages. Quality gates (steps 4 and 8) are deterministic pre-processing steps, not new stages. They sit inside the existing cycle and follow the auto-fix-then-escalate pattern described in Section 10.12. When a quality gate fails, the cycle enters a retry sub-stage (`quality_gate_a_retry` or `quality_gate_b_retry`) that re-invokes the preceding agent for a fix re-pass before re-running the gate tools (see Section 10.12 for the full retry flow).

**Scenarios — Per-unit verification.**
*Best case:* Tests generated, quality gate A passes (auto-fix only), red run confirms meaningful tests, implementation generated, quality gate B passes (auto-fix only), green run passes, coverage complete. Zero human interaction per unit.
*Worst case:* Quality gate B finds type errors that the agent cannot fix in one re-pass. Gate fails, enters the fix ladder. The implementation fix ladder also fails. Diagnostic escalation determines the blueprint contract is wrong. Document revision. Pipeline restarts from Stage 2.

### 10.1 Test Generation

**Prerequisite:** Stub generation (Section 10.2) must complete before test generation begins.

A test agent receives the current unit's definition from the blueprint (description, inputs, outputs, errors, invariants, contracts, machine-readable signatures) and the contracts of upstream dependencies. These are provided as the task prompt.

The test agent generates a complete pytest test suite, including synthetic test data matching any data characteristics in the stakeholder spec. The test agent does not see any implementation.

**Synthetic data assumption declarations.** The test agent must declare its synthetic data generation assumptions as part of its output. These assumptions are presented to the human at the test validation gate.

The test agent is told that its output will be automatically formatted and linted by quality tools **(NEW IN 2.1)**. This is communicated through the agent definition's system prompt — the agent should write clean code from the start.

The test agent receives `testing.readable_test_names` from the profile **(CHANGED IN 2.0)**.

**Lessons learned filtering for test agent (NEW IN 2.1).** When assembling the test agent's task prompt, Unit 9 filters the lessons learned document for entries relevant to the current unit. Filtering criteria (applied as a union — any match qualifies):

1. Entries where the affected unit number matches the current unit number.
2. Entries where the pattern classification (P1-P8) matches a pattern associated with the current unit's dependency structure: units with many upstream dependencies are P1 candidates; units that read pipeline state are P2/P3 candidates.

Filtering is deterministic — no LLM involvement. Unit 9 reads the bug catalog (Part 1) and extracts entries matching the criteria. The filtered entries are appended to the test agent's task prompt under a heading: "Historical failure patterns for this unit — write tests that probe these behaviors." If no entries match, this section is omitted.

This adds token cost proportional to the filtered entries. For units with no history, cost is zero. For units with relevant history, cost is bounded by the number of matching entries.

### 10.2 Stub Generation (CHANGED IN 2.1 — Bug 36 fix)

A deterministic script reads the machine-readable signature block from the blueprint and generates a stub module using `ast`. Every function body raises `NotImplementedError`. Every class body contains the declared methods (each raising `NotImplementedError`) and any class-level attributes declared in the signature block (set to `None`). The script also generates `NotImplementedError` stub modules for upstream dependencies (same form as the current unit's stub — importable Python files with correct function and class signatures).

**Routing sub-stage (Bug 36 fix).** Stub generation is step 1 in the per-unit cycle (Section 10.0) and has its own routing sub-stage: `"stub_generation"`. The routing script emits a `run_command` action to invoke the stub generator script. Both `sub_stage: None` (initial entry after unit completion resets sub-stage) and `sub_stage: "stub_generation"` emit the same `run_command` action with the same POST command — `route()` normalizes `None` to `"stub_generation"` before dispatching. The sub-stage transitions: on `COMMAND_SUCCEEDED`, advance to `"test_generation"`. On `COMMAND_FAILED`, the stub generator error (forward-reference violation, malformed signatures) is presented to the human. Stub generation MUST complete before test generation begins — the test agent's imports depend on the stub module existing.

**Forward-reference guard.** The stub generator validates that every dependency referenced in the current unit's Tier 3 has a lower unit number than the current unit. If a forward reference is detected (e.g., Unit 5 lists Unit 8 as a dependency), the stub generator fails with a clear error. This is the third line of defense after the blueprint checker (Stage 2) and the infrastructure DAG validation (Pre-Stage-3).

**Stub sentinel (NEW IN 2.1).** The stub generator must prepend the following line as the first non-import statement in every generated stub file:

```python
__SVP_STUB__ = True  # DO NOT DELIVER — stub file generated by SVP
```

This sentinel is a machine-detectable marker. It is not removed by the implementation agent when writing the implementation — it is absent from implementations because implementations are written as new files, not edits to stub files. The sentinel's presence in any file indicates the file has not been implemented.

**Importability invariant.** The stub must be importable without error. Module-level `assert` statements are stripped from the parsed AST (they would fail against stub functions). Assertions inside function bodies are replaced along with the rest of the body.

### 10.3 Quality Gate A: Post-Test, Pre-Red-Run (NEW IN 2.1)

After the test agent produces tests and before the red run, a deterministic quality checkpoint runs on the test files.

**Sub-stage:** `"quality_gate_a"`.

**Purpose:** Ensure test code is clean before the red run. Prevents false red-run failures from syntax issues, import problems, or formatting errors in tests.

**Tools run (from `toolchain.json` `quality.gate_a`).** Each operation is resolved via `resolve_command` with `{target}` set to the test directory path (e.g., `tests/unit_N/`):
1. `ruff format {target}` — auto-fix formatting in place.
2. `ruff check --select E,F,I --fix {target}` — auto-fix basic errors (E), pyflakes (F), import sorting (I).

**Light lint rule set rationale:** Tests are about to fail by design (red run against stub). Heavy linting at this point would flag issues like "unused import" when the import is for the module under test that raises `NotImplementedError`. The light set catches real problems (syntax, undefined names, import order) without false positives from the stub-driven test structure.

**No type checking on tests.** Gate A does not run mypy on test files. Test code often uses dynamic fixtures, mock objects, and assertion patterns that produce false positives. Type checking runs only on implementation code (Gate B) and on the assembled project (Gate C).

**If auto-fix resolves everything:** Continue to red run. No agent involvement. This is the expected path — formatting and import sorting are fully mechanical.

**If residuals remain after auto-fix:** Issues that ruff cannot fix automatically (e.g., undefined name that isn't an import-sorting issue). The test agent gets one re-pass with the quality report appended to its task prompt. Sub-stage transitions to `"quality_gate_a_retry"`. After the re-pass, gate A runs again. If residuals persist after one retry, the gate **fails** and enters the fix ladder from the test side (same as a test generation failure).

**Retry budget:** 1 agent re-pass. This is separate from the fix ladder retry budget — if the gate fails after its retry and enters the fix ladder, the ladder gets its full budget.

### 10.4 Red Run

The main session runs the test suite against the stub via bash command. Test execution commands are resolved from `toolchain.json` **(CHANGED IN 2.0)**. Every test must fail. Three outcomes:

- **All tests fail:** structurally sound. Proceed to implementation. **State transition (Bug 45 fix):** `dispatch_command_status` for `test_execution` at `sub_stage=red_run` must advance `sub_stage` to `implementation` when `TESTS_FAILED` is received. A no-op return is invalid — it causes an infinite loop re-running the red run.
- **Some tests pass against the stub:** those tests are defective. Test suite is regenerated by a fresh test agent with the passing tests identified. Red run repeated. **State transition (Bug 65 fix):** `dispatch_command_status` for `test_execution` at `sub_stage=red_run` must increment `red_run_retries` when `TESTS_PASSED` is received, then: if retries < limit (default 3), advance `sub_stage` to `test_generation` for regeneration; if retries >= limit, advance `sub_stage` to `gate_3_1` to present Gate 3.1 (`gate_3_1_test_validation`) for human decision. See Section 3.6 extended dispatch table.
- **Tests error (won't run):** syntax problems, import issues, malformed fixtures. Test suite regenerated. Red run repeated.

If the test suite fails the red run after the configured number of attempts (default 3, tracked as `red_run_retries`), Gate 3.1 is presented for human decision (Section 10.9).

Collection error indicators are read from `toolchain.json` (`testing.collection_error_indicators`) **(CHANGED IN 2.0)**.

**"No tests ran" behavioral requirement.** The `"no tests ran"` indicator in the collection error list applies only when test files exist but pytest reports no tests collected (e.g., all test functions are skipped or deselected, or test files contain no valid test functions). An empty test directory with no test files present is a different condition — it indicates the test agent has not yet produced output — and must not be classified as a collection error. The dispatch logic must check for test file presence before applying this indicator.

### 10.5 Implementation

An implementation agent receives the same unit definition and generates the Python implementation. The implementation agent does not see the tests. This separation ensures that if the blueprint contains an ambiguity, the two agents are less likely to resolve it identically.

The implementation agent is told that its output will be automatically formatted, linted, and type-checked by quality tools **(NEW IN 2.1)**.

### 10.6 Quality Gate B: Post-Implementation, Pre-Green-Run (NEW IN 2.1)

After the implementation agent produces code and before the green run, a deterministic quality checkpoint runs on the implementation files.

**Sub-stage:** `"quality_gate_b"`.

**Purpose:** Ensure implementation is well-formed before testing. Catches type errors, style violations, and formatting issues that would either cause false test failures or produce sloppy code that passes tests.

**Tools run (from `toolchain.json` `quality.gate_b`, in order).** Each operation is resolved via `resolve_command` with `{target}` set to the implementation directory path (e.g., `src/unit_N/`):
1. `ruff format {target}` — auto-fix formatting in place.
2. `ruff check --fix {target}` — auto-fix all linting rules (full rule set).
3. `mypy {target} --ignore-missing-imports` — type check (report only, no auto-fix). The `--ignore-missing-imports` flag is specified in `toolchain.json` as `quality.type_checker.unit_flags`. At the unit level, mypy does not have visibility into upstream units' actual types — it checks only internal type consistency.

**Heavy lint rule set rationale:** At this point the implementation is supposed to be complete. Full linting catches: unused variables, overly complex functions, naming violations, missing docstrings (if configured), unreachable code, bare except clauses.

**If auto-fix resolves all lint issues and mypy passes:** Continue to green run. Expected fast path.

**If residuals remain:** Two categories:
- **Lint residuals** (ruff couldn't auto-fix): complexity or structural issues needing judgment.
- **Type errors** (mypy failures): interface mismatches, missing annotations, wrong return types.

The implementation agent gets one re-pass with the quality report appended to its task prompt. Sub-stage transitions to `"quality_gate_b_retry"`. After the re-pass, gate B runs again. If residuals persist after one retry, the gate **fails** and enters the fix ladder from the implementation side.

**Retry budget:** 1 agent re-pass. Separate from the fix ladder retry budget.

### 10.7 Green Run

The main session runs the test suite against the real implementation via bash command. All tests must pass. Test execution commands are resolved from `toolchain.json` **(CHANGED IN 2.0)**.

**State transition (Bug 45 fix, CHANGED — Bug 65 fix).** `dispatch_command_status` for `test_execution` at `sub_stage=green_run` must advance `sub_stage` to `coverage_review` when `TESTS_PASSED` is received. When `TESTS_FAILED` is received, the fix ladder must engage (Section 10.10): the dispatch advances `fix_ladder_position` to the next rung and sets `sub_stage` to `implementation` for retry, or to `gate_3_2` when the ladder is exhausted. A no-op return is invalid for either status — it causes an infinite loop re-running the green run. See Section 3.6 extended dispatch table.

### 10.8 On Pass: Coverage Review

A coverage review agent reads the blueprint and the passing test suite to identify behaviors the blueprint implies but no test covers. Missing coverage is added. Newly added tests go through red-green validation as an atomic operation within coverage review.

**Quality gate exception (CHANGED IN 2.1).** Coverage review does not re-run the full quality gate A or B cycles. However, newly added test code must receive a minimum quality floor: after coverage review adds test files, the routing script runs auto-formatting on the new test files as a deterministic `run_command` immediately after coverage review completion, before advancing to the next sub-stage. Specifically, the routing script emits `run_command` actions for `ruff format {target}` and `ruff check --select E,F,I --fix {target}` (the same Gate A auto-fix operations, resolved from `toolchain.json`). This is a formatting-only pass with no agent re-pass cycle, no type check, and no dedicated sub-stage — the auto-formatting commands execute within the `coverage_review` sub-stage's completion flow. If auto-fix resolves everything, continue to the red-green validation. Formatting residuals from coverage review auto-fix are silently accepted at this stage — they do not affect test correctness and are not eliminated but deferred: Gate C during Stage 5 assembly (Section 12.2) runs format check + full lint on the entire assembled project and will catch and fix them as part of the Stage 5 bounded fix cycle (Section 12.4). These deferred residuals will consume bounded fix cycle attempts in Stage 5; this is acceptable because formatting fixes are trivial for the git repo agent (auto-fix resolves them mechanically) and do not represent a meaningful draw on the Stage 5 retry budget. The implementation is not modified during coverage review, so Gate B does not re-run. If coverage review causes implementation changes (via the simplified fix ladder), those changes go through Gate B as part of the fix ladder's normal flow.

**State transition (Bug 46 fix, CHANGED — Bug 65 fix).** `dispatch_agent_status` for `coverage_review` returns state unchanged (keeps `sub_stage` at `coverage_review`). The two-branch routing pattern in `route()` reads `last_status.txt` to determine the next action: if `COVERAGE_COMPLETE: no gaps`, advance directly to `unit_completion`; if `COVERAGE_COMPLETE: tests added`, emit auto-format `run_command` before advancing. This change moves the dispatch logic from `dispatch_agent_status` to `route()` to support the two-branch pattern (Section 3.6 command-presenting entries).

**Green-run failure path.** If any newly added coverage test fails the green run, this follows the simplified fix ladder (Section 10.10). If a second coverage review produces tests that also fail, escalate directly to diagnostic — the repeated coverage gap pattern is a diagnostic signal.

### 10.9 On Fail: Test Validation

Before assuming the implementation is wrong, the diagnostic agent produces a structured analysis explaining the failing test's intent in plain language, including synthetic data assumptions.

Gate response options:

- **TEST CORRECT** — the test is right, the implementation needs fixing. Proceed to the implementation fix ladder. The human may provide a hint via `/svp:help`.
- **TEST WRONG** — the test doesn't match the human's requirements. Proceed to the test fix ladder:
  1. Fresh test agent receives: rejected test code, failure output, rejection reason, unit definition, upstream contracts, and any forwarded hint. Red run validation, then green run.
  2. If the fresh agent's tests also fail: the human is re-involved with Help Agent. One additional hint-assisted attempt. If this also fails, diagnostic agent determines whether the issue is blueprint-level. No further test fix attempts.

### 10.10 Implementation Fix Ladder

A deterministic escalation sequence when tests fail and the test is confirmed correct:

1. **Fresh agent attempt.** A fresh implementation agent receives: failing code, test failure output, diagnostic analysis, unit definition, upstream contracts, and any hint. Tests re-run.
2. **Diagnostic escalation.** If the fresh agent also fails, the diagnostic agent is invoked with the three-hypothesis discipline (Section 10.11).

**Position-aware ladder advancement.** The state-update script checks the current fix ladder position before advancing. The ladder progresses: `None → fresh_impl → diagnostic → diagnostic_impl → exhausted`. The handler advances to the *next* rung, never re-enters the current position.

### 10.11 Diagnostic Escalation: Three-Hypothesis Discipline

The diagnostic agent receives the stakeholder spec, blueprint (current unit plus upstream contracts), tests, failing implementation(s), and error output. Before converging, it must articulate a plausible case at each of three levels:

- **Implementation-level:** code is wrong relative to a correct blueprint. Remedy: one more implementation attempt with diagnostic guidance.
- **Blueprint-level:** unit definition or contracts are wrong relative to a correct spec. Remedy: restart from Stage 2.
- **Spec-level:** requirements are incomplete or contradictory. Remedy: targeted spec revision, then restart from Stage 2.

**Dual-format output:** prose for the human, then structured block:

```
[PROSE]
Here's what I think happened...

[STRUCTURED]
UNIT: 4
HYPOTHESIS_1: implementation -- off-by-one in loop boundary
HYPOTHESIS_2: blueprint -- contract doesn't specify boundary behavior
HYPOTHESIS_3: spec -- no mention of boundary handling for edge electrodes
RECOMMENDATION: implementation
```

Terminal status: `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec`.

Gate response options:

- **FIX IMPLEMENTATION**: one fresh agent attempt with diagnostic guidance and optional hint. If this fails, escalate to document revision.
- **FIX BLUEPRINT**: restart from Stage 2.
- **FIX SPEC**: targeted spec revision, then restart from Stage 2.

### 10.12 Quality Gate Mechanism (NEW IN 2.1)

This section specifies the quality gate mechanism that applies to both Gate A (Section 10.3) and Gate B (Section 10.6).

**Not a new stage, not a new fix ladder position.** Quality gates are deterministic pre-processing steps within the existing Stage 3 cycle. They are analogous to Pre-Stage-3 infrastructure setup — a deterministic script runs, reports success or failure, and the routing script acts on the result.

**Auto-fix first, agent escalation for residuals.** All gates run deterministic tools first. Tools that support auto-fix (`ruff format`, `ruff check --fix`) modify files in place. Tools that are report-only (`mypy`) produce output without modifying files. If all tools succeed (no residuals), the gate passes and the pipeline continues. No agent involvement.

**Residual classification.** After auto-fix, residuals fall into two categories:
- **Lint residuals:** issues ruff reported but could not auto-fix. Typically complexity violations, structural issues, or naming problems.
- **Type errors:** mypy failures. Interface mismatches, missing annotations, wrong types.

Both categories are reported to the producing agent as a structured quality report appended to its task prompt for the re-pass.

**One retry, then fix ladder.** The producing agent (test agent for Gate A, implementation agent for Gate B) gets exactly one re-pass. The test agent's re-pass produces `TEST_GENERATION_COMPLETE` and the implementation agent's re-pass produces `IMPLEMENTATION_COMPLETE` — the same terminal status lines as their initial invocations. After the re-pass, the gate runs again. If residuals persist:
- Gate A failure → enters the test fix ladder (same as a test generation failure).
- Gate B failure → enters the implementation fix ladder (same as a green-run failure).

**Quality gate retries are separate from fix ladder retries.** The gate gets 1 retry. If it fails and enters the fix ladder, the ladder gets its full budget. Quality gates run again after the ladder produces new code. This prevents quality issues from stealing retry budget from logic issues.

**Quality gates are mandatory.** There is no opt-out flag. Formatting and linting are a pipeline guarantee. Every project built by SVP 2.1 receives formatted, linted, type-checked code.

**File modification by quality tools.** Quality auto-fix modifies files in place via subprocess calls from deterministic scripts, not via Claude Code's Write tool. The hook system controls Claude Code tool invocations, not subprocess calls from pipeline scripts. Quality auto-fix bypasses hooks — this is correct. The scripts run as pipeline infrastructure.

**State machine additions.** Five sub-stages (CHANGED IN 2.1 — Bug 36 fix adds `stub_generation`):
- `"stub_generation"` — first step of per-unit cycle, before test_generation (Bug 36 fix).
- `"quality_gate_a"` — between test_generation and red_run.
- `"quality_gate_b"` — between implementation and green_run.
- `"quality_gate_a_retry"` — agent re-pass for Gate A residuals.
- `"quality_gate_b_retry"` — agent re-pass for Gate B residuals.

**Routing script additions.** The routing script gains new paths:

```
After test agent completes → quality_gate_a:
  Run quality commands (deterministic, from toolchain.json gate_a list,
    each operation qualified with "quality." prefix per Section 6.5.1 quality gate operation resolution)
  If clean → advance to red_run
  If residuals → set sub_stage to quality_gate_a_retry
    Re-invoke test agent with quality feedback
    Re-run quality gate A
    If clean → advance to red_run
    If still residuals → enter fix ladder (test side)

After implementation agent completes → quality_gate_b:
  Run quality commands (deterministic, from toolchain.json gate_b list,
    each operation qualified with "quality." prefix per Section 6.5.1 quality gate operation resolution)
  If clean → advance to green_run
  If residuals → set sub_stage to quality_gate_b_retry
    Re-invoke implementation agent with quality feedback
    Re-run quality gate B
    If clean → advance to green_run
    If still residuals → enter fix ladder (implementation side)
```

### 10.13 Unit Completion

A unit is verified when:

- All tests passed the red run (failed against stub).
- All tests passed the green run (passed against implementation).
- Quality gates A and B passed **(NEW IN 2.1)**.
- The coverage review agent has confirmed complete coverage.

The unit's code and tests are saved. A completion marker is written to `.svp/markers/unit_N_verified`. The state-management script resets `sub_stage` to `None`, `fix_ladder_position` to `None`, and `red_run_retries` to `0`, ensuring the new unit starts from scratch. Session boundary fires.

**COMMAND/POST separation (Bug 47 fix).** The `unit_completion` routing action's COMMAND field must not embed `update_state.py` calls or any other state update invocations. State updates are exclusively the responsibility of the POST command. If both COMMAND and POST invoke `update_state.py` for the same phase, the state update runs twice: the first call advances `current_unit`, and the second call raises `TransitionError` because the unit is no longer current. The COMMAND should only write the completion marker and status; the POST command handles the state transition via `update_state.py --phase unit_completion`.

### 10.14 Context Isolation

Each unit is processed in a fresh context window containing only:

- The stakeholder spec.
- The current unit's definition extracted from the blueprint (not the full blueprint).
- The contract signatures of upstream dependencies.

No prior unit's implementation code is loaded. Each unit is built assuming all others work according to their blueprint contracts. The extraction is a deterministic script operation, not LLM summarization.

---

## 11. Stage 4: Integration Testing (CHANGED IN 2.0, CHANGED IN 2.1)

### 11.1 Integration Test Generation

**Two-branch routing requirement (NEW IN 2.1 — routing invariant).** Stage 4 is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `INTEGRATION_TESTS_COMPLETE`, `route()` must emit a `run_command` action to execute the integration test suite, not re-invoke the integration test author agent. This is a command-presenting entry (Section 3.6): the "done" branch runs the test suite deterministically rather than presenting a human gate. A regression test must verify both branches.

After all units pass individual verification, an integration test author agent generates tests that cover cross-unit interactions. This agent receives a lean task prompt: the stakeholder spec plus contract signatures from all units. The full blueprint is not loaded into the task prompt — the agent reads specific source files on demand from disk.

The integration tests specifically target behaviors that no single unit owns: data flow across the full chain, resource contention, timing dependencies, error propagation across unit boundaries, and emergent behavior from unit composition. At least one end-to-end test must validate a complete input-to-output scenario from the stakeholder spec, checking domain-meaningful output values.

**SVP 2.1 integration test coverage requirement (CHANGED IN 2.0, CHANGED IN 2.1).** The integration test author must cover all cross-unit paths introduced by SVP 2.0 and 2.1:

1. **Toolchain resolution chain:** Profile → `toolchain.json` → reader → resolved command. Verify fully resolved commands match SVP 1.2 equivalents.
2. **Profile flow through preparation script:** Verify correct profile sections reach correct agents.
3. **Blueprint checker profile validation:** Verify alignment failure when blueprint omits a profile-mandated constraint.
4. **Redo agent profile classification:** Verify `profile_delivery` for delivery-only changes, `profile_blueprint` for blueprint-influencing changes.
5. **Gate 0.3 dispatch:** Verify state transitions for `PROFILE APPROVED` and `PROFILE REJECTED`.
6. **Preference compliance scan:** Verify detection of banned patterns in synthetic delivered code.
7. **Write authorization for new paths:** Verify `project_profile.json` writable during correct sub-stages, blocked otherwise. Verify `toolchain.json` always blocked. Verify `ruff.toml` always blocked **(NEW IN 2.1)**.
8. **Redo-triggered profile revision state transitions.**
9. **Quality gate execution chain (NEW IN 2.1):** Verify Gate A runs correct tools from `toolchain.json` `gate_a` list on test files; verify Gate B runs correct tools from `gate_b` list on implementation files; verify auto-fix modifies files in place; verify residual detection triggers agent re-pass; verify gate failure after retry enters the correct fix ladder position.
10. **Quality gate retry isolation (NEW IN 2.1):** Verify gate retry does not consume fix ladder retry budget.
11. **Quality package installation (NEW IN 2.1):** Verify `quality.packages` installed during Pre-Stage-3 alongside `testing.framework_packages`.

### 11.2 Integration Test Execution

The main session runs the integration test suite via bash command. Test commands resolved from `toolchain.json` **(CHANGED IN 2.0)**.

#### 11.2.1 Three-State Post-Execution Dispatch (NEW IN 2.1)

**Relationship to the two-branch routing invariant (Section 3.6).** The two-branch routing invariant governs the transition *before* the integration test command runs (agent done vs. not done). The three-state dispatch governs the transition *after* the integration test command completes (pass vs. fail vs. exhausted). These are sequential, independent dispatch points. First, the two-branch check determines whether to invoke the integration test author agent or run the test suite. Then, after the test suite `run_command` completes, the three-state dispatch determines the next pipeline action based on the test result.

After the integration test `run_command` completes, the routing script performs three-state dispatch based on the test result status and retry count:

1. **Tests passed** (`TESTS_PASSED`): All integration tests pass. Advance to Stage 5.
2. **Tests failed** (`TESTS_FAILED`): One or more integration tests failed. Present the diagnostic gate (Section 11.4, Gate 4.1). The diagnostic agent applies the three-hypothesis discipline with an inverted prior.
3. **Retries exhausted** (retries >= 3): The assembly fix ladder has been exhausted after three attempts. Present Gate 4.2 with options **FIX BLUEPRINT** or **FIX SPEC**. No further assembly fix attempts.

This dispatch is a first-class behavioral requirement. The routing script must implement all three branches explicitly. A missing branch (e.g., no check for retries >= 3) causes the pipeline to loop indefinitely or present the wrong gate.

### 11.3 On Pass

Proceed to Stage 5.

### 11.4 On Fail

The diagnostic agent applies the three-hypothesis discipline with an inverted prior: integration failures are disproportionately blueprint-level issues. Dual-format output.

Gate response options:

- **ASSEMBLY FIX**: units are correct individually; assembly has a localized error. Assembly fix ladder (three attempts):
  1. Fresh implementation agent with failure output, diagnostic guidance, and interface-boundary constraint. Fix applied, affected unit tests re-run, then integration tests re-run.
  2. Same with first attempt's failure context.
  3. Human involved. Help agent available. Hint forwarded. If this fails or breaks unit tests, the ladder is exhausted. Gate 4.2: **FIX BLUEPRINT** or **FIX SPEC**.

- **FIX BLUEPRINT**: restart from Stage 2.
- **FIX SPEC**: targeted spec revision, then restart from Stage 2.

---

## 12. Stage 5: Repository Delivery (CHANGED IN 2.0, CHANGED IN 2.1)

### 12.1 Repository Creation

**Two-branch routing requirement (NEW IN 2.1 — routing invariant, Bug 43 fix).** Stage 5 is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `REPO_ASSEMBLY_COMPLETE`, `route()` must emit a `human_gate` action for Gate 5.1 (`gate_5_1_repo_test`), not re-invoke the git repo agent. If `route()` unconditionally re-invokes the agent without checking `last_status.txt`, the pipeline loops indefinitely after the repository is already assembled. A regression test must verify both branches.

The git repo agent creates a clean git repository in `projectname-repo/` at the same level as the project workspace. On successful repository creation, the pipeline records the absolute path of the delivered repository in `pipeline_state.json` as `delivered_repo_path` **(NEW IN 2.1)**. This path is deterministically available to all subsequent operations, including the post-delivery debug loop.

**Repo collision avoidance (NEW IN 2.1).** When the pipeline reaches Stage 5 and the target directory `projectname-repo/` already exists (e.g., from a previous pass before an `/svp:redo` triggered a restart), the git repo agent must not overwrite or merge into the existing directory. Instead, the existing directory is renamed to `projectname-repo.bak.YYYYMMDD-HHMMSS` (using the current UTC timestamp) before creating the new repository. This preserves the previous delivery for human inspection while ensuring a clean directory for the new assembly. The rename is performed by the deterministic preparation script before the git repo agent is invoked — the agent always receives a clean target path. If multiple backup directories exist from prior passes, they are all preserved (no cleanup of older backups). The `delivered_repo_path` in `pipeline_state.json` is updated to reflect the new repository path, which is always `projectname-repo/` (the canonical name, not a timestamped variant).

Commits in order:

1. Conda environment file, dependency list, directory structure — first commit.
2. The stakeholder spec — second commit.
3. The blueprint — third commit.
4. Each unit with implementation and tests, committed sequentially in topological order.
5. Integration tests.
6. Project configuration files (entry point, README).
7. Document version history (`docs/history/`).
8. Reference documents and summaries (`docs/references/`).
9. Project context (`docs/project_context.md`) **(NEW IN 2.1 — unified Bug 15 fix)**.
10. Quality tool configuration files **(NEW IN 2.1)**.
11. Changelog **(NEW IN 2.1, if configured)**.

### 12.1.1 Assembly Mapping: Workspace to Repository

During assembly, the git repo agent relocates unit implementations from workspace paths (`src/unit_N/`) to final locations. The blueprint's preamble file tree is the authoritative mapping.

Rules:
1. Read the blueprint file tree with `<- Unit N` annotations.
2. Copy implementation content, not file paths.
3. Never reference `src/unit_N/` paths in entry points or imports.
4. Rewrite cross-unit imports from `src.unit_N` to final module paths.
5. The `src/` directory in the delivered repo is organized by the blueprint file tree, not by unit number.
6. Non-Python deliverables are produced as `{FILENAME_UPPER}_CONTENT` string constants in the unit's implementation, extracted during assembly.

### 12.2 Quality Gate C: Assembly Quality Check (NEW IN 2.1)

During Stage 5 structural validation, after assembly and before the compliance scan, a cross-unit quality check runs on the complete assembled project.

**No dedicated sub-stage (CHANGED IN 2.1).** Unlike Gates A and B (which are routing-level checkpoints between agent invocations and have their own sub-stages), Gate C runs as part of the structural validation step within the git repo agent's assembly cycle. It does not have a `quality_gate_c` sub-stage in `pipeline_state.json`. This is because Gate C operates within the bounded fix cycle (Section 12.4) — if it finds issues, the git repo agent addresses them in its next assembly iteration. Gates A and B need sub-stages because they sit between different agent invocations (test agent to red run, implementation agent to green run) and the routing script must dispatch accordingly.

**Execution mechanism.** Gate C uses the same deterministic quality gate script as Gates A and B, invoked during the structural validation step (Section 12.3) with `"gate_c"` as the gate identifier. The gate identifier selects the operation list from `toolchain.json` (`quality.gate_c`) and the flags value (`type_checker.project_flags`), exactly as `"gate_a"` and `"gate_b"` do for their respective gates. The only difference is invocation context: Gates A/B are invoked by the routing script at routing-level checkpoints; Gate C is invoked by the structural validation script within the bounded fix cycle.

**Tools run (from `toolchain.json` `quality.gate_c`).** Each operation is resolved via `resolve_command` with `{target}` set to the assembled project source directory path. Target resolution is layout-dependent: for conventional layout, `{target}` resolves to `src/packagename/`; for flat layout, `{target}` resolves to the package directory at the repository root (e.g., `packagename/`); for SVP-native layout, `{target}` resolves to `src/` (the parent of all `unit_N/` directories). The structural validation script determines the correct target path from `delivery.source_layout` in the project profile. Example for conventional layout:
1. `ruff format --check {target}` — verify formatting (should already be clean from Gate B; this is belt-and-suspenders).
2. `ruff check {target}` — full lint on assembled project.
3. `mypy {target}` — cross-unit type check with full visibility. No `--ignore-missing-imports` — the full project is assembled so all imports should resolve.

**Purpose:** Catch cross-unit interface mismatches, naming collisions, and inconsistencies not visible at the single-unit level. Gate B checks each unit with `--ignore-missing-imports`; Gate C checks the assembled whole with full type resolution.

**Unused exported function detection (NEW IN 2.1 -- Bug 56 fix).** After lint and type check pass, Gate C scans the assembled codebase for exported functions (functions listed in Tier 2 signatures) that are defined but never called from any other module. This is a dead code detection check that catches functions implemented but never wired into the dispatch path (the pattern that produced Bugs 52-55). The check uses ruff's F811 rule or a custom AST-based scan -- whatever fits the existing quality tool pipeline. Functions that are only called from tests are NOT considered unused (test-only usage is valid).

**If unused exported functions are found:** Gate C does NOT automatically fail or trigger a restart. Instead, the pipeline presents a human gate -- Gate 5.3 (`gate_5_3_unused_functions`) -- with the findings (which functions, where defined, no call site found). The gate **strongly recommends** the human invoke `/svp:redo` to go back and fix the spec/blueprint, since unused exported functions typically indicate a spec-level or blueprint-level gap. The human can choose:
- **FIX SPEC** -- invoke the equivalent of `/svp:redo` to address the structural gap (strongly recommended)
- **OVERRIDE CONTINUE** -- acknowledge the dead code and proceed with delivery; the human takes responsibility for the unused functions

This is a human judgment gate, not an automatic failure. The human may have valid reasons to ship with unused functions (e.g., public API surface intended for external callers, future extension points). The pipeline surfaces the finding; the human decides.

**If other issues found (format, lint, type check):** They enter the existing Stage 5 bounded fix cycle (Section 12.4) as structural validation failures. Gate C findings are included as context in the next bounded fix cycle iteration — a fresh git repo agent invocation receives the quality report along with other structural validation failures. The agent is single-shot; it does not iterate internally. No new mechanism needed.

### 12.3 Structural Validation (CHANGED IN 2.1)

After assembly, a deterministic validation step checks:

- All expected files exist at their blueprint-specified paths.
- No `src/unit_N/` paths remain in the delivered repository.
- All imports resolve correctly.
- `pyproject.toml` entry point references final module paths.
- The SVP launcher (if Mode A) is self-contained.
- Quality Gate C passes (format check + full lint + full type check) **(NEW IN 2.1)**.
- Delivery compliance scan passes (Layer 3 — see Section 12.5). Note: the compliance scan runs initially within the bounded fix cycle as part of structural validation, then runs again as a final verification in the `"compliance_scan"` sub-stage after human testing (Section 22.4).
- Commit structure matches the prescribed order (Section 12.1): one commit per prescribed step, minus any steps the profile disables (e.g., `vcs.changelog: "none"` omits the changelog commit). The expected count equals the number of enabled steps in the commit order table. A single monolithic commit is a structural validation failure **(NEW IN 2.1 — Bug 28 fix)**.
- All regression and unit tests pass when run in the delivered repository layout, not only the workspace layout. Path-dependent modules that are relocated during assembly (e.g., from `src/unit_N/` to `svp/scripts/`) must resolve correctly in the delivered layout **(NEW IN 2.1 — Bug 29 fix)**.
- No delivered Python source file contains the string `__SVP_STUB__`. The presence of this sentinel in any assembled file means the git repo agent copied a stub instead of an implementation. This is an immediate structural validation failure. The error message must identify the offending file: "Structural validation failed: stub file detected in delivered repository. File: {path} contains __SVP_STUB__ sentinel." Enters the bounded fix cycle **(NEW IN 2.1)**.
- Both `blueprint_prose.md` and `blueprint_contracts.md` exist in `docs/`. A missing file is a structural validation failure. (The delivered `docs/` directory contains the complete blueprint as a paired artifact, not a single file.) **(NEW IN 2.1)**.
- `pyproject.toml` contains `[tool.pytest.ini_options]` with appropriate `pythonpath` configuration enabling tests to pass in the delivered repository layout, not only the workspace layout. The pytest path configuration must reference the final module locations as specified in the blueprint file tree **(NEW IN 2.1 — Bug 29 fix)**.
- README is a carry-forward artifact in Mode A: content from the previous version's README (`references/README_v{previous}.md`) is preserved and extended, not rewritten. Structural validation checks that the reference README's headings and content lines are present in the delivered README (see Section 12.7) **(NEW IN 2.1 — Bug 30 fix)**.

Structural validation failures follow the bounded fix cycle.

### 12.4 Bounded Fix Cycle

1. The git repo agent assembles the repository.
2. Structural validation runs (Section 12.3).
3. The pipeline instructs the human with an exact test command to run in the delivered repository. The human runs this manually — verifying the repo is self-contained.
4. Gate response: **TESTS PASSED** or **TESTS FAILED** (with output pasted).
5. If fail: a fresh git repo agent reassembles with error output as context.
6. Up to 3 attempts. If all fail, Gate 5.2: **RETRY ASSEMBLY**, **FIX BLUEPRINT**, or **FIX SPEC**.

### 12.5 Delivery Compliance Scan (Layer 3) (CHANGED IN 2.0)

During structural validation, a deterministic script reads the `delivery` section of `project_profile.json` and scans delivered Python source files for preference violations.

**Scan scope.** Python source files in `src/` and `tests/`. Documentation, configuration, and end-user scripts are not scanned. The scan operates on the AST, inspecting subprocess invocation calls for command strings containing tool names that violate the profile's delivery toolchain constraints. It does not flag non-executable contexts (comments, docstrings, print statements). Limited to literal string or f-string command arguments — variable-constructed commands are not analyzed.

**Banned pattern sets by delivery environment recommendation:**

- **conda** (default): scan for `pip`, `python`, or `pytest` as bare tokens not preceded by `conda run -n`.
- **pyenv**: scan for `conda` commands.
- **venv**: scan for `conda` commands.
- **poetry**: scan for `conda` commands or bare `pip install` calls.
- **none**: scan source files for any environment manager commands.

Violations enter the bounded fix cycle.

### 12.6 Commit Message Style (CHANGED IN 2.0)

The git repo agent reads `vcs.commit_style` from `project_profile.json`. Conventional (default), freeform, or custom template.

### 12.7 README Generation (CHANGED IN 2.0)

The git repo agent reads the `readme` and `delivery` sections from `project_profile.json`: section structure, custom sections, audience and depth, optional content flags, installation instructions matching `delivery.environment_recommendation`.

**Mode A (SVP self-build):** carry-forward artifact. The previous version's README (`references/README_v{previous}.md`) is the base document. The git repo agent preserves its full content — structure, prose, installation instructions, configuration, commands, history — and adds only the sections describing new features in the current release. The 12-section structure is captured explicitly in the profile. The agent must not rewrite, reorganize, or summarize existing content; it extends.

**Mode B (general project):** generated from profile preferences. If a reference README is provided (e.g., from a previous version or an upstream project), the git repo agent preserves the provided content and extends it rather than generating from scratch.

*Mode B section template:*
1. Header and tagline — from stakeholder spec.
2. What [Project] Does — high-level description.
3. Who It's For — target audience from spec.
4. Installation — from Conda environment file and `pyproject.toml`, matching delivery environment.
5. Configuration — if applicable.
6. Usage — CLI commands, API entry points, or library usage.
7. Quick Tutorial — if the project has a natural happy path.
8. Examples — if bundled examples exist.
9. Project Structure — directory tree of delivered repo.
10. License — from stakeholder spec.

Derive all content from the spec and blueprint. Omit inapplicable sections. Write for the project's target audience.

### 12.8 Delivered Source Layout (CHANGED IN 2.0)

The git repo agent reads `delivery.source_layout`:
- `"conventional"`: restructures `src/unit_N/` into `src/packagename/` with `__init__.py`.
- `"flat"`: package at repository root.
- `"svp_native"`: keeps `src/unit_N/` as-is.

**Module collision detection.** When `source_layout` is `conventional`, the git repo agent detects name collisions during restructuring. Collisions enter the bounded fix cycle.

### 12.9 Delivered Dependency Format (CHANGED IN 2.0)

The git repo agent reads `delivery.dependency_format` and generates the appropriate files. When multiple formats are specified, the first is the primary recommendation in README.

### 12.10 Entry Points (CHANGED IN 2.0)

If `delivery.entry_points` is true, the git repo agent generates `[project.scripts]` in `pyproject.toml`. Path format depends on `delivery.source_layout`.

### 12.11 SPDX License Headers (CHANGED IN 2.0)

If `license.spdx_headers` is true, SPDX identifier comments added to all delivered source files.

### 12.12 Additional Metadata in Delivery (CHANGED IN 2.0)

The git repo agent acts on `license.additional_metadata`: citation → "How to Cite" section and `CITATION.cff`, funding → "Acknowledgments" section, acknowledgments → alongside funding, unknown keys → generic key-value list.

### 12.13 Delivered Quality Configuration (NEW IN 2.1)

The git repo agent reads the `quality` section from `project_profile.json` and generates quality tool configuration for the delivered project:

- If `quality.linter` is not `"none"`: generates the appropriate configuration section in `pyproject.toml` (for ruff, flake8, pylint) or standalone config file, adds the linter package to delivery dependency files.
- If `quality.formatter` is not `"none"`: generates formatter configuration, adds package to delivery dependencies.
- If `quality.type_checker` is not `"none"`: generates type checker configuration (`[tool.mypy]` or `[tool.pyright]` in `pyproject.toml`), adds package to delivery dependencies.
- If `quality.import_sorter` is not `"none"` and differs from linter: generates import sorter configuration, adds package.
- `quality.line_length` is applied to all quality tool configurations.

**Delivered vs. pipeline quality tools.** The delivered project's quality configuration reflects the human's preferences from the profile, not the pipeline's internal tools. If the human chose `quality.formatter: "black"` and the pipeline used ruff internally, the delivered project ships with black configuration. The pipeline's internal quality tools (ruff + mypy) are pipeline artifacts — they do not appear in the delivered repo.

**Mode A clarification (SVP self-build).** When SVP builds itself, `ruff.toml` appears in the delivered repository in two distinct roles that must not be confused:

1. **As a plugin artifact** at `svp/scripts/toolchain_defaults/ruff.toml` — this is a pipeline tool that future SVP-built projects will use during their build. It is part of the SVP plugin's deliverables, specified in the blueprint file tree. The git repo agent places it there during assembly because the blueprint says so, not because of the quality profile.

2. **As contributor quality config** in `pyproject.toml` `[tool.ruff]` section — this is the delivered quality configuration from the profile's `quality` section. It tells SVP's own contributors how to lint their code.

These are different files serving different consumers. The blueprint author must ensure the git repo agent generates both: one from the unit that produces the toolchain defaults (a blueprint-specified deliverable), and one from the profile-driven delivery logic (Section 12.13). The two may have identical settings in Mode A, but they exist for different reasons and are generated by different mechanisms.

### 12.14 Changelog (NEW IN 2.1)

The git repo agent reads `vcs.changelog` from `project_profile.json`:

- `"keep_a_changelog"`: generates `CHANGELOG.md` following Keep a Changelog format, with an initial "Unreleased" section.
- `"conventional_changelog"`: generates `CHANGELOG.md` in Conventional Changelog format, with an initial version section.
- `"none"`: no changelog generated.

### 12.15 Delivered Repository Contents (CHANGED IN 2.0, CHANGED IN 2.1)

The delivered repository includes:

- All source code, organized per `delivery.source_layout`.
- All test suites (unit and integration).
- The stakeholder spec, `blueprint_prose.md`, and `blueprint_contracts.md` as documentation in `docs/`.
- Document version history in `docs/history/`.
- Project context (`docs/project_context.md`) **(NEW IN 2.1 — unified Bug 15 fix)**.
- Reference documents and their summaries in `docs/references/` **(NEW IN 2.1 — unified Bug 15 fix)**.
- A Conda environment file.
- Dependency files per `delivery.dependency_format`.
- `README.md` per profile preferences.
- A `.gitignore` excluding Python build artifacts.
- A clean git history with commit messages per `vcs.commit_style`.
- Quality tool configuration per `quality` profile **(NEW IN 2.1)**.
- `CHANGELOG.md` per `vcs.changelog` **(NEW IN 2.1)**.
- `CITATION.cff` if `readme.citation_file` is true.
- `LICENSE` file matching `license.type`.
- `CONTRIBUTING.md` if `readme.contributing_guide` is true.

**Artifacts NOT included in delivered repo:** `toolchain.json` (pipeline config at workspace root), `project_profile.json`, `ruff.toml` (pipeline config at workspace root), `pipeline_state.json`, `svp_config.json`, conversation ledgers, diagnostic logs, raw iteration artifacts. Note: in Mode A (self-build), the delivered SVP plugin contains `svp/scripts/toolchain_defaults/python_conda_pytest.json` and `svp/scripts/toolchain_defaults/ruff.toml` as plugin artifacts — these are part of the blueprint file tree, distinct from the workspace-root pipeline config files that are excluded.

**Bundled example (Mode A only):** `examples/game-of-life/` with stakeholder spec, blueprint, and project context. Carry-forward artifact.

### 12.16 Workspace Cleanup

Upon successful delivery, the pipeline congratulates the human, announces `/svp:bug` availability, and offers `/svp:clean` with three options: archive, delete, or keep.

**Workspace cleanup constraints:**
- Conda environment removed via `conda env remove -n {env_name} --yes`.
- Directory deleted with permission-aware handler (`__pycache__` may be read-only).
- The delivered repository is never touched by `/svp:clean`.
- Invoked as `PYTHONPATH=scripts python scripts/cmd_clean.py`.

### 12.17 Post-Delivery Debug Loop (CHANGED IN 2.1)

After Stage 5 completion, the human may discover bugs. `/svp:bug` initiates a structured debug loop.

#### 12.17.1 Entry Point and Debug Permission Reset

`/svp:bug` serves as the entry point. The human does not classify the problem. **Precondition:** workspace intact, one debug session at a time.

The preparation script resolves the delivered repo path from `pipeline_state.json` (`delivered_repo_path`) and includes it in the triage agent's task prompt **(NEW IN 2.1)**. The agent never guesses or asks for the repo location.

**Gate 6.0 (debug permission reset).** The bug triage agent begins in read-only mode. After gathering information, the pipeline presents: **AUTHORIZE DEBUG** or **ABANDON DEBUG**. On authorize, `update_state.py` activates all debug write rules — including write access to the delivered repo path and the lessons learned document. On abandon, return to "Stage 5 complete."

#### 12.17.2 Triage Classification

The triage agent classifies:
- **Build/environment issue:** code doesn't run, fails at import, environment error.
- **Logic bug:** code runs but produces wrong results.

#### 12.17.3 Build/Environment Fix Path (Fast Path)

No regression test needed. Repair agent fixes directly. Narrow mandate: can modify environment files, package config, `__init__.py`, directory structure. Cannot modify implementation files. Up to 3 attempts. If fix requires implementation changes, returns `REPAIR_RECLASSIFY`.

#### 12.17.4 Logic Bug Path (Full Path) (CHANGED IN 2.1)

The logic bug path follows a seven-step workflow. Steps 1-2 involve human dialog and classification confirmation (Gate 6.2). Steps 3-4 are largely autonomous. Step 5 includes a human review gate (TEST CORRECT/TEST WRONG). Step 6 is autonomous. Step 7 requires explicit human permission for commit/push.

**Two-branch routing requirements for debug loop agents (NEW IN 2.1 — routing invariant, Bug 43 fix).** The following debug loop agent-to-gate transitions are governed by the two-branch routing invariant (Section 3.6):

- **Triage agent to Gate 6.2:** When `last_status.txt` contains `TRIAGE_COMPLETE: single_unit` or `TRIAGE_COMPLETE: cross_unit`, `route()` must emit a `human_gate` action for Gate 6.2 (`gate_6_2_debug_classification`), not re-invoke the triage agent. When `last_status.txt` contains `TRIAGE_COMPLETE: build_env`, `route()` must route directly to the build/environment repair agent via the fast path (Section 12.17.3), bypassing Gate 6.2.
- **Triage agent to Gate 6.4 (non-reproducible):** When `last_status.txt` contains `TRIAGE_NON_REPRODUCIBLE`, `route()` must emit a `human_gate` action for Gate 6.4 (`gate_6_4_non_reproducible`), not re-invoke the triage agent.
- **Repair agent outcome dispatch:** When `last_status.txt` contains `REPAIR_COMPLETE`, `route()` must route to the success path (reassembly and debug completion per Section 12.17.6), not re-invoke the repair agent. When `last_status.txt` contains `REPAIR_RECLASSIFY` or `REPAIR_FAILED` (with retries exhausted), `route()` must emit a `human_gate` action for Gate 6.3 (`gate_6_3_repair_exhausted`), not re-invoke the repair agent (see also Section 12.17.8).
- **Test agent (regression test mode) to Gate 6.1:** When `last_status.txt` contains `REGRESSION_TEST_COMPLETE`, `route()` must emit a `human_gate` action for Gate 6.1 (`gate_6_1_regression_test`), not re-invoke the test agent.

Each of these transitions must have an explicit `last_status.txt` check in `route()`. Without the check, the pipeline loops indefinitely re-invoking the agent after its work is already done. The universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`) verifies all of these transitions.

**Step 1 — Prompt human for directions.** Socratic triage dialog oriented toward reproducing the bug with concrete inputs/outputs/assertions. Real data access for diagnosis; regression test uses synthetic data. Triage output: affected unit(s), root cause hypothesis, regression test specification, classification (build_env, single_unit, or cross_unit). The `build_env` classification routes to the build/environment fast path (Section 12.17.3), bypassing Gate 6.2; `single_unit` and `cross_unit` classifications proceed to Gate 6.2 for human confirmation.

**Step 2 — Investigate the bug and propose classification.** The triage agent applies the three-hypothesis discipline (Section 10.11): implementation-level, blueprint-level, or spec-level. The agent reads workspace source, tests, blueprint contracts, and the delivered repo (via `delivered_repo_path`) to produce a structured diagnosis. The triage agent proposes a classification but does not act on it — the human confirms at Gate 6.2 before any fix is applied.

**Gate 6.2 (debug classification).** The pipeline presents the triage agent's diagnosis and proposed classification to the human. Gate response options: **FIX UNIT**, **FIX BLUEPRINT**, or **FIX SPEC**. The human may accept the triage agent's recommendation or override it. No fix is applied until the human confirms at this gate.

**Step 3 — Apply the confirmed fix.** After the human confirms the classification at Gate 6.2, the fix is applied in the workspace first, where the agent has unit structure, blueprint context, and pipeline machinery. The fix type follows the confirmed classification:

- **FIX UNIT (single-unit code fix):** Contract correct, implementation wrong for this case. The pipeline calls `rollback_to_unit(state, N)` where N is the lowest affected unit from the triage classification. This invalidates all verified units >= N (removes them from `verified_units`), deletes source and test files for units >= N, sets `stage: "3"`, `current_unit: N`, `sub_stage: None`, `fix_ladder_position: null`, `red_run_retries: 0`. The pipeline then rebuilds from unit N forward through all remaining units (test generation + implementation for each). Quality Gates A and B run normally during re-entry. The `debug_session` object tracks re-entry (phase transitions to `"stage3_reentry"`). Steps 4-7 follow.
- **FIX BLUEPRINT (cross-unit contract problem):** Blueprint problem. Targeted blueprint revision, ruthless forward restart. Regression test preserved. Steps 4-7 do not apply — the pipeline restarts from Stage 2 (complete pipeline re-entry).
- **FIX SPEC:** Spec-level gap. Targeted spec revision, then restart from Stage 2. Steps 4-7 do not apply — the pipeline restarts from Stage 1 revision (complete pipeline re-entry).

After the workspace fix passes all existing tests (unit, regression, and integration — distinct from the new regression test authored in Step 5), the pipeline performs a full Stage 5 reassembly to the delivered repo. This preserves the assembly mapping as a one-way function — workspace to repo, never the reverse.

**Step 4 — Evaluate whether spec or blueprint need revision (FIX UNIT path only).** After the fix is applied, the agent evaluates whether the root cause reveals a gap in the spec or blueprint. A fix that works may still indicate an incomplete spec (P7 pattern — the implementation faithfully followed an omission). If a document-level issue is identified, the agent flags it and initiates targeted revision per the three-hypothesis classification from Step 2.

**Step 5 — Write regression tests.** Test agent writes a failing regression test to `tests/regressions/test_bugNN_descriptive_suffix.py` (where NN is the unified bug catalog number and the suffix describes the bug scenario; see Section 6.8 for the naming convention). Must fail against the pre-fix implementation. Must pass against the post-fix implementation. Human reviews at Gate 6.1 (`gate_6_1_regression_test`): **TEST CORRECT** or **TEST WRONG**.

**Step 6 — Update lessons learned document.** The agent appends a new entry to the lessons learned document (Document 4) following the established catalog format: bug number, how caught, test file reference, description, root cause pattern classification (P1-P9 or new pattern with definition), and prevention rule. If the bug reveals a new pattern not covered by P1-P8, the agent defines the pattern and adds it to the pattern catalog. The agent also updates the regression test file mapping table.

**Step 7 — Commit and push (human permission required).** The agent prepares a commit with a detailed, fixed-format debug commit message (see Section 12.17.11) and presents it to the human for approval. Gate 6.5 (`gate_6_5_debug_commit`) response options: **COMMIT APPROVED** or **COMMIT REJECTED**. On approval, the agent commits and pushes. On rejection, the human may edit the commit message or abort.

#### 12.17.5 Regression Test Survival

`tests/regressions/` is protected — ruthless restart never touches it. Unit-level regressions run with affected unit's tests. Cross-unit regressions run with integration tests.

#### 12.17.6 Completion and Repo Reassembly

After successful fix: all unit tests pass, all regression tests pass, integration tests pass, full Stage 5 repo reassembly to `delivered_repo_path`, debug session recorded in history, lessons learned document updated. After `REPAIR_COMPLETE`, the routing script must re-enter Stage 5 with `sub_stage=None` to trigger git_repo_agent reassembly. The debug session remains active during reassembly. This ensures the workspace fix is propagated to the delivered repository through the canonical assembly path.

**Artifact synchronization invariant (NEW IN 2.1).** Every artifact that exists in both the workspace and the delivered repository must be kept in sync. When a fix modifies any workspace artifact that has a corresponding copy in the delivered repository, the delivered copy must be updated as part of the same fix. This applies regardless of whether the fix follows the formal debug loop (agent-driven with reassembly) or is applied directly by the main session. The dual-copy artifacts are:

- **Python source files:** workspace `src/unit_N/` and `scripts/` → delivered `svp/scripts/` (via assembly mapping)
- **Command files:** workspace `*_MD_CONTENT` constants in Unit 20 → delivered `svp/commands/*.md`
- **Skill files:** workspace `SKILL_MD_CONTENT` constant in Unit 21 → delivered `svp/skills/orchestration/SKILL.md`
- **Agent definitions:** workspace `*_AGENT_MD_CONTENT` constants → delivered `svp/agents/*.md`
- **Hook configurations:** workspace Unit 12 constants → delivered `svp/hooks/hooks.json`
- **Documentation:** workspace `specs/`, `blueprint/`, `references/` → delivered `docs/`, `docs/references/`

When full Stage 5 reassembly is not triggered (e.g., direct fixes outside the formal debug loop), the main session must manually propagate changes to all affected delivered copies. A fix that updates a workspace artifact without updating its delivered counterpart creates documentation drift — the same failure mode the pipeline is designed to prevent.

#### 12.17.7 Non-Reproducible Bugs

If triage cannot produce a failing test after iteration limit: revised hypothesis (retry triage), environmental mismatch (ask for more data characteristics), or genuinely non-reproducible (structured report). Gate 6.4 (`gate_6_4_non_reproducible`): **RETRY TRIAGE** or **ABANDON DEBUG**.

#### 12.17.8 Repair Agent Exhaustion

Gate 6.3: **RETRY REPAIR**, **RECLASSIFY BUG**, or **ABANDON DEBUG**. RECLASSIFY BUG resets the debug phase to triage and clears the existing classification, allowing the triage agent to re-investigate with a fresh hypothesis (Bug 69 fix). ABANDON DEBUG calls `abandon_debug_session` and returns to "Stage 5 complete."

#### 12.17.9 Debug Session Abandonment

`/svp:bug --abandon` cleans up and returns to "Stage 5 complete." Ledger renamed to `bug_triage_N_abandoned.jsonl`.

#### 12.17.10 Dual Write-Path During Debug (NEW IN 2.1)

During the debug loop, two write paths coexist: agent writes (through Claude Code's Write tool, gated by hooks) and pipeline subprocess writes (quality tools, assembly scripts, bypassing hooks). This is the same dual write-path that operates during the build (Section 10.12). The hook system authorizes agent writes to debug-permitted paths; subprocess writes from pipeline scripts operate independently. The blueprint author must not conflate these paths — a hook that blocks agent writes to the delivered repo does not block the reassembly script's subprocess writes, and vice versa.

#### 12.17.11 Debug Commit Message Format (NEW IN 2.1)

Debug commits use a fixed format regardless of the project's `vcs.commit_style` setting. Debug commits are pipeline infrastructure, not project development, and a consistent structure makes the regression history scannable across projects.

Format:

```
[SVP-DEBUG] Bug NNN: <one-line summary>

Affected units: <unit numbers and names>
Root cause: <P1-P8 or new pattern> — <brief description>
Classification: <single-unit | cross-unit | build_env>

Changes:
- <file>: <what changed and why>
- <file>: <what changed and why>

Regression test: tests/regressions/test_bugNN_descriptive_suffix.py
Spec/blueprint revised: <yes/no, with details if yes>
```

---

## 13. Human Commands (CHANGED IN 2.0, CHANGED IN 2.1)

All SVP commands use the plugin namespace `svp:`. Claude Code's built-in commands remain available alongside SVP commands. Commands are available at gates and between units, not during autonomous execution.

### 13.1 Command Group Classification

**Group A — Utility commands.** Invoke a dedicated `cmd_*.py` script directly. No subagent.

- `/svp:save` — invokes `cmd_save.py`
- `/svp:quit` — invokes `cmd_quit.py`
- `/svp:status` — invokes `cmd_status.py`
- `/svp:clean` — invokes `cmd_clean.py`

**Group B — Agent-driven workflow commands.** Invoke `prepare_task.py` to assemble a task prompt, then spawn a subagent. Each Group B command definition must include the **complete action cycle**: (1) run `prepare_task.py`, (2) spawn the agent, (3) write the agent's terminal status line to `.svp/last_status.txt`, (4) run `update_state.py` with the correct `--phase` flag, (5) re-run the routing script. The command definition provides the correct `--phase` value — the main session must not guess or construct it. **(CHANGED IN 2.1)**

- `/svp:help` — spawns help agent (`--phase help`)
- `/svp:hint` — spawns hint agent (`--phase hint`)
- `/svp:ref` — spawns reference indexing agent (`--phase reference_indexing`)
- `/svp:redo` — spawns redo agent (`--phase redo`)
- `/svp:bug` — spawns bug triage agent (`--phase bug_triage`)

**Prohibited scripts.** The following must never exist: `cmd_help.py`, `cmd_hint.py`, `cmd_ref.py`, `cmd_redo.py`, `cmd_bug.py`. Group B commands must not be implemented as dedicated scripts.

**`/svp:save`** — Flush pending state, verify file integrity, confirm to human. Auto-save runs after every significant transition; this is primarily a confirmation mechanism.

**`/svp:quit`** — Run save script, then exit. Save confirmation before exit.

**`/svp:help`** — Pause pipeline, launch help agent. See Section 14.

**`/svp:hint`** — Request diagnostic analysis. Two modes: **reactive** (during failure conditions — reads accumulated failures, identifies patterns) or **proactive** (during normal flow — human acts on intuition). Gate options: **CONTINUE** or **RESTART**. **Mode determination:** The human chooses by invoking `/svp:hint` (reactive mode — invoked when something fails or is confusing; the routing script detects that the pipeline is at a failure gate or fix ladder position and assembles the hint agent's task prompt with accumulated failure context). The pipeline may also invoke the hint agent proactively at defined diagnostic points (e.g., after repeated fix ladder failures or before diagnostic escalation). Reactive invocations use single-shot interaction (the hint agent reads accumulated failures and produces one-shot analysis). Proactive invocations during normal flow use ledger-based multi-turn (the human acts on intuition and may need multi-turn clarification). The routing script distinguishes the two modes by checking pipeline state: if the current sub-stage is a failure-related position (fix ladder, diagnostic escalation, quality gate retry), the hint agent is invoked in reactive mode with accumulated failure logs; otherwise, it is invoked in proactive mode with ledger support.

**`/svp:status`** (CHANGED IN 2.1) — Report pipeline state: current stage, sub-stage, verified units, alignment iterations, next expected action. Includes pass history and pipeline toolchain summary **(CHANGED IN 2.0)**, plus one-line profile summary and active quality gate status **(NEW IN 2.1)**:

```
Project: Spike Sorting Pipeline
Pipeline: python_conda_pytest
Quality: ruff + mypy (pipeline), ruff + none (delivery)    (NEW IN 2.1)
Delivery: pyenv, conventional commits, comprehensive README, Apache 2.0
Current: Stage 3, Unit 2 of 11 (pass 2)
Pass 1: Reached Unit 7, spec revision triggered
Pass 2: In progress, Unit 1 verified
```

**`/svp:ref`** — Add a reference. Available Stages 0-2 only. Handles document references (file copy + indexing) and repository references (GitHub MCP exploration + summary). If GitHub MCP not configured, offers to configure it.

**`/svp:redo`** (CHANGED IN 2.0) — Roll back to redo a previously completed step. The redo agent traces the relevant term through the document hierarchy and classifies:

- **`REDO_CLASSIFIED: spec`** — spec says the wrong thing. Targeted revision, restart from Stage 2.
- **`REDO_CLASSIFIED: blueprint`** — blueprint translated incorrectly. Restart from Stage 2.
- **`REDO_CLASSIFIED: gate`** — documents correct, human approved wrong thing. Unit-level rollback: invalidate from affected unit forward, reprocess.
- **`REDO_CLASSIFIED: profile_delivery`** (CHANGED IN 2.0) — delivery-only profile change. Focused dialog, no pipeline restart. Takes effect at Stage 5. The repo collision avoidance mechanism (Section 12.1) applies: if the previous delivered repo directory exists, it is renamed to a timestamped backup before the new repo is created.
- **`REDO_CLASSIFIED: profile_blueprint`** (CHANGED IN 2.0) — blueprint-influencing profile change. Focused dialog, then restart from Stage 2.

**Redo-triggered profile revision (CHANGED IN 2.0).** When redo produces a `profile_delivery` or `profile_blueprint` classification, the setup agent runs in targeted revision mode. The pipeline writes a redo sub-stage (`"redo_profile_delivery"` or `"redo_profile_blueprint"`) and captures a `redo_triggered_from` snapshot of the current pipeline position. Mini-Gate 0.3r (same vocabulary: **PROFILE APPROVED**, **PROFILE REJECTED**). On completion: `profile_delivery` restores the snapshot; `profile_blueprint` restarts from Stage 2.

**Two-branch routing requirement for redo profile sub-stages (NEW IN 2.1 — routing invariant, Bug 43 fix).** Both `redo_profile_delivery` and `redo_profile_blueprint` sub-stages are governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `PROFILE_COMPLETE`, `route()` must emit a `human_gate` action for Gate 0.3r (`gate_0_3r_profile_revision`), not re-invoke the setup agent. If `route()` unconditionally re-invokes the setup agent without checking `last_status.txt`, the pipeline loops indefinitely after the profile revision is already written. A regression test must verify both branches for both redo profile sub-stages.

**Redo and delivery collision (NEW IN 2.1).** All redo classifications that cause the pipeline to re-enter Stage 5 — `spec` (restart from Stage 2, eventually reaches Stage 5), `blueprint` (restart from Stage 2), `profile_delivery` (takes effect at Stage 5), and `profile_blueprint` (restart from Stage 2) — are subject to the repo collision avoidance mechanism in Section 12.1. When a redo is triggered from post-delivery (stage 5 complete or the debug loop), the previous delivered repository directory will exist. The Stage 5 preparation script renames it to a timestamped backup before invoking the git repo agent, ensuring no directory collision. The `delivered_repo_path` in `pipeline_state.json` is always updated to the canonical `projectname-repo/` path after re-delivery. Note: the collision avoidance rename happens at Stage 5 entry (in the Stage 5 preparation script), not at redo classification time. The redo classifications listed above are subject to collision avoidance because they eventually cause re-entry into Stage 5, not because the rename is triggered immediately upon classification.

**`/svp:bug`** — Post-delivery bug report or abandon. See Section 12.17.

**`/svp:clean`** — After Stage 5. Archive, delete, or keep workspace. The delivered repository is never touched.

---

## 14. The Help Agent

### 14.1 Availability

Available at any point during any stage via `/svp:help` or by asking a question the orchestration logic recognizes as a help request.

### 14.2 Behavior

- Stateless across sessions; maintains a conversation ledger within a single help session.
- Read-only: never modifies documents, code, tests, or pipeline state. Tool access restricted to Read, Grep, Glob, and web search. Reinforced by write authorization hooks.
- Selective context: receives project summary plus spec and blueprint as task prompt; retrieves specific files on demand.
- Pipeline pauses while active. Resumes with no state change on dismissal.
- Has web search access.
- Uses `claude-sonnet-4-6` by default.
- Output to main session: terminal status line only — `HELP_SESSION_COMPLETE: no hint` or `HELP_SESSION_COMPLETE: hint forwarded` followed by hint content.

### 14.3 Scope

The help agent answers any question: explaining code, error messages, technical concepts, SVP behavior, external libraries, Python syntax, domain-adjacent questions.

### 14.4 Gate-Invocation Mode and Hint Forwarding

When invoked at a decision gate, the help agent gains hint formulation capability. The human brings domain expertise; the help agent brings code-reading ability. Together they produce engineering-precise suggestions.

**Formulation workflow:**
1. Human discusses problem with help agent (read access to code, tests, blueprint, diagnostics).
2. When conversation produces an actionable observation, help agent offers to formulate it as a hint.
3. Human approves (or edits and approves).
4. Terminal status: `HELP_SESSION_COMPLETE: hint forwarded` followed by hint content.

**Forwarding mechanism.** Main session detects hint, stores it. Before injecting into the next agent's task prompt, a deterministic hint prompt assembler wraps it in a context-dependent prompt block adapted to agent type (test vs. implementation) and ladder position. No LLM involvement — deterministic templates with variable substitution.

The hint is logged as a `[HINT]` entry in the relevant ledger with full gate metadata. After forwarding, stored hint is cleared — injected into one invocation only. The `[HINT]` ledger entry persists.

**Receiving agent behavior.** Evaluates the hint alongside blueprint contract, diagnostic analysis, and its own judgment. If the hint contradicts the blueprint, returns `HINT_BLUEPRINT_CONFLICT: [details]`.

---

## 15. Interaction Patterns

### 15.1 Ledger-Based Multi-Turn

Used for open-ended conversations: Socratic dialog, blueprint dialog, help sessions, hint sessions, setup dialog, triage dialog.

A conversation ledger is an append-only JSONL file with role, content, and timestamp per entry. Each turn is a fresh invocation with the full ledger as task prompt.

**Agent response structure.** Two parts: a body (substantive content) and a tagged closing line (final line, exactly one marker):
- `[QUESTION]` — agent asks, expects answer.
- `[DECISION]` — agent records consensus.
- `[CONFIRMED]` — agent records domain fact.

Tagged lines must be self-contained. The body carries no markers. System-level `[HINT]` entries are written by the main session, preserved verbatim during compaction.

**Ledger locations:** `ledgers/setup_dialog.jsonl`, `ledgers/stakeholder_dialog.jsonl`, `ledgers/blueprint_dialog.jsonl`, `ledgers/spec_revision_N.jsonl`, `ledgers/help_session.jsonl` (cleared on dismissal), `ledgers/hint_session.jsonl` (cleared on dismissal), `ledgers/bug_triage_N.jsonl`.

### 15.2 Single-Shot

Used for task agents that produce output and are dismissed: test generation, implementation, coverage review, diagnostic analysis, blueprint checking, reviewing, integration test authoring, reference indexing, redo classification, git repo creation, hint analysis.

Agent receives context, produces output with terminal status line, terminates.

**Dual-mode note:** The hint agent uses single-shot when invoked reactively during failure conditions (reads accumulated failures, produces one-shot analysis), but uses ledger-based multi-turn when invoked proactively during normal flow (human acts on intuition, may need multi-turn clarification). See Section 21 agent summary for details.

### 15.3 Hint Injection at Decision Gates

Optional at every gate. Human invokes `/svp:help`, discusses with help agent, formulates hint. Main session stores hint and injects into next agent's task prompt via the hint prompt assembler. Always optional.

---

## 16. Session Lifecycle Management

### 16.1 Session Boundaries

Session boundaries fire at:
- Unit N verified → starting unit N+1.
- Construction → document revision.
- Document revision complete → stage restart.
- All stage transitions.

### 16.2 Restart Mechanism

1. Main session writes `.svp/restart_signal` with boundary reason.
2. Main session presents brief transition message and exits.
3. Launcher detects signal, deletes it, sets permissions, relaunches Claude Code.
4. New session reads CLAUDE.md, runs routing script, picks up from state file.

### 16.3 Post-Restart Context Summary

Every post-restart session begins with: project name, current stage/sub-stage, what just happened, what happens next, pass history summary if applicable.

### 16.4 Filesystem Permission Management

Between sessions: launcher sets workspace to read-only. On session start: restores write permissions. First layer of universal write authorization.

---

## 17. Routing Script Output Format

The routing script reads `pipeline_state.json` and outputs the exact next action as a structured key-value block.

### 17.1 Action Types

**Invoke a subagent:**
```
ACTION: invoke_agent
AGENT: test_agent
PREPARE: python scripts/prepare_task.py --unit 4 --agent test --project-root . --output .svp/task_prompt.md
TASK_PROMPT_FILE: .svp/task_prompt.md
POST: python scripts/update_state.py --unit 4 --phase test_generation --status-file .svp/last_status.txt
MESSAGE: Starting test generation for Unit 4: Spike Detection
REMINDER: [standard block]
```

**Run a bash command:**
```
ACTION: run_command
COMMAND: cd projectname && conda run -n projectname pytest tests/unit_4/ -v
POST: python scripts/update_state.py --unit 4 --phase red_run --status-file .svp/last_status.txt
MESSAGE: Running red validation for Unit 4: Spike Detection
REMINDER: [standard block]
```

**Present a decision gate:**
```
ACTION: human_gate
GATE: gate_3_1_test_validation
UNIT: 4
PREPARE: python scripts/prepare_task.py --unit 4 --gate gate_3_1_test_validation --project-root . --output .svp/gate_prompt.md
POST: python scripts/update_state.py --unit 4 --gate gate_3_1_test_validation --phase test_validation --status-file .svp/last_status.txt
PROMPT_FILE: .svp/gate_prompt.md
OPTIONS: TEST CORRECT, TEST WRONG
MESSAGE: A test failed. Please review the diagnostic analysis.
REMINDER: [standard block]
```

**Session boundary:**
```
ACTION: session_boundary
MESSAGE: Unit 4 verified. Preparing for next unit.
```

**Pipeline complete:**
```
ACTION: pipeline_complete
MESSAGE: Repository delivered successfully. Pipeline complete.
```

**Pipeline held:**
```
ACTION: pipeline_held
MESSAGE: Project context was insufficient. Please return when you have thought more about your requirements.
REMINDER: [standard block]
```

The `pipeline_held` action type is emitted when the pipeline cannot proceed and requires human re-engagement before continuing. Currently used only for the `PROJECT_CONTEXT_REJECTED` state (Section 18.1): when the setup agent determines the human cannot provide sufficient answers, `route()` emits `pipeline_held` rather than re-invoking the agent or presenting a gate. The main session displays the MESSAGE and awaits human re-engagement. The held state is cleared explicitly (e.g., via `/svp:redo` or by re-running the pipeline), which clears `last_status.txt` and allows normal routing to resume.

### 17.2 Field Definitions

- **ACTION** (required): `invoke_agent`, `run_command`, `human_gate`, `session_boundary`, `pipeline_complete`, `pipeline_held`.
- **AGENT** (invoke_agent only): agent identifier.
- **PREPARE** (optional): command to produce task/gate prompt file.
- **TASK_PROMPT_FILE** (invoke_agent only): path to prepared task prompt.
- **COMMAND** (run_command only): exact bash command. Must be fully resolved (Bug 35 fix — see below).
- **POST** (optional): state update command after action. Must be fully resolved (Bug 35 fix — see below).

**Routing output resolution invariant (Bug 35 fix).** All fields in the routing output action block that contain executable commands (COMMAND, PREPARE, POST) must be fully resolved — no placeholders (e.g., `{env_name}`, `{N}`) may appear. The routing script must resolve all placeholders using `derive_env_name(state.project_name)`, `state.current_unit`, and other state/profile values before emitting the action block. This applies uniformly to COMMAND, PREPARE, and POST fields.
- **GATE** (human_gate only): gate identifier.
- **UNIT** (human_gate, optional): unit number.
- **PROMPT_FILE** (human_gate only): path to gate prompt.
- **OPTIONS** (human_gate only): comma-separated valid responses.
- **MESSAGE** (required): human-readable announcement.
- **REMINDER** (required for invoke_agent, run_command, human_gate): behavioral reinforcement block.

---

## 18. Agent Output Interface (CHANGED IN 2.0, CHANGED IN 2.1)

### 18.1 Terminal Status Lines

Every subagent produces a terminal status line as its final output. Written to `.svp/last_status.txt`. Dispatched by POST script using **prefix matching** (agents may append trailing context).

Complete vocabulary:

**Setup Agent:** `PROJECT_CONTEXT_COMPLETE`, `PROJECT_CONTEXT_REJECTED`, `PROFILE_COMPLETE` (CHANGED IN 2.0). The setup agent emits `PROJECT_CONTEXT_REJECTED` when, after multiple attempts, the human cannot provide substantive answers and the agent determines the project context is insufficient to proceed (Section 3.11). On receiving `PROJECT_CONTEXT_REJECTED`, the routing script presents a message to the human explaining that the project context was insufficient and suggesting they return when they have thought more about their requirements, then holds the pipeline at `project_context` sub-stage with `last_status.txt` retained as `PROJECT_CONTEXT_REJECTED`. The routing script must recognize `PROJECT_CONTEXT_REJECTED` as a held state: when `last_status.txt` contains this value, `route()` emits a `pipeline_held` action (displaying the "insufficient context" message and awaiting human re-engagement) rather than re-invoking the setup agent. The human resumes by clearing the held state explicitly (e.g., via `/svp:redo` or by re-running the pipeline), which clears `last_status.txt` and allows the two-branch invariant to route to the setup agent. This status triggers a hold, not a gate presentation or agent re-invocation, so it is not governed by the two-branch invariant (Section 3.6).

**Stakeholder Dialog Agent:** `SPEC_DRAFT_COMPLETE`, `SPEC_REVISION_COMPLETE`.

**Stakeholder Spec Reviewer:** `REVIEW_COMPLETE`.

**Blueprint Author Agent:** `BLUEPRINT_DRAFT_COMPLETE`, `BLUEPRINT_REVISION_COMPLETE`.

**Blueprint Checker Agent:** `ALIGNMENT_CONFIRMED`, `ALIGNMENT_FAILED: spec`, `ALIGNMENT_FAILED: blueprint`.

**Blueprint Reviewer Agent:** `REVIEW_COMPLETE`.

**`REVIEW_COMPLETE` disambiguation.** Both the Stakeholder Spec Reviewer and Blueprint Reviewer Agent produce the same `REVIEW_COMPLETE` status line. The routing script disambiguates by reading the current stage number from `pipeline_state.json`: in Stage 1, `REVIEW_COMPLETE` routes to Gate 1.2 (`gate_1_2_spec_post_review`); in Stage 2, `REVIEW_COMPLETE` routes to Gate 2.2 (`gate_2_2_blueprint_post_review`). See also Section 7.4 (reviewer status routing) and Section 22.4 (Stage 1 sub-stage note).

**Test Agent:** `TEST_GENERATION_COMPLETE`, `REGRESSION_TEST_COMPLETE` (debug loop regression test mode — Section 12.17.4 Step 5).

**Implementation Agent:** `IMPLEMENTATION_COMPLETE`.

**Coverage Review Agent:** `COVERAGE_COMPLETE: no gaps`, `COVERAGE_COMPLETE: tests added`.

**Diagnostic Agent:** `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, `DIAGNOSIS_COMPLETE: spec`.

**Integration Test Author:** `INTEGRATION_TESTS_COMPLETE`.

**Git Repo Agent:** `REPO_ASSEMBLY_COMPLETE`.

**Help Agent:** `HELP_SESSION_COMPLETE: no hint`, `HELP_SESSION_COMPLETE: hint forwarded`.

**Hint Agent:** `HINT_ANALYSIS_COMPLETE`.

**Redo Agent:** `REDO_CLASSIFIED: spec`, `REDO_CLASSIFIED: blueprint`, `REDO_CLASSIFIED: gate`, `REDO_CLASSIFIED: profile_delivery` (CHANGED IN 2.0), `REDO_CLASSIFIED: profile_blueprint` (CHANGED IN 2.0).

**Bug Triage Agent:** `TRIAGE_COMPLETE: build_env`, `TRIAGE_COMPLETE: single_unit`, `TRIAGE_COMPLETE: cross_unit`, `TRIAGE_NEEDS_REFINEMENT`, `TRIAGE_NON_REPRODUCIBLE`.

**`TRIAGE_NEEDS_REFINEMENT` routing (NEW IN 2.1). `triage_refinement_count` is an `int` field (default 0) on `DebugSession`.** When the triage agent emits `TRIAGE_NEEDS_REFINEMENT`, the routing script re-invokes the triage agent with refinement context appended to its task prompt (the previous triage output and the reason refinement was needed). This is a same-agent re-invocation, not a gate presentation -- the human is not involved at this point. The re-invocation is bounded: a `triage_refinement_count` counter in `debug_session` tracks attempts (default limit 2). If the limit is reached, the routing script presents Gate 6.4 (`gate_6_4_non_reproducible`) with an explanation that triage could not converge. Because this status triggers re-invocation rather than gate presentation, it is not governed by the two-branch invariant (Section 3.6).

**Repair Agent:** `REPAIR_COMPLETE`, `REPAIR_FAILED`, `REPAIR_RECLASSIFY`.

**`REPAIR_FAILED` routing (NEW IN 2.1). `repair_retry_count` is an `int` field (default 0) on `DebugSession`.** When the repair agent emits `REPAIR_FAILED`, the routing script increments a `repair_retry_count` counter in `debug_session` (default limit 3). If retries remain, the routing script re-invokes the repair agent with the previous failure output appended to its task prompt. If the retry limit is exhausted, the routing script presents Gate 6.3 (`gate_6_3_repair_exhausted`) for the human to decide: **RETRY REPAIR**, **RECLASSIFY BUG**, or **ABANDON DEBUG**. The re-invocation branch (retries remaining) is not governed by the two-branch invariant because it does not present a gate -- it is a same-agent retry loop. The exhaustion branch (present Gate 6.3) is already covered by the two-branch invariant entry for the repair agent (Section 3.6), since `REPAIR_FAILED` with exhausted retries results in the same Gate 6.3 presentation as `REPAIR_COMPLETE` and `REPAIR_RECLASSIFY`.

**Reference Indexing Agent:** `INDEXING_COMPLETE`.

**Cross-agent (hint conflict):** `HINT_BLUEPRINT_CONFLICT: [details]`.

### 18.2 Dual-Format Output

Agents whose output determines routing (diagnostic, blueprint checker, redo) produce: `[PROSE]` section for the human, then `[STRUCTURED]` section with key-value data for routing.

### 18.3 Command Result Status Lines

Written after `run_command` actions:

- `TESTS_PASSED: N passed` — all tests passed.
- `TESTS_FAILED: N passed, M failed` — some tests failed.
- `TESTS_ERROR: [error summary]` — execution error preventing test collection. Collection errors are narrowly defined: `ERROR collecting`, `ImportError`, `ModuleNotFoundError`, `SyntaxError` during collection. Fixture setup errors (`NotImplementedError` from stubs) are `TESTS_FAILED`, not `TESTS_ERROR`.

**TESTS_ERROR dispatch rules (NEW IN 2.1 -- Bug 70 fix):** `TESTS_ERROR` must never return state unchanged. Dispatch behavior by sub_stage:
  - **Red run:** Increment `red_run_retries`. If under limit (default 3), set `sub_stage` to `test_generation` (regenerate tests). If at limit, set `sub_stage` to `gate_3_1` (present Gate 3.1 for human decision).
  - **Green run:** Engage the fix ladder, same as `TESTS_FAILED` -- the collection error indicates an implementation problem (import/syntax errors in generated code).
  - **Stage 4:** Increment `red_run_retries` and present `gate_4_1` (under limit) or `gate_4_2` (at limit), same as `TESTS_FAILED`.
- `COMMAND_SUCCEEDED` — non-test command exit code 0.
- `COMMAND_FAILED: [exit code]` — non-test command nonzero exit.

### 18.4 Gate Status Strings (CHANGED IN 2.0)

Every gate response is written to `.svp/last_status.txt` as the exact string the human typed — no translation.

| Gate | ID | Valid Status Strings |
|---|---|---|
| 0.1 | gate_0_1_hook_activation | HOOKS ACTIVATED, HOOKS FAILED |
| 0.2 | gate_0_2_context_approval | CONTEXT APPROVED, CONTEXT REJECTED, CONTEXT NOT READY |
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

**Invariant:** OPTIONS field must list exactly these strings. No other strings are valid. The human-typed gate status strings (with spaces) are distinct from system-generated command status lines (with underscores and payloads).

---

## 19. Universal Write Authorization (CHANGED IN 2.0, CHANGED IN 2.1)

### 19.1 Layer 1 — Filesystem Permissions

Between sessions: workspace read-only (`chmod -R a-w`). On session start: write permissions restored. Delivered repository is unprotected.

### 19.2 Layer 2 — Hook-Based Write Authorization

`PreToolUse` hooks validate every write against current pipeline state.

**Two-tier path authorization:**
- **Infrastructure paths** (`.svp/`, `pipeline_state.json`, `ledgers/`, `logs/`, `.svp/triage_result.json`): always writable.
- **Project artifact paths** (`src/`, `tests/`, `specs/`, `blueprint/`, `references/`, `projectname-repo/`): state-gated. Writable only when authorized by the current pipeline state.

**Profile and toolchain paths (CHANGED IN 2.0, CHANGED IN 2.1):**
- `project_profile.json`: writable during Stage 0 `project_profile` sub-stage and during active redo-triggered profile revision sub-stages. Read-only otherwise.
- `toolchain.json`: permanently read-only after creation. No agent, session, or command may modify it.
- `ruff.toml`: permanently read-only after creation **(NEW IN 2.1)**.

**Debug session write rules.** Activated only after AUTHORIZE DEBUG at Gate 6.0:
- `tests/regressions/`: always writable during authorized debug session.
- Build/env fix: repair agent can write to environment files, package config, `__init__.py`. Cannot write to implementation files.
- Single-unit fix: `src/unit_N/` and `tests/unit_N/` for affected unit(s) only.
- `.svp/triage_scratch/`: writable during triage.
- Delivered repo path (`delivered_repo_path` from `pipeline_state.json`): writable during authorized debug session for reassembly **(NEW IN 2.1)**.
- Lessons learned document (`references/svp_2_1_lessons_learned.md`): writable during authorized debug session for regression cataloging **(NEW IN 2.1)**.

**Hook path resolution.** Project-level `hooks.json` must use `.claude/scripts/` paths (not bare `scripts/`). The launcher rewrites paths during copy.

**Hook configuration schema (NEW IN 2.1 — Bug 17 fix).** The plugin's `hooks.json` must conform to Claude Code's hook configuration schema. Each `PreToolUse` entry is an object with a `matcher` string and a `hooks` array containing handler objects. Each handler has `type: "command"` and a `command` string. The correct structure:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/scripts/write_authorization.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/scripts/non_svp_protection.sh"
          }
        ]
      }
    ]
  }
}
```

The following are schema violations (Bug 17 root causes): `type: "bash"` (must be `"command"`), `script` field (must be `command`), handler fields placed directly on the matcher object (must be nested inside the `hooks` array). A regression test validates the schema and confirms the plugin loads successfully.

The complete `hooks.json` including both `PreToolUse` and `PostToolUse` entries:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/scripts/write_authorization.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/scripts/non_svp_protection.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/scripts/stub_sentinel_check.sh"
          }
        ]
      }
    ]
  }
}
```

**PostToolUse stub sentinel hook (NEW IN 2.1).** A `PostToolUse` command hook matches Write tool calls to Python source files under `src/unit_N/` paths. The handler is a shell script that greps the written file content for `__SVP_STUB__`. If found, the hook exits with code 2 and emits: "Write blocked: stub sentinel detected in implementation file {path}. Re-read the blueprint Tier 2 signatures and write the implementation, not the stub." This provides a second enforcement point at write time, before structural validation.

This hook fires on `PostToolUse` (not `PreToolUse`) because it validates the content that was written, not the intent to write. Exit code 2 on `PostToolUse` causes Claude Code to surface the error to the main session. **Recovery behavior:** After PostToolUse exit code 2, Claude Code surfaces the error to the main session. The main session treats this as a quality signal -- the agent's current action cycle continues (the implementation agent is NOT re-invoked by the hook), but the error message is logged. The normal pipeline flow (quality gates, fix ladder) handles any content issues: if a stub was written instead of an implementation, the green run will fail, triggering the fix ladder. The PostToolUse hook provides an early warning, not a pipeline control mechanism. **Platform dependency note:** Exit code semantics (exit code 2 for hard block) are a Claude Code platform convention. If Claude Code's exit code handling changes in a future version, the hook scripts must be updated accordingly.

### 19.3 Non-SVP Session Protection

`PreToolUse` hook on the `bash` tool blocks all bash tool use in non-SVP sessions. A `README_SVP.txt` explains the protection.

---

## 20. Autonomous Execution Protocol

### 20.1 Announcement

Before each autonomous sequence: "Starting test generation for Unit 4: Spike Detection. Please wait."

### 20.2 Deferral of Human Input

CLAUDE.md instructs deferral during autonomous execution. If interrupted: "I'm currently running the red validation. I'll address your question when this sequence completes." Behavioral expectation with soft enforcement.

### 20.3 Command Availability

Commands available at gates and between units, not during autonomous execution.

---

## 21. Agent Summary (CHANGED IN 2.0, CHANGED IN 2.1)

| Agent | Stage | Interaction | Task Prompt Receives | Default Model |
|---|---|---|---|---|
| Setup Agent | 0 | Ledger multi-turn | Environment state, ledger. Expanded: profile dialog, targeted revision mode (CHANGED IN 2.0) | `claude-sonnet-4-6` |
| Stakeholder Dialog Agent | 1 (+ revision) | Ledger multi-turn | Ledger, reference summaries, project context (+ critique in revision) | `claude-opus-4-6` |
| Stakeholder Spec Reviewer | 1 | Single-shot | Spec, project context, reference summaries (no ledger) | `claude-opus-4-6` |
| Reference Indexing Agent | 1, 2+ | Single-shot | Full document or repo (via GitHub MCP) | `claude-sonnet-4-6` |
| Blueprint Author Agent | 2 | Ledger multi-turn | Spec, checker feedback, references, ledger, profile (readme, vcs, delivery, quality sections) (CHANGED IN 2.0, CHANGED IN 2.1) | `claude-opus-4-6` |
| Blueprint Checker Agent | 2 | Single-shot | Spec (with notes) + blueprint + profile (full preference validation incl. quality) (CHANGED IN 2.0, CHANGED IN 2.1) | `claude-opus-4-6` |
| Blueprint Reviewer Agent | 2 | Single-shot | Blueprint, spec, project context, references (no ledger) | `claude-opus-4-6` |
| Test Agent | 3 | Single-shot | Unit definition + upstream contracts. Receives `testing.readable_test_names` (CHANGED IN 2.0). Told quality tools will auto-format output (NEW IN 2.1) | `claude-opus-4-6` |
| Implementation Agent | 3, 4 | Single-shot | Unit definition + upstream contracts (+ diagnostic + hint in ladder). Told quality tools will auto-format and type-check output (NEW IN 2.1) | `claude-opus-4-6` |
| Coverage Review Agent | 3 | Single-shot | Blueprint unit definition + passing tests | `claude-opus-4-6` |
| Diagnostic Agent | 3, 4 | Single-shot | Spec + unit blueprint + failing tests + errors | `claude-opus-4-6` |
| Integration Test Author | 4 | Single-shot | Spec + all contract signatures (reads source on demand) | `claude-opus-4-6` |
| Git Repo Agent | 5 | Single-shot | All verified artifacts + references + profile (full) (CHANGED IN 2.0) | `claude-sonnet-4-6` |
| Help Agent | Any | Ledger multi-turn | Project summary + spec + blueprint (+ gate flag) | `claude-sonnet-4-6` |
| Hint Agent | Any | Single-shot / Ledger | Logs, documents, human concern. **Dual interaction pattern:** uses single-shot when invoked reactively during failure conditions (reads accumulated failures, produces one-shot analysis); uses ledger (`ledgers/hint_session.jsonl`) when invoked proactively during normal flow (human acts on intuition, may need multi-turn clarification). The ledger is cleared on dismissal. | `claude-opus-4-6` |
| Redo Agent | 2, 3, 4 | Single-shot | State summary, error description, unit definition (reads on demand). New classifications: profile_delivery, profile_blueprint (CHANGED IN 2.0) | `claude-opus-4-6` |
| Bug Triage Agent | Debug | Ledger multi-turn | Spec + blueprint + source + tests + ledger + real data access | `claude-opus-4-6` |
| Repair Agent | Debug | Single-shot | Error diagnosis + environment state | `claude-sonnet-4-6` |

Model identifiers are configured in `svp_config.json` and can be changed at any time. Correctness-critical roles use Opus; support roles use Sonnet.

---

## 22. Configuration (CHANGED IN 2.0, CHANGED IN 2.1)

### 22.1 Configuration File

`svp_config.json` in the project workspace root. Contains:

- `iteration_limit`: maximum attempts for bounded retries. Default: 3. Does not govern fix ladder shapes.
- `models.test_agent`: Default: `"claude-opus-4-6"`.
- `models.implementation_agent`: Default: `"claude-opus-4-6"`.
- `models.help_agent`: Default: `"claude-sonnet-4-6"`.
- `models.default`: Default: `"claude-opus-4-6"`.
- `context_budget_override`: optional manual override in tokens. Default: null.
- `context_budget_threshold`: percentage reserved for fixed context. Default: 65.
- `compaction_character_threshold`: minimum characters for self-contained tagged lines. Default: 200.
- `auto_save`: Default: true.
- `skip_permissions`: whether to pass `--dangerously-skip-permissions`. Default: true. Hook-based authorization remains active regardless.

Human can edit at any time. Changes take effect on next invocation.

### 22.2 Project Profile File (CHANGED IN 2.0, CHANGED IN 2.1)

Produced during Stage 0. Schema in Section 6.4. Immutable after Gate 0.3. Changes via `/svp:redo`.

### 22.3 Toolchain File (CHANGED IN 2.0, CHANGED IN 2.1)

Copied from plugin at project creation. Schema in Section 6.5. Permanently read-only.

### 22.4 Pipeline State File (CHANGED IN 2.0, CHANGED IN 2.1)

`pipeline_state.json`. Tracks: current stage (0-5 plus pre-Stage-3), sub-stage, blueprint alignment iteration count, fix ladder position, red run retries, `total_units`, verified units with timestamps, pass history, log references, `debug_session` (object or null with `authorized` flag), `debug_history`, `redo_triggered_from` (snapshot dict or null) (CHANGED IN 2.0), `delivered_repo_path` (string, set at Stage 5 completion) **(NEW IN 2.1)**.

Stage 0 sub-stages: `"hook_activation"`, `"project_context"`, `"project_profile"` (CHANGED IN 2.0).

Stage 1 sub-stages (NEW IN 2.1): `None` (stakeholder dialog in progress or not yet started). Stage 1 does not use named sub-stages — the routing script uses `last_status.txt` to distinguish "dialog in progress" from "draft complete, present gate" per the two-branch routing invariant (Section 3.6). The sub-stage remains `None` throughout; the two-branch check on `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` provides the routing branch. **Implementation note:** Because Stage 1 has no named sub-stage, the two-branch check is keyed on `stage: "1"` alone. Any generic implementation of the two-branch invariant that dispatches solely by sub-stage name must handle Stage 1 as a special case (dispatch by stage number when `sub_stage` is `None` and the stage uses the two-branch pattern). **Reviewer status routing:** `route()` must also handle `REVIEW_COMPLETE` (from the spec reviewer) by routing to Gate 1.2 (`gate_1_2_spec_post_review`), not Gate 1.1 — distinguishing it from the dialog agent's `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` which route to Gate 1.1. The same pattern applies in Stage 2 for the blueprint reviewer's `REVIEW_COMPLETE` routing to Gate 2.2 (see Section 8.2).

Stage 2 sub-stages (NEW IN 2.1 — Bug 23 fix): `"blueprint_dialog"`, `"alignment_check"`.

Pre-Stage-3 sub-stages: `None` (single deterministic step — no named sub-stages). Infrastructure setup runs as one `run_command` action.

Stage 3 sub-stages: `None` (initial entry — `route()` treats `None` identically to `"stub_generation"` by mapping both to the same code path), `"stub_generation"` (Bug 36 fix), `"test_generation"`, `"quality_gate_a"`, `"quality_gate_a_retry"`, `"red_run"`, `"implementation"`, `"quality_gate_b"`, `"quality_gate_b_retry"`, `"green_run"`, `"coverage_review"`, `"unit_completion"`. The routing script must emit a distinct action for each sub-stage (Bug 25 fix — NEW IN 2.1, updated for Bug 36).

Quality gate sub-stages (subset of Stage 3 sub-stages, NEW IN 2.1): `"quality_gate_a"`, `"quality_gate_b"`, `"quality_gate_a_retry"`, `"quality_gate_b_retry"`.

Stage 4 sub-stages (NEW IN 2.1): `None` (initial entry, invokes integration test author agent). The two-branch routing invariant applies: when `last_status.txt` contains `INTEGRATION_TESTS_COMPLETE`, `route()` emits a `run_command` action for the integration test suite (not re-invocation of the agent). After the `run_command` completes, the routing script reads the test result status and performs three-state dispatch: (1) if tests passed (`TESTS_PASSED`), advance to Stage 5; (2) if tests failed (`TESTS_FAILED`), present the diagnostic gate (Section 11.4, Gate 4.1); (3) if the assembly fix ladder is exhausted (retries >= 3), present Gate 4.2.

Stage 5 sub-stages (NEW IN 2.1 — Bug 26 fix): `None` (initial entry, invokes git_repo_agent), `"repo_test"`, `"compliance_scan"`, `"repo_complete"`. Progression: `None` → git repo agent assembles repo (structural validation including Gate C runs within bounded fix cycle, Section 12.4) → on `REPO_ASSEMBLY_COMPLETE`, two-branch check presents Gate 5.1 → `"repo_test"` (human tests in delivered repo) → on TESTS PASSED → `"compliance_scan"` (deterministic `run_command`; on pass → `"repo_complete"`; on fail → re-enter bounded fix cycle, Section 12.4). The routing script must have an explicit branch for each sub-stage; Bug 26 was caused by Stage 5 routing having only debug-session and pipeline-complete paths with no repo assembly sub-stage routing.

Redo-triggered profile revision sub-stages (CHANGED IN 2.0, CHANGED IN 2.1): `"redo_profile_delivery"`, `"redo_profile_blueprint"`. Both sub-stages are governed by the two-branch routing invariant (Section 3.6): when `last_status.txt` contains `PROFILE_COMPLETE`, `route()` must emit a `human_gate` action for Gate 0.3r (`gate_0_3r_profile_revision`), not re-invoke the setup agent (Bug 43 fix).

Updated by deterministic scripts after every significant transition. The complete schema is a blueprint concern.

### 22.5 Resume Behavior (CHANGED IN 2.0)

On resume: routing script reads state file, main session presents context summary including project name, stage, sub-stage, verified units, pass history, pipeline toolchain, and profile summary.

---

## 23. Document Version Tracking (CHANGED IN 2.1)

Every time a document is revised:

1. Current version copied to history: `stakeholder_spec_v1.md`, `blueprint_prose_v1.md`, `blueprint_contracts_v1.md`, etc.
2. Diff summary saved alongside: what changed, why, what stage triggered it, timestamp.
3. Current working version remains `stakeholder_spec.md` / `blueprint_prose.md` / `blueprint_contracts.md`.

Each review cycle resulting in a revision increments the version number. History is included in the delivered repository at `docs/history/`.

**Caller.** The routing script's `dispatch_gate_response` function calls `version_document()` (from the state transition engine) at every REVISE trigger point before the revision occurs:

- Gate 1.1 / 1.2 REVISE: versions `stakeholder_spec.md`.
- Gate 2.1 / 2.2 REVISE: versions `blueprint_prose.md` and `blueprint_contracts.md` as an atomic pair.
- Gate 2.3 REVISE SPEC: versions `stakeholder_spec.md`.
- Gate 3.2 / 4.1 / 4.2 / 5.2 / 6.2 FIX BLUEPRINT: versions both blueprint files.
- Gate 3.2 / 4.1 / 4.2 / 5.2 / 5.3 / 6.2 FIX SPEC: versions `stakeholder_spec.md`.

---

## 24. Failure Modes and Recovery (CHANGED IN 2.1)

### 24.1 Implementation Failure
Tests fail, test confirmed correct. Fix ladder: fresh agent → diagnostic escalation → human decides.

### 24.2 Blueprint Failure
Discovered at any stage. Restart from Stage 2.

### 24.3 Spec Failure
Targeted spec revision, then restart from Stage 2. Full spec restart if pervasive.

### 24.4 Alignment Non-Convergence
Iteration limit exceeded. Diagnostic hint to human. Options: revise spec, restart spec, retry blueprint.

### 24.5 Session Interruption
Launcher resumes from saved state. At most one in-progress subagent call lost.

### 24.6 Token or Rate Limit Exhaustion
Save state, inform human, exit cleanly. Resume on next launch.

### 24.7 Non-SVP Session Modification
Hooks prevent modification. README_SVP.txt explains.

### 24.8 Human Gate Error
`/svp:redo` traces error, classifies, rolls back or restarts.

### 24.9 Ledger Overflow
Warning at 80%, compaction required at 90%.

### 24.10 Repository Assembly Failure
Bounded fix cycle. Up to 3 attempts. Gate 5.2 on exhaustion.

### 24.11 Conda Environment Guardrail Violation
All invocations must use `conda run -n {env_name}`. Environment name derived deterministically.

### 24.12 Repository Output Path Collision
Output repository at `{project_root.parent}/{project_name}-repo`. If exists, rename to `{project_name}-repo.bak.YYYYMMDD-HHMMSS` before creating new repo (see Section 12.1).

### 24.13 Blueprint Tier 2 Heading Format Error
The canonical heading string is `### Tier 2 — Signatures` (em-dash, not hyphen). This is the authoritative form; Section 8.1's reference to "Tier 2 — Machine-readable signatures" is a descriptive label for the tier's content, not the heading string. The blueprint extractor must use prefix matching (`### Tier 2`) to locate the heading, accommodating minor suffix variations while requiring the em-dash separator.

### 24.14 DAG Violation (Forward Dependency) (NEW IN 2.1)

A unit's dependency list references a unit with a higher number (forward edge) or creates a cycle.

**Detection:** Three independent checkpoints: blueprint checker (Stage 2), infrastructure DAG validation (Pre-Stage-3), stub generator forward-reference guard (Stage 3). Any one catching the violation is sufficient.

**Recovery:** This is always a blueprint-level problem. The pipeline returns to Stage 2. The blueprint author must restructure units to eliminate forward edges. If the forward dependency reflects a genuine circular relationship in the domain logic, the blueprint author must merge the circularly dependent components into a single unit or decompose differently.

### 24.14a Stage 3 Error-Path Dispatch Failure (NEW IN 2.1 — Bug 65)

A Stage 3 dispatch function returns state unchanged for a status line that requires a state transition. The pipeline loops indefinitely re-running the same command or re-invoking the same agent.

**Root cause:** The blueprint Tier 3 contracts covered only happy-path transitions. Error-path dispatch (TESTS_PASSED at red_run, TESTS_FAILED at green_run, DIAGNOSIS_COMPLETE at diagnostic) was described in spec prose (Sections 10.4, 10.9, 10.10, 10.11) but never appeared as enumerable contracts in the blueprint. The implementation agent correctly implemented the contracted paths and produced no-op stubs for the uncontracted ones.

**Detection:** The extended dispatch table (Section 3.6) enumerates every (phase, sub_stage, status) combination. A regression test (`test_bug65_stage3_error_handling.py`) verifies that each combination produces a distinct state transition.

**Recovery:** This is a compound P7+P9+P1 instance. The fix adds concrete dispatch contracts for every error path and wires all fix ladder, diagnostic escalation, Gate 3.1/3.2, and stub_generation transitions.

### 24.15 Quality Gate Failure (NEW IN 2.1)

Quality gate finds residuals that auto-fix cannot resolve and the agent re-pass does not fix.

**Recovery:** The gate fails and enters the existing fix ladder (test side for Gate A, implementation side for Gate B). The fix ladder operates normally — fresh agent attempts, diagnostic escalation, document revision if needed. Quality gates run again after the ladder produces new code. This is not a new failure mode — it is an existing failure mode (test generation failure or implementation failure) with a new trigger (quality residuals instead of test failures).

### 24.16 Sub-Stage Routing Fails to Present Gate After Agent Completion (NEW IN 2.1 — Bug 21, CHANGED IN 2.1 — Bugs 41, 43)

The routing script returns an agent invocation for a sub-stage that has already completed, instead of presenting the corresponding gate. The pipeline loops indefinitely re-invoking the agent.

**Root cause:** The `route()` function has a single code path for the sub-stage that always emits `invoke_agent`, with no conditional branch checking whether the agent has already completed. The `update_state` function intentionally keeps the sub-stage unchanged after agent completion so that the next `route()` call presents the gate — but `route()` never checks `last_status.txt` to distinguish "agent not yet done" from "agent done, present gate."

**Affected sub-stages:** Every sub-stage where an agent completion should trigger a gate presentation. The complete list is maintained in the two-branch routing invariant (Section 3.6). The originally discovered instances were `project_context` (Gate 0.2) and `project_profile` (Gate 0.3). The pattern was subsequently identified as affecting all agent-to-gate transitions across the pipeline, including Stage 1 (`stakeholder_spec_authoring` (sub_stage=None, descriptive label) to Gate 1.1), Stage 2 (`blueprint_dialog` to Gate 2.1, `alignment_check` to alignment outcome gate), Stage 4 (integration test author to test execution), Stage 5 (git repo agent to Gate 5.1), and the post-delivery debug loop (triage and repair agents to their corresponding gates). Stage 1 was missed in the prior build because the fix was applied per-stage rather than as an invariant.

**Detection:** The routing script's two-branch check on `last_status.txt` prevents the loop. Regression tests must verify that `route()` returns a `human_gate` action (not `invoke_agent`) when `last_status.txt` contains the agent's terminal status for **every** affected sub-stage — not just the originally discovered ones. A regression test that covers only Stage 0 sub-stages is insufficient. The universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`, Bug 43) is the definitive structural test for this invariant — it verifies all entries in the Section 3.6 exhaustive list in a single test.

**Recovery:** This is a routing-level implementation bug (pattern P1 — cross-unit contract drift between the routing script and the state update script). The state update script and the routing script must agree on the two-phase sub-stage protocol: the state update script holds the sub-stage steady; the routing script reads `last_status.txt` to decide which action to emit. This is a generalization of Bug 18. The fix is now specified as a structural invariant (Section 3.6) rather than a per-stage patch, ensuring it cannot be missed when new agent-to-gate sub-stages are added. Bug 43 demonstrated that even after the invariant was specified, piecemeal application (fixing only discovered stages) left other stages unprotected — hence the universal compliance requirement (Section 3.6) mandating single-pass application with a comprehensive structural test.

### 24.17 Pipeline Artifact Filename Mismatch (NEW IN 2.1 — Bug 22)

A component that writes a pipeline artifact uses a different filename than the component that reads it. The pipeline crashes with `FileNotFoundError` at the boundary between the two components.

**Root cause:** The filename is hardcoded independently in both components with no shared constant or single source of truth. The setup agent writes `specs/stakeholder.md`; the preparation script reads `specs/stakeholder_spec.md`. Neither references a shared definition.

**Affected artifacts:** The stakeholder spec filename is the discovered instance, but the pattern applies to any pipeline artifact referenced by path across multiple components (blueprint, project context, ledger files, marker files).

**Detection:** A regression test verifies that the filename constant used by the file writer matches the filename constant used by the file reader. AST-based structural tests can verify that both components import the same constant rather than hardcoding independent strings.

**Recovery:** This is a P1 (cross-unit contract drift) instance. The fix is to define the canonical filename in one shared location and have all producers and consumers reference that definition. The canonical stakeholder spec filename is `stakeholder_spec.md` (see Section 7.5).

### 24.18 Alignment Check Skipped in Stage Progression (NEW IN 2.1 — Bug 23)

After Gate 2.1 blueprint approval, the pipeline advances directly to Pre-Stage-3 without invoking the blueprint checker. The alignment check never runs.

**Root cause:** The stage transition function (`advance_stage`) for Stage 2 transitions directly to `pre_stage_3` with no intermediate sub-stage for the alignment check. The routing script has no routing path that leads to the blueprint checker agent. The agent definition, phase, and gate vocabulary (`gate_2_3_alignment_exhausted`) all exist but are never wired into the execution flow. The blueprint proceeds to test generation unvalidated.

**Detection:** A regression test verifies that after Gate 2.1 APPROVE, the pipeline transitions to `alignment_check` sub-stage and invokes the blueprint checker — not directly to Pre-Stage-3. The test verifies that `ALIGNMENT_CONFIRMED` presents Gate 2.2, and only Gate 2.2 APPROVE advances to Pre-Stage-3. `ALIGNMENT_FAILED` presents the appropriate gate.

**Recovery:** This is a P1 (cross-unit contract drift) instance: the vocabulary and agent definitions define the alignment check, but the routing and state transition logic never references them. The fix is to add an `alignment_check` sub-stage to Stage 2 (see Section 8.2) and wire it into the routing script. The alignment check is the final step of Stage 2, not a separate stage.

### 24.19 Infrastructure Setup Reads `total_units` From State Instead of Deriving From Blueprint (NEW IN 2.1 — Bug 24)

Infrastructure setup crashes with `TypeError` because `total_units` is `None` in pipeline state at Pre-Stage-3.

**Root cause:** The infrastructure setup script reads `total_units` from pipeline state using `state.get("total_units", 1)`. At Pre-Stage-3, the key exists with an explicit `null` value (set during initial state creation), so `dict.get()` returns `None` rather than the default `1`. This `None` propagates to directory creation which attempts `range(1, None + 1)`. The deeper issue is a producer/consumer inversion: infrastructure setup is the component that should **derive** `total_units` from the blueprint (by counting extracted units) and **write** it to state. Instead, the code reads it from state before blueprint extraction — a chicken-and-egg dependency.

**Detection:** A regression test verifies that infrastructure setup derives `total_units` from the blueprint, not from state. The test runs infrastructure setup with `total_units: null` in state and a valid blueprint, verifying that (1) no crash occurs, (2) the correct unit count is derived from the blueprint, (3) `total_units` is written to state as a positive integer after extraction.

**Recovery:** This is a P3 (implicit assumption) instance. The infrastructure setup script assumes `total_units` is already available in state, but at Pre-Stage-3 it has not been set yet. The fix is to derive the count from the blueprint during extraction and validate it before use (see Section 9.4).

### 24.20 Stage 3 Core Sub-Stage Routing Unspecified (NEW IN 2.1 — Bug 25)

The routing script's `route()` function for Stage 3 defaults to returning `implementation_agent` for all sub-stages except `unit_completion`. There is no branching logic for `test_generation`, `red_run`, `green_run`, `coverage_review`, or the initial `None` sub-stage. The pipeline skips test generation, red run validation, green run validation, and coverage review — jumping directly to implementation for every unit.

**Root cause:** `STAGE_3_SUB_STAGES` defines the full 11-step cycle (Unit 2), and the dispatch contracts describe transitions between sub-stages (Unit 10), but the routing contracts never specify what action to emit for each core sub-stage. The routing function has a single default return path instead of a branch per sub-stage. This is the same structural pattern as Bug 23: vocabulary and transitions are defined, but routing wiring is absent.

**Detection:** A regression test verifies that `route()` returns distinct action types and agents for each Stage 3 sub-stage: `run_command` for stub generator at `stub_generation`/`None` (Bug 36 fix); `invoke_agent` for `test_agent` at `test_generation`; `run_command` for pytest at `red_run` and `green_run`; `invoke_agent` for `implementation_agent` at `implementation`; `invoke_agent` for `coverage_review` at `coverage_review`; and the appropriate completion logic at `unit_completion`. The test must verify that no two non-equivalent sub-stages produce identical routing output.

**Recovery:** This is a P1 (cross-unit contract drift) instance. The routing script must have an explicit branch for every sub-stage defined in `STAGE_3_SUB_STAGES`. The routing contracts in Unit 10 must specify the action type, agent/command, PREPARE, and POST for each sub-stage (see Section 22.4 for the sub-stage list).

### 24.21 Stage 5 Repo Assembly Routing Missing (Post-delivery — Bug 26)

The routing script's `route()` function for Stage 5 returned `pipeline_complete` immediately when no debug session was active, without ever invoking the git repo agent. All Stage 5 infrastructure existed but was unreachable: gate vocabulary entries (`gate_5_1_repo_test`, `gate_5_2_assembly_exhausted`), phase-to-agent mapping (`repo_assembly -> git_repo_agent`), known phases (`repo_assembly`, `compliance_scan`). Additionally, `dispatch_agent_status` for `git_repo_agent` was a no-op, and `dispatch_gate_response` for `gate_5_1_repo_test` returned state unchanged for both responses. No repository directory was ever created.

**Root cause:** The Stage 5 branch in `route()` had only two paths: debug session active (invoke `bug_triage`) or no debug session (return `pipeline_complete`). The repo assembly sub-stage routing was never implemented. This is the same structural pattern as Bugs 23 and 25: infrastructure defined in vocabulary and dispatch tables, but routing wiring absent.

**Detection:** A regression test (`test_bug17_stage5_repo_assembly_routing.py`) structurally verifies: (1) `route()` returns an `invoke_agent` action for `git_repo_agent`; (2) the action includes PREPARE and POST keys; (3) `repo_assembly` phase is referenced in route(); (4) `gate_5_1` and `gate_5_2` are reachable from route() or dispatch functions; (5) `dispatch_agent_status` for `git_repo_agent` is not a bare `return state`; (6) Stage 5 references git_repo_agent before pipeline_complete.

**Recovery:** This is a P1 (cross-unit contract drift) instance. Stage 5 routing must implement full sub-stage flow: `sub_stage=None` invokes git_repo_agent; `repo_test` presents gate_5_1; `compliance_scan` runs the compliance scan; `repo_complete` returns pipeline_complete. All dispatch functions must perform proper state transitions.

### 24.22 Environment Name Derivation Mismatch in Delivered Repository (Post-delivery — Bug 27)

The git repo agent generated `environment.yml` and `README.md` with environment name `svp2_1`, replacing the dot in the project name with an underscore. The canonical `derive_env_name()` function (Unit 1) only replaces spaces and hyphens with underscores, preserving dots: `svp2.1` → `svp2.1`. The actual conda environment was `svp2.1`. Users running the documented setup commands received `EnvironmentLocationNotFound`.

**Root cause:** The git repo agent independently derived the environment name using a broader replacement rule (dots → underscores) instead of using or replicating the canonical `derive_env_name()` logic from Unit 1. Producer/consumer contract violation: Unit 1 defines the canonical derivation, but the git repo agent (Unit 18) reimplemented it with different rules.

**Detection:** Manual verification. Future prevention: tests should verify the delivered `environment.yml` name matches `derive_env_name(project_name)`.

**Recovery:** This is a P1 (cross-unit contract drift) instance. The git repo agent's task prompt should include the pre-derived canonical env name so the agent does not derive it independently. Alternatively, the agent must use `derive_env_name()` from Unit 1 exactly.

### 24.23 Git Repo Agent Single-Commit Assembly Instead of Prescribed Commit Order (Post-delivery — Bug 28)

The spec (Section 12.1) prescribes 11 sequential commits in a specific order. The git repo agent created a single monolithic "feat: initial delivery of SVP 2.1" commit containing all files. Additionally, `docs/references/` and `docs/history/` directories were not created, so reference documents (lessons learned, summary, baseline, roadmap) and version history were absent from the delivered repository.

**Root cause:** The git repo agent's task prompt describes the commit order, but the agent took a shortcut and created a single commit. The structural validation step (Section 12.3) checks file existence, import resolution, and quality gates, but does not validate commit structure or count.

**Detection:** Manual inspection of `git log --oneline`. Future prevention: structural validation should verify commit count matches the prescribed order (one commit per enabled step) and that each commit contains only the files specified for that step.

**Recovery:** This is a P7 (spec completeness) + P1 (cross-unit contract drift) instance. The structural validation checklist must include commit structure verification. The git repo agent's task prompt should state the commit order as a hard requirement with explicit validation criteria. Re-invoke the git repo agent with emphasis on the prescribed commit ordering.

### 24.24 Multiple Assembly Defects in Delivered Repository (Post-delivery — Bug 29)

During Gate 5.1 repo test, 8 tests failed revealing 5 distinct defects in the delivered repository: (1) an integration test expected pre-Bug-26 Stage 5 behavior; (2) `ALL_GATE_IDS` in `prepare_task.py` was missing 4 gate IDs that `route()` references, and `prepare_gate_prompt()` had no handlers for them; (3) the `unit_completion` command was missing the `COMMAND_SUCCEEDED` status write before `update_state.py` (Bug 11 regression); (4) hook schema regression tests used pre-Bug-17 field names (`entry["script"]` instead of `entry["hooks"][0]["command"]`); (5) Game of Life template path resolution failed in the delivered layout because `_load_gol()` resolved paths relative to `svp/` instead of the repo root.

**Root cause:** Assembly relocates files from workspace layout (`src/unit_N/`) to delivered layout (`svp/scripts/`), changing relative path relationships. Tests written against the workspace layout may fail in the delivered layout. Gate ID registries must be kept in sync with route()'s GATE_ID fields. Status write ordering (Bug 11) must be maintained when routing commands are modified.

**Detection:** Running the full test suite in the delivered repo during Gate 5.1. All 5 defects were caught by existing regression tests.

**Recovery:** P1 + P3 instance. Tests must be validated in both workspace and delivered layouts. Path-dependent modules need layout-aware resolution. Gate ID registries must be validated against route() output.

### 24.25 README Carry-Forward Content Lost During Assembly (Post-delivery — Bug 30)

The git repo agent rewrote the README from scratch instead of preserving the previous version's content. The SVP 2.0 README (`references/README_v2.0.md`) was the carry-forward base. The delivered README had different structure, different installation instructions, missing configuration fields, wrong license, and inaccurate history descriptions.

**Root cause:** Section 12.7 used the term "carry-forward" without defining what it means operationally. The task prompt did not include the reference README with explicit preserve-and-extend instructions. The agent treated README generation as a fresh authoring task.

**Detection:** Human inspection of delivered README.

**Recovery:** P7 instance. Section 12.7 updated to define carry-forward semantics: the previous version's README is the base document, preserved in full, with only new-version sections added. Task prompt must include the reference artifact. Regression test (`test_bug18_readme_carry_forward.py`) verifies reference content lines and headings are preserved in the delivered README.

### 24.26 Launcher Uses Non-Existent `--project-dir` CLI Flag (Post-delivery — Bug 31)

`launch_claude_code` invoked `claude --project-dir <path>`, but Claude Code CLI has no `--project-dir` flag. Running `svp new <name>` created the project successfully but failed at session launch with `error: unknown option '--project-dir'`.

**Root cause:** The implementation agent hallucinated a Claude Code CLI flag. The `cwd` parameter was already set correctly on the `subprocess.run` call, making the flag unnecessary. No blueprint contract specified the exact subprocess arguments, so nothing caught the error at code review.

**Detection:** Human ran `svp new` and observed the error on session launch.

**Recovery:** Removed the `--project-dir` flag from `launch_claude_code`. The function now runs `["claude"]` with `cwd=str(project_root)`, which is sufficient since Claude Code uses the working directory as the project root.

### 24.27 Unnecessary `resume` Subcommand Regression (Post-delivery — Bug 32)

The launcher introduced an explicit `svp resume` subcommand that did not exist in SVP 1.2.1. In the previous version, running `svp` with no arguments in a project directory auto-detected and resumed the project. The new `resume` subcommand added unnecessary UI complexity and broke the established workflow.

**Root cause:** The blueprint specified `_handle_resume` as a separate command handler. The spec did not explicitly define the CLI subcommand vocabulary, leaving the blueprint free to introduce new subcommands without constraint.

**Detection:** Human noticed the UI change from v1.2.1.

**Recovery:** Removed the `resume` subcommand. Running `svp` with no arguments now auto-detects an existing project in the current directory (via `pipeline_state.json` presence) and resumes it. If no project is found, it prints an error directing the user to `svp new <project_name>`.

### 24.28 Delivered Repo Created Inside Workspace (Post-delivery — Bug 37)

The git repo agent created the delivered repository inside the project workspace (`projectname/projectname-repo/`) instead of as a sibling directory (`projectname-repo/` at the same level as the workspace). Section 12.1 specifies "at the same level as the project workspace" but this instruction was not relayed to the agent definition.

**Root cause:** The blueprint's Unit 18 Tier 3 behavioral contract for the Git Repo Agent did not include the repo location requirement from spec Section 12.1. The agent definition (`GIT_REPO_AGENT_MD_CONTENT`) lacked any instruction about where to create the repository, so the agent defaulted to creating it inside the workspace.

**Detection:** Human noticed the repo was inside the workspace during Gate 5.1 review.

**Recovery:** Added explicit "Repository Location" section to the git repo agent definition specifying creation as a sibling directory. Updated blueprint Unit 18 Tier 3 behavioral contract to include the location requirement.

### 24.29 Stage 1 Routing Missing Two-Branch Check and Gate Registration (Post-delivery — Bug 41)

Stage 1 routing unconditionally invokes the stakeholder dialog agent with no two-branch check on `last_status.txt`. When the agent completes (`SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`), the next routing call re-invokes the agent instead of presenting Gate 1.1. Additionally, `gate_1_1_spec_draft` and `gate_1_2_spec_post_review` exist in routing dispatch tables (`GATE_RESPONSES`) but are not registered in gate preparation registries (`ALL_GATE_IDS`), causing `prepare_gate_prompt()` to raise `ValueError: Unknown gate ID` when the gate is triggered.

**Root cause:** The spec's two-branch routing invariant (Section 3.6) explicitly lists Stage 1 as requiring the pattern, and Section 7.4 describes the two-branch routing requirement. However, the blueprint and implementation did not apply the pattern to Stage 1 — the routing code for Stage 1 had no `last_status.txt` check. The `ALL_GATE_IDS` list was incomplete, including only Stage 0 gates (`gate_0_1_hook_activation`, `gate_0_2_context_approval`, `gate_0_3_profile_approval`, `gate_0_3r_profile_revision`) and `gate_5_1_repo_test` / `gate_5_2_assembly_exhausted`, but omitting Stage 1 gates and many others (the full extent of the omission was discovered later as Bug 43). Two distinct P1 (cross-unit contract drift) failures: routing dispatch vs. routing invariant, and routing dispatch vs. gate preparation registry.

**Detection:** A regression test (`test_bug23_stage1_spec_gate_routing.py`) structurally verifies: (1) `route()` returns a `human_gate` action for `gate_1_1_spec_draft` when `last_status.txt` contains `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`; (2) `gate_1_1_spec_draft` and `gate_1_2_spec_post_review` are present in both `GATE_RESPONSES` and `ALL_GATE_IDS`; (3) the set of gate IDs in `GATE_RESPONSES` is identical to the set in `ALL_GATE_IDS` (the gate ID consistency invariant, Section 3.6).

**Recovery:** P7 + P1 instance. Section 7 updated with explicit sub-stage flow diagram. Gate ID consistency invariant added to Section 3.6 requiring structural test verification that all gate registries are synchronized.

### 24.30 Pre-Stage-3 Reference Indexing Overwrites Alignment Status (Post-delivery — Bug 42)

After the blueprint checker confirms alignment (`ALIGNMENT_CONFIRMED`), `route()` must present Gate 2.2 to the human. When the human selects APPROVE at Gate 2.2, `route()` calls `complete_alignment_check()` to advance the in-memory state to `pre_stage_3`, then recursively calls `route()` which returns the reference indexing action block. However, the intermediate `pre_stage_3` state is never saved to disk. When the reference indexing agent completes and `update_state.py` runs, it loads the old state from disk (`stage=2, sub_stage=alignment_check`). The agent's `INDEXING_COMPLETE` status overwrites the previous status in `last_status.txt`. On the next routing call, the alignment check branch reads `INDEXING_COMPLETE`, falls into the `else` branch, and re-invokes the blueprint checker — creating an infinite loop.

Additionally, `dispatch_agent_status` for `reference_indexing` unconditionally returned `state` without advancing the pipeline from `pre_stage_3` to stage 3.

**Root cause:** Two state management gaps: (1) `route()` performed an in-memory state transition via `complete_alignment_check()` but relied on the recursive action block's POST command (`update_state.py`) to persist the result — but `update_state.py` loads state from disk independently, so the in-memory transition was lost. (2) `dispatch_agent_status` for `reference_indexing` was a no-op (`return state`), so even if the state had been persisted correctly, the pipeline would never advance from `pre_stage_3` to stage 3. Note: `ALIGNMENT_CONFIRMED` itself presents Gate 2.2 (a human gate); the state transition to `pre_stage_3` occurs only on Gate 2.2 APPROVE.

**Detection:** A regression test (`test_bug42_pre_stage3_state_persistence.py`) structurally verifies: (1) every `complete_*` or `advance_*` call in `route()` is followed by a `save_state()` call before any recursive `route()` call or action block return; (2) `dispatch_agent_status` for `reference_indexing` is not a bare `return state` — it must modify at least one of `stage`, `sub_stage`, or a state flag; (3) after Gate 2.2 APPROVE, the persisted state reflects `pre_stage_3` before the reference indexing action block is returned. **Scope note:** Despite the `test_bug42_*` name suggesting a narrow focus on the original Bug 42 scenario, check (1) enforces the route-level state persistence invariant globally — it verifies that *all* `complete_*`/`advance_*` calls in `route()` are followed by `save_state()`, not just the Gate 2.2 APPROVE-to-Pre-Stage-3 transition. This broad scope is intentional: the test prevents regression of the structural invariant itself, not just the specific bug that motivated it.

**Recovery:** P2 (State Management Assumptions) instance. Two new structural invariants added to Section 3.6: route-level state persistence invariant and exhaustive `dispatch_agent_status` invariant. Section 8.2 updated with explicit state persistence requirement for the Gate 2.2 APPROVE-to-Pre-Stage-3 transition.

### 24.31 Systemic Two-Branch Routing Invariant Violation Across Multiple Stages (Post-delivery — Bug 43)

The two-branch routing invariant (Section 3.6) was only applied to Stages 0, 1, and the Stage 2 alignment check. Every other agent-to-gate transition was missing the `last_status.txt` check:

1. **Stage 2, blueprint dialog** (`sub_stage=blueprint_dialog`): Always re-invoked `blueprint_author` instead of presenting Gate 2.1 after `BLUEPRINT_DRAFT_COMPLETE`.
2. **Stage 4**: Always invoked `integration_test_author` instead of running the integration test suite after `INTEGRATION_TESTS_COMPLETE`.
3. **Stage 5** (`sub_stage=None`): Always invoked `git_repo_agent` instead of presenting Gate 5.1 after `REPO_ASSEMBLY_COMPLETE`.
4. **Redo profile sub-stages** (`redo_profile_delivery`, `redo_profile_blueprint`): Always invoked `setup_agent` instead of presenting Gate 0.3r after `PROFILE_COMPLETE`.
5. **Debug loop triage**: Always invoked `bug_triage` instead of presenting Gate 6.2 after `TRIAGE_COMPLETE` or Gate 6.4 after `TRIAGE_NON_REPRODUCIBLE`.

Additionally, 11 gate IDs were missing from `ALL_GATE_IDS` in the preparation module and had no gate prompt handlers: `gate_2_1_blueprint_approval`, `gate_2_2_blueprint_post_review`, `gate_3_1_test_validation`, `gate_3_2_diagnostic_decision`, `gate_4_1_integration_failure`, `gate_4_2_assembly_exhausted`, `gate_6_0_debug_permission`, `gate_6_1_regression_test`, `gate_6_2_debug_classification`, `gate_6_3_repair_exhausted`, `gate_6_4_non_reproducible`.

**Root cause:** The two-branch routing invariant was applied incrementally as bugs were discovered (Bug 21 for Stage 0, Bug 41 for Stage 1) rather than universally. Each fix addressed only the stage where the bug was observed, leaving all other stages unprotected. The spec defined the invariant with an exhaustive enumeration of all affected sub-stages, but the implementation applied it piecemeal. This is a P7 (Spec completeness) + P1 (Cross-unit contract drift) compound failure: the spec correctly enumerated all affected sub-stages, but no structural test verified universal compliance, and the `ALL_GATE_IDS` list was never validated against the complete `GATE_VOCABULARY` in the routing module.

**Detection:** A universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`) structurally verifies: (1) EVERY entry in Section 3.6's exhaustive list has a corresponding two-branch check in `route()` -- the test must fail if a new gate-presenting or command-presenting entry is added to the spec without a routing-level check; (2) every key in `GATE_VOCABULARY` (routing module) appears in `ALL_GATE_IDS` (preparation module) and has a gate prompt handler; (3) every key in `ALL_GATE_IDS` appears in `GATE_VOCABULARY` (no orphan registrations). The test covers both the gate-presenting and command-presenting categories from Section 3.6.

**Recovery:** P7 + P1 instance. Universal compliance requirement added to Section 3.6 mandating single-pass application. Explicit two-branch routing paragraphs added to Section 12.1 (Stage 5), Section 12.17.4 (debug loop agents), Section 13 (redo profile sub-stages), and Section 22.4 (redo profile sub-stage state definitions). This ensures every agent-to-gate transition in the spec has an explicit, locally visible two-branch routing requirement in its own section -- not only in the centralized Section 3.6 list.

### 24.32 dispatch_agent_status Null sub_stage for test_agent (Post-delivery — Bug 44)

Stage 3 routing normalizes `sub_stage=None` to `test_generation` for routing purposes, but `dispatch_agent_status` for `test_agent` only checked `state.sub_stage == "test_generation"`. When the test agent completed with `TEST_GENERATION_COMPLETE` and `sub_stage` was still `None`, the dispatch didn't match, causing an infinite routing loop re-invoking the test agent.

**Root cause:** The routing function and the dispatch function had different assumptions about sub_stage normalization. Routing treated `None` as equivalent to `test_generation`, but dispatch required the literal string. This is a P1 (cross-unit contract drift) instance: the routing and dispatch functions are in the same file but have inconsistent null-handling contracts.

**Detection:** A regression test (`test_bug44_null_substage_dispatch.py`) verifies that `dispatch_agent_status` for `test_agent` produces a state transition when `sub_stage` is `None` and the status line is `TEST_GENERATION_COMPLETE`.

**Recovery:** Dispatch handlers must accept the same sub_stage values that routing normalizes to. When routing treats `None` as equivalent to a named sub_stage, the dispatch must also handle `None`. The exhaustive dispatch_agent_status invariant (Section 3.6) is strengthened to require consistent null-handling between routing and dispatch.

### 24.33 dispatch_command_status for test_execution Doesn't Advance sub_stage (Post-delivery — Bug 45)

`dispatch_command_status` for phase `test_execution` returned `state` unchanged for all three status lines (`TESTS_PASSED`, `TESTS_FAILED`, `TESTS_ERROR`). After the red run (sub_stage `red_run`), `TESTS_FAILED` should advance to `implementation`. After the green run (sub_stage `green_run`), `TESTS_PASSED` should advance to `coverage_review`. Without these transitions, the routing script kept re-running tests in an infinite loop.

**Root cause:** The dispatch was a no-op placeholder that was never filled in with actual state transitions. P2 (state management assumptions) instance: the dispatch assumed routing would handle advancement, but routing delegates to dispatch via `update_state.py`.

**Detection:** A regression test (`test_bug45_test_execution_dispatch.py`) verifies that `dispatch_command_status` for `test_execution` advances `sub_stage` to `implementation` when `TESTS_FAILED` is received at `sub_stage=red_run`, and advances `sub_stage` to `coverage_review` when `TESTS_PASSED` is received at `sub_stage=green_run`.

**Recovery:** Every dispatch handler must produce a state transition for the expected outcome. No-op returns are only valid for slash-command agents. A new exhaustive dispatch_command_status invariant is added to Section 3.6.

### 24.34 dispatch_agent_status for coverage_review Doesn't Advance to unit_completion (Post-delivery — Bug 46)

`dispatch_agent_status` for `coverage_review` returned `state` unchanged. After `COVERAGE_COMPLETE`, the sub_stage should advance to `unit_completion`. Without this, routing re-invoked the coverage review agent infinitely.

**Root cause:** Same as Bug 45 — the dispatch was a no-op placeholder. P2 (state management assumptions) instance. The exhaustive dispatch_agent_status invariant (Section 3.6) should have caught this — every main-pipeline agent type must explicitly advance state.

**Detection:** A regression test (`test_bug46_coverage_dispatch.py`) verifies that `dispatch_agent_status` for `coverage_review` advances `sub_stage` to `unit_completion` when `COVERAGE_COMPLETE` is received.

**Recovery:** Same as Bug 45. The exhaustive dispatch_agent_status invariant is strengthened with explicit coverage_review agent coverage.

### 24.35 unit_completion COMMAND Embeds State Update Causing Double Dispatch (Post-delivery — Bug 47)

The `unit_completion` routing action embedded `python scripts/update_state.py --phase unit_completion --unit N` inside the COMMAND string, AND also had a POST command that called `update_state.py --phase unit_completion --unit N`. This caused `complete_unit(N)` to be called twice — the first call advanced `current_unit` to N+1, and the second call raised `TransitionError` because unit N was no longer the current unit.

**Root cause:** The COMMAND was designed as a compound shell command that both wrote the status file AND ran the state update, but the POST was also generated as normal. The two mechanisms conflict. P1 (cross-unit contract drift) instance: the COMMAND and POST fields have overlapping responsibilities.

**Detection:** A regression test (`test_bug47_unit_completion_double_dispatch.py`) verifies that the `unit_completion` routing action's COMMAND field does not contain `update_state.py` or any state update invocation, and that state updates are exclusively in the POST command.

**Recovery:** COMMAND fields must never embed state update calls (`update_state.py`). State updates are exclusively the responsibility of POST commands. The COMMAND should only produce output/status; POST handles state transitions. A new COMMAND/POST separation constraint is added to the Key Constraints section.

### 24.36 Launcher CLI Contract Loss Across Spec-Blueprint-Implementation Boundary (Post-delivery — Bug 48)

The delivered launcher had three defects: (1) bare `svp` with no subcommand produced "Unknown command: None" instead of auto-detecting resume mode, (2) `--profile` argument missing from restore mode despite being required by the spec, (3) `--blueprint` (file) used instead of `--blueprint-dir` (directory) despite spec and blueprint both specifying directory semantics.

**Root cause:** The blueprint's Tier 2 signatures listed `parse_args` as a bare stub (`def parse_args(argv): ...`) without enumerating the argparse arguments. The spec defined 6 restore mode arguments in a single dense paragraph (Section 6.1.1), but the blueprint translated this into two sentences, losing `--profile` and the exact argument names. The test for bare `svp` mode accepted `None` (the broken state) instead of asserting `"resume"` (the correct post-default state). P1 (cross-unit contract drift) + P7 (spec completeness) instance: CLI argument contracts require explicit enumeration in Tier 2 signatures, not prose descriptions in Tier 3.

**Detection:** A regression test (`test_bug48_launcher_cli_contract.py`) verifies that `parse_args([])` returns `args.command == "resume"`, that restore mode accepts `--blueprint-dir` and `--profile`, and that `parse_args(["new", "myproject"])` works correctly.

**Recovery:** (1) Fix `parse_args` to default `args.command = "resume"` when no subcommand given. (2) Change `--blueprint` to `--blueprint-dir` with directory semantics. (3) Add `--profile` as a required restore mode argument. A new CLI argument enumeration invariant is added to Section 3.6.

### 24.37 Systemic Bare Argparse Stubs Across 5 Units (Post-delivery — Bug 49)

Following Bug 48, an audit found that 5 additional units (6, 7, 9, 10, 23) had the same pattern: bare `main() -> None: ...` stubs in the blueprint's Tier 2 signatures with no argparse argument enumeration. Unit 10 was the worst offender with three CLI wrappers (`update_state_main`, `run_tests_main`, `run_quality_gate_main`) each having complex argument signatures. The implementations happen to be correct in this build because the implementation agents inferred arguments from context, but a future rebuild from the blueprint alone would likely produce incorrect CLI interfaces.

**Root cause:** Bug 48's prevention rule (CLI argument enumeration invariant) was applied only to Unit 24. The systemic application to all units with argparse was not performed. Same piecemeal-fix pattern as Bug 43. P1 + P7 instance.

**Detection:** A regression test (`test_bug49_argparse_enumeration.py`) verifies that every CLI entry point across Units 6, 7, 9, 10, 23 accepts its documented argparse arguments.

**Recovery:** (1) Blueprint Tier 2 updated for all affected units with full argparse argument enumeration. (2) CLI argument enumeration invariant (Section 3.6) strengthened to list all affected units explicitly and require blueprint checker verification. (3) Structural regression test added.

### 24.38 Insufficient Contract Specificity and Boundary Violations in Blueprint (Post-delivery -- Bug 50)

A systematic audit found 16 functions across 6 units where Tier 3 behavioral contracts were too vague for deterministic reimplementation, and several internal helper functions that had leaked into Tier 2 signatures. Under-specification: functions depending on specific data values (lookup tables, enum validation sets, magic numbers) not mentioned in contracts. Over-specification: internal helpers (`_deep_merge`, `_clone_state`, `_replace_function_bodies`) appearing in Tier 2 where they don't belong.

**Root cause:** The spec gave the blueprint author no guidance on what level of detail is required in each tier or where the boundary lies between contracts and implementation details. P7 (Spec completeness).

**Detection:** A regression test (`test_bug50_contract_sufficiency.py`) verifies critical data values and behavioral details across all affected units.

**Recovery:** (1) Contract sufficiency invariant added to spec Section 3.16. (2) Contract boundary rule added to spec Section 3.16. (3) Blueprint Tier 2 expanded with critical data constants and enum sets. (4) Blueprint Tier 3 expanded with sufficient implementation detail. (5) Internal helpers removed from Tier 2 signatures. (6) Blueprint author guidance updated in Section 30.

### 24.39 Debug Loop Missing Reassembly Routing After Repair Completion (Post-delivery -- Bug 51)

After a successful repair in the debug loop, the triage agent's Step 6 instructs "fix workspace, then Stage 5 reassembly." But `dispatch_agent_status` for `repair_agent` with `REPAIR_COMPLETE` returned `state` unchanged -- no routing to re-enter Stage 5. The workspace fix was never propagated to the delivered repo through the pipeline. In practice, fixes were applied directly to the delivered repo, bypassing the canonical workspace-then-reassemble flow and creating potential drift between workspace and delivered repo.

**Root cause:** The triage agent definition (Unit 19) documented the intent (Step 6: fix workspace, then reassemble), but the routing script (Unit 10) had no corresponding state transition for `REPAIR_COMPLETE`. The agent's behavioral instructions and the routing dispatch were not synchronized. P1 (Cross-unit contract drift).

**Detection:** A regression test (`test_bug51_debug_reassembly.py`) verifies that `dispatch_agent_status` for `repair_agent` with `REPAIR_COMPLETE` during an active debug session sets `stage="5"` and `sub_stage=None` to trigger git_repo_agent reassembly.

**Recovery:** (1) `dispatch_agent_status` for `repair_agent` updated: on `REPAIR_COMPLETE` during an active debug session (`state.debug_session is not None`), set `stage="5"`, `sub_stage=None` to trigger git_repo_agent reassembly. Debug session remains active during reassembly. (2) Regression test added. (3) Lessons learned updated.

### 24.40 version_document Not Wired at Every REVISE/FIX Gate (Post-delivery -- Bug 52)

Before Bug 52, several REVISE and FIX gate responses in `dispatch_gate_response` called `restart_from_stage` without first calling `version_document` to archive the current document. This meant document history was incomplete -- some revisions had no archived prior version.

**Root cause:** The document versioning contract (Section 23) lists all trigger points, but the implementation only wired `version_document` at a subset. P1 (Cross-unit contract drift) between the spec's trigger list and the dispatch implementation.

**Detection:** A regression test (`test_bug52_version_document_wiring.py`) verifies that every REVISE/FIX gate path calls `version_document` before `restart_from_stage`.

**Recovery:** All missing `version_document` / `_version_spec` / `_version_blueprint` calls added to `dispatch_gate_response` at every REVISE/FIX trigger point listed in Section 23.

### 24.41 Orphaned Functions Without Call Sites (Post-delivery -- Bug 53)

Functions existed in the codebase with no callers -- dead code that passed all tests because no test exercised the orphaned path.

**Root cause:** P5 (Orphaned code). Functions were defined in contracts but never wired into any dispatch or routing path.

**Detection:** A regression test (`test_bug53_orphaned_functions.py`) scans for exported functions without call sites.

**Recovery:** Orphaned functions removed or wired into their intended call sites.

### 24.42 Orphaned Hollow Function update_state_from_status (Post-delivery -- Bug 54)

`update_state_from_status` existed as a hollow stub with no implementation, no callers, and no tests. It duplicated the role of `dispatch_agent_status` and `dispatch_command_status`.

**Root cause:** P5 (Orphaned code). A function was specified in the blueprint but never connected to the pipeline flow.

**Detection:** A regression test (`test_bug54_orphaned_update_state_from_status.py`) verifies the function does not exist or has been properly removed.

**Recovery:** Function removed from the codebase.

### 24.43 rollback_to_unit and set_debug_classification Never Wired Into Dispatch (Post-delivery -- Bug 55)

Gate 6.2 FIX UNIT response existed in `GATE_VOCABULARY` but `dispatch_gate_response` did not call `rollback_to_unit` or `set_debug_classification`. The debug loop could not execute the FIX UNIT path.

**Root cause:** P1 (Cross-unit contract drift). The gate vocabulary defined the response option, but the dispatch handler was missing the state transition calls.

**Detection:** Structural validation of `dispatch_gate_response` against `GATE_VOCABULARY` response options.

**Recovery:** `dispatch_gate_response` for `gate_6_2_debug_classification` FIX UNIT now calls `set_debug_classification` and `rollback_to_unit`. Phase-based debug routing added.

### 24.44 Spec Structural Gaps: Downstream Dependency and Contract Granularity (Post-delivery -- Bug 56)

The spec lacked explicit rules for downstream dependency invalidation during re-entry paths and for contract granularity requirements. This allowed blueprints that were structurally correct but operationally incomplete.

**Root cause:** P7 (Spec omission). The spec described what happens but not what must be verified.

**Detection:** Structural review during blueprint checker operation.

**Recovery:** Added Section 3.18 (Downstream Dependency Invariant) and Section 3.19 (Contract Granularity Rules) to the spec. Blueprint checker updated to verify these rules.

### 24.45 Review Enforcement: Baked Dependency and Contract Checklists (Post-delivery -- Bug 57)

Reviewer agent definitions lacked concrete checklists for verifying downstream dependencies and contract completeness, relying on general instructions that were insufficient to catch systematic omissions.

**Root cause:** P8 (Agent instruction insufficiency). Agent definitions described goals but not verification steps.

**Detection:** Structural review of reviewer agent output quality.

**Recovery:** Added Section 3.20 (Review Enforcement). Mandatory checklists baked into stakeholder reviewer, blueprint checker, and blueprint reviewer agent definitions.

### 24.46 Gate 5.3 Missing From GATE_VOCABULARY and Dispatch (Post-delivery -- Bug 58)

Gate 5.3 (`gate_5_3_unused_functions`) was defined in the spec but missing from `GATE_VOCABULARY` in routing.py and had no dispatch handler. The compliance scan could detect unused functions but could not present the gate to the human.

**Root cause:** P1 (Cross-unit contract drift). The spec defined the gate, but the routing implementation omitted it.

**Detection:** A regression test (`test_bug58_gate_5_3_unused_functions.py`) verifies Gate 5.3 is in `GATE_VOCABULARY` and has a dispatch handler.

**Recovery:** Gate 5.3 added to `GATE_VOCABULARY` with response options `FIX SPEC` and `OVERRIDE CONTINUE`. Dispatch handler added to `dispatch_gate_response`.

### 24.47 Stale blueprints/ Directory and Multiple Implementation Bugs (Post-delivery -- Bug 59)

Multiple issues discovered during comprehensive audit: stale `blueprints/` (plural) directory diverging from canonical `blueprint/` (singular); `_version_blueprint` hardcoded wrong path; `advance_stage` checked non-existent file; `load_blueprint` did not handle two-file format; missing gate and status registrations; `DebugSession` missing retry counters; `version_document` lacked companion file support; `_FIX_LADDER_TRANSITIONS` had cross-branch error.

**Root cause:** P1 (Cross-unit contract drift) and P7 (Spec completeness). Multiple components maintained independent assumptions about directory naming and file structure after the blueprint split.

**Detection:** Regression test (`test_bug59_blueprint_path_and_gates.py`) verifies blueprint path resolution, gate registration completeness, and structural correctness.

**Recovery:** Removed stale directory, fixed all path references, added missing registrations, updated state schema, and added companion file support to version_document.

### 24.48 Broken _get_unit_context and Stale Fallback ARTIFACT_FILENAMES (Post-delivery -- Bug 60)

`_get_unit_context` in Unit 9 constructed an invalid path (`blueprint/blueprint.md`) because the fallback `ARTIFACT_FILENAMES` dict had a stale `"blueprint"` key instead of `"blueprint_dir"`, and the path construction joined a directory name with a filename instead of passing the directory to `build_unit_context`. All agents receiving unit context silently got the placeholder "(Unit N context not available.)" instead of actual blueprint content.

**Root cause:** P3 (Stale cross-unit reference). Bug 59 updated Unit 1 ARTIFACT_FILENAMES but did not propagate the key rename to Unit 9's fallback dict.

**Detection:** Regression test (`test_bug60_unit_context_blueprint_path.py`) verifies `_get_unit_context` resolves the blueprint directory correctly and returns non-placeholder content.

**Recovery:** Changed fallback key to `"blueprint_dir": "blueprint"`. Changed `_get_unit_context` to pass the directory (not a constructed file path) to `build_unit_context`.

### 24.49 Missing include_tier1 Parameter in _get_unit_context and build_unit_context (Post-delivery -- Bug 61)

`build_unit_context` (Unit 5) and `_get_unit_context` (Unit 9) lacked the `include_tier1` parameter. All agents received full Tier 1 prose descriptions, defeating the token reduction purpose of the two-file blueprint split (Section 3.16). The stubs correctly specified the parameter but the deployed implementations never implemented it.

**Root cause:** P3 (Stale cross-unit reference). Deployed implementations diverged from their stub specifications.

**Detection:** Regression test (`test_bug61_include_tier1_parameter.py`) verifies the `include_tier1` parameter is accepted by both functions and that `test_agent`/`implementation_agent` call sites pass `include_tier1=False`.

**Recovery:** Added `include_tier1: bool = True` parameter to both functions. Wired `test_agent` and `implementation_agent` call sites to pass `False`.

### 24.50 Selective Blueprint Loading Not Wired Per Agent Matrix (Post-delivery -- Bug 62)

Three agents (`integration_test_author`, `git_repo_agent`, `help_agent`) received full blueprint content when the Section 3.16 matrix prescribed selective loading. No `load_blueprint_contracts_only` or `load_blueprint_prose_only` functions existed.

**Root cause:** P7 (Spec completeness — incomplete implementation). The spec defined the agent matrix but the implementation used the same full loader for all agents.

**Detection:** Regression test (`test_bug62_selective_blueprint_loading.py`) verifies each agent receives exactly the content prescribed by the Section 3.16 matrix.

**Recovery:** Added `load_blueprint_contracts_only()` and `load_blueprint_prose_only()` to Unit 9. Wired `integration_test_author` and `git_repo_agent` to contracts-only, `help_agent` to prose-only.

---

## 25. Test Data

Test agents generate synthetic test data from stakeholder spec data characteristics. The test agent declares synthetic data assumptions, presented to the human at the test validation gate. Human-provided real data is not supported in this version.

---

## 26. Deterministic Components (CHANGED IN 2.1)

The following are implemented as scripts with no LLM involvement:

- **State management scripts:** read, update, validate `pipeline_state.json`. Update scripts validate preconditions.
- **Routing script:** reads state, outputs structured action block. Handles quality gate sub-stages and routing paths **(NEW IN 2.1)**.
- **Preparation script:** assembles task/gate prompts. Includes quality report in agent re-pass prompts **(NEW IN 2.1)**.
- **Stub generator:** parses signatures from blueprint via `ast`, produces stub files.
- **Blueprint extractor:** extracts unit definitions and upstream contracts.
- **Dependency extractor:** scans signature blocks, extracts imports, produces dependency list. Installs quality packages from toolchain **(NEW IN 2.1)**.
- **Import validator:** executes imports in Conda environment.
- **Ledger manager:** append, read, compact, clear ledgers.
- **Hint prompt assembler:** wraps hints in context-dependent prompt blocks.
- **Command scripts:** `cmd_save.py`, `cmd_quit.py`, `cmd_status.py`, `cmd_clean.py`.
- **Quality gate scripts (NEW IN 2.1):** execute quality tool commands from `toolchain.json`, parse output, classify residuals, produce quality reports for agent re-passes.
- **Delivery compliance scan:** reads profile, scans delivered source for banned patterns.
- **Universal write authorization hooks:** validate writes against pipeline state.
- **SVP launcher:** session lifecycle, prerequisite verification, file copying, permission management.

All have pytest test suites. The preparation script has elevated coverage.

---

## 27. Future Directions (CHANGED IN 2.1)

SVP 2.1 is the terminal release of the SVP product line. The pipeline architecture is complete. No further SVP releases are planned.

### 27.1 Language-Directed Variants

Future development takes the form of language-targeted products, each built by SVP 2.1:

```
SVP 2.1  ──builds──>  SVP-R       (targets R projects: renv, testthat, roxygen2)
SVP 2.1  ──builds──>  SVP-elisp   (targets Emacs Lisp: Cask, ERT)
SVP 2.1  ──builds──>  SVP-bash    (targets bash: shunit2 or bats)
```

Each variant is a complete standalone Claude Code plugin. It shares SVP's pipeline architecture (stages, gates, fix ladders, state machine, orchestration protocol) but implements language-specific tooling: parsers, stub generators, test output readers, environment management, and agent prompts. Each variant is a Python project containing Python code that manipulates artifacts in the target language. SVP 2.1 builds it without any language extensions.

Each variant can evolve independently. SVP-R may gain R-specific features that SVP-elisp doesn't need, and vice versa.

### 27.2 The Build Chain

```
SVP 1.2.1  ──builds──>  SVP 2.0
SVP 2.0    ──builds──>  SVP 2.1
SVP 2.1    ──builds──>  SVP-R, SVP-elisp, SVP-bash  (independently)
```

No manual bootstrap at any step. No version of SVP ever needs to build a non-Python project.

### 27.3 CLI as Foundational Interface

The CLI is not an interim choice. The terminal model is intrinsic: matches the orchestration architecture, preserves full conversation history, ensures all interactions are explicit, auditable, and reproducible.

### 27.4 Beyond the Current Architecture

Long-term directions that would require a new major version (not SVP 2.x) are documented separately in the SVP Product Roadmap (`svp_product_roadmap.md`). These include capabilities that would change the pipeline's fundamental architecture, such as multi-model test authoring. They are not planned for any current development timeline.

---

## 28. Implementation Note

This spec is built using SVP 2.0. Blueprint must fit within context budget. Primary risk: blueprint size from quality gate routing paths and delivered quality configuration. Blueprint author should fold quality gate functionality into existing units per the unit impact matrix in Part III.

Bundled example (Game of Life): carried forward unchanged. Prompt caching: out of scope.

---

# PART III — ARCHITECTURAL STRATEGY (Sections 29–34)

---

## 29. The Two-File Architecture (CHANGED IN 2.0)

1. **`project_profile.json`** — Human-facing. Delivery preferences. Agents read via task prompts. Immutable after Gate 0.3.
2. **`toolchain.json`** — Pipeline-facing. Build commands. Scripts read at runtime. Never modified.

The profile says how the delivered project should look. The toolchain file says how SVP builds and tests. They serve different consumers and change at different rates.

---

## 30. Blueprint Author Guidance (CHANGED IN 2.0, CHANGED IN 2.1)

**Unit 1 (scope grows):** Add quality section to toolchain schema + validation. Add quality section to profile schema. Three schemas, three loaders, three validators **(CHANGED IN 2.1)**. Define canonical pipeline artifact filenames (e.g., `stakeholder_spec.md`, `blueprint_prose.md`, `blueprint_contracts.md`) as shared constants; all producers and consumers must reference these constants (Bug 22 fix) **(NEW IN 2.1)**. `DEFAULT_PROFILE` must use the exact canonical section and field names from the profile schema (Section 6.4): top-level sections `delivery` (not `packaging`), `license` (not `licensing`); field `readme.audience` (not `readme.target_audience`); field `delivery.environment_recommendation` (not `delivery.environment`). A regression test must verify that every key path in `DEFAULT_PROFILE` matches the canonical schema **(NEW IN 2.1)**.

**Unit 2:** Add quality gate sub-stages to state schema **(NEW IN 2.1)**. Add Stage 2 sub-stages (`blueprint_dialog`, `alignment_check`) to state schema (Bug 23 fix) **(NEW IN 2.1)**.

**Unit 3:** Add quality gate state transitions (enter gate, retry, fail-to-ladder) **(NEW IN 2.1)**. Add Stage 2 state transitions: Gate 2.1 APPROVE must transition to `alignment_check` sub-stage (not directly to Pre-Stage-3); `ALIGNMENT_CONFIRMED` presents Gate 2.2 (human decides); Gate 2.2 APPROVE advances to Pre-Stage-3; `ALIGNMENT_FAILED` dispatches per checker classification (Bug 23 fix) **(NEW IN 2.1)**. `dispatch_agent_status` for `reference_indexing` must advance the pipeline from `pre_stage_3` to stage 3 — a bare `return state` is not valid for a main-pipeline agent (Bug 42 fix, exhaustive dispatch_agent_status invariant, Section 3.6) **(Post-delivery fix)**. `dispatch_agent_status` for `test_agent` must handle `sub_stage=None` equivalently to `sub_stage="test_generation"` (Bug 44 fix). `dispatch_command_status` for `test_execution` must advance from `red_run` to `implementation` on `TESTS_FAILED` and from `green_run` to `coverage_review` on `TESTS_PASSED` — no-op handlers are invalid (Bug 45 fix, exhaustive dispatch_command_status invariant, Section 3.6). `dispatch_agent_status` for `coverage_review` must advance to `unit_completion` on `COVERAGE_COMPLETE` (Bug 46 fix) **(Post-delivery fix)**.

**Unit 5 (CHANGED IN 2.1):** `extract_unit`, `extract_upstream_contracts`, and `build_unit_context` must accept a `include_tier1: bool` parameter (default `True`). When `False`, Tier 1 description content is excluded from the returned context. `parse_blueprint` must accept an optional `contracts_path` parameter to parse `blueprint_contracts.md` separately from `blueprint_prose.md`. The `UnitDefinition` dataclass is unchanged — it continues to carry all tiers; the parameter controls what is included in assembled context strings.

**Unit 6 (CHANGED IN 2.1):** `generate_stub_source` must prepend `__SVP_STUB__ = True  # DO NOT DELIVER — stub file generated by SVP` as the first non-import statement in every generated stub. This sentinel is required — its absence from stub output is a Unit 6 contract violation. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `main()`'s argparse arguments: `--blueprint`, `--unit`, `--output-dir`, `--upstream`.

**Unit 7:** Install `quality.packages` during infrastructure setup **(NEW IN 2.1)**. Replace hardcoded commands with toolchain reader calls **(CHANGED IN 2.0)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `main()`'s argparse arguments: `--project-root`.

**Unit 9 (CHANGED IN 2.1):** Include quality report in agent re-pass task prompts **(NEW IN 2.1)**. Extract profile sections for agent task prompts **(CHANGED IN 2.0)**. Reference shared filename constants for all artifact paths — no hardcoded filenames (Bug 22 fix) **(NEW IN 2.1)**. Task prompt assembly for test agent and implementation agent invocations must pass `include_tier1=False` to `build_unit_context`. Task prompt assembly for diagnostic agent, help agent, and blueprint checker invocations must pass `include_tier1=True`. Add lessons learned filtering for test agent task prompt assembly. Filtering logic: match on unit number and/or pattern classification. Output appended under a dedicated heading. No LLM involvement in filtering — pure text matching and extraction. `ALL_GATE_IDS` must include every gate ID in the pipeline — the complete set of 22 gate IDs enumerated in Section 18.4: `gate_0_1_hook_activation`, `gate_0_2_context_approval`, `gate_0_3_profile_approval`, `gate_0_3r_profile_revision`, `gate_1_1_spec_draft`, `gate_1_2_spec_post_review`, `gate_2_1_blueprint_approval`, `gate_2_2_blueprint_post_review`, `gate_2_3_alignment_exhausted`, `gate_3_1_test_validation`, `gate_3_2_diagnostic_decision`, `gate_4_1_integration_failure`, `gate_4_2_assembly_exhausted`, `gate_5_1_repo_test`, `gate_5_2_assembly_exhausted`, `gate_6_0_debug_permission`, `gate_6_1_regression_test`, `gate_6_2_debug_classification`, `gate_6_3_repair_exhausted`, `gate_6_4_non_reproducible`, `gate_6_5_debug_commit`, `gate_hint_conflict` (Bug 41 fix for Stage 1 gates, Bug 43 fix for remaining gaps). The gate ID consistency invariant (Section 3.6) requires that `ALL_GATE_IDS` is synchronized with `GATE_RESPONSES`/`GATE_VOCABULARY` in Unit 10 — every gate ID must appear in both, with no orphans in either direction **(Post-delivery fix, expanded by Bug 43)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `main()`'s argparse arguments: `--project-root`, `--agent`, `--gate`, `--unit`, `--output`, `--ladder`, `--revision-mode`, `--quality-report`. **Selective blueprint loading (Bugs 60-62 fix):** Unit 9 must export `load_blueprint_contracts_only()` and `load_blueprint_prose_only()` as Tier 2 functions. Per the Section 3.16 agent loading matrix: `integration_test_author` and `git_repo_agent` use `load_blueprint_contracts_only()`; `help_agent` uses `load_blueprint_prose_only()`; `blueprint_checker`, `blueprint_reviewer`, `hint_agent`, and `bug_triage` use `load_blueprint()` (both files). The internal helper `_get_unit_context` must accept `include_tier1: bool` and pass it through to `build_unit_context` (Unit 5). Blueprint directory resolution uses `get_blueprint_dir()` which reads `ARTIFACT_FILENAMES["blueprint_dir"]` from Unit 1 (Bug 60 fix) **(Post-delivery fix)**.

**Unit 10 (HEAVIEST CHANGE):** Add quality gate routing paths and command execution **(NEW IN 2.1)**. Gate composition read from toolchain **(NEW IN 2.1)**. Replace hardcoded commands with toolchain reader calls **(CHANGED IN 2.0)**. Implement the two-branch routing invariant (Section 3.6) for **every** sub-stage with an agent-to-gate transition in a single implementation pass — not incrementally as bugs are discovered (Bug 43 fix): `route()` must check `last_status.txt` to distinguish "agent not yet done" from "agent done, present gate." This applies to Stage 0 (`project_context`, `project_profile`), Stage 1 (`stakeholder_spec_authoring` — Bug 41 fix: Stage 1 routing must check for `SPEC_DRAFT_COMPLETE`/`SPEC_REVISION_COMPLETE` before presenting Gate 1.1), Stage 2 (`blueprint_dialog`, `alignment_check`), Stage 4 (integration test author), Stage 5 (git repo agent), redo profile sub-stages (`redo_profile_delivery`, `redo_profile_blueprint`), and all post-delivery debug loop agent-to-gate transitions (triage to Gate 6.2/6.4, repair to Gate 6.3, test agent to Gate 6.1). The invariant is a structural requirement — not a per-stage fix list (Bug 21 generalized fix, Bug 43 universal compliance requirement, see Section 3.6) **(CHANGED IN 2.1, expanded by Bug 43)**. `GATE_RESPONSES`/`GATE_VOCABULARY` must include entries for every gate ID in the pipeline, and the set of gate IDs must be identical to `ALL_GATE_IDS` in Unit 9 (gate ID consistency invariant, Section 3.6 — Bug 41 fix, expanded by Bug 43) **(Post-delivery fix)**. Wire alignment check into Stage 2 routing: after Gate 2.1 APPROVE, route to `alignment_check` sub-stage and invoke blueprint checker; on `ALIGNMENT_CONFIRMED`, present Gate 2.2; on Gate 2.2 APPROVE, advance to Pre-Stage-3; dispatch on checker failure outcome (Bug 23 fix, see Section 8.2) **(NEW IN 2.1)**. Any `route()` branch that performs an in-memory state transition (via `complete_*` or `advance_*`) and then recursively routes must persist state to disk via `save_state()` before returning the action block — specifically, the Gate 2.2 APPROVE transition to `pre_stage_3` must be saved before the Pre-Stage-3/reference-indexing action block is returned (Bug 42 fix, route-level state persistence invariant, Section 3.6) **(Post-delivery fix)**. Add explicit routing branches for all core Stage 3 sub-stages (`stub_generation`, `test_generation`, `red_run`, `implementation`, `green_run`, `coverage_review`, `unit_completion`): `route()` must emit the correct action type (invoke_agent or run_command) for each sub-stage (Bug 25 fix, see Section 24.20) **(NEW IN 2.1)**. Add full Stage 5 sub-stage routing: `route()` must invoke git_repo_agent at `sub_stage=None`, present `gate_5_1_repo_test` at `repo_test`, run compliance scan at `compliance_scan`, and return `pipeline_complete` at `repo_complete`; all dispatch functions must perform proper state transitions (Bug 26 fix, see Section 24.21) **(Post-delivery fix)**. **Dispatch completeness for Stage 3 (Bugs 44-47 fix):** `dispatch_agent_status` for `test_agent` must handle `sub_stage=None` the same as `sub_stage="test_generation"` (Bug 44). `dispatch_command_status` for `test_execution` must advance `sub_stage` from `red_run` to `implementation` on `TESTS_FAILED` and from `green_run` to `coverage_review` on `TESTS_PASSED` — no-op returns are invalid (Bug 45). `dispatch_agent_status` for `coverage_review` must advance `sub_stage` to `unit_completion` on `COVERAGE_COMPLETE` (Bug 46). The `unit_completion` routing action's COMMAND must not embed `update_state.py` calls — state updates are exclusively in POST (Bug 47). See exhaustive dispatch invariants in Section 3.6 and COMMAND/POST separation in Key Constraints **(Post-delivery fix)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate argparse arguments for `update_state_main` (`--project-root`, `--gate-id`, `--unit`, `--phase`), `run_tests_main` (positional `test_path`, `--env-name`, `--project-root`, `--test-path`), and `run_quality_gate_main` (positional `gate_id`, `--gate`, `--target`, `--env-name`, `--project-root`). **Debug loop reassembly (Bug 51 fix):** `dispatch_agent_status` for `repair_agent` must trigger Stage 5 reassembly on `REPAIR_COMPLETE` during an active debug session — set `stage="5"`, `sub_stage=None`. Debug session remains active. `REPAIR_FAILED` and `REPAIR_RECLASSIFY` retain existing behavior **(Post-delivery fix)**.

**Unit 11:** Replace hardcoded commands with toolchain reader calls **(CHANGED IN 2.0)**.

**Unit 12 (hooks) (CHANGED IN 2.1):** Add write authorization for `project_profile.json`, `toolchain.json` **(CHANGED IN 2.0)**, `ruff.toml` **(NEW IN 2.1)**, delivered repo path during debug sessions **(NEW IN 2.1)**, and lessons learned document during debug sessions **(NEW IN 2.1)**. Add `PostToolUse` stub sentinel hook. Handler is a command hook (shell script). Matcher: Write tool calls to `src/unit_N/` paths. Behavior: grep written content for `__SVP_STUB__`; exit 2 with explanatory message if found.

**Unit 13 (setup agent):** Expand dialog for Area 5 (quality preferences) **(NEW IN 2.1)**, changelog question in Area 1 **(NEW IN 2.1)**. Profile dialog and Gate 0.3. Targeted revision mode **(CHANGED IN 2.0)**. The setup agent's system prompt must include the complete `project_profile.json` schema with exact canonical field names (Section 6.4) so that the agent's JSON output uses the same section and field names as `DEFAULT_PROFILE` in Unit 1 **(NEW IN 2.1)**.

**Unit 14 (blueprint checker) (CHANGED IN 2.1):** Add quality profile preference validation (Layer 2) **(NEW IN 2.1)**. Blueprint checker receives the pattern catalog section of `svp_2_1_lessons_learned.md` as an additional input. Checker produces a risk section in its output identifying structural features matching known failure patterns (P1-P9+). Advisory only — does not block approval.

**Unit 15 (test/impl agents):** Add quality awareness to agent prompts **(NEW IN 2.1)**.

**Unit 16 (redo agent):** Add `profile_delivery` and `profile_blueprint` classifications **(CHANGED IN 2.0)**.

**Unit 18 (git repo agent):** Generate delivered quality tool configs **(NEW IN 2.1)**. Generate changelog **(NEW IN 2.1)**. Deliver all project documents to repo (unified Bug 15 fix) **(NEW IN 2.1)**. Read profile for all delivery preferences **(CHANGED IN 2.0)**. Record `delivered_repo_path` in `pipeline_state.json` at Stage 5 completion **(NEW IN 2.1)**. Environment name in delivered `environment.yml` and `README.md` must use canonical `derive_env_name()` derivation from Unit 1, not independent derivation (Bug 27 fix, see Section 24.22) **(Post-delivery fix)**.

**Unit 20 (slash commands) (CHANGED IN 2.1):** Group B command definitions (`help`, `hint`, `ref`, `redo`, `bug`) must include the complete action cycle: steps for running `prepare_task.py`, spawning the agent, writing status to `.svp/last_status.txt`, running `update_state.py --phase <phase>` with the correct phase value, and re-running the routing script. The `--phase` values are: `help`, `hint`, `reference_indexing`, `redo`, `bug_triage`. These must match the `phase_to_agent` mapping in Unit 10. A command definition that stops after "spawn the agent" is incomplete and will cause the main session to fail the action cycle (Bug 38 fix).

**Unit 21 (orchestration skill) (CHANGED IN 2.1):** `SKILL_MD_CONTENT` must include a section on slash-command-initiated action cycles. Group B commands bypass the routing script — the command definition substitutes for the routing script's action block. The skill must explain that the same six-step cycle applies, with the command definition providing the PREPARE command, agent type, and POST command (including the correct `--phase` value). Without this section, the main session has no behavioral guidance for completing the action cycle when a slash command is invoked outside the routing loop (Bug 39 fix).

**Unit 22 (templates):** Add `ruff.toml` to project templates **(NEW IN 2.1)**. Update toolchain default JSON **(NEW IN 2.1)**.

**Unit 23 (plugin manifest):** Validate quality section in structural validation **(NEW IN 2.1)**. Add `toolchain_defaults/` **(CHANGED IN 2.0)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `compliance_scan_main()`'s argparse arguments: `--project-root`, `--src-dir`, `--tests-dir`.

**Unit 24 (launcher):** Copy `ruff.toml` during project creation and set to read-only **(NEW IN 2.1)**. Copy toolchain file **(CHANGED IN 2.0)**. Implement `svp restore` subcommand with document placement and state initialization **(CHANGED IN 2.1)**. Implement full pre-flight check sequence with ordered checks and specific error messages (Section 6.1.2) **(CHANGED IN 2.1)**. Session launch via `subprocess.run` with `cwd`, `env` (for `SVP_PLUGIN_ACTIVE`), and restart signal loop (Section 6.1.5) **(CHANGED IN 2.1)**. `parse_args` must enumerate all argparse arguments in Tier 2 invariants per the CLI argument enumeration invariant (Section 3.6, Bug 48 fix): bare `svp` defaults `args.command = "resume"`, restore mode uses `--blueprint-dir` (directory, not file), and `--profile` is a required restore argument **(Post-delivery fix)**.

**Critical: Dual write-path awareness (NEW IN 2.1).** Two independent write paths exist in the pipeline: agent writes (through Claude Code's Write tool, validated by `PreToolUse` hooks) and pipeline subprocess writes (quality auto-fix, assembly scripts, executed via `subprocess.run` from deterministic scripts). Hooks control the first path; they do not intercept the second. This is correct by design -- quality tools and assembly scripts are pipeline infrastructure, not agent actions. The blueprint author must not implement hooks that assume all file modifications flow through Claude Code's Write tool. Conversely, the blueprint author must not assume subprocess writes are covered by hook authorization. Both paths must be considered independently when designing write authorization rules. This dual-path model applies during both the build (Sections 10.3, 10.6, 10.12) and the post-delivery debug loop (Section 12.17.10).

**Critical: Contract sufficiency and boundary awareness (NEW IN 2.1 -- Bug 50 fix).** The blueprint author must apply both the contract sufficiency invariant (Section 3.16) and the contract boundary rule (Section 3.16) when designing each unit. Concretely: (1) Every function whose behavior depends on specific data values (e.g., `_MODEL_CONTEXT_WINDOWS` mapping model names to token counts, `_RECOGNIZED_PLACEHOLDERS` listing valid placeholder names, enum validation sets like `{"ruff", "flake8", "pylint", "none"}`) must have those values specified in the Tier 2 invariants or Tier 3 contract. (2) Internal helper functions (underscore-prefixed, not imported cross-unit) must NOT appear in Tier 2 signatures -- their behavioral effect must instead be described in the Tier 3 contract of the public function that uses them. Example: `_deep_merge` should not be in Tier 2, but `load_config`'s Tier 3 contract should say "missing keys filled from defaults via recursive merge: for nested dicts, merge recursively; for non-dict values, override wins."

---

## 31. Forking Point Classification (CHANGED IN 2.1)

**Tier A (pipeline-fixed):** Language (Python), environment (conda), test framework (pytest), build backend (setuptools), VCS (git), source layout during build (SVP-native), quality tools during build (ruff + mypy). Recorded in profile `fixed` section. Not presented as choices.

**Tier B (delivery-configurable):** Five dialog areas: version control (commit style, branch strategy, tagging, changelog), README and documentation (audience, sections, depth, optional content), testing (coverage, readable names), licensing and packaging (license, metadata, entry points, delivery environment, dependency format, source layout), delivered quality tools (linter, formatter, type checker, import sorter, line length). Captured in profile. Acted on by git repo agent.

**Unsupported preferences.** If the human requests a delivery feature that SVP 2.1 does not support (CI templates, Docker, pre-commit hooks, documentation sites, etc.), the setup agent acknowledges the request, explains honestly that SVP does not handle it, and tells the human they will need to add it manually after delivery. Nothing is recorded in the profile. SVP 2.1 is the terminal release — there is no "future version" promise.

---

## 32. What the Blueprint Author Must NOT Do (CHANGED IN 2.1)

- Build provider interfaces, abstract base classes, or dynamic dispatch.
- Make `toolchain.json` user-editable.
- Make `ruff.toml` user-editable **(NEW IN 2.1)**.
- Parameterize agent definition files with toolchain variables.
- Add a language or toolchain selection dialog.
- Break behavioral equivalence for existing toolchain sections.
- Add new stages, agents, or gate types for quality gates **(NEW IN 2.1)**.
- Implement quality gates as fix ladder positions **(NEW IN 2.1)**.

---

## 33. Self-Hosting Invariant

SVP is a Python application. It will always be a Python application. The `toolchain.json`, `ruff.toml`, and `project_profile.json` govern the target project. SVP's own build toolchain is always `python_conda_pytest` with ruff and mypy for quality. The abstraction layer sits between SVP and the projects it builds, not between SVP and itself.

**Mode A pipeline/delivery split.** When SVP builds SVP, the pipeline toolchain and the delivery toolchain happen to coincide (both are Python/Conda/pytest/ruff/mypy). This coincidence must not collapse the separation. The pipeline reads `toolchain.json` for build commands. The git repo agent reads `project_profile.json` for delivery configuration. These are different code paths that produce the same result in Mode A and different results in Mode B. A blueprint that short-circuits by reading profile data during the build (or toolchain data during delivery) is architecturally wrong even if it produces correct output for the self-build case.

---

## 34. Glossary

The complete glossary of all SVP terms — pipeline architecture, four-layer orchestration, three-layer preference enforcement, quality gates, command groups, forking point tiers, document types, configuration files, agent roles, and Claude Code ecosystem concepts — is maintained in the SVP 2.1 Specification Summary (Document 3). Terms are defined in context throughout this document where they are first used.

---

*End of specification.*
---