# Unit 4: Ledger Manager
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class LedgerEntry:
    """A single entry in a conversation ledger."""

    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]]

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.role = role
        self.content = content
        self.timestamp = (
            timestamp if timestamp is not None else datetime.utcnow().isoformat()
        )
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
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
        """Deserialize from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata"),
        )


def append_entry(ledger_path: Path, entry: LedgerEntry) -> None:
    """Append entry to ledger. Creates file if needed."""
    entries: List[Dict[str, Any]] = []
    if ledger_path.exists():
        text = ledger_path.read_text(encoding="utf-8")
        if text.strip():
            entries = json.loads(text)
    entries.append(entry.to_dict())
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_ledger(
    ledger_path: Path,
) -> List[LedgerEntry]:
    """Read all entries. Empty list if missing/empty."""
    if not ledger_path.exists():
        return []
    text = ledger_path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    raw = json.loads(text)
    return [LedgerEntry.from_dict(d) for d in raw]


def clear_ledger(ledger_path: Path) -> None:
    """Clear ledger contents. No error if missing."""
    if ledger_path.exists():
        ledger_path.write_text(
            json.dumps([], indent=2),
            encoding="utf-8",
        )


def rename_ledger(ledger_path: Path, new_name: str) -> Path:
    """Rename ledger file, return new path."""
    new_path = ledger_path.parent / new_name
    ledger_path.rename(new_path)
    return new_path


def get_ledger_size_chars(ledger_path: Path) -> int:
    """Return character count of ledger file."""
    if not ledger_path.exists():
        return 0
    return len(ledger_path.read_text(encoding="utf-8"))


def check_ledger_capacity(
    ledger_path: Path, max_chars: int
) -> Tuple[float, Optional[str]]:
    """Check capacity ratio and return warning."""
    size = get_ledger_size_chars(ledger_path)
    if max_chars <= 0:
        ratio = 1.0
    else:
        ratio = size / max_chars
    warning: Optional[str] = None
    if ratio >= 0.9:
        warning = "Ledger at 90%+ capacity. Compaction required."
    elif ratio >= 0.8:
        warning = "Ledger at 80%+ capacity. Warning."
    return (ratio, warning)


# Pattern for tagged lines: [TAG] body
_TAG_PATTERN = re.compile(r"^\[([A-Z][A-Z0-9_]*)\]\s*(.*)", re.MULTILINE)


def extract_tagged_lines(
    content: str,
) -> List[Tuple[str, str]]:
    """Extract (tag, body) tuples from content."""
    if not content:
        return []
    results: List[Tuple[str, str]] = []
    for line in content.splitlines():
        m = _TAG_PATTERN.match(line.strip())
        if m:
            results.append((m.group(1), m.group(2)))
    return results


def compact_ledger(
    ledger_path: Path,
    character_threshold: int = 200,
) -> int:
    """Compact ledger using the compaction algorithm.

    For tagged lines above character_threshold, body is
    deleted. At or below, body is preserved. [HINT]
    entries always preserved verbatim.

    Returns count of compacted entries.
    """
    entries = read_ledger(ledger_path)
    if not entries:
        return 0
    compacted_count = 0
    new_entries: List[LedgerEntry] = []
    for entry in entries:
        content = entry.content
        tagged = extract_tagged_lines(content)
        if not tagged:
            # No tagged lines -- keep as is
            new_entries.append(entry)
            continue
        # Check if this is a HINT entry
        is_hint = any(tag == "HINT" for tag, _ in tagged)
        if is_hint:
            # Always preserve verbatim
            new_entries.append(entry)
            continue
        # Apply compaction to tagged content
        if len(content) > character_threshold:
            # Body deleted, keep only tag
            new_lines: List[str] = []
            for tag, _body in tagged:
                new_lines.append(f"[{tag}]")
            entry_copy = LedgerEntry(
                role=entry.role,
                content="\n".join(new_lines),
                timestamp=entry.timestamp,
                metadata=entry.metadata,
            )
            new_entries.append(entry_copy)
            compacted_count += 1
        else:
            # At or below threshold -- preserve
            new_entries.append(entry)
    # Write back
    raw = [e.to_dict() for e in new_entries]
    ledger_path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return compacted_count


def write_hint_entry(
    ledger_path: Path,
    hint_content: str,
    gate_id: str,
    unit_number: Optional[int],
    stage: str,
    decision: str,
) -> None:
    """Write a [HINT] entry to the ledger."""
    unit_str = str(unit_number) if unit_number is not None else "global"
    content = (
        f"[HINT] {hint_content} "
        f"(gate={gate_id}, unit={unit_str}, "
        f"stage={stage}, decision={decision})"
    )
    entry = LedgerEntry(
        role="system",
        content=content,
        metadata={
            "gate_id": gate_id,
            "unit_number": unit_str,
            "stage": stage,
            "decision": decision,
        },
    )
    append_entry(ledger_path, entry)
