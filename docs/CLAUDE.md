# SVP-Managed Project: svp2.2-pass2

This project is managed by the **Stratified Verification Pipeline (SVP)**. You are the orchestration layer — the main session. Your behavior is fully constrained by deterministic scripts. Do not improvise pipeline flow.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and outputs a structured action block telling you exactly what to do next. Execute its output. Do not reason about what stage the pipeline is in or what should happen next.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated:

1. **Run the routing script** → receive a structured action block.
2. **Run the PREPARE command** (if present) → produces a task prompt or gate prompt file.
3. **Execute the ACTION** (invoke agent / run command / present gate).
4. **Write the result to `.svp/last_status.txt`** (agent terminal status line or constructed command status).
5. **Run the POST command** (if present) → updates pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps.

## Verbatim Task Prompt Relay

When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.

## REMINDER

- Execute the ACTION above exactly as specified.
- When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt verbatim.
- Wait for the agent to produce its terminal status line before proceeding.
- Write the agent's terminal status line to .svp/last_status.txt.
- Run the POST command if one was specified.
- Then re-run the routing script for the next action.
- Do not improvise pipeline flow. Do not skip steps. Do not add steps.
- If the human types during an autonomous sequence, acknowledge and defer.
- You MUST NOT write to pipeline_state.json directly or batch multiple units.

## Manual Bug-Fixing Protocol (Break-Glass Mode)

**Action type `invoke_break_glass`**: routing may emit this action_type when the human authorizes a debug session and selects a mode at gate_6_1_mode_classification. Follow the Manual Bug-Fixing Protocol below; consult `state.debug_session["mode"]` ("bug" or "enhancement") for which sub-flow applies. (Mode-aware sub-flows ship in cycle G2.)

When the SVP routing mechanism is too broken to function and the human asks you to fix bugs directly, follow this protocol EXACTLY.

**RULE 0: NEVER directly fix a bug. ALWAYS enter plan mode first.**

### Bug-Fixing Cycle (repeat for each bug):

1. **DIAGNOSE** — Identify root cause. Trace through spec → blueprint → code to understand WHY.

2. **PLAN** the fixes in:
   - a. **SPEC** — port the change upstream to the stakeholder spec:
     - Add bug entry to Section 24 (changelog narrative). Use the rich format: Symptom / Root cause / Surface area / Resolution / Pattern (link to lessons-learned pattern number) / Detection (name regression test functions).
     - **MANDATORY**: Update every normative spec section whose described behavior changes. If the cycle changes setup_agent → update §6.4 / §21 setup_agent entries. If the cycle changes a state field → update §22.4. If the cycle changes routing action blocks → update §17. If the cycle changes terminal statuses → update §18.1. Failing to port the change upstream creates accumulated debt.
     - **MANDATORY**: Update `blueprint/blueprint_prose.md` (Tier-1 narrative) to mirror any new contract clauses in `blueprint/blueprint_contracts.md` (Tier-2/3). Prose is the human-readable summary; contracts is the formal specification. Keep them aligned.
   - b. **BLUEPRINT** — Amend contracts in affected units
   - c. **CODE** — Fix implementation in `src/unit_*/stub.py`. **Stubs are the single source of truth.** Never edit `scripts/*.py` directly — they are derived from stubs by `sync_workspace.sh` Step 0 (import rewriting). Fix the stub, run sync, scripts auto-update.
   - d. **EXECUTE** — Apply the code changes
   - e. **EVALUATE** — Run tests, verify the fix works
   - f. **LESSONS LEARNED** — Write entry in `references/svp_2_1_lessons_learned.md`
   - g. **REGRESSION TESTS** — Author tests covering ALL aspects of the bug
   - h. **VERIFY** — Tests pass with 0 skipped
   - i. **DEPLOYED ARTIFACTS** — If the fix touches Units that produce deployed plugin artifacts (Unit 25 → `svp/commands/`, Unit 26 → `svp/skills/`, Unit 23 → `svp/agents/`, `svp/hooks/`), manually update the corresponding `.md` files in the repo's `svp/` directory. `sync_workspace.sh` does NOT sync these. The deployed `.md` file is what Claude Code loads — the Python source is only an input to assembly.
   - j. **SYNC** — Run `bash sync_workspace.sh` from the workspace directory. This handles:
     - Step 0: Derives `scripts/*.py` from `src/unit_*/stub.py` by rewriting imports (stubs → flat modules)
     - Scripts: workspace `scripts/` ↔ repo `svp/scripts/` (newer wins)
     - Source units: workspace `src/unit_*/stub.py` ↔ repo `src/unit_*/stub.py` (newer wins)
     - Docs: workspace is authoritative → repo `docs/`, `specs/`, `blueprint/`, `references/` + Pass 1 repo
     - Tests: workspace `tests/` ↔ repo `tests/` (newer wins)
     - Use `--dry-run` to preview, `--force-workspace` or `--force-repo` to override timestamps
   - k. **TEST FROM BOTH** — Run `pytest` from BOTH the workspace AND the repo directory. Do not skip either. Failures in one but not the other indicate stale test files or permission issues.

3. **EVALUATE** — All tests pass from BOTH workspace AND repo. 0 skipped, 0 failed. Repos fully in sync. Clean up any stale test artifacts (e.g., `test_project/`, `test_restore/`) left by previous runs.

## Propagation Scope of SVP Improvements

When a break-glass cycle (or any improvement cycle) lands a change to SVP — to a stub, to an agent prompt, to the blueprint format, to the audit, to a deployed artifact — the change propagates to:

1. **SVP itself** (when self-hosted, F-mode oracle, or any future re-author of SVP's own blueprint/code).
2. **Future jobs** SVP authors (new children projects). The deployed plugin (`svp/agents/`, `svp/scripts/`, `svp/commands/`, `svp/skills/`, `svp/hooks/`) IS the propagation mechanism — new children pick up the improvement automatically when they invoke SVP.

The change does **NOT** retroactively migrate:

- **Existing children projects in-flight** (mid-pipeline). If they re-enter a stage that exercises the improved logic, they may benefit; otherwise, they continue with the state they were authored in.
- **Existing children projects shipped** (Stage 5 complete or delivered). They are static deliverables; SVP improvements do not edit them.

Children that want a retroactive improvement run their own one-time migration (or re-author through the relevant pipeline phase). SVP improvement cycles must NOT include "migrate every existing child" as in-scope work — that would entangle the cycle with arbitrarily many downstream projects and erode atomicity.

This convention applies symmetrically: every cycle's PLAN explicitly limits scope to "SVP itself + future jobs" and treats existing children as out-of-scope.
