"""Regression tests for Bugs S3-51 and S3-52: Plugin assembly completeness.

S3-51: Verifies that assemble_plugin_components creates .claude-plugin/
directories with marketplace.json and plugin.json manifests.

S3-52: Verifies that assemble_plugin_components extracts agent, command,
hook, and skill definitions into the delivered repo's svp/ subdirectory.
"""

import json
import tempfile
from pathlib import Path

import pytest

from generate_assembly_map import assemble_plugin_components


@pytest.fixture
def valid_profile():
    """A profile with a proper plugin section."""
    return {
        "plugin": {
            "name": "svp",
            "description": "Test SVP",
            "version": "2.2.0",
            "author": {"name": "Test Author", "email": "test@test.com"},
            "commands": "commands/",
            "agents": "agents/",
            "skills": "skills/",
            "hooks": "hooks/",
        },
        "license": {"author": "Test Author"},
    }


@pytest.fixture
def assembled_repo(valid_profile):
    """Assemble plugin components in a temp directory and return the path."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        assemble_plugin_components(repo, valid_profile)
        yield repo


class TestS3_51_PluginManifestDirectories:
    """Bug S3-51: manifest directories must be created during assembly."""

    def test_root_claude_plugin_dir_exists(self, assembled_repo):
        """Root .claude-plugin/ directory is created."""
        assert (assembled_repo / ".claude-plugin").is_dir()

    def test_marketplace_json_exists(self, assembled_repo):
        """marketplace.json is created at root .claude-plugin/."""
        mp = assembled_repo / ".claude-plugin" / "marketplace.json"
        assert mp.is_file()

    def test_marketplace_json_valid(self, assembled_repo):
        """marketplace.json has valid non-empty required fields."""
        mp = assembled_repo / ".claude-plugin" / "marketplace.json"
        data = json.loads(mp.read_text())
        assert data["name"] == "svp"
        assert "owner" in data
        assert "plugins" in data
        assert len(data["plugins"]) >= 1

    def test_plugin_claude_plugin_dir_exists(self, assembled_repo):
        """svp/.claude-plugin/ directory is created."""
        assert (assembled_repo / "svp" / ".claude-plugin").is_dir()

    def test_plugin_json_exists(self, assembled_repo):
        """plugin.json is created at svp/.claude-plugin/."""
        pj = assembled_repo / "svp" / ".claude-plugin" / "plugin.json"
        assert pj.is_file()

    def test_plugin_json_valid(self, assembled_repo):
        """plugin.json has valid non-empty required fields."""
        pj = assembled_repo / "svp" / ".claude-plugin" / "plugin.json"
        data = json.loads(pj.read_text())
        assert data["name"] == "svp"
        assert data["description"] != ""
        assert data["version"] == "2.2.0"
        assert "author" in data


class TestS3_52_PluginComponentDirectories:
    """Bug S3-52: component directories must be populated during assembly."""

    def test_agents_directory_exists(self, assembled_repo):
        """svp/agents/ directory is created."""
        assert (assembled_repo / "svp" / "agents").is_dir()

    def test_agents_count(self, assembled_repo):
        """svp/agents/ has 21 agent definition files."""
        agents = list((assembled_repo / "svp" / "agents").glob("*.md"))
        assert len(agents) == 21, f"Expected 21 agents, got {len(agents)}: {[a.name for a in agents]}"

    def test_agent_files_non_empty(self, assembled_repo):
        """All agent definition files are non-empty."""
        for md in (assembled_repo / "svp" / "agents").glob("*.md"):
            assert md.stat().st_size > 0, f"{md.name} is empty"

    def test_expected_agents_present(self, assembled_repo):
        """Key agent definition files are present."""
        agents_dir = assembled_repo / "svp" / "agents"
        expected = [
            "setup_agent.md",
            "test_agent.md",
            "implementation_agent.md",
            "diagnostic_agent.md",
            "git_repo_agent.md",
            "oracle_agent.md",
            "bug_triage_agent.md",
            "repair_agent.md",
        ]
        for name in expected:
            assert (agents_dir / name).is_file(), f"Missing agent: {name}"

    def test_commands_directory_exists(self, assembled_repo):
        """svp/commands/ directory is created."""
        assert (assembled_repo / "svp" / "commands").is_dir()

    def test_commands_count(self, assembled_repo):
        """svp/commands/ has 11 command definition files."""
        cmds = list((assembled_repo / "svp" / "commands").glob("*.md"))
        assert len(cmds) == 11, f"Expected 11 commands, got {len(cmds)}: {[c.name for c in cmds]}"

    def test_expected_commands_present(self, assembled_repo):
        """Key command definition files are present."""
        cmds_dir = assembled_repo / "svp" / "commands"
        expected = [
            "svp_save.md",
            "svp_status.md",
            "svp_bug.md",
            "svp_oracle.md",
        ]
        for name in expected:
            assert (cmds_dir / name).is_file(), f"Missing command: {name}"

    def test_hooks_directory_exists(self, assembled_repo):
        """svp/hooks/ directory is created."""
        assert (assembled_repo / "svp" / "hooks").is_dir()

    def test_hooks_json_exists(self, assembled_repo):
        """svp/hooks/hooks.json is created and valid JSON."""
        hj = assembled_repo / "svp" / "hooks" / "hooks.json"
        assert hj.is_file()
        data = json.loads(hj.read_text())
        assert isinstance(data, dict)

    def test_hook_scripts_present(self, assembled_repo):
        """All 4 hook bash scripts are present."""
        hooks_dir = assembled_repo / "svp" / "hooks"
        expected = [
            "write_authorization.sh",
            "non_svp_protection.sh",
            "stub_sentinel_check.sh",
            "monitoring_reminder.sh",
        ]
        for name in expected:
            assert (hooks_dir / name).is_file(), f"Missing hook script: {name}"

    def test_hook_scripts_executable(self, assembled_repo):
        """Hook bash scripts have executable permissions."""
        import stat
        for sh in (assembled_repo / "svp" / "hooks").glob("*.sh"):
            mode = sh.stat().st_mode
            assert mode & stat.S_IXUSR, f"{sh.name} is not executable"

    def test_skills_directory_exists(self, assembled_repo):
        """svp/skills/orchestration/ directory is created."""
        assert (assembled_repo / "svp" / "skills" / "orchestration").is_dir()

    def test_orchestration_skill_exists(self, assembled_repo):
        """svp/skills/orchestration/SKILL.md is created and non-empty."""
        skill = assembled_repo / "svp" / "skills" / "orchestration" / "SKILL.md"
        assert skill.is_file()
        assert skill.stat().st_size > 0
