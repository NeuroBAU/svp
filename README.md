# SVP — Stratified Verification Pipeline

**Version: 2.2**

A Claude Code plugin that turns natural language requirements into verified software projects. SVP 2.2 supports Python, R, mixed Python-R projects, and Claude Code plugins. You describe what you want; SVP orchestrates LLM agents to build, test, and deliver it — with deterministic state management, multi-agent cross-checking, and human decision gates at every critical point.

**Paper:** [TODO: link to ArXiv paper] — the theoretical
foundations, design rationale, and empirical results
behind SVP.

## What SVP Does

SVP is a six-stage pipeline where a domain expert authors software requirements in conversation, and LLM agents generate, verify, and deliver a working Python project. You never write code. The pipeline compensates for your inability to evaluate generated code through forced separation of concerns: one agent writes tests, a different agent writes implementation, a third reviews coverage, and deterministic scripts control every state transition.

The pipeline stages:

1. **Setup** — Describe your project context and delivery preferences, optionally connect GitHub references.
2. **Stakeholder Spec** — A Socratic dialog extracts your requirements, surfacing contradictions and edge cases.
3. **Blueprint** — An agent decomposes the spec into testable units with a dependency DAG. An independent checker verifies alignment.
4. **Unit Verification** — Each unit goes through test generation → red run → implementation → green run → coverage review. Human gates at every decision point.
5. **Integration Testing** — Cross-unit tests verify the seams. Bounded fix cycles handle assembly issues.
6. **Repository Delivery** — A clean git repo with meaningful commit history, profile-driven README, and all artifacts.
7. **Post-Delivery Debugging** *(optional)* — Investigate and fix bugs in the delivered software via `/svp:bug`. See "When Things Go Wrong" below.

## Who It's For

Domain experts who know exactly what their software should do but cannot write it themselves. The motivating example is an academic scientist — a neuroscientist who understands spike sorting, a climate scientist who understands atmospheric models — but SVP is domain-agnostic. If you can judge whether a test assertion makes domain sense when explained in plain language, SVP can build your project.

You need:

- Deep knowledge of your professional field
- Conceptual understanding of programming (you know what functions and loops are)
- Ability to follow terminal instructions precisely
- A Claude Code subscription with API access

You do not need:

- Ability to write code in any language
- Ability to evaluate whether an implementation is correct
- Experience with testing frameworks, git, or environment management

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com) installed and functional
- A valid Anthropic API key configured
- [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda) installed and on your PATH
- [Git](https://git-scm.com/) installed and configured
- Python 3.10+

### Install the Plugin

Clone the repository, then register it as a Claude Code marketplace and install the plugin.

#### macOS / Linux / Windows (WSL2)

```bash
git clone https://github.com/NeuroBAU/svp.git
cd svp
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp --scope project
```

**Note (Bug S3-123).** The `--scope project` flag is important. Without it, `claude plugin install` defaults to `--scope user`, which enables SVP in **every** Claude Code session on the machine regardless of working directory — you would see `/svp:*` commands and the SVP consultant agent in `/tmp`, in unrelated project directories, everywhere. The `--scope project` flag writes the enablement into `<project_root>/.claude/settings.json` so SVP activates only in directories where you have an SVP pipeline. The SVP launcher (`svp new`, `svp resume`, `svp restore`) also writes this file automatically via `ensure_project_settings()`, so you normally don't need to run `claude plugin install` at all — just `svp new <project>` and the launcher takes care of scoping.

### Migration: from user-scope to project-scope (existing SVP users, Bug S3-123)

If you installed SVP before version 2.2 (or with the wrong scope), your enablement entry lives in `~/.claude/settings.json` at user scope, which leaks SVP into every `claude` session on your machine. To migrate:

```bash
# Step 1: remove the user-scope leak
claude plugin uninstall svp@svp --scope user

# Step 2: for each SVP pipeline directory you have, run the launcher once
# to write .claude/settings.json and re-enable at project scope:
cd /path/to/my/svp-pipeline
svp       # bare svp == resume; triggers ensure_project_settings

# Verify:
cd /tmp && claude
# Autocomplete should NOT show /svp:* commands and the SVP consultant
# agent should NOT appear in the system reminder.
```

The migration is **opt-in**. If you prefer to keep user-scope enablement (SVP always available, accepting the leak), leave your config alone — SVP continues to work as before.

The `ensure_project_settings()` helper is **idempotent**, **non-destructive** (preserves unrelated settings.json keys), and **self-healing** (rewrites the marketplace path if you move the SVP repo on disk). Re-running the launcher in a migrated directory is always safe.

### Install the Launcher

```bash
pip install -e . --prefix ~/.local
```

This installs the `svp` CLI entry point into `~/.local/bin/`. The `-e` flag means "editable install" — pip creates a link to the source code rather than copying it, so any changes to the plugin source are immediately reflected without reinstalling. The `--prefix ~/.local` flag tells pip to install the script into `~/.local/bin/` instead of the system or virtual environment default, which keeps user-installed tools separate from system packages.

You can use any directory you prefer instead of `~/.local` — the only requirement is that the `bin/` subdirectory of your chosen prefix is on your shell's `PATH`. If `svp --help` does not work after installation, the install directory is not on your PATH.

#### Adding the install directory to your PATH

The `PATH` environment variable tells your shell where to find executable commands. If pip installs `svp` to a directory not already in your PATH, you need to add it.

**macOS (zsh — default shell since Catalina):**

```bash
# Add to ~/.zshrc (loaded on every new terminal)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

# Apply to current session without restarting terminal
source ~/.zshrc
```

**Linux (bash — most common default shell):**

```bash
# Add to ~/.bashrc (loaded on every new terminal)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Apply to current session
source ~/.bashrc
```

**Windows (WSL2):**

Inside WSL2, follow the Linux/bash instructions above. For native Windows with Anaconda, scripts are typically installed to the Anaconda `Scripts` directory (e.g., `C:\Users\<you>\anaconda3\Scripts\svp.exe`), which is usually on PATH after Anaconda installation. To add a custom directory to PATH on native Windows, open **Settings > System > About > Advanced system settings > Environment Variables** and edit the `Path` variable under "User variables."

#### Verify the installation

```bash
svp --help
```

### Start a New Project

```bash
svp new my-project
```

The launcher verifies all prerequisites, creates the
project directory structure, writes the initial
configuration, and launches Claude Code with SVP active.

## Setup Process

When SVP starts a new project, the setup agent guides you through a Socratic dialog. The dialog begins with **project archetype selection**:

- **Option A** — Python project
- **Option B** — R project (with optional Stan integration)
- **Option C** — Claude Code plugin
- **Option D** — Mixed-language project (Python + R, either direction)
- **Option E** — SVP language extension self-build (adds a new language to SVP)
- **Option F** — SVP architectural self-build (modifies SVP's pipeline machinery)

Your choice determines the language toolchain, test framework, quality tools, and project structure used throughout the build. Options A-D are for building your own software. Options E-F are for extending or rebuilding SVP itself (see [docs/extending-languages.md](docs/extending-languages.md)).

After archetype selection, the dialog captures your **project context** — what the project does, who it's for, what domain it operates in — and your **delivery preferences** across several areas:

1. **Version Control** — Commit style, branch strategy, changelog format, GitHub repository configuration.
2. **README and Documentation** — Generate new or update existing, target audience, sections, depth, docstring convention.
3. **Test and Quality** — Coverage target, readable test names, test scenarios in README.
4. **Licensing, Metadata, and Packaging** — License type, author info, entry points, environment manager, dependency format, source layout.
5. **Delivered Code Quality** — Linter, formatter, type checker, import sorter, and line length for the delivered project. Tool choices are language-specific.
6. **Agent Model Configuration** — Choose which Claude model (opus, sonnet, or haiku) each pipeline agent uses. Opus is the default for most agents.

Every area offers a fast path: accept sensible defaults with a single response, or dive into detailed options. The setup agent explains every choice in plain language and uses progressive disclosure — details only when you ask.

Your choices are recorded in `project_profile.json` and drive everything from Stage 5 delivery to agent model selection during the build.

## Workspace and Delivered Repository

SVP maintains two separate directories for your project:

The **workspace** is where the pipeline builds your
software. When you run `svp new my-project`, the launcher
creates `my-project/` containing the pipeline scripts,
configuration files, source directories (`src/unit_N/`),
test directories (`tests/unit_N/`), and all pipeline
state. This is the build environment — you work here
during Stages 0 through 4.

The **delivered repository** is the clean output. At
Stage 5, the git repo agent assembles a separate git
repository at `my-project-repo/` (a sibling directory,
not inside the workspace). It relocates your code from
the workspace's `src/unit_N/stub.py` structure into
proper module paths, rewrites imports, generates
`pyproject.toml`, creates a meaningful commit history,
and delivers a repository that looks like a normal Python
project — no SVP infrastructure, no stubs, no pipeline
state.

The two directories serve different purposes: the
workspace is disposable build scaffolding; the delivered
repo is what you ship, share, or publish.

If you use `/svp:redo` to roll back to the stakeholder
spec or blueprint (before Stage 3), the pipeline rebuilds
from scratch. When Stage 5 runs again, it does not
overwrite the existing delivered repo — it renames the
old one with a timestamp (e.g., `my-project-repo` becomes
`my-project-repo_20260315_143022`) and creates a fresh
`my-project-repo`. Each restart produces a new delivered
directory. After N restarts, you will have N+1 directories:
the current `my-project-repo` plus N timestamped backups.
You can delete the backups once you are satisfied with the
current delivery.

When you use `/svp:bug` after delivery, the triage agent
investigates in the delivered repository (using the
`delivered_repo_path` recorded in pipeline state) and
applies fixes to the workspace source first. The pipeline
then triggers a Stage 5 reassembly to propagate the fix
into the delivered repository. This ensures the workspace
remains the canonical source and the delivered repo stays
in sync.

Once you are satisfied with the delivered project, use
`/svp:clean` to dispose of the workspace. It offers three
modes: **archive** compresses the workspace into a
timestamped zip file and deletes the directory;
**delete** removes the workspace immediately without
backup; **keep** removes the Conda environment but leaves
the workspace files in place. All three modes remove the
Conda environment created during the build. The delivered
repository is never touched by `/svp:clean` — it is yours
to keep regardless of what you do with the workspace.
`/svp:clean` is only available after Stage 5 completes.

## Configuration

SVP is configured through `svp_config.json` in your project root. Changes take effect on the next agent invocation — no restart required.

### Default Configuration

```json
{
    "iteration_limit": 3,
    "models": {
        "test_agent": "claude-opus-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6"
    },
    "context_budget_override": null,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": true,
    "skip_permissions": true
}
```

## Commands

All SVP commands use the `/svp:` namespace.

| Command | Description |
|---------|-------------|
| `/svp:save` | Flush state to disk and confirm. |
| `/svp:quit` | Save and exit the pipeline. |
| `/svp:status` | Show current pipeline state including toolchain, profile summary, and active quality gate status. |
| `/svp:help` | Pause the pipeline and launch the help agent. |
| `/svp:hint` | Request a diagnostic analysis. |
| `/svp:ref` | Add a reference document (Stages 0–2 only). |
| `/svp:redo` | Roll back a previous decision. Supports profile revisions. |
| `/svp:bug` | Enter the post-delivery debug loop (after Stage 5). |
| `/svp:oracle` | Run the oracle agent for systematic trajectory review and fix planning. |
| `/svp:clean` | Archive, delete, or keep the workspace after delivery. |

## When Things Go Wrong: The Two Fix Ladders

Every project has bugs. In practice, bugs almost always
trace back to something the stakeholder spec didn't say
clearly enough. The agents are probabilistic, but when
they produce wrong code it is nearly always because the
spec left room for the wrong interpretation — a vague
contract, a missing constraint, an unstated assumption.
The code is wrong because the spec allowed it to be wrong.

SVP provides two strategies for fixing bugs. Both start
the same way — you find something wrong in the delivered
software — but they climb different ladders. The
difference is not where the bug comes from (it comes from
the spec), but whether the cost of fixing the spec is
worth it for your project.

### Ladder 1: Fix the Unit

The pragmatic choice for small projects and disposable
code. You know the bug comes from the spec, but fixing
the spec, regenerating the blueprint, and rebuilding from
scratch would cost more in time and tokens than the
project is worth. So you fix the symptom and move on.

**When to use:** Small projects, exploratory code, or any
situation where the cost of a full rebuild outweighs the
benefit. The LLM can compensate for spec vagueness in
common domains — data analysis, simulations, utilities —
so unit-level fixes stick well enough.

**How it works:**

1. Run `/svp:bug` and describe what you observed.
2. The triage agent investigates the delivered repo,
   identifies the affected unit, and classifies the bug.
3. A regression test is written to reproduce the failure.
4. The repair agent fixes the unit implementation.
5. All tests pass (including the new regression test).
6. The fix is committed to the delivered repo.

This is fast and self-contained. The spec and blueprint
are not touched. You are fixing the instance of the bug,
not the class. For most projects, this is the right
trade-off.

### Ladder 2: Fix the Source

The thorough choice for complex projects where spec-level
gaps produce cascading bugs across multiple units. You fix
the root cause — the spec itself — and rebuild.

**When to use:** Complex projects with cross-unit
contracts, state machines, or architectural invariants.
Also any project where you fix a unit bug and the same
*kind* of bug keeps appearing elsewhere — that pattern
means the spec has a systemic gap that unit-level repair
cannot close.

**How it works:**

1. Run `/svp:bug` and describe what you observed.
2. The triage agent investigates. Pay attention to its
   root cause analysis and ask yourself: *Why did the
   spec allow this bug to exist? What should it have
   said?*
3. Use the triage agent's findings to trace the bug
   backward: from the failing code, to the blueprint
   contract that produced it, to the spec section that
   should have prevented it.
4. Run `/svp:redo` to roll back to the stakeholder spec.
5. Revise the spec to close the gap — add the missing
   detail, the missing constraint, the missing invariant.
6. The pipeline rebuilds from the corrected spec: new
   blueprint, new tests, new implementation.

This is expensive in time and tokens. You are throwing
away completed work and rebuilding from scratch. But for
the class of project that needs it, there is no
alternative — you cannot test your way out of a spec gap.

## Writing a Good Spec

The quality of your implementation is capped by the quality of your specification. In AI-assisted coding, this is not a platitude — it is a mechanical fact. AI is very good at expanding local structure and very bad at rescuing an ambiguous plan. Give it a blurry request and it will generate plausible blur. Give it a precise specification and it can produce useful, testable components.

You do not need to learn to code. What matters is learning to close the gap between what you know and what the machine needs to hear. That gap is where bugs live. The Socratic dialog in Stage 1 helps you close it: the agent asks questions, surfaces contradictions, and structures your answers into a formal specification. With experience, the dialog gets shorter — not because you are learning Python, but because you are learning to think like someone who specifies software.

SVP produces two key documents. The **stakeholder spec** is yours — it describes *what* your software should do using your domain concepts. The **blueprint** is the LLM's translation into software architecture — units, signatures, contracts, dependencies. You approve the blueprint but do not write it.

The essential concepts for writing good specs are: **invariants** (conditions that must always be true), **enumerations** (listing all valid values explicitly), **error semantics** (what happens when things go wrong), **scope** (what the system owns vs. what it does not), and **testability** (can you verify it from the outside?). For the blueprint, additional concepts matter: **signatures**, **contracts**, **dispatch tables**, **data models**, and **state machines**.

For a comprehensive treatment of these concepts — with worked examples, SVP's own bug history, a nine-question checklist, and guidance on what belongs in the spec vs. the blueprint — see [docs/writing-specifications.md](docs/writing-specifications.md).

## Example Project

SVP includes a complete Game of Life example in `examples/game-of-life/` with a stakeholder spec, blueprint, and project context.

```bash
svp restore game-of-life --repo .
```

## Project Structure

```
svp-repo/
├── .claude-plugin/marketplace.json   <- Marketplace catalog
├── svp/                              <- Plugin subdirectory
│   ├── .claude-plugin/plugin.json   <- Plugin manifest
│   ├── agents/                      <- Agent definition files
│   ├── commands/                    <- Slash command files
│   ├── hooks/                       <- Write authorization hooks
│   ├── scripts/                     <- Deterministic pipeline scripts
│   │   └── toolchain_defaults/      <- Default toolchain configuration
│   └── skills/orchestration/        <- Orchestration skill
├── src/                             <- Unit stubs (source of truth)
│   └── unit_N/stub.py              <- One stub per pipeline unit
├── tests/                           <- Test suite
│   ├── unit_N/                     <- Unit tests
│   ├── integration/                <- Cross-unit integration tests
│   └── regressions/                <- Carry-forward regression tests
├── examples/                        <- Bundled examples + oracle test projects
│   └── game-of-life/
├── docs/                            <- All documentation (consolidated)
│   ├── CLAUDE.md                   <- Workspace instructions (restore-only)
│   ├── project_context.md          <- Project context (restore-only)
│   ├── stakeholder_spec.md
│   ├── blueprint_prose.md
│   ├── blueprint_contracts.md
│   ├── history/                    <- Document version snapshots
│   └── references/
│       ├── svp_2_1_lessons_learned.md
│       └── existing_readme.md
├── sync_workspace.sh               <- One-way workspace → repo sync
├── pyproject.toml                   <- Build/packaging configuration
├── environment.yml                  <- Conda environment
├── ruff.toml                       <- Quality tool configuration
└── README.md                       <- This file
```

### Workspace-Repo Sync Protocol

The workspace is the single source of truth. The repo is a derived artifact.

- **Sync direction:** One-way, workspace → repo. `sync_workspace.sh` copies workspace files to repo, warning if repo files are newer.
- **Repo paths:** Stored in `.svp/sync_config.json` (written by `restore_project()`, read by `sync_workspace.sh`).
- **Test imports:** All tests use flat module imports (`from routing import ...`), not workspace-internal stub imports.
- **Documentation:** Consolidated in `docs/` — no `specs/`, `blueprint/`, `references/` at repo root.
- **Script derivation:** Stubs (`src/unit_N/stub.py`) are the source of truth. Scripts (`scripts/*.py`) are derived by import rewriting. Never edit scripts directly.

### Document Version Tracking

Every time a document is revised through a gate decision (REVISE, FIX BLUEPRINT, or FIX SPEC), the routing script's `dispatch_gate_response` function calls `version_document()` to snapshot the current version before the revision occurs. The previous version is copied to `docs/history/` with an incrementing version number (e.g., `stakeholder_spec_v1.md`, `blueprint_prose_v2.md`), and a diff summary is saved alongside it recording the timestamp, trigger context, and what changed. The current working version remains at its canonical path in `docs/`. Blueprint files are always versioned as an atomic pair — both prose and contracts are snapshotted together. This history is included in the delivered repository at `docs/history/`.

## Test Scenarios

The SVP test suite covers:

- **Unit tests** (`tests/unit_N/`): One test module per pipeline unit, covering the unit's behavioral contracts.
- **Regression tests** (`tests/regressions/`): Carry-forward tests for all catalogued bugs. Each file targets a specific bug scenario. New in SVP 2.2: `test_assembly_map_generation.py`, `test_dispatch_exhaustiveness.py`, `test_three_layer_separation.py`, `test_profile_migration.py`, `test_r_test_output_parsing.py`, `test_behavioral_equivalence.py`.
- **Integration tests** (`tests/integration/`): Cross-unit tests covering toolchain resolution, profile flow, blueprint checker preference validation, quality gate execution, and write authorization.

Run the full test suite from the repository root:

```bash
conda run -n svp2_2 pytest tests/ -v
```

## SVP 2.0 Features

SVP 2.0 adds two capabilities to the complete SVP 1.2 baseline:

**Project Profile (`project_profile.json`)**
The setup agent conducts a Socratic dialog to capture your delivery preferences: README structure, commit message style, documentation depth, license, dependency format, and more. These preferences are recorded in `project_profile.json` and used to drive Stage 5 delivery. You can accept sensible defaults with a single response or dive into detailed configuration.

**Pipeline Toolchain Abstraction (`toolchain.json`)**
SVP's own build commands (conda, pytest, setuptools, git) are now read from a configuration file rather than hardcoded. This is a code quality improvement — it does not change how SVP builds your project. The file is copied from the plugin at project creation and is permanently read-only.

## SVP 2.1 Features

SVP 2.1 is the terminal release of the SVP product line, adding pipeline-integrated quality gates and delivered quality configuration.

**Pipeline Quality Gates (A, B, C)**
Every project built by SVP 2.1 is automatically formatted, linted, and type-checked during the build. Quality is a pipeline guarantee, not an opt-out feature.

| Gate | Position | Operations |
|------|----------|------------|
| Gate A | Post-test generation, pre-red-run | `ruff format` + light lint (E, F, I rules). No type check on tests. |
| Gate B | Post-implementation, pre-green-run | `ruff format` + heavy lint + `mypy --ignore-missing-imports` |
| Gate C | Stage 5 assembly | `ruff format --check` + full lint + full `mypy` (cross-unit) + unused function detection (human-gated) |

- Gate composition is data-driven from `toolchain.json` (`gate_a`, `gate_b`, `gate_c` lists).
- All gates are mandatory. No opt-out.
- Auto-fix runs first; residuals trigger one agent re-pass; then fix ladder.
- Quality gate retry budget is separate from fix ladder retry budget.

**Delivered Quality Configuration**
The `project_profile.json` `quality` section captures your preferences for the delivered project's quality tools (linter, formatter, type checker, import sorter, line length). The git repo agent generates the corresponding configuration in `pyproject.toml`.

**Changelog Support**
Set `vcs.changelog` in your profile to `"keep_a_changelog"` or `"conventional_changelog"` to generate a `CHANGELOG.md` in the delivered repository.

**Test Scenarios in README**
When `testing.readme_test_scenarios` is set in the profile, the README includes a section describing the test suite's coverage approach.

## SVP 2.1.1 Features

SVP 2.1.1 adds unit-level preference capture to the blueprint dialog, enabling domain experts to express non-requirement preferences (output format conventions, naming styles, display choices) during blueprint construction rather than after delivery.

**Unit-Level Preference Capture**
During Stage 2 blueprint construction, the blueprint author agent follows four rules (P1-P4) to capture domain preferences at the unit level:

- **Rule P1 (Ask at the unit level):** After establishing each unit's Tier 1 description and before finalizing its contracts, ask about domain conventions, output appearance preferences, and domain-specific choices that are not requirements but matter.
- **Rule P2 (Domain language only):** Use the human's domain vocabulary, not engineering vocabulary. The agent asks "What file format do your collaborators' tools expect?" rather than "Do you have preferences for the serialization format?"
- **Rule P3 (Progressive disclosure):** One open question per unit. Follow-up only if the human indicates preferences. No menu of categories for every unit.
- **Rule P4 (Conflict detection at capture time):** If a preference contradicts a behavioral contract being developed, identify immediately and resolve during dialog.

Captured preferences are recorded as a `### Preferences` subsection within each unit's Tier 1 description in `blueprint_prose.md`. Absence of the subsection means "no preferences" -- no explicit marker is needed. The authority hierarchy is: spec > contracts > preferences. Preferences are non-binding guidance that operates within the space contracts leave open.

**Preference-Contract Consistency Validation**
The blueprint checker validates that no stated preference contradicts a Tier 2 signature or Tier 3 behavioral contract. Inconsistencies are reported as non-blocking warnings (not alignment failures), since preferences are advisory by design.

**Structural Completeness Checking**
SVP 2.1.1 introduces a four-layer structural completeness defense: a project-agnostic AST scanner, 14 automated declaration-vs-usage techniques, 163 structural tests, and registry completeness validation. This system catches orphaned functions, missing dispatch paths, and declaration-usage mismatches at build time rather than after delivery.

## SVP 2.2 Features

SVP 2.2 extends the pipeline to support multiple languages and new project archetypes.

**Multi-Language Support**
SVP 2.2 ships with full support for Python and R projects, plus Stan as a component language (embedded in R or Python projects). A language provider framework makes it straightforward to add new languages. See [docs/extending-languages.md](docs/extending-languages.md) for a step-by-step guide to adding a new language.

**Six Per-Language Dispatch Tables**
All language-specific behavior is encapsulated in dispatch tables:

| Dispatch Table | Module | Dispatch Key |
|---|---|---|
| `SIGNATURE_PARSERS` | `signature_parser.py` | language name |
| `STUB_GENERATORS` | `stub_generator.py` | language name |
| `TEST_OUTPUT_PARSERS` | `routing.py` | language name |
| `QUALITY_RUNNERS` | `quality_gate.py` | language name |
| `PROJECT_ASSEMBLERS` | `adapt_regression_tests.py` | language name |
| `COMPLIANCE_SCANNERS` | `structural_check.py` | language name |

**Archetype System (Areas A-F)**
The setup agent offers six project archetypes: Python project (A), R project (B), Claude Code plugin (C), mixed-language project (D), SVP language extension self-build (E), and SVP architectural self-build (F). Options E and F trigger the Pass 1/Pass 2 bootstrap protocol.

**Three-Layer Toolchain Separation**
SVP 2.2 enforces strict separation between the pipeline toolchain (`toolchain.json`), the build-time language toolchain (`python_conda_pytest.json` / `r_renv_testthat.json`), and the delivered project quality configuration (from `project_profile.json`). This is enforced by a structural regression test.

**Oracle Agent**
The oracle agent provides systematic post-delivery analysis with a four-phase protocol: dry run, Gate A (trajectory review), green run with fix plan, Gate B (fix plan approval). Invoked via `/svp:oracle`.

**Profile Migration**
SVP 2.2 automatically migrates SVP 2.1 project profiles to the new language-keyed format (`delivery.python.*`, `quality.python.*`). No manual migration required.

## History

- **SVP 1.0** — Initial release. The pipeline scripts and plugin infrastructure were hand-written, then used to build subsequent versions of SVP itself.
- **SVP 1.1** — Introduced Gate 6 (post-delivery debug loop), the `/svp:bug` command, triage and repair agent workflows.
- **SVP 1.2** — Bug fixes and hardening. Fixed gate status string vocabulary (Bug 1) and hook permission reset after debug session entry (Bug 2).
- **SVP 1.2.1** — Further bug fixes and robustness improvements.
- **SVP 2.0** — Project Profile (`project_profile.json`) for delivery preferences. Pipeline Toolchain Abstraction (`toolchain.json`). Profile-driven Stage 5 delivery. Delivery compliance scan. `/svp:redo` profile revision support.
- **SVP 2.1** — Pipeline Quality Gates (A, B, C) as mandatory build-time checkpoints. Delivered quality configuration via `project_profile.json`. Blueprint prose/contracts split for token-efficient agent context. Universal two-branch routing invariant applied across all pipeline stages. 51 bug fixes (Bugs 17-58) spanning routing, dispatch, state persistence, dead code removal, and spec structural gaps. See CHANGELOG.md for detailed bug-by-bug history.
- **SVP 2.1.1** — Unit-level preference capture in blueprint dialog (Rules P1-P4, preference-contract consistency validation). Structural completeness checking system: four-layer defense with project-agnostic AST scanner, 14 automated declaration-vs-usage techniques, 163 structural tests (Bugs 71-72). Configurable agent models (`pipeline.agent_models` in profile -- opus/sonnet/haiku per agent). GitHub repository configuration (`vcs.github` in profile -- new/existing_force/existing_branch/none modes). README mode (`readme.mode` in profile -- generate or update existing). 39 additional bug fixes (Bugs 52-91) including full Stage 3 error handling, Stage 4 failure paths, debug loop gates, selective blueprint loading, routing dispatch loops (Bug 73), test target invariant (Bug 74), and regression test import adaptation (Bug 85). 95 total bugs cataloged across SVP 1.0 through 2.1.1.
- **SVP 2.2** — Multi-language support: Python, R, mixed Python-R projects, and Claude Code plugins. Language provider framework with per-language dispatch tables (six dispatch tables: signature parsers, stub generators, test output parsers, quality runners, project assemblers, compliance scanners). Language registry (`language_registry.py`) as the single source of truth for all per-language configuration. Three-layer toolchain separation (pipeline toolchain, build-time language toolchain, delivered project quality config). Archetype system (A-F) in setup agent. Pass 1 / Pass 2 bootstrap protocol for SVP self-builds (Options E/F). Oracle agent for trajectory review and systematic post-delivery analysis. Profile migration for SVP 2.1 compatibility. 29-unit build (up from 22 units in SVP 2.1.1).

## License

Copyright 2026 Carlo Fusco and Leonardo Restivo

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
