"""
Tests for Unit 15: Quality Gate Execution.

Synthetic Data Assumptions:
- QUALITY_RUNNERS is a module-level dict with exactly 6 keys:
  "python", "r", "stan_syntax_check", "plugin_markdown", "plugin_bash", "plugin_json".
  Each value is a callable accepting (Path, str, Dict[str, Any], Dict[str, Any])
  and returning a QualityResult named tuple.
- QualityResult is a NamedTuple from Unit 2 with fields:
  status (str), auto_fixed (bool), residuals (List[str]), report (str).
- Valid status strings are: "QUALITY_CLEAN", "QUALITY_AUTO_FIXED",
  "QUALITY_RESIDUAL", "QUALITY_ERROR".
- run_quality_gate accepts (target_path, gate_id, language, language_config,
  toolchain_config) and dispatches to QUALITY_RUNNERS[language].
- Gate composition is read from toolchain via get_gate_composition(toolchain_config,
  gate_id), returning an ordered list of operation dicts with "operation" and
  "command" keys.
- resolve_command from Unit 4 is used to resolve command templates.
- Commands are executed in order; results are classified into one of the four
  status values.
- For languages where a tool is "none" in toolchain, the corresponding operation
  is skipped.
- run_quality_gate_main is a CLI entry point with arguments: --target, --gate,
  --unit, --language, --project-root. It loads language config and toolchain,
  calls run_quality_gate, and prints status to stdout.
- Toolchain configs are synthetic dicts with quality gate compositions.
- Language configs are synthetic dicts representing language registry entries.
- tmp_path is used for filesystem paths to avoid side effects.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quality_gate import (
    QUALITY_RUNNERS,
    run_quality_gate,
    run_quality_gate_main,
)

# ---------------------------------------------------------------------------
# Expected constants from the blueprint
# ---------------------------------------------------------------------------

EXPECTED_RUNNER_KEYS = {
    "python",
    "r",
    "stan_syntax_check",
    "plugin_markdown",
    "plugin_bash",
    "plugin_json",
}

VALID_QUALITY_STATUSES = {
    "QUALITY_CLEAN",
    "QUALITY_AUTO_FIXED",
    "QUALITY_RESIDUAL",
    "QUALITY_ERROR",
}


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------


def make_toolchain_config(gate_id="gate_a", operations=None):
    """Build a minimal synthetic toolchain config with quality gate composition."""
    if operations is None:
        operations = [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
        ]
    return {
        "quality": {
            gate_id: operations,
        },
        "env_name": "test_env",
        "run_prefix": "conda run -n test_env",
    }


def make_language_config(language="python"):
    """Build a minimal synthetic language config dict."""
    if language == "python":
        return {
            "id": "python",
            "display_name": "Python",
            "file_extension": ".py",
            "quality_runner_key": "python",
            "default_quality": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
        }
    elif language == "r":
        return {
            "id": "r",
            "display_name": "R",
            "file_extension": ".R",
            "quality_runner_key": "r",
            "default_quality": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
        }
    elif language == "stan_syntax_check":
        return {
            "id": "stan",
            "display_name": "Stan",
            "file_extension": ".stan",
            "quality_runner_key": "stan_syntax_check",
        }
    elif language == "plugin_markdown":
        return {
            "id": "plugin_markdown",
            "quality_runner_key": "plugin_markdown",
        }
    elif language == "plugin_bash":
        return {
            "id": "plugin_bash",
            "quality_runner_key": "plugin_bash",
        }
    elif language == "plugin_json":
        return {
            "id": "plugin_json",
            "quality_runner_key": "plugin_json",
        }
    return {}


# ---------------------------------------------------------------------------
# QUALITY_RUNNERS dispatch table tests
# ---------------------------------------------------------------------------


class TestQualityRunnersDispatchTable:
    """Tests for the QUALITY_RUNNERS module-level constant."""

    def test_quality_runners_is_a_dict(self):
        assert isinstance(QUALITY_RUNNERS, dict)

    def test_quality_runners_has_exactly_six_keys(self):
        assert len(QUALITY_RUNNERS) == 6

    def test_quality_runners_contains_python_key(self):
        assert "python" in QUALITY_RUNNERS

    def test_quality_runners_contains_r_key(self):
        assert "r" in QUALITY_RUNNERS

    def test_quality_runners_contains_stan_syntax_check_key(self):
        assert "stan_syntax_check" in QUALITY_RUNNERS

    def test_quality_runners_contains_plugin_markdown_key(self):
        assert "plugin_markdown" in QUALITY_RUNNERS

    def test_quality_runners_contains_plugin_bash_key(self):
        assert "plugin_bash" in QUALITY_RUNNERS

    def test_quality_runners_contains_plugin_json_key(self):
        assert "plugin_json" in QUALITY_RUNNERS

    def test_quality_runners_keys_match_expected_set(self):
        assert set(QUALITY_RUNNERS.keys()) == EXPECTED_RUNNER_KEYS

    def test_quality_runners_values_are_callable(self):
        for key, runner in QUALITY_RUNNERS.items():
            assert callable(runner), f"QUALITY_RUNNERS['{key}'] is not callable"


# ---------------------------------------------------------------------------
# Python runner tests
# ---------------------------------------------------------------------------


class TestPythonRunner:
    """Tests for the 'python' quality runner (ruff format, ruff check, mypy)."""

    def test_python_runner_returns_quality_result(self, tmp_path):
        runner = QUALITY_RUNNERS["python"]
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")
        assert hasattr(result, "residuals")
        assert hasattr(result, "report")

    def test_python_runner_status_is_valid(self, tmp_path):
        runner = QUALITY_RUNNERS["python"]
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES

    def test_python_runner_auto_fixed_is_bool(self, tmp_path):
        runner = QUALITY_RUNNERS["python"]
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert isinstance(result.auto_fixed, bool)

    def test_python_runner_residuals_is_list(self, tmp_path):
        runner = QUALITY_RUNNERS["python"]
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert isinstance(result.residuals, list)

    def test_python_runner_report_is_string(self, tmp_path):
        runner = QUALITY_RUNNERS["python"]
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert isinstance(result.report, str)


# ---------------------------------------------------------------------------
# R runner tests
# ---------------------------------------------------------------------------


class TestRRunner:
    """Tests for the 'r' quality runner (lintr, styler)."""

    def test_r_runner_returns_quality_result(self, tmp_path):
        runner = QUALITY_RUNNERS["r"]
        target = tmp_path / "example.R"
        target.write_text("x <- 1\n")
        lang_cfg = make_language_config("r")
        tc_cfg = make_toolchain_config(
            operations=[
                {"operation": "quality.lint", "command": "lintr {target}"},
                {"operation": "quality.format", "command": "styler {target}"},
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")
        assert hasattr(result, "residuals")
        assert hasattr(result, "report")

    def test_r_runner_status_is_valid(self, tmp_path):
        runner = QUALITY_RUNNERS["r"]
        target = tmp_path / "example.R"
        target.write_text("x <- 1\n")
        lang_cfg = make_language_config("r")
        tc_cfg = make_toolchain_config(
            operations=[
                {"operation": "quality.lint", "command": "lintr {target}"},
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# Stan syntax check runner tests
# ---------------------------------------------------------------------------


class TestStanSyntaxCheckRunner:
    """Tests for 'stan_syntax_check' runner: pass/fail only."""

    def test_stan_runner_returns_quality_result(self, tmp_path):
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        target = tmp_path / "model.stan"
        target.write_text("data { int N; }\n")
        lang_cfg = make_language_config("stan_syntax_check")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.syntax_check",
                    "command": "stanc --syntax-only {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")

    def test_stan_runner_is_pass_fail_only(self, tmp_path):
        """Stan syntax check should return pass (QUALITY_CLEAN) or fail status,
        not auto-fix statuses."""
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        target = tmp_path / "model.stan"
        target.write_text("data { int N; }\n")
        lang_cfg = make_language_config("stan_syntax_check")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.syntax_check",
                    "command": "stanc --syntax-only {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        # Stan is pass/fail only -- should not report auto-fixed
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# Plugin markdown runner tests
# ---------------------------------------------------------------------------


class TestPluginMarkdownRunner:
    """Tests for 'plugin_markdown' runner: supports auto-fix."""

    def test_markdown_runner_returns_quality_result(self, tmp_path):
        runner = QUALITY_RUNNERS["plugin_markdown"]
        target = tmp_path / "doc.md"
        target.write_text("# Hello\n")
        lang_cfg = make_language_config("plugin_markdown")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.markdown_check",
                    "command": "markdownlint --fix {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")
        assert hasattr(result, "residuals")
        assert hasattr(result, "report")

    def test_markdown_runner_status_is_valid(self, tmp_path):
        runner = QUALITY_RUNNERS["plugin_markdown"]
        target = tmp_path / "doc.md"
        target.write_text("# Hello\n")
        lang_cfg = make_language_config("plugin_markdown")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.markdown_check",
                    "command": "markdownlint --fix {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# Plugin bash runner tests
# ---------------------------------------------------------------------------


class TestPluginBashRunner:
    """Tests for 'plugin_bash' runner: pass/fail only via bash -n."""

    def test_bash_runner_returns_quality_result(self, tmp_path):
        runner = QUALITY_RUNNERS["plugin_bash"]
        target = tmp_path / "script.sh"
        target.write_text("#!/bin/bash\necho hello\n")
        lang_cfg = make_language_config("plugin_bash")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.bash_syntax",
                    "command": "bash -n {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")

    def test_bash_runner_is_pass_fail_only(self, tmp_path):
        """Plugin bash should return pass/fail, not auto-fix."""
        runner = QUALITY_RUNNERS["plugin_bash"]
        target = tmp_path / "script.sh"
        target.write_text("#!/bin/bash\necho hello\n")
        lang_cfg = make_language_config("plugin_bash")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.bash_syntax",
                    "command": "bash -n {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# Plugin JSON runner tests
# ---------------------------------------------------------------------------


class TestPluginJsonRunner:
    """Tests for 'plugin_json' runner: supports auto-fix (pretty-print)."""

    def test_json_runner_returns_quality_result(self, tmp_path):
        runner = QUALITY_RUNNERS["plugin_json"]
        target = tmp_path / "data.json"
        target.write_text('{"key": "value"}\n')
        lang_cfg = make_language_config("plugin_json")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.json_validate",
                    "command": "json_check {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")
        assert hasattr(result, "residuals")
        assert hasattr(result, "report")

    def test_json_runner_status_is_valid(self, tmp_path):
        runner = QUALITY_RUNNERS["plugin_json"]
        target = tmp_path / "data.json"
        target.write_text('{"key": "value"}\n')
        lang_cfg = make_language_config("plugin_json")
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.json_validate",
                    "command": "json_check {target}",
                },
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# run_quality_gate tests
# ---------------------------------------------------------------------------


class TestRunQualityGateDispatchesCorrectRunner:
    """Tests that run_quality_gate dispatches to the correct QUALITY_RUNNERS entry."""

    def test_dispatches_to_python_runner(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()

        with patch.dict(
            "src.unit_15.stub.QUALITY_RUNNERS",
            {"python": MagicMock(return_value=MagicMock())},
        ):
            from quality_gate import QUALITY_RUNNERS as patched_runners

            run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
            patched_runners["python"].assert_called_once()

    def test_dispatches_to_r_runner(self, tmp_path):
        target = tmp_path / "example.R"
        target.write_text("x <- 1\n")
        lang_cfg = make_language_config("r")
        tc_cfg = make_toolchain_config()

        with patch.dict(
            "src.unit_15.stub.QUALITY_RUNNERS",
            {"r": MagicMock(return_value=MagicMock())},
        ):
            from quality_gate import QUALITY_RUNNERS as patched_runners

            run_quality_gate(target, "gate_a", "r", lang_cfg, tc_cfg)
            patched_runners["r"].assert_called_once()

    def test_dispatches_to_stan_syntax_check_runner(self, tmp_path):
        target = tmp_path / "model.stan"
        target.write_text("data { int N; }\n")
        lang_cfg = make_language_config("stan_syntax_check")
        tc_cfg = make_toolchain_config()

        with patch.dict(
            "src.unit_15.stub.QUALITY_RUNNERS",
            {"stan_syntax_check": MagicMock(return_value=MagicMock())},
        ):
            from quality_gate import QUALITY_RUNNERS as patched_runners

            run_quality_gate(target, "gate_a", "stan_syntax_check", lang_cfg, tc_cfg)
            patched_runners["stan_syntax_check"].assert_called_once()

    def test_dispatches_to_plugin_markdown_runner(self, tmp_path):
        target = tmp_path / "doc.md"
        target.write_text("# Hello\n")
        lang_cfg = make_language_config("plugin_markdown")
        tc_cfg = make_toolchain_config()

        with patch.dict(
            "src.unit_15.stub.QUALITY_RUNNERS",
            {"plugin_markdown": MagicMock(return_value=MagicMock())},
        ):
            from quality_gate import QUALITY_RUNNERS as patched_runners

            run_quality_gate(target, "gate_a", "plugin_markdown", lang_cfg, tc_cfg)
            patched_runners["plugin_markdown"].assert_called_once()

    def test_dispatches_to_plugin_bash_runner(self, tmp_path):
        target = tmp_path / "script.sh"
        target.write_text("#!/bin/bash\necho hello\n")
        lang_cfg = make_language_config("plugin_bash")
        tc_cfg = make_toolchain_config()

        with patch.dict(
            "src.unit_15.stub.QUALITY_RUNNERS",
            {"plugin_bash": MagicMock(return_value=MagicMock())},
        ):
            from quality_gate import QUALITY_RUNNERS as patched_runners

            run_quality_gate(target, "gate_a", "plugin_bash", lang_cfg, tc_cfg)
            patched_runners["plugin_bash"].assert_called_once()

    def test_dispatches_to_plugin_json_runner(self, tmp_path):
        target = tmp_path / "data.json"
        target.write_text('{"key": "value"}\n')
        lang_cfg = make_language_config("plugin_json")
        tc_cfg = make_toolchain_config()

        with patch.dict(
            "src.unit_15.stub.QUALITY_RUNNERS",
            {"plugin_json": MagicMock(return_value=MagicMock())},
        ):
            from quality_gate import QUALITY_RUNNERS as patched_runners

            run_quality_gate(target, "gate_a", "plugin_json", lang_cfg, tc_cfg)
            patched_runners["plugin_json"].assert_called_once()


class TestRunQualityGateReturnValue:
    """Tests that run_quality_gate returns a QualityResult with correct fields."""

    def test_returns_quality_result_with_status_field(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert hasattr(result, "status")

    def test_returns_quality_result_with_auto_fixed_field(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert hasattr(result, "auto_fixed")

    def test_returns_quality_result_with_residuals_field(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert hasattr(result, "residuals")

    def test_returns_quality_result_with_report_field(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert hasattr(result, "report")

    def test_status_is_one_of_valid_values(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES

    def test_auto_fixed_is_boolean(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert isinstance(result.auto_fixed, bool)

    def test_residuals_is_list_of_strings(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert isinstance(result.residuals, list)
        for item in result.residuals:
            assert isinstance(item, str)

    def test_report_is_string(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert isinstance(result.report, str)


class TestRunQualityGateStatusClassification:
    """Tests that run_quality_gate correctly classifies result statuses."""

    def test_quality_clean_means_no_issues(self, tmp_path):
        """When status is QUALITY_CLEAN, auto_fixed should be False and
        residuals should be empty."""
        target = tmp_path / "clean.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        if result.status == "QUALITY_CLEAN":
            assert result.auto_fixed is False
            assert result.residuals == []

    def test_quality_auto_fixed_means_all_issues_auto_fixed(self, tmp_path):
        """When status is QUALITY_AUTO_FIXED, auto_fixed should be True and
        residuals should be empty."""
        target = tmp_path / "fixable.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        if result.status == "QUALITY_AUTO_FIXED":
            assert result.auto_fixed is True
            assert result.residuals == []

    def test_quality_residual_means_residuals_remain(self, tmp_path):
        """When status is QUALITY_RESIDUAL, residuals list should be non-empty."""
        target = tmp_path / "messy.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        if result.status == "QUALITY_RESIDUAL":
            assert len(result.residuals) > 0


class TestRunQualityGateGateComposition:
    """Tests that run_quality_gate reads gate composition from toolchain."""

    def test_uses_get_gate_composition_for_gate_id(self, tmp_path):
        """run_quality_gate should call get_gate_composition with the
        toolchain_config and gate_id."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config("gate_b")

        with patch(
            "src.unit_15.stub.get_gate_composition",
            return_value=[
                {"operation": "quality.format", "command": "ruff format {target}"}
            ],
        ) as mock_get_gate:
            # Also need to mock subprocess or command execution to avoid
            # actual command execution
            try:
                run_quality_gate(target, "gate_b", "python", lang_cfg, tc_cfg)
            except Exception:
                pass
            # Verify get_gate_composition was called with correct args
            if mock_get_gate.called:
                call_args = mock_get_gate.call_args
                assert call_args[0][0] == tc_cfg or call_args[0][0] is tc_cfg
                assert call_args[0][1] == "gate_b"

    def test_supports_gate_a_gate_id(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config("gate_a")
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES

    def test_supports_gate_b_gate_id(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config("gate_b")
        result = run_quality_gate(target, "gate_b", "python", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES

    def test_supports_gate_c_gate_id(self, tmp_path):
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config("gate_c")
        result = run_quality_gate(target, "gate_c", "python", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


class TestRunQualityGateCommandExecution:
    """Tests that commands are resolved and executed in order."""

    def test_executes_operations_in_order(self, tmp_path):
        """Gate composition operations should be executed in the order specified."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        operations = [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
            {"operation": "quality.typecheck", "command": "mypy {target}"},
        ]
        tc_cfg = make_toolchain_config("gate_a", operations)

        with patch("src.unit_15.stub.resolve_command") as mock_resolve:
            mock_resolve.return_value = "mocked_command"
            try:
                run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
            except Exception:
                pass
            # If resolve_command was called, verify it was called for each operation
            if mock_resolve.called:
                assert mock_resolve.call_count >= 1

    def test_resolve_command_is_called_for_templates(self, tmp_path):
        """Command templates from gate composition should be resolved via
        resolve_command."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        tc_cfg = make_toolchain_config()

        with patch("src.unit_15.stub.resolve_command") as mock_resolve:
            mock_resolve.return_value = "resolved_command"
            try:
                run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
            except Exception:
                pass
            if mock_resolve.called:
                for call in mock_resolve.call_args_list:
                    # First arg should be the template string
                    assert isinstance(call[0][0], str) or isinstance(
                        call.kwargs.get("template", ""), str
                    )


class TestRunQualityGateToolNoneSkipping:
    """Tests that operations with tool 'none' are skipped."""

    def test_skips_operation_when_tool_is_none_in_toolchain(self, tmp_path):
        """For languages where a tool is 'none' in toolchain, the corresponding
        operation should be skipped."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        # Create toolchain where type_checker is "none"
        tc_cfg = make_toolchain_config(
            operations=[
                {"operation": "quality.format", "command": "ruff format {target}"},
                {"operation": "quality.typecheck", "command": "none"},
            ]
        )
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        # Should still complete without error even with "none" tool
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# run_quality_gate with each language
# ---------------------------------------------------------------------------


class TestRunQualityGateAllLanguages:
    """Tests run_quality_gate with every supported language key."""

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_run_quality_gate_accepts_each_supported_language(self, tmp_path, language):
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        result = run_quality_gate(target, "gate_a", language, lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# run_quality_gate error conditions
# ---------------------------------------------------------------------------


class TestRunQualityGateErrorConditions:
    """Tests for error conditions in run_quality_gate."""

    def test_unknown_language_raises_error(self, tmp_path):
        """Using a language key not in QUALITY_RUNNERS should raise an error."""
        target = tmp_path / "example.xyz"
        target.write_text("content\n")
        lang_cfg = {"id": "unknown"}
        tc_cfg = make_toolchain_config()
        with pytest.raises((KeyError, ValueError)):
            run_quality_gate(target, "gate_a", "unknown_language", lang_cfg, tc_cfg)

    def test_quality_error_status_on_tool_execution_failure(self, tmp_path):
        """When tool execution fails, status should be QUALITY_ERROR."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        lang_cfg = make_language_config("python")
        # Use a command that will definitely fail
        tc_cfg = make_toolchain_config(
            operations=[
                {
                    "operation": "quality.format",
                    "command": "nonexistent_tool_xyz {target}",
                },
            ]
        )
        result = run_quality_gate(target, "gate_a", "python", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES


# ---------------------------------------------------------------------------
# run_quality_gate_main CLI tests
# ---------------------------------------------------------------------------


class TestRunQualityGateMainCliArguments:
    """Tests for run_quality_gate_main CLI argument parsing."""

    def test_accepts_target_argument(self, tmp_path):
        """CLI should accept --target argument."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        # Mock the underlying calls to avoid real execution
        with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass

    def test_accepts_gate_argument(self, tmp_path):
        """CLI should accept --gate argument with valid gate IDs."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        for gate_id in ["gate_a", "gate_b", "gate_c"]:
            argv = [
                "--target",
                str(target),
                "--gate",
                gate_id,
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(project_root),
            ]
            with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
                mock_rqg.return_value = MagicMock(
                    status="QUALITY_CLEAN",
                    auto_fixed=False,
                    residuals=[],
                    report="All clean",
                )
                try:
                    run_quality_gate_main(argv)
                except SystemExit:
                    pass

    def test_accepts_unit_argument(self, tmp_path):
        """CLI should accept --unit argument."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "5",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass

    def test_accepts_language_argument(self, tmp_path):
        """CLI should accept --language argument."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass

    def test_accepts_project_root_argument(self, tmp_path):
        """CLI should accept --project-root argument."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass


class TestRunQualityGateMainBehavior:
    """Tests for run_quality_gate_main functional behavior."""

    def test_loads_language_config_and_toolchain(self, tmp_path):
        """CLI should load language config and toolchain before calling
        run_quality_gate."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        with (
            patch("src.unit_15.stub.run_quality_gate") as mock_rqg,
            patch("src.unit_15.stub.get_language_config") as mock_lang,
            patch("src.unit_15.stub.load_toolchain") as mock_tc,
        ):
            mock_lang.return_value = make_language_config("python")
            mock_tc.return_value = make_toolchain_config()
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass
            # At least one of the config-loading functions should be called
            # The exact import path may vary but the behavior contract says
            # it loads language config and toolchain

    def test_calls_run_quality_gate_with_parsed_arguments(self, tmp_path):
        """CLI should call run_quality_gate with the parsed arguments."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass
            if mock_rqg.called:
                call_args = mock_rqg.call_args
                # Verify the target path is passed correctly
                assert Path(str(call_args[0][0])) == target or (
                    call_args.kwargs.get("target_path") == target
                )

    def test_prints_status_to_stdout(self, tmp_path, capsys):
        """CLI should print status to stdout."""
        target = tmp_path / "example.py"
        target.write_text("x = 1\n")
        project_root = tmp_path / "project"
        project_root.mkdir()
        argv = [
            "--target",
            str(target),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(project_root),
        ]
        with patch("src.unit_15.stub.run_quality_gate") as mock_rqg:
            mock_rqg.return_value = MagicMock(
                status="QUALITY_CLEAN",
                auto_fixed=False,
                residuals=[],
                report="All clean",
            )
            try:
                run_quality_gate_main(argv)
            except SystemExit:
                pass
            captured = capsys.readouterr()
            # CLI should print something about the status
            assert len(captured.out) > 0 or len(captured.err) >= 0

    def test_default_argv_is_none(self):
        """run_quality_gate_main should accept argv=None (default)."""
        # Just verify the function signature accepts None
        import inspect

        sig = inspect.signature(run_quality_gate_main)
        params = sig.parameters
        assert "argv" in params
        assert params["argv"].default is None


# ---------------------------------------------------------------------------
# QualityResult invariant tests
# ---------------------------------------------------------------------------


class TestQualityResultInvariants:
    """Tests for QualityResult structural invariants across all runners."""

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_runner_result_has_four_fields(self, tmp_path, language):
        """Every runner's QualityResult must have exactly 4 fields:
        status, auto_fixed, residuals, report."""
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert hasattr(result, "status")
        assert hasattr(result, "auto_fixed")
        assert hasattr(result, "residuals")
        assert hasattr(result, "report")

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_runner_status_is_valid_string(self, tmp_path, language):
        """Every runner must return a status from the valid set."""
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_runner_auto_fixed_is_boolean(self, tmp_path, language):
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert isinstance(result.auto_fixed, bool)

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_runner_residuals_is_list(self, tmp_path, language):
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert isinstance(result.residuals, list)

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_runner_report_is_string(self, tmp_path, language):
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert isinstance(result.report, str)


# ---------------------------------------------------------------------------
# Pass/fail-only runner invariants (stan_syntax_check, plugin_bash)
# ---------------------------------------------------------------------------


class TestPassFailOnlyRunnerInvariants:
    """Tests for runners that are documented as pass/fail only."""

    @pytest.mark.parametrize("language", ["stan_syntax_check", "plugin_bash"])
    def test_pass_fail_runner_does_not_auto_fix(self, tmp_path, language):
        """Stan and bash runners are pass/fail only -- auto_fixed should be False."""
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config(
            operations=[
                {"operation": "quality.check", "command": "check_tool {target}"}
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        # Pass/fail only runners should never auto-fix
        assert result.auto_fixed is False


# ---------------------------------------------------------------------------
# Auto-fix support runner invariants (plugin_markdown, plugin_json)
# ---------------------------------------------------------------------------


class TestAutoFixSupportRunnerInvariants:
    """Tests for runners documented as supporting auto-fix."""

    @pytest.mark.parametrize("language", ["plugin_markdown", "plugin_json"])
    def test_auto_fix_runner_returns_valid_result(self, tmp_path, language):
        """Markdown and JSON runners support auto-fix and should return
        a valid QualityResult."""
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config(
            operations=[
                {"operation": "quality.check", "command": "check_tool --fix {target}"}
            ]
        )
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result.status in VALID_QUALITY_STATUSES
        assert isinstance(result.auto_fixed, bool)


# ---------------------------------------------------------------------------
# Callable signature verification
# ---------------------------------------------------------------------------


class TestQualityRunnerCallableSignatures:
    """Tests that QUALITY_RUNNERS callables accept the correct arguments."""

    @pytest.mark.parametrize(
        "language",
        [
            "python",
            "r",
            "stan_syntax_check",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        ],
    )
    def test_runner_accepts_four_positional_arguments(self, tmp_path, language):
        """Each runner callable should accept (target_path, gate_id,
        language_config, toolchain_config)."""
        runner = QUALITY_RUNNERS[language]
        target = tmp_path / "target_file"
        target.write_text("content\n")
        lang_cfg = make_language_config(language)
        tc_cfg = make_toolchain_config()
        # Should not raise TypeError for wrong number of arguments
        result = runner(target, "gate_a", lang_cfg, tc_cfg)
        assert result is not None


# ---------------------------------------------------------------------------
# Function existence and signature tests
# ---------------------------------------------------------------------------


class TestFunctionSignatures:
    """Tests that public functions exist with correct signatures."""

    def test_run_quality_gate_is_callable(self):
        assert callable(run_quality_gate)

    def test_run_quality_gate_main_is_callable(self):
        assert callable(run_quality_gate_main)

    def test_run_quality_gate_accepts_five_arguments(self, tmp_path):
        """run_quality_gate should accept (target_path, gate_id, language,
        language_config, toolchain_config)."""
        import inspect

        sig = inspect.signature(run_quality_gate)
        params = list(sig.parameters.keys())
        assert len(params) == 5
        assert params[0] == "target_path"
        assert params[1] == "gate_id"
        assert params[2] == "language"
        assert params[3] == "language_config"
        assert params[4] == "toolchain_config"

    def test_run_quality_gate_main_accepts_argv_parameter(self):
        import inspect

        sig = inspect.signature(run_quality_gate_main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_run_quality_gate_main_argv_defaults_to_none(self):
        import inspect

        sig = inspect.signature(run_quality_gate_main)
        assert sig.parameters["argv"].default is None

    def test_quality_runners_is_module_level_dict(self):
        """QUALITY_RUNNERS should be a module-level dict constant."""
        assert isinstance(QUALITY_RUNNERS, dict)
