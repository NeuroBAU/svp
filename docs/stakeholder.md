# SVP — Stratified Verification Pipeline

## Stakeholder Specification v6.0

---

## 1. Purpose and Scope

SVP is a deterministically orchestrated, sequentially gated development system where a domain expert authors software requirements in natural language, and LLM agents generate, verify, and deliver a working Python project. The pipeline's state transitions, routing logic, and stage gating are controlled by deterministic scripts; the LLM agents that operate within this framework are not themselves deterministic, but are maximally constrained by a four-layer architecture of behavioral instruction, recency-reinforced reminders, structured agent output, and hook-based enforcement (see Section 3.6). The human never writes code. The system compensates for the human's inability to evaluate generated code through multi-agent cross-checking, forced diagnostic discipline, and human decision gates concentrated where domain expertise — not engineering skill — is the deciding factor.

This document is the stakeholder specification for building SVP itself. It is intended to be read by a human-LLM pair working through a chat interface, producing a Claude Code plugin as output. It describes what SVP must do, for whom, under what constraints, and what constitutes success or failure. It does not prescribe implementation, but it is written with awareness of the Claude Code ecosystem in which SVP will operate, and specifically with awareness of that ecosystem's actual capabilities and constraints.

### 1.1 When SVP Is Appropriate

SVP is designed for projects where at least two of the following conditions hold:

- The human cannot evaluate the generated code for correctness.
- The system is complex enough that errors can cascade silently between components.
- The cost of undetected errors is high relative to the cost of slower development.

SVP is not appropriate when the human can competently evaluate the output, when the project is small enough that manual testing suffices, or when speed matters more than defensive depth. Building SVP itself is an intermediate case: the builder can evaluate the generated output, but the system is complex enough that key SVP principles — a blueprint, tests, and a DAG with no-forward dependencies — are used during construction, with a human in the loop for the manual intervention that LLM-assisted development requires (see Section 29).

### 1.2 Language and Environment Constraints

- All generated code is Python.
- All tests use pytest.
- All environments are managed with Conda.
- All version control uses Git.
- The system runs inside Claude Code's terminal interface as a Claude Code plugin. The CLI is the foundational interface — not a stepping stone to a graphical interface (see Section 27).
- The human interacts through typed conversation and explicit commands.

These constraints are fixed for this version of SVP. Future versions may extend to other languages and environments by revising this spec.

### 1.3 Project Size Constraint

SVP is designed for projects where the full blueprint fits within the effective context budget. The effective context budget is derived from the available context window of the active models, minus the overhead required for agent system prompts and operational context. This overhead is substantial — each subagent invocation consumes approximately 20,000 tokens before any project content is loaded — and the budget calculation must account for it.

The effective budget defaults to the smallest usable context among all models configured for agent roles. This budget is configurable via override in the SVP configuration file and is validated during blueprint alignment (Stage 2). If a model configuration change reduces the available budget below the size of an existing blueprint, the system warns the human.

Projects exceeding this limit require a different approach and are out of scope.

### 1.4 Delivery Form

SVP is delivered as a Claude Code plugin containing: skill files for each agent role, agent definitions for each subagent, slash commands for human interaction, hooks for enforcement and safety, deterministic scripts for state management and stub generation, a configuration file, and a test suite for the deterministic components (with elevated coverage for the preparation script). SVP is also accompanied by a standalone `svp` launcher CLI tool, distributed alongside the plugin but installed separately to the user's PATH. The launcher is not a plugin component — it runs before Claude Code starts and manages the complete SVP lifecycle: prerequisite verification, session cycling, filesystem permission management, and Claude Code invocation.

The repository containing SVP has the following top-level structure:

```
svp-repo/                  <- repository root
|-- .claude-plugin/
|   +-- marketplace.json      <- marketplace catalog for Claude Code plugin installation
|-- svp/                   <- the plugin subdirectory
|   |-- .claude-plugin/
|   |   +-- plugin.json       <- plugin manifest
|   |-- agents/
|   |-- commands/
|   |-- hooks/
|   |-- scripts/
|   |   +-- svp_launcher.py  <- standalone launcher (installed to PATH)
|   +-- skills/
|-- src/                      <- SVP source code (Python)
|-- tests/                    <- SVP test suite
+-- ...
```

The SVP launcher (`svp_launcher.py`) lives at `svp/scripts/svp_launcher.py` in the delivered repository. Although the launcher is not a plugin component (it runs before Claude Code starts), it is distributed inside the plugin's `scripts/` directory for discoverability and is referenced by the `pyproject.toml` entry point as `svp.scripts.svp_launcher:main`.

The `marketplace.json` at the repository root registers the plugin for installation via `claude plugin marketplace add`. Its schema requires a top-level `name` (string), `owner` (object with `name` string), and `plugins` array. Each plugin entry requires `name`, `source` (relative path prefixed with `./`, e.g. `"./svp"`), `description`, `version`, and `author` (object with `name` string). The exact schema:

```json
{
  "name": "svp",
  "owner": { "name": "SVP" },
  "plugins": [
    {
      "name": "svp",
      "source": "./svp",
      "description": "Stratified Verification Pipeline — deterministically orchestrated, sequentially gated development for domain experts",
      "version": "1.2.0",
      "author": { "name": "SVP" }
    }
  ]
}
```

The plugin subdirectory (`svp/`) contains all Claude Code plugin components at its root level: `commands/`, `agents/`, `skills/`, `hooks/`, and `scripts/`, with a `.claude-plugin/plugin.json` manifest. All component directories must be at the plugin subdirectory root level — not nested inside `.claude-plugin/`, and not at the repository root level.

The human installs the SVP plugin and types `svp` (or `svp new` for a new project) in a terminal within a project directory. The launcher verifies prerequisites, sets up the environment, and launches Claude Code with the SVP orchestration protocol active. The human can still type `claude` for normal Claude Code work in any directory — SVP sessions are cleanly separated from regular Claude Code usage.

---

## 2. Target User Profile

The primary user is a domain expert with the following characteristics:

- Deep knowledge of their professional field (e.g., neuroscience, climate science, finance, logistics).
- Conceptual understanding of programming: knows what functions, classes, variables, loops, and conditionals are.
- Cannot author code in any specific language, or has only tutorial-level experience insufficient for building a meaningful project.
- Can read code and roughly follow its logic when guided, but cannot independently evaluate whether an implementation is correct.
- Can judge whether a test's assertion makes domain sense when explained in plain language (e.g., "this test checks that spike sorting rejects any waveform shorter than 0.3 milliseconds — is that correct?").
- Can follow terminal instructions precisely but cannot troubleshoot environment problems independently.
- Has the statistical or quantitative literacy typical of their field.

The motivating example is an academic neuroscientist who understands exactly what a spike-sorting pipeline should do but has never developed a meaningful Python project. However, SVP is domain-agnostic — the domain expertise enters through the stakeholder spec, not through the system's design.

---

## 3. Design Principles

These principles govern every design decision in SVP. When in doubt, refer to these.

### 3.1 Ruthless Restart

Any problem traced to a document — the stakeholder spec or the blueprint — triggers a fix to the document followed by a complete forward restart from the appropriate stage. No surgical repair of downstream artifacts. No blast radius analysis. No selective re-validation. This trades compute cost for correctness certainty.

The rationale: blast radius analysis is itself an LLM-generated artifact that could be wrong. If the LLM reports "only units 5 and 8 are affected" and misses unit 11, the system has a silently broken unit that was never re-validated. Ruthless restart eliminates this failure mode entirely. The human never needs engineering judgment to evaluate whether a partial re-validation is safe.

Ruthless restart applies to what comes *after* the revised document — everything downstream is regenerated from scratch. It does not require redoing the work that came *before* the problem. When the blueprint checker finds a localized spec issue, the fix is a targeted revision of the spec (a focused Socratic dialog about just that issue), followed by fresh blueprint generation. The human does not redo the entire stakeholder dialog to fix one contradiction. The distinction between targeted revision and full restart is described in Section 7.6.

**Corollary — report most fundamental level.** When any agent identifies problems at multiple levels of the document hierarchy, it reports only the deepest problem. Spec problems supersede blueprint problems, which supersede implementation problems. This prevents patching at multiple levels simultaneously, which would undermine ruthless restart.

### 3.2 Binary Decision Logic

At every diagnostic failure point, the diagnosis produces a binary outcome:

- **Implementation problem**: fix locally, continue building.
- **Document problem**: fix the document, restart.

No third option. No "maybe we can patch it." The human never evaluates blast radius, cascade impact, or architectural risk. They evaluate domain intent — is the spec correct? Is the blueprint faithful to the spec?

Binary decision logic applies to diagnostic gates — the failure points where the pipeline must determine whether the problem is in the code or in the documents. Approval gates (such as spec approval, blueprint approval, and fresh review requests) support three or more options as appropriate. Decision gates present explicit response options to the human (see Section 3.5).

### 3.3 Stateless Agents

Every agent invocation is a fresh instance with no memory of prior invocations. Agents receive their role prompt and the relevant context documents, produce output, and are dismissed. This prevents anchoring to prior outputs and ensures each assessment is independent.

When a blueprint is rejected and regenerated, the new blueprint author has never seen the old blueprint. When a checker verifies alignment, it has never seen a prior checker's assessment. Fresh perspective on every iteration.

Where multi-turn conversation is required (Socratic dialog, help sessions), conversation history is maintained through an append-only conversation ledger — a structured file that records each exchange. On each turn, the agent is freshly invoked with the full ledger as context, preserving the appearance of continuity while maintaining true statelessness. The ledger survives session interruptions and terminal closures. When the human provides a domain hint at a decision gate (see Section 14.4), the hint is injected into the next agent's task prompt as a one-shot context item — it is not accumulated across invocations. However, the hint is also recorded as a `[HINT]` entry in the relevant ledger, making it visible to subsequent agents that read the log.

Ledger growth is bounded. When a ledger approaches the context limit for its associated agent role (accounting for the agent's system prompt and operational overhead), the system warns the human. The human may then choose to finalize the current phase (e.g., approve the stakeholder spec draft as-is) or use the `/svp:hint` command to get a summary of the conversation so far before the ledger is compacted. Compaction is a safety valve, not a rescue mechanism. It condenses exploratory exchanges — sequences of questions and answers that led to a confirmed decision — into summary references, while preserving all decisions, confirmed facts, and any content that cannot be mechanically classified. Agents produce self-contained tagged lines (see Section 15.1): every `[DECISION]`, `[CONFIRMED]`, or `[QUESTION]` line carries its own rationale and context, not just a bare conclusion. This ensures that compacted ledgers retain full meaning. The compaction script uses a character threshold safety net: tagged lines above 200 characters are presumed self-contained and their bodies are deleted during compaction; tagged lines at or below 200 characters keep their bodies as insurance. This threshold is configurable in `svp_config.json`. Compaction is performed by a deterministic script with no LLM involvement. For most projects, the effective context budget (see Section 22) is sufficient for a complete stakeholder or blueprint dialog without compaction firing. Compaction exists for unusually long or complex dialogs where the conversation approaches the budget limit.

### 3.4 Agent Separation

Different agents handle different roles. No agent both writes code and writes the tests for that code. No agent both authors and checks a document. This structurally breaks correlated interpretation bias — the failure mode where a single agent misinterprets a specification and produces both implementation and tests that encode the same error.

To further reduce correlation, the test agent and the implementation agent are always separate invocations with no shared context — the implementation agent never sees the tests. Both use the most capable model by default (`claude-opus-4-6`). Model assignments are configurable at any time, including mid-pipeline, and take effect on the next agent invocation.

SVP acknowledges that using the same model for test and implementation agents creates a residual risk of correlated interpretation. This risk is mitigated by procedural separation (agent isolation with no shared context, coverage review by a third agent, human gates at test validation, and synthetic data assumption review) rather than model diversity. Model assignments remain configurable — if a future model landscape offers meaningful diversity, the configuration can exploit it without spec changes.

### 3.5 Human Judgment at Decision Gates

The human makes pipeline decisions at gates designed around their domain expertise:

- Is this stakeholder spec a correct and complete description of what I want?
- Does this test assertion make domain sense?
- Are we stuck because the spec is wrong?

These decisions require domain knowledge, not engineering skill. The pipeline's control flow — cascade impact assessment, partial re-validation safety, stage sequencing — is determined by deterministic scripts, not by human engineering judgment.

**Explicit response options.** Decision gates present explicit response options to the human. The gate prompt includes the exact words to type for each option. If the human's response does not match any option, the main session re-presents the options rather than interpreting the ambiguous response. The `/svp:help` command remains available at any gate independent of the gate's response options — the human can always invoke the help agent before making a decision. Example:

```
Please choose one:
  -> TEST CORRECT — the test is right, the implementation needs fixing
  -> TEST WRONG — the test doesn't match my requirements
```

The complete vocabulary of gate status strings — the exact strings written to `.svp/last_status.txt` for each gate response — is defined in Section 18.4.

**Hint-blueprint conflicts.** When an agent receives a human domain hint that contradicts the blueprint contract, the agent does not silently resolve the conflict. Instead, it returns a structured terminal status line: `HINT_BLUEPRINT_CONFLICT: [details]`. The routing script presents a binary gate: blueprint correct (discard hint, proceed) or hint correct (document revision, restart). This ensures that no human correction is silently lost.

However, the human is not limited to domain-only observations. At any decision gate, the human may collaborate with the Help Agent (see Section 14.4) to formulate and forward engineering-level suggestions — "the formula uses 5/9 instead of 9/5," "it's comparing the wrong columns," "the loop iterates one too many times." These suggestions emerge from the collaboration between the human's domain expertise and the Help Agent's engineering literacy. The human brings the intuition and domain knowledge ("something is wrong with the conversion," "this threshold doesn't match my data"), and the Help Agent brings the ability to read code, trace logic, and identify the specific technical issue. Together, they produce engineering suggestions that neither could formulate alone — the human would lack the code-reading ability, and the Help Agent would lack the domain context to know what "correct" looks like.

The key constraint is how the pipeline treats these observations: they are a signal, not a command. The receiving agent evaluates the hint alongside the blueprint contract, diagnostic analysis, and its own judgment. If the hint contradicts the blueprint, the conflict is surfaced as a human decision gate (see above). The human's hint influences the agent's work — it does not alter the pipeline's routing, gating, or control flow, which remain script-driven (see Section 3.6).

### 3.6 Maximally Constrained Orchestration

The main Claude Code session — the top-level Claude instance the human interacts with — acts as the orchestration layer for the entire pipeline. Its behavior is constrained through a four-layer architecture where each layer compensates for the weaknesses of the others:

**Layer 1 — CLAUDE.md.** Loaded at session start, this file identifies the project as SVP-managed and defines the orchestration protocol: how the main session should read the routing script output, execute the indicated action, and avoid improvising pipeline flow. CLAUDE.md sets the behavioral expectations for the entire session but its influence degrades as context accumulates.

**Layer 2 — Routing script REMINDER.** Every routing script output includes a mandatory REMINDER block at the end, reinforcing critical CLAUDE.md behavioral constraints at the point of highest context recency. The REMINDER exploits the recency effect: instructions at position 49,500 in the context window are stronger than instructions at position 500. The exact REMINDER text is:

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

**Layer 3 — Agent terminal status lines.** Every subagent produces a structured terminal status line as its final output (see Section 18). The set of possible status lines for each agent role is defined in this spec. The routing script recognizes these status lines and dispatches accordingly. This constrains what the main session must interpret — instead of parsing natural language, it captures a structured string.

**Layer 4 — Hooks and universal write authorization.** Enforcement at boundaries, blocking unauthorized actions regardless of what the main session attempts. Hooks cannot compel the main session to take a specific action, but they can prevent unauthorized actions. Universal write authorization (see Section 19) validates every write operation against the current pipeline state. This is the safety net when the other three layers fail.

No single layer is sufficient. CLAUDE.md fades with context accumulation. The REMINDER can be ignored by a misbehaving session. Terminal status lines can be misinterpreted. Hooks can only block, not direct. Together, they provide defense in depth — practical reliability through redundancy, not theoretical determinism through any one mechanism.

**The six-step mechanical action cycle.** The main session's complete behavior is six steps, repeated:

1. Run the routing script -> receive a structured action block (see Section 17).
2. Run the PREPARE command (if present) -> produces a task prompt or gate prompt file.
3. Execute the ACTION (invoke agent / run command / present gate).
4. Write the result to `.svp/last_status.txt`.
5. Run the POST command (if present) -> updates pipeline state.
6. Go to step 1.

The main session never decides which state update to call, never constructs arguments for state scripts, and never reasons about what should happen next. Every decision about pipeline flow is made by deterministic scripts. The main session's freedom is limited to how it communicates with the human within a stage — how it phrases a progress update, how it presents a subagent's output, how it formats an error message.

**Session cycling.** The SVP launcher manages automatic session cycling to prevent context degradation. Session boundaries fire at every major pipeline transition: unit verified -> starting next unit, construction -> document revision, document revision complete -> stage restart, and all stage transitions. The mechanism: the main session writes a restart signal file and exits. The launcher detects the signal and relaunches Claude Code. The new session reads CLAUDE.md, runs the routing script, and picks up from the state file. Every post-restart session begins with a mandatory context summary drawn from the state file: what project, what stage, what just happened, what happens next. The human sees a brief transition message and the pipeline continues. Session lifecycle management is described in detail in Section 16.

**State management.** The routing script predetermines the POST command (including the state update script and its arguments) at the time it specifies the action. The main session writes the agent's terminal status line to `.svp/last_status.txt`. The POST script reads the status file, parses the structured status line, validates preconditions, and updates `pipeline_state.json`. The state-update scripts validate preconditions before writing new state. If preconditions are not met (e.g., tests have not passed, coverage review is incomplete), the script refuses to advance the state and returns an error message. This makes the scripts — not the hooks and not the LLM — the primary stage-gating mechanism.

The main session does not hold domain conversation history. Multi-turn exchanges (Socratic dialog, help sessions) are maintained in conversation ledgers, read and written by subagents. The main session's context remains clean — it carries only the current stage's working state, not the accumulated history of the project.

### 3.7 Explicit Context Loading

Claude Code subagents receive their agent definition file (the system prompt) plus basic environment details. They do not automatically receive project documents. Every agent invocation in SVP must therefore have an explicit context loading protocol specifying:

- **Role context (system prompt):** The agent's behavioral instructions, output format requirements, and constraints. This is static — defined once in the agent definition file and identical across all invocations of that agent role.
- **Task context (task prompt):** The project-specific content the agent needs for this particular invocation. This is dynamic — assembled by running a deterministic preparation script (triggered by the PREPARE command in the routing script output) that produces a ready-to-use task prompt file. The main session passes the contents of this file as the task prompt verbatim. Examples: the current unit's blueprint definition and upstream contracts (for the test agent), the stakeholder spec and reference summaries (for the blueprint author), or the conversation ledger (for the dialog agent).
- **On-demand context (disk reads):** Files the agent reads from the project workspace during execution. Used when the full content is too large for the task prompt but may be needed selectively. Examples: full reference documents (summaries go in the task prompt; the agent reads the full document from `references/` only if it needs detail), or specific upstream unit implementations (only if the agent's role requires it, which in SVP is rare by design).

This three-layer protocol ensures that each agent receives exactly the context it needs — no more, no less — and that the context loading is predictable and auditable. The preparation scripts that assemble task context are deterministic components with no LLM involvement. The task prompt content must transit through the main session's context window to reach the subagent via the Task tool — this is an acknowledged platform constraint (see Section 4).

### 3.8 Transparency on Demand

During autonomous work (agents generating, tests running), the human sees minimal output — a progress indicator, not a flood of agent transcripts. The pipeline announces the start of each autonomous sequence with a clear message indicating what is about to happen and that the human should wait for it to complete (see Section 20). When the pipeline needs the human, it presents a clear summary of what happened and what decision is needed. At any time, the human can request a detailed explanation of what the system just did, through the help agent. At decision gates, this transparency extends further: the human can not only see what happened but contribute domain insight to the next step through the hint forwarding mechanism (see Section 14.4).

### 3.9 Speed-Correctness Tradeoff

SVP chooses the path that requires less LLM judgment and more human involvement. The value proposition is making coding possible for people who could not do it at all, not making it fast. When a design decision offers a choice between a faster path that requires more LLM judgment and a slower path that relies on deterministic scripts and human decisions, SVP chooses the slower path. This principle governs fix ladder design (fresh agents over same-agent retries), state management (scripts over LLM reasoning), and pipeline flow (routing script decisions over main session reasoning).

### 3.10 Always Clean Spec

Working notes are absorbed into the spec body at every iteration boundary. The stakeholder spec is never a patched document with appended addenda. During the blueprint dialog, ambiguities are resolved as working notes appended temporarily so the dialog can continue. At every iteration boundary — whether the blueprint alignment succeeds or fails — all working notes are incorporated into the spec body through a focused revision by the Socratic dialog agent in revision mode. The result is always a clean, cohesive spec.

### 3.11 Human at Readiness Boundary

The pipeline refuses to proceed if the human has not provided sufficient context. This is the one place SVP says "no." The quality gate on `project_context.md` (see Section 6.1) enforces a minimum standard of input from the human. If after multiple attempts the human cannot provide substantive answers about their domain, the pipeline suggests they return when they have thought more about their requirements. This is not a failure — it is the pipeline protecting the human from building something they have not yet defined.

### 3.12 Universal Write Authorization

SVP-managed projects are protected by a two-layer write authorization system that controls all file modifications. The first layer uses filesystem permissions managed by the SVP launcher. The second layer uses hooks that validate every write operation against the current pipeline state. This system replaces simple "project protection" with a comprehensive authorization model that governs all writes — not just those from non-SVP sessions. The complete specification is in Section 19.

---

## 4. Platform Constraints

SVP operates within Claude Code's architecture, which imposes constraints that are not design flaws but inherent properties of the platform. The spec documents these constraints, the risks they create, and the mitigations SVP employs.

### 4.1 Task Prompt Relay Fidelity

Task prompt content prepared by deterministic scripts must transit through the main session's context window to reach the Task tool. The main session may summarize, reformat, annotate, or truncate the content. Claude Code provides no mechanism to pipe content directly from a script to a subagent.

**Risk:** Content transformation during relay. An agent receives a modified version of the carefully prepared task prompt, leading to incorrect behavior.

**Mitigations:**
- CLAUDE.md instructs verbatim relay explicitly.
- The REMINDER block reinforces this at point of highest context recency before every agent invocation.
- Routing script output is structured to make the expected action unambiguous — the TASK_PROMPT_FILE path is specified, not the content itself.
- Preparation scripts produce bounded, structured content that LLMs are more likely to relay faithfully than free-form prose.

**Diagnostic signal:** Repeated inexplicable agent failures that fix ladders do not resolve, suggesting agents are working from corrupted input.

**Future mitigation:** A platform-level mechanism (direct file-to-agent piping) if Claude Code's architecture ever supports it.

### 4.2 Agent Tool Restriction Enforcement

Agent tool restrictions specified in AGENT.md may be advisory rather than platform-enforced. The help agent's "read-only" guarantee — restricting its tool access to Read, Grep, Glob, and web search — may be probabilistic.

**Risk:** A help agent could modify files despite its tool whitelist.

**Mitigation:** Defense in depth. The help agent's read-only guarantee is supported by two layers: the AGENT.md tool whitelist (may or may not be platform-enforced) and the universal write authorization hooks (Section 19), which block unauthorized writes regardless of source. During a help session, the pipeline state authorizes no artifact writes — the hooks enforce this even if the agent attempts a write.

### 4.3 Cross-Platform Portability

SVP is designed to run on any platform where Claude Code and conda are available — macOS, Linux, and Windows. All deterministic scripts must be OS-agnostic.

**Constraints:**
- Scripts must never hardcode OS-specific paths (e.g. `/Users/`, `/home/`, `C:\Users\`), conda installation directories (e.g. `~/anaconda3/`, `~/miniconda3/`), or Python interpreter paths.
- All subprocess invocations targeting the project conda environment must use `conda run -n {env_name} <command>`. This is the canonical interpreter invocation strategy throughout SVP -- simpler is safer with an LLM orchestration layer.
- The conda environment name is derived deterministically from the project name: `project_name.lower().replace(" ", "_").replace("-", "_")`. This derivation must be used consistently across all scripts — never hardcoded.
- File path separators must use `pathlib.Path` throughout — never string concatenation with `/` or `\`.

---

## 5. Pipeline Overview

SVP proceeds through the following stages in strict order. Each stage must complete before the next begins. If a document-level problem is discovered at any stage, the pipeline restarts from the appropriate earlier stage.

```
Stage 0: Setup
Stage 1: Stakeholder Spec Authoring
Stage 2: Blueprint Generation and Alignment
Pre-Stage-3: Infrastructure Setup
Stage 3: Unit-by-Unit Verification
Stage 4: Integration Testing
Stage 5: Repository Delivery
```

After Stage 5 completion, the pipeline supports re-entry via `/svp:bug` for post-delivery bug investigation. The debug loop allows the human to report bugs discovered while using the delivered software, triggering a structured triage, regression test, and fix cycle that preserves SVP's verification guarantees. See Section 12.6.

### 5.1 What to Expect: Best Case and Worst Case

This section describes the two extremes of the pipeline experience for the stakeholder. Every real project falls somewhere between them. The detailed gate-by-gate scenarios are provided inline in the relevant sections (marked as **Scenarios**).

**Best case (everything works).** The human describes their requirements clearly. The Socratic dialog produces a complete spec on the first draft. The blueprint decomposes the problem cleanly, and the checker confirms alignment on the first attempt. Each unit's tests pass the red run, the implementation passes the green run, and coverage is complete — no human intervention needed at any unit. Integration tests pass. The repository is delivered. The human's involvement after the Socratic dialog is limited to a small number of approvals: approve the spec draft, approve the blueprint structure, and receive the final repo. Total human decisions: roughly 5-10 approvals across the full pipeline.

**Worst case (everything fails).** The human's initial requirements are incomplete. The spec draft requires multiple revisions with Help Agent assistance. The blueprint fails alignment checking three times, hitting the iteration limit — the spec must be revised before the blueprint can converge. During unit verification, tests are wrong (the human's domain assertions were imprecise), requiring the test fix ladder. Implementations fail, requiring the fix ladder and diagnostic escalation — which also fails, forcing a document revision and restart from Stage 2. After restarting, integration tests reveal a cross-unit issue that cannot be fixed by an assembly fix, forcing another document revision and another restart. The human provides hints at multiple gates, each requiring a Help Agent session. The pipeline eventually converges and delivers a correct repository, but only after several full restarts. Total human decisions: potentially dozens of gate decisions, hint sessions, and revision dialogs across multiple pipeline passes.

The pipeline is designed so that the worst case still terminates correctly — every escalation path has a bounded endpoint, and every restart produces a cleaner foundation. The cost of the worst case is time and compute, not correctness.

---

## 6. Stage 0: Setup

### 6.1 Behavior

Stage 0 is split between the SVP launcher (deterministic, runs before Claude Code) and the setup agent (runs within Claude Code for the interactive `project_context.md` creation).

**Launcher pre-flight (deterministic).** The SVP launcher runs before Claude Code launches and performs all prerequisite checking and environment setup:

- Verifies Claude Code is installed and functional.
- Verifies the SVP plugin is loaded and active.
- Verifies API credentials are valid.
- Verifies Conda is installed and accessible.
- Verifies Python is available at a compatible version.
- Verifies pytest is available.
- Verifies Git is installed and configured.
- Verifies network access is working.

If any prerequisite fails, the launcher reports the specific failure and exits with guidance. The human fixes the issue and runs `svp` again.

For new projects, the launcher also:

- Creates the project directory structure (see Section 6.2).
- Copies deterministic scripts from the SVP plugin into the project workspace's `scripts/` directory, making them available at workspace-relative paths (e.g., `python scripts/prepare_task.py`).

**Dual-file synchronization contract.** Six units maintain both a canonical implementation under `src/unit_N/stub.py` and a runtime copy under `scripts/`: Unit 1 (`svp_config.py`), Unit 2 (`pipeline_state.py`), Unit 4 (`ledger_manager.py`), Unit 5 (`blueprint_extractor.py`), Unit 8 (`hint_prompt_assembler.py`), and Unit 9 (`prepare_task.py`). The dual copies exist because subprocess invocations use `PYTHONPATH=scripts` with bare imports (e.g., `import prepare_task`), while the `src/` tree uses package imports (e.g., `from src.unit_9.stub import ...`). The `src/unit_N/stub.py` copy is always canonical — it is the version under test and the source of truth. The `scripts/` copy is the runtime deployment and must be updated to match whenever the canonical copy changes. To guard against drift, the routing script performs a startup check comparing `KNOWN_AGENT_TYPES` between `src/unit_9/stub.py` and `scripts/prepare_task.py` and emits a warning to stderr if they differ.

- Writes the initial `pipeline_state.json` with `stage: 0, sub_stage: hook_activation`.
- Writes the SVP configuration file with defaults.
- Generates the project's CLAUDE.md.
- Sets filesystem permissions (see Section 19).
- Launches Claude Code.

**Hook activation guidance (`stage: 0, sub_stage: hook_activation`).** Once Claude Code starts, the routing script outputs a `human_gate` action that instructs the main session to guide the human through reviewing and activating hooks via Claude Code's `/hooks` menu. Claude Code requires that changes to hook configuration files be reviewed through this menu before taking effect. The human confirms activation. The gate response options are **HOOKS ACTIVATED** and **HOOKS FAILED**. The POST command advances state to `sub_stage: project_context`.

**Project context creation (`stage: 0, sub_stage: project_context`).** The routing script outputs an `invoke_agent` action for the setup agent. The setup agent asks the human for a brief domain description (1-3 sentences) of what they want to build. The agent then conducts a structured conversation to refine this description into a well-written `project_context.md` file with the following sections: Domain, Problem Statement, Key Terminology, Data Characteristics, Intended Users, and Success Criteria.

The setup agent's role here is not merely transcription — it is active rewriting. The human is a domain expert, not a skilled context engineer. Whatever the human says, the setup agent transforms into well-structured, LLM-optimized context that downstream agents can work with effectively. The agent ensures each section contains precise, actionable language that will produce good results when fed to the stakeholder dialog agent and, later, to the blueprint author agent as foundational project context.

**Quality gate.** The setup agent evaluates whether each section of `project_context.md` contains substantive content. If any section is hollow or tautological (e.g., "I want to analyze some data"), the agent pushes back with specific questions designed to elicit the missing information. If after multiple attempts the human cannot provide sufficient content for the pipeline to proceed meaningfully, the setup agent refuses to advance and suggests the human return when they have thought more about their requirements. The state file records `Stage 0, awaiting sufficient context` so the human can return and pick up where they left off.

The agent presents the draft `project_context.md` to the human for approval. The gate response options are **CONTEXT APPROVED**, **CONTEXT REJECTED**, and **CONTEXT NOT READY**. If **CONTEXT APPROVED**: the POST command advances state to Stage 1 and the routing script triggers a session boundary. If **CONTEXT REJECTED**: the setup agent restarts the context creation dialog from scratch. If **CONTEXT NOT READY**: the pipeline pauses; the human can return later and resume where they left off. When requesting revisions before rejection, the human may invoke `/svp:help` to formulate a precise hint about what should change (see Section 14.4); the hint is forwarded to the setup agent's next refinement iteration.

**Resume mode.** When the launcher detects a valid project directory already exists, it reads the pipeline state file and launches Claude Code directly. The routing script outputs a context summary and the pipeline resumes at the appropriate stage. If the state file is missing or corrupt, recovery uses deterministic file-presence checking: the setup script checks for approved documents (stakeholder spec, blueprint) using completion markers (`<!-- SVP_APPROVED: 2025-03-15T14:32:07Z -->` appended to approved documents) and completed unit artifacts using marker files (`.svp/markers/unit_N_verified`). It reconstructs a conservative state estimate and presents it to the human for confirmation. No LLM inference. If reconstruction fails entirely, start fresh.

**Scenarios — Gate 0.1 (hook activation) and Gate 0.2 (project_context.md approval).**
*Best case:* Hooks activate successfully. The human provides a clear domain description. The setup agent refines it into a well-structured, LLM-optimized `project_context.md`. The human approves the first draft. Time: one interaction.
*Worst case:* Hooks fail to activate and the human needs guidance to resolve the issue. The human's initial description is vague or uses ambiguous terminology. Multiple refinement rounds are needed, with the human invoking `/svp:help` to formulate precise rewording. Eventually the human approves a `project_context.md` that captures their intent in language that downstream agents can work with effectively. Time: several interactions, but the pipeline does not restart — this gate only loops within Stage 0. In the most extreme case, the setup agent determines that the human cannot provide sufficient context and the pipeline pauses until they can.

**Optional integrations.** During bootstrap, the setup agent asks whether the human wants to enable optional integrations:

- **GitHub MCP:** connects the pipeline to GitHub for read-only access to external repositories. Useful when the human wants to reference an existing codebase — a library, a colleague's implementation, or a published tool — as context for the stakeholder spec or blueprint dialog. When enabled, the human can use `/svp:ref` with a GitHub repository URL to add a codebase as a reference during Stages 0-2. Not required — if not configured, all context enters through the Socratic dialog, reference documents, and file uploads. The GitHub MCP is read-only; it never writes to any repository. SVP's own git repo delivery (Stage 5) uses local git commands, not the GitHub MCP.

  **Setup flow.** If the human says yes, the setup agent guides them through configuration:

  1. The setup agent explains that GitHub access requires a Personal Access Token (PAT) with read-only repository permissions and asks the human whether they already have one or need instructions.
  2. If the human needs instructions, the setup agent provides step-by-step guidance: go to github.com/settings/tokens, create a fine-grained token scoped to the repositories they want to reference, with read-only Contents permission. The setup agent emphasizes: no write permissions, no admin permissions.
  3. The human provides the PAT. The setup agent configures the GitHub MCP server at user scope using Claude Code's `claude mcp add-json` command with the token passed via environment variable.
  4. The setup agent verifies the connection by requesting the server's tool list. If the connection fails, the setup agent reports the error and offers two options: retry with a new token, or skip GitHub MCP and continue without it.

  The setup agent never stores the PAT in any SVP file. The token is stored only in Claude Code's native MCP configuration (`~/.claude.json`), which is outside the project directory and not committed to version control.

  If the human declines during setup but later wants to add a repository reference via `/svp:ref`, the system offers to configure GitHub MCP at that point (see Section 13).

Additional integrations may be added in future versions. All integrations are optional — the core pipeline functions without any of them.

### 6.2 Directory Structure

```
parent/
|-- projectname/                  <- pipeline workspace
|   |-- .claude/                  <- Claude Code project config
|   |   |-- hooks.json            <- project protection hooks
|   |   +-- settings.json         <- Claude Code settings
|   |-- .svp/                     <- SVP infrastructure (always writable)
|   |   |-- task_prompt.md        <- current task prompt (prepared by scripts)
|   |   |-- gate_prompt.md        <- current gate prompt (prepared by scripts)
|   |   |-- last_status.txt       <- last agent terminal status line
|   |   |-- restart_signal        <- session restart signal file
|   |   +-- markers/              <- unit completion markers
|   |-- CLAUDE.md                 <- project-level Claude context (orchestration protocol)
|   |-- pipeline_state.json       <- current stage, verified units, iteration counts, pass history
|   |-- svp_config.json           <- tunable parameters (models, limits, budget)
|   |-- project_context.md        <- structured domain description (human-approved, Stage 0)
|   |-- logs/                     <- rejection reasons, diagnostic summaries, session logs
|   |   +-- rollback/             <- preserved artifacts from unit-level rollbacks
|   |-- ledgers/                  <- conversation ledgers for multi-turn interactions
|   |-- specs/
|   |   |-- stakeholder.md        <- the stakeholder spec (current version)
|   |   +-- history/              <- versioned copies and diff summaries
|   |-- blueprint/
|   |   |-- blueprint.md          <- the technical blueprint (current version)
|   |   +-- history/              <- versioned copies and diff summaries
|   |-- references/
|   |   |-- index/                <- generated summaries of reference documents and repos
|   |   |-- repos.json            <- URLs of referenced GitHub repositories
|   |   +-- (original documents)  <- human-provided reference documents
|   |-- scripts/                  <- deterministic scripts (copied from plugin at bootstrap)
|   |-- src/                      <- generated source code, organized by unit
|   |-- tests/                    <- generated test suites, organized by unit
|   +-- data/                     <- synthetic test fixtures
+-- projectname-repo/             <- clean git repo (final deliverable)
```

The workspace is the build environment. The repo is the deliverable. The human works with the repo; the workspace is internal to SVP unless the human chooses to inspect it via the help agent.

## 7. Stage 1: Stakeholder Spec Authoring

### 7.1 Entry Point

The pipeline begins with a welcome message explaining:

- What SVP is and what the human can expect.
- The rules of engagement for the agent: one question at a time, consensus before moving on, all topics covered before drafting.
- The rules of engagement for the human: the responsibility to convey as much meaning as possible, without expecting the LLM to fill gaps. The LLM will fill gaps, but the human should strive for clarity and completeness.
- The available commands (`/svp:save`, `/svp:quit`, `/svp:help`, `/svp:hint`, `/svp:status`, `/svp:ref`).
- The ability to provide reference documents and enable optional integrations (see Section 7.2).

### 7.2 Reference Documents

At any point during the stakeholder dialog (or before it begins), the human can provide reference documents that should inform the specification. These might include:

- A methods section from a paper the human is replicating.
- A lab protocol or standard operating procedure.
- A grant proposal describing the desired analysis.
- A technical specification for equipment or data formats.
- A reference paper describing an algorithm to be implemented.
- A colleague's code repository (via the GitHub MCP, if configured).
- Any other document that carries domain knowledge relevant to the project.

Supported formats: PDF, markdown, plain text, and URLs. When a reference document is added:

1. The document is copied to the `references/` directory in the project workspace.
2. A subagent reads the document and produces a structured summary -- saved to `references/index/`. The summary includes: what the document is, what topics it covers, key terms, and which sections are most relevant. For PDFs, the subagent uses Claude's native document understanding capabilities to read the content.
3. The summary is made available as context to subsequent agent invocations. The full document remains accessible for on-demand retrieval if any agent needs detail.

For GitHub repositories (via the GitHub MCP), the same indexing pattern applies: a subagent explores the repository structure, key modules, APIs, and documentation, and produces a summary. The full repository remains accessible via MCP for selective file-level retrieval.

The agents use reference documents as informational context -- they interrogate the human about which aspects to include, what to modify, and what to leave out. Reference documents do not replace the Socratic dialog; they supplement it. The stakeholder spec remains the single source of truth for intent, even when it draws on reference material. The reference documents themselves are preserved in the project workspace and included in the final repository for traceability.

### 7.3 Socratic Dialog

The stakeholder dialog agent conducts a structured conversation to produce the stakeholder spec. The conversation is maintained through a conversation ledger (`ledgers/stakeholder_dialog.jsonl`) -- an append-only file that records every exchange. Each turn of the dialog is a fresh agent invocation with the full ledger as context, ensuring statelessness while preserving conversational continuity across turns and sessions.

Its behavior:

- As one of its first questions, explicitly asks: "Do you have any reference documents -- papers, protocols, data format specifications, or other materials that describe what you want to build?" If yes, the human provides file paths (using Claude Code's `@` syntax, e.g., `@~/Documents/methods.pdf`) or URLs. The agent indexes each document and briefly summarizes what it found before continuing. The human can also add documents later at any time using the `/svp:ref` command.
- Asks one question at a time.
- Waits for an answer before proceeding.
- When consensus on a topic is reached, explicitly confirms and moves to the next topic.
- Actively surfaces contradictions, edge cases, and unstated assumptions in the human's requirements.
- Probes adversarial scenarios: what should happen when input is malformed, when resources are unavailable, when data has unexpected characteristics.
- When reference documents are available, draws on their summaries to ask more specific and informed questions -- and retrieves full document details on demand when needed. Always confirms interpretations with the human rather than assuming the reference documents are authoritative.
- Does not make technical architecture decisions -- those belong in the blueprint. The stakeholder spec describes what the system must do, not how it does it.

### 7.4 Draft-Review-Approve Cycle

When all topics have been discussed:

1. The agent asks for permission to write the initial draft.
2. The agent produces the complete stakeholder spec document.
3. The human reads the document (this is a stated human duty, not optional).
4. The human chooses from explicit options: **APPROVE**, **REVISE**, or **FRESH REVIEW**.
5. If **APPROVE**: the spec is finalized with a completion marker (`<!-- SVP_APPROVED: timestamp -->`) and the pipeline advances to Stage 2.
6. If **REVISE**: the human may invoke `/svp:help` to formulate a precise hint about what should change and why (see Section 14.4). The hint is forwarded to the stakeholder dialog agent for the next draft iteration. The agent incorporates the revisions (and any forwarded hint) and presents the revised draft. The cycle repeats.
7. If **FRESH REVIEW**: a distinct stakeholder spec reviewer agent receives only the document, project context, and reference summaries -- no dialog ledger. It reads the document cold, identifying gaps, contradictions, underspecified areas, and missing edge cases, and produces a structured critique. The human reads the critique and decides: accept the critique (take it to revision), dismiss it (approve as-is), or request another fresh review. Review cycles are unbounded -- the human can request as many as they want. Each review cycle that results in a revision increments the document version number. Review critiques are stored in workspace logs for diagnostic reference but are not delivered to the final repository.

**Scenarios -- Gates 1.1/1.2 (spec draft approval and revision).**
*Best case:* The Socratic dialog was thorough. The agent produces a complete spec draft. The human reads it, finds it accurate, and approves. Pipeline advances to Stage 2. Time: one draft, one approval.
*Worst case:* The draft has gaps or misinterpretations. The human requests fresh reviews and multiple revisions, using the Help Agent to formulate precise hints about what should change. In the most extreme case, the human realizes during revision that their fundamental understanding of their requirements has changed -- the agent recommends a full spec restart, and the entire Socratic dialog begins again from scratch. Time: multiple revision rounds, potentially a full restart of Stage 1.

### 7.5 Output

An approved `stakeholder.md` file with completion marker, saved to the project workspace. The pipeline state is updated to record Stage 1 completion. A session boundary fires.

### 7.6 Spec Revision Modes

The stakeholder spec may need modification after initial approval -- during blueprint authoring, blueprint alignment checking, unit verification, or integration testing. SVP distinguishes two modes of spec modification, plus a temporary working-notes mechanism for the blueprint dialog.

**Working notes (during blueprint dialog only).** When the blueprint dialog (Section 8.1) surfaces a narrow spec ambiguity that only became visible during technical decomposition -- for example, "the spec says 'process electrodes independently' but doesn't specify whether output should be merged afterward" -- the human provides a short answer. The answer is appended to the stakeholder spec as a working note with a provenance marker ("Working note added during blueprint authoring, Stage 2, in response to: [question]"). The blueprint dialog continues without interruption.

At every iteration boundary -- whether the blueprint alignment succeeds or fails -- all working notes are incorporated into the spec body through a focused revision by the Socratic dialog agent in revision mode. The result is always a clean, cohesive spec with no appended patches. Working notes from failed iterations cannot become stale because they are absorbed into the spec before the next iteration begins.

If the blueprint checker determines that a working note contradicts the original spec text rather than clarifying it, the issue escalates to a targeted revision.

**Targeted Spec Revision.** A correction triggered when the blueprint checker, diagnostic agent, or human (via `/svp:redo` or `/svp:hint`) identifies a localized error, contradiction, or gap in the spec. The stakeholder dialog agent is invoked in **revision mode**: it receives the current approved spec, the specific critique or issue description, any pending human domain hint from the triggering gate (see Section 14.4), and all reference summaries. It then conducts a focused Socratic dialog with the human about *just that issue* -- not the entire spec. This dialog uses its own conversation ledger (`ledgers/spec_revision_N.jsonl`). When the revision is agreed upon, the spec is amended, versioned with a diff summary that records the critique that triggered the revision, and the pipeline restarts from Stage 2 (fresh blueprint generation from the amended spec). All downstream artifacts (blueprint, units, tests) are regenerated from scratch. The unrevised portions of the spec are untouched.

The targeted revision dialog is scoped. The stakeholder dialog agent in revision mode is instructed to: address the identified issue, probe for related implications ("does this change affect anything else you told me earlier?"), and confirm with the human that the revision is complete. It does not reopen settled topics. If during the focused dialog it becomes clear that the problem is pervasive -- the human realizes their fundamental understanding was wrong -- the agent recommends escalation to a full spec restart, and the human decides.

**Full Spec Restart.** The spec is fundamentally wrong or the human's understanding of their own requirements has changed substantially. This is rare and always human-initiated -- the system never forces a full restart; it recommends it. The human explicitly confirms that they want to redo the full stakeholder Socratic dialog from scratch. A fresh stakeholder dialog agent begins with no ledger history, producing a new spec. All downstream artifacts are regenerated.

The classification between modes is a human judgment call, assisted by the agent. The default assumption is targeted revision -- the most common case. The human escalates to full restart only when they recognize that the problem is pervasive.

---

## 8. Stage 2: Blueprint Generation and Alignment

### 8.1 Blueprint Authoring

A fresh blueprint author agent receives the approved stakeholder spec and reference summaries and conducts a Socratic dialog with the human about system decomposition. This dialog is maintained through a conversation ledger (`ledgers/blueprint_dialog.jsonl`) using the same ledger-based multi-turn pattern as the stakeholder dialog.

The blueprint dialog focuses on **decomposition structure** -- how the system should be broken into conceptual units -- not on implementation details. The domain expert often has real knowledge about decomposition even if they cannot code. A neuroscientist knows that spike sorting has a detection phase, a feature extraction phase, and a clustering phase. A climate scientist knows that their model has an initialization step, a time-stepping loop, and a post-processing stage. This knowledge is valuable and should inform the blueprint directly.

The blueprint dialog agent's behavior:

- Proposes an initial high-level decomposition based on the stakeholder spec.
- Asks the human whether the decomposition matches their conceptual model of the problem: "Does it make sense to separate detection from feature extraction, or are these one conceptual step in your workflow?"
- Asks about data flow between phases: "After filtering, does the data go to one analysis path or does it fork into multiple independent analyses?"
- Asks about boundaries the human considers important: "Is there a natural point where you'd want to inspect intermediate results?"
- Keeps questions at the domain level -- never asks about classes, data structures, or algorithms.
- When a decomposition question reveals that the stakeholder spec is ambiguous on a point, the agent distinguishes between clarification and contradiction (see Section 7.6). For clarifications, the agent proposes a working note, confirms it with the human, appends it to the spec, and continues. When approving or refining a working note, the human may invoke `/svp:help` to formulate a precise rewording (see Section 14.4); the hint is forwarded to the blueprint author agent. For contradictions or gaps, the agent pauses the dialog and initiates a targeted spec revision.

When the decomposition dialog is complete, the agent produces the full technical blueprint. Before submitting the blueprint for alignment checking, the human may review it and invoke `/svp:help` to formulate observations about the decomposition structure (see Section 14.4). Decomposition-level hints from the human carry additional weight because the human is a domain expert on how the problem should be structured -- the Blueprint Author Agent is instructed to weigh such hints more heavily than implementation-level observations. The hint is forwarded to the Blueprint Checker Agent as additional context.

**Unit definition template.** Each unit is defined by a rigid template with three format tiers:

**Tier 1 -- Free prose:**
- **Description:** what the unit does, in plain language.

**Tier 2 -- Valid Python parseable by `ast`:**
- **Machine-readable signatures:** import statements declaring all referenced types, followed by type-annotated function and class signatures with ellipsis bodies. Example:

```python
import numpy as np
from typing import List
from unit_2_types import SpikeEvent

def detect_spikes(recording: np.ndarray, threshold: float) -> List[SpikeEvent]: ...
def validate_recording(recording: np.ndarray) -> bool: ...
```

The stub generator parses these using Python's standard `ast` module and produces stub files mechanically (replacing `...` with `raise NotImplementedError()`). The blueprint author agent is instructed to produce signatures in this format. The blueprint checker validates that all signatures are syntactically valid Python and that all referenced types have corresponding import statements.

- **Invariants:** pre-conditions and post-conditions as `assert` statements with descriptive messages. Example:

```python
# Pre-conditions
assert recording.ndim == 1, "Recording must be a 1D array (single channel)"
assert threshold > 0, "Detection threshold must be positive"

# Post-conditions
assert all(e.timestamp >= 0 for e in result), "All spike timestamps must be non-negative"
assert all(e.channel_id < recording.shape[0] for e in result), "Channel IDs must be valid"
```

**Tier 3 -- Structured text following defined patterns:**
- **Error conditions:** each entry specifies exception type, description, and triggering condition. Example:
  ```
  ValueError: "Recording array is empty" -- when recording.size == 0
  ValueError: "Threshold below noise floor" -- when threshold < estimated_noise
  ```
- **Behavioral contracts:** discrete testable claims as a list. Each claim is a single sentence that can be verified by a test. Example:
  ```
  - Returns an empty list when no spikes exceed the threshold.
  - Spike timestamps are sorted in ascending order.
  - Does not modify the input recording array.
  ```
- **Dependencies:** upstream unit references by name and unit number. Backward-only -- each unit may depend on previously defined units but never on units defined later.

The blueprint author agent is instructed to produce units in this format. The blueprint checker validates all fields are present, well-formed, and internally consistent. The stub generator operates only on the Python-parseable fields.

**Unit granularity.** A unit is the smallest piece of code that can be independently tested against its blueprint contract without requiring any other unit's implementation to exist. A unit might be a single function, a class, or a small module -- the blueprint author decides based on the problem's structure, informed by the decomposition dialog. The testability constraint is the hard rule:

- If something cannot be tested in isolation against defined inputs and outputs, it is either too small (merge it with another unit) or too entangled (decompose it differently).
- If unit B depends on unit A, unit B's tests use unit A's contract (its type signatures and promised behavior) to create mocks, never unit A's implementation. This means unit boundaries must be clean interfaces, not internal implementation details.
- The blueprint author agent is instructed to prefer units that are coarse enough to have meaningful contracts but fine enough that each unit's test suite exercises a single coherent responsibility.

**Unit ordering.** Units are ordered by dependency in topological order. The first unit is the first piece of domain logic -- infrastructure setup (directory structure, dependency file, environment configuration) is handled by the pre-Stage-3 infrastructure step (see Section 9), not by a blueprint unit. The entry point unit is the last unit in the topological order, because it depends on all other units. It goes through the standard test-stub-implement-verify cycle like every other unit.

The backward-only dependency constraint produces a topological ordering: deterministic build sequence, bounded context per unit, and structurally impossible circular dependencies.

**Context budget validation.** The blueprint must fit within the effective context budget (see Section 1.3). The blueprint's structure must support selective extraction -- the system must be able to extract a single unit's definition plus upstream contract signatures without loading the full blueprint. This is validated during alignment checking.

**Scenarios -- Gates 2.1/2.2 (working note approval and blueprint review).**
*Best case:* The decomposition dialog completes without encountering spec ambiguity. The agent produces a blueprint. The human reviews it, finds the decomposition matches their conceptual model, and submits it for alignment checking. Time: one dialog, one blueprint, no working notes.
*Worst case:* The dialog repeatedly uncovers spec ambiguities -- some are clarifications (working notes), but one is a contradiction that forces a targeted spec revision, pausing the blueprint dialog entirely. After the spec is amended, the blueprint dialog restarts from scratch. The human reviews the resulting blueprint and, using the Help Agent, identifies a decomposition issue that the agent missed. The hint is forwarded to the checker as additional context. Time: multiple dialog restarts and spec revisions before the blueprint reaches the alignment checker.

### 8.2 Blueprint Alignment Check

A fresh blueprint checker agent -- different from the author -- receives the stakeholder spec (including any working notes from the blueprint dialog), the blueprint, and reference summaries, and verifies alignment. The checker also validates structural requirements: machine-readable signatures are present and parseable (valid Python via `ast`) for every unit, all referenced types have corresponding import statements, per-unit worst-case context budget is within threshold, selective unit extraction is possible, and any working notes are consistent with the original spec text.

**Per-unit context budget validation.** The blueprint checker validates that the fixed context load for each unit (unit definition plus upstream contract signatures) does not exceed 65% of the available context budget. The remaining 35% is reserved for variable context in worst-case fix ladder invocations (failing code, error output, diagnostic analysis, human hint). Units exceeding the threshold are flagged for decomposition. The 65/35 threshold is configurable in `svp_config.json`.

**Report most fundamental level.** When the checker identifies problems at multiple levels of the document hierarchy (spec and blueprint simultaneously), it reports only the deepest problem. Spec problems supersede blueprint problems.

Three outcomes:

- **Spec is the problem:** the checker identifies a gap, contradiction, or inconsistency in the stakeholder spec (including between working notes and the original text) that the blueprint cannot faithfully represent. The checker produces a precise critique describing the specific issue. The human may invoke `/svp:help` to formulate a hint about why alignment is failing (see Section 14.4); the hint is forwarded alongside the critique. Before the pipeline enters targeted spec revision, all accumulated working notes are incorporated into the spec body through a focused revision by the Socratic dialog agent. Then the targeted revision addresses the identified issue. The spec is amended and versioned. A fresh blueprint author agent restarts the blueprint dialog from scratch with the amended spec -- the decomposition conversation begins anew because the spec change may affect the structure.
- **Blueprint is the problem:** the checker identifies a deviation, omission, structural issue, or format violation in the blueprint relative to the spec. The human may invoke `/svp:help` to formulate a hint (see Section 14.4); the hint is forwarded to the next blueprint author iteration. Before the fresh blueprint dialog starts, all accumulated working notes are incorporated into the spec body. A fresh blueprint author agent restarts the blueprint dialog from scratch, with the checker's critique (and any forwarded hint) as additional context. The alignment check is then repeated with a fresh checker agent.
- **Alignment is confirmed:** the checker blesses the blueprint. The human chooses from explicit options: **APPROVE**, **REVISE**, or **FRESH REVIEW**. If **FRESH REVIEW**: a distinct blueprint reviewer agent receives only the blueprint, the stakeholder spec, project context, and reference summaries -- no dialog ledger. It reads the documents cold and produces a structured critique. The human reads the critique and decides: accept (take critique to revision), dismiss (approve as-is), or request another fresh review. Review cycles are unbounded. If **APPROVE**: proceed to Pre-Stage-3 infrastructure. If **REVISE**: return to a fresh blueprint author iteration with the human's feedback.

**Scenarios -- Gate 2.1/2.2 (blueprint approval and post-review decision).**
*Best case:* The checker confirms alignment on the first attempt. The human approves. The pipeline advances to Pre-Stage-3 infrastructure.
*Worst case:* The checker identifies a spec problem. The human uses the Help Agent to formulate a hint about why alignment is failing. Working notes are absorbed, a targeted spec revision is initiated, followed by a fresh blueprint dialog from scratch. The alignment check is repeated -- and fails again, this time identifying a blueprint problem. Another fresh blueprint dialog restarts with the critique. The cycle continues until alignment is confirmed or the iteration limit is reached (see Section 8.3).

### 8.3 Alignment Loop

The blueprint generation and checking cycle may iterate. On each iteration:

- All accumulated working notes from the previous iteration are incorporated into the spec body through a focused revision by the Socratic dialog agent in revision mode. The spec entering each new iteration is always clean.
- A fresh author agent conducts a new decomposition dialog with the human (never resumes a prior dialog) and produces the blueprint.
- A fresh checker agent evaluates alignment.
- Rejection reasons are logged to the project's log directory.

This continues until alignment is confirmed, the human intervenes, or the iteration limit is reached.

**Iteration limit:** configurable, default 3. After the configured number of failed alignment attempts, the system stops, generates a diagnostic summary explaining why alignment is not converging (based on patterns in the accumulated rejection reasons), presents it to the human, and requires a decision. The gate response options are **REVISE SPEC**, **RESTART SPEC**, and **RETRY BLUEPRINT**. The diagnostic summary recommends which option fits the situation. **REVISE SPEC** initiates a targeted spec revision on the identified issue, then restarts from Stage 2. **RESTART SPEC** initiates a full stakeholder Socratic dialog from scratch. **RETRY BLUEPRINT** resets the alignment iteration counter and tries again with a fresh blueprint author. The human may invoke `/svp:help` to formulate a hint about why convergence is failing (see Section 14.4); the hint is forwarded to the revision agent or next blueprint author iteration. The rationale: multiple independent agents failing to produce an aligned blueprint from the same spec is strong evidence that the spec is underspecified or contradictory.

**Convergence signal.** If multiple independent agents reading the same spec produce similar blueprint decompositions, the spec is clear. If they produce divergent structures, the spec is underspecified. Non-convergence is a diagnostic signal about spec quality, not a problem to solve at the blueprint level.

**Human intervention.** The human may invoke `/svp:hint` at any time during this stage to receive a diagnostic analysis of why the loop is not converging. The human may also choose to initiate a spec revision at any time without waiting for the iteration limit.

**Scenarios -- Gate 2.3 (iteration limit reached).**
*Best case:* The iteration limit is never reached. The alignment loop converges within 1-2 attempts. This gate is never activated.
*Worst case:* Three alignment attempts fail. The diagnostic summary identifies a pattern (e.g., "every blueprint attempt underspecifies error handling"). The human uses the Help Agent to formulate a hint identifying the root cause -- their spec omitted critical domain-specific error types. The hint is forwarded to a targeted spec revision dialog. The spec is amended, the pipeline restarts from Stage 2 with a fresh blueprint dialog, and the alignment loop begins again. In the most extreme case, the human realizes the problem is pervasive and opts for a full spec restart -- the entire pipeline returns to Stage 1.

### 8.4 Output

A blessed `blueprint.md` file with completion marker, saved to the project workspace. The pipeline state is updated to record Stage 2 completion, including the number of alignment iterations required. A session boundary fires.

---

## 9. Pre-Stage-3: Infrastructure Setup

Before any unit verification begins, a deterministic infrastructure step prepares the build environment. This step is fully mechanical -- no LLM involvement.

### 9.1 Dependency Extraction and Environment Creation

1. A deterministic script scans all machine-readable signature blocks across all units in the blessed blueprint, extracting every external import statement.
2. The script produces a complete dependency list from the extracted imports.
3. The script creates the Conda environment and installs all packages.

### 9.2 Import Validation

After environment creation, the script validates that every extracted import statement actually resolves in the created environment by executing each import:

```bash
conda run -n {env_name} python -c "from scipy.signal import ShortTimeFFT"
```

This catches version-specific API issues (e.g., a class that exists only in SciPy 1.12+ when an earlier version was installed) before they surface as confusing red-run errors during Stage 3.

If any import fails to resolve, this is a blueprint problem -- the blueprint specified a dependency that cannot be satisfied. The pipeline returns to blueprint revision.

### 9.3 Directory Structure and Scaffolding

The script creates the source and test directory structure based on the blueprint's unit definitions: `src/unit_N/` and `tests/unit_N/` for each unit.

### 9.4 Output

A working Conda environment with all dependencies installed and validated. A complete project directory structure ready for unit verification. This step is logged in the final repository as the first commit (Conda environment file, dependency list, directory structure). The pipeline state is updated to record pre-Stage-3 completion, including setting `total_units` to the number of units defined in the blueprint. A session boundary fires.

**`total_units` invariant:** The pipeline state field `total_units` must be set to the blueprint's unit count during infrastructure setup. It is required by the unit completion logic to determine when all units are done and Stage 4 should begin. If `total_units` is null at unit completion time, `update_state.py` falls back to counting `## Unit N` headings in `blueprint.md` -- but this is a recovery path, not normal operation.

---

## 10. Stage 3: Unit-by-Unit Verification

Units are processed in topological order as defined by the blueprint. The first unit is the first piece of domain logic. The last unit is the entry point. Each unit goes through the following sequence. No unit begins until the previous unit is fully verified.

**Scenarios -- Per-unit verification (best and worst case).**
*Best case:* Tests are generated, the red run confirms they demand real behavior, the implementation is generated, the green run passes all tests, and coverage review finds no gaps. The human makes no decisions -- the unit proceeds autonomously from test generation through verification. Time per unit: minutes of compute, zero human interaction.
*Worst case:* The green run fails. The human determines the test is wrong -> test fix ladder runs -> fails -> diagnostic agent determines the blueprint contract is untestable -> document revision -> pipeline restarts from Stage 2. Alternatively: the test is correct -> implementation fix ladder runs -> fails -> diagnostic escalation -> human chooses "fix implementation" -> fresh agent with diagnostic guidance fails -> document revision -> pipeline restarts from Stage 2. In the absolute worst case for a single unit, the human goes through both the test fix ladder and the implementation fix ladder before arriving at a document revision that restarts the entire pipeline.

### 10.1 Test Generation

A test agent receives:

- The current unit's definition from the blueprint (description, inputs, outputs, errors, invariants, contracts, machine-readable signatures).
- The contracts of upstream dependencies (from the blueprint, not from their implementations).

These are provided as the task prompt when the main session spawns the test agent. The test agent's own system prompt (its agent definition file) contains only its behavioral instructions: how to write tests, what framework to use, output format requirements, and the constraint that it must not attempt to see any implementation.

The test agent generates a complete pytest test suite for the unit, including synthetic test data that matches any data characteristics described in the stakeholder spec. The test agent does not see any implementation.

**Synthetic data assumption declarations.** The test agent must declare its synthetic data generation assumptions as part of its output -- for example, "motion artifacts modeled as Gaussian noise with sigma=0.5" or "inter-spike intervals drawn from exponential distribution with lambda=50Hz." These assumptions are presented to the human at the test validation gate. The human evaluates whether the assumptions match their real domain data. If not, the human can reject and provide a hint (via the help agent's collaborative formulation process) about what realistic data looks like.

The test agent uses the most capable available model by default (`claude-opus-4-6`), as test correctness is the foundation of the entire verification strategy. Wrong tests produce false confidence, which is the most dangerous failure mode in the pipeline.

### 10.2 Stub Generation

A deterministic script -- no LLM involvement -- reads the machine-readable signature block from the current unit's blueprint definition and generates a stub module. The script parses the Python signature block using the standard `ast` module and produces a Python file containing all function and class signatures where every function body raises `NotImplementedError`. The script also generates stubs or mocks for upstream dependencies based on their contract signatures, so the test suite has something to import against.

**Importability invariant.** The generated stub must be importable without error. Blueprint signature blocks may contain module-level `assert` statements (used as invariant documentation in Tier 2), but these assertions test runtime behavior that stubs cannot satisfy -- stub functions raise `NotImplementedError`, so any module-level assertion that calls a stub function will fail at import time, blocking test collection entirely. The stub generator must strip all module-level `assert` statements from the parsed AST before producing the stub file. Assertions inside function bodies are not affected (they are replaced along with the rest of the body by `raise NotImplementedError()`).

This step is fully mechanical. The script parses structured Python from the blueprint and produces code. If the signatures are malformed or fail `ast.parse()`, the script fails with a clear error -- this is caught and reported as a blueprint format problem, triggering blueprint revision.

### 10.3 Red Run

The main session runs the test suite against the stub via bash command. Every test must fail. This validates that the tests are actually testing behavior, not asserting something vacuous or testing their own fixtures.

Three outcomes:

- **All tests fail:** the tests are structurally sound. They demand behavior that does not yet exist. Proceed to implementation.
- **Some tests pass against the stub:** those tests are defective -- they pass without any real implementation, meaning they assert nothing meaningful. The test suite is regenerated by a fresh test agent, with the specific passing tests identified as defective and the reason explained. The red run is repeated.
- **Tests error (won't run):** syntax problems, import issues, or malformed fixtures. The test suite is regenerated by a fresh test agent with the error output provided. The red run is repeated.

If the test suite fails the red run after the configured number of attempts (default 3; this retry count is tracked in the pipeline state as `red_run_retries` and reset when the unit advances past the red run), the diagnostic agent is invoked to determine whether the blueprint's contract for this unit is insufficiently specified for meaningful test generation.

### 10.4 Implementation

An implementation agent receives the same unit definition from the blueprint and generates the Python implementation. The implementation agent does not see the tests. This separation ensures that if the blueprint contains an ambiguity, the two agents are less likely to resolve it identically, causing a test failure rather than a silent coherent mistake.

As with the test agent, the unit definition and upstream contracts are provided as the task prompt. The implementation agent's system prompt contains only its behavioral instructions.

### 10.5 Green Run

The main session runs the test suite against the real implementation via bash command. All tests must pass. This is the green phase of the red-green cycle: the same tests that failed against the stub must now pass against the implementation.

### 10.6 On Pass: Coverage Review

A coverage review agent reads the blueprint and the passing test suite to identify behaviors the blueprint implies but no test covers. Missing coverage is added. Any newly added tests go through their own red-green validation: they must be validated as meaningful by demonstrating that they fail for the right reason -- not merely because the stub raises `NotImplementedError`. This validation is performed as an atomic operation within the coverage review step -- the main session verifies the new tests fail (confirming they test real behavior), then verifies they pass against the implementation, within a single coverage review invocation. It does not constitute a separate pipeline stage or sub-stage. The specific mechanism for meaningful failure validation is a blueprint concern.

**Green-run failure path.** If any newly added coverage test fails the green run (the implementation does not satisfy a behavior the blueprint implies but no original test covered), this is treated as a standard unit test failure, following the simplified fix ladder (Section 10.8). If the implementation fix succeeds, all tests (original plus new) are re-run, followed by one additional coverage review pass. If that second coverage review produces tests that fail the green run, escalate directly to diagnostic -- no further fix attempts. The repeated coverage gap pattern is treated as a diagnostic signal of a document-level problem.

Only when the coverage review agent is satisfied and all tests pass does the unit proceed.

### 10.7 On Fail: Test Validation

Before assuming the implementation is wrong, the diagnostic agent produces a structured analysis that explains the failing test's intent to the human in plain language, including any synthetic data assumptions. This is a single-shot invocation -- the diagnostic agent produces its explanation and recommendation, the main session presents it to the human, and the human makes a decision from explicit options.

For example: "This test checks that spike sorting rejects any waveform shorter than 0.3 milliseconds -- is that correct given your data? (Data assumption: waveforms modeled as 1ms Gaussian pulses with 0.1ms jitter.)"

- **TEST CORRECT** -- the test is right, the implementation needs fixing. Proceed to the implementation fix ladder. The human may invoke `/svp:help` to formulate a hint about why the implementation is likely wrong (see Section 14.4); the hint is forwarded to the implementation agent on its next attempt.
- **TEST WRONG** -- the test doesn't match the human's requirements. The pipeline proceeds to the test fix ladder:
  1. Fresh test agent receives: the rejected test code, the test failure error output, the reason the human rejected the test, the unit definition and upstream contracts from the blueprint, and any forwarded hint. Red run validation, then green run.
  2. If the fresh agent's tests also fail: the human is re-involved. The human may invoke `/svp:help` to reassess with the Help Agent and produce a hint. A single additional attempt is made: a fresh test agent receives the accumulated context from all prior attempts plus the new hint. If this hint-assisted attempt also fails, the diagnostic agent is invoked to determine whether the issue is a blueprint-level problem (the unit's contract is untestable as specified). No further test fix attempts are made -- the ladder is exhausted.

**Scenarios -- Gate 3.1 (is the test correct?).**
*Best case:* The green run fails. The diagnostic agent explains the failing test in plain language. The human confirms the test is correct -- the problem is in the implementation. The implementation fix ladder begins. Time: one human decision.
*Worst case:* The human determines the test is wrong. The test fix ladder runs: fresh agent fails, the human re-engages with the Help Agent and provides a hint, the hint-assisted attempt also fails. The diagnostic agent determines the unit's blueprint contract is untestable as specified -- the problem is at the document level, not the test level. The pipeline restarts from Stage 2 after a document revision. Time: two failed test attempts, one human assessment session, a diagnostic escalation, and a full pipeline restart.

### 10.8 Implementation Fix Ladder

A deterministic escalation sequence when tests fail and the test is confirmed correct:

1. **Fresh agent attempt.** A fresh implementation agent receives: the failing implementation code, the test failure output, the diagnostic agent's structured analysis, the unit definition and upstream contracts from the blueprint, and any forwarded hint. Tests re-run.
2. **Diagnostic escalation.** If the fresh agent's implementation also fails, the diagnostic agent is invoked with the three-hypothesis discipline (Section 10.9).

**Position-aware ladder advancement.** The state-update script that handles green-run failures must check the current fix ladder position before advancing. The ladder progresses through a fixed sequence: `None -> fresh_impl -> diagnostic -> diagnostic_impl -> exhausted`. When a green run fails, the handler advances to the *next* rung, not to a fixed target. Specifically: if the ladder is at `None`, advance to `fresh_impl` and route to implementation; if already at `fresh_impl`, advance to `diagnostic` and route to the diagnostic agent; if at `diagnostic`, advance to `diagnostic_impl` and route to implementation; if at `diagnostic_impl`, the ladder is exhausted and the pipeline escalates to human intervention. The handler must never attempt to re-enter the current position -- this produces a `TransitionError` that, if caught silently, leaves the state unchanged and creates an infinite loop.

### 10.9 Diagnostic Escalation: Three-Hypothesis Discipline

The diagnostic agent receives:

- The stakeholder spec.
- The blueprint (current unit's section plus upstream contracts).
- The current unit's tests and failing implementation(s).
- The error output from test runs.

Before converging on a diagnosis, the agent must articulate a plausible case for the failure at each of three levels:

- **Implementation-level:** the unit code is wrong relative to a correct blueprint. Remedy: one more implementation attempt with diagnostic guidance.
- **Blueprint-level:** the unit's definition, contracts, or decomposition is wrong relative to a correct stakeholder spec. Remedy: restart from Stage 2 (fresh blueprint dialog and generation).
- **Spec-level:** the stakeholder requirements are incomplete or contradictory. Remedy: targeted spec revision (Section 7.6) on the identified issue, then restart from Stage 2.

The forced three-hypothesis discipline prevents the LLM's natural bias toward the easiest diagnosis.

**Dual-format output.** The diagnostic agent produces output in two formats: prose explanation for the human, followed by a structured summary block for the routing layer:

```
[PROSE]
Here's what I think happened... (human-readable explanation)

[STRUCTURED]
UNIT: 4
HYPOTHESIS_1: implementation -- off-by-one in loop boundary
HYPOTHESIS_2: blueprint -- contract doesn't specify boundary behavior
HYPOTHESIS_3: spec -- no mention of boundary handling for edge electrodes
RECOMMENDATION: implementation
```

Terminal status line: `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec`.

The main session presents the prose to the human, and the human makes the call from explicit options:

- **FIX IMPLEMENTATION**: one fresh agent attempt with the diagnostic guidance and any optional human hint. The human may invoke `/svp:help` to formulate a hint (see Section 14.4). If this attempt fails, escalate to document revision. No further implementation attempts.
- **FIX BLUEPRINT**: the blueprint's contracts or decomposition is wrong relative to a correct stakeholder spec. The pipeline restarts from Stage 2 (fresh blueprint dialog and generation). All downstream artifacts are regenerated from scratch.
- **FIX SPEC**: the stakeholder requirements are incomplete or contradictory. A targeted revision dialog addresses just the identified problem (Section 7.6), then the pipeline restarts from Stage 2. All downstream artifacts are regenerated from scratch.

At this gate, hint forwarding follows the standard mechanism (see Section 14.4). If the hint contradicts the blueprint contract, the agent returns `HINT_BLUEPRINT_CONFLICT: [details]` and the routing script presents the conflict as a human decision gate.

**Scenarios -- Gate 3.2 (three-hypothesis decision after diagnostic escalation).**
*Best case:* The human chooses FIX IMPLEMENTATION. The fresh implementation attempt succeeds -- the diagnostic agent's guidance was sufficient. Tests pass, the unit proceeds to coverage review and completion. Time: one human decision, one implementation attempt.
*Worst case:* The human chooses FIX IMPLEMENTATION. The fresh agent fails. The issue is escalated to document revision. The spec or blueprint is revised, and the pipeline restarts from Stage 2. All downstream artifacts are regenerated from scratch. Time: one failed implementation attempt, a document revision dialog, and a full pipeline restart.

### 10.10 Unit Completion

A unit is verified when:

- All tests passed the red run (failed against stub).
- All tests passed the green run (passed against implementation).
- The coverage review agent has confirmed complete coverage.
- Any cascade re-validation from earlier stages has been resolved.

The unit's code and tests are saved to the workspace. A completion marker file is written to `.svp/markers/unit_N_verified`. The pipeline state is updated by the state-management script, which validates that all completion criteria are met before writing the new state. A session boundary fires. The next unit begins in a fresh session.

### 10.11 Context Isolation

Each unit is processed in a fresh context window containing only:

- The stakeholder spec.
- The current unit's definition extracted from the blueprint (not the full blueprint).
- The contract signatures of upstream dependencies (extracted from the blueprint).

No prior unit's implementation code is loaded. No full blueprint is loaded. Each unit is built with the assumption that all other units work according to their blueprint contracts. This keeps context bounded and predictable regardless of how many units have been verified.

The extraction of unit definitions and upstream contracts from the blueprint is a deterministic operation performed by a script, not by LLM summarization. The extracted content is passed to subagents as the task prompt (see Section 3.7).

---

## 11. Stage 4: Integration Testing

### 11.1 Integration Test Generation

After all units pass individual verification, an integration test author agent generates tests that cover cross-unit interactions. This agent receives a lean task prompt: the stakeholder spec plus contract signatures from all units. The full blueprint is not loaded into the task prompt. The agent reads specific source files on demand from disk when it needs implementation detail. This keeps the task prompt bounded while preserving access to both domain intent (stakeholder spec) and implementation detail (code on demand).

The integration tests specifically target behaviors that no single unit owns:

- Data flow across the full chain of units.
- Resource contention scenarios.
- Timing dependencies.
- Error propagation across unit boundaries.
- Emergent behavior from unit composition.

In addition to contract-based integration tests, the agent must write at least one end-to-end test that validates a complete input-to-output scenario described in the stakeholder spec, checking not just types and shapes but domain-meaningful output values. This catches cases where all contracts are honored but the composed behavior is subtly wrong in a domain-specific way (e.g., double-normalization, unit conversion errors, scientifically meaningless outputs).

### 11.2 Integration Test Execution

The main session runs the integration test suite against the assembled system via bash command. This is a deterministic step.

### 11.3 On Pass

Proceed to Stage 5.

### 11.4 On Fail

The diagnostic agent applies the same three-hypothesis discipline, but with an inverted prior: integration failures are disproportionately caused by blueprint-level issues -- missing cross-cutting concerns, underspecified contracts, emergent behaviors the blueprint didn't anticipate. The diagnostic agent produces dual-format output (prose + structured block).

The human chooses from explicit options:

- **ASSEMBLY FIX**: the units are correct individually, but their assembly has a localized error that does not reflect a document-level problem. An assembly fix is a narrowly scoped code change -- applied to one or more existing units at their interface boundaries -- that corrects how units connect without changing what any unit does according to its contract.

  Assembly fix ladder (three attempts):
  1. **First attempt:** A fresh implementation agent is invoked with the integration test failure output, the affected unit's blueprint definition, diagnostic guidance, and an explicit constraint that the fix must be limited to interface boundary code and must not alter any unit's internal behavior. The fix is applied, the affected unit's existing tests are re-run (ensuring the fix didn't break the unit's contract), then integration tests are re-run. If unit tests fail, this was not an assembly fix -- escalate to document fix.
  2. **Second attempt:** A fresh implementation agent receives the first attempt's code and failure output plus diagnostic guidance. Same validation sequence.
  3. **Third attempt:** The human is pulled in. Help agent available (reactive mode). The human can provide a hint. A fresh implementation agent receives everything plus the hint. Same validation sequence. If this attempt fails or any attempt breaks unit tests, the assembly fix ladder is exhausted. The human is presented with Gate 4.2: **FIX BLUEPRINT** or **FIX SPEC** (see below).

- **FIX BLUEPRINT**: the blueprint's contracts didn't capture a cross-cutting concern, or a unit's contract itself was wrong. This is a blueprint-level problem. The pipeline restarts from Stage 2 (fresh blueprint dialog and generation). All downstream artifacts are regenerated from scratch.
- **FIX SPEC**: the stakeholder requirements are incomplete or contradictory on the cross-unit interaction. A targeted spec revision (Section 7.6) addresses just the identified concern, then the pipeline restarts from Stage 2. All downstream artifacts are regenerated from scratch.

At either decision, the human may invoke `/svp:help` to formulate a hint about the cross-unit interaction that is semantically wrong (see Section 14.4). The hint is forwarded to the implementation agent (for assembly fixes) or the blueprint author / stakeholder dialog agent (for document fixes).

The rationale for restarting from Stage 2 rather than patching the blueprint: if the integration test reveals that the blueprint's decomposition missed something, the entire decomposition may need to change. A fresh blueprint dialog with the amended spec produces a clean structure.

**Scenarios -- Gates 4.1/4.2 (integration failure decisions).**
*Best case:* Integration tests pass on the first run. No human decision needed -- the pipeline advances directly to Stage 5 (repository delivery).
*Worst case:* Integration tests fail. The diagnostic agent identifies a cross-unit issue. The human uses the Help Agent to formulate a hint about the interface problem (e.g., "Unit 3 outputs frequencies in Hz but Unit 5 expects kHz"). The human chooses ASSEMBLY FIX. The first attempt's unit tests fail -- proving this was not an assembly fix. The issue escalates through the assembly fix ladder until exhausted. The human is presented with Gate 4.2 and chooses FIX BLUEPRINT or FIX SPEC. The spec or blueprint is revised, and the pipeline restarts from Stage 2. After the restart, integration tests fail again on a different issue, requiring another document revision. Eventually the documents are comprehensive enough that the integration tests pass. Time: potentially multiple full pipeline restarts.

---

## 12. Stage 5: Repository Delivery

### 12.1 Repository Creation

The git repo agent creates a clean git repository in `projectname-repo/` at the same level as the project workspace. It commits artifacts in the following order:

1. The Conda environment file, dependency list, and directory structure -- first commit (from pre-Stage-3 infrastructure).
2. The stakeholder spec (`stakeholder.md`) -- second commit.
3. The blueprint (`blueprint.md`) -- third commit.
4. Each unit, with its implementation and tests, committed sequentially in topological order. Each commit message references the unit's name and a brief description from the blueprint.
5. Integration tests -- committed after all unit commits.
6. Project configuration files (entry point, README).
7. Document version history (`docs/history/`) -- the full revision history of both the stakeholder spec and blueprint, including all diff summaries.
8. Reference documents and their summaries (`docs/references/`).

The commit history tells the story of the project's design and construction: environment first, then intent, then design, then implementation in dependency order.

### 12.1.1 Assembly Mapping: Workspace to Repository

During assembly, the git repo agent must relocate unit implementations from their workspace paths (`src/unit_N/`) to their correct final locations in the delivered repository. The workspace path structure (`src/unit_N/stub.py`) is an internal SVP convention for test isolation -- it is NOT the delivered file layout.

The blueprint's preamble contains an explicit file tree (Section 1.4 of this spec, and the blueprint's Architecture Overview) that maps every unit to its final file path within the repository. The git repo agent MUST use this mapping when placing files. Specifically:

1. **Read the blueprint file tree.** The blueprint's preamble lists every delivered file with a `<- Unit N` annotation. This is the authoritative mapping from unit number to destination path.
2. **Copy implementation content, not file paths.** For each unit, read the verified implementation from `src/unit_N/` in the workspace, but write it to the path specified in the blueprint file tree. For example, if the blueprint says `svp/scripts/svp_launcher.py <- Unit 24`, the content of `src/unit_24/`'s implementation file is written to `svp/scripts/svp_launcher.py` in the repository -- NOT to `src/unit_24/stub.py`.
3. **Never reference `src/unit_N/` paths in entry points or imports.** The delivered repository must use the final relocated paths. Entry points in `pyproject.toml` must reference modules at their final locations (e.g., `svp.scripts.svp_launcher:main`), never `src.unit_N.stub:main`.
4. **Never import from `src.unit_N.stub` in delivered code.** If an implementation file contains imports like `from src.unit_22.stub import ...`, these must be rewritten to use the final module paths (e.g., `from svp.scripts.templates.claude_md import ...`). Cross-unit imports via `src.unit_N` are a workspace convention that does not exist in the delivered repository.
5. **The `src/` directory in the delivered repository** contains the Python source code organized by the blueprint's file tree, NOT by unit number. The workspace's `src/unit_N/` structure is never reproduced in the delivered repository.
6. **Non-Python deliverables.** Units whose artifact category is not "Python script" (e.g., Markdown agent definitions, JSON configurations, shell scripts, template files) produce their deliverable content as Python string constants named `{FILENAME_UPPER}_CONTENT` in the unit's implementation file. Each string constant contains the complete file content. During assembly, the git repo agent extracts these strings and writes them as files to the paths specified in the blueprint file tree. For example, Unit 13's implementation contains `SETUP_AGENT_MD_CONTENT: str` whose value is the complete content of `agents/setup_agent.md`. This convention ensures all deliverables — regardless of their file type — go through SVP's standard test-stub-implement-verify cycle.

This mapping is critical for the delivered software to function. A repository that passes tests in the workspace but uses workspace-internal paths (`src.unit_N.stub`) in its entry points or imports will fail when installed by the end user.

### 12.2 Installability Guarantee

The delivered repository must be immediately installable and runnable. This is a hard output requirement. The git repo agent must:

1. Use `build-backend = "setuptools.build_meta"` in `pyproject.toml` -- never `"setuptools.backends.legacy:build"` or any other variant.
2. Set entry points to actual implementation files at their **final relocated paths** (see Section 12.1.1) -- never to `stub.py`, never to `src.unit_N` paths. For example, the SVP launcher entry point must be `svp.scripts.svp_launcher:main`, not `src.unit_24.stub:main`.
3. Scan all Python files in the delivered repository for imports referencing `src.unit_N` or `stub` modules. Any such import is an assembly error -- these are workspace-internal paths that do not exist in the installed package. All cross-module imports must use the final relocated module paths.
4. Verify the package installs successfully by running `pip install -e .` inside the repo directory using the project conda environment before considering assembly complete.
5. Verify that the CLI entry point is callable: after `pip install -e .`, run the entry point command with `--help` (or equivalent) to confirm it resolves and loads without import errors.

Failure to produce an installable package is treated as an assembly error triggering the bounded fix cycle (Section 12.3).

### 12.3 Structural Validation

Before presenting the repository test results to the human, a deterministic validation step verifies that the delivered repository conforms to the required plugin directory structure (Section 1.4). The validation checks:

- The repository root contains `.claude-plugin/marketplace.json`.
- The plugin subdirectory (`svp/`) exists and contains `.claude-plugin/plugin.json`.
- All plugin component directories (`agents/`, `commands/`, `hooks/`, `scripts/`, `skills/`) are at the plugin subdirectory root level -- not nested inside `.claude-plugin/` and not at the repository root level.
- No component directories exist at the repository root level (they must be inside the plugin subdirectory).
- No Python file in the repository contains `from src.unit_` or `import src.unit_` -- these are workspace-internal import paths that indicate incomplete assembly mapping (see Section 12.1.1).
- The `pyproject.toml` entry point does not reference `stub` or `src.unit_` -- it must reference the final relocated module path.
- The SVP launcher exists at `svp/scripts/svp_launcher.py` and is a complete, self-contained module (no imports from `src.unit_N`).

Structural validation failures are treated as assembly errors and follow the bounded fix cycle (Section 12.4). This validation is specific to SVP's own delivery -- projects built *with* SVP have their own structure defined by their blueprint and do not undergo plugin structural validation.

### 12.4 Bounded Fix Cycle

Stage 5 includes a bounded fix cycle for repository assembly errors. The git repo agent may produce a repository with structural problems (wrong import paths, incorrect directory structure, missing files).

1. The git repo agent assembles the repository.
2. Structural validation runs (Section 12.3).
3. The pipeline instructs the human with an exact test command to run in the delivered repository (e.g., `cd projectname-repo && conda run -n {env_name} pytest`). The human runs this command manually rather than the pipeline running it automatically -- this verifies that the delivered repository is self-contained and works independently of the SVP workspace. If the pipeline ran the tests itself, it might inadvertently rely on workspace paths, environment variables, or other context that would not exist for a real user.
4. The human runs the command and reports the result from explicit options: **TESTS PASSED** or **TESTS FAILED** (with output pasted).
5. If fail: a fresh git repo agent reassembles with the error output as context.
6. Up to 3 attempts. If all 3 fail, the assembly fix cycle is exhausted. The human is presented with Gate 5.2: **RETRY ASSEMBLY** (reset the counter and try again), **FIX BLUEPRINT**, or **FIX SPEC**.
7. The pipeline never restarts from earlier stages for packaging errors unless the assembly fix cycle is exhausted and the human explicitly chooses a document fix.

### 12.5 Workspace Cleanup Constraints

When `/svp:clean` deletes the workspace (`delete` or `archive` mode):
- The project conda environment must be removed via `conda env remove -n {env_name} --yes`.
- The workspace directory must be deleted with a permission-aware handler -- `__pycache__` directories and conda-installed files may have read-only permissions on macOS/Linux. The deletion must chmod affected paths and retry before reporting failure.
- The delivered repository (`projectname-repo/`) is never touched by `/svp:clean`.
- The command must be invoked as `PYTHONPATH=scripts python scripts/cmd_clean.py` so library imports resolve correctly.

### 12.6 Commit Message Conventions

Commit messages follow the Conventional Commits format. The specific style is defined in the stakeholder spec for the project being built (not in SVP's own spec -- each project may have different conventions, though a sensible default is provided if the human does not specify).

### 12.7 Output

A complete, self-contained git repository containing:

- All source code, organized by unit.
- All test suites (unit and integration).
- The stakeholder spec and blueprint as documentation.
- The full version history of both documents, with diff summaries explaining every revision.
- Reference documents and their generated summaries, as provided by the human during Stages 1 and 2.
- A Conda environment file for reproducibility.
- A README.md (see Section 12.7.1).
- A clean git history with meaningful commit messages.

This repository is the final deliverable. The pipeline is complete.

#### 12.7.1 README.md

The delivered repository includes a `README.md`. The git repo agent is responsible for producing it during Stage 5 assembly. The README operates in one of two modes depending on the project being built.

**Mode A — SVP self-build (SVP building a new version of itself):**

The README is a **carry-forward artifact**. The previous version's README.md is the baseline, and the git repo agent must only update it to reflect actual changes in the new version — not rewrite it from scratch.

*Baseline structure (12 sections, preserve in order):*

1. **Header and tagline** — Project name, one-paragraph description, post-delivery debug loop mention.
2. **What SVP Does** — Six-stage pipeline overview with numbered stage list, Gate 6 paragraph.
3. **Who It's For** — Target audience, "you need" / "you do not need" lists.
4. **Installation** — Prerequisites, per-platform plugin install/uninstall (macOS, Linux, Windows WSL2), per-platform launcher install, `svp new`, `svp` resume, `svp restore`, example project verification.
5. **Configuration** — `svp_config.json` default values, configuration reference table, model assignment, context budget.
6. **Commands** — `/svp:` namespace command table with descriptions. `/svp:bug` must document `--abandon` flag.
7. **Quick Tutorial** — Step-by-step walkthrough including Section 6 "Post-Delivery Bug Fixing (Gate 6)".
8. **Example Project** — Bundled example reference.
9. **Project Structure** — ASCII directory tree of a workspace.
10. **Troubleshooting** — Common issues and solutions (conda, PATH, imports, Python version, hooks, permissions, state recovery).
11. **History** — Version changelog (SVP 1.0, 1.1, 1.2, etc.).
12. **License** — Copyright and license reference.

*Update rules:*

- Preserve the section order and section headings exactly.
- Update version-specific content only where the new version introduces a change (e.g., new commands, changed configuration parameters, new prerequisites).
- Do not rewrite prose that has not changed in substance.
- If the new version adds a feature not covered by any existing section, add it as a subsection within the most relevant existing section — do not create new top-level sections without explicit human approval.
- The Troubleshooting and History sections must be kept up to date with each new version.

The blueprint author must include the full previous-version README.md text as a baseline reference in the git repo agent's unit (or its content constants), so the implementation agent has the exact text to carry forward and update.

**Mode B — General project (SVP building any other software):**

The README is a **generated artifact**. The git repo agent produces it from scratch, modeled on the same structural template but adapted entirely to the project's domain. The content must be derived from the stakeholder spec and blueprint — not copied from SVP's own README.

*Section template (adapt headings and content to the project):*

1. **Header and tagline** — Project name and one-paragraph description derived from the stakeholder spec.
2. **What [Project] Does** — High-level description of the project's purpose and architecture.
3. **Who It's For** — Target audience as described in the stakeholder spec.
4. **Installation** — Prerequisites, dependencies, install instructions derived from the Conda environment file and `pyproject.toml`.
5. **Configuration** — Configuration options, if the project has any. Omit if not applicable.
6. **Usage** — How to run the software: CLI commands, API entry points, or library usage examples as appropriate.
7. **Quick Tutorial** — A short walkthrough of the most common use case, if the project has a natural "happy path." Omit if not applicable.
8. **Examples** — Reference to bundled examples, if any. Omit if none.
9. **Project Structure** — ASCII directory tree of the delivered repository.
10. **License** — Copyright and license as specified in the stakeholder spec.

*Generation rules:*

- Derive all content from the stakeholder spec and blueprint. Do not invent features or capabilities not described in the spec.
- Omit sections that are not applicable (e.g., Configuration for a project with no config, Examples for a project with no bundled examples). Do not include empty sections.
- Write for the project's target audience as described in the stakeholder spec — match the technical level and domain vocabulary.
- Include concrete usage examples (command invocations, code snippets) where the spec provides enough detail to produce them accurately.
- The README should be useful to someone who receives the repository without having seen the stakeholder spec.

**Mode detection:** The blueprint author determines which mode applies based on the stakeholder spec. If the spec describes SVP itself (a Claude Code plugin for building verified Python projects), Mode A applies. Otherwise, Mode B applies. The blueprint must explicitly state which mode the git repo agent should use.

#### 12.7.2 Bundled Example Project (SVP Self-Build Only)

When SVP builds a new version of itself (Mode A), the delivered repository must include a bundled example project at `examples/game-of-life/` containing three files:

1. `stakeholder_spec.md` — A complete stakeholder spec for a Conway's Game of Life CLI simulator.
2. `blueprint.md` — A complete blueprint decomposing the Game of Life spec into testable units.
3. `gol_project_context.md` — A project context file for the Game of Life project.

These files are **carry-forward artifacts** from the previous version. They are not regenerated — they are carried forward verbatim unless a change in SVP's document format requires updating them.

**Purpose:** The example serves two roles:

1. **Installation verification** — Users run `svp restore game-of-life --spec .../stakeholder_spec.md --blueprint .../blueprint.md --context .../gol_project_context.md --scripts-source .../svp/scripts` to verify their SVP installation works end-to-end.
2. **Integration test** — During Stage 4, one of the integration tests must exercise the `svp restore` code path using these example files. The test calls the launcher's restore logic (not a subprocess — the Python functions directly) with the example files as input and verifies that a valid workspace structure is created: directory tree exists, pipeline state is initialized at `pre_stage_3`, the injected spec and blueprint are present and match the originals, CLAUDE.md is generated, and default config is written. This tests the seam between the launcher (Unit 24), templates (Unit 22), pipeline state (Unit 2), and configuration (Unit 1).

For general projects (Mode B), no bundled example is included.

### 12.8 Workspace Cleanup

Upon successful repository delivery, the pipeline congratulates the human, announces that `/svp:bug` is now available for post-delivery bug investigation (see Section 12.9), and offers the `/svp:clean` command with its three options (archive, delete, or keep the workspace). The human is not required to act immediately -- they can inspect the repo first and run `/svp:bug` or `/svp:clean` whenever they choose.

**Workspace vs. repository contents.** The following artifacts are workspace-only and are not delivered to the repository: conversation ledgers, diagnostic logs, pipeline state file, raw iteration artifacts, review critiques, and the SVP configuration file. These are build process artifacts. If the human archives the workspace, they are preserved; if the human deletes the workspace, they are gone. The insight they contain about the build process is reflected in the document version history, which is delivered.

### 12.9 Post-Delivery Debug Loop

After Stage 5 completion, the human may discover bugs while using the delivered software. The `/svp:bug` command initiates a structured debug loop that preserves SVP's verification guarantees throughout the fix process.

#### 12.9.1 Entry Point and Debug Permission Reset

A single command -- `/svp:bug` -- serves as the entry point for all post-delivery problems. The human does not need to classify their problem. They say "something is wrong" and the system determines what kind of problem it is.

**Precondition:** The project workspace is intact (not archived or deleted). The human used `/svp:clean --keep` or has not yet run `/svp:clean`. Only one debug session can be active at a time.

**Debug permission reset (Gate 6.0).** When `/svp:bug` is invoked, the pipeline transitions from the post-Stage-5 locked state (where hooks prevent all artifact writes) to an intermediate read-only triage state. The bug triage agent begins its initial Socratic dialog in read-only mode -- it can read all project files but cannot modify any artifacts. After the triage agent has gathered sufficient information from the human and presented its initial assessment, the pipeline presents Gate 6.0 with two options: **AUTHORIZE DEBUG** and **ABANDON DEBUG**. If **AUTHORIZE DEBUG**: `update_state.py` updates `pipeline_state.json` to activate all debug session write rules simultaneously (see Section 19.2). The triage agent continues with write access to `tests/regressions/` and `.svp/triage_scratch/`. If **ABANDON DEBUG**: the pipeline returns to "Stage 5 complete" with no state changes.

This explicit confirmation gate ensures that the transition from locked post-delivery state to debug write permissions is always human-authorized and never automatic.

#### 12.9.2 Triage Classification

The bug triage agent's first job is classifying the kind of problem. This is an early branch that determines the entire downstream path:

- **Build/environment issue:** Wrong library version, missing dependency, broken import path, `pyproject.toml` error, environment corruption. The code doesn't run at all, fails at import time, or produces an environment error. No logic is wrong -- the packaging is broken.
- **Logic bug:** Wrong behavior, wrong output, domain-level incorrectness. The code runs but produces results the human knows are wrong based on their domain expertise.

The triage agent makes this classification based on the error description and Socratic probing of ambiguous cases.

#### 12.9.3 Build/Environment Fix Path (Fast Path)

For build and environment issues, no regression test is needed. The repair agent fixes the issue directly, following a bounded fix cycle:

1. The triage agent identifies the build/packaging error.
2. A repair agent fixes the issue. The repair agent has a narrow mandate: it can modify environment files, package configuration (`pyproject.toml`), `__init__.py` files, and directory structure. It **cannot** modify implementation files (any `.py` file in `src/unit_N/` other than `__init__.py`). The write authorization hook enforces this scope constraint.
3. Verification: the repo installs and tests pass.
4. Up to 3 attempts. If all fail, the human gets a structured diagnosis.
5. If the "build fix" requires changes to unit source code, the repair agent returns `REPAIR_RECLASSIFY` -- the bug is reclassified and switches to the logic bug path.
6. Full Stage 5 repo reassembly after successful fix.

#### 12.9.4 Logic Bug Path (Full Path)

**Socratic triage dialog.** The bug triage agent conducts a Socratic dialog oriented toward reproducing the bug. Unlike `/svp:help` (which asks "what do you want to understand?"), the triage agent asks "what exactly happened, with what input, and what did you expect instead?" Every question aims at getting closer to a test-writable assertion -- concrete inputs, concrete expected outputs, concrete actual outputs. The triage dialog uses its own conversation ledger (`ledgers/bug_triage_N.jsonl`).

The triage agent has access to the stakeholder spec, the blueprint, all source code, all existing test suites, and the human's real data files.

**Real data access.** The human provides their actual data during the triage dialog. The triage agent uses real data to understand the bug, then produces a test with synthetic data that reproduces it. The real data is the diagnostic tool, not the test fixture. The regression test must be self-contained -- the delivered repo cannot depend on the human's data files.

The triage agent produces a structured output: affected unit(s), root cause hypothesis, regression test specification (concrete inputs, expected outputs, assertion), and classification (single-unit code fix or cross-unit contract problem).

#### 12.9.5 Regression Test and Binary Classification

A test agent writes a failing regression test based on the triage output, saved to `tests/regressions/test_bug_NNN.py`. The test is run against the current implementation and must fail (confirming the bug is reproducible). If it passes, the triage hypothesis is wrong -- the dialog returns for a revised hypothesis. The human reviews the test assertion in plain language at a human gate.

The gate response options for regression test validation are **TEST CORRECT** and **TEST WRONG**.

After the regression test is confirmed, the triage agent's classification determines the path:

- **Single-unit code fix:** The contract is correct. The implementation doesn't fulfill it for this specific case. The pipeline re-enters Stage 3 for the affected unit. The `stage` field in `pipeline_state.json` remains at 5 -- the `debug_session` object tracks the re-entry via its current debug phase status (e.g., `"phase": "stage3_reentry", "unit": N`). The implementation agent receives the bug diagnosis, the regression test, existing unit tests, and current code. Debug write authorization (activated at Gate 6.0) permits writes to both `src/unit_N/` and `tests/unit_N/` for the affected unit. After the fix: regression test plus all unit tests for the affected unit must pass.
- **Cross-unit contract problem:** The contracts between units don't capture something they should. This is a blueprint problem. Targeted blueprint revision of the affected contracts, then ruthless forward restart from the affected units. The regression test is preserved (see Section 12.9.6) and becomes part of the integration test suite.

The gate response options for debug fix classification are **FIX UNIT**, **FIX BLUEPRINT**, and **FIX SPEC**.

#### 12.9.6 Regression Test Survival

`tests/regressions/` is a protected directory that ruthless restart never touches. The test runner includes regression tests in the appropriate runs:

- Unit-level regression tests run alongside the affected unit's tests during Stage 3 green runs.
- Cross-unit regression tests run alongside integration tests during Stage 4.

This is a critical design requirement: the regression test -- which is the only proof the bug won't recur -- must survive document revisions and restarts.

#### 12.9.7 Completion and Repo Reassembly

After any successful fix (single-unit or post-restart):

1. All unit tests pass.
2. All regression tests pass.
3. Integration tests pass.
4. Full Stage 5 repo reassembly -- the old repo is discarded entirely and rebuilt.
5. The new repo includes the regression test in its test suite and commit history.
6. The debug session is recorded in pipeline state history.
7. Pipeline returns to "Stage 5 complete" state.

#### 12.9.8 Non-Reproducible Bugs

If the triage agent cannot produce a failing test after the iteration limit (consistent with `iteration_limit` in `svp_config.json`):

1. **Triage was wrong.** The hypothesis about the affected unit is incorrect -- the dialog continues with a revised hypothesis. The gate response options are **RETRY TRIAGE** and **ABANDON DEBUG**.
2. **Environmental/data mismatch.** The bug occurs with real data but synthetic data can't trigger it -- the agent asks for more specific data characteristics.
3. **Genuinely non-reproducible.** The agent produces a structured report of what it tried and what it ruled out. The human gets a useful diagnosis even without an automated fix.

#### 12.9.9 Repair Agent Exhaustion

If the repair agent exhausts its fix cycle (3 failed attempts for build/environment fixes, or implementation fix failure for logic bugs), the human is presented with Gate 6.3 with options: **RETRY REPAIR** (reset the counter and try again), **RECLASSIFY BUG** (return to triage for a different classification), or **ABANDON DEBUG** (return to Stage 5 complete without applying any fix).

#### 12.9.10 Debug Session Abandonment

The human can abandon an active debug session at any time via `/svp:bug --abandon`. This cleans up the debug session state and returns the pipeline to "Stage 5 complete" without applying any fix. The triage conversation ledger is renamed to `bug_triage_N_abandoned.jsonl` and preserved for reference in future debug sessions.

## 13. Human Commands

The following commands are available to the human at any point during any stage of the pipeline. All SVP commands use the plugin namespace `svp:` -- the Claude Code plugin system automatically namespaces plugin commands as `plugin-name:command-name`, so a command file `save.md` in the `svp` plugin produces `/svp:save`. This namespacing avoids collisions with Claude Code's built-in slash commands (such as `/help`, `/compact`, `/clear`, `/context`). Claude Code's built-in commands remain available alongside SVP commands.

Each command is implemented as a markdown file in the plugin's `commands/` directory. When the human types the command, Claude Code injects the markdown content into the conversation. The markdown content is written as an explicit, unambiguous directive that instructs the main session to execute a specific deterministic script and present its output. The directive is phrased to minimize the probability of the main session deviating from the intended action -- it names the exact script, the exact arguments, and the exact presentation format.

Commands are available at gates and between units, not during autonomous execution sequences (see Section 20).

### 13.1 Command Group Classification

Commands are divided into two groups based on their execution mechanism. Confusing these groups -- routing a Group B command through a Group A script or vice versa -- was the most costly bug in SVP 1.1 and must not recur.

**Group A -- Utility commands.** These invoke a dedicated `cmd_*.py` script directly. No subagent is spawned. The script executes a deterministic action and returns output for the main session to present.

- `/svp:save` -- invokes `cmd_save.py`
- `/svp:quit` -- invokes `cmd_quit.py`
- `/svp:status` -- invokes `cmd_status.py`
- `/svp:clean` -- invokes `cmd_clean.py`

**Group B -- Agent-driven workflow commands.** These invoke `prepare_task.py` to assemble a task prompt, then the main session spawns a subagent with that task prompt. The subagent conducts its workflow and returns a terminal status line.

- `/svp:help` -- prepares task prompt, spawns help agent
- `/svp:hint` -- prepares task prompt, spawns hint agent
- `/svp:ref` -- prepares task prompt, spawns reference indexing agent
- `/svp:redo` -- prepares task prompt, spawns redo agent
- `/svp:bug` -- prepares task prompt, spawns bug triage agent

**Prohibited scripts.** The following scripts must never exist: `cmd_help.py`, `cmd_hint.py`, `cmd_ref.py`, `cmd_redo.py`, `cmd_bug.py`. Group B commands are not utility commands and must not be implemented as dedicated scripts. If any of these files are created during development, the blueprint checker or test suite must flag them as violations.

**`/svp:save`**

Flush any pending state to disk and confirm to the human that the save is complete. In practice, the system auto-saves after every significant transition (stage completion, unit verification, document approval, ledger turn). The `/svp:save` command is primarily a confirmation mechanism -- it verifies file integrity and tells the human "you are safe to close the terminal." The human can never lose more than the current in-progress subagent call.

**`/svp:quit`**

Exit the pipeline. Runs the save script first, then exits. An explicit save confirmation is presented before exit.

**`/svp:help`**

Pause the pipeline and launch the SVP help agent. The help agent is stateless, causes no pipeline side effects, and has selective read access to all project documents (it receives a project summary and retrieves specific files on demand rather than loading everything). It also has web search access for questions beyond the project itself.

The help agent can answer questions such as:

- "What does this function do?"
- "What is pytest and why are we using it?"
- "What is the MNE library and does it handle EEG data?"
- "Explain this error message in plain English."
- "How do I save the project?"
- "Why did the pipeline restart?"

The help agent uses a conversation ledger for multi-turn interaction. When the human is done, the pipeline resumes exactly where it was. No state change. The ledger is cleared on dismissal. Help agent output to the main session is constrained to a terminal status line only -- either `HELP_SESSION_COMPLETE: no hint` or `HELP_SESSION_COMPLETE: hint forwarded` followed by the hint content. The full help session conversation lives in the help session ledger and does not enter the main session's context.

When `/svp:help` is invoked at a decision gate (rather than during normal pipeline flow), the help agent operates in **gate-invocation mode**: it receives an additional context flag indicating the current gate. In this mode, the help agent's system prompt includes an instruction to proactively offer hint formulation and guide the human through the approval-and-forward flow when the conversation naturally produces an actionable observation. During regular (non-gate) help sessions, this forwarding instruction is omitted. See Section 14.4 for the complete hint forwarding mechanism.

Note: Claude Code's built-in `/help` command remains available and shows all slash commands, including SVP's. `/svp:help` is specifically for launching SVP's domain-aware help agent.

**`/svp:hint`**

Request a diagnostic analysis of the current state of the project. Operates in two modes depending on context:

**Reactive mode** (invoked during a failure condition -- e.g., blueprint alignment loop not converging, repeated unit test failures). The system already knows what's wrong. The hint agent reads accumulated rejection reasons and failure logs and identifies patterns. No additional input from the human is needed. After presenting its analysis, the hint agent asks from explicit options: "CONTINUE -- resume where we left off" or "RESTART -- revise a document and restart."

**Proactive mode** (invoked during normal pipeline flow, when no failure condition is active). The system does not know anything is wrong -- the human is acting on intuition, a concern they noticed, or a requirement they forgot. The hint agent follows this sequence:

1. Asks: "What is prompting this concern?" -- letting the human articulate their unease in their own words.
2. Asks: "Which document do you suspect is at fault -- the stakeholder spec, the blueprint, or are you unsure?" If unsure, the agent examines both documents against the human's stated concern.
3. Produces a targeted diagnostic analysis.
4. Presents explicit options: "CONTINUE -- resume where we left off" or "RESTART -- revise the document and restart."

If the human chooses to continue, the pipeline resumes with no state change. If the human chooses to restart, the pipeline enters the appropriate document revision flow (Socratic dialog to fix the identified document, then restart from the corresponding stage). Before restarting, the human may invoke `/svp:help` to formulate a hint (see Section 14.4) that is forwarded to the revision agent alongside the hint agent's diagnostic analysis.

The `/svp:hint` command never modifies documents or advances the pipeline on its own. It provides information and offers a decision. The human acts.

**`/svp:status`**

Report the current pipeline state in human-readable form: current stage, current sub-stage, which units are verified, how many alignment iterations have been used, and what the next expected action is. Additionally, `/svp:status` includes a brief pipeline history showing pass numbers, how far each pass reached, why it ended, and current progress:

```
Project: Spike Sorting Pipeline
Current: Stage 3, Unit 2 of 11 (pass 2)
Pass 1: Reached Unit 7, spec revision triggered
        (electrode boundary handling was underspecified)
Pass 2: In progress, Unit 1 verified
```

This history provides context for the non-linear progress experience -- reaching unit 7 and then restarting from unit 1 is expected behavior, not a regression. The state file tracks pass history.

Informational only. Replaces the former `/svp:tokens` command -- direct token usage and rate limit information is not reliably accessible from within a Claude Code session, so the status command focuses on pipeline progress, which is always available from the state file.

**`/svp:ref`**

Add a reference to the project. Available during Stages 0, 1, and 2 only. Locked from Stage 3 onward. The human provides a file path (using Claude Code's `@` syntax, e.g., `@~/Downloads/methods.pdf`), a URL, or a GitHub repository URL. The system handles two reference types:

**Document references** (files and non-GitHub URLs). The document is copied to the `references/` directory, indexed by the reference indexing agent (which produces a structured summary saved to `references/index/`), and a brief confirmation is presented.

**Repository references** (GitHub URLs matching the pattern `github.com/owner/repo`). The system checks whether the GitHub MCP server is configured. If it is, the reference indexing agent explores the repository via GitHub MCP tools: reads the README, maps the directory structure, identifies key modules, and produces a structured summary to `references/index/`. The repository URL is recorded in `references/repos.json` so that dialog agents can read specific files on demand when the human directs them to (see below). If GitHub MCP is not configured, the system informs the human that repository references require GitHub MCP, offers to configure it now (which triggers a session boundary to apply the new MCP configuration, after which the pipeline resumes and the `/svp:ref` command is re-executed automatically), or allows the human to skip and continue without the repo reference.

**On-demand file access for repository references.** When GitHub MCP is configured and at least one repository has been added via `/svp:ref`, the stakeholder dialog agent and blueprint author agent gain GitHub MCP read access in their tool whitelist. This allows the human to direct these agents to read specific files from referenced repositories during the conversation -- for example, "look at `src/cluster.py` in the spike-sorting repo." The agent reads the file via GitHub MCP and uses it as context for the ongoing dialog. Agents never browse the repository autonomously; file reads occur only when the human requests them. This on-demand access follows the existing three-layer context protocol (Section 3.7): the reference summary enters via the task prompt, specific files are retrieved on demand during execution.

In both cases, a brief confirmation is presented and the pipeline resumes with the new reference available as context.

If the human attempts `/svp:ref` during Stage 3 or later, the system informs them that references cannot be added during construction and suggests `/svp:redo` or `/svp:hint` if the reference reveals a spec issue that needs addressing.

**`/svp:redo`**

Roll back the pipeline to redo a previously completed step. This command exists because the target user -- a domain expert learning about their own requirements through the building process -- will sometimes realize, after approving a test assertion or finalizing a decision, that they were wrong. This is not a failure mode; it is the expected behavior of someone iterating on their understanding. The `/svp:redo` command handles it as a first-class scenario.

When invoked, the redo agent receives a lean task prompt (pipeline state summary, the human's error description, current unit definition) and uses read tools to search documents on demand. The redo agent's classification is document-driven:

1. The human describes the mistake in their own words -- for example, "I said waveforms under 0.3ms should be rejected, but it should be 0.5ms" or "I approved a test that checks for Euclidean distance but I actually need cosine similarity."

2. The redo agent traces the relevant term or decision through the document hierarchy (stakeholder spec -> blueprint -> tests/implementation), identifies where the discrepancy originates, and presents its finding to the human for confirmation. The redo agent does not ask the human to self-classify their error -- the human does not know the document hierarchy well enough for reliable self-diagnosis.

The redo agent produces dual-format output (prose explanation for the human, structured block for routing) and one of three terminal status lines:

   - **`REDO_CLASSIFIED: spec`** -- the stakeholder spec says the wrong thing. The human is correcting their own requirements. Remedy: targeted spec revision (Section 7.6) on the identified issue, then restart from Stage 2. If the problem is pervasive, the human may choose a full spec restart.
   - **`REDO_CLASSIFIED: blueprint`** -- the stakeholder spec is correct, but the blueprint translated it incorrectly (or the human notices the blueprint made a decomposition choice they disagree with now that they see its consequences). Remedy: restart from Stage 2 (fresh blueprint dialog and generation).
   - **`REDO_CLASSIFIED: gate`** -- the documents are correct, but the human approved something wrong during Stage 3 execution -- confirmed an incorrect test assertion, approved a stakeholder spec draft without catching an issue, or otherwise made a judgment call they now regret. Remedy: unit-level rollback (see below).

**Unit-level rollback (gate error).** When the human made an incorrect approval during unit verification, the pipeline rolls back to the start of the affected unit and invalidates all units from that point forward. Every unit from the affected unit onward is marked as unverified in the pipeline state, and their generated code and tests are moved to a `logs/rollback/` directory (preserved for diagnostic reference, not deleted). The pipeline then resumes at the affected unit, reprocessing it and all subsequent units from scratch.

The rationale for invalidating all units from the affected unit forward -- rather than only the affected unit -- is consistency with ruthless restart at the unit level. The pipeline cannot know whether the human's error propagated through their other approval decisions at subsequent gates. The human who approved the wrong threshold at unit 5 may have also approved related assertions at units 6, 7, and 8 that were influenced by the same misunderstanding. Invalidating forward eliminates this risk without requiring blast radius analysis.

After classification, the human may invoke `/svp:help` to formulate a precise hint about the error (see Section 14.4); the hint is forwarded to the agent that performs the fix (determined by the redo classification). The redo agent's own classification output is not automatically treated as a hint -- hint forwarding requires a separate Help Agent invocation.

The `/svp:redo` command is available during Stages 2, 3, and 4. It is not available during Stage 1 (nothing to redo yet), Stage 0 (setup), or Stage 5 (delivery is complete -- the human should start a new project or use a future incremental modification feature).


**`/svp:bug`**

Report a post-delivery bug or abandon an active debug session. Available only when Stage 5 is complete. Initiates the post-delivery debug loop described in Section 12.9.

When invoked without flags, the bug triage agent is launched to conduct a Socratic dialog with the human. The agent classifies the bug (build/environment issue or logic bug), reproduces it, and produces a structured triage output that determines the downstream fix path. The triage dialog uses its own conversation ledger (`ledgers/bug_triage_N.jsonl`).

When invoked with `--abandon`, the current debug session is abandoned: the debug session state is cleaned up, the triage conversation ledger is renamed to `bug_triage_N_abandoned.jsonl` for reference, and the pipeline returns to "Stage 5 complete." Only one debug session can be active at a time.

**Precondition:** The project workspace is intact (not archived or deleted via `/svp:clean`). The pipeline must be in the "complete" state (Stage 5 finished) with no active debug session (for bug report) or with an active debug session (for abandon).

**`/svp:clean`**

Available after Stage 5 (repository delivery) is complete, or offered automatically by the pipeline upon successful completion. Manages the workspace directory after the final repository has been delivered. Three options:

- **Archive:** compress the workspace into a single `.tar.gz` file alongside the repo, then delete the workspace directory. The human keeps the full history without the clutter.
- **Delete:** remove the workspace entirely. The repo is the only artifact that survives.
- **Keep:** leave everything as-is. The human can inspect the workspace later.

This command is only functional after a successful Stage 5 delivery. Invoking it before delivery has no effect.

---

## 14. The Help Agent

The help agent deserves dedicated specification because it exists outside the pipeline's state machine.

### 14.1 Availability

Available at any point during any stage. The human invokes it with `/svp:help` or by asking a question that the orchestration logic recognizes as a help request (e.g., "what does this mean?").

### 14.2 Behavior

- Stateless across sessions: no memory between invocations, but maintains a conversation ledger within a single help session for multi-turn follow-up questions.
- Read-only: never modifies documents, code, tests, or pipeline state. The agent definition restricts its tool access to read-only tools (Read, Grep, Glob, and web search). This restriction is reinforced by the universal write authorization hooks (Section 19), which block all artifact writes during help sessions regardless of what the agent attempts.
- Selective context: receives a project summary (current stage, verified units, what's happening) plus the stakeholder spec and blueprint as task prompt. Retrieves specific files on demand using read tools rather than loading all project artifacts upfront.
- The pipeline pauses while the help agent is active.
- The pipeline resumes with no state change when the help agent is dismissed.
- Has web search access for questions beyond the project itself.
- Uses an economical model by default (`claude-sonnet-4-6`) to manage API costs, since help queries are frequent and typically do not require the most capable model.
- Output to the main session is constrained to a terminal status line only: `HELP_SESSION_COMPLETE: no hint` or `HELP_SESSION_COMPLETE: hint forwarded` followed by the hint content. The full help session conversation lives in the help session ledger (cleared on dismissal). The main session's context receives only the status line.

### 14.3 Scope

The help agent answers any question the human has. It is not limited to the project. Examples:

- Explaining code, error messages, or technical concepts.
- Explaining SVP's own behavior ("why did the pipeline restart?").
- Researching external libraries, tools, or methods.
- Clarifying Python syntax, data structures, or patterns.
- Answering domain-adjacent questions ("what statistical test is appropriate for this comparison?").

### 14.4 Gate-Invocation Mode and Hint Forwarding

When the help agent is invoked at a decision gate (indicated by a gate-invocation flag in its context), it gains an additional capability: collaborating with the human to formulate and forward engineering suggestions to the next agent in the pipeline. The human brings domain expertise and intuition about what should be happening; the help agent brings the ability to read code, trace logic, and identify the specific technical issue. Together, they produce suggestions that are both domain-informed and engineering-precise -- the human knows the correct formula, the help agent finds the line where the wrong formula is used. The resulting hint is forwarded to the next agent's task prompt.

**Formulation workflow.** In gate-invocation mode, the help agent's system prompt includes an instruction to proactively offer hint formulation when the conversation naturally produces an actionable observation:

1. The human discusses the problem with the help agent, which has read access to code, tests, blueprint, and diagnostic output.
2. When the conversation produces an actionable observation, the help agent offers to formulate it as a hint and presents the final text for the human's explicit approval.
3. The human approves (or edits and approves).
4. The help agent's final output is the approved hint text, tagged with the terminal status line `HELP_SESSION_COMPLETE: hint forwarded` followed by the hint content.
5. The main session receives this as the terminal output and stores it for forwarding.

During regular (non-gate) help sessions, the proactive hint formulation instruction is omitted from the system prompt.

**Forwarding mechanism.** The main session detects the hint content following the terminal status line and stores the raw hint content. Before injecting the hint into the next agent's task prompt, the main session runs a deterministic hint prompt assembler script that wraps the hint in a context-dependent prompt block. The wrapper is not a verbatim pass-through -- it is a structured prompt block assembled by the script that adapts to:

- **Agent type:** whether the receiving agent is a test agent or an implementation agent. A test agent wrapper frames the hint in terms of what behavior should be tested and why the prior tests were wrong. An implementation agent wrapper frames the hint in terms of what the code should do differently and why prior implementations failed.
- **Ladder position:** where in the fix ladder the invocation sits. The wrapper adjusts the framing accordingly.

The wrapper is produced by the hint prompt assembler script that takes the raw hint content, the gate metadata, the agent type, and the ladder position as inputs, and outputs the complete `## Human Domain Hint (via Help Agent)` section for inclusion in the task prompt. This script applies prompt engineering principles: clear framing, explicit instructions on how the agent should use the hint, and the constraint that the hint is a signal to evaluate rather than a command to execute blindly. No LLM involvement -- the wrapping uses deterministic templates with variable substitution.

The main session also logs the hint as a `[HINT]` entry in the relevant ledger or session log, with full gate metadata (gate identifier, unit number, stage, and decision made). After forwarding, the stored hint is cleared -- it is injected into one invocation only. However, the `[HINT]` ledger entry persists and is visible to subsequent agents that read the log.

**Hint prompt template.** The hint prompt uses a uniform template filled with gate-specific details. The template includes the current gate context (which decision, which unit, what failed) so the help agent can provide relevant assistance without requiring gate-specific prompt engineering.

**Receiving agent behavior.** The receiving agent evaluates the hint alongside the blueprint contract, diagnostic analysis, and its own judgment. The hint is a signal, not a command. If the hint contradicts the blueprint contract, the agent returns a structured terminal status line: `HINT_BLUEPRINT_CONFLICT: [details]`. The routing script presents a binary gate: blueprint correct (discard hint, proceed) or hint correct (document revision, restart). For Stage 2 gates involving decomposition structure, the Blueprint Author Agent is instructed to weigh decomposition-level hints from the human more heavily, since the human is a domain expert on how their problem should be structured.

**No explicit length limit.** The hint has no fixed token limit. The help agent exercises judgment to keep hints concise and relevant, and the overall context budget provides a natural ceiling.

**Constraints.** The help agent remains read-only -- it never modifies files, code, tests, or pipeline state. The hint content is a form of output, not file modification. The main session handles forwarding mechanically as part of its task context preparation (consistent with Section 3.6). The routing script is not affected -- hints are injected during task context preparation, between the routing script's output and the actual subagent invocation. Hint forwarding is always optional -- the human can make the categorical decision without providing a hint, and the pipeline proceeds exactly as it does without the mechanism.

---

## 15. Interaction Patterns

SVP uses three distinct interaction patterns for agent-human communication, chosen based on the nature of the interaction.

### 15.1 Ledger-Based Multi-Turn

Used for open-ended conversations where the exchange builds cumulatively: Socratic dialog (Stage 1), blueprint dialog (Stage 2), help sessions, and proactive hint sessions.

A conversation ledger is an append-only structured file (JSONL format) that records each exchange with role, content, and timestamp. Each agent turn is a fresh subagent invocation that receives the full ledger as part of its task prompt. The ledger is auto-saved after every turn, surviving session interruptions and terminal closures.

**Ledger size management.** Each ledger has a maximum size determined by the context budget available to its associated agent role (total context window minus system prompt overhead minus a safety margin). When a ledger reaches 80% of this limit, the system warns the human that the conversation is approaching its capacity. At 90%, the system requires either finalization of the current phase or ledger compaction before continuing. Compaction is performed by a deterministic script as described in Section 3.3.

**Agent response structure.** All agents using ledger-based multi-turn interaction must follow a structured response format designed to maximize compaction effectiveness:

Every agent response consists of two parts: a body (the substantive content -- explanation, analysis, elaboration, preamble) and a tagged closing line. The tagged closing line is the final line of the response and must begin with exactly one of the following markers:

- `[QUESTION]` -- the agent is asking the human something and expects an answer.
- `[DECISION]` -- the agent is recording a consensus reached with the human.
- `[CONFIRMED]` -- the agent is recording a domain fact stated by the human.

Tagged lines must be self-contained: they carry their own rationale and context, not just a bare conclusion. For example, `[DECISION] Spike detection will use a threshold of 4.5 standard deviations above the noise floor, applied independently per electrode, because the human confirmed that cross-electrode correlation is not relevant for their experimental setup` -- not merely `[DECISION] Use 4.5 SD threshold`.

The body of the response carries no markers -- it is free-form content that provides context for the tagged closing line. This structure means the compaction script can identify the body content associated with each tagged line and condense it when appropriate, because every body belongs to exactly one tagged closing.

If an agent's response does not naturally fall into any of the three categories -- for example, the agent is providing a lengthy explanation before asking a question, or is summarizing the conversation so far -- the response must still end with a tagged line. In most cases this will be a `[QUESTION]` asking the human to confirm the agent's understanding or to proceed.

This format is a structural requirement in every ledger-based agent's system prompt. It is not optional and not subject to the agent's judgment. The agent chooses which marker to use; it does not choose whether to use one.

**System-level ledger entries.** In addition to agent response markers, the orchestration layer writes system-level entries to ledgers. The `[HINT]` marker records a human domain hint forwarded at a decision gate (see Section 14.4). `[HINT]` entries include full gate metadata (gate identifier, unit number, stage, and decision made) and are preserved verbatim during compaction -- they are anchors, never condensed. `[HINT]` entries are written by the main session, not by agents.

Ledger locations:

- Setup dialog: `ledgers/setup_dialog.jsonl`
- Socratic dialog: `ledgers/stakeholder_dialog.jsonl`
- Blueprint dialog: `ledgers/blueprint_dialog.jsonl`
- Spec revision: `ledgers/spec_revision_N.jsonl` (N is the revision number)
- Help sessions: `ledgers/help_session.jsonl` (cleared on dismissal)
- Hint sessions: `ledgers/hint_session.jsonl` (cleared on dismissal)

### 15.2 Single-Shot

Used for task agents that produce a defined output and are dismissed: test generation, implementation, coverage review, diagnostic analysis, blueprint checking, stakeholder spec reviewing, blueprint reviewing, integration test authoring, reference indexing, redo classification, and git repo creation.

The agent receives its context (role prompt via system prompt, relevant documents via task prompt), produces its output with a terminal status line (see Section 18), and terminates. No conversation, no ledger, no follow-up.

### 15.3 Hint Injection at Decision Gates

A third interaction pattern, optional at every decision gate in the pipeline. The human invokes `/svp:help` at a gate, discusses the problem with the help agent (ledger-based multi-turn within the help session), and the help agent formulates a hint with the human's explicit approval. The main session detects the terminal status line, stores the hint content, and includes it in the next agent's task prompt as labeled context via the deterministic hint prompt assembler. The hint is logged as a `[HINT]` entry in the relevant ledger. This pattern is neither purely ledger-based (the hint crosses agent boundaries via the main session) nor purely single-shot (it involves a multi-turn help session that produces a forwarded artifact). It is always optional -- the human can skip it at any gate and make the categorical decision alone.

---

## 16. Session Lifecycle Management

The SVP launcher manages automatic session cycling to prevent context degradation within the main session. This section describes the complete session lifecycle.

### 16.1 Session Boundaries

Session boundaries fire at every major pipeline transition:

- Unit N verified -> starting unit N+1.
- Construction -> document revision.
- Document revision complete -> stage restart.
- Stage 2 complete -> Pre-Stage-3 start.
- Pre-Stage-3 complete -> Stage 3 start.
- Stage 3 complete -> Stage 4 start.
- Stage 4 complete -> Stage 5 start.
- Stage 5 assembly -> human testing phase.

The routing script signals these through the `session_boundary` action type.

### 16.2 Restart Mechanism

When the routing script outputs a `session_boundary` action:

1. The main session writes a restart signal file (`.svp/restart_signal`) containing the reason for the boundary (e.g., "Unit 4 verified, preparing for Unit 5").
2. The main session presents a brief transition message to the human.
3. The main session exits.
4. The SVP launcher detects the restart signal file, deletes it, sets filesystem permissions (see Section 19), and relaunches Claude Code.
5. The new session reads CLAUDE.md, runs the routing script, and picks up from the state file.

### 16.3 Post-Restart Context Summary

Every post-restart session begins with a mandatory context summary drawn from the state file. The routing script's first output in a new session includes a MESSAGE field with:

- Project name.
- Current stage and sub-stage.
- What just happened (e.g., "Unit 4: Spike Detection was verified").
- What happens next (e.g., "Starting test generation for Unit 5: Feature Extraction").
- Pass history summary if applicable (e.g., "This is pass 2. Pass 1 reached Unit 7 before a spec revision was needed.").

The human sees this summary and the pipeline continues. No confirmation is needed for automatic session cycling -- the pipeline proceeds directly.

### 16.4 Filesystem Permission Management

Between sessions (including during automatic restart cycling), the SVP launcher manages filesystem permissions:

- **On session end:** The launcher sets the entire workspace directory tree to read-only (`chmod -R a-w`) after the session exits.
- **On session start:** The launcher restores write permissions before launching Claude Code.

This ensures that between sessions, no process can accidentally modify workspace files. The permission management is the first layer of the universal write authorization system (see Section 19).

---

## 17. Routing Script Output Format

The routing script is a deterministic script that reads `pipeline_state.json` and outputs the exact next action as a structured key-value block. The main session executes this output rather than reasoning about pipeline flow independently. This section defines the complete output format.

### 17.1 Action Types

Five action types are defined:

**Invoke a subagent:**
```
ACTION: invoke_agent
AGENT: test_agent
PREPARE: python scripts/prepare_task.py --unit 4 --agent test --project-root . --output .svp/task_prompt.md
TASK_PROMPT_FILE: .svp/task_prompt.md
POST: python scripts/update_state.py --unit 4 --phase test_generation --status-file .svp/last_status.txt
MESSAGE: Starting test generation for Unit 4: Spike Detection
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

**Run a bash command:**
```
ACTION: run_command
COMMAND: cd projectname && conda run -n {env_name} pytest tests/unit_4/ -v
POST: python scripts/update_state.py --unit 4 --phase red_run --status-file .svp/last_status.txt
MESSAGE: Running red validation for Unit 4: Spike Detection
REMINDER:
[same text as above]
```

**Present a decision gate:**
```
ACTION: human_gate
GATE: gate_3_1_test_validation
UNIT: 4
PREPARE: python scripts/prepare_task.py --unit 4 --gate gate_3_1_test_validation --project-root . --output .svp/gate_prompt.md
PROMPT_FILE: .svp/gate_prompt.md
OPTIONS: TEST CORRECT, TEST WRONG
MESSAGE: A test failed. Please review the diagnostic analysis.
REMINDER:
[same text as above]
```

**Session boundary:**
```
ACTION: session_boundary
MESSAGE: Unit 4 verified. Preparing for next unit.
```

**Pipeline complete:**
```
ACTION: pipeline_complete
MESSAGE: All integration tests passed. Proceeding to repository delivery.
```

### 17.2 Field Definitions

- **ACTION** (required): one of `invoke_agent`, `run_command`, `human_gate`, `session_boundary`, `pipeline_complete`.
- **AGENT** (invoke_agent only): the agent identifier to invoke.
- **PREPARE** (optional): a command to run before the action. Typically a preparation script that produces a task prompt file or a gate prompt file. The main session runs this command first, then uses its output. Used with both `invoke_agent` (to produce task prompts) and `human_gate` (to produce gate prompts).
- **TASK_PROMPT_FILE** (invoke_agent only): path to the file containing the prepared task prompt. The main session passes the contents of this file as the task prompt verbatim.
- **COMMAND** (run_command only): the exact bash command to execute.
- **POST** (optional): a command to run after the action completes. Typically a state update script. The POST command includes the path to the status file so it can read the agent's terminal status line.
- **GATE** (human_gate only): the gate identifier.
- **UNIT** (human_gate, optional): the unit number if applicable.
- **PROMPT_FILE** (human_gate only): path to the file containing the gate prompt to present to the human, including explicit response options.
- **OPTIONS** (human_gate only): comma-separated list of valid response options.
- **MESSAGE** (required): a human-readable message to display. For session boundaries and pipeline completion, this is the only content.
- **REMINDER** (required for invoke_agent, run_command, human_gate): the standard behavioral reinforcement block. The `session_boundary` and `pipeline_complete` action types do not carry a REMINDER field -- `session_boundary` terminates the current session (no further action cycle will occur in this context), and `pipeline_complete` marks the end of the pipeline (no further actions at all). Behavioral reinforcement is unnecessary when no behavior follows.

### 17.3 Design Rationale

The tight key-value structure minimizes the hallucination surface. The main session does not parse natural language to determine what to do -- it reads structured fields. The PREPARE command produces the task prompt or gate prompt as a file, so the main session passes a file path rather than constructing content. The POST command is predetermined by the routing script, so the main session does not decide which state update to call. Every field that could be a source of LLM judgment has been moved to the routing script or to a deterministic preparation script.

---

## 18. Agent Output Interface

### 18.1 Terminal Status Lines

Every subagent produces a structured terminal status line as its final output. The main session captures this line and writes it to `.svp/last_status.txt`. The POST script reads this file and dispatches accordingly. The complete vocabulary:

**Setup Agent:**
- `PROJECT_CONTEXT_COMPLETE` -- `project_context.md` approved by the human.
- `PROJECT_CONTEXT_REJECTED` -- human not providing sufficient content; pipeline pauses.

**Stakeholder Dialog Agent:**
- `SPEC_DRAFT_COMPLETE` -- draft ready for human review.
- `SPEC_REVISION_COMPLETE` -- targeted revision complete.

**Stakeholder Spec Reviewer Agent:**
- `REVIEW_COMPLETE` -- critique produced.

**Blueprint Author Agent:**
- `BLUEPRINT_DRAFT_COMPLETE` -- blueprint produced, ready for checking.

**Blueprint Checker Agent:**
- `ALIGNMENT_CONFIRMED` -- blueprint aligns with spec.
- `ALIGNMENT_FAILED: spec` -- spec is the problem.
- `ALIGNMENT_FAILED: blueprint` -- blueprint is the problem.

**Blueprint Reviewer Agent:**
- `REVIEW_COMPLETE` -- critique produced.

**Test Agent:**
- `TEST_GENERATION_COMPLETE` -- tests produced successfully.

**Implementation Agent:**
- `IMPLEMENTATION_COMPLETE` -- implementation produced successfully.

**Coverage Review Agent:**
- `COVERAGE_COMPLETE: no gaps` -- no missing coverage found.
- `COVERAGE_COMPLETE: tests added` -- new tests were added, need red-green validation.

**Diagnostic Agent:**
- `DIAGNOSIS_COMPLETE: implementation` -- recommends implementation-level fix.
- `DIAGNOSIS_COMPLETE: blueprint` -- recommends blueprint-level fix.
- `DIAGNOSIS_COMPLETE: spec` -- recommends spec-level fix.

**Integration Test Author:**
- `INTEGRATION_TESTS_COMPLETE` -- integration tests produced.

**Git Repo Agent:**
- `REPO_ASSEMBLY_COMPLETE` -- repository assembled.

**Help Agent:**
- `HELP_SESSION_COMPLETE: no hint` -- session ended, no hint forwarded.
- `HELP_SESSION_COMPLETE: hint forwarded` -- session ended, hint content follows.

**Hint Agent:**
- `HINT_ANALYSIS_COMPLETE` -- diagnostic analysis produced.

**Redo Agent:**
- `REDO_CLASSIFIED: spec` -- error traced to spec.
- `REDO_CLASSIFIED: blueprint` -- error traced to blueprint.
- `REDO_CLASSIFIED: gate` -- error traced to human gate decision.

**Bug Triage Agent:**
- `TRIAGE_COMPLETE: build_env` -- classified as a build/environment issue. The repair agent handles this.
- `TRIAGE_COMPLETE: single_unit` -- classified as a single-unit code problem. The pipeline re-enters Stage 3 for the affected unit.
- `TRIAGE_COMPLETE: cross_unit` -- classified as a cross-unit contract problem. Triggers targeted blueprint revision.
- `TRIAGE_NEEDS_REFINEMENT` -- the regression test passed (bug not reproduced). Returning to dialog for revised hypothesis.
- `TRIAGE_NON_REPRODUCIBLE` -- iteration limit reached. Structured report produced.

**Repair Agent:**
- `REPAIR_COMPLETE` -- the build/environment fix has been applied successfully. The repo installs and tests pass.
- `REPAIR_FAILED` -- the fix attempt failed. Includes a structured summary of what was tried.
- `REPAIR_RECLASSIFY` -- the fix requires implementation changes outside the repair agent's scope. The bug should be reclassified to the logic bug path.

**Reference Indexing Agent:**
- `INDEXING_COMPLETE` -- summary produced.

**Cross-agent (any agent receiving a hint):**
- `HINT_BLUEPRINT_CONFLICT: [details]` -- the hint contradicts the blueprint; needs human decision.

### 18.2 Dual-Format Output

Agents whose output determines routing -- the diagnostic agent, the blueprint checker, and the redo agent -- produce dual-format output: a prose explanation for the human followed by a structured summary block in defined key-value format for the routing layer. The prose section is labeled `[PROSE]` and the structured section is labeled `[STRUCTURED]`.

The dual-format pattern ensures the human receives a readable explanation while the routing layer receives parseable data, without requiring the main session to extract meaning from natural language.

### 18.3 Command Result Status Lines

When the main session executes a `run_command` action, it writes a status line to `.svp/last_status.txt` constructed from the command's exit code and output. The POST script reads this file and dispatches accordingly. The complete vocabulary:

**Test execution (red runs, green runs, integration tests):**
- `TESTS_PASSED: N passed` -- all tests passed (exit code 0). N is the count of passing tests.
- `TESTS_FAILED: N passed, M failed` -- some tests failed (nonzero exit code). N and M are parsed from pytest output.
- `TESTS_ERROR: [error summary]` -- execution error preventing test collection or execution, not a test failure (import errors, environment issues, fixture problems). The error summary is the first line of the error output.

**Non-test commands (Conda setup, import validation, stub generation):**
- `COMMAND_SUCCEEDED` -- exit code 0.
- `COMMAND_FAILED: [exit code]` -- nonzero exit code.

The REMINDER block instructs the main session to write these status lines after every `run_command` execution, following the same pattern as agent terminal status lines.

### 18.4 Gate Status Strings

Every human gate response is written to `.svp/last_status.txt` as the exact string the human typed. There is no translation, prefix, or reformatting -- the human-facing option text is the status string. The `update_state.py` POST script reads this file and dispatches based on exact string matching against the canonical vocabulary defined below.

This design eliminates the translation step that was the source of the gate status mismatch bug in SVP 1.1, where the orchestration layer wrote "GATE_APPROVED" while `update_state.py` checked `s.startswith("APPROVE")`, producing a routing loop.

The complete gate status string vocabulary:

| Gate | ID | Context | Valid Status Strings |
|---|---|---|---|
| 0.1 | gate_0_1_hook_activation | Hook activation result | HOOKS ACTIVATED, HOOKS FAILED |
| 0.2 | gate_0_2_context_approval | Project context approval | CONTEXT APPROVED, CONTEXT REJECTED, CONTEXT NOT READY |
| 1.1 | gate_1_1_spec_draft | Spec draft approval | APPROVE, REVISE, FRESH REVIEW |
| 1.2 | gate_1_2_spec_post_review | Spec post-review decision | APPROVE, REVISE, FRESH REVIEW |
| 2.1 | gate_2_1_blueprint_approval | Blueprint approval | APPROVE, REVISE, FRESH REVIEW |
| 2.2 | gate_2_2_blueprint_post_review | Blueprint post-review decision | APPROVE, REVISE, FRESH REVIEW |
| 2.3 | gate_2_3_alignment_exhausted | Alignment iteration limit reached | REVISE SPEC, RESTART SPEC, RETRY BLUEPRINT |
| 3.1 | gate_3_1_test_validation | Test correctness validation | TEST CORRECT, TEST WRONG |
| 3.2 | gate_3_2_diagnostic_decision | Diagnostic escalation decision | FIX IMPLEMENTATION, FIX BLUEPRINT, FIX SPEC |
| 4.1 | gate_4_1_integration_failure | Integration test failure decision | ASSEMBLY FIX, FIX BLUEPRINT, FIX SPEC |
| 4.2 | gate_4_2_assembly_exhausted | Assembly fix ladder exhausted | FIX BLUEPRINT, FIX SPEC |
| 5.1 | gate_5_1_repo_test | Repository test result | TESTS PASSED, TESTS FAILED |
| 5.2 | gate_5_2_assembly_exhausted | Repository assembly exhausted | RETRY ASSEMBLY, FIX BLUEPRINT, FIX SPEC |
| 6.0 | gate_6_0_debug_permission | Debug permission reset | AUTHORIZE DEBUG, ABANDON DEBUG |
| 6.1 | gate_6_1_regression_test | Debug regression test validation | TEST CORRECT, TEST WRONG |
| 6.2 | gate_6_2_debug_classification | Debug fix classification | FIX UNIT, FIX BLUEPRINT, FIX SPEC |
| 6.3 | gate_6_3_repair_exhausted | Repair agent exhausted | RETRY REPAIR, RECLASSIFY BUG, ABANDON DEBUG |
| 6.4 | gate_6_4_non_reproducible | Non-reproducible bug decision | RETRY TRIAGE, ABANDON DEBUG |

**Invariant:** The OPTIONS field in the routing script's `human_gate` output must list exactly the valid status strings from the table above for the corresponding gate. The `update_state.py` script must match against exactly these strings. No other strings are valid gate responses. If the human types anything that does not exactly match one of the listed options, the main session re-presents the gate prompt.

**Naming clarification (Gate 5.1):** The human-typed gate status strings `TESTS PASSED` and `TESTS FAILED` (with spaces, no payload) are distinct from the system-generated command result status lines `TESTS_PASSED: N passed` and `TESTS_FAILED: N passed, M failed` (with underscores and count data) defined in Section 18.3. Gate 5.1 is a human gate where the human reports the result of manually running tests in the delivered repository; the system-generated status lines are written automatically by the main session after `run_command` actions during Stages 3 and 4. The two never appear in the same context.

**Shared vocabulary:** Gates 1.1, 1.2, 2.1, and 2.2 share the same status strings (APPROVE, REVISE, FRESH REVIEW). The gate ID provides contextual distinction -- `update_state.py` dispatches to different state transitions based on the gate ID, not the status string alone.

---

## 19. Universal Write Authorization

SVP-managed projects are protected by a two-layer write authorization system that governs all file modifications.

### 19.1 Layer 1 -- Filesystem Permissions

When no Claude Code session is active, the SVP launcher sets the entire workspace directory tree to read-only (`chmod -R a-w`). On session start, the launcher restores write permissions before launching Claude Code. Between sessions (including during automatic restart cycling), the workspace is read-only at the OS level. No process can modify files.

Only the workspace directory is locked. The deliverable repository (`projectname-repo/`) is unprotected -- the human can open it in other tools, push to GitHub, etc.

### 19.2 Layer 2 -- Hook-Based Write Authorization

When a Claude Code session is active, `PreToolUse` hooks validate every write operation against the current pipeline state. Each pipeline state defines a set of writable paths -- only those paths are permitted. All others are blocked regardless of source (main session, subagent, or any tool).

**Two-tier path authorization:**

- **Infrastructure paths** (`.svp/`, `pipeline_state.json`, `ledgers/`, `logs/`): always writable. These are SVP's operational files and must be accessible at every pipeline state.
- **Project artifact paths** (`src/`, `tests/`, `specs/`, `blueprint/`, `references/`, `projectname-repo/`): state-gated. Writable only when the current pipeline state authorizes writes to that specific path. For example, `src/unit_4/` is writable only when Stage 3 is processing unit 4. `specs/stakeholder.md` is writable only during Stage 1 or during a targeted spec revision.


**Debug session write rules.** When a debug session is active (see Section 12.9), the following write rules apply. These rules are activated only after the human explicitly authorizes the debug session at Gate 6.0 (AUTHORIZE DEBUG). Before authorization, the triage agent operates in read-only mode -- it can read all project files but cannot modify any artifacts. When the human responds AUTHORIZE DEBUG, `update_state.py` updates `pipeline_state.json` to set `debug_session.authorized: true`, which activates all of the following write rules simultaneously:

- `tests/regressions/`: always writable during any authorized debug session, regardless of classification. Regression tests are the single point of leverage for the debug loop.
- During a build/environment fix (classification `build_env`): the repair agent can write to environment files, package configuration, `__init__.py` files, and directory structure. It **cannot** write to implementation files (any `.py` file in `src/unit_N/` other than `__init__.py`). If the repair agent attempts to modify implementation code, the hook blocks the write -- the agent must return `REPAIR_RECLASSIFY` instead.
- During a single-unit fix cycle (classification `single_unit`): `src/unit_N/` and `tests/unit_N/` are writable only for the affected unit(s) identified by the triage agent. The pipeline state remains at Stage 5 throughout -- the `debug_session` object tracks the Stage 3 re-entry context.
- `.svp/triage_scratch/`: writable during triage, for diagnostic scripts written by the bug triage agent.

**Hook path resolution.** The project-level `hooks.json` that SVP copies to managed projects must use paths relative to the project root, not plugin-specific variables (such as `${CLAUDE_PLUGIN_ROOT}`) that do not resolve outside the plugin context. The SVP launcher is responsible for rewriting hook script paths during the copy operation so they reference the correct location within the project's `.claude/scripts/` directory.

### 19.3 Non-SVP Session Protection

A `PreToolUse` hook on the `bash` tool blocks all bash tool use in non-SVP sessions. If a human opens a plain Claude Code session (via `claude` rather than `svp`) in the SVP project directory without the SVP plugin active and attempts to modify files, the hook prevents the modification, informs the human that this is an SVP-managed project, and guides them to use the SVP plugin.

A `README_SVP.txt` at the workspace root explains the protection mechanism.

---

## 20. Autonomous Execution Protocol

During autonomous sequences -- test generation, implementation, red/green runs, coverage review -- the pipeline announces the start of each sequence and instructs the human to wait.

### 20.1 Announcement

Before each autonomous sequence, the main session presents a message such as: "Starting test generation for Unit 4: Spike Detection. Please wait -- I'll let you know when I need your input."

The MESSAGE field in the routing script output provides the content for this announcement.

### 20.2 Deferral of Human Input

The CLAUDE.md instructs the main session to defer human input during autonomous execution. If the human types during an autonomous sequence despite the announcement, the main session is instructed to acknowledge and defer: "I'm currently running the red validation. I'll address your question when this sequence completes."

This is a behavioral expectation with soft enforcement, not a hard platform constraint. If interruption causes problems, the stated recovery is a session restart.

### 20.3 Command Availability

Commands (`/svp:help`, `/svp:hint`, `/svp:status`, etc.) remain available at gates and between units, not during autonomous execution.

## 21. Agent Summary

The following agents operate within SVP. Each is a stateless subagent spun up for a specific task with a specific role, producing output and then being dismissed. Each agent has two context components: a **role prompt** (the agent definition file, containing behavioral instructions) and a **task prompt** (project-specific content assembled by the preparation script for each invocation).

| Agent | Stage | Interaction | Task Prompt Receives | Produces | Default Model |
|---|---|---|---|---|---|
| Setup Agent | 0 | Ledger multi-turn | Environment state, ledger | Structured `project_context.md` (actively rewritten for LLM consumption) | `claude-sonnet-4-6` |
| Stakeholder Dialog Agent | 1 (+ revision mode) | Ledger multi-turn | Ledger, reference summaries, project context (+ critique in revision mode) | Stakeholder spec draft (or targeted amendment) | `claude-opus-4-6` |
| Stakeholder Spec Reviewer Agent | 1 | Single-shot | Stakeholder spec, project context, reference summaries (no ledger) | Structured critique | `claude-opus-4-6` |
| Reference Indexing Agent | 1, 2+ | Single-shot | Full reference document or repo (via GitHub MCP for repos) | Structured summary | `claude-sonnet-4-6` |
| Blueprint Author Agent | 2 | Ledger multi-turn | Stakeholder spec, checker feedback, reference summaries, ledger | Complete blueprint | `claude-opus-4-6` |
| Blueprint Checker Agent | 2 | Single-shot | Stakeholder spec (with working notes) + blueprint | Alignment verdict + critique (dual-format) | `claude-opus-4-6` |
| Blueprint Reviewer Agent | 2 | Single-shot | Blueprint, stakeholder spec, project context, reference summaries (no ledger) | Structured critique | `claude-opus-4-6` |
| Test Agent | 3 | Single-shot | Unit definition + upstream contracts from blueprint | pytest test suite + synthetic data + data assumption declarations | `claude-opus-4-6` |
| Implementation Agent | 3, 4 | Single-shot | Unit definition + upstream contracts from blueprint (+ diagnostic guidance + hint in fix ladder) | Python implementation | `claude-opus-4-6` |
| Coverage Review Agent | 3 | Single-shot | Blueprint unit definition + passing tests | Missing coverage report + additional tests | `claude-opus-4-6` |
| Diagnostic Agent | 3, 4 | Single-shot | Stakeholder spec + unit blueprint + failing tests + errors | Three-hypothesis analysis (dual-format) | `claude-opus-4-6` |
| Integration Test Author | 4 | Single-shot | Stakeholder spec + contract signatures from all units (reads source on demand) | Integration test suite | `claude-opus-4-6` |
| Git Repo Agent | 5 | Single-shot | All verified artifacts + reference documents (+ error output in fix cycle) | Clean git repository | `claude-sonnet-4-6` |
| Help Agent | Any | Ledger multi-turn | Project summary + stakeholder spec + blueprint (+ gate flag in gate-invocation mode) | Terminal status line only to main session; `hint forwarded` with hint content at gates | `claude-sonnet-4-6` |
| Hint Agent | Any | Single-shot (reactive) / Ledger multi-turn (proactive) | Logs, documents, human concern | Diagnostic analysis + decision options | `claude-opus-4-6` |
| Redo Agent | 2, 3, 4 | Single-shot | Pipeline state summary, human description of error, current unit definition (reads documents on demand) | Error classification (dual-format) + rollback action | `claude-opus-4-6` |
| Bug Triage Agent | Debug loop | Ledger multi-turn | Stakeholder spec + blueprint + source code + test suites + ledger + real data access (via Bash) | Triage classification + regression test specification (dual-format) | `claude-opus-4-6` |
| Repair Agent | Debug loop | Single-shot | Build/environment error diagnosis + environment state (+ prior failure output in retry) | Build/environment fix | `claude-sonnet-4-6` |

Model identifiers refer to specific Claude API model strings. `claude-opus-4-6` is the most capable available model; `claude-sonnet-4-6` is a highly capable but more economical model. `claude-haiku-4-5-20251001` is available as a further cost-reduction option for the help agent if desired. The specific model strings are configured in `svp_config.json` and can be changed at any time. Changes take effect on the next agent invocation. The distinction between Opus and Sonnet assignments reflects the design principle that correctness-critical roles (test generation, implementation, blueprint checking, diagnostics) warrant the most capable model, while support roles (indexing, help, setup, repo creation) can use a more economical model without compromising the pipeline's defensive properties.

Note: The Implementation Agent is also invoked for assembly fixes during Stage 4, constrained to interface-boundary changes (see Section 11.4).

Note: At decision gates, agents receiving task prompts may also receive an optional human domain hint under the heading `## Human Domain Hint (via Help Agent)`. The hint is formulated by the Help Agent in gate-invocation mode (see Section 14.4) and forwarded by the main session via the deterministic hint prompt assembler. The hint is a signal, not a command -- the receiving agent evaluates it alongside its other context. If the hint contradicts the blueprint, the agent returns `HINT_BLUEPRINT_CONFLICT: [details]` for human resolution.

---

## 22. Configuration

### 22.1 Configuration File

`svp_config.json` in the project workspace root. Contains all tunable parameters:

- `iteration_limit`: maximum attempts for all bounded retry mechanisms in the pipeline. This single shared key governs: blueprint alignment loop iterations, red-run retries, assembly fix cycle attempts, debug triage iteration limits, and repair agent fix attempts. Default: 3. Note: this key does not govern fix ladder structures (implementation fix ladder, test fix ladder), whose shapes are fixed by design (see Sections 10.7 and 10.8) and are not configurable.
- `models.test_agent`: model for test generation. Default: `"claude-opus-4-6"`.
- `models.implementation_agent`: model for code generation. Default: `"claude-opus-4-6"`.
- `models.help_agent`: model for help sessions. Default: `"claude-sonnet-4-6"`.
- `models.default`: model for all other agents. Default: `"claude-opus-4-6"`.
- `context_budget_override`: optional manual override for context budget in tokens. Default: null (auto-derived from smallest model context window minus estimated overhead).
- `context_budget_threshold`: percentage of context budget reserved for fixed context load per unit. Default: 65 (meaning fixed context must not exceed 65% of budget, leaving 35% for variable context in worst-case fix ladder invocations).
- `compaction_character_threshold`: minimum character count for tagged lines to be presumed self-contained during compaction. Tagged lines above this threshold have their bodies deleted; those at or below keep their bodies as insurance. Default: 200. This threshold is intentionally character-based rather than token-based: compaction is performed by a deterministic script with no LLM involvement (Section 3.3), so introducing a tokenizer dependency would add complexity for no benefit. The threshold is a heuristic safety net, not a precision measurement -- character count is a sufficient proxy.
- `auto_save`: whether to auto-save after every transition. Default: true.
- `skip_permissions`: whether to pass `--dangerously-skip-permissions` to Claude Code on launch. When true, Claude Code runs without interactive permission prompts -- required for autonomous pipeline execution. The hook-based write authorization system (Section 19) remains active regardless of this setting and provides the actual safety boundary. Default: true.

The human can edit this file at any time. Changes take effect on the next agent invocation. No pipeline restart is required. If a model change reduces the effective context budget below the size of an existing blueprint, the system warns the human on next invocation.

### 22.2 Pipeline State File

`pipeline_state.json` in the project workspace root. Tracks all information necessary for deterministic routing, session recovery, status reporting, and pass history. Behavioral requirements:

- Current stage (0-5, plus pre-Stage-3).
- Current sub-stage within that stage (e.g., which unit is being verified in Stage 3; `hook_activation` or `project_context` within Stage 0).
- Blueprint alignment iteration count (Stage 2).
- Fix ladder position for the current unit (Stage 3). Reset on unit completion or document revision escalation.
- Red run retry count for the current unit (Stage 3). Reset when the unit advances past the red run.
- `total_units`: the number of units defined in the blueprint. Set during pre-Stage-3 infrastructure setup. Required by the unit completion logic to determine when all units are done and Stage 4 should begin (see Section 9.3 for the `total_units` invariant).
- List of verified units with verification timestamps.
- Pass history: for each pass, how far it reached, why it ended, and when.
- References to log files for rejection reasons, diagnostic summaries, and session records.
- `debug_session`: object or null. When a post-delivery debug session is active (Section 12.9), contains the bug description, triage classification (build/environment, single-unit, or cross-unit), affected unit(s), regression test path, current debug phase status, and `authorized` (boolean indicating whether the human has authorized debug write permissions at Gate 6.0). Null when no debug session is active.
- `debug_history`: list of completed debug session records (analogous to `pass_history`). Each record includes the bug ID, what was reported, which unit was affected, what the fix was, and timestamps.

The complete schema is a blueprint concern. The spec states the behavioral requirement; the blueprint defines the schema as an internal contract between all deterministic components.

The state file is updated automatically by deterministic scripts after every significant transition: stage completion, unit verification, blueprint blessing, spec approval. Each state update script validates that the preconditions for the transition are met before writing. The `/svp:save` command additionally verifies file integrity and confirms to the human that the save is complete.

### 22.3 Resume Behavior

On resume, the routing script reads the state file and the main session presents a mandatory context summary: "You are building project X. You are currently at Stage 3, unit 7 of 12. Units 1-6 are verified. This is pass 2 (pass 1 reached unit 9 before a spec revision was needed). Shall I continue?" The human confirms, and the pipeline resumes.

If the state file is missing or corrupt, recovery uses deterministic file-presence checking as described in Section 6.1. The setup script checks for completion markers in approved documents and unit marker files, reconstructs a conservative state estimate, and presents it to the human for confirmation. No LLM inference. If reconstruction fails entirely, start fresh.

---

## 23. Document Version Tracking

### 23.1 Rationale

When the stakeholder spec or blueprint is revised during construction, the history of what changed and why is valuable knowledge. It records which requirements were discovered during construction rather than known upfront, which blueprint decompositions failed alignment and why, and what the human learned about their own problem through the building process. This history is essential for the human who returns months later to modify their system -- it tells them where the original understanding was fragile.

### 23.2 Versioning Behavior

Every time a document is revised, before the revision is applied:

1. The current version is copied to the history directory with a version number: `stakeholder_v1.md`, `stakeholder_v2.md`, `blueprint_v1.md`, etc.
2. A diff summary is saved alongside it: `stakeholder_v1_diff.md`. This contains:
   - What changed (a brief, human-readable description of the revision).
   - Why it changed (the diagnostic critique, checker rejection, or human decision that prompted the revision).
   - What stage triggered the revision (e.g., "Stage 2, blueprint alignment iteration 2" or "Stage 3, unit 5 diagnostic escalation").
   - A timestamp.
3. The current working version remains `stakeholder.md` or `blueprint.md` -- always the latest. Versioned copies are history, not active documents.

Each review cycle (from the stakeholder spec reviewer or blueprint reviewer) that results in a revision increments the document version number.

### 23.3 Directory Structure

```
projectname/
|-- specs/
|   |-- stakeholder.md           <- current working version
|   +-- history/
|       |-- stakeholder_v1.md
|       |-- stakeholder_v1_diff.md
|       |-- stakeholder_v2.md
|       +-- stakeholder_v2_diff.md
|-- blueprint/
|   |-- blueprint.md             <- current working version
|   +-- history/
|       |-- blueprint_v1.md
|       |-- blueprint_v1_diff.md
|       |-- blueprint_v2.md
|       +-- blueprint_v2_diff.md
```

### 23.4 Inclusion in Final Repository

The git repo agent includes the version history as documentation in the final delivered repository, in a `docs/history/` directory. The project's deliverable contains not just the final spec and blueprint, but the full evolution of understanding that produced them. This serves as institutional memory: the human can trace any design decision back to the moment it was made and understand the context that produced it.

---

## 24. Failure Modes and Recovery

### 24.1 Implementation Failure

Tests fail for a single unit. The test is confirmed correct by the human. The fix ladder runs: fresh agent attempt with diagnostic guidance and optional human hint -> if fail, diagnostic escalation with three-hypothesis discipline -> human decides fix implementation or fix document -> if fix implementation, one fresh agent attempt with diagnostic guidance and hint -> if fail, escalate to document revision.

Recovery: fix implementation locally. No restart.

### 24.2 Blueprint Failure

Discovered during blueprint alignment (Stage 2), unit verification (Stage 3), or integration testing (Stage 4). The blueprint does not faithfully represent the stakeholder spec, or its decomposition is structurally flawed.

Recovery: fix the blueprint, restart from Stage 2 (blueprint generation). A fresh blueprint author regenerates from scratch.

### 24.3 Spec Failure

Discovered at any stage. The stakeholder spec is incomplete, contradictory, or missing a requirement that only became apparent during later stages.

Recovery: targeted spec revision (Section 7.6) -- a focused Socratic dialog about the identified issue, followed by spec amendment and restart from Stage 2. If the problem is pervasive and the human recognizes that their fundamental understanding was wrong, the human may choose a full spec restart.

### 24.4 Alignment Non-Convergence

The blueprint alignment loop exceeds the configured iteration limit without convergence.

Recovery: mandatory diagnostic hint presented to the human. The hint agent analyzes the pattern of failures and recommends either a targeted spec revision (if the non-convergence points to a specific spec issue) or a full spec restart (if the pattern suggests pervasive underspecification). The human decides from explicit options.

### 24.5 Session Interruption

The human closes the terminal, loses connection, or otherwise exits unexpectedly.

Recovery: on next launch via `svp`, the launcher detects the project and resumes from the last saved state. With auto-save enabled (default), the human loses at most the current in-progress subagent call.

### 24.6 Token or Rate Limit Exhaustion

The model's context window or API rate limits are reached mid-operation.

Recovery: the system saves state, informs the human of the situation, and exits cleanly. On next launch, resumes from saved state. The human can check their API usage through their Anthropic console or Claude Code's built-in mechanisms.

Implementation guidance: the orchestration layer wraps every subagent invocation in error handling that detects API rate limit or context window exhaustion errors. On detection, the main session runs the save script, presents a plain-language message to the human explaining the situation (naming the specific limit reached if possible), and exits the session. The routing script does not need to handle this case -- it is a pre-routing error that the orchestration layer catches before any routing occurs. On the next session launch, normal resume behavior applies.

### 24.7 Non-SVP Session Modification Attempt

A human opens a plain Claude Code session in the SVP project directory without the SVP plugin active and attempts to modify files.

Recovery: the universal write authorization hooks prevent the modification (see Section 19.3), inform the human that this is an SVP-managed project, and guide them to use the SVP plugin. Filesystem permissions (read-only when no session is active) provide the first line of defense.

### 24.8 Human Gate Error

The human approved something incorrect during pipeline execution -- confirmed a wrong test assertion, approved a stakeholder spec draft without catching an issue, or made a judgment call they now regret. Discovered when the human realizes the error at any later point.

Recovery: the human invokes `/svp:redo`. The redo agent traces the error through the document hierarchy and classifies the source. If it's a spec or blueprint error, the existing restart flow applies. If it's a gate error (documents are correct, human approved the wrong thing), the pipeline rolls back to the affected unit and invalidates all units from that point forward, reprocessing them from scratch.

### 24.9 Ledger Overflow

A conversation ledger approaches the context limit for its associated agent role during an extended Socratic dialog or help session.

Recovery: the system warns the human at 80% capacity. At 90%, compaction is required before continuing. The compaction script preserves all finalized decisions (self-contained tagged lines above 200 characters have bodies deleted; thinner tagged lines keep bodies as insurance) and ambiguous content while condensing exploratory exchanges. If compaction is insufficient, the human is advised to finalize the current phase.

### 24.10 Repository Assembly Failure

The git repo agent produces a repository where tests do not pass when the human runs them.

Recovery: the bounded fix cycle (Section 12.4). Up to 3 fresh reassembly attempts with error output as context. If all 3 fail, the human is presented with Gate 5.2 for escalation options.

### 24.11 Conda Environment Guardrail Violation

Any pipeline script, test runner, or agent invocation uses bare `python`, `pip`, or `pytest` outside of the project conda environment instead of `conda run -n {env_name}`.

**Constraint:** All test execution, package installation, and script invocation that targets the project environment must use `conda run -n {env_name} <command>`. The only permitted exception is `pip install -e .` for local package installation, which must be run inside an already-activated conda environment. Direct use of system Python, MacPorts Python, or any Python interpreter outside the project conda environment is a pipeline violation. The conda environment name is derived deterministically from the project name: `project_name.lower().replace(" ", "_").replace("-", "_")`. The routing script and update_state script must use this derivation -- never hardcode `projenv` or any other fixed env name.

Recovery: identify which script is using the wrong interpreter, patch it to use `conda run -n {env_name}`, and re-run the failing step.

### 24.12 Repository Output Path Collision

The git repo agent creates the output repository at a relative path or inside the project workspace, rather than at the correct sibling directory.

**Constraint:** The output repository must always be created at the absolute path `{project_root.parent}/{project_name}-repo`. The agent must never use relative paths for repository creation. Before creating the repository, the agent must check if the output path already exists and remove it completely if so -- never attempt to create a repository on top of an existing directory.

Recovery: delete the misplaced directory, correct the path, and re-run Stage 5.

### 24.13 Blueprint Tier 2 Heading Format Error

The blueprint author agent writes Tier 2 section headings in a format that the infrastructure parser cannot match, causing `setup_infrastructure.py` to fail with "No signature blocks found in blueprint".

**Constraint:** The blueprint must use this exact heading format for all Tier 2 signature sections:

```
### Tier 2 — Signatures
```

The separator must be an em-dash, not a hyphen (-) or double hyphen (--). No additional words may appear after "Signatures" on the same heading line. The infrastructure parser (`dependency_extractor.py`) matches this exact string -- any deviation causes a hard failure.

Recovery: correct the heading format in `blueprint/blueprint.md` and re-run infrastructure setup.

---

## 25. Test Data

Test agents generate synthetic test data informed by any data characteristics described in the stakeholder spec. If the spec says "EEG recordings sampled at 30kHz with typical motion artifacts," the test agent generates fixtures matching that description. The quality of synthetic data is bounded by the clarity of the human's description of their data.

**Synthetic data assumption declarations.** The test agent must declare its synthetic data generation assumptions as part of its output (see Section 10.1). These assumptions are presented to the human at the test validation gate (Section 10.7). The human evaluates whether the assumptions match their real domain data. If not, the human can reject the tests and provide a hint about what realistic data looks like -- for example, "motion artifacts are not Gaussian noise; they're correlated low-frequency signals that look like slow waves."

Human-provided real data files are not supported in this version. This is a recognized limitation and a candidate for future enhancement.

---

## 26. Deterministic Components

The following components are implemented as Python or bash scripts with no LLM involvement. They are the mechanical backbone of the pipeline:

- **State management scripts:** read, update, and validate `pipeline_state.json`. Critically, the update scripts validate preconditions before writing new state -- this is the primary stage-gating mechanism.
- **Routing script:** reads the current state file and outputs the exact next action as a structured key-value block (see Section 17) with one of five action types. The main session executes this output rather than reasoning about pipeline flow independently. This script is the primary mechanism for constraining the main session's orchestration behavior. During Stage 0, the routing script handles the `hook_activation` and `project_context` sub-stages.
- **Preparation script (`prepare_task.py`):** assembles task prompt files for agent invocations and gate prompt files for human decision gates. Takes the agent type (or gate identifier), unit number, ladder position, and other parameters as input and produces a ready-to-use file at the path specified in the routing script's TASK_PROMPT_FILE or PROMPT_FILE field. The main session receives a single PREPARE command that produces the file; the internal decomposition of the preparation logic (monolithic script vs. composed pipeline) is a blueprint decision. The preparation script's test suite must cover every combination of agent type, gate type, and ladder position -- this is an elevated coverage requirement, distinct from the smaller test suites adequate for simpler deterministic components.
- **Stub generator:** parses machine-readable signatures from the blueprint using Python's `ast` module and produces Python stub files with `NotImplementedError` bodies. Also generates stubs or mocks for upstream dependencies based on their contract signatures.
- **Blueprint extractor:** extracts a single unit's definition and upstream contract signatures from the full blueprint for context-isolated agent invocations. This extracted content becomes part of the task prompt for the relevant subagent.
- **Dependency extractor:** scans all signature blocks across all blueprint units, extracts every external import statement, and produces a complete dependency list. Used during pre-Stage-3 infrastructure setup (Section 9).
- **Import validator:** executes each extracted import statement in the Conda environment to verify resolution. Catches version-specific API issues before Stage 3 begins.
- **Ledger manager:** append to, read, compact, and (where specified) clear conversation ledgers. Compaction preserves self-contained tagged lines (above the 200-character threshold, bodies are deleted; at or below, bodies are preserved), `[HINT]` entries, decisions, confirmed facts, and ambiguous content while condensing exploratory exchanges.
- **Hint prompt assembler:** takes the raw hint content from a help agent's terminal output, the gate metadata, the receiving agent type (test or implementation), and the ladder position, and produces a wrapped `## Human Domain Hint (via Help Agent)` section for inclusion in the task prompt. Applies prompt engineering principles to frame the hint appropriately for the specific context. No LLM involvement -- the wrapping uses deterministic templates with variable substitution.
- **Command scripts:** logic for `/svp:save`, `/svp:quit`, `/svp:clean`, and `/svp:status`.
- **Universal write authorization hooks:** validate every write operation against the current pipeline state. Two-tier path authorization (infrastructure always-writable, artifacts state-gated). Bash tool blocking for non-SVP sessions.
- **SVP launcher:** manages the complete session lifecycle: prerequisite verification, directory creation, filesystem permission management, session cycling (detects restart signal files, relaunches Claude Code), and clean separation from regular Claude Code usage.

These scripts have pytest test suites to validate their correctness. The preparation script has an elevated-coverage test suite covering every combination of agent type, gate type, and ladder position. Other deterministic components have smaller test suites proportionate to their complexity. These test suites are part of the SVP plugin itself, not part of any project built with SVP.

---

## 27. Future Directions

Two directions are recognized for future development:

- **Multi-language support:** extending beyond Python to other languages (R, Julia, MATLAB, and others). The pipeline's architecture -- blueprint contracts, stub generation, red-green validation, agent separation -- is language-agnostic in principle. Adaptation requires language-specific test frameworks, stub generators, and environment managers. Each target language would be specified through a future revision of this stakeholder spec.

- **Model evolution adaptation:** re-implementing pipeline components as the underlying models change. Larger context windows would allow coarser unit granularity and richer task prompts. Improved instruction following would permit tighter agent constraints. New capabilities (persistent memory, native tool use, multi-modal output) could change which components need to be deterministic scripts versus agent-driven. The pipeline should be periodically reassessed and rebuilt to exploit the capabilities of current models rather than remaining anchored to the constraints of the models available when it was first constructed.

The CLI is a foundational interface decision. SVP operates through Claude Code's terminal interface -- typed conversation and explicit commands. This is not an interim choice pending a graphical interface. The terminal interaction model is intrinsic to the design: it matches the orchestration architecture (the main session is a CLI agent), it preserves full conversation history as text, and it ensures that every human-pipeline interaction is explicit, auditable, and reproducible. No graphical interface is planned or considered.

---

## 28. Glossary

### System

- **SVP (Stratified Verification Pipeline):** The complete system described in this spec. A deterministically orchestrated, sequentially gated development process where a domain expert authors requirements in natural language and LLM agents generate, verify, and deliver a working Python project. The pipeline's orchestration -- state transitions, routing, stage gating -- is controlled by deterministic scripts. The LLM agents operating within this framework are not themselves deterministic but are maximally constrained by a four-layer architecture: CLAUDE.md, routing script REMINDER blocks, agent terminal status lines, and hooks with universal write authorization.

### Documents

- **Stakeholder Spec:** The first-tier document. A natural language description of what the system must do, for whom, under what constraints, and what constitutes success or failure. Authored by the human through Socratic dialog. The single source of truth for intent. Always a clean document -- working notes are absorbed into the body at every iteration boundary, never left as appended patches.

- **Blueprint:** The second-tier document. A technical decomposition of the stakeholder spec into discrete units, each defined by the three-tier unit template: free prose (description), valid Python parseable by `ast` (machine-readable signatures, invariants), and structured text following defined patterns (error conditions, behavioral contracts, dependencies). Generated by an agent, verified for alignment with the stakeholder spec by a separate agent. The single source of truth for implementation structure.

- **Unit:** The smallest piece of code that can be independently tested against its blueprint contract without requiring any other unit's implementation to exist. A unit might be a single function, a class, or a small module -- the blueprint author decides based on the problem's structure. Each unit is defined by the three-tier template. Units are ordered by dependency -- each unit may depend only on previously defined units, never on later ones. The first unit is the first piece of domain logic; the last unit is the entry point. Unit boundaries must be clean interfaces: if unit B depends on unit A, unit B's tests mock unit A based on its contract, never its implementation.

- **Machine-Readable Signatures:** Python syntax within each unit's blueprint definition: import statements declaring all referenced types, followed by type-annotated function and class signatures with ellipsis bodies. Parsed by the stub generator using Python's standard `ast` module. Must be syntactically valid Python with all referenced types having corresponding import statements. This format is domain-agnostic -- the domain-specific decisions (which libraries, which types, which function names) are made by the blueprint author agent at project time.

- **Contract:** The explicit interface definition between units. Specifies what one unit promises to provide and what another unit expects to receive. Lives in the blueprint as behavioral contracts (discrete testable claims) and machine-readable signatures.

- **Invariant:** A condition that must be true before and after a unit executes. Defined in the blueprint as Python `assert` statements with descriptive messages, parseable by `ast`.

- **Topological Order:** The dependency-driven sequence in which units are built and verified. The first unit is the first piece of domain logic (no upstream dependencies within the project). The last unit is the entry point (depends on everything else). No circular dependencies are possible by construction.

- **DAG (Directed Acyclic Graph):** The dependency structure of units in the blueprint. Each unit may depend on previously defined units but never on units defined later (no-forward dependencies), forming a directed acyclic graph. This structure guarantees a valid topological build order, bounded context per unit, and structurally impossible circular dependencies. The DAG is a core architectural principle -- it is used both by the automated pipeline and during SVP's own construction.

- **Pipeline State:** A JSON file in the project directory that records the current stage of the pipeline, which units are verified, loop iteration counts, pass history, and references to logs. The source of truth for resuming interrupted sessions and for deterministic routing of pipeline progression. Updated exclusively by deterministic scripts that validate preconditions before writing. The complete schema is a blueprint concern; the spec defines behavioral requirements.

- **SVP Configuration:** A JSON file in the project directory containing all tunable parameters: model assignments (using Claude API model strings such as `claude-opus-4-6` and `claude-sonnet-4-6`), iteration limits, context budget, context budget threshold, compaction character threshold, and auto-save settings. Editable at any time; changes take effect on next agent invocation.

- **Conversation Ledger:** An append-only JSONL file that records multi-turn exchanges between the human and an agent. Each entry includes role, content, and timestamp. Agents receive the full ledger as part of their task prompt on each invocation, maintaining conversational continuity while preserving true agent statelessness. Ledgers are auto-saved after every turn. Ledgers have bounded growth -- the system warns the human as a ledger approaches the context limit for its associated agent role, and compaction is required before overflow. Agent responses in ledgers follow a structured format: a free-form body followed by a mandatory tagged closing line (`[QUESTION]`, `[DECISION]`, or `[CONFIRMED]`). Tagged lines must be self-contained, carrying their own rationale and context. This structure enables effective compaction.

- **Ledger Compaction:** A deterministic operation that reduces ledger size. The compaction script identifies sequences where a series of agent bodies and human answers led to a `[DECISION]` or `[CONFIRMED]` closing. For tagged lines above 200 characters (configurable), the bodies are deleted -- the tagged line is presumed self-contained. For tagged lines at or below 200 characters, the bodies are preserved as insurance. Decisions, confirmed facts, `[HINT]` entries, and any untagged content are always preserved verbatim. The structured response format (every agent turn ends with a tagged closing line) ensures that nearly all content is classifiable, making compaction effective. Compaction is a safety valve for unusually long dialogs -- most projects complete without it firing.

- **Working Note:** A temporary clarification appended to the stakeholder spec during the blueprint dialog (Section 8.1). Added when the spec is correct but ambiguous on a narrow point that only became visible during technical decomposition. Working notes are incorporated into the spec body at every iteration boundary through a focused revision by the Socratic dialog agent. The spec is never left with appended working notes -- they are always absorbed into a clean document before the next iteration begins.

- **Reference Summary:** A structured summary of a reference document or GitHub repository, generated by the reference indexing agent on ingestion. For documents: what the document is, topics covered, key terms, and relevant sections. For repositories: purpose, directory structure, key modules, and relevant interfaces. Stored in `references/index/`. Used as context by agents; full documents retrieved on demand, and specific repository files read via GitHub MCP on demand when the human directs.

- **Version History:** The record of all revisions to the stakeholder spec and blueprint. Each revision is preserved as a versioned copy with an accompanying diff summary. Stored in the `history/` subdirectory under each document's directory and included in the final delivered repository.

- **Diff Summary:** A brief document saved alongside each versioned copy of a revised spec or blueprint. Records what changed, why it changed, what stage triggered the revision, and a timestamp. Provides traceability from any design decision back to the moment and context that produced it.

- **Reference Documents:** Human-provided materials that inform the stakeholder spec and blueprint -- papers, protocols, grant proposals, equipment specifications, GitHub repositories, or any material carrying domain knowledge relevant to the project. Documents are stored in the `references/` directory; repository URLs are recorded in `references/repos.json`. All references are indexed on ingestion with a structured summary. Provided during the Socratic dialog when the agent explicitly asks, or during Stages 0-2 via the `/svp:ref` command. Used as context by dialog and authoring agents but do not replace the Socratic dialog. For repository references, dialog agents can read specific files on demand via GitHub MCP when the human directs. Preserved in the final repository for traceability.

- **Targeted Spec Revision:** A focused correction to the stakeholder spec triggered by the blueprint checker, diagnostic agent, or human. The stakeholder dialog agent operates in revision mode: it receives the current spec plus a specific critique, conducts a Socratic dialog about just that issue, and produces an amendment. The unrevised portions of the spec are untouched. The pipeline then restarts from Stage 2 with a fresh blueprint dialog. Distinguished from a full spec restart by its scope -- only the identified issue is discussed.

- **Full Spec Restart:** A complete redo of the stakeholder Socratic dialog, producing a new spec from scratch. Rare and always human-initiated. Reserved for cases where the spec is fundamentally wrong or the human's understanding of their requirements has changed substantially. The system may recommend it but never forces it.

- **Revision Mode:** An operating mode of the stakeholder dialog agent used during targeted spec revision. In revision mode, the agent receives the current approved spec and a specific critique, and conducts a focused dialog about just that issue. It does not reopen settled topics. It probes for related implications of the change and confirms with the human that the revision is complete. Uses its own conversation ledger (`ledgers/spec_revision_N.jsonl`).

- **Completion Marker:** A deterministic marker used for state reconstruction when the pipeline state file is missing or corrupt. Document approval markers (`<!-- SVP_APPROVED: timestamp -->`) are appended to approved `stakeholder.md` and `blueprint.md` files. Unit completion markers are files placed at `.svp/markers/unit_N_verified` containing `VERIFIED: timestamp`. The setup script checks for these markers using file-presence and string-presence checks -- no LLM inference.

- **Gate Status String:** The exact string written to `.svp/last_status.txt` when the human responds to a decision gate. Gate status strings are the human-facing option text with no translation or prefix -- the string the human types is the string the POST script matches against. The complete vocabulary of gate status strings is defined in Section 18.4.

### Agents

- **Setup Agent:** Runs within Claude Code during Stage 0 after hook activation completes (sub-stage `project_context`). Conducts the `project_context.md` creation dialog -- actively rewriting the human's rough domain description into well-structured, LLM-optimized context. Enforces a quality gate: refuses to advance if the human cannot provide substantive content.

- **Stakeholder Dialog Agent:** Conducts the Socratic dialog with the human to produce the stakeholder spec. Uses the ledger-based multi-turn pattern. Asks one question at a time, seeks consensus per topic, surfaces contradictions and edge cases. Draws on reference summaries; retrieves full documents on demand. When GitHub MCP is configured and repository references have been added, gains GitHub MCP read access and can read specific files from referenced repositories when the human directs. Drafts the spec when all topics are covered and submits it for human review. Also operates in **revision mode** when triggered by the blueprint checker, diagnostic agent, or `/svp:redo`: receives the current approved spec plus a specific critique, and conducts a focused Socratic dialog about just the identified issue. In revision mode, it does not reopen settled topics. Also absorbs working notes into the spec body at iteration boundaries.

- **Stakeholder Spec Reviewer Agent:** A distinct agent that receives only the stakeholder spec, project context, and reference summaries -- no dialog ledger. Reads the document cold and produces a structured critique identifying gaps, contradictions, underspecified areas, and missing edge cases. Invoked when the human requests a fresh review at the spec approval gate. Unbounded review cycles.

- **Reference Indexing Agent:** Reads a full reference document or explores a GitHub repository and produces a structured summary. Single-shot invocation on each new reference. For document references, uses Claude's native document understanding for PDF content. For repository references, uses GitHub MCP tools to perform light indexing: reads the README, maps the directory structure, identifies key modules, and summarizes the repository's purpose, architecture, and relevant interfaces. Repository summaries follow the same format as document summaries and are stored in `references/index/`.

- **Blueprint Author Agent:** Conducts a Socratic dialog with the human about system decomposition, then generates the blueprint from the approved stakeholder spec and reference summaries. Uses the ledger-based multi-turn pattern. Asks domain-level questions about conceptual phases, data flow, and boundaries -- never about implementation details. When GitHub MCP is configured and repository references have been added, gains GitHub MCP read access and can read specific files from referenced repositories when the human directs -- for example, examining how an existing codebase structures its data flow to inform decomposition decisions. When the dialog surfaces a spec ambiguity, distinguishes between clarification (appends working note, continues) and contradiction (initiates targeted spec revision). Stateless across iterations -- each alignment loop iteration starts a fresh decomposition dialog, never resumes a prior one. Must produce units in the three-tier format with machine-readable signatures in Python syntax, and respect the context budget.

- **Blueprint Checker Agent:** A separate agent that receives the stakeholder spec (including any working notes), the blueprint, and reference summaries, and verifies their alignment, plus validates structural requirements (parseable Python signatures via `ast`, per-unit worst-case context budget within threshold, working note consistency). Reports only the most fundamental level when multiple issues are found. Three outcomes: spec is the problem (produces precise critique, triggering targeted spec revision), blueprint is the problem (regenerate blueprint with fresh author), alignment is good (bless and proceed). Produces dual-format output. Always a fresh agent per checking iteration.

- **Blueprint Reviewer Agent:** A distinct agent that receives only the blueprint, stakeholder spec, project context, and reference summaries -- no dialog ledger. Reads the documents cold and produces a structured critique. Invoked when the human requests a fresh review at the blueprint approval gate. Unbounded review cycles.

- **Test Agent:** Reads a single unit's definition from the blueprint (via task prompt) and generates a complete pytest test suite for that unit, including synthetic test data and synthetic data assumption declarations. Does not see the implementation. Uses `claude-opus-4-6` by default.

- **Implementation Agent:** Reads the same unit definition (via task prompt) and generates the Python implementation. A separate agent from the test agent, invoked independently and without access to the tests, to break correlated interpretation bias. Does not see the tests. In fix ladder positions, receives diagnostic guidance, prior failure context, and optional human hints.

- **Coverage Review Agent:** After tests pass, reads the blueprint and the passing test suite to identify behaviors implied by the blueprint that no test covers. Adds missing coverage. If newly added tests fail the green run, the failure follows the standard fix ladder.

- **Diagnostic Agent:** Invoked when tests fail. Applies the three-hypothesis discipline to identify where the failure lives (implementation, blueprint, or spec). Produces dual-format output: prose explanation for the human followed by a structured summary block for the routing layer. Terminal status line indicates the recommended level.

- **Integration Test Author Agent:** After all units pass individually, generates tests that cover cross-unit interactions. Receives stakeholder spec plus contract signatures from all units as task prompt; reads specific source files on demand from disk. Covers data flow, resource contention, timing, error propagation across boundaries, plus at least one end-to-end domain-meaningful validation from the stakeholder spec.

- **Git Repo Agent:** After integration tests pass, creates a git repository. Commits infrastructure first, then stakeholder spec and blueprint, then each unit with its tests in topological order, then integration tests, configuration, version history, and references. Participates in the bounded fix cycle (up to 3 reassembly attempts). Uses `claude-sonnet-4-6` by default.

- **Help Agent:** Available at any time. Uses ledger-based multi-turn within a session; ledger cleared on dismissal. Read-only (tool access restricted to Read, Grep, Glob, and web search), reinforced by universal write authorization hooks. Output to main session constrained to terminal status line only. Receives project summary and retrieves files on demand. Has web search access. Uses `claude-sonnet-4-6` by default. Pauses the pipeline while active, resumes cleanly on dismissal. In **gate-invocation mode** (when invoked at a decision gate), proactively offers hint formulation when the conversation produces an actionable observation. The human approves the hint text explicitly. The hint is forwarded to the next agent's task prompt via the deterministic hint prompt assembler (see Section 14.4).

- **Hint Agent:** Available at any time via `/svp:hint`. Operates in reactive mode (reads failure logs, identifies patterns) or proactive mode (asks human about their concern, examines documents). Produces diagnostic analysis and offers explicit decision options: continue or restart.

- **Redo Agent:** Invoked via `/svp:redo`. Receives a lean task prompt and uses read tools to trace the human's described error through the document hierarchy. Classifies the error as spec, blueprint, or gate error based on where the discrepancy originates -- does not ask the human to self-classify. Produces dual-format output. Executes the appropriate recovery: existing restart flow for document errors, or unit-level rollback for gate errors. Available during Stages 2, 3, and 4.

### Design Concepts

- **Socratic Dialog:** A structured conversation between a human and an agent where the agent interrogates the human's requirements through focused, sequential questions. Maintained through a conversation ledger. Used at the stakeholder spec stage (requirements gathering), during the blueprint dialog (decomposition structure), during targeted spec revision (focused correction), and during diagnosis.

- **Three-Hypothesis Discipline:** When tests fail and the diagnostic agent is invoked, it must articulate a plausible case for the failure at each of three levels -- implementation, blueprint, spec -- before converging on a diagnosis. Prevents defaulting to the easiest fix. The diagnostic agent produces dual-format output: prose explanation for the human followed by a structured summary block for the routing layer.

- **Fix Ladder:** The escalation sequence when a unit's tests fail and the test is confirmed correct. Fresh implementation agent with diagnostic guidance and optional hint -> if fail, diagnostic escalation with three-hypothesis discipline -> human decides -> if fix implementation, one fresh agent with guidance -> if fail, escalate to document revision. All retries use fresh agents -- same-agent retries are eliminated to reduce LLM judgment.

- **Test Fix Ladder:** The escalation sequence when the human determines a test is wrong at the test validation gate (Section 10.7). Fresh test agent with accumulated failure context and any human hint -> if fail, human re-involved with hint opportunity for one last attempt -> if fail, diagnostic agent determines whether blueprint contract is untestable. All retries use fresh agents.

- **Red-Green Cycle:** The TDD-inspired validation pattern applied to every unit. Tests are first run against a stub with no real implementation (the "red run" -- all tests must fail, proving they test real behavior). Then the same tests are run against the actual implementation (the "green run" -- all tests must pass). A test that never fails against a stub is defective: it asserts nothing meaningful.

- **Red Run:** The first test execution in the red-green cycle. Tests are run against a deterministically generated stub that raises `NotImplementedError` for every function. All tests must fail. Any test that passes against the stub is identified as defective and regenerated.

- **Green Run:** The second test execution in the red-green cycle. Tests are run against the real implementation. All tests must pass. Failures proceed to test validation and the fix ladder.

- **Stub:** A mechanically generated Python module containing all function and class signatures defined in the blueprint's machine-readable signatures (parsed using `ast`), where every function body raises `NotImplementedError`. Generated deterministically by a script -- no LLM involvement. Used exclusively for the red run.

- **Correlated Interpretation Bias:** The failure mode where a single agent misinterprets a specification and produces both implementation and tests that encode the same error. Tests pass, behavior is wrong. SVP breaks this by using separate agents for test generation and implementation, invoked independently with no shared context -- the implementation agent never sees the tests. Residual risk from using the same model is mitigated by procedural separation (agent isolation, coverage review, human gates, synthetic data assumption review) rather than model diversity.

- **Ruthless Restart:** SVP's core recovery strategy. Any document-level problem -- in the stakeholder spec or blueprint -- triggers a fix to the document followed by a complete forward restart: everything downstream of the revised document is regenerated from scratch. No surgical repair of downstream artifacts, no blast radius analysis, no selective re-validation. The document fix itself is proportionate to the problem: a localized spec issue gets a targeted revision (focused dialog about just that issue); only a fundamentally wrong spec warrants a full redo of the stakeholder dialog. The ruthlessness applies to forward regeneration, not to upstream rework. Corollary: when problems span multiple levels, report only the most fundamental.

- **Convergence Signal:** When independent agents reading the same spec produce similar blueprints, this indicates the spec is sufficiently clear. When they produce divergent blueprints, the spec is underspecified. Emergent property of using fresh agents for each blueprint attempt.

- **Diagnostic Hint:** An on-demand analysis available to the human at any time via `/svp:hint`. Operates in two modes: reactive (during a failure condition, reads accumulated logs and identifies patterns automatically) and proactive (during normal flow, asks the human what prompted their concern and which document they suspect before producing a targeted analysis). In both modes, the hint concludes by offering the human explicit options: continue the pipeline or revise a document and restart. Mandatory in reactive mode after the iteration limit is reached.

- **Binary Decision Logic:** At every diagnostic failure point, the diagnosis produces exactly two possible outcomes: fix implementation locally (continue), or fix a document (restart). No third option. No cascade analysis. No engineering judgment required from the human. Applies to diagnostic gates. Approval gates support three or more options as appropriate.

- **Decision Gate:** A point in the pipeline where the human makes a categorical choice. Gates present explicit response options -- the exact words to type for each option. If the human's response does not match any option, the main session re-presents the options rather than interpreting the ambiguous response. The `/svp:help` command is always available at any gate independent of the gate's response options. At most decision gates, the human may optionally invoke the Help Agent to formulate a domain hint that is forwarded to the next agent (see Section 14.4). Gates where the human is already in a free-text dialog (Socratic dialog, blueprint dialog) do not need the forwarding mechanism -- the dialog itself is the channel. The complete vocabulary of gate status strings is defined in Section 18.4.

- **Human Domain Hint:** An optional domain or engineering suggestion produced collaboratively by the human and the Help Agent at a decision gate, then forwarded to the next agent's task prompt by the main session via the deterministic hint prompt assembler. The human contributes domain expertise and intuition; the Help Agent contributes engineering literacy (code reading, logic tracing, issue identification). The human explicitly approves the final hint text before forwarding. The hint is additive context -- a signal, not a command. The receiving agent evaluates it alongside the blueprint contract, diagnostic analysis, and its own judgment. If the hint contradicts the blueprint, the agent returns `HINT_BLUEPRINT_CONFLICT: [details]` and the routing script presents a binary gate for human resolution. Hints are logged as `[HINT]` entries in the relevant ledger with full gate metadata. Hint entries are preserved verbatim during compaction.

- **Forward Hint:** The terminal output produced by the Help Agent in gate-invocation mode when the human approves a hint for forwarding. The help agent's terminal status line is `HELP_SESSION_COMPLETE: hint forwarded` followed by the hint content. The main session stores the hint content, runs the deterministic hint prompt assembler to wrap it in a context-dependent prompt block, and includes the wrapped hint in the next agent's task prompt under `## Human Domain Hint (via Help Agent)`. The hint is logged as a `[HINT]` ledger entry and the stored content is cleared after forwarding.

- **Context Isolation:** Each unit in Stage 3 is processed with only its own definition and upstream contract signatures, extracted from the blueprint by a deterministic script. No prior implementation code, no full blueprint. Keeps context bounded regardless of project size.

- **Universal Write Authorization:** The two-layer system governing all file modifications in SVP-managed projects. Layer 1: filesystem permissions managed by the SVP launcher (read-only when no session is active). Layer 2: hook-based write authorization when a session is active, validating every write against the current pipeline state. Two-tier path model: infrastructure paths (`.svp/`, `pipeline_state.json`, `ledgers/`, `logs/`) are always writable; project artifact paths (`src/`, `tests/`, `specs/`, `blueprint/`, `references/`, `projectname-repo/`) are state-gated, writable only when the current pipeline state authorizes writes to that specific path.

- **Assembly Fix:** A narrowly scoped code change at integration time that corrects how verified units connect without changing what any unit does according to its contract. Distinguished from a document fix by re-running the affected unit's existing tests -- if unit tests still pass, the fix is valid; if they fail, the problem is at the document level and requires a restart. Assembly fix ladder allows up to 3 attempts (two autonomous, one human-assisted).

- **Gate Error:** A failure mode where the documents (stakeholder spec and blueprint) are correct, but the human approved something wrong during pipeline execution -- confirmed an incorrect test assertion, missed an issue during spec review, or made a judgment call they now regret. Distinct from spec errors and blueprint errors in that the source of the problem is the human's decision, not the documents. The redo agent traces through the document hierarchy to classify the error rather than asking the human to self-classify. Handled through the `/svp:redo` command with unit-level rollback.

- **Unit-Level Rollback:** The recovery mechanism for gate errors. The pipeline rolls back to the start of the affected unit and invalidates all units from that point forward. Consistent with ruthless restart applied at unit granularity -- the pipeline cannot know whether the human's error propagated through their approval decisions at subsequent gates, so all forward units are reprocessed from scratch.

- **Four-Layer Constraint Architecture:** The defense-in-depth model for constraining the main session's orchestration behavior. Layer 1: CLAUDE.md (loaded at session start, sets the protocol). Layer 2: routing script REMINDER (refreshed before every action, reinforces the protocol at point of highest context recency). Layer 3: agent terminal status lines (structured output constraining what the main session interprets). Layer 4: hooks and universal write authorization (enforcement at boundaries, blocking unauthorized actions). No single layer is sufficient; together they provide practical reliability through redundancy.

- **Session Boundary:** A transition point where the SVP launcher cycles the Claude Code session to prevent context degradation. Fires at every major pipeline transition (unit completion, stage transitions, document revisions). The routing script signals boundaries through the `session_boundary` action type. The launcher manages the restart transparently -- the human sees a brief transition message and the pipeline continues in a fresh session.

- **Pass History:** The record of previous pipeline passes through Stage 3 and beyond. Each pass records how far it reached, why it ended (e.g., spec revision triggered), and when. Tracked in the pipeline state file. Displayed by `/svp:status` to provide context for the non-linear progress experience.

### Claude Code Ecosystem

- **Claude Code:** Anthropic's CLI-based AI agent. Runs in the terminal. Can read, write, and edit files, execute bash commands, and conduct natural language conversation. The runtime environment for SVP.

- **SVP Launcher:** A standalone CLI tool (`svp` command, or `svp new` for new projects) distributed alongside the SVP plugin but installed separately to the user's PATH. The launcher is not a plugin component -- it runs before Claude Code starts and therefore cannot be a skill, agent, hook, or MCP server within the plugin system. It manages the complete SVP session lifecycle: prerequisite verification, directory creation, copying deterministic scripts from the plugin into the project workspace, filesystem permission management, session cycling, and clean separation from regular Claude Code usage. The human types `svp` to start; the launcher does the rest.

- **Plugin:** A distributable bundle of skills, agents, commands, hooks, and configuration. SVP itself is distributed as a Claude Code plugin, installed via the plugin system. The plugin lives in its own subdirectory (`svp/`) within the repository. Its component directories (`commands/`, `agents/`, `skills/`, `hooks/`, `scripts/`) are at the plugin subdirectory's root level -- not nested inside `.claude-plugin/` and not at the repository root. The `.claude-plugin/plugin.json` manifest is the only file inside `.claude-plugin/`. The repository root contains a separate `.claude-plugin/marketplace.json` that registers the plugin for installation. The SVP launcher is distributed alongside the plugin as a separate CLI tool (see SVP Launcher) -- it is not a plugin component in the platform sense. During bootstrap, the launcher copies the plugin's `scripts/` directory into the project workspace so that routing script examples can use workspace-relative paths.

- **Skill (SKILL.md):** A directory containing a SKILL.md file with instructions and metadata that Claude loads on demand based on description matching. In SVP, the orchestration skill defines the main session's constrained behavior protocol.

- **Custom Agent (AGENT.md):** A markdown file defining a subagent with its own system prompt, tool restrictions, model assignment, and independent context window. Claude delegates tasks to agents based on description matching or explicit invocation. The markdown body becomes the agent's system prompt -- it does not receive the full Claude Code system prompt. Agents receive project-specific context through the task prompt provided when the main session spawns them. Tool restrictions in AGENT.md may be advisory rather than platform-enforced (see Section 4.2).

- **Slash Command:** A markdown file in the `commands/` directory defining a user-invoked command (e.g., `/svp:save`). When invoked, the markdown content is injected into the conversation as context. The content must be written as an explicit, unambiguous directive to the main session to execute a specific action -- typically running a deterministic script. The main session is an LLM and will interpret (not mechanically execute) the directive, so the wording must be precise and leave no room for deviation.

- **Hook:** An event-driven automation that fires at specific lifecycle points (PreToolUse, PostToolUse, Stop, SessionStart, SubagentStop, etc.). Used in SVP for universal write authorization and boundary enforcement. Hooks can block actions (exit code 2), provide additional context, or force continuation. They are the enforcement layer -- they prevent unauthorized actions but do not drive pipeline flow. Note: changes to hook configuration files require review through Claude Code's `/hooks` menu before taking effect. **Plugin hook format:** within a Claude Code plugin, hooks are defined in `hooks/hooks.json` and must use a top-level `"hooks"` wrapper key -- this differs from the flat format used in `.claude/settings.json`. The correct plugin format is `{ "hooks": { "PreToolUse": [...] } }`, not `{ "PreToolUse": [...] }`.

- **CLAUDE.md:** A project-level markdown file that gives any Claude session opened in the directory persistent context. SVP generates this during bootstrap to identify the project as SVP-managed and to define the orchestration protocol: how the main session should read the routing script output, execute the indicated action, relay task prompts verbatim, and avoid improvising pipeline flow.

- **Subagent:** An isolated Claude instance that works on a task independently and returns results to the main session. Operates in its own context window with approximately 20,000 tokens of overhead before any project content is loaded. Receives only its agent definition (system prompt) plus basic environment details -- all project-specific context must be provided through the task prompt or read from disk. Cannot spawn further subagents -- this is a hard platform constraint that shapes SVP's architecture (all subagent invocations are managed by the main session).

- **Task Prompt:** The project-specific content provided by the main session when spawning a subagent via the Task tool. Distinguished from the system prompt (agent definition), which contains the agent's behavioral instructions. In SVP, deterministic preparation scripts assemble the task prompt content (e.g., extracting a unit definition from the blueprint, assembling context for a specific fix ladder position). The preparation script produces a ready-to-use file at a specified path; the main session passes the contents verbatim.

- **MCP (Model Context Protocol):** An open standard for connecting LLMs to external tools and data sources. MCP servers are external processes that provide tools to Claude Code via a defined protocol. SVP uses MCP for optional GitHub repository access -- the GitHub MCP server allows the reference indexing agent and dialog agents to read external codebases that the human provides as context via `/svp:ref`. Web search for the help agent is provided via MCP. MCP server configuration is stored in Claude Code's native config system (`~/.claude.json`), not in SVP's `svp_config.json`.

- **GitHub MCP:** An optional MCP integration that provides read-only access to external GitHub repositories via the official GitHub MCP server (github.com/github/github-mcp-server). Configured during Stage 0 setup if the human wants to reference existing codebases as context, or on first use of `/svp:ref` with a GitHub URL. Requires a GitHub Personal Access Token scoped to read-only repository permissions; the token is stored in Claude Code's MCP configuration (`~/.claude.json`), not in any SVP project file. Used by the reference indexing agent to explore repositories on ingestion, and by dialog agents (stakeholder dialog, blueprint author) to read specific files on demand when the human directs. Never writes to any repository. SVP's own git repo delivery uses local git commands, not the GitHub MCP.

- **Main Session:** The top-level Claude instance that the human interacts with directly. In SVP, the main session is the orchestration layer -- maximally constrained by the four-layer architecture (CLAUDE.md, REMINDER, terminal status lines, hooks). It executes a six-step mechanical action cycle: run routing script, run PREPARE, execute ACTION, write status, run POST, repeat. It does not hold domain conversation history (that lives in ledgers), does not decide which stage to enter (that's determined by the routing script reading the state file), does not evaluate success or failure of agent outputs (that's determined by test execution and script validation), and cannot bypass stage boundaries (hooks enforce this). Its only area of freedom is how it communicates with the human -- phrasing, formatting, presentation. The design provides high-probability compliance with enforcement at boundaries, not theoretical determinism.

- **Routing Script:** A deterministic script that reads `pipeline_state.json` and outputs the exact next action as a structured key-value block (see Section 17): one of five action types (invoke_agent, run_command, human_gate, session_boundary, pipeline_complete) with all necessary parameters predetermined. The main session executes this output rather than reasoning about pipeline flow independently. Every output includes a REMINDER block reinforcing critical behavioral constraints at point of highest context recency.

- **Context Window:** The total amount of text an LLM can process in a single interaction. SVP's context budget is bounded by the smallest context window among configured models, minus the overhead required for agent system prompts and operational context (approximately 20,000 tokens per subagent invocation).

- **Conda:** A Python environment and package manager. Used by SVP to create isolated, reproducible project environments. The Conda environment is created during the pre-Stage-3 infrastructure step with all dependencies extracted from the blueprint's signature blocks.

---

## 29. Implementation Note

This spec is the stakeholder specification for building SVP itself. The implementation is built incrementally through the Claude web interface and Claude Code, with manual human testing. While the full automated SVP pipeline is not used to build SVP -- the builder can evaluate the generated output directly -- the construction process does rely on core SVP principles: a technical blueprint, tests, and a DAG with no-forward dependencies. The key difference is that LLM-assisted development requires a human in the loop for manual intervention at steps that the automated pipeline would handle through its agent orchestration. This is a pragmatic middle ground: the structural discipline of the pipeline without the full automation overhead.

The implementation should produce SVP as a Claude Code plugin and an accompanying standalone launcher CLI tool. The plugin contains: skill files for the orchestration protocol, agent definitions for each subagent role (including the two reviewer agents), slash commands for human interaction, hooks for universal write authorization and project protection, deterministic scripts for state management, routing, preparation, stub generation, dependency extraction, import validation, ledger management, and hint prompt assembly, a configuration file, test suites for the deterministic components (with elevated coverage for the preparation script), and documentation. The SVP launcher is a standalone CLI tool distributed alongside the plugin that manages session lifecycle. The plugin, once installed and the launcher placed on PATH, provides the complete SVP experience: the human types `svp` in a terminal, the launcher verifies prerequisites, and the pipeline proceeds as described in this spec.

---

*End of specification.*

<!-- SVP_APPROVED: 2026-02-28T22:00:00Z -->
