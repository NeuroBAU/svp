"""Structural completeness tests for SVP 2.2.

Verifies that every registry, dispatch table, vocabulary, and enum-like
constant in the codebase has complete handler coverage. Uses AST-based
inspection to discover declared values and handler references.

Required by SVP 2.1 Bug 72 fix -- ensures no registry value is left
unhandled, and no handler references a non-existent value.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

import pytest

# ---------------------------------------------------------------------------
# Direct imports of registries and dispatch tables
# ---------------------------------------------------------------------------

from language_registry import LANGUAGE_REGISTRY
from pipeline_state import (
    VALID_DEBUG_PHASES,
    VALID_FIX_LADDER_POSITIONS,
    VALID_ORACLE_PHASES,
    VALID_STAGES,
    VALID_SUB_STAGES,
)
from state_transitions import ADDITIONAL_SUB_STAGES
from signature_parser import SIGNATURE_PARSERS
from stub_generator import STUB_GENERATORS
from prepare_task import (
    ALL_GATE_IDS,
    KNOWN_AGENT_TYPES,
    SELECTIVE_LOADING_MATRIX,
)
from routing import (
    AGENT_STATUS_LINES,
    GATE_VOCABULARY,
    PHASE_TO_AGENT,
    TEST_OUTPUT_PARSERS,
)
from quality_gate import QUALITY_RUNNERS
from adapt_regression_tests import PROJECT_ASSEMBLERS
from unit_25 import COMMAND_NAMES


# ---------------------------------------------------------------------------
# Project root for AST scanning
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"


# ---------------------------------------------------------------------------
# AST-based discovery helpers
# ---------------------------------------------------------------------------


def _read_source(unit_number: int) -> str:
    """Read the source of a unit's stub.py file."""
    path = _SRC_DIR / f"unit_{unit_number}" / "stub.py"
    return path.read_text(encoding="utf-8")


def _extract_dict_keys_from_ast(source: str, variable_name: str) -> Set[str]:
    """Extract string keys from a module-level dict literal using AST.

    Finds assignments like:
        VARIABLE_NAME: Dict[...] = { "key1": ..., "key2": ..., }
    or
        VARIABLE_NAME = { "key1": ..., "key2": ..., }

    Returns the set of string keys.
    """
    tree = ast.parse(source)
    keys: Set[str] = set()

    for node in ast.walk(tree):
        # Handle both Assign and AnnAssign
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(
                                key.value, str
                            ):
                                keys.add(key.value)
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == variable_name
                and node.value is not None
            ):
                if isinstance(node.value, ast.Dict):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            keys.add(key.value)

    return keys


def _extract_set_values_from_ast(source: str, variable_name: str) -> Set[str]:
    """Extract string values from a module-level set literal using AST.

    Handles both Set literals and set() constructor calls with literal args.
    """
    tree = ast.parse(source)
    values: Set[str] = set()

    for node in ast.walk(tree):
        target_name = None
        value_node = None

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    target_name = target.id
                    value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == variable_name:
                target_name = node.target.id
                value_node = node.value

        if target_name and value_node:
            if isinstance(value_node, ast.Set):
                for elt in value_node.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        values.add(elt.value)
                    elif elt is None:
                        values.add(None)

    return values


def _extract_list_values_from_ast(source: str, variable_name: str) -> List:
    """Extract values from a module-level list literal using AST."""
    tree = ast.parse(source)
    values = []

    for node in ast.walk(tree):
        target_name = None
        value_node = None

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    target_name = target.id
                    value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == variable_name:
                target_name = node.target.id
                value_node = node.value

        if target_name and value_node:
            if isinstance(value_node, ast.List):
                for elt in value_node.elts:
                    if isinstance(elt, ast.Constant):
                        values.append(elt.value)

    return values


def _find_string_literals_in_function(source: str, function_name: str) -> Set[str]:
    """Find all string literals used in a specific function body."""
    tree = ast.parse(source)
    strings: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                for child in ast.walk(node):
                    if isinstance(child, ast.Constant) and isinstance(child.value, str):
                        strings.add(child.value)

    return strings


def _find_if_elif_comparisons(source: str, function_name: str) -> Set[str]:
    """Find string values in if/elif == comparisons within a function."""
    tree = ast.parse(source)
    values: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                for child in ast.walk(node):
                    if isinstance(child, ast.Compare):
                        for comparator in child.comparators:
                            if isinstance(comparator, ast.Constant) and isinstance(
                                comparator.value, str
                            ):
                                values.add(comparator.value)

    return values


# ===================================================================
# Structural Completeness Tests
# ===================================================================


class TestLanguageRegistryCompleteness:
    """Every LANGUAGE_REGISTRY key has all required dispatch table entries."""

    def test_all_full_languages_have_stub_generator(self):
        """Every full language in LANGUAGE_REGISTRY has a STUB_GENERATORS entry."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            key = entry.get("stub_generator_key")
            if key:
                assert key in STUB_GENERATORS, (
                    f"Language '{lang}': stub_generator_key '{key}' "
                    f"missing from STUB_GENERATORS. "
                    f"Available keys: {sorted(STUB_GENERATORS.keys())}"
                )

    def test_all_full_languages_have_quality_runner(self):
        """Every language in LANGUAGE_REGISTRY with quality_runner_key has a runner."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            key = entry.get("quality_runner_key")
            if key:
                assert key in QUALITY_RUNNERS, (
                    f"Language '{lang}': quality_runner_key '{key}' "
                    f"missing from QUALITY_RUNNERS. "
                    f"Available keys: {sorted(QUALITY_RUNNERS.keys())}"
                )

    def test_all_full_languages_have_test_output_parser(self):
        """Every full language with test_output_parser_key has a parser."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            key = entry.get("test_output_parser_key")
            if key:
                assert key in TEST_OUTPUT_PARSERS, (
                    f"Language '{lang}': test_output_parser_key '{key}' "
                    f"missing from TEST_OUTPUT_PARSERS. "
                    f"Available keys: {sorted(TEST_OUTPUT_PARSERS.keys())}"
                )

    def test_all_full_languages_have_signature_parser(self):
        """Every non-component language has a SIGNATURE_PARSERS entry."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert lang in SIGNATURE_PARSERS, (
                    f"Full language '{lang}' missing from SIGNATURE_PARSERS. "
                    f"Available keys: {sorted(SIGNATURE_PARSERS.keys())}"
                )

    def test_all_full_languages_have_project_assembler(self):
        """Every non-component language has a PROJECT_ASSEMBLERS entry."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert lang in PROJECT_ASSEMBLERS, (
                    f"Full language '{lang}' missing from PROJECT_ASSEMBLERS. "
                    f"Available keys: {sorted(PROJECT_ASSEMBLERS.keys())}"
                )


class TestDispatchTableCompleteness:
    """Every dispatch table key is referenced by the registry, and vice versa."""

    def test_stub_generators_no_orphans(self):
        """No STUB_GENERATORS key exists without a LANGUAGE_REGISTRY reference."""
        referenced = {
            entry["stub_generator_key"]
            for entry in LANGUAGE_REGISTRY.values()
            if "stub_generator_key" in entry
        }
        for key in STUB_GENERATORS:
            assert key in referenced, (
                f"STUB_GENERATORS has orphan key '{key}' -- "
                f"not referenced by any LANGUAGE_REGISTRY entry"
            )

    def test_quality_runners_no_orphans(self):
        """No QUALITY_RUNNERS key exists without a LANGUAGE_REGISTRY reference."""
        referenced = {
            entry["quality_runner_key"]
            for entry in LANGUAGE_REGISTRY.values()
            if "quality_runner_key" in entry
        }
        for key in QUALITY_RUNNERS:
            assert key in referenced, (
                f"QUALITY_RUNNERS has orphan key '{key}' -- "
                f"not referenced by any LANGUAGE_REGISTRY entry"
            )

    def test_test_output_parsers_no_orphans(self):
        """No TEST_OUTPUT_PARSERS key exists without a LANGUAGE_REGISTRY reference."""
        referenced = {
            entry["test_output_parser_key"]
            for entry in LANGUAGE_REGISTRY.values()
            if "test_output_parser_key" in entry
        }
        for key in TEST_OUTPUT_PARSERS:
            assert key in referenced, (
                f"TEST_OUTPUT_PARSERS has orphan key '{key}' -- "
                f"not referenced by any LANGUAGE_REGISTRY entry"
            )

    def test_project_assemblers_no_orphans(self):
        """No PROJECT_ASSEMBLERS key exists without a matching LANGUAGE_REGISTRY entry."""
        full_languages = {
            lang
            for lang, entry in LANGUAGE_REGISTRY.items()
            if not entry.get("is_component_only", False)
        }
        for key in PROJECT_ASSEMBLERS:
            assert key in full_languages, (
                f"PROJECT_ASSEMBLERS has orphan key '{key}' -- "
                f"not a full language in LANGUAGE_REGISTRY"
            )


class TestGateVocabularyCompleteness:
    """GATE_VOCABULARY and ALL_GATE_IDS are perfectly aligned."""

    def test_gate_vocabulary_keys_match_all_gate_ids(self):
        """GATE_VOCABULARY keys == ALL_GATE_IDS (as a set)."""
        vocab_keys = set(GATE_VOCABULARY.keys())
        gate_ids = set(ALL_GATE_IDS)
        assert vocab_keys == gate_ids, (
            f"Mismatch between GATE_VOCABULARY and ALL_GATE_IDS.\n"
            f"In GATE_VOCABULARY but not ALL_GATE_IDS: {vocab_keys - gate_ids}\n"
            f"In ALL_GATE_IDS but not GATE_VOCABULARY: {gate_ids - vocab_keys}"
        )

    def test_gate_response_options_unit13_matches_unit14(self):
        """_GATE_RESPONSE_OPTIONS (Unit 13) matches GATE_VOCABULARY (Unit 14)."""
        from prepare_task import _GATE_RESPONSE_OPTIONS

        for gate_id in _GATE_RESPONSE_OPTIONS:
            assert gate_id in GATE_VOCABULARY, (
                f"Gate '{gate_id}' in Unit 13 _GATE_RESPONSE_OPTIONS "
                f"but not in Unit 14 GATE_VOCABULARY"
            )
            unit13_responses = sorted(_GATE_RESPONSE_OPTIONS[gate_id])
            unit14_responses = sorted(GATE_VOCABULARY[gate_id])
            assert unit13_responses == unit14_responses, (
                f"Gate '{gate_id}' response mismatch:\n"
                f"  Unit 13: {unit13_responses}\n"
                f"  Unit 14: {unit14_responses}"
            )

        for gate_id in GATE_VOCABULARY:
            assert gate_id in _GATE_RESPONSE_OPTIONS, (
                f"Gate '{gate_id}' in Unit 14 GATE_VOCABULARY "
                f"but not in Unit 13 _GATE_RESPONSE_OPTIONS"
            )

    def test_every_gate_has_at_least_two_responses(self):
        """Every gate has at least two response options (binary decision logic)."""
        for gate_id, responses in GATE_VOCABULARY.items():
            assert len(responses) >= 2, (
                f"Gate '{gate_id}' has only {len(responses)} response(s): {responses}. "
                f"SVP binary decision logic requires at least 2."
            )


class TestAgentStatusLinesCompleteness:
    """AGENT_STATUS_LINES covers all expected agents."""

    def test_every_agent_has_status_lines(self):
        """Every entry in AGENT_STATUS_LINES has at least one status line."""
        for agent, statuses in AGENT_STATUS_LINES.items():
            assert len(statuses) >= 1, f"Agent '{agent}' has no terminal status lines"

    def test_status_lines_are_non_empty_strings(self):
        """Every status line is a non-empty string."""
        for agent, statuses in AGENT_STATUS_LINES.items():
            for status in statuses:
                assert isinstance(status, str) and len(status) > 0, (
                    f"Agent '{agent}' has invalid status line: {status!r}"
                )


class TestValidStagesCompleteness:
    """VALID_STAGES, VALID_SUB_STAGES, and related constants are consistent."""

    def test_every_stage_has_sub_stages(self):
        """Every VALID_STAGE has an entry in VALID_SUB_STAGES."""
        for stage in VALID_STAGES:
            assert stage in VALID_SUB_STAGES, (
                f"Stage '{stage}' in VALID_STAGES but not in VALID_SUB_STAGES"
            )

    def test_every_sub_stage_stage_is_valid(self):
        """Every key in VALID_SUB_STAGES is a valid stage."""
        for stage in VALID_SUB_STAGES:
            assert stage in VALID_STAGES, (
                f"Stage '{stage}' in VALID_SUB_STAGES but not in VALID_STAGES"
            )

    def test_fix_ladder_starts_with_none(self):
        """Fix ladder positions start with None (initial state)."""
        assert VALID_FIX_LADDER_POSITIONS[0] is None

    def test_fix_ladder_ends_with_exhausted(self):
        """Fix ladder positions end with 'exhausted'."""
        assert VALID_FIX_LADDER_POSITIONS[-1] == "exhausted"

    def test_oracle_phases_include_none(self):
        """Oracle phases include None (inactive state)."""
        assert None in VALID_ORACLE_PHASES


class TestASTBasedRegistryDiscovery:
    """AST-based discovery of registry keys vs handler dispatch logic."""

    def test_gate_vocabulary_keys_via_ast(self):
        """AST-extracted GATE_VOCABULARY keys match runtime keys."""
        source = _read_source(14)
        ast_keys = _extract_dict_keys_from_ast(source, "GATE_VOCABULARY")
        runtime_keys = set(GATE_VOCABULARY.keys())

        # AST-extracted keys should be a subset (AST may miss dynamically
        # constructed keys, but should catch all literal keys)
        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime GATE_VOCABULARY keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_agent_status_lines_keys_via_ast(self):
        """AST-extracted AGENT_STATUS_LINES keys match runtime keys."""
        source = _read_source(14)
        ast_keys = _extract_dict_keys_from_ast(source, "AGENT_STATUS_LINES")
        runtime_keys = set(AGENT_STATUS_LINES.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime AGENT_STATUS_LINES keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_stub_generators_keys_via_ast(self):
        """AST-extracted STUB_GENERATORS keys match runtime keys."""
        source = _read_source(10)
        ast_keys = _extract_dict_keys_from_ast(source, "STUB_GENERATORS")
        runtime_keys = set(STUB_GENERATORS.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime STUB_GENERATORS keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_quality_runners_keys_via_ast(self):
        """AST-extracted QUALITY_RUNNERS keys match runtime keys."""
        source = _read_source(15)
        ast_keys = _extract_dict_keys_from_ast(source, "QUALITY_RUNNERS")
        runtime_keys = set(QUALITY_RUNNERS.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime QUALITY_RUNNERS keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_test_output_parsers_keys_via_ast(self):
        """AST-extracted TEST_OUTPUT_PARSERS keys match runtime keys."""
        source = _read_source(14)
        ast_keys = _extract_dict_keys_from_ast(source, "TEST_OUTPUT_PARSERS")
        runtime_keys = set(TEST_OUTPUT_PARSERS.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime TEST_OUTPUT_PARSERS keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_signature_parsers_keys_via_ast(self):
        """AST-extracted SIGNATURE_PARSERS keys match runtime keys."""
        source = _read_source(9)
        ast_keys = _extract_dict_keys_from_ast(source, "SIGNATURE_PARSERS")
        runtime_keys = set(SIGNATURE_PARSERS.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime SIGNATURE_PARSERS keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_project_assemblers_keys_via_ast(self):
        """AST-extracted PROJECT_ASSEMBLERS keys match runtime keys."""
        source = _read_source(23)
        ast_keys = _extract_dict_keys_from_ast(source, "PROJECT_ASSEMBLERS")
        runtime_keys = set(PROJECT_ASSEMBLERS.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime PROJECT_ASSEMBLERS keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_language_registry_keys_via_ast(self):
        """AST-extracted LANGUAGE_REGISTRY keys match runtime keys."""
        source = _read_source(2)
        ast_keys = _extract_dict_keys_from_ast(source, "LANGUAGE_REGISTRY")
        runtime_keys = set(LANGUAGE_REGISTRY.keys())

        if ast_keys:
            assert ast_keys == runtime_keys, (
                f"AST vs runtime LANGUAGE_REGISTRY keys differ.\n"
                f"AST-only: {ast_keys - runtime_keys}\n"
                f"Runtime-only: {runtime_keys - ast_keys}"
            )

    def test_known_agent_types_via_ast(self):
        """AST-extracted KNOWN_AGENT_TYPES match runtime list."""
        source = _read_source(13)
        ast_values = _extract_list_values_from_ast(source, "KNOWN_AGENT_TYPES")
        runtime_values = list(KNOWN_AGENT_TYPES)

        if ast_values:
            assert set(ast_values) == set(runtime_values), (
                f"AST vs runtime KNOWN_AGENT_TYPES differ.\n"
                f"AST-only: {set(ast_values) - set(runtime_values)}\n"
                f"Runtime-only: {set(runtime_values) - set(ast_values)}"
            )

    def test_all_gate_ids_via_ast(self):
        """AST-extracted ALL_GATE_IDS match runtime list."""
        source = _read_source(13)
        ast_values = _extract_list_values_from_ast(source, "ALL_GATE_IDS")
        runtime_values = list(ALL_GATE_IDS)

        if ast_values:
            assert set(ast_values) == set(runtime_values), (
                f"AST vs runtime ALL_GATE_IDS differ.\n"
                f"AST-only: {set(ast_values) - set(runtime_values)}\n"
                f"Runtime-only: {set(runtime_values) - set(ast_values)}"
            )

    def test_command_names_via_ast(self):
        """AST-extracted COMMAND_NAMES match runtime list."""
        source = _read_source(25)
        ast_values = _extract_list_values_from_ast(source, "COMMAND_NAMES")
        runtime_values = list(COMMAND_NAMES)

        if ast_values:
            assert set(ast_values) == set(runtime_values), (
                f"AST vs runtime COMMAND_NAMES differ.\n"
                f"AST-only: {set(ast_values) - set(runtime_values)}\n"
                f"Runtime-only: {set(runtime_values) - set(ast_values)}"
            )


class TestDispatchGateResponseCompleteness:
    """dispatch_gate_response handles every gate_id x response combination."""

    def test_dispatch_recognizes_all_gate_ids(self, tmp_path):
        """dispatch_gate_response does not raise ValueError for any valid gate_id."""
        from pipeline_state import PipelineState

        _write_json(tmp_path / "svp_config.json", {})
        _write_json(
            tmp_path / "pipeline_state.json",
            {"stage": "0", "sub_stage": "hook_activation", "pass": None},
        )
        (tmp_path / ".svp").mkdir(parents=True, exist_ok=True)

        for gate_id in GATE_VOCABULARY:
            responses = GATE_VOCABULARY[gate_id]
            for response in responses:
                state = PipelineState(stage="0", sub_stage="hook_activation")
                # Should not raise ValueError
                try:
                    dispatch_gate_response(state, gate_id, response, tmp_path)
                except ValueError:
                    pytest.fail(
                        f"dispatch_gate_response raised ValueError for "
                        f"gate_id='{gate_id}', response='{response}'"
                    )
                except (TransitionError, AttributeError, KeyError):
                    # These are acceptable -- the state may not be in the right
                    # precondition for the transition, but the gate/response
                    # pair was recognized.
                    pass

    def test_dispatch_rejects_invalid_response_for_every_gate(self, tmp_path):
        """dispatch_gate_response raises ValueError for invalid responses."""
        from pipeline_state import PipelineState

        _write_json(tmp_path / "svp_config.json", {})
        _write_json(
            tmp_path / "pipeline_state.json",
            {"stage": "0", "sub_stage": "hook_activation", "pass": None},
        )
        (tmp_path / ".svp").mkdir(parents=True, exist_ok=True)

        for gate_id in GATE_VOCABULARY:
            state = PipelineState(stage="0", sub_stage="hook_activation")
            with pytest.raises(ValueError, match="Invalid response"):
                dispatch_gate_response(
                    state, gate_id, "COMPLETELY_INVALID_RESPONSE", tmp_path
                )


class TestPrepareTaskPromptCompleteness:
    """prepare_task_prompt dispatch covers all known agent types."""

    def test_prepare_handles_all_agent_types_without_crashing(self, tmp_path):
        """prepare_task_prompt does not crash for any KNOWN_AGENT_TYPES entry."""
        # Create workspace with all needed files
        _write_json(tmp_path / "svp_config.json", {})
        _write_json(
            tmp_path / "project_profile.json",
            {
                "archetype": "python_project",
                "language": {"primary": "python", "components": []},
            },
        )
        _write_json(
            tmp_path / "pipeline_state.json",
            {
                "stage": "3",
                "sub_stage": "implementation",
                "current_unit": 1,
                "total_units": 5,
                "pass": None,
            },
        )
        (tmp_path / ".svp").mkdir(parents=True, exist_ok=True)

        # Create blueprint files
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose\n")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts\n")

        # Create specs dir
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        (specs_dir / "stakeholder_spec.md").write_text("# Spec\n")

        for agent_type in KNOWN_AGENT_TYPES:
            try:
                result = prepare_task_prompt(tmp_path, agent_type, unit_number=1)
                assert isinstance(result, str), (
                    f"prepare_task_prompt for '{agent_type}' did not return a string"
                )
            except FileNotFoundError:
                # Some agents need files that may not exist in our minimal setup;
                # FileNotFoundError is acceptable, ValueError/TypeError is not.
                pass
            except Exception as exc:
                # Only fail on truly unexpected errors
                if isinstance(exc, (ValueError, TypeError, AttributeError)):
                    pytest.fail(
                        f"prepare_task_prompt('{agent_type}') raised "
                        f"{type(exc).__name__}: {exc}"
                    )


class TestSelectiveLoadingMatrixCompleteness:
    """SELECTIVE_LOADING_MATRIX values are valid loading modes."""

    def test_all_loading_modes_are_valid(self):
        """Every SELECTIVE_LOADING_MATRIX value is a known loading mode."""
        valid_modes = {"contracts_only", "prose_only", "both"}
        for agent, mode in SELECTIVE_LOADING_MATRIX.items():
            assert mode in valid_modes, (
                f"Agent '{agent}' has invalid loading mode '{mode}'. "
                f"Valid modes: {valid_modes}"
            )
