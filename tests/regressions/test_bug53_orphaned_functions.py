"""Regression test for Bug 53: Orphaned functions removed.

Verifies that the three dead-code functions (reset_fix_ladder,
reset_alignment_iteration, record_pass_end) do NOT exist in
state_transitions, and that restart_from_stage and complete_unit
handle their behavior inline.

SVP 2.2 adaptation:
- state_transitions module is scripts/state_transitions.py
- PipelineState from src.unit_5.stub (alignment_iterations field, no alignment_iteration)
- restart_from_stage(state, target_stage) takes 2 args (no reason/project_root)
- complete_unit(state) takes 1 arg (state must have sub_stage=unit_completion)
"""

import ast
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from src.unit_5.stub import PipelineState
from src.unit_6.stub import restart_from_stage, complete_unit


class TestOrphanedFunctionsRemoved:
    """The three orphaned functions must not exist."""

    def test_reset_fix_ladder_not_importable(self):
        import state_transitions

        assert not hasattr(state_transitions, "reset_fix_ladder"), (
            "reset_fix_ladder should have been removed"
        )

    def test_reset_alignment_iteration_not_importable(self):
        import state_transitions

        assert not hasattr(state_transitions, "reset_alignment_iteration"), (
            "reset_alignment_iteration should have been removed"
        )

    def test_record_pass_end_not_importable(self):
        import state_transitions

        assert not hasattr(state_transitions, "record_pass_end"), (
            "record_pass_end should have been removed"
        )

    def test_functions_not_in_source_ast(self):
        """Parse state_transitions.py source to confirm
        the functions are not defined."""
        import state_transitions
        import inspect

        source_file = Path(inspect.getfile(state_transitions))
        tree = ast.parse(source_file.read_text())
        func_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        for name in [
            "reset_fix_ladder",
            "reset_alignment_iteration",
            "record_pass_end",
        ]:
            assert name not in func_names, (
                f"{name} should have been removed from state_transitions.py"
            )

    def test_not_imported_by_routing_ast(self):
        """Parse routing.py to confirm these names
        are not imported."""
        import routing
        import inspect

        source_file = Path(inspect.getfile(routing))
        tree = ast.parse(source_file.read_text())
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.name)
        for name in [
            "reset_fix_ladder",
            "reset_alignment_iteration",
            "record_pass_end",
        ]:
            assert name not in imported_names, (
                f"{name} should not be imported by routing.py"
            )


class TestBehaviorHandledInline:
    """restart_from_stage and complete_unit handle the
    behavior that these functions provided."""

    def test_restart_from_stage_resets_fix_ladder(self):
        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            total_units=5,
            fix_ladder_position="fresh_impl",
        )
        result = restart_from_stage(state, "2")
        assert result.fix_ladder_position is None

    def test_restart_from_stage_resets_alignment_iterations(self):
        state = PipelineState(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            total_units=5,
            alignment_iterations=2,
        )
        result = restart_from_stage(state, "2")
        assert result.alignment_iterations == 0

    def test_complete_unit_resets_fix_ladder(self):
        state = PipelineState(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=3,
            fix_ladder_position="diagnostic",
        )
        result = complete_unit(state)
        assert result.fix_ladder_position is None
