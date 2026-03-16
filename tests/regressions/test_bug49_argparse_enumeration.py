"""Bug 49 regression test: CLI argument enumeration for all
argparse-using units.

Verifies that every CLI entry point in the delivered codebase
accepts its documented argparse arguments. Catches the systemic
pattern where bare ``main() -> None: ...`` stubs in the blueprint
Tier 2 signatures lack argparse argument enumeration.

Units covered: 6, 7, 9, 10, 23.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import List

# --------------- helpers ----------------------------------- #

# Locate the scripts directory relative to this test file.
# Works in both workspace (tests/regressions/) and delivered
# repo (tests/regressions/) layouts because the scripts dir
# is always at ../../scripts or ../../svp/scripts.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent

# Try delivered layout first, then workspace layout.
_SCRIPTS_DIR = _REPO_ROOT / "svp" / "scripts"
if not _SCRIPTS_DIR.is_dir():
    _SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _capture_help(
    func,
    argv: List[str] | None = None,
) -> str:
    """Call *func* with ``["--help"]`` (or *argv*) and return
    the captured stdout/stderr combined text.

    Catches ``SystemExit`` raised by argparse on ``--help``.
    """
    if argv is None:
        argv = ["--help"]
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    saved = sys.argv
    try:
        sys.argv = ["test"] + argv
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            try:
                func()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    return buf_out.getvalue() + buf_err.getvalue()


def _capture_help_argv(
    func,
    argv: List[str] | None = None,
) -> str:
    """Like ``_capture_help`` but passes *argv* directly to
    *func(argv)* instead of patching ``sys.argv``.
    """
    if argv is None:
        argv = ["--help"]
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        try:
            func(argv)
        except SystemExit:
            pass
    return buf_out.getvalue() + buf_err.getvalue()


def _ensure_scripts_on_path() -> None:
    """Add the scripts directory to sys.path if needed."""
    s = str(_SCRIPTS_DIR)
    if s not in sys.path:
        sys.path.insert(0, s)


# --------------- Unit 6 ----------------------------------- #


class TestUnit6StubGenerator:
    """Unit 6: stub_generator.py main()."""

    def test_accepts_blueprint_dir(self) -> None:
        _ensure_scripts_on_path()
        from stub_generator import main

        help_text = _capture_help(main)
        assert "--blueprint" in help_text

    def test_accepts_unit(self) -> None:
        _ensure_scripts_on_path()
        from stub_generator import main

        help_text = _capture_help(main)
        assert "--unit" in help_text

    def test_accepts_output_dir(self) -> None:
        _ensure_scripts_on_path()
        from stub_generator import main

        help_text = _capture_help(main)
        assert "--output-dir" in help_text


# --------------- Unit 7 ----------------------------------- #


class TestUnit7DependencyExtractor:
    """Unit 7: dependency_extractor.py main()."""

    def test_accepts_project_root(self) -> None:
        _ensure_scripts_on_path()
        from dependency_extractor import main

        help_text = _capture_help(main)
        assert "--project-root" in help_text


# --------------- Unit 9 ----------------------------------- #


class TestUnit9PreparationScript:
    """Unit 9: prepare_task.py main()."""

    def test_accepts_project_root(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--project-root" in help_text

    def test_accepts_agent(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--agent" in help_text

    def test_accepts_gate(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--gate" in help_text

    def test_accepts_unit(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--unit" in help_text

    def test_accepts_output(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--output" in help_text

    def test_accepts_ladder(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--ladder" in help_text

    def test_accepts_revision_mode(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--revision-mode" in help_text

    def test_accepts_quality_report(self) -> None:
        _ensure_scripts_on_path()
        from prepare_task import main

        help_text = _capture_help(main)
        assert "--quality-report" in help_text


# --------------- Unit 10 ---------------------------------- #


class TestUnit10UpdateStateMain:
    """Unit 10: routing.py update_state_main()."""

    def test_accepts_project_root(self) -> None:
        _ensure_scripts_on_path()
        from routing import update_state_main

        help_text = _capture_help_argv(update_state_main)
        assert "--project-root" in help_text

    def test_accepts_gate(self) -> None:
        _ensure_scripts_on_path()
        from routing import update_state_main

        help_text = _capture_help_argv(update_state_main)
        # Accepts --gate-id or --gate
        assert "--gate" in help_text or "--gate-id" in help_text

    def test_accepts_unit(self) -> None:
        _ensure_scripts_on_path()
        from routing import update_state_main

        help_text = _capture_help_argv(update_state_main)
        assert "--unit" in help_text

    def test_accepts_phase(self) -> None:
        _ensure_scripts_on_path()
        from routing import update_state_main

        help_text = _capture_help_argv(update_state_main)
        assert "--phase" in help_text


class TestUnit10RunTestsMain:
    """Unit 10: routing.py run_tests_main()."""

    def test_accepts_test_path(self) -> None:
        _ensure_scripts_on_path()
        from routing import run_tests_main

        help_text = _capture_help_argv(run_tests_main)
        assert "test_path" in help_text or ("--test-path" in help_text)

    def test_accepts_env_name(self) -> None:
        _ensure_scripts_on_path()
        from routing import run_tests_main

        help_text = _capture_help_argv(run_tests_main)
        assert "--env-name" in help_text

    def test_accepts_project_root(self) -> None:
        _ensure_scripts_on_path()
        from routing import run_tests_main

        help_text = _capture_help_argv(run_tests_main)
        assert "--project-root" in help_text


class TestUnit10RunQualityGateMain:
    """Unit 10: routing.py run_quality_gate_main()."""

    def test_accepts_gate_id(self) -> None:
        _ensure_scripts_on_path()
        from routing import run_quality_gate_main

        help_text = _capture_help_argv(run_quality_gate_main)
        assert "gate_id" in help_text or "--gate" in help_text

    def test_accepts_target(self) -> None:
        _ensure_scripts_on_path()
        from routing import run_quality_gate_main

        help_text = _capture_help_argv(run_quality_gate_main)
        assert "--target" in help_text

    def test_accepts_project_root(self) -> None:
        _ensure_scripts_on_path()
        from routing import run_quality_gate_main

        help_text = _capture_help_argv(run_quality_gate_main)
        assert "--project-root" in help_text


# --------------- Unit 23 ---------------------------------- #


class TestUnit23ComplianceScanMain:
    """Unit 23: compliance_scan.py compliance_scan_main()."""

    def test_accepts_project_root(self) -> None:
        _ensure_scripts_on_path()
        from compliance_scan import compliance_scan_main

        help_text = _capture_help(compliance_scan_main)
        assert "--project-root" in help_text

    def test_accepts_src_dir(self) -> None:
        _ensure_scripts_on_path()
        from compliance_scan import compliance_scan_main

        help_text = _capture_help(compliance_scan_main)
        assert "--src-dir" in help_text

    def test_accepts_tests_dir(self) -> None:
        _ensure_scripts_on_path()
        from compliance_scan import compliance_scan_main

        help_text = _capture_help(compliance_scan_main)
        assert "--tests-dir" in help_text
