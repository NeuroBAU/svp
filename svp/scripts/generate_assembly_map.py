"""Unit 23: Utility Agent Definitions and Assembly Dispatch.

Provides agent definition constants (git repo, checklist generation,
regression adaptation, oracle), project assembly functions for Python
and R, assembly map generation, and regression test import adaptation CLI.
"""

import argparse
import ast
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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

## Delivered Repo Location (Bug S3-112)

The delivered repository MUST be placed at the canonical sibling path:

    {project_root.parent}/{project_name}-repo

where `project_name` is `profile["name"]` (or `profile["project_name"]`, \
or the basename of `project_root` as fallback). Your task prompt's \
"Delivered Repo Path (REQUIRED)" section contains the resolved absolute \
path you must use — do not recompute or improvise.

You MUST call the language-appropriate assembler helper from the \
`generate_assembly_map` module. These helpers already place the repo at \
the canonical sibling path and return the Path of the created repo:

  - Python archetype: `assemble_python_project(project_root, profile, assembly_config)`
  - R archetype: `assemble_r_project(project_root, profile, assembly_config)`
  - Plugin archetype: `assemble_plugin_project(project_root, profile, assembly_config)`
  - Mixed archetype: `assemble_mixed_project(project_root, profile, assembly_config)`

You MUST NOT:

  - Create a directory named `delivered/`, `delivered_repo/`, `output/`, \
    or any sub-directory of the project root as the destination. The \
    canonical location is always a SIBLING of the project root, never \
    inside it.
  - Manually edit `.svp/pipeline_state.json`. The POST dispatch step \
    (`dispatch_agent_status` for `REPO_ASSEMBLY_COMPLETE`) automatically \
    computes the canonical path, verifies the directory exists, and \
    sets `state.delivered_repo_path` to the absolute resolved path. If \
    you set it yourself and deviate from the canonical sibling path, \
    the dispatch step will overwrite your value (if the canonical \
    directory exists) or RAISE an error (if it does not), halting the \
    pipeline. Do not try to set state directly.

## Automated Delivery Steps (Bugs S3-146, S3-147, S3-148)

The assembler helpers now perform **four delivery steps automatically** \
after creating the repo structure: (1) `copy_workspace_tests_to_repo` copies \
`workspace/tests/` to `repo/tests/` with a fixed exclusion list (caches, \
backups, cross-unit workspace stubs); (2) `adapt_test_imports_in_repo` \
adapts test imports to match the delivered source layout (no-op for \
`svp_native`; rewrites flat imports to package-prefixed form for \
`conventional` / `flat`); (3) `write_delivered_claude_md` writes a \
delivered-repo-scoped `CLAUDE.md` carrying a Universal Manual Bug-Fixing \
Protocol stripped of SVP-internal references (workspace, pipeline state, \
PREPARE/POST commands) — skipped for E/F self-builds where \
`assemble_svp_workspace_artifacts` already writes the SVP-meta variant; \
(4) `deliver_source_files` walks `.svp/assembly_map.json` and copies each \
Python source entry from `workspace/src/unit_N/stub.py` to the \
layout-appropriate destination in the delivered repo, rewriting \
stub-style imports (`from src.unit_N.stub import X`) to flat or \
package-prefixed form depending on `delivery.python.source_layout`.

You **MUST NOT** re-do these steps manually. The helpers are idempotent and \
deterministic; running them again from your shell would not produce a \
better result and risks divergence between the workspace contents and the \
delivered repo. If you observe missing tests, missing CLAUDE.md, or \
incorrectly-adapted imports in the delivered repo, treat it as a bug in \
the assembler helper (file via `/svp:bug`), not as a step for you to \
compensate for.

You **MUST still** run `generate_assembly_map.py regression-adapt` after \
the assembler returns — that script handles the separate concern of \
carry-forward regression test imports (SVP N→N+1 module migrations) and \
is keyed by an explicit `regression_test_import_map.json` file. It is not \
covered by the automated unit-test adapt above.

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
- **Every seed item from spec Section 44** verbatim or with project-specific \
refinement (Section 7.8.2 mandates that no seed item may be omitted).

## Six Universal Categories (NEW IN 2.2 — Section 44.11)

The generated `blueprint_author_checklist.md` MUST embed every item from spec \
Section 44.11, organized into the following six categories. These categories are \
universal structural principles that apply to any blueprint regardless of project \
archetype or primary language:

1. **Schema Coherence (Category S, Section 44.11.1, items SC-27..SC-31):** every \
type/class/schema referenced exists; no phantom fields; no orphan schemas; consistent \
nullability propagation; exhaustive enumerated domains.

2. **Function Reachability (Category F, Section 44.11.2, items SC-32..SC-36):** every \
declared function is called or is a public entry point; every function call is \
declared; no dead functions; no undeclared callees; private-helper scope respected.

3. **Invariant Coherence (Category I, Section 44.11.3, items SC-37..SC-41):** every \
invariant is a precise testable predicate; no contradictions; every invariant is \
established and maintained; dependencies between invariants are explicit; invariants \
are observable.

4. **Dispatch Completeness (Category D, Section 44.11.4, items SC-42..SC-47):** every \
dispatch table has declared key/value types; tables with \u22653 keys use markdown \
table form; missing-key behavior is specified; tie-breaking is explicit; dispatch \
values reach Tier 2 signatures; enumerable-domain keys assert domain equality.

5. **Branch Reachability (Category B, Section 44.11.5, items SC-48..SC-52):** every \
branch is reachable; no contradictory guards; error branches have triggering \
conditions; happy/error coverage is symmetric; branches are classified normal vs \
safety net.

6. **Contract Bidirectional Mapping (Category C, Section 44.11.6, items SC-53..SC-57):** \
forward mapping (every spec requirement \u2192 contract); backward mapping (every \
contract cites spec/preference/invariant/bug); no orphan contracts or requirements; \
preference and bug citations are verbatim and traceable.

### Per-Language Refinement

Many items in Categories S and F have language-specific refinement notes in Section \
44.11 (e.g., Python \u2192 type imports; R \u2192 S3/S4 classes; Bash \u2192 N/A; \
Stan \u2192 explicit type declarations). When generating the project-specific \
`blueprint_author_checklist.md`, you MUST:

- Read the project profile's `language` section to determine the primary language.
- For each Section 44.11 item with language-specific refinement, write the item with \
the refinement appropriate to the project's primary language.
- For items marked "skipped" for the primary language (e.g., S-1 for Bash), explicitly \
mark the item as "N/A for this archetype" rather than omitting it entirely \u2014 \
this preserves the audit trail.
- Items marked *(language-agnostic)* in Section 44.11 are included verbatim with no \
refinement.

The blueprint author will then use the refined checklist as the authoritative source \
for the self-review step (see `BLUEPRINT_AUTHOR_DEFINITION` Methodology step 6 and \
Self-Review Artifact section).

## Output Files

The generated checklists are written to:
- `.svp/blueprint_author_checklist.md` (consumed by the blueprint author for the \
Self-Review Pass step)
- `.svp/alignment_checker_checklist.md` (consumed by the blueprint alignment checker \
during Stage 2 alignment review)

The blueprint author additionally produces a third file at \
`.svp/blueprint_self_review.md` containing its own filled self-review against \
`blueprint_author_checklist.md`. You do NOT generate `blueprint_self_review.md` \
\u2014 it is produced by the blueprint author after blueprint construction.
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
    source_layout = python_delivery.get("source_layout", "conventional")

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

    # Bug S3-146 + S3-152: pytest must resolve the delivered modules without
    # requiring `pip install`. Set pythonpath per layout so the package
    # prefix (or flat module name, for svp_native) imports cleanly when
    # `pytest` is invoked in the delivered repo.
    if source_layout == "svp_native":
        pytest_pythonpath = '["scripts"]'
    elif source_layout == "conventional":
        pytest_pythonpath = '["src"]'
    elif source_layout == "flat":
        pytest_pythonpath = '["."]'
    else:
        pytest_pythonpath = None
    if pytest_pythonpath is not None:
        content_lines.extend(
            [
                "",
                "[tool.pytest.ini_options]",
                f"pythonpath = {pytest_pythonpath}",
            ]
        )

    content_lines.append("")
    (repo_dir / "pyproject.toml").write_text("\n".join(content_lines))


# ---------------------------------------------------------------------------
# Bug S3-146: Deterministic test delivery and import adaptation
# ---------------------------------------------------------------------------

# Files / dirs to skip when copying workspace/tests/ to repo/tests/. Caches and
# backups have no use in the delivered repo; cross-unit workspace stub helpers
# (tests/unit_*/unit_*_stub.py) resolve via flat imports in the workspace but
# would be noise in the delivered repo where the script-derivation pipeline
# has already produced flat modules.
_TEST_COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "*.pyc",
    "*.bak.*",
    "*.bak",
    "unit_*_stub.py",
)


def _workspace_module_names(workspace: Path) -> List[str]:
    """Return the flat module names of scripts in workspace/scripts/.

    These are the modules that workspace tests import via
    `from <name> import …`. Must be called after sync_workspace.sh Step 0
    has derived scripts/ from src/unit_*/stub.py. Excludes __init__.py.
    """
    scripts_dir = workspace / "scripts"
    if not scripts_dir.is_dir():
        return []
    return sorted(
        p.stem
        for p in scripts_dir.glob("*.py")
        if p.is_file() and p.name != "__init__.py"
    )


def _derive_package_name(profile: Dict[str, Any], repo_dir: Path) -> str:
    """Derive the Python package name from profile or repo dir name.

    Precedence: profile.delivery.python.package_name > repo_dir.name (with
    "-" and " " replaced by "_" to make a valid Python identifier).
    """
    python_delivery = profile.get("delivery", {}).get("python", {})
    explicit = python_delivery.get("package_name")
    if explicit:
        return str(explicit)
    return repo_dir.name.replace("-", "_").replace(" ", "_")


def copy_workspace_tests_to_repo(
    workspace: Path, repo_dir: Path, profile: Dict[str, Any]
) -> int:
    """Copy workspace/tests/ to repo/tests/ with fixed exclusions.

    Idempotent (dirs_exist_ok=True). Returns the count of .py files in the
    destination after the copy.

    Python archetype focus for now (Bug S3-146 scope). R archetype's
    workspace/tests/testthat/ also lands at repo/tests/testthat/ via the
    same copytree because the source already has that subdirectory layout.
    Plugin and mixed archetypes are deferred — they may need destination
    routing (e.g., repo/<plugin>/tests/) which this helper doesn't yet do.
    """
    src = workspace / "tests"
    if not src.is_dir():
        return 0
    dst = repo_dir / "tests"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=_TEST_COPY_IGNORE, dirs_exist_ok=True)
    return sum(1 for _ in dst.rglob("*.py"))


def _rewrite_imports_with_prefix(
    repo_dir: Path, workspace_modules: List[str], package: str
) -> int:
    """Rewrite flat imports in repo/tests/*.py to package-prefixed form.

    Transformations (only for module names in workspace_modules):
      from <module> import …   →   from <package>.<module> import …
      import <module>          →   import <package>.<module>
      import <module> as X     →   import <package>.<module> as X

    Idempotent by construction: an import already prefixed (e.g.,
    `from <package>.<module>`) has node.module == "<package>.<module>",
    which is NOT in workspace_modules, so the walk leaves it alone.

    Uses ast.parse + ast.unparse for safety. ast.unparse preserves
    semantics but may normalize formatting (e.g., quote style); test
    files do not depend on sensitive formatting.

    Returns the number of files modified.
    """
    modset = set(workspace_modules)
    tests_dir = repo_dir / "tests"
    if not tests_dir.is_dir():
        return 0

    count = 0
    for pyfile in sorted(tests_dir.rglob("*.py")):
        try:
            source = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        modified = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Only rewrite absolute imports of known workspace modules.
                if node.module in modset and node.level == 0:
                    node.module = f"{package}.{node.module}"
                    modified = True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in modset:
                        alias.name = f"{package}.{alias.name}"
                        modified = True
        if modified:
            pyfile.write_text(ast.unparse(tree) + "\n", encoding="utf-8")
            count += 1
    return count


# Layout-keyed dispatch table. Adding a new layout = one entry.
_ADAPT_BY_LAYOUT: Dict[str, Callable[[Path, List[str], str], int]] = {
    "svp_native": lambda repo, mods, pkg: 0,  # no-op: pyproject pythonpath handles it
    "conventional": _rewrite_imports_with_prefix,
    "flat": _rewrite_imports_with_prefix,
}


def adapt_test_imports_in_repo(
    repo_dir: Path, profile: Dict[str, Any], workspace_modules: List[str]
) -> int:
    """Adapt test imports in repo_dir/tests/ to the delivered repo's layout.

    For svp_native layout: no-op (flat imports resolve via pyproject's
    pythonpath = ["scripts"]).
    For conventional and flat layouts: rewrites flat imports to
    package-prefixed form via _rewrite_imports_with_prefix.

    Returns the number of files modified.
    """
    layout = (
        profile.get("delivery", {})
        .get("python", {})
        .get("source_layout", "conventional")
    )
    package = _derive_package_name(profile, repo_dir)
    adapter = _ADAPT_BY_LAYOUT.get(layout, _rewrite_imports_with_prefix)
    return adapter(repo_dir, workspace_modules, package)


_NON_SOURCE_REPO_PATH_MARKERS = (
    "/tests/",
    "/agents/",
    "/commands/",
    "/hooks/",
    "/skills/",
    "/.claude-plugin/",
    ".claude-plugin/",
)


def _extract_unit_number(stub_path: str) -> int | None:
    """Extract N from 'src.unit_N.stub' or 'src/unit_N/stub.py' or any path
    containing 'unit_<digits>'. Returns None if no unit number is present.
    """
    match = re.search(r"unit_(\d+)", stub_path)
    return int(match.group(1)) if match else None


def _derive_unit_to_module_map(repo_to_workspace: Dict[str, str]) -> Dict[int, str]:
    """Build a unit-number → deployed-module-name map from the assembly map.

    Filters to .py source-code entries (excludes tests, agents, commands,
    hooks, skills, manifests, __init__.py). Uses the basename of the
    deployed path (without .py) as the module name. Assumes 1:1 within the
    source tree per Bug S3-98 (one stub per unit). When multiple source
    entries map to the same unit (unexpected), the last entry wins.
    """
    unit_to_module: Dict[int, str] = {}
    for deployed_path, source_path in repo_to_workspace.items():
        if not deployed_path.endswith(".py"):
            continue
        if any(marker in deployed_path for marker in _NON_SOURCE_REPO_PATH_MARKERS):
            continue
        if Path(deployed_path).name == "__init__.py":
            continue
        unit_n = _extract_unit_number(source_path)
        if unit_n is None:
            continue
        unit_to_module[unit_n] = Path(deployed_path).stem
    return unit_to_module


def _rewrite_source_imports(
    source_text: str,
    unit_to_module: Dict[int, str],
    package: str | None,
) -> str:
    """Rewrite stub-style imports in a workspace stub to delivered form.

    Handles three patterns when the imported module is `src.unit_N.stub`
    and `N` is in `unit_to_module`:
      from src.unit_N.stub import X  →  from <prefix><module> import X
      import src.unit_N.stub          →  import <prefix><module>
      import src.unit_N.stub as Y     →  import <prefix><module> as Y

    `<prefix>` is empty for svp_native (`package is None`); for
    conventional/flat layouts it is `<package>.`.

    Idempotent: an already-rewritten import does not start with `src.unit_`
    and is left alone. Returns rewritten source if any changes were made,
    else the original source unchanged.
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return source_text

    modified = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (
                node.module
                and node.module.startswith("src.unit_")
                and node.module.endswith(".stub")
                and node.level == 0
            ):
                unit_n = _extract_unit_number(node.module)
                if unit_n is not None and unit_n in unit_to_module:
                    module_name = unit_to_module[unit_n]
                    new_module = (
                        f"{package}.{module_name}" if package else module_name
                    )
                    node.module = new_module
                    modified = True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.unit_") and alias.name.endswith(".stub"):
                    unit_n = _extract_unit_number(alias.name)
                    if unit_n is not None and unit_n in unit_to_module:
                        module_name = unit_to_module[unit_n]
                        new_name = (
                            f"{package}.{module_name}" if package else module_name
                        )
                        alias.name = new_name
                        modified = True

    if modified:
        return ast.unparse(tree) + "\n"
    return source_text


def deliver_source_files(
    workspace: Path,
    repo_dir: Path,
    assembly_map: Dict[str, Any],
    profile: Dict[str, Any],
) -> int:
    """Walk assembly_map repo_to_workspace .py source entries, copy + rewrite imports.

    For each .py source entry (excluding tests/, agents/, commands/, hooks/,
    skills/, manifests, __init__.py), reads the workspace stub, rewrites
    stub-style imports via _rewrite_source_imports, and writes to
    repo_dir / relative_path (where relative_path strips a leading
    `<repo_dir.name>/` prefix from deployed_path if present).

    Layout-keyed prefix selection: svp_native uses no package prefix
    (modules land at repo/scripts/<module>.py); conventional / flat use
    `<package>.<module>` form (modules land at repo/src/<pkg>/<module>.py
    or repo/<pkg>/<module>.py respectively). Package name is derived via
    _derive_package_name(profile, repo_dir).

    Returns the number of files written. Soft-fails on missing
    repo_to_workspace key (returns 0).
    """
    layout = (
        profile.get("delivery", {})
        .get("python", {})
        .get("source_layout", "conventional")
    )
    package = None if layout == "svp_native" else _derive_package_name(profile, repo_dir)

    repo_to_workspace = assembly_map.get("repo_to_workspace", {})
    if not repo_to_workspace:
        return 0

    unit_to_module = _derive_unit_to_module_map(repo_to_workspace)
    repo_name = repo_dir.name
    count = 0

    for deployed_path, source_path in repo_to_workspace.items():
        if not deployed_path.endswith(".py"):
            continue
        if any(marker in deployed_path for marker in _NON_SOURCE_REPO_PATH_MARKERS):
            continue
        if Path(deployed_path).name == "__init__.py":
            continue

        # Strip leading `<repo_name>/` from deployed path to get a path
        # relative to repo_dir.
        if deployed_path.startswith(repo_name + "/"):
            relative = deployed_path[len(repo_name) + 1 :]
        else:
            relative = deployed_path

        target = repo_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        source_stub = workspace / source_path
        if not source_stub.is_file():
            continue

        source_text = source_stub.read_text(encoding="utf-8")
        rewritten = _rewrite_source_imports(source_text, unit_to_module, package)
        target.write_text(rewritten, encoding="utf-8")
        count += 1

    return count


def _get_orchestrator_break_glass_primer_text(
    project_root: Path,
    profile: Dict[str, Any],
) -> Optional[str]:
    """Return the orchestrator_break_glass primer markdown for the project's
    archetype if the toolchain manifest declares one; None otherwise.

    Bug S3-183 (cycle E3): the 5th primer key in the manifest's
    ``language_architecture_primers`` field is wired at Stage 5 delivery
    rather than at ``prepare_task`` time (the four other keys are dispatched
    by Unit 13's ``_get_language_architecture_primer`` per S3-182). Rationale:
    the orchestrator is the main Claude Code session — its "task prompt" is
    the on-disk CLAUDE.md loaded on session boot, not a subagent prompt.
    Mirror of P66 but the dispatch surface is "session boot" not "task prompt
    assembly".

    Defensive at every step: returns ``None`` on missing profile fields,
    missing manifest, missing ``language_architecture_primers`` field,
    missing ``orchestrator_break_glass`` key, missing file, or any read
    error. No primer-append site can crash Stage 5 delivery.
    """
    primary_language = (profile.get("language") or {}).get("primary")
    if not primary_language:
        return None
    try:
        from toolchain_reader import load_toolchain
    except Exception:
        return None
    try:
        toolchain = load_toolchain(project_root, language=primary_language)
    except Exception:
        return None
    primers = toolchain.get("language_architecture_primers") or {}
    if not isinstance(primers, dict):
        return None
    primer_path = primers.get("orchestrator_break_glass")
    if not primer_path:
        return None
    full_path = Path(project_root) / primer_path
    if not full_path.exists():
        return None
    try:
        return full_path.read_text(encoding="utf-8")
    except Exception:
        return None


def write_delivered_claude_md(
    repo_dir: Path,
    profile: Dict[str, Any],
    project_name: str,
    project_root: Optional[Path] = None,
) -> bool:
    """Write a delivered-repo-scoped CLAUDE.md to repo_dir (Bug S3-147).

    For A-D archetypes only. E/F self-builds set profile["is_svp_build"]=True
    and use the existing assemble_svp_workspace_artifacts path which writes
    CLAUDE_MD_TEMPLATE + CLAUDE_MD_SVP_ADDENDUM into the repo; this function
    skips that case so we don't overwrite the SVP-meta content.

    Always overwrites for A-D archetypes — the assembly path is
    regenerative (_backup_existing already preserved any prior content
    under .bak.YYYYMMDD-HHMMSS). Same inputs → same output every assembly.

    Bug S3-183 (cycle E3): when ``project_root`` is supplied and the
    toolchain manifest for ``profile["language"]["primary"]`` declares an
    ``orchestrator_break_glass`` primer path under
    ``language_architecture_primers``, this function appends the primer's
    file contents as a top-level section at the end of the rendered
    template. Defensive: silent no-op on any missing prerequisite. The
    parameter defaults to ``None`` for back-compat with callers that do not
    pass it (existing tests, etc.) — no primer section is appended in that
    case.

    Returns True iff the file was written.
    """
    if profile.get("is_svp_build", False):
        return False
    from svp_launcher import CLAUDE_MD_DELIVERED_REPO_TEMPLATE
    content = CLAUDE_MD_DELIVERED_REPO_TEMPLATE.format(project_name=project_name)
    if project_root is not None:
        primer_text = _get_orchestrator_break_glass_primer_text(
            project_root, profile
        )
        if primer_text:
            content += (
                "\n\n## Orchestrator Break-Glass Primer (Archetype-Specific)\n\n"
                + primer_text
            )
    (repo_dir / "CLAUDE.md").write_text(content, encoding="utf-8")
    return True


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

    # Bug S3-146: deterministic test suite delivery + import adaptation.
    # Replaces the previous agent-discretionary step where the git_repo_agent
    # was expected to copy tests and adapt imports manually (often missed,
    # especially on Windows where path semantics differ).
    copy_workspace_tests_to_repo(project_root, repo_dir, profile)
    adapt_test_imports_in_repo(
        repo_dir, profile, _workspace_module_names(project_root)
    )

    # Bug S3-147: deterministic delivered-repo CLAUDE.md with break-glass
    # protocol. Skipped for E/F self-builds (assemble_svp_workspace_artifacts
    # writes a different template).
    # Bug S3-183 (cycle E3): pass project_root so write_delivered_claude_md
    # can resolve the toolchain manifest's orchestrator_break_glass primer
    # and append it as an archetype-specific section.
    write_delivered_claude_md(
        repo_dir, profile, project_name, project_root=project_root
    )

    # Bug S3-148: deterministic source-file delivery. Reads the assembly_map
    # produced by generate_assembly_map and copies/rewrites each .py source
    # entry into the delivered repo at the layout-appropriate destination.
    # Soft-fails when the assembly_map is absent — early-pipeline assembly
    # may run before generate_assembly_map has produced the map.
    assembly_map_path = project_root / ".svp" / "assembly_map.json"
    if assembly_map_path.is_file():
        try:
            assembly_map_obj = json.loads(
                assembly_map_path.read_text(encoding="utf-8")
            )
            deliver_source_files(project_root, repo_dir, assembly_map_obj, profile)
        except (json.JSONDecodeError, OSError):
            # Map exists but is unreadable; skip delivery rather than crash.
            pass

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

    # Bug S3-147: deterministic delivered-repo CLAUDE.md.
    # Bug S3-183 (cycle E3): pass project_root so the orchestrator
    # break-glass primer can be appended for R archetypes.
    write_delivered_claude_md(
        repo_dir, profile, project_name, project_root=project_root
    )

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

    # Bug S3-147: deterministic delivered-repo CLAUDE.md.
    # Bug S3-183 (cycle E3): pass project_root so the orchestrator
    # break-glass primer can be appended for plugin archetypes.
    write_delivered_claude_md(
        repo_dir, profile, project_name, project_root=project_root
    )

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
        STATISTICAL_CORRECTNESS_REVIEWER_DEFINITION,
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
        "statistical_correctness_reviewer.md": STATISTICAL_CORRECTNESS_REVIEWER_DEFINITION,
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
        "statistical_correctness_reviewer": "statistical_correctness_reviewer",
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
        # Bug S3-122: frontmatter `name` MUST equal the filename stem verbatim.
        # Claude Code uses the frontmatter `name` field as the agent registration
        # identifier; transforming it (e.g., `_` -> `-`) creates drift between the
        # registered subagent_type and every internal reference (PHASE_TO_AGENT,
        # AGENT_STATUS_LINES, action block agent_type, etc.) which all use the
        # underscored form.
        name = stem
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

    # Bug S3-121: defensive cleanup of stale *.md files. Without this, a cached
    # svp_*.md file (from before the rename) could survive reassembly and
    # continue to register as /svp:svp_bug alongside the fresh /svp:bug.
    # Invariant: after assembly, commands_dir contains exactly the files
    # COMMAND_DEFINITIONS declares and nothing else.
    for stale in commands_dir.glob("*.md"):
        stale.unlink()

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
            STATISTICAL_CORRECTNESS_REVIEWER_DEFINITION,
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
            "statistical_correctness_reviewer.md": STATISTICAL_CORRECTNESS_REVIEWER_DEFINITION,
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
            "statistical_correctness_reviewer": "statistical_correctness_reviewer",
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
            # Bug S3-122: frontmatter `name` is the filename stem verbatim
            # (see assemble_plugin_components above for the full rationale).
            name = stem
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
                "Could not find file tree with Unit annotations in "
                "blueprint_prose.md.\n\n"
                "Bug S3-150: the blueprint must include a section titled "
                "'## Preamble: Delivered File Tree' containing a fenced code "
                "block with the delivered repository's file tree. Each row "
                "that maps to a workspace unit must carry an inline "
                "`<- Unit N` annotation pointing at the producing unit "
                "number.\n\n"
                "Fix: invoke the blueprint_author agent in revision mode and "
                "ask it to add the Preamble section. The agent's definition "
                "(unit_20::BLUEPRINT_AUTHOR_DEFINITION, 'Delivered File Tree' "
                "section) describes the required format and includes a worked "
                "example. See spec section 24.164."
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
