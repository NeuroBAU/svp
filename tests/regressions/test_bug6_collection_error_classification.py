"""Bug 10: Collection errors must be classified as errors, not pass/fail.

Tests that _parse_pytest_output (via TEST_OUTPUT_PARSERS["python"]) returns
errors > 0 when pytest output contains collection-error indicators like
'ERROR collecting'.
"""

from routing import TEST_OUTPUT_PARSERS


def _parse_python(output, exit_code=1, context=None):
    """Call the Python test output parser with mock pytest output."""
    parser = TEST_OUTPUT_PARSERS["python"]
    ctx = context or {
        "collection_error_indicators": [
            "ERROR collecting",
            "ImportError",
            "ModuleNotFoundError",
            "SyntaxError",
            "no tests ran",
            "collection error",
        ],
    }
    return parser(output, "python", exit_code, ctx)


def test_collection_error_returns_errors_gt_zero():
    """When output contains 'ERROR collecting', errors must be > 0."""
    output = (
        "============================= ERRORS =============================\n"
        "ERROR collecting tests/test_foo.py\n"
        "ImportError: No module named 'nonexistent'\n"
        "========================= 1 error in 0.05s =========================\n"
    )
    result = _parse_python(output)
    assert result.errors > 0, f"Expected errors > 0, got {result.errors}"


def test_collection_error_status_is_tests_error():
    """Collection errors must produce status TESTS_ERROR, not TESTS_PASSED/FAILED."""
    output = (
        "ERROR collecting tests/test_bar.py\n"
        "ModuleNotFoundError: No module named 'missing_dep'\n"
        "no tests ran\n"
    )
    result = _parse_python(output)
    assert result.status == "TESTS_ERROR", (
        f"Expected TESTS_ERROR, got {result.status}"
    )


def test_collection_error_flag_is_set():
    """collection_error field should be True for collection errors."""
    output = (
        "ERROR collecting tests/test_baz.py\n"
        "SyntaxError: invalid syntax\n"
        "1 error\n"
    )
    result = _parse_python(output)
    assert result.collection_error is True


def test_normal_failure_is_not_collection_error():
    """Normal test failures must NOT be classified as collection errors."""
    output = (
        "tests/test_math.py::test_add PASSED\n"
        "tests/test_math.py::test_sub FAILED\n"
        "==================== 1 failed, 1 passed in 0.10s ====================\n"
    )
    result = _parse_python(output, exit_code=1)
    assert result.status == "TESTS_FAILED"
    assert result.collection_error is False


def test_no_tests_ran_returns_error():
    """'no tests ran' output must produce errors > 0."""
    output = (
        "========================= no tests ran =========================\n"
    )
    result = _parse_python(output)
    assert result.errors > 0
    assert result.status == "TESTS_ERROR"
