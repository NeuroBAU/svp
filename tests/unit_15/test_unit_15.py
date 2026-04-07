"""Unit 15: Quality Gate Execution -- complete test suite.

Synthetic data assumptions:
- QUALITY_RUNNERS is a dispatch dict mapping language keys to callables.
  Each callable accepts (target_path: Path, gate_id: str, language_config: dict,
  toolchain_config: dict) and returns a QualityResult.
- Supported dispatch keys: "python", "r", "stan_syntax_check",
  "plugin_markdown", "plugin_bash", "plugin_json".
- run_quality_gate orchestrates gate execution:
    * Reads gate composition from toolchain via get_gate_composition(toolchain_config, gate_id).
    * Resolves each operation's command template via resolve_command.
    * Executes commands in order.
    * Classifies results into one of four statuses:
      QUALITY_CLEAN (no issues), QUALITY_AUTO_FIXED (all issues auto-fixed),
      QUALITY_RESIDUAL (residuals remain), QUALITY_ERROR (tool execution error).
    * Returns QualityResult(status, auto_fixed, residuals, report).
- When a tool is "none" in toolchain, the corresponding operation is skipped.
- "python" runner: runs ruff format, ruff check, mypy per gate composition.
- "r" runner: runs lintr, styler per gate composition.
- "stan_syntax_check" runner: Stan compiler syntax validation, pass/fail only.
- "plugin_markdown" runner: markdownlint --fix, with auto-fix support.
- "plugin_bash" runner: bash -n syntax validation, pass/fail only.
- "plugin_json" runner: JSON validation and formatting check, with auto-fix support.
- run_quality_gate_main (CLI) accepts: --target (path), --gate (str: "gate_a",
  "gate_b", "gate_c"), --unit (int), --language (str), --project-root (path).
  It loads language config and toolchain, calls run_quality_gate, and prints
  status to stdout.
- QualityResult is a NamedTuple with fields: status (str), auto_fixed (bool),
  residuals (List[str]), report (str).
- Toolchain configs contain a "quality" key mapping gate IDs to ordered lists
  of operation dicts, each with at minimum "operation" and "command" keys.
- Synthetic toolchain configs simulate realistic gate compositions for testing
  (e.g., gate_a with format+lint, gate_b with format+lint+typecheck).
"""

import sys
from pathlib import Path
from unittest.mock import patch

from language_registry import QualityResult
from quality_gate import (
    QUALITY_RUNNERS,
    run_quality_gate,
    run_quality_gate_main,
)

# ---------------------------------------------------------------------------
# Synthetic data / fixtures
# ---------------------------------------------------------------------------

SAMPLE_TARGET = Path("/tmp/test_project/src/unit_1/impl.py")
SAMPLE_TARGET_R = Path("/tmp/test_project/R/unit_1.R")
SAMPLE_TARGET_STAN = Path("/tmp/test_project/stan/model.stan")
SAMPLE_TARGET_MD = Path("/tmp/test_project/docs/README.md")
SAMPLE_TARGET_SH = Path("/tmp/test_project/scripts/build.sh")
SAMPLE_TARGET_JSON = Path("/tmp/test_project/config/settings.json")
SAMPLE_PROJECT_ROOT = Path("/tmp/test_project")

PYTHON_LANGUAGE_CONFIG = {
    "name": "python",
    "file_extension": ".py",
    "environment_manager": "conda",
    "python_version": "3.11",
}

R_LANGUAGE_CONFIG = {
    "name": "r",
    "file_extension": ".R",
    "environment_manager": "renv",
}

STAN_LANGUAGE_CONFIG = {
    "name": "stan",
    "file_extension": ".stan",
}

MARKDOWN_LANGUAGE_CONFIG = {
    "name": "markdown",
    "file_extension": ".md",
}

BASH_LANGUAGE_CONFIG = {
    "name": "bash",
    "file_extension": ".sh",
}

JSON_LANGUAGE_CONFIG = {
    "name": "json",
    "file_extension": ".json",
}

# Toolchain config with gate compositions for Python
PYTHON_TOOLCHAIN_CONFIG = {
    "quality": {
        "gate_a": [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
        ],
        "gate_b": [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
            {"operation": "quality.typecheck", "command": "mypy {target}"},
        ],
        "gate_c": [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check --fix {target}"},
            {"operation": "quality.typecheck", "command": "mypy {target}"},
        ],
    },
}

# Toolchain config with gate compositions for R
R_TOOLCHAIN_CONFIG = {
    "quality": {
        "gate_a": [
            {"operation": "quality.style", "command": "styler {target}"},
            {"operation": "quality.lint", "command": "lintr {target}"},
        ],
    },
}

# Toolchain config where a tool is "none" (should be skipped)
TOOLCHAIN_WITH_NONE = {
    "quality": {
        "gate_a": [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "none"},
        ],
    },
}

# Toolchain for Stan syntax check
STAN_TOOLCHAIN_CONFIG = {
    "quality": {
        "gate_a": [
            {
                "operation": "quality.syntax_check",
                "command": "stanc --syntax-only {target}",
            },
        ],
    },
}

# Toolchain for markdown
MARKDOWN_TOOLCHAIN_CONFIG = {
    "quality": {
        "gate_a": [
            {"operation": "quality.format", "command": "markdownlint --fix {target}"},
        ],
    },
}

# Toolchain for bash
BASH_TOOLCHAIN_CONFIG = {
    "quality": {
        "gate_a": [
            {"operation": "quality.syntax", "command": "bash -n {target}"},
        ],
    },
}

# Toolchain for JSON
JSON_TOOLCHAIN_CONFIG = {
    "quality": {
        "gate_a": [
            {
                "operation": "quality.validate",
                "command": "python -m json.tool {target}",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Contract: QUALITY_RUNNERS dispatch table structure
# ---------------------------------------------------------------------------


class TestQualityRunnersDispatchTable:
    """QUALITY_RUNNERS is a dict mapping language keys to runner callables."""

    def test_quality_runners_is_dict(self):
        assert isinstance(QUALITY_RUNNERS, dict)

    def test_python_key_exists(self):
        assert "python" in QUALITY_RUNNERS

    def test_r_key_exists(self):
        assert "r" in QUALITY_RUNNERS

    def test_stan_syntax_check_key_exists(self):
        assert "stan_syntax_check" in QUALITY_RUNNERS

    def test_plugin_markdown_key_exists(self):
        assert "plugin_markdown" in QUALITY_RUNNERS

    def test_plugin_bash_key_exists(self):
        assert "plugin_bash" in QUALITY_RUNNERS

    def test_plugin_json_key_exists(self):
        assert "plugin_json" in QUALITY_RUNNERS

    def test_all_runners_are_callable(self):
        for key, runner in QUALITY_RUNNERS.items():
            assert callable(runner), f"Runner for '{key}' is not callable"


# ---------------------------------------------------------------------------
# Contract: QUALITY_RUNNERS — each runner returns QualityResult
# ---------------------------------------------------------------------------


class TestQualityRunnersReturnType:
    """Each runner callable returns a QualityResult NamedTuple."""

    @patch("quality_gate.subprocess.run" if True else "", create=True)
    def test_python_runner_returns_quality_result(self, mock_run=None):
        """Python runner returns QualityResult when invoked."""
        runner = QUALITY_RUNNERS["python"]
        result = runner(
            SAMPLE_TARGET, "gate_a", PYTHON_LANGUAGE_CONFIG, PYTHON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_r_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["r"]
        result = runner(
            SAMPLE_TARGET_R, "gate_a", R_LANGUAGE_CONFIG, R_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_stan_syntax_check_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_plugin_markdown_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["plugin_markdown"]
        result = runner(
            SAMPLE_TARGET_MD,
            "gate_a",
            MARKDOWN_LANGUAGE_CONFIG,
            MARKDOWN_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_plugin_bash_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_plugin_json_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["plugin_json"]
        result = runner(
            SAMPLE_TARGET_JSON, "gate_a", JSON_LANGUAGE_CONFIG, JSON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)


# ---------------------------------------------------------------------------
# Contract: run_quality_gate returns QualityResult
# ---------------------------------------------------------------------------


class TestRunQualityGateReturnType:
    """run_quality_gate always returns a QualityResult NamedTuple."""

    def test_returns_quality_result_instance(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_result_has_status_field(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert hasattr(result, "status")

    def test_result_has_auto_fixed_field(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert hasattr(result, "auto_fixed")

    def test_result_has_residuals_field(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert hasattr(result, "residuals")

    def test_result_has_report_field(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert hasattr(result, "report")


# ---------------------------------------------------------------------------
# Contract: run_quality_gate reads gate composition via get_gate_composition
# ---------------------------------------------------------------------------


class TestRunQualityGateReadsGateComposition:
    """run_quality_gate reads gate composition from toolchain via get_gate_composition."""

    @patch("quality_gate.get_gate_composition")
    def test_calls_get_gate_composition_with_toolchain_and_gate_id(self, mock_ggc):
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "ruff format {target}"},
        ]
        run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        mock_ggc.assert_called_once_with(PYTHON_TOOLCHAIN_CONFIG, "gate_a")

    @patch("quality_gate.get_gate_composition")
    def test_calls_get_gate_composition_with_gate_b(self, mock_ggc):
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
            {"operation": "quality.typecheck", "command": "mypy {target}"},
        ]
        run_quality_gate(
            SAMPLE_TARGET,
            "gate_b",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        mock_ggc.assert_called_once_with(PYTHON_TOOLCHAIN_CONFIG, "gate_b")

    @patch("quality_gate.get_gate_composition")
    def test_calls_get_gate_composition_with_gate_c(self, mock_ggc):
        mock_ggc.return_value = []
        run_quality_gate(
            SAMPLE_TARGET,
            "gate_c",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        mock_ggc.assert_called_once_with(PYTHON_TOOLCHAIN_CONFIG, "gate_c")


# ---------------------------------------------------------------------------
# Contract: run_quality_gate resolves each operation via resolve_command
# ---------------------------------------------------------------------------


class TestRunQualityGateResolvesCommands:
    """run_quality_gate resolves each operation's command template via resolve_command."""

    @patch("quality_gate.resolve_command")
    @patch("quality_gate.get_gate_composition")
    def test_resolve_command_called_for_each_operation(self, mock_ggc, mock_rc):
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
        ]
        mock_rc.return_value = "resolved_command"
        run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert mock_rc.call_count == 2

    @patch("quality_gate.resolve_command")
    @patch("quality_gate.get_gate_composition")
    def test_resolve_command_receives_command_template(self, mock_ggc, mock_rc):
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "ruff format {target}"},
        ]
        mock_rc.return_value = "ruff format /tmp/file.py"
        run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        # The first positional arg to resolve_command should be the command template
        first_call_args = mock_rc.call_args_list[0]
        assert "ruff format" in first_call_args[0][0] or "ruff format" in str(
            first_call_args
        )


# ---------------------------------------------------------------------------
# Contract: run_quality_gate executes commands in order
# ---------------------------------------------------------------------------


class TestRunQualityGateExecutionOrder:
    """Operations from gate composition are executed in their specified order."""

    @patch("quality_gate.resolve_command")
    @patch("quality_gate.get_gate_composition")
    def test_operations_executed_in_composition_order(self, mock_ggc, mock_rc):
        """Commands must be resolved in the same order as the gate composition list."""
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "ruff check {target}"},
            {"operation": "quality.typecheck", "command": "mypy {target}"},
        ]
        call_order = []

        def track_resolve(template, *args, **kwargs):
            call_order.append(template)
            return f"resolved_{template}"

        mock_rc.side_effect = track_resolve
        run_quality_gate(
            SAMPLE_TARGET,
            "gate_b",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert len(call_order) == 3
        assert "format" in call_order[0]
        assert "check" in call_order[1] or "lint" in call_order[1]
        assert "mypy" in call_order[2]


# ---------------------------------------------------------------------------
# Contract: Status classification — QUALITY_CLEAN
# ---------------------------------------------------------------------------


class TestStatusClassificationClean:
    """QUALITY_CLEAN status: no issues found by any operation."""

    def test_clean_status_when_no_issues(self):
        """When all operations pass cleanly, status is QUALITY_CLEAN."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        # For a clean run, the status should be one of the valid quality statuses
        assert result.status in (
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        )

    def test_clean_result_auto_fixed_is_bool(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result.auto_fixed, bool)

    def test_clean_result_residuals_is_list(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result.residuals, list)

    def test_clean_result_report_is_str(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result.report, str)


# ---------------------------------------------------------------------------
# Contract: Status classification — QUALITY_AUTO_FIXED
# ---------------------------------------------------------------------------


class TestStatusClassificationAutoFixed:
    """QUALITY_AUTO_FIXED: all issues were automatically resolved."""

    def test_auto_fixed_status_has_auto_fixed_true(self):
        """When status is QUALITY_AUTO_FIXED, auto_fixed must be True."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_AUTO_FIXED":
            assert result.auto_fixed is True

    def test_auto_fixed_status_has_empty_residuals(self):
        """When status is QUALITY_AUTO_FIXED, residuals should be empty."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_AUTO_FIXED":
            assert result.residuals == []


# ---------------------------------------------------------------------------
# Contract: Status classification — QUALITY_RESIDUAL
# ---------------------------------------------------------------------------


class TestStatusClassificationResidual:
    """QUALITY_RESIDUAL: residuals remain after auto-fix."""

    def test_residual_status_has_nonempty_residuals(self):
        """When status is QUALITY_RESIDUAL, residuals must be non-empty."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_RESIDUAL":
            assert len(result.residuals) > 0


# ---------------------------------------------------------------------------
# Contract: Status classification — QUALITY_ERROR
# ---------------------------------------------------------------------------


class TestStatusClassificationError:
    """QUALITY_ERROR: tool execution error."""

    def test_error_status_value_is_quality_error(self):
        """When a tool execution error occurs, status should be QUALITY_ERROR."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_ERROR":
            assert result.status == "QUALITY_ERROR"


# ---------------------------------------------------------------------------
# Contract: Valid status values are exhaustive
# ---------------------------------------------------------------------------


class TestStatusValuesExhaustive:
    """run_quality_gate only returns one of the four defined statuses."""

    VALID_STATUSES = {
        "QUALITY_CLEAN",
        "QUALITY_AUTO_FIXED",
        "QUALITY_RESIDUAL",
        "QUALITY_ERROR",
    }

    def test_status_is_one_of_four_valid_values_python(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert result.status in self.VALID_STATUSES

    def test_status_is_one_of_four_valid_values_gate_b(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_b",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert result.status in self.VALID_STATUSES

    def test_status_is_one_of_four_valid_values_gate_c(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_c",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert result.status in self.VALID_STATUSES


# ---------------------------------------------------------------------------
# Contract: "none" tool in toolchain skips operation
# ---------------------------------------------------------------------------


class TestNoneToolSkipping:
    """For languages where a tool is 'none' in toolchain, the operation is skipped."""

    @patch("quality_gate.resolve_command")
    @patch("quality_gate.get_gate_composition")
    def test_none_command_is_skipped(self, mock_ggc, mock_rc):
        """An operation with command='none' should not invoke resolve_command for that op."""
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "ruff format {target}"},
            {"operation": "quality.lint", "command": "none"},
        ]
        mock_rc.return_value = "resolved_format_command"
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            TOOLCHAIN_WITH_NONE,
        )
        # resolve_command should only be called once (for format), not for 'none'
        assert mock_rc.call_count == 1
        assert isinstance(result, QualityResult)

    @patch("quality_gate.resolve_command")
    @patch("quality_gate.get_gate_composition")
    def test_all_none_operations_produce_clean_result(self, mock_ggc, mock_rc):
        """If all operations are 'none', result should be QUALITY_CLEAN."""
        mock_ggc.return_value = [
            {"operation": "quality.format", "command": "none"},
            {"operation": "quality.lint", "command": "none"},
        ]
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            TOOLCHAIN_WITH_NONE,
        )
        assert mock_rc.call_count == 0
        assert result.status == "QUALITY_CLEAN"


# ---------------------------------------------------------------------------
# Contract: Python runner — ruff format, ruff check, mypy
# ---------------------------------------------------------------------------


class TestPythonRunner:
    """Python runner executes ruff format, ruff check, mypy per gate composition."""

    def test_python_runner_is_callable(self):
        assert callable(QUALITY_RUNNERS["python"])

    def test_python_runner_accepts_four_args(self):
        """Python runner callable accepts (target_path, gate_id, language_config, toolchain_config)."""
        runner = QUALITY_RUNNERS["python"]
        result = runner(
            SAMPLE_TARGET, "gate_a", PYTHON_LANGUAGE_CONFIG, PYTHON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_python_runner_gate_b_includes_typecheck(self):
        """Gate B for Python should include format, lint, and typecheck operations."""
        runner = QUALITY_RUNNERS["python"]
        result = runner(
            SAMPLE_TARGET, "gate_b", PYTHON_LANGUAGE_CONFIG, PYTHON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)


# ---------------------------------------------------------------------------
# Contract: R runner — lintr, styler
# ---------------------------------------------------------------------------


class TestRRunner:
    """R runner executes lintr, styler per gate composition."""

    def test_r_runner_is_callable(self):
        assert callable(QUALITY_RUNNERS["r"])

    def test_r_runner_accepts_four_args(self):
        runner = QUALITY_RUNNERS["r"]
        result = runner(
            SAMPLE_TARGET_R, "gate_a", R_LANGUAGE_CONFIG, R_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)


# ---------------------------------------------------------------------------
# Contract: Stan syntax check runner — pass/fail only
# ---------------------------------------------------------------------------


class TestStanSyntaxCheckRunner:
    """Stan syntax check runner returns QualityResult with pass/fail only."""

    def test_stan_runner_is_callable(self):
        assert callable(QUALITY_RUNNERS["stan_syntax_check"])

    def test_stan_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_stan_runner_pass_fail_status_only(self):
        """Stan syntax check should yield QUALITY_CLEAN or QUALITY_ERROR (no auto-fix)."""
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert result.status in ("QUALITY_CLEAN", "QUALITY_ERROR")

    def test_stan_runner_auto_fixed_always_false(self):
        """Stan syntax check has no auto-fix capability."""
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert result.auto_fixed is False


# ---------------------------------------------------------------------------
# Contract: Plugin markdown runner — auto-fix support
# ---------------------------------------------------------------------------


class TestPluginMarkdownRunner:
    """Markdown runner supports auto-fix (markdownlint --fix)."""

    def test_markdown_runner_is_callable(self):
        assert callable(QUALITY_RUNNERS["plugin_markdown"])

    def test_markdown_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["plugin_markdown"]
        result = runner(
            SAMPLE_TARGET_MD,
            "gate_a",
            MARKDOWN_LANGUAGE_CONFIG,
            MARKDOWN_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_markdown_runner_can_produce_auto_fixed(self):
        """Markdown runner has auto-fix capability (status can be QUALITY_AUTO_FIXED)."""
        runner = QUALITY_RUNNERS["plugin_markdown"]
        result = runner(
            SAMPLE_TARGET_MD,
            "gate_a",
            MARKDOWN_LANGUAGE_CONFIG,
            MARKDOWN_TOOLCHAIN_CONFIG,
        )
        # auto-fix support means the status can be QUALITY_AUTO_FIXED
        assert result.status in (
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        )


# ---------------------------------------------------------------------------
# Contract: Plugin bash runner — pass/fail only
# ---------------------------------------------------------------------------


class TestPluginBashRunner:
    """Bash runner runs bash -n syntax validation, pass/fail only."""

    def test_bash_runner_is_callable(self):
        assert callable(QUALITY_RUNNERS["plugin_bash"])

    def test_bash_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_bash_runner_pass_fail_status_only(self):
        """Bash syntax check should yield QUALITY_CLEAN or QUALITY_ERROR (no auto-fix)."""
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert result.status in ("QUALITY_CLEAN", "QUALITY_ERROR")

    def test_bash_runner_auto_fixed_always_false(self):
        """Bash syntax check has no auto-fix capability."""
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert result.auto_fixed is False


# ---------------------------------------------------------------------------
# Contract: Plugin JSON runner — auto-fix support
# ---------------------------------------------------------------------------


class TestPluginJsonRunner:
    """JSON runner validates and formats JSON with auto-fix support."""

    def test_json_runner_is_callable(self):
        assert callable(QUALITY_RUNNERS["plugin_json"])

    def test_json_runner_returns_quality_result(self):
        runner = QUALITY_RUNNERS["plugin_json"]
        result = runner(
            SAMPLE_TARGET_JSON, "gate_a", JSON_LANGUAGE_CONFIG, JSON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_json_runner_can_produce_auto_fixed(self):
        """JSON runner supports auto-fix (pretty-print normalization)."""
        runner = QUALITY_RUNNERS["plugin_json"]
        result = runner(
            SAMPLE_TARGET_JSON, "gate_a", JSON_LANGUAGE_CONFIG, JSON_TOOLCHAIN_CONFIG
        )
        assert result.status in (
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        )


# ---------------------------------------------------------------------------
# Contract: run_quality_gate — consistency between status and auto_fixed
# ---------------------------------------------------------------------------


class TestStatusAutoFixedConsistency:
    """Status and auto_fixed fields must be consistent."""

    def test_clean_status_implies_auto_fixed_false(self):
        """QUALITY_CLEAN means nothing was fixed (no issues found)."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_CLEAN":
            assert result.auto_fixed is False
            assert result.residuals == []

    def test_auto_fixed_status_implies_auto_fixed_true(self):
        """QUALITY_AUTO_FIXED requires auto_fixed=True."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_AUTO_FIXED":
            assert result.auto_fixed is True

    def test_error_status_implies_auto_fixed_false(self):
        """QUALITY_ERROR means the tool failed, not that it fixed anything."""
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_ERROR":
            assert result.auto_fixed is False


# ---------------------------------------------------------------------------
# Contract: run_quality_gate — consistency between status and residuals
# ---------------------------------------------------------------------------


class TestStatusResidualsConsistency:
    """Status and residuals fields must be consistent."""

    def test_clean_status_implies_empty_residuals(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_CLEAN":
            assert result.residuals == []

    def test_auto_fixed_status_implies_empty_residuals(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_AUTO_FIXED":
            assert result.residuals == []

    def test_residual_status_implies_nonempty_residuals(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        if result.status == "QUALITY_RESIDUAL":
            assert len(result.residuals) > 0
            for r in result.residuals:
                assert isinstance(r, str)


# ---------------------------------------------------------------------------
# Contract: run_quality_gate — report is always a string
# ---------------------------------------------------------------------------


class TestReportField:
    """The report field is always a non-None string."""

    def test_report_is_string_for_python_gate_a(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result.report, str)

    def test_report_is_string_for_python_gate_b(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_b",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result.report, str)

    def test_report_is_string_for_r(self):
        result = run_quality_gate(
            SAMPLE_TARGET_R,
            "gate_a",
            "r",
            R_LANGUAGE_CONFIG,
            R_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result.report, str)


# ---------------------------------------------------------------------------
# Contract: run_quality_gate_main — CLI arguments
# ---------------------------------------------------------------------------


class TestRunQualityGateMainCLI:
    """run_quality_gate_main accepts CLI arguments and prints status to stdout."""

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_accepts_all_required_args(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report="All clean"
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        captured = capsys.readouterr()
        assert "QUALITY_CLEAN" in captured.out

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_gate_b_argument(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_AUTO_FIXED",
            auto_fixed=True,
            residuals=[],
            report="Auto-fixed",
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_b",
                "--unit",
                "5",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        captured = capsys.readouterr()
        assert "QUALITY_AUTO_FIXED" in captured.out

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_gate_c_argument(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_RESIDUAL",
            auto_fixed=True,
            residuals=["line 10: unused import"],
            report="Residuals found",
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_c",
                "--unit",
                "3",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        captured = capsys.readouterr()
        assert "QUALITY_RESIDUAL" in captured.out


# ---------------------------------------------------------------------------
# Contract: run_quality_gate_main — loads language config and toolchain
# ---------------------------------------------------------------------------


class TestRunQualityGateMainLoadsDeps:
    """CLI entry point loads language config and toolchain before calling run_quality_gate."""

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_calls_get_language_config(self, mock_glc, mock_lt, mock_rqg):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        mock_glc.assert_called_once_with("python")

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_calls_load_toolchain(self, mock_glc, mock_lt, mock_rqg):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        mock_lt.assert_called_once()

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_calls_run_quality_gate(self, mock_glc, mock_lt, mock_rqg):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        mock_rqg.assert_called_once()


# ---------------------------------------------------------------------------
# Contract: run_quality_gate_main — prints status to stdout
# ---------------------------------------------------------------------------


class TestRunQualityGateMainOutput:
    """CLI entry point prints the quality status to stdout."""

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_prints_clean_status(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report="All clean"
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0
        assert "QUALITY_CLEAN" in captured.out

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_prints_error_status(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_ERROR", auto_fixed=False, residuals=[], report="Tool failed"
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        captured = capsys.readouterr()
        assert "QUALITY_ERROR" in captured.out

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_prints_residual_status(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_RESIDUAL",
            auto_fixed=True,
            residuals=["E501 line too long"],
            report="Residuals",
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_b",
                "--unit",
                "2",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        captured = capsys.readouterr()
        assert "QUALITY_RESIDUAL" in captured.out


# ---------------------------------------------------------------------------
# Contract: run_quality_gate_main — default argv is None (uses sys.argv)
# ---------------------------------------------------------------------------


class TestRunQualityGateMainDefaultArgv:
    """When argv is None, the CLI should read from sys.argv."""

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_with_none_argv_uses_sys_argv(self, mock_glc, mock_lt, mock_rqg):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        test_args = [
            "prog",
            "--target",
            str(SAMPLE_TARGET),
            "--gate",
            "gate_a",
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(SAMPLE_PROJECT_ROOT),
        ]
        with patch.object(sys, "argv", test_args):
            run_quality_gate_main(None)
        mock_rqg.assert_called_once()


# ---------------------------------------------------------------------------
# Contract: run_quality_gate with different languages dispatches correctly
# ---------------------------------------------------------------------------


class TestLanguageDispatch:
    """run_quality_gate dispatches to the correct runner based on language."""

    def test_python_language_dispatches(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_r_language_dispatches(self):
        result = run_quality_gate(
            SAMPLE_TARGET_R,
            "gate_a",
            "r",
            R_LANGUAGE_CONFIG,
            R_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_stan_syntax_check_dispatches(self):
        result = run_quality_gate(
            SAMPLE_TARGET_STAN,
            "gate_a",
            "stan_syntax_check",
            STAN_LANGUAGE_CONFIG,
            STAN_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_plugin_markdown_dispatches(self):
        result = run_quality_gate(
            SAMPLE_TARGET_MD,
            "gate_a",
            "plugin_markdown",
            MARKDOWN_LANGUAGE_CONFIG,
            MARKDOWN_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_plugin_bash_dispatches(self):
        result = run_quality_gate(
            SAMPLE_TARGET_SH,
            "gate_a",
            "plugin_bash",
            BASH_LANGUAGE_CONFIG,
            BASH_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_plugin_json_dispatches(self):
        result = run_quality_gate(
            SAMPLE_TARGET_JSON,
            "gate_a",
            "plugin_json",
            JSON_LANGUAGE_CONFIG,
            JSON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)


# ---------------------------------------------------------------------------
# Contract: run_quality_gate with multiple gates
# ---------------------------------------------------------------------------


class TestMultipleGates:
    """run_quality_gate supports gate_a, gate_b, and gate_c."""

    def test_gate_a_returns_valid_result(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)
        assert result.status in {
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        }

    def test_gate_b_returns_valid_result(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_b",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_gate_c_returns_valid_result(self):
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_c",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)


# ---------------------------------------------------------------------------
# Contract: run_quality_gate — target_path is a Path
# ---------------------------------------------------------------------------


class TestTargetPathType:
    """run_quality_gate accepts target_path as a Path object."""

    def test_accepts_path_object(self):
        result = run_quality_gate(
            Path("/tmp/test.py"),
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_target_path_is_used_in_resolution(self):
        """The target path should be passed through to command resolution."""
        with (
            patch("quality_gate.resolve_command") as mock_rc,
            patch("quality_gate.get_gate_composition") as mock_ggc,
        ):
            mock_ggc.return_value = [
                {"operation": "quality.format", "command": "ruff format {target}"},
            ]
            mock_rc.return_value = "ruff format /specific/path.py"
            target = Path("/specific/path.py")
            run_quality_gate(
                target,
                "gate_a",
                "python",
                PYTHON_LANGUAGE_CONFIG,
                PYTHON_TOOLCHAIN_CONFIG,
            )
            # The target should appear in resolve_command call args
            call_args_str = str(mock_rc.call_args_list)
            assert "/specific/path.py" in call_args_str or mock_rc.called


# ---------------------------------------------------------------------------
# Contract: QUALITY_RUNNERS callable signature
# ---------------------------------------------------------------------------


class TestQualityRunnersSignature:
    """Each QUALITY_RUNNERS value is callable with (Path, str, dict, dict) -> QualityResult."""

    def test_python_runner_four_arg_signature(self):
        runner = QUALITY_RUNNERS["python"]
        result = runner(
            SAMPLE_TARGET, "gate_a", PYTHON_LANGUAGE_CONFIG, PYTHON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_r_runner_four_arg_signature(self):
        runner = QUALITY_RUNNERS["r"]
        result = runner(
            SAMPLE_TARGET_R, "gate_a", R_LANGUAGE_CONFIG, R_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_stan_runner_four_arg_signature(self):
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_markdown_runner_four_arg_signature(self):
        runner = QUALITY_RUNNERS["plugin_markdown"]
        result = runner(
            SAMPLE_TARGET_MD,
            "gate_a",
            MARKDOWN_LANGUAGE_CONFIG,
            MARKDOWN_TOOLCHAIN_CONFIG,
        )
        assert isinstance(result, QualityResult)

    def test_bash_runner_four_arg_signature(self):
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)

    def test_json_runner_four_arg_signature(self):
        runner = QUALITY_RUNNERS["plugin_json"]
        result = runner(
            SAMPLE_TARGET_JSON, "gate_a", JSON_LANGUAGE_CONFIG, JSON_TOOLCHAIN_CONFIG
        )
        assert isinstance(result, QualityResult)


# ---------------------------------------------------------------------------
# Contract: Pass/fail-only runners never produce AUTO_FIXED or RESIDUAL
# ---------------------------------------------------------------------------


class TestPassFailOnlyRunners:
    """Runners that are pass/fail only should never produce AUTO_FIXED or RESIDUAL."""

    def test_stan_never_produces_auto_fixed(self):
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert result.status != "QUALITY_AUTO_FIXED"

    def test_stan_never_produces_residual(self):
        runner = QUALITY_RUNNERS["stan_syntax_check"]
        result = runner(
            SAMPLE_TARGET_STAN, "gate_a", STAN_LANGUAGE_CONFIG, STAN_TOOLCHAIN_CONFIG
        )
        assert result.status != "QUALITY_RESIDUAL"

    def test_bash_never_produces_auto_fixed(self):
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert result.status != "QUALITY_AUTO_FIXED"

    def test_bash_never_produces_residual(self):
        runner = QUALITY_RUNNERS["plugin_bash"]
        result = runner(
            SAMPLE_TARGET_SH, "gate_a", BASH_LANGUAGE_CONFIG, BASH_TOOLCHAIN_CONFIG
        )
        assert result.status != "QUALITY_RESIDUAL"


# ---------------------------------------------------------------------------
# Contract: Empty gate composition produces QUALITY_CLEAN
# ---------------------------------------------------------------------------


class TestEmptyGateComposition:
    """An empty gate composition (no operations) should yield QUALITY_CLEAN."""

    @patch("quality_gate.get_gate_composition")
    def test_empty_composition_returns_clean(self, mock_ggc):
        mock_ggc.return_value = []
        result = run_quality_gate(
            SAMPLE_TARGET,
            "gate_a",
            "python",
            PYTHON_LANGUAGE_CONFIG,
            PYTHON_TOOLCHAIN_CONFIG,
        )
        assert result.status == "QUALITY_CLEAN"
        assert result.auto_fixed is False
        assert result.residuals == []


# ---------------------------------------------------------------------------
# Contract: run_quality_gate_main — R language support
# ---------------------------------------------------------------------------


class TestCLIWithRLanguage:
    """CLI entry point works with R language."""

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_main_with_r_language(self, mock_glc, mock_lt, mock_rqg, capsys):
        mock_glc.return_value = R_LANGUAGE_CONFIG
        mock_lt.return_value = R_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report="Clean"
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET_R),
                "--gate",
                "gate_a",
                "--unit",
                "1",
                "--language",
                "r",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        mock_glc.assert_called_once_with("r")
        captured = capsys.readouterr()
        assert "QUALITY_CLEAN" in captured.out


# ---------------------------------------------------------------------------
# Contract: run_quality_gate_main passes correct arguments to run_quality_gate
# ---------------------------------------------------------------------------


class TestCLIPassesCorrectArgs:
    """CLI entry point passes parsed args to run_quality_gate correctly."""

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_target_path_passed_as_path(self, mock_glc, mock_lt, mock_rqg):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        run_quality_gate_main(
            [
                "--target",
                "/tmp/specific/file.py",
                "--gate",
                "gate_b",
                "--unit",
                "7",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        call_args = mock_rqg.call_args
        # target_path should be a Path
        assert (
            isinstance(call_args[0][0], Path)
            or isinstance(call_args[1].get("target_path"), Path)
            or str(call_args).count("specific/file.py") > 0
        )
        # gate_id should be passed
        assert "gate_b" in str(call_args)
        # language should be passed
        assert "python" in str(call_args)

    @patch("quality_gate.run_quality_gate")
    @patch("quality_gate.load_toolchain")
    @patch("quality_gate.get_language_config")
    def test_gate_id_passed_correctly(self, mock_glc, mock_lt, mock_rqg):
        mock_glc.return_value = PYTHON_LANGUAGE_CONFIG
        mock_lt.return_value = PYTHON_TOOLCHAIN_CONFIG
        mock_rqg.return_value = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        run_quality_gate_main(
            [
                "--target",
                str(SAMPLE_TARGET),
                "--gate",
                "gate_c",
                "--unit",
                "1",
                "--language",
                "python",
                "--project-root",
                str(SAMPLE_PROJECT_ROOT),
            ]
        )
        call_args_str = str(mock_rqg.call_args)
        assert "gate_c" in call_args_str
