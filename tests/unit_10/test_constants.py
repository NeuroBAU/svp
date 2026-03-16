"""Tests for Unit 10 constants: GATE_VOCABULARY, GATE_RESPONSES,
AGENT_STATUS_LINES, COMMAND_STATUS_PATTERNS, CROSS_AGENT_STATUS_LINES.

Synthetic data assumptions:
- ALL_GATE_IDS from Unit 9 stub is the canonical list of gate IDs.
- GATE_VOCABULARY and GATE_RESPONSES must have identical keys.
- Every agent type in AGENT_STATUS_LINES has at least one status.
- COMMAND_STATUS_PATTERNS contains exactly 5 patterns.
"""

from src.unit_10.stub import (
    AGENT_STATUS_LINES,
    COMMAND_STATUS_PATTERNS,
    CROSS_AGENT_STATUS_LINES,
    GATE_RESPONSES,
)


class TestGateResponses:
    def test_gate_responses_is_dict(self):
        assert isinstance(GATE_RESPONSES, dict)

    def test_gate_responses_keys_are_strings(self):
        for key in GATE_RESPONSES:
            assert isinstance(key, str)

    def test_gate_responses_values_are_lists(self):
        for key, val in GATE_RESPONSES.items():
            assert isinstance(val, list), f"{key} value is not a list"

    def test_gate_responses_values_contain_strings(self):
        for key, val in GATE_RESPONSES.items():
            for item in val:
                assert isinstance(item, str), f"{key} contains non-string: {item}"

    def test_gate_responses_not_empty(self):
        assert len(GATE_RESPONSES) > 0

    def test_gate_responses_each_gate_has_responses(self):
        for key, val in GATE_RESPONSES.items():
            assert len(val) > 0, f"Gate {key} has no responses"

    def test_gate_responses_contains_stage_0_gates(self):
        expected = [
            "gate_0_1_hook_activation",
            "gate_0_2_context_approval",
            "gate_0_3_profile_approval",
            "gate_0_3r_profile_revision",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_stage_1_gates(self):
        expected = [
            "gate_1_1_spec_draft",
            "gate_1_2_spec_post_review",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_stage_2_gates(self):
        expected = [
            "gate_2_1_blueprint_approval",
            "gate_2_2_blueprint_post_review",
            "gate_2_3_alignment_exhausted",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_stage_3_gates(self):
        expected = [
            "gate_3_1_test_validation",
            "gate_3_2_diagnostic_decision",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_stage_4_gates(self):
        expected = [
            "gate_4_1_integration_failure",
            "gate_4_2_assembly_exhausted",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_stage_5_gates(self):
        expected = [
            "gate_5_1_repo_test",
            "gate_5_2_assembly_exhausted",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_stage_6_gates(self):
        expected = [
            "gate_6_0_debug_permission",
            "gate_6_1_regression_test",
            "gate_6_2_debug_classification",
            "gate_6_3_repair_exhausted",
            "gate_6_4_non_reproducible",
            "gate_6_5_debug_commit",
        ]
        for g in expected:
            assert g in GATE_RESPONSES

    def test_gate_responses_contains_hint_conflict(self):
        assert "gate_hint_conflict" in GATE_RESPONSES

    def test_gate_id_consistency_with_unit_9(self):
        """GATE_RESPONSES keys must be identical to
        ALL_GATE_IDS from Unit 9."""
        from src.unit_9.stub import ALL_GATE_IDS

        gate_response_keys = set(GATE_RESPONSES.keys())
        all_gate_ids_set = set(ALL_GATE_IDS)
        assert gate_response_keys == all_gate_ids_set, (
            f"Mismatch: "
            f"in GATE_RESPONSES only: "
            f"{gate_response_keys - all_gate_ids_set}, "
            f"in ALL_GATE_IDS only: "
            f"{all_gate_ids_set - gate_response_keys}"
        )

    def test_gate_responses_specific_values(self):
        """Spot-check specific gate response values."""
        assert "HOOKS ACTIVATED" in GATE_RESPONSES["gate_0_1_hook_activation"]
        assert "HOOKS FAILED" in GATE_RESPONSES["gate_0_1_hook_activation"]
        assert "APPROVE" in GATE_RESPONSES["gate_1_1_spec_draft"]
        assert "REVISE" in GATE_RESPONSES["gate_1_1_spec_draft"]
        assert "TEST CORRECT" in GATE_RESPONSES["gate_3_1_test_validation"]


class TestAgentStatusLines:
    def test_agent_status_lines_is_dict(self):
        assert isinstance(AGENT_STATUS_LINES, dict)

    def test_all_agent_types_present(self):
        expected_agents = [
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
        ]
        for agent in expected_agents:
            assert agent in AGENT_STATUS_LINES, f"Missing agent: {agent}"

    def test_each_agent_has_at_least_one_status(self):
        for agent, statuses in AGENT_STATUS_LINES.items():
            assert len(statuses) > 0, f"{agent} has no status lines"

    def test_setup_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["setup_agent"]
        assert "PROJECT_CONTEXT_COMPLETE" in statuses
        assert "PROJECT_CONTEXT_REJECTED" in statuses
        assert "PROFILE_COMPLETE" in statuses

    def test_test_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["test_agent"]
        assert "TEST_GENERATION_COMPLETE" in statuses
        assert "REGRESSION_TEST_COMPLETE" in statuses

    def test_implementation_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["implementation_agent"]
        assert "IMPLEMENTATION_COMPLETE" in statuses

    def test_coverage_review_statuses(self):
        statuses = AGENT_STATUS_LINES["coverage_review"]
        assert "COVERAGE_COMPLETE: no gaps" in statuses
        assert "COVERAGE_COMPLETE: tests added" in statuses

    def test_diagnostic_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["diagnostic_agent"]
        assert "DIAGNOSIS_COMPLETE: implementation" in statuses
        assert "DIAGNOSIS_COMPLETE: blueprint" in statuses
        assert "DIAGNOSIS_COMPLETE: spec" in statuses

    def test_redo_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["redo_agent"]
        assert "REDO_CLASSIFIED: spec" in statuses
        assert "REDO_CLASSIFIED: blueprint" in statuses
        assert "REDO_CLASSIFIED: gate" in statuses
        assert "REDO_CLASSIFIED: profile_delivery" in statuses
        assert "REDO_CLASSIFIED: profile_blueprint" in statuses

    def test_bug_triage_statuses(self):
        statuses = AGENT_STATUS_LINES["bug_triage"]
        assert "TRIAGE_COMPLETE: build_env" in statuses
        assert "TRIAGE_COMPLETE: single_unit" in statuses
        assert "TRIAGE_COMPLETE: cross_unit" in statuses
        assert "TRIAGE_NEEDS_REFINEMENT" in statuses
        assert "TRIAGE_NON_REPRODUCIBLE" in statuses

    def test_repair_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["repair_agent"]
        assert "REPAIR_COMPLETE" in statuses
        assert "REPAIR_FAILED" in statuses
        assert "REPAIR_RECLASSIFY" in statuses

    def test_help_agent_statuses(self):
        statuses = AGENT_STATUS_LINES["help_agent"]
        assert "HELP_SESSION_COMPLETE: no hint" in statuses
        assert "HELP_SESSION_COMPLETE: hint forwarded" in statuses

    def test_reference_indexing_statuses(self):
        statuses = AGENT_STATUS_LINES["reference_indexing"]
        assert "INDEXING_COMPLETE" in statuses

    def test_status_lines_are_all_strings(self):
        for agent, statuses in AGENT_STATUS_LINES.items():
            for s in statuses:
                assert isinstance(s, str), f"{agent} has non-string status"


class TestCommandStatusPatterns:
    def test_command_status_patterns_is_list(self):
        assert isinstance(COMMAND_STATUS_PATTERNS, list)

    def test_contains_tests_passed(self):
        assert "TESTS_PASSED" in COMMAND_STATUS_PATTERNS

    def test_contains_tests_failed(self):
        assert "TESTS_FAILED" in COMMAND_STATUS_PATTERNS

    def test_contains_tests_error(self):
        assert "TESTS_ERROR" in COMMAND_STATUS_PATTERNS

    def test_contains_command_succeeded(self):
        assert "COMMAND_SUCCEEDED" in COMMAND_STATUS_PATTERNS

    def test_contains_command_failed(self):
        assert "COMMAND_FAILED" in COMMAND_STATUS_PATTERNS

    def test_exactly_five_patterns(self):
        assert len(COMMAND_STATUS_PATTERNS) == 5

    def test_all_items_are_strings(self):
        for p in COMMAND_STATUS_PATTERNS:
            assert isinstance(p, str)


class TestCrossAgentStatusLines:
    def test_cross_agent_status_lines_is_dict(self):
        assert isinstance(CROSS_AGENT_STATUS_LINES, dict)

    def test_contains_hint_blueprint_conflict(self):
        assert "HINT_BLUEPRINT_CONFLICT" in CROSS_AGENT_STATUS_LINES

    def test_hint_conflict_maps_to_gate(self):
        val = CROSS_AGENT_STATUS_LINES["HINT_BLUEPRINT_CONFLICT"]
        assert val == "gate_hint_conflict"
