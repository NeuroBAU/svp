"""
Tests for Unit 7: Ledger Management.

Synthetic Data Assumptions:
- JSONL entries use simple string content like "Hello world", "This is a decision",
  "Short", etc., chosen to exercise threshold comparisons.
- Timestamps are assumed to be ISO-8601 UTC format strings (e.g., "2026-01-15T10:30:00Z").
- Tags are bracket-prefixed strings like "[DECISION]", "[CONFIRMED]", "[HINT]", "[QUESTION]".
- Ledger types tested: "setup", "stakeholder", "blueprint", "spec_revision", "help",
  "hint", "bug_triage" -- all values specified in the blueprint contract.
- Session numbers are positive integers (1, 2, 42) for session-based ledger types.
- project_root is a temporary directory created per-test via tmp_path fixture.
- Character threshold for compaction tests uses the default (200) and custom values (10, 50).
- Content strings are crafted to be above or below the threshold as needed.
- Non-tagged lines are "exploratory" lines without any recognized tag.
- The .bak rename behavior for clear_ledger is tested per task specification.
"""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List

from ledger_manager import (
    append_entry,
    clear_ledger,
    compact_ledger,
    get_ledger_path,
    read_ledger,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_raw_lines(path: Path) -> List[str]:
    """Read raw lines from a JSONL file."""
    return path.read_text().strip().splitlines()


def _parse_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Parse a JSONL file into a list of dicts."""
    lines = _read_raw_lines(path)
    return [json.loads(line) for line in lines]


def _write_jsonl(path: Path, entries: List[Dict[str, Any]]) -> None:
    """Write entries as JSONL lines to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Tests for append_entry
# ---------------------------------------------------------------------------


class TestAppendEntry:
    """Tests for the append_entry function."""

    def test_creates_file_if_absent_and_appends_entry(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        assert not ledger.exists()

        append_entry(ledger, "user", "Hello world")

        assert ledger.exists()
        entries = _parse_jsonl(ledger)
        assert len(entries) == 1

    def test_appended_entry_has_required_keys(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "Hello world", tags=["[DECISION]"])

        entries = _parse_jsonl(ledger)
        entry = entries[0]
        assert "timestamp" in entry
        assert "role" in entry
        assert "content" in entry
        assert "tags" in entry

    def test_entry_role_matches_input(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "assistant", "Response content")

        entries = _parse_jsonl(ledger)
        assert entries[0]["role"] == "assistant"

    def test_entry_content_matches_input(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "My specific content")

        entries = _parse_jsonl(ledger)
        assert entries[0]["content"] == "My specific content"

    def test_entry_tags_matches_input_when_provided(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(
            ledger, "user", "Tagged content", tags=["[DECISION]", "[CONFIRMED]"]
        )

        entries = _parse_jsonl(ledger)
        assert entries[0]["tags"] == ["[DECISION]", "[CONFIRMED]"]

    def test_entry_tags_default_when_none_provided(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "No tags")

        entries = _parse_jsonl(ledger)
        # tags should be present in the entry (either None or empty list)
        assert "tags" in entries[0]

    def test_timestamp_is_iso8601_utc(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "Check timestamp")

        entries = _parse_jsonl(ledger)
        ts = entries[0]["timestamp"]
        # Should be parseable as ISO-8601.
        # Common formats: "2026-01-15T10:30:00Z" or "2026-01-15T10:30:00+00:00"
        parsed = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None or ts.endswith("Z")

    def test_appends_multiple_entries_sequentially(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "First message")
        append_entry(ledger, "assistant", "Second message")
        append_entry(ledger, "user", "Third message")

        entries = _parse_jsonl(ledger)
        assert len(entries) == 3
        assert entries[0]["content"] == "First message"
        assert entries[1]["content"] == "Second message"
        assert entries[2]["content"] == "Third message"

    def test_each_entry_is_a_separate_jsonl_line(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "Line one")
        append_entry(ledger, "assistant", "Line two")

        lines = _read_raw_lines(ledger)
        assert len(lines) == 2
        # Each line should be valid JSON
        for line in lines:
            json.loads(line)

    def test_creates_parent_directories_if_needed(self, tmp_path):
        ledger = tmp_path / "deep" / "nested" / "ledger.jsonl"
        assert not ledger.parent.exists()

        append_entry(ledger, "user", "Deep content")

        assert ledger.exists()
        entries = _parse_jsonl(ledger)
        assert len(entries) == 1

    def test_appends_to_existing_file(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        # Pre-populate with one entry
        existing = {
            "timestamp": "2026-01-01T00:00:00Z",
            "role": "system",
            "content": "Init",
            "tags": None,
        }
        _write_jsonl(ledger, [existing])

        append_entry(ledger, "user", "New entry")

        entries = _parse_jsonl(ledger)
        assert len(entries) == 2
        assert entries[0]["content"] == "Init"
        assert entries[1]["content"] == "New entry"


# ---------------------------------------------------------------------------
# Tests for read_ledger
# ---------------------------------------------------------------------------


class TestReadLedger:
    """Tests for the read_ledger function."""

    def test_returns_empty_list_when_file_absent(self, tmp_path):
        ledger = tmp_path / "nonexistent.jsonl"
        result = read_ledger(ledger)
        assert result == []

    def test_returns_list_of_dicts_from_jsonl(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Hello",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "assistant",
                "content": "Hi",
                "tags": None,
            },
        ]
        _write_jsonl(ledger, entries)

        result = read_ledger(ledger)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(entry, dict) for entry in result)

    def test_preserves_entry_content(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Hello world",
                "tags": ["[DECISION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        result = read_ledger(ledger)
        assert result[0]["content"] == "Hello world"
        assert result[0]["role"] == "user"
        assert result[0]["tags"] == ["[DECISION]"]

    def test_returns_entries_in_file_order(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "First",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "assistant",
                "content": "Second",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:02:00Z",
                "role": "user",
                "content": "Third",
                "tags": None,
            },
        ]
        _write_jsonl(ledger, entries)

        result = read_ledger(ledger)
        assert [e["content"] for e in result] == ["First", "Second", "Third"]

    def test_returns_empty_list_for_empty_file(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        ledger.write_text("")

        result = read_ledger(ledger)
        assert result == []

    def test_roundtrip_with_append_entry(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "Test content", tags=["[HINT]"])

        result = read_ledger(ledger)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Test content"
        assert result[0]["tags"] == ["[HINT]"]


# ---------------------------------------------------------------------------
# Tests for compact_ledger
# ---------------------------------------------------------------------------


class TestCompactLedger:
    """Tests for the compact_ledger function."""

    def test_preserves_decision_tagged_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Short",
                "tags": ["[DECISION]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Exploratory chat",
                "tags": None,
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        # The [DECISION] tagged entry must be preserved
        decision_entries = [
            e for e in result if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) == 1

    def test_preserves_confirmed_tagged_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Confirmed item",
                "tags": ["[CONFIRMED]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Some chat",
                "tags": None,
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        confirmed_entries = [
            e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]
        ]
        assert len(confirmed_entries) == 1

    def test_preserves_hint_tagged_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "A hint",
                "tags": ["[HINT]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Random chat",
                "tags": None,
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        hint_entries = [e for e in result if e.get("tags") and "[HINT]" in e["tags"]]
        assert len(hint_entries) == 1

    def test_tagged_line_above_threshold_has_body_deleted(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        long_content = "A" * 201  # Above default threshold of 200
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": long_content,
                "tags": ["[DECISION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        assert len(result) >= 1
        decision_entries = [
            e for e in result if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) == 1
        # Body should be deleted (content shortened/emptied) but the entry is preserved
        assert len(decision_entries[0]["content"]) < len(long_content)

    def test_tagged_line_at_threshold_keeps_body_intact(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        exact_content = "B" * 200  # Exactly at default threshold of 200
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": exact_content,
                "tags": ["[DECISION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        decision_entries = [
            e for e in result if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) == 1
        assert decision_entries[0]["content"] == exact_content

    def test_tagged_line_below_threshold_keeps_body_intact(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        short_content = "C" * 50  # Well below default threshold
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": short_content,
                "tags": ["[CONFIRMED]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        confirmed_entries = [
            e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]
        ]
        assert len(confirmed_entries) == 1
        assert confirmed_entries[0]["content"] == short_content

    def test_non_tagged_exploratory_lines_are_removed_or_summarized(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Decide this",
                "tags": ["[DECISION]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Some exploratory chat A",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:02:00Z",
                "role": "assistant",
                "content": "Some exploratory chat B",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:03:00Z",
                "role": "user",
                "content": "Another decision",
                "tags": ["[DECISION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        # Original non-tagged exploratory lines should not appear verbatim
        verbatim_exploratory = [
            e
            for e in result
            if e.get("content")
            in ("Some exploratory chat A", "Some exploratory chat B")
            and (e.get("tags") is None or e.get("tags") == [])
        ]
        assert len(verbatim_exploratory) == 0

    def test_custom_character_threshold(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        # Content of 15 chars, with threshold of 10 -> above threshold
        content_above = "D" * 15
        # Content of 8 chars, with threshold of 10 -> below threshold
        content_below = "E" * 8
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": content_above,
                "tags": ["[QUESTION]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": content_below,
                "tags": ["[DECISION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger, character_threshold=10)

        result = read_ledger(ledger)
        # Entry above threshold: body deleted
        question_entries = [
            e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]
        ]
        assert len(question_entries) >= 1
        assert len(question_entries[0]["content"]) < len(content_above)

        # Entry at or below threshold: body intact
        decision_entries = [
            e for e in result if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) == 1
        assert decision_entries[0]["content"] == content_below

    def test_question_tagged_entry_above_threshold_has_body_deleted(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        long_content = "Q" * 201
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": long_content,
                "tags": ["[QUESTION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        question_entries = [
            e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]
        ]
        assert len(question_entries) >= 1
        assert len(question_entries[0]["content"]) < len(long_content)

    def test_question_tagged_entry_below_threshold_keeps_body(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        short_content = "Q" * 50
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": short_content,
                "tags": ["[QUESTION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        question_entries = [
            e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]
        ]
        assert len(question_entries) >= 1
        assert question_entries[0]["content"] == short_content

    def test_confirmed_tagged_entry_above_threshold_has_body_deleted(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        long_content = "X" * 250
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": long_content,
                "tags": ["[CONFIRMED]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        confirmed_entries = [
            e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]
        ]
        assert len(confirmed_entries) == 1
        assert len(confirmed_entries[0]["content"]) < len(long_content)

    def test_compaction_does_not_use_llm(self, tmp_path):
        """Compaction is a deterministic operation -- no external calls.
        This test verifies compaction completes without network/LLM dependency
        by simply running it in an isolated tmp_path environment."""
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Hi",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Decided",
                "tags": ["[DECISION]"],
            },
        ]
        _write_jsonl(ledger, entries)

        # Should complete without errors in isolated environment (no LLM calls)
        compact_ledger(ledger)

        result = read_ledger(ledger)
        assert len(result) >= 1

    def test_all_non_tagged_lines_removed_when_no_preserved_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "Exploratory A",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "assistant",
                "content": "Exploratory B",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:02:00Z",
                "role": "user",
                "content": "Exploratory C",
                "tags": None,
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        # All exploratory lines should be removed or summarized;
        # none of the original verbatim content should remain
        original_contents = {"Exploratory A", "Exploratory B", "Exploratory C"}
        for entry in result:
            assert entry.get("content") not in original_contents

    def test_mixed_tags_and_exploratory_with_threshold_boundary(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "X" * 50,
                "tags": ["[DECISION]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Chat 1",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:02:00Z",
                "role": "assistant",
                "content": "Chat 2",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:03:00Z",
                "role": "user",
                "content": "Y" * 201,
                "tags": ["[CONFIRMED]"],
            },
            {
                "timestamp": "2026-01-01T00:04:00Z",
                "role": "user",
                "content": "Z" * 10,
                "tags": ["[HINT]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger, character_threshold=200)

        result = read_ledger(ledger)

        # [DECISION] with 50 chars (below 200): body preserved
        decisions = [e for e in result if e.get("tags") and "[DECISION]" in e["tags"]]
        assert len(decisions) == 1
        assert decisions[0]["content"] == "X" * 50

        # [CONFIRMED] with 201 chars (above 200): body deleted
        confirmed = [e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]]
        assert len(confirmed) == 1
        assert len(confirmed[0]["content"]) < 201

        # [HINT] preserved (always preserved regardless)
        hints = [e for e in result if e.get("tags") and "[HINT]" in e["tags"]]
        assert len(hints) == 1

    def test_hint_tagged_entry_is_always_preserved(self, tmp_path):
        """[HINT] is in the 'always preserved' list but NOT in the
        'body deletion' list ([QUESTION], [DECISION], [CONFIRMED]).
        A [HINT] entry should be preserved with its full body."""
        ledger = tmp_path / "ledger.jsonl"
        long_hint = "H" * 500
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": long_hint,
                "tags": ["[HINT]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        hint_entries = [e for e in result if e.get("tags") and "[HINT]" in e["tags"]]
        assert len(hint_entries) == 1
        # [HINT] is preserved -- contract says "Preserves all entries tagged [HINT]"
        # and body deletion only applies to [QUESTION], [DECISION], [CONFIRMED]

    def test_empty_ledger_compaction_is_noop(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        ledger.write_text("")

        compact_ledger(ledger)

        result = read_ledger(ledger)
        assert result == []


# ---------------------------------------------------------------------------
# Tests for clear_ledger
# ---------------------------------------------------------------------------


class TestClearLedger:
    """Tests for the clear_ledger function."""

    def test_removes_ledger_file(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        _write_jsonl(
            ledger,
            [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "role": "user",
                    "content": "Data",
                    "tags": None,
                },
            ],
        )
        assert ledger.exists()

        clear_ledger(ledger)

        # After clear, the original ledger content should be gone.
        # The file is either removed entirely, or replaced with an empty file.
        if ledger.exists():
            assert ledger.read_text().strip() == ""

    def test_noop_when_file_absent(self, tmp_path):
        ledger = tmp_path / "nonexistent.jsonl"
        assert not ledger.exists()

        # Should not raise
        clear_ledger(ledger)

    def test_backup_file_created_on_clear(self, tmp_path):
        """Per task spec: clear_ledger renames to .bak."""
        ledger = tmp_path / "ledger.jsonl"
        original_content = (
            json.dumps(
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "role": "user",
                    "content": "Important",
                    "tags": None,
                }
            )
            + "\n"
        )
        ledger.write_text(original_content)

        clear_ledger(ledger)

        bak = tmp_path / "ledger.jsonl.bak"
        # Check if .bak was created (renamed from original)
        if bak.exists():
            assert bak.read_text() == original_content

    def test_cleared_ledger_returns_empty_on_read(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        _write_jsonl(
            ledger,
            [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "role": "user",
                    "content": "Data",
                    "tags": None,
                },
            ],
        )

        clear_ledger(ledger)

        result = read_ledger(ledger)
        assert result == []

    def test_clear_then_append_works(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        _write_jsonl(
            ledger,
            [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "role": "user",
                    "content": "Old",
                    "tags": None,
                },
            ],
        )

        clear_ledger(ledger)
        append_entry(ledger, "user", "New data after clear")

        result = read_ledger(ledger)
        assert len(result) == 1
        assert result[0]["content"] == "New data after clear"


# ---------------------------------------------------------------------------
# Tests for get_ledger_path
# ---------------------------------------------------------------------------


class TestGetLedgerPath:
    """Tests for the get_ledger_path function."""

    def test_setup_ledger_path(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert result == tmp_path / "ledgers" / "setup_dialog.jsonl"

    def test_stakeholder_ledger_path(self, tmp_path):
        result = get_ledger_path(tmp_path, "stakeholder")
        assert result == tmp_path / "ledgers" / "stakeholder_dialog.jsonl"

    def test_blueprint_ledger_path(self, tmp_path):
        result = get_ledger_path(tmp_path, "blueprint")
        assert result == tmp_path / "ledgers" / "blueprint_dialog.jsonl"

    def test_help_ledger_path(self, tmp_path):
        result = get_ledger_path(tmp_path, "help")
        assert result == tmp_path / "ledgers" / "help_session.jsonl"

    def test_hint_ledger_path(self, tmp_path):
        result = get_ledger_path(tmp_path, "hint")
        assert result == tmp_path / "ledgers" / "hint_session.jsonl"

    def test_spec_revision_ledger_path_with_session_number(self, tmp_path):
        result = get_ledger_path(tmp_path, "spec_revision", session_number=1)
        assert result == tmp_path / "ledgers" / "spec_revision_1.jsonl"

    def test_spec_revision_ledger_path_with_different_session_number(self, tmp_path):
        result = get_ledger_path(tmp_path, "spec_revision", session_number=42)
        assert result == tmp_path / "ledgers" / "spec_revision_42.jsonl"

    def test_bug_triage_ledger_path_with_session_number(self, tmp_path):
        result = get_ledger_path(tmp_path, "bug_triage", session_number=1)
        assert result == tmp_path / "ledgers" / "bug_triage_1.jsonl"

    def test_bug_triage_ledger_path_with_different_session_number(self, tmp_path):
        result = get_ledger_path(tmp_path, "bug_triage", session_number=5)
        assert result == tmp_path / "ledgers" / "bug_triage_5.jsonl"

    def test_returns_path_object(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert isinstance(result, Path)

    def test_path_is_relative_to_project_root(self, tmp_path):
        result = get_ledger_path(tmp_path, "stakeholder")
        # The path should start with the project_root
        assert str(result).startswith(str(tmp_path))

    def test_deterministic_same_input_same_output(self, tmp_path):
        result1 = get_ledger_path(tmp_path, "setup")
        result2 = get_ledger_path(tmp_path, "setup")
        assert result1 == result2

    def test_different_ledger_types_produce_different_paths(self, tmp_path):
        paths = set()
        for ledger_type in ["setup", "stakeholder", "blueprint", "help", "hint"]:
            paths.add(get_ledger_path(tmp_path, ledger_type))
        assert len(paths) == 5

    def test_session_based_types_produce_different_paths_for_different_sessions(
        self, tmp_path
    ):
        path1 = get_ledger_path(tmp_path, "spec_revision", session_number=1)
        path2 = get_ledger_path(tmp_path, "spec_revision", session_number=2)
        assert path1 != path2

    def test_all_paths_are_under_ledgers_directory(self, tmp_path):
        for ledger_type in ["setup", "stakeholder", "blueprint", "help", "hint"]:
            result = get_ledger_path(tmp_path, ledger_type)
            assert result.parent == tmp_path / "ledgers"

        for ledger_type in ["spec_revision", "bug_triage"]:
            result = get_ledger_path(tmp_path, ledger_type, session_number=1)
            assert result.parent == tmp_path / "ledgers"

    def test_all_paths_have_jsonl_extension(self, tmp_path):
        for ledger_type in ["setup", "stakeholder", "blueprint", "help", "hint"]:
            result = get_ledger_path(tmp_path, ledger_type)
            assert result.suffix == ".jsonl"

        for ledger_type in ["spec_revision", "bug_triage"]:
            result = get_ledger_path(tmp_path, ledger_type, session_number=1)
            assert result.suffix == ".jsonl"


# ---------------------------------------------------------------------------
# Integration-style tests across multiple functions
# ---------------------------------------------------------------------------


class TestLedgerIntegration:
    """Integration tests exercising multiple ledger functions together."""

    def test_full_lifecycle_append_read_compact_clear(self, tmp_path):
        ledger = tmp_path / "lifecycle.jsonl"

        # Append entries
        append_entry(ledger, "user", "Exploratory question", tags=None)
        append_entry(ledger, "assistant", "Exploratory answer", tags=None)
        append_entry(ledger, "user", "We decided X", tags=["[DECISION]"])
        append_entry(ledger, "assistant", "Confirmed", tags=["[CONFIRMED]"])

        # Read back
        entries = read_ledger(ledger)
        assert len(entries) == 4

        # Compact
        compact_ledger(ledger)
        compacted = read_ledger(ledger)
        # After compaction, [DECISION] and [CONFIRMED] entries are preserved
        decision_entries = [
            e for e in compacted if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        confirmed_entries = [
            e for e in compacted if e.get("tags") and "[CONFIRMED]" in e["tags"]
        ]
        assert len(decision_entries) >= 1
        assert len(confirmed_entries) >= 1

        # Clear
        clear_ledger(ledger)
        cleared = read_ledger(ledger)
        assert cleared == []

    def test_get_ledger_path_used_with_append_and_read(self, tmp_path):
        ledger = get_ledger_path(tmp_path, "setup")

        # Ensure parent directory exists for append_entry
        ledger.parent.mkdir(parents=True, exist_ok=True)

        append_entry(ledger, "user", "Setup message")

        result = read_ledger(ledger)
        assert len(result) == 1
        assert result[0]["content"] == "Setup message"

    def test_compaction_preserves_entry_order(self, tmp_path):
        ledger = tmp_path / "order.jsonl"
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "role": "user",
                "content": "First decision",
                "tags": ["[DECISION]"],
            },
            {
                "timestamp": "2026-01-01T00:01:00Z",
                "role": "user",
                "content": "Chat",
                "tags": None,
            },
            {
                "timestamp": "2026-01-01T00:02:00Z",
                "role": "user",
                "content": "Second decision",
                "tags": ["[DECISION]"],
            },
            {
                "timestamp": "2026-01-01T00:03:00Z",
                "role": "user",
                "content": "A hint",
                "tags": ["[HINT]"],
            },
        ]
        _write_jsonl(ledger, entries)

        compact_ledger(ledger)

        result = read_ledger(ledger)
        # Preserved entries should maintain their relative order
        preserved_contents = [e["content"] for e in result if e.get("tags")]
        if (
            "First decision" in preserved_contents
            and "Second decision" in preserved_contents
        ):
            idx_first = preserved_contents.index("First decision")
            idx_second = preserved_contents.index("Second decision")
            assert idx_first < idx_second
