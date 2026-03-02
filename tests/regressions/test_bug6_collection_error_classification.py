"""Regression tests for Bug 6: Fixture errors misclassified as collection errors.

_is_collection_error must NOT use a bare "ERROR" indicator. Fixture setup
errors (e.g., NotImplementedError from stubs) produce pytest "ERROR at setup
of test_X" lines, which are expected during red runs and must NOT be classified
as collection errors. Only specific indicators (ERROR collecting, ImportError,
ModuleNotFoundError, SyntaxError, no tests ran) indicate true collection errors.

DATA ASSUMPTION: Pytest output strings are synthetic but representative of
real pytest output patterns. Fixture error output matches what pytest produces
when fixtures raise NotImplementedError against stubs.
"""

import pytest

from svp.scripts.routing import _is_collection_error


class TestFixtureErrorsNotClassifiedAsCollection:
    """Bug 6: Fixture setup errors must not be classified as collection errors."""

    def test_fixture_not_implemented_error_is_not_collection(self):
        """Fixture NotImplementedError (expected during red runs) is NOT a collection error."""
        output = (
            "============================= ERRORS ==============================\n"
            "_____________ ERROR at setup of test_grid_creation ________________\n"
            "    grid = Grid(5, 5)\n"
            "E   NotImplementedError\n"
            "_____________ ERROR at setup of test_grid_step ____________________\n"
            "    grid = Grid(10, 10)\n"
            "E   NotImplementedError\n"
            "=========================== short test summary info ===============\n"
            "ERROR tests/unit_1/test_grid.py::test_grid_creation - NotImplementedError\n"
            "ERROR tests/unit_1/test_grid.py::test_grid_step - NotImplementedError\n"
            "============================== 2 errors in 0.03s =================\n"
        )
        assert _is_collection_error(output) is False, (
            "Fixture setup errors (NotImplementedError from stubs) are expected "
            "during red runs and must NOT be classified as collection errors"
        )

    def test_all_errors_no_failures_is_not_collection(self):
        """When all tests error at fixture setup with zero failures, NOT a collection error."""
        output = (
            "============================== 0 passed, 5 errors in 0.10s ========\n"
            "ERROR at setup of test_foo\n"
            "ERROR at setup of test_bar\n"
        )
        assert _is_collection_error(output) is False

    def test_error_summary_line_with_count_is_not_collection(self):
        """Pytest summary '3 errors' line should not trigger false positive."""
        output = (
            "============================= short test summary info =============\n"
            "ERROR tests/test_a.py::test_x - NotImplementedError\n"
            "============================= 3 errors in 0.05s ==================\n"
        )
        assert _is_collection_error(output) is False


class TestRealCollectionErrorsStillDetected:
    """Verify that actual collection errors are still properly detected."""

    def test_error_collecting_detected(self):
        """ERROR collecting is a true collection error."""
        output = (
            "ERROR collecting tests/unit_1/test_grid.py\n"
            "ImportError: cannot import name 'Grid' from 'src.unit_1.stub'\n"
        )
        assert _is_collection_error(output) is True

    def test_import_error_detected(self):
        """ImportError during collection is a collection error."""
        output = (
            "ImportError: No module named 'nonexistent_package'\n"
            "============================= 0 passed in 0.01s ==================\n"
        )
        assert _is_collection_error(output) is True

    def test_module_not_found_detected(self):
        """ModuleNotFoundError is a collection error."""
        output = "ModuleNotFoundError: No module named 'src.unit_2.stub'\n"
        assert _is_collection_error(output) is True

    def test_syntax_error_detected(self):
        """SyntaxError in test file is a collection error."""
        output = "SyntaxError: invalid syntax (test_grid.py, line 15)\n"
        assert _is_collection_error(output) is True

    def test_no_tests_ran_detected(self):
        """'no tests ran' is a collection error."""
        output = "============================= no tests ran ====================\n"
        assert _is_collection_error(output) is True


class TestMixedErrorsAndFailures:
    """When both errors and failures exist, not a collection error."""

    def test_errors_with_failures_is_not_collection(self):
        """If some tests failed alongside errors, not a collection error."""
        output = (
            "FAILED tests/test_a.py::test_x - AssertionError\n"
            "ERROR at setup of test_y\n"
            "============================= 1 failed, 1 error in 0.05s =========\n"
        )
        assert _is_collection_error(output) is False
