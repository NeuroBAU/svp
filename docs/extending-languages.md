# Extending SVP with a New Language

This guide walks you through adding support for a new programming language to SVP. The process uses SVP itself — you write a stakeholder specification describing the new language support, and SVP's agents build, test, and deliver the extension.

**Prerequisites:** You should be familiar with SVP's basic workflow (running a project through the pipeline) and with the target language you want to add (its test framework, package manager, quality tools, and project conventions).

---

## Overview

Adding a new language to SVP requires defining:

1. **Language registry entry** — metadata about the language (file extensions, test framework, directory conventions, quality tools)
2. **Toolchain defaults** — a JSON configuration file defining the environment manager, test commands, and quality gate commands
3. **Six dispatch table entries** — language-specific functions for each pipeline stage:

| Dispatch Table | Unit | Purpose |
|---------------|------|---------|
| `SIGNATURE_PARSERS` | Unit 9 | Parse function signatures from blueprint code blocks |
| `STUB_GENERATORS` | Unit 10 | Generate stub files with `NotImplementedError` bodies |
| `TEST_OUTPUT_PARSERS` | Unit 14 | Parse test framework output (pass/fail/error counts) |
| `QUALITY_RUNNERS` | Unit 15 | Run linter, formatter, type checker for quality gates |
| `PROJECT_ASSEMBLERS` | Unit 23 | Assemble the delivered repository in language-specific layout |
| `COMPLIANCE_SCANNERS` | Unit 28 | Verify delivered repo meets language-specific structural requirements |

The process has three phases: **get SVP running**, **build the extension**, and **validate and deliver**.

---

## Phase 1: Get SVP Running

### 1.1 Clone and Install

```bash
# Clone the SVP repository
git clone https://github.com/NeuroBAU/svp.git
cd svp

# Install the Claude Code plugin
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp

# Install the SVP launcher
pip install -e . --prefix ~/.local

# Verify
svp --help
```

If `svp --help` doesn't work, ensure `~/.local/bin` is on your PATH (see the README for OS-specific instructions).

### 1.2 Restore the Development Workspace

The repository contains the delivered code, but development happens in a **workspace** — a separate directory with the source stubs, specs, blueprint, and tests in their working layout. Create one from the repo:

```bash
# From the repo root
svp restore svp-workspace --repo .
```

This auto-discovers all artifacts from the repo's `docs/` directory and creates a workspace with the correct structure (`specs/`, `blueprint/`, `references/`, `scripts/`, `src/`, `tests/`). It also writes `.svp/sync_config.json` so that `sync_workspace.sh` knows where the repo is.

### 1.3 Verify the Baseline

Before making any changes, verify everything works:

```bash
cd svp-workspace

# Run all tests
pytest tests/ -v

# Run tests from the repo too (should match)
cd ../svp
pytest tests/ -v
```

All tests should pass with 0 failures and 0 skipped.

### 1.4 Run the Oracle (Optional but Recommended)

The oracle performs end-to-end validation of the delivered product. Running it before you start confirms the baseline is clean:

```bash
# From the workspace, resume the SVP session
svp

# Then invoke the oracle
/svp:oracle
```

Select a test project (e.g., GoL Python) and let the oracle run its dry run and green run. An ALL CLEAR result means the baseline is solid.

---

## Phase 2: Build the Language Extension

### 2.1 Start a New Project

From a clean directory (not inside the workspace), start a new SVP project:

```bash
svp new julia-svp-extension
```

The setup agent will guide you through a Socratic dialog. When asked about the project archetype, choose **Option E — SVP language extension self-build**. This tells SVP that the project's output is an updated version of SVP itself with new language support.

### 2.2 Write the Stakeholder Specification

The setup agent will help you define your requirements through conversation. The key topics to cover in your spec:

**Language identity:**
- Language name, file extension(s), display name
- Source directory convention (e.g., `src/` for Python, `R/` for R, `lib/` for Julia)
- Test directory convention (e.g., `tests/` for Python, `tests/testthat/` for R)

**Environment and toolchain:**
- Environment manager (conda, renv, or custom)
- How to create, activate, and install packages in the environment
- The `run_prefix` command template (e.g., `conda run -n {env_name}`)

**Test framework:**
- Which test framework to use (e.g., `Test.jl` for Julia, `testthat` for R)
- Test file naming pattern (e.g., `test_*.py`, `test-*.R`)
- How to run tests from the command line
- How to parse test output (what patterns indicate pass, fail, error, collection error)

**Quality tools:**
- Linter, formatter, type checker (or `"none"` if not applicable)
- How to invoke each tool from the command line
- Quality gate composition (which tools run at Gate A, B, C)

**Project structure:**
- How a delivered project should be laid out (directory structure, manifest files)
- Package manifest file (e.g., `pyproject.toml`, `DESCRIPTION`, `Project.toml`)
- Environment/dependency file (e.g., `environment.yml`, `renv.lock`)

**Use existing languages as templates.** The spec should reference the existing Python and R implementations as models. The Python entry in `LANGUAGE_REGISTRY` (Unit 2) and `python_conda_pytest.json` (toolchain defaults) are the most complete examples.

**Mixed-language projects.** Adding a new language also opens the door to mixed-language projects — for example, a Python application calling Julia for numerical computation, or a Julia GUI driving a Python ML backend. Mixed-language support requires additional work beyond the base language entry:

- **Bridge library:** Define how the two languages communicate at runtime. Python-R uses `rpy2` (Python calling R) and `reticulate` (R calling Python). For Julia, you might use `PyJulia`/`PythonCall.jl` (Python calling Julia) or `PyCall.jl` (Julia calling Python). Specify the bridge library in the `bridge_libraries` field of both language registry entries.
- **Cross-language stub generation:** When a unit in one language depends on a unit in another, the stub generator must produce stubs in the dependency's language, not the caller's. SVP already handles this (Bug S3-49) — your language's signature parser and stub generator will be invoked automatically for upstream dependencies written in your language.
- **Bridge test injection:** The test agent needs instructions for writing integration tests that exercise the cross-language bridge. These tests verify that data crosses the language boundary correctly (type conversions, error propagation, memory management).
- **Two-phase assembly:** Mixed projects are assembled in two phases — the primary language's project structure first, then the secondary language's files in a subdirectory. Your project assembler needs to handle both roles (primary and secondary).

Mixed-language support is selected as **Option D** in the setup dialog. If your spec only defines the standalone language (Option A/B equivalent), mixed-language projects with your new language won't be available until the bridge definitions are added. You can add mixed-language support in the same spec or as a follow-up extension.

### 2.3 Pipeline Build (Two Passes)

SVP self-builds use a two-pass architecture:

**Pass 1** generates the initial implementation:
- Stage 1: Spec review and approval
- Stage 2: Blueprint authoring (the blueprint author decomposes your spec into units)
- Stage 3: Test generation, stub generation, implementation (for each unit)
- Stage 4: Integration testing
- Stage 5: Repository assembly and delivery

**Pass 2** validates and refines:
- Carries forward the spec and blueprint from Pass 1
- Re-runs Stages 3-5 with the Pass 1 deliverable as the build tool
- This is the self-validation step: SVP builds itself using the version that includes your extension

The pipeline manages the two-pass transition automatically. Follow the orchestrator's prompts at each gate.

### 2.4 Interact with the Orchestrator

During the build, the orchestrator (Claude Code's main session) drives the pipeline. Key interaction patterns:

- **At decision gates:** Read the options carefully. The orchestrator presents explicit choices — pick the one that matches your intent.
- **If you see issues:** You can provide domain hints at any gate. The receiving agent evaluates your hint alongside the blueprint.
- **If stuck:** Use `/svp:help` to consult the Help Agent, which can formulate engineering-level suggestions from your domain observations.

---

## Phase 3: Fix Bugs

After delivery, you'll likely encounter bugs. SVP provides two mechanisms for fixing them:

### 3.1 The `/svp:bug` Command (Pipeline-Integrated)

For bugs found during normal pipeline operation (test failures, quality gate issues), use:

```
/svp:bug
```

This enters the post-delivery debug loop — a structured triage-diagnose-repair cycle managed by the pipeline. The triage agent classifies the bug, the diagnostic agent identifies root cause, and the repair agent applies the fix. Human gates at each step let you confirm the direction.

### 3.2 Break-Glass Protocol (Manual Bug Fixing)

When the pipeline machinery itself is broken (routing errors, state corruption, script bugs), the normal debug loop can't help. In this case, use the **break-glass protocol**:

1. Ask the orchestrator to **read CLAUDE.md** to refresh its memory on the protocol
2. Ask it to **enter plan mode** — this is mandatory (Rule 0: never fix without a plan)
3. The orchestrator diagnoses, plans fixes across spec/blueprint/code, presents the plan for your approval
4. After approval, it executes: applies code changes, runs tests, syncs repos
5. Always verify with `pytest` from **both** the workspace and the repo

The break-glass protocol is documented in CLAUDE.md under "Manual Bug-Fixing Protocol."

### 3.3 Oracle Validation

After fixing bugs, run the oracle to verify the extension works end-to-end:

```
/svp:oracle
```

For a language extension, you should create **oracle test projects** — small example projects in the new language that exercise the full pipeline path. Place them in `examples/`:

```
examples/
  hello-julia/
    oracle_manifest.json      # Oracle metadata
    oracle_trajectory.json    # Test trajectory config
    stakeholder_spec.md       # Small project spec
    blueprint_prose.md        # Blueprint for the test project
    blueprint_contracts.md    # Contracts for the test project
    project_context.md        # Project context
```

The `oracle_manifest.json` should specify:
```json
{
  "name": "Hello Julia",
  "description": "Minimal Julia project exercising the full pipeline",
  "archetype": "julia_project",
  "oracle_mode": "product",
  "languages": ["julia"],
  "key_paths": [
    "Julia environment setup",
    "Julia test execution",
    "Julia quality gates",
    "Julia project assembly"
  ]
}
```

Run the oracle with your test project selected. Iterate: fix bugs, re-run oracle, until you get **ALL CLEAR**.

---

## Phase 4: Use the Extended SVP

Once the oracle reports ALL CLEAR:

1. **Install the updated plugin** from the delivered repo:
   ```bash
   cd julia-svp-extension-repo
   claude plugin marketplace add "$(pwd)"
   claude plugin install svp@svp
   ```

2. **Start a new project** using the new language:
   ```bash
   svp new my-julia-project
   ```
   The setup agent will now offer your new language as an option in the archetype selection dialog.

---

## Reference: Existing Language Implementations

Use these as templates when writing your spec:

| Language | Registry Entry | Toolchain File | Key Files |
|----------|---------------|----------------|-----------|
| Python | `src/unit_2/stub.py` line 38 | `scripts/toolchain_defaults/python_conda_pytest.json` | `src/unit_9/stub.py` (parser), `src/unit_10/stub.py` (stubs), `src/unit_15/stub.py` (quality) |
| R | `src/unit_2/stub.py` line 101 | `scripts/toolchain_defaults/r_renv_testthat.json` | Same units, R-specific functions |

The stakeholder spec Section 40 (Language Framework) contains the complete specification for language extensibility.
