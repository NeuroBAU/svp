# SVP 2.1 — Baseline and Rationale

**Date:** 2026-03-12
**Pipeline role:** Reference document. Not the stakeholder spec.
**Audience:** Human stakeholder, human reviewer, future maintainers.

---

## 1. What This Document Is

This document explains why SVP 2.1 exists — what SVP 2.0 gets right, where it falls short, and why the specific changes in 2.1 were chosen. It is the "why" behind the "what" in the Stakeholder Specification (Document 2).

This document does NOT enter the pipeline as `specs/stakeholder_spec.md`. It is a reference document indexed by SVP's reference system and available to agents on demand.

---

## 2. The SVP Product Line

SVP is a deterministically orchestrated, sequentially gated development system where a domain expert authors software requirements in natural language and LLM agents generate, verify, and deliver a working Python project. It has evolved through five releases:

**SVP 1.0** — First working prototype. Six-stage pipeline, deterministic gating, agent separation.

**SVP 1.1** — Hardening. Five blueprint-era fixes: gate status string mismatch, hook permission freeze, SVP_PLUGIN_ACTIVE canonicalization, configurable skip_permissions, command Group A/B enforcement.

**SVP 1.2** — Post-delivery debug loop. Nine post-delivery regression fixes (Bugs 6-14 in the unified catalog). The build tool for SVP 2.0.

**SVP 2.0** — Terminal feature release. Project profile, toolchain abstraction, pipeline/delivery split, three-layer preference enforcement, redo-triggered profile revision. Two additional regression fixes (Bugs 15-16). The build tool for SVP 2.1.

**SVP 2.1** — Terminal release of the product line. Quality gates, delivered quality configuration, changelog. Sixteen post-delivery and rebuild regression fixes (Bugs 26-41): Stage 5 repo assembly routing missing, environment name derivation mismatch, launcher CLI flag and subcommand regressions, quality gate operation paths, conda version-specific flags, unresolved routing placeholders, stub generation routing, repo sibling directory, Group B command definitions, orchestration skill guidance, artifact synchronization, Stage 1 routing. Two new structural invariants: universal two-branch routing (§3.6), profile canonical naming (§6.4). Fully specified launcher behavior. Setup agent UX requirements for domain experts. The build tool for language-directed variants.

---

## 3. What SVP 2.0 Gets Right

These are the sound architectural decisions that SVP 2.1 preserves without modification:

**The six-stage pipeline (plus one transitional phase).** Six stages (0-5) plus one transitional phase (Pre-Stage-3), for a total of seven sequential phases: Setup → Spec → Blueprint → Infrastructure → Verification → Integration Testing → Delivery. Each phase has clear entry/exit criteria. The sequential gating ensures no phase begins until the previous phase's contracts are satisfied.

**The four-layer orchestration.** CLAUDE.md sets the frame. The REMINDER block reinforces at recency. Terminal status lines constrain interpretation. Hooks enforce at boundaries. No single layer is sufficient; together they provide practical reliability.

**The state machine and routing script.** Every pipeline decision is made by deterministic scripts reading pipeline_state.json. The main session executes structured action blocks, never reasons about flow. SVP 2.1 strengthens this with the two-branch routing invariant: every sub-stage with an agent-to-gate transition must check `last_status.txt` to distinguish "agent not yet done" from "agent done, present gate." This was discovered through Bug 21 (which caused infinite re-invocation loops) and elevated from a per-stage fix to a universal structural invariant.

**The fix ladders.** Bounded escalation with deterministic advancement. The three-hypothesis diagnostic discipline forces consideration of implementation, blueprint, and spec levels before converging on a diagnosis.

**The project profile and toolchain abstraction.** SVP 2.0's cleanest architectural contribution. The pipeline/delivery split — build with Conda, deliver with whatever the human prefers — was the key insight that enables language-directed variants. The toolchain file moves commands from hardcoded strings to a configuration file, making the pipeline's tool usage auditable and testable.

**The three-layer preference enforcement.** Blueprint contracts (Layer 1), checker validation (Layer 2), compliance scan (Layer 3). Each layer catches what the previous layer misses.

**The 24-unit decomposition.** The DAG with backward-only dependencies, the topological build order, the context isolation per unit. This structure is the foundation that makes the pipeline scale to complex projects.

---

## 4. The Quality Gap

SVP 2.0 verifies that code **works**. It does not verify that code is **well-formed**.

A project built by SVP 2.0 passes all tests, installs correctly, and functions as specified. But the code itself may have:

- Inconsistent formatting — tabs mixed with spaces, irregular whitespace, inconsistent line lengths.
- Unused imports and variables — artifacts of the agent's generation process.
- Style violations — bare except clauses, mutable default arguments, naming inconsistencies.
- Missing type annotations — or incorrect ones that happen not to cause runtime errors.
- Import ordering inconsistencies — standard library, third-party, and local imports interleaved.
- Overly complex functions — that work correctly but are difficult to read or maintain.

These are not bugs. The code works. But for the domain developer receiving the project, they represent manual cleanup work that the pipeline should have handled.

---

## 5. Why Post-Delivery Quality Fixing Is Inadequate

The obvious alternative: include linter and formatter configs in the delivered project (a Tier B delivery feature) and let the end user run them. This is necessary but not sufficient.

**The agents are gone.** During the build, the implementation agent can fix quality issues interactively — it has context about what the code does and why it made specific choices. After delivery, there is no agent. The human must either fix issues themselves (they can't — they're not an engineer) or bring in another tool.

**Formatting after delivery breaks the diff.** If the first thing the human does with their delivered project is run `ruff format` and it reformats 200 lines, the initial commit history is noisy and misleading. If formatting is applied during the build, the delivered code is already clean — every commit in the history reflects intentional changes, not formatting cleanup.

**Type errors lack fix context after delivery.** A mypy error that says "Argument 1 has incompatible type str; expected int" is actionable during the build — the implementation agent knows what the function should accept and can fix it in seconds. After delivery, the human must trace the type chain through unfamiliar code.

The right time to catch and fix quality issues is immediately after the code is produced, while the producing agent is still available for re-passes. This is the core insight behind pipeline-integrated quality gates.

---

## 6. Why SVP 2.1 Is a Pipeline Change, Not Just a Delivery Feature

The v7.0 roadmap (Section 19.1) stated that the 2.x line would have "no pipeline changes, no new stages, no new agents." SVP 2.1 relaxes this constraint. The justification:

**Quality gates are operationally identical to infrastructure setup.** Pre-Stage-3 infrastructure setup is a deterministic script that runs tools, checks output, and reports success or failure to the routing script. Quality gates are the same pattern applied at different points in the cycle. If infrastructure setup was not considered a "pipeline change," quality gates are not either.

**Quality gates do not add stages, agents, or gate types.** They add sub-stages to the state schema and routing paths to the routing script. The Stage 3 verification cycle gains two deterministic checkpoints (between test generation and red run, between implementation and green run). Stage 5 structural validation gains one checkpoint (before delivery). The existing fix ladders, gate vocabulary, and orchestration protocol are unchanged.

**Quality gates follow the auto-fix-then-escalate pattern.** They are not a new architectural concept. The pattern — run a deterministic tool, check for issues, fix mechanically where possible, escalate to an agent only if necessary — is the same pattern the pipeline already uses for test execution, import validation, and structural checking.

The change is bounded: 13 of 24 units are touched, but 11 are unchanged. The highest-impact unit is Unit 10 (routing script), which gains new routing paths. No new agents are created. No new gate types are created. The human gate vocabulary is unchanged.

---

## 7. The Toolchain Abstraction Was Ready

SVP 2.0's `toolchain.json` was designed for exactly this kind of extension. Adding a `quality` section with formatter, linter, and type checker commands follows the same pattern as the existing `environment`, `testing`, `packaging`, `vcs`, `language`, and `file_structure` sections:

- Each section maps abstract operation names to concrete command templates.
- Placeholders (`{run_prefix}`, `{target}`, `{env_name}`) are resolved at runtime.
- Resolution is single-pass, deterministic, auditable.

The `quality` section adds gate composition lists (`gate_a`, `gate_b`, `gate_c`) that define which operations run at each quality gate. This makes gate behavior data-driven rather than hardcoded — a future toolchain variant could define different gate compositions without code changes.

---

## 8. Regression Bug History

SVP has accumulated 42 bugs across its development history. The full analysis, root cause patterns, and prevention rules are in the Lessons Learned document (Document 4). The bugs reveal eight recurring patterns:

- **P1 — Cross-unit contract drift** (24 bugs): Two units must agree on something; the implementation misses the detail.
- **P2 — State management assumptions** (5 bugs): A transition function assumes a precondition or forgets a reset.
- **P3 — Implicit resolution assumption** (5 bugs): A value is assumed to resolve correctly in a context where it does not.
- **P4 — Framework dependency completeness** (1 bug): Always-needed packages missing from extraction.
- **P5 — Error classification precision** (1 bug): Broad indicator matches both target and expected conditions.
- **P6 — Status line matching inconsistency** (1 bug): Two dispatchers use different strategies.
- **P7 — Spec completeness** (9 bugs): Spec enumeration is incomplete or terminology undefined; implementation faithfully follows the gap.
- **P8 — Version upgrade regression** (1 bug): A function rewritten during a version upgrade loses edge cases or validation logic from the prior version.

The single most important finding: cross-unit contract drift is the dominant pattern (24 of 42 bugs). AST-based structural tests at every cross-unit boundary are the primary defense. Bugs 17-25, all discovered during SVP 2.1 preparation and early build, reinforce the P1 dominance: hook schema mismatch (Bug 17), dead helper functions never wired into the output path (Bug 18), gate prepare flag/registry mismatch across units (Bug 19), routing script missing gate presentation after agent completion (Bug 21), stakeholder spec filename mismatch between setup agent and prepare script (Bug 22), alignment check skipped in stage progression (Bug 23), Stage 3 core sub-stage routing unspecified (Bug 25). Bug 20 (same-file copy guard) is a P2 variant — a file operation assuming source and destination will always differ. Bug 24 (`total_units` read as None during infrastructure setup) is a P3 variant — the infrastructure setup reads a state field that it should derive and produce, not consume. Bugs 26-30, discovered post-delivery: Stage 5 repo assembly routing entirely missing from route() (Bug 26) — all infrastructure defined but never wired; environment name derivation mismatch in delivered repo (Bug 27) — git repo agent independently derived env name instead of using canonical `derive_env_name()`; single-commit assembly instead of prescribed 11-commit order (Bug 28) — no structural validation of commit structure; multiple assembly defects in delivered repo (Bug 29) — stale tests, incomplete gate registry, missing status write, path resolution mismatch; README carry-forward content lost (Bug 30) — agent rewrote README from scratch instead of preserving previous version's content. Bugs 31-32, discovered during rebuild preparation: launcher passed non-existent `--project-dir` flag to Claude Code CLI (Bug 31) — P1, launcher assumed a flag that does not exist; unnecessary `svp resume` subcommand introduced (Bug 32) — P7, spec did not explicitly define the CLI subcommand vocabulary, allowing the blueprint to invent new subcommands.

Bugs 33-36, discovered during SVP 2.1 rebuild (bootstrapping): quality gate operation paths not qualified before passing to `resolve_command` (Bug 33) — P1+P3, gate operations are relative to the `quality` section but the caller passed them as top-level paths; `--no-banner` flag in toolchain.json incompatible with conda 25.x (Bug 34) — P7, version-specific flag hardcoded in template; routing script emits unresolved `{env_name}` placeholder in COMMAND output (Bug 35) — P3, routing function doesn't resolve placeholders before returning action blocks; stub generation missing from Stage 3 routing cycle (Bug 36) — P7, Section 10.0 cycle overview omits stub generation step, routing has no `stub_generation` sub-stage, tests fail with collection errors instead of test failures.

Bugs 37-41, discovered post-delivery during SVP 2.1 rebuild: delivered repo created inside workspace instead of as sibling directory (Bug 37) — P1, spec requirement not relayed to agent definition; Group B command definitions missing action cycle steps (Bug 38) — P1+P7, command definitions stopped after step 2; orchestration skill missing slash-command cycle guidance (Bug 39) — P7, skill covered only routing-script-driven cycles; artifact synchronization not enforced between workspace and delivered repo (Bug 40) — P1, direct fixes bypass the formal reassembly loop; Stage 1 routing missing two-branch check and gate registration (Bug 41) — P7+P1, spec listed Stage 1 in the invariant but no structural test verified it.

Bug 21 is particularly instructive. The original fix was applied only to Stage 0 sub-stages (project_context, project_profile), but the same pattern affects every agent-to-gate transition in the pipeline. Stage 1 was missed in the prior build because the fix was applied per-stage rather than as an invariant. The v8.2 spec revision elevated this to a universal structural invariant (§3.6) with an exhaustive enumeration of all affected sub-stages, ensuring the pattern cannot be missed again. Bug 41 proved that enumeration alone is insufficient -- even with Stage 1 explicitly listed in the invariant, the implementation omitted it. The fix added a gate ID consistency invariant (every gate ID in routing dispatch must also appear in gate preparation registries) and a structural test to enforce it, closing the gap between specification and implementation verification.

---

## 9. Why SVP Uses Claude Code Features the Way It Does

SVP uses a deliberately narrow subset of Claude Code's extension model:

**One skill, not many.** Skills load on demand based on description matching — Claude decides when a skill is relevant. SVP needs deterministic control, not probabilistic loading. The orchestration skill exists as belt-and-suspenders reinforcement.

**Subagents for all substantive work.** Context isolation, tool restriction, terminal status lines. The hard constraint that subagents cannot spawn further subagents is why the main session orchestrates all invocations.

**Hooks for enforcement, not orchestration.** Two hooks: write authorization and non-SVP session protection. Hooks cannot inject action blocks or control agent sequences.

**Commands split into Group A and Group B.** Group A runs scripts. Group B spawns agents. Confusing these groups was the most costly bug in SVP 1.1. Group B command definitions must include the complete action cycle (prepare, spawn, write status, POST, re-run routing) — an incomplete definition causes the main session to fail the cycle because it has no other source of the correct `--phase` value.

**CLAUDE.md for session-level identity.** The REMINDER block maintains it through context accumulation.

**`.claude/rules/` not used.** SVP's instructions are monolithic and unconditional.

**MCP for optional external access only.** GitHub read access and web search. Never for core operations.

**Plugin structure for distribution, not runtime.** The launcher copies scripts to workspace-local paths so runtime is independent of plugin installation path.

**Artifact synchronization between workspace and delivered repo.** Multiple artifacts exist as dual copies: Python source in workspace and delivered scripts, `*_MD_CONTENT` constants and delivered `.md` files, spec/blueprint/references in workspace and `docs/` in the delivered repo. The formal debug loop syncs via Stage 5 reassembly. Direct fixes outside the loop require manual propagation — the spec enumerates all dual-copy artifacts and requires sync as part of every fix.

---

## 10. SVP 2.1 as Terminal Release

SVP 2.1 is the last release of the SVP product line. The pipeline architecture — six stages (0-5) plus one transitional phase (Pre-Stage-3) for a total of seven sequential phases, quality gates, deterministic gating, four-layer orchestration, fix ladders, project profile, toolchain abstraction, two-branch routing invariant, profile canonical naming invariant — is complete.

Future development takes the form of language-directed variants (SVP-R, SVP-elisp, SVP-bash), each built by SVP 2.1 as a Python project. The strategic rationale and build plan are in the Product Roadmap (`svp_product_roadmap.md`).

---

## 11. Architectural Improvements in the 2.1 Rebuild

Three architectural improvements were introduced during the SVP 2.1 rebuild, after the initial 2.1 implementation revealed token budget pressure and a recurring assembly failure mode.

**Blueprint prose/contracts split.** The single `blueprint.md` was split into `blueprint_prose.md` (Tier 1 descriptions) and `blueprint_contracts.md` (Tier 2 signatures + Tier 3 contracts). Test and implementation agents — the highest-frequency Stage 3 invocations — receive only the contracts file. Tier 1 prose is never needed by these agents; they need precise contracts, not intent descriptions. The saving compounds across all units, passes, and retries. The primary risk is synchronization drift between the two files, mitigated by treating them as an atomic pair with explicit instructions in the blueprint author agent's definition.

**Stub sentinel.** The stub generator now writes `__SVP_STUB__ = True` as the first non-import statement in every generated stub. Structural validation scans all delivered Python source files for this sentinel and fails immediately if found. A `PostToolUse` hook provides a second enforcement point at write time. This closes a silent failure mode where the git repo agent copied stub files to delivery paths — a failure that previously reached the human's manual test step before being detected.

**Proactive lessons learned use.** The lessons learned document previously informed agents only reactively (updated on bug triage, available on demand). Two proactive uses close the gap: (1) the blueprint checker receives the pattern catalog and reports structural features matching known failure patterns as advisory risks at Gate 2.2; (2) the test agent receives filtered lessons learned entries for the current unit, enabling it to write tests that probe historically problematic behaviors. Both uses are token-bounded — the checker receives only the pattern catalog section, and the test agent receives only entries matching the current unit by unit number or pattern classification.

---

*End of baseline and rationale.*
