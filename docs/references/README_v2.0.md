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

This builds the `svp` CLI entry point. The script is placed in pip's script directory, which may not be on your PATH. If `svp --help` does not work after installation, you need to locate the script and make it accessible.

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
| `/svp:status` | Show current pipeline state including toolchain and profile summary. |
| `/svp:help` | Pause the pipeline and launch the help agent. |
| `/svp:hint` | Request a diagnostic analysis. |
| `/svp:ref` | Add a reference document (Stages 0–2 only). |
| `/svp:redo` | Roll back a previous decision. Supports profile revisions in SVP 2.0. |
| `/svp:bug` | Enter the post-delivery debug loop (after Stage 5). |
| `/svp:clean` | Archive, delete, or keep the workspace after delivery. |

## Example Project

SVP includes a complete Game of Life example in `examples/game-of-life/` with a stakeholder spec, blueprint, and project context.

```bash
svp restore game-of-life \
  --spec examples/game-of-life/stakeholder_spec.md \
  --blueprint examples/game-of-life/blueprint.md \
  --context examples/game-of-life/project_context.md
```

## Project Structure

```
svp/
├── .claude-plugin/plugin.json    <- Plugin manifest
├── agents/                       <- Agent definition files
├── commands/                     <- Slash command files
├── hooks/                        <- Write authorization hooks
├── scripts/                      <- Deterministic pipeline scripts
│   ├── toolchain_defaults/       <- Default toolchain configuration
│   └── templates/                <- Project template files
└── skills/orchestration/         <- Orchestration skill
```

## History

- **SVP 1.0** — Initial release. The pipeline scripts and plugin infrastructure were hand-written, then used to build subsequent versions of SVP itself.
- **SVP 1.1** — Introduced Gate 6 (post-delivery debug loop), the `/svp:bug` command, triage and repair agent workflows.
- **SVP 1.2** — Bug fixes and hardening. Fixed gate status string vocabulary (Bug 1) and hook permission reset after debug session entry (Bug 2).
- **SVP 1.2.1** — Further bug fixes and robustness improvements.
- **SVP 2.0** — Project Profile (`project_profile.json`) for delivery preferences. Pipeline Toolchain Abstraction (`toolchain.json`). Profile-driven Stage 5 delivery. Delivery compliance scan. `/svp:redo` profile revision support.

## License

Copyright 2026 Carlo Fusco and Leonardo Restivo

Licensed under the MIT License. See [LICENSE](LICENSE) for the full text.
