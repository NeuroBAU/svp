"""Regression tests for Bug S3-43: restore_project must carry forward references."""
import os
from pathlib import Path

import pytest


def _pass2_repo() -> Path:
    """Resolve the delivered Pass 2 repo, or skip if it isn't available.

    Resolution order: ``SVP_PASS2_REPO`` env var, then the conventional sibling
    ``<repo-parent>/svp2.2-pass2-repo``. The original hardcoded developer path
    (a personal macOS Nextcloud directory) made these tests fail on every other
    machine; resolving dynamically keeps them meaningful where the repo exists
    and skips cleanly where it does not.
    """
    env = os.environ.get("SVP_PASS2_REPO")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.append(Path(__file__).resolve().parents[2].parent / "svp2.2-pass2-repo")
    for repo in candidates:
        if repo.is_dir():
            return repo
    pytest.skip("Pass 2 delivered repo not present (set SVP_PASS2_REPO to enable)")


def test_pass2_repo_has_readme():
    """S3-43: Pass 2 repo must contain README.md."""
    repo = _pass2_repo()
    assert (repo / "README.md").exists(), "Pass 2 repo missing README.md"


def test_pass2_repo_has_changelog():
    """S3-43: Pass 2 repo must contain CHANGELOG.md."""
    repo = _pass2_repo()
    assert (repo / "CHANGELOG.md").exists(), "Pass 2 repo missing CHANGELOG.md"


def test_pass2_repo_has_license():
    """S3-43: Pass 2 repo must contain LICENSE."""
    repo = _pass2_repo()
    assert (repo / "LICENSE").exists(), "Pass 2 repo missing LICENSE"


def test_restore_project_copies_references(tmp_path, monkeypatch):
    """S3-43: restore_project must copy references/ if present in source."""
    from svp_launcher import restore_project

    # Create source workspace with references
    source = tmp_path / "source"
    source.mkdir()
    specs_dir = source / "specs"
    specs_dir.mkdir()
    (specs_dir / "stakeholder_spec.md").write_text("# Spec", encoding="utf-8")
    bp_dir = source / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_contracts.md").write_text("# Contracts", encoding="utf-8")
    (bp_dir / "blueprint_prose.md").write_text("# Prose", encoding="utf-8")
    context = source / "context.md"
    context.write_text("# Context", encoding="utf-8")
    scripts = source / "scripts"
    scripts.mkdir()
    (scripts / "routing.py").write_text("# routing", encoding="utf-8")
    profile = source / "project_profile.json"
    profile.write_text('{"archetype": "python_project"}', encoding="utf-8")
    refs = source / "references"
    refs.mkdir()
    (refs / "existing_readme.md").write_text("# README reference", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    result = restore_project(
        project_name="test-restore",
        spec_path=specs_dir / "stakeholder_spec.md",
        blueprint_dir=bp_dir,
        context_path=context,
        scripts_source=scripts,
        profile_path=profile,
    )

    # References should have been copied
    dest_refs = result / "references"
    assert dest_refs.is_dir(), "references/ not copied"
    assert (dest_refs / "existing_readme.md").exists(), "existing_readme.md not carried forward"
