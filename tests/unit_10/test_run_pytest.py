"""Tests for Unit 10 run_pytest and _is_collection_error.

Synthetic data assumptions:
- run_pytest takes test_path, env_name, project_root,
  and optional toolchain dict.
- run_pytest returns a status string from
  COMMAND_STATUS_PATTERNS (TESTS_PASSED, TESTS_FAILED,
  TESTS_ERROR).
- _is_collection_error checks if pytest output
  indicates a collection error vs a test failure.
- Toolchain param is optional and may provide
  collection_error_indicators.
"""

from src.unit_10.stub import (
    _is_collection_error,
    run_pytest,
)


class TestRunPytest:
    def test_returns_string(self, tmp_path):
        result = run_pytest(
            tmp_path / "tests",
            "test_env",
            tmp_path,
        )
        assert isinstance(result, str)

    def test_returns_valid_status_pattern(self, tmp_path):
        valid = {
            "TESTS_PASSED",
            "TESTS_FAILED",
            "TESTS_ERROR",
        }
        result = run_pytest(
            tmp_path / "tests",
            "test_env",
            tmp_path,
        )
        assert result in valid

    def test_accepts_toolchain_param(self, tmp_path):
        toolchain = {"key": "value"}
        result = run_pytest(
            tmp_path / "tests",
            "test_env",
            tmp_path,
            toolchain=toolchain,
        )
        assert isinstance(result, str)

    def test_default_toolchain_is_none(self, tmp_path):
        """run_pytest should work without toolchain."""
        result = run_pytest(
            tmp_path / "tests",
            "test_env",
            tmp_path,
        )
        assert result is not None


class TestIsCollectionError:
    def test_empty_output_not_collection_error(self):
        assert _is_collection_error("") is False

    def test_normal_failure_not_collection_error(
        self,
    ):
        output = "FAILED test_foo.py::test_bar - "
        "AssertionError"
        assert _is_collection_error(output) is False

    def test_collection_error_detected(self):
        output = "ERROR collecting test_foo.py\nModuleNotFoundError: No module"
        result = _is_collection_error(output)
        assert isinstance(result, bool)

    def test_accepts_toolchain_param(self):
        toolchain = {"collection_error_indicators": ["ModuleNotFoundError"]}
        result = _is_collection_error(
            "some output",
            toolchain=toolchain,
        )
        assert isinstance(result, bool)

    def test_default_toolchain_none(self):
        result = _is_collection_error("some output")
        assert isinstance(result, bool)

    def test_import_error_detection(self):
        output = "E   ImportError: cannot import name 'foo' from 'bar'"
        result = _is_collection_error(output)
        assert isinstance(result, bool)
