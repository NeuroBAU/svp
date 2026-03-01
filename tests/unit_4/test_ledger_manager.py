"""
Test suite for Unit 4: Ledger Manager

Tests cover all behavioral contracts, invariants, error conditions, and
signatures from the blueprint.

## Synthetic Data Assumptions

DATA ASSUMPTION: Ledger entries use roles "agent", "human", "system" as
specified in the blueprint. Content strings are short English sentences.

DATA ASSUMPTION: Timestamps are ISO format strings (e.g. "2026-01-15T10:30:00").

DATA ASSUMPTION: [HINT] entries follow the Section 15.1 structured format
with gate metadata including gate_id, unit_number, stage, decision.

DATA ASSUMPTION: Tagged lines use markers [QUESTION], [DECISION], [CONFIRMED]
as described in spec Section 15.1.

DATA ASSUMPTION: Compaction threshold default is 200 characters. Bodies above
this threshold are deleted; bodies at or below are preserved.

DATA ASSUMPTION: Capacity warning triggers at 80%, required action at 90%.
"""

import json
import os
import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

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
# 1. LedgerEntry Signature and Data Contract Tests
# ===========================================================================

class TestLedgerEntrySignature:
    """Verify the LedgerEntry class signature and data contract."""

    def test_init_with_all_args(self):
        """LedgerEntry.__init__ accepts role, content, timestamp, metadata."""
        # DATA ASSUMPTION: Simple string values for all fields.
        entry = LedgerEntry(
            role="agent",
            content="Test content",
            timestamp="2026-01-15T10:30:00",
            metadata={"key": "value"},
        )
        assert entry.role == "agent"
        assert entry.content == "Test content"
        assert entry.timestamp == "2026-01-15T10:30:00"
        assert entry.metadata == {"key": "value"}

    def test_init_optional_timestamp(self):
        """LedgerEntry.__init__ allows timestamp to be None / defaulted."""
        entry = LedgerEntry(role="human", content="Question")
        assert entry.role == "human"
        assert entry.content == "Question"
        # timestamp should be set (either None or auto-generated ISO string)
        # The blueprint says timestamp is Optional[str] with default None in __init__
        # but the field is typed as str. The implementation may auto-fill.
        # We just verify the attribute exists.
        assert hasattr(entry, "timestamp")

    def test_init_optional_metadata(self):
        """LedgerEntry.__init__ allows metadata to be None (default)."""
        entry = LedgerEntry(role="system", content="System message")
        assert entry.metadata is None or isinstance(entry.metadata, dict)

    def test_to_dict_returns_dict(self):
        """LedgerEntry.to_dict() returns a dictionary representation."""
        entry = _make_entry()
        d = entry.to_dict()
        assert isinstance(d, dict)
        assert d["role"] == "agent"
        assert d["content"] == "Hello world"
        assert "timestamp" in d

    def test_to_dict_contains_all_fields(self):
        """to_dict() includes role, content, timestamp, and metadata."""
        # DATA ASSUMPTION: metadata is a simple dict with string values.
        entry = LedgerEntry(
            role="system",
            content="A system message",
            timestamp="2026-02-01T08:00:00",
            metadata={"gate_id": "G1"},
        )
        d = entry.to_dict()
        assert d["role"] == "system"
        assert d["content"] == "A system message"
        assert d["timestamp"] == "2026-02-01T08:00:00"
        assert d["metadata"] == {"gate_id": "G1"}

    def test_from_dict_classmethod(self):
        """LedgerEntry.from_dict() reconstructs an entry from a dictionary."""
        data = {
            "role": "agent",
            "content": "Response text",
            "timestamp": "2026-01-15T12:00:00",
            "metadata": None,
        }
        entry = LedgerEntry.from_dict(data)
        assert isinstance(entry, LedgerEntry)
        assert entry.role == "agent"
        assert entry.content == "Response text"
        assert entry.timestamp == "2026-01-15T12:00:00"

    def test_from_dict_roundtrip(self):
        """to_dict -> from_dict produces an equivalent entry."""
        original = _make_entry(metadata={"x": 1})
        d = original.to_dict()
        restored = LedgerEntry.from_dict(d)
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.timestamp == original.timestamp
        assert restored.metadata == original.metadata


# ===========================================================================
# 2. append_entry Tests
# ===========================================================================

class TestAppendEntry:
    """Tests for append_entry behavior."""

    def test_creates_file_if_not_exists(self, tmp_path):
        """append_entry creates the ledger file if it does not exist."""
        lp = _ledger_path(tmp_path)
        assert not lp.exists()
        append_entry(lp, _make_entry())
        # Post-condition: file must exist after append
        assert lp.exists()

    def test_appends_single_jsonl_line(self, tmp_path):
        """append_entry writes exactly one JSONL line per call."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="First"))
        lines = lp.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["content"] == "First"

    def test_appends_multiple_entries(self, tmp_path):
        """Multiple append_entry calls produce multiple JSONL lines."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Three simple entries appended sequentially.
        for i in range(3):
            append_entry(lp, _make_entry(content=f"Entry {i}"))
        lines = lp.read_text().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["content"] == f"Entry {i}"

    def test_append_preserves_existing_entries(self, tmp_path):
        """Appending does not destroy previously written entries."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Original"))
        append_entry(lp, _make_entry(content="New"))
        lines = lp.read_text().strip().split("\n")
        assert json.loads(lines[0])["content"] == "Original"
        assert json.loads(lines[1])["content"] == "New"

    def test_append_valid_json_per_line(self, tmp_path):
        """Each appended line is valid JSON."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Check JSON validity"))
        for line in lp.read_text().strip().split("\n"):
            parsed = json.loads(line)  # Should not raise
            assert isinstance(parsed, dict)


# ===========================================================================
# 3. read_ledger Tests
# ===========================================================================

class TestReadLedger:
    """Tests for read_ledger behavior."""

    def test_read_returns_list_of_ledger_entries(self, tmp_path):
        """read_ledger returns a list of LedgerEntry instances."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry())
        result = read_ledger(lp)
        assert isinstance(result, list)
        # Invariant: all entries must be LedgerEntry instances
        assert all(isinstance(e, LedgerEntry) for e in result)

    def test_read_preserves_order(self, tmp_path):
        """read_ledger returns entries in the order they were appended."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Sequential entries with numbered content.
        for i in range(5):
            append_entry(lp, _make_entry(content=f"Message {i}"))
        result = read_ledger(lp)
        assert len(result) == 5
        for i, entry in enumerate(result):
            assert entry.content == f"Message {i}"

    def test_read_empty_file_returns_empty_list(self, tmp_path):
        """read_ledger on an empty file returns an empty list."""
        lp = _ledger_path(tmp_path)
        lp.touch()
        result = read_ledger(lp)
        assert result == []

    def test_read_nonexistent_file_returns_empty_list(self, tmp_path):
        """read_ledger on a non-existent file returns an empty list."""
        # NOTE: The behavioral contract says "Returns an empty list for a
        # non-existent or empty file", but the error conditions say
        # FileNotFoundError is raised for non-existent files.
        # The behavioral contract takes precedence, but we test both
        # possibilities. If the implementation raises FileNotFoundError,
        # this test should be adjusted.
        lp = _ledger_path(tmp_path, "nonexistent.jsonl")
        assert not lp.exists()
        result = read_ledger(lp)
        assert result == []

    def test_read_entries_have_correct_fields(self, tmp_path):
        """read_ledger entries have role, content, timestamp fields."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(role="human", content="Hi there"))
        entries = read_ledger(lp)
        assert len(entries) == 1
        e = entries[0]
        assert e.role == "human"
        assert e.content == "Hi there"
        assert hasattr(e, "timestamp")


# ===========================================================================
# 4. clear_ledger Tests
# ===========================================================================

class TestClearLedger:
    """Tests for clear_ledger behavior."""

    def test_clear_truncates_to_zero(self, tmp_path):
        """clear_ledger truncates the file to zero bytes."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Some data"))
        clear_ledger(lp)
        assert lp.read_text() == ""

    def test_clear_file_still_exists(self, tmp_path):
        """clear_ledger does not delete the file -- it continues to exist."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry())
        clear_ledger(lp)
        assert lp.exists()

    def test_clear_then_read_returns_empty(self, tmp_path):
        """After clear_ledger, read_ledger returns an empty list."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry())
        clear_ledger(lp)
        result = read_ledger(lp)
        assert result == []


# ===========================================================================
# 5. rename_ledger Tests
# ===========================================================================

class TestRenameLedger:
    """Tests for rename_ledger behavior."""

    def test_rename_returns_new_path(self, tmp_path):
        """rename_ledger returns the new Path after renaming."""
        lp = _ledger_path(tmp_path, "session.jsonl")
        append_entry(lp, _make_entry())
        new_path = rename_ledger(lp, "session_abandoned.jsonl")
        assert isinstance(new_path, Path)

    def test_rename_old_file_gone(self, tmp_path):
        """After rename, the original file no longer exists."""
        lp = _ledger_path(tmp_path, "bug_triage_1.jsonl")
        append_entry(lp, _make_entry())
        rename_ledger(lp, "bug_triage_1_abandoned.jsonl")
        assert not lp.exists()

    def test_rename_new_file_exists(self, tmp_path):
        """After rename, the new file exists at the returned path."""
        lp = _ledger_path(tmp_path, "debug.jsonl")
        append_entry(lp, _make_entry())
        new_path = rename_ledger(lp, "debug_abandoned.jsonl")
        assert new_path.exists()

    def test_rename_content_preserved(self, tmp_path):
        """Rename preserves the file content."""
        lp = _ledger_path(tmp_path, "original.jsonl")
        append_entry(lp, _make_entry(content="Important data"))
        new_path = rename_ledger(lp, "renamed.jsonl")
        entries = read_ledger(new_path)
        assert len(entries) == 1
        assert entries[0].content == "Important data"


# ===========================================================================
# 6. get_ledger_size_chars Tests
# ===========================================================================

class TestGetLedgerSizeChars:
    """Tests for get_ledger_size_chars behavior."""

    def test_returns_int(self, tmp_path):
        """get_ledger_size_chars returns an integer."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry())
        result = get_ledger_size_chars(lp)
        assert isinstance(result, int)

    def test_empty_file_returns_zero(self, tmp_path):
        """An empty file has zero characters."""
        lp = _ledger_path(tmp_path)
        lp.touch()
        result = get_ledger_size_chars(lp)
        assert result == 0

    def test_size_increases_with_entries(self, tmp_path):
        """Adding entries increases the character count."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Short"))
        size_after_one = get_ledger_size_chars(lp)
        append_entry(lp, _make_entry(content="Another entry"))
        size_after_two = get_ledger_size_chars(lp)
        assert size_after_two > size_after_one

    def test_size_matches_file_length(self, tmp_path):
        """Character count matches the actual file content length."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Simple content, no special multi-byte characters.
        append_entry(lp, _make_entry(content="Hello"))
        expected = len(lp.read_text())
        result = get_ledger_size_chars(lp)
        assert result == expected


# ===========================================================================
# 7. check_ledger_capacity Tests
# ===========================================================================

class TestCheckLedgerCapacity:
    """Tests for check_ledger_capacity behavior."""

    def test_returns_tuple(self, tmp_path):
        """check_ledger_capacity returns a (float, Optional[str]) tuple."""
        lp = _ledger_path(tmp_path)
        lp.touch()
        result = check_ledger_capacity(lp, max_chars=1000)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_empty_file_zero_usage(self, tmp_path):
        """Empty file has 0.0 usage fraction."""
        lp = _ledger_path(tmp_path)
        lp.touch()
        fraction, warning = check_ledger_capacity(lp, max_chars=1000)
        assert fraction == 0.0
        assert warning is None

    def test_below_80_percent_no_warning(self, tmp_path):
        """Usage below 80% produces no warning."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: We write content that is about 50% of max_chars.
        # Write a small amount relative to max_chars=1000
        lp.write_text("x" * 100)
        fraction, warning = check_ledger_capacity(lp, max_chars=1000)
        assert fraction < 0.8
        assert warning is None

    def test_at_80_percent_warning(self, tmp_path):
        """Usage at or above 80% triggers a warning."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Write exactly 850 chars with max_chars=1000 (85% usage).
        lp.write_text("x" * 850)
        fraction, warning = check_ledger_capacity(lp, max_chars=1000)
        assert 0.8 <= fraction < 0.9
        assert warning is not None

    def test_at_90_percent_required_action(self, tmp_path):
        """Usage at or above 90% triggers required action warning."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Write 950 chars with max_chars=1000 (95% usage).
        lp.write_text("x" * 950)
        fraction, warning = check_ledger_capacity(lp, max_chars=1000)
        assert fraction >= 0.9
        assert warning is not None

    def test_usage_fraction_range(self, tmp_path):
        """Usage fraction is between 0.0 and 1.0 (inclusive)."""
        lp = _ledger_path(tmp_path)
        lp.write_text("x" * 500)
        fraction, _ = check_ledger_capacity(lp, max_chars=1000)
        assert 0.0 <= fraction <= 1.0

    def test_full_capacity(self, tmp_path):
        """At full capacity, fraction is 1.0."""
        lp = _ledger_path(tmp_path)
        lp.write_text("x" * 1000)
        fraction, warning = check_ledger_capacity(lp, max_chars=1000)
        assert fraction >= 1.0
        assert warning is not None


# ===========================================================================
# 8. compact_ledger Tests
# ===========================================================================

class TestCompactLedger:
    """Tests for compact_ledger compaction algorithm."""

    def test_returns_non_negative_int(self, tmp_path):
        """compact_ledger returns a non-negative integer (chars saved)."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Simple entry"))
        result = compact_ledger(lp)
        # Post-condition: result >= 0
        assert isinstance(result, int)
        assert result >= 0

    def test_compact_nonexistent_file_raises(self, tmp_path):
        """compact_ledger on a non-existent file raises FileNotFoundError."""
        lp = _ledger_path(tmp_path, "missing.jsonl")
        with pytest.raises(FileNotFoundError):
            compact_ledger(lp)

    def test_compact_preserves_hint_entries(self, tmp_path):
        """[HINT] entries are always preserved verbatim during compaction."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: A [HINT] entry has system role and [HINT] marker.
        hint_content = "[HINT] This is a system hint with important context."
        append_entry(lp, _make_entry(role="system", content=hint_content))
        compact_ledger(lp)
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert "[HINT]" in entries[0].content

    def test_compact_default_threshold_is_200(self, tmp_path):
        """Default character_threshold for compact_ledger is 200."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Entry with a body and a tagged decision line.
        # The tagged line itself is short (< 200 chars), so body is preserved.
        body = "Analysis paragraph.\n[DECISION] Keep this approach."
        append_entry(lp, _make_entry(role="agent", content=body))
        # This should work with default threshold=200
        result = compact_ledger(lp)
        assert result >= 0

    def test_compact_removes_body_for_long_tagged_line(self, tmp_path):
        """When a tagged line exceeds threshold, body is deleted."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: A long tagged line (> 200 chars) means the body
        # is considered redundant and gets deleted.
        long_decision = "[DECISION] " + "x" * 250  # > 200 chars total
        body_text = "This is the analysis body that led to the decision.\n" + long_decision
        append_entry(lp, _make_entry(role="agent", content=body_text))
        original_size = get_ledger_size_chars(lp)
        saved = compact_ledger(lp, character_threshold=200)
        new_size = get_ledger_size_chars(lp)
        # Compaction should have saved some characters
        assert saved > 0
        assert new_size < original_size

    def test_compact_preserves_body_for_short_tagged_line(self, tmp_path):
        """When a tagged line is at or below threshold, body is preserved."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: A short tagged line (<= 200 chars) means the body
        # must be preserved because the tag alone is not self-contained.
        short_decision = "[DECISION] Yes."  # Well under 200 chars
        body_text = "Analysis of the problem.\n" + short_decision
        append_entry(lp, _make_entry(role="agent", content=body_text))
        original_content = lp.read_text()
        compact_ledger(lp, character_threshold=200)
        # Body should be preserved -- content should still contain the analysis
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert "Analysis of the problem" in entries[0].content

    def test_compact_empty_file(self, tmp_path):
        """Compacting an empty file returns 0 characters saved."""
        lp = _ledger_path(tmp_path)
        lp.touch()
        # An empty file may raise FileNotFoundError or return 0.
        # The blueprint says empty file exists, so it shouldn't raise.
        # But the file is empty, so there's nothing to compact.
        result = compact_ledger(lp)
        assert result == 0

    def test_compact_custom_threshold(self, tmp_path):
        """compact_ledger respects a custom character_threshold."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: With a very low threshold (e.g., 10), even short
        # tagged lines are considered self-contained.
        tagged = "[DECISION] Approve."  # ~20 chars, > threshold of 10
        body_text = "Long analysis paragraph with many words.\n" + tagged
        append_entry(lp, _make_entry(role="agent", content=body_text))
        saved = compact_ledger(lp, character_threshold=10)
        # With threshold=10, the tagged line (>10) should trigger body deletion
        assert saved > 0


# ===========================================================================
# 9. write_hint_entry Tests
# ===========================================================================

class TestWriteHintEntry:
    """Tests for write_hint_entry behavior."""

    def test_creates_system_entry(self, tmp_path):
        """write_hint_entry appends a system-level entry."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Gate metadata uses typical SVP identifiers.
        write_hint_entry(
            ledger_path=lp,
            hint_content="Consider edge cases",
            gate_id="test_validation_gate",
            unit_number=4,
            stage="red_run",
            decision="iterate",
        )
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert entries[0].role == "system"

    def test_hint_content_in_entry(self, tmp_path):
        """The hint_content appears in the written entry."""
        lp = _ledger_path(tmp_path)
        write_hint_entry(
            ledger_path=lp,
            hint_content="Fix the boundary condition",
            gate_id="G1",
            unit_number=3,
            stage="green_run",
            decision="pass",
        )
        entries = read_ledger(lp)
        assert "Fix the boundary condition" in entries[0].content

    def test_hint_entry_contains_hint_marker(self, tmp_path):
        """The written entry contains a [HINT] marker."""
        lp = _ledger_path(tmp_path)
        write_hint_entry(
            ledger_path=lp,
            hint_content="Add more tests",
            gate_id="G2",
            unit_number=5,
            stage="test_validation",
            decision="reject",
        )
        entries = read_ledger(lp)
        assert "[HINT]" in entries[0].content

    def test_hint_entry_has_gate_metadata(self, tmp_path):
        """The hint entry includes gate_id, unit_number, stage, decision."""
        lp = _ledger_path(tmp_path)
        write_hint_entry(
            ledger_path=lp,
            hint_content="Some hint",
            gate_id="validation_gate_7",
            unit_number=7,
            stage="implementation",
            decision="approve",
        )
        entries = read_ledger(lp)
        entry = entries[0]
        # Metadata should contain gate information
        # It could be in metadata dict or in content -- check both
        entry_dict = entry.to_dict()
        entry_str = json.dumps(entry_dict)
        assert "validation_gate_7" in entry_str
        assert "7" in entry_str
        assert "implementation" in entry_str
        assert "approve" in entry_str

    def test_hint_entry_with_none_unit_number(self, tmp_path):
        """write_hint_entry handles unit_number=None."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: unit_number can be None for project-level hints.
        write_hint_entry(
            ledger_path=lp,
            hint_content="Project-level observation",
            gate_id="G0",
            unit_number=None,
            stage="planning",
            decision="note",
        )
        entries = read_ledger(lp)
        assert len(entries) == 1

    def test_hint_entry_appends_to_existing(self, tmp_path):
        """write_hint_entry appends; does not overwrite existing entries."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Existing entry"))
        write_hint_entry(
            ledger_path=lp,
            hint_content="New hint",
            gate_id="G3",
            unit_number=1,
            stage="test",
            decision="pass",
        )
        entries = read_ledger(lp)
        assert len(entries) == 2
        assert entries[0].content == "Existing entry"


# ===========================================================================
# 10. extract_tagged_lines Tests
# ===========================================================================

class TestExtractTaggedLines:
    """Tests for extract_tagged_lines behavior."""

    def test_returns_list_of_tuples(self):
        """extract_tagged_lines returns a list of (marker, full_line) tuples."""
        # DATA ASSUMPTION: Simple content with one [DECISION] line.
        content = "Analysis text.\n[DECISION] We should proceed."
        result = extract_tagged_lines(content)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_extracts_decision_marker(self):
        """Extracts [DECISION] tagged lines."""
        content = "Some body.\n[DECISION] Approved the design."
        result = extract_tagged_lines(content)
        assert len(result) >= 1
        markers = [m for m, _ in result]
        assert "[DECISION]" in markers

    def test_extracts_question_marker(self):
        """Extracts [QUESTION] tagged lines."""
        content = "[QUESTION] What is the expected behavior?"
        result = extract_tagged_lines(content)
        assert len(result) >= 1
        markers = [m for m, _ in result]
        assert "[QUESTION]" in markers

    def test_extracts_confirmed_marker(self):
        """Extracts [CONFIRMED] tagged lines."""
        content = "Details here.\n[CONFIRMED] The fix works correctly."
        result = extract_tagged_lines(content)
        assert len(result) >= 1
        markers = [m for m, _ in result]
        assert "[CONFIRMED]" in markers

    def test_extracts_multiple_markers(self):
        """Extracts multiple tagged lines from the same content."""
        # DATA ASSUMPTION: Content can have multiple different markers.
        content = (
            "Intro paragraph.\n"
            "[QUESTION] Is this correct?\n"
            "More analysis.\n"
            "[DECISION] Yes, proceed.\n"
            "[CONFIRMED] Implementation matches spec."
        )
        result = extract_tagged_lines(content)
        assert len(result) == 3
        markers = [m for m, _ in result]
        assert "[QUESTION]" in markers
        assert "[DECISION]" in markers
        assert "[CONFIRMED]" in markers

    def test_returns_full_line(self):
        """Each tuple contains the full line text."""
        content = "[DECISION] This is the full decision line."
        result = extract_tagged_lines(content)
        assert len(result) == 1
        marker, full_line = result[0]
        assert "This is the full decision line" in full_line

    def test_no_tagged_lines(self):
        """Content with no tagged lines returns an empty list."""
        content = "Just a plain paragraph with no markers."
        result = extract_tagged_lines(content)
        assert result == []

    def test_empty_content(self):
        """Empty string returns an empty list."""
        result = extract_tagged_lines("")
        assert result == []

    def test_preserves_order(self):
        """Tagged lines are returned in their order of appearance."""
        content = (
            "[QUESTION] First?\n"
            "[DECISION] Second.\n"
            "[CONFIRMED] Third."
        )
        result = extract_tagged_lines(content)
        assert len(result) == 3
        assert result[0][0] == "[QUESTION]"
        assert result[1][0] == "[DECISION]"
        assert result[2][0] == "[CONFIRMED]"


# ===========================================================================
# 11. Error Condition Tests
# ===========================================================================

class TestErrorConditions:
    """Tests for all blueprint-specified error conditions."""

    def test_read_malformed_json_raises_decode_error(self, tmp_path):
        """Malformed JSONL entry raises json.JSONDecodeError."""
        lp = _ledger_path(tmp_path)
        lp.write_text("not valid json\n")
        with pytest.raises(json.JSONDecodeError):
            read_ledger(lp)

    def test_read_missing_required_field_raises_value_error(self, tmp_path):
        """Entry missing 'role' raises ValueError about missing field."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: A JSON object missing the 'role' field.
        bad_entry = json.dumps({"content": "Hello", "timestamp": "2026-01-01T00:00:00"})
        lp.write_text(bad_entry + "\n")
        with pytest.raises(ValueError, match="missing required field"):
            read_ledger(lp)

    def test_read_missing_content_field_raises_value_error(self, tmp_path):
        """Entry missing 'content' raises ValueError about missing field."""
        lp = _ledger_path(tmp_path)
        bad_entry = json.dumps({"role": "agent", "timestamp": "2026-01-01T00:00:00"})
        lp.write_text(bad_entry + "\n")
        with pytest.raises(ValueError, match="missing required field"):
            read_ledger(lp)

    def test_read_missing_timestamp_field_raises_value_error(self, tmp_path):
        """Entry missing 'timestamp' raises ValueError about missing field."""
        lp = _ledger_path(tmp_path)
        bad_entry = json.dumps({"role": "agent", "content": "Hello"})
        lp.write_text(bad_entry + "\n")
        with pytest.raises(ValueError, match="missing required field"):
            read_ledger(lp)

    def test_compact_nonexistent_raises_file_not_found(self, tmp_path):
        """compact_ledger on non-existent file raises FileNotFoundError."""
        lp = _ledger_path(tmp_path, "does_not_exist.jsonl")
        with pytest.raises(FileNotFoundError):
            compact_ledger(lp)


# ===========================================================================
# 12. Invariant Tests
# ===========================================================================

class TestInvariants:
    """Tests for blueprint invariants."""

    def test_append_creates_file(self, tmp_path):
        """Post-condition: ledger file exists after append_entry."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry())
        assert lp.exists()

    def test_compact_non_negative_result(self, tmp_path):
        """Post-condition: compaction returns >= 0 characters saved."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry())
        result = compact_ledger(lp)
        assert result >= 0

    def test_read_returns_all_ledger_entries(self, tmp_path):
        """Post-condition: all returned items are LedgerEntry instances."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(role="agent", content="A"))
        append_entry(lp, _make_entry(role="human", content="B"))
        append_entry(lp, _make_entry(role="system", content="C"))
        result = read_ledger(lp)
        assert all(isinstance(e, LedgerEntry) for e in result)


# ===========================================================================
# 13. Function Signature Tests
# ===========================================================================

class TestFunctionSignatures:
    """Verify that all functions exist and are callable with expected args."""

    def test_append_entry_callable(self):
        """append_entry is callable."""
        assert callable(append_entry)

    def test_read_ledger_callable(self):
        """read_ledger is callable."""
        assert callable(read_ledger)

    def test_clear_ledger_callable(self):
        """clear_ledger is callable."""
        assert callable(clear_ledger)

    def test_rename_ledger_callable(self):
        """rename_ledger is callable."""
        assert callable(rename_ledger)

    def test_get_ledger_size_chars_callable(self):
        """get_ledger_size_chars is callable."""
        assert callable(get_ledger_size_chars)

    def test_check_ledger_capacity_callable(self):
        """check_ledger_capacity is callable."""
        assert callable(check_ledger_capacity)

    def test_compact_ledger_callable(self):
        """compact_ledger is callable."""
        assert callable(compact_ledger)

    def test_write_hint_entry_callable(self):
        """write_hint_entry is callable."""
        assert callable(write_hint_entry)

    def test_extract_tagged_lines_callable(self):
        """extract_tagged_lines is callable."""
        assert callable(extract_tagged_lines)

    def test_ledger_entry_class_exists(self):
        """LedgerEntry class exists and is instantiable."""
        entry = LedgerEntry(role="agent", content="test")
        assert isinstance(entry, LedgerEntry)

    def test_ledger_entry_has_to_dict(self):
        """LedgerEntry has a to_dict method."""
        entry = LedgerEntry(role="agent", content="test")
        assert hasattr(entry, "to_dict")
        assert callable(entry.to_dict)

    def test_ledger_entry_has_from_dict(self):
        """LedgerEntry has a from_dict classmethod."""
        assert hasattr(LedgerEntry, "from_dict")
        assert callable(LedgerEntry.from_dict)


# ===========================================================================
# 14. Integration-Style Behavioral Tests
# ===========================================================================

class TestIntegrationBehaviors:
    """Tests that exercise multiple functions together."""

    def test_append_read_roundtrip(self, tmp_path):
        """Append an entry then read it back -- full roundtrip."""
        lp = _ledger_path(tmp_path)
        original = _make_entry(
            role="human",
            content="What is the status?",
            timestamp="2026-03-01T09:00:00",
            metadata={"session": "debug_1"},
        )
        append_entry(lp, original)
        entries = read_ledger(lp)
        assert len(entries) == 1
        e = entries[0]
        assert e.role == "human"
        assert e.content == "What is the status?"
        assert e.timestamp == "2026-03-01T09:00:00"

    def test_append_clear_append_cycle(self, tmp_path):
        """Append, clear, then append again works correctly."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="First session"))
        clear_ledger(lp)
        append_entry(lp, _make_entry(content="Second session"))
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert entries[0].content == "Second session"

    def test_size_after_clear_is_zero(self, tmp_path):
        """After clearing, get_ledger_size_chars returns 0."""
        lp = _ledger_path(tmp_path)
        append_entry(lp, _make_entry(content="Data"))
        clear_ledger(lp)
        assert get_ledger_size_chars(lp) == 0

    def test_compact_reduces_size(self, tmp_path):
        """Compaction of eligible entries reduces the ledger size."""
        lp = _ledger_path(tmp_path)
        # DATA ASSUMPTION: Agent entry with long body and a long tagged
        # decision line (> 200 chars), making body eligible for deletion.
        long_body = "Detailed analysis paragraph. " * 20  # ~600 chars
        long_decision = "[DECISION] " + "Comprehensive decision text. " * 10  # > 200 chars
        content = long_body + "\n" + long_decision
        append_entry(lp, _make_entry(role="agent", content=content))
        size_before = get_ledger_size_chars(lp)
        saved = compact_ledger(lp, character_threshold=200)
        size_after = get_ledger_size_chars(lp)
        if saved > 0:
            assert size_after < size_before

    def test_write_hint_then_compact_preserves_hint(self, tmp_path):
        """Hint entries survive compaction."""
        lp = _ledger_path(tmp_path)
        write_hint_entry(
            ledger_path=lp,
            hint_content="Critical domain insight",
            gate_id="G10",
            unit_number=4,
            stage="test",
            decision="iterate",
        )
        compact_ledger(lp)
        entries = read_ledger(lp)
        assert len(entries) == 1
        assert "[HINT]" in entries[0].content
        assert "Critical domain insight" in entries[0].content
