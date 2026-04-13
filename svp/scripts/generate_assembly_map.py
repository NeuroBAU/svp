"""Unit 23: Utility Agent Definitions and Assembly Dispatch.

Provides agent definition constants (git repo, checklist generation,
regression adaptation, oracle), project assembly functions for Python
and R, assembly map generation, and regression test import adaptation CLI.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

from svp_config import ARTIFACT_FILENAMES

# ---------------------------------------------------------------------------
# Agent definition constants
# ---------------------------------------------------------------------------

GIT_REPO_AGENT_DEFINITION: str = """\
# Git Repository Assembly Agent

## Role

You are the Git Repository Assembly Agent. Your job is to assemble the \
delivered repository from workspace source files using the assembly map, \
apply conventional commits, generate README and quality configuration, \
and ensure delivery compliance.

## Terminal Status

Your terminal status line must be exactly:

```
REPO_ASSEMBLY_COMPLETE
```

## Assembly Mapping Rules

- Read `.svp/assembly_map.json` to look up the source stub path for any \
delivered artifact. The map provides deployed-path → source-stub-path \
lookup via a single top-level key `"repo_to_workspace"`, whose values point \
at `src/unit_N/stub.py` files — the single source of truth for each unit. \
**(CHANGED IN 2.2 — Bug S3-111. Pre-S3-111 schema had a second \
`workspace_to_repo` direction, now removed: the relationship is many-to-one \
post-Bug-S3-98, which `Dict[str, str]` cannot represent.)**
- The map is NOT authoritative over HOW to assemble — actual assembly is \
driven by `regenerate_deployed_artifacts()` (agents, commands, hooks, \
skills) and `derive_scripts_from_stubs.py` (Python scripts). The map is \
consulted for source-location path lookup, not iteration.

## Commit Order

Follow conventional commits (https://www.conventionalcommits.org/):
1. `feat:` for new features
2. `fix:` for bug fixes
3. `docs:` for documentation changes
4. `chore:` for maintenance tasks
5. `refactor:` for code restructuring
6. `test:` for test changes
7. `style:` for formatting changes
8. `ci:` for CI configuration changes
9. `perf:` for performance improvements
10. `build:` for build system changes
11. Initial commit with project scaffold, then feature commits in \
dependency order.

## Delivery Compliance

- Verify all files pass quality gates before committing.
- Ensure `pyproject.toml` or `DESCRIPTION` is accurate.
- Verify entry points are configured if specified in profile.
- No stub sentinels remain in delivered code.

## README Generation

- Generate README.md with project name, description, installation \
instructions, usage examples, and license information.

## Quality Configuration Generation

- Generate quality tool configuration files matching the profile's \
quality settings (linter, formatter, type checker configs).

## Mixed Archetype Assembly (Bug S3-97)

When the project profile has `archetype: "mixed"`:

1. **Detect mixed archetype** — Read `profile["archetype"]`. If `"mixed"`, \
execute two-phase composition instead of single-language assembly.

2. **Phase 1 — Primary assembly** — Use the primary language's assembler \
(`PROJECT_ASSEMBLERS[profile["language"]["primary"]]`) to create the project \
root structure (e.g., `pyproject.toml` for Python, `DESCRIPTION` for R).

3. **Phase 2 — Secondary placement** — Create a `<secondary_language>/` \
subdirectory at the project root (e.g., `r/` if secondary is R). Place all \
secondary language source files there. Create `<secondary_language>/tests/` \
for secondary test files.

4. **Dual quality configs** — Generate quality tool configuration files for \
BOTH languages (e.g., `ruff.toml` for Python AND `.lintr` for R).

5. **Single environment.yml** — Generate one `environment.yml` at the project \
root listing dependencies for both languages and bridge libraries \
(e.g., rpy2 or reticulate).

6. **Constraints:**
   - Primary language owns root structure; secondary files never appear at root.
   - No cross-language import rewriting — bridge libraries use runtime discovery.
   - Entry points: primary is canonical; secondary documented as auxiliary.

## Bounded Fix Cycle

- If assembly fails, retry up to `iteration_limit` attempts.
- Each retry addresses the specific failure from the previous attempt.
- After exhausting retries, report failure with diagnostics.
"""

CHECKLIST_GENERATION_AGENT_DEFINITION: str = """\
# Checklist Generation Agent

## Role

You are the Checklist Generation Agent. Your job is to produce two \
checklists that seed the Stage 2 alignment and blueprint review agents.

## Terminal Status

Your terminal status line must be exactly:

```
CHECKLISTS_COMPLETE
```

## Outputs

1. **alignment_checker_checklist.md** -- A checklist for the blueprint \
alignment checker agent. Contains items to verify that the blueprint \
faithfully represents the stakeholder spec, with no omissions, \
contradictions, or scope drift.

2. **blueprint_author_checklist.md** -- A checklist for the blueprint \
author agent. Contains items to verify structural completeness, \
contract granularity, dependency correctness, and pattern catalog \
cross-references.

## Checklist Seed Content

Each checklist must include:
- Items derived from the approved stakeholder spec
- Items derived from lessons learned (if available)
- Items derived from regression test inventory (if available)
- Language-specific items based on the project's language configuration
"""

REGRESSION_ADAPTATION_AGENT_DEFINITION: str = """\
# Regression Test Adaptation Agent

## Role

You are the Regression Test Adaptation Agent. Your job is to adapt \
carry-forward regression tests to work with the current project's \
module structure by rewriting imports and flagging behavioral changes.

## Terminal Status

Your terminal status line must be exactly one of:

```
ADAPTATION_COMPLETE
```

or, if manual review is needed:

```
ADAPTATION_NEEDS_REVIEW
```

## Import Rewrites

- Read the assembly map and regression test import map.
- Rewrite `from X import Y` statements to use new module paths.
- Rewrite `import X` statements to use new module paths.
- Rewrite `@patch("X.Y")` and `patch("X.Y")` decorators/calls.
- For R files: rewrite `source()` path references.

## Behavioral Change Flagging

- When a regression test exercises behavior that has changed between \
versions, flag it for human review rather than silently adapting.
- Produce a summary of flagged changes with explanations.
"""

ORACLE_AGENT_DEFINITION: str = """\
# Oracle Agent

## Role

You are the Oracle Agent. You perform end-to-end validation of the \
delivered product using real test projects. You operate in two modes: \
E-mode (product testing) and F-mode (machinery testing).

## Terminal Status

Your terminal status line must be exactly one of:

```
ORACLE_DRY_RUN_COMPLETE
```
```
ORACLE_FIX_APPLIED
```
```
ORACLE_ALL_CLEAR
```
```
ORACLE_HUMAN_ABORT
```

## Dual Mode

- **E-mode (product testing):** Tests the delivered product against \
stakeholder requirements using test projects from `examples/` and `docs/`.
- **F-mode (machinery testing):** Tests the SVP pipeline machinery itself \
using self-build test projects.

## Four-Phase Structure

1. **dry_run:** Analyze the test project, plan trajectory, identify risks. \
Produce diagnostic map entries. Status: `ORACLE_DRY_RUN_COMPLETE`.
2. **gate_a:** Human reviews the planned trajectory. Response: \
`APPROVE TRAJECTORY` or `MODIFY TRAJECTORY` or `ABORT`.
3. **green_run:** Execute the test project through the pipeline. Run tests, \
verify outputs, identify bugs. You are READ-ONLY during green_run — all \
fixes go through `/svp:bug` after Gate B approval. If bugs found, produce \
fix plan and signal `ORACLE_FIX_APPLIED`. If no bugs: `ORACLE_ALL_CLEAR`.
4. **gate_b:** Human reviews the fix plan. Response: `APPROVE FIX` or \
`ABORT`. After fix: `ORACLE_FIX_APPLIED`. After abort: `ORACLE_HUMAN_ABORT`.

## Oracle Phase Transitions

- `dry_run` -> `gate_a`: on `ORACLE_DRY_RUN_COMPLETE`, routing sets \
`oracle_phase = "gate_a"`.
- `gate_a` -> `green_run`: on `APPROVE TRAJECTORY`, routing sets \
`oracle_phase = "green_run"`.
- `green_run` -> `gate_b`: oracle signals fix plan, routing sets \
`oracle_phase = "gate_b"`.
- `gate_b` -> `exit`: on `APPROVE FIX` or `ABORT`, routing sets \
`oracle_phase = "exit"`.
- `green_run` -> `exit`: on `ORACLE_ALL_CLEAR`, routing sets \
`oracle_phase = "exit"` directly.

## Multi-Turn Session

The oracle agent invocation spans `green_run` + Gate B as a multi-turn \
session: the oracle's green run invocation continues through the fix plan \
review gate, maintaining session state.

## Surrogate Human Protocol

For internal `/svp:bug` calls during green run:
- Auto-respond at Gate 6.0 (authorize debug session)
- Auto-respond at Gate 6.1 (triage confirmation)
- Auto-respond at Gate 6.2 (repair approval)

## Read-Only Constraint (Bug S3-95)

During green_run, you are READ-ONLY. You MUST NOT use Edit, Write, or Bash \
to modify any workspace files except your own oracle artifacts:
- `.svp/oracle_run_ledger.json` (your run ledger)
- `.svp/oracle_diagnostic_map.json` (your diagnostic map)
- `.svp/oracle_trajectory.json` (your trajectory)

You MUST NOT modify source code, specs, blueprints, tests, lessons learned, \
or deployed artifacts. This is enforced by a PreToolUse hook — attempts \
will be blocked with exit code 2.

When you find a bug: produce `ORACLE_FIX_APPLIED` as your terminal status \
with a fix plan in your output. The routing script handles Gate B and \
`/svp:bug` routing. You do NOT fix bugs yourself.

## Context Budget Management

- Selective analysis with reporting.
- Prioritize high-risk areas identified during dry run.

## Run Ledger

Cross-invocation memory stored at `.svp/oracle_run_ledger.json`. \
Each entry contains:
- `run_number` (int): sequential run number
- `exit_reason` (str): `"all_clear"`, `"fix_applied"`, or `"human_abort"`
- `abort_phase` (str or null): `"gate_a"` or `"gate_b"`, present only \
on abort
- `trajectory_summary` (str): compact description of planned trajectory
- `discoveries` (list of dicts): issues found with root causes, \
classifications, affected units
- `fix_targets` (list of str): units/files targeted for repair
- `root_causes_found` (list of str): root causes identified
- `root_causes_resolved` (list of str): root causes fixed and verified

## Diagnostic Map

Stored at `.svp/oracle_diagnostic_map.json`. Each entry contains:
- `event_id` (str): unique label, e.g. `"stage3.unit_foo.gate_a"`
- `classification` (str): `"PASS"`, `"FAIL"`, or `"WARN"`
- `observation` (str): what the oracle actually observed
- `expected` (str): what the spec says should happen
- `affected_artifact` (str): file path or artifact identifier affected

## Bounds

- Fix verification: 2 attempts max per bug.
- MODIFY TRAJECTORY: 3 per invocation.
"""


# ---------------------------------------------------------------------------
# Assembly helper functions
# ---------------------------------------------------------------------------


def _get_project_name(
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
    fallback: str = "",
) -> str:
    """Extract project name from profile or assembly config."""
    # Check assembly_config first for explicit project_name
    if "project_name" in assembly_config:
        return assembly_config["project_name"]
    # Check profile for name
    if "name" in profile:
        return profile["name"]
    # Check profile for project_name
    if "project_name" in profile:
        return profile["project_name"]
    return fallback


def _backup_existing(target: Path) -> None:
    """Rename existing directory to .bak.YYYYMMDD-HHMMSS."""
    if target.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{target.name}.bak.{timestamp}"
        backup_path = target.parent / backup_name
        target.rename(backup_path)


def _write_pyproject_toml(
    repo_dir: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
    project_name: str,
) -> None:
    """Generate pyproject.toml with project metadata and dependencies."""
    python_delivery = profile.get("delivery", {}).get("python", {})
    entry_points_enabled = python_delivery.get("entry_points", False)

    content_lines = [
        "[build-system]",
        'requires = ["setuptools>=61.0"]',
        'build-backend = "setuptools.build_meta"',
        "",
        "[project]",
        f'name = "{project_name}"',
        'version = "0.1.0"',
        f'description = "{assembly_config.get("description", "")}"',
        'requires-python = ">=3.11"',
        "dependencies = []",
    ]

    if entry_points_enabled:
        content_lines.extend(
            [
                "",
                "[project.scripts]",
            ]
        )
        ep_config = python_delivery.get("entry_point_config", {})
        if ep_config:
            for name, target in ep_config.items():
                content_lines.append(f'{name} = "{target}"')
        else:
            content_lines.append(f'{project_name} = "{project_name}:main"')

    content_lines.append("")
    (repo_dir / "pyproject.toml").write_text("\n".join(content_lines))


def assemble_python_project(
    project_root: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
) -> Path:
    """Assemble a Python project repository.

    Creates target directory at {project_root.parent}/{project_name}-repo.
    Renames existing to .bak.YYYYMMDD-HHMMSS.
    Generates pyproject.toml with project metadata, dependencies, entry points.
    Source layout per profile["delivery"]["python"]["source_layout"].
    Returns path to created repository.
    """
    project_name = _get_project_name(profile, assembly_config, project_root.name)
    repo_dir = project_root.parent / f"{project_name}-repo"

    # Back up existing repo directory
    _backup_existing(repo_dir)

    # Create repo directory
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Read source layout from profile
    python_delivery = profile.get("delivery", {}).get("python", {})
    source_layout = python_delivery.get("source_layout", "conventional")

    # Create layout-specific structure
    package_name = project_name.replace("-", "_").replace(" ", "_")

    if source_layout == "conventional":
        # src/packagename/ layout
        src_pkg_dir = repo_dir / "src" / package_name
        src_pkg_dir.mkdir(parents=True, exist_ok=True)
        (src_pkg_dir / "__init__.py").write_text("")
    elif source_layout == "flat":
        # packagename/ layout
        pkg_dir = repo_dir / package_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "__init__.py").write_text("")
    elif source_layout == "svp_native":
        # scripts/ layout
        scripts_dir = repo_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Default to conventional
        src_pkg_dir = repo_dir / "src" / package_name
        src_pkg_dir.mkdir(parents=True, exist_ok=True)
        (src_pkg_dir / "__init__.py").write_text("")

    # Generate pyproject.toml
    _write_pyproject_toml(repo_dir, profile, assembly_config, project_name)

    return repo_dir


def assemble_r_project(
    project_root: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
) -> Path:
    """Assemble an R package repository.

    Creates R package structure: R/, man/, tests/testthat/.
    Generates DESCRIPTION, NAMESPACE.
    Returns path to created repository.
    """
    project_name = _get_project_name(profile, assembly_config, project_root.name)
    repo_dir = project_root.parent / f"{project_name}-repo"

    # Back up existing repo directory
    _backup_existing(repo_dir)

    # Create repo directory
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create R package directories
    (repo_dir / "R").mkdir(parents=True, exist_ok=True)
    (repo_dir / "man").mkdir(parents=True, exist_ok=True)
    (repo_dir / "tests" / "testthat").mkdir(parents=True, exist_ok=True)

    # Generate DESCRIPTION
    r_delivery = profile.get("delivery", {}).get("r", {})
    description_lines = [
        f"Package: {project_name.replace('-', '.')}",
        "Type: Package",
        f"Title: {assembly_config.get('description', project_name)}",
        "Version: 0.1.0",
        f"Author: {assembly_config.get('author', 'Unknown')}",
        f"Maintainer: {assembly_config.get('author', 'Unknown')} <unknown@example.com>",
        f"Description: {assembly_config.get('description', 'An R package.')}",
        "License: MIT + file LICENSE",
        "Encoding: UTF-8",
        "LazyData: true",
    ]

    # Add roxygen2 if configured
    r_quality = profile.get("quality", {}).get("r", {})
    if r_delivery.get("roxygen2", False) or assembly_config.get("roxygen2", False):
        description_lines.append("RoxygenNote: 7.2.3")

    description_lines.append("")
    (repo_dir / "DESCRIPTION").write_text("\n".join(description_lines))

    # Generate NAMESPACE
    namespace_content = (
        "# Generated by roxygen2: do not edit by hand\n\n"
        'exportPattern("^[[:alpha:]]")\n'
    )
    (repo_dir / "NAMESPACE").write_text(namespace_content)

    # Generate testthat.R in tests/
    pkg_r_name = project_name.replace("-", ".")
    testthat_r = (
        f'library(testthat)\nlibrary({pkg_r_name})\n\ntest_check("{pkg_r_name}")\n'
    )
    (repo_dir / "tests" / "testthat.R").write_text(testthat_r)

    return repo_dir


def assemble_plugin_project(
    project_root: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
) -> Path:
    """Assemble a Claude Code plugin repository.

    Creates plugin directory structure: repo root with .claude-plugin/
    marketplace.json, plugin subdirectory with .claude-plugin/plugin.json,
    agents/, commands/, skills/, hooks/, scripts/.
    Returns path to created repository.

    (Bug S3-90: PROJECT_ASSEMBLERS must have claude_code_plugin entry per
    spec Section 35.6 and Section 40.7.9.)
    """
    project_name = _get_project_name(profile, assembly_config, project_root.name)
    repo_dir = project_root.parent / f"{project_name}-repo"

    # Back up existing repo directory
    _backup_existing(repo_dir)

    # Create repo directory
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Root-level marketplace catalog directory
    (repo_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)

    # Plugin subdirectory structure (spec Section 40.7.9, Section 1.4)
    plugin_name = project_name.replace("_", "-")
    plugin_dir = repo_dir / plugin_name

    (plugin_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "agents").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "commands").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "skills").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "hooks").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "scripts").mkdir(parents=True, exist_ok=True)

    # Python source directory for plugin Python modules
    (plugin_dir / "strategies").mkdir(parents=True, exist_ok=True)

    return repo_dir


def assemble_mixed_project(
    project_root: Path,
    profile: Dict[str, Any],
    assembly_config: Dict[str, Any],
) -> Path:
    """Assemble a mixed-language project repository (Bug S3-97).

    Two-phase composition per spec Section 40.6.4:
    Phase 1: Call primary language assembler to create root structure.
    Phase 2: Create <secondary_language>/ subdirectory for secondary source
    files and <secondary_language>/tests/ for secondary test files.
    Generate quality configs for both languages.
    Single environment.yml with both languages' dependencies and bridge libraries.
    Returns path to created repository.
    """
    primary_language = profile.get("language", {}).get("primary", "python")
    secondary_language = profile.get("language", {}).get("secondary")

    if not secondary_language:
        raise ValueError(
            "Mixed archetype requires profile['language']['secondary'] to be set"
        )

    # Phase 1: Create root structure using primary assembler
    primary_assembler = PROJECT_ASSEMBLERS.get(primary_language)
    if primary_assembler is None:
        raise ValueError(
            f"No assembler registered for primary language: {primary_language}"
        )
    repo_dir = primary_assembler(project_root, profile, assembly_config)

    # Phase 2: Create secondary language subdirectory
    secondary_dir = repo_dir / secondary_language
    secondary_dir.mkdir(parents=True, exist_ok=True)

    # Secondary tests directory
    secondary_tests_dir = secondary_dir / "tests"
    secondary_tests_dir.mkdir(parents=True, exist_ok=True)

    return repo_dir


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

PROJECT_ASSEMBLERS: Dict[
    str, Callable[[Path, Dict[str, Any], Dict[str, Any]], Path]
] = {
    "python": assemble_python_project,
    "r": assemble_r_project,
    "claude_code_plugin": assemble_plugin_project,
    "mixed": assemble_mixed_project,
}


# ---------------------------------------------------------------------------
# Bug S3-51/S3-52: Plugin component assembly
# ---------------------------------------------------------------------------


def assemble_plugin_components(repo_dir: Path, profile: Dict[str, Any]) -> None:
    """Assemble plugin manifests and component directories for Claude Code plugins.

    Creates .claude-plugin/ directories with manifests and extracts
    agent/command/hook/skill definitions from workspace units into the
    delivered repo's svp/ subdirectory.
    """
    plugin_subdir = repo_dir / "svp"
    plugin_subdir.mkdir(parents=True, exist_ok=True)

    # --- Plugin manifests (Bug S3-51) ---
    from structural_check import generate_marketplace_json, generate_plugin_json

    # Root-level marketplace.json
    marketplace_dir = repo_dir / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text(
        generate_marketplace_json(profile) + "\n"
    )

    # Plugin-level plugin.json
    plugin_manifest_dir = plugin_subdir / ".claude-plugin"
    plugin_manifest_dir.mkdir(parents=True, exist_ok=True)
    (plugin_manifest_dir / "plugin.json").write_text(
        generate_plugin_json(profile) + "\n"
    )

    # --- Agent definitions (Bug S3-52) ---
    agents_dir = plugin_subdir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    from setup_agent import SETUP_AGENT_DEFINITION
    from blueprint_checker import BLUEPRINT_CHECKER_DEFINITION
    from construction_agents import (
        BLUEPRINT_AUTHOR_DEFINITION,
        BLUEPRINT_REVIEWER_DEFINITION,
        COVERAGE_REVIEW_AGENT_DEFINITION,
        IMPLEMENTATION_AGENT_DEFINITION,
        INTEGRATION_TEST_AUTHOR_DEFINITION,
        STAKEHOLDER_DIALOG_DEFINITION,
        STAKEHOLDER_REVIEWER_DEFINITION,
        TEST_AGENT_DEFINITION,
    )
    from diagnostic_agents import DIAGNOSTIC_AGENT_DEFINITION, REDO_AGENT_DEFINITION
    from support_agents import (
        HELP_AGENT_DEFINITION,
        HINT_AGENT_DEFINITION,
        REFERENCE_INDEXING_AGENT_DEFINITION,
    )
    from debug_agents import BUG_TRIAGE_AGENT_DEFINITION, REPAIR_AGENT_DEFINITION

    agent_defs = {
        "setup_agent.md": SETUP_AGENT_DEFINITION,
        "blueprint_checker.md": BLUEPRINT_CHECKER_DEFINITION,
        "stakeholder_dialog.md": STAKEHOLDER_DIALOG_DEFINITION,
        "stakeholder_reviewer.md": STAKEHOLDER_REVIEWER_DEFINITION,
        "blueprint_author.md": BLUEPRINT_AUTHOR_DEFINITION,
        "blueprint_reviewer.md": BLUEPRINT_REVIEWER_DEFINITION,
        "test_agent.md": TEST_AGENT_DEFINITION,
        "implementation_agent.md": IMPLEMENTATION_AGENT_DEFINITION,
        "coverage_review_agent.md": COVERAGE_REVIEW_AGENT_DEFINITION,
        "integration_test_author.md": INTEGRATION_TEST_AUTHOR_DEFINITION,
        "diagnostic_agent.md": DIAGNOSTIC_AGENT_DEFINITION,
        "redo_agent.md": REDO_AGENT_DEFINITION,
        "help_agent.md": HELP_AGENT_DEFINITION,
        "hint_agent.md": HINT_AGENT_DEFINITION,
        "reference_indexing.md": REFERENCE_INDEXING_AGENT_DEFINITION,
        "git_repo_agent.md": GIT_REPO_AGENT_DEFINITION,
        "checklist_generation.md": CHECKLIST_GENERATION_AGENT_DEFINITION,
        "regression_adaptation.md": REGRESSION_ADAPTATION_AGENT_DEFINITION,
        "oracle_agent.md": ORACLE_AGENT_DEFINITION,
        "bug_triage_agent.md": BUG_TRIAGE_AGENT_DEFINITION,
        "repair_agent.md": REPAIR_AGENT_DEFINITION,
    }

    # Bug S3-58: inject YAML frontmatter (Claude Code requires name + description)
    agent_models = profile.get("pipeline", {}).get("agent_models", {})
    # Map filename stems to profile agent_models keys
    _agent_model_keys = {
        "setup_agent": "setup_agent",
        "blueprint_checker": "blueprint_checker",
        "stakeholder_dialog": "stakeholder_dialog",
        "stakeholder_reviewer": "stakeholder_reviewer",
        "blueprint_author": "blueprint_author",
        "blueprint_reviewer": "blueprint_reviewer",
        "test_agent": "test_agent",
        "implementation_agent": "implementation_agent",
        "coverage_review_agent": "coverage_review",
        "integration_test_author": "integration_test_author",
        "diagnostic_agent": "diagnostic_agent",
        "redo_agent": "redo_agent",
        "help_agent": "help_agent",
        "hint_agent": "hint_agent",
        "reference_indexing": "reference_indexing",
        "git_repo_agent": "git_repo_agent",
        "checklist_generation": "checklist_generation",
        "regression_adaptation": "regression_adaptation",
        "oracle_agent": "oracle_agent",
        "bug_triage_agent": "bug_triage",
        "repair_agent": "repair_agent",
    }

    for filename, content in agent_defs.items():
        stem = filename.replace(".md", "")
        model_key = _agent_model_keys.get(stem, stem)
        model = agent_models.get(model_key, "claude-sonnet-4-6")
        # Extract description from first paragraph after the heading
        desc_line = ""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                desc_line = stripped[:120]
                break
        name = stem.replace("_", "-")
        frontmatter = (
            f"---\n"
            f"name: {name}\n"
            f"description: {desc_line}\n"
            f"model: {model}\n"
            f"---\n\n"
        )
        (agents_dir / filename).write_text(frontmatter + content)

    # --- Command definitions (Bug S3-52) ---
    commands_dir = plugin_subdir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    from slash_commands import COMMAND_DEFINITIONS

    for cmd_name, content in COMMAND_DEFINITIONS.items():
        (commands_dir / f"{cmd_name}.md").write_text(content)

    # --- Hook configurations (Bug S3-52) ---
    hooks_dir = plugin_subdir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    from hooks import (
        generate_hooks_json,
        generate_monitoring_reminder_sh,
        generate_non_svp_protection_sh,
        generate_stub_sentinel_check_sh,
        generate_write_authorization_sh,
    )

    (hooks_dir / "hooks.json").write_text(generate_hooks_json() + "\n")
    (hooks_dir / "write_authorization.sh").write_text(
        generate_write_authorization_sh()
    )
    (hooks_dir / "non_svp_protection.sh").write_text(
        generate_non_svp_protection_sh()
    )
    (hooks_dir / "stub_sentinel_check.sh").write_text(
        generate_stub_sentinel_check_sh()
    )
    (hooks_dir / "monitoring_reminder.sh").write_text(
        generate_monitoring_reminder_sh()
    )

    # Make hook scripts executable
    for sh_file in hooks_dir.glob("*.sh"):
        sh_file.chmod(0o755)

    # --- Skill definitions (Bug S3-52) ---
    skill_dir = plugin_subdir / "skills" / "orchestration"
    skill_dir.mkdir(parents=True, exist_ok=True)

    from orchestration_skill import ORCHESTRATION_SKILL

    (skill_dir / "SKILL.md").write_text(ORCHESTRATION_SKILL)

    # --- Bug S3-60: Package init file for svp.scripts imports ---
    scripts_dir = plugin_subdir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    init_file = scripts_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")


# ---------------------------------------------------------------------------
# SVP workspace artifact assembly (Bug S3-99)
# ---------------------------------------------------------------------------


def assemble_svp_workspace_artifacts(
    repo_dir: Path,
    workspace_root: Path,
    project_name: str,
) -> Dict[str, int]:
    """Assemble SVP workspace carry-over artifacts for E/F self-build repos.

    Called during Stage 5 assembly when is_svp_build is true.
    Writes workspace management files to the repo so that future passes
    can recreate workspaces via restore_project().

    Normal (A-D) projects do NOT call this — their repos stay clean.
    """
    from svp_launcher import CLAUDE_MD_TEMPLATE, CLAUDE_MD_SVP_ADDENDUM

    counts: Dict[str, int] = {"files": 0}

    # Full CLAUDE.md (Tier 1 + Tier 2)
    claude_content = CLAUDE_MD_TEMPLATE.format(project_name=project_name)
    claude_content += CLAUDE_MD_SVP_ADDENDUM
    (repo_dir / "CLAUDE.md").write_text(claude_content, encoding="utf-8")
    counts["files"] += 1

    # sync_workspace.sh
    sync_src = workspace_root / "sync_workspace.sh"
    if sync_src.is_file():
        import shutil

        shutil.copy2(sync_src, repo_dir / "sync_workspace.sh")
        counts["files"] += 1

    # examples/ directory (test projects for oracle)
    examples_src = workspace_root / "examples"
    if examples_src.is_dir():
        import shutil

        examples_dst = repo_dir / "examples"
        if examples_dst.exists():
            shutil.rmtree(examples_dst)
        shutil.copytree(str(examples_src), str(examples_dst))
        counts["files"] += 1

    # references/ directory → docs/references/ (consolidated repo layout)
    refs_src = workspace_root / "references"
    if refs_src.is_dir():
        import shutil

        refs_dst = repo_dir / "docs" / "references"
        if refs_dst.exists():
            shutil.rmtree(refs_dst)
        refs_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(refs_src), str(refs_dst))
        counts["files"] += 1

    # project_context.md
    ctx_src = workspace_root / "project_context.md"
    if ctx_src.is_file():
        import shutil

        shutil.copy2(ctx_src, repo_dir / "project_context.md")
        counts["files"] += 1

    # ruff.toml
    ruff_src = workspace_root / "ruff.toml"
    if ruff_src.is_file():
        import shutil

        shutil.copy2(ruff_src, repo_dir / "ruff.toml")
        counts["files"] += 1

    return counts


# ---------------------------------------------------------------------------
# Deployed artifact regeneration (Bug S3-80)
# ---------------------------------------------------------------------------


def regenerate_deployed_artifacts(repo_dir: Path) -> Dict[str, int]:
    """Regenerate deployed plugin artifacts from source Unit definitions.

    Re-derives command, agent, hook, and skill .md files from their source
    Unit constants and writes them to the repo's svp/ directory.  Called by
    sync_workspace.sh after source sync to prevent stale deployed artifacts.

    Skips manifests (.claude-plugin/) as these contain metadata, not
    behavioral content that Claude Code interprets for decision-making.

    Returns a dict with counts of regenerated files per category.
    """
    import json as _json

    plugin_subdir = repo_dir / "svp"
    if not plugin_subdir.is_dir():
        return {"commands": 0, "agents": 0, "hooks": 0, "skills": 0}

    counts: Dict[str, int] = {"commands": 0, "agents": 0, "hooks": 0, "skills": 0}

    # --- Command definitions (from Unit 25) ---
    commands_dir = plugin_subdir / "commands"
    if commands_dir.is_dir():
        from slash_commands import COMMAND_DEFINITIONS

        for cmd_name, content in COMMAND_DEFINITIONS.items():
            (commands_dir / f"{cmd_name}.md").write_text(content)
            counts["commands"] += 1

    # --- Orchestration skill (from Unit 26) ---
    skill_dir = plugin_subdir / "skills" / "orchestration"
    if skill_dir.is_dir():
        from orchestration_skill import ORCHESTRATION_SKILL

        (skill_dir / "SKILL.md").write_text(ORCHESTRATION_SKILL)
        counts["skills"] += 1

    # --- Agent definitions (from Units 18-24) ---
    agents_dir = plugin_subdir / "agents"
    if agents_dir.is_dir():
        from setup_agent import SETUP_AGENT_DEFINITION
        from blueprint_checker import BLUEPRINT_CHECKER_DEFINITION
        from construction_agents import (
            BLUEPRINT_AUTHOR_DEFINITION,
            BLUEPRINT_REVIEWER_DEFINITION,
            COVERAGE_REVIEW_AGENT_DEFINITION,
            IMPLEMENTATION_AGENT_DEFINITION,
            INTEGRATION_TEST_AUTHOR_DEFINITION,
            STAKEHOLDER_DIALOG_DEFINITION,
            STAKEHOLDER_REVIEWER_DEFINITION,
            TEST_AGENT_DEFINITION,
        )
        from diagnostic_agents import DIAGNOSTIC_AGENT_DEFINITION, REDO_AGENT_DEFINITION
        from support_agents import (
            HELP_AGENT_DEFINITION,
            HINT_AGENT_DEFINITION,
            REFERENCE_INDEXING_AGENT_DEFINITION,
        )
        from debug_agents import BUG_TRIAGE_AGENT_DEFINITION, REPAIR_AGENT_DEFINITION

        agent_defs = {
            "setup_agent.md": SETUP_AGENT_DEFINITION,
            "blueprint_checker.md": BLUEPRINT_CHECKER_DEFINITION,
            "stakeholder_dialog.md": STAKEHOLDER_DIALOG_DEFINITION,
            "stakeholder_reviewer.md": STAKEHOLDER_REVIEWER_DEFINITION,
            "blueprint_author.md": BLUEPRINT_AUTHOR_DEFINITION,
            "blueprint_reviewer.md": BLUEPRINT_REVIEWER_DEFINITION,
            "test_agent.md": TEST_AGENT_DEFINITION,
            "implementation_agent.md": IMPLEMENTATION_AGENT_DEFINITION,
            "coverage_review_agent.md": COVERAGE_REVIEW_AGENT_DEFINITION,
            "integration_test_author.md": INTEGRATION_TEST_AUTHOR_DEFINITION,
            "diagnostic_agent.md": DIAGNOSTIC_AGENT_DEFINITION,
            "redo_agent.md": REDO_AGENT_DEFINITION,
            "help_agent.md": HELP_AGENT_DEFINITION,
            "hint_agent.md": HINT_AGENT_DEFINITION,
            "reference_indexing.md": REFERENCE_INDEXING_AGENT_DEFINITION,
            "git_repo_agent.md": GIT_REPO_AGENT_DEFINITION,
            "checklist_generation.md": CHECKLIST_GENERATION_AGENT_DEFINITION,
            "regression_adaptation.md": REGRESSION_ADAPTATION_AGENT_DEFINITION,
            "oracle_agent.md": ORACLE_AGENT_DEFINITION,
            "bug_triage_agent.md": BUG_TRIAGE_AGENT_DEFINITION,
            "repair_agent.md": REPAIR_AGENT_DEFINITION,
        }

        # Read agent models from profile
        profile_path = repo_dir / "project_profile.json"
        agent_models: Dict[str, str] = {}
        if profile_path.is_file():
            try:
                profile = _json.loads(profile_path.read_text(encoding="utf-8"))
                agent_models = profile.get("pipeline", {}).get("agent_models", {})
            except (ValueError, OSError):
                pass

        _agent_model_keys = {
            "setup_agent": "setup_agent",
            "blueprint_checker": "blueprint_checker",
            "stakeholder_dialog": "stakeholder_dialog",
            "stakeholder_reviewer": "stakeholder_reviewer",
            "blueprint_author": "blueprint_author",
            "blueprint_reviewer": "blueprint_reviewer",
            "test_agent": "test_agent",
            "implementation_agent": "implementation_agent",
            "coverage_review_agent": "coverage_review",
            "integration_test_author": "integration_test_author",
            "diagnostic_agent": "diagnostic_agent",
            "redo_agent": "redo_agent",
            "help_agent": "help_agent",
            "hint_agent": "hint_agent",
            "reference_indexing": "reference_indexing",
            "git_repo_agent": "git_repo_agent",
            "checklist_generation": "checklist_generation",
            "regression_adaptation": "regression_adaptation",
            "oracle_agent": "oracle_agent",
            "bug_triage_agent": "bug_triage",
            "repair_agent": "repair_agent",
        }

        for filename, content in agent_defs.items():
            stem = filename.replace(".md", "")
            model_key = _agent_model_keys.get(stem, stem)
            model = agent_models.get(model_key, "claude-sonnet-4-6")
            desc_line = ""
            for line in content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                    desc_line = stripped[:120]
                    break
            name = stem.replace("_", "-")
            frontmatter = (
                f"---\n"
                f"name: {name}\n"
                f"description: {desc_line}\n"
                f"model: {model}\n"
                f"---\n\n"
            )
            (agents_dir / filename).write_text(frontmatter + content)
            counts["agents"] += 1

    # --- Hook configurations (from Unit 17) ---
    hooks_dir = plugin_subdir / "hooks"
    if hooks_dir.is_dir():
        from hooks import (
            generate_hooks_json,
            generate_monitoring_reminder_sh,
            generate_non_svp_protection_sh,
            generate_stub_sentinel_check_sh,
            generate_write_authorization_sh,
        )

        (hooks_dir / "hooks.json").write_text(generate_hooks_json() + "\n")
        (hooks_dir / "write_authorization.sh").write_text(generate_write_authorization_sh())
        (hooks_dir / "non_svp_protection.sh").write_text(generate_non_svp_protection_sh())
        (hooks_dir / "stub_sentinel_check.sh").write_text(generate_stub_sentinel_check_sh())
        (hooks_dir / "monitoring_reminder.sh").write_text(generate_monitoring_reminder_sh())
        for sh_file in hooks_dir.glob("*.sh"):
            sh_file.chmod(0o755)
        counts["hooks"] = 5

    return counts


# ---------------------------------------------------------------------------
# Assembly map generation
# ---------------------------------------------------------------------------


def _detect_indent_unit(lines: List[str]) -> int:
    """Detect the indentation unit used in a file tree.

    Returns the number of spaces per indentation level.
    Defaults to 2 if detection fails.
    """
    # Check if pipe-tree format is used
    for line in lines:
        if "|--" in line or "+--" in line:
            return 4  # Pipe-tree uses 4-char groups

    # For space-indented, find the smallest non-zero indent
    min_indent = None
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        # Skip lines that are annotations only
        if "<-" in stripped:
            stripped = stripped[: stripped.index("<-")].rstrip()
        lstripped = stripped.lstrip()
        leading = len(stripped) - len(lstripped)
        if leading > 0:
            if min_indent is None or leading < min_indent:
                min_indent = leading

    return min_indent if min_indent is not None else 2


def _parse_tree_line(line: str, indent_unit: int):
    """Parse a file tree line and return (depth, name, is_root) or None.

    Handles both pipe-tree format and space-indented format.
    """
    # Strip annotation if present
    path_part = line
    if "<-" in path_part:
        path_part = path_part[: path_part.index("<-")].rstrip()

    stripped = path_part.rstrip()
    if not stripped:
        return None

    # Try pipe-tree format: look for |-- or +--
    pipe_match = re.match(r"^([\s|]*)[|+]--\s+(.+)$", stripped)
    if pipe_match:
        name = pipe_match.group(2).strip()
        # Find the position of the connector to determine depth
        for connector in ("|--", "+--"):
            idx = stripped.find(connector)
            if idx >= 0:
                depth = idx // 4 + 1
                return (depth, name, False)

    # Space-indented format
    lstripped = stripped.lstrip()
    leading_spaces = len(stripped) - len(lstripped)

    if not lstripped:
        return None

    # Root-level item: no leading whitespace, name ends with /
    if leading_spaces == 0:
        if lstripped.endswith("/"):
            return (0, lstripped, True)
        # Could be a root-level file (unlikely in tree) -- skip
        return None

    # Indented item
    name = lstripped
    depth = leading_spaces // indent_unit
    if depth < 1:
        depth = 1

    return (depth, name, False)


def generate_assembly_map(
    blueprint_dir: Path,
    project_root: Path,
) -> Dict[str, Dict[str, str]]:
    """Parse blueprint file tree annotations and produce deployed-to-source map.

    Parses blueprint_prose.md from blueprint_dir for the file tree code block.
    Extracts every `<- Unit N` annotation line, parsing the indented path
    and the unit number.

    Produces a mapping dict stored at .svp/assembly_map.json with a single
    top-level key "repo_to_workspace" that maps each deployed repo path to
    the source stub that produces it:

        {
          "repo_to_workspace": {
            "svp-repo/svp/scripts/routing.py": "src/unit_14/stub.py",
            "svp-repo/svp/agents/git_repo_agent.md": "src/unit_23/stub.py",
            ...
          }
        }

    The relationship is many-to-one: multiple deployed artifacts from the
    same unit share one source stub. Post-Bug-S3-98, every Unit N has only
    one source file at src/unit_N/stub.py — no per-file sources exist.

    Pre-S3-111, this function produced a `workspace_to_repo` forward dict
    and a `repo_to_workspace` reverse dict with a bijectivity invariant.
    The forward dict was removed because many-to-one cannot be represented
    as Dict[str, str] without collision, and no caller actually needs the
    forward direction (Unit 13 embeds the map as raw text; Unit 24's debug
    agent uses only the reverse direction; Unit 23's git repo agent docs
    were vestigial — the actual assembly does not iterate the map).

    Returns the mapping dict (also written to disk).
    """
    blueprint_prose_path = blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
    if not blueprint_prose_path.exists():
        raise FileNotFoundError(
            f"Blueprint prose file not found: {blueprint_prose_path}"
        )

    content = blueprint_prose_path.read_text()

    # Find a code block containing "<- Unit" annotations.
    # Try Preamble section first, then fall back to any code block with annotations.
    preamble_match = re.search(
        r"## Preamble.*?```\n(.*?)```",
        content,
        re.DOTALL,
    )
    if preamble_match:
        file_tree_text = preamble_match.group(1)
    else:
        # Fall back: find any fenced code block that contains "<- Unit" annotations
        code_blocks = re.findall(r"```\n(.*?)```", content, re.DOTALL)
        file_tree_text = None
        for block in code_blocks:
            if re.search(r"<-\s*Unit\s+\d+", block):
                file_tree_text = block
                break
        if file_tree_text is None:
            raise ValueError(
                "Could not find file tree with Unit annotations in blueprint_prose.md"
            )

    repo_to_workspace: Dict[str, str] = {}

    lines = file_tree_text.strip().split("\n")

    # Build a path stack to track the current directory context
    # path_stack[i] is the directory name at depth i
    path_stack: List[str] = []
    unmapped_annotations: List[str] = []  # Annotations that couldn't produce a mapping

    # Detect indent unit for space-indented trees
    indent_unit = _detect_indent_unit(lines)

    for line in lines:
        # Check for unit annotation
        annotation_match = re.search(r"<-\s*Unit\s+(\d+)", line)
        unit_number = int(annotation_match.group(1)) if annotation_match else None

        # Parse the line
        parsed = _parse_tree_line(line, indent_unit)
        if parsed is None:
            if unit_number is not None:
                unmapped_annotations.append(line.strip())
            continue

        depth, name, is_root = parsed

        if is_root:
            # Root directory
            dir_name = name.rstrip("/")
            path_stack = [dir_name]
            continue

        is_dir = name.endswith("/")

        if is_dir:
            dir_name = name.rstrip("/")
            # Trim stack to parent depth, then set this level
            while len(path_stack) > depth:
                path_stack.pop()
            if len(path_stack) < depth:
                # Fill gaps (shouldn't normally happen)
                while len(path_stack) < depth:
                    path_stack.append("")
            path_stack.append(dir_name)
        else:
            # File entry
            # Trim stack to the parent directory depth
            while len(path_stack) > depth:
                path_stack.pop()

            if unit_number is not None:
                repo_path = "/".join(path_stack + [name])
                # Bug S3-111: post-S3-98, every unit has ONE source stub.
                # The deployed file (agent .md, derived .py, command .md)
                # is produced from src/unit_N/stub.py by regenerate_deployed_
                # artifacts() or derive_scripts_from_stubs.py. The pre-S3-111
                # formula `f"src/unit_{N}/{name}"` was stale on every run.
                workspace_path = f"src/unit_{unit_number}/stub.py"
                repo_to_workspace[repo_path] = workspace_path

    # Verify completeness: annotations on unparseable lines are errors.
    # Directory-level annotations are structural documentation and are
    # silently skipped (they don't produce mappings).
    if unmapped_annotations:
        raise ValueError(
            f"Assembly map incomplete: {len(unmapped_annotations)} "
            f"annotation(s) could not be mapped:\n"
            + "\n".join(f"  {a}" for a in unmapped_annotations)
        )

    # Write to disk. Single top-level key: repo_to_workspace.
    # Staleness invariant (enforced by regression tests, not here): every
    # value matches ^src/unit_\d+/stub\.py$ and points at a file on disk.
    assembly_map = {"repo_to_workspace": repo_to_workspace}

    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    map_path = svp_dir / "assembly_map.json"
    map_path.write_text(json.dumps(assembly_map, indent=2) + "\n")

    return assembly_map


# ---------------------------------------------------------------------------
# Regression test import adaptation CLI
# ---------------------------------------------------------------------------


def _apply_python_replacements(
    content: str,
    import_map: Dict[str, str],
) -> str:
    """Apply Python import replacements to file content."""
    for old_module, new_module in import_map.items():
        # Replace 'from X import Y' patterns
        content = re.sub(
            rf"from\s+{re.escape(old_module)}\s+import\s+",
            f"from {new_module} import ",
            content,
        )
        # Replace 'import X' patterns (full module import)
        content = re.sub(
            rf"^import\s+{re.escape(old_module)}\b",
            f"import {new_module}",
            content,
            flags=re.MULTILINE,
        )
        # Replace '@patch("X.Y")' and 'patch("X.Y")' patterns
        # Handle both decorator and inline forms
        content = re.sub(
            rf'@patch\(\s*"{re.escape(old_module)}\.([^"]+)"\s*\)',
            f'@patch("{new_module}.\\1")',
            content,
        )
        content = re.sub(
            rf'patch\(\s*"{re.escape(old_module)}\.([^"]+)"\s*\)',
            f'patch("{new_module}.\\1")',
            content,
        )
    return content


def _apply_r_replacements(
    content: str,
    import_map: Dict[str, str],
) -> str:
    """Apply R source() path replacements to file content."""
    for old_path, new_path in import_map.items():
        # Replace source("old_path") with source("new_path")
        content = re.sub(
            rf'source\(\s*"{re.escape(old_path)}"\s*\)',
            f'source("{new_path}")',
            content,
        )
        content = re.sub(
            rf"source\(\s*'{re.escape(old_path)}'\s*\)",
            f"source('{new_path}')",
            content,
        )
    return content


def adapt_regression_tests_main(argv: list = None) -> None:
    """CLI entry point for regression test import adaptation.

    Arguments:
        --map-file: path to regression_test_import_map.json
        --tests-dir: path to tests/regressions/
        --language: language identifier (optional)
    """
    parser = argparse.ArgumentParser(
        description="Adapt regression test imports.",
    )
    parser.add_argument(
        "--map-file",
        type=str,
        required=True,
        help="Path to regression_test_import_map.json",
    )
    parser.add_argument(
        "--tests-dir",
        type=str,
        required=True,
        help="Path to tests/regressions/ directory",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language identifier (optional, auto-detects from extension)",
    )

    args = parser.parse_args(argv)

    map_path = Path(args.map_file)
    tests_dir = Path(args.tests_dir)

    if not map_path.exists():
        print(f"Import map not found: {map_path}", file=sys.stderr)
        sys.exit(1)

    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}", file=sys.stderr)
        sys.exit(1)

    # Load the import map
    with open(map_path) as f:
        import_map = json.load(f)

    # Process each test file
    for test_file in sorted(tests_dir.iterdir()):
        if not test_file.is_file():
            continue

        # Determine language from file extension or --language flag
        language = args.language
        if language is None:
            if test_file.suffix == ".py":
                language = "python"
            elif test_file.suffix == ".R":
                language = "r"
            else:
                continue

        content = test_file.read_text()

        if language == "python":
            new_content = _apply_python_replacements(content, import_map)
        elif language == "r":
            new_content = _apply_r_replacements(content, import_map)
        else:
            continue

        # Only write if content changed (idempotent)
        if new_content != content:
            test_file.write_text(new_content)


# ---------------------------------------------------------------------------
# CLI entry point (Bug S3-110)
# ---------------------------------------------------------------------------
#
# When this stub is derived to scripts/generate_assembly_map.py it becomes
# the canonical CLI for Unit 23's deterministic utilities. Subcommands:
#
#   regression-adapt --target <dir> --map <json> [--language python|r]
#       Adapt carry-forward regression tests by rewriting imports per the
#       given map. Invoked by Unit 11 infrastructure setup step 8.
#
# Historically this functionality lived in a standalone script
# scripts/adapt_regression_tests.py. Bug S3-109 revealed that script was
# an orphaned duplicate of Unit 23 code; Bug S3-110 deleted it entirely
# and redirected Unit 11 here.


def _main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="generate_assembly_map.py",
        description="Unit 23 CLI — deterministic utilities for assembly and regression adaptation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_adapt = sub.add_parser(
        "regression-adapt",
        help="Adapt carry-forward regression tests by rewriting imports per a map.",
    )
    p_adapt.add_argument("--target", required=True, help="Directory of regression tests to adapt.")
    p_adapt.add_argument(
        "--map",
        required=True,
        dest="map_file",
        help="Path to regression_test_import_map.json.",
    )
    p_adapt.add_argument("--language", choices=["python", "r"], default=None)

    args = parser.parse_args(argv)

    if args.command == "regression-adapt":
        # Translate the S3-110 outer flag names (--target/--map) to the
        # inner function's flag names (--tests-dir/--map-file).
        forwarded = ["--tests-dir", args.target, "--map-file", args.map_file]
        if args.language:
            forwarded += ["--language", args.language]
        adapt_regression_tests_main(forwarded)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv[1:]))
