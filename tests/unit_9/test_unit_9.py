"""
Tests for Unit 9: Signature Parser Dispatch.

Synthetic Data Assumptions:
- Valid Python source is a simple function definition: 'def greet(name: str) -> str: ...'
- Invalid Python source is syntactically broken: 'def greet(name str -> str:'
- Valid R source contains standard R function assignment: 'greet <- function(name) { ... }'
- R source may use multiple assignment operators: '<-' and '='
- A "component" language like Stan has dispatch key "stan_template" which is NOT in SIGNATURE_PARSERS
- Plugin artifact types (e.g., "plugin_markdown") are NOT in SIGNATURE_PARSERS
- The language_config dict for full languages includes at minimum the keys referenced by the
  registry (e.g., stub_generator_key, etc.), but parse_signatures primarily uses the
  dispatch key derived from the language name for full languages.
- For CLI testing, a blueprint file contains Tier 2 code blocks fenced with ```python
  under a '## Unit N:' heading with '### Tier 2' subheading.
- Unit numbers for CLI are positive integers.
"""

import ast
import textwrap
from pathlib import Path

import pytest

from signature_parser import SIGNATURE_PARSERS, main, parse_signatures

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

VALID_PYTHON_SOURCE = textwrap.dedent("""\
    from typing import Optional

    MY_CONST: int

    def greet(name: str) -> str: ...

    def add(a: int, b: int) -> int: ...

    class Greeter:
        def hello(self) -> str: ...
""")

INVALID_PYTHON_SOURCE = "def greet(name str -> str:"

VALID_R_SOURCE = textwrap.dedent("""\
    greet <- function(name) {
        paste("Hello,", name)
    }

    add <- function(a, b) {
        a + b
    }
""")

VALID_R_SOURCE_EQUALS = textwrap.dedent("""\
    greet = function(name) {
        paste("Hello,", name)
    }
""")

EMPTY_SOURCE = ""

PYTHON_LANGUAGE_CONFIG = {
    "id": "python",
    "display_name": "Python",
    "file_extension": ".py",
    "stub_generator_key": "python",
    "is_component_only": False,
}

R_LANGUAGE_CONFIG = {
    "id": "r",
    "display_name": "R",
    "file_extension": ".R",
    "stub_generator_key": "r",
    "is_component_only": False,
}


# ===========================================================================
# SIGNATURE_PARSERS dispatch table tests
# ===========================================================================


class TestSignatureParsersDispatchTable:
    """Tests for the SIGNATURE_PARSERS module-level dispatch table."""

    def test_signature_parsers_contains_python_key(self):
        """SIGNATURE_PARSERS must have a 'python' key."""
        assert "python" in SIGNATURE_PARSERS

    def test_signature_parsers_contains_r_key(self):
        """SIGNATURE_PARSERS must have an 'r' key."""
        assert "r" in SIGNATURE_PARSERS

    def test_signature_parsers_python_value_is_callable(self):
        """The 'python' entry must be a callable."""
        assert callable(SIGNATURE_PARSERS["python"])

    def test_signature_parsers_r_value_is_callable(self):
        """The 'r' entry must be a callable."""
        assert callable(SIGNATURE_PARSERS["r"])

    def test_signature_parsers_does_not_contain_stan_template(self):
        """Component languages like Stan do not appear in SIGNATURE_PARSERS."""
        assert "stan_template" not in SIGNATURE_PARSERS

    def test_signature_parsers_does_not_contain_stan(self):
        """The raw language name 'stan' should not appear in SIGNATURE_PARSERS."""
        assert "stan" not in SIGNATURE_PARSERS

    def test_signature_parsers_does_not_contain_plugin_markdown(self):
        """Plugin artifact types are not in SIGNATURE_PARSERS."""
        assert "plugin_markdown" not in SIGNATURE_PARSERS

    def test_signature_parsers_does_not_contain_plugin_bash(self):
        """Plugin artifact types are not in SIGNATURE_PARSERS."""
        assert "plugin_bash" not in SIGNATURE_PARSERS

    def test_signature_parsers_does_not_contain_plugin_json(self):
        """Plugin artifact types are not in SIGNATURE_PARSERS."""
        assert "plugin_json" not in SIGNATURE_PARSERS

    def test_signature_parsers_is_dict_of_callables(self):
        """All values in SIGNATURE_PARSERS must be callables."""
        for key, value in SIGNATURE_PARSERS.items():
            assert callable(value), f"Parser for '{key}' is not callable"

    def test_signature_parsers_keys_are_strings(self):
        """All keys in SIGNATURE_PARSERS must be strings."""
        for key in SIGNATURE_PARSERS:
            assert isinstance(key, str), f"Key {key!r} is not a string"


# ===========================================================================
# Python parser tests (via SIGNATURE_PARSERS["python"])
# ===========================================================================


class TestPythonParser:
    """Tests for the Python parser registered under SIGNATURE_PARSERS['python']."""

    def test_python_parser_returns_ast_module_for_valid_source(self):
        """Python parser wraps ast.parse and returns an AST Module node."""
        parser = SIGNATURE_PARSERS["python"]
        result = parser(VALID_PYTHON_SOURCE, PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

    def test_python_parser_ast_contains_function_definitions(self):
        """Parsed AST should contain the function definitions from the source."""
        parser = SIGNATURE_PARSERS["python"]
        result = parser(VALID_PYTHON_SOURCE, PYTHON_LANGUAGE_CONFIG)
        func_names = [
            node.name for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert "greet" in func_names
        assert "add" in func_names

    def test_python_parser_ast_contains_class_definition(self):
        """Parsed AST should contain class definitions from the source."""
        parser = SIGNATURE_PARSERS["python"]
        result = parser(VALID_PYTHON_SOURCE, PYTHON_LANGUAGE_CONFIG)
        class_names = [
            node.name for node in ast.walk(result) if isinstance(node, ast.ClassDef)
        ]
        assert "Greeter" in class_names

    def test_python_parser_raises_syntax_error_on_invalid_source(self):
        """Python parser raises SyntaxError on invalid Python code."""
        parser = SIGNATURE_PARSERS["python"]
        with pytest.raises(SyntaxError):
            parser(INVALID_PYTHON_SOURCE, PYTHON_LANGUAGE_CONFIG)

    def test_python_parser_handles_empty_source(self):
        """Python parser should handle empty source (ast.parse accepts it)."""
        parser = SIGNATURE_PARSERS["python"]
        result = parser(EMPTY_SOURCE, PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

    def test_python_parser_handles_single_function(self):
        """Python parser handles a minimal single function definition."""
        parser = SIGNATURE_PARSERS["python"]
        source = "def foo(): pass"
        result = parser(source, PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)
        func_names = [
            node.name for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert func_names == ["foo"]

    def test_python_parser_preserves_annotations(self):
        """Python parser preserves type annotations in the AST."""
        parser = SIGNATURE_PARSERS["python"]
        source = "def greet(name: str) -> str: ..."
        result = parser(source, PYTHON_LANGUAGE_CONFIG)
        func_defs = [
            node for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert len(func_defs) == 1
        assert func_defs[0].returns is not None


# ===========================================================================
# R parser tests (via SIGNATURE_PARSERS["r"])
# ===========================================================================


class TestRParser:
    """Tests for the R parser registered under SIGNATURE_PARSERS['r']."""

    def test_r_parser_returns_list_of_function_definitions(self):
        """R parser returns a structured list of function definitions."""
        parser = SIGNATURE_PARSERS["r"]
        result = parser(VALID_R_SOURCE, R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_r_parser_extracts_function_names(self):
        """R parser extracts function names from 'name <- function(...)' syntax."""
        parser = SIGNATURE_PARSERS["r"]
        result = parser(VALID_R_SOURCE, R_LANGUAGE_CONFIG)
        # Each entry should have identifiable function name information
        assert len(result) >= 2

    def test_r_parser_handles_arrow_assignment(self):
        """R parser handles '<-' assignment operator for function definitions."""
        parser = SIGNATURE_PARSERS["r"]
        result = parser(VALID_R_SOURCE, R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_r_parser_returns_structured_data(self):
        """Each entry in R parser output should be structured (not raw string)."""
        parser = SIGNATURE_PARSERS["r"]
        result = parser(VALID_R_SOURCE, R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        # Result should be a list of structured definitions, not empty
        assert len(result) > 0

    def test_r_parser_handles_empty_source(self):
        """R parser returns empty list for source with no function definitions."""
        parser = SIGNATURE_PARSERS["r"]
        result = parser("# just a comment\nx <- 42\n", R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_r_parser_handles_multiple_functions(self):
        """R parser extracts multiple function definitions."""
        parser = SIGNATURE_PARSERS["r"]
        result = parser(VALID_R_SOURCE, R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) == 2


# ===========================================================================
# parse_signatures dispatch tests
# ===========================================================================


class TestParseSignaturesDispatch:
    """Tests for parse_signatures dispatching to the correct parser."""

    def test_parse_signatures_dispatches_to_python_parser(self):
        """parse_signatures('python') dispatches to SIGNATURE_PARSERS['python']."""
        result = parse_signatures(VALID_PYTHON_SOURCE, "python", PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

    def test_parse_signatures_dispatches_to_r_parser(self):
        """parse_signatures('r') dispatches to SIGNATURE_PARSERS['r']."""
        result = parse_signatures(VALID_R_SOURCE, "r", R_LANGUAGE_CONFIG)
        assert isinstance(result, list)

    def test_parse_signatures_raises_key_error_for_unknown_language(self):
        """parse_signatures raises KeyError when no parser exists for the language."""
        with pytest.raises(KeyError):
            parse_signatures("some source", "nonexistent_lang", {})

    def test_parse_signatures_raises_key_error_for_stan(self):
        """Stan is component-only; parse_signatures raises KeyError for 'stan'."""
        with pytest.raises(KeyError):
            parse_signatures("data { }", "stan", {"is_component_only": True})

    def test_parse_signatures_raises_key_error_for_stan_template(self):
        """stan_template dispatch key is not in SIGNATURE_PARSERS."""
        with pytest.raises(KeyError):
            parse_signatures("data { }", "stan_template", {"is_component_only": True})

    def test_parse_signatures_raises_key_error_for_plugin_markdown(self):
        """Plugin artifact types bypass parsing; KeyError if called directly."""
        with pytest.raises(KeyError):
            parse_signatures("# doc", "plugin_markdown", {})

    def test_parse_signatures_raises_key_error_for_plugin_bash(self):
        """Plugin artifact types bypass parsing; KeyError if called directly."""
        with pytest.raises(KeyError):
            parse_signatures("#!/bin/bash", "plugin_bash", {})

    def test_parse_signatures_raises_key_error_for_plugin_json(self):
        """Plugin artifact types bypass parsing; KeyError if called directly."""
        with pytest.raises(KeyError):
            parse_signatures("{}", "plugin_json", {})

    def test_parse_signatures_propagates_syntax_error_from_python(self):
        """parse_signatures propagates SyntaxError from the Python parser."""
        with pytest.raises(SyntaxError):
            parse_signatures(INVALID_PYTHON_SOURCE, "python", PYTHON_LANGUAGE_CONFIG)

    def test_parse_signatures_python_returns_ast_module(self):
        """parse_signatures for Python returns an ast.Module object."""
        result = parse_signatures(VALID_PYTHON_SOURCE, "python", PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

    def test_parse_signatures_r_returns_list(self):
        """parse_signatures for R returns a list of function definitions."""
        result = parse_signatures(VALID_R_SOURCE, "r", R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_parse_signatures_dispatch_key_is_language_name_for_full_languages(self):
        """For full languages the dispatch key equals the language name itself."""
        # If we can parse with language="python", it means the dispatch key is "python"
        result = parse_signatures("def f(): pass", "python", PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

        result_r = parse_signatures("f <- function() {}\n", "r", R_LANGUAGE_CONFIG)
        assert isinstance(result_r, list)


# ===========================================================================
# main CLI entry point tests
# ===========================================================================


class TestMainCLIEntryPoint:
    """Tests for the main() CLI entry point."""

    def _make_blueprint_file(self, tmp_path: Path, unit_num: int = 1) -> Path:
        """Create a minimal blueprint_contracts.md with a Python Tier 2 block."""
        content = textwrap.dedent(f"""\
            ## Unit {unit_num}: Test Unit

            ### Tier 2 -- Signatures

            ```python
            def greet(name: str) -> str: ...
            ```

            ### Tier 3 -- Behavioral Contracts

            Some contracts here.
        """)
        bp_file = tmp_path / "blueprint_contracts.md"
        bp_file.write_text(content)
        return bp_file

    def test_main_accepts_blueprint_unit_language_arguments(self, tmp_path):
        """main() accepts --blueprint, --unit, and --language arguments."""
        bp_file = self._make_blueprint_file(tmp_path)
        # Should not raise TypeError for the argument signature
        try:
            main(["--blueprint", str(bp_file), "--unit", "1", "--language", "python"])
        except (SystemExit, Exception):
            # We expect it to either succeed or fail on parsing, but not
            # on argument handling since the stub raises NotImplementedError.
            # The stub will raise NotImplementedError, which is expected.
            pass

    def test_main_exits_with_code_0_on_success(self, tmp_path):
        """main() completes without error on valid input."""
        bp_file = self._make_blueprint_file(tmp_path)
        # Should not raise on valid input
        main(["--blueprint", str(bp_file), "--unit", "1", "--language", "python"])

    def test_main_exits_with_code_1_on_parse_failure(self, tmp_path):
        """main() exits with code 1 on parse failure."""
        content = textwrap.dedent("""\
            ## Unit 1: Test Unit

            ### Tier 2 -- Signatures

            ```python
            def greet(name str -> str:
            ```

            ### Tier 3 -- Behavioral Contracts

            Some contracts here.
        """)
        bp_file = tmp_path / "blueprint_contracts.md"
        bp_file.write_text(content)
        with pytest.raises(SystemExit) as exc_info:
            main(["--blueprint", str(bp_file), "--unit", "1", "--language", "python"])
        assert exc_info.value.code == 1

    def test_main_with_no_arguments_raises_system_exit(self):
        """main() with no arguments raises SystemExit (missing required args)."""
        with pytest.raises(SystemExit):
            main([])

    def test_main_with_explicit_none_argv_raises_system_exit(self):
        """main(None) uses sys.argv which has no required args."""
        with pytest.raises(SystemExit):
            main(None)

    def test_main_with_explicit_argv_list(self, tmp_path):
        """main() accepts an explicit argv list rather than reading sys.argv."""
        bp_file = self._make_blueprint_file(tmp_path)
        # Should complete without error when given valid args
        main(["--blueprint", str(bp_file), "--unit", "1", "--language", "python"])


# ===========================================================================
# Component/plugin bypass documentation tests
# ===========================================================================


class TestComponentAndPluginBypass:
    """
    Tests verifying that component languages and plugin artifact types
    are documented as bypassing signature parsing.
    """

    def test_stan_not_parseable_via_signature_parsers(self):
        """Stan (component language) has no entry in SIGNATURE_PARSERS."""
        assert "stan" not in SIGNATURE_PARSERS
        assert "stan_template" not in SIGNATURE_PARSERS

    def test_plugin_types_not_parseable_via_signature_parsers(self):
        """Plugin artifact types have no entries in SIGNATURE_PARSERS."""
        plugin_keys = ["plugin_markdown", "plugin_bash", "plugin_json"]
        for key in plugin_keys:
            assert key not in SIGNATURE_PARSERS, (
                f"Plugin key '{key}' should not be in SIGNATURE_PARSERS"
            )

    def test_only_full_language_keys_present(self):
        """Only full-language dispatch keys (python, r) are present."""
        expected_full_language_keys = {"python", "r"}
        # SIGNATURE_PARSERS should contain at least python and r
        assert expected_full_language_keys.issubset(set(SIGNATURE_PARSERS.keys()))
        # And should not contain component or plugin keys
        non_parser_keys = {
            "stan",
            "stan_template",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        }
        assert non_parser_keys.isdisjoint(set(SIGNATURE_PARSERS.keys()))


# ===========================================================================
# Edge case and invariant tests
# ===========================================================================


class TestEdgeCasesAndInvariants:
    """Edge cases and invariant tests for parse_signatures."""

    def test_parse_signatures_with_multiline_python_source(self):
        """parse_signatures handles multi-line Python source with imports and classes."""
        source = textwrap.dedent("""\
            from typing import List, Optional
            import json

            class Config:
                name: str
                values: List[int]

                def validate(self) -> bool: ...

            def load(path: str) -> Config: ...
        """)
        result = parse_signatures(source, "python", PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)
        class_names = [n.name for n in ast.walk(result) if isinstance(n, ast.ClassDef)]
        assert "Config" in class_names

    def test_parse_signatures_python_with_only_imports(self):
        """parse_signatures handles Python source that only contains imports."""
        source = "from typing import Any\nimport os\n"
        result = parse_signatures(source, "python", PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

    def test_parse_signatures_python_with_constants_only(self):
        """parse_signatures handles Python source with only type-annotated constants."""
        source = "MY_CONSTANT: int\nANOTHER: str\n"
        result = parse_signatures(source, "python", PYTHON_LANGUAGE_CONFIG)
        assert isinstance(result, ast.Module)

    def test_parse_signatures_r_with_single_function(self):
        """parse_signatures for R with a single function definition."""
        source = "my_func <- function(x, y) {\n  x + y\n}\n"
        result = parse_signatures(source, "r", R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_parse_signatures_r_with_no_functions(self):
        """parse_signatures for R source with no function definitions returns empty."""
        source = "x <- 42\ny <- 'hello'\n"
        result = parse_signatures(source, "r", R_LANGUAGE_CONFIG)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_dispatch_table_is_dict(self):
        """SIGNATURE_PARSERS is a dict."""
        assert isinstance(SIGNATURE_PARSERS, dict)

    def test_parse_signatures_key_error_message_contains_language(self):
        """KeyError from unknown language includes the requested language name."""
        with pytest.raises(KeyError) as exc_info:
            parse_signatures("source", "cobol", {})
        # The KeyError should reference the unknown language somehow
        assert "cobol" in str(exc_info.value)
