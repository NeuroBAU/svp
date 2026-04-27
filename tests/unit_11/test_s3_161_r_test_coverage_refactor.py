"""Tests for Bug S3-161: R archetype test runner + coverage API refactor.

Covers three atomic changes:
1. r_conda_testthat.json + r_renv_testthat.json testing block:
   run_command -> devtools::test() with SilentReporter
   run_coverage -> environment_coverage after load_all(export_all=TRUE)
   framework_packages -> add r-devtools / devtools
2. src/unit_11/stub.py Step 5: helper-svp.R templated content is the
   namespace-walk helper (asNamespace + load_all + globalenv).
3. helper-svp.R generation is gated to R/mixed archetypes only (Python
   does not receive helper-svp.R).
"""
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Manifest contract tests (Changes 1 + 2)
# ---------------------------------------------------------------------------


def _toolchain_defaults_dir() -> Path:
    """Locate the toolchain_defaults directory.

    Supports both the workspace layout (scripts/toolchain_defaults/) and the
    deployed repo layout (svp/scripts/toolchain_defaults/) by walking up from
    this test file and trying each candidate sub-path at every parent.
    """
    here = Path(__file__).resolve()
    candidates = (
        Path("scripts") / "toolchain_defaults",
        Path("svp") / "scripts" / "toolchain_defaults",
    )
    for parent in [here, *here.parents]:
        for sub in candidates:
            if (parent / sub).is_dir():
                return parent / sub
    raise RuntimeError(
        "Could not locate toolchain_defaults/ in either scripts/ or svp/scripts/"
    )


def _load_manifest(name: str) -> dict:
    path = _toolchain_defaults_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def r_conda_manifest() -> dict:
    return _load_manifest("r_conda_testthat.json")


@pytest.fixture
def r_renv_manifest() -> dict:
    return _load_manifest("r_renv_testthat.json")


# --- r_conda_testthat.json ---------------------------------------------------


def test_r_conda_manifest_run_command_uses_devtools_test(r_conda_manifest):
    cmd = r_conda_manifest["testing"]["run_command"]
    assert "devtools::test" in cmd, (
        f"run_command must use devtools::test(); got: {cmd}"
    )
    assert "SilentReporter" in cmd, (
        f"run_command must use testthat::SilentReporter; got: {cmd}"
    )
    # Must NOT use the superseded testthat::test_dir() call.
    assert "testthat::test_dir" not in cmd, (
        f"run_command must NOT use testthat::test_dir (S3-161); got: {cmd}"
    )


def test_r_conda_manifest_run_coverage_uses_environment_coverage(r_conda_manifest):
    cov = r_conda_manifest["testing"]["run_coverage"]
    assert "environment_coverage" in cov, (
        f"run_coverage must use covr::environment_coverage; got: {cov}"
    )
    assert "load_all" in cov, (
        f"run_coverage must call devtools::load_all; got: {cov}"
    )
    assert "export_all = TRUE" in cov, (
        f"run_coverage must set export_all = TRUE on load_all; got: {cov}"
    )
    assert "read.dcf" in cov, (
        f"run_coverage must read package name from DESCRIPTION via read.dcf; got: {cov}"
    )
    # Must NOT use the superseded covr::package_coverage() call.
    assert "package_coverage" not in cov, (
        f"run_coverage must NOT use covr::package_coverage (S3-161); got: {cov}"
    )


def test_r_conda_manifest_framework_packages_includes_devtools(r_conda_manifest):
    pkgs = r_conda_manifest["testing"]["framework_packages"]
    assert "r-devtools" in pkgs, (
        f"framework_packages must include r-devtools; got: {pkgs}"
    )
    # Existing packages are preserved.
    assert "r-testthat" in pkgs
    assert "r-covr" in pkgs


# --- r_renv_testthat.json ----------------------------------------------------


def test_r_renv_manifest_run_command_uses_devtools_test(r_renv_manifest):
    cmd = r_renv_manifest["testing"]["run_command"]
    assert "devtools::test" in cmd, (
        f"run_command must use devtools::test(); got: {cmd}"
    )
    assert "SilentReporter" in cmd, (
        f"run_command must use testthat::SilentReporter; got: {cmd}"
    )
    # Renv variant uses bare Rscript (no {run_prefix}).
    assert "{run_prefix}" not in cmd, (
        f"renv run_command must use bare Rscript (no run_prefix); got: {cmd}"
    )
    assert cmd.startswith("Rscript -e"), (
        f"renv run_command must start with bare 'Rscript -e'; got: {cmd}"
    )


def test_r_renv_manifest_run_coverage_uses_environment_coverage(r_renv_manifest):
    cov = r_renv_manifest["testing"]["run_coverage"]
    assert "environment_coverage" in cov
    assert "load_all" in cov
    assert "export_all = TRUE" in cov
    assert "read.dcf" in cov
    assert "package_coverage" not in cov


def test_r_renv_manifest_framework_packages_includes_devtools(r_renv_manifest):
    pkgs = r_renv_manifest["testing"]["framework_packages"]
    # renv uses bare R package names (not conda-prefixed r-devtools).
    assert "devtools" in pkgs, (
        f"framework_packages must include devtools (bare name for renv); got: {pkgs}"
    )
    assert "testthat" in pkgs
    assert "covr" in pkgs


# --- Both manifests are valid JSON --------------------------------------------


def test_both_r_manifests_are_valid_json():
    """Round-trip both manifests through json to confirm well-formedness."""
    tdd = _toolchain_defaults_dir()
    conda_path = tdd / "r_conda_testthat.json"
    renv_path = tdd / "r_renv_testthat.json"
    json.loads(conda_path.read_text())
    json.loads(renv_path.read_text())


# ---------------------------------------------------------------------------
# Helper-svp.R templating tests (Change 3)
# ---------------------------------------------------------------------------


def _write_minimal_blueprint(blueprint_dir: Path) -> None:
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    (blueprint_dir / "blueprint_contracts.md").write_text(
        "## Unit 1: First\n\n"
        "### Tier 2 -- Signatures\n\n"
        "```python\n"
        "import json\n"
        "def f(): ...\n"
        "```\n"
    )
    (blueprint_dir / "blueprint_prose.md").write_text("")


def _seed_state(project_root: Path) -> None:
    svp = project_root / ".svp"
    svp.mkdir(parents=True, exist_ok=True)
    (svp / "pipeline_state.json").write_text(json.dumps({"total_units": 0}))


def _r_profile() -> dict:
    return {
        "language": {"primary": "r"},
        "archetype": "r_project",
        "delivery": {
            "r": {
                "environment_recommendation": "renv",
                "dependency_format": "renv.lock",
                "source_layout": "package",
                "entry_points": False,
            }
        },
    }


def _r_registry() -> dict:
    return {
        "r": {
            "environment_manager": "renv",
            "file_extension": ".R",
            "source_dir": "R",
            "test_dir": "tests/testthat",
            "test_file_pattern": "test-*.R",
            "toolchain_file": "r_renv_testthat.json",
            "bridge_libraries": {},
            "default_delivery": {"environment_recommendation": "renv"},
        }
    }


def _r_renv_toolchain() -> dict:
    """Minimal renv-shape pipeline toolchain (no conda verify)."""
    return {
        "environment": {
            "tool": "renv",
            "create_command": "Rscript -e 'renv::init()'",
            "install_command": "Rscript -e 'renv::install(\"{package}\")'",
        },
        "language": {"version_constraint": ">=4.0"},
        "quality": {},
    }


def _python_profile() -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
    }


def _python_registry() -> dict:
    return {
        "python": {
            "environment_manager": "conda",
            "file_extension": ".py",
            "toolchain_file": "python_conda_pytest.json",
            "import_syntax": "import {module}",
        }
    }


def _python_toolchain() -> dict:
    return {
        "environment": {
            "create": "conda create -n {env_name} python={python_version} -y",
            "install": "conda run -n {env_name} pip install {packages}",
        },
        "language": {"version_constraint": ">=3.11"},
        "quality": {},
    }


def test_infrastructure_setup_helper_svp_r_contains_namespace_walk(
    tmp_path, mock_infrastructure_subprocess
):
    """Step 5 generates helper-svp.R for an R archetype with namespace-walk content."""
    from infrastructure_setup import run_infrastructure_setup

    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_r_profile(),
        toolchain=_r_renv_toolchain(),
        language_registry=_r_registry(),
        blueprint_dir=blueprint_dir,
    )

    helper = tmp_path / "tests" / "testthat" / "helper-svp.R"
    assert helper.exists(), (
        f"helper-svp.R must be generated for R archetype at {helper}"
    )
    content = helper.read_text()
    # Required namespace-walk tokens.
    assert "asNamespace" in content, (
        f"helper-svp.R must call asNamespace(pkg); got:\n{content}"
    )
    assert "ls(" in content, (
        f"helper-svp.R must walk ls(ns); got:\n{content}"
    )
    assert "globalenv" in content, (
        f"helper-svp.R must assign into globalenv(); got:\n{content}"
    )
    assert "load_all" in content, (
        f"helper-svp.R must call devtools::load_all; got:\n{content}"
    )
    assert "read.dcf" in content, (
        f"helper-svp.R must read DESCRIPTION via read.dcf; got:\n{content}"
    )
    # Old placeholder is gone.
    assert "svp_source <- function" not in content, (
        f"helper-svp.R must NOT contain the old svp_source stub; got:\n{content}"
    )


def test_infrastructure_setup_helper_svp_not_generated_for_python(
    tmp_path, mock_infrastructure_subprocess
):
    """Step 5 does NOT generate helper-svp.R for a python archetype."""
    from infrastructure_setup import run_infrastructure_setup

    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_python_profile(),
        toolchain=_python_toolchain(),
        language_registry=_python_registry(),
        blueprint_dir=blueprint_dir,
    )

    helper = tmp_path / "tests" / "testthat" / "helper-svp.R"
    assert not helper.exists(), (
        f"helper-svp.R must NOT be generated for python archetype; "
        f"unexpected file at {helper}"
    )
    # The tests/testthat directory itself also should not exist for Python.
    assert not (tmp_path / "tests" / "testthat").exists(), (
        "tests/testthat/ directory must NOT be created for python archetype"
    )


def test_infrastructure_setup_helper_svp_r_idempotent(
    tmp_path, mock_infrastructure_subprocess
):
    """Step 5 must NOT clobber a pre-existing helper-svp.R."""
    from infrastructure_setup import run_infrastructure_setup

    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)

    # Pre-create a custom helper.
    helper_dir = tmp_path / "tests" / "testthat"
    helper_dir.mkdir(parents=True, exist_ok=True)
    helper = helper_dir / "helper-svp.R"
    custom_content = "# custom user-edited helper -- must not be clobbered\n"
    helper.write_text(custom_content)

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_r_profile(),
        toolchain=_r_renv_toolchain(),
        language_registry=_r_registry(),
        blueprint_dir=blueprint_dir,
    )

    assert helper.read_text() == custom_content, (
        "Step 5 must NOT overwrite a pre-existing helper-svp.R"
    )
