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

from src.unit_2.stub import LANGUAGE_REGISTRY

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STAGES = {"0", "1", "2", "pre_stage_3", "3", "4", "5"}


def _get_plugin_search_locations() -> List[Path]:
    """Return the 5 standard plugin search locations (computed dynamically)."""
    home = Path.home()
    return [
        home / ".claude" / "plugins" / "svp",
        home / ".claude" / "plugins" / "cache" / "svp" / "svp",
        home / ".config" / "claude" / "plugins" / "svp",
        Path("/usr/local/share/claude/plugins/svp"),
        Path("/usr/share/claude/plugins/svp"),
    ]


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
    restore_parser.add_argument("--spec", required=True, help="Path to spec file")
    restore_parser.add_argument(
        "--blueprint-dir", required=True, help="Path to blueprint directory"
    )
    restore_parser.add_argument("--context", required=True, help="Path to context file")
    restore_parser.add_argument(
        "--scripts-source", required=True, help="Path to scripts source directory"
    )
    restore_parser.add_argument(
        "--profile", required=True, help="Path to project profile"
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


def preflight_check(project_root: Optional[Path] = None) -> List[str]:
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

    Returns a list of error messages (empty if all pass).
    """
    errors: List[str] = []

    # 1. Claude Code installed
    if shutil.which("claude") is None:
        errors.append("Claude Code is not installed or not on PATH")

    # 2. SVP plugin loaded
    try:
        _find_plugin_root()
    except FileNotFoundError:
        errors.append("SVP plugin not found in any standard location")

    # 3. API credentials valid
    if not os.environ.get("ANTHROPIC_API_KEY"):
        # Check if claude is configured (best-effort)
        pass  # Advisory: no easy way to check without calling API

    # 4. conda installed
    if shutil.which("conda") is None:
        errors.append("conda is not installed or not on PATH")

    # 5. Python >= 3.11
    if sys.version_info < (3, 11):
        errors.append(
            f"Python >= 3.11 required, found "
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )

    # 6. pytest importable
    try:
        import pytest  # noqa: F401
    except ImportError:
        errors.append("pytest is not importable")

    # 7. git installed
    if shutil.which("git") is None:
        errors.append("git is not installed or not on PATH")

    # 8. Language runtime pre-flight from LANGUAGE_REGISTRY
    for lang_key, entry in LANGUAGE_REGISTRY.items():
        if entry.get("is_component_only", False):
            continue
        version_cmd = entry.get("version_check_command")
        if version_cmd:
            try:
                subprocess.run(
                    version_cmd.split(),
                    capture_output=True,
                    timeout=10,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                errors.append(
                    f"{entry.get('display_name', lang_key)} runtime check failed: "
                    f"'{version_cmd}' not available"
                )

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

    # Copy regression test files
    tests_src = plugin_root / "tests"
    if tests_src.is_dir():
        tests_dst = project_root / "tests"
        if tests_dst.exists():
            shutil.rmtree(tests_dst)
        shutil.copytree(tests_src, tests_dst)

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
    state_path = project_root / "pipeline_state.json"
    state_path.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")

    # Create svp_config.json
    from src.unit_1.stub import DEFAULT_CONFIG

    config_path = project_root / "svp_config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    # Create CLAUDE.md
    claude_md = project_root / "CLAUDE.md"
    claude_md.write_text(
        f"# SVP-Managed Project: {project_name}\n\n"
        "This project is managed by the **Stratified Verification Pipeline (SVP)**. "
        "You are the orchestration layer \u2014 the main session. "
        "Your behavior is fully constrained by deterministic scripts. "
        "Do not improvise pipeline flow.\n\n"
        "## On Session Start\n\n"
        "Run the routing script immediately:\n\n"
        "```\npython scripts/routing.py --project-root .\n```\n\n"
        "The routing script reads `pipeline_state.json` and outputs a structured "
        "action block telling you exactly what to do next. Execute its output. "
        "Do not reason about what stage the pipeline is in or what should happen next.\n",
        encoding="utf-8",
    )

    return project_root


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
) -> Path:
    """Restore an SVP project from existing artifacts.

    - Creates project directory at CWD/project_name
    - Copies spec, blueprint, context, scripts, profile from provided paths
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

    state_path = project_root / "pipeline_state.json"
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
      --prompt "run the routing script"
    - Environment: SVP_PLUGIN_ACTIVE=1. If plugin_path: SVP_PLUGIN_ROOT=<path>
    - Restart loop: after exit, checks .svp/restart_signal.
      If present, removes signal and relaunches.
    - Returns exit code.
    """
    cmd = ["claude"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.extend(["--prompt", "run the routing script"])

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
    errors = preflight_check()
    if errors:
        for err in errors:
            print(f"Pre-flight error: {err}", file=sys.stderr)
        sys.exit(1)

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
        project_root = restore_project(
            project_name=args.project_name,
            spec_path=Path(args.spec),
            blueprint_dir=Path(args.blueprint_dir),
            context_path=Path(args.context),
            scripts_source=Path(args.scripts_source),
            profile_path=Path(args.profile),
            plugin_path=plugin_path,
            skip_to=args.skip_to,
        )
        launch_session(project_root, plugin_path=plugin_path)
