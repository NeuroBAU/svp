# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json

class LedgerEntry:
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]]

    def __init__(self, role: str, content: str, timestamp: Optional[str]=None, metadata: Optional[Dict[str, Any]]=None) -> None:
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LedgerEntry':
        return MagicMock()

def append_entry(ledger_path: Path, entry: LedgerEntry) -> None:
    return None

def read_ledger(ledger_path: Path) -> List[LedgerEntry]:
    return []

def clear_ledger(ledger_path: Path) -> None:
    return None

def rename_ledger(ledger_path: Path, new_name: str) -> Path:
    return MagicMock()

def get_ledger_size_chars(ledger_path: Path) -> int:
    return 0

def check_ledger_capacity(ledger_path: Path, max_chars: int) -> Tuple[float, Optional[str]]:
    return ()

def compact_ledger(ledger_path: Path, character_threshold: int=200) -> int:
    return 0

def write_hint_entry(ledger_path: Path, hint_content: str, gate_id: str, unit_number: Optional[int], stage: str, decision: str) -> None:
    return None

def extract_tagged_lines(content: str) -> List[Tuple[str, str]]:
    return []
