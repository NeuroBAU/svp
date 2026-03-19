"""Bug 6 regression: _is_collection_error must detect known indicators.

The function must correctly classify output containing known collection
error indicators (ModuleNotFoundError, ImportError, SyntaxError, etc.).
"""

from routing import _is_collection_error


def test_detects_module_not_found():
    assert _is_collection_error("ModuleNotFoundError: No module named 'foo'") is True


def test_detects_import_error():
    assert _is_collection_error("ImportError: cannot import name 'bar'") is True


def test_detects_syntax_error():
    assert _is_collection_error("SyntaxError: invalid syntax") is True


def test_detects_no_tests_ran():
    assert _is_collection_error("no tests ran") is True


def test_detects_error_collecting():
    assert _is_collection_error("ERROR collecting tests/test_foo.py") is True


def test_clean_output_not_classified():
    assert _is_collection_error("3 passed in 0.5s") is False


def test_custom_indicators_from_toolchain():
    """When toolchain provides custom indicators, use those."""
    tc = {"testing": {"collection_error_indicators": ["CUSTOM_ERROR"]}}
    assert _is_collection_error("CUSTOM_ERROR happened", tc) is True
    assert _is_collection_error("ModuleNotFoundError", tc) is False
