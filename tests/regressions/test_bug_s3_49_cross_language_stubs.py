"""Regression test for Bug S3-49: cross-language upstream stub generation."""
import inspect
from stub_generator import generate_upstream_stubs


def test_generate_upstream_stubs_checks_dep_unit_languages():
    """S3-49: generate_upstream_stubs must reference dep_unit.languages."""
    source = inspect.getsource(generate_upstream_stubs)
    assert "languages" in source, (
        "generate_upstream_stubs must check dep_unit.languages for per-unit language detection"
    )


def test_generate_upstream_stubs_does_not_hardcode_caller_language():
    """S3-49: Must not use caller's language for all upstream units."""
    source = inspect.getsource(generate_upstream_stubs)
    # The function should NOT pass the outer `language` variable directly to parse_signatures
    # for upstream units — it should use dep_language derived from dep_unit.languages
    lines = source.split("\n")
    for line in lines:
        if "parse_signatures" in line and "dep_" not in line and "language" in line:
            # Check it's not using the outer `language` variable
            stripped = line.strip()
            if stripped.startswith("parsed") and "language," in stripped and "dep_language" not in stripped:
                assert False, f"Line still uses caller's language: {stripped}"
