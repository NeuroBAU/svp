"""Tests for Bug S3-138: run_quality_gate_main exit-code contract.

Spec §3.7 (lines 3741-3742) defines run_command status as exit-code-based:
    - exit 0 → orchestrator writes COMMAND_SUCCEEDED
    - exit nonzero → orchestrator writes COMMAND_FAILED: [code]

Prior to S3-138, run_quality_gate_main printed its QUALITY_* status and
exited 0 regardless. This meant QUALITY_RESIDUAL and QUALITY_ERROR runs
silently advanced past the gate as if they had passed.

Exhaustive 4-status coverage lives here; the narrow print-only regression
tests stay in test_unit_15.py::TestRunQualityGateMainCLI.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from language_registry import QualityResult
from quality_gate import run_quality_gate_main


_LANGUAGE_CONFIG = {
    "name": "python",
    "file_extension": ".py",
    "environment_manager": "conda",
    "python_version": "3.11",
}

_TOOLCHAIN_CONFIG = {
    "environment": {
        "create": "conda create -n {env_name} python={python_version} -y",
        "install": "conda run -n {env_name} pip install {packages}",
    },
    "quality": {},
}

_SAMPLE_ARGS = [
    "--target", "/tmp/test/src/unit_1/impl.py",
    "--gate", "gate_a",
    "--unit", "1",
    "--language", "python",
    "--project-root", "/tmp/test",
]


@pytest.mark.parametrize(
    "status,expected_code",
    [
        ("QUALITY_CLEAN", 0),
        ("QUALITY_AUTO_FIXED", 0),
        ("QUALITY_RESIDUAL", 1),
        ("QUALITY_ERROR", 1),
    ],
)
@patch("quality_gate.run_quality_gate")
@patch("quality_gate.load_toolchain")
@patch("quality_gate.get_language_config")
def test_exit_code_per_quality_status(
    mock_glc, mock_lt, mock_rqg, status, expected_code, capsys
):
    """Every QUALITY_* status maps to the correct exit code per spec §3.7.

    CLEAN and AUTO_FIXED: no SystemExit (implicit exit 0).
    RESIDUAL and ERROR: SystemExit with code 1.
    Status string is printed to stdout in all cases.
    """
    mock_glc.return_value = _LANGUAGE_CONFIG
    mock_lt.return_value = _TOOLCHAIN_CONFIG
    mock_rqg.return_value = QualityResult(
        status=status,
        auto_fixed=(status == "QUALITY_AUTO_FIXED"),
        residuals=[],
        report="",
    )

    if expected_code == 0:
        # Should return cleanly (no SystemExit).
        run_quality_gate_main(_SAMPLE_ARGS)
    else:
        with pytest.raises(SystemExit) as exc:
            run_quality_gate_main(_SAMPLE_ARGS)
        assert exc.value.code == expected_code, (
            f"Status {status} should exit {expected_code}, "
            f"got {exc.value.code}"
        )

    captured = capsys.readouterr()
    assert status in captured.out, (
        f"Status {status} must still be printed to stdout as the diagnostic "
        f"record; got: {captured.out!r}"
    )
