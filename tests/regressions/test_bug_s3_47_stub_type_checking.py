"""Regression test for Bug S3-47: upstream imports behind TYPE_CHECKING."""
import ast
from src.unit_10.stub import generate_stub
from src.unit_2.stub import LANGUAGE_REGISTRY


def test_upstream_imports_behind_type_checking():
    """S3-47: Non-stdlib imports must be wrapped in if TYPE_CHECKING."""
    source = (
        "from engine import Engine\n"
        "from patterns import PATTERNS\n"
        "\n"
        "class Foo:\n"
        "    engine: Engine\n"
        "    def run(self) -> None: ...\n"
    )
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "if TYPE_CHECKING:" in result
    assert "from engine import Engine" in result
    assert "from __future__ import annotations" in result


def test_stdlib_imports_not_guarded():
    """S3-47: stdlib imports must NOT be behind TYPE_CHECKING."""
    source = (
        "import argparse\n"
        "from pathlib import Path\n"
        "\n"
        "def foo(p: Path) -> None: ...\n"
    )
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    lines = result.split("\n")
    for line in lines:
        if "import argparse" in line and line.strip().startswith("import"):
            assert not line.startswith("    "), (
                "stdlib import should not be indented under TYPE_CHECKING"
            )


def test_mixed_imports_separated():
    """S3-47: Mixed stdlib + upstream imports are correctly separated."""
    source = (
        "import json\n"
        "from engine import Engine\n"
        "from pathlib import Path\n"
        "\n"
        "def foo() -> None: ...\n"
    )
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "if TYPE_CHECKING:" in result
    # json and pathlib NOT under TYPE_CHECKING
    lines = result.split("\n")
    in_type_checking = False
    for line in lines:
        if "if TYPE_CHECKING:" in line:
            in_type_checking = True
        if in_type_checking and "import json" in line:
            assert False, "json should not be under TYPE_CHECKING"
        if in_type_checking and "from pathlib" in line:
            assert False, "pathlib should not be under TYPE_CHECKING"


def test_no_upstream_no_type_checking_block():
    """S3-47: If no upstream imports, TYPE_CHECKING block is omitted."""
    source = (
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "def foo() -> None: ...\n"
    )
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "if TYPE_CHECKING:" not in result
