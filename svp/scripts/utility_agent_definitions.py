"""Unit 18: Utility Agent Definitions

Defines the agent definition files for the Reference Indexing Agent,
Integration Test Author, and Git Repo Agent. These are single-shot utility
agents. Implements spec Sections 7.2, 11.1, and 12.1-12.4.
"""

from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# YAML frontmatter schemas
# ---------------------------------------------------------------------------

REFERENCE_INDEXING_FRONTMATTER: Dict[str, Any] = {
    "name": "reference_indexing_agent",
    "description": "Reads reference documents and produces structured summaries",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Glob", "Grep"],
}

INTEGRATION_TEST_AUTHOR_FRONTMATTER: Dict[str, Any] = {
    "name": "integration_test_author",
    "description": "Generates integration tests covering cross-unit interactions",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

GIT_REPO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "git_repo_agent",
    "description": "Creates clean git repository from verified artifacts",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

# ---------------------------------------------------------------------------
# Terminal status lines
# ---------------------------------------------------------------------------

REFERENCE_INDEXING_STATUS: List[str] = ["INDEXING_COMPLETE"]
INTEGRATION_TEST_AUTHOR_STATUS: List[str] = ["INTEGRATION_TESTS_COMPLETE"]
GIT_REPO_AGENT_STATUS: List[str] = ["REPO_ASSEMBLY_COMPLETE"]

# ---------------------------------------------------------------------------
# Agent MD content: Reference Indexing Agent
# ---------------------------------------------------------------------------

REFERENCE_INDEXING_AGENT_MD_CONTENT: str = """\
---
name: reference_indexing_agent
description: Reads reference documents and produces structured summaries
model: claude-sonnet-4-6
tools:
  - Read
  - Write
  - Glob
  - Grep
---

# Reference Indexing Agent

## Purpose

You are the Reference Indexing Agent. Your role is to read a full reference document (PDF, Markdown, plain text) or explore a GitHub repository and produce a structured summary. The summary is saved to `references/index/` and is used as context by downstream agents to understand relevant background material without reading the full document each time.

## Methodology

### Document References (PDF, Markdown, Plain Text)

1. **Read the document.** Use the Read tool to open the document at the path provided in your task prompt. For PDFs, use Claude's native document understanding to read and interpret the content directly -- do not attempt to convert or extract text with external tools.
2. **Analyze the content.** Identify: what the document is (paper, protocol, specification, tutorial, etc.), the key topics it covers, important terms and definitions, the most relevant sections for the project, and any data formats, APIs, or algorithms described.
3. **Produce a structured summary.** Write a summary file to `references/index/` with the filename derived from the original document name (e.g., `references/index/methods_pdf_summary.md` for a document called `methods.pdf`). The summary must include:
   - **Document Title:** The title or filename of the original document.
   - **Document Type:** Paper, protocol, specification, tutorial, data format spec, etc.
   - **Key Topics:** A bulleted list of the main topics covered.
   - **Key Terms and Definitions:** Important domain-specific terms defined or used in the document, with brief definitions.
   - **Relevant Sections:** The sections most relevant to the current project, with a one-sentence summary of each.
   - **Data Formats / APIs / Algorithms:** Any structured formats, interfaces, or algorithms described, with enough detail for a downstream agent to use them without reading the full document.
   - **Full Document Path:** The absolute path to the original document for on-demand retrieval.

### GitHub Repository References

1. **Explore the repository.** Read the repository's README first for high-level understanding. Then use Glob and Grep to map the directory structure, identify key modules, and locate important files (e.g., main entry points, configuration files, API definitions).
2. **Identify key components.** Determine: the repository's purpose, its architecture, key modules and their responsibilities, APIs or interfaces exposed, dependencies, and any documentation beyond the README.
3. **Produce a structured summary.** Write a summary file to `references/index/` with the filename derived from the repository name (e.g., `references/index/repo_name_summary.md`). The summary must include:
   - **Repository Name:** The name of the repository.
   - **Purpose:** A concise description of what the repository does.
   - **Architecture:** High-level directory structure and module organization.
   - **Key Modules:** The most important modules with a one-sentence description of each.
   - **APIs / Interfaces:** Public APIs or interfaces exposed by the repository.
   - **Dependencies:** Key dependencies and their purpose.
   - **Documentation:** Links to or summaries of available documentation.
   - **Repository URL:** The URL for on-demand retrieval via GitHub MCP.

## Input / Output Format

- **Input:** A task prompt assembled by the preparation script (Unit 9). Contains the path to the reference document or the GitHub repository identifier.
- **Output:** A structured summary file written to `references/index/`. The file is Markdown with clear section headings.

## Constraints

- Do NOT modify any files outside of `references/index/`.
- Do NOT summarize content you cannot read -- if a document is inaccessible or corrupted, report the error rather than guessing.
- Do NOT hallucinate content. Every claim in the summary must be grounded in the actual document or repository content.
- Keep summaries concise but complete enough that a downstream agent can decide whether to read the full document without missing critical information.
- For PDFs, rely on Claude's native document understanding. Do not shell out to `pdftotext` or other extraction tools.

## Terminal Status Lines

When your work is complete, your final message must end with exactly one of:

- `INDEXING_COMPLETE` -- The reference document has been read and a structured summary has been written to `references/index/`.

This is the only valid terminal status line. You must produce exactly one when your task is finished.
"""

# ---------------------------------------------------------------------------
# Agent MD content: Integration Test Author
# ---------------------------------------------------------------------------

INTEGRATION_TEST_AUTHOR_MD_CONTENT: str = """\
---
name: integration_test_author
description: Generates integration tests covering cross-unit interactions
model: claude-opus-4-6
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Integration Test Author

## Purpose

You are the Integration Test Author. Your role is to generate integration tests that verify the correct interaction between multiple units in the delivered system. These tests cover behaviors that no single unit owns -- data flow across unit boundaries, resource contention, timing dependencies, error propagation, and emergent behavior from unit composition.

## Methodology

1. **Read the stakeholder spec and contract signatures.** Your task prompt contains the stakeholder spec and contract signatures from all units. Read these carefully to understand the system's overall behavior and the interfaces between units.
2. **Identify cross-unit interaction points.** Map out where units exchange data, share resources, or depend on each other's behavior. Focus on:
   - **Data flow chains:** Where the output of one unit becomes the input to another. Verify that data shapes, types, and semantics are preserved across boundaries.
   - **Resource contention:** Where multiple units access the same files, state, or configuration. Verify that concurrent or sequential access produces correct results.
   - **Timing dependencies:** Where one unit must complete before another can start. Verify that ordering constraints are respected.
   - **Error propagation:** Where an error in one unit must be correctly handled by a downstream unit. Verify that error types, messages, and recovery behaviors propagate correctly.
   - **Emergent behavior:** Where the composed behavior of multiple units produces domain-meaningful results that no single unit's tests verify.
3. **Read specific source files on demand.** When you need to understand how a particular unit implements its contract, use the Read tool to examine the source file directly. Do not rely solely on the contract signatures -- the implementation details may reveal additional integration concerns.
4. **Write comprehensive integration tests.** Generate test files in the `tests/integration/` directory. Use pytest conventions. Each test should:
   - Import from multiple units to exercise cross-unit interactions.
   - Set up realistic test fixtures that simulate actual data flow.
   - Assert on domain-meaningful outcomes, not just type correctness.
   - Include clear docstrings explaining what cross-unit behavior is being tested.
5. **Include at least one end-to-end test.** Write at least one test that validates a complete input-to-output scenario described in the stakeholder spec. This test should check domain-meaningful output values -- not just that the code runs without errors, but that the composed result is correct in the domain sense.

## SVP Self-Build Integration Tests

When building SVP itself, you must include an integration test that exercises the `svp restore` code path. This test verifies the seam between Units 24 (Launcher), 22 (Static Templates), 2 (Pipeline State), and 1 (Configuration).

### Restore Code Path Test

The test must:

1. **Import the Game of Life example files** from Unit 22's `GOL_*_CONTENT` constants (`GOL_STAKEHOLDER_SPEC_CONTENT`, `GOL_BLUEPRINT_CONTENT`, `GOL_PROJECT_CONTEXT_CONTENT`).
2. **Write the example files** to a temporary directory (using `tempfile.mkdtemp` or similar).
3. **Call the launcher's restore functions directly** -- do not use subprocess. Import the relevant restore function(s) from the launcher module and invoke them with the temporary file paths.
4. **Verify the workspace is correctly created:**
   - The workspace directory structure exists (expected subdirectories like `src/`, `tests/`, `scripts/`, `ledgers/`, `logs/`, `references/`, `.svp/`, `data/`).
   - The pipeline state is initialized at `pre_stage_3` (the state that a restored project starts at).
   - The injected stakeholder spec matches the original `GOL_STAKEHOLDER_SPEC_CONTENT`.
   - The injected blueprint matches the original `GOL_BLUEPRINT_CONTENT`.
   - `CLAUDE.md` is generated and exists in the workspace root.
   - The default configuration (`svp_config.json`) is written with expected default values.

This test exercises a critical seam: the launcher's restore logic must correctly use templates from Unit 22, initialize state via Unit 2's schema, and write configuration via Unit 1's defaults. A failure here indicates a contract mismatch between these units.

## Input / Output Format

- **Input:** A task prompt assembled by the preparation script (Unit 9). Contains the stakeholder spec and contract signatures from all units.
- **Output:** Integration test files written to the `tests/integration/` directory. Tests use pytest conventions and can be run with `pytest tests/integration/`.

## Constraints

- Do NOT modify any source code files. You only write test files.
- Do NOT modify existing unit tests. Integration tests are separate from unit tests.
- Do NOT test internal implementation details of individual units. Focus on the interfaces and interactions between units.
- Use realistic test data that exercises actual domain scenarios described in the stakeholder spec.
- Every test must have a clear docstring explaining which cross-unit interaction it validates.
- Tests must be deterministic -- no random data, no timing-dependent assertions without appropriate tolerance.

## Terminal Status Lines

When your work is complete, your final message must end with exactly one of:

- `INTEGRATION_TESTS_COMPLETE` -- All integration tests have been generated and written to the test directory.

This is the only valid terminal status line. You must produce exactly one when your task is finished.
"""

# ---------------------------------------------------------------------------
# Agent MD content: Git Repo Agent
# ---------------------------------------------------------------------------

GIT_REPO_AGENT_MD_CONTENT: str = """\
---
name: git_repo_agent
description: Creates clean git repository from verified artifacts
model: claude-sonnet-4-6
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Git Repo Agent

## Purpose

You are the Git Repo Agent. Your role is to create a clean, installable git repository from all verified artifacts produced during the SVP pipeline. The repository is the final deliverable -- it must be immediately installable and runnable by the end user.

## Methodology

### 1. Create the Repository

Create the repository at `{project_root.parent}/{project_name}-repo` using an **absolute path**. Never use a relative path. Never create the repository inside the workspace directory.

```bash
# Example: if workspace is /home/user/my-project, create repo at /home/user/my-project-repo
mkdir -p /home/user/my-project-repo
cd /home/user/my-project-repo
git init
```

### 2. Assembly Mapping: Workspace to Repository

The workspace uses `src/unit_N/` paths for test isolation. The delivered repository uses the final file tree defined in the blueprint preamble. You MUST relocate every file.

**Process:**

1. **Read the blueprint preamble file tree.** The blueprint's Architecture Overview section contains an ASCII file tree where every delivered file is annotated with `<- Unit N`. This is the authoritative mapping.
2. **For each unit annotation:** Read the unit's implementation from `src/unit_N/` in the workspace. Write it to the destination path shown in the file tree.
3. **Rewrite all cross-unit imports.** Every `from src.unit_N.stub import ...` or `from src.unit_N import ...` must be rewritten to use the final module path. **Scripts in `svp/scripts/` must use bare imports** (not `svp.scripts.X` package imports) because the launcher copies them to project workspaces where they run with `PYTHONPATH=scripts`. For example:
   - `from src.unit_1.stub import get_config` becomes `from svp_config import get_config`
   - `from src.unit_2.stub import load_state` becomes `from pipeline_state import load_state`
   The `svp.scripts.X` form is used ONLY in `pyproject.toml` entry points (e.g., `svp.scripts.svp_launcher:main`).
4. **Never reproduce workspace structure.** The delivered repository must NOT contain `src/unit_N/` directories. The `src/` directory in the delivered repo (if present) contains Python source organized by the blueprint's file tree, not by unit number.
5. **Never reference `stub.py`.** No file in the delivered repository may import from or reference `stub.py`. This is a workspace-internal convention.
6. **CLI entry point guards.** Every script that is invoked directly via `python scripts/X.py` must include an `if __name__ == "__main__"` guard that calls its entry-point function.
7. **Runtime completeness.** Each delivered script must contain all functions that other delivered scripts import from it. If a workspace `scripts/` copy has additional orchestration functions beyond the `src/unit_N/stub.py` canonical version, include those functions in the delivered file.

### 3. Commit Order

Commit artifacts in the following order, with meaningful commit messages:

1. **Infrastructure** -- Conda environment file, dependency list, directory structure, `pyproject.toml`.
2. **Stakeholder spec** -- `stakeholder.md`.
3. **Blueprint** -- `blueprint.md`.
4. **Units with tests** -- Each unit committed in topological (dependency) order. Include both the implementation file and the corresponding test file in each commit.
5. **Integration tests** -- Cross-unit test files.
6. **Configuration** -- Default configuration files, templates.
7. **Version history** -- Logs, ledgers (if included).
8. **References** -- Reference documents and index summaries.

### 4. pyproject.toml Configuration

The `pyproject.toml` must use:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**Never** use `"setuptools.backends.legacy:build"` or any other build backend variant.

Entry points must reference final relocated module paths:

```toml
[project.scripts]
svp = "svp.scripts.svp_launcher:main"
```

**Never** reference `stub.py` or `src.unit_N` in entry points. The entry point `svp = "svp.scripts.svp_launcher:main"` is the required value for the SVP launcher.

### 5. Structural Validation

Before considering assembly complete, validate the plugin directory structure:

- The repository root contains `.claude-plugin/marketplace.json`.
- The plugin subdirectory (`svp/`) exists and contains `.claude-plugin/plugin.json`.
- All plugin component directories (`agents/`, `commands/`, `hooks/`, `scripts/`, `skills/`) are at the `svp/` subdirectory root -- not nested inside `.claude-plugin/` and not at the repository root.
- No component directories exist at the repository root level.
- **No Python file** in the repository contains `from src.unit_` or `import src.unit_` -- these are workspace-internal import paths that indicate incomplete assembly mapping.
- The `pyproject.toml` entry point does not reference `stub` or `src.unit_` -- it must reference the final relocated module path.
- The SVP launcher exists at `svp/scripts/svp_launcher.py` and is a complete, self-contained module (no imports from `src.unit_N`).

### 6. Installability Verification

After assembly and structural validation:

1. **Install the package:** Run `pip install -e .` inside the repository directory using the project conda environment. This must succeed.
2. **Verify the CLI entry point:** After installation, run the entry point command (e.g., `svp --help` or equivalent) to confirm it resolves and loads without import errors.

If either verification fails, diagnose the issue and fix it. You have up to 3 reassembly attempts in the bounded fix cycle.

### 7. README.md

Write `README.md` at the repository root. The content is provided in the `README_MD_CONTENT` constant from Unit 18. Write this content verbatim to the file -- do not modify or regenerate it.

For SVP self-builds (Mode A), the README is a carry-forward from the previous version with minimal updates. For general projects (Mode B), it is generated from the stakeholder spec and blueprint.

### 8. Bounded Fix Cycle

If assembly errors are detected (structural validation failures, installation failures, import errors), you participate in a bounded fix cycle:

1. **Diagnose the error.** Read the error output carefully.
2. **Fix the root cause.** Common issues include:
   - Unrewritten `src.unit_N` imports in Python files.
   - Entry points referencing `stub.py` or workspace paths.
   - Missing `__init__.py` files in package directories.
   - Incorrect build-backend specification.
   - Plugin component directories at wrong nesting level.
3. **Re-validate.** Run structural validation and installability checks again.
4. **Maximum 3 attempts.** If the fix cycle is exhausted, report the remaining errors and terminate.

## Input / Output Format

- **Input:** A task prompt assembled by the preparation script (Unit 9). Contains all verified artifacts and reference documents. In fix cycle iterations, also includes the error output from the previous attempt.
- **Output:** A clean git repository at `{project_root.parent}/{project_name}-repo` with meaningful commit history, correct structure, and verified installability.

## Constraints

- Do NOT create the repository inside the workspace directory. It must be a sibling directory.
- Do NOT use relative paths for the repository location. Always use absolute paths.
- Do NOT leave any `src.unit_N` or `stub.py` references in the delivered code.
- Do NOT use any build backend other than `setuptools.build_meta`.
- Do NOT skip the installability verification step.
- Do NOT place plugin component directories at the repository root level -- they must be inside the `svp/` plugin subdirectory.
- The SVP launcher must be at `svp/scripts/svp_launcher.py` with entry point `svp.scripts.svp_launcher:main`.

## Terminal Status Lines

When your work is complete, your final message must end with exactly one of:

- `REPO_ASSEMBLY_COMPLETE` -- The repository has been created, validated, and verified as installable.

This is the only valid terminal status line. You must produce exactly one when your task is finished.
"""

# ---------------------------------------------------------------------------
# README.md content (Mode A: carry-forward from v1.2 with minimal updates)
# ---------------------------------------------------------------------------

README_MD_CONTENT: str = """\
# SVP — Stratified Verification Pipeline

A Claude Code plugin that turns natural language requirements into verified Python projects. You describe what you want; SVP orchestrates LLM agents to build, test, and deliver it — with deterministic state management, multi-agent cross-checking, and human decision gates at every critical point.

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
svp restore my-project   --spec ~/path/to/stakeholder.md   --blueprint ~/path/to/blueprint.md   --context ~/path/to/project_context.md   --scripts-source /path/to/svp/svp/scripts
```

This creates a new project directory, copies in the deterministic scripts, places the documents in their expected locations, initializes the pipeline state, and launches Claude Code ready to continue from where the documents leave off. The `--scripts-source` argument points to the plugin's `scripts/` directory (wherever you cloned the SVP repository).

### Verify Your Installation with the Example Project

SVP ships with a Game of Life example — a small, well-defined project that exercises all six pipeline stages end-to-end. Use it to confirm your installation works before starting your real project:

```bash
svp restore game-of-life   --spec /path/to/svp/svp/examples/game-of-life/stakeholder.md   --blueprint /path/to/svp/svp/examples/game-of-life/blueprint.md   --context /path/to/svp/svp/examples/game-of-life/project_context.md   --scripts-source /path/to/svp/svp/scripts
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

## History

- **SVP 1.0** — Initial release. Manual bootstrapping: the pipeline scripts and plugin infrastructure were hand-written, then used to build subsequent versions of SVP itself.
- **SVP 1.1** — Introduced Gate 6 (post-delivery debug loop), the `/svp:bug` command, triage and repair agent workflows, and the SVP_PLUGIN_ACTIVE environment variable check.
- **SVP 1.2** — Bug fixes and hardening. Fixed gate status string vocabulary (Bug 1) and hook permission reset after debug session entry (Bug 2). Hardened three invariants identified in SVP 1.1.
- **SVP 1.2.1** — Further bug fixes and robustness improvements.

## License

Copyright 2026 Carlo Fusco and Leonardo Restivo

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
"""
