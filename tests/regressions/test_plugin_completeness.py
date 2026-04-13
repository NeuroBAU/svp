"""Plugin completeness tests — verify SVP plugin is well-formed and installable."""
import ast
import json
import subprocess
import sys
from pathlib import Path
import pytest

# Detect context: are we running from workspace or repo?
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Find repo relative to the parent directory
_PARENT = _PROJECT_ROOT.parent
PASS2_REPO = _PARENT / "svp2.2-pass2-repo"

# The workspace is wherever scripts/ and .svp/ live
# When running from the repo, WORKSPACE is the repo itself if it has scripts/,
# otherwise look for the sibling workspace
if (_PROJECT_ROOT / "scripts").is_dir():
    WORKSPACE = _PROJECT_ROOT
elif (_PARENT / "svp2.2-pass2" / "scripts").is_dir():
    WORKSPACE = _PARENT / "svp2.2-pass2"
else:
    WORKSPACE = _PROJECT_ROOT  # fallback

# Pass 1 repo was retired on 2026-04-13. REPOS is a list for historical
# compatibility with parametrized tests; it now contains only Pass 2.
REPOS = [PASS2_REPO] if PASS2_REPO.is_dir() else []
REPO_IDS = [r.name for r in REPOS]


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

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_marketplace_json_exists(self, repo):
        path = repo / ".claude-plugin" / "marketplace.json"
        assert path.is_file()

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_marketplace_json_valid(self, repo):
        path = repo / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text())
        assert data["name"] == "svp"
        assert data["plugins"][0]["source"] == "./svp"
        assert data["plugins"][0]["name"] != ""

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_plugin_json_exists(self, repo):
        path = repo / "svp" / ".claude-plugin" / "plugin.json"
        assert path.is_file()

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_plugin_json_valid(self, repo):
        path = repo / "svp" / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text())
        assert data["name"] == "svp"
        assert data["description"] != ""


class TestPluginComponents:
    """Plugin component directories must be populated."""

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_agents_count(self, repo):
        agents = list((repo / "svp" / "agents").glob("*.md"))
        assert len(agents) == 21

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_agents_have_frontmatter(self, repo):
        for md in (repo / "svp" / "agents").glob("*.md"):
            content = md.read_text()
            assert content.startswith("---"), f"{md.name} missing frontmatter"

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_commands_count(self, repo):
        cmds = list((repo / "svp" / "commands").glob("*.md"))
        assert len(cmds) == 11

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_hooks_json_format(self, repo):
        path = repo / "svp" / "hooks" / "hooks.json"
        data = json.loads(path.read_text())
        for entries in data["hooks"].values():
            for entry in entries:
                assert "hooks" in entry, "Hook entry uses 'handler' instead of 'hooks'"

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_skill_exists(self, repo):
        path = repo / "svp" / "skills" / "orchestration" / "SKILL.md"
        assert path.is_file()
        assert path.read_text().startswith("---")

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_scripts_init_py(self, repo):
        assert (repo / "svp" / "scripts" / "__init__.py").is_file()


class TestPyprojectToml:
    """pyproject.toml must have correct build config."""

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_has_entry_point(self, repo):
        content = (repo / "pyproject.toml").read_text()
        assert "svp.scripts.svp_launcher:main" in content

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_build_backend(self, repo):
        content = (repo / "pyproject.toml").read_text()
        assert "setuptools.build_meta" in content


class TestDeliveredPyprojectGenerator:
    """Bug S3-109 regression: the generator for delivered Python projects'
    pyproject.toml MUST emit a real PEP 517 build backend. An earlier bug
    hardcoded `setuptools.backends._legacy:_Backend` — a module that does not
    exist — and broke `pip install -e .` in every delivered repo. This class
    tests the GENERATOR directly, not a hand-authored fixture."""

    @staticmethod
    def _minimal_profile():
        return {"name": "bug_s3_109_fixture", "delivery": {"python": {"source_layout": "conventional"}}}

    @staticmethod
    def _parse_pyproject(repo_dir):
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore
        return tomllib.loads((repo_dir / "pyproject.toml").read_text())

    def test_unit_23_stub_generator_emits_build_meta(self, tmp_path):
        import importlib.util
        stub_path = WORKSPACE / "src" / "unit_23" / "stub.py"
        if not stub_path.is_file():
            pytest.skip("src/unit_23/stub.py not present (running from delivered repo?)")
        spec = importlib.util.spec_from_file_location("unit_23_stub", stub_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        project_root = tmp_path / "bug_s3_109_fixture"
        project_root.mkdir()
        repo_dir = mod.assemble_python_project(project_root, self._minimal_profile(), {})
        data = self._parse_pyproject(repo_dir)
        assert data["build-system"]["build-backend"] == "setuptools.build_meta"

    def test_generate_assembly_map_generator_emits_build_meta(self, tmp_path):
        import importlib
        sys.path.insert(0, str(WORKSPACE / "scripts"))
        try:
            mod = importlib.import_module("generate_assembly_map")
            importlib.reload(mod)
        finally:
            sys.path.pop(0)

        project_root = tmp_path / "bug_s3_109_fixture"
        project_root.mkdir()
        repo_dir = mod.assemble_python_project(project_root, self._minimal_profile(), {})
        data = self._parse_pyproject(repo_dir)
        assert data["build-system"]["build-backend"] == "setuptools.build_meta"

    # (Bug S3-110) test_adapt_regression_tests_generator_emits_build_meta was
    # removed when scripts/adapt_regression_tests.py was deleted. Its role is
    # now covered by TestAdaptRegressionTestsOrphanRemoved below, plus the
    # two remaining generator tests in this class which exercise the single
    # source of truth via unit_23.stub and the derived generate_assembly_map.

    def test_build_meta_backend_is_importable(self):
        """The declared backend string must resolve to a real module."""
        result = subprocess.run(
            [sys.executable, "-c", "import setuptools.build_meta; print('OK')"],
            capture_output=True, text=True,
        )
        assert "OK" in result.stdout, (
            f"setuptools.build_meta is not importable: {result.stderr}"
        )

    def test_no_fictional_setuptools_backends_in_source_tree(self):
        """Walk source directories and ensure no code file references the
        fictional `setuptools.backends` module. Allowed: historical mentions
        in specs and lessons-learned docs (which document this fix), and
        this test file itself (which contains the bad string as a literal
        search target)."""
        bad = "setuptools.backends"
        # Only search source/script directories. Do NOT search tests/ —
        # this test file contains `bad` as a literal search target, and
        # self-skip-by-path is fragile across workspace/repo layouts.
        search_dirs = [
            WORKSPACE / "src",
            WORKSPACE / "scripts",
            WORKSPACE / "svp",
        ]
        offenders = []
        for d in search_dirs:
            if not d.exists():
                continue
            for path in d.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix not in (".py", ".md", ".json", ".toml", ".sh"):
                    continue
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if bad in content:
                    offenders.append(str(path.relative_to(WORKSPACE)))
        assert not offenders, (
            f"Fictional '{bad}' module referenced in: {offenders}. "
            "The correct PEP 517 backend is 'setuptools.build_meta'."
        )


class TestAdaptRegressionTestsOrphanRemoved:
    """Bug S3-110 regression: scripts/adapt_regression_tests.py was an
    orphaned stale duplicate of Unit 23 code. It is now DELETED and its
    functionality is exposed via the `regression-adapt` subcommand of
    scripts/generate_assembly_map.py. These tests prevent the orphan from
    being silently reintroduced."""

    def test_orphan_not_in_workspace_scripts(self):
        assert not (WORKSPACE / "scripts" / "adapt_regression_tests.py").exists(), (
            "scripts/adapt_regression_tests.py must not exist (deleted in Bug S3-110)"
        )

    def test_orphan_not_in_workspace_src_unit_23(self):
        assert not (WORKSPACE / "src" / "unit_23" / "adapt_regression_tests.py").exists()

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_orphan_not_in_deployed_svp_scripts(self, repo):
        assert not (repo / "svp" / "scripts" / "adapt_regression_tests.py").exists(), (
            f"{repo.name}/svp/scripts/adapt_regression_tests.py must not exist "
            "(deleted in Bug S3-110)"
        )

    def test_unit_11_invokes_generate_assembly_map_for_regression_adapt(self):
        """Unit 11 subprocess path must point at generate_assembly_map.py,
        not the deleted adapt_regression_tests.py. Only checks for LIVE
        code references (string literals in Path construction) — historical
        comments are allowed."""
        unit_11_stub = WORKSPACE / "src" / "unit_11" / "stub.py"
        if not unit_11_stub.is_file():
            pytest.skip("src/unit_11/stub.py not present (running from delivered repo?)")
        content = unit_11_stub.read_text()
        # A live reference is a string literal used in a Path join.
        assert '"adapt_regression_tests.py"' not in content, (
            "Unit 11 must not reference the deleted adapt_regression_tests.py "
            "as a string literal (Bug S3-110)"
        )
        assert "'adapt_regression_tests.py'" not in content
        assert '"regression-adapt"' in content or "'regression-adapt'" in content, (
            "Unit 11 must invoke the regression-adapt subcommand of generate_assembly_map.py"
        )
        assert '"generate_assembly_map.py"' in content, (
            "Unit 11 must reference generate_assembly_map.py as the subprocess target"
        )


class TestGenerateAssemblyMapCLI:
    """Bug S3-110: generate_assembly_map.py must expose a working CLI with a
    regression-adapt subcommand that rewrites test imports end-to-end."""

    @staticmethod
    def _cli_path():
        return WORKSPACE / "scripts" / "generate_assembly_map.py"

    def test_cli_help_exits_clean(self):
        cli = self._cli_path()
        if not cli.is_file():
            pytest.skip("scripts/generate_assembly_map.py not present")
        result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "regression-adapt" in result.stdout

    def test_cli_regression_adapt_help_exits_clean(self):
        cli = self._cli_path()
        if not cli.is_file():
            pytest.skip("scripts/generate_assembly_map.py not present")
        result = subprocess.run(
            [sys.executable, str(cli), "regression-adapt", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--target" in result.stdout
        assert "--map" in result.stdout

    def test_cli_regression_adapt_rewrites_imports_end_to_end(self, tmp_path):
        """The most important test: actually run the subcommand and verify
        it rewrites imports in a target file. This is what Unit 11 relies on."""
        cli = self._cli_path()
        if not cli.is_file():
            pytest.skip("scripts/generate_assembly_map.py not present")

        target_dir = tmp_path / "tests_dir"
        target_dir.mkdir()
        test_file = target_dir / "test_example.py"
        test_file.write_text(
            "from old_module import stuff\n"
            "import another_old\n"
        )
        map_file = tmp_path / "map.json"
        map_file.write_text(
            '{"old_module": "new_module", "another_old": "another_new"}'
        )

        result = subprocess.run(
            [
                sys.executable, str(cli), "regression-adapt",
                "--target", str(target_dir),
                "--map", str(map_file),
            ],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"regression-adapt exited {result.returncode}: {result.stderr}"
        )

        rewritten = test_file.read_text()
        assert "from new_module import stuff" in rewritten
        assert "import another_new" in rewritten
        assert "old_module" not in rewritten
        assert "another_old" not in rewritten

    def test_cli_regression_adapt_missing_args_errors(self):
        cli = self._cli_path()
        if not cli.is_file():
            pytest.skip("scripts/generate_assembly_map.py not present")
        result = subprocess.run(
            [sys.executable, str(cli), "regression-adapt"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "required" in result.stdout.lower()


class TestAssemblyMapFreshness:
    """Bug S3-111 regression: the committed .svp/assembly_map.json must have
    the post-S3-111 flat schema AND every value must point at a source stub
    that actually exists on disk. This catches the stale-path class of bug
    that went undetected for ~5 months."""

    @staticmethod
    def _load_map():
        map_path = WORKSPACE / ".svp" / "assembly_map.json"
        if not map_path.is_file():
            pytest.skip("No .svp/assembly_map.json in workspace")
        return json.loads(map_path.read_text())

    def test_only_repo_to_workspace_top_level_key(self):
        data = self._load_map()
        assert list(data.keys()) == ["repo_to_workspace"], (
            f"assembly_map.json must have only 'repo_to_workspace' at top level; "
            f"got {list(data.keys())}. Bug S3-111 removed workspace_to_repo."
        )

    def test_no_workspace_to_repo_key(self):
        data = self._load_map()
        assert "workspace_to_repo" not in data, (
            "Legacy workspace_to_repo key must NOT exist in assembly_map.json "
            "after Bug S3-111. Has the generator reverted?"
        )

    def test_every_value_is_an_existing_stub_file(self):
        """THE staleness-prevention test. Every source value in the map
        must be a file that exists on disk. Pre-S3-111, all 70 values
        pointed at non-existent files and no test caught it."""
        import re as _re
        data = self._load_map()
        stub_re = _re.compile(r"^src/unit_\d+/stub\.py$")
        offenders_shape = []
        offenders_missing = []
        for key, value in data["repo_to_workspace"].items():
            if not stub_re.match(value):
                offenders_shape.append((key, value))
                continue
            abs_path = WORKSPACE / value
            if not abs_path.exists():
                offenders_missing.append((key, value))
        assert not offenders_shape, (
            f"Values not matching ^src/unit_\\d+/stub\\.py$: {offenders_shape[:5]} "
            f"(total {len(offenders_shape)}). Bug S3-111."
        )
        assert not offenders_missing, (
            f"Values pointing at non-existent files: {offenders_missing[:5]} "
            f"(total {len(offenders_missing)}). This is the stale-path bug S3-111."
        )

    def test_map_is_non_empty(self):
        data = self._load_map()
        assert len(data["repo_to_workspace"]) > 0, (
            "Assembly map is empty — regeneration failure?"
        )


class TestLauncherImport:
    """Launcher must be importable as installed package."""

    @pytest.mark.parametrize("repo", REPOS, ids=REPO_IDS)
    def test_launcher_importable(self, repo):
        result = subprocess.run(
            [sys.executable, "-c", "from svp.scripts.svp_launcher import main; print('OK')"],
            capture_output=True, text=True, cwd=str(repo)
        )
        assert "OK" in result.stdout, f"Import failed: {result.stderr}"


class TestCommandScriptsAcceptProjectRoot:
    """All cmd scripts must accept --project-root argument."""

    # cmd_save.py is a re-export wrapper (Bug S3-98), not a CLI entry point
    CMD_SCRIPTS = ["cmd_quit.py", "cmd_status.py", "cmd_clean.py"]

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
        assert (WORKSPACE / "specs" / "stakeholder_spec.md").is_file()
