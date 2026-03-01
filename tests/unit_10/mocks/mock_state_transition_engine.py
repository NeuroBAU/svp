# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from svp.scripts.pipeline_state import PipelineState, DebugSession

class TransitionError(Exception):
    """Raised when a state transition's preconditions are not met."""
    ...

def advance_stage(state: PipelineState, project_root: Path) -> PipelineState:
    return MagicMock()

def advance_sub_stage(state: PipelineState, sub_stage: str, project_root: Path) -> PipelineState:
    return MagicMock()

def complete_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState:
    return MagicMock()

def advance_fix_ladder(state: PipelineState, new_position: str) -> PipelineState:
    return MagicMock()

def reset_fix_ladder(state: PipelineState) -> PipelineState:
    return MagicMock()

def increment_red_run_retries(state: PipelineState) -> PipelineState:
    return MagicMock()

def reset_red_run_retries(state: PipelineState) -> PipelineState:
    return MagicMock()

def increment_alignment_iteration(state: PipelineState) -> PipelineState:
    return MagicMock()

def reset_alignment_iteration(state: PipelineState) -> PipelineState:
    return MagicMock()

def record_pass_end(state: PipelineState, reason: str) -> PipelineState:
    return MagicMock()

def rollback_to_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState:
    return MagicMock()

def restart_from_stage(state: PipelineState, target_stage: str, reason: str, project_root: Path) -> PipelineState:
    return MagicMock()

def version_document(doc_path: Path, history_dir: Path, diff_summary: str, trigger_context: str) -> Tuple[Path, Path]:
    return ()

def enter_debug_session(state: PipelineState, bug_description: str) -> PipelineState:
    return MagicMock()

def authorize_debug_session(state: PipelineState) -> PipelineState:
    return MagicMock()

def complete_debug_session(state: PipelineState, fix_summary: str) -> PipelineState:
    return MagicMock()

def abandon_debug_session(state: PipelineState) -> PipelineState:
    return MagicMock()

def update_debug_phase(state: PipelineState, phase: str) -> PipelineState:
    return MagicMock()

def set_debug_classification(state: PipelineState, classification: str, affected_units: List[int]) -> PipelineState:
    return MagicMock()

def update_state_from_status(state: PipelineState, status_file: Path, unit: Optional[int], phase: str, project_root: Path) -> PipelineState:
    return MagicMock()
