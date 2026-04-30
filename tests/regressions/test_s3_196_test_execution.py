"""Cycle H6 (S3-196) -- verify test-execution determinism fixes:
(a) _parse_pytest_output uses exit_code==2 + anchored substrings (R1 #6);
(b) run_tests_main subprocess env override + bytes-decode (R1 #8);
(c) run_tests_main integration sub_stage path (R1 #10).

S3-103 flat-module imports.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from routing import _parse_pytest_output, run_tests_main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_toolchain(tmp_path: Path) -> None:
    """Write a minimal pipeline toolchain.json into tmp_path so that
    run_tests_main's `load_toolchain(project_root)` call succeeds."""
    toolchain = {
        "toolchain_id": "test_s3_196",
        "environment": {
            "tool": "conda",
            "run_prefix": "conda run -n {env_name}",
        },
        "testing": {
            "tool": "pytest",
            "run_command": "{run_prefix} python -m pytest {test_path} -v",
            "framework_packages": ["pytest"],
            "file_pattern": "test_*.py",
        },
        "language": {
            "name": "python",
            "extension": ".py",
            "version_constraint": ">=3.9",
            "signature_parser": "ast",
            "stub_body": "raise NotImplementedError",
        },
    }
    (tmp_path / "toolchain.json").write_text(json.dumps(toolchain))


# ---------------------------------------------------------------------------
# R1 #6 -- parser collection-error gating (4 tests)
# ---------------------------------------------------------------------------


def test_h6_parser_normal_failure_with_ImportError_in_test_code_is_not_collection_error():
    """Bug R1 #6: test code containing literal 'ImportError' would trigger
    collection_error under the substring-match rule. Post-fix: returns
    TESTS_FAILED, not TESTS_ERROR."""
    output = (
        "============= test session starts =============\n"
        "tests/test_foo.py::test_bar FAILED\n"
        "AssertionError: expected 'ImportError: oops', got 'something else'\n"
        "============= 1 failed, 13 passed in 0.5s =============\n"
    )
    result = _parse_pytest_output(output, "python", exit_code=1, context={})
    assert result.status != "TESTS_ERROR", (
        "Substring 'ImportError' in normal failure output should NOT trigger collection_error"
    )
    assert result.status == "TESTS_FAILED"
    assert result.collection_error is False


def test_h6_parser_exit_code_2_is_collection_error():
    """Bug R1 #6: exit_code==2 is pytest's documented collection-error code;
    has_collection_error MUST be True regardless of output content."""
    output = "tests/test_foo.py - SomeError\n"
    result = _parse_pytest_output(output, "python", exit_code=2, context={})
    assert result.status == "TESTS_ERROR", (
        "exit_code=2 should produce TESTS_ERROR (pytest collection-error code)"
    )
    assert result.collection_error is True


def test_h6_parser_ERROR_collecting_banner_is_collection_error():
    """Bug R1 #6: pytest banner 'ERROR collecting' MUST trigger collection_error."""
    output = (
        "==== ERRORS ====\n"
        "ERROR collecting tests/test_foo.py\n"
        "import bar  # ModuleNotFoundError\n"
    )
    result = _parse_pytest_output(output, "python", exit_code=2, context={})
    assert result.status == "TESTS_ERROR"
    assert result.collection_error is True


def test_h6_parser_no_tests_ran_is_collection_error():
    """Bug R1 #6: pytest message 'no tests ran' MUST trigger collection_error
    even when exit_code is the no-tests-collected code (5) rather than 2."""
    output = "============= no tests ran in 0.01s =============\n"
    result = _parse_pytest_output(output, "python", exit_code=5, context={})
    assert result.status == "TESTS_ERROR"
    # Either path qualifies under the new gate -- either has_collection_error
    # short-circuits via the "no tests ran" branch or the post-block
    # "no tests ran" branch fires.
    assert result.errors >= 1


# ---------------------------------------------------------------------------
# R1 #8 -- subprocess UTF-8 hygiene (3 tests)
# ---------------------------------------------------------------------------


def test_h6_run_tests_main_passes_PYTHONIOENCODING_utf8(monkeypatch, tmp_path, capsys):
    """Bug R1 #8: run_tests_main MUST set PYTHONIOENCODING=utf-8 +
    PYTHONUTF8=1 on the child subprocess.run env."""
    _write_toolchain(tmp_path)

    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs.get("env", {})
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        m = MagicMock()
        m.stdout = b"============= no tests ran in 0.01s =============\n"
        m.stderr = b""
        m.returncode = 5
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_tests_main(
        [
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(tmp_path),
            "--sub-stage",
            "red_run",
        ]
    )

    capsys.readouterr()  # drain stdout
    assert captured.get("env", {}).get("PYTHONIOENCODING") == "utf-8", (
        "subprocess.run env must set PYTHONIOENCODING=utf-8"
    )
    assert captured.get("env", {}).get("PYTHONUTF8") == "1", (
        "subprocess.run env must set PYTHONUTF8=1"
    )


def test_h6_run_tests_main_decodes_bytes_with_replace_on_invalid_utf8(monkeypatch, tmp_path, capsys):
    """Bug R1 #8: When child stdout contains invalid UTF-8 bytes, run_tests_main
    MUST decode with errors='replace' so no UnicodeDecodeError propagates."""
    _write_toolchain(tmp_path)

    invalid_utf8 = b"\x9d\xfe pytest output\nno tests ran\n"

    def fake_run(*args, **kwargs):
        m = MagicMock()
        m.stdout = invalid_utf8
        m.stderr = b""
        m.returncode = 5
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Should NOT raise UnicodeDecodeError
    run_tests_main(
        [
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(tmp_path),
            "--sub-stage",
            "red_run",
        ]
    )
    captured = capsys.readouterr()
    # Status emitted on stdout (TESTS_ERROR for the no-tests-ran path)
    assert "TESTS_ERROR" in captured.out


def test_h6_run_tests_main_does_not_use_text_True(monkeypatch, tmp_path, capsys):
    """Bug R1 #8 regression guard: subprocess.run MUST be invoked with
    capture_output=True but NOT text=True (we decode bytes manually)."""
    _write_toolchain(tmp_path)

    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        m = MagicMock()
        m.stdout = b"no tests ran\n"
        m.stderr = b""
        m.returncode = 5
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_tests_main(
        [
            "--unit",
            "1",
            "--language",
            "python",
            "--project-root",
            str(tmp_path),
            "--sub-stage",
            "red_run",
        ]
    )
    capsys.readouterr()
    assert captured.get("capture_output") is True, (
        "subprocess.run MUST use capture_output=True"
    )
    assert captured.get("text") in (None, False), (
        "subprocess.run MUST NOT use text=True (we decode bytes manually)"
    )


# ---------------------------------------------------------------------------
# R1 #10 -- integration sub_stage path (2 tests)
# ---------------------------------------------------------------------------


def test_h6_run_tests_main_integration_sub_stage_targets_integration_dir(monkeypatch, tmp_path, capsys):
    """Bug R1 #10: args.sub_stage == 'integration' -> test_cmd contains
    'tests/integration', NOT 'tests/unit_0'."""
    _write_toolchain(tmp_path)

    captured: dict = {}

    def fake_run(*args, **kwargs):
        # subprocess.run(test_cmd, shell=True, ...) -- positional first arg is the command string
        captured["test_cmd"] = args[0] if args else kwargs.get("args", "")
        m = MagicMock()
        m.stdout = b"no tests ran\n"
        m.stderr = b""
        m.returncode = 5
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_tests_main(
        [
            "--unit",
            "0",
            "--language",
            "python",
            "--project-root",
            str(tmp_path),
            "--sub-stage",
            "integration",
        ]
    )
    capsys.readouterr()

    test_cmd = captured.get("test_cmd", "")
    assert "tests/integration" in test_cmd, (
        f"integration sub_stage MUST target tests/integration, got: {test_cmd!r}"
    )
    assert "tests/unit_0" not in test_cmd, (
        f"integration sub_stage MUST NOT target tests/unit_0, got: {test_cmd!r}"
    )


def test_h6_run_tests_main_unit_sub_stage_targets_unit_dir(monkeypatch, tmp_path, capsys):
    """Bug R1 #10 regression guard: args.sub_stage != 'integration' (e.g.,
    'red_run') -> test_cmd contains 'tests/unit_<N>'."""
    _write_toolchain(tmp_path)

    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["test_cmd"] = args[0] if args else kwargs.get("args", "")
        m = MagicMock()
        m.stdout = b"no tests ran\n"
        m.stderr = b""
        m.returncode = 5
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_tests_main(
        [
            "--unit",
            "5",
            "--language",
            "python",
            "--project-root",
            str(tmp_path),
            "--sub-stage",
            "red_run",
        ]
    )
    capsys.readouterr()

    test_cmd = captured.get("test_cmd", "")
    assert "tests/unit_5" in test_cmd, (
        f"red_run sub_stage MUST target tests/unit_<N>, got: {test_cmd!r}"
    )
    assert "tests/integration" not in test_cmd
