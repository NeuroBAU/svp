"""Toolchain manifest schema validator (Bug S3-175).

Pure-Python validator for SVP toolchain manifests. Enforces the schema
documented at references/toolchain_manifest_schema.md.

Usage as library:
    from validate_toolchain_schema import validate_manifest
    errors = validate_manifest(manifest_dict)
    if errors:
        for err in errors:
            print(err)

Usage as CLI:
    python scripts/validate_toolchain_schema.py
        Validates all scripts/toolchain_defaults/*.json files.
        Exit 0 if all valid; exit 1 if any failures.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


_REQUIRED_TOP_LEVEL_KEYS = (
    "toolchain_id",
    "environment",
    "quality",
    "testing",
    "language",
    "file_structure",
)

_REQUIRED_ENV_KEYS = (
    "tool",
    "run_prefix",
    "create_command",
    "install_command",
    "cleanup_command",
)

_REQUIRED_LANGUAGE_KEYS = (
    "name",
    "extension",
    "version_constraint",
)

_REQUIRED_TESTING_KEYS = (
    "tool",
    "run_command",
    "framework_packages",
)

_REQUIRED_FILE_STRUCTURE_KEYS = (
    "source_dir_pattern",
    "test_dir_pattern",
    "source_extension",
    "test_extension",
)

_ALLOWED_PRIMER_SUBKEYS = frozenset({
    "blueprint_author",
    "implementation_agent",
    "test_agent",
    "coverage_review",
    "orchestrator_break_glass",
})

_TEMPLATES_PREFIX = "scripts/toolchain_defaults/templates/"


def validate_manifest(
    manifest: Dict[str, Any],
    *,
    expected_toolchain_id: str | None = None,
) -> List[str]:
    """Validate a toolchain manifest dict against the schema.

    Args:
        manifest: parsed manifest JSON.
        expected_toolchain_id: optional filename-stem match check.

    Returns:
        List of human-readable error messages. Empty list == valid.
    """
    errors: List[str] = []

    # Check 1: top-level required keys
    for key in _REQUIRED_TOP_LEVEL_KEYS:
        if key not in manifest:
            errors.append(f"missing required top-level key: {key}")

    # Check 2: environment required nested
    env = manifest.get("environment")
    if isinstance(env, dict):
        for key in _REQUIRED_ENV_KEYS:
            if key not in env:
                errors.append(f"missing required key: environment.{key}")
        # Check 3: verify_commands convention (if present)
        verify_commands = env.get("verify_commands")
        if verify_commands is not None:
            if not isinstance(verify_commands, list) or len(verify_commands) == 0:
                errors.append(
                    "environment.verify_commands must be a non-empty list when present"
                )
            else:
                for i, cmd in enumerate(verify_commands):
                    if not isinstance(cmd, str) or "{run_prefix}" not in cmd:
                        errors.append(
                            f"environment.verify_commands[{i}] must use "
                            f"{{run_prefix}} template substitution"
                        )

    # Check 4: language required nested
    language = manifest.get("language")
    if isinstance(language, dict):
        for key in _REQUIRED_LANGUAGE_KEYS:
            if key not in language:
                errors.append(f"missing required key: language.{key}")

    # Check 5: testing required nested
    testing = manifest.get("testing")
    if isinstance(testing, dict):
        for key in _REQUIRED_TESTING_KEYS:
            if key not in testing:
                errors.append(f"missing required key: testing.{key}")
        framework_packages = testing.get("framework_packages")
        if framework_packages is not None and not isinstance(framework_packages, list):
            errors.append("testing.framework_packages must be a list")

    # Check 6: quality.packages is list
    quality = manifest.get("quality")
    if isinstance(quality, dict):
        packages = quality.get("packages")
        if packages is not None and not isinstance(packages, list):
            errors.append("quality.packages must be a list")

    # Check 7: file_structure required keys
    fs = manifest.get("file_structure")
    if isinstance(fs, dict):
        for key in _REQUIRED_FILE_STRUCTURE_KEYS:
            if key not in fs:
                errors.append(f"missing required key: file_structure.{key}")

    # Check 8: templated_helpers convention (if present)
    helpers = manifest.get("templated_helpers")
    if helpers is not None:
        if not isinstance(helpers, list):
            errors.append("templated_helpers must be a list when present")
        else:
            for i, entry in enumerate(helpers):
                if not isinstance(entry, dict):
                    errors.append(
                        f"templated_helpers[{i}] must be an object with src + dest"
                    )
                    continue
                if "src" not in entry or "dest" not in entry:
                    errors.append(
                        f"templated_helpers[{i}] missing src or dest"
                    )
                    continue
                src = entry["src"]
                if not isinstance(src, str) or not src.startswith(_TEMPLATES_PREFIX):
                    errors.append(
                        f"templated_helpers[{i}].src must live under "
                        f"{_TEMPLATES_PREFIX} (got: {src!r})"
                    )

    # Check 9: language_architecture_primers (if present)
    primers = manifest.get("language_architecture_primers")
    if primers is not None:
        if not isinstance(primers, dict):
            errors.append(
                "language_architecture_primers must be an object when present"
            )
        else:
            for key in primers:
                if key not in _ALLOWED_PRIMER_SUBKEYS:
                    errors.append(
                        f"language_architecture_primers has unknown sub-key: "
                        f"{key} (allowed: {sorted(_ALLOWED_PRIMER_SUBKEYS)})"
                    )

    # Check 10: toolchain_id matches filename stem (if expected provided)
    if expected_toolchain_id is not None:
        actual = manifest.get("toolchain_id")
        if actual != expected_toolchain_id:
            errors.append(
                f"toolchain_id mismatch: filename stem expects "
                f"{expected_toolchain_id!r}, manifest has {actual!r}"
            )

    return errors


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate SVP toolchain manifests against the schema."
    )
    parser.add_argument(
        "--manifests-dir",
        type=Path,
        default=None,
        help="Directory containing manifest JSON files. "
             "Default: scripts/toolchain_defaults relative to script location.",
    )
    args = parser.parse_args(argv)

    manifests_dir = args.manifests_dir
    if manifests_dir is None:
        # Default: locate scripts/toolchain_defaults/ relative to this file
        # In workspace: <ws>/scripts/toolchain_defaults/
        # In repo svp/: <repo>/svp/scripts/toolchain_defaults/
        here = Path(__file__).resolve()
        candidate = here.parent / "toolchain_defaults"
        if candidate.is_dir():
            manifests_dir = candidate
        else:
            print(
                f"ERROR: cannot locate manifests directory at {candidate}",
                file=sys.stderr,
            )
            return 1

    if not manifests_dir.is_dir():
        print(f"ERROR: not a directory: {manifests_dir}", file=sys.stderr)
        return 1

    json_files = sorted(manifests_dir.glob("*.json"))
    if not json_files:
        print(f"ERROR: no .json files in {manifests_dir}", file=sys.stderr)
        return 1

    total_errors = 0
    for path in json_files:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"{path.name}: JSON parse error: {exc}", file=sys.stderr)
            total_errors += 1
            continue
        errors = validate_manifest(manifest, expected_toolchain_id=path.stem)
        if errors:
            total_errors += len(errors)
            print(f"{path.name}: {len(errors)} error(s):")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"{path.name}: OK")

    if total_errors:
        print(f"\nTotal: {total_errors} error(s) across {len(json_files)} files",
              file=sys.stderr)
        return 1
    print(f"\nAll {len(json_files)} manifests valid.")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
