"""Bug S3-108 regression: hook scripts must be deployed to .claude/scripts/.

The plugin hooks.json references .claude/scripts/*.sh but nothing copied
the generated shell scripts from svp/hooks/ to .claude/scripts/ in the
project workspace. This test verifies that create_new_project() and
restore_project() both deploy hook scripts correctly.
"""

import json
from pathlib import Path

from svp_launcher import create_new_project, restore_project


HOOK_SCRIPTS = [
    "write_authorization.sh",
    "non_svp_protection.sh",
    "stub_sentinel_check.sh",
    "monitoring_reminder.sh",
]


def _setup_plugin_with_hooks(plugin_root: Path) -> None:
    """Create minimal plugin structure with hook scripts."""
    scripts_dir = plugin_root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "routing.py").write_text("# routing\n")
    toolchain_dir = plugin_root / "toolchains"
    toolchain_dir.mkdir(exist_ok=True)
    (toolchain_dir / "python_conda_pytest.json").write_text("{}\n")
    ruff_file = plugin_root / "ruff.toml"
    ruff_file.write_text("line-length = 88\n")
    plugin_json_dir = plugin_root / ".claude-plugin"
    plugin_json_dir.mkdir(exist_ok=True)
    (plugin_json_dir / "plugin.json").write_text(
        json.dumps({"name": "svp", "version": "2.2.0"})
    )
    # Create hook scripts in plugin_root/hooks/ (NOT svp/hooks/).
    # Bug S3-145: the real plugin cache layout places hooks at plugin_root
    # /hooks/. The original S3-108 fixture used plugin_root/svp/hooks/ which
    # matched the buggy code path but not reality — corrected here.
    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for script_name in HOOK_SCRIPTS:
        script = hooks_dir / script_name
        script.write_text(f"#!/usr/bin/env bash\n# {script_name}\nexit 0\n")
        script.chmod(0o755)


def _setup_repo_with_hooks(repo_root: Path) -> None:
    """Create minimal repo structure with hook scripts for restore."""
    hooks_dir = repo_root / "svp" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for script_name in HOOK_SCRIPTS:
        script = hooks_dir / script_name
        script.write_text(f"#!/usr/bin/env bash\n# {script_name}\nexit 0\n")
        script.chmod(0o755)
    # Create svp/scripts/ (required by restore --repo auto-discover)
    scripts_dir = repo_root / "svp" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "routing.py").write_text("# routing\n")


class TestCreateNewProjectDeploysHooks:
    """create_new_project must deploy hook scripts to .claude/scripts/."""

    def test_hook_scripts_exist_after_create(self, tmp_path, monkeypatch):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        _setup_plugin_with_hooks(plugin_root)

        # create_new_project builds at Path.cwd() / name — chdir into tmp_path
        # so the leaked project is auto-cleaned by pytest instead of
        # polluting the repo root.
        monkeypatch.chdir(tmp_path)
        project_root = create_new_project("test_hooks", plugin_root)

        scripts_dir = project_root / ".claude" / "scripts"
        assert scripts_dir.is_dir(), ".claude/scripts/ directory must exist"
        for script_name in HOOK_SCRIPTS:
            script = scripts_dir / script_name
            assert script.is_file(), f".claude/scripts/{script_name} must exist"

    def test_hook_scripts_are_executable(self, tmp_path, monkeypatch):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        _setup_plugin_with_hooks(plugin_root)

        monkeypatch.chdir(tmp_path)
        project_root = create_new_project("test_hooks_exec", plugin_root)

        scripts_dir = project_root / ".claude" / "scripts"
        for script_name in HOOK_SCRIPTS:
            script = scripts_dir / script_name
            mode = script.stat().st_mode
            assert mode & 0o100, f"{script_name} must be executable"


class TestRestoreProjectDeploysHooks:
    """restore_project must deploy hook scripts to .claude/scripts/."""

    def test_hook_scripts_exist_after_restore_with_repo(self, tmp_path, monkeypatch):
        # Set up a minimal repo
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _setup_repo_with_hooks(repo_root)
        # Create required docs for auto-discover
        docs = repo_root / "docs"
        docs.mkdir()
        (docs / "stakeholder_spec.md").write_text("# Spec\n")
        (docs / "blueprint_prose.md").write_text("# Prose\n")
        (docs / "blueprint_contracts.md").write_text("# Contracts\n")
        (docs / "project_context.md").write_text("# Context\n")
        (docs / "project_profile.json").write_text("{}\n")

        # restore_project, like create_new_project, creates the project at
        # Path.cwd() / project_name — chdir into tmp_path so the leaked
        # directory is auto-cleaned by pytest.
        monkeypatch.chdir(tmp_path)
        project_root = restore_project(
            "test_restore_hooks",
            spec_path=docs / "stakeholder_spec.md",
            blueprint_dir=docs,
            context_path=docs / "project_context.md",
            scripts_source=repo_root / "svp" / "scripts",
            profile_path=docs / "project_profile.json",
            repo_path=repo_root,
        )

        scripts_dir = project_root / ".claude" / "scripts"
        assert scripts_dir.is_dir(), ".claude/scripts/ directory must exist"
        for script_name in HOOK_SCRIPTS:
            script = scripts_dir / script_name
            assert script.is_file(), f".claude/scripts/{script_name} must exist"
