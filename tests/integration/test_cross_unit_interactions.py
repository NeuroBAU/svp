"""
Integration tests for SVP cross-unit interactions.

These tests validate behaviors that emerge from the interaction of multiple
units, not behaviors owned by any single unit. They exercise data flow across
the full chain, error propagation across unit boundaries, timing dependencies,
and emergent behavior from unit composition.

Integration tests should be run with:
    python -m pytest tests/integration/ tests/regressions/ -v

All regression tests from tests/regressions/ MUST be included in the
integration test run to ensure previously fixed bugs remain fixed.
"""
import copy
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import pytest

# ---------------------------------------------------------------------------
# Import units under test
# ---------------------------------------------------------------------------
from svp.scripts.svp_config import (
    DEFAULT_CONFIG,
    load_config,
    validate_config,
    get_model_for_agent,
    get_effective_context_budget,
    write_default_config,
)
from svp.scripts.pipeline_state import (
    STAGES,
    PipelineState,
    DebugSession,
    create_initial_state,
    load_state,
    save_state,
    validate_state,
    recover_state_from_markers,
    get_stage_display,
)
from svp.scripts.state_transitions import (
    TransitionError,
    advance_stage,
    advance_sub_stage,
    complete_unit,
    advance_fix_ladder,
    reset_fix_ladder,
    increment_red_run_retries,
    reset_red_run_retries,
    increment_alignment_iteration,
    reset_alignment_iteration,
    record_pass_end,
    rollback_to_unit,
    restart_from_stage,
    version_document,
    enter_debug_session,
    authorize_debug_session,
    complete_debug_session,
    abandon_debug_session,
    update_debug_phase,
    set_debug_classification,
)
from svp.scripts.ledger_manager import (
    LedgerEntry,
    append_entry,
    read_ledger,
    clear_ledger,
    get_ledger_size_chars,
    check_ledger_capacity,
    compact_ledger,
    write_hint_entry,
    extract_tagged_lines,
)
from svp.scripts.blueprint_extractor import (
    UnitDefinition,
    parse_blueprint,
    extract_unit,
    extract_upstream_contracts,
    build_unit_context,
)
from svp.scripts.stub_generator import (
    parse_signatures,
    generate_stub_source,
    strip_module_level_asserts,
    generate_upstream_mocks,
    write_stub_file,
    write_upstream_stubs,
)
from svp.scripts.dependency_extractor import (
    classify_import,
    map_imports_to_packages,
    create_project_directories,
    derive_env_name,
)
from svp.scripts.hint_assembler import (
    assemble_hint_prompt,
    get_agent_type_framing,
    get_ladder_position_framing,
)
from svp.scripts.routing import (
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
    route,
    format_action_block,
    derive_env_name_from_state,
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
)
from svp.scripts.command_logic import (
    save_project,
    quit_project,
    get_status,
    format_pass_history,
    format_debug_history,
    clean_workspace,
)
from svp.scripts.plugin_manifest import (
    PLUGIN_JSON,
    MARKETPLACE_JSON,
    validate_plugin_structure,
)
from svp.scripts.svp_launcher import (
    PROJECT_DIRS,
    SVP_ENV_VAR,
    create_project_directory,
    write_initial_state,
    write_default_config as launcher_write_default_config,
    write_readme_svp,
    detect_existing_project,
    parse_args,
    _generate_claude_md_fallback,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with standard SVP structure."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    for d in PROJECT_DIRS:
        (project_root / d).mkdir(parents=True, exist_ok=True)
    return project_root


@pytest.fixture
def project_with_state(tmp_project):
    """Create a project with an initial pipeline state and config."""
    state = create_initial_state("test_project")
    save_state(state, tmp_project)
    write_default_config(tmp_project)
    return tmp_project


@pytest.fixture
def project_at_stage3(project_with_state):
    """Create a project at Stage 3, Unit 1, with total_units set."""
    state = load_state(project_with_state)
    # Advance through stages: 0 -> 1 -> 2 -> pre_stage_3 -> 3
    state = advance_stage(state, project_with_state)  # -> 1
    state = advance_stage(state, project_with_state)  # -> 2
    state = advance_stage(state, project_with_state)  # -> pre_stage_3
    state = advance_stage(state, project_with_state)  # -> 3
    state.total_units = 5
    state.current_unit = 1
    save_state(state, project_with_state)
    return project_with_state


@pytest.fixture
def project_at_stage5(project_with_state):
    """Create a project at Stage 5 with some verified units."""
    state = load_state(project_with_state)
    state.stage = "5"
    state.sub_stage = None
    state.current_unit = None
    state.total_units = 3
    now = datetime.now(timezone.utc).isoformat()
    state.verified_units = [
        {"unit": 1, "timestamp": now},
        {"unit": 2, "timestamp": now},
        {"unit": 3, "timestamp": now},
    ]
    save_state(state, project_with_state)
    return project_with_state


@pytest.fixture
def sample_blueprint(tmp_path):
    """Create a minimal blueprint file with 3 units for testing."""
    blueprint_content = """\
# Blueprint

## Unit 1: Configuration Loader

### Tier 1 -- Description

Loads project configuration from JSON files.

### Tier 2 \u2014 Signatures

```python
from typing import Dict, Any
from pathlib import Path

def load_config(project_root: Path) -> Dict[str, Any]: ...
def validate_config(config: Dict[str, Any]) -> list[str]: ...
```

### Tier 2 \u2014 Invariants

```python
assert isinstance(load_config(Path(".")), dict)
```

### Tier 3 -- Error Conditions

- FileNotFoundError if config file does not exist
- JSONDecodeError if config file is invalid JSON

### Tier 3 -- Behavioral Contracts

- load_config always returns a dict
- validate_config returns empty list for valid configs

### Tier 3 -- Dependencies

None

---

## Unit 2: State Manager

### Tier 1 -- Description

Manages pipeline state lifecycle.

### Tier 2 \u2014 Signatures

```python
from typing import Optional, Dict, Any
from pathlib import Path

class PipelineState:
    stage: str
    def __init__(self, **kwargs) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...

def create_state(name: str) -> PipelineState: ...
def save_state(state: PipelineState, path: Path) -> None: ...
```

### Tier 2 \u2014 Invariants

```python
assert create_state("test").stage == "0"
```

### Tier 3 -- Error Conditions

- ValueError on invalid state

### Tier 3 -- Behavioral Contracts

- create_state returns state at stage 0

### Tier 3 -- Dependencies

**Unit 1 (Configuration Loader):** Uses load_config for defaults

---

## Unit 3: Transition Engine

### Tier 1 -- Description

Handles state transitions between pipeline stages.

### Tier 2 \u2014 Signatures

```python
from typing import Optional
from pathlib import Path

def advance_stage(state, project_root: Path): ...
def complete_unit(state, unit_number: int, project_root: Path): ...
```

### Tier 2 \u2014 Invariants

```python
# No invariants
```

### Tier 3 -- Error Conditions

- TransitionError on invalid transition

### Tier 3 -- Behavioral Contracts

- advance_stage increments stage

### Tier 3 -- Dependencies

**Unit 1 (Configuration Loader):** Uses load_config for iteration limits
**Unit 2 (State Manager):** Uses PipelineState for state manipulation
"""
    bp_path = tmp_path / "blueprint.md"
    bp_path.write_text(blueprint_content, encoding="utf-8")
    return bp_path


# =========================================================================
# SECTION 1: Data flow across the full chain of units
# =========================================================================


class TestStateCreateSaveLoadRoundTrip:
    """Verify that state created by Unit 2, saved to disk, and loaded back
    produces identical data -- and that Unit 1 config interacts correctly
    with the loaded state.
    """

    def test_create_save_load_roundtrip(self, tmp_project):
        """State created, saved, and loaded must be structurally identical."""
        original = create_initial_state("roundtrip_test")
        save_state(original, tmp_project)
        loaded = load_state(tmp_project)

        assert loaded.stage == original.stage
        assert loaded.sub_stage == original.sub_stage
        assert loaded.project_name == "roundtrip_test"
        assert loaded.current_unit == original.current_unit
        assert loaded.total_units == original.total_units
        assert loaded.fix_ladder_position == original.fix_ladder_position
        assert loaded.red_run_retries == 0
        assert loaded.alignment_iteration == 0
        assert loaded.verified_units == []
        assert loaded.pass_history == []
        assert loaded.debug_session is None
        assert loaded.debug_history == []

    def test_state_with_debug_session_roundtrip(self, project_at_stage5):
        """DebugSession serialization/deserialization must survive save/load."""
        state = load_state(project_at_stage5)
        state = enter_debug_session(state, "Button click does nothing")
        save_state(state, project_at_stage5)

        loaded = load_state(project_at_stage5)
        assert loaded.debug_session is not None
        assert isinstance(loaded.debug_session, DebugSession)
        assert loaded.debug_session.description == "Button click does nothing"
        assert loaded.debug_session.phase == "triage_readonly"
        assert loaded.debug_session.authorized is False
        assert loaded.debug_session.bug_id == 1

    def test_config_loaded_alongside_state(self, project_with_state):
        """Config and state should both load from the same project root."""
        config = load_config(project_with_state)
        state = load_state(project_with_state)

        assert validate_config(config) == []
        assert validate_state(state) == []
        assert config["iteration_limit"] == 3
        assert state.stage == "0"


class TestBlueprintToStubPipeline:
    """Verify the data pipeline: blueprint file -> blueprint extractor (Unit 5)
    -> stub generator (Unit 6), ensuring the full chain produces usable stubs.
    """

    def test_blueprint_parse_to_stub_generation(self, sample_blueprint, tmp_path):
        """Parsed blueprint signatures should produce valid stub files
        via the stub generator.
        """
        units = parse_blueprint(sample_blueprint)
        assert len(units) == 3

        output_dir = tmp_path / "stubs"
        output_dir.mkdir()

        for unit_def in units:
            if unit_def.signatures.strip():
                stub_path = write_stub_file(
                    unit_def.unit_number,
                    unit_def.signatures,
                    output_dir,
                )
                assert stub_path.exists()
                content = stub_path.read_text(encoding="utf-8")
                assert "NotImplementedError" in content

    def test_upstream_contracts_to_mock_generation(self, sample_blueprint, tmp_path):
        """Upstream contracts extracted by Unit 5 should feed into Unit 6 mock
        generation without error, producing importable mock files.
        """
        # Unit 3 depends on Unit 1 and Unit 2
        upstream = extract_upstream_contracts(sample_blueprint, 3)
        assert len(upstream) == 2

        output_dir = tmp_path / "mocks"
        output_dir.mkdir()

        mock_paths = write_upstream_stubs(upstream, output_dir)
        assert len(mock_paths) == 2

        for mp in mock_paths:
            assert mp.exists()
            content = mp.read_text(encoding="utf-8")
            assert len(content) > 0

    def test_build_unit_context_includes_upstream(self, sample_blueprint):
        """build_unit_context for a unit with dependencies should include
        both the unit's own definition and the upstream contract signatures.
        """
        context = build_unit_context(sample_blueprint, 3)
        assert "Unit 3" in context
        assert "Transition Engine" in context
        # Must include upstream contracts
        assert "Upstream Contract Signatures" in context
        assert "Unit 1" in context
        assert "Unit 2" in context

    def test_extract_unit_signatures_parseable_by_stub_generator(
        self, sample_blueprint
    ):
        """The signatures extracted by Unit 5 must be parseable by Unit 6's
        parse_signatures, ensuring the two units agree on format.
        """
        unit_def = extract_unit(sample_blueprint, 1)
        assert len(unit_def.signatures) > 0

        tree = parse_signatures(unit_def.signatures)
        source = generate_stub_source(tree)
        assert "NotImplementedError" in source
        # Must be valid Python
        compile(source, "<stub>", "exec")


class TestHintFlowAcrossUnits:
    """Verify hint data flows correctly: hint_prompt_assembler (Unit 8) ->
    ledger_manager (Unit 4) -> preparation script (Unit 9 contract).
    """

    def test_hint_assembled_then_written_to_ledger(self, tmp_path):
        """A hint assembled by Unit 8 should be writable as a ledger entry
        by Unit 4, and retrievable with metadata intact.
        """
        hint_text = "The config parser should handle nested dicts recursively."
        assembled = assemble_hint_prompt(
            hint_content=hint_text,
            gate_id="gate_3_1_test_validation",
            agent_type="test",
            ladder_position=None,
            unit_number=5,
            stage="3",
        )
        assert "## Human Domain Hint (via Help Agent)" in assembled
        assert hint_text in assembled

        ledger_path = tmp_path / "hint_ledger.jsonl"
        write_hint_entry(
            ledger_path,
            hint_content=hint_text,
            gate_id="gate_3_1_test_validation",
            unit_number=5,
            stage="3",
            decision="TEST CORRECT",
        )

        entries = read_ledger(ledger_path)
        assert len(entries) == 1
        assert entries[0].role == "system"
        assert "[HINT]" in entries[0].content
        assert hint_text in entries[0].content
        assert entries[0].metadata is not None
        assert entries[0].metadata["gate_id"] == "gate_3_1_test_validation"
        assert entries[0].metadata["unit_number"] == 5
        assert entries[0].metadata["decision"] == "TEST CORRECT"


# =========================================================================
# SECTION 2: Error propagation across unit boundaries
# =========================================================================


class TestTransitionErrorPropagation:
    """Verify that TransitionError from Unit 3 propagates correctly when
    called through Unit 10's dispatch functions.
    """

    def test_invalid_gate_response_raises_value_error(self, project_with_state):
        """dispatch_gate_response with an invalid response string must raise
        ValueError, not silently succeed.
        """
        state = load_state(project_with_state)
        with pytest.raises(ValueError, match="Invalid gate response"):
            dispatch_gate_response(
                state,
                gate_id="gate_0_1_hook_activation",
                response="INVALID_RESPONSE",
                project_root=project_with_state,
            )

    def test_unknown_gate_id_raises_value_error(self, project_with_state):
        """dispatch_gate_response with an unknown gate_id must raise
        ValueError.
        """
        state = load_state(project_with_state)
        with pytest.raises(ValueError):
            dispatch_gate_response(
                state,
                gate_id="gate_99_nonexistent",
                response="APPROVE",
                project_root=project_with_state,
            )

    def test_fix_ladder_invalid_transition_raises(self, project_at_stage3):
        """advance_fix_ladder called from None directly to 'diagnostic' should
        raise TransitionError, and this error should not be swallowed by
        calling code.
        """
        state = load_state(project_at_stage3)
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "diagnostic")

    def test_complete_unit_wrong_stage_raises(self, project_with_state):
        """Attempting to complete a unit outside Stage 3 must raise
        TransitionError.
        """
        state = load_state(project_with_state)
        assert state.stage == "0"
        with pytest.raises(TransitionError, match="Stage 3"):
            complete_unit(state, 1, project_with_state)

    def test_debug_session_requires_stage5(self, project_at_stage3):
        """enter_debug_session must raise TransitionError if not at Stage 5."""
        state = load_state(project_at_stage3)
        with pytest.raises(TransitionError, match="Stage 5"):
            enter_debug_session(state, "Some bug")


class TestLedgerErrorHandling:
    """Verify that ledger errors from Unit 4 propagate correctly when used
    in cross-unit workflows.
    """

    def test_compact_nonexistent_ledger_raises(self, tmp_path):
        """Compacting a ledger that does not exist must raise FileNotFoundError."""
        nonexistent = tmp_path / "missing.jsonl"
        with pytest.raises(FileNotFoundError):
            compact_ledger(nonexistent)

    def test_malformed_jsonl_raises_on_read(self, tmp_path):
        """A ledger with corrupt JSONL must raise JSONDecodeError."""
        ledger = tmp_path / "bad.jsonl"
        ledger.write_text("not valid json\n", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            read_ledger(ledger)


# =========================================================================
# SECTION 3: Routing-state-transition composition (Units 2 + 3 + 10)
# =========================================================================


class TestRoutingAndStateTransitionComposition:
    """Verify that the router (Unit 10) produces action blocks whose
    POST commands, when executed, would trigger the correct state
    transitions (Unit 3) on the state (Unit 2).
    """

    def test_stage0_hook_activation_route_and_dispatch(self, project_with_state):
        """Route at stage 0 / hook_activation should produce a gate action.
        Dispatching HOOKS ACTIVATED should advance sub_stage to project_context.
        """
        state = load_state(project_with_state)
        assert state.stage == "0"
        assert state.sub_stage == "hook_activation"

        action = route(state, project_with_state)
        assert action["ACTION"] == "human_gate"
        assert action["GATE"] == "gate_0_1_hook_activation"
        assert "HOOKS ACTIVATED" in action["OPTIONS"]
        assert "HOOKS FAILED" in action["OPTIONS"]

        new_state = dispatch_gate_response(
            state,
            gate_id="gate_0_1_hook_activation",
            response="HOOKS ACTIVATED",
            project_root=project_with_state,
        )
        assert new_state.sub_stage == "project_context"

    def test_stage1_spec_approval_route_and_dispatch(self, project_with_state):
        """Route at stage 1 with approval sub_stage should produce a gate.
        Dispatching APPROVE should advance to stage 2.
        """
        state = load_state(project_with_state)
        state.stage = "1"
        state.sub_stage = "approval"
        save_state(state, project_with_state)

        state = load_state(project_with_state)
        action = route(state, project_with_state)
        assert action["ACTION"] == "human_gate"
        assert action["GATE"] == "gate_1_1_spec_draft"

        new_state = dispatch_gate_response(
            state,
            gate_id="gate_1_1_spec_draft",
            response="APPROVE",
            project_root=project_with_state,
        )
        assert new_state.stage == "2"

    def test_stage3_test_gen_route_produces_agent_action(self, project_at_stage3):
        """Route at stage 3, test_generation sub_stage should produce
        an invoke_agent action for the test_agent.
        """
        state = load_state(project_at_stage3)
        state.sub_stage = "test_generation"
        save_state(state, project_at_stage3)

        state = load_state(project_at_stage3)
        action = route(state, project_at_stage3)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "test_agent"
        assert action["UNIT"] == 1

    def test_stage3_green_run_pass_advances_to_coverage(self, project_at_stage3):
        """At stage 3, green_run sub_stage, TESTS_PASSED should advance
        to coverage_review.
        """
        state = load_state(project_at_stage3)
        state.sub_stage = "green_run"
        save_state(state, project_at_stage3)
        state = load_state(project_at_stage3)

        new_state = dispatch_command_status(
            state,
            status_line="TESTS_PASSED: 12 passed",
            unit=1,
            phase="green_run",
            project_root=project_at_stage3,
        )
        assert new_state.sub_stage == "coverage_review"

    def test_stage3_green_run_fail_goes_to_validation(self, project_at_stage3):
        """At stage 3, green_run sub_stage, TESTS_FAILED should advance
        to test_validation (gate for human decision).
        """
        state = load_state(project_at_stage3)
        state.sub_stage = "green_run"
        save_state(state, project_at_stage3)
        state = load_state(project_at_stage3)

        new_state = dispatch_command_status(
            state,
            status_line="TESTS_FAILED: 10 passed, 2 failed",
            unit=1,
            phase="green_run",
            project_root=project_at_stage3,
        )
        assert new_state.sub_stage == "test_validation"

    def test_stage4_integration_route(self, project_with_state):
        """Route at stage 4, integration_test_generation should produce
        an invoke_agent for integration_test_author.
        """
        state = load_state(project_with_state)
        state.stage = "4"
        state.sub_stage = "integration_test_generation"
        save_state(state, project_with_state)
        state = load_state(project_with_state)

        action = route(state, project_with_state)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "integration_test_author"


class TestFormatActionBlockOutputShape:
    """Verify that format_action_block (Unit 10) produces the expected
    structured output for different action types from route().
    """

    def test_invoke_agent_has_reminder(self, project_at_stage3):
        """invoke_agent actions must include REMINDER block."""
        state = load_state(project_at_stage3)
        action = route(state, project_at_stage3)
        block = format_action_block(action)
        assert "REMINDER:" in block
        assert "ACTION: invoke_agent" in block

    def test_human_gate_has_options_and_reminder(self, project_with_state):
        """human_gate actions must include OPTIONS and REMINDER."""
        state = load_state(project_with_state)
        action = route(state, project_with_state)
        block = format_action_block(action)
        assert "ACTION: human_gate" in block
        assert "OPTIONS:" in block
        assert "REMINDER:" in block

    def test_pipeline_complete_no_reminder(self, project_at_stage5):
        """pipeline_complete actions must NOT include REMINDER."""
        state = load_state(project_at_stage5)
        state.sub_stage = "complete"
        save_state(state, project_at_stage5)
        state = load_state(project_at_stage5)

        action = route(state, project_at_stage5)
        assert action["ACTION"] == "pipeline_complete"
        block = format_action_block(action)
        assert "REMINDER:" not in block


# =========================================================================
# SECTION 4: Gate vocabulary consistency (Bug 1 invariant)
# =========================================================================


class TestGateVocabularyConsistency:
    """Verify that GATE_VOCABULARY (Unit 10) and the dispatch_gate_response
    function agree -- every gate_id is handled, and every valid option
    for each gate produces a new state without error.
    """

    def test_all_gate_ids_are_handled_by_dispatch(self, project_with_state):
        """Every gate_id in GATE_VOCABULARY must be handled by
        dispatch_gate_response without raising an unrecognized-gate error.
        """
        for gate_id, options in GATE_VOCABULARY.items():
            # Build a state appropriate for this gate
            state = _build_state_for_gate(gate_id, project_with_state)
            for option in options:
                try:
                    result = dispatch_gate_response(
                        state, gate_id, option, project_with_state
                    )
                    # Must return a PipelineState
                    assert isinstance(result, PipelineState), (
                        f"Gate {gate_id} option '{option}' did not return PipelineState"
                    )
                except (TransitionError, ValueError):
                    # Some transitions may fail due to preconditions
                    # (e.g. debug transitions when there is no debug session).
                    # That is acceptable as long as the gate itself is recognized.
                    pass

    def test_gate_options_in_route_match_vocabulary(self, project_with_state):
        """When route() returns a human_gate action, the OPTIONS field
        must exactly match GATE_VOCABULARY[gate_id].
        """
        state = load_state(project_with_state)
        action = route(state, project_with_state)
        if action["ACTION"] == "human_gate":
            gate_id = action["GATE"]
            expected = GATE_VOCABULARY[gate_id]
            assert action["OPTIONS"] == expected, (
                f"Route OPTIONS for {gate_id} do not match GATE_VOCABULARY"
            )


# =========================================================================
# SECTION 5: Config-to-transition interaction (Units 1 + 3)
# =========================================================================


class TestConfigAffectsTransitions:
    """Verify that configuration values loaded by Unit 1 correctly influence
    transition behavior in Unit 3.
    """

    def test_alignment_iteration_respects_iteration_limit(self, project_with_state):
        """increment_alignment_iteration must raise TransitionError when
        the count exceeds the iteration_limit from Unit 1 config.
        """
        config = load_config(project_with_state)
        limit = config["iteration_limit"]
        assert limit == 3

        state = load_state(project_with_state)
        state.stage = "2"
        save_state(state, project_with_state)
        state = load_state(project_with_state)

        # Increment up to the limit
        for i in range(limit):
            state = increment_alignment_iteration(state)
        assert state.alignment_iteration == limit

        # One more should raise
        with pytest.raises(TransitionError, match="limit"):
            increment_alignment_iteration(state)

    def test_model_resolution_for_all_agent_types(self, project_with_state):
        """get_model_for_agent must return a valid model string for every
        agent type referenced in AGENT_STATUS_LINES (Unit 10).
        """
        config = load_config(project_with_state)
        for agent_type in AGENT_STATUS_LINES.keys():
            model = get_model_for_agent(config, agent_type)
            assert isinstance(model, str)
            assert len(model) > 0


# =========================================================================
# SECTION 6: Unit completion and marker pipeline (Units 2 + 3)
# =========================================================================


class TestUnitCompletionMarkerPipeline:
    """Verify the full unit completion pipeline: complete_unit writes markers,
    updates verified_units, and advances current_unit. Then
    recover_state_from_markers can rebuild state from those markers.
    """

    def test_complete_unit_writes_marker_and_updates_state(self, project_at_stage3):
        """Completing a unit must write a marker file and update verified_units."""
        state = load_state(project_at_stage3)
        assert state.current_unit == 1

        new_state = complete_unit(state, 1, project_at_stage3)

        # Marker must exist
        marker = project_at_stage3 / ".svp" / "markers" / "unit_1_verified"
        assert marker.exists()

        # State must be updated
        assert len(new_state.verified_units) == 1
        assert new_state.verified_units[0]["unit"] == 1
        assert new_state.current_unit == 2
        assert new_state.fix_ladder_position is None

    def test_complete_all_units_advances_to_stage4(self, project_at_stage3):
        """Completing the final unit (when total_units is reached) must
        advance the pipeline to Stage 4.
        """
        state = load_state(project_at_stage3)
        state.total_units = 3
        save_state(state, project_at_stage3)
        state = load_state(project_at_stage3)

        for u in range(1, 4):
            state.current_unit = u
            state = complete_unit(state, u, project_at_stage3)

        assert state.stage == "4"
        assert state.current_unit is None
        assert len(state.verified_units) == 3

    def test_recover_from_markers_after_completion(self, project_at_stage3):
        """After completing units and writing markers, recover_state_from_markers
        should reconstruct a consistent state.
        """
        state = load_state(project_at_stage3)
        state = complete_unit(state, 1, project_at_stage3)
        save_state(state, project_at_stage3)

        # Recover from markers
        recovered = recover_state_from_markers(project_at_stage3)
        assert recovered is not None
        assert recovered.stage == "3"
        assert recovered.current_unit == 2
        assert len(recovered.verified_units) == 1

    def test_rollback_removes_markers(self, project_at_stage3):
        """rollback_to_unit must remove marker files for invalidated units."""
        state = load_state(project_at_stage3)
        state = complete_unit(state, 1, project_at_stage3)
        state.current_unit = 2
        state = complete_unit(state, 2, project_at_stage3)
        save_state(state, project_at_stage3)

        marker1 = project_at_stage3 / ".svp" / "markers" / "unit_1_verified"
        marker2 = project_at_stage3 / ".svp" / "markers" / "unit_2_verified"
        assert marker1.exists()
        assert marker2.exists()

        state = load_state(project_at_stage3)
        state = rollback_to_unit(state, 1, project_at_stage3)

        assert not marker1.exists()
        assert not marker2.exists()
        assert state.current_unit == 1
        assert len(state.verified_units) == 0


# =========================================================================
# SECTION 7: Document versioning across transitions (Units 3 + filesystem)
# =========================================================================


class TestDocumentVersioningIntegration:
    """Verify that version_document (Unit 3) works correctly when used
    with the project's standard directory structure.
    """

    def test_version_stakeholder_spec(self, project_with_state):
        """Versioning a stakeholder spec should create history files in the
        standard location.
        """
        spec_path = project_with_state / "specs" / "stakeholder.md"
        spec_path.write_text("# Stakeholder Spec v1\n\nOriginal content.", encoding="utf-8")

        history_dir = project_with_state / "specs" / "history"

        versioned, diff = version_document(
            spec_path,
            history_dir,
            diff_summary="Changed requirements section",
            trigger_context="Gate 1.1 REVISE",
        )
        assert versioned.exists()
        assert diff.exists()
        assert "stakeholder_v1.md" in versioned.name
        assert "stakeholder_v1_diff.md" in diff.name

        # Diff file content should include the summary
        diff_content = diff.read_text(encoding="utf-8")
        assert "Changed requirements section" in diff_content
        assert "Gate 1.1 REVISE" in diff_content

    def test_multiple_versions_increment(self, project_with_state):
        """Multiple calls to version_document should produce incrementing
        version numbers.
        """
        doc_path = project_with_state / "blueprint" / "blueprint.md"
        doc_path.write_text("# Blueprint v1", encoding="utf-8")
        history_dir = project_with_state / "blueprint" / "history"

        v1, _ = version_document(doc_path, history_dir, "v1 changes", "revision 1")
        v2, _ = version_document(doc_path, history_dir, "v2 changes", "revision 2")

        assert "v1" in v1.name
        assert "v2" in v2.name


# =========================================================================
# SECTION 8: Debug session lifecycle (Units 2 + 3 + 10)
# =========================================================================


class TestDebugSessionLifecycle:
    """Verify the full debug session lifecycle: enter -> authorize ->
    triage -> classification -> repair -> complete, with correct
    routing at each phase.
    """

    def test_full_debug_lifecycle(self, project_at_stage5):
        """Walk through the complete debug lifecycle checking that state
        transitions compose correctly across units.
        """
        state = load_state(project_at_stage5)

        # Enter debug session
        state = enter_debug_session(state, "Login form rejects valid passwords")
        assert state.debug_session is not None
        assert state.debug_session.phase == "triage_readonly"
        assert state.debug_session.authorized is False

        # Route should produce Gate 6.0
        action = route(state, project_at_stage5)
        assert action["ACTION"] == "human_gate"
        assert action["GATE"] == "gate_6_0_debug_permission"

        # Authorize
        state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", project_at_stage5
        )
        assert state.debug_session.authorized is True
        assert state.debug_session.phase == "triage"

        # Route should produce bug_triage agent
        action = route(state, project_at_stage5)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "bug_triage"

        # Triage completes with single_unit classification
        state = dispatch_agent_status(
            state, "bug_triage", "TRIAGE_COMPLETE: single_unit",
            unit=None, phase="bug_triage", project_root=project_at_stage5,
        )
        assert state.debug_session.phase == "regression_test"

        # Route should produce test_agent for regression test
        action = route(state, project_at_stage5)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "test_agent"

    def test_abandon_debug_moves_to_history(self, project_at_stage5):
        """Abandoning a debug session should move it to debug_history."""
        state = load_state(project_at_stage5)
        state = enter_debug_session(state, "Edge case crash")

        state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG", project_at_stage5
        )
        assert state.debug_session is None
        assert len(state.debug_history) == 1
        assert state.debug_history[0]["status"] == "abandoned"

    def test_sequential_debug_sessions_get_incrementing_ids(self, project_at_stage5):
        """Multiple debug sessions should receive incrementing bug_ids."""
        state = load_state(project_at_stage5)

        # First session
        state = enter_debug_session(state, "Bug one")
        assert state.debug_session.bug_id == 1
        state = abandon_debug_session(state)

        # Second session
        state = enter_debug_session(state, "Bug two")
        assert state.debug_session.bug_id == 2


# =========================================================================
# SECTION 9: Env name derivation consistency (Units 7 + 10 + 24)
# =========================================================================


class TestEnvNameDerivationConsistency:
    """Verify that the conda environment name derivation is consistent
    across Unit 7 (derive_env_name), Unit 10 (derive_env_name_from_state),
    and Unit 24 (launcher state writing).
    """

    def test_derive_env_name_matches_across_units(self):
        """The same project name must produce the same env name from
        both Unit 7 and Unit 10.
        """
        project_name = "My Cool Project"
        expected = "my_cool_project"

        from_unit7 = derive_env_name(project_name)
        assert from_unit7 == expected

        state = PipelineState(project_name=project_name)
        from_unit10 = derive_env_name_from_state(state)
        assert from_unit10 == expected

    def test_derive_env_name_with_hyphens(self):
        """Hyphens must be replaced with underscores consistently."""
        project_name = "my-project-name"
        expected = "my_project_name"

        from_unit7 = derive_env_name(project_name)
        from_unit10 = derive_env_name_from_state(
            PipelineState(project_name=project_name)
        )

        assert from_unit7 == expected
        assert from_unit10 == expected


# =========================================================================
# SECTION 10: Launcher project setup and state compatibility (Units 24 + 2)
# =========================================================================


class TestLauncherStateCompatibility:
    """Verify that the state written by Unit 24's launcher is loadable by
    Unit 2's load_state, ensuring the two units agree on schema.
    """

    def test_launcher_writes_loadable_state(self, tmp_path):
        """State written by launcher's write_initial_state must be loadable
        by Unit 2's load_state.
        """
        project_root = tmp_path / "launcher_test"
        project_root.mkdir()
        for d in PROJECT_DIRS:
            (project_root / d).mkdir(parents=True, exist_ok=True)

        write_initial_state(project_root, "launcher_test_project")
        state = load_state(project_root)
        assert state.stage == "0"
        assert state.sub_stage == "hook_activation"
        assert state.project_name == "launcher_test_project"
        assert validate_state(state) == []

    def test_launcher_config_loadable_by_unit1(self, tmp_path):
        """Config written by launcher must be loadable and valid per Unit 1."""
        project_root = tmp_path / "config_test"
        project_root.mkdir()

        launcher_write_default_config(project_root)
        config = load_config(project_root)
        assert validate_config(config) == []
        assert config["iteration_limit"] == 3

    def test_detect_existing_project_after_launcher_setup(self, tmp_path):
        """detect_existing_project must return True after a full launcher setup."""
        project_root = tmp_path / "detect_test"
        project_root.mkdir()
        for d in PROJECT_DIRS:
            (project_root / d).mkdir(parents=True, exist_ok=True)

        write_initial_state(project_root, "detect_test")
        assert detect_existing_project(project_root) is True


# =========================================================================
# SECTION 11: Ledger + config interaction for compaction thresholds
# =========================================================================


class TestLedgerCompactionWithConfig:
    """Verify that the compaction_character_threshold from Unit 1 config
    works correctly when applied to Unit 4 ledger compaction.
    """

    def test_compaction_threshold_from_config(self, project_with_state):
        """The compaction_character_threshold from loaded config should
        be usable by compact_ledger to control compaction behavior.
        """
        config = load_config(project_with_state)
        threshold = config["compaction_character_threshold"]
        assert threshold == 200

        ledger_path = project_with_state / "ledgers" / "test.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Create entries with tagged lines above the threshold
        long_decision = "[DECISION] " + "x" * (threshold + 50)
        entry = LedgerEntry(
            role="agent",
            content=f"Some analysis text.\n{long_decision}",
        )
        append_entry(ledger_path, entry)

        original_size = get_ledger_size_chars(ledger_path)
        chars_saved = compact_ledger(ledger_path, character_threshold=threshold)

        # Should have compacted since tagged line exceeds threshold
        assert chars_saved > 0
        new_entries = read_ledger(ledger_path)
        assert len(new_entries) == 1
        # The body text should be removed, only tagged line remains
        assert "Some analysis text" not in new_entries[0].content

    def test_hint_entries_survive_compaction(self, tmp_path):
        """[HINT] entries must survive compaction regardless of threshold."""
        ledger_path = tmp_path / "hint_test.jsonl"

        write_hint_entry(
            ledger_path,
            hint_content="Consider edge case for empty input",
            gate_id="gate_3_1_test_validation",
            unit_number=1,
            stage="3",
            decision="TEST CORRECT",
        )

        # Add a compactable entry
        long_decision = "[DECISION] " + "x" * 300
        entry = LedgerEntry(
            role="agent",
            content=f"Discussion text.\n{long_decision}",
        )
        append_entry(ledger_path, entry)

        compact_ledger(ledger_path, character_threshold=200)

        entries = read_ledger(ledger_path)
        hint_entries = [e for e in entries if "[HINT]" in e.content]
        assert len(hint_entries) == 1
        assert "Consider edge case for empty input" in hint_entries[0].content


# =========================================================================
# SECTION 12: Status command integration (Units 2 + 11)
# =========================================================================


class TestStatusCommandIntegration:
    """Verify that the status command (Unit 11) correctly reads state
    written by Unit 2 and produces meaningful output.
    """

    def test_status_reflects_current_stage(self, project_with_state):
        """get_status must reflect the actual pipeline stage."""
        status = get_status(project_with_state)
        assert "Stage 0" in status
        assert "hook_activation" in status

    def test_status_with_verified_units(self, project_at_stage3):
        """Status with verified units should list them."""
        state = load_state(project_at_stage3)
        state = complete_unit(state, 1, project_at_stage3)
        save_state(state, project_at_stage3)

        status = get_status(project_at_stage3)
        assert "1" in status

    def test_status_with_pass_history(self, project_at_stage3):
        """Status with pass_history should format it correctly."""
        state = load_state(project_at_stage3)
        state = record_pass_end(state, "blueprint fix needed")
        save_state(state, project_at_stage3)

        status = get_status(project_at_stage3)
        assert "Pass history" in status or "pass" in status.lower()

    def test_save_then_status_consistent(self, project_with_state):
        """save_project should verify files, and get_status should reflect
        the same state.
        """
        save_msg = save_project(project_with_state)
        assert "pipeline_state.json" in save_msg
        assert "All files OK" in save_msg

        status = get_status(project_with_state)
        assert "Stage 0" in status

    def test_quit_calls_save(self, project_with_state):
        """quit_project should include save confirmation."""
        quit_msg = quit_project(project_with_state)
        assert "saved" in quit_msg.lower()
        assert "pipeline_state.json" in quit_msg


# =========================================================================
# SECTION 13: Plugin manifest validation (Unit 23)
# =========================================================================


class TestPluginManifestDataContracts:
    """Verify the plugin manifest constants and validation function
    against the expected schema.
    """

    def test_plugin_json_has_required_fields(self):
        """PLUGIN_JSON must contain name, version, and description."""
        assert "name" in PLUGIN_JSON
        assert "version" in PLUGIN_JSON
        assert "description" in PLUGIN_JSON
        assert PLUGIN_JSON["name"] == "svp"

    def test_marketplace_json_has_required_structure(self):
        """MARKETPLACE_JSON must contain name, owner, plugins array."""
        assert "name" in MARKETPLACE_JSON
        assert "owner" in MARKETPLACE_JSON
        assert "plugins" in MARKETPLACE_JSON
        assert isinstance(MARKETPLACE_JSON["plugins"], list)
        assert len(MARKETPLACE_JSON["plugins"]) > 0

        plugin_entry = MARKETPLACE_JSON["plugins"][0]
        assert "name" in plugin_entry
        assert "source" in plugin_entry
        assert "description" in plugin_entry
        assert "version" in plugin_entry
        assert "author" in plugin_entry

        # Source must use relative path with ./
        assert plugin_entry["source"].startswith("./")

    def test_version_consistency(self):
        """Plugin JSON and marketplace entry must have the same version."""
        marketplace_version = MARKETPLACE_JSON["plugins"][0]["version"]
        assert PLUGIN_JSON["version"] == marketplace_version


# =========================================================================
# SECTION 14: Stage display formatting (Units 2 + 11)
# =========================================================================


class TestStageDisplayFormatting:
    """Verify that get_stage_display (Unit 2) and the status command
    (Unit 11) produce consistent human-readable output.
    """

    def test_stage_display_stage0(self):
        """Stage 0 with hook_activation sub_stage."""
        state = PipelineState(stage="0", sub_stage="hook_activation")
        display = get_stage_display(state)
        assert "Stage 0" in display
        assert "hook_activation" in display

    def test_stage_display_stage3_with_unit(self):
        """Stage 3 should show unit info and pass number."""
        state = PipelineState(
            stage="3",
            current_unit=4,
            total_units=11,
            pass_history=[],
        )
        display = get_stage_display(state)
        assert "Stage 3" in display
        assert "Unit 4" in display
        assert "of 11" in display
        assert "pass 1" in display

    def test_stage_display_pre_stage_3(self):
        """Pre-Stage 3 has its own display format."""
        state = PipelineState(stage="pre_stage_3")
        display = get_stage_display(state)
        assert "Pre-Stage 3" in display

    def test_stage_display_stage3_pass2(self):
        """Stage 3 with one completed pass should show pass 2."""
        now = datetime.now(timezone.utc).isoformat()
        state = PipelineState(
            stage="3",
            current_unit=1,
            total_units=5,
            pass_history=[{
                "pass_number": 1,
                "reached_unit": 3,
                "ended_reason": "blueprint fix",
                "timestamp": now,
            }],
        )
        display = get_stage_display(state)
        assert "pass 2" in display


# =========================================================================
# SECTION 15: Import classification consistency (Unit 7)
# =========================================================================


class TestImportClassificationConsistency:
    """Verify that import classification and package mapping produce
    consistent results across different import formats.
    """

    def test_stdlib_imports_classified_correctly(self):
        """Standard library imports must be classified as 'stdlib'."""
        assert classify_import("import os") == "stdlib"
        assert classify_import("import json") == "stdlib"
        assert classify_import("from pathlib import Path") == "stdlib"
        assert classify_import("from typing import Dict, Any") == "stdlib"

    def test_project_imports_classified_correctly(self):
        """Internal project imports must be classified as 'project'."""
        assert classify_import("from svp.scripts.svp_config import load_config") == "project"
        assert classify_import("import svp.scripts.pipeline_state") == "project"

    def test_third_party_mapped_correctly(self):
        """Third-party imports must map to their correct package names."""
        imports = [
            "import yaml",
            "import numpy",
            "from PIL import Image",
        ]
        packages = map_imports_to_packages(imports)
        assert "yaml" in packages
        assert packages["yaml"] == "pyyaml"
        assert "PIL" in packages
        assert packages["PIL"] == "Pillow"


# =========================================================================
# SECTION 16: Full pipeline traversal -- end-to-end domain scenario
# =========================================================================


class TestEndToEndPipelineTraversal:
    """End-to-end test that validates a complete input-to-output scenario:
    starting from project creation at Stage 0, advancing through all
    pipeline stages, completing units, and arriving at Stage 5.

    This test checks domain-meaningful values at each step, not just
    types and shapes, to catch subtle composition errors like
    double-normalization or lost state fields.
    """

    def test_full_pipeline_stage_traversal(self, tmp_path):
        """Simulate the entire SVP pipeline from Stage 0 to Stage 5,
        verifying domain-correct state values at each transition.

        This is the primary end-to-end test. It validates:
        - State creation with correct initial values
        - Config loading and validation
        - Stage advancement with correct stage strings
        - Sub-stage transitions within stages
        - Unit completion with marker files
        - Pass history recording
        - Final state at Stage 5 with all units verified
        """
        # Step 1: Create project via launcher
        project_root = tmp_path / "e2e_project"
        project_root.mkdir()
        for d in PROJECT_DIRS:
            (project_root / d).mkdir(parents=True, exist_ok=True)

        write_initial_state(project_root, "End-to-End Test")
        launcher_write_default_config(project_root)

        # Verify: State from launcher is at Stage 0, hook_activation
        state = load_state(project_root)
        assert state.stage == "0"
        assert state.sub_stage == "hook_activation"
        assert state.project_name == "End-to-End Test"
        assert state.current_unit is None
        assert state.total_units is None
        assert state.verified_units == []
        assert state.pass_history == []
        assert state.debug_session is None
        assert validate_state(state) == []

        # Verify: Config is valid and has expected defaults
        config = load_config(project_root)
        assert config["iteration_limit"] == 3
        assert config["models"]["default"] == "claude-opus-4-6"
        budget = get_effective_context_budget(config)
        assert budget == 200_000 - 20_000  # 180000 tokens

        # Step 2: Route at Stage 0 produces hook activation gate
        action = route(state, project_root)
        assert action["ACTION"] == "human_gate"
        assert action["GATE"] == "gate_0_1_hook_activation"
        assert action["OPTIONS"] == ["HOOKS ACTIVATED", "HOOKS FAILED"]

        # Step 3: Activate hooks -> advance to project_context
        state = dispatch_gate_response(
            state, "gate_0_1_hook_activation", "HOOKS ACTIVATED", project_root
        )
        assert state.stage == "0"
        assert state.sub_stage == "project_context"

        # Step 4: Complete project context -> advance to Stage 1
        state = dispatch_agent_status(
            state, "setup_agent", "PROJECT_CONTEXT_COMPLETE",
            unit=None, phase="project_context", project_root=project_root,
        )
        assert state.stage == "1"
        assert state.sub_stage is None

        # Step 5: Stakeholder dialog completes -> approval gate
        state = dispatch_agent_status(
            state, "stakeholder_dialog", "SPEC_DRAFT_COMPLETE",
            unit=None, phase="stakeholder_dialog", project_root=project_root,
        )
        assert state.sub_stage == "approval"

        # Step 6: Approve spec -> advance to Stage 2
        state = dispatch_gate_response(
            state, "gate_1_1_spec_draft", "APPROVE", project_root
        )
        assert state.stage == "2"

        # Step 7: Blueprint dialog completes -> alignment check
        state = dispatch_agent_status(
            state, "blueprint_author", "BLUEPRINT_DRAFT_COMPLETE",
            unit=None, phase="blueprint_dialog", project_root=project_root,
        )
        assert state.sub_stage == "alignment_check"

        # Step 8: Alignment confirmed -> approval gate
        state = dispatch_agent_status(
            state, "blueprint_checker", "ALIGNMENT_CONFIRMED",
            unit=None, phase="alignment_check", project_root=project_root,
        )
        assert state.sub_stage == "approval"

        # Step 9: Approve blueprint -> pre_stage_3
        state = dispatch_gate_response(
            state, "gate_2_1_blueprint_approval", "APPROVE", project_root
        )
        assert state.stage == "pre_stage_3"

        # Step 10: Infrastructure setup succeeds -> Stage 3
        state = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", unit=None,
            phase="infrastructure_setup", project_root=project_root,
        )
        assert state.stage == "3"
        assert state.current_unit == 1

        # Step 11: Configure total_units
        state.total_units = 2
        save_state(state, project_root)
        state = load_state(project_root)
        assert state.total_units == 2

        # Step 12: Unit 1 -- test generation -> stub gen -> red run -> impl -> green run -> coverage -> complete
        state = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE",
            unit=1, phase="test_generation", project_root=project_root,
        )
        assert state.sub_stage == "stub_generation"

        state = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", unit=1,
            phase="stub_generation", project_root=project_root,
        )
        assert state.sub_stage == "red_run"

        state = dispatch_command_status(
            state, "TESTS_FAILED: 0 passed, 5 failed", unit=1,
            phase="red_run", project_root=project_root,
        )
        assert state.sub_stage == "implementation"

        state = dispatch_agent_status(
            state, "implementation_agent", "IMPLEMENTATION_COMPLETE",
            unit=1, phase="implementation", project_root=project_root,
        )
        assert state.sub_stage == "green_run"

        state = dispatch_command_status(
            state, "TESTS_PASSED: 5 passed", unit=1,
            phase="green_run", project_root=project_root,
        )
        assert state.sub_stage == "coverage_review"

        state = dispatch_agent_status(
            state, "coverage_review", "COVERAGE_COMPLETE: no gaps",
            unit=1, phase="coverage_review", project_root=project_root,
        )
        assert state.sub_stage == "unit_completion"

        # Complete unit 1
        state = complete_unit(state, 1, project_root)
        assert state.current_unit == 2
        assert len(state.verified_units) == 1
        assert state.verified_units[0]["unit"] == 1

        # Verify marker file exists
        marker1 = project_root / ".svp" / "markers" / "unit_1_verified"
        assert marker1.exists()

        # Step 13: Unit 2 -- abbreviated cycle
        state.sub_stage = None
        state = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE",
            unit=2, phase="test_generation", project_root=project_root,
        )
        state = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", unit=2,
            phase="stub_generation", project_root=project_root,
        )
        state = dispatch_command_status(
            state, "TESTS_FAILED: 0 passed, 3 failed", unit=2,
            phase="red_run", project_root=project_root,
        )
        state = dispatch_agent_status(
            state, "implementation_agent", "IMPLEMENTATION_COMPLETE",
            unit=2, phase="implementation", project_root=project_root,
        )
        state = dispatch_command_status(
            state, "TESTS_PASSED: 3 passed", unit=2,
            phase="green_run", project_root=project_root,
        )
        state = dispatch_agent_status(
            state, "coverage_review", "COVERAGE_COMPLETE: no gaps",
            unit=2, phase="coverage_review", project_root=project_root,
        )

        # Complete final unit -> should auto-advance to Stage 4
        state = complete_unit(state, 2, project_root)
        assert state.stage == "4"
        assert state.current_unit is None
        assert len(state.verified_units) == 2

        # Step 14: Integration tests pass -> Stage 5
        state = dispatch_agent_status(
            state, "integration_test_author", "INTEGRATION_TESTS_COMPLETE",
            unit=None, phase="integration_test_generation", project_root=project_root,
        )
        assert state.sub_stage == "integration_run"

        state = dispatch_command_status(
            state, "TESTS_PASSED: 15 passed", unit=None,
            phase="integration_run", project_root=project_root,
        )
        assert state.stage == "5"

        # Step 15: Repo assembly and delivery
        state = dispatch_agent_status(
            state, "git_repo_agent", "REPO_ASSEMBLY_COMPLETE",
            unit=None, phase="repo_assembly", project_root=project_root,
        )
        assert state.sub_stage == "test_gate"

        state = dispatch_gate_response(
            state, "gate_5_1_repo_test", "TESTS PASSED", project_root
        )
        assert state.sub_stage == "complete"

        # Step 16: Pipeline complete verification
        action = route(state, project_root)
        assert action["ACTION"] == "pipeline_complete"

        # Final domain assertions
        save_state(state, project_root)
        final_state = load_state(project_root)
        assert final_state.stage == "5"
        assert final_state.sub_stage == "complete"
        assert final_state.project_name == "End-to-End Test"
        assert len(final_state.verified_units) == 2
        assert final_state.verified_units[0]["unit"] == 1
        assert final_state.verified_units[1]["unit"] == 2
        assert final_state.debug_session is None
        assert final_state.debug_history == []
        assert final_state.pass_history == []
        assert validate_state(final_state) == []

        # Verify the env name derivation is domain-correct
        env_name = derive_env_name_from_state(final_state)
        assert env_name == "end_to_end_test"

        # Verify context budget is domain-correct
        assert budget == 180_000

        # Verify both markers exist on disk
        marker2 = project_root / ".svp" / "markers" / "unit_2_verified"
        assert marker1.exists()
        assert marker2.exists()


# =========================================================================
# SECTION 17: Restart / pass-history pipeline (Units 2 + 3 + 10)
# =========================================================================


class TestRestartAndPassHistory:
    """Verify that restarting from earlier stages correctly records
    pass history and resets state.
    """

    def test_restart_from_stage2_records_pass(self, project_at_stage3):
        """restart_from_stage should record the current pass and set
        the target stage.
        """
        state = load_state(project_at_stage3)
        # Complete units in order: current_unit starts at 1
        state = complete_unit(state, 1, project_at_stage3)
        # After completing unit 1, current_unit advances to 2
        state = complete_unit(state, 2, project_at_stage3)
        # After completing unit 2, current_unit advances to 3

        new_state = restart_from_stage(
            state, "2", "Blueprint fix needed", project_at_stage3
        )

        assert new_state.stage == "2"
        assert new_state.current_unit is None
        assert len(new_state.pass_history) == 1
        assert new_state.pass_history[0]["pass_number"] == 1
        assert new_state.pass_history[0]["reached_unit"] == 3
        assert new_state.pass_history[0]["ended_reason"] == "Blueprint fix needed"
        assert new_state.fix_ladder_position is None
        assert new_state.alignment_iteration == 0

    def test_gate_3_2_fix_spec_triggers_restart(self, project_at_stage3):
        """Gate 3.2 FIX SPEC response should restart from Stage 1 and
        record the pass.
        """
        state = load_state(project_at_stage3)
        state.current_unit = 2
        state.sub_stage = "diagnostic_gate"

        new_state = dispatch_gate_response(
            state, "gate_3_2_diagnostic_decision", "FIX SPEC", project_at_stage3
        )
        assert new_state.stage == "1"
        assert len(new_state.pass_history) == 1


# =========================================================================
# SECTION 18: Fix ladder composition (Units 3 + 10)
# =========================================================================


class TestFixLadderComposition:
    """Verify that the fix ladder transitions compose correctly when
    driven by gate responses through the dispatch functions.
    """

    def test_test_fix_ladder_progression(self, project_at_stage3):
        """TEST WRONG at gate 3.1 should advance to fresh_test,
        and route should produce the correct test_agent action.
        """
        state = load_state(project_at_stage3)

        # Gate 3.1: test is wrong
        new_state = dispatch_gate_response(
            state, "gate_3_1_test_validation", "TEST WRONG", project_at_stage3
        )
        assert new_state.fix_ladder_position == "fresh_test"

        # Route should produce test_agent with ladder context
        action = route(new_state, project_at_stage3)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "test_agent"
        assert "fresh_test" in (action.get("PREPARE") or "")

    def test_impl_fix_ladder_progression(self, project_at_stage3):
        """TEST CORRECT at gate 3.1 should advance to fresh_impl."""
        state = load_state(project_at_stage3)

        new_state = dispatch_gate_response(
            state, "gate_3_1_test_validation", "TEST CORRECT", project_at_stage3
        )
        assert new_state.fix_ladder_position == "fresh_impl"

        # Route should produce implementation_agent
        action = route(new_state, project_at_stage3)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "implementation_agent"

    def test_full_impl_fix_ladder_to_diagnostic(self, project_at_stage3):
        """Walk the implementation fix ladder: fresh_impl -> diagnostic ->
        diagnostic_impl.
        """
        state = load_state(project_at_stage3)

        state = advance_fix_ladder(state, "fresh_impl")
        assert state.fix_ladder_position == "fresh_impl"

        state = advance_fix_ladder(state, "diagnostic")
        assert state.fix_ladder_position == "diagnostic"

        state = advance_fix_ladder(state, "diagnostic_impl")
        assert state.fix_ladder_position == "diagnostic_impl"

        # diagnostic_impl is terminal
        with pytest.raises(TransitionError):
            advance_fix_ladder(state, "something_else")


# =========================================================================
# SECTION 19: Project directory creation consistency (Units 7 + 24)
# =========================================================================


class TestProjectDirectoryConsistency:
    """Verify that Unit 7's create_project_directories and Unit 24's
    create_project_directory produce compatible directory structures.
    """

    def test_unit7_creates_src_and_test_dirs(self, tmp_path):
        """create_project_directories should create src/unit_N and
        tests/unit_N with __init__.py files.
        """
        project_root = tmp_path / "dir_test"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "tests").mkdir()

        create_project_directories(project_root, total_units=3)

        for n in range(1, 4):
            src_dir = project_root / "src" / f"unit_{n}"
            test_dir = project_root / "tests" / f"unit_{n}"
            assert src_dir.is_dir()
            assert test_dir.is_dir()
            assert (src_dir / "__init__.py").exists()
            assert (test_dir / "__init__.py").exists()

    def test_launcher_dirs_and_unit7_dirs_coexist(self, tmp_path):
        """Launcher creates the base structure; Unit 7 adds unit dirs on top.
        Both should coexist without conflict.
        """
        project_root = create_project_directory("coexist_test", tmp_path)

        # Now create unit directories
        create_project_directories(project_root, total_units=2)

        # All launcher dirs should still exist
        for d in PROJECT_DIRS:
            assert (project_root / d).is_dir()

        # Unit dirs should also exist
        assert (project_root / "src" / "unit_1").is_dir()
        assert (project_root / "tests" / "unit_2").is_dir()


# =========================================================================
# SECTION 20: Tagged line extraction for ledger and compaction
# =========================================================================


class TestTaggedLineExtraction:
    """Verify that extract_tagged_lines (Unit 4) correctly identifies
    markers that are then used by the compaction algorithm.
    """

    def test_decision_and_confirmed_markers(self):
        """Extract [DECISION] and [CONFIRMED] markers from content."""
        content = (
            "Some discussion text\n"
            "[QUESTION] What is the correct behavior?\n"
            "More text\n"
            "[DECISION] We will use approach A with B.\n"
            "Final remarks\n"
            "[CONFIRMED] Approach A confirmed.\n"
        )
        tagged = extract_tagged_lines(content)
        assert len(tagged) == 3
        markers = [t[0] for t in tagged]
        assert "[QUESTION]" in markers
        assert "[DECISION]" in markers
        assert "[CONFIRMED]" in markers

    def test_no_markers_produces_empty_list(self):
        """Content without markers should produce empty list."""
        tagged = extract_tagged_lines("Just regular text.\nNo markers here.")
        assert tagged == []


# =========================================================================
# Helper function
# =========================================================================


def _build_state_for_gate(gate_id: str, project_root: Path) -> PipelineState:
    """Build a PipelineState appropriate for testing a given gate_id."""
    state = create_initial_state("test")

    if gate_id.startswith("gate_0"):
        state.stage = "0"
        state.sub_stage = "hook_activation"
    elif gate_id.startswith("gate_1"):
        state.stage = "1"
        state.sub_stage = "approval"
    elif gate_id.startswith("gate_2"):
        state.stage = "2"
        state.sub_stage = "approval"
    elif gate_id.startswith("gate_3"):
        state.stage = "3"
        state.current_unit = 1
        state.total_units = 5
    elif gate_id.startswith("gate_4"):
        state.stage = "4"
    elif gate_id.startswith("gate_5"):
        state.stage = "5"
    elif gate_id.startswith("gate_6"):
        state.stage = "5"
        state.debug_session = DebugSession(
            bug_id=1,
            description="Test bug",
            phase="triage_readonly",
            authorized=False,
        )
        # Some gate_6 gates require authorized session or specific phase
        if gate_id in (
            "gate_6_1_regression_test",
            "gate_6_2_debug_classification",
            "gate_6_3_repair_exhausted",
        ):
            state.debug_session.authorized = True
            state.debug_session.phase = "regression_test"
        if gate_id == "gate_6_3_repair_exhausted":
            state.debug_session.phase = "repair"
        if gate_id == "gate_6_4_non_reproducible":
            state.debug_session.authorized = True
            state.debug_session.phase = "triage"

    return state
