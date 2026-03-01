# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any
from pathlib import Path
DEFAULT_CONFIG: Dict[str, Any] = {'iteration_limit': 3, 'models': {'test_agent': 'claude-opus-4-6', 'implementation_agent': 'claude-opus-4-6', 'help_agent': 'claude-sonnet-4-6', 'default': 'claude-opus-4-6'}, 'context_budget_override': None, 'context_budget_threshold': 65, 'compaction_character_threshold': 200, 'auto_save': True, 'skip_permissions': True}

def load_config(project_root: Path) -> Dict[str, Any]:
    return {}

def validate_config(config: Dict[str, Any]) -> list[str]:
    return MagicMock()

def get_model_for_agent(config: Dict[str, Any], agent_role: str) -> str:
    return ''

def get_effective_context_budget(config: Dict[str, Any]) -> int:
    return 0

def write_default_config(project_root: Path) -> Path:
    return MagicMock()
