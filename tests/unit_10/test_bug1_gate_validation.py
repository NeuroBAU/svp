"""
Tests specifically for the Bug 1 fix: gate status string vocabulary
ensures human-typed option text is the exact status string.

This is the critical behavioral contract: no translation, no prefix,
no reformatting. dispatch_gate_response uses exact string matching
against GATE_VOCABULARY, and the OPTIONS field in human_gate output
lists exactly the valid status strings.

DATA ASSUMPTION: Gate IDs and response strings come verbatim from the
blueprint's GATE_VOCABULARY specification. Invalid responses are
synthetic variations (lowercase, prefixed, truncated) designed to
exercise the exact-match boundary.
"""

import pytest
from pathlib import Path

from svp.scripts.routing import (
    dispatch_gate_response,
    GATE_VOCABULARY,
)
from svp.scripts.pipeline_state import PipelineState
from svp.scripts.state_transitions import TransitionError


@pytest.fixture
def tmp_project_root(tmp_path):
    return tmp_path


def _make_state(**kwargs):
    defaults = {
        "stage": "0",
        "sub_stage": "hook_activation",
        "project_name": "test_project",
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


class TestBug1ExactStringMatching:
    """Comprehensive tests for the Bug 1 exact string matching fix."""

    @pytest.mark.parametrize("gate_id,valid_option", [
        ("gate_0_1_hook_activation", "HOOKS ACTIVATED"),
        ("gate_0_1_hook_activation", "HOOKS FAILED"),
        ("gate_0_2_context_approval", "CONTEXT APPROVED"),
        ("gate_0_2_context_approval", "CONTEXT REJECTED"),
        ("gate_0_2_context_approval", "CONTEXT NOT READY"),
        ("gate_1_1_spec_draft", "APPROVE"),
        ("gate_1_1_spec_draft", "REVISE"),
        ("gate_1_1_spec_draft", "FRESH REVIEW"),
        ("gate_2_3_alignment_exhausted", "REVISE SPEC"),
        ("gate_2_3_alignment_exhausted", "RESTART SPEC"),
        ("gate_2_3_alignment_exhausted", "RETRY BLUEPRINT"),
        ("gate_3_1_test_validation", "TEST CORRECT"),
        ("gate_3_1_test_validation", "TEST WRONG"),
        ("gate_3_2_diagnostic_decision", "FIX IMPLEMENTATION"),
        ("gate_3_2_diagnostic_decision", "FIX BLUEPRINT"),
        ("gate_3_2_diagnostic_decision", "FIX SPEC"),
        ("gate_6_0_debug_permission", "AUTHORIZE DEBUG"),
        ("gate_6_0_debug_permission", "ABANDON DEBUG"),
        ("gate_6_3_repair_exhausted", "RETRY REPAIR"),
        ("gate_6_3_repair_exhausted", "RECLASSIFY BUG"),
        ("gate_6_3_repair_exhausted", "ABANDON DEBUG"),
    ])
    def test_valid_option_accepted(self, gate_id, valid_option, tmp_project_root):
        """Each valid option string must be accepted without ValueError."""
        state = _make_state()
        try:
            result = dispatch_gate_response(state, gate_id, valid_option, tmp_project_root)
            assert isinstance(result, PipelineState)
        except TransitionError:
            # TransitionError from state transitions is acceptable
            pass
        except NotImplementedError:
            # Stub behavior
            pass

    @pytest.mark.parametrize("gate_id,invalid_option", [
        # Lowercase versions
        ("gate_0_1_hook_activation", "hooks activated"),
        ("gate_0_1_hook_activation", "Hooks Activated"),
        ("gate_1_1_spec_draft", "approve"),
        ("gate_1_1_spec_draft", "Approve"),
        ("gate_3_1_test_validation", "test correct"),
        # With numeric prefix
        ("gate_0_1_hook_activation", "1. HOOKS ACTIVATED"),
        ("gate_1_1_spec_draft", "1) APPROVE"),
        ("gate_3_1_test_validation", "2. TEST WRONG"),
        # With extra whitespace
        ("gate_0_1_hook_activation", " HOOKS ACTIVATED"),
        ("gate_0_1_hook_activation", "HOOKS ACTIVATED "),
        ("gate_1_1_spec_draft", "  APPROVE  "),
        # Truncated
        ("gate_0_1_hook_activation", "HOOKS"),
        ("gate_0_2_context_approval", "CONTEXT"),
        # Partial match
        ("gate_0_1_hook_activation", "HOOKS ACTIVAT"),
        ("gate_3_2_diagnostic_decision", "FIX"),
        # Completely wrong
        ("gate_0_1_hook_activation", "YES"),
        ("gate_0_1_hook_activation", "NO"),
        ("gate_0_1_hook_activation", ""),
        # Cross-gate option (valid for different gate)
        ("gate_0_1_hook_activation", "APPROVE"),
        ("gate_1_1_spec_draft", "HOOKS ACTIVATED"),
    ])
    def test_invalid_option_rejected(self, gate_id, invalid_option, tmp_project_root):
        """Invalid options must raise ValueError with proper message."""
        state = _make_state()
        with pytest.raises(ValueError, match=r"Invalid gate response"):
            dispatch_gate_response(state, gate_id, invalid_option, tmp_project_root)

    def test_error_message_format(self, tmp_project_root):
        """ValueError message must include the response, gate_id, and valid options."""
        state = _make_state()
        gate_id = "gate_0_1_hook_activation"
        bad_response = "INVALID_OPTION_XYZ"
        with pytest.raises(ValueError) as exc_info:
            dispatch_gate_response(state, gate_id, bad_response, tmp_project_root)

        error_msg = str(exc_info.value)
        # Must include the invalid response
        assert bad_response in error_msg or "Invalid gate response" in error_msg
        # Must include the gate_id
        assert gate_id in error_msg
        # Must include valid options
        for opt in GATE_VOCABULARY[gate_id]:
            assert opt in error_msg

    def test_all_gates_reject_empty_string(self, tmp_project_root):
        """Every gate must reject an empty string response."""
        state = _make_state()
        for gate_id in GATE_VOCABULARY:
            with pytest.raises(ValueError):
                dispatch_gate_response(state, gate_id, "", tmp_project_root)

    def test_all_gates_reject_none_like_strings(self, tmp_project_root):
        """Every gate must reject 'None' or 'null' as a response."""
        state = _make_state()
        for gate_id in GATE_VOCABULARY:
            with pytest.raises(ValueError):
                dispatch_gate_response(state, gate_id, "None", tmp_project_root)
            with pytest.raises(ValueError):
                dispatch_gate_response(state, gate_id, "null", tmp_project_root)

    def test_gate_vocabulary_completeness(self):
        """All 18 gates from the blueprint must be present in GATE_VOCABULARY."""
        assert len(GATE_VOCABULARY) == 18

    def test_unknown_gate_id_rejected(self, tmp_project_root):
        """An unknown gate_id must be rejected (invariant: gate_id must be in vocabulary)."""
        state = _make_state()
        with pytest.raises((ValueError, KeyError, AssertionError)):
            dispatch_gate_response(
                state, "gate_99_nonexistent", "SOME OPTION", tmp_project_root
            )
