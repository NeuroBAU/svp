"""Behavioral equivalence: routing is language-agnostic at equivalent stages."""
import json, tempfile
from pathlib import Path
from pipeline_state import PipelineState, save_state
from routing import route

def _route_with_language(lang, stage, sub_stage, **extra):
    defaults = dict(
        stage=stage, sub_stage=sub_stage, current_unit=None, total_units=29,
        verified_units=[], alignment_iterations=0, fix_ladder_position=None,
        red_run_retries=0, pass_history=[], debug_session=None, debug_history=[],
        redo_triggered_from=None, delivered_repo_path=None, primary_language=lang,
        component_languages=[], secondary_language=None, oracle_session_active=False,
        oracle_test_project=None, oracle_phase=None, oracle_run_count=0,
        oracle_nested_session_path=None, state_hash=None, spec_revision_count=0,
        pass_=None, pass2_nested_session_path=None, deferred_broken_units=[],
    )
    defaults.update(extra)
    state = PipelineState(**defaults)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        (root / ".svp").mkdir(exist_ok=True)
        (root / ".svp" / "last_status.txt").write_text("")
        return route(root)

class TestBehavioralEquivalence:
    def test_stage0_routing_language_agnostic(self):
        py = _route_with_language("python", "0", "hook_activation")
        r = _route_with_language("r", "0", "hook_activation")
        assert py["action_type"] == r["action_type"]

    def test_stage1_routing_language_agnostic(self):
        py = _route_with_language("python", "1", None)
        r = _route_with_language("r", "1", None)
        assert py["action_type"] == r["action_type"]

    def test_stage2_routing_language_agnostic(self):
        py = _route_with_language("python", "2", "blueprint_dialog")
        r = _route_with_language("r", "2", "blueprint_dialog")
        assert py["action_type"] == r["action_type"]

    def test_stage5_routing_language_agnostic(self):
        py = _route_with_language("python", "5", None)
        r = _route_with_language("r", "5", None)
        assert py["action_type"] == r["action_type"]
