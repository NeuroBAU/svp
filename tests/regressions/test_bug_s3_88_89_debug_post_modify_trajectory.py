"""Regression tests for Bugs S3-88 and S3-89.

S3-88: Debug loop run_command blocks (stage3_reentry, lessons_learned, debug_commit)
were missing post fields. dispatch_command_status was never called for these phases,
so the debug loop state never advanced — dead-end states.

S3-89: GATE_VOCABULARY always includes MODIFY TRAJECTORY for gate_7_a even when
oracle_modification_count >= 3. Section 35.4 requires only APPROVE TRAJECTORY and
ABORT are offered after 3 modifications.
"""

import pytest

from routing import (
    GATE_VOCABULARY,
    dispatch_command_status,
    dispatch_gate_response,
    route,
    save_state,
    _route_debug,
)
from pipeline_state import PipelineState
from state_transitions import enter_debug_session, authorize_debug_session


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


def _make_debug_state(phase, tmp_path, **overrides):
    """Create a state with an active authorized debug session in a given phase."""
    state = _make_state(stage="5", sub_stage="pass_transition", **overrides)
    state = enter_debug_session(state, 1)
    state = authorize_debug_session(state)
    # Set the debug phase directly
    state.debug_session["phase"] = phase
    save_state(tmp_path, state)
    (tmp_path / ".svp").mkdir(exist_ok=True)
    (tmp_path / ".svp" / "last_status.txt").write_text("")
    return state


# ============================================================
# S3-88: Debug run_command blocks must have post fields
# ============================================================

class TestDebugRunCommandPostFields:
    """Every debug loop run_command block must include a post field (Bug S3-88)."""

    def test_stage3_reentry_has_post_field(self, tmp_path):
        """stage3_reentry run_command block must include a post field."""
        state = _make_debug_state("stage3_reentry", tmp_path)
        action = _route_debug(state, tmp_path, "", 3)
        assert action["action_type"] == "run_command"
        assert action["command"] == "stage3_reentry"
        assert "post" in action, "stage3_reentry action block missing 'post' field"
        assert "update_state.py" in action["post"]
        assert "stage3_reentry" in action["post"]

    def test_lessons_learned_has_post_field(self, tmp_path):
        """lessons_learned run_command block must include a post field."""
        state = _make_debug_state("lessons_learned", tmp_path)
        action = _route_debug(state, tmp_path, "", 3)
        assert action["action_type"] == "run_command"
        assert action["command"] == "lessons_learned"
        assert "post" in action, "lessons_learned action block missing 'post' field"
        assert "update_state.py" in action["post"]
        assert "lessons_learned" in action["post"]

    def test_debug_commit_has_post_field(self, tmp_path):
        """debug_commit run_command block must include a post field."""
        state = _make_debug_state("commit", tmp_path)
        state.debug_session["phase"] = "commit"
        save_state(tmp_path, state)
        # Force the COMMIT APPROVED branch
        action = _route_debug(state, tmp_path, "COMMIT APPROVED", 3)
        assert action["action_type"] == "run_command"
        assert action["command"] == "debug_commit"
        assert "post" in action, "debug_commit action block missing 'post' field"
        assert "update_state.py" in action["post"]
        assert "debug_commit" in action["post"]

    def test_stage3_reentry_dispatch_advances_state(self, tmp_path):
        """dispatch_command_status for stage3_reentry advances pipeline state."""
        state = _make_debug_state("stage3_reentry", tmp_path)
        new = dispatch_command_status(
            state, "stage3_reentry", "COMMAND_SUCCEEDED",
            project_root=tmp_path,
        )
        # After stage3_reentry, sub_stage should be stub_generation
        assert new.sub_stage == "stub_generation", (
            f"Expected sub_stage='stub_generation' after stage3_reentry dispatch, "
            f"got '{new.sub_stage}'"
        )

    def test_lessons_learned_dispatch_advances_debug_phase(self, tmp_path):
        """dispatch_command_status for lessons_learned advances debug phase to commit."""
        state = _make_debug_state("lessons_learned", tmp_path)
        new = dispatch_command_status(
            state, "lessons_learned", "COMMAND_SUCCEEDED",
            project_root=tmp_path,
        )
        # After lessons_learned, debug phase should advance
        assert new.debug_session["phase"] == "commit", (
            f"Expected debug phase='commit' after lessons_learned dispatch, "
            f"got '{new.debug_session.get('phase')}'"
        )

    def test_debug_commit_dispatch_completes_session(self, tmp_path):
        """dispatch_command_status for debug_commit completes the debug session."""
        state = _make_debug_state("commit", tmp_path)
        new = dispatch_command_status(
            state, "debug_commit", "COMMAND_SUCCEEDED",
            project_root=tmp_path,
        )
        # After debug_commit, debug session should be cleared
        assert new.debug_session is None, (
            f"Expected debug_session=None after debug_commit dispatch, "
            f"got '{new.debug_session}'"
        )

    def test_full_round_trip_stage3_reentry(self, tmp_path):
        """Full round-trip: stage3_reentry route → POST dispatch → state advances."""
        # Step 1: Create state in stage3_reentry phase
        state = _make_debug_state("stage3_reentry", tmp_path)

        # Step 2: Route produces action with post field
        action = _route_debug(state, tmp_path, "", 3)
        assert action["action_type"] == "run_command"
        assert "post" in action

        # Step 3: POST dispatch advances state
        new = dispatch_command_status(
            state, "stage3_reentry", "COMMAND_SUCCEEDED",
            project_root=tmp_path,
        )
        assert new.sub_stage == "stub_generation"


# ============================================================
# S3-89: MODIFY TRAJECTORY must be restricted at count >= 3
# ============================================================

class TestModifyTrajectoryRestriction:
    """MODIFY TRAJECTORY must be rejected when oracle_modification_count >= 3 (Bug S3-89)."""

    def _make_oracle_state(self, phase="gate_a", mod_count=0):
        return _make_state(
            stage="5",
            sub_stage=None,
            oracle_session_active=True,
            oracle_phase=phase,
            oracle_test_project="docs/",
            oracle_run_count=1,
            oracle_modification_count=mod_count,
            oracle_nested_session_path=None,
        )

    def test_modify_trajectory_accepted_when_count_lt_3(self, tmp_path):
        """MODIFY TRAJECTORY is accepted when oracle_modification_count < 3."""
        state = self._make_oracle_state(phase="gate_a", mod_count=0)
        save_state(tmp_path, state)
        new = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY",
            project_root=tmp_path,
        )
        assert new.oracle_phase == "dry_run"
        assert new.oracle_modification_count == 1

    def test_modify_trajectory_accepted_at_count_2(self, tmp_path):
        """MODIFY TRAJECTORY is accepted when count is exactly 2 (last allowed)."""
        state = self._make_oracle_state(phase="gate_a", mod_count=2)
        save_state(tmp_path, state)
        new = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY",
            project_root=tmp_path,
        )
        assert new.oracle_phase == "dry_run"
        assert new.oracle_modification_count == 3

    def test_modify_trajectory_rejected_at_count_3(self, tmp_path):
        """MODIFY TRAJECTORY is rejected when oracle_modification_count == 3."""
        state = self._make_oracle_state(phase="gate_a", mod_count=3)
        save_state(tmp_path, state)
        with pytest.raises(ValueError, match="MODIFY TRAJECTORY not available"):
            dispatch_gate_response(
                state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY",
                project_root=tmp_path,
            )

    def test_modify_trajectory_rejected_at_count_4(self, tmp_path):
        """MODIFY TRAJECTORY is rejected when oracle_modification_count > 3."""
        state = self._make_oracle_state(phase="gate_a", mod_count=4)
        save_state(tmp_path, state)
        with pytest.raises(ValueError, match="MODIFY TRAJECTORY not available"):
            dispatch_gate_response(
                state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY",
                project_root=tmp_path,
            )

    def test_approve_trajectory_always_works(self, tmp_path):
        """APPROVE TRAJECTORY works regardless of modification count."""
        state = self._make_oracle_state(phase="gate_a", mod_count=5)
        save_state(tmp_path, state)
        new = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "APPROVE TRAJECTORY",
            project_root=tmp_path,
        )
        assert new.oracle_phase == "green_run"

    def test_gate_7a_gate_vocabulary_includes_modify_by_default(self):
        """GATE_VOCABULARY includes MODIFY TRAJECTORY for general use."""
        assert "MODIFY TRAJECTORY" in GATE_VOCABULARY["gate_7_a_trajectory_review"]


class TestModifyTrajectoryGateOptions:
    """prepare_gate_prompt must exclude MODIFY TRAJECTORY when count >= 3 (Bug S3-89)."""

    def test_prepare_gate_prompt_filters_modify_at_count_3(self, tmp_path):
        """prepare_gate_prompt excludes MODIFY TRAJECTORY when count >= 3."""
        # Import here to avoid top-level import issues
        try:
            import sys
            scripts_dir = str(
                __import__("pathlib").Path(__file__).resolve().parent.parent.parent
                / "svp" / "scripts"
            )
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from prepare_task import prepare_gate_prompt
        except ImportError:
            pytest.skip("prepare_task not importable in this environment")

        # Create state with modification count at limit
        state = _make_state(
            stage="5",
            sub_stage=None,
            oracle_session_active=True,
            oracle_phase="gate_a",
            oracle_test_project="docs/",
            oracle_modification_count=3,
        )
        save_state(tmp_path, state)

        # Generate gate prompt
        content = prepare_gate_prompt(tmp_path, "gate_7_a_trajectory_review")

        # MODIFY TRAJECTORY should NOT appear as a response option
        # (it may appear in explanatory text, so we check the options section)
        assert "APPROVE TRAJECTORY" in content
        assert "ABORT" in content
        # The option should be removed from response options
        lines = content.splitlines()
        option_lines = [l for l in lines if l.startswith("- **")]
        option_texts = [l.strip("- **").rstrip("**") for l in option_lines]
        assert "MODIFY TRAJECTORY" not in option_texts, (
            "MODIFY TRAJECTORY should be excluded from gate options when count >= 3"
        )

    def test_prepare_gate_prompt_keeps_modify_at_count_2(self, tmp_path):
        """prepare_gate_prompt keeps MODIFY TRAJECTORY when count < 3."""
        try:
            import sys
            scripts_dir = str(
                __import__("pathlib").Path(__file__).resolve().parent.parent.parent
                / "svp" / "scripts"
            )
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from prepare_task import prepare_gate_prompt
        except ImportError:
            pytest.skip("prepare_task not importable in this environment")

        state = _make_state(
            stage="5",
            sub_stage=None,
            oracle_session_active=True,
            oracle_phase="gate_a",
            oracle_test_project="docs/",
            oracle_modification_count=2,
        )
        save_state(tmp_path, state)

        content = prepare_gate_prompt(tmp_path, "gate_7_a_trajectory_review")

        assert "MODIFY TRAJECTORY" in content
