"""Regression test for Bug 53: Orphaned functions removed.

Verifies that the three dead-code functions (reset_fix_ladder,
reset_alignment_iteration, record_pass_end) do NOT exist in
state_transitions, and that restart_from_stage and complete_unit
handle their behavior inline.
"""

import ast
from pathlib import Path


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

    def test_restart_from_stage_resets_fix_ladder(self, tmp_path):
        from state_transitions import restart_from_stage
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="3",
            current_unit=2,
            fix_ladder_position="fresh_test",
        )
        result = restart_from_stage(state, "2", "test", tmp_path)
        assert result.fix_ladder_position is None

    def test_restart_from_stage_resets_alignment_iteration(self, tmp_path):
        from state_transitions import restart_from_stage
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="3",
            current_unit=2,
            alignment_iteration=2,
        )
        result = restart_from_stage(state, "2", "test", tmp_path)
        assert result.alignment_iteration == 0

    def test_restart_from_stage_records_pass_history(self, tmp_path):
        from state_transitions import restart_from_stage
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="3",
            current_unit=2,
            pass_history=[],
        )
        result = restart_from_stage(state, "2", "blueprint revision", tmp_path)
        assert len(result.pass_history) == 1
        assert result.pass_history[0]["ended_reason"] == "blueprint revision"

    def test_complete_unit_resets_fix_ladder(self, tmp_path):
        from state_transitions import complete_unit
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="3",
            current_unit=1,
            total_units=3,
            fix_ladder_position="diagnostic",
        )
        result = complete_unit(state, 1, tmp_path)
        assert result.fix_ladder_position is None
