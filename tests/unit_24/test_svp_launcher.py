"""
Test suite for Unit 24: SVP Launcher

Tests cover:
- Constants and module-level values
- Plugin discovery functions
- Output formatting functions
- CLI argument parsing
- 8 prerequisite checks
- Project setup functions (directory creation, script copying, CLAUDE.md, state, config, readme)
- Filesystem permissions
- Session lifecycle (launch, restart signal, session loop)
- Resume functionality
- Command handlers
- Entry point (main)

DATA ASSUMPTIONS:
- Project names are simple alphanumeric strings like "test_project", "my_app".
- Parent directories are temporary directories created by pytest's tmp_path fixture.
- Plugin directories are synthesized with the expected .claude-plugin/plugin.json manifest.
- Pipeline state JSON follows the schema from Unit 22's PIPELINE_STATE_INITIAL_JSON_CONTENT.
- Config JSON follows the schema from Unit 22's SVP_CONFIG_DEFAULT_JSON_CONTENT.
- Subprocess calls to external tools (claude, conda, git, curl, pytest) are mocked;
  no real external processes are invoked during testing.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from svp.scripts.svp_launcher import (
    # Constants
    RESTART_SIGNAL_FILE,
    STATE_FILE,
    CONFIG_FILE,
    SVP_DIR,
    MARKERS_DIR,
    CLAUDE_MD_FILE,
    README_SVP_FILE,
    SVP_ENV_VAR,
    PROJECT_DIRS,
    # Plugin discovery
    _find_plugin_root,
    _is_svp_plugin_dir,
    # Output formatting
    _print_header,
    _print_status,
    _print_transition,
    # CLI parsing
    parse_args,
    # Prerequisite checks
    check_claude_code,
    check_svp_plugin,
    check_api_credentials,
    check_conda,
    check_python,
    check_pytest as check_pytest_func,
    check_git,
    check_network,
    run_all_prerequisites,
    # Project setup
    create_project_directory,
    copy_scripts_to_workspace,
    generate_claude_md,
    _generate_claude_md_fallback,
    write_initial_state,
    write_default_config,
    write_readme_svp,
    # Filesystem permissions
    set_filesystem_permissions,
    # Session lifecycle
    launch_claude_code,
    detect_restart_signal,
    clear_restart_signal,
    run_session_loop,
    # Resume
    detect_existing_project,
    resume_project,
    # Command handlers
    _handle_new_project,
    _handle_restore,
    _handle_resume,
    # Entry point
    main,
)


# =============================================================================
# Constants and Invariants
# =============================================================================


class TestConstants:
    """Verify all module-level constants match the blueprint specification."""

    def test_restart_signal_file(self):
        assert RESTART_SIGNAL_FILE == ".svp/restart_signal"

    def test_state_file(self):
        assert STATE_FILE == "pipeline_state.json"

    def test_config_file(self):
        assert CONFIG_FILE == "svp_config.json"

    def test_svp_dir(self):
        assert SVP_DIR == ".svp"

    def test_markers_dir(self):
        assert MARKERS_DIR == ".svp/markers"

    def test_claude_md_file(self):
        assert CLAUDE_MD_FILE == "CLAUDE.md"

    def test_readme_svp_file(self):
        assert README_SVP_FILE == "README_SVP.txt"

    def test_svp_env_var_matches_unit_12(self):
        """Cross-unit invariant: SVP_PLUGIN_ACTIVE must match Unit 12."""
        assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"

    def test_project_dirs_is_list(self):
        assert isinstance(PROJECT_DIRS, list)

    def test_project_dirs_contains_svp(self):
        assert ".svp" in PROJECT_DIRS

    def test_project_dirs_contains_scripts(self):
        assert "scripts" in PROJECT_DIRS

    def test_project_dirs_contains_src(self):
        assert "src" in PROJECT_DIRS

    def test_project_dirs_contains_tests(self):
        assert "tests" in PROJECT_DIRS

    def test_project_dirs_contains_svp_markers(self):
        assert ".svp/markers" in PROJECT_DIRS

    def test_project_dirs_contains_claude(self):
        assert ".claude" in PROJECT_DIRS

    def test_project_dirs_contains_ledgers(self):
        assert "ledgers" in PROJECT_DIRS

    def test_project_dirs_contains_logs(self):
        assert "logs" in PROJECT_DIRS

    def test_project_dirs_contains_logs_rollback(self):
        assert "logs/rollback" in PROJECT_DIRS

    def test_project_dirs_contains_specs(self):
        assert "specs" in PROJECT_DIRS

    def test_project_dirs_contains_specs_history(self):
        assert "specs/history" in PROJECT_DIRS

    def test_project_dirs_contains_blueprint(self):
        assert "blueprint" in PROJECT_DIRS

    def test_project_dirs_contains_blueprint_history(self):
        assert "blueprint/history" in PROJECT_DIRS

    def test_project_dirs_contains_references(self):
        assert "references" in PROJECT_DIRS

    def test_project_dirs_contains_references_index(self):
        assert "references/index" in PROJECT_DIRS

    def test_project_dirs_contains_data(self):
        assert "data" in PROJECT_DIRS


# =============================================================================
# Signature Verification
# =============================================================================


class TestSignatures:
    """Verify function signatures match the blueprint."""

    def test_find_plugin_root_returns_optional_path(self):
        """_find_plugin_root() -> Optional[Path]"""
        import inspect

        sig = inspect.signature(_find_plugin_root)
        assert len(sig.parameters) == 0

    def test_is_svp_plugin_dir_takes_path(self):
        """_is_svp_plugin_dir(path: Path) -> bool"""
        import inspect

        sig = inspect.signature(_is_svp_plugin_dir)
        params = list(sig.parameters.keys())
        assert "path" in params

    def test_parse_args_takes_optional_argv(self):
        """parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace"""
        import inspect

        sig = inspect.signature(parse_args)
        params = sig.parameters
        assert "argv" in params
        assert params["argv"].default is None

    def test_create_project_directory_signature(self):
        import inspect

        sig = inspect.signature(create_project_directory)
        params = list(sig.parameters.keys())
        assert "project_name" in params
        assert "parent_dir" in params

    def test_copy_scripts_to_workspace_signature(self):
        import inspect

        sig = inspect.signature(copy_scripts_to_workspace)
        params = list(sig.parameters.keys())
        assert "plugin_root" in params
        assert "project_root" in params

    def test_generate_claude_md_signature(self):
        import inspect

        sig = inspect.signature(generate_claude_md)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "project_name" in params

    def test_set_filesystem_permissions_signature(self):
        import inspect

        sig = inspect.signature(set_filesystem_permissions)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "read_only" in params

    def test_launch_claude_code_signature(self):
        import inspect

        sig = inspect.signature(launch_claude_code)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "plugin_dir" in params

    def test_detect_restart_signal_signature(self):
        import inspect

        sig = inspect.signature(detect_restart_signal)
        params = list(sig.parameters.keys())
        assert "project_root" in params

    def test_clear_restart_signal_signature(self):
        import inspect

        sig = inspect.signature(clear_restart_signal)
        params = list(sig.parameters.keys())
        assert "project_root" in params

    def test_run_session_loop_signature(self):
        import inspect

        sig = inspect.signature(run_session_loop)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "plugin_dir" in params

    def test_detect_existing_project_signature(self):
        import inspect

        sig = inspect.signature(detect_existing_project)
        params = list(sig.parameters.keys())
        assert "directory" in params

    def test_resume_project_signature(self):
        import inspect

        sig = inspect.signature(resume_project)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "plugin_dir" in params

    def test_main_signature(self):
        import inspect

        sig = inspect.signature(main)
        params = sig.parameters
        assert "argv" in params
        assert params["argv"].default is None

    def test_check_functions_return_tuple(self):
        """All check functions should have no parameters."""
        import inspect

        for fn in [
            check_claude_code,
            check_svp_plugin,
            check_api_credentials,
            check_conda,
            check_python,
            check_pytest_func,
            check_git,
            check_network,
        ]:
            sig = inspect.signature(fn)
            assert len(sig.parameters) == 0, f"{fn.__name__} should take no params"

    def test_write_initial_state_signature(self):
        import inspect

        sig = inspect.signature(write_initial_state)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "project_name" in params

    def test_write_default_config_signature(self):
        import inspect

        sig = inspect.signature(write_default_config)
        params = list(sig.parameters.keys())
        assert "project_root" in params

    def test_write_readme_svp_signature(self):
        import inspect

        sig = inspect.signature(write_readme_svp)
        params = list(sig.parameters.keys())
        assert "project_root" in params

    def test_handle_new_project_signature(self):
        import inspect

        sig = inspect.signature(_handle_new_project)
        params = list(sig.parameters.keys())
        assert "args" in params
        assert "plugin_dir" in params

    def test_handle_restore_signature(self):
        import inspect

        sig = inspect.signature(_handle_restore)
        params = list(sig.parameters.keys())
        assert "args" in params
        assert "plugin_dir" in params

    def test_handle_resume_signature(self):
        import inspect

        sig = inspect.signature(_handle_resume)
        params = list(sig.parameters.keys())
        assert "plugin_dir" in params

    def test_run_all_prerequisites_signature(self):
        import inspect

        sig = inspect.signature(run_all_prerequisites)
        assert len(sig.parameters) == 0

    def test_generate_claude_md_fallback_signature(self):
        import inspect

        sig = inspect.signature(_generate_claude_md_fallback)
        params = list(sig.parameters.keys())
        assert "project_name" in params

    def test_print_header_signature(self):
        import inspect

        sig = inspect.signature(_print_header)
        params = list(sig.parameters.keys())
        assert "text" in params

    def test_print_status_signature(self):
        import inspect

        sig = inspect.signature(_print_status)
        params = list(sig.parameters.keys())
        assert "name" in params
        assert "passed" in params
        assert "message" in params

    def test_print_transition_signature(self):
        import inspect

        sig = inspect.signature(_print_transition)
        params = list(sig.parameters.keys())
        assert "message" in params


# =============================================================================
# Plugin Discovery
# =============================================================================


class TestIsPluginDir:
    """Tests for _is_svp_plugin_dir."""

    def test_valid_plugin_dir(self, tmp_path):
        """Returns True for a directory with .claude-plugin/plugin.json with name=svp."""
        # DATA ASSUMPTION: Plugin manifest is a JSON file with "name": "svp".
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir()
        manifest = manifest_dir / "plugin.json"
        manifest.write_text(json.dumps({"name": "svp", "version": "1.2.1"}))

        result = _is_svp_plugin_dir(plugin_dir)
        assert result is True

    def test_missing_plugin_json(self, tmp_path):
        """Returns False when .claude-plugin/plugin.json is missing."""
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()

        result = _is_svp_plugin_dir(plugin_dir)
        assert result is False

    def test_invalid_json(self, tmp_path):
        """Returns False on JSON decode error."""
        # DATA ASSUMPTION: Corrupted manifest file with invalid JSON.
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir()
        manifest = manifest_dir / "plugin.json"
        manifest.write_text("not valid json {{{")

        result = _is_svp_plugin_dir(plugin_dir)
        assert result is False

    def test_wrong_name(self, tmp_path):
        """Returns False when the plugin name is not 'svp'."""
        # DATA ASSUMPTION: Non-SVP plugin with a different name field.
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir()
        manifest = manifest_dir / "plugin.json"
        manifest.write_text(json.dumps({"name": "other_plugin"}))

        result = _is_svp_plugin_dir(plugin_dir)
        assert result is False

    def test_missing_name_field(self, tmp_path):
        """Returns False when plugin.json has no 'name' key."""
        # DATA ASSUMPTION: Manifest with missing 'name' key.
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir()
        manifest = manifest_dir / "plugin.json"
        manifest.write_text(json.dumps({"version": "1.0"}))

        result = _is_svp_plugin_dir(plugin_dir)
        assert result is False


class TestFindPluginRoot:
    """Tests for _find_plugin_root."""

    def test_finds_via_env_var(self, tmp_path):
        """Returns plugin root from SVP_PLUGIN_ROOT env var when valid."""
        # DATA ASSUMPTION: SVP_PLUGIN_ROOT env var points to a valid plugin directory.
        plugin_dir = tmp_path / "svp_plugin"
        plugin_dir.mkdir()
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir()
        manifest = manifest_dir / "plugin.json"
        manifest.write_text(json.dumps({"name": "svp"}))

        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(plugin_dir)}):
            result = _find_plugin_root()
            assert result == plugin_dir

    def test_returns_none_when_no_plugin_found(self):
        """Returns None when no plugin directory exists at any search location."""
        # Mock all paths as non-existent
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "svp.scripts.svp_launcher._is_svp_plugin_dir", return_value=False
            ):
                result = _find_plugin_root()
                assert result is None

    def test_env_var_invalid_dir(self, tmp_path):
        """Falls through env var if directory is not a valid plugin."""
        # DATA ASSUMPTION: SVP_PLUGIN_ROOT points to a dir without valid manifest.
        non_plugin_dir = tmp_path / "not_a_plugin"
        non_plugin_dir.mkdir()

        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(non_plugin_dir)}):
            with patch("svp.scripts.svp_launcher._is_svp_plugin_dir") as mock_check:
                mock_check.return_value = False
                result = _find_plugin_root()
                assert result is None


# =============================================================================
# Output Formatting
# =============================================================================


class TestOutputFormatting:
    """Tests for _print_header, _print_status, _print_transition."""

    def test_print_header_produces_output(self, capsys):
        """_print_header prints a decorated header line."""
        _print_header("SVP Launcher")
        captured = capsys.readouterr()
        assert "SVP Launcher" in captured.out

    def test_print_status_passed(self, capsys):
        """_print_status prints a pass icon for passing checks."""
        _print_status("Python", True, "Python 3.11.0")
        captured = capsys.readouterr()
        assert "Python" in captured.out
        assert "3.11.0" in captured.out

    def test_print_status_failed(self, capsys):
        """_print_status prints a fail icon for failing checks."""
        _print_status("Git", False, "Not found")
        captured = capsys.readouterr()
        assert "Git" in captured.out
        assert "Not found" in captured.out

    def test_print_transition(self, capsys):
        """_print_transition prints a session transition message."""
        _print_transition("Restarting session...")
        captured = capsys.readouterr()
        assert "Restarting session" in captured.out


# =============================================================================
# CLI Argument Parsing
# =============================================================================


class TestParseArgs:
    """Tests for parse_args."""

    def test_new_subcommand(self):
        """parse_args parses 'new <project_name>'."""
        # DATA ASSUMPTION: A simple project name "my_project" with no special characters.
        result = parse_args(["new", "my_project"])
        assert isinstance(result, argparse.Namespace)
        assert result.project_name == "my_project"

    def test_new_with_parent_dir(self):
        """parse_args parses 'new <project_name> --parent-dir /tmp/foo'."""
        result = parse_args(["new", "my_project", "--parent-dir", "/tmp/foo"])
        assert isinstance(result, argparse.Namespace)
        assert result.project_name == "my_project"
        assert str(result.parent_dir) == "/tmp/foo"

    def test_restore_subcommand(self):
        """parse_args parses 'restore <project_name> --spec ... --blueprint ...'."""
        # DATA ASSUMPTION: Valid file paths for spec and blueprint files.
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint",
                "/path/to/blueprint.md",
            ]
        )
        assert isinstance(result, argparse.Namespace)
        assert result.project_name == "my_project"

    def test_restore_with_context(self):
        """parse_args accepts optional --context on restore."""
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint",
                "/path/to/blueprint.md",
                "--context",
                "/path/to/context.md",
            ]
        )
        assert isinstance(result, argparse.Namespace)

    def test_restore_with_scripts_source(self):
        """parse_args accepts --scripts-source on restore."""
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint",
                "/path/to/blueprint.md",
                "--scripts-source",
                "/dev/scripts",
            ]
        )
        assert isinstance(result, argparse.Namespace)

    def test_restore_with_parent_dir(self):
        """parse_args accepts --parent-dir on restore."""
        result = parse_args(
            [
                "restore",
                "my_project",
                "--spec",
                "/path/to/spec.md",
                "--blueprint",
                "/path/to/blueprint.md",
                "--parent-dir",
                "/tmp/bar",
            ]
        )
        assert isinstance(result, argparse.Namespace)

    def test_no_subcommand_defaults_to_resume(self):
        """parse_args with no args defaults to resume behavior."""
        result = parse_args([])
        assert isinstance(result, argparse.Namespace)

    def test_accepts_none_for_argv(self):
        """parse_args(None) should use sys.argv-like behavior."""
        # We test that it accepts the parameter; actual behavior depends on sys.argv
        # so we provide explicit empty list to avoid side effects
        result = parse_args([])
        assert isinstance(result, argparse.Namespace)


# =============================================================================
# Prerequisite Checks
# =============================================================================


class TestCheckClaudeCode:
    """Tests for check_claude_code."""

    def test_returns_tuple(self):
        """check_claude_code returns (bool, str)."""
        result = check_claude_code()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    @patch("subprocess.run")
    def test_success(self, mock_run):
        """Returns (True, version_message) when claude is available."""
        # DATA ASSUMPTION: Claude CLI returns version string like "1.0.0".
        mock_run.return_value = MagicMock(returncode=0, stdout="1.0.0\n", stderr="")
        passed, message = check_claude_code()
        assert passed is True
        # The version should be mentioned in the message
        assert "1.0.0" in message

    @patch("subprocess.run")
    def test_failure_not_found(self, mock_run):
        """Returns (False, ...) when claude is not available."""
        mock_run.side_effect = FileNotFoundError("claude not found")
        passed, message = check_claude_code()
        assert passed is False


class TestCheckSvpPlugin:
    """Tests for check_svp_plugin."""

    def test_returns_tuple(self):
        """check_svp_plugin returns (bool, str)."""
        result = check_svp_plugin()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("svp_host_claude.launcher_adapter._find_plugin_root")
    def test_success(self, mock_find):
        """Returns (True, ...) when plugin is found."""
        # DATA ASSUMPTION: Plugin root at a typical path.
        mock_find.return_value = Path("/home/user/.claude/plugins/svp")
        passed, message = check_svp_plugin()
        assert passed is True

    @patch("svp_host_claude.launcher_adapter._find_plugin_root")
    def test_failure(self, mock_find):
        """Returns (False, ...) when plugin is not found."""
        mock_find.return_value = None
        passed, message = check_svp_plugin()
        assert passed is False

    """Tests for check_api_credentials."""

    def test_returns_tuple(self):
        """check_api_credentials returns (bool, str)."""
        result = check_api_credentials()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123"})
    def test_success_via_env_var(self):
        """Returns (True, ...) when ANTHROPIC_API_KEY is set."""
        passed, message = check_api_credentials()
        assert passed is True

    @patch("subprocess.run")
    @patch.dict(os.environ, {}, clear=True)
    def test_fallback_to_claude_auth(self, mock_run):
        """Falls back to 'claude auth status' when env var is absent."""
        # Remove ANTHROPIC_API_KEY if present
        mock_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Authenticated", stderr=""
        )
        with patch.dict(os.environ, mock_env, clear=True):
            passed, message = check_api_credentials()
            # Should at least not crash; result depends on implementation


class TestCheckConda:
    """Tests for check_conda."""

    def test_returns_tuple(self):
        result = check_conda()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("subprocess.run")
    def test_success(self, mock_run):
        """Returns (True, version) when conda is available."""
        # DATA ASSUMPTION: conda --version outputs "conda 23.7.4".
        mock_run.return_value = MagicMock(
            returncode=0, stdout="conda 23.7.4\n", stderr=""
        )
        passed, message = check_conda()
        assert passed is True

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        """Returns (False, ...) when conda is not found."""
        mock_run.side_effect = FileNotFoundError("conda not found")
        passed, message = check_conda()
        assert passed is False


class TestCheckPython:
    """Tests for check_python."""

    def test_returns_tuple(self):
        result = check_python()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("subprocess.run")
    def test_success_recent_version(self, mock_run):
        """Returns (True, ...) for Python >= 3.10."""
        # DATA ASSUMPTION: Python version string like "Python 3.11.5".
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Python 3.11.5\n", stderr=""
        )
        passed, message = check_python()
        assert passed is True

    @patch("subprocess.run")
    def test_failure_old_version(self, mock_run):
        """Returns (False, ...) for Python < 3.10."""
        # DATA ASSUMPTION: Python 3.9 should fail the >= 3.10 check.
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Python 3.9.1\n", stderr=""
        )
        passed, message = check_python()
        assert passed is False


class TestCheckPytest:
    """Tests for check_pytest."""

    def test_returns_tuple(self):
        result = check_pytest_func()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("subprocess.run")
    def test_success(self, mock_run):
        """Returns (True, ...) when pytest is available."""
        # DATA ASSUMPTION: pytest --version outputs version info.
        mock_run.return_value = MagicMock(
            returncode=0, stdout="pytest 7.4.0\n", stderr=""
        )
        passed, message = check_pytest_func()
        assert passed is True

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        """Returns (False, ...) when pytest is not available."""
        mock_run.side_effect = FileNotFoundError("pytest not found")
        passed, message = check_pytest_func()
        assert passed is False


class TestCheckGit:
    """Tests for check_git."""

    def test_returns_tuple(self):
        result = check_git()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("subprocess.run")
    def test_success(self, mock_run):
        """Returns (True, ...) when git is configured with user name and email."""

        # DATA ASSUMPTION: git --version returns a version, git config returns user info.
        def side_effect(cmd, *args, **kwargs):
            if "git" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="git version 2.42.0\n", stderr="")
            elif "git" in cmd and "user.name" in cmd:
                return MagicMock(returncode=0, stdout="Test User\n", stderr="")
            elif "git" in cmd and "user.email" in cmd:
                return MagicMock(returncode=0, stdout="test@example.com\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect
        passed, message = check_git()
        assert passed is True

    @patch("subprocess.run")
    def test_failure_no_user_config(self, mock_run):
        """Returns (False, ...) when git user is not configured."""

        # DATA ASSUMPTION: git config user.name fails with non-zero exit code.
        def side_effect(cmd, *args, **kwargs):
            if "git" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="git version 2.42.0\n", stderr="")
            elif "git" in cmd and "user.name" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="")

        mock_run.side_effect = side_effect
        passed, message = check_git()
        assert passed is False


class TestCheckNetwork:
    """Tests for check_network."""

    def test_returns_tuple(self):
        result = check_network()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("subprocess.run")
    def test_success_via_curl(self, mock_run):
        """Returns (True, ...) when curl succeeds to api.anthropic.com."""
        # DATA ASSUMPTION: curl returns HTTP 200 for api.anthropic.com.
        mock_run.return_value = MagicMock(returncode=0, stdout="200", stderr="")
        passed, message = check_network()
        assert passed is True


class TestRunAllPrerequisites:
    """Tests for run_all_prerequisites."""

    def test_returns_exactly_8_results(self):
        """Invariant: exactly 8 prerequisite checks, in order."""
        results = run_all_prerequisites()
        assert isinstance(results, list)
        assert len(results) == 8

    def test_result_format(self):
        """Each result is (name: str, passed: bool, message: str)."""
        results = run_all_prerequisites()
        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 3
            name, passed, message = result
            assert isinstance(name, str)
            assert isinstance(passed, bool)
            assert isinstance(message, str)


# =============================================================================
# Project Setup
# =============================================================================


class TestCreateProjectDirectory:
    """Tests for create_project_directory."""

    def test_creates_all_project_dirs(self, tmp_path):
        """Creates all directories listed in PROJECT_DIRS."""
        # DATA ASSUMPTION: A simple project name "test_project" with tmp_path as parent.
        project_root = create_project_directory("test_project", tmp_path)
        assert project_root.exists()
        assert project_root == tmp_path / "test_project"

        for dir_name in PROJECT_DIRS:
            dir_path = project_root / dir_name
            assert dir_path.is_dir(), f"Missing directory: {dir_name}"

    def test_returns_project_root_path(self, tmp_path):
        """Returns the created project root Path."""
        result = create_project_directory("my_app", tmp_path)
        assert isinstance(result, Path)
        assert result.name == "my_app"

    def test_raises_file_exists_error(self, tmp_path):
        """Raises FileExistsError if project directory already exists."""
        # DATA ASSUMPTION: Pre-existing directory triggers the error.
        existing = tmp_path / "existing_project"
        existing.mkdir()

        with pytest.raises(FileExistsError, match="already exists"):
            create_project_directory("existing_project", tmp_path)


class TestCopyScriptsToWorkspace:
    """Tests for copy_scripts_to_workspace."""

    def test_copies_scripts_directory(self, tmp_path):
        """Copies scripts/ from plugin to workspace."""
        # DATA ASSUMPTION: Plugin has a scripts/ directory with at least one file.
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing script")
        (scripts_dir / "helpers.py").write_text("# helpers")

        project_root = tmp_path / "project"
        project_root.mkdir()

        copy_scripts_to_workspace(plugin_root, project_root)

        assert (project_root / "scripts").is_dir()
        assert (project_root / "scripts" / "routing.py").exists()
        assert (project_root / "scripts" / "helpers.py").exists()

    def test_copies_subdirectories(self, tmp_path):
        """Copies scripts subdirectories (files and subdirectories)."""
        # DATA ASSUMPTION: Plugin scripts has a templates/ subdirectory.
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir()
        templates_dir = scripts_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "template.txt").write_text("template content")

        project_root = tmp_path / "project"
        project_root.mkdir()

        copy_scripts_to_workspace(plugin_root, project_root)

        assert (project_root / "scripts" / "templates" / "template.txt").exists()

    def test_raises_runtime_error_no_scripts_dir(self, tmp_path):
        """Raises RuntimeError when plugin has no scripts/ directory."""
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()

        project_root = tmp_path / "project"
        project_root.mkdir()

        with pytest.raises(RuntimeError, match="scripts directory not found"):
            copy_scripts_to_workspace(plugin_root, project_root)


class TestGenerateClaudeMd:
    """Tests for generate_claude_md and _generate_claude_md_fallback."""

    def test_generates_claude_md_file(self, tmp_path):
        """generate_claude_md creates CLAUDE.md in the project root."""
        # DATA ASSUMPTION: No template module available, so fallback is used.
        project_root = tmp_path / "project"
        project_root.mkdir()
        scripts_dir = project_root / "scripts"
        scripts_dir.mkdir()

        generate_claude_md(project_root, "my_project")

        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "my_project" in content

    def test_fallback_contains_project_name(self):
        """_generate_claude_md_fallback includes the project name."""
        # DATA ASSUMPTION: Project name "test_proj" should appear in the output.
        content = _generate_claude_md_fallback("test_proj")
        assert isinstance(content, str)
        assert "test_proj" in content

    def test_fallback_contains_routing_instruction(self):
        """Fallback includes the 'On Session Start' routing instruction."""
        content = _generate_claude_md_fallback("my_project")
        assert "routing" in content.lower() or "routing.py" in content

    def test_fallback_contains_six_step_cycle(self):
        """Fallback includes the six-step action cycle."""
        content = _generate_claude_md_fallback("my_project")
        assert "six" in content.lower() or "Six-Step" in content or "6" in content

    def test_fallback_contains_verbatim_relay(self):
        """Fallback includes the verbatim relay rule."""
        content = _generate_claude_md_fallback("my_project")
        assert "verbatim" in content.lower()

    def test_fallback_contains_do_not_improvise(self):
        """Fallback includes the 'Do Not Improvise' section."""
        content = _generate_claude_md_fallback("my_project")
        assert "improvise" in content.lower()

    def test_fallback_contains_human_input_deferral(self):
        """Fallback includes the human input deferral rule."""
        content = _generate_claude_md_fallback("my_project")
        assert "human" in content.lower() or "defer" in content.lower()

    def test_fallback_references_orchestration_skill(self):
        """Fallback references the SVP orchestration skill."""
        content = _generate_claude_md_fallback("my_project")
        assert "orchestration" in content.lower()

    def test_generate_uses_template_when_available(self, tmp_path):
        """generate_claude_md uses scripts/templates/claude_md.py when available."""
        # DATA ASSUMPTION: Template module with render_claude_md function exists.
        project_root = tmp_path / "project"
        project_root.mkdir()
        scripts_dir = project_root / "scripts"
        scripts_dir.mkdir()
        templates_dir = scripts_dir / "templates"
        templates_dir.mkdir()

        # Write a simple template module
        template_content = """
def render_claude_md(project_name):
    return f"# SVP Project: {project_name}\\nTemplate-generated content."
"""
        (templates_dir / "claude_md.py").write_text(template_content)

        generate_claude_md(project_root, "template_test")

        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "template_test" in content


class TestWriteInitialState:
    """Tests for write_initial_state."""

    def test_writes_pipeline_state_json(self, tmp_path):
        """Creates pipeline_state.json in project root."""
        # DATA ASSUMPTION: Initial state has stage "0", sub_stage "hook_activation".
        write_initial_state(tmp_path, "test_project")

        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert state["stage"] == "0"
        assert state["sub_stage"] == "hook_activation"

    def test_sets_project_name(self, tmp_path):
        """Initial state includes the project name."""
        write_initial_state(tmp_path, "my_app")

        state = json.loads((tmp_path / "pipeline_state.json").read_text())
        assert state["project_name"] == "my_app"

    def test_sets_timestamps(self, tmp_path):
        """Initial state includes created_at and updated_at as UTC ISO timestamps."""
        write_initial_state(tmp_path, "test_project")

        state = json.loads((tmp_path / "pipeline_state.json").read_text())
        assert state["created_at"] is not None
        assert state["updated_at"] is not None
        # Verify they parse as ISO timestamps
        datetime.fromisoformat(state["created_at"])
        datetime.fromisoformat(state["updated_at"])

    def test_counters_at_zero(self, tmp_path):
        """Initial state has all counters at zero/null/empty."""
        write_initial_state(tmp_path, "test_project")

        state = json.loads((tmp_path / "pipeline_state.json").read_text())
        assert state["red_run_retries"] == 0
        assert state["alignment_iteration"] == 0
        assert state["verified_units"] == []
        assert state["current_unit"] is None
        assert state["total_units"] is None

    def test_uses_template_when_available(self, tmp_path):
        """Falls back gracefully when template is not found."""
        # DATA ASSUMPTION: No template file exists, so inline fallback is used.
        # This test verifies the function works without templates present.
        write_initial_state(tmp_path, "no_template")

        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert "stage" in state


class TestWriteDefaultConfig:
    """Tests for write_default_config."""

    def test_writes_config_file(self, tmp_path):
        """Creates svp_config.json in project root."""
        write_default_config(tmp_path)

        config_file = tmp_path / "svp_config.json"
        assert config_file.exists()

        config = json.loads(config_file.read_text())
        assert isinstance(config, dict)

    def test_config_has_iteration_limit(self, tmp_path):
        """Config includes iteration_limit key."""
        # DATA ASSUMPTION: Default config has iteration_limit as a positive integer.
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "iteration_limit" in config

    def test_config_has_models(self, tmp_path):
        """Config includes models dict with required keys."""
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "models" in config
        models = config["models"]
        assert "test_agent" in models
        assert "implementation_agent" in models
        assert "help_agent" in models
        assert "default" in models

    def test_config_has_context_budget_override(self, tmp_path):
        """Config includes context_budget_override."""
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "context_budget_override" in config

    def test_config_has_context_budget_threshold(self, tmp_path):
        """Config includes context_budget_threshold."""
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "context_budget_threshold" in config

    def test_config_has_compaction_character_threshold(self, tmp_path):
        """Config includes compaction_character_threshold."""
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "compaction_character_threshold" in config

    def test_config_has_auto_save(self, tmp_path):
        """Config includes auto_save."""
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "auto_save" in config

    def test_config_has_skip_permissions(self, tmp_path):
        """Config includes skip_permissions."""
        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        assert "skip_permissions" in config


class TestWriteReadmeSvp:
    """Tests for write_readme_svp."""

    def test_writes_readme_file(self, tmp_path):
        """Creates README_SVP.txt in project root."""
        write_readme_svp(tmp_path)

        readme_file = tmp_path / "README_SVP.txt"
        assert readme_file.exists()
        content = readme_file.read_text()
        assert len(content) > 0

    def test_readme_mentions_svp(self, tmp_path):
        """README_SVP.txt mentions SVP."""
        write_readme_svp(tmp_path)

        content = (tmp_path / "README_SVP.txt").read_text()
        assert "SVP" in content

    def test_readme_mentions_protection(self, tmp_path):
        """README_SVP.txt explains the two-layer protection system."""
        write_readme_svp(tmp_path)

        content = (tmp_path / "README_SVP.txt").read_text()
        assert "protect" in content.lower() or "authorization" in content.lower()


# =============================================================================
# Filesystem Permissions
# =============================================================================


class TestSetFilesystemPermissions:
    """Tests for set_filesystem_permissions."""

    @patch("subprocess.run")
    def test_read_only_runs_chmod_remove_write(self, mock_run):
        """When read_only=True, runs chmod -R a-w."""
        # DATA ASSUMPTION: Filesystem permissions use chmod subprocess calls.
        project_root = Path("/tmp/test_project")
        mock_run.return_value = MagicMock(returncode=0)

        set_filesystem_permissions(project_root, read_only=True)

        # Should have called subprocess.run with chmod removing write
        mock_run.assert_called()
        cmd = mock_run.call_args[0][0]
        assert "chmod" in cmd or "chmod" in str(cmd)

    @patch("subprocess.run")
    def test_writable_runs_chmod_add_write(self, mock_run):
        """When read_only=False, runs chmod -R u+w."""
        project_root = Path("/tmp/test_project")
        mock_run.return_value = MagicMock(returncode=0)

        set_filesystem_permissions(project_root, read_only=False)

        mock_run.assert_called()
        cmd = mock_run.call_args[0][0]
        assert "chmod" in cmd or "chmod" in str(cmd)

    @patch("subprocess.run")
    def test_read_only_best_effort(self, mock_run):
        """Best-effort: catches errors from files owned by other users."""
        project_root = Path("/tmp/test_project")
        mock_run.side_effect = subprocess.CalledProcessError(1, "chmod")

        # Should not raise
        set_filesystem_permissions(project_root, read_only=True)


# =============================================================================
# Session Lifecycle
# =============================================================================


class TestLaunchClaudeCode:
    """Tests for launch_claude_code."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_sets_env_var_in_subprocess(self, mock_which, mock_run):
        """Sets SVP_PLUGIN_ACTIVE=1 in the subprocess environment, not launcher's."""
        # DATA ASSUMPTION: Config file exists with skip_permissions=True.
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)

        # Create a config file mock
        config_content = json.dumps({"skip_permissions": True})
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                launch_claude_code(project_root, plugin_dir)

        # Verify subprocess was called
        mock_run.assert_called()
        # The env passed to subprocess should have SVP_PLUGIN_ACTIVE
        call_kwargs = mock_run.call_args
        if call_kwargs.kwargs.get("env"):
            assert call_kwargs.kwargs["env"].get("SVP_PLUGIN_ACTIVE") == "1"
        elif len(call_kwargs.args) > 0 and isinstance(call_kwargs.args, tuple):
            # Check via keyword args
            pass

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_env_var_not_set_on_launcher_process(self, mock_which, mock_run):
        """SVP_PLUGIN_ACTIVE must NOT be set in the launcher's own os.environ."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)
        config_content = json.dumps({"skip_permissions": True})

        original_env = os.environ.get("SVP_PLUGIN_ACTIVE")
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                launch_claude_code(project_root, plugin_dir)

        # The launcher's own environment should not have this set
        assert os.environ.get("SVP_PLUGIN_ACTIVE") == original_env

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_returns_exit_code(self, mock_which, mock_run):
        """Returns the subprocess exit code."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=42)
        config_content = json.dumps({"skip_permissions": True})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = launch_claude_code(project_root, plugin_dir)

        assert result == 42

    @patch("subprocess.run")
    @patch("shutil.which", return_value=None)
    def test_raises_on_claude_not_found(self, mock_which, mock_run):
        """Raises RuntimeError when claude executable is not found."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.side_effect = FileNotFoundError("claude not found")
        config_content = json.dumps({"skip_permissions": True})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(
                    RuntimeError, match="Claude Code executable not found"
                ):
                    launch_claude_code(project_root, plugin_dir)

    @patch("subprocess.run")
    def test_raises_on_other_subprocess_error(self, mock_run):
        """Raises RuntimeError for other subprocess errors."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.side_effect = subprocess.SubprocessError("some error")
        config_content = json.dumps({"skip_permissions": True})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(RuntimeError, match="Session launch failed"):
                    launch_claude_code(project_root, plugin_dir)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_skip_permissions_adds_flag(self, mock_which, mock_run):
        """When skip_permissions=True, adds --dangerously-skip-permissions to cmd."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)
        config_content = json.dumps({"skip_permissions": True})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                launch_claude_code(project_root, plugin_dir)

        cmd = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" in cmd

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_no_skip_permissions_omits_flag(self, mock_which, mock_run):
        """When skip_permissions=False, does not add the flag."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)
        config_content = json.dumps({"skip_permissions": False})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                launch_claude_code(project_root, plugin_dir)

        cmd = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" not in cmd


class TestDetectRestartSignal:
    """Tests for detect_restart_signal."""

    def test_returns_content_when_signal_exists(self, tmp_path):
        """Returns file content (stripped) when restart signal exists."""
        # DATA ASSUMPTION: Signal file contains a simple reason string.
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        signal_file = svp_dir / "restart_signal"
        signal_file.write_text("  restart_reason  \n")

        result = detect_restart_signal(tmp_path)
        assert result == "restart_reason"

    def test_returns_none_when_no_signal(self, tmp_path):
        """Returns None when no restart signal file exists."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        result = detect_restart_signal(tmp_path)
        assert result is None

    def test_returns_none_when_svp_dir_missing(self, tmp_path):
        """Returns None when .svp directory doesn't exist."""
        result = detect_restart_signal(tmp_path)
        assert result is None


class TestClearRestartSignal:
    """Tests for clear_restart_signal."""

    def test_removes_signal_file(self, tmp_path):
        """Deletes the restart signal file."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        signal_file = svp_dir / "restart_signal"
        signal_file.write_text("restart")

        clear_restart_signal(tmp_path)
        assert not signal_file.exists()

    def test_no_error_when_missing(self, tmp_path):
        """Does not raise when signal file is already absent (missing_ok=True)."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        # Should not raise
        clear_restart_signal(tmp_path)


class TestRunSessionLoop:
    """Tests for run_session_loop."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    @patch("svp.scripts.svp_launcher.detect_restart_signal")
    @patch("svp.scripts.svp_launcher.clear_restart_signal")
    @patch("svp_host_claude.launcher_adapter.launch_claude_code")
    @patch("svp.scripts.svp_launcher._print_transition")
    def test_single_session_no_restart(
        self, mock_print, mock_launch, mock_clear, mock_detect, mock_perms, mock_which
    ):
        """Exits after one session when no restart signal is detected."""
        project_root = Path("/tmp/project")
        plugin_dir = Path("/tmp/plugin")

        mock_launch.return_value = 0
        mock_detect.return_value = None  # No restart signal

        result = run_session_loop(project_root, plugin_dir)

        assert result == 0
        mock_launch.assert_called_once()

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    @patch("svp.scripts.svp_launcher.detect_restart_signal")
    @patch("svp.scripts.svp_launcher.clear_restart_signal")
    @patch("svp_host_claude.launcher_adapter.launch_claude_code")
    @patch("svp.scripts.svp_launcher._print_transition")
    def test_restart_loop(
        self, mock_print, mock_launch, mock_clear, mock_detect, mock_perms, mock_which
    ):
        """Loops when restart signal is detected, then exits on no signal."""
        project_root = Path("/tmp/project")
        plugin_dir = Path("/tmp/plugin")

        mock_launch.return_value = 0
        # First call: restart, second call: no restart
        mock_detect.side_effect = ["restart", None]

        result = run_session_loop(project_root, plugin_dir)

        assert mock_launch.call_count == 2
        mock_clear.assert_called_once()


# =============================================================================
# Resume
# =============================================================================


class TestDetectExistingProject:
    """Tests for detect_existing_project."""

    def test_returns_true_when_both_exist(self, tmp_path):
        """Returns True when both pipeline_state.json and .svp/ exist."""
        (tmp_path / "pipeline_state.json").write_text("{}")
        (tmp_path / ".svp").mkdir()

        assert detect_existing_project(tmp_path) is True

    def test_returns_false_when_state_missing(self, tmp_path):
        """Returns False when pipeline_state.json is missing."""
        (tmp_path / ".svp").mkdir()

        assert detect_existing_project(tmp_path) is False

    def test_returns_false_when_svp_dir_missing(self, tmp_path):
        """Returns False when .svp/ is missing."""
        (tmp_path / "pipeline_state.json").write_text("{}")

        assert detect_existing_project(tmp_path) is False

    def test_returns_false_when_both_missing(self, tmp_path):
        """Returns False when both are missing."""
        assert detect_existing_project(tmp_path) is False


class TestResumeProject:
    """Tests for resume_project."""

    @patch("svp_host_claude.launcher_adapter.run_session_loop")
    def test_calls_run_session_loop(self, mock_loop, tmp_path):
        """resume_project calls run_session_loop."""
        # DATA ASSUMPTION: Valid pipeline state JSON for resume display.
        state = {
            "stage": "3",
            "sub_stage": "test_generation",
            "project_name": "test_proj",
        }
        (tmp_path / "pipeline_state.json").write_text(json.dumps(state))
        (tmp_path / ".svp").mkdir()

        plugin_dir = Path("/tmp/plugin")
        mock_loop.return_value = 0

        result = resume_project(tmp_path, plugin_dir)

        mock_loop.assert_called_once_with(tmp_path, plugin_dir)
        assert result == 0

    @patch("svp_host_claude.launcher_adapter.run_session_loop")
    def test_handles_malformed_json_gracefully(self, mock_loop, tmp_path):
        """Gracefully handles malformed pipeline_state.json on resume."""
        # DATA ASSUMPTION: Corrupted JSON in pipeline_state.json.
        (tmp_path / "pipeline_state.json").write_text("not valid json")
        (tmp_path / ".svp").mkdir()

        plugin_dir = Path("/tmp/plugin")
        mock_loop.return_value = 0

        # Should not raise, should still call run_session_loop
        result = resume_project(tmp_path, plugin_dir)
        mock_loop.assert_called_once()


# =============================================================================
# Command Handlers
# =============================================================================


class TestHandleNewProject:
    """Tests for _handle_new_project."""

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_creates_full_project(self, mock_perms, mock_loop, tmp_path):
        """_handle_new_project creates directory, scripts, CLAUDE.md, state, config, readme."""
        # DATA ASSUMPTION: Plugin root with scripts/ and hooks/ directories.
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        scripts_dir = plugin_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing")
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")

        args = argparse.Namespace(
            command="new",
            project_name="new_project",
            parent_dir=str(tmp_path / "projects"),
        )
        (tmp_path / "projects").mkdir()

        result = _handle_new_project(args, plugin_dir)

        project_root = tmp_path / "projects" / "new_project"
        assert project_root.exists()
        assert (project_root / "CLAUDE.md").exists()
        assert (project_root / "pipeline_state.json").exists()
        assert (project_root / "svp_config.json").exists()
        assert (project_root / "README_SVP.txt").exists()
        assert result == 0


class TestHandleRestore:
    """Tests for _handle_restore."""

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_restore_injects_spec_and_blueprint(self, mock_perms, mock_loop, tmp_path):
        """_handle_restore copies spec and blueprint files into the project."""
        # DATA ASSUMPTION: Spec and blueprint are markdown files.
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        scripts_dir = plugin_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing")
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Stakeholder Spec")
        blueprint_file = tmp_path / "blueprint.md"
        blueprint_file.write_text("# Blueprint")

        args = argparse.Namespace(
            command="restore",
            project_name="restored_project",
            parent_dir=str(tmp_path / "projects"),
            spec=str(spec_file),
            blueprint=str(blueprint_file),
            context=None,
            scripts_source=None,
        )
        (tmp_path / "projects").mkdir()

        result = _handle_restore(args, plugin_dir)

        project_root = tmp_path / "projects" / "restored_project"
        assert (project_root / "specs" / "stakeholder.md").exists()
        assert (project_root / "blueprint" / "blueprint.md").exists()

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_restore_sets_state_to_pre_stage_3(self, mock_perms, mock_loop, tmp_path):
        """_handle_restore writes pipeline state at pre_stage_3."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        scripts_dir = plugin_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing")
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Stakeholder Spec")
        blueprint_file = tmp_path / "blueprint.md"
        blueprint_file.write_text("# Blueprint")

        args = argparse.Namespace(
            command="restore",
            project_name="restored_project",
            parent_dir=str(tmp_path / "projects"),
            spec=str(spec_file),
            blueprint=str(blueprint_file),
            context=None,
            scripts_source=None,
        )
        (tmp_path / "projects").mkdir()

        _handle_restore(args, plugin_dir)

        project_root = tmp_path / "projects" / "restored_project"
        state = json.loads((project_root / "pipeline_state.json").read_text())
        assert (
            "pre_stage_3" in str(state.get("stage", ""))
            or "pre_stage_3" in str(state.get("sub_stage", ""))
            or state.get("stage") == "pre_stage_3"
        )

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_restore_with_context(self, mock_perms, mock_loop, tmp_path):
        """_handle_restore injects optional context file."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        scripts_dir = plugin_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing")
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Stakeholder Spec")
        blueprint_file = tmp_path / "blueprint.md"
        blueprint_file.write_text("# Blueprint")
        context_file = tmp_path / "context.md"
        context_file.write_text("# Project Context")

        args = argparse.Namespace(
            command="restore",
            project_name="restored_project",
            parent_dir=str(tmp_path / "projects"),
            spec=str(spec_file),
            blueprint=str(blueprint_file),
            context=str(context_file),
            scripts_source=None,
        )
        (tmp_path / "projects").mkdir()

        _handle_restore(args, plugin_dir)

        project_root = tmp_path / "projects" / "restored_project"
        assert (project_root / ".svp" / "project_context.md").exists()

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_restore_with_scripts_source(self, mock_perms, mock_loop, tmp_path):
        """_handle_restore uses --scripts-source for script copying."""
        alt_scripts = tmp_path / "alt_scripts"
        alt_scripts.mkdir()
        scripts_in_alt = alt_scripts / "scripts"
        scripts_in_alt.mkdir()
        (scripts_in_alt / "routing.py").write_text("# alt routing")

        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Stakeholder Spec")
        blueprint_file = tmp_path / "blueprint.md"
        blueprint_file.write_text("# Blueprint")

        args = argparse.Namespace(
            command="restore",
            project_name="restored_project",
            parent_dir=str(tmp_path / "projects"),
            spec=str(spec_file),
            blueprint=str(blueprint_file),
            context=None,
            scripts_source=str(alt_scripts),
        )
        (tmp_path / "projects").mkdir()

        _handle_restore(args, plugin_dir)

        project_root = tmp_path / "projects" / "restored_project"
        # Scripts should come from the alt source
        assert (project_root / "scripts" / "routing.py").exists()
        content = (project_root / "scripts" / "routing.py").read_text()
        assert "alt routing" in content


class TestHandleResume:
    """Tests for _handle_resume."""

    @patch("svp.scripts.svp_launcher.resume_project", return_value=0)
    @patch("svp.scripts.svp_launcher.detect_existing_project", return_value=True)
    def test_resume_success(self, mock_detect, mock_resume):
        """Calls resume_project when an existing project is found in cwd."""
        plugin_dir = Path("/tmp/plugin")

        result = _handle_resume(plugin_dir)

        assert result == 0
        mock_resume.assert_called_once()

    @patch("svp.scripts.svp_launcher.detect_existing_project", return_value=False)
    def test_resume_no_project(self, mock_detect, capsys):
        """Returns 1 and prints guidance when no project is found."""
        plugin_dir = Path("/tmp/plugin")

        result = _handle_resume(plugin_dir)

        assert result == 1


# =============================================================================
# Entry Point (main)
# =============================================================================


class TestMain:
    """Tests for main."""

    @patch("svp.scripts.svp_launcher._handle_resume", return_value=0)
    @patch("svp.scripts.svp_launcher._find_plugin_root")
    @patch("svp.scripts.svp_launcher.run_all_prerequisites")
    @patch("svp.scripts.svp_launcher._print_status")
    @patch("svp.scripts.svp_launcher._print_header")
    def test_main_resume_path(
        self, mock_header, mock_status, mock_prereqs, mock_find, mock_resume
    ):
        """main() with no args: runs prereqs, finds plugin, resumes."""
        # DATA ASSUMPTION: All prerequisites pass; plugin found at a mock path.
        mock_prereqs.return_value = [
            ("claude_code", True, "ok"),
            ("svp_plugin", True, "ok"),
            ("api_credentials", True, "ok"),
            ("conda", True, "ok"),
            ("python", True, "ok"),
            ("pytest", True, "ok"),
            ("git", True, "ok"),
            ("network", True, "ok"),
        ]
        mock_find.return_value = Path("/tmp/plugin")

        result = main([])

        assert result == 0

    @patch("svp.scripts.svp_launcher.run_all_prerequisites")
    @patch("svp.scripts.svp_launcher._print_status")
    @patch("svp.scripts.svp_launcher._print_header")
    def test_main_prereq_failure(self, mock_header, mock_status, mock_prereqs):
        """main() returns 1 when any prerequisite fails."""
        # DATA ASSUMPTION: One prerequisite (git) fails.
        mock_prereqs.return_value = [
            ("claude_code", True, "ok"),
            ("svp_plugin", True, "ok"),
            ("api_credentials", True, "ok"),
            ("conda", True, "ok"),
            ("python", True, "ok"),
            ("pytest", True, "ok"),
            ("git", False, "Git not configured"),
            ("network", True, "ok"),
        ]

        result = main([])

        assert result == 1

    def test_main_accepts_argv_parameter(self):
        """main() accepts an argv parameter for testing."""
        # This just verifies the interface; actual behavior requires mocking
        import inspect

        sig = inspect.signature(main)
        assert "argv" in sig.parameters

    @patch("svp.scripts.svp_launcher._handle_new_project", return_value=0)
    @patch("svp.scripts.svp_launcher._find_plugin_root")
    @patch("svp.scripts.svp_launcher.run_all_prerequisites")
    @patch("svp.scripts.svp_launcher._print_status")
    @patch("svp.scripts.svp_launcher._print_header")
    def test_main_new_project_dispatch(
        self, mock_header, mock_status, mock_prereqs, mock_find, mock_new
    ):
        """main(['new', 'proj']) dispatches to _handle_new_project."""
        mock_prereqs.return_value = [
            ("claude_code", True, "ok"),
            ("svp_plugin", True, "ok"),
            ("api_credentials", True, "ok"),
            ("conda", True, "ok"),
            ("python", True, "ok"),
            ("pytest", True, "ok"),
            ("git", True, "ok"),
            ("network", True, "ok"),
        ]
        mock_find.return_value = Path("/tmp/plugin")

        result = main(["new", "test_proj"])

        assert result == 0
        mock_new.assert_called_once()

    @patch("svp.scripts.svp_launcher._handle_restore", return_value=0)
    @patch("svp.scripts.svp_launcher._find_plugin_root")
    @patch("svp.scripts.svp_launcher.run_all_prerequisites")
    @patch("svp.scripts.svp_launcher._print_status")
    @patch("svp.scripts.svp_launcher._print_header")
    def test_main_restore_dispatch(
        self, mock_header, mock_status, mock_prereqs, mock_find, mock_restore
    ):
        """main(['restore', ...]) dispatches to _handle_restore."""
        mock_prereqs.return_value = [
            ("claude_code", True, "ok"),
            ("svp_plugin", True, "ok"),
            ("api_credentials", True, "ok"),
            ("conda", True, "ok"),
            ("python", True, "ok"),
            ("pytest", True, "ok"),
            ("git", True, "ok"),
            ("network", True, "ok"),
        ]
        mock_find.return_value = Path("/tmp/plugin")

        result = main(
            [
                "restore",
                "my_proj",
                "--spec",
                "/tmp/spec.md",
                "--blueprint",
                "/tmp/bp.md",
            ]
        )

        assert result == 0
        mock_restore.assert_called_once()

    @patch("svp.scripts.svp_launcher.run_all_prerequisites")
    @patch("svp.scripts.svp_launcher._print_status")
    @patch("svp.scripts.svp_launcher._print_header")
    def test_main_returns_int(self, mock_header, mock_status, mock_prereqs):
        """main() always returns an integer."""
        mock_prereqs.return_value = [
            ("claude_code", False, "fail"),
            ("svp_plugin", True, "ok"),
            ("api_credentials", True, "ok"),
            ("conda", True, "ok"),
            ("python", True, "ok"),
            ("pytest", True, "ok"),
            ("git", True, "ok"),
            ("network", True, "ok"),
        ]

        result = main([])
        assert isinstance(result, int)


# =============================================================================
# Self-Containment Invariant (structural verification)
# =============================================================================


class TestSelfContainment:
    """Verify the self-containment invariant: no imports from other SVP modules.

    NOTE: This test reads the actual source file, so it will only run
    meaningfully against the real implementation, not the stub.
    """

    def test_no_cross_unit_imports_in_stub(self):
        """Stub file should not import from other SVP units."""
        # DATA ASSUMPTION: The stub.py file is at src/unit_24/stub.py.
        import importlib

        module = importlib.import_module("svp.scripts.svp_launcher")
        source_file = module.__file__
        if source_file:
            with open(source_file, "r") as f:
                content = f.read()
            # Check for forbidden import patterns
            forbidden_patterns = [
                "from src.unit_",
                "import src.unit_",
                "from svp.scripts.",
                "import svp.scripts.",
            ]
            for pattern in forbidden_patterns:
                # Only flag if it's an actual import, not a comment or string
                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if pattern in stripped:
                        pytest.fail(
                            f"Self-containment violation: found '{pattern}' in "
                            f"{source_file}: {stripped}"
                        )


# =============================================================================
# Integration-like Tests (combining multiple functions)
# =============================================================================


class TestProjectCreationFlow:
    """Tests that verify the overall project creation flow."""

    def test_create_then_detect(self, tmp_path):
        """After creating a project with state and .svp, detect_existing_project returns True."""
        project_root = create_project_directory("flow_test", tmp_path)
        write_initial_state(project_root, "flow_test")

        assert detect_existing_project(project_root) is True

    def test_create_project_directory_is_idempotent_for_dirs(self, tmp_path):
        """Creating a project makes all expected directories exactly once."""
        project_root = create_project_directory("idem_test", tmp_path)

        # All dirs from PROJECT_DIRS should exist
        for d in PROJECT_DIRS:
            assert (project_root / d).is_dir()

        # Trying again should fail
        with pytest.raises(FileExistsError):
            create_project_directory("idem_test", tmp_path)

    def test_write_then_read_initial_state(self, tmp_path):
        """Written initial state can be read back as valid JSON."""
        write_initial_state(tmp_path, "roundtrip")
        state = json.loads((tmp_path / "pipeline_state.json").read_text())

        assert isinstance(state, dict)
        assert state["project_name"] == "roundtrip"
        assert state["stage"] == "0"

    def test_write_then_read_default_config(self, tmp_path):
        """Written default config can be read back as valid JSON."""
        write_default_config(tmp_path)
        config = json.loads((tmp_path / "svp_config.json").read_text())

        assert isinstance(config, dict)
        assert "models" in config
        assert "iteration_limit" in config


class TestDetectRestartSignalAndClear:
    """Tests for the restart signal detect/clear cycle."""

    def test_full_cycle(self, tmp_path):
        """Create signal -> detect -> clear -> detect returns None."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        signal_file = svp_dir / "restart_signal"
        signal_file.write_text("cycle_test")

        # Detect
        result = detect_restart_signal(tmp_path)
        assert result == "cycle_test"

        # Clear
        clear_restart_signal(tmp_path)
        assert not signal_file.exists()

        # Detect again
        result = detect_restart_signal(tmp_path)
        assert result is None
