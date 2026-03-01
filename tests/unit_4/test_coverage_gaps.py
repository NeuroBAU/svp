"""
Coverage gap tests for Unit 4: Ledger Manager

These tests cover behaviors implied by the blueprint that are not exercised
by the existing test suite in test_ledger_manager.py.

## Synthetic Data Assumptions

DATA ASSUMPTION: Ledger entries use roles "agent", "human", "system" as
specified in the blueprint.

DATA ASSUMPTION: Compaction works with both [DECISION] and [CONFIRMED]
closings, as described in the blueprint behavioral contract.

DATA ASSUMPTION: The .jsonl extension pre-condition applies to all functions
that accept a ledger_path parameter.

DATA ASSUMPTION: The check_ledger_capacity warning messages are distinct
for the 80% and 90% thresholds.

DATA ASSUMPTION: compact_ledger returns the exact number of characters
saved, matching the difference in file size before and after compaction.

DATA ASSUMPTION: The FileNotFoundError message from compact_ledger
includes the path, matching "Ledger file not found: {path}".
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, Optional

from svp.scripts.ledger_manager import (
    LedgerEntry,
    append_entry,
    read_ledger,
    clear_ledger,
    rename_ledger,
    get_ledger_size_chars,
    check_ledger_capacity,
    compact_ledger,
    write_hint_entry,
    extract_tagged_lines,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    role: str = "agent",
    content: str = "Hello world",
    timestamp: str = "2026-01-15T10:30:00",
    metadata: Optional[Dict[str, Any]] = None,
) -> LedgerEntry:
    """Helper to create a LedgerEntry with sane defaults."""
    return LedgerEntry(role=role, content=content, timestamp=timestamp, metadata=metadata)


def _ledger_path(tmp_path: Path, name: str = "test_ledger.jsonl") -> Path:
    """Return a .jsonl path inside tmp_path."""
    return tmp_path / name


# ===========================================================================
# Gap 1: Compaction with [CONFIRMED] closing (not just [DECISION])
# ===========================================================================

class TestCompactWithConfirmedClosing:
    """Blueprint says compaction identifies [DECISION] or [CONFIRMED] closings.
    Existing tests only exercise [DECISION]. These tests cover [CONFIRMED]."""

    def test_compact_removes_body_for_long_confirmed_line(self, tmp_path):
        """When a [CONFIRMED] tagged line exceeds threshold, body is deleted."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: A long [CONFIRMED] line (> 200 chars) triggers
        # body deletion, same as [DECISION].
        long_confirmed = "[CONFIRMED] " + "y" * 250  # > 200 chars total
        body_text = "Verification analysis body text.\n" + long_confirmed
        append_entry(lp, _make_entry(role="agent", content=body_text))
        original_size = get_ledger_size_chars(lp)
        saved = compact_ledger(lp, character_threshold=200)
        new_size = get_ledger_size_chars(lp)
        # Compaction should have saved characters by removing the body
        assert saved > 0
        assert new_size < original_size

    def test_compact_preserves_body_for_short_confirmed_line(self, tmp_path):
        """When a [CONFIRMED] tagged line is at or below threshold, body is preserved."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: A short [CONFIRMED] line (<= 200 chars) means
        # the body must be preserved.
        short_confirmed = "[CONFIRMED] Yes, verified."  # Well under 200 chars
        body_text = "Detailed verification steps taken.\n" + short_confirmed
        append_entry(lp, _make_entry(role="agent", content=body_text))
        compact_ledger(lp, character_threshold=200)
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert "Detailed verification steps taken" in entries[0].content


# ===========================================================================
# Gap 2: Compaction preserves non-tagged entries as-is
# ===========================================================================

class TestCompactPreservesNonTaggedEntries:
    """Blueprint says compaction targets entries with [DECISION]/[CONFIRMED]
    closings. Entries without those tags should be preserved as-is."""

    def test_compact_preserves_human_entries(self, tmp_path):
        """Human entries without tags are preserved during compaction."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Human entries do not have decision/confirmed tags.
        append_entry(lp, _make_entry(role="human", content="What should we do?"))
        compact_ledger(lp)
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert entries[0].content == "What should we do?"
        assert entries[0].role == "human"

    def test_compact_preserves_agent_entries_without_tags(self, tmp_path):
        """Agent entries without [DECISION]/[CONFIRMED] are preserved."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Agent entry with analysis text but no decision tags.
        append_entry(lp, _make_entry(
            role="agent",
            content="Here is my analysis of the situation. No decision yet.",
        ))
        compact_ledger(lp)
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert "No decision yet" in entries[0].content

    def test_compact_mixed_entries_only_compacts_eligible(self, tmp_path):
        """In a mix of entries, only those with long tagged lines get compacted."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Three entries -- one human (preserved), one agent
        # with long [DECISION] (compacted), one system [HINT] (preserved).
        append_entry(lp, _make_entry(role="human", content="Please investigate."))
        long_decision = "[DECISION] " + "z" * 250
        agent_content = "Long analysis body for compaction.\n" + long_decision
        append_entry(lp, _make_entry(role="agent", content=agent_content))
        hint_content = "[HINT] Important system hint."
        append_entry(lp, _make_entry(role="system", content=hint_content))
        compact_ledger(lp, character_threshold=200)
        entries = read_ledger(lp)
        assert len(entries) == 3
        # Human entry preserved
        assert entries[0].content == "Please investigate."
        # Agent entry compacted -- body removed, only tagged line remains
        assert "Long analysis body" not in entries[1].content
        assert "[DECISION]" in entries[1].content
        # Hint entry preserved
        assert "[HINT]" in entries[2].content


# ===========================================================================
# Gap 3: compact_ledger return value equals actual chars saved
# ===========================================================================

class TestCompactReturnValueAccuracy:
    """Blueprint says compact_ledger returns the number of characters saved.
    Existing tests check saved > 0 but do not verify the arithmetic."""

    def test_compact_return_matches_size_difference(self, tmp_path):
        """The returned value equals the difference in file size."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Agent entry with body and a long [DECISION] line.
        long_decision = "[DECISION] " + "a" * 250
        body = "Body paragraph that will be removed.\n" + long_decision
        append_entry(lp, _make_entry(role="agent", content=body))
        size_before = get_ledger_size_chars(lp)
        saved = compact_ledger(lp, character_threshold=200)
        size_after = get_ledger_size_chars(lp)
        assert saved == size_before - size_after


# ===========================================================================
# Gap 4: Pre-condition -- .jsonl extension enforcement
# ===========================================================================

class TestJsonlExtensionPrecondition:
    """Blueprint invariant: ledger_path.suffix == '.jsonl'. All functions that
    accept a ledger_path should enforce this pre-condition."""

    def test_append_entry_rejects_non_jsonl(self, tmp_path):
        """append_entry rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.txt"
        with pytest.raises(AssertionError, match="jsonl"):
            append_entry(bad_path, _make_entry())

    def test_read_ledger_rejects_non_jsonl(self, tmp_path):
        """read_ledger rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.json"
        with pytest.raises(AssertionError, match="jsonl"):
            read_ledger(bad_path)

    def test_clear_ledger_rejects_non_jsonl(self, tmp_path):
        """clear_ledger rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.log"
        bad_path.touch()
        with pytest.raises(AssertionError, match="jsonl"):
            clear_ledger(bad_path)

    def test_rename_ledger_rejects_non_jsonl(self, tmp_path):
        """rename_ledger rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.csv"
        bad_path.touch()
        with pytest.raises(AssertionError, match="jsonl"):
            rename_ledger(bad_path, "new_name.jsonl")

    def test_get_ledger_size_chars_rejects_non_jsonl(self, tmp_path):
        """get_ledger_size_chars rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.txt"
        bad_path.touch()
        with pytest.raises(AssertionError, match="jsonl"):
            get_ledger_size_chars(bad_path)

    def test_check_ledger_capacity_rejects_non_jsonl(self, tmp_path):
        """check_ledger_capacity rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.dat"
        bad_path.touch()
        with pytest.raises(AssertionError, match="jsonl"):
            check_ledger_capacity(bad_path, max_chars=1000)

    def test_compact_ledger_rejects_non_jsonl(self, tmp_path):
        """compact_ledger rejects a path without .jsonl extension."""
        bad_path = tmp_path / "ledger.txt"
        bad_path.touch()
        with pytest.raises(AssertionError, match="jsonl"):
            compact_ledger(bad_path)

    def test_write_hint_entry_rejects_non_jsonl(self, tmp_path):
        """write_hint_entry rejects a path without .jsonl extension."""
        bad_path = tmp_path / "hints.txt"
        with pytest.raises(AssertionError, match="jsonl"):
            write_hint_entry(
                ledger_path=bad_path,
                hint_content="test",
                gate_id="G1",
                unit_number=1,
                stage="test",
                decision="pass",
            )


# ===========================================================================
# Gap 5: compact_ledger FileNotFoundError message format
# ===========================================================================

class TestCompactFileNotFoundMessage:
    """Blueprint specifies error message: 'Ledger file not found: {path}'.
    Existing test checks exception type but not the message."""

    def test_compact_nonexistent_error_message_contains_path(self, tmp_path):
        """FileNotFoundError message includes the file path."""
        lp = _ledger_path(tmp_path, "nonexistent_ledger.jsonl")
        with pytest.raises(FileNotFoundError, match="nonexistent_ledger"):
            compact_ledger(lp)


# ===========================================================================
# Gap 6: check_ledger_capacity distinct warnings at 80% vs 90%
# ===========================================================================

class TestCapacityWarningDistinction:
    """Blueprint says 'Warning at 80%, required action at 90%'. The existing
    tests check that warning is not None but do not verify the messages
    are distinct."""

    def test_80_and_90_warnings_are_different(self, tmp_path):
        """The warning message at 80% is different from the one at 90%."""
        lp_80 = _ledger_path(tmp_path, "ledger_80.jsonl")
        lp_90 = _ledger_path(tmp_path, "ledger_90.jsonl")
        # DATA ASSUMPTION: 850 chars for 85% usage, 950 chars for 95% usage.
        lp_80.write_text("x" * 850)
        lp_90.write_text("x" * 950)
        _, warning_80 = check_ledger_capacity(lp_80, max_chars=1000)
        _, warning_90 = check_ledger_capacity(lp_90, max_chars=1000)
        assert warning_80 is not None
        assert warning_90 is not None
        # The warnings should be different strings
        assert warning_80 != warning_90

    def test_usage_fraction_is_correct_arithmetic(self, tmp_path):
        """The usage fraction equals current_size / max_chars."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Write exactly 500 chars, max_chars=1000.
        lp.write_text("x" * 500)
        fraction, _ = check_ledger_capacity(lp, max_chars=1000)
        assert fraction == 0.5


# ===========================================================================
# Gap 7: from_dict with metadata present
# ===========================================================================

class TestFromDictWithMetadata:
    """Existing from_dict tests pass metadata=None. This tests that metadata
    is correctly restored when present in the dict."""

    def test_from_dict_restores_metadata(self):
        """from_dict correctly restores metadata when present."""
        data = {
            "role": "system",
            "content": "[HINT] Some hint",
            "timestamp": "2026-02-01T12:00:00",
            "metadata": {"gate_id": "G5", "unit_number": 3, "stage": "test"},
        }
        entry = LedgerEntry.from_dict(data)
        assert entry.metadata is not None
        assert entry.metadata["gate_id"] == "G5"
        assert entry.metadata["unit_number"] == 3
        assert entry.metadata["stage"] == "test"

    def test_from_dict_without_metadata_key(self):
        """from_dict handles a dict that has no 'metadata' key at all."""
        data = {
            "role": "agent",
            "content": "No metadata key",
            "timestamp": "2026-01-01T00:00:00",
        }
        entry = LedgerEntry.from_dict(data)
        assert isinstance(entry, LedgerEntry)
        assert entry.role == "agent"
        # metadata should be None when absent from the dict
        assert entry.metadata is None


# ===========================================================================
# Gap 8: LedgerEntry timestamp auto-generation
# ===========================================================================

class TestTimestampAutoGeneration:
    """Blueprint shows timestamp: Optional[str] = None in __init__ but the
    field type is str (ISO format). When timestamp is omitted, the entry
    should still have a valid string timestamp."""

    def test_auto_generated_timestamp_is_string(self):
        """When timestamp is not provided, it is auto-generated as a string."""
        entry = LedgerEntry(role="agent", content="Test")
        assert isinstance(entry.timestamp, str)
        assert len(entry.timestamp) > 0
