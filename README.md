# SVP — Stratified Verification Pipeline

A Claude Code plugin that turns natural language requirements into verified Python projects. Also available as **SVP-G** for the Gemini CLI.

**Paper:** \[ArXiv link — forthcoming\]

## What SVP Does

SVP is a six-stage pipeline where a domain expert authors software requirements in conversation, and LLM agents generate, verify, and deliver a working Python project. You never write code. The pipeline compensates for your inability to evaluate generated code through forced separation of concerns: one agent writes tests, a different agent writes implementation, a third reviews coverage, and deterministic scripts control every state transition.

The pipeline stages:

1. **Setup** — Describe your project context, optionally connect GitHub references.
2. **Stakeholder Spec** — A Socratic dialog extracts your requirements, surfacing contradictions and edge cases.
3. **Blueprint** — An agent decomposes the spec into testable units with a dependency DAG. An independent checker verifies alignment.
4. **Unit Verification** — Each unit goes through test generation → red run → implementation → green run → coverage review. Human gates at every decision point.
5. **Integration Testing** — Cross-unit tests verify the seams. Bounded fix cycles handle assembly issues.
6. **Repository Delivery** — A clean git repo with meaningful commit history, Conda environment, and all artifacts.

After delivery, an optional **post-delivery debug loop** (Gate 6) allows investigation and fixing of bugs discovered in the delivered software without requiring engineering judgment from the human.

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
- Python 3.11+

### Install the Plugin

Clone the repository, then register it as a Claude Code marketplace and install the plugin.

#### macOS

```bash
git clone https://github.com/wilya7/svp.git
cd svp
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp
```

#### Linux

```bash
git clone https://github.com/wilya7/svp.git
cd svp
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp
```

#### Windows (WSL2)

All commands must be run inside a WSL2 terminal (Ubuntu recommended). Native Windows (PowerShell, CMD) is not supported.

```bash
git clone https://github.com/wilya7/svp.git
cd svp
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp
```

### Uninstall the Plugin

To remove SVP cleanly, uninstall the plugin first, then remove the marketplace:

```bash
claude plugin uninstall svp@svp
claude plugin marketplace remove svp
```

You can then delete the cloned repository directory if you no longer need it:

```bash
rm -rf /path/to/svp
```

### Install the Launcher

The SVP launcher is a standalone CLI tool that manages session lifecycle. Copy it to your PATH:

#### macOS

```bash
cp /path/to/svp/svp/scripts/svp_launcher.py /usr/local/bin/svp
chmod +x /usr/local/bin/svp
```

Or add to your `~/.zshrc` or `~/.bash_profile`:

```bash
export PATH="$PATH:/path/to/svp/bin"
```

#### Linux

```bash
cp /path/to/svp/svp/scripts/svp_launcher.py /usr/local/bin/svp
chmod +x /usr/local/bin/svp
```

Or add to your `~/.bashrc`:

```bash
export PATH="$PATH:/path/to/svp/bin"
```

#### Windows (WSL2)

```bash
cp /path/to/svp/svp/scripts/svp_launcher.py /usr/local/bin/svp
chmod +x /usr/local/bin/svp
```

The launcher supports three modes:

| Command | Description |
|---------|-------------|
| `svp new [project-name]` | Create a new project from scratch, starting at Stage 0. |
| `svp` | Resume an existing project in the current directory. |
| `svp restore <name> --spec <path> --blueprint <path> --context <path> --scripts-source <path>` | Restore a project from backed-up documents. |

### Start a New Project

```bash
mkdir my-project && cd my-project
svp new my-project
```

The launcher verifies all prerequisites, creates the project directory structure, writes the initial configuration, and launches Claude Code with SVP active.

### Resume an Existing Project

```bash
cd my-project
svp
```

SVP reads the pipeline state file and resumes exactly where you left off.

### Restore a Project from Backed-Up Documents

If you have a stakeholder spec, blueprint, and project context from a previous SVP project (or from the bundled example), you can restore a fully functional workspace without re-running Stages 0–2:

```bash
svp restore my-project \
  --spec ~/path/to/stakeholder.md \
  --blueprint ~/path/to/blueprint.md \
  --context ~/path/to/project_context.md \
  --scripts-source /path/to/svp/svp/scripts
```

This creates a new project directory, copies in the deterministic scripts, places the documents in their expected locations, initializes the pipeline state, and launches Claude Code ready to continue from where the documents leave off. The `--scripts-source` argument points to the plugin's `scripts/` directory (wherever you cloned the SVP repository).

### Verify Your Installation with the Example Project

SVP ships with a Game of Life example — a small, well-defined project that exercises all six pipeline stages end-to-end. Use it to confirm your installation works before starting your real project:

```bash
svp restore game-of-life \
  --spec /path/to/svp/svp/examples/game-of-life/stakeholder.md \
  --blueprint /path/to/svp/svp/examples/game-of-life/blueprint.md \
  --context /path/to/svp/svp/examples/game-of-life/project_context.md \
  --scripts-source /path/to/svp/svp/scripts
```

The Game of Life project is small enough to complete in a single pass (typically under 30 minutes of compute) and requires no domain expertise — the rules are deterministic and universally known. If this completes successfully, your SVP installation is fully functional.

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

### Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `iteration_limit` | integer (>=1) | `3` | Maximum attempts for alignment loops and red-run retries before escalation. After this many failed attempts, the system stops and requires human intervention. |
| `models.test_agent` | string | `"claude-opus-4-6"` | Model used for test generation agents. Use Claude API model strings. |
| `models.implementation_agent` | string | `"claude-opus-4-6"` | Model used for implementation agents. |
| `models.help_agent` | string | `"claude-sonnet-4-6"` | Model used for the help agent. Sonnet is sufficient and faster for advisory tasks. |
| `models.default` | string | `"claude-opus-4-6"` | Fallback model for any agent role not explicitly configured. |
| `context_budget_override` | integer or null | `null` | When set, overrides the automatic context budget calculation. Value is in tokens. When null, the budget is computed from the smallest model's context window minus 20,000 tokens overhead. |
| `context_budget_threshold` | integer (1-100) | `65` | Percentage of the context budget that a single unit's definition plus upstream contracts may consume. Units exceeding this threshold trigger a warning during blueprint validation. |
| `compaction_character_threshold` | integer | `200` | During ledger compaction, tagged lines longer than this threshold are presumed self-contained and their body text is removed. Lines at or below this threshold keep their bodies as a safety net. |
| `auto_save` | boolean | `true` | When enabled, the system automatically saves state after every significant transition (stage completion, unit verification, document approval, ledger turn). |
| `skip_permissions` | boolean | `true` | When enabled, passes `--dangerously-skip-permissions` to Claude Code on launch, suppressing interactive permission prompts during autonomous pipeline execution. The hook-based write authorization system remains active regardless of this setting and provides the actual safety boundary. Set to `false` if you prefer to approve each tool use manually. |

### Changing Models

To use a different model for test generation:

```json
{
    "models": {
        "test_agent": "claude-sonnet-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6"
    }
}
```

Model assignments use Claude API model strings. You can assign any available model to any role. Keep in mind that using the same model for both test and implementation agents creates a residual risk of correlated interpretation — SVP mitigates this through procedural separation rather than model diversity, but if future models offer meaningful diversity, you can exploit it here.

### Adjusting the Context Budget

The context budget determines the maximum project size SVP can handle. By default, it is computed automatically from the smallest model's context window minus 20,000 tokens of overhead. If you are using models with larger context windows and want to allow bigger projects:

```json
{
    "context_budget_override": 150000
}
```

Set this to `null` to return to automatic calculation.

## Commands

All SVP commands use the `/svp:` namespace. Claude Code's built-in commands (`/help`, `/compact`, `/clear`) remain available alongside them.

| Command | Description |
|---------|-------------|
| `/svp:save` | Flush state to disk and confirm. Primarily a confirmation mechanism — the system auto-saves after every significant transition. Tells you "you are safe to close the terminal." |
| `/svp:quit` | Save and exit the pipeline. |
| `/svp:status` | Show current pipeline state: stage, sub-stage, verified units, alignment iterations used, next expected action, and pass history. |
| `/svp:help` | Pause the pipeline and launch the help agent. Ask any question — about the project, about code, about SVP itself, or about anything else. Read-only, no side effects. At decision gates, the help agent proactively offers to formulate hints. |
| `/svp:hint` | Request a diagnostic analysis. In reactive mode (during failures), automatically reads logs and identifies patterns. In proactive mode (during normal flow), asks what prompted your concern before analyzing. Always concludes with explicit options: continue or restart. |
| `/svp:ref` | Add a reference document or GitHub repository. Available during Stages 0–2 only. Documents are indexed and summarized; GitHub repos require MCP configuration. |
| `/svp:redo` | Roll back a previous decision. Describe your mistake in plain language — the redo agent traces it through the document hierarchy and classifies whether it's a spec issue, blueprint issue, or gate approval error. |
| `/svp:bug` | Enter the post-delivery debug loop. Available after Stage 5 delivery. Initiates a triage dialog to classify the bug and runs a bounded fix cycle. Use `/svp:bug --abandon` to abandon an active debug session. |
| `/svp:clean` | Available after delivery. Archive the workspace (compress to `.tar.gz`), delete it, or keep it as-is. |

## Quick Tutorial

### 1. Start a New Project

```bash
mkdir spike-sorter && cd spike-sorter
svp new
```

SVP launches and asks you to describe your project. Be specific about your domain — the more context you provide, the better the Socratic dialog will be.

### 2. The Socratic Dialog (Stages 0–1)

SVP asks you questions one at a time about your requirements. It surfaces contradictions, probes edge cases, and asks about error handling. Answer honestly — if you're unsure, say so. You can provide reference documents at any time with `/svp:ref`.

When the dialog is complete, SVP drafts a stakeholder spec for your review. You can approve it, request revisions, or ask for a fresh review by an independent reviewer agent.

### 3. Blueprint Generation (Stage 2)

SVP decomposes your spec into testable units with a dependency graph. An independent checker verifies the blueprint aligns with your spec. If alignment fails, SVP iterates — up to the configured `iteration_limit`.

### 4. Building Your Project (Stage 3)

This is where SVP shines. For each unit in dependency order:

- A test agent generates tests from the blueprint contract (you never see the implementation)
- A red run confirms the tests fail against a stub (proving the tests actually test something)
- An implementation agent writes the code (it never sees the tests)
- A green run confirms all tests pass
- A coverage reviewer checks for gaps

At every decision gate, you can invoke `/svp:help` to ask questions or `/svp:hint` to get diagnostic analysis. If something looks wrong to you — a test assertion that doesn't match your domain knowledge, an error message that suggests a misunderstanding — speak up. You are the domain expert.

### 5. Integration and Delivery (Stages 4–5)

After all units pass, integration tests verify the cross-unit seams. SVP delivers a clean git repository with meaningful commit history, a Conda environment file, and all artifacts.

### 6. Post-Delivery Bug Fixing (Gate 6)

After delivery, if you discover a bug in the delivered software:

```bash
/svp:bug
```

SVP enters a triage dialog. A triage agent asks you to describe the problem and classifies it:

- **build/env** — environment or configuration issue
- **single_unit** — bug isolated to one unit
- **cross_unit** — bug spanning multiple units

A regression test is written first to capture the bug, then a bounded fix cycle runs. The fix cycle follows the same escalation ladder as Stage 3 — fresh attempt, hint-guided attempt, diagnostic, diagnostic-guided implementation — ensuring the fix is verified before delivery.

To abandon a debug session without completing the fix:

```bash
/svp:bug --abandon
```

### Tips

- **Use `/svp:help` liberally.** It's free, it's read-only, and it's your primary tool for understanding what's happening. The help agent can explain code, error messages, and pipeline behavior in plain language.
- **Trust your domain instincts.** If a test assertion doesn't match your understanding of the domain, say so at the gate. SVP is designed around the principle that you are the authority on what "correct" means.
- **Don't worry about restarts.** SVP's pass history tracks every restart. Reaching unit 7 and restarting from unit 1 because you caught a spec issue is not a failure — it's the system working as designed.
- **Save before closing the terminal.** Run `/svp:save` or `/svp:quit` to ensure nothing is lost. You can resume any time with `svp`.
- **Use Gate 6 for post-delivery issues.** Don't manually edit the delivered code. Run `/svp:bug` and let SVP handle the investigation, regression test, and fix through its verified workflow.

## Example Project

SVP includes a complete Game of Life example in `examples/game-of-life/` with a stakeholder spec, blueprint, and project context. This serves as both an installation test and a reference for how SVP documents look. The Game of Life was chosen because it has deterministic, universally known rules, is small enough to complete in a single pipeline pass, and exercises every pipeline stage without requiring domain expertise.

## Project Structure

```
my-project/
├── svp_config.json              <- Configuration (editable)
├── pipeline_state.json          <- Pipeline state (managed by SVP)
├── project_context.md           <- Your project description
├── stakeholder.md               <- Generated stakeholder spec
├── blueprint.md                 <- Generated technical blueprint
├── src/                         <- Generated source code (per unit)
├── tests/                       <- Generated tests (per unit)
├── ledgers/                     <- Conversation ledgers
├── logs/                        <- Diagnostic logs and version history
├── references/                  <- Reference documents and index
├── .svp/                        <- Internal state (markers, temp files)
└── scripts/                     <- Deterministic pipeline scripts
```

## Troubleshooting

### "conda activate svp" fails

If `conda activate svp` reports "No such environment":

```bash
# Verify the environment was created
conda env list

# If not listed, create it
conda env create -f environment.yml

# If the environment exists but activate fails, initialize conda for your shell
conda init bash  # or zsh, fish, etc.
# Then restart your terminal
```

### "command not found: svp" after installation

The `svp` command requires PATH setup. Verify:

```bash
# Check if the conda environment is active
conda activate svp

# Run directly with Python if PATH is not set
python -m src.unit_24.stub --help
```

### Import errors when running tests

If pytest reports `ModuleNotFoundError`:

```bash
# Ensure the package is installed in development mode
conda activate svp
pip install -e .

# Verify installation
pip show svp
```

### Wrong Python version

SVP requires Python 3.11 or later:

```bash
# Check Python version in the conda environment
conda activate svp
python --version

# If wrong version, recreate the environment
conda env remove -n svp
conda env create -f environment.yml
```

### Hook errors in Claude Code ("Write not authorized")

If Claude Code reports write authorization failures:

1. Verify you are running inside an SVP session (via `svp`, not `claude`).
2. Check the pipeline state: `/svp:status`.
3. If the session was interrupted mid-unit, resume with `svp`.
4. If hooks are blocking legitimate writes, use `/svp:clean` to reset artifact state for the current unit.

### macOS "permission denied" on project directory

SVP sets project directories to read-only between sessions. This is intentional — run `svp` (not `claude`) to restore write permissions for the session.

### "State file not found" on session resume

If SVP cannot find `pipeline_state.json`, the state recovery mechanism scans for completion markers (`.svp/markers/unit_N_verified`) to reconstruct the most conservative valid state. If recovery fails, use `/svp:status` to inspect the current situation.

## SVP-G: Gemini CLI Version

SVP-G is a fork of the Stratified Verification Pipeline specifically designed for the **Gemini CLI**. It uses a "Project Playbook" and custom commands to orchestrate the pipeline within the Gemini ecosystem.

For documentation and setup instructions specific to the Gemini version, see the [SVP-G README](svp-gemini/README.md).

## History

- **SVP 1.0** — Initial release. Manual bootstrapping: the pipeline scripts and plugin infrastructure were hand-written, then used to build subsequent versions of SVP itself.
- **SVP 1.1** — Introduced Gate 6 (post-delivery debug loop), the `/svp:bug` command, triage and repair agent workflows, and the SVP_PLUGIN_ACTIVE environment variable check.
- **SVP 1.2** — Bug fixes and hardening. Fixed gate status string vocabulary (Bug 1) and hook permission reset after debug session entry (Bug 2). Hardened three invariants identified in SVP 1.1.
- **SVP 1.2.1** — Further bug fixes and robustness improvements.

## License

Copyright 2026 Carlo Fusco and Leonardo Restivo

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
