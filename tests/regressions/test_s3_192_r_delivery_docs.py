"""Cycle H2 (S3-192) -- verify generate_r_delivery_docs creates default
R-archetype delivery docs (README, LICENSE, .gitignore, environment.yml,
CHANGELOG.md) when workspace lacks them, while preserving workspace
versions when present (precedence layer).

Layered fallback architecture:
    workspace > H2 generator > H1 hardcoded > nothing

H1 (S3-191) shipped `_copy_r_project_sources` plus the H1 hardcoded
DESCRIPTION/NAMESPACE/tests/testthat.R fallbacks. H2 fills the gap for
the other 5 R-archetype required files.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

# S3-103 honors flat-module imports (no `from src.unit_23.stub import ...`).
from generate_assembly_map import (
    _r_changelog_content,
    _r_environment_yml_content,
    _r_gitignore_content,
    _r_license_content,
    _r_readme_content,
    assemble_python_project,
    assemble_r_project,
    generate_r_delivery_docs,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _project_root_with_toolchain(tmp_path: Path) -> Path:
    """Build a synthetic project_root that ships the R toolchain manifest.

    `assemble_r_project` calls `load_toolchain(project_root, language="r")`
    which resolves to `scripts/toolchain_defaults/r_conda_testthat.json`
    under project_root. Copy the workspace's authoritative manifest into
    the synthetic project so toolchain lookups succeed.

    Searches for the manifest under either workspace layout
    (`<root>/scripts/toolchain_defaults/`) or repo layout
    (`<root>/svp/scripts/toolchain_defaults/`) by walking up from this
    test file.
    """
    here = Path(__file__).resolve()
    candidates = [
        ancestor / "scripts" / "toolchain_defaults"
        for ancestor in [here, *here.parents]
    ] + [
        ancestor / "svp" / "scripts" / "toolchain_defaults"
        for ancestor in [here, *here.parents]
    ]
    src_dir: Path | None = None
    for candidate in candidates:
        if (candidate / "r_conda_testthat.json").is_file():
            src_dir = candidate
            break
    dst = tmp_path / "scripts" / "toolchain_defaults"
    dst.mkdir(parents=True, exist_ok=True)
    if src_dir is not None:
        for fname in ("r_conda_testthat.json",):
            src_file = src_dir / fname
            if src_file.is_file():
                shutil.copy2(src_file, dst / fname)
    return tmp_path


@pytest.fixture
def minimal_r_workspace(tmp_path: Path) -> Path:
    """Build a synthetic R-package workspace at tmp_path/myrproj WITHOUT
    delivery docs (no README, no LICENSE, no .gitignore, no environment.yml,
    no CHANGELOG). H2 generator must fill these gaps.
    """
    project_root = _project_root_with_toolchain(tmp_path)
    workspace = project_root / "myrproj"
    workspace.mkdir()
    (workspace / "R").mkdir()
    (workspace / "R" / "foo.R").write_text("foo <- function() 1\n")
    (workspace / "tests" / "testthat").mkdir(parents=True)
    (workspace / "DESCRIPTION").write_text(
        "Package: myrproj\nVersion: 0.1\n"
    )
    # Replicate toolchain defaults underneath the workspace so
    # load_toolchain(project_root=workspace, language="r") resolves.
    src = project_root / "scripts" / "toolchain_defaults"
    dst = workspace / "scripts" / "toolchain_defaults"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.json"):
        shutil.copy2(f, dst / f.name)
    return workspace


@pytest.fixture
def r_profile() -> Dict[str, Any]:
    return {
        "archetype": "pure_r",
        "language": {"primary": "r"},
        "delivery": {"r": {"roxygen2": True}},
        "license": {"type": "MIT", "holder": "Acme Corp"},
        "author": "Test User",
        "description": "A test R package",
        "quality": {},
        "testing": {},
        "readme": {},
        "vcs": {"provider": "github"},
        "pipeline": {},
    }


@pytest.fixture
def r_assembly_config() -> Dict[str, Any]:
    return {"project_name": "myrproj", "description": "A test R package"}


@pytest.fixture
def r_toolchain_stub() -> Dict[str, Any]:
    """Minimal toolchain dict for unit tests of helpers (no project_root I/O)."""
    return {
        "language": {"version_constraint": ">=4.3"},
        "testing": {
            "framework_packages": ["r-testthat", "r-covr", "r-devtools"]
        },
        "quality": {"packages": ["r-lintr", "r-styler"]},
    }


# ---------------------------------------------------------------------------
# 5 generate-when-missing tests
# ---------------------------------------------------------------------------


def test_h2_readme_generated_when_workspace_lacks_it(
    minimal_r_workspace, r_profile, r_assembly_config
):
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    readme = repo / "README.md"
    assert readme.is_file(), "H2 must generate README.md when workspace lacks it"
    text = readme.read_text()
    assert "myrproj" in text
    assert "A test R package" in text
    assert "MIT" in text
    assert "Test User" in text


def test_h2_license_generated_when_workspace_lacks_it(
    minimal_r_workspace, r_profile, r_assembly_config
):
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    license_path = repo / "LICENSE"
    assert license_path.is_file(), "H2 must generate LICENSE when workspace lacks it"
    text = license_path.read_text()
    assert "MIT License" in text
    assert "Acme Corp" in text
    # Year stamp present
    assert "20" in text


def test_h2_gitignore_generated_when_workspace_lacks_it(
    minimal_r_workspace, r_profile, r_assembly_config
):
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    gi = repo / ".gitignore"
    assert gi.is_file(), "H2 must generate .gitignore when workspace lacks it"
    text = gi.read_text()
    # language_registry["r"]["gitignore_patterns"] supplies these
    assert ".Rhistory" in text
    assert ".RData" in text


def test_h2_environment_yml_generated_when_workspace_lacks_it(
    minimal_r_workspace, r_profile, r_assembly_config
):
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    env = repo / "environment.yml"
    assert env.is_file(), "H2 must generate environment.yml when workspace lacks it"
    text = env.read_text()
    assert "name:" in text
    assert "r-base=" in text
    # Framework packages from toolchain
    assert "r-testthat" in text
    # Quality packages from toolchain
    assert "r-lintr" in text


def test_h2_changelog_generated_when_workspace_lacks_it(
    minimal_r_workspace, r_profile, r_assembly_config
):
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    changelog = repo / "CHANGELOG.md"
    assert changelog.is_file(), "H2 must generate CHANGELOG.md when workspace lacks it"
    text = changelog.read_text()
    assert "Keep a Changelog" in text
    assert "[Unreleased]" in text


# ---------------------------------------------------------------------------
# 5 workspace-precedence tests
# ---------------------------------------------------------------------------


def test_h2_workspace_readme_takes_precedence(
    minimal_r_workspace, r_profile, r_assembly_config
):
    custom = "# Custom workspace README\nDo not overwrite me.\n"
    (minimal_r_workspace / "README.md").write_text(custom)
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    text = (repo / "README.md").read_text()
    assert "Custom workspace README" in text
    assert "Do not overwrite me." in text


def test_h2_workspace_license_takes_precedence(
    minimal_r_workspace, r_profile, r_assembly_config
):
    custom = "Custom workspace LICENSE content -- proprietary.\n"
    (minimal_r_workspace / "LICENSE").write_text(custom)
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    text = (repo / "LICENSE").read_text()
    assert "Custom workspace LICENSE content" in text
    assert "MIT License" not in text


def test_h2_workspace_gitignore_takes_precedence(
    minimal_r_workspace, r_profile, r_assembly_config
):
    custom = "# custom workspace gitignore\nmy_secret_dir/\n"
    (minimal_r_workspace / ".gitignore").write_text(custom)
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    text = (repo / ".gitignore").read_text()
    assert "my_secret_dir/" in text


def test_h2_workspace_environment_yml_takes_precedence(
    minimal_r_workspace, r_profile, r_assembly_config
):
    custom = "name: my-custom-env\nchannels: [conda-forge]\ndependencies: [r-base=4.4]\n"
    (minimal_r_workspace / "environment.yml").write_text(custom)
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    text = (repo / "environment.yml").read_text()
    assert "my-custom-env" in text


def test_h2_workspace_changelog_takes_precedence(
    minimal_r_workspace, r_profile, r_assembly_config
):
    custom = "# Custom CHANGELOG\nv1.2.3 shipped.\n"
    (minimal_r_workspace / "CHANGELOG.md").write_text(custom)
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)
    text = (repo / "CHANGELOG.md").read_text()
    assert "Custom CHANGELOG" in text
    assert "Keep a Changelog" not in text


# ---------------------------------------------------------------------------
# Regression guard: Python archetype unaffected
# ---------------------------------------------------------------------------


def test_h2_assemble_python_project_does_not_call_r_doc_generator(tmp_path):
    """assemble_python_project MUST NOT invoke generate_r_delivery_docs.

    Easiest assertion: monkey-patch the function to raise on call; assembly
    must complete without raising.
    """
    workspace = tmp_path / "py_proj"
    workspace.mkdir()
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

    with patch(
        "generate_assembly_map.generate_r_delivery_docs",
        side_effect=AssertionError(
            "Python assembler must not call generate_r_delivery_docs"
        ),
    ):
        repo = assemble_python_project(workspace, profile, assembly_config)

    assert (repo / "pyproject.toml").is_file()
    # R-archetype-only docs from H2 must NOT appear automatically for Python
    assert not (repo / "DESCRIPTION").exists()
    assert not (repo / "NAMESPACE").exists()


# ---------------------------------------------------------------------------
# Integration: validate_delivered_repo_contents finds 0 missing files
# ---------------------------------------------------------------------------


def test_h2_validate_passes_for_minimal_r_workspace_after_h2(
    minimal_r_workspace, r_profile, r_assembly_config
):
    """End-to-end BLOCKER closure: a minimal R workspace (only DESCRIPTION
    plus R/foo.R) MUST produce a delivered repo whose required-file set is
    fully populated after H1 (DESCRIPTION/NAMESPACE/testthat.R fallbacks)
    plus H2 (README/LICENSE/.gitignore/environment.yml/CHANGELOG.md).
    """
    repo = assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)

    required_r_files = [
        "DESCRIPTION",
        "NAMESPACE",
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        ".gitignore",
        "environment.yml",
    ]
    missing = [f for f in required_r_files if not (repo / f).exists()]
    assert missing == [], (
        f"After H1 + H2, delivered R repo MUST have all required files; "
        f"missing: {missing}"
    )


# ---------------------------------------------------------------------------
# Helper unit tests (license type dispatch + YAML manifest sourcing)
# ---------------------------------------------------------------------------


def test_h2_license_apache2_supported(r_profile):
    p = dict(r_profile)
    p["license"] = {"type": "Apache-2.0", "holder": "Acme"}
    text = _r_license_content(p)
    assert "Apache License" in text
    assert "Version 2.0" in text


def test_h2_license_unknown_falls_back_to_mit_with_comment(r_profile):
    p = dict(r_profile)
    p["license"] = {"type": "WTFPL", "holder": "Acme"}
    text = _r_license_content(p)
    # The note is documented at the top
    assert "WTFPL" in text
    assert "MIT License" in text


def test_h2_environment_yml_uses_derive_env_name(tmp_path, r_toolchain_stub):
    workspace = tmp_path / "myproj"
    workspace.mkdir()
    text = _r_environment_yml_content(workspace, r_toolchain_stub)
    # derive_env_name returns f"svp-{project_root.resolve().name}"
    assert "name: svp-myproj" in text
    # framework + quality merge dedup sort
    assert "r-testthat" in text
    assert "r-lintr" in text


def test_h2_changelog_contains_keep_a_changelog():
    text = _r_changelog_content("foo")
    assert "Keep a Changelog" in text
    assert "[Unreleased]" in text


def test_h2_readme_uses_project_name_in_install_block():
    profile = {
        "license": {"type": "MIT", "holder": "Acme"},
        "author": "Alice",
        "description": "Pkg desc",
    }
    text = _r_readme_content(profile, "foo_pkg")
    assert "# foo_pkg" in text
    assert 'devtools::install("./foo_pkg")' in text
    assert "Pkg desc" in text
    assert "MIT" in text
    assert "Alice" in text


def test_h2_gitignore_returns_nonempty_string():
    text = _r_gitignore_content()
    assert text.strip() != ""
    assert ".Rhistory" in text
