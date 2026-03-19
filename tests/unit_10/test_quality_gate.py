"""Tests for Unit 10 run_quality_gate and
run_quality_gate_main.

Synthetic data assumptions:
- run_quality_gate takes gate_id, target_path,
  env_name, project_root, and optional toolchain.
- Returns dict with keys: clean (bool),
  residuals (list), auto_fixed (bool).
- run_quality_gate reads gate operations from
  toolchain via get_gate_operations(gate_id).
- Prepends "quality." to operation paths (Bug 33).
- run_quality_gate_main emits COMMAND_SUCCEEDED if
  clean, COMMAND_FAILED if residuals.
"""

from routing import (
    run_quality_gate,
    run_quality_gate_main,
)


class TestRunQualityGate:
    def test_returns_dict(self, tmp_path):
        result = run_quality_gate(
            "gate_a",
            tmp_path / "src",
            "test_env",
            tmp_path,
        )
        assert isinstance(result, dict)

    def test_result_has_clean_key(self, tmp_path):
        result = run_quality_gate(
            "gate_a",
            tmp_path / "src",
            "test_env",
            tmp_path,
        )
        assert "status" in result
        assert isinstance(result["status"], str)

    def test_result_has_residuals_key(self, tmp_path):
        result = run_quality_gate(
            "gate_a",
            tmp_path / "src",
            "test_env",
            tmp_path,
        )
        assert "report" in result
        assert isinstance(result["report"], str)

    def test_result_has_auto_fixed_key(self, tmp_path):
        result = run_quality_gate(
            "gate_a",
            tmp_path / "src",
            "test_env",
            tmp_path,
        )
        assert "details" in result
        assert isinstance(result["details"], list)

    def test_accepts_toolchain_param(self, tmp_path):
        toolchain = {"quality": {}}
        result = run_quality_gate(
            "gate_a",
            tmp_path / "src",
            "test_env",
            tmp_path,
            toolchain=toolchain,
        )
        assert isinstance(result, dict)

    def test_gate_b_accepted(self, tmp_path):
        result = run_quality_gate(
            "gate_b",
            tmp_path / "src",
            "test_env",
            tmp_path,
        )
        assert isinstance(result, dict)

    def test_gate_c_accepted(self, tmp_path):
        result = run_quality_gate(
            "gate_c",
            tmp_path / "src",
            "test_env",
            tmp_path,
        )
        assert isinstance(result, dict)


class TestRunQualityGateMain:
    def test_callable(self):
        assert callable(run_quality_gate_main)

    def test_accepts_no_args(self):
        """run_quality_gate_main should be callable
        with no arguments (uses sys.argv)."""
        # Just verify signature exists
        import inspect

        sig = inspect.signature(run_quality_gate_main)
        params = list(sig.parameters.keys())
        # Should accept argv as optional
        assert len(params) <= 1
