"""Unit 15: Quality Gate Execution.

Dispatches quality-gate operations (format, lint, type-check, etc.) through
a language-keyed runner table.  Each runner reads gate composition from the
toolchain, resolves command templates, executes them, and classifies the
aggregate result.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from src.unit_2.stub import QualityResult, get_language_config
from src.unit_4.stub import get_gate_composition, load_toolchain, resolve_command

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tool_is_none(command_template: str) -> bool:
    """Check if a tool command is 'none', meaning it should be skipped."""
    return command_template.strip().lower() == "none"


def _get_env_name(toolchain_config: Dict[str, Any]) -> str:
    """Extract env_name from toolchain config, falling back to empty string."""
    return toolchain_config.get("env_name", "")


def _get_run_prefix(toolchain_config: Dict[str, Any]) -> str:
    """Extract run_prefix template from toolchain environment section."""
    env = toolchain_config.get("environment", {})
    return env.get("run_prefix", "")


def _run_command(cmd: str) -> subprocess.CompletedProcess:
    """Run a shell command and return the CompletedProcess."""
    return subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )


def _execute_gate_operations(
    target_path: Path,
    gate_id: str,
    toolchain_config: Dict[str, Any],
    env_name: str,
    allow_auto_fix: bool = True,
    pass_fail_only: bool = False,
) -> QualityResult:
    """Core logic shared by most runners: get composition, resolve, execute.

    Parameters
    ----------
    target_path : Path
        File or directory to check.
    gate_id : str
        Gate identifier (e.g. "gate_a").
    toolchain_config : dict
        Parsed toolchain configuration.
    env_name : str
        Environment name for command resolution.
    allow_auto_fix : bool
        Whether auto-fix is possible for this language type.
    pass_fail_only : bool
        If True, only QUALITY_CLEAN or QUALITY_ERROR are valid statuses.

    Returns
    -------
    QualityResult
    """
    run_prefix = _get_run_prefix(toolchain_config)
    operations = get_gate_composition(toolchain_config, gate_id)

    all_outputs: List[str] = []
    residuals: List[str] = []
    auto_fixed = False
    had_error = False

    for op in operations:
        operation_name = op.get("operation", "")
        command_template = op.get("command", "")

        # Skip operations whose tool is "none"
        if _tool_is_none(command_template):
            continue

        # Bug S3-140: look up per-tool unit_flags from toolchain quality config
        # and pass as flags= to resolve_command so the {flags} placeholder in
        # the command template is populated. operation_name format is
        # "quality.<tool>.<op>" (e.g., "quality.type_checker.check"); parts[1]
        # selects the subconfig that declares unit_flags. project_flags at
        # higher scopes is out of scope for this unit-level fix.
        flags = ""
        parts = operation_name.split(".")
        if len(parts) >= 2 and parts[0] == "quality":
            tool_cfg = toolchain_config.get("quality", {}).get(parts[1], {})
            if isinstance(tool_cfg, dict):
                flags = tool_cfg.get("unit_flags", "") or ""

        # Resolve command
        cmd = resolve_command(
            command_template, env_name, run_prefix, str(target_path), flags=flags,
        )

        # Capture file content before execution for auto-fix detection
        content_before = None
        if target_path.is_file() and allow_auto_fix:
            try:
                content_before = target_path.read_bytes()
            except OSError:
                pass

        # Execute
        try:
            result = _run_command(cmd)
            output = result.stdout + result.stderr
            all_outputs.append(f"[{operation_name}]\n{output}")

            # Detect auto-fix: file was modified by the tool
            if content_before is not None and target_path.is_file():
                try:
                    content_after = target_path.read_bytes()
                    if content_after != content_before:
                        auto_fixed = True
                except OSError:
                    pass

            if result.returncode != 0:
                if pass_fail_only:
                    had_error = True
                else:
                    residuals.append(f"{operation_name}: {output.strip()}")
        except Exception as exc:
            had_error = True
            all_outputs.append(f"[{operation_name}]\nError: {exc}")

    report = "\n".join(all_outputs)

    # Classify result
    if had_error:
        status = "QUALITY_ERROR"
    elif auto_fixed and allow_auto_fix:
        status = "QUALITY_AUTO_FIXED"
    elif not residuals:
        status = "QUALITY_CLEAN"
    else:
        status = "QUALITY_RESIDUAL"

    return QualityResult(
        status=status,
        auto_fixed=auto_fixed if not pass_fail_only else False,
        residuals=residuals if not pass_fail_only else [],
        report=report,
    )


# ---------------------------------------------------------------------------
# Language-specific runners
# ---------------------------------------------------------------------------


def _run_python(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Python quality runner: ruff format, ruff check, mypy per gate composition."""
    env_name = _get_env_name(toolchain_config)
    return _execute_gate_operations(
        target_path, gate_id, toolchain_config, env_name, allow_auto_fix=True
    )


def _run_r(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """R quality runner: lintr, styler per gate composition."""
    env_name = _get_env_name(toolchain_config)
    return _execute_gate_operations(
        target_path, gate_id, toolchain_config, env_name, allow_auto_fix=True
    )


def _run_stan_syntax_check(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Stan syntax check: compiler validation. Pass/fail only, auto_fixed always False."""
    env_name = _get_env_name(toolchain_config)
    return _execute_gate_operations(
        target_path,
        gate_id,
        toolchain_config,
        env_name,
        allow_auto_fix=False,
        pass_fail_only=True,
    )


def _run_plugin_markdown(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Markdown format check with auto-fix support."""
    env_name = _get_env_name(toolchain_config)
    return _execute_gate_operations(
        target_path, gate_id, toolchain_config, env_name, allow_auto_fix=True
    )


def _run_plugin_bash(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Bash syntax validation via bash -n. Pass/fail only, auto_fixed always False."""
    env_name = _get_env_name(toolchain_config)
    return _execute_gate_operations(
        target_path,
        gate_id,
        toolchain_config,
        env_name,
        allow_auto_fix=False,
        pass_fail_only=True,
    )


def _run_plugin_json(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """JSON validation and formatting check with auto-fix support (pretty-print normalization)."""
    env_name = _get_env_name(toolchain_config)
    return _execute_gate_operations(
        target_path, gate_id, toolchain_config, env_name, allow_auto_fix=True
    )


# ---------------------------------------------------------------------------
# QUALITY_RUNNERS dispatch table
# ---------------------------------------------------------------------------

QUALITY_RUNNERS: Dict[
    str, Callable[[Path, str, Dict[str, Any], Dict[str, Any]], QualityResult]
] = {
    "python": _run_python,
    "r": _run_r,
    "stan_syntax_check": _run_stan_syntax_check,
    "plugin_markdown": _run_plugin_markdown,
    "plugin_bash": _run_plugin_bash,
    "plugin_json": _run_plugin_json,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_quality_gate(
    target_path: Path,
    gate_id: str,
    language: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Dispatch quality-gate execution through QUALITY_RUNNERS.

    Looks up the ``quality_runner_key`` from *language_config*, falling back
    to the *language* parameter itself.  Finds the corresponding runner in
    ``QUALITY_RUNNERS`` and delegates execution.

    Parameters
    ----------
    target_path : Path
        File or directory to check.
    gate_id : str
        Gate identifier (e.g. ``"gate_a"``).
    language : str
        Language identifier (e.g. ``"python"``).
    language_config : dict
        Language registry entry (from ``get_language_config``).
    toolchain_config : dict
        Parsed toolchain configuration.

    Returns
    -------
    QualityResult

    Raises
    ------
    KeyError
        If the quality_runner_key is not found in QUALITY_RUNNERS.
    """
    runner_key = language_config.get("quality_runner_key", language)

    if runner_key not in QUALITY_RUNNERS:
        raise KeyError(f"No quality runner registered for key: {runner_key}")

    runner = QUALITY_RUNNERS[runner_key]
    return runner(target_path, gate_id, language_config, toolchain_config)


def _load_toolchain_for_cli(project_root: Path, language: str) -> Dict[str, Any]:
    """Load toolchain config, trying pipeline toolchain first, then language default.

    Falls back to an empty dict if no toolchain file is found.
    """
    # Try pipeline toolchain first
    try:
        return load_toolchain(project_root)
    except FileNotFoundError:
        pass

    # Try language-specific default toolchain
    try:
        return load_toolchain(project_root, language=language)
    except (FileNotFoundError, KeyError):
        pass

    # Fallback: empty toolchain config
    return {}


def run_quality_gate_main(argv: list = None) -> None:
    """CLI entry point for quality gate execution.

    Arguments
    ---------
    --target : path
        File or directory to check.
    --gate : str
        Gate identifier (``"gate_a"``, ``"gate_b"``, ``"gate_c"``).
    --unit : int
        Unit number (informational).
    --language : str
        Language identifier.
    --project-root : path
        Project root directory.
    --env-name : str, optional
        Environment name override.
    """
    parser = argparse.ArgumentParser(description="SVP Quality Gate Execution")
    parser.add_argument("--target", type=str, required=True, help="Target path")
    parser.add_argument(
        "--gate",
        type=str,
        required=True,
        choices=["gate_a", "gate_b", "gate_c"],
        help="Gate identifier",
    )
    parser.add_argument("--unit", type=int, default=None, help="Unit number")
    parser.add_argument("--language", type=str, required=True, help="Language")
    parser.add_argument("--project-root", type=str, required=True, help="Project root")
    parser.add_argument(
        "--env-name", type=str, default=None, help="Environment name override"
    )

    args = parser.parse_args(argv)

    # Bug S3-118: resolve at CLI boundary so downstream helpers see an
    # absolute path (Path('.').name is '', which breaks derive_env_name).
    project_root = Path(args.project_root).resolve()
    target_path = Path(args.target)

    # Load language config
    lang_config = get_language_config(args.language)

    # Load toolchain (pipeline or language-specific)
    toolchain_config = _load_toolchain_for_cli(project_root, args.language)

    # Derive or use provided env_name
    if args.env_name is not None:
        env_name = args.env_name
    else:
        from src.unit_1.stub import derive_env_name

        env_name = derive_env_name(project_root)

    # Inject env_name into toolchain_config so runners can access it
    toolchain_config["env_name"] = env_name

    # Run the quality gate
    result = run_quality_gate(
        target_path, args.gate, args.language, lang_config, toolchain_config
    )

    # Print status to stdout
    print(result.status)
    if result.residuals:
        for residual in result.residuals:
            print(residual)
    if result.report:
        print(result.report)

    # Bug S3-138: exit nonzero on failure statuses so the orchestrator
    # constructs COMMAND_FAILED per spec §3.7 exit-code rule. QUALITY_CLEAN
    # and QUALITY_AUTO_FIXED are both "gate passed" — the auto-fixed run
    # already observed a clean post-fix state, so advancing is defensible
    # (see §24.63 / S3-36 and §24.151).
    if result.status in ("QUALITY_RESIDUAL", "QUALITY_ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    run_quality_gate_main()
