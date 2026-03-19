"""Bug 12 regression: Command scripts must have if __name__ == '__main__' guards.

CLI entry point scripts (cmd_clean.py, cmd_quit.py, cmd_status.py) and
wrapper scripts (run_tests.py, run_quality_gate.py, update_state.py,
prepare_task.py, generate_stubs.py, setup_infrastructure.py) must have
main guards so they don't execute on import.

Note: cmd_save.py is the library module (not a CLI wrapper) and is
excluded from this check.
"""

import ast
from pathlib import Path


def _get_scripts_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "svp" / "scripts"


def _has_main_guard(filepath: Path) -> bool:
    """Check if a Python file has an if __name__ == '__main__' guard."""
    source = filepath.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check for __name__ == "__main__" pattern
            test = node.test
            if isinstance(test, ast.Compare):
                if isinstance(test.left, ast.Name) and test.left.id == "__name__":
                    return True
                if isinstance(test.left, ast.Constant) and test.left.value == "__main__":
                    return True
                # Check comparators
                for comp in test.comparators:
                    if isinstance(comp, ast.Constant) and comp.value == "__main__":
                        return True
    return False


def test_cmd_wrapper_scripts_have_main_guards():
    """CLI wrapper cmd_*.py scripts (not cmd_save.py) must have main guards."""
    scripts_dir = _get_scripts_dir()
    # cmd_save.py is the library module; cmd_clean/quit/status are wrappers
    wrapper_cmds = ["cmd_clean.py", "cmd_quit.py", "cmd_status.py"]
    for name in wrapper_cmds:
        cmd_file = scripts_dir / name
        if cmd_file.exists():
            assert _has_main_guard(cmd_file), f"{name} missing main guard"


def test_wrapper_scripts_have_main_guards():
    """Wrapper scripts must have main guards."""
    scripts_dir = _get_scripts_dir()
    wrappers = [
        "run_tests.py",
        "run_quality_gate.py",
        "update_state.py",
        "prepare_task.py",
        "generate_stubs.py",
        "setup_infrastructure.py",
    ]
    for name in wrappers:
        filepath = scripts_dir / name
        if filepath.exists():
            assert _has_main_guard(filepath), f"{name} missing main guard"
