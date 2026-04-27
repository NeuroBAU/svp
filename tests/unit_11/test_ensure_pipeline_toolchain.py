"""Tests for ensure_pipeline_toolchain — Bug S3-135 / Pattern P34.

Verifies the Stage-0 → Stage-3 toolchain materialization helper in
src/unit_11/stub.py (infrastructure_setup):
- no-op when toolchain.json already exists
- copies python_conda_pytest.json when profile.language.primary == "python"
- copies r_conda_testthat.json when profile.language.primary == "r"
  (Bug S3-160 — was r_renv_testthat.json before R archetype became
  conda-foundational; renv manifest remains opt-in)
- no-op when profile is missing or primary language is absent/unknown
"""

import json
from pathlib import Path

import infrastructure_setup
from infrastructure_setup import ensure_pipeline_toolchain


# toolchain_defaults/ lives as a sibling of infrastructure_setup.py in every
# deployed layout (workspace: scripts/, repo: svp/scripts/), so resolve it
# from the module file rather than a project-root-relative path.
DEFAULTS_DIR = (
    Path(infrastructure_setup.__file__).resolve().parent / "toolchain_defaults"
)


def _write_profile(project_root: Path, primary_language: str | None) -> None:
    """Write a minimal project_profile.json with optional primary language."""
    profile: dict = {}
    if primary_language is not None:
        profile["language"] = {"primary": primary_language}
    (project_root / "project_profile.json").write_text(json.dumps(profile))


def _scaffold_project_with_defaults(project_root: Path) -> None:
    """Copy scripts/toolchain_defaults into the test project so load_toolchain
    can resolve language-keyed templates from project_root."""
    dst = project_root / "scripts" / "toolchain_defaults"
    dst.mkdir(parents=True, exist_ok=True)
    for f in DEFAULTS_DIR.glob("*.json"):
        (dst / f.name).write_text(f.read_text())


def test_noop_when_toolchain_json_already_exists(tmp_path):
    _scaffold_project_with_defaults(tmp_path)
    _write_profile(tmp_path, "python")
    existing = {"sentinel": "do-not-overwrite"}
    (tmp_path / "toolchain.json").write_text(json.dumps(existing))

    ensure_pipeline_toolchain(tmp_path)

    assert json.loads((tmp_path / "toolchain.json").read_text()) == existing


def test_materializes_from_python_default(tmp_path):
    _scaffold_project_with_defaults(tmp_path)
    _write_profile(tmp_path, "python")

    ensure_pipeline_toolchain(tmp_path)

    materialized = json.loads((tmp_path / "toolchain.json").read_text())
    expected = json.loads((DEFAULTS_DIR / "python_conda_pytest.json").read_text())
    assert materialized == expected


def test_materializes_from_r_default(tmp_path):
    _scaffold_project_with_defaults(tmp_path)
    _write_profile(tmp_path, "r")

    ensure_pipeline_toolchain(tmp_path)

    materialized = json.loads((tmp_path / "toolchain.json").read_text())
    # Bug S3-160: R archetype now materializes the conda manifest by default.
    expected = json.loads((DEFAULTS_DIR / "r_conda_testthat.json").read_text())
    assert materialized == expected


def test_noop_when_profile_missing(tmp_path):
    _scaffold_project_with_defaults(tmp_path)
    # no project_profile.json

    ensure_pipeline_toolchain(tmp_path)

    assert not (tmp_path / "toolchain.json").exists()


def test_noop_when_primary_language_unknown(tmp_path):
    _scaffold_project_with_defaults(tmp_path)
    _write_profile(tmp_path, "klingon")

    ensure_pipeline_toolchain(tmp_path)

    assert not (tmp_path / "toolchain.json").exists()
