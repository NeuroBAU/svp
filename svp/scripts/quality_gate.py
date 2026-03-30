"""Unit 15: Quality Gate Execution.

Dispatches quality-gate operations (format, lint, type-check, etc.) through
a language-keyed runner table.  Each runner reads gate composition from the
toolchain, resolves command templates, executes them, and classifies the
aggregate result.
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List

from language_registry import QualityResult, get_language_config
from toolchain_reader import get_gate_composition, load_toolchain, resolve_command

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_env_name(toolchain_config: Dict[str, Any]) -> str:
    """Extract env_name from toolchain config, falling back to empty string."""
    return toolchain_config.get("env_name", "")


def _get_run_prefix(toolchain_config: Dict[str, Any]) -> str:
    """Extract run_prefix template from toolchain environment section."""
    env = toolchain_config.get("environment", {})
    return env.get("run_prefix", "")


def _tool_is_none(toolchain_config: Dict[str, Any], operation: str) -> bool:
    """Check if the tool for a given operation is configured as 'none'.

    operation is like "quality.formatter.check" -- we strip the "quality."
    prefix and check the tool key of the first segment.
    """
    quality = toolchain_config.get("quality", {})
    # Strip "quality." prefix
    op = operation
    if op.startswith("quality."):
        op = op[len("quality.") :]
    # Get tool category (e.g., "formatter", "linter", "type_checker")
    parts = op.split(".", 1)
    tool_key = parts[0]
    tool_config = quality.get(tool_key, {})
    if isinstance(tool_config, dict):
        return tool_config.get("tool", "") == "none"
    return False


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
        if _tool_is_none(toolchain_config, operation_name):
            continue

        # Resolve command using positional args
        cmd = resolve_command(command_template, env_name, run_prefix, str(target_path))

        # Execute
        result = _run_command(cmd)
        output = result.stdout + result.stderr
        all_outputs.append(f"[{operation_name}]\n{output}")

        if result.returncode != 0:
            # Non-zero return code means issues found
            residuals.append(f"{operation_name}: {output.strip()}")

    report = "\n".join(all_outputs)

    # Classify result
    if had_error:
        status = "QUALITY_ERROR"
    elif not residuals:
        status = "QUALITY_CLEAN"
    elif auto_fixed and allow_auto_fix:
        status = "QUALITY_AUTO_FIXED"
    else:
        status = "QUALITY_RESIDUAL"

    return QualityResult(
        status=status,
        auto_fixed=auto_fixed,
        residuals=residuals,
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
    run_prefix = _get_run_prefix(toolchain_config)

    try:
        operations = get_gate_composition(toolchain_config, gate_id)
    except KeyError:
        # No gate composition for Stan -- return clean
        return QualityResult(
            status="QUALITY_CLEAN",
            auto_fixed=False,
            residuals=[],
            report="No gate composition found for Stan.",
        )

    all_outputs: List[str] = []
    residuals: List[str] = []

    for op in operations:
        operation_name = op.get("operation", "")
        command_template = op.get("command", "")

        if _tool_is_none(toolchain_config, operation_name):
            continue

        cmd = resolve_command(command_template, env_name, run_prefix, str(target_path))

        result = _run_command(cmd)
        output = result.stdout + result.stderr
        all_outputs.append(f"[{operation_name}]\n{output}")

        if result.returncode != 0:
            residuals.append(f"{operation_name}: {output.strip()}")

    report = "\n".join(all_outputs)

    if residuals:
        status = "QUALITY_RESIDUAL"
    else:
        status = "QUALITY_CLEAN"

    return QualityResult(
        status=status,
        auto_fixed=False,
        residuals=residuals,
        report=report,
    )


def _run_plugin_markdown(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Markdown format check with auto-fix support."""
    env_name = _get_env_name(toolchain_config)

    try:
        operations = get_gate_composition(toolchain_config, gate_id)
    except KeyError:
        return QualityResult(
            status="QUALITY_CLEAN",
            auto_fixed=False,
            residuals=[],
            report="No gate composition found for markdown.",
        )

    run_prefix = _get_run_prefix(toolchain_config)
    all_outputs: List[str] = []
    residuals: List[str] = []
    auto_fixed = False

    for op in operations:
        operation_name = op.get("operation", "")
        command_template = op.get("command", "")

        if _tool_is_none(toolchain_config, operation_name):
            continue

        cmd = resolve_command(command_template, env_name, run_prefix, str(target_path))

        result = _run_command(cmd)
        output = result.stdout + result.stderr
        all_outputs.append(f"[{operation_name}]\n{output}")

        if result.returncode != 0:
            residuals.append(f"{operation_name}: {output.strip()}")

    report = "\n".join(all_outputs)

    if not residuals:
        status = "QUALITY_CLEAN"
    elif auto_fixed:
        status = "QUALITY_AUTO_FIXED"
    else:
        status = "QUALITY_RESIDUAL"

    return QualityResult(
        status=status,
        auto_fixed=auto_fixed,
        residuals=residuals,
        report=report,
    )


def _run_plugin_bash(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """Bash syntax validation via bash -n. Pass/fail only, auto_fixed always False."""
    env_name = _get_env_name(toolchain_config)

    try:
        operations = get_gate_composition(toolchain_config, gate_id)
    except KeyError:
        # Fallback: run bash -n directly
        cmd = f"bash -n {target_path}"
        result = _run_command(cmd)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            return QualityResult(
                status="QUALITY_RESIDUAL",
                auto_fixed=False,
                residuals=[output.strip()],
                report=output,
            )
        return QualityResult(
            status="QUALITY_CLEAN",
            auto_fixed=False,
            residuals=[],
            report=output,
        )

    run_prefix = _get_run_prefix(toolchain_config)
    all_outputs: List[str] = []
    residuals: List[str] = []

    for op in operations:
        operation_name = op.get("operation", "")
        command_template = op.get("command", "")

        if _tool_is_none(toolchain_config, operation_name):
            continue

        cmd = resolve_command(command_template, env_name, run_prefix, str(target_path))

        result = _run_command(cmd)
        output = result.stdout + result.stderr
        all_outputs.append(f"[{operation_name}]\n{output}")

        if result.returncode != 0:
            residuals.append(f"{operation_name}: {output.strip()}")

    report = "\n".join(all_outputs)

    if residuals:
        status = "QUALITY_RESIDUAL"
    else:
        status = "QUALITY_CLEAN"

    return QualityResult(
        status=status,
        auto_fixed=False,
        residuals=residuals,
        report=report,
    )


def _run_plugin_json(
    target_path: Path,
    gate_id: str,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> QualityResult:
    """JSON validation and formatting check with auto-fix (pretty-print normalization)."""
    env_name = _get_env_name(toolchain_config)

    try:
        operations = get_gate_composition(toolchain_config, gate_id)
    except KeyError:
        # Fallback: validate JSON directly
        try:
            content = target_path.read_text(encoding="utf-8")
            parsed = json.loads(content)
            normalized = json.dumps(parsed, indent=2) + "\n"
            if content != normalized:
                target_path.write_text(normalized, encoding="utf-8")
                return QualityResult(
                    status="QUALITY_AUTO_FIXED",
                    auto_fixed=True,
                    residuals=[],
                    report="JSON reformatted to standard pretty-print.",
                )
            return QualityResult(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="JSON is valid and properly formatted.",
            )
        except (json.JSONDecodeError, OSError) as exc:
            return QualityResult(
                status="QUALITY_RESIDUAL",
                auto_fixed=False,
                residuals=[str(exc)],
                report=f"JSON validation failed: {exc}",
            )

    run_prefix = _get_run_prefix(toolchain_config)
    all_outputs: List[str] = []
    residuals: List[str] = []
    auto_fixed = False

    for op in operations:
        operation_name = op.get("operation", "")
        command_template = op.get("command", "")

        if _tool_is_none(toolchain_config, operation_name):
            continue

        cmd = resolve_command(command_template, env_name, run_prefix, str(target_path))

        result = _run_command(cmd)
        output = result.stdout + result.stderr
        all_outputs.append(f"[{operation_name}]\n{output}")

        if result.returncode != 0:
            residuals.append(f"{operation_name}: {output.strip()}")

    report = "\n".join(all_outputs)

    if not residuals:
        status = "QUALITY_CLEAN"
    elif auto_fixed:
        status = "QUALITY_AUTO_FIXED"
    else:
        status = "QUALITY_RESIDUAL"

    return QualityResult(
        status=status,
        auto_fixed=auto_fixed,
        residuals=residuals,
        report=report,
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

    Looks up the ``quality_runner_key`` from *language_config*, finds the
    corresponding runner in ``QUALITY_RUNNERS``, and delegates execution.

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

    project_root = Path(args.project_root)
    target_path = Path(args.target)

    # Load language config
    language_config = get_language_config(args.language)

    # Load toolchain (pipeline or language-specific)
    toolchain_config = _load_toolchain_for_cli(project_root, args.language)

    # Derive or use provided env_name
    if args.env_name is not None:
        env_name = args.env_name
    else:
        from svp_config import derive_env_name

        env_name = derive_env_name(project_root)

    # Inject env_name into toolchain_config so runners can access it
    toolchain_config["env_name"] = env_name

    # Run the quality gate (positional args for mockability)
    result = run_quality_gate(
        target_path, args.gate, args.language, language_config, toolchain_config
    )

    # Print status to stdout
    print(result.status)
    if result.residuals:
        for residual in result.residuals:
            print(residual)
    if result.report:
        print(result.report)
