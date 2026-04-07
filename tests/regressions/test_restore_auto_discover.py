"""Regression tests for restore_project auto-discover (Bug S3-103 Phase 4).

Tests the --repo auto-discover mechanism that finds artifacts from
the repo's docs/ directory, and the sync_config.json generation.
"""
import json
from pathlib import Path

import pytest

from svp_launcher import _auto_discover_from_repo, restore_project


# --- Auto-discover function tests ---


class TestAutoDiscover:
    """_auto_discover_from_repo must find all required artifacts."""

    def _make_repo(self, tmp_path):
        """Create a minimal repo structure for auto-discover."""
        repo = tmp_path / "repo"
        docs = repo / "docs"
        docs.mkdir(parents=True)
        (docs / "stakeholder_spec.md").write_text("# Spec")
        (docs / "blueprint_prose.md").write_text("# Prose")
        (docs / "blueprint_contracts.md").write_text("# Contracts")
        (docs / "project_context.md").write_text("# Context")
        (docs / "project_profile.json").write_text('{"archetype": "python_project"}')
        refs = docs / "references"
        refs.mkdir()
        (refs / "svp_2_1_lessons_learned.md").write_text("# Lessons")
        scripts = repo / "svp" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "routing.py").write_text("# routing")
        return repo

    def test_finds_spec(self, tmp_path):
        repo = self._make_repo(tmp_path)
        result = _auto_discover_from_repo(repo)
        assert result["spec_path"] == repo / "docs" / "stakeholder_spec.md"

    def test_finds_blueprint_dir(self, tmp_path):
        repo = self._make_repo(tmp_path)
        result = _auto_discover_from_repo(repo)
        assert result["blueprint_dir"] == repo / "docs"

    def test_finds_context(self, tmp_path):
        repo = self._make_repo(tmp_path)
        result = _auto_discover_from_repo(repo)
        assert result["context_path"] == repo / "docs" / "project_context.md"

    def test_finds_scripts(self, tmp_path):
        repo = self._make_repo(tmp_path)
        result = _auto_discover_from_repo(repo)
        assert result["scripts_source"] == repo / "svp" / "scripts"

    def test_finds_profile(self, tmp_path):
        repo = self._make_repo(tmp_path)
        result = _auto_discover_from_repo(repo)
        assert result["profile_path"] == repo / "docs" / "project_profile.json"

    def test_raises_on_missing_docs(self, tmp_path):
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        with pytest.raises(FileNotFoundError, match="No docs/"):
            _auto_discover_from_repo(repo)

    def test_raises_on_missing_spec(self, tmp_path):
        repo = self._make_repo(tmp_path)
        (repo / "docs" / "stakeholder_spec.md").unlink()
        with pytest.raises(FileNotFoundError, match="stakeholder_spec"):
            _auto_discover_from_repo(repo)

    def test_raises_on_missing_blueprint(self, tmp_path):
        repo = self._make_repo(tmp_path)
        (repo / "docs" / "blueprint_contracts.md").unlink()
        with pytest.raises(FileNotFoundError, match="blueprint_contracts"):
            _auto_discover_from_repo(repo)

    def test_raises_on_missing_scripts(self, tmp_path):
        repo = self._make_repo(tmp_path)
        import shutil
        shutil.rmtree(repo / "svp")
        with pytest.raises(FileNotFoundError, match="scripts"):
            _auto_discover_from_repo(repo)

    def test_raises_on_missing_profile(self, tmp_path):
        repo = self._make_repo(tmp_path)
        (repo / "docs" / "project_profile.json").unlink()
        with pytest.raises(FileNotFoundError, match="project_profile"):
            _auto_discover_from_repo(repo)


# --- Restore with --repo tests ---


class TestRestoreWithRepo:
    """restore_project with repo_path creates correct workspace."""

    def _make_repo(self, tmp_path):
        """Create a minimal repo structure."""
        repo = tmp_path / "repo"
        docs = repo / "docs"
        docs.mkdir(parents=True)
        (docs / "stakeholder_spec.md").write_text("# Spec")
        (docs / "blueprint_prose.md").write_text("# Prose")
        (docs / "blueprint_contracts.md").write_text("# Contracts")
        (docs / "project_context.md").write_text("# Context")
        (docs / "CLAUDE.md").write_text("# CLAUDE")
        (docs / "project_profile.json").write_text('{"archetype": "python_project"}')
        refs = docs / "references"
        refs.mkdir()
        (refs / "existing_readme.md").write_text("# README ref")
        scripts = repo / "svp" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "routing.py").write_text("# routing")
        (repo / "sync_workspace.sh").write_text("#!/bin/bash\necho sync")
        (repo / "ruff.toml").write_text("[tool.ruff]")
        examples = repo / "examples" / "game-of-life"
        examples.mkdir(parents=True)
        (examples / "stakeholder_spec.md").write_text("# GoL Spec")
        return repo

    def test_creates_workspace_with_spec(self, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        discovered = _auto_discover_from_repo(repo)
        result = restore_project(
            "test-ws", discovered["spec_path"], discovered["blueprint_dir"],
            discovered["context_path"], discovered["scripts_source"],
            discovered["profile_path"], repo_path=repo,
        )
        assert (result / "specs" / "stakeholder_spec.md").exists()

    def test_creates_workspace_with_blueprint(self, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        discovered = _auto_discover_from_repo(repo)
        result = restore_project(
            "test-ws", discovered["spec_path"], discovered["blueprint_dir"],
            discovered["context_path"], discovered["scripts_source"],
            discovered["profile_path"], repo_path=repo,
        )
        assert (result / "blueprint" / "blueprint_contracts.md").exists()
        assert (result / "blueprint" / "blueprint_prose.md").exists()

    def test_writes_sync_config(self, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        discovered = _auto_discover_from_repo(repo)
        result = restore_project(
            "test-ws", discovered["spec_path"], discovered["blueprint_dir"],
            discovered["context_path"], discovered["scripts_source"],
            discovered["profile_path"], repo_path=repo,
        )
        config_path = result / ".svp" / "sync_config.json"
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config["repo"] == str(repo)

    def test_no_sync_config_without_repo_path(self, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        discovered = _auto_discover_from_repo(repo)
        result = restore_project(
            "test-ws2", discovered["spec_path"], discovered["blueprint_dir"],
            discovered["context_path"], discovered["scripts_source"],
            discovered["profile_path"],
        )
        config_path = result / ".svp" / "sync_config.json"
        assert not config_path.exists()

    def test_copies_claude_md_from_docs(self, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        discovered = _auto_discover_from_repo(repo)
        result = restore_project(
            "test-ws", discovered["spec_path"], discovered["blueprint_dir"],
            discovered["context_path"], discovered["scripts_source"],
            discovered["profile_path"], repo_path=repo,
        )
        assert (result / "CLAUDE.md").exists()
        assert (result / "CLAUDE.md").read_text() == "# CLAUDE"

    def test_copies_references_from_docs(self, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        discovered = _auto_discover_from_repo(repo)
        result = restore_project(
            "test-ws", discovered["spec_path"], discovered["blueprint_dir"],
            discovered["context_path"], discovered["scripts_source"],
            discovered["profile_path"], repo_path=repo,
        )
        assert (result / "references" / "existing_readme.md").exists()
