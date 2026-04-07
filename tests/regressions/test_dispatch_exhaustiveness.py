"""test_dispatch_exhaustiveness.py -- Regression test for dispatch exhaustiveness.

NEW IN SVP 2.2 (Unit 28). This regression test verifies that all six dispatch
tables have entries for every registered language.

Tests:
- Complete dispatch tables produce empty error list
- Missing language entry produces non-empty error list
- Component-only language handling (only required tables checked)
"""
import pytest

from structural_check import validate_dispatch_exhaustiveness


# A minimal set of 6 dispatch table names matching _ALL_DISPATCH_TABLE_NAMES
_TABLE_NAMES = [
    "STUB_GENERATORS",
    "TEST_OUTPUT_PARSERS",
    "QUALITY_RUNNERS",
    "SPEC_ASSEMBLERS",
    "COMPLIANCE_SCANNERS",
    "BLUEPRINT_PARSERS",
]


def _make_full_tables(lang_id):
    """Build dispatch tables with entries for lang_id in all 6 tables."""
    return {name: {lang_id: lambda: None} for name in _TABLE_NAMES}


class TestCompleteTables:
    """Complete dispatch tables produce empty error list."""

    def test_single_language_all_tables(self):
        registry = {
            "python": {"is_component_only": False},
        }
        tables = _make_full_tables("python")
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert errors == []

    def test_multiple_languages_all_tables(self):
        registry = {
            "python": {"is_component_only": False},
            "r": {"is_component_only": False},
        }
        tables = {}
        for name in _TABLE_NAMES:
            tables[name] = {"python": lambda: None, "r": lambda: None}
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert errors == []


class TestMissingLanguageEntry:
    """Missing language in a dispatch table produces non-empty error list."""

    def test_missing_from_one_table(self):
        registry = {
            "python": {"is_component_only": False},
        }
        tables = _make_full_tables("python")
        # Remove from one table
        del tables["STUB_GENERATORS"]["python"]
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert len(errors) > 0
        assert any("python" in e and "STUB_GENERATORS" in e for e in errors)

    def test_missing_from_all_tables(self):
        registry = {
            "python": {"is_component_only": False},
        }
        tables = {name: {} for name in _TABLE_NAMES}
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert len(errors) == 6


class TestComponentLanguageHandling:
    """Component-only languages only need entries in required_dispatch_entries."""

    def test_component_with_required_entries_passes(self):
        registry = {
            "markdown": {
                "is_component_only": True,
                "required_dispatch_entries": ["STUB_GENERATORS", "TEST_OUTPUT_PARSERS"],
            },
        }
        tables = {
            "STUB_GENERATORS": {"markdown": lambda: None},
            "TEST_OUTPUT_PARSERS": {"markdown": lambda: None},
        }
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert errors == []

    def test_component_missing_required_entry_fails(self):
        registry = {
            "markdown": {
                "is_component_only": True,
                "required_dispatch_entries": ["STUB_GENERATORS", "TEST_OUTPUT_PARSERS"],
            },
        }
        tables = {
            "STUB_GENERATORS": {"markdown": lambda: None},
            "TEST_OUTPUT_PARSERS": {},
        }
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert len(errors) > 0
        assert any("markdown" in e and "TEST_OUTPUT_PARSERS" in e for e in errors)

    def test_component_not_required_in_other_tables(self):
        """Component language should NOT be flagged for tables not in required_dispatch_entries."""
        registry = {
            "markdown": {
                "is_component_only": True,
                "required_dispatch_entries": ["STUB_GENERATORS"],
            },
        }
        tables = {
            "STUB_GENERATORS": {"markdown": lambda: None},
            # markdown is NOT in other tables, but that is fine
        }
        errors = validate_dispatch_exhaustiveness(registry, tables)
        assert errors == []
