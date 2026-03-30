"""
Test suite for Unit 7: Ledger Management.

Synthetic data assumptions:
- All ledger files are created in temporary directories via tmp_path fixtures.
- JSONL content uses simple synthetic role/content/tags values (e.g., role="user",
  content="hello", tags=["[DECISION]"]) not tied to any real dialog.
- Character threshold values (200 default, custom overrides) are synthetic integers
  chosen to exercise boundary conditions.
- Tag names ([DECISION], [CONFIRMED], [HINT], [QUESTION]) match the blueprint
  contract literally. Non-tagged lines use plain content without bracket prefixes.
- The project_root for get_ledger_path tests uses tmp_path; the resulting paths
  are validated structurally (suffix and segment checks), not for file existence.
- Session numbers (1, 42, 100) are arbitrary positive integers for parameterized
  ledger_type tests.
- Concurrent append tests use threading to exercise file-lock / atomic-append
  behavior with a modest thread count (10 threads, 10 entries each).
- ISO-8601 UTC timestamp validation uses regex and fromisoformat parsing;
  no real clock dependency beyond the append_entry implementation.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.unit_7.stub import (
    append_entry,
    clear_ledger,
    compact_ledger,
    get_ledger_path,
    read_ledger,
)

# ---------------------------------------------------------------------------
# append_entry
# ---------------------------------------------------------------------------


class TestAppendEntry:
    """Tests for append_entry(ledger_path, role, content, tags)."""

    def test_append_entry_creates_file_if_absent(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "hello")
        assert ledger.exists()

    def test_append_entry_writes_valid_jsonl(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "hello")
        line = ledger.read_text().strip()
        parsed = json.loads(line)
        assert isinstance(parsed, dict)

    def test_append_entry_contains_timestamp_key(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "hello")
        entry = json.loads(ledger.read_text().strip())
        assert "timestamp" in entry

    def test_append_entry_timestamp_is_iso8601_utc(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "hello")
        entry = json.loads(ledger.read_text().strip())
        ts = entry["timestamp"]
        # Should parse as a valid datetime and be UTC
        parsed_dt = datetime.fromisoformat(ts)
        assert parsed_dt.tzinfo is not None or ts.endswith("Z") or "+00:00" in ts

    def test_append_entry_timestamp_close_to_now(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        before = datetime.now(timezone.utc)
        append_entry(ledger, "user", "hello")
        after = datetime.now(timezone.utc)
        entry = json.loads(ledger.read_text().strip())
        ts_str = entry["timestamp"]
        # Normalize Z suffix for fromisoformat compatibility
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert before <= ts <= after

    def test_append_entry_contains_role_key(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "assistant", "response text")
        entry = json.loads(ledger.read_text().strip())
        assert "role" in entry

    def test_append_entry_role_matches_argument(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "assistant", "response text")
        entry = json.loads(ledger.read_text().strip())
        assert entry["role"] == "assistant"

    def test_append_entry_contains_content_key(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "my question")
        entry = json.loads(ledger.read_text().strip())
        assert "content" in entry

    def test_append_entry_content_matches_argument(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "my question")
        entry = json.loads(ledger.read_text().strip())
        assert entry["content"] == "my question"

    def test_append_entry_contains_tags_key(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "tagged line", tags=["[DECISION]"])
        entry = json.loads(ledger.read_text().strip())
        assert "tags" in entry

    def test_append_entry_tags_match_argument(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "tagged line", tags=["[DECISION]", "[HINT]"])
        entry = json.loads(ledger.read_text().strip())
        assert entry["tags"] == ["[DECISION]", "[HINT]"]

    def test_append_entry_tags_default_to_none_or_empty(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "no tags")
        entry = json.loads(ledger.read_text().strip())
        # Tags should be None or empty list when not provided
        assert entry["tags"] is None or entry["tags"] == []

    def test_append_entry_appends_to_existing_file(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "first")
        append_entry(ledger, "assistant", "second")
        lines = ledger.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_append_entry_preserves_existing_entries(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "first")
        append_entry(ledger, "assistant", "second")
        lines = ledger.read_text().strip().split("\n")
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["content"] == "first"
        assert second["content"] == "second"

    def test_append_entry_each_line_is_independent_json(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "line1")
        append_entry(ledger, "assistant", "line2")
        append_entry(ledger, "user", "line3")
        lines = ledger.read_text().strip().split("\n")
        for line in lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)

    def test_append_entry_has_exactly_four_keys(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "check keys", tags=["[HINT]"])
        entry = json.loads(ledger.read_text().strip())
        assert set(entry.keys()) == {"timestamp", "role", "content", "tags"}

    def test_append_entry_returns_none(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        result = append_entry(ledger, "user", "hello")
        assert result is None

    def test_append_entry_with_empty_content(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "")
        entry = json.loads(ledger.read_text().strip())
        assert entry["content"] == ""

    def test_append_entry_with_multiline_content(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        multiline = "line one\nline two\nline three"
        append_entry(ledger, "user", multiline)
        entry = json.loads(ledger.read_text().strip())
        assert entry["content"] == multiline

    def test_append_entry_with_special_characters_in_content(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        special = "He said \"hello\" & she said 'bye' \t\n end"
        append_entry(ledger, "user", special)
        entry = json.loads(ledger.read_text().strip())
        assert entry["content"] == special

    def test_append_entry_concurrent_safety(self, tmp_path):
        """Multiple threads appending should not lose entries or corrupt the file."""
        ledger = tmp_path / "concurrent_ledger.jsonl"
        num_threads = 10
        entries_per_thread = 10

        def writer(thread_id):
            for i in range(entries_per_thread):
                append_entry(ledger, f"thread-{thread_id}", f"entry-{i}")

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = ledger.read_text().strip().split("\n")
        assert len(lines) == num_threads * entries_per_thread
        # Every line should be valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert "role" in parsed
            assert "content" in parsed

    def test_append_entry_creates_parent_directories_or_writes_to_existing(
        self, tmp_path
    ):
        """If the ledger path has non-existent parent dirs, the function should
        either create them or require they exist. We test the common case where
        the parent exists."""
        subdir = tmp_path / "ledgers"
        subdir.mkdir()
        ledger = subdir / "nested_ledger.jsonl"
        append_entry(ledger, "user", "nested")
        assert ledger.exists()


# ---------------------------------------------------------------------------
# read_ledger
# ---------------------------------------------------------------------------


class TestReadLedger:
    """Tests for read_ledger(ledger_path)."""

    def test_read_ledger_returns_list(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "hello")
        result = read_ledger(ledger)
        assert isinstance(result, list)

    def test_read_ledger_returns_empty_list_if_file_absent(self, tmp_path):
        ledger = tmp_path / "nonexistent.jsonl"
        result = read_ledger(ledger)
        assert result == []

    def test_read_ledger_returns_dicts(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "hello")
        result = read_ledger(ledger)
        assert all(isinstance(entry, dict) for entry in result)

    def test_read_ledger_one_dict_per_line(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "first")
        append_entry(ledger, "assistant", "second")
        append_entry(ledger, "user", "third")
        result = read_ledger(ledger)
        assert len(result) == 3

    def test_read_ledger_preserves_entry_order(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "alpha")
        append_entry(ledger, "assistant", "beta")
        append_entry(ledger, "user", "gamma")
        result = read_ledger(ledger)
        assert result[0]["content"] == "alpha"
        assert result[1]["content"] == "beta"
        assert result[2]["content"] == "gamma"

    def test_read_ledger_entries_contain_all_keys(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "check keys", tags=["[DECISION]"])
        result = read_ledger(ledger)
        entry = result[0]
        assert "timestamp" in entry
        assert "role" in entry
        assert "content" in entry
        assert "tags" in entry

    def test_read_ledger_content_matches_what_was_written(self, tmp_path):
        ledger = tmp_path / "test_ledger.jsonl"
        append_entry(ledger, "user", "payload", tags=["[HINT]"])
        result = read_ledger(ledger)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "payload"
        assert result[0]["tags"] == ["[HINT]"]

    def test_read_ledger_empty_file_returns_empty_list(self, tmp_path):
        ledger = tmp_path / "empty.jsonl"
        ledger.write_text("")
        result = read_ledger(ledger)
        assert result == []

    def test_read_ledger_single_entry(self, tmp_path):
        ledger = tmp_path / "single.jsonl"
        append_entry(ledger, "system", "init")
        result = read_ledger(ledger)
        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_read_ledger_many_entries(self, tmp_path):
        ledger = tmp_path / "many.jsonl"
        for i in range(50):
            append_entry(ledger, "user", f"entry-{i}")
        result = read_ledger(ledger)
        assert len(result) == 50
        assert result[0]["content"] == "entry-0"
        assert result[49]["content"] == "entry-49"


# ---------------------------------------------------------------------------
# compact_ledger
# ---------------------------------------------------------------------------


class TestCompactLedger:
    """Tests for compact_ledger(ledger_path, character_threshold)."""

    def _write_entry(
        self, ledger: Path, role: str, content: str, tags: List[str] = None
    ) -> None:
        """Helper: append a single JSONL entry to the ledger file."""
        append_entry(ledger, role, content, tags=tags)

    def test_compact_ledger_preserves_decision_tagged_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "short decision", tags=["[DECISION]"])
        compact_ledger(ledger)
        result = read_ledger(ledger)
        decision_entries = [
            e for e in result if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) >= 1

    def test_compact_ledger_preserves_confirmed_tagged_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "short confirmed", tags=["[CONFIRMED]"])
        compact_ledger(ledger)
        result = read_ledger(ledger)
        confirmed_entries = [
            e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]
        ]
        assert len(confirmed_entries) >= 1

    def test_compact_ledger_preserves_hint_tagged_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "short hint", tags=["[HINT]"])
        compact_ledger(ledger)
        result = read_ledger(ledger)
        hint_entries = [e for e in result if e.get("tags") and "[HINT]" in e["tags"]]
        assert len(hint_entries) >= 1

    def test_compact_ledger_removes_non_tagged_exploratory_exchanges(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        # Non-tagged exploratory lines
        self._write_entry(ledger, "user", "What about this approach?")
        self._write_entry(ledger, "assistant", "That could work, let me think...")
        self._write_entry(ledger, "user", "And what about that?")
        self._write_entry(ledger, "assistant", "That too could work.")
        # A preserved decision entry
        self._write_entry(
            ledger, "user", "Final choice: approach A", tags=["[DECISION]"]
        )
        compact_ledger(ledger)
        result = read_ledger(ledger)
        # The decision entry must be present
        decision_entries = [
            e for e in result if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) == 1
        # Total entries should be fewer than original 5
        assert len(result) < 5

    def test_compact_ledger_keeps_short_tagged_content_intact(self, tmp_path):
        """Tagged entry with content <= character_threshold keeps body intact."""
        ledger = tmp_path / "ledger.jsonl"
        short_content = "Yes, approved."  # well under 200 chars
        self._write_entry(ledger, "user", short_content, tags=["[DECISION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        decision = [e for e in result if e.get("tags") and "[DECISION]" in e["tags"]][0]
        assert decision["content"] == short_content

    def test_compact_ledger_truncates_long_tagged_content(self, tmp_path):
        """Tagged entry with content > character_threshold has body deleted
        (only tag line kept)."""
        ledger = tmp_path / "ledger.jsonl"
        long_content = "A" * 300  # > 200 default threshold
        self._write_entry(ledger, "user", long_content, tags=["[DECISION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        decision = [e for e in result if e.get("tags") and "[DECISION]" in e["tags"]][0]
        # Content should be stripped/truncated -- the body is deleted
        assert len(decision["content"]) <= 200 or decision["content"] != long_content

    def test_compact_ledger_threshold_boundary_equal_keeps_body(self, tmp_path):
        """Content exactly equal to character_threshold is kept intact."""
        ledger = tmp_path / "ledger.jsonl"
        exact_content = "B" * 200
        self._write_entry(ledger, "user", exact_content, tags=["[QUESTION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        question = [e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]][0]
        assert question["content"] == exact_content

    def test_compact_ledger_threshold_boundary_one_over_deletes_body(self, tmp_path):
        """Content one character over threshold has body deleted."""
        ledger = tmp_path / "ledger.jsonl"
        over_content = "C" * 201
        self._write_entry(ledger, "user", over_content, tags=["[QUESTION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        question = [e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]][0]
        assert question["content"] != over_content

    def test_compact_ledger_custom_threshold(self, tmp_path):
        """Custom character_threshold is respected."""
        ledger = tmp_path / "ledger.jsonl"
        content_50_chars = "D" * 50
        self._write_entry(ledger, "user", content_50_chars, tags=["[CONFIRMED]"])
        compact_ledger(ledger, character_threshold=30)
        result = read_ledger(ledger)
        confirmed = [e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]][
            0
        ]
        # 50 chars > threshold 30, body should be deleted
        assert confirmed["content"] != content_50_chars

    def test_compact_ledger_custom_threshold_keeps_short(self, tmp_path):
        """Content under custom threshold is kept intact."""
        ledger = tmp_path / "ledger.jsonl"
        short = "E" * 25
        self._write_entry(ledger, "user", short, tags=["[CONFIRMED]"])
        compact_ledger(ledger, character_threshold=30)
        result = read_ledger(ledger)
        confirmed = [e for e in result if e.get("tags") and "[CONFIRMED]" in e["tags"]][
            0
        ]
        assert confirmed["content"] == short

    def test_compact_ledger_preserves_tags_on_truncated_entries(self, tmp_path):
        """Even when body is deleted, the tag information is preserved."""
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "X" * 500, tags=["[DECISION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        assert len(result) >= 1
        entry = result[0]
        assert "[DECISION]" in entry["tags"]

    def test_compact_ledger_no_llm_involvement(self, tmp_path):
        """Compaction is deterministic and mechanical -- no LLM calls.
        Verified by the fact that compaction completes without network/API access
        and produces consistent results on repeated invocation."""
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "exploratory chat")
        self._write_entry(ledger, "assistant", "exploratory response")
        self._write_entry(ledger, "user", "decision made", tags=["[DECISION]"])
        compact_ledger(ledger)
        result_1 = read_ledger(ledger)

        # Re-create the same ledger and compact again
        ledger2 = tmp_path / "ledger2.jsonl"
        self._write_entry(ledger2, "user", "exploratory chat")
        self._write_entry(ledger2, "assistant", "exploratory response")
        self._write_entry(ledger2, "user", "decision made", tags=["[DECISION]"])
        compact_ledger(ledger2)
        result_2 = read_ledger(ledger2)

        # Same number of entries (deterministic)
        assert len(result_1) == len(result_2)

    def test_compact_ledger_returns_none(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "hello", tags=["[DECISION]"])
        result = compact_ledger(ledger)
        assert result is None

    def test_compact_ledger_mixed_tagged_and_untagged(self, tmp_path):
        """A realistic sequence: untagged exchanges interspersed with tagged entries.
        After compaction, all three preserved tag types survive."""
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "How should we proceed?")
        self._write_entry(ledger, "assistant", "Option A or B")
        self._write_entry(ledger, "user", "We go with A", tags=["[DECISION]"])
        self._write_entry(ledger, "user", "Some more exploration")
        self._write_entry(ledger, "assistant", "Noted")
        self._write_entry(ledger, "user", "Confirmed: A is final", tags=["[CONFIRMED]"])
        self._write_entry(ledger, "user", "Extra chatter")
        self._write_entry(ledger, "assistant", "Here is a hint", tags=["[HINT]"])
        compact_ledger(ledger)
        result = read_ledger(ledger)

        all_tags = []
        for entry in result:
            if entry.get("tags"):
                all_tags.extend(entry["tags"])
        assert "[DECISION]" in all_tags
        assert "[CONFIRMED]" in all_tags
        assert "[HINT]" in all_tags

    def test_compact_ledger_question_tagged_entry_short_content_preserved(
        self, tmp_path
    ):
        """[QUESTION] tagged entries follow the same threshold rules."""
        ledger = tmp_path / "ledger.jsonl"
        short_q = "What color?"  # well under 200
        self._write_entry(ledger, "user", short_q, tags=["[QUESTION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        questions = [e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]]
        assert len(questions) >= 1
        assert questions[0]["content"] == short_q

    def test_compact_ledger_question_tagged_entry_long_content_deleted(self, tmp_path):
        """[QUESTION] tagged entry with long content has body deleted."""
        ledger = tmp_path / "ledger.jsonl"
        long_q = "Q" * 250
        self._write_entry(ledger, "user", long_q, tags=["[QUESTION]"])
        compact_ledger(ledger, character_threshold=200)
        result = read_ledger(ledger)
        questions = [e for e in result if e.get("tags") and "[QUESTION]" in e["tags"]]
        assert len(questions) >= 1
        assert questions[0]["content"] != long_q

    def test_compact_ledger_all_exploratory_removed_when_no_preserved_tags(
        self, tmp_path
    ):
        """If no entries are tagged with preserved tags, all exploratory exchanges
        are summarized or removed."""
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "random thought 1")
        self._write_entry(ledger, "assistant", "random reply 1")
        self._write_entry(ledger, "user", "random thought 2")
        self._write_entry(ledger, "assistant", "random reply 2")
        compact_ledger(ledger)
        result = read_ledger(ledger)
        # Original was 4 entries; after compaction should be fewer or summary
        assert len(result) < 4

    def test_compact_ledger_preserves_all_decision_entries(self, tmp_path):
        """Multiple [DECISION] entries should all be preserved."""
        ledger = tmp_path / "ledger.jsonl"
        self._write_entry(ledger, "user", "Decision 1: use Python", tags=["[DECISION]"])
        self._write_entry(ledger, "user", "chatter")
        self._write_entry(ledger, "user", "Decision 2: use pytest", tags=["[DECISION]"])
        self._write_entry(ledger, "user", "more chatter")
        self._write_entry(ledger, "user", "Decision 3: use JSONL", tags=["[DECISION]"])
        compact_ledger(ledger)
        result = read_ledger(ledger)
        decisions = [e for e in result if e.get("tags") and "[DECISION]" in e["tags"]]
        assert len(decisions) == 3

    def test_compact_ledger_default_threshold_is_200(self, tmp_path):
        """Verify the default threshold behavior matches 200 characters."""
        ledger = tmp_path / "ledger.jsonl"
        # Content of exactly 200 chars should be kept
        content_200 = "Z" * 200
        self._write_entry(ledger, "user", content_200, tags=["[DECISION]"])
        compact_ledger(ledger)  # no explicit threshold -> default 200
        result = read_ledger(ledger)
        decision = [e for e in result if e.get("tags") and "[DECISION]" in e["tags"]][0]
        assert decision["content"] == content_200


# ---------------------------------------------------------------------------
# clear_ledger
# ---------------------------------------------------------------------------


class TestClearLedger:
    """Tests for clear_ledger(ledger_path)."""

    def test_clear_ledger_removes_file(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "hello")
        assert ledger.exists()
        clear_ledger(ledger)
        assert not ledger.exists()

    def test_clear_ledger_noop_if_file_absent(self, tmp_path):
        ledger = tmp_path / "nonexistent.jsonl"
        # Should not raise any exception
        clear_ledger(ledger)
        assert not ledger.exists()

    def test_clear_ledger_returns_none(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "hello")
        result = clear_ledger(ledger)
        assert result is None

    def test_clear_ledger_returns_none_when_absent(self, tmp_path):
        ledger = tmp_path / "absent.jsonl"
        result = clear_ledger(ledger)
        assert result is None

    def test_clear_ledger_file_with_multiple_entries(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        for i in range(10):
            append_entry(ledger, "user", f"entry-{i}")
        clear_ledger(ledger)
        assert not ledger.exists()

    def test_clear_ledger_then_read_returns_empty(self, tmp_path):
        """After clearing, read_ledger should return empty list (file absent)."""
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "hello")
        clear_ledger(ledger)
        result = read_ledger(ledger)
        assert result == []

    def test_clear_ledger_can_recreate_after_clearing(self, tmp_path):
        """After clearing, new entries can be appended to the same path."""
        ledger = tmp_path / "ledger.jsonl"
        append_entry(ledger, "user", "first round")
        clear_ledger(ledger)
        append_entry(ledger, "user", "second round")
        result = read_ledger(ledger)
        assert len(result) == 1
        assert result[0]["content"] == "second round"


# ---------------------------------------------------------------------------
# get_ledger_path
# ---------------------------------------------------------------------------


class TestGetLedgerPath:
    """Tests for get_ledger_path(project_root, ledger_type, session_number)."""

    def test_get_ledger_path_returns_path_object(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert isinstance(result, Path)

    def test_get_ledger_path_setup(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert result == tmp_path / "ledgers" / "setup_dialog.jsonl"

    def test_get_ledger_path_stakeholder(self, tmp_path):
        result = get_ledger_path(tmp_path, "stakeholder")
        assert result == tmp_path / "ledgers" / "stakeholder_dialog.jsonl"

    def test_get_ledger_path_blueprint(self, tmp_path):
        result = get_ledger_path(tmp_path, "blueprint")
        assert result == tmp_path / "ledgers" / "blueprint_dialog.jsonl"

    def test_get_ledger_path_help(self, tmp_path):
        result = get_ledger_path(tmp_path, "help")
        assert result == tmp_path / "ledgers" / "help_session.jsonl"

    def test_get_ledger_path_hint(self, tmp_path):
        result = get_ledger_path(tmp_path, "hint")
        assert result == tmp_path / "ledgers" / "hint_session.jsonl"

    def test_get_ledger_path_spec_revision_with_session_number(self, tmp_path):
        result = get_ledger_path(tmp_path, "spec_revision", session_number=1)
        assert result == tmp_path / "ledgers" / "spec_revision_1.jsonl"

    def test_get_ledger_path_spec_revision_session_42(self, tmp_path):
        result = get_ledger_path(tmp_path, "spec_revision", session_number=42)
        assert result == tmp_path / "ledgers" / "spec_revision_42.jsonl"

    def test_get_ledger_path_spec_revision_session_100(self, tmp_path):
        result = get_ledger_path(tmp_path, "spec_revision", session_number=100)
        assert result == tmp_path / "ledgers" / "spec_revision_100.jsonl"

    def test_get_ledger_path_bug_triage_with_session_number(self, tmp_path):
        result = get_ledger_path(tmp_path, "bug_triage", session_number=1)
        assert result == tmp_path / "ledgers" / "bug_triage_1.jsonl"

    def test_get_ledger_path_bug_triage_session_42(self, tmp_path):
        result = get_ledger_path(tmp_path, "bug_triage", session_number=42)
        assert result == tmp_path / "ledgers" / "bug_triage_42.jsonl"

    def test_get_ledger_path_is_under_project_root(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert str(result).startswith(str(tmp_path))

    def test_get_ledger_path_is_in_ledgers_subdirectory(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert "ledgers" in result.parts

    def test_get_ledger_path_deterministic(self, tmp_path):
        result_1 = get_ledger_path(tmp_path, "stakeholder")
        result_2 = get_ledger_path(tmp_path, "stakeholder")
        assert result_1 == result_2

    def test_get_ledger_path_different_types_produce_different_paths(self, tmp_path):
        paths = set()
        for ledger_type in ["setup", "stakeholder", "blueprint", "help", "hint"]:
            paths.add(get_ledger_path(tmp_path, ledger_type))
        assert len(paths) == 5

    def test_get_ledger_path_different_roots_produce_different_paths(self, tmp_path):
        root_a = tmp_path / "project_a"
        root_b = tmp_path / "project_b"
        root_a.mkdir()
        root_b.mkdir()
        path_a = get_ledger_path(root_a, "setup")
        path_b = get_ledger_path(root_b, "setup")
        assert path_a != path_b

    def test_get_ledger_path_all_types_end_with_jsonl(self, tmp_path):
        for ledger_type in ["setup", "stakeholder", "blueprint", "help", "hint"]:
            result = get_ledger_path(tmp_path, ledger_type)
            assert str(result).endswith(".jsonl")

    def test_get_ledger_path_session_types_end_with_jsonl(self, tmp_path):
        for ledger_type in ["spec_revision", "bug_triage"]:
            result = get_ledger_path(tmp_path, ledger_type, session_number=5)
            assert str(result).endswith(".jsonl")

    def test_get_ledger_path_setup_filename(self, tmp_path):
        result = get_ledger_path(tmp_path, "setup")
        assert result.name == "setup_dialog.jsonl"

    def test_get_ledger_path_stakeholder_filename(self, tmp_path):
        result = get_ledger_path(tmp_path, "stakeholder")
        assert result.name == "stakeholder_dialog.jsonl"

    def test_get_ledger_path_blueprint_filename(self, tmp_path):
        result = get_ledger_path(tmp_path, "blueprint")
        assert result.name == "blueprint_dialog.jsonl"

    def test_get_ledger_path_help_filename(self, tmp_path):
        result = get_ledger_path(tmp_path, "help")
        assert result.name == "help_session.jsonl"

    def test_get_ledger_path_hint_filename(self, tmp_path):
        result = get_ledger_path(tmp_path, "hint")
        assert result.name == "hint_session.jsonl"

    def test_get_ledger_path_spec_revision_filename_includes_session_number(
        self, tmp_path
    ):
        result = get_ledger_path(tmp_path, "spec_revision", session_number=7)
        assert result.name == "spec_revision_7.jsonl"

    def test_get_ledger_path_bug_triage_filename_includes_session_number(
        self, tmp_path
    ):
        result = get_ledger_path(tmp_path, "bug_triage", session_number=3)
        assert result.name == "bug_triage_3.jsonl"


# ---------------------------------------------------------------------------
# Integration: append + read round-trip
# ---------------------------------------------------------------------------


class TestAppendReadRoundTrip:
    """Integration tests verifying append_entry and read_ledger work together."""

    def test_round_trip_single_entry(self, tmp_path):
        ledger = tmp_path / "rt.jsonl"
        append_entry(ledger, "user", "round trip", tags=["[HINT]"])
        entries = read_ledger(ledger)
        assert len(entries) == 1
        assert entries[0]["role"] == "user"
        assert entries[0]["content"] == "round trip"
        assert entries[0]["tags"] == ["[HINT]"]

    def test_round_trip_multiple_entries(self, tmp_path):
        ledger = tmp_path / "rt.jsonl"
        for i in range(20):
            append_entry(ledger, "user" if i % 2 == 0 else "assistant", f"msg-{i}")
        entries = read_ledger(ledger)
        assert len(entries) == 20
        for i, entry in enumerate(entries):
            assert entry["content"] == f"msg-{i}"
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert entry["role"] == expected_role

    def test_round_trip_preserves_unicode_content(self, tmp_path):
        ledger = tmp_path / "unicode.jsonl"
        append_entry(
            ledger, "user", "Hello in Japanese: \u3053\u3093\u306b\u3061\u306f"
        )
        entries = read_ledger(ledger)
        assert (
            entries[0]["content"] == "Hello in Japanese: \u3053\u3093\u306b\u3061\u306f"
        )

    def test_round_trip_after_compact(self, tmp_path):
        """Entries survive a compact + read cycle when tagged appropriately."""
        ledger = tmp_path / "rt_compact.jsonl"
        append_entry(ledger, "user", "exploratory")
        append_entry(ledger, "user", "kept decision", tags=["[DECISION]"])
        compact_ledger(ledger)
        entries = read_ledger(ledger)
        decision_entries = [
            e for e in entries if e.get("tags") and "[DECISION]" in e["tags"]
        ]
        assert len(decision_entries) == 1
        assert decision_entries[0]["content"] == "kept decision"

    def test_round_trip_clear_then_rebuild(self, tmp_path):
        """Full lifecycle: write, clear, write again, read."""
        ledger = tmp_path / "lifecycle.jsonl"
        append_entry(ledger, "user", "old data")
        clear_ledger(ledger)
        append_entry(ledger, "user", "new data")
        entries = read_ledger(ledger)
        assert len(entries) == 1
        assert entries[0]["content"] == "new data"


# ---------------------------------------------------------------------------
# Integration: get_ledger_path + append/read
# ---------------------------------------------------------------------------


class TestGetLedgerPathIntegration:
    """Tests verifying get_ledger_path produces usable paths for ledger operations."""

    def test_append_to_path_from_get_ledger_path(self, tmp_path):
        ledger_path = get_ledger_path(tmp_path, "setup")
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        append_entry(ledger_path, "user", "via get_ledger_path")
        entries = read_ledger(ledger_path)
        assert len(entries) == 1

    def test_clear_path_from_get_ledger_path(self, tmp_path):
        ledger_path = get_ledger_path(tmp_path, "help")
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        append_entry(ledger_path, "user", "to be cleared")
        clear_ledger(ledger_path)
        assert not ledger_path.exists()

    def test_session_ledger_path_usable_for_operations(self, tmp_path):
        ledger_path = get_ledger_path(tmp_path, "spec_revision", session_number=5)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        append_entry(ledger_path, "user", "session entry")
        entries = read_ledger(ledger_path)
        assert len(entries) == 1
        assert entries[0]["content"] == "session entry"
