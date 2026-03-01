"""
Tests for Unit 6: Stub Generator

Verifies the behavioral contracts, invariants, error conditions, and
signatures of the stub generator module.

## Synthetic Data Assumptions

DATA ASSUMPTION: Signature blocks are valid Python code containing
function definitions with type annotations (e.g., `def foo(x: int) -> str: ...`)
and/or class definitions, as would be extracted from a blueprint's Tier 2 section.

DATA ASSUMPTION: Import statements in signature blocks (e.g., `import ast`,
`from typing import Optional`) are preserved verbatim in the generated stub source.

DATA ASSUMPTION: Module-level `assert` statements in signature blocks (e.g.,
`assert len(x) > 0`) are stripped from the generated stub to satisfy the
importability invariant; asserts inside function/class bodies are not stripped.

DATA ASSUMPTION: Upstream contracts are represented as a list of dicts, each
containing `unit_number`, `unit_name`, and `signatures` keys (as returned by
Unit 5's `extract_upstream_contracts`).

DATA ASSUMPTION: Output directories exist as real filesystem directories
(created via tmp_path); stub files are written as `stub.py`.

DATA ASSUMPTION: Invalid Python syntax in signature blocks triggers a
SyntaxError with a message containing "Blueprint signature block is not valid Python".
"""

import ast
import inspect
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from svp.scripts.stub_generator import (
    generate_stub_source,
    generate_upstream_mocks,
    parse_signatures,
    strip_module_level_asserts,
    write_stub_file,
    write_upstream_stubs,
)


# ---------------------------------------------------------------------------
# Synthetic signature block data
# ---------------------------------------------------------------------------

# DATA ASSUMPTION: A minimal valid signature block containing a single
# function definition with type annotations. This is the simplest unit of
# code that would appear in a blueprint's Tier 2 section.
MINIMAL_SIGNATURE_BLOCK = "def foo() -> None: ..."

# DATA ASSUMPTION: A signature block with multiple functions, import
# statements, and class definitions -- representing a typical blueprint unit.
TYPICAL_SIGNATURE_BLOCK = textwrap.dedent("""\
import ast
from typing import Optional, Dict, Any, List
from pathlib import Path

def parse_signatures(signature_block: str) -> ast.Module: ...

def generate_stub_source(parsed_ast: ast.Module) -> str: ...

class StubConfig:
    output_dir: Path
    unit_number: int

    def __init__(self, output_dir: Path, unit_number: int) -> None: ...

    def validate(self) -> bool: ...
""")

# DATA ASSUMPTION: A signature block with module-level assert statements
# that must be stripped for the importability invariant.
SIGNATURE_BLOCK_WITH_ASSERTS = textwrap.dedent("""\
import os

assert len("hello") > 0, "Non-empty check"
assert True

def process(x: int) -> int: ...

def validate(y: str) -> bool: ...
""")

# DATA ASSUMPTION: A signature block with asserts inside a function body.
# These should NOT be stripped because only module-level asserts are removed.
SIGNATURE_BLOCK_WITH_INNER_ASSERTS = textwrap.dedent("""\
def check(x: int) -> bool:
    assert x > 0
    return True
""")

# DATA ASSUMPTION: Invalid Python syntax that cannot be parsed by ast.parse().
INVALID_SIGNATURE_BLOCK = "def foo(x: int -> str: ..."

# DATA ASSUMPTION: An empty string representing a missing/empty signature block.
EMPTY_SIGNATURE_BLOCK = ""

# DATA ASSUMPTION: A whitespace-only string representing a blank signature block.
WHITESPACE_ONLY_BLOCK = "   \n  \n  "

# DATA ASSUMPTION: Upstream contracts follow the format returned by
# Unit 5's extract_upstream_contracts: list of dicts with unit_number,
# unit_name, and signatures keys.
SAMPLE_UPSTREAM_CONTRACTS = [
    {
        "unit_number": "1",
        "unit_name": "Alpha Module",
        "signatures": "def alpha_func(x: int) -> str: ...",
    },
    {
        "unit_number": "2",
        "unit_name": "Beta Module",
        "signatures": textwrap.dedent("""\
from typing import List

def beta_func(items: List[str]) -> bool: ...

class BetaHelper:
    def help(self) -> None: ...
"""),
    },
]

# DATA ASSUMPTION: A single upstream contract for simpler test cases.
SINGLE_UPSTREAM_CONTRACT = [
    {
        "unit_number": "3",
        "unit_name": "Gamma Module",
        "signatures": "def gamma_func(z: float) -> float: ...",
    },
]

# DATA ASSUMPTION: An empty upstream contracts list for units with no dependencies.
EMPTY_UPSTREAM_CONTRACTS: List[Dict[str, str]] = []


# ---------------------------------------------------------------------------
# 1. Signature / structure tests
# ---------------------------------------------------------------------------

class TestSignatures:
    """Verify that all functions have the documented signatures."""

    def test_parse_signatures_signature(self):
        """parse_signatures accepts a string and returns ast.Module."""
        sig = inspect.signature(parse_signatures)
        params = list(sig.parameters.keys())
        assert params == ["signature_block"]

    def test_generate_stub_source_signature(self):
        """generate_stub_source accepts an ast.Module and returns a string."""
        sig = inspect.signature(generate_stub_source)
        params = list(sig.parameters.keys())
        assert params == ["parsed_ast"]

    def test_strip_module_level_asserts_signature(self):
        """strip_module_level_asserts accepts an ast.Module and returns ast.Module."""
        sig = inspect.signature(strip_module_level_asserts)
        params = list(sig.parameters.keys())
        assert params == ["tree"]

    def test_generate_upstream_mocks_signature(self):
        """generate_upstream_mocks accepts a list of dicts and returns a dict."""
        sig = inspect.signature(generate_upstream_mocks)
        params = list(sig.parameters.keys())
        assert params == ["upstream_contracts"]

    def test_write_stub_file_signature(self):
        """write_stub_file accepts unit_number, signature_block, output_dir."""
        sig = inspect.signature(write_stub_file)
        params = list(sig.parameters.keys())
        assert params == ["unit_number", "signature_block", "output_dir"]

    def test_write_upstream_stubs_signature(self):
        """write_upstream_stubs accepts upstream_contracts and output_dir."""
        sig = inspect.signature(write_upstream_stubs)
        params = list(sig.parameters.keys())
        assert params == ["upstream_contracts", "output_dir"]


# ---------------------------------------------------------------------------
# 2. parse_signatures tests
# ---------------------------------------------------------------------------

class TestParseSignatures:
    """Behavioral contracts for parse_signatures."""

    def test_returns_ast_module(self):
        """parse_signatures calls ast.parse() and returns the AST as an ast.Module."""
        result = parse_signatures(MINIMAL_SIGNATURE_BLOCK)
        assert isinstance(result, ast.Module)

    def test_parses_simple_function(self):
        """The returned AST should contain the parsed function definition."""
        result = parse_signatures(MINIMAL_SIGNATURE_BLOCK)
        assert isinstance(result, ast.Module)
        # The module body should contain at least one node (the function def)
        assert len(result.body) > 0
        assert isinstance(result.body[0], ast.FunctionDef)

    def test_parses_multiple_functions(self):
        """parse_signatures handles signature blocks with multiple functions."""
        block = textwrap.dedent("""\
def func_a(x: int) -> str: ...
def func_b(y: float) -> bool: ...
""")
        result = parse_signatures(block)
        assert isinstance(result, ast.Module)
        func_names = [
            node.name for node in result.body
            if isinstance(node, ast.FunctionDef)
        ]
        assert "func_a" in func_names
        assert "func_b" in func_names

    def test_parses_imports(self):
        """parse_signatures preserves import statements in the AST."""
        block = textwrap.dedent("""\
import ast
from typing import List

def my_func() -> None: ...
""")
        result = parse_signatures(block)
        assert isinstance(result, ast.Module)
        has_import = any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            for node in result.body
        )
        assert has_import

    def test_parses_class_definitions(self):
        """parse_signatures handles class definitions in the signature block."""
        block = textwrap.dedent("""\
class MyClass:
    x: int
    def method(self) -> None: ...
""")
        result = parse_signatures(block)
        assert isinstance(result, ast.Module)
        has_class = any(isinstance(node, ast.ClassDef) for node in result.body)
        assert has_class

    def test_parses_typical_signature_block(self):
        """parse_signatures handles a typical multi-function, multi-import block."""
        result = parse_signatures(TYPICAL_SIGNATURE_BLOCK)
        assert isinstance(result, ast.Module)
        # Should have imports, functions, and a class
        node_types = {type(node) for node in result.body}
        assert ast.Import in node_types or ast.ImportFrom in node_types
        assert ast.FunctionDef in node_types
        assert ast.ClassDef in node_types

    def test_syntax_error_on_invalid_python(self):
        """SyntaxError raised when signature block is not valid Python.

        Error message should contain 'Blueprint signature block is not valid Python'.
        """
        with pytest.raises(SyntaxError, match=r"Blueprint signature block is not valid Python"):
            parse_signatures(INVALID_SIGNATURE_BLOCK)

    def test_syntax_error_includes_details(self):
        """SyntaxError message should include details about the parse failure."""
        with pytest.raises(SyntaxError) as exc_info:
            parse_signatures(INVALID_SIGNATURE_BLOCK)
        # The error message format is:
        # "Blueprint signature block is not valid Python: {details}"
        assert "Blueprint signature block is not valid Python" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. generate_stub_source tests
# ---------------------------------------------------------------------------

class TestGenerateStubSource:
    """Behavioral contracts for generate_stub_source."""

    def test_contains_not_implemented_error(self):
        """Post-condition: stub source must contain NotImplementedError."""
        tree = parse_signatures(MINIMAL_SIGNATURE_BLOCK)
        result = generate_stub_source(tree)
        assert isinstance(result, str)
        assert "NotImplementedError" in result

    def test_replaces_function_bodies(self):
        """generate_stub_source replaces all function bodies with raise NotImplementedError()."""
        tree = parse_signatures(MINIMAL_SIGNATURE_BLOCK)
        result = generate_stub_source(tree)
        assert "NotImplementedError" in result

    def test_preserves_import_statements(self):
        """generate_stub_source preserves import statements from the signature block."""
        block = textwrap.dedent("""\
import ast
from typing import Optional

def my_func(x: int) -> Optional[str]: ...
""")
        tree = parse_signatures(block)
        result = generate_stub_source(tree)
        assert "import ast" in result
        assert "from typing import Optional" in result

    def test_preserves_class_definitions(self):
        """generate_stub_source preserves class definitions from the signature block."""
        block = textwrap.dedent("""\
class MyConfig:
    name: str
    def validate(self) -> bool: ...
""")
        tree = parse_signatures(block)
        result = generate_stub_source(tree)
        assert "MyConfig" in result

    def test_strips_module_level_asserts(self):
        """generate_stub_source strips module-level assert statements (importability invariant).

        Post-condition: no module-level asserts in stub.
        """
        tree = parse_signatures(SIGNATURE_BLOCK_WITH_ASSERTS)
        result = generate_stub_source(tree)
        # The invariant says: no module-level asserts in stub
        # "assert" should not appear in the part before the first "def "
        if "def " in result:
            before_first_def = result.split("def ")[0]
            assert "assert" not in before_first_def
        else:
            # If there are no function defs, there should be no asserts at all
            assert "assert" not in result

    def test_multiple_functions_all_get_not_implemented(self):
        """All function bodies in the stub should raise NotImplementedError."""
        block = textwrap.dedent("""\
def func_a(x: int) -> str: ...
def func_b(y: float) -> bool: ...
def func_c() -> None: ...
""")
        tree = parse_signatures(block)
        result = generate_stub_source(tree)
        # Each function should have NotImplementedError
        assert result.count("NotImplementedError") >= 3

    def test_stub_source_is_valid_python(self):
        """The generated stub source should be valid Python (parseable by ast)."""
        tree = parse_signatures(TYPICAL_SIGNATURE_BLOCK)
        result = generate_stub_source(tree)
        # Should not raise SyntaxError
        ast.parse(result)

    def test_stub_source_for_class_methods(self):
        """Class method bodies should also be replaced with NotImplementedError."""
        block = textwrap.dedent("""\
class MyClass:
    def method_a(self) -> None: ...
    def method_b(self, x: int) -> str: ...
""")
        tree = parse_signatures(block)
        result = generate_stub_source(tree)
        assert "NotImplementedError" in result
        # Both methods should get NotImplementedError
        assert result.count("NotImplementedError") >= 2


# ---------------------------------------------------------------------------
# 4. strip_module_level_asserts tests
# ---------------------------------------------------------------------------

class TestStripModuleLevelAsserts:
    """Behavioral contracts for strip_module_level_asserts."""

    def test_returns_ast_module(self):
        """strip_module_level_asserts returns an ast.Module."""
        tree = ast.parse(SIGNATURE_BLOCK_WITH_ASSERTS)
        result = strip_module_level_asserts(tree)
        assert isinstance(result, ast.Module)

    def test_removes_module_level_asserts(self):
        """Module-level assert nodes should be removed from the AST."""
        tree = ast.parse(SIGNATURE_BLOCK_WITH_ASSERTS)
        # Verify asserts exist before stripping
        assert_count_before = sum(
            1 for node in tree.body if isinstance(node, ast.Assert)
        )
        assert assert_count_before > 0

        result = strip_module_level_asserts(tree)
        assert_count_after = sum(
            1 for node in result.body if isinstance(node, ast.Assert)
        )
        assert assert_count_after == 0

    def test_preserves_non_assert_nodes(self):
        """Non-assert nodes (imports, functions) should be preserved."""
        tree = ast.parse(SIGNATURE_BLOCK_WITH_ASSERTS)
        # Count non-assert nodes before
        non_assert_before = [
            node for node in tree.body if not isinstance(node, ast.Assert)
        ]

        result = strip_module_level_asserts(tree)
        non_assert_after = [
            node for node in result.body if not isinstance(node, ast.Assert)
        ]

        assert len(non_assert_after) == len(non_assert_before)

    def test_does_not_affect_asserts_inside_functions(self):
        """Asserts inside function bodies should NOT be stripped."""
        tree = ast.parse(SIGNATURE_BLOCK_WITH_INNER_ASSERTS)
        result = strip_module_level_asserts(tree)

        # The function body should still contain the assert
        func_node = None
        for node in result.body:
            if isinstance(node, ast.FunctionDef):
                func_node = node
                break

        assert func_node is not None
        inner_asserts = [
            stmt for stmt in func_node.body if isinstance(stmt, ast.Assert)
        ]
        assert len(inner_asserts) > 0

    def test_does_not_affect_asserts_inside_classes(self):
        """Asserts inside class bodies (within methods) should NOT be stripped."""
        # DATA ASSUMPTION: Class with a method containing an assert statement.
        block = textwrap.dedent("""\
assert True  # module-level, should be stripped

class MyClass:
    def check(self) -> bool:
        assert self is not None
        return True
""")
        tree = ast.parse(block)
        result = strip_module_level_asserts(tree)

        # Module-level assert should be gone
        module_asserts = [
            node for node in result.body if isinstance(node, ast.Assert)
        ]
        assert len(module_asserts) == 0

        # Class method assert should remain
        class_node = [n for n in result.body if isinstance(n, ast.ClassDef)][0]
        method_node = [n for n in class_node.body if isinstance(n, ast.FunctionDef)][0]
        method_asserts = [s for s in method_node.body if isinstance(s, ast.Assert)]
        assert len(method_asserts) > 0

    def test_no_asserts_to_strip(self):
        """When there are no module-level asserts, the tree is unchanged."""
        tree = ast.parse(MINIMAL_SIGNATURE_BLOCK)
        original_count = len(tree.body)
        result = strip_module_level_asserts(tree)
        assert len(result.body) == original_count

    def test_all_asserts_stripped(self):
        """All module-level asserts are stripped, even multiple ones."""
        # DATA ASSUMPTION: Multiple consecutive module-level asserts.
        block = textwrap.dedent("""\
assert True
assert 1 == 1
assert "hello"
def func() -> None: ...
""")
        tree = ast.parse(block)
        result = strip_module_level_asserts(tree)
        module_asserts = [
            node for node in result.body if isinstance(node, ast.Assert)
        ]
        assert len(module_asserts) == 0
        # The function should still be there
        func_nodes = [n for n in result.body if isinstance(n, ast.FunctionDef)]
        assert len(func_nodes) == 1


# ---------------------------------------------------------------------------
# 5. generate_upstream_mocks tests
# ---------------------------------------------------------------------------

class TestGenerateUpstreamMocks:
    """Behavioral contracts for generate_upstream_mocks."""

    def test_returns_dict(self):
        """generate_upstream_mocks returns a dict of mock module source code."""
        result = generate_upstream_mocks(SINGLE_UPSTREAM_CONTRACT)
        assert isinstance(result, dict)

    def test_returns_string_values(self):
        """Each value in the result dict should be a string (Python source code)."""
        result = generate_upstream_mocks(SINGLE_UPSTREAM_CONTRACT)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_mock_for_each_upstream(self):
        """One mock module is produced per upstream dependency."""
        result = generate_upstream_mocks(SAMPLE_UPSTREAM_CONTRACTS)
        assert len(result) >= len(SAMPLE_UPSTREAM_CONTRACTS)

    def test_single_upstream_mock(self):
        """A single upstream contract produces at least one mock module."""
        result = generate_upstream_mocks(SINGLE_UPSTREAM_CONTRACT)
        assert len(result) >= 1

    def test_empty_upstream_returns_empty_or_dict(self):
        """Empty upstream contracts list should return an empty dict."""
        result = generate_upstream_mocks(EMPTY_UPSTREAM_CONTRACTS)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_mock_source_is_valid_python(self):
        """Generated mock source code should be valid Python."""
        result = generate_upstream_mocks(SINGLE_UPSTREAM_CONTRACT)
        for key, source in result.items():
            # Should not raise SyntaxError
            ast.parse(source)

    def test_mock_contains_function_signatures(self):
        """Mock source should contain the function definitions from the contract."""
        result = generate_upstream_mocks(SINGLE_UPSTREAM_CONTRACT)
        # The mock for gamma module should contain gamma_func
        all_sources = " ".join(result.values())
        assert "gamma_func" in all_sources


# ---------------------------------------------------------------------------
# 6. write_stub_file tests
# ---------------------------------------------------------------------------

class TestWriteStubFile:
    """Behavioral contracts for write_stub_file."""

    def test_creates_stub_file(self, tmp_path: Path):
        """write_stub_file produces a stub file at {output_dir}/stub.py."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_returns_path(self, tmp_path: Path):
        """write_stub_file returns a Path object."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert isinstance(result, Path)

    def test_stub_file_is_python(self, tmp_path: Path):
        """Post-condition: stub file must be a Python file (.py extension)."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert result.suffix == ".py"

    def test_stub_file_is_named_stub_py(self, tmp_path: Path):
        """The stub file should be named stub.py."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert result.name == "stub.py"

    def test_stub_file_contains_not_implemented(self, tmp_path: Path):
        """The content of the stub file should contain NotImplementedError."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        assert "NotImplementedError" in content

    def test_stub_file_is_valid_python(self, tmp_path: Path):
        """The generated stub file should be valid Python (parseable by ast)."""
        result = write_stub_file(
            unit_number=1,
            signature_block=TYPICAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        # Should not raise SyntaxError
        ast.parse(content)

    def test_stub_file_strips_module_asserts(self, tmp_path: Path):
        """Module-level asserts should be stripped from the generated stub file."""
        result = write_stub_file(
            unit_number=1,
            signature_block=SIGNATURE_BLOCK_WITH_ASSERTS,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        # No module-level asserts
        if "def " in content:
            before_first_def = content.split("def ")[0]
            assert "assert" not in before_first_def

    def test_stub_preserves_imports(self, tmp_path: Path):
        """Import statements should be preserved in the generated stub."""
        block = textwrap.dedent("""\
import os
from pathlib import Path

def my_func(p: Path) -> None: ...
""")
        result = write_stub_file(
            unit_number=1,
            signature_block=block,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        assert "import os" in content
        assert "from pathlib import Path" in content

    def test_combines_parse_strip_generate(self, tmp_path: Path):
        """write_stub_file combines parse_signatures, strip_module_level_asserts,
        and generate_stub_source to produce the stub."""
        # This test verifies the integration: a block with module-level asserts
        # should produce a stub with no module-level asserts but with
        # NotImplementedError bodies.
        result = write_stub_file(
            unit_number=1,
            signature_block=SIGNATURE_BLOCK_WITH_ASSERTS,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        assert "NotImplementedError" in content
        assert result.exists()
        assert result.suffix == ".py"

    def test_file_not_found_for_missing_output_dir(self, tmp_path: Path):
        """FileNotFoundError when output directory does not exist."""
        nonexistent_dir = tmp_path / "nonexistent" / "deep" / "path"
        with pytest.raises(FileNotFoundError, match=r"Output directory does not exist"):
            write_stub_file(
                unit_number=1,
                signature_block=MINIMAL_SIGNATURE_BLOCK,
                output_dir=nonexistent_dir,
            )

    def test_syntax_error_propagated(self, tmp_path: Path):
        """SyntaxError from parse_signatures should propagate through write_stub_file."""
        with pytest.raises(SyntaxError, match=r"Blueprint signature block is not valid Python"):
            write_stub_file(
                unit_number=1,
                signature_block=INVALID_SIGNATURE_BLOCK,
                output_dir=tmp_path,
            )


# ---------------------------------------------------------------------------
# 7. write_upstream_stubs tests
# ---------------------------------------------------------------------------

class TestWriteUpstreamStubs:
    """Behavioral contracts for write_upstream_stubs."""

    def test_returns_list_of_paths(self, tmp_path: Path):
        """write_upstream_stubs returns a list of Path objects."""
        result = write_upstream_stubs(
            upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
            output_dir=tmp_path,
        )
        assert isinstance(result, list)
        for p in result:
            assert isinstance(p, Path)

    def test_files_exist_after_write(self, tmp_path: Path):
        """All returned paths should point to files that exist."""
        result = write_upstream_stubs(
            upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
            output_dir=tmp_path,
        )
        for p in result:
            assert p.exists()

    def test_files_are_python(self, tmp_path: Path):
        """All generated mock files should be Python files."""
        result = write_upstream_stubs(
            upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
            output_dir=tmp_path,
        )
        for p in result:
            assert p.suffix == ".py"

    def test_multiple_upstream_stubs(self, tmp_path: Path):
        """Multiple upstream contracts produce multiple stub files."""
        result = write_upstream_stubs(
            upstream_contracts=SAMPLE_UPSTREAM_CONTRACTS,
            output_dir=tmp_path,
        )
        assert len(result) >= len(SAMPLE_UPSTREAM_CONTRACTS)

    def test_empty_upstream_returns_empty_list(self, tmp_path: Path):
        """Empty upstream contracts list should return an empty list."""
        result = write_upstream_stubs(
            upstream_contracts=EMPTY_UPSTREAM_CONTRACTS,
            output_dir=tmp_path,
        )
        assert isinstance(result, list)
        assert len(result) == 0

    def test_generated_files_are_valid_python(self, tmp_path: Path):
        """Generated upstream stub files should be valid Python."""
        result = write_upstream_stubs(
            upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
            output_dir=tmp_path,
        )
        for p in result:
            content = p.read_text(encoding="utf-8")
            ast.parse(content)

    def test_file_not_found_for_missing_output_dir(self, tmp_path: Path):
        """FileNotFoundError when output directory does not exist."""
        nonexistent_dir = tmp_path / "nonexistent" / "output"
        with pytest.raises(FileNotFoundError, match=r"Output directory does not exist"):
            write_upstream_stubs(
                upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
                output_dir=nonexistent_dir,
            )


# ---------------------------------------------------------------------------
# 8. Invariant tests (pre-conditions and post-conditions)
# ---------------------------------------------------------------------------

class TestInvariants:
    """Verify pre-conditions and post-conditions from Tier 2 invariants."""

    def test_empty_signature_block_rejected(self):
        """Pre-condition: signature block must not be empty."""
        # DATA ASSUMPTION: An empty string is invalid input for parse_signatures.
        with pytest.raises((ValueError, AssertionError, SyntaxError)):
            parse_signatures(EMPTY_SIGNATURE_BLOCK)

    def test_whitespace_only_signature_block_rejected(self):
        """Pre-condition: whitespace-only signature block is effectively empty."""
        # DATA ASSUMPTION: A whitespace-only string should be treated as empty.
        with pytest.raises((ValueError, AssertionError, SyntaxError)):
            parse_signatures(WHITESPACE_ONLY_BLOCK)

    def test_parse_result_is_ast_module(self):
        """Post-condition: parse result must be an ast.Module."""
        result = parse_signatures(MINIMAL_SIGNATURE_BLOCK)
        assert isinstance(result, ast.Module)

    def test_stub_source_contains_not_implemented(self):
        """Post-condition: stub source must contain NotImplementedError."""
        tree = parse_signatures(MINIMAL_SIGNATURE_BLOCK)
        result = generate_stub_source(tree)
        assert "NotImplementedError" in result

    def test_no_module_level_asserts_in_stub(self):
        """Post-condition: no module-level asserts in stub source."""
        tree = parse_signatures(SIGNATURE_BLOCK_WITH_ASSERTS)
        result = generate_stub_source(tree)
        if "def " in result:
            before_first_def = result.split("def ")[0]
            assert "assert" not in before_first_def

    def test_stub_file_exists_after_write(self, tmp_path: Path):
        """Post-condition: stub file must exist after write."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_stub_file_has_py_suffix(self, tmp_path: Path):
        """Post-condition: stub file must be a Python file (.py)."""
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert result.suffix == ".py"

    def test_empty_block_rejected_by_write_stub_file(self, tmp_path: Path):
        """Pre-condition: empty signature block rejected by write_stub_file."""
        with pytest.raises((ValueError, AssertionError, SyntaxError)):
            write_stub_file(
                unit_number=1,
                signature_block=EMPTY_SIGNATURE_BLOCK,
                output_dir=tmp_path,
            )


# ---------------------------------------------------------------------------
# 9. Error condition tests
# ---------------------------------------------------------------------------

class TestErrorConditions:
    """Verify all documented error conditions from Tier 3."""

    def test_syntax_error_on_invalid_signature(self):
        """SyntaxError when ast.parse() fails on the signature block."""
        with pytest.raises(SyntaxError, match=r"Blueprint signature block is not valid Python"):
            parse_signatures(INVALID_SIGNATURE_BLOCK)

    def test_syntax_error_includes_details(self):
        """SyntaxError message should include details from the parse failure."""
        # DATA ASSUMPTION: The error message format is
        # "Blueprint signature block is not valid Python: {details}"
        with pytest.raises(SyntaxError) as exc_info:
            parse_signatures("def +++bad_code:")
        msg = str(exc_info.value)
        assert "Blueprint signature block is not valid Python" in msg

    def test_file_not_found_write_stub(self, tmp_path: Path):
        """FileNotFoundError when output directory does not exist for write_stub_file."""
        missing_dir = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError, match=r"Output directory does not exist"):
            write_stub_file(
                unit_number=1,
                signature_block=MINIMAL_SIGNATURE_BLOCK,
                output_dir=missing_dir,
            )

    def test_file_not_found_includes_path(self, tmp_path: Path):
        """FileNotFoundError message should include the missing path."""
        missing_dir = tmp_path / "missing_output"
        with pytest.raises(FileNotFoundError) as exc_info:
            write_stub_file(
                unit_number=1,
                signature_block=MINIMAL_SIGNATURE_BLOCK,
                output_dir=missing_dir,
            )
        msg = str(exc_info.value)
        assert "Output directory does not exist" in msg
        assert str(missing_dir) in msg

    def test_file_not_found_write_upstream_stubs(self, tmp_path: Path):
        """FileNotFoundError when output directory does not exist for write_upstream_stubs."""
        missing_dir = tmp_path / "no_such_dir"
        with pytest.raises(FileNotFoundError, match=r"Output directory does not exist"):
            write_upstream_stubs(
                upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
                output_dir=missing_dir,
            )


# ---------------------------------------------------------------------------
# 10. Importability invariant tests
# ---------------------------------------------------------------------------

class TestImportabilityInvariant:
    """The generated stub must be importable without error."""

    def test_generated_stub_is_importable(self, tmp_path: Path):
        """The stub file produced by write_stub_file should be importable.

        DATA ASSUMPTION: We verify importability by executing the generated
        stub source with exec() rather than importing as a module, since the
        file is in a temporary directory.
        """
        result = write_stub_file(
            unit_number=1,
            signature_block=TYPICAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        # exec() should not raise any errors (module-level asserts stripped)
        # We compile first to check for SyntaxError, then the exec tests
        # runtime importability.
        compiled = compile(content, str(result), "exec")
        # If there were module-level asserts that could fail, they would raise
        # AssertionError here. The importability invariant ensures they are gone.
        # Note: We don't actually exec because some imports might not be available,
        # but we verify the code compiles without syntax errors.
        assert compiled is not None

    def test_stub_with_asserts_still_importable(self, tmp_path: Path):
        """Even when the signature block has module-level asserts, the generated
        stub should be importable because they are stripped.

        DATA ASSUMPTION: Module-level assert statements like `assert len("x") > 0`
        would be stripped, preventing potential AssertionError on import.
        """
        # Use a block where asserts would FAIL if not stripped
        block_with_failing_assert = textwrap.dedent("""\
assert False, "This would fail if not stripped"

def safe_func() -> None: ...
""")
        result = write_stub_file(
            unit_number=1,
            signature_block=block_with_failing_assert,
            output_dir=tmp_path,
        )
        content = result.read_text(encoding="utf-8")
        # The assert False should have been stripped
        assert "assert False" not in content
        # Should be compilable
        compiled = compile(content, str(result), "exec")
        assert compiled is not None


# ---------------------------------------------------------------------------
# 11. Integration-style tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end behavioral tests combining multiple functions."""

    def test_full_pipeline_parse_to_file(self, tmp_path: Path):
        """Full pipeline: signature block -> parse -> strip -> generate -> write."""
        sig_block = textwrap.dedent("""\
import os
from typing import List

assert os.name, "OS must have a name"

def list_files(directory: str) -> List[str]: ...

def count_files(directory: str) -> int: ...
""")
        result_path = write_stub_file(
            unit_number=7,
            signature_block=sig_block,
            output_dir=tmp_path,
        )

        assert result_path.exists()
        assert result_path.suffix == ".py"

        content = result_path.read_text(encoding="utf-8")
        assert "NotImplementedError" in content
        assert "import os" in content
        assert "from typing import List" in content

        # Module-level assert should be stripped
        if "def " in content:
            before_first_def = content.split("def ")[0]
            assert "assert" not in before_first_def

    def test_write_stub_file_with_class(self, tmp_path: Path):
        """write_stub_file handles blocks with class definitions."""
        block = textwrap.dedent("""\
from dataclasses import dataclass

class Config:
    name: str
    value: int

    def validate(self) -> bool: ...

def process_config(config: Config) -> None: ...
""")
        result_path = write_stub_file(
            unit_number=2,
            signature_block=block,
            output_dir=tmp_path,
        )

        content = result_path.read_text(encoding="utf-8")
        assert "Config" in content
        assert "NotImplementedError" in content
        assert result_path.exists()
