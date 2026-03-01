"""
Tests for Unit 10 data contracts: GATE_VOCABULARY, AGENT_STATUS_LINES,
CROSS_AGENT_STATUS, and COMMAND_STATUS_PATTERNS.

These are the canonical vocabularies that drive dispatch logic and enforce
the Bug 1 fix (human-typed option text IS the status string).

DATA ASSUMPTION: All gate IDs and status strings are taken verbatim from the
blueprint's Tier 2 signatures. No domain-specific distribution assumed --
these are exact enumeration values.
"""

import pytest
from svp.scripts.routing import (
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
)


class TestGateVocabulary:
    """Verify the GATE_VOCABULARY data constant matches the blueprint exactly."""

    def test_gate_vocabulary_is_dict(self):
        """GATE_VOCABULARY must be a dict mapping gate IDs to lists of strings."""
        assert isinstance(GATE_VOCABULARY, dict)

    def test_gate_vocabulary_contains_all_expected_gate_ids(self):
        """Verify all gate IDs from the blueprint are present."""
        expected_gate_ids = {
            "gate_0_1_hook_activation",
            "gate_0_2_context_approval",
            "gate_1_1_spec_draft",
            "gate_1_2_spec_post_review",
            "gate_2_1_blueprint_approval",
            "gate_2_2_blueprint_post_review",
            "gate_2_3_alignment_exhausted",
            "gate_3_1_test_validation",
            "gate_3_2_diagnostic_decision",
            "gate_4_1_integration_failure",
            "gate_4_2_assembly_exhausted",
            "gate_5_1_repo_test",
            "gate_5_2_assembly_exhausted",
            "gate_6_0_debug_permission",
            "gate_6_1_regression_test",
            "gate_6_2_debug_classification",
            "gate_6_3_repair_exhausted",
            "gate_6_4_non_reproducible",
        }
        assert set(GATE_VOCABULARY.keys()) == expected_gate_ids

    def test_gate_vocabulary_values_are_lists_of_strings(self):
        """Every value must be a list of strings."""
        for gate_id, options in GATE_VOCABULARY.items():
            assert isinstance(options, list), f"{gate_id} options is not a list"
            for opt in options:
                assert isinstance(opt, str), f"{gate_id} has non-string option: {opt!r}"

    def test_gate_vocabulary_no_empty_option_lists(self):
        """Every gate must have at least one valid option."""
        for gate_id, options in GATE_VOCABULARY.items():
            assert len(options) > 0, f"{gate_id} has no valid options"

    # DATA ASSUMPTION: Each gate's exact option strings come from the blueprint.
    # These are the Bug 1 fix strings -- human types these exactly.

    def test_gate_0_1_options(self):
        assert GATE_VOCABULARY["gate_0_1_hook_activation"] == [
            "HOOKS ACTIVATED", "HOOKS FAILED"
        ]

    def test_gate_0_2_options(self):
        assert GATE_VOCABULARY["gate_0_2_context_approval"] == [
            "CONTEXT APPROVED", "CONTEXT REJECTED", "CONTEXT NOT READY"
        ]

    def test_gate_1_1_options(self):
        assert GATE_VOCABULARY["gate_1_1_spec_draft"] == [
            "APPROVE", "REVISE", "FRESH REVIEW"
        ]

    def test_gate_1_2_options(self):
        assert GATE_VOCABULARY["gate_1_2_spec_post_review"] == [
            "APPROVE", "REVISE", "FRESH REVIEW"
        ]

    def test_gate_2_1_options(self):
        assert GATE_VOCABULARY["gate_2_1_blueprint_approval"] == [
            "APPROVE", "REVISE", "FRESH REVIEW"
        ]

    def test_gate_2_2_options(self):
        assert GATE_VOCABULARY["gate_2_2_blueprint_post_review"] == [
            "APPROVE", "REVISE", "FRESH REVIEW"
        ]

    def test_gate_2_3_options(self):
        assert GATE_VOCABULARY["gate_2_3_alignment_exhausted"] == [
            "REVISE SPEC", "RESTART SPEC", "RETRY BLUEPRINT"
        ]

    def test_gate_3_1_options(self):
        assert GATE_VOCABULARY["gate_3_1_test_validation"] == [
            "TEST CORRECT", "TEST WRONG"
        ]

    def test_gate_3_2_options(self):
        assert GATE_VOCABULARY["gate_3_2_diagnostic_decision"] == [
            "FIX IMPLEMENTATION", "FIX BLUEPRINT", "FIX SPEC"
        ]

    def test_gate_4_1_options(self):
        assert GATE_VOCABULARY["gate_4_1_integration_failure"] == [
            "ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"
        ]

    def test_gate_4_2_options(self):
        assert GATE_VOCABULARY["gate_4_2_assembly_exhausted"] == [
            "FIX BLUEPRINT", "FIX SPEC"
        ]

    def test_gate_5_1_options(self):
        assert GATE_VOCABULARY["gate_5_1_repo_test"] == [
            "TESTS PASSED", "TESTS FAILED"
        ]

    def test_gate_5_2_options(self):
        assert GATE_VOCABULARY["gate_5_2_assembly_exhausted"] == [
            "RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"
        ]

    def test_gate_6_0_options(self):
        assert GATE_VOCABULARY["gate_6_0_debug_permission"] == [
            "AUTHORIZE DEBUG", "ABANDON DEBUG"
        ]

    def test_gate_6_1_options(self):
        assert GATE_VOCABULARY["gate_6_1_regression_test"] == [
            "TEST CORRECT", "TEST WRONG"
        ]

    def test_gate_6_2_options(self):
        assert GATE_VOCABULARY["gate_6_2_debug_classification"] == [
            "FIX UNIT", "FIX BLUEPRINT", "FIX SPEC"
        ]

    def test_gate_6_3_options(self):
        assert GATE_VOCABULARY["gate_6_3_repair_exhausted"] == [
            "RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"
        ]

    def test_gate_6_4_options(self):
        assert GATE_VOCABULARY["gate_6_4_non_reproducible"] == [
            "RETRY TRIAGE", "ABANDON DEBUG"
        ]

    def test_bug1_options_are_exact_strings_not_prefixed(self):
        """Bug 1 fix: option strings must not have any prefix or reformatting.
        They must be plain uppercase human-typeable strings."""
        for gate_id, options in GATE_VOCABULARY.items():
            for opt in options:
                # No leading/trailing whitespace
                assert opt == opt.strip(), (
                    f"Option {opt!r} in {gate_id} has leading/trailing whitespace"
                )
                # No numeric prefixes like "1. " or "1) "
                assert not opt[0].isdigit(), (
                    f"Option {opt!r} in {gate_id} starts with a digit (prefix)"
                )


class TestAgentStatusLines:
    """Verify the AGENT_STATUS_LINES data constant matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(AGENT_STATUS_LINES, dict)

    def test_contains_all_expected_agents(self):
        expected_agents = {
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
        }
        assert set(AGENT_STATUS_LINES.keys()) == expected_agents

    def test_values_are_lists_of_strings(self):
        for agent, statuses in AGENT_STATUS_LINES.items():
            assert isinstance(statuses, list), f"{agent} statuses not a list"
            for s in statuses:
                assert isinstance(s, str), f"{agent} has non-string status: {s!r}"

    def test_no_empty_status_lists(self):
        for agent, statuses in AGENT_STATUS_LINES.items():
            assert len(statuses) > 0, f"{agent} has no status lines"

    # DATA ASSUMPTION: Spot-check selected agents' status lines from blueprint.

    def test_setup_agent_statuses(self):
        assert AGENT_STATUS_LINES["setup_agent"] == [
            "PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED"
        ]

    def test_blueprint_checker_statuses(self):
        assert AGENT_STATUS_LINES["blueprint_checker"] == [
            "ALIGNMENT_CONFIRMED",
            "ALIGNMENT_FAILED: spec",
            "ALIGNMENT_FAILED: blueprint",
        ]

    def test_bug_triage_statuses(self):
        assert AGENT_STATUS_LINES["bug_triage"] == [
            "TRIAGE_COMPLETE: build_env",
            "TRIAGE_COMPLETE: single_unit",
            "TRIAGE_COMPLETE: cross_unit",
            "TRIAGE_NEEDS_REFINEMENT",
            "TRIAGE_NON_REPRODUCIBLE",
        ]

    def test_repair_agent_statuses(self):
        assert AGENT_STATUS_LINES["repair_agent"] == [
            "REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"
        ]

    def test_test_agent_statuses(self):
        assert AGENT_STATUS_LINES["test_agent"] == ["TEST_GENERATION_COMPLETE"]

    def test_diagnostic_agent_statuses(self):
        assert AGENT_STATUS_LINES["diagnostic_agent"] == [
            "DIAGNOSIS_COMPLETE: implementation",
            "DIAGNOSIS_COMPLETE: blueprint",
            "DIAGNOSIS_COMPLETE: spec",
        ]


class TestCrossAgentStatus:
    """Verify the CROSS_AGENT_STATUS constant."""

    def test_is_string(self):
        assert isinstance(CROSS_AGENT_STATUS, str)

    def test_value(self):
        assert CROSS_AGENT_STATUS == "HINT_BLUEPRINT_CONFLICT"


class TestCommandStatusPatterns:
    """Verify the COMMAND_STATUS_PATTERNS constant."""

    def test_is_list(self):
        assert isinstance(COMMAND_STATUS_PATTERNS, list)

    def test_contains_expected_patterns(self):
        expected = [
            "TESTS_PASSED",
            "TESTS_FAILED",
            "TESTS_ERROR",
            "COMMAND_SUCCEEDED",
            "COMMAND_FAILED",
        ]
        assert COMMAND_STATUS_PATTERNS == expected

    def test_all_strings(self):
        for pattern in COMMAND_STATUS_PATTERNS:
            assert isinstance(pattern, str)
