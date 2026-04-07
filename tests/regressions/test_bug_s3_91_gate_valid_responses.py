"""Regression tests for Bug S3-91: All human_gate action blocks must include valid_responses.

Every human_gate action block must include a valid_responses field whose value
matches GATE_VOCABULARY[gate_id] exactly. This ensures the orchestrator knows
the exact strings to write to .svp/last_status.txt without guessing.
"""

import ast
from pathlib import Path

import pytest

import routing
from routing import (
    GATE_VOCABULARY,
    _make_action_block,
    route,
    save_state,
)
from pipeline_state import PipelineState
from state_transitions import enter_debug_session


ROUTING_PY = Path(routing.__file__).resolve()


def _make_state(**overrides):
    defaults = {
        "stage": "0",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "oracle_modification_count": 0,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestMakeActionBlockIncludesValidResponses:
    """_make_action_block includes valid_responses for every GATE_VOCABULARY entry."""

    @pytest.mark.parametrize("gate_id", sorted(GATE_VOCABULARY.keys()))
    def test_human_gate_has_valid_responses(self, gate_id):
        """Every gate_id in GATE_VOCABULARY produces valid_responses in the action block."""
        block = _make_action_block(
            action_type="human_gate",
            gate_id=gate_id,
            reminder="test",
        )
        assert "valid_responses" in block, (
            f"human_gate with gate_id={gate_id!r} missing valid_responses"
        )
        assert isinstance(block["valid_responses"], list)
        assert len(block["valid_responses"]) > 0
        assert block["valid_responses"] == GATE_VOCABULARY[gate_id]


class TestNonGateBlocksLackValidResponses:
    """Non-human_gate action types must NOT include valid_responses."""

    def test_invoke_agent_no_valid_responses(self):
        block = _make_action_block(
            action_type="invoke_agent",
            agent_type="test_agent",
            reminder="test",
        )
        assert "valid_responses" not in block

    def test_run_command_no_valid_responses(self):
        block = _make_action_block(
            action_type="run_command",
            command="echo hello",
            reminder="test",
        )
        assert "valid_responses" not in block

    def test_pipeline_complete_no_valid_responses(self):
        block = _make_action_block(
            action_type="pipeline_complete",
            reminder="done",
        )
        assert "valid_responses" not in block

    def test_invoke_agent_with_gate_id_no_valid_responses(self):
        """Even if gate_id is passed, non-human_gate types must not get valid_responses."""
        block = _make_action_block(
            action_type="invoke_agent",
            gate_id="gate_0_1_hook_activation",
            reminder="test",
        )
        assert "valid_responses" not in block


class TestExhaustiveGateVocabularyCoverage:
    """Every gate_id literal in _make_action_block(action_type='human_gate', ...) calls
    must exist in GATE_VOCABULARY (AST-based structural test)."""

    def test_all_human_gate_call_site_ids_in_vocabulary(self):
        """AST scan: every gate_id string literal in human_gate calls exists in GATE_VOCABULARY."""
        source = ROUTING_PY.read_text()
        tree = ast.parse(source)
        missing = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Match _make_action_block(...) calls
            if isinstance(func, ast.Name) and func.id == "_make_action_block":
                pass
            elif isinstance(func, ast.Attribute) and func.attr == "_make_action_block":
                pass
            else:
                continue
            # Extract keyword arguments
            kw = {k.arg: k.value for k in node.keywords}
            # Check if action_type is "human_gate"
            at = kw.get("action_type")
            if not (isinstance(at, ast.Constant) and at.value == "human_gate"):
                continue
            # Extract gate_id
            gid = kw.get("gate_id")
            if isinstance(gid, ast.Constant) and isinstance(gid.value, str):
                if gid.value not in GATE_VOCABULARY:
                    missing.append(gid.value)
        assert not missing, (
            f"human_gate call sites with gate_id not in GATE_VOCABULARY: {missing}"
        )


class TestLiveRouteGatesIncludeValidResponses:
    """Representative gates reachable via route() include valid_responses in output."""

    def test_gate_0_1_hook_activation(self, tmp_path):
        state = _make_state(stage="0", sub_stage="hook_activation")
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("")
        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_0_1_hook_activation"
        assert "valid_responses" in action, "gate_0_1 missing valid_responses"
        assert action["valid_responses"] == GATE_VOCABULARY["gate_0_1_hook_activation"]

    def test_gate_6_0_debug_permission(self, tmp_path):
        state = _make_state(stage="5", sub_stage="pass_transition")
        state = enter_debug_session(state, 1)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("")
        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_6_0_debug_permission"
        assert "valid_responses" in action, "gate_6_0 missing valid_responses"
        assert action["valid_responses"] == GATE_VOCABULARY["gate_6_0_debug_permission"]

    def test_gate_7_a_trajectory_review(self, tmp_path):
        """The gate that originally triggered this bug."""
        state = _make_state(
            oracle_session_active=True,
            oracle_test_project="examples/game-of-life/",
            oracle_phase="gate_a",
            oracle_run_count=1,
        )
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "last_status.txt").write_text("")
        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_7_a_trajectory_review"
        assert "valid_responses" in action, "gate_7_a missing valid_responses"
        assert action["valid_responses"] == GATE_VOCABULARY["gate_7_a_trajectory_review"]
