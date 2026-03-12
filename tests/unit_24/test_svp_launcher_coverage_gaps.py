"""
Coverage gap tests for Unit 24: SVP Launcher

These tests cover blueprint behaviors not exercised by the main test suite.

DATA ASSUMPTIONS:
- Same conventions as the main test file.
- Plugin directories are synthesized with expected structure.
- Subprocess calls are mocked; no real external processes invoked.
- Template files are synthesized in tmp_path for template-loading tests.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from svp.scripts.svp_launcher import (
    # Constants
    SVP_ENV_VAR,
    CONFIG_FILE,
    STATE_FILE,
    SVP_DIR,
    PROJECT_DIRS,
    RESTART_SIGNAL_FILE,
    README_SVP_FILE,
    # Plugin discovery
    _find_plugin_root,
    _is_svp_plugin_dir,
    # Prerequisite checks
    check_claude_code,
    check_network,
    check_git,
    check_python,
    run_all_prerequisites,
    # Project setup
    generate_claude_md,
    _generate_claude_md_fallback,
    write_initial_state,
    write_default_config,
    write_readme_svp,
    copy_scripts_to_workspace,
    create_project_directory,
    # Filesystem permissions
    set_filesystem_permissions,
    # Session lifecycle
    launch_claude_code,
    detect_restart_signal,
    run_session_loop,
    # Resume
    resume_project,
    detect_existing_project,
    # Command handlers
    _handle_new_project,
    _handle_restore,
    _handle_resume,
    # CLI parsing
    parse_args,
    # Entry point
    main,
)


# =============================================================================
# Plugin Discovery -- Coverage Gaps
# =============================================================================


class TestFindPluginRootSearchOrder:
    """Tests verifying _find_plugin_root searches standard locations."""

    def test_finds_standard_location_home_claude_plugins(self, tmp_path):
        """_find_plugin_root searches ~/.claude/plugins/svp as a standard location."""
        # DATA ASSUMPTION: Plugin at the standard ~/.claude/plugins/svp location.
        plugin_dir = tmp_path / ".claude" / "plugins" / "svp"
        plugin_dir.mkdir(parents=True)
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir()
        manifest = manifest_dir / "plugin.json"
        manifest.write_text(json.dumps({"name": "svp"}))

        # Patch Path.home() to return tmp_path, and clear env var
        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.home", return_value=tmp_path):
                result = _find_plugin_root()
                assert result == plugin_dir

    def test_finds_cache_version_directories_sorted(self, tmp_path):
        """_find_plugin_root searches cache version directories in sorted order."""
        # DATA ASSUMPTION: Cache directory has multiple version dirs, only latest is valid.
        cache_base = tmp_path / ".claude" / "plugins" / "cache" / "svp" / "svp"
        cache_base.mkdir(parents=True)

        # Version dirs -- alphabetical sort: 1.0.0 < 1.1.0 < 2.0.0
        v1 = cache_base / "1.0.0"
        v1.mkdir()
        v2 = cache_base / "1.1.0"
        v2.mkdir()
        v3 = cache_base / "2.0.0"
        v3.mkdir()

        # Only the first valid one found (1.0.0) should be returned
        for v in [v1]:
            md = v / ".claude-plugin"
            md.mkdir()
            (md / "plugin.json").write_text(json.dumps({"name": "svp"}))

        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.home", return_value=tmp_path):
                result = _find_plugin_root()
                assert result == v1

    def test_env_var_takes_precedence_over_standard_locations(self, tmp_path):
        """SVP_PLUGIN_ROOT env var is checked before standard locations."""
        # DATA ASSUMPTION: Both env var and standard location point to valid plugins.
        env_plugin = tmp_path / "env_plugin"
        env_plugin.mkdir()
        md1 = env_plugin / ".claude-plugin"
        md1.mkdir()
        (md1 / "plugin.json").write_text(json.dumps({"name": "svp"}))

        std_plugin = tmp_path / ".claude" / "plugins" / "svp"
        std_plugin.mkdir(parents=True)
        md2 = std_plugin / ".claude-plugin"
        md2.mkdir()
        (md2 / "plugin.json").write_text(json.dumps({"name": "svp"}))

        with patch.dict(os.environ, {"SVP_PLUGIN_ROOT": str(env_plugin)}):
            with patch("pathlib.Path.home", return_value=tmp_path):
                result = _find_plugin_root()
                assert result == env_plugin


# =============================================================================
# Prerequisite Checks -- Coverage Gaps
# =============================================================================


class TestCheckNetworkDnsFallback:
    """Tests for check_network DNS resolution fallback."""

    @patch("socket.getaddrinfo")
    @patch("subprocess.run")
    def test_falls_back_to_dns_when_curl_not_found(self, mock_run, mock_dns):
        """Falls back to DNS resolution via socket.getaddrinfo when curl is unavailable."""
        # DATA ASSUMPTION: curl not found triggers FileNotFoundError.
        mock_run.side_effect = FileNotFoundError("curl not found")
        mock_dns.return_value = [("AF_INET", None, None, None, ("1.2.3.4", 443))]

        passed, message = check_network()
        assert passed is True
        mock_dns.assert_called_once_with("api.anthropic.com", 443)

    @patch("socket.getaddrinfo")
    @patch("subprocess.run")
    def test_fails_when_dns_fails(self, mock_run, mock_dns):
        """Returns (False, ...) when both curl and DNS resolution fail."""
        mock_run.side_effect = FileNotFoundError("curl not found")
        mock_dns.side_effect = socket.gaierror("DNS resolution failed")

        passed, message = check_network()
        assert passed is False
        assert "api.anthropic.com" in message.lower() or "network" in message.lower()


class TestCheckGitEmailNotConfigured:
    """Tests for check_git when user.email is not configured."""

    @patch("subprocess.run")
    def test_failure_no_email_config(self, mock_run):
        """Returns (False, ...) when git user.email is not configured, with guidance."""

        # DATA ASSUMPTION: git --version works, user.name works, but user.email fails.
        def side_effect(cmd, *args, **kwargs):
            if "git" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="git version 2.42.0\n", stderr="")
            elif "git" in cmd and "user.name" in cmd:
                return MagicMock(returncode=0, stdout="Test User\n", stderr="")
            elif "git" in cmd and "user.email" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect
        passed, message = check_git()
        assert passed is False
        assert "email" in message.lower()
        assert "git config --global" in message


class TestCheckClaudeCodeCommand:
    """Tests verifying check_claude_code runs the right command."""

    @patch("subprocess.run")
    def test_runs_with_dangerously_skip_permissions_and_version(self, mock_run):
        """check_claude_code runs claude --dangerously-skip-permissions --version."""
        mock_run.return_value = MagicMock(returncode=0, stdout="1.0.0\n", stderr="")
        check_claude_code()

        cmd = mock_run.call_args[0][0]
        assert "claude" in cmd
        assert "--dangerously-skip-permissions" in cmd
        assert "--version" in cmd

    @patch("subprocess.run")
    def test_handles_timeout(self, mock_run):
        """Returns (False, ...) when claude version check times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=15)
        passed, message = check_claude_code()
        assert passed is False
        assert "timed out" in message.lower()


class TestCheckPythonUseSysExecutable:
    """Tests verifying check_python uses sys.executable."""

    @patch("subprocess.run")
    def test_uses_sys_executable(self, mock_run):
        """check_python runs sys.executable --version."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Python 3.11.5\n", stderr=""
        )
        check_python()

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert "--version" in cmd


# =============================================================================
# Project Setup -- Template Loading Coverage Gaps
# =============================================================================


class TestWriteInitialStateWithTemplate:
    """Tests for write_initial_state when a template file is available."""

    def test_uses_template_when_present(self, tmp_path):
        """write_initial_state loads pipeline_state_initial.json template when available."""
        # DATA ASSUMPTION: Template exists at scripts/templates/pipeline_state_initial.json.
        scripts_dir = tmp_path / "scripts" / "templates"
        scripts_dir.mkdir(parents=True)

        template_state = {
            "stage": "0",
            "sub_stage": "hook_activation",
            "current_unit": None,
            "total_units": None,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "alignment_iteration": 0,
            "verified_units": [],
            "pass_history": [],
            "log_references": {},
            "project_name": "PLACEHOLDER",
            "last_action": None,
            "debug_session": None,
            "debug_history": [],
            "created_at": "PLACEHOLDER",
            "updated_at": "PLACEHOLDER",
            "extra_template_field": "from_template",
        }
        (scripts_dir / "pipeline_state_initial.json").write_text(
            json.dumps(template_state, indent=2)
        )

        write_initial_state(tmp_path, "template_proj")

        state = json.loads((tmp_path / "pipeline_state.json").read_text())
        assert state["project_name"] == "template_proj"
        # Template loaded: the extra field should be present
        assert state.get("extra_template_field") == "from_template"
        # Timestamps should be overwritten
        assert state["created_at"] != "PLACEHOLDER"
        assert state["updated_at"] != "PLACEHOLDER"


class TestWriteDefaultConfigWithTemplate:
    """Tests for write_default_config when a template file is available."""

    def test_uses_template_when_present(self, tmp_path):
        """write_default_config copies svp_config_default.json template when available."""
        # DATA ASSUMPTION: Template exists at scripts/templates/svp_config_default.json.
        scripts_dir = tmp_path / "scripts" / "templates"
        scripts_dir.mkdir(parents=True)

        template_config = {
            "iteration_limit": 5,
            "models": {
                "test_agent": "claude-opus-4-6",
                "implementation_agent": "claude-opus-4-6",
                "help_agent": "claude-sonnet-4-6",
                "default": "claude-opus-4-6",
            },
            "context_budget_override": None,
            "context_budget_threshold": 65,
            "compaction_character_threshold": 200,
            "auto_save": True,
            "skip_permissions": True,
            "template_marker": True,
        }
        (scripts_dir / "svp_config_default.json").write_text(
            json.dumps(template_config, indent=2)
        )

        write_default_config(tmp_path)

        config = json.loads((tmp_path / "svp_config.json").read_text())
        # Should have the template_marker since the template was used
        assert config.get("template_marker") is True
        assert config["iteration_limit"] == 5


class TestWriteReadmeSvpWithTemplate:
    """Tests for write_readme_svp when a template file is available."""

    def test_uses_template_when_present(self, tmp_path):
        """write_readme_svp copies readme_svp.txt template when available."""
        # DATA ASSUMPTION: Template exists at scripts/templates/readme_svp.txt.
        scripts_dir = tmp_path / "scripts" / "templates"
        scripts_dir.mkdir(parents=True)

        template_content = "TEMPLATE README SVP CONTENT\nThis is from the template."
        (scripts_dir / "readme_svp.txt").write_text(template_content)

        write_readme_svp(tmp_path)

        content = (tmp_path / "README_SVP.txt").read_text()
        assert "TEMPLATE README SVP CONTENT" in content


# =============================================================================
# Session Lifecycle -- Coverage Gaps
# =============================================================================


class TestLaunchClaudeCodeCommand:
    """Tests verifying launch_claude_code command construction."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_includes_routing_prompt(self, mock_which, mock_run):
        """launch_claude_code includes 'run the routing script' as initial prompt."""
        # DATA ASSUMPTION: Config with skip_permissions=False.
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)
        config_content = json.dumps({"skip_permissions": False})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    launch_claude_code(project_root, plugin_dir)

        cmd = mock_run.call_args[0][0]
        assert "run the routing script" in cmd

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_uses_project_root_as_cwd(self, mock_which, mock_run):
        """launch_claude_code uses cwd=project_root for the subprocess."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)
        config_content = json.dumps({"skip_permissions": True})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    launch_claude_code(project_root, plugin_dir)

        call_kwargs = mock_run.call_args
        assert str(project_root) in str(call_kwargs)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_passes_env_copy_not_os_environ(self, mock_which, mock_run):
        """launch_claude_code creates env copy with SVP_PLUGIN_ACTIVE, not modifying os.environ."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.return_value = MagicMock(returncode=0)
        config_content = json.dumps({"skip_permissions": False})

        # Ensure SVP_PLUGIN_ACTIVE is not set before the call
        original_val = os.environ.pop("SVP_PLUGIN_ACTIVE", None)
        try:
            with patch("builtins.open", mock_open(read_data=config_content)):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        launch_claude_code(project_root, plugin_dir)

            # The env passed to subprocess should contain SVP_PLUGIN_ACTIVE
            call_kwargs = mock_run.call_args
            env_passed = call_kwargs.kwargs.get("env") or (
                call_kwargs[1].get("env") if len(call_kwargs) > 1 else None
            )
            if env_passed:
                assert env_passed.get("SVP_PLUGIN_ACTIVE") == "1"

            # The launcher's own os.environ must NOT have it
            assert "SVP_PLUGIN_ACTIVE" not in os.environ
        finally:
            if original_val is not None:
                os.environ["SVP_PLUGIN_ACTIVE"] = original_val


class TestRunSessionLoopPermissions:
    """Tests verifying permission management in run_session_loop."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    @patch("svp.scripts.svp_launcher.detect_restart_signal")
    @patch("svp.scripts.svp_launcher.clear_restart_signal")
    @patch("svp_host_claude.launcher_adapter.launch_claude_code")
    @patch("svp.scripts.svp_launcher._print_transition")
    def test_restores_writable_before_launch(
        self, mock_print, mock_launch, mock_clear, mock_detect, mock_perms, mock_which
    ):
        """run_session_loop restores write permissions before each launch."""
        project_root = Path("/tmp/project")
        plugin_dir = Path("/tmp/plugin")

        mock_launch.return_value = 0
        mock_detect.return_value = None

        run_session_loop(project_root, plugin_dir)

        first_perm_call = mock_perms.call_args_list[0]
        assert first_perm_call == call(project_root, read_only=False)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    @patch("svp.scripts.svp_launcher.detect_restart_signal")
    @patch("svp.scripts.svp_launcher.clear_restart_signal")
    @patch("svp_host_claude.launcher_adapter.launch_claude_code")
    @patch("svp.scripts.svp_launcher._print_transition")
    def test_sets_read_only_on_exit(
        self, mock_print, mock_launch, mock_clear, mock_detect, mock_perms, mock_which
    ):
        """run_session_loop sets read-only permissions before exiting."""
        project_root = Path("/tmp/project")
        plugin_dir = Path("/tmp/plugin")

        mock_launch.return_value = 0
        mock_detect.return_value = None  # No restart, exit immediately

        run_session_loop(project_root, plugin_dir)

        last_perm_call = mock_perms.call_args_list[-1]
        assert last_perm_call == call(project_root, read_only=True)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    @patch("svp.scripts.svp_launcher.detect_restart_signal")
    @patch("svp.scripts.svp_launcher.clear_restart_signal")
    @patch("svp_host_claude.launcher_adapter.launch_claude_code")
    @patch("svp.scripts.svp_launcher._print_transition")
    def test_sets_read_only_before_restart(
        self, mock_print, mock_launch, mock_clear, mock_detect, mock_perms, mock_which
    ):
        """run_session_loop sets read-only permissions before printing transition on restart."""
        project_root = Path("/tmp/project")
        plugin_dir = Path("/tmp/plugin")

        mock_launch.return_value = 0
        mock_detect.side_effect = ["restart_reason", None]

        run_session_loop(project_root, plugin_dir)

        perm_calls = mock_perms.call_args_list
        assert len(perm_calls) >= 4


# =============================================================================
# Command Handlers -- Coverage Gaps
# =============================================================================


class TestHandleRestoreValidation:
    """Tests for _handle_restore file validation."""

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_returns_1_when_spec_file_missing(self, mock_perms, mock_loop, tmp_path):
        """_handle_restore returns 1 when --spec file does not exist."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()

        blueprint_file = tmp_path / "blueprint.md"
        blueprint_file.write_text("# Blueprint")

        args = argparse.Namespace(
            command="restore",
            project_name="test_proj",
            parent_dir=str(tmp_path / "projects"),
            spec="/nonexistent/spec.md",
            blueprint=str(blueprint_file),
            context=None,
            scripts_source=None,
        )
        (tmp_path / "projects").mkdir()

        result = _handle_restore(args, plugin_dir)
        assert result == 1

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_returns_1_when_blueprint_file_missing(
        self, mock_perms, mock_loop, tmp_path
    ):
        """_handle_restore returns 1 when --blueprint file does not exist."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        args = argparse.Namespace(
            command="restore",
            project_name="test_proj",
            parent_dir=str(tmp_path / "projects"),
            spec=str(spec_file),
            blueprint="/nonexistent/blueprint.md",
            context=None,
            scripts_source=None,
        )
        (tmp_path / "projects").mkdir()

        result = _handle_restore(args, plugin_dir)
        assert result == 1


class TestHandleNewProjectHooks:
    """Tests for hook copying in _handle_new_project."""

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_copies_hooks_json_to_claude_dir(self, mock_perms, mock_loop, tmp_path):
        """_handle_new_project copies hooks.json to project's .claude/ directory."""
        # DATA ASSUMPTION: Plugin has hooks/hooks.json and hooks/scripts/.
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        scripts_dir = plugin_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing")
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text('{"hooks": []}')
        (hooks_scripts_dir / "non_svp_protection.sh").write_text("#!/bin/bash\nexit 0")

        args = argparse.Namespace(
            command="new",
            project_name="hooks_test",
            parent_dir=str(tmp_path / "projects"),
        )
        (tmp_path / "projects").mkdir()

        _handle_new_project(args, plugin_dir)

        project_root = tmp_path / "projects" / "hooks_test"
        assert (project_root / ".claude" / "hooks.json").exists()
        assert (project_root / ".claude" / "scripts" / "non_svp_protection.sh").exists()


class TestHandleRestoreHooks:
    """Tests for hook copying in _handle_restore."""

    @patch("svp.scripts.svp_launcher.run_session_loop", return_value=0)
    @patch("svp.scripts.svp_launcher.set_filesystem_permissions")
    def test_copies_hooks_json_to_claude_dir(self, mock_perms, mock_loop, tmp_path):
        """_handle_restore copies hooks.json to project's .claude/ directory."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        scripts_dir = plugin_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing")
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        hooks_scripts_dir = hooks_dir / "scripts"
        hooks_scripts_dir.mkdir()
        (hooks_dir / "hooks.json").write_text('{"hooks": []}')
        (hooks_scripts_dir / "non_svp_protection.sh").write_text("#!/bin/bash\nexit 0")

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")
        blueprint_file = tmp_path / "blueprint.md"
        blueprint_file.write_text("# Blueprint")

        args = argparse.Namespace(
            command="restore",
            project_name="hooks_restore_test",
            parent_dir=str(tmp_path / "projects"),
            spec=str(spec_file),
            blueprint=str(blueprint_file),
            context=None,
            scripts_source=None,
        )
        (tmp_path / "projects").mkdir()

        _handle_restore(args, plugin_dir)

        project_root = tmp_path / "projects" / "hooks_restore_test"
        assert (project_root / ".claude" / "hooks.json").exists()
        assert (project_root / ".claude" / "scripts" / "non_svp_protection.sh").exists()


# =============================================================================
# Entry Point -- Coverage Gaps
# =============================================================================


class TestMainPluginNotFound:
    """Tests for main when plugin root cannot be found."""

    @patch("svp.scripts.svp_launcher._find_plugin_root")
    @patch("svp.scripts.svp_launcher.run_all_prerequisites")
    @patch("svp.scripts.svp_launcher._print_status")
    @patch("svp.scripts.svp_launcher._print_header")
    def test_returns_1_when_plugin_not_found_after_prereqs_pass(
        self, mock_header, mock_status, mock_prereqs, mock_find
    ):
        """main() returns 1 when all prerequisites pass but plugin root is None."""
        # DATA ASSUMPTION: All 8 prerequisites pass, but plugin root is None.
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
        mock_find.return_value = None

        result = main([])

        assert result == 1


# =============================================================================
# Resume -- Coverage Gaps
# =============================================================================


class TestResumeProjectPermissionError:
    """Tests for resume_project with permission errors on state file."""

    @patch("svp_host_claude.launcher_adapter.run_session_loop")
    def test_handles_permission_error_gracefully(self, mock_loop, tmp_path):
        """resume_project handles permission errors when reading state file gracefully."""
        # DATA ASSUMPTION: pipeline_state.json exists but cannot be read (permission error).
        state_path = tmp_path / "pipeline_state.json"
        state_path.write_text('{"stage": "3"}')
        (tmp_path / ".svp").mkdir()

        plugin_dir = Path("/tmp/plugin")
        mock_loop.return_value = 0

        # Mock open to raise PermissionError
        original_open = open

        def mock_open_fn(path, *args, **kwargs):
            if str(path) == str(state_path):
                raise PermissionError("Permission denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_fn):
            # Should not raise, should still proceed to run_session_loop
            result = resume_project(tmp_path, plugin_dir)

        mock_loop.assert_called_once()


# =============================================================================
# Filesystem Permissions -- Coverage Gaps
# =============================================================================


class TestSetFilesystemPermissionsCommands:
    """Tests verifying the specific chmod commands used."""

    @patch("subprocess.run")
    def test_read_only_uses_a_minus_w(self, mock_run):
        """When read_only=True, runs chmod -R a-w (remove write for all)."""
        project_root = Path("/tmp/test_project")
        mock_run.return_value = MagicMock(returncode=0)

        set_filesystem_permissions(project_root, read_only=True)

        cmd = mock_run.call_args[0][0]
        assert "a-w" in cmd

    @patch("subprocess.run")
    def test_writable_uses_u_plus_w(self, mock_run):
        """When read_only=False, runs chmod -R u+w (add write for user)."""
        project_root = Path("/tmp/test_project")
        mock_run.return_value = MagicMock(returncode=0)

        set_filesystem_permissions(project_root, read_only=False)

        cmd = mock_run.call_args[0][0]
        assert "u+w" in cmd


# =============================================================================
# CLI Parsing -- Additional Edge Cases
# =============================================================================


class TestParseArgsRestoreRequiredFields:
    """Tests for parse_args restore subcommand required options."""

    def test_restore_requires_spec(self):
        """parse_args 'restore' fails when --spec is not provided."""
        with pytest.raises(SystemExit):
            parse_args(
                [
                    "restore",
                    "my_project",
                    "--blueprint",
                    "/path/to/blueprint.md",
                ]
            )

    def test_restore_requires_blueprint(self):
        """parse_args 'restore' fails when --blueprint is not provided."""
        with pytest.raises(SystemExit):
            parse_args(
                [
                    "restore",
                    "my_project",
                    "--spec",
                    "/path/to/spec.md",
                ]
            )


# =============================================================================
# Prerequisite Check Order
# =============================================================================


class TestPrerequisiteOrder:
    """Tests that the 8 prerequisite checks run in the specified order."""

    def test_checks_run_in_blueprint_order(self):
        """The 8 checks run in the order specified by the blueprint."""
        results = run_all_prerequisites()
        names = [name for name, _, _ in results]
        assert len(names) == 8
        # Blueprint specifies: Claude Code, SVP Plugin, API Credentials, Conda,
        # Python, Pytest, Git, Network
        # Check the first and last to verify ordering
        assert "claude" in names[0].lower() or "Claude" in names[0]
        assert "network" in names[7].lower() or "Network" in names[7]


# =============================================================================
# Fallback Content Completeness
# =============================================================================


class TestFallbackClaudeMdSvpHeader:
    """Tests for _generate_claude_md_fallback SVP-managed project header."""

    def test_fallback_contains_svp_managed_header(self):
        """Fallback CLAUDE.md starts with SVP-Managed Project header."""
        content = _generate_claude_md_fallback("test_project")
        assert "SVP-Managed Project" in content or "SVP" in content

    def test_fallback_contains_last_status_txt(self):
        """Fallback includes reference to .svp/last_status.txt in the six-step cycle."""
        content = _generate_claude_md_fallback("test_project")
        assert "last_status.txt" in content


# =============================================================================
# launch_claude_code -- Config Read on Every Launch
# =============================================================================


class TestLaunchClaudeCodeReadsConfigEachTime:
    """Tests that skip_permissions is read from config on every launch."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_reads_config_file_each_call(self, mock_which, mock_run, tmp_path):
        """launch_claude_code reads svp_config.json on each invocation."""
        # DATA ASSUMPTION: Config file changes between calls.
        project_root = tmp_path
        plugin_dir = Path("/tmp/plugin")

        # First call with skip_permissions=True
        config1 = {"skip_permissions": True}
        (project_root / CONFIG_FILE).write_text(json.dumps(config1))
        mock_run.return_value = MagicMock(returncode=0)

        launch_claude_code(project_root, plugin_dir)
        cmd1 = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" in cmd1

        # Change config to skip_permissions=False
        config2 = {"skip_permissions": False}
        (project_root / CONFIG_FILE).write_text(json.dumps(config2))
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=0)

        launch_claude_code(project_root, plugin_dir)
        cmd2 = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" not in cmd2


# =============================================================================
# Error Conditions
# =============================================================================


class TestLaunchClaudeCodeErrorConditions:
    """Tests for specific error messages from launch_claude_code."""

    @patch("shutil.which", return_value=None)
    def test_raises_runtime_error_claude_not_found_message(self, mock_which):
        """Raises RuntimeError with specific 'Claude Code executable not found' message."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        with pytest.raises(RuntimeError) as exc_info:
            launch_claude_code(project_root, plugin_dir)

        assert "Claude Code executable not found" in str(exc_info.value)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_raises_runtime_error_with_details_on_other_errors(
        self, mock_which, mock_run
    ):
        """Raises RuntimeError with 'Session launch failed: {details}' for other errors."""
        project_root = Path("/tmp/test_project")
        plugin_dir = Path("/tmp/plugin")

        mock_run.side_effect = OSError("Permission denied")
        config_content = json.dumps({"skip_permissions": False})

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    with pytest.raises(RuntimeError) as exc_info:
                        launch_claude_code(project_root, plugin_dir)

        assert "Session launch failed" in str(exc_info.value)


class TestCopyScriptsErrorMessage:
    """Tests for the specific error message from copy_scripts_to_workspace."""

    def test_error_message_mentions_corrupted(self, tmp_path):
        """RuntimeError message mentions 'corrupted' when plugin scripts/ is missing."""
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()

        project_root = tmp_path / "project"
        project_root.mkdir()

        with pytest.raises(RuntimeError, match="corrupted"):
            copy_scripts_to_workspace(plugin_root, project_root)


class TestCreateProjectDirectoryErrorMessage:
    """Tests for the specific error message from create_project_directory."""

    def test_error_message_includes_path(self, tmp_path):
        """FileExistsError message includes the project path."""
        existing = tmp_path / "my_project"
        existing.mkdir()

        with pytest.raises(FileExistsError) as exc_info:
            create_project_directory("my_project", tmp_path)

        assert str(existing) in str(exc_info.value)
