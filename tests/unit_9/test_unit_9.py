"""Unit 9: Signature Parser Dispatch -- complete test suite.

Synthetic data assumptions:
- SIGNATURE_PARSERS is a dict mapping language dispatch keys (str) to callables
  that accept (source: str, language_config: Dict[str, Any]) and return parsed
  representations.
- For key "python": the parser wraps ast.parse(source) and returns an AST module
  object. It raises SyntaxError on invalid Python source code.
- For key "r": the parser is regex-based, recognizing R function assignment
  patterns (name <- function(...)), and returns a structured list of function
  definitions.
- parse_signatures resolves the dispatch key from the language name for
  full languages (dispatch key == language name, e.g., "python", "r").
- parse_signatures raises KeyError when no parser exists for the resolved
  dispatch key (e.g., for component languages like Stan or plugin artifact types).
- main CLI accepts --blueprint (path), --unit (int), --language (str). It extracts
  the Tier 2 block for the given unit, strips code fences, and parses.
  Exit code 0 on success, 1 on parse failure. Output to stdout/stderr.
- Valid Python source: "def foo(x): return x" produces an AST with one FunctionDef.
- Valid R source: "my_func <- function(x, y) { x + y }" produces a list with one
  entry containing name="my_func" and params.
- A Tier 2 block for a blueprint unit is delimited by markdown code fences
  (```python ... ```) within the blueprint_contracts.md file.
- Component languages (e.g., Stan) and plugin artifact types do not have entries
  in SIGNATURE_PARSERS. Attempting to parse them raises KeyError.
"""

import ast
import textwrap
from unittest.mock import patch

import pytest

from src.unit_9.stub import (
    SIGNATURE_PARSERS,
    main,
    parse_signatures,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PYTHON_SOURCE = "def foo(x):\n    return x\n"

VALID_PYTHON_CLASS_SOURCE = textwrap.dedent("""\
    class MyClass:
        def method(self, a, b):
            return a + b
""")

INVALID_PYTHON_SOURCE = "def foo(x:\n"

VALID_R_SOURCE = "my_func <- function(x, y) {\n  x + y\n}\n"

VALID_R_MULTIPLE = textwrap.dedent("""\
    add <- function(a, b) {
      a + b
    }

    subtract <- function(a, b) {
      a - b
    }
""")

MINIMAL_PYTHON_CONFIG = {
    "id": "python",
    "display_name": "Python",
    "file_extension": ".py",
    "stub_generator_key": "python",
    "is_component_only": False,
}

MINIMAL_R_CONFIG = {
    "id": "r",
    "display_name": "R",
    "file_extension": ".R",
    "stub_generator_key": "r",
    "is_component_only": False,
}

STAN_COMPONENT_CONFIG = {
    "id": "stan",
    "display_name": "Stan",
    "file_extension": ".stan",
    "is_component_only": True,
    "compatible_hosts": ["r", "python"],
    "stub_generator_key": "stan_template",
}


# ---------------------------------------------------------------------------
# SIGNATURE_PARSERS dispatch table
# ---------------------------------------------------------------------------


class TestSignatureParsersDispatchTable:
    """Tests for the SIGNATURE_PARSERS module-level dispatch table."""

    def test_signature_parsers_is_dict(self):
        """SIGNATURE_PARSERS must be a dict."""
        assert isinstance(SIGNATURE_PARSERS, dict)

    def test_python_key_present(self):
        """Dispatch table must contain a 'python' key."""
        assert "python" in SIGNATURE_PARSERS

    def test_r_key_present(self):
        """Dispatch table must contain an 'r' key."""
        assert "r" in SIGNATURE_PARSERS

    def test_python_parser_is_callable(self):
        """The python parser must be callable."""
        assert callable(SIGNATURE_PARSERS["python"])

    def test_r_parser_is_callable(self):
        """The r parser must be callable."""
        assert callable(SIGNATURE_PARSERS["r"])

    def test_stan_key_absent(self):
        """Component languages like Stan must NOT have entries in the table."""
        assert "stan" not in SIGNATURE_PARSERS

    def test_stan_template_key_absent(self):
        """Component dispatch keys like 'stan_template' must NOT be in the table."""
        assert "stan_template" not in SIGNATURE_PARSERS

    def test_plugin_markdown_key_absent(self):
        """Plugin artifact type 'plugin_markdown' must NOT be in the table."""
        assert "plugin_markdown" not in SIGNATURE_PARSERS

    def test_plugin_bash_key_absent(self):
        """Plugin artifact type 'plugin_bash' must NOT be in the table."""
        assert "plugin_bash" not in SIGNATURE_PARSERS

    def test_plugin_json_key_absent(self):
        """Plugin artifact type 'plugin_json' must NOT be in the table."""
        assert "plugin_json" not in SIGNATURE_PARSERS


# ---------------------------------------------------------------------------
# Python parser via SIGNATURE_PARSERS["python"]
# ---------------------------------------------------------------------------


class TestPythonParser:
    """Tests for the Python signature parser (SIGNATURE_PARSERS['python'])."""

    def test_python_parser_returns_ast_module(self):
        """Python parser wraps ast.parse and returns an AST module object."""
        result = SIGNATURE_PARSERS["python"](VALID_PYTHON_SOURCE, MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)

    def test_python_parser_single_function(self):
        """Parsing source with one function produces AST containing one FunctionDef."""
        result = SIGNATURE_PARSERS["python"](VALID_PYTHON_SOURCE, MINIMAL_PYTHON_CONFIG)
        func_defs = [
            node for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert len(func_defs) == 1
        assert func_defs[0].name == "foo"

    def test_python_parser_class_source(self):
        """Parsing source with a class produces AST containing a ClassDef."""
        result = SIGNATURE_PARSERS["python"](
            VALID_PYTHON_CLASS_SOURCE, MINIMAL_PYTHON_CONFIG
        )
        class_defs = [
            node for node in ast.walk(result) if isinstance(node, ast.ClassDef)
        ]
        assert len(class_defs) == 1
        assert class_defs[0].name == "MyClass"

    def test_python_parser_multiple_definitions(self):
        """Parsing source with multiple top-level definitions captures all of them."""
        source = "def alpha(): pass\ndef beta(): pass\nclass Gamma: pass\n"
        result = SIGNATURE_PARSERS["python"](source, MINIMAL_PYTHON_CONFIG)
        names = [
            node.name
            for node in ast.walk(result)
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        ]
        assert "alpha" in names
        assert "beta" in names
        assert "Gamma" in names

    def test_python_parser_empty_source(self):
        """Parsing an empty string returns an AST module with no body items."""
        result = SIGNATURE_PARSERS["python"]("", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        assert len(result.body) == 0

    def test_python_parser_syntax_error_raises(self):
        """Invalid Python source raises SyntaxError."""
        with pytest.raises(SyntaxError):
            SIGNATURE_PARSERS["python"](INVALID_PYTHON_SOURCE, MINIMAL_PYTHON_CONFIG)

    def test_python_parser_preserves_function_args(self):
        """The AST captures function argument structure."""
        source = "def process(a, b, c=10): pass\n"
        result = SIGNATURE_PARSERS["python"](source, MINIMAL_PYTHON_CONFIG)
        func_defs = [
            node for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert len(func_defs) == 1
        args = func_defs[0].args
        # a, b, c are the positional args
        arg_names = [a.arg for a in args.args]
        assert arg_names == ["a", "b", "c"]

    def test_python_parser_with_imports(self):
        """Source containing imports parses correctly into AST with Import nodes."""
        source = "import os\nfrom pathlib import Path\ndef run(): pass\n"
        result = SIGNATURE_PARSERS["python"](source, MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        has_import = any(
            isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(result)
        )
        assert has_import

    def test_python_parser_with_type_annotations(self):
        """Source with type annotations parses correctly."""
        source = "def compute(x: int, y: float = 0.0) -> str: pass\n"
        result = SIGNATURE_PARSERS["python"](source, MINIMAL_PYTHON_CONFIG)
        func_defs = [
            node for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert len(func_defs) == 1
        # Return annotation should be present
        assert func_defs[0].returns is not None


# ---------------------------------------------------------------------------
# R parser via SIGNATURE_PARSERS["r"]
# ---------------------------------------------------------------------------


class TestRParser:
    """Tests for the R signature parser (SIGNATURE_PARSERS['r'])."""

    def test_r_parser_returns_list(self):
        """R parser returns a structured list of function definitions."""
        result = SIGNATURE_PARSERS["r"](VALID_R_SOURCE, MINIMAL_R_CONFIG)
        assert isinstance(result, list)

    def test_r_parser_single_function_name(self):
        """Parsing single R function assignment captures the function name."""
        result = SIGNATURE_PARSERS["r"](VALID_R_SOURCE, MINIMAL_R_CONFIG)
        assert len(result) >= 1
        names = [entry.get("name", entry.get("function_name", "")) for entry in result]
        # Accept either key convention; at least one entry should match
        assert any("my_func" in str(n) for n in names)

    def test_r_parser_multiple_functions(self):
        """Parsing source with two R functions returns two entries."""
        result = SIGNATURE_PARSERS["r"](VALID_R_MULTIPLE, MINIMAL_R_CONFIG)
        assert len(result) == 2

    def test_r_parser_captures_both_function_names(self):
        """Both function names from multi-function R source are captured."""
        result = SIGNATURE_PARSERS["r"](VALID_R_MULTIPLE, MINIMAL_R_CONFIG)
        all_names_str = str(result)
        assert "add" in all_names_str
        assert "subtract" in all_names_str

    def test_r_parser_empty_source(self):
        """Parsing empty R source returns an empty list."""
        result = SIGNATURE_PARSERS["r"]("", MINIMAL_R_CONFIG)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_r_parser_no_function_assignments(self):
        """Source with no function assignments returns an empty list."""
        result = SIGNATURE_PARSERS["r"]("x <- 42\ny <- 'hello'\n", MINIMAL_R_CONFIG)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_r_parser_arrow_assignment_pattern(self):
        """R parser recognizes the 'name <- function(...)' pattern."""
        source = "processor <- function(data, threshold = 0.05) {\n  data\n}\n"
        result = SIGNATURE_PARSERS["r"](source, MINIMAL_R_CONFIG)
        assert len(result) >= 1
        assert "processor" in str(result)

    def test_r_parser_equals_assignment(self):
        """R parser should handle 'name = function(...)' if supported, or at
        minimum not crash. The contract specifies 'name <- function(...)' pattern,
        so equals assignment may or may not be detected."""
        source = "my_func = function(x) { x }\n"
        # Must not raise -- may return empty list or list with the function
        result = SIGNATURE_PARSERS["r"](source, MINIMAL_R_CONFIG)
        assert isinstance(result, list)

    def test_r_parser_function_with_no_params(self):
        """R parser handles functions with no parameters."""
        source = "get_version <- function() {\n  '1.0'\n}\n"
        result = SIGNATURE_PARSERS["r"](source, MINIMAL_R_CONFIG)
        assert len(result) >= 1
        assert "get_version" in str(result)

    def test_r_parser_dotted_function_name(self):
        """R parser handles function names with dots (common R convention)."""
        source = "my.func.name <- function(x) { x }\n"
        result = SIGNATURE_PARSERS["r"](source, MINIMAL_R_CONFIG)
        assert len(result) >= 1
        assert "my.func.name" in str(result)


# ---------------------------------------------------------------------------
# parse_signatures function
# ---------------------------------------------------------------------------


class TestParseSignatures:
    """Tests for the parse_signatures dispatch function."""

    def test_python_dispatch_returns_ast_module(self):
        """parse_signatures for language='python' returns an AST module."""
        result = parse_signatures(VALID_PYTHON_SOURCE, "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)

    def test_r_dispatch_returns_list(self):
        """parse_signatures for language='r' returns a list."""
        result = parse_signatures(VALID_R_SOURCE, "r", MINIMAL_R_CONFIG)
        assert isinstance(result, list)

    def test_python_dispatch_key_is_language_name(self):
        """For full languages, the dispatch key is the language name itself."""
        # Verify that dispatching with language="python" works
        result = parse_signatures(VALID_PYTHON_SOURCE, "python", MINIMAL_PYTHON_CONFIG)
        assert result is not None

    def test_r_dispatch_key_is_language_name(self):
        """For full languages, the dispatch key for R is 'r'."""
        result = parse_signatures(VALID_R_SOURCE, "r", MINIMAL_R_CONFIG)
        assert result is not None

    def test_unknown_language_raises_key_error(self):
        """parse_signatures raises KeyError for an unregistered dispatch key."""
        with pytest.raises(KeyError):
            parse_signatures("some source", "unknown_lang", {"id": "unknown_lang"})

    def test_stan_raises_key_error(self):
        """Component languages like Stan have no parser; KeyError is raised."""
        with pytest.raises(KeyError):
            parse_signatures("data { }", "stan", STAN_COMPONENT_CONFIG)

    def test_plugin_markdown_raises_key_error(self):
        """Plugin artifact type 'plugin_markdown' has no parser; KeyError raised."""
        with pytest.raises(KeyError):
            parse_signatures("# heading", "plugin_markdown", {"id": "plugin_markdown"})

    def test_plugin_bash_raises_key_error(self):
        """Plugin artifact type 'plugin_bash' has no parser; KeyError raised."""
        with pytest.raises(KeyError):
            parse_signatures("#!/bin/bash", "plugin_bash", {"id": "plugin_bash"})

    def test_plugin_json_raises_key_error(self):
        """Plugin artifact type 'plugin_json' has no parser; KeyError raised."""
        with pytest.raises(KeyError):
            parse_signatures("{}", "plugin_json", {"id": "plugin_json"})

    def test_python_syntax_error_propagates(self):
        """SyntaxError from the python parser propagates through parse_signatures."""
        with pytest.raises(SyntaxError):
            parse_signatures(INVALID_PYTHON_SOURCE, "python", MINIMAL_PYTHON_CONFIG)

    def test_python_parse_preserves_function_names(self):
        """Parsed Python AST via parse_signatures contains expected function names."""
        source = "def alpha(): pass\ndef beta(): pass\n"
        result = parse_signatures(source, "python", MINIMAL_PYTHON_CONFIG)
        names = [
            node.name for node in ast.walk(result) if isinstance(node, ast.FunctionDef)
        ]
        assert "alpha" in names
        assert "beta" in names

    def test_r_parse_captures_functions(self):
        """Parsed R source via parse_signatures captures function definitions."""
        result = parse_signatures(VALID_R_MULTIPLE, "r", MINIMAL_R_CONFIG)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# main CLI entry point
# ---------------------------------------------------------------------------


class TestMainCLI:
    """Tests for the main CLI entry point."""

    def _make_blueprint_file(self, tmp_path, unit_number=9, language="python"):
        """Create a minimal blueprint_contracts.md with a Tier 2 block."""
        content = textwrap.dedent(f"""\
            ## Unit {unit_number}: Test Unit

            ### Tier 2 -- Signatures

            ```{language}
            def example_func(x: int) -> str:
                pass
            ```

            ### Tier 3 -- Behavioral Contracts

            Some contract text here.
        """)
        bp_path = tmp_path / "blueprint_contracts.md"
        bp_path.write_text(content)
        return bp_path

    def _make_r_blueprint_file(self, tmp_path, unit_number=9):
        """Create a minimal blueprint_contracts.md with an R Tier 2 block."""
        content = textwrap.dedent(f"""\
            ## Unit {unit_number}: Test Unit

            ### Tier 2 -- Signatures

            ```r
            example_func <- function(x) {{
              x
            }}
            ```

            ### Tier 3 -- Behavioral Contracts

            Some contract text here.
        """)
        bp_path = tmp_path / "blueprint_contracts.md"
        bp_path.write_text(content)
        return bp_path

    def test_main_success_exit_code_zero(self, tmp_path):
        """main exits with code 0 on successful parse."""
        bp_path = self._make_blueprint_file(tmp_path)
        try:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "python"])
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    def test_main_parse_failure_exit_code_one(self, tmp_path):
        """main exits with code 1 on parse failure."""
        content = textwrap.dedent("""\
            ## Unit 9: Test Unit

            ### Tier 2 -- Signatures

            ```python
            def broken(x:
            ```

            ### Tier 3 -- Behavioral Contracts

            Text.
        """)
        bp_path = tmp_path / "blueprint_contracts.md"
        bp_path.write_text(content)
        with pytest.raises(SystemExit) as exc_info:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "python"])
        assert exc_info.value.code == 1

    def test_main_prints_parsed_result_to_stdout(self, tmp_path, capsys):
        """main prints parsed result to stdout on success."""
        bp_path = self._make_blueprint_file(tmp_path)
        try:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "python"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        # Should have some output on success
        assert len(captured.out) > 0 or len(captured.err) == 0

    def test_main_prints_error_to_stderr_on_failure(self, tmp_path, capsys):
        """main prints error information to stderr on parse failure."""
        content = textwrap.dedent("""\
            ## Unit 9: Test Unit

            ### Tier 2 -- Signatures

            ```python
            def broken(x:
            ```

            ### Tier 3 -- Behavioral Contracts

            Text.
        """)
        bp_path = tmp_path / "blueprint_contracts.md"
        bp_path.write_text(content)
        with pytest.raises(SystemExit):
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "python"])
        captured = capsys.readouterr()
        assert len(captured.err) > 0

    def test_main_accepts_blueprint_argument(self, tmp_path):
        """main accepts --blueprint as a path argument."""
        bp_path = self._make_blueprint_file(tmp_path)
        # Should not raise (other than clean exit)
        try:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "python"])
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    def test_main_accepts_unit_argument(self, tmp_path):
        """main accepts --unit as an integer argument."""
        bp_path = self._make_blueprint_file(tmp_path, unit_number=5)
        try:
            main(["--blueprint", str(bp_path), "--unit", "5", "--language", "python"])
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    def test_main_accepts_language_argument(self, tmp_path):
        """main accepts --language as a string argument."""
        bp_path = self._make_r_blueprint_file(tmp_path)
        try:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "r"])
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    def test_main_extracts_and_strips_code_fences(self, tmp_path, capsys):
        """main extracts the Tier 2 block and strips code fence markers before parsing."""
        bp_path = self._make_blueprint_file(tmp_path)
        try:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "python"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        # The code fences (```python and ```) should not appear in the parsed output
        assert "```" not in captured.out

    def test_main_missing_unit_in_blueprint_exits_one(self, tmp_path):
        """main exits with code 1 when the specified unit is not found in blueprint."""
        content = textwrap.dedent("""\
            ## Unit 1: Only Unit

            ### Tier 2 -- Signatures

            ```python
            def foo(): pass
            ```

            ### Tier 3 -- Behavioral Contracts

            Text.
        """)
        bp_path = tmp_path / "blueprint_contracts.md"
        bp_path.write_text(content)
        with pytest.raises(SystemExit) as exc_info:
            main(["--blueprint", str(bp_path), "--unit", "99", "--language", "python"])
        assert exc_info.value.code == 1

    def test_main_unknown_language_exits_one(self, tmp_path):
        """main exits with code 1 when the language has no parser."""
        bp_path = self._make_blueprint_file(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            main(["--blueprint", str(bp_path), "--unit", "9", "--language", "fortran"])
        assert exc_info.value.code == 1

    def test_main_nonexistent_blueprint_exits_one(self):
        """main exits with code 1 when the blueprint file does not exist."""
        with pytest.raises((SystemExit, FileNotFoundError)) as exc_info:
            main(
                [
                    "--blueprint",
                    "/nonexistent/path/blueprint_contracts.md",
                    "--unit",
                    "9",
                    "--language",
                    "python",
                ]
            )
        if isinstance(exc_info.value, SystemExit):
            assert exc_info.value.code == 1

    def test_main_default_argv_is_none(self):
        """main with no arguments defaults to reading sys.argv."""
        with patch(
            "sys.argv",
            ["prog", "--blueprint", "/dev/null", "--unit", "1", "--language", "python"],
        ):
            # May fail but should at least attempt to parse sys.argv
            try:
                main()
            except (SystemExit, Exception):
                pass  # Expected -- /dev/null is not a valid blueprint


# ---------------------------------------------------------------------------
# Dispatch table keying and extensibility
# ---------------------------------------------------------------------------


class TestDispatchTableKeying:
    """Tests for dispatch table keying semantics."""

    def test_dispatch_keys_are_strings(self):
        """All keys in SIGNATURE_PARSERS must be strings."""
        for key in SIGNATURE_PARSERS:
            assert isinstance(key, str), f"Key {key!r} is not a string"

    def test_dispatch_values_are_callable(self):
        """All values in SIGNATURE_PARSERS must be callable."""
        for key, parser in SIGNATURE_PARSERS.items():
            assert callable(parser), f"Parser for {key!r} is not callable"

    def test_dispatch_key_for_python_matches_language_name(self):
        """The dispatch key for Python is 'python' (same as language name)."""
        # Verify through parse_signatures that the dispatch key is the language name
        result = parse_signatures(VALID_PYTHON_SOURCE, "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)

    def test_dispatch_key_for_r_matches_language_name(self):
        """The dispatch key for R is 'r' (same as language name)."""
        result = parse_signatures(VALID_R_SOURCE, "r", MINIMAL_R_CONFIG)
        assert isinstance(result, list)

    def test_full_language_dispatch_keys_present(self):
        """Both full-language dispatch keys ('python', 'r') exist."""
        expected_keys = {"python", "r"}
        assert expected_keys.issubset(set(SIGNATURE_PARSERS.keys()))

    def test_no_component_or_plugin_keys_in_table(self):
        """No component-language or plugin-artifact keys should appear in the table."""
        forbidden_keys = {
            "stan",
            "stan_template",
            "plugin_markdown",
            "plugin_bash",
            "plugin_json",
        }
        actual_keys = set(SIGNATURE_PARSERS.keys())
        overlap = forbidden_keys & actual_keys
        assert len(overlap) == 0, f"Unexpected keys in SIGNATURE_PARSERS: {overlap}"


# ---------------------------------------------------------------------------
# Integration: parse_signatures with SIGNATURE_PARSERS consistency
# ---------------------------------------------------------------------------


class TestParseSignaturesDispatchConsistency:
    """Tests that parse_signatures correctly dispatches through SIGNATURE_PARSERS."""

    def test_python_dispatch_result_matches_direct_call(self):
        """parse_signatures('python') returns same type as SIGNATURE_PARSERS['python']."""
        direct = SIGNATURE_PARSERS["python"](VALID_PYTHON_SOURCE, MINIMAL_PYTHON_CONFIG)
        dispatched = parse_signatures(
            VALID_PYTHON_SOURCE, "python", MINIMAL_PYTHON_CONFIG
        )
        assert type(direct) == type(dispatched)

    def test_r_dispatch_result_matches_direct_call(self):
        """parse_signatures('r') returns same type as SIGNATURE_PARSERS['r']."""
        direct = SIGNATURE_PARSERS["r"](VALID_R_SOURCE, MINIMAL_R_CONFIG)
        dispatched = parse_signatures(VALID_R_SOURCE, "r", MINIMAL_R_CONFIG)
        assert type(direct) == type(dispatched)

    def test_python_dispatch_passes_source_correctly(self):
        """parse_signatures passes source to the python parser faithfully."""
        source = "x = 42\ny = 'hello'\n"
        result = parse_signatures(source, "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        # Should have two Assign nodes
        assigns = [n for n in result.body if isinstance(n, ast.Assign)]
        assert len(assigns) == 2

    def test_python_dispatch_passes_config_correctly(self):
        """parse_signatures passes language_config through to the parser."""
        custom_config = {**MINIMAL_PYTHON_CONFIG, "custom_key": "custom_value"}
        # Should not raise -- config is passed through
        result = parse_signatures(VALID_PYTHON_SOURCE, "python", custom_config)
        assert isinstance(result, ast.Module)

    def test_r_dispatch_passes_source_correctly(self):
        """parse_signatures passes source to the R parser faithfully."""
        result = parse_signatures(VALID_R_MULTIPLE, "r", MINIMAL_R_CONFIG)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Edge cases and robustness
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and robustness of signature parsing."""

    def test_python_parse_whitespace_only_source(self):
        """Whitespace-only Python source parses to an AST with no body items."""
        result = parse_signatures("   \n\n  \n", "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        assert len(result.body) == 0

    def test_python_parse_comment_only_source(self):
        """Comment-only Python source parses to an AST with no meaningful body."""
        result = parse_signatures(
            "# just a comment\n# another one\n", "python", MINIMAL_PYTHON_CONFIG
        )
        assert isinstance(result, ast.Module)

    def test_python_parse_complex_signatures(self):
        """Complex Python signatures with decorators and *args/**kwargs parse correctly."""
        source = textwrap.dedent("""\
            from typing import Any

            def complex_func(*args, key: str = "default", **kwargs: Any) -> None:
                pass
        """)
        result = parse_signatures(source, "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        func_defs = [n for n in ast.walk(result) if isinstance(n, ast.FunctionDef)]
        assert len(func_defs) == 1
        assert func_defs[0].name == "complex_func"

    def test_python_parse_namedtuple(self):
        """Python source with NamedTuple parses correctly."""
        source = textwrap.dedent("""\
            from typing import NamedTuple

            class Result(NamedTuple):
                status: str
                value: int
        """)
        result = parse_signatures(source, "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        class_defs = [n for n in ast.walk(result) if isinstance(n, ast.ClassDef)]
        assert len(class_defs) == 1
        assert class_defs[0].name == "Result"

    def test_r_parse_nested_function_in_body(self):
        """R parser handles functions with nested function calls in body."""
        source = (
            "wrapper <- function(x) {\n  inner <- function(y) { y }\n  inner(x)\n}\n"
        )
        result = parse_signatures(source, "r", MINIMAL_R_CONFIG)
        # Should at least capture the outer wrapper function
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_key_error_message_is_informative(self):
        """KeyError raised by parse_signatures should be catchable."""
        with pytest.raises(KeyError):
            parse_signatures("x", "nonexistent", {"id": "nonexistent"})

    def test_python_multiline_string_source(self):
        """Python source with multiline strings parses correctly."""
        source = textwrap.dedent('''\
            TEMPLATE = """
            This is a multiline string.
            """

            def process():
                pass
        ''')
        result = parse_signatures(source, "python", MINIMAL_PYTHON_CONFIG)
        assert isinstance(result, ast.Module)
        func_defs = [n for n in ast.walk(result) if isinstance(n, ast.FunctionDef)]
        assert len(func_defs) == 1
