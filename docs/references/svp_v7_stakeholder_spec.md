# SVP — Stratified Verification Pipeline

## Stakeholder Specification v7.0 (SVP 2.0)

**Date:** 2026-03-08
**Supersedes:** Stakeholder Specification v6.0 (SVP 1.2)
**Build Tool:** SVP 1.2.1

---

## How to Read This Document

This specification is organized into three parts:

**Part I — What We Have Now** describes SVP 1.2 as-built: its architecture, its hardcoded assumptions, its use of Claude Code's features, and where those assumptions create barriers to future evolution.

**Part II — What We Want to Obtain** describes SVP 2.0: its goals, its new capabilities, its constraints, and the detailed behavioral requirements for everything that changes.

**Part III — How We Get There** describes the architectural strategy: what changes, what stays the same, what is deferred to the 2.x line, and why. It includes the product roadmap, because the shape of that roadmap constrains the abstractions that SVP 2.0 must build correctly the first time.

The separation between Parts II and III matters. Part II says what the system must do. Part III says how the system's internal architecture should be structured. A blueprint author reads Part II for behavioral requirements and Part III for architectural constraints. The human reviewer reads Part I to verify the baseline, Part II to verify the goals, and Part III to verify the strategy.

**Separation of concerns with the blueprint.** This document describes behavior — what the human sees, what agents produce, what files the pipeline reads and writes. It does not prescribe function signatures, class hierarchies, or module boundaries. Where this spec must constrain the blueprint, it says so explicitly.

**Relationship to the v6.0 spec.** This document extends the v6.0 stakeholder spec, which is incorporated by reference as the behavioral baseline. When this document says "unchanged from v6.0 Section N," the blueprint author must consult v6.0 for full requirements.

---

# PART I — WHAT WE HAVE NOW

---

## 1. SVP 1.2 Baseline

SVP 1.2 is a deterministically orchestrated, sequentially gated development system where a domain expert authors software requirements in natural language and LLM agents generate, verify, and deliver a working Python project. The pipeline's state transitions, routing logic, and stage gating are controlled by deterministic scripts. The LLM agents are maximally constrained by a four-layer architecture: CLAUDE.md, routing script REMINDER blocks, agent terminal status lines, and hook-based enforcement.

SVP 1.2 is delivered as a Claude Code plugin with 24 units, a standalone launcher CLI tool, and a complete test suite. It has been successfully used to build itself. The v6.0 stakeholder spec and v1.0 blueprint are the authoritative references.

### 1.1 Hardcoded Toolchain Assumptions in SVP 1.2

SVP 1.2 hardcodes the following toolchain choices throughout its codebase. These are not configurable and cannot be changed without modifying source code.

**Language: Python only.** Agent prompts instruct "generate a pytest test suite" and "produce a Python implementation." The stub generator uses `ast.parse()`. The blueprint format requires Tier 2 signatures to be "valid Python parseable by `ast`." All import extraction, dependency resolution, and validation assume Python imports.

**Environment manager: Conda only.** `conda create`, `conda run -n {env_name}`, `conda env remove` are hardcoded in Units 7, 10, and 24. The canonical interpreter invocation is `conda run -n {env_name} <command>`. Environment name derivation is hardcoded.

**Test framework: pytest only.** Test execution, output parsing, collection error detection, and framework installation are all pytest-specific.

**Package format: setuptools only.** `pyproject.toml` with `build-backend = "setuptools.build_meta"`, validated by `pip install -e .`.

**Version control: Git only.** All VCS operations use `git` commands with Conventional Commits by default.

**Delivery: Fixed README and directory structure.** README structure is determined by Mode A (self-build) or Mode B (general project) with fixed templates. Commit style, README audience, and documentation depth are not configurable.

### 1.2 The Stage 0 Setup Agent in SVP 1.2

The setup agent has a narrow mandate: domain description, `project_context.md` creation, optional GitHub MCP configuration. It does not ask about delivery preferences, toolchain choices, commit style, README structure, or test coverage expectations.

### 1.3 What SVP 1.2 Gets Right

The following are sound and must not be disrupted:

- The six-stage pipeline structure (Setup, Spec, Blueprint, Infrastructure, Verification, Delivery).
- The four-layer orchestration constraint architecture.
- The state machine, routing script, and deterministic gating logic.
- The fix ladder structures and three-hypothesis diagnostic discipline.
- The ledger-based multi-turn interaction pattern with structured response format.
- The hint forwarding mechanism.
- The universal write authorization system.
- The session cycling mechanism.
- The pass history and debug loop.
- The human gate vocabulary and status line contracts.
- The command Group A/B classification.
- The scripts synchronization rule and CLI wrapper contracts.
- The 24-unit decomposition, unit numbering, and dependency DAG.

### 1.4 What SVP 1.2 Gets Wrong (For the Purpose of Evolution)

These are not bugs — they are design choices appropriate for 1.2's scope.

1. **No separation between pipeline toolchain and delivery toolchain.** The pipeline's build tools (conda, pytest) are also the delivered project's tools. A human who wants their project's README to say "install with pyenv" has no mechanism to express that.

2. **No separation between pipeline logic and delivery preferences.** The git repo agent's README template, commit style, and documentation structure are baked into agent prompts.

3. **The setup agent does not capture delivery intent.** The human's preferences about how their project should look, feel, and be documented are never asked and never recorded.

### 1.5 Why SVP Uses Claude Code's Features the Way It Does

Claude Code offers skills, agents, commands, hooks, MCP servers, plugins, CLAUDE.md, `.claude/rules/`, and the built-in tool set. SVP uses a deliberately narrow subset.

**One skill, not many.** The main session has a single job: execute the six-step action cycle mechanically. Skills load on demand based on description matching — Claude decides when a skill is relevant. This is the opposite of what SVP needs. Each additional skill would be another probabilistic loading decision. The orchestration skill exists as belt-and-suspenders reinforcement of CLAUDE.md.

**Subagents for all substantive work.** Every task requiring judgment is delegated via the Task tool. Subagents provide context isolation (clean context window), tool restriction (defense in depth), and terminal status lines (machine-parseable output). The hard platform constraint that subagents cannot spawn further subagents is why the main session orchestrates all invocations.

**Hooks for enforcement, not orchestration.** Two hooks: write authorization and non-SVP session protection. Hooks cannot inject structured action blocks, present gates, or control agent invocation sequences. SVP does not use prompt-type hooks (non-deterministic) or HTTP hooks (external dependency).

**Commands split into Group A and Group B.** Group A (save, quit, status, clean) run deterministic scripts. Group B (help, hint, ref, redo, bug) spawn subagents. Confusing these groups was the most costly bug in SVP 1.1.

**CLAUDE.md for session-level identity.** Sets the frame; the REMINDER block maintains it. Detailed instructions live in agent definitions, the routing script, and the state machine.

**`.claude/rules/` not used.** SVP's behavioral instructions are monolithic and unconditional. Path-scoped rules would fragment the orchestration protocol.

**MCP for optional external access only.** GitHub read access and web search. Never for core pipeline operations.

**Plugin structure for distribution, not runtime behavior.** The launcher copies scripts to workspace-local paths so runtime execution is independent of the plugin installation path.

### 1.6 SVP 1.2 Bug Fixes and Regression Tests

SVP 1.2 carries two categories of bug-related tests. Both must be preserved in SVP 2.0.

**Category 1: Blueprint-era fixes (validated by unit tests in the regular test suite).**

These were identified during SVP 1.2 design and fixed in the blueprint before delivery:

1. **Bug 1 (Gate status string mismatch):** Routing loops from unrecognized status strings. Fixed by canonical gate vocabulary as data constant.
2. **Bug 2 (Hook permission freeze after Stage 5):** Debug write permissions not activated. Fixed by `debug_session.authorized` field.
3. **SVP 1.1 Hardening — `SVP_PLUGIN_ACTIVE`:** Canonical env var shared between hooks and launcher.
4. **SVP 1.1 Hardening — `--dangerously-skip-permissions`:** Controlled by config key.
5. **SVP 1.1 Hardening — Command Group A/B:** Enforced prohibition of Group B `cmd_*.py` scripts.

These are validated by assertions within the regular unit test suites, not by separate regression test files.

**Category 2: Post-delivery bugs (validated by regression tests in `tests/regressions/`).**

These were discovered during post-delivery use via Gate 6 and fixed through the debug loop. Each has a dedicated regression test file:

6. **Bug 2 — Wrapper drift** (`test_bug2_wrapper_delegation.py`): CLI wrappers reimplemented logic instead of delegating to canonical modules, causing sync drift. Tests structurally verify delegation via AST inspection.
7. **Bug 3 — CLI argument mismatch** (`test_bug3_cli_argument_contracts.py`): Routing generated flags that consuming scripts didn't accept. Tests verify all generated flags are accepted by their consumers.
8. **Bug 4 — Status line vocabulary** (`test_bug4_status_line_contracts.py`): Run-command scripts emitted custom status strings not in `COMMAND_STATUS_PATTERNS`. Tests verify only approved vocabulary is emitted.
9. **Bug 5 — Framework deps missing** (`test_bug5_pytest_framework_deps.py`): pytest and pytest-cov not installed in conda environment. Tests verify unconditional installation.
10. **Bug 6 — Collection error misclassification** (`test_bug6_collection_error_classification.py`): Fixture `NotImplementedError` errors (expected during red runs) classified as collection errors. Tests verify classification precision.
11. **Bug 7 — Stale status file** (`test_bug7_unit_completion_status_file.py`): Unit completion read stale status from previous phase. Tests verify `COMMAND_SUCCEEDED` is written before dispatch reads.
12. **Bug 8 — Sub-stage not reset** (`test_bug8_sub_stage_reset_on_completion.py`): Next unit inherited `sub_stage="unit_completion"` and was completed without building. Tests verify sub-stage, fix ladder, and retry counters reset on completion.
13. **Bug 9 — Hook path resolution** (`test_bug9_hook_path_resolution.py`): Hook commands used bare `scripts/` paths instead of `.claude/scripts/`, causing silent 127 exits. Tests verify correct paths in content, schema, and copy logic.
14. **Bug 10 — Agent status line exact matching** (`test_bug10_agent_status_prefix_matching.py`): `dispatch_agent_status` used exact string matching for agent status lines, but agents may append trailing context to their terminal status (e.g., `TEST_GENERATION_COMPLETE: 45 tests`). `dispatch_command_status` already used prefix matching via `startswith()`. Tests verify `dispatch_agent_status` also uses prefix matching, consistent with command status validation.

**Regression test preservation requirement.** SVP 2.0 must preserve all tests from both categories. Assertions may be updated for signature changes (e.g., functions gaining a parameter for the toolchain reader); bug scenarios must remain covered. No test may be deleted without a replacement covering the identical failure mode. The detailed per-test compatibility notes are in `references/regression_test_descriptions.md`.

### 1.7 Known SVP 1.2.1 Build Tool Limitation

The SVP 1.2.1 routing script generates a `--revision-mode` flag for `prepare_task.py`, but `prepare_task.py` does not accept this flag, causing a command failure (exit code 2). SVP 2.0's routing script and preparation script must handle revision mode properly -- the routing script must only generate flags that the preparation script accepts.

---

# PART II — WHAT WE WANT TO OBTAIN

---

## 2. SVP 2.0 Purpose and Scope

SVP 2.0 retains the full purpose and scope of SVP 1.2. All behavioral contracts from v6.0 not explicitly modified below remain in force.

SVP 2.0 is the terminal feature release of the SVP product line. The pipeline architecture — stages, gates, fix ladders, verification cycle, state machine, orchestration protocol — is complete. Future 2.x releases expand the delivery surface (more Tier B options) without changing the pipeline.

SVP 2.0 adds two capabilities:

1. **Project Profile (`project_profile.json`):** A structured configuration file capturing the human's delivery preferences, produced by an expanded setup agent through Socratic dialog.

2. **Pipeline Toolchain Abstraction (`toolchain.json`):** A data-driven indirection layer that moves SVP's own build commands from hardcoded strings to a configuration file. This is a code quality improvement — it does not enable different pipeline toolchains.

SVP 2.0 also introduces a clean separation between the **pipeline toolchain** (how SVP builds and tests — always Python/Conda/pytest) and the **delivery toolchain** (how the delivered project presents itself to its end user — configurable through the profile).

### 2.1 The Pipeline/Delivery Split

SVP always builds with Conda, always tests with pytest, always packages with setuptools. This is the pipeline toolchain. It is fixed for the entire 2.x line.

The delivered project may present itself differently. The human may want their README to say "install with pyenv" or "install with Poetry." The human may want `requirements.txt` instead of `environment.yml`. The human may want their project structured as a flat package instead of `src/unit_N/`. These are delivery preferences — they affect what the git repo agent produces in Stage 5, not how the pipeline builds and verifies in Stages 3-4.

The pipeline builds and tests the project using its own toolchain. Stage 5 repackages the verified artifacts according to the human's delivery preferences. The manual test at Gate 5.1 — where the human runs tests in the delivered repository — verifies that the repackaging preserved correctness.

### 2.2 Language and Environment Constraints

Same as v6.0 Section 1.2. All generated code remains Python. Pipeline tool commands are read from `toolchain.json` rather than hardcoded, but the commands themselves are identical to SVP 1.2.

### 2.3 Delivery Form

Same as v6.0 Section 1.4, with this addition: SVP 2.0 ships with a `toolchain_defaults/python_conda_pytest.json` file containing the pipeline toolchain configuration.

---

## 3. Design Principles

All principles from v6.0 Section 3 remain in force. SVP 2.0 adds:

### 3.13 Explicit Delivery Intent

The human's preferences about how their project should be delivered are first-class inputs captured during setup. They are not inferred, not defaulted silently, and not hardcoded. The setup agent asks. The human answers. The answers are recorded in `project_profile.json`. Downstream agents read the profile and act accordingly.

### 3.14 Pipeline Toolchain as Data

SVP's own tool commands are read from `toolchain.json` rather than hardcoded. In SVP 2.0, the file contains exactly the Python/Conda/pytest/setuptools/Git commands that were previously hardcoded. The behavioral effect is identical. The structural effect is clean, testable, auditable separation of data from logic.

The toolchain file is not a plugin system, provider registry, or class hierarchy. It is a flat JSON file read with `json.load()`. No dynamic dispatch, no inheritance, no abstract base classes.

### 3.15 Three-Layer Preference Enforcement

The human's tool preferences must be respected by the delivered code. LLM agents may revert to training priors despite explicit instructions. SVP 2.0 enforces preferences through three layers:

**Layer 1 — Blueprint contracts.** The blueprint author translates profile tool preferences into explicit behavioral contracts in affected units. "All subprocess calls targeting the project environment must use `conda run -n {env_name}`." The test suite tests for compliance.

**Layer 2 — Blueprint checker validation.** The blueprint checker receives the project profile and verifies that every profile preference — including documentation, metadata, commit style, and delivery packaging, not just code-behavior preferences — is reflected as an explicit contract in at least one unit. Missing coverage is an alignment failure.

**Layer 3 — Delivery compliance scan.** A deterministic script reads the profile's tool preferences and scans delivered Python source files for banned patterns. The scan operates on the AST of delivered Python source files in `src/` and `tests/`. It inspects subprocess invocation calls (`subprocess.run`, `subprocess.call`, `subprocess.Popen`, `os.system`) for command strings containing tool names that violate the profile's pipeline toolchain constraints. It does not flag string literals in non-executable contexts (comments, docstrings, print statements). Profile says "conda, no bare pip" → scan for unguarded `pip` calls in subprocess invocations. This runs during Stage 5 structural validation.

If the implementation agent writes `pip install` despite the blueprint contract, tests catch it (Layer 1). If the blueprint omits the contract, the checker catches it (Layer 2). If both miss it, the scan catches it (Layer 3). No single layer is sufficient; the combination is.

---

## 4. Platform Constraints

Same as v6.0 Section 4. No changes.

---

## 5. Pipeline Overview

Same as v6.0 Section 5. Six stages unchanged. Post-Stage-5 debug loop unchanged.

---

## 6. Stage 0: Setup (CHANGED)

Stage 0 is the primary area of change. Launcher pre-flight and hook activation are unchanged. Project context creation is unchanged in scope. A new sub-stage for project profile creation is added.

Full Stage 0 sub-stage progression:

```
hook_activation → [Gate 0.1] → project_context → [Gate 0.2] → project_profile → [Gate 0.3] → Stage 1
```

### 6.1 Launcher Pre-Flight (Unchanged)

Same as v6.0 Section 6.1. All eight prerequisite checks identical.

### 6.2 Hook Activation (Unchanged)

Same as v6.0 Section 6.1. Gate 0.1: **HOOKS ACTIVATED** or **HOOKS FAILED**.

### 6.3 Setup Agent: Project Context (Unchanged)

Same as v6.0 Section 6.1 for project context creation. Gate 0.2: **CONTEXT APPROVED**, **CONTEXT REJECTED**, **CONTEXT NOT READY**. On approval, pipeline advances to `project_profile` sub-stage (not directly to Stage 1).

### 6.4 Setup Agent: Project Profile (NEW)

After project context approval, the setup agent conducts a second Socratic dialog to capture delivery preferences. Output: `project_profile.json`.

**Sub-stage:** `stage: "0", sub_stage: "project_profile"`.

**Interaction pattern:** Ledger-based multi-turn on the same ledger (`ledgers/setup_dialog.jsonl`), continuing from the project context conversation.

**Experience-aware dialog.** The setup agent is mindful that the human is a domain expert, not a software engineer. Every question is explained in plain language with examples. Every area offers a fast path: "I can use sensible defaults for version control. Would you like to accept them, or would you prefer to go through the options?" A human who accepts all defaults faces roughly five decisions (Python version, README audience, license, author name, "anything else you want to customize?"). A human with detailed requirements can dive into any area.

**Mode A awareness.** When the build type is Mode A (self-build), the setup agent pre-populates the profile with Mode A defaults: the 12-section README structure (Header, What it does, Who it's for, Installation, Configuration, Usage, Quick Tutorial, Examples, Project Structure, License, Contributing, Changelog), conventional commits, MIT license, `entry_points: true`, `source_layout: "conventional"`, `depth: "comprehensive"`, `audience: "developer"`. The human reviews and approves rather than answering from scratch. It only asks questions that are genuinely open even for a self-build -- license holder name, author name, author contact, and any preference that cannot be inferred from the build type.

**Dialog areas.** The setup agent covers four areas. Each area corresponds to a set of forking points from the comprehensive enumeration (see Section 18.3). The setup agent uses this enumeration as its knowledge base but does not expose F-numbers to the human.

**Area 1: Version Control Preferences.**
- Commit message style: Conventional Commits (default), free-form, or custom template. When "custom" is chosen, the human provides a `commit_template` — free-form text that may contain a pattern with placeholders (e.g., `[TICKET-{number}] {description}`), a prose description of the format, or an example commit message. The git repo agent interprets whatever form the human provides.
- Whether commit messages should reference issue numbers.
- Branch strategy: main-only (default) or other.
- Tagging convention: semantic versioning (default), calendar versioning, or none.
- Team-specific conventions (free-text).

**Area 2: README and Documentation Preferences.**
- Target audience: domain expert (default), developer, both, or custom description.
- Section list: the agent presents the default list (Header, What it does, Who it's for, Installation, Configuration, Usage, Quick Tutorial, Examples, Project Structure, License) and asks for additions, removals, or reordering.
- Documentation depth: minimal, standard (default), or comprehensive.
- Optional content: mathematical notation, glossary, data format descriptions, code examples. When `include_code_examples` is true, the agent asks a follow-up: what should the examples demonstrate? The answer populates `code_example_focus`. When `include_code_examples` is false, `code_example_focus` is null.
- Custom sections with human-provided descriptions.
- Docstring convention: Google style (default), NumPy style, or no preference.
- Citation file (`CITATION.cff`) for academic projects: yes or no.
- Contributing guide: yes or no.

**Cross-area dependency:** If `testing.readme_test_scenarios` is set to true in Area 3, the setup agent automatically adds a Testing section to `readme.sections` if one is not already present. The human does not need to add it manually in Area 2.

**Area 3: Test and Quality Preferences.**
- Coverage target: the agent explains code coverage and asks for a threshold (valid range: 0-100, or null for no explicit target). Default: no explicit target.
- Readable test names: yes (default) or no.
- Test scenarios mentioned in README: yes or no.

**Area 4: Licensing, Metadata, and Packaging.**
- License type: MIT (default), Apache 2.0, GPL v3, BSD 2-Clause (simplified), BSD 3-Clause (new), or other. One-sentence explanation of each.
- SPDX license headers: conditional follow-up when the chosen license type warrants it (e.g., Apache 2.0). Default: false for MIT/BSD. When true, the git repo agent adds SPDX license identifier comments to delivered source files. Populates `license.spdx_headers`.
- Copyright holder and year: "Who holds the copyright? (This might be your university or employer.)"
- Author name: "What name should appear as the package author?" (may differ from copyright holder for academic projects). Populates `license.author`.
- Author contact.
- Additional metadata, asked conditionally:
  - "Is this academic or research work that others might cite?" -- populates `additional_metadata.citation` (BibTeX or plain-text citation string).
  - "Is this funded by a grant or organization that should be acknowledged?" -- populates `additional_metadata.funding` (grant numbers, funding bodies, acknowledgment text).
  - "Are there other people or institutions you'd like to acknowledge?" -- populates `additional_metadata.acknowledgments` (contributors, institutions, other credits).
  - Unknown keys added by the human are preserved in the JSON; the git repo agent renders them as a generic key-value list in the README's metadata section.
- Entry points: "Does your project have a command-line tool that users run from the terminal? If so, I'll configure an entry point so they can run it by name after installation." Populates `delivery.entry_points`. If true, the git repo agent generates the `[project.scripts]` section in the delivered `pyproject.toml`.

**Citation file interaction.** When `readme.citation_file` is true and `additional_metadata.citation` is populated, the git repo agent uses the citation content for `CITATION.cff`. When `citation_file` is true but `citation` is null, the git repo agent constructs a citation from `license.holder`, the project name, and `license.year`.

**What the setup agent does NOT ask in SVP 2.0.** The following are pipeline-fixed (Tier A) and are not presented as choices:
- Programming language (Python only).
- Environment manager for the pipeline (Conda only).
- Test framework (pytest only).
- Package format for the pipeline build (setuptools only).
- Source layout during build (`src/unit_N/` — SVP-native).
- VCS system (Git only).

If the human asks about these, the agent explains they are fixed for the pipeline but the delivery can differ — "SVP builds with Conda, but your delivered project's README can recommend pyenv if you prefer."

**Tier C preferences.** If the human volunteers a preference that SVP 2.0 does not support (a Tier C item — see Section 18.3), the setup agent acknowledges the request, explains the limitation honestly, and tells the human it will not be tracked in the profile — they will need to handle it manually after delivery. Nothing is recorded in `project_profile.json` for Tier C items.

**What the setup agent DOES ask that affects delivery packaging.** These are the delivery-side choices where the pipeline tool and the delivered tool may differ:
- Delivered environment recommendation: conda (default, same as pipeline), pyenv, venv, Poetry, or "no environment instructions in README."
- Dependency specification in delivered repo: `environment.yml` (default if conda), `requirements.txt`, `pyproject.toml` dependencies section, or multiple formats.
- Delivered source layout: SVP-native `src/unit_N/` restructured into conventional `src/packagename/` layout (default), flat layout, or kept as-is.

**Output: `project_profile.json`.** Strongly-typed, flat JSON. Schema:

```
project_profile.json
├── pipeline_toolchain: "python_conda_pytest"  (fixed, informational)
├── python_version: string           // e.g. "3.11", used for {python_version} in toolchain templates
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
│   └── conventions_notes: string | null
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
│   ├── type: "MIT" | "Apache-2.0" | "GPL-3.0" | "BSD-2-Clause" | "BSD-3-Clause" | string
│   ├── holder: string              // copyright holder (may be organization)
│   ├── author: string              // package author name (may differ from holder)
│   ├── year: string
│   ├── contact: string | null
│   ├── spdx_headers: boolean
│   └── additional_metadata:
│       ├── citation: string | null       // BibTeX or plain-text citation for academic projects
│       ├── funding: string | null        // Grant numbers, funding bodies, acknowledgment text
│       ├── acknowledgments: string | null // Contributors, institutions, other credits
│       └── (additional free-form keys preserved, rendered generically)
├── fixed:
│   ├── language: "python"
│   ├── pipeline_environment: "conda"
│   ├── test_framework: "pytest"
│   ├── build_backend: "setuptools"
│   ├── vcs_system: "git"
│   └── source_layout_during_build: "svp_native"
└── created_at: ISO timestamp
```

The `fixed` section records Tier A values for transparency. The human sees "Pipeline: Python, Conda, pytest, setuptools, Git (fixed)" in the summary. No agent reads `fixed` at runtime — the pipeline reads `toolchain.json`.

**Schema constraint:** Every field has a defined default. The setup agent always writes a fully populated `project_profile.json` with every field explicitly present, including defaults accepted via fast-path. No downstream consumer needs a defaults table — every field is always present in the file.

**Contradiction detection.** The setup agent checks for known contradictory combinations during the dialog and asks the human to resolve them before writing the profile. Known contradictions include:

- `readme.depth: "minimal"` with more than 5 sections or any custom sections.
- `readme.include_code_examples: true` with `readme.depth: "minimal"`.
- `delivery.entry_points: true` with no identifiable CLI module in the stakeholder spec.
- `delivery.source_layout: "flat"` with more than approximately 10 units.
- `vcs.commit_style: "custom"` with `vcs.commit_template: null`.
- Mismatched delivery environment and dependency format (e.g., pyenv for environment with `environment.yml` as dependency format).

The list of known contradictions is a blueprint concern — the spec requires that obvious contradictions are caught but does not enumerate all possible combinations. Undetected contradictions that surface during later stages are handled by the normal alignment and redo mechanisms. The profile is not written until detected contradictions are resolved.

**Determinism constraint:** The setup agent records what the human said. It does not generate creative content for the profile.

**Immutability.** Once approved at Gate 0.3, `project_profile.json` is a blessed document. Changes require `/svp:redo` (see Section 12.1).

**Read-time validation.** Every script and agent that reads `project_profile.json` must validate the fields it uses against expected types before acting. Unknown fields are ignored (forward compatibility). Missing fields are filled from defaults. Type mismatches produce a clear error message.

**Integrity requirement.** If `project_profile.json` is missing or fails JSON parsing when a script or agent attempts to read it, the reader raises a `RuntimeError` with a message identifying the missing file and directing the human to resume from Stage 0 or re-run `/svp:redo`. This is a project integrity error. Scripts that read optional profile fields where the profile might not yet exist (such as during Stage 0 before Gate 0.3) must handle the missing-file case gracefully by using defaults.

**Gate 0.3 (project profile approval) (NEW).** The setup agent presents a formatted summary (not raw JSON). Gate response options: **PROFILE APPROVED**, **PROFILE REJECTED**. On rejection, the agent asks which areas need revision -- the human may specify multiple areas. The agent handles all specified areas in one pass, then re-presents the full summary once. There is no iteration limit on Gate 0.3 rejections -- the human can reject and revise as many times as needed. Unlike the alignment loop, Stage 0 setup has no bounded retry because the human is the sole author of their preferences.

### 6.5 Toolchain Configuration File (NEW)

On profile approval, the pipeline writes `toolchain.json` to the project root, copied from `toolchain_defaults/python_conda_pytest.json`. The `toolchain_defaults/` directory is a subdirectory of the plugin's `scripts/` directory; it contains `python_conda_pytest.json`. The launcher copies the file to the project root as `toolchain.json` during project creation. This is the pipeline's own toolchain — the commands SVP uses to build and test. It is never modified.

The file maps abstract operation names to concrete command templates:

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
│   └── pass_fail_pattern: "Parses pytest summary line. Extracts integer counts from patterns: '{N} passed', '{N} failed', '{N} error'. Returns (passed, failed, errors) tuple."
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
└── file_structure:
    ├── source_dir_pattern: "src/unit_{n}/"
    ├── test_dir_pattern: "tests/unit_{n}/"
    ├── source_extension: ".py"
    └── test_extension: ".py"
```

**Environment name derivation.** The `{env_name}` placeholder used in toolchain templates is resolved by a function in Unit 1 (foundational data contract) that reads `project_name` from the state file and applies a fixed rule: lowercase, spaces to underscores, hyphens to underscores. This derivation is not part of `toolchain.json` because it is not a command template — it is a data transformation that belongs in the data contract layer.

**Placeholder resolution.** Placeholder resolution is single-pass: the toolchain reader resolves `environment.run_prefix` first, then substitutes the resolved value into all templates that reference `{run_prefix}`. The `{python_version}` placeholder is resolved from the project profile's `python_version` field. The `{env_name}` placeholder is resolved from the environment name derivation function. No recursive or multi-level resolution. This is a blueprint constraint.

**Python version validation.** The toolchain reader validates that the resolved `{python_version}` satisfies the constraint in `toolchain.json` (`version_constraint: ">=3.10"`). If the human specifies a version that does not satisfy the constraint (e.g., `3.9`), the reader rejects it with a clear error at Pre-Stage-3.

**Behavioral equivalence.** Every resolved command must produce identical behavior to SVP 1.2's hardcoded commands. This is testable: compare fully resolved commands (after placeholder substitution with known test inputs) against the exact strings SVP 1.2 would have produced for the same inputs. The test compares post-substitution output, not templates.

**Integrity requirement.** If `toolchain.json` is missing or fails JSON parsing, the toolchain reader raises a `RuntimeError` with a message directing the human to re-run `svp new` or reinstall the plugin. This is a project integrity error, not a recoverable condition. No fallback to hardcoded values.

**Schema validation.** Profile and toolchain file validation uses JSON Schema or equivalent structural checking. The exact validation library is a blueprint concern. The spec requires that validation runs at read time, produces actionable error messages, and is deterministic (no LLM involvement).

**Human visibility.** The human never edits or sees `toolchain.json`. The pipeline toolchain is reflected in `project_profile.json`'s `fixed` section.

### 6.6 Directory Structure (Modified)

Same as v6.0 Section 6.2, with additions:

```
projectname/
|-- project_profile.json    <- delivery preferences (human-approved, Stage 0)  [NEW]
|-- toolchain.json           <- pipeline toolchain commands (from plugin)       [NEW]
|-- tests/
|   +-- regressions/         <- carry-forward regression tests from 1.2        [NEW]
|-- ... (all other paths unchanged)
```

**Carry-forward artifacts** placed at project creation:
- `tests/regressions/` — Regression test files from SVP 1.2 (see Section 16.2).
- `examples/game-of-life/` — Bundled example from v1.1.
- `doc/stakeholder.md` — Copy of the stakeholder specification used to produce the project.
- `doc/blueprint.md` — Copy of the technical blueprint used to produce the project.

### 6.7 Resume Mode, Optional Integrations, Scenarios

Resume mode: unchanged from v6.0 Section 6.1.
Optional integrations: unchanged.
Scenarios for Gates 0.1, 0.2, 0.3: see v6.0 for 0.1 and 0.2 baselines. Gate 0.3 best case: human accepts defaults, one interaction. Worst case: detailed requirements across multiple areas, several revision rounds.

---

## 7. Stages 1-2: Stakeholder Spec and Blueprint (CHANGED — Agent Context)

Behavioral flow unchanged from v6.0 Sections 7 and 8. All gates, dialogs, alignment loops, iteration limits identical.

What changes: the Blueprint Author Agent receives `project_profile.json` content (the `readme`, `vcs`, and `delivery` sections) as task prompt context. This allows the blueprint author to:

- Structure the delivery unit with awareness of the human's README preferences and source layout choice.
- Encode tool preferences as explicit behavioral contracts in affected units (Layer 1 of preference enforcement).
- Include commit style in the git repo agent's behavioral contract.

**Constraint:** The profile is context, not instruction override. Discrepancies between profile and spec are surfaced through normal alignment.

**Profile preferences reassessable during Socratic dialog.** If the human's requirements reveal a mismatch with their profile choices — for example, "I need Bioconductor packages" when they chose pyenv for delivery — the stakeholder dialog agent or blueprint author agent surfaces the issue. The human can invoke `/svp:redo` to revise the profile.

**Blueprint checker profile validation (Layer 2).** The blueprint checker receives the project profile in addition to the spec and blueprint. It verifies that every profile preference — including documentation, metadata, commit style, and delivery packaging, not just code-behavior preferences — is reflected as an explicit contract in at least one unit. A profile that says "conda, no bare pip" with no unit mentioning conda usage is an alignment failure. A profile that says "comprehensive README for developers" with no unit contract specifying audience and depth is also an alignment failure.

---

## 8. Pre-Stage-3: Infrastructure Setup (CHANGED — Command Source)

Behavioral flow unchanged from v6.0 Section 9. Same outcomes.

Scripts read tool commands from `toolchain.json` instead of hardcoding them: `environment.create`, `environment.run_prefix`, `environment.install`, `testing.framework_packages`. Behavioral equivalence required.

Pre-Stage-3 infrastructure setup always creates the Conda environment from scratch, regardless of whether an environment from a prior pass exists. If a prior environment exists with the same name, it is replaced. This ensures that Python version changes, dependency changes, or blueprint revisions that alter the extracted imports always produce a fresh, consistent environment.

---

## 9. Stage 3: Unit-by-Unit Verification (CHANGED — Command Source and Agent Context)

Behavioral flow unchanged from v6.0 Section 10. Red-green cycle, fix ladders, diagnostic escalation, coverage review, unit completion — all identical.

Changes:
1. Test execution commands resolved from `toolchain.json`.
2. Collection error indicators read from `toolchain.json`.
3. Test agent receives `testing.readable_test_names` from profile.
4. Agent definition files retain toolchain-specific terms ("pytest", "Python implementation"). Not parameterized in SVP 2.0.

Test and implementation agents receive only their specific profile fields, not the full profile.

---

## 10. Stage 4: Integration Testing (CHANGED — Command Source and Coverage Requirement)

Behavioral flow unchanged from v6.0 Section 11. Test commands resolved from `toolchain.json`.

**New: SVP 2.0 integration test coverage requirement.** The integration test author must cover all new cross-unit paths introduced by SVP 2.0:

1. **Toolchain resolution chain:** Profile → `toolchain.json` → reader → resolved command. Verify fully resolved commands (after placeholder substitution with known test inputs) match the exact strings SVP 1.2 would have produced for the same inputs.
2. **Profile flow through preparation script:** Verify correct profile sections reach correct agents (git repo agent gets full profile, test agent gets only `readable_test_names`).
3. **Blueprint checker profile validation:** Verify alignment failure when blueprint omits a profile-mandated constraint.
4. **Redo agent profile classification:** Verify `profile_delivery` for delivery-only changes, `profile_blueprint` for blueprint-influencing changes.
5. **Gate 0.3 dispatch:** Verify state transitions for `PROFILE APPROVED` and `PROFILE REJECTED`.
6. **Preference compliance scan:** Verify detection of banned patterns in synthetic delivered code.
7. **Write authorization for new paths:** Verify `project_profile.json` writable during Stage 0 `project_profile` sub-stage and during `redo_profile_delivery` / `redo_profile_blueprint` sub-stages, and blocked otherwise. Verify `toolchain.json` always blocked.
8. **Redo-triggered profile revision state transitions:** Verify that `redo_profile_delivery` returns to the triggering stage after approval, and `redo_profile_blueprint` restarts from Stage 2 after approval. Verify mini-Gate 0.3r dispatch.

These tests exercise deterministic script behavior. They do not require LLM involvement. They must be covered at Stage 4 so that no post-delivery regression test is needed for SVP 2.0 architectural changes.

---

## 11. Stage 5: Repository Delivery (CHANGED — Profile-Driven Delivery)

Behavioral flow unchanged from v6.0 Section 12 for assembly, structural validation, bounded fix cycle, and workspace cleanup.

### 11.1 Delivery Compliance Scan (NEW -- Layer 3)

During Stage 5 structural validation (before the human tests the repo), a deterministic script reads the `delivery` section of `project_profile.json` and scans delivered Python source files for preference violations. The scan is always driven by the delivery preferences -- it reads `delivery.environment_recommendation`, not the pipeline's `fixed` section. When the human keeps the default (delivery = same as pipeline, i.e. conda), the scan enforces the same constraints as the pipeline would -- no regressions are allowed to surface through this mechanism.

**Scan scope and mechanism.** The scan covers Python source files in the delivered `src/` and `tests/` directories. Documentation files, configuration files, and scripts intended for end users are not scanned -- they correctly reference the delivery toolchain, not the pipeline toolchain. The scan operates on the AST of delivered Python source files. It inspects subprocess invocation calls (`subprocess.run`, `subprocess.call`, `subprocess.Popen`, `os.system`) for command strings containing tool names that violate the profile's delivery toolchain constraints. It does not flag string literals in non-executable contexts (comments, docstrings, print statements, variable assignments). The compliance scan is limited to subprocess calls with literal string or f-string command arguments. Variable-constructed commands, commands built by function calls, and commands assembled through string concatenation across multiple statements are not analyzed. This is an acknowledged limitation — the scan is Layer 3 (last resort), not Layer 1 (primary enforcement). Layers 1 and 2 (blueprint contracts and checker validation) are the primary mechanisms. The scan catches the common case where an LLM agent writes `subprocess.run(['pip', 'install', ...])` from training priors. The exact detection patterns are a blueprint concern.

**Banned pattern sets by delivery environment recommendation:**

- **conda** (default, same as pipeline): Scan delivered source files for subprocess calls containing `pip`, `python`, or `pytest` as bare tokens not preceded by `conda run -n`.
- **pyenv**: Scan delivered source files for subprocess calls containing `conda` commands.
- **venv**: Scan delivered source files for subprocess calls containing `conda` commands.
- **poetry**: Scan delivered source files for subprocess calls containing `conda` commands or bare `pip install` calls.
- **none** (no environment instructions): When `delivery.environment_recommendation` is `none`, the compliance scan skips delivery artifact checks (README, install scripts) and only scans source files. The source file scan checks that no subprocess calls contain environment manager commands (`conda`, `pyenv`, `venv`, `poetry`).

Violations enter the bounded fix cycle (same as structural validation failures).

### 11.2 Commit Message Style

The git repo agent reads `vcs.commit_style` from `project_profile.json`. Conventional (default), freeform, or custom template.

### 11.3 README Generation

The git repo agent reads the `readme` and `delivery` sections from `project_profile.json`:

- Section structure from `readme.sections`.
- Custom sections from `readme.custom_sections`.
- Audience and depth from `readme.audience` and `readme.depth`.
- Optional content from boolean flags.
- Installation instructions match `delivery.environment_recommendation`, not the pipeline toolchain.

Mode A (SVP self-build): carry-forward artifact, profile captures the 12-section structure explicitly.
Mode B (general project): generated from profile preferences.

### 11.4 Delivered Source Layout

The git repo agent reads `delivery.source_layout`:
- `"conventional"`: restructures `src/unit_N/` into `src/packagename/` with proper `__init__.py` hierarchy.
- `"flat"`: package at repository root.
- `"svp_native"`: keeps the `src/unit_N/` structure as-is.

**Restructuring precondition for "conventional" layout.** The blueprint author must ensure no module name collisions across units. During the pipeline build, modules in different units occupy separate directories (`src/unit_3/utils.py` and `src/unit_7/utils.py`), so no collision occurs. But merging into `src/packagename/` would create a collision. This is a blueprint constraint -- the blueprint author is responsible for unique module names across the full unit set when `delivery.source_layout` is "conventional."

**Module collision detection at assembly time.** When `delivery.source_layout` is `conventional`, the git repo agent must detect module name collisions during restructuring and report them as assembly errors. If two units both define a module with the same name, the agent cannot flatten them into the same directory without overwriting. Collisions enter the bounded fix cycle as assembly errors.

### 11.5 Delivered Dependency Format

The git repo agent reads `delivery.dependency_format` and generates the appropriate files: `environment.yml`, `requirements.txt`, `pyproject.toml` dependencies, or multiple formats. When multiple formats are specified (list value), the first in the list is the primary recommendation in the README. All formats are generated.

### 11.6 Entry Points

If `delivery.entry_points` is true, the git repo agent generates the `[project.scripts]` entry point section in the delivered `pyproject.toml`. The git repo agent must compute entry point module paths based on `delivery.source_layout`. The path format differs by layout: `conventional` uses `src.packagename.module:func`, `flat` uses `packagename.module:func`, `svp_native` uses the original SVP path. For the SVP self-build (Mode A), `entry_points: true` is correct -- the `svp` CLI launcher is an entry point.

### 11.7 SPDX License Headers

If `license.spdx_headers` is true, the git repo agent adds SPDX license identifier comments to the top of all delivered source files.

### 11.8 Additional Metadata in Delivery

The git repo agent acts on `license.additional_metadata` keys specifically:
- `citation`: content goes into a "How to Cite" README section and into `CITATION.cff` if `readme.citation_file` is true.
- `funding`: content goes into an "Acknowledgments" README section.
- `acknowledgments`: content goes alongside funding in the "Acknowledgments" section.
- Unknown keys: preserved in the JSON and rendered as a generic key-value list in the README's metadata section.

### 11.9 Delivered Repository Gitignore

The git repo agent must include a `.gitignore` in the delivered repository that excludes Python build artifacts (`__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `*.pyc`, `dist/`, `build/`).

### 11.10 Build Artifacts in Delivered Repository

`toolchain.json` and `project_profile.json` are pipeline-internal artifacts. They do not appear in the delivered repository. The git repo agent excludes them during Stage 5 assembly.

### 11.11 Documentation Artifacts in Delivered Repository

The delivered repository includes a `doc/` directory containing:
- `doc/stakeholder.md` — Copy of the stakeholder specification (`specs/stakeholder.md`).
- `doc/blueprint.md` — Copy of the technical blueprint (`blueprint/blueprint.md`).

These are copied verbatim during Stage 5 assembly so that end users can reference the specification and design that produced the project.

### 11.12 Bundled Example, Post-Delivery, Debug Loop

Example project: carried forward unchanged. Debug loop: unchanged from v6.0.

---

## 12. Human Commands (CHANGED)

All commands from v6.0 Section 13 remain identical in behavior, grouping, and execution. Group A/B classification unchanged.

### 12.1 `/svp:redo` Profile Support (NEW)

The redo agent gains a fourth classification level for profile issues. When the human invokes `/svp:redo` describing a delivery preference problem, the redo agent classifies:

- **`REDO_CLASSIFIED: profile_delivery`** -- The issue affects only Stage 5 delivery. No blueprint contract changes. Examples: `vcs.commit_style`, `license.type`, `readme.audience`, `readme.depth`, `delivery.environment_recommendation`, `license.spdx_headers`, `license.additional_metadata`. The profile is revised through a focused dialog (the setup agent in targeted revision mode reopens only the affected area). No pipeline restart. The change takes effect when Stage 5 runs.

- **`REDO_CLASSIFIED: profile_blueprint`** -- The issue affects blueprint contracts. Examples: `readme.sections`, `readme.custom_sections` (the blueprint author encodes contracts about README section structure in the delivery unit), `testing.coverage_target` (the blueprint references the target), `delivery.source_layout` (affects how the blueprint author structures units and module naming — a change from `svp_native` to `conventional` triggers restart from Stage 2; the new blueprint is written with awareness of the layout and the blueprint checker validates module name uniqueness). The profile is revised, then the pipeline restarts from Stage 2. Ruthless restart of everything downstream.

The existing classifications (`REDO_CLASSIFIED: spec`, `REDO_CLASSIFIED: blueprint`, `REDO_CLASSIFIED: gate`) are unchanged.

The setup agent is never re-entered for a full Stage 0 re-run. The redo-triggered profile revision uses the setup agent in targeted revision mode -- the human makes the specific change, approves, and the pipeline continues or restarts as classified.

**State machine for redo-triggered profile revision.** When `/svp:redo` produces a `profile_delivery` or `profile_blueprint` classification, the pipeline writes a new sub-stage to `pipeline_state.json` within the current stage:

- `"redo_profile_delivery"` -- for delivery-only profile changes.
- `"redo_profile_blueprint"` -- for blueprint-influencing profile changes.

The state file also records `redo_triggered_from` as a snapshot dict capturing the full pipeline position at the time of the redo:

```
"redo_triggered_from": {
    "stage": "3",
    "sub_stage": "diagnostic_impl",
    "current_unit": 4,
    "fix_ladder_position": "diagnostic",
    "red_run_retries": 1
}
```

This snapshot includes fix ladder state, retry counters, and the current unit so the routing script can restore the exact position after a `profile_delivery` revision completes. On `profile_delivery` completion, the routing script restores this snapshot — fix ladder state is preserved, and the pipeline completes the current fix ladder after returning. The delivery change takes effect at Stage 5. On `profile_blueprint` completion, the snapshot is discarded — `restart_from_stage` resets everything downstream including fix ladder, red run retries, current unit, and verified units.

The routing script sees the redo sub-stage and emits an `invoke_agent` action for the setup agent with the redo context. This is analogous to how the existing redo mechanism works for spec revisions -- the pipeline pauses at its current position, runs a focused revision dialog, then either resumes or restarts.

**Targeted revision mode.** The setup agent in targeted revision mode receives: (1) the current `project_profile.json`, (2) the redo agent's classification indicating which area is affected and why, and (3) a "revision mode" flag in its system prompt that suppresses the full four-area dialog flow. The agent reopens only the affected dialog area, modifies the affected fields, and presents the changes. This is analogous to the stakeholder dialog agent's existing revision mode (v6.0 Section 7.6) -- same concept, applied to the setup agent.

**Mini-Gate 0.3 for profile revision.** After the targeted revision dialog, the setup agent presents the modified profile summary showing what changed (highlighted against the previous version). The human approves or rejects using the same vocabulary: **PROFILE APPROVED**, **PROFILE REJECTED**. On rejection, the revision dialog continues. On approval, the pipeline resumes at the triggering stage (for `profile_delivery`) or restarts from Stage 2 (for `profile_blueprint`). The gate ID is `gate_0_3r_profile_revision` to distinguish it from the original `gate_0_3_profile_approval`.

### 12.2 `/svp:status` (Modified Output)

The status report includes the pipeline toolchain and a one-line profile summary:

```
Project: Spike Sorting Pipeline
Pipeline: python_conda_pytest
Delivery: pyenv, conventional commits, comprehensive README, MIT
Current: Stage 3, Unit 2 of 11 (pass 2)
Pass 1: Reached Unit 7, spec revision triggered
Pass 2: In progress, Unit 1 verified
```

---

## 13. Agent Summary (MODIFIED)

Agent table from v6.0 Section 21 unchanged in structure. Additional context for SVP 2.0:

| Agent | Additional Context in 2.0 |
|---|---|
| Setup Agent | Expanded dialog: project profile creation after project context. Targeted revision mode for redo-triggered profile changes (receives current profile, redo classification, revision-mode flag). |
| Blueprint Author Agent | `project_profile.json` (readme, vcs, delivery sections) |
| Blueprint Checker Agent | `project_profile.json` (for full preference coverage validation — all profile preferences, not just code-behavior — Layer 2) |
| Git Repo Agent | `project_profile.json` (full profile) |
| Test Agent | `project_profile.testing.readable_test_names` flag |
| Redo Agent | New classifications: `profile_delivery`, `profile_blueprint` |

---

## 14. Configuration (MODIFIED)

### 14.1 SVP Configuration File

Unchanged from v6.0 Section 22.1.

### 14.2 Project Profile File (NEW)

Produced during Stage 0. Schema in Section 6.4. Immutable after Gate 0.3. Changes via `/svp:redo`.

### 14.3 Toolchain File (NEW)

Copied from plugin at project creation. Schema in Section 6.5. Permanently read-only.

### 14.4 Pipeline State

Same as v6.0 Section 22.2. Stage 0 sub-stages: `"hook_activation"` -> `"project_context"` -> `"project_profile"`.

**Redo-triggered profile revision sub-stages (NEW).** Two additional sub-stages may appear within any stage when a redo triggers profile revision:

- `"redo_profile_delivery"` -- setup agent targeted revision, delivery-only change.
- `"redo_profile_blueprint"` -- setup agent targeted revision, blueprint-influencing change.

When either sub-stage is active, the state file also contains a `redo_triggered_from` snapshot dict (see Section 12.1 for schema) recording the full pipeline position at the time of the redo, including fix ladder state and retry counters, so the routing script can restore the exact position after a `profile_delivery` revision completes.

### 14.5 Gate Vocabulary Additions

| Gate | ID | Valid Status Strings |
|---|---|---|
| 0.3 | gate_0_3_profile_approval | PROFILE APPROVED, PROFILE REJECTED |
| 0.3r | gate_0_3r_profile_revision | PROFILE APPROVED, PROFILE REJECTED |

Redo agent status line additions: `REDO_CLASSIFIED: profile_delivery`, `REDO_CLASSIFIED: profile_blueprint`.

### 14.6 Resume Behavior

Same as v6.0 Section 22.3, plus pipeline toolchain and profile summary in context summary.

---

## 15. Universal Write Authorization (MODIFIED)

Same as v6.0 Section 19, with additions:

- `project_profile.json`: writable during Stage 0 `project_profile` sub-stage and during any active redo-triggered profile revision (sub-stage is `redo_profile_delivery` or `redo_profile_blueprint`, regardless of the current pipeline stage). Read-only otherwise. The write authorization hook checks the sub-stage field in `pipeline_state.json` to detect an active revision.
- `toolchain.json`: permanently read-only after creation. No agent, session, or command may modify it.

---

## 16. Unit Structure Preservation

### 16.1 Unit Numbering

SVP 2.0 preserves the 24-unit structure, dependency DAG, and topological ordering from SVP 1.2. Units may be expanded (additional parameters, broader scope). Adding or renumbering units only when clearly justified.

### 16.2 Regression Test Preservation

All eight regression test files from SVP 1.2's `tests/regressions/` are carry-forward workspace artifacts placed at project creation:

- `test_bug2_wrapper_delegation.py`
- `test_bug3_cli_argument_contracts.py`
- `test_bug4_status_line_contracts.py`
- `test_bug5_pytest_framework_deps.py`
- `test_bug6_collection_error_classification.py`
- `test_bug7_unit_completion_status_file.py`
- `test_bug8_sub_stage_reset_on_completion.py`
- `test_bug9_hook_path_resolution.py`
- `test_bug10_agent_status_prefix_matching.py`

Test assertions may be updated for signature changes (e.g., functions gaining a toolchain reader parameter, `PipelineState` gaining new required fields); bug scenarios must remain covered. The detailed per-test compatibility notes in `references/regression_test_descriptions.md` identify exactly which assertions are sensitive to SVP 2.0 changes and why.

The five blueprint-era fixes (Section 1.6, Category 1) are validated by the regular unit test suites and are similarly preserved.

The integration test suite (Section 10) covers all new SVP 2.0 architectural paths, so no new post-delivery regression tests should be needed for 2.0 changes.

---

## 17. All Unchanged Sections (By Reference)

The following v6.0 sections are incorporated by reference:

- Section 2 (purpose and scope baseline)
- Sections 3.1-3.12 (design principles baseline)
- Section 4 (platform constraints)
- Section 5.1 (pipeline overview)
- Section 7 (stakeholder spec stage -- behavioral flow)
- Section 8 (blueprint stage -- behavioral flow)
- Sections 10.1-10.11 (unit-by-unit verification -- behavioral flow)
- Section 11 (integration testing -- behavioral flow)
- Sections 12.1-12.9 (repository delivery -- behavioral flow)
- Section 13 (human commands -- except changes in this spec's Section 12)
- Section 14 (agent definitions)
- Section 15 (session management)
- Section 16 (error handling)
- Section 17 (debug loop)
- Section 18 (gate vocabulary -- base vocabulary)
- Sections 19.1-19.3 (write authorization -- base rules)
- Section 20 (state machine)
- Section 23 (plugin structure)
- Section 24 (launcher)
- Section 25 (CLI wrappers)
- Section 26 (scripts synchronization)
- Section 28 (glossary)

---

# PART III — HOW WE GET THERE

---

## 18. Architectural Strategy

### 18.1 The Two-File Architecture

1. **`project_profile.json`** — Human-facing. Delivery preferences. Agents read it via task prompts. Immutable after Gate 0.3.
2. **`toolchain.json`** — Pipeline-facing. Build commands. Scripts read it at runtime. Never modified.

The profile says how the delivered project should look. The toolchain file says how SVP builds and tests. They serve different consumers and change at different rates.

### 18.2 Blueprint Author Guidance

**Unit 1 (scope grows):** Add `toolchain.json` loader and `project_profile.json` loader alongside `svp_config.json`. Three schemas, three loaders, three validators. Natural home: foundational data contract with no upstream dependencies.

**Units 7, 10, 11:** Replace hardcoded commands with toolchain reader calls.

**Unit 9 (preparation script):** Extract profile sections for agent task prompts. Git repo agent gets full profile. Test agent gets only `readable_test_names`. Blueprint checker gets profile for Layer 2 validation.

**Unit 12 (hooks):** Add write authorization for `project_profile.json` and `toolchain.json`.

**Unit 13 (setup agent):** Expand for project profile dialog and Gate 0.3. Add targeted revision mode for redo-triggered profile changes.

**Unit 14 (blueprint checker):** Add Layer 2 preference coverage validation.

**Unit 16 (redo agent):** Add `profile_delivery` and `profile_blueprint` classifications.

**Unit 18 (git repo agent):** Read profile for commit style, README structure, source layout, dependency format, entry points, SPDX headers, additional metadata, all delivery preferences. Add delivery compliance scan (Layer 3). When `delivery.source_layout` is "conventional," the blueprint author must ensure no module name collisions across units (see Section 11.4).

**Unit 23 (plugin manifest):** Add `toolchain_defaults/` directory.

**Unit 24 (launcher):** Copy toolchain file during project creation.

### 18.3 Forking Point Enumeration

The comprehensive enumeration of all setup decisions for a generic Python project (the F1-F10 catalog) ships as part of the setup agent's knowledge base. It is a reference document within the plugin — the setup agent consults it to ensure comprehensive coverage during dialog.

The enumeration is classified into tiers:
- **Tier A (pipeline-fixed):** Recorded in the `fixed` section of the profile. Not presented as choices. F2.1 (conda), F3.1 (SVP-native layout during build), F7.1 (pytest), F8.1 (setuptools).
- **Tier B (delivery-configurable in 2.0):** The four dialog areas. Captured in the profile body. Acted on by the git repo agent.
- **Tier C (recognized, not implemented):** If the human asks, the setup agent acknowledges the request, explains the limitation honestly, and tells the human it will not be tracked — they will need to handle it manually after delivery. Nothing is recorded in the profile. Candidates for SVP 2.1+.

### 18.4 What the Blueprint Author Must NOT Do

- Build provider interfaces, abstract base classes, or dynamic dispatch.
- Make `toolchain.json` user-editable.
- Parameterize agent definition files with toolchain variables.
- Add a language or toolchain selection dialog.
- Break behavioral equivalence.

### 18.5 Self-Hosting Invariant

SVP is a Python application. It will always be a Python application. The `toolchain.json` and `project_profile.json` govern the target project. SVP's own build toolchain is always `python_conda_pytest`. The abstraction layer sits between SVP and the projects it builds, not between SVP and itself.

---

## 19. Product Roadmap

SVP 2.0 is the terminal feature release of the SVP product line. The pipeline architecture is complete. Future development takes two forms:

### 19.1 The SVP 2.x Line

SVP 2.1, 2.2, etc. are maintenance releases that expand the delivery surface:
- Promote Tier C forking points to Tier B (CI templates, linter scaffolding, citation files, code of conduct, experiment tracking).
- Widen what the git repo agent can produce.
- Add new questions to the setup agent dialog.
- No pipeline changes, no new stages, no new agents.

### 19.2 Language-Directed Variants

Language support is delivered as separate products — each one a Python project built by SVP 2.0:

```
SVP 2.0  ──builds──>  SVP-R       (targets R projects: renv, testthat, roxygen2)
SVP 2.0  ──builds──>  SVP-elisp   (targets Emacs Lisp: Cask, ERT)
SVP 2.0  ──builds──>  SVP-bash    (targets bash: shunit2 or bats)
```

Each variant is a complete standalone Claude Code plugin. It shares SVP's pipeline architecture (stages, gates, fix ladders, state machine, orchestration protocol) but implements language-specific tooling: parsers, stub generators, test output readers, environment management, and agent prompts.

Each variant is a Python project containing Python code that manipulates artifacts in the target language. SVP 2.0 builds it without any language extensions.

**Why not SVP 3.0?** SVP 2.0's pipeline is language-agnostic in its architecture — the stages, gates, and verification cycle work for any language. What's language-specific is the tooling: how signatures are parsed, how stubs are generated, how tests are run, how output is parsed. Building separate products lets each variant design its tooling for its specific language without compromises. It also means each variant can evolve independently.

### 19.3 The Build Chain

Every link in the chain is a Python project built by SVP:

```
SVP 1.2.1  ──builds──>  SVP 2.0
SVP 2.0    ──builds──>  SVP-R, SVP-elisp, SVP-bash  (in parallel, independently)
```

No manual bootstrap at any step. No version of SVP ever needs to build a non-Python project.

---

## 20. Implementation Note

This spec is built using SVP 1.2.1. Blueprint must fit within context budget. Primary risk: blueprint size from expanded setup agent and profile-driven delivery. Blueprint author should fold new functionality into existing units per Section 16.1.

Bundled example (Game of Life): carried forward unchanged. Prompt caching: out of scope.

---

## 21. Glossary Additions

- **Project Profile (`project_profile.json`):** Structured JSON capturing delivery preferences. Human-approved at Gate 0.3. Immutable after approval.

- **Toolchain File (`toolchain.json`):** Pipeline-internal JSON mapping operations to command templates. Copied from plugin defaults. Permanently read-only.

- **Pipeline Toolchain:** The tools SVP uses to build and test: Conda, pytest, setuptools, Git. Fixed for the 2.x line. Distinct from the delivery toolchain.

- **Delivery Toolchain:** The tools the delivered project presents to its end user. Configurable through the profile. May differ from the pipeline toolchain.

- **Command Template:** String with named placeholders resolved at runtime. Composed: `{run_prefix} pytest {test_path}` → `conda run -n myproject pytest tests/unit_4/`.

- **Behavioral Equivalence:** Resolved commands must be character-for-character identical to SVP 1.2 hardcoded commands.

- **Forking Point:** A setup decision that determines an aspect of the delivered project. Classified into Tier A (fixed), Tier B (configurable in 2.0), Tier C (recognized, deferred to 2.x).

- **Preference Enforcement:** Three-layer mechanism ensuring LLM agents respect human tool preferences: blueprint contracts (Layer 1), checker validation (Layer 2), delivery scan (Layer 3).

- **Delivery Compliance Scan:** Deterministic script running during Stage 5 that checks delivered source code against profile preferences for banned patterns.

- **Language-Directed Variant:** A separate product (SVP-R, SVP-elisp, SVP-bash) sharing SVP's pipeline architecture but implementing language-specific tooling. Built by SVP 2.0 as a Python project.

All v6.0 glossary entries remain unchanged.

---

*End of specification.*
