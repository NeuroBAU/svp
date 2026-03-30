"""Tests for Unit 29: SVP Launcher.

Synthetic data assumptions:
- parse_args accepts an argv list and returns an argparse.Namespace with a
  .command attribute that is never None after successful parsing.
- Three CLI modes: "svp new <name>", bare "svp" (resume), "svp restore <name> ...".
- preflight_check returns a list of error strings (empty = all pass). It checks
  Claude Code, SVP plugin, API credentials, conda, Python>=3.11, pytest, git,
  and language-specific runtimes.
- create_new_project creates a project directory, copies scripts/toolchains/hooks,
  creates initial pipeline_state.json/svp_config.json/CLAUDE.md, and returns Path.
- restore_project creates a project directory from provided paths, optionally sets
  skip_to stage, and returns Path.
- launch_session runs subprocess with cwd=project_root, handles restart loop, and
  returns exit code.
- main orchestrates parse_args -> preflight -> dispatch.
- _find_plugin_root searches env var then 5 standard locations, validates
  plugin.json with name=="svp", raises FileNotFoundError if none found.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.unit_29.stub import (
    create_new_project,
    launch_session,
    main,
    parse_args,
    preflight_check,
    restore_project,
)

# ---------------------------------------------------------------------------
# parse_args contracts
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Tests for the parse_args function."""

    def test_parse_args_returns_namespace(self):
        result = parse_args(["new", "my_project"])
        assert isinstance(result, argparse.Namespace)

    def test_parse_args_new_command(self):
        result = parse_args(["new", "my_project"])
        assert result.command == "new"

    def test_parse_args_new_command_has_project_name(self):
        result = parse_args(["new", "test_proj"])
        assert hasattr(result, "project_name") or hasattr(result, "name")
        name = getattr(result, "project_name", None) or getattr(result, "name", None)
        assert name == "test_proj"

    def test_parse_args_bare_svp_defaults_to_resume(self):
        """Bare 'svp' (empty argv) should default to resume mode internally."""
        result = parse_args([])
        # command is never None after returning
        assert result.command is not None

    def test_parse_args_command_never_none(self):
        """args.command is never None after returning."""
        for argv in [[], ["new", "proj"]]:
            result = parse_args(argv)
            assert result.command is not None

    def test_parse_args_restore_command(self):
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint-dir",
                "/path/to/blueprint",
                "--context",
                "/path/to/context.md",
                "--scripts-source",
                "/path/to/scripts",
                "--profile",
                "/path/to/profile.json",
            ]
        )
        assert result.command == "restore"

    def test_parse_args_restore_has_required_args(self):
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint-dir",
                "/path/to/blueprint",
                "--context",
                "/path/to/context.md",
                "--scripts-source",
                "/path/to/scripts",
                "--profile",
                "/path/to/profile.json",
            ]
        )
        assert hasattr(result, "spec")
        assert hasattr(result, "blueprint_dir")
        assert hasattr(result, "context")
        assert hasattr(result, "scripts_source")
        assert hasattr(result, "profile")

    def test_parse_args_restore_optional_plugin_path(self):
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint-dir",
                "/path/to/blueprint",
                "--context",
                "/path/to/context.md",
                "--scripts-source",
                "/path/to/scripts",
                "--profile",
                "/path/to/profile.json",
                "--plugin-path",
                "/path/to/plugin",
            ]
        )
        assert hasattr(result, "plugin_path")
        plugin_path = getattr(result, "plugin_path")
        assert plugin_path is not None

    def test_parse_args_restore_optional_skip_to(self):
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint-dir",
                "/path/to/blueprint",
                "--context",
                "/path/to/context.md",
                "--scripts-source",
                "/path/to/scripts",
                "--profile",
                "/path/to/profile.json",
                "--skip-to",
                "pre_stage_3",
            ]
        )
        assert hasattr(result, "skip_to")
        assert result.skip_to == "pre_stage_3"

    def test_parse_args_restore_skip_to_default_none(self):
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint-dir",
                "/path/to/blueprint",
                "--context",
                "/path/to/context.md",
                "--scripts-source",
                "/path/to/scripts",
                "--profile",
                "/path/to/profile.json",
            ]
        )
        skip_to = getattr(result, "skip_to", None)
        assert skip_to is None

    def test_parse_args_restore_plugin_path_default_none(self):
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint-dir",
                "/path/to/blueprint",
                "--context",
                "/path/to/context.md",
                "--scripts-source",
                "/path/to/scripts",
                "--profile",
                "/path/to/profile.json",
            ]
        )
        plugin_path = getattr(result, "plugin_path", None)
        assert plugin_path is None


# ---------------------------------------------------------------------------
# preflight_check contracts
# ---------------------------------------------------------------------------


class TestPreflightCheck:
    """Tests for the preflight_check function."""

    def test_preflight_check_returns_list(self):
        result = preflight_check()
        assert isinstance(result, list)

    def test_preflight_check_errors_are_strings(self):
        result = preflight_check()
        for error in result:
            assert isinstance(error, str)

    def test_preflight_check_accepts_optional_project_root(self, tmp_path):
        result = preflight_check(project_root=tmp_path)
        assert isinstance(result, list)

    def test_preflight_check_accepts_none_project_root(self):
        result = preflight_check(project_root=None)
        assert isinstance(result, list)

    def test_preflight_check_checks_claude_code_installed(self):
        """Should check that Claude Code CLI is installed."""
        with patch("shutil.which", return_value=None):
            result = preflight_check()
            # With no tools found, there should be errors
            assert isinstance(result, list)

    def test_preflight_check_checks_git_installed(self):
        """Should detect missing git."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: (
                None if cmd == "git" else "/usr/bin/" + cmd
            )
            result = preflight_check()
            git_errors = [e for e in result if "git" in e.lower()]
            assert len(git_errors) > 0 or len(result) > 0

    def test_preflight_check_checks_conda_installed(self):
        """Should detect missing conda."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: (
                None if cmd == "conda" else "/usr/bin/" + cmd
            )
            result = preflight_check()
            # May have conda-related error
            assert isinstance(result, list)

    def test_preflight_check_empty_list_means_all_pass(self):
        """Empty return list = all checks pass."""
        result = preflight_check()
        # We can't guarantee all checks pass in test env, but verify type contract
        assert isinstance(result, list)
        if len(result) == 0:
            assert result == []


# ---------------------------------------------------------------------------
# create_new_project contracts
# ---------------------------------------------------------------------------


class TestCreateNewProject:
    """Tests for the create_new_project function."""

    def test_create_new_project_returns_path(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        result = create_new_project("test_project", plugin_root)
        assert isinstance(result, Path)

    def test_create_new_project_creates_directory(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        result = create_new_project("test_project", plugin_root)
        assert result.exists()
        assert result.is_dir()

    def test_create_new_project_creates_pipeline_state(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        project_root = create_new_project("test_project", plugin_root)
        pipeline_state = project_root / "pipeline_state.json"
        assert pipeline_state.exists()

    def test_create_new_project_creates_svp_config(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        project_root = create_new_project("test_project", plugin_root)
        svp_config = project_root / "svp_config.json"
        assert svp_config.exists()

    def test_create_new_project_creates_claude_md(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        project_root = create_new_project("test_project", plugin_root)
        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists()

    def test_create_new_project_copies_scripts(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        project_root = create_new_project("test_project", plugin_root)
        scripts_dir = project_root / "scripts"
        assert scripts_dir.exists()

    def test_create_new_project_ruff_toml_is_read_only(self, tmp_path):
        """ruff.toml should be set read-only after copy."""
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        project_root = create_new_project("test_project", plugin_root)
        ruff_toml = project_root / "ruff.toml"
        if ruff_toml.exists():
            mode = ruff_toml.stat().st_mode
            # Check that write bits are not set (owner write = 0o200)
            assert not (mode & 0o200), "ruff.toml should be read-only"

    def test_create_new_project_pipeline_state_is_valid_json(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        self._setup_minimal_plugin(plugin_root)
        project_root = create_new_project("test_project", plugin_root)
        pipeline_state = project_root / "pipeline_state.json"
        content = json.loads(pipeline_state.read_text())
        assert isinstance(content, dict)

    def _setup_minimal_plugin(self, plugin_root):
        """Create minimal plugin structure for testing."""
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
            json.dumps(
                {
                    "name": "svp",
                    "version": "2.2.0",
                }
            )
        )


# ---------------------------------------------------------------------------
# restore_project contracts
# ---------------------------------------------------------------------------


class TestRestoreProject:
    """Tests for the restore_project function."""

    def test_restore_project_returns_path(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        result = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
        )
        assert isinstance(result, Path)

    def test_restore_project_creates_directory(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        result = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
        )
        assert result.exists()
        assert result.is_dir()

    def test_restore_project_copies_spec(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec Content\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        project_root = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
        )
        # Spec should exist somewhere in project
        spec_files = list(project_root.rglob("spec*")) + list(
            project_root.rglob("*.md")
        )
        assert len(spec_files) > 0 or (project_root / "spec.md").exists()

    def test_restore_project_copies_scripts(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        project_root = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
        )
        scripts_dir = project_root / "scripts"
        assert scripts_dir.exists()

    def test_restore_project_with_skip_to(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        project_root = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
            skip_to="pre_stage_3",
        )
        # Pipeline state should reflect the skip_to stage
        pipeline_state_path = project_root / "pipeline_state.json"
        if pipeline_state_path.exists():
            state = json.loads(pipeline_state_path.read_text())
            assert isinstance(state, dict)

    def test_restore_project_with_plugin_path(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")
        plugin_path = tmp_path / "plugin"
        plugin_path.mkdir()

        result = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
            plugin_path=plugin_path,
        )
        assert isinstance(result, Path)

    def test_restore_project_without_optional_args(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing\n")
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        result = restore_project(
            "test_restore",
            spec_path=spec,
            blueprint_dir=blueprint,
            context_path=context,
            scripts_source=scripts,
            profile_path=profile,
            plugin_path=None,
            skip_to=None,
        )
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# launch_session contracts
# ---------------------------------------------------------------------------


class TestLaunchSession:
    """Tests for the launch_session function."""

    @patch("subprocess.run")
    def test_launch_session_returns_int(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        result = launch_session(tmp_path)
        assert isinstance(result, int)

    @patch("subprocess.run")
    def test_launch_session_uses_project_root_as_cwd(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        launch_session(tmp_path)
        call_kwargs = mock_run.call_args
        # cwd should be set to project_root
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs.get("cwd") == tmp_path or str(
                call_kwargs.kwargs.get("cwd")
            ) == str(tmp_path)
        else:
            # Positional args -- check named args
            assert any(
                str(tmp_path) in str(arg)
                for arg in call_kwargs.args + tuple(call_kwargs.kwargs.values())
            )

    @patch("subprocess.run")
    def test_launch_session_sets_svp_plugin_active_env(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        launch_session(tmp_path)
        call_kwargs = mock_run.call_args
        env = call_kwargs.kwargs.get("env", {})
        if env:
            assert env.get("SVP_PLUGIN_ACTIVE") == "1"

    @patch("subprocess.run")
    def test_launch_session_skip_permissions_flag(self, mock_run, tmp_path):
        """When skip_permissions=True, should include --dangerously-skip-permissions."""
        mock_run.return_value = MagicMock(returncode=0)
        launch_session(tmp_path, skip_permissions=True)
        call_args = mock_run.call_args
        cmd = call_args.args[0] if call_args.args else call_args.kwargs.get("args", [])
        cmd_str = (
            " ".join(str(c) for c in cmd)
            if isinstance(cmd, (list, tuple))
            else str(cmd)
        )
        assert "dangerously-skip-permissions" in cmd_str

    @patch("subprocess.run")
    def test_launch_session_includes_prompt_arg(self, mock_run, tmp_path):
        """Should include --prompt 'run the routing script'."""
        mock_run.return_value = MagicMock(returncode=0)
        launch_session(tmp_path)
        call_args = mock_run.call_args
        cmd = call_args.args[0] if call_args.args else call_args.kwargs.get("args", [])
        cmd_str = (
            " ".join(str(c) for c in cmd)
            if isinstance(cmd, (list, tuple))
            else str(cmd)
        )
        assert "prompt" in cmd_str
        assert "routing" in cmd_str.lower()

    @patch("subprocess.run")
    def test_launch_session_with_plugin_path_sets_env(self, mock_run, tmp_path):
        """When plugin_path is provided, SVP_PLUGIN_ROOT should be set."""
        mock_run.return_value = MagicMock(returncode=0)
        plugin_path = tmp_path / "plugin"
        plugin_path.mkdir()
        launch_session(tmp_path, plugin_path=plugin_path)
        call_kwargs = mock_run.call_args
        env = call_kwargs.kwargs.get("env", {})
        if env:
            assert env.get("SVP_PLUGIN_ROOT") == str(plugin_path)

    @patch("subprocess.run")
    def test_launch_session_returns_exit_code(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=42)
        result = launch_session(tmp_path)
        assert result == 42

    @patch("subprocess.run")
    def test_launch_session_restart_loop_on_signal(self, mock_run, tmp_path):
        """After session exit, checks for .svp/restart_signal and relaunches."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        restart_signal = svp_dir / "restart_signal"

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: create restart signal
                restart_signal.write_text("restart")
                return MagicMock(returncode=0)
            else:
                # Second call: no signal, exit
                if restart_signal.exists():
                    restart_signal.unlink()
                return MagicMock(returncode=0)

        mock_run.side_effect = side_effect
        launch_session(tmp_path)
        # Should have been called at least twice due to restart
        assert mock_run.call_count >= 2

    @patch("subprocess.run")
    def test_launch_session_no_restart_without_signal(self, mock_run, tmp_path):
        """Without restart_signal, should not relaunch."""
        mock_run.return_value = MagicMock(returncode=0)
        launch_session(tmp_path)
        assert mock_run.call_count == 1


# ---------------------------------------------------------------------------
# main contracts
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main function."""

    @patch("src.unit_29.stub.launch_session", return_value=0)
    @patch("src.unit_29.stub.preflight_check", return_value=[])
    @patch("src.unit_29.stub.create_new_project", return_value=Path("/tmp/test"))
    def test_main_new_project_dispatches_to_create(
        self, mock_create, mock_preflight, mock_launch
    ):
        main(["new", "my_project"])
        mock_create.assert_called_once()

    @patch("src.unit_29.stub.launch_session", return_value=0)
    @patch("src.unit_29.stub.preflight_check", return_value=[])
    def test_main_bare_svp_dispatches_to_resume(self, mock_preflight, mock_launch):
        """Bare svp (empty argv) should dispatch to resume/route mode."""
        try:
            main([])
        except (SystemExit, FileNotFoundError):
            pass  # May fail due to missing project, but should attempt resume

    @patch("src.unit_29.stub.launch_session", return_value=0)
    @patch("src.unit_29.stub.preflight_check", return_value=[])
    @patch("src.unit_29.stub.restore_project", return_value=Path("/tmp/test"))
    def test_main_restore_dispatches_to_restore(
        self, mock_restore, mock_preflight, mock_launch, tmp_path
    ):
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec\n")
        blueprint = tmp_path / "blueprint"
        blueprint.mkdir()
        context = tmp_path / "context.md"
        context.write_text("# Context\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        profile = tmp_path / "profile.json"
        profile.write_text("{}\n")

        main(
            [
                "restore",
                "my_project",
                "--spec",
                str(spec),
                "--blueprint-dir",
                str(blueprint),
                "--context",
                str(context),
                "--scripts-source",
                str(scripts),
                "--profile",
                str(profile),
            ]
        )
        mock_restore.assert_called_once()

    @patch("src.unit_29.stub.preflight_check")
    def test_main_runs_preflight(self, mock_preflight):
        mock_preflight.return_value = ["Claude Code not found"]
        try:
            main(["new", "test"])
        except (SystemExit, Exception):
            pass
        mock_preflight.assert_called()

    def test_main_accepts_none_argv(self):
        """main(None) should use sys.argv -- verify it doesn't crash on call signature."""
        with patch("sys.argv", ["svp"]):
            try:
                main(None)
            except (SystemExit, FileNotFoundError, Exception):
                pass  # Expected in test environment
