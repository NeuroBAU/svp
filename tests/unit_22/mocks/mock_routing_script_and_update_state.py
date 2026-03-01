# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any, List
from pathlib import Path
from svp.scripts.pipeline_state import PipelineState
from state_transitions import TransitionError
GATE_VOCABULARY: Dict[str, List[str]] = {'gate_0_1_hook_activation': ['HOOKS ACTIVATED', 'HOOKS FAILED'], 'gate_0_2_context_approval': ['CONTEXT APPROVED', 'CONTEXT REJECTED', 'CONTEXT NOT READY'], 'gate_1_1_spec_draft': ['APPROVE', 'REVISE', 'FRESH REVIEW'], 'gate_1_2_spec_post_review': ['APPROVE', 'REVISE', 'FRESH REVIEW'], 'gate_2_1_blueprint_approval': ['APPROVE', 'REVISE', 'FRESH REVIEW'], 'gate_2_2_blueprint_post_review': ['APPROVE', 'REVISE', 'FRESH REVIEW'], 'gate_2_3_alignment_exhausted': ['REVISE SPEC', 'RESTART SPEC', 'RETRY BLUEPRINT'], 'gate_3_1_test_validation': ['TEST CORRECT', 'TEST WRONG'], 'gate_3_2_diagnostic_decision': ['FIX IMPLEMENTATION', 'FIX BLUEPRINT', 'FIX SPEC'], 'gate_4_1_integration_failure': ['ASSEMBLY FIX', 'FIX BLUEPRINT', 'FIX SPEC'], 'gate_4_2_assembly_exhausted': ['FIX BLUEPRINT', 'FIX SPEC'], 'gate_5_1_repo_test': ['TESTS PASSED', 'TESTS FAILED'], 'gate_5_2_assembly_exhausted': ['RETRY ASSEMBLY', 'FIX BLUEPRINT', 'FIX SPEC'], 'gate_6_0_debug_permission': ['AUTHORIZE DEBUG', 'ABANDON DEBUG'], 'gate_6_1_regression_test': ['TEST CORRECT', 'TEST WRONG'], 'gate_6_2_debug_classification': ['FIX UNIT', 'FIX BLUEPRINT', 'FIX SPEC'], 'gate_6_3_repair_exhausted': ['RETRY REPAIR', 'RECLASSIFY BUG', 'ABANDON DEBUG'], 'gate_6_4_non_reproducible': ['RETRY TRIAGE', 'ABANDON DEBUG']}
AGENT_STATUS_LINES: Dict[str, List[str]] = {'setup_agent': ['PROJECT_CONTEXT_COMPLETE', 'PROJECT_CONTEXT_REJECTED'], 'stakeholder_dialog': ['SPEC_DRAFT_COMPLETE', 'SPEC_REVISION_COMPLETE'], 'stakeholder_reviewer': ['REVIEW_COMPLETE'], 'blueprint_author': ['BLUEPRINT_DRAFT_COMPLETE'], 'blueprint_checker': ['ALIGNMENT_CONFIRMED', 'ALIGNMENT_FAILED: spec', 'ALIGNMENT_FAILED: blueprint'], 'blueprint_reviewer': ['REVIEW_COMPLETE'], 'test_agent': ['TEST_GENERATION_COMPLETE'], 'implementation_agent': ['IMPLEMENTATION_COMPLETE'], 'coverage_review': ['COVERAGE_COMPLETE: no gaps', 'COVERAGE_COMPLETE: tests added'], 'diagnostic_agent': ['DIAGNOSIS_COMPLETE: implementation', 'DIAGNOSIS_COMPLETE: blueprint', 'DIAGNOSIS_COMPLETE: spec'], 'integration_test_author': ['INTEGRATION_TESTS_COMPLETE'], 'git_repo_agent': ['REPO_ASSEMBLY_COMPLETE'], 'help_agent': ['HELP_SESSION_COMPLETE: no hint', 'HELP_SESSION_COMPLETE: hint forwarded'], 'hint_agent': ['HINT_ANALYSIS_COMPLETE'], 'redo_agent': ['REDO_CLASSIFIED: spec', 'REDO_CLASSIFIED: blueprint', 'REDO_CLASSIFIED: gate'], 'bug_triage': ['TRIAGE_COMPLETE: build_env', 'TRIAGE_COMPLETE: single_unit', 'TRIAGE_COMPLETE: cross_unit', 'TRIAGE_NEEDS_REFINEMENT', 'TRIAGE_NON_REPRODUCIBLE'], 'repair_agent': ['REPAIR_COMPLETE', 'REPAIR_FAILED', 'REPAIR_RECLASSIFY'], 'reference_indexing': ['INDEXING_COMPLETE']}
CROSS_AGENT_STATUS: str = 'HINT_BLUEPRINT_CONFLICT'
COMMAND_STATUS_PATTERNS: List[str] = ['TESTS_PASSED', 'TESTS_FAILED', 'TESTS_ERROR', 'COMMAND_SUCCEEDED', 'COMMAND_FAILED']

def route(state: PipelineState, project_root: Path) -> Dict[str, Any]:
    return {}

def format_action_block(action: Dict[str, Any]) -> str:
    return ''

def derive_env_name_from_state(state: PipelineState) -> str:
    return ''

def dispatch_status(state: PipelineState, status_line: str, gate_id: Optional[str], unit: Optional[int], phase: str, project_root: Path) -> PipelineState:
    return MagicMock()

def dispatch_gate_response(state: PipelineState, gate_id: str, response: str, project_root: Path) -> PipelineState:
    return MagicMock()

def dispatch_agent_status(state: PipelineState, agent_type: str, status_line: str, unit: Optional[int], phase: str, project_root: Path) -> PipelineState:
    return MagicMock()

def dispatch_command_status(state: PipelineState, status_line: str, unit: Optional[int], phase: str, project_root: Path) -> PipelineState:
    return MagicMock()

def run_pytest(test_path: Path, env_name: str, project_root: Path) -> str:
    return ''

def routing_main() -> None:
    return None

def update_state_main() -> None:
    return None

def run_tests_main() -> None:
    return None
