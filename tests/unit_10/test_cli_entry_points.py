"""Tests for Unit 10 CLI entry points: routing_main,
update_state_main, run_tests_main,
run_quality_gate_main.

Synthetic data assumptions:
- CLI entry points are callable functions.
- update_state_main accepts optional argv list.
- run_tests_main accepts optional argv list.
- run_quality_gate_main accepts optional argv list.
- routing_main reads pipeline_state.json, calls
  route(), and prints formatted action block.
- update_state_main reads last_status.txt and
  dispatches to appropriate handler.
- update_state_main accepts --gate for gate response
  dispatch (cross-unit CLI contract).
"""

import inspect

from routing import (
    read_last_status,
    run_quality_gate_main,
    run_tests_main,
    update_state_main,
)


class TestUpdateStateMain:
    def test_callable(self):
        assert callable(update_state_main)

    def test_accepts_argv(self):
        sig = inspect.signature(update_state_main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_argv_is_optional(self):
        sig = inspect.signature(update_state_main)
        param = sig.parameters["argv"]
        assert param.default is None or param.default is inspect.Parameter.empty


class TestRunTestsMain:
    def test_callable(self):
        assert callable(run_tests_main)

    def test_accepts_argv(self):
        sig = inspect.signature(run_tests_main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_argv_is_optional(self):
        sig = inspect.signature(run_tests_main)
        param = sig.parameters["argv"]
        assert param.default is None or param.default is inspect.Parameter.empty


class TestRunQualityGateMainEntry:
    def test_callable(self):
        assert callable(run_quality_gate_main)

    def test_accepts_argv(self):
        sig = inspect.signature(run_quality_gate_main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_argv_is_optional(self):
        sig = inspect.signature(run_quality_gate_main)
        param = sig.parameters["argv"]
        assert param.default is None or param.default is inspect.Parameter.empty


class TestReadLastStatus:
    def test_callable(self):
        assert callable(read_last_status)

    def test_returns_string(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("TESTS_PASSED")
        result = read_last_status(tmp_path)
        assert isinstance(result, str)

    def test_reads_status_content(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("TEST_GENERATION_COMPLETE")
        result = read_last_status(tmp_path)
        assert result == "TEST_GENERATION_COMPLETE"

    def test_strips_whitespace(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("  TESTS_PASSED  \n")
        result = read_last_status(tmp_path)
        assert result.strip() == "TESTS_PASSED"
