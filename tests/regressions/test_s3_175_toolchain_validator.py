"""S3-175 — pure-Python toolchain manifest validator.

Tests:
- The 3 existing manifests pass validation.
- Malformed fixtures are rejected for each enforced check.
- CLI smoke: subprocess returns 0 on the clean manifest set.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest


def _project_root() -> Path:
    """Walk up from this test file to find the project/repo root.

    Project root is detected by presence of either:
      - workspace layout: scripts/toolchain_defaults/
      - repo layout: svp/scripts/toolchain_defaults/
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "scripts" / "toolchain_defaults").is_dir():
            return parent
        if (parent / "svp" / "scripts" / "toolchain_defaults").is_dir():
            return parent
    raise RuntimeError("Could not locate project root containing scripts/toolchain_defaults/")


def _manifests_dir() -> Path:
    root = _project_root()
    ws = root / "scripts" / "toolchain_defaults"
    if ws.is_dir():
        return ws
    repo = root / "svp" / "scripts" / "toolchain_defaults"
    if repo.is_dir():
        return repo
    raise RuntimeError("manifests dir not found")


def _validator_script() -> Path:
    root = _project_root()
    ws = root / "scripts" / "validate_toolchain_schema.py"
    if ws.is_file():
        return ws
    repo = root / "svp" / "scripts" / "validate_toolchain_schema.py"
    if repo.is_file():
        return repo
    raise RuntimeError("validator script not found")


@pytest.fixture(scope="module")
def validate_manifest():
    """Import validate_manifest from the validator script (dual-layout)."""
    script = _validator_script()
    sys.path.insert(0, str(script.parent))
    try:
        # Force fresh import to pick up correct location
        if "validate_toolchain_schema" in sys.modules:
            del sys.modules["validate_toolchain_schema"]
        from validate_toolchain_schema import validate_manifest as fn
        return fn
    finally:
        # Leave sys.path entry in place; module-scoped fixture
        pass


def _load(name: str) -> Dict[str, Any]:
    path = _manifests_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Acceptance tests for each existing manifest
# ---------------------------------------------------------------------------

def test_validator_accepts_python_conda_pytest(validate_manifest):
    manifest = _load("python_conda_pytest.json")
    errors = validate_manifest(manifest, expected_toolchain_id="python_conda_pytest")
    assert errors == [], f"unexpected validation errors: {errors}"


def test_validator_accepts_r_conda_testthat(validate_manifest):
    manifest = _load("r_conda_testthat.json")
    errors = validate_manifest(manifest, expected_toolchain_id="r_conda_testthat")
    assert errors == [], f"unexpected validation errors: {errors}"


def test_validator_accepts_r_renv_testthat(validate_manifest):
    """r_renv_testthat lacks verify_commands — must still pass (optional field)."""
    manifest = _load("r_renv_testthat.json")
    errors = validate_manifest(manifest, expected_toolchain_id="r_renv_testthat")
    assert errors == [], f"unexpected validation errors: {errors}"


# ---------------------------------------------------------------------------
# Rejection tests for malformed fixtures
# ---------------------------------------------------------------------------

def test_validator_rejects_missing_top_level_required_key(validate_manifest):
    manifest = _load("python_conda_pytest.json")
    del manifest["environment"]
    errors = validate_manifest(manifest)
    assert any("environment" in e and "missing" in e for e in errors), errors


def test_validator_rejects_verify_commands_without_run_prefix(validate_manifest):
    manifest = _load("python_conda_pytest.json")
    manifest = copy.deepcopy(manifest)
    manifest["environment"]["verify_commands"] = [
        "python --version",  # missing {run_prefix}
        "{run_prefix} pytest --version",
    ]
    errors = validate_manifest(manifest)
    assert any("{run_prefix}" in e for e in errors), errors


def test_validator_rejects_templated_helpers_outside_canonical_dir(validate_manifest):
    manifest = _load("python_conda_pytest.json")
    manifest = copy.deepcopy(manifest)
    manifest["templated_helpers"] = [
        {"src": "/tmp/external/helper.py", "dest": "tests/helper.py"},
    ]
    errors = validate_manifest(manifest)
    assert any("templated_helpers" in e and "scripts/toolchain_defaults/templates/" in e
               for e in errors), errors


def test_validator_rejects_unknown_primer_subkey(validate_manifest):
    manifest = _load("python_conda_pytest.json")
    manifest = copy.deepcopy(manifest)
    manifest["language_architecture_primers"] = {
        "unexpected_role": "scripts/primers/foo.md",
    }
    errors = validate_manifest(manifest)
    assert any("language_architecture_primers" in e and "unknown sub-key" in e
               for e in errors), errors


def test_validator_rejects_toolchain_id_mismatch_with_filename(validate_manifest):
    manifest = _load("python_conda_pytest.json")
    manifest = copy.deepcopy(manifest)
    manifest["toolchain_id"] = "wrong_id"
    errors = validate_manifest(manifest, expected_toolchain_id="python_conda_pytest")
    assert any("toolchain_id mismatch" in e for e in errors), errors


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

def test_validator_cli_returns_zero_on_clean_manifest_set():
    script = _validator_script()
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"CLI returned {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "valid" in result.stdout.lower()
