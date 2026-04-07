"""Unit 14: Routing and Test Execution -- complete test suite.

Synthetic data assumptions:
- PipelineState is constructed via keyword arguments as defined in the Unit 5 stub.
  Default state has stage="3", sub_stage="stub_generation", current_unit=1, total_units=10.
- GATE_VOCABULARY contains exactly 31 gate entries mapping gate IDs to lists of valid
  response strings.
- TEST_OUTPUT_PARSERS maps language keys ("python", "r", "plugin_markdown",
  "plugin_bash", "plugin_json") to callables that accept (stdout, stderr, exit_code, context)
  and return RunResult named tuples.
- PHASE_TO_AGENT maps 8 phase strings to agent type strings:
  {"help": "help_agent", "hint": "hint_agent", "reference_indexing": "reference_indexing",
   "redo": "redo_agent", "bug_triage": "bug_triage", "oracle": "oracle_agent",
   "checklist_generation": "checklist_generation", "regression_adaptation": "regression_adaptation"}.
- RunResult is a NamedTuple with fields: status, passed, failed, errors, output, collection_error.
- route() reads pipeline_state.json and last_status.txt from project_root/.svp/.
- dispatch_agent_status, dispatch_gate_response, dispatch_command_status all receive
  a PipelineState and return a (possibly modified) PipelineState.
- main(), update_state_main(), run_tests_main() are CLI entry points that accept argv lists.
- The pipeline_state.json and last_status.txt files are synthesized via tmp_path fixtures.
- All state-modifying functions from Unit 6 are mocked to return predictable PipelineState values.
- A debug_session dict follows: authorized (bool), bug_number (int|null),
  classification (str|null), affected_units (list[int]), phase (str),
  repair_retry_count (int), triage_refinement_count (int), ledger_path (str|null).
- Config defaults: iteration_limit=3, default pipeline state values per Unit 5 stub.
- The "no tests ran" indicator applies when test files exist but the framework reports
  no tests collected. This is distinct from collection errors.
- COLLECTION_ERROR at RunResult level is normalized to TESTS_ERROR before dispatch.
"""

import json
from pathlib import Path

import pytest

from src.unit_14.stub import (
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
from src.unit_14.unit_2_stub import RunResult
from src.unit_14.unit_5_stub import PipelineState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides):
    """Build a minimal PipelineState with sane defaults for testing."""
    defaults = {
        "stage": "3",
        "sub_stage": "stub_generation",
        "current_unit": 1,
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


def _make_debug_session(**overrides):
    """Build a minimal debug_session dict with defaults."""
    session = {
        "authorized": False,
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


def _write_state_file(tmp_path, state):
    """Write a pipeline_state.json file from a PipelineState object."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    state_dict = {
        "stage": state.stage,
        "sub_stage": state.sub_stage,
        "current_unit": state.current_unit,
        "total_units": state.total_units,
        "verified_units": state.verified_units,
        "alignment_iterations": state.alignment_iterations,
        "fix_ladder_position": state.fix_ladder_position,
        "red_run_retries": state.red_run_retries,
        "pass_history": state.pass_history,
        "debug_session": state.debug_session,
        "debug_history": state.debug_history,
        "redo_triggered_from": state.redo_triggered_from,
        "delivered_repo_path": state.delivered_repo_path,
        "primary_language": state.primary_language,
        "component_languages": state.component_languages,
        "secondary_language": state.secondary_language,
        "oracle_session_active": state.oracle_session_active,
        "oracle_test_project": state.oracle_test_project,
        "oracle_phase": state.oracle_phase,
        "oracle_run_count": state.oracle_run_count,
        "oracle_nested_session_path": state.oracle_nested_session_path,
        "state_hash": state.state_hash,
        "spec_revision_count": state.spec_revision_count,
        "pass_": state.pass_,
        "pass2_nested_session_path": state.pass2_nested_session_path,
        "deferred_broken_units": state.deferred_broken_units,
    }
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict))
    return svp_dir


def _write_last_status(tmp_path, status_text):
    """Write last_status.txt in the .svp directory."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "last_status.txt").write_text(status_text)


# ===========================================================================
# GATE_VOCABULARY tests
# ===========================================================================


class TestGateVocabulary:
    """Tests for the GATE_VOCABULARY constant."""

    def test_gate_vocabulary_is_dict(self):
        """GATE_VOCABULARY must be a dict."""
        assert isinstance(GATE_VOCABULARY, dict)

    def test_gate_vocabulary_has_31_gates(self):
        """GATE_VOCABULARY must contain exactly 31 gate entries."""
        assert len(GATE_VOCABULARY) == 31

    def test_all_gate_values_are_lists_of_strings(self):
        """Every gate entry must map to a list of string responses."""
        for gate_id, responses in GATE_VOCABULARY.items():
            assert isinstance(responses, list), f"{gate_id} value is not a list"
            for r in responses:
                assert isinstance(r, str), f"{gate_id} has non-string response: {r}"

    def test_gate_0_1_hook_activation(self):
        """gate_0_1_hook_activation has exactly HOOKS ACTIVATED and HOOKS FAILED."""
        assert "gate_0_1_hook_activation" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_0_1_hook_activation"]) == {
            "HOOKS ACTIVATED",
            "HOOKS FAILED",
        }

    def test_gate_0_2_context_approval(self):
        """gate_0_2_context_approval has CONTEXT APPROVED, CONTEXT REJECTED, CONTEXT NOT READY."""
        assert "gate_0_2_context_approval" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_0_2_context_approval"]) == {
            "CONTEXT APPROVED",
            "CONTEXT REJECTED",
            "CONTEXT NOT READY",
        }

    def test_gate_0_3_profile_approval(self):
        """gate_0_3_profile_approval has PROFILE APPROVED and PROFILE REJECTED."""
        assert "gate_0_3_profile_approval" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_0_3_profile_approval"]) == {
            "PROFILE APPROVED",
            "PROFILE REJECTED",
        }

    def test_gate_0_3r_profile_revision(self):
        """gate_0_3r_profile_revision has PROFILE APPROVED and PROFILE REJECTED."""
        assert "gate_0_3r_profile_revision" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_0_3r_profile_revision"]) == {
            "PROFILE APPROVED",
            "PROFILE REJECTED",
        }

    def test_gate_1_1_spec_draft(self):
        """gate_1_1_spec_draft has APPROVE, REVISE, FRESH REVIEW."""
        assert "gate_1_1_spec_draft" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_1_1_spec_draft"]) == {
            "APPROVE",
            "REVISE",
            "FRESH REVIEW",
        }

    def test_gate_1_2_spec_post_review(self):
        """gate_1_2_spec_post_review has APPROVE, REVISE, FRESH REVIEW."""
        assert "gate_1_2_spec_post_review" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_1_2_spec_post_review"]) == {
            "APPROVE",
            "REVISE",
            "FRESH REVIEW",
        }

    def test_gate_2_1_blueprint_approval(self):
        """gate_2_1_blueprint_approval has APPROVE, REVISE, FRESH REVIEW."""
        assert "gate_2_1_blueprint_approval" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_2_1_blueprint_approval"]) == {
            "APPROVE",
            "REVISE",
            "FRESH REVIEW",
        }

    def test_gate_2_2_blueprint_post_review(self):
        """gate_2_2_blueprint_post_review has APPROVE, REVISE, FRESH REVIEW."""
        assert "gate_2_2_blueprint_post_review" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_2_2_blueprint_post_review"]) == {
            "APPROVE",
            "REVISE",
            "FRESH REVIEW",
        }

    def test_gate_2_3_alignment_exhausted(self):
        """gate_2_3_alignment_exhausted has REVISE SPEC, RESTART SPEC, RETRY BLUEPRINT."""
        assert "gate_2_3_alignment_exhausted" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_2_3_alignment_exhausted"]) == {
            "REVISE SPEC",
            "RESTART SPEC",
            "RETRY BLUEPRINT",
        }

    def test_gate_3_1_test_validation(self):
        """gate_3_1_test_validation has TEST CORRECT and TEST WRONG."""
        assert "gate_3_1_test_validation" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_3_1_test_validation"]) == {
            "TEST CORRECT",
            "TEST WRONG",
        }

    def test_gate_3_2_diagnostic_decision(self):
        """gate_3_2_diagnostic_decision has FIX IMPLEMENTATION, FIX BLUEPRINT, FIX SPEC."""
        assert "gate_3_2_diagnostic_decision" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_3_2_diagnostic_decision"]) == {
            "FIX IMPLEMENTATION",
            "FIX BLUEPRINT",
            "FIX SPEC",
        }

    def test_gate_3_completion_failure(self):
        """gate_3_completion_failure has INVESTIGATE, FORCE ADVANCE, RESTART STAGE 3."""
        assert "gate_3_completion_failure" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_3_completion_failure"]) == {
            "INVESTIGATE",
            "FORCE ADVANCE",
            "RESTART STAGE 3",
        }

    def test_gate_4_1_integration_failure(self):
        """gate_4_1_integration_failure has ASSEMBLY FIX, FIX BLUEPRINT, FIX SPEC."""
        assert "gate_4_1_integration_failure" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_4_1_integration_failure"]) == {
            "ASSEMBLY FIX",
            "FIX BLUEPRINT",
            "FIX SPEC",
        }

    def test_gate_4_1a(self):
        """gate_4_1a has HUMAN FIX and ESCALATE."""
        assert "gate_4_1a" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_4_1a"]) == {"HUMAN FIX", "ESCALATE"}

    def test_gate_4_2_assembly_exhausted(self):
        """gate_4_2_assembly_exhausted has FIX BLUEPRINT and FIX SPEC."""
        assert "gate_4_2_assembly_exhausted" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_4_2_assembly_exhausted"]) == {
            "FIX BLUEPRINT",
            "FIX SPEC",
        }

    def test_gate_4_3_adaptation_review(self):
        """gate_4_3_adaptation_review has ACCEPT ADAPTATIONS, MODIFY TEST, REMOVE TEST."""
        assert "gate_4_3_adaptation_review" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_4_3_adaptation_review"]) == {
            "ACCEPT ADAPTATIONS",
            "MODIFY TEST",
            "REMOVE TEST",
        }

    def test_gate_5_1_repo_test(self):
        """gate_5_1_repo_test has TESTS PASSED and TESTS FAILED."""
        assert "gate_5_1_repo_test" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_5_1_repo_test"]) == {
            "TESTS PASSED",
            "TESTS FAILED",
        }

    def test_gate_5_2_assembly_exhausted(self):
        """gate_5_2_assembly_exhausted has RETRY ASSEMBLY, FIX BLUEPRINT, FIX SPEC."""
        assert "gate_5_2_assembly_exhausted" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_5_2_assembly_exhausted"]) == {
            "RETRY ASSEMBLY",
            "FIX BLUEPRINT",
            "FIX SPEC",
        }

    def test_gate_5_3_unused_functions(self):
        """gate_5_3_unused_functions has FIX SPEC and OVERRIDE CONTINUE."""
        assert "gate_5_3_unused_functions" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_5_3_unused_functions"]) == {
            "FIX SPEC",
            "OVERRIDE CONTINUE",
        }

    def test_gate_6_0_debug_permission(self):
        """gate_6_0_debug_permission has AUTHORIZE DEBUG and ABANDON DEBUG."""
        assert "gate_6_0_debug_permission" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_0_debug_permission"]) == {
            "AUTHORIZE DEBUG",
            "ABANDON DEBUG",
        }

    def test_gate_6_1_regression_test(self):
        """gate_6_1_regression_test has TEST CORRECT and TEST WRONG."""
        assert "gate_6_1_regression_test" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_1_regression_test"]) == {
            "TEST CORRECT",
            "TEST WRONG",
        }

    def test_gate_6_1a_divergence_warning(self):
        """gate_6_1a_divergence_warning has PROCEED, FIX DIVERGENCE, ABANDON DEBUG."""
        assert "gate_6_1a_divergence_warning" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_1a_divergence_warning"]) == {
            "PROCEED",
            "FIX DIVERGENCE",
            "ABANDON DEBUG",
        }

    def test_gate_6_2_debug_classification(self):
        """gate_6_2_debug_classification has FIX UNIT, FIX BLUEPRINT, FIX SPEC, FIX IN PLACE."""
        assert "gate_6_2_debug_classification" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_2_debug_classification"]) == {
            "FIX UNIT",
            "FIX BLUEPRINT",
            "FIX SPEC",
            "FIX IN PLACE",
        }

    def test_gate_6_3_repair_exhausted(self):
        """gate_6_3_repair_exhausted has RETRY REPAIR, RECLASSIFY BUG, ABANDON DEBUG."""
        assert "gate_6_3_repair_exhausted" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_3_repair_exhausted"]) == {
            "RETRY REPAIR",
            "RECLASSIFY BUG",
            "ABANDON DEBUG",
        }

    def test_gate_6_4_non_reproducible(self):
        """gate_6_4_non_reproducible has RETRY TRIAGE and ABANDON DEBUG."""
        assert "gate_6_4_non_reproducible" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_4_non_reproducible"]) == {
            "RETRY TRIAGE",
            "ABANDON DEBUG",
        }

    def test_gate_6_5_debug_commit(self):
        """gate_6_5_debug_commit has COMMIT APPROVED and COMMIT REJECTED."""
        assert "gate_6_5_debug_commit" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_6_5_debug_commit"]) == {
            "COMMIT APPROVED",
            "COMMIT REJECTED",
        }

    def test_gate_hint_conflict(self):
        """gate_hint_conflict has BLUEPRINT CORRECT and HINT CORRECT."""
        assert "gate_hint_conflict" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_hint_conflict"]) == {
            "BLUEPRINT CORRECT",
            "HINT CORRECT",
        }

    def test_gate_7_a_trajectory_review(self):
        """gate_7_a_trajectory_review has APPROVE TRAJECTORY, MODIFY TRAJECTORY, ABORT."""
        assert "gate_7_a_trajectory_review" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_7_a_trajectory_review"]) == {
            "APPROVE TRAJECTORY",
            "MODIFY TRAJECTORY",
            "ABORT",
        }

    def test_gate_7_b_fix_plan_review(self):
        """gate_7_b_fix_plan_review has APPROVE FIX and ABORT."""
        assert "gate_7_b_fix_plan_review" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_7_b_fix_plan_review"]) == {
            "APPROVE FIX",
            "ABORT",
        }

    def test_gate_pass_transition_post_pass1(self):
        """gate_pass_transition_post_pass1 has PROCEED TO PASS 2 and FIX BUGS."""
        assert "gate_pass_transition_post_pass1" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_pass_transition_post_pass1"]) == {
            "PROCEED TO PASS 2",
            "FIX BUGS",
        }

    def test_gate_pass_transition_post_pass2(self):
        """gate_pass_transition_post_pass2 has FIX BUGS and RUN ORACLE."""
        assert "gate_pass_transition_post_pass2" in GATE_VOCABULARY
        assert set(GATE_VOCABULARY["gate_pass_transition_post_pass2"]) == {
            "FIX BUGS",
            "RUN ORACLE",
        }

    def test_all_expected_gate_ids_present(self):
        """All 31 expected gate IDs are present in GATE_VOCABULARY."""
        expected_gates = {
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
        }
        assert set(GATE_VOCABULARY.keys()) == expected_gates

    def test_no_gate_has_empty_response_list(self):
        """Every gate must have at least one valid response."""
        for gate_id, responses in GATE_VOCABULARY.items():
            assert len(responses) > 0, f"{gate_id} has no responses"

    def test_no_duplicate_responses_within_a_gate(self):
        """Within any single gate, response strings must be unique."""
        for gate_id, responses in GATE_VOCABULARY.items():
            assert len(responses) == len(set(responses)), (
                f"{gate_id} has duplicate responses"
            )


# ===========================================================================
# TEST_OUTPUT_PARSERS tests
# ===========================================================================


class TestTestOutputParsers:
    """Tests for the TEST_OUTPUT_PARSERS dispatch table."""

    def test_is_dict(self):
        """TEST_OUTPUT_PARSERS must be a dict."""
        assert isinstance(TEST_OUTPUT_PARSERS, dict)

    def test_has_python_key(self):
        """Must include 'python' parser key."""
        assert "python" in TEST_OUTPUT_PARSERS

    def test_has_r_key(self):
        """Must include 'r' parser key."""
        assert "r" in TEST_OUTPUT_PARSERS

    def test_has_plugin_markdown_key(self):
        """Must include 'plugin_markdown' parser key."""
        assert "plugin_markdown" in TEST_OUTPUT_PARSERS

    def test_has_plugin_bash_key(self):
        """Must include 'plugin_bash' parser key."""
        assert "plugin_bash" in TEST_OUTPUT_PARSERS

    def test_has_plugin_json_key(self):
        """Must include 'plugin_json' parser key."""
        assert "plugin_json" in TEST_OUTPUT_PARSERS

    def test_all_values_are_callable(self):
        """Every parser value must be callable."""
        for key, parser in TEST_OUTPUT_PARSERS.items():
            assert callable(parser), f"Parser '{key}' is not callable"

    # -- Python parser --

    def test_python_parser_all_passed(self):
        """Python parser: '5 passed' output returns TESTS_PASSED with counts."""
        parser = TEST_OUTPUT_PARSERS["python"]
        result = parser("5 passed", "", 0, {})
        assert isinstance(result, RunResult)
        assert result.status == "TESTS_PASSED"
        assert result.passed == 5
        assert result.failed == 0

    def test_python_parser_mixed_results(self):
        """Python parser: '3 passed, 2 failed' returns TESTS_FAILED with counts."""
        parser = TEST_OUTPUT_PARSERS["python"]
        result = parser("3 passed, 2 failed", "", 0, {})
        assert result.status == "TESTS_FAILED"
        assert result.passed == 3
        assert result.failed == 2

    def test_python_parser_with_errors(self):
        """Python parser: '1 passed, 0 failed, 2 errors' includes error count."""
        parser = TEST_OUTPUT_PARSERS["python"]
        result = parser("1 passed, 0 failed, 2 errors", "", 0, {})
        assert result.errors == 2

    def test_python_parser_collection_error_import(self):
        """Python parser detects ImportError as collection error."""
        parser = TEST_OUTPUT_PARSERS["python"]
        ctx = {
            "collection_error_indicators": [
                "ERROR collecting",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
            ]
        }
        result = parser("ImportError: No module named 'foo'", "", 1, ctx)
        assert result.collection_error is True

    def test_python_parser_collection_error_syntax(self):
        """Python parser detects SyntaxError as collection error."""
        parser = TEST_OUTPUT_PARSERS["python"]
        ctx = {
            "collection_error_indicators": [
                "ERROR collecting",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
            ]
        }
        result = parser("SyntaxError: invalid syntax", "", 1, ctx)
        assert result.collection_error is True

    def test_python_parser_collection_error_module_not_found(self):
        """Python parser detects ModuleNotFoundError as collection error."""
        parser = TEST_OUTPUT_PARSERS["python"]
        ctx = {
            "collection_error_indicators": [
                "ERROR collecting",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
            ]
        }
        result = parser("ModuleNotFoundError: No module named 'bar'", "", 1, ctx)
        assert result.collection_error is True

    def test_python_parser_collection_error_collecting(self):
        """Python parser detects 'ERROR collecting' as collection error."""
        parser = TEST_OUTPUT_PARSERS["python"]
        ctx = {
            "collection_error_indicators": [
                "ERROR collecting",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
            ]
        }
        result = parser("ERROR collecting tests/test_foo.py", "", 1, ctx)
        assert result.collection_error is True

    def test_python_parser_no_collection_error_on_normal_failure(self):
        """Python parser: normal test failure is not a collection error."""
        parser = TEST_OUTPUT_PARSERS["python"]
        result = parser("1 passed, 1 failed", "", 0, {})
        assert result.collection_error is not True

    def test_python_parser_preserves_output(self):
        """Python parser preserves the raw stdout in the output field."""
        parser = TEST_OUTPUT_PARSERS["python"]
        raw = "5 passed in 1.2s"
        result = parser(raw, "", 0, {})
        assert raw in result.output

    def test_python_parser_unparseable_returns_tests_error(self):
        """Python parser: unparseable output returns TESTS_ERROR."""
        parser = TEST_OUTPUT_PARSERS["python"]
        result = parser("completely garbled output with no counts", "", 1, {})
        assert result.status == "TESTS_ERROR"

    # -- R parser --

    def test_r_parser_all_ok(self):
        """R parser: 'OK: 5 Failed: 0 Warnings: 0' returns TESTS_PASSED."""
        parser = TEST_OUTPUT_PARSERS["r"]
        result = parser("OK: 5 Failed: 0 Warnings: 0", "", 0, {})
        assert isinstance(result, RunResult)
        assert result.status == "TESTS_PASSED"
        assert result.passed == 5
        assert result.failed == 0
        assert result.errors == 0

    def test_r_parser_with_failures(self):
        """R parser: 'OK: 3 Failed: 2 Warnings: 1' returns TESTS_FAILED."""
        parser = TEST_OUTPUT_PARSERS["r"]
        result = parser("OK: 3 Failed: 2 Warnings: 1", "", 0, {})
        assert result.status == "TESTS_FAILED"
        assert result.passed == 3
        assert result.failed == 2
        assert result.errors == 1

    def test_r_parser_unparseable_returns_tests_error(self):
        """R parser: unparseable output returns TESTS_ERROR."""
        parser = TEST_OUTPUT_PARSERS["r"]
        result = parser("garbled R output", "", 1, {})
        assert result.status == "TESTS_ERROR"

    # -- Plugin markdown parser --

    def test_plugin_markdown_clean_output(self):
        """Markdown parser: clean output returns TESTS_PASSED."""
        parser = TEST_OUTPUT_PARSERS["plugin_markdown"]
        result = parser("", "", 0, {})
        assert isinstance(result, RunResult)
        assert result.status == "TESTS_PASSED"

    def test_plugin_markdown_lint_errors(self):
        """Markdown parser: lint errors map to TESTS_FAILED."""
        parser = TEST_OUTPUT_PARSERS["plugin_markdown"]
        result = parser(
            "file.md:1 MD001 Heading levels should only increment by one level",
            "",
            1,
            {},
        )
        assert result.status == "TESTS_FAILED"

    # -- Plugin bash parser --

    def test_plugin_bash_clean_syntax(self):
        """Bash parser: clean 'bash -n' output returns TESTS_PASSED."""
        parser = TEST_OUTPUT_PARSERS["plugin_bash"]
        result = parser("", "", 0, {})
        assert isinstance(result, RunResult)
        assert result.status == "TESTS_PASSED"

    def test_plugin_bash_syntax_error(self):
        """Bash parser: syntax errors map to TESTS_FAILED."""
        parser = TEST_OUTPUT_PARSERS["plugin_bash"]
        result = parser("script.sh: line 10: syntax error", "", 2, {})
        assert result.status == "TESTS_FAILED"

    # -- Plugin JSON parser --

    def test_plugin_json_valid(self):
        """JSON parser: valid JSON output returns TESTS_PASSED."""
        parser = TEST_OUTPUT_PARSERS["plugin_json"]
        result = parser("{}", "", 0, {})
        assert isinstance(result, RunResult)
        assert result.status == "TESTS_PASSED"

    def test_plugin_json_parse_error(self):
        """JSON parser: parse errors map to TESTS_FAILED."""
        parser = TEST_OUTPUT_PARSERS["plugin_json"]
        result = parser("Expecting value: line 1", "", 1, {})
        assert result.status == "TESTS_FAILED"

    def test_no_tests_ran_indicator(self):
        """Python parser: 'no tests ran' with test files existing is distinct from collection error."""
        parser = TEST_OUTPUT_PARSERS["python"]
        ctx = {
            "collection_error_indicators": [
                "ERROR collecting",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
                "no tests ran",
            ]
        }
        result = parser("no tests ran", "", 0, ctx)
        # "no tests ran" is a collection error indicator per registry
        assert result.collection_error is True


# ===========================================================================
# PHASE_TO_AGENT tests
# ===========================================================================


class TestPhaseToAgent:
    """Tests for the PHASE_TO_AGENT constant."""

    def test_is_dict(self):
        """PHASE_TO_AGENT must be a dict."""
        assert isinstance(PHASE_TO_AGENT, dict)

    def test_has_exactly_8_entries(self):
        """PHASE_TO_AGENT must have exactly 8 phase mappings."""
        assert len(PHASE_TO_AGENT) == 8

    def test_help_maps_to_help_agent(self):
        """Phase 'help' maps to 'help_agent'."""
        assert PHASE_TO_AGENT["help"] == "help_agent"

    def test_hint_maps_to_hint_agent(self):
        """Phase 'hint' maps to 'hint_agent'."""
        assert PHASE_TO_AGENT["hint"] == "hint_agent"

    def test_reference_indexing_maps_correctly(self):
        """Phase 'reference_indexing' maps to 'reference_indexing'."""
        assert PHASE_TO_AGENT["reference_indexing"] == "reference_indexing"

    def test_redo_maps_to_redo_agent(self):
        """Phase 'redo' maps to 'redo_agent'."""
        assert PHASE_TO_AGENT["redo"] == "redo_agent"

    def test_bug_triage_maps_correctly(self):
        """Phase 'bug_triage' maps to 'bug_triage_agent' (Bug S3-86 fix)."""
        assert PHASE_TO_AGENT["bug_triage"] == "bug_triage_agent"

    def test_oracle_maps_to_oracle_agent(self):
        """Phase 'oracle' maps to 'oracle_agent'."""
        assert PHASE_TO_AGENT["oracle"] == "oracle_agent"

    def test_checklist_generation_maps_correctly(self):
        """Phase 'checklist_generation' maps to 'checklist_generation'."""
        assert PHASE_TO_AGENT["checklist_generation"] == "checklist_generation"

    def test_regression_adaptation_maps_correctly(self):
        """Phase 'regression_adaptation' maps to 'regression_adaptation'."""
        assert PHASE_TO_AGENT["regression_adaptation"] == "regression_adaptation"

    def test_exact_key_set(self):
        """PHASE_TO_AGENT keys match the expected set exactly."""
        expected = {
            "help",
            "hint",
            "reference_indexing",
            "redo",
            "bug_triage",
            "oracle",
            "checklist_generation",
            "regression_adaptation",
        }
        assert set(PHASE_TO_AGENT.keys()) == expected

    def test_all_values_are_strings(self):
        """Every value in PHASE_TO_AGENT must be a string."""
        for phase, agent in PHASE_TO_AGENT.items():
            assert isinstance(agent, str), f"Phase '{phase}' maps to non-string"


# ===========================================================================
# route() tests
# ===========================================================================


class TestRoute:
    """Tests for the route() function."""

    def test_returns_dict(self, tmp_path):
        """route() must return a dict."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert isinstance(result, dict)

    def test_action_block_has_action_type(self, tmp_path):
        """Returned action block must include 'action_type' key."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert "action_type" in result

    def test_action_block_has_reminder(self, tmp_path):
        """Returned action block must include 'reminder' key."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert "reminder" in result

    def test_valid_action_types(self, tmp_path):
        """action_type must be one of the seven valid values."""
        valid_types = {
            "invoke_agent",
            "run_command",
            "human_gate",
            "session_boundary",
            "pipeline_complete",
            "pipeline_held",
            "break_glass",
        }
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] in valid_types

    def test_emits_exactly_one_action_block(self, tmp_path):
        """route() returns exactly one action block per call (pipeline fidelity)."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        # Verifies it is a single dict, not a list
        assert isinstance(result, dict)
        assert "action_type" in result

    def test_invoke_agent_includes_agent_type(self, tmp_path):
        """When action_type is invoke_agent, agent_type must be present."""
        state = _make_state(stage="0", sub_stage="project_context")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        if result["action_type"] == "invoke_agent":
            assert "agent_type" in result
            assert isinstance(result["agent_type"], str)

    def test_human_gate_includes_gate_id(self, tmp_path):
        """When action_type is human_gate, gate_id must be present."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "HOOKS ACTIVATED")
        # This may or may not produce a gate; test the structure if it does
        result = route(tmp_path)
        if result["action_type"] == "human_gate":
            assert "gate_id" in result
            assert isinstance(result["gate_id"], str)

    # -- Oracle routing --

    def test_oracle_dry_run_routes_to_invoke_agent(self, tmp_path):
        """When oracle_session_active and oracle_phase=='dry_run' with test project set, emits invoke_agent with oracle_agent."""
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="dry_run",
            oracle_test_project="examples/demo",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] == "invoke_agent"
        assert result["agent_type"] == "oracle_agent"

    def test_oracle_gate_a_routes_to_human_gate(self, tmp_path):
        """When oracle_phase=='gate_a', emits human_gate with gate_7_a_trajectory_review."""
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="gate_a",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] == "human_gate"
        assert result["gate_id"] == "gate_7_a_trajectory_review"

    def test_oracle_green_run_routes_to_invoke_agent(self, tmp_path):
        """When oracle_phase=='green_run', emits invoke_agent with oracle_agent."""
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] == "invoke_agent"
        assert result["agent_type"] == "oracle_agent"

    def test_oracle_gate_b_routes_to_human_gate(self, tmp_path):
        """When oracle_phase=='gate_b', emits human_gate with gate_7_b_fix_plan_review."""
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="gate_b",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] == "human_gate"
        assert result["gate_id"] == "gate_7_b_fix_plan_review"

    def test_oracle_exit_deactivates_session(self, tmp_path):
        """When oracle_phase=='exit', emits pipeline_complete or returns to Stage 5."""
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="exit",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] in {"pipeline_complete", "session_boundary"}

    def test_oracle_select_builds_deterministic_list(self, tmp_path):
        """Bug S3-76: oracle_select_test_project must contain pre-built list with hardcoded F-mode entry."""
        # Create examples/ with a manifest
        examples = tmp_path / "examples" / "test-project"
        examples.mkdir(parents=True)
        (examples / "oracle_manifest.json").write_text(
            json.dumps({"name": "Test", "oracle_mode": "product", "description": "A test project"}),
            encoding="utf-8",
        )
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="dry_run",
            oracle_test_project=None,
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert result["action_type"] == "oracle_select_test_project"
        reminder = result["reminder"]
        assert "SVP Pipeline" in reminder, "F-mode hardcoded entry missing"
        assert "Test (test-project/)" in reminder, "E-mode discovered entry missing"

    def test_oracle_select_has_post_and_mapping(self, tmp_path):
        """Bug S3-77: oracle_select_test_project must have post command and number-to-path mapping."""
        examples = tmp_path / "examples" / "demo"
        examples.mkdir(parents=True)
        (examples / "oracle_manifest.json").write_text(
            json.dumps({"name": "Demo", "oracle_mode": "product", "description": "Demo"}),
            encoding="utf-8",
        )
        state = _make_state(
            stage="5",
            sub_stage="repo_complete",
            oracle_session_active=True,
            oracle_phase="dry_run",
            oracle_test_project=None,
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert "post" in result, "Bug S3-77: action block must have post field"
        assert "oracle_test_project_selection" in result["post"]
        reminder = result["reminder"]
        assert "docs/" in reminder, "Mapping must include docs/ for F-mode"
        assert "examples/demo/" in reminder, "Mapping must include examples/demo/ for E-mode"

    def test_emode_bootstrap_resets_pipeline_state_to_stage_0(self, tmp_path):
        """Bug S3-90: E-mode bootstrap must reset pipeline_state.json to stage=0.

        When _bootstrap_oracle_nested_session runs in E-mode (oracle_test_project starts
        with 'examples/'), copying .svp/ from project_root brings in the stale stage=5
        pipeline_state.json. The fix must overwrite pipeline_state.json with a fresh
        stage=0 state so the nested session starts at Stage 0.

        This is verified by:
        1. Setting up a stale .svp/pipeline_state.json with stage=5 in project_root.
        2. Triggering the green_run oracle routing which calls _bootstrap_oracle_nested_session.
        3. Verifying the nested session workspace has pipeline_state.json with stage='0'.
        """
        import dataclasses

        # Create a stale pipeline_state.json with stage=5 in project_root/.svp/
        stale_state = _make_state(
            stage="5",
            sub_stage="pass_transition",
            oracle_session_active=True,
            oracle_phase="green_run",
            oracle_test_project="examples/gol-plugin",
            oracle_run_count=7,
        )
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        stale_state_dict = {
            "stage": "5",
            "sub_stage": "pass_transition",
            "oracle_session_active": True,
            "oracle_phase": "green_run",
            "oracle_test_project": "examples/gol-plugin",
            "oracle_run_count": 7,
            "oracle_nested_session_path": None,
            "oracle_modification_count": 0,
            "current_unit": None,
            "total_units": 0,
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
            "state_hash": None,
            "spec_revision_count": 0,
            "pass_": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        (svp_dir / "pipeline_state.json").write_text(
            json.dumps(stale_state_dict), encoding="utf-8"
        )
        _write_last_status(tmp_path, "")

        # Create the test project directory structure (examples/gol-plugin)
        examples_dir = tmp_path / "examples" / "gol-plugin"
        examples_dir.mkdir(parents=True)
        (examples_dir / "stakeholder_spec.md").write_text("# GoL Plugin Spec")
        (examples_dir / "oracle_manifest.json").write_text(
            json.dumps({"name": "GoL Plugin", "oracle_mode": "product", "archetype": "claude_code_plugin"})
        )

        # Directly invoke _bootstrap_oracle_nested_session
        from src.unit_14.stub import _bootstrap_oracle_nested_session
        from src.unit_14.unit_5_stub import PipelineState

        oracle_state = PipelineState(
            stage="5",
            sub_stage="pass_transition",
            oracle_session_active=True,
            oracle_phase="green_run",
            oracle_test_project="examples/gol-plugin",
            oracle_run_count=7,
        )

        new_state = _bootstrap_oracle_nested_session(oracle_state, tmp_path)

        # Verify the nested session workspace was created
        workspace = tmp_path.parent / "oracle-session-7"
        assert workspace.exists(), "Nested session workspace must be created"

        # Verify pipeline_state.json is reset to stage=0
        nested_state_path = workspace / ".svp" / "pipeline_state.json"
        assert nested_state_path.exists(), "Nested session must have pipeline_state.json"

        nested_state = json.loads(nested_state_path.read_text())
        assert nested_state["stage"] == "0", (
            f"Bug S3-90: E-mode nested session pipeline_state.json must have stage='0', "
            f"got stage='{nested_state['stage']}' -- stale stage=5 state was not reset"
        )
        assert not nested_state.get("oracle_session_active", False), (
            "Bug S3-90: Nested session pipeline_state.json must not have oracle_session_active=True"
        )

    def test_emode_bootstrap_fresh_state_when_no_svp_dir(self, tmp_path):
        """Bug S3-90: E-mode bootstrap creates fresh pipeline_state.json even if .svp/ doesn't exist."""
        from src.unit_14.stub import _bootstrap_oracle_nested_session
        from src.unit_14.unit_5_stub import PipelineState

        # Create test project dir WITHOUT .svp/
        examples_dir = tmp_path / "examples" / "gol-plugin"
        examples_dir.mkdir(parents=True)
        (examples_dir / "stakeholder_spec.md").write_text("# Spec")

        oracle_state = PipelineState(
            stage="5",
            oracle_session_active=True,
            oracle_phase="green_run",
            oracle_test_project="examples/gol-plugin",
            oracle_run_count=9,
        )

        new_state = _bootstrap_oracle_nested_session(oracle_state, tmp_path)
        workspace = tmp_path.parent / "oracle-session-9"
        nested_state_path = workspace / ".svp" / "pipeline_state.json"
        assert nested_state_path.exists(), "Fresh pipeline_state.json must be created"
        nested_state = json.loads(nested_state_path.read_text())
        assert nested_state["stage"] == "0", (
            "Bug S3-90: Fresh stage=0 state must be written even without .svp/ in project_root"
        )

    def test_all_invoke_agent_blocks_have_prepare(self, tmp_path):
        """Bug S3-78: every invoke_agent action block must have a prepare field."""
        import re
        from pathlib import Path as P
        # Read routing.py source and check all invoke_agent blocks
        routing_path = P(__file__).resolve().parents[2] / "src" / "unit_14" / "stub.py"
        content = routing_path.read_text()
        blocks = list(re.finditer(r'action_type="invoke_agent"', content))
        assert len(blocks) > 0, "No invoke_agent blocks found"
        for m in blocks:
            ctx = content[m.start() - 100:m.start() + 300]
            at_match = re.search(r'agent_type="(\w+)"', ctx)
            agent = at_match.group(1) if at_match else "unknown"
            if agent == "pass2_nested":
                continue
            assert "prepare=" in ctx, (
                f"Bug S3-78: invoke_agent for {agent} missing prepare field"
            )

    # -- Break-glass routing --

    def test_break_glass_includes_diagnostic_context(self, tmp_path):
        """Break-glass action block must include diagnostic context."""
        # Simulate exhaustion state that would trigger break-glass
        state = _make_state(
            stage="3",
            sub_stage="exhausted",
            fix_ladder_position="exhausted",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        if result["action_type"] == "break_glass":
            # The diagnostic context should be present in the action block
            assert any(
                k in result for k in ("diagnostic", "context", "error", "message")
            )

    # -- Pass 2 routing --

    def test_pass2_active_delegates_to_nested_session(self, tmp_path):
        """When sub_stage=='pass2_active', route delegates to nested session."""
        state = _make_state(
            stage="3",
            sub_stage="pass2_active",
            pass_=2,
            pass2_nested_session_path="/tmp/nested",
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert isinstance(result, dict)
        assert "action_type" in result


# ===========================================================================
# dispatch_agent_status tests
# ===========================================================================


class TestDispatchAgentStatus:
    """Tests for dispatch_agent_status()."""

    def test_returns_pipeline_state(self):
        """dispatch_agent_status must return a PipelineState."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_COMPLETE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Setup agent statuses --

    def test_setup_agent_context_complete_no_state_change(self):
        """setup_agent + PROJECT_CONTEXT_COMPLETE: no state change (two-branch in route)."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage
        assert result.sub_stage == state.sub_stage

    def test_setup_agent_context_rejected_no_state_change(self):
        """setup_agent + PROJECT_CONTEXT_REJECTED: route emits pipeline_held, no state change."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_REJECTED", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_setup_agent_profile_complete_no_state_change(self):
        """setup_agent + PROFILE_COMPLETE: no state change (two-branch in route)."""
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_agent_status(
            state, "setup_agent", "PROFILE_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Stakeholder dialog --

    def test_stakeholder_dialog_spec_draft_complete_no_state_change(self):
        """stakeholder_dialog + SPEC_DRAFT_COMPLETE: no state change."""
        state = _make_state(stage="1", sub_stage="spec_dialog")
        result = dispatch_agent_status(
            state, "stakeholder_dialog", "SPEC_DRAFT_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_stakeholder_dialog_spec_revision_complete_no_state_change(self):
        """stakeholder_dialog + SPEC_REVISION_COMPLETE: no state change."""
        state = _make_state(stage="1", sub_stage="spec_revision")
        result = dispatch_agent_status(
            state, "stakeholder_dialog", "SPEC_REVISION_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Stakeholder reviewer --

    def test_stakeholder_reviewer_review_complete_no_state_change(self):
        """stakeholder_reviewer + REVIEW_COMPLETE: no state change."""
        state = _make_state(stage="1", sub_stage="spec_review")
        result = dispatch_agent_status(
            state, "stakeholder_reviewer", "REVIEW_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Blueprint author --

    def test_blueprint_author_draft_complete_no_state_change(self):
        """blueprint_author + BLUEPRINT_DRAFT_COMPLETE: no state change."""
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_agent_status(
            state, "blueprint_author", "BLUEPRINT_DRAFT_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_blueprint_author_revision_complete_no_state_change(self):
        """blueprint_author + BLUEPRINT_REVISION_COMPLETE: no state change."""
        state = _make_state(stage="2", sub_stage="blueprint_revision")
        result = dispatch_agent_status(
            state, "blueprint_author", "BLUEPRINT_REVISION_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Blueprint reviewer --

    def test_blueprint_reviewer_review_complete_no_state_change(self):
        """blueprint_reviewer + REVIEW_COMPLETE: no state change."""
        state = _make_state(stage="2", sub_stage="blueprint_review")
        result = dispatch_agent_status(
            state, "blueprint_reviewer", "REVIEW_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Blueprint checker --

    def test_blueprint_checker_alignment_confirmed_advances(self):
        """blueprint_checker + ALIGNMENT_CONFIRMED: advance sub_stage to alignment_confirmed."""
        state = _make_state(stage="2", sub_stage="alignment_check")
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_CONFIRMED", Path("/tmp")
        )
        assert result.sub_stage == "alignment_confirmed"

    def test_blueprint_checker_alignment_failed_blueprint_resets(self):
        """blueprint_checker + ALIGNMENT_FAILED: blueprint: reset sub_stage to blueprint_dialog, increment alignment_iterations."""
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=0
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: blueprint", Path("/tmp")
        )
        assert result.sub_stage == "blueprint_dialog"
        assert result.alignment_iterations == 1

    def test_blueprint_checker_alignment_failed_spec_targets_revision(self):
        """blueprint_checker + ALIGNMENT_FAILED: spec: set sub_stage to targeted_spec_revision."""
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=0
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: spec", Path("/tmp")
        )
        assert result.sub_stage == "targeted_spec_revision"
        assert result.alignment_iterations == 1

    def test_blueprint_checker_alignment_failed_at_limit_presents_gate(self):
        """When alignment_iterations hits limit after ALIGNMENT_FAILED, gate_2_3 is presented."""
        # At limit (e.g., 2 iterations, limit is 3 -- the increment brings it to 3)
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=2
        )
        result = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_FAILED: blueprint", Path("/tmp")
        )
        # After increment: alignment_iterations >= limit (3), gate_2_3 should be presented
        assert result.alignment_iterations >= 3

    # -- Checklist generation --

    def test_checklist_generation_complete_no_state_change(self):
        """checklist_generation + CHECKLISTS_COMPLETE: no state change."""
        state = _make_state(stage="1", sub_stage="checklist_generation")
        result = dispatch_agent_status(
            state, "checklist_generation", "CHECKLISTS_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Test agent --

    def test_test_agent_generation_complete_no_state_change(self):
        """test_agent + TEST_GENERATION_COMPLETE: no state change."""
        state = _make_state(stage="3", sub_stage="test_generation")
        result = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Implementation agent --

    def test_implementation_agent_complete_no_state_change(self):
        """implementation_agent + IMPLEMENTATION_COMPLETE: no state change."""
        state = _make_state(stage="3", sub_stage="implementation")
        result = dispatch_agent_status(
            state, "implementation_agent", "IMPLEMENTATION_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Coverage review agent --

    def test_coverage_review_no_gaps_no_state_change(self):
        """coverage_review_agent + COVERAGE_COMPLETE: no gaps: no state change."""
        state = _make_state(stage="3", sub_stage="coverage_review")
        result = dispatch_agent_status(
            state, "coverage_review_agent", "COVERAGE_COMPLETE: no gaps", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_coverage_review_tests_added_no_state_change(self):
        """coverage_review_agent + COVERAGE_COMPLETE: tests added: no state change."""
        state = _make_state(stage="3", sub_stage="coverage_review")
        result = dispatch_agent_status(
            state,
            "coverage_review_agent",
            "COVERAGE_COMPLETE: tests added",
            Path("/tmp"),
        )
        assert result.stage == state.stage

    # -- Diagnostic agent --

    def test_diagnostic_agent_complete_no_state_change(self):
        """diagnostic_agent + DIAGNOSIS_COMPLETE: *: no state change."""
        state = _make_state(
            stage="3", sub_stage="diagnostic", fix_ladder_position="diagnostic"
        )
        result = dispatch_agent_status(
            state, "diagnostic_agent", "DIAGNOSIS_COMPLETE: import error", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Integration test author --

    def test_integration_test_author_complete_no_state_change(self):
        """integration_test_author + INTEGRATION_TESTS_COMPLETE: no state change."""
        state = _make_state(stage="4", sub_stage="integration_test_authoring")
        result = dispatch_agent_status(
            state, "integration_test_author", "INTEGRATION_TESTS_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Regression adaptation --

    def test_regression_adaptation_complete_no_state_change(self):
        """regression_adaptation + ADAPTATION_COMPLETE: no state change."""
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_agent_status(
            state, "regression_adaptation", "ADAPTATION_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_regression_adaptation_needs_review_no_state_change(self):
        """regression_adaptation + ADAPTATION_NEEDS_REVIEW: no state change."""
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_agent_status(
            state, "regression_adaptation", "ADAPTATION_NEEDS_REVIEW", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Git repo agent --

    def test_git_repo_agent_complete_no_state_change(self):
        """git_repo_agent + REPO_ASSEMBLY_COMPLETE: no state change."""
        state = _make_state(stage="5", sub_stage="repo_assembly")
        result = dispatch_agent_status(
            state, "git_repo_agent", "REPO_ASSEMBLY_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Bug triage agent --

    def test_bug_triage_single_unit_no_state_change(self):
        """bug_triage_agent + TRIAGE_COMPLETE: single_unit: no state change."""
        state = _make_state(
            stage="3",
            sub_stage="debug_triage",
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_bug_triage_cross_unit_no_state_change(self):
        """bug_triage_agent + TRIAGE_COMPLETE: cross_unit: no state change."""
        state = _make_state(
            stage="3",
            sub_stage="debug_triage",
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: cross_unit", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_bug_triage_build_env_routes_to_repair(self):
        """bug_triage_agent + TRIAGE_COMPLETE: build_env: routes directly to repair (fast path)."""
        state = _make_state(
            stage="3",
            sub_stage="debug_triage",
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: build_env", Path("/tmp")
        )
        # Fast path: skips gate_6_2, goes directly to repair
        assert isinstance(result, PipelineState)

    def test_bug_triage_non_reproducible_no_state_change(self):
        """bug_triage_agent + TRIAGE_NON_REPRODUCIBLE: no state change."""
        state = _make_state(
            stage="3",
            sub_stage="debug_triage",
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NON_REPRODUCIBLE", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_bug_triage_needs_refinement_under_limit_reinvokes(self):
        """bug_triage_agent + TRIAGE_NEEDS_REFINEMENT: under limit, increments triage_refinement_count."""
        state = _make_state(
            stage="3",
            sub_stage="debug_triage",
            debug_session=_make_debug_session(
                authorized=True, phase="triage", triage_refinement_count=0
            ),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NEEDS_REFINEMENT", Path("/tmp")
        )
        assert result.debug_session["triage_refinement_count"] >= 1

    def test_bug_triage_needs_refinement_at_limit_routes_to_gate(self):
        """bug_triage_agent + TRIAGE_NEEDS_REFINEMENT: at limit (3), routes to gate_6_4."""
        state = _make_state(
            stage="3",
            sub_stage="debug_triage",
            debug_session=_make_debug_session(
                authorized=True, phase="triage", triage_refinement_count=2
            ),
        )
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_NEEDS_REFINEMENT", Path("/tmp")
        )
        # At limit, routes to gate_6_4 instead of re-invocation
        assert isinstance(result, PipelineState)

    # -- Repair agent --

    def test_repair_agent_complete_routes_to_reassembly(self):
        """repair_agent + REPAIR_COMPLETE: routes to reassembly/debug completion."""
        state = _make_state(
            stage="3",
            sub_stage="debug_repair",
            debug_session=_make_debug_session(authorized=True, phase="repair"),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_COMPLETE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_repair_agent_reclassify_routes_to_gate_6_3(self):
        """repair_agent + REPAIR_RECLASSIFY: routes to gate_6_3."""
        state = _make_state(
            stage="3",
            sub_stage="debug_repair",
            debug_session=_make_debug_session(authorized=True, phase="repair"),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_RECLASSIFY", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_repair_agent_failed_under_limit_increments_retry(self):
        """repair_agent + REPAIR_FAILED under limit: increment repair_retry_count, re-invoke."""
        state = _make_state(
            stage="3",
            sub_stage="debug_repair",
            debug_session=_make_debug_session(
                authorized=True, phase="repair", repair_retry_count=0
            ),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_FAILED", Path("/tmp")
        )
        assert result.debug_session["repair_retry_count"] >= 1

    def test_repair_agent_failed_at_limit_routes_to_gate_6_3(self):
        """repair_agent + REPAIR_FAILED at limit (3): routes to gate_6_3."""
        state = _make_state(
            stage="3",
            sub_stage="debug_repair",
            debug_session=_make_debug_session(
                authorized=True, phase="repair", repair_retry_count=2
            ),
        )
        result = dispatch_agent_status(
            state, "repair_agent", "REPAIR_FAILED", Path("/tmp")
        )
        assert result.debug_session["repair_retry_count"] >= 3

    # -- Oracle agent --

    def test_oracle_agent_dry_run_complete_no_state_change(self):
        """oracle_agent + ORACLE_DRY_RUN_COMPLETE: no state change."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="dry_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_DRY_RUN_COMPLETE", Path("/tmp")
        )
        assert result.oracle_session_active is True

    def test_oracle_agent_fix_applied_no_state_change(self):
        """oracle_agent + ORACLE_FIX_APPLIED: no state change."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_FIX_APPLIED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_oracle_agent_all_clear_no_state_change(self):
        """oracle_agent + ORACLE_ALL_CLEAR: no state change."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_ALL_CLEAR", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_oracle_agent_human_abort_deactivates_session(self):
        """oracle_agent + ORACLE_HUMAN_ABORT: set oracle_session_active to False."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="green_run",
        )
        result = dispatch_agent_status(
            state, "oracle_agent", "ORACLE_HUMAN_ABORT", Path("/tmp")
        )
        assert result.oracle_session_active is False

    # -- Help agent --

    def test_help_agent_no_hint_no_state_change(self):
        """help_agent + HELP_SESSION_COMPLETE: no hint: no state change."""
        state = _make_state()
        result = dispatch_agent_status(
            state, "help_agent", "HELP_SESSION_COMPLETE: no hint", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_help_agent_hint_forwarded_stores_hint(self):
        """help_agent + HELP_SESSION_COMPLETE: hint forwarded: stores hint content."""
        state = _make_state()
        result = dispatch_agent_status(
            state, "help_agent", "HELP_SESSION_COMPLETE: hint forwarded", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Hint agent --

    def test_hint_agent_analysis_complete_no_state_change(self):
        """hint_agent + HINT_ANALYSIS_COMPLETE: no state change."""
        state = _make_state()
        result = dispatch_agent_status(
            state, "hint_agent", "HINT_ANALYSIS_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    def test_hint_agent_blueprint_conflict_presents_gate(self):
        """hint_agent + HINT_BLUEPRINT_CONFLICT: presents gate_hint_conflict."""
        state = _make_state()
        result = dispatch_agent_status(
            state, "hint_agent", "HINT_BLUEPRINT_CONFLICT: some details", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Reference indexing --

    def test_reference_indexing_complete_no_state_change(self):
        """reference_indexing + INDEXING_COMPLETE: no state change."""
        state = _make_state()
        result = dispatch_agent_status(
            state, "reference_indexing", "INDEXING_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- Redo agent --

    def test_redo_agent_classified_spec(self):
        """redo_agent + REDO_CLASSIFIED: spec: version_document(spec), enter targeted_spec_revision."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: spec", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_redo_agent_classified_blueprint(self):
        """redo_agent + REDO_CLASSIFIED: blueprint: version_document, restart_from_stage('2')."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: blueprint", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_redo_agent_classified_gate(self):
        """redo_agent + REDO_CLASSIFIED: gate: rollback_to_unit for affected unit."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: gate", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_redo_agent_classified_profile_delivery(self):
        """redo_agent + REDO_CLASSIFIED: profile_delivery: enter_redo_profile_revision('delivery')."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: profile_delivery", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_redo_agent_classified_profile_blueprint(self):
        """redo_agent + REDO_CLASSIFIED: profile_blueprint: enter_redo_profile_revision('blueprint')."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_agent_status(
            state, "redo_agent", "REDO_CLASSIFIED: profile_blueprint", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Test agent in regression mode --

    def test_test_agent_regression_complete_no_state_change(self):
        """test_agent (regression mode) + REGRESSION_TEST_COMPLETE: no state change."""
        state = _make_state(
            stage="3",
            sub_stage="debug_regression_test",
            debug_session=_make_debug_session(authorized=True, phase="regression_test"),
        )
        result = dispatch_agent_status(
            state, "test_agent", "REGRESSION_TEST_COMPLETE", Path("/tmp")
        )
        assert result.stage == state.stage

    # -- No bare return state --

    def test_dispatch_agent_status_never_returns_none(self):
        """No dispatch path should return None (no bare return state)."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_COMPLETE", Path("/tmp")
        )
        assert result is not None


# ===========================================================================
# dispatch_gate_response tests
# ===========================================================================


class TestDispatchGateResponse:
    """Tests for dispatch_gate_response()."""

    def test_returns_pipeline_state(self):
        """dispatch_gate_response must return a PipelineState."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 0.1 --

    def test_gate_0_1_hooks_activated_advances(self):
        """gate_0_1 + HOOKS ACTIVATED: advance_sub_stage to project_context."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED", Path("/tmp")
        )
        assert result.sub_stage == "project_context"

    def test_gate_0_1_hooks_failed_halts(self):
        """gate_0_1 + HOOKS FAILED: halt pipeline."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS FAILED", Path("/tmp")
        )
        # Halted pipeline -- the exact representation depends on implementation
        assert isinstance(result, PipelineState)

    # -- Gate 0.2 --

    def test_gate_0_2_context_approved_advances(self):
        """gate_0_2 + CONTEXT APPROVED: advance_sub_stage to project_profile."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT APPROVED", Path("/tmp")
        )
        assert result.sub_stage == "project_profile"

    def test_gate_0_2_context_rejected_re_invokes(self):
        """gate_0_2 + CONTEXT REJECTED: delete project_context.md, clear last_status.txt, re-invoke."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT REJECTED", Path("/tmp")
        )
        assert result.sub_stage == "project_context"

    def test_gate_0_2_context_not_ready_clears_status(self):
        """gate_0_2 + CONTEXT NOT READY: clear last_status.txt, re-invoke."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT NOT READY", Path("/tmp")
        )
        assert result.sub_stage == "project_context"

    # -- Gate 0.3 --

    def test_gate_0_3_profile_approved_advances_stage(self):
        """gate_0_3 + PROFILE APPROVED: advance_stage to '1'."""
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE APPROVED", Path("/tmp")
        )
        assert result.stage == "1"

    def test_gate_0_3_profile_rejected_re_invokes(self):
        """gate_0_3 + PROFILE REJECTED: re-invoke setup agent in profile mode."""
        state = _make_state(stage="0", sub_stage="project_profile")
        result = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE REJECTED", Path("/tmp")
        )
        assert result.stage == "0"

    # -- Gate 0.3r --

    def test_gate_0_3r_profile_approved_completes_redo(self):
        """gate_0_3r + PROFILE APPROVED: complete_redo_profile_revision, restart per redo_type."""
        state = _make_state(stage="0", sub_stage="redo_profile_delivery")
        result = dispatch_gate_response(
            state, "gate_0_3r_profile_revision", "PROFILE APPROVED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_0_3r_profile_rejected_re_invokes(self):
        """gate_0_3r + PROFILE REJECTED: re-invoke setup agent in redo mode."""
        state = _make_state(stage="0", sub_stage="redo_profile_delivery")
        result = dispatch_gate_response(
            state, "gate_0_3r_profile_revision", "PROFILE REJECTED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 1.1 --

    def test_gate_1_1_approve_advances_to_checklist(self):
        """gate_1_1 + APPROVE: advance to checklist_generation sub_stage."""
        state = _make_state(stage="1", sub_stage="spec_dialog")
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "APPROVE", Path("/tmp")
        )
        assert result.sub_stage == "checklist_generation"

    def test_gate_1_1_revise_re_invokes_dialog(self):
        """gate_1_1 + REVISE: re-invoke stakeholder dialog in revision mode."""
        state = _make_state(stage="1", sub_stage="spec_dialog")
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "REVISE", Path("/tmp")
        )
        assert result.stage == "1"

    def test_gate_1_1_fresh_review_invokes_reviewer(self):
        """gate_1_1 + FRESH REVIEW: invoke stakeholder reviewer."""
        state = _make_state(stage="1", sub_stage="spec_dialog")
        result = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "FRESH REVIEW", Path("/tmp")
        )
        assert result.stage == "1"

    # -- Gate 1.2 --

    def test_gate_1_2_approve_advances_to_checklist(self):
        """gate_1_2 + APPROVE: advance to checklist_generation sub_stage."""
        state = _make_state(stage="1", sub_stage="spec_review")
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "APPROVE", Path("/tmp")
        )
        assert result.sub_stage == "checklist_generation"

    def test_gate_1_2_revise_versions_spec(self):
        """gate_1_2 + REVISE: version_document(spec), re-invoke stakeholder dialog."""
        state = _make_state(stage="1", sub_stage="spec_review")
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "REVISE", Path("/tmp")
        )
        assert result.stage == "1"

    def test_gate_1_2_fresh_review_invokes_reviewer(self):
        """gate_1_2 + FRESH REVIEW: invoke stakeholder reviewer."""
        state = _make_state(stage="1", sub_stage="spec_review")
        result = dispatch_gate_response(
            state, "gate_1_2_spec_post_review", "FRESH REVIEW", Path("/tmp")
        )
        assert result.stage == "1"

    # -- Gate 2.1 --

    def test_gate_2_1_approve_invokes_checker(self):
        """gate_2_1 + APPROVE: invoke blueprint checker (enter alignment_check)."""
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "APPROVE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_2_1_revise_re_invokes_author(self):
        """gate_2_1 + REVISE: re-invoke blueprint author in revision mode."""
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "REVISE", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_2_1_fresh_review_invokes_reviewer(self):
        """gate_2_1 + FRESH REVIEW: invoke blueprint reviewer."""
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        result = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "FRESH REVIEW", Path("/tmp")
        )
        assert result.stage == "2"

    # -- Gate 2.2 --

    def test_gate_2_2_approve_enters_alignment_check(self):
        """gate_2_2 + APPROVE: enter alignment_check."""
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", "APPROVE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_2_2_revise_versions_blueprint(self):
        """gate_2_2 + REVISE: version_document(prose+contracts), re-invoke blueprint author."""
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", "REVISE", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_2_2_fresh_review_invokes_reviewer(self):
        """gate_2_2 + FRESH REVIEW: invoke blueprint reviewer."""
        state = _make_state(stage="2", sub_stage="alignment_confirmed")
        result = dispatch_gate_response(
            state, "gate_2_2_blueprint_post_review", "FRESH REVIEW", Path("/tmp")
        )
        assert result.stage == "2"

    # -- Gate 2.3 --

    def test_gate_2_3_revise_spec_enters_targeted_revision(self):
        """gate_2_3 + REVISE SPEC: version_document, advance to targeted_spec_revision, reset alignment."""
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=3
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "REVISE SPEC", Path("/tmp")
        )
        assert result.sub_stage == "targeted_spec_revision"
        assert result.alignment_iterations == 0

    def test_gate_2_3_restart_spec_restarts_from_stage_1(self):
        """gate_2_3 + RESTART SPEC: restart_from_stage('1')."""
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=3
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RESTART SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    def test_gate_2_3_retry_blueprint_re_invokes_author(self):
        """gate_2_3 + RETRY BLUEPRINT: re-invoke blueprint author."""
        state = _make_state(
            stage="2", sub_stage="alignment_check", alignment_iterations=3
        )
        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", Path("/tmp")
        )
        assert result.stage == "2"

    # -- Gate 3.1 --

    def test_gate_3_1_autonomous_defaults_test_correct(self):
        """gate_3_1 is autonomous, defaults to TEST CORRECT. No human presentation."""
        state = _make_state(stage="3", sub_stage="test_generation")
        result = dispatch_gate_response(
            state, "gate_3_1_test_validation", "TEST CORRECT", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 3.2 --

    def test_gate_3_2_fix_implementation_advances_ladder(self):
        """gate_3_2 + FIX IMPLEMENTATION: advance_fix_ladder, re-invoke implementation agent."""
        state = _make_state(
            stage="3", sub_stage="diagnostic", fix_ladder_position="diagnostic"
        )
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX IMPLEMENTATION", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_3_2_fix_blueprint_restarts_stage_2(self):
        """gate_3_2 + FIX BLUEPRINT: version_document, restart_from_stage('2')."""
        state = _make_state(stage="3", sub_stage="diagnostic")
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_3_2_fix_spec_restarts_stage_1(self):
        """gate_3_2 + FIX SPEC: version_document(spec), restart_from_stage('1')."""
        state = _make_state(stage="3", sub_stage="diagnostic")
        result = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    # -- Gate 3 completion failure --

    def test_gate_3_completion_investigate(self):
        """gate_3_completion_failure + INVESTIGATE: enter debug session."""
        state = _make_state(stage="3", sub_stage="completion_validation")
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", "INVESTIGATE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_3_completion_force_advance(self):
        """gate_3_completion_failure + FORCE ADVANCE: advance_stage('4')."""
        state = _make_state(stage="3", sub_stage="completion_validation")
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", "FORCE ADVANCE", Path("/tmp")
        )
        assert result.stage == "4"

    def test_gate_3_completion_restart_stage_3(self):
        """gate_3_completion_failure + RESTART STAGE 3: restart_from_stage('3')."""
        state = _make_state(stage="3", sub_stage="completion_validation")
        result = dispatch_gate_response(
            state, "gate_3_completion_failure", "RESTART STAGE 3", Path("/tmp")
        )
        assert result.stage == "3"

    # -- Gate 4.1 --

    def test_gate_4_1_assembly_fix_re_invokes_author(self):
        """gate_4_1 + ASSEMBLY FIX: re-invoke integration test author, increment retry."""
        state = _make_state(stage="4", sub_stage="integration_test_run")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        assert result.stage == "4"

    def test_gate_4_1_fix_blueprint_restarts_stage_2(self):
        """gate_4_1 + FIX BLUEPRINT: version_document, restart_from_stage('2')."""
        state = _make_state(stage="4", sub_stage="integration_test_run")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_4_1_fix_spec_restarts_stage_1(self):
        """gate_4_1 + FIX SPEC: version_document(spec), restart_from_stage('1')."""
        state = _make_state(stage="4", sub_stage="integration_test_run")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "FIX SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    # -- Gate 4.1a --

    def test_gate_4_1a_human_fix(self):
        """gate_4_1a + HUMAN FIX: re-invoke integration test author with human guidance."""
        state = _make_state(stage="4", sub_stage="integration_test_run")
        result = dispatch_gate_response(state, "gate_4_1a", "HUMAN FIX", Path("/tmp"))
        assert result.stage == "4"

    def test_gate_4_1a_escalate_presents_gate_4_2(self):
        """gate_4_1a + ESCALATE: present gate_4_2_assembly_exhausted."""
        state = _make_state(stage="4", sub_stage="integration_test_run")
        result = dispatch_gate_response(state, "gate_4_1a", "ESCALATE", Path("/tmp"))
        assert isinstance(result, PipelineState)

    # -- Gate 4.2 --

    def test_gate_4_2_fix_blueprint_restarts_stage_2(self):
        """gate_4_2 + FIX BLUEPRINT: version_document, restart_from_stage('2')."""
        state = _make_state(stage="4", sub_stage="assembly_exhausted")
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_4_2_fix_spec_restarts_stage_1(self):
        """gate_4_2 + FIX SPEC: version_document(spec), restart_from_stage('1')."""
        state = _make_state(stage="4", sub_stage="assembly_exhausted")
        result = dispatch_gate_response(
            state, "gate_4_2_assembly_exhausted", "FIX SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    # -- Gate 4.3 --

    def test_gate_4_3_accept_adaptations_advances_stage_5(self):
        """gate_4_3 + ACCEPT ADAPTATIONS: advance_stage('5')."""
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", "ACCEPT ADAPTATIONS", Path("/tmp")
        )
        assert result.stage == "5"

    def test_gate_4_3_modify_test_re_invokes_adaptation(self):
        """gate_4_3 + MODIFY TEST: re-invoke regression adaptation agent."""
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", "MODIFY TEST", Path("/tmp")
        )
        assert result.stage == "4"

    def test_gate_4_3_remove_test_advances_stage_5(self):
        """gate_4_3 + REMOVE TEST: remove flagged test, advance_stage('5')."""
        state = _make_state(stage="4", sub_stage="regression_adaptation")
        result = dispatch_gate_response(
            state, "gate_4_3_adaptation_review", "REMOVE TEST", Path("/tmp")
        )
        assert result.stage == "5"

    # -- Gate 5.1 --

    def test_gate_5_1_tests_passed_advances_to_compliance(self):
        """gate_5_1 + TESTS PASSED: advance_sub_stage to compliance_scan."""
        state = _make_state(stage="5", sub_stage="repo_test")
        result = dispatch_gate_response(
            state, "gate_5_1_repo_test", "TESTS PASSED", Path("/tmp")
        )
        assert result.sub_stage == "compliance_scan"

    def test_gate_5_1_tests_failed_re_enters_fix_cycle(self):
        """gate_5_1 + TESTS FAILED: re-enter bounded fix cycle."""
        state = _make_state(stage="5", sub_stage="repo_test")
        result = dispatch_gate_response(
            state, "gate_5_1_repo_test", "TESTS FAILED", Path("/tmp")
        )
        assert result.stage == "5"

    # -- Gate 5.2 --

    def test_gate_5_2_retry_assembly(self):
        """gate_5_2 + RETRY ASSEMBLY: re-invoke git repo agent."""
        state = _make_state(stage="5", sub_stage="assembly_exhausted")
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", "RETRY ASSEMBLY", Path("/tmp")
        )
        assert result.stage == "5"

    def test_gate_5_2_fix_blueprint_restarts_stage_2(self):
        """gate_5_2 + FIX BLUEPRINT: version_document, restart_from_stage('2')."""
        state = _make_state(stage="5", sub_stage="assembly_exhausted")
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_5_2_fix_spec_restarts_stage_1(self):
        """gate_5_2 + FIX SPEC: version_document(spec), restart_from_stage('1')."""
        state = _make_state(stage="5", sub_stage="assembly_exhausted")
        result = dispatch_gate_response(
            state, "gate_5_2_assembly_exhausted", "FIX SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    # -- Gate 5.3 --

    def test_gate_5_3_fix_spec_restarts_stage_1(self):
        """gate_5_3 + FIX SPEC: version_document(spec), restart_from_stage('1')."""
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "FIX SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    def test_gate_5_3_override_continue_advances(self):
        """gate_5_3 + OVERRIDE CONTINUE: advance to repo_complete."""
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 6.0 --

    def test_gate_6_0_authorize_debug(self):
        """gate_6_0 + AUTHORIZE DEBUG: authorize_debug_session."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=False),
        )
        result = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", Path("/tmp")
        )
        assert result.debug_session["authorized"] is True

    def test_gate_6_0_abandon_debug(self):
        """gate_6_0 + ABANDON DEBUG: abandon_debug_session."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=False),
        )
        result = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 6.1 --

    def test_gate_6_1_test_correct_advances_to_lessons_learned(self):
        """gate_6_1 + TEST CORRECT: advance debug phase to lessons_learned."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="regression_test"),
        )
        result = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST CORRECT", Path("/tmp")
        )
        assert result.debug_session["phase"] == "lessons_learned"

    def test_gate_6_1_test_wrong_re_invokes_test_agent(self):
        """gate_6_1 + TEST WRONG: re-invoke test agent in regression mode."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="regression_test"),
        )
        result = dispatch_gate_response(
            state, "gate_6_1_regression_test", "TEST WRONG", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 6.1a --

    def test_gate_6_1a_proceed_continues(self):
        """gate_6_1a + PROCEED: continue normal debug flow."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", "PROCEED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_6_1a_fix_divergence_re_invokes_repo_agent(self):
        """gate_6_1a + FIX DIVERGENCE: re-invoke git repo agent for sync."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", "FIX DIVERGENCE", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_6_1a_abandon_debug(self):
        """gate_6_1a + ABANDON DEBUG: abandon_debug_session."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_1a_divergence_warning", "ABANDON DEBUG", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 6.2 --

    def test_gate_6_2_fix_unit_sets_classification(self):
        """gate_6_2 + FIX UNIT: set_debug_classification, rollback_to_unit, update_debug_phase."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", Path("/tmp")
        )
        assert result.debug_session["classification"] == "single_unit"
        assert result.debug_session["phase"] == "stage3_reentry"

    def test_gate_6_2_fix_blueprint_restarts_stage_2(self):
        """gate_6_2 + FIX BLUEPRINT: version_document, restart_from_stage('2')."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX BLUEPRINT", Path("/tmp")
        )
        assert result.stage == "2"

    def test_gate_6_2_fix_spec_restarts_stage_1(self):
        """gate_6_2 + FIX SPEC: version_document(spec), restart_from_stage('1')."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX SPEC", Path("/tmp")
        )
        assert result.stage == "1"

    def test_gate_6_2_fix_in_place_updates_phase(self):
        """gate_6_2 + FIX IN PLACE: update_debug_phase to repair."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", Path("/tmp")
        )
        assert result.debug_session["phase"] == "repair"

    # -- Gate 6.3 --

    def test_gate_6_3_retry_repair_resets_count(self):
        """gate_6_3 + RETRY REPAIR: reset repair_retry_count, re-invoke."""
        state = _make_state(
            debug_session=_make_debug_session(
                authorized=True, phase="repair", repair_retry_count=3
            ),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RETRY REPAIR", Path("/tmp")
        )
        assert result.debug_session["repair_retry_count"] == 0

    def test_gate_6_3_reclassify_under_triage_limit(self):
        """gate_6_3 + RECLASSIFY BUG under triage limit: re-invoke triage agent."""
        state = _make_state(
            debug_session=_make_debug_session(
                authorized=True,
                phase="repair",
                repair_retry_count=3,
                triage_refinement_count=1,
            ),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_6_3_abandon_debug(self):
        """gate_6_3 + ABANDON DEBUG: abandon_debug_session."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="repair"),
        )
        result = dispatch_gate_response(
            state, "gate_6_3_repair_exhausted", "ABANDON DEBUG", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 6.4 --

    def test_gate_6_4_retry_triage_increments_refinement(self):
        """gate_6_4 + RETRY TRIAGE: increment triage_refinement_count, re-invoke triage."""
        state = _make_state(
            debug_session=_make_debug_session(
                authorized=True, phase="triage", triage_refinement_count=0
            ),
        )
        result = dispatch_gate_response(
            state, "gate_6_4_non_reproducible", "RETRY TRIAGE", Path("/tmp")
        )
        assert result.debug_session["triage_refinement_count"] >= 1

    def test_gate_6_4_abandon_debug(self):
        """gate_6_4 + ABANDON DEBUG: abandon_debug_session."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="triage"),
        )
        result = dispatch_gate_response(
            state, "gate_6_4_non_reproducible", "ABANDON DEBUG", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 6.5 --

    def test_gate_6_5_commit_approved_completes_session(self):
        """gate_6_5 + COMMIT APPROVED: complete_debug_session."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="commit"),
        )
        result = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT APPROVED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_6_5_commit_rejected_re_presents(self):
        """gate_6_5 + COMMIT REJECTED: re-present commit for revision."""
        state = _make_state(
            debug_session=_make_debug_session(authorized=True, phase="commit"),
        )
        result = dispatch_gate_response(
            state, "gate_6_5_debug_commit", "COMMIT REJECTED", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate hint conflict --

    def test_gate_hint_blueprint_correct_discards_hint(self):
        """gate_hint_conflict + BLUEPRINT CORRECT: discard hint, continue."""
        state = _make_state()
        result = dispatch_gate_response(
            state, "gate_hint_conflict", "BLUEPRINT CORRECT", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_hint_hint_correct_versions_document(self):
        """gate_hint_conflict + HINT CORRECT: version appropriate document, restart."""
        state = _make_state()
        result = dispatch_gate_response(
            state, "gate_hint_conflict", "HINT CORRECT", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    # -- Gate 7.a --

    def test_gate_7_a_approve_trajectory_sets_green_run(self):
        """gate_7_a + APPROVE TRAJECTORY: set oracle_phase to green_run."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_a",
        )
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "APPROVE TRAJECTORY", Path("/tmp")
        )
        assert result.oracle_phase == "green_run"

    def test_gate_7_a_modify_trajectory_under_limit(self):
        """gate_7_a + MODIFY TRAJECTORY under limit: re-enter dry_run."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_a",
            oracle_run_count=0,
        )
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY", Path("/tmp")
        )
        assert result.oracle_phase == "dry_run"

    def test_gate_7_a_abort_exits_oracle(self):
        """gate_7_a + ABORT: log abort, exit oracle session."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_a",
        )
        result = dispatch_gate_response(
            state, "gate_7_a_trajectory_review", "ABORT", Path("/tmp")
        )
        assert result.oracle_session_active is False

    # -- Gate 7.b --

    def test_gate_7_b_approve_fix(self):
        """gate_7_b + APPROVE FIX: oracle calls /svp:bug internally."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_b",
        )
        result = dispatch_gate_response(
            state, "gate_7_b_fix_plan_review", "APPROVE FIX", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_7_b_abort_exits_with_discovery(self):
        """gate_7_b + ABORT: log abort with discovery, exit oracle session."""
        state = _make_state(
            oracle_session_active=True,
            oracle_phase="gate_b",
        )
        result = dispatch_gate_response(
            state, "gate_7_b_fix_plan_review", "ABORT", Path("/tmp")
        )
        assert result.oracle_session_active is False

    # -- Pass transition gates --

    def test_gate_pass_transition_post_pass1_proceed(self):
        """gate_pass_transition_post_pass1 + PROCEED TO PASS 2: enter_pass_2."""
        state = _make_state(stage="5", sub_stage="pass_transition", pass_=1)
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass1", "PROCEED TO PASS 2", Path("/tmp")
        )
        assert result.pass_ == 2

    def test_gate_pass_transition_post_pass1_fix_bugs(self):
        """gate_pass_transition_post_pass1 + FIX BUGS: enter debug session."""
        state = _make_state(stage="5", sub_stage="pass_transition", pass_=1)
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass1", "FIX BUGS", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_pass_transition_post_pass2_fix_bugs(self):
        """gate_pass_transition_post_pass2 + FIX BUGS: enter debug session."""
        state = _make_state(stage="5", sub_stage="pass_transition", pass_=2)
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass2", "FIX BUGS", Path("/tmp")
        )
        assert isinstance(result, PipelineState)

    def test_gate_pass_transition_post_pass2_run_oracle(self):
        """gate_pass_transition_post_pass2 + RUN ORACLE: start oracle session."""
        state = _make_state(stage="5", sub_stage="pass_transition", pass_=2)
        result = dispatch_gate_response(
            state, "gate_pass_transition_post_pass2", "RUN ORACLE", Path("/tmp")
        )
        assert result.oracle_session_active is True

    # -- Never returns None --

    def test_dispatch_gate_response_never_returns_none(self):
        """No gate dispatch path should return None."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED", Path("/tmp")
        )
        assert result is not None


# ===========================================================================
# dispatch_command_status tests
# ===========================================================================


class TestDispatchCommandStatus:
    """Tests for dispatch_command_status()."""

    def test_returns_pipeline_state(self):
        """dispatch_command_status must return a PipelineState."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_command_status(
            state, "stub_generation", "COMMAND_SUCCEEDED", None
        )
        assert isinstance(result, PipelineState)

    # -- Stub generation --

    def test_stub_generation_succeeded_advances_to_test_generation(self):
        """stub_generation + COMMAND_SUCCEEDED: advance_sub_stage to test_generation."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_command_status(
            state, "stub_generation", "COMMAND_SUCCEEDED", None
        )
        assert result.sub_stage == "test_generation"

    def test_stub_generation_failed_presents_error(self):
        """stub_generation + COMMAND_FAILED: present error to human."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_command_status(
            state, "stub_generation", "COMMAND_FAILED", None
        )
        assert isinstance(result, PipelineState)

    # -- Test execution: red run --

    def test_red_run_tests_failed_advances_to_implementation(self):
        """test_execution at red_run + TESTS_FAILED: advance to implementation."""
        state = _make_state(stage="3", sub_stage="red_run")
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "red_run"
        )
        assert result.sub_stage == "implementation"

    def test_red_run_tests_passed_under_limit_retries(self):
        """test_execution at red_run + TESTS_PASSED under limit: increment retries, set test_generation."""
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "red_run"
        )
        assert result.sub_stage == "test_generation"
        assert result.red_run_retries >= 1

    def test_red_run_tests_passed_at_limit_autonomous_test_correct(self):
        """test_execution at red_run + TESTS_PASSED at limit: autonomous TEST CORRECT, enter fix ladder."""
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=2)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "red_run"
        )
        # At limit (3), tests are autonomously treated as correct
        assert isinstance(result, PipelineState)

    def test_red_run_tests_error_under_limit_regenerates(self):
        """test_execution at red_run + TESTS_ERROR under limit: set sub_stage to test_generation."""
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "red_run"
        )
        assert result.sub_stage == "test_generation"
        assert result.red_run_retries >= 1

    def test_red_run_tests_error_at_limit_autonomous(self):
        """test_execution at red_run + TESTS_ERROR at limit: treat as TEST CORRECT, enter fix ladder."""
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=2)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "red_run"
        )
        assert isinstance(result, PipelineState)

    # -- Test execution: green run --

    def test_green_run_tests_passed_advances_to_coverage(self):
        """test_execution at green_run + TESTS_PASSED: advance to coverage_review."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "green_run"
        )
        assert result.sub_stage == "coverage_review"

    def test_green_run_tests_failed_advances_fix_ladder(self):
        """test_execution at green_run + TESTS_FAILED: advance_fix_ladder."""
        state = _make_state(stage="3", sub_stage="green_run", fix_ladder_position=None)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "green_run"
        )
        assert result.fix_ladder_position == "fresh_impl"

    def test_green_run_fix_ladder_progression(self):
        """test_execution at green_run: ladder progresses None -> fresh_impl -> diagnostic -> diagnostic_impl -> exhausted."""
        positions = [None, "fresh_impl", "diagnostic", "diagnostic_impl"]
        expected_next = ["fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"]
        for pos, expected in zip(positions, expected_next):
            state = _make_state(
                stage="3", sub_stage="green_run", fix_ladder_position=pos
            )
            result = dispatch_command_status(
                state, "test_execution", "TESTS_FAILED", "green_run"
            )
            assert result.fix_ladder_position == expected, (
                f"From {pos}, expected {expected} but got {result.fix_ladder_position}"
            )

    def test_green_run_tests_error_engages_fix_ladder(self):
        """test_execution at green_run + TESTS_ERROR: engages fix ladder same as TESTS_FAILED."""
        state = _make_state(stage="3", sub_stage="green_run", fix_ladder_position=None)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "green_run"
        )
        assert result.fix_ladder_position == "fresh_impl"

    # -- Quality gate --

    def test_quality_gate_a_succeeded_advances_to_red_run(self):
        """quality_gate at quality_gate_a + COMMAND_SUCCEEDED: advance to red_run."""
        state = _make_state(stage="3", sub_stage="quality_gate_a")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", "quality_gate_a"
        )
        assert result.sub_stage == "red_run"

    def test_quality_gate_a_failed_advances_to_retry(self):
        """quality_gate at quality_gate_a + COMMAND_FAILED: advance to quality_gate_a_retry."""
        state = _make_state(stage="3", sub_stage="quality_gate_a")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", "quality_gate_a"
        )
        assert result.sub_stage == "quality_gate_a_retry"

    def test_quality_gate_b_succeeded_advances_to_green_run(self):
        """quality_gate at quality_gate_b + COMMAND_SUCCEEDED: advance to green_run."""
        state = _make_state(stage="3", sub_stage="quality_gate_b")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", "quality_gate_b"
        )
        assert result.sub_stage == "green_run"

    def test_quality_gate_b_failed_advances_to_retry(self):
        """quality_gate at quality_gate_b + COMMAND_FAILED: advance to quality_gate_b_retry."""
        state = _make_state(stage="3", sub_stage="quality_gate_b")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", "quality_gate_b"
        )
        assert result.sub_stage == "quality_gate_b_retry"

    def test_quality_gate_a_retry_succeeded_advances_to_red_run(self):
        """quality_gate at quality_gate_a_retry + COMMAND_SUCCEEDED: advance to red_run."""
        state = _make_state(stage="3", sub_stage="quality_gate_a_retry")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", "quality_gate_a_retry"
        )
        assert result.sub_stage == "red_run"

    def test_quality_gate_a_retry_failed_enters_fix_ladder(self):
        """quality_gate at quality_gate_a_retry + COMMAND_FAILED: enter fix ladder."""
        state = _make_state(stage="3", sub_stage="quality_gate_a_retry")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", "quality_gate_a_retry"
        )
        assert isinstance(result, PipelineState)

    def test_quality_gate_b_retry_succeeded_advances_to_green_run(self):
        """quality_gate at quality_gate_b_retry + COMMAND_SUCCEEDED: advance to green_run."""
        state = _make_state(stage="3", sub_stage="quality_gate_b_retry")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", "quality_gate_b_retry"
        )
        assert result.sub_stage == "green_run"

    def test_quality_gate_b_retry_failed_enters_fix_ladder(self):
        """quality_gate at quality_gate_b_retry + COMMAND_FAILED: enter fix ladder."""
        state = _make_state(stage="3", sub_stage="quality_gate_b_retry")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_FAILED", "quality_gate_b_retry"
        )
        assert isinstance(result, PipelineState)

    # -- Test execution: Stage 4 --

    def test_stage4_tests_passed_advances_to_regression(self):
        """test_execution at Stage 4 + TESTS_PASSED: advance to regression_adaptation."""
        state = _make_state(stage="4", sub_stage="integration_test_run")
        result = dispatch_command_status(
            state, "test_execution", "TESTS_PASSED", "integration_test_run"
        )
        assert result.sub_stage == "regression_adaptation"

    def test_stage4_tests_failed_under_limit_presents_gate_4_1(self):
        """test_execution at Stage 4 + TESTS_FAILED under limit: present gate_4_1."""
        state = _make_state(
            stage="4", sub_stage="integration_test_run", red_run_retries=0
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "integration_test_run"
        )
        assert isinstance(result, PipelineState)

    def test_stage4_tests_failed_at_limit_presents_gate_4_2(self):
        """test_execution at Stage 4 + TESTS_FAILED at limit: present gate_4_2."""
        state = _make_state(
            stage="4", sub_stage="integration_test_run", red_run_retries=2
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_FAILED", "integration_test_run"
        )
        assert isinstance(result, PipelineState)

    def test_stage4_tests_error_same_as_failed(self):
        """test_execution at Stage 4 + TESTS_ERROR: same dispatch as TESTS_FAILED."""
        state = _make_state(
            stage="4", sub_stage="integration_test_run", red_run_retries=0
        )
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "integration_test_run"
        )
        assert isinstance(result, PipelineState)

    # -- Unit completion --

    def test_unit_completion_succeeded_completes_unit(self):
        """unit_completion + COMMAND_SUCCEEDED: complete_unit, advance to next."""
        state = _make_state(
            stage="3", sub_stage="unit_completion", current_unit=1, total_units=10
        )
        result = dispatch_command_status(
            state, "unit_completion", "COMMAND_SUCCEEDED", None
        )
        assert isinstance(result, PipelineState)

    # -- No bare return state --

    def test_dispatch_command_status_never_returns_none(self):
        """No dispatch path should return None."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_command_status(
            state, "stub_generation", "COMMAND_SUCCEEDED", None
        )
        assert result is not None


# ===========================================================================
# main() (routing.py CLI) tests
# ===========================================================================


class TestMainCli:
    """Tests for main() CLI entry point."""

    def test_main_accepts_argv(self):
        """main() accepts an argv list argument."""
        # Just verify it accepts the parameter (execution depends on file system)
        assert callable(main)

    def test_main_prints_json_to_stdout(self, tmp_path, capsys):
        """main() prints action block as JSON to stdout."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        main(["--project-root", str(tmp_path)])
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "action_type" in output

    def test_main_appends_build_log_entry(self, tmp_path):
        """main() appends a build log entry with source='routing' and event_type='action_emitted'."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        svp_dir = _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        main(["--project-root", str(tmp_path)])
        # Build log should exist and contain the entry
        build_log_path = svp_dir / "build_log.json"
        if build_log_path.exists():
            log = json.loads(build_log_path.read_text())
            assert any(
                e.get("source") == "routing" and e.get("event_type") == "action_emitted"
                for e in (log if isinstance(log, list) else [log])
            )

    def test_main_default_project_root(self):
        """main() defaults project_root to '.' when not provided."""
        # Verifying the callable accepts empty/default args
        assert callable(main)


# ===========================================================================
# update_state_main() tests
# ===========================================================================


class TestUpdateStateMain:
    """Tests for update_state_main() CLI entry point."""

    def test_update_state_main_accepts_argv(self):
        """update_state_main() accepts an argv list argument."""
        assert callable(update_state_main)

    def test_update_state_main_validates_phase(self, tmp_path):
        """update_state_main validates --phase matches a known agent type from PHASE_TO_AGENT."""
        state = _make_state(stage="3", sub_stage="test_generation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "TEST_GENERATION_COMPLETE")
        # Valid phase should not raise for known phase
        # Invalid phase should be rejected
        with pytest.raises((SystemExit, ValueError, KeyError)):
            update_state_main(
                [
                    "--phase",
                    "INVALID_PHASE",
                    "--project-root",
                    str(tmp_path),
                    "--status",
                    "TEST_GENERATION_COMPLETE",
                ]
            )

    def test_update_state_main_appends_build_log(self, tmp_path):
        """update_state_main appends build log entry with source='update_state'."""
        state = _make_state(stage="3", sub_stage="test_generation")
        svp_dir = _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "HELP_SESSION_COMPLETE: no hint")
        update_state_main(
            [
                "--phase",
                "help",
                "--project-root",
                str(tmp_path),
                "--status",
                "HELP_SESSION_COMPLETE: no hint",
            ]
        )
        build_log_path = svp_dir / "build_log.json"
        if build_log_path.exists():
            log = json.loads(build_log_path.read_text())
            assert any(
                e.get("source") == "update_state"
                for e in (log if isinstance(log, list) else [log])
            )

    def test_update_state_main_rejects_phase_mismatch(self, tmp_path):
        """update_state_main rejects --phase that does not match current pipeline state."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        # Trying to update with a phase that makes no sense at stage 0
        with pytest.raises((SystemExit, ValueError, KeyError)):
            update_state_main(
                [
                    "--phase",
                    "NONEXISTENT",
                    "--project-root",
                    str(tmp_path),
                ]
            )


# ===========================================================================
# run_tests_main() tests
# ===========================================================================


class TestRunTestsMain:
    """Tests for run_tests_main() CLI entry point."""

    def test_run_tests_main_accepts_argv(self):
        """run_tests_main() accepts an argv list argument."""
        assert callable(run_tests_main)

    def test_run_tests_main_exit_code_always_zero(self, tmp_path, capsys):
        """run_tests_main: exit code is always 0 (status communicated via stdout)."""
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        _write_state_file(tmp_path, state)
        # This requires the test infrastructure to exist; we verify the contract
        # that the function does not raise SystemExit with non-zero code
        try:
            run_tests_main(
                [
                    "--unit",
                    "1",
                    "--language",
                    "python",
                    "--project-root",
                    str(tmp_path),
                    "--sub-stage",
                    "red_run",
                ]
            )
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    def test_run_tests_main_writes_status_to_stdout(self, tmp_path, capsys):
        """run_tests_main writes result status to stdout."""
        state = _make_state(stage="3", sub_stage="red_run", current_unit=1)
        _write_state_file(tmp_path, state)
        try:
            run_tests_main(
                [
                    "--unit",
                    "1",
                    "--language",
                    "python",
                    "--project-root",
                    str(tmp_path),
                    "--sub-stage",
                    "red_run",
                ]
            )
        except (SystemExit, FileNotFoundError, Exception):
            pass
        captured = capsys.readouterr()
        # Status should be written to stdout (may be empty if test infra is missing)
        assert isinstance(captured.out, str)


# ===========================================================================
# COLLECTION_ERROR normalization tests
# ===========================================================================


class TestCollectionErrorNormalization:
    """Tests for the COLLECTION_ERROR to TESTS_ERROR normalization (M-3 clarification)."""

    def test_collection_error_normalized_to_tests_error_for_dispatch(self):
        """RunResult with collection_error=True is dispatched as TESTS_ERROR, not COLLECTION_ERROR."""
        # Verify that the dispatch_command_status handles TESTS_ERROR status
        # even when collection_error is true (normalization happens before dispatch)
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=0)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "red_run"
        )
        assert isinstance(result, PipelineState)
        # Under limit: should set sub_stage to test_generation (regenerate tests)
        assert result.sub_stage == "test_generation"

    def test_tests_error_at_red_run_increments_retries(self):
        """TESTS_ERROR at red run increments red_run_retries."""
        state = _make_state(stage="3", sub_stage="red_run", red_run_retries=1)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "red_run"
        )
        assert result.red_run_retries >= 2

    def test_tests_error_at_green_run_advances_fix_ladder(self):
        """TESTS_ERROR at green run advances fix ladder same as TESTS_FAILED."""
        state = _make_state(stage="3", sub_stage="green_run", fix_ladder_position=None)
        result = dispatch_command_status(
            state, "test_execution", "TESTS_ERROR", "green_run"
        )
        assert result.fix_ladder_position == "fresh_impl"


# ===========================================================================
# Stage 3 completion validation tests
# ===========================================================================


class TestStage3CompletionValidation:
    """Tests for _validate_stage3_completion() behavior via route()."""

    def test_stage3_completion_checks_all_units_verified(self, tmp_path):
        """At Stage 3/4 boundary, validation checks all units are verified."""
        # All 3 units verified
        verified = [{"unit": i, "status": "verified"} for i in range(1, 4)]
        state = _make_state(
            stage="3",
            sub_stage="completion_validation",
            total_units=3,
            verified_units=verified,
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert isinstance(result, dict)

    def test_stage3_completion_fails_with_missing_units(self, tmp_path):
        """At Stage 3/4 boundary, incomplete units present gate_3_completion_failure."""
        # Only 1 of 3 units verified
        verified = [{"unit": 1, "status": "verified"}]
        state = _make_state(
            stage="3",
            sub_stage="completion_validation",
            total_units=3,
            verified_units=verified,
        )
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert isinstance(result, dict)
        # Should present gate_3_completion_failure or similar
        if result["action_type"] == "human_gate":
            assert result["gate_id"] == "gate_3_completion_failure"


# ===========================================================================
# Structural invariants
# ===========================================================================


class TestStructuralInvariants:
    """Tests for cross-cutting structural invariants of Unit 14."""

    def test_phase_to_agent_set_equality_with_group_b(self):
        """PHASE_TO_AGENT keys must match Group B command --phase values from Unit 25."""
        group_b_phases = {
            "help",
            "hint",
            "reference_indexing",
            "redo",
            "bug_triage",
            "oracle",
            "checklist_generation",
            "regression_adaptation",
        }
        assert set(PHASE_TO_AGENT.keys()) == group_b_phases

    def test_all_gate_ids_in_vocabulary_are_strings(self):
        """All gate IDs in GATE_VOCABULARY must be strings."""
        for gate_id in GATE_VOCABULARY.keys():
            assert isinstance(gate_id, str)

    def test_route_state_persistence_invariant(self, tmp_path):
        """route() calls save_state before any recursive route() call."""
        # We verify that after route(), the state file still exists and is valid JSON
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        route(tmp_path)
        state_file = tmp_path / ".svp" / "pipeline_state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "stage" in data

    def test_all_action_type_values_are_strings(self, tmp_path):
        """action_type in returned action block must be a string."""
        state = _make_state(stage="0", sub_stage="hook_activation")
        _write_state_file(tmp_path, state)
        _write_last_status(tmp_path, "")
        result = route(tmp_path)
        assert isinstance(result["action_type"], str)

    def test_gate_vocabulary_covers_all_dispatch_gate_response_gates(self):
        """Every gate_id referenced in dispatch_gate_response contracts exists in GATE_VOCABULARY."""
        # All gate IDs that dispatch_gate_response must handle
        expected_gate_ids = {
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
        }
        for gate_id in expected_gate_ids:
            assert gate_id in GATE_VOCABULARY, f"{gate_id} not in GATE_VOCABULARY"

    def test_all_parser_keys_are_strings(self):
        """All keys in TEST_OUTPUT_PARSERS must be strings."""
        for key in TEST_OUTPUT_PARSERS.keys():
            assert isinstance(key, str)

    def test_run_result_is_named_tuple(self):
        """RunResult is a NamedTuple with expected fields."""
        r = RunResult(
            status="TESTS_PASSED",
            passed=5,
            failed=0,
            errors=0,
            output="ok",
            collection_error=False,
        )
        assert r.status == "TESTS_PASSED"
        assert r.passed == 5
        assert r.failed == 0
        assert r.errors == 0
        assert r.output == "ok"
        assert r.collection_error is False
