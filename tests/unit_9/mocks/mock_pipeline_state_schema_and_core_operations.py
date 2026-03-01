# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
STAGES: List[str] = ['0', '1', '2', 'pre_stage_3', '3', '4', '5']
SUB_STAGES_STAGE_0: List[str] = ['hook_activation', 'project_context']
FIX_LADDER_POSITIONS: List[Optional[str]] = [None, 'fresh_test', 'hint_test', 'fresh_impl', 'diagnostic', 'diagnostic_impl']

class DebugSession:
    """Debug session state for post-delivery bug investigation."""
    bug_id: int
    description: str
    classification: Optional[str]
    affected_units: List[int]
    regression_test_path: Optional[str]
    phase: str
    authorized: bool
    created_at: str

    def __init__(self, **kwargs: Any) -> None:
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DebugSession':
        return MagicMock()

class PipelineState:
    """Complete pipeline state. This is the schema contract."""
    stage: str
    sub_stage: Optional[str]
    current_unit: Optional[int]
    total_units: Optional[int]
    fix_ladder_position: Optional[str]
    red_run_retries: int
    alignment_iteration: int
    verified_units: List[Dict[str, Any]]
    pass_history: List[Dict[str, Any]]
    log_references: Dict[str, str]
    project_name: Optional[str]
    last_action: Optional[str]
    debug_session: Optional[DebugSession]
    debug_history: List[Dict[str, Any]]
    created_at: str
    updated_at: str

    def __init__(self, **kwargs: Any) -> None:
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineState':
        return MagicMock()

def create_initial_state(project_name: str) -> PipelineState:
    return MagicMock()

def load_state(project_root: Path) -> PipelineState:
    return MagicMock()

def save_state(state: PipelineState, project_root: Path) -> None:
    return None

def validate_state(state: PipelineState) -> list[str]:
    return MagicMock()

def recover_state_from_markers(project_root: Path) -> Optional[PipelineState]:
    return None

def get_stage_display(state: PipelineState) -> str:
    return ''
