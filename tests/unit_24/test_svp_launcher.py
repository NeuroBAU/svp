"""
Tests for Unit 24: SVP Launcher.

Verifies constants, prerequisite checks, project
creation, file copying, session management, CLI
parsing, and main entry point.
"""

import json
from pathlib import Path
from unittest.mock import patch

from src.unit_24.stub import (
    CLAUDE_MD_FILE,
    CONFIG_FILE,
    MARKERS_DIR,
    PROFILE_FILE,
    PROJECT_DIRS,
    README_SVP_FILE,
    RESTART_SIGNAL_FILE,
    RUFF_CONFIG_FILE,
    STATE_FILE,
    SVP_DIR,
    SVP_ENV_VAR,
    TOOLCHAIN_FILE,
    _find_plugin_root,
    _is_svp_plugin_dir,
    _print_header,
    _print_status,
    _print_transition,
    check_api_credentials,
    check_claude_code,
    check_conda,
    check_git,
    check_network,
    check_pytest,
    check_python,
    check_svp_plugin,
    clear_restart_signal,
    copy_hooks,
    copy_regression_tests,
    copy_ruff_config,
    copy_scripts_to_workspace,
    copy_toolchain_default,
    create_project_directory,
    detect_existing_project,
    detect_restart_signal,
    generate_claude_md,
    launch_claude_code,
    main,
    parse_args,
    resume_project,
    run_all_prerequisites,
    run_session_loop,
    set_filesystem_permissions,
    write_default_config,
    write_initial_state,
    write_readme_svp,
)

# -------------------------------------------------------
# Constants
# -------------------------------------------------------


class TestConstants:
    def test_restart_signal(self):
        assert RESTART_SIGNAL_FILE == ".svp/restart_signal"

    def test_state_file(self):
        assert STATE_FILE == "pipeline_state.json"

    def test_config_file(self):
        assert CONFIG_FILE == "svp_config.json"

    def test_toolchain_file(self):
        assert TOOLCHAIN_FILE == "toolchain.json"

    def test_ruff_config_file(self):
        assert RUFF_CONFIG_FILE == "ruff.toml"

    def test_svp_dir(self):
        assert SVP_DIR == ".svp"

    def test_markers_dir(self):
        assert MARKERS_DIR == ".svp/markers"

    def test_claude_md_file(self):
        assert CLAUDE_MD_FILE == "CLAUDE.md"

    def test_readme_svp_file(self):
        assert README_SVP_FILE == "README_SVP.txt"

    def test_svp_env_var(self):
        assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"

    def test_profile_file(self):
        assert PROFILE_FILE == "project_profile.json"


class TestProjectDirs:
    def test_is_list(self):
        assert isinstance(PROJECT_DIRS, list)

    def test_has_svp_dir(self):
        assert ".svp" in PROJECT_DIRS

    def test_has_markers(self):
        assert ".svp/markers" in PROJECT_DIRS

    def test_has_scripts(self):
        assert "scripts" in PROJECT_DIRS

    def test_has_src(self):
        assert "src" in PROJECT_DIRS

    def test_has_tests(self):
        assert "tests" in PROJECT_DIRS

    def test_has_regressions(self):
        assert "tests/regressions" in PROJECT_DIRS


# -------------------------------------------------------
# Plugin discovery
# -------------------------------------------------------


class TestIsSvpPluginDir:
    def test_callable(self):
        assert callable(_is_svp_plugin_dir)

    def test_returns_bool(self, tmp_path):
        result = _is_svp_plugin_dir(tmp_path)
        assert isinstance(result, bool)

    def test_false_for_empty(self, tmp_path):
        assert _is_svp_plugin_dir(tmp_path) is False

    def test_true_for_valid(self, tmp_path):
        cp = tmp_path / ".claude-plugin"
        cp.mkdir()
        pj = cp / "plugin.json"
        pj.write_text(json.dumps({"name": "svp", "version": "2.1.0"}))
        assert _is_svp_plugin_dir(tmp_path) is True


class TestFindPluginRoot:
    def test_callable(self):
        assert callable(_find_plugin_root)

    def test_returns_path_or_none(self):
        result = _find_plugin_root()
        assert result is None or isinstance(result, Path)


# -------------------------------------------------------
# CLI parsing
# -------------------------------------------------------


class TestParseArgs:
    def test_new_mode(self):
        args = parse_args(["new", "myproject"])
        assert args.command == "new"
        assert args.project_name == "myproject"

    def test_bare_mode(self):
        args = parse_args([])
        assert args.command is None or (args.command == "")


# -------------------------------------------------------
# Prerequisite checks
# -------------------------------------------------------


class TestPrerequisiteChecks:
    def test_check_claude_code_returns_tuple(self):
        result = check_claude_code()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_check_conda_returns_tuple(self):
        result = check_conda()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_python_returns_tuple(self):
        result = check_python()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_pytest_returns_tuple(self):
        result = check_pytest()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_git_returns_tuple(self):
        result = check_git()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_network_returns_tuple(self):
        result = check_network()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_svp_plugin_returns_tuple(self):
        result = check_svp_plugin()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_api_credentials_returns_tuple(
        self,
    ):
        result = check_api_credentials()
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestRunAllPrerequisites:
    def test_returns_list(self):
        result = run_all_prerequisites()
        assert isinstance(result, list)
        assert len(result) == 8
        for name, passed, msg in result:
            assert isinstance(name, str)
            assert isinstance(passed, bool)
            assert isinstance(msg, str)


# -------------------------------------------------------
# Project creation
# -------------------------------------------------------


class TestCreateProjectDirectory:
    def test_creates_directory(self, tmp_path):
        result = create_project_directory("testproj", tmp_path)
        assert result.is_dir()
        assert result.name == "testproj"

    def test_creates_subdirs(self, tmp_path):
        root = create_project_directory("testproj", tmp_path)
        assert (root / ".svp").is_dir()
        assert (root / "scripts").is_dir()


# -------------------------------------------------------
# Copy functions
# -------------------------------------------------------


class TestCopyFunctions:
    def test_copy_scripts_callable(self):
        assert callable(copy_scripts_to_workspace)

    def test_copy_toolchain_callable(self):
        assert callable(copy_toolchain_default)

    def test_copy_ruff_callable(self):
        assert callable(copy_ruff_config)

    def test_copy_regression_callable(self):
        assert callable(copy_regression_tests)

    def test_copy_hooks_callable(self):
        assert callable(copy_hooks)


# -------------------------------------------------------
# Generate and write functions
# -------------------------------------------------------


class TestGenerateClaudeMd:
    def test_callable(self):
        assert callable(generate_claude_md)


class TestWriteFunctions:
    def test_write_initial_state_callable(self):
        assert callable(write_initial_state)

    def test_write_default_config_callable(self):
        assert callable(write_default_config)

    def test_write_readme_svp_callable(self):
        assert callable(write_readme_svp)


# -------------------------------------------------------
# Filesystem permissions
# -------------------------------------------------------


class TestSetFilesystemPermissions:
    def test_callable(self):
        assert callable(set_filesystem_permissions)


# -------------------------------------------------------
# Session management
# -------------------------------------------------------


class TestSessionManagement:
    def test_launch_callable(self):
        assert callable(launch_claude_code)

    def test_detect_restart_callable(self):
        assert callable(detect_restart_signal)

    def test_clear_restart_callable(self):
        assert callable(clear_restart_signal)

    def test_run_session_loop_callable(self):
        assert callable(run_session_loop)

    def test_detect_existing_callable(self):
        assert callable(detect_existing_project)

    def test_resume_callable(self):
        assert callable(resume_project)


class TestDetectRestartSignal:
    def test_none_when_no_signal(self, tmp_path):
        result = detect_restart_signal(tmp_path)
        assert result is None

    def test_returns_content_when_exists(self, tmp_path):
        svp = tmp_path / ".svp"
        svp.mkdir()
        sig = svp / "restart_signal"
        sig.write_text("restart reason")
        result = detect_restart_signal(tmp_path)
        assert result == "restart reason"


class TestClearRestartSignal:
    def test_removes_file(self, tmp_path):
        svp = tmp_path / ".svp"
        svp.mkdir()
        sig = svp / "restart_signal"
        sig.write_text("test")
        clear_restart_signal(tmp_path)
        assert not sig.exists()

    def test_noop_when_missing(self, tmp_path):
        clear_restart_signal(tmp_path)


class TestDetectExistingProject:
    def test_false_for_empty(self, tmp_path):
        assert detect_existing_project(tmp_path) is False

    def test_true_for_state_file(self, tmp_path):
        (tmp_path / "pipeline_state.json").write_text("{}")
        assert detect_existing_project(tmp_path) is True


# -------------------------------------------------------
# Print helpers
# -------------------------------------------------------


class TestPrintHelpers:
    def test_print_header(self, capsys):
        _print_header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out

    def test_print_status_pass(self, capsys):
        _print_status("Check", True, "OK")
        captured = capsys.readouterr()
        assert "Check" in captured.out

    def test_print_status_fail(self, capsys):
        _print_status("Check", False, "FAIL")
        captured = capsys.readouterr()
        assert "Check" in captured.out

    def test_print_transition(self, capsys):
        _print_transition("Moving on")
        captured = capsys.readouterr()
        assert "Moving on" in captured.out


# -------------------------------------------------------
# Main entry point
# -------------------------------------------------------


class TestMain:
    def test_callable(self):
        assert callable(main)

    def test_returns_int(self):
        with patch(
            "src.unit_24.stub._find_plugin_root",
            return_value=None,
        ):
            result = main(["new", "testproj"])
            assert isinstance(result, int)


# -------------------------------------------------------
# Self-containment
# -------------------------------------------------------


class TestSelfContainment:
    """Unit 24 must not import from other SVP units."""

    def test_no_svp_unit_imports(self):
        import inspect

        source = inspect.getsource(
            __import__(
                "src.unit_24.stub",
                fromlist=["stub"],
            )
        )
        # Should not import from src.unit_N
        for i in range(1, 24):
            assert f"from src.unit_{i}" not in source
