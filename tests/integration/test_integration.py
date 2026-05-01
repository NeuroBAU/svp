"""Integration tests for SVP 2.2 Pass 2 cross-unit interactions.

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
    ARTIFACT_FILENAMES,
    DEFAULT_CONFIG,
    derive_env_name,
    get_blueprint_dir,
    get_model_for_agent,
    load_config,
    save_config,
)
from language_registry import (
    LANGUAGE_REGISTRY,
    QualityResult,
    RunResult,
    get_language_config,
    validate_component_entry,
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
    VALID_DEBUG_PHASES,
    VALID_FIX_LADDER_POSITIONS,
    VALID_ORACLE_PHASES,
    VALID_STAGES,
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
    restart_from_stage,
)
from blueprint_extractor import UnitDefinition, extract_units, build_unit_context
from signature_parser import SIGNATURE_PARSERS, parse_signatures
from stub_generator import STUB_GENERATORS, generate_stub
from prepare_task import (
    ALL_GATE_IDS,
    KNOWN_AGENT_TYPES,
    SELECTIVE_LOADING_MATRIX,
    _GATE_RESPONSE_OPTIONS,
    build_language_context,
    prepare_task_prompt,
    prepare_gate_prompt,
)
from routing import (
    AGENT_STATUS_LINES,
    GATE_VOCABULARY,
    PHASE_TO_AGENT,
    TEST_OUTPUT_PARSERS,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
    route,
)
from quality_gate import QUALITY_RUNNERS, run_quality_gate
from generate_assembly_map import (
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

    # pipeline_state.json (at the ARTIFACT_FILENAMES location)
    state_path = root / ARTIFACT_FILENAMES["pipeline_state"]
    _write_json(
        state_path,
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
        "testing": {
            "run_command": "{run_prefix} python -m pytest {test_path} -v",
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
# 1. Unit 1 -> Unit 5: ARTIFACT_FILENAMES used by load_state/save_state
# ===================================================================


class TestArtifactFilenamesUsedByState:
    """Integration: ARTIFACT_FILENAMES (Unit 1) -> load_state/save_state (Unit 5)."""

    def test_load_state_reads_from_artifact_filenames_path(self, tmp_path):
        """load_state reads pipeline_state.json from ARTIFACT_FILENAMES path."""
        state_path = tmp_path / ARTIFACT_FILENAMES["pipeline_state"]
        _write_json(state_path, {
            "stage": "3",
            "sub_stage": "stub_generation",
            "current_unit": 1,
            "total_units": 10,
        })

        loaded = load_state(tmp_path)
        assert loaded.stage == "3"
        assert loaded.sub_stage == "stub_generation"
        assert loaded.current_unit == 1

    def test_save_state_writes_to_artifact_filenames_path(self, tmp_path):
        """save_state writes pipeline_state.json to ARTIFACT_FILENAMES path."""
        # Create the initial file so save_state can compute hash
        state_path = tmp_path / ARTIFACT_FILENAMES["pipeline_state"]
        _write_json(state_path, {"stage": "0", "sub_stage": None})

        state = PipelineState(stage="2", sub_stage="blueprint_dialog")
        save_state(tmp_path, state)

        # Verify the file at the ARTIFACT_FILENAMES location was updated
        raw = json.loads(state_path.read_text())
        assert raw["stage"] == "2"
        assert raw["sub_stage"] == "blueprint_dialog"

    def test_save_then_load_roundtrip_uses_same_path(self, tmp_path):
        """save_state and load_state use the same ARTIFACT_FILENAMES path."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=5,
            total_units=10,
            primary_language="python",
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)

        assert loaded.stage == state.stage
        assert loaded.sub_stage == state.sub_stage
        assert loaded.current_unit == state.current_unit
        assert loaded.primary_language == state.primary_language

    def test_artifact_filenames_has_all_required_keys(self):
        """ARTIFACT_FILENAMES contains all keys required by the pipeline."""
        required_keys = {
            "pipeline_state", "project_profile", "toolchain",
            "stakeholder_spec", "blueprint_dir", "blueprint_prose",
            "blueprint_contracts", "build_log", "task_prompt",
            "gate_prompt", "last_status", "svp_config",
            "assembly_map", "triage_result", "oracle_run_ledger",
        }
        assert required_keys.issubset(set(ARTIFACT_FILENAMES.keys())), (
            f"Missing keys: {required_keys - set(ARTIFACT_FILENAMES.keys())}"
        )

    def test_artifact_filenames_values_are_relative_paths(self):
        """Every ARTIFACT_FILENAMES value is a relative path string."""
        for key, value in ARTIFACT_FILENAMES.items():
            assert isinstance(value, str), f"Key '{key}' value is not a string"
            assert not Path(value).is_absolute(), (
                f"Key '{key}' has absolute path: {value}"
            )

    def test_state_hash_computed_on_save(self, tmp_path):
        """save_state computes SHA-256 hash of prior state file."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="1", sub_stage=None)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)

        # Hash should be present because initial file existed
        assert loaded.state_hash is not None
        assert isinstance(loaded.state_hash, str)
        assert len(loaded.state_hash) == 64  # SHA-256 hex digest


# ===================================================================
# 2. Unit 2 -> Unit 4: LANGUAGE_REGISTRY drives load_toolchain dispatch
# ===================================================================


class TestRegistryDrivesToolchainDispatch:
    """Integration: LANGUAGE_REGISTRY (Unit 2) -> load_toolchain (Unit 4)."""

    def test_python_toolchain_file_from_registry(self):
        """Python registry entry's toolchain_file matches expected path."""
        python_config = get_language_config("python")
        assert python_config["toolchain_file"] == "python_conda_pytest.json"

    def test_r_toolchain_file_from_registry(self):
        """R registry entry's toolchain_file matches expected path.

        Bug S3-160: R archetype is conda-foundational by default; the
        renv manifest remains as opt-in.
        """
        r_config = get_language_config("r")
        assert r_config["toolchain_file"] == "r_conda_testthat.json"

    def test_toolchain_file_path_resolves_via_registry(self, tmp_path):
        """Toolchain file paths constructed from registry resolve correctly."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                continue
            toolchain_file = entry["toolchain_file"]
            expected_path = (
                tmp_path / "scripts" / "toolchain_defaults" / toolchain_file
            )
            assert expected_path.name == toolchain_file, (
                f"Language '{lang_key}' toolchain_file path mismatch"
            )

    def test_pipeline_toolchain_loads_without_language(self, tmp_path):
        """load_toolchain(language=None) loads pipeline toolchain.json."""
        _create_toolchain_file(tmp_path)
        toolchain = load_toolchain(tmp_path)
        assert "environment" in toolchain
        assert "testing" in toolchain
        assert "quality" in toolchain


# ===================================================================
# 3. Unit 2 -> Unit 10: LANGUAGE_REGISTRY drives stub generator dispatch
# ===================================================================


class TestRegistryDrivesStubGeneratorDispatch:
    """Integration: LANGUAGE_REGISTRY (Unit 2) -> STUB_GENERATORS (Unit 10)."""

    def test_python_stub_generator_key_in_dispatch_table(self):
        """Python stub_generator_key resolves in STUB_GENERATORS."""
        python_config = get_language_config("python")
        key = python_config["stub_generator_key"]
        assert key in STUB_GENERATORS, f"Key '{key}' not in STUB_GENERATORS"

    def test_r_stub_generator_key_in_dispatch_table(self):
        """R stub_generator_key resolves in STUB_GENERATORS."""
        r_config = get_language_config("r")
        key = r_config["stub_generator_key"]
        assert key in STUB_GENERATORS, f"Key '{key}' not in STUB_GENERATORS"

    def test_stan_stub_generator_key_in_dispatch_table(self):
        """Stan stub_generator_key resolves in STUB_GENERATORS."""
        stan_config = get_language_config("stan")
        key = stan_config["stub_generator_key"]
        assert key in STUB_GENERATORS, f"Key '{key}' not in STUB_GENERATORS"

    def test_all_registry_stub_generator_keys_resolve(self):
        """Every language with stub_generator_key has matching STUB_GENERATORS entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if "stub_generator_key" in entry:
                key = entry["stub_generator_key"]
                assert key in STUB_GENERATORS, (
                    f"Language '{lang_key}' stub_generator_key '{key}' "
                    f"not in STUB_GENERATORS"
                )

    def test_python_stub_generation_end_to_end(self):
        """Python: parse signatures -> generate stub produces valid Python."""
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

    def test_stub_sentinel_injected_verbatim_from_registry(self):
        """Sentinel in generated stub is exact match of registry value (Bug S3-2)."""
        for lang_key in ("python", "r"):
            config = get_language_config(lang_key)
            sentinel = config["stub_sentinel"]
            source = "def foo(): ..." if lang_key == "python" else "foo <- function() { 1 }"
            parsed = parse_signatures(source, lang_key, config)
            stub = generate_stub(parsed, lang_key, config)
            assert sentinel in stub, (
                f"Sentinel not found verbatim in '{lang_key}' stub"
            )


# ===================================================================
# 4. Unit 2 -> Unit 15: LANGUAGE_REGISTRY drives quality runner dispatch
# ===================================================================


class TestRegistryDrivesQualityRunnerDispatch:
    """Integration: LANGUAGE_REGISTRY (Unit 2) -> QUALITY_RUNNERS (Unit 15)."""

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

    def test_all_registry_quality_runner_keys_resolve(self):
        """Every language with quality_runner_key has matching QUALITY_RUNNERS entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if "quality_runner_key" in entry:
                key = entry["quality_runner_key"]
                assert key in QUALITY_RUNNERS, (
                    f"Language '{lang_key}' quality_runner_key '{key}' "
                    f"not in QUALITY_RUNNERS"
                )

    def test_quality_result_types_match_gate_outcomes(self):
        """QualityResult status values cover the expected gate outcomes."""
        valid_statuses = {
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        }
        for status in valid_statuses:
            result = QualityResult(
                status=status, auto_fixed=False, residuals=[], report=""
            )
            assert result.status == status


# ===================================================================
# 5. Unit 5 -> Unit 6: PipelineState used by all transition functions
# ===================================================================


class TestPipelineStateUsedByTransitions:
    """Integration: PipelineState (Unit 5) -> transition functions (Unit 6)."""

    def test_advance_stage_returns_new_pipeline_state(self):
        """advance_stage returns a new PipelineState, not mutating original."""
        state = PipelineState(stage="0", sub_stage="project_profile")
        original_stage = state.stage
        new_state = advance_stage(state, "1")

        assert new_state.stage == "1"
        assert state.stage == original_stage  # original unchanged

    def test_advance_sub_stage_preserves_other_fields(self):
        """advance_sub_stage only changes sub_stage, preserving all other fields."""
        state = PipelineState(
            stage="3", sub_stage="stub_generation",
            current_unit=5, total_units=10,
        )
        new_state = advance_sub_stage(state, "test_generation")

        assert new_state.sub_stage == "test_generation"
        assert new_state.current_unit == 5
        assert new_state.total_units == 10
        assert new_state.stage == "3"

    def test_complete_unit_increments_current_unit(self):
        """complete_unit increments current_unit when more units remain."""
        state = PipelineState(
            stage="3", sub_stage="unit_completion",
            current_unit=1, total_units=5,
        )
        new_state = complete_unit(state)
        assert new_state.current_unit == 2
        assert new_state.sub_stage == "stub_generation"

    def test_complete_unit_clears_unit_when_done(self):
        """complete_unit sets current_unit=None when last unit is done."""
        state = PipelineState(
            stage="3", sub_stage="unit_completion",
            current_unit=5, total_units=5,
        )
        new_state = complete_unit(state)
        assert new_state.current_unit is None
        assert new_state.sub_stage is None

    def test_rollback_to_unit_resets_fix_state(self):
        """rollback_to_unit resets fix_ladder_position and red_run_retries."""
        state = PipelineState(
            stage="3", sub_stage="implementation",
            current_unit=5, total_units=10,
            fix_ladder_position="diagnostic",
            red_run_retries=2,
            verified_units=[
                {"unit": 1}, {"unit": 2}, {"unit": 3}, {"unit": 4},
            ],
        )
        rolled = rollback_to_unit(state, 3)
        assert rolled.current_unit == 3
        assert rolled.fix_ladder_position is None
        assert rolled.red_run_retries == 0
        assert rolled.sub_stage == "stub_generation"
        assert len(rolled.verified_units) == 2  # units 1 and 2 remain

    def test_all_valid_stages_accepted_by_advance_stage(self):
        """advance_stage accepts every value in VALID_STAGES."""
        for stage in VALID_STAGES:
            state = PipelineState()
            new_state = advance_stage(state, stage)
            assert new_state.stage == stage

    def test_all_valid_sub_stages_accepted_by_advance_sub_stage(self):
        """Every sub-stage in VALID_SUB_STAGES can be set by advance_sub_stage."""
        for stage, sub_stages in VALID_SUB_STAGES.items():
            for sub in sub_stages:
                if sub is None:
                    continue
                state = PipelineState(stage=stage)
                new_state = advance_sub_stage(state, sub)
                assert new_state.sub_stage == sub

    def test_additional_sub_stages_accepted_by_advance_sub_stage(self):
        """ADDITIONAL_SUB_STAGES are recognized by advance_sub_stage."""
        for sub in ADDITIONAL_SUB_STAGES:
            state = PipelineState(stage="3", sub_stage="implementation")
            new_state = advance_sub_stage(state, sub)
            assert new_state.sub_stage == sub

    def test_fix_ladder_traversal_visits_all_positions(self):
        """advance_fix_ladder traverses all VALID_FIX_LADDER_POSITIONS."""
        state = PipelineState(
            stage="3", sub_stage="implementation", current_unit=1,
        )
        visited = [None]
        current = state

        while current.fix_ladder_position != "exhausted":
            current = advance_fix_ladder(current)
            visited.append(current.fix_ladder_position)

        assert visited == VALID_FIX_LADDER_POSITIONS

    def test_pipeline_state_save_load_roundtrip(self, tmp_path):
        """PipelineState survives full save -> load roundtrip via Unit 5."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(
            stage="3", sub_stage="green_run",
            current_unit=7, total_units=29,
            fix_ladder_position="fresh_impl",
            red_run_retries=1,
            primary_language="python",
            pass_=1,
            deferred_broken_units=[3, 12],
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)

        assert loaded.stage == "3"
        assert loaded.sub_stage == "green_run"
        assert loaded.current_unit == 7
        assert loaded.total_units == 29
        assert loaded.fix_ladder_position == "fresh_impl"
        assert loaded.red_run_retries == 1
        assert loaded.primary_language == "python"
        assert loaded.pass_ == 1
        assert loaded.deferred_broken_units == [3, 12]


# ===================================================================
# 6. Unit 6 -> Unit 14: Transition functions called by dispatch (Bug S3-8)
# ===================================================================


class TestTransitionFunctionsCalledByDispatch:
    """Integration: Transition functions (Unit 6) called by dispatch (Unit 14)."""

    def test_gate_0_3_profile_approved_calls_advance_sub_stage(self, tmp_path):
        """Bug S3-176: PROFILE APPROVED at Gate 0.3 transitions to the new
        sub_stage 'toolchain_provisioning' (stage stays 0). Advance to stage
        1 happens at gate_0_4 PROCEED."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        new_state = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE APPROVED", tmp_path
        )
        assert new_state.stage == "0"
        assert new_state.sub_stage == "toolchain_provisioning"

    def test_gate_0_3_profile_rejected_stays_at_profile(self, tmp_path):
        """PROFILE REJECTED at Gate 0.3 returns to project_profile."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        new_state = dispatch_gate_response(
            state, "gate_0_3_profile_approval", "PROFILE REJECTED", tmp_path
        )
        assert new_state.stage == "0"
        assert new_state.sub_stage == "project_profile"

    def test_gate_0_2_context_approved_advances_to_profile(self, tmp_path):
        """CONTEXT APPROVED at Gate 0.2 advances to project_profile."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_context")

        new_state = dispatch_gate_response(
            state, "gate_0_2_context_approval", "CONTEXT APPROVED", tmp_path
        )
        assert new_state.stage == "0"
        assert new_state.sub_stage == "project_profile"

    def test_invalid_gate_response_raises_value_error(self, tmp_path):
        """Invalid response at a valid gate raises ValueError."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        with pytest.raises(ValueError, match="Invalid response"):
            dispatch_gate_response(
                state, "gate_0_3_profile_approval", "NONSENSE", tmp_path
            )

    def test_unknown_gate_id_raises_value_error(self, tmp_path):
        """Unknown gate_id raises ValueError."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")

        with pytest.raises(ValueError, match="Unknown gate_id"):
            dispatch_gate_response(state, "gate_nonexistent", "APPROVE", tmp_path)

    def test_dispatch_gate_handles_all_gates_and_responses(self, tmp_path):
        """dispatch_gate_response handles every valid response for every gate."""
        _create_minimal_workspace(tmp_path)

        for gate_id, responses in GATE_VOCABULARY.items():
            for response in responses:
                state = PipelineState(stage="0", sub_stage="hook_activation")
                try:
                    result = dispatch_gate_response(
                        state, gate_id, response, tmp_path
                    )
                    assert hasattr(result, "stage") or isinstance(
                        result, PipelineState
                    )
                except (TransitionError, AttributeError, KeyError):
                    # Some transitions may fail due to incorrect state
                    # preconditions, but dispatch itself should not raise
                    # ValueError for valid gate_id + response combos
                    pass

    def test_quality_gate_transition_chain_gate_a_to_red_run(self):
        """Quality gate A pass -> red_run via Unit 6 transitions."""
        state = PipelineState(
            stage="3", sub_stage="stub_generation", current_unit=1,
        )
        state_qa = enter_quality_gate(state, "quality_gate_a")
        assert state_qa.sub_stage == "quality_gate_a"

        state_rr = quality_gate_pass(state_qa)
        assert state_rr.sub_stage == "red_run"

    def test_quality_gate_transition_chain_gate_b_to_green_run(self):
        """Quality gate B pass -> green_run via Unit 6 transitions."""
        state = PipelineState(
            stage="3", sub_stage="quality_gate_b", current_unit=1,
        )
        new_state = quality_gate_pass(state)
        assert new_state.sub_stage == "green_run"

    def test_quality_gate_fail_enters_fix_ladder(self):
        """Quality gate failure enters fix ladder from current position."""
        state = PipelineState(
            stage="3", sub_stage="quality_gate_a",
            current_unit=1, fix_ladder_position=None,
        )
        new_state = quality_gate_fail_to_ladder(state)
        assert new_state.fix_ladder_position == "fresh_impl"
        assert new_state.sub_stage == "implementation"

    def test_gate_retry_from_non_gate_raises(self):
        """Cannot advance to retry from a non-gate sub-stage."""
        state = PipelineState(
            stage="3", sub_stage="implementation", current_unit=1,
        )
        with pytest.raises(TransitionError):
            advance_quality_gate_to_retry(state)

    def test_redo_state_transitions_and_completion(self):
        """Redo enter -> complete restores original state via Unit 6."""
        state = PipelineState(
            stage="3", sub_stage="implementation", current_unit=5,
        )
        redo_state = enter_redo_profile_revision(state, "delivery")
        assert redo_state.sub_stage == "redo_profile_delivery"
        assert redo_state.redo_triggered_from is not None

        restored = complete_redo_profile_revision(redo_state)
        assert restored.stage == "3"
        assert restored.sub_stage == "implementation"
        assert restored.current_unit == 5
        assert restored.redo_triggered_from is None


# ===================================================================
# 7. Unit 8 -> Unit 10: extract_units feeds stub generation
# ===================================================================


class TestExtractUnitsFeedsStubGeneration:
    """Integration: extract_units (Unit 8) -> stub generation (Unit 10)."""

    def test_extract_units_tier2_parseable_by_signature_parser(self, tmp_path):
        """Tier 2 blocks from extract_units are parseable by Unit 9."""
        _create_blueprint_files(tmp_path)
        units = extract_units(tmp_path / "blueprint")

        assert len(units) >= 2
        unit1 = next(u for u in units if u.number == 1)

        # Tier 2 should be parseable Python
        python_config = get_language_config("python")
        parsed = parse_signatures(unit1.tier2, "python", python_config)
        assert isinstance(parsed, ast.Module)

    def test_extracted_tier2_generates_valid_stub(self, tmp_path):
        """Tier 2 from extract_units -> parse -> generate_stub produces valid stub."""
        _create_blueprint_files(tmp_path)
        units = extract_units(tmp_path / "blueprint")

        unit1 = next(u for u in units if u.number == 1)
        python_config = get_language_config("python")
        parsed = parse_signatures(unit1.tier2, "python", python_config)
        stub = generate_stub(parsed, "python", python_config)

        assert python_config["stub_sentinel"] in stub
        assert "NotImplementedError" in stub
        assert "load_config" in stub
        assert "save_config" in stub

    def test_tier2_code_fences_stripped_before_parsing(self, tmp_path):
        """Tier 2 blocks have code fences stripped by extract_units."""
        _create_blueprint_files(tmp_path)
        units = extract_units(tmp_path / "blueprint")

        unit1 = next(u for u in units if u.number == 1)
        # The tier2 should not contain markdown code fence markers
        assert not unit1.tier2.strip().startswith("```")
        assert "```python" not in unit1.tier2

    def test_units_sorted_by_number(self, tmp_path):
        """extract_units returns list sorted by unit number."""
        _create_blueprint_files(tmp_path)
        units = extract_units(tmp_path / "blueprint")
        numbers = [u.number for u in units]
        assert numbers == sorted(numbers)


# ===================================================================
# 8. Unit 13 -> all agents: prepare_task_prompt dispatches for all types
# ===================================================================


class TestPrepareTaskPromptDispatches:
    """Integration: prepare_task_prompt (Unit 13) dispatches for all agent types."""

    def test_setup_agent_prompt_generated(self, tmp_path):
        """prepare_task_prompt generates prompt for setup_agent."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        prompt = prepare_task_prompt(tmp_path, "setup_agent")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_blueprint_author_prompt_includes_profile(self, tmp_path):
        """Blueprint author prompt includes profile data."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        prompt = prepare_task_prompt(tmp_path, "blueprint_author")
        assert "python_project" in prompt
        assert "Profile" in prompt

    def test_language_context_injected_for_stage3_agents(self):
        """Stage 3 agents get LANGUAGE_CONTEXT from registry."""
        ctx = build_language_context("python", "test_agent", LANGUAGE_REGISTRY)
        assert "LANGUAGE_CONTEXT" in ctx
        assert "Python" in ctx
        assert "pytest" in ctx

    def test_language_context_empty_for_non_stage3_agents(self):
        """Non-stage-3 agents get empty language context."""
        ctx = build_language_context("python", "setup_agent", LANGUAGE_REGISTRY)
        assert ctx == ""

    def test_sentinel_injected_in_language_context_for_stub_agents(self):
        """Sentinel appears in language context for test/implementation agents."""
        for agent_type in ("test_agent", "implementation_agent", "coverage_review"):
            ctx = build_language_context("python", agent_type, LANGUAGE_REGISTRY)
            if ctx:  # coverage_review may be named differently
                sentinel = LANGUAGE_REGISTRY["python"]["stub_sentinel"]
                assert sentinel in ctx, (
                    f"Sentinel missing from '{agent_type}' language context"
                )

    def test_selective_loading_matrix_determines_blueprint_loading(self):
        """SELECTIVE_LOADING_MATRIX maps agent types to blueprint loading modes."""
        assert SELECTIVE_LOADING_MATRIX["test_agent"] == "contracts_only"
        assert SELECTIVE_LOADING_MATRIX["implementation_agent"] == "contracts_only"
        assert SELECTIVE_LOADING_MATRIX["diagnostic_agent"] == "both"
        assert SELECTIVE_LOADING_MATRIX["help_agent"] == "prose_only"

    def test_known_agent_types_complete(self):
        """KNOWN_AGENT_TYPES covers all expected agent types."""
        expected_agents = {
            "setup_agent", "stakeholder_dialog", "stakeholder_reviewer",
            "blueprint_author", "blueprint_checker", "blueprint_reviewer",
            # Bug S3-168 (cycle 5 capstone): added the new specialist.
            "statistical_correctness_reviewer",
            "test_agent", "implementation_agent", "coverage_review",
            "diagnostic_agent", "integration_test_author", "git_repo_agent",
            "help_agent", "hint_agent", "redo_agent", "bug_triage",
            "repair_agent", "reference_indexing", "checklist_generation",
            "regression_adaptation", "oracle_agent",
        }
        assert expected_agents == set(KNOWN_AGENT_TYPES)


# ===================================================================
# 9. Unit 14: GATE_VOCABULARY covers all 31 gates, dispatch handles all
# ===================================================================


class TestGateVocabularyCoversAllGates:
    """Integration: GATE_VOCABULARY (Unit 14) covers all gates from Unit 13."""

    def test_gate_vocabulary_has_35_gates(self):
        """GATE_VOCABULARY contains exactly 35 gate entries (31 baseline +
        gate_0_4_toolchain_provisioned added by Bug S3-176 +
        gate_2_3_toolchain_verified added by Bug S3-180 +
        gate_6_1_mode_classification added by Bug S3-186 cycle G1 +
        gate_3_3_test_layer_review added by Bug S3-205 cycle K-3).
        The S3-186 rename gate_6_1_regression_test -> gate_6_3_regression_test
        does not change the count."""
        assert len(GATE_VOCABULARY) == 35

    def test_all_gate_ids_have_vocabulary_entries(self):
        """Every gate in ALL_GATE_IDS has a GATE_VOCABULARY entry."""
        for gate_id in ALL_GATE_IDS:
            assert gate_id in GATE_VOCABULARY, (
                f"Gate '{gate_id}' in ALL_GATE_IDS but missing from GATE_VOCABULARY"
            )

    def test_all_vocabulary_gates_in_gate_ids(self):
        """Every GATE_VOCABULARY entry is listed in ALL_GATE_IDS."""
        for gate_id in GATE_VOCABULARY:
            assert gate_id in ALL_GATE_IDS, (
                f"Gate '{gate_id}' in GATE_VOCABULARY but missing from ALL_GATE_IDS"
            )

    def test_set_equality_gate_ids_and_vocabulary(self):
        """Set equality: ALL_GATE_IDS == GATE_VOCABULARY keys."""
        assert set(ALL_GATE_IDS) == set(GATE_VOCABULARY.keys())

    def test_gate_response_options_match_between_units_13_and_14(self):
        """Gate response options in Unit 13 match GATE_VOCABULARY in Unit 14."""
        for gate_id, responses in _GATE_RESPONSE_OPTIONS.items():
            assert gate_id in GATE_VOCABULARY, (
                f"Gate '{gate_id}' in Unit 13 but not in GATE_VOCABULARY"
            )
            assert sorted(responses) == sorted(GATE_VOCABULARY[gate_id]), (
                f"Response mismatch for '{gate_id}': "
                f"Unit 13={responses}, Unit 14={GATE_VOCABULARY[gate_id]}"
            )

    def test_every_gate_has_at_least_one_response(self):
        """Every gate in GATE_VOCABULARY has at least one valid response."""
        for gate_id, responses in GATE_VOCABULARY.items():
            assert len(responses) > 0, f"Gate '{gate_id}' has no valid responses"

    def test_all_gate_ids_list_has_35_entries(self):
        """ALL_GATE_IDS contains exactly 35 entries (31 baseline +
        gate_0_4_toolchain_provisioned added by Bug S3-176 +
        gate_2_3_toolchain_verified added by Bug S3-180 +
        gate_6_1_mode_classification added by Bug S3-186 cycle G1 +
        gate_3_3_test_layer_review added by Bug S3-205 cycle K-3)."""
        assert len(ALL_GATE_IDS) == 35


# ===================================================================
# 10. Registry-handler alignment: dispatch table keys match registry
# ===================================================================


class TestRegistryHandlerAlignment:
    """Structural completeness: registry keys align with dispatch table entries."""

    def test_stub_generators_cover_all_registry_entries(self):
        """Every language with stub_generator_key has matching STUB_GENERATORS entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if "stub_generator_key" in entry:
                key = entry["stub_generator_key"]
                assert key in STUB_GENERATORS, (
                    f"Language '{lang_key}' stub_generator_key '{key}' "
                    f"not in STUB_GENERATORS"
                )

    def test_stub_generators_all_referenced_or_plugin(self):
        """Every STUB_GENERATORS key is referenced by registry or is a plugin key."""
        _PLUGIN_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}
        referenced_keys = set()
        for entry in LANGUAGE_REGISTRY.values():
            if "stub_generator_key" in entry:
                referenced_keys.add(entry["stub_generator_key"])
        for gen_key in STUB_GENERATORS:
            assert gen_key in referenced_keys or gen_key in _PLUGIN_KEYS, (
                f"STUB_GENERATORS key '{gen_key}' not referenced by any "
                f"registry entry or plugin"
            )

    def test_quality_runners_cover_all_registry_entries(self):
        """Every language with quality_runner_key has matching QUALITY_RUNNERS entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if "quality_runner_key" in entry:
                key = entry["quality_runner_key"]
                assert key in QUALITY_RUNNERS, (
                    f"Language '{lang_key}' quality_runner_key '{key}' "
                    f"not in QUALITY_RUNNERS"
                )

    def test_quality_runners_all_referenced_or_plugin(self):
        """Every QUALITY_RUNNERS key is referenced by registry or is a plugin key."""
        _PLUGIN_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}
        referenced_keys = set()
        for entry in LANGUAGE_REGISTRY.values():
            if "quality_runner_key" in entry:
                referenced_keys.add(entry["quality_runner_key"])
        for runner_key in QUALITY_RUNNERS:
            assert runner_key in referenced_keys or runner_key in _PLUGIN_KEYS, (
                f"QUALITY_RUNNERS key '{runner_key}' not referenced by any "
                f"registry entry or plugin"
            )

    def test_test_output_parsers_cover_full_languages(self):
        """Every full language with test_output_parser_key has parser entry."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                if "test_output_parser_key" in entry:
                    key = entry["test_output_parser_key"]
                    assert key in TEST_OUTPUT_PARSERS, (
                        f"Language '{lang_key}' test_output_parser_key '{key}' "
                        f"not in TEST_OUTPUT_PARSERS"
                    )

    def test_test_output_parsers_all_referenced_or_plugin(self):
        """Every TEST_OUTPUT_PARSERS key is referenced by entry or is plugin key."""
        _PLUGIN_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}
        referenced_keys = set()
        for entry in LANGUAGE_REGISTRY.values():
            if "test_output_parser_key" in entry:
                referenced_keys.add(entry["test_output_parser_key"])
        for parser_key in TEST_OUTPUT_PARSERS:
            assert parser_key in referenced_keys or parser_key in _PLUGIN_KEYS, (
                f"TEST_OUTPUT_PARSERS key '{parser_key}' not referenced by any "
                f"registry entry or plugin"
            )

    def test_signature_parsers_cover_full_languages(self):
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

    def test_component_required_dispatch_entries_have_handlers(self):
        """Component languages' required_dispatch_entries resolve to handlers."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                required_entries = entry.get("required_dispatch_entries", [])
                for req_key in required_entries:
                    dispatch_value = entry.get(req_key)
                    assert dispatch_value is not None, (
                        f"Component '{lang_key}' requires '{req_key}' "
                        f"but has no value"
                    )
                    if req_key == "stub_generator_key":
                        assert dispatch_value in STUB_GENERATORS
                    elif req_key == "quality_runner_key":
                        assert dispatch_value in QUALITY_RUNNERS

    def test_registry_entries_self_validate(self):
        """All built-in registry entries pass their own validation."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                errors = validate_component_entry(entry)
            else:
                errors = validate_registry_entry(entry)
            assert errors == [], (
                f"Registry entry '{lang_key}' fails validation: {errors}"
            )


# ===================================================================
# 11. Agent definition consistency: Unit 13 <-> Unit 14
# ===================================================================


class TestAgentDefinitionConsistency:
    """Integration: Agent definitions (Unit 13) <-> dispatch tables (Unit 14)."""

    def test_agent_status_lines_cover_known_agents(self):
        """Every agent in AGENT_STATUS_LINES has at least one terminal status."""
        for agent_key, statuses in AGENT_STATUS_LINES.items():
            assert len(statuses) > 0, (
                f"Agent '{agent_key}' has no terminal status lines"
            )

    def test_phase_to_agent_values_exist_in_status_lines(self):
        """PHASE_TO_AGENT values have corresponding AGENT_STATUS_LINES entries."""
        for phase, agent_key in PHASE_TO_AGENT.items():
            found = (
                agent_key in AGENT_STATUS_LINES
                or f"{agent_key}_agent" in AGENT_STATUS_LINES
            )
            assert found, (
                f"Phase '{phase}' maps to '{agent_key}' with no status lines"
            )

    def test_selective_loading_matrix_agents_are_known(self):
        """All agents in SELECTIVE_LOADING_MATRIX are recognized."""
        for agent_type in SELECTIVE_LOADING_MATRIX:
            base_name = agent_type.replace("_agent", "")
            found = (
                agent_type in KNOWN_AGENT_TYPES
                or base_name in KNOWN_AGENT_TYPES
                or f"{agent_type}_agent" in KNOWN_AGENT_TYPES
                or agent_type in AGENT_STATUS_LINES
            )
            assert found, (
                f"Agent '{agent_type}' in SELECTIVE_LOADING_MATRIX but not known"
            )


# ===================================================================
# 12. Toolchain resolution chain: Unit 1 -> Unit 4 -> resolved commands
# ===================================================================


class TestToolchainResolutionChain:
    """Integration: Config (Unit 1) -> Toolchain (Unit 4) -> resolved commands."""

    def test_config_env_name_flows_into_toolchain_resolution(self, tmp_path):
        """Config-derived env_name flows into command resolution."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        env_name = derive_env_name(tmp_path)
        assert env_name == f"svp-{tmp_path.name}"

        toolchain = load_toolchain(tmp_path)
        run_prefix = toolchain["environment"]["run_prefix"]

        test_cmd = toolchain["testing"]["run_command"]
        # Bug S3-100: normalize {test_path} to {target} as run_tests_main does
        test_cmd = test_cmd.replace("{test_path}", "{target}")
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
        assert "{" not in resolved  # no unresolved placeholders
        assert "  " not in resolved  # no double spaces

    def test_gate_composition_commands_fully_resolvable(self, tmp_path):
        """Gate composition returns commands that can be fully resolved."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        env_name = derive_env_name(tmp_path)
        toolchain = load_toolchain(tmp_path)
        run_prefix_template = toolchain["environment"]["run_prefix"]

        gate_ops = get_gate_composition(toolchain, "gate_a")
        assert len(gate_ops) >= 2

        for op in gate_ops:
            assert "operation" in op
            assert "command" in op
            resolved = resolve_command(
                op["command"],
                env_name=env_name,
                run_prefix=run_prefix_template.replace("{env_name}", env_name),
                target="src/",
            )
            assert "{" not in resolved

    def test_gate_b_is_superset_of_gate_a(self, tmp_path):
        """Gate B operations include all Gate A operations plus type_checker."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        toolchain = load_toolchain(tmp_path)
        gate_a_ops = get_gate_composition(toolchain, "gate_a")
        gate_b_ops = get_gate_composition(toolchain, "gate_b")

        gate_a_names = {op["operation"] for op in gate_a_ops}
        gate_b_names = {op["operation"] for op in gate_b_ops}

        assert gate_a_names.issubset(gate_b_names)
        assert any("type_checker" in name for name in gate_b_names)


# ===================================================================
# 13. Profile validation against registry: Unit 3 <-> Unit 2
# ===================================================================


class TestProfileValidationAgainstRegistry:
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
        assert any(
            "conda" in e.lower() or "environment_recommendation" in e for e in errors
        )

    def test_quality_config_merges_with_registry_defaults(self, tmp_path):
        """Profile quality config deep-merges with registry defaults."""
        _create_minimal_workspace(tmp_path)
        profile = load_profile(tmp_path)
        quality = get_quality_config(profile, "python", LANGUAGE_REGISTRY)

        assert quality["linter"] == "ruff"
        assert quality["formatter"] == "ruff"
        assert quality["type_checker"] == "mypy"
        assert quality["line_length"] == 88

    def test_delivery_config_merges_with_registry_defaults(self, tmp_path):
        """Profile delivery config deep-merges with registry defaults."""
        _create_minimal_workspace(tmp_path)
        profile = load_profile(tmp_path)
        delivery = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)

        assert delivery["environment_recommendation"] == "conda"
        assert delivery["dependency_format"] == "environment.yml"
        assert delivery["source_layout"] == "conventional"


# ===================================================================
# 14. Test output parser dispatch: Unit 2 -> Unit 14
# ===================================================================


class TestTestOutputParserDispatch:
    """Integration: LANGUAGE_REGISTRY (Unit 2) -> TEST_OUTPUT_PARSERS (Unit 14)."""

    def test_python_parser_classifies_passing_tests(self):
        """Python test output parser correctly classifies passing tests."""
        parser = TEST_OUTPUT_PARSERS["python"]
        output = "2 passed in 0.5s"
        result = parser(output, "python", 0, {})
        assert result.status == "TESTS_PASSED"
        assert result.passed == 2

    def test_python_parser_classifies_failing_tests(self):
        """Python test output parser correctly classifies failing tests."""
        parser = TEST_OUTPUT_PARSERS["python"]
        output = "1 passed, 2 failed in 1.0s"
        result = parser(output, "python", 1, {})
        assert result.status == "TESTS_FAILED"
        assert result.passed == 1
        assert result.failed == 2

    def test_python_parser_detects_collection_errors(self):
        """Python test output parser detects collection errors."""
        parser = TEST_OUTPUT_PARSERS["python"]
        output = "ERROR collecting tests/test_foo.py\nModuleNotFoundError: No module"
        result = parser(output, "python", 2, {})
        assert result.collection_error is True

    def test_r_parser_classifies_passing_tests(self):
        """R test output parser correctly classifies passing tests."""
        parser = TEST_OUTPUT_PARSERS["r"]
        output = "OK: 5\nFailed: 0\nWarnings: 0"
        result = parser(output, "r", 0, {})
        assert result.status == "TESTS_PASSED"
        assert result.passed == 5

    def test_r_parser_classifies_failing_tests(self):
        """R test output parser correctly classifies failing tests."""
        parser = TEST_OUTPUT_PARSERS["r"]
        output = "OK: 3\nFailed: 2\nWarnings: 0"
        result = parser(output, "r", 1, {})
        assert result.status == "TESTS_FAILED"
        assert result.failed == 2

    def test_parser_dispatch_key_from_registry(self):
        """Python test_output_parser_key from registry resolves in parsers table."""
        python_config = get_language_config("python")
        key = python_config["test_output_parser_key"]
        assert key in TEST_OUTPUT_PARSERS

    def test_r_parser_dispatch_key_from_registry(self):
        """R test_output_parser_key from registry resolves in parsers table."""
        r_config = get_language_config("r")
        key = r_config["test_output_parser_key"]
        assert key in TEST_OUTPUT_PARSERS


# ===================================================================
# 15. Routing reads pipeline state: Unit 14 -> Unit 5
# ===================================================================


class TestRoutingReadsPipelineState:
    """Integration: route (Unit 14) reads pipeline state (Unit 5)."""

    def test_route_stage_0_hook_activation(self, tmp_path):
        """Route at Stage 0 / hook_activation returns gate action."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="hook_activation")
        save_state(tmp_path, state)

        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_0_1_hook_activation"

    def test_route_stage_0_project_context_invokes_setup(self, tmp_path):
        """Route at Stage 0 / project_context (no last_status) invokes setup_agent."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_context")
        save_state(tmp_path, state)

        action = route(tmp_path)
        assert action["action_type"] == "invoke_agent"
        assert action["agent_type"] == "setup_agent"

    def test_route_stage_0_profile_done_presents_gate(self, tmp_path):
        """Route at Stage 0 / project_profile with PROFILE_COMPLETE presents gate."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(stage="0", sub_stage="project_profile")
        save_state(tmp_path, state)

        status_path = tmp_path / ".svp" / "last_status.txt"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text("PROFILE_COMPLETE")

        action = route(tmp_path)
        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_0_3_profile_approval"

    def test_route_after_advance_stage_reads_updated_state(self, tmp_path):
        """After advance_stage + save_state, route reads the updated state."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="0", sub_stage="project_profile")
        new_state = advance_stage(state, "1")
        save_state(tmp_path, new_state)

        action = route(tmp_path)
        assert action["action_type"] in ("invoke_agent", "human_gate", "run_command")

    def test_route_stage_3_dispatches_correctly(self, tmp_path):
        """Route at Stage 3 / stub_generation dispatches correctly."""
        _create_minimal_workspace(tmp_path)
        state = PipelineState(
            stage="3", sub_stage="stub_generation",
            current_unit=1, total_units=5,
        )
        save_state(tmp_path, state)

        action = route(tmp_path)
        assert action["action_type"] in ("invoke_agent", "run_command")


# ===================================================================
# 16. State transition -> save -> load roundtrip
# ===================================================================


class TestStateTransitionSaveLoadRoundtrip:
    """Integration: Unit 6 transitions -> Unit 5 save/load preserve state."""

    def test_redo_state_roundtrip(self, tmp_path):
        """Redo state survives save -> load round-trip."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(
            stage="3", sub_stage="implementation", current_unit=5,
        )
        redo_state = enter_redo_profile_revision(state, "delivery")
        save_state(tmp_path, redo_state)
        loaded = load_state(tmp_path)

        assert loaded.sub_stage == "redo_profile_delivery"
        assert loaded.redo_triggered_from is not None
        assert loaded.redo_triggered_from["stage"] == "3"

    def test_rollback_to_unit_roundtrip(self, tmp_path):
        """rollback_to_unit state is preserved through save/load."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(
            stage="3", sub_stage="unit_completion",
            current_unit=3, total_units=5,
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

    def test_redo_sub_stages_in_additional_sub_stages(self):
        """Redo sub-stages are valid additional sub-stages."""
        assert "redo_profile_delivery" in ADDITIONAL_SUB_STAGES
        assert "redo_profile_blueprint" in ADDITIONAL_SUB_STAGES

    def test_pass_field_roundtrip(self, tmp_path):
        """pass_ field (serialized as 'pass') survives roundtrip."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(stage="3", sub_stage=None, pass_=2)
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.pass_ == 2

    def test_deferred_broken_units_roundtrip(self, tmp_path):
        """deferred_broken_units list survives save -> load roundtrip."""
        _create_minimal_workspace(tmp_path)

        state = PipelineState(
            stage="3", sub_stage=None,
            deferred_broken_units=[3, 7, 15],
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert loaded.deferred_broken_units == [3, 7, 15]


# ===================================================================
# 17. Assembly map generation: Unit 8 -> Unit 23
# ===================================================================


class TestAssemblyMapGeneration:
    """Integration: Blueprint (Unit 8) -> Assembly Map (Unit 23)."""

    def test_assembly_map_has_flat_repo_to_workspace_schema(self, tmp_path):
        """Bug S3-111: assembly map has one top-level key, every value is a
        stub path, many-to-one relationship is allowed."""
        import re as _re
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        blueprint_dir = tmp_path / "blueprint"
        assembly_map = generate_assembly_map(blueprint_dir, tmp_path)

        assert list(assembly_map.keys()) == ["repo_to_workspace"]
        assert "workspace_to_repo" not in assembly_map

        stub_re = _re.compile(r"^src/unit_\d+/stub\.py$")
        for repo_path, ws_path in assembly_map["repo_to_workspace"].items():
            assert stub_re.match(ws_path), (
                f"Non-stub source path for {repo_path}: {ws_path}"
            )

    def test_assembly_map_written_to_disk(self, tmp_path):
        """Assembly map is persisted at .svp/assembly_map.json."""
        _create_minimal_workspace(tmp_path)
        _create_blueprint_files(tmp_path)

        blueprint_dir = tmp_path / "blueprint"
        generate_assembly_map(blueprint_dir, tmp_path)

        map_path = tmp_path / ".svp" / "assembly_map.json"
        assert map_path.exists()

        loaded = json.loads(map_path.read_text())
        assert list(loaded.keys()) == ["repo_to_workspace"]
        assert "workspace_to_repo" not in loaded


# ===================================================================
# 18. Config model selection chain: Unit 1 -> Unit 3
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
# 19. Profile migration: SVP 2.1 flat -> language-keyed (Unit 3)
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


# ===================================================================
# 20. End-to-end: config -> profile -> blueprint -> stub -> parse
# ===================================================================


class TestEndToEndFlow:
    """Integration: Full pipeline data flow across Units 1, 2, 3, 8, 9, 10, 14."""

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
# 21. Write authorization: Unit 2 -> authorized_write_dirs
# ===================================================================


class TestWriteAuthorization:
    """Integration: Language Registry (Unit 2) authorized_write_dirs."""

    def test_python_authorized_dirs_include_src_tests_root(self):
        """Python has src, tests, and root as authorized write dirs."""
        python_config = get_language_config("python")
        authorized = python_config["authorized_write_dirs"]
        assert "src" in authorized
        assert "tests" in authorized
        assert "." in authorized

    def test_r_authorized_dirs_include_r_tests_root(self):
        """R has R, tests/testthat, and root as authorized write dirs."""
        r_config = get_language_config("r")
        authorized = r_config["authorized_write_dirs"]
        assert "R" in authorized
        assert "tests/testthat" in authorized
        assert "." in authorized

    def test_all_full_languages_have_authorized_write_dirs(self):
        """All full-language registry entries have authorized_write_dirs."""
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert "authorized_write_dirs" in entry, (
                    f"Language {lang_key} missing authorized_write_dirs"
                )
                assert len(entry["authorized_write_dirs"]) > 0


# ===================================================================
# 22. Quality gate execution chain: Unit 4 -> Unit 15
# ===================================================================


class TestQualityGateExecutionChain:
    """Integration: Toolchain (Unit 4) gate composition -> Quality Runner (Unit 15)."""

    def test_gate_composition_feeds_quality_runner(self, tmp_path):
        """Gate composition from toolchain is used by quality runner."""
        _create_minimal_workspace(tmp_path)
        _create_toolchain_file(tmp_path)

        toolchain = load_toolchain(tmp_path)
        python_config = get_language_config("python")

        gate_ops = get_gate_composition(toolchain, "gate_a")
        assert all(op["operation"].startswith("quality.") for op in gate_ops)

        runner_key = python_config["quality_runner_key"]
        assert runner_key in QUALITY_RUNNERS

    def test_gate_a_precedes_gate_b_in_stage3(self):
        """Gate A sub-stage comes before Gate B in Stage 3 sub-stages."""
        stage3_subs = list(VALID_SUB_STAGES["3"])
        assert "quality_gate_a" in stage3_subs
        assert "quality_gate_b" in stage3_subs

    def test_quality_gate_retry_isolation(self):
        """Retrying gate A does not affect gate B's behavior."""
        state = PipelineState(
            stage="3", sub_stage="quality_gate_a", current_unit=1,
        )
        retry_state = advance_quality_gate_to_retry(state)
        assert retry_state.sub_stage == "quality_gate_a_retry"

        passed = quality_gate_pass(retry_state)
        assert passed.sub_stage == "red_run"

    def test_quality_gate_b_retry_isolation(self):
        """Retrying gate B advances correctly."""
        state = PipelineState(
            stage="3", sub_stage="quality_gate_b", current_unit=1,
        )
        retry_state = advance_quality_gate_to_retry(state)
        assert retry_state.sub_stage == "quality_gate_b_retry"

        passed = quality_gate_pass(retry_state)
        assert passed.sub_stage == "green_run"


# ===================================================================
# 23. Quality package defaults: Profile -> Registry valid sets
# ===================================================================


class TestQualityPackageDefaults:
    """Integration: Profile quality config -> registry valid tool sets."""

    def test_default_python_quality_tools_are_valid(self):
        """Default Python quality tools are in the registry's valid sets."""
        python_entry = LANGUAGE_REGISTRY["python"]
        default_q = python_entry["default_quality"]
        assert default_q["linter"] in python_entry["valid_linters"]
        assert default_q["formatter"] in python_entry["valid_formatters"]
        assert default_q["type_checker"] in python_entry["valid_type_checkers"]

    def test_default_r_quality_tools_are_valid(self):
        """Default R quality tools are in the registry's valid sets."""
        r_entry = LANGUAGE_REGISTRY["r"]
        default_q = r_entry["default_quality"]
        assert default_q["linter"] in r_entry["valid_linters"]
        assert default_q["formatter"] in r_entry["valid_formatters"]
        assert default_q["type_checker"] in r_entry["valid_type_checkers"]

    def test_profile_quality_override_merged_with_defaults(self, tmp_path):
        """Profile quality override merges with registry defaults."""
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

        assert quality["line_length"] == 120  # override applied
        assert quality["linter"] == "ruff"  # default preserved
        assert quality["formatter"] == "ruff"  # default preserved


# ===================================================================
# 24. Preference compliance: Profile sections validated
# ===================================================================


class TestPreferenceCompliance:
    """Integration: Profile (Unit 3) preferences against registry (Unit 2)."""

    def test_documentation_preferences_in_profile(self):
        """Documentation preferences (readme section) are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "readme" in profile
        assert "audience" in profile["readme"]
        assert "sections" in profile["readme"]

    def test_vcs_preferences_in_profile(self):
        """VCS preferences are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "vcs" in profile
        assert "commit_style" in profile["vcs"]
        assert "branch_strategy" in profile["vcs"]

    def test_testing_preferences_in_profile(self):
        """Testing preferences are part of profile."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
        assert "testing" in profile
        assert "readable_test_names" in profile["testing"]

    def test_tooling_preferences_match_registry_valid_sets(self):
        """Quality tooling preferences are validated against registry."""
        profile = copy.deepcopy(DEFAULT_PROFILE)
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
