"""Regression tests for Bug S3-43: restore_project must carry forward references."""
from pathlib import Path


def test_pass2_repo_has_readme():
    """S3-43: Pass 2 repo must contain README.md."""
    repo = Path("/Users/cfusco/Nextcloud/coding projects/svp2.2/svp2.2-pass2-repo")
    assert (repo / "README.md").exists(), "Pass 2 repo missing README.md"


def test_pass2_repo_has_changelog():
    """S3-43: Pass 2 repo must contain CHANGELOG.md."""
    repo = Path("/Users/cfusco/Nextcloud/coding projects/svp2.2/svp2.2-pass2-repo")
    assert (repo / "CHANGELOG.md").exists(), "Pass 2 repo missing CHANGELOG.md"


def test_pass2_repo_has_license():
    """S3-43: Pass 2 repo must contain LICENSE."""
    repo = Path("/Users/cfusco/Nextcloud/coding projects/svp2.2/svp2.2-pass2-repo")
    assert (repo / "LICENSE").exists(), "Pass 2 repo missing LICENSE"


def test_restore_project_copies_references(tmp_path, monkeypatch):
    """S3-43: restore_project must copy references/ if present in source."""
    from svp_launcher import restore_project

    # Create source workspace with references
    source = tmp_path / "source"
    source.mkdir()
    specs_dir = source / "specs"
    specs_dir.mkdir()
    (specs_dir / "stakeholder_spec.md").write_text("# Spec")
    bp_dir = source / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_contracts.md").write_text("# Contracts")
    (bp_dir / "blueprint_prose.md").write_text("# Prose")
    context = source / "context.md"
    context.write_text("# Context")
    scripts = source / "scripts"
    scripts.mkdir()
    (scripts / "routing.py").write_text("# routing")
    profile = source / "project_profile.json"
    profile.write_text('{"archetype": "python_project"}')
    refs = source / "references"
    refs.mkdir()
    (refs / "existing_readme.md").write_text("# README reference")

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
