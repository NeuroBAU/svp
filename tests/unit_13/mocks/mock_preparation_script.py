# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any, List
from pathlib import Path

def prepare_agent_task(project_root: Path, agent_type: str, unit_number: Optional[int]=None, ladder_position: Optional[str]=None, hint_content: Optional[str]=None, gate_id: Optional[str]=None, extra_context: Optional[Dict[str, str]]=None) -> Path:
    return MagicMock()

def prepare_gate_prompt(project_root: Path, gate_id: str, unit_number: Optional[int]=None, extra_context: Optional[Dict[str, str]]=None) -> Path:
    return MagicMock()

def load_stakeholder_spec(project_root: Path) -> str:
    return ''

def load_blueprint(project_root: Path) -> str:
    return ''

def load_reference_summaries(project_root: Path) -> str:
    return ''

def load_project_context(project_root: Path) -> str:
    return ''

def load_ledger_content(project_root: Path, ledger_name: str) -> str:
    return ''

def build_task_prompt_content(agent_type: str, sections: Dict[str, str], hint_block: Optional[str]=None) -> str:
    return ''

def main() -> None:
    return None
