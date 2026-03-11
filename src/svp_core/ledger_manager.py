"""Ledger Manager -- manage JSONL conversation ledgers."""

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json
import re


class LedgerEntry:
    """Represents a single entry in a JSONL conversation ledger."""

    role: str           # "agent", "human", "system"
    content: str
    timestamp: str      # ISO format
    metadata: Optional[Dict[str, Any]]  # e.g., gate info for [HINT] entries

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp if timestamp is not None else datetime.now().isoformat()
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry":
        for field in ("role", "content", "timestamp"):
            if field not in data:
                raise ValueError(f"Invalid ledger entry: missing required field '{field}'")
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata"),
        )


def _validate_jsonl_extension(ledger_path: Path) -> None:
    """Validate that the path has a .jsonl extension."""
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"


def append_entry(ledger_path: Path, entry: LedgerEntry) -> None:
    """Append a single JSONL line to the ledger file.

    Creates the file if it does not exist. Writes atomically in append mode.
    """
    _validate_jsonl_extension(ledger_path)
    # Ensure parent directory exists
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")
    assert ledger_path.exists(), "Ledger file must exist after append"


def read_ledger(ledger_path: Path) -> List[LedgerEntry]:
    """Read all entries from a JSONL file and return them as LedgerEntry instances.

    Returns an empty list for a non-existent or empty file.
    """
    _validate_jsonl_extension(ledger_path)
    if not ledger_path.exists():
        return []

    text = ledger_path.read_text(encoding="utf-8")
    if not text.strip():
        return []

    entries: List[LedgerEntry] = []
    for line_num, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            raise json.JSONDecodeError(
                f"Malformed JSONL entry at line {line_num}",
                text,
                0,
            )
        entries.append(LedgerEntry.from_dict(data))

    assert all(isinstance(e, LedgerEntry) for e in entries), \
        "All entries must be LedgerEntry instances"
    return entries


def clear_ledger(ledger_path: Path) -> None:
    """Truncate the ledger file to zero bytes. The file continues to exist."""
    _validate_jsonl_extension(ledger_path)
    ledger_path.write_text("", encoding="utf-8")


def rename_ledger(ledger_path: Path, new_name: str) -> Path:
    """Rename the ledger file. Returns the new path."""
    _validate_jsonl_extension(ledger_path)
    new_path = ledger_path.parent / new_name
    ledger_path.rename(new_path)
    return new_path


def get_ledger_size_chars(ledger_path: Path) -> int:
    """Return the total character count of the ledger file."""
    _validate_jsonl_extension(ledger_path)
    if not ledger_path.exists():
        return 0
    return len(ledger_path.read_text(encoding="utf-8"))


def check_ledger_capacity(
    ledger_path: Path, max_chars: int
) -> Tuple[float, Optional[str]]:
    """Return a tuple of (usage fraction 0.0-1.0, warning message or None).

    Warning at 80%, required action at 90%.
    """
    _validate_jsonl_extension(ledger_path)
    current_size = get_ledger_size_chars(ledger_path)
    if max_chars <= 0:
        fraction = 1.0
    else:
        fraction = current_size / max_chars

    warning: Optional[str] = None
    if fraction >= 0.9:
        warning = "Ledger at 90% capacity or above: compaction or clearing required"
    elif fraction >= 0.8:
        warning = "Ledger at 80% capacity: consider compaction"

    return (fraction, warning)


def extract_tagged_lines(content: str) -> List[Tuple[str, str]]:
    """Parse content for [QUESTION], [DECISION], and [CONFIRMED] markers.

    Returns a list of (marker, full_line) tuples.
    """
    results: List[Tuple[str, str]] = []
    tag_pattern = re.compile(r"\[(QUESTION|DECISION|CONFIRMED)\]")
    for line in content.splitlines():
        match = tag_pattern.search(line)
        if match:
            marker = f"[{match.group(1)}]"
            results.append((marker, line))
    return results


def compact_ledger(ledger_path: Path, character_threshold: int = 200) -> int:
    """Implement the compaction algorithm.

    Identifies sequences where agent bodies led to a [DECISION] or [CONFIRMED]
    closing. For tagged lines above character_threshold characters, the body is
    deleted (the tagged line is presumed self-contained). For tagged lines at or
    below the threshold, the body is preserved. [HINT] entries are always
    preserved verbatim. Returns the number of characters saved.
    """
    _validate_jsonl_extension(ledger_path)
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger file not found: {ledger_path}")

    entries = read_ledger(ledger_path)
    if not entries:
        return 0

    # Build the original content for size comparison
    original_text = ledger_path.read_text(encoding="utf-8")
    original_size = len(original_text)

    # Process entries for compaction
    # The algorithm: look for agent entries whose content contains [DECISION]
    # or [CONFIRMED] tagged lines. For those entries, if the tagged lines are
    # above character_threshold, remove the non-tagged body lines.
    # [HINT] entries (system entries with [HINT] in content) are always preserved.

    compacted_entries: List[LedgerEntry] = []
    for entry in entries:
        # [HINT] entries are always preserved verbatim
        if entry.role == "system" and "[HINT]" in entry.content:
            compacted_entries.append(entry)
            continue

        # Check if this entry has [DECISION] or [CONFIRMED] tagged lines
        tagged = extract_tagged_lines(entry.content)
        decision_or_confirmed = [
            (marker, line) for marker, line in tagged
            if marker in ("[DECISION]", "[CONFIRMED]")
        ]

        if not decision_or_confirmed:
            # No decision/confirmed tags -- preserve as-is
            compacted_entries.append(entry)
            continue

        # This entry has decision/confirmed closings
        # Check if any tagged line is above the threshold
        content_lines = entry.content.splitlines()
        tagged_line_set = set(line for _, line in tagged)

        # Determine if we should compact: look at the tagged lines
        # For tagged lines above character_threshold, delete the body
        # For tagged lines at or below, preserve the body
        should_compact = False
        for _, tagged_line in decision_or_confirmed:
            if len(tagged_line) > character_threshold:
                should_compact = True
                break

        if should_compact:
            # Keep only the tagged lines (all tagged lines, not just decision/confirmed)
            new_content_lines = [line for line in content_lines if line in tagged_line_set]
            new_content = "\n".join(new_content_lines)
            compacted_entries.append(LedgerEntry(
                role=entry.role,
                content=new_content,
                timestamp=entry.timestamp,
                metadata=entry.metadata,
            ))
        else:
            # Preserve the full entry body
            compacted_entries.append(entry)

    # Write back the compacted entries
    new_lines: List[str] = []
    for entry in compacted_entries:
        new_lines.append(json.dumps(entry.to_dict()))

    new_text = "\n".join(new_lines) + "\n" if new_lines else ""
    ledger_path.write_text(new_text, encoding="utf-8")

    chars_saved = original_size - len(new_text)
    result = max(chars_saved, 0)
    assert result >= 0, "Compaction must report non-negative bytes saved"
    return result


def write_hint_entry(
    ledger_path: Path,
    hint_content: str,
    gate_id: str,
    unit_number: Optional[int],
    stage: str,
    decision: str,
) -> None:
    """Create a system-level [HINT] entry with full gate metadata and append to ledger.

    The entry includes gate_id, unit_number, stage, and decision.
    """
    _validate_jsonl_extension(ledger_path)
    content = f"[HINT] {hint_content}"
    metadata: Dict[str, Any] = {
        "gate_id": gate_id,
        "unit_number": unit_number,
        "stage": stage,
        "decision": decision,
    }
    entry = LedgerEntry(
        role="system",
        content=content,
        metadata=metadata,
    )
    append_entry(ledger_path, entry)
