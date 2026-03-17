"""Regression test for Bug 54: Orphaned hollow function update_state_from_status removed.

Verifies that update_state_from_status does NOT exist in state_transitions
or routing imports, and that update_state_main calls dispatch_status directly.
"""

import ast
from pathlib import Path


class TestUpdateStateFromStatusRemoved:
    """update_state_from_status must not exist anywhere."""

    def test_not_in_state_transitions(self):
        import state_transitions

        assert not hasattr(state_transitions, "update_state_from_status"), (
            "update_state_from_status should have been removed "
            "from state_transitions"
        )

    def test_not_in_state_transitions_ast(self):
        """Parse state_transitions.py to confirm the function
        is not defined there."""
        st_path = (
            Path(__file__).resolve().parents[2]
            / "svp"
            / "scripts"
            / "state_transitions.py"
        )
        if not st_path.exists():
            return
        tree = ast.parse(st_path.read_text())
        func_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        assert "update_state_from_status" not in func_names, (
            "update_state_from_status should have been removed "
            "from state_transitions.py"
        )

    def test_not_imported_by_routing(self):
        """Parse routing.py to confirm the name is not imported."""
        routing_path = (
            Path(__file__).resolve().parents[2]
            / "svp"
            / "scripts"
            / "routing.py"
        )
        if not routing_path.exists():
            return
        tree = ast.parse(routing_path.read_text())
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.name)
        assert "update_state_from_status" not in imported_names, (
            "update_state_from_status should not be imported by routing.py"
        )


class TestUpdateStateMainCallsDispatchStatus:
    """update_state_main must call dispatch_status directly."""

    def test_dispatch_status_called_in_update_state_main(self):
        """Parse routing.py AST to confirm update_state_main calls
        dispatch_status."""
        routing_path = (
            Path(__file__).resolve().parents[2]
            / "svp"
            / "scripts"
            / "routing.py"
        )
        if not routing_path.exists():
            return
        tree = ast.parse(routing_path.read_text())

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "update_state_main"
            ):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Name) and func.id == "dispatch_status":
                            return  # found it
                raise AssertionError(
                    "update_state_main does not call dispatch_status"
                )
        raise AssertionError("update_state_main not found in routing.py")
