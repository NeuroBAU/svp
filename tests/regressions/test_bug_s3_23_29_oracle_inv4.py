"""Regression tests for S3-23, S3-24, S3-25, S3-29.

S3-23: stage3_reentry COMMAND_SUCCEEDED must exit debug routing by
       transitioning the debug phase to stage3_rebuild_active, so
       _route_debug delegates to _route_stage_3 instead of re-dispatching
       stage3_reentry in an infinite loop.
S3-24: RECLASSIFY BUG at Gate 6.3 must increment triage_refinement_count
       before resetting to triage phase. Without the increment, the
       3-reclassification limit is never enforced.
S3-25: ESCALATE at Gate 4.1a must set sub_stage to gate_4_2; HUMAN FIX
       must reset sub_stage and red_run_retries for a fresh attempt.
S3-29: generate_upstream_stubs must use unit_N_stub{ext} filenames for
       upstream stubs to avoid overwriting when multiple dependencies exist.
"""

import json
from pathlib import Path

from src.unit_5.stub import PipelineState
from src.unit_10.stub import generate_upstream_stubs
from src.unit_14.stub import dispatch_command_status, dispatch_gate_response, route


def _make_state(**overrides):
    """Build a minimal PipelineState with defaults."""
    defaults = {
        "stage": "3",
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
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _setup_project_root(tmp_path, state_dict, last_status=""):
    """Create a minimal project root with pipeline_state.json and last_status.txt."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict, indent=2))
    (svp_dir / "last_status.txt").write_text(last_status)
    return tmp_path


# ---------------------------------------------------------------------------
# S3-23: stage3_reentry COMMAND_SUCCEEDED must exit debug routing
# ---------------------------------------------------------------------------


class TestS3_23_Stage3ReentryDoesNotLoop:
    """S3-23: stage3_reentry COMMAND_SUCCEEDED must transition debug phase."""

    def test_stage3_reentry_sets_rebuild_active_phase(self):
        """S3-23: After COMMAND_SUCCEEDED, debug phase must change to stage3_rebuild_active."""
        state = _make_state(
            stage="3",
            current_unit=3,
            debug_session={
                "authorized": True,
                "phase": "stage3_reentry",
                "bug_report": "test bug",
                "affected_units": [3],
            },
        )
        new = dispatch_command_status(state, "stage3_reentry", "COMMAND_SUCCEEDED")
        assert new.sub_stage == "stub_generation"
        assert new.debug_session is not None
        assert new.debug_session["phase"] == "stage3_rebuild_active", (
            "S3-23 regression: stage3_reentry COMMAND_SUCCEEDED must set "
            "debug phase to stage3_rebuild_active to prevent routing loop"
        )

    def test_stage3_reentry_failed_does_not_change_phase(self):
        """S3-23: COMMAND_FAILED should not change the debug phase."""
        state = _make_state(
            stage="3",
            current_unit=3,
            debug_session={
                "authorized": True,
                "phase": "stage3_reentry",
                "bug_report": "test bug",
            },
        )
        new = dispatch_command_status(state, "stage3_reentry", "COMMAND_FAILED")
        # Phase should remain as stage3_reentry for retry
        assert new.debug_session["phase"] == "stage3_reentry"

    def test_stage3_rebuild_active_routes_to_stage3(self, tmp_path):
        """S3-23: stage3_rebuild_active phase should delegate to Stage 3 routing."""
        state_dict = {
            "stage": "3",
            "sub_stage": "stub_generation",
            "current_unit": 3,
            "total_units": 10,
            "verified_units": [1, 2],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "stage3_rebuild_active",
                "bug_report": "test bug",
            },
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="")
        result = route(root)
        # stage3_rebuild_active with sub_stage=stub_generation should route to
        # the stub_generation command, not re-dispatch stage3_reentry or pipeline_held
        assert result["action_type"] == "run_command", (
            "S3-23 regression: stage3_rebuild_active must delegate to Stage 3 "
            f"routing, got action_type={result['action_type']}"
        )
        assert result.get("command") == "stub_generation", (
            "S3-23 regression: stage3_rebuild_active with sub_stage=stub_generation "
            f"must dispatch stub_generation command, got command={result.get('command')}"
        )

    def test_stage3_reentry_phase_dispatches_reentry_command(self, tmp_path):
        """S3-23: stage3_reentry phase (before success) should dispatch stage3_reentry command."""
        state_dict = {
            "stage": "3",
            "sub_stage": None,
            "current_unit": 3,
            "total_units": 10,
            "verified_units": [1, 2],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "stage3_reentry",
                "bug_report": "test bug",
            },
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="")
        result = route(root)
        assert result["action_type"] == "run_command"
        assert result["command"] == "stage3_reentry"


# ---------------------------------------------------------------------------
# S3-24: Gate 6.3 RECLASSIFY BUG must increment triage_refinement_count
# ---------------------------------------------------------------------------


class TestS3_24_Gate63ReclassifyIncrementsCount:
    """S3-24: RECLASSIFY BUG must increment triage_refinement_count."""

    def test_reclassify_increments_triage_count(self, tmp_path):
        """S3-24: RECLASSIFY BUG with count=0 must produce count=1."""
        state = _make_state(
            stage="5",
            debug_session={
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
                "triage_refinement_count": 0,
            },
        )
        root = _setup_project_root(tmp_path, {
            "stage": "5",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
                "triage_refinement_count": 0,
            },
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }, last_status="")
        new = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", root
        )
        assert new.debug_session is not None
        assert new.debug_session["triage_refinement_count"] == 1, (
            "S3-24 regression: RECLASSIFY BUG must increment triage_refinement_count "
            f"from 0 to 1, got {new.debug_session.get('triage_refinement_count')}"
        )
        assert new.debug_session["phase"] == "triage"

    def test_reclassify_increments_from_nonzero(self, tmp_path):
        """S3-24: RECLASSIFY BUG with count=1 must produce count=2."""
        state = _make_state(
            stage="5",
            debug_session={
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
                "triage_refinement_count": 1,
            },
        )
        root = _setup_project_root(tmp_path, {
            "stage": "5",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
                "triage_refinement_count": 1,
            },
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }, last_status="")
        new = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", root
        )
        assert new.debug_session is not None
        assert new.debug_session["triage_refinement_count"] == 2, (
            "S3-24 regression: RECLASSIFY BUG must increment triage_refinement_count "
            f"from 1 to 2, got {new.debug_session.get('triage_refinement_count')}"
        )

    def test_reclassify_at_limit_does_not_reset(self, tmp_path):
        """S3-24: When triage_refinement_count >= limit, RECLASSIFY should not reset to triage."""
        state = _make_state(
            stage="5",
            debug_session={
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
                "triage_refinement_count": 3,
            },
        )
        root = _setup_project_root(tmp_path, {
            "stage": "5",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
                "triage_refinement_count": 3,
            },
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }, last_status="")
        new = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", root
        )
        # At the limit, the phase should NOT be reset to triage
        # (the handler should not update debug phase when at limit)
        assert new.debug_session is not None
        if new.debug_session.get("phase") == "triage":
            # If phase was reset, the count should be at least 4
            # (but the spec says limit >= 3 means no more reclassification)
            assert False, (
                "S3-24 regression: at triage_refinement_count >= 3, RECLASSIFY BUG "
                "should not reset to triage phase"
            )


# ---------------------------------------------------------------------------
# S3-25: Gate 4.1a ESCALATE must advance to gate_4_2
# ---------------------------------------------------------------------------


class TestS3_25_Gate41aEscalateAdvances:
    """S3-25: ESCALATE at Gate 4.1a must set sub_stage to gate_4_2."""

    def test_escalate_advances_to_gate_4_2(self, tmp_path):
        """S3-25: ESCALATE must set sub_stage to gate_4_2."""
        state = _make_state(
            stage="4",
            sub_stage="integration_test",
            red_run_retries=3,
        )
        root = _setup_project_root(tmp_path, {
            "stage": "4",
            "sub_stage": "integration_test",
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 3,
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }, last_status="")
        new = dispatch_gate_response(state, "gate_4_1a", "ESCALATE", root)
        assert new.sub_stage == "gate_4_2", (
            "S3-25 regression: ESCALATE at Gate 4.1a must set sub_stage to gate_4_2, "
            f"got sub_stage={new.sub_stage}"
        )

    def test_human_fix_resets_for_fresh_attempt(self, tmp_path):
        """S3-25: HUMAN FIX must reset sub_stage and red_run_retries."""
        state = _make_state(
            stage="4",
            sub_stage="integration_test",
            red_run_retries=3,
        )
        root = _setup_project_root(tmp_path, {
            "stage": "4",
            "sub_stage": "integration_test",
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 3,
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }, last_status="")
        new = dispatch_gate_response(state, "gate_4_1a", "HUMAN FIX", root)
        assert new.sub_stage is None, (
            "S3-25 regression: HUMAN FIX at Gate 4.1a must set sub_stage to None, "
            f"got sub_stage={new.sub_stage}"
        )
        assert new.red_run_retries == 0, (
            "S3-25 regression: HUMAN FIX must reset red_run_retries to 0, "
            f"got red_run_retries={new.red_run_retries}"
        )

    def test_escalate_does_not_noop(self, tmp_path):
        """S3-25: ESCALATE must not be a no-op (must change state)."""
        state = _make_state(
            stage="4",
            sub_stage="integration_test",
        )
        root = _setup_project_root(tmp_path, {
            "stage": "4",
            "sub_stage": "integration_test",
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }, last_status="")
        new = dispatch_gate_response(state, "gate_4_1a", "ESCALATE", root)
        # Must differ from input state's sub_stage
        assert new.sub_stage != "integration_test", (
            "S3-25 regression: ESCALATE must not be a no-op"
        )


# ---------------------------------------------------------------------------
# S3-29: generate_upstream_stubs must use distinct filenames
# ---------------------------------------------------------------------------


class TestS3_29_UpstreamStubsDistinctFilenames:
    """S3-29: generate_upstream_stubs must not overwrite to same filename."""

    def test_upstream_stubs_have_distinct_filenames(self, tmp_path, monkeypatch):
        """S3-29: Each upstream stub must produce a unique filename."""
        output_dir = tmp_path / "stubs"
        output_dir.mkdir()

        # Mock the dependencies that generate_upstream_stubs needs
        from unittest.mock import MagicMock, patch
        import ast

        # Create a minimal AST module for each upstream unit
        mock_module = ast.parse("def foo(): pass")

        # Create mock unit objects
        mock_unit_1 = MagicMock()
        mock_unit_1.number = 1
        mock_unit_1.tier2 = "def func_a(): pass"

        mock_unit_2 = MagicMock()
        mock_unit_2.number = 2
        mock_unit_2.tier2 = "def func_b(): pass"

        mock_lang_config = {
            "stub_generator_key": "python",
            "file_extension": ".py",
            "stub_sentinel": "__SVP_STUB__ = True",
        }

        with patch("src.unit_10.stub.get_language_config", return_value=mock_lang_config), \
             patch("src.unit_10.stub.extract_units", return_value=[mock_unit_1, mock_unit_2]), \
             patch("src.unit_10.stub.parse_signatures", return_value=mock_module):

            generate_upstream_stubs(
                blueprint_dir=tmp_path,
                unit_number=5,
                upstream_units=[1, 2],
                output_dir=output_dir,
                language="python",
            )

        # Check that two distinct files were created
        files = sorted(output_dir.iterdir())
        filenames = [f.name for f in files]
        assert len(filenames) == 2, (
            f"S3-29 regression: expected 2 upstream stub files, got {len(filenames)}: {filenames}"
        )
        assert "unit_1_stub.py" in filenames, (
            f"S3-29 regression: expected unit_1_stub.py, got {filenames}"
        )
        assert "unit_2_stub.py" in filenames, (
            f"S3-29 regression: expected unit_2_stub.py, got {filenames}"
        )

    def test_upstream_stubs_do_not_overwrite_each_other(self, tmp_path):
        """S3-29: Writing two upstream stubs must not produce a single file."""
        output_dir = tmp_path / "stubs"
        output_dir.mkdir()

        from unittest.mock import MagicMock, patch
        import ast

        mock_module_1 = ast.parse("def unique_func_1(): pass")
        mock_module_2 = ast.parse("def unique_func_2(): pass")

        mock_unit_1 = MagicMock()
        mock_unit_1.number = 1
        mock_unit_1.tier2 = "def unique_func_1(): pass"

        mock_unit_2 = MagicMock()
        mock_unit_2.number = 2
        mock_unit_2.tier2 = "def unique_func_2(): pass"

        mock_lang_config = {
            "stub_generator_key": "python",
            "file_extension": ".py",
            "stub_sentinel": "__SVP_STUB__ = True",
        }

        call_count = [0]
        modules = [mock_module_1, mock_module_2]

        def mock_parse(source, lang, config):
            result = modules[call_count[0]]
            call_count[0] += 1
            return result

        with patch("src.unit_10.stub.get_language_config", return_value=mock_lang_config), \
             patch("src.unit_10.stub.extract_units", return_value=[mock_unit_1, mock_unit_2]), \
             patch("src.unit_10.stub.parse_signatures", side_effect=mock_parse):

            generate_upstream_stubs(
                blueprint_dir=tmp_path,
                unit_number=5,
                upstream_units=[1, 2],
                output_dir=output_dir,
                language="python",
            )

        # Read both files and verify they have different content
        file1 = output_dir / "unit_1_stub.py"
        file2 = output_dir / "unit_2_stub.py"
        assert file1.exists(), "S3-29 regression: unit_1_stub.py should exist"
        assert file2.exists(), "S3-29 regression: unit_2_stub.py should exist"

        content1 = file1.read_text()
        content2 = file2.read_text()
        assert "unique_func_1" in content1, (
            "S3-29 regression: unit_1_stub.py should contain unique_func_1"
        )
        assert "unique_func_2" in content2, (
            "S3-29 regression: unit_2_stub.py should contain unique_func_2"
        )
