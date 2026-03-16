"""
Tests for Unit 4: Ledger Manager.

Synthetic Data Assumptions:
- Ledger files are JSON files containing arrays of entry
  dicts with keys: role, content, timestamp, metadata.
- Timestamps are ISO-8601 formatted strings.
- Tagged lines follow the pattern [TAG] body_text.
- HINT entries use the [HINT] tag prefix.
- Roles are short lowercase strings (e.g. "user",
  "assistant", "system").
- Metadata is either None or a flat dict of string values.
- Character threshold for compaction defaults to 200.
- Ledger paths point to .json files in temp directories.
"""

from pathlib import Path

# ===================================================
# LedgerEntry class tests
# ===================================================


class TestLedgerEntryInit:
    """LedgerEntry.__init__ contracts."""

    def test_init_required_fields(self):
        """Construct with role and content only."""
        from src.unit_4.ledger_manager import LedgerEntry

        entry = LedgerEntry(role="user", content="hi")
        assert entry.role == "user"
        assert entry.content == "hi"

    def test_init_with_timestamp(self):
        """Explicit timestamp is stored."""
        from src.unit_4.ledger_manager import LedgerEntry

        ts = "2026-03-15T12:00:00"
        entry = LedgerEntry(role="assistant", content="ok", timestamp=ts)
        assert entry.timestamp == ts

    def test_init_default_timestamp(self):
        """Omitted timestamp gets auto-populated."""
        from src.unit_4.ledger_manager import LedgerEntry

        entry = LedgerEntry(role="user", content="x")
        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, str)
        assert len(entry.timestamp) > 0

    def test_init_metadata_none(self):
        """Metadata defaults to None."""
        from src.unit_4.ledger_manager import LedgerEntry

        entry = LedgerEntry(role="user", content="x")
        assert entry.metadata is None

    def test_init_metadata_dict(self):
        """Metadata stores provided dict."""
        from src.unit_4.ledger_manager import LedgerEntry

        meta = {"key": "value"}
        entry = LedgerEntry(role="user", content="x", metadata=meta)
        assert entry.metadata == meta


class TestLedgerEntryToDict:
    """LedgerEntry.to_dict contracts."""

    def test_to_dict_keys(self):
        """to_dict returns dict with expected keys."""
        from src.unit_4.ledger_manager import LedgerEntry

        entry = LedgerEntry(role="user", content="hello")
        d = entry.to_dict()
        assert isinstance(d, dict)
        assert "role" in d
        assert "content" in d
        assert "timestamp" in d

    def test_to_dict_values(self):
        """to_dict preserves field values."""
        from src.unit_4.ledger_manager import LedgerEntry

        ts = "2026-01-01T00:00:00"
        entry = LedgerEntry(
            role="system",
            content="msg",
            timestamp=ts,
            metadata={"a": "b"},
        )
        d = entry.to_dict()
        assert d["role"] == "system"
        assert d["content"] == "msg"
        assert d["timestamp"] == ts
        assert d["metadata"] == {"a": "b"}


class TestLedgerEntryFromDict:
    """LedgerEntry.from_dict contracts."""

    def test_from_dict_roundtrip(self):
        """from_dict(to_dict()) reproduces original."""
        from src.unit_4.ledger_manager import LedgerEntry

        original = LedgerEntry(
            role="user",
            content="test",
            timestamp="2026-01-01T00:00:00",
            metadata={"k": "v"},
        )
        rebuilt = LedgerEntry.from_dict(original.to_dict())
        assert rebuilt.role == original.role
        assert rebuilt.content == original.content
        assert rebuilt.timestamp == original.timestamp
        assert rebuilt.metadata == original.metadata

    def test_from_dict_minimal(self):
        """from_dict works with minimal dict."""
        from src.unit_4.ledger_manager import LedgerEntry

        data = {
            "role": "user",
            "content": "hi",
            "timestamp": "2026-01-01T00:00:00",
        }
        entry = LedgerEntry.from_dict(data)
        assert entry.role == "user"
        assert entry.content == "hi"


# ===================================================
# append_entry tests
# ===================================================


class TestAppendEntry:
    """append_entry contracts."""

    def test_creates_file_if_not_exists(self, tmp_path):
        """Contract: creates file if not exists."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
        )

        ledger = tmp_path / "new_ledger.json"
        assert not ledger.exists()
        entry = LedgerEntry(role="user", content="first")
        append_entry(ledger, entry)
        assert ledger.exists()

    def test_appends_to_existing(self, tmp_path):
        """Append adds entry to existing ledger."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        e1 = LedgerEntry(role="user", content="first")
        e2 = LedgerEntry(role="assistant", content="second")
        append_entry(ledger, e1)
        append_entry(ledger, e2)
        entries = read_ledger(ledger)
        assert len(entries) == 2
        assert entries[0].content == "first"
        assert entries[1].content == "second"

    def test_append_preserves_existing(self, tmp_path):
        """Existing entries remain after append."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        for i in range(3):
            append_entry(
                ledger,
                LedgerEntry(role="user", content=f"msg{i}"),
            )
        entries = read_ledger(ledger)
        assert len(entries) == 3
        for i in range(3):
            assert entries[i].content == f"msg{i}"


# ===================================================
# read_ledger tests
# ===================================================


class TestReadLedger:
    """read_ledger contracts."""

    def test_nonexistent_returns_empty(self, tmp_path):
        """Contract: empty list for missing file."""
        from src.unit_4.ledger_manager import (
            read_ledger,
        )

        result = read_ledger(tmp_path / "missing.json")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path):
        """Contract: empty list for empty file."""
        from src.unit_4.ledger_manager import (
            read_ledger,
        )

        ledger = tmp_path / "empty.json"
        ledger.write_text("")
        result = read_ledger(ledger)
        assert result == []

    def test_reads_entries(self, tmp_path):
        """Reads back written entries."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="data"),
        )
        entries = read_ledger(ledger)
        assert len(entries) == 1
        assert entries[0].role == "user"
        assert entries[0].content == "data"

    def test_returns_ledger_entry_instances(self, tmp_path):
        """Each item is a LedgerEntry."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x"),
        )
        entries = read_ledger(ledger)
        assert isinstance(entries[0], LedgerEntry)


# ===================================================
# clear_ledger tests
# ===================================================


class TestClearLedger:
    """clear_ledger contracts."""

    def test_clears_existing_ledger(self, tmp_path):
        """After clear, read returns empty."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            clear_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x"),
        )
        clear_ledger(ledger)
        assert read_ledger(ledger) == []

    def test_clear_nonexistent_no_error(self, tmp_path):
        """Clearing missing file does not raise."""
        from src.unit_4.ledger_manager import (
            clear_ledger,
        )

        clear_ledger(tmp_path / "nope.json")


# ===================================================
# rename_ledger tests
# ===================================================


class TestRenameLedger:
    """rename_ledger contracts."""

    def test_rename_returns_new_path(self, tmp_path):
        """Returns the new Path after rename."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            rename_ledger,
        )

        ledger = tmp_path / "old.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x"),
        )
        new_path = rename_ledger(ledger, "new.json")
        assert isinstance(new_path, Path)
        assert new_path.name == "new.json"
        assert new_path.exists()

    def test_rename_removes_old(self, tmp_path):
        """Old path no longer exists after rename."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            rename_ledger,
        )

        ledger = tmp_path / "old.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x"),
        )
        rename_ledger(ledger, "new.json")
        assert not ledger.exists()

    def test_rename_preserves_content(self, tmp_path):
        """Content is preserved after rename."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            read_ledger,
            rename_ledger,
        )

        ledger = tmp_path / "old.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="keep"),
        )
        new_path = rename_ledger(ledger, "new.json")
        entries = read_ledger(new_path)
        assert len(entries) == 1
        assert entries[0].content == "keep"


# ===================================================
# get_ledger_size_chars tests
# ===================================================


class TestGetLedgerSizeChars:
    """get_ledger_size_chars contracts."""

    def test_returns_int(self, tmp_path):
        """Returns an integer."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            get_ledger_size_chars,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x"),
        )
        size = get_ledger_size_chars(ledger)
        assert isinstance(size, int)
        assert size > 0

    def test_size_increases_with_content(self, tmp_path):
        """More content means larger size."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            get_ledger_size_chars,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="a"),
        )
        s1 = get_ledger_size_chars(ledger)
        append_entry(
            ledger,
            LedgerEntry(role="user", content="b" * 1000),
        )
        s2 = get_ledger_size_chars(ledger)
        assert s2 > s1


# ===================================================
# check_ledger_capacity tests
# ===================================================


class TestCheckLedgerCapacity:
    """check_ledger_capacity contracts."""

    def test_returns_tuple(self, tmp_path):
        """Returns (float, Optional[str])."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            check_ledger_capacity,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x"),
        )
        result = check_ledger_capacity(ledger, 10000)
        assert isinstance(result, tuple)
        assert len(result) == 2
        ratio, _warning = result
        assert isinstance(ratio, float)

    def test_small_ledger_low_ratio(self, tmp_path):
        """Small ledger has low capacity ratio."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            check_ledger_capacity,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="hi"),
        )
        ratio, _warning = check_ledger_capacity(ledger, 1_000_000)
        assert ratio < 0.1

    def test_near_capacity_warning(self, tmp_path):
        """Near-capacity ledger may produce warning."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            check_ledger_capacity,
        )

        ledger = tmp_path / "ledger.json"
        big_content = "x" * 900
        append_entry(
            ledger,
            LedgerEntry(role="user", content=big_content),
        )
        ratio, _warning = check_ledger_capacity(ledger, 1000)
        assert ratio > 0.5


# ===================================================
# compact_ledger tests
# ===================================================


class TestCompactLedger:
    """compact_ledger contracts -- compaction algo."""

    def test_returns_int(self, tmp_path):
        """Returns count of compacted entries."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
        )

        ledger = tmp_path / "ledger.json"
        append_entry(
            ledger,
            LedgerEntry(role="user", content="x" * 300),
        )
        result = compact_ledger(ledger)
        assert isinstance(result, int)

    def test_long_tagged_body_deleted(self, tmp_path):
        """Contract: tagged lines above threshold
        have body deleted."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        long_body = "x" * 300
        tagged = f"[OBSERVATION] {long_body}"
        append_entry(
            ledger,
            LedgerEntry(role="user", content=tagged),
        )
        compact_ledger(ledger, character_threshold=200)
        entries = read_ledger(ledger)
        assert len(entries) >= 1
        for e in entries:
            if "[OBSERVATION]" in e.content:
                assert len(e.content) <= 250

    def test_short_tagged_preserved(self, tmp_path):
        """Contract: tagged lines at or below threshold
        are preserved."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        short_content = "[NOTE] short message"
        append_entry(
            ledger,
            LedgerEntry(role="user", content=short_content),
        )
        compact_ledger(ledger, character_threshold=200)
        entries = read_ledger(ledger)
        found = any("short message" in e.content for e in entries)
        assert found, "Short tagged line body should be preserved"

    def test_hint_always_preserved(self, tmp_path):
        """Contract: [HINT] entries always preserved
        verbatim."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        long_hint = "[HINT] " + "h" * 500
        append_entry(
            ledger,
            LedgerEntry(role="system", content=long_hint),
        )
        compact_ledger(ledger, character_threshold=200)
        entries = read_ledger(ledger)
        found = any(long_hint in e.content for e in entries)
        assert found, "[HINT] entries must be preserved verbatim"

    def test_default_threshold_200(self, tmp_path):
        """Default character_threshold is 200."""
        from src.unit_4.ledger_manager import (
            LedgerEntry,
            append_entry,
            compact_ledger,
            read_ledger,
        )

        ledger = tmp_path / "ledger.json"
        at_threshold = "[TAG] " + "a" * 194
        assert len(at_threshold) == 200
        append_entry(
            ledger,
            LedgerEntry(role="user", content=at_threshold),
        )
        compact_ledger(ledger)
        entries = read_ledger(ledger)
        found = any("a" * 194 in e.content for e in entries)
        assert found, "Content at threshold should be preserved"


# ===================================================
# write_hint_entry tests
# ===================================================


class TestWriteHintEntry:
    """write_hint_entry contracts."""

    def test_writes_hint_to_ledger(self, tmp_path):
        """Creates a hint entry in the ledger."""
        from src.unit_4.ledger_manager import (
            read_ledger,
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="fix the bug",
            gate_id="gate_1",
            unit_number=4,
            stage="test",
            decision="fail",
        )
        entries = read_ledger(ledger)
        assert len(entries) >= 1

    def test_hint_contains_content(self, tmp_path):
        """Hint content is findable in entry."""
        from src.unit_4.ledger_manager import (
            read_ledger,
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="specific hint text",
            gate_id="g2",
            unit_number=None,
            stage="impl",
            decision="pass",
        )
        entries = read_ledger(ledger)
        combined = " ".join(e.content for e in entries)
        assert "specific hint text" in combined

    def test_hint_has_hint_tag(self, tmp_path):
        """Written hint entry uses [HINT] tag."""
        from src.unit_4.ledger_manager import (
            read_ledger,
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="advice",
            gate_id="g3",
            unit_number=7,
            stage="test",
            decision="fail",
        )
        entries = read_ledger(ledger)
        found = any("[HINT]" in e.content for e in entries)
        assert found, "Hint entries should contain [HINT] tag"

    def test_hint_unit_number_none(self, tmp_path):
        """unit_number=None is valid."""
        from src.unit_4.ledger_manager import (
            write_hint_entry,
        )

        ledger = tmp_path / "ledger.json"
        write_hint_entry(
            ledger_path=ledger,
            hint_content="global hint",
            gate_id="g4",
            unit_number=None,
            stage="review",
            decision="pass",
        )


# ===================================================
# extract_tagged_lines tests
# ===================================================


class TestExtractTaggedLines:
    """extract_tagged_lines contracts."""

    def test_returns_list_of_tuples(self):
        """Returns List[Tuple[str, str]]."""
        from src.unit_4.ledger_manager import (
            extract_tagged_lines,
        )

        result = extract_tagged_lines("[TAG] some body")
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], tuple)
            assert len(result[0]) == 2

    def test_extracts_tag_and_body(self):
        """Parses tag and body from tagged line."""
        from src.unit_4.ledger_manager import (
            extract_tagged_lines,
        )

        result = extract_tagged_lines("[OBSERVATION] the body text")
        assert len(result) >= 1
        tag, body = result[0]
        assert "OBSERVATION" in tag
        assert "the body text" in body

    def test_multiple_tagged_lines(self):
        """Parses multiple tagged lines."""
        from src.unit_4.ledger_manager import (
            extract_tagged_lines,
        )

        content = "[TAG1] first line\n[TAG2] second line"
        result = extract_tagged_lines(content)
        assert len(result) == 2

    def test_no_tagged_lines(self):
        """No tags returns empty list."""
        from src.unit_4.ledger_manager import (
            extract_tagged_lines,
        )

        result = extract_tagged_lines("just plain text no tags")
        assert result == []

    def test_hint_tag_extracted(self):
        """[HINT] lines are extractable."""
        from src.unit_4.ledger_manager import (
            extract_tagged_lines,
        )

        result = extract_tagged_lines("[HINT] do this thing")
        assert len(result) >= 1
        tag, _body = result[0]
        assert "HINT" in tag

    def test_empty_string(self):
        """Empty input returns empty list."""
        from src.unit_4.ledger_manager import (
            extract_tagged_lines,
        )

        result = extract_tagged_lines("")
        assert result == []
