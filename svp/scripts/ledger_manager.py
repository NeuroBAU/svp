"""Unit 7: Ledger Management.

Provides JSONL-based ledger operations for dialog tracking across SVP pipeline stages.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Tags recognized during compaction
_TRUNCATABLE_TAGS = {"[QUESTION]", "[DECISION]", "[CONFIRMED]"}
_ALL_TAGS = {"[QUESTION]", "[DECISION]", "[CONFIRMED]", "[HINT]"}

# Ledger type to filename mapping
_LEDGER_FILENAMES = {
    "setup": "setup_dialog.jsonl",
    "stakeholder": "stakeholder_dialog.jsonl",
    "blueprint": "blueprint_dialog.jsonl",
    "help": "help_session.jsonl",
    "hint": "hint_session.jsonl",
}

_LEDGER_PARAMETERIZED = {
    "spec_revision": "spec_revision_{session_number}.jsonl",
    "bug_triage": "bug_triage_{session_number}.jsonl",
}


def append_entry(
    ledger_path: Path,
    role: str,
    content: str,
    tags: Optional[List[str]] = None,
) -> None:
    """Append a JSONL entry to the ledger file.

    Creates the file and parent directories if absent.
    Each entry has keys: timestamp (ISO-8601 UTC), role, content, tags.
    """
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content,
        "tags": tags if tags is not None else [],
    }

    line = json.dumps(entry, ensure_ascii=False)

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_ledger(ledger_path: Path) -> List[Dict[str, Any]]:
    """Parse a JSONL ledger file and return list of dicts.

    Returns empty list if the file is absent.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return []

    entries: List[Dict[str, Any]] = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries


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
    """Get all recognized tags from an entry (from both tags field and content)."""
    found = set()

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

    If the content contains a tag inline, extract the line with the tag.
    Otherwise, use the first tag from the entry's tags field.
    """
    # First, try to find a line in the content that contains a tag
    for line in content.split("\n"):
        for tag in _ALL_TAGS:
            if tag in line:
                return line.strip()

    # Content doesn't contain tags inline; use the tag from the tags field
    # Return the first truncatable tag found
    for tag in entry_tags:
        if tag in _TRUNCATABLE_TAGS:
            return tag

    # Fallback (shouldn't reach here if called correctly)
    if entry_tags:
        return entry_tags[0]
    return ""


def compact_ledger(
    ledger_path: Path,
    character_threshold: int = 200,
) -> None:
    """Compact a ledger by removing non-tagged entries and truncating large tagged entries.

    - Preserves all entries with recognized tags ([QUESTION], [DECISION], [CONFIRMED], [HINT]).
    - For tagged lines ([QUESTION], [DECISION], [CONFIRMED]): if len(content) > character_threshold,
      delete body (keep tag line only). If len(content) <= character_threshold, keep body intact.
    - [HINT] entries are always preserved as-is (no truncation).
    - Non-tagged entries are removed.
    - No LLM involvement.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return

    entries = read_ledger(ledger_path)
    compacted: List[Dict[str, Any]] = []

    for entry in entries:
        if not _entry_has_tag(entry):
            # Non-tagged: remove
            continue

        entry_tags = _get_entry_tags(entry)
        content = entry.get("content", "")

        # Check if this entry has any truncatable tags
        has_truncatable = any(t in _TRUNCATABLE_TAGS for t in entry_tags)

        if has_truncatable and len(content) > character_threshold:
            # Truncate: keep only the tag line
            truncated = _truncate_content(content, entry_tags)
            entry = dict(entry)
            entry["content"] = truncated
            compacted.append(entry)
        else:
            # Keep as-is (includes [HINT]-only entries, and entries at/below threshold)
            compacted.append(entry)

    # Rewrite the file
    with open(ledger_path, "w", encoding="utf-8") as f:
        for entry in compacted:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def clear_ledger(ledger_path: Path) -> None:
    """Rename ledger to .bak and create empty file. No-op if file absent."""
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return

    # Rename to .bak
    bak_path = ledger_path.with_suffix(ledger_path.suffix + ".bak")
    ledger_path.rename(bak_path)

    # Create empty file
    with open(ledger_path, "w", encoding="utf-8") as f:
        pass


def get_ledger_path(
    project_root: Path,
    ledger_type: str,
    session_number: Optional[int] = None,
) -> Path:
    """Map ledger_type to deterministic path under project_root/ledgers/.

    Types: setup, stakeholder, blueprint, help, hint, spec_revision, bug_triage.
    Parameterized types (spec_revision, bug_triage) require session_number.
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
