"""Claude host runtime adapter for SVP."""

from typing import Optional, List, Tuple
from pathlib import Path
import subprocess
import shutil
import os
import json


# Constants needed by adapter functions
RESTART_SIGNAL_FILE: str = ".svp/restart_signal"
CONFIG_FILE: str = "svp_config.json"
SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"


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
    env_root = os.environ.get("SVP_PLUGIN_ROOT")
    if env_root:
        p = Path(env_root)
        if _is_svp_plugin_dir(p):
            return p

    home = Path.home()

    candidates: List[Path] = [
        home / ".claude" / "plugins" / "svp",
    ]

    cache_base = home / ".claude" / "plugins" / "cache" / "svp" / "svp"
    if cache_base.is_dir():
        version_dirs = sorted(cache_base.iterdir())
        candidates.extend(version_dirs)

    candidates.extend(
        [
            home / ".config" / "claude" / "plugins" / "svp",
            Path("/usr/local/share/claude/plugins/svp"),
            Path("/usr/share/claude/plugins/svp"),
        ]
    )

    for candidate in candidates:
        if candidate.is_dir() and _is_svp_plugin_dir(candidate):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Claude runtime checks
# ---------------------------------------------------------------------------


def check_claude_code() -> Tuple[bool, str]:
    """Check that Claude Code is installed and functional."""
    try:
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, f"Claude Code {version}")
        return (False, f"Claude Code returned exit code {result.returncode}")
    except FileNotFoundError:
        return (
            False,
            "Claude Code executable not found. Install from https://claude.ai/code",
        )
    except subprocess.TimeoutExpired:
        return (False, "Claude Code version check timed out")
    except Exception as e:
        return (False, f"Error checking Claude Code: {e}")


def check_svp_plugin() -> Tuple[bool, str]:
    """Check that the SVP plugin is installed."""
    plugin_root = _find_plugin_root()
    if plugin_root is None:
        return (False, "SVP plugin not found. Check your plugin installation.")
    return (True, f"SVP plugin found at {plugin_root}")


def check_api_credentials() -> Tuple[bool, str]:
    """Check that API credentials are available."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return (True, "ANTHROPIC_API_KEY environment variable is set")

    try:
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return (True, "Authenticated via Claude Code")
        return (
            False,
            "Not authenticated. Set ANTHROPIC_API_KEY or run 'claude auth login'",
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return (
            False,
            "Not authenticated. Set ANTHROPIC_API_KEY or run 'claude auth login'",
        )


# ---------------------------------------------------------------------------
# Config reading
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
# Claude session lifecycle
# ---------------------------------------------------------------------------


def launch_claude_code(project_root: Path, plugin_dir: Path) -> int:
    """Launch Claude Code subprocess with SVP_PLUGIN_ACTIVE set."""
    if not shutil.which("claude"):
        raise RuntimeError("Session launch failed: Claude Code executable not found")

    env = os.environ.copy()
    env[SVP_ENV_VAR] = "1"

    config = _load_launch_config(project_root)
    skip_permissions = config.get("skip_permissions", True)

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


def run_session_loop(
    project_root: Path,
    plugin_dir: Path,
    set_permissions_fn=None,
    print_transition_fn=None,
    detect_restart_fn=None,
    clear_restart_fn=None,
) -> int:
    """Run the session loop: launch, check restart, repeat."""
    if set_permissions_fn is None:
        from svp.scripts.svp_launcher import set_filesystem_permissions

        set_permissions_fn = set_filesystem_permissions
    if print_transition_fn is None:
        from svp.scripts.svp_launcher import _print_transition

        print_transition_fn = _print_transition
    if detect_restart_fn is None:
        detect_restart_fn = detect_restart_signal
    if clear_restart_fn is None:
        clear_restart_fn = clear_restart_signal

    exit_code = 0
    while True:
        set_permissions_fn(project_root, read_only=False)

        exit_code = launch_claude_code(project_root, plugin_dir)

        signal = detect_restart_fn(project_root)
        if signal is not None:
            clear_restart_fn(project_root)
            set_permissions_fn(project_root, read_only=True)
            print_transition_fn(
                f"Session restart: {signal}" if signal else "Session restarting..."
            )
            continue
        else:
            set_permissions_fn(project_root, read_only=True)
            print("\nSVP session ended.")
            break

    return exit_code


def resume_project(project_root: Path, plugin_dir: Path) -> int:
    """Resume an existing SVP project session."""
    state_path = project_root / "pipeline_state.json"
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
# Hook management
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

    hooks_json_src = hooks_src / "hooks.json"
    if hooks_json_src.is_file():
        with open(str(hooks_json_src), "r", encoding="utf-8") as f:
            hooks_data = json.load(f)
        hooks_obj = hooks_data.get("hooks", {}) if isinstance(hooks_data, dict) else {}
        pre_tool_use = (
            hooks_obj.get("PreToolUse", []) if isinstance(hooks_obj, dict) else []
        )
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

    hooks_scripts_src = hooks_src / "scripts"
    if hooks_scripts_src.is_dir():
        dst_scripts = claude_dir / "scripts"
        if dst_scripts.exists():
            shutil.rmtree(dst_scripts)
        shutil.copytree(str(hooks_scripts_src), str(dst_scripts))
