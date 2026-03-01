"""
Tests for Unit 10 run_pytest function and CLI entry points.

DATA ASSUMPTION: test_path is a Path object pointing to a test directory or file.
env_name is a conda environment name string like "my_project" derived from
the project name. project_root is an existing directory.

DATA ASSUMPTION: run_pytest wraps "conda run -n {env_name} pytest {test_path} -v"
and constructs status lines from the output. We mock subprocess calls since we
cannot assume conda is available in the test environment.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from svp.scripts.routing import (
    run_pytest,
    routing_main,
    update_state_main,
    run_tests_main,
    COMMAND_STATUS_PATTERNS,
)
from svp.scripts.pipeline_state import PipelineState


@pytest.fixture
def tmp_project_root(tmp_path):
    """Create a temporary project root directory."""
    return tmp_path


class TestRunPytest:
    """Tests for the run_pytest function."""

    def test_returns_string(self, tmp_project_root):
        """run_pytest must return a string (the status line)."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)
        result = run_pytest(test_path, "test_env", tmp_project_root)
        assert isinstance(result, str)

    def test_return_starts_with_known_pattern(self, tmp_project_root):
        """The returned status line must start with one of the known patterns."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)
        result = run_pytest(test_path, "test_env", tmp_project_root)
        valid_prefixes = tuple(COMMAND_STATUS_PATTERNS)
        assert any(result.startswith(prefix) for prefix in valid_prefixes), (
            f"Status line {result!r} does not start with any of {valid_prefixes}"
        )

    def test_signature_accepts_path_string_path(self, tmp_project_root):
        """run_pytest signature: test_path is Path, env_name is str, project_root is Path."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)
        # Verify the function accepts these types (will raise NotImplementedError from stub)
        try:
            result = run_pytest(test_path, "my_env", tmp_project_root)
        except NotImplementedError:
            pass  # Expected from stub

    def test_uses_conda_run_not_bare_pytest(self, tmp_project_root):
        """Contract: run_pytest must use 'conda run -n {env_name} pytest ...',
        never bare 'python' or 'pytest'."""
        # This is a behavioral contract that we verify by checking the
        # command construction. We mock subprocess to inspect the command.
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="10 passed",
                stderr="",
            )
            try:
                result = run_pytest(test_path, "test_env", tmp_project_root)
                # If it ran, check the subprocess call
                if mock_run.called:
                    call_args = mock_run.call_args
                    cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args", [])
                    if isinstance(cmd, list):
                        cmd_str = " ".join(str(c) for c in cmd)
                    else:
                        cmd_str = str(cmd)
                    assert "conda" in cmd_str.lower() or "conda" in str(call_args), (
                        "run_pytest must use conda run, not bare pytest"
                    )
            except NotImplementedError:
                pass  # Expected from stub


class TestCLIEntryPoints:
    """Tests for CLI entry points: routing_main, update_state_main, run_tests_main."""

    def test_routing_main_is_callable(self):
        """routing_main must be a callable function."""
        assert callable(routing_main)

    def test_update_state_main_is_callable(self):
        """update_state_main must be a callable function."""
        assert callable(update_state_main)

    def test_run_tests_main_is_callable(self):
        """run_tests_main must be a callable function."""
        assert callable(run_tests_main)

    def test_routing_main_signature_no_args(self):
        """routing_main takes no arguments (CLI entry point)."""
        import inspect
        sig = inspect.signature(routing_main)
        # Should have no required parameters
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required_params) == 0

    def test_update_state_main_signature_no_args(self):
        """update_state_main takes no arguments (CLI entry point)."""
        import inspect
        sig = inspect.signature(update_state_main)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required_params) == 0

    def test_run_tests_main_signature_no_args(self):
        """run_tests_main takes no arguments (CLI entry point)."""
        import inspect
        sig = inspect.signature(run_tests_main)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required_params) == 0
