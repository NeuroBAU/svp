"""
Tests to cover behavioral contract gaps identified during coverage review
for Unit 10: Routing Script and Update State.

Gaps covered:
  A. Route output dict contains the full set of expected keys.
  B. format_action_block includes OPTIONS in formatted output for human_gate.
  C. derive_env_name_from_state applies canonical derivation (lowercase, replace
     spaces/hyphens with underscores).
  D. dispatch_status handles HINT_BLUEPRINT_CONFLICT (cross-agent status).
  E. dispatch_agent_status recognizes HINT_BLUEPRINT_CONFLICT as cross-agent status.
  F. dispatch_command_status raises ValueError for unrecognized command status lines.
  G. run_pytest constructs correct status lines from subprocess output (mocked).
  H. human_gate action builder populates OPTIONS from GATE_VOCABULARY for every gate.
  I. route handles debug loop phases (triage, regression_test, repair, etc.).

DATA ASSUMPTION: PipelineState objects are constructed with defaults from Unit 2.
DebugSession objects use synthetic data for bug_id, classification, and phase.
Subprocess output for run_pytest tests is mocked with synthetic pytest output strings.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from svp.scripts.routing import (
    route,
    format_action_block,
    derive_env_name_from_state,
    dispatch_status,
    dispatch_agent_status,
    dispatch_command_status,
    run_pytest,
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
)
from svp.scripts.pipeline_state import PipelineState, DebugSession
from svp.scripts.state_transitions import TransitionError


@pytest.fixture
def tmp_project_root(tmp_path):
    """Create a temporary project root directory."""
    return tmp_path


def _make_state(**kwargs):
    """Helper to create a PipelineState with sensible defaults."""
    defaults = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "project_name": "test_project",
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


def _write_state(project_root, state):
    """Write pipeline state to disk."""
    state_path = project_root / "pipeline_state.json"
    state_path.write_text(
        json.dumps(state.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# GAP A: Route output dict contains the full set of expected keys
# ---------------------------------------------------------------------------

class TestRouteOutputKeys:
    """Verify route returns a dict containing all expected keys from the blueprint."""

    EXPECTED_KEYS = {
        "ACTION", "AGENT", "PREPARE", "TASK_PROMPT_FILE", "POST",
        "COMMAND", "GATE", "UNIT", "OPTIONS", "PROMPT_FILE", "MESSAGE",
    }

    def test_route_invoke_agent_has_all_keys(self, tmp_project_root):
        """An invoke_agent action from route must contain all expected keys."""
        state = _make_state(stage="0", sub_stage="project_context")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "invoke_agent"
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key '{key}' in route output"

    def test_route_human_gate_has_all_keys(self, tmp_project_root):
        """A human_gate action from route must contain all expected keys."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "human_gate"
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key '{key}' in route output"

    def test_route_run_command_has_all_keys(self, tmp_project_root):
        """A run_command action from route must contain all expected keys."""
        state = _make_state(stage="pre_stage_3", sub_stage=None)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "run_command"
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key '{key}' in route output"

    def test_route_session_boundary_has_all_keys(self, tmp_project_root):
        """A session_boundary action from route must contain all expected keys."""
        state = _make_state(
            stage="3", sub_stage="unit_verified",
            current_unit=1, total_units=5,
        )
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "session_boundary"
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key '{key}' in route output"

    def test_route_pipeline_complete_has_all_keys(self, tmp_project_root):
        """A pipeline_complete action from route must contain all expected keys."""
        state = _make_state(stage="5", sub_stage="complete")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "pipeline_complete"
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key '{key}' in route output"


# ---------------------------------------------------------------------------
# GAP B: format_action_block includes OPTIONS in output for human_gate
# ---------------------------------------------------------------------------

class TestFormatActionBlockOptions:
    """Verify format_action_block renders the OPTIONS field for human_gate."""

    def test_human_gate_options_in_output(self):
        """OPTIONS from a human_gate dict must appear in the formatted output."""
        action = {
            "ACTION": "human_gate",
            "AGENT": None,
            "PREPARE": None,
            "TASK_PROMPT_FILE": None,
            "COMMAND": None,
            "POST": None,
            "GATE": "gate_0_1_hook_activation",
            "UNIT": None,
            "OPTIONS": ["HOOKS ACTIVATED", "HOOKS FAILED"],
            "PROMPT_FILE": ".svp/gate_prompt.md",
            "MESSAGE": "Test gate message.",
        }
        result = format_action_block(action)
        assert "OPTIONS:" in result
        assert "HOOKS ACTIVATED" in result
        assert "HOOKS FAILED" in result

    def test_invoke_agent_no_options_in_output(self):
        """An invoke_agent action without OPTIONS should not have OPTIONS in output."""
        action = {
            "ACTION": "invoke_agent",
            "AGENT": "test_agent",
            "PREPARE": "python scripts/prepare.py",
            "TASK_PROMPT_FILE": ".svp/task_prompt.md",
            "COMMAND": None,
            "POST": "python scripts/update.py",
            "GATE": None,
            "UNIT": None,
            "OPTIONS": None,
            "PROMPT_FILE": None,
            "MESSAGE": "Test message.",
        }
        result = format_action_block(action)
        assert "OPTIONS:" not in result


# ---------------------------------------------------------------------------
# GAP C: derive_env_name_from_state canonical derivation
# ---------------------------------------------------------------------------

class TestDeriveEnvNameCanonical:
    """Verify the canonical derivation: lowercase, replace spaces/hyphens."""

    def test_lowercase_conversion(self):
        """Project names with uppercase must be lowercased."""
        state = _make_state(project_name="My_Project")
        result = derive_env_name_from_state(state)
        assert result == "my_project"

    def test_spaces_replaced_with_underscores(self):
        """Spaces in project names must be replaced with underscores."""
        state = _make_state(project_name="my project")
        result = derive_env_name_from_state(state)
        assert result == "my_project"

    def test_hyphens_replaced_with_underscores(self):
        """Hyphens in project names must be replaced with underscores."""
        state = _make_state(project_name="my-project")
        result = derive_env_name_from_state(state)
        assert result == "my_project"

    def test_combined_transformations(self):
        """Mixed case, spaces, and hyphens should all be handled."""
        state = _make_state(project_name="My Cool-Project")
        result = derive_env_name_from_state(state)
        assert result == "my_cool_project"

    def test_already_canonical(self):
        """An already canonical name should be returned unchanged."""
        state = _make_state(project_name="my_project")
        result = derive_env_name_from_state(state)
        assert result == "my_project"

    def test_with_dots(self):
        """Project name with dots (like svp1.2.1) retains dots."""
        state = _make_state(project_name="svp1.2.1")
        result = derive_env_name_from_state(state)
        assert result == "svp1.2.1"


# ---------------------------------------------------------------------------
# GAP D: dispatch_status handles HINT_BLUEPRINT_CONFLICT
# ---------------------------------------------------------------------------

class TestDispatchStatusCrossAgent:
    """Verify dispatch_status handles the HINT_BLUEPRINT_CONFLICT cross-agent status."""

    def test_hint_blueprint_conflict_returns_state(self, tmp_project_root):
        """HINT_BLUEPRINT_CONFLICT status should be handled without raising."""
        state = _make_state()
        result = dispatch_status(
            state,
            "HINT_BLUEPRINT_CONFLICT: test contradiction details",
            gate_id=None,
            unit=None,
            phase="test_generation",
            project_root=tmp_project_root,
        )
        assert isinstance(result, PipelineState)

    def test_hint_blueprint_conflict_exact_string(self, tmp_project_root):
        """Exact HINT_BLUEPRINT_CONFLICT string should be handled."""
        state = _make_state()
        result = dispatch_status(
            state,
            "HINT_BLUEPRINT_CONFLICT",
            gate_id=None,
            unit=None,
            phase="test_generation",
            project_root=tmp_project_root,
        )
        assert isinstance(result, PipelineState)


# ---------------------------------------------------------------------------
# GAP E: dispatch_agent_status recognizes HINT_BLUEPRINT_CONFLICT
# ---------------------------------------------------------------------------

class TestDispatchAgentStatusCrossAgent:
    """Verify dispatch_agent_status accepts HINT_BLUEPRINT_CONFLICT as valid."""

    def test_hint_blueprint_conflict_recognized(self, tmp_project_root):
        """HINT_BLUEPRINT_CONFLICT should not raise 'Unknown agent status line'."""
        state = _make_state()
        # Should not raise ValueError("Unknown agent status line")
        try:
            result = dispatch_agent_status(
                state, "",
                "HINT_BLUEPRINT_CONFLICT: some details",
                None, "test_generation", tmp_project_root,
            )
            assert isinstance(result, PipelineState)
        except (TransitionError, NotImplementedError):
            pass  # Acceptable - these come from downstream transitions


# ---------------------------------------------------------------------------
# GAP F: dispatch_command_status raises ValueError for unrecognized status
# ---------------------------------------------------------------------------

class TestDispatchCommandStatusUnknown:
    """Verify dispatch_command_status raises ValueError for unknown status lines."""

    def test_unknown_command_status_raises_value_error(self, tmp_project_root):
        """A status line not matching any COMMAND_STATUS_PATTERNS must raise ValueError."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        with pytest.raises(ValueError, match=r"Unknown"):
            dispatch_command_status(
                state, "COMPLETELY_UNKNOWN_STATUS_XYZ",
                1, "red_run", tmp_project_root,
            )

    def test_agent_status_line_not_valid_as_command(self, tmp_project_root):
        """An agent status line should not be valid as a command status."""
        state = _make_state(stage="3", current_unit=1, total_units=5)
        with pytest.raises(ValueError):
            dispatch_command_status(
                state, "TEST_GENERATION_COMPLETE",
                1, "red_run", tmp_project_root,
            )


# ---------------------------------------------------------------------------
# GAP G: run_pytest constructs correct status lines from subprocess output
# ---------------------------------------------------------------------------

class TestRunPytestStatusConstruction:
    """Verify run_pytest constructs proper status lines from subprocess results."""

    def test_all_tests_pass_returns_tests_passed(self, tmp_project_root):
        """When subprocess returns 0, status line must start with TESTS_PASSED."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="===== 10 passed in 2.5s =====",
                stderr="",
            )
            result = run_pytest(test_path, "test_env", tmp_project_root)
            assert result.startswith("TESTS_PASSED")
            assert "10 passed" in result

    def test_test_failures_returns_tests_failed(self, tmp_project_root):
        """When tests fail, status line must start with TESTS_FAILED."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="===== 8 passed, 2 failed in 3.0s =====",
                stderr="",
            )
            result = run_pytest(test_path, "test_env", tmp_project_root)
            assert result.startswith("TESTS_FAILED")
            assert "8 passed" in result
            assert "2 failed" in result

    def test_collection_error_returns_tests_error(self, tmp_project_root):
        """When there's a collection/import error, status must start with TESTS_ERROR."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=2,
                stdout="ERROR collecting tests/test_foo.py\nImportError: No module named 'foo'\nno tests ran",
                stderr="",
            )
            result = run_pytest(test_path, "test_env", tmp_project_root)
            assert result.startswith("TESTS_ERROR")

    def test_timeout_returns_tests_error(self, tmp_project_root):
        """When subprocess times out, status must start with TESTS_ERROR."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)

        import subprocess as sp
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = sp.TimeoutExpired(cmd="pytest", timeout=600)
            result = run_pytest(test_path, "test_env", tmp_project_root)
            assert result.startswith("TESTS_ERROR")

    def test_conda_not_found_returns_tests_error(self, tmp_project_root):
        """When conda is not found, status must start with TESTS_ERROR."""
        test_path = tmp_project_root / "tests"
        test_path.mkdir(exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("conda not found")
            result = run_pytest(test_path, "test_env", tmp_project_root)
            assert result.startswith("TESTS_ERROR")


# ---------------------------------------------------------------------------
# GAP H: human_gate OPTIONS populated from GATE_VOCABULARY for every gate
# ---------------------------------------------------------------------------

class TestHumanGateOptionsFromVocabulary:
    """Verify that every human_gate route output has OPTIONS matching GATE_VOCABULARY."""

    @pytest.mark.parametrize("gate_id", list(GATE_VOCABULARY.keys()))
    def test_gate_vocabulary_options_match(self, gate_id):
        """For each gate_id, building a human_gate action must yield OPTIONS
        that exactly match GATE_VOCABULARY[gate_id]."""
        # We test this by importing the internal builder (testing via route behavior)
        # We construct the action through format_action_block after building
        from svp.scripts.routing import _human_gate_action
        action = _human_gate_action(
            gate_id=gate_id,
            message="Test message",
        )
        assert action["OPTIONS"] == GATE_VOCABULARY[gate_id], (
            f"OPTIONS for {gate_id} does not match GATE_VOCABULARY"
        )


# ---------------------------------------------------------------------------
# GAP I: route handles different debug loop phases
# ---------------------------------------------------------------------------

class TestRouteDebugPhases:
    """Verify route handles various debug session phases correctly."""

    def _make_debug_state(self, phase, sub_stage=None, authorized=True):
        debug = DebugSession(
            bug_id=1,
            description="Test bug",
            classification="single_unit",
            affected_units=[3],
            phase=phase,
            authorized=authorized,
        )
        return _make_state(
            stage="5",
            sub_stage=sub_stage,
            debug_session=debug,
            current_unit=3,
            total_units=5,
        )

    def test_route_debug_triage_readonly_unauthorized(self, tmp_project_root):
        """Debug phase triage_readonly with unauthorized should produce gate_6_0."""
        state = self._make_debug_state("triage_readonly", authorized=False)
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "human_gate"
        assert result["GATE"] == "gate_6_0_debug_permission"

    def test_route_debug_triage(self, tmp_project_root):
        """Debug phase triage should invoke bug_triage agent."""
        state = self._make_debug_state("triage")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "bug_triage"

    def test_route_debug_regression_test(self, tmp_project_root):
        """Debug phase regression_test should invoke test_agent or gate."""
        state = self._make_debug_state("regression_test")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] in ("invoke_agent", "human_gate")

    def test_route_debug_regression_test_validation_gate(self, tmp_project_root):
        """Debug phase regression_test with sub_stage regression_test_validation
        should produce gate_6_1."""
        state = self._make_debug_state(
            "regression_test", sub_stage="regression_test_validation"
        )
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "human_gate"
        assert result["GATE"] == "gate_6_1_regression_test"

    def test_route_debug_classification_gate(self, tmp_project_root):
        """Debug phase regression_test with sub_stage debug_classification
        should produce gate_6_2."""
        state = self._make_debug_state(
            "regression_test", sub_stage="debug_classification"
        )
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "human_gate"
        assert result["GATE"] == "gate_6_2_debug_classification"

    def test_route_debug_repair(self, tmp_project_root):
        """Debug phase repair should invoke repair_agent."""
        state = self._make_debug_state("repair")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "invoke_agent"
        assert result["AGENT"] == "repair_agent"

    def test_route_debug_repair_exhausted_gate(self, tmp_project_root):
        """Debug phase repair with sub_stage repair_exhausted should produce gate_6_3."""
        state = self._make_debug_state("repair", sub_stage="repair_exhausted")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "human_gate"
        assert result["GATE"] == "gate_6_3_repair_exhausted"

    def test_route_debug_complete(self, tmp_project_root):
        """Debug phase complete should produce pipeline_complete."""
        state = self._make_debug_state("complete")
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "pipeline_complete"

    def test_route_debug_non_reproducible(self, tmp_project_root):
        """Debug with sub_stage non_reproducible should produce gate_6_4."""
        state = self._make_debug_state("triage", sub_stage="non_reproducible")
        # non_reproducible is checked at the end of _route_debug via state.sub_stage
        # We need a phase that falls through to the non_reproducible check
        debug = DebugSession(
            bug_id=1,
            description="Test bug",
            classification="single_unit",
            affected_units=[3],
            phase="unknown_phase",
            authorized=True,
        )
        state = _make_state(
            stage="5",
            sub_stage="non_reproducible",
            debug_session=debug,
            current_unit=3,
            total_units=5,
        )
        _write_state(tmp_project_root, state)
        result = route(state, tmp_project_root)
        assert result["ACTION"] == "human_gate"
        assert result["GATE"] == "gate_6_4_non_reproducible"
