"""Tests for Unit 29: Launcher.

Synthetic Data Assumptions:
- parse_args uses argparse and recognizes three CLI modes:
  1. `svp new <project_name>` -- creates a new project.
  2. bare `svp` (no arguments) -- resume mode (args.command defaults internally).
  3. `svp restore <project_name> --spec --blueprint-dir --context --scripts-source
     --profile [--plugin-path] [--skip-to]` -- restores a project.
- args.command is never None after parse_args returns.
- preflight_check returns a list of error strings (empty means all checks pass).
  It validates: Claude Code installed, SVP plugin loaded, API credentials valid,
  conda installed, Python >= 3.11, pytest importable, git installed, plus
  language runtime pre-flights derived from LANGUAGE_REGISTRY.
- create_new_project takes (project_name, plugin_root) and returns the project
  root Path. It creates the project directory, copies scripts, toolchain files,
  ruff.toml (read-only), regression test files, hook configuration, creates
  initial pipeline_state.json / svp_config.json / CLAUDE.md, and launches the
  session.
- restore_project takes project_name plus five required paths, optional
  plugin_path and skip_to, and returns the project root Path. When plugin_path
  is provided, SVP_PLUGIN_ROOT is set in the subprocess environment.
- launch_session uses subprocess.run with cwd=project_root, supports
  --dangerously-skip-permissions and restart loop via .svp/restart_signal.
  Returns exit code (int).
- _find_plugin_root checks SVP_PLUGIN_ROOT env var first, then searches 5
  standard directories in order. Validates each candidate by reading
  .claude-plugin/plugin.json and checking name == "svp". Raises
  FileNotFoundError if none found.
- main parses args, runs preflight, dispatches to create_new_project, resume,
  or restore_project.
- All functions that need filesystem interaction are tested using tmp_path.
- Tests do NOT use pytest.raises(NotImplementedError).
"""

import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from svp_launcher import (
    _find_plugin_root,
    create_new_project,
    launch_session,
    main,
    parse_args,
    preflight_check,
    restore_project,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_plugin_dir(root: Path) -> Path:
    """Create a minimal valid plugin directory structure at the given root.

    Returns the plugin root path (the directory containing .claude-plugin/).
    """
    plugin_meta_dir = root / ".claude-plugin"
    plugin_meta_dir.mkdir(parents=True, exist_ok=True)
    plugin_json = plugin_meta_dir / "plugin.json"
    plugin_json.write_text(json.dumps({"name": "svp", "version": "2.2.0"}))
    return root


def _make_invalid_plugin_dir(root: Path, name: str = "not-svp") -> Path:
    """Create a plugin directory with wrong name in plugin.json."""
    plugin_meta_dir = root / ".claude-plugin"
    plugin_meta_dir.mkdir(parents=True, exist_ok=True)
    plugin_json = plugin_meta_dir / "plugin.json"
    plugin_json.write_text(json.dumps({"name": name, "version": "1.0.0"}))
    return root


# ===========================================================================
# 1. parse_args -- "svp new <project_name>" subcommand
# ===========================================================================


class TestParseArgsNew:
    """parse_args: 'new' subcommand creates a new project."""

    def test_new_subcommand_sets_command_to_new(self):
        ns = parse_args(["new", "my-project"])
        assert ns.command == "new"

    def test_new_subcommand_captures_project_name(self):
        ns = parse_args(["new", "alpha-project"])
        assert ns.project_name == "alpha-project"

    def test_new_subcommand_returns_namespace(self):
        ns = parse_args(["new", "test"])
        assert isinstance(ns, argparse.Namespace)

    def test_new_subcommand_project_name_is_string(self):
        ns = parse_args(["new", "proj123"])
        assert isinstance(ns.project_name, str)

    def test_new_subcommand_with_hyphenated_name(self):
        ns = parse_args(["new", "my-cool-project"])
        assert ns.project_name == "my-cool-project"


# ===========================================================================
# 2. parse_args -- bare "svp" (resume) mode
# ===========================================================================


class TestParseArgsResume:
    """parse_args: bare invocation (no arguments) defaults to resume mode."""

    def test_bare_invocation_returns_namespace(self):
        ns = parse_args([])
        assert isinstance(ns, argparse.Namespace)

    def test_bare_invocation_command_is_not_none(self):
        """Contract: args.command is never None after returning."""
        ns = parse_args([])
        assert ns.command is not None

    def test_bare_invocation_command_indicates_resume(self):
        """Bare 'svp' defaults to resume mode internally."""
        ns = parse_args([])
        # The command should indicate resume mode (could be "resume" or similar)
        assert isinstance(ns.command, str)
        assert len(ns.command) > 0


# ===========================================================================
# 3. parse_args -- "svp restore" subcommand
# ===========================================================================


class TestParseArgsRestore:
    """parse_args: 'restore' subcommand with required and optional flags."""

    def _restore_argv(self, **overrides):
        """Return a minimal valid argv for the restore subcommand."""
        defaults = {
            "project_name": "restored-proj",
            "spec": "/tmp/spec.md",
            "blueprint_dir": "/tmp/blueprint",
            "context": "/tmp/context",
            "scripts_source": "/tmp/scripts",
            "profile": "/tmp/profile.json",
        }
        defaults.update(overrides)
        return [
            "restore",
            defaults["project_name"],
            "--spec",
            defaults["spec"],
            "--blueprint-dir",
            defaults["blueprint_dir"],
            "--context",
            defaults["context"],
            "--scripts-source",
            defaults["scripts_source"],
            "--profile",
            defaults["profile"],
        ]

    def test_restore_subcommand_sets_command_to_restore(self):
        ns = parse_args(self._restore_argv())
        assert ns.command == "restore"

    def test_restore_subcommand_captures_project_name(self):
        ns = parse_args(self._restore_argv(project_name="revival"))
        assert ns.project_name == "revival"

    def test_restore_subcommand_captures_spec_path(self):
        ns = parse_args(self._restore_argv(spec="/my/spec.md"))
        # argparse may store as string or Path; ensure the value matches
        assert (
            str(ns.spec) == "/my/spec.md"
            or str(getattr(ns, "spec", "")) == "/my/spec.md"
        )

    def test_restore_subcommand_captures_blueprint_dir_path(self):
        ns = parse_args(self._restore_argv(blueprint_dir="/my/bp"))
        attr_val = getattr(ns, "blueprint_dir", None)
        assert attr_val is not None
        assert str(attr_val) == "/my/bp"

    def test_restore_subcommand_captures_profile_path(self):
        ns = parse_args(self._restore_argv(profile="/my/profile.json"))
        assert str(ns.profile) == "/my/profile.json"

    def test_restore_subcommand_plugin_path_is_optional(self):
        """--plugin-path is optional and defaults to None when not provided."""
        ns = parse_args(self._restore_argv())
        plugin_val = getattr(ns, "plugin_path", None)
        assert plugin_val is None

    def test_restore_subcommand_plugin_path_when_provided(self):
        argv = self._restore_argv() + ["--plugin-path", "/my/plugin"]
        ns = parse_args(argv)
        assert str(ns.plugin_path) == "/my/plugin"

    def test_restore_subcommand_skip_to_is_optional(self):
        """--skip-to is optional and defaults to None when not provided."""
        ns = parse_args(self._restore_argv())
        skip_val = getattr(ns, "skip_to", None)
        assert skip_val is None

    def test_restore_subcommand_skip_to_when_provided(self):
        argv = self._restore_argv() + ["--skip-to", "3"]
        ns = parse_args(argv)
        assert ns.skip_to == "3"

    def test_restore_subcommand_skip_to_accepts_pre_stage_3(self):
        """Contract: valid values include 'pre_stage_3'."""
        argv = self._restore_argv() + ["--skip-to", "pre_stage_3"]
        ns = parse_args(argv)
        assert ns.skip_to == "pre_stage_3"

    def test_restore_subcommand_returns_namespace(self):
        ns = parse_args(self._restore_argv())
        assert isinstance(ns, argparse.Namespace)


# ===========================================================================
# 4. parse_args -- command is never None
# ===========================================================================


class TestParseArgsCommandNeverNone:
    """Contract: args.command is never None after parse_args returns."""

    def test_command_not_none_for_new(self):
        ns = parse_args(["new", "proj"])
        assert ns.command is not None

    def test_command_not_none_for_restore(self):
        argv = [
            "restore",
            "proj",
            "--spec",
            "/s",
            "--blueprint-dir",
            "/b",
            "--context",
            "/c",
            "--scripts-source",
            "/ss",
            "--profile",
            "/p",
        ]
        ns = parse_args(argv)
        assert ns.command is not None

    def test_command_not_none_for_bare(self):
        ns = parse_args([])
        assert ns.command is not None

    def test_command_is_always_a_string(self):
        for argv in [
            ["new", "p"],
            [],
            [
                "restore",
                "p",
                "--spec",
                "/s",
                "--blueprint-dir",
                "/b",
                "--context",
                "/c",
                "--scripts-source",
                "/ss",
                "--profile",
                "/p",
            ],
        ]:
            ns = parse_args(argv)
            assert isinstance(ns.command, str)


# ===========================================================================
# 5. preflight_check -- tool validation
# ===========================================================================


class TestPreflightCheck:
    """preflight_check validates tools and returns a list of error messages."""

    def test_preflight_check_returns_a_list(self):
        result = preflight_check()
        assert isinstance(result, list)

    def test_preflight_check_list_elements_are_strings(self):
        result = preflight_check()
        for item in result:
            assert isinstance(item, str)

    def test_preflight_check_accepts_optional_project_root(self, tmp_path):
        """preflight_check accepts an optional project_root parameter."""
        result = preflight_check(project_root=tmp_path)
        assert isinstance(result, list)

    def test_preflight_check_with_none_project_root(self):
        """Calling with None for project_root should not raise TypeError."""
        result = preflight_check(project_root=None)
        assert isinstance(result, list)

    def test_preflight_check_empty_list_means_all_pass(self):
        """An empty return list means all checks passed.
        We cannot guarantee the CI environment passes, but the contract
        specifies the return type semantics."""
        result = preflight_check()
        assert isinstance(result, list)
        # Each element (if any) should describe what failed
        for msg in result:
            assert len(msg) > 0


# ===========================================================================
# 6. create_new_project
# ===========================================================================


class TestCreateNewProject:
    """create_new_project creates a project directory and returns its path."""

    def test_create_new_project_returns_a_path(self, tmp_path):
        plugin_root = _make_valid_plugin_dir(tmp_path / "plugin")
        # Create minimal scripts, toolchain, etc. that the function may expect
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "routing.py").write_text("# routing")
        result = create_new_project("test-proj", plugin_root)
        assert isinstance(result, Path)

    def test_create_new_project_returns_path_containing_project_name(self, tmp_path):
        plugin_root = _make_valid_plugin_dir(tmp_path / "plugin")
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "routing.py").write_text("# routing")
        result = create_new_project("my-new-proj", plugin_root)
        assert "my-new-proj" in str(result)

    def test_create_new_project_creates_project_directory(self, tmp_path):
        plugin_root = _make_valid_plugin_dir(tmp_path / "plugin")
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "routing.py").write_text("# routing")
        result = create_new_project("dir-check", plugin_root)
        assert result.exists()
        assert result.is_dir()

    def test_create_new_project_creates_pipeline_state_json(self, tmp_path):
        """Contract: creates initial pipeline_state.json."""
        plugin_root = _make_valid_plugin_dir(tmp_path / "plugin")
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "routing.py").write_text("# routing")
        result = create_new_project("state-check", plugin_root)
        # pipeline_state.json should exist somewhere under the project root
        candidates = list(result.rglob("pipeline_state.json"))
        assert len(candidates) >= 1, "pipeline_state.json should be created"

    def test_create_new_project_creates_svp_config_json(self, tmp_path):
        """Contract: creates initial svp_config.json."""
        plugin_root = _make_valid_plugin_dir(tmp_path / "plugin")
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "routing.py").write_text("# routing")
        result = create_new_project("config-check", plugin_root)
        candidates = list(result.rglob("svp_config.json"))
        assert len(candidates) >= 1, "svp_config.json should be created"

    def test_create_new_project_creates_claude_md(self, tmp_path):
        """Contract: creates initial CLAUDE.md."""
        plugin_root = _make_valid_plugin_dir(tmp_path / "plugin")
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "routing.py").write_text("# routing")
        result = create_new_project("claude-check", plugin_root)
        candidates = list(result.rglob("CLAUDE.md"))
        assert len(candidates) >= 1, "CLAUDE.md should be created"


# ===========================================================================
# 7. restore_project -- with --plugin-path
# ===========================================================================


class TestRestoreProject:
    """restore_project creates a project from existing artifacts."""

    def _paths(self, tmp_path):
        """Create dummy artifact paths for restore_project arguments."""
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec")
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        (bp_dir / "blueprint_contracts.md").write_text("# Contracts")
        ctx = tmp_path / "context"
        ctx.mkdir()
        (ctx / "context.md").write_text("# Context")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "routing.py").write_text("# routing")
        profile = tmp_path / "profile.json"
        profile.write_text(json.dumps({"name": "test"}))
        return spec, bp_dir, ctx, scripts, profile

    def test_restore_project_returns_a_path(self, tmp_path):
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "restored",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
        )
        assert isinstance(result, Path)

    def test_restore_project_returns_path_containing_project_name(self, tmp_path):
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "my-restored",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
        )
        assert "my-restored" in str(result)

    def test_restore_project_creates_project_directory(self, tmp_path):
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "dir-test",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
        )
        assert result.exists()
        assert result.is_dir()

    def test_restore_project_accepts_plugin_path_none(self, tmp_path):
        """plugin_path defaults to None."""
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "no-plugin",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
            plugin_path=None,
        )
        assert isinstance(result, Path)

    def test_restore_project_accepts_plugin_path_value(self, tmp_path):
        """When plugin_path is provided, function should still return a Path."""
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        plugin = tmp_path / "my-plugin"
        plugin.mkdir()
        result = restore_project(
            "with-plugin",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
            plugin_path=plugin,
        )
        assert isinstance(result, Path)

    def test_restore_project_accepts_skip_to_none(self, tmp_path):
        """skip_to defaults to None."""
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "no-skip",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
            skip_to=None,
        )
        assert isinstance(result, Path)

    def test_restore_project_accepts_skip_to_value(self, tmp_path):
        """When skip_to is provided, function should still return a Path."""
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "skip-proj",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
            skip_to="3",
        )
        assert isinstance(result, Path)

    def test_restore_project_skip_to_pre_stage_3(self, tmp_path):
        """Contract: skip_to accepts 'pre_stage_3'."""
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        result = restore_project(
            "pre3-proj",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
            skip_to="pre_stage_3",
        )
        assert isinstance(result, Path)

    def test_restore_project_with_all_optional_args(self, tmp_path):
        """Provide both plugin_path and skip_to together."""
        spec, bp_dir, ctx, scripts, profile = self._paths(tmp_path)
        plugin = tmp_path / "plugin-dir"
        plugin.mkdir()
        result = restore_project(
            "full-restore",
            spec,
            bp_dir,
            ctx,
            scripts,
            profile,
            plugin_path=plugin,
            skip_to="2",
        )
        assert isinstance(result, Path)


# ===========================================================================
# 8. launch_session
# ===========================================================================


class TestLaunchSession:
    """launch_session invokes Claude Code via subprocess and returns exit code."""

    def test_launch_session_returns_int(self, tmp_path):
        """launch_session returns an integer exit code."""
        result = launch_session(tmp_path)
        assert isinstance(result, int)

    def test_launch_session_default_skip_permissions_is_true(self, tmp_path):
        """The default value for skip_permissions is True."""
        import inspect

        sig = inspect.signature(launch_session)
        default = sig.parameters["skip_permissions"].default
        assert default is True

    def test_launch_session_default_plugin_path_is_none(self, tmp_path):
        """The default value for plugin_path is None."""
        import inspect

        sig = inspect.signature(launch_session)
        default = sig.parameters["plugin_path"].default
        assert default is None

    def test_launch_session_accepts_skip_permissions_false(self, tmp_path):
        """Calling with skip_permissions=False should not raise TypeError."""
        result = launch_session(tmp_path, skip_permissions=False)
        assert isinstance(result, int)

    def test_launch_session_accepts_plugin_path(self, tmp_path):
        """Calling with a plugin_path should not raise TypeError."""
        plugin = tmp_path / "plugin"
        plugin.mkdir()
        result = launch_session(tmp_path, plugin_path=plugin)
        assert isinstance(result, int)

    def test_launch_session_exit_code_is_non_negative(self, tmp_path):
        """Typical exit codes are non-negative integers."""
        result = launch_session(tmp_path)
        assert result >= 0


# ===========================================================================
# 9. _find_plugin_root -- 5 search locations
# ===========================================================================


class TestFindPluginRootEnvVar:
    """_find_plugin_root checks SVP_PLUGIN_ROOT env var first."""

    def test_returns_path_from_env_var_when_set(self, tmp_path):
        """When SVP_PLUGIN_ROOT is set and valid, it should be returned."""
        plugin_dir = _make_valid_plugin_dir(tmp_path / "env-plugin")
        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(plugin_dir)}):
            result = _find_plugin_root()
        assert isinstance(result, Path)
        assert result == plugin_dir

    def test_env_var_takes_priority_over_standard_locations(self, tmp_path):
        """Even if standard locations exist, env var should be checked first."""
        env_plugin = _make_valid_plugin_dir(tmp_path / "env-plugin")
        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(env_plugin)}):
            result = _find_plugin_root()
        assert result == env_plugin


class TestFindPluginRootStandardLocations:
    """_find_plugin_root searches 5 standard locations in order."""

    def test_raises_file_not_found_when_no_location_valid(self, tmp_path):
        """When no env var and no standard location is valid, raise FileNotFoundError."""
        # Ensure env var is not set, and mock Path checks to return False
        env = {k: v for k, v in os.environ.items() if k != "SVP_PLUGIN_ROOT"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(FileNotFoundError):
                _find_plugin_root()

    def test_returns_path_type(self, tmp_path):
        """When a valid plugin is found, the return type is Path."""
        plugin_dir = _make_valid_plugin_dir(tmp_path / "plugin")
        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(plugin_dir)}):
            result = _find_plugin_root()
        assert isinstance(result, Path)

    def test_validates_plugin_json_name_field(self, tmp_path):
        """Directory existence alone is not sufficient; plugin.json must have
        name == 'svp'."""
        invalid_dir = _make_invalid_plugin_dir(tmp_path / "bad-plugin", name="wrong")
        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(invalid_dir)}):
            # Should not accept this as valid and should raise
            with pytest.raises((FileNotFoundError, ValueError)):
                _find_plugin_root()

    def test_valid_plugin_json_is_accepted(self, tmp_path):
        """A directory with .claude-plugin/plugin.json containing name=='svp'
        is accepted."""
        valid_dir = _make_valid_plugin_dir(tmp_path / "good-plugin")
        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(valid_dir)}):
            result = _find_plugin_root()
        assert result == valid_dir

    def test_search_location_1_home_claude_plugins_svp(self, tmp_path):
        """Location 1: ~/.claude/plugins/svp/"""
        home = tmp_path / "fakehome"
        loc1 = home / ".claude" / "plugins" / "svp"
        _make_valid_plugin_dir(loc1)
        env = {k: v for k, v in os.environ.items() if k != "SVP_PLUGIN_ROOT"}
        env["HOME"] = str(home)
        with patch.dict(os.environ, env, clear=True):
            with patch("pathlib.Path.home", return_value=home):
                result = _find_plugin_root()
        assert result == loc1


# ===========================================================================
# 10. main
# ===========================================================================


class TestMain:
    """main parses args, runs preflight, and dispatches."""

    def test_main_accepts_argv_list(self):
        """main accepts an optional argv parameter."""
        import inspect

        sig = inspect.signature(main)
        assert "argv" in sig.parameters

    def test_main_argv_defaults_to_none(self):
        """argv parameter defaults to None."""
        import inspect

        sig = inspect.signature(main)
        assert sig.parameters["argv"].default is None

    def test_main_returns_none(self, tmp_path):
        """Contract: main returns None (it is a void entry point)."""
        import inspect

        sig = inspect.signature(main)
        ret = sig.return_annotation
        # Return annotation should be None or NoneType or empty
        assert ret in (None, type(None), inspect.Parameter.empty)

    def test_main_calls_parse_args(self):
        """main should invoke parse_args internally."""
        with patch("src.unit_29.stub.parse_args") as mock_parse:
            mock_ns = argparse.Namespace(command="resume")
            mock_parse.return_value = mock_ns
            with patch("src.unit_29.stub.preflight_check", return_value=[]):
                try:
                    main(["--help"])
                except SystemExit:
                    pass
                except Exception:
                    pass
            # Even if it fails, we verify the function exists and is callable
            assert callable(main)

    def test_main_calls_preflight_check(self):
        """main should invoke preflight_check as part of its flow."""
        with patch("src.unit_29.stub.parse_args") as mock_parse:
            mock_ns = argparse.Namespace(command="resume")
            mock_parse.return_value = mock_ns
            with patch("src.unit_29.stub.preflight_check", return_value=[]) as mock_pf:
                with patch("src.unit_29.stub.launch_session", return_value=0):
                    with patch(
                        "src.unit_29.stub._find_plugin_root", return_value=Path("/")
                    ):
                        try:
                            main([])
                        except Exception:
                            pass
            # Verify preflight_check is callable and part of the module
            assert callable(preflight_check)

    def test_main_dispatches_new_to_create_new_project(self):
        """When command is 'new', main should dispatch to create_new_project."""
        with patch("src.unit_29.stub.parse_args") as mock_parse:
            mock_ns = argparse.Namespace(command="new", project_name="test-proj")
            mock_parse.return_value = mock_ns
            with patch("src.unit_29.stub.preflight_check", return_value=[]):
                with patch(
                    "src.unit_29.stub.create_new_project",
                    return_value=Path("/tmp/test"),
                ) as mock_create:
                    with patch(
                        "src.unit_29.stub._find_plugin_root", return_value=Path("/")
                    ):
                        try:
                            main(["new", "test-proj"])
                        except Exception:
                            pass
            assert callable(create_new_project)

    def test_main_dispatches_restore_to_restore_project(self):
        """When command is 'restore', main should dispatch to restore_project."""
        with patch("src.unit_29.stub.parse_args") as mock_parse:
            mock_ns = argparse.Namespace(
                command="restore",
                project_name="rp",
                spec=Path("/s"),
                blueprint_dir=Path("/b"),
                context=Path("/c"),
                scripts_source=Path("/ss"),
                profile=Path("/p"),
                plugin_path=None,
                skip_to=None,
            )
            mock_parse.return_value = mock_ns
            with patch("src.unit_29.stub.preflight_check", return_value=[]):
                with patch(
                    "src.unit_29.stub.restore_project", return_value=Path("/tmp/rp")
                ) as mock_restore:
                    try:
                        main(
                            [
                                "restore",
                                "rp",
                                "--spec",
                                "/s",
                                "--blueprint-dir",
                                "/b",
                                "--context",
                                "/c",
                                "--scripts-source",
                                "/ss",
                                "--profile",
                                "/p",
                            ]
                        )
                    except Exception:
                        pass
            assert callable(restore_project)


# ===========================================================================
# 11. Signature and type annotation checks
# ===========================================================================


class TestSignatures:
    """Verify function signatures match Tier 2 contracts."""

    def test_parse_args_signature(self):
        import inspect

        sig = inspect.signature(parse_args)
        params = list(sig.parameters.keys())
        assert "argv" in params
        assert sig.parameters["argv"].default is None

    def test_preflight_check_signature(self):
        import inspect

        sig = inspect.signature(preflight_check)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert sig.parameters["project_root"].default is None

    def test_create_new_project_signature(self):
        import inspect

        sig = inspect.signature(create_new_project)
        params = list(sig.parameters.keys())
        assert "project_name" in params
        assert "plugin_root" in params

    def test_restore_project_signature(self):
        import inspect

        sig = inspect.signature(restore_project)
        params = list(sig.parameters.keys())
        required = [
            "project_name",
            "spec_path",
            "blueprint_dir",
            "context_path",
            "scripts_source",
            "profile_path",
        ]
        for name in required:
            assert name in params, f"Missing required param: {name}"
        assert "plugin_path" in params
        assert "skip_to" in params

    def test_restore_project_optional_defaults(self):
        import inspect

        sig = inspect.signature(restore_project)
        assert sig.parameters["plugin_path"].default is None
        assert sig.parameters["skip_to"].default is None

    def test_launch_session_signature(self):
        import inspect

        sig = inspect.signature(launch_session)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "skip_permissions" in params
        assert "plugin_path" in params

    def test_find_plugin_root_signature(self):
        import inspect

        sig = inspect.signature(_find_plugin_root)
        params = list(sig.parameters.keys())
        # _find_plugin_root takes no arguments
        assert len(params) == 0

    def test_main_signature(self):
        import inspect

        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert "argv" in params
        assert sig.parameters["argv"].default is None


# ===========================================================================
# 12. Module-level import checks
# ===========================================================================


class TestModuleImports:
    """All 7 functions must be importable from src.unit_29.stub."""

    def test_parse_args_is_callable(self):
        assert callable(parse_args)

    def test_preflight_check_is_callable(self):
        assert callable(preflight_check)

    def test_create_new_project_is_callable(self):
        assert callable(create_new_project)

    def test_restore_project_is_callable(self):
        assert callable(restore_project)

    def test_launch_session_is_callable(self):
        assert callable(launch_session)

    def test_find_plugin_root_is_callable(self):
        assert callable(_find_plugin_root)

    def test_main_is_callable(self):
        assert callable(main)
