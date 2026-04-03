"""Plugin completeness tests — verify SVP plugin is well-formed and installable."""
import ast
import json
import subprocess
import sys
from pathlib import Path
import pytest

# Detect context: are we running from workspace or repo?
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Find repos relative to the parent directory
_PARENT = _PROJECT_ROOT.parent
PASS2_REPO = _PARENT / "svp2.2-pass2-repo"
PASS1_REPO = _PARENT / "svp2.2-repo"

# The workspace is wherever scripts/ and .svp/ live
# When running from the repo, WORKSPACE is the repo itself if it has scripts/,
# otherwise look for the sibling workspace
if (_PROJECT_ROOT / "scripts").is_dir():
    WORKSPACE = _PROJECT_ROOT
elif (_PARENT / "svp2.2-pass2" / "scripts").is_dir():
    WORKSPACE = _PARENT / "svp2.2-pass2"
else:
    WORKSPACE = _PROJECT_ROOT  # fallback

REPOS = [r for r in [PASS2_REPO, PASS1_REPO] if r.is_dir()]


class TestEntryPointScripts:
    """Every entry point script must have __name__ guard."""

    ENTRY_SCRIPTS = ["routing.py", "prepare_task.py", "update_state.py", "run_tests.py"]

    @pytest.mark.parametrize("script", ENTRY_SCRIPTS)
    def test_has_name_guard_in_workspace(self, script):
        path = WORKSPACE / "scripts" / script
        if not path.exists():
            pytest.skip(f"Workspace scripts/{script} not found (running from repo?)")
        content = path.read_text()
        assert 'if __name__' in content, f"{script} missing __name__ guard"

    @pytest.mark.parametrize("script", ENTRY_SCRIPTS)
    def test_has_name_guard_in_repos(self, script):
        for repo in REPOS:
            path = repo / "svp" / "scripts" / script
            if path.exists():
                content = path.read_text()
                assert 'if __name__' in content, f"{script} missing __name__ guard in {repo.name}"


class TestRoutingProducesOutput:
    """Routing script must produce JSON when invoked."""

    def test_routing_produces_json(self):
        result = subprocess.run(
            [sys.executable, "scripts/routing.py", "--project-root", "."],
            capture_output=True, text=True, cwd=str(WORKSPACE)
        )
        assert result.stdout.strip(), "routing.py produced no output"
        data = json.loads(result.stdout)
        assert "action_type" in data


class TestPluginManifests:
    """Plugin manifests must be valid and complete."""

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_marketplace_json_exists(self, repo):
        path = repo / ".claude-plugin" / "marketplace.json"
        assert path.is_file()

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_marketplace_json_valid(self, repo):
        path = repo / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text())
        assert data["name"] == "svp"
        assert data["plugins"][0]["source"] == "./svp"
        assert data["plugins"][0]["name"] != ""

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_plugin_json_exists(self, repo):
        path = repo / "svp" / ".claude-plugin" / "plugin.json"
        assert path.is_file()

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_plugin_json_valid(self, repo):
        path = repo / "svp" / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text())
        assert data["name"] == "svp"
        assert data["description"] != ""


class TestPluginComponents:
    """Plugin component directories must be populated."""

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_agents_count(self, repo):
        agents = list((repo / "svp" / "agents").glob("*.md"))
        assert len(agents) == 21

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_agents_have_frontmatter(self, repo):
        for md in (repo / "svp" / "agents").glob("*.md"):
            content = md.read_text()
            assert content.startswith("---"), f"{md.name} missing frontmatter"

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_commands_count(self, repo):
        cmds = list((repo / "svp" / "commands").glob("*.md"))
        assert len(cmds) == 11

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_hooks_json_format(self, repo):
        path = repo / "svp" / "hooks" / "hooks.json"
        data = json.loads(path.read_text())
        for entries in data["hooks"].values():
            for entry in entries:
                assert "hooks" in entry, "Hook entry uses 'handler' instead of 'hooks'"

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_skill_exists(self, repo):
        path = repo / "svp" / "skills" / "orchestration" / "SKILL.md"
        assert path.is_file()
        assert path.read_text().startswith("---")

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_scripts_init_py(self, repo):
        assert (repo / "svp" / "scripts" / "__init__.py").is_file()


class TestPyprojectToml:
    """pyproject.toml must have correct build config."""

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_has_entry_point(self, repo):
        content = (repo / "pyproject.toml").read_text()
        assert "svp.scripts.svp_launcher:main" in content

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_build_backend(self, repo):
        content = (repo / "pyproject.toml").read_text()
        assert "setuptools.build_meta" in content


class TestLauncherImport:
    """Launcher must be importable as installed package."""

    @pytest.mark.parametrize("repo", REPOS, ids=["pass2", "pass1"])
    def test_launcher_importable(self, repo):
        result = subprocess.run(
            [sys.executable, "-c", "from svp.scripts.svp_launcher import main; print('OK')"],
            capture_output=True, text=True, cwd=str(repo)
        )
        assert "OK" in result.stdout, f"Import failed: {result.stderr}"


class TestCommandScriptsAcceptProjectRoot:
    """All cmd scripts must accept --project-root argument."""

    CMD_SCRIPTS = ["cmd_save.py", "cmd_quit.py", "cmd_status.py", "cmd_clean.py"]

    @pytest.mark.parametrize("script", CMD_SCRIPTS)
    def test_accepts_project_root_flag(self, script):
        """Script must accept --project-root without error."""
        result = subprocess.run(
            [sys.executable, f"scripts/{script}", "--project-root", "."],
            capture_output=True, text=True, cwd=str(WORKSPACE),
            timeout=10,
        )
        assert result.returncode == 0, f"{script} failed: {result.stderr}"

    @pytest.mark.parametrize("script", CMD_SCRIPTS)
    def test_has_argparse(self, script):
        """Script must use argparse, not sys.argv positional."""
        path = WORKSPACE / "scripts" / script
        content = path.read_text()
        assert "argparse" in content, f"{script} doesn't use argparse"
        assert "--project-root" in content, f"{script} missing --project-root argument"


class TestWorkspaceReadiness:
    """Working directory must have all files for orchestrator."""

    def test_claude_md_exists(self):
        assert (WORKSPACE / "CLAUDE.md").is_file()

    def test_claude_md_has_routing_instruction(self):
        content = (WORKSPACE / "CLAUDE.md").read_text()
        assert "routing" in content.lower()
        assert "scripts/routing.py" in content

    def test_pipeline_state_in_svp(self):
        assert (WORKSPACE / ".svp" / "pipeline_state.json").is_file()

    def test_no_stale_root_state(self):
        """Root pipeline_state.json should not exist (stale)."""
        assert not (WORKSPACE / "pipeline_state.json").is_file(), \
            "Stale root pipeline_state.json exists — should be in .svp/ only"

    def test_spec_path_resolves(self):
        assert (WORKSPACE / "spec" / "stakeholder_spec.md").is_file()
