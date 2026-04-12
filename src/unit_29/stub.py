"""Unit 29: Launcher -- full implementation."""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Ensure sibling scripts are importable when running as pip entry point.
_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from src.unit_1.stub import ARTIFACT_FILENAMES
from src.unit_2.stub import LANGUAGE_REGISTRY

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tier 1: Universal CLAUDE.md content for ALL SVP projects (A-D, E, F)
CLAUDE_MD_TEMPLATE: str = """\
# SVP-Managed Project: {project_name}

This project is managed by the **Stratified Verification Pipeline (SVP)**. \
You are the orchestration layer — the main session. \
Your behavior is fully constrained by deterministic scripts. \
Do not improvise pipeline flow.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and outputs a structured \
action block telling you exactly what to do next. Execute its output. \
Do not reason about what stage the pipeline is in or what should happen next.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated:

1. **Run the routing script** → receive a structured action block.
2. **Run the PREPARE command** (if present) → produces a task prompt or gate prompt file.
3. **Execute the ACTION** (invoke agent / run command / present gate).
4. **Write the result to `.svp/last_status.txt`** (agent terminal status line or constructed command status).
5. **Run the POST command** (if present) → updates pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps.

## Verbatim Task Prompt Relay

When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt \
**verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled \
by a deterministic preparation script and contains exactly the context the agent needs.

## REMINDER

- Execute the ACTION above exactly as specified.
- When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt verbatim.
- Wait for the agent to produce its terminal status line before proceeding.
- Write the agent's terminal status line to .svp/last_status.txt.
- Run the POST command if one was specified.
- Then re-run the routing script for the next action.
- Do not improvise pipeline flow. Do not skip steps. Do not add steps.
- If the human types during an autonomous sequence, acknowledge and defer.
- You MUST NOT write to pipeline_state.json directly or batch multiple units.
"""

# Tier 2: SVP self-build addendum (E/F only) — bug-fixing protocol, sync, stubs
CLAUDE_MD_SVP_ADDENDUM: str = """\

## Manual Bug-Fixing Protocol (Break-Glass Mode)

When the SVP routing mechanism is too broken to function and the human asks \
you to fix bugs directly, follow this protocol EXACTLY.

**RULE 0: NEVER directly fix a bug. ALWAYS enter plan mode first.**

### Bug-Fixing Cycle (repeat for each bug):

1. **DIAGNOSE** — Identify root cause. Trace through spec → blueprint → code to understand WHY.

2. **PLAN** the fixes in:
   - a. **SPEC** — Add bug entry to Section 24, fix any spec gaps
   - b. **BLUEPRINT** — Amend contracts in affected units
   - c. **CODE** — Fix implementation in `src/unit_*/stub.py`. \
**Stubs are the single source of truth.** Never edit `scripts/*.py` directly \
— they are derived from stubs by `sync_workspace.sh` Step 0 (import rewriting). \
Fix the stub, run sync, scripts auto-update.
   - d. **EXECUTE** — Apply the code changes
   - e. **EVALUATE** — Run tests, verify the fix works
   - f. **LESSONS LEARNED** — Write entry in `references/svp_2_1_lessons_learned.md`
   - g. **REGRESSION TESTS** — Author tests covering ALL aspects of the bug
   - h. **VERIFY** — Tests pass with 0 skipped
   - i. **DEPLOYED ARTIFACTS** — If the fix touches Units that produce deployed \
plugin artifacts (Unit 25 → `svp/commands/`, Unit 26 → `svp/skills/`, \
Unit 23 → `svp/agents/`, `svp/hooks/`), manually update the corresponding \
`.md` files in the repo's `svp/` directory. `sync_workspace.sh` does NOT \
sync these. The deployed `.md` file is what Claude Code loads — the Python \
source is only an input to assembly.
   - j. **SYNC** — Run `bash sync_workspace.sh` from the workspace directory. This handles:
     - Step 0: Derives `scripts/*.py` from `src/unit_*/stub.py` by rewriting imports (stubs → flat modules)
     - Scripts: workspace `scripts/` ↔ repo `svp/scripts/` (newer wins)
     - Source units: workspace `src/unit_*/stub.py` ↔ repo `src/unit_*/stub.py` (newer wins)
     - Docs: workspace is authoritative → repo `docs/`, `specs/`, `blueprint/`, `references/` + Pass 1 repo
     - Tests: workspace `tests/` ↔ repo `tests/` (newer wins)
     - Use `--dry-run` to preview, `--force-workspace` or `--force-repo` to override timestamps
   - k. **TEST FROM BOTH** — Run `pytest` from BOTH the workspace AND the repo directory. \
Do not skip either. Failures in one but not the other indicate stale test files or permission issues.

3. **EVALUATE** — All tests pass from BOTH workspace AND repo. 0 skipped, 0 failed. \
Repos fully in sync. Clean up any stale test artifacts (e.g., `test_project/`, \
`test_restore/`) left by previous runs.
"""

VALID_STAGES = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}


def _get_plugin_search_locations() -> List[Path]:
    """Return standard plugin search locations (platform-aware, Bug S3-71)."""
    home = Path.home()
    locations = [
        home / ".claude" / "plugins" / "svp",
        home / ".claude" / "plugins" / "cache" / "svp" / "svp",
        home / ".config" / "claude" / "plugins" / "svp",
    ]
    if sys.platform == "win32":
        for var in ("LOCALAPPDATA", "PROGRAMDATA"):
            val = os.environ.get(var, "")
            if val:
                locations.append(Path(val) / "claude" / "plugins" / "svp")
    else:
        locations.append(Path("/usr/local/share/claude/plugins/svp"))
        locations.append(Path("/usr/share/claude/plugins/svp"))
    return locations


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def parse_args(argv: list = None) -> argparse.Namespace:
    """Parse CLI arguments for the SVP launcher.

    Three CLI modes:
      - ``svp new <project_name>``
      - bare ``svp`` (resume)
      - ``svp restore <project_name> --spec ... --blueprint-dir ... --context ...
        --scripts-source ... --profile ... [--plugin-path] [--skip-to]``

    ``args.command`` is never ``None`` after returning.
    """
    parser = argparse.ArgumentParser(prog="svp", description="SVP Launcher")
    subparsers = parser.add_subparsers(dest="command")

    # svp new <project_name>
    new_parser = subparsers.add_parser("new", help="Create a new SVP project")
    new_parser.add_argument("project_name", help="Name of the new project")

    # svp restore <project_name> --spec ... --blueprint-dir ... --context ...
    #   --scripts-source ... --profile ... [--plugin-path] [--skip-to]
    restore_parser = subparsers.add_parser(
        "restore", help="Restore an SVP project from existing artifacts"
    )
    restore_parser.add_argument("project_name", help="Name of the project to restore")
    restore_parser.add_argument(
        "--repo", default=None,
        help="Path to repo root for auto-discovering artifacts from docs/"
    )
    restore_parser.add_argument("--spec", default=None, help="Path to spec file")
    restore_parser.add_argument(
        "--blueprint-dir", default=None, help="Path to blueprint directory"
    )
    restore_parser.add_argument("--context", default=None, help="Path to context file")
    restore_parser.add_argument(
        "--scripts-source", default=None, help="Path to scripts source directory"
    )
    restore_parser.add_argument(
        "--profile", default=None, help="Path to project profile"
    )
    restore_parser.add_argument(
        "--plugin-path", default=None, help="Path to SVP plugin root"
    )
    restore_parser.add_argument(
        "--skip-to",
        default=None,
        choices=sorted(VALID_STAGES | {"pre_stage_3"}),
        help="Stage to skip to",
    )

    args = parser.parse_args(argv)

    # Bare `svp` (no subcommand) defaults to resume
    if args.command is None:
        args.command = "resume"

    return args


# ---------------------------------------------------------------------------
# preflight_check
# ---------------------------------------------------------------------------


def _check(label: str, passed: bool, detail: str = "", verbose: bool = True) -> Optional[str]:
    """Print a preflight check result and return error string if failed."""
    if passed:
        if verbose:
            print(f"  \u2713 {label}")
        return None
    msg = f"{label}: {detail}" if detail else label
    if verbose:
        print(f"  \u2717 {label} -- {detail}")
    return msg


def preflight_check(
    project_root: Optional[Path] = None, verbose: bool = True,
) -> List[str]:
    """Validate that required tools and runtimes are available.

    Checks in order:
      1. Claude Code installed
      2. SVP plugin loaded
      3. API credentials valid
      4. conda installed
      5. Python >= 3.11
      6. pytest importable
      7. git installed
      8. Language runtime checks from LANGUAGE_REGISTRY

    When verbose=True, prints each check result to stdout.
    Returns a list of error messages (empty if all pass).
    """
    if verbose:
        print("\nSVP 2.2 -- Preflight checks\n")

    errors: List[str] = []

    # 1. Claude Code installed
    claude_ok = shutil.which("claude") is not None
    err = _check("Claude Code installed", claude_ok,
                 "not installed or not on PATH", verbose)
    if err:
        errors.append(err)

    # 2. SVP plugin loaded
    plugin_ok = True
    try:
        _find_plugin_root()
    except FileNotFoundError:
        plugin_ok = False
    err = _check("SVP plugin loaded", plugin_ok,
                 "not found in any standard location", verbose)
    if err:
        errors.append(err)

    # 3. API credentials valid (advisory only)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if verbose:
        if has_key:
            print("  \u2713 API credentials (ANTHROPIC_API_KEY set)")
        else:
            print("  - API credentials (relying on Claude Code auth)")

    # 4. conda installed
    conda_ok = shutil.which("conda") is not None
    err = _check("conda installed", conda_ok,
                 "not installed or not on PATH", verbose)
    if err:
        errors.append(err)

    # 5. Python >= 3.11
    py_ok = sys.version_info >= (3, 11)
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    err = _check(f"Python >= 3.11 (found {py_ver})", py_ok,
                 f"found {py_ver}", verbose)
    if err:
        errors.append(err)

    # 6. pytest importable
    pytest_ok = True
    try:
        import pytest  # noqa: F401
    except ImportError:
        pytest_ok = False
    err = _check("pytest importable", pytest_ok,
                 "not importable", verbose)
    if err:
        errors.append(err)

    # 7. git installed
    git_ok = shutil.which("git") is not None
    err = _check("git installed", git_ok,
                 "not installed or not on PATH", verbose)
    if err:
        errors.append(err)

    # 8. Language runtime pre-flight from LANGUAGE_REGISTRY
    for lang_key, entry in LANGUAGE_REGISTRY.items():
        if entry.get("is_component_only", False):
            continue
        version_cmd = entry.get("version_check_command")
        if version_cmd:
            lang_ok = True
            try:
                subprocess.run(
                    version_cmd.split(),
                    capture_output=True,
                    timeout=10,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                lang_ok = False
            display = entry.get("display_name", lang_key)
            err = _check(f"{display} runtime", lang_ok,
                         f"'{version_cmd}' not available", verbose)
            if err:
                errors.append(err)

    if verbose:
        print()  # blank line after checks

    return errors


# ---------------------------------------------------------------------------
# _find_plugin_root
# ---------------------------------------------------------------------------


def _find_plugin_root() -> Path:
    """Find the SVP plugin root directory.

    Checks ``SVP_PLUGIN_ROOT`` environment variable first, then searches
    5 standard locations. Validates that the directory contains
    ``.claude-plugin/plugin.json`` with ``name == "svp"``.

    Returns the ``Path`` to the valid plugin root.
    Raises ``FileNotFoundError`` if none found.
    """
    # 1. Check environment variable
    env_root = os.environ.get("SVP_PLUGIN_ROOT")
    if env_root:
        candidate = Path(env_root)
        if _validate_plugin_dir(candidate):
            return candidate
        # Env var was explicitly set but invalid -- raise immediately
        raise FileNotFoundError(
            f"SVP_PLUGIN_ROOT is set to '{env_root}' but that directory does "
            "not contain a valid SVP plugin (.claude-plugin/plugin.json with "
            "name='svp')."
        )

    # 2. Search standard locations
    locations = _get_plugin_search_locations()
    cache_location = Path.home() / ".claude" / "plugins" / "cache" / "svp" / "svp"
    for location in locations:
        if location == cache_location:
            # Check all version subdirs, sorted
            if location.is_dir():
                subdirs = sorted(location.iterdir(), reverse=True)
                for subdir in subdirs:
                    if subdir.is_dir() and _validate_plugin_dir(subdir):
                        return subdir
        else:
            if _validate_plugin_dir(location):
                return location

    raise FileNotFoundError(
        "SVP plugin not found. Searched SVP_PLUGIN_ROOT env var and "
        "standard plugin locations."
    )


def _validate_plugin_dir(path: Path) -> bool:
    """Check if path contains .claude-plugin/plugin.json with name=='svp'."""
    plugin_json = path / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        return False
    try:
        with open(plugin_json, "r") as f:
            data = json.load(f)
        return data.get("name") == "svp"
    except (json.JSONDecodeError, OSError):
        return False


# ---------------------------------------------------------------------------
# create_new_project
# ---------------------------------------------------------------------------


def create_new_project(
    project_name: str,
    plugin_root: Path,
) -> Path:
    """Create a new SVP project.

    - Creates project directory at CWD/project_name
    - Copies scripts from plugin source
    - Copies toolchain files
    - Copies ruff.toml (set read-only after copy)
    - Copies regression test files
    - Copies hook configuration with path rewriting
    - Creates initial pipeline_state.json, svp_config.json, CLAUDE.md
    - Sets filesystem permissions
    - Returns project root path
    """
    project_root = Path.cwd() / project_name
    project_root.mkdir(parents=True, exist_ok=True)

    # Create .svp directory
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(exist_ok=True)

    # Copy scripts
    scripts_src = plugin_root / "scripts"
    if scripts_src.is_dir():
        scripts_dst = project_root / "scripts"
        if scripts_dst.exists():
            shutil.rmtree(scripts_dst)
        shutil.copytree(scripts_src, scripts_dst)

    # Copy toolchain files
    toolchain_src = plugin_root / "toolchain"
    if toolchain_src.is_dir():
        toolchain_dst = project_root / "toolchain"
        if toolchain_dst.exists():
            shutil.rmtree(toolchain_dst)
        shutil.copytree(toolchain_src, toolchain_dst)

    # Copy ruff.toml (set read-only)
    ruff_src = plugin_root / "ruff.toml"
    if ruff_src.is_file():
        ruff_dst = project_root / "ruff.toml"
        # Make writable first if it already exists (it may be read-only)
        if ruff_dst.exists():
            ruff_dst.chmod(stat.S_IRUSR | stat.S_IWUSR)
        shutil.copy2(ruff_src, ruff_dst)
        ruff_dst.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    # Create empty tests scaffold. SVP regression tests are only copied
    # for E/F builds (post-Stage-0 via copy_svp_regression_tests).
    # For A-D projects, the test agent populates tests/ during Stage 3.
    tests_dst = project_root / "tests"
    tests_dst.mkdir(exist_ok=True)
    (tests_dst / "__init__.py").write_text("")
    regressions_dst = tests_dst / "regressions"
    regressions_dst.mkdir(exist_ok=True)
    (regressions_dst / "__init__.py").write_text("")

    # Copy hook configuration with path rewriting
    hooks_src = plugin_root / ".claude-plugin"
    if hooks_src.is_dir():
        hooks_dst = project_root / ".claude-plugin"
        if hooks_dst.exists():
            shutil.rmtree(hooks_dst)
        shutil.copytree(hooks_src, hooks_dst)
        # Rewrite paths in hook config files
        _rewrite_hook_paths(hooks_dst, plugin_root, project_root)

    # Create initial pipeline_state.json
    # Bug S3-38: sub_stage must start as "hook_activation", not None
    initial_state = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "current_unit": None,
        "total_units": 0,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    state_path = project_root / ".svp" / "pipeline_state.json"
    state_path.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")

    # Create svp_config.json
    from src.unit_1.stub import DEFAULT_CONFIG

    config_path = project_root / "svp_config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    # Create CLAUDE.md (Tier 1: universal, always present)
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(
        CLAUDE_MD_TEMPLATE.format(project_name=project_name),
        encoding="utf-8",
    )

    return project_root


def copy_svp_regression_tests(project_root: Path, plugin_root: Path) -> None:
    """Copy SVP regression tests to workspace for E/F builds.

    Called by the routing script after Stage 0 completes when
    is_svp_build is true. A-D projects get an empty tests/ scaffold
    (test agent populates during Stage 3); E/F projects need SVP's
    own regression tests as carry-over artifacts.
    """
    tests_src = plugin_root / "tests"
    if not tests_src.is_dir():
        return

    tests_dst = project_root / "tests"
    if tests_dst.exists():
        shutil.rmtree(tests_dst)
    shutil.copytree(tests_src, tests_dst)


def enrich_claude_md_for_svp_build(project_root: Path) -> None:
    """Append SVP self-build addendum to CLAUDE.md for E/F projects.

    Called by the routing script after Stage 0 completes when
    is_svp_build is true. Appends Tier 2 content (bug-fixing protocol,
    stubs-as-source-of-truth, sync instructions) to the existing
    Tier 1 CLAUDE.md.

    Idempotent: checks if addendum is already present before appending.
    """
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        return

    content = claude_md.read_text(encoding="utf-8")

    # Idempotency check: don't append if already present
    if "Manual Bug-Fixing Protocol" in content:
        return

    content += CLAUDE_MD_SVP_ADDENDUM
    claude_md.write_text(content, encoding="utf-8")


def _rewrite_hook_paths(hooks_dir: Path, plugin_root: Path, project_root: Path) -> None:
    """Rewrite plugin paths to project paths in hook configuration files."""
    for hook_file in hooks_dir.rglob("*"):
        if hook_file.is_file() and hook_file.suffix in (
            ".json",
            ".yaml",
            ".yml",
            ".toml",
        ):
            try:
                content = hook_file.read_text(encoding="utf-8")
                rewritten = content.replace(str(plugin_root), str(project_root))
                hook_file.write_text(rewritten, encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                pass


def _copy_artifact(src: Path, dst: Path) -> None:
    """Copy a file or directory to the destination."""
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# auto-discover from repo (Bug S3-103)
# ---------------------------------------------------------------------------


def _auto_discover_from_repo(repo_path: Path) -> dict:
    """Auto-discover artifact paths from a repo's docs/ directory.

    Returns a dict with keys: spec_path, blueprint_dir, context_path,
    scripts_source, profile_path. Raises FileNotFoundError if required
    artifacts are missing.
    """
    docs = repo_path / "docs"
    if not docs.is_dir():
        raise FileNotFoundError(f"No docs/ directory in {repo_path}")

    discovered: dict = {}

    spec = docs / "stakeholder_spec.md"
    if not spec.exists():
        raise FileNotFoundError(f"Missing {spec}")
    discovered["spec_path"] = spec

    bp_prose_name = Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
    bp_contracts_name = Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name
    for bp_file in (bp_prose_name, bp_contracts_name):
        if not (docs / bp_file).exists():
            raise FileNotFoundError(f"Missing {docs / bp_file}")
    discovered["blueprint_dir"] = docs

    context = docs / "project_context.md"
    if not context.exists():
        raise FileNotFoundError(f"Missing {context}")
    discovered["context_path"] = context

    scripts = repo_path / "svp" / "scripts"
    if not scripts.is_dir():
        raise FileNotFoundError(f"Missing {scripts}")
    discovered["scripts_source"] = scripts

    profile = docs / "project_profile.json"
    if not profile.exists():
        raise FileNotFoundError(f"Missing {profile}")
    discovered["profile_path"] = profile

    return discovered


# ---------------------------------------------------------------------------
# restore_project
# ---------------------------------------------------------------------------


def restore_project(
    project_name: str,
    spec_path: Path,
    blueprint_dir: Path,
    context_path: Path,
    scripts_source: Path,
    profile_path: Path,
    plugin_path: Optional[Path] = None,
    skip_to: Optional[str] = None,
    repo_path: Optional[Path] = None,
) -> Path:
    """Restore an SVP project from existing artifacts.

    - Creates project directory at CWD/project_name
    - Copies spec, blueprint, context, scripts, profile from provided paths
    - If repo_path provided: writes .svp/sync_config.json (Bug S3-103)
    - If skip_to provided: sets pipeline state to skip to that stage
    - If plugin_path provided: sets SVP_PLUGIN_ROOT in subprocess environment
    - Returns project root path
    """
    project_root = Path.cwd() / project_name
    project_root.mkdir(parents=True, exist_ok=True)

    # Create .svp directory
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(exist_ok=True)

    # Copy spec
    specs_dir = project_root / "specs"
    specs_dir.mkdir(exist_ok=True)
    _copy_artifact(spec_path, specs_dir / spec_path.name)

    # Copy blueprint directory
    bp_dst = project_root / "blueprint"
    if bp_dst.exists():
        shutil.rmtree(bp_dst)
    shutil.copytree(blueprint_dir, bp_dst)

    # Copy context
    _copy_artifact(context_path, project_root / context_path.name)

    # Copy scripts
    scripts_dst = project_root / "scripts"
    if scripts_dst.exists():
        shutil.rmtree(scripts_dst)
    shutil.copytree(scripts_source, scripts_dst)

    # Copy profile
    _copy_artifact(profile_path, project_root / "project_profile.json")

    # Bug S3-43: copy references directory from source workspace if present
    # Try source_workspace/references/ first, then docs/references/ (consolidated repo layout)
    source_workspace = blueprint_dir.parent
    src_refs = source_workspace / "references"
    if not src_refs.is_dir():
        src_refs = source_workspace / "docs" / "references"
    if src_refs.is_dir():
        dst_refs = project_root / "references"
        if not dst_refs.exists():
            shutil.copytree(str(src_refs), str(dst_refs))

    # Bug S3-72: copy sync_workspace.sh from repo or source workspace
    repo_root = scripts_source.parent
    for candidate in (repo_root / "sync_workspace.sh", source_workspace / "sync_workspace.sh"):
        if candidate.is_file():
            _copy_artifact(candidate, project_root / "sync_workspace.sh")
            break

    # Bug S3-72: copy examples/ from repo or source workspace for oracle
    for candidate in (repo_root / "examples", source_workspace / "examples"):
        if candidate.is_dir():
            examples_dst = project_root / "examples"
            if not examples_dst.exists():
                shutil.copytree(str(candidate), str(examples_dst))
            break

    # Bug S3-98, S3-103: copy workspace root files from repo, docs/, or source workspace
    for rootfile in ("CLAUDE.md", "project_context.md", "ruff.toml"):
        dst = project_root / rootfile
        if not dst.exists():
            for candidate in (
                repo_root / rootfile,
                source_workspace / rootfile,
                repo_root / "docs" / rootfile,
                source_workspace / "docs" / rootfile,
            ):
                if candidate.is_file():
                    _copy_artifact(candidate, dst)
                    break

    # Bug S3-103: write sync config for sync_workspace.sh
    if repo_path is not None:
        sync_config = {"repo": str(repo_path)}
        sync_config_path = svp_dir / "sync_config.json"
        sync_config_path.write_text(
            json.dumps(sync_config, indent=2), encoding="utf-8"
        )

    # Create initial pipeline state
    initial_state = {
        "stage": "0",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 0,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }

    # If skip_to is provided, set stage accordingly
    if skip_to is not None:
        initial_state["stage"] = skip_to
        if skip_to == "pre_stage_3":
            initial_state["sub_stage"] = None
            # When --plugin-path + --skip-to pre_stage_3: initialize pass:2
            if plugin_path is not None:
                initial_state["pass"] = 2

    state_path = project_root / ".svp" / "pipeline_state.json"
    state_path.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")

    # Create svp_config.json
    from src.unit_1.stub import DEFAULT_CONFIG

    config_path = project_root / "svp_config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    return project_root


# ---------------------------------------------------------------------------
# launch_session
# ---------------------------------------------------------------------------


def launch_session(
    project_root: Path,
    skip_permissions: bool = True,
    plugin_path: Optional[Path] = None,
) -> int:
    """Launch a Claude Code session with restart signal loop.

    - Uses subprocess.run with cwd=project_root
    - Arguments: optional --dangerously-skip-permissions,
      positional prompt "run the routing script" (Bug S3-68)
    - Environment: SVP_PLUGIN_ACTIVE=1. If plugin_path: SVP_PLUGIN_ROOT=<path>
    - Restart loop: after exit, checks .svp/restart_signal.
      If present, removes signal and relaunches.
    - Returns exit code.
    """
    cmd = ["claude"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.append("run the routing script")

    env = os.environ.copy()
    env["SVP_PLUGIN_ACTIVE"] = "1"
    if plugin_path is not None:
        env["SVP_PLUGIN_ROOT"] = str(plugin_path)

    restart_signal = project_root / ".svp" / "restart_signal"

    while True:
        result = subprocess.run(cmd, cwd=str(project_root), env=env)

        # Check for restart signal
        if restart_signal.is_file():
            restart_signal.unlink()
            continue
        else:
            return result.returncode


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list = None) -> None:
    """Main entry point: parse args, run preflight, dispatch."""
    args = parse_args(argv)

    # Run preflight checks
    errors = preflight_check(verbose=True)
    if errors:
        print(f"{len(errors)} pre-flight error(s). Cannot continue.",
              file=sys.stderr)
        sys.exit(1)

    print(f"Launching SVP session ({args.command})...\n")

    if args.command == "new":
        plugin_root = _find_plugin_root()
        project_root = create_new_project(args.project_name, plugin_root)
        launch_session(project_root, plugin_path=plugin_root)
    elif args.command == "resume":
        # Auto-detect project and launch
        project_root = Path.cwd()
        plugin_root = _find_plugin_root()
        launch_session(project_root, plugin_path=plugin_root)
    elif args.command == "restore":
        plugin_path = Path(args.plugin_path) if args.plugin_path else None
        resolved_repo_path = None

        # Bug S3-103: auto-discover from repo if --repo provided
        if args.repo:
            resolved_repo_path = Path(args.repo).resolve()
            discovered = _auto_discover_from_repo(resolved_repo_path)
            spec_path = Path(args.spec) if args.spec else discovered["spec_path"]
            blueprint_dir = Path(args.blueprint_dir) if args.blueprint_dir else discovered["blueprint_dir"]
            context_path = Path(args.context) if args.context else discovered["context_path"]
            scripts_source = Path(args.scripts_source) if args.scripts_source else discovered["scripts_source"]
            profile_path = Path(args.profile) if args.profile else discovered["profile_path"]
        else:
            # Require explicit args when --repo not provided
            missing = [
                name for name in ("spec", "blueprint_dir", "context", "scripts_source", "profile")
                if getattr(args, name) is None
            ]
            if missing:
                print(
                    f"Error: --{', --'.join(n.replace('_', '-') for n in missing)} "
                    f"required when --repo is not provided",
                    file=sys.stderr,
                )
                sys.exit(1)
            spec_path = Path(args.spec)
            blueprint_dir = Path(args.blueprint_dir)
            context_path = Path(args.context)
            scripts_source = Path(args.scripts_source)
            profile_path = Path(args.profile)

        project_root = restore_project(
            project_name=args.project_name,
            spec_path=spec_path,
            blueprint_dir=blueprint_dir,
            context_path=context_path,
            scripts_source=scripts_source,
            profile_path=profile_path,
            plugin_path=plugin_path,
            skip_to=args.skip_to,
            repo_path=resolved_repo_path,
        )
        launch_session(project_root, plugin_path=plugin_path)
