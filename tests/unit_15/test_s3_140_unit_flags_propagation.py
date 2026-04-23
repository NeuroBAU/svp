"""Tests for Bug S3-140: unit_flags propagation to resolve_command.

`_execute_gate_operations` must look up per-tool `unit_flags` from the
toolchain quality config and pass as `flags=` to `resolve_command`.
Previously `flags=""` was silently used, and mypy ran without
`--ignore-missing-imports` at every Stage 3 unit gate.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

from language_registry import QualityResult


_PYTHON_GATE_B_OPS = [
    {
        "operation": "quality.formatter.format",
        "command": "{run_prefix} ruff format {target}",
    },
    {
        "operation": "quality.linter.light",
        "command": "{run_prefix} ruff check {target}",
    },
    {
        "operation": "quality.type_checker.check",
        "command": "{run_prefix} mypy {flags} {target}",
    },
]


_TOOLCHAIN_WITH_UNIT_FLAGS = {
    "environment": {"run_prefix": "conda run -n {env_name}"},
    "quality": {
        "formatter": {
            "tool": "ruff",
            "format": "{run_prefix} ruff format {target}",
            "unit_flags": "",
        },
        "linter": {
            "tool": "ruff",
            "light": "{run_prefix} ruff check {target}",
            "unit_flags": "",
        },
        "type_checker": {
            "tool": "mypy",
            "check": "{run_prefix} mypy {flags} {target}",
            "unit_flags": "--ignore-missing-imports",
            "project_flags": "",
        },
    },
}


_TOOLCHAIN_WITHOUT_UNIT_FLAGS = {
    "environment": {"run_prefix": "conda run -n {env_name}"},
    "quality": {
        "type_checker": {
            "tool": "mypy",
            "check": "{run_prefix} mypy {flags} {target}",
            # no unit_flags declared
        },
    },
}


def _fake_run_command_success():
    """Return a subprocess-like completed process with returncode=0."""
    mock = MagicMock()
    mock.stdout = ""
    mock.stderr = ""
    mock.returncode = 0
    return mock


@patch("quality_gate._run_command")
@patch("quality_gate.resolve_command")
@patch("quality_gate.get_gate_composition")
def test_unit_flags_forwarded_when_set(mock_gc, mock_rc, mock_run):
    """When toolchain.quality.<tool>.unit_flags is set, resolve_command
    receives flags=<that value> for that tool's operation."""
    mock_gc.return_value = [_PYTHON_GATE_B_OPS[2]]  # just the type_checker op
    mock_rc.return_value = "conda run -n env mypy --ignore-missing-imports /tmp/target"
    mock_run.return_value = _fake_run_command_success()

    from quality_gate import _execute_gate_operations

    _execute_gate_operations(
        target_path=Path("/tmp/target"),
        gate_id="gate_b",
        toolchain_config=_TOOLCHAIN_WITH_UNIT_FLAGS,
        env_name="env",
    )

    assert mock_rc.call_count == 1
    call = mock_rc.call_args
    assert call.kwargs.get("flags") == "--ignore-missing-imports", (
        f"Expected flags='--ignore-missing-imports'; got {call.kwargs.get('flags')!r}"
    )


@patch("quality_gate._run_command")
@patch("quality_gate.resolve_command")
@patch("quality_gate.get_gate_composition")
def test_unit_flags_empty_when_missing(mock_gc, mock_rc, mock_run):
    """When the tool's subconfig has no unit_flags, flags='' is passed."""
    mock_gc.return_value = [_PYTHON_GATE_B_OPS[2]]
    mock_rc.return_value = "conda run -n env mypy  /tmp/target"
    mock_run.return_value = _fake_run_command_success()

    from quality_gate import _execute_gate_operations

    _execute_gate_operations(
        target_path=Path("/tmp/target"),
        gate_id="gate_b",
        toolchain_config=_TOOLCHAIN_WITHOUT_UNIT_FLAGS,
        env_name="env",
    )

    call = mock_rc.call_args
    assert call.kwargs.get("flags") == "", (
        f"Expected flags=''; got {call.kwargs.get('flags')!r}"
    )


@patch("quality_gate._run_command")
@patch("quality_gate.resolve_command")
@patch("quality_gate.get_gate_composition")
def test_non_quality_operation_does_not_trigger_lookup(mock_gc, mock_rc, mock_run):
    """Operations whose name does not start with 'quality.' get flags=''."""
    mock_gc.return_value = [
        {"operation": "test.something", "command": "{run_prefix} something {target}"}
    ]
    mock_rc.return_value = "conda run -n env something /tmp/target"
    mock_run.return_value = _fake_run_command_success()

    from quality_gate import _execute_gate_operations

    _execute_gate_operations(
        target_path=Path("/tmp/target"),
        gate_id="gate_x",
        toolchain_config=_TOOLCHAIN_WITH_UNIT_FLAGS,
        env_name="env",
    )

    call = mock_rc.call_args
    assert call.kwargs.get("flags") == "", (
        "Non-quality operation should not consult unit_flags; "
        f"got flags={call.kwargs.get('flags')!r}"
    )


@patch("quality_gate._run_command")
@patch("quality_gate.resolve_command")
@patch("quality_gate.get_gate_composition")
def test_unit_flags_per_tool_independent(mock_gc, mock_rc, mock_run):
    """Each tool's unit_flags is looked up independently: formatter='',
    type_checker='--ignore-missing-imports'. The per-call flags argument
    differs accordingly."""
    mock_gc.return_value = _PYTHON_GATE_B_OPS  # all 3 ops
    mock_rc.return_value = "some-resolved-command"
    mock_run.return_value = _fake_run_command_success()

    from quality_gate import _execute_gate_operations

    _execute_gate_operations(
        target_path=Path("/tmp/target"),
        gate_id="gate_b",
        toolchain_config=_TOOLCHAIN_WITH_UNIT_FLAGS,
        env_name="env",
    )

    assert mock_rc.call_count == 3
    flags_by_call = [call.kwargs.get("flags") for call in mock_rc.call_args_list]
    # Order matches _PYTHON_GATE_B_OPS: formatter (empty), linter (empty),
    # type_checker ('--ignore-missing-imports').
    assert flags_by_call == ["", "", "--ignore-missing-imports"], (
        f"Expected per-tool flags progression; got {flags_by_call}"
    )
