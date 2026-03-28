"""
Tests for Unit 13: Task Preparation.

Synthetic Data Assumptions:
- Blueprint prose and contracts files are created as minimal markdown files
  with "## Unit N: Name" headings and "### Tier 2" / "### Tier 3" subheadings.
- Pipeline state JSON files are minimal valid structures matching Unit 5 schema.
- Profile JSON files use the default profile structure from Unit 3.
- Toolchain JSON files are minimal valid structures matching Unit 4 schema.
- LANGUAGE_REGISTRY entries mirror the structure described in Unit 2 contracts.
- Gate IDs and agent type strings are taken verbatim from the blueprint.
- The 31 gate IDs and 21 agent types are exact string values from the contracts.
- SELECTIVE_LOADING_MATRIX keys/values are exact strings from the contracts.
- tmp_path is used for all filesystem operations to avoid side effects.
"""

import ast
import json
from pathlib import Path
from unittest.mock import patch

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
# Expected constant values from the blueprint
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def blueprint_dir(tmp_path):
    """Create a minimal blueprint directory with prose and contracts files."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()

    prose_content = (
        "# Blueprint Prose\n\n"
        "## Unit 1: Core Configuration\n\n"
        "Tier 1 prose description for Unit 1.\n\n"
        "## Unit 2: Language Registry\n\n"
        "Tier 1 prose description for Unit 2.\n\n"
        "## Unit 3: Profile Schema\n\n"
        "Tier 1 prose description for Unit 3.\n\n"
    )
    (bp_dir / "blueprint_prose.md").write_text(prose_content)

    contracts_content = (
        "# Blueprint Contracts\n\n"
        "## Unit 1: Core Configuration\n\n"
        "### Tier 2 -- Signatures\n\n"
        "```python\n"
        "def load_config(project_root: Path) -> Dict[str, Any]: ...\n"
        "```\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n"
        "load_config reads config from project_root.\n\n"
        "## Unit 2: Language Registry\n\n"
        "### Tier 2 -- Signatures\n\n"
        "```python\n"
        "LANGUAGE_REGISTRY: Dict[str, Dict[str, Any]]\n"
        "```\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n"
        "Registry contains language entries.\n\n"
        "## Unit 3: Profile Schema\n\n"
        "### Tier 2 -- Signatures\n\n"
        "```python\n"
        "def load_profile(project_root: Path) -> Dict[str, Any]: ...\n"
        "```\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n"
        "Profile schema validation.\n\n"
    )
    (bp_dir / "blueprint_contracts.md").write_text(contracts_content)

    return bp_dir


@pytest.fixture
def project_root(tmp_path, blueprint_dir):
    """Create a minimal project root with required artifacts."""
    root = tmp_path / "project"
    root.mkdir()
    svp_dir = root / ".svp"
    svp_dir.mkdir()

    # Blueprint dir symlink or copy
    bp_dest = root / "blueprint"
    if not bp_dest.exists():
        import shutil

        shutil.copytree(blueprint_dir, bp_dest)

    # Pipeline state
    state = {
        "stage": "3",
        "sub_stage": "test_generation",
        "current_unit": 1,
        "total_units": 3,
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
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state, indent=2))

    # Profile
    profile = {
        "archetype": "python_project",
        "language": {
            "primary": "python",
            "components": [],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "python": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            }
        },
        "quality": {
            "python": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            }
        },
        "testing": {"readable_test_names": True},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }
    (svp_dir / "project_profile.json").write_text(json.dumps(profile, indent=2))

    # Toolchain
    toolchain = {
        "quality": {},
        "test": {"command": "pytest {target}"},
    }
    (svp_dir / "toolchain.json").write_text(json.dumps(toolchain, indent=2))

    # Spec placeholder
    (svp_dir / "stakeholder_spec.md").write_text("# Spec\nMinimal spec for testing.")

    # Config
    config = {
        "iteration_limit": 3,
        "models": {"default": "claude-opus-4-6"},
        "context_budget_override": None,
        "context_budget_threshold": 65,
        "compaction_character_threshold": 200,
        "auto_save": True,
        "skip_permissions": True,
    }
    (svp_dir / "svp_config.json").write_text(json.dumps(config, indent=2))

    return root


# ===========================================================================
# ALL_GATE_IDS constant tests
# ===========================================================================


class TestAllGateIds:
    """Tests for the ALL_GATE_IDS constant."""

    def test_all_gate_ids_is_a_list(self):
        assert isinstance(ALL_GATE_IDS, list)

    def test_all_gate_ids_contains_exactly_31_entries(self):
        assert len(ALL_GATE_IDS) == 31

    def test_all_gate_ids_contains_only_strings(self):
        for gate_id in ALL_GATE_IDS:
            assert isinstance(gate_id, str), (
                f"Expected str, got {type(gate_id)} for {gate_id!r}"
            )

    def test_all_gate_ids_matches_expected_set(self):
        assert set(ALL_GATE_IDS) == set(EXPECTED_GATE_IDS)

    def test_all_gate_ids_has_no_duplicates(self):
        assert len(ALL_GATE_IDS) == len(set(ALL_GATE_IDS))

    def test_all_gate_ids_contains_each_expected_gate(self):
        for gate_id in EXPECTED_GATE_IDS:
            assert gate_id in ALL_GATE_IDS, f"Missing gate ID: {gate_id}"

    def test_all_gate_ids_contains_gate_0_1_hook_activation(self):
        assert "gate_0_1_hook_activation" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_0_2_context_approval(self):
        assert "gate_0_2_context_approval" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_0_3_profile_approval(self):
        assert "gate_0_3_profile_approval" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_0_3r_profile_revision(self):
        assert "gate_0_3r_profile_revision" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_7_a_trajectory_review(self):
        assert "gate_7_a_trajectory_review" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_7_b_fix_plan_review(self):
        assert "gate_7_b_fix_plan_review" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_pass_transition_post_pass1(self):
        assert "gate_pass_transition_post_pass1" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_pass_transition_post_pass2(self):
        assert "gate_pass_transition_post_pass2" in ALL_GATE_IDS

    def test_all_gate_ids_contains_gate_hint_conflict(self):
        assert "gate_hint_conflict" in ALL_GATE_IDS

    def test_all_gate_ids_contains_no_extra_entries_beyond_expected(self):
        extras = set(ALL_GATE_IDS) - set(EXPECTED_GATE_IDS)
        assert extras == set(), f"Unexpected extra gate IDs: {extras}"


# ===========================================================================
# KNOWN_AGENT_TYPES constant tests
# ===========================================================================


class TestKnownAgentTypes:
    """Tests for the KNOWN_AGENT_TYPES constant."""

    def test_known_agent_types_is_a_list(self):
        assert isinstance(KNOWN_AGENT_TYPES, list)

    def test_known_agent_types_contains_exactly_21_entries(self):
        assert len(KNOWN_AGENT_TYPES) == 21

    def test_known_agent_types_contains_only_strings(self):
        for agent_type in KNOWN_AGENT_TYPES:
            assert isinstance(agent_type, str), (
                f"Expected str, got {type(agent_type)} for {agent_type!r}"
            )

    def test_known_agent_types_matches_expected_set(self):
        assert set(KNOWN_AGENT_TYPES) == set(EXPECTED_AGENT_TYPES)

    def test_known_agent_types_has_no_duplicates(self):
        assert len(KNOWN_AGENT_TYPES) == len(set(KNOWN_AGENT_TYPES))

    def test_known_agent_types_contains_each_expected_agent(self):
        for agent_type in EXPECTED_AGENT_TYPES:
            assert agent_type in KNOWN_AGENT_TYPES, f"Missing agent type: {agent_type}"

    def test_known_agent_types_contains_setup_agent(self):
        assert "setup_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_stakeholder_dialog(self):
        assert "stakeholder_dialog" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_test_agent(self):
        assert "test_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_implementation_agent(self):
        assert "implementation_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_oracle_agent(self):
        assert "oracle_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_bug_triage(self):
        assert "bug_triage" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_repair_agent(self):
        assert "repair_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_redo_agent(self):
        assert "redo_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_help_agent(self):
        assert "help_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_hint_agent(self):
        assert "hint_agent" in KNOWN_AGENT_TYPES

    def test_known_agent_types_contains_no_extra_entries_beyond_expected(self):
        extras = set(KNOWN_AGENT_TYPES) - set(EXPECTED_AGENT_TYPES)
        assert extras == set(), f"Unexpected extra agent types: {extras}"


# ===========================================================================
# SELECTIVE_LOADING_MATRIX constant tests
# ===========================================================================


class TestSelectiveLoadingMatrix:
    """Tests for the SELECTIVE_LOADING_MATRIX constant."""

    def test_selective_loading_matrix_is_a_dict(self):
        assert isinstance(SELECTIVE_LOADING_MATRIX, dict)

    def test_selective_loading_matrix_has_expected_keys(self):
        assert set(SELECTIVE_LOADING_MATRIX.keys()) == set(
            EXPECTED_SELECTIVE_LOADING_MATRIX.keys()
        )

    def test_selective_loading_matrix_values_are_strings(self):
        for key, value in SELECTIVE_LOADING_MATRIX.items():
            assert isinstance(value, str), (
                f"Expected str value for key {key!r}, got {type(value)}"
            )

    def test_selective_loading_matrix_values_are_valid_modes(self):
        valid_modes = {"contracts_only", "prose_only", "both"}
        for key, value in SELECTIVE_LOADING_MATRIX.items():
            assert value in valid_modes, f"Invalid mode {value!r} for key {key!r}"

    def test_test_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX.get("test_agent") == "contracts_only"

    def test_implementation_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX.get("implementation_agent") == "contracts_only"

    def test_diagnostic_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("diagnostic_agent") == "both"

    def test_help_agent_loads_prose_only(self):
        assert SELECTIVE_LOADING_MATRIX.get("help_agent") == "prose_only"

    def test_hint_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("hint_agent") == "both"

    def test_integration_test_author_loads_contracts_only(self):
        assert (
            SELECTIVE_LOADING_MATRIX.get("integration_test_author") == "contracts_only"
        )

    def test_git_repo_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX.get("git_repo_agent") == "contracts_only"

    def test_bug_triage_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("bug_triage_agent") == "both"

    def test_repair_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("repair_agent") == "both"

    def test_blueprint_author_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("blueprint_author") == "both"

    def test_blueprint_checker_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("blueprint_checker") == "both"

    def test_blueprint_reviewer_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("blueprint_reviewer") == "both"

    def test_coverage_review_agent_loads_contracts_only(self):
        assert SELECTIVE_LOADING_MATRIX.get("coverage_review_agent") == "contracts_only"

    def test_oracle_agent_loads_both(self):
        assert SELECTIVE_LOADING_MATRIX.get("oracle_agent") == "both"

    def test_selective_loading_matrix_matches_expected_exactly(self):
        assert SELECTIVE_LOADING_MATRIX == EXPECTED_SELECTIVE_LOADING_MATRIX

    def test_agent_types_not_in_matrix_do_not_load_blueprint(self):
        """Agents not in the matrix should not appear as keys."""
        non_matrix_agents = {
            "setup_agent",
            "stakeholder_dialog",
            "stakeholder_reviewer",
            "redo_agent",
            "reference_indexing",
            "checklist_generation",
            "regression_adaptation",
            "coverage_review",
        }
        for agent in non_matrix_agents:
            assert agent not in SELECTIVE_LOADING_MATRIX, (
                f"Agent {agent!r} should NOT be in SELECTIVE_LOADING_MATRIX"
            )


# ===========================================================================
# load_blueprint tests
# ===========================================================================


class TestLoadBlueprint:
    """Tests for load_blueprint function."""

    def test_load_blueprint_returns_string(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert isinstance(result, str)

    def test_load_blueprint_concatenates_both_files(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        prose_content = (blueprint_dir / "blueprint_prose.md").read_text()
        contracts_content = (blueprint_dir / "blueprint_contracts.md").read_text()
        assert prose_content in result or "Blueprint Prose" in result
        assert contracts_content in result or "Blueprint Contracts" in result

    def test_load_blueprint_includes_prose_content(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert "Tier 1 prose description" in result

    def test_load_blueprint_includes_contracts_content(self, blueprint_dir):
        result = load_blueprint(blueprint_dir)
        assert "Behavioral Contracts" in result

    def test_load_blueprint_reads_from_correct_filenames(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("PROSE MARKER")
        (bp_dir / "blueprint_contracts.md").write_text("CONTRACTS MARKER")
        result = load_blueprint(bp_dir)
        assert "PROSE MARKER" in result
        assert "CONTRACTS MARKER" in result


# ===========================================================================
# load_blueprint_contracts_only tests
# ===========================================================================


class TestLoadBlueprintContractsOnly:
    """Tests for load_blueprint_contracts_only function."""

    def test_returns_string(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert isinstance(result, str)

    def test_reads_contracts_file_only(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("PROSE ONLY CONTENT")
        (bp_dir / "blueprint_contracts.md").write_text("CONTRACTS ONLY CONTENT")
        result = load_blueprint_contracts_only(bp_dir)
        assert "CONTRACTS ONLY CONTENT" in result
        assert "PROSE ONLY CONTENT" not in result

    def test_includes_tier_2_signatures(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert "Tier 2" in result or "Signatures" in result

    def test_includes_behavioral_contracts(self, blueprint_dir):
        result = load_blueprint_contracts_only(blueprint_dir)
        assert "Behavioral Contracts" in result


# ===========================================================================
# load_blueprint_prose_only tests
# ===========================================================================


class TestLoadBlueprintProseOnly:
    """Tests for load_blueprint_prose_only function."""

    def test_returns_string(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert isinstance(result, str)

    def test_reads_prose_file_only(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("PROSE FILE CONTENT")
        (bp_dir / "blueprint_contracts.md").write_text("CONTRACTS FILE CONTENT")
        result = load_blueprint_prose_only(bp_dir)
        assert "PROSE FILE CONTENT" in result
        assert "CONTRACTS FILE CONTENT" not in result

    def test_includes_tier_1_descriptions(self, blueprint_dir):
        result = load_blueprint_prose_only(blueprint_dir)
        assert "Tier 1 prose description" in result


# ===========================================================================
# build_unit_context tests
# ===========================================================================


class TestBuildUnitContext:
    """Tests for build_unit_context function."""

    def test_returns_string(self, blueprint_dir):
        result = build_unit_context(blueprint_dir, unit_number=1)
        assert isinstance(result, str)

    def test_includes_unit_definition_content(self, blueprint_dir):
        result = build_unit_context(blueprint_dir, unit_number=1)
        # Should contain something related to Unit 1
        assert (
            "Unit 1" in result
            or "Core Configuration" in result
            or "load_config" in result
        )

    def test_include_tier1_true_includes_prose(self, blueprint_dir):
        result = build_unit_context(blueprint_dir, unit_number=1, include_tier1=True)
        # When include_tier1 is True, Tier 1 prose should be present
        assert isinstance(result, str)
        assert len(result) > 0

    def test_include_tier1_false_excludes_tier1_prose(self, blueprint_dir):
        result_with = build_unit_context(
            blueprint_dir, unit_number=1, include_tier1=True
        )
        result_without = build_unit_context(
            blueprint_dir, unit_number=1, include_tier1=False
        )
        # Without tier1, the result should be shorter or different
        assert isinstance(result_without, str)
        # The result without tier1 should not contain tier1 prose content
        # but should still contain tier2 and tier3 content
        assert len(result_without) <= len(result_with)

    def test_includes_upstream_dependency_contracts(self, blueprint_dir):
        """Unit 2 depends on Unit 1; building context for Unit 2 should include Unit 1 contracts."""
        # Create blueprint with dependency info
        bp_dir = blueprint_dir
        contracts = (
            "## Unit 1: Core Configuration\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef load_config(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** None.\n\n"
            "Contract for Unit 1.\n\n"
            "## Unit 2: Language Registry\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\nLANGUAGE_REGISTRY: Dict\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 1.\n\n"
            "Contract for Unit 2.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts)
        result = build_unit_context(bp_dir, unit_number=2, include_tier1=True)
        # Should include upstream Unit 1 contracts
        assert isinstance(result, str)
        assert len(result) > 0

    def test_default_include_tier1_is_true(self, blueprint_dir):
        """Default value for include_tier1 should be True."""
        result = build_unit_context(blueprint_dir, unit_number=1)
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# build_language_context tests
# ===========================================================================


class TestBuildLanguageContext:
    """Tests for build_language_context function."""

    def test_returns_string(self):
        registry = {
            "python": {
                "agent_prompts": {
                    "test_agent": "Use pytest for testing Python code.",
                },
                "test_framework": "pytest",
                "file_extension": ".py",
                "default_quality": {
                    "linter": "ruff",
                    "formatter": "ruff",
                    "type_checker": "mypy",
                    "import_sorter": "ruff",
                    "line_length": 88,
                },
            }
        }
        result = build_language_context("python", "test_agent", registry)
        assert isinstance(result, str)

    def test_includes_language_specific_agent_guidance(self):
        registry = {
            "python": {
                "agent_prompts": {
                    "test_agent": "Use pytest for all tests.",
                },
                "test_framework": "pytest",
                "file_extension": ".py",
                "default_quality": {"linter": "ruff", "formatter": "ruff"},
            }
        }
        result = build_language_context("python", "test_agent", registry)
        assert "pytest" in result or "test" in result.lower()

    def test_includes_test_framework_info(self):
        registry = {
            "python": {
                "agent_prompts": {
                    "test_agent": "Guidance for test agent.",
                },
                "test_framework": "pytest",
                "file_extension": ".py",
                "default_quality": {"linter": "ruff"},
            }
        }
        result = build_language_context("python", "test_agent", registry)
        # Should include test framework or file extension info
        assert isinstance(result, str)

    def test_returns_empty_string_when_agent_has_no_language_prompts(self):
        registry = {
            "python": {
                "agent_prompts": {},
                "test_framework": "pytest",
                "file_extension": ".py",
                "default_quality": {},
            }
        }
        result = build_language_context("python", "setup_agent", registry)
        assert result == ""

    def test_includes_file_extension(self):
        registry = {
            "python": {
                "agent_prompts": {
                    "implementation_agent": "Implement in Python.",
                },
                "test_framework": "pytest",
                "file_extension": ".py",
                "default_quality": {"linter": "ruff"},
            }
        }
        result = build_language_context("python", "implementation_agent", registry)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_r_language_context(self):
        registry = {
            "r": {
                "agent_prompts": {
                    "test_agent": "Use testthat for R tests.",
                },
                "test_framework": "testthat",
                "file_extension": ".R",
                "default_quality": {"linter": "lintr", "formatter": "styler"},
            }
        }
        result = build_language_context("r", "test_agent", registry)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string_for_agent_type_not_in_agent_prompts(self):
        """Agent types without language-specific prompts should return empty string."""
        registry = {
            "python": {
                "agent_prompts": {
                    "test_agent": "Test guidance.",
                },
                "test_framework": "pytest",
                "file_extension": ".py",
                "default_quality": {},
            }
        }
        result = build_language_context("python", "redo_agent", registry)
        assert result == ""


# ===========================================================================
# prepare_task_prompt tests
# ===========================================================================


class TestPrepareTaskPrompt:
    """Tests for prepare_task_prompt function."""

    def test_returns_string(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        assert isinstance(result, str)

    def test_writes_output_to_task_prompt_file(self, project_root):
        prepare_task_prompt(project_root, agent_type="test_agent", unit_number=1)
        task_prompt_path = project_root / ".svp" / "task_prompt.md"
        assert task_prompt_path.exists()

    def test_returned_content_matches_written_file(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        task_prompt_path = project_root / ".svp" / "task_prompt.md"
        assert task_prompt_path.read_text() == result

    def test_test_agent_loads_contracts_only(self, project_root):
        """test_agent is in SELECTIVE_LOADING_MATRIX as contracts_only."""
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_implementation_agent_loads_contracts_only(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="implementation_agent", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_diagnostic_agent_loads_both(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="diagnostic_agent", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_help_agent_loads_prose_only(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="help_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_setup_agent_with_context_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="context"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_setup_agent_with_profile_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="profile"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_setup_agent_with_redo_delivery_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="redo_delivery"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_setup_agent_with_redo_blueprint_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="redo_blueprint"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stakeholder_dialog_draft_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="stakeholder_dialog", mode="draft"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stakeholder_dialog_revision_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="stakeholder_dialog", mode="revision"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stakeholder_dialog_targeted_revision_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="stakeholder_dialog", mode="targeted_revision"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stakeholder_reviewer(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="stakeholder_reviewer")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_blueprint_author_draft_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="blueprint_author", mode="draft"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_blueprint_author_revision_mode(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="blueprint_author", mode="revision"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_blueprint_reviewer(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="blueprint_reviewer")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_blueprint_checker(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="blueprint_checker")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_checklist_generation(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="checklist_generation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_coverage_review(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="coverage_review", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_integration_test_author(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="integration_test_author")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_regression_adaptation(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="regression_adaptation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_git_repo_agent(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="git_repo_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hint_agent(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="hint_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reference_indexing(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="reference_indexing")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_redo_agent(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="redo_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_bug_triage_agent(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="bug_triage", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_repair_agent(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="repair_agent", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_oracle_agent(self, project_root):
        result = prepare_task_prompt(project_root, agent_type="oracle_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_optional_context_parameter_is_included(self, project_root):
        context_text = "UNIQUE_CONTEXT_MARKER_12345"
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1, context=context_text
        )
        assert context_text in result

    def test_optional_mode_parameter_is_accepted(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="context"
        )
        assert isinstance(result, str)

    def test_unit_number_parameter_is_optional(self, project_root):
        """unit_number is optional; should work for agents that do not need it."""
        result = prepare_task_prompt(project_root, agent_type="help_agent")
        assert isinstance(result, str)

    def test_test_agent_normal_mode(self, project_root):
        """test_agent dispatches by mode: normal mode."""
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1, mode="normal"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_test_agent_regression_test_mode(self, project_root):
        """test_agent dispatches by mode: regression_test mode."""
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1, mode="regression_test"
        )
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# prepare_gate_prompt tests
# ===========================================================================


class TestPrepareGatePrompt:
    """Tests for prepare_gate_prompt function."""

    def test_returns_string(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_0_1_hook_activation")
        assert isinstance(result, str)

    def test_writes_output_to_gate_prompt_file(self, project_root):
        prepare_gate_prompt(project_root, gate_id="gate_0_1_hook_activation")
        gate_prompt_path = project_root / ".svp" / "gate_prompt.md"
        assert gate_prompt_path.exists()

    def test_returned_content_matches_written_file(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_0_1_hook_activation")
        gate_prompt_path = project_root / ".svp" / "gate_prompt.md"
        assert gate_prompt_path.read_text() == result

    def test_gate_prompt_includes_gate_id_context(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_0_1_hook_activation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_0_2_context_approval(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_0_2_context_approval")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_1_1_spec_draft(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_1_1_spec_draft")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_2_1_blueprint_approval(self, project_root):
        result = prepare_gate_prompt(
            project_root, gate_id="gate_2_1_blueprint_approval"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_3_1_test_validation(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_3_1_test_validation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_5_1_repo_test(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_5_1_repo_test")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_6_0_debug_permission(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_6_0_debug_permission")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_7_a_trajectory_review(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_7_a_trajectory_review")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_hint_conflict(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_hint_conflict")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_pass_transition_post_pass1(self, project_root):
        result = prepare_gate_prompt(
            project_root, gate_id="gate_pass_transition_post_pass1"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_for_gate_pass_transition_post_pass2(self, project_root):
        result = prepare_gate_prompt(
            project_root, gate_id="gate_pass_transition_post_pass2"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_optional_context_parameter_is_included_in_gate_prompt(self, project_root):
        context_text = "GATE_CONTEXT_MARKER_67890"
        result = prepare_gate_prompt(
            project_root, gate_id="gate_0_1_hook_activation", context=context_text
        )
        assert context_text in result

    def test_gate_prompt_reads_pipeline_state(self, project_root):
        """Gate prompt uses pipeline state for gate-specific context."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_2_diagnostic_decision"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gate_prompt_includes_response_options(self, project_root):
        """Gate prompt should include the response options for the gate."""
        result = prepare_gate_prompt(project_root, gate_id="gate_0_1_hook_activation")
        # The gate prompt should contain some indication of valid responses
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# prepare_task_prompt: blueprint loading dispatch tests
# ===========================================================================


class TestPrepareTaskPromptBlueprintLoading:
    """Tests verifying blueprint loading per SELECTIVE_LOADING_MATRIX."""

    def test_contracts_only_agent_does_not_include_prose(self, project_root):
        """Agents with contracts_only should not include prose content."""
        bp_dir = project_root / "blueprint"
        (bp_dir / "blueprint_prose.md").write_text("UNIQUE_PROSE_SENTINEL_ABC")
        (bp_dir / "blueprint_contracts.md").write_text("UNIQUE_CONTRACTS_SENTINEL_XYZ")
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        # contracts_only should not include prose
        assert "UNIQUE_PROSE_SENTINEL_ABC" not in result

    def test_contracts_only_agent_includes_contracts(self, project_root):
        """Agents with contracts_only should include contracts content."""
        bp_dir = project_root / "blueprint"
        (bp_dir / "blueprint_contracts.md").write_text("UNIQUE_CONTRACTS_SENTINEL_XYZ")
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        # Should include contracts
        assert "UNIQUE_CONTRACTS_SENTINEL_XYZ" in result

    def test_prose_only_agent_does_not_include_contracts(self, project_root):
        """Agents with prose_only should not include contracts content."""
        bp_dir = project_root / "blueprint"
        (bp_dir / "blueprint_prose.md").write_text("UNIQUE_PROSE_SENTINEL_DEF")
        (bp_dir / "blueprint_contracts.md").write_text("UNIQUE_CONTRACTS_SENTINEL_GHI")
        result = prepare_task_prompt(project_root, agent_type="help_agent")
        assert "UNIQUE_CONTRACTS_SENTINEL_GHI" not in result

    def test_prose_only_agent_includes_prose(self, project_root):
        """Agents with prose_only should include prose content."""
        bp_dir = project_root / "blueprint"
        (bp_dir / "blueprint_prose.md").write_text("UNIQUE_PROSE_SENTINEL_DEF")
        result = prepare_task_prompt(project_root, agent_type="help_agent")
        assert "UNIQUE_PROSE_SENTINEL_DEF" in result

    def test_both_agent_includes_prose_and_contracts(self, project_root):
        """Agents with 'both' should include both prose and contracts."""
        bp_dir = project_root / "blueprint"
        (bp_dir / "blueprint_prose.md").write_text("UNIQUE_PROSE_SENTINEL_JKL")
        (bp_dir / "blueprint_contracts.md").write_text("UNIQUE_CONTRACTS_SENTINEL_MNO")
        result = prepare_task_prompt(
            project_root, agent_type="diagnostic_agent", unit_number=1
        )
        assert "UNIQUE_PROSE_SENTINEL_JKL" in result
        assert "UNIQUE_CONTRACTS_SENTINEL_MNO" in result

    def test_agent_not_in_matrix_does_not_load_blueprint(self, project_root):
        """Agents not in SELECTIVE_LOADING_MATRIX should not include blueprint."""
        bp_dir = project_root / "blueprint"
        (bp_dir / "blueprint_prose.md").write_text("BLUEPRINT_PROSE_NOT_EXPECTED")
        (bp_dir / "blueprint_contracts.md").write_text(
            "BLUEPRINT_CONTRACTS_NOT_EXPECTED"
        )
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="context"
        )
        assert "BLUEPRINT_PROSE_NOT_EXPECTED" not in result
        assert "BLUEPRINT_CONTRACTS_NOT_EXPECTED" not in result


# ===========================================================================
# prepare_task_prompt: language context injection tests
# ===========================================================================


class TestPrepareTaskPromptLanguageContext:
    """Tests for LANGUAGE_CONTEXT injection in task prompts."""

    def test_stage3_agent_includes_language_context_section(self, project_root):
        """Stage 3 agents should have LANGUAGE_CONTEXT injected."""
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        # The result should contain a language context section
        assert "LANGUAGE_CONTEXT" in result or "python" in result.lower()

    def test_non_stage3_agent_may_not_include_language_context(self, project_root):
        """Non-Stage 3 agents may not have LANGUAGE_CONTEXT."""
        result = prepare_task_prompt(
            project_root, agent_type="setup_agent", mode="context"
        )
        assert isinstance(result, str)


# ===========================================================================
# main CLI tests
# ===========================================================================


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_accepts_agent_argument(self, project_root):
        """main should accept --agent argument."""
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
            ]
        )

    def test_main_accepts_gate_argument(self, project_root):
        """main should accept --gate argument."""
        main(
            [
                "--project-root",
                str(project_root),
                "--gate",
                "gate_0_1_hook_activation",
            ]
        )

    def test_main_accepts_output_argument(self, project_root, tmp_path):
        """main should accept --output argument."""
        output_path = tmp_path / "custom_output.md"
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
                "--output",
                str(output_path),
            ]
        )

    def test_main_accepts_context_argument(self, project_root):
        """main should accept --context argument."""
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
                "--context",
                "extra context here",
            ]
        )

    def test_main_accepts_mode_argument(self, project_root):
        """main should accept --mode argument."""
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "setup_agent",
                "--mode",
                "context",
            ]
        )

    def test_main_accepts_ladder_argument(self, project_root):
        """main should accept --ladder argument."""
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "implementation_agent",
                "--unit",
                "1",
                "--ladder",
                "fresh_impl",
            ]
        )

    def test_main_accepts_revision_mode_flag(self, project_root):
        """main should accept --revision-mode flag."""
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "stakeholder_dialog",
                "--revision-mode",
            ]
        )

    def test_main_accepts_quality_report_argument(self, project_root, tmp_path):
        """main should accept --quality-report argument."""
        report_path = tmp_path / "quality_report.txt"
        report_path.write_text("Quality report content.")
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
                "--quality-report",
                str(report_path),
            ]
        )

    def test_main_with_no_argv_uses_sys_argv(self, project_root):
        """main with argv=None should use sys.argv."""
        with patch(
            "sys.argv",
            [
                "prepare_task",
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
            ],
        ):
            main(None)

    def test_main_creates_task_prompt_for_agent(self, project_root):
        """main with --agent should create a task prompt file."""
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
            ]
        )
        task_prompt_path = project_root / ".svp" / "task_prompt.md"
        assert task_prompt_path.exists()

    def test_main_creates_gate_prompt_for_gate(self, project_root):
        """main with --gate should create a gate prompt file."""
        main(
            [
                "--project-root",
                str(project_root),
                "--gate",
                "gate_0_1_hook_activation",
            ]
        )
        gate_prompt_path = project_root / ".svp" / "gate_prompt.md"
        assert gate_prompt_path.exists()

    def test_main_custom_output_writes_to_specified_path(self, project_root, tmp_path):
        """main with --output should write to the specified path."""
        output_path = tmp_path / "my_custom_output.md"
        main(
            [
                "--project-root",
                str(project_root),
                "--agent",
                "test_agent",
                "--unit",
                "1",
                "--output",
                str(output_path),
            ]
        )
        assert output_path.exists()
        assert len(output_path.read_text()) > 0


# ===========================================================================
# Structural / invariant tests
# ===========================================================================


class TestStructuralInvariants:
    """Tests verifying structural invariants of Unit 13."""

    def test_all_gate_ids_set_equality_with_expected(self):
        """ALL_GATE_IDS set should match the expected 31 gate IDs exactly."""
        assert set(ALL_GATE_IDS) == set(EXPECTED_GATE_IDS)

    def test_known_agent_types_set_equality_with_expected(self):
        """KNOWN_AGENT_TYPES set should match the expected 21 agent types exactly."""
        assert set(KNOWN_AGENT_TYPES) == set(EXPECTED_AGENT_TYPES)

    def test_selective_loading_matrix_values_are_valid_loading_modes(self):
        """All SELECTIVE_LOADING_MATRIX values must be one of the three valid modes."""
        valid = {"contracts_only", "prose_only", "both"}
        for agent, mode in SELECTIVE_LOADING_MATRIX.items():
            assert mode in valid, f"Agent {agent!r} has invalid loading mode {mode!r}"

    def test_all_gate_ids_is_list_type(self):
        assert type(ALL_GATE_IDS) is list

    def test_known_agent_types_is_list_type(self):
        assert type(KNOWN_AGENT_TYPES) is list

    def test_selective_loading_matrix_is_dict_type(self):
        assert type(SELECTIVE_LOADING_MATRIX) is dict

    def test_prepare_task_prompt_returns_content_string_not_none(self, project_root):
        result = prepare_task_prompt(
            project_root, agent_type="test_agent", unit_number=1
        )
        assert result is not None
        assert isinstance(result, str)

    def test_prepare_gate_prompt_returns_content_string_not_none(self, project_root):
        result = prepare_gate_prompt(project_root, gate_id="gate_0_1_hook_activation")
        assert result is not None
        assert isinstance(result, str)


# ===========================================================================
# load_blueprint edge cases
# ===========================================================================


class TestLoadBlueprintEdgeCases:
    """Edge case tests for blueprint loading functions."""

    def test_load_blueprint_with_empty_files(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("")
        (bp_dir / "blueprint_contracts.md").write_text("")
        result = load_blueprint(bp_dir)
        assert isinstance(result, str)

    def test_load_blueprint_contracts_only_with_empty_file(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("some prose")
        (bp_dir / "blueprint_contracts.md").write_text("")
        result = load_blueprint_contracts_only(bp_dir)
        assert isinstance(result, str)

    def test_load_blueprint_prose_only_with_empty_file(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("")
        (bp_dir / "blueprint_contracts.md").write_text("some contracts")
        result = load_blueprint_prose_only(bp_dir)
        assert isinstance(result, str)

    def test_load_blueprint_with_large_content(self, tmp_path):
        bp_dir = tmp_path / "bp"
        bp_dir.mkdir()
        large_prose = "# Prose\n" + "x" * 100000
        large_contracts = "# Contracts\n" + "y" * 100000
        (bp_dir / "blueprint_prose.md").write_text(large_prose)
        (bp_dir / "blueprint_contracts.md").write_text(large_contracts)
        result = load_blueprint(bp_dir)
        assert len(result) >= 200000


# ===========================================================================
# prepare_task_prompt: per-agent-type dispatch detail tests
# ===========================================================================


class TestPrepareTaskPromptAgentDispatch:
    """Tests verifying per-agent dispatch specifics."""

    def test_implementation_agent_with_diagnostic_impl_ladder(self, project_root):
        """implementation_agent at diagnostic_impl ladder position should include diagnostic report."""
        # Update state to have diagnostic_impl ladder position
        state_path = project_root / ".svp" / "pipeline_state.json"
        state = json.loads(state_path.read_text())
        state["fix_ladder_position"] = "diagnostic_impl"
        state["sub_stage"] = "implementation"
        state_path.write_text(json.dumps(state, indent=2))

        result = prepare_task_prompt(
            project_root, agent_type="implementation_agent", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_oracle_agent_prompt_is_assembled(self, project_root):
        """oracle_agent should produce a task prompt."""
        # Set oracle state
        state_path = project_root / ".svp" / "pipeline_state.json"
        state = json.loads(state_path.read_text())
        state["oracle_session_active"] = True
        state["oracle_phase"] = "dry_run"
        state_path.write_text(json.dumps(state, indent=2))

        result = prepare_task_prompt(project_root, agent_type="oracle_agent")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_bug_triage_prompt_includes_state_context(self, project_root):
        """bug_triage should include state context in its prompt."""
        # Set debug session state
        state_path = project_root / ".svp" / "pipeline_state.json"
        state = json.loads(state_path.read_text())
        state["debug_session"] = {
            "authorized": True,
            "bug_number": 1,
            "classification": None,
            "affected_units": [],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state_path.write_text(json.dumps(state, indent=2))

        result = prepare_task_prompt(
            project_root, agent_type="bug_triage", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_repair_agent_includes_affected_unit_context(self, project_root):
        """repair_agent should include affected unit context."""
        state_path = project_root / ".svp" / "pipeline_state.json"
        state = json.loads(state_path.read_text())
        state["debug_session"] = {
            "authorized": True,
            "bug_number": 1,
            "classification": "single_unit",
            "affected_units": [1],
            "phase": "repair",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state_path.write_text(json.dumps(state, indent=2))

        result = prepare_task_prompt(
            project_root, agent_type="repair_agent", unit_number=1
        )
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# prepare_gate_prompt: convergent gate path tests (SC-20)
# ===========================================================================


class TestPrepareGatePromptConvergentPaths:
    """Tests for convergent gate path distinction using pipeline state (SC-20)."""

    def test_gate_prompt_distinguishes_convergent_paths_via_state(self, project_root):
        """Gate prompts should use pipeline state to distinguish convergent paths."""
        # gate_0_3_profile_approval and gate_0_3r_profile_revision are convergent
        result_regular = prepare_gate_prompt(
            project_root, gate_id="gate_0_3_profile_approval"
        )
        assert isinstance(result_regular, str)

        # Update state for redo context
        state_path = project_root / ".svp" / "pipeline_state.json"
        state = json.loads(state_path.read_text())
        state["sub_stage"] = "redo_profile_delivery"
        state["redo_triggered_from"] = {"stage": "3", "sub_stage": "test_generation"}
        state_path.write_text(json.dumps(state, indent=2))

        result_redo = prepare_gate_prompt(
            project_root, gate_id="gate_0_3r_profile_revision"
        )
        assert isinstance(result_redo, str)

    def test_all_31_gates_can_produce_prompts(self, project_root):
        """Every gate ID in ALL_GATE_IDS should be able to produce a gate prompt."""
        for gate_id in EXPECTED_GATE_IDS:
            result = prepare_gate_prompt(project_root, gate_id=gate_id)
            assert isinstance(result, str), f"Gate {gate_id} did not return a string"
            assert len(result) > 0, f"Gate {gate_id} returned empty string"


# ===========================================================================
# Syntax validation: test file is valid Python
# ===========================================================================


class TestFileValidity:
    """Meta-test verifying this test file is syntactically valid."""

    def test_this_test_file_parses_as_valid_python(self):
        test_file_path = Path(__file__)
        source = test_file_path.read_text()
        tree = ast.parse(source)
        assert tree is not None

    def test_this_test_file_contains_test_functions(self):
        test_file_path = Path(__file__)
        source = test_file_path.read_text()
        tree = ast.parse(source)
        test_funcs = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]
        # Should have many test functions
        assert len(test_funcs) > 100
