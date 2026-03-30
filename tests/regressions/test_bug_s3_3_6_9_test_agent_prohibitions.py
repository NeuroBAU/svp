"""
Regression test for Bugs S3-3, S3-6, S3-9: TEST_AGENT_DEFINITION must contain
explicit prohibitions against common test generation anti-patterns.
"""
from src.unit_20.stub import TEST_AGENT_DEFINITION


def _lower(text):
    return text.lower()


def test_prohibits_pytest_raises_not_implemented_error():
    """S3-3: Definition must prohibit pytest.raises(NotImplementedError)."""
    lower = _lower(TEST_AGENT_DEFINITION)
    assert "pytest.raises(notimplementederror)" in lower or (
        "notimplementederror" in lower and "prohibit" in lower
    )


def test_prohibits_pytest_skip_for_stubs():
    """S3-6: Definition must prohibit pytest.skip for unimplemented stubs."""
    lower = _lower(TEST_AGENT_DEFINITION)
    assert "pytest.skip" in lower


def test_mandates_src_prefix_import():
    """S3-9: Definition must mandate src. prefix in import paths."""
    lower = _lower(TEST_AGENT_DEFINITION)
    assert "src.unit_" in lower or "from src." in lower
