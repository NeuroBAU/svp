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

# Tier 1: Universal CLAUDE.md content for ALL SVP projects (A-D, E, F).
# Includes the universal Manual Bug-Fixing Protocol (Break-Glass Mode) with
# commit-to-git final step (Bug S3-126).
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

## Manual Bug-Fixing Protocol (Break-Glass Mode)

When the SVP routing mechanism is too broken to function and the human asks \
you to fix bugs directly, follow this protocol EXACTLY. This protocol is \
universal — it applies to every archetype (A-F).

**RULE 0: NEVER directly fix a bug. ALWAYS enter plan mode first.**

### Workspace vs. Delivered Repo

You operate inside this **workspace** directory. The **workspace is NOT a git \
repository**. Git lives in a sibling directory: the delivered repo at \
`{project_name}-repo/` (sibling of the workspace), whose absolute path is \
persisted in `.svp/pipeline_state.json` as `delivered_repo_path`. When the \
protocol tells you to commit, you navigate to the delivered repo (NOT the \
workspace) and run git there.

If `delivered_repo_path` is unset in pipeline state (pre-Stage-5), no delivered \
repo exists yet; in that case skip the COMMIT TO GIT step and tell the human \
the commit was deferred because the repo has not been assembled.

### Bug-Fixing Cycle (repeat for each bug)

1. **DIAGNOSE** — Identify the root cause. Trace through spec → blueprint → \
code to understand WHY the bug exists, not just what triggers it.

2. **PLAN** the fixes in:
   - a. **SPEC** — Add a bug entry to Section 24 of the stakeholder spec; fix \
any spec gaps the diagnosis revealed.
   - b. **BLUEPRINT** — Amend contracts in the affected units.
   - c. **CODE** — Identify the source files that must change.

3. **EXECUTE** — Apply the code changes.

4. **EVALUATE** — Run the relevant tests; verify the fix works in isolation.

5. **LESSONS LEARNED** — If `references/lessons_learned.md` (or a project-specific \
equivalent named in the profile) exists, append an entry describing the root \
cause, the fix, and the pattern. If no lessons-learned file exists for this \
project, skip this step.

6. **REGRESSION TESTS** — Author tests that cover ALL aspects of the bug: the \
original failure, the underlying invariant that was violated, and any adjacent \
behaviors that the fix touched. Place them under `tests/regressions/` using \
the `test_bug_<id>_*.py` naming convention.

7. **VERIFY** — Run the full test suite. All tests pass, 0 skipped, 0 failed. \
Clean up any stale test artifacts left by previous runs.

8. **COMMIT TO GIT** — Commit the fix in the **delivered repo**, NOT the workspace.
   - a. Read `delivered_repo_path` from `.svp/pipeline_state.json`. If unset, \
skip this step (see "Workspace vs. Delivered Repo" above).
   - b. `cd` into the delivered repo directory.
   - c. Read `project_profile.json` (in the workspace or delivered repo, \
whichever exists). Look up `vcs.commit_style`:
     - `"conventional"` (default) or absent → use `fix: <bug-id> <short-desc>`.
     - `"freeform"` → a short descriptive sentence.
     - `"custom"` → render `vcs.commit_template`, substituting any placeholders \
it defines (e.g., `{{bug_id}}`, `{{summary}}`).
   - d. `git add` the files changed by the fix and `git commit -m "<message>"`. \
Do not `git push`; pushing is the human's decision.
"""

# Bug S3-147: delivered-repo CLAUDE.md template for A-D archetypes.
# Distinct from CLAUDE_MD_TEMPLATE because the workspace template references
# SVP-internal concepts (workspace, pipeline_state.json, PREPARE/POST,
# routing script) that don't exist in a delivered repo. A user pulling down
# the repo doesn't run SVP. This template gives them break-glass guidance
# scoped to "working in this repo" — no workspace, no pipeline.
CLAUDE_MD_DELIVERED_REPO_TEMPLATE: str = """\
# {project_name}

This repository was generated by the Stratified Verification Pipeline (SVP). \
You may be working in it via Claude Code or another agentic interface; the \
guidance below applies in either case. The repo is a standalone deliverable: \
no SVP workspace exists alongside it, and you do NOT need the SVP pipeline \
machinery to develop here.

## Manual Bug-Fixing Protocol (Break-Glass Mode)

**Action type `invoke_break_glass`**: routing may emit this action_type when \
the human authorizes a debug session and selects a mode at \
gate_6_1_mode_classification. Follow the Manual Bug-Fixing Protocol below; \
consult `state.debug_session["mode"]` ("bug" or "enhancement") for which \
sub-flow applies. (Mode-aware sub-flows ship in cycle G2.)

When asked to fix a bug or apply a non-trivial change to this repository, \
follow this protocol.

**RULE 0: NEVER directly fix a bug. ALWAYS enter plan mode first.**

### Bug-Fixing Cycle (repeat for each bug)

1. **DIAGNOSE** — Identify the root cause. Trace through any docs (e.g., \
`docs/`, `README.md`) and the affected code to understand WHY the bug exists, \
not just what triggers it.

2. **PLAN** — Outline the changes needed: which files, which functions, \
which tests. Get the user's approval before applying.

3. **EXECUTE** — Apply the code changes.

4. **EVALUATE** — Run the relevant tests; verify the fix works in isolation.

5. **LESSONS LEARNED** (optional) — If `docs/lessons_learned.md` (or a similar \
project-specific document) exists, append a brief entry: root cause, fix, \
the pattern. If no such document exists, skip this step.

6. **REGRESSION TESTS** — Author tests that cover the original failure, the \
underlying invariant that was violated, and adjacent behaviors the fix \
touched. Place under `tests/regressions/` using `test_bug_<id>_*.py` naming \
when possible.

7. **VERIFY** — Run the full test suite (`pytest tests/` for Python projects, \
or the equivalent for the project's stack). All tests pass; 0 skipped, 0 failed.

8. **COMMIT TO GIT** — `git add` the changed files and `git commit` with a \
clear message. Match this project's existing commit style — read recent \
commits with `git log --oneline -10` first if uncertain. Do not `git push`; \
pushing is the human's decision.
"""

# Tier 2: SVP self-build OVERRIDE addendum (E/F only).
# Appended post-Stage-0 by enrich_claude_md_for_svp_build() when is_svp_build
# is true. Does NOT restate Tier 1's universal cycle — it layers overrides
# and extra steps on top. The top-level heading "## SVP Self-Build Override"
# is the idempotency marker consumed by enrich_claude_md_for_svp_build().
# (Bug S3-99, Bug S3-126.)
CLAUDE_MD_SVP_ADDENDUM: str = """\

## SVP Self-Build Override

This project is an SVP self-build (archetype E or F). The universal Manual \
Bug-Fixing Protocol in Tier 1 above applies, with the overrides and extra \
steps defined in this section. Do NOT treat this as a replacement for Tier 1 \
— it only modifies specific steps.

### EXECUTE — stubs are the single source of truth

When you reach the EXECUTE step of the Tier 1 cycle, apply code changes in \
`src/unit_*/stub.py`, never in `scripts/*.py` directly. Scripts are derived \
from stubs by `sync_workspace.sh` Step 0 (import rewriting: stubs → flat \
modules). Editing scripts directly is overwritten by the next sync.

### DEPLOYED ARTIFACTS (new step, runs after VERIFY)

If the fix touches Units that produce deployed plugin artifacts, manually \
update the corresponding `.md` files in the workspace's `svp/` directory \
before sync:

| Unit | Produces |
|------|----------|
| Unit 25 | `svp/commands/*.md` |
| Unit 26 | `svp/skills/*.md` |
| Unit 23 | `svp/agents/*.md`, `svp/hooks/*.sh` |

`sync_workspace.sh` does NOT regenerate these from Python sources. The \
deployed `.md` file is what Claude Code loads at runtime — the Python source \
is only an input to assembly and does not reach Claude Code directly.

### SYNC (new step, runs after DEPLOYED ARTIFACTS)

Run `bash sync_workspace.sh` from the workspace directory. This handles:

- Step 0: derives `scripts/*.py` from `src/unit_*/stub.py` (import rewriting).
- Scripts: workspace `scripts/` → repo `svp/scripts/`.
- Source units: workspace `src/unit_*/stub.py` → repo `src/unit_*/stub.py`.
- Docs: workspace → repo `docs/`, `specs/`, `blueprint/`, `references/`.
- Tests: workspace `tests/` → repo `tests/`.

Use `--dry-run` to preview changes before applying.

### VERIFY — test from BOTH workspace AND repo

The Tier 1 VERIFY step is strengthened: run `pytest` from BOTH the workspace \
directory AND the delivered repo directory. Do not skip either. Failures in \
one but not the other indicate stale test files, path-resolution divergence, \
or permission issues that must be resolved before commit.

### COMMIT TO GIT (Tier 1 step, still terminal)

The Tier 1 COMMIT TO GIT step is unchanged and remains the terminal action. \
The SYNC step above has already propagated your workspace changes into the \
delivered repo, so `git add` inside `delivered_repo_path` will see the fix.

Do NOT add a second commit in the workspace — the workspace has no git \
repository, and the delivered repo is the single authoritative location for \
git history.
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

    # 2a. User-scope svp@svp leak advisory (Bug S3-128)
    # Advisory only: warn when ~/.claude/settings.json still has svp@svp
    # enabled at user scope (a pre-S3-123 residual state). Does not fail
    # preflight. See spec §24.141 and §4.4 migration story.
    leak_msg = check_user_scope_svp_leak()
    if leak_msg and verbose:
        print(f"  ! {leak_msg}")

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
# check_user_scope_svp_leak (Bug S3-128)
# ---------------------------------------------------------------------------


def check_user_scope_svp_leak() -> Optional[str]:
    """Detect whether user-scope ``~/.claude/settings.json`` leaks ``svp@svp``.

    Returns an advisory message string if the leak is detected, or ``None``
    if no leak is present, the file does not exist, or the file is
    unparseable. Never raises.

    A "leak" is defined as user-scope ``settings.json`` having
    ``enabledPlugins["svp@svp"] == True``. This enables SVP in every
    Claude Code session on the machine regardless of cwd — the exact
    failure mode Bug S3-123 migrated users away from. This helper is
    **advisory and read-only**: it does not mutate the file, does not
    fail preflight, and does not block the launcher. It only informs
    the user that a machine-wide leak may still be in place from a
    pre-S3-123 install.

    Every failure mode (missing file, corrupt JSON, permission denied,
    wrong types) is treated as "no leak detected" and returns ``None``.
    This is pure detection — the helper must never raise, because it
    runs from inside ``preflight_check`` and a crash here would block
    the launcher for a check that is advisory by design.

    The returned advisory message (when non-``None``) is guaranteed to
    contain the substrings ``"svp@svp"`` and ``"user scope"``, to
    reference the migration command
    ``claude plugin uninstall svp@svp --scope user``, and to cite
    spec §4.4. Regression tests lock these invariants.
    """
    user_settings = Path.home() / ".claude" / "settings.json"
    if not user_settings.is_file():
        return None
    try:
        data = json.loads(user_settings.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    enabled = data.get("enabledPlugins")
    if not isinstance(enabled, dict):
        return None
    if enabled.get("svp@svp") is not True:
        return None
    return (
        f"svp@svp is enabled at user scope in {user_settings}. "
        "SVP will load in every Claude Code session on this machine "
        "regardless of working directory. To migrate to project scope, "
        "run: claude plugin uninstall svp@svp --scope user "
        "(see spec §4.4)."
    )


# ---------------------------------------------------------------------------
# _find_plugin_root
# ---------------------------------------------------------------------------


def _find_plugin_root() -> Path:
    """Find the SVP plugin root directory.

    Checks ``SVP_PLUGIN_ROOT`` environment variable first, then performs a
    **two-pass search** over standard locations (Bug S3-127):

    - **First pass:** return only candidates whose parent directory is a
      valid marketplace root (contains ``.claude-plugin/marketplace.json``
      listing an ``svp`` plugin). This prefers source-repo installs over
      stale cache snapshots.
    - **Second pass:** fall back to any candidate with a valid
      ``.claude-plugin/plugin.json`` (pre-S3-127 behavior). Preserves
      compatibility for users with only a cache install — downstream
      callers that need a marketplace will hard-fail with a clear message.

    Returns the ``Path`` to the valid plugin root.
    Raises ``FileNotFoundError`` if no candidate is found in either pass.
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

    # 2. Enumerate all candidates from standard locations
    candidates: List[Path] = []
    locations = _get_plugin_search_locations()
    cache_location = Path.home() / ".claude" / "plugins" / "cache" / "svp" / "svp"
    for location in locations:
        if location == cache_location:
            if location.is_dir():
                subdirs = sorted(location.iterdir(), reverse=True)
                for subdir in subdirs:
                    if subdir.is_dir() and _validate_plugin_dir(subdir):
                        candidates.append(subdir)
        else:
            if _validate_plugin_dir(location):
                candidates.append(location)

    # 3. First pass: prefer candidates whose parent is a valid marketplace.
    # Bug S3-127: a candidate whose parent has no marketplace.json is
    # unusable by ensure_project_settings(). Skip such candidates in the
    # first pass so the source-repo install wins over a cache snapshot.
    for candidate in candidates:
        if _is_valid_marketplace_dir(candidate.parent):
            return candidate

    # 4. Second pass: any validated candidate (backward compatibility).
    if candidates:
        return candidates[0]

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
# _find_marketplace_root (Bug S3-127)
# ---------------------------------------------------------------------------


def _is_valid_marketplace_dir(path: Path) -> bool:
    """Check if ``path`` is a valid SVP marketplace root.

    A directory is a valid marketplace root iff (Bug S3-127):
      (a) ``<path>/.claude-plugin/marketplace.json`` exists and is parseable,
      (b) the parsed object has a ``plugins`` array, and
      (c) at least one entry in ``plugins`` has ``name == "svp"``.

    All three conditions must hold. File existence alone is not sufficient —
    the marketplace must actually advertise the SVP plugin.
    """
    marketplace_json = path / ".claude-plugin" / "marketplace.json"
    if not marketplace_json.is_file():
        return False
    try:
        with open(marketplace_json, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return False
    for entry in plugins:
        if isinstance(entry, dict) and entry.get("name") == "svp":
            return True
    return False


def _find_marketplace_root(plugin_root: Path) -> Optional[Path]:
    """Locate a directory that can be registered as the SVP marketplace source.

    Returns a ``Path`` to a directory containing ``.claude-plugin/marketplace.json``
    whose ``plugins`` array lists an entry with ``name == "svp"``, or ``None``
    if no such directory can be located.

    Resolution order (first hit wins):

    1. ``SVP_MARKETPLACE_ROOT`` environment variable. If set and valid, returned.
       If set but invalid, raises ``FileNotFoundError`` — explicit user intent
       must not be silently ignored.
    2. ``plugin_root.parent`` if it is a valid marketplace directory. Fast path
       for source-repo layouts (``<repo>/svp/`` with marketplace at ``<repo>/``).
    3. ``__file__`` walk-up. Walks parent directories of this module's own
       location on disk and returns the first ancestor that is a valid
       marketplace root. The launcher is itself part of the plugin, so its
       own location transitively identifies a valid marketplace when imported
       from a source tree (rather than a site-packages reinstall).

    Claude Code's internal plugin cache layout
    (``~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/``) is NOT a
    valid marketplace root — the cache parent directory contains no
    ``marketplace.json``. This helper rejects such paths rather than writing
    them into settings.
    """
    # 1. SVP_MARKETPLACE_ROOT env var
    env_root = os.environ.get("SVP_MARKETPLACE_ROOT")
    if env_root:
        candidate = Path(env_root)
        if _is_valid_marketplace_dir(candidate):
            return candidate.resolve()
        raise FileNotFoundError(
            f"SVP_MARKETPLACE_ROOT is set to '{env_root}' but that directory "
            "does not contain a valid SVP marketplace "
            "(.claude-plugin/marketplace.json listing a plugin named 'svp')."
        )

    # 2. plugin_root.parent fast path (source-repo layout)
    parent_candidate = plugin_root.parent.resolve()
    if _is_valid_marketplace_dir(parent_candidate):
        return parent_candidate

    # 3. __file__ walk-up
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if _is_valid_marketplace_dir(ancestor):
            return ancestor

    return None


# ---------------------------------------------------------------------------
# ensure_project_settings (Bug S3-123)
# ---------------------------------------------------------------------------


def ensure_project_settings(project_root: Path, plugin_root: Path) -> None:
    """Write <project_root>/.claude/settings.json for project-scoped SVP activation.

    Creates or updates ``<project_root>/.claude/settings.json`` so Claude Code
    loads the SVP plugin via project-scoped marketplace enablement (spec §4.4).
    This replaces reliance on user-scope enablement (``~/.claude/settings.json``)
    which leaked SVP into every Claude Code session on the machine regardless
    of working directory.

    Two keys are written:
      - ``extraKnownMarketplaces.svp.source`` — registers the marketplace at
        the directory located by :func:`_find_marketplace_root`, which must
        contain ``.claude-plugin/marketplace.json`` listing an ``svp`` plugin.
      - ``enabledPlugins["svp@svp"]`` — set to ``True`` to enable the plugin
        when Claude Code is launched from ``project_root``.

    Properties (all load-bearing):
      1. **Idempotent** — re-running with the same ``(project_root, plugin_root)``
         produces a byte-equal file.
      2. **Non-destructive** — all other pre-existing keys are preserved
         byte-for-byte. Only the two SVP-related keys above are touched.
      3. **Self-healing (widened by Bug S3-127)** — the helper rewrites
         ``extraKnownMarketplaces.svp.source.path`` when either (a) the stored
         path differs from the freshly-computed marketplace root, OR (b) the
         stored path does not contain ``.claude-plugin/marketplace.json``.
         The second clause catches cache-parent paths written by earlier
         versions of the helper and converts them to loud failures on the
         next run.
      4. **Corrupt-JSON recovery** — if the pre-existing file is unparseable
         JSON, the helper starts from an empty dict rather than raising.
      5. **Atomic write** — writes to ``settings.json.tmp`` then calls
         ``Path.replace()`` so interrupted writes do not leave a partial or
         corrupt ``settings.json``.
      6. **Marketplace-root validated (Bug S3-127)** — the path written into
         ``extraKnownMarketplaces.svp.source.path`` must resolve to a real
         directory containing ``.claude-plugin/marketplace.json`` listing an
         ``svp`` plugin. If no such directory can be located, the helper
         raises ``FileNotFoundError`` with an actionable message. Silent
         fallback to ``plugin_root.parent`` is prohibited.

    Does NOT invoke ``subprocess``. The ``claude plugin install svp@svp
    --scope project`` CLI command is a user migration step, not a runtime
    dependency.

    Parameters
    ----------
    project_root
        The SVP pipeline directory (the one containing ``.svp/``, ``specs/``,
        ``blueprint/``, etc.). The ``.claude/settings.json`` file is written
        inside this directory.
    plugin_root
        The SVP plugin inner directory (e.g., ``<repo>/svp/``). Passed to
        :func:`_find_marketplace_root` which tries ``plugin_root.parent``
        first, then walks up from the launcher's own ``__file__``.

    Raises
    ------
    FileNotFoundError
        If :func:`_find_marketplace_root` cannot locate a valid marketplace
        root. The message instructs the user to set ``SVP_MARKETPLACE_ROOT``.
    OSError
        If the settings directory cannot be created or the file cannot be
        written. Corrupt JSON in the pre-existing file is handled gracefully
        (recovered to empty dict); only I/O failures raise.
    """
    marketplace_path = _find_marketplace_root(plugin_root)
    if marketplace_path is None:
        raise FileNotFoundError(
            "Cannot locate a valid SVP marketplace root. The discovered "
            f"plugin at '{plugin_root}' has no '.claude-plugin/marketplace.json' "
            "in its parent, and no ancestor of the launcher's own location "
            "contains one either. Set SVP_MARKETPLACE_ROOT=<path-to-svp-source-repo> "
            "to the directory containing '.claude-plugin/marketplace.json', "
            "or run from a directory where the SVP launcher can discover it "
            "via its own __file__."
        )
    marketplace_root = str(marketplace_path)

    settings_dir = project_root / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"

    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text())
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            # Corrupt JSON recovery: start fresh rather than crashing.
            data = {}
    else:
        data = {}

    extra = data.get("extraKnownMarketplaces")
    if not isinstance(extra, dict):
        extra = {}
        data["extraKnownMarketplaces"] = extra
    extra["svp"] = {
        "source": {
            "source": "directory",
            "path": marketplace_root,
        }
    }

    enabled = data.get("enabledPlugins")
    if not isinstance(enabled, dict):
        enabled = {}
        data["enabledPlugins"] = enabled
    enabled["svp@svp"] = True

    # Atomic write: write to .tmp then rename. Prevents corruption on
    # interrupted writes (Ctrl-C, kernel panic, power loss).
    tmp = settings_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(settings_path)


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

    # Bug S3-108 / Bug S3-145: deploy hook shell scripts to .claude/scripts/.
    # The plugin cache layout places hook scripts at plugin_root/hooks/,
    # NOT plugin_root/svp/hooks/. The earlier assumption (svp/hooks/) caused
    # silent deployment failures because the directory didn't exist; the
    # non_svp_protection.sh gate then failed open. See spec §24.158.
    hooks_scripts_src = plugin_root / "hooks"
    if hooks_scripts_src.is_dir():
        hooks_scripts_dst = project_root / ".claude" / "scripts"
        hooks_scripts_dst.mkdir(parents=True, exist_ok=True)
        for sh_file in hooks_scripts_src.glob("*.sh"):
            shutil.copy2(str(sh_file), str(hooks_scripts_dst / sh_file.name))
            (hooks_scripts_dst / sh_file.name).chmod(0o755)

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
    """Append SVP self-build override addendum to CLAUDE.md for E/F projects.

    Called by the routing script after Stage 0 completes when
    is_svp_build is true. Appends Tier 2 override content (stubs-as-source-
    of-truth, deployed artifacts, sync, test-from-both) on top of the
    universal Tier 1 CLAUDE.md (which already contains the universal Manual
    Bug-Fixing Protocol per Bug S3-126).

    Idempotent: checks for the Tier-2-unique marker "SVP Self-Build Override"
    before appending. The pre-S3-126 marker ("Manual Bug-Fixing Protocol")
    cannot be used here because that string now appears in Tier 1 by default,
    which would short-circuit every call and prevent Tier 2 from ever
    appending.
    """
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        return

    content = claude_md.read_text(encoding="utf-8")

    # Idempotency check: Tier-2-unique marker, not the Tier-1 bug protocol heading.
    if "SVP Self-Build Override" in content:
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

    # Bug S3-108: deploy hook shell scripts to .claude/scripts/
    # repo_root is scripts_source.parent (e.g., repo/svp/), so hooks are at sibling hooks/
    hooks_scripts_src = repo_root / "hooks"
    if hooks_scripts_src.is_dir():
        hooks_scripts_dst = project_root / ".claude" / "scripts"
        hooks_scripts_dst.mkdir(parents=True, exist_ok=True)
        for sh_file in hooks_scripts_src.glob("*.sh"):
            shutil.copy2(str(sh_file), str(hooks_scripts_dst / sh_file.name))
            (hooks_scripts_dst / sh_file.name).chmod(0o755)

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
        # Bug S3-123: write project-scoped .claude/settings.json so Claude
        # Code loads SVP in this directory only (not every directory on the
        # machine). See spec §4.4.
        ensure_project_settings(project_root, plugin_root)
        launch_session(project_root, plugin_path=plugin_root)
    elif args.command == "resume":
        # Auto-detect project and launch
        project_root = Path.cwd()
        plugin_root = _find_plugin_root()
        # Bug S3-123: write project-scoped .claude/settings.json. Idempotent
        # on re-entry and self-heals stale marketplace paths if the user has
        # moved the SVP repo since the last run.
        ensure_project_settings(project_root, plugin_root)
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
        # Bug S3-123: write project-scoped .claude/settings.json for the
        # restored project. plugin_path may be None when SVP was discovered
        # via _find_plugin_root; resolve it now for the settings file.
        resolved_plugin_root = plugin_path if plugin_path else _find_plugin_root()
        ensure_project_settings(project_root, resolved_plugin_root)
        launch_session(project_root, plugin_path=plugin_path)
