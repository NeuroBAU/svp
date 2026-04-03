"""test_r_test_output_parsing.py -- Regression test for R test output parsing.

NEW IN SVP 2.2 (Unit 14). This regression test verifies that the R test output
parser correctly extracts OK/Failed/Warnings counts from testthat output.

Tests:
- Parsing "OK: N" lines
- Parsing "Failed: N" lines
- Empty output handling
- RunResult return type
"""
import pytest

from src.unit_14.stub import _parse_testthat_output
from src.unit_2.stub import RunResult


class TestParseOKLines:
    """Parser extracts OK count from testthat output."""

    def test_ok_count_extracted(self):
        output = "OK: 5\nFailed: 0\n"
        result = _parse_testthat_output(output, "r", 0, {})
        assert result.passed == 5

    def test_ok_only_produces_passed(self):
        output = "OK: 10\n"
        result = _parse_testthat_output(output, "r", 0, {})
        assert result.status == "TESTS_PASSED"
        assert result.passed == 10
        assert result.failed == 0


class TestParseFailedLines:
    """Parser extracts Failed count from testthat output."""

    def test_failed_count_extracted(self):
        output = "OK: 3\nFailed: 2\n"
        result = _parse_testthat_output(output, "r", 1, {})
        assert result.failed == 2

    def test_failed_produces_tests_failed(self):
        output = "OK: 3\nFailed: 2\n"
        result = _parse_testthat_output(output, "r", 1, {})
        assert result.status == "TESTS_FAILED"

    def test_failed_with_warnings(self):
        output = "OK: 3\nFailed: 1\nWarnings: 2\n"
        result = _parse_testthat_output(output, "r", 1, {})
        # Failed takes priority over warnings
        assert result.status == "TESTS_FAILED"
        assert result.failed == 1


class TestEmptyOutput:
    """Parser handles empty or no-results output."""

    def test_empty_string_produces_error(self):
        result = _parse_testthat_output("", "r", 1, {})
        assert result.status == "TESTS_ERROR"
        assert result.passed == 0
        assert result.failed == 0

    def test_no_counts_produces_error(self):
        result = _parse_testthat_output("some random output\n", "r", 1, {})
        assert result.status == "TESTS_ERROR"


class TestRunResultType:
    """Parser returns RunResult instances with correct fields."""

    def test_returns_run_result(self):
        output = "OK: 5\nFailed: 0\n"
        result = _parse_testthat_output(output, "r", 0, {})
        assert isinstance(result, RunResult)

    def test_run_result_has_output(self):
        output = "OK: 5\nFailed: 0\n"
        result = _parse_testthat_output(output, "r", 0, {})
        assert result.output == output

    def test_run_result_has_collection_error_flag(self):
        output = "OK: 5\nFailed: 0\n"
        result = _parse_testthat_output(output, "r", 0, {})
        assert result.collection_error is False
