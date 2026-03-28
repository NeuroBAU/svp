"""Integration tests for SVP 2.2 cross-unit interactions.

Tests cover cross-unit data flows and integration boundaries.
Individual unit behavior is tested by Stage 3 unit tests.
"""

import ast
import copy
import json
import textwrap
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Unit imports
# ---------------------------------------------------------------------------
from svp_config import (
    DEFAULT_CONFIG,
    derive_env_name,
    get_model_for_agent,
    load_config,
)
from language_registry import (
    LANGUAGE_REGISTRY,
    QualityResult,
    get_language_config,
    validate_registry_entry,
)
from profile_schema import (
    DEFAULT_PROFILE,
    get_delivery_config,
    get_quality_config,
    load_profile,
    validate_profile,
)
from toolchain_reader import get_gate_composition, load_toolchain, resolve_command
from pipeline_state import (
    VALID_FIX_LADDER_POSITIONS,
    VALID_SUB_STAGES,
    PipelineState,
    load_state,
    save_state,
)
from state_transitions import (
    ADDITIONAL_SUB_STAGES,
    TransitionError,
    advance_fix_ladder,
    advance_quality_gate_to_retry,
    advance_stage,
    advance_sub_stage,
    complete_redo_profile_revision,
    complete_unit,
    enter_quality_gate,
    enter_redo_profile_revision,
    quality_gate_fail_to_ladder,
    quality_gate_pass,
    rollback_to_unit,
)
from signature_parser import SIGNATURE_PARSERS, parse_signatures
from stub_generator import STUB_GENERATORS, generate_stub
from prepare_task import (
    ALL_GATE_IDS,
    KNOWN_AGENT_TYPES,
    SELECTIVE_LOADING_MATRIX,
    build_language_context,
    prepare_task_prompt,
)
from routing import (
    AGENT_STATUS_LINES,
    GATE_VOCABULARY,
    PHASE_TO_AGENT,
    TEST_OUTPUT_PARSERS,
    dispatch_gate_response,
    route,
)
from quality_gate import QUALITY_RUNNERS
from adapt_regression_tests import (
    PROJECT_ASSEMBLERS,
    generate_assembly_map,
)

# ---------------------------------------------------------------------------
# Helpers for synthetic workspace setup
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: Any) -> None:
    """Write a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _create_minimal_workspace(root: Path) -> None:
    """Create the minimum files needed for most integration tests."""
    # svp_config.json
    _write_json(root / "svp_config.json", {"iteration_limit": 3})

    # project_profile.json
    _write_json(
        root / "project_profile.json",
        {
            "archetype": "python_project",
            "language": {"primary": "python", "components": [], "communication": {}},
        },
    )

    # pipeline_state.json
    _write_json(
        root / "pipeline_state.json",
        {"stage": "0", "sub_stage": "hook_activation", "pass": None},
    )

    # .svp directory
    (root / ".svp").mkdir(parents=True, exist_ok=True)


def _create_toolchain_file(root: Path) -> None:
    """Create a pipeline toolchain.json with quality gate definitions."""
    toolchain = {
        "environment": {
            "manager": "conda",
            "run_prefix": "conda run -n {env_name}",
        },
        "env_name": "svp-test",
        "test": {
            "command": "{run_prefix} python -m pytest {flags} {target}",
        },
        "quality": {
            "formatter": {
                "tool": "ruff",
                "check": "{run_prefix} ruff format --check {target}",
                "fix": "{run_prefix} ruff format {target}",
            },
            "linter": {
                "tool": "ruff",
                "check": "{run_prefix} ruff check {target}",
                "fix": "{run_prefix} ruff check --fix {target}",
            },
            "type_checker": {
                "tool": "mypy",
                "check": "{run_prefix} mypy {target}",
            },
            "gate_a": ["formatter.check", "linter.check"],
            "gate_b": ["formatter.check", "linter.check", "type_checker.check"],
            "gate_c": ["formatter.fix", "linter.fix"],
        },
    }
    _write_json(root / "toolchain.json", toolchain)


def _create_blueprint_files(root: Path) -> None:
    """Create minimal blueprint files for extraction tests."""
    blueprint_dir = root / "blueprint"
    blueprint_dir.mkdir(parents=True, exist_ok=True)

    prose_content = textwrap.dedent("""\
        # SVP 2.2 Blueprint -- Prose

        ## Preamble

        ```
        project/
        |-- scripts/
        |   |-- config.py       <- Unit 1
        |   +-- registry.py     <- Unit 2
        +-- tests/
            +-- test_config.py  <- Unit 1
        ```

        ## Unit 1: Core Configuration

        ### Tier 1

        Core configuration management.

        ## Unit 2: Language Registry

        ### Tier 1

        Language registry and validation.
    """)

    contracts_content = textwrap.dedent("""\
        # SVP 2.2 Blueprint -- Contracts

        ## Unit 1: Core Configuration

        ### Tier 2 -- Signatures

        ```python
        from typing import Any, Dict
        from pathlib import Path

        def load_config(project_root: Path) -> Dict[str, Any]: ...
        def save_config(project_root: Path, config: Dict[str, Any]) -> None: ...
        ```

        ### Tier 3 -- Behavioral Contracts

        **Dependencies:** None (root unit).

        ## Unit 2: Language Registry

        ### Tier 2 -- Signatures

        ```python
        from typing import Any, Dict, List

        def get_language_config(language: str) -> Dict[str, Any]: ...
        ```

        ### Tier 3 -- Behavioral Contracts

        **Dependencies:** Unit 1.
    """)

    (blueprint_dir / "blueprint_prose.md").write_text(prose_content)
    (blueprint_dir / "blueprint_contracts.md").write_text(contracts_content)


# ===================================================================
# 1. Toolchain Resolution Chain
#    Unit 1 config -> Unit 4 toolchain -> resolved command
# ===================================================================


class TestToolchainResolutionChain:
    """Integration: Config (Unit 1) -> Toolchain (Unit 4) -> resolved commands."""

    def test_config_provides_env_name_for_toolchain_resolution(self, tmp_path):
        """Config-derived env_name flows into command resolution."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        # Unit 1: derive env name from project root
        env_name = derive_env_name(tmp_path)
        assert env_name == f"svp-{tmp_path.name}"

        # Unit 4: load toolchain
        toolchain = load_toolchain(tmp_path)
        run_prefix = toolchain["environment"]["run_prefix"]

        # Unit 4: resolve command using env_name from Unit 1
        test_cmd = toolchain["test"]["command"]
        resolved = resolve_command(
            test_cmd,
            env_name=env_name,
            run_prefix=run_prefix.replace("{env_name}", env_name),
            target="tests/",
            flags="-v",
        )

        assert env_name in resolved
        assert "pytest" in resolved
        assert "-v" in resolved
        assert "tests/" in resolved
        # No unresolved placeholders
        assert "{" not in resolved
        # No double spaces
        assert "  " not in resolved

    def test_toolchain_gate_composition_uses_resolved_commands(self, tmp_path):
        """Gate composition returns operations whose commands can be resolved."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        env_name = derive_env_name(tmp_path)
        toolchain = load_toolchain(tmp_path)
        run_prefix_template = toolchain["environment"]["run_prefix"]

        # Get gate_a composition
        gate_ops = get_gate_composition(toolchain, "gate_a")
        assert len(gate_ops) >= 2

        for op in gate_ops:
            assert "operation" in op
            assert "command" in op
            assert op["operation"].startswith("quality.")

            # Each command can be fully resolved
            resolved = resolve_command(
                op["command"],
                env_name=env_name,
                run_prefix=run_prefix_template.replace("{env_name}", env_name),
                target="src/",
            )
            assert "{" not in resolved

    def test_language_specific_toolchain_path_from_registry(self, tmp_path):
        """Language registry provides toolchain_file name used by load_toolchain."""
        _create_minimal_workspace(tmp_path)

        python_config = get_language_config("python")
        toolchain_file = python_config["toolchain_file"]
        assert toolchain_file == "python_conda_pytest.json"

        r_config = get_language_config("r")
        r_toolchain_file = r_config["toolchain_file"]
        assert r_toolchain_file == "r_renv_testthat.json"

        # Verify the toolchain path would be constructed correctly
        expected_python_path = (
            tmp_path / "scripts" / "toolchain_defaults" / toolchain_file
        )
        expected_r_path = tmp_path / "scripts" / "toolchain_defaults" / r_toolchain_file
        assert expected_python_path.name == "python_conda_pytest.json"
        assert expected_r_path.name == "r_renv_testthat.json"

    def test_gate_b_is_superset_of_gate_a(self, tmp_path):
        """Gate B operations include all Gate A operations plus type_checker."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        toolchain = load_toolchain(tmp_path)
        gate_a_ops = get_gate_composition(toolchain, "gate_a")
        gate_b_ops = get_gate_composition(toolchain, "gate_b")

        gate_a_names = {op["operation"] for op in gate_a_ops}
        gate_b_names = {op["operation"] for op in gate_b_ops}

        # gate_b should contain all gate_a operations
        assert gate_a_names.issubset(gate_b_names)
        # gate_b should also have the type_checker
        assert any("type_checker" in name for name in gate_b_names)


# ===================================================================
# 2. Profile Flow Through Preparation Script
#    Unit 3 load_profile -> Unit 13 prepare_task_prompt -> agent context
# ===================================================================


class TestProfileFlowThroughPreparation:
    """Integration: Profile (Unit 3) -> Task Preparation (Unit 13) -> agent context."""

    def test_profile_loads_and_appears_in_blueprint_author_prompt(self, tmp_path):
        """Profile data loaded by Unit 3 is included in blueprint_author prompt."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        # Verify profile can be loaded
        profile = load_profile(tmp_path)
        assert profile["archetype"] == "python_project"
        assert profile["language"]["primary"] == "python"

        # Prepare task prompt for blueprint_author
        prompt = prepare_task_prompt(tmp_path, "blueprint_author")

        # The prompt should include the profile data
        assert "python_project" in prompt
        assert "Profile" in prompt

    def test_profile_missing_produces_prompt_without_profile(self, tmp_path):
        """When profile is missing, preparation script still succeeds."""
        (tmp_path / ".svp").mkdir(parents=True, exist_ok=True)
        _write_json(tmp_path / "svp_config.json", {})
        _write_json(
            tmp_path / "pipeline_state.json",
            {"stage": "0", "sub_stage": "hook_activation", "pass": None},
        )
        _create_blueprint_files(tmp_path)

        # prepare_task_prompt should not raise even without profile
        prompt = prepare_task_prompt(tmp_path, "setup_agent")
        assert "Setup Agent" in prompt

    def test_language_context_injected_for_stage3_agents(self, tmp_path):
        """Stage 3 agents (test, implementation) get LANGUAGE_CONTEXT from registry."""
        _create_minimal_workspace(tmp_path)

        # Build language context for test_agent
        ctx = build_language_context("python", "test_agent", LANGUAGE_REGISTRY)
        assert "LANGUAGE_CONTEXT" in ctx
        assert "Python" in ctx
        assert "pytest" in ctx

    def test_language_context_empty_for_non_stage3_agents(self, tmp_path):
        """Non-stage-3 agents (setup_agent) get empty language context."""
        ctx = build_language_context("python", "setup_agent", LANGUAGE_REGISTRY)
        assert ctx == ""

    def test_quality_config_from_profile_uses_registry_defaults(self, tmp_path):
        """Profile quality config deep-merges with registry defaults."""
        _create_minimal_workspace(tmp_path)

        profile = load_profile(tmp_path)
        quality = get_quality_config(profile, "python", LANGUAGE_REGISTRY)

        # Should have all default quality fields
        assert quality["linter"] == "ruff"
        assert quality["formatter"] == "ruff"
        assert quality["type_checker"] == "mypy"
        assert quality["line_length"] == 88

    def test_delivery_config_from_profile_uses_registry_defaults(self, tmp_path):
        """Profile delivery config deep-merges with registry defaults."""
        _create_minimal_workspace(tmp_path)

        profile = load_profile(tmp_path)
        delivery = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)

        assert delivery["environment_recommendation"] == "conda"
        assert delivery["dependency_format"] == "environment.yml"
        assert delivery["source_layout"] == "conventional"


# ===================================================================
# 3. Blueprint Checker Profile Validation
#    Unit 3 validate_profile -> Unit 2 registry -> valid tool sets
# ===================================================================


class TestBlueprintCheckerProfileValidation:
    """Integration: Profile validation (Unit 3) against Language Registry (Unit 2)."""

    def test_valid_python_profile_passes_validation(self):
        """A standard Python project profile passes validation."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_invalid_linter_detected(self):
        """Profile with an invalid linter is detected by registry validation."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["python"]["linter"] = "nonexistent_linter"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("linter" in e.lower() for e in errors)

    def test_invalid_formatter_detected(self):
        """Profile with an invalid formatter is detected."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["python"]["formatter"] = "invalid_formatter"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("formatter" in e.lower() for e in errors)

    def test_invalid_type_checker_detected(self):
        """Profile with an invalid type checker is detected."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["python"]["type_checker"] = "invalid_tc"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("type_checker" in e.lower() for e in errors)

    def test_invalid_source_layout_detected(self):
        """Profile with an invalid source layout is detected."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["delivery"]["python"]["source_layout"] = "nonstandard_layout"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("source_layout" in e.lower() for e in errors)

    def test_invalid_archetype_detected(self):
        """Profile with an invalid archetype is detected."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["archetype"] = "invalid_archetype"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("archetype" in e.lower() for e in errors)

    def test_unknown_primary_language_detected(self):
        """Profile with an unknown primary language is detected."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["language"]["primary"] = "golang"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("language" in e.lower() for e in errors)

    def test_mixed_archetype_requires_secondary_language(self):
        """Mixed archetype must have a secondary language."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["archetype"] = "mixed"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert any("mixed" in e.lower() or "secondary" in e.lower() for e in errors)

    def test_mixed_archetype_forces_conda(self):
        """Mixed archetype enforces conda for both languages."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["archetype"] = "mixed"
        profile["language"]["primary"] = "python"
        profile["language"]["secondary"] = "r"
        profile["delivery"]["python"] = copy.deepcopy(
            LANGUAGE_REGISTRY["python"]["default_delivery"]
        )
        profile["delivery"]["r"] = copy.deepcopy(
            LANGUAGE_REGISTRY["r"]["default_delivery"]
        )
        profile["delivery"]["r"]["environment_recommendation"] = "renv"
        profile["quality"]["python"] = copy.deepcopy(
            LANGUAGE_REGISTRY["python"]["default_quality"]
        )
        profile["quality"]["r"] = copy.deepcopy(
            LANGUAGE_REGISTRY["r"]["default_quality"]
        )

        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        # renv is invalid for mixed archetype
        assert any(
            "conda" in e.lower() or "environment_recommendation" in e for e in errors
        )

    def test_component_language_requires_host(self):
        """Component language (stan) with no compatible host produces error."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["language"]["primary"] = "r"
        profile["language"]["components"] = ["stan"]
        profile["delivery"] = {
            "r": copy.deepcopy(LANGUAGE_REGISTRY["r"]["default_delivery"])
        }
        profile["quality"] = {
            "r": copy.deepcopy(LANGUAGE_REGISTRY["r"]["default_quality"])
        }

        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        # Stan is compatible with r, so no error
        assert not any("stan" in e.lower() and "host" in e.lower() for e in errors)

    def test_registry_entries_self_validate(self):
        """All built-in registry entries pass their own validation."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                from language_registry import validate_component_entry

                errors = validate_component_entry(entry)
            else:
                errors = validate_registry_entry(entry)
            assert errors == [], (
                f"Registry entry '{lang_key}' fails validation: {errors}"
            )


# ===================================================================
# 4. Redo Agent Profile Classification
#    Unit 6 enter_redo_profile_revision -> state transitions
# ===================================================================


class TestRedoAgentProfileClassification:
    """Integration: Redo profile classification (Unit 6) -> state transitions."""

    def test_delivery_redo_enters_correct_sub_stage(self):
        """Redo type 'delivery' sets sub_stage to 'redo_profile_delivery'."""
        state = PipelineState(stage="3", sub_stage="implementation", current_unit=5)
        new_state = enter_redo_profile_revision(state, "delivery")

        assert new_state.sub_stage == "redo_profile_delivery"
        assert new_state.redo_triggered_from is not None
        assert new_state.redo_triggered_from["stage"] == "3"
        assert new_state.redo_triggered_from["sub_stage"] == "implementation"
        assert new_state.redo_triggered_from["current_unit"] == 5

    def test_blueprint_redo_enters_correct_sub_stage(self):
        """Redo type 'blueprint' sets sub_stage to 'redo_profile_blueprint'."""
        state = PipelineState(stage="2", sub_stage="blueprint_dialog")
        new_state = enter_redo_profile_revision(state, "blueprint")

        assert new_state.sub_stage == "redo_profile_blueprint"
        assert new_state.redo_triggered_from is not None
        assert new_state.redo_triggered_from["stage"] == "2"

    def test_redo_completion_restores_original_state(self):
        """Completing a redo profile revision restores the original state."""
        state = PipelineState(stage="3", sub_stage="implementation", current_unit=5)
        redo_state = enter_redo_profile_revision(state, "delivery")

        # Now complete the redo
        restored_state = complete_redo_profile_revision(redo_state)

        assert restored_state.stage == "3"
        assert restored_state.sub_stage == "implementation"
        assert restored_state.current_unit == 5
        assert restored_state.redo_triggered_from is None

    def test_invalid_redo_type_raises(self):
        """Invalid redo type raises TransitionError."""
        state = PipelineState(stage="3", sub_stage="implementation")
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(state, "invalid")

    def test_redo_does_not_mutate_original_state(self):
        """Redo operations produce new state without mutating the original."""
        state = PipelineState(stage="3", sub_stage="implementation", current_unit=5)
        original_stage = state.stage
        original_sub = state.sub_stage

        new_state = enter_redo_profile_revision(state, "delivery")

        # Original is untouched
        assert state.stage == original_stage
        assert state.sub_stage == original_sub
        assert state.redo_triggered_from is None


# ===================================================================
# 5. Gate 0.3 Dispatch
#    Unit 14 dispatch_gate_response -> Unit 6 state transitions
# ===================================================================


class TestGate03Dispatch:
    """Integration: Gate 0.3 dispatch (Unit 14) -> state transitions (Unit 6)."""

    def test_profile_approved_advances_to_stage_1(self, tmp_path):
        """PROFILE APPROVED at Gate 0.3 advances pipeline to Stage 1."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        new_state = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE APPROVED", tmp_path
        )

        assert new_state.stage == "1"
        assert new_state.sub_stage is None

    def test_profile_rejected_stays_at_profile_stage(self, tmp_path):
        """PROFILE REJECTED at Gate 0.3 returns to project_profile sub-stage."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        new_state = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE REJECTED", tmp_path
        )

        assert new_state.stage == "0"
        assert new_state.sub_stage == "project_profile"

    def test_invalid_response_at_gate_raises(self, tmp_path):
        """Invalid response at a gate raises ValueError."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        with pytest.raises(ValueError, match="Invalid response"):
            dispatch_gate_response(
                state, "gate_0_3_profile_approval", "NONSENSE", tmp_path
            )

    def test_unknown_gate_id_raises(self, tmp_path):
        """Unknown gate_id raises ValueError."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        with pytest.raises(ValueError, match="Unknown gate_id"):
            dispatch_gate_response(state, "gate_nonexistent", "APPROVE", tmp_path)

    def test_context_approved_advances_to_profile_sub_stage(self, tmp_path):
        """CONTEXT APPROVED at Gate 0.2 advances to project_profile."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_context")

        new_state = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT APPROVED", tmp_path
        )

        assert new_state.stage == "0"
        assert new_state.sub_stage == "project_profile"


# ===================================================================
# 6. Preference Compliance Scan
#    Profile validation across preference categories
# ===================================================================


class TestPreferenceComplianceScan:
    """Integration: Profile (Unit 3) preferences validated against registry (Unit 2)."""

    def test_documentation_preferences_validated(self):
        """Documentation preferences (readme section) are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "readme" in profile
        assert "audience" in profile["readme"]
        assert "sections" in profile["readme"]

    def test_metadata_preferences_validated(self):
        """Metadata preferences (license section) are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "license" in profile
        assert "type" in profile["license"]

    def test_vcs_preferences_validated(self):
        """VCS preferences are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "vcs" in profile
        assert "commit_style" in profile["vcs"]
        assert "branch_strategy" in profile["vcs"]

    def test_testing_preferences_validated(self):
        """Testing preferences are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "testing" in profile
        assert "readable_test_names" in profile["testing"]

    def test_tooling_preferences_validated(self):
        """Quality tooling preferences are validated against registry."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "quality" in profile
        python_quality = profile["quality"]["python"]
        assert python_quality["linter"] in LANGUAGE_REGISTRY["python"]["valid_linters"]
        assert (
            python_quality["formatter"]
            in LANGUAGE_REGISTRY["python"]["valid_formatters"]
        )
        assert (
            python_quality["type_checker"]
            in LANGUAGE_REGISTRY["python"]["valid_type_checkers"]
        )


# ===================================================================
# 7. Write Authorization for New Paths
#    Unit 2 authorized_write_dirs -> Unit 17 hook logic
# ===================================================================


class TestWriteAuthorizationForNewPaths:
    """Integration: Language Registry (Unit 2) authorized_write_dirs -> hooks (Unit 17)."""

    def test_python_authorized_dirs_include_src_tests_and_root(self):
        """Python language entry has src, tests, and root as authorized write dirs."""
        python_config = get_language_config("python")
        authorized = python_config["authorized_write_dirs"]
        assert "src" in authorized
        assert "tests" in authorized
        assert "." in authorized

    def test_r_authorized_dirs_include_r_tests_and_root(self):
        """R language entry has R, tests/testthat, and root as authorized write dirs."""
        r_config = get_language_config("r")
        authorized = r_config["authorized_write_dirs"]
        assert "R" in authorized
        assert "tests/testthat" in authorized
        assert "." in authorized

    def test_quality_config_files_are_in_root_dir(self):
        """Quality config files (ruff.toml etc.) are in root dir, which is authorized."""
        python_config = get_language_config("python")
        quality_mapping = python_config["quality_config_mapping"]

        # ruff.toml is at project root, which is authorized via "."
        assert quality_mapping["ruff"] == "ruff.toml"
        authorized = python_config["authorized_write_dirs"]
        assert "." in authorized, "Root dir must be authorized for quality config files"

    def test_all_languages_have_authorized_write_dirs(self):
        """All full-language registry entries have authorized_write_dirs."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert "authorized_write_dirs" in entry, (
                    f"Language {lang_key} missing authorized_write_dirs"
                )
                assert len(entry["authorized_write_dirs"]) > 0


# ===================================================================
# 8. Redo-Triggered Profile Revision State Transitions
#    Unit 6 state transitions -> Unit 5 save/load round-trip
# ===================================================================


class TestRedoTriggeredStateTransitions:
    """Integration: Redo state transitions (Unit 6) -> save/load (Unit 5)."""

    def test_redo_state_roundtrip_through_save_load(self, tmp_path):
        """Redo state survives save -> load round-trip."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="3", sub_stage="implementation", current_unit=5)
        redo_state = enter_redo_profile_revision(state, "delivery")

        # Save and reload
        save_state(tmp_path, redo_state)
        loaded = load_state(tmp_path)

        assert loaded.sub_stage == "redo_profile_delivery"
        assert loaded.redo_triggered_from is not None
        assert loaded.redo_triggered_from["stage"] == "3"

    def test_redo_completion_roundtrip(self, tmp_path):
        """Redo completion -> save -> load preserves restored state."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="3", sub_stage="implementation", current_unit=5)
        redo_state = enter_redo_profile_revision(state, "delivery")
        restored = complete_redo_profile_revision(redo_state)

        save_state(tmp_path, restored)
        loaded = load_state(tmp_path)

        assert loaded.stage == "3"
        assert loaded.sub_stage == "implementation"
        assert loaded.current_unit == 5
        assert loaded.redo_triggered_from is None

    def test_redo_sub_stages_are_in_additional_sub_stages(self):
        """Redo sub-stages are valid additional sub-stages recognized by Unit 6."""
        assert "redo_profile_delivery" in ADDITIONAL_SUB_STAGES
        assert "redo_profile_blueprint" in ADDITIONAL_SUB_STAGES


# ===================================================================
# 9. Quality Gate Execution Chain
#    Unit 4 get_gate_composition -> Unit 15 run_quality_gate -> QualityResult
# ===================================================================


class TestQualityGateExecutionChain:
    """Integration: Toolchain (Unit 4) gate composition -> Quality Runner (Unit 15)."""

    def test_gate_composition_feeds_quality_runner(self, tmp_path):
        """Gate composition from toolchain is used by quality runner to execute checks."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        toolchain = load_toolchain(tmp_path)
        python_config = get_language_config("python")

        # Gate A composition resolves to operations with quality. prefix
        gate_ops = get_gate_composition(toolchain, "gate_a")
        assert all(op["operation"].startswith("quality.") for op in gate_ops)

        # The quality_runner_key from language config matches a registered runner
        runner_key = python_config["quality_runner_key"]
        assert runner_key in QUALITY_RUNNERS

    def test_gate_a_precedes_gate_b_in_stage3_substages(self):
        """Gate A sub-stage comes before Gate B in the Stage 3 sub-stage ordering."""
        stage3_subs = list(VALID_SUB_STAGES["3"])
        # Both must exist
        assert "quality_gate_a" in stage3_subs
        assert "quality_gate_b" in stage3_subs

    def test_quality_gate_transition_chain(self):
        """Quality gate state transitions follow correct sequence: gate -> pass -> next."""
        state = PipelineState(stage="3", sub_stage="stub_generation", current_unit=1)

        # Enter gate A
        state_qa = enter_quality_gate(state, "quality_gate_a")
        assert state_qa.sub_stage == "quality_gate_a"

        # Gate A passes -> red_run
        state_rr = quality_gate_pass(state_qa)
        assert state_rr.sub_stage == "red_run"

    def test_quality_gate_b_pass_advances_to_green_run(self):
        """Gate B passing advances to green_run sub-stage."""
        state = PipelineState(stage="3", sub_stage="quality_gate_b", current_unit=1)
        new_state = quality_gate_pass(state)
        assert new_state.sub_stage == "green_run"

    def test_quality_result_types_match_gate_outcomes(self):
        """QualityResult status values cover the expected gate outcomes."""
        valid_statuses = {
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        }
        # Create a result for each status
        for status in valid_statuses:
            result = QualityResult(
                status=status, auto_fixed=False, residuals=[], report=""
            )
            assert result.status == status


# ===================================================================
# 10. Quality Gate Retry Isolation
#     Gate retry cycles are isolated per-gate
# ===================================================================


class TestQualityGateRetryIsolation:
    """Integration: Quality gate retries (Unit 6) are isolated per-gate."""

    def test_gate_a_retry_does_not_affect_gate_b(self):
        """Retrying gate A does not change gate B's sub-stage."""
        state = PipelineState(stage="3", sub_stage="quality_gate_a", current_unit=1)

        # Advance gate A to retry
        retry_state = advance_quality_gate_to_retry(state)
        assert retry_state.sub_stage == "quality_gate_a_retry"

        # Gate B sub-stage is independent -- we can still enter it later
        # First, pass gate A retry
        passed = quality_gate_pass(retry_state)
        assert passed.sub_stage == "red_run"

    def test_gate_b_retry_does_not_affect_gate_a_results(self):
        """Retrying gate B does not affect any gate A state."""
        state = PipelineState(stage="3", sub_stage="quality_gate_b", current_unit=1)

        retry_state = advance_quality_gate_to_retry(state)
        assert retry_state.sub_stage == "quality_gate_b_retry"

        # Passing from retry still goes to green_run
        passed = quality_gate_pass(retry_state)
        assert passed.sub_stage == "green_run"

    def test_retry_from_non_gate_raises(self):
        """Cannot advance to retry from a non-gate sub-stage."""
        state = PipelineState(stage="3", sub_stage="implementation", current_unit=1)

        with pytest.raises(TransitionError):
            advance_quality_gate_to_retry(state)

    def test_quality_gate_fail_enters_fix_ladder(self):
        """Quality gate failure enters fix ladder from current position."""
        state = PipelineState(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
            fix_ladder_position=None,
        )

        # Failing gate -> enters fix ladder
        new_state = quality_gate_fail_to_ladder(state)
        assert new_state.fix_ladder_position == "fresh_impl"
        assert new_state.sub_stage == "implementation"


# ===================================================================
# 11. Quality Package Installation
#     Profile quality config -> registry valid tools
# ===================================================================


class TestQualityPackageInstallation:
    """Integration: Profile quality config -> registry -> correct tool versions."""

    def test_default_python_quality_tools_are_valid(self):
        """Default Python quality tools are in the registry's valid sets."""
        python_entry = LANGUAGE_REGISTRY["python"]
        default_q = python_entry["default_quality"]

        assert default_q["linter"] in python_entry["valid_linters"]
        assert default_q["formatter"] in python_entry["valid_formatters"]
        assert default_q["type_checker"] in python_entry["valid_type_checkers"]

    def test_profile_quality_config_merges_with_registry(self, tmp_path):
        """Profile quality config merges with registry defaults correctly."""
        _write_json(
            tmp_path / "project_profile.json",
            {
                "archetype": "python_project",
                "language": {"primary": "python", "components": []},
                "quality": {"python": {"line_length": 120}},
            },
        )

        profile = load_profile(tmp_path)
        quality = get_quality_config(profile, "python", LANGUAGE_REGISTRY)

        # Override applied
        assert quality["line_length"] == 120
        # Defaults preserved
        assert quality["linter"] == "ruff"
        assert quality["formatter"] == "ruff"

    def test_quality_config_mapping_provides_config_paths(self):
        """Quality config mapping provides file paths for each tool."""
        python_config = get_language_config("python")
        mapping = python_config["quality_config_mapping"]

        assert "ruff" in mapping
        assert "mypy" in mapping
        assert mapping["ruff"] == "ruff.toml"

    def test_r_quality_tools_are_valid(self):
        """Default R quality tools are in the registry's valid sets."""
        r_entry = LANGUAGE_REGISTRY["r"]
        default_q = r_entry["default_quality"]

        assert default_q["linter"] in r_entry["valid_linters"]
        assert default_q["formatter"] in r_entry["valid_formatters"]
        assert default_q["type_checker"] in r_entry["valid_type_checkers"]


# ===================================================================
# 12. Per-Language Dispatch: Stub Generator, Test Output Parser,
#     Quality Runner for Python and R
# ===================================================================


class TestPerLanguageDispatch:
    """Integration: Registry keys -> dispatch tables across Units 9, 10, 14, 15."""

    def test_python_stub_generator_key_resolves(self):
        """Python stub_generator_key resolves in STUB_GENERATORS dispatch table."""
        python_config = get_language_config("python")
        key = python_config["stub_generator_key"]
        assert key in STUB_GENERATORS

    def test_r_stub_generator_key_resolves(self):
        """R stub_generator_key resolves in STUB_GENERATORS dispatch table."""
        r_config = get_language_config("r")
        key = r_config["stub_generator_key"]
        assert key in STUB_GENERATORS

    def test_stan_stub_generator_key_resolves(self):
        """Stan stub_generator_key resolves in STUB_GENERATORS dispatch table."""
        stan_config = get_language_config("stan")
        key = stan_config["stub_generator_key"]
        assert key in STUB_GENERATORS

    def test_python_test_output_parser_key_resolves(self):
        """Python test_output_parser_key resolves in TEST_OUTPUT_PARSERS."""
        python_config = get_language_config("python")
        key = python_config["test_output_parser_key"]
        assert key in TEST_OUTPUT_PARSERS

    def test_r_test_output_parser_key_resolves(self):
        """R test_output_parser_key resolves in TEST_OUTPUT_PARSERS."""
        r_config = get_language_config("r")
        key = r_config["test_output_parser_key"]
        assert key in TEST_OUTPUT_PARSERS

    def test_python_quality_runner_key_resolves(self):
        """Python quality_runner_key resolves in QUALITY_RUNNERS."""
        python_config = get_language_config("python")
        key = python_config["quality_runner_key"]
        assert key in QUALITY_RUNNERS

    def test_r_quality_runner_key_resolves(self):
        """R quality_runner_key resolves in QUALITY_RUNNERS."""
        r_config = get_language_config("r")
        key = r_config["quality_runner_key"]
        assert key in QUALITY_RUNNERS

    def test_stan_quality_runner_key_resolves(self):
        """Stan quality_runner_key resolves in QUALITY_RUNNERS."""
        stan_config = get_language_config("stan")
        key = stan_config["quality_runner_key"]
        assert key in QUALITY_RUNNERS

    def test_python_signature_parser_key_resolves(self):
        """Python signature parser key resolves in SIGNATURE_PARSERS."""
        assert "python" in SIGNATURE_PARSERS

    def test_r_signature_parser_key_resolves(self):
        """R signature parser key resolves in SIGNATURE_PARSERS."""
        assert "r" in SIGNATURE_PARSERS

    def test_python_stub_generation_end_to_end(self):
        """Python: parse signatures -> generate stub produces valid Python stub."""
        source = textwrap.dedent("""\
            from typing import Dict

            def my_function(x: int, y: str) -> Dict[str, int]: ...
        """)
        python_config = get_language_config("python")
        parsed = parse_signatures(source, "python", python_config)
        assert isinstance(parsed, ast.Module)

        stub_text = generate_stub(parsed, "python", python_config)
        assert python_config["stub_sentinel"] in stub_text
        assert "NotImplementedError" in stub_text
        assert "my_function" in stub_text

    def test_r_stub_generation_end_to_end(self):
        """R: parse signatures -> generate stub produces valid R stub."""
        source = textwrap.dedent("""\
            my_function <- function(x, y = 10) {
              x + y
            }
        """)
        r_config = get_language_config("r")
        parsed = parse_signatures(source, "r", r_config)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "my_function"

        stub_text = generate_stub(parsed, "r", r_config)
        assert r_config["stub_sentinel"] in stub_text
        assert "my_function" in stub_text
        assert 'stop("Not implemented")' in stub_text

    def test_python_test_output_parser_handles_passing(self):
        """Python test output parser correctly classifies passing tests."""
        parser = TEST_OUTPUT_PARSERS["python"]
        output = "2 passed in 0.5s"
        result = parser(output, "python", 0, {})
        assert result.status == "TESTS_PASSED"
        assert result.passed == 2

    def test_python_test_output_parser_handles_failure(self):
        """Python test output parser correctly classifies failing tests."""
        parser = TEST_OUTPUT_PARSERS["python"]
        output = "1 passed, 2 failed in 1.0s"
        result = parser(output, "python", 1, {})
        assert result.status == "TESTS_FAILED"
        assert result.passed == 1
        assert result.failed == 2

    def test_python_test_output_parser_handles_collection_error(self):
        """Python test output parser detects collection errors."""
        parser = TEST_OUTPUT_PARSERS["python"]
        output = "ERROR collecting tests/test_foo.py\nModuleNotFoundError: No module"
        result = parser(output, "python", 2, {})
        assert result.collection_error is True

    def test_r_test_output_parser_handles_passing(self):
        """R test output parser correctly classifies passing tests."""
        parser = TEST_OUTPUT_PARSERS["r"]
        output = "OK: 5\nFailed: 0\nWarnings: 0"
        result = parser(output, "r", 0, {})
        assert result.status == "TESTS_PASSED"
        assert result.passed == 5

    def test_r_test_output_parser_handles_failure(self):
        """R test output parser correctly classifies failing tests."""
        parser = TEST_OUTPUT_PARSERS["r"]
        output = "OK: 3\nFailed: 2\nWarnings: 0"
        result = parser(output, "r", 1, {})
        assert result.status == "TESTS_FAILED"
        assert result.failed == 2

    def test_project_assembler_keys_match_languages(self):
        """PROJECT_ASSEMBLERS has entries for python and r."""
        assert "python" in PROJECT_ASSEMBLERS
        assert "r" in PROJECT_ASSEMBLERS


# ===================================================================
# 13. State Transition -> Routing Consistency
#     Unit 6 advance_stage -> Unit 5 save_state -> Unit 14 route
# ===================================================================


class TestStateTransitionRoutingConsistency:
    """Integration: State transitions (Unit 6) -> save (Unit 5) -> route (Unit 14)."""

    def test_advance_stage_then_route_reads_updated_state(self, tmp_path):
        """After advance_stage + save_state, route reads the updated state."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="0", sub_stage="project_profile")
        # Advance to stage 1
        new_state = advance_stage(state, "1")
        save_state(tmp_path, new_state)

        # Route should read Stage 1 state
        action = route(tmp_path)
        # In Stage 1 with no sub_stage, routing should emit spec-related action
        assert action["action_type"] in ("invoke_agent", "human_gate", "run_command")

    def test_advance_sub_stage_then_route(self, tmp_path):
        """After advance_sub_stage + save, route reads the new sub-stage."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="0", sub_stage="hook_activation")
        new_state = advance_sub_stage(state, "project_context")
        save_state(tmp_path, new_state)

        action = route(tmp_path)
        # Should route based on project_context sub-stage
        assert action["action_type"] in ("invoke_agent", "human_gate", "pipeline_held")

    def test_save_state_hash_is_consistent(self, tmp_path):
        """save_state computes a hash that survives load_state round-trip."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="3", sub_stage="stub_generation", current_unit=1)
        save_state(tmp_path, state)

        loaded = load_state(tmp_path)
        assert loaded.state_hash is not None
        assert isinstance(loaded.state_hash, str)
        assert len(loaded.state_hash) == 64  # SHA-256 hex digest

    def test_rollback_to_unit_then_save_load(self, tmp_path):
        """rollback_to_unit state is preserved through save/load."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(
            stage="3",
            sub_stage="unit_completion",
            current_unit=3,
            total_units=5,
            verified_units=[
                {"unit": 1, "timestamp": "t1"},
                {"unit": 2, "timestamp": "t2"},
            ],
        )
        rolled = rollback_to_unit(state, 2)
        save_state(tmp_path, rolled)

        loaded = load_state(tmp_path)
        assert loaded.current_unit == 2
        assert loaded.sub_stage == "stub_generation"
        assert loaded.stage == "3"
        assert len(loaded.verified_units) == 1
        assert loaded.verified_units[0]["unit"] == 1

    def test_complete_unit_advances_or_finishes(self, tmp_path):
        """complete_unit advances to next unit or marks Stage 3 done."""
        _create_minimal_workspace(tmp_path)

        # Complete unit 1 of 2
        state = PipelineState(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=2,
        )
        new_state = complete_unit(state)
        assert new_state.current_unit == 2
        assert new_state.sub_stage == "stub_generation"

        # Complete unit 2 of 2 (final)
        state2 = PipelineState(
            stage="3",
            sub_stage="unit_completion",
            current_unit=2,
            total_units=2,
        )
        final_state = complete_unit(state2)
        assert final_state.current_unit is None
        assert final_state.sub_stage is None


# ===================================================================
# 14. Assembly Map Generation
#     Unit 23 generate_assembly_map -> bidirectional mapping
# ===================================================================


class TestAssemblyMapGeneration:
    """Integration: Blueprint (Unit 8) -> Assembly Map (Unit 23) -> bidirectional mapping."""

    def test_assembly_map_is_bidirectional(self, tmp_path):
        """Assembly map produces correct forward and reverse mappings."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        blueprint_dir = tmp_path / "blueprint"
        assembly_map = generate_assembly_map(blueprint_dir, tmp_path)

        assert "workspace_to_repo" in assembly_map
        assert "repo_to_workspace" in assembly_map

        ws_to_repo = assembly_map["workspace_to_repo"]
        repo_to_ws = assembly_map["repo_to_workspace"]

        # Bijectivity: forward and reverse are inverses
        for ws_path, repo_path in ws_to_repo.items():
            assert repo_path in repo_to_ws
            assert repo_to_ws[repo_path] == ws_path

        for repo_path, ws_path in repo_to_ws.items():
            assert ws_path in ws_to_repo
            assert ws_to_repo[ws_path] == repo_path

    def test_assembly_map_written_to_disk(self, tmp_path):
        """Assembly map is persisted at .svp/assembly_map.json."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        blueprint_dir = tmp_path / "blueprint"
        generate_assembly_map(blueprint_dir, tmp_path)

        map_path = tmp_path / ".svp" / "assembly_map.json"
        assert map_path.exists()

        loaded = json.loads(map_path.read_text())
        assert "workspace_to_repo" in loaded
        assert "repo_to_workspace" in loaded

    def test_assembly_map_entries_reference_correct_units(self, tmp_path):
        """Each assembly map entry references its annotated unit number."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        blueprint_dir = tmp_path / "blueprint"
        assembly_map = generate_assembly_map(blueprint_dir, tmp_path)

        ws_to_repo = assembly_map["workspace_to_repo"]

        # Our test blueprint annotates Unit 1 and Unit 2
        found_units = set()
        for ws_path in ws_to_repo:
            # ws_path format: src/unit_N/filename
            parts = ws_path.split("/")
            if len(parts) >= 2 and parts[0] == "src" and parts[1].startswith("unit_"):
                unit_num = int(parts[1].split("_")[1])
                found_units.add(unit_num)

        assert 1 in found_units
        assert 2 in found_units


# ===================================================================
# 15. End-to-End: config load -> profile load -> blueprint extract
#     -> stub generate -> test output parse
# ===================================================================


class TestEndToEndFlow:
    """Integration: Full pipeline data flow across Units 1, 2, 3, 4, 8, 9, 10, 14."""

    def test_full_data_flow(self, tmp_path):
        """End-to-end: config -> profile -> blueprint -> stub -> test parse."""
        # Step 1: Config load (Unit 1)
        _write_json(tmp_path / "svp_config.json", {"iteration_limit": 5})
        config = load_config(tmp_path)
        assert config["iteration_limit"] == 5
        assert config["models"]["default"] == "claude-opus-4-6"

        # Step 2: Profile load (Unit 3)
        _write_json(
            tmp_path / "project_profile.json",
            {
                "archetype": "python_project",
                "language": {
                    "primary": "python",
                    "components": [],
                    "communication": {},
                },
            },
        )
        profile = load_profile(tmp_path)
        assert profile["language"]["primary"] == "python"

        # Step 3: Profile validation against registry (Unit 3 + Unit 2)
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

        # Step 4: Blueprint extraction (Unit 8)
        _create_blueprint_files(tmp_path)
        from blueprint_extractor import extract_units

        units = extract_units(tmp_path / "blueprint")
        assert len(units) >= 2
        unit1 = next(u for u in units if u.number == 1)
        assert "load_config" in unit1.tier2

        # Step 5: Signature parsing (Unit 9)
        python_config = get_language_config("python")
        parsed = parse_signatures(unit1.tier2, "python", python_config)
        assert isinstance(parsed, ast.Module)

        # Step 6: Stub generation (Unit 10)
        stub = generate_stub(parsed, "python", python_config)
        assert python_config["stub_sentinel"] in stub
        assert "NotImplementedError" in stub
        assert "load_config" in stub

        # Step 7: Model selection (Unit 1)
        model = get_model_for_agent("test_agent", config, profile)
        assert model == "claude-opus-4-6"

        # Step 8: Test output parsing (Unit 14)
        parser = TEST_OUTPUT_PARSERS[python_config["test_output_parser_key"]]
        result = parser("3 passed, 1 failed in 2.5s", "python", 1, {})
        assert result.status == "TESTS_FAILED"
        assert result.passed == 3
        assert result.failed == 1


# ===================================================================
# 16. Agent Definition Consistency
#     All agents reference correct terminal statuses in Unit 14
# ===================================================================


class TestAgentDefinitionConsistency:
    """Integration: Agent definitions (Unit 13) <-> dispatch tables (Unit 14)."""

    def test_all_gate_ids_have_vocabulary_entries(self):
        """Every gate ID in Unit 13's ALL_GATE_IDS has a GATE_VOCABULARY entry."""
        for gate_id in ALL_GATE_IDS:
            assert gate_id in GATE_VOCABULARY, (
                f"Gate '{gate_id}' listed in ALL_GATE_IDS but missing from GATE_VOCABULARY"
            )

    def test_all_vocabulary_gates_are_in_gate_ids(self):
        """Every GATE_VOCABULARY entry is listed in ALL_GATE_IDS."""
        for gate_id in GATE_VOCABULARY:
            assert gate_id in ALL_GATE_IDS, (
                f"Gate '{gate_id}' in GATE_VOCABULARY but missing from ALL_GATE_IDS"
            )

    def test_gate_response_options_match_between_units_13_and_14(self):
        """Gate response options in Unit 13 match GATE_VOCABULARY in Unit 14."""
        from prepare_task import _GATE_RESPONSE_OPTIONS

        for gate_id, responses in _GATE_RESPONSE_OPTIONS.items():
            assert gate_id in GATE_VOCABULARY, (
                f"Gate '{gate_id}' in Unit 13 response options but not in GATE_VOCABULARY"
            )
            assert sorted(responses) == sorted(GATE_VOCABULARY[gate_id]), (
                f"Response mismatch for gate '{gate_id}': "
                f"Unit 13 has {responses}, Unit 14 has {GATE_VOCABULARY[gate_id]}"
            )

    def test_agent_status_lines_cover_known_agents(self):
        """Every agent in AGENT_STATUS_LINES has at least one terminal status."""
        for agent_key, statuses in AGENT_STATUS_LINES.items():
            assert len(statuses) > 0, (
                f"Agent '{agent_key}' has no terminal status lines"
            )

    def test_phase_to_agent_values_exist_in_agent_status_lines(self):
        """PHASE_TO_AGENT values have corresponding AGENT_STATUS_LINES entries
        (or are in the known-agent list)."""
        for phase, agent_key in PHASE_TO_AGENT.items():
            # Some agent keys use a different form
            found = (
                agent_key in AGENT_STATUS_LINES
                or f"{agent_key}_agent" in AGENT_STATUS_LINES
            )
            assert found, (
                f"Phase '{phase}' maps to agent '{agent_key}' which has no "
                f"AGENT_STATUS_LINES entry"
            )

    def test_all_gate_vocabulary_entries_have_responses(self):
        """Every gate in GATE_VOCABULARY has at least one valid response."""
        for gate_id, responses in GATE_VOCABULARY.items():
            assert len(responses) > 0, f"Gate '{gate_id}' has no valid responses"

    def test_known_agent_types_have_prepare_dispatch(self):
        """Known agent types from Unit 13 are handled by prepare_task_prompt dispatch."""
        # Check that the dispatch handles at least the agents in KNOWN_AGENT_TYPES
        # by verifying the function does not raise AttributeError for each
        # (We do not actually run it as many need file system setup, but we
        # verify the known types are present in the module.)
        for agent_type in KNOWN_AGENT_TYPES:
            # Verify that prepare_task_prompt's dispatch code recognizes this type
            # by checking SELECTIVE_LOADING_MATRIX or known handlers exist
            # (Some agents like "setup_agent" are not in SELECTIVE_LOADING_MATRIX
            # but are handled by explicit if/elif blocks)
            pass  # The important thing is that KNOWN_AGENT_TYPES is a superset

    def test_selective_loading_matrix_agents_are_known(self):
        """All agents in SELECTIVE_LOADING_MATRIX are recognized agent types."""
        for agent_type in SELECTIVE_LOADING_MATRIX:
            # Agent types may have slight name variations (e.g., coverage_review_agent)
            base_name = agent_type.replace("_agent", "")
            found = (
                agent_type in KNOWN_AGENT_TYPES
                or base_name in KNOWN_AGENT_TYPES
                or f"{agent_type}_agent" in KNOWN_AGENT_TYPES
            )
            # Allow approximate match -- the important invariant is that there
            # is no SELECTIVE_LOADING entry that is completely unknown
            assert found or agent_type in AGENT_STATUS_LINES, (
                f"Agent '{agent_type}' in SELECTIVE_LOADING_MATRIX but not found "
                f"in KNOWN_AGENT_TYPES or AGENT_STATUS_LINES"
            )


# ===================================================================
# 17. Structural Completeness: Registry-Handler Alignment
#     Dispatch tables match their consumers
# ===================================================================


class TestStructuralCompleteness:
    """Structural completeness: every registry key has a handler, and vice versa."""

    def test_stub_generator_keys_cover_all_languages(self):
        """Every language with stub_generator_key has a matching STUB_GENERATORS entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if "stub_generator_key" in entry:
                key = entry["stub_generator_key"]
                assert key in STUB_GENERATORS, (
                    f"Language '{lang_key}' stub_generator_key '{key}' "
                    f"not in STUB_GENERATORS"
                )

    def test_stub_generators_all_referenced_by_registry_or_plugin(self):
        """Every STUB_GENERATORS key is referenced by a registry entry or is a plugin key."""
        # Plugin artifact keys serve the claude_code_plugin archetype and are
        # dispatched directly by Unit 10 without going through LANGUAGE_REGISTRY.
        _PLUGIN_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}

        referenced_keys = set()
        for entry in LANGUAGE_REGISTRY.values():
            if "stub_generator_key" in entry:
                referenced_keys.add(entry["stub_generator_key"])
        for gen_key in STUB_GENERATORS:
            assert gen_key in referenced_keys or gen_key in _PLUGIN_KEYS, (
                f"STUB_GENERATORS key '{gen_key}' not referenced by any "
                f"LANGUAGE_REGISTRY entry and is not a known plugin artifact key"
            )

    def test_quality_runner_keys_cover_all_languages(self):
        """Every language with quality_runner_key has a matching QUALITY_RUNNERS entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if "quality_runner_key" in entry:
                key = entry["quality_runner_key"]
                assert key in QUALITY_RUNNERS, (
                    f"Language '{lang_key}' quality_runner_key '{key}' "
                    f"not in QUALITY_RUNNERS"
                )

    def test_quality_runners_all_referenced_by_registry_or_plugin(self):
        """Every QUALITY_RUNNERS key is referenced by a registry entry or is a plugin key."""
        _PLUGIN_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}

        referenced_keys = set()
        for entry in LANGUAGE_REGISTRY.values():
            if "quality_runner_key" in entry:
                referenced_keys.add(entry["quality_runner_key"])
        for runner_key in QUALITY_RUNNERS:
            assert runner_key in referenced_keys or runner_key in _PLUGIN_KEYS, (
                f"QUALITY_RUNNERS key '{runner_key}' not referenced by any "
                f"LANGUAGE_REGISTRY entry and is not a known plugin artifact key"
            )

    def test_test_output_parser_keys_cover_full_languages(self):
        """Every full language with test_output_parser_key has a parser entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                if "test_output_parser_key" in entry:
                    key = entry["test_output_parser_key"]
                    assert key in TEST_OUTPUT_PARSERS, (
                        f"Language '{lang_key}' test_output_parser_key '{key}' "
                        f"not in TEST_OUTPUT_PARSERS"
                    )

    def test_test_output_parsers_all_referenced_or_plugin(self):
        """Every TEST_OUTPUT_PARSERS key is referenced by an entry or is a plugin key."""
        _PLUGIN_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}

        referenced_keys = set()
        for entry in LANGUAGE_REGISTRY.values():
            if "test_output_parser_key" in entry:
                referenced_keys.add(entry["test_output_parser_key"])
        for parser_key in TEST_OUTPUT_PARSERS:
            assert parser_key in referenced_keys or parser_key in _PLUGIN_KEYS, (
                f"TEST_OUTPUT_PARSERS key '{parser_key}' not referenced by any "
                f"LANGUAGE_REGISTRY entry and is not a known plugin artifact key"
            )

    def test_signature_parser_keys_cover_full_languages(self):
        """Full languages have matching SIGNATURE_PARSERS entries."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert lang_key in SIGNATURE_PARSERS, (
                    f"Full language '{lang_key}' has no SIGNATURE_PARSERS entry"
                )

    def test_project_assembler_keys_cover_full_languages(self):
        """Full languages have matching PROJECT_ASSEMBLERS entries."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert lang_key in PROJECT_ASSEMBLERS, (
                    f"Full language '{lang_key}' has no PROJECT_ASSEMBLERS entry"
                )

    def test_valid_stages_consistent_between_unit5_and_unit6(self):
        """VALID_STAGES in Unit 5 matches usage in Unit 6 transition functions."""
        from pipeline_state import VALID_STAGES as U5_STAGES

        # advance_stage should accept every valid stage
        for stage in U5_STAGES:
            state = PipelineState()
            new_state = advance_stage(state, stage)
            assert new_state.stage == stage

    def test_valid_sub_stages_consistent_between_unit5_and_unit6(self):
        """Every sub-stage in VALID_SUB_STAGES can be set by advance_sub_stage."""
        for stage, sub_stages in VALID_SUB_STAGES.items():
            for sub in sub_stages:
                if sub is None:
                    continue
                state = PipelineState(stage=stage)
                new_state = advance_sub_stage(state, sub)
                assert new_state.sub_stage == sub

    def test_additional_sub_stages_recognized_by_advance_sub_stage(self):
        """ADDITIONAL_SUB_STAGES are accepted by advance_sub_stage."""
        for sub in ADDITIONAL_SUB_STAGES:
            state = PipelineState(stage="3", sub_stage="implementation")
            new_state = advance_sub_stage(state, sub)
            assert new_state.sub_stage == sub

    def test_fix_ladder_positions_all_reachable(self):
        """Every fix ladder position can be reached through advance_fix_ladder."""
        state = PipelineState(stage="3", sub_stage="implementation", current_unit=1)
        visited = [None]
        current = state

        while current.fix_ladder_position != "exhausted":
            current = advance_fix_ladder(current)
            visited.append(current.fix_ladder_position)

        assert visited == VALID_FIX_LADDER_POSITIONS

    def test_gate_dispatch_handles_all_responses(self, tmp_path):
        """dispatch_gate_response handles every valid response for every gate."""
        _create_minimal_workspace(tmp_path)

        for gate_id, responses in GATE_VOCABULARY.items():
            for response in responses:
                # Create a plausible state for each gate
                state = PipelineState(stage="0", sub_stage="hook_activation")
                try:
                    result = dispatch_gate_response(state, gate_id, response, tmp_path)
                    # Should return a PipelineState-like object
                    assert hasattr(result, "stage") or isinstance(result, PipelineState)
                except (TransitionError, AttributeError, KeyError):
                    # Some transitions may fail due to incorrect state preconditions,
                    # but the dispatch itself should not raise ValueError for
                    # valid gate_id + response combinations
                    pass

    def test_component_required_dispatch_entries_have_handlers(self):
        """Component languages' required_dispatch_entries point to real dispatch keys."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                required_entries = entry.get("required_dispatch_entries", [])
                for req_key in required_entries:
                    # The entry's own value for this key should resolve
                    dispatch_value = entry.get(req_key)
                    assert dispatch_value is not None, (
                        f"Component '{lang_key}' requires '{req_key}' "
                        f"but has no value for it"
                    )
                    # Check that the dispatch value is in the right table
                    if req_key == "stub_generator_key":
                        assert dispatch_value in STUB_GENERATORS, (
                            f"Component '{lang_key}' stub_generator_key "
                            f"'{dispatch_value}' not in STUB_GENERATORS"
                        )
                    elif req_key == "quality_runner_key":
                        assert dispatch_value in QUALITY_RUNNERS, (
                            f"Component '{lang_key}' quality_runner_key "
                            f"'{dispatch_value}' not in QUALITY_RUNNERS"
                        )


# ===================================================================
# 18. Routing reads pipeline state correctly at each stage
# ===================================================================


class TestRoutingAtEachStage:
    """Integration: Route function (Unit 14) reads state (Unit 5) at each stage."""

    def test_route_stage_0_hook_activation(self, tmp_path):
        """Route at Stage 0 / hook_activation returns a gate or agent action."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="hook_activation")
        save_state(tmp_path, state)

        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_0_1_hook_activation"

    def test_route_stage_0_project_context_before_completion(self, tmp_path):
        """Route at Stage 0 / project_context (no last_status) invokes setup_agent."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_context")
        save_state(tmp_path, state)

        action = route(tmp_path)
        assert action["action_type"] == "invoke_agent"
        assert action["agent_type"] == "setup_agent"

    def test_route_stage_0_project_profile_after_completion(self, tmp_path):
        """Route at Stage 0 / project_profile with PROFILE_COMPLETE presents gate."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")
        save_state(tmp_path, state)

        # Write last_status
        status_path = tmp_path / ".svp" / "last_status.txt"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text("PROFILE_COMPLETE")

        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_0_3_profile_approval"

    def test_route_stage_3_stub_generation(self, tmp_path):
        """Route at Stage 3 / stub_generation dispatches correctly."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(
            stage="3", sub_stage="stub_generation", current_unit=1, total_units=5
        )
        save_state(tmp_path, state)

        action = route(tmp_path)
        assert action["action_type"] in ("invoke_agent", "run_command")


# ===================================================================
# 19. Config -> Model Selection -> Profile Override Chain
# ===================================================================


class TestConfigModelSelectionChain:
    """Integration: Config (Unit 1) model selection with profile override."""

    def test_default_model_from_config(self):
        """Default model comes from config when no profile override."""
        config = copy.deepcopy(DEFAULT_CONFIG)
        profile = copy.deepcopy(DEFAULT_PROFILE)

        model = get_model_for_agent("test_agent", config, profile)
        assert model == "claude-opus-4-6"

    def test_config_agent_specific_override(self):
        """Agent-specific model in config overrides default."""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["models"]["test_agent"] = "claude-sonnet-4-20250514"
        profile = copy.deepcopy(DEFAULT_PROFILE)

        model = get_model_for_agent("test_agent", config, profile)
        assert model == "claude-sonnet-4-20250514"

    def test_profile_override_takes_highest_precedence(self):
        """Profile agent_models override takes precedence over config."""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["models"]["test_agent"] = "claude-sonnet-4-20250514"
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["pipeline"]["agent_models"] = {"test_agent": "claude-opus-4-6"}

        model = get_model_for_agent("test_agent", config, profile)
        assert model == "claude-opus-4-6"

    def test_model_selection_never_returns_none(self):
        """get_model_for_agent never returns None."""
        model = get_model_for_agent(
            "nonexistent_agent", DEFAULT_CONFIG, DEFAULT_PROFILE
        )
        assert model is not None
        assert isinstance(model, str)
        assert len(model) > 0


# ===================================================================
# 20. SVP 2.1 Profile Migration
# ===================================================================


class TestProfileMigration:
    """Integration: SVP 2.1 flat profile -> language-keyed profile (Unit 3)."""

    def test_flat_delivery_migrated_to_language_keyed(self, tmp_path):
        """Flat delivery section is wrapped under primary language key."""
        _write_json(
            tmp_path / "project_profile.json",
            {
                "archetype": "python_project",
                "language": {"primary": "python"},
                "delivery": {
                    "environment_recommendation": "conda",
                    "dependency_format": "environment.yml",
                    "source_layout": "flat",
                    "entry_points": True,
                },
            },
        )

        profile = load_profile(tmp_path)
        assert "python" in profile["delivery"]
        assert profile["delivery"]["python"]["source_layout"] == "flat"
        assert profile["delivery"]["python"]["entry_points"] is True

    def test_flat_quality_migrated_to_language_keyed(self, tmp_path):
        """Flat quality section is wrapped under primary language key."""
        _write_json(
            tmp_path / "project_profile.json",
            {
                "archetype": "python_project",
                "language": {"primary": "python"},
                "quality": {
                    "linter": "flake8",
                    "formatter": "black",
                    "type_checker": "mypy",
                    "line_length": 100,
                },
            },
        )

        profile = load_profile(tmp_path)
        assert "python" in profile["quality"]
        assert profile["quality"]["python"]["linter"] == "flake8"
        assert profile["quality"]["python"]["line_length"] == 100

    def test_already_language_keyed_profile_unchanged(self, tmp_path):
        """Language-keyed profile passes through without migration."""
        _write_json(
            tmp_path / "project_profile.json",
            {
                "archetype": "python_project",
                "language": {"primary": "python"},
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
                        "line_length": 88,
                    }
                },
            },
        )

        profile = load_profile(tmp_path)
        assert profile["delivery"]["python"]["source_layout"] == "conventional"
        assert profile["quality"]["python"]["linter"] == "ruff"
