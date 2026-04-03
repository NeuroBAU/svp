# SVP — Stratified Verification Pipeline

**Upstream import TYPE_CHECKING guards (NEW IN 2.2 -- Bug S3-47).** The stub generator must wrap non-stdlib imports (upstream dependency modules) in `if TYPE_CHECKING:` guards with `from __future__ import annotations` at the top of the file. Stubs never execute upstream code at runtime (all bodies are `raise NotImplementedError()`), so upstream imports are only needed for type annotations. This ensures stubs are importable regardless of workspace directory layout.
**R test source path resolution (NEW IN 2.2 -- Bug S3-48).** The infrastructure setup generates `tests/testthat/helper-svp.R`, which testthat auto-sources before test execution. This file provides `svp_source(path)` -- a helper function that resolves `source()` paths relative to the project root. R tests must use `svp_source("src/unit_N/stub.R")` instead of bare `source()`. This is the R equivalent of Python's `pyproject.toml pythonpath` setting. The helper uses `testthat::test_path()` (which returns `"tests/testthat"`) and navigates two levels up (`file.path(test_path(), "..", "..")`) to locate the project root deterministically.
**Cross-language upstream stub generation (NEW IN 2.2 -- Bug S3-49).** In mixed-language projects, `generate_upstream_stubs` must detect each upstream unit's language from `UnitDefinition.languages` and use the appropriate signature parser and stub generator for that language. The caller's `--language` flag applies only to the current unit, not to upstream dependencies. This is symmetric: Python callers with R upstreams use the R parser for R units, and R callers with Python upstreams use the Python parser for Python units.
**Delivery artifact completeness (NEW IN 2.2 — Bug S3-50).** The structural completion audit verifies Pass 2's delivered repo contains all root-level delivery artifacts present in Pass 1's repo: `environment.yml`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `LICENSE`, `.gitignore`. Any file present in Pass 1 but absent in Pass 2 is a delivery gap.
## Stakeholder Specification v9.0 (SVP 2.2)

**Date:** 2026-03-21
**Supersedes:** v8.33 (SVP 2.1)
**Build Tool:** SVP 2.1 (SVP 2.1 builds SVP 2.2)

---

## How to Read This Document

This is the complete, self-contained stakeholder specification for SVP 2.2. It contains every behavioral requirement and every architectural constraint needed to produce a correct blueprint. The blueprint author reads this one document.

**Part II** contains all behavioral requirements — what the system must do. **Part III** contains architectural strategy — how the blueprint should be structured. The blueprint author needs both parts. Other agents (checker, diagnostic, redo) primarily need Part II.

**Document length.** This specification is approximately 6,900 lines. For focused reading:
- **Stages 0-5 (unchanged from 2.1):** Sections 6-12. Read only if building from scratch or debugging stage-specific issues.
- **What's new in 2.2:** Search for `(NEW IN 2.2)` markers. Key new sections: 3.29-3.32 (orchestrator role definition), 7.7-7.8 (orchestrator oversight), 8.5 (Stage 2 oversight protocol), 10.15 (Stage 3 oversight protocol), 11.5 (regression adaptation), 35 (oracle), 40 (language framework), 41 (hard stop), 42 (unit architecture).
- **Bug catalog:** Section 24. Reference only -- consult when a specific failure pattern needs investigation.
- **Blueprint author:** Read Sections 30 and 32, plus the pre-blueprint checklists (Section 7.8).

**Change markers.** Sections unchanged from v6.0/v7.0 carry no marker. Sections modified by SVP 2.0 carry **(CHANGED IN 2.0)**. Sections modified or added by SVP 2.1 carry **(CHANGED IN 2.1)** or **(NEW IN 2.1)**. Sections modified or added by SVP 2.2 carry **(CHANGED IN 2.2)** or **(NEW IN 2.2)**. These markers are a scanning convenience — the full text is authoritative regardless.

**Separation of concerns with the blueprint.** This document describes behavior — what the human sees, what agents produce, what files the pipeline reads and writes. It does not prescribe function signatures, class hierarchies, or module boundaries. Where this spec must constrain the blueprint, it says so explicitly.

---

# PART II — BEHAVIORAL REQUIREMENTS

---

## 1. Purpose and Scope

SVP is a deterministically orchestrated, sequentially gated development system where a domain expert authors software requirements in natural language, and LLM agents generate, verify, and deliver a working software project. The pipeline's state transitions, routing logic, and stage gating are controlled by deterministic scripts; the LLM agents that operate within this framework are not themselves deterministic, but are maximally constrained by a four-layer architecture of behavioral instruction, recency-reinforced reminders, structured agent output, and hook-based enforcement (see Section 3.6). The human never writes code. The system compensates for the human's inability to evaluate generated code through multi-agent cross-checking, forced diagnostic discipline, and human decision gates concentrated where domain expertise — not engineering skill — is the deciding factor.

This document is the stakeholder specification for building SVP itself. It describes what SVP must do, for whom, under what constraints, and what constitutes success or failure. It is written with awareness of the Claude Code ecosystem in which SVP operates, and specifically with awareness of that ecosystem's actual capabilities and constraints.

### 1.1 When SVP Is Appropriate

SVP is designed for projects where at least two of the following conditions hold:

- The human cannot evaluate the generated code for correctness.
- The system is complex enough that errors can cascade silently between components.
- The cost of undetected errors is high relative to the cost of slower development.

SVP is not appropriate when the human can competently evaluate the output, when the project is small enough that manual testing suffices, or when speed matters more than defensive depth.

### 1.2 Language and Environment Constraints (CHANGED IN 2.0, CHANGED IN 2.2)

The pipeline itself is written in Python and uses conda, pytest, ruff, mypy, git, and setuptools. These pipeline tools are fixed and never change (Layer 1 -- see Section 3.25).

The delivered project can be written in Python, R (with Stan integration), or structured as a Claude Code plugin. The language and archetype are selected through the setup dialog (Area 0, Section 6.4). Support for additional languages is planned through the language extension archetype (Section 40.5). Target language tools (Layer 2) and delivery tools (Layer 3) are independent and per-language.

Claude Code plugins are a first-class project type (Section 40.7). All version control uses Git. The human interacts through typed conversation and explicit commands. The system runs inside Claude Code's terminal interface as a Claude Code plugin.

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

Different agents handle different roles. No agent both writes code and writes the tests for that code. No agent both authors and checks a document. The test agent and the implementation agent are always separate invocations with no shared context — the implementation agent never sees the tests. Both default to Opus-class models (see Section 22.1 for model configuration).

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
- You MUST NOT write to pipeline_state.json directly or batch multiple units. One action block per routing cycle.
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

**Command dispatch through update_state.py (NEW IN 2.2 -- Bug S3-14).** `update_state.py` accepts both `--phase` (for agent status dispatch) and `--command` (for command status dispatch). The routing script includes a `post` field in every `run_command` action block that invokes `update_state.py --command <command_type>`. This ensures the six-step action cycle is uniform for both agent and command actions.

**Two-branch routing invariant (NEW IN 2.1 — generalized Bug 21 fix).** Every sub-stage where an agent completion should trigger a different action (gate presentation or deterministic command) rather than re-invocation has two reachable states: (1) the agent has not yet been invoked or has not yet completed, and (2) the agent has completed (indicated by its terminal status line in `last_status.txt`). The `route()` function must distinguish these two states for every such sub-stage. In state (1), it emits an `invoke_agent` action. In state (2), it emits the appropriate next action — typically a `human_gate` for the corresponding gate, or a `run_command` for a deterministic check (as in quality gate retry sub-stages). If `route()` always returns the agent invocation without checking `last_status.txt`, the pipeline loops indefinitely re-invoking the agent after its work is already done.

This is a structural invariant, not a per-stage fix. The complete list of sub-stages governed by this invariant follows, in two groups distinguished by what the "done" branch emits:

**Gate-presenting entries** — the "done" branch emits a `human_gate` action:

- **Stage 0, `project_context`:** check for `PROJECT_CONTEXT_COMPLETE` or `PROJECT_CONTEXT_REJECTED` before presenting `gate_0_2_context_approval` (Section 6.3). `PROJECT_CONTEXT_REJECTED` is a gate-presenting status (pipeline_held) — the routing script presents the gate to let the human decide next steps.
- **Stage 0, `project_profile`:** check for `PROFILE_COMPLETE` before presenting `gate_0_3_profile_approval` (Section 6.4).
- **Stage 1, `stakeholder_spec_authoring` (sub_stage=None):** check for `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE` before presenting `gate_1_1_spec_draft` (Section 7.4). Note: `stakeholder_spec_authoring` is a descriptive label for this routing branch, not a literal sub-stage value; Stage 1 uses `sub_stage: None` throughout (see Section 22.4).
- **Stage 1, reviewer completion (sub_stage=None):** check for `REVIEW_COMPLETE` before presenting `gate_1_2_spec_post_review` (Section 7.4). When the stakeholder spec reviewer agent (invoked via FRESH REVIEW at Gate 1.1 or Gate 1.2) completes, `route()` must present Gate 1.2, not re-invoke the reviewer. Disambiguation from the dialog agent's status is by prefix: `REVIEW_COMPLETE` routes to Gate 1.2, while `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` route to Gate 1.1 (see Section 18.1, `REVIEW_COMPLETE` disambiguation).
- **Stage 2, `blueprint_dialog`:** check for `BLUEPRINT_DRAFT_COMPLETE` or `BLUEPRINT_REVISION_COMPLETE` before presenting `gate_2_1_blueprint_approval` (Section 8.1).
- **Stage 2, reviewer completion (`blueprint_dialog` sub-stage):** check for `REVIEW_COMPLETE` before presenting `gate_2_2_blueprint_post_review` (Section 8.2). When the blueprint reviewer agent (invoked via FRESH REVIEW at Gate 2.1 or Gate 2.2) completes, `route()` must present Gate 2.2, not re-invoke the reviewer. Disambiguation from the blueprint author's status is by prefix: `REVIEW_COMPLETE` routes to Gate 2.2, while `BLUEPRINT_DRAFT_COMPLETE` / `BLUEPRINT_REVISION_COMPLETE` route to Gate 2.1. Stage-level disambiguation (Stage 1 vs Stage 2) uses the current stage number from `pipeline_state.json` (see Section 18.1, `REVIEW_COMPLETE` disambiguation).
- **Stage 2, `alignment_check`:** check for `ALIGNMENT_CONFIRMED` or `ALIGNMENT_FAILED:*` before dispatching the alignment outcome (Gate 2.2 on confirmation, restart on failure) (Section 8.2). When `alignment_iterations >= iteration_limit` after an `ALIGNMENT_FAILED` result, present Gate 2.3 (`gate_2_3_alignment_exhausted`) instead of the normal failure transition.
- **Stage 2, `targeted_spec_revision` (NEW IN 2.2):** check for `SPEC_REVISION_COMPLETE` before transitioning back to `blueprint_dialog` (Section 8.3). When the stakeholder dialog agent completes in revision mode, `route()` transitions to `blueprint_dialog` for a fresh blueprint attempt, not re-invokes the revision agent.
- **Stage 5:** check for `REPO_ASSEMBLY_COMPLETE` before presenting `gate_5_1_repo_test` (Section 12.1).
- **Post-delivery debug loop, triage agent (reproducible):** check for `TRIAGE_COMPLETE: single_unit` or `TRIAGE_COMPLETE: cross_unit` before presenting Gate 6.2 (`gate_6_2_debug_classification`) (Section 12.18.4 Steps 1-2). Note: `TRIAGE_COMPLETE: build_env` does NOT present Gate 6.2 -- it routes directly to the build/environment repair agent via the fast path (Section 12.18.3).
- **Post-delivery debug loop, triage agent (non-reproducible):** check for `TRIAGE_NON_REPRODUCIBLE` before presenting Gate 6.4 (`gate_6_4_non_reproducible`) (Section 12.18.7).
- **Post-delivery debug loop, repair agent:** check for `REPAIR_COMPLETE`, `REPAIR_RECLASSIFY`, or `REPAIR_FAILED` (with retries exhausted) before dispatching the repair outcome (Sections 12.18.3, 12.18.6, 12.18.8, 18.1). `REPAIR_COMPLETE` routes to the success path: reassembly and debug completion (Section 12.18.6) -- it does NOT present Gate 6.3. `REPAIR_RECLASSIFY` and `REPAIR_FAILED` (with retries exhausted) present Gate 6.3 (`gate_6_3_repair_exhausted`) for the human to decide: RETRY REPAIR, RECLASSIFY BUG, or ABANDON DEBUG. Note: `REPAIR_FAILED` with retries remaining triggers re-invocation of the repair agent (not governed by this invariant -- see Section 18.1).
- **Post-delivery debug loop, test agent (regression test mode):** check for `REGRESSION_TEST_COMPLETE` before presenting Gate 6.1 (`gate_6_1_regression_test`) (Section 12.18.4 Step 5).
- **Redo profile sub-stages, `redo_profile_delivery`:** check for `PROFILE_COMPLETE` before presenting Gate 0.3r (`gate_0_3r_profile_revision`) (Section 13, `/svp:redo`).
- **Redo profile sub-stages, `redo_profile_blueprint`:** check for `PROFILE_COMPLETE` before presenting Gate 0.3r (`gate_0_3r_profile_revision`) (Section 13, `/svp:redo`).
- **Stage 7 (oracle), `dry_run` (NEW IN 2.2):** check for `ORACLE_DRY_RUN_COMPLETE` before presenting Gate 7.A (`gate_7_a_trajectory_review`) (Section 35.4).
- **Stage 7 (oracle), `green_run` (NEW IN 2.2, CHANGED IN 2.2 -- Bug S3-44):** check for `ORACLE_FIX_APPLIED` before presenting Gate 7.B (`gate_7_b_fix_plan_review`); check for `ORACLE_ALL_CLEAR` before exiting the oracle session directly via `complete_oracle_session` with exit_reason "all_clear" (Section 35.4). `ORACLE_ALL_CLEAR` must NOT present Gate 7.B.
- **E/F self-build, `pass_transition` after Pass 1 (NEW IN 2.2):** After Pass 1's Stage 5 completes for E/F archetypes (`is_svp_build` is true, `pass` is 1), present `gate_pass_transition_post_pass1` (Section 43.7). Options: PROCEED TO PASS 2, FIX BUGS.
- **E/F self-build, `pass_transition` after Pass 2 (NEW IN 2.2):** After Pass 2's Stage 5 completes (`pass` is 2), present `gate_pass_transition_post_pass2` (Section 43.7). Options: FIX BUGS, RUN ORACLE.
- **Post-Stage-1, `checklist_generation` (NEW IN 2.2):** check for `CHECKLISTS_COMPLETE` before advancing to Stage 2 (Section 7.8). If the Checklist Generation Agent has not yet completed, invoke it; if it has completed, advance to Stage 2 (blueprint_dialog).
- **Post-Stage-4, `regression_adaptation` (NEW IN 2.2):** check for `ADAPTATION_COMPLETE` or `ADAPTATION_NEEDS_REVIEW` before advancing to Stage 5 or presenting Gate 4.3 (`gate_4_3_adaptation_review`) (Section 11.5). `ADAPTATION_COMPLETE` advances directly to Stage 5; `ADAPTATION_NEEDS_REVIEW` presents Gate 4.3 for the human to review behavioral changes in regression tests.
- **Stage 3, diagnostic escalation (triggered by `fix_ladder_position: "diagnostic"`):** check for `DIAGNOSIS_COMPLETE` before presenting Gate 3.2 (`gate_3_2_diagnostic_decision`) (Section 10.11). Diagnostic escalation is not keyed on a named sub-stage value; it is triggered when the fix ladder position reaches `"diagnostic"` (see Section 10.10, ladder progression: `None -> fresh_impl -> diagnostic -> diagnostic_impl -> exhausted`). The sub-stage remains at `"green_run"` or `"implementation"` during the fix ladder; `route()` must check `fix_ladder_position` to determine whether the diagnostic agent should be invoked. When the diagnostic agent completes with `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec`, the routing script must present Gate 3.2 for the human to confirm the fix direction, not re-invoke the diagnostic agent.

**Gates not governed by the two-branch invariant.** Thirteen gate IDs from Section 18.4 are intentionally absent from the exhaustive list above: `gate_0_1_hook_activation` (Gate 0.1 is presented unconditionally at session start, not after an agent completion), `gate_6_5_debug_commit` (Gate 6.5 is presented after a deterministic commit preparation step, not after an agent completion), `gate_hint_conflict` (Gate H.1 is presented by the hint system when a conflict is detected, not as part of an agent-to-gate routing transition; it IS present in `GATE_VOCABULARY` and `ALL_GATE_IDS` because it has defined response options, but it is exempt from the two-branch routing pattern), `gate_2_3_alignment_exhausted` (Gate 2.3 is presented when the alignment iteration counter is exhausted after an `ALIGNMENT_FAILED` result -- the counter-based dispatch is deterministic and handled within `dispatch_agent_status`, not as a separate routing branch requiring a `last_status.txt` two-branch check), `gate_3_1_test_validation` (autonomous — defaults to TEST CORRECT, no human presentation, NEW IN 2.2; red-run exhaustion autonomously enters the implementation fix ladder per Section 10.9), `gate_4_1_integration_failure` (Gate 4.1 is presented after integration tests fail via a deterministic test command, not after an agent completion -- see Section 11.2.1 three-state dispatch), `gate_4_2_assembly_exhausted` (Gate 4.2 is presented when the assembly fix ladder retry counter is exhausted, not after an agent completion), `gate_5_2_assembly_exhausted` (Gate 5.2 is presented when Stage 5 assembly retries are exhausted, not after an agent completion), `gate_5_3_unused_functions` (Gate 5.3 is presented after a deterministic unused-function scan within Gate C structural validation, not after an agent completion), `gate_6_0_debug_permission` (Gate 6.0 is presented when a `/svp:bug` command is issued, not after an agent completion -- it is an entry gate for the debug loop), `gate_3_completion_failure` **(NEW IN 2.2)** (presented by the Stage 3 completion integrity check, a routing-time precondition), `gate_6_1a_divergence_warning` **(NEW IN 2.2)** (presented after post-fix structural validation detects workspace/repo divergence, not after an agent completion), and `gate_4_1a` **(NEW IN 2.2)** (presented at step 3 of the assembly fix ladder when human assist is needed). Note: `gate_pass_transition_post_pass1` and `gate_pass_transition_post_pass2` **(NEW IN 2.2)** ARE governed by the two-branch invariant and are listed above in the gate-presenting entries. These gates do not follow the agent-completion/gate-presentation pattern and therefore do not require a two-branch `last_status.txt` check in `route()`.

**Command-presenting entries** — the "done" branch emits a `run_command` action (a deterministic tool invocation, not a human gate):

- **Stage 3, `quality_gate_a_retry`:** check for `TEST_GENERATION_COMPLETE` before re-running Gate A tools (Section 10.12). If the test agent has not yet completed, re-invoke it; if it has, run the quality gate deterministic check.
- **Stage 3, `quality_gate_b_retry`:** check for `IMPLEMENTATION_COMPLETE` before re-running Gate B tools (Section 10.12). Same two-branch structure as Gate A retry.
- **Stage 3, `coverage_review`:** check for `COVERAGE_COMPLETE` (either `COVERAGE_COMPLETE: no gaps` or `COVERAGE_COMPLETE: tests added`) before dispatching the coverage review completion flow (Section 10.8). If the coverage review agent has not yet completed, invoke it; if it has completed with `COVERAGE_COMPLETE: tests added`, run the auto-format `run_command` actions within the `coverage_review` sub-stage before advancing to red-green validation; if it has completed with `COVERAGE_COMPLETE: no gaps`, advance directly to `unit_completion`. The auto-format commands execute within the `coverage_review` sub-stage's completion flow (Section 10.8), so `route()` must distinguish "agent not done" from "agent done" while the sub-stage is still `coverage_review`.
- **Stage 4:** check for `INTEGRATION_TESTS_COMPLETE` before running the integration test suite (Section 11.1). If the agent has not yet completed, re-invoke it; if it has, run the integration test command.

**State-advancing entries** — entries where the "done" branch performs an internal state transition (no gate, no command) and recursively calls `route()`:

- **Stage 2, `targeted_spec_revision` → `blueprint_dialog`:** After `SPEC_REVISION_COMPLETE`, advance `sub_stage` to `"blueprint_dialog"` and persist state before recursing. No gate is presented.
- **Stage 1/2, `checklist_generation` → Stage 2 advance:** After `CHECKLISTS_COMPLETE`, advance `stage` to `"2"` and `sub_stage` to `"blueprint_dialog"`. Persist before recursing.

State-advancing entries follow the route-level state persistence invariant (Section 3.6, Bug 42 fix): persist intermediate state to disk before any recursive `route()` call.

**Fix ladder dispatch (all 5 positions).** The implementation-side fix ladder (Section 10.10) has five positions, each with a distinct routing behavior:

| Position | Dispatch |
|----------|----------|
| `None` (no ladder active) | Green run `TESTS_FAILED` → advance to `fresh_impl`, re-invoke implementation agent |
| `fresh_impl` | Green run `TESTS_FAILED` → advance to `diagnostic`, invoke diagnostic agent |
| `diagnostic` | `DIAGNOSIS_COMPLETE` → present Gate 3.2 (`gate_3_2_diagnostic_decision`) |
| `diagnostic_impl` | Green run `TESTS_FAILED` → advance to `exhausted`, present Gate 3.2 |
| `exhausted` | Present Gate 3.2 unconditionally |

**Universal counter-exhaustion rule (NEW IN 2.2).** Every bounded retry counter in the pipeline follows the same pattern: when the counter reaches its limit, the routing script presents an exhaustion gate instead of re-invoking the agent or command. The exhaustion gates for each counter:

| Counter field | Limit | Exhaustion gate |
|---|---|---|
| `alignment_iterations` | `iteration_limit` (default 3) | `gate_2_3_alignment_exhausted` |
| `triage_refinement_count` | `iteration_limit` (default 3) | `gate_6_4_non_reproducible` |
| `repair_retry_count` | `iteration_limit` (default 3) | `gate_6_3_repair_exhausted` |
| `red_run_retries` | `iteration_limit` (default 3) | Autonomous TEST CORRECT → implementation fix ladder (no human gate, NEW IN 2.2) |
| Stage 4 assembly retries | 3 (fixed) | `gate_4_2_assembly_exhausted` |
| Stage 5 bounded fix cycle | `iteration_limit` (default 3) | `gate_5_2_assembly_exhausted` |
| Oracle fix verification | 2 (fixed) | Diagnostic map recording + exit report (not a human gate — oracle continues trajectory) **(NEW IN 2.2)** |
| Stage 6 reclassification | 3 (fixed) | RECLASSIFY option removed; only RETRY REPAIR and ABANDON DEBUG offered **(NEW IN 2.2)** |
| Break-glass retry per unit | 3 (fixed) | Unit auto-marked `deferred_broken` **(NEW IN 2.2)** |
| Oracle MODIFY TRAJECTORY | 3 (fixed) | Only APPROVE TRAJECTORY and ABORT offered **(NEW IN 2.2)** |

**Universal four-state test execution dispatch rule (NEW IN 2.2).** Every test execution `run_command` in the pipeline follows a four-state dispatch: `TESTS_PASSED` (advance), `TESTS_FAILED` (fix path), `TESTS_ERROR` (re-invoke producing agent once with error output), and retries exhausted (present exhaustion gate). The four states are universal; the stage-specific handlers are defined in Section 10.0. This rule applies to: Stage 3 red run, Stage 3 green run, Stage 4 integration tests, and Stage 5 human test (Gate 5.1).

**Session boundary cross-reference.** Session boundaries follow the state-persistence-before-cycling invariant (Section 16).

**Script execution invariant (NEW IN 2.2 — Bug S3-66).** Every deterministic script with a `main()` function must include `if __name__ == "__main__": main()` at the end. Every script invoked by the orchestrator from a non-scripts working directory must add its own directory to `sys.path` before bare imports. Without these, the script loads but produces no output, breaking the action cycle.

The blueprint must implement `route()` such that adding a new agent-to-gate sub-stage automatically requires a two-branch check. Regression tests must verify both branches (agent-not-done and agent-done) for every sub-stage in this list. A regression test that only verifies the agent invocation branch is incomplete.

**Universal compliance requirement (NEW IN 2.1 — Bug 43 fix).** The two-branch routing invariant must be applied universally in a single implementation pass, not incrementally as bugs are discovered in individual stages. Bugs 21, 41, and 43 demonstrated that applying the invariant piecemeal -- fixing only the stage where the bug was observed and leaving other stages unprotected -- leads to the same bug recurring in every unprotected stage. A universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`) must verify that EVERY entry in the exhaustive list above has a corresponding two-branch check in `route()`. The test must fail if a new gate-presenting or command-presenting entry is added to the spec without a routing-level check. Additionally, the test must verify cross-unit consistency: every key in `GATE_VOCABULARY` (routing module) appears in `ALL_GATE_IDS` (preparation module) and has a gate prompt handler. The test covers both the gate-presenting and command-presenting categories. This is the definitive structural test for the two-branch invariant -- it supersedes per-stage regression tests as the primary compliance mechanism, though per-stage tests remain as defense in depth.

**Gate ID consistency invariant (NEW IN 2.1 — Bug 41 fix).** Every gate ID that appears in routing dispatch tables (e.g., `GATE_RESPONSES` in the routing script) must also be registered in gate preparation registries (e.g., `ALL_GATE_IDS` in the preparation script). Conversely, every gate ID in a preparation registry should have a corresponding entry in the routing dispatch table. If a gate ID exists in the routing dispatch but not in the preparation registry, `prepare_gate_prompt()` raises a `ValueError` when the gate is triggered. If a gate ID exists in the preparation registry but not in the routing dispatch, the gate is never reachable. Both conditions are bugs. A structural test must verify that the set of gate IDs in `GATE_RESPONSES` is identical to the set of gate IDs in `ALL_GATE_IDS`. This test must be a carry-forward regression test. The complete gate ID vocabulary is enumerated in Section 18.4.

**Gate reachability and dispatch exhaustiveness invariant (NEW IN 2.1 -- Bugs 65-69, 73 fix, P10 root cause).** Every gate in GATE_VOCABULARY must have a reachable code path in `route()` that presents it. Every response option in every gate must produce a meaningful state transition in `dispatch_gate_response` (not a bare `return state`), unless the response is an intentional two-branch no-op where the gate response written to `last_status.txt` drives the next routing decision. Intentional two-branch no-ops must be explicitly documented as such in the Tier 3 contract. This invariant applies across ALL pipeline stages (Stages 0-5 and the debug loop) -- not just the stage where a particular bug was discovered. Bugs 65-69 demonstrated that the same disease (P10: Error-Path Contract Omission) affected every stage independently. A structural regression test must verify that every gate in GATE_VOCABULARY is reachable from `route()` for at least one valid pipeline state. Gates that are intentionally triggered by external mechanisms (e.g., `gate_hint_conflict` triggered by the orchestration layer, `gate_0_1_hook_activation` presented unconditionally at session start) must be documented as exceptions in the test.

**Regression test target invariant (NEW IN 2.1 — Bug 74 fix).** All regression tests must import from and test the real implementation modules (e.g., `routing`, `pipeline_state`, `state_transitions`), never from stubs (`src/unit_N/stub.py`). Stubs are simplified implementations used during the build process; they may have correct behavior that the real scripts lack (or vice versa). Testing stubs instead of real scripts creates a false-pass scenario where regression tests pass but the actual deployed code is broken. This invariant applies to ALL projects built by SVP, not just SVP itself. The blueprint checker must verify that no regression test file contains `from src.unit_` imports. The blueprint reviewer must include this check in its review checklist.

**Mode isolation invariant (NEW IN 2.1 — Bug 86 fix).** When an agent operates in multiple modes within the same stage (e.g., setup agent's context mode and profile mode in Stage 0), three requirements must hold: (1) The routing script must pass a mode identifier to the preparation script (e.g., via `--context` argument). (2) The preparation script must inject an explicit mode signal into the agent's task prompt that unambiguously identifies which mode to execute. (3) The routing guard for each mode must only accept the terminal status line specific to that mode — not artifact existence, carry-over statuses, or generic success indicators. Violation of any of these three requirements can cause the agent to execute the wrong mode and bypass required interactions.

**Route-level state persistence invariant (NEW IN 2.1 — Bug 42 fix).** Any `route()` branch that performs an in-memory state transition (via a `complete_*` or `advance_*` helper function) and then recursively calls `route()` or returns an action block for a different sub-stage must persist the intermediate state to disk (via `save_state()`) before returning the action block. Without persistence, the POST command of the returned action block loads stale state from disk via `update_state.py`, losing the in-memory transition. This creates an invisible state rollback: the action block executes against the new state, but `update_state.py` overwrites it with the old state, and subsequent routing calls see the old state — potentially creating infinite loops. Structural tests must verify that every `complete_*` or `advance_*` call in `route()` is followed by a `save_state()` call before any recursive `route()` call or action block return.

**Exhaustive dispatch_agent_status invariant (NEW IN 2.1 — Bug 42 fix, CHANGED IN 2.1 — Bugs 44, 46 fix).** Every agent type registered in `dispatch_agent_status` must explicitly handle its success status line with a state transition that advances the pipeline (modifying at least one of `stage`, `sub_stage`, or a state flag). A bare `return state` (no field changes) is only valid when the agent's completion genuinely does not require a stage/sub-stage change — for example, slash-command-initiated agents (help, hint) whose completion returns control to the current pipeline position. For agents on the main pipeline path (reference indexing, git repo agent, blueprint checker, triage agent, repair agent, test agent, coverage review agent, etc.), a bare `return state` is a bug — it leaves the pipeline stuck at the current position with no mechanism to advance. A structural test must verify that every main-pipeline agent type in `dispatch_agent_status` modifies at least one state field in its success handler. The routing function and dispatch function must have consistent null-handling for `sub_stage`: when routing treats `None` as equivalent to a named sub_stage (e.g., `test_generation`), the dispatch must also accept `None` for that agent type (Bug 44 fix).

**Exhaustive dispatch_command_status invariant (NEW IN 2.1 — Bug 45 fix, CHANGED IN 2.1 — Bug 65 fix).** Every `dispatch_command_status` handler for `test_execution` must produce a state transition for the expected outcome at each sub-stage. No-op returns (`return state`) are invalid for `red_run` (`TESTS_FAILED` must advance to `implementation`) and `green_run` (`TESTS_PASSED` must advance to `coverage_review`). A `dispatch_command_status` handler that returns state unchanged for a status line that requires advancement is a bug — it leaves the pipeline stuck re-running the same command indefinitely. A structural test must verify that `dispatch_command_status` for `test_execution` advances `sub_stage` for each expected status/sub_stage combination.

**Extended exhaustive dispatch table (Bug 65 fix).** The invariant above covers only two happy-path cases. The complete dispatch table for ALL (phase, sub_stage, status) combinations in Stage 3 is:

| Phase | Sub-stage | Status | Required transition |
|-------|-----------|--------|-------------------|
| `stub_generation` | `None` / `stub_generation` | `COMMAND_SUCCEEDED` | advance to `test_generation` |
| `test_execution` | `red_run` | `TESTS_FAILED` | advance to `implementation` |
| `test_execution` | `red_run` | `TESTS_PASSED` | increment `red_run_retries`; if < limit: regenerate tests (`test_generation`); if >= limit: autonomous TEST CORRECT → implementation fix ladder (NEW IN 2.2) |
| `test_execution` | `green_run` | `TESTS_PASSED` | advance to `coverage_review` |
| `test_execution` | `green_run` | `TESTS_FAILED` | advance fix ladder: `None` -> `fresh_impl` (implementation); `fresh_impl` -> `diagnostic` (implementation); `diagnostic_impl` -> exhausted (`gate_3_2`) |
| `quality_gate` | `quality_gate_a` / `quality_gate_b` | `COMMAND_SUCCEEDED` | advance to next sub-stage (`red_run` / `green_run`) |
| `quality_gate` | `quality_gate_a` / `quality_gate_b` | `COMMAND_FAILED` | advance to retry sub-stage |
| `unit_completion` | `unit_completion` | `COMMAND_SUCCEEDED` | complete unit, advance to next |

A bare `return state` (no-op) is not a valid contract outcome for any entry in this table. Every cell must produce a distinct state transition.

**Stage 5 command dispatch completeness (NEW IN 2.2 — Bug S3-11).** `dispatch_command_status` must handle ALL command types emitted by the routing script, including `structural_check` and `compliance_scan` for Stage 5. Missing handlers cause crashes when the routing advances to these sub-stages.

**Gate dispatch routing corrections (NEW IN 2.2 — Bug S3-17).** Three gate dispatch corrections: (1) Gate 1.1 FRESH REVIEW must route to stakeholder_reviewer, not stakeholder_dialog. The dispatch handler must set `sub_stage` to `"spec_review"`, which `_route_stage_1` maps to invoke the stakeholder_reviewer agent. (2) Gate 5.1 TESTS FAILED must re-enter bounded fix cycle by resetting sub_stage to `None` (which falls through to re-invoke git_repo_agent), not loop to Gate 5.1 by setting sub_stage to `"repo_test"`. (3) gate_pass_transition_post_pass1 PROCEED TO PASS 2 must reject when `deferred_broken_units` is non-empty, raising a ValueError to prevent advancing with unresolved broken units.

**Routing loop prevention (NEW IN 2.2 — Bugs S3-18, S3-19, S3-20, S3-21).** Every agent invocation in the routing script must include a two-branch check: if `last_status` contains the agent's completion status, advance to the next phase/gate; otherwise invoke the agent. Without this check, completed agents are re-invoked indefinitely. Specific instances: (1) Debug reassembly phase must check for `REPO_ASSEMBLY_COMPLETE` and advance to `regression_test` phase. (2) Diagnostic escalation in Stage 3 implementation must check for `DIAGNOSIS_COMPLETE` and present Gate 3.2. (3) Debug repair phase must transition to `reassembly` phase on `REPAIR_COMPLETE`, not directly invoke `git_repo_agent` (which would leave the phase as `repair` after assembly completes, causing a loop). (4) `dispatch_command_status` must handle ALL command types emitted by `_route_debug`: `lessons_learned` (transitions debug phase to `commit`), `debug_commit` (completes the debug session), and `stage3_reentry` (sets `sub_stage` to `stub_generation` for unit rebuild).

**COMMAND/POST separation invariant (NEW IN 2.1 — Bug 47 fix).** COMMAND fields in routing action blocks must never embed state update calls (`update_state.py`). State updates are exclusively the responsibility of POST commands. If a COMMAND embeds a state update call and a POST command also invokes `update_state.py` for the same phase, the state update runs twice, causing a `TransitionError` on the second invocation. The COMMAND should only produce output, write status files, or execute deterministic tool commands; the POST command handles state transitions. This applies to all routing action blocks, not just `unit_completion` (though Bug 47 was discovered there).

**CLI argument enumeration invariant (NEW IN 2.1 — Bug 48 fix, STRENGTHENED — Bug 49 fix).** Any blueprint Tier 2 function signature that accepts `argv` and uses `argparse` internally must enumerate every `add_argument` call (argument name, type, required/optional) in the Tier 2 invariants section. Prose-only descriptions in Tier 3 are insufficient for CLI contracts. Without explicit enumeration, the implementation agent has no way to determine which arguments to implement, leading to missing arguments, incorrect names, or wrong semantics. This invariant applies to ALL units that produce CLI entry points, not just Unit 24. The blueprint checker must verify compliance across all units. Units with CLI entry points as of SVP 2.1: Unit 6 (`main`), Unit 7 (`main`), Unit 9 (`main`), Unit 10 (`update_state_main`, `run_tests_main`, `run_quality_gate_main`), Unit 23 (`compliance_scan_main`), Unit 24 (`parse_args`). A structural regression test (`test_bug49_argparse_enumeration.py`) verifies that every CLI entry point accepts its documented arguments.

**Session cycling.** The SVP launcher manages automatic session cycling at every major pipeline transition. The mechanism: the main session writes a restart signal file and exits; the launcher detects it and relaunches Claude Code. The new session reads CLAUDE.md, runs the routing script, and picks up from the state file. See Section 16.

**State management.** The routing script predetermines the POST command at the time it specifies the action. State-update scripts validate preconditions before writing new state. This makes the scripts — not the hooks and not the LLM — the primary stage-gating mechanism.

**Orchestrator Pipeline Fidelity Invariant (NEW IN 2.2).** The orchestrator executes exactly one action block per routing cycle. After executing an action block, the orchestrator MUST call the routing script before taking any other pipeline action. The orchestrator MUST NOT:

- Write to `pipeline_state.json` directly. All state changes go through `update_state.py`. This is enforced by a PreToolUse hook (Section 19).
- Combine multiple units into a single agent invocation.
- Skip any sub-stage in the per-unit cycle (stub_generation → test_generation → quality_gate_a → red_run → implementation → quality_gate_b → green_run → coverage_review → unit_completion).
- Invoke `update_state.py` with a phase that does not match the current pipeline state. `update_state.py` validates that the `--phase` argument is a legal transition from the current state and rejects mismatches.
- Batch operations across multiple units (e.g., generating stubs for units 16-29 in one command).

There are no light units. Every unit — including agent definition units that export only string constants — receives the full verification cycle. The verification cycle exists to catch integration errors, namespace mismatches, and contract drift that occur in any unit regardless of perceived complexity.

**Orchestrator Self-Escalation Invariant (NEW IN 2.2).** During E/F self-builds, the orchestrator monitors for loop conditions: the same action dispatched 3 or more consecutive times with no pipeline state change. When detected, the orchestrator self-escalates to break-glass mode (Section 43.9) without waiting for the routing script to emit `break_glass`. This is a narrow, bounded self-escalation — it does not grant the orchestrator general authority to modify pipeline flow. It is a safety valve for routing script bugs, which are likely during E/F builds. The loop detection is mechanical (count consecutive identical actions, check for state changes), not a judgment call.

**`deferred_broken` Unit Status (NEW IN 2.2).** A unit may be marked `deferred_broken` by the orchestrator during break-glass handling (Section 43.9). This status means the unit failed during the current pass and was deferred by human decision. A `deferred_broken` unit is excluded from the current pass's progress tracking (other units continue normally) but blocks pass completion — the pass cannot complete until all `deferred_broken` units are resolved (either fixed via Stage 6 after the pass, or explicitly acknowledged by the human at the post-Stage-5 transition gate). The `deferred_broken_units` array in pipeline state tracks these units. This status is only used during E/F self-builds.

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

Every project built by SVP is automatically formatted, linted, and type-checked during the build. Quality is a pipeline guarantee, not an opt-out feature. Deterministic quality tools run at defined points in the verification cycle:

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

2. **LLM-driven review checks at Gates 1.1/1.2 and 2.1/2.2 (authoring time).** The stakeholder spec reviewer, blueprint checker, and blueprint reviewer agents each have mandatory review checklists baked into their agent definitions. These checklists require the review agents to explicitly verify downstream dependency analysis, contract granularity, per-gate dispatch contracts, call-site traceability, re-entry invalidation, and gate reachability (for every gate in GATE_VOCABULARY, verify there exists a route() code path that presents it; for every gate response option, verify dispatch_gate_response produces a state transition or is documented as an intentional two-branch no-op -- Bugs 65-69 P10 fix). The stakeholder spec reviewer applies these items at the requirements level (see Section 7.4.1 for spec-level interpretation); the blueprint checker and blueprint reviewer apply them at the architecture level (see Section 8.2.1 for blueprint-level interpretation). The checklists are part of the agent's system prompt and run automatically during every spec review and blueprint review -- no human action required to activate them.

The two mechanisms are complementary: the review checklists catch the root cause (spec/blueprint gaps) at authoring time; the Gate C check catches the symptom (dead code) at assembly time. Neither alone is sufficient. The review checklists are LLM-driven and advisory (the review agent flags issues but does not block progress mechanically); the Gate C check is deterministic and presents a human gate.

### 3.21 Structural Completeness Test Suite (NEW IN 2.1 -- Bug 71 fix)

The regression test file `tests/regressions/test_bug71_structural_completeness.py` provides a third enforcement layer: 14 automated guard tests that verify declaration-vs-usage consistency across the pipeline's constants, dispatch tables, routing functions, and state transitions. These tests run as part of the standard pytest suite and catch classes of bugs that neither LLM review nor Gate C can detect (e.g., a gate declared in GATE_VOCABULARY but missing from route(), or a status line declared in AGENT_STATUS_LINES but not handled by dispatch).

The 14 techniques are: (1) gate vocabulary vs route reachability, (2) response options vs dispatch handlers, (3) exported functions vs call sites, (4) stub vs script constant synchronization, (5) skipped (narrative-only), (6) per-agent loading matrix, (7) agent status lines vs dispatch, (8) known agent types vs route invocations, (9) debug phase transitions vs route handlers, (10) sub-stages vs route branches, (11) fix ladder positions vs route context, (12) command status patterns vs phase handlers, (13) phase-to-agent map vs known phases, (14) debug phase transitions vs known phases.

This suite must be maintained as the pipeline evolves: any new gate, agent type, status line, sub-stage, debug phase, or fix ladder position must be reflected in the corresponding stub constants, script constants, and structural tests.

**(CHANGED IN 2.2)** The structural completeness test suite includes dispatch exhaustiveness verification: every full language (not component-only) in `LANGUAGE_REGISTRY` must have entries in all six dispatch tables. Component-only languages must have entries in the dispatch tables listed in their `required_dispatch_entries` field. `validate_dispatch_exhaustiveness()` runs as part of Stage 5 structural validation (Gate C), not only during import-time checks.


### 3.22 Oracle Simulation-Only Constraint (NEW IN 2.2)

The `/svp:oracle` post-delivery acceptance testing tool (Section 35) creates a nested pipeline session for verification purposes only. This is a first-class architectural constraint, not a usage guideline:

1. **No production deliverables.** The nested pipeline run produces no usable deliverable. Any repository, workspace, or artifact generated by the nested session is a disposable verification output.
2. **Verification, not production.** The oracle's purpose is to verify that the pipeline behaves correctly, not to produce a project. The nested session exists to exercise routing paths, gate dispatch, and agent orchestration under controlled conditions.
3. **Disposable artifacts.** After the oracle session concludes, the nested session's artifacts may be discarded without loss. No downstream process, consumer, or human should depend on oracle-generated outputs.

This constraint is enforced by the oracle's architecture: the nested session runs in an isolated workspace, and no mechanism exists to promote its outputs to production status.

### 3.23 Generalized Structural Completeness Checking -- Four-Layer Defense (NEW IN 2.1 -- Bug 72 fix)

SVP employs a four-layer defense system for structural completeness that works for any Python project, not just SVP itself:

**Layer 1 -- Blueprint checker prompt update.** The blueprint checker agent definition includes a mandatory registry completeness checklist item. The checker must identify every registry, vocabulary, enum, or dispatch table declared in the blueprint and verify that every declared value has a corresponding handler/branch contract in at least one unit. A registry value with no handler contract is an alignment failure.

**Layer 2 -- Integration test author prompt update.** The integration test author agent definition includes a requirement to generate registry-handler alignment tests. For every registry, dispatch table, vocabulary, and enum-like constant in the codebase, the integration test author generates a pytest test that collects all declared values via AST, collects all values handled in the corresponding dispatch logic, and asserts bidirectional coverage.

**Layer 3 -- Deterministic structural check script.** `scripts/structural_check.py` is a project-agnostic AST scanner that performs four high-confidence, low-false-positive checks: (1) dict registry keys never dispatched, (2) enum values never matched, (3) exported functions never called, (4) string dispatch gaps (registry-linked). The script uses only stdlib imports (ast, json, pathlib, argparse, sys) and has no project-specific knowledge. It runs as a Stage 5 sub-stage (`structural_check`) between `repo_test` and `compliance_scan`. CLI: `python scripts/structural_check.py --target <path> [--format json|text] [--strict]`. In `--strict` mode, any findings produce exit code 1.

**Layer 4 -- Triage agent pre-computation.** The bug triage agent task prompt includes structural check results (pre-computed by `prepare_task.py` running `structural_check.py` against the delivered repo). The triage agent reviews these results in Step 0 before reproducing the bug. If a structural finding directly explains the reported symptom, the agent classifies immediately. The triage agent definition also includes a Registry Diagnosis Recipe for manual investigation.

The four layers are complementary: Layer 1 catches gaps at blueprint authoring time (LLM-driven), Layer 2 generates persistent regression guards (test-driven), Layer 3 catches gaps at assembly time (deterministic), and Layer 4 accelerates post-delivery debugging (diagnostic).

### 3.24 Orchestrator as Spec Quality Gate (NEW IN 2.2)

The orchestrator (main session) is not a passive relay between the human and the stakeholder dialog agent. During Stage 1, the orchestrator actively verifies that every decision made during the Socratic dialog is correctly reflected in the spec draft. The orchestrator maintains a decision ledger, constructs a verification checklist, runs it against every draft, and catches contradictions, omissions, and agent drift before the human reviews the spec. This ensures that the spec is a faithful encoding of the dialog — not an approximation filtered through agent interpretation.

The orchestrator also runs two quality passes on every completed draft: a contradiction detection pass (verifying numeric and behavioral consistency across all sections) and a staleness/redundancy pass (identifying inherited statements that are no longer accurate and unnecessary duplication). Both passes are delegated to dedicated subagents with fresh context to prevent the orchestrator from normalizing inconsistencies through familiarity.

The quality gate principle extends beyond Stage 1. The orchestrator has stage-specific oversight protocols for Stages 2 and 3 as well: Section 8.5 defines the Stage 2 blueprint oversight protocol (23-item detection checklist), and Section 10.15 defines the Stage 3 per-unit and cross-unit oversight protocols. In every stage, the orchestrator detects but does not fix — all corrections flow through the appropriate agents via the routing script. See Section 20.4 for the consolidated per-stage reference.

### 3.25 Three-Layer Toolchain Separation (NEW IN 2.2)

SVP distinguishes three independent toolchain layers. No function may read across layers.

**Layer 1 — Pipeline Toolchain (fixed forever):** The tools SVP itself runs as. Python, conda, pytest, ruff, mypy, git, setuptools. Invariant across all projects and all SVP versions. Read from SVP source code and `svp_config.json`.

**Layer 2 — Build-Time Target Quality (per-language, pipeline-controlled):** The tools the pipeline uses to check agent-generated code in the target language during Stages 3-4. The human never interacts with these directly. Gate structure (A/B/C) is invariant; gate composition varies by language. Read from the language-specific toolchain file.

**Layer 3 — Delivery Toolchain (fully user-configurable):** What the delivered project presents to its end user. Chosen through the setup agent dialog. Completely independent from Layers 1 and 2. A delivered Python project might use `pip + requirements.txt + black + flake8` while the pipeline built it with `conda + ruff + mypy`. Read from `project_profile.json`.

**Separation Invariant:** No function reads pipeline quality from the profile. No function reads delivery quality from the toolchain. A structural regression test enforces this by AST-scanning import paths.

### 3.26 Dispatch Exhaustiveness Invariant (NEW IN 2.2)

Every language registered in the language registry must have a matching entry in ALL six dispatch tables (signature parsing, stub generation, test output parsing, quality gate execution, project assembly, compliance scanning). Missing entries are caught at two levels:

1. **Import-time validation:** The compliance module validates every registry entry has matching keys in all six dispatch tables. Produces a descriptive error listing exactly which entries are missing.
2. **Structural regression test:** AST-based scan finds every dispatch table dict, extracts keys, compares against registry keys. Catches gaps even if import-time validation is bypassed.

A language with missing dispatch entries cannot be used to build a project. The error message serves as a checklist for implementors.

### 3.27 Component Language Constraint (NEW IN 2.2)

A component language (e.g., Stan) is a language that cannot be the primary project language — it always requires a host language to function. Component languages:
- Have `is_component_only: true` in their registry entry
- Have `compatible_hosts` listing which languages can host them
- Must have an explicit communication mechanism declared in the profile (e.g., `cmdstanr` for Stan hosted by R)
- Do NOT need all six dispatch table entries — they need only the entries relevant to their role (e.g., Stan needs a quality runner for syntax checking but not a full project assembler)

**Distinction from secondary languages.** A component language (e.g., Stan) is an incomplete language that depends on a host. A secondary language in a `"mixed"` archetype project (e.g., R in a Python-primary mixed project) is a full language with complete dispatch table entries — it can serve as primary in a different project. The `"mixed"` archetype uses `language.secondary` (not `language.components`) because the semantics are different: secondary languages are peers, not dependents. See Section 40.6.

### 3.28 Dynamic Registry Construction [PLACEHOLDER] (NEW IN 2.2)

SVP 2.2 ships with built-in language support for Python and R. The dynamic registry construction mechanism described below is the intended design for language extension via self-build (archetype `"svp_language_extension"`, Option E in the Area 0 selector — see Section 43.3). Dynamic registry construction will be fully specified and activated in a future round. Until then, only built-in languages are supported as primary languages.

*Intended design (not yet active):*

For languages not built into SVP (neither Python nor R), the setup agent constructs a registry entry through Socratic dialog. The dialog-constructed entry must pass the same validation as built-in entries. The setup agent:
1. Asks the human about the language's ecosystem (file extension, environment manager, test framework, linter, formatter, type checker, build system, error indicators)
2. Asks for agent guidance ("How should I describe writing [language] code to an LLM?")
3. Constructs a registry entry and validates it
4. Writes it to the project workspace as `language_registry_extensions.json`

Dynamic entries are project-scoped — they exist only in the project workspace, not in the SVP plugin itself.

### 3.29 The Orchestrator: Critical Importance (NEW IN 2.2)

The orchestrator (main session) is the single session with full pipeline visibility. It has access to: the stakeholder spec, the blueprint, all agent outputs, all test results, the pipeline state file, the build log, and the project workspace. Unlike stateless subagents that are spun up for a single task and terminated, the orchestrator persists across the entire build and accumulates context about every decision, every failure, and every fix.

This combination — full visibility plus persistent authority — makes the orchestrator simultaneously the most powerful component in the pipeline and the most dangerous when it goes off the rails. It is SVP's single point of failure. A well-functioning orchestrator enables the pipeline to build correct software; a malfunctioning orchestrator can silently corrupt the build in ways that no downstream check can catch, because the orchestrator controls which checks run and how their results are interpreted.

### 3.30 Orchestrator Failure Modes (NEW IN 2.2)

Five cataloged failure modes, all observed during the SVP 2.1 Stage 3 incident:

1. **Scope creep.** The orchestrator starts "helping" by performing tasks that agents should perform. It writes a stub, fixes a test, patches an import — each individually small, collectively devastating because they bypass the verification cycle.

2. **Role conflation.** The orchestrator merges oversight (diagnosing problems, reviewing outputs, running checklists) with execution (writing code, modifying files, running implementations). These roles must remain separated: oversight informs what the routing script should dispatch next; execution is what agents and scripts do when dispatched.

3. **Rationalized pipeline bypass.** The orchestrator decides that certain units are "light" or "trivial" and batches them, skips sub-stages, or combines agent invocations. The rationalization sounds reasonable ("these are just string constants") but eliminates the verification steps that catch integration errors.

4. **Direct state manipulation.** The orchestrator writes to `pipeline_state.json` directly instead of going through `update_state.py`. This bypasses transition validation, precondition checks, and build log recording.

5. **Builder modification.** The orchestrator encounters a bug in a `scripts/*.py` file and fixes it directly instead of invoking the Hard Stop Protocol (Section 41). This is particularly dangerous because it modifies the pipeline's own infrastructure mid-build, potentially introducing cascading failures.

### 3.31 The Two Principles (NEW IN 2.2)

Two principles govern the orchestrator's role. Together they define what the orchestrator SHOULD do. The enforcement mechanisms (below) catch violations when it doesn't.

**Principle 1: Oversee with the full picture, never execute directly.** The orchestrator uses its unique full-pipeline visibility to diagnose problems, prescribe solutions, and review outputs. It never writes source files, runs implementations, generates tests, or modifies pipeline state. Oversight and execution are structurally separate roles.

**Principle 2: All execution through subagents or deterministic scripts.** Every action that modifies the workspace, the pipeline state, or the build artifacts flows through either a subagent (invoked via the Task tool) or a deterministic script (invoked via the routing script's action block). The orchestrator initiates these actions by following the routing script's instructions — it does not perform them itself.

**Enforcement mechanisms.** Six mechanisms catch violations of these principles:
- Section 3.6, line 276: Orchestrator Pipeline Fidelity Invariant — one action block per routing cycle, no direct state writes, no batching, no sub-stage skipping.
- Section 10.13: Stage 3 Completion Integrity Check — verifies all 9 sub-stages ran for every unit.
- Section 22.6: Build Log — creates an audit trail of every routing decision and state transition.
- Section 19.2: PreToolUse hook — blocks direct writes to `pipeline_state.json`.
- Section 7.7.8: Pipeline Fidelity Constraint — no light units, Hard Stop Protocol for builder bugs.
- CLAUDE.md: Six-step action cycle — structural constraint on orchestrator behavior per action block.

These principles define what the orchestrator SHOULD do; the enforcement mechanisms catch violations when it doesn't. The principles are proactive (preventing the failure modes in Section 3.30); the enforcement mechanisms are reactive (detecting violations after the fact).

### 3.32 Autonomous Operation Definition (NEW IN 2.2)

**Autonomous operation means:** the orchestrator makes gate decisions without human input during sequences where the routing script specifies autonomous dispatch.

**Autonomous operation does NOT mean:**
- Bypassing pipeline steps.
- Batching multiple units into a single agent invocation.
- Skipping agents or sub-stages.
- Writing to pipeline state directly.
- Modifying builder scripts.
- Combining oversight and execution in a single action.

**Bounded by the routing script.** Every orchestrator action originates from a routing script action block. Between action blocks, the orchestrator performs oversight only: running checklists (Sections 8.5, 10.15), detecting issues, and preparing for the next routing cycle. Corrective action for detected issues goes through the routing script — the orchestrator does not fix issues directly.

### 3.33 Oracle E-Mode/F-Mode Split (NEW IN 2.2)

The oracle (`/svp:oracle`, Section 35) operates in one of two primary modes for E/F self-builds, inferred from the project's `self_build_scope`:

- **E-mode (product testing):** Verifies that the product built by SVP works correctly. For language extensions, this means the new language pipeline produces correct projects — dispatch tables route correctly, toolchain integration works, assembly produces valid deliverables. Test targets: language dispatch, toolchain integration, assembly, delivery. Test projects: GoL re-expressions produced by the E build (Section 43.3).

- **F-mode (machinery testing):** Verifies that the pipeline machinery itself works correctly. For architectural changes, this means routing, state transitions, gates, and orchestration function as specified. Test targets: routing path coverage, gate reachability, state machine integrity. Test project: SVP `docs/` (the pipeline rebuilding itself).

**Human selects mode via test project.** The human decides which mode to use on each `/svp:oracle` invocation by selecting the test project. GoL test project → E-mode (product testing). SVP `docs/` → F-mode (machinery testing). There is no mode state in pipeline state, no sequencing enforcement, and no automatic mode selection. The human is the pilot.

**Run ledger as cross-invocation memory.** If this is the first `/svp:oracle` invocation (empty run ledger), the oracle plans from scratch. If prior runs exist, the oracle reads the run ledger to retrieve relevant events — what was tested, what was found, what was fixed — and factors this into trajectory prioritization. The four-phase structure (dry run, Gate A, green run, exit) is unchanged regardless of mode or invocation count.

This is an architectural constraint: the oracle's verification targets are fundamentally different for product testing vs. machinery testing. A single undifferentiated oracle would either test everything shallowly or miss the domain-specific paths that matter most for each archetype.

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

## 5. Pipeline Overview (CHANGED IN 2.2)

SVP proceeds through six main sequential stages (0-5) plus one transitional phase (Pre-Stage-3). After Stage 5 completes, the project is delivered. Two post-delivery tools are available: Stage 6 (`/svp:bug`) for debugging any project, and Stage 7 (`/svp:oracle`) for acceptance testing SVP itself (when `is_svp_build` is true). See Section 35 for Stage 7 details. Each phase must complete before the next begins. If a document-level problem is discovered at any phase, the pipeline restarts from the appropriate earlier stage.

**(CHANGED IN 2.2) Self-build lifecycle (E/F archetypes).** For self-build archetypes (`"svp_language_extension"` and `"svp_architectural"`), the pipeline includes a two-pass lifecycle. Pass 1 (scaffolding) builds the new SVP through Stages 0-5. Pass 2 (production) rebuilds through an orchestrator-driven nested session from Pre-Stage-3 through Stage 5 using the Pass 1 deliverable as the active plugin. The delivered product is Pass 2's output — Pass 1's output is scaffolding, not the delivery. Stage 7 (`/svp:oracle`) is available only after Pass 2 completes. See Section 43 for the full two-pass protocol.

```
E/F Self-Build Lifecycle:
Pass 1 (Scaffolding):  Stages 0-5 under SVP N
Transition:            Bug summary → Human chooses Stage 6 or Pass 2
Pass 2 (Production):   Pre-Stage-3 through Stage 5 under SVP N+1
Transition:            Bug summary → Human chooses Stage 6 or Stage 7
```

```
Stage 0: Setup
Stage 1: Stakeholder Spec Authoring
Stage 2: Blueprint Generation and Alignment
Pre-Stage-3: Infrastructure Setup
Stage 3: Unit-by-Unit Verification
Stage 4: Integration Testing
Stage 5: Repository Delivery
```

**Language dispatch tables (NEW IN 2.2).** SVP 2.2 uses six per-language dispatch tables, each owned by a specific unit. These tables are referenced throughout the stage sections below and defined in Section 40.3:

| Dispatch Table | Owning Unit | Consumed During |
|---------------|-------------|-----------------|
| `SIGNATURE_PARSERS` | Unit 9 | Stage 3 (stub generation) |
| `STUB_GENERATORS` | Unit 10 | Stage 3 (stub generation) |
| `TEST_OUTPUT_PARSERS` | Unit 14 | Stage 3 (test execution) |
| `QUALITY_RUNNERS` | Unit 15 | Stage 3 (quality gates) |
| `PROJECT_ASSEMBLERS` | Unit 23 | Stage 5 (repository assembly) |
| `COMPLIANCE_SCANNERS` | Unit 28 | Stage 5 (compliance scan) |

All six tables follow the same protocol: look up the language key, call the registered function. See Section 40.3 for the dispatch protocol and Section 42 for the unit DAG.

After Stage 5 completion, the pipeline supports re-entry via `/svp:bug` for post-delivery bug investigation (see Section 12.18), and via `/svp:oracle` for pipeline acceptance testing (see Section 35) **(NEW IN 2.2)**. Details of post-delivery tools follow.

**Post-delivery tools.** After Stage 5 completes, the pipeline is done and the project is delivered. Two post-delivery tools are available:

- **Stage 6 (`/svp:bug`):** Fixes bugs in the delivered project. Available for ANY project built by SVP. The human identifies a bug, the triage agent investigates, a fix is applied, and Stage 5 reassembles the delivered repo. This is the general-purpose post-delivery debug tool.

- **Stage 7 (`/svp:oracle`):** Pipeline acceptance testing. Available ONLY when the delivered project is SVP itself. An oracle agent drives the delivered SVP pipeline end-to-end in a simulation environment to verify that the pipeline functions correctly as a product. This is a specialized tool reserved exclusively for SVP -- it cannot be used on projects built by SVP (unless that project IS SVP).

The pipeline state after Stage 5 depends on the project type and pass (CHANGED IN 2.2):
- When `is_svp_build` is false: "Stage 5 complete, Stage 6 available." (Stage 7 is not offered.)
- When `is_svp_build` is true AND `pass` is 1: "Pass 1 complete. Stage 6 available. Pass 2 available. Stage 7 NOT yet available." The human chooses to fix bugs (Stage 6) or proceed to Pass 2 (Section 43.7).
- When `is_svp_build` is true AND Pass 2 is complete: "Pass 2 complete. Stage 6 and Stage 7 available." The pipeline state is now identical to any A-D archetype post-delivery, except Stage 7 is also offered.

### 5.1 What to Expect: Best Case and Worst Case

**Best case (everything works).** The human describes their requirements clearly. The Socratic dialog produces a complete spec on the first draft. The blueprint decomposes the problem cleanly. Each unit's tests pass the red run, the implementation passes the green run, and coverage is complete — no human intervention needed. Integration tests pass. The repository is delivered. Total human decisions: roughly 5-10 approvals.

**Worst case (everything fails).** Multiple spec revisions. Blueprint fails alignment three times, hitting the iteration limit. Unit tests are wrong. Implementation fix ladders and diagnostic escalation fail, forcing document revision and restart. Multiple full restarts. The pipeline eventually converges and delivers a correct repository, but only after several passes. Total human decisions: potentially dozens.

The pipeline is designed so that the worst case still terminates correctly — every escalation path has a bounded endpoint, and every restart produces a cleaner foundation. The cost of the worst case is time and compute, not correctness.

---

## 6. Stage 0: Setup (CHANGED IN 2.0, CHANGED IN 2.1)

> **Governing invariants (Section 3.6):** Two-branch routing (entries: `project_context` → Gate 0.2, `project_profile` → Gate 0.3). Mode isolation (context mode vs profile mode). Orchestrator pipeline fidelity.

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

**(NEW IN 2.2)** `--plugin-path` (optional): Overrides default plugin discovery. When provided, sets `SVP_PLUGIN_ROOT` in the subprocess environment, directing Claude Code to use the specified plugin directory instead of searching standard paths. Used by the oracle for nested session isolation (Section 35.17) but available as a general-purpose plugin path override.

**Reference document carry-forward (NEW IN 2.2 -- Bug S3-43).** `svp restore` copies the `references/` directory from the source workspace if it exists. This ensures carry-forward artifacts (existing README, lessons learned) are available to downstream agents (git repo agent for README generation, test agent for lessons learned filtering).

**Oracle ALL_CLEAR exit path (NEW IN 2.2 -- Bug S3-44).** `ORACLE_ALL_CLEAR` during the green run must exit the oracle session directly (calling `complete_oracle_session` with exit_reason "all_clear"), NOT present Gate 7B. Gate 7B is exclusively for fix plan review after `ORACLE_FIX_APPLIED`.

**Gate routing completeness (NEW IN 2.2 -- Bug S3-45).** Every gate in GATE_VOCABULARY that can be reached through normal pipeline operation must have a corresponding routing branch in `route()` that presents it. Gates `gate_5_2_assembly_exhausted`, `gate_5_3_unused_functions`, and `gate_4_1a` must be routable via their respective sub_stage values (`gate_5_2`, `gate_5_3`, `gate_4_1a`). These sub_stages are registered in `ADDITIONAL_SUB_STAGES`.

**(NEW IN 2.2, CHANGED IN 2.2) Pass 2 usage.** During a self-build's Pass 2, `svp restore` is invoked with `--plugin-path` pointing to the Pass 1 deliverable's SVP plugin directory and `--skip-to pre-stage-3` to initialize pipeline state at Pre-Stage-3 (Stages 0-2 skipped, spec/blueprint carried forward). When invoked with `--plugin-path` during Pass 2, the restore sequence additionally initializes `pass: 2` in the pipeline state (via `enter_pass_2()` from Unit 6). Example: `svp restore --plugin-path <pass1-deliverable>/svp/ --skip-to pre-stage-3 --spec <spec> --blueprint-dir <blueprint>`. Pass 2 is orchestrator-driven (Section 43.8), not human-initiated. See Section 43.2 for the full two-pass bootstrap protocol.

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
8. ~~**Network access.**~~ *Removed.* Network connectivity is already validated by step 3 (API credentials valid) — a successful API credential check implies network access. A separate network check is redundant.
9. **MCP server dependencies available (plugin projects only).** When `archetype` is `"claude_code_plugin"` and the profile has `plugin.external_services` with MCP server entries, verify that required environment variables for each service are set. Only runs on `svp resume` (profile must already exist). Failure message: "Missing environment variables for MCP service '{service_name}': {missing_vars}. Set these in your environment before resuming."
10. **External service reachability (plugin projects only).** For HTTP-transport MCP servers declared in `plugin.external_services`, perform a basic connectivity check (HEAD request to server URL with timeout). Only runs on `svp resume`. Failure message: "External service '{service_name}' at {url} is not reachable. Check network and credentials." This check is advisory -- it warns but does not block pipeline resumption.

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

1. Reads `pipeline_state.json` to verify it is valid JSON and contains the expected schema. If missing or corrupt, attempts state recovery from completion markers. **Completion markers** are stored in `.svp/markers/` with the naming convention: `stage_N_complete` (stage completion), `unit_N_verified` (unit verification), `spec_approved` (spec approval at Gate 1.2), `blueprint_approved` (blueprint approval at Gate 2.2). Markers are created at the corresponding pipeline transition points (unit completion writes `unit_N_verified`, stage advance writes `stage_N_complete`, gate approval writes `spec_approved` or `blueprint_approved`). The **recovery algorithm**: scan `.svp/markers/` for the highest `stage_N_complete` marker; within that stage, count `unit_N_verified` markers to determine progress; reconstruct `pipeline_state.json` with the recovered stage, sub_stage, current_unit, and verified_units. If recovery fails (no markers exist), prints an error and exits.
2. Restores write permissions on the workspace (reversing the read-only lock set at session end; see Section 19.1).
3. Launches Claude Code via `subprocess.run` (see Section 6.1.5).

**6.1.5 Session Launch Mechanism**

The launcher launches Claude Code using `subprocess.run` with the following configuration:

- **Working directory:** `cwd=str(project_root)`. Claude Code uses the working directory as the project root. No `--project-dir` flag exists in the Claude Code CLI; the launcher must not pass it (Bug 31 fix — see Section 24.26).
- **Permissions flag:** `--dangerously-skip-permissions` is passed if `skip_permissions` is true in `svp_config.json` (default: true). The hook-based write authorization system (Section 19) remains active regardless of this setting.
- **Initial prompt:** `"run the routing script"` — passed as a **positional argument** (not a `--prompt` flag, which does not exist in the Claude Code CLI) so the new session immediately enters the action cycle.
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

**Two-branch routing requirement (NEW IN 2.1 — Bug 21 fix).** The `project_context` sub-stage has two reachable states: (1) the setup agent has not yet been invoked or has not yet completed, and (2) the setup agent has completed (indicated by `PROJECT_CONTEXT_COMPLETE` in `last_status.txt`). The routing script must distinguish these two states. In state (1), it emits an `invoke_agent` action for the setup agent. In state (2), it emits a `human_gate` action for Gate 0.2 (`gate_0_2_context_approval`). If `route()` always returns the agent invocation without checking `last_status.txt`, the pipeline loops indefinitely re-invoking the setup agent after the context is already written. This is a generalization of the routing action block pattern (see `test_bug14_routing_action_block_commands.py`): the routing function must handle all reachable states within a sub-stage, not just the initial entry. The same two-branch pattern applies to the `project_profile` sub-stage and Gate 0.3 (see Section 6.4). A regression test must verify that `route()` returns a gate action (not an agent invocation) when `last_status.txt` contains the agent's terminal status for both sub-stages. **Cross-artifact completion (Bug 73 fix, CHANGED — Bug 86 fix).** If the setup agent completes both `project_context.md` and `project_profile.json` in a single session, it writes `PROFILE_COMPLETE` (not `PROJECT_CONTEXT_COMPLETE`). The `project_context` routing branch must accept both status values. Additionally, the `project_profile` branch must only accept `PROFILE_COMPLETE` as the status that triggers Gate 0.3 presentation. Artifact existence (checking whether `project_profile.json` exists) must NOT be used as a fallback, because a speculative write during the context phase can create the artifact before the required profile dialog occurs (Bug 86 fix). If `last_status.txt` contains any value other than `PROFILE_COMPLETE`, routing must invoke the setup agent for the profile dialog regardless of disk state.

### 6.4 Setup Agent: Project Profile (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

After project context approval, the setup agent conducts a second Socratic dialog to capture delivery preferences. The dialog covers seven areas (0-6), beginning with Area 0 (language and ecosystem configuration, NEW IN 2.2) followed by six areas covering delivery, VCS, documentation, testing, licensing, and quality preferences. Output: `project_profile.json`.

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

**(NEW IN 2.2)** `is_svp_build` (boolean, derived): True when `archetype` is `"svp_language_extension"` or `"svp_architectural"`, false otherwise. This field controls Stage 7 (`/svp:oracle`) availability -- the oracle is only offered as a post-delivery tool when `is_svp_build` is true. Computed from archetype at profile creation — never independently set. When `is_svp_build` is true, Area 0 defaults to Python/same-as-pipeline automatically (zero additional questions beyond the archetype selection itself).

**Mode A awareness.** When the build type is Mode A (self-build), the setup agent pre-populates the profile with Mode A defaults: the 12-section README structure, conventional commits, Apache 2.0 license, `delivery.<lang>.entry_points: true`, `delivery.<lang>.source_layout: "conventional"`, `depth: "comprehensive"`, `audience: "developer"`. For Area 5, Mode A defaults are `quality.<lang>.linter: "ruff"`, `quality.<lang>.formatter: "ruff"`, `quality.<lang>.type_checker: "mypy"`, `quality.<lang>.import_sorter: "ruff"`, `quality.<lang>.line_length: 88` — matching the pipeline tools, because SVP contributors should use the same quality tools the pipeline uses **(NEW IN 2.1)**. The human reviews and approves rather than answering from scratch. It only asks questions that are genuinely open even for a self-build — license holder name, author name, author contact.

**Dialog areas.** The setup agent covers seven areas (0-6). Area 0 determines the target language(s) and configures the build/test/quality toolchain; Areas 1-6 cover delivery preferences. Each area corresponds to a set of forking points from the comprehensive enumeration (see Part III, Section 31).

**Area 0: Language and Ecosystem Configuration. (NEW IN 2.2)**

This is the first area in the setup dialog. It determines the target language(s) for the delivered project and configures the entire build/test/quality toolchain accordingly. Area 0 runs before all other areas and its output shapes which questions are asked (or skipped) in Areas 1-6.

**Archetype selector (CHANGED IN 2.2).** Area 0 begins with the archetype question:

"What are you building?"

A. **A Python software project** -- A Python library, CLI tool, or application.
B. **An R software project** -- An R package, analysis pipeline, or application.
C. **A Claude Code plugin** -- An AI-powered tool with agents, skills, hooks, and commands.
D. **A mixed-language project** -- Python and R as peers. One language owns the project structure; the other is embedded. See Section 40.6.

---
**EXPERT MODE** *(visually separated from Options A-D — typographic break, different formatting, or horizontal rule)*

**(CHANGED IN 2.2)** Expert Mode provides access to SVP self-build archetypes. These are meaningless for non-SVP projects and involve complex two-pass bootstrap protocols (Section 43). Options A-D are for building projects; Expert Mode is for building SVP itself.

When the human selects Expert Mode, the setup agent presents:

E. **SVP self-build: language extension** -- Add a new language to SVP. Pipeline mechanisms unchanged. See Section 43.3.
F. **SVP self-build: architectural change** -- Modify pipeline stages, routing, state machine, or quality gates. See Section 43.4.

**Option D -- Mixed-language project (Path 4, ~5-7 questions).** The agent sets `archetype: "mixed"` and conducts a focused dialog:

1. "Which language owns the project structure?" — presents all non-component-only languages in the registry (currently Python and R). Sets `language.primary`. The other becomes `language.secondary`.
2. "How do the languages communicate?" — Options: (a) Primary calls secondary (e.g., Python calls R via rpy2) — creates one entry `"<caller>_<callee>"`, (b) Secondary calls primary (e.g., R calls Python via reticulate) — creates one entry `"<caller>_<callee>"`, (c) Both directions — creates two entries (`"<primary>_<secondary>"` and `"<secondary>_<primary>"`). Key convention: always `"<caller>_<callee>"`. Bidirectional communication always produces two entries. Populates `language.communication` with the appropriate direction keys and bridge libraries.
3. Primary toolchain: "SVP uses conda, pytest, ruff, and mypy. Would you like your [primary] code to use the same tools?" If yes (fast path), populate primary delivery/quality with pipeline defaults. If no, conduct the detailed tool dialog (same as Path 2 for Python, Path 3 for R).
4. Secondary toolchain defaults: "For [secondary] code, SVP will use [defaults]. Would you like to change any of these?" Present the secondary language's registry defaults with opt-out. Most users accept defaults.

Hard constraint notice: "Both languages will share a single conda environment. This is required for cross-language communication." Both `delivery.<primary>.environment_recommendation` and `delivery.<secondary>.environment_recommendation` are set to `"conda"`. Both `dependency_format` fields are set to `"environment.yml"`. This is not configurable.

After the archetype-specific dialog, the notebook question and remaining areas proceed normally.

**Option A -- Python project (Path 1 or Path 2).** The agent sets `archetype: "python_project"` and asks: "SVP uses conda, pytest, ruff, and mypy for its own pipeline. Would you like your delivered project to use the same tools?"

If yes (**Path 1**, fast path, ~1 question), the agent populates the profile's language-keyed sections with pipeline-matching values:

- `language.primary`: `"python"`
- `delivery.python.environment_recommendation`: `"conda"`
- `delivery.python.dependency_format`: `"environment.yml"`
- `delivery.python.source_layout`: `"conventional"`
- `delivery.python.entry_points`: determined by Area 4 question (line 875)
- `quality.python.linter`: `"ruff"`
- `quality.python.formatter`: `"ruff"`
- `quality.python.type_checker`: `"mypy"`
- `quality.python.import_sorter`: `"ruff"`
- `quality.python.line_length`: `88`

This skips Area 5 entirely and skips the environment/dependency questions in Area 4 (environment recommendation, dependency format, source layout). **(CHANGED IN 2.2)** Path 1 does NOT skip the entry_points question in Area 4: "Does your project have a command-line tool?" is always asked for archetypes A, B, D. Only archetype C skips it (always false per Section 6.4). The remaining areas (VCS, README, testing, license, metadata, agent models) proceed normally. This is the expected path for most Python projects.

If no (**Path 2**, ~5 additional questions), the agent conducts a focused tool dialog:
- Environment manager: pip / poetry / uv / conda?
- Test framework: pytest / unittest?
- Formatter: ruff / black / autopep8 / none?
- Linter: ruff / flake8 / pylint / none?
- Type checker: mypy / pyright / none?

The valid tool sets come from the Python entry in the language registry. The agent presents options from those sets and explains each choice in plain language.

**Option B -- R project (Path 3, ~8-12 questions) (CHANGED IN 2.2).** The agent sets `archetype: "r_project"` and conducts an ecosystem-specific dialog. Each question populates a specific profile field:
- Environment manager: renv / conda / packrat? → Populates `delivery.r.environment_recommendation` (`"renv"`, `"conda"`, or `"packrat"`).
- Test framework: testthat / tinytest? → Populates `quality.r.test_framework` (`"testthat"` or `"tinytest"`).
- Linter: lintr / none? → Populates `quality.r.linter` (`"lintr"` or `"none"`).
- Formatter: styler / none? → Populates `quality.r.formatter` (`"styler"` or `"none"`).
- Documentation: roxygen2 / none? → Populates `delivery.r.documentation` (`"roxygen2"` or `"none"`).
- Package or scripts? (R package with DESCRIPTION vs. plain R scripts). → Populates `delivery.r.source_layout`: `"package"` for R package, `"scripts"` for plain R scripts.
- Shiny? (Conditional: only asked when "Package" is selected. If yes: adds shinytest2 to test dependencies, asks framework preference: plain Shiny / golem / rhino. → Populates `delivery.r.app_framework`. Plain Shiny uses `app.R` convention. Golem provides module scaffolding and deployment structure. Rhino provides enterprise-grade project organization with box modules. The setup agent recommends golem for most Shiny projects: "Golem gives you a standard project structure with module scaffolding — it's the most widely used Shiny framework.")
- Bioconductor? → Populates `delivery.r.bioconductor` (boolean). If true, adds BiocManager and changes repository configuration.
- Stan? → Populates `language.components` with Stan entry and `language.communication` with R→Stan bridge (via cmdstanr or rstan, human selects). Stan becomes a component language. If yes: configures Stan compiler.

The valid tool sets come from the R entry in the language registry.

**Option C -- Claude Code plugin (no toolchain questions, extended plugin interview).** Option C is for non-SVP plugins. SVP self-builds use Options E or F instead. The agent sets `archetype: "claude_code_plugin"` and `language.primary: "python"`. The toolchain is hardcoded: conda, pytest, ruff, mypy (same as Path 1). All delivery and quality fields are set to pipeline defaults. Option C skips Area 4 entry_points (always false) and Area 5 quality preferences (hardcoded).

The Option C interview has 4 questions:

1. "Will your plugin connect to external services via MCP servers?" If yes: "Which services?" → populates `plugin.external_services` with service names and MCP server names. The agent explains: "MCP servers let your plugin talk to things like Google Drive, Slack, databases, or any API. You provide the credentials; Claude Code provides the AI."
2. "Do any of those services need API keys or OAuth credentials?" Per service, captures auth type (`api_key`, `oauth`, or `none`) and required environment variable names → populates `plugin.external_services[].auth` and `plugin.external_services[].env_vars`.
3. "What hook events does your plugin use?" The agent presents common events with plain-language explanations: `PreToolUse` for access control, `PostToolUse` for logging/auto-format, `SessionStart` for initialization, `Stop` for cleanup → populates `plugin.hook_events`.
4. "What user-facing skills does your plugin expose?" → populates `plugin.skills`.

For SVP self-build archetypes (`"svp_language_extension"`, `"svp_architectural"`), all four plugin questions are auto-populated from SVP context and not asked interactively.

Plugin feature set details (agent definitions, specific implementations) are still Stage 1 responsibility -- the Option C interview captures only the high-level plugin integration surface.

**After archetype selection (Options A and B).** After the primary language is configured:

"Do you use computational notebooks?" (asked for Options A and B):
- Jupyter / Quarto / RMarkdown / none?
- Which languages in notebooks?

**Area 0 output.** Area 0 produces:
- `archetype` in the profile
- `language.primary` in the profile
- `language.secondary` (present only for Option D; absent for A/B/C/E/F)
- `language.components` list (empty for archetypes A/B/C/D; populated by Option B Stan dialog)
- `language.communication` dict (populated by Option D with bridge libs; populated by Option B Stan dialog; empty for A/C)
- `language.notebooks` (if applicable)
- Language-keyed `delivery` and `quality` sections in the profile (populated with defaults or dialog answers)

**UX rules for Area 0.** All four setup agent UX rules (Rules 1-4: plain language, recommendation, defaults, progressive disclosure) apply to Area 0. Advanced options (Bioconductor, Stan, custom notebooks) are asked only when relevant. The agent does not present a menu of every possible option for every project.

**Fast path summary for Area 0.** For the most common case (Python, same as pipeline):
- "What are you building?" -- A Python software project (Option A)
- "Same tools as pipeline?" -- Yes
- Area 0 complete. Two questions total.

For mixed-language projects (Option D), the fast path is ~5 questions:
- "What are you building?" -- A mixed-language project (Option D)
- "Which language owns?" -- Python (or R)
- "Communication direction?" -- Primary calls secondary (or both)
- "Same tools as pipeline for [primary]?" -- Yes
- "Default tools for [secondary]?" -- Yes
- Area 0 complete. Five questions total.

For SVP self-builds (Options E and F), the human selects the option directly. Archetype determines `is_svp_build` and `self_build_scope`. **(CHANGED IN 2.2)** For Option F, Area 0 reduces to one question (the archetype selector itself). For Option E, one additional question is asked to determine the build scope:

**Option E build scope question:** "What are you adding?"

1. **NEW LANGUAGE** -- Add a standalone language (e.g., Julia). No mixed environment. After delivery, standalone projects in the new language work.
2. **MIX LANGUAGES** -- Add a mixed environment for an existing language pair (e.g., Julia/Python). Requires the standalone language already exists. After delivery, mixed projects with that pair work.
3. **BOTH** -- Add both a standalone language and one or more mixed pairs in a single build.

The build scope determines which GoL re-expression test projects are required for oracle verification (Section 43.3).

**Option E/F defaults (auto-populated):**
- `archetype`: `"svp_language_extension"` (E) or `"svp_architectural"` (F)
- `is_svp_build`: `true`
- `self_build_scope`: `"language_extension"` (E) or `"architectural"` (F)
- `pass`: `1` (self-builds start at Pass 1)
- `language.primary`: `"python"`
- All `delivery` and `quality` fields: pipeline defaults (same as Mode A — see Section 6.4 Mode A awareness)
- Plugin fields: read from the current SVP's `plugin.json` (version, name, description)

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
- Entry points: "Does your project have a command-line tool?" Populates `delivery.<lang>.entry_points` (where `<lang>` is the primary language). **(NEW IN 2.2)** Archetype conditioning: if `archetype` is `"claude_code_plugin"`, this question is skipped and `entry_points` is set to `false` (plugin projects use Claude Code's plugin system, not `[project.scripts]` entry points). For all other archetypes, this question is asked normally.

**Area 5: Delivered Code Quality Preferences. (NEW IN 2.1)**

**(NEW IN 2.2)** If Area 0 already populated the quality section (Path 1: same as pipeline, or Path 3 where quality tools were configured), Area 5 is skipped entirely. The agent informs the human: "Quality tools were already configured during language setup."

If Area 0 did not populate quality (Path 2: Python with different tools, where only environment/test framework were chosen), the agent introduces this area with a three-path choice:

1. **Use repo tooling:** The human selects this when their repository already has its own tooling configuration (e.g., existing `ruff.toml`, `pyproject.toml` tool sections, `.flake8`, etc.). When selected, the agent sets `quality.<lang>.use_repo_tooling: true` and skips all individual tool questions. The delivered repository keeps its existing quality tool configuration unchanged.
2. **Accept defaults:** Pre-populate with the standard defaults (ruff linter, ruff formatter, mypy type checker, ruff import sorter, line length 88).
3. **Configure individually:** Walk through each tool choice below.

If the human selects path 1 (use repo tooling), the agent sets `quality.<lang>.use_repo_tooling: true`, `quality.<lang>.linter: "repo"`, `quality.<lang>.formatter: "repo"`, `quality.<lang>.type_checker: "repo"`, `quality.<lang>.import_sorter: "repo"`, `quality.<lang>.line_length: null`, and skips to the contradiction check. No individual tool questions are asked.

If the human selects path 2 or 3, the agent frames the section with: "Your project's code will be automatically formatted and checked for common problems during the build — that's a pipeline guarantee. For the delivered project, I can also include configuration so you or your contributors can run these same checks locally."

If the human enters the detailed options (path 3), each tool category must be explained before choices are presented (per Rule 1). For example, "A linter is a tool that checks your code for common mistakes and style problems — think of it like a spell-checker for code. I recommend ruff, which is fast and catches the most issues."

**(CHANGED IN 2.2)** The tool options below are the Python choices (from `LANGUAGE_REGISTRY["python"]["valid_linters"]`, etc.). Area 5 is only reached for Python Path 2 projects — R and other languages configure quality tools in Area 0, which skips Area 5 entirely (see line above).

- Linter for delivered project: ruff (default, recommended), flake8, pylint, or none.
- Formatter for delivered project: ruff (default, recommended), black, or none.
- Type checker for delivered project: mypy, pyright, or none (default, recommended — "type checking catches a specific kind of bug but requires extra annotations in the code; if you don't plan to maintain the code yourself, you can skip this").
- Import sorter for delivered project: ruff (default, recommended), isort, or none.
- Line length: integer (default: 88, recommended — "this is the most common standard; it controls how wide lines of code are allowed to be").

**Note on defaults:** The pipeline always uses ruff + mypy internally (the quality gate guarantee). The delivery defaults match the pipeline for formatter and linter (ruff) but default type checker to "none" because the end user may not want to maintain type annotations. The setup agent explains this distinction.

**What the setup agent does NOT ask in Areas 1-6.** The following are either pipeline-fixed (Tier A) or determined by Area 0, and are not presented as choices in later areas:

- Programming language -- determined in Area 0 (NEW IN 2.2). No longer pipeline-fixed.
- Environment manager for the pipeline (Conda only).
- Test framework for the pipeline (pytest only — the target project's test framework is determined in Area 0).
- Package format for the pipeline build (setuptools only).
- Source layout during build (`src/unit_N/` — SVP-native).
- VCS system (Git only).
- Quality tools for the pipeline (ruff + mypy — fixed) **(NEW IN 2.1)**.

If the human asks about these, the agent explains they are fixed for the pipeline but the delivery can differ.

**What the setup agent DOES ask that affects delivery packaging.** **(CHANGED IN 2.2)** For R projects, these questions are handled entirely within Area 0 Path 3 and are not re-asked in later areas. The following apply to Python projects where Area 0 did not already determine the delivery configuration (Path 2):

- Delivered environment recommendation: conda (default), pyenv, venv, Poetry, or "no environment instructions in README."
- Dependency specification in delivered repo: `environment.yml` (default if conda), `requirements.txt`, `pyproject.toml` dependencies, or multiple formats.
- Delivered source layout: conventional `src/packagename/` (default), flat, or SVP-native.

**Unsupported preferences.** If the human volunteers a preference that SVP does not support, the setup agent acknowledges the request, explains the limitation honestly, and tells the human it will not be tracked — they will need to handle it manually after delivery. Nothing is recorded in the profile.

**Output: `project_profile.json`.** Strongly-typed JSON. The `language`, `delivery`, and `quality` sections use language-keyed structure (NEW IN 2.2). Schema:

```
project_profile.json
├── pipeline_toolchain: "python_conda_pytest"  (fixed, informational)
├── is_svp_build: boolean                              (NEW IN 2.2, derived from archetype)
├── self_build_scope: string | null                    (NEW IN 2.2, derived from archetype)
├── archetype: string                                  (NEW IN 2.2, "python_project" | "r_project" | "claude_code_plugin" | "mixed" | "svp_language_extension" | "svp_architectural")
├── language:                                          (NEW IN 2.2)
│   ├── primary: string                  (e.g., "python", "r")
│   ├── secondary: string | absent       (present only when archetype is "mixed", e.g., "r")
│   ├── components: list of strings      (e.g., ["stan"], may be empty)
│   ├── communication: dict              (e.g., {"stan": "cmdstanr"}, or {"python_r": "rpy2"} for mixed)
│   └── notebooks: string | null         ("jupyter" | "quarto" | "rmarkdown" | null)
├── python_version: string               (present when primary or component is python)
├── delivery:                            (language-keyed, NEW IN 2.2)
│   └── <language_key>:                  (e.g., "python", "r")
│       ├── environment_recommendation: string
│       ├── dependency_format: string | list
│       ├── source_layout: "conventional" | "flat" | "svp_native" | "package" | "scripts"
│       │     ("conventional"/"flat"/"svp_native" are Python layouts; "package" = R package with DESCRIPTION/NAMESPACE, "scripts" = plain R scripts)
│       ├── app_framework: "shiny" | "golem" | "rhino" | null  (R only, NEW IN 2.2)
│       ├── entry_points: boolean
│       ├── documentation: "roxygen2" | "none" | absent        (R only, NEW IN 2.2; absent for non-R languages)
│       └── bioconductor: boolean | absent                     (R only, NEW IN 2.2; absent for non-R languages)
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
├── quality:                             (language-keyed, CHANGED IN 2.2)
│   │   (Delivery configuration only. All fields in the quality section
│   │    configure the delivered project's quality tools, not the pipeline's.
│   │    The pipeline always uses ruff + mypy via toolchain.json regardless
│   │    of these settings. See Section 12.13.)
│   └── <language_key>:                  (e.g., "python", "r")
│       ├── use_repo_tooling: boolean    (if true, skip individual tool fields)
│       ├── linter: string | "none"
│       ├── formatter: string | "none"
│       ├── type_checker: string | "none"
│       ├── import_sorter: string | "none"  (python only)
│       ├── line_length: integer | null
│       └── test_framework: string | absent            (R only, NEW IN 2.2; "testthat" | "tinytest"; absent for Python which uses pytest via toolchain)
├── plugin:                             (present when archetype is "claude_code_plugin" or self-build, NEW IN 2.2)
│   ├── external_services: list of {service_name, mcp_server, auth, env_vars}
│   ├── hook_events: list of string     ("PreToolUse" | "PostToolUse" | "SessionStart" | "Stop")
│   ├── skills: list of string
│   ├── mcp_servers: list of string
│   └── uses_lsp: boolean
├── pipeline:                            (NEW IN 2.2)
│   ├── agent_models:                    (dict of agent_key → model_id)
│   │   ├── stakeholder_dialog: string
│   │   ├── stakeholder_reviewer: string
│   │   ├── blueprint_author: string
│   │   ├── blueprint_checker: string
│   │   ├── blueprint_reviewer: string
│   │   ├── test_agent: string
│   │   ├── implementation_agent: string
│   │   ├── coverage_review: string
│   │   ├── diagnostic_agent: string
│   │   ├── integration_test_author: string
│   │   ├── git_repo_agent: string
│   │   ├── bug_triage: string
│   │   ├── repair_agent: string
│   │   ├── reference_indexing: string
│   │   ├── setup_agent: string
│   │   ├── help_agent: string
│   │   ├── hint_agent: string
│   │   ├── redo_agent: string
│   │   ├── checklist_generation: string  (NEW IN 2.2)
│   │   ├── regression_adaptation: string (NEW IN 2.2)
│   │   └── oracle_agent: string          (NEW IN 2.2)
│   ├── context_budget_override: integer | null
│   └── context_budget_threshold: integer (0-100)
├── fixed:
│   ├── pipeline_environment: "conda"
│   ├── test_framework: "pytest"
│   ├── build_backend: "setuptools"
│   ├── vcs_system: "git"
│   ├── source_layout_during_build: "svp_native"
│   └── pipeline_quality_tools: "ruff_mypy"           (NEW IN 2.1)
└── created_at: ISO timestamp
```

The `fixed` section records Tier A values for transparency. No agent reads `fixed` at runtime -- the pipeline reads `toolchain.json`. Note that `fixed.language` has been removed in 2.2 since the language is now determined by Area 0 and stored in `language.primary`.

**Schema constraint:** Every field has a defined default. The setup agent always writes a fully populated `project_profile.json` with every field explicitly present. No downstream consumer needs a defaults table.

#### 6.4.1 Canonical Naming Invariant (NEW IN 2.1)

The schema above defines the exact canonical section names and field names for `project_profile.json`. These names are authoritative. Every component that produces or consumes profile data must use exactly these names:

- Top-level sections are: `pipeline_toolchain`, `is_svp_build`, `language` (NEW IN 2.2), `python_version`, `delivery` (not `packaging`), `vcs`, `readme`, `testing`, `license` (not `licensing`), `quality`, `pipeline` (NEW IN 2.2), `fixed`, `created_at`.
- Within `readme`: the audience field is `audience` (not `target_audience`).
- Within `delivery`: the environment field is `environment_recommendation` (not `environment`).
- Within `license`: metadata is under `additional_metadata` (not `metadata`).
- Within `pipeline`: model overrides are under `agent_models` (not `models`). Keys use the agent role identifiers listed in the schema tree above.
- Within `delivery.<lang>`: the app framework field is `app_framework` (not `framework`, not `shiny_framework`). Null when not applicable.

This invariant applies to three components that must agree on names:

1. **`DEFAULT_PROFILE` in the config reader** (`svp_config.py` / Unit 1): the hardcoded default profile used as the merge base in `load_profile()`. Its section names and field names must exactly match this schema.
2. **The setup agent's output**: the `project_profile.json` file written during Stage 0. The setup agent's system prompt must reference this schema. The agent must use these exact names when constructing the JSON output.
3. **Every downstream consumer** (preparation scripts, blueprint checker, git repo agent, compliance scan, redo agent): field access must use these exact names.

If any component uses a different name (e.g., `licensing` instead of `license`, `readme.target_audience` instead of `readme.audience`), the `_deep_merge` in `load_profile()` will not override the default — both the default value and the misnamed value will coexist in the merged result, producing silent conflicts. This is not a validation-catchable error; the merge succeeds but the semantics are wrong.

**Enforcement mechanism.** The canonical field names must be defined as constants in a single shared location (Unit 1's schema definition). The setup agent's system prompt must include the complete schema with exact field names. A regression test must verify that every key in `DEFAULT_PROFILE` appears in the schema definition, and that the setup agent's output (for a representative dialog) uses only keys present in `DEFAULT_PROFILE`. No component may invent profile field names independently.

**Contradiction detection.** The setup agent checks for known contradictory combinations during the dialog and asks the human to resolve them before writing the profile. Known contradictions include:

- `readme.depth: "minimal"` with more than 5 sections or any custom sections.
- `readme.include_code_examples: true` with `readme.depth: "minimal"`.
- `delivery.<lang>.entry_points: true` with no identifiable CLI module in the stakeholder spec.
- `delivery.<lang>.source_layout: "flat"` with more than approximately 10 units.
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

**(CHANGED IN 2.2)** The toolchain configuration now supports the three-layer model (Section 3.25):

- **Pipeline toolchain** (`toolchain.json` at project root): Fixed. Controls how SVP runs. Permanently read-only after project creation.
- **Language-specific toolchain** (in `scripts/toolchain_defaults/`, e.g., `python_conda_pytest.json`, `r_renv_testthat.json`): Controls build-time quality gates for the target language. Selected based on `LANGUAGE_REGISTRY[language]["toolchain_file"]`. Read-only.

The `load_toolchain` function gains an optional `language` parameter. When provided, loads the language-specific toolchain file. When `None`, loads the pipeline toolchain. In SVP 2.2, for Python-only projects, both resolve to the same file (`python_conda_pytest.json`).

The `toolchain_defaults/` directory ships with toolchain files for all built-in languages (Python, R). Dynamic toolchain generation (activated via self-build with `self_build_scope: "language_extension"` — see Section 43.3) is not active in SVP 2.2.

**(NEW IN 2.2) R toolchain file schema.** The R build-time toolchain file (`r_renv_testthat.json`) follows the same structure as the Python toolchain file but with R-specific commands. Reference defaults (may be refined during blueprint/implementation):

```json
{
    "environment": {
        "manager": "renv",
        "create": "Rscript -e 'renv::init()'",
        "install": "Rscript -e 'renv::install(\"{package}\")'",
        "run_prefix": "Rscript -e '"
    },
    "test": {
        "framework": "testthat",
        "run": "Rscript -e 'testthat::test_dir(\"tests/testthat\")'",
        "coverage": "Rscript -e 'covr::package_coverage()'"
    },
    "quality": {
        "packages": ["lintr", "styler"],
        "gate_a": ["Rscript -e 'styler::style_dir(\"R/\")'"],
        "gate_b": ["Rscript -e 'styler::style_dir(\"R/\")'", "Rscript -e 'lintr::lint_dir(\"R/\")'"],
        "gate_c": ["Rscript -e 'styler::style_dir(\"R/\", dry=\"check\")'", "Rscript -e 'lintr::lint_dir(\"R/\")'"]
    }
}
```

These are reference defaults. The exact commands may be refined during blueprint construction. The gate composition structure (gate_a, gate_b, gate_c lists) is invariant; the commands within each gate vary by language.

Language-specific toolchain files follow the same top-level structure (environment, test/testing, quality sections) but key names within sections may vary by language to match that language's conventions (e.g., Python uses `testing` while R uses `test`). The toolchain reader (Unit 4) normalizes access through `resolve_command()` and other accessor functions that abstract over key naming differences.

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
|   |   |-- toolchain_defaults/
|   |   |   |-- python_conda_pytest.json        <- Python build-time toolchain
|   |   |   |-- r_renv_testthat.json            <- R build-time toolchain (NEW IN 2.2)
|   |   |   |-- ruff.toml
|   |   |   +-- README.md                       <- Toolchain file format spec (NEW IN 2.2)
|   |   +-- delivery_quality_templates/         <- NEW IN 2.2
|   |       |-- python/
|   |       |   |-- ruff.toml.template
|   |       |   |-- flake8.template
|   |       |   |-- mypy.ini.template
|   |       |   +-- pyproject_black.toml.template
|   |       |-- r/
|   |       |   |-- lintr.template
|   |       |   +-- styler.template
|   |       +-- README.md                       <- Template format spec
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

The following table lists every bug in the unified catalog (Bugs 1-74) with its coverage mechanism. Dedicated regression test files are carried forward from the previous build -- copied from the SVP plugin's `tests/regressions/` directory into the project workspace during project creation. All dedicated regression test files must pass in both the workspace layout and the delivered repository layout.

This table is the single authoritative reference for the dual numbering scheme. The "Filename Bug #" column shows the number used in the test filename prefix (`test_bugNN_*`). The "Unified Bug #" column shows the canonical bug number in the unified catalog (Bugs 1-74). Where these differ, it is due to historical naming (see naming collision note below).

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
| bug55 | 55 | Dedicated file | `test_bug55_rollback_gate62_wiring.py` | Gate 6.2 FIX UNIT dispatch / rollback_to_unit and set_debug_classification wiring |
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
| bug68 | 68 | Dedicated file | `test_bug68_stage4_failure_handling.py` | Stage 4 failure handling: gate_4_1/4_2 routing, ASSEMBLY FIX dispatch, TESTS_FAILED dispatch |
| bug69 | 69 | Dedicated file | `test_bug69_debug_loop_gates.py` | Debug loop gates: gate_6_0, gate_6_1, gate_6_3 RECLASSIFY, gate_6_5 commit |
| bug70 | 70 | Dedicated file | `test_bug70_ladder_routing_tests_error.py` | Fix ladder routing at sub_stage=None, TESTS_ERROR infinite loop, dead phases |
| bug71 | 71 | Dedicated file | `test_bug71_structural_completeness.py` | Structural completeness: gate/status/dispatch consistency (163 tests) |
| bug72 | 72 | Dedicated file | `test_bug72_structural_check.py` | Structural check command and compliance scan routing |
| bug73 | 73 | Dedicated file | `test_bug73_routing_dispatch_loops.py` | Routing/dispatch loops: Stage 0 PROFILE_COMPLETE, Gate 5.3 OVERRIDE CONTINUE, Gate 4.1 ASSEMBLY FIX |

**Regression test count.** There are 51 distinct regression test file entries in the table above (46 unique filenames): 15 carry-forward from SVP 2.0, 7 carry-forward from SVP 2.1 prior builds, and 29 newly authored in this build. Three `test_bugNN_` filename prefixes are reused across different bugs (`test_bug17_*`, `test_bug18_*`, `test_bug19_*` -- see naming note above), but each table entry corresponds to a distinct file with a unique full filename. The 29 newly authored files are: `test_bug13_hook_schema_validation.py` (Bug 17), `test_bug22_repo_sibling_directory.py` (Bug 37), `test_bug23_stage1_spec_gate_routing.py` (Bug 41), `test_bug42_pre_stage3_state_persistence.py` (Bug 42), `test_bug43_stage2_blueprint_routing.py` (Bug 43), `test_bug44_null_substage_dispatch.py` (Bug 44), `test_bug45_test_execution_dispatch.py` (Bug 45), `test_bug46_coverage_dispatch.py` (Bug 46), `test_bug47_unit_completion_double_dispatch.py` (Bug 47), `test_bug48_launcher_cli_contract.py` (Bug 48), `test_bug49_argparse_enumeration.py` (Bug 49), `test_bug50_contract_sufficiency.py` (Bug 50), `test_bug51_debug_reassembly.py` (Bug 51), `test_bug52_version_document_wiring.py` (Bug 52), `test_bug53_orphaned_functions.py` (Bug 53), `test_bug54_orphaned_update_state_from_status.py` (Bug 54), `test_bug55_rollback_gate62_wiring.py` (Bug 55), `test_bug58_gate_5_3_unused_functions.py` (Bug 58), `test_bug59_blueprint_path_and_gates.py` (Bug 59), `test_bug60_unit_context_blueprint_path.py` (Bug 60), `test_bug61_include_tier1_parameter.py` (Bug 61), `test_bug62_selective_blueprint_loading.py` (Bug 62), `test_bug65_stage3_error_handling.py` (Bug 65), `test_bug67_gate_5_3_routing.py` (Bug 67), `test_bug68_stage4_failure_handling.py` (Bug 68), `test_bug69_debug_loop_gates.py` (Bug 69), `test_bug70_ladder_routing_tests_error.py` (Bug 70), `test_bug71_structural_completeness.py` (Bug 71), `test_bug72_structural_check.py` (Bug 72), and `test_bug73_routing_dispatch_loops.py` (Bug 73). All other files are carried forward unchanged.

(Note: The 51 entries above and their 'carry-forward' / 'newly authored' classifications describe the SVP 2.1 build. In the SVP 2.2 context, all 51 are carry-forward from SVP 2.1. The 6 additional regression test files listed below are newly authored for SVP 2.2.)

**New regression test naming convention.** Newly authored regression tests in this build use the unified catalog number: `test_bugNN_descriptive_suffix.py` where NN is the unified bug number. The `test_bug13_hook_schema_validation.py` file for unified Bug 17 uses a pre-unified filename prefix (`bug13`) because Bug 17 was catalogued before the unified numbering convention was established. Despite being newly authored in this build, its filename uses the old numbering for backward compatibility: the SVP 2.0 regression test inventory already allocated the `test_bug13` prefix slot, and existing tooling and documentation reference this filename. Changing it would break the established carry-forward contract. The filename is treated as a fixed historical artifact.

**Test filename note for Bug 43.** The test file `test_bug43_stage2_blueprint_routing.py` carries "stage2_blueprint" in its suffix because the bug was originally discovered in Stage 2's blueprint dialog routing. However, the test's scope is universal -- it verifies two-branch compliance for ALL entries in the Section 3.6 exhaustive list and cross-unit gate ID consistency. The suffix is a historical artifact of the discovery context, not a scope limitation.

**(CHANGED IN 2.2)** The regression test `test_bug43_stage2_blueprint_routing.py` must be updated to include all SVP 2.2 gates in its exhaustive gate ID consistency check. The complete gate vocabulary is now 31 gate IDs (23 from SVP 2.1, including gate_hint_conflict, plus 8 new: gate_4_3_adaptation_review, gate_7_a_trajectory_review, gate_7_b_fix_plan_review, gate_pass_transition_post_pass1, gate_pass_transition_post_pass2, gate_3_completion_failure, gate_4_1a, gate_6_1a_divergence_warning). The test must fail (not pass silently) if a new entry is added to Section 3.6's exhaustive list without a corresponding two-branch routing check and gate ID registration.

**(NEW IN 2.2) Additional regression test requirements:**
- `test_assembly_map_generation.py`: Verifies `assembly_map.json` is generated correctly during Stage 5 and that the bidirectional mapping is consistent (bijectivity check).
- `test_dispatch_exhaustiveness.py`: Verifies all six dispatch tables cover all registered full languages. AST-based scan.
- `test_three_layer_separation.py`: Verifies no function reads pipeline quality from profile or delivery quality from toolchain. AST-based import path scan.
- `test_profile_migration.py`: Verifies SVP 2.1-format profiles auto-migrate to language-keyed format.
- `test_r_test_output_parsing.py`: Verifies R test output parser correctly identifies pass/fail/error from testthat output.
- `test_behavioral_equivalence.py`: Verifies SVP 2.2 Python-only output matches SVP 2.1 output.

**Total regression test file count (SVP 2.2).** 51 carry-forward files from SVP 2.1 plus 6 new files from SVP 2.2 = 57 total regression test files.

### 6.9 Stage 0 Orchestrator Mentor Protocol (NEW IN 2.2)

Stage 0 is the only stage where every decision belongs to the human. Nothing has been generated yet, so there are no agent outputs to detect errors in. The orchestrator's role is mentorship — using its full-pipeline visibility to provide contextual framing that helps the human make informed decisions at each gate. This protocol operationalizes the two principles (Section 3.31) for Stage 0: the orchestrator informs with the full picture but never decides for the human; it explains downstream consequences without executing anything.

#### 6.9.1 Gate 0.1 — Hook Activation Guidance

When presenting Gate 0.1, the orchestrator explains what hooks protect and what the human should verify. Hooks are the write authorization system (Section 19) — they prevent agents from writing outside their authorized paths during the build. Without active hooks, agents can overwrite `pipeline_state.json`, modify `scripts/` files, and write outside the workspace — all failure modes described in Section 3.30. The human should verify in the `/hooks` menu that hooks are listed and their scripts are present in `.claude/scripts/`.

#### 6.9.2 Gate 0.2 — Context Approval Guidance

When presenting Gate 0.2, the orchestrator explains what downstream agents will consume the project context and what distinguishes strong context from weak context. The `project_context.md` document is read by the stakeholder dialog agent (Stage 1), every reviewer, and the help agent throughout the build. Strong context has concrete domain terminology, specific data characteristics, measurable success criteria, and a clear problem statement. Weak context — vague descriptions, missing terminology, no data characteristics — forces the Stage 1 agent to fill gaps with assumptions that may not match the human's domain, leading to spec revisions and restarts.

#### 6.9.3 Gate 0.3 — Profile Approval Guidance

When presenting Gate 0.3, the orchestrator explains how profile choices propagate through later stages and which choices are hard to change. The conda environment name, quality tools, and gate check configuration are all derived from the profile. `delivery.<lang>.source_layout` determines how Stage 5 assembles the repository and is impractical to change after Stage 3 begins (units are built against a specific layout). `testing.framework` is similarly difficult to change after tests are written. Other delivery preferences (commit style, changelog format, README structure) are easy to change via `/svp:redo` at any point before Stage 5. Once approved, the profile is immutable (Section 6.4) — changes require `/svp:redo`.

---

## 7. Stage 1: Stakeholder Spec Authoring (CHANGED IN 2.1)

> **Governing invariants (Section 3.6):** Two-branch routing (entries: `stakeholder_spec_authoring` → Gate 1.1, reviewer completion → Gate 1.2, `checklist_generation` → Stage 2 advance). Gate ID consistency (Gates 1.1, 1.2).

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
2. The **Reference Indexing Subagent** reads it and produces a structured summary (what it is, topics, key terms, relevant sections) saved to `references/index/`. This is a single-shot agent invocation: it receives the full document content, produces the summary, and exits with terminal status `INDEXING_COMPLETE`. Default model: Sonnet-class (pattern-driven summarization task).
3. The summary is available as context to subsequent agents. The full document is accessible on demand.

For GitHub repositories, the **GitHub MCP Subagent** explores the repo structure, key modules, and APIs via the GitHub MCP server, and produces a summary following the same format as document summaries. Terminal status: `INDEXING_COMPLETE`. Default model: Sonnet-class.

**Contradiction and staleness subagents (Section 7.7.6, 7.7.7).** The orchestrator delegates the contradiction detection pass and the staleness/redundancy pass to dedicated single-shot subagents, each reading the entire spec with fresh context. The contradiction subagent produces a structured report of numeric inconsistencies, behavioral conflicts, and conditional accuracy issues. Terminal status: `CONTRADICTION_CHECK_COMPLETE`. The staleness subagent produces a report of stale statements, unnecessary duplication, and orphaned references. Terminal status: `STALENESS_CHECK_COMPLETE`. Both default to Opus-class (require deep document comprehension).

Reference documents supplement the Socratic dialog — they do not replace it. The stakeholder spec remains the single source of truth for intent.

### 7.3 Socratic Dialog

**Agent definition.**

| Property | Value |
|----------|-------|
| Name | Stakeholder Dialog Agent |
| Stage | 1 (+ revision mode) |
| Default model | Configured via `pipeline.agent_models.stakeholder_dialog` (see Section 22.1 precedence). Defaults to Opus-class (requires deep domain understanding) |
| Inputs | Conversation ledger, reference summaries, project context (+ critique in revision mode) |
| Outputs | Stakeholder spec draft (`specs/stakeholder_spec.md`) |
| Terminal status | `SPEC_DRAFT_COMPLETE` (initial draft), `SPEC_REVISION_COMPLETE` (revision mode) |
| Interaction | Ledger multi-turn (`ledgers/stakeholder_dialog.jsonl`; revision mode: `ledgers/spec_revision_N.jsonl`) |

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

#### 7.4.1 Stakeholder Spec Reviewer — Role and Scope

The stakeholder spec reviewer is a cold reviewer: it receives the spec document, project context, and reference summaries — no dialog ledger, no authoring history. It reads the document as a finished artifact and produces a structured critique.

**Agent definition.**

| Property | Value |
|----------|-------|
| Name | Stakeholder Spec Reviewer |
| Stage | 1 |
| Default model | Configured via `pipeline.agent_models.stakeholder_reviewer` (see Section 22.1 precedence) |
| Inputs | Approved/draft stakeholder spec, project context, reference summaries (no ledger) |
| Outputs | Structured critique document |
| Terminal status | `REVIEW_COMPLETE` |
| Interaction | Single-shot |

**Role boundary — what this agent reviews.**

The spec reviewer evaluates the stakeholder spec as a *requirements document*. Its concerns are:

1. **Completeness.** Are there gaps — behaviors, flows, edge cases, or constraints that the spec should define but does not? Would a blueprint author reading this spec be forced to guess intent in any area?
2. **Consistency.** Do different sections contradict each other? Are numeric values, enumerated sets, and behavioral descriptions consistent throughout?
3. **Clarity.** Are descriptions unambiguous? Could a competent blueprint author interpret a requirement in two materially different ways?
4. **Scope discipline.** Does the spec stay within its jurisdiction as a requirements document? Does it avoid prescribing implementation architecture that belongs in the blueprint?
5. **Downstream dependency analysis.** For every behavior the spec defines, is there enough information for the blueprint to create contracts without guessing? (This is the spec-level interpretation of the Section 3.20 checklist.)

**Role boundary — what this agent does NOT review.**

The spec reviewer does NOT evaluate:

- **Technical architecture choices.** Unit decomposition, dependency graphs, dispatch table design, module structure — these are blueprint concerns.
- **Contract sufficiency.** Whether a blueprint contract would be detailed enough for implementation — the spec reviewer has no blueprint to evaluate.
- **Implementation feasibility.** Whether a requirement is technically achievable given the chosen architecture.
- **Gate dispatch mechanics.** The specific state transitions, dispatch functions, and routing logic — these are blueprint-level implementation details.

**The only blueprint-adjacent concerns this agent should flag:**

1. **Underspecification.** Places where the spec is vague, silent, or ambiguous in ways that would force the blueprint author to *guess* stakeholder intent. Example: the spec says "the agent handles errors" but doesn't define what constitutes an error or what "handling" means.
2. **Spec overreach.** Places where the spec prescribes technical implementation details that belong in the blueprint. Example: the spec dictates specific function signatures, module organization, or dispatch table structure instead of defining the *behavior* those mechanisms should achieve.

**Baked checklist (Section 3.20 adaptation).**

The Section 3.20 baked checklist items are interpreted at the spec level by this agent:

- *Downstream dependency analysis* → Does the spec define each behavior clearly enough that a blueprint author can derive dependency relationships without guessing?
- *Contract granularity* → Does the spec distinguish fine-grained behaviors (each needing its own contract) rather than lumping multiple behaviors into vague descriptions?
- *Per-gate dispatch contracts* → Does the spec define all gate response options and their intended effects on pipeline flow?
- *Call-site traceability* → Does every capability the spec defines have a clear trigger (who invokes it, when, under what conditions)?
- *Re-entry invalidation* → Does the spec define what happens when a flow is re-entered (revision cycles, retries, restarts)?
- *Gate reachability* → Does every gate the spec defines have a described path that reaches it?

**Scenarios — Gates 1.1/1.2.**
*Best case:* Thorough dialog, complete draft, human approves. One draft, one approval.
*Worst case:* Gaps and misinterpretations. Multiple reviews and revisions, with Help Agent sessions to formulate hints. In the most extreme case, a full spec restart.

### 7.5 Output

An approved `stakeholder_spec.md` file with completion marker. Pipeline state updated to record Stage 1 completion. Session boundary fires.

**Canonical filename (NEW IN 2.1 — Bug 22 fix, CHANGED IN 2.1).** The stakeholder spec filename is `stakeholder_spec.md`. This name must be defined as a shared constant referenced by both the setup agent's file placement logic and the preparation script's file loading logic. No component may hardcode an alternative name (e.g., `stakeholder.md`). This is a cross-unit contract: the setup agent (which writes the file) and the preparation script (which reads it) must agree on the exact filename through a single source of truth. The same principle applies to any pipeline artifact referenced by path across multiple components. The complete set of canonical filenames that must be defined as shared constants includes: `stakeholder_spec.md`, `blueprint_prose.md`, `blueprint_contracts.md`, `project_context.md`, `project_profile.json`, `toolchain.json`, `ruff.toml`, `pipeline_state.json`, `svp_config.json`, and `svp_2_1_lessons_learned.md` (the lessons learned document, at workspace-relative path `references/svp_2_1_lessons_learned.md`, referenced by the debug loop's Step 6). **(Naming note):** The filename `svp_2_1_lessons_learned.md` is a carry-forward artifact from SVP 2.1. It retains this name across versions because it contains cumulative lessons; it is not renamed per-version.

### 7.6 Spec Revision Modes

The stakeholder spec may need modification after initial approval. SVP distinguishes two modes plus a temporary mechanism:

**Working notes (during blueprint dialog only).** When the blueprint dialog surfaces a narrow spec ambiguity, the human provides a short answer. The answer is appended as a working note with provenance marker. The blueprint dialog continues without interruption. Working notes are incorporated into the spec body at every iteration boundary — the spec is never left with appended patches.

**Targeted spec revision.** Triggered by the blueprint checker, diagnostic agent, or `/svp:redo`. The stakeholder dialog agent operates in revision mode: receives the current spec plus a specific critique, conducts a Socratic dialog about just that issue, and produces an amendment. Unrevised portions are untouched. The agent produces `SPEC_REVISION_COMPLETE` as its terminal status line. The pipeline restarts from Stage 2. Uses its own ledger (`ledgers/spec_revision_N.jsonl`) where N = `spec_revision_count` from `pipeline_state.json`, an incrementing integer starting at 1. The `spec_revision_count` field is incremented each time a targeted spec revision is initiated. The original conversation ledger (`ledgers/stakeholder_dialog.jsonl`) is provided as read-only context to the revision agent so it understands the decisions that led to the original spec.

**Full spec restart.** Complete redo of the Socratic dialog, producing a new spec from scratch. Rare and always human-initiated. Reserved for cases where the spec is fundamentally wrong or the human's understanding has changed substantially.

### 7.7 Orchestrator Oversight Protocol (NEW IN 2.2)

The main session (orchestrator) has specific quality assurance responsibilities during Stage 1 spec authoring that go beyond relaying prompts between the human and the stakeholder dialog agent. These responsibilities are automatic — the orchestrator performs them without being asked.

#### 7.7.1 Decision Ledger

During the Socratic dialog (Section 7.3), the orchestrator maintains a running decision ledger — a numbered list of every architectural decision, design choice, and constraint established during the dialog. Each entry records:
- The decision number
- What was decided
- The human's choice (if options were presented)
- Any agent recommendations that informed the choice

The decision ledger is ephemeral (exists only in the orchestrator's context) but its content is used to verify the spec draft. The orchestrator does not need to persist the ledger to disk — it is a working document for the current Stage 1 session.

#### 7.7.2 Spec Draft Verification Checklist

After the stakeholder dialog agent produces a spec draft, the orchestrator constructs a verification checklist from the decision ledger. The checklist maps every decision to a specific location in the spec draft. For each decision, the orchestrator verifies:

1. **Presence:** The decision is reflected in the spec. Missing decisions are flagged.
2. **Accuracy:** The spec text matches what was decided. Contradictions or deviations from the dialog are flagged (e.g., the agent wrote "mandatory" when the human decided "optional").
3. **Consistency:** The decision does not contradict other decisions in the spec. Cross-references are checked.

The orchestrator runs this checklist after every spec draft revision — not just the first draft. Each revision is verified against the full checklist before being presented to the human for review.

#### 7.7.3 Feature Parity Verification

**Trigger condition:** Feature parity verification runs when `is_svp_build` is `true` in the project profile AND a prior version spec exists in `references/` (e.g., `references/stakeholder_spec_v8.33.md`). When these conditions are not met, this section does not apply.

When the spec builds on a previous version (e.g., SVP 2.2 builds on SVP 2.1), the orchestrator performs a deep comparison between the new spec and the baseline spec. This verification ensures:

1. **No regressions:** Every section, gate, agent, invariant, terminal status line, pipeline state field, command, and failure mode from the baseline spec exists in the new spec.
2. **Correct markers:** Changed sections are marked with the appropriate version marker (e.g., `(CHANGED IN 2.2)`). New sections are marked `(NEW IN 2.2)`.
3. **Strict superset:** The new spec is a strict superset of the baseline — nothing is removed unless explicitly decided during the dialog.

The feature parity check is run once after the full spec is assembled (not after every draft iteration). The orchestrator produces a category-by-category count comparison (sections, gates, agents, invariants, status lines, state fields, commands, failure modes) and reports any missing items.

#### 7.7.4 Contradiction and Ambiguity Detection

Throughout the dialog and during draft verification, the orchestrator watches for:

1. **Agent drift:** The stakeholder dialog agent proposing or writing something that contradicts a previous decision. The orchestrator catches this and flags it to the human before it enters the spec.
2. **Scope creep:** The agent adding features, constraints, or requirements that were not discussed during the dialog. The orchestrator flags undiscussed additions.
3. **Ambiguous language:** Spec text that could be interpreted multiple ways. The orchestrator identifies ambiguities and raises them for the human to resolve.
4. **Cross-section conflicts:** A statement in one section that contradicts a statement in another. The orchestrator checks cross-references.

#### 7.7.5 Checkpoint Cycle

The orchestrator follows a checkpoint cycle for spec drafts:

1. **Agent produces draft** -> orchestrator receives it
2. **Orchestrator runs verification checklist** -> identifies failures
3. **If failures exist:** orchestrator instructs the agent to revise, providing the specific failure list. Go to step 1.
4. **If no failures:** orchestrator presents the draft to the human with the checklist results (all passing)
5. **Human reviews** -> approves, requests changes, or raises new points
6. **If changes:** orchestrator updates the decision ledger and instructs the agent to revise. Go to step 1.

**Checkpoint cycle bound:** The internal revision loop (steps 1-3) is bounded to 2 iterations. If after 2 internal revision attempts the checklist still has failures, the orchestrator presents the draft to the human WITH the failure list, allowing the human to decide whether to accept, request targeted revision, or provide guidance on unresolvable items.

The human never sees a spec draft that has uncaught checklist failures (within the 2-iteration bound). The orchestrator is the quality gate between the agent and the human.

#### 7.7.6 Contradiction Detection Pass

After every spec draft passes the verification checklist, the orchestrator runs a contradiction detection pass. This pass checks:

1. **Numeric consistency:** Gate counts, unit counts, agent counts, design principle counts, failure mode counts, and acceptance criteria counts are consistent across all sections.
2. **Behavioral consistency:** Stage 7 entry mechanism (command-invoked vs automatic), workspace vs. repo references, source-of-truth claims, discovery vs. bug language — all must be consistent across every section that references them.
3. **Conditional accuracy:** Statements that are conditionally true (e.g., Stage 7 availability depends on `is_svp_build`) must be correctly conditioned everywhere they appear.

The orchestrator delegates this pass to a dedicated subagent to reduce semantic drift. The subagent reads the entire spec with fresh context and reports contradictions without being influenced by the orchestrator's assumptions.

#### 7.7.7 Staleness and Redundancy Pass

After the contradiction pass, the orchestrator runs a staleness and redundancy pass:

1. **Stale statements:** Statements inherited from the previous version that are no longer accurate due to new features. Examples: old stage counts, old unit counts, old gate counts, references to removed constraints.
2. **Redundant statements:** The same fact stated in multiple places where consolidation would improve clarity without losing information. The orchestrator distinguishes between:
   - **Acceptable repetition:** Design principle stated concisely in Section 3, then explained in detail in a stage section. Both needed.
   - **Unnecessary duplication:** The same paragraph appearing in two different sections with identical wording. One should become a cross-reference.
3. **Orphaned references:** Cross-references to sections, documents, or artifacts that don't exist.

Fixes are applied, then the full verification checklist is re-run.

The orchestrator delegates this pass to a dedicated subagent for the same reason as the contradiction pass — fresh context reduces the risk of normalizing stale or redundant content.

#### 7.7.8 Pipeline Fidelity Constraint (NEW IN 2.2)

The orchestrator's role, failure modes, and governing principles are defined in Sections 3.29-3.32. The autonomous operation definition (Section 3.32) applies to all stages including Stage 1. The per-stage oversight protocols are consolidated in Section 20.4.

The six-step action cycle (Section 20) is mandatory for every action block, with one defined exception: during Stage 1, the orchestrator has additional quality assurance responsibilities (Sections 7.7.1-7.7.7) that operate alongside — not instead of — the action cycle.

There are no light units (Section 3.6, Orchestrator Pipeline Fidelity Invariant). Every unit receives the full verification cycle regardless of complexity.

If the orchestrator encounters a bug in the builder pipeline (e.g., a script in `scripts/` produces incorrect output), it MUST follow the Hard Stop Protocol (Section 41). It MUST NOT modify builder scripts directly during Stages 3-5. This is enforced by a PreToolUse hook (Section 19).

### 7.8 Pre-Blueprint Checklist Generation (NEW IN 2.2)

After the stakeholder spec is approved (Gate 1.2) and before Stage 2 (Blueprint Generation) begins, a dedicated **Checklist Generation Agent** reads the approved spec cold and produces two structured checklists. This agent is NOT the spec author and NOT the blueprint author — it reads the spec with fresh context.

#### 7.8.1 Purpose

The stakeholder spec may be thousands of lines. Neither the blueprint author nor the alignment checker can hold the entire document in context. The checklists distill the spec into structured, verifiable controls — a bridge between spec prose and blueprint construction.

#### 7.8.2 Checklist 1: Blueprint Author Self-Evaluation Checklist

A numbered list of actionable verification items the blueprint author uses during and after blueprint construction. Each item:
- References a specific spec section (for traceability)
- Is binary checkable (pass/fail, not subjective)
- Targets a concrete blueprint artifact (unit, contract, invariant, dispatch entry, DAG edge)

The blueprint author reviews this checklist after completing the blueprint draft, before submitting it for alignment checking. Any unchecked item is addressed before submission.

**Seed checklist inclusion (mandatory):** The generated checklist MUST include every item from the seed checklist (Section 44), either verbatim or refined with project-specific detail. The seed encodes verification criteria derived from prior build failures. Missing seed items are a generation failure.

**Mandatory categories (closed required set).** The generated checklist MUST include items from all of the following categories. The generator MAY add project-specific categories beyond this set but MUST NOT omit any required category:
- **Structural completeness:** Every spec section has corresponding blueprint coverage
- **Invariant encoding:** Every design principle and invariant is reflected in unit contracts
- **Dispatch coverage:** Every dispatch table has contracted entries for all registered languages
- **Gate coverage:** Every gate ID has a dispatch contract with all response options
- **Artifact coverage:** Every artifact type (Python, markdown, bash, JSON for plugin projects) has appropriate stub/test/quality contracts
- **DAG integrity:** Dependencies match the spec's unit architecture, no forward edges
- **Language framework:** Registry entries, toolchain files, profile schema all contracted
- **Spec/blueprint boundary:** Every seed checklist item (Section 44) is included — these mark known boundaries where the spec defines WHAT and the blueprint must determine HOW

**Final item (mandatory):** Review ALL lesson learned bugs and regression tests. For each bug:
- Verify the blueprint does not recreate the failure pattern
- If the bug is not already generalized into a pattern (P1-P12+), attempt to generalize it: identify the structural characteristic that produced the bug and state it as a universal rule
- Check that the generalized pattern is preventable by at least one blueprint contract

#### 7.8.3 Checklist 2: Blueprint Alignment Checker Checklist

A numbered list of systematic verification criteria the alignment checker uses when reviewing the blueprint against the spec. Each item:
- References a specific spec section
- Is binary checkable
- Specifies what "aligned" means for that requirement

The alignment checker works through this checklist item by item. Any failure is reported as an alignment issue.

Categories include but are not limited to:
- **Section coverage:** Every spec section maps to at least one blueprint unit
- **Contract sufficiency:** Every behavioral requirement in the spec has a Tier 3 contract sufficient for deterministic reimplementation
- **Invariant presence:** Every invariant from Section 3 appears as a structural constraint in the blueprint
- **Gate-response completeness:** Every gate response option has a dispatch contract specifying the exact state transition
- **Enumeration completeness:** Every enumerated value set in the spec (valid tools, valid status strings, valid gate responses) appears as a validation contract
- **Cross-unit contracts:** Every dependency edge in the DAG has corresponding interface contracts on both sides
- **Language framework alignment:** Registry structure, dispatch protocols, return type contracts all match spec definitions

**Final item (mandatory):** Verify that the blueprint author completed the lesson learned / regression test review (Checklist 1 final item). Additionally, independently review all lesson learned bugs and regression tests:
- For each bug, verify the blueprint has contracts that prevent the failure pattern
- For each bug not yet generalized into a pattern, verify the blueprint author's proposed generalization is sound
- Flag any regression test whose failure scenario is not covered by at least one blueprint contract

#### 7.8.4 Checklist Delivery

The two checklists are written as structured markdown files:
- `.svp/blueprint_author_checklist.md`
- `.svp/alignment_checker_checklist.md`

These files are passed as additional inputs to the blueprint author agent (Stage 2, Section 8.1) and the blueprint checker agent (Stage 2, Section 8.2) respectively.

#### 7.8.5 Agent Definition

| Property | Value |
|----------|-------|
| Name | Checklist Generation Agent |
| Stage | Post-Stage-1, pre-Stage-2 |
| Default model | Configured via `pipeline.agent_models.checklist_generation` (see Section 22.1 precedence). Defaults to Opus-class (requires deep spec comprehension) |
| Inputs | Approved stakeholder spec, lessons learned document, regression test inventory, **seed checklist (Section 44)** |
| Outputs | Two checklist files (`.svp/blueprint_author_checklist.md`, `.svp/alignment_checker_checklist.md`) |
| Terminal status | `CHECKLISTS_COMPLETE` |
| Interaction | Single-shot (reads spec, produces checklists, exits) |

---

## 8. Stage 2: Blueprint Generation and Alignment (CHANGED IN 2.0, CHANGED IN 2.1)

> **Governing invariants (Section 3.6):** Two-branch routing (entries: `blueprint_dialog` → Gate 2.1, reviewer completion → Gate 2.2, `alignment_check` → Gate 2.2 or restart). Route-level state persistence (Gate 2.2 APPROVE → Pre-Stage-3 transition). Gate ID consistency (Gates 2.1, 2.2, 2.3).

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

**(NEW IN 2.2 — Bug 84 fix)** The blueprint author agent receives the full lessons learned document (`references/svp_2_1_lessons_learned.md`) as an additional input. The author uses the pattern catalog (Part 2 of the document) to avoid recreating known failure patterns during contract design. For example, if pattern P4 (missing error conditions) has historically produced bugs, the author proactively specifies error conditions in new unit contracts. This is a preventive measure — the author designs contracts with awareness of what has gone wrong in previous builds.

**(CHANGED IN 2.2)** The blueprint author agent receives the Blueprint Author Self-Evaluation Checklist (`.svp/blueprint_author_checklist.md`, generated by the Checklist Generation Agent in Section 7.8) as an additional input. The author uses this checklist for self-evaluation during and after blueprint construction.

**(NEW IN 2.2)** For `"mixed"` archetype projects, units may be tagged with different languages. Bridge units (cross-language communication) are tagged with the calling language per Section 40.6.3. Cross-language dependencies are valid DAG edges.

The blueprint must produce units in the three-tier format:

- **Tier 1 — Description:** free prose describing purpose, inputs, outputs, role. May optionally include a `### Preferences` subsection (see below).
- **Tier 2 — Machine-readable signatures:** valid Python parseable by `ast`. Import statements declaring all types, followed by type-annotated function and class signatures with ellipsis bodies. Also includes invariants as Python `assert` statements.
- **Tier 3 — Error conditions, behavioral contracts, dependencies:** structured text. Error conditions as exception types with messages. Behavioral contracts as discrete testable claims. Dependencies as upstream unit references (backward-only).

**Unit-level Preferences subsection (NEW IN 2.1 — RFC-2).** Each unit's Tier 1 description in `blueprint_prose.md` may optionally include a `### Preferences` subsection. This subsection captures domain conventions, output appearance choices, and domain-specific decisions that are not requirements but matter to the human. The format is a `### Preferences` heading within the unit's Tier 1 block, followed by free prose describing the preferences.

- **Absence means "no preferences."** If a unit has no `### Preferences` subsection, no explicit "no preferences" marker is needed.
- **Authority hierarchy:** spec > contracts > preferences. Preferences are non-binding guidance that operates within the space that contracts leave open. A preference never overrides a behavioral contract or a spec requirement.
- **No new artifacts.** Preferences travel inside Tier 1 descriptions. Agents that receive Tier 1 (via `build_unit_context` with `include_tier1=True`) automatically receive any Preferences subsections. No changes to `prepare_task.py` are needed.

The blueprint author agent captures preferences during the decomposition dialog using Rules P1-P4 (see Unit 13 agent definition). The blueprint checker validates preference-contract consistency as a non-blocking warning (see Unit 14 agent definition).

**Testability requirement.** Rules P1-P4 must appear verbatim in the blueprint author agent definition (`BLUEPRINT_AUTHOR_AGENT_MD_CONTENT`). The blueprint checker validates their presence. A structural test verifies the rule text is present. This mirrors Section 6.4's testability requirement for Setup Agent Rules 1-4.

**Unit granularity.** A unit is the smallest piece of code that can be independently tested against its blueprint contract without requiring any other unit's implementation to exist. Unit boundaries must be clean interfaces — if unit B depends on unit A, unit B's tests mock unit A based on its contract, never its implementation.

**Unit ordering.** Units are ordered by dependency in topological order. The first unit is the first piece of domain logic. The entry point is the last unit. No circular dependencies by construction.

**Backward-only dependency invariant.** This is a foundational structural constraint — the entire verification cycle, context isolation, stub generation, and fix ladder depend on it. Every unit's Tier 3 dependency list must reference only units with lower unit numbers. Unit 5 may depend on Units 1-4. It may never depend on Units 6 or higher. The blueprint author agent is explicitly instructed to enforce this in its system prompt. The blueprint checker validates it structurally (see Section 8.2). The infrastructure setup validates it again before creating directories (see Section 9). The stub generator refuses to generate stubs for forward-referenced units. A forward dependency is a blueprint-level failure — if detected at any stage, the pipeline returns to Stage 2.

The blueprint author produces two files: `blueprint_prose.md` containing all Tier 1 descriptions, and `blueprint_contracts.md` containing all Tier 2 signatures, invariants, and Tier 3 contracts. Both files use the same unit heading structure (`## Unit N: Name`) so that the blueprint extractor can parse them independently. The files are a pair — they must be submitted together at every gate and revised together in every alignment loop iteration.

**(NEW IN 2.2) Regression test import mapping.** When the blueprint documents module reorganizations (splits, renames, relocations) relative to the previous SVP version, the blueprint author agent produces `regression_test_import_map.json` as a blueprint artifact. This mapping captures all module renames and function relocations needed to adapt carry-forward regression tests. The mapping is derived from the blueprint's unit-to-module assignments and the previous version's module structure. See Section 12.1.2 for the mapping format and Section 11.5 for how the mapping is consumed during regression test adaptation.

**(NEW IN 2.2) Language tagging in blueprints.** When the project uses multiple languages, the blueprint author tags each unit with its language using code fence annotations in the signature blocks. For example:

````
```python
def parse_signatures(block: str) -> List[Signature]:
```
````

or

````
```r
parse_signatures <- function(block) {
```
````

The blueprint extractor detects the language from code fence tags: `python` -> "python", `r` -> "r", `stan` -> "stan", untagged -> project's primary language. This tagging drives per-unit language dispatch during Stage 3.

For single-language projects, code fence tags are optional -- all units default to the primary language.

**(NEW IN 2.2) Stub extraction contract.** The blueprint must provide signature blocks in a standardized format that the stub generator can parse mechanically. For each unit, the Tier 2 section contains code-fenced signature blocks that serve as the input to the language-specific signature parser (dispatch table entry 1) and stub generator (dispatch table entry 2). The blueprint extractor must strip code fence markers (opening ` ```language ` and closing ` ``` ` lines) before passing block content to the signature parser. The parser receives raw code, not markdown. This stripping is the extractor's responsibility (Unit 8), not the parser's (Unit 9) — the parser contract assumes clean input.

**For Python:** Signature blocks use standard Python function/class definitions. The signature parser uses `ast.parse()`.

**For R:** Signature blocks use standard R function assignment syntax (`function_name <- function(args) { }`). The signature parser uses a regex-based parser for R function definitions.

**For dynamic languages:** The blueprint author must describe the signature format in the unit's Tier 2 section, and the setup agent's dynamic registry construction (Area 0) must have captured enough information for the signature parser to handle it.

**Invariant:** Every Tier 2 signature block must be parseable by the registered signature parser for that unit's language. The blueprint checker validates this by attempting to parse each signature block. Parse failures are alignment errors.

**(NEW IN 2.2) Blueprint file tree annotation format.** The blueprint preamble contains a file tree that maps workspace paths to delivered repo paths. Each entry uses `<- Unit N` annotations:

```
svp/
├── scripts/
│   ├── routing.py              <- Unit 14
│   ├── pipeline_state.py       <- Unit 5
│   ├── quality_gate.py         <- Unit 15
```

The assembly map generator (`assembly_map.json`) parses these annotations to produce the bidirectional path mapping. Every unit that generates deliverable code MUST have a file tree entry. Missing entries cause incomplete assembly maps, which break path correlation in Stage 6 (triage) and Stage 7 (oracle).

**Context budget validation.** The blueprint must fit within the effective context budget and support selective extraction (a single unit's definition plus upstream contracts without loading the full blueprint).

### 8.2 Blueprint Alignment Check (CHANGED IN 2.0, CHANGED IN 2.1)

**Sub-stage:** `stage: "2", sub_stage: "alignment_check"` **(NEW IN 2.1 — Bug 23 fix)**.

**Routing requirement.** After Gate 2.1 APPROVE, the routing script must transition to the `alignment_check` sub-stage and invoke the blueprint checker agent — not advance directly to Pre-Stage-3. This is the same two-branch pattern as Bug 21: `route()` must check the current sub-stage and dispatch accordingly. The alignment check agent, phase, and gate vocabulary all exist in the system; the routing script must wire them into the execution path. A regression test must verify that after Gate 2.1 APPROVE, the next action is a blueprint checker invocation (not a stage advance to Pre-Stage-3).

**State persistence requirement (NEW IN 2.1 — Bug 42 fix).** When Gate 2.2 APPROVE triggers the transition from `alignment_check` to `pre_stage_3`, the `route()` function must persist the intermediate state to disk before returning the Pre-Stage-3 action block. If `route()` performs the transition in memory and then recursively routes to produce the Pre-Stage-3 action block without saving, the POST command of the returned action block will load stale state from disk and overwrite the transition. Note: `ALIGNMENT_CONFIRMED` itself presents Gate 2.2 (a human gate) and does not directly advance to Pre-Stage-3 -- the advance occurs only when the human selects APPROVE at Gate 2.2. This is governed by the route-level state persistence invariant (Section 3.6). Additionally, `dispatch_agent_status` for `reference_indexing` must advance the pipeline from `pre_stage_3` to stage 3 — it must not be a bare `return state` (exhaustive dispatch_agent_status invariant, Section 3.6).

A fresh blueprint checker agent receives the stakeholder spec (including working notes), both `blueprint_prose.md` and `blueprint_contracts.md`, reference summaries, and the project profile **(CHANGED IN 2.0, CHANGED IN 2.1)**. **(CHANGED IN 2.2)** The blueprint checker agent receives the Blueprint Alignment Checker Checklist (`.svp/alignment_checker_checklist.md`, generated by the Checklist Generation Agent in Section 7.8) as an additional input. The checker works through this checklist item by item as part of its alignment verification. The checker verifies internal consistency: every unit present in the prose file must have a corresponding contracts entry, and every unit in the contracts file must have a corresponding prose entry. A unit present in one file but absent from the other is an unconditional alignment failure. It also verifies alignment and validates structural requirements: machine-readable signatures are parseable, all types have imports, per-unit context budget is within threshold, selective extraction works, working notes are consistent with spec text.

**DAG acyclicity validation.** The checker must parse every unit's Tier 3 dependency list, build the dependency graph, and verify: (1) no unit references a unit with a higher number (no forward edges), (2) no cycles exist, (3) every referenced unit number exists in the blueprint. This is a deterministic structural check on the blueprint text — no LLM judgment required. A forward edge or cycle is an unconditional blueprint failure, regardless of alignment status.

**Profile preference validation (Layer 2) (CHANGED IN 2.0, CHANGED IN 2.1).** The checker verifies that every profile preference — including documentation, metadata, commit style, delivery packaging, and quality tool configuration — is reflected as an explicit contract in at least one unit. A profile that says "conda, no bare pip" with no unit mentioning conda usage is an alignment failure. A profile that says "comprehensive README for developers" with no unit specifying audience and depth is also an alignment failure. A profile with `quality.<lang>.linter: "ruff"` with no unit contracting ruff configuration generation is an alignment failure **(NEW IN 2.1)**.

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
- **Alignment is confirmed:** The checker blesses the blueprint. The pipeline presents Gate 2.2 (`gate_2_2_blueprint_post_review`). The human chooses: **APPROVE** (advance to Pre-Stage-3), **REVISE**, or **FRESH REVIEW**. The human always decides when to advance -- `ALIGNMENT_CONFIRMED` never directly advances to Pre-Stage-3. If **FRESH REVIEW**: a distinct blueprint reviewer agent reads the documents cold and produces a critique. Review cycles are unbounded. **(NEW IN 2.2 — Bug 84 fix)** The blueprint reviewer agent receives the full lessons learned document (`references/svp_2_1_lessons_learned.md`) as an additional input. The reviewer cross-references the blueprint against known failure patterns (P1-P9+) during its cold review, similar to the blueprint checker. The reviewer uses this to identify structural risks that the checker's alignment-focused analysis might miss.

**Alignment failure state transitions (CHANGED IN 2.2).** The `dispatch_agent_status` handler for `blueprint_checker` must implement explicit state transitions for each outcome — no bare `return state` is permitted (exhaustive dispatch_agent_status invariant, Section 3.6):

- **`ALIGNMENT_FAILED: blueprint`**: Reset `sub_stage` to `"blueprint_dialog"`, increment `alignment_iterations` counter. This returns the pipeline to the blueprint dialog entry point — a fresh blueprint author agent is invoked on the next routing cycle, producing a new draft that flows through Gate 2.1 → alignment_check. The failed alignment's critique is passed to the fresh author via the preparation script.
- **`ALIGNMENT_FAILED: spec`**: Set `sub_stage` to `"targeted_spec_revision"` (or equivalent restart state per Section 8.3). The pipeline initiates a targeted spec revision cycle. After the revision completes, the pipeline restarts Stage 2 from `blueprint_dialog`.
- **`ALIGNMENT_CONFIRMED`**: Set `sub_stage` to `"alignment_confirmed"` (or equivalent gate-presenting state). The routing script presents Gate 2.2. Only Gate 2.2 APPROVE advances to Pre-Stage-3.

**Invariant: the only path from Stage 2 to Pre-Stage-3 is Gate 2.2 APPROVE.** No `ALIGNMENT_FAILED` outcome — regardless of classification — may advance the pipeline to Pre-Stage-3. Every `ALIGNMENT_FAILED` outcome loops back through the blueprint dialog or spec revision, eventually re-entering the alignment check. The human always approves progression via Gate 2.2.

**Gate 2.2 dual entry paths.** Gate 2.2 (`gate_2_2_blueprint_post_review`) is reached via two distinct paths: (1) alignment confirmed by the blueprint checker (the "alignment is confirmed" outcome above — `ALIGNMENT_CONFIRMED` presents Gate 2.2), and (2) fresh review completed by the blueprint reviewer (the "FRESH REVIEW" option from either Gate 2.1 or Gate 2.2 itself — `REVIEW_COMPLETE` presents Gate 2.2). Both paths present the same gate with the same response options (**APPROVE**, **REVISE**, **FRESH REVIEW**). **APPROVE** at Gate 2.2 is the only path that advances to Pre-Stage-3 — the human always controls this transition. Both paths set `sub_stage` to `"alignment_confirmed"` before presenting Gate 2.2 — the checker path sets it in `dispatch_agent_status` for `blueprint_checker` (Section 8.2 transitions), and the reviewer path sets it in `dispatch_agent_status` for `blueprint_reviewer`. The routing script must handle both entry paths identically at Gate 2.2. **Path-context mechanism:** The preparation script for Gate 2.2 reads `last_status.txt` to distinguish the two paths: if `last_status.txt` contains `ALIGNMENT_CONFIRMED`, the path was checker to Gate 2.2, and the preparation script includes the alignment report (checker output) as gate context; if `last_status.txt` contains `REVIEW_COMPLETE`, the path was reviewer to Gate 2.2, and the preparation script includes the reviewer critique as gate context. This ensures the human sees the appropriate analysis at Gate 2.2 regardless of which path reached it.

**Gate naming rationale.** Gate 2.1 (`gate_2_1_blueprint_approval`) is the human's initial approval before machine validation — an alignment check has not yet run. Gate 2.2 (`gate_2_2_blueprint_post_review`) is the human's final approval after machine validation has confirmed alignment. The naming follows the same pattern as Stage 1: `gate_1_2_spec_post_review` is presented after the spec checker has validated the artifact, just as `gate_2_2_blueprint_post_review` is presented after the blueprint checker has validated the artifact.

**Scenarios — Gates 2.1/2.2.**
*Best case:* Checker confirms alignment first attempt. Human approves. Advances to Pre-Stage-3.
*Worst case:* Multiple failures — spec problems, then blueprint problems. Several fresh dialogs and spec revisions before alignment converges.

#### 8.2.1 Blueprint Reviewer — Role and Scope

The blueprint reviewer is a cold reviewer: it receives the blueprint, spec, project context, references, and lessons learned — no dialog ledger, no authoring history. It reads both documents with fresh context and produces a structured critique of the blueprint's faithfulness to the spec.

**Agent definition.**

| Property | Value |
|----------|-------|
| Name | Blueprint Reviewer Agent |
| Stage | 2 |
| Default model | Configured via `pipeline.agent_models.blueprint_reviewer` (see Section 22.1 precedence) |
| Inputs | Blueprint (prose + contracts), stakeholder spec, project context, reference summaries, lessons learned (full) (no ledger) |
| Outputs | Structured critique document |
| Terminal status | `REVIEW_COMPLETE` |
| Interaction | Single-shot |

**Role boundary — what this agent reviews.**

The blueprint reviewer evaluates the blueprint as a *faithful translation* of the stakeholder spec into buildable architecture. Its concerns are:

1. **Spec fidelity.** Does the blueprint accurately reflect every requirement in the spec? Are there spec requirements that the blueprint omits, misinterprets, or contradicts?
2. **Contract completeness.** Does every behavioral requirement in the spec have a corresponding Tier 3 contract in the blueprint sufficient for deterministic reimplementation?
3. **Structural soundness.** Is the unit decomposition, dependency DAG, and dispatch architecture internally consistent? Are there circular dependencies, missing edges, or orphaned units?
4. **Invariant encoding.** Is every design principle and invariant from the spec (Section 3) reflected as a structural constraint in the blueprint?
5. **Historical risk patterns.** Does the blueprint recreate any known failure pattern from the lessons learned document (P1-P13+)? Are there structural characteristics that match historical bug root causes? (NEW IN 2.2 — Bug 84 fix.)
6. **Downstream dependency analysis, contract granularity, gate dispatch completeness, call-site traceability, re-entry invalidation, gate reachability.** (Section 3.20 baked checklist — applied at the blueprint level where these items are directly evaluable.)

**Role boundary — what this agent does NOT review.**

The blueprint reviewer does NOT evaluate:

- **Spec quality as a standalone document.** The spec is the source of truth. The blueprint reviewer does not critique whether the spec *should* have required something different — that was the spec reviewer's job.
- **Implementation code.** The blueprint reviewer works with contracts and architecture, not source code.
- **Test design.** Whether tests are sufficient or well-structured — that is a Stage 3/4 concern.

**The only spec-adjacent concerns this agent should flag:**

1. **Spec ambiguity exposed by blueprint work.** Places where the blueprint author was forced to make an interpretation choice because the spec was ambiguous. The reviewer flags these as "spec clarification needed" — the blueprint may be correct, but the spec should be more explicit.
2. **Spec incompleteness exposed by blueprint work.** Behaviors the blueprint defines that have no corresponding spec requirement — either the spec forgot to specify it (spec gap) or the blueprint is adding unspecified behavior (blueprint overreach).

**Critique output format.** The blueprint reviewer writes its critique to `.svp/blueprint_review.md`. The critique is structured as per-concern sections, each containing: (1) **Spec reference** — the specific spec section and requirement, (2) **Blueprint reference** — the specific unit/contract/tier affected, (3) **Gap** — what is missing, contradictory, or overreaching, (4) **Severity** — `critical` (blocks correctness), `major` (likely to cause build failures), or `minor` (quality/clarity improvement). The gate preparation script reads this file to populate the Gate 2.2 context when the reviewer path reaches it.

### 8.3 Alignment Loop (CHANGED IN 2.2)

The blueprint generation and checking cycle may iterate. The alignment loop is a state machine with the following rules:

**Iteration counter semantics.** The `alignment_iterations` counter in `pipeline_state.json` tracks the total number of alignment loop iterations. Both failure types (`ALIGNMENT_FAILED: blueprint` and `ALIGNMENT_FAILED: spec`) increment the counter. A targeted spec revision does NOT reset the counter — the revision addresses a specific issue but does not restart the alignment effort. The counter measures total effort expended, not consecutive failures of one type.

**Per-failure-type transitions:**
- **`ALIGNMENT_FAILED: blueprint`**: Working notes from the current iteration are incorporated into the spec body. A fresh blueprint author agent conducts a new decomposition dialog (never resumes a prior dialog). The checker's critique is passed to the fresh author via the preparation script. Counter increments.
- **`ALIGNMENT_FAILED: spec`**: Enters the `targeted_spec_revision` sub-stage (see below). After revision completes, the pipeline returns to `blueprint_dialog` for a fresh blueprint attempt. Counter increments.

**Working notes handling.** When the blueprint author agent is re-invoked after an alignment failure, it receives the accumulated working notes from all prior iterations. Working notes are incorporated into the spec body at every iteration boundary — the spec is never left with appended patches. The fresh author receives the cleaned spec (with absorbed notes) plus the checker's critique.

**`targeted_spec_revision` sub-stage.** When `ALIGNMENT_FAILED: spec` triggers a spec revision: (1) `sub_stage` is set to `"targeted_spec_revision"`, (2) the stakeholder dialog agent is invoked in revision mode with the checker's critique as the revision prompt, (3) the agent conducts a focused Socratic dialog about the specific issue and produces a spec amendment, (4) terminal status: `SPEC_REVISION_COMPLETE`, (5) on completion, the pipeline transitions back to `sub_stage: "blueprint_dialog"` for a fresh blueprint attempt with the revised spec. The revision uses its own ledger (`ledgers/spec_revision_N.jsonl` where N = `spec_revision_count`).

**Iteration limit and exhaustion.** Configurable via `iteration_limit` (Section 22.1), default 3. When `alignment_iterations >= iteration_limit`, the alignment checker's last report serves as the diagnostic summary explaining why alignment is not converging. The pipeline presents Gate 2.3 (`gate_2_3_alignment_exhausted`).

**Gate 2.3 full dispatch:**
- **REVISE SPEC**: Enters `targeted_spec_revision` sub-stage. After revision, resets `alignment_iterations` to 0 and returns to `blueprint_dialog`. This is the "fresh start with revised requirements" path.
- **RESTART SPEC**: Clears the spec entirely. Returns to Stage 1 for a full spec restart (new Socratic dialog from scratch). The `alignment_iterations` counter is reset to 0.
- **RETRY BLUEPRINT**: Does NOT reset the counter (the human acknowledges the effort spent). Returns to `blueprint_dialog` for one more attempt. If the next attempt also fails and `alignment_iterations >= iteration_limit`, Gate 2.3 re-presents.

Each Gate 2.3 response has an explicit state transition in `dispatch_gate_response()`. No response is a no-op.

**Scenarios — Gate 2.3.**
*Best case:* Never reached. Alignment converges within 1-2 attempts.
*Worst case:* Three attempts fail. The human uses the Help Agent to identify the root cause, revises the spec, and restarts.

### 8.4 Output

Blessed `blueprint_prose.md` and `blueprint_contracts.md` files with completion marker. Pipeline state updated. Session boundary fires.

### 8.5 Stage 2 Orchestrator Oversight Protocol (NEW IN 2.2)

The orchestrator runs the following 23-item detection checklist against the blueprint before presenting it to the human for approval. This protocol operationalizes the two principles (Section 3.31) for Stage 2: the orchestrator detects issues using the checklist; all fixing is delegated to the blueprint author agent through the normal pipeline cycle.

#### 8.5.1 Structural Completeness (6 items)

1. Every spec section maps to at least one blueprint unit. No spec requirement is left unaddressed.
2. Every design principle (Section 3) is encoded in unit invariants or cross-unit contracts. Principles do not float as prose — they must be mechanically checkable.
3. The DAG is acyclic with correct topological ordering. No forward edges, no cycles.
4. Every Tier 2 block is parseable by the appropriate language-specific `SIGNATURE_PARSERS` entry. Catches code fence contamination (markdown ` ``` ` inside signature blocks) and content in the wrong language for a unit's target.
5. Every unit's contracts are sufficient for independent implementation. An agent receiving only the unit definition and upstream signatures can produce a correct implementation without reading other units.
6. Every language in the project profile has a registry entry and dispatch table entries for all six tables (signature parsing, stub generation, test output parsing, quality gate execution, project assembly, compliance scanning). Component languages are exempt per Section 3.27.

#### 8.5.2 Namespace Consistency (5 items)

7. Terminal statuses are character-identical across: spec Section 18.1, agent definition units, routing dispatch units.
8. Gate responses are character-identical across: spec Section 18.4, GATE_VOCABULARY definitions, dispatch contract units.
9. Agent types are character-identical across: KNOWN_AGENT_TYPES, AGENT_BLUEPRINT_LOADING, PHASE_TO_AGENT definitions.
10. Dispatch keys match: every registry entry has corresponding entries in all dispatch tables.
11. Status values are character-identical across Units 2, 14, and 15 (the units that define, validate, and route on status values).

#### 8.5.3 Dead Code (4 items)

12. Every Tier 2 function has at least one consumer (another unit that imports or calls it).
13. Every agent type defined in agent definition units has a routing path (appears in dispatch).
14. Every gate defined in the spec has both a preparation script and a dispatch entry.
15. No unreachable dispatch entries: every key in every dispatch table is reachable from the routing logic.

#### 8.5.4 Contract Alignment (5 items)

16. Every acceptance criterion in the spec is addressable by at least one unit's contracts.
17. Every failure mode cataloged in the spec (Section 24) has preventive contracts in at least one unit.
18. Cross-unit interfaces match both sides: if unit A's contracts say it calls `unit_B.foo(x, y)`, then unit B's Tier 2 exports `foo(x, y)` with compatible types.
19. No scope creep: every contract traces back to a spec requirement. No unit contains contracts for functionality not in the spec.
20. No omissions: every spec requirement traces forward to at least one contract. Bidirectional traceability with item 16.

#### 8.5.5 Lessons Learned (3 items)

21. Every pattern P1-P13+ in the bug catalog (Section 24) has preventive contracts in the blueprint. The blueprint encodes the fix, not just awareness of the bug.
22. Every regression test in `tests/regressions/` maps to contracts that would prevent the regression from recurring.
23. If `regression_test_import_map.json` is needed (Section 11.5), the blueprint's module structure is compatible with the existing regression tests. Import paths in the blueprint match or are mappable from the paths the regression tests use.

---

## 9. Pre-Stage-3: Infrastructure Setup (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

Before any unit verification begins, Pre-Stage-3 prepares the build environment. Pre-Stage-3 has two sequential phases: (1) infrastructure setup — a deterministic run_command that creates the environment, installs packages, validates imports, and creates directories. (2) reference indexing — an agent-driven step that indexes any reference documents provided via /svp:ref. After infrastructure completes (COMMAND_SUCCEEDED), route() invokes the reference indexing agent. After INDEXING_COMPLETE, the pipeline advances to Stage 3. If no reference documents exist, the reference indexing agent completes immediately.

**(CHANGED IN 2.2)** Infrastructure setup is language-aware:

1. **Environment creation** dispatches via the language registry's `environment_manager` field. For Python: `conda create`. **(CHANGED IN 2.2)** For R: dispatches through `delivery.r.environment_recommendation` from the profile (set during Option B dialog, Section 6.4). If `"renv"`: `renv::init()`. If `"conda"`: `conda create` (same mechanism as Python). If `"packrat"`: `packrat::init()`. For multi-language projects with components: component environments are created within the primary language's environment. Component packages are installed inside the host language's conda/renv environment — no separate environment is created for components. For `"mixed"` archetype: a single `conda create` with both Python and R plus bridge libraries (rpy2 and/or r-reticulate per the communication dict). No renv. This is a hard constraint per Section 40.6.2.

2. **Quality tool installation** reads packages from the language-specific toolchain file. Each language's quality tools are installed in the appropriate environment. **(CHANGED IN 2.2)** For `"mixed"` archetype projects, quality packages from BOTH language toolchains are installed into the single conda environment.

3. **Import validation** is language-specific. Python imports are validated with `python -c "import X"`. R imports are validated with `Rscript -e "library(X)"`. Validation uses the `collection_error_indicators` from the language registry to detect failures.

4. **Directory structure** follows the primary language's conventions (`source_dir`, `test_dir` from registry). Component language files go in language-specific subdirectories.

### 9.1 Dependency Extraction and Environment Creation

1. A deterministic script scans all machine-readable signature blocks across all units in the blueprint, extracting every external import statement.
2. The script produces a complete dependency list from the extracted imports.
3. The script creates the build environment using the language registry's `environment_manager` (Section 40.2) and installs all packages. For Python: conda. For R: renv. For dynamic languages: the configured environment manager.
4. The test framework packages from the language-specific toolchain file (`testing.framework_packages`) must be installed unconditionally — test code uses the target language's test framework but it doesn't appear in blueprint signature blocks. Python default: pytest, pytest-cov. R default: testthat.
5. The quality tool packages from the language-specific toolchain file (`quality.packages`) must be installed unconditionally **(NEW IN 2.1)**. Python default: ruff, mypy. R default: lintr, styler.

Scripts read tool commands from `toolchain.json` instead of hardcoding them: `environment.create`, `environment.run_prefix`, `environment.install`, `testing.framework_packages`, `quality.packages` **(CHANGED IN 2.0, CHANGED IN 2.1)**.

Pre-Stage-3 always creates the build environment from scratch, regardless of whether an environment from a prior pass exists. If a prior environment exists with the same name, it is replaced. For Python this is a conda environment; for R this is an renv library; for dynamic languages, whatever the registry's `environment_manager` specifies.

### 9.2 Import Validation

After environment creation, the script validates that every extracted import resolves in the created environment:

```bash
conda run -n {env_name} python -c "from scipy.signal import ShortTimeFFT"
```

If any import fails to resolve, this is a blueprint problem — the pipeline returns to blueprint revision.

### 9.3 Directory Structure, Scaffolding, and DAG Validation

The script creates the source and test directory structure based on the blueprint's unit definitions: `src/unit_N/` and `tests/unit_N/` for each unit.

**DAG re-validation.** Before creating directories, the infrastructure script re-validates the dependency graph by parsing each unit's dependency list from the blueprint. If any forward edge or cycle is detected, the script fails with a clear error identifying the violating units. This is a belt-and-suspenders check — the blueprint checker should have caught this at Stage 2, but a corrupted or manually edited blueprint could reintroduce violations. This check is deterministic with no LLM involvement.

### 9.4 Regression Test Import Adaptation (NEW IN 2.2)

If `regression_test_import_map.json` exists in the workspace, `adapt_regression_tests.py` is run against `tests/regressions/` to adapt carry-forward regression test imports to the current project's module layout. This is an optional step -- if the mapping file does not exist (e.g., no module reorganization occurred), the step is skipped. See Section 12.1.2 for the mapping format and Section 11.5 for the full adaptation mechanism.

### 9.5 Output

A working Conda environment with all dependencies, framework packages, and quality tools installed and validated. A complete project directory structure. The pipeline state is updated to record pre-Stage-3 completion, including setting `total_units` to the number of units in the blueprint. Session boundary fires.

**`total_units` invariant (CHANGED IN 2.1 — Bug 24 fix):** `total_units` must be **derived from the blueprint** during infrastructure setup — by counting extracted units from the blueprint file. The infrastructure setup script is the **producer** of `total_units`, not a consumer. It must never read `total_units` from pipeline state (which is `null` at this point). The derivation sequence is: (1) extract units from the blueprint, (2) count them, (3) validate the count is a positive integer, (4) use the count for directory creation, (5) write the count to pipeline state. Any function that receives `total_units` as a parameter must validate it is a positive integer, not `None` — `dict.get("total_units", 1)` does not guard against an explicit `null` value (key exists with value `None`, so the default is not used). Required by unit completion logic to determine when Stage 4 should begin.

---

## 10. Stage 3: Unit-by-Unit Verification (CHANGED IN 2.0, CHANGED IN 2.1)

> **Governing invariants (Section 3.6):** Two-branch routing (command-presenting entries: `quality_gate_a_retry`, `quality_gate_b_retry`, `coverage_review`; gate-presenting: diagnostic escalation → Gate 3.2). Exhaustive dispatch tables (`dispatch_agent_status`, `dispatch_command_status` — see table in Section 3.6). COMMAND/POST separation. Orchestrator pipeline fidelity (no unit batching, no sub-stage skipping).

Units are processed in topological order as defined by the blueprint. No unit begins until the previous unit is fully verified.

### 10.0 Stage 3 Cycle Overview (CHANGED IN 2.1, CHANGED IN 2.2)

**`current_unit`/`sub_stage` co-invariant.** When `current_unit` is set (non-null), `sub_stage` MUST be non-null. The state management function that sets `current_unit` also sets `sub_stage` to `"stub_generation"` as an atomic operation. A state where `current_unit` is set but `sub_stage` is `None` is invalid and indicates a state corruption — the routing script must detect this and halt with a diagnostic message.

**Universal four-state test execution dispatch rule (NEW IN 2.2).** Every test execution `run_command` in the pipeline follows a four-state dispatch pattern:

| Status | Meaning | Action |
|--------|---------|--------|
| `TESTS_PASSED` | All tests pass | Advance to next sub-stage (stage-specific) |
| `TESTS_FAILED` | One or more tests fail | Enter fix/diagnostic path (stage-specific) |
| `TESTS_ERROR` | Test infrastructure error (collection failure, import error, framework crash) | Re-invoke the producing agent once with error output. If error persists after one retry, escalate to human. |
| Retries exhausted | Fix attempts exceeded limit | Present exhaustion gate (stage-specific) |

Per-stage handler customization: Stage 3 red run treats `TESTS_PASSED` as a defective-test signal (Section 10.4). Stage 3 green run uses the fix ladder (Section 10.10). Stage 4 uses the assembly fix ladder (Section 11.4). Stage 5 uses the bounded fix cycle (Section 12.4). The four states are universal; the handlers are stage-specific.

The complete per-unit cycle:

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

**Test import switch (pre-green-run requirement, NEW IN 2.1 — Bug 74 fix).** The test agent (step 3) writes tests that import from stub modules (`from src.unit_N.stub import ...`). This is correct for the red run (step 5), which verifies tests fail against the stub. After the implementation agent writes the real code (step 7), the test imports must be switched from stubs to real script modules (e.g., `from routing import ...`, `from pipeline_state import ...`) before the green run (step 9). Without this switch, the green run tests the stub (which may have different behavior than the real script), creating a false-pass scenario where tests pass but the deployed code is broken. This is the mechanism by which Bug 73-B hid: the stub had the correct fix, but `scripts/routing.py` did not. The import switch is a deterministic transformation: replace `from src.unit_N.stub import X` with `from <real_module> import X` using the stub-to-script module mapping. Gate C's structural check (step 5 of `check_stub_imports_in_tests`) validates that no stub imports remain in test files. The `pyproject.toml` `pythonpath` setting must include the `scripts/` directory so that real module imports resolve correctly. **(CHANGED IN 2.2)** For R units, the equivalent switch changes `source()` paths from stub files to real script modules (e.g., from `source("src/unit_N/stub.R")` to `source("R/real_module.R")`). The R import switch is a deterministic `source()` path rewrite: scan test files for `source("src/unit_N/stub.R")` patterns and replace with `source("<real_module_path>")` where the real module path is resolved from the stub-to-script module mapping. Gate C's structural check validates that no `source("src/unit_N/stub.R")` patterns remain in R test files after the switch. The path resolution mechanism is language-specific — see the language's registry entry (Section 40.2) for the switch mechanism and path resolution details.

If any step fails, the fix ladder engages. Quality gates (steps 4 and 8) are deterministic pre-processing steps, not new stages. They sit inside the existing cycle and follow the auto-fix-then-escalate pattern described in Section 10.12. When a quality gate fails, the cycle enters a retry sub-stage (`quality_gate_a_retry` or `quality_gate_b_retry`) that re-invokes the preceding agent for a fix re-pass before re-running the gate tools (see Section 10.12 for the full retry flow).

**(NEW IN 2.2) Language context injection.** Every Stage 3 agent invocation (test agent, implementation agent, coverage review agent) receives a `LANGUAGE_CONTEXT` section in its task prompt. This section contains:
- The unit's language (detected from blueprint code fence tags)
- Language-specific agent guidance (from `LANGUAGE_REGISTRY[language]["agent_prompts"][agent_type]`)
- The test framework name and conventions
- The quality tools that will check the code
- File extension and naming conventions

For widely-known languages, this context is informational. For less common languages or specialized frameworks, the language context is critical guidance that shapes the agent's output.

**(NEW IN 2.2) Per-unit language dispatch in Stage 3.** The Stage 3 cycle dispatches per-unit based on the unit's language:

- **Stub generation** (Section 10.2): Dispatches through `STUB_GENERATORS[language]` (Section 40.3). Generator behavior is language-specific; see language registry entries (Section 40.2).
- **Quality Gate A** (Section 10.3): Gate tool composition read from the language-specific toolchain file (`LANGUAGE_REGISTRY[language]["toolchain_file"]`).
- **Test execution** (Section 10.4, 10.7): Dispatches through `TEST_OUTPUT_PARSERS[language]` (Section 40.3). Test framework resolved from `LANGUAGE_REGISTRY[language]["test_framework"]`.
- **Quality Gate B** (Section 10.6): Same toolchain dispatch as Gate A, with heavier checks. Languages without a type checker (toolchain `quality.type_checker.tool` is `"none"`) skip the type-check step.

The dispatch key for each unit comes from the blueprint extractor's language detection. If a unit has no language tag, it defaults to the project's primary language.

**(CHANGED IN 2.2) Optional capability pattern.** When a language's toolchain specifies a quality tool as `"none"` (e.g., the R toolchain sets `quality.type_checker.tool: "none"`), all pipeline steps referencing that tool are skipped. This applies to type checking in Gates B and C, import sorting, and any other tool-specific step. The pipeline checks the toolchain value, not the language name — the mechanism is the same for all languages.

**(NEW IN 2.2)** The test file naming pattern for each unit is read from `LANGUAGE_REGISTRY[language]["test_file_pattern"]` — not hardcoded. The test execution dispatcher and test discovery logic use this registry value to locate test files for the current unit's language.

**Stage 3 autonomous execution principle (NEW IN 2.2).** Stage 3 runs autonomously through the per-unit cycle. The fix ladder (configurable retry budget via `iteration_limit`, default 3) executes without human gates. The human is consulted only when all autonomous fix attempts are exhausted — at Gate 3.2 (diagnostic escalation, Section 10.11). If the human's guidance resolves the issue, Stage 3 continues autonomously with the next unit. If the human cannot resolve it (FIX BLUEPRINT or FIX SPEC), the pipeline performs a ruthless reset to Stage 2 or targeted spec revision.

**Consequence:** Gate 3.1 (`gate_3_1_test_validation`) is removed as a human gate. Red-run exhaustion defaults to TEST CORRECT and enters the implementation fix ladder. The test-side fix ladder (fresh_test → hint_test) is removed. All test validation failures route to the implementation fix ladder.

**Scenarios — Per-unit verification.**
*Best case:* Tests generated, quality gate A passes (auto-fix only), red run confirms meaningful tests, implementation generated, quality gate B passes (auto-fix only), green run passes, coverage complete. Zero human interaction per unit.
*Worst case:* Quality gate B finds type errors that the agent cannot fix in one re-pass. Gate fails, enters the fix ladder. The implementation fix ladder exhausts all attempts. Diagnostic escalation (Gate 3.2) presents to the human. Diagnostic agent determines the blueprint contract is wrong. Document revision. Pipeline restarts from Stage 2.

### 10.1 Test Generation

**Prerequisite:** Stub generation (Section 10.2) must complete before test generation begins.

A test agent receives the current unit's definition from the blueprint (description, inputs, outputs, errors, invariants, contracts, machine-readable signatures) and the contracts of upstream dependencies. These are provided as the task prompt.

The test agent generates a complete test suite using the unit's test framework (`LANGUAGE_REGISTRY[language]["test_framework"]`), including synthetic test data matching any data characteristics in the stakeholder spec. The test agent does not see any implementation.

**Synthetic data assumption declarations.** The test agent must declare its synthetic data generation assumptions as part of its output. These assumptions are presented to the human at the test validation gate.

The test agent is told that its output will be automatically formatted and linted by quality tools **(NEW IN 2.1)**. This is communicated through the agent definition's system prompt — the agent should write clean code from the start.

The test agent receives `testing.readable_test_names` from the profile **(CHANGED IN 2.0)**.

**Lessons learned filtering for test agent (NEW IN 2.1).** When assembling the test agent's task prompt, Unit 9 filters the lessons learned document for entries relevant to the current unit. Filtering criteria (applied as a union — any match qualifies):

1. Entries where the affected unit number matches the current unit number.
2. Entries where the pattern classification (P1-P13) matches a pattern associated with the current unit's dependency structure: units with many upstream dependencies are P1 candidates; units that read pipeline state are P2/P3 candidates.

Filtering is deterministic — no LLM involvement. Unit 9 reads the bug catalog (Part 1) and extracts entries matching the criteria. The filtered entries are appended to the test agent's task prompt under a heading: "Historical failure patterns for this unit — write tests that probe these behaviors." If no entries match, this section is omitted.

This adds token cost proportional to the filtered entries. For units with no history, cost is zero. For units with relevant history, cost is bounded by the number of matching entries.

**Test agent prohibited patterns (NEW IN 2.2 — Bug S3-3, S3-6, S3-9).** The test agent definition must include the following explicit prohibitions:

1. **No `pytest.raises(NotImplementedError)` as behavioral test.** Stubs raise `NotImplementedError` by design; testing for that exception verifies the stub, not the contract. Every test must verify actual behavioral contracts from the blueprint. (Bug S3-3)
2. **No `pytest.skip()` for stub exceptions.** Tests must let `NotImplementedError` propagate as natural failures. A red run must show FAILED (not SKIPPED) for every test that exercises unimplemented functionality. Using `pytest.skip("Not yet implemented")` masks the red run signal and triggers the wrong retry path. (Bug S3-6)
3. **Always use `src.` prefix in imports.** Test files must use `from src.unit_N.stub import ...` — never bare `from unit_N.stub import ...`. The bare form causes `ModuleNotFoundError` at collection time because `unit_N` is not a top-level package. (Bug S3-9)

### 10.2 Stub Generation (CHANGED IN 2.1 — Bug 36 fix)

A deterministic script reads the machine-readable signature block from the blueprint and generates a stub module. **(CHANGED IN 2.2)** Stub generation dispatches through `STUB_GENERATORS[language]` (Section 40.3). The generator's behavior is language-specific — each language's stub body pattern is defined by its dispatch table implementation (see Section 40.2 built-in entries for Python and R specifics). [Python reference: uses `ast.parse()`, every function body raises `NotImplementedError`, every class body contains declared methods (each raising `NotImplementedError`) and class-level attributes (set to `None`).] The script also generates stub modules for upstream dependencies (same form as the current unit's stub — importable source files with correct function signatures in the unit's language).

**Routing sub-stage (Bug 36 fix).** Stub generation is step 1 in the per-unit cycle (Section 10.0) and has its own routing sub-stage: `"stub_generation"`. The routing script emits a `run_command` action to invoke the stub generator script. The invocation command is: `PYTHONPATH=scripts python -m stub_generator --blueprint <blueprint_contracts_path> --unit <unit_number> --output-dir <unit_src_dir> --upstream <comma_separated_upstream_unit_numbers>`. The arguments match Unit 9's CLI interface (Section 3.6, Bug 49 invariant): `--blueprint` is the path to `blueprint_contracts.md`, `--unit` is the current unit number, `--output-dir` is the unit's `src/unit_N/` directory, and `--upstream` is the comma-separated list of upstream unit numbers from the unit's Tier 3 dependency list (empty string if no dependencies). The routing script constructs these paths from `pipeline_state.json` fields (`project_root`, `current_unit`) and the blueprint extractor's dependency resolution. Both `sub_stage: None` (initial entry after unit completion resets sub-stage) and `sub_stage: "stub_generation"` emit the same `run_command` action with the same POST command — `route()` normalizes `None` to `"stub_generation"` before dispatching. The sub-stage transitions: on `COMMAND_SUCCEEDED`, advance to `"test_generation"`. On `COMMAND_FAILED`, the stub generator error (forward-reference violation, malformed signatures) is presented to the human. Stub generation MUST complete before test generation begins — the test agent's imports depend on the stub module existing.

**Forward-reference guard.** The stub generator validates that every dependency referenced in the current unit's Tier 3 has a lower unit number than the current unit. If a forward reference is detected (e.g., Unit 5 lists Unit 8 as a dependency), the stub generator fails with a clear error. This is the third line of defense after the blueprint checker (Stage 2) and the infrastructure DAG validation (Pre-Stage-3).

**Stub sentinel (NEW IN 2.1).** The stub generator must prepend the following line as the first non-import statement in every generated stub file:

```python
__SVP_STUB__ = True  # DO NOT DELIVER — stub file generated by SVP
```

This sentinel is a machine-detectable marker. It is not removed by the implementation agent when writing the implementation — it is absent from implementations because implementations are written as new files, not edits to stub files. The sentinel's presence in any file indicates the file has not been implemented.

**(CHANGED IN 2.2)** The stub sentinel is language-specific, read from `LANGUAGE_REGISTRY[language]["stub_sentinel"]` (Section 40.2). Each language's sentinel value is documented in its registry entry.

**Sentinel injection invariant (NEW IN 2.2 — Bug S3-2, S3-4):** The stub generator (Unit 10) MUST inject the exact sentinel string from `LANGUAGE_REGISTRY[language]["stub_sentinel"]` into every generated stub file verbatim. The agent or script producing stubs must use this exact string, not improvise its own sentinel format. The compliance scanner (Section 12.5) and delivery structural validation rely on exact string matching to detect undelivered stubs. Any deviation in sentinel format will cause false negatives in stub detection.

**Module-level constant defaults (NEW IN 2.2 — Bug S3-10).** Module-level annotated assignments (constants) in stubs must be assigned sensible default values to ensure importability. Dict-annotated constants get `{}`, List-annotated get `[]`, Set-annotated get `set()`, str-annotated get `""`, all others get `None`. A stub with a bare annotation (`X: Dict[str, str]`) is invalid — it must be `X: Dict[str, str] = {}`. This ensures test agents can import from stubs during red runs.

**Stub output filename (NEW IN 2.2 -- Bug S3-13, AMENDED BY S3-29).** The stub generator must produce output files named `stub{file_ext}` (e.g., `stub.py`, `stub.R`) for the current unit, not `unit_N_stub{file_ext}`. The unit number is encoded in the directory path (`src/unit_N/`), not the filename. **Exception:** Upstream dependency stubs generated by `generate_upstream_stubs` use `unit_N_stub{ext}` filenames to avoid overwriting when multiple upstream dependencies exist (see Bug S3-29, Section 24.62).

**Importability invariant.** The stub must be importable without error. Module-level `assert` statements are stripped from the parsed AST (they would fail against stub functions). Assertions inside function bodies are replaced along with the rest of the body. **(CHANGED IN 2.2)** Stub importability verification is language-specific — each language's `STUB_GENERATORS` implementation ensures the generated stub is loadable in that language's runtime (see Section 40.2 registry entries for language-specific importability requirements).

### 10.3 Quality Gate A: Post-Test, Pre-Red-Run (NEW IN 2.1)

After the test agent produces tests and before the red run, a deterministic quality checkpoint runs on the test files.

**Sub-stage:** `"quality_gate_a"`.

**Purpose:** Ensure test code is clean before the red run. Prevents false red-run failures from syntax issues, import problems, or formatting errors in tests.

**(CHANGED IN 2.2)** The tool commands below are the Python toolchain defaults. All languages resolve their gate tool commands from the language-specific toolchain file (`LANGUAGE_REGISTRY[language]["toolchain_file"]`, Section 6.5). The gate mechanism is identical for all languages; only the tool commands differ. Python reference examples appear throughout this section. They show the concrete toolchain values for the Python built-in language entry. Other languages resolve equivalent values from their own toolchain files.

[Python reference — from python_conda_pytest.json quality.gate_a:]

**Tools run (from `toolchain.json` `quality.gate_a`).** Each operation is resolved via `resolve_command` with `{target}` set to the test directory path (e.g., `tests/unit_N/`):
1. `ruff format {target}` — auto-fix formatting in place.
2. `ruff check --select E,F,I --fix {target}` — auto-fix basic errors (E), pyflakes (F), import sorting (I).

**Light lint rule set rationale:** Tests are about to fail by design (red run against stub). Heavy linting at this point would flag issues like "unused import" when the import is for the module under test that raises `NotImplementedError`. The light set catches real problems (syntax, undefined names, import order) without false positives from the stub-driven test structure.

**No type checking on tests.** Gate A does not run mypy on test files. Test code often uses dynamic fixtures, mock objects, and assertion patterns that produce false positives. Type checking runs only on implementation code (Gate B) and on the assembled project (Gate C).

**If auto-fix resolves everything:** Continue to red run. No agent involvement. This is the expected path — formatting and import sorting are fully mechanical.

**If residuals remain after auto-fix:** Issues that ruff cannot fix automatically (e.g., undefined name that isn't an import-sorting issue). The test agent gets one re-pass with the quality report appended to its task prompt. Sub-stage transitions to `"quality_gate_a_retry"`. After the re-pass, gate A runs again. If residuals persist after one retry, the gate **fails** and enters the implementation fix ladder (CHANGED IN 2.2).

**Retry budget:** 1 agent re-pass. This is separate from the fix ladder retry budget — if the gate fails after its retry and enters the fix ladder, the ladder gets its full budget.

### 10.4 Red Run

The main session runs the test suite against the stub via bash command. Test execution commands are resolved from `toolchain.json` **(CHANGED IN 2.0)**. Every test must fail. Three outcomes:

- **All tests fail:** structurally sound. Proceed to implementation. **State transition (Bug 45 fix):** `dispatch_command_status` for `test_execution` at `sub_stage=red_run` must advance `sub_stage` to `implementation` when `TESTS_FAILED` is received. A no-op return is invalid — it causes an infinite loop re-running the red run.
- **Some tests pass against the stub:** those tests are defective. Test suite is regenerated by a fresh test agent with the passing tests identified. Red run repeated. **State transition (Bug 65 fix, CHANGED IN 2.2):** `dispatch_command_status` for `test_execution` at `sub_stage=red_run` must increment `red_run_retries` when `TESTS_PASSED` is received, then: if retries < limit (default 3), advance `sub_stage` to `test_generation` for regeneration; if retries >= limit, autonomously treat tests as correct (TEST CORRECT) and enter the implementation fix ladder (Section 10.9). See Section 3.6 extended dispatch table.
- **Tests error (`TESTS_ERROR` — won't run):** syntax problems, import issues, malformed fixtures. Per the universal four-state dispatch rule (Section 10.0), the test agent is re-invoked once with the error output appended to its task prompt. If the error persists after one retry, the pipeline autonomously enters the implementation fix ladder (Section 10.9). Red run repeated after successful regeneration.

If the test suite fails the red run after the configured number of attempts (default 3, tracked as `red_run_retries`), the pipeline autonomously treats the tests as correct and enters the implementation fix ladder (Section 10.9).

Collection error indicators are read from the language registry entry's `collection_error_indicators` field (Section 40.2) **(CHANGED IN 2.0, CHANGED IN 2.2)**. The Python pipeline toolchain file (`testing.collection_error_indicators`, line 1087) retains a copy of these values for backward compatibility with pre-2.2 code paths, but the registry entry is the authoritative source for all languages including Python.

**"No tests ran" behavioral requirement.** The `"no tests ran"` indicator in the collection error list applies only when test files exist but the test framework reports no tests collected. The specific manifestation varies by framework (enumerated in `LANGUAGE_REGISTRY[language]["collection_error_indicators"]`, Section 40.2). An empty test directory with no test files present is a different condition — it indicates the test agent has not yet produced output — and must not be classified as a collection error. The dispatch logic must check for test file presence before applying this indicator.

### 10.5 Implementation

An implementation agent receives the same unit definition and generates the implementation in the unit's language. The implementation agent does not see the tests. This separation ensures that if the blueprint contains an ambiguity, the two agents are less likely to resolve it identically.

The implementation agent is told that its output will be automatically formatted, linted, and type-checked by quality tools **(NEW IN 2.1)**.

### 10.6 Quality Gate B: Post-Implementation, Pre-Green-Run (NEW IN 2.1)

After the implementation agent produces code and before the green run, a deterministic quality checkpoint runs on the implementation files.

**Sub-stage:** `"quality_gate_b"`.

**Purpose:** Ensure implementation is well-formed before testing. Catches type errors, style violations, and formatting issues that would either cause false test failures or produce sloppy code that passes tests.

**(CHANGED IN 2.2)** The tool commands below are the Python toolchain defaults. All languages resolve their gate tool commands from the language-specific toolchain file. Languages where the toolchain specifies `quality.type_checker.tool` as `"none"` skip the type-check step (see Section 10.0 optional capability pattern).

[Python reference — from python_conda_pytest.json quality.gate_b:]

**Tools run (from `toolchain.json` `quality.gate_b`, in order).** Each operation is resolved via `resolve_command` with `{target}` set to the implementation directory path (e.g., `src/unit_N/`):
1. `ruff format {target}` — auto-fix formatting in place.
2. `ruff check --fix {target}` — auto-fix all linting rules (full rule set).
3. `mypy {target} --ignore-missing-imports` — type check (report only, no auto-fix). The `--ignore-missing-imports` flag is specified in `toolchain.json` as `quality.type_checker.unit_flags`. At the unit level, mypy does not have visibility into upstream units' actual types — it checks only internal type consistency. Languages where `quality.type_checker.tool` is `"none"` omit step 3.

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

A coverage review agent reads the blueprint and the passing test suite to identify behaviors the blueprint implies but no test covers. Missing coverage is added. Newly added tests go through red-green validation as an atomic operation within coverage review: the red run executes the new tests against the stub (import switch toggles stub imports back temporarily), verifying the tests fail; the green run executes against the implementation (import switch toggles to real imports), verifying they pass.

**Quality gate exception (CHANGED IN 2.1).** Coverage review does not re-run the full quality gate A or B cycles. However, newly added test code must receive a minimum quality floor: after coverage review adds test files, the routing script runs auto-formatting on the new test files as a deterministic `run_command` immediately after coverage review completion, before advancing to the next sub-stage. Specifically, the routing script emits `run_command` actions for the Gate A auto-fix operations resolved from the unit's language-specific toolchain file (the `quality.gate_a` operation list). This is a formatting-only pass with no agent re-pass cycle, no type check, and no dedicated sub-stage — the auto-formatting commands execute within the `coverage_review` sub-stage's completion flow. If auto-fix resolves everything, continue to the red-green validation. Formatting residuals from coverage review auto-fix are silently accepted at this stage — they do not affect test correctness and are not eliminated but deferred: Gate C during Stage 5 assembly (Section 12.2) runs format check + full lint on the entire assembled project and will catch and fix them as part of the Stage 5 bounded fix cycle (Section 12.4). These deferred residuals will consume bounded fix cycle attempts in Stage 5; this is acceptable because formatting fixes are trivial for the git repo agent (auto-fix resolves them mechanically) and do not represent a meaningful draw on the Stage 5 retry budget. The implementation is not modified during coverage review, so Gate B does not re-run. If coverage review causes implementation changes (via the simplified fix ladder), those changes go through Gate B as part of the fix ladder's normal flow.

**State transition (Bug 46 fix, CHANGED — Bug 65 fix).** `dispatch_agent_status` for `coverage_review` returns state unchanged (keeps `sub_stage` at `coverage_review`). The two-branch routing pattern in `route()` reads `last_status.txt` to determine the next action: if `COVERAGE_COMPLETE: no gaps`, advance directly to `unit_completion`; if `COVERAGE_COMPLETE: tests added`, emit auto-format `run_command` before advancing. This change moves the dispatch logic from `dispatch_agent_status` to `route()` to support the two-branch pattern (Section 3.6 command-presenting entries).

**Green-run failure path.** If any newly added coverage test fails the green run, this follows the simplified fix ladder (Section 10.10). If a second coverage review produces tests that also fail, escalate directly to the diagnostic agent — the repeated coverage gap pattern is a diagnostic signal. The diagnostic agent's recommendation is constrained to either implementation-level (the coverage test is correct but the implementation has a gap) or blueprint-level (the contract is under-specified and the coverage test exposed it).

**(CHANGED IN 2.2) Coverage review invocation bound.** Coverage review is invoked at most twice per unit during the per-unit cycle. If a second coverage review produces tests that also fail and escalate to diagnostic (Gate 3.2), and the human selects FIX IMPLEMENTATION: on success, the unit proceeds through `green_run` and then directly to `unit_completion` WITHOUT invoking coverage review a third time. The coverage gap has been addressed by the diagnostic-guided fix.

**Coverage review bounded validation.** When coverage review identifies gaps and adds tests: (1) the new tests undergo bounded red-green validation within the coverage_review sub-stage (retry limit matches the pipeline's iteration_limit, default 3), (2) if tests pass, auto-format runs on the new test files, (3) the unit advances to completion. If new tests fail after retries, the pipeline enters the implementation fix ladder. If coverage review finds no gaps, the unit advances directly to completion.

### 10.9 On Fail: Test Validation (CHANGED IN 2.2)

**Entry condition:** Section 10.9 applies ONLY to red-run-exhaustion (the test suite has failed the red run after the configured number of attempts, tracked as `red_run_retries`). Green-run failures enter Section 10.10 (Implementation Fix Ladder) instead.

**Autonomous test validation (CHANGED IN 2.2).** When the red run exhausts its retry budget (`red_run_retries >= iteration_limit`), the pipeline autonomously treats the tests as correct and proceeds to the implementation fix ladder (Section 10.10). The diagnostic agent's analysis is generated and logged to the build log, but no human gate is presented.

**(CHANGED IN 2.2) Counter increment timing.** `red_run_retries` is incremented immediately when `dispatch_command_status` processes `TESTS_PASSED` at `sub_stage=red_run`, BEFORE the routing script advances to `test_generation` for regeneration. This ensures the counter reflects the number of completed red-run attempts, not pending ones. The increment-then-route ordering prevents off-by-one errors that could cause extra iterations beyond the configured limit.

Rationale: tests were generated from blueprint contracts and are structurally sound. If the tests are genuinely wrong, the implementation fix ladder will exhaust, and the diagnostic escalation (Gate 3.2) will surface the root cause — at which point the human IS consulted.

### 10.10 Implementation Fix Ladder

A deterministic escalation sequence when tests fail and the test is confirmed correct:

1. **Fresh agent attempt.** A fresh implementation agent receives: failing code, test failure output, diagnostic analysis, unit definition, upstream contracts, and any hint. Tests re-run.
2. **Diagnostic escalation.** If the fresh agent also fails, the diagnostic agent is invoked with the three-hypothesis discipline (Section 10.11).

**Position-aware ladder advancement.** The state-update script checks the current fix ladder position before advancing. The ladder progresses: `None → fresh_impl → diagnostic → diagnostic_impl → exhausted`. The handler advances to the *next* rung, never re-enters the current position.

**A single implementation-side fix ladder exists (CHANGED IN 2.2).** Ladder positions: None → fresh_impl → diagnostic → diagnostic_impl → exhausted. Entry points: green run TESTS_FAILED enters at None. Red-run exhaustion (Section 10.9) autonomously enters at None (TEST CORRECT assumed). Quality gate retry exhaustion enters the ladder (Gate A failure and Gate B failure both route to the implementation-side ladder). At exhaustion, Gate 3.2 presents to the human.

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

- **FIX IMPLEMENTATION** (CHANGED IN 2.2): one fresh agent attempt with diagnostic guidance and optional hint. The fix ladder advances to `diagnostic_impl` position. On success (green run `TESTS_PASSED`): proceed to `coverage_review` (or `unit_completion` if coverage review already completed twice per Section 10.8). On failure (green run `TESTS_FAILED`): ladder advances to `exhausted`, Gate 3.2 re-presents with only FIX BLUEPRINT and FIX SPEC options (FIX IMPLEMENTATION is no longer available at exhaustion).
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
- Gate A failure → enters the implementation fix ladder (CHANGED IN 2.2).
- Gate B failure → enters the implementation fix ladder (same as a green-run failure).

**Quality gate retries are separate from fix ladder retries.** The gate gets 1 retry. If it fails and enters the fix ladder, the ladder gets its full budget. Quality gates run again after the ladder produces new code. This prevents quality issues from stealing retry budget from logic issues.

**Quality gates are mandatory.** There is no opt-out flag. Formatting and linting are a pipeline guarantee. Every project built by SVP receives formatted, linted, type-checked code.

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

**(NEW IN 2.2) Stage 3 Completion Integrity Check.** Before advancing from Stage 3 to Stage 4, the routing script performs a routing-time validation (not a new sub-stage). The `route()` function calls `_validate_stage3_completion(state, project_root)` which checks:

1. **Unit count:** `len(verified_units) == total_units`. Every unit from 1 through total_units has an entry with a `timestamp` produced by `complete_unit()`.
2. **Build log sub-stage audit:** For each unit, `.svp/build_log.jsonl` must contain routing-script entries (`source: "routing"`) for ALL 9 required sub-stages: `stub_generation`, `test_generation`, `quality_gate_a`, `red_run`, `implementation`, `quality_gate_b`, `green_run`, `coverage_review`, `unit_completion`. Retry sub-stages (quality_gate_a_retry, quality_gate_b_retry) are optional — they appear only when gates fail.
3. **Red run validation:** For each unit, the build log must contain an `update_state` entry with `status_line` containing `TESTS_FAILED` during the `red_run` sub-stage. This proves the tests are meaningful — they fail against stubs.
4. **Green run validation:** For each unit, the build log must contain an `update_state` entry with `status_line` containing `TESTS_PASSED` during the `green_run` sub-stage. This proves the implementation satisfies the tests.

If any check fails, `route()` presents Gate `gate_3_completion_failure` with the diagnostic message listing the failing units and missing sub-stages. Gate response options: **INVESTIGATE** (invoke diagnostic agent with the completion failure details), **FORCE ADVANCE** (override the check and advance to Stage 4 — the human takes responsibility for the incomplete verification), **RESTART STAGE 3** (restart Stage 3 from unit 1 with a clean state).

This check is a routing-time precondition, not a new pipeline sub-stage. It does not appear in Stage 4's sub-stage enumeration and does not require two-branch routing entries.

### 10.14 Context Isolation

Each unit is processed in a fresh context window containing only:

- The stakeholder spec.
- The current unit's definition extracted from the blueprint (not the full blueprint).
- The contract signatures of upstream dependencies.

No prior unit's implementation code is loaded. Each unit is built assuming all others work according to their blueprint contracts. The extraction is a deterministic script operation, not LLM summarization.

### 10.15 Stage 3 Orchestrator Oversight Protocol (NEW IN 2.2)

The orchestrator is a detection instrument during Stage 3. It runs the checklists below at the specified checkpoints. When issues are detected, the orchestrator does not fix them directly — it delegates all fixing to agents through the normal pipeline cycle (routing script → agent invocation → state update). This protocol operationalizes the two principles (Section 3.31) for Stage 3.

#### 10.15.1 Per-Unit Checklist (every unit, no exceptions)

**After stub generation (4 items):**
1. Stub imports resolve against workspace (no dangling references to modules that don't exist yet).
2. Stub has `__SVP_STUB__` sentinel.
3. Signatures match Tier 2 block in the blueprint (parameter names, types, return types).
4. Cross-unit imports use correct paths for already-completed units.

**After test generation (4 items):**
5. Tests import from the stub path (not a hardcoded or incorrect module path).
6. Test names are descriptive (not `test_1`, `test_2`).
7. Tests cover Tier 3 contracts (behavioral requirements from the blueprint).
8. Tests cover error conditions (not just happy paths).

**After Gate A (1 item):**
9. Gate A ran all tools from the toolchain `gate_a` list (no tools skipped).

**After red run (3 items):**
10. Status is `TESTS_FAILED` (not `TESTS_PASSED`, not a collection error).
11. Failure count is positive (tests actually ran and failed, not zero tests collected).
12. Only constants and trivial stubs pass (if most tests pass, the stub is doing too much).

**After implementation (6 items):**
13. No `__SVP_STUB__` sentinel remains in the implementation.
14. All imports resolve against the workspace.
15. Exports match Tier 2 block (same public API as the stub).
16. No hardcoded values that should come from parameters or configuration.
17. Flag scope creep: implementation contains functionality not traceable to the unit's contracts.
18. Flag signature changes: any deviation from Tier 2 signatures.

**After Gate B (1 item):**
19. Gate B ran all tools from the toolchain `gate_b` list (no tools skipped).

**After green run (3 items):**
20. All tests pass.
21. No collection errors (every test file was found and loaded).
22. Test count ≥ red run test count (no tests were lost between red and green runs).

**After coverage review (2 items):**
23. Coverage review agent was actually invoked (not skipped).
24. Coverage supplements (if any) pass when run.

**Detected issues (2 items — checked at every checkpoint):**
25. Code fence contamination: Tier 2 blocks in the blueprint contain markdown code fences (` ``` `) that will be copied verbatim into generated code.
26. Language-mismatched blocks: Tier 2 blocks contain code in a language that doesn't match the unit's target language, causing language-specific parsing failures.

#### 10.15.2 Cross-Unit Checklist (every 5 units + stage boundary)

At every 5th completed unit and at the Stage 3 boundary (final unit), the orchestrator runs a cross-unit consistency check. Issues are delegated to the appropriate agent through the routing script.

**Namespace consistency (5 items):**
1. Terminal statuses identical across: spec Section 18.1, agent definition units, routing dispatch units.
2. Gate responses identical across: spec Section 18.4, GATE_VOCABULARY definitions, dispatch contract units.
3. Agent types identical across: KNOWN_AGENT_TYPES, AGENT_BLUEPRINT_LOADING, PHASE_TO_AGENT definitions.
4. Dispatch keys match: registry entries align with all dispatch table entries.
5. Import paths consistent: no unit imports a symbol from a path that was refactored in a later unit.

**Interface consistency (3 items):**
6. Cross-unit function signatures match both caller and callee (parameter names, types, order).
7. No stale references to functions or modules that were renamed or removed during implementation.
8. Return types consistent: what one unit returns matches what consuming units expect.

**API preservation (2 items):**
9. Stub-to-implementation API preserved: every public function in the stub exists in the implementation with the same signature.
10. Behavior matches tests: no implementation silently changes semantics while keeping the signature.

**Scope and symmetry (2 items):**
11. No scope creep: no unit implements functionality outside its blueprint contracts.
12. Interfaces symmetric: if unit A calls unit B's function, unit B's contracts include that function.

**Regression (1 item):**
13. Regression tests still pass against all completed units (no later unit broke an earlier one).

#### 10.15.3 Builder Integrity (checked continuously)

1. No `scripts/*.py` file has been modified since Pre-Stage-3 completion. The orchestrator does NOT compare file contents — it checks `git diff --name-only` (or file modification timestamps if not in a git repo) against the Pre-Stage-3 baseline.
2. If any builder script produces incorrect output or fails unexpectedly, the orchestrator MUST invoke the Hard Stop Protocol (Section 41). It MUST NOT modify builder scripts directly.

---

## 11. Stage 4: Integration Testing (CHANGED IN 2.0, CHANGED IN 2.1)

> **Governing invariants (Section 3.6):** Two-branch routing (command-presenting entry: integration test author → run test suite; gate-presenting entry: `regression_adaptation` → Gate 4.3). Gate ID consistency (Gates 4.1, 4.2, 4.3).

### 11.1 Integration Test Generation

**Two-branch routing requirement (NEW IN 2.1 — routing invariant).** Stage 4 is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `INTEGRATION_TESTS_COMPLETE`, `route()` must emit a `run_command` action to execute the integration test suite, not re-invoke the integration test author agent. This is a command-presenting entry (Section 3.6): the "done" branch runs the test suite deterministically rather than presenting a human gate. A regression test must verify both branches.

**Agent definition.**

| Property | Value |
|----------|-------|
| Name | Integration Test Author |
| Stage | 4 |
| Default model | Configured via `pipeline.agent_models.integration_test_author` (see Section 22.1 precedence). Defaults to Opus-class (correctness-critical) |
| Inputs | Stakeholder spec, all unit contract signatures, source files (on demand) |
| Outputs | Integration test files in `tests/integration/` |
| Terminal status | `INTEGRATION_TESTS_COMPLETE` |
| Interaction | Single-shot |

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

**(NEW IN 2.2)** The integration test suite must include at least one test verifying per-language dispatch: a test that invokes the stub generator, test output parser, and quality runner for each built-in language (Python and R) and confirms correct dispatch and output parsing. This is the earliest point where non-Python dispatch paths are verified. For `"mixed"` archetype projects, the integration test suite must additionally include cross-language bridge verification tests per Section 40.6.5 — at least one test per declared communication direction in `language.communication`.

### 11.2 Integration Test Execution

The main session runs the integration test suite via bash command. Test commands resolved from `toolchain.json` **(CHANGED IN 2.0)**.

**Explicit gate IDs for Stage 4:** `gate_4_1_integration_failure` (Gate 4.1 — integration test failure diagnostic), `gate_4_2_assembly_exhausted` (Gate 4.2 — assembly fix ladder exhausted), `gate_4_1a` (assembly fix human assist, step 3 of the assembly fix ladder). All three must be registered in both `GATE_VOCABULARY` and `ALL_GATE_IDS`.

#### 11.2.1 Four-State Post-Execution Dispatch (NEW IN 2.1, CHANGED IN 2.2)

**Relationship to the two-branch routing invariant (Section 3.6).** The two-branch routing invariant governs the transition *before* the integration test command runs (agent done vs. not done). The three-state dispatch governs the transition *after* the integration test command completes (pass vs. fail vs. exhausted). These are sequential, independent dispatch points. First, the two-branch check determines whether to invoke the integration test author agent or run the test suite. Then, after the test suite `run_command` completes, the three-state dispatch determines the next pipeline action based on the test result.

After the integration test `run_command` completes, the routing script performs four-state dispatch based on the test result status and retry count (per the universal four-state test execution dispatch rule, Section 10.0):

1. **Tests passed** (`TESTS_PASSED`): All integration tests pass. Advance to `regression_adaptation` sub-stage (Section 11.5).
2. **Tests failed** (`TESTS_FAILED`): One or more integration tests failed. Present the diagnostic gate (Section 11.4, Gate 4.1 `gate_4_1_integration_failure`).
3. **Tests error** (`TESTS_ERROR`): Test execution encountered a non-test error (import failure, collection error, infrastructure problem). Re-invoke the integration test author agent with the error output appended to its task prompt. This follows the universal `TESTS_ERROR` pattern: one automatic re-invocation before escalating to the human.
4. **Retries exhausted** (retries >= 3): The assembly fix ladder has been exhausted after three attempts. Present Gate 4.2 (`gate_4_2_assembly_exhausted`) with options **FIX BLUEPRINT** or **FIX SPEC**. No further assembly fix attempts.

This dispatch is a first-class behavioral requirement. The routing script must implement all four branches explicitly. A missing branch (e.g., no check for retries >= 3) causes the pipeline to loop indefinitely or present the wrong gate.

**Stage 4 test dispatch differentiation (NEW IN 2.2 — Bug S3-16).** `dispatch_command_status` for Stage 4 `test_execution` must differentiate: TESTS_FAILED presents Gate 4.1 (`gate_4_1_integration_failure`) for human decision; TESTS_ERROR re-invokes the integration test author; retries exhausted presents Gate 4.2 (`gate_4_2_assembly_exhausted`). Simple retry-increment without gate presentation is incorrect.

### 11.3 On Pass

Proceed to Stage 5.

### 11.4 On Fail

**Assembly fix agent.** The assembly fix uses the existing Implementation Agent (Section 21) with additional context (failure output, diagnostic guidance, interface-boundary constraint). No separate agent definition is needed — the implementation agent is re-invoked with enriched context. The preparation script assembles the enriched task prompt.

The diagnostic agent applies the three-hypothesis discipline. The task prompt directive instructs: "Integration test failures disproportionately originate from blueprint-level issues (incorrect contracts, missing cross-unit interfaces, wrong dependency edges). Evaluate the blueprint hypothesis FIRST and with the highest initial credence. Only conclude implementation-level if the blueprint contracts are clearly correct and the implementation deviates from them." Dual-format output.

Gate response options:

- **ASSEMBLY FIX**: units are correct individually; assembly has a localized error. Assembly fix ladder (three attempts):
  1. Fresh implementation agent with failure output, diagnostic guidance, and interface-boundary constraint. The **interface-boundary constraint** instructs the agent: "This fix MUST preserve the unit's existing Tier 2 contract signatures and Tier 3 behavioral contracts. Changes are limited to the implementation body — the unit's public interface (function signatures, return types, exception types) is frozen. If the fix requires a signature change, return `REPAIR_RECLASSIFY` to escalate to blueprint revision." Fix applied, affected unit tests re-run (where "affected unit tests" = tests for the modified unit(s) plus tests for all units that list the modified unit(s) as dependencies in their Tier 3 dependency list), then integration tests re-run.
  2. Same with first attempt's failure context.
  3. Gate `gate_4_1a` (assembly fix human assist): Human involved. Help agent available. Hint forwarded to a fresh implementation agent. If this fails or breaks unit tests, the ladder is exhausted. Gate 4.2: **FIX BLUEPRINT** or **FIX SPEC**.

- **FIX BLUEPRINT**: restart from Stage 2.
- **FIX SPEC**: targeted spec revision, then restart from Stage 2.

### 11.5 Regression Test Adaptation (NEW IN 2.2)

After all units pass individual verification and integration tests pass (Stage 4 complete), a regression test adaptation sub-stage runs before Stage 5 assembly. This addresses a real bug: when SVP N builds SVP N+1 and modules are reorganized, carry-forward regression tests break because their imports reference old module names. During the SVP 2.2 build, this caused 233 test failures.

**Sub-stage:** `stage: "4", sub_stage: "regression_adaptation"`.

The adaptation proceeds in four steps:

1. **Deterministic adaptation first:** `adapt_regression_tests.py` runs with `regression_test_import_map.json` against `tests/regressions/`. This handles the majority of cases (simple import renames) deterministically. See Section 12.1.2 for the mapping format and the script's capabilities.

2. **Run regression tests:** All regression tests in `tests/regressions/` are executed. If all pass, adaptation is complete -- proceed to Stage 5.

3. **Agent adaptation for failures:** If any regression tests fail after the deterministic script, a **Regression Test Adaptation Agent** is invoked. This agent:
   - Receives: the failing test files, the blueprint (unit-to-module mapping from the prose preamble file tree), a listing of all delivered modules (`scripts/*.py`), the assembly map (`assembly_map.json`), and the previous version's spec summary (so it knows old module names)
   - Reads each failing test, diagnoses the failure:
     - **Import failure** (fixable): Identifies the correct new module from the blueprint/file listing and rewrites the import
     - **Patch target failure** (fixable): Resolves the correct patch target by understanding where the name is used (not just where it is defined)
     - **Behavioral change** (needs human review): The test's assertion is incompatible with the new version's behavior -- flagged for human review, not auto-fixed
   - Rewrites fixable tests and re-runs them to verify
   - Reports unfixable tests (behavioral changes) to the human at a gate

4. **Human gate for behavioral changes:** If the adaptation agent identifies tests that fail due to behavioral changes (not just import issues), these are presented to the human at Gate 4.3 (`gate_4_3_adaptation_review`). The human decides for each flagged test whether to update the test, remove it (if the tested behavior intentionally changed), or investigate further. Gate response options: **ACCEPT ADAPTATIONS**, **MODIFY TEST**, **REMOVE TEST**.

**(NEW IN 2.2) Recovery from adaptation-induced failures.** If regression test adaptation introduces new integration test failures (the adapted test fails for a different reason than the original import error), the pipeline re-runs the integration test suite. If integration tests still pass, adaptation proceeds normally. If integration tests fail, the adaptation is rolled back for the affected test(s) using backup-based rollback: the adaptation script creates a backup copy of each test file before modification (at `<test_file>.bak`), and rollback restores from the backup. Those tests are then flagged for human review at Gate 4.3 as behavioral changes requiring manual resolution.

**Two-branch routing requirement (NEW IN 2.2 -- routing invariant).** The `regression_adaptation` sub-stage is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `ADAPTATION_COMPLETE` or `ADAPTATION_NEEDS_REVIEW`, `route()` must check the status: `ADAPTATION_COMPLETE` advances directly to Stage 5; `ADAPTATION_NEEDS_REVIEW` presents Gate 4.3 (`gate_4_3_adaptation_review`) for the human to review behavioral changes. A regression test must verify both branches.

**(NEW IN 2.2) Gate 4.3 dispatch contract:**
- **ACCEPT ADAPTATIONS:** Commits all adapted test files and advances to Stage 5. No version_document call (no spec/blueprint revision triggered).
- **MODIFY TEST:** Re-invokes the Regression Test Adaptation Agent targeting all flagged tests (not just one). The agent receives the human's guidance on what to change and re-processes all flagged tests.
- **REMOVE TEST:** Deletes the flagged regression test file and advances to Stage 5. The removal is logged in lessons learned. No version_document call.

Each response option has an explicit state transition in `dispatch_gate_response()`. No response option is a no-op.

When the adaptation agent flags multiple tests as behavioral changes, Gate 4.3 is presented ONCE with all flagged tests listed. The gate prompt includes each flagged test with the agent's diagnosis. The human reviews all flagged tests and selects one response for the batch:
- **ACCEPT ADAPTATIONS:** Accept all flagged tests as adapted. Advance to Stage 5.
- **MODIFY TEST:** Re-invoke the adaptation agent for all flagged tests with additional human guidance. The agent re-processes and Gate 4.3 re-presents with updated results.
- **REMOVE TEST:** Remove all flagged tests. Advance to Stage 5.

If the human needs different treatment for different tests (e.g., accept some, remove others), they select MODIFY TEST and provide specific instructions to the agent about which tests to keep, modify, or remove. The agent applies the instructions and Gate 4.3 re-presents with the remaining unresolved tests.

#### 11.5.1 Agent Definition

| Property | Value |
|----------|-------|
| Name | Regression Test Adaptation Agent |
| Stage | Post-Stage-4, pre-Stage-5 |
| Default model | Configured via `pipeline.agent_models.regression_adaptation` (see Section 22.1 precedence). Defaults to Sonnet-class (pattern-driven task) |
| Inputs | Failing test files, blueprint, assembly_map.json, module listing, previous spec summary |
| Outputs | Adapted test files + behavioral change report |
| Terminal status | `ADAPTATION_COMPLETE`, `ADAPTATION_NEEDS_REVIEW` |
| Interaction | Single-shot |

### 11.6 Stage 4 Orchestrator Oversight Protocol (NEW IN 2.2)

The orchestrator runs the following 6-item detection checklist after integration tests pass and regression test adaptation completes, before advancing to Stage 5. This protocol operationalizes the two principles (Section 3.31) for Stage 4: the orchestrator detects issues using the checklist; all fixing is delegated to the appropriate agent through the normal pipeline cycle.

#### 11.6.1 Integration Test Completeness (4 items)

1. Coverage completeness: integration tests cover all items in the required coverage list (Section 11.1, items 1-11) plus the per-language dispatch requirement. Each required item maps to at least one test.
2. Scope correctness: integration tests target cross-unit interactions (data flow across chains, resource contention, timing dependencies, error propagation across boundaries), not single-unit behavior already covered by Stage 3 unit tests.
3. Contract freshness: contract signatures the integration test author agent received match the current unit contracts on disk. Stale signatures from a prior build pass produce tests against outdated interfaces.
4. End-to-end depth: the integration test suite includes at least one test that validates a complete input-to-output scenario checking domain-meaningful output values (Section 11.1), not only structural or wiring tests.

#### 11.6.2 Adaptation Integrity (2 items)

5. Adaptation classification audit: every regression test the adaptation agent flagged as an "import fix" (Section 11.5) is actually an import or patch target change — not a disguised behavioral change where assertions or test logic were rewritten.
6. Over-adaptation detection: every adapted regression test still tests its original scenario. Only import paths and patch targets changed; expected values, assertions, and test logic are unmodified.

---

## 12. Stage 5: Repository Delivery (CHANGED IN 2.0, CHANGED IN 2.1)

> **Governing invariants (Section 3.6):** Two-branch routing (gate-presenting entries: Stage 5 → Gate 5.1; debug loop: triage → Gate 6.2/6.4, repair → Gate 6.3, regression test → Gate 6.1). Route-level state persistence (debug loop reassembly). Gate ID consistency (Gates 5.1, 5.2, 5.3, 6.0–6.5).

### 12.1 Repository Creation

**Two-branch routing requirement (NEW IN 2.1 — routing invariant, Bug 43 fix).** Stage 5 is governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `REPO_ASSEMBLY_COMPLETE`, `route()` must emit a `human_gate` action for Gate 5.1 (`gate_5_1_repo_test`), not re-invoke the git repo agent. If `route()` unconditionally re-invokes the agent without checking `last_status.txt`, the pipeline loops indefinitely after the repository is already assembled. A regression test must verify both branches.

The git repo agent creates a clean git repository in `projectname-repo/` at the same level as the project workspace. On successful repository creation, the pipeline records the absolute path of the delivered repository in `pipeline_state.json` as `delivered_repo_path` **(NEW IN 2.1)**. This path is deterministically available to all subsequent operations, including the post-delivery debug loop.

**Repo collision avoidance (NEW IN 2.1).** When the pipeline reaches Stage 5 and the target directory `projectname-repo/` already exists (e.g., from a previous pass before an `/svp:redo` triggered a restart), the git repo agent must not overwrite or merge into the existing directory. Instead, the existing directory is renamed to `projectname-repo.bak.YYYYMMDD-HHMMSS` (using the current UTC timestamp) before creating the new repository. This preserves the previous delivery for human inspection while ensuring a clean directory for the new assembly. The rename is performed by the git repo agent's `prepare_task.py` (Unit 9) during Stage 5 task prompt preparation — the agent always receives a clean target path. If multiple backup directories exist from prior passes, they are all preserved (no cleanup of older backups). The `delivered_repo_path` in `pipeline_state.json` is updated to reflect the new repository path, which is always `projectname-repo/` (the canonical name, not a timestamped variant).

Commits in order:

1. Environment file (`LANGUAGE_REGISTRY[language]["environment_file_name"]`), dependency list, directory structure — first commit.
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
6. Non-source deliverables (configuration files, templates, scripts in other languages) are produced as named string constants in the unit's implementation file (using the embedding style from `LANGUAGE_REGISTRY[language]["non_source_embedding"]`), extracted during assembly.

**(NEW IN 2.2)** During Stage 5 assembly, the git repo agent produces `assembly_map.json` -- a machine-readable bidirectional mapping between workspace paths and delivered repo paths. This file is stored at `.svp/assembly_map.json` in the workspace. It is generated automatically from the blueprint file tree annotations during assembly and updated on every Stage 5 reassembly.

Example format:
```json
{
  "workspace_to_repo": {
    "src/unit_14/routing.py": "svp/scripts/routing.py",
    "src/unit_5/pipeline_state.py": "svp/scripts/pipeline_state.py"
  },
  "repo_to_workspace": {
    "svp/scripts/routing.py": "src/unit_14/routing.py",
    "svp/scripts/pipeline_state.py": "src/unit_5/pipeline_state.py"
  }
}
```

This artifact is consumed by the triage agent (Stage 6), the oracle agent (Stage 7), and the artifact synchronization mechanism. It eliminates the need for agents to parse blueprint file tree annotations at runtime.
All paths are relative (workspace paths relative to workspace root, repo paths relative to repo root). The mapping is bijective: every workspace_to_repo entry has a corresponding repo_to_workspace entry. Generated deterministically from blueprint file tree annotations. A structural test verifies bijectivity.

### 12.1.2 Regression Test Import Adaptation (NEW IN 2.2)

When SVP N builds SVP N+1, carry-forward regression tests are copied from SVP N's test suite into the SVP N+1 workspace. These tests import from SVP N's module names. If SVP N+1 reorganizes its modules (splits, renames, relocates functions), these imports break.

SVP 2.2 introduces a deterministic import adaptation mechanism with two components:

1. **`scripts/adapt_regression_tests.py`** -- A deterministic utility script that reads a JSON mapping file and applies text replacements to all `.py` files in a target directory. It handles:
   - `from old_module import X` to `from new_module import X`
   - `import old_module` to `import new_module`
   - `@patch("old_module.X")` to `@patch("new_module.X")`
   - `patch("old_module.X")` to `patch("new_module.X")` (context manager form)

2. **`regression_test_import_map.json`** -- A per-project mapping file authored during Stage 2 (derived from the blueprint's unit split documentation). Format:
   ```json
   {
     "module_renames": {
       "old_module.function_name": "new_module.function_name",
       "svp_config.load_toolchain": "toolchain_reader.load_toolchain"
     },
     "module_aliases": {
       "command_logic": "cmd_save"
     }
   }
   ```

**Call sites:**
- **Pre-Stage-3 (optional):** The script runs on `tests/regressions/` in the workspace during infrastructure setup (Section 9.4), so carry-forward regression tests work during the build.
- **Post-Stage-4 regression adaptation (mandatory if mapping exists):** The adaptation sub-stage (Section 11.5) runs the script before invoking the adaptation agent for any remaining failures.
- **Stage 5 assembly (mandatory):** The git repo agent runs the script after copying regression tests into the delivered repo, before committing. This ensures the delivered repo has correctly adapted imports.

The mapping file is a deterministic, auditable artifact. A structural test verifies that every import in every regression test resolves after adaptation.

**(NEW IN 2.2) regression_test_import_map.json schema:**
```json
{
  "module_renames": {
    "svp_config.load_toolchain": "toolchain_reader.load_toolchain",
    "svp_config.get_framework_packages": "toolchain_reader.get_framework_packages",
    "command_logic": "cmd_save"
  },
  "module_aliases": {
    "command_logic": "cmd_save"
  }
}
```
The `module_renames` section maps old fully-qualified names to new ones (used for `from X import Y` and `@patch("X.Y")` replacements). The `module_aliases` section maps old module names to new ones (used for `import X` replacements). Generated by the blueprint author during Stage 2 when module reorganizations occur. For non-Python languages, the format extends with language-specific sections.

### 12.2 Quality Gate C: Assembly Quality Check (NEW IN 2.1)

During Stage 5 structural validation, after assembly and before the compliance scan, a cross-unit quality check runs on the complete assembled project.

**No dedicated sub-stage (CHANGED IN 2.1).** Unlike Gates A and B (which are routing-level checkpoints between agent invocations and have their own sub-stages), Gate C runs as part of the structural validation step within the git repo agent's assembly cycle. It does not have a `quality_gate_c` sub-stage in `pipeline_state.json`. This is because Gate C operates within the bounded fix cycle (Section 12.4) — if it finds issues, the git repo agent addresses them in its next assembly iteration. Gates A and B need sub-stages because they sit between different agent invocations (test agent to red run, implementation agent to green run) and the routing script must dispatch accordingly.

**Execution mechanism.** Gate C uses the same deterministic quality gate script as Gates A and B, invoked during the structural validation step (Section 12.3) with `"gate_c"` as the gate identifier. The gate identifier selects the operation list from `toolchain.json` (`quality.gate_c`) and the flags value (`type_checker.project_flags`), exactly as `"gate_a"` and `"gate_b"` do for their respective gates. The only difference is invocation context: Gates A/B are invoked by the routing script at routing-level checkpoints; Gate C is invoked by the structural validation script within the bounded fix cycle.

**(CHANGED IN 2.2)** The tool commands below are the Python toolchain defaults for Gate C. All languages resolve Gate C tool commands from the language-specific toolchain file. Languages where `quality.type_checker.tool` is `"none"` omit the type-check step. The gate mechanism is identical across languages.

[Python reference — from python_conda_pytest.json quality.gate_c:]

**Tools run (from `toolchain.json` `quality.gate_c`).** Each operation is resolved via `resolve_command` with `{target}` set to the assembled project source directory path. Target resolution is layout-dependent: for conventional layout, `{target}` resolves to `src/packagename/`; for flat layout, `{target}` resolves to the package directory at the repository root (e.g., `packagename/`); for SVP-native layout, `{target}` resolves to `src/` (the parent of all `unit_N/` directories). The structural validation script determines the correct target path from `delivery.source_layout` in the project profile. Example for conventional layout:
1. `ruff format --check {target}` — verify formatting (should already be clean from Gate B; this is belt-and-suspenders).
2. `ruff check {target}` — full lint on assembled project.
3. `mypy {target}` — cross-unit type check with full visibility. No `--ignore-missing-imports` — the full project is assembled so all imports should resolve. Languages where `quality.type_checker.tool` is `"none"` omit step 3.

**Purpose:** Catch cross-unit interface mismatches, naming collisions, and inconsistencies not visible at the single-unit level. Gate B checks each unit with `--ignore-missing-imports`; Gate C checks the assembled whole with full type resolution.

**Unused exported function detection (NEW IN 2.1 -- Bug 56 fix).** After lint and type check pass, Gate C scans the assembled codebase for exported functions (functions listed in Tier 2 signatures) that are defined but never called from any other module. This is a dead code detection check that catches functions implemented but never wired into the dispatch path (the pattern that produced Bugs 52-55). The detection mechanism must identify functions that are defined in one module but have zero call sites in any other module (excluding test files). The specific implementation approach (AST-based cross-reference scan, import graph analysis, or equivalent) is a blueprint decision — the behavioral requirement is: every exported function with no non-test call site is flagged. Functions that are only called from tests are NOT considered unused (test-only usage is valid).

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
- Language-appropriate project manifest (`LANGUAGE_REGISTRY[language]["project_manifest_file"]`) references final module paths.
- The SVP launcher (if Mode A) is self-contained.
- Quality Gate C passes (format check + full lint + type check where configured) **(NEW IN 2.1, CHANGED IN 2.2)**. Languages where the toolchain specifies no type checker run format check + full lint only.
- Delivery compliance scan passes (Layer 3 — see Section 12.5). Note: the compliance scan runs initially within the bounded fix cycle as part of structural validation, then runs again as a final verification in the `"compliance_scan"` sub-stage after human testing (Section 22.4).
- Commit structure matches the prescribed order (Section 12.1): one commit per prescribed step, minus any steps the profile disables (e.g., `vcs.changelog: "none"` omits the changelog commit). The expected count equals the number of enabled steps in the commit order table. A single monolithic commit is a structural validation failure **(NEW IN 2.1 — Bug 28 fix)**.
- All regression and unit tests pass when run in the delivered repository layout, not only the workspace layout. Path-dependent modules that are relocated during assembly (e.g., from `src/unit_N/` to `svp/scripts/`) must resolve correctly in the delivered layout **(NEW IN 2.1 — Bug 29 fix)**.
- No delivered source file contains the language-appropriate stub sentinel (`LANGUAGE_REGISTRY[language]["stub_sentinel"]`, Section 40.2). The presence of a stub sentinel in any assembled file means the git repo agent copied a stub instead of an implementation. This is an immediate structural validation failure. The error message must identify the offending file: "Structural validation failed: stub file detected in delivered repository. File: {path} contains stub sentinel." Enters the bounded fix cycle **(NEW IN 2.1, CHANGED IN 2.2)**.
- Both `blueprint_prose.md` and `blueprint_contracts.md` exist in `docs/`. A missing file is a structural validation failure. (The delivered `docs/` directory contains the complete blueprint as a paired artifact, not a single file.) **(NEW IN 2.1)**.
- Test framework path configuration enables tests to pass in the delivered repository layout, not only the workspace layout. The path configuration mechanism is language-specific (handled by `PROJECT_ASSEMBLERS[language]` during assembly). The test path configuration must reference the final module locations as specified in the blueprint file tree **(NEW IN 2.1 — Bug 29 fix, CHANGED IN 2.2)**.
- README is a carry-forward artifact in Mode A: content from the previous version's README (`references/README_v{previous}.md`) is preserved and extended, not rewritten. Structural validation checks that the reference README's headings and content lines are present in the delivered README (see Section 12.7) **(NEW IN 2.1 — Bug 30 fix)**.

Structural validation failures follow the bounded fix cycle.

### 12.4 Bounded Fix Cycle

1. The git repo agent assembles the repository.
2. Structural validation runs (Section 12.3).
3. The pipeline instructs the human with an exact test command to run in the delivered repository. The test command is derived from the language registry's test framework: for Python, `cd <repo_path> && conda run -n <env_name> pytest`; for R, `cd <repo_path> && Rscript -e "testthat::test_dir('tests')"`. The exact command template is read from `LANGUAGE_REGISTRY[language]["test_command_template"]`. The human runs this manually — verifying the repo is self-contained.
4. Gate response: **TESTS PASSED** or **TESTS FAILED** (with output pasted).
5. If fail: a fresh git repo agent reassembles with error output as context.
6. Up to `iteration_limit` attempts (Section 22.1, default: 3). If all fail, Gate 5.2: **RETRY ASSEMBLY**, **FIX BLUEPRINT**, or **FIX SPEC**.

### 12.5 Delivery Compliance Scan (Layer 3) (CHANGED IN 2.0)

During structural validation, a deterministic script reads the `delivery` section of `project_profile.json` and scans delivered source files for preference violations. **(CHANGED IN 2.2)** The compliance scan dispatches through `COMPLIANCE_SCANNERS[language]` (Section 40.3, Section 12.15.1).

**Scan scope.** Source files in `LANGUAGE_REGISTRY[language]["source_dir"]` and `LANGUAGE_REGISTRY[language]["test_dir"]`. Documentation, configuration, and end-user scripts are not scanned. The scan method is language-specific (the `COMPLIANCE_SCANNERS` dispatch table handles per-language scanning mechanics).

**Banned pattern sets** are defined per language in the registry entries (Section 40.2), keyed by the delivery environment recommendation. The compliance scanner reads the project's `environment_recommendation` from the profile and applies the corresponding pattern set.

[Python reference — banned patterns for "conda" environment: scan for `pip`, `python`, or `pytest` as bare tokens not preceded by `conda run -n`.]

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
4. Installation — from environment file (`LANGUAGE_REGISTRY[language]["environment_file_name"]`) and project manifest (`LANGUAGE_REGISTRY[language]["project_manifest_file"]`), matching delivery environment.
5. Configuration — if applicable.
6. Usage — CLI commands, API entry points, or library usage.
7. Quick Tutorial — if the project has a natural happy path.
8. Examples — if bundled examples exist.
9. Project Structure — directory tree of delivered repo.
10. License — from stakeholder spec.

Derive all content from the spec and blueprint. Omit inapplicable sections. Write for the project's target audience.

### 12.8 Delivered Source Layout (CHANGED IN 2.0)

The git repo agent reads `delivery.source_layout`. Valid layouts for the project's language are defined in `LANGUAGE_REGISTRY[language]["valid_source_layouts"]`. The assembly dispatch (Section 12.15.1) handles each layout's structural requirements. **(CHANGED IN 2.2)** Source layouts are language-specific:

| Layout | Language(s) | Structure |
|--------|------------|-----------|
| `conventional` | Python | `src/packagename/` with `__init__.py` |
| `flat` | Python | Package at repository root |
| `svp_native` | Python | Keeps `src/unit_N/` as-is |
| `package` | R | `R/`, `man/`, `DESCRIPTION`, `NAMESPACE` |
| `scripts` | R | Plain R scripts at root or `scripts/` |

**Note:** This table is the only place in Sections 10-12 where language-specific layouts are enumerated. It serves as a quick reference; authoritative layout definitions are in the registry entries.

**Module collision detection.** When `source_layout` is `conventional`, the git repo agent detects name collisions during restructuring. Collisions enter the bounded fix cycle.

### 12.9 Delivered Dependency Format (CHANGED IN 2.0)

The git repo agent reads `delivery.dependency_format` and generates the appropriate files. When multiple formats are specified, the first is the primary recommendation in README.

### 12.10 Entry Points (CHANGED IN 2.0)

If `delivery.entry_points` is true, the git repo agent generates language-appropriate entry points using the mechanism from `LANGUAGE_REGISTRY[language]["entry_point_mechanism"]` (Section 40.2). Languages where this is null skip entry point generation. Path format depends on `delivery.source_layout`. **(CHANGED IN 2.2)**

### 12.11 SPDX License Headers (CHANGED IN 2.0)

If `license.spdx_headers` is true, SPDX identifier comments added to all delivered source files.

### 12.12 Additional Metadata in Delivery (CHANGED IN 2.0)

The git repo agent acts on `license.additional_metadata`: citation → "How to Cite" section and `CITATION.cff`, funding → "Acknowledgments" section, acknowledgments → alongside funding, unknown keys → generic key-value list.

### 12.13 Delivered Quality Configuration (NEW IN 2.1)

The git repo agent reads the `quality` section from `project_profile.json` and generates quality tool configuration for the delivered project. **(CHANGED IN 2.2)** Configuration file locations are resolved from `LANGUAGE_REGISTRY[language]["quality_config_mapping"]`, which maps quality tool identifiers to config file paths. For each non-`"none"` quality tool, the git repo agent generates the configuration at the mapped path and adds the tool package to the language-appropriate dependency file.

- If `quality.linter` is not `"none"`: generates the appropriate configuration at the mapped path, adds the linter package to delivery dependency files.
- If `quality.formatter` is not `"none"`: generates formatter configuration, adds package to delivery dependencies.
- If `quality.type_checker` is not `"none"`: generates type checker configuration at the mapped path, adds package to delivery dependencies.
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
- An environment file (`LANGUAGE_REGISTRY[language]["environment_file_name"]`).
- Dependency files per `delivery.dependency_format`.
- `README.md` per profile preferences.
- A `.gitignore` excluding language-appropriate build artifacts (`LANGUAGE_REGISTRY[language]["gitignore_patterns"]`).
- A clean git history with commit messages per `vcs.commit_style`.
- Quality tool configuration per `quality` profile **(NEW IN 2.1)**.
- `CHANGELOG.md` per `vcs.changelog` **(NEW IN 2.1)**.
- `CITATION.cff` if `readme.citation_file` is true.
- `LICENSE` file matching `license.type`.
- `CONTRIBUTING.md` if `readme.contributing_guide` is true.
- For `"mixed"` archetype: secondary language source in `<secondary_language>/` subdirectory (per Phase 2 constraint, Section 40.6.4), secondary language tests in `<secondary_language>/tests/` subdirectory, quality tool configs for both languages, single `environment.yml` covering both languages and bridge libraries.

**Artifacts NOT included in delivered repo:** `toolchain.json` (pipeline config at workspace root), `project_profile.json`, `ruff.toml` (pipeline config at workspace root), `pipeline_state.json`, `svp_config.json`, conversation ledgers, diagnostic logs, raw iteration artifacts. Note: in Mode A (self-build), the delivered SVP plugin contains `svp/scripts/toolchain_defaults/python_conda_pytest.json` and `svp/scripts/toolchain_defaults/ruff.toml` as plugin artifacts — these are part of the blueprint file tree, distinct from the workspace-root pipeline config files that are excluded.

**Bundled examples (Mode A only):**
- `examples/game-of-life/` — Python Game of Life with stakeholder spec, blueprint, and project context. Carry-forward artifact.
- `examples/gol-python-r/` — Mixed archetype (Python primary, R secondary) Game of Life. See Section 40.6.7.
- `examples/gol-r-python/` — Mixed archetype (R primary, Python secondary) Game of Life. See Section 40.6.7.
- `examples/gol-r/` — R-only Game of Life. Exercises R archetype pipeline paths. See Section 35.6.
- `examples/gol-plugin/` — GoL spec generator Claude Code plugin. Exercises plugin archetype pipeline paths. See Section 35.6 and Section 40.7.10.

### 12.15.1 Language-Dispatch Assembly (NEW IN 2.2)

**(CHANGED IN 2.2) Language-dispatch assembly.** The git repo agent dispatches assembly through `PROJECT_ASSEMBLERS[language]`:

- **Python assembly:** Produces `pyproject.toml`, proper module paths, `__init__.py` files. Exact SVP 2.1 behavior.
- **R assembly:** Produces `DESCRIPTION`, `NAMESPACE`, R package structure. **(CHANGED IN 2.2)** When `delivery.r.documentation` is `"roxygen2"` (set during Option B dialog, Section 6.4), the R assembler invokes `devtools::document()` after placing source files to generate NAMESPACE and man pages from roxygen2 comments.
- **R/Shiny assembly:** Extends R assembly with Shiny-specific structure. When `delivery.r.app_framework` is `"golem"`, produces golem project structure (`R/`, `inst/`, `dev/`, golem config files). When `"rhino"`, produces rhino structure (`app/logic/`, `app/view/`, `rhino.yml`). When `"shiny"` (plain), produces minimal Shiny structure (`app.R` or `R/` with `ui.R`/`server.R`). All variants include shinytest2 test infrastructure in `tests/`.
- **Multi-language assembly (component):** Primary language determines project structure. Component language files (e.g., Stan) are placed in language-appropriate subdirectories.
- **Multi-language assembly (mixed archetype):** Two-phase composition. Phase 1: primary assembler creates root structure. Phase 2: secondary language files placed in `<secondary_language>/` subdirectory. See Section 40.6.4 for the eight composition constraints.

**Delivery quality config generation** is language-keyed:
- Python/ruff -> `ruff.toml`
- Python/black -> `pyproject.toml [tool.black]`
- Python/flake8 -> `.flake8`
- R/lintr -> `.lintr`
- R/styler -> `.styler.R`

Templates for these configs live in `scripts/delivery_quality_templates/[language]/`.

**Compliance scan** dispatches through `COMPLIANCE_SCANNERS[language]` to verify the delivered project meets language-specific quality standards.

### 12.16 Workspace Cleanup

Upon successful delivery, the pipeline congratulates the human, announces `/svp:bug` and `/svp:oracle` availability **(CHANGED IN 2.2)**, and offers `/svp:clean` with three options: archive, delete, or keep.

**Workspace cleanup constraints:**
- Build environment removed via the language-specific cleanup command. Python: `conda env remove -n {env_name} --yes`. R: `Rscript -e "renv::deactivate()"` followed by removal of the project-local `renv/` directory and `renv.lock`. Mixed archetype: `conda env remove -n {env_name} --yes` (single conda environment covers both languages — no renv cleanup). Dynamic languages: the configured environment removal command from the toolchain file (`environment.remove`).
- Directory deleted with permission-aware handler (`__pycache__` may be read-only).
- The delivered repository is never touched by `/svp:clean`.
- Invoked as `PYTHONPATH=scripts python scripts/cmd_clean.py`.

### 12.17 Stage 5 Orchestrator Oversight Protocol (NEW IN 2.2)

The orchestrator runs the following 10-item detection checklist after Stage 5 assembly completes and structural validation passes, before presenting the delivered repository to the human for testing. This checklist covers cross-artifact consistency that structural validation scripts cannot verify and confirms that mandatory validation steps executed. This protocol operationalizes the two principles (Section 3.31) for Stage 5: the orchestrator detects issues; all fixing flows through the git repo agent via the bounded fix cycle (Section 12.4).

#### 12.17.1 Cross-Artifact Consistency (7 items)

1. Assembly map bijectivity: every `workspace_to_repo` entry in `assembly_map.json` has a corresponding `repo_to_workspace` entry, and vice versa. No orphaned entries in either direction.
2. Assembly map completeness: every blueprint file tree `<- Unit N` annotation has a corresponding assembly map entry. No blueprint-declared deliverable file is missing from the map.
3. No surviving workspace references: delivered repository source files contain no `src.unit_N` or `src/unit_N` import paths. These workspace-internal paths must all be rewritten to final module paths during assembly (Section 12.1.1 Rule 3).
4. Commit order matches Section 12.1 prescribed sequence: environment file first, spec second, blueprint third, units in topological order, then integration tests, configuration, history, references, context, quality config, changelog. Expected count equals the number of enabled steps (profile may disable some).
5. Source layout matches `delivery.source_layout` from project profile. The layout must be a member of `LANGUAGE_REGISTRY[language]["valid_source_layouts"]`. Layout-specific structural requirements are verified by the assembly dispatch (Section 12.15.1).
6. Delivered quality configuration in the files specified by `LANGUAGE_REGISTRY[language]["quality_config_mapping"]` references the human's profile-chosen tools (from the `quality` section of `project_profile.json`), not the pipeline's internal tools. The delivered project ships with what the human chose, not what the pipeline used (Section 12.13).
7. README carry-forward (Mode A only): all headings from the reference README (`references/README_v{previous}.md`) are present in the delivered README. Content was extended, not rewritten (Section 12.7). Skip this item for Mode B projects.

#### 12.17.2 Validation Meta-Oversight (3 items)

8. Structural validation (Section 12.3) completed: the build log contains a structural validation entry for the current assembly pass. The orchestrator confirms the validation ran rather than trusting it implicitly.
9. Regression test adaptation applied to delivered tests: if `regression_test_import_map.json` exists, the adaptation script (Section 12.1.2) ran on the delivered test copies during assembly. Delivered regression test imports resolve correctly.
10. Compliance scan (Section 12.5) ran against delivered files: the build log contains a compliance scan entry for the current assembly pass. Compliance findings (if any) entered the bounded fix cycle.

### 12.18 Post-Delivery Debug Loop (CHANGED IN 2.1, CHANGED IN 2.2)

After Stage 5 completion, the human may discover bugs. `/svp:bug` initiates a structured debug loop.

**(CHANGED IN 2.2)** The triage agent and repair agent are language-aware. The triage agent's task prompt includes the unit's language and the relevant language-specific context. The repair agent generates fixes in the unit's language using the language-specific agent prompts. All existing debug loop behavior (triage, classification, fix ladders, regression tests, lessons learned, reassembly) is unchanged.

#### 12.18.1 Entry Point and Debug Permission Reset

`/svp:bug` serves as the entry point. The human does not classify the problem. **Precondition:** workspace intact, one debug session at a time.

The preparation script resolves the delivered repo path from `pipeline_state.json` (`delivered_repo_path`) and includes it in the triage agent's task prompt **(NEW IN 2.1)**. The agent never guesses or asks for the repo location. **(CHANGED IN 2.2)** The triage agent's task prompt also includes `assembly_map.json` (`.svp/assembly_map.json`) so the agent can map human-reported repo paths back to workspace unit paths and vice versa.

**Gate 6.0 (debug permission reset).** The bug triage agent begins in read-only mode. After gathering information, the pipeline presents: **AUTHORIZE DEBUG** or **ABANDON DEBUG**. On authorize, `update_state.py` activates all debug write rules — including write access to the delivered repo path and the lessons learned document. On abandon, return to "Stage 5 complete."

#### 12.18.2 Triage Classification

The triage agent classifies:
- **Build/environment issue:** code doesn't run, fails at import, environment error.
- **Logic bug:** code runs but produces wrong results.

#### 12.18.3 Build/Environment Fix Path (Fast Path)

No regression test needed. Repair agent fixes directly. Narrow mandate: can modify environment files, package config, `__init__.py`, directory structure. Cannot modify implementation files. Up to `iteration_limit` attempts (Section 22.1, default: 3). If fix requires implementation changes, returns `REPAIR_RECLASSIFY`.

#### 12.18.4 Logic Bug Path (Full Path) (CHANGED IN 2.1)

The logic bug path follows a seven-step workflow. Steps 1-2 involve human dialog and classification confirmation (Gate 6.2). Steps 3-4 are largely autonomous. Step 5 includes a human review gate (TEST CORRECT/TEST WRONG). Step 6 is autonomous. Step 7 requires explicit human permission for commit/push.

**Two-branch routing requirements for debug loop agents (NEW IN 2.1 — routing invariant, Bug 43 fix).** The following debug loop agent-to-gate transitions are governed by the two-branch routing invariant (Section 3.6):

- **Triage agent to Gate 6.2:** When `last_status.txt` contains `TRIAGE_COMPLETE: single_unit` or `TRIAGE_COMPLETE: cross_unit`, `route()` must emit a `human_gate` action for Gate 6.2 (`gate_6_2_debug_classification`), not re-invoke the triage agent. When `last_status.txt` contains `TRIAGE_COMPLETE: build_env`, `route()` must route directly to the build/environment repair agent via the fast path (Section 12.18.3), bypassing Gate 6.2.
- **Triage agent to Gate 6.4 (non-reproducible):** When `last_status.txt` contains `TRIAGE_NON_REPRODUCIBLE`, `route()` must emit a `human_gate` action for Gate 6.4 (`gate_6_4_non_reproducible`), not re-invoke the triage agent.
- **Repair agent outcome dispatch:** When `last_status.txt` contains `REPAIR_COMPLETE`, `route()` must route to the success path (reassembly and debug completion per Section 12.18.6), not re-invoke the repair agent. When `last_status.txt` contains `REPAIR_RECLASSIFY` or `REPAIR_FAILED` (with retries exhausted), `route()` must emit a `human_gate` action for Gate 6.3 (`gate_6_3_repair_exhausted`), not re-invoke the repair agent (see also Section 12.18.8).
- **Test agent (regression test mode) to Gate 6.1:** When `last_status.txt` contains `REGRESSION_TEST_COMPLETE`, `route()` must emit a `human_gate` action for Gate 6.1 (`gate_6_1_regression_test`), not re-invoke the test agent.

Each of these transitions must have an explicit `last_status.txt` check in `route()`. Without the check, the pipeline loops indefinitely re-invoking the agent after its work is already done. The universal compliance regression test (`test_bug43_stage2_blueprint_routing.py`) verifies all of these transitions.

**Step 1 — Prompt human for directions.** Socratic triage dialog oriented toward reproducing the bug with concrete inputs/outputs/assertions. Real data access for diagnosis; regression test uses synthetic data. Triage output: affected unit(s), root cause hypothesis, regression test specification, classification (build_env, single_unit, or cross_unit). The `build_env` classification routes to the build/environment fast path (Section 12.18.3), bypassing Gate 6.2; `single_unit` and `cross_unit` classifications proceed to Gate 6.2 for human confirmation. The triage report (`.svp/triage_result.json`) is appended to the revision agent's task prompt when the debug session triggers targeted spec or blueprint revision.

**Step 2 — Investigate the bug and propose classification.** The triage agent applies the three-hypothesis discipline (Section 10.11): implementation-level, blueprint-level, or spec-level. The agent reads workspace source, tests, blueprint contracts, and the delivered repo (via `delivered_repo_path` and `assembly_map.json` for path correlation) to produce a structured diagnosis. **Bug number assignment:** The triage agent assigns a bug number derived from `len(debug_history) + 1`, cross-checked against the highest existing regression test number (scanning `tests/regressions/test_bug*.py` filenames) to avoid collisions. The triage agent proposes a classification but does not act on it — the human confirms at Gate 6.2 before any fix is applied. After classification, the triage agent must write `.svp/triage_result.json` with `{"affected_units": [N, M, ...], "classification": "<type>", "bug_number": N}` (Bug 93 fix: routing dispatch reads this file to populate the debug session's `affected_units` for Gate 6.2 FIX UNIT dispatch).

**Missing `triage_result.json` handling.** If `triage_result.json` is missing after triage agent completion (expected at `.svp/triage_result.json`), the routing script re-invokes the triage agent once with an explicit instruction to write the result file. If the result file is still missing after the second invocation, the pipeline presents Gate 6.4 (`gate_6_4_non_reproducible`) for the human to decide whether to retry triage or abandon.

**Gate 6.2 (debug classification).** The pipeline presents the triage agent's diagnosis and proposed classification to the human. Gate response options: **FIX UNIT**, **FIX BLUEPRINT**, **FIX SPEC**, or **FIX IN PLACE**. The human may accept the triage agent's recommendation or override it. No fix is applied until the human confirms at this gate.

**Step 3 — Apply the confirmed fix.** After the human confirms the classification at Gate 6.2, the fix is applied in the workspace first, where the agent has unit structure, blueprint context, and pipeline machinery. The fix type follows the confirmed classification:

- **FIX UNIT (single-unit code fix):** Contract correct, implementation wrong for this case. The pipeline calls `rollback_to_unit(state, N)` where N is the lowest affected unit from the triage classification. This invalidates all verified units >= N (removes them from `verified_units`), deletes source and test files for units >= N, sets `stage: "3"`, `current_unit: N`, `sub_stage: None`, `fix_ladder_position: null`, `red_run_retries: 0`. The pipeline then rebuilds from unit N forward through all remaining units (test generation + implementation for each). Quality Gates A and B run normally during re-entry. The `debug_session` object tracks re-entry (phase transitions to `"stage3_reentry"`). Steps 4-7 follow.
- **FIX BLUEPRINT (cross-unit contract problem):** Blueprint problem. Targeted blueprint revision, ruthless forward restart. Regression test preserved. Steps 4-7 do not apply — the pipeline restarts from Stage 2 (complete pipeline re-entry).
- **FIX SPEC:** Spec-level gap. Targeted spec revision, then restart from Stage 2. Steps 4-7 do not apply — the pipeline restarts from Stage 1 revision (complete pipeline re-entry).
- **FIX IN PLACE (surgical fix):** The human has already applied the fix directly to workspace scripts and the delivered repository. No rollback, no unit rebuild. The pipeline proceeds directly to regression test writing (Step 5), lessons learned (Step 6), and commit (Step 7). This path is appropriate when the fix is small enough to apply manually and the human is confident the fix is correct in both locations. **(CHANGED IN 2.2)** After FIX IN PLACE, the pipeline runs a post-fix structural validation step: `structural_check.py` is executed against the delivered repo, and the affected files are verified for content consistency between workspace and repo using `assembly_map.json`. If the workspace and repo copies of any affected file differ, the human is warned before proceeding to regression test authoring.

After the workspace fix passes all existing tests (unit, regression, and integration — distinct from the new regression test authored in Step 5), the pipeline performs a full Stage 5 reassembly to the delivered repo. This preserves the assembly mapping as a one-way function — workspace to repo, never the reverse.

**Step 4 — Evaluate whether spec or blueprint need revision (FIX UNIT path only).** After the fix is applied, the agent evaluates whether the root cause reveals a gap in the spec or blueprint. A fix that works may still indicate an incomplete spec (P7 pattern — the implementation faithfully followed an omission). If a document-level issue is identified, the agent flags it and initiates targeted revision per the three-hypothesis classification from Step 2.

**Gate 6.1a — Divergence Warning (`gate_6_1a_divergence_warning`).** If FIX IN PLACE post-fix structural validation detects workspace/repo divergence on affected files, the pipeline presents `gate_6_1a_divergence_warning` before proceeding to regression test authoring. Gate response options: **PROCEED** (acknowledge divergence, continue to Step 5), **FIX DIVERGENCE** (return to manual fix — human resolves the divergence), **ABANDON DEBUG** (calls `abandon_debug_session`). This gate is only reached via the FIX IN PLACE path when validation detects inconsistency.

**Step 5 — Write regression tests.** Test agent writes a failing regression test to `tests/regressions/test_bugNN_descriptive_suffix.py` (where NN is the unified bug catalog number and the suffix describes the bug scenario; see Section 6.8 for the naming convention). Must fail against the pre-fix implementation. Must pass against the post-fix implementation. Human reviews at Gate 6.1 (`gate_6_1_regression_test`): **TEST CORRECT** or **TEST WRONG**. **(CHANGED IN 2.2)** Regression tests authored during the debug loop MUST use layout-agnostic imports that work in both the workspace layout and the delivered repository layout. The test agent receives the delivered repo layout information (from `assembly_map.json`) to ensure imports resolve correctly in both environments. This extends the existing regression test target invariant (Section 3.6, Bug 74 fix) to debug loop test authoring. **(CHANGED IN 2.2)** When authoring regression tests for non-Python units, the test agent uses the unit's language from `UnitDefinition.languages`. Python regression tests use pytest; R regression tests use testthat. The task prompt includes language-specific test authoring examples and `assembly_map.json` for correct import path selection. Tests must be layout-agnostic: they must run in both workspace and delivered repo layouts.

**Step 6 — Update lessons learned document.** **(CHANGED IN 2.2)** The agent appends a new entry to `references/svp_2_1_lessons_learned.md` in the **workspace** (the canonical source) following the established catalog format: bug number, how caught, test file reference, description, root cause pattern classification (P1-P13 or new pattern with definition), and prevention rule. Stage 5 reassembly propagates this to `docs/svp_2_1_lessons_learned.md` in the delivered repository. The agent does NOT write directly to the delivered repository's `docs/` directory -- all propagation goes through reassembly. This eliminates the risk of reassembly overwriting direct repo writes. If the bug reveals a new pattern not covered by existing patterns, the agent defines the pattern and adds it to the pattern catalog. The agent also updates the regression test file mapping table in the workspace. CHANGELOG.md and README.md bug counts are updated in the workspace and propagated to the delivered repository via Stage 5 reassembly. The agent must NOT write separately to `docs/references/` -- a deterministic post-triage sync script (Section 12.18.6) handles copy propagation.

**Step 7 — Commit and push (human permission required).** The agent prepares a commit with a detailed, fixed-format debug commit message (see Section 12.18.11) and presents it to the human for approval. Gate 6.5 (`gate_6_5_debug_commit`) response options: **COMMIT APPROVED** or **COMMIT REJECTED**. On approval, the agent commits and pushes. On rejection, the human may edit the commit message or abort.

#### 12.18.5 Regression Test Survival

`tests/regressions/` is protected — ruthless restart never touches it. Unit-level regressions run with affected unit's tests. Cross-unit regressions run with integration tests.

#### 12.18.6 Completion and Repo Reassembly

After successful fix: all unit tests pass, all regression tests pass, integration tests pass, full Stage 5 repo reassembly to `delivered_repo_path`, debug session recorded in history, lessons learned document updated. After `REPAIR_COMPLETE`, the routing script must re-enter Stage 5 with `sub_stage=None` to trigger git_repo_agent reassembly. The debug session remains active during reassembly. This ensures the workspace fix is propagated to the delivered repository through the canonical assembly path.

**(CHANGED IN 2.2)** ALL debug loop completions -- whether via the full FIX UNIT path, the build/environment fast path, or FIX IN PLACE -- trigger Stage 5 reassembly to propagate workspace changes to the delivered repository. The only exception is FIX IN PLACE with the human explicitly confirming that both locations are already in sync (verified by post-fix structural validation).

**(NEW IN 2.2)** If Stage 5 reassembly (triggered after a debug loop fix) fails and escalates to Gate 5.2, and the human selects FIX BLUEPRINT or FIX SPEC (which triggers a pipeline restart from an earlier stage), the active debug session is terminated. The redo triggered by Gate 5.2 takes precedence over the debug session. The debug session's findings (triage report, regression tests authored so far) are preserved in the workspace but the debug session state in `pipeline_state.json` is cleared.

**Artifact synchronization invariant (NEW IN 2.1).** Every artifact that exists in both the workspace and the delivered repository must be kept in sync. When a fix modifies any workspace artifact that has a corresponding copy in the delivered repository, the delivered copy must be updated as part of the same fix. This applies regardless of whether the fix follows the formal debug loop (agent-driven with reassembly) or is applied directly by the main session. The dual-copy artifacts are:

- **Python source files:** workspace `src/unit_N/` and `scripts/` → delivered `svp/scripts/` (via assembly mapping)
- **Command files:** workspace `*_MD_CONTENT` constants in Unit 20 → delivered `svp/commands/*.md`
- **Skill files:** workspace `SKILL_MD_CONTENT` constant in Unit 21 → delivered `svp/skills/orchestration/SKILL.md`
- **Agent definitions:** workspace `*_AGENT_MD_CONTENT` constants → delivered `svp/agents/*.md`
- **Hook configurations:** workspace Unit 12 constants → delivered `svp/hooks/hooks.json`
- **Documentation:** workspace `specs/`, `blueprint/`, `references/` → delivered `docs/`, `docs/references/`

When full Stage 5 reassembly is not triggered (e.g., direct fixes outside the formal debug loop), the main session must manually propagate changes to all affected delivered copies. A fix that updates a workspace artifact without updating its delivered counterpart creates documentation drift — the same failure mode the pipeline is designed to prevent.

**Documentation sync invariant (NEW IN 2.1 — Bug 87 fix, CHANGED IN 2.2).** The documentation sync script (`sync_debug_docs.py`) runs at TWO points: (1) after triage agent completion (before Gate 6.2), syncing triage-generated documentation, and (2) after Step 6 completion (lessons learned update), syncing the updated lessons learned document. This ensures workspace and delivered repo documentation copies remain in sync throughout the debug loop, not just after triage. However, the canonical write target for all documentation is the workspace -- sync propagates workspace changes to the repo, not the reverse. The script: (a) copies `docs/svp_2_1_lessons_learned.md` to `docs/references/svp_2_1_lessons_learned.md` in the delivered repository (single source of truth: workspace wins), (b) copies `docs/svp_2_1_summary.md` to `docs/references/svp_2_1_summary.md`, (c) syncs both documents back to workspace `references/`, (d) stages and commits all dirty documentation files (CHANGELOG, README, lessons_learned, summary). The triage agent and repair agent write only to the workspace -- never to the delivered repo directly. This eliminates the three documentation sync gaps identified in Bug 87.

#### 12.18.7 Non-Reproducible Bugs

If triage cannot produce a failing test after iteration limit: revised hypothesis (retry triage), environmental mismatch (ask for more data characteristics), or genuinely non-reproducible (structured report). Gate 6.4 (`gate_6_4_non_reproducible`): **RETRY TRIAGE** or **ABANDON DEBUG**.

#### 12.18.8 Repair Agent Exhaustion

Gate 6.3: **RETRY REPAIR**, **RECLASSIFY BUG**, or **ABANDON DEBUG**. RECLASSIFY BUG resets `triage_refinement_count` and `repair_retry_count` to 0, deletes `.svp/triage_result.json`, resets the debug phase to triage, and clears the existing classification, allowing the triage agent to re-investigate with a fresh hypothesis (Bug 69 fix). RECLASSIFY does NOT revert any repair changes already applied — the workspace state is carried forward. **(CHANGED IN 2.2) Reclassification bound:** RECLASSIFY BUG may be selected at most 3 times per debug session. After 3 consecutive reclassifications without successful repair, the routing script presents only RETRY REPAIR and ABANDON DEBUG — RECLASSIFY is no longer offered. ABANDON DEBUG calls `abandon_debug_session` and returns to "Stage 5 complete."

#### 12.18.9 Debug Session Abandonment

`/svp:bug --abandon` cleans up and returns to "Stage 5 complete." Ledger renamed to `bug_triage_N_abandoned.jsonl`.

**`abandon_debug_session` postconditions (closed set):**
1. `debug_session` field in `pipeline_state.json` set to `null`.
2. Active triage ledger renamed to `bug_triage_N_abandoned.jsonl`.
3. `.svp/triage_result.json` deleted (if exists).
4. `stage` restored to `"5"`, `sub_stage` restored to `"repo_complete"` (Stage 5 complete state).
5. `fix_ladder_position` set to `null`, `red_run_retries` set to `0`.

**Auto-abandon on pipeline restart.** If `debug_session` is active when `restart_from_stage` is called (e.g., due to FIX BLUEPRINT or FIX SPEC classification that triggers a pipeline restart), `restart_from_stage` calls `abandon_debug_session` as its first action before performing the stage reset. This ensures no orphaned debug sessions persist across pipeline restarts.

#### 12.18.10 Dual Write-Path During Debug (NEW IN 2.1)

During the debug loop, two write paths coexist: agent writes (through Claude Code's Write tool, gated by hooks) and pipeline subprocess writes (quality tools, assembly scripts, bypassing hooks). This is the same dual write-path that operates during the build (Section 10.12). The hook system authorizes agent writes to debug-permitted paths; subprocess writes from pipeline scripts operate independently. The blueprint author must not conflate these paths — a hook that blocks agent writes to the delivered repo does not block the reassembly script's subprocess writes, and vice versa.

#### 12.18.11 Debug Commit Message Format (NEW IN 2.1)

Debug commits use a fixed format regardless of the project's `vcs.commit_style` setting. Debug commits are pipeline infrastructure, not project development, and a consistent structure makes the regression history scannable across projects.

Format:

```
[SVP-DEBUG] Bug NNN: <one-line summary>

Affected units: <unit numbers and names>
Root cause: <P1-P13 or new pattern> — <brief description>
Classification: <single-unit | cross-unit | build_env>

Changes:
- <file>: <what changed and why>
- <file>: <what changed and why>

Regression test: tests/regressions/test_bugNN_descriptive_suffix.py
Spec/blueprint revised: <yes/no, with details if yes>
```

#### 12.18.12 Directory Authority Rules (NEW IN 2.2)

Every post-delivery operation must know which directory to read from and write to. The following rules are authoritative:

| Operation | Read Source | Write Target | Propagation |
|-----------|------------|--------------|-------------|
| Triage investigation | Workspace + delivered repo (via `assembly_map.json`) | None (read-only) | N/A |
| Repair agent (fix code) | Workspace | Workspace `src/unit_N/` | Stage 5 reassembly propagates to repo |
| Regression test authoring | Workspace | Workspace `tests/regressions/` | Stage 5 reassembly propagates to repo |
| Lessons learned update | Workspace | Workspace `references/` | Stage 5 reassembly propagates to repo |
| FIX IN PLACE | Both (human applies) | Both (human responsible) | Post-fix structural validation verifies sync |
| Oracle dry run (code analysis) | Delivered repo (actual executable code) | None (read-only) | N/A |
| Oracle green run (behavioral test) | Nested session (temp dir) | Nested session | Cleaned up on exit |
| Oracle fix planning | Delivered repo + `assembly_map.json` | None (read-only) | N/A |
| Oracle fix execution (`/svp:bug`) | Workspace (via `/svp:bug`) | Workspace (via `/svp:bug`) | Stage 5 reassembly propagates to repo |
| Oracle fix verification | Workspace + delivered repo | None (read-only) | N/A |

**Canonical source principle:** The workspace is always the canonical source of truth for code and artifacts. The delivered repo is a derived artifact produced by Stage 5 assembly. All writes target the workspace; all propagation to the repo goes through Stage 5 reassembly. The only exception is FIX IN PLACE, where the human is responsible for both locations.

#### 12.18.13 Debug Phase Transition Summary Table (NEW IN 2.2)

The following table maps every debug phase transition to its field mutations, file operations, and counter resets:

| Transition | `debug_session.phase` | Field Mutations | File Operations | Counter Resets |
|---|---|---|---|---|
| `/svp:bug` entry → triage | `null` → `"triage"` | Create `debug_session` object, set `authorized: false` | Create triage ledger | None |
| Gate 6.0 AUTHORIZE | `"triage"` | Set `authorized: true`, activate debug write rules | None | None |
| Triage complete → Gate 6.2 | `"triage"` → `"repair"` | Set `classification`, `affected_units`, `bug_number` | Write `triage_result.json` | None |
| Gate 6.2 FIX UNIT → Stage 3 re-entry | `"repair"` → `"stage3_reentry"` | Call `rollback_to_unit(N)` | Delete source/test files for units >= N | `fix_ladder_position: null`, `red_run_retries: 0` |
| Gate 6.2 FIX BLUEPRINT / FIX SPEC | `"repair"` → session terminated | `debug_session: null` (via abandon) | Delete `triage_result.json` | All counters reset |
| REPAIR_COMPLETE → reassembly | `"repair"` → `"reassembly"` | None | None | None |
| Reassembly complete → regression test | `"reassembly"` → `"regression_test"` | None | None | None |
| REGRESSION_TEST_COMPLETE → Gate 6.1 | `"regression_test"` | None | Write test file | None |
| Gate 6.1 TEST CORRECT → lessons learned | `"regression_test"` → `"lessons_learned"` | None | None | None |
| Lessons learned → commit | `"lessons_learned"` → `"commit"` | None | Update lessons learned doc | None |
| Gate 6.5 COMMIT APPROVED → complete | `"commit"` → session terminated | `debug_session: null`, record in `debug_history` | Rename ledger | All counters reset |
| RECLASSIFY → re-triage | `"repair"` → `"triage"` | Clear `classification` | Delete `triage_result.json` | `triage_refinement_count: 0`, `repair_retry_count: 0` |
| ABANDON → complete | Any → session terminated | `debug_session: null` | Rename ledger, delete `triage_result.json` | All counters reset |

#### 12.18.14 Stage 6 Orchestrator Oversight Protocol (NEW IN 2.2)

The orchestrator runs the following checkpoint-annotated checklist during the post-delivery debug loop. Items are checked at specific points in the workflow as annotated. This protocol operationalizes the two principles (Section 3.31) for Stage 6: the orchestrator detects issues; all fixing flows through agents via the normal debug loop cycle.

**After triage (3 items):**

1. `triage_result.json` exists at `.svp/triage_result.json`.
2. `triage_result.json` is valid JSON with `affected_units` (non-empty array of integers) and `classification` (one of `build_env`, `single_unit`, `cross_unit`).
3. Build/env fast-path guard: if classification is `build_env`, the triage agent's reported symptom describes an environmental issue (import failure, missing package, environment error), not a behavioral issue (wrong output, logic error, incorrect result). A behavioral issue misclassified as `build_env` bypasses Gate 6.2 and the regression test requirement (Section 12.18.3), eliminating two safeguards.

**After repair (2 items):**

4. For FIX UNIT path: modified files are within the scope of affected units listed in `triage_result.json`. No out-of-scope modifications to units not in `affected_units`.
5. For FIX IN PLACE path: all affected files are consistent between workspace and delivered repo, verified via `assembly_map.json` path correlation. The post-fix structural validation (Section 12.18.4) should have caught divergence; the orchestrator confirms it did.

**After regression test (2 items):**

6. Regression test file exists at the expected path (`tests/regressions/test_bugNN_descriptive_suffix.py`) with the correct bug number from the triage report.
7. Regression test exercises the specific failure condition identified during triage, not a generic scenario unrelated to the diagnosed root cause.

**After lessons learned / before reassembly (2 items):**

8. New entry appended to the lessons learned document with all required fields: bug number, how caught, test file reference, description, root cause pattern classification (P1-P13 or new pattern with definition), and prevention rule.
9. `assembly_map.json` is current: its modification timestamp is newer than or equal to the last Stage 5 reassembly. A stale assembly map causes incorrect path correlation during reassembly, potentially propagating fixes to wrong files or missing files entirely.

---

## 13. Human Commands (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

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
- `/svp:oracle` — spawns oracle agent (`--phase oracle`) **(NEW IN 2.2)**

**Prohibited scripts.** The following must never exist: `cmd_help.py`, `cmd_hint.py`, `cmd_ref.py`, `cmd_redo.py`, `cmd_bug.py`, `cmd_oracle.py` **(CHANGED IN 2.2)**. Group B commands must not be implemented as dedicated scripts.

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

**`/svp:redo`** (CHANGED IN 2.0) — Roll back to redo a previously completed step. The redo agent is invoked exclusively through the /svp:redo slash command. It does not appear in the main routing dispatch table. The redo sub-stages (redo_profile_delivery, redo_profile_blueprint) are reachable only when the redo agent is active via slash command. The redo agent traces the relevant term through the document hierarchy and classifies:

- **`REDO_CLASSIFIED: spec`** — spec says the wrong thing. Targeted revision, restart from Stage 2.
- **`REDO_CLASSIFIED: blueprint`** — blueprint translated incorrectly. Restart from Stage 2.
- **`REDO_CLASSIFIED: gate`** — documents correct, human approved wrong thing. Unit-level rollback: invalidate from affected unit forward, reprocess.
- **`REDO_CLASSIFIED: profile_delivery`** (CHANGED IN 2.0) — delivery-only profile change. Focused dialog, no pipeline restart. Takes effect at Stage 5. The repo collision avoidance mechanism (Section 12.1) applies: if the previous delivered repo directory exists, it is renamed to a timestamped backup before the new repo is created.
- **`REDO_CLASSIFIED: profile_blueprint`** (CHANGED IN 2.0) — blueprint-influencing profile change. Focused dialog, then restart from Stage 2.

**Redo-triggered profile revision (CHANGED IN 2.0).** When redo produces a `profile_delivery` or `profile_blueprint` classification, the setup agent runs in targeted revision mode. The pipeline writes a redo sub-stage (`"redo_profile_delivery"` or `"redo_profile_blueprint"`) and captures a `redo_triggered_from` snapshot of the current pipeline position. Mini-Gate 0.3r (same vocabulary: **PROFILE APPROVED**, **PROFILE REJECTED**). On completion: `profile_delivery` restores the snapshot; `profile_blueprint` restarts from Stage 2.

**Two-branch routing requirement for redo profile sub-stages (NEW IN 2.1 — routing invariant, Bug 43 fix).** Both `redo_profile_delivery` and `redo_profile_blueprint` sub-stages are governed by the two-branch routing invariant (Section 3.6). When `last_status.txt` contains `PROFILE_COMPLETE`, `route()` must emit a `human_gate` action for Gate 0.3r (`gate_0_3r_profile_revision`), not re-invoke the setup agent. If `route()` unconditionally re-invokes the setup agent without checking `last_status.txt`, the pipeline loops indefinitely after the profile revision is already written. A regression test must verify both branches for both redo profile sub-stages.

**Redo and delivery collision (NEW IN 2.1).** All redo classifications that cause the pipeline to re-enter Stage 5 — `spec` (restart from Stage 2, eventually reaches Stage 5), `blueprint` (restart from Stage 2), `profile_delivery` (takes effect at Stage 5), and `profile_blueprint` (restart from Stage 2) — are subject to the repo collision avoidance mechanism in Section 12.1. When a redo is triggered from post-delivery (stage 5 complete or the debug loop), the previous delivered repository directory will exist. The Stage 5 preparation script renames it to a timestamped backup before invoking the git repo agent, ensuring no directory collision. The `delivered_repo_path` in `pipeline_state.json` is always updated to the canonical `projectname-repo/` path after re-delivery. Note: the collision avoidance rename happens at Stage 5 entry (in the Stage 5 preparation script), not at redo classification time. The redo classifications listed above are subject to collision avoidance because they eventually cause re-entry into Stage 5, not because the rename is triggered immediately upon classification.

**`/svp:bug`** — Post-delivery bug report or abandon. See Section 12.18. During an active `/svp:oracle` session, `/svp:bug` is blocked for the human (the oracle can call it internally) **(CHANGED IN 2.2)**.

**`/svp:oracle`** **(NEW IN 2.2)** — Post-delivery pipeline acceptance testing. Available after Stage 5 completes. See Section 35.

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
- Default model configured via `pipeline.agent_models.help_agent` (see Section 22.1 precedence). Defaults to Sonnet-class.
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

**State-persistence-before-cycling invariant.** Session boundaries MUST NOT fire until all pending state mutations are persisted to `pipeline_state.json`. State persistence always precedes session cycling. A session boundary that fires before state is persisted causes the new session to read stale state, potentially re-executing completed work or skipping required steps.

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

- **ACTION** (required): `invoke_agent`, `run_command`, `human_gate`, `session_boundary`, `pipeline_complete`, `pipeline_held`, `break_glass` **(NEW IN 2.2)**. The `break_glass` action type is emitted by the routing script during E/F self-builds when known exhaustion conditions are met (Section 43.9). The orchestrator's `break_glass` handler has a narrow, enumerated set of permitted responses — it does not grant general authority to modify pipeline flow.
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

## 18. Agent Output Interface (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

**Agent dispatch mechanisms.** Agents are dispatched by two mechanisms: (1) agent_type for unit-development agents that produce artifacts during Stage 3 (valid agent_type values: test_agent, implementation_agent, coverage_review_agent, diagnostic_agent). These receive typed hint context and ladder position. (2) phase for support and orthogonal agents invoked via slash commands or special routing (valid phase values: help, hint, reference_indexing, redo, bug_triage, oracle, checklist_generation, regression_adaptation). The prepare_task_prompt function dispatches on agent_type; slash-command action cycles dispatch on phase via PHASE_TO_AGENT mapping.

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

**Test Agent:** `TEST_GENERATION_COMPLETE`, `REGRESSION_TEST_COMPLETE` (debug loop regression test mode — Section 12.18.4 Step 5).

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

**Checklist Generation Agent (NEW IN 2.2):** `CHECKLISTS_COMPLETE`.

**Regression Test Adaptation Agent (NEW IN 2.2):** `ADAPTATION_COMPLETE`, `ADAPTATION_NEEDS_REVIEW`.

**Oracle Agent (NEW IN 2.2):** `ORACLE_DRY_RUN_COMPLETE`, `ORACLE_ALL_CLEAR`, `ORACLE_FIX_APPLIED`, `ORACLE_HUMAN_ABORT`.

**Cross-agent (hint conflict):** `HINT_BLUEPRINT_CONFLICT: [details]`.

### 18.2 Dual-Format Output

Agents whose output determines routing (diagnostic, blueprint checker, redo) produce: `[PROSE]` section for the human, then `[STRUCTURED]` section with key-value data for routing.

### 18.3 Command Result Status Lines

Written after `run_command` actions:

- `TESTS_PASSED: N passed` — all tests passed.
- `TESTS_FAILED: N passed, M failed` — some tests failed.
- `TESTS_ERROR: [error summary]` — execution error preventing test collection. Collection errors are detected using the `collection_error_indicators` list from the language registry entry (Section 40.2); Python defaults include `ERROR collecting`, `ImportError`, `ModuleNotFoundError`, `SyntaxError`. Fixture setup errors (`NotImplementedError` from stubs) are `TESTS_FAILED`, not `TESTS_ERROR`.

**TESTS_ERROR dispatch rules (NEW IN 2.1 -- Bug 70 fix):** `TESTS_ERROR` must never return state unchanged. Dispatch behavior by sub_stage:
  - **Red run:** Increment `red_run_retries`. If under limit (default 3), set `sub_stage` to `test_generation` (regenerate tests). If at limit, autonomously treat tests as correct (TEST CORRECT) and enter the implementation fix ladder (NEW IN 2.2).
  - **Green run:** Engage the fix ladder, same as `TESTS_FAILED` -- the collection error indicates an implementation problem (import/syntax errors in generated code).
  - **Stage 4:** Increment `red_run_retries` and present `gate_4_1` (under limit) or `gate_4_2` (at limit), same as `TESTS_FAILED`.
- `COMMAND_SUCCEEDED` — non-test command exit code 0.
- `COMMAND_FAILED: [exit code]` — non-test command nonzero exit.

### 18.4 Gate Status Strings (CHANGED IN 2.0, CHANGED IN 2.2)

**(CHANGED IN 2.2)** The complete GATE_VOCABULARY contains 31 gate IDs: the 23 from SVP 2.1 (including gate_hint_conflict) plus 8 new gates: `gate_4_3_adaptation_review` (NEW IN 2.2), `gate_7_a_trajectory_review` (NEW IN 2.2), `gate_7_b_fix_plan_review` (NEW IN 2.2), `gate_pass_transition_post_pass1` (NEW IN 2.2), `gate_pass_transition_post_pass2` (NEW IN 2.2), `gate_3_completion_failure` (NEW IN 2.2), `gate_4_1a` (NEW IN 2.2), `gate_6_1a_divergence_warning` (NEW IN 2.2).

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
| 3.1 | gate_3_1_test_validation | TEST CORRECT, TEST WRONG | (autonomous — no human presentation, NEW IN 2.2) |
| 3.2 | gate_3_2_diagnostic_decision | FIX IMPLEMENTATION, FIX BLUEPRINT, FIX SPEC |
| 4.1 | gate_4_1_integration_failure | ASSEMBLY FIX, FIX BLUEPRINT, FIX SPEC |
| 4.2 | gate_4_2_assembly_exhausted | FIX BLUEPRINT, FIX SPEC |
| 4.3 | gate_4_3_adaptation_review | ACCEPT ADAPTATIONS, MODIFY TEST, REMOVE TEST **(NEW IN 2.2)** |
| 5.1 | gate_5_1_repo_test | TESTS PASSED, TESTS FAILED |
| 5.2 | gate_5_2_assembly_exhausted | RETRY ASSEMBLY, FIX BLUEPRINT, FIX SPEC |
| 5.3 | gate_5_3_unused_functions | FIX SPEC, OVERRIDE CONTINUE |
| 6.0 | gate_6_0_debug_permission | AUTHORIZE DEBUG, ABANDON DEBUG |
| 6.1 | gate_6_1_regression_test | TEST CORRECT, TEST WRONG |
| 6.2 | gate_6_2_debug_classification | FIX UNIT, FIX BLUEPRINT, FIX SPEC, FIX IN PLACE |
| 6.3 | gate_6_3_repair_exhausted | RETRY REPAIR, RECLASSIFY BUG, ABANDON DEBUG |
| 6.4 | gate_6_4_non_reproducible | RETRY TRIAGE, ABANDON DEBUG |
| 6.5 | gate_6_5_debug_commit | COMMIT APPROVED, COMMIT REJECTED |
| H.1 | gate_hint_conflict | BLUEPRINT CORRECT, HINT CORRECT |
| 7.A | gate_7_a_trajectory_review | APPROVE TRAJECTORY, MODIFY TRAJECTORY, ABORT **(NEW IN 2.2)** |
| 7.B | gate_7_b_fix_plan_review | APPROVE FIX, ABORT **(NEW IN 2.2)** |
| P1 | gate_pass_transition_post_pass1 | PROCEED TO PASS 2, FIX BUGS **(NEW IN 2.2)** |
| P2 | gate_pass_transition_post_pass2 | FIX BUGS, RUN ORACLE **(NEW IN 2.2)** |
| 3.CF | gate_3_completion_failure | INVESTIGATE, FORCE ADVANCE, RESTART STAGE 3 **(NEW IN 2.2)** |
| 4.1a | gate_4_1a | HUMAN FIX, ESCALATE **(NEW IN 2.2)** |
| 6.1a | gate_6_1a_divergence_warning | PROCEED, FIX DIVERGENCE, ABANDON DEBUG **(NEW IN 2.2)** |

**Invariant:** OPTIONS field must list exactly these strings. No other strings are valid. The human-typed gate status strings (with spaces) are distinct from system-generated command status lines (with underscores and payloads).

---

## 19. Universal Write Authorization (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

### 19.1 Layer 1 — Filesystem Permissions

Between sessions: workspace read-only (`chmod -R a-w`). On session start: write permissions restored. Delivered repository is unprotected.

### 19.2 Layer 2 — Hook-Based Write Authorization

`PreToolUse` hooks validate every write against current pipeline state.

**Two-tier path authorization:**
- **Infrastructure paths** (`.svp/`, `ledgers/`, `logs/`, `.svp/triage_result.json`, `.svp/build_log.jsonl`): always writable.

- **Pipeline state** (`pipeline_state.json`): writable ONLY by `update_state.py`. A PreToolUse hook blocks direct Write tool calls targeting this file. The hook script checks the file path; if it matches `pipeline_state.json`, the write is blocked with exit code 2 and a message directing to `update_state.py`. The Bash tool bypass (e.g., `python -c "..."`) is accepted as residual risk mitigated by the build log cross-validation (Section 22.6) and the Stage 3 completion integrity check (Section 10).

- **Builder scripts** (`scripts/*.py`, `scripts/toolchain_defaults/*`, `scripts/templates/*`): writable during Stages 0-2, read-only during Stages 3-5. A PreToolUse hook reads the current stage from `pipeline_state.json` and blocks Write tool calls to these paths when the stage is 3, 4, or 5. The hook message directs to the Hard Stop Protocol (Section 41): 'Builder scripts are read-only during Stage {N}. If the builder has a bug, follow the Hard Stop Protocol: stop, produce bug analysis, fix the builder via /svp:bug in the builder workspace, reload, and resume.'

Non-Python files in `scripts/` (e.g., shell scripts) remain writable at all stages. Only `.py` files and the `toolchain_defaults/` and `templates/` subdirectories are protected.

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
- Lessons learned document (`references/svp_2_1_lessons_learned.md`): writable during authorized debug session for regression cataloging **(NEW IN 2.1)**, OR during orchestrator break-glass mode (Section 43.9) for E/F self-builds **(NEW IN 2.2)**.

**Oracle session write rules (NEW IN 2.2).** During an active `/svp:oracle` session:
- `.svp/oracle_run_ledger.json`: always writable.
- Nested session workspace: writable by the oracle agent for driving the pipeline under test.
- The oracle does NOT write to the main workspace or delivered repository directly; fixes propagate through internal `/svp:bug` calls which have their own write authorization.

**Hook implementation order (NEW IN 2.2).** The write authorization hook must read the current pipeline stage BEFORE evaluating path-specific rules. The stage read occurs at the beginning of the hook script. The hook order is: (1) read stage, (2) check pipeline_state.json protection, (3) check builder script protection, (4) check remaining path rules.

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

### 20.4 Orchestrator Quality Assurance (CHANGED IN 2.2)

**(CHANGED IN 2.2)** The orchestrator's quality assurance responsibilities are defined per-stage and governed by the two principles (Section 3.31). In every stage, the orchestrator oversees with the full picture but never executes directly; all execution flows through subagents or deterministic scripts.

- **Stage 0:** Section 6.9 — Stage 0 Orchestrator Mentor Protocol. Gate-specific contextual guidance at Gates 0.1, 0.2, and 0.3. The orchestrator provides framing to help the human make informed decisions using its full-pipeline visibility; no detection checklist (nothing generated yet to detect errors in).
- **Stage 1:** Section 7.7 — Orchestrator Oversight Protocol. Decision tracking, spec draft verification, feature parity checking, contradiction detection, staleness/redundancy passes. The orchestrator constructs and runs verification checklists, delegating contradiction and staleness passes to dedicated subagents with fresh context.
- **Stage 2:** Section 8.5 — Stage 2 Orchestrator Oversight Protocol. 23-item detection checklist across structural completeness, namespace consistency, dead code, contract alignment, and lessons learned. The orchestrator detects issues; all fixing is delegated to the blueprint author agent.
- **Stage 3:** Section 10.15 — Stage 3 Orchestrator Oversight Protocol. Per-unit checklist (26 items at 8 checkpoints), cross-unit checklist (13 items every 5 units + stage boundary), builder integrity checks (2 items). The orchestrator detects issues; all fixing flows through agents via the normal pipeline cycle.
- **Stage 4:** Section 11.6 — Stage 4 Orchestrator Oversight Protocol. 6-item detection checklist across integration test completeness (4 items) and adaptation integrity (2 items). The orchestrator detects issues; all fixing is delegated to the appropriate agent.
- **Stage 5:** Section 12.17 — Stage 5 Orchestrator Oversight Protocol. 10-item detection checklist across cross-artifact consistency (7 items) and validation meta-oversight (3 items). The orchestrator detects issues; all fixing flows through the git repo agent via the bounded fix cycle.
- **Stage 6:** Section 12.18.13 — Stage 6 Orchestrator Oversight Protocol. 9-item checkpoint-annotated checklist at four debug loop checkpoints (after triage, after repair, after regression test, after lessons learned). The orchestrator detects issues; all fixing flows through agents via the normal debug loop cycle.

Stage 7 (oracle) is itself an orchestrator-level construct — it drives a nested SVP session, makes gate decisions autonomously, and calls `/svp:bug` internally. No separate oversight protocol is needed.

---

## 21. Agent Summary (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

| Agent | Stage | Interaction | Task Prompt Receives | Default Model | Terminal Status (Section 18.1) |
|---|---|---|---|---|---|
| Setup Agent | 0 | Ledger multi-turn | Environment state, ledger. Expanded: profile dialog, targeted revision mode (CHANGED IN 2.0) | `claude-sonnet-4-6` | `PROJECT_CONTEXT_COMPLETE`, `PROFILE_COMPLETE` |
| Stakeholder Dialog Agent | 1 (+ revision) | Ledger multi-turn | Ledger, reference summaries, project context (+ critique in revision) | `claude-opus-4-6` | `SPEC_DRAFT_COMPLETE`, `SPEC_REVISION_COMPLETE` |
| Stakeholder Spec Reviewer | 1 | Single-shot | Spec, project context, reference summaries (no ledger) | `claude-opus-4-6` | `REVIEW_COMPLETE` |
| Reference Indexing Agent | 1, 2+ | Single-shot | Full document or repo (via GitHub MCP) | `claude-sonnet-4-6` | `INDEXING_COMPLETE` |
| Blueprint Author Agent | 2 | Ledger multi-turn | Spec, checker feedback, references, ledger, profile (readme, vcs, delivery, quality sections) (CHANGED IN 2.0, CHANGED IN 2.1), lessons_learned (full, NEW IN 2.2 — Bug 84 fix) | `claude-opus-4-6` | `BLUEPRINT_DRAFT_COMPLETE`, `BLUEPRINT_REVISION_COMPLETE` |
| Blueprint Checker Agent | 2 | Single-shot | Spec (with notes) + blueprint + profile (full preference validation incl. quality) (CHANGED IN 2.0, CHANGED IN 2.1) | `claude-opus-4-6` | `ALIGNMENT_CONFIRMED`, `ALIGNMENT_FAILED: spec`, `ALIGNMENT_FAILED: blueprint` |
| Blueprint Reviewer Agent | 2 | Single-shot | Blueprint, spec, project context, references (no ledger), lessons_learned (full, NEW IN 2.2 — Bug 84 fix) | `claude-opus-4-6` | `REVIEW_COMPLETE` |
| Test Agent | 3 | Single-shot | Unit definition + upstream contracts. Receives `testing.readable_test_names` (CHANGED IN 2.0). Told quality tools will auto-format output (NEW IN 2.1) | `claude-opus-4-6` | `TEST_GENERATION_COMPLETE` |
| Implementation Agent | 3, 4 | Single-shot | Unit definition + upstream contracts (+ diagnostic + hint in ladder). Told quality tools will auto-format and type-check output (NEW IN 2.1) | `claude-opus-4-6` | `IMPLEMENTATION_COMPLETE` |
| Coverage Review Agent | 3 | Single-shot | Blueprint unit definition + passing tests | `claude-opus-4-6` | `COVERAGE_COMPLETE: no gaps`, `COVERAGE_COMPLETE: tests added` |
| Diagnostic Agent | 3, 4 | Single-shot | Spec + unit blueprint + failing tests + errors | `claude-opus-4-6` | `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, `DIAGNOSIS_COMPLETE: spec` |
| Integration Test Author | 4 | Single-shot | Spec + all contract signatures (reads source on demand) | `claude-opus-4-6` | `INTEGRATION_TESTS_COMPLETE` |
| Git Repo Agent | 5 | Single-shot | All verified artifacts + references + profile (full) (CHANGED IN 2.0) | `claude-sonnet-4-6` | `REPO_ASSEMBLY_COMPLETE` |
| Help Agent | Any | Ledger multi-turn | Project summary + spec + blueprint (+ gate flag) | `claude-sonnet-4-6` | `HELP_SESSION_COMPLETE: no hint`, `HELP_SESSION_COMPLETE: hint forwarded` |
| Hint Agent | Any | Single-shot / Ledger | Logs, documents, human concern. **Dual interaction pattern:** uses single-shot when invoked reactively during failure conditions (reads accumulated failures, produces one-shot analysis); uses ledger (`ledgers/hint_session.jsonl`) when invoked proactively during normal flow (human acts on intuition, may need multi-turn clarification). The ledger is cleared on dismissal. | `claude-opus-4-6` | `HINT_ANALYSIS_COMPLETE` |
| Redo Agent | 2, 3, 4 | Single-shot | State summary, error description, unit definition (reads on demand). New classifications: profile_delivery, profile_blueprint (CHANGED IN 2.0) | `claude-opus-4-6` | `REDO_CLASSIFIED: spec`, `REDO_CLASSIFIED: blueprint`, `REDO_CLASSIFIED: gate`, `REDO_CLASSIFIED: profile_delivery`, `REDO_CLASSIFIED: profile_blueprint` |
| Bug Triage Agent | Debug | Ledger multi-turn | Spec + blueprint + source + tests + ledger + real data access + `assembly_map.json` (CHANGED IN 2.2) | `claude-opus-4-6` | `TRIAGE_COMPLETE: single_unit`, `TRIAGE_COMPLETE: cross_unit`, `TRIAGE_COMPLETE: build_env`, `TRIAGE_NON_REPRODUCIBLE` |
| Repair Agent | Debug | Single-shot | Error diagnosis + environment state | `claude-sonnet-4-6` | `REPAIR_COMPLETE`, `REPAIR_FAILED`, `REPAIR_RECLASSIFY` |
| Checklist Generation Agent **(NEW IN 2.2)** | Post-Stage-1, pre-Stage-2 | Single-shot | Approved spec, lessons learned, regression test inventory | `claude-opus-4-6` | `CHECKLISTS_COMPLETE` |
| Regression Test Adaptation Agent **(NEW IN 2.2)** | Post-Stage-4, pre-Stage-5 | Single-shot | Failing test files, blueprint, assembly_map.json, module listing, previous spec summary | `claude-sonnet-4-6` | `ADAPTATION_COMPLETE`, `ADAPTATION_NEEDS_REVIEW` |
| Oracle Agent **(NEW IN 2.2)** | Post-delivery (Stage 7) | Ledger multi-turn (dry run) / Autonomous (green run) | Stakeholder spec, blueprint, run ledger, bug catalog, regression tests, test project artifacts, nested session state | `claude-opus-4-6` | `ORACLE_DRY_RUN_COMPLETE`, `ORACLE_ALL_CLEAR`, `ORACLE_FIX_APPLIED`, `ORACLE_HUMAN_ABORT` |

Agent models are configurable. The "Default Model" column shows the recommended model for each role; actual model selection follows the precedence rules in Section 22.1. Correctness-critical roles default to Opus; support roles default to Sonnet.

---

## 22. Configuration (CHANGED IN 2.0, CHANGED IN 2.1)

### 22.1 Configuration File

`svp_config.json` in the project workspace root. Contains:

- `iteration_limit`: maximum attempts for bounded retries. Default: 3. Does not govern fix ladder shapes.
- `models.<agent_key>`: per-agent model override. Any agent key from the Section 21 agent table is valid (e.g., `models.test_agent`, `models.diagnostic_agent`). Default for each key: the "Default Model" listed in the Section 21 table.
- `models.default`: fallback model for any agent not overridden above. Default: `"claude-opus-4-6"`.
- `context_budget_override`: optional manual override in tokens. Default: null.
- `context_budget_threshold`: percentage reserved for fixed context. Default: 65.
- `compaction_character_threshold`: minimum characters for self-contained tagged lines. Default: 200.
- `auto_save`: Default: true.
- `skip_permissions`: whether to pass `--dangerously-skip-permissions`. Default: true. Hook-based authorization remains active regardless.

Human can edit at any time. Changes take effect on next invocation.

**Model configuration precedence.** For agent model selection, `project_profile.json` `pipeline.agent_models` takes precedence over `svp_config.json` `models.*` entries. `svp_config.json` provides user-level defaults; the project profile provides project-specific settings configured during Stage 0. If neither specifies a model for a given agent, `models.default` from `svp_config.json` applies. Both files use full model identifiers (e.g., `"claude-opus-4-6"`, `"claude-sonnet-4-6"`), not shorthand.

### 22.2 Project Profile File (CHANGED IN 2.0, CHANGED IN 2.1)

Produced during Stage 0. Schema in Section 6.4. Immutable after Gate 0.3. Changes via `/svp:redo`.

### 22.3 Toolchain File (CHANGED IN 2.0, CHANGED IN 2.1)

Copied from plugin at project creation. Schema in Section 6.5. Permanently read-only.

### 22.4 Pipeline State File (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

**Preamble rule:** Every field in `pipeline_state.json` that accepts constrained string values MUST have its valid values enumerated as a closed set in this section. Fields with open-ended values (e.g., `delivered_repo_path`, timestamps) are exempt.

`pipeline_state.json`. Tracks: current stage (0-5 plus pre-Stage-3), sub-stage, blueprint alignment iteration count, fix ladder position, red run retries, `total_units`, verified units with timestamps, pass history, log references, `debug_session` (object or null with `authorized` flag), `debug_history`, `redo_triggered_from` (snapshot dict or null) (CHANGED IN 2.0), `delivered_repo_path` (string, set at Stage 5 completion) **(NEW IN 2.1)**, `oracle_session_active` (bool, default false) **(NEW IN 2.2)**, `oracle_test_project` (string or null) **(NEW IN 2.2)**, `oracle_phase` (string or null: `dry_run`, `gate_a`, `green_run`, `gate_b`, `exit`) **(NEW IN 2.2)**, `oracle_run_count` (int, default 0) **(NEW IN 2.2)**, `oracle_nested_session_path` (string or null, default null) **(NEW IN 2.2)**, `state_hash` (string or null) **(NEW IN 2.2)**, `pass` (integer or null: `1`, `2`, or `null`) **(NEW IN 2.2)**, `pass2_nested_session_path` (string or null, default null) **(NEW IN 2.2)**, `deferred_broken_units` (array of int, default `[]`) **(NEW IN 2.2)**.

**(NEW IN 2.2) Self-build pass fields:**

| Field | Type | Default | Valid Values | Description |
|-------|------|---------|-------------|-------------|
| `pass` | int or null | `null` | `1`, `2`, `null` | Current pass for E/F self-builds. `null` for non-self-builds (A-D). Set to `1` at pipeline start for E/F. Set to `2` when Pass 2 begins. Cleared after Pass 2 completion. |
| `pass2_nested_session_path` | string or null | `null` | valid path or `null` | Absolute path to the Pass 2 nested session workspace. Set when Pass 2 begins. Cleared after Pass 2 completes. |
| `deferred_broken_units` | array of int | `[]` | array of positive integers | Units marked `deferred_broken` during break-glass handling (Section 43.9). Blocks pass completion until resolved. |

The routing script checks `pass` before allowing `oracle_session_active` to be set: oracle sessions are rejected if `pass` is `1` or if `is_svp_build` is true and Pass 2 has not completed. The oracle requires a clean Pass 2 deliverable.

**`debug_session` schema (closed set):**

| Field | Type | Default | Valid Values |
|-------|------|---------|-------------|
| `authorized` | bool | `false` | `true`, `false` |
| `bug_number` | int or null | `null` | positive integer or `null` |
| `classification` | string or null | `null` | `"build_env"`, `"single_unit"`, `"cross_unit"`, `null` |
| `affected_units` | array | `[]` | array of positive integers |
| `phase` | string | `"triage"` | `"triage"`, `"repair"`, `"regression_test"`, `"lessons_learned"`, `"reassembly"`, `"stage3_reentry"`, `"commit"` |
| `repair_retry_count` | int | `0` | non-negative integer |
| `triage_refinement_count` | int | `0` | non-negative integer |
| `ledger_path` | string or null | `null` | valid file path or `null` |

When `debug_session` is `null`, no debug session is active.

**`oracle_phase` relationship to `sub_stage`:** `oracle_phase` is a distinct field from `sub_stage`. During oracle operation, `sub_stage` remains at its Stage 5 completion value (the pipeline stays at "Stage 5 complete"). `oracle_phase` tracks the oracle's internal progression. The routing script dispatches on `oracle_session_active` first — if true, it reads `oracle_phase` for oracle-specific routing; if false, it reads `stage`/`sub_stage` for normal pipeline routing.

**`state_hash`:** SHA-256 hex digest of the `pipeline_state.json` file as it existed on disk immediately before the current write. The `save_state` function reads the raw file bytes of the existing file, computes the hash, stores it in the new state object, then writes the new state to disk. The hash in the file is therefore always the hash of the *previous* file state, not the current one. This avoids self-referential hashing. Enables detection of state file corruption or out-of-order writes. **(Clarified in 2.2 — Bug S3-1, S3-5)**

Stage 0 sub-stages: `"hook_activation"`, `"project_context"`, `"project_profile"` (CHANGED IN 2.0).

Stage 1 sub-stages (NEW IN 2.1, CHANGED IN 2.2): `None` (stakeholder dialog in progress or not yet started), `"checklist_generation"` **(NEW IN 2.2)**. Stage 1 uses `sub_stage: None` during the spec authoring dialog. After the spec is approved at Gate 1.2, the pipeline transitions to `sub_stage: "checklist_generation"` (NEW IN 2.2) for the pre-blueprint checklist generation step (Section 7.8). When `CHECKLISTS_COMPLETE` is received, the pipeline advances to Stage 2. The checklist generation sub-stage is governed by the two-branch routing invariant: check for `CHECKLISTS_COMPLETE` before advancing to Stage 2. The routing script uses `last_status.txt` to distinguish "dialog in progress" from "draft complete, present gate" per the two-branch routing invariant (Section 3.6). During the spec authoring phase, the sub-stage is `None`; the two-branch check on `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` provides the routing branch. **Implementation note:** Because Stage 1's spec authoring phase has no named sub-stage, the two-branch check is keyed on `stage: "1"` alone. Any generic implementation of the two-branch invariant that dispatches solely by sub-stage name must handle Stage 1 as a special case (dispatch by stage number when `sub_stage` is `None` and the stage uses the two-branch pattern). **Reviewer status routing:** `route()` must also handle `REVIEW_COMPLETE` (from the spec reviewer) by routing to Gate 1.2 (`gate_1_2_spec_post_review`), not Gate 1.1 — distinguishing it from the dialog agent's `SPEC_DRAFT_COMPLETE` / `SPEC_REVISION_COMPLETE` which route to Gate 1.1. The same pattern applies in Stage 2 for the blueprint reviewer's `REVIEW_COMPLETE` routing to Gate 2.2 (see Section 8.2).

Stage 2 sub-stages (NEW IN 2.1 — Bug 23 fix): `"blueprint_dialog"`, `"alignment_check"`.

Pre-Stage-3 sub-stages: `None` (single deterministic step — no named sub-stages). Infrastructure setup runs as one `run_command` action.

Stage 3 sub-stages: `None` (initial entry — `route()` treats `None` identically to `"stub_generation"` by mapping both to the same code path), `"stub_generation"` (Bug 36 fix), `"test_generation"`, `"quality_gate_a"`, `"quality_gate_a_retry"`, `"red_run"`, `"implementation"`, `"quality_gate_b"`, `"quality_gate_b_retry"`, `"green_run"`, `"coverage_review"`, `"unit_completion"`. The routing script must emit a distinct action for each sub-stage (Bug 25 fix — NEW IN 2.1, updated for Bug 36).

Quality gate sub-stages (subset of Stage 3 sub-stages, NEW IN 2.1): `"quality_gate_a"`, `"quality_gate_b"`, `"quality_gate_a_retry"`, `"quality_gate_b_retry"`.

Stage 4 sub-stages (NEW IN 2.1, CHANGED IN 2.2): `None` (initial entry, invokes integration test author agent), `"regression_adaptation"` **(NEW IN 2.2)**. The two-branch routing invariant applies: when `last_status.txt` contains `INTEGRATION_TESTS_COMPLETE`, `route()` emits a `run_command` action for the integration test suite (not re-invocation of the agent). After the `run_command` completes, the routing script reads the test result status and performs three-state dispatch: (1) if tests passed (`TESTS_PASSED`), advance to `regression_adaptation` sub-stage (Section 11.5) **(CHANGED IN 2.2 -- previously advanced directly to Stage 5)**; (2) if tests failed (`TESTS_FAILED`), present the diagnostic gate (Section 11.4, Gate 4.1); (3) if the assembly fix ladder is exhausted (retries >= 3), present Gate 4.2. The `regression_adaptation` sub-stage is governed by the two-branch routing invariant: check for `ADAPTATION_COMPLETE` (advance to Stage 5) or `ADAPTATION_NEEDS_REVIEW` (present Gate 4.3).

Stage 5 sub-stages (NEW IN 2.1 — Bug 26 fix): `None` (initial entry, invokes git_repo_agent), `"repo_test"`, `"compliance_scan"`, `"repo_complete"`. Progression: `None` → git repo agent assembles repo (structural validation including Gate C runs within bounded fix cycle, Section 12.4) → on `REPO_ASSEMBLY_COMPLETE`, two-branch check presents Gate 5.1 → `"repo_test"` (human tests in delivered repo) → on `TESTS PASSED` → `"compliance_scan"` (deterministic `run_command`; on pass → `"repo_complete"`; on fail → re-enter bounded fix cycle, Section 12.4); on `TESTS FAILED` → re-enter bounded fix cycle (Section 12.4) with test failure output as context for the git repo agent. The routing script must have an explicit branch for each sub-stage; Bug 26 was caused by Stage 5 routing having only debug-session and pipeline-complete paths with no repo assembly sub-stage routing.

Redo-triggered profile revision sub-stages (CHANGED IN 2.0, CHANGED IN 2.1): `"redo_profile_delivery"`, `"redo_profile_blueprint"`. Both sub-stages are governed by the two-branch routing invariant (Section 3.6): when `last_status.txt` contains `PROFILE_COMPLETE`, `route()` must emit a `human_gate` action for Gate 0.3r (`gate_0_3r_profile_revision`), not re-invoke the setup agent (Bug 43 fix).

Pass 2 sub-stages (NEW IN 2.2): `"pass_transition"` (human decision gate after Pass 1's or Pass 2's Stage 5 — see Section 43.7), `"pass2_active"` (Pass 2 nested session is running — see Section 43.8). During `pass2_active`, the routing script delegates to the nested session; normal pipeline sub-stages (pre_stage_3 through Stage 5) run inside the nested session and are tracked by the nested session's own `pipeline_state.json`. The `pass_transition` sub-stage is used after both Pass 1 (offering Stage 6 / Pass 2) and Pass 2 (offering Stage 6 / Stage 7); the routing script distinguishes between them using the `pass` field.

Updated by deterministic scripts after every significant transition. The complete schema is a blueprint concern.

### 22.5 Resume Behavior (CHANGED IN 2.0)

On resume: routing script reads state file, main session presents context summary including project name, stage, sub-stage, verified units, pass history, pipeline toolchain, and profile summary.

### 22.6 Build Log (`.svp/build_log.jsonl`) (NEW IN 2.2)

An append-only JSONL file recording every pipeline action. Two deterministic sources write to the log — the orchestrator does NOT write to the build log.

**Writer 1: `routing.py`** appends an entry every time it emits an action block. This is deterministic — the routing script always runs and always writes.

**Writer 2: `update_state.py`** appends an entry every time it processes a state transition. This is deterministic — the POST command always runs update_state.py.

**Entry schema:**

```json
{
  "timestamp": "ISO-8601 UTC",
  "source": "routing" | "update_state",
  "event_type": "action_emitted" | "state_transition",
  "unit": null | integer,
  "sub_stage": "string",
  "stage": "string",
  "phase": "string or null",
  "action_type": "invoke_agent" | "run_command" | "human_gate" | "break_glass" | null,
  "status_line": "string or null",
  "state_hash": "SHA-256 of pipeline_state.json at write time"
}
```

**Cross-validation at stage boundaries:** For every routing entry, there must be a corresponding update_state entry (the orchestrator executed the action and the POST command ran). A routing entry without a matching update_state entry indicates the orchestrator received an action block but did not complete the cycle. An update_state entry without a corresponding routing entry indicates the orchestrator called update_state.py outside the routing cycle.

**state_hash chain:** Each entry includes the SHA-256 hash of `pipeline_state.json` at write time. If `pipeline_state.json` is modified between a routing entry and its corresponding update_state entry (indicating direct manipulation), the hashes will not form a consistent chain.

**Creation:** The build log is created during Pre-Stage-3 infrastructure setup (Section 9). It is append-only — never truncated or overwritten.

**The build log is a pipeline artifact included in the delivered repository.**

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

**(CHANGED IN 2.2)** The three new gates (4.3, 7.A, 7.B) do not trigger `version_document()`. Gate 4.3 modifies regression tests, not spec or blueprint. Gates 7.A and 7.B are oracle-internal decisions. Only gates whose response options include REVISE, FIX BLUEPRINT, or FIX SPEC trigger `version_document()`. This list is unchanged from SVP 2.1.

---

## 24. Failure Modes and Recovery (CHANGED IN 2.1)

> **Blueprint note:** All prevention rules from these bugs are encoded as structural invariants in Section 3 and as stage-specific requirements in Sections 6–12. This section is reference-only for post-delivery debugging — it is not needed for blueprint translation.

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
Warning at 80% capacity, compaction required at 90%. These thresholds are fixed constants in `ledger_manager.py`, not user-configurable.

### 24.10 Repository Assembly Failure
Bounded fix cycle. Up to `iteration_limit` attempts (Section 22.1, default: 3). Gate 5.2 on exhaustion.

### 24.11 Build Environment Guardrail Violation
All pipeline subprocess invocations targeting the project environment must use the language-specific run prefix from the toolchain file. For Python: `conda run -n {env_name}`. For R: the renv-activated R session. Environment name derived deterministically.

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

**Recovery:** P7 + P1 instance. Universal compliance requirement added to Section 3.6 mandating single-pass application. Explicit two-branch routing paragraphs added to Section 12.1 (Stage 5), Section 12.18.4 (debug loop agents), Section 13 (redo profile sub-stages), and Section 22.4 (redo profile sub-stage state definitions). This ensures every agent-to-gate transition in the spec has an explicit, locally visible two-branch routing requirement in its own section -- not only in the centralized Section 3.6 list.

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

### 24.51 Profile Dialog Skipped Due to Speculative Artifact Write (Post-delivery — Bug 86)

The setup agent speculatively writes `project_profile.json` during the context phase (Mode 1) because the preparation script does not inject a mode signal distinguishing context from profile. After Gate 0.2 approval, `last_status.txt` contains `CONTEXT APPROVED`, and the artifact-existence fallback in the profile routing guard treats this as sufficient to skip the profile dialog.

**Root cause:** Two gaps: (1) Unit 9 `prepare_task.py` assembled identical task prompt sections for both modes, with no mode signal (P1 — cross-unit contract drift between routing and preparation). (2) Unit 10 `routing.py` profile guard used artifact existence as a fallback, allowing carry-over statuses to satisfy the condition.

**Detection:** Regression test (`test_bug86_profile_dialog_skip.py`) verifies that `route()` invokes the setup agent (not the gate) when `last_status.txt` is `CONTEXT APPROVED` and `project_profile.json` exists. Additional tests verify mode signal injection into task prompts.

**Recovery:** Fix A: Added `--context` CLI argument to `prepare_task.py`; when set, injects a `current_mode` section into the setup agent's task prompt. Fix B: Profile routing guard now only accepts `PROFILE_COMPLETE` — artifact existence is no longer a fallback. New invariant: Mode isolation invariant (Section 3.6).

### 24.52 Stage 2 Agents Missing Lessons Learned Document (NEW IN 2.2 — Bug 84)

**(NEW IN 2.2 — Bug 84)** Stage 2 agents (blueprint author, blueprint reviewer) did not receive the lessons learned document. The blueprint checker received the pattern catalog (Part 2) but the other two Stage 2 agents had no access to historical failure patterns during their work. This meant the blueprint author could unknowingly recreate known failure patterns, and the blueprint reviewer could not cross-reference against historical bugs.

**Root cause:** `prepare_task.py` had lessons learned loading only for Stage 3 per-unit agents. Stage 2 agent sections were missing the loading calls.

**Fix:** All three Stage 2 agents (blueprint_author, blueprint_checker, blueprint_reviewer) now receive the full unfiltered lessons learned document. The checker continues to focus on pattern catalog validation; the author uses it for preventive contract design; the reviewer uses it for risk identification during cold review.

### 24.53 Hard Stop: Pipeline Builder Bug During Build (NEW IN 2.2)

When SVP N has a bug that prevents SVP N+1 from being built, no workaround is attempted. The hard stop protocol (Section 41) is followed: save artifacts, produce bug analysis, fix SVP N via `/svp:bug`, reload, restart from checkpoint.

### 24.54 Triage Result File Not Written (Bug 93, NEW IN 2.2)

The triage agent must write `.svp/triage_result.json` containing `{"affected_units": [N, M, ...], "classification": "<type>"}` after completing triage. Without this file, the Gate 6.2 FIX UNIT dispatch cannot determine which units to roll back.

**Root cause:** Triage agent contract did not require structured output file. The routing dispatch at Gate 6.2 assumed `triage_result.json` existed but the triage agent's terminal behavior only wrote to the conversation ledger.

**Fix:** Added file-write requirement to triage agent terminal behavior. A regression test verifies the file exists after triage completion.

### 24.55 Debug Reassembly Phase Infinite Loop (Stage 3 Build — Bug S3-18, NEW IN 2.2)

`_route_debug` for `phase == "reassembly"` unconditionally invokes `git_repo_agent` without checking `last_status`. After `REPO_ASSEMBLY_COMPLETE`, the debug phase stays at "reassembly" and the agent is re-invoked indefinitely.

**Root cause:** Missing two-branch check in the reassembly phase handler. The routing did not check whether the git_repo_agent had already completed before re-invoking it.

**Fix:** Added a check for `last_status == "REPO_ASSEMBLY_COMPLETE"` that advances the debug phase to `regression_test` before re-routing. A regression test (`test_bug_s3_18_21_routing_loops.py`) verifies the fix.

### 24.56 Diagnostic Escalation Infinite Loop (Stage 3 Build — Bug S3-19, NEW IN 2.2)

In `_route_stage_3`, when `fix_ladder_position == "diagnostic"`, the code unconditionally invokes `diagnostic_agent` without checking if `DIAGNOSIS_COMPLETE` has been written. After the agent completes, the same invocation is issued again indefinitely.

**Root cause:** Missing two-branch check in the diagnostic escalation handler. The routing checked for `IMPLEMENTATION_COMPLETE` at the top of the `implementation` sub-stage handler, but did not check for `DIAGNOSIS_COMPLETE` in the diagnostic branch.

**Fix:** Added a check for `last_status.startswith("DIAGNOSIS_COMPLETE")` that presents Gate 3.2 (`gate_3_2_diagnostic_decision`) for human decision. A regression test verifies the fix.

### 24.57 Debug Repair Phase Routing Loop (Stage 3 Build — Bug S3-20, NEW IN 2.2)

When `phase == "repair"` and `last_status == "REPAIR_COMPLETE"`, the routing directly invoked `git_repo_agent` for reassembly. After git_repo_agent completed with `REPO_ASSEMBLY_COMPLETE`, the repair handler did not recognize this status and fell through to re-invoke `repair_agent`, creating an infinite loop.

**Root cause:** The repair phase handler directly invoked `git_repo_agent` instead of transitioning to the `reassembly` phase. After the git agent completed, the debug phase was still `repair`, so the repair handler processed the `REPO_ASSEMBLY_COMPLETE` status as an unrecognized status and fell through to the default repair_agent invocation.

**Fix:** On `REPAIR_COMPLETE`, transition the debug phase to `reassembly` and re-route. The reassembly handler (fixed in S3-18) then properly handles the git_repo_agent invocation and subsequent transition. A regression test verifies the fix.

### 24.58 Missing dispatch_command_status Handlers for Debug Commands (Stage 3 Build — Bug S3-21, NEW IN 2.2)

Three command types emitted by `_route_debug` had no handler in `dispatch_command_status`: `lessons_learned`, `debug_commit`, and `stage3_reentry`. When the POST command called `update_state.py --command <type>`, it raised `ValueError: Unknown command_type`.

**Root cause:** Incomplete specification of the `dispatch_command_status` contract. The debug routing emitted `run_command` action blocks with POST commands referencing these command types, but the dispatch function only handled Stage 3/4/5 command types.

**Fix:** Added handlers for all three command types: `lessons_learned` (transitions debug phase to `commit`), `debug_commit` (completes the debug session via `complete_debug_session`), `stage3_reentry` (sets `sub_stage` to `stub_generation` for unit rebuild). A regression test verifies all three handlers.

### 24.59 Debug Re-entry Loop Prevention (Stage 6 Debug — Bug S3-23, NEW IN 2.2)

**Debug re-entry loop prevention (NEW IN 2.2 -- Bug S3-23).** `dispatch_command_status` for `stage3_reentry` must transition the debug session out of the stage3_reentry phase after COMMAND_SUCCEEDED, so normal Stage 3 routing takes over instead of `_route_debug` re-dispatching stage3_reentry. The fix sets the debug phase to `stage3_rebuild_active`, and `_route_debug` delegates that phase to `_route_stage_3` for the per-unit build loop.

**Root cause:** On COMMAND_SUCCEEDED, the handler set `sub_stage = "stub_generation"` but left `debug_session.phase = "stage3_reentry"`. Since `_route_debug` intercepts all routing when `debug_session` is active, it re-dispatched the stage3_reentry command on every cycle -- infinite loop.

**Fix:** After stage3_reentry COMMAND_SUCCEEDED, set `debug_session["phase"] = "stage3_rebuild_active"`. Added a `stage3_rebuild_active` handler in `_route_debug` that delegates to `_route_stage_3`.

### 24.60 Gate 6.3 Reclassification Counter (Stage 6 Debug — Bug S3-24, NEW IN 2.2)

**Gate 6.3 reclassification counter (NEW IN 2.2 -- Bug S3-24).** RECLASSIFY BUG at Gate 6.3 must increment `triage_refinement_count` before resetting to triage phase. Without the increment, the 3-reclassification limit is never enforced.

**Root cause:** The RECLASSIFY BUG handler read `triage_refinement_count` and checked the limit but never wrote back an incremented value. The counter stayed at 0 across all reclassifications.

**Fix:** After the limit check passes, increment `triage_refinement_count = triage_count + 1` in the debug session dict.

### 24.61 Gate 4.1a No-op Responses (Stage 4 Integration — Bug S3-25, NEW IN 2.2)

Both HUMAN FIX and ESCALATE responses at Gate 4.1a were no-ops (just copied state without modifying it). ESCALATE must advance to `gate_4_2` sub-stage. HUMAN FIX must reset `sub_stage` to `None` and `red_run_retries` to 0 for a fresh integration test attempt.

**Root cause:** Both branches contained `pass` statements with comments describing intended behavior that was never implemented.

**Fix:** ESCALATE sets `sub_stage = "gate_4_2"`. HUMAN FIX sets `sub_stage = None` and `red_run_retries = 0`.

### 24.62 Upstream Stub Filename Convention (Stage 3 Build — Bug S3-29, NEW IN 2.2)

**Upstream stub filename convention (NEW IN 2.2 -- Bug S3-29).** Upstream dependency stubs use `unit_N_stub{ext}` filenames (with unit number prefix) to avoid overwriting. Only the current unit's stub uses the bare `stub{ext}` filename.

**Root cause:** The S3-13 fix changed the filename from `f"unit_{dep_num}_stub{file_ext}"` to `f"stub{file_ext}"` in `generate_upstream_stubs`, but this was incorrect -- that fix should only have applied to the `main()` function (current unit stub). In `generate_upstream_stubs`, all upstream stubs wrote to the same `stub.py` file, with each overwriting the previous.

**Fix:** Restored `f"unit_{dep_num}_stub{file_ext}"` in `generate_upstream_stubs`. The `main()` function retains `f"stub{file_ext}"` for the current unit.

### 24.63 Quality Gate QUALITY_ERROR and QUALITY_AUTO_FIXED Unreachable (Stage 3 Build — Bug S3-36, NEW IN 2.2)

**Quality gate dead status variables (NEW IN 2.2 -- Bug S3-36).** In `_execute_gate_operations` (and the equivalent loops in `_run_plugin_markdown` and `_run_plugin_json`), `had_error` and `auto_fixed` are initialized to `False` and never set to `True`. This makes QUALITY_ERROR and QUALITY_AUTO_FIXED statuses unreachable -- every execution classifies as either QUALITY_CLEAN or QUALITY_RESIDUAL.

**Root cause:** The classification logic at the end of each function correctly checks `had_error` and `auto_fixed`, but the execution loop never modifies these variables. Subprocess failures are not caught (so `had_error` stays False), and file content changes from auto-fix tools are not detected (so `auto_fixed` stays False).

**Fix:** (1) Wrap `_run_command` in try/except; on exception set `had_error = True`. (2) Snapshot file content before and after each tool execution; if content changed, set `auto_fixed = True`.

### 24.64 Hooks JSON Malformed Structure (Stage 3 Build — Bug S3-37, NEW IN 2.2)

**Hooks JSON uses handler object instead of hooks array (NEW IN 2.2 -- Bug S3-37).** `HOOKS_JSON_SCHEMA` uses `{"matcher": "Write", "handler": {"type": "command", "command": "..."}}` instead of the spec-required `{"matcher": "Write", "hooks": [{"type": "command", "command": "..."}]}`. The Claude Code hooks configuration format requires a `"hooks"` array at the entry level, not a singular `"handler"` object.

**Root cause:** The implementation used the wrong key name (`handler` instead of `hooks`) and wrong structure (object instead of array) for hook entries.

**Fix:** Changed every entry in both PreToolUse and PostToolUse arrays from `"handler": {...}` to `"hooks": [{...}]`.

### 24.65 New Project Initial sub_stage (Stage 3 Build — Bug S3-38, NEW IN 2.2)

**New project initial sub_stage must be hook_activation (NEW IN 2.2 -- Bug S3-38).** `create_new_project` writes `"sub_stage": None` in the initial `pipeline_state.json`. The spec requires `"sub_stage": "hook_activation"` so that the routing script's first action block directs the orchestrator to activate hooks before proceeding to the setup dialog.

**Root cause:** The initial state dictionary used `None` for `sub_stage` instead of the spec-required `"hook_activation"` value.

**Fix:** Changed `"sub_stage": None` to `"sub_stage": "hook_activation"` in `create_new_project`.

### 24.66 Setup Agent Definition Wrong Terminal Status Names (Stage 3 Build — Bug S3-41, NEW IN 2.2)

**Terminal status name consistency (NEW IN 2.2 — Bug S3-41).** Agent definition terminal status names must be character-identical to the values handled by `dispatch_agent_status`. The setup agent uses `PROJECT_CONTEXT_COMPLETE`, `PROJECT_CONTEXT_REJECTED`, and `PROFILE_COMPLETE` — not any variant spellings.

**Root cause:** `SETUP_AGENT_DEFINITION` string used `PROFILE_DIALOG_COMPLETE` and `CONTEXT_DIALOG_COMPLETE` as terminal statuses. But `dispatch_agent_status` in Unit 14 expects `PROJECT_CONTEXT_COMPLETE`, `PROJECT_CONTEXT_REJECTED`, and `PROFILE_COMPLETE`. The mismatched names would cause the orchestrator to emit status lines that the routing script does not recognize.

**Fix:** Replaced `PROFILE_DIALOG_COMPLETE` with `PROFILE_COMPLETE`, `CONTEXT_DIALOG_COMPLETE` with `PROJECT_CONTEXT_COMPLETE`, and added `PROJECT_CONTEXT_REJECTED` as an additional terminal status in the `SETUP_AGENT_DEFINITION` string constant.

### 24.67 dispatch_agent_status Missing HINT_BLUEPRINT_CONFLICT for Stage 3 Agents (Stage 3 Build — Bug S3-42, NEW IN 2.2)

**Cross-agent HINT_BLUEPRINT_CONFLICT dispatch (NEW IN 2.2 — Bug S3-42).** Every agent that receives hint context (implementation_agent, test_agent, coverage_review_agent, diagnostic_agent) must have `HINT_BLUEPRINT_CONFLICT` handled in `dispatch_agent_status`. Missing handlers cause pipeline crashes when agents correctly detect hint-blueprint contradictions.

**Root cause:** `dispatch_agent_status` for `implementation_agent` only handled `IMPLEMENTATION_COMPLETE`. The same omission applied to `test_agent`, `coverage_review_agent`, and `diagnostic_agent`. When any of these agents received a hint that contradicted the blueprint and correctly emitted `HINT_BLUEPRINT_CONFLICT`, the dispatch function raised `ValueError` instead of routing to `gate_hint_conflict`.

**Fix:** Added `HINT_BLUEPRINT_CONFLICT` handling to all four hint-receiving agent types in `dispatch_agent_status`. The handler returns a copy of state with no changes — routing detects the conflict status and presents `gate_hint_conflict`.

### 24.68 Stage 5 pass_transition Sub-Stage Not Routed (Post-delivery — Bug S3-54, NEW IN 2.2)

**Stage 5 pass_transition routing (NEW IN 2.2 -- Bug S3-54).** `_route_stage_5()` sets `sub_stage` to `pass_transition` via `advance_sub_stage` when `repo_complete` is reached for pass 1 or 2. It then recursively calls `route()`. But `_route_stage_5()` has no explicit handler for `pass_transition`, so the recursive call falls through to the default `git_repo_agent` invocation. The handler for `pass_transition` exists only in `_route_stage_3()`. Fix: add a `pass_transition` handler in `_route_stage_5()` that presents `gate_pass_transition_post_pass1` (pass=1) or `gate_pass_transition_post_pass2` (pass=2), mirroring the Stage 3 handler.

**Root cause:** Sub-stage set in one routing function (`_route_stage_5`) but handler only in a different one (`_route_stage_3`), with the dispatcher selecting by stage. When stage is "5", `_route_stage_3` is never called.

**Pattern:** P2 (State Management). **Detection:** Regression test `test_bug_s3_54_pass_transition_routing.py`.

### 24.69 Plugin Manifest Fields Empty Due to Missing Profile Section (Post-delivery — Bug S3-53, NEW IN 2.2)

**Plugin profile section requirement (NEW IN 2.2 -- Bug S3-53).** `generate_plugin_json()` and `generate_marketplace_json()` in Unit 28 extract metadata from `profile.get("plugin", {})`. When the profile has no `"plugin"` section and no top-level `name`/`description`, all required manifest fields resolve to empty strings. Both Pass 1 and Pass 2 delivered repos had manifests with all-empty required fields. Fix: (1) `project_profile.json` must contain a `"plugin"` section with non-empty `name`, `description`, `version`, and `author` for plugin-producing archetypes, (2) generation functions must raise `ValueError` if any required field resolves to an empty string.

**Root cause:** The setup dialog contract doesn't require populating plugin metadata for self-build archetypes (`svp_architectural`). The profile had `license.author` but no `plugin.name`, `plugin.description`, or top-level equivalents.

**Pattern:** P1 (Incomplete Specification). **Detection:** Regression test `test_bug_s3_53_plugin_profile.py`.

### 24.70 Plugin Manifest Directories Missing From Delivered Repo (Post-delivery — Bug S3-51, NEW IN 2.2)

**Plugin manifest assembly (NEW IN 2.2 -- Bug S3-51).** The repository assembler (`assemble_python_project` in Unit 23) does not create `.claude-plugin/marketplace.json` at the repo root or `svp/.claude-plugin/plugin.json` in the plugin subdirectory. These are required by the Claude Code plugin discovery mechanism (Section 1.4). Fix: added `assemble_plugin_components()` to Unit 23 that calls `generate_marketplace_json()` and `generate_plugin_json()` from Unit 28 during assembly and writes the results to the correct paths.

**Root cause:** Assembly function creates source code structure but omits plugin manifest files. No code path existed to generate or place these files.

**Pattern:** P1 (Incomplete Implementation). **Detection:** Regression test `test_bug_s3_51_52_plugin_assembly.py`.

### 24.71 Plugin Component Directories Missing From Delivered Repo (Post-delivery — Bug S3-52, NEW IN 2.2)

**Plugin component extraction during assembly (NEW IN 2.2 -- Bug S3-52).** The repository assembler copies Python scripts to `svp/scripts/` but does not extract and write agent definitions (`svp/agents/*.md`), command definitions (`svp/commands/*.md`), hook configurations (`svp/hooks/`), or skill definitions (`svp/skills/`). These are Claude Code plugin component directories required for plugin functionality. The definition constants exist in workspace Units 17-26 but the assembler never reads them. Fix: `assemble_plugin_components()` in Unit 23 imports all definition constants from Units 17-26, creates the component directories, and writes 21 agent definitions, 11 command definitions, 5 hook files, and 1 skill definition.

**Root cause:** Assembly handled code files (Python scripts) but omitted non-code plugin component artifacts (markdown definitions, JSON configurations, bash scripts).

**Pattern:** P1 (Incomplete Implementation). **Detection:** Regression test `test_bug_s3_51_52_plugin_assembly.py`.

### 24.72 Pass 1 Artifacts Not Synchronized to Pass 2 Workspace (Post-delivery — Bug S3-55, NEW IN 2.2)

**Workspace artifact synchronization gap (NEW IN 2.2 -- Bug S3-55).** After Pass 2's Stage 5 completes, the Pass 2 workspace is missing artifacts accumulated during Pass 1's Stage 6: regression tests (S3-10 through S3-50), lessons-learned entries, inline spec amendments (Bugs S3-47/48/49/50), and .svp metadata (checklists, quality report, triage result). Section 43.8 clears `pass1_workspace_path` from pipeline state after Pass 2 completes, but no code path existed to copy the accumulated artifacts before clearing. Fix: added `sync_pass1_artifacts()` to Unit 16 that runs automatically at `pass_transition` when `pass == 2`, before the gate is presented. The function derives the Pass 1 workspace path from the Pass 2 workspace name (`{name}-pass2` convention), copies regression tests (union), merges lessons learned (append-unique), merges the spec (insert Pass 1-only lines using context matching), and copies .svp metadata files if absent. Idempotent via `.svp/pass1_sync_complete` marker file.

**Root cause:** Section 43.8 specifies that Pass 1 workspace references are cleared after Pass 2 completes but does not specify any artifact synchronization step. Pass 2's Stage 5 produces a clean build but omits artifacts created during Pass 1's Stage 6 debug loop.

**Pattern:** P1 (Incomplete Specification). **Detection:** Regression test `test_bug_s3_55_pass1_artifact_sync.py`.

### 24.73 Malformed Plugin Manifest Paths (Post-delivery — Bug S3-56, NEW IN 2.2)

**Plugin manifest path format (NEW IN 2.2 -- Bug S3-56).** Two path format issues prevent Claude Code plugin discovery: (1) `generate_marketplace_json()` hardcodes `source: "./"` instead of `source: "./{plugin_name}"` — the source field must point to the plugin subdirectory relative to the marketplace.json location. (2) `project_profile.json` plugin section uses bare paths (`"commands/"`) instead of relative paths (`"./commands/"`) — Claude Code requires `./` prefix on all custom component paths in plugin.json. Fix: (1) `generate_marketplace_json()` uses `f"./{name}"` for the source field. (2) Profile plugin paths updated to use `./` prefix.

**Root cause:** The source field was copied from a generic template that assumes the plugin is at the same level as marketplace.json. The path prefix requirement was not documented in the spec's Section 40.7 plugin manifest schema.

**Pattern:** P1 (Incomplete Specification). **Detection:** Regression test `test_bug_s3_56_manifest_paths.py`.

### 24.74 Missing pyproject.toml Entry Point and Build Backend (Post-delivery — Bug S3-57, NEW IN 2.2)

**pyproject.toml completeness (NEW IN 2.2 -- Bug S3-57).** The delivered repo's `pyproject.toml` is missing: (1) `[project.scripts]` section with `svp = "svp.scripts.svp_launcher:main"` entry point, (2) `[tool.setuptools.packages.find]` section, (3) `readme` field. Build backend is `setuptools.backends.legacy:build` instead of `setuptools.build_meta`. Without these, the `svp` CLI command is not registered and the package cannot be installed. Fix: reconstruct pyproject.toml to match SVP 2.1 structure with 2.2 metadata. The assembler's `_write_pyproject_toml` must include entry points from profile.

**Pattern:** P1 (Incomplete Implementation). **Detection:** Manual audit against SVP 2.1 reference.

### 24.75 Agent Definition Files Missing YAML Frontmatter (Post-delivery — Bug S3-58, NEW IN 2.2)

**Agent frontmatter requirement (NEW IN 2.2 -- Bug S3-58).** Claude Code requires YAML frontmatter on agent .md files with at least `name` and `description`. All 21 agent definition files in `svp/agents/` were generated without frontmatter — they started with bare `# Agent Name` headers. Fix: `assemble_plugin_components()` injects YAML frontmatter at assembly time using agent model data from the profile's `pipeline.agent_models` mapping.

**Pattern:** P1 (Incomplete Implementation). **Detection:** Regression test `test_bug_s3_57_60_plugin_readiness.py`.

### 24.76 hooks.json Uses handler Object Instead of hooks Array (Post-delivery — Bug S3-59, NEW IN 2.2)

**hooks.json schema (NEW IN 2.2 -- Bug S3-59).** Claude Code requires hook entries with `"hooks": [{"type": "command", ...}]` (array format). The `HOOKS_JSON_SCHEMA` in Unit 17 used `"handler": {"type": "command", ...}` (single object). This was already documented as Bug S3-37 in Section 24.64 but the fix was not applied to the generated hooks.json. Fix: updated `HOOKS_JSON_SCHEMA` to use `"hooks"` array format matching the Claude Code spec and SVP 2.1 reference.

**Pattern:** P3 (Regression from Prior Fix). **Detection:** Regression test `test_bug_s3_57_60_plugin_readiness.py`.

### 24.77 Missing svp/scripts/__init__.py (Post-delivery — Bug S3-60, NEW IN 2.2)

**Package init file (NEW IN 2.2 -- Bug S3-60).** The delivered repo is missing `svp/scripts/__init__.py`. This file is required for Python package imports — `svp.scripts.svp_launcher` (the CLI entry point) cannot resolve without it. SVP 2.1 has it. Fix: `assemble_plugin_components()` creates an empty `__init__.py` in `svp/scripts/` during assembly.

**Pattern:** P1 (Incomplete Implementation). **Detection:** Regression test `test_bug_s3_57_60_plugin_readiness.py`.

### 24.78 SVP 2.1 Carry-Forward Regression Tests Missing (Post-delivery — Bug S3-62, NEW IN 2.2)

**Carry-forward regression test gap (NEW IN 2.2 -- Bug S3-62).** Section 6.8 mandates 51 carry-forward regression tests from SVP 2.1 (test_bug2 through test_bug96, covering unified Bugs 6-73). Zero of these were present in the SVP 2.2 delivered repo or workspace. The tests were authored during the SVP 2.1 build and stored in the SVP 2.1 repo at `tests/regressions/`. Neither `svp restore` during Pass 2 creation nor the Stage 5 assembly process copied them forward. Without these tests, bugs that SVP 2.1 had already caught and fixed (e.g., Bug 48: launcher CLI contract) went undetected in SVP 2.2.

**Root cause:** The carry-forward mechanism relies on `create_new_project()` in the launcher copying regression tests from the plugin's `tests/regressions/` to the workspace. During Pass 2, the active plugin was the Pass 1 deliverable, which itself lacked the carry-forward tests (they were never assembled into the repo during Pass 1's Stage 5). The chain: SVP 2.1 tests → should be in SVP 2.2 plugin → should be copied to workspace. The first link was broken.

**Triage of 60 carried-forward tests against SVP 2.2:** 7 pass, 22 error (import failures due to API changes: DebugSession class removed, utility_agents.py consolidated, function renames), 33 fail (18 due to intentional API signature changes in route()/dispatch_*(), 15 require investigation for real bugs). Each test requires adaptation to SVP 2.2's API before it can serve as a regression guard.

**Pattern:** P1 (Incomplete Specification) — Section 6.8 specifies WHAT must carry forward but not HOW the carry-forward chain works across a two-pass self-build. **Detection:** Manual audit against SVP 2.1 reference.

### 24.79 Oracle State Transition Functions Never Implemented (Post-delivery — Bug S3-63, NEW IN 2.2)

**Oracle state transition functions missing (NEW IN 2.2 -- Bug S3-63).** `enter_oracle_session`, `complete_oracle_session`, `abandon_oracle_session` were specified in the blueprint (Unit 6, Tier 2 lines 451-455, Tier 3 lines 579-589) but never implemented. The implementation agent for Unit 6 produced 30 functions but missed these 3. The test agent wrote `test_bug_s3_15_oracle_session.py` which imports the missing functions — but since they don't exist, the test errors during collection and gets silently skipped, not flagged as a failure. Unit 14 (routing/dispatch), unable to import them, worked around the absence by directly setting oracle state fields (`oracle_session_active`, `oracle_phase`) in 8+ locations, violating the spec's design principle that state transitions go through Unit 6. The workaround caused three downstream bugs: (1) `oracle_run_count` never incremented, (2) no precondition validation for double-entry, (3) `oracle_test_project` and `oracle_nested_session_path` not cleaned up on session exit.

**Root cause:** The implementation agent for Unit 6 missed the oracle functions. The test agent correctly imported them but the collection error was treated as a skip, not a failure. The coverage review agent saw "8 skipped" but didn't flag it. Unit 14's implementation agent worked around the missing functions rather than reporting the gap. Pattern: P1 (Incomplete Implementation) compounded by P15 (Silent Test Skip).

**Fix:** Implemented all 3 functions in Unit 6. Replaced all 8 direct oracle field mutations in Unit 14 with proper function calls.

**Pattern:** P15 (NEW — Silent Test Skip Masks Missing Implementation). **Detection:** Regression test `test_bug_s3_15_oracle_session.py` (un-skipped).

**Oracle state transition invariant (NEW IN 2.2 — Bug S3-63).** All oracle state mutations (`oracle_session_active`, `oracle_phase`, `oracle_test_project`, `oracle_nested_session_path`, `oracle_run_count`) MUST go through Unit 6 transition functions: `enter_oracle_session`, `complete_oracle_session`, `abandon_oracle_session`. Direct field assignment in Unit 14 routing or dispatch is prohibited. The only acceptable direct `oracle_phase` assignment is for intra-session phase transitions (e.g., `dry_run→gate_a`, `gate_a→green_run`) that don't involve session start/stop.

### 24.80 Oracle Implementation Incomplete — Cross-Cutting Concern Not Wired (Post-delivery — Bug S3-65, NEW IN 2.2)

**Oracle cross-cutting integration gap (NEW IN 2.2 -- Bug S3-65).** The oracle (Stage 7) was ~40% implemented: state fields, session lifecycle, routing skeleton, agent definition, and command definition existed, but operational logic was missing. Test project selection, nested session bootstrap, run ledger management, phase-specific prompt assembly, modification bound enforcement, internal /svp:bug invocation, fix verification, and session cleanup were all absent. The oracle could not run end-to-end.

**Root cause:** The spec describes oracle behavior in Section 35 (~500 lines) as a narrative across multiple concerns. The blueprint decomposes it into per-unit contributions (Unit 5 state, Unit 6 lifecycle, Unit 7 ledger, Unit 13 prompts, Unit 14 routing, Unit 23 agent, Unit 25 command, Unit 29 launcher). No unit owns the end-to-end integration. Each implementation agent built its piece but the cross-unit wiring was nobody's responsibility. Compare with the debug loop (Stage 6) which works because Unit 14's blueprint contracts specify every routing transition, dispatch handler, and gate response explicitly.

**Fix:** Added test project selection via oracle_start command, run ledger functions (Unit 7), modification bound (oracle_modification_count field), phase-specific prompt assembly (Unit 13), nested session bootstrap, Gate 7.B→debug loop integration, fix verification cycle, and session cleanup with ledger recording. Added oracle integration contract to spec Section 35.

**Pattern:** P16 (NEW — Cross-Cutting Concern Without Integration Owner). Prevention: When a spec feature spans 3+ units, the blueprint must designate one unit as the integration owner with an explicit wiring checklist.

**Oracle integration contract (NEW IN 2.2 — Bug S3-65).** Unit 14's `_route_oracle` is the single owner of the oracle lifecycle. All operational steps (nested session creation, run ledger recording, test project resolution, internal /svp:bug invocation) are dispatched from `_route_oracle` through calls to other units. This mirrors the debug loop's integration pattern in `_route_debug`.

### 24.81 Entry Point Scripts Missing __name__ Guards and sys.path (Post-delivery — Bug S3-66, NEW IN 2.2)

**Script execution completeness (NEW IN 2.2 -- Bug S3-66).** Two entry point scripts (`routing.py`, `prepare_task.py`) lacked `if __name__ == "__main__": main()` guards. When the orchestrator invokes `python scripts/routing.py --project-root .`, the module loads but `main()` is never called, producing no output. Additionally, bare imports (e.g., `from pipeline_state import ...`) fail when the working directory is not `scripts/` because `scripts/` is not on `sys.path`. SVP 2.1 had `__name__` guards in all 4 entry point scripts; SVP 2.2 had them in only 2 of 4.

**Root cause:** The blueprint specifies `def main(argv=None) -> None: ...` function signatures but not the `if __name__` execution guard or sys.path setup. Implementation agents added the guard inconsistently.

**Pattern:** P17 (NEW — Entry Point Script Completeness). Prevention: Every script with a `main()` function must include `if __name__ == "__main__": main()` at the end. Every script invoked from a non-scripts working directory must add its own directory to `sys.path`.

### 24.82 Command Scripts Use Positional Args Instead of --project-root (Post-delivery — Bug S3-67, NEW IN 2.2)

**Command script CLI interface (NEW IN 2.2 -- Bug S3-67).** All 4 command scripts (`cmd_save.py`, `cmd_quit.py`, `cmd_status.py`, `cmd_clean.py`) used `sys.argv[1]` positional argument instead of argparse `--project-root`. When invoked as `python scripts/cmd_save.py --project-root .`, the literal string `--project-root` was used as the path, causing `FileNotFoundError`. SVP 2.1 uses argparse with `--project-root` for all scripts.

**Pattern:** P17 (Entry Point Script Completeness). **Detection:** Regression test in `test_plugin_completeness.py`.

### 24.83 Launcher Uses --prompt Flag Instead of Positional Argument (Post-delivery — Bug S3-68, NEW IN 2.2)

**Launcher CLI invocation (NEW IN 2.2 -- Bug S3-68).** `launch_session()` in Unit 29 passed the initial prompt via `--prompt "run the routing script"`, but the Claude Code CLI does not have a `--prompt` flag. The prompt must be passed as a **positional argument**: `claude [options] [prompt]`. Using `--prompt` causes `error: unknown option '--prompt'` and the session fails to launch. This bug originated in the spec (Section 6.1.5) and cascaded through the blueprint and implementation unchanged.

**Pattern:** P18 (NEW — External CLI Interface Verification). Prevention: When a spec references an external tool's CLI interface, verify the interface against the tool's actual `--help` output before codifying flags or argument formats. **Detection:** Regression test in `test_unit_29.py`.

### 24.84 Orchestration Skill Name Uses Hyphen Instead of Colon (Post-delivery — Bug S3-69, NEW IN 2.2)

**Skill naming convention (NEW IN 2.2 -- Bug S3-69).** The orchestration skill frontmatter used `name: "svp-orchestration"` (hyphen), inconsistent with the SVP command convention `/svp:command` (colon). All other SVP skills and commands use the colon separator (e.g., `/svp:bug`, `/svp:oracle`, `/svp:help`). The frontmatter `name` field controls how Claude Code resolves `/skill-name` invocations. Fix: rename to `name: "svp:orchestration"` in the skill definition, code generators, blueprint, and tests.

**Pattern:** P7 (Specification Omission). The spec did not explicitly mandate the colon convention for skill names, allowing the hyphen form to propagate. **Detection:** Regression test in `test_unit_26.py`.

### 24.85 Oracle Test Project Selection Lists docs/ Files Individually (Post-delivery — Bug S3-70, NEW IN 2.2)

**Oracle test project listing (NEW IN 2.2 -- Bug S3-70).** The routing script's `oracle_select_test_project` action used a vague reminder ("List projects from examples/ and docs/"), causing the orchestrator to list individual files in `docs/` (stakeholder_spec.md, blueprint_contracts.md, blueprint_prose.md) as separate F-mode test projects. Per Section 35.6, `docs/` is ONE test project ("SVP Pipeline") for F-mode machinery testing, not individual files. Fix: replace the vague reminder with prescriptive text specifying the exact expected format.

**Pattern:** P7 (Specification Omission). The spec defined the expected UI format (Section 35.6) but the routing script's reminder text did not encode it, leaving the orchestrator to guess. **Detection:** Manual testing of `/svp:oracle`.

### 24.86 Platform-Specific Code Prevents Cross-Platform Use (Post-delivery — Bug S3-71, NEW IN 2.2)

**Cross-platform portability (NEW IN 2.2 -- Bug S3-71).** Three platform-specific issues: (1) `_get_plugin_search_locations()` in Unit 29 hardcodes Unix-only paths (`/usr/local/share/`, `/usr/share/`) with no Windows equivalents (`%LOCALAPPDATA%`, `%PROGRAMDATA%`); (2) hook shell scripts invoke `python3` which may not exist on Windows (only `python`); (3) `sync_workspace.sh` used macOS-only `stat -f %m` (fixed with fallback chain, but script not in repo). Fix: add platform-conditional paths, use portable Python invocation in hooks, place sync script in repo with platform-aware path resolution.

**Pattern:** P19 (NEW — Cross-Platform Assumption). Prevention: When codifying filesystem paths or tool invocations, always consider Unix, macOS, and Windows variants. Use `sys.platform` guards or environment variables for system-level paths. **Detection:** Code audit.

### 24.87 restore_project Missing sync_workspace.sh and examples/ (Post-delivery — Bug S3-72, NEW IN 2.2)

**Restore workspace completeness (NEW IN 2.2 -- Bug S3-72).** `restore_project()` in Unit 29 did not copy `sync_workspace.sh` or the `examples/` directory to the restored workspace. Without `sync_workspace.sh`, the workspace-repo sync tool is unavailable after restore. Without `examples/`, the oracle cannot list test projects for E-mode selection. Fix: after copying references, also copy `sync_workspace.sh` and `examples/` from the repo or source workspace if present.

**Pattern:** P7 (Specification Omission). The spec did not enumerate all workspace artifacts that must be restored. **Detection:** Code audit of restore_project after adding sync_workspace.sh and examples/ to the repo.

### 24.88 Oracle F-mode Entry Treated as Discoverable Instead of Hardcoded (Post-delivery — Bug S3-73, NEW IN 2.2)

**Oracle F-mode hardcoded entry (NEW IN 2.2 -- Bug S3-73).** The routing script's `oracle_select_test_project` reminder referenced "docs/" as the source for F-mode projects, causing the orchestrator to scan for a `docs/` directory. When no `docs/` directory existed in the workspace, the orchestrator reported "No docs/ projects found" and omitted the F-mode option entirely. Per Section 35.6 (line 5304), the SVP Pipeline F-mode entry is **hardcoded** — it does not have an `oracle_manifest.json` and is always available regardless of directory structure. Fix: rewrite the reminder to state that item 1 is always present and hardcoded, and explicitly prohibit scanning `docs/` for F-mode projects.

**Pattern:** P7 (Specification Omission). The spec stated the entry is hardcoded (Section 35.6) but the routing script's reminder text contradicted this by referencing `docs/`. **Detection:** Manual testing of `/svp:oracle`.

### 24.89 oracle_select_test_project Action Type Missing From Orchestration Skill (Post-delivery — Bug S3-74, NEW IN 2.2)

**Orchestration skill action type coverage (NEW IN 2.2 -- Bug S3-74).** The orchestration skill (Unit 26) listed six action types in its "Action Type Handling" section (`invoke_agent`, `human_gate`, `run_command`, `advance_stage`, `break_glass`, `pipeline_complete`) but did not include `oracle_select_test_project`. When the routing script emitted this action type, the orchestrator had no handler and improvised — scanning directories instead of presenting the hardcoded list from the reminder text. Fix: add `oracle_select_test_project` to the orchestration skill's action type handling section with explicit instructions to present the list from the reminder text verbatim, including the hardcoded F-mode entry, without scanning any directories.

**Pattern:** P20 (NEW — Incomplete Action Type Dispatch). Prevention: Every `action_type` value that `_make_action_block()` can produce in `routing.py` must have a corresponding handler in the orchestration skill. **Detection:** Cross-reference routing script action types against orchestration skill handlers.

### 24.90 pipeline_held Action Type Missing From Orchestration Skill (Post-delivery — Bug S3-75, NEW IN 2.2)

**Orchestration skill pipeline_held handler (NEW IN 2.2 -- Bug S3-75).** The routing script emits `pipeline_held` in 6 locations (oracle session active, debug session active, etc.) but the orchestration skill had no handler for it. Same class of bug as S3-74 (P20). The orchestrator must present the reminder text to the human and wait — similar to `human_gate` but informational (no gate response required). Fix: add `pipeline_held` handler to the orchestration skill's Action Type Handling section.

**Pattern:** P20 (Incomplete Action Type Dispatch). **Detection:** Cross-reference audit of routing.py action types vs orchestration skill handlers.

### 24.91 Oracle Test Project List Delegated to Orchestrator Instead of Built Deterministically (Post-delivery — Bug S3-76, NEW IN 2.2)

**Deterministic test project list construction (NEW IN 2.2 -- Bug S3-76).** Bugs S3-70, S3-73, and S3-74 attempted to fix the missing F-mode entry by improving reminder text and adding action type handlers. All failed because the orchestrator is an LLM that ignores instructional text and scans directories instead. The fundamental error: delegating content construction to the orchestrator instead of building it deterministically in the routing script. Fix: `_route_oracle` builds the complete numbered test project list in Python — hardcoded F-mode entry ("SVP Pipeline") plus auto-discovered E-mode entries from `examples/*/oracle_manifest.json` — and embeds the formatted list in the `reminder` field. The orchestrator presents it verbatim.

**Pattern:** P21 (NEW — Deterministic Content Construction). Prevention: Never delegate content construction to the orchestrator. All content the human sees must be produced by deterministic scripts. The orchestrator is a relay, not a generator. **Detection:** Review all action blocks for cases where the reminder describes *how* to build content rather than *containing* the content.

---

## 25. Test Data

Test agents generate synthetic test data from stakeholder spec data characteristics. The test agent declares synthetic data assumptions, presented to the human at the test validation gate. Human-provided real data is not supported in this version.

---

## 26. Deterministic Components (CHANGED IN 2.1, CHANGED IN 2.2)

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

- **Regression test import adapter (NEW IN 2.2):** `scripts/adapt_regression_tests.py` reads `regression_test_import_map.json` and applies deterministic text replacements to regression test files. Called during Pre-Stage-3 (optional, Section 9.4) and Stage 5 assembly (mandatory). Also called as the first step of the regression adaptation sub-stage (Section 11.5). `adapt_regression_tests.py` supports per-language import replacements. For each test file, it determines the language from file extension (`.py` -> Python, `.R` -> R, `.stan` -> Stan) and applies language-specific regex patterns from `regression_test_import_map.json`. Unsupported file extensions cause a failure with an explicit error message -- the script does not silently skip adaptation.
- **Checklist generation (NEW IN 2.2):** Post-Stage-1 agent reads the approved spec and produces two structured checklists for Stage 2 agents. Single-shot invocation.
- **Oracle session management scripts (NEW IN 2.2):** state tracking for oracle sessions, run ledger management, nested session lifecycle.
- **Assembly map generator (NEW IN 2.2):** produces `.svp/assembly_map.json` during Stage 5 assembly, providing a bidirectional mapping between workspace paths and delivered repo paths. Generated from blueprint file tree annotations. Updated on every Stage 5 reassembly.

**(NEW IN 2.2)** Language-dispatch deterministic components:
- **Language registry** (`language_registry.py`): Built-in entries for Python, R, Stan. Import-time validation.
- **Language registry extensions** (`language_registry_extensions.json`): Project-scoped dynamic entries. Generated by setup agent Area 0.
- **R toolchain file** (`scripts/toolchain_defaults/r_renv_testthat.json`): R build-time quality gate composition.
- **Delivery quality templates** (`scripts/delivery_quality_templates/`): Per-language quality config templates for Stage 5 assembly.
- **Signature parser dispatch** (`SIGNATURE_PARSERS`): Per-language function dispatch in Unit 9.
- **Stub generator dispatch** (`STUB_GENERATORS`): Per-language function dispatch in Unit 10.
- **Test output parser dispatch** (`TEST_OUTPUT_PARSERS`): Per-language function dispatch in Unit 14.
- **Quality runner dispatch** (`QUALITY_RUNNERS`): Per-language function dispatch in Unit 15.
- **Project assembler dispatch** (`PROJECT_ASSEMBLERS`): Per-language function dispatch in Unit 23.
- **Compliance scanner dispatch** (`COMPLIANCE_SCANNERS`): Per-language function dispatch in Unit 28.
- **Dispatch exhaustiveness validator** (`validate_dispatch_exhaustiveness()`): Verifies all registry entries have matching dispatch table entries. Runs during structural validation.
- **Plugin manifest validator (CHANGED IN 2.2):** Validates `plugin.json` against the full schema per Section 40.7.1 (all 12 fields including `mcpServers`, `lspServers`, `hooks`, `skills`, `agents`, `tools`) and `marketplace.json` against Section 40.7.8 schema during Gate C for `claude_code_plugin` archetype.
- **Agent definition format checker (CHANGED IN 2.2):** Validates markdown agent definition files for YAML frontmatter per Section 40.7.6 schema (fields: `name`, `description`, `model`, `effort`, `maxTurns`, `disallowedTools`, `skills`, `memory`, `background`, `isolation`).
- **Skill definition format checker (NEW IN 2.2):** Validates `SKILL.md` files for YAML frontmatter per Section 40.7.4 schema (fields: `name`, `description`, `argument-hint`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `disable-model-invocation`, `user-invocable`). Validates string substitution syntax.
- **Hook definition validator (NEW IN 2.2):** Validates hook definitions (in `hooks.json` or inline in `plugin.json`) against Section 40.7.5 schema -- valid event names from the 12-event set, valid hook types (`command`, `http`, `prompt`, `agent`), proper matcher regex syntax for tool events.
- **Hook syntax validator (CHANGED IN 2.2):** Runs `bash -n` on `.sh` hook scripts and ruff on `.py` hook scripts during Gate C.
- **MCP config validator (NEW IN 2.2):** Validates `.mcp.json` and inline `mcpServers` per Section 40.7.2 -- transport-specific required fields (stdio requires `command`, http requires `url`), valid transport types, env var `${...}` syntax, no absolute paths.
- **Cross-reference integrity checker (NEW IN 2.2):** Validates that skill references in agent definitions resolve to existing skills in `skills/`, MCP server references in hooks resolve to declared servers, and command references in manifest resolve to existing command files.

- **Build log writers (NEW IN 2.2):** `routing.py` and `update_state.py` each append structured JSONL entries to `.svp/build_log.jsonl` at every routing cycle and state transition respectively.

All have pytest test suites. The preparation script has elevated coverage.

---

## 27. Future Directions (CHANGED IN 2.1, CHANGED IN 2.2)

SVP 2.2 is the current release. The self-hosting build chain is:

**SVP 1.2.1 -> SVP 2.0 -> SVP 2.1 -> SVP 2.2**

SVP 2.1 builds SVP 2.2. After SVP 2.2 is delivered, the chain continues with SVP 2.2 as the active builder for the next release.

### 27.1 Language-Directed Variants

Future development takes the form of language-targeted products, each built by SVP 2.2:

```
SVP 2.2  ──builds──>  SVP-R       (targets R projects: renv, testthat, roxygen2)
SVP 2.2  ──builds──>  SVP-elisp   (targets Emacs Lisp: Cask, ERT)
SVP 2.2  ──builds──>  SVP-bash    (targets bash: shunit2 or bats)
```

Each variant is a complete standalone Claude Code plugin. It shares SVP's pipeline architecture (stages, gates, fix ladders, state machine, orchestration protocol) but implements language-specific tooling: parsers, stub generators, test output readers, environment management, and agent prompts. Each variant is a Python project containing Python code that manipulates artifacts in the target language. SVP 2.2 builds it without any language extensions.

Each variant can evolve independently. SVP-R may gain R-specific features that SVP-elisp doesn't need, and vice versa.

### 27.2 The Build Chain (CHANGED IN 2.2)

```
SVP 1.2.1  ──builds──>  SVP 2.0
SVP 2.0    ──builds──>  SVP 2.1
SVP 2.1    ──builds──>  SVP 2.2
SVP 2.2    ──builds──>  SVP 2.3  (per Section 43)
SVP 2.2    ──builds──>  SVP-R, SVP-elisp, SVP-bash  (independently)
```

No manual bootstrap at any step. No version of SVP ever needs to build a non-Python project. Every self-build follows the two-pass bootstrap protocol (Section 43).

### 27.3 CLI as Foundational Interface

The CLI is not an interim choice. The terminal model is intrinsic: matches the orchestration architecture, preserves full conversation history, ensures all interactions are explicit, auditable, and reproducible.

### 27.4 Beyond the Current Architecture

Long-term directions that would require a new major version (not SVP 2.x) are documented separately in the SVP Product Roadmap (`svp_product_roadmap.md`). These include capabilities that would change the pipeline's fundamental architecture, such as multi-model test authoring. They are not planned for any current development timeline.

---

## 28. Implementation Note (CHANGED IN 2.2)

This specification defines SVP 2.2, built using SVP 2.1. Blueprint must fit within context budget. Primary risk: blueprint size from oracle agent orchestration logic and nested session management. Blueprint author should fold oracle functionality into new units that follow the established patterns for post-delivery tools (modeled on `/svp:bug`).

Bundled example (Game of Life): carried forward unchanged. Prompt caching: out of scope.

---

# PART III — ARCHITECTURAL STRATEGY (Sections 29–34)

---

## 29. The Two-File Architecture (CHANGED IN 2.0)

1. **`project_profile.json`** — Human-facing. Delivery preferences. Agents read via task prompts. Immutable after Gate 0.3.
2. **`toolchain.json`** — Pipeline-facing. Build commands. Scripts read at runtime. Never modified.

The profile says how the delivered project should look. The toolchain file says how SVP builds and tests. They serve different consumers and change at different rates.

---

## 30. Blueprint Author Guidance (CHANGED IN 2.0, CHANGED IN 2.1, CHANGED IN 2.2)

**(CHANGED IN 2.2)** SVP 2.2 restructures units from SVP 2.1's 24. The reference decomposition (Section 42) illustrates one valid organization; the blueprint author determines the actual unit count and boundaries. The guidance below uses SVP 2.2 reference unit numbers.

**Agent loading matrix (from Section 3.16).** For blueprint construction, the authoritative context-loading rules:

| Agent | Blueprint Files Loaded |
|-------|----------------------|
| Blueprint author | Both (`blueprint_prose.md` + `blueprint_contracts.md`) |
| Blueprint checker | Both |
| Blueprint reviewer | Both |
| Test agent | `blueprint_contracts.md` only (`include_tier1=False`) |
| Implementation agent | `blueprint_contracts.md` only (`include_tier1=False`) |
| Diagnostic agent | Both (`include_tier1=True`) |
| Help agent | `blueprint_prose.md` only |
| Hint agent | Both |
| Integration test author | `blueprint_contracts.md` only |
| Git repo agent | `blueprint_contracts.md` only |
| Bug triage agent | Both |
| Repair agent | Both |

The loader functions are in Unit 13: `load_blueprint()`, `load_blueprint_contracts_only()`, `load_blueprint_prose_only()`. Unit context assembly via `build_unit_context` (Unit 8) respects the `include_tier1` parameter.

| SVP 2.1 Unit | SVP 2.2 Unit(s) | Responsibility |
|-------------|----------------|----------------|
| Unit 1 | Units 1, 2, 3, 4 | Config, Language Registry, Profile, Toolchain |
| Unit 2 | Unit 5 | Pipeline State |
| Unit 3 | Unit 6 | State Transitions |
| Unit 4 | Unit 7 | Ledger Management |
| Unit 5 | Unit 8 | Blueprint Extractor |
| Unit 6 | Units 9, 10 | Signature Parser, Stub Generator |
| Unit 7 | Unit 11 | Infrastructure Setup |
| Unit 8 | Unit 12 | Hint Prompt Assembler |
| Unit 9 | Unit 13 | Task Preparation |
| Unit 10 | Units 14, 15 | Routing + Test Execution, Quality Gates |
| Unit 11 | Unit 16 | Command Logic |
| Unit 12 | Unit 17 | Hook Enforcement |
| Unit 13 | Unit 18 | Setup Agent |
| Unit 14 | Unit 19 | Blueprint Checker |
| Unit 15 | Unit 20 | Construction Agents |
| Unit 16 | Unit 21 | Diagnostic/Redo Agents |
| Unit 17 | Unit 22 | Support Agents |
| Unit 18 | Unit 23 | Utility Agents + Assembly |
| Units 19-20 | Unit 24 | Debug Loop Agents |
| Unit 21 | Unit 25 | Slash Commands |
| Unit 22 | Unit 26 | Orchestration Skill |
| Unit 23 | Unit 27 | Templates |
| Unit 24 | Unit 28 | Plugin Manifest + Validation |
| (new) | Unit 29 | Launcher |

**Unit 1 (Core Configuration):** Define canonical pipeline artifact filenames (e.g., `stakeholder_spec.md`, `blueprint_prose.md`, `blueprint_contracts.md`) as shared constants; all producers and consumers must reference these constants (Bug 22 fix) **(NEW IN 2.1)**. `svp_config.json` schema and validation. Blueprint discovery paths.

**Unit 2 (Language Registry -- NEW IN 2.2):** `LANGUAGE_REGISTRY` with built-in entries for Python, R, and Stan (component). Validation guardrails. `get_language_config()`. `RunResult`/`QualityResult` named tuple types. Dynamic registry extension loading from `language_registry_extensions.json`.

**Unit 3 (Profile Schema -- restructured in 2.2):** Language-keyed `DEFAULT_PROFILE`. Add quality section to profile schema. `DEFAULT_PROFILE` must use the exact canonical section and field names from the profile schema (Section 6.4): top-level sections `delivery` (not `packaging`), `license` (not `licensing`); field `readme.audience` (not `readme.target_audience`); field `delivery.environment_recommendation` (not `delivery.environment`). A regression test must verify that every key path in `DEFAULT_PROFILE` matches the canonical schema **(NEW IN 2.1)**. `load_profile` with SVP 2.1 migration (auto-wraps flat delivery/quality under `"python"` key). `validate_profile` with per-language validation. Language-keyed accessors.

**Unit 4 (Toolchain Reader -- restructured in 2.2):** `load_toolchain` with optional language parameter. Three-layer separation (Section 3.25). Add quality section to toolchain schema + validation **(CHANGED IN 2.1)**. Three schemas, three loaders, three validators **(CHANGED IN 2.1)**.

**Unit 5 (Pipeline State):** Add quality gate sub-stages to state schema **(NEW IN 2.1)**. Add Stage 2 sub-stages (`blueprint_dialog`, `alignment_check`) to state schema (Bug 23 fix) **(NEW IN 2.1)**. All SVP 2.1 fields plus `primary_language`, `component_languages`, and `secondary_language` (present when `archetype` is `"mixed"`, absent otherwise).

**Unit 6 (State Transitions):** Add quality gate state transitions (enter gate, retry, fail-to-ladder) **(NEW IN 2.1)**. Add Stage 2 state transitions: Gate 2.1 APPROVE must transition to `alignment_check` sub-stage (not directly to Pre-Stage-3); `ALIGNMENT_CONFIRMED` presents Gate 2.2 (human decides); Gate 2.2 APPROVE advances to Pre-Stage-3; `ALIGNMENT_FAILED: blueprint` resets `sub_stage` to `"blueprint_dialog"` and increments `alignment_iterations`; `ALIGNMENT_FAILED: spec` initiates targeted spec revision; neither outcome advances to Pre-Stage-3 (Section 8.2 invariant, Bug 23 fix) **(NEW IN 2.1)**. `dispatch_agent_status` for `reference_indexing` must advance the pipeline from `pre_stage_3` to stage 3 -- a bare `return state` is not valid for a main-pipeline agent (Bug 42 fix, exhaustive dispatch_agent_status invariant, Section 3.6) **(Post-delivery fix)**. `dispatch_agent_status` for `test_agent` must handle `sub_stage=None` equivalently to `sub_stage="test_generation"` (Bug 44 fix). `dispatch_command_status` for `test_execution` must advance from `red_run` to `implementation` on `TESTS_FAILED` and from `green_run` to `coverage_review` on `TESTS_PASSED` -- no-op handlers are invalid (Bug 45 fix, exhaustive dispatch_command_status invariant, Section 3.6). `dispatch_agent_status` for `coverage_review` must advance to `unit_completion` on `COVERAGE_COMPLETE` (Bug 46 fix) **(Post-delivery fix)**.

**Unit 8 (Blueprint Extractor -- CHANGED IN 2.2):** `extract_unit`, `extract_upstream_contracts`, and `build_unit_context` must accept a `include_tier1: bool` parameter (default `True`). When `False`, Tier 1 description content is excluded from the returned context. `parse_blueprint` must accept an optional `contracts_path` parameter to parse `blueprint_contracts.md` separately from `blueprint_prose.md`. The `UnitDefinition` dataclass gains `languages` field -- it continues to carry all tiers; the parameter controls what is included in assembled context strings. `detect_code_block_language()` NEW -- detects code fence language tags from both blueprint files **(NEW IN 2.2)**. Code fence stripping: `extract_unit` and `extract_upstream_contracts` must strip markdown code fence markers (` ```language ` / ` ``` `) from Tier 2 blocks before returning content. Signature parsers receive raw code, not markdown.

**Unit 9 (Signature Parser Dispatch -- NEW split in 2.2):** `SIGNATURE_PARSERS` dispatch table. Python parser wraps `ast.parse()`. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `main()`'s argparse arguments: `--blueprint`, `--unit`, `--output-dir`, `--upstream`.

**Unit 10 (Stub Generator Dispatch -- NEW split in 2.2):** `STUB_GENERATORS` dispatch table. `generate_stub_source` must prepend the language-appropriate stub sentinel (from the language registry) as the first non-import statement in every generated stub. This sentinel is required -- its absence from stub output is a Unit 10 contract violation.

**Unit 11 (Infrastructure Setup):** Install `quality.packages` during infrastructure setup **(NEW IN 2.1)**. Replace hardcoded commands with toolchain reader calls **(CHANGED IN 2.0)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `main()`'s argparse arguments: `--project-root`. Language-dispatch for environment creation, quality tool installation, import validation **(NEW IN 2.2)**.

**Unit 13 (Task Preparation -- CHANGED IN 2.2):** Include quality report in agent re-pass task prompts **(NEW IN 2.1)**. Extract profile sections for agent task prompts **(CHANGED IN 2.0)**. Reference shared filename constants for all artifact paths -- no hardcoded filenames (Bug 22 fix) **(NEW IN 2.1)**. Task prompt assembly for test agent and implementation agent invocations must pass `include_tier1=False` to `build_unit_context`. Task prompt assembly for diagnostic agent, help agent, and blueprint checker invocations must pass `include_tier1=True`. Add lessons learned loading for blueprint_author, blueprint_checker, blueprint_reviewer task prompt assembly (full unfiltered document -- Bug 84 fix, NEW IN 2.2). Add lessons learned filtering for test agent and implementation agent task prompt assembly (per-unit filtered). Filtering logic: match on unit number and/or pattern classification. Output appended under a dedicated heading. No LLM involvement in filtering -- pure text matching and extraction. `ALL_GATE_IDS` must include every gate ID in the pipeline -- **(CHANGED IN 2.2)** the complete set of 31 gate IDs enumerated in Section 18.4: `gate_0_1_hook_activation`, `gate_0_2_context_approval`, `gate_0_3_profile_approval`, `gate_0_3r_profile_revision`, `gate_1_1_spec_draft`, `gate_1_2_spec_post_review`, `gate_2_1_blueprint_approval`, `gate_2_2_blueprint_post_review`, `gate_2_3_alignment_exhausted`, `gate_3_1_test_validation`, `gate_3_2_diagnostic_decision`, `gate_3_completion_failure`, `gate_4_1_integration_failure`, `gate_4_1a`, `gate_4_2_assembly_exhausted`, `gate_4_3_adaptation_review`, `gate_5_1_repo_test`, `gate_5_2_assembly_exhausted`, `gate_5_3_unused_functions`, `gate_6_0_debug_permission`, `gate_6_1_regression_test`, `gate_6_1a_divergence_warning`, `gate_6_2_debug_classification`, `gate_6_3_repair_exhausted`, `gate_6_4_non_reproducible`, `gate_6_5_debug_commit`, `gate_hint_conflict`, `gate_7_a_trajectory_review`, `gate_7_b_fix_plan_review`, `gate_pass_transition_post_pass1`, `gate_pass_transition_post_pass2` (Bug 41 fix for Stage 1 gates, Bug 43 fix for remaining gaps). The gate ID consistency invariant (Section 3.6) requires that `ALL_GATE_IDS` is synchronized with `GATE_RESPONSES`/`GATE_VOCABULARY` in Unit 14 -- every gate ID must appear in both, with no orphans in either direction **(Post-delivery fix, expanded by Bug 43)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `main()`'s argparse arguments: `--project-root`, `--agent`, `--gate`, `--unit`, `--output`, `--ladder`, `--revision-mode`, `--quality-report`. **Selective blueprint loading (Bugs 60-62 fix):** Unit 13 must export `load_blueprint_contracts_only()` and `load_blueprint_prose_only()` as Tier 2 functions. Per the Section 3.16 agent loading matrix: `integration_test_author` and `git_repo_agent` use `load_blueprint_contracts_only()`; `help_agent` uses `load_blueprint_prose_only()`; `blueprint_checker`, `blueprint_reviewer`, `hint_agent`, and `bug_triage` use `load_blueprint()` (both files). The internal helper `_get_unit_context` must accept `include_tier1: bool` and pass it through to `build_unit_context` (Unit 8). Blueprint directory resolution uses `get_blueprint_dir()` which reads `ARTIFACT_FILENAMES["blueprint_dir"]` from Unit 1 (Bug 60 fix) **(Post-delivery fix)**. `build_language_context()` NEW -- language context injected into all agent prompts **(NEW IN 2.2)**. Selective blueprint loading for Stage 2 agents: lessons learned loading for blueprint_author, blueprint_checker, blueprint_reviewer.

**Unit 14 (Routing + Test Execution -- HEAVIEST CHANGE, split in 2.2):** `TEST_OUTPUT_PARSERS` dispatch table **(NEW IN 2.2)**. Add quality gate routing paths **(NEW IN 2.1)**. Replace hardcoded commands with toolchain reader calls **(CHANGED IN 2.0)**. Implement the two-branch routing invariant (Section 3.6) for **every** sub-stage with an agent-to-gate transition in a single implementation pass -- not incrementally as bugs are discovered (Bug 43 fix): `route()` must check `last_status.txt` to distinguish "agent not yet done" from "agent done, present gate." This applies to Stage 0 (`project_context`, `project_profile`), Stage 1 (`stakeholder_spec_authoring` -- Bug 41 fix: Stage 1 routing must check for `SPEC_DRAFT_COMPLETE`/`SPEC_REVISION_COMPLETE` before presenting Gate 1.1), Stage 2 (`blueprint_dialog`, `alignment_check`), Stage 4 (integration test author), Stage 5 (git repo agent), redo profile sub-stages (`redo_profile_delivery`, `redo_profile_blueprint`), and all post-delivery debug loop agent-to-gate transitions (triage to Gate 6.2/6.4, repair to Gate 6.3, test agent to Gate 6.1). The invariant is a structural requirement -- not a per-stage fix list (Bug 21 generalized fix, Bug 43 universal compliance requirement, see Section 3.6) **(CHANGED IN 2.1, expanded by Bug 43)**. `GATE_RESPONSES`/`GATE_VOCABULARY` must include entries for every gate ID in the pipeline, and the set of gate IDs must be identical to `ALL_GATE_IDS` in Unit 13 (gate ID consistency invariant, Section 3.6 -- Bug 41 fix, expanded by Bug 43) **(Post-delivery fix)**. Wire alignment check into Stage 2 routing: after Gate 2.1 APPROVE, route to `alignment_check` sub-stage and invoke blueprint checker; on `ALIGNMENT_CONFIRMED`, present Gate 2.2; on Gate 2.2 APPROVE, advance to Pre-Stage-3; dispatch on checker failure outcome: `ALIGNMENT_FAILED: blueprint` resets to `blueprint_dialog`, `ALIGNMENT_FAILED: spec` initiates targeted spec revision — neither advances to Pre-Stage-3 (Section 8.2 invariant, Bug 23 fix) **(NEW IN 2.1)**. Any `route()` branch that performs an in-memory state transition (via `complete_*` or `advance_*`) and then recursively routes must persist state to disk via `save_state()` before returning the action block -- specifically, the Gate 2.2 APPROVE transition to `pre_stage_3` must be saved before the Pre-Stage-3/reference-indexing action block is returned (Bug 42 fix, route-level state persistence invariant, Section 3.6) **(Post-delivery fix)**. Add explicit routing branches for all core Stage 3 sub-stages (`stub_generation`, `test_generation`, `red_run`, `implementation`, `green_run`, `coverage_review`, `unit_completion`): `route()` must emit the correct action type (invoke_agent or run_command) for each sub-stage (Bug 25 fix, see Section 24.20) **(NEW IN 2.1)**. Add full Stage 5 sub-stage routing: `route()` must invoke git_repo_agent at `sub_stage=None`, present `gate_5_1_repo_test` at `repo_test`, run compliance scan at `compliance_scan`, and return `pipeline_complete` at `repo_complete`; all dispatch functions must perform proper state transitions (Bug 26 fix, see Section 24.21) **(Post-delivery fix)**. **Dispatch completeness for Stage 3 (Bugs 44-47 fix):** `dispatch_agent_status` for `test_agent` must handle `sub_stage=None` the same as `sub_stage="test_generation"` (Bug 44). `dispatch_command_status` for `test_execution` must advance `sub_stage` from `red_run` to `implementation` on `TESTS_FAILED` and from `green_run` to `coverage_review` on `TESTS_PASSED` -- no-op returns are invalid (Bug 45). `dispatch_agent_status` for `coverage_review` must advance `sub_stage` to `unit_completion` on `COVERAGE_COMPLETE` (Bug 46). The `unit_completion` routing action's COMMAND must not embed `update_state.py` calls -- state updates are exclusively in POST (Bug 47). See exhaustive dispatch invariants in Section 3.6 and COMMAND/POST separation in Key Constraints **(Post-delivery fix)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate argparse arguments for `update_state_main` (`--project-root`, `--gate-id`, `--unit`, `--phase`), `run_tests_main` (positional `test_path`, `--env-name`, `--project-root`, `--test-path`), and `run_quality_gate_main` (positional `gate_id`, `--gate`, `--target`, `--env-name`, `--project-root`). **Debug loop reassembly (Bug 51 fix):** `dispatch_agent_status` for `repair_agent` must trigger Stage 5 reassembly on `REPAIR_COMPLETE` during an active debug session -- set `stage="5"`, `sub_stage=None`. Debug session remains active. `REPAIR_FAILED` and `REPAIR_RECLASSIFY` retain existing behavior **(Post-delivery fix)**.

**Unit 15 (Quality Gate Execution -- NEW split in 2.2):** `QUALITY_RUNNERS` dispatch table. Gate composition read from language-specific toolchain **(NEW IN 2.1 scope, split in 2.2)**. Quality gate command execution dispatched by language.

**Unit 16 (Command Logic):** Replace hardcoded commands with toolchain reader calls **(CHANGED IN 2.0)**.

**Unit 17 (Hook Enforcement) (CHANGED IN 2.1):** Add write authorization for `project_profile.json`, `toolchain.json` **(CHANGED IN 2.0)**, `ruff.toml` **(NEW IN 2.1)**, delivered repo path during debug sessions **(NEW IN 2.1)**, and lessons learned document during debug sessions **(NEW IN 2.1)**. Add `PostToolUse` stub sentinel hook. Handler is a command hook (shell script). Matcher: Write tool calls to `src/unit_N/` paths. Behavior: grep written content for stub sentinel (from language registry); exit 2 with explanatory message if found. Write paths from language registry **(NEW IN 2.2)**.

**Unit 18 (Setup Agent):** Expand dialog for Area 0 (language and ecosystem configuration) **(NEW IN 2.2)**, Area 5 (quality preferences) **(NEW IN 2.1)**, changelog question in Area 1 **(NEW IN 2.1)**. Profile dialog and Gate 0.3. Targeted revision mode **(CHANGED IN 2.0)**. The setup agent's system prompt must include the complete `project_profile.json` schema with exact canonical field names (Section 6.4) so that the agent's JSON output uses the same section and field names as `DEFAULT_PROFILE` in Unit 3 **(NEW IN 2.1)**. Language-keyed profile output **(NEW IN 2.2)**.

**Unit 19 (Blueprint Checker) (CHANGED IN 2.1):** Add quality profile preference validation (Layer 2) **(NEW IN 2.1)**. Blueprint checker receives the pattern catalog section of `svp_2_1_lessons_learned.md` as an additional input. Checker produces a risk section in its output identifying structural features matching known failure patterns (P1-P9+). Advisory only -- does not block approval. Language registry completeness validation. Profile language-key validation **(NEW IN 2.2)**.

**Unit 20 (Construction Agent Defs):** Add quality awareness to agent prompts **(NEW IN 2.1)**. Agent prompts reference `LANGUAGE_CONTEXT`. Language-conditional guidance **(NEW IN 2.2)**.

**Unit 21 (Diagnostic/Redo Agent Defs):** Add `profile_delivery` and `profile_blueprint` classifications **(CHANGED IN 2.0)**.

**Unit 23 (Utility Agent Defs + Assembly Dispatch):** Reference Indexing Agent, Checklist Generation Agent **(NEW IN 2.2)**, Regression Test Adaptation Agent **(NEW IN 2.2)**, **Oracle Agent (NEW IN 2.2)**, Git Repo Agent. Generate delivered quality tool configs **(NEW IN 2.1)**. Generate changelog **(NEW IN 2.1)**. Deliver all project documents to repo (unified Bug 15 fix) **(NEW IN 2.1)**. Read profile for all delivery preferences **(CHANGED IN 2.0)**. Record `delivered_repo_path` in `pipeline_state.json` at Stage 5 completion **(NEW IN 2.1)**. Environment name in delivered `environment.yml` and `README.md` must use canonical `derive_env_name()` derivation from Unit 1, not independent derivation (Bug 27 fix, see Section 24.22) **(Post-delivery fix)**. `PROJECT_ASSEMBLERS` dispatch table. Language-keyed delivery config generation **(NEW IN 2.2)**. `assembly_map.json` generation. Oracle agent definition includes dry run and green run modes, stateless principle, nested session bootstrap (Section 35.17), pipeline state isolation.

**Unit 25 (Slash Commands) (CHANGED IN 2.1):** Group B command definitions (`help`, `hint`, `ref`, `redo`, `bug`) must include the complete action cycle: steps for running `prepare_task.py`, spawning the agent, writing status to `.svp/last_status.txt`, running `update_state.py --phase <phase>` with the correct phase value, and re-running the routing script. The `--phase` values are: `help`, `hint`, `reference_indexing`, `redo`, `bug_triage`. These must match the `phase_to_agent` mapping in Unit 14. A command definition that stops after "spawn the agent" is incomplete and will cause the main session to fail the action cycle (Bug 38 fix).

**Unit 26 (Orchestration Skill) (CHANGED IN 2.1):** `SKILL_MD_CONTENT` must include a section on slash-command-initiated action cycles. Group B commands bypass the routing script -- the command definition substitutes for the routing script's action block. The skill must explain that the same six-step cycle applies, with the command definition providing the PREPARE command, agent type, and POST command (including the correct `--phase` value). Without this section, the main session has no behavioral guidance for completing the action cycle when a slash command is invoked outside the routing loop (Bug 39 fix). Three-layer model explanation. Language context flow guidance **(NEW IN 2.2)**.

**Unit 27 (Project Templates):** Add `ruff.toml` to project templates **(NEW IN 2.1)**. Update toolchain default JSON **(NEW IN 2.1)**. Language-specific toolchain files. Delivery quality templates. `claude_md.py` with language note **(NEW IN 2.2)**.

**Unit 28 (Plugin Manifest + Validation + Compliance):** Validate quality section in structural validation **(NEW IN 2.1)**. Add `toolchain_defaults/` **(CHANGED IN 2.0)**. Per the CLI argument enumeration invariant (Bug 49 fix), the blueprint Tier 2 must enumerate `compliance_scan_main()`'s argparse arguments: `--project-root`, `--src-dir`, `--tests-dir`. `COMPLIANCE_SCANNERS` dispatch table. `validate_dispatch_exhaustiveness()` **(NEW IN 2.2)**.

**Unit 29 (Launcher -- NEW in 2.2):** Copy `ruff.toml` during project creation and set to read-only **(NEW IN 2.1)**. Copy toolchain file **(CHANGED IN 2.0)**. Implement `svp restore` subcommand with document placement and state initialization **(CHANGED IN 2.1)**. Implement full pre-flight check sequence with ordered checks and specific error messages (Section 6.1.2) **(CHANGED IN 2.1)**. Session launch via `subprocess.run` with `cwd`, `env` (for `SVP_PLUGIN_ACTIVE`), and restart signal loop (Section 6.1.5) **(CHANGED IN 2.1)**. `parse_args` must enumerate all argparse arguments in Tier 2 invariants per the CLI argument enumeration invariant (Section 3.6, Bug 48 fix): bare `svp` defaults `args.command = "resume"`, restore mode uses `--blueprint-dir` (directory, not file), and `--profile` is a required restore argument **(Post-delivery fix)**. Language runtime pre-flight checks. `_DEFAULT_REGISTRY` sync with Unit 2 **(NEW IN 2.2)**.

**Critical: Dual write-path awareness (NEW IN 2.1).** Two independent write paths exist in the pipeline: agent writes (through Claude Code's Write tool, validated by `PreToolUse` hooks) and pipeline subprocess writes (quality auto-fix, assembly scripts, executed via `subprocess.run` from deterministic scripts). Hooks control the first path; they do not intercept the second. This is correct by design -- quality tools and assembly scripts are pipeline infrastructure, not agent actions. The blueprint author must not implement hooks that assume all file modifications flow through Claude Code's Write tool. Conversely, the blueprint author must not assume subprocess writes are covered by hook authorization. Both paths must be considered independently when designing write authorization rules. This dual-path model applies during both the build (Sections 10.3, 10.6, 10.12) and the post-delivery debug loop (Section 12.18.10).

**Critical: Contract sufficiency and boundary awareness (NEW IN 2.1 -- Bug 50 fix).** The blueprint author must apply both the contract sufficiency invariant (Section 3.16) and the contract boundary rule (Section 3.16) when designing each unit. Concretely: (1) Every function whose behavior depends on specific data values (e.g., `_MODEL_CONTEXT_WINDOWS` mapping model names to token counts, `_RECOGNIZED_PLACEHOLDERS` listing valid placeholder names, enum validation sets like `{"ruff", "flake8", "pylint", "none"}`) must have those values specified in the Tier 2 invariants or Tier 3 contract. (2) Internal helper functions (underscore-prefixed, not imported cross-unit) must NOT appear in Tier 2 signatures -- their behavioral effect must instead be described in the Tier 3 contract of the public function that uses them. Example: `_deep_merge` should not be in Tier 2, but `load_config`'s Tier 3 contract should say "missing keys filled from defaults via recursive merge: for nested dicts, merge recursively; for non-dict values, override wins."

---

## 31. Forking Point Classification (CHANGED IN 2.1)

**Tier A (pipeline-fixed):** Pipeline language (Python), pipeline environment (conda), pipeline test framework (pytest), pipeline build backend (setuptools), pipeline VCS (git), pipeline quality tools (ruff + mypy), source layout during build (SVP-native). These are the tools SVP itself runs as (Layer 1, Section 3.25). Recorded in profile `fixed` section. Not presented as choices.

**(NEW IN 2.2)** Target language tools (environment manager, test framework, quality tools) are determined by the language registry (Section 40.2) based on language selection in Area 0. They are not directly user-configurable but are not pipeline-fixed either -- they vary by language. For example, an R project uses renv/testthat/lintr (not conda/pytest/ruff). These are Layer 2 tools, distinct from both Tier A (pipeline-fixed) and Tier B (delivery-configurable).

**Tier B (delivery-configurable):** Five dialog areas: version control (commit style, branch strategy, tagging, changelog), README and documentation (audience, sections, depth, optional content), testing (coverage, readable names), licensing and packaging (license, metadata, entry points, delivery environment, dependency format, source layout), delivered quality tools (linter, formatter, type checker, import sorter, line length). Captured in profile. Acted on by git repo agent.

**Unsupported preferences.** If the human requests a delivery feature that SVP 2.2 does not support (CI templates, Docker, pre-commit hooks, documentation sites, etc.), the setup agent acknowledges the request, explains honestly that SVP does not handle it, and tells the human they will need to add it manually after delivery. Nothing is recorded in the profile. **(CHANGED IN 2.2)**

---

## 32. What the Blueprint Author Must NOT Do (CHANGED IN 2.1, CHANGED IN 2.2)

- Build provider interfaces or abstract base classes. Note: the six data-driven dispatch tables specified in Section 40.3 are the required language-dispatch mechanism — they are dict-based lookups, not the prohibited pattern. The prohibition targets unnecessary abstraction layers: ABC hierarchies, plugin registries, metaclass-based dispatch, or any indirection that adds complexity beyond what the six dispatch tables provide.
- Make `toolchain.json` user-editable.
- Make `ruff.toml` user-editable **(NEW IN 2.1)**.
- Parameterize agent definition files with toolchain variables.
- Add a language or toolchain selection dialog.
- Break behavioral equivalence for existing toolchain sections.
- Add new stages, agents, or gate types for quality gates **(NEW IN 2.1)**.
- Implement quality gates as fix ladder positions **(NEW IN 2.1)**.

**(NEW IN 2.2)** The following additional prohibitions apply to the language-dispatch framework:

1. **Must not add non-Python, non-R entries to LANGUAGE_REGISTRY as built-in.** Built-in entries are Python and R only (plus Stan as component). Any other language is dynamically constructed through Area 0 dialog.
2. **Must not add language-conditional branches in routing or dispatch.** No `if language == "python"` in pipeline logic. All language-specific behavior goes through dispatch tables.
3. **Must not collapse the three-layer split.** Pipeline quality and delivery quality are independent code paths with no cross-reads.
4. **Must not make dispatch table entries optional for full languages.** Every registered full language (not component-only) must have all six dispatch entries.
5. **Must not break behavioral equivalence with SVP 2.1.** All SVP 2.1 regression tests pass with adapted imports.
6. **Must not add forward dependencies to the DAG.** All unit dependencies point backward.
7. **Must not hardcode language-specific file extensions, directory names, or tool names.** All language-specific values come from the registry or toolchain files.

---

## 33. Self-Hosting Invariant (CHANGED IN 2.2)

SVP is a Python application. It will always be a Python application. The `toolchain.json`, `ruff.toml`, and `project_profile.json` govern the target project. SVP's own build toolchain is always `python_conda_pytest` with ruff and mypy for quality. The abstraction layer sits between SVP and the projects it builds, not between SVP and itself.

**Mode A pipeline/delivery split.** When SVP builds SVP, the pipeline toolchain and the delivery toolchain happen to coincide (both are Python/Conda/pytest/ruff/mypy). This coincidence must not collapse the separation. The pipeline reads `toolchain.json` for build commands. The git repo agent reads `project_profile.json` for delivery configuration. These are different code paths that produce the same result in Mode A and different results in Mode B. A blueprint that short-circuits by reading profile data during the build (or toolchain data during delivery) is architecturally wrong even if it produces correct output for the self-build case.

**(CHANGED IN 2.2)** The self-hosting invariant is extended: SVP 2.2 must be able to build itself (Mode A self-host) with all tests passing. Additionally, SVP 2.2 must produce behaviorally equivalent output to SVP 2.1 for Python-only projects -- the language-dispatch framework adds capability without changing existing behavior. A behavioral equivalence regression test verifies this.

The self-hosting invariant is operationalized by the two-pass bootstrap protocol (Section 43). Every SVP self-build must complete both passes. Pass 1 (scaffolding) builds SVP N+1 under SVP N — its output is a tool, not the delivery. Pass 2 (production) rebuilds SVP N+1 under itself — its output is the authoritative deliverable. A self-build that completes only Pass 1 has produced scaffolding, not a delivered product, and has not satisfied the invariant.

---

## 34. Glossary

SVP terms — pipeline architecture, four-layer orchestration, three-layer preference enforcement, quality gates, command groups, forking point tiers, document types, configuration files, agent roles, and Claude Code ecosystem concepts — are defined in context throughout this document where they are first used.

**Additional terms (NEW IN 2.2):**

- **Language Registry:** Data structure mapping language identifiers to complete build/test/lint/deliver configurations. See Section 40.2.
- **Dispatch Table:** Per-language function lookup table. Six tables distribute language-specific logic across pipeline units. See Section 40.3.
- **Three-Layer Toolchain Model:** Pipeline (fixed) / Build-time target (per-language) / Delivery (user-configurable). See Section 3.25.
- **Component Language:** A language that cannot be a project's primary language; requires a host language (e.g., Stan requires R or Python). See Section 3.27. **(CHANGED IN 2.2) Stage 3 lifecycle for component languages:** Component languages have a reduced per-unit cycle: stub generation produces a template, quality gate runs syntax validation only (e.g., Stan compiler syntax check), no independent test suite is generated (component files are tested through their host language's tests). The blueprint author determines which units contain component language files based on the stakeholder spec.
- **Dynamic Registry Construction:** [DEFERRED] Socratic dialog mechanism for configuring languages not built into SVP. Designed but not active in SVP 2.2; activated via self-build with `self_build_scope: "language_extension"`. See Sections 3.28 and 43.3.
- **Primary Language:** The main language of a delivered project; determines project structure and default tooling.
- **Hard Stop Protocol:** Procedure for handling builder pipeline bugs during a build. See Section 41.
- **Two-Pass Bootstrap (CHANGED IN 2.2):** Protocol for SVP self-builds. Pass 1 (scaffolding): SVP N builds SVP N+1 through Stages 0–5; output is scaffolding, NOT the deliverable. Pass 2 (production): SVP N+1 rebuilds itself via orchestrator-driven nested session from Pre-Stage-3 through Stage 5; output is the authoritative deliverable. See Section 43.
- **Pass 1 (Scaffolding):** First pass of E/F self-build. SVP N builds SVP N+1. Output is a tool for building, not the delivered product. See Section 43.2.
- **Pass 2 (Production):** Second pass of E/F self-build. SVP N+1 rebuilds itself through an orchestrator-driven nested session. Output is the real deliverable. See Section 43.2.
- **Self-Build Scope:** Classification of a self-build scenario as `"language_extension"` (low risk, 5 artifacts change) or `"architectural"` (high risk, pipeline mechanisms change). Determines orchestrator posture and verification requirements. See Section 43.
- **Break-Glass Protocol (NEW IN 2.2):** Orchestrator escalation mechanism for E/F self-build failures that exhaust normal retry paths. Narrow, enumerated permitted actions. See Section 43.9.
- **Deferred Broken (`deferred_broken`) (NEW IN 2.2):** Unit status indicating a unit failed during break-glass handling and was deferred by human decision. Must be resolved before pass completion. See Section 3.6.
- **E-Mode (Product Testing) (NEW IN 2.2):** Oracle mode for `svp_language_extension` archetypes. Tests the product (new language dispatch) using GoL re-expression test projects. See Section 3.33.
- **F-Mode (Machinery Testing) (NEW IN 2.2):** Oracle mode for `svp_architectural` archetypes. Tests the pipeline machinery (routing, state, gates) using SVP `docs/`. See Section 3.33.
- **Mode A (Self-Build):** When SVP builds SVP (Options E and F). The pipeline toolchain and delivery toolchain coincide. See Section 33.
- **Mode B (Standard Build):** When SVP builds a non-SVP project (Options A-D). The pipeline toolchain and delivery toolchain are independent.

---

## 35. Pipeline Acceptance Testing: `/svp:oracle` (NEW IN 2.2)

### 35.1 Overview

SVP 2.2 introduces `/svp:oracle`, a post-delivery pipeline acceptance testing tool. It verifies that the delivered SVP pipeline actually functions as a pipeline from a user's perspective -- that a new project can be driven through all stages to a correct delivery.

**Scope and purpose.** `/svp:oracle` is for debugging SVP itself — it is not a general-purpose acceptance testing framework for projects built by SVP. It exists because SVP's product-level integration failures — broken routing paths, unreachable gates, malformed agent prompts — are undetectable by unit tests (Stage 3), integration tests (Stage 4), or structural checks (Stage 5). These are integration failures at the product level, not the code level. End-to-end execution with a known test project is the only viable verification method.

**Simulation-only constraint:** The oracle does NOT deliver a Game of Life repo, a new SVP repo, or any other usable deliverable. The oracle creates a SIMULATION ENVIRONMENT for verification purposes only. The nested pipeline run is disposable -- its artifacts exist only to verify pipeline behavior, not to produce a usable deliverable. The nested session's workspace and any repository it generates are temporary verification artifacts that may be discarded after the oracle session concludes. No consumer of SVP should treat oracle-generated artifacts as production outputs.

### 35.2 Lifecycle Position (CHANGED IN 2.2)

**Distinction between Stage 6 and Stage 7.** See Section 5 for the post-delivery tool lifecycle. Stage 6 (`/svp:bug`) fixes bugs in any delivered project. Stage 7 (`/svp:oracle`) verifies that SVP itself works as a pipeline. Stage 7 is available only when `is_svp_build` is true AND Pass 2 is complete.

- `/svp:oracle` is available to the human after Pass 2's Stage 5 completes, but only when `is_svp_build` is true in the project profile. **(CHANGED IN 2.2)** The `is_svp_build` field AND Pass 2 completion are both required gates for oracle availability -- the routing script checks both before offering `/svp:oracle`. The oracle is NOT available after Pass 1's Stage 5 (Section 43.7).
- It is NOT mandatory. It is NOT automatic. It does NOT run as part of the pipeline.
- It is an ALTERNATIVE to `/svp:bug`, not a prerequisite for it.
- After Pass 2's Stage 5, the human chooses which post-delivery tool to invoke: `/svp:bug` or `/svp:oracle` (Section 43.7).
- Each `/svp:oracle` invocation is self-contained: at most one discovery fixed, then exit. A "discovery" is a root cause or related cluster of bugs found during normal trajectory execution; it may span multiple units.
- Full restart on each invocation -- the oracle does not skip previously tested paths. The run ledger is context (so the oracle knows what happened before), not a skip list.

### 35.3 Interaction Between `/svp:oracle` and `/svp:bug`

- The human can invoke `/svp:bug` or `/svp:oracle` independently after Stage 5. **(CHANGED IN 2.2)** For E/F archetypes, "after Stage 5" means after Pass 2's Stage 5. `/svp:oracle` is not available after Pass 1's Stage 5 (Section 43.7).
- The human CANNOT invoke `/svp:bug` directly while an `/svp:oracle` session is active.
- During an active `/svp:oracle` session, the oracle itself can call `/svp:bug` internally (during the green run phase) to fix a discovered bug.
- Once the `/svp:oracle` session exits, the human regains access to both `/svp:bug` and `/svp:oracle`.

### 35.4 Sub-Stage Structure

Each `/svp:oracle` invocation follows four phases:

**(NEW IN 2.2) Oracle gate dispatch:**
- **Gate 7.A (APPROVE TRAJECTORY):** Sets oracle phase to `green_run`. Proceeds to green run execution.
- **Gate 7.A (MODIFY TRAJECTORY):** Returns to dry run phase. Oracle re-analyzes and produces a revised trajectory.
- **Gate 7.A (ABORT):** Logs abort to run ledger. Exits oracle session.
- **Gate 7.B (APPROVE FIX):** Oracle calls `/svp:bug` internally with the approved fix plan.
- **Gate 7.B (ABORT):** Logs abort with discovery details to run ledger. Exits oracle session.

Each response has an explicit state transition. No response is a no-op.

**(NEW IN 2.2 — Bug S3-65) Test project selection.** When `/svp:oracle` is invoked, the orchestration skill handles test project selection before entering the routing cycle. The selected test project path is passed via `update_state.py --command oracle_start`. If the oracle enters dry_run with no test project set, routing returns an `oracle_select_test_project` action block requiring selection before proceeding.

**(NEW IN 2.2) Oracle mode selection for E/F archetypes.** The oracle operates in one of two modes, determined by the human's test project selection (Section 3.33):

- **E-mode (product testing):** Activated when the human selects a GoL test project. The oracle verifies that the product works — the new language dispatch produces correct projects. Test projects are the GoL re-expressions produced by the E build (Section 43.3). The oracle does NOT re-test routing (assumed unchanged for language extensions).
- **F-mode (machinery testing):** Activated when the human selects SVP `docs/` as the test project. The oracle verifies that the pipeline machinery works — routing, state transitions, gates, and orchestration function correctly.

The human selects the mode by choosing a test project at invocation (Section 3.33): GoL test project → E-mode, SVP `docs/` → F-mode.

#### Phase 1: Dry Run (Planning / Spec-Driven Analysis) (CHANGED IN 2.2)

The oracle's primary input is a **spec** — the spec defines what "correct" means. Code is the subject of evaluation, not the lens. The oracle reads the spec, then evaluates code against it, then proves its evaluation by executing the pipeline (in the green run).

**(CHANGED IN 2.2) Mode-specific dry run analysis:**

**E-mode dry run (product testing).** The oracle reads:
- The GoL spec (the selected test project) — this defines what the product should do.
- The new language's implementation code from the delivered repository — the 5 artifacts from Section 40.5: (1) registry entry, (2) toolchain JSON, (3) setup interview path, (4) dispatch table implementations (`STUB_GENERATORS[new_lang]`, `QUALITY_RUNNERS[new_lang]`, etc.), (5) spec documentation.
- The oracle plans how to drive the pipeline with the GoL spec and what to check at each stage: "At Stage 3, the spec says stub generation should produce files in the new language; I'll verify the dispatch table routes correctly and the stubs are valid."
- Analysis is focused on language-specific code. The oracle does NOT re-analyze routing or state machinery (assumed unchanged for language extensions).

**F-mode dry run (machinery testing).** The oracle reads:
- The SVP stakeholder spec — this defines how the pipeline should behave at every gate and state transition.
- The pipeline machinery code from the delivered repository: routing scripts, state transition functions, gate dispatch tables, orchestration logic.
- The oracle plans which gates to check, which state transitions to verify, which routing paths to exercise: "At Gate 2.1, the spec says APPROVE should advance to alignment_check; I'll verify the routing dispatches correctly."
- Analysis focuses on pipeline machinery. The oracle does NOT evaluate the quality of code the pipeline produces.

**Both modes:** The spec is the source of truth. The dry run plans a trajectory of evaluations — at each step, the oracle knows what the spec requires and plans to verify it. Does NOT execute the pipeline. Does NOT apply any fixes.

**First run vs. subsequent runs.** If this is the first `/svp:oracle` invocation (empty run ledger), the oracle plans from scratch. If prior runs exist, the oracle reads the run ledger to retrieve relevant events — what was tested, what was found, what was fixed — and factors this into trajectory prioritization.

**(CHANGED IN 2.2)** During the dry run, the oracle reads and analyzes source code from the **delivered repository** -- this is the code that will actually execute when the delivered SVP is used as a plugin. The oracle uses `assembly_map.json` to correlate delivered repo paths back to workspace unit paths when planning fixes. The oracle does NOT analyze workspace `src/unit_N/` files (build scaffolding with different paths) or workspace `scripts/` files (these are SVP 2.1 -- the builder, not the deliverable).

The output is a trajectory plan with risk-prioritized execution order.

**(NEW IN 2.2) Context budget management.** If the codebase under analysis exceeds the oracle agent's effective context budget, the oracle performs selective analysis. For F-mode: it prioritizes routing scripts, state transition logic, and dispatch tables over agent definitions and template files. For E-mode: it prioritizes dispatch table entries and language-specific toolchain code over unchanged pipeline code. The oracle reports which files it analyzed and which it skipped in its trajectory plan, so the human can assess coverage and adjust the test strategy at Gate A.

#### Phase 2: Human Consultation (Gate A -- Review Plan)

The trajectory plan is presented to the human. The oracle summarizes its run history from previous invocations (read from the run ledger) so the human has full context on what has been tested, found, and fixed in prior runs. The human and oracle agent together:

- Review the planned test trajectory.
- Confirm the risk prioritization.
- Identify any paths the oracle missed or the human considers high-priority.
- Approve the plan or request modifications.

This is a human decision gate. The oracle does not proceed to the green run without human approval. **The human can abort at Gate A.** If the human aborts, the oracle does not proceed -- it logs the abort to the run ledger and exits (see Section 35.14).

**(NEW IN 2.2) Gate A mandatory information.** The trajectory plan presented at Gate A must include: (1) the selected test project name and oracle mode (E-mode or F-mode), (2) summary of prior runs from run ledger (if any) — what was tested, found, fixed, and any unresolved bugs, (3) the risk-prioritized trajectory with pass ordering and estimated scope, (4) which files/paths the oracle analyzed during dry run and which were skipped (context budget), (5) human observations from prior runs (if the human provided any at the previous Gate A). The human can ask clarifying questions before responding. **MODIFY TRAJECTORY behavior:** the human provides guidance in natural language (e.g., "prioritize the Julia dispatch path" or "I noticed the scroll bar didn't render — test that first"); the oracle re-enters dry run incorporating the guidance and produces a revised plan presented at a new Gate A. **(CHANGED IN 2.2) Modification bound:** MODIFY TRAJECTORY may be selected up to 3 times per oracle invocation. After 3 modifications, only APPROVE TRAJECTORY and ABORT are offered.

#### Phase 3: Green Run (Execute Trajectory, Find Bugs, Fix via `/svp:bug`) (CHANGED IN 2.2)

The oracle agent executes the approved trajectory against the delivered pipeline. This is the execution phase. The green run behavior differs by mode:

**(NEW IN 2.2) E-mode green run (product testing).** The oracle feeds the GoL spec into a nested pipeline session. The nested session builds the GoL project through Stages 0-5 using normal SVP pipeline mechanics. The oracle monitors progress, but its primary evaluation is the **product**:

- After the nested session completes Stage 5, the oracle runs the GoL test suite (unit tests, integration tests). This is the primary, deterministic verification.
- Optional: the oracle may invoke the `/svp:visual-verify` skill (Section 35.18) for GUI-based test projects — capture screenshots and perform visual sanity checks. This is supplementary, not authoritative.
- The oracle checks that assembly produced valid artifacts for the new language (correct file types, directory structure, manifest entries).
- If product evaluation fails → that's the discovery. The oracle classifies the root cause and presents at Gate B.
- The GoL project persists after the oracle exits — sibling of the delivered repo, same parent directory. The human can inspect and run it.

**(NEW IN 2.2) F-mode green run (machinery testing).** The oracle drives the nested pipeline session with the SVP stakeholder spec and evaluates pipeline **behavior** at each gate and state transition:

- Drives the pipeline end-to-end, supplying inputs at each gate and decision point per the approved trajectory.
- At each step, classifies pipeline behavior as:
  - **Root cause** -- independently wrong, not explained by an earlier issue.
  - **Possibly downstream** -- may be caused by an earlier failure (cascade noise).
  - **Clean** -- correct behavior.
- Records diagnostic entries at each observation point (see Section 35.12).
- In F-mode, the generated code is disposable. The oracle does not evaluate the quality of the code produced by the nested session — only the pipeline's behavior during production. The artifacts of value are: bug identification, documentation, regression tests written, fixes applied, and the rebuilt repo via Stage 5 reassembly.

**Both modes:** If a bug is found, the oracle presents its fix plan to the human at **Gate B** (see below). At most ONE DISCOVERY is fixed per `/svp:oracle` invocation. A "discovery" is a root cause or related cluster of bugs encountered during trajectory execution. If a single root cause manifests across multiple units, the oracle plans and executes a comprehensive fix covering all affected units in a single triage cycle. The oracle uses its dry-run code knowledge to plan smartly -- it does not fix myopically.

**Gate B (Fix Plan Review):** Before calling `/svp:bug`, the oracle shares its fix plan with the human. This is the second human decision point. The oracle and human decide together whether to proceed with the fix. **The human can abort at Gate B.** If the human aborts, the oracle logs the abort (including the discovery and planned fix) to the run ledger and exits (see Section 35.14).

**(NEW IN 2.2) Gate B mandatory information.** The fix plan presented at Gate B must include: (1) root cause description — what's wrong and why, with reference to the spec requirement being violated, (2) affected units/files, (3) proposed change — what the oracle plans to tell `/svp:bug` to fix, (4) expected outcome — what should be different after the fix, (5) risk assessment — could this fix break other things? The human can ask clarifying questions before responding.

**Fix verification (CHANGED IN 2.2):** After `/svp:bug` completes (which includes Stage 5 reassembly), fix verification consists of two distinct steps:
1. **Code verification:** Using `assembly_map.json`, confirm the fix landed in both the workspace (`src/unit_N/` files) and the delivered repo (proper module paths). Compare file content to ensure consistency.
2. **Behavioral verification:** Tear down the stale nested session, recreate a fresh nested session using the UPDATED delivered plugin, and re-drive the pipeline to verify the behavior is corrected. The old nested session used pre-fix code and cannot be reused.

If the fix did not resolve the issue or did not propagate correctly, the oracle calls `/svp:bug` again. This fix verification cycle is bounded to 2 attempts per bug. If the fix is not verified after 2 attempts, the unresolved bug is recorded in the diagnostic map, the oracle continues its trajectory, and the unresolved bug is reported at Gate B in the exit report.

After the fix is verified: the oracle produces a full report to the human (what was found, what was fixed, verification result), logs the outcome to the run ledger, and exits.

**(NEW IN 2.2) Oracle as surrogate human during `/svp:bug`.** When the oracle invokes `/svp:bug` internally after Gate B approval: (1) the oracle provides the discovery data (root cause, affected units, proposed fix) as the initial bug description, (2) at Gate 6.0 (debug permission), the oracle auto-responds AUTHORIZE DEBUG, (3) at Gate 6.2 (classification), the oracle provides its classification based on dry-run analysis, (4) at subsequent debug gates, the oracle responds based on its fix plan approved at Gate B, (5) at Gate 6.1 (regression test review), the oracle evaluates the test against its spec knowledge and responds TEST CORRECT or TEST WRONG. The oracle does NOT surface these internal gates to the human — the human's approval was given at Gate B. The oracle is a fully autonomous surrogate human within the debug loop.

#### Phase 4: Exit

The oracle session concludes in one of three ways:

- **All-clear:** All passes defined in the trajectory configuration (`oracle_trajectory.json`) executed without discovering any bugs. The pipeline passes acceptance testing for this trajectory.
- **After fix:** A bug was discovered, approved at Gate B, fixed via internal `/svp:bug` call, verified, and the oracle exits. The human can invoke `/svp:oracle` again to continue testing with a fresh session.
- **Human abort:** The human aborted at Gate A or Gate B. Partial results are preserved in the run ledger.

**(NEW IN 2.2) Exit report mandatory information.** The exit report presented to the human must include:
- **All-clear exit:** Which trajectory passes were executed, how many diagnostic entries were recorded, summary of PASS/FAIL/WARN classifications, confirmation that all passes completed without discovery.
- **After-fix exit:** The discovery (root cause, affected units), the fix applied, verification result (passed/failed, attempt count), any unresolved bugs from failed verification attempts.
- **Abort exit:** Which phase was active at abort, what had been completed, any partial discoveries logged.
- **All exits include:** total elapsed time, test project used, oracle mode, run number.

**(NEW IN 2.2) E-mode artifact persistence.** In E-mode, the GoL project built during the green run persists after the oracle session exits — it is placed as a sibling of the delivered repo (same parent directory). The human can inspect, run, and interact with the oracle about it at Gate A on the next `/svp:oracle` invocation. In F-mode, the nested session's generated code is disposable — only the bug discovery/fix cycle and the run ledger entries have lasting value.

### 35.5 Trajectory Strategy: Risk-Prioritized

The oracle plans and executes its trajectory using a three-pass risk-prioritized approach:

1. **Happy path first:** The primary end-to-end pipeline execution with valid inputs and expected gate responses. This exercises the mainline routing path that every project will follow. If this fails, nothing else matters.

2. **Revision paths second:** Paths involving gate decisions that trigger revisions, rollbacks, or re-passes (e.g., REVISE at a spec review gate, FIX BLUEPRINT, `/svp:redo`). These are the second most common execution paths and exercise the pipeline's ability to handle corrections.

3. **Error paths third:** Edge cases, error conditions, malformed inputs, and failure recovery paths. These exercise the pipeline's robustness and error handling.

Within each pass, the oracle prioritizes paths by estimated risk of failure (based on code complexity, number of state transitions, and code coverage gaps identified during the dry run).

**Archetype-specific trajectory priorities.** Each test project exercises pipeline paths specific to its archetype. The oracle's trajectory plan should prioritize paths unique to that archetype:
- **R test project:** R dispatch at every Stage 3 checkpoint (stub generation, quality gates, test execution), renv environment creation, R-specific structural validation.
- **Plugin test project:** Plugin artifact structural validation (40.7.6), multi-artifact-type stub generation (40.7.4), language-tag-dependent quality gates, plugin manifest validation, delivered plugin directory structure.
- **Mixed test projects:** Cross-language bridge tests (Stage 4), two-phase assembly composition (Stage 5), shared conda environment with bridge libraries.

**(NEW IN 2.2) E/F archetype trajectory priorities.** E and F archetypes have fundamentally different oracle verification targets:

- **E-mode (product testing):** Trajectory exercises the new language dispatch through the full pipeline. Test projects are the GoL re-expressions produced by the E build (Section 43.3). Priorities: new-language-specific dispatch at every Stage 3 checkpoint (stub generation using `STUB_GENERATORS[new_lang]`, quality gates using `QUALITY_RUNNERS[new_lang]`, test execution using `TEST_OUTPUT_PARSERS[new_lang]`), new-language assembly (`PROJECT_ASSEMBLERS[new_lang]`), new-language compliance scanning (`COMPLIANCE_SCANNERS[new_lang]`). If mixed-pair test projects exist, additionally: cross-language bridge tests, two-phase assembly composition.
- **F-mode (machinery testing):** Trajectory exercises routing, state transitions, gate dispatch, and pipeline flow. Uses SVP `docs/` as test project (the pipeline rebuilding itself). Priorities: routing path coverage (every reachable branch in `route()`), gate reachability (every gate ID in `GATE_VOCABULARY` is exercisable), state machine integrity (every state transition produces the correct next state), break-glass protocol paths (if applicable).
**Configurable per test project:** The trajectory strategy is configurable per test project via `examples/<project>/oracle_trajectory.json`. This configuration file specifies: `passes` (array of pass names to execute, e.g., `["happy_path", "revision_paths", "error_paths"]`), `timeout_minutes` (integer, maximum minutes per green run invocation), and `max_bugs` (integer, maximum discoveries per invocation — always 1 in the current design but parameterized for future use). A smoke test project may use happy-path-only, while a thorough test project uses the full three-pass strategy. The human selects the test project and its associated trajectory configuration before invocation.

### 35.6 Test Projects

The acceptance framework supports multiple test projects. This framework exists to test SVP itself -- it is not a general-purpose testing tool for projects built by SVP.

Each test project requires:
- A `project_context.md` file describing the project.
- A `stakeholder_spec.md` file with requirements for the test project.
- Blueprint documents (prose and contracts).

Each artifact is required because it enables the oracle to probe a specific pipeline stage:

- **project_context.md** enables probing **Stage 0 (setup)** -- the oracle can verify that the setup agent correctly processes project context.
- **stakeholder_spec.md** enables probing **Stage 1 (spec authoring)** -- the oracle can verify that the spec dialog, review, and approval workflow functions correctly.
- **Blueprint documents (prose and contracts)** enable probing **Stage 2 (blueprint generation and alignment)** and **Stage 3 (unit verification)** -- the oracle can verify blueprint decomposition, alignment checking, and the per-unit test/implement/verify cycle.

Without these artifacts, the oracle cannot verify whether the pipeline correctly handles each stage's inputs and outputs.

Available test projects:

- **SVP self-build (always available):** SVP uses its own pipeline documents (`docs/`) as the test project. The oracle reads artifacts implicitly from `docs/` -- specifically `docs/project_context.md`, `docs/stakeholder_spec.md`, and blueprint documents (`docs/blueprint_prose.md`, `docs/blueprint_contracts.md`). No `examples/` folder is needed because the pipeline's own documentation serves as the test project. If the result passes SVP's own regression tests, this constitutes the strongest possible validation -- the system can reproduce itself. This test project is always available because it uses the pipeline's own documentation. **(CHANGED IN 2.2)** For SVP self-build, the oracle reads the spec and blueprint from the delivered repo's `docs/` directory (e.g., `docs/stakeholder_spec.md`, `docs/blueprint_prose.md`, `docs/blueprint_contracts.md`). These are the delivered copies. The workspace `specs/` and `blueprint/` directories contain the same content (per the artifact synchronization invariant) but the delivered repo is the authoritative source for oracle evaluation because the oracle is testing the delivered product.
- **Additional test projects (in `examples/`):** Other test projects may be created and placed in `examples/` following the required structure above. The oracle reads artifacts from `examples/<project_name>/` -- specifically `examples/<project_name>/project_context.md`, `examples/<project_name>/stakeholder_spec.md`, and blueprint documents in the same directory. These are designed to exercise specific pipeline paths (e.g., a simple project for smoke testing, a project with unusual constraints for edge-case coverage).
- The mixed archetype test projects (`examples/gol-python-r/`, `examples/gol-r-python/`) exercise pipeline paths not covered by other test projects: Option D setup dialog, dual-language Stage 3 dispatch, cross-language bridge tests in Stage 4, and two-phase Stage 5 assembly composition. These are high-value oracle trajectories for verifying mixed-archetype machinery.

- `examples/gol-r/` (R-only GoL, archetype B): R package with testthat, lintr/styler. ~4 units: GoL engine (neighbor counting, birth/death rules), display/IO (terminal grid renderer), main entry (`Rscript` launcher), test suite. Exercises: R toolchain dispatch, renv environment management, R stub generation (`STUB_GENERATORS["r"]`), R quality gates (lintr, no type checker), R test output parsing (`TEST_OUTPUT_PARSERS["r"]`), R compliance scanning, R assembly (`PROJECT_ASSEMBLERS["r"]` producing DESCRIPTION, NAMESPACE).

- `examples/gol-plugin/` (GoL spec generator plugin, archetype C): A Claude Code plugin that spawns 3 implementation agents (naive grid, hashlife, sparse set GoL strategies), benchmarks each against fixed quality criteria (speed, complexity, memory, readability), and produces a ranked evaluation report. Components: 3 agent definitions (`.md`), 1 evaluation agent definition, 1 orchestration skill, 3 commands (`/gol:generate`, `/gol:evaluate`, `/gol:report`), hooks (write authorization during multi-agent execution), plugin manifest. No configurable options — fixed criteria, fixed strategies. Exercises: plugin-specific assembly (`PROJECT_ASSEMBLERS["claude_code_plugin"]`), agent/skill/hook/command file delivery (Section 40.7), MCP dependency handling, plugin manifest validation, structural validation of all plugin artifact types.

**Coverage matrix:**

| Archetype | Test Project | Key Pipeline Paths Exercised |
|---|---|---|
| A (Python) | `examples/game-of-life/` | Python toolchain, conda, pytest, ruff+mypy |
| B (R) | `examples/gol-r/` | R toolchain, renv, testthat, lintr/styler, R dispatch |
| C (Plugin) | `examples/gol-plugin/` | Plugin assembly, agent/skill/hook/command delivery, manifest |
| D (Mixed, Py→R) | `examples/gol-python-r/` | Dual dispatch, bridge tests, two-phase assembly, shared conda |
| D (Mixed, R→Py) | `examples/gol-r-python/` | Same paths, reversed primary/secondary |
| E (Language ext., primary) | Build-produced GoL re-expressions in `examples/` | New language dispatch, toolchain, assembly (E-mode) |
| F (Architectural, primary) | SVP `docs/` | Routing, state, gates, pipeline flow (F-mode) |

**Carry-forward rule:** All test projects are authored once as real specs + blueprints + project contexts, maintained across SVP versions, and delivered as carry-forward artifacts in `examples/`. They are not minimal stubs — they are real projects that exercise real pipeline paths.

**Test project selection:** The human selects which test project to use before each `/svp:oracle` invocation. The oracle does not choose the test project autonomously.

**(NEW IN 2.2) Test project registry and invocation UX.** When the human invokes `/svp:oracle`, the routing script presents the available test projects with a short explanation for each. The list is composed from two sources:

1. **SVP self-build (hardcoded):** Always listed. Uses `docs/` from the delivered repository. Exercises F-mode (machinery testing) — verifies routing, state transitions, gates, and pipeline flow.
2. **Example test projects (auto-discovered):** The routing script scans `examples/` in the delivered repository for directories containing the required artifacts (`project_context.md`, `stakeholder_spec.md`, and blueprint documents). Each valid test project is listed with its directory name and a description from the test project manifest.

The human sees a numbered list:

```
Available test projects for /svp:oracle:

1. SVP Pipeline (docs/) — Machinery testing: verifies routing, state transitions, gates, pipeline flow. [F-mode]
2. GoL Python (examples/game-of-life/) — Product testing: Python toolchain, conda, pytest, ruff+mypy. [E-mode]
3. GoL R (examples/gol-r/) — Product testing: R toolchain, renv, testthat, lintr/styler. [E-mode]
...

Select a test project (number), or ask a question:
```

The human can select a test project by number or ask questions before selecting. The oracle enters dry run with the selected test project.

**Test project manifest (`oracle_manifest.json`).** Each test project directory contains an `oracle_manifest.json` file that provides metadata for the oracle:

```json
{
  "name": "GoL Python",
  "description": "Python Game of Life — exercises Python toolchain dispatch end-to-end.",
  "archetype": "python_project",
  "oracle_mode": "product",
  "languages": ["python"],
  "key_paths": ["Python dispatch", "conda environment", "pytest execution", "ruff+mypy quality gates"],
  "trajectory_config": "oracle_trajectory.json"
}
```

Fields:
- `name`: Human-readable name shown in the test project list.
- `description`: One-line explanation shown in the test project list.
- `archetype`: The project archetype this test project exercises (e.g., `"python_project"`, `"r_project"`, `"mixed"`).
- `oracle_mode`: `"product"` (E-mode — oracle evaluates the built product) or `"machinery"` (F-mode — oracle evaluates pipeline behavior). Informs the oracle's verification targets and trajectory strategy.
- `languages`: Array of languages exercised by this test project.
- `key_paths`: Array of short labels describing the pipeline paths this test project exercises. Displayed to the human for context.
- `trajectory_config`: Filename of the trajectory configuration file in the same directory (default: `oracle_trajectory.json`).

The SVP self-build test project does not have an `oracle_manifest.json` — its metadata is hardcoded in the routing script (name: "SVP Pipeline", mode: "machinery", always available).

**(NEW IN 2.2) Manifest validation.** Test projects in `examples/` that lack `oracle_manifest.json` are still listed but displayed with a warning: "[no manifest — mode and trajectory unknown]". The human can still select them; the oracle uses defaults: `oracle_mode: "product"`, trajectory config: happy-path-only. Test projects with malformed manifests (invalid JSON, missing required `oracle_mode` field) are skipped with an error message.

### 35.7 What `/svp:oracle` Adds to the Codebase

The implementation requires:

- **New agents:** Oracle agent definition(s) for trajectory planning, execution, and diagnostic classification.
- **New orchestration logic:** Routing and state management for oracle sessions, including the constraint that `/svp:bug` is blocked for the human during active oracle sessions but available to the oracle internally.
- **New pipeline state:** State fields to track oracle session status (see Section 35.15).
- **New command:** `/svp:oracle` slash command to initiate an oracle session.
- **New skill:** `/svp:visual-verify` for GUI-based visual verification during E-mode green runs (Section 35.18).

### 35.8 Constraints

- No existing stage (0-5) is modified. **(CHANGED IN 2.2)** The two-pass protocol for E/F archetypes (Section 43) adds routing logic around stage transitions but does not modify the internal behavior of any stage.
- No existing command behavior is modified (except the access constraint on `/svp:bug` during active oracle sessions).
- The oracle reads from the delivered repository for code analysis but all writes target the workspace via `/svp:bug`. Fixes propagate to the delivered repository through `/svp:bug`'s Stage 5 reassembly step, which is part of the normal `/svp:bug` workflow.
- Each invocation is a full restart: the oracle re-walks from scratch every time. The run ledger provides context from previous runs but does not cause the oracle to skip paths.
- At most one discovery is fixed per invocation. A discovery may encompass multiple related bugs or a bug cascading across multiple units, but is bounded by what the agent encounters during its current task.
- **Simulation only (see Section 35.1).** The nested pipeline run produces NO usable deliverable. All artifacts generated by the nested session are disposable verification outputs. The oracle's purpose is to verify pipeline behavior, not to produce a project.
- **Pipeline state isolation.** The oracle MUST NOT modify the main pipeline's state beyond its own oracle-specific fields. Specifically:
  - **The oracle CAN write:** `.svp/oracle_run_ledger.json` (its own ledger); `oracle_session_active`, `oracle_test_project`, `oracle_phase`, `oracle_run_count` in `pipeline_state.json`; diagnostic map files in `.svp/`.
  - **The oracle MUST NOT write:** `stage`, `sub_stage`, or any non-oracle field in `pipeline_state.json`; the main pipeline's conversation ledger or any other pipeline artifacts; any files in the main workspace beyond its own oracle artifacts listed above.
  - The pipeline remains at "Stage 5 complete" throughout the oracle's operation. The oracle operates in a side channel -- it does not advance, modify, or roll back the main pipeline's state machine.

**(NEW IN 2.2)** The oracle's routing follows the same route-level state persistence invariant (Section 3.6, Bug 42 fix). Every in-memory state transition in the oracle's route() function must be persisted to `pipeline_state.json` before returning an action block. This prevents the invisible state rollback pattern where the POST command overwrites in-memory transitions with stale disk state.

### 35.9 Oracle Agent Design

| Property | Value |
|----------|-------|
| Name | Oracle Agent |
| Stage | 7 (post-delivery, SVP-only) |
| Default model | Configured via `pipeline.agent_models.oracle_agent` (see Section 22.1 precedence). Defaults to Opus-class (correctness-critical) |
| Inputs | Run ledger, stakeholder spec, spec history, blueprint (dry run only), bug catalog, regression tests, test project artifacts, nested session files, delivered repo path, assembly_map.json |
| Outputs | Diagnostic map, run ledger entry, exit report |
| Terminal status | `ORACLE_DRY_RUN_COMPLETE`, `ORACLE_ALL_CLEAR`, `ORACLE_FIX_APPLIED`, `ORACLE_HUMAN_ABORT` |
| Interaction | Dual-mode: analytical (dry run), autonomous execution (green run). Run ledger for cross-invocation context. |
| Oracle mode | **(NEW IN 2.2)** E-mode (product testing) or F-mode (machinery testing), determined by the human's test project selection. GoL → E-mode, SVP docs → F-mode. See Section 3.33. |

**Behavioral capabilities.** The oracle must be able to: (1) send arbitrary text input to the nested session via stdio, (2) detect when the nested session presents a gate (by recognizing gate prompt patterns in stdout), (3) send gate responses to advance the nested pipeline, (4) detect when the nested session completes a stage or sub-stage (by monitoring state transitions), and (5) invoke `/svp:bug` in the nested session by acting as the human at all gates in the debug loop. The spec constrains WHAT the oracle must accomplish at each step; the mechanism (parsing strategy, timing, buffering) is a blueprint decision.

The oracle agent follows the **stateless agent principle** (as defined in Section 3.3). Key design properties:

- **Nested session communication:** The oracle drives an inner Claude Code session as a subprocess with bidirectional communication. The oracle is the outer controller; the nested session is the pipeline instance under test. The communication mechanism (stdio piping, IPC, or other) is a blueprint decision.
- **Full read access:** The oracle has full read access to the nested session's files, including `pipeline_state.json`, all source code, generated artifacts, and agent outputs.
- **Full restart every invocation:** The oracle does not carry state between invocations. Each invocation starts fresh. The run ledger is the oracle's memory -- it reads it at startup to understand what happened in previous runs, but it re-plans and re-executes from scratch. The run ledger is context, not a skip list.
- **Stakeholder spec as sole source of truth:** The oracle evaluates pipeline behavior against the stakeholder specification. The stakeholder spec defines what "correct" means. The blueprint is a reference document used during dry run for code analysis, but it is not the correctness standard.
- **Default model:** Configured via `pipeline.agent_models.oracle_agent`. Defaults to Opus-class.
- **Workspace and delivered repo awareness:** The oracle is aware of both the workspace (where it operates) and the delivered repository (a sibling directory, located via `delivered_repo_path` in `pipeline_state.json`). The oracle does NOT write to the delivered repo directly -- changes reach it only through `/svp:bug`'s Stage 5 reassembly.

**(NEW IN 2.2) Dual-mode oracle behavior.** The oracle agent adapts its verification targets and trajectory strategy based on the active mode:
- **E-mode:** The oracle's dry run analyzes the new language's dispatch table entries, toolchain integration, and assembly paths. The green run builds a GoL project in the new language through the nested session. Verification targets focus on language-specific paths: stub generation, quality gates, test execution, assembly, compliance scanning.
- **F-mode:** The oracle's dry run analyzes routing logic, state transition functions, gate dispatch tables, and orchestration code. The green run drives the nested session through a full pipeline rebuild (SVP rebuilding itself). Verification targets focus on machinery: routing path coverage, gate reachability, state machine integrity.
**(CHANGED IN 2.2)** For SVP self-build, the oracle always analyzes the delivered repo copy of pipeline scripts (`svp/scripts/routing.py`, `svp/agents/*.md`, etc.) -- never the main workspace's active `scripts/` (which is SVP 2.1, the builder) or `src/unit_N/` (build scaffolding). The delivered repo contains the actual code that will execute when the delivered SVP is installed as a plugin.

The nested session launched by the oracle uses the DELIVERED SVP's gate vocabulary and dispatch logic -- not the oracle's own. The nested session is a real SVP pipeline instance running the delivered code. Gates in the nested session are handled by the nested session's own `dispatch_gate_response()`. The oracle interacts with these gates via stdio piping, not by calling dispatch functions directly.

### 35.10 Oracle Inputs

The oracle reads the following inputs at the start of each invocation:

1. **Run ledger** (`.svp/oracle_run_ledger.json`): The oracle's own history of previous runs. Compact JSON, appended at each exit. Contains run number, exit reason, trajectory summaries, discoveries, and fix outcomes (see Section 35.13 for format).
2. **Stakeholder specification:** The sole source of truth for evaluating correctness of pipeline behavior.
3. **Spec modification history:** Diffs from `docs/history/` -- the oracle checks if the spec was modified since the last run and re-reads it if so.
4. **Blueprint:** Used during dry run only, for code analysis and understanding the pipeline's intended structure. Not the correctness standard.
5. **Bug catalog / lessons learned:** The oracle maps all previous bugs from the existing bug catalog and lessons learned infrastructure. This informs its risk prioritization.
6. **Regression tests:** Read during planning to understand existing coverage and identify gaps.
7. **Test project artifacts:** The selected test project's `project_context.md`, `stakeholder_spec.md`, and blueprint documents.
7a. **Test project manifest** (`oracle_manifest.json`): The selected test project's manifest file, providing `oracle_mode`, `languages`, `key_paths`, and `trajectory_config`. For SVP self-build, this metadata is hardcoded (no manifest file). The oracle uses `oracle_mode` to determine its verification targets and trajectory strategy. **(NEW IN 2.2)** For test projects in `examples/`, artifacts are read from `examples/<project_name>/` (e.g., `examples/<project_name>/project_context.md`, `examples/<project_name>/stakeholder_spec.md`, and blueprint documents in the same directory). For SVP self-build, artifacts are read from `docs/` (i.e., `docs/project_context.md`, `docs/stakeholder_spec.md`, `docs/blueprint_prose.md`, `docs/blueprint_contracts.md`).
8. **Nested session's `pipeline_state.json`:** Read during green run for state transition verification. The oracle has full file access to the nested session.
9. **Delivered repository path:** The oracle reads `delivered_repo_path` from `pipeline_state.json` to locate the delivered repository (a sibling directory of the workspace, not inside it). The oracle needs this to verify that fixes propagated correctly after `/svp:bug` completes its Stage 5 reassembly.

### 35.11 Verification Targets (CHANGED IN 2.2)

During the green run, the oracle verifies different targets depending on mode. Targets 1-7 are primarily F-mode (machinery testing) but some apply to both modes. Targets 8-9 are E-mode specific.

**F-mode targets (machinery testing) — also applicable to both modes where noted:**

1. **State transitions:** Compare expected state in `pipeline_state.json` against actual state after each pipeline operation. Verify that routing scripts produce the correct next state. *(F-mode primary; E-mode monitors but does not prioritize.)*
2. **Dispatch paths:** Verify that the correct handler is invoked for each gate response (e.g., APPROVE routes to the next stage, REVISE routes to the revision workflow). *(F-mode primary.)*
3. **Gate prompts:** Verify that gate prompts are well-formed and present the correct options to the human. *(F-mode primary.)*
4. **Agent terminal status lines:** Verify that agent outputs contain the expected terminal status vocabulary and that these are parsed correctly by the orchestration layer. *(Both modes.)*
5. **Delivered artifacts:** Verify that expected artifacts exist with expected content after each stage completes. *(Both modes.)*
6. **Test suites:** Verify that test suites pass when run (unit tests, integration tests, regression tests). *(Both modes.)*
7. **Fix propagation (NEW IN 2.2):** The oracle uses `assembly_map.json` for path correlation when verifying fix propagation. After `/svp:bug` completes and Stage 5 reassembles, the oracle reads the assembly map to identify which repo files correspond to the fixed workspace files, then performs content comparison to confirm the fix propagated correctly. *(Both modes.)*

**(NEW IN 2.2) E-mode targets (product testing):**

8. **Product correctness (E-mode):** Verify the built GoL project's test suite passes. Verify assembly produced valid language-specific artifacts (correct file types, directory structure, language-specific manifest entries). Verify the project can be launched and run.
9. **Visual verification (E-mode, optional):** For GUI-based test projects, invoke `/svp:visual-verify` (Section 35.18) and check that the visual output matches spec requirements (e.g., GoL grid renders, scroll bar functions, generations advance correctly).

### 35.12 Diagnostic Map

The oracle maintains a diagnostic map throughout the green run. The diagnostic map is stored at `.svp/oracle_diagnostic_map.json` in the workspace, in JSON format. The diagnostic map is the oracle's structured record of everything it observes.

- **Entry points:** Diagnostic entries are recorded at both **human gates** (where the pipeline presents choices) and **state transitions** (where the pipeline changes state).
- **Hybrid capture:** The oracle logs everything it observes, annotating each entry with a classification: `PASS`, `FAIL`, or `WARN`.
- **Entry structure:** Each diagnostic entry contains:
  - **Event identifier:** A unique label for the observation point (e.g., `stage3.unit_foo.gate_a`, `stage5.reassembly.state_transition`).
  - **Classification:** `PASS`, `FAIL`, or `WARN`.
  - **Observation:** What the oracle actually observed (the concrete behavior).
  - **Expected behavior:** What the stakeholder spec says should happen.
  - **Affected artifact:** The file, state field, or output affected by this observation.

### 35.13 Context Management and Run Ledger

#### Run Ledger Format

The run ledger is a compact JSON file located at `.svp/oracle_run_ledger.json` in the workspace (working directory), with one entry per oracle invocation. Each entry contains:

- `run_number`: Sequential integer.
- `exit_reason`: One of `all_clear`, `fix_applied`, `human_abort`.
- `abort_phase`: (If applicable) `gate_a` or `gate_b`.
- `trajectory_summary`: Compact description of the planned trajectory.
- `discoveries`: List of issues found (root causes, classifications, affected units).
- `fix_targets`: Units/files targeted for repair.
- `root_causes_found`: Root causes identified in this run.
- `root_causes_resolved`: Root causes fixed and verified in this run.

#### Summarization

Summarization happens at two points:

1. **After bug fix (before exit):** The oracle summarizes the discovery, fix, and verification outcome.
2. **At end of path:** If the oracle completes a trajectory path without finding bugs, it summarizes the path's results.

The oracle does not maintain a separate Stage 7-specific lessons learned file. It uses the existing bug catalog and lessons learned infrastructure established in earlier stages.

#### Run History at Gate A

At Gate A (Phase 2), the oracle reads the run ledger and summarizes previous run history to the human. This gives the human context on what has already been tested, what was found, and what was fixed before approving the next trajectory.

### 35.14 Failure, Abandonment, and Abort Handling (CHANGED IN 2.2)

**(NEW IN 2.2) Scope clarification.** This section covers failures DURING oracle execution (dry run crashes, green run bugs, human aborts at Gate A or Gate B). Failures during Pass 1 or Pass 2 construction are NOT oracle failures — they are handled by the orchestrator break-glass protocol (Section 43.9). The oracle only runs on a clean deliverable — Pass 2's Stage 5 must have completed successfully before `/svp:oracle` is available.

#### Safety Invariant

**Stage 7 never damages the Stage 5 deliverable.** This is an explicit invariant. The oracle reads from the delivered repository for code analysis but all writes target the workspace via `/svp:bug`; changes reach the delivered repository only through `/svp:bug`'s Stage 5 reassembly, which has its own quality gates.

#### Safe Abandonment

The oracle session is **always safely abandonable** at any point. If the oracle session is interrupted, crashes, or is explicitly abandoned:

- Partial results are preserved on disk (run ledger, diagnostic map) but are not authoritative.
- Pipeline state rolls back to "Stage 7 available but not active."
- The delivered repository is untouched.
- No corruption of pipeline state or workspace.

#### Abort Points

The human can abort at two defined points:

1. **Gate A (before green run execution):** The human reviews the trajectory plan and decides not to proceed.
2. **Gate B (before bug fix execution):** The human reviews the fix plan and decides not to proceed with the fix.

#### Abort State Preservation

When the human aborts, the following is preserved in the run ledger:

- `exit_reason`: `human_abort`
- `abort_phase`: `gate_a` or `gate_b`
- `trajectory_summary`: The planned trajectory (what the oracle intended to do)
- `discoveries`: (If abort at Gate B) The discovery that prompted the fix plan
- `partial_diagnostic_map_path`: Path to the partial diagnostic map on disk (if any observations were recorded)

#### Abort Context in Future Runs

On the next invocation, the oracle reads the abort history from the run ledger. It knows what was planned and (if at Gate B) what was found in the aborted run. The full restart principle is maintained -- the oracle re-walks from scratch -- but it has this context to inform its planning.

### 35.15 Pipeline State Extensions

Oracle session state is tracked via **flat fields** in `pipeline_state.json`, consistent with the Stage 6 pattern established in SVP 2.1.

**(CHANGED IN 2.2)** Oracle state schema (closed set, per Section 22.4 preamble rule):

| Field | Type | Default | Valid Values |
|-------|------|---------|-------------|
| `oracle_session_active` | bool | `false` | `true`, `false` |
| `oracle_test_project` | string or null | `null` | valid test project path or `null` |
| `oracle_phase` | string or null | `null` | `"dry_run"`, `"gate_a"`, `"green_run"`, `"gate_b"`, `"exit"`, `null` |
| `oracle_run_count` | int | `0` | non-negative integer |
| `oracle_nested_session_path` | string or null | `null` | valid file path or `null` |

**Oracle session lifecycle functions (NEW IN 2.2 -- Bug S3-15).** The oracle session follows the same structured lifecycle pattern as debug sessions. `enter_oracle_session(state, test_project)` validates preconditions (no active session) and initializes the session with `oracle_phase="dry_run"`. `complete_oracle_session(state, exit_reason)` deactivates after success. `abandon_oracle_session(state)` deactivates after human abort. Direct field assignment of `oracle_session_active` is prohibited -- all activation must go through transition functions.

### 35.16 Cleanup and Environment Hygiene

**(NEW IN 2.2)** The nested session workspace is created in the system's temporary directory (e.g., `/tmp/svp-oracle-XXXX/` or equivalent platform-appropriate temp path) -- NOT inside the main workspace and NOT as a sibling directory. This prevents hook conflicts, `.svp/` namespace collisions, and confusion between the nested session's files and the main workspace/repo files. The exact path is recorded in `pipeline_state.json` as `oracle_nested_session_path` for cleanup purposes.

#### On Exit (All Exit Paths)

On exit -- whether the exit path is all-clear, after-fix, human abort, or crash recovery -- the oracle cleans up the nested session's workspace. **(CHANGED IN 2.2)** In E-mode, before cleanup, the oracle copies the built GoL project to a sibling directory of the delivered repo (same parent directory, named `oracle-<test-project-name>/`). This copy persists after cleanup so the human can inspect and run it. In F-mode, no project artifacts are preserved — the generated code is disposable. After the E-mode copy (if applicable), the nested session workspace is removed entirely, including the simulation directory, any repositories it generated, and all temporary files created by the nested pipeline run.

The **only** artifacts that persist after cleanup are:

- The run ledger (`.svp/oracle_run_ledger.json`).
- The diagnostic map (if produced).
- The oracle-specific fields in `pipeline_state.json` (`oracle_session_active`, `oracle_test_project`, `oracle_phase`, `oracle_run_count`).
- The E-mode GoL project copy (if E-mode, at `oracle-<test-project-name>/` sibling to delivered repo).

The main workspace is left in exactly the state it was in before the oracle was invoked, plus the updated run ledger and diagnostic map.

#### On Startup

Before beginning any work, the oracle checks for a clean environment. **Stale detection:** A stale nested session exists when `oracle_nested_session_path` in `pipeline_state.json` is non-null AND the referenced directory exists on disk. If remnants of a previous oracle run exist (e.g., a stale nested session workspace that was not cleaned up due to a crash), the oracle cleans them up first and logs the cleanup event in the run ledger as a housekeeping entry.

The oracle does not begin its dry run until the environment is verified clean.

#### Post-Fix Nested Session Recreation (NEW IN 2.2)

After a fix is applied and Stage 5 reassembly completes, the delivered SVP plugin has changed. The oracle MUST tear down the existing nested session and create a fresh one using the updated delivered plugin before performing behavioral verification. The stale nested session was launched with pre-fix code and cannot be reused for verification. The teardown and recreation is part of the fix verification cycle and is logged in the diagnostic map.

### 35.17 Nested Session Bootstrap Sequence (NEW IN 2.2, CHANGED IN 2.2)

**(CHANGED IN 2.2) Dual-purpose mechanism.** This nested session bootstrap mechanism is used for TWO distinct purposes:

1. **Pass 2 (production build):** The orchestrator drives a nested session using this mechanism to produce the real deliverable (Section 43.8). Pass 2's nested session output IS the delivered product — artifacts are kept.
2. **Oracle (verification):** The oracle drives a nested session using this mechanism to verify pipeline behavior (simulation-only constraint, Section 3.22). Oracle's nested session output is disposable.

The bootstrap mechanism (plugin path, version isolation, stdio piping, CLAUDE.md generation) is identical; the purposes and workspace locations are distinct. Both use the same `svp restore --plugin-path` invocation, the same plugin version isolation, and the same stdio piping. The differences: (1) Pass 2 creates a sibling directory to the main workspace (the output is the deliverable and must persist); the oracle creates a temp directory (the output is disposable). (2) What happens to the output — Pass 2's is kept, oracle's is discarded.

When the oracle creates a nested session for the green run (or when the orchestrator creates a nested session for Pass 2):

1. **Create workspace directory.** For oracle: a new directory in the system temp area (e.g., `/tmp/svp-oracle-XXXX/`), path recorded in `pipeline_state.json` as `oracle_nested_session_path`. For Pass 2: a sibling directory to the main workspace, path recorded as `pass2_nested_session_path`. See `svp restore` definition in Section 6.1.1 for restore semantics and CLI arguments.

2. **Run `svp restore` with plugin path.** The oracle invokes `svp restore` in the nested workspace with the test project artifacts (spec, blueprint, context, profile). **(NEW IN 2.2)** `svp restore` gains a `--plugin-path` argument that specifies the SVP plugin directory to use. The oracle passes the delivered SVP plugin path (resolved from `delivered_repo_path` -- the plugin directory is at `<delivered_repo>/svp/`). The oracle resolves artifact paths from the test project directory: for SVP self-build, artifacts are in the delivered repo's `docs/` directory; for `examples/` test projects, artifacts are in `examples/<project_name>/`. The oracle passes these resolved paths as `--spec`, `--blueprint-dir`, `--context`, and `--profile` arguments to `svp restore`.

3. **Plugin version isolation.** The `--plugin-path` argument configures plugin isolation in the nested session's environment, ensuring the nested session uses ONLY the delivered SVP plugin — not the builder SVP that is currently running. The builder SVP is invisible to the nested session. The isolation mechanism (environment variable, configuration file, or other) is a blueprint decision.

4. **CLAUDE.md generation.** The `svp restore` launcher generates the nested workspace's CLAUDE.md to point to the delivered SVP plugin, using the standard CLAUDE.md template (Unit 27) with the plugin path from `--plugin-path`.

5. **Launch nested session.** The oracle launches `claude` as a subprocess in the nested workspace directory with plugin isolation configured. The oracle communicates bidirectionally with the nested session.

6. **Verification.** Before beginning the green run trajectory, the oracle verifies the nested session is using the delivered plugin (not the builder) by checking the plugin version in the nested session's CLAUDE.md.

### 35.18 Visual Verification Skill (NEW IN 2.2)

`/svp:visual-verify` provides a visual verification capability for GUI-based test projects during E-mode green runs. The system can launch a target program, capture visual output (screenshots) at defined intervals or interaction points, and return captured images for evaluation by the oracle or human. The packaging mechanism (Claude Code skill, standalone script, or other) is a blueprint decision.

**Usage by the oracle.** During E-mode green run, after the GoL test suite passes (primary verification), the oracle may invoke `/svp:visual-verify` on GUI-based test projects (e.g., GoL with tkinter GUI and scroll bar). The oracle inspects the returned screenshots to check: grid renders correctly, cells follow GoL rules (known patterns like blinkers and gliders behave as expected), scroll bar functions, generation counter increments. Any visual anomaly is flagged as a potential discovery.

**Usage by the human.** The human can invoke `/svp:visual-verify` independently to capture their own screenshots of the persisted GoL project. This supports the human's ability to inspect and run the E-mode product after the oracle exits.

**Supplementary, not authoritative.** Visual verification is a best-effort sanity check — LLM visual inspection is probabilistic and may miss subtle rendering bugs. The test suite is the authoritative verification. Screenshots are a bonus layer of confidence.

---

## 36. Non-Functional Requirements for `/svp:oracle` (NEW IN 2.2)

### NFR-5: Performance

- Oracle dry run (code analysis) should complete without requiring human intervention beyond the initial invocation.
- Oracle green run executes against a real pipeline instance and therefore takes as long as a real pipeline execution. No artificial time constraints.

### NFR-6: Reliability

- Oracle session failures (crashes, context exhaustion) must not corrupt pipeline state or the delivered repository.
- The oracle must be able to resume from scratch on a fresh invocation (no dependency on previous session state).
- Stage 7 never damages the Stage 5 deliverable (see Section 35.14).

### NFR-7: Usability

- The human must be able to understand the trajectory plan without reading source code.
- Diagnostic classifications (root cause / possibly downstream / clean) must be explained in plain language.
- The exit report must clearly state what was tested, what passed, and what was fixed (if anything).
- At Gate A, the oracle must summarize run history from previous invocations so the human has context.

### NFR-8: Compatibility

- The regression test suite must pass all carry-forward tests from SVP 2.1 plus all tests newly authored for SVP 2.2. The complete inventory is enumerated in Section 6.8. Failure mode entries are in Section 24.

---

## 37. Assumptions for `/svp:oracle` (NEW IN 2.2)

1. The delivered SVP pipeline (the output of Stage 5) is a functional Claude Code plugin that can be invoked programmatically by the oracle agent via stdio piping.
2. The oracle agent has sufficient context window to analyze the full pipeline source code during the dry run phase.
3. Test projects are available and correctly configured before oracle invocation (each with project_context, stakeholder_spec, and blueprint docs).
4. The human understands that each `/svp:oracle` invocation fixes at most one discovery (which may span multiple units), and multiple invocations may be needed to clear all issues.
5. The human selects the test project before each invocation.
6. SVP self-build test project is always available because it uses the pipeline's own docs/.

---

## 38. Scope Boundaries for `/svp:oracle` (NEW IN 2.2)

### In Scope

- `/svp:oracle` command and its four-phase execution model.
- Oracle agent definition(s) with trajectory planning and diagnostic classification capabilities.
- Risk-prioritized trajectory strategy, configurable per test project.
- Internal `/svp:bug` integration (oracle can call bug workflow during green run).
- Gate A (trajectory plan review) and Gate B (fix plan review) as human decision points.
- Access control: `/svp:bug` blocked for human during active oracle session.
- Pipeline state extensions for oracle session tracking (flat fields).
- Support for multiple test projects with defined artifact requirements.
- Run ledger for cross-invocation context.
- Diagnostic map with hybrid capture.
- Fix verification after `/svp:bug` completes.
- Safe abandonment and abort handling.

### Out of Scope

- Modification of any existing stage (0-5).
- Modification of `/svp:bug` behavior (only access control during oracle sessions is new).
- Automated scheduling of oracle runs (always human-initiated).
- Parallel oracle sessions (one at a time).
- General-purpose acceptance testing for arbitrary projects built by SVP (oracle is for SVP itself only).
- New test project creation tooling (test projects are manually prepared).
- **Production deliverables from oracle runs.** The nested pipeline session produces simulation artifacts only. No oracle-generated repository, project, or artifact is a production deliverable. The oracle exists to verify pipeline behavior, not to produce usable outputs.

---

## 39. Acceptance Criteria for `/svp:oracle` (NEW IN 2.2)

### AC-1: Oracle Invocation

Given the pipeline is at Stage 5 (delivered), when the human runs `/svp:oracle`, then the human is prompted to select a test project, and an oracle session begins with the dry run phase.

### AC-2: Dry Run Produces Trajectory Plan

Given an active oracle session in the dry run phase, when the oracle analyzes the pipeline code, then it produces a structured trajectory plan with risk prioritization appropriate to the selected test project's configuration.

### AC-3: Human Gate A (Review Plan)

Given a completed dry run with a trajectory plan, when the plan is presented to the human, then the oracle also summarizes run history from previous invocations (if any). The oracle waits for human approval before proceeding to the green run. The human can request modifications to the plan or abort. If the human aborts, the oracle logs the abort to the run ledger and exits.

### AC-4: Green Run Executes Trajectory

Given human approval of the trajectory plan, when the oracle executes the green run, then it drives the pipeline end-to-end using the selected test project, classifies each step as root cause, possibly downstream, or clean, and records diagnostic entries at each observation point.

### AC-5: Human Gate B (Fix Plan Review)

Given the oracle discovers a bug during the green run, when it prepares a fix plan, then it presents the plan to the human at Gate B. The human and oracle decide together whether to proceed. The human can abort at Gate B. If the human aborts, the oracle logs the discovery and planned fix to the run ledger and exits.

### AC-6: At Most One Discovery Fixed Per Invocation

Given the oracle and human approve a fix at Gate B, when the oracle calls `/svp:bug` internally, then the oracle plans a comprehensive fix using its dry-run code knowledge -- covering all units affected by that discovery -- and proceeds with at most one discovery per invocation. A discovery is bounded by what the agent encounters during normal trajectory execution; it does not hunt for unrelated issues.

### AC-7: Fix Verification

Given `/svp:bug` completes a fix, when the oracle re-tests the affected behavior, then it verifies the fix resolved the issue. If the fix did not resolve the issue, the oracle calls `/svp:bug` again. After verification: the oracle produces a full report, logs the outcome, and exits.

### AC-8: All-Clear Exit

Given the oracle completes the entire trajectory without discovering bugs, when the green run finishes, then the oracle reports all-clear and exits.

### AC-9: `/svp:bug` Blocked During Oracle Session

Given an active `/svp:oracle` session, when the human attempts to invoke `/svp:bug`, then the command is rejected with an explanation that `/svp:bug` is unavailable during an active oracle session.

### AC-10: Oracle Can Call `/svp:bug` Internally

Given the oracle discovers a bug during the green run and the human approves the fix at Gate B, when the oracle proceeds, then it invokes the `/svp:bug` workflow internally without additional human initiation.

### AC-11: Self-Contained Sessions with Run Ledger

Given a completed `/svp:oracle` session, when the human invokes `/svp:oracle` again, then a completely fresh session begins. The oracle reads the run ledger for context but re-plans and re-executes from scratch. The run ledger is context, not a skip list.

### AC-12: No Baseline Regression

Given SVP 2.2 with all new features, when the full regression test suite is executed, then all carry-forward tests from SVP 2.1 and all SVP 2.2 regression tests pass. The complete test inventory is in Section 6.8.

### AC-13: Existing Stage Integrity

Given SVP 2.2, when Stages 0-5 are executed for any project, then behavior is identical to SVP 2.1. No stage logic is modified.

### AC-14: Test Project Support

Given a properly configured test project (with project_context, stakeholder_spec, and blueprint docs), when the oracle is invoked with that test project selected, then it can analyze and execute against that project's pipeline instance.

### AC-15: SVP Self-Build Always Available

Given the pipeline has been delivered, when the human invokes `/svp:oracle`, then the SVP self-build test project is always available as an option (because it uses the pipeline's own docs/).

### AC-16: Archetype Coverage (NEW IN 2.2)

Given a test project exists for each supported archetype (A, B, C, D, E/F), when the oracle is invoked with each test project, then it exercises the pipeline paths specific to that archetype — including language-specific dispatch, archetype-specific assembly, and archetype-specific structural validation.

### AC-17: R Archetype Pipeline Paths (NEW IN 2.2)

Given a test project for archetype B (R), when the oracle drives the nested session through Stage 3, then R-specific dispatch paths are exercised: R stub generation, R quality gates (lintr, no type checker), R test output parsing (testthat format), R compliance scanning.

### AC-18: Plugin Archetype Pipeline Paths (NEW IN 2.2)

Given a test project for archetype C (plugin), when the oracle drives the nested session through Stage 5, then plugin-specific assembly is exercised: agent definition delivery, skill file delivery, hook config delivery, command registration, plugin manifest validation.

### AC-19: Safe Abandonment

Given an active oracle session, when the session is interrupted or the human aborts at any point, then pipeline state rolls back to "Stage 7 available but not active," partial results are preserved on disk but are not authoritative, and the delivered repository is untouched.

### AC-20: Diagnostic Map Produced

Given the oracle executes a green run, when it observes pipeline behavior at human gates and state transitions, then it records diagnostic entries with event identifier, classification (PASS/FAIL/WARN), observation, expected behavior, and affected artifact.

### AC-21: Abort Context Preserved

Given the human aborts at Gate A or Gate B, when the oracle exits, then the run ledger contains the abort reason, abort phase, trajectory plan, discoveries (if at Gate B), and partial diagnostic map path. On the next invocation, the oracle reads this abort history to inform its planning.

### AC-22: Stage 5 Deliverable Invariant

Given any oracle session (including crashes, aborts, and fix cycles), the Stage 5 deliverable is never damaged. Changes reach the delivered repository only through `/svp:bug`'s Stage 5 reassembly with its own quality gates.

### AC-23: Nested Session Architecture

Given the oracle is executing a green run, when it drives the pipeline under test, then it does so via stdio piping to an inner Claude Code session launched as a subprocess, with full read access to the nested session's files.

### AC-24: Simulation-Only Constraint

Given an `/svp:oracle` session completes (by any exit path: all-clear, after fix, or human abort), the nested pipeline session's artifacts (workspace, delivered repository, generated code, test outputs) are treated as disposable verification outputs. No oracle-generated artifact is promoted to production status, delivered to any consumer, or treated as a usable project deliverable. The oracle verifies pipeline behavior; it does not produce deliverables.

### AC-25: Clean Environment on Exit

Given an oracle session completes (by any exit path: all-clear, after-fix, human abort, or crash recovery), when the oracle exits, then the nested session workspace is fully cleaned up. Only the run ledger (`.svp/oracle_run_ledger.json`), diagnostic map, and oracle pipeline state fields (`oracle_session_active`, `oracle_test_project`, `oracle_phase`, `oracle_run_count`) persist. The main workspace is in the same state as before the oracle was invoked.

### AC-26: Clean Environment on Startup

Given the oracle is invoked, when it starts, then it checks for remnants of previous oracle runs. If stale artifacts exist (e.g., a nested session workspace not cleaned up due to a prior crash), the oracle cleans them up and logs the event in the run ledger as a housekeeping entry before proceeding with its dry run.

### AC-27: Pipeline State Isolation

Given an active oracle session, the oracle never modifies `stage`, `sub_stage`, or any non-oracle field in `pipeline_state.json`. The main pipeline state machine is unaffected by oracle operations. The pipeline remains at "Stage 5 complete" throughout the oracle's operation.

### AC-28: Assembly Map Produced (NEW IN 2.2)

Given Stage 5 assembly completes, then `.svp/assembly_map.json` exists and contains a bidirectional mapping between all workspace source paths and their corresponding delivered repo paths.

### AC-29: Triage Agent Uses Assembly Map (NEW IN 2.2)

Given a `/svp:bug` triage, when the triage agent receives its task prompt, then `assembly_map.json` is included as an input for path correlation between workspace and delivered repo.

### AC-30: Post-Fix-In-Place Validation (NEW IN 2.2)

Given a FIX IN PLACE completion, when the pipeline proceeds, then structural validation runs against the delivered repo and workspace/repo file consistency is verified using `assembly_map.json`.

### AC-31: Nested Session in Temp Directory (NEW IN 2.2)

Given the oracle creates a nested session, then the nested session workspace is in the system temp directory, NOT inside the main workspace or as a sibling. The path is recorded in `pipeline_state.json` as `oracle_nested_session_path`.

### AC-32: Post-Fix Nested Session Recreation (NEW IN 2.2)

Given a fix is applied during an oracle green run, when Stage 5 reassembly completes, then the oracle tears down the stale nested session and creates a fresh one with the updated delivered plugin before performing behavioral verification.

### AC-33: is_svp_build Gate (NEW IN 2.2)

Given a delivered project where `is_svp_build` is false in the project profile, when the human attempts to invoke `/svp:oracle`, then the command is rejected with an explanation that oracle testing is only available for SVP builds.

### AC-34: Deterministic Import Adaptation (NEW IN 2.2)

Given carry-forward regression tests with imports referencing old module names, when `adapt_regression_tests.py` runs with `regression_test_import_map.json`, then imports are updated to reference the correct new module names. The script handles `from X import Y`, `import X`, `@patch("X.Y")`, and `patch("X.Y")` forms.

### AC-35: Agent Adaptation Fallback (NEW IN 2.2)

Given regression tests that still fail after deterministic adaptation, when the Regression Test Adaptation Agent is invoked, then it diagnoses each failure as import-fixable, patch-target-fixable, or behavioral-change, and rewrites fixable tests. Fixable tests are re-run to verify the fix. Unfixable tests (behavioral changes) are reported to the human.

### AC-36: Behavioral Change Human Review (NEW IN 2.2)

Given the adaptation agent identifies behavioral changes in regression tests, when it reports them at Gate 4.3 (`gate_4_3_adaptation_review`), then the human reviews each flagged test and decides to accept the adaptations, modify the test, or remove the test.

### AC-37: Stage 2 Agents Receive Lessons Learned (Bug 84 Fix) (NEW IN 2.2)

Given Stage 2 agent invocations, when the blueprint author, blueprint checker, or blueprint reviewer task prompt is assembled, then the full lessons learned document (`references/svp_2_1_lessons_learned.md`) is included as an input.

### AC-105: Orchestrator Decision Ledger (NEW IN 2.2)

Given a Stage 1 Socratic dialog, then the orchestrator maintains a numbered decision ledger tracking every architectural choice made during the dialog.

### AC-106: Spec Draft Verification (NEW IN 2.2)

Given a spec draft from the stakeholder dialog agent, when the orchestrator receives it, then the orchestrator runs a verification checklist mapping every decision in the ledger to the spec. Failures are identified and the agent is instructed to revise before the human sees the draft.

### AC-107: Feature Parity Check (NEW IN 2.2)

Given a spec that builds on a previous version, when the full spec is assembled, then the orchestrator performs a category-by-category comparison (sections, gates, agents, invariants, status lines, state fields, commands, failure modes) and reports any items present in the baseline but missing in the new spec.

### AC-38: Language Registry Validation (NEW IN 2.2)

Given the language registry at import time, then validation runs and confirms all required keys are present for every entry (Python, R, Stan). Any missing key raises a RuntimeError with a descriptive checklist of violations.

### AC-39: Python Registry Entry Complete (NEW IN 2.2)

Given the Python entry in the language registry, then it has all required keys, all six dispatch table entries, and produces behaviorally equivalent output to SVP 2.1 for Python-only projects.

### AC-40: R Registry Entry Complete (NEW IN 2.2)

Given the R entry in the language registry, then it has all required keys, all six dispatch table entries (signature parser, stub generator, test output parser, quality runner, project assembler, compliance scanner), and the R-specific toolchain file (`r_renv_testthat.json`) exists.

### AC-41: Stan Component Entry (NEW IN 2.2)

Given the Stan entry in the language registry, then `is_component_only` is true, `compatible_hosts` lists R and Python, and the entry has the dispatch entries appropriate for a component language (quality runner for syntax checking, stub generator for model templates).

### AC-42: Dispatch Exhaustiveness (NEW IN 2.2)

Given the language registry with N full-language entries, then each of the six dispatch tables has exactly N entries, one per registered full language. The structural exhaustiveness test and import-time validation both confirm this.

### AC-43: Three-Layer Separation (NEW IN 2.2)

Given the SVP 2.2 codebase, then no function reads pipeline quality settings from the profile, and no function reads delivery quality settings from the toolchain. A structural regression test enforces this by AST-scanning import paths.

### AC-44: Profile Backward Compatibility (NEW IN 2.2)

Given an SVP 2.1-format profile (flat delivery/quality sections), when `load_profile` reads it, then it auto-migrates to language-keyed format with `language.primary = "python"` and wraps delivery/quality under a `"python"` key.

### AC-45: Setup Agent Area 0 Fast Path (NEW IN 2.2)

Given a new project where the human selects Python and same-as-pipeline tools, when Area 0 completes, then the profile has language-keyed sections matching pipeline defaults, and no more than two questions were asked.

### AC-46: Setup Agent Area 0 R Path (NEW IN 2.2)

Given a new project where the human selects R as primary language, when Area 0 completes, then the profile has R-specific delivery and quality sections, the R toolchain file is selected, and any declared components (Stan, Python) have their communication mechanisms recorded.

### AC-47: Setup Agent Area 0 Mixed Path (NEW IN 2.2)

Given a new project where the human selects Option D (mixed-language), when the Option D dialog completes, then the profile has: `archetype: "mixed"`, `language.primary` set to the owning language, `language.secondary` set to the embedded language, `language.communication` with the correct bridge library (`rpy2` for Python→R, `reticulate` for R→Python), and both `delivery` and `quality` sections for both languages with conda-only defaults per Section 40.6.2.

### AC-47b: Setup Agent Area 0 Dynamic Path [DEFERRED] (NEW IN 2.2)

This acceptance criterion is deferred to dynamic language extension (the Socratic dialog for configuring languages beyond Python and R — see Section 3.28). In SVP 2.2, the dynamic registry construction mechanism is not yet active. When the human requests adding a language other than Python or R, the agent explains: "Dynamic language construction will be available in a future SVP release. For now, SVP supports Python, R, and mixed Python+R projects (Options A, B, C, D)."

### AC-48: Per-Unit Language Dispatch in Stage 3 (NEW IN 2.2)

Given a multi-language project in Stage 3, when a unit tagged with language X is processed, then the stub generator, test framework, and quality gates all dispatch through the correct language-specific entries for X.

### AC-49: Language Context in Agent Prompts (NEW IN 2.2)

Given any Stage 3 agent invocation, when the task prompt is assembled, then it includes a LANGUAGE_CONTEXT section with the unit's language, agent-specific guidance from the registry, and the relevant test/quality tool names.

### AC-50: Language-Dispatch Assembly (NEW IN 2.2)

Given Stage 5 assembly for a project with primary language X, when the git repo agent assembles the delivered repository, then it dispatches through `PROJECT_ASSEMBLERS[X]` and generates language-appropriate project structure (pyproject.toml for Python, DESCRIPTION for R, etc.).

### AC-51: Multi-Language Profile (NEW IN 2.2)

Given a project declaring R as primary and Python + Stan as components, when the profile is validated, then language-keyed delivery and quality sections exist for R and Python, communication mechanisms are recorded, and Stan's host interface is specified. For the `"mixed"` archetype specifically, `language.secondary` is present and validated (must be a non-component registry language different from `language.primary`); for all other archetypes, `language.secondary` is absent.

### AC-52: Behavioral Equivalence with SVP 2.1 (NEW IN 2.2)

Given SVP 2.2 building a Python-only project, then every pipeline behavior (routing, dispatch, gates, quality gates, assembly, delivery) is identical to SVP 2.1. All SVP 2.1 regression tests pass with adapted imports only.

### AC-53: Hard Stop Protocol (NEW IN 2.2)

Given an SVP N bug that prevents SVP N+1 from building, when a hard stop is declared, then the protocol from Section 41 is followed: save artifacts, produce bug analysis, fix SVP N, reload, restart from checkpoint.

### AC-54: 29-Unit DAG Integrity (NEW IN 2.2)

Given the 29-unit dependency DAG (Section 42.2), then all dependencies point backward (no forward edges), the topological build order is valid, and no circular dependencies exist.

### AC-55: Stub Extraction Contract (NEW IN 2.2)

Given a blueprint with Tier 2 signature blocks, when the signature parser for the unit's language processes them, then every signature block parses successfully. Parse failures are alignment errors caught by the blueprint checker.

### AC-56: Dynamic Language Toolchain Generation [DEFERRED] (NEW IN 2.2)

This acceptance criterion is deferred to the `language_extension` archetype (Option E). No dynamically configured languages can be created in SVP 2.2.

### AC-57: Plugin Project Type Recognition (NEW IN 2.2)

Given a new project where the human selects "Claude Code plugin" as archetype, when setup completes, then the profile has `archetype: "claude_code_plugin"` and all subsequent stages handle mixed artifact types (Python + markdown + bash + JSON).

### AC-58: Plugin Stage 3 Mixed Artifacts (NEW IN 2.2)

Given a Claude Code plugin project in Stage 3, when a markdown unit (agent definition) is processed, then the stub generator produces a markdown template, the test agent writes structural validation tests, and quality gates perform format checking (not ruff/mypy).

### AC-59: Plugin Stage 5 Assembly (NEW IN 2.2)

Given a Claude Code plugin project at Stage 5, when assembly runs, then the delivered repo has proper plugin directory structure (`.claude-plugin/plugin.json`, `agents/`, `commands/`, `hooks/`, `skills/`, `scripts/`), marketplace manifest at repo root, and passes plugin installability check.

### AC-60: Plugin Gate C Validation (NEW IN 2.2)

Given a Claude Code plugin project at Gate C, then plugin manifest schema, marketplace manifest, agent definition format, hook syntax, and command format are all validated. Failures are reported as Gate C issues.

### AC-61: SVP Self-Build Archetype Derivation (NEW IN 2.2)

Given archetype `"svp_language_extension"` or `"svp_architectural"`, then `is_svp_build` is derived as `true` and `self_build_scope` is derived from the archetype. No separate detection or scope question is needed.

### AC-62: Pre-Blueprint Checklists Generated (NEW IN 2.2)

Given the stakeholder spec is approved at Gate 1.2, when the Checklist Generation Agent runs, then it produces two checklist files (`.svp/blueprint_author_checklist.md` and `.svp/alignment_checker_checklist.md`) derived from the approved spec, lessons learned, and regression test inventory.

### AC-63: Blueprint Author Receives Checklist (NEW IN 2.2)

Given Stage 2 begins, when the blueprint author agent's task prompt is assembled, then `.svp/blueprint_author_checklist.md` is included as an input.

### AC-64: Alignment Checker Receives Checklist (NEW IN 2.2)

Given the blueprint alignment check runs, when the checker agent's task prompt is assembled, then `.svp/alignment_checker_checklist.md` is included as an input.

### AC-65: Lesson Learned Review in Checklists (NEW IN 2.2)

Given both checklists, then each contains a mandatory final item requiring review of all lesson learned bugs and regression tests, including generalization of ungeneralized bugs into preventable patterns.

### AC-66: Orchestrator Pipeline Fidelity (NEW IN 2.2)

Given any pipeline stage, when the orchestrator attempts to write to pipeline_state.json via the Write tool, then the PreToolUse hook blocks the write. When update_state.py receives a --phase argument that does not match the current pipeline state, it rejects with an error. The REMINDER block includes the no-direct-write and no-batching constraint.

### AC-67: Stage 3 Completion Integrity (NEW IN 2.2)

Given Stage 3 with N total units, when route() evaluates advancement to Stage 4, then it validates: (a) all N units have complete_unit() timestamps, (b) the build log has routing entries for all 9 required sub-stages per unit, (c) each unit has a red run TESTS_FAILED entry, and (d) each unit has a green run TESTS_PASSED entry. Missing entries block advancement with a diagnostic.

### AC-68: Cross-Validated Build Log (NEW IN 2.2)

Given any routing action or state transition during Stages 3-5, then routing.py and update_state.py each append a structured JSONL entry to .svp/build_log.jsonl with the defined schema. The orchestrator does not write to the build log. At stage boundaries, every routing entry has a matching update_state entry.

### AC-69: Builder Script Write Protection (NEW IN 2.2)

Given Stages 3, 4, or 5, when the orchestrator attempts to write to scripts/*.py, scripts/toolchain_defaults/*, or scripts/templates/*, then the PreToolUse hook blocks the write and directs to the Hard Stop Protocol. During Stages 0-2, these paths remain writable.

### AC-70: Stage 0 Orchestrator Mentor Protocol (NEW IN 2.2)

Given Stage 0 gate transitions, when the orchestrator presents Gate 0.1, Gate 0.2, or Gate 0.3 to the human, then the orchestrator provides gate-specific contextual guidance per Section 6.9 — explaining what the gate protects, what to look for, and downstream consequences of the decision.

### AC-71: Stage 4 Orchestrator Oversight (NEW IN 2.2)

Given Stage 4 completion, when integration tests pass and regression test adaptation completes, then the orchestrator runs the 6-item detection checklist (Section 11.6) covering integration test completeness and adaptation integrity. Detected issues are delegated to agents; the orchestrator does not fix directly.

### AC-72: Stage 5 Orchestrator Oversight (NEW IN 2.2)

Given Stage 5 assembly completion, when structural validation passes, then the orchestrator runs the 10-item detection checklist (Section 12.17) covering cross-artifact consistency and validation meta-oversight. Detected issues flow through the bounded fix cycle; the orchestrator does not fix directly.

### AC-73: Stage 6 Orchestrator Oversight (NEW IN 2.2)

Given a post-delivery debug loop, when the orchestrator reaches each checkpoint (after triage, after repair, after regression test, after lessons learned), then it runs the applicable items from the 9-item checkpoint-annotated checklist (Section 12.18.13). Detected issues are flagged to the human or routed through the debug loop pipeline; the orchestrator does not fix directly.

### AC-74: Plugin MCP Server Declaration (NEW IN 2.2)

Given a `claude_code_plugin` project with `plugin.external_services` populated in the profile, when Stage 5 assembly completes, then the assembled `plugin.json` contains matching `mcpServers` entries for each declared service, all environment variable references use valid `${...}` syntax, and Gate C validates the MCP config against the schema in Section 40.7.2.

### AC-75: Plugin Skill Frontmatter Validation (NEW IN 2.2)

Given a `claude_code_plugin` project with skills, when Gate C runs, then each `SKILL.md` file has valid YAML frontmatter conforming to the schema in Section 40.7.4 -- all fields are from the recognized set, `allowed-tools` entries are valid Claude Code tool names, `model` values are valid identifiers, and string substitution syntax (`$ARGUMENTS`, `$0`, `$1`, `${...}`, `` !`...` ``) is valid.

### AC-76: Plugin Hook Event Coverage (NEW IN 2.2)

Given a `claude_code_plugin` project with `plugin.hook_events` populated in the profile, when Gate C runs, then each declared event has a corresponding hook definition in `hooks.json` or inline in `plugin.json`. Hook definitions conform to the schema in Section 40.7.5 with valid event names, valid hook types, and proper matcher syntax for tool events.

### AC-77: Plugin Agent Frontmatter Validation (NEW IN 2.2)

Given a `claude_code_plugin` project with agent definitions, when Gate C runs, then each `.md` file in `agents/` has valid YAML frontmatter conforming to the schema in Section 40.7.6 -- all fields are from the recognized set, `disallowedTools` entries are valid Claude Code tool names, and skills referenced in the `skills` array exist in the `skills/` directory.

### AC-78: Plugin Environment Variable Hygiene (NEW IN 2.2)

Given a `claude_code_plugin` project, when Gate C runs, then no file path references in `plugin.json`, hook scripts, or MCP/LSP configs contain hardcoded absolute paths -- all must use `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}`. All `${...}` environment variable references resolve to documented variables or standard plugin variables. Required env vars from `plugin.external_services` are documented.

### AC-79: Plugin External Service Integration (NEW IN 2.2)

Given a `claude_code_plugin` project, when the Option C interview captures external service dependencies, then the profile stores them in `plugin.external_services` with `name`, `mcp_server`, `auth`, and `env_vars` per entry (Section 40.7.9). On `svp resume`, pre-flight checks (Section 6.1.2) verify that required environment variables for each service are set.

### AC-80: Plugin Option C Extended Interview (NEW IN 2.2)

Given a `claude_code_plugin` project (not an SVP self-build archetype), when the setup agent runs the Option C interview, then it asks the 4-question extended interview (Section 6.4): MCP server connections, credential requirements, hook events, and user-facing skills. Responses populate `plugin.external_services`, `plugin.hook_events`, `plugin.skills`, and `plugin.mcp_servers` in the profile.

### AC-81: Two-Pass Bootstrap Completion (NEW IN 2.2, CHANGED IN 2.2)

Given an SVP self-build (`is_svp_build: true`), Pass 1 produces scaffolding (NOT the deliverable). Pass 2 produces the real deliverable. The build is complete when Pass 2's Stage 5 succeeds. `delivered_repo_path` points to Pass 2's output. Pass 1's workspace is a build artifact only — no reference to it is retained in pipeline state after Pass 2 completes. After Pass 2 completion, the pipeline state is identical to any A-D archetype post-delivery, with Stage 7 additionally available.

### AC-82: Self-Build Scope Classification (NEW IN 2.2)

Given an SVP self-build, `self_build_scope` is derived from `archetype`: `"language_extension"` for `"svp_language_extension"`, `"architectural"` for `"svp_architectural"`. No separate scope question is asked. The scope determines orchestrator posture and Pass 2 verification requirements per Section 43.

### AC-83: Language Extension Scope Invariant (NEW IN 2.2)

Given a self-build with `self_build_scope: "language_extension"`, only the 5 artifacts from Section 40.5 change (registry entry, toolchain JSON, setup interview path, dispatch implementations, spec docs). If any pipeline mechanism code (routing, state transition, quality gate execution, agent orchestration) changes, the build must be reclassified to `"architectural"`.

### AC-84: Architectural Build Elevated Oversight (NEW IN 2.2)

Given a self-build with `self_build_scope: "architectural"`, the orchestrator applies elevated oversight: checkpoint summaries at post-Stage-2 (mechanism change summary), every-5-units during Stage 3 (cross-unit consistency), post-Stage-4 (new vs. inherited test coverage), and post-Stage-5 (blind spot checklist before Pass 2).

### AC-85: Pass 2 Self-Reinforcing Failure Detection (NEW IN 2.2, CHANGED IN 2.2)

Given a self-build in Pass 2, when a unit implementing routing, state transition, or quality gate logic fails during its own pipeline processing, the orchestrator flags this as a potential self-reinforcing failure loop and enters the break-glass protocol (Section 43.9). This is NOT a Hard Stop — Hard Stop is exclusively for SVP N bugs during Pass 1. Break-glass permitted actions: present diagnostics to the human, write lessons-learned, mark unit `deferred_broken`, retry with human guidance, escalate to restart. Forbidden: fix code directly, modify spec/blueprint, skip stages. The goal is to push through to a deliverable state, then use Stage 6 and Stage 7 to systematically fix the bugs.

### AC-86: Mixed Scope Rejected (NEW IN 2.2)

Given the Area 0 archetype selector, Options E and F are mutually exclusive self-build scopes. If the human needs both language extension and architectural changes, they must sequence as two separate builds per Section 43.5. The setup agent explains this if asked. Note: this AC concerns self-build scope mixing (Options E+F), not the `"mixed"` project archetype (Option D). The `"mixed"` archetype is a standard project type, not a self-build scope.

### AC-87: Oracle After Pass 2 (NEW IN 2.2, CHANGED IN 2.2)

Given a completed self-build (Pass 2's Stage 5 succeeded), `/svp:oracle` (Section 35) is available as optional post-Pass-2 verification. The oracle is NOT available after Pass 1's Stage 5. The human selects the test project for each invocation: GoL test project for product testing (E-mode), SVP `docs/` for machinery testing (F-mode). No mode sequencing is enforced — the human decides what to test. The oracle reads the run ledger for cross-invocation context. The oracle is not part of the bootstrap protocol — it runs on the clean Pass 2 deliverable.

### AC-88: Language Extension Test Project (NEW IN 2.2, CHANGED IN 2.2)

Given a self-build with `self_build_scope: "language_extension"`, the stakeholder spec includes test project(s) matching the declared build scope (Section 43.3). Test projects are GoL re-expressions — same Game of Life game logic, adapted to the new language context. Standalone language scope: GoL in the new language. Mixed pair scope: GoL split across the two languages. Both scope: all of the above. The blueprint includes units that produce these test project artifacts, bundled in the deliverable under `examples/<test_project>/`. After Pass 2, the oracle uses these test projects (E-mode, Section 3.33) — not the Python Game of Life — to verify the new language pipeline works end-to-end.

### AC-89: Mixed Option D Dialog (NEW IN 2.2)

Given a new project where the human selects Option D, when the Area 0 dialog completes, then exactly 3-4 questions were asked (which language owns, communication direction(s), primary toolchain fast-path-or-detailed, secondary toolchain defaults-with-opt-out), and the profile is correctly populated with `archetype: "mixed"`, both language keys, communication dict, and both delivery/quality sections.

### AC-90: Mixed Single Conda Environment (NEW IN 2.2)

Given a `"mixed"` archetype project, when Pre-Stage-3 infrastructure setup runs, then a single conda environment is created containing both Python and R, bridge libraries (rpy2 and/or r-reticulate per the communication dict) are installed as conda packages, no renv is used, and both `delivery.<primary>.environment_recommendation` and `delivery.<secondary>.environment_recommendation` are `"conda"`.

### AC-91: Mixed Stage 5 Composition (NEW IN 2.2)

Given a `"mixed"` archetype project in Stage 5, when assembly completes, then: (1) two-phase assembly executed — primary assembler created root structure, secondary files placed in `<secondary_language>/` subdirectory; (2) both compliance scanners ran on their respective source trees; (3) quality configs for both languages are present; (4) a single `environment.yml` lists dependencies for both languages; (5) no cross-language import rewriting was attempted.

### AC-92: Mixed Cross-Language Bridge Test (NEW IN 2.2)

Given a `"mixed"` archetype project in Stage 4, when integration tests are authored, then at least one bridge verification test exists per declared communication direction in `language.communication`. Each bridge test invokes the secondary language from the primary (or vice versa) via the declared bridge library and verifies the result.

### AC-93: Mixed Profile Validation (NEW IN 2.2)

Given profile validation, when `archetype` is `"mixed"`, then: `language.secondary` is present and is a valid non-component registry language different from `language.primary`; `language.communication` contains at least one entry with a bridge library valid per the calling language's `bridge_libraries` registry field; secondary R `source_layout` must be `"scripts"`; secondary Python `source_layout` must be `"flat"`; both `delivery.<primary>.environment_recommendation` and `delivery.<secondary>.environment_recommendation` are `"conda"`; both `delivery.<primary>.dependency_format` and `delivery.<secondary>.dependency_format` are `"environment.yml"`. When `archetype` is NOT `"mixed"`, `language.secondary` is absent.

### AC-94: Test Project 1 — Python-owns-R (NEW IN 2.2)

Given the delivered SVP 2.2, `examples/gol-python-r/` contains a complete Game of Life test project with: stakeholder spec, blueprint, project context, and project profile. Python is primary (tkinter GUI + speed slider), R is secondary (GoL engine), rpy2 bridge. ~4 units. The oracle can use this test project to verify mixed-archetype pipeline behavior end-to-end.

### AC-95: Test Project 2 — R-owns-Python (NEW IN 2.2)

Given the delivered SVP 2.2, `examples/gol-r-python/` contains a complete Game of Life test project with: stakeholder spec, blueprint, project context, and project profile. R is primary (plain Shiny app + speed slider), Python is secondary (GoL engine), reticulate bridge. ~4 units. The oracle can use this test project to verify mixed-archetype pipeline behavior end-to-end.

### AC-96: Mixed Cleanup (NEW IN 2.2)

Given a `"mixed"` archetype project, when `/svp:clean` runs, then a single `conda env remove -n {env_name} --yes` removes the shared environment. No renv cleanup logic is invoked. No special mixed-specific cleanup is needed beyond the standard conda removal.

### AC-97: Orchestrator Break-Glass Protocol (NEW IN 2.2)

Given an E/F self-build during Pass 1 or Pass 2, when the routing script emits `break_glass` or the orchestrator detects loop conditions (same action dispatched 3+ consecutive times with no pipeline state change), then the orchestrator enters break-glass mode (Section 43.9). Permitted: present diagnostics to the human, write lessons-learned entries, mark unit `deferred_broken`, retry with human guidance, escalate to pipeline restart. Forbidden: fix code directly, modify spec/blueprint, skip stages or sub-stages.

### AC-98: Orchestrator Role Enforcement for Self-Builds (NEW IN 2.2)

Given an E/F self-build, then two additional enforcement mechanisms are active (Section 43.10): (1) a Claude Code skill for spec refresh at major phase transitions (Pass 1 start, transition gate, Pass 2 start, transition gate, oracle start), and (2) a PostToolUse hook on Agent tool returns that injects a monitoring reminder to verify subagent output against the spec before proceeding.

### AC-99: Pass 2 Nested Session (NEW IN 2.2)

Given an E/F self-build after Pass 1's Stage 5 completes and the human chooses PROCEED TO PASS 2 at the transition gate, then the orchestrator launches a nested session via `svp restore --plugin-path <pass1-deliverable>/svp/ --skip-to pre-stage-3` with spec and blueprint carried forward. For E archetypes (`self_build_scope: "language_extension"`), the orchestrator auto-approves all Stages 3-5 gates in the nested session (the post-Pass-2 transition gate is always presented to the human). For F archetypes (`self_build_scope: "architectural"`), all gates are surfaced transparently to the human. The nested session's `delivered_repo_path` becomes the authoritative deliverable on Pass 2 completion.

### AC-100: Post-Stage-5 Transition Gate for Self-Builds (NEW IN 2.2)

Given an E/F self-build at Pass 1 completion, when Stage 5 completes, then the routing script presents a structured bug summary (from build log and lessons-learned) and the transition gate `gate_pass_transition_post_pass1`. Human chooses: PROCEED TO PASS 2 or FIX BUGS (Stage 6). Stage 7 is NOT offered. After Pass 2 completion, the routing script presents `gate_pass_transition_post_pass2`. Human chooses: FIX BUGS (Stage 6) or RUN ORACLE (Stage 7).

### AC-101: E/F Archetype Selector Visibility (NEW IN 2.2)

Given a new project at Stage 0, when the archetype selector is presented, then Options A-D are shown as the standard choices. Below them, visually separated (typographic break or horizontal rule), an **EXPERT MODE** option is presented. Options E and F are shown only after the user selects Expert Mode. If E is selected, the setup agent asks the build scope question: NEW LANGUAGE, MIX LANGUAGES, or BOTH.

### AC-102: Oracle Mode Selection via Test Project (NEW IN 2.2, CHANGED IN 2.2)

Given an E/F self-build with Pass 2 complete, when `/svp:oracle` is invoked, the human selects a test project. GoL test projects invoke E-mode (product testing) — the oracle evaluates the built product. SVP `docs/` invokes F-mode (machinery testing) — the oracle evaluates pipeline behavior at each gate and state transition. No mode sequencing is enforced. The oracle reads the run ledger for cross-invocation context: first run plans from scratch; subsequent runs factor in prior events.

### AC-103: Pass 2 Deliverable Authority (NEW IN 2.2)

Given an E/F self-build after Pass 2's Stage 5 completes, then `delivered_repo_path` points to Pass 2's output. No reference to Pass 1's deliverable is retained in pipeline state (`pass2_nested_session_path` cleared to null). The pipeline state is identical to any A-D archetype post-delivery, with Stage 7 additionally available because `is_svp_build` is true.

### AC-104: Bug Capture via Lessons-Learned (NEW IN 2.2)

Given failures during Pass 1 or Pass 2 of an E/F self-build that trigger the orchestrator break-glass protocol, then bugs are logged using the existing lessons-learned infrastructure (Section 12.18). No separate bug tracking mechanism is created for self-builds. The same lessons-learned entries are consumed by Stage 6 triage (for immediate fixes), oracle trajectory planning (for risk prioritization), and future builds (for prevention). One channel, multiple consumers.

---

## 40. Language Provider Framework (NEW IN 2.2)

### 40.1 Overview

SVP 2.2 is a polyglot pipeline. While the pipeline itself always runs as Python, the delivered project can be written in Python or R (with component languages like Stan). The language provider framework is the mechanism that makes this possible.

The framework has three active components:
1. **Language Registry** — a data structure mapping language identifiers to complete build/test/lint/deliver configurations
2. **Dispatch Tables** — six per-language function dispatch tables distributed across pipeline units
3. **Profile Schema** — language-keyed delivery and quality configuration

A fourth component, **Dynamic Construction** (a Socratic dialog mechanism for configuring unsupported languages), is designed but deferred. Activated via self-build with `self_build_scope: "language_extension"`. See Sections 3.28 and 43.3.

### 40.2 Language Registry

The registry maps language identifiers to configuration dicts. Each entry is a complete specification of how to build, test, lint, and deliver in that language.

**Required keys for every language entry:**
- Identity: `id`, `display_name`
- File system: `file_extension`, `source_dir`, `test_dir`, `test_file_pattern`
- Build-time toolchain: `toolchain_file`, `environment_manager`, `test_framework`, `version_check_command`
- Code generation: `stub_sentinel`, `stub_generator_key`, `test_output_parser_key`, `quality_runner_key`
- Delivery defaults: `default_delivery`, `default_quality`
- Validation sets: `valid_linters`, `valid_formatters`, `valid_type_checkers`
- Hook configuration: `authorized_write_dirs`
- Error detection: `collection_error_indicators`
- Component support: `is_component_only`, `compatible_hosts`
- Cross-language support: `bridge_libraries` (dict mapping `"<caller>_<callee>"` direction strings to `{"library": "<name>", "conda_package": "<package>"}` — e.g., Python entry: `{"python_r": {"library": "rpy2", "conda_package": "rpy2"}}`, R entry: `{"r_python": {"library": "reticulate", "conda_package": "r-reticulate"}}`. Empty dict for languages with no bridge support. Used by Option D dialog and profile validation.)
- Delivery structure: `environment_file_name`, `project_manifest_file`, `valid_source_layouts`, `gitignore_patterns`, `entry_point_mechanism`, `quality_config_mapping`, `non_source_embedding`
- Agent prompts: `agent_prompts` (keyed by agent type: test_agent, implementation_agent, coverage_review_agent)

**Registry defaults contract.** The `default_delivery` and `default_quality` dicts must contain values for every field in the corresponding profile schema section (Section 6.4). For Python: `default_delivery` maps to `delivery.python.*` (environment_recommendation, dependency_format, source_layout, entry_points). For `default_quality`: maps to `quality.python.*` (linter, formatter, type_checker, import_sorter, line_length). The setup agent uses these defaults when populating the profile for Path 1 (same as pipeline) and as initial values for Path 2/3 dialogs. `use_repo_tooling` is excluded — it is always `false` by default and only set to `true` by explicit Area 5 selection.

**Built-in entries (shipped with SVP 2.2):**

**Python:**
- Full-language provider. File extension `.py`. Source dir `src`. Test dir `tests`. Test pattern `test_*.py`.
- Toolchain: `python_conda_pytest.json`. Environment: conda. Test framework: pytest.
- Stub sentinel: `__SVP_STUB__ = True  # DO NOT DELIVER — stub file generated by SVP`
- Quality: ruff (format + lint) + mypy (type check).
- Quality defaults (`default_quality`): `linter: "ruff"`, `formatter: "ruff"`, `type_checker: "mypy"`, `import_sorter: "ruff"`, `line_length: 88`.
- Collection error indicators: "ERROR collecting", "ImportError", "ModuleNotFoundError", "SyntaxError", "no tests ran".
- Delivery defaults (`default_delivery`): `environment_recommendation: "conda"`, `dependency_format: "environment.yml"`, `source_layout: "conventional"`, `entry_points: false`.
- Valid tools: linters (ruff, flake8, pylint, none), formatters (ruff, black, autopep8, none), type checkers (mypy, pyright, none).
- Authorized write dirs: `src`, `tests`, project root (for config files).
- Agent prompts: keyed by `test_agent`, `implementation_agent`, `coverage_review_agent` — contain Python-specific coding conventions and idioms for each agent role.
- Environment file: `environment.yml`. Project manifest: `pyproject.toml`.
- Valid source layouts: `conventional`, `flat`, `svp_native`.
- Gitignore patterns: `__pycache__/`, `*.pyc`, `.mypy_cache/`, `dist/`, `*.egg-info/`.
- Entry point mechanism: `pyproject_scripts` (generates `[project.scripts]` in `pyproject.toml`).
- Quality config mapping: `{"ruff": "ruff.toml", "black": "pyproject.toml [tool.black]", "flake8": ".flake8", "mypy": "pyproject.toml [tool.mypy]", "pyright": "pyproject.toml [tool.pyright]"}`.
- Non-source embedding: module-level string variable assignments (`FILENAME_UPPER_CONTENT = """..."""`).
- Compliance scan: AST-based. Banned patterns by environment: conda → scan for bare `pip`, `python`, `pytest` not preceded by `conda run -n`; pyenv → scan for `conda`; venv → scan for `conda`; poetry → scan for `conda` or bare `pip install`; none → scan for any environment manager commands.
- Bridge libraries: `{"python_r": {"library": "rpy2", "conda_package": "rpy2"}}`.
- Not component-only.

**R:**
- Full-language provider. File extension `.R`. Source dir `R`. Test dir `tests/testthat`. Test pattern `test-*.R`.
- Toolchain: `r_renv_testthat.json`. Environment: renv. Test framework: testthat.
- Stub sentinel: `# __SVP_STUB__ <- TRUE  # DO NOT DELIVER — stub file generated by SVP`
- Quality: lintr (lint) + styler (format). No type checker.
- Delivery defaults (`default_delivery`): `environment_recommendation: "renv"`, `dependency_format: "renv.lock"`, `source_layout: "package"`, `entry_points: false`.
- Quality defaults (`default_quality`): `linter: "lintr"`, `formatter: "styler"`, `type_checker: "none"`, `line_length: 80`.
- Valid tools: linters (lintr, none), formatters (styler, none), type checkers (none).
- Collection error indicators: "Error in library", "there is no package called", "could not find function".
- Authorized write dirs: `R`, `tests/testthat`, project root (for config files).
- Agent prompts: keyed by `test_agent`, `implementation_agent`, `coverage_review_agent` — contain R-specific coding conventions and idioms for each agent role.
- Environment file: `renv.lock`. Project manifest: `DESCRIPTION`.
- Valid source layouts: `package`, `scripts`.
- Gitignore patterns: `.Rhistory`, `.RData`, `.Rproj.user/`, `inst/doc/`.
- Entry point mechanism: `namespace_exports` (R packages use NAMESPACE exports; executable R scripts use shebang lines). No `[project.scripts]` equivalent.
- Quality config mapping: `{"lintr": ".lintr", "styler": ".styler.R"}`.
- Non-source embedding: top-level character assignments (`FILENAME_UPPER_CONTENT <- "..."`).
- Compliance scan: regex-based (R has no standard AST inspection library accessible from the pipeline). Banned patterns by environment: renv → scan for `install.packages()` (should use `renv::install()`), `system()` calls containing pip/conda; conda (R+conda) → scan for `install.packages()` or bare `Rscript` without `conda run`; packrat → scan for `renv::` calls.
- Test import switch: `source()` path rewrite (from `source("src/unit_N/stub.R")` to `source("R/real_module.R")`); path resolution via `.Rprofile` or testthat helpers.
- Importability: stub must be loadable via `source()` without error; R stubs do not require AST manipulation.
- Bridge libraries: `{"r_python": {"library": "reticulate", "conda_package": "r-reticulate"}}`.
- Not component-only.
- Ecosystem extensions: bioconductor (BiocManager), stan (cmdstanr/rstan), shiny (shinytest2; frameworks: golem, rhino), python interop (reticulate), notebooks (quarto, rmarkdown).

**Stan (component-only):**
- Component language. File extension `.stan`. `is_component_only: true`.
- Compatible hosts: R (via cmdstanr or rstan), Python (via cmdstanpy or pystan).
- Quality: Stan compiler syntax validation only.
- No test framework, no formatter, no linter of its own.
- Does not need all six dispatch entries — needs only quality runner (syntax check) and stub generator (model template).
- Bridge libraries: `{}` (no cross-language bridge support — Stan communicates via host language interfaces, not bridge libraries).

**Dispatch key fields.** Each registry entry contains dispatch key fields that map to dispatch table entries: stub_generator_key (maps to STUB_GENERATORS), test_output_parser_key (maps to TEST_OUTPUT_PARSERS), quality_runner_key (maps to QUALITY_RUNNERS). Full languages typically use their language name as the dispatch key value. Component languages use custom keys (e.g., Stan uses stan_template, stan_syntax, stan_syntax_check). Component languages must include a required_dispatch_entries field in their registry entry — a list of dispatch key field names where they must have entries (e.g., Stan: ['stub_generator_key', 'quality_runner_key']). Full languages omit this field; all six dispatch tables are required.

**COMPONENT_REQUIRED_KEYS** includes `required_dispatch_entries` in addition to the standard required keys for component language entries.

### 40.3 Dispatch Tables

Six dispatch tables, each living in the unit that owns the concern:

| # | Dispatch Table | Owning Unit | Protocol |
|---|---------------|-------------|----------|
| 1 | SIGNATURE_PARSERS | Signature Parsing unit | `(source: str, language_config: Dict) -> Any` |
| 2 | STUB_GENERATORS | Stub Generation unit | `(parsed_signatures: Any, language_config: Dict) -> str` |
| 3 | TEST_OUTPUT_PARSERS | Routing/Test Execution unit | `(stdout: str, stderr: str, returncode: int, language_config: Dict) -> RunResult` |
| 4 | QUALITY_RUNNERS | Quality Gate Execution unit | `(target_path: Path, gate_id: str, language_config: Dict, toolchain_config: Dict) -> QualityResult` |
| 5 | PROJECT_ASSEMBLERS | Git Repo Agent unit | `(project_root: Path, profile: Dict, assembly_config: Dict) -> Path` |
| 6 | COMPLIANCE_SCANNERS | Compliance unit | `(src_dir: Path, tests_dir: Path, language_config: Dict, toolchain_config: Dict) -> List[Dict]` |

Each dispatch table is a module-level dict in its owning unit. Implementations are local functions. No circular imports.

**Keying strategy:** COMPLIANCE_SCANNERS and PROJECT_ASSEMBLERS are keyed by language identifier (e.g., 'python', 'r'). SIGNATURE_PARSERS, STUB_GENERATORS, TEST_OUTPUT_PARSERS, and QUALITY_RUNNERS are keyed by the dispatch key value from the language registry entry (e.g., LANGUAGE_REGISTRY['python']['quality_runner_key']). The validate_dispatch_exhaustiveness function must use the correct key lookup strategy per table: language ID for assemblers and scanners, dispatch key for parsers and runners.

**(NEW IN 2.2) Test output parser contracts:**
- **Python (pytest):** Parses pytest stdout for lines matching `N passed, M failed, K errors`. Returns `RunResult` with parsed counts. Collection errors detected by `collection_error_indicators` from registry.
- **R (testthat):** Parses testthat output for `OK:`, `Failed:`, `Warnings:` counts. Returns `RunResult` with mapped counts (`OK` → passed, `Failed` → failed, `Warnings` → errors). Exact regex patterns for parsing are a blueprint decision — the spec constrains the expected output fields and their semantic mapping. Collection errors detected by `collection_error_indicators` from registry (R default: "Error in library", "there is no package called").
- **Stan (syntax check):** Parses Stan compiler output for syntax errors. Returns `RunResult` with status only (no passed/failed counts -- Stan files are compiled, not tested).

If parsing fails (unexpected output format), the parser returns `status="TESTS_ERROR"` with the raw output in the `output` field.

**Return type contracts** (defined as NamedTuples):
- `RunResult`: status, passed, failed, errors, output, collection_error
- `QualityResult`: status, auto_fixed, residuals, report

**RunResult NamedTuple fields** (renamed from TestResult in 2.2 to avoid pytest collection warning)**:** status (str), passed (int), failed (int), errors (int), output (str), collection_error (bool). Valid status values: 'TESTS_PASSED', 'TESTS_FAILED', 'TESTS_ERROR', 'COLLECTION_ERROR'.

**QualityResult NamedTuple fields:** status (str), auto_fixed (bool), residuals (list of str), report (str). Valid status values: 'QUALITY_CLEAN', 'QUALITY_AUTO_FIXED', 'QUALITY_RESIDUAL', 'QUALITY_ERROR'.

### 40.4 Profile Schema (Language-Keyed, CHANGED IN 2.2)

The `delivery` and `quality` sections of `project_profile.json` are language-keyed.

**(NEW IN 2.2)** The profile includes a top-level `archetype` field that determines the project category:

```json
{
  "archetype": "python_project",
  "language": {
    "primary": "python",
    "components": [],
    "communication": {},
    "notebooks": null
  }
}
```

**Valid archetypes:**
- `"python_project"` -- A Python software project. Toolchain configured through Area 0 dialog (Path 1 or Path 2). Standard Python assembly, testing, and quality gates apply.
- `"r_project"` -- An R software project. Toolchain configured through Area 0 dialog (Path 3). Standard R assembly, testing, and quality gates apply.
- `"claude_code_plugin"` -- A Claude Code plugin / agentic system. Hardcoded Python toolchain (conda, pytest, ruff, mypy). Activates plugin infrastructure: agent definitions, skills, hooks, commands, manifests, plugin-specific assembly and validation. See Section 40.7 for full specification. This is what SVP itself is.
- `"mixed"` -- Python and R as peer languages. One owns project structure (primary), the other is embedded (secondary). Single conda environment. See Section 40.6.
- `"language_extension"` -- [RETIRED: Use archetype `"svp_language_extension"` (Option E). See Section 43.3.]
- `"svp_language_extension"` -- SVP self-build adding a new language. Pipeline mechanisms unchanged. Derives `is_svp_build: true` and `self_build_scope: "language_extension"`. See Section 43.3.
- `"svp_architectural"` -- SVP self-build modifying pipeline architecture (stages, routing, state machine, quality gates). Derives `is_svp_build: true` and `self_build_scope: "architectural"`. See Section 43.4.

When `archetype` is `"svp_language_extension"` or `"svp_architectural"`, the derived field `is_svp_build` is set to `true` and plugin fields are auto-populated from SVP context (not asked interactively).

**(NEW IN 2.2) Plugin-specific profile fields.** When `archetype` is `"claude_code_plugin"`, the profile gains a `plugin` section:

| Field | Type | Description |
|-------|------|-------------|
| `plugin.external_services` | array | External service dependencies -- each entry has `name`, `mcp_server`, `auth`, `env_vars` (see Section 40.7.9) |
| `plugin.hook_events` | array of string | Hook events the plugin uses (e.g., `["PreToolUse", "PostToolUse", "SessionStart"]`) |
| `plugin.skills` | array of string | User-facing skills the plugin exposes (e.g., `["orchestration", "commit"]`) |
| `plugin.mcp_servers` | array of string | MCP server names the plugin bundles (e.g., `["google-drive", "slack"]`) |
| `plugin.uses_lsp` | boolean | Whether the plugin bundles LSP configs |

These fields are populated by the Option C extended interview (Section 6.4). They are consumed by Gate C validations (Section 40.7 Quality Gate C) and pre-flight checks (Section 6.1.2). When `archetype` is `"svp_language_extension"` or `"svp_architectural"`, these fields are auto-populated from SVP context rather than asked interactively.

**(NEW IN 2.2) Profile-to-manifest field mapping.** During Stage 5 assembly, plugin profile fields map to `plugin.json` manifest fields as follows: `plugin.external_services` → `mcpServers` (object), `plugin.hook_events` → `hooks` (string, path to hooks config), `plugin.skills` → `skills` (string, path to skills directory), `plugin.mcp_servers` → `mcpServers` (merged with external_services), `plugin.uses_lsp` → `lspServers` (object, if true). The camelCase naming in `plugin.json` follows the Claude Code plugin manifest convention; the snake_case naming in the profile follows Python convention.

**(NEW IN 2.2) Self-build scope field.** Derived from archetype:

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `self_build_scope` | string or null | `"language_extension"`, `"architectural"`, null | Derived from archetype: `"language_extension"` when archetype is `"svp_language_extension"`, `"architectural"` when archetype is `"svp_architectural"`, null otherwise. Determines orchestrator posture and Pass 2 verification requirements. See Section 43. Mixed scope is not supported — split into sequential builds (Section 43.5). |

Computed from archetype at profile creation — never independently set.

**Language-keyed example:**

```json
{
  "archetype": "r_project",
  "language": {
    "primary": "r",
    "components": ["python", "stan"],
    "communication": {
      "r_python": "reticulate",
      "r_stan": "cmdstanr"
    },
    "notebooks": "quarto"
  },
  "delivery": {
    "r": { "environment_recommendation": "renv" },
    "python": { "environment_recommendation": "conda" }
  },
  "quality": {
    "r": { "linter": "lintr", "formatter": "styler" },
    "python": { "linter": "ruff", "formatter": "ruff" }
  }
}
```

*(Example abbreviated -- production profiles include all fields per the registry defaults contract: `delivery.<key>` includes `environment_recommendation`, `dependency_format`, `source_layout`, `entry_points`; `quality.<key>` includes `use_repo_tooling`, `linter`, `formatter`, `type_checker`, `import_sorter` (Python only), `line_length`.)*

**Mixed archetype profile example (Python primary, R secondary):**

```json
{
  "archetype": "mixed",
  "language": {
    "primary": "python",
    "secondary": "r",
    "communication": {
      "python_r": "rpy2"
    },
    "notebooks": null
  },
  "delivery": {
    "python": {
      "environment_recommendation": "conda",
      "dependency_format": "environment.yml",
      "source_layout": "conventional",
      "entry_points": true
    },
    "r": {
      "environment_recommendation": "conda",
      "dependency_format": "environment.yml",
      "source_layout": "scripts",
      "entry_points": false
    }
  },
  "quality": {
    "python": {
      "linter": "ruff",
      "formatter": "ruff",
      "type_checker": "mypy",
      "import_sorter": "ruff",
      "line_length": 88
    },
    "r": {
      "linter": "lintr",
      "formatter": "styler",
      "type_checker": "none",
      "line_length": 80
    }
  }
}
```

*(Footnote: For the `"mixed"` archetype, `environment_recommendation` and `dependency_format` for both languages are hard constraints forced to `"conda"` and `"environment.yml"` respectively — these are not configurable by the human. See Section 40.6.2.)*

**Backward compatibility:** `load_profile` detects SVP 2.1-format profiles (flat delivery/quality sections) and auto-migrates by wrapping under a `"python"` key and adding `language.primary = "python"`.

**Field path shorthand convention.** Throughout this spec, `delivery.<field>` and `quality.<field>` without an explicit language key (e.g., `delivery.source_layout`, `quality.linter`) refer to the resolved language-specific subsection for the language currently being processed. The full path is always `delivery.<language_key>.<field>` (e.g., `delivery.python.source_layout`). This shorthand appears in sections describing per-language delivery agent behavior and profile-driven generation (Sections 12.7–12.15) and cross-artifact consistency checks (Section 12.17), where the operating language is unambiguous from context. Toolchain structure references (`quality.gate_a`, `quality.packages` in `toolchain.json`) are not profile paths and are unaffected by this convention. Schema-level references (Section 6.4, contradiction detection, profile validation) use explicit language-keyed paths.

### 40.5 Adding a New Language (CHANGED IN 2.2)

To add support for a new language, an implementer provides exactly five artifacts. No modifications to Sections 10, 11, 12, or any other pipeline-mechanism section are required — those sections dispatch through registry lookups and dispatch tables.

**Artifact 1: Language Registry Entry (Section 40.2)**

Add an entry to the LANGUAGE_REGISTRY with all required keys (use the Python or R built-in entry as template). Every key must have a value; use null or "none" for inapplicable capabilities.

Required key groups:
- Identity: `id`, `display_name`
- File system: `file_extension`, `source_dir`, `test_dir`, `test_file_pattern`
- Build-time toolchain: `toolchain_file`, `environment_manager`, `test_framework`, `version_check_command`
- Code generation: `stub_sentinel`, `stub_generator_key`, `test_output_parser_key`, `quality_runner_key`
- Delivery structure: `environment_file_name`, `project_manifest_file`, `valid_source_layouts`, `gitignore_patterns`, `entry_point_mechanism`, `quality_config_mapping`, `non_source_embedding`
- Delivery defaults: `default_delivery`, `default_quality`
- Validation sets: `valid_linters`, `valid_formatters`, `valid_type_checkers`
- Hook configuration: `authorized_write_dirs`
- Error detection: `collection_error_indicators`
- Component support: `is_component_only`, `compatible_hosts`
- Agent prompts: `agent_prompts` (test_agent, implementation_agent, coverage_review_agent)

**Artifact 2: Toolchain JSON File (Section 6.5)**

Create `scripts/toolchain_defaults/<language>_<env>_<test>.json` following the toolchain schema (Section 6.5). Must contain: environment (create, install, run_prefix), testing (framework, run, coverage), quality (packages, gate_a, gate_b, gate_c composition lists), packaging, language.

**Artifact 3: Stage 0 Interview Path (Section 6.4)**

Add a setup interview path for the new language. The path must populate all profile fields using registry defaults. Follow the existing Python (Path 1/2) or R (Path 3) patterns.

**Artifact 4: Six Dispatch Table Implementations (Section 40.3)**

Implement:
1. `SIGNATURE_PARSERS[key]` — parse source to extract signatures
2. `STUB_GENERATORS[key]` — generate stub modules from signatures
3. `TEST_OUTPUT_PARSERS[key]` — parse test framework output into RunResult
4. `QUALITY_RUNNERS[key]` — run quality gates, return QualityResult
5. `PROJECT_ASSEMBLERS[language]` — assemble delivered repository
6. `COMPLIANCE_SCANNERS[language]` — scan for delivery compliance violations

Each must conform to the protocol in Section 40.3.

**Artifact 5: Spec Documentation**

Add a built-in entry subsection under Section 40.2 documenting the language's registry values. This is the only spec prose that mentions the new language by name.

**What does NOT change:** Sections 10 (Stage 3 cycle), 11 (Stage 4), 12 (Stage 5) — these dispatch through registry lookups and dispatch tables. Section 3 (architecture) — routing and state management are language-agnostic. Pre-Stage-3 (Section 9) — environment creation dispatches through the registry.

### 40.6 Multi-Language Projects (ACTIVATED IN 2.2)

The `"mixed"` archetype supports two non-component languages as peers in a single project. One language is **primary** (owns project structure) and the other is **secondary** (embedded). Communication uses bridge libraries registered in the language registry (e.g., Python calls R via rpy2; R calls Python via reticulate). The Area 0 Option D dialog determines which language is primary and which is secondary.

The component language infrastructure (registry fields `is_component_only`, `compatible_hosts`, `required_dispatch_entries`) remains in the registry schema for component-only languages like Stan. The `"mixed"` archetype is distinct from the component model: both primary and secondary are full languages with complete dispatch table entries.

#### 40.6.1 Profile Structure

The `"mixed"` archetype introduces the `language.secondary` field:

- `language.primary`: the language that owns project structure (e.g., `"python"`)
- `language.secondary`: the peer language embedded in the project (e.g., `"r"`). Present only when `archetype` is `"mixed"`.
- `language.communication`: dict keyed by `"<caller>_<callee>"` direction strings (e.g., `"python_r": "rpy2"`, `"r_python": "reticulate"`). One or both directions may be present depending on the project's communication needs.

The profile contains two `delivery` sections (keyed by primary and secondary language) and two `quality` sections (keyed by primary and secondary language). Both are populated during the Option D dialog.

**Validation rules:**
- When `archetype` is `"mixed"`, `language.secondary` MUST be present and MUST be a valid language in the registry (not a component-only language).
- When `archetype` is NOT `"mixed"`, `language.secondary` MUST be absent. Its presence is a profile validation error.
- `language.primary` and `language.secondary` MUST be different languages.
- `language.communication` MUST contain at least one entry with a bridge library that is valid per the `bridge_libraries` field in the language registry for the calling language (e.g., `rpy2` for Python→R, `reticulate` for R→Python).
- When a language is secondary in a `"mixed"` project, `delivery.<secondary>.source_layout` is constrained to layouts that do not produce a competing project manifest. For R secondary: forced to `"scripts"` (not `"package"`, which would produce DESCRIPTION). For Python secondary: forced to `"flat"` (not `"conventional"` or `"svp_native"`, which produce `pyproject.toml` at root competing with the primary project manifest). Profile validation enforces this for all secondary languages.

#### 40.6.2 Environment Constraint

Mixed-language projects use a single conda environment for both languages. This is a hard constraint — no renv + conda side-by-side.

- Both `delivery.<primary>.environment_recommendation` and `delivery.<secondary>.environment_recommendation` are forced to `"conda"`.
- Both `delivery.<primary>.dependency_format` and `delivery.<secondary>.dependency_format` are forced to `"environment.yml"`.
- R packages are installed via conda (e.g., `conda install r-base r-ggplot2`), not renv.
- Bridge libraries are installed as conda packages using the `conda_package` value from the registry's `bridge_libraries` field (e.g., `rpy2` for Python→R, `r-reticulate` for R→Python).
- A single `environment.yml` lists dependencies for both languages plus bridge libraries.

#### 40.6.3 Blueprint and Stage 3

Per-unit language dispatch (Section 10, AC-48) already handles mixed projects without modification. Each unit in the blueprint is tagged with its language, and the stub generator, test framework, and quality gates dispatch through the correct language-specific entries. **(CHANGED IN 2.2) Cross-language failure handling:** In mixed-archetype projects, Stage 3 processes all units regardless of language. If units in one language pass but units in the other fail, the failing units follow the normal fix ladder for their language. Stage 3 completion requires ALL units (both languages) to pass — there is no per-language partial advancement. Bridge test failures in Stage 4 are attributed to the calling language (the language that initiates the bridge call) for fix ladder purposes. The no-cross-language-import-rewriting constraint (Section 40.6.4) applies during Stage 3 import switching as well as Stage 5 assembly.

Both primary and secondary languages need all 6 dispatch table entries (signature parser, stub generator, test output parser, quality runner, project assembler, compliance scanner). This is what distinguishes a secondary language from a component language — components may have fewer entries, but secondary languages are full peers.

**Bridge unit language tagging.** In mixed projects, bridge units — units that implement cross-language communication via rpy2 or reticulate — are tagged with the **calling** language (the language the bridge code is written in, not the language being called). An rpy2 bridge unit is Python code that calls R; it is tagged as Python. A reticulate bridge unit is R code that calls Python; it is tagged as R. This determines which language's stub generator, test framework, and quality gates apply to the bridge unit.

**Cross-language DAG edges.** Dependencies between units of different languages are valid DAG edges. A Python bridge unit may declare an R engine unit as an upstream dependency. The DAG is a logical dependency graph — contracts are language-agnostic prose. `extract_upstream_contracts` works across languages without modification. Topological build order naturally builds upstream units first regardless of language.

#### 40.6.4 Stage 5 Assembly Composition

Stage 5 assembly for `"mixed"` projects uses a two-phase composition model:

- **Phase 1 — Primary assembly:** The primary language's `PROJECT_ASSEMBLERS[primary]` creates the project root structure (e.g., `pyproject.toml` for Python, `DESCRIPTION` for R).
- **Phase 2 — Secondary placement:** Secondary language source files are placed in a `<secondary_language>/` subdirectory at the project root (e.g., `r/` for R secondary, `python/` for Python secondary). Secondary test files go in `<secondary_language>/tests/`.

The git repo agent handles both phases in a single invocation. When the agent reads `archetype: "mixed"` from the profile, it executes Phase 1 (primary assembler) then Phase 2 (secondary placement) within its single task. No routing script change is needed — assembly remains a single agent invocation as for all other archetypes.

**Eight composition constraints:**

1. **Primary owns root.** The primary assembler determines root-level project structure. Secondary files never appear at the project root.
2. **Secondary in subdirectory.** All secondary language source and test files are placed in `<secondary_language>/` at the project root.
3. **Both compliance scanners.** `COMPLIANCE_SCANNERS[primary]` runs on the primary source tree; `COMPLIANCE_SCANNERS[secondary]` runs on the `<secondary_language>/` subtree.
4. **Both quality configs.** Quality tool configuration files for both languages are generated (e.g., `ruff.toml` for Python + `.lintr` for R).
5. **Single environment.yml.** One `environment.yml` at the project root lists all dependencies for both languages and bridge libraries.
6. **Entry points: primary canonical, secondary auxiliary.** Both `delivery.<primary>.entry_points` and `delivery.<secondary>.entry_points` may be `true`. The primary language's entry point is the project's canonical entry (shown first in README, registered in the primary manifest). Secondary language entry points are documented as auxiliary under an "Additional scripts" section in README. When only one language has entry points, it is the sole entry regardless of primary/secondary status.
7. **No cross-language import rewriting.** Bridge libraries (rpy2, reticulate) use runtime discovery — they find R/Python at runtime, not through import paths. The Stage 5 import rewriting (Section 12.1.1 Rule 3) operates within each language's source tree independently. No cross-language import rewriting is needed or attempted.
8. **Gate C per-language.** Gate C runs within each language's source tree independently. No cross-language type checking.

#### 40.6.5 Stage 4 Cross-Language Integration Tests

For `"mixed"` archetype projects, the integration test suite (Stage 4) must additionally include at least one cross-language bridge verification test per declared communication direction:

- If `language.communication` contains a `"python_r"` entry: a test that invokes R from Python via rpy2 and verifies the result.
- If `language.communication` contains a `"r_python"` entry: a test that invokes Python from R via reticulate and verifies the result.

These bridge tests verify that the cross-language communication mechanism works end-to-end in the built project. They are in addition to the standard integration tests required by Section 11.

#### 40.6.6 Cleanup

Mixed archetype cleanup is a single `conda env remove -n {env_name} --yes`. No renv cleanup, no special logic — the single conda environment contains everything for both languages.

#### 40.6.7 Test Projects

Two Game of Life test projects demonstrate the `"mixed"` archetype in both directions:

**Test Project 1: `examples/gol-python-r/` (Python-owns-R)**

Python is primary, R is secondary. Communication: Python calls R via rpy2.

- **GUI unit (Python):** tkinter-based graphical interface with a speed slider. Calls the R GoL engine via rpy2 to compute each generation. Displays the grid and handles user interaction.
- **GoL engine unit (R):** Pure R implementation of Game of Life step logic (neighbor counting, birth/death rules). Exposed to Python through rpy2.
- **Bridge unit (Python):** rpy2 integration layer — imports the R engine, converts between Python and R data structures (numpy arrays ↔ R matrices).
- **Main entry point (Python):** Launches the tkinter GUI, initializes the R engine via the bridge.

Approximate scope: ~4 units. Single conda environment with Python, R, rpy2, numpy, tkinter.

**Test Project 2: `examples/gol-r-python/` (R-owns-Python)**

R is primary, Python is secondary. Communication: R calls Python via reticulate.

- **Shiny app unit (R):** Plain Shiny application (not golem/rhino) with a speed slider. Uses reticulate to call the Python GoL engine. Renders the grid via Shiny reactive output.
- **GoL engine unit (Python):** Pure Python implementation of Game of Life step logic. Exposed to R through reticulate.
- **Bridge unit (R):** reticulate integration layer — sources the Python engine, converts between R and Python data structures (R matrices ↔ numpy arrays).
- **Main entry point (R):** `app.R` launches the Shiny application.

Approximate scope: ~4 units. Single conda environment with R, Python, r-shiny, r-reticulate, numpy.

### 40.7 Claude Code Plugin Archetype (NEW IN 2.2, EXTENDED IN 2.2)

When `archetype` is `"claude_code_plugin"`, the pipeline recognizes the project as a Claude Code plugin -- an agentic system that runs inside Claude Code. This is the archetype SVP uses when building itself (Mode A self-build). Plugins can "glue" Claude Code to external products (Google Drive, NotebookLM, Slack, databases, etc.) via MCP servers -- without needing separate API keys for model access.

**What a Claude Code plugin adds to a standard Python project:**

The language is Python. All Python toolchain applies (conda, pytest, ruff, mypy). The plugin archetype activates additional infrastructure:

| Artifact Category | File Type | Directory | Examples |
|------------------|-----------|-----------|----------|
| Agent definitions | Markdown (`.md`) | `agents/` | `setup_agent.md`, `test_agent.md` |
| Slash commands | Markdown (`.md`) | `commands/` | `cmd_save.md`, `cmd_bug.md` |
| Skills | Markdown (`.md`) | `skills/` | `skills/orchestration/orchestration.md` |
| Hook scripts | Bash (`.sh`), Python (`.py`) | `hooks/` | `write_authorization.sh`, `non_svp_protection.sh` |
| Plugin manifest | JSON | `.claude-plugin/` | `plugin.json` |
| Marketplace catalog | JSON | `.claude-plugin/` (repo root) | `marketplace.json` |
| MCP server config | JSON (`.mcp.json`) | plugin root | External service connections |
| LSP server config | JSON (`.lsp.json`) | plugin root | Language intelligence |
| Pipeline scripts | Python (`.py`) | `scripts/` | `routing.py`, `prepare_task.py` |
| Templates | Mixed | `scripts/templates/` | `claude_md.py`, config templates |

Note: `.mcp.json` and `.lsp.json` go at plugin root level (alongside `agents/`, `skills/`), NOT inside `.claude-plugin/`. Only `plugin.json` goes in `.claude-plugin/`.

**Mixed artifact types in the blueprint:**

A Claude Code plugin blueprint contains units that produce different artifact types:
- **Python units:** Standard code -- tested with pytest, checked by ruff/mypy. Follow the normal Stage 3 cycle.
- **Markdown units (agent definitions, skills, commands):** Content artifacts -- validated for structure (required frontmatter fields, section headings, parameter schemas) but not compiled or type-checked. The test agent writes structural validation tests for these.
- **Bash units (hook scripts):** Shell scripts -- validated for syntax (bash -n) and tested for correct behavior via pytest (testing hook output against known inputs).
- **JSON units (manifests, MCP configs, LSP configs):** Configuration artifacts -- validated against schema (plugin.json schema, marketplace.json schema, MCP schema, LSP schema). Tests verify required fields, correct paths, valid values, and environment variable syntax.

The blueprint author tags each unit with its artifact type using code fence annotations:
- ` ```python ` -- Python code unit
- ` ```markdown ` -- Agent definition / skill / command unit
- ` ```bash ` -- Hook script unit
- ` ```json ` -- Manifest / configuration unit

**(CHANGED IN 2.2) Plugin artifact dispatch mechanism.** Plugin units are tagged with a `language_tag` in the blueprint that determines dispatch. Python units use `"python"` (standard dispatch). Non-Python artifact units use composite dispatch keys: `"plugin_markdown"`, `"plugin_bash"`, `"plugin_json"`. These keys are registered in the plugin archetype's dispatch table extensions — NOT in the language registry (which is for full languages only). The plugin archetype registers additional entries in `STUB_GENERATORS`, `TEST_OUTPUT_PARSERS`, and `QUALITY_RUNNERS` for each composite key. These entries implement the behavior described in the table below. Red run and green run for non-executable artifacts run pytest tests that validate structure/schema — they DO go through the standard Stage 3 per-unit cycle, but the tests verify structure rather than behavior. Coverage review applies to all artifact types — the coverage agent checks that blueprint-specified structural requirements have corresponding tests. The fix ladder applies to all artifact types — if structural tests fail, the implementation agent is re-invoked to fix the content.

**Stage 3 adaptations for plugin units:**

| Artifact Type | Dispatch Key | Stub Generation | Test Generation | Quality Gate A/B | Implementation |
|--------------|--------------|----------------|-----------------|-----------------|----------------|
| Python | `"python"` | AST-based stub | pytest behavioral tests | ruff + mypy | Python code |
| Markdown (agent def) | `"plugin_markdown"` | Template with required sections | pytest structural tests (check headings, frontmatter per 40.7.6) | Format check only | Markdown content |
| Markdown (skill) | `"plugin_markdown"` | Template with frontmatter | pytest structural tests (check frontmatter per 40.7.4) | Format check only | Markdown content |
| Bash (hook) | `"plugin_bash"` | Template with shebang + placeholder | pytest behavioral tests (subprocess calls) | bash -n syntax check | Shell script |
| Python (hook) | `"python"` | Template with main guard | pytest subprocess tests | ruff + mypy | Python script |
| JSON (manifest) | `"plugin_json"` | Template with required fields | pytest schema tests (full schema per 40.7.1) | JSON validation | JSON content |
| JSON (MCP config) | `"plugin_json"` | Template with server entries | pytest schema tests (transport-specific per 40.7.2) | JSON + env var syntax validation | JSON content |
| JSON (LSP config) | `"plugin_json"` | Template with language entries | pytest schema tests (per 40.7.3) | JSON validation | JSON content |

#### 40.7.1 Plugin Manifest Schema (Full plugin.json)

The `plugin.json` manifest declares all plugin capabilities. Full schema:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Plugin identifier (kebab-case) |
| `description` | string | Yes | Human-readable description |
| `version` | string | Yes | Semver string |
| `author` | object | Yes | `{ "name", "email"?, "url"? }` |
| `mcpServers` | object or string | No | MCP server definitions inline, or path to `.mcp.json` |
| `lspServers` | object or string | No | LSP server definitions inline, or path to `.lsp.json` |
| `hooks` | object or string | No | Hook definitions inline, or path to `hooks.json` |
| `commands` | string or array | No | Path to commands dir or list of command files |
| `agents` | string | No | Path to agents directory (default: `agents/`) |
| `skills` | string | No | Path to skills directory (default: `skills/`) |
| `outputStyles` | string | No | Path to output styles directory |
| `tools` | array of string | No | Native Claude Code tools the plugin uses |

The `tools` field enumerates which native Claude Code tools the plugin requires: `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `Agent`, `WebFetch`, `WebSearch`, etc. This is declarative. Plugins do NOT need separate API keys for tool use -- they operate under the host session's model access.

`mcpServers` and `lspServers` can be either an inline object (keys = server names, values = server configs) or a string path relative to plugin root. When a string path is provided, the referenced file (`.mcp.json` or `.lsp.json`) is loaded at plugin install time.

#### 40.7.2 MCP Server Integration

MCP (Model Context Protocol) servers are the core mechanism for connecting Claude Code plugins to external products and services. A plugin bundles MCP server configurations; Claude Code manages the server lifecycle.

**MCP server definition schema** (each entry keyed by server name, in `.mcp.json` or inline in `plugin.json` under `mcpServers`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes (if not stdio default) | Transport: `"stdio"`, `"http"`, `"sse"` (deprecated) |
| `command` | string | Yes (stdio) | Executable command |
| `args` | array of string | No | Command arguments |
| `env` | object | No | Environment variables for server process |
| `url` | string | Yes (http) | Server URL |
| `headers` | object | No | HTTP headers (for auth tokens etc.) |

**Environment variable expansion** in all string values:
- `${CLAUDE_PLUGIN_ROOT}` -- plugin installation dir (changes on update)
- `${CLAUDE_PLUGIN_DATA}` -- plugin persistent data dir (survives updates)
- `${ENV_VAR}` -- any host environment variable
- `${ENV_VAR:-default}` -- with fallback

**External service integration pattern.** The plugin bundles the MCP server config; the human provides credentials via environment variables or OAuth flow at install time. The plugin itself does not store secrets -- it references them via `${ENV_VAR}` expansion.

**Credential handling.** Three authentication patterns:
1. **API key via env var:** `"headers": { "Authorization": "Bearer ${SERVICE_API_KEY}" }`
2. **OAuth flow:** Claude Code handles OAuth interactively via `/mcp` command. Tokens stored in system keychain, refreshed automatically.
3. **No auth:** For local MCP servers (stdio transport).

**Stage 3 adaptations:** `.mcp.json` is a JSON artifact validated against the MCP schema. Tests verify server names are unique, transport types are valid, required fields per transport type are present (stdio requires `command`; http requires `url`), and env var references use valid `${...}` syntax.

#### 40.7.3 LSP Server Integration

Plugins can bundle LSP (Language Server Protocol) configs for real-time language intelligence (diagnostics, go-to-definition, hover/type info).

**LSP server definition schema** (each entry keyed by language ID, in `.lsp.json` or inline in `plugin.json` under `lspServers`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | LSP server executable |
| `args` | array of string | No | Command arguments |
| `env` | object | No | Environment variables |
| `extensionToLanguage` | object | No | File extension to language ID mapping |
| `initializationOptions` | object | No | LSP initialization options |
| `settings` | object | No | LSP workspace settings |

Environment variable expansion rules from Section 40.7.2 apply.

**Stage 3 adaptations:** `.lsp.json` is a JSON artifact validated against the LSP schema. Tests verify language IDs are unique, `command` is present for each entry, and env var references use valid syntax.

#### 40.7.4 Skill System Specification

Skills are user-invocable or auto-invocable capabilities defined as `SKILL.md` files in the `skills/` directory (or subdirectories).

**Skill frontmatter schema (YAML in SKILL.md):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Overrides directory name |
| `description` | string | Recommended | Used by Claude for auto-invocation decisions |
| `argument-hint` | string | No | Autocomplete hint |
| `allowed-tools` | comma-separated string | No | Restricts tool access for this skill |
| `model` | string | No | Model override (`sonnet`, `opus`, `haiku`) |
| `effort` | string | No | `low`, `medium`, `high`, `max` |
| `context` | string | No | `"fork"` for isolated subagent context |
| `agent` | string | No | Agent type when `context: fork` |
| `disable-model-invocation` | boolean | No | Skill runs without model calls |
| `user-invocable` | boolean | No | Appears in user-facing skill list |

**String substitution in skill bodies:**
- `$ARGUMENTS` / `$0`, `$1` -- arguments passed to invocation
- `${CLAUDE_SESSION_ID}` -- current session ID
- `${CLAUDE_SKILL_DIR}` -- directory containing this SKILL.md
- `` !`command` `` -- inline command execution (output substituted before Claude sees prompt)

**Stage 3 structural tests validate:** valid YAML frontmatter, all fields from recognized set, `allowed-tools` entries are valid tool names, `model` values are valid identifiers, string substitution uses valid `$ARGUMENTS` / `$0` / `$1` / `${...}` / `` !`...` `` syntax.

#### 40.7.5 Hook System Specification

Hooks allow plugins to execute code in response to Claude Code lifecycle events. The system supports four hook types and 12+ events.

**Hook types:**

| Type | Description |
|------|-------------|
| `command` | Shell command (subprocess) |
| `http` | HTTP POST to URL |
| `prompt` | Text injected into model context |
| `agent` | Subagent spawned with tools |

**Hook events:**

| Event | Trigger | Common Use |
|-------|---------|-----------|
| `SessionStart` | Session begins | Initialize state, load configs |
| `UserPromptSubmit` | User submits prompt | Input validation |
| `PreToolUse` | Before tool invocation | Authorization, path protection |
| `PostToolUse` | After tool succeeds | Auditing, auto-format |
| `PostToolUseFailure` | After tool fails | Error recovery |
| `PermissionRequest` | Permission dialog | Custom permission policies |
| `PreCompact` | Before context compaction | Save critical state |
| `PostCompact` | After compaction | Restore state |
| `SubagentStart` | Subagent spawned | Resource tracking |
| `SubagentStop` | Subagent terminates | Cleanup |
| `ConfigChange` | Configuration modified | Validation |
| `Stop` | Session ending | Final state save, cleanup |

**Hook definition schema** (in `hooks.json` or inline in `plugin.json` under `hooks`):

```json
{
  "hooks": {
    "<EventName>": [
      {
        "matcher": "<tool-name-regex>",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/check.sh"
          }
        ]
      }
    ]
  }
}
```

The `matcher` field is optional and only applies to tool-related events (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`). It filters which tool invocations trigger the hook using a regex pattern against the tool name.

**Stage 3 adaptations:** Expanded validation table replacing the current single "Bash (hook)" row:

| Hook Type | Stub | Tests | Quality Gate |
|-----------|------|-------|-------------|
| `command` (bash) | Template + shebang | pytest subprocess tests | `bash -n` |
| `command` (python) | Template + main guard | pytest subprocess tests | ruff + mypy |
| `http` | URL template | pytest mock-server tests | URL format validation |
| `prompt` | Placeholder text | pytest content tests | Markdown format check |
| `agent` | Agent reference | pytest reference tests | Agent-exists check |

#### 40.7.6 Agent Definition Specification

Agent definitions are Markdown files in the `agents/` directory that define specialized subagents the plugin can spawn.

**Agent frontmatter schema (YAML):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Agent identifier |
| `description` | string | Recommended | When Claude should invoke this agent |
| `model` | string | No | Model override |
| `effort` | string | No | Reasoning effort |
| `maxTurns` | number | No | Max conversation turns |
| `disallowedTools` | comma-separated string | No | Tools this agent cannot use |
| `skills` | array of string | No | Skills this agent can invoke |
| `memory` | string | No | Memory persistence setting |
| `background` | string | No | Background context loaded at startup |
| `isolation` | string | No | `"worktree"` for isolated copy |

**Required body:** System prompt text defining agent behavior. May reference skills via `/skillname` invocation syntax.

**Stage 3 structural tests:** Valid YAML frontmatter, all fields from recognized set, `model` values are valid identifiers, `disallowedTools` entries are valid tool names, referenced skills in `skills` array exist in the `skills/` directory.

#### 40.7.7 Plugin Environment and Lifecycle

**Plugin environment variables:**

| Variable | Description | Persistence |
|----------|-------------|-------------|
| `CLAUDE_PLUGIN_ROOT` | Installation directory | Changes on update |
| `CLAUDE_PLUGIN_DATA` | Persistent data directory | Survives updates |

Plugin code must use `CLAUDE_PLUGIN_DATA` for state that survives updates (configuration, caches, learned data). `CLAUDE_PLUGIN_ROOT` is for read-only bundled assets (scripts, templates, agent definitions).

**Lifecycle:** Install → Load → (Update preserves `PLUGIN_DATA`) → Uninstall.

**Stage 5 assembly rule:** All file path references in `plugin.json`, hook scripts, and MCP configs must use `${CLAUDE_PLUGIN_ROOT}` for bundled assets -- never absolute paths. Gate C checks for hardcoded absolute paths.

#### 40.7.8 Marketplace and Distribution

**Source types** for plugin installation:

| Type | Format | Example |
|------|--------|---------|
| Relative path | `./path` | `"source": "./svp"` |
| GitHub | `owner/repo` | `"source": {"source": "github", "repo": "owner/repo"}` |
| Git URL | Full URL | `"source": {"source": "url", "url": "https://..."}` |
| Git subdir | `owner/repo:path` | `"source": {"source": "git-subdir", ...}` |
| npm | `@scope/pkg` | `"source": {"source": "npm", "package": "@org/plugin"}` |

**Installation scopes:**
- `user` -- all projects (global installation)
- `project` -- shared, version-controlled (committed to repo)
- `local` -- private/dev (gitignored)

**marketplace.json schema** -- extends the existing brief mention in Section 1.4 with the full schema:

```json
{
  "name": "plugin-name",
  "owner": "author-name",
  "plugins": [
    {
      "name": "plugin-name",
      "source": "./path",
      "metadata": {
        "category": "development",
        "tags": ["mcp", "integration"],
        "description": "Plugin description"
      },
      "strict": true
    }
  ]
}
```

**Strict mode:** `strict: true` (default) means `plugin.json` inside the plugin directory is authoritative for all plugin configuration. `strict: false` means the marketplace entry itself is the entire definition (for lightweight plugins that don't need a full directory structure).

#### 40.7.9 External Service Integration Patterns

Three patterns for connecting plugins to external services:

**Pattern 1: MCP-bridged services.** Plugin bundles MCP server config connecting to an external service (Google Drive, NotebookLM, Slack, databases). The MCP server handles protocol translation and auth. Claude Code invokes MCP tools as if they were native tools. This is the primary integration mechanism.

**Pattern 2: Hook-based integrations.** Hooks on lifecycle events (`PostToolUse`, `Stop`) push data to external services for logging, notifications, or audit trails.

**Pattern 3: Skill-mediated workflows.** Skills orchestrate multi-step interactions across MCP servers and native tools, providing high-level user-facing commands.

**No separate API keys for model access.** Plugins run inside the host Claude Code session -- they use the session's model. Only external service credentials (API keys, OAuth tokens) are needed, and these are provided by the human at install time or via environment variables.

**Profile field: `plugin.external_services`.** Array of external service dependencies captured during the Option C interview (Section 6.4):

```json
{
  "name": "google_drive",
  "mcp_server": "google-drive",
  "auth": "oauth",
  "env_vars": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
}
```

Each entry records the service name, the MCP server that bridges it, the authentication method (`"api_key"`, `"oauth"`, or `"none"`), and the environment variables the human must provide. Pre-flight checks (Section 6.1.2) verify these env vars are set on `svp resume`.

**Stage 5 assembly for plugin projects:**

The git repo agent uses the `claude_code_plugin` assembler which produces:
- Plugin directory structure: `svp/` (or project name) containing `.claude-plugin/plugin.json`, `agents/`, `commands/`, `hooks/`, `skills/`, `scripts/`
- `.mcp.json` at plugin root (if MCP servers declared in profile or plugin.json)
- `.lsp.json` at plugin root (if LSP servers declared in profile or plugin.json)
- `hooks.json` at plugin root, or hooks inlined in `plugin.json` (per plugin preference)
- Marketplace catalog at repo root: `.claude-plugin/marketplace.json`
- Proper file placement per Claude Code plugin conventions
- All Python files assembled as normal (proper module paths, `__init__.py`, `pyproject.toml`) -- the profile's `source_layout` field governs only this Python code restructuring, not the plugin directory structure
- Markdown, bash, and JSON files placed in their correct directories without transformation
- All path references rewritten to use `${CLAUDE_PLUGIN_ROOT}` for bundled assets

**Quality Gate C additions for plugin projects:**

Gate C (Stage 5 structural validation) adds when `archetype` is `"claude_code_plugin"`. **(CHANGED IN 2.2)** Optional plugin directories (`agents/`, `skills/`, `hooks/`, `commands/`) that are absent or empty pass Gate C validation silently — validation items apply only to files that exist. A valid plugin may have zero agents, zero skills, zero hooks, or zero commands:
1. **Plugin manifest schema validation:** `plugin.json` validates against full schema per Section 40.7.1 (required: `name`, `description`, `version`, `author`; optional: `mcpServers`, `lspServers`, `hooks`, `commands`, `agents`, `skills`, `outputStyles`, `tools`)
2. **MCP server config validation:** If `.mcp.json` exists or `mcpServers` is inline, validates against schema per Section 40.7.2 -- transport-specific required fields, valid transport types, env var `${...}` syntax
3. **LSP server config validation:** If `.lsp.json` exists or `lspServers` is inline, validates against schema per Section 40.7.3 -- `command` required per entry, valid env var syntax
4. **Skill frontmatter validation:** Each `SKILL.md` in `skills/` has valid YAML frontmatter per Section 40.7.4 -- fields from recognized set, `allowed-tools` entries are valid tool names, `model` values are valid
5. **Agent definition frontmatter validation:** Each `.md` file in `agents/` has valid YAML frontmatter per Section 40.7.6 -- fields from recognized set, `disallowedTools` valid, referenced skills exist
6. **Hook definition validation:** Hook definitions (in `hooks.json` or inline) conform to schema per Section 40.7.5 -- valid event names, valid hook types, proper matcher syntax
7. **Hook script syntax validation:** Each `.sh` file in `hooks/` passes `bash -n` syntax check; each `.py` hook passes ruff check
8. **Slash command format check:** Each `.md` file in `commands/` has required structure
9. **Marketplace manifest validation:** `marketplace.json` has required fields (`name`, `owner`, `plugins` array with valid entries per Section 40.7.8)
10. **Environment variable reference consistency:** All `${...}` references in MCP configs, hook scripts, and manifest resolve to documented env vars or standard plugin variables (`CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`)
11. **No hardcoded absolute paths:** No file path references in `plugin.json`, hook scripts, or MCP/LSP configs contain hardcoded absolute paths -- all must use `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}`
12. **Cross-reference integrity:** Skill references in agent definitions resolve to existing skills in `skills/`; MCP server references in hooks resolve to declared servers; command references in manifest resolve to existing command files
13. **Plugin installability check:** The assembled plugin directory can be registered via `claude plugin marketplace add` and installed via `claude plugin install`

#### 40.7.10 Plugin Archetype Test Project: `examples/gol-plugin/` (NEW IN 2.2)

The GoL spec generator plugin demonstrates the `"claude_code_plugin"` archetype for oracle testing.

**Architecture:**
- **3 implementation agents:** Each agent receives the GoL specification and produces a Python implementation using a different strategy (naive grid iteration, hashlife algorithm, sparse set representation). Agent definitions are markdown files delivered to `agents/`.
- **1 evaluation agent:** Receives all three implementations, benchmarks each against fixed quality criteria (execution speed on standard patterns, cyclomatic complexity, peak memory usage, code readability score). Produces a ranked evaluation report. Agent definition delivered to `agents/`.
- **Orchestration skill:** Drives the generate → evaluate → report workflow. Skill definition delivered to `skills/gol-evaluator/SKILL.md`.
- **3 commands:** `/gol:generate` (invoke implementation agents), `/gol:evaluate` (invoke evaluation agent), `/gol:report` (display results). Command definitions delivered to `commands/`.
- **Hooks:** Write authorization for agent output files. Hook configuration delivered to `hooks/`.
- **Plugin manifest:** `plugin.json` with agent, skill, command, and hook registrations.

**Fixed criteria (no configuration):** Speed is measured as generations-per-second on a 100x100 grid for 1000 steps. Complexity is cyclomatic complexity via radon. Memory is peak RSS via tracemalloc. Readability is a composite of line count, comment ratio, and function size. Weights are fixed: speed 40%, complexity 25%, memory 20%, readability 15%.

**Approximate unit scope:** ~6-8 units covering: core evaluation logic (Python), agent definitions (markdown), skill definition (markdown), command definitions (markdown), hook configurations (JSON/bash), plugin manifest (JSON), GoL implementations (Python, embedded as test fixtures).

**Pipeline paths exercised:** Stage 0 Option C archetype selection, Stage 3 multi-artifact-type dispatch (Python + markdown + bash + JSON per Section 40.7.4), plugin-specific quality gates (Section 40.7.5), Stage 5 plugin assembly (Section 40.7.6), plugin manifest validation, structural validation of all plugin artifact types.

---

## 41. Hard Stop Protocol (NEW IN 2.2)

When SVP N has a bug that prevents forward progress during SVP N+1 build:

1. **Hard stop.** No agent compensation. No workarounds. The pipeline is broken.
2. **Save the salvageable.** The spec (if approved), blueprint (if approved), profile, and all completed units are valid artifacts.
3. **Produce bug analysis.** Structured report: exact failure point, error output, root cause hypothesis, suggested fix, affected SVP N unit, whether fix changes contracts or only implementation.
4. **Switch to SVP N working directory.** Fix the bug using `/svp:bug`. Run regression tests. Update lessons learned.
5. **Reload the updated plugin.** SVP N is now patched.
6. **Restart SVP N+1 build from last checkpoint.** Use `svp restore` with saved artifacts.
7. **Arrive at the crisis point.** Proceed on the happy path if fixed.
8. **Repeat if fix failed.** New hard stop, new analysis, new fix cycle.

**Operational rules:**
- **Never compensate.** If the agent could work around the bug, the bug still exists and will bite again.
- **Bug analysis is a deliverable.** Transfers directly into SVP N's debug loop.
- **Checkpoint granularity.** `svp restore` restores from spec + blueprint + profile. Units will be rebuilt.
- **Lessons learned are cumulative.** Every SVP N bug found during SVP N+1 build is appended to lessons learned.

---

## 42. Unit Architecture (NEW IN 2.2)

### 42.1 Overview (Reference Decomposition)

The reference decomposition below illustrates one valid organization of SVP 2.2's behavioral requirements into units. The blueprint author determines the actual unit count and boundaries — the spec constrains behavior, not decomposition granularity.

**Unit splits:**
| SVP 2.1 Unit | SVP 2.2 Units | Reason |
|-------------|---------------|--------|
| Unit 1 (config + profile + toolchain) | Units 1, 2, 3, 4 | Adding language registry, restructured profile, and toolchain reader would exceed any reasonable unit size. Each split unit has a clean, single responsibility. |
| Unit 6 (stub generation) | Units 9, 10 | Signature parsing and stub generation are independent dispatch points. Different languages may share a parser but not a generator. |
| Unit 10 (routing + quality gates) | Units 14, 15 | Quality gate execution is its own dispatch point. Separating it reduces routing complexity. |

**New unit:** Unit 2 (Language Registry).

### 42.2 Reference Dependency DAG

```
Unit 1  (Core Configuration)
  |
Unit 2  (Language Registry)           <- depends on 1
  |
Unit 3  (Profile Schema)             <- depends on 1, 2
Unit 4  (Toolchain Reader)           <- depends on 1, 2
  |
Unit 5  (Pipeline State)             <- depends on 1, 2
  |
Unit 6  (State Transitions)          <- depends on 5
  |
Unit 7  (Ledger Management)          <- depends on 1
  |
Unit 8  (Blueprint Extractor)        <- depends on 1, 2
  |
Unit 9  (Signature Parser Dispatch)  <- depends on 2, 8
  |
Unit 10 (Stub Generator Dispatch)    <- depends on 2, 8, 9
  |
Unit 11 (Infrastructure Setup)       <- depends on 1, 2, 3, 4, 8
  |
Unit 12 (Hint Prompt Assembler)      <- depends on 7
  |
Unit 13 (Task Preparation)           <- depends on 1, 2, 3, 4, 5, 7, 8, 12
  |
Unit 14 (Routing + Test Execution)   <- depends on 1, 2, 4, 5, 6
  |
Unit 15 (Quality Gate Execution)     <- depends on 2, 4
  |
Unit 16 (Command Logic Scripts)      <- depends on 1, 4, 5
  |
Unit 17 (Hook Enforcement)           <- depends on 2, 5
  |
Unit 18 (Setup Agent Definition)     <- depends on 2, 3
Unit 19 (Blueprint Checker Def)      <- depends on 2
Unit 20 (Construction Agent Defs)    <- depends on 2
Unit 21 (Diagnostic/Redo Agent Defs) <- (none)
Unit 22 (Support Agent Defs)         <- (none)
Unit 23 (Utility Agent Defs + Assembly Dispatch) <- depends on 1, 2, 3, 4, 5
Unit 24 (Debug Loop Agent Defs)      <- (none)
  |
Unit 25 (Slash Command Files)        <- (none, markdown)
Unit 26 (Orchestration Skill)        <- (none, markdown)
  |
Unit 27 (Project Templates)          <- depends on 2
  |
Unit 28 (Plugin Manifest + Structural Validation + Compliance Scan) <- depends on 1, 2, 3
  |
Unit 29 (Launcher)                   <- depends on 2
```

### 42.3 Reference Topological Build Order

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15
→ 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24 → 25 → 26 → 27 → 28 → 29
```

All dependencies point backward. No forward edges.

### 42.4 Reference Unit Responsibilities

Brief description of each unit's role (single paragraph each):

- **Unit 1 (Core Configuration):** `svp_config.json`, `ARTIFACT_FILENAMES`, blueprint discovery. Unchanged from SVP 2.1.
- **Unit 2 (Language Registry -- NEW):** `LANGUAGE_REGISTRY`, validation guardrails, `RunResult`/`QualityResult` types, `get_language_config()`. In SVP 2.2, exactly two full entries (Python, R) plus one component entry (Stan).
- **Unit 3 (Profile Schema -- restructured):** Language-keyed `DEFAULT_PROFILE`, `load_profile` with 2.1 migration, `validate_profile` with per-language validation, language-aware accessors.
- **Unit 4 (Toolchain Reader -- restructured):** `load_toolchain` with optional language parameter, three-layer separation.
- **Unit 5 (Pipeline State):** All SVP 2.1 fields plus `primary_language`, `component_languages`, `pass` (int or null), `pass2_nested_session_path` (string or null), `deferred_broken_units` (array of int) **(CHANGED IN 2.2)**.
- **Unit 6 (State Transitions):** Validates preconditions and executes all state transitions. Exports: advance_stage, advance_sub_stage, complete_unit, advance_fix_ladder, increment_red_run_retries, reset_red_run_retries, increment_alignment_iteration, rollback_to_unit, restart_from_stage, version_document (with companion_paths support), enter_debug_session, authorize_debug_session, complete_debug_session, abandon_debug_session, update_debug_phase, set_debug_classification, enter_redo_profile_revision, complete_redo_profile_revision, enter_alignment_check, complete_alignment_check, enter_quality_gate, advance_quality_gate_to_retry, quality_gate_pass, quality_gate_fail_to_ladder, set_delivered_repo_path. All functions take PipelineState and return new PipelineState via deep copy. Input state is never mutated. Pre/post-conditions are contracted in the blueprint. **(CHANGED IN 2.2)** Adds pass management functions for E/F self-builds: `enter_pass_1` (set `pass: 1` at E/F pipeline start), `enter_pass_2` (set `pass: 2` when Pass 2 begins), `clear_pass` (set `pass: null` after Pass 2 completion), `mark_unit_deferred_broken` (add unit to `deferred_broken_units`), `resolve_deferred_broken` (remove unit from `deferred_broken_units`). All other transitions are unchanged from SVP 2.1 — language-invariant.
- **Unit 7 (Ledger Management):** Unchanged.
- **Unit 8 (Blueprint Extractor):** `UnitDefinition` gains `languages` field. `detect_code_block_language()` NEW. **(NEW IN 2.2) Blueprint Extractor language detection path handling.** `detect_code_block_language()` must use `get_blueprint_dir()` from Unit 1 to resolve blueprint file paths. It reads code fence tags from BOTH `blueprint_prose.md` (Tier 1) and `blueprint_contracts.md` (Tier 2/3). No hardcoded paths. No assumptions about file location. The function populates `UnitDefinition.languages` but does NOT interact with `build_unit_context()` or the `include_tier1` parameter -- language detection is a metadata operation, not a content loading operation.
- **Unit 9 (Signature Parser Dispatch -- NEW split):** `SIGNATURE_PARSERS` dispatch table. Python parser wraps `ast.parse()`.
- **Unit 10 (Stub Generator Dispatch -- NEW split):** `STUB_GENERATORS` dispatch table. Stub sentinel from registry.
- **Unit 11 (Infrastructure Setup):** Language-dispatch for environment creation, quality tool installation, import validation.
- **Unit 12 (Hint Prompt Assembler):** Unchanged.
- **Unit 13 (Task Preparation):** `build_language_context()` NEW. Language context injected into all agent prompts. **(CHANGED IN 2.2)** `ALL_GATE_IDS` must include all 31 gate IDs: the 23 from SVP 2.1 plus 8 new in 2.2 (`gate_4_3_adaptation_review`, `gate_7_a_trajectory_review`, `gate_7_b_fix_plan_review`, `gate_pass_transition_post_pass1`, `gate_pass_transition_post_pass2`, `gate_3_completion_failure`, `gate_4_1a`, `gate_6_1a_divergence_warning`).
- **Unit 14 (Routing + Test Execution -- split):** `TEST_OUTPUT_PARSERS` dispatch table. All routing logic unchanged.
- **Unit 15 (Quality Gate Execution -- NEW split):** `QUALITY_RUNNERS` dispatch table. Gate composition from language-specific toolchain.
- **Unit 16 (Command Logic):** Unchanged.
- **Unit 17 (Hook Enforcement):** Write paths from language registry. Stub sentinel from registry.
- **Unit 18 (Setup Agent Definition):** Area 0 language dialog. Language-keyed profile output. **(CHANGED IN 2.2)** Option C extended interview populates `plugin.external_services`, `plugin.hook_events`, `plugin.skills`, and `plugin.mcp_servers` in the profile (see Section 40.7.9 and Section 6.4 Option C).
- **Unit 19 (Blueprint Checker):** Language registry completeness validation. Profile language-key validation.
- **Unit 20 (Construction Agent Defs):** Agent prompts reference `LANGUAGE_CONTEXT`. Language-conditional guidance.
- **Unit 21 (Diagnostic/Redo Agent Defs):** Unchanged.
- **Unit 22 (Support Agent Defs):** Unchanged.
- **Unit 23 (Utility Agent Defs + Assembly Dispatch):** `PROJECT_ASSEMBLERS` dispatch table. Language-keyed delivery config generation. Oracle agent definition.
- **Unit 24 (Debug Loop Agent Defs):** Unchanged.
- **Unit 25 (Slash Commands):** Unchanged.
- **Unit 26 (Orchestration Skill):** Three-layer model explanation. Language context flow guidance.
- **Unit 27 (Project Templates):** Language-specific toolchain files. Delivery quality templates. `claude_md.py` with language note.
- **Unit 28 (Plugin Manifest + Validation + Compliance):** `COMPLIANCE_SCANNERS` dispatch table. `validate_dispatch_exhaustiveness()`. **(CHANGED IN 2.2)** Full `plugin.json` schema validation per Section 40.7.1, MCP config validation per Section 40.7.2, LSP config validation per Section 40.7.3, skill frontmatter validation per Section 40.7.4, hook definition validation per Section 40.7.5, agent definition frontmatter validation per Section 40.7.6, environment variable reference consistency, absolute path detection, and cross-reference integrity (skills↔agents, MCP↔hooks, commands↔manifest).
- **Unit 29 (Launcher):** Language runtime pre-flight checks. `_DEFAULT_REGISTRY` sync with Unit 2. **(CHANGED IN 2.2)** Unit 29 gains `--plugin-path` argument for `svp restore` mode. When provided, sets `SVP_PLUGIN_ROOT` environment variable in the launched Claude Code subprocess, overriding default plugin discovery. Used by the oracle for nested session isolation.

---

## 43. Self-Build Protocol (NEW IN 2.2)

### 43.1 Overview (CHANGED IN 2.2)

SVP self-builds (SVP N building SVP N+1) use dedicated archetypes: `"svp_language_extension"` (Option E) or `"svp_architectural"` (Option F). The profile fields `is_svp_build` and `self_build_scope` are derived from the archetype — never independently set. Every self-build follows a two-pass bootstrap protocol. The archetype determines risk posture and verification requirements.

**Foundational semantics.** Pass 1 is scaffolding — it builds the builder (SVP N+1), but its output is NOT the delivery. Pass 2 is the real build — SVP N+1 rebuilds itself through its own pipeline, and the Pass 2 output is the authoritative deliverable. E and F archetypes are identical through Pass 2 (both follow the same two-pass mechanics). They diverge only at Stage 7 (oracle), where E tests the product (new language capability) and F tests the machinery (routing, state, gates). See Section 3.33 for the oracle E-mode/F-mode design principle.

**E/F visibility.** Options E and F are hidden from normal users in the archetype selector (Section 6.4). They are accessible only through an advanced user access path. Normal users building Python, R, plugin, or mixed projects never see these options.

This section operationalizes the Self-Hosting Invariant (Section 33), relates to the Hard Stop Protocol (Section 41) for SVP N bugs during Pass 1, defines the orchestrator break-glass protocol (Section 43.9) for Pass 1/Pass 2 failures, and positions the Oracle (Section 35) as an optional post-Pass-2 verification tool. See also: Section 3.6 (routing invariants for `break_glass` action type and Pass 2 two-branch entries), Section 22.4 (pipeline state extensions for `pass` field and Pass 2 sub-stages), Section 18.4 (new gate IDs for pass transitions).

### 43.2 Two-Pass Bootstrap Protocol (CHANGED IN 2.2)

Every SVP self-build completes two passes before it is considered delivered. Pass 1 produces scaffolding. Pass 2 produces the deliverable.

**Pass 1 (Scaffolding — build the builder):**
- SVP N builds SVP N+1 through the standard pipeline (Stages 0–5).
- SVP N's dispatch tables, routing, quality gates validate SVP N+1's code.
- Output: Pass 1 deliverable. This is scaffolding — a tool for building, NOT the delivered product.
- On SVP N bug discovered during Pass 1: Hard Stop Protocol (Section 41).
- On Pass 1 failures that exhaust normal retry paths: orchestrator break-glass protocol (Section 43.9). The orchestrator logs bugs as lessons-learned, routes around failures with human guidance, and continues toward Pass 1 completion.

**Post-Pass-1 transition gate.** After Pass 1's Stage 5 completes, the routing script presents a structured bug summary (from the build log and lessons-learned infrastructure) to the human. The human chooses:
- **FIX BUGS (Stage 6):** Enter `/svp:bug` to fix bugs discovered during Pass 1. After Stage 6 completes, return to this transition gate. Pass 2 is available after Stage 6.
- **PROCEED TO PASS 2:** Begin the Pass 2 nested session.
- **Stage 7 is NOT offered at this point.** Stage 7 requires Pass 2 completion.

See Section 43.7 for the transition gate specification and Section 43.8 for Pass 2 nested session mechanics.

**Pass 2 (Production — the real build):**
- The orchestrator (SVP N) drives a nested Claude Code session with SVP N+1 installed as the active plugin.
- The nested session runs `svp restore --plugin-path <pass1-deliverable>/svp/ --skip-to pre-stage-3` with the spec and blueprint carried forward from Pass 1 (Stages 0–2 skipped).
- SVP N+1's own pipeline validates SVP N+1's own code through Stages 3–5.
- Gate handling depends on archetype: E auto-approves all gates (routing is unchanged, same pipeline mechanics). F surfaces all gates transparently to the human (pipeline mechanics may have changed). See Section 43.8.
- The orchestrator monitors the nested session via stdio piping (same mechanism as oracle, Section 35.17).
- On Pass 2 failures: orchestrator break-glass protocol (Section 43.9), same as Pass 1. NOT a Hard Stop — Hard Stop is exclusively for SVP N bugs during Pass 1.
- Output: Pass 2 deliverable. This is the authoritative delivery.

**Post-Pass-2 deliverable handling.** When Pass 2's Stage 5 completes:
- `delivered_repo_path` in pipeline state points to Pass 2's output.
- No reference to Pass 1's deliverable is retained in pipeline state. Pass 1's workspace is a build artifact only.
- The pipeline state is then identical to any A-D archetype post-delivery, with the sole difference that Stage 7 (`/svp:oracle`) is additionally available because `is_svp_build` is true.

**Post-Pass-2 transition gate.** After Pass 2's Stage 5 completes, the routing script presents a structured bug summary to the human. The human chooses:
- **FIX BUGS (Stage 6):** Enter `/svp:bug` to fix bugs in the Pass 2 deliverable.
- **RUN ORACLE (Stage 7):** Enter `/svp:oracle` for pipeline acceptance testing.

Stage 6 and Stage 7 operate on the Pass 2 deliverable exactly as they would on any other delivered project. They find bugs, write regression tests, patch files (including spec and blueprint if necessary), and activate Stage 5 reassembly for any correction.

**Pass 2 Completion Criteria:**
- All units green under SVP N+1's own pipeline
- All regression tests pass
- Structural validation and compliance scan pass
- No `deferred_broken` units remain (all must be resolved before Pass 2 completes)

**Post-Pass-2: Oracle (optional).** After Pass 2 succeeds, `/svp:oracle` (Section 35) is available for product-level verification. The oracle operates in E-mode (product testing) or F-mode (machinery testing) depending on the archetype (Section 3.33). The oracle is NOT part of the bootstrap — it is a separate, optional post-delivery tool that runs on the clean Pass 2 deliverable.

### 43.3 Scenario 1: Language Extension Build (CHANGED IN 2.2)

`self_build_scope: "language_extension"` — **LOW RISK**

Only the 5 artifacts from Section 40.5 change (registry entry, toolchain JSON, setup interview path, dispatch implementations, spec docs). Pipeline mechanism code (Sections 10, 11, 12) is unchanged — it dispatches through the registry.

- Pass 1 is safe: the old pipeline validates through existing dispatch infrastructure
- Pass 2 uses unchanged routing: the orchestrator auto-approves all gates (Section 43.8)
- **Orchestrator posture: Standard.** Normal oversight protocols apply. Break-glass on failure (Section 43.9).
- **Invariant:** If any pipeline mechanism code changes, the build must be reclassified to `"architectural"`

**E build scope.** An Option E build covers one or more of the following scopes, declared during setup (Section 6.4):

1. **Standalone language** — add a new language (e.g., Julia) with no mixed environment. After delivery, standalone projects in the new language work, but mixed projects pairing this language with others do not.
2. **Mixed pair** — add a mixed environment for a specific language pair (e.g., Julia/Python). Requires the standalone language already exists. After delivery, mixed projects with that specific pair work.
3. **Both** — add both a standalone language and one or more mixed pairs in a single build.

Each scope determines which test projects the oracle requires (see below).

**Language test project (Stage 1 responsibility).** The stakeholder spec for a language extension self-build must include test project(s) matching the declared build scope. Test projects are GoL re-expressions — the same Game of Life game logic, adapted to the new language context:

- **Standalone language scope:** One test project — GoL re-expression in the new language (e.g., "Implement the Game of Life in Julia"). Same acceptance criteria as the Python GoL, targeting the new language's toolchain and idioms.
- **Mixed pair scope:** One test project per pair — GoL split across the two languages (e.g., "R computes the GoL engine, Python renders with a GUI and scroll bar"). The spec describes how the languages divide the work and communicate.
- **Both scope:** All of the above — standalone GoL plus mixed GoL(s).

These are not novel specs written from scratch. The GoL spec already exists and is battle-tested. The human adapts it to the new language context — the game is known, the requirements are known, what's new is the language-specific decomposition. The blueprint includes units that produce these test project artifacts, which are bundled in the deliverable under `examples/<test_project>/`. After Pass 2, the oracle uses these test projects — not the Python Game of Life — to verify the new language pipeline works end-to-end.

**Pass 2 specifics for language extension:**
- The orchestrator auto-approves all gates (routing unchanged)
- Registry validation confirms the new language entry is complete
- Dispatch exhaustiveness (Section 3.26) confirms all six tables have entries for the new language
- Behavioral equivalence: all existing-language regression tests pass unchanged
- Oracle verification (post-Pass-2): runs the build-scope-matching test project(s) through the full pipeline (E-mode, Section 3.33)

### 43.4 Scenario 2: Architectural Change Build (CHANGED IN 2.2)

`self_build_scope: "architectural"` — **HIGH RISK**

SVP-current CANNOT validate what it doesn't implement. This is a blind spot by construction. Pass 1 produces code that passes old tests/types/gates but hasn't been exercised under the new architecture's emergent behavior. Pass 2 is where bugs surface — and these can be self-reinforcing (broken routing corrupts the build of routing code).

**Orchestrator posture: Elevated.** Additional detection checklists beyond standard protocols. These follow the same pattern as the per-stage orchestrator oversight protocols (Sections 8.5, 10.15, 11.6, 12.17): they are detection checklists evaluated by the orchestrator between action cycles, NOT human gates. They do not have gate IDs and do not appear in `GATE_VOCABULARY`. If a checkpoint detects an issue (e.g., post-Stage-2 reveals that pipeline mechanism code changed but scope is classified as `"language_extension"`), the orchestrator escalates to the human via break-glass protocol (Section 43.9) for reclassification or acknowledgment.

1. **Post-Stage-2 checkpoint:** Summary of which pipeline mechanisms change vs. are preserved. If mechanism code changes detected but scope is `"language_extension"`, flag reclassification need.
2. **Every-5-units checkpoint (Stage 3):** Cross-unit consistency check focused on mechanism interactions. Detect units whose Tier 2 contracts export functions consumed by routing/state/quality modules.
3. **Post-Stage-4 checkpoint:** Flag which integration tests exercise new architecture vs. inherited behavior. Missing coverage is flagged.
4. **Post-Stage-5 checkpoint (before Pass 2):** Checklist — (a) what changed, (b) blind spot coverage, (c) what Pass 2 will verify that Pass 1 could not.

**No separate test project for architectural changes.** The only meaningful verification for architectural changes is SVP rebuilding itself — that is what Pass 2 does. A separate test project (Game of Life, etc.) exercises language dispatch, not pipeline architecture. The oracle is still available post-Pass-2 for machinery verification (F-mode, Section 3.33).

**Pass 2 gate handling for architectural changes.** Unlike E builds (where the orchestrator auto-approves all gates), F builds surface all gates from the nested session transparently to the human. The pipeline mechanics may have changed, so human judgment is needed at every gate. The orchestrator acts as a transparent window — it presents the nested session's gate prompts unmodified.

**Self-reinforcing failure detection (Pass 2).** If a unit implementing routing/state/quality logic fails during its own pipeline processing, the orchestrator flags this as a potential self-reinforcing loop. **(CHANGED IN 2.2) Detection guidance for the blueprint author:** Units whose Tier 2 contracts export functions consumed by the routing module (Unit 14), state transition module (Unit 6), quality gate module (Unit 15), or agent orchestration code paths should be flagged with a `machinery: true` metadata tag in the blueprint. During Pass 2, the orchestrator checks this tag when a unit fails — if `machinery: true`, the failure is flagged as potentially self-reinforcing and escalated via break-glass. This is handled by the orchestrator break-glass protocol (Section 43.9) — NOT by a Hard Stop. Hard Stop is exclusively for SVP N bugs during Pass 1. During break-glass, the orchestrator presents diagnostics to the human, logs the issue as a lessons-learned entry, and together they route around the failure (mark the unit `deferred_broken`, retry with guidance, or escalate to restart). The goal is to push through to a deliverable state, then use Stage 6 and Stage 7 to systematically fix the bugs.

**Invariant:** `self_build_scope` must be `"architectural"` whenever any file in routing, state transition, quality gate execution, or agent orchestration code paths changes. This is a human-asserted classification.

### 43.5 Mixed Scope — Not Supported

Mixed scope (combining language extension with architectural changes in a single self-build) is **not supported and strongly discouraged**. When Pass 2 fails, you cannot determine whether the bug is in the new language artifacts or the new pipeline architecture, making failure isolation impossible.

**Required approach:** Sequence the changes as two separate self-builds:
1. First self-build: `self_build_scope: "language_extension"` — add the new language. Complete both passes. Deliver SVP N+1.
2. Second self-build: `self_build_scope: "architectural"` — change pipeline architecture using SVP N+1 as the builder. Complete both passes. Deliver SVP N+2.

If the setup agent determines that a self-build requires both language extension and architectural changes, it **rejects the scope** and instructs the human to split the work into sequential builds. It does not proceed.

### 43.6 Relationship to Existing Sections (CHANGED IN 2.2)

- **Section 3.6 (Maximally Constrained Orchestration):** Defines the `break_glass` action type (Section 43.9), orchestrator self-escalation rule, `deferred_broken` unit status, and Pass 2 two-branch routing entries.
- **Section 3.33 (Oracle E-Mode/F-Mode Split):** Design principle for oracle mode selection based on archetype.
- **Section 18.4 (Gate Vocabulary):** New gate IDs: `gate_pass_transition_post_pass1`, `gate_pass_transition_post_pass2`.
- **Section 22.4 (Pipeline State):** New fields: `pass`, `pass2_nested_session_path`, `deferred_broken_units`. New sub-stages: `pass_transition`, `pass2_active`.
- **Section 33 (Self-Hosting Invariant):** States the invariant; Section 43 operationalizes it via the two-pass bootstrap. Pass 1 produces scaffolding; Pass 2 produces the deliverable.
- **Section 35 (Oracle):** Available after Pass 2 only, not part of the bootstrap. E-mode (product testing) or F-mode (machinery testing) based on archetype.
- **Section 40.5 (5-Artifact Recipe):** Unchanged. Section 43.3 wraps it in self-build context.
- **Section 41 (Hard Stop):** Invoked during Pass 1 for SVP N bugs only. Pass 2 failures use the orchestrator break-glass protocol (Section 43.9), NOT Hard Stop.

### 43.7 Post-Stage-5 Transition Gate (NEW IN 2.2)

For E/F archetypes, the post-Stage-5 routing is different from standard archetypes (A-D). Instead of immediately offering Stage 6 and (optionally) Stage 7, the routing script presents a pass-aware transition gate.

**After Pass 1's Stage 5 completes:**

The routing script reads the build log and lessons-learned entries accumulated during Pass 1 and presents a structured bug summary to the human. The summary includes: units that encountered failures, units marked `deferred_broken`, lessons-learned entries written during break-glass events, and any routing anomalies detected. The human chooses:

- **PROCEED TO PASS 2:** Begin the Pass 2 nested session (Section 43.8). Available directly after Stage 5 or after Stage 6 fixes.
- **FIX BUGS (Stage 6):** Enter `/svp:bug` to fix discovered bugs. After Stage 6 completes, the routing script returns to this transition gate.

Stage 7 (`/svp:oracle`) is NOT offered after Pass 1. The oracle requires a clean Pass 2 deliverable.

Gate ID: `gate_pass_transition_post_pass1`. Response options: `PROCEED TO PASS 2`, `FIX BUGS`. **(CHANGED IN 2.2) Deferred_broken constraint:** If `deferred_broken_units` is non-empty, the bug summary prominently lists the deferred units. PROCEED TO PASS 2 is NOT offered until `deferred_broken_units` is empty — the human must select FIX BUGS to resolve them first.

**After Pass 2's Stage 5 completes:**

**(NEW IN 2.2 — Bug S3-55) Workspace artifact synchronization.** Before presenting the transition gate, the routing script automatically synchronizes accumulated artifacts from the Pass 1 workspace (regression tests, lessons learned, spec amendments) into the Pass 2 workspace. This ensures Stage 6 bug fixing and Stage 7 oracle have access to all historical artifacts. The Pass 1 workspace path is derived from the Pass 2 workspace name by removing the `-pass2` suffix. The sync is idempotent (guarded by `.svp/pass1_sync_complete` marker). See Section 43.8 for details.

The routing script then presents a bug summary for the Pass 2 build. At this point, `delivered_repo_path` points to the Pass 2 output and the pipeline state is identical to any A-D archetype post-delivery. The human chooses:

- **FIX BUGS (Stage 6):** Enter `/svp:bug` to fix bugs in the Pass 2 deliverable. Stage 6 operates on the Pass 2 deliverable exactly as it would on any other delivered project — it finds bugs, writes regression tests, patches files (including spec and blueprint if necessary), and activates Stage 5 reassembly for any correction.
- **RUN ORACLE (Stage 7):** Enter `/svp:oracle` for pipeline acceptance testing.

Gate ID: `gate_pass_transition_post_pass2`. Response options: `FIX BUGS`, `RUN ORACLE`. **(CHANGED IN 2.2) Deferred_broken constraint:** Same as post-Pass-1 — if `deferred_broken_units` is non-empty, RUN ORACLE is NOT offered until all deferred units are resolved via FIX BUGS.

### 43.8 Pass 2 Nested Session Mechanics (NEW IN 2.2)

Pass 2 is an orchestrator-driven nested session for BOTH E and F archetypes. The orchestrator (SVP N, running in the main session) creates and drives the nested session; the human does not directly interact with the nested session.

**Transition sequence:**

1. Human selects PROCEED TO PASS 2 at the pass transition gate (Section 43.7).
2. Routing script sets `pass: 2`, `sub_stage: "pass2_active"` in pipeline state.
3. Orchestrator creates a new workspace directory (sibling to the main workspace).
4. Orchestrator launches `svp restore --plugin-path <pass1-deliverable>/svp/ --skip-to pre-stage-3 --spec <spec> --blueprint-dir <blueprint> --context <context> --profile <profile>` in the new workspace. The `--skip-to pre-stage-3` argument initializes pipeline state to begin from Pre-Stage-3, carrying forward the spec and blueprint from Pass 1. This follows the same `svp restore` semantics defined in Section 6.1.1.
5. Orchestrator launches a nested Claude Code session in the Pass 2 workspace with plugin isolation configured, ensuring the nested session uses SVP N+1 (the Pass 1 deliverable), not SVP N (the builder). Same isolation mechanism as oracle (Section 35.17).
6. Orchestrator monitors the nested session, tracking progress by reading the nested session's `pipeline_state.json`.

**Gate handling by archetype:**

- **E (language extension):** The orchestrator auto-approves all Stages 3-5 gates in the nested session (routing is unchanged, so gate outcomes are predetermined). The post-Pass-2 transition gate (`gate_pass_transition_post_pass2`) is NOT auto-approved — it is always presented to the human. The human is not prompted for other nested session gates. Break-glass on failure (Section 43.9) is the only escalation path for Stages 3-5.
- **F (architectural change):** The orchestrator surfaces all gates from the nested session transparently to the human. The orchestrator presents the nested session's gate prompts unmodified — it is a window, not a filter. Pipeline mechanics may have changed, so human judgment is needed at every gate.

**Completion:** When the nested session's Stage 5 completes, the orchestrator:

1. Captures the nested session's `delivered_repo_path`.
2. Updates the main pipeline state: `delivered_repo_path` = Pass 2's output. `pass1_workspace_path` and `pass2_nested_session_path` are cleared (set to null) — they are no longer part of pipeline state.
3. Sets `sub_stage: "pass_transition"` to present the post-Pass-2 transition gate.

After this point, the pipeline state is indistinguishable from any A-D archetype post-delivery, except `is_svp_build` is true and Stage 7 is available.

**Reuse of nested session infrastructure.** Pass 2 uses the same nested session bootstrap mechanism as the oracle (Section 35.17). The mechanisms are identical; the purposes are distinct:
- **Pass 2 (production):** The nested session's output IS the deliverable. Artifacts are kept.
- **Oracle (verification):** The nested session's output is disposable (simulation-only constraint, Section 3.22).

### 43.9 Orchestrator Break-Glass Protocol (NEW IN 2.2)

During Pass 1 or Pass 2 of an E/F self-build, failures that exhaust normal retry paths are handled by the orchestrator break-glass protocol. This replaces the Hard Stop approach for Pass 2 failures (Hard Stop is exclusively for SVP N bugs discovered during Pass 1).

**Trigger mechanisms:**

1. **Routing script trigger:** The routing script emits a `break_glass` action type when known exhaustion conditions are met (e.g., fix ladder exhausted for a unit, assembly failure after maximum retries, quality gate failure after retry cycle). This is an explicit, deterministic trigger.
2. **Orchestrator self-escalation:** The orchestrator independently detects loop conditions — the same action dispatched 3 or more consecutive times with no pipeline state change. When detected, the orchestrator self-escalates to break-glass mode without waiting for the routing script. This is a narrow, bounded safety valve for routing script bugs (which are likely during E/F builds, per Section 43.4).

**Permitted actions in break-glass mode:**

- Present failure diagnostics to the human (what failed, how many times, what the last error was).
- Write a lessons-learned entry using the existing lessons-learned infrastructure (Section 12.18). One channel, multiple consumers — the same entry is consumed by Stage 6 triage, oracle trajectory planning, and future builds.
- Mark the failing unit as `deferred_broken` in pipeline state. A `deferred_broken` unit is excluded from the current pass's completion check but must be resolved before the pass is considered complete (either fixed via Stage 6 or explicitly acknowledged by the human).
- Retry the failing operation with human-provided guidance (e.g., the human suggests a different implementation approach). **(CHANGED IN 2.2) Retry bound:** At most 3 retries per unit per pass. After the 3rd retry failure for the same unit, the unit is automatically marked `deferred_broken` — further retries for that unit require a pipeline restart.
- Escalate to pipeline restart (scrap the current pass and start over). This is the "ruthless restart" option — available but never the default.

**Forbidden actions in break-glass mode:**

- Fix code directly. The orchestrator does not write implementation code.
- Modify the stakeholder spec or blueprint. These are authored through their respective agents.
- Skip stages or sub-stages. The pipeline flow is preserved even during break-glass.

**Re-entry to normal pipeline flow:** After the human decides (skip via `deferred_broken`, retry with guidance, or restart), the orchestrator writes the decision to pipeline state and resumes the six-step action cycle (Section 3.6). The routing script picks up from the new state.

### 43.10 Orchestrator Role Enforcement for Self-Builds (NEW IN 2.2)

E/F self-builds are long, complex sessions where orchestrator context degradation is a significant risk. Two additional enforcement mechanisms supplement the six mechanisms defined in Section 3.31:

**1. Claude Code skill for spec refresh at phase transitions.** A dedicated skill (invoked at session start and at each major phase transition: Pass 1 start, Pass 1 → transition gate, Pass 2 start, Pass 2 → transition gate, oracle start) forces the orchestrator to re-read the relevant spec sections for the upcoming phase. This prevents the orchestrator from operating on stale context accumulated during the previous phase. The skill restates the three orchestrator rules:
- Re-read the spec at each phase transition.
- Can only plan and delegate to subagents — never execute directly.
- Must monitor subagent output and intervene (call the human or warn the human) when the subagent deviates from spec.

**2. PostToolUse hook on Agent returns.** After any subagent returns (PostToolUse event on the Agent tool), a hook injects a monitoring reminder: "Before proceeding, verify the subagent's output against the spec sections loaded above. Flag any deviations to the human." This is defense-in-depth — the orchestrator may still fail to comply (LLM limitation), but the reminder is injected at the highest-recency position in context, maximizing compliance probability.

These mechanisms supplement (not replace) the existing enforcement architecture: CLAUDE.md (Layer 1), routing script REMINDER (Layer 2), agent terminal status lines (Layer 3), and hooks/write authorization (Layer 4).

---

## 44. Blueprint Author Verification Seed Checklist (NEW IN 2.2)

This section provides the **seed checklist** — a minimum set of verification criteria derived from hard-won build failures. The Checklist Generation Agent (Section 7.8) consumes this seed and produces a unified, project-specific checklist. The blueprint author receives only the generated checklist, not this seed directly. The generated checklist MUST include every seed item below (verbatim or with project-specific refinement) plus additional items derived from the approved spec.

**Validation rule:** After checklist generation, the orchestrator verifies that every numbered seed item below has a corresponding entry in the generated checklist. Missing seed items are a generation failure — the Checklist Generation Agent is re-invoked.

### 44.1 State Management and Routing

SC-1. Every state transition function has a contracted postcondition specifying which `pipeline_state.json` fields change and which are preserved. The blueprint defines these — the spec does not prescribe field-level mutations.

SC-2. Every state management function takes immutable state input and returns new state. The specific mechanism (deep copy, persistent data structure, etc.) is a blueprint decision.

SC-3. The complete set of state management exports is determined by the blueprint's unit decomposition. The spec defines WHAT transitions are needed (advance stage, complete unit, rollback, enter/exit debug session, etc.); the blueprint determines HOW many functions, their names, and their signatures.

SC-4. Document synchronization between workspace and delivered repo has contracted trigger points and a contracted invariant (workspace is canonical). The internal copy sequence is a blueprint decision.

### 44.2 Stub Generation and Code Generation

SC-5. Stubs are importable by the language's standard import mechanism without error. The specific mechanism for achieving importability (AST manipulation, template generation, etc.) is a blueprint decision.

SC-6. Stubs contain a machine-detectable sentinel distinguishing them from implementations. The sentinel value per language is read from the language registry. The sentinel's exact format and placement are blueprint decisions constrained by the registry value.

SC-7. Import validation confirms every extracted dependency resolves in the created environment. The specific validation command per language is a blueprint decision informed by the registry's `version_check_command`.

SC-8. Workspace directory structure follows the language registry's `source_dir` and `test_dir` values. The specific naming convention for per-unit directories is a blueprint decision derived from these registry values.

SC-9. The stub generator accepts blueprint path, unit identifier, output location, and upstream dependency list as inputs and produces importable stub files. The specific CLI interface (argument names, invocation style, environment setup) is a blueprint decision.

### 44.3 Quality Gates and Toolchain

SC-10. Quality gate tool commands are resolved from the language-specific toolchain file at runtime. Gate definitions in the blueprint specify WHICH tools run at WHICH gate; the specific flags and invocation syntax live in the toolchain file, not in blueprint contracts.

SC-11. Toolchain files contain gate compositions (ordered tool command lists per gate). The specific command templates, including language-specific flags, are toolchain data — the blueprint contracts the gate structure and dispatch, not the command content.

SC-12. Placeholder resolution in toolchain files produces fully resolved commands with no unresolved placeholders and no whitespace artifacts. The resolution algorithm is a blueprint decision; the postcondition (clean, resolved commands) is the contract.

SC-13. Delivered quality configuration files are generated from templates using the registry's `quality_config_mapping`. The specific template filenames and directory organization are blueprint decisions.

### 44.4 Parsing and Signatures

SC-14. Tier 2 signature blocks are valid, parseable syntax in their declared language. The specific parsing technology per language (AST library, regex, custom tokenizer) is a blueprint decision.

SC-15. Profile loading detects and rejects field name mismatches between profile data and schema. The specific merge/validation strategy is a blueprint decision.

### 44.5 Assembly and Delivery

SC-16. A machine-readable bidirectional mapping exists between workspace paths and delivered repository paths. The mapping is bijective and uses relative paths. The specific file format, key structure, and filename are blueprint decisions.

SC-17. Regression test import adaptation applies text replacements for all standard import forms in the target language (direct imports, qualified imports, mock/patch references). The specific set of syntactic patterns to match is a blueprint decision derived from the language's import mechanics.

SC-18. Gate C target resolution produces the correct source directory path for the active source layout. The specific resolution logic per layout is a blueprint decision derivable from the layout definitions in Section 12.8.

### 44.6 Agent Output Formats

SC-19. The diagnostic agent produces dual-format output: human-readable prose analysis and machine-parseable structured data containing three hypotheses (one per level: implementation, blueprint, spec) and a recommendation. The specific field names, section delimiters, and output schema are blueprint decisions.

### 44.7 Routing Mechanisms

SC-20. When multiple code paths converge on a single gate, the preparation script distinguishes which path reached the gate using pipeline state. The specific state field or mechanism used for path discrimination is a blueprint decision.

SC-21. Hook configuration files are functional in the project workspace after copying from the plugin source. The specific mechanism for achieving path correctness (rewriting, templating, symlinks) is a blueprint decision.

### 44.8 Oracle Infrastructure

SC-22. The nested oracle session uses ONLY the delivered SVP plugin, not the builder. The blueprint defines the isolation mechanism — the spec constrains only the invariant (delivered plugin, isolated workspace, no builder contamination).

SC-23. The nested oracle workspace's CLAUDE.md points to the delivered plugin. Which component generates it and via what template is a blueprint decision.

SC-24. Oracle directory authority rules (which operations may read/write which directories) are defined alongside the oracle specification. The blueprint determines where these rules are enforced — they are not Stage 6 concerns.

### 44.9 Orchestrator Working Memory

SC-25. Orchestrator-internal working documents (decision tracking, verification notes) serve their defined purpose (e.g., ensuring decisions are reflected in drafts). Their internal structure is an orchestrator behavioral choice, not a blueprint contract — the orchestrator is an LLM, not a coded component.

### 44.10 Checklist Completeness

SC-26. The generated checklist covers all mandatory categories defined in Section 7.8. The category list is a closed required set — the generator MAY add project-specific categories but MUST NOT omit any required category.

---

*End of specification.*
---