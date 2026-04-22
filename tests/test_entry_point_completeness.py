"""Regression tests for P17 invariant — Entry Point Script Completeness.

P17 (spec §24.81, §24.143): every stub module defining a CLI main() function
must have a module-level `if __name__ == "__main__":` guard. Without it,
`python scripts/<name>.py` loads the module and exits 0 without calling
main() — silent false-positive success.

Populated incrementally as each P17 violator is fixed:
- Bug S3-130 (Cycle 1): unit_11 infrastructure_setup
- Bug S3-131 (Cycle 2): unit_10 stub_generator
- Bug S3-132 (Cycle 3): unit_15 quality_gate
- Bug S3-133 (Cycle 4): unit_28 structural_check
"""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _has_main_guard(source_path: Path) -> bool:
    """Return True iff the module has a top-level `if __name__ == "__main__":` block."""
    tree = ast.parse(source_path.read_text())
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if not (isinstance(test.left, ast.Name) and test.left.id == "__name__"):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        if len(test.comparators) != 1:
            continue
        comp = test.comparators[0]
        if isinstance(comp, ast.Constant) and comp.value == "__main__":
            return True
    return False


def test_unit_11_stub_has_main_guard():
    """Unit 11 (infrastructure_setup) must have __main__ guard — Bug S3-130."""
    stub_path = PROJECT_ROOT / "src" / "unit_11" / "stub.py"
    assert _has_main_guard(stub_path), (
        f"{stub_path} defines main() but lacks `if __name__ == '__main__': main()`. "
        "Violates P17 (spec §24.143)."
    )


def test_unit_10_stub_has_main_guard():
    """Unit 10 (stub_generator) must have __main__ guard — Bug S3-131."""
    stub_path = PROJECT_ROOT / "src" / "unit_10" / "stub.py"
    assert _has_main_guard(stub_path), (
        f"{stub_path} defines main() but lacks `if __name__ == '__main__': main()`. "
        "Violates P17 (spec §24.144)."
    )


def test_unit_15_stub_has_main_guard():
    """Unit 15 (quality_gate) must have __main__ guard — Bug S3-132.

    The entry-point function is named run_quality_gate_main (not main),
    so the guard must reference it by that exact name.
    """
    stub_path = PROJECT_ROOT / "src" / "unit_15" / "stub.py"
    assert _has_main_guard(stub_path), (
        f"{stub_path} defines run_quality_gate_main() but lacks "
        "`if __name__ == '__main__': run_quality_gate_main()`. "
        "Violates P17 (spec §24.145)."
    )
