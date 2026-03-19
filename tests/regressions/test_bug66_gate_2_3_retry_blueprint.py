"""Regression test for Bug 66: gate_2_3 RETRY BLUEPRINT no-op causing routing loop.

When the human selects RETRY BLUEPRINT at gate_2_3_alignment_exhausted,
the dispatch must:
1. Version the blueprint (call _version_blueprint)
2. Reset alignment_iteration to 0
3. Reset sub_stage to None (so routing invokes blueprint_author, not blueprint_checker)
4. Set last_action to describe the transition

Previously, the dispatch returned state unchanged, leaving sub_stage as
'alignment_check'. On the next routing cycle, route() re-invoked the
blueprint_checker instead of the blueprint_author, creating an infinite loop.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _make_state(**kwargs):
    """Create a minimal mock PipelineState."""
    defaults = {
        "stage": "2",
        "sub_stage": "alignment_check",
        "current_unit": None,
        "total_units": 5,
        "red_run_retries": 0,
        "fix_ladder_position": None,
        "debug_session": None,
        "alignment_iteration": 3,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test",
        "last_action": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
    }
    defaults.update(kwargs)
    state = SimpleNamespace(**defaults)
    state.to_dict = lambda: {k: getattr(state, k) for k in defaults}
    return state


def _write_last_status(project_root, status):
    """Write a status to .svp/last_status.txt."""
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    (svp_dir / "last_status.txt").write_text(status)


class TestBug66Gate23RetryBlueprint(unittest.TestCase):
    """Test that RETRY BLUEPRINT at gate_2_3 resets sub_stage to None."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)
        # Create required directories
        (self.project_root / ".svp").mkdir(parents=True, exist_ok=True)
        (self.project_root / "blueprint").mkdir(parents=True, exist_ok=True)
        (self.project_root / "blueprint" / "history").mkdir(parents=True, exist_ok=True)

    def test_retry_blueprint_resets_sub_stage_to_none(self):
        """RETRY BLUEPRINT must set sub_stage to None, not leave it as alignment_check."""
        from routing import dispatch_gate_response, PipelineState

        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iteration=3)

        with patch("routing._version_blueprint") as mock_version:
            result = dispatch_gate_response(
                state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
            )

        self.assertIsNone(
            result.sub_stage,
            "RETRY BLUEPRINT must reset sub_stage to None (was left as 'alignment_check' in Bug 66)"
        )

    def test_retry_blueprint_resets_alignment_iteration(self):
        """RETRY BLUEPRINT must reset alignment_iteration to 0."""
        from routing import dispatch_gate_response, PipelineState

        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iteration=3)

        with patch("routing._version_blueprint"):
            result = dispatch_gate_response(
                state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
            )

        self.assertEqual(
            result.alignment_iteration, 0,
            "RETRY BLUEPRINT must reset alignment_iteration to 0"
        )

    def test_retry_blueprint_versions_blueprint(self):
        """RETRY BLUEPRINT must call _version_blueprint before resetting."""
        from routing import dispatch_gate_response, PipelineState

        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iteration=3)

        with patch("routing._version_blueprint") as mock_version:
            result = dispatch_gate_response(
                state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
            )

        mock_version.assert_called_once_with(self.project_root, "Gate 2.3 RETRY BLUEPRINT")

    def test_retry_blueprint_sets_last_action(self):
        """RETRY BLUEPRINT must set a descriptive last_action."""
        from routing import dispatch_gate_response, PipelineState

        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iteration=3)

        with patch("routing._version_blueprint"):
            result = dispatch_gate_response(
                state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
            )

        self.assertIn(
            "RETRY BLUEPRINT", result.last_action,
            "last_action must mention RETRY BLUEPRINT"
        )

    def test_after_retry_blueprint_route_invokes_blueprint_author(self):
        """After RETRY BLUEPRINT, route() must invoke blueprint_author, not blueprint_checker."""
        from routing import route

        # State after RETRY BLUEPRINT: stage=2, sub_stage=None
        state = _make_state(stage="2", sub_stage=None, alignment_iteration=0)
        _write_last_status(self.project_root, "")

        with patch("routing._read_last_status", return_value=None):
            action = route(state, self.project_root)

        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(
            action["AGENT"], "blueprint_author",
            "After RETRY BLUEPRINT (sub_stage=None), route must invoke blueprint_author"
        )

    def test_revise_spec_still_restarts_from_stage_1(self):
        """REVISE SPEC must still restart from Stage 1 (not broken by Bug 66 fix)."""
        from routing import dispatch_gate_response

        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iteration=3)

        with patch("routing._version_spec"), \
             patch("routing.restart_from_stage") as mock_restart:
            mock_restart.return_value = _make_state(stage="1", sub_stage=None)
            result = dispatch_gate_response(
                state, "gate_2_3_alignment_exhausted", "REVISE SPEC", self.project_root
            )

        mock_restart.assert_called_once()
        args = mock_restart.call_args[0]
        self.assertEqual(args[1], "1", "REVISE SPEC must restart from Stage 1")

    def test_restart_spec_still_restarts_from_stage_1(self):
        """RESTART SPEC must still restart from Stage 1 (not broken by Bug 66 fix)."""
        from routing import dispatch_gate_response

        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iteration=3)

        with patch("routing.restart_from_stage") as mock_restart:
            mock_restart.return_value = _make_state(stage="1", sub_stage=None)
            result = dispatch_gate_response(
                state, "gate_2_3_alignment_exhausted", "RESTART SPEC", self.project_root
            )

        mock_restart.assert_called_once()
        args = mock_restart.call_args[0]
        self.assertEqual(args[1], "1", "RESTART SPEC must restart from Stage 1")


if __name__ == "__main__":
    unittest.main()
