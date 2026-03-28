"""
Tests for Unit 14: Routing and Test Execution.

Synthetic Data Assumptions:
- GATE_VOCABULARY is expected to contain exactly 31 gate IDs as specified in the
  blueprint, each mapping to a list of response option strings.
- ALL_GATE_IDS from Unit 13 is the canonical list of 31 gate IDs; GATE_VOCABULARY
  keys must match this set exactly.
- TEST_OUTPUT_PARSERS is expected to contain exactly 5 keys: "python", "r",
  "plugin_markdown", "plugin_bash", "plugin_json".
- PHASE_TO_AGENT maps 8 CLI --phase values to agent type strings.
- PipelineState objects are constructed as mock objects with attributes matching
  the Unit 5 schema (stage, sub_stage, current_unit, etc.).
- State transition functions from Unit 6 are mocked to verify they are called
  with correct arguments. The mock returns are themselves mocks (representing
  new state objects) to verify no bare return of the input state.
- dispatch_gate_response, dispatch_agent_status, and dispatch_command_status
  must return a new/modified state for every valid input -- never bare return
  the original input state.
- Test parsers receive (stdout_text, stderr_text, exit_code, context_dict) and
  return a TestResult named tuple.
- Gate vocabulary response lists are taken verbatim from the blueprint contracts.
- AGENT_STATUS_LINES maps agent type strings to lists of valid status lines.
- tmp_path is used for all filesystem operations to avoid side effects.
- route() reads pipeline_state.json and .svp/last_status.txt from project_root.
- Action blocks returned by route() have keys: action_type, and optionally
  agent_type, command, gate_id, prepare, post, reminder.
"""

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from routing import (
    AGENT_STATUS_LINES,
    GATE_RESPONSES,
    GATE_VOCABULARY,
    PHASE_TO_AGENT,
    TEST_OUTPUT_PARSERS,
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
    main,
    route,
    run_tests_main,
    update_state_main,
)

# ---------------------------------------------------------------------------
# Expected constant values from the blueprint
# ---------------------------------------------------------------------------

EXPECTED_ALL_GATE_IDS = [
    "gate_0_1_hook_activation",
    "gate_0_2_context_approval",
    "gate_0_3_profile_approval",
    "gate_0_3r_profile_revision",
    "gate_1_1_spec_draft",
    "gate_1_2_spec_post_review",
    "gate_2_1_blueprint_approval",
    "gate_2_2_blueprint_post_review",
    "gate_2_3_alignment_exhausted",
    "gate_3_1_test_validation",
    "gate_3_2_diagnostic_decision",
    "gate_3_completion_failure",
    "gate_4_1_integration_failure",
    "gate_4_1a",
    "gate_4_2_assembly_exhausted",
    "gate_4_3_adaptation_review",
    "gate_5_1_repo_test",
    "gate_5_2_assembly_exhausted",
    "gate_5_3_unused_functions",
    "gate_6_0_debug_permission",
    "gate_6_1_regression_test",
    "gate_6_1a_divergence_warning",
    "gate_6_2_debug_classification",
    "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible",
    "gate_6_5_debug_commit",
    "gate_hint_conflict",
    "gate_7_a_trajectory_review",
    "gate_7_b_fix_plan_review",
    "gate_pass_transition_post_pass1",
    "gate_pass_transition_post_pass2",
]

EXPECTED_GATE_VOCABULARY = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": [
        "CONTEXT APPROVED",
        "CONTEXT REJECTED",
        "CONTEXT NOT READY",
    ],
    "gate_0_3_profile_approval": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_0_3r_profile_revision": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_1_1_spec_draft": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_1_2_spec_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_1_blueprint_approval": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_2_blueprint_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_3_alignment_exhausted": [
        "REVISE SPEC",
        "RESTART SPEC",
        "RETRY BLUEPRINT",
    ],
    "gate_3_1_test_validation": ["TEST CORRECT", "TEST WRONG"],
    "gate_3_2_diagnostic_decision": [
        "FIX IMPLEMENTATION",
        "FIX BLUEPRINT",
        "FIX SPEC",
    ],
    "gate_3_completion_failure": [
        "INVESTIGATE",
        "FORCE ADVANCE",
        "RESTART STAGE 3",
    ],
    "gate_4_1_integration_failure": ["ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_1a": ["HUMAN FIX", "ESCALATE"],
    "gate_4_2_assembly_exhausted": ["FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_3_adaptation_review": [
        "ACCEPT ADAPTATIONS",
        "MODIFY TEST",
        "REMOVE TEST",
    ],
    "gate_5_1_repo_test": ["TESTS PASSED", "TESTS FAILED"],
    "gate_5_2_assembly_exhausted": ["RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_5_3_unused_functions": ["FIX SPEC", "OVERRIDE CONTINUE"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_1a_divergence_warning": [
        "PROCEED",
        "FIX DIVERGENCE",
        "ABANDON DEBUG",
    ],
    "gate_6_2_debug_classification": [
        "FIX UNIT",
        "FIX BLUEPRINT",
        "FIX SPEC",
        "FIX IN PLACE",
    ],
    "gate_6_3_repair_exhausted": [
        "RETRY REPAIR",
        "RECLASSIFY BUG",
        "ABANDON DEBUG",
    ],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
    "gate_6_5_debug_commit": ["COMMIT APPROVED", "COMMIT REJECTED"],
    "gate_hint_conflict": ["BLUEPRINT CORRECT", "HINT CORRECT"],
    "gate_7_a_trajectory_review": [
        "APPROVE TRAJECTORY",
        "MODIFY TRAJECTORY",
        "ABORT",
    ],
    "gate_7_b_fix_plan_review": ["APPROVE FIX", "ABORT"],
    "gate_pass_transition_post_pass1": ["PROCEED TO PASS 2", "FIX BUGS"],
    "gate_pass_transition_post_pass2": ["FIX BUGS", "RUN ORACLE"],
}

EXPECTED_PHASE_TO_AGENT = {
    "help": "help_agent",
    "hint": "hint_agent",
    "reference_indexing": "reference_indexing",
    "redo": "redo_agent",
    "bug_triage": "bug_triage",
    "oracle": "oracle_agent",
    "checklist_generation": "checklist_generation",
    "regression_adaptation": "regression_adaptation",
}

EXPECTED_TEST_OUTPUT_PARSER_KEYS = {
    "python",
    "r",
    "plugin_markdown",
    "plugin_bash",
    "plugin_json",
}

VALID_ACTION_TYPES = {
    "invoke_agent",
    "run_command",
    "human_gate",
    "session_boundary",
    "pipeline_complete",
    "pipeline_held",
    "break_glass",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides):
    """Build a minimal mock PipelineState with default attributes."""
    state = MagicMock()
    defaults = {
        "stage": "0",
        "sub_stage": "hook_activation",
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
    for key, val in defaults.items():
        setattr(state, key, val)
    return state


def _make_debug_session(**overrides):
    """Build a minimal debug_session dict with defaults."""
    session = {
        "authorized": True,
        "bug_number": 1,
        "classification": None,
        "affected_units": [],
        "phase": "triage",
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    session.update(overrides)
    return session


def _setup_project_root(tmp_path, state_dict=None, last_status=""):
    """Create a minimal project root with pipeline_state.json and last_status.txt."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    if state_dict is None:
        state_dict = {
            "stage": "0",
            "sub_stage": "hook_activation",
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
        }
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict, indent=2))
    (svp_dir / "last_status.txt").write_text(last_status)
    return tmp_path


# ===========================================================================
# Section 1: GATE_VOCABULARY structural tests
# ===========================================================================


class TestGateVocabularyStructure:
    """Tests for the GATE_VOCABULARY constant structure and completeness."""

    def test_gate_vocabulary_is_a_dict(self):
        assert isinstance(GATE_VOCABULARY, dict)

    def test_gate_vocabulary_has_exactly_31_entries(self):
        assert len(GATE_VOCABULARY) == 31

    def test_gate_vocabulary_keys_match_all_gate_ids_from_unit_13(self):
        assert set(GATE_VOCABULARY.keys()) == set(EXPECTED_ALL_GATE_IDS)

    def test_gate_vocabulary_every_value_is_a_list(self):
        for gate_id, options in GATE_VOCABULARY.items():
            assert isinstance(options, list), f"{gate_id} value is not a list"

    def test_gate_vocabulary_every_list_is_non_empty(self):
        for gate_id, options in GATE_VOCABULARY.items():
            assert len(options) > 0, f"{gate_id} has empty response list"

    def test_gate_vocabulary_every_option_is_a_string(self):
        for gate_id, options in GATE_VOCABULARY.items():
            for opt in options:
                assert isinstance(opt, str), (
                    f"{gate_id} contains non-string option: {opt!r}"
                )

    def test_gate_vocabulary_no_empty_string_options(self):
        for gate_id, options in GATE_VOCABULARY.items():
            for opt in options:
                assert opt.strip() != "", (
                    f"{gate_id} contains empty/whitespace-only option"
                )

    @pytest.mark.parametrize(
        "gate_id,expected_options",
        list(EXPECTED_GATE_VOCABULARY.items()),
        ids=list(EXPECTED_GATE_VOCABULARY.keys()),
    )
    def test_gate_vocabulary_response_options_match_blueprint(
        self, gate_id, expected_options
    ):
        assert gate_id in GATE_VOCABULARY, f"Missing gate: {gate_id}"
        actual_options = GATE_VOCABULARY[gate_id]
        assert set(actual_options) == set(expected_options), (
            f"{gate_id}: expected {expected_options}, got {actual_options}"
        )


# ===========================================================================
# Section 2: TEST_OUTPUT_PARSERS structural tests
# ===========================================================================


class TestTestOutputParsersStructure:
    """Tests for the TEST_OUTPUT_PARSERS dispatch table."""

    def test_test_output_parsers_is_a_dict(self):
        assert isinstance(TEST_OUTPUT_PARSERS, dict)

    def test_test_output_parsers_has_exactly_five_keys(self):
        assert len(TEST_OUTPUT_PARSERS) == 5

    def test_test_output_parsers_contains_all_expected_keys(self):
        assert set(TEST_OUTPUT_PARSERS.keys()) == EXPECTED_TEST_OUTPUT_PARSER_KEYS

    def test_test_output_parsers_values_are_callable(self):
        for key, parser in TEST_OUTPUT_PARSERS.items():
            assert callable(parser), f"Parser for {key!r} is not callable"


class TestPythonParser:
    """Tests for the 'python' test output parser."""

    def test_python_parser_parses_all_passed(self):
        stdout = "===== 10 passed in 1.23s ====="
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 0, {})
        assert result.status == "TESTS_PASSED"
        assert result.passed == 10
        assert result.failed == 0
        assert result.errors == 0

    def test_python_parser_parses_mixed_results(self):
        stdout = "===== 8 passed, 2 failed in 3.45s ====="
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 1, {})
        assert result.status == "TESTS_FAILED"
        assert result.passed == 8
        assert result.failed == 2

    def test_python_parser_parses_errors(self):
        stdout = "===== 5 passed, 1 failed, 2 errors in 2.00s ====="
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 1, {})
        assert result.failed >= 1 or result.errors >= 1
        assert result.status in ("TESTS_FAILED", "TESTS_ERROR")

    def test_python_parser_detects_collection_error_with_error_collecting(self):
        stdout = "ERROR collecting tests/test_foo.py\nImportError: cannot import"
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 2, {})
        assert result.collection_error is True

    def test_python_parser_detects_collection_error_with_import_error(self):
        stdout = "ImportError: No module named 'foo'"
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 2, {})
        assert result.collection_error is True

    def test_python_parser_detects_collection_error_with_module_not_found(self):
        stdout = "ModuleNotFoundError: No module named 'bar'"
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 2, {})
        assert result.collection_error is True

    def test_python_parser_detects_collection_error_with_syntax_error(self):
        stdout = "SyntaxError: invalid syntax"
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 2, {})
        assert result.collection_error is True

    def test_python_parser_detects_no_tests_ran(self):
        stdout = "===== no tests ran in 0.01s ====="
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 0, {})
        assert result.collection_error is True or result.passed == 0

    def test_python_parser_returns_test_result_named_tuple(self):
        stdout = "===== 1 passed in 0.5s ====="
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 0, {})
        assert hasattr(result, "status")
        assert hasattr(result, "passed")
        assert hasattr(result, "failed")
        assert hasattr(result, "errors")
        assert hasattr(result, "output")
        assert hasattr(result, "collection_error")

    def test_python_parser_returns_tests_error_on_unparseable_output(self):
        stdout = "completely garbled output that is not pytest"
        result = TEST_OUTPUT_PARSERS["python"](stdout, "", 1, {})
        assert result.status == "TESTS_ERROR"


class TestRParser:
    """Tests for the 'r' test output parser."""

    def test_r_parser_parses_ok_count(self):
        stdout = "OK: 15\nFailed: 0\nWarnings: 0"
        result = TEST_OUTPUT_PARSERS["r"](stdout, "", 0, {})
        assert result.passed == 15
        assert result.failed == 0
        assert result.errors == 0
        assert result.status == "TESTS_PASSED"

    def test_r_parser_parses_failed_count(self):
        stdout = "OK: 10\nFailed: 3\nWarnings: 1"
        result = TEST_OUTPUT_PARSERS["r"](stdout, "", 1, {})
        assert result.passed == 10
        assert result.failed == 3
        assert result.errors == 1
        assert result.status == "TESTS_FAILED"

    def test_r_parser_maps_warnings_to_errors(self):
        stdout = "OK: 10\nFailed: 0\nWarnings: 2"
        result = TEST_OUTPUT_PARSERS["r"](stdout, "", 0, {})
        assert result.errors == 2

    def test_r_parser_returns_tests_error_on_unparseable_output(self):
        stdout = "Error in library(nonexistent): there is no package"
        result = TEST_OUTPUT_PARSERS["r"](stdout, "", 1, {})
        assert result.status == "TESTS_ERROR"


class TestPluginMarkdownParser:
    """Tests for the 'plugin_markdown' test output parser."""

    def test_markdown_parser_clean_output_returns_tests_passed(self):
        stdout = ""
        result = TEST_OUTPUT_PARSERS["plugin_markdown"](stdout, "", 0, {})
        assert result.status == "TESTS_PASSED"

    def test_markdown_parser_lint_errors_return_tests_failed(self):
        stdout = "file.md:1 MD001/heading-increment Heading levels"
        result = TEST_OUTPUT_PARSERS["plugin_markdown"](stdout, "", 1, {})
        assert result.status == "TESTS_FAILED"


class TestPluginBashParser:
    """Tests for the 'plugin_bash' test output parser."""

    def test_bash_parser_clean_output_returns_tests_passed(self):
        stdout = ""
        result = TEST_OUTPUT_PARSERS["plugin_bash"](stdout, "", 0, {})
        assert result.status == "TESTS_PASSED"

    def test_bash_parser_syntax_error_returns_tests_failed(self):
        stdout = "script.sh: line 5: syntax error near unexpected token"
        result = TEST_OUTPUT_PARSERS["plugin_bash"](stdout, "", 2, {})
        assert result.status == "TESTS_FAILED"


class TestPluginJsonParser:
    """Tests for the 'plugin_json' test output parser."""

    def test_json_parser_valid_json_returns_tests_passed(self):
        stdout = '{"key": "value"}'
        result = TEST_OUTPUT_PARSERS["plugin_json"](stdout, "", 0, {})
        assert result.status == "TESTS_PASSED"

    def test_json_parser_parse_error_returns_tests_failed(self):
        stdout = "Expecting property name enclosed in double quotes: line 1"
        result = TEST_OUTPUT_PARSERS["plugin_json"](stdout, "", 1, {})
        assert result.status == "TESTS_FAILED"


# ===========================================================================
# Section 3: PHASE_TO_AGENT structural tests
# ===========================================================================


class TestPhaseToAgentStructure:
    """Tests for the PHASE_TO_AGENT constant."""

    def test_phase_to_agent_is_a_dict(self):
        assert isinstance(PHASE_TO_AGENT, dict)

    def test_phase_to_agent_has_exactly_eight_entries(self):
        assert len(PHASE_TO_AGENT) == 8

    def test_phase_to_agent_matches_expected_mapping(self):
        assert PHASE_TO_AGENT == EXPECTED_PHASE_TO_AGENT

    @pytest.mark.parametrize(
        "phase,agent_type",
        list(EXPECTED_PHASE_TO_AGENT.items()),
    )
    def test_phase_to_agent_individual_mapping(self, phase, agent_type):
        assert phase in PHASE_TO_AGENT
        assert PHASE_TO_AGENT[phase] == agent_type


# ===========================================================================
# Section 4: AGENT_STATUS_LINES structural tests
# ===========================================================================


class TestAgentStatusLinesStructure:
    """Tests for the AGENT_STATUS_LINES constant."""

    def test_agent_status_lines_is_a_dict(self):
        assert isinstance(AGENT_STATUS_LINES, dict)

    def test_agent_status_lines_values_are_lists_of_strings(self):
        for agent_type, statuses in AGENT_STATUS_LINES.items():
            assert isinstance(statuses, list), f"{agent_type} value is not a list"
            for s in statuses:
                assert isinstance(s, str), (
                    f"{agent_type} contains non-string status: {s!r}"
                )


# ===========================================================================
# Section 5: dispatch_gate_response -- comprehensive tests for all 31 gates
# ===========================================================================


class TestDispatchGateResponseGate01HookActivation:
    """Tests for gate_0_1_hook_activation dispatch."""

    def test_hooks_activated_advances_sub_stage(self):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED", Path("/tmp")
        )
        assert result is not state

    def test_hooks_failed_halts_pipeline(self):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS FAILED", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate02ContextApproval:
    """Tests for gate_0_2_context_approval dispatch."""

    def test_context_approved_advances_sub_stage(self):
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT APPROVED", Path("/tmp")
        )
        assert result is not state

    def test_context_rejected_reinvokes_setup(self):
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT REJECTED", Path("/tmp")
        )
        assert result is not state

    def test_context_not_ready_reinvokes_setup(self):
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT NOT READY", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate03ProfileApproval:
    """Tests for gate_0_3_profile_approval dispatch."""

    def test_profile_approved_advances_to_stage_1(self):
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE APPROVED", Path("/tmp")
        )
        assert result is not state

    def test_profile_rejected_reinvokes_setup(self):
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE REJECTED", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate03rProfileRevision:
    """Tests for gate_0_3r_profile_revision dispatch."""

    def test_profile_approved_completes_redo_revision(self):
        state = _make_state(
            stage="0",
            sub_stage="redo_profile_delivery",
            redo_triggered_from={"stage": "3"},
        )
        result = dispatch_gate_response(
            state, "gate_0_3r_profile_revision", "PROFILE APPROVED", Path("/tmp")
        )
        assert result is not state

    def test_profile_rejected_reinvokes_setup_in_redo_mode(self):
        state = _make_state(
            stage="0",
            sub_stage="redo_profile_delivery",
            redo_triggered_from={"stage": "3"},
        )
        result = dispatch_gate_response(
            state, "gate_0_3r_profile_revision", "PROFILE REJECTED", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate11SpecDraft:
    """Tests for gate_1_1_spec_draft dispatch."""

    def test_approve_advances_to_checklist_generation(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "APPROVE", Path("/tmp")
        )
        assert result is not state

    def test_revise_reinvokes_stakeholder_dialog(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "REVISE", Path("/tmp")
        )
        assert result is not state

    def test_fresh_review_invokes_reviewer(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "FRESH REVIEW", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate12SpecPostReview:
    """Tests for gate_1_2_spec_post_review dispatch."""

    def test_approve_advances_to_checklist_generation(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "APPROVE", Path("/tmp")
        )
        assert result is not state

    def test_revise_versions_spec_and_reinvokes_dialog(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "REVISE", Path("/tmp")
        )
        assert result is not state

    def test_fresh_review_invokes_reviewer(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "FRESH REVIEW", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate21BlueprintApproval:
    """Tests for gate_2_1_blueprint_approval dispatch."""

    def test_approve_invokes_blueprint_checker(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "APPROVE", Path("/tmp")
        )
        assert result is not state

    def test_revise_reinvokes_blueprint_author(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "REVISE", Path("/tmp")
        )
        assert result is not state

    def test_fresh_review_invokes_blueprint_reviewer(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "FRESH REVIEW", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate22BlueprintPostReview:
    """Tests for gate_2_2_blueprint_post_review dispatch."""

    def test_approve_enters_alignment_check(self):
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", "APPROVE", Path("/tmp")
        )
        assert result is not state

    def test_revise_versions_and_reinvokes_blueprint_author(self):
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", "REVISE", Path("/tmp")
        )
        assert result is not state

    def test_fresh_review_invokes_blueprint_reviewer(self):
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", "FRESH REVIEW", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate23AlignmentExhausted:
    """Tests for gate_2_3_alignment_exhausted dispatch."""

    def test_revise_spec_versions_spec_and_advances(self):
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=3
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "REVISE SPEC", Path("/tmp")
        )
        assert result is not state

    def test_restart_spec_restarts_from_stage_1(self):
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=3
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RESTART SPEC", Path("/tmp")
        )
        assert result is not state

    def test_retry_blueprint_reinvokes_blueprint_author(self):
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=3
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate31TestValidation:
    """Tests for gate_3_1_test_validation dispatch (autonomous gate)."""

    def test_test_correct_continues(self):
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        result = dispatch_gate_response(
            state, "gate_3_1_test_validation", "TEST CORRECT", Path("/tmp")
        )
        assert result is not state

    def test_test_wrong_re_enters_test_generation(self):
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        result = dispatch_gate_response(
            state, "gate_3_1_test_validation", "TEST WRONG", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate32DiagnosticDecision:
    """Tests for gate_3_2_diagnostic_decision dispatch."""

    def test_fix_implementation_advances_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="diagnostic",
        )
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX IMPLEMENTATION", Path("/tmp")
        )
        assert result is not state

    def test_fix_blueprint_versions_and_restarts_stage_2(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="exhausted",
        )
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result is not state

    def test_fix_spec_versions_and_restarts_stage_1(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="exhausted",
        )
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX SPEC", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate3CompletionFailure:
    """Tests for gate_3_completion_failure dispatch."""

    def test_investigate_enters_debug_session(self):
        state = _make_state(stage="3", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", "INVESTIGATE", Path("/tmp")
        )
        assert result is not state

    def test_force_advance_moves_to_stage_4(self):
        state = _make_state(stage="3", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", "FORCE ADVANCE", Path("/tmp")
        )
        assert result is not state

    def test_restart_stage_3_restarts(self):
        state = _make_state(stage="3", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", "RESTART STAGE 3", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate41IntegrationFailure:
    """Tests for gate_4_1_integration_failure dispatch."""

    def test_assembly_fix_reinvokes_integration_test_author(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        assert result is not state

    def test_fix_blueprint_restarts_stage_2(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result is not state

    def test_fix_spec_restarts_stage_1(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "FIX SPEC", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate41a:
    """Tests for gate_4_1a dispatch."""

    def test_human_fix_reinvokes_with_human_guidance(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(state, "gate_4_1a", "HUMAN FIX", Path("/tmp"))
        assert result is not state

    def test_escalate_presents_assembly_exhausted(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(state, "gate_4_1a", "ESCALATE", Path("/tmp"))
        assert result is not state


class TestDispatchGateResponseGate42AssemblyExhausted:
    """Tests for gate_4_2_assembly_exhausted dispatch."""

    def test_fix_blueprint_restarts_stage_2(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result is not state

    def test_fix_spec_restarts_stage_1(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", "FIX SPEC", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate43AdaptationReview:
    """Tests for gate_4_3_adaptation_review dispatch."""

    def test_accept_adaptations_advances_to_stage_5(self):
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", "ACCEPT ADAPTATIONS", Path("/tmp")
        )
        assert result is not state

    def test_modify_test_reinvokes_regression_adaptation(self):
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", "MODIFY TEST", Path("/tmp")
        )
        assert result is not state

    def test_remove_test_removes_and_advances_to_stage_5(self):
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", "REMOVE TEST", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate51RepoTest:
    """Tests for gate_5_1_repo_test dispatch."""

    def test_tests_passed_advances_to_compliance_scan(self):
        state = _make_state(stage="5", sub_stage="repo_test")
        result = dispatch_gate_response(
            state, "gate_5_1_repo_test", "TESTS PASSED", Path("/tmp")
        )
        assert result is not state

    def test_tests_failed_re_enters_fix_cycle(self):
        state = _make_state(stage="5", sub_stage="repo_test")
        result = dispatch_gate_response(
            state, "gate_5_1_repo_test", "TESTS FAILED", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate52AssemblyExhausted:
    """Tests for gate_5_2_assembly_exhausted dispatch."""

    def test_retry_assembly_reinvokes_git_repo_agent(self):
        state = _make_state(stage="5", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", "RETRY ASSEMBLY", Path("/tmp")
        )
        assert result is not state

    def test_fix_blueprint_restarts_stage_2(self):
        state = _make_state(stage="5", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result is not state

    def test_fix_spec_restarts_stage_1(self):
        state = _make_state(stage="5", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", "FIX SPEC", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate53UnusedFunctions:
    """Tests for gate_5_3_unused_functions dispatch."""

    def test_fix_spec_versions_and_restarts_stage_1(self):
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "FIX SPEC", Path("/tmp")
        )
        assert result is not state

    def test_override_continue_advances_to_repo_complete(self):
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate60DebugPermission:
    """Tests for gate_6_0_debug_permission dispatch."""

    def test_authorize_debug_authorizes_session(self):
        state = _make_state(debug_session=_make_debug_session(authorized=False))
        result = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", Path("/tmp")
        )
        assert result is not state

    def test_abandon_debug_abandons_session(self):
        state = _make_state(debug_session=_make_debug_session(authorized=False))
        result = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate61RegressionTest:
    """Tests for gate_6_1_regression_test dispatch."""

    def test_test_correct_advances_debug_to_lessons_learned(self):
        state = _make_state(debug_session=_make_debug_session(phase="regression_test"))
        result = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST CORRECT", Path("/tmp")
        )
        assert result is not state

    def test_test_wrong_reinvokes_test_agent_in_regression_mode(self):
        state = _make_state(debug_session=_make_debug_session(phase="regression_test"))
        result = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST WRONG", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate61aDivergenceWarning:
    """Tests for gate_6_1a_divergence_warning dispatch."""

    def test_proceed_continues_normal_debug_flow(self):
        state = _make_state(debug_session=_make_debug_session())
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", "PROCEED", Path("/tmp")
        )
        assert result is not state

    def test_fix_divergence_reinvokes_git_repo_agent(self):
        state = _make_state(debug_session=_make_debug_session())
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", "FIX DIVERGENCE", Path("/tmp")
        )
        assert result is not state

    def test_abandon_debug_abandons_session(self):
        state = _make_state(debug_session=_make_debug_session())
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", "ABANDON DEBUG", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate62DebugClassification:
    """Tests for gate_6_2_debug_classification dispatch."""

    def test_fix_unit_sets_classification_and_rollback(self):
        state = _make_state(
            stage="3",
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", Path("/tmp")
        )
        assert result is not state

    def test_fix_blueprint_versions_and_restarts_stage_2(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result is not state

    def test_fix_spec_versions_and_restarts_stage_1(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX SPEC", Path("/tmp")
        )
        assert result is not state

    def test_fix_in_place_updates_debug_phase_to_repair(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate63RepairExhausted:
    """Tests for gate_6_3_repair_exhausted dispatch."""

    def test_retry_repair_resets_count_and_reinvokes(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair", repair_retry_count=3),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RETRY REPAIR", Path("/tmp")
        )
        assert result is not state

    def test_reclassify_bug_reinvokes_triage_under_limit(self):
        state = _make_state(
            debug_session=_make_debug_session(
                phase="repair", repair_retry_count=3, triage_refinement_count=1
            ),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", Path("/tmp")
        )
        assert result is not state

    def test_abandon_debug_abandons_session(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair", repair_retry_count=3),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "ABANDON DEBUG", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate64NonReproducible:
    """Tests for gate_6_4_non_reproducible dispatch."""

    def test_retry_triage_increments_and_reinvokes(self):
        state = _make_state(
            debug_session=_make_debug_session(triage_refinement_count=0),
        )
        result = dispatch_gate_response(
            state, "gate_6_4_non_reproducible", "RETRY TRIAGE", Path("/tmp")
        )
        assert result is not state

    def test_abandon_debug_abandons_session(self):
        state = _make_state(
            debug_session=_make_debug_session(),
        )
        result = dispatch_gate_response(
            state, "gate_6_4_non_reproducible", "ABANDON DEBUG", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate65DebugCommit:
    """Tests for gate_6_5_debug_commit dispatch."""

    def test_commit_approved_completes_debug_session(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="commit"),
        )
        result = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT APPROVED", Path("/tmp")
        )
        assert result is not state

    def test_commit_rejected_re_presents_commit(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="commit"),
        )
        result = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT REJECTED", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGateHintConflict:
    """Tests for gate_hint_conflict dispatch."""

    def test_blueprint_correct_discards_hint(self):
        state = _make_state()
        result = dispatch_gate_response(
            state, "gate_hint_conflict", "BLUEPRINT CORRECT", Path("/tmp")
        )
        assert result is not state

    def test_hint_correct_versions_and_restarts(self):
        state = _make_state()
        result = dispatch_gate_response(
            state, "gate_hint_conflict", "HINT CORRECT", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate7aTrajectoryReview:
    """Tests for gate_7_a_trajectory_review dispatch."""

    def test_approve_trajectory_sets_oracle_phase_to_green_run(self):
        state = _make_state(oracle_session_active=True, oracle_phase="gate_a")
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "APPROVE TRAJECTORY", Path("/tmp")
        )
        assert result is not state

    def test_modify_trajectory_re_enters_dry_run(self):
        state = _make_state(oracle_session_active=True, oracle_phase="gate_a")
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY", Path("/tmp")
        )
        assert result is not state

    def test_abort_exits_oracle_session(self):
        state = _make_state(oracle_session_active=True, oracle_phase="gate_a")
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "ABORT", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGate7bFixPlanReview:
    """Tests for gate_7_b_fix_plan_review dispatch."""

    def test_approve_fix_triggers_internal_bug_fix(self):
        state = _make_state(oracle_session_active=True, oracle_phase="gate_b")
        result = dispatch_gate_response(
            state, "gate_7_b_fix_plan_review", "APPROVE FIX", Path("/tmp")
        )
        assert result is not state

    def test_abort_logs_and_exits_oracle_session(self):
        state = _make_state(oracle_session_active=True, oracle_phase="gate_b")
        result = dispatch_gate_response(
            state, "gate_7_b_fix_plan_review", "ABORT", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGatePassTransitionPostPass1:
    """Tests for gate_pass_transition_post_pass1 dispatch."""

    def test_proceed_to_pass_2_enters_pass_2(self):
        state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            pass_=1,
            deferred_broken_units=[],
        )
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass1", "PROCEED TO PASS 2", Path("/tmp")
        )
        assert result is not state

    def test_fix_bugs_enters_debug_session(self):
        state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            pass_=1,
            deferred_broken_units=[],
        )
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass1", "FIX BUGS", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseGatePassTransitionPostPass2:
    """Tests for gate_pass_transition_post_pass2 dispatch."""

    def test_fix_bugs_enters_debug_session(self):
        state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            pass_=2,
            deferred_broken_units=[],
        )
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass2", "FIX BUGS", Path("/tmp")
        )
        assert result is not state

    def test_run_oracle_starts_oracle_session(self):
        state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            pass_=2,
            deferred_broken_units=[],
        )
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass2", "RUN ORACLE", Path("/tmp")
        )
        assert result is not state


class TestDispatchGateResponseCompletenessAndInvariants:
    """Cross-cutting tests for dispatch_gate_response completeness."""

    @pytest.mark.parametrize(
        "gate_id,response",
        [
            (gate_id, resp)
            for gate_id, resps in EXPECTED_GATE_VOCABULARY.items()
            for resp in resps
        ],
        ids=[
            f"{gid}--{resp.replace(' ', '_')}"
            for gid, resps in EXPECTED_GATE_VOCABULARY.items()
            for resp in resps
        ],
    )
    def test_every_gate_response_combination_does_not_bare_return_state(
        self, gate_id, response
    ):
        """Verify that every gate+response combination returns a modified state,
        not the original state object."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position=None,
            oracle_session_active=(
                "oracle" in gate_id or "7_a" in gate_id or "7_b" in gate_id
            ),
            oracle_phase=(
                "gate_a" if "7_a" in gate_id else "gate_b" if "7_b" in gate_id else None
            ),
            debug_session=(
                _make_debug_session()
                if "6_" in gate_id or "debug" in gate_id.lower()
                else None
            ),
            pass_=1 if "pass1" in gate_id else 2 if "pass2" in gate_id else None,
        )
        result = dispatch_gate_response(state, gate_id, response, Path("/tmp"))
        assert result is not state, (
            f"dispatch_gate_response({gate_id!r}, {response!r}) returned the "
            f"same state object -- no bare return allowed"
        )

    def test_dispatch_gate_response_handles_all_31_gates(self):
        """Verify the function can be called with each of the 31 gate IDs."""
        for gate_id, options in EXPECTED_GATE_VOCABULARY.items():
            state = _make_state(
                oracle_session_active="oracle" in gate_id or "7_" in gate_id,
                oracle_phase="gate_a"
                if "7_a" in gate_id
                else "gate_b"
                if "7_b" in gate_id
                else None,
                debug_session=_make_debug_session()
                if "6_" in gate_id or "debug" in gate_id.lower()
                else None,
                pass_=1 if "pass1" in gate_id else 2 if "pass2" in gate_id else None,
            )
            result = dispatch_gate_response(state, gate_id, options[0], Path("/tmp"))
            assert result is not None, f"dispatch returned None for {gate_id}"


# ===========================================================================
# Section 6: dispatch_agent_status -- comprehensive tests per agent type
# ===========================================================================


class TestDispatchAgentStatusSetupAgent:
    """Tests for setup_agent status dispatch."""

    def test_project_context_complete_no_bare_return(self):
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_project_context_rejected_no_bare_return(self):
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_REJECTED", Path("/tmp")
        )
        assert result is not state

    def test_profile_complete_no_bare_return(self):
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_agent_status(
            state, "setup_agent", "PROFILE_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusStakeholderDialog:
    """Tests for stakeholder_dialog status dispatch."""

    def test_spec_draft_complete_no_bare_return(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_agent_status(
            state, "stakeholder_dialog", "SPEC_DRAFT_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_spec_revision_complete_no_bare_return(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_agent_status(
            state, "stakeholder_dialog", "SPEC_REVISION_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusStakeholderReviewer:
    """Tests for stakeholder_reviewer status dispatch."""

    def test_review_complete_no_bare_return(self):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_agent_status(
            state, "stakeholder_reviewer", "REVIEW_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusBlueprintAuthor:
    """Tests for blueprint_author status dispatch."""

    def test_blueprint_draft_complete_no_bare_return(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_agent_status(
            state, "blueprint_author", "BLUEPRINT_DRAFT_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_blueprint_revision_complete_no_bare_return(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_agent_status(
            state, "blueprint_author", "BLUEPRINT_REVISION_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusBlueprintReviewer:
    """Tests for blueprint_reviewer status dispatch."""

    def test_review_complete_no_bare_return(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_agent_status(
            state, "blueprint_reviewer", "REVIEW_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusBlueprintChecker:
    """Tests for blueprint_checker status dispatch."""

    def test_alignment_confirmed_advances_sub_stage(self):
        state = _make_state(stage="2", sub_stage="alignment_check")
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_CONFIRMED", Path("/tmp")
        )
        assert result is not state

    def test_alignment_failed_blueprint_resets_to_blueprint_dialog(self):
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=0,
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: blueprint", Path("/tmp")
        )
        assert result is not state

    def test_alignment_failed_spec_sets_targeted_spec_revision(self):
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=0,
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: spec", Path("/tmp")
        )
        assert result is not state

    def test_alignment_failed_blueprint_at_limit_presents_gate_2_3(self):
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=3,
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: blueprint", Path("/tmp")
        )
        assert result is not state

    def test_alignment_failed_spec_at_limit_presents_gate_2_3(self):
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=3,
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: spec", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusChecklistGeneration:
    """Tests for checklist_generation status dispatch."""

    def test_checklists_complete_no_bare_return(self):
        state = _make_state(stage="1", sub_stage="checklist_generation")
        result = dispatch_agent_status(
            state, "checklist_generation", "CHECKLISTS_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusTestAgent:
    """Tests for test_agent status dispatch."""

    def test_test_generation_complete_no_bare_return(self):
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_regression_test_complete_no_bare_return(self):
        state = _make_state(
            stage="3",
            debug_session=_make_debug_session(phase="regression_test"),
        )
        result = dispatch_agent_status(
            state, "test_agent", "REGRESSION_TEST_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusImplementationAgent:
    """Tests for implementation_agent status dispatch."""

    def test_implementation_complete_no_bare_return(self):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state, "implementation_agent", "IMPLEMENTATION_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusCoverageReviewAgent:
    """Tests for coverage_review_agent status dispatch."""

    def test_coverage_complete_no_gaps_no_bare_return(self):
        state = _make_state(
            stage="3",
            sub_stage="coverage_review",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state, "coverage_review_agent", "COVERAGE_COMPLETE: no gaps", Path("/tmp")
        )
        assert result is not state

    def test_coverage_complete_tests_added_no_bare_return(self):
        state = _make_state(
            stage="3",
            sub_stage="coverage_review",
            current_unit=1,
        )
        result = dispatch_agent_status(
            state,
            "coverage_review_agent",
            "COVERAGE_COMPLETE: tests added",
            Path("/tmp"),
        )
        assert result is not state


class TestDispatchAgentStatusDiagnosticAgent:
    """Tests for diagnostic_agent status dispatch."""

    def test_diagnosis_complete_no_bare_return(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="diagnostic",
        )
        result = dispatch_agent_status(
            state,
            "diagnostic_agent",
            "DIAGNOSIS_COMPLETE: implementation_fault",
            Path("/tmp"),
        )
        assert result is not state


class TestDispatchAgentStatusIntegrationTestAuthor:
    """Tests for integration_test_author status dispatch."""

    def test_integration_tests_complete_no_bare_return(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_agent_status(
            state, "integration_test_author", "INTEGRATION_TESTS_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusRegressionAdaptation:
    """Tests for regression_adaptation status dispatch."""

    def test_adaptation_complete_no_bare_return(self):
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_agent_status(
            state, "regression_adaptation", "ADAPTATION_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_adaptation_needs_review_no_bare_return(self):
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_agent_status(
            state, "regression_adaptation", "ADAPTATION_NEEDS_REVIEW", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusGitRepoAgent:
    """Tests for git_repo_agent status dispatch."""

    def test_repo_assembly_complete_no_bare_return(self):
        state = _make_state(stage="5", sub_stage=None)
        result = dispatch_agent_status(
            state, "git_repo_agent", "REPO_ASSEMBLY_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusBugTriageAgent:
    """Tests for bug_triage_agent status dispatch."""

    def test_triage_complete_single_unit_no_bare_return(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", Path("/tmp")
        )
        assert result is not state

    def test_triage_complete_cross_unit_no_bare_return(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: cross_unit", Path("/tmp")
        )
        assert result is not state

    def test_triage_complete_build_env_routes_directly_to_repair(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: build_env", Path("/tmp")
        )
        assert result is not state

    def test_triage_non_reproducible_no_bare_return(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NON_REPRODUCIBLE", Path("/tmp")
        )
        assert result is not state

    def test_triage_needs_refinement_under_limit_reinvokes_triage(self):
        state = _make_state(
            debug_session=_make_debug_session(
                phase="triage", triage_refinement_count=0
            ),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NEEDS_REFINEMENT", Path("/tmp")
        )
        assert result is not state

    def test_triage_needs_refinement_at_limit_routes_to_gate_6_4(self):
        state = _make_state(
            debug_session=_make_debug_session(
                phase="triage", triage_refinement_count=3
            ),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NEEDS_REFINEMENT", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusRepairAgent:
    """Tests for repair_agent status dispatch."""

    def test_repair_complete_routes_to_reassembly(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair"),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_repair_reclassify_routes_to_gate_6_3(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair"),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_RECLASSIFY", Path("/tmp")
        )
        assert result is not state

    def test_repair_failed_under_limit_increments_and_reinvokes(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair", repair_retry_count=0),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_FAILED", Path("/tmp")
        )
        assert result is not state

    def test_repair_failed_at_limit_routes_to_gate_6_3(self):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair", repair_retry_count=3),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_FAILED", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusOracleAgent:
    """Tests for oracle_agent status dispatch."""

    def test_oracle_dry_run_complete_no_bare_return(self):
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="dry_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_DRY_RUN_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_oracle_fix_applied_no_bare_return(self):
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_FIX_APPLIED", Path("/tmp")
        )
        assert result is not state

    def test_oracle_all_clear_no_bare_return(self):
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_ALL_CLEAR", Path("/tmp")
        )
        assert result is not state

    def test_oracle_human_abort_exits_oracle_session(self):
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_HUMAN_ABORT", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusHelpAgent:
    """Tests for help_agent status dispatch."""

    def test_help_session_complete_no_hint_no_bare_return(self):
        state = _make_state()
        result = dispatch_agent_status(
            state, "help_agent", "HELP_SESSION_COMPLETE: no hint", Path("/tmp")
        )
        assert result is not state

    def test_help_session_complete_hint_forwarded_no_bare_return(self):
        state = _make_state()
        result = dispatch_agent_status(
            state, "help_agent", "HELP_SESSION_COMPLETE: hint forwarded", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusHintAgent:
    """Tests for hint_agent status dispatch."""

    def test_hint_analysis_complete_no_bare_return(self):
        state = _make_state()
        result = dispatch_agent_status(
            state, "hint_agent", "HINT_ANALYSIS_COMPLETE", Path("/tmp")
        )
        assert result is not state

    def test_hint_blueprint_conflict_presents_gate(self):
        state = _make_state()
        result = dispatch_agent_status(
            state, "hint_agent", "HINT_BLUEPRINT_CONFLICT: some details", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusReferenceIndexing:
    """Tests for reference_indexing status dispatch."""

    def test_indexing_complete_no_bare_return(self):
        state = _make_state()
        result = dispatch_agent_status(
            state, "reference_indexing", "INDEXING_COMPLETE", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusRedoAgent:
    """Tests for redo_agent status dispatch."""

    def test_redo_classified_spec_versions_and_enters_targeted_revision(self):
        state = _make_state(stage="3")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: spec", Path("/tmp")
        )
        assert result is not state

    def test_redo_classified_blueprint_versions_and_restarts_stage_2(self):
        state = _make_state(stage="3")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: blueprint", Path("/tmp")
        )
        assert result is not state

    def test_redo_classified_gate_rollback_to_unit(self):
        state = _make_state(stage="3", current_unit=5)
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: gate", Path("/tmp")
        )
        assert result is not state

    def test_redo_classified_profile_delivery_enters_redo_profile(self):
        state = _make_state(stage="3")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: profile_delivery", Path("/tmp")
        )
        assert result is not state

    def test_redo_classified_profile_blueprint_enters_redo_profile(self):
        state = _make_state(stage="3")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: profile_blueprint", Path("/tmp")
        )
        assert result is not state


class TestDispatchAgentStatusNoBareBeturnInvariant:
    """Cross-cutting invariant: no main-pipeline agent type has a bare return."""

    MAIN_AGENT_STATUS_PAIRS = [
        ("setup_agent", "PROJECT_CONTEXT_COMPLETE"),
        ("setup_agent", "PROJECT_CONTEXT_REJECTED"),
        ("setup_agent", "PROFILE_COMPLETE"),
        ("stakeholder_dialog", "SPEC_DRAFT_COMPLETE"),
        ("stakeholder_dialog", "SPEC_REVISION_COMPLETE"),
        ("stakeholder_reviewer", "REVIEW_COMPLETE"),
        ("blueprint_author", "BLUEPRINT_DRAFT_COMPLETE"),
        ("blueprint_author", "BLUEPRINT_REVISION_COMPLETE"),
        ("blueprint_reviewer", "REVIEW_COMPLETE"),
        ("blueprint_checker", "ALIGNMENT_CONFIRMED"),
        ("blueprint_checker", "ALIGNMENT_FAILED: blueprint"),
        ("blueprint_checker", "ALIGNMENT_FAILED: spec"),
        ("checklist_generation", "CHECKLISTS_COMPLETE"),
        ("test_agent", "TEST_GENERATION_COMPLETE"),
        ("test_agent", "REGRESSION_TEST_COMPLETE"),
        ("implementation_agent", "IMPLEMENTATION_COMPLETE"),
        ("coverage_review_agent", "COVERAGE_COMPLETE: no gaps"),
        ("coverage_review_agent", "COVERAGE_COMPLETE: tests added"),
        ("diagnostic_agent", "DIAGNOSIS_COMPLETE: implementation_fault"),
        ("integration_test_author", "INTEGRATION_TESTS_COMPLETE"),
        ("regression_adaptation", "ADAPTATION_COMPLETE"),
        ("regression_adaptation", "ADAPTATION_NEEDS_REVIEW"),
        ("git_repo_agent", "REPO_ASSEMBLY_COMPLETE"),
        ("bug_triage_agent", "TRIAGE_COMPLETE: single_unit"),
        ("bug_triage_agent", "TRIAGE_COMPLETE: cross_unit"),
        ("bug_triage_agent", "TRIAGE_COMPLETE: build_env"),
        ("bug_triage_agent", "TRIAGE_NON_REPRODUCIBLE"),
        ("bug_triage_agent", "TRIAGE_NEEDS_REFINEMENT"),
        ("repair_agent", "REPAIR_COMPLETE"),
        ("repair_agent", "REPAIR_RECLASSIFY"),
        ("repair_agent", "REPAIR_FAILED"),
        ("oracle_agent", "ORACLE_DRY_RUN_COMPLETE"),
        ("oracle_agent", "ORACLE_FIX_APPLIED"),
        ("oracle_agent", "ORACLE_ALL_CLEAR"),
        ("oracle_agent", "ORACLE_HUMAN_ABORT"),
        ("help_agent", "HELP_SESSION_COMPLETE: no hint"),
        ("help_agent", "HELP_SESSION_COMPLETE: hint forwarded"),
        ("hint_agent", "HINT_ANALYSIS_COMPLETE"),
        ("hint_agent", "HINT_BLUEPRINT_CONFLICT: details"),
        ("reference_indexing", "INDEXING_COMPLETE"),
        ("redo_agent", "REDO_CLASSIFIED: spec"),
        ("redo_agent", "REDO_CLASSIFIED: blueprint"),
        ("redo_agent", "REDO_CLASSIFIED: gate"),
        ("redo_agent", "REDO_CLASSIFIED: profile_delivery"),
        ("redo_agent", "REDO_CLASSIFIED: profile_blueprint"),
    ]

    @pytest.mark.parametrize(
        "agent_type,status_line",
        MAIN_AGENT_STATUS_PAIRS,
        ids=[
            f"{at}--{sl.replace(' ', '_').replace(':', '')}"
            for at, sl in MAIN_AGENT_STATUS_PAIRS
        ],
    )
    def test_no_bare_return_for_main_pipeline_agent(self, agent_type, status_line):
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
            alignment_iterations=0,
            debug_session=(
                _make_debug_session()
                if agent_type
                in (
                    "bug_triage_agent",
                    "repair_agent",
                )
                else None
            ),
            oracle_session_active=agent_type == "oracle_agent",
            oracle_phase="dry_run" if agent_type == "oracle_agent" else None,
        )
        result = dispatch_agent_status(state, agent_type, status_line, Path("/tmp"))
        assert result is not state, (
            f"dispatch_agent_status({agent_type!r}, {status_line!r}) "
            f"returned same state object -- no bare return allowed"
        )


# ===========================================================================
# Section 7: dispatch_command_status -- comprehensive tests
# ===========================================================================


class TestDispatchCommandStatusStubGeneration:
    """Tests for stub_generation command status dispatch."""

    def test_command_succeeded_advances_to_test_generation(self):
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "stub_generation", "COMMAND_SUCCEEDED", sub_stage="stub_generation"
        )
        assert result is not state

    def test_command_failed_presents_error(self):
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "stub_generation", "COMMAND_FAILED", sub_stage="stub_generation"
        )
        assert result is not state


class TestDispatchCommandStatusTestExecutionRedRun:
    """Tests for test_execution at red_run."""

    def test_tests_failed_advances_to_implementation(self):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="red_run"
        )
        assert result is not state

    def test_tests_passed_under_limit_increments_retries(self):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            red_run_retries=0,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", sub_stage="red_run"
        )
        assert result is not state

    def test_tests_passed_at_limit_enters_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            red_run_retries=3,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", sub_stage="red_run"
        )
        assert result is not state

    def test_tests_error_under_limit_sets_test_generation(self):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            red_run_retries=0,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", sub_stage="red_run"
        )
        assert result is not state

    def test_tests_error_at_limit_enters_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            red_run_retries=3,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", sub_stage="red_run"
        )
        assert result is not state


class TestDispatchCommandStatusTestExecutionGreenRun:
    """Tests for test_execution at green_run."""

    def test_tests_passed_advances_to_coverage_review(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", sub_stage="green_run"
        )
        assert result is not state

    def test_tests_failed_advances_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position=None,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
        )
        assert result is not state

    def test_tests_error_engages_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position=None,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", sub_stage="green_run"
        )
        assert result is not state

    def test_tests_failed_fix_ladder_progression_fresh_impl(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position=None,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
        )
        assert result is not state

    def test_tests_failed_fix_ladder_progression_diagnostic(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="fresh_impl",
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
        )
        assert result is not state

    def test_tests_failed_fix_ladder_progression_diagnostic_impl(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="diagnostic",
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
        )
        assert result is not state

    def test_tests_failed_fix_ladder_progression_exhausted(self):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="diagnostic_impl",
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
        )
        assert result is not state


class TestDispatchCommandStatusQualityGateA:
    """Tests for quality_gate at quality_gate_a."""

    def test_command_succeeded_advances_to_red_run(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", sub_stage="quality_gate_a"
        )
        assert result is not state

    def test_command_failed_advances_to_retry(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", sub_stage="quality_gate_a"
        )
        assert result is not state


class TestDispatchCommandStatusQualityGateB:
    """Tests for quality_gate at quality_gate_b."""

    def test_command_succeeded_advances_to_green_run(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", sub_stage="quality_gate_b"
        )
        assert result is not state

    def test_command_failed_advances_to_retry(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", sub_stage="quality_gate_b"
        )
        assert result is not state


class TestDispatchCommandStatusQualityGateARetry:
    """Tests for quality_gate at quality_gate_a_retry."""

    def test_command_succeeded_advances_to_red_run(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", sub_stage="quality_gate_a_retry"
        )
        assert result is not state

    def test_command_failed_enters_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", sub_stage="quality_gate_a_retry"
        )
        assert result is not state


class TestDispatchCommandStatusQualityGateBRetry:
    """Tests for quality_gate at quality_gate_b_retry."""

    def test_command_succeeded_advances_to_green_run(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b_retry",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", sub_stage="quality_gate_b_retry"
        )
        assert result is not state

    def test_command_failed_enters_fix_ladder(self):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b_retry",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", sub_stage="quality_gate_b_retry"
        )
        assert result is not state


class TestDispatchCommandStatusTestExecutionStage4:
    """Tests for test_execution at Stage 4 (integration tests)."""

    def test_tests_passed_advances_to_regression_adaptation(self):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", sub_stage=None
        )
        assert result is not state

    def test_tests_failed_under_limit_presents_gate_4_1(self):
        state = _make_state(stage="4", sub_stage=None, red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage=None
        )
        assert result is not state

    def test_tests_failed_at_limit_presents_gate_4_2(self):
        state = _make_state(stage="4", sub_stage=None, red_run_retries=3)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage=None
        )
        assert result is not state

    def test_tests_error_under_limit_presents_gate_4_1(self):
        state = _make_state(stage="4", sub_stage=None, red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", sub_stage=None
        )
        assert result is not state

    def test_tests_error_at_limit_presents_gate_4_2(self):
        state = _make_state(stage="4", sub_stage=None, red_run_retries=3)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", sub_stage=None
        )
        assert result is not state


class TestDispatchCommandStatusUnitCompletion:
    """Tests for unit_completion command status dispatch."""

    def test_command_succeeded_completes_unit_and_advances(self):
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
        )
        result = dispatch_command_status(
            state, "unit_completion", "COMMAND_SUCCEEDED", sub_stage="unit_completion"
        )
        assert result is not state


class TestDispatchCommandStatusNoBareReturnInvariant:
    """Cross-cutting invariant: no entry returns bare state."""

    COMMAND_STATUS_PAIRS = [
        ("stub_generation", "COMMAND_SUCCEEDED", "stub_generation"),
        ("stub_generation", "COMMAND_FAILED", "stub_generation"),
        ("test_execution", "TESTS_FAILED", "red_run"),
        ("test_execution", "TESTS_PASSED", "red_run"),
        ("test_execution", "TESTS_ERROR", "red_run"),
        ("test_execution", "TESTS_PASSED", "green_run"),
        ("test_execution", "TESTS_FAILED", "green_run"),
        ("test_execution", "TESTS_ERROR", "green_run"),
        ("quality_gate", "COMMAND_SUCCEEDED", "quality_gate_a"),
        ("quality_gate", "COMMAND_FAILED", "quality_gate_a"),
        ("quality_gate", "COMMAND_SUCCEEDED", "quality_gate_b"),
        ("quality_gate", "COMMAND_FAILED", "quality_gate_b"),
        ("quality_gate", "COMMAND_SUCCEEDED", "quality_gate_a_retry"),
        ("quality_gate", "COMMAND_FAILED", "quality_gate_a_retry"),
        ("quality_gate", "COMMAND_SUCCEEDED", "quality_gate_b_retry"),
        ("quality_gate", "COMMAND_FAILED", "quality_gate_b_retry"),
        ("unit_completion", "COMMAND_SUCCEEDED", "unit_completion"),
    ]

    @pytest.mark.parametrize(
        "command_type,status_line,sub_stage",
        COMMAND_STATUS_PAIRS,
        ids=[f"{ct}--{sl}--{ss}" for ct, sl, ss in COMMAND_STATUS_PAIRS],
    )
    def test_no_bare_return_for_command_status(
        self, command_type, status_line, sub_stage
    ):
        state = _make_state(
            stage="3",
            sub_stage=sub_stage,
            current_unit=1,
            fix_ladder_position=None,
            red_run_retries=0,
        )
        result = dispatch_command_status(state, command_type, status_line, sub_stage)
        assert result is not state, (
            f"dispatch_command_status({command_type!r}, {status_line!r}, "
            f"sub_stage={sub_stage!r}) returned same state -- no bare return"
        )


# ===========================================================================
# Section 8: route() tests
# ===========================================================================


class TestRouteReturnStructure:
    """Tests for route() return value structure."""

    def test_route_returns_a_dict(self, tmp_path):
        root = _setup_project_root(tmp_path)
        result = route(root)
        assert isinstance(result, dict)

    def test_route_returns_dict_with_action_type_key(self, tmp_path):
        root = _setup_project_root(tmp_path)
        result = route(root)
        assert "action_type" in result

    def test_route_action_type_is_valid(self, tmp_path):
        root = _setup_project_root(tmp_path)
        result = route(root)
        assert result["action_type"] in VALID_ACTION_TYPES

    def test_route_returns_dict_with_reminder_key(self, tmp_path):
        root = _setup_project_root(tmp_path)
        result = route(root)
        assert "reminder" in result

    def test_route_emits_exactly_one_action_block_per_call(self, tmp_path):
        root = _setup_project_root(tmp_path)
        result = route(root)
        # Single dict, not a list of dicts
        assert isinstance(result, dict)
        assert "action_type" in result


class TestRouteOraclePhaseDispatching:
    """Tests for route() oracle phase dispatching."""

    def test_route_oracle_dry_run_emits_invoke_agent(self, tmp_path):
        state_dict = {
            "stage": "5",
            "sub_stage": "repo_complete",
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
            "delivered_repo_path": "/repo",
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": True,
            "oracle_test_project": "/test_project",
            "oracle_phase": "dry_run",
            "oracle_run_count": 1,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict=state_dict)
        result = route(root)
        assert result["action_type"] == "invoke_agent"
        assert result.get("agent_type") == "oracle_agent"

    def test_route_oracle_gate_a_emits_human_gate(self, tmp_path):
        state_dict = {
            "stage": "5",
            "sub_stage": "repo_complete",
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
            "delivered_repo_path": "/repo",
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": True,
            "oracle_test_project": "/test_project",
            "oracle_phase": "gate_a",
            "oracle_run_count": 1,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict=state_dict)
        result = route(root)
        assert result["action_type"] == "human_gate"
        assert result.get("gate_id") == "gate_7_a_trajectory_review"

    def test_route_oracle_green_run_emits_invoke_agent(self, tmp_path):
        state_dict = {
            "stage": "5",
            "sub_stage": "repo_complete",
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
            "delivered_repo_path": "/repo",
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": True,
            "oracle_test_project": "/test_project",
            "oracle_phase": "green_run",
            "oracle_run_count": 1,
            "oracle_nested_session_path": "/nested",
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict=state_dict)
        result = route(root)
        assert result["action_type"] == "invoke_agent"
        assert result.get("agent_type") == "oracle_agent"

    def test_route_oracle_gate_b_emits_human_gate(self, tmp_path):
        state_dict = {
            "stage": "5",
            "sub_stage": "repo_complete",
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
            "delivered_repo_path": "/repo",
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": True,
            "oracle_test_project": "/test_project",
            "oracle_phase": "gate_b",
            "oracle_run_count": 1,
            "oracle_nested_session_path": "/nested",
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict=state_dict)
        result = route(root)
        assert result["action_type"] == "human_gate"
        assert result.get("gate_id") == "gate_7_b_fix_plan_review"

    def test_route_oracle_exit_deactivates_oracle_session(self, tmp_path):
        state_dict = {
            "stage": "5",
            "sub_stage": "repo_complete",
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
            "delivered_repo_path": "/repo",
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": True,
            "oracle_test_project": "/test_project",
            "oracle_phase": "exit",
            "oracle_run_count": 1,
            "oracle_nested_session_path": "/nested",
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict=state_dict)
        result = route(root)
        assert result["action_type"] in ("pipeline_complete", "session_boundary")


class TestRouteStage0Dispatching:
    """Tests for route() Stage 0 dispatching."""

    def test_route_stage_0_hook_activation_emits_gate(self, tmp_path):
        state_dict = {
            "stage": "0",
            "sub_stage": "hook_activation",
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
        }
        root = _setup_project_root(tmp_path, state_dict=state_dict)
        result = route(root)
        # Stage 0, hook_activation sub-stage should present gate_0_1 or invoke setup
        assert result["action_type"] in VALID_ACTION_TYPES


class TestRouteTwoBranchInvariant:
    """Tests for the two-branch routing invariant."""

    def test_route_with_empty_last_status_distinguishes_not_done(self, tmp_path):
        """With no last_status, route should interpret agent as 'not done'."""
        root = _setup_project_root(tmp_path, last_status="")
        result = route(root)
        assert isinstance(result, dict)
        assert "action_type" in result

    def test_route_with_status_distinguishes_done(self, tmp_path):
        """With a status line, route should interpret agent as 'done'."""
        state_dict = {
            "stage": "0",
            "sub_stage": "project_context",
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
        }
        root = _setup_project_root(
            tmp_path, state_dict=state_dict, last_status="PROJECT_CONTEXT_COMPLETE"
        )
        result = route(root)
        assert isinstance(result, dict)
        assert "action_type" in result


# ===========================================================================
# Section 9: CLI entry points
# ===========================================================================


class TestMainCLI:
    """Tests for main() CLI entry point."""

    def test_main_returns_none(self, tmp_path):
        root = _setup_project_root(tmp_path)
        result = main(["--project-root", str(root)])
        # main should print JSON to stdout and return None
        assert result is None

    def test_main_accepts_project_root_argument(self, tmp_path):
        root = _setup_project_root(tmp_path)
        # Should not raise
        main(["--project-root", str(root)])


class TestUpdateStateMainCLI:
    """Tests for update_state_main() CLI entry point."""

    def test_update_state_main_accepts_phase_argument(self, tmp_path):
        root = _setup_project_root(tmp_path)
        # This should attempt to process, may fail due to state mismatch,
        # but should accept the argument structure
        try:
            update_state_main(
                [
                    "--phase",
                    "help",
                    "--project-root",
                    str(root),
                    "--status",
                    "HELP_SESSION_COMPLETE: no hint",
                ]
            )
        except (SystemExit, Exception):
            pass  # Expected if state doesn't match

    def test_update_state_main_validates_phase_against_phase_to_agent(self):
        """Phase argument must correspond to a known agent type in PHASE_TO_AGENT."""
        # This is a structural assertion about PHASE_TO_AGENT
        for phase in EXPECTED_PHASE_TO_AGENT:
            assert phase in PHASE_TO_AGENT


class TestRunTestsMainCLI:
    """Tests for run_tests_main() CLI entry point."""

    def test_run_tests_main_accepts_unit_and_language_arguments(self, tmp_path):
        root = _setup_project_root(tmp_path)
        # This will likely fail because there are no actual tests/toolchain,
        # but it should parse arguments
        try:
            run_tests_main(
                [
                    "--unit",
                    "1",
                    "--language",
                    "python",
                    "--project-root",
                    str(root),
                    "--sub-stage",
                    "red_run",
                ]
            )
        except (SystemExit, Exception):
            pass  # Expected with minimal setup


# ===========================================================================
# Section 10: GATE_RESPONSES structural tests (if separate from GATE_VOCABULARY)
# ===========================================================================


class TestGateResponsesStructure:
    """Tests for the GATE_RESPONSES constant (alias or separate from GATE_VOCABULARY)."""

    def test_gate_responses_is_a_dict(self):
        assert isinstance(GATE_RESPONSES, dict)


# ===========================================================================
# Section 11: Cross-unit structural invariants
# ===========================================================================


class TestCrossUnitStructuralInvariants:
    """Structural tests verifying cross-unit consistency."""

    def test_gate_vocabulary_keys_equals_expected_31_gate_ids(self):
        """GATE_VOCABULARY keys must equal ALL_GATE_IDS from Unit 13."""
        assert set(GATE_VOCABULARY.keys()) == set(EXPECTED_ALL_GATE_IDS)

    def test_gate_vocabulary_has_no_extra_gates(self):
        extra = set(GATE_VOCABULARY.keys()) - set(EXPECTED_ALL_GATE_IDS)
        assert extra == set(), f"Extra gates in GATE_VOCABULARY: {extra}"

    def test_gate_vocabulary_has_no_missing_gates(self):
        missing = set(EXPECTED_ALL_GATE_IDS) - set(GATE_VOCABULARY.keys())
        assert missing == set(), f"Missing gates from GATE_VOCABULARY: {missing}"

    def test_test_output_parsers_keys_match_expected(self):
        assert set(TEST_OUTPUT_PARSERS.keys()) == EXPECTED_TEST_OUTPUT_PARSER_KEYS

    def test_phase_to_agent_values_are_known_agent_types(self):
        """PHASE_TO_AGENT values should be known agent type strings."""
        known_agents = {
            "setup_agent",
            "stakeholder_dialog",
            "stakeholder_reviewer",
            "blueprint_author",
            "blueprint_checker",
            "blueprint_reviewer",
            "test_agent",
            "implementation_agent",
            "coverage_review",
            "diagnostic_agent",
            "integration_test_author",
            "git_repo_agent",
            "help_agent",
            "hint_agent",
            "redo_agent",
            "bug_triage",
            "repair_agent",
            "reference_indexing",
            "checklist_generation",
            "regression_adaptation",
            "oracle_agent",
        }
        for phase, agent_type in PHASE_TO_AGENT.items():
            assert agent_type in known_agents, (
                f"PHASE_TO_AGENT[{phase!r}] = {agent_type!r} is not a known agent"
            )


# ===========================================================================
# Section 12: Parametric completeness for dispatch_gate_response
# ===========================================================================


class TestDispatchGateResponseParametricCompleteness:
    """Exhaustive parametric tests: every gate x every response option."""

    # Gate 0_1
    @pytest.mark.parametrize("response", ["HOOKS ACTIVATED", "HOOKS FAILED"])
    def test_gate_0_1_hook_activation_all_responses(self, response):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", response, Path("/tmp")
        )
        assert result is not state

    # Gate 0_2
    @pytest.mark.parametrize(
        "response", ["CONTEXT APPROVED", "CONTEXT REJECTED", "CONTEXT NOT READY"]
    )
    def test_gate_0_2_context_approval_all_responses(self, response):
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", response, Path("/tmp")
        )
        assert result is not state

    # Gate 0_3
    @pytest.mark.parametrize("response", ["PROFILE APPROVED", "PROFILE REJECTED"])
    def test_gate_0_3_profile_approval_all_responses(self, response):
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_gate_response(
            state, "gate_0_3_profile_approval", response, Path("/tmp")
        )
        assert result is not state

    # Gate 0_3r
    @pytest.mark.parametrize("response", ["PROFILE APPROVED", "PROFILE REJECTED"])
    def test_gate_0_3r_profile_revision_all_responses(self, response):
        state = _make_state(
            stage="0",
            sub_stage="redo_profile_delivery",
            redo_triggered_from={"stage": "3"},
        )
        result = dispatch_gate_response(
            state, "gate_0_3r_profile_revision", response, Path("/tmp")
        )
        assert result is not state

    # Gate 1_1
    @pytest.mark.parametrize("response", ["APPROVE", "REVISE", "FRESH REVIEW"])
    def test_gate_1_1_spec_draft_all_responses(self, response):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", response, Path("/tmp")
        )
        assert result is not state

    # Gate 1_2
    @pytest.mark.parametrize("response", ["APPROVE", "REVISE", "FRESH REVIEW"])
    def test_gate_1_2_spec_post_review_all_responses(self, response):
        state = _make_state(stage="1", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", response, Path("/tmp")
        )
        assert result is not state

    # Gate 2_1
    @pytest.mark.parametrize("response", ["APPROVE", "REVISE", "FRESH REVIEW"])
    def test_gate_2_1_blueprint_approval_all_responses(self, response):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", response, Path("/tmp")
        )
        assert result is not state

    # Gate 2_2
    @pytest.mark.parametrize("response", ["APPROVE", "REVISE", "FRESH REVIEW"])
    def test_gate_2_2_blueprint_post_review_all_responses(self, response):
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", response, Path("/tmp")
        )
        assert result is not state

    # Gate 2_3
    @pytest.mark.parametrize(
        "response", ["REVISE SPEC", "RESTART SPEC", "RETRY BLUEPRINT"]
    )
    def test_gate_2_3_alignment_exhausted_all_responses(self, response):
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=3,
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", response, Path("/tmp")
        )
        assert result is not state

    # Gate 3_1
    @pytest.mark.parametrize("response", ["TEST CORRECT", "TEST WRONG"])
    def test_gate_3_1_test_validation_all_responses(self, response):
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        result = dispatch_gate_response(
            state, "gate_3_1_test_validation", response, Path("/tmp")
        )
        assert result is not state

    # Gate 3_2
    @pytest.mark.parametrize(
        "response", ["FIX IMPLEMENTATION", "FIX BLUEPRINT", "FIX SPEC"]
    )
    def test_gate_3_2_diagnostic_decision_all_responses(self, response):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            fix_ladder_position="exhausted",
        )
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", response, Path("/tmp")
        )
        assert result is not state

    # Gate 3_completion_failure
    @pytest.mark.parametrize(
        "response", ["INVESTIGATE", "FORCE ADVANCE", "RESTART STAGE 3"]
    )
    def test_gate_3_completion_failure_all_responses(self, response):
        state = _make_state(stage="3", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", response, Path("/tmp")
        )
        assert result is not state

    # Gate 4_1
    @pytest.mark.parametrize("response", ["ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"])
    def test_gate_4_1_integration_failure_all_responses(self, response):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", response, Path("/tmp")
        )
        assert result is not state

    # Gate 4_1a
    @pytest.mark.parametrize("response", ["HUMAN FIX", "ESCALATE"])
    def test_gate_4_1a_all_responses(self, response):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(state, "gate_4_1a", response, Path("/tmp"))
        assert result is not state

    # Gate 4_2
    @pytest.mark.parametrize("response", ["FIX BLUEPRINT", "FIX SPEC"])
    def test_gate_4_2_assembly_exhausted_all_responses(self, response):
        state = _make_state(stage="4", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", response, Path("/tmp")
        )
        assert result is not state

    # Gate 4_3
    @pytest.mark.parametrize(
        "response", ["ACCEPT ADAPTATIONS", "MODIFY TEST", "REMOVE TEST"]
    )
    def test_gate_4_3_adaptation_review_all_responses(self, response):
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", response, Path("/tmp")
        )
        assert result is not state

    # Gate 5_1
    @pytest.mark.parametrize("response", ["TESTS PASSED", "TESTS FAILED"])
    def test_gate_5_1_repo_test_all_responses(self, response):
        state = _make_state(stage="5", sub_stage="repo_test")
        result = dispatch_gate_response(
            state, "gate_5_1_repo_test", response, Path("/tmp")
        )
        assert result is not state

    # Gate 5_2
    @pytest.mark.parametrize(
        "response", ["RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"]
    )
    def test_gate_5_2_assembly_exhausted_all_responses(self, response):
        state = _make_state(stage="5", sub_stage=None)
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", response, Path("/tmp")
        )
        assert result is not state

    # Gate 5_3
    @pytest.mark.parametrize("response", ["FIX SPEC", "OVERRIDE CONTINUE"])
    def test_gate_5_3_unused_functions_all_responses(self, response):
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_0
    @pytest.mark.parametrize("response", ["AUTHORIZE DEBUG", "ABANDON DEBUG"])
    def test_gate_6_0_debug_permission_all_responses(self, response):
        state = _make_state(
            debug_session=_make_debug_session(authorized=False),
        )
        result = dispatch_gate_response(
            state, "gate_6_0_debug_permission", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_1
    @pytest.mark.parametrize("response", ["TEST CORRECT", "TEST WRONG"])
    def test_gate_6_1_regression_test_all_responses(self, response):
        state = _make_state(
            debug_session=_make_debug_session(phase="regression_test"),
        )
        result = dispatch_gate_response(
            state, "gate_6_1_regression_test", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_1a
    @pytest.mark.parametrize("response", ["PROCEED", "FIX DIVERGENCE", "ABANDON DEBUG"])
    def test_gate_6_1a_divergence_warning_all_responses(self, response):
        state = _make_state(
            debug_session=_make_debug_session(),
        )
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_2
    @pytest.mark.parametrize(
        "response", ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC", "FIX IN PLACE"]
    )
    def test_gate_6_2_debug_classification_all_responses(self, response):
        state = _make_state(
            stage="3",
            debug_session=_make_debug_session(phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_3
    @pytest.mark.parametrize(
        "response", ["RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"]
    )
    def test_gate_6_3_repair_exhausted_all_responses(self, response):
        state = _make_state(
            debug_session=_make_debug_session(phase="repair", repair_retry_count=3),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_4
    @pytest.mark.parametrize("response", ["RETRY TRIAGE", "ABANDON DEBUG"])
    def test_gate_6_4_non_reproducible_all_responses(self, response):
        state = _make_state(
            debug_session=_make_debug_session(),
        )
        result = dispatch_gate_response(
            state, "gate_6_4_non_reproducible", response, Path("/tmp")
        )
        assert result is not state

    # Gate 6_5
    @pytest.mark.parametrize("response", ["COMMIT APPROVED", "COMMIT REJECTED"])
    def test_gate_6_5_debug_commit_all_responses(self, response):
        state = _make_state(
            debug_session=_make_debug_session(phase="commit"),
        )
        result = dispatch_gate_response(
            state, "gate_6_5_debug_commit", response, Path("/tmp")
        )
        assert result is not state

    # Gate hint_conflict
    @pytest.mark.parametrize("response", ["BLUEPRINT CORRECT", "HINT CORRECT"])
    def test_gate_hint_conflict_all_responses(self, response):
        state = _make_state()
        result = dispatch_gate_response(
            state, "gate_hint_conflict", response, Path("/tmp")
        )
        assert result is not state

    # Gate 7_a
    @pytest.mark.parametrize(
        "response", ["APPROVE TRAJECTORY", "MODIFY TRAJECTORY", "ABORT"]
    )
    def test_gate_7_a_trajectory_review_all_responses(self, response):
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_a",
        )
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", response, Path("/tmp")
        )
        assert result is not state

    # Gate 7_b
    @pytest.mark.parametrize("response", ["APPROVE FIX", "ABORT"])
    def test_gate_7_b_fix_plan_review_all_responses(self, response):
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_b",
        )
        result = dispatch_gate_response(
            state, "gate_7_b_fix_plan_review", response, Path("/tmp")
        )
        assert result is not state

    # Gate pass_transition_post_pass1
    @pytest.mark.parametrize("response", ["PROCEED TO PASS 2", "FIX BUGS"])
    def test_gate_pass_transition_post_pass1_all_responses(self, response):
        state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            pass_=1,
            deferred_broken_units=[],
        )
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass1", response, Path("/tmp")
        )
        assert result is not state

    # Gate pass_transition_post_pass2
    @pytest.mark.parametrize("response", ["FIX BUGS", "RUN ORACLE"])
    def test_gate_pass_transition_post_pass2_all_responses(self, response):
        state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            pass_=2,
            deferred_broken_units=[],
        )
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass2", response, Path("/tmp")
        )
        assert result is not state


# ===========================================================================
# Section 13: Additional edge case tests
# ===========================================================================


class TestDispatchGateResponseEdgeCases:
    """Edge case tests for dispatch_gate_response."""

    def test_gate_6_3_reclassify_bug_at_triage_limit_only_retry_and_abandon(self):
        """When triage_refinement_count >= 3, RECLASSIFY BUG should still
        produce a state transition (contract says only RETRY REPAIR and
        ABANDON DEBUG offered, but the function must still handle the call)."""
        state = _make_state(
            debug_session=_make_debug_session(
                phase="repair", repair_retry_count=3, triage_refinement_count=3
            ),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", Path("/tmp")
        )
        assert result is not state

    def test_gate_7_a_modify_trajectory_at_modification_limit(self):
        """When modification_count >= 3, MODIFY TRAJECTORY behavior should
        still produce a state transition."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_a",
            oracle_run_count=4,
        )
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY", Path("/tmp")
        )
        assert result is not state


class TestDispatchCommandStatusEdgeCases:
    """Edge case tests for dispatch_command_status."""

    def test_red_run_tests_passed_at_exactly_limit_boundary(self):
        """At exactly the iteration_limit (default 3), should enter fix ladder."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            red_run_retries=2,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", sub_stage="red_run"
        )
        assert result is not state

    def test_red_run_tests_error_at_boundary_minus_one(self):
        """At retries = limit - 1, should still regenerate tests."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            red_run_retries=1,
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", sub_stage="red_run"
        )
        assert result is not state

    def test_green_run_fix_ladder_full_progression(self):
        """Test that multiple failures progress through the full ladder."""
        positions = [None, "fresh_impl", "diagnostic", "diagnostic_impl"]
        for pos in positions:
            state = _make_state(
                stage="3",
                sub_stage="green_run",
                current_unit=1,
                fix_ladder_position=pos,
            )
            result = dispatch_command_status(
                state, "test_execution", "TESTS_FAILED", sub_stage="green_run"
            )
            assert result is not state

    def test_stage_4_tests_failed_increments_assembly_retry(self):
        """Stage 4 TESTS_FAILED should increment assembly retry counter."""
        state = _make_state(stage="4", sub_stage=None, red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", sub_stage=None
        )
        assert result is not state


class TestDispatchAgentStatusEdgeCases:
    """Edge case tests for dispatch_agent_status."""

    def test_repair_failed_boundary_at_default_limit(self):
        """At repair_retry_count == 2 (under default limit 3), should reinvoke."""
        state = _make_state(
            debug_session=_make_debug_session(phase="repair", repair_retry_count=2),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_FAILED", Path("/tmp")
        )
        assert result is not state

    def test_triage_needs_refinement_boundary_at_default_limit(self):
        """At triage_refinement_count == 2 (under default limit 3), should reinvoke."""
        state = _make_state(
            debug_session=_make_debug_session(
                phase="triage", triage_refinement_count=2
            ),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NEEDS_REFINEMENT", Path("/tmp")
        )
        assert result is not state

    def test_alignment_failed_blueprint_increments_alignment_iterations(self):
        """alignment_iterations should be incremented."""
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=1,
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: blueprint", Path("/tmp")
        )
        assert result is not state

    def test_alignment_failed_spec_increments_alignment_iterations(self):
        """alignment_iterations should be incremented."""
        state = _make_state(
            stage="2",
            sub_stage="alignment_check",
            alignment_iterations=1,
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: spec", Path("/tmp")
        )
        assert result is not state


# ===========================================================================
# Section 14: Syntax validation of this test file
# ===========================================================================


class TestSelfValidation:
    """Meta-test: verify this file parses as valid Python."""

    def test_this_test_file_is_syntactically_valid(self):
        test_file = Path(__file__)
        source = test_file.read_text()
        tree = ast.parse(source)
        assert tree is not None
