# Auto-generated stub for unit 4
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json
import re


class LedgerEntry:
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]]

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp if timestamp is not None else datetime.utcnow().isoformat()
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


def append_entry(ledger_path: Path, entry: LedgerEntry) -> None:
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    # Create parent directories if needed
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def read_ledger(ledger_path: Path) -> List[LedgerEntry]:
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    if not ledger_path.exists():
        return []
    content = ledger_path.read_text(encoding="utf-8")
    if not content.strip():
        return []
    entries: List[LedgerEntry] = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            raise json.JSONDecodeError(
                f"Malformed JSONL entry at line {line_num}", line, 0
            )
        entries.append(LedgerEntry.from_dict(data))
    return entries


def clear_ledger(ledger_path: Path) -> None:
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.truncate(0)


def rename_ledger(ledger_path: Path, new_name: str) -> Path:
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    new_path = ledger_path.parent / new_name
    ledger_path.rename(new_path)
    return new_path


def get_ledger_size_chars(ledger_path: Path) -> int:
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    if not ledger_path.exists():
        return 0
    return len(ledger_path.read_text(encoding="utf-8"))


def check_ledger_capacity(
    ledger_path: Path, max_chars: int
) -> Tuple[float, Optional[str]]:
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    current_size = get_ledger_size_chars(ledger_path)
    if max_chars <= 0:
        fraction = 1.0
    else:
        fraction = current_size / max_chars

    warning: Optional[str] = None
    if fraction >= 0.9:
        warning = f"Ledger at {fraction:.0%} capacity ({current_size}/{max_chars} chars). Compaction or clearing required."
    elif fraction >= 0.8:
        warning = f"Ledger at {fraction:.0%} capacity ({current_size}/{max_chars} chars). Consider compaction."

    return (fraction, warning)


def extract_tagged_lines(content: str) -> List[Tuple[str, str]]:
    """Parses content for [QUESTION], [DECISION], and [CONFIRMED] markers.
    Returns a list of (marker, full_line) tuples."""
    results: List[Tuple[str, str]] = []
    tag_pattern = re.compile(r"\[(QUESTION|DECISION|CONFIRMED)\]")
    for line in content.splitlines():
        match = tag_pattern.search(line)
        if match:
            marker = f"[{match.group(1)}]"
            results.append((marker, line))
    return results


def compact_ledger(ledger_path: Path, character_threshold: int = 200) -> int:
    """Implements the compaction algorithm from spec Section 3.3.

    Identifies sequences where agent bodies led to a [DECISION] or [CONFIRMED]
    closing. For tagged lines above character_threshold characters, the body is
    deleted (the tagged line is presumed self-contained). For tagged lines at or
    below the threshold, the body is preserved. [HINT] entries are always
    preserved verbatim. Returns the number of characters saved.
    """
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger file not found: {ledger_path}")

    entries = read_ledger(ledger_path)
    if not entries:
        return 0

    original_size = get_ledger_size_chars(ledger_path)

    hint_pattern = re.compile(r"\[HINT\]")

    compacted_entries: List[LedgerEntry] = []

    i = 0
    while i < len(entries):
        entry = entries[i]

        # [HINT] entries are always preserved verbatim
        if entry.role == "system" and hint_pattern.search(entry.content):
            compacted_entries.append(entry)
            i += 1
            continue

        # Check if this entry contains a [DECISION] or [CONFIRMED] tag
        tagged_lines = extract_tagged_lines(entry.content)
        has_closing_tag = any(
            marker in ("[DECISION]", "[CONFIRMED]") for marker, _ in tagged_lines
        )

        if has_closing_tag:
            closing_tagged = [
                (marker, line)
                for marker, line in tagged_lines
                if marker in ("[DECISION]", "[CONFIRMED]")
            ]

            # Calculate body length (non-tagged lines)
            content_lines = entry.content.splitlines()
            body_lines = [l for l in content_lines if not extract_tagged_lines(l)]
            body_text = "\n".join(body_lines)

            if len(body_text) > character_threshold:
                # Remove preceding consecutive agent body entries
                while (
                    compacted_entries
                    and compacted_entries[-1].role == "agent"
                    and not hint_pattern.search(compacted_entries[-1].content)
                    and not any(
                        m in ("[DECISION]", "[CONFIRMED]")
                        for m, _ in extract_tagged_lines(compacted_entries[-1].content)
                    )
                ):
                    compacted_entries.pop()

                # Compact body within this entry: keep only tagged lines
                kept_lines = [l for l in content_lines if extract_tagged_lines(l)]
                new_content = "\n".join(kept_lines)
                entry = LedgerEntry(
                    role=entry.role,
                    content=new_content,
                    timestamp=entry.timestamp,
                    metadata=entry.metadata,
                )

            compacted_entries.append(entry)
        else:
            compacted_entries.append(entry)

        i += 1

    # Write compacted entries back
    with open(ledger_path, "w", encoding="utf-8") as f:
        for entry in compacted_entries:
            f.write(json.dumps(entry.to_dict()) + "\n")

    new_size = get_ledger_size_chars(ledger_path)
    chars_saved = original_size - new_size
    assert chars_saved >= 0, "Compaction must report non-negative bytes saved"
    return chars_saved


def write_hint_entry(
    ledger_path: Path,
    hint_content: str,
    gate_id: str,
    unit_number: Optional[int],
    stage: str,
    decision: str,
) -> None:
    """Creates a system-level [HINT] entry with full gate metadata and appends it."""
    assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"
    metadata: Dict[str, Any] = {
        "gate_id": gate_id,
        "unit_number": unit_number,
        "stage": stage,
        "decision": decision,
    }
    content = f"[HINT] {hint_content}"
    entry = LedgerEntry(
        role="system",
        content=content,
        metadata=metadata,
    )
    append_entry(ledger_path, entry)
