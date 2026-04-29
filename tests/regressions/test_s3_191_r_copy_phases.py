"""Cycle H1 (S3-191) -- verify R-archetype Stage-5 copy machinery.

`assemble_r_project` MUST copy workspace `R/`, `tests/testthat/`, `inst/`,
`.github/`, `man/`, plus top-level R-package files (DESCRIPTION, NAMESPACE,
LICENSE, README.md, NEWS.md). Workspace versions take precedence over the
hardcoded fallback. `sync_workspace_to_repo` MUST gain an R-archetype branch
that walks `tests/testthat/` for `*.R` files. Python archetype behavior
MUST be unchanged.

Mirrors the S3-146/147/148 Python pattern.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from generate_assembly_map import (
    _copy_r_project_sources,
    assemble_python_project,
    assemble_r_project,
)
from pipeline_state import PipelineState
from sync_debug_docs import sync_workspace_to_repo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_r_workspace(tmp_path):
    """Build a synthetic R-package workspace at tmp_path/myrproj.

    Layout mirrors the canonical R-package structure expected by
    assemble_r_project.
    """
    workspace = tmp_path / "myrproj"
    workspace.mkdir()
    (workspace / ".svp").mkdir()  # SVP marker dir, must be ignored on copy

    # R/
    (workspace / "R").mkdir()
    (workspace / "R" / "foo.R").write_text("foo <- function() 1\n")
    (workspace / "R" / "bar.R").write_text("bar <- function() 2\n")

    # tests/testthat/
    (workspace / "tests" / "testthat").mkdir(parents=True)
    (workspace / "tests" / "testthat" / "test-foo.R").write_text(
        "test_that('foo', { expect_equal(foo(), 1) })\n"
    )

    # inst/
    (workspace / "inst" / "data").mkdir(parents=True)
    (workspace / "inst" / "data" / "x.csv").write_text("a,b\n1,2\n")

    # .github/
    (workspace / ".github" / "workflows").mkdir(parents=True)
    (workspace / ".github" / "workflows" / "r.yml").write_text("name: R\n")

    # man/
    (workspace / "man").mkdir()
    (workspace / "man" / "foo.Rd").write_text(
        "\\name{foo}\n\\title{foo}\n"
    )

    # Top-level R-pkg files
    (workspace / "DESCRIPTION").write_text(
        "Package: myrproj\nVersion: 0.1\nTitle: My R Project\n"
    )
    (workspace / "NAMESPACE").write_text("export(foo)\nexport(bar)\n")
    (workspace / "LICENSE").write_text("MIT\n")
    (workspace / "README.md").write_text("# myrproj\nA test project.\n")
    (workspace / "NEWS.md").write_text(
        "# myrproj 0.1\n* Initial release.\n"
    )

    return workspace


@pytest.fixture
def r_profile() -> Dict[str, Any]:
    """Synthetic R profile matching the shape used in tests/unit_23."""
    return {
        "archetype": "pure_r",
        "language": {
            "primary": "r",
            "secondary": None,
            "components": [],
            "communication": None,
            "notebooks": False,
        },
        "delivery": {
            "r": {
                "roxygen2": True,
            },
        },
        "quality": {},
        "testing": {},
        "readme": {},
        "license": "GPL-3",
        "vcs": {"provider": "github"},
        "pipeline": {},
    }


@pytest.fixture
def r_assembly_config() -> Dict[str, Any]:
    return {
        "project_name": "myrproj",
        "description": "A test R project",
        "author": "Test Author",
    }


@pytest.fixture
def python_workspace_for_sync(tmp_path):
    """Build a synthetic Python workspace for sync_workspace_to_repo
    regression-guard tests.
    """
    workspace = tmp_path / "py_proj"
    workspace.mkdir()
    (workspace / ".svp").mkdir()

    # Standard Python tests layout
    (workspace / "tests").mkdir()
    (workspace / "tests" / "regressions").mkdir()
    (workspace / "tests" / "regressions" / "test_one.py").write_text(
        "def test_one(): assert True\n"
    )

    # An R file in tests/testthat that MUST NOT be picked up for python
    (workspace / "tests" / "testthat").mkdir(parents=True)
    (workspace / "tests" / "testthat" / "test-stray.R").write_text(
        "test_that('stray', {})\n"
    )
    return workspace


# ---------------------------------------------------------------------------
# assemble_r_project copy tests
# ---------------------------------------------------------------------------


def test_h1_assemble_r_project_copies_R_directory(
    synthetic_r_workspace, r_profile, r_assembly_config
):
    """Workspace R/foo.R and R/bar.R must land in repo/R/."""
    repo = assemble_r_project(
        synthetic_r_workspace, r_profile, r_assembly_config
    )
    assert (repo / "R" / "foo.R").is_file()
    assert (repo / "R" / "bar.R").is_file()
    assert (repo / "R" / "foo.R").read_text() == "foo <- function() 1\n"
    assert (repo / "R" / "bar.R").read_text() == "bar <- function() 2\n"


def test_h1_assemble_r_project_copies_testthat_directory(
    synthetic_r_workspace, r_profile, r_assembly_config
):
    """Workspace tests/testthat/test-foo.R must land in repo/tests/testthat/."""
    repo = assemble_r_project(
        synthetic_r_workspace, r_profile, r_assembly_config
    )
    target = repo / "tests" / "testthat" / "test-foo.R"
    assert target.is_file()
    assert "expect_equal(foo(), 1)" in target.read_text()


def test_h1_assemble_r_project_copies_inst_directory(
    synthetic_r_workspace, r_profile, r_assembly_config
):
    """Workspace inst/data/x.csv must land in repo/inst/data/x.csv."""
    repo = assemble_r_project(
        synthetic_r_workspace, r_profile, r_assembly_config
    )
    target = repo / "inst" / "data" / "x.csv"
    assert target.is_file()
    assert target.read_text() == "a,b\n1,2\n"


def test_h1_assemble_r_project_copies_github_directory(
    synthetic_r_workspace, r_profile, r_assembly_config
):
    """Workspace .github/workflows/r.yml must land in repo/.github/workflows/."""
    repo = assemble_r_project(
        synthetic_r_workspace, r_profile, r_assembly_config
    )
    target = repo / ".github" / "workflows" / "r.yml"
    assert target.is_file()
    assert target.read_text() == "name: R\n"


def test_h1_assemble_r_project_copies_man_directory(
    synthetic_r_workspace, r_profile, r_assembly_config
):
    """Workspace man/foo.Rd must land in repo/man/foo.Rd."""
    repo = assemble_r_project(
        synthetic_r_workspace, r_profile, r_assembly_config
    )
    target = repo / "man" / "foo.Rd"
    assert target.is_file()
    assert "\\name{foo}" in target.read_text()


def test_h1_assemble_r_project_prefers_workspace_DESCRIPTION(
    synthetic_r_workspace, r_profile, r_assembly_config
):
    """Workspace DESCRIPTION must ship as-is; hardcoded fallback must not fire."""
    repo = assemble_r_project(
        synthetic_r_workspace, r_profile, r_assembly_config
    )
    desc_text = (repo / "DESCRIPTION").read_text()
    # Workspace DESCRIPTION had Title: My R Project (not the hardcoded one)
    assert "Title: My R Project" in desc_text
    # The hardcoded version sets License: MIT + file LICENSE; workspace
    # version omits License, so its absence proves precedence.
    assert "License: MIT + file LICENSE" not in desc_text


def test_h1_assemble_r_project_falls_back_to_hardcoded_DESCRIPTION(
    tmp_path, r_profile, r_assembly_config
):
    """When workspace lacks DESCRIPTION, hardcoded fallback must produce one."""
    workspace = tmp_path / "barerproj"
    workspace.mkdir()
    (workspace / ".svp").mkdir()
    # Note: NO DESCRIPTION, NO NAMESPACE, no R/ etc.
    repo = assemble_r_project(workspace, r_profile, r_assembly_config)
    desc_path = repo / "DESCRIPTION"
    assert desc_path.is_file()
    desc_text = desc_path.read_text()
    # Hardcoded shape: License: MIT + file LICENSE plus Type: Package
    assert "License: MIT + file LICENSE" in desc_text
    assert "Type: Package" in desc_text


# ---------------------------------------------------------------------------
# sync_workspace_to_repo R-archetype branch tests
# ---------------------------------------------------------------------------


def _make_state_for_sync(repo_path: Path, primary_language: str):
    """Build a minimal PipelineState fixture whose load returns a state with
    delivered_repo_path set and primary_language as requested.
    """
    state = PipelineState(primary_language=primary_language)
    state.delivered_repo_path = str(repo_path)
    return state


def test_h1_sync_workspace_to_repo_R_archetype_copies_R_files(
    synthetic_r_workspace, tmp_path
):
    """When state.primary_language == "r", *.R files in tests/testthat/ must
    be copied to repo/tests/testthat/.
    """
    repo_dir = tmp_path / "myrproj-repo"
    repo_dir.mkdir()
    state = _make_state_for_sync(repo_dir, "r")

    with patch(
        "sync_debug_docs.load_state", return_value=state
    ):
        result = sync_workspace_to_repo(synthetic_r_workspace)

    assert isinstance(result, dict)
    target = repo_dir / "tests" / "testthat" / "test-foo.R"
    assert target.is_file(), (
        "R-archetype branch must copy *.R files from tests/testthat/"
    )
    assert "expect_equal(foo(), 1)" in target.read_text()


def test_h1_sync_workspace_to_repo_python_archetype_unchanged(
    python_workspace_for_sync, tmp_path
):
    """Python archetype: regressions/*.py copies as before; *.R files in
    tests/testthat/ MUST NOT be copied (regression guard).
    """
    repo_dir = tmp_path / "py_proj-repo"
    repo_dir.mkdir()
    state = _make_state_for_sync(repo_dir, "python")

    with patch(
        "sync_debug_docs.load_state", return_value=state
    ):
        sync_workspace_to_repo(python_workspace_for_sync)

    # Python tests still copy
    assert (repo_dir / "tests" / "regressions" / "test_one.py").is_file(), (
        "Python branch must continue to copy regressions/*.py"
    )
    # R files NOT copied for Python archetype
    stray = repo_dir / "tests" / "testthat" / "test-stray.R"
    assert not stray.exists(), (
        "Python archetype must NOT copy *.R files even if testthat/ exists"
    )


# ---------------------------------------------------------------------------
# Python archetype regression guard
# ---------------------------------------------------------------------------


def test_h1_assemble_python_project_unchanged(tmp_path):
    """Regression guard: assemble_python_project must continue to work and
    must NOT accidentally invoke _copy_r_project_sources behavior on a
    Python workspace.
    """
    workspace = tmp_path / "py_proj"
    workspace.mkdir()
    (workspace / ".svp").mkdir()
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_basic.py").write_text(
        "def test_basic(): assert True\n"
    )
    profile = {
        "archetype": "pure_python",
        "language": {
            "primary": "python",
            "secondary": None,
            "components": [],
            "communication": None,
            "notebooks": False,
        },
        "delivery": {
            "python": {
                "source_layout": "conventional",
                "entry_points": True,
            },
        },
        "quality": {},
        "testing": {},
        "readme": {},
        "license": "MIT",
        "vcs": {"provider": "github"},
        "pipeline": {},
    }
    assembly_config = {
        "project_name": "py_proj",
        "description": "A test Python project",
        "author": "Test Author",
    }

    repo = assemble_python_project(workspace, profile, assembly_config)
    # Must produce a Python repo with pyproject.toml and src/ layout
    assert (repo / "pyproject.toml").is_file()
    assert (repo / "src" / "py_proj").is_dir()
    # Must NOT produce R-archetype directories
    assert not (repo / "R").exists(), (
        "assemble_python_project must not create R/ directory"
    )
    assert not (repo / "DESCRIPTION").exists(), (
        "assemble_python_project must not create DESCRIPTION"
    )
    assert not (repo / "NAMESPACE").exists(), (
        "assemble_python_project must not create NAMESPACE"
    )
