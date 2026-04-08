"""Unit 7: Ledger Management.

Provides JSONL-based ledger operations for dialog tracking across SVP pipeline stages.
"""

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.unit_1.stub import ARTIFACT_FILENAMES

# ---------------------------------------------------------------------------
# Tag sets used during compaction
# ---------------------------------------------------------------------------

# Tags whose entries are truncated when content exceeds the threshold
_TRUNCATABLE_TAGS = {"[QUESTION]", "[DECISION]", "[CONFIRMED]"}

# All recognized tags (truncatable + always-preserved-as-is)
_ALL_TAGS = {"[QUESTION]", "[DECISION]", "[CONFIRMED]", "[HINT]"}

# ---------------------------------------------------------------------------
# Ledger type -> filename mappings (7 types total)
# ---------------------------------------------------------------------------

_LEDGER_FILENAMES: Dict[str, str] = {
    "setup": "setup_dialog.jsonl",
    "stakeholder": "stakeholder_dialog.jsonl",
    "blueprint": "blueprint_dialog.jsonl",
    "help": "help_session.jsonl",
    "hint": "hint_session.jsonl",
}

_LEDGER_PARAMETERIZED: Dict[str, str] = {
    "spec_revision": "spec_revision_{session_number}.jsonl",
    "bug_triage": "bug_triage_{session_number}.jsonl",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def append_entry(
    ledger_path: Path,
    role: str,
    content: str,
    tags: Optional[List[str]] = None,
) -> None:
    """Append a JSONL entry to the ledger file.

    Creates the file and parent directories if absent.
    Each entry has keys: timestamp (ISO-8601 UTC), role, content, tags.
    Uses file-level locking (fcntl) for concurrent safety.
    """
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content,
        "tags": tags if tags is not None else [],
    }

    line = json.dumps(entry, ensure_ascii=False) + "\n"

    with open(ledger_path, "a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def read_ledger(ledger_path: Path) -> List[Dict[str, Any]]:
    """Parse a JSONL ledger file and return list of dicts.

    Returns empty list if the file is absent or empty.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return []

    entries: List[Dict[str, Any]] = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries


def compact_ledger(
    ledger_path: Path,
    character_threshold: int = 200,
) -> None:
    """Compact a ledger by removing non-tagged entries and truncating large tagged ones.

    Compaction rules (no LLM involvement):
    - Preserves all entries with recognized tags ([DECISION], [CONFIRMED], [HINT],
      [QUESTION]).
    - For truncatable tags ([QUESTION], [DECISION], [CONFIRMED]):
        if len(content) > character_threshold  -> delete body, keep tag line only.
        if len(content) <= character_threshold  -> keep body intact.
    - [HINT] entries are always preserved as-is (never truncated).
    - Non-tagged exploratory entries are removed.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return

    entries = read_ledger(ledger_path)
    compacted: List[Dict[str, Any]] = []

    for entry in entries:
        entry_tags = _get_entry_tags(entry)
        if not entry_tags:
            # Non-tagged exploratory entry -> remove
            continue

        content = entry.get("content", "")

        # Does this entry carry any truncatable tag?
        has_truncatable = any(t in _TRUNCATABLE_TAGS for t in entry_tags)

        if has_truncatable and len(content) > character_threshold:
            # Truncate: keep only the tag line from content (or the tag itself)
            truncated = _truncate_content(content, entry_tags)
            entry = dict(entry)
            entry["content"] = truncated
            compacted.append(entry)
        else:
            # Keep as-is ([HINT]-only entries, or entries at/below threshold)
            compacted.append(entry)

    # Rewrite the file atomically
    with open(ledger_path, "w", encoding="utf-8") as f:
        for entry in compacted:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def clear_ledger(ledger_path: Path) -> None:
    """Remove the ledger file. No-op if file absent."""
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return
    ledger_path.unlink()


def append_oracle_run_entry(project_root: Path, entry: Dict[str, Any]) -> None:
    """Append an entry to .svp/oracle_run_ledger.json."""
    ledger_path = project_root / ARTIFACT_FILENAMES["oracle_run_ledger"]
    entries = read_oracle_run_ledger(project_root)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    entries.append(entry)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def read_oracle_run_ledger(project_root: Path) -> List[Dict[str, Any]]:
    """Read all entries from .svp/oracle_run_ledger.json."""
    ledger_path = project_root / ARTIFACT_FILENAMES["oracle_run_ledger"]
    if not ledger_path.is_file():
        return []
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def get_ledger_path(
    project_root: Path,
    ledger_type: str,
    session_number: Optional[int] = None,
) -> Path:
    """Map ledger_type to deterministic path under project_root/ledgers/.

    Supported types (7 total):
        setup, stakeholder, blueprint, help, hint  (static filenames)
        spec_revision, bug_triage                   (parameterized by session_number)
    """
    project_root = Path(project_root)
    ledgers_dir = project_root / "ledgers"

    if ledger_type in _LEDGER_FILENAMES:
        return ledgers_dir / _LEDGER_FILENAMES[ledger_type]
    elif ledger_type in _LEDGER_PARAMETERIZED:
        if session_number is None:
            raise ValueError(
                f"session_number is required for ledger_type '{ledger_type}'"
            )
        filename = _LEDGER_PARAMETERIZED[ledger_type].format(
            session_number=session_number
        )
        return ledgers_dir / filename
    else:
        raise ValueError(f"Unknown ledger_type: '{ledger_type}'")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _entry_has_tag(entry: Dict[str, Any]) -> bool:
    """Check if an entry has any recognized tag in its tags field or content."""
    tags = entry.get("tags") or []
    for tag in tags:
        if tag in _ALL_TAGS:
            return True

    content = entry.get("content", "")
    for tag in _ALL_TAGS:
        if tag in content:
            return True

    return False


def _get_entry_tags(entry: Dict[str, Any]) -> List[str]:
    """Collect all recognized tags from an entry (from both tags list and content text)."""
    found: set = set()

    tags = entry.get("tags") or []
    for tag in tags:
        if tag in _ALL_TAGS:
            found.add(tag)

    content = entry.get("content", "")
    for tag in _ALL_TAGS:
        if tag in content:
            found.add(tag)

    return list(found)


def _truncate_content(content: str, entry_tags: List[str]) -> str:
    """Truncate content for a tagged entry, keeping only the tag line.

    Strategy:
    1. If the content contains a line with a recognized tag, return that line.
    2. Otherwise fall back to the first truncatable tag from entry_tags.
    """
    for line in content.split("\n"):
        for tag in _ALL_TAGS:
            if tag in line:
                return line.strip()

    # Content doesn't embed tags inline; use the tag from the tags field
    for tag in entry_tags:
        if tag in _TRUNCATABLE_TAGS:
            return tag

    # Fallback
    if entry_tags:
        return entry_tags[0]
    return ""
