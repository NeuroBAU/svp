"""Cycle H3 (S3-193) -- verify (a) validate_delivered_repo_contents accepts
NEWS.md as alternative to CHANGELOG.md for R archetype (IMPROV-27);
(b) assemble_python_project and assemble_r_project auto-ship foundational
docs (specs, blueprint) to delivered repo's docs/ directory via
sync_debug_docs (IMPROV-32).

S3-103: tests use flat-module imports.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

# S3-103 honors flat-module imports.
from generate_assembly_map import (
    assemble_python_project,
    assemble_r_project,
)
from structural_check import validate_delivered_repo_contents
from sync_debug_docs import sync_debug_docs


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _r_project_with_toolchain(tmp_path: Path) -> Path:
    """Build a synthetic project_root that ships the R toolchain manifest.

    `assemble_r_project` calls `load_toolchain(project_root, language="r")`
    which resolves to `scripts/toolchain_defaults/r_conda_testthat.json`
    under project_root. Mirrors the H2 fixture pattern.
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


def _make_validate_project(
    tmp_path: Path,
    language: str,
    delivered_files: list[str],
) -> Path:
    """Build synthetic project_root + delivered repo for validation tests.

    - Writes profile.json + .svp/pipeline_state.json with delivered_repo_path.
    - Writes the named relative file paths into the delivered repo.
    - Returns project_root.
    """
    project_root = tmp_path / "myproj"
    project_root.mkdir()
    (project_root / ".svp").mkdir()

    profile = {
        "archetype": f"{language}_project",
        "language": {"primary": language},
    }
    (project_root / "project_profile.json").write_text(json.dumps(profile))

    sibling = tmp_path / "myproj-repo"
    sibling.mkdir()
    for rel in delivered_files:
        f = sibling / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("placeholder")

    state_data = {
        "stage": "5",
        "sub_stage": "compliance_scan",
        "delivered_repo_path": str(sibling),
    }
    (project_root / ".svp" / "pipeline_state.json").write_text(
        json.dumps(state_data)
    )
    return project_root


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
def python_profile() -> Dict[str, Any]:
    return {
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


@pytest.fixture
def python_assembly_config() -> Dict[str, Any]:
    return {
        "project_name": "py_proj",
        "description": "A test Python project",
        "author": "Test Author",
    }


@pytest.fixture
def minimal_r_workspace(tmp_path: Path) -> Path:
    """Build a synthetic R-package workspace at tmp_path/myrproj.

    Mirrors the H2 minimal_r_workspace fixture but additionally provisions
    specs/ + blueprint/ to exercise the H3 docs/ auto-ship.
    """
    project_root = _r_project_with_toolchain(tmp_path)
    workspace = project_root / "myrproj"
    workspace.mkdir()
    (workspace / "R").mkdir()
    (workspace / "R" / "foo.R").write_text("foo <- function() 1\n")
    (workspace / "tests" / "testthat").mkdir(parents=True)
    (workspace / "DESCRIPTION").write_text(
        "Package: myrproj\nVersion: 0.1\n"
    )
    # Foundational docs that the H3 auto-ship should pick up.
    (workspace / "specs").mkdir()
    (workspace / "specs" / "stakeholder_spec.md").write_text(
        "# Test stakeholder spec\n"
    )
    (workspace / "blueprint").mkdir()
    (workspace / "blueprint" / "blueprint_prose.md").write_text(
        "# Test blueprint prose\n"
    )
    (workspace / "blueprint" / "blueprint_contracts.md").write_text(
        "# Test blueprint contracts\n"
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
def minimal_python_workspace(tmp_path: Path) -> Path:
    """Build a synthetic Python workspace with foundational docs."""
    workspace = tmp_path / "py_proj"
    workspace.mkdir()
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_basic.py").write_text(
        "def test_basic(): assert True\n"
    )
    (workspace / "specs").mkdir()
    (workspace / "specs" / "stakeholder_spec.md").write_text(
        "# Test Python stakeholder spec\n"
    )
    (workspace / "blueprint").mkdir()
    (workspace / "blueprint" / "blueprint_prose.md").write_text(
        "# Test Python blueprint prose\n"
    )
    (workspace / "blueprint" / "blueprint_contracts.md").write_text(
        "# Test Python blueprint contracts\n"
    )
    return workspace


# ---------------------------------------------------------------------------
# IMPROV-27 tests (5)
# ---------------------------------------------------------------------------


def test_h3_r_archetype_accepts_NEWS_md_when_changelog_absent(tmp_path):
    """R workspace with NEWS.md but no CHANGELOG.md -> validate passes the
    one-of changelog check (no missing-changelog finding).
    """
    project_root = _make_validate_project(
        tmp_path,
        language="r",
        delivered_files=[
            "DESCRIPTION",
            "NAMESPACE",
            "README.md",
            "NEWS.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ],
    )
    findings = validate_delivered_repo_contents(project_root)
    messages = [f["message"] for f in findings]
    # No missing-changelog finding (the post-loop one-of must accept NEWS.md).
    assert not any("CHANGELOG.md" in m for m in messages), (
        f"NEWS.md must satisfy R-archetype changelog requirement; "
        f"unexpected messages: {messages}"
    )
    assert not any("NEWS.md" in m for m in messages), (
        f"NEWS.md present must not produce a missing-file finding; "
        f"unexpected messages: {messages}"
    )


def test_h3_r_archetype_accepts_CHANGELOG_md_when_news_absent(tmp_path):
    """Regression guard: R workspace with CHANGELOG.md but no NEWS.md
    -> validate passes (existing convention preserved).
    """
    project_root = _make_validate_project(
        tmp_path,
        language="r",
        delivered_files=[
            "DESCRIPTION",
            "NAMESPACE",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ],
    )
    findings = validate_delivered_repo_contents(project_root)
    messages = [f["message"] for f in findings]
    assert not any("CHANGELOG.md" in m for m in messages), (
        f"CHANGELOG.md present must not produce missing-file finding; "
        f"messages: {messages}"
    )
    assert not any("NEWS.md" in m for m in messages), (
        f"NEWS.md absent does not matter when CHANGELOG.md is present; "
        f"messages: {messages}"
    )


def test_h3_r_archetype_fails_when_both_changelog_and_news_absent(tmp_path):
    """R workspace with neither CHANGELOG.md nor NEWS.md -> validate
    reports exactly one missing-file error mentioning both filenames.
    """
    project_root = _make_validate_project(
        tmp_path,
        language="r",
        delivered_files=[
            "DESCRIPTION",
            "NAMESPACE",
            "README.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ],
    )
    findings = validate_delivered_repo_contents(project_root)
    changelog_findings = [
        f for f in findings
        if "CHANGELOG.md" in f["message"] or "NEWS.md" in f["message"]
    ]
    assert len(changelog_findings) == 1, (
        f"Expected exactly one changelog-related finding, got "
        f"{len(changelog_findings)}: "
        f"{[f['message'] for f in changelog_findings]}"
    )
    msg = changelog_findings[0]["message"]
    assert "CHANGELOG.md" in msg, msg
    assert "NEWS.md" in msg, msg
    assert "S3-193" in msg, msg


def test_h3_r_archetype_passes_when_both_changelog_and_news_present(tmp_path):
    """Regression guard: R workspace with both CHANGELOG.md and NEWS.md
    -> validate passes (no duplicate or conflicting finding).
    """
    project_root = _make_validate_project(
        tmp_path,
        language="r",
        delivered_files=[
            "DESCRIPTION",
            "NAMESPACE",
            "README.md",
            "CHANGELOG.md",
            "NEWS.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ],
    )
    findings = validate_delivered_repo_contents(project_root)
    messages = [f["message"] for f in findings]
    assert not any(
        "CHANGELOG.md" in m or "NEWS.md" in m for m in messages
    ), f"Both files present; no findings expected; messages: {messages}"


def test_h3_python_archetype_still_requires_CHANGELOG_md(tmp_path):
    """Regression guard: Python validation unchanged. Workspace with NEWS.md
    but no CHANGELOG.md -> validate FAILS for Python (Python convention is
    CHANGELOG.md; NEWS.md is NOT an alternative for Python).
    """
    project_root = _make_validate_project(
        tmp_path,
        language="python",
        delivered_files=[
            "pyproject.toml",
            "README.md",
            "NEWS.md",  # NEWS.md present
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ],
    )
    findings = validate_delivered_repo_contents(project_root)
    messages = [f["message"] for f in findings]
    # Python must still flag missing CHANGELOG.md.
    assert any(
        "CHANGELOG.md" in m and "python" in m for m in messages
    ), (
        f"Python archetype must still strictly require CHANGELOG.md; "
        f"messages: {messages}"
    )


# ---------------------------------------------------------------------------
# IMPROV-32 tests (5)
# ---------------------------------------------------------------------------


def test_h3_assemble_python_project_ships_docs_directory(
    minimal_python_workspace, python_profile, python_assembly_config
):
    """Workspace with specs/stakeholder_spec.md + blueprint/blueprint_prose.md
    -> delivered repo has docs/stakeholder_spec.md + docs/blueprint_prose.md.
    """
    repo = assemble_python_project(
        minimal_python_workspace, python_profile, python_assembly_config
    )
    docs_dir = repo / "docs"
    assert docs_dir.is_dir(), (
        "Python assembler must auto-ship docs/ via sync_debug_docs"
    )
    assert (docs_dir / "stakeholder_spec.md").is_file(), (
        "stakeholder_spec.md must be copied into delivered repo docs/"
    )
    assert (docs_dir / "blueprint_prose.md").is_file(), (
        "blueprint_prose.md must be copied into delivered repo docs/"
    )
    assert (docs_dir / "blueprint_contracts.md").is_file(), (
        "blueprint_contracts.md must be copied into delivered repo docs/"
    )


def test_h3_assemble_r_project_ships_docs_directory(
    minimal_r_workspace, r_profile, r_assembly_config
):
    """R archetype: workspace specs/ + blueprint/ -> delivered repo docs/."""
    repo = assemble_r_project(
        minimal_r_workspace, r_profile, r_assembly_config
    )
    docs_dir = repo / "docs"
    assert docs_dir.is_dir(), (
        "R assembler must auto-ship docs/ via sync_debug_docs"
    )
    assert (docs_dir / "stakeholder_spec.md").is_file(), (
        "stakeholder_spec.md must be copied into delivered repo docs/"
    )
    assert (docs_dir / "blueprint_prose.md").is_file(), (
        "blueprint_prose.md must be copied into delivered repo docs/"
    )
    assert (docs_dir / "blueprint_contracts.md").is_file(), (
        "blueprint_contracts.md must be copied into delivered repo docs/"
    )


def test_h3_sync_debug_docs_uses_repo_dir_kwarg_when_provided(tmp_path):
    """sync_debug_docs(project_root, repo_dir=explicit_path) uses
    explicit_path even when state.delivered_repo_path is unset.
    """
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / ".svp").mkdir()
    (project_root / "specs").mkdir()
    (project_root / "specs" / "stakeholder_spec.md").write_text(
        "# explicit-kwarg test\n"
    )
    (project_root / "blueprint").mkdir()
    (project_root / "blueprint" / "blueprint_prose.md").write_text(
        "# kwarg blueprint\n"
    )
    # State has NO delivered_repo_path -> sync_debug_docs would normally
    # silently return; with the kwarg, it should use repo_dir directly.
    (project_root / ".svp" / "pipeline_state.json").write_text(
        json.dumps({"stage": "5", "sub_stage": "compliance_scan"})
    )

    explicit_repo = tmp_path / "explicit-repo"
    explicit_repo.mkdir()

    sync_debug_docs(project_root, repo_dir=explicit_repo)

    assert (explicit_repo / "docs" / "stakeholder_spec.md").is_file(), (
        "kwarg path must be honored when state has no delivered_repo_path"
    )
    assert (explicit_repo / "docs" / "blueprint_prose.md").is_file(), (
        "kwarg path must receive blueprint files"
    )


def test_h3_sync_debug_docs_falls_back_to_state_when_no_kwarg(tmp_path):
    """Regression guard: sync_debug_docs(project_root) without kwarg still
    reads delivered_repo_path from state (existing callers unchanged).
    """
    project_root = tmp_path / "proj2"
    project_root.mkdir()
    (project_root / ".svp").mkdir()
    (project_root / "specs").mkdir()
    (project_root / "specs" / "stakeholder_spec.md").write_text(
        "# back-compat test\n"
    )
    (project_root / "blueprint").mkdir()
    (project_root / "blueprint" / "blueprint_prose.md").write_text(
        "# back-compat blueprint\n"
    )

    state_repo = tmp_path / "state-repo"
    state_repo.mkdir()
    (project_root / ".svp" / "pipeline_state.json").write_text(
        json.dumps(
            {
                "stage": "5",
                "sub_stage": "compliance_scan",
                "delivered_repo_path": str(state_repo),
            }
        )
    )

    # Call WITHOUT repo_dir kwarg -- old callers must still work.
    sync_debug_docs(project_root)

    assert (state_repo / "docs" / "stakeholder_spec.md").is_file(), (
        "Existing call signature without kwarg must read state and copy "
        "spec into delivered_repo_path/docs/"
    )
    assert (state_repo / "docs" / "blueprint_prose.md").is_file(), (
        "Existing call signature without kwarg must copy blueprint files"
    )


def test_h3_integration_minimal_r_workspace_passes_full_validation_and_has_docs(
    minimal_r_workspace, r_profile, r_assembly_config
):
    """End-to-end: assemble_r_project on minimal R workspace -> delivered repo
    has docs/ populated AND passes validate_delivered_repo_contents (no
    missing-file errors for R archetype after H1 + H2 + H3).
    """
    repo = assemble_r_project(
        minimal_r_workspace, r_profile, r_assembly_config
    )

    # docs/ shipped
    assert (repo / "docs" / "stakeholder_spec.md").is_file()
    assert (repo / "docs" / "blueprint_prose.md").is_file()

    # All R required files present via H1 + H2 layered fallback
    required_r_files = [
        "DESCRIPTION",
        "NAMESPACE",
        "README.md",
        "LICENSE",
        ".gitignore",
        "environment.yml",
    ]
    for fname in required_r_files:
        assert (repo / fname).exists(), f"missing required file: {fname}"

    # Either CHANGELOG.md or NEWS.md must satisfy the changelog one-of
    has_changelog = (repo / "CHANGELOG.md").exists()
    has_news = (repo / "NEWS.md").exists()
    assert has_changelog or has_news, (
        "delivered R repo must have CHANGELOG.md OR NEWS.md (S3-193)"
    )

    # Build a synthetic project_root pointing at this delivered repo and
    # invoke the validator end-to-end.
    project_root = minimal_r_workspace.parent / "validate_proj"
    project_root.mkdir()
    (project_root / ".svp").mkdir()
    (project_root / "project_profile.json").write_text(
        json.dumps({"archetype": "r_project", "language": {"primary": "r"}})
    )
    (project_root / ".svp" / "pipeline_state.json").write_text(
        json.dumps(
            {
                "stage": "5",
                "sub_stage": "compliance_scan",
                "delivered_repo_path": str(repo),
            }
        )
    )
    findings = validate_delivered_repo_contents(project_root)
    # Filter out assembly-map findings (orthogonal to H3); we care only
    # about missing-file findings for the R archetype.
    missing_file_findings = [
        f for f in findings
        if "missing required file" in f["message"]
        or "missing required changelog" in f["message"]
    ]
    assert missing_file_findings == [], (
        f"After H1+H2+H3, minimal R workspace must produce 0 missing-file "
        f"findings; got: "
        f"{[f['message'] for f in missing_file_findings]}"
    )
