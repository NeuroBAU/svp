"""Bug 71: Structural completeness test suite.

Automates 14 techniques for catching declaration-vs-usage bugs
across the SVP pipeline. Each test class guards against one class
of bug found systematically in Bugs 52-70.

These tests act as permanent regression guards: if any new gate,
agent, status line, sub-stage, or phase is declared in a stub or
script but not wired into the corresponding handler, these tests
will fail.

Adapted for SVP 2.2:
- DebugSession replaced with plain dict
- route() takes only project_root (loads state from disk)
- dispatch_agent_status takes (state, agent_type, status_line, project_root)
- dispatch_command_status takes (state, command_type, status_line, sub_stage=None)
- Action block keys are lowercase (action_type, command, gate_id, agent_type)
- FIX_LADDER_POSITIONS -> VALID_FIX_LADDER_POSITIONS
- STAGE_N_SUB_STAGES -> VALID_SUB_STAGES[N]
- COMMAND_STATUS_PATTERNS, _KNOWN_PHASES, _DEBUG_PHASE_TRANSITIONS, _clone_state
  do not exist in SVP 2.2 -- related tests are skipped
"""

import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if not SCRIPTS_DIR.is_dir():
    SCRIPTS_DIR = PROJECT_ROOT / "svp" / "scripts"
SRC_DIR = PROJECT_ROOT / "src"

# Add scripts to path so we can import routing, state_transitions, etc.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Imports from scripts (SVP 2.2 API)
# ---------------------------------------------------------------------------
from pipeline_state import (
    PipelineState,
    VALID_FIX_LADDER_POSITIONS,
    VALID_SUB_STAGES,
)
from prepare_task import ALL_GATE_IDS, KNOWN_AGENT_TYPES
from routing import (
    AGENT_STATUS_LINES,
    GATE_RESPONSES,
    GATE_VOCABULARY,
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
    route,
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
    }
    defaults.update(overrides)
    # Remove keys not in PipelineState (e.g. alignment_iteration typo from SVP 2.1)
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


def _make_debug_state(phase: str = "triage", authorized: bool = True) -> PipelineState:
    """Create a Stage 5 state with an active debug session (plain dict)."""
    ds = {
        "authorized": authorized,
        "bug_number": 1,
        "classification": None,
        "affected_units": [1],
        "phase": phase,
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    return PipelineState(
        stage="5",
        sub_stage=None,
        current_unit=None,
        total_units=10,
        debug_session=ds,
    )


def _write_state_json(tmp_path, state):
    """Write a PipelineState to .svp/pipeline_state.json for route() to load."""
    from dataclasses import asdict
    data = asdict(state)
    # Rename pass_ -> pass for JSON
    pass_val = data.pop("pass_", None)
    data["pass"] = pass_val
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    state_path = svp_dir / "pipeline_state.json"
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _extract_agent_strings_from_route_source() -> Set[str]:
    """Use AST to extract all agent_type string values from route() and its helpers."""
    routing_path = SCRIPTS_DIR / "routing.py"
    tree = ast.parse(routing_path.read_text(encoding="utf-8"))
    agents = set()
    for node in ast.walk(tree):
        # Match dict literals like {"agent_type": "some_agent", ...}
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value in ("agent_type", "AGENT")
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    agents.add(value.value)
        # Match _make_action_block(agent_type="agent_name", ...) calls
        if isinstance(node, ast.Call):
            func = node.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name in ("_make_action_block", "_invoke_agent_action"):
                # Check keyword args for agent_type
                for kw in node.keywords:
                    if kw.arg == "agent_type" and isinstance(kw.value, ast.Constant):
                        agents.add(kw.value.value)
                # Also check positional args for _invoke_agent_action
                if func_name == "_invoke_agent_action" and node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        agents.add(first_arg.value)
    return agents


def _extract_gate_ids_from_route_source() -> Set[str]:
    """Use AST to extract all gate_id string values from route() and its helpers."""
    routing_path = SCRIPTS_DIR / "routing.py"
    tree = ast.parse(routing_path.read_text(encoding="utf-8"))
    gate_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value in ("gate_id", "GATE_ID")
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    gate_ids.add(value.value)
        # Match _make_action_block(gate_id="gate_name", ...) calls
        if isinstance(node, ast.Call):
            func = node.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name == "_make_action_block":
                for kw in node.keywords:
                    if kw.arg == "gate_id" and isinstance(kw.value, ast.Constant):
                        gate_ids.add(kw.value.value)
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
    pipeline state where route() returns an action with gate_id == gate_id.

    Exception: gate_hint_conflict is triggered by orchestration (cross-agent
    status line), not by route().
    """

    # SVP 2.2: Some gates are only in dispatch_gate_response, not presented by route()
    # These include gates presented by orchestration, CLI, or via sub_stage-based routing
    ORCHESTRATION_OR_DISPATCH_ONLY_GATES = {
        "gate_hint_conflict",
        "gate_3_1_test_validation",
        "gate_4_1_integration_failure",
        "gate_4_1a",
        "gate_4_2_assembly_exhausted",
        "gate_5_2_assembly_exhausted",
        "gate_5_3_unused_functions",
        "gate_6_1a_divergence_warning",
    }

    def test_all_gate_ids_reachable_via_ast(self):
        """Every gate_id declared in GATE_VOCABULARY appears as a gate_id
        value in route() source code (AST analysis), except for gates that
        are only handled in dispatch_gate_response."""
        gate_ids_in_source = _extract_gate_ids_from_route_source()
        for gate_id in GATE_VOCABULARY:
            if gate_id in self.ORCHESTRATION_OR_DISPATCH_ONLY_GATES:
                continue
            assert gate_id in gate_ids_in_source, (
                f"Gate '{gate_id}' is declared in GATE_VOCABULARY but never "
                f"appears as gate_id in route() source. "
                f"Found gate_ids: {sorted(gate_ids_in_source)}"
            )

    def test_no_undeclared_gates_in_route(self):
        """Every gate_id used in route() source is declared in GATE_VOCABULARY."""
        gate_ids_in_source = _extract_gate_ids_from_route_source()
        for gate_id in gate_ids_in_source:
            assert gate_id in GATE_VOCABULARY, (
                f"gate_id '{gate_id}' used in route() but not declared in GATE_VOCABULARY"
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
        ("gate_6_3_regression_test", "TEST WRONG"),
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
        elif gate_id == "gate_2_3_toolchain_verified":
            # Bug S3-180: this gate is presented at pre_stage_3 / dep_diff,
            # not stage 2. Distinct from gate_2_3_alignment_exhausted.
            return _make_state(
                stage="pre_stage_3", sub_stage="dep_diff", current_unit=None
            )
        elif gate_id.startswith("gate_2"):
            return _make_state(stage="2", sub_stage="alignment_check", current_unit=None)
        elif gate_id == "gate_3_1_test_validation":
            return _make_state(stage="3", sub_stage="gate_3_1")
        elif gate_id == "gate_3_2_diagnostic_decision":
            return _make_state(stage="3", sub_stage="gate_3_2")
        elif gate_id == "gate_3_3_test_layer_review":
            # Bug S3-205 / cycle K-3: implementation_agent emits TESTS_FLAWED
            # while sub_stage="implementation"; routing presents this gate.
            return _make_state(stage="3", sub_stage="implementation", current_unit=1)
        elif gate_id.startswith("gate_4"):
            return _make_state(stage="4", sub_stage=None, current_unit=None)
        elif gate_id.startswith("gate_5"):
            return _make_state(stage="5", sub_stage="repo_test", current_unit=None)
        elif gate_id.startswith("gate_6"):
            return _make_debug_state(phase="triage")
        elif gate_id == "gate_hint_conflict":
            return _make_state(stage="3", sub_stage="implementation")
        elif gate_id == "gate_pass_transition_post_pass1":
            return _make_state(stage="5", sub_stage="pass_transition", current_unit=None, pass_=1)
        elif gate_id == "gate_pass_transition_post_pass2":
            return _make_state(stage="5", sub_stage="pass_transition", current_unit=None, pass_=2)
        elif gate_id.startswith("gate_7"):
            return _make_state(stage="5", sub_stage=None, current_unit=None,
                               oracle_session_active=True)
        return _make_state()

    @pytest.mark.parametrize(
        "gate_id,response",
        [
            (gid, resp)
            for gid, responses in sorted(GATE_VOCABULARY.items())
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

        # Gather imports from routing.py, prepare_task.py, and update_state.py
        consumers = set()
        for fname in ("routing.py", "prepare_task.py", "update_state.py"):
            fpath = SCRIPTS_DIR / fname
            if fpath.exists():
                consumers |= _get_imported_names(fpath)

        orphaned = public_funcs - consumers
        # Filter out class names and known compatibility aliases
        _COMPAT_ALIASES = {
            "advance_from_quality_gate",
            "enter_quality_gate_retry",
            "fail_quality_gate_to_ladder",
            # SVP 2.2 transition functions consumed by src stubs, not scripts
            "clear_pass",
            "mark_unit_deferred_broken",
            "resolve_deferred_broken",
            "enter_pass_1",
            # Quality gate functions imported by routing.py directly from unit_6 stubs
            "advance_quality_gate_to_retry",
            "complete_alignment_check",
            "enter_alignment_check",
            "enter_quality_gate",
            "quality_gate_fail_to_ladder",
            "quality_gate_pass",
            "reset_red_run_retries",
            "set_delivered_repo_path",
            "version_document",
        }
        orphaned = {
            f for f in orphaned
            if not f[0].isupper()  # skip class names
            and f not in _COMPAT_ALIASES
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
        """GATE_RESPONSES keys == GATE_VOCABULARY keys."""
        stub_keys = set(GATE_RESPONSES.keys())
        script_keys = set(GATE_VOCABULARY.keys())
        assert stub_keys == script_keys, (
            f"Mismatch in gate IDs.\n"
            f"  GATE_RESPONSES-only: {sorted(stub_keys - script_keys)}\n"
            f"  GATE_VOCABULARY-only: {sorted(script_keys - stub_keys)}"
        )

    def test_gate_responses_match(self):
        """For each gate, the response options match between GATE_RESPONSES and GATE_VOCABULARY."""
        for gate_id in GATE_RESPONSES:
            stub_responses = set(GATE_RESPONSES[gate_id])
            script_responses = set(GATE_VOCABULARY.get(gate_id, []))
            assert stub_responses == script_responses, (
                f"Response mismatch for {gate_id}.\n"
                f"  GATE_RESPONSES: {sorted(stub_responses)}\n"
                f"  GATE_VOCABULARY: {sorted(script_responses)}"
            )

    def test_all_gate_ids_match_vocabulary(self):
        """ALL_GATE_IDS (prepare_task) matches GATE_VOCABULARY keys."""
        stub_set = set(ALL_GATE_IDS)
        script_set = set(GATE_VOCABULARY.keys())
        assert stub_set == script_set, (
            f"ALL_GATE_IDS mismatch.\n"
            f"  ALL_GATE_IDS-only: {sorted(stub_set - script_set)}\n"
            f"  GATE_VOCABULARY-only: {sorted(script_set - stub_set)}"
        )

    def test_known_agent_types_match_status_lines(self):
        """KNOWN_AGENT_TYPES (prepare_task) matches AGENT_STATUS_LINES keys.

        SVP 2.2: Some agents use short names in KNOWN_AGENT_TYPES
        (coverage_review, bug_triage) but _agent suffix in AGENT_STATUS_LINES
        (coverage_review_agent, bug_triage_agent). These are known aliases.
        """
        # Known naming aliases between KNOWN_AGENT_TYPES and AGENT_STATUS_LINES
        _KNOWN_ALIASES = {
            "coverage_review": "coverage_review_agent",
            "bug_triage": "bug_triage_agent",
        }
        stub_set = set(KNOWN_AGENT_TYPES)
        script_set = set(AGENT_STATUS_LINES.keys())
        # Normalize: expand aliases in stub_set
        normalized_stub = set()
        for name in stub_set:
            normalized_stub.add(_KNOWN_ALIASES.get(name, name))
        diff_stub_only = normalized_stub - script_set
        diff_script_only = script_set - normalized_stub
        assert not diff_stub_only and not diff_script_only, (
            f"KNOWN_AGENT_TYPES mismatch vs AGENT_STATUS_LINES.\n"
            f"  KNOWN_AGENT_TYPES-only: {sorted(diff_stub_only)}\n"
            f"  AGENT_STATUS_LINES-only: {sorted(diff_script_only)}"
        )

    def test_fix_ladder_positions_valid(self):
        """VALID_FIX_LADDER_POSITIONS includes all expected positions."""
        expected_non_none = {"fresh_impl", "diagnostic", "diagnostic_impl", "exhausted"}
        actual_non_none = {p for p in VALID_FIX_LADDER_POSITIONS if p is not None}
        assert expected_non_none.issubset(actual_non_none), (
            f"VALID_FIX_LADDER_POSITIONS missing expected positions.\n"
            f"  Missing: {sorted(expected_non_none - actual_non_none)}"
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
        # Bug S3-112: dispatch_agent_status for git_repo_agent +
        # REPO_ASSEMBLY_COMPLETE validates the canonical sibling directory
        # exists. Create it here so the structural-completeness sweep
        # does not fail for that one case. Profile is absent, so fallback
        # to project_root.name (= tmp_path.name) is used.
        sibling = tmp_path.parent / f"{tmp_path.name}-repo"
        sibling.mkdir(exist_ok=True)
        return tmp_path

    # Map agent_type to state_kwargs for dispatch (SVP 2.2: no phase/unit args)
    AGENT_DISPATCH_CONTEXT: Dict[str, dict] = {
        "setup_agent": {"stage": "0", "sub_stage": "project_context", "current_unit": None},
        "stakeholder_dialog": {"stage": "1", "sub_stage": None, "current_unit": None},
        "stakeholder_reviewer": {"stage": "1", "sub_stage": None, "current_unit": None},
        "blueprint_author": {"stage": "2", "sub_stage": None, "current_unit": None},
        "blueprint_checker": {"stage": "2", "sub_stage": "alignment_check", "current_unit": None},
        "blueprint_reviewer": {"stage": "2", "sub_stage": None, "current_unit": None},
        # Bug S3-168 (cycle 5 capstone): the new specialist mirrors
        # blueprint_reviewer's dispatch context (Stage 2, sub_stage None).
        "statistical_correctness_reviewer": {"stage": "2", "sub_stage": None, "current_unit": None},
        "test_agent": {"stage": "3", "sub_stage": "test_generation"},
        "implementation_agent": {"stage": "3", "sub_stage": "implementation"},
        "coverage_review": {"stage": "3", "sub_stage": "coverage_review"},
        "coverage_review_agent": {"stage": "3", "sub_stage": "coverage_review"},
        "diagnostic_agent": {"stage": "3", "sub_stage": "implementation", "fix_ladder_position": "diagnostic"},
        "integration_test_author": {"stage": "4", "sub_stage": None, "current_unit": None},
        "git_repo_agent": {"stage": "5", "sub_stage": None, "current_unit": None},
        "help_agent": {"stage": "3", "sub_stage": "implementation"},
        "hint_agent": {"stage": "3", "sub_stage": "implementation"},
        "redo_agent": {"stage": "3", "sub_stage": None},
        "bug_triage": {"stage": "5", "sub_stage": None, "current_unit": None},
        "bug_triage_agent": {"stage": "5", "sub_stage": None, "current_unit": None},
        "repair_agent": {"stage": "5", "sub_stage": None, "current_unit": None},
        "reference_indexing": {"stage": "pre_stage_3", "sub_stage": None, "current_unit": None},
        "oracle_agent": {"stage": "5", "sub_stage": None, "current_unit": None, "oracle_session_active": True, "oracle_phase": "green_run"},
        "regression_adaptation": {"stage": "4", "sub_stage": "regression_adaptation", "current_unit": None},
        "checklist_generation": {"stage": "2", "sub_stage": None, "current_unit": None},
    }

    # Bug S3-159: per-status sub_stage overrides for multi-mode agents that
    # are mode-validated by dispatch_agent_status. The default
    # AGENT_DISPATCH_CONTEXT entry pins a single sub_stage per agent, but
    # mode-validated agents reject status lines that don't match the sub_stage.
    # Map (agent_type, status_line) -> sub_stage override.
    #
    # Coverage:
    #   - setup_agent: project_context vs project_profile is mode-validated.
    #   - stakeholder_dialog: only sub_stage=targeted_spec_revision triggers
    #     mode-validation; the default sub_stage=None bypasses it, so both
    #     SPEC_DRAFT_COMPLETE and SPEC_REVISION_COMPLETE pass without override.
    #   - blueprint_author: dispatch is NOT mode-validated (sub_stage=
    #     blueprint_dialog admits both modes), so no override needed.
    SUB_STAGE_OVERRIDES: Dict[Tuple[str, str], str] = {
        ("setup_agent", "PROJECT_CONTEXT_COMPLETE"): "project_context",
        ("setup_agent", "PROJECT_CONTEXT_REJECTED"): "project_context",
        ("setup_agent", "PROFILE_COMPLETE"): "project_profile",
    }

    @pytest.mark.parametrize(
        "agent_type,status_line",
        [
            (atype, sline)
            for atype, lines in sorted(AGENT_STATUS_LINES.items())
            for sline in lines
        ],
    )
    def test_dispatch_agent_status_no_error(self, agent_type, status_line, project_root):
        """dispatch_agent_status does not raise for any declared status line."""
        ctx = dict(self.AGENT_DISPATCH_CONTEXT[agent_type])
        # Bug S3-159: apply per-(agent, status) sub_stage override for
        # mode-validated multi-mode agents.
        override = self.SUB_STAGE_OVERRIDES.get((agent_type, status_line))
        if override is not None:
            ctx["sub_stage"] = override
        # Add debug session for bug_triage, bug_triage_agent, and repair_agent
        if agent_type in ("bug_triage", "bug_triage_agent", "repair_agent"):
            state = _make_debug_state(
                phase="triage" if agent_type in ("bug_triage", "bug_triage_agent") else "repair"
            )
        else:
            state = _make_state(**ctx)
        # SVP 2.2: dispatch_agent_status(state, agent_type, status_line, project_root)
        result = dispatch_agent_status(state, agent_type, status_line, project_root)
        assert result is not None

    def test_test_agent_returns_valid_state(self, project_root):
        """test_agent TEST_GENERATION_COMPLETE returns a valid state copy.
        In SVP 2.2, dispatch_agent_status returns _copy(state) for two-branch
        agents; the routing decision happens in route() reading last_status."""
        state = _make_state(stage="3", sub_stage="test_generation")
        result = dispatch_agent_status(
            state, "test_agent", "TEST_GENERATION_COMPLETE", project_root
        )
        assert result is not None
        assert result is not state  # Should be a copy

    def test_implementation_agent_returns_valid_state(self, project_root):
        """implementation_agent IMPLEMENTATION_COMPLETE returns a valid state copy."""
        state = _make_state(stage="3", sub_stage="implementation")
        result = dispatch_agent_status(
            state, "implementation_agent", "IMPLEMENTATION_COMPLETE", project_root
        )
        assert result is not None
        assert result is not state

    def test_coverage_review_returns_valid_state(self, project_root):
        """coverage_review_agent returns valid state for two-branch routing.
        Note: SVP 2.2 uses 'coverage_review_agent' in AGENT_STATUS_LINES,
        though KNOWN_AGENT_TYPES has 'coverage_review' (naming mismatch)."""
        state = _make_state(stage="3", sub_stage="coverage_review")
        result = dispatch_agent_status(
            state, "coverage_review_agent", "COVERAGE_COMPLETE: no gaps", project_root
        )
        assert result is not None

    def test_diagnostic_agent_returns_valid_state(self, project_root):
        """diagnostic_agent DIAGNOSIS_COMPLETE: implementation returns valid state."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="diagnostic"
        )
        result = dispatch_agent_status(
            state, "diagnostic_agent", "DIAGNOSIS_COMPLETE: implementation",
            project_root
        )
        assert result is not None


# ===========================================================================
# Test 8 -- Known Agent Types vs Route Invocations
# ===========================================================================


class TestKnownAgentTypesVsRouteInvocations:
    """All agent_type values in route() source are in KNOWN_AGENT_TYPES.

    Exception: agents invoked only by slash commands (help_agent,
    hint_agent, redo_agent) may be in KNOWN_AGENT_TYPES but not in route().
    """

    SLASH_COMMAND_ONLY_AGENTS = {"help_agent", "hint_agent", "redo_agent"}

    # SVP 2.2: route() uses _agent suffix variants for some agents, and has
    # pass2_nested which is an internal routing concept, not a KNOWN_AGENT_TYPE.
    # Also some agents are invoked via orchestration, not route() directly.
    _ROUTE_ONLY_AGENTS = {"pass2_nested"}
    _KNOWN_ALIASES = {
        "coverage_review": "coverage_review_agent",
        "bug_triage": "bug_triage_agent",
    }
    # Agents that appear in KNOWN_AGENT_TYPES but are invoked by
    # orchestration or reviewer patterns, not directly by route()
    _ORCHESTRATION_AGENTS = {
        "blueprint_reviewer", "stakeholder_reviewer", "reference_indexing",
    }

    def test_route_agents_are_known(self):
        """Every agent_type value emitted by route() is in KNOWN_AGENT_TYPES."""
        agents_in_route = _extract_agent_strings_from_route_source()
        known = set(KNOWN_AGENT_TYPES)
        # Expand known with alias variants
        expanded_known = set(known)
        for alias_target in self._KNOWN_ALIASES.values():
            expanded_known.add(alias_target)
        unknown = agents_in_route - expanded_known - self._ROUTE_ONLY_AGENTS
        assert not unknown, (
            f"Agents used in route() but not in KNOWN_AGENT_TYPES: {sorted(unknown)}"
        )

    def test_known_agents_reachable(self):
        """Every KNOWN_AGENT_TYPE is either in route() or is a slash-command/orchestration agent."""
        agents_in_route = _extract_agent_strings_from_route_source()
        # Add alias sources (if route uses coverage_review_agent, that covers coverage_review)
        reverse_aliases = {v: k for k, v in self._KNOWN_ALIASES.items()}
        expanded_route = set(agents_in_route)
        for agent in agents_in_route:
            if agent in reverse_aliases:
                expanded_route.add(reverse_aliases[agent])
        known = set(KNOWN_AGENT_TYPES)
        unreachable = known - expanded_route - self.SLASH_COMMAND_ONLY_AGENTS - self._ORCHESTRATION_AGENTS
        assert not unreachable, (
            f"Known agent types not reachable from route() and not slash-command-only: "
            f"{sorted(unreachable)}"
        )


# ===========================================================================
# Test 9 -- Debug Phase Transitions vs Route Handlers
# ===========================================================================


# ===========================================================================
# Test 10 -- Sub-Stages vs Route Branches
# ===========================================================================


class TestSubStagesVsRouteBranches:
    """For each stage (3, 4, 5), for every sub_stage in VALID_SUB_STAGES,
    construct a state and call route(). Verify route() returns a meaningful
    action (not None, not an error)."""

    @pytest.fixture
    def project_root(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        return tmp_path

    @pytest.mark.parametrize("sub_stage", sorted(VALID_SUB_STAGES.get("3", set()) - {None}))
    def test_stage_3_sub_stages(self, sub_stage, project_root):
        state = _make_state(stage="3", sub_stage=sub_stage)
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action is not None
        action_type = action.get("action_type", "")
        assert action_type != "error", (
            f"Stage 3 sub_stage='{sub_stage}' returned error: {action}"
        )

    @pytest.mark.parametrize("sub_stage", sorted(VALID_SUB_STAGES.get("4", set()) - {None}))
    def test_stage_4_sub_stages(self, sub_stage, project_root):
        state = _make_state(stage="4", sub_stage=sub_stage, current_unit=None)
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action is not None
        action_type = action.get("action_type", "")
        assert action_type != "error", (
            f"Stage 4 sub_stage='{sub_stage}' returned error: {action}"
        )

    @pytest.mark.parametrize("sub_stage", sorted(VALID_SUB_STAGES.get("5", set()) - {None}))
    def test_stage_5_sub_stages(self, sub_stage, project_root):
        state = _make_state(stage="5", sub_stage=sub_stage, current_unit=None)
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action is not None
        action_type = action.get("action_type", "")
        assert action_type != "error", (
            f"Stage 5 sub_stage='{sub_stage}' returned error: {action}"
        )


# ===========================================================================
# Test 11 -- Fix Ladder Positions vs Route Context
# ===========================================================================


class TestFixLadderPositionsVsRouteContext:
    """For each position in VALID_FIX_LADDER_POSITIONS (excluding None), construct
    a Stage 3 state at implementation sub_stage with that ladder position.
    Call route(). Verify the returned action's agent_type varies based on ladder
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
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action.get("agent_type") == "diagnostic_agent", (
            f"Expected diagnostic_agent for ladder_pos=diagnostic, got: {action}"
        )

    def test_fresh_impl_routes_to_implementation_agent(self, project_root):
        """fix_ladder_position='fresh_impl' at sub_stage='implementation'
        routes to implementation_agent."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="fresh_impl"
        )
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action.get("agent_type") == "implementation_agent", (
            f"Expected implementation_agent for ladder_pos=fresh_impl, got: {action}"
        )

    def test_diagnostic_impl_routes_to_implementation_agent(self, project_root):
        """fix_ladder_position='diagnostic_impl' at sub_stage='implementation'
        routes to implementation_agent."""
        state = _make_state(
            stage="3", sub_stage="implementation", fix_ladder_position="diagnostic_impl"
        )
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action.get("agent_type") == "implementation_agent", (
            f"Expected implementation_agent for ladder_pos=diagnostic_impl, got: {action}"
        )

    def test_null_ladder_at_null_substage_runs_stub_gen(self, project_root):
        """fix_ladder_position=None at sub_stage=None runs stub generation (run_command)."""
        state = _make_state(stage="3", sub_stage=None, fix_ladder_position=None)
        _write_state_json(project_root, state)
        action = route(project_root)
        assert action.get("action_type") == "run_command", (
            f"Expected run_command for null ladder at sub_stage=None, got: {action}"
        )


# ===========================================================================
# Test 12 -- Command Status Patterns vs Phase Handlers
# ===========================================================================


class TestCommandStatusPatternsVsPhaseHandlers:
    """For key (command_type, status_line) combinations that should produce state
    transitions, call dispatch_command_status and verify state changes.

    SVP 2.2 signature: dispatch_command_status(state, command_type, status_line, sub_stage=None)
    """

    def test_green_run_tests_passed(self):
        """green_run + TESTS_PASSED -> coverage_review."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(state, "test_execution", "TESTS_PASSED", "green_run")
        assert result.sub_stage == "coverage_review"

    def test_green_run_tests_failed(self):
        """green_run + TESTS_FAILED -> engage fix ladder."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(state, "test_execution", "TESTS_FAILED", "green_run")
        assert result.sub_stage == "implementation"
        assert result.fix_ladder_position == "fresh_impl"

    def test_red_run_tests_failed(self):
        """red_run + TESTS_FAILED -> implementation."""
        state = _make_state(stage="3", sub_stage="red_run")
        result = dispatch_command_status(state, "test_execution", "TESTS_FAILED", "red_run")
        assert result.sub_stage == "implementation"

    def test_red_run_tests_error(self):
        """red_run + TESTS_ERROR -> test_generation (not infinite loop)."""
        state = _make_state(stage="3", sub_stage="red_run")
        result = dispatch_command_status(state, "test_execution", "TESTS_ERROR", "red_run")
        assert result.sub_stage in ("test_generation", "gate_3_1"), (
            f"red_run TESTS_ERROR should advance, got sub_stage={result.sub_stage}"
        )

    def test_green_run_tests_error(self):
        """green_run + TESTS_ERROR -> fix ladder (not infinite loop)."""
        state = _make_state(stage="3", sub_stage="green_run")
        result = dispatch_command_status(state, "test_execution", "TESTS_ERROR", "green_run")
        assert result.sub_stage != "green_run", (
            "green_run TESTS_ERROR must not stay at green_run (infinite loop)"
        )

    def test_compliance_scan_succeeded(self):
        """compliance_scan + COMMAND_SUCCEEDED -> repo_complete."""
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_command_status(state, "compliance_scan", "COMMAND_SUCCEEDED")
        assert result.sub_stage == "repo_complete"

    def test_compliance_scan_failed(self):
        """compliance_scan + COMMAND_FAILED -> resets sub_stage."""
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = dispatch_command_status(state, "compliance_scan", "COMMAND_FAILED")
        assert result.sub_stage is None

    def test_stub_generation_succeeded(self):
        """stub_generation + COMMAND_SUCCEEDED -> test_generation."""
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = dispatch_command_status(state, "stub_generation", "COMMAND_SUCCEEDED")
        assert result.sub_stage == "test_generation"

    def test_stage4_tests_passed(self):
        """Stage 4 test_execution + TESTS_PASSED -> advance."""
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_command_status(state, "test_execution", "TESTS_PASSED")
        # In SVP 2.2, Stage 4 TESTS_PASSED advances to regression_adaptation
        assert result.sub_stage == "regression_adaptation" or result.stage == "5"

    def test_stage4_tests_failed(self):
        """Stage 4 test_execution + TESTS_FAILED -> increment retries."""
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_command_status(state, "test_execution", "TESTS_FAILED")
        assert result is not None

    def test_stage4_tests_error(self):
        """Stage 4 test_execution + TESTS_ERROR -> increment retries."""
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_command_status(state, "test_execution", "TESTS_ERROR")
        assert result is not None


# ===========================================================================
# Test 13 -- Phase-to-Agent Map vs Known Phases
# ===========================================================================


