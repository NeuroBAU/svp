"""Claude-host adapters for SVP."""

from svp_host_claude.command_builders import (
    gate_prepare_cmd,
    post_cmd,
    prepare_cmd,
)

from svp_host_claude.launcher_adapter import (
    check_claude_code,
    check_svp_plugin,
    check_api_credentials,
    launch_claude_code,
    detect_restart_signal,
    clear_restart_signal,
    run_session_loop,
    resume_project,
    _copy_hooks,
    _find_plugin_root,
    _is_svp_plugin_dir,
)

__all__ = [
    # command builders
    "post_cmd",
    "prepare_cmd",
    "gate_prepare_cmd",
    # launcher adapter
    "check_claude_code",
    "check_svp_plugin",
    "check_api_credentials",
    "launch_claude_code",
    "detect_restart_signal",
    "clear_restart_signal",
    "run_session_loop",
    "resume_project",
    "_copy_hooks",
    "_find_plugin_root",
    "_is_svp_plugin_dir",
]
