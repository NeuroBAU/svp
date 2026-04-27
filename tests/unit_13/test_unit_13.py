"""Unit 13: Task Preparation -- complete test suite.

Synthetic data assumptions:
- A temporary directory tree simulates the project root with:
    * .svp/ directory for output files (task_prompt.md, gate_prompt.md)
    * blueprint/ directory containing blueprint_prose.md and blueprint_contracts.md
    * pipeline_state.json with minimal valid state
    * project_profile.json with minimal valid profile
    * toolchain.json with minimal valid toolchain
  These files contain synthetic placeholder content sufficient to exercise
  the contracts without depending on real project data.

- ALL_GATE_IDS is a list of exactly 31 gate ID strings whose set equality
  with GATE_VOCABULARY.keys() (Unit 14) is verified structurally.

- KNOWN_AGENT_TYPES is a list of 21 agent type strings enumerating every
  agent the pipeline can invoke.

- SELECTIVE_LOADING_MATRIX maps agent_type strings to one of three loading
  modes: "contracts_only", "prose_only", or "both". Agent types not present
  in the matrix do not load blueprint at all.

- prepare_task_prompt dispatches by agent_type and mode, reads blueprint
  according to the matrix, writes output to .svp/task_prompt.md, and returns
  the content string.

- prepare_gate_prompt reads pipeline state, uses gate_id to build a gate
  prompt, writes to .svp/gate_prompt.md, and returns the content string.

- load_blueprint reads and concatenates both blueprint_prose.md and
  blueprint_contracts.md from the given directory.
- load_blueprint_contracts_only reads only blueprint_contracts.md.
- load_blueprint_prose_only reads only blueprint_prose.md.

- build_unit_context extracts a unit's definition and returns context
  including upstream dependency contracts. include_tier1 controls tier 1
  inclusion.

- build_language_context returns a formatted block with language metadata,
  agent-specific guidance, test framework, quality tools, and file extension.
  Returns empty string if agent_type has no language-specific prompts.

- For sentinel-checking agent types (test_agent, implementation_agent,
  coverage_review_agent), the LANGUAGE_CONTEXT injected into task prompts
  MUST include the verbatim stub_sentinel value from the language registry.

- main parses CLI arguments (--unit, --agent, --project-root, --output,
  --gate, --context, --mode, --ladder, --revision-mode, --quality-report)
  and invokes the appropriate preparation function.
"""

import json
from pathlib import Path

import pytest

from prepare_task import (
    ALL_GATE_IDS,
    KNOWN_AGENT_TYPES,
    SELECTIVE_LOADING_MATRIX,
    build_language_context,
    build_unit_context,
    load_blueprint,
    load_blueprint_contracts_only,
    load_blueprint_prose_only,
    main,
    prepare_gate_prompt,
    prepare_task_prompt,
)

# ---------------------------------------------------------------------------
# Synthetic data constants
# ---------------------------------------------------------------------------

BLUEPRINT_PROSE_CONTENT = (
    "# SVP Blueprint Prose\n\n"
    "This is synthetic prose content for testing.\n"
    "It describes the overall architecture.\n"
)

BLUEPRINT_CONTRACTS_CONTENT = (
    "# SVP Blueprint Contracts\n\n"
    "## Unit 1: Configuration\n"
    "### Tier 1\nUnit 1 overview.\n"
    "### Tier 2 -- Signatures\n```python\ndef load_config(): ...\n```\n"
    "### Tier 3 -- Behavioral Contracts\nload_config returns dict.\n\n"
    "## Unit 5: Test Infrastructure\n"
    "### Tier 1\nUnit 5 overview.\n"
    "### Tier 2 -- Signatures\n```python\ndef run_tests(): ...\n```\n"
    "### Tier 3 -- Behavioral Contracts\nrun_tests returns RunResult.\n"
)

MINIMAL_PIPELINE_STATE = {
    "stage": 3,
    "sub_stage": "test",
    "pass_number": 1,
    "current_unit": 5,
    "status": "running",
}

MINIMAL_PROFILE = {
    "archetype": "python_project",
    "language": {"primary": "python", "components": []},
}

MINIMAL_TOOLCHAIN = {
    "python": "3.11",
    "pytest": "7.4",
}

EXPECTED_GATE_COUNT = 31
EXPECTED_AGENT_COUNT = 21

EXPECTED_GATE_IDS = [
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

EXPECTED_AGENT_TYPES = [
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
]

EXPECTED_SELECTIVE_LOADING_MATRIX = {
    "test_agent": "contracts_only",
    "implementation_agent": "contracts_only",
    "diagnostic_agent": "both",
    "help_agent": "prose_only",
    "hint_agent": "both",
    "integration_test_author": "contracts_only",
    "git_repo_agent": "contracts_only",
    "bug_triage_agent": "both",
    "repair_agent": "both",
    "blueprint_author": "both",
    "blueprint_checker": "both",
    "blueprint_reviewer": "both",
    "coverage_review_agent": "contracts_only",
    "oracle_agent": "both",
}

# Agents that verify stub presence/absence and need sentinel injection
SENTINEL_CHECKING_AGENTS = [
    "test_agent",
    "implementation_agent",
    "coverage_review_agent",
]

PYTHON_STUB_SENTINEL = (
    "__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP"
)

SAMPLE_LANGUAGE_REGISTRY = {
    "python": {
        "id": "python",
        "display_name": "Python",
        "file_extension": ".py",
        "test_framework": "pytest",
        "stub_sentinel": PYTHON_STUB_SENTINEL,
        "agent_prompts": {
            "test_agent": "Python test agent guidance: use pytest conventions.",
            "implementation_agent": "Python implementation guidance: follow PEP 8.",
            "coverage_review_agent": "Python coverage guidance: check branch coverage.",
        },
        "default_quality": {
            "linter": "ruff",
            "formatter": "ruff",
        },
    },
}

R_STUB_SENTINEL = (
    "# __SVP_STUB__ <- TRUE  # DO NOT DELIVER -- stub file generated by SVP"
)

SAMPLE_LANGUAGE_REGISTRY_R = {
    "r": {
        "id": "r",
        "display_name": "R",
        "file_extension": ".R",
        "test_framework": "testthat",
        "stub_sentinel": R_STUB_SENTINEL,
        "agent_prompts": {
            "test_agent": "R test agent guidance: use testthat conventions.",
            "implementation_agent": "R implementation guidance: follow tidyverse style.",
            "coverage_review_agent": "R coverage guidance: check function coverage.",
        },
        "default_quality": {
            "linter": "lintr",
            "formatter": "styler",
        },
    },
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path):
    """Create a minimal synthetic project root for testing."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    blueprint_dir = tmp_path / "blueprint"
    blueprint_dir.mkdir()

    (blueprint_dir / "blueprint_prose.md").write_text(BLUEPRINT_PROSE_CONTENT)
    (blueprint_dir / "blueprint_contracts.md").write_text(BLUEPRINT_CONTRACTS_CONTENT)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(MINIMAL_PIPELINE_STATE))
    (tmp_path / "project_profile.json").write_text(json.dumps(MINIMAL_PROFILE))
    (tmp_path / "toolchain.json").write_text(json.dumps(MINIMAL_TOOLCHAIN))

    return tmp_path


@pytest.fixture
def blueprint_dir(project_root):
    """Return the blueprint directory within the project root."""
    return project_root / "blueprint"


# ---------------------------------------------------------------------------
# Contract: ALL_GATE_IDS constant
# ---------------------------------------------------------------------------


class TestAllGateIds:
    """ALL_GATE_IDS must be a list of exactly 31 gate ID strings matching
    the specification."""

    def test_all_gate_ids_is_a_list(self):
        assert isinstance(ALL_GATE_IDS, list)

    def test_all_gate_ids_has_31_entries(self):
        assert len(ALL_GATE_IDS) == EXPECTED_GATE_COUNT

    def test_all_gate_ids_contains_only_strings(self):
        for gate_id in ALL_GATE_IDS:
            assert isinstance(gate_id, str), f"Non-string gate ID: {gate_id!r}"

    def test_all_gate_ids_matches_expected_set(self):
        assert set(ALL_GATE_IDS) == set(EXPECTED_GATE_IDS)

    def test_all_gate_ids_no_duplicates(self):
        assert len(ALL_GATE_IDS) == len(set(ALL_GATE_IDS))

    def test_gate_0_1_hook_activation_present(self):
        assert "gate_0_1_hook_activation" in ALL_GATE_IDS

    def test_gate_pass_transition_post_pass2_present(self):
        assert "gate_pass_transition_post_pass2" in ALL_GATE_IDS

    def test_gate_7_b_fix_plan_review_present(self):
        assert "gate_7_b_fix_plan_review" in ALL_GATE_IDS

    def test_gate_6_5_debug_commit_present(self):
        assert "gate_6_5_debug_commit" in ALL_GATE_IDS

    def test_gate_hint_conflict_present(self):
        assert "gate_hint_conflict" in ALL_GATE_IDS


# ---------------------------------------------------------------------------
# Contract: KNOWN_AGENT_TYPES constant
# ---------------------------------------------------------------------------


class TestKnownAgentTypes:
    """KNOWN_AGENT_TYPES must be a list of exactly 21 agent type strings."""

    def test_known_agent_types_is_a_list(self):
        assert isinstance(KNOWN_AGENT_TYPES, list)

    def test_known_agent_types_has_21_entries(self):
        assert len(KNOWN_AGENT_TYPES) == EXPECTED_AGENT_COUNT

    def test_known_agent_types_contains_only_strings(self):
        for agent_type in KNOWN_AGENT_TYPES:
            assert isinstance(agent_type, str), f"Non-string agent type: {agent_type!r}"

    def test_known_agent_types_matches_expected_set(self):
        assert set(KNOWN_AGENT_TYPES) == set(EXPECTED_AGENT_TYPES)

    def test_known_agent_types_no_duplicates(self):
        assert len(KNOWN_AGENT_TYPES) == len(set(KNOWN_AGENT_TYPES))

    def test_setup_agent_present(self):
        assert "setup_agent" in KNOWN_AGENT_TYPES

    def test_oracle_agent_present(self):
        assert "oracle_agent" in KNOWN_AGENT_TYPES

    def test_test_agent_present(self):
        assert "test_agent" in KNOWN_AGENT_TYPES

    def test_implementation_agent_present(self):
        assert "implementation_agent" in KNOWN_AGENT_TYPES

    def test_bug_triage_present(self):
        assert "bug_triage" in KNOWN_AGENT_TYPES


# ---------------------------------------------------------------------------
# Contract: SELECTIVE_LOADING_MATRIX constant
# ---------------------------------------------------------------------------


class TestSelectiveLoadingMatrix:
    """SELECTIVE_LOADING_MATRIX maps agent types to blueprint loading modes."""

    def test_selective_loading_matrix_is_a_dict(self):
        assert isinstance(SELECTIVE_LOADING_MATRIX, dict)

    def test_selective_loading_matrix_has_expected_keys(self):
        assert set(SELECTIVE_LOADING_MATRIX.keys()) == set(
            EXPECTED_SELECTIVE_LOADING_MATRIX.keys()
        )

    def test_selective_loading_matrix_values_are_valid_modes(self):
        valid_modes = {"contracts_only", "prose_only", "both"}
        for agent_type, mode in SELECTIVE_LOADING_MATRIX.items():
            assert mode in valid_modes, (
                f"Agent '{agent_type}' has invalid mode '{mode}'"
            )

    def test_test_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX["test_agent"] == "contracts_only"

    def test_implementation_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX["implementation_agent"] == "contracts_only"

    def test_diagnostic_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["diagnostic_agent"] == "both"

    def test_help_agent_loads_prose_only(self):
        assert SELECTIVE_LOADING_MATRIX["help_agent"] == "prose_only"

    def test_hint_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["hint_agent"] == "both"

    def test_integration_test_author_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX["integration_test_author"] == "contracts_only"

    def test_git_repo_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX["git_repo_agent"] == "contracts_only"

    def test_bug_triage_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["bug_triage_agent"] == "both"

    def test_repair_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["repair_agent"] == "both"

    def test_blueprint_author_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["blueprint_author"] == "both"

    def test_blueprint_checker_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["blueprint_checker"] == "both"

    def test_blueprint_reviewer_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["blueprint_reviewer"] == "both"

    def test_coverage_review_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX["coverage_review_agent"] == "contracts_only"

    def test_oracle_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX["oracle_agent"] == "both"

    def test_matrix_matches_expected_exactly(self):
        for agent_type, expected_mode in EXPECTED_SELECTIVE_LOADING_MATRIX.items():
            assert SELECTIVE_LOADING_MATRIX.get(agent_type) == expected_mode, (
                f"Mismatch for '{agent_type}': "
                f"expected '{expected_mode}', got '{SELECTIVE_LOADING_MATRIX.get(agent_type)}'"
            )


# ---------------------------------------------------------------------------
# Contract: load_blueprint reads and concatenates both files
# ---------------------------------------------------------------------------


class TestLoadBlueprint:
    """load_blueprint concatenates both prose and contracts files."""

    def test_load_blueprint_returns_string(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert isinstance(result, str)

    def test_load_blueprint_contains_prose_content(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert "SVP Blueprint Prose" in result

    def test_load_blueprint_contains_contracts_content(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert "SVP Blueprint Contracts" in result

    def test_load_blueprint_contains_both_files(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert "overall architecture" in result
        assert "Behavioral Contracts" in result

    def test_load_blueprint_nonempty(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert len(result) > 0

    def test_load_blueprint_longer_than_either_file_alone(self, blueprint_dir):
        full = load_blueprint(blueprint_dir)
        contracts_only = load_blueprint_contracts_only(blueprint_dir)
        prose_only = load_blueprint_prose_only(blueprint_dir)
        assert len(full) >= len(contracts_only)
        assert len(full) >= len(prose_only)


# ---------------------------------------------------------------------------
# Contract: load_blueprint_contracts_only reads contracts file only
# ---------------------------------------------------------------------------


class TestLoadBlueprintContractsOnly:
    """load_blueprint_contracts_only reads only blueprint_contracts.md."""

    def test_returns_string(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert isinstance(result, str)

    def test_contains_contracts_content(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert "SVP Blueprint Contracts" in result

    def test_does_not_contain_prose_content(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert "SVP Blueprint Prose" not in result

    def test_contains_behavioral_contracts(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert "Behavioral Contracts" in result

    def test_nonempty(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Contract: load_blueprint_prose_only reads prose file only
# ---------------------------------------------------------------------------


class TestLoadBlueprintProseOnly:
    """load_blueprint_prose_only reads only blueprint_prose.md."""

    def test_returns_string(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert isinstance(result, str)

    def test_contains_prose_content(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert "SVP Blueprint Prose" in result

    def test_does_not_contain_contracts_content(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert "SVP Blueprint Contracts" not in result

    def test_contains_architecture_description(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert "overall architecture" in result

    def test_nonempty(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Contract: load functions are mutually exclusive in content sourcing
# ---------------------------------------------------------------------------


class TestBlueprintLoadingMutualExclusivity:
    """The three load functions source from distinct file subsets."""

    def test_contracts_only_is_subset_of_full(self, blueprint_dir):
        full = load_blueprint(blueprint_dir)
        contracts = load_blueprint_contracts_only(blueprint_dir)
        # The contracts content should appear within the full load
        assert BLUEPRINT_CONTRACTS_CONTENT.strip().split("\n")[0] in full
        assert BLUEPRINT_CONTRACTS_CONTENT.strip().split("\n")[0] in contracts

    def test_prose_only_is_subset_of_full(self, blueprint_dir):
        full = load_blueprint(blueprint_dir)
        prose = load_blueprint_prose_only(blueprint_dir)
        assert BLUEPRINT_PROSE_CONTENT.strip().split("\n")[0] in full
        assert BLUEPRINT_PROSE_CONTENT.strip().split("\n")[0] in prose

    def test_contracts_and_prose_do_not_overlap(self, blueprint_dir):
        contracts = load_blueprint_contracts_only(blueprint_dir)
        prose = load_blueprint_prose_only(blueprint_dir)
        # Prose-specific content not in contracts
        assert "overall architecture" not in contracts
        # Contracts-specific content not in prose
        assert "Behavioral Contracts" not in prose


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt returns a string
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptReturnType:
    """prepare_task_prompt always returns a string."""

    def test_returns_string_for_test_agent(self, project_root):
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert isinstance(result, str)

    def test_returns_nonempty_string(self, project_root):
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert len(result) > 0

    def test_returns_string_for_implementation_agent(self, project_root):
        result = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=5
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt writes output to .svp/task_prompt.md
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptWritesFile:
    """prepare_task_prompt writes the prompt to .svp/task_prompt.md."""

    def test_writes_task_prompt_file(self, project_root):
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        output_file = project_root / ".svp" / "task_prompt.md"
        assert output_file.exists()

    def test_file_content_matches_return_value(self, project_root):
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        output_file = project_root / ".svp" / "task_prompt.md"
        file_content = output_file.read_text()
        assert file_content == result

    def test_subsequent_call_overwrites_file(self, project_root):
        result1 = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        result2 = prepare_task_prompt(project_root, "help_agent")
        output_file = project_root / ".svp" / "task_prompt.md"
        file_content = output_file.read_text()
        assert file_content == result2


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt dispatches by agent_type
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptDispatchByAgentType:
    """Different agent types produce different prompts."""

    def test_test_agent_differs_from_implementation_agent(self, project_root):
        result_test = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        result_impl = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=5
        )
        assert result_test != result_impl

    def test_help_agent_differs_from_test_agent(self, project_root):
        result_help = prepare_task_prompt(project_root, "help_agent")
        result_test = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert result_help != result_test

    def test_diagnostic_agent_differs_from_implementation_agent(self, project_root):
        result_diag = prepare_task_prompt(
            project_root, "diagnostic_agent", unit_number=5
        )
        result_impl = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=5
        )
        assert result_diag != result_impl


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt dispatches by mode for mode-sensitive agents
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptDispatchByMode:
    """Mode-sensitive agent types produce different prompts for different modes."""

    def test_setup_agent_context_mode_differs_from_profile_mode(self, project_root):
        result_ctx = prepare_task_prompt(project_root, "setup_agent", mode="context")
        result_prof = prepare_task_prompt(project_root, "setup_agent", mode="profile")
        assert result_ctx != result_prof

    def test_setup_agent_redo_delivery_mode(self, project_root):
        result_redo = prepare_task_prompt(
            project_root, "setup_agent", mode="redo_delivery"
        )
        result_ctx = prepare_task_prompt(project_root, "setup_agent", mode="context")
        assert result_redo != result_ctx

    def test_setup_agent_redo_blueprint_mode(self, project_root):
        result_redo_bp = prepare_task_prompt(
            project_root, "setup_agent", mode="redo_blueprint"
        )
        result_prof = prepare_task_prompt(project_root, "setup_agent", mode="profile")
        assert result_redo_bp != result_prof

    def test_stakeholder_dialog_draft_differs_from_revision(self, project_root):
        result_draft = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="draft"
        )
        result_rev = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="revision"
        )
        assert result_draft != result_rev

    def test_stakeholder_dialog_targeted_revision_differs(self, project_root):
        result_rev = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="revision"
        )
        result_targeted = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="targeted_revision"
        )
        assert result_rev != result_targeted

    def test_blueprint_author_draft_differs_from_revision(self, project_root):
        result_draft = prepare_task_prompt(
            project_root, "blueprint_author", mode="draft"
        )
        result_rev = prepare_task_prompt(
            project_root, "blueprint_author", mode="revision"
        )
        assert result_draft != result_rev

    def test_test_agent_normal_differs_from_regression_test(self, project_root):
        result_normal = prepare_task_prompt(
            project_root, "test_agent", unit_number=5, mode="normal"
        )
        result_regression = prepare_task_prompt(
            project_root, "test_agent", unit_number=5, mode="regression_test"
        )
        assert result_normal != result_regression


# ---------------------------------------------------------------------------
# Contract: Blueprint loading per SELECTIVE_LOADING_MATRIX
# ---------------------------------------------------------------------------


class TestBlueprintLoadingByMatrix:
    """Agent types in SELECTIVE_LOADING_MATRIX load blueprint according to
    their mapped mode. Agent types not in the matrix do not load blueprint."""

    def test_test_agent_prompt_includes_contracts(self, project_root):
        """test_agent -> contracts_only: contracts content present."""
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert "SVP Blueprint Contracts" in result or "Behavioral Contracts" in result

    def test_test_agent_prompt_excludes_prose(self, project_root):
        """test_agent -> contracts_only: prose-only content absent."""
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert "SVP Blueprint Prose" not in result

    def test_help_agent_prompt_includes_prose(self, project_root):
        """help_agent -> prose_only: prose content present."""
        result = prepare_task_prompt(project_root, "help_agent")
        assert "SVP Blueprint Prose" in result or "overall architecture" in result

    def test_help_agent_prompt_excludes_contracts(self, project_root):
        """help_agent -> prose_only: contracts-only content absent."""
        result = prepare_task_prompt(project_root, "help_agent")
        assert "SVP Blueprint Contracts" not in result

    def test_diagnostic_agent_prompt_includes_both(self, project_root):
        """diagnostic_agent -> both: both prose and contracts present."""
        result = prepare_task_prompt(project_root, "diagnostic_agent", unit_number=5)
        # Must include content from both files
        has_prose = "SVP Blueprint Prose" in result or "overall architecture" in result
        has_contracts = (
            "SVP Blueprint Contracts" in result or "Behavioral Contracts" in result
        )
        assert has_prose and has_contracts

    def test_agent_not_in_matrix_excludes_blueprint(self, project_root):
        """Agents not in SELECTIVE_LOADING_MATRIX do not load blueprint."""
        # setup_agent is not in the matrix
        result = prepare_task_prompt(project_root, "setup_agent", mode="context")
        assert "SVP Blueprint Prose" not in result
        assert "SVP Blueprint Contracts" not in result

    def test_implementation_agent_loads_contracts_only(self, project_root):
        result = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=5
        )
        assert "SVP Blueprint Contracts" in result or "Behavioral Contracts" in result
        assert "SVP Blueprint Prose" not in result

    def test_hint_agent_loads_both(self, project_root):
        result = prepare_task_prompt(
            project_root, "hint_agent", context="hint text here"
        )
        has_prose = "SVP Blueprint Prose" in result or "overall architecture" in result
        has_contracts = (
            "SVP Blueprint Contracts" in result or "Behavioral Contracts" in result
        )
        assert has_prose and has_contracts


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt accepts optional context parameter
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptContext:
    """The optional context parameter affects the output."""

    def test_context_appears_in_output_when_provided(self, project_root):
        context_str = "Extra context for the agent."
        result = prepare_task_prompt(
            project_root, "test_agent", unit_number=5, context=context_str
        )
        assert context_str in result

    def test_none_context_still_produces_valid_output(self, project_root):
        result = prepare_task_prompt(
            project_root, "test_agent", unit_number=5, context=None
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_differs_with_and_without_context(self, project_root):
        result_with = prepare_task_prompt(
            project_root, "test_agent", unit_number=5, context="Special instructions."
        )
        result_without = prepare_task_prompt(
            project_root, "test_agent", unit_number=5, context=None
        )
        assert result_with != result_without


# ---------------------------------------------------------------------------
# Contract: prepare_gate_prompt returns a string
# ---------------------------------------------------------------------------


class TestPrepareGatePromptReturnType:
    """prepare_gate_prompt always returns a string."""

    def test_returns_string(self, project_root):
        result = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        assert isinstance(result, str)

    def test_returns_nonempty_string(self, project_root):
        result = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Contract: prepare_gate_prompt writes to .svp/gate_prompt.md
# ---------------------------------------------------------------------------


class TestPrepareGatePromptWritesFile:
    """prepare_gate_prompt writes the prompt to .svp/gate_prompt.md."""

    def test_writes_gate_prompt_file(self, project_root):
        prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        output_file = project_root / ".svp" / "gate_prompt.md"
        assert output_file.exists()

    def test_file_content_matches_return_value(self, project_root):
        result = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        output_file = project_root / ".svp" / "gate_prompt.md"
        file_content = output_file.read_text()
        assert file_content == result


# ---------------------------------------------------------------------------
# Contract: prepare_gate_prompt uses gate_id for lookup
# ---------------------------------------------------------------------------


class TestPrepareGatePromptGateIdDispatch:
    """Different gate IDs produce different prompts."""

    def test_different_gate_ids_produce_different_prompts(self, project_root):
        result_test_val = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        result_diag_dec = prepare_gate_prompt(
            project_root, "gate_3_2_diagnostic_decision"
        )
        assert result_test_val != result_diag_dec

    def test_gate_prompt_references_gate_id(self, project_root):
        gate_id = "gate_5_1_repo_test"
        result = prepare_gate_prompt(project_root, gate_id)
        # The prompt should reference the gate in some form
        assert "gate_5_1" in result or "repo_test" in result or gate_id in result

    def test_gate_prompt_includes_response_options(self, project_root):
        """The gate prompt should contain response options for the human."""
        result = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        # gate_3_1_test_validation has options: TEST CORRECT, TEST WRONG
        assert "TEST CORRECT" in result or "TEST WRONG" in result


# ---------------------------------------------------------------------------
# Contract: prepare_gate_prompt accepts optional context
# ---------------------------------------------------------------------------


class TestPrepareGatePromptContext:
    """The optional context parameter affects the gate prompt output."""

    def test_context_affects_gate_prompt(self, project_root):
        result_with = prepare_gate_prompt(
            project_root, "gate_3_1_test_validation", context="Review test carefully."
        )
        result_without = prepare_gate_prompt(
            project_root, "gate_3_1_test_validation", context=None
        )
        assert result_with != result_without

    def test_context_content_appears_in_output(self, project_root):
        context_str = "Additional gate context for reviewer."
        result = prepare_gate_prompt(
            project_root, "gate_3_1_test_validation", context=context_str
        )
        assert context_str in result


# ---------------------------------------------------------------------------
# Contract: prepare_gate_prompt covers all 31 gate IDs
# ---------------------------------------------------------------------------


class TestPrepareGatePromptAllGates:
    """Every gate ID in ALL_GATE_IDS can be used with prepare_gate_prompt."""

    @pytest.mark.parametrize("gate_id", EXPECTED_GATE_IDS)
    def test_gate_prompt_accepts_every_gate_id(self, project_root, gate_id):
        result = prepare_gate_prompt(project_root, gate_id)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Contract: build_unit_context returns context with dependencies
# ---------------------------------------------------------------------------


class TestBuildUnitContext:
    """build_unit_context extracts unit definition and includes upstream
    dependency contracts."""

    def test_returns_string(self, blueprint_dir):
        result = build_unit_context(blueprint_dir, unit_number=5)
        assert isinstance(result, str)

    def test_returns_nonempty_string(self, blueprint_dir):
        result = build_unit_context(blueprint_dir, unit_number=5)
        assert len(result) > 0

    def test_includes_unit_reference(self, blueprint_dir):
        """The context should reference the requested unit."""
        result = build_unit_context(blueprint_dir, unit_number=5)
        assert "5" in result or "Unit 5" in result

    def test_include_tier1_true_includes_tier1(self, blueprint_dir):
        result_with = build_unit_context(
            blueprint_dir, unit_number=5, include_tier1=True
        )
        result_without = build_unit_context(
            blueprint_dir, unit_number=5, include_tier1=False
        )
        # With tier1 should produce different (typically longer) output
        assert result_with != result_without

    def test_include_tier1_default_is_true(self, blueprint_dir):
        """Default include_tier1=True should match explicit True."""
        result_default = build_unit_context(blueprint_dir, unit_number=5)
        result_explicit = build_unit_context(
            blueprint_dir, unit_number=5, include_tier1=True
        )
        assert result_default == result_explicit

    def test_different_units_produce_different_context(self, blueprint_dir):
        result_1 = build_unit_context(blueprint_dir, unit_number=1)
        result_5 = build_unit_context(blueprint_dir, unit_number=5)
        assert result_1 != result_5


# ---------------------------------------------------------------------------
# Contract: build_language_context returns formatted language block
# ---------------------------------------------------------------------------


class TestBuildLanguageContext:
    """build_language_context returns a formatted block with language metadata."""

    def test_returns_string(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert isinstance(result, str)

    def test_returns_nonempty_for_known_agent(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert len(result) > 0

    def test_includes_language_name(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert "python" in result.lower() or "Python" in result

    def test_includes_test_framework(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert "pytest" in result

    def test_includes_file_extension(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert ".py" in result

    def test_includes_agent_specific_guidance(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert "pytest conventions" in result

    def test_impl_agent_gets_different_guidance(self):
        result_test = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        result_impl = build_language_context(
            "python", "implementation_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert result_test != result_impl

    def test_empty_string_for_agent_without_prompts(self):
        """Agent types without language-specific prompts get empty string."""
        result = build_language_context(
            "python", "setup_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert result == ""

    def test_empty_string_for_redo_agent(self):
        result = build_language_context(
            "python", "redo_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert result == ""

    def test_includes_quality_tools(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        # Quality tool info should be present
        assert (
            "ruff" in result.lower()
            or "quality" in result.lower()
            or "linter" in result.lower()
        )

    def test_r_language_context(self):
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        result = build_language_context("r", "test_agent", combined_registry)
        assert "testthat" in result
        assert ".R" in result

    def test_build_language_context_reflects_synced_primary_language(self):
        """Bug S3-154 downstream anchor: when gate_0_3 sync sets
        state.primary_language to 'r', build_language_context returns an
        R-flavored block (testthat / .R / R display name), not Python defaults.
        """
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        # Simulate post-sync state value
        synced_primary_language = "r"
        result = build_language_context(
            synced_primary_language, "test_agent", combined_registry
        )
        # R-flavored metadata present
        assert "testthat" in result
        assert ".R" in result
        assert "R" in result
        # Python defaults absent
        assert "pytest" not in result
        assert ".py" not in result

    def test_coverage_review_agent_gets_guidance(self):
        result = build_language_context(
            "python", "coverage_review_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert len(result) > 0
        assert "coverage" in result.lower()


# ---------------------------------------------------------------------------
# Contract: Sentinel injection for stub-checking agents (Bug S3-2, S3-4)
# ---------------------------------------------------------------------------


class TestSentinelInjection:
    """For test_agent, implementation_agent, and coverage_review_agent,
    the LANGUAGE_CONTEXT must include the verbatim stub_sentinel value
    from the language registry."""

    def test_python_sentinel_in_test_agent_context(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert PYTHON_STUB_SENTINEL in result

    def test_python_sentinel_in_implementation_agent_context(self):
        result = build_language_context(
            "python", "implementation_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert PYTHON_STUB_SENTINEL in result

    def test_python_sentinel_in_coverage_review_agent_context(self):
        result = build_language_context(
            "python", "coverage_review_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert PYTHON_STUB_SENTINEL in result

    def test_r_sentinel_in_test_agent_context(self):
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        result = build_language_context("r", "test_agent", combined_registry)
        assert R_STUB_SENTINEL in result

    def test_r_sentinel_in_implementation_agent_context(self):
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        result = build_language_context("r", "implementation_agent", combined_registry)
        assert R_STUB_SENTINEL in result

    def test_r_sentinel_in_coverage_review_agent_context(self):
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        result = build_language_context("r", "coverage_review_agent", combined_registry)
        assert R_STUB_SENTINEL in result

    def test_sentinel_not_injected_for_non_stub_checking_agent(self):
        """Agents that do not check stubs should not necessarily have the sentinel."""
        # setup_agent has no language-specific prompts, returns empty
        result = build_language_context(
            "python", "setup_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert PYTHON_STUB_SENTINEL not in result

    @pytest.mark.parametrize("agent_type", SENTINEL_CHECKING_AGENTS)
    def test_all_sentinel_agents_get_python_sentinel(self, agent_type):
        result = build_language_context("python", agent_type, SAMPLE_LANGUAGE_REGISTRY)
        assert PYTHON_STUB_SENTINEL in result


# ---------------------------------------------------------------------------
# Contract: LANGUAGE_CONTEXT injected for all Stage 3 agents
# ---------------------------------------------------------------------------


class TestLanguageContextInjectedInTaskPrompt:
    """prepare_task_prompt injects LANGUAGE_CONTEXT via build_language_context
    for all Stage 3 agents."""

    def test_test_agent_prompt_contains_language_context_marker(self, project_root):
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        # Should contain some form of language context section
        assert "LANGUAGE_CONTEXT" in result or "python" in result.lower()

    def test_implementation_agent_prompt_contains_language_info(self, project_root):
        result = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=5
        )
        assert "LANGUAGE_CONTEXT" in result or "python" in result.lower()

    def test_diagnostic_agent_prompt_contains_language_info(self, project_root):
        result = prepare_task_prompt(project_root, "diagnostic_agent", unit_number=5)
        assert "LANGUAGE_CONTEXT" in result or "python" in result.lower()


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt deterministic
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptDeterminism:
    """Same inputs always produce the same output."""

    def test_deterministic_for_test_agent(self, project_root):
        a = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        b = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert a == b

    def test_deterministic_for_gate_prompt(self, project_root):
        a = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        b = prepare_gate_prompt(project_root, "gate_3_1_test_validation")
        assert a == b

    def test_deterministic_for_help_agent(self, project_root):
        a = prepare_task_prompt(project_root, "help_agent")
        b = prepare_task_prompt(project_root, "help_agent")
        assert a == b


# ---------------------------------------------------------------------------
# Contract: build_language_context deterministic
# ---------------------------------------------------------------------------


class TestBuildLanguageContextDeterminism:
    """Same inputs always produce the same output."""

    def test_deterministic_python_test_agent(self):
        a = build_language_context("python", "test_agent", SAMPLE_LANGUAGE_REGISTRY)
        b = build_language_context("python", "test_agent", SAMPLE_LANGUAGE_REGISTRY)
        assert a == b

    def test_deterministic_for_agent_without_prompts(self):
        a = build_language_context("python", "setup_agent", SAMPLE_LANGUAGE_REGISTRY)
        b = build_language_context("python", "setup_agent", SAMPLE_LANGUAGE_REGISTRY)
        assert a == b


# ---------------------------------------------------------------------------
# Contract: main CLI entry point
# ---------------------------------------------------------------------------


class TestMainCli:
    """main parses CLI arguments and invokes the appropriate function."""

    def test_main_with_agent_and_project_root(self, project_root):
        main(
            [
                "--agent",
                "test_agent",
                "--project-root",
                str(project_root),
                "--unit",
                "5",
            ]
        )
        output_file = project_root / ".svp" / "task_prompt.md"
        assert output_file.exists()

    def test_main_with_gate_flag(self, project_root):
        main(
            [
                "--gate",
                "gate_3_1_test_validation",
                "--project-root",
                str(project_root),
            ]
        )
        output_file = project_root / ".svp" / "gate_prompt.md"
        assert output_file.exists()

    def test_main_with_mode_flag(self, project_root):
        main(
            [
                "--agent",
                "setup_agent",
                "--project-root",
                str(project_root),
                "--mode",
                "context",
            ]
        )
        output_file = project_root / ".svp" / "task_prompt.md"
        assert output_file.exists()

    def test_main_with_context_flag(self, project_root):
        main(
            [
                "--agent",
                "test_agent",
                "--project-root",
                str(project_root),
                "--unit",
                "5",
                "--context",
                "Extra context string.",
            ]
        )
        output_file = project_root / ".svp" / "task_prompt.md"
        content = output_file.read_text()
        assert "Extra context string." in content

    def test_main_with_output_flag(self, project_root):
        custom_output = project_root / "custom_prompt.md"
        main(
            [
                "--agent",
                "test_agent",
                "--project-root",
                str(project_root),
                "--unit",
                "5",
                "--output",
                str(custom_output),
            ]
        )
        assert custom_output.exists()

    def test_main_with_ladder_flag(self, project_root):
        """--ladder flag is accepted without error."""
        main(
            [
                "--agent",
                "implementation_agent",
                "--project-root",
                str(project_root),
                "--unit",
                "5",
                "--ladder",
                "diagnostic_impl",
            ]
        )
        output_file = project_root / ".svp" / "task_prompt.md"
        assert output_file.exists()

    def test_main_with_revision_mode_flag(self, project_root):
        """--revision-mode flag is accepted without error."""
        main(
            [
                "--agent",
                "stakeholder_dialog",
                "--project-root",
                str(project_root),
                "--mode",
                "revision",
                "--revision-mode",
            ]
        )
        output_file = project_root / ".svp" / "task_prompt.md"
        assert output_file.exists()

    def test_main_with_quality_report_flag(self, project_root):
        """--quality-report flag is accepted and injected into prompt."""
        report_path = project_root / "quality_report.txt"
        report_path.write_text("Quality report: 3 issues found.")
        main(
            [
                "--agent",
                "test_agent",
                "--project-root",
                str(project_root),
                "--unit",
                "5",
                "--quality-report",
                str(report_path),
            ]
        )
        output_file = project_root / ".svp" / "task_prompt.md"
        assert output_file.exists()

    def test_main_defaults_argv_to_sys_argv(self, project_root):
        """When argv is None, main should read from sys.argv."""
        import sys

        original_argv = sys.argv
        try:
            sys.argv = [
                "prepare_task",
                "--agent",
                "test_agent",
                "--project-root",
                str(project_root),
                "--unit",
                "5",
            ]
            main(None)
            output_file = project_root / ".svp" / "task_prompt.md"
            assert output_file.exists()
        finally:
            sys.argv = original_argv


# ---------------------------------------------------------------------------
# Contract: Per-agent-type specifics in task prompts
# ---------------------------------------------------------------------------


class TestPerAgentTypePromptContent:
    """Each agent type includes appropriate content in the generated prompt."""

    def test_stakeholder_reviewer_loads_spec(self, project_root):
        """stakeholder_reviewer loads spec and review checklist."""
        result = prepare_task_prompt(project_root, "stakeholder_reviewer")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_blueprint_checker_loads_spec_and_blueprint(self, project_root):
        """blueprint_checker loads spec, blueprint (both), alignment checklist."""
        result = prepare_task_prompt(project_root, "blueprint_checker")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reference_indexing_loads_reference_paths(self, project_root):
        result = prepare_task_prompt(project_root, "reference_indexing")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_redo_agent_loads_state_summary(self, project_root):
        result = prepare_task_prompt(project_root, "redo_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_checklist_generation_loads_spec(self, project_root):
        result = prepare_task_prompt(project_root, "checklist_generation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_regression_adaptation_loads_failing_tests(self, project_root):
        result = prepare_task_prompt(project_root, "regression_adaptation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_coverage_review_agent_loads_contracts(self, project_root):
        result = prepare_task_prompt(project_root, "coverage_review", unit_number=5)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Contract: Different unit numbers produce different task prompts
# ---------------------------------------------------------------------------


class TestUnitNumberAffectsPrompt:
    """The unit_number parameter changes the generated prompt."""

    def test_different_units_produce_different_test_agent_prompts(self, project_root):
        result_5 = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        result_1 = prepare_task_prompt(project_root, "test_agent", unit_number=1)
        assert result_5 != result_1

    def test_different_units_produce_different_impl_agent_prompts(self, project_root):
        result_5 = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=5
        )
        result_1 = prepare_task_prompt(
            project_root, "implementation_agent", unit_number=1
        )
        assert result_5 != result_1

    def test_unit_number_appears_in_prompt(self, project_root):
        result = prepare_task_prompt(project_root, "test_agent", unit_number=7)
        assert "7" in result


# ---------------------------------------------------------------------------
# Contract: Convergent gate paths (SC-20)
# ---------------------------------------------------------------------------


class TestConvergentGatePaths:
    """prepare_gate_prompt distinguishes convergent gate paths using
    pipeline state."""

    def test_gate_prompt_reads_pipeline_state(self, project_root):
        """Gate prompts incorporate state context."""
        result = prepare_gate_prompt(project_root, "gate_3_2_diagnostic_decision")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_with_different_state_may_differ(self, project_root):
        """Changing pipeline state may alter the gate prompt for convergent gates."""
        result_1 = prepare_gate_prompt(project_root, "gate_3_2_diagnostic_decision")
        # Modify state to represent a different convergent path
        modified_state = dict(MINIMAL_PIPELINE_STATE)
        modified_state["sub_stage"] = "diagnostic"
        (project_root / ".svp" / "pipeline_state.json").write_text(json.dumps(modified_state))
        result_2 = prepare_gate_prompt(project_root, "gate_3_2_diagnostic_decision")
        # At minimum, both should be valid; they may or may not differ
        # depending on whether this gate has convergent paths in this state
        assert isinstance(result_1, str)
        assert isinstance(result_2, str)


# ---------------------------------------------------------------------------
# Contract: load_blueprint functions handle Path objects
# ---------------------------------------------------------------------------


class TestBlueprintLoadPathHandling:
    """Blueprint loading functions accept Path objects."""

    def test_load_blueprint_accepts_path_object(self, blueprint_dir):
        assert isinstance(blueprint_dir, Path)
        result = load_blueprint(blueprint_dir)
        assert isinstance(result, str)

    def test_load_contracts_accepts_path_object(self, blueprint_dir):
        assert isinstance(blueprint_dir, Path)
        result = load_blueprint_contracts_only(blueprint_dir)
        assert isinstance(result, str)

    def test_load_prose_accepts_path_object(self, blueprint_dir):
        assert isinstance(blueprint_dir, Path)
        result = load_blueprint_prose_only(blueprint_dir)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Contract: prepare_task_prompt accepts Path for project_root
# ---------------------------------------------------------------------------


class TestPrepareTaskPromptPathHandling:
    """prepare_task_prompt accepts Path objects for project_root."""

    def test_accepts_path_object(self, project_root):
        assert isinstance(project_root, Path)
        result = prepare_task_prompt(project_root, "test_agent", unit_number=5)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Contract: Full agent type matrix -- every agent type produces a prompt
# ---------------------------------------------------------------------------


class TestGitRepoAgentCanonicalPathInjection:
    """Bug S3-112: _prepare_git_repo_agent must inject the canonical
    delivered repo path as a REQUIRED directive, computed from
    (project_root.parent, profile_name)."""

    def test_prepare_injects_delivered_repo_path_section(self, project_root):
        prompt = prepare_task_prompt(project_root, "git_repo_agent")
        assert "Delivered Repo Path (REQUIRED)" in prompt

    def test_prepare_injects_absolute_canonical_path(self, project_root):
        """The injected path must be absolute and match the sibling convention."""
        prompt = prepare_task_prompt(project_root, "git_repo_agent")
        # MINIMAL_PROFILE has no "name", so falls back to project_root.name
        expected_path = (project_root.parent / f"{project_root.name}-repo").resolve()
        assert str(expected_path) in prompt
        # Ensure it's absolute and starts at filesystem root (Unix test env).
        assert str(expected_path).startswith("/")

    def test_prepare_injects_required_directive(self, project_root):
        """The prompt must contain the MUST directive and forbidden-destination warning."""
        prompt = prepare_task_prompt(project_root, "git_repo_agent")
        assert "MUST place the delivered repository" in prompt
        assert "assemble_python_project" in prompt
        assert "./delivered/" in prompt  # mentioned in the prohibition
        assert "S3-112" in prompt

    def test_prepare_uses_profile_name_when_present(self, tmp_path):
        """When profile["name"] is set, it wins over project_root.name."""
        project_root = tmp_path / "some_random_dir"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        (project_root / "blueprint").mkdir()
        (project_root / "blueprint" / "blueprint_prose.md").write_text(BLUEPRINT_PROSE_CONTENT)
        (project_root / "blueprint" / "blueprint_contracts.md").write_text(BLUEPRINT_CONTRACTS_CONTENT)
        (project_root / ".svp" / "pipeline_state.json").write_text(json.dumps(MINIMAL_PIPELINE_STATE))
        profile = {"name": "foo", "archetype": "python_project", "language": {"primary": "python"}}
        (project_root / "project_profile.json").write_text(json.dumps(profile))
        (project_root / "toolchain.json").write_text(json.dumps(MINIMAL_TOOLCHAIN))

        prompt = prepare_task_prompt(project_root, "git_repo_agent")
        expected = (project_root.parent / "foo-repo").resolve()
        assert str(expected) in prompt

    def test_prepare_falls_back_to_project_root_name_when_profile_missing(self, tmp_path):
        """No project_profile.json → fallback to project_root.name."""
        project_root = tmp_path / "bareproject"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        (project_root / "blueprint").mkdir()
        (project_root / "blueprint" / "blueprint_prose.md").write_text(BLUEPRINT_PROSE_CONTENT)
        (project_root / "blueprint" / "blueprint_contracts.md").write_text(BLUEPRINT_CONTRACTS_CONTENT)
        (project_root / ".svp" / "pipeline_state.json").write_text(json.dumps(MINIMAL_PIPELINE_STATE))
        (project_root / "toolchain.json").write_text(json.dumps(MINIMAL_TOOLCHAIN))
        # Deliberately NO project_profile.json.

        prompt = prepare_task_prompt(project_root, "git_repo_agent")
        expected = (project_root.parent / "bareproject-repo").resolve()
        assert str(expected) in prompt


class TestAllAgentTypesProducePrompts:
    """Every known agent type produces a valid task prompt without error."""

    @pytest.mark.parametrize(
        "agent_type",
        [
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
        ],
    )
    def test_agent_type_produces_valid_prompt(self, project_root, agent_type):
        # Some agents need mode or unit_number; provide defaults
        kwargs = {}
        if agent_type in (
            "test_agent",
            "implementation_agent",
            "diagnostic_agent",
            "integration_test_author",
            "coverage_review",
        ):
            kwargs["unit_number"] = 5
        if agent_type == "setup_agent":
            kwargs["mode"] = "context"
        if agent_type in ("stakeholder_dialog", "blueprint_author"):
            kwargs["mode"] = "draft"
        result = prepare_task_prompt(project_root, agent_type, **kwargs)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Contract: Selective loading matrix values constrain blueprint loading calls
# ---------------------------------------------------------------------------


class TestSelectiveLoadingMatrixValues:
    """Only three valid values exist in the matrix: contracts_only, prose_only, both."""

    def test_no_unknown_values_in_matrix(self):
        allowed = {"contracts_only", "prose_only", "both"}
        for agent_type, mode in SELECTIVE_LOADING_MATRIX.items():
            assert mode in allowed, (
                f"Unknown loading mode '{mode}' for agent '{agent_type}'"
            )

    def test_contracts_only_agents(self):
        contracts_agents = {
            k for k, v in SELECTIVE_LOADING_MATRIX.items() if v == "contracts_only"
        }
        expected = {
            "test_agent",
            "implementation_agent",
            "integration_test_author",
            "git_repo_agent",
            "coverage_review_agent",
        }
        assert contracts_agents == expected

    def test_prose_only_agents(self):
        prose_agents = {
            k for k, v in SELECTIVE_LOADING_MATRIX.items() if v == "prose_only"
        }
        expected = {"help_agent"}
        assert prose_agents == expected

    def test_both_agents(self):
        both_agents = {k for k, v in SELECTIVE_LOADING_MATRIX.items() if v == "both"}
        expected = {
            "diagnostic_agent",
            "hint_agent",
            "bug_triage_agent",
            "repair_agent",
            "blueprint_author",
            "blueprint_checker",
            "blueprint_reviewer",
            "oracle_agent",
        }
        assert both_agents == expected


# ---------------------------------------------------------------------------
# Contract: build_language_context with different languages
# ---------------------------------------------------------------------------


class TestBuildLanguageContextDifferentLanguages:
    """Different languages produce different context blocks."""

    def test_python_and_r_produce_different_context(self):
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        result_py = build_language_context("python", "test_agent", combined_registry)
        result_r = build_language_context("r", "test_agent", combined_registry)
        assert result_py != result_r

    def test_python_context_mentions_py_extension(self):
        result = build_language_context(
            "python", "test_agent", SAMPLE_LANGUAGE_REGISTRY
        )
        assert ".py" in result

    def test_r_context_mentions_r_extension(self):
        combined_registry = {**SAMPLE_LANGUAGE_REGISTRY, **SAMPLE_LANGUAGE_REGISTRY_R}
        result = build_language_context("r", "test_agent", combined_registry)
        assert ".R" in result


# ---------------------------------------------------------------------------
# Bug S3-159: Multi-mode agent prompts must stamp explicit Mode and
# Expected Terminal Status blocks (not the legacy inline `**Mode:**`).
# ---------------------------------------------------------------------------


class TestS3_159MultiModePromptBlocks:
    """The _prepare_* helpers for multi-mode agents stamp two explicit
    markdown blocks into the task prompt: `## Mode` and
    `## Expected Terminal Status` listing the canonical valid status lines
    for that (agent, mode) pair."""

    def test_prepare_setup_agent_project_context_stamps_mode_and_expected_status_blocks(
        self, project_root
    ):
        result = prepare_task_prompt(
            project_root, "setup_agent", mode="project_context"
        )
        # Explicit mode block (heading form, not inline `**Mode:**`).
        assert "## Mode" in result
        assert "project_context" in result
        # Explicit expected terminal status block listing both project_context
        # statuses.
        assert "## Expected Terminal Status" in result
        assert "PROJECT_CONTEXT_COMPLETE" in result
        assert "PROJECT_CONTEXT_REJECTED" in result
        # Profile-mode-only status must NOT appear.
        assert "PROFILE_COMPLETE" not in result

    def test_prepare_setup_agent_project_profile_stamps_mode_and_expected_status_blocks(
        self, project_root
    ):
        result = prepare_task_prompt(
            project_root, "setup_agent", mode="project_profile"
        )
        assert "## Mode" in result
        assert "project_profile" in result
        assert "## Expected Terminal Status" in result
        assert "PROFILE_COMPLETE" in result
        # Context-mode statuses must NOT appear.
        assert "PROJECT_CONTEXT_COMPLETE" not in result
        assert "PROJECT_CONTEXT_REJECTED" not in result

    def test_prepare_stakeholder_dialog_draft_stamps_mode_and_expected_status_blocks(
        self, project_root
    ):
        result = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="draft"
        )
        assert "## Mode" in result
        # The literal mode word "draft" appears in the Mode block.
        # (Anchor on the heading form to avoid false-matches against
        # surrounding prose.)
        assert "## Mode\n\ndraft" in result
        assert "## Expected Terminal Status" in result
        assert "SPEC_DRAFT_COMPLETE" in result
        # Revision-mode-only status must NOT appear.
        assert "SPEC_REVISION_COMPLETE" not in result


# ---------------------------------------------------------------------------
# Bug S3-165: Conditional STAKEHOLDER_DIALOG_STATISTICAL_PRIMER append
# ---------------------------------------------------------------------------


def _write_pipeline_state(project_root, requires_stats):
    """Helper: rewrite the project's pipeline_state.json with the given
    requires_statistical_analysis flag (everything else minimal)."""
    state_path = project_root / ".svp" / "pipeline_state.json"
    state_data = dict(MINIMAL_PIPELINE_STATE)
    state_data["requires_statistical_analysis"] = bool(requires_stats)
    state_path.write_text(json.dumps(state_data))


class TestPrepareStakeholderDialogStatisticalPrimerAppend:
    """Bug S3-165: _prepare_stakeholder_dialog must append
    STAKEHOLDER_DIALOG_STATISTICAL_PRIMER to the assembled task prompt
    iff state.requires_statistical_analysis is True. When the flag is False
    or state is None (legacy callers), the primer must NOT appear."""

    _PRIMER_MARKER = "Statistical Analysis Primer"

    def test_prepare_stakeholder_dialog_appends_primer_when_flag_true(
        self, project_root
    ):
        """When the loaded state has requires_statistical_analysis=True, the
        primer's distinctive substring must appear in the generated prompt."""
        _write_pipeline_state(project_root, requires_stats=True)
        result = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="draft"
        )
        assert self._PRIMER_MARKER in result, (
            "When state.requires_statistical_analysis=True, "
            "STAKEHOLDER_DIALOG_STATISTICAL_PRIMER must be appended to "
            "the stakeholder_dialog task prompt (Bug S3-165)."
        )

    def test_prepare_stakeholder_dialog_omits_primer_when_flag_false(
        self, project_root
    ):
        """When the loaded state has requires_statistical_analysis=False, the
        primer's distinctive substring must NOT appear in the prompt."""
        _write_pipeline_state(project_root, requires_stats=False)
        result = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="draft"
        )
        assert self._PRIMER_MARKER not in result, (
            "When state.requires_statistical_analysis=False, "
            "STAKEHOLDER_DIALOG_STATISTICAL_PRIMER must NOT be appended "
            "(Bug S3-165 — append is conditional on the profile flag)."
        )

    def test_prepare_stakeholder_dialog_omits_primer_when_state_none(
        self, project_root
    ):
        """When pipeline_state.json is absent (state=None), the primer must
        NOT be appended (defensive guard for legacy callers)."""
        # Remove pipeline_state.json so _get_state_safe returns None.
        state_path = project_root / ".svp" / "pipeline_state.json"
        if state_path.exists():
            state_path.unlink()
        result = prepare_task_prompt(
            project_root, "stakeholder_dialog", mode="draft"
        )
        assert self._PRIMER_MARKER not in result, (
            "When state is None (no pipeline_state.json), "
            "STAKEHOLDER_DIALOG_STATISTICAL_PRIMER must NOT be appended "
            "(Bug S3-165 — defensive guard against legacy callers)."
        )


# ---------------------------------------------------------------------------
# Bug S3-166: Conditional BLUEPRINT_AUTHOR_STATISTICAL_PRIMER append
# ---------------------------------------------------------------------------


class TestPrepareBlueprintAuthorStatisticalPrimerAppend:
    """Bug S3-166: _prepare_blueprint_author must append
    BLUEPRINT_AUTHOR_STATISTICAL_PRIMER to the assembled task prompt iff
    state.requires_statistical_analysis is True. When the flag is False
    or state is None (legacy callers), the primer must NOT appear."""

    _PRIMER_MARKER = "Library-version pinning"

    def test_prepare_blueprint_author_appends_primer_when_flag_true(
        self, project_root
    ):
        """When the loaded state has requires_statistical_analysis=True,
        the primer's distinctive substring must appear in the generated
        prompt."""
        _write_pipeline_state(project_root, requires_stats=True)
        result = prepare_task_prompt(
            project_root, "blueprint_author", mode="draft"
        )
        assert self._PRIMER_MARKER in result, (
            "When state.requires_statistical_analysis=True, "
            "BLUEPRINT_AUTHOR_STATISTICAL_PRIMER must be appended to "
            "the blueprint_author task prompt (Bug S3-166)."
        )

    def test_prepare_blueprint_author_omits_primer_when_flag_false(
        self, project_root
    ):
        """When the loaded state has requires_statistical_analysis=False,
        the primer's distinctive substring must NOT appear."""
        _write_pipeline_state(project_root, requires_stats=False)
        result = prepare_task_prompt(
            project_root, "blueprint_author", mode="draft"
        )
        assert self._PRIMER_MARKER not in result, (
            "When state.requires_statistical_analysis=False, "
            "BLUEPRINT_AUTHOR_STATISTICAL_PRIMER must NOT be appended "
            "(Bug S3-166 — append is conditional on the profile flag)."
        )

    def test_prepare_blueprint_author_omits_primer_when_state_none(
        self, project_root
    ):
        """When pipeline_state.json is absent (state=None), the primer
        must NOT be appended (defensive guard for legacy callers)."""
        state_path = project_root / ".svp" / "pipeline_state.json"
        if state_path.exists():
            state_path.unlink()
        result = prepare_task_prompt(
            project_root, "blueprint_author", mode="draft"
        )
        assert self._PRIMER_MARKER not in result, (
            "When state is None (no pipeline_state.json), "
            "BLUEPRINT_AUTHOR_STATISTICAL_PRIMER must NOT be appended "
            "(Bug S3-166 — defensive guard against legacy callers)."
        )
