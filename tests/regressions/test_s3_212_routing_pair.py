"""Regression tests for Bug S3-212 -- Unit 14 routing pair.

  * BUG-4 -- gate_1_2_spec_post_review REVISE must route to the
    targeted_spec_revision sub-stage (mirror gate_2_3 REVISE SPEC) so post-review
    fixes are actually applied via stakeholder_dialog, instead of dead-ending by
    re-invoking stakeholder_reviewer on the unchanged spec.
  * BUG-7 -- _parse_pytest_output must read pass/fail/error COUNTS only from
    pytest's summary line, not the verbose -v body (whose echoed docstrings/IDs
    like "REQ-PSF-01 error." overmatch the error-count regex -> false TESTS_ERROR).

Flat-module imports resolve via pyproject.toml pythonpath = [src, scripts].
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import (
    _parse_pytest_output,
    _pytest_summary_count_source,
    _route_stage_1,
    dispatch_gate_response,
)


# ---------------------------------------------------------------------------
# BUG-4 -- gate_1_2 REVISE routes to targeted_spec_revision
# ---------------------------------------------------------------------------


def test_s3_212_gate_1_2_revise_advances_to_targeted_spec_revision():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = PipelineState(stage="1", sub_stage="spec_review")
        save_state(root, state)
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "REVISE", root
        )
    assert result.stage == "1"
    assert result.sub_stage == "targeted_spec_revision"


def test_s3_212_gate_1_2_revise_then_routes_to_stakeholder_dialog_not_reviewer():
    """After REVISE, the next Stage-1 pass invokes stakeholder_dialog (to apply
    the revision), NOT stakeholder_reviewer (the pre-fix dead-end)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = PipelineState(stage="1", sub_stage="spec_review")
        save_state(root, state)
        revised = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "REVISE", root
        )
        save_state(root, revised)
        action = _route_stage_1(revised, root, "")
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "stakeholder_dialog"
    assert action["agent_type"] != "stakeholder_reviewer"


# ---------------------------------------------------------------------------
# BUG-7 -- counts read from the summary line, not the verbose body
# ---------------------------------------------------------------------------

# A realistic failing-run body: an error-path test whose docstring contains the
# literal "REQ-PSF-01 error." (the overmatch trigger), plus the real pytest
# result-summary line reporting failures (no errors).
_FAILED_OUTPUT = (
    "============================= test session starts ==============================\n"
    "collected 41 items\n\n"
    "tests/unit_2/test_psf.py::test_error_path\n"
    '    """Error path for REQ-PSF-01 error."""\n'
    "tests/unit_2/test_psf.py::test_error_path FAILED\n"
    "=========================== short test summary info ============================\n"
    "FAILED tests/unit_2/test_psf.py::test_error_path - AssertionError\n"
    "========================= 39 failed, 2 passed in 0.12s =========================\n"
)

_ERROR_OUTPUT = (
    "============================= test session starts ==============================\n"
    "collected 1 item\n\n"
    "tests/unit_2/test_psf.py::test_x\n"
    "=========================== short test summary info ============================\n"
    "ERROR tests/unit_2/test_psf.py::test_x\n"
    "============================== 1 error in 0.03s ===============================\n"
)


def test_s3_212_failed_run_with_error_in_docstring_is_tests_failed():
    result = _parse_pytest_output(_FAILED_OUTPUT, "python", 1, {})
    assert result.status == "TESTS_FAILED"
    assert result.failed == 39
    assert result.passed == 2
    assert result.errors == 0


def test_s3_212_genuine_error_summary_still_tests_error():
    result = _parse_pytest_output(_ERROR_OUTPUT, "python", 1, {})
    assert result.status == "TESTS_ERROR"
    assert result.errors == 1


def test_s3_212_bannerless_output_falls_back_to_whole_body():
    result = _parse_pytest_output("5 passed in 1.2s", "python", 0, {})
    assert result.status == "TESTS_PASSED"
    assert result.passed == 5


def test_s3_212_summary_count_source_prefers_summary_line():
    src = _pytest_summary_count_source(_FAILED_OUTPUT)
    assert "39 failed" in src
    assert "REQ-PSF-01" not in src  # the verbose body is excluded


def test_s3_212_summary_count_source_falls_back_when_no_banner():
    assert _pytest_summary_count_source("5 passed in 1.2s") == "5 passed in 1.2s"
