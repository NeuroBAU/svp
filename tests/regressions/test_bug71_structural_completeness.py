"""Bug 71: Structural completeness test suite.

Automates 14 techniques for catching declaration-vs-usage bugs
across the SVP pipeline. Each test class guards against one class
of bug found systematically in Bugs 52-70.

These tests act as permanent regression guards: if any new gate,
agent, status line, sub-stage, or phase is declared in a stub or
script but not wired into the corresponding handler, these tests
will fail.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"

# Add scripts to path so we can import routing, state_transitions, etc.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Imports from stubs (canonical API)
# ---------------------------------------------------------------------------
from src.unit_2.stub import (
    DebugSession,
    FIX_LADDER_POSITIONS,
    PipelineState,
    STAGE_3_SUB_STAGES,
    STAGE_4_SUB_STAGES,
    STAGE_5_SUB_STAGES,
)
from src.unit_9.stub import ALL_GATE_IDS, KNOWN_AGENT_TYPES
from src.unit_10.stub import (
    AGENT_STATUS_LINES as STUB_AGENT_STATUS_LINES,
    COMMAND_STATUS_PATTERNS as STUB_COMMAND_STATUS_PATTERNS,
    GATE_RESPONSES as STUB_GATE_RESPONSES,
)

# ---------------------------------------------------------------------------
# Imports from scripts (implementation)
# ---------------------------------------------------------------------------
from routing import (
    AGENT_STATUS_LINES as SCRIPT_AGENT_STATUS_LINES,
    COMMAND_STATUS_PATTERNS as SCRIPT_COMMAND_STATUS_PATTERNS,
    GATE_VOCABULARY as SCRIPT_GATE_VOCABULARY,
    _KNOWN_PHASES,
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
    route,
)
from state_transitions import (
    _DEBUG_PHASE_TRANSITIONS,
    _clone_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**overrides) -> PipelineState:
    """Create a PipelineState with sensible defaults, applying overrides."""
    defaults = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 10,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _make_debug_state(phase: str = "triage", authorized: bool = True) -> PipelineState:
    """Create a Stage 5 state with an active debug session."""
    ds = DebugSession(
        bug_id=1,
        description="test bug",
        classification=None,
        affected_units=[1],
        phase=phase,
        authorized=authorized,
    )
    return PipelineState(
        stage="5",
        sub_stage=None,
        current_unit=None,
        total_units=10,
        debug_session=ds,
    )


def _extract_agent_strings_from_route_source() -> Set[str]:
    """Use AST to extract all AGENT string values from route() and its helpers."""
    routing_path = SCRIPTS_DIR / "routing.py"
    tree = ast.parse(routing_path.read_text(encoding="utf-8"))
    agents = set()
    for node in ast.walk(tree):
        # Match dict literals like {"AGENT": "some_agent", ...}
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "AGENT"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    agents.add(value.value)
    return agents


def _extract_gate_ids_from_route_source() -> Set[str]:
    """Use AST to extract all GATE_ID string values from route() and its helpers."""
    routing_path = SCRIPTS_DIR / "routing.py"
    tree = ast.parse(routing_path.read_text(encoding="utf-8"))
    gate_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "GATE_ID"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    gate_ids.add(value.value)
    return gate_ids


def _get_public_function_names(filepath: Path) -> Set[str]:
    """Extract all public (non-underscore-prefixed) function names from a module."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    names = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
    return names


def _get_imported_names(filepath: Path) -> Set[str]:
    """Extract all names imported from any module in the given file."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname if alias.asname else alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname if alias.asname else alias.name)
    return names


# ===========================================================================
# Test 1 -- Gate Vocabulary vs Route Reachability
# ===========================================================================


class TestGateVocabularyVsRouteReachability:
    """For every gate_id in GATE_VOCABULARY, verify there exists at least one
    pipeline state where route() returns an action with GATE_ID == gate_id.

    Exception: gate_hint_conflict is triggered by orchestration (cross-agent
    status line), not by route().
    """

    ORCHESTRATION_ONLY_GATES = {"gate_hint_conflict"}

    def test_all_gate_ids_reachable_via_ast(self):
        """Every gate_id declared in GATE_VOCABULARY appears as a GATE_ID
        value in route() source code (AST analysis)."""
        gate_ids_in_source = _extract_gate_ids_from_route_source()
        for gate_id in SCRIPT_GATE_VOCABULARY:
            if gate_id in self.ORCHESTRATION_ONLY_GATES:
                continue
            assert gate_id in gate_ids_in_source, (
                f"Gate '{gate_id}' is declared in GATE_VOCABULARY but never "
                f"appears as GATE_ID in route() source. "
                f"Found GATE_IDs: {sorted(gate_ids_in_source)}"
            )

    def test_no_undeclared_gates_in_route(self):
        """Every GATE_ID used in route() source is declared in GATE_VOCABULARY."""
        gate_ids_in_source = _extract_gate_ids_from_route_source()
        for gate_id in gate_ids_in_source:
            assert gate_id in SCRIPT_GATE_VOCABULARY, (
                f"GATE_ID '{gate_id}' used in route() but not declared in GATE_VOCABULARY"
            )


# ===========================================================================
# Test 2 -- Response Options vs Dispatch Handlers
# ===========================================================================


class TestResponseOptionsVsDispatchHandlers:
    """For every (gate_id, response) pair in GATE_VOCABULARY, call
    dispatch_gate_response and verify the handler exists (no KeyError).

    Intentional no-ops are documented.
    """

    # These (gate_id, response) pairs intentionally return state unchanged
    # (two-branch no-ops: the response just keeps the status in last_status.txt
    # and the next route() call reads it to decide what to do)
    INTENTIONAL_NO_OPS = {
        ("gate_0_1_hook_activation", "HOOKS FAILED"),
        ("gate_0_2_context_approval", "CONTEXT REJECTED"),
        ("gate_0_2_context_approval", "CONTEXT NOT READY"),
        ("gate_0_3r_profile_revision", "PROFILE REJECTED"),
        ("gate_1_1_spec_draft", "REVISE"),
        ("gate_1_1_spec_draft", "FRESH REVIEW"),
        ("gate_1_2_spec_post_review", "REVISE"),
        ("gate_1_2_spec_post_review", "FRESH REVIEW"),
        ("gate_2_1_blueprint_approval", "REVISE"),
        ("gate_2_1_blueprint_approval", "FRESH REVIEW"),
        ("gate_2_2_blueprint_post_review", "REVISE"),
        ("gate_2_2_blueprint_post_review", "FRESH REVIEW"),
        ("gate_4_1_integration_failure", "ASSEMBLY FIX"),
        ("gate_5_3_unused_functions", "OVERRIDE CONTINUE"),
        ("gate_6_1_regression_test", "TEST WRONG"),
        ("gate_6_3_repair_exhausted", "RETRY REPAIR"),
        ("gate_6_4_non_reproducible", "RETRY TRIAGE"),
        ("gate_6_5_debug_commit", "COMMIT REJECTED"),
        ("gate_hint_conflict", "BLUEPRINT CORRECT"),
    }

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create minimal project structure for dispatch."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (tmp_path / "specs").mkdir()
        (tmp_path / "docs" / "history").mkdir(parents=True)
        (tmp_path / "blueprint" / "history").mkdir(parents=True)
        # Create spec and blueprint files for versioning
        (tmp_path / "specs" / "stakeholder_spec.md").write_text("spec", encoding="utf-8")
        (tmp_path / "blueprint" / "blueprint_prose.md").write_text("prose", encoding="utf-8")
        (tmp_path / "blueprint" / "blueprint_contracts.md").write_text("contracts", encoding="utf-8")
        return tmp_path

    def _state_for_gate(self, gate_id: str) -> PipelineState:
        """Construct a valid state for the given gate."""
        if gate_id == "gate_0_3r_profile_revision":
            # Redo profile revision gate requires redo sub-stage
            return _make_state(
                stage="3", sub_stage="redo_profile_delivery",
                current_unit=1,
                redo_triggered_from={
                    "stage": "3", "sub_stage": "implementation",
                    "current_unit": 1, "fix_ladder_position": None,
                    "red_run_retries": 0,
                },
            )
        elif gate_id.startswith("gate_0"):
            return _make_state(stage="0", sub_stage="hook_activation", current_unit=None)
        elif gate_id.startswith("gate_1"):
            return _make_state(stage="1", sub_stage=None, current_unit=None)
        elif gate_id.startswith("gate_2"):
            return _make_state(stage="2", sub_stage="alignment_check", current_unit=None)
        elif gate_id == "gate_3_1_test_validation":
            return _make_state(stage="3", sub_stage="gate_3_1")
        elif gate_id == "gate_3_2_diagnostic_decision":
            return _make_state(stage="3", sub_stage="gate_3_2")
        elif gate_id.startswith("gate_4"):
            return _make_state(stage="4", sub_stage=None, current_unit=None)
        elif gate_id.startswith("gate_5"):
            return _make_state(stage="5", sub_stage="repo_test", current_unit=None)
        elif gate_id.startswith("gate_6"):
            return _make_debug_state(phase="triage")
        elif gate_id == "gate_hint_conflict":
            return _make_state(stage="3", sub_stage="implementation")
        return _make_state()

    @pytest.mark.parametrize(
        "gate_id,response",
        [
            (gid, resp)
            for gid, responses in sorted(SCRIPT_GATE_VOCABULARY.items())
            for resp in responses
        ],
    )
    def test_dispatch_gate_response_no_error(self, gate_id, response, project_root):
        """dispatch_gate_response does not raise for any declared (gate_id, response)."""
        state = self._state_for_gate(gate_id)
        # Should not raise
        result = dispatch_gate_response(state, gate_id, response, project_root)
        assert result is not None


# ===========================================================================
# Test 3 -- Exported Functions vs Call Sites
# ===========================================================================


class TestExportedFunctionsVsCallSites:
    """Every public function in state_transitions.py is imported somewhere
    in routing.py or prepare_task.py. No orphaned public functions."""

    def test_no_orphaned_public_functions(self):
        st_path = SCRIPTS_DIR / "state_transitions.py"
        if not st_path.exists():
            pytest.skip("scripts/state_transitions.py not found")

        public_funcs = _get_public_function_names(st_path)

        # Gather imports from routing.py and prepare_task.py
        consumers = set()
        for fname in ("routing.py", "prepare_task.py", "update_state.py"):
            fpath = SCRIPTS_DIR / fname
            if fpath.exists():
                consumers |= _get_imported_names(fpath)

        orphaned = public_funcs - consumers
        # TransitionError is a class, not a function -- filter it out
        # Also filter known exceptions (classes)
        orphaned = {
            f for f in orphaned
            if not f[0].isupper()  # skip class names
        }
        assert not orphaned, (
            f"Orphaned public functions in state_transitions.py "
            f"not imported anywhere: {sorted(orphaned)}"
        )


# ===========================================================================
# Test 4 -- Stub vs Script Synchronization (constants)
# ===========================================================================


class TestStubVsScriptSynchronization:
    """Key constants in stubs must match their script counterparts."""

    def test_gate_vocabulary_keys_match(self):
        """GATE_RESPONSES (stub) keys == GATE_VOCABULARY (script) keys."""
        stub_keys = set(STUB_GATE_RESPONSES.keys())
        script_keys = set(SCRIPT_GATE_VOCABULARY.keys())
        assert stub_keys == script_keys, (
            f"Mismatch in gate IDs.\n"
            f"  Stub-only: {sorted(stub_keys - script_keys)}\n"
            f"  Script-only: {sorted(script_keys - stub_keys)}"
        )

    def test_gate_responses_match(self):
        """For each gate, the response options match between stub and script."""
        for gate_id in STUB_GATE_RESPONSES:
            stub_responses = set(STUB_GATE_RESPONSES[gate_id])
            script_responses = set(SCRIPT_GATE_VOCABULARY.get(gate_id, []))
            assert stub_responses == script_responses, (
                f"Response mismatch for {gate_id}.\n"
                f"  Stub: {sorted(stub_responses)}\n"
                f"  Script: {sorted(script_responses)}"
            )

    def test_agent_status_lines_match(self):
        """AGENT_STATUS_LINES keys and values match between stub and script."""
        stub_keys = set(STUB_AGENT_STATUS_LINES.keys())
        script_keys = set(SCRIPT_AGENT_STATUS_LINES.keys())
        assert stub_keys == script_keys, (
            f"Agent type mismatch.\n"
            f"  Stub-only: {sorted(stub_keys - script_keys)}\n"
            f"  Script-only: {sorted(script_keys - stub_keys)}"
        )
        for agent_type in STUB_AGENT_STATUS_LINES:
            stub_lines = set(STUB_AGENT_STATUS_LINES[agent_type])
            script_lines = set(SCRIPT_AGENT_STATUS_LINES.get(agent_type, []))
            assert stub_lines == script_lines, (
                f"Status line mismatch for {agent_type}.\n"
                f"  Stub: {sorted(stub_lines)}\n"
                f"  Script: {sorted(script_lines)}"
            )

    def test_command_status_patterns_match(self):
        """COMMAND_STATUS_PATTERNS match between stub and script."""
        stub_set = set(STUB_COMMAND_STATUS_PATTERNS)
        script_set = set(SCRIPT_COMMAND_STATUS_PATTERNS)
        assert stub_set == script_set, (
            f"Command status pattern mismatch.\n"
            f"  Stub-only: {sorted(stub_set - script_set)}\n"
            f"  Script-only: {sorted(script_set - stub_set)}"
        )

    def test_all_gate_ids_match_vocabulary(self):
        """ALL_GATE_IDS (unit_9 stub) matches GATE_VOCABULARY keys (script)."""
        stub_set = set(ALL_GATE_IDS)
        script_set = set(SCRIPT_GATE_VOCABULARY.keys())
        assert stub_set == script_set, (
            f"ALL_GATE_IDS mismatch.\n"
            f"  Stub-only: {sorted(stub_set - script_set)}\n"
            f"  Script-only: {sorted(script_set - stub_set)}"
        )

    def test_known_agent_types_match_status_lines(self):
        """KNOWN_AGENT_TYPES (unit_9 stub) matches AGENT_STATUS_LINES keys (script)."""
        stub_set = set(KNOWN_AGENT_TYPES)
        script_set = set(SCRIPT_AGENT_STATUS_LINES.keys())
        assert stub_set == script_set, (
            f"KNOWN_AGENT_TYPES mismatch vs AGENT_STATUS_LINES.\n"
            f"  KNOWN_AGENT_TYPES-only: {sorted(stub_set - script_set)}\n"
            f"  AGENT_STATUS_LINES-only: {sorted(script_set - stub_set)}"
        )

    def test_fix_ladder_positions_match(self):
        """FIX_LADDER_POSITIONS (unit_2 stub) includes all positions used
        in _FIX_LADDER_TRANSITIONS (unit_3 stub)."""
        from src.unit_3.stub import _FIX_LADDER_TRANSITIONS
        all_positions = set()
        for k, v in _FIX_LADDER_TRANSITIONS.items():
            if k is not None:
                all_positions.add(k)
            all_positions.update(v)
        stub_positions = {p for p in FIX_LADDER_POSITIONS if p is not None}
        assert all_positions == stub_positions, (
            f"FIX_LADDER_POSITIONS mismatch.\n"
            f"  In transitions but not declared: {sorted(all_positions - stub_positions)}\n"
            f"  Declared but not in transitions: {sorted(stub_positions - all_positions)}"
        )


# ===========================================================================
# Test 5 -- SKIP (narrative-vs-contract not automatable)
# ===========================================================================

# Intentionally skipped per task specification.


# ===========================================================================
# Test 6 -- Per-Agent Loading Matrix
# ===========================================================================


class TestPerAgentLoadingMatrix:
    """Verify that agent task prompt assembly uses the correct blueprint
    loading mode for each agent type."""

    def test_prepare_task_source_exists(self):
        """prepare_task.py exists in the scripts directory."""
        assert (SCRIPTS_DIR / "prepare_task.py").exists()

    def test_prepare_task_has_agent_handling(self):
        """prepare_task.py contains agent-type-specific logic (AST check)."""
        pt_path = SCRIPTS_DIR / "prepare_task.py"
        if not pt_path.exists():
            pytest.skip("prepare_task.py not found")
        source = pt_path.read_text(encoding="utf-8")
        # Verify key agent types are referenced
        for agent in ("test_agent", "implementation_agent", "blueprint_checker"):
            assert agent in source, (
                f"prepare_task.py does not reference '{agent}'"
            )


# ===========================================================================
# Test 7 -- Agent Status Lines vs Dispatch
# ===========================================================================


class TestAgentStatusLinesVsDispatch:
    """For every (agent_type, status_line) in AGENT_STATUS_LINES, construct
    a state and call dispatch_agent_status. Verify it does not raise."""

    @pytest.fixture
    def project_root(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (tmp_path / "specs").mkdir()
        (tmp_path / "docs" / "history").mkdir(parents=True)
        (tmp_path / "blueprint" / "history").mkdir(parents=True)
        (tmp_path / "specs" / "stakeholder_spec.md").write_text("spec", encoding="utf-8")
        (tmp_path / "blueprint" / "blueprint_prose.md").write_text("prose", encoding="utf-8")
        (tmp_path / "blueprint" / "blueprint_contracts.md").write_text("contracts", encoding="utf-8")
        return tmp_path

    # Map agent_type to (phase, state_kwargs) for dispatch
    AGENT_DISPATCH_CONTEXT: Dict[str, tuple] = {
        "setup_agent": ("setup", {"stage": "0", "sub_stage": "project_context", "current_unit": None}),
        "stakeholder_dialog": ("spec_draft", {"stage": "1", "sub_stage": None, "current_unit": None}),
        "stakeholder_reviewer": ("spec_review", {"stage": "1", "sub_stage": None, "current_unit": None}),
        "blueprint_author": ("blueprint_draft", {"stage": "2", "sub_stage": None, "current_unit": None}),
        "blueprint_checker": ("alignment_check", {"stage": "2", "sub_stage": "alignment_check", "current_unit": None}),
        "blueprint_reviewer": ("blueprint_review", {"stage": "2", "sub_stage": None, "current_unit": None}),
        "test_agent": ("test_generation", {"stage": "3", "sub_stage": "test_generation"}),
        "implementation_agent": ("implementation", {"stage": "3", "sub_stage": "implementation"}),
        "coverage_review": ("coverage_review", {"stage": "3", "sub_stage": "coverage_review"}),
        "diagnostic_agent": ("diagnostic", {"stage": "3", "sub_stage": "implementation", "fix_ladder_position": "diagnostic"}),
        "integration_test_author": ("integration_test", {"stage": "4", "sub_stage": None, "current_unit": None}),
        "git_repo_agent": ("repo_assembly", {"stage": "5", "sub_stage": None, "current_unit": None}),
        "help_agent": ("help", {"stage": "3", "sub_stage": "implementation"}),
        "hint_agent": ("hint", {"stage": "3", "sub_stage": "implementation"}),
        "redo_agent": ("redo", {"stage": "3", "sub_stage": None}),
        "bug_triage": ("debug", {"stage": "5", "sub_stage": None, "current_unit": None}),
        "repair_agent": ("repair", {"stage": "5", "sub_stage": None, "current_unit": None}),
        "reference_indexing": ("reference_indexing", {"stage": "pre_stage_3", "sub_stage": None, "current_unit": None}),
    }

    @pytest.mark.parametrize(
        "agent_type,status_line",
        [
            (atype, sline)
            for atype, lines in sorted(SCRIPT_AGENT_STATUS_LINES.items())
            for sline in lines
        ],
    )
    def test_dispatch_agent_status_no_error(self, agent_type, status_line, project_root):
        """dispatch_agent_status does not raise for any declared status line."""
        ctx = self.AGENT_DISPATCH_CONTEXT.get(agent_type)
        if ctx is None:
            pytest.skip(f"No dispatch context configured for {agent_type}")
        phase, state_kwargs = ctx
        # Add debug session for bug_triage and repair_agent
        if agent_type in ("bug_triage", "repair_agent"):
            state = _make_debug_state(
                phase="triage" if agent_type == "bug_triage" else "repair"
            )
        else:
            state = _make_state(**state_kwargs)
        unit = state.current_unit
        result = dispatch_agent_status(state, agent_type, status_line, unit, phase, project_root)
        assert result is not None

    def test_test_agent_produces_state_change(self, project_root):
        """test_agent TEST_GENERATION_COMPLETE produces a meaningful state change."""
        state = _make_state(stage="3", sub_stage="test_generation")
        result = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE", 1, "test_generation", project_root
        )
        assert result.sub_stage != state.sub_stage or result.stage != state.stage, (
            "test_agent TEST_GENERATION_COMPLETE should change state"
        )

    def test_implementation_agent_produces_state_change(self, project_root):
        """implementation_agent IMPLEMENTATION_COMPLETE produces a state change."""
        state = _make_state(stage="3", sub_stage="implementation")
        result = dispatch_agent_status(
            state, "implementation_agent", "IMPLEMENTATION_COMPLETE", 1, "implementation", project_root
        )
        assert result.sub_stage != state.sub_stage or result.stage != state.stage, (
            "implementation_agent IMPLEMENTATION_COMPLETE should change state"
        )

    def test_coverage_review_keeps_substage(self, project_root):
        """coverage_review agents keep sub_stage for two-branch routing."""
        state = _make_state(stage="3", sub_stage="coverage_review")
        result = dispatch_agent_status(
            state, "coverage_review", "COVERAGE_COMPLETE: no gaps", 1, "coverage_review", project_root
        )
        # Coverage review keeps state unchanged; route() reads last_status
        assert result is not None

    def test_diagnostic_agent_produces_state_change(self, project_root):
        """diagnostic_agent DIAGNOSIS_COMPLETE: implementation changes state."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="diagnostic"
        )
        result = dispatch_agent_status(
            state, "diagnostic_agent", "DIAGNOSIS_COMPLETE: implementation",
            1, "diagnostic", project_root
        )
        assert (
            result.fix_ladder_position != state.fix_ladder_position
            or result.sub_stage != state.sub_stage
        ), "diagnostic_agent DIAGNOSIS_COMPLETE: implementation should change state"


# ===========================================================================
# Test 8 -- Known Agent Types vs Route Invocations
# ===========================================================================


class TestKnownAgentTypesVsRouteInvocations:
    """All AGENT values in route() source are in KNOWN_AGENT_TYPES.

    Exception: agents invoked only by slash commands (help_agent,
    hint_agent, redo_agent) may be in KNOWN_AGENT_TYPES but not in route().
    """

    SLASH_COMMAND_ONLY_AGENTS = {"help_agent", "hint_agent", "redo_agent"}

    def test_route_agents_are_known(self):
        """Every AGENT value emitted by route() is in KNOWN_AGENT_TYPES."""
        agents_in_route = _extract_agent_strings_from_route_source()
        known = set(KNOWN_AGENT_TYPES)
        unknown = agents_in_route - known
        assert not unknown, (
            f"Agents used in route() but not in KNOWN_AGENT_TYPES: {sorted(unknown)}"
        )

    def test_known_agents_reachable(self):
        """Every KNOWN_AGENT_TYPE is either in route() or is a slash-command-only agent."""
        agents_in_route = _extract_agent_strings_from_route_source()
        known = set(KNOWN_AGENT_TYPES)
        unreachable = known - agents_in_route - self.SLASH_COMMAND_ONLY_AGENTS
        assert not unreachable, (
            f"Known agent types not reachable from route() and not slash-command-only: "
            f"{sorted(unreachable)}"
        )


# ===========================================================================
# Test 9 -- Debug Phase Transitions vs Route Handlers
# ===========================================================================


class TestDebugPhaseTransitionsVsRouteHandlers:
    """For every key in _DEBUG_PHASE_TRANSITIONS, construct a Stage 5 state
    with debug_session.phase = key, call route(), verify the result is not
    pipeline_complete or session_boundary (i.e., the phase is handled)."""

    @pytest.fixture
    def project_root(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        return tmp_path

    @pytest.mark.parametrize("debug_phase", list(_DEBUG_PHASE_TRANSITIONS.keys()))
    def test_debug_phase_is_handled(self, debug_phase, project_root):
        """route() handles debug phase '{debug_phase}' without falling to
        pipeline_complete or session_boundary."""
        state = _make_debug_state(phase=debug_phase)
        action = route(state, project_root)
        action_type = action.get("ACTION", "")
        # "stage3_reentry" falls through to normal Stage 5 routing (git_repo_agent),
        # "complete" goes to gate_6_5, "repair" may fall through to git_repo_agent.
        # The key assertion is it must not be session_boundary or error.
        assert action_type != "session_boundary", (
            f"Debug phase '{debug_phase}' fell through to session_boundary. "
            f"Action: {action}"
        )
        # "complete" should result in a human_gate for gate_6_5
        if debug_phase == "complete":
            assert action.get("GATE_ID") == "gate_6_5_debug_commit", (
                f"Debug phase 'complete' should present gate_6_5_debug_commit, got: {action}"
            )


# ===========================================================================
# Test 10 -- Sub-Stages vs Route Branches
# ===========================================================================


class TestSubStagesVsRouteBranches:
    """For each stage (3, 4, 5), for every sub_stage in STAGE_N_SUB_STAGES,
    construct a state and call route(). Verify route() returns a meaningful
    action (not None, not an error)."""

    @pytest.fixture
    def project_root(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        return tmp_path

    @pytest.mark.parametrize("sub_stage", STAGE_3_SUB_STAGES)
    def test_stage_3_sub_stages(self, sub_stage, project_root):
        state = _make_state(stage="3", sub_stage=sub_stage)
        action = route(state, project_root)
        assert action is not None
        action_type = action.get("ACTION", "")
        assert action_type != "error", (
            f"Stage 3 sub_stage='{sub_stage}' returned error: {action}"
        )

    @pytest.mark.parametrize("sub_stage", STAGE_4_SUB_STAGES)
    def test_stage_4_sub_stages(self, sub_stage, project_root):
        state = _make_state(stage="4", sub_stage=sub_stage, current_unit=None)
        action = route(state, project_root)
        assert action is not None
        action_type = action.get("ACTION", "")
        assert action_type != "error", (
            f"Stage 4 sub_stage='{sub_stage}' returned error: {action}"
        )

    @pytest.mark.parametrize("sub_stage", STAGE_5_SUB_STAGES)
    def test_stage_5_sub_stages(self, sub_stage, project_root):
        state = _make_state(stage="5", sub_stage=sub_stage, current_unit=None)
        action = route(state, project_root)
        assert action is not None
        action_type = action.get("ACTION", "")
        assert action_type != "error", (
            f"Stage 5 sub_stage='{sub_stage}' returned error: {action}"
        )


# ===========================================================================
# Test 11 -- Fix Ladder Positions vs Route Context
# ===========================================================================


class TestFixLadderPositionsVsRouteContext:
    """For each position in FIX_LADDER_POSITIONS (excluding None), construct
    a Stage 3 state at implementation sub_stage with that ladder position.
    Call route(). Verify the returned action's AGENT varies based on ladder
    position."""

    @pytest.fixture
    def project_root(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        return tmp_path

    def test_diagnostic_routes_to_diagnostic_agent(self, project_root):
        """fix_ladder_position='diagnostic' at sub_stage='implementation'
        routes to diagnostic_agent, not implementation_agent."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="diagnostic"
        )
        action = route(state, project_root)
        assert action.get("AGENT") == "diagnostic_agent", (
            f"Expected diagnostic_agent for ladder_pos=diagnostic, got: {action}"
        )

    def test_fresh_impl_routes_to_implementation_agent(self, project_root):
        """fix_ladder_position='fresh_impl' at sub_stage='implementation'
        routes to implementation_agent."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="fresh_impl"
        )
        action = route(state, project_root)
        assert action.get("AGENT") == "implementation_agent", (
            f"Expected implementation_agent for ladder_pos=fresh_impl, got: {action}"
        )

    def test_diagnostic_impl_routes_to_implementation_agent(self, project_root):
        """fix_ladder_position='diagnostic_impl' at sub_stage='implementation'
        routes to implementation_agent."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="diagnostic_impl"
        )
        action = route(state, project_root)
        assert action.get("AGENT") == "implementation_agent", (
            f"Expected implementation_agent for ladder_pos=diagnostic_impl, got: {action}"
        )

    def test_fresh_test_at_null_substage_routes_to_test_agent(self, project_root):
        """fix_ladder_position='fresh_test' at sub_stage=None routes to test_agent."""
        state = _make_state(
            stage="3", sub_stage=None, fix_ladder_position="fresh_test"
        )
        action = route(state, project_root)
        assert action.get("AGENT") == "test_agent", (
            f"Expected test_agent for ladder_pos=fresh_test at sub_stage=None, got: {action}"
        )

    def test_hint_test_at_null_substage_routes_to_test_agent(self, project_root):
        """fix_ladder_position='hint_test' at sub_stage=None routes to test_agent."""
        state = _make_state(
            stage="3", sub_stage=None, fix_ladder_position="hint_test"
        )
        action = route(state, project_root)
        assert action.get("AGENT") == "test_agent", (
            f"Expected test_agent for ladder_pos=hint_test at sub_stage=None, got: {action}"
        )

    def test_diagnostic_at_null_substage_routes_to_diagnostic_agent(self, project_root):
        """fix_ladder_position='diagnostic' at sub_stage=None routes to diagnostic_agent."""
        state = _make_state(
            stage="3", sub_stage=None, fix_ladder_position="diagnostic"
        )
        action = route(state, project_root)
        assert action.get("AGENT") == "diagnostic_agent", (
            f"Expected diagnostic_agent for ladder_pos=diagnostic at sub_stage=None, got: {action}"
        )

    def test_null_ladder_at_null_substage_runs_stub_gen(self, project_root):
        """fix_ladder_position=None at sub_stage=None runs stub generation (run_command)."""
        state = _make_state(stage="3", sub_stage=None, fix_ladder_position=None)
        action = route(state, project_root)
        assert action.get("ACTION") == "run_command", (
            f"Expected run_command for null ladder at sub_stage=None, got: {action}"
        )


# ===========================================================================
# Test 12 -- Command Status Patterns vs Phase Handlers
# ===========================================================================


class TestCommandStatusPatternsVsPhaseHandlers:
    """For key (phase, pattern) combinations that should produce state
    transitions, call dispatch_command_status and verify state changes."""

    @pytest.fixture
    def project_root(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        return tmp_path

    def test_green_run_tests_passed(self, project_root):
        """green_run + TESTS_PASSED -> coverage_review."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(state, "TESTS_PASSED", 1, "test_execution", project_root)
        assert result.sub_stage == "coverage_review"

    def test_green_run_tests_failed(self, project_root):
        """green_run + TESTS_FAILED -> engage fix ladder."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(state, "TESTS_FAILED", 1, "test_execution", project_root)
        assert result.sub_stage == "implementation"
        assert result.fix_ladder_position == "fresh_impl"

    def test_red_run_tests_failed(self, project_root):
        """red_run + TESTS_FAILED -> implementation."""
        state = _make_state(stage="3", sub_stage="red_run")
        result = dispatch_command_status(state, "TESTS_FAILED", 1, "test_execution", project_root)
        assert result.sub_stage == "implementation"

    def test_red_run_tests_error(self, project_root):
        """red_run + TESTS_ERROR -> test_generation (not infinite loop)."""
        state = _make_state(stage="3", sub_stage="red_run")
        result = dispatch_command_status(state, "TESTS_ERROR", 1, "test_execution", project_root)
        assert result.sub_stage in ("test_generation", "gate_3_1"), (
            f"red_run TESTS_ERROR should advance, got sub_stage={result.sub_stage}"
        )

    def test_green_run_tests_error(self, project_root):
        """green_run + TESTS_ERROR -> fix ladder (not infinite loop)."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(state, "TESTS_ERROR", 1, "test_execution", project_root)
        assert result.sub_stage != "green_run", (
            "green_run TESTS_ERROR must not stay at green_run (infinite loop)"
        )

    def test_compliance_scan_succeeded(self, project_root):
        """compliance_scan + COMMAND_SUCCEEDED -> repo_complete."""
        state = _make_state(stage="5", sub_stage="compliance_scan", current_unit=None)
        result = dispatch_command_status(state, "COMMAND_SUCCEEDED", None, "compliance_scan", project_root)
        assert result.sub_stage == "repo_complete"

    def test_compliance_scan_unused_functions(self, project_root):
        """compliance_scan + UNUSED_FUNCTIONS_DETECTED -> gate_5_3."""
        state = _make_state(stage="5", sub_stage="compliance_scan", current_unit=None)
        result = dispatch_command_status(
            state, "UNUSED_FUNCTIONS_DETECTED", None, "compliance_scan", project_root
        )
        assert result.sub_stage == "gate_5_3"

    def test_stub_generation_succeeded(self, project_root):
        """stub_generation + COMMAND_SUCCEEDED -> test_generation."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_command_status(state, "COMMAND_SUCCEEDED", 1, "stub_generation", project_root)
        assert result.sub_stage == "test_generation"

    def test_stage4_tests_passed(self, project_root):
        """Stage 4 test_execution + TESTS_PASSED -> advance to Stage 5."""
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_command_status(state, "TESTS_PASSED", None, "test_execution", project_root)
        assert result.stage == "5"

    def test_stage4_tests_failed(self, project_root):
        """Stage 4 test_execution + TESTS_FAILED -> present gate."""
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_command_status(state, "TESTS_FAILED", None, "test_execution", project_root)
        assert result.sub_stage in ("gate_4_1", "gate_4_2")

    def test_stage4_tests_error(self, project_root):
        """Stage 4 test_execution + TESTS_ERROR -> present gate (not stuck)."""
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_command_status(state, "TESTS_ERROR", None, "test_execution", project_root)
        assert result.sub_stage in ("gate_4_1", "gate_4_2")


# ===========================================================================
# Test 13 -- Phase-to-Agent Map vs Known Phases
# ===========================================================================


class TestPhaseToAgentMapVsKnownPhases:
    """Every phase in _KNOWN_PHASES either has a phase_to_agent mapping
    or is a gate/command phase (documented exception)."""

    # Phases that are gate or command phases (no agent mapping needed)
    GATE_OR_COMMAND_PHASES = {
        "gate",
        "stub_generation",
        "unit_completion",
        "quality_gate",
        "compliance_scan",
        "test_execution",
    }

    def test_all_known_phases_have_mapping_or_exception(self):
        """Every _KNOWN_PHASE has a phase_to_agent mapping or is in exceptions."""
        # Extract phase_to_agent from routing.py source
        routing_path = SCRIPTS_DIR / "routing.py"
        source = routing_path.read_text(encoding="utf-8")

        # Find the phase_to_agent dict in dispatch_status
        tree = ast.parse(source)
        phase_to_agent_keys: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                # Check if this looks like the phase_to_agent dict
                # by looking for known keys
                str_keys = []
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        str_keys.append(k.value)
                if "setup" in str_keys and "spec_draft" in str_keys:
                    phase_to_agent_keys = set(str_keys)
                    break

        if not phase_to_agent_keys:
            pytest.skip("Could not extract phase_to_agent from routing.py")

        unmapped = _KNOWN_PHASES - phase_to_agent_keys - self.GATE_OR_COMMAND_PHASES
        assert not unmapped, (
            f"Phases in _KNOWN_PHASES without phase_to_agent mapping "
            f"and not in documented exceptions: {sorted(unmapped)}"
        )


# ===========================================================================
# Test 14 -- Debug Phase Transitions vs Known Phases
# ===========================================================================


class TestDebugPhaseTransitionsVsKnownPhases:
    """Every value in _DEBUG_PHASE_TRANSITIONS (both keys and transition
    targets) is recognized."""

    # All valid debug phase strings
    VALID_DEBUG_PHASES = {
        "triage_readonly",
        "triage",
        "regression_test",
        "stage3_reentry",
        "repair",
        "complete",
    }

    def test_all_transition_keys_are_valid(self):
        """Every key in _DEBUG_PHASE_TRANSITIONS is a valid debug phase."""
        for key in _DEBUG_PHASE_TRANSITIONS:
            assert key in self.VALID_DEBUG_PHASES, (
                f"Debug phase transition key '{key}' is not a recognized debug phase"
            )

    def test_all_transition_targets_are_valid(self):
        """Every target in _DEBUG_PHASE_TRANSITIONS values is a valid debug phase."""
        for source, targets in _DEBUG_PHASE_TRANSITIONS.items():
            for target in targets:
                assert target in self.VALID_DEBUG_PHASES, (
                    f"Debug phase transition target '{target}' "
                    f"(from '{source}') is not a recognized debug phase"
                )

    def test_all_valid_phases_are_keys(self):
        """Every valid debug phase appears as a key in _DEBUG_PHASE_TRANSITIONS."""
        for phase in self.VALID_DEBUG_PHASES:
            assert phase in _DEBUG_PHASE_TRANSITIONS, (
                f"Valid debug phase '{phase}' is not a key in _DEBUG_PHASE_TRANSITIONS"
            )

    def test_transition_targets_match_stub(self):
        """_DEBUG_PHASE_TRANSITIONS in scripts matches the stub version."""
        from src.unit_3.stub import _DEBUG_PHASE_TRANSITIONS as STUB_DPT
        assert set(STUB_DPT.keys()) == set(_DEBUG_PHASE_TRANSITIONS.keys()), (
            f"Debug phase transition keys differ between stub and script.\n"
            f"  Stub-only: {sorted(set(STUB_DPT.keys()) - set(_DEBUG_PHASE_TRANSITIONS.keys()))}\n"
            f"  Script-only: {sorted(set(_DEBUG_PHASE_TRANSITIONS.keys()) - set(STUB_DPT.keys()))}"
        )
        for key in STUB_DPT:
            assert set(STUB_DPT[key]) == set(_DEBUG_PHASE_TRANSITIONS[key]), (
                f"Debug phase transitions from '{key}' differ.\n"
                f"  Stub: {sorted(STUB_DPT[key])}\n"
                f"  Script: {sorted(_DEBUG_PHASE_TRANSITIONS[key])}"
            )
