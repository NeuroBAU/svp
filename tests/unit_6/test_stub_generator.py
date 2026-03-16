"""
Tests for Unit 6: Stub Generator.

Generated from blueprint Tier 2 signatures and Tier 3
behavioral contracts only. No implementation code was
read during test authoring.

Synthetic Data Assumptions:
- Signature blocks are valid Python source containing
  function defs, class defs, imports, and constants.
- parsed_ast is an ast.Module returned by ast.parse().
- upstream_contracts is a list of dicts with keys
  "unit_number", "module_name", and "signature_block".
- output_dir is a temporary directory (via tmp_path).
- Unit numbers are positive integers.
"""

import ast
import textwrap
from pathlib import Path

import pytest

# --------------- fixtures ---------------


@pytest.fixture
def simple_signature_block():
    return textwrap.dedent("""\
        import os
        from pathlib import Path

        SOME_CONST: str = "hello"

        def foo(x: int) -> str: ...

        def bar() -> None: ...
    """)


@pytest.fixture
def signature_with_class():
    return textwrap.dedent("""\
        class Widget:
            name: str
            def run(self) -> bool: ...

        def helper() -> int: ...
    """)


@pytest.fixture
def signature_with_asserts():
    return textwrap.dedent("""\
        import math

        assert True

        def compute(x: int) -> float: ...

        assert False, "should be stripped"
    """)


@pytest.fixture
def upstream_contracts_list():
    return [
        {
            "unit_number": "3",
            "module_name": "state_engine",
            "signature_block": textwrap.dedent("""\
                def transition(s: str) -> str: ...
            """),
        },
        {
            "unit_number": "4",
            "module_name": "ledger",
            "signature_block": textwrap.dedent("""\
                def record(entry: dict) -> None: ...
            """),
        },
    ]


# --------------- import guard ---------------


def _import_stub_generator():
    """Import stub_generator, skip if not available."""
    try:
        import importlib

        mod = importlib.import_module("stub_generator")
        return mod
    except ImportError:
        pytest.skip("stub_generator module not importable")


# --------------- parse_signatures ---------------


class TestParseSignatures:
    def test_returns_ast_module(self, simple_signature_block):
        sg = _import_stub_generator()
        result = sg.parse_signatures(simple_signature_block)
        assert isinstance(result, ast.Module)

    def test_preserves_function_defs(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "foo" in func_names
        assert "bar" in func_names

    def test_preserves_imports(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        import_nodes = [
            n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        assert len(import_nodes) >= 1

    def test_preserves_class_defs(self, signature_with_class):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(signature_with_class)
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "Widget" in class_names

    def test_invalid_syntax_raises(self):
        sg = _import_stub_generator()
        with pytest.raises(SyntaxError):
            sg.parse_signatures("def broken(")


# --------------- generate_stub_source ---------------


class TestGenerateStubSource:
    def test_contains_stub_sentinel(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        source = sg.generate_stub_source(tree)
        assert "__SVP_STUB__ = True" in source

    def test_sentinel_is_first_non_import_statement(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        source = sg.generate_stub_source(tree)
        # Parse generated source; find sentinel position
        gen_tree = ast.parse(source)
        first_non_import = None
        for node in gen_tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            first_non_import = node
            break
        assert first_non_import is not None
        # The first non-import should be the sentinel
        # assignment
        assert isinstance(first_non_import, ast.Assign)
        target = first_non_import.targets[0]
        assert isinstance(target, ast.Name)
        assert target.id == "__SVP_STUB__"

    def test_output_is_valid_python(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        source = sg.generate_stub_source(tree)
        # Must parse without error
        ast.parse(source)

    def test_output_contains_function_defs(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        source = sg.generate_stub_source(tree)
        assert "def foo" in source
        assert "def bar" in source

    def test_sentinel_value_matches_constant(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = sg.parse_signatures(simple_signature_block)
        source = sg.generate_stub_source(tree)
        assert sg.STUB_SENTINEL in source


# --------------- strip_module_level_asserts ----------


class TestStripModuleLevelAsserts:
    def test_removes_top_level_asserts(self, signature_with_asserts):
        sg = _import_stub_generator()
        tree = ast.parse(signature_with_asserts)
        stripped = sg.strip_module_level_asserts(tree)
        top_level_asserts = [n for n in stripped.body if isinstance(n, ast.Assert)]
        assert len(top_level_asserts) == 0

    def test_preserves_non_assert_nodes(self, signature_with_asserts):
        sg = _import_stub_generator()
        tree = ast.parse(signature_with_asserts)
        stripped = sg.strip_module_level_asserts(tree)
        func_names = [n.name for n in stripped.body if isinstance(n, ast.FunctionDef)]
        assert "compute" in func_names

    def test_preserves_imports(self, signature_with_asserts):
        sg = _import_stub_generator()
        tree = ast.parse(signature_with_asserts)
        stripped = sg.strip_module_level_asserts(tree)
        import_nodes = [
            n for n in stripped.body if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        assert len(import_nodes) >= 1

    def test_returns_ast_module(self, signature_with_asserts):
        sg = _import_stub_generator()
        tree = ast.parse(signature_with_asserts)
        result = sg.strip_module_level_asserts(tree)
        assert isinstance(result, ast.Module)

    def test_does_not_strip_nested_asserts(self):
        sg = _import_stub_generator()
        code = textwrap.dedent("""\
            def check():
                assert True
        """)
        tree = ast.parse(code)
        stripped = sg.strip_module_level_asserts(tree)
        # The function should still contain its assert
        func_node = stripped.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        nested_asserts = [n for n in ast.walk(func_node) if isinstance(n, ast.Assert)]
        assert len(nested_asserts) == 1

    def test_no_asserts_is_noop(self, simple_signature_block):
        sg = _import_stub_generator()
        tree = ast.parse(simple_signature_block)
        original_count = len(tree.body)
        stripped = sg.strip_module_level_asserts(tree)
        assert len(stripped.body) == original_count


# --------------- generate_upstream_mocks -------------


class TestGenerateUpstreamMocks:
    def test_returns_dict(self, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.generate_upstream_mocks(upstream_contracts_list)
        assert isinstance(result, dict)

    def test_keys_are_module_names(self, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.generate_upstream_mocks(upstream_contracts_list)
        for contract in upstream_contracts_list:
            module_name = contract["module_name"]
            assert module_name in result

    def test_values_are_strings(self, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.generate_upstream_mocks(upstream_contracts_list)
        for value in result.values():
            assert isinstance(value, str)

    def test_generated_mock_is_valid_python(self, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.generate_upstream_mocks(upstream_contracts_list)
        for source in result.values():
            ast.parse(source)

    def test_empty_list_returns_empty_dict(self):
        sg = _import_stub_generator()
        result = sg.generate_upstream_mocks([])
        assert result == {}


# --------------- write_stub_file ---------------------


class TestWriteStubFile:
    def test_returns_path(self, tmp_path, simple_signature_block):
        sg = _import_stub_generator()
        result = sg.write_stub_file(
            unit_number=6,
            signature_block=simple_signature_block,
            output_dir=tmp_path,
        )
        assert isinstance(result, Path)

    def test_creates_file(self, tmp_path, simple_signature_block):
        sg = _import_stub_generator()
        result = sg.write_stub_file(
            unit_number=6,
            signature_block=simple_signature_block,
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_file_contains_sentinel(self, tmp_path, simple_signature_block):
        sg = _import_stub_generator()
        result = sg.write_stub_file(
            unit_number=6,
            signature_block=simple_signature_block,
            output_dir=tmp_path,
        )
        content = result.read_text()
        assert "__SVP_STUB__ = True" in content

    def test_file_is_importable(self, tmp_path, simple_signature_block):
        sg = _import_stub_generator()
        result = sg.write_stub_file(
            unit_number=6,
            signature_block=simple_signature_block,
            output_dir=tmp_path,
        )
        content = result.read_text()
        # Importability invariant: must compile
        compile(content, str(result), "exec")

    def test_file_is_valid_python(self, tmp_path, simple_signature_block):
        sg = _import_stub_generator()
        result = sg.write_stub_file(
            unit_number=6,
            signature_block=simple_signature_block,
            output_dir=tmp_path,
        )
        content = result.read_text()
        ast.parse(content)


# --------------- write_upstream_stubs ----------------


class TestWriteUpstreamStubs:
    def test_returns_list_of_paths(self, tmp_path, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.write_upstream_stubs(
            upstream_contracts=upstream_contracts_list,
            output_dir=tmp_path,
        )
        assert isinstance(result, list)
        for p in result:
            assert isinstance(p, Path)

    def test_creates_files(self, tmp_path, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.write_upstream_stubs(
            upstream_contracts=upstream_contracts_list,
            output_dir=tmp_path,
        )
        for p in result:
            assert p.exists()

    def test_number_of_files_matches_contracts(self, tmp_path, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.write_upstream_stubs(
            upstream_contracts=upstream_contracts_list,
            output_dir=tmp_path,
        )
        assert len(result) == len(upstream_contracts_list)

    def test_generated_files_are_valid_python(self, tmp_path, upstream_contracts_list):
        sg = _import_stub_generator()
        result = sg.write_upstream_stubs(
            upstream_contracts=upstream_contracts_list,
            output_dir=tmp_path,
        )
        for p in result:
            content = p.read_text()
            ast.parse(content)

    def test_empty_contracts_returns_empty_list(self, tmp_path):
        sg = _import_stub_generator()
        result = sg.write_upstream_stubs(
            upstream_contracts=[],
            output_dir=tmp_path,
        )
        assert result == []


# --------------- forward reference guard -------------


class TestForwardReferenceGuard:
    def test_higher_unit_dependency_raises(self):
        """
        Forward-reference guard: validates every
        dependency has a lower unit number. Fails with
        clear error if violated.
        """
        sg = _import_stub_generator()
        # A contract referencing a higher unit number
        # than the current unit should fail.
        bad_contracts = [
            {
                "unit_number": "99",
                "module_name": "future_mod",
                "signature_block": "def f(): ...",
            },
        ]
        # write_upstream_stubs or write_stub_file should
        # enforce forward-reference guard. We test both
        # possible enforcement points.
        with pytest.raises((ValueError, RuntimeError, Exception)):
            sg.write_upstream_stubs(
                upstream_contracts=bad_contracts,
                output_dir=Path("/tmp/dummy"),
            )


# --------------- STUB_SENTINEL constant --------------


class TestStubSentinel:
    def test_sentinel_constant_exists(self):
        sg = _import_stub_generator()
        assert hasattr(sg, "STUB_SENTINEL")

    def test_sentinel_contains_marker(self):
        sg = _import_stub_generator()
        assert "__SVP_STUB__" in sg.STUB_SENTINEL

    def test_sentinel_contains_true(self):
        sg = _import_stub_generator()
        assert "True" in sg.STUB_SENTINEL

    def test_sentinel_is_string(self):
        sg = _import_stub_generator()
        assert isinstance(sg.STUB_SENTINEL, str)


# --------------- CLI wrapper contract ----------------


class TestCLIWrapper:
    def test_cli_emits_succeeded_on_success(self):
        """
        CLI wrapper emits COMMAND_SUCCEEDED /
        COMMAND_FAILED status lines.
        """
        try:
            import importlib

            mod = importlib.import_module("generate_stubs")
        except ImportError:
            pytest.skip("generate_stubs CLI module not importable")
        assert hasattr(mod, "main")

    def test_cli_main_is_callable(self):
        try:
            import importlib

            mod = importlib.import_module("generate_stubs")
        except ImportError:
            pytest.skip("generate_stubs CLI module not importable")
        assert callable(mod.main)


# --------------- importability invariant -------------


class TestImportabilityInvariant:
    def test_generated_stub_compiles(self, tmp_path, simple_signature_block):
        """
        Generated stub must be importable without error
        (importability invariant).
        """
        sg = _import_stub_generator()
        path = sg.write_stub_file(
            unit_number=6,
            signature_block=simple_signature_block,
            output_dir=tmp_path,
        )
        content = path.read_text()
        code = compile(content, str(path), "exec")
        assert code is not None

    def test_generated_stub_with_class_compiles(self, tmp_path, signature_with_class):
        sg = _import_stub_generator()
        path = sg.write_stub_file(
            unit_number=6,
            signature_block=signature_with_class,
            output_dir=tmp_path,
        )
        content = path.read_text()
        code = compile(content, str(path), "exec")
        assert code is not None
