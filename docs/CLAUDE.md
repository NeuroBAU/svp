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

## Gate 6 — Canonical Break-Glass Path

When the human authorizes a debug session at `gate_6_0_debug_permission`,
SVP routes through `gate_6_1_mode_classification` (BUG | ENHANCEMENT).
Routing then emits action_type=`invoke_break_glass` with the mode tag.
Orchestrator (this Claude session) follows the corresponding sub-flow
below. Both modes share the existing Gate 6.0 authorization and
DEBUG_SESSION_COMPLETE terminal status.

**RULE 0: NEVER directly fix a bug or amend a contract. ALWAYS enter
plan mode first.**

### DIAGNOSE — Layer-Triage L1-L5

Systematically check each architectural layer to identify where the bug
actually lives. The symptom may appear in one layer while the root cause
lives in another. Rule out (or rule in) each layer in order.

**L1 — Reproduce the symptom**
- Run the failing test / agent / command end-to-end. Capture exact failure
  modes: stack traces, missing tokens, agent loops, wrong outputs.
- Note non-determinism (flaky tests, retry-success, environment-sensitive
  failures). If you cannot reliably reproduce, STOP and escalate to user.
- Output: a concise reproducer (test name + expected vs observed).

**L2 — Spec layer**
- Read the relevant normative spec sections (§17 routing, §18.1 statuses,
  §22.4 state, §6 setup_agent, §40 archetypes — match to symptom).
- Read Section 24 most recent related entries; check if a prior cycle
  introduced the behavior in question.
- Verdict: spec says X but you observed Y → continue to L3+. Spec is
  silent / self-contradictory → spec-layer bug (rare; usually means
  enhancement mode is the right flow, not bug mode).

**L3 — Blueprint layer**
- Read `blueprint/blueprint_contracts.md` (formal Tier-2/3) for the
  affected unit.
- Read `blueprint/blueprint_prose.md` (narrative Tier-1) for the same unit.
- Check Calls / Called-by / Package Dependencies sections for accuracy.
- Verdict: contract says X but spec says Y → blueprint-layer bug.
  Contract matches spec → continue to L4.

**L4 — Code layer**
- Find the relevant `src/unit_*/stub.py`.
- Trace data flow, control flow, state transitions through the function
  named in the contract. Check for missing branches, off-by-one, wrong
  data structures, swallowed exceptions.
- Verdict: most bugs live here. Code says X but contract says Y →
  code-layer bug.

**L5 — Test layer**
- Does the test correctly assert on the contract? Or does it lie about
  state / assert on wrong fixtures / pass for the wrong reason?
- Is regression coverage adequate? If yes, why did existing regression
  not catch this?
- Verdict: test-layer bug often co-occurs with L4 (incorrect test masked
  the L4 bug).

After L1-L5: state the root cause in one sentence and the layer it lives
in. Do NOT proceed to PLAN until the root layer is named.

### Bug Mode (`debug_session["mode"] == "bug"`)

For changes that ALIGN code with already-specified behavior. Specs and
contracts already say what should happen; you are restoring intended
behavior. Use this when L1-L5 found the root cause in L2-L5.

1. **DIAGNOSE** — Layer-Triage L1-L5 (see above). State root cause + layer.

2. **PLAN** the fixes in:
   - a. **SPEC** — port the change upstream to the stakeholder spec:
     - Add bug entry to Section 24 (changelog narrative). Use the rich
       format: Symptom / Root cause / Surface area / Resolution / Pattern
       (link to lessons-learned pattern number) / Detection (name
       regression test functions).
     - **MANDATORY**: Update every normative spec section whose described
       behavior changes (§6.4 / §21 setup_agent, §22.4 state, §17 routing,
       §18.1 statuses — match to layer).
     - **MANDATORY**: Update `blueprint/blueprint_prose.md` (Tier-1
       narrative) to mirror any new contract clauses in
       `blueprint/blueprint_contracts.md` (Tier-2/3).
   - b. **BLUEPRINT** — Amend contracts in affected units.
   - c. **CODE** — Fix implementation in `src/unit_*/stub.py`. Stubs are
     the single source of truth. Never edit `scripts/*.py` directly.
   - d. **EXECUTE** — Apply the code changes.
   - e. **EVALUATE** — Run tests, verify the fix works.
   - f. **LESSONS LEARNED** — Write entry in
     `references/svp_2_1_lessons_learned.md`.
   - g. **REGRESSION TESTS** — Author tests covering ALL aspects of
     the bug.
   - h. **VERIFY** — Tests pass with 0 skipped.
   - i. **DEPLOYED ARTIFACTS** — If the fix touches Units that produce
     deployed plugin artifacts (Unit 25 → `svp/commands/`, Unit 26 →
     `svp/skills/`, Unit 23 → `svp/agents/`, `svp/hooks/`), manually
     update the corresponding `.md` files in the repo svp/ directory.
   - j. **SYNC** — Run `bash sync_workspace.sh` from the workspace.
   - k. **TEST FROM BOTH** — Run pytest from BOTH workspace AND repo.

3. **EVALUATE** — All tests pass from both. Repos in sync. Clean up
   stale test artifacts.

### Enhancement Mode (`debug_session["mode"] == "enhancement"`)

For changes that ALTER intended behavior — the desired behavior is new
or different, not previously specified. Specs and/or contracts must be
amended. Use this when L1-L5 found the root cause is in L2 (spec is
silent / wants to change).

Do NOT use bug mode for these; the framing is wrong.

1. **SPEC_AMENDMENT** — Author the upstream change first.
   - Section 24 entry in rich format describing the new behavior.
   - Update normative sections (§6, §17, §18.1, §22.4, §40, etc.) for
     anything whose described behavior is changing.
   - This is MANDATORY first step (S3-169): code must not get ahead of
     spec.

2. **BLUEPRINT_AMENDMENT** — Mirror the spec change in blueprint.
   - `blueprint/blueprint_prose.md` (Tier-1 narrative summary).
   - `blueprint/blueprint_contracts.md` (Tier-2/3 formal contract clauses).
   - Both must move in lockstep.

3. **IMPLEMENTATION** — Edit `src/unit_*/stub.py` to satisfy the new
   contracts. Stubs are the single source of truth.

4. **TESTS** — Author regression tests asserting the newly-introduced
   behavior. For enhancement, regression tests document the contract
   that was just added.

5. **VERIFY** — pytest from BOTH workspace and repo. 0 fail / 0 skip.

6. **SYNC + COMMIT** — `bash sync_workspace.sh`, then commit + push.

### Choosing the entry-point

**Run break-glass directly** (default for human-initiated work):
- The bug spans multiple layers (e.g., spec + code).
- You need to investigate before knowing the root layer.
- The issue may turn out to be an enhancement.
- Multiple units may be affected.

**Call /svp:bug as a sub-tool** (narrow):
- The bug is genuinely localized to a single unit.
- The contract is well-specified and the violation is mechanical.
- You expect the fix to be a small contract-bounded change.

**Auto-dispatched /svp:bug** (routing-detected red runs):
- Routing emits this when a single Stage-3 red run is genuinely
  contract-bounded.
- The orchestrator MAY abort /svp:bug and escalate to break-glass at
  any time if scope turns out wider (G3 wires the abort path).

If /svp:bug invocation reveals scope creep (multiple units affected,
spec questions arise, behavior intent unclear), ABORT and escalate to
break-glass.

## Propagation Scope of SVP Improvements

When a break-glass cycle (or any improvement cycle) lands a change to SVP — to a stub, to an agent prompt, to the blueprint format, to the audit, to a deployed artifact — the change propagates to:

1. **SVP itself** (when self-hosted, F-mode oracle, or any future re-author of SVP's own blueprint/code).
2. **Future jobs** SVP authors (new children projects). The deployed plugin (`svp/agents/`, `svp/scripts/`, `svp/commands/`, `svp/skills/`, `svp/hooks/`) IS the propagation mechanism — new children pick up the improvement automatically when they invoke SVP.

The change does **NOT** retroactively migrate:

- **Existing children projects in-flight** (mid-pipeline). If they re-enter a stage that exercises the improved logic, they may benefit; otherwise, they continue with the state they were authored in.
- **Existing children projects shipped** (Stage 5 complete or delivered). They are static deliverables; SVP improvements do not edit them.

Children that want a retroactive improvement run their own one-time migration (or re-author through the relevant pipeline phase). SVP improvement cycles must NOT include "migrate every existing child" as in-scope work — that would entangle the cycle with arbitrarily many downstream projects and erode atomicity.

This convention applies symmetrically: every cycle's PLAN explicitly limits scope to "SVP itself + future jobs" and treats existing children as out-of-scope.
