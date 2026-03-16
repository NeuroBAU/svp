# SVP — Stratified Verification Pipeline

A Claude Code plugin that turns natural language requirements into verified Python projects. You describe what you want; SVP orchestrates LLM agents to build, test, and deliver it — with deterministic state management, multi-agent cross-checking, and human decision gates at every critical point.

## What SVP Does

SVP is a six-stage pipeline where a domain expert authors software requirements in conversation, and LLM agents generate, verify, and deliver a working Python project. You never write code. The pipeline compensates for your inability to evaluate generated code through forced separation of concerns: one agent writes tests, a different agent writes implementation, a third reviews coverage, and deterministic scripts control every state transition.

The pipeline stages:

1. **Setup** — Describe your project context and delivery preferences, optionally connect GitHub references.
2. **Stakeholder Spec** — A Socratic dialog extracts your requirements, surfacing contradictions and edge cases.
3. **Blueprint** — An agent decomposes the spec into testable units with a dependency DAG. An independent checker verifies alignment.
4. **Unit Verification** — Each unit goes through test generation → red run → implementation → green run → coverage review. Human gates at every decision point.
5. **Integration Testing** — Cross-unit tests verify the seams. Bounded fix cycles handle assembly issues.
6. **Repository Delivery** — A clean git repo with meaningful commit history, profile-driven README, and all artifacts.

After delivery, an optional **post-delivery debug loop** (Gate 6) allows investigation and fixing of bugs discovered in the delivered software without requiring engineering judgment from the human.

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
| Gate C | Stage 5 assembly | `ruff format --check` + full lint + full `mypy` (cross-unit) |

- Gate composition is data-driven from `toolchain.json` (`gate_a`, `gate_b`, `gate_c` lists).
- All gates are mandatory. No opt-out.
- Auto-fix runs first; residuals trigger one agent re-pass; then fix ladder.
- Quality gate retry budget is separate from fix ladder retry budget.

**Delivered Quality Configuration**
The `project_profile.json` `quality` section captures your preferences for the delivered project's quality tools (linter, formatter, type checker, import sorter, line length). The git repo agent generates the corresponding configuration in `pyproject.toml`.

**Changelog Support**
Set `vcs.changelog` in your profile to `"keep_a_changelog"` or `"conventional_changelog"` to generate a `CHANGELOG.md` in the delivered repository.

**Post-Delivery Debug Workflow**
The debug loop is restructured: `delivered_repo_path` is tracked in `pipeline_state.json`, the triage agent receives the delivered repo path directly, the debug commit uses a fixed format regardless of `vcs.commit_style`, and the lessons learned document is updated as part of the debug session.

**Test Scenarios in README**
When `testing.readme_test_scenarios` is set in the profile, the README includes a section describing the test suite's coverage approach.

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
git clone https://github.com/wilya7/svp.git
cd svp
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp
```

### Install the Launcher

```bash
pip install -e .
```

This builds the `svp` CLI entry point. The `svp` command is simply a wrapper that invokes `svp/scripts/svp_launcher.py` — the launcher source lives inside the plugin directory and the `pip install` step creates a CLI entry point for it via `pyproject.toml`. The script is placed in pip's script directory, which may not be on your PATH. If `svp --help` does not work after installation, you need to locate the script and make it accessible.

#### macOS / Linux

Find where pip placed the script, then copy or symlink it to a directory on your PATH:

```bash
# Find the script location
find "$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')" -name svp 2>/dev/null

# If found, copy it to ~/.local/bin/ (create the directory if needed)
mkdir -p ~/.local/bin
cp "$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')/svp" ~/.local/bin/svp
chmod +x ~/.local/bin/svp

# Ensure ~/.local/bin is on your PATH (add to ~/.bashrc or ~/.zshrc if not already)
export PATH="$HOME/.local/bin:$PATH"
```

#### Windows (WSL2)

Inside WSL2, the same Linux instructions apply. For native Windows with Anaconda, scripts are typically installed to the Anaconda `Scripts` directory (e.g., `C:\Users\<you>\anaconda3\Scripts\svp.exe`), which is usually on PATH after Anaconda installation.

Verify the installation:

```bash
svp --help
```

### Start a New Project

```bash
svp new my-project
```

The launcher verifies all prerequisites, creates the project directory structure, writes the initial configuration, and launches Claude Code with SVP active.

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

## Writing a Good Spec: Intent Engineering

You do not need to learn to code. In a world with AI,
learning to code is not the skill that matters. What
matters is learning to tell the LLM what you actually
need — precisely enough that the gap between what you said
and what you meant is as small as possible. That gap is
where bugs live. Closing it is the skill. We call it
intent engineering.

When you start your first SVP project, you will not be
good at this. That is expected. The Socratic dialog in
Stage 1 exists precisely to compensate: the agent asks
you questions, surfaces contradictions, pushes you to
think about edge cases you hadn't considered, and
structures your answers into a formal specification. You
bring the domain knowledge; the agent brings the
engineering discipline. Together you produce a spec that
is better than either of you would write alone.

But here is what changes with experience: the dialog gets
shorter. Not linearly — exponentially. Your first project
might take an hour of back-and-forth in Stage 1 as the
agent extracts requirements you didn't know you had. Your
fifth project, you walk in with half the spec already
clear in your head because you have learned what the
pipeline needs to hear. Your tenth project, you write a
draft spec before starting SVP and the dialog becomes a
focused review rather than an extraction.

This happens because you are not learning to code. You
are learning to think like someone who specifies software.
You learn that "compute the budget" is not a spec — it is
a wish. A spec says which models to look up, what their
context windows are, what to subtract, and what to return
when no model matches. You learn that every value the
system uses must come from somewhere explicit — a constant
in the spec, a configuration file, a user input — and
that "the agent will figure it out" is not a source.

The return on this skill is enormous. A domain expert who
has learned intent engineering can produce a stakeholder
spec that flows through the pipeline with minimal
friction: fewer review rounds, fewer redo cycles, fewer
post-delivery bugs. The spec is the highest-leverage
artifact in the entire system. Every hour spent making it
precise saves many hours downstream.

This is what makes you a developer for your domain. Not
the ability to write Python, but the ability to close the
gap between what you know and what the machine needs to
hear.

## Example Project

SVP includes a complete Game of Life example in `examples/game-of-life/` with a stakeholder spec, blueprint, and project context.

```bash
svp restore game-of-life \
  --spec examples/game-of-life/stakeholder_spec.md \
  --blueprint-dir examples/game-of-life/ \
  --context examples/game-of-life/project_context.md \
  --scripts-source svp/scripts/ \
  --profile examples/game-of-life/project_profile.json
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
│   │   ├── toolchain_defaults/      <- Default toolchain configuration
│   │   └── templates/               <- Project template files
│   └── skills/orchestration/        <- Orchestration skill
├── tests/                           <- Test suite
│   └── regressions/                 <- Carry-forward regression tests
├── examples/
│   └── game-of-life/                <- Bundled example
└── docs/                            <- Documentation
    ├── stakeholder_spec.md
    ├── blueprint_prose.md
    ├── blueprint_contracts.md
    ├── project_context.md
    ├── history/
    └── references/
```

## Test Scenarios

The SVP test suite covers:

- **Unit tests** (`tests/unit_N/`): One test module per pipeline unit, covering the unit's behavioral contracts.
- **Regression tests** (`tests/regressions/`): Carry-forward tests for all 47 catalogued bugs. Each file targets a specific bug scenario.
- **Integration tests** (`tests/integration/`): Cross-unit tests covering toolchain resolution, profile flow, blueprint checker preference validation, quality gate execution, and write authorization.

Run the full test suite from the repository root:

```bash
conda run -n svp2_1 pytest tests/ -v
```

## History

- **SVP 1.0** — Initial release. The pipeline scripts and plugin infrastructure were hand-written, then used to build subsequent versions of SVP itself.
- **SVP 1.1** — Introduced Gate 6 (post-delivery debug loop), the `/svp:bug` command, triage and repair agent workflows.
- **SVP 1.2** — Bug fixes and hardening. Fixed gate status string vocabulary (Bug 1) and hook permission reset after debug session entry (Bug 2).
- **SVP 1.2.1** — Further bug fixes and robustness improvements.
- **SVP 2.0** — Project Profile (`project_profile.json`) for delivery preferences. Pipeline Toolchain Abstraction (`toolchain.json`). Profile-driven Stage 5 delivery. Delivery compliance scan. `/svp:redo` profile revision support.
- **SVP 2.1** — Pipeline Quality Gates (A, B, C). Delivered quality configuration. Changelog support. Blueprint prose/contracts split. Stub sentinel. Proactive lessons learned integration. Universal two-branch routing invariant. 47 bug fixes across all pipeline stages.

## License

Copyright 2026 Carlo Fusco and Leonardo Restivo

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
