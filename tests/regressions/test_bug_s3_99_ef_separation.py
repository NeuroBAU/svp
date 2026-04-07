"""Regression tests for Bug S3-99: E/F separation for workspace artifact carry-over.

Verifies that:
- CLAUDE.md templates are correctly tiered (Tier 1 universal, Tier 2 SVP-only)
- create_new_project() produces empty tests/ scaffold with Tier 1 CLAUDE.md
- copy_svp_regression_tests() copies full test suite for E/F
- enrich_claude_md_for_svp_build() appends Tier 2 idempotently
- assemble_svp_workspace_artifacts() writes carry-over files to repo for E/F
- Normal (A-D) projects never see SVP internals
"""

import json
import shutil
from pathlib import Path

import pytest

from svp_launcher import (
    CLAUDE_MD_SVP_ADDENDUM,
    CLAUDE_MD_TEMPLATE,
    copy_svp_regression_tests,
    create_new_project,
    enrich_claude_md_for_svp_build,
)
from generate_assembly_map import assemble_svp_workspace_artifacts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plugin_root(tmp_path):
    """Create a minimal plugin root with scripts/ and tests/."""
    root = tmp_path / "svp"
    root.mkdir()

    # Minimal scripts directory
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "__init__.py").write_text("")
    (scripts / "routing.py").write_text("# routing stub")

    # SVP regression tests
    tests = root / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    regs = tests / "regressions"
    regs.mkdir()
    (regs / "__init__.py").write_text("")
    (regs / "test_bug42_example.py").write_text("def test_x(): pass")
    unit5 = tests / "unit_5"
    unit5.mkdir()
    (unit5 / "test_unit_5.py").write_text("def test_y(): pass")

    return root


@pytest.fixture
def project(tmp_path, plugin_root, monkeypatch):
    """Create a project via create_new_project."""
    monkeypatch.chdir(tmp_path)
    return create_new_project("test_project", plugin_root)


# ---------------------------------------------------------------------------
# Class 1: CLAUDE.md Template Content
# ---------------------------------------------------------------------------


class TestClaudeMdTemplates:
    """Bug S3-99: CLAUDE.md templates must be correctly tiered."""

    def test_tier1_has_project_name_placeholder(self):
        assert "{project_name}" in CLAUDE_MD_TEMPLATE

    def test_tier1_has_action_cycle(self):
        assert "Six-Step Action Cycle" in CLAUDE_MD_TEMPLATE

    def test_tier1_has_routing_instructions(self):
        assert "routing script" in CLAUDE_MD_TEMPLATE

    def test_tier1_no_bug_protocol(self):
        """Tier 1 must NOT contain bug-fixing protocol."""
        assert "Manual Bug-Fixing Protocol" not in CLAUDE_MD_TEMPLATE

    def test_tier2_has_bug_protocol(self):
        assert "Manual Bug-Fixing Protocol" in CLAUDE_MD_SVP_ADDENDUM

    def test_tier2_has_stubs_note(self):
        assert "single source of truth" in CLAUDE_MD_SVP_ADDENDUM.lower()

    def test_tier2_has_sync_instructions(self):
        assert "sync_workspace.sh" in CLAUDE_MD_SVP_ADDENDUM

    def test_tier2_has_deployed_artifacts(self):
        assert "DEPLOYED ARTIFACTS" in CLAUDE_MD_SVP_ADDENDUM


# ---------------------------------------------------------------------------
# Class 2: create_new_project Tests Scaffold
# ---------------------------------------------------------------------------


class TestCreateNewProjectTestsScaffold:
    """Bug S3-99: create_new_project produces empty tests/ scaffold."""

    def test_tests_dir_exists(self, project):
        assert (project / "tests").is_dir()

    def test_tests_init_exists(self, project):
        assert (project / "tests" / "__init__.py").exists()

    def test_regressions_dir_exists(self, project):
        assert (project / "tests" / "regressions").is_dir()

    def test_regressions_init_exists(self, project):
        assert (project / "tests" / "regressions" / "__init__.py").exists()

    def test_no_svp_regression_tests(self, project):
        """A-D projects must NOT have SVP regression test files."""
        test_files = list((project / "tests").rglob("test_bug*.py"))
        assert test_files == [], (
            f"SVP regression tests should not be in A-D projects: {test_files}"
        )

    def test_no_unit_test_dirs(self, project):
        """A-D projects must NOT have unit_N/ test directories."""
        unit_dirs = [
            d for d in (project / "tests").iterdir()
            if d.is_dir() and d.name.startswith("unit_")
        ]
        assert unit_dirs == [], (
            f"SVP unit test dirs should not be in A-D projects: {unit_dirs}"
        )

    def test_claude_md_has_project_name(self, project):
        content = (project / "CLAUDE.md").read_text()
        assert "test_project" in content

    def test_claude_md_tier1_only(self, project):
        content = (project / "CLAUDE.md").read_text()
        assert "Six-Step Action Cycle" in content
        assert "Manual Bug-Fixing Protocol" not in content


# ---------------------------------------------------------------------------
# Class 3: copy_svp_regression_tests
# ---------------------------------------------------------------------------


class TestCopySvpRegressionTests:
    """Bug S3-99: copy_svp_regression_tests for E/F builds."""

    def test_copies_test_tree(self, project, plugin_root):
        copy_svp_regression_tests(project, plugin_root)
        assert (project / "tests" / "regressions" / "test_bug42_example.py").exists()
        assert (project / "tests" / "unit_5" / "test_unit_5.py").exists()

    def test_overwrites_existing(self, project, plugin_root):
        """Existing scaffold is replaced with full test suite."""
        # Scaffold has __init__.py only
        assert not (project / "tests" / "regressions" / "test_bug42_example.py").exists()
        copy_svp_regression_tests(project, plugin_root)
        assert (project / "tests" / "regressions" / "test_bug42_example.py").exists()

    def test_handles_missing_source(self, tmp_path):
        """Gracefully handles plugin with no tests/ directory."""
        empty_plugin = tmp_path / "empty_plugin"
        empty_plugin.mkdir()
        project = tmp_path / "proj"
        project.mkdir()
        (project / "tests").mkdir()
        copy_svp_regression_tests(project, empty_plugin)
        # No error raised, tests/ unchanged
        assert (project / "tests").is_dir()


# ---------------------------------------------------------------------------
# Class 4: enrich_claude_md_for_svp_build
# ---------------------------------------------------------------------------


class TestEnrichClaudeMdForSvpBuild:
    """Bug S3-99: enrich_claude_md_for_svp_build appends Tier 2."""

    def test_appends_tier2(self, project):
        enrich_claude_md_for_svp_build(project)
        content = (project / "CLAUDE.md").read_text()
        assert "Manual Bug-Fixing Protocol" in content
        assert "Six-Step Action Cycle" in content  # Tier 1 still present

    def test_idempotent(self, project):
        enrich_claude_md_for_svp_build(project)
        content_after_first = (project / "CLAUDE.md").read_text()
        enrich_claude_md_for_svp_build(project)
        content_after_second = (project / "CLAUDE.md").read_text()
        assert content_after_first == content_after_second
        assert content_after_second.count("Manual Bug-Fixing Protocol") == 1

    def test_handles_missing_file(self, tmp_path):
        """No error when CLAUDE.md doesn't exist."""
        enrich_claude_md_for_svp_build(tmp_path)  # No CLAUDE.md here
        assert not (tmp_path / "CLAUDE.md").exists()


# ---------------------------------------------------------------------------
# Class 5: assemble_svp_workspace_artifacts
# ---------------------------------------------------------------------------


class TestAssembleSvpWorkspaceArtifacts:
    """Bug S3-99: assemble_svp_workspace_artifacts for E/F Stage 5."""

    def _make_workspace(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "sync_workspace.sh").write_text("#!/bin/bash\necho sync")
        examples = ws / "examples"
        examples.mkdir()
        (examples / "game-of-life").mkdir()
        (examples / "game-of-life" / "spec.md").write_text("# GoL spec")
        return ws

    def test_writes_claude_md(self, tmp_path):
        ws = self._make_workspace(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()
        assemble_svp_workspace_artifacts(repo, ws, "my_svp")
        assert (repo / "CLAUDE.md").exists()
        content = (repo / "CLAUDE.md").read_text()
        assert "my_svp" in content
        assert "Six-Step Action Cycle" in content
        assert "Manual Bug-Fixing Protocol" in content

    def test_copies_sync_workspace(self, tmp_path):
        ws = self._make_workspace(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()
        assemble_svp_workspace_artifacts(repo, ws, "test")
        assert (repo / "sync_workspace.sh").exists()

    def test_copies_examples(self, tmp_path):
        ws = self._make_workspace(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()
        assemble_svp_workspace_artifacts(repo, ws, "test")
        assert (repo / "examples" / "game-of-life" / "spec.md").exists()

    def test_returns_counts(self, tmp_path):
        ws = self._make_workspace(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()
        result = assemble_svp_workspace_artifacts(repo, ws, "test")
        assert result["files"] == 3  # CLAUDE.md + sync_workspace.sh + examples/

    def test_graceful_missing_sync(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        # No sync_workspace.sh, no examples/
        repo = tmp_path / "repo"
        repo.mkdir()
        result = assemble_svp_workspace_artifacts(repo, ws, "test")
        assert (repo / "CLAUDE.md").exists()  # Always written
        assert not (repo / "sync_workspace.sh").exists()
        assert result["files"] == 1


# ---------------------------------------------------------------------------
# Class 6: E/F vs A-D Integration
# ---------------------------------------------------------------------------


class TestEFvsADSeparation:
    """Bug S3-99: E/F and A-D paths produce different artifacts."""

    def test_ad_project_clean(self, project):
        """A-D project: Tier 1 CLAUDE.md, empty tests/, no sync_workspace.sh."""
        content = (project / "CLAUDE.md").read_text()
        assert "Manual Bug-Fixing Protocol" not in content
        assert not list((project / "tests").rglob("test_bug*.py"))

    def test_ef_enrichment(self, project, plugin_root):
        """E/F project: after enrichment, has Tier 2 + regression tests."""
        enrich_claude_md_for_svp_build(project)
        copy_svp_regression_tests(project, plugin_root)

        content = (project / "CLAUDE.md").read_text()
        assert "Manual Bug-Fixing Protocol" in content
        assert (project / "tests" / "regressions" / "test_bug42_example.py").exists()

    def test_stage5_produces_repo_with_carryover(self, tmp_path):
        """Stage 5 for E/F: repo has CLAUDE.md + sync_workspace.sh + examples/."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "sync_workspace.sh").write_text("#!/bin/bash")
        (ws / "examples").mkdir()
        (ws / "examples" / "gol").mkdir()

        repo = tmp_path / "repo"
        repo.mkdir()

        assemble_svp_workspace_artifacts(repo, ws, "svp_self")

        assert (repo / "CLAUDE.md").exists()
        assert "Manual Bug-Fixing Protocol" in (repo / "CLAUDE.md").read_text()
        assert (repo / "sync_workspace.sh").exists()
        assert (repo / "examples" / "gol").is_dir()
