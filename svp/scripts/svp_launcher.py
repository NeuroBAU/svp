#!/usr/bin/env python3
# Unit 24: SVP Launcher
# Self-contained CLI tool -- NO imports from other SVP units.

from typing import Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import sys
import argparse
import shutil
import os
import json
import stat
import time
import importlib.util
import socket

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESTART_SIGNAL_FILE: str = ".svp/restart_signal"
STATE_FILE: str = "pipeline_state.json"
CONFIG_FILE: str = "svp_config.json"
SVP_DIR: str = ".svp"
MARKERS_DIR: str = ".svp/markers"
CLAUDE_MD_FILE: str = "CLAUDE.md"
README_SVP_FILE: str = "README_SVP.txt"
SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

PROJECT_DIRS: List[str] = [
    ".svp", ".svp/markers", ".claude", "scripts", "ledgers",
    "logs", "logs/rollback", "specs", "specs/history",
    "blueprint", "blueprint/history", "references", "references/index",
    "src", "tests", "data",
]

# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------

def _is_svp_plugin_dir(path: Path) -> bool:
    """Check whether a directory contains .claude-plugin/plugin.json with name 'svp'."""
    plugin_json = path / ".claude-plugin" / "plugin.json"
    try:
        with open(plugin_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("name") == "svp"
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return False


def _find_plugin_root() -> Optional[Path]:
    """Locate the SVP plugin root directory.

    Checks SVP_PLUGIN_ROOT env var first, then standard plugin locations.
    """
    # Check environment variable first
    env_root = os.environ.get("SVP_PLUGIN_ROOT")
    if env_root:
        p = Path(env_root)
        if _is_svp_plugin_dir(p):
            return p

    home = Path.home()

    # Standard Claude Code plugin locations, in order
    candidates: List[Path] = [
        home / ".claude" / "plugins" / "svp",
    ]

    # All version directories under ~/.claude/plugins/cache/svp/svp/*/
    cache_base = home / ".claude" / "plugins" / "cache" / "svp" / "svp"
    if cache_base.is_dir():
        version_dirs = sorted(cache_base.iterdir())
        candidates.extend(version_dirs)

    candidates.extend([
        home / ".config" / "claude" / "plugins" / "svp",
        Path("/usr/local/share/claude/plugins/svp"),
        Path("/usr/share/claude/plugins/svp"),
    ])

    for candidate in candidates:
        if candidate.is_dir() and _is_svp_plugin_dir(candidate):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_header(text: str) -> None:
    """Print a decorated header line with = border and centered text."""
    width = 60
    border = "=" * width
    centered = text.center(width)
    print(border)
    print(centered)
    print(border)


def _print_status(name: str, passed: bool, message: str) -> None:
    """Print a single prerequisite result with pass/fail icon."""
    icon = "\u2713" if passed else "\u2717"
    status = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {name}: {status} - {message}")


def _print_transition(message: str) -> None:
    """Print a session transition message between restart cycles."""
    print()
    print("-" * 60)
    print(f"  {message}")
    print("-" * 60)
    print()


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments. Supports 'new', 'restore', and default 'resume'."""
    parser = argparse.ArgumentParser(
        prog="svp",
        description="SVP Launcher - Stratified Verification Pipeline session manager",
    )

    subparsers = parser.add_subparsers(dest="command")

    # 'new' subcommand
    new_parser = subparsers.add_parser("new", help="Create a new SVP project")
    new_parser.add_argument("project_name", type=str, help="Name of the project")
    new_parser.add_argument(
        "--parent-dir", type=str, default=None,
        help="Parent directory for the project (default: current directory)",
    )

    # 'restore' subcommand
    restore_parser = subparsers.add_parser(
        "restore", help="Create a project with pre-existing spec and blueprint",
    )
    restore_parser.add_argument("project_name", type=str, help="Name of the project")
    restore_parser.add_argument(
        "--spec", type=str, required=True,
        help="Path to the stakeholder spec file",
    )
    restore_parser.add_argument(
        "--blueprint", type=str, required=True,
        help="Path to the blueprint file",
    )
    restore_parser.add_argument(
        "--context", type=str, default=None,
        help="Path to the project context file (optional)",
    )
    restore_parser.add_argument(
        "--parent-dir", type=str, default=None,
        help="Parent directory for the project (default: current directory)",
    )
    restore_parser.add_argument(
        "--scripts-source", type=str, default=None,
        help="Override where scripts are copied from (for development)",
    )

    args = parser.parse_args(argv)

    # Default to 'resume' if no subcommand given
    if args.command is None:
        args.command = "resume"

    return args


# ---------------------------------------------------------------------------
# Prerequisite checking (8 checks, each returns (passed, message))
# ---------------------------------------------------------------------------

def check_claude_code() -> Tuple[bool, str]:
    """Check that Claude Code is installed and functional."""
    try:
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, f"Claude Code {version}")
        return (False, f"Claude Code returned exit code {result.returncode}")
    except FileNotFoundError:
        return (False, "Claude Code executable not found. Install from https://claude.ai/code")
    except subprocess.TimeoutExpired:
        return (False, "Claude Code version check timed out")
    except Exception as e:
        return (False, f"Error checking Claude Code: {e}")


def check_svp_plugin() -> Tuple[bool, str]:
    """Check that the SVP plugin is installed."""
    plugin_root = _find_plugin_root()
    if plugin_root is None:
        return (False, "SVP plugin not found. Check your plugin installation.")
    # _find_plugin_root already validates the manifest via _is_svp_plugin_dir
    return (True, f"SVP plugin found at {plugin_root}")


def check_api_credentials() -> Tuple[bool, str]:
    """Check that API credentials are available."""
    # Check environment variable first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return (True, "ANTHROPIC_API_KEY environment variable is set")

    # Fall back to claude auth status
    try:
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "auth", "status"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return (True, "Authenticated via Claude Code")
        return (False, "Not authenticated. Set ANTHROPIC_API_KEY or run 'claude auth login'")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return (False, "Not authenticated. Set ANTHROPIC_API_KEY or run 'claude auth login'")


def check_conda() -> Tuple[bool, str]:
    """Check that conda is installed and functional."""
    try:
        result = subprocess.run(
            ["conda", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, f"{version}")
        return (False, f"conda returned exit code {result.returncode}")
    except FileNotFoundError:
        return (False, "conda not found. Install Miniconda or Anaconda.")
    except subprocess.TimeoutExpired:
        return (False, "conda version check timed out")
    except Exception as e:
        return (False, f"Error checking conda: {e}")


def check_python() -> Tuple[bool, str]:
    """Check that Python >= 3.10 is available."""
    try:
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version_str = result.stdout.strip()
            # Parse version, e.g. "Python 3.10.4"
            parts = version_str.split()
            if len(parts) >= 2:
                version_num = parts[1]
                version_parts = version_num.split(".")
                major = int(version_parts[0])
                minor = int(version_parts[1]) if len(version_parts) > 1 else 0
                if major > 3 or (major == 3 and minor >= 10):
                    return (True, f"Python {version_num}")
                return (False, f"Python {version_num} found, but >= 3.10 required")
            return (False, f"Could not parse Python version: {version_str}")
        return (False, f"Python returned exit code {result.returncode}")
    except subprocess.TimeoutExpired:
        return (False, "Python version check timed out")
    except Exception as e:
        return (False, f"Error checking Python: {e}")


def check_pytest() -> Tuple[bool, str]:
    """Check that pytest is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            return (True, f"{version}")
        return (False, f"pytest returned exit code {result.returncode}")
    except subprocess.TimeoutExpired:
        return (False, "pytest version check timed out")
    except Exception as e:
        return (False, f"Error checking pytest: {e}")


def check_git() -> Tuple[bool, str]:
    """Check that git is installed and user is configured."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return (False, f"git returned exit code {result.returncode}")

        version = result.stdout.strip()

        # Check user.name
        name_result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, timeout=10,
        )
        # Check user.email
        email_result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=10,
        )

        if name_result.returncode != 0 or not name_result.stdout.strip():
            return (
                False,
                "Git user.name not configured. Run: git config --global user.name \"Your Name\"",
            )
        if email_result.returncode != 0 or not email_result.stdout.strip():
            return (
                False,
                "Git user.email not configured. Run: git config --global user.email \"you@example.com\"",
            )

        return (True, f"{version}")
    except FileNotFoundError:
        return (False, "git not found. Install git.")
    except subprocess.TimeoutExpired:
        return (False, "git version check timed out")
    except Exception as e:
        return (False, f"Error checking git: {e}")


def check_network() -> Tuple[bool, str]:
    """Check network connectivity to the Anthropic API."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--connect-timeout", "5", "https://api.anthropic.com"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            code = result.stdout.strip()
            return (True, f"Anthropic API reachable (HTTP {code})")
        # Fall through to DNS fallback
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    # Fallback: DNS resolution via socket
    try:
        socket.getaddrinfo("api.anthropic.com", 443)
        return (True, "Anthropic API DNS resolution successful")
    except socket.gaierror:
        return (False, "Cannot reach api.anthropic.com. Check your network connection.")
    except Exception as e:
        return (False, f"Network check failed: {e}")


def run_all_prerequisites() -> List[Tuple[str, bool, str]]:
    """Run all 8 prerequisite checks in order. Returns list of (name, passed, message)."""
    checks = [
        ("Claude Code", check_claude_code),
        ("SVP Plugin", check_svp_plugin),
        ("API Credentials", check_api_credentials),
        ("Conda", check_conda),
        ("Python", check_python),
        ("Pytest", check_pytest),
        ("Git", check_git),
        ("Network", check_network),
    ]
    results: List[Tuple[str, bool, str]] = []
    for name, check_fn in checks:
        passed, message = check_fn()
        results.append((name, passed, message))
    return results


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

def create_project_directory(project_name: str, parent_dir: Path) -> Path:
    """Create project directory structure. Raises FileExistsError if it already exists."""
    project_root = parent_dir / project_name
    if project_root.exists():
        raise FileExistsError(f"Project directory already exists: {project_root}")

    project_root.mkdir(parents=True)
    for d in PROJECT_DIRS:
        (project_root / d).mkdir(parents=True, exist_ok=True)

    return project_root


def copy_scripts_to_workspace(plugin_root: Path, project_root: Path) -> None:
    """Copy the entire scripts/ directory from the plugin to the project workspace."""
    src_scripts = plugin_root / "scripts"
    if not src_scripts.is_dir():
        raise RuntimeError(
            f"Plugin scripts directory not found at {src_scripts}. "
            f"The SVP plugin installation may be corrupted."
        )
    dst_scripts = project_root / "scripts"
    if dst_scripts.exists():
        shutil.rmtree(dst_scripts)
    shutil.copytree(str(src_scripts), str(dst_scripts))


def generate_claude_md(project_root: Path, project_name: str) -> None:
    """Generate CLAUDE.md. Tries template module first, falls back to inline."""
    template_module_path = project_root / "scripts" / "templates" / "claude_md.py"

    content = None
    if template_module_path.is_file():
        try:
            spec = importlib.util.spec_from_file_location(
                "claude_md_template", str(template_module_path),
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                render_fn = getattr(mod, "render_claude_md", None)
                if render_fn:
                    content = render_fn(project_name)
        except Exception:
            content = None

    if content is None:
        content = _generate_claude_md_fallback(project_name)

    claude_md_path = project_root / CLAUDE_MD_FILE
    with open(claude_md_path, "w", encoding="utf-8") as f:
        f.write(content)


def _generate_claude_md_fallback(project_name: str) -> str:
    """Return a complete CLAUDE.md string inline without any external dependencies."""
    return f"""# SVP-Managed Project: {project_name}

This project is managed by the **Stratified Verification Pipeline (SVP)**. You are the orchestration layer \u2014 the main session. Your behavior is fully constrained by deterministic scripts. Do not improvise pipeline flow.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and outputs a structured action block telling you exactly what to do next. Execute its output. Do not reason about what stage the pipeline is in or what should happen next.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated:

1. **Run the routing script** \u2192 receive a structured action block.
2. **Run the PREPARE command** (if present) \u2192 produces a task prompt or gate prompt file.
3. **Execute the ACTION** (invoke agent / run command / present gate).
4. **Write the result to `.svp/last_status.txt`** (agent terminal status line or constructed command status).
5. **Run the POST command** (if present) \u2192 updates pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps.

## Verbatim Task Prompt Relay

When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.

## Do Not Improvise

- Do not decide which state update to call.
- Do not construct arguments for state scripts.
- Do not evaluate agent outputs for correctness.
- Do not hold domain conversation history.
- Do not reason about pipeline flow.

The routing script makes every decision. You execute.

## Human Input During Autonomous Sequences

During autonomous sequences (agent invocations, command executions), defer human input. If the human types during an autonomous sequence, acknowledge briefly and defer: complete the current action cycle before engaging.

## Detailed Protocol

For the complete orchestration protocol \u2014 action type handling, status line construction, gate presentation rules, session boundary handling \u2014 refer to the **SVP orchestration skill** (`svp-orchestration`).
"""


def write_initial_state(project_root: Path, project_name: str) -> None:
    """Write initial pipeline_state.json. Tries template, falls back to inline."""
    state_path = project_root / STATE_FILE
    template_path = project_root / "scripts" / "templates" / "pipeline_state_initial.json"

    now = datetime.now(timezone.utc).isoformat()

    if template_path.is_file():
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            state["project_name"] = project_name
            state["created_at"] = now
            state["updated_at"] = now
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.write("\n")
            return
        except (json.JSONDecodeError, OSError):
            pass

    # Inline fallback
    state = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "current_unit": None,
        "total_units": None,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": project_name,
        "last_action": None,
        "debug_session": None,
        "debug_history": [],
        "created_at": now,
        "updated_at": now,
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def write_default_config(project_root: Path) -> None:
    """Write default svp_config.json. Tries template, falls back to inline."""
    config_path = project_root / CONFIG_FILE
    template_path = project_root / "scripts" / "templates" / "svp_config_default.json"

    if template_path.is_file():
        try:
            shutil.copy2(str(template_path), str(config_path))
            return
        except OSError:
            pass

    # Inline fallback
    config = {
        "iteration_limit": 3,
        "models": {
            "test_agent": "claude-opus-4-6",
            "implementation_agent": "claude-opus-4-6",
            "help_agent": "claude-sonnet-4-6",
            "default": "claude-opus-4-6",
        },
        "context_budget_override": None,
        "context_budget_threshold": 65,
        "compaction_character_threshold": 200,
        "auto_save": True,
        "skip_permissions": True,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def write_readme_svp(project_root: Path) -> None:
    """Write README_SVP.txt. Tries template, falls back to inline."""
    readme_path = project_root / README_SVP_FILE
    template_path = project_root / "scripts" / "templates" / "readme_svp.txt"

    if template_path.is_file():
        try:
            shutil.copy2(str(template_path), str(readme_path))
            return
        except OSError:
            pass

    # Inline fallback
    content = """\
================================================================================
                        SVP-MANAGED PROJECT NOTICE
================================================================================

This project is managed by the Stratified Verification Pipeline (SVP).

IMPORTANT: Files in this project are protected by a two-layer write
authorization system:

  1. Pre-commit hooks prevent unauthorized modifications to pipeline-controlled
     files (pipeline_state.json, blueprint documents, verified source files).

  2. The SVP orchestration layer enforces write permissions at runtime,
     ensuring that only authorized pipeline operations can modify protected
     artifacts.

Do NOT manually edit pipeline-controlled files. All changes must flow through
the SVP pipeline to maintain verification integrity.

To interact with this project, use the `svp` command:

    svp start          Start or resume the pipeline
    svp status         Show current pipeline state
    svp restore        Restore example project files
    svp help           Show available commands

For more information about SVP, refer to the project documentation.

================================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Filesystem permissions
# ---------------------------------------------------------------------------

def set_filesystem_permissions(project_root: Path, read_only: bool) -> None:
    """Set filesystem permissions on the project root. Best-effort."""
    try:
        if read_only:
            subprocess.run(
                ["chmod", "-R", "a-w", str(project_root)],
                capture_output=True, timeout=30,
            )
        else:
            subprocess.run(
                ["chmod", "-R", "u+w", str(project_root)],
                capture_output=True, timeout=30,
            )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        pass


# ---------------------------------------------------------------------------
# Config reading helper (inline, no external imports)
# ---------------------------------------------------------------------------

def _load_launch_config(project_root: Path) -> dict:
    """Load svp_config.json from project root. Returns empty dict on failure."""
    config_path = project_root / CONFIG_FILE
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError, PermissionError):
        return {}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def launch_claude_code(project_root: Path, plugin_dir: Path) -> int:
    """Launch Claude Code subprocess with SVP_PLUGIN_ACTIVE set."""
    # Check that claude is available
    if not shutil.which("claude"):
        raise RuntimeError("Session launch failed: Claude Code executable not found")

    # Create environment copy with SVP_PLUGIN_ACTIVE (NOT in launcher's own env)
    env = os.environ.copy()
    env[SVP_ENV_VAR] = "1"

    # Read skip_permissions from config (default True if missing or unreadable,
    # because launching claude without --dangerously-skip-permissions from a
    # subprocess hangs waiting for interactive permission approval)
    config = _load_launch_config(project_root)
    skip_permissions = config.get("skip_permissions", True)

    # Build command
    cmd = ["claude"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.append("run the routing script")

    try:
        result = subprocess.run(cmd, cwd=str(project_root), env=env)
        return result.returncode
    except Exception as e:
        raise RuntimeError(f"Session launch failed: {e}")


def detect_restart_signal(project_root: Path) -> Optional[str]:
    """Read .svp/restart_signal if it exists. Returns content or None."""
    signal_path = project_root / RESTART_SIGNAL_FILE
    try:
        with open(signal_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content if content else ""
    except (FileNotFoundError, OSError):
        return None


def clear_restart_signal(project_root: Path) -> None:
    """Delete the restart signal file."""
    signal_path = project_root / RESTART_SIGNAL_FILE
    try:
        signal_path.unlink(missing_ok=True)
    except OSError:
        pass


def run_session_loop(project_root: Path, plugin_dir: Path) -> int:
    """Run the session loop: launch, check restart, repeat."""
    exit_code = 0
    while True:
        # Restore permissions (make writable)
        set_filesystem_permissions(project_root, read_only=False)

        # Launch Claude Code
        exit_code = launch_claude_code(project_root, plugin_dir)

        # Check for restart signal
        signal = detect_restart_signal(project_root)
        if signal is not None:
            # Restart requested
            clear_restart_signal(project_root)
            set_filesystem_permissions(project_root, read_only=True)
            _print_transition(f"Session restart: {signal}" if signal else "Session restarting...")
            continue
        else:
            # No restart signal -- exit
            set_filesystem_permissions(project_root, read_only=True)
            print("\nSVP session ended.")
            break

    return exit_code


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

def detect_existing_project(directory: Path) -> bool:
    """Return True if both pipeline_state.json and .svp/ exist in the directory."""
    state_exists = (directory / STATE_FILE).is_file()
    svp_dir_exists = (directory / SVP_DIR).is_dir()
    return state_exists and svp_dir_exists


def resume_project(project_root: Path, plugin_dir: Path) -> int:
    """Resume an existing SVP project session."""
    # Display current stage info
    state_path = project_root / STATE_FILE
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        stage = state.get("stage", "unknown")
        sub_stage = state.get("sub_stage", "")
        project_name = state.get("project_name", "unknown")
        print(f"Resuming project: {project_name}")
        print(f"Current stage: {stage} ({sub_stage})")
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Could not read pipeline state: {e}")
        print("Attempting to resume anyway...")

    return run_session_loop(project_root, plugin_dir)


# ---------------------------------------------------------------------------
# Hook copying helper
# ---------------------------------------------------------------------------

def _copy_hooks(plugin_root: Path, project_root: Path) -> None:
    """Copy hook files from plugin's hooks/ directory to project's .claude/ directory.

    Per spec Section 19.2, rewrites hook script paths so they reference
    the correct location within the project's .claude/scripts/ directory.
    """
    hooks_src = plugin_root / "hooks"
    claude_dir = project_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    if not hooks_src.is_dir():
        return

    # Copy hooks.json with path rewriting (spec Section 19.2)
    hooks_json_src = hooks_src / "hooks.json"
    if hooks_json_src.is_file():
        with open(str(hooks_json_src), "r", encoding="utf-8") as f:
            hooks_data = json.load(f)
        # Rewrite script paths to .claude/scripts/
        hooks_obj = hooks_data.get("hooks", {}) if isinstance(hooks_data, dict) else {}
        pre_tool_use = hooks_obj.get("PreToolUse", []) if isinstance(hooks_obj, dict) else []
        for hook_group in pre_tool_use:
            if not isinstance(hook_group, dict):
                continue
            for hook_entry in hook_group.get("hooks", []):
                if not isinstance(hook_entry, dict):
                    continue
                cmd = hook_entry.get("command", "")
                if cmd.startswith("bash ") and "scripts/" in cmd:
                    script_name = cmd.rsplit("/", 1)[-1]
                    hook_entry["command"] = f"bash .claude/scripts/{script_name}"
        dst_hooks_json = claude_dir / "hooks.json"
        with open(str(dst_hooks_json), "w", encoding="utf-8") as f:
            json.dump(hooks_data, f, indent=2)
            f.write("\n")

    # Copy scripts/ subdirectory
    hooks_scripts_src = hooks_src / "scripts"
    if hooks_scripts_src.is_dir():
        dst_scripts = claude_dir / "scripts"
        if dst_scripts.exists():
            shutil.rmtree(dst_scripts)
        shutil.copytree(str(hooks_scripts_src), str(dst_scripts))


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _handle_new_project(args: argparse.Namespace, plugin_dir: Path) -> int:
    """Handle the 'new' subcommand."""
    project_name = args.project_name
    parent_dir = Path(args.parent_dir) if args.parent_dir else Path.cwd()

    # Create directory structure
    print("Creating project directory structure...")
    project_root = create_project_directory(project_name, parent_dir)
    _print_status("Directory structure", True, str(project_root))

    # Copy scripts
    print("Copying scripts to workspace...")
    copy_scripts_to_workspace(plugin_dir, project_root)
    _print_status("Scripts", True, "Copied")

    # Generate CLAUDE.md
    print("Generating CLAUDE.md...")
    generate_claude_md(project_root, project_name)
    _print_status("CLAUDE.md", True, "Generated")

    # Write initial state
    print("Writing initial pipeline state...")
    write_initial_state(project_root, project_name)
    _print_status("Pipeline state", True, "Initialized")

    # Write default config
    print("Writing default configuration...")
    write_default_config(project_root)
    _print_status("Configuration", True, "Default config written")

    # Write README_SVP.txt
    print("Writing README_SVP.txt...")
    write_readme_svp(project_root)
    _print_status("README_SVP.txt", True, "Written")

    # Copy hooks
    print("Copying hook configurations...")
    _copy_hooks(plugin_dir, project_root)
    _print_status("Hooks", True, "Copied")

    print()
    print(f"Project '{project_name}' created at {project_root}")
    print("Starting SVP session...")
    print()

    return run_session_loop(project_root, plugin_dir)


def _handle_restore(args: argparse.Namespace, plugin_dir: Path) -> int:
    """Handle the 'restore' subcommand -- create project with injected spec and blueprint."""
    project_name = args.project_name
    parent_dir = Path(args.parent_dir) if args.parent_dir else Path.cwd()

    # Validate that required files exist
    spec_path = Path(args.spec)
    blueprint_path = Path(args.blueprint)

    if not spec_path.is_file():
        print(f"Error: Spec file not found: {spec_path}")
        return 1
    if not blueprint_path.is_file():
        print(f"Error: Blueprint file not found: {blueprint_path}")
        return 1

    # Create directory structure
    print("Creating project directory structure...")
    project_root = create_project_directory(project_name, parent_dir)
    _print_status("Directory structure", True, str(project_root))

    # Copy scripts (from --scripts-source if provided, else from plugin)
    print("Copying scripts to workspace...")
    scripts_source = Path(args.scripts_source) if args.scripts_source else plugin_dir
    copy_scripts_to_workspace(scripts_source, project_root)
    _print_status("Scripts", True, "Copied")

    # Generate CLAUDE.md
    print("Generating CLAUDE.md...")
    generate_claude_md(project_root, project_name)
    _print_status("CLAUDE.md", True, "Generated")

    # Write default config
    print("Writing default configuration...")
    write_default_config(project_root)
    _print_status("Configuration", True, "Default config written")

    # Write README_SVP.txt
    print("Writing README_SVP.txt...")
    write_readme_svp(project_root)
    _print_status("README_SVP.txt", True, "Written")

    # Copy hooks
    print("Copying hook configurations...")
    _copy_hooks(plugin_dir, project_root)
    _print_status("Hooks", True, "Copied")

    # Inject spec
    print("Injecting stakeholder spec...")
    spec_dest = project_root / "specs" / "stakeholder.md"
    shutil.copy2(str(spec_path), str(spec_dest))
    _print_status("Spec", True, f"Injected from {spec_path}")

    # Inject blueprint
    print("Injecting blueprint...")
    blueprint_dest = project_root / "blueprint" / "blueprint.md"
    shutil.copy2(str(blueprint_path), str(blueprint_dest))
    _print_status("Blueprint", True, f"Injected from {blueprint_path}")

    # Optionally inject context
    if args.context:
        context_path = Path(args.context)
        if context_path.is_file():
            print("Injecting project context...")
            context_dest = project_root / ".svp" / "project_context.md"
            shutil.copy2(str(context_path), str(context_dest))
            _print_status("Context", True, f"Injected from {context_path}")

    # Write pipeline state at pre_stage_3
    print("Writing pipeline state (pre_stage_3)...")
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "stage": "pre_stage_3",
        "sub_stage": "hook_activation",
        "current_unit": None,
        "total_units": None,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": project_name,
        "last_action": None,
        "debug_session": None,
        "debug_history": [],
        "created_at": now,
        "updated_at": now,
    }
    state_path = project_root / STATE_FILE
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    _print_status("Pipeline state", True, "Set to pre_stage_3")

    print()
    print(f"Project '{project_name}' restored at {project_root}")
    print("Starting SVP session...")
    print()

    return run_session_loop(project_root, plugin_dir)


def _handle_resume(plugin_dir: Path) -> int:
    """Handle the default 'resume' subcommand."""
    cwd = Path.cwd()
    if not detect_existing_project(cwd):
        print("No SVP project found in the current directory.")
        print("To create a new project, run: svp new <project_name>")
        print("To resume, cd into the project directory first.")
        return 1

    return resume_project(cwd, plugin_dir)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the SVP launcher."""
    args = parse_args(argv)

    _print_header("SVP Launcher")

    # Run prerequisites
    print("\nChecking prerequisites...\n")
    results = run_all_prerequisites()
    for name, passed, message in results:
        _print_status(name, passed, message)

    # Check if any failed
    all_passed = all(passed for _, passed, _ in results)
    if not all_passed:
        print("\nSome prerequisites failed. Please fix the issues above and try again.")
        return 1

    print("\nAll prerequisites passed.\n")

    # Find plugin root
    plugin_dir = _find_plugin_root()
    if plugin_dir is None:
        print("Error: Could not find SVP plugin root directory.")
        return 1

    # Dispatch to command handler
    command = args.command
    if command == "new":
        return _handle_new_project(args, plugin_dir)
    elif command == "restore":
        return _handle_restore(args, plugin_dir)
    elif command == "resume":
        return _handle_resume(plugin_dir)
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
