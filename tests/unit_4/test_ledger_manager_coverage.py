"""
Coverage-gap tests for Unit 4: Ledger Manager.

These tests close gaps identified during blueprint
contract review. Each test class documents which
Tier 2 or Tier 3 contract it covers.

Synthetic Data Assumptions:
- Same as test_ledger_manager.py.
"""

import json
from pathlib import Path


# ===================================================
# check_ledger_capacity -- warning type contracts
# ===================================================


class TestCheckLedgerCapacityWarning:
    """Tier 2 return-type gap: Optional[str] warning."""

    def test_low_capacity_warning_is_none(self, tmp_path):
        """Well-under-capacity ledger returns None
        as second tuple element."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
            check_ledger_capacity,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="tiny"),
        )
        _ratio, warning = check_ledger_capacity(
            ledger, 1_000_000
        )
        assert warning is None

    def test_near_capacity_warning_is_str(self, tmp_path):
        """Near-capacity ledger returns a non-empty
        warning string."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
            check_ledger_capacity,
        )

        ledger = tmp_path / "ledger.json"
        big = "x" * 900
        append_entry(
            ledger,
            LedgerEntry(role="user", content=big),
        )
        _ratio, warning = check_ledger_capacity(
            ledger, 1000
        )
        assert isinstance(warning, str)
        assert len(warning) > 0


# ===================================================
# compact_ledger -- non-tagged content contract
# ===================================================


class TestCompactLedgerPlainContent:
    """Tier 3 gap: plain (non-tagged) content must
    survive compaction unchanged."""

    def test_plain_content_preserved(self, tmp_path):
        """Non-tagged entry content is not modified
        by compaction."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        plain = "This has no tags at all " + "z" * 300
        append_entry(
            ledger,
            LedgerEntry(role="user", content=plain),
        )
        compact_ledger(ledger, character_threshold=200)
        entries = read_ledger(ledger)
        found = any(plain in e.content for e in entries)
        assert found, (
            "Plain non-tagged content must survive "
            "compaction unchanged"
        )


# ===================================================
# compact_ledger -- mixed-entry integration contract
# ===================================================


class TestCompactLedgerMixed:
    """Tier 3 gap: mixed entries in one ledger."""

    def test_mixed_entries_handled(self, tmp_path):
        """Compaction with tagged-long, tagged-short,
        HINT, and plain entries in one ledger."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        long_tagged = "[OBS] " + "a" * 300
        short_tagged = "[NOTE] short"
        hint_long = "[HINT] " + "h" * 400
        plain_text = "no tags here"

        for content in (
            long_tagged,
            short_tagged,
            hint_long,
            plain_text,
        ):
            append_entry(
                ledger,
                LedgerEntry(
                    role="user", content=content
                ),
            )

        compact_ledger(ledger, character_threshold=200)
        entries = read_ledger(ledger)
        contents = [e.content for e in entries]
        combined = " ".join(contents)

        # Short tagged preserved
        assert any(
            "short" in c for c in contents
        ), "Short tagged body must be preserved"

        # HINT preserved verbatim
        assert any(
            hint_long in c for c in contents
        ), "[HINT] must be preserved verbatim"

        # Plain text preserved
        assert any(
            plain_text in c for c in contents
        ), "Plain text must be preserved"

        # Long tagged body should be compacted
        assert all(
            len(c) <= 350 for c in contents
            if "[OBS]" in c
        ), "Long tagged body should be compacted"


# ===================================================
# compact_ledger -- return value semantics
# ===================================================


class TestCompactLedgerReturnValue:
    """Tier 3 gap: return int reflects compaction
    count."""

    def test_returns_nonzero_when_compacted(
        self, tmp_path
    ):
        """Return value > 0 when entries are
        compacted."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
        )

        ledger = tmp_path / "ledger.json"
        tagged = "[DATA] " + "d" * 500
        append_entry(
            ledger,
            LedgerEntry(role="user", content=tagged),
        )
        result = compact_ledger(
            ledger, character_threshold=200
        )
        assert result >= 1, (
            "Should report at least 1 compacted entry"
        )

    def test_returns_zero_nothing_to_compact(
        self, tmp_path
    ):
        """Return value is 0 when no entries need
        compaction."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(
                role="user", content="short content"
            ),
        )
        result = compact_ledger(
            ledger, character_threshold=200
        )
        assert result == 0, (
            "No compaction needed means 0 returned"
        )


# ===================================================
# append_entry -- atomicity / valid JSON contract
# ===================================================


class TestAppendEntryAtomicity:
    """Tier 3 contract: appends atomically -- file is
    valid JSON after every append."""

    def test_valid_json_after_each_append(
        self, tmp_path
    ):
        """File contains valid JSON after each
        successive append."""
        from ledger_manager import (
            LedgerEntry,
            append_entry,
        )

        ledger = tmp_path / "ledger.json"
        for i in range(5):
            append_entry(
                ledger,
                LedgerEntry(
                    role="user",
                    content=f"entry_{i}",
                ),
            )
            raw = ledger.read_text()
            data = json.loads(raw)
            assert isinstance(data, list)
            assert len(data) == i + 1


# ===================================================
# write_hint_entry -- metadata fields contract
# ===================================================


class TestWriteHintEntryMetadata:
    """Tier 2 signature gap: gate_id, stage, decision
    should appear in the written entry."""

    def test_hint_entry_contains_gate_id(
        self, tmp_path
    ):
        """gate_id is findable in the hint entry."""
        from ledger_manager import (
            read_ledger,
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="advice",
            gate_id="gate_42",
            unit_number=4,
            stage="test",
            decision="fail",
        )
        entries = read_ledger(ledger)
        combined = " ".join(e.content for e in entries)
        meta_combined = ""
        for e in entries:
            if e.metadata:
                meta_combined += str(e.metadata)
        searchable = combined + " " + meta_combined
        assert "gate_42" in searchable, (
            "gate_id should appear in entry content "
            "or metadata"
        )

    def test_hint_entry_contains_stage(
        self, tmp_path
    ):
        """stage is findable in the hint entry."""
        from ledger_manager import (
            read_ledger,
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="advice",
            gate_id="g1",
            unit_number=4,
            stage="impl",
            decision="pass",
        )
        entries = read_ledger(ledger)
        combined = " ".join(e.content for e in entries)
        meta_combined = ""
        for e in entries:
            if e.metadata:
                meta_combined += str(e.metadata)
        searchable = combined + " " + meta_combined
        assert "impl" in searchable, (
            "stage should appear in entry content "
            "or metadata"
        )

    def test_hint_entry_contains_decision(
        self, tmp_path
    ):
        """decision is findable in the hint entry."""
        from ledger_manager import (
            read_ledger,
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="advice",
            gate_id="g1",
            unit_number=4,
            stage="test",
            decision="fail",
        )
        entries = read_ledger(ledger)
        combined = " ".join(e.content for e in entries)
        meta_combined = ""
        for e in entries:
            if e.metadata:
                meta_combined += str(e.metadata)
        searchable = combined + " " + meta_combined
        assert "fail" in searchable, (
            "decision should appear in entry content "
            "or metadata"
        )
