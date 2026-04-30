"""Unit 4: Toolchain Reader.

Loads pipeline toolchain configuration (Layer 1 / Layer 2), resolves
command templates, and composes quality-gate operation lists.

This module enforces three-layer separation: it never reads delivery
configuration or profile files.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.unit_1.stub import ARTIFACT_FILENAMES
from src.unit_2.stub import LANGUAGE_REGISTRY


def load_toolchain(
    project_root: Path,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a toolchain JSON file and return its parsed contents.

    Parameters
    ----------
    project_root : Path
        Root directory of the project.
    language : str or None
        If None, loads the pipeline toolchain (toolchain.json) from
        *project_root*.  If a language string (e.g. ``"python"``),
        loads the language-specific default toolchain from
        ``scripts/toolchain_defaults/``.

    Returns
    -------
    dict
        Parsed JSON content of the toolchain file.

    Raises
    ------
    FileNotFoundError
        If the toolchain file does not exist.
    KeyError
        If *language* is not in LANGUAGE_REGISTRY.
    """
    if language is None:
        # Layer 1 pipeline toolchain
        toolchain_path = project_root / ARTIFACT_FILENAMES["toolchain"]
    else:
        # Language-specific default toolchain (Layer 2)
        if language not in LANGUAGE_REGISTRY:
            raise KeyError(f"Unknown language: {language}")
        toolchain_file = LANGUAGE_REGISTRY[language]["toolchain_file"]
        toolchain_path = (
            project_root / "scripts" / "toolchain_defaults" / toolchain_file
        )

    with open(toolchain_path, "r") as f:
        return json.load(f)


def resolve_command(
    template: str,
    env_name: str,
    run_prefix: str,
    target: str = "",
    python_version: str = "",
    flags: str = "",
) -> str:
    """Substitute placeholders in a command template string.

    Performs single-pass substitution in the order:
    ``{run_prefix}`` -> ``{env_name}`` -> ``{python_version}`` ->
    ``{flags}`` -> ``{target}``.

    After substitution, collapses multiple spaces to a single space and
    strips leading/trailing whitespace.

    Parameters
    ----------
    template : str
        Command template with ``{placeholder}`` markers.
    env_name : str
        Environment name to substitute for ``{env_name}``.
    run_prefix : str
        Run prefix to substitute for ``{run_prefix}``.
    target : str
        Target path to substitute for ``{target}``.
    python_version : str
        Python version string to substitute for ``{python_version}``.
    flags : str
        Additional flags to substitute for ``{flags}``.

    Returns
    -------
    str
        Fully resolved command string with no unresolved placeholders,
        no double spaces, and no leading/trailing whitespace.
    """
    # Single-pass substitution in specified order
    result = template.replace("{run_prefix}", run_prefix)
    result = result.replace("{env_name}", env_name)
    result = result.replace("{python_version}", python_version)
    result = result.replace("{flags}", flags)
    result = result.replace("{target}", target)

    # Collapse multiple spaces to single
    result = re.sub(r" {2,}", " ", result)

    # Strip leading/trailing whitespace
    return result.strip()


def get_gate_composition(
    toolchain: Dict[str, Any],
    gate_id: str,
) -> List[Dict[str, str]]:
    """Return the ordered list of operation dicts for a quality gate.

    Parameters
    ----------
    toolchain : dict
        Parsed toolchain configuration (as returned by ``load_toolchain``).
    gate_id : str
        Gate identifier (e.g. ``"gate_a"``, ``"gate_b"``, ``"gate_c"``).

    Returns
    -------
    list of dict
        Each dict has at minimum ``"operation"`` and ``"command"`` keys.
        Operation names are qualified with a ``"quality."`` prefix.

    Raises
    ------
    KeyError
        If *gate_id* is not present in ``toolchain["quality"]``.
    """
    quality = toolchain["quality"]

    if gate_id not in quality:
        raise KeyError(gate_id)

    gate_ops = quality[gate_id]
    result: List[Dict[str, str]] = []

    for op_ref in gate_ops:
        if isinstance(op_ref, str):
            # String reference like "formatter.check" -- resolve to dict
            parts = op_ref.split(".", 1)
            tool_key = parts[0]
            action_key = parts[1]

            # Look up the command template from toolchain quality config
            command = quality[tool_key][action_key]

            # Qualify operation name with "quality." prefix
            operation = f"quality.{op_ref}"

            result.append(
                {
                    "operation": operation,
                    "command": command,
                }
            )
        elif isinstance(op_ref, dict):
            # Already a dict -- qualify operation name with "quality." prefix
            entry = dict(op_ref)
            op_name = entry.get("operation", "")
            if not op_name.startswith("quality."):
                entry["operation"] = f"quality.{op_name}"
            result.append(entry)

    return result


def verify_toolchain_ready(
    project_root: Path,
    env_name: str,
    *,
    runner: Optional[Callable[[str], int]] = None,
) -> Tuple[bool, List[str]]:
    """Verify the toolchain env created by infrastructure_setup is functional.

    Loads the pipeline toolchain via load_toolchain(project_root) and reads
    the environment.verify_commands list. Each entry is a templated string;
    placeholders {run_prefix} and {env_name} are substituted (run_prefix
    itself is read from environment.run_prefix and substituted with
    {env_name} first). Each resolved command is executed via the supplied
    runner (or via subprocess.run with shell=False in production).

    A non-zero return code from any command yields (False, [messages]); on
    success returns (True, []).

    Bug S3-160: pairs env creation with mechanical verification so a
    silent conda-forge / network / pin-conflict failure surfaces here
    instead of much later at red-run.

    Parameters
    ----------
    project_root : Path
        Project root that contains a materialized toolchain.json.
    env_name : str
        Name of the conda env to substitute for {env_name}.
    runner : callable, optional
        For testability: a function taking a command string and returning
        the integer return code. In production, callers pass None and
        subprocess.run is used (shell=False; the command is split on
        whitespace).

    Returns
    -------
    (bool, list of str)
        (True, []) on success.
        (False, [error messages]) when one or more commands return
        non-zero. Each error message contains the failing command.
    """
    toolchain = load_toolchain(project_root)
    env_section = toolchain.get("environment", {}) or {}
    verify_commands = env_section.get("verify_commands", []) or []
    run_prefix_template = env_section.get("run_prefix", "") or ""
    run_prefix = run_prefix_template.replace("{env_name}", env_name)

    def _default_runner(cmd: str) -> int:
        # Bug S3-200 / cycle I-3: force UTF-8 decoding for cross-platform
        # robustness (mirrors H6 / S3-196 fix in Unit 14 run_tests_main).
        # PYTHONIOENCODING + PYTHONUTF8 env override coerces the child to emit
        # UTF-8; text=True is dropped so stdout/stderr come back as bytes
        # (output is unused at this site so no decode is needed). Defends
        # against Windows cp1252 default decoding crashes when verify_commands
        # children emit non-cp1252 bytes (em-dashes, smart quotes, glyphs).
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        proc = subprocess.run(
            cmd.split(),
            check=False,
            capture_output=True,  # NOTE: text=True dropped (decode bytes manually if consumed)
            env=env,
        )
        return proc.returncode

    invoke = runner if runner is not None else _default_runner

    errors: List[str] = []
    for template in verify_commands:
        cmd = template.replace("{run_prefix}", run_prefix).replace(
            "{env_name}", env_name
        )
        # Collapse double-spaces left by empty substitutions.
        cmd = re.sub(r" {2,}", " ", cmd).strip()
        try:
            rc = invoke(cmd)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"verify command raised exception: {cmd}: {exc}")
            continue
        if rc != 0:
            errors.append(
                f"verify command failed (returncode={rc}): {cmd}"
            )

    return (len(errors) == 0, errors)
