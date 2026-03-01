"""
Additional coverage tests for Unit 6: Stub Generator

These tests address gaps identified by comparing the blueprint's behavioral
contracts against the existing test suite.

## Synthetic Data Assumptions

DATA ASSUMPTION: Upstream contracts are represented as a list of dicts, each
containing `unit_number`, `unit_name`, and `signatures` keys (as returned by
Unit 5's `extract_upstream_contracts`).

DATA ASSUMPTION: The CLI wrapper `main()` uses Unit 5's `extract_unit` and
`extract_upstream_contracts` functions, which are mocked to avoid actual
blueprint file I/O.

DATA ASSUMPTION: Output directories exist as real filesystem directories
(created via tmp_path).
"""

import ast
import inspect
import textwrap
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from svp.scripts.stub_generator import (
    generate_stub_source,
    generate_upstream_mocks,
    main,
    parse_signatures,
    strip_module_level_asserts,
    write_stub_file,
    write_upstream_stubs,
)


# ---------------------------------------------------------------------------
# Synthetic data (reused from primary test file where appropriate)
# ---------------------------------------------------------------------------

MINIMAL_SIGNATURE_BLOCK = "def foo() -> None: ..."

# DATA ASSUMPTION: Upstream contracts follow the format returned by
# Unit 5's extract_upstream_contracts.
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

SINGLE_UPSTREAM_CONTRACT = [
    {
        "unit_number": "3",
        "unit_name": "Gamma Module",
        "signatures": "def gamma_func(z: float) -> float: ...",
    },
]


# ---------------------------------------------------------------------------
# Gap 1: main() signature and importability
# ---------------------------------------------------------------------------

class TestMainSignature:
    """Verify that main() has the documented signature and is importable."""

    def test_main_is_callable(self):
        """main() should be importable and callable (CLI wrapper)."""
        assert callable(main)

    def test_main_accepts_no_arguments(self):
        """main() takes no arguments per the blueprint signature."""
        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert params == []


# ---------------------------------------------------------------------------
# Gap 2: FileNotFoundError includes path for write_upstream_stubs
# ---------------------------------------------------------------------------

class TestWriteUpstreamStubsErrorPath:
    """Verify FileNotFoundError from write_upstream_stubs includes the path."""

    def test_file_not_found_includes_path(self, tmp_path: Path):
        """FileNotFoundError message should include the missing directory path.

        Blueprint error format: 'Output directory does not exist: {path}'
        """
        missing_dir = tmp_path / "missing_upstream_dir"
        with pytest.raises(FileNotFoundError) as exc_info:
            write_upstream_stubs(
                upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
                output_dir=missing_dir,
            )
        msg = str(exc_info.value)
        assert "Output directory does not exist" in msg
        assert str(missing_dir) in msg


# ---------------------------------------------------------------------------
# Gap 3: generate_upstream_mocks preserves class definitions
# ---------------------------------------------------------------------------

class TestUpstreamMocksClassDefinitions:
    """Verify upstream mocks handle class definitions from contracts."""

    def test_mock_contains_class_definitions(self):
        """Mock source for an upstream contract with a class should contain
        the class name from the contract signatures.

        DATA ASSUMPTION: SAMPLE_UPSTREAM_CONTRACTS[1] contains a BetaHelper class.
        """
        result = generate_upstream_mocks(SAMPLE_UPSTREAM_CONTRACTS)
        all_sources = " ".join(result.values())
        assert "BetaHelper" in all_sources

    def test_mock_contains_not_implemented_error(self):
        """Upstream mock source should contain NotImplementedError for function stubs.

        The blueprint says mocks are produced 'based on their contract signatures',
        implying function bodies are replaced with NotImplementedError.
        """
        result = generate_upstream_mocks(SINGLE_UPSTREAM_CONTRACT)
        all_sources = " ".join(result.values())
        assert "NotImplementedError" in all_sources

    def test_mock_for_multiple_upstreams_contains_all_functions(self):
        """Mock source for multiple upstream contracts should contain all
        function names from all contracts."""
        result = generate_upstream_mocks(SAMPLE_UPSTREAM_CONTRACTS)
        all_sources = " ".join(result.values())
        assert "alpha_func" in all_sources
        assert "beta_func" in all_sources


# ---------------------------------------------------------------------------
# Gap 4: write_upstream_stubs file content verification
# ---------------------------------------------------------------------------

class TestWriteUpstreamStubsContent:
    """Verify that files written by write_upstream_stubs contain expected content."""

    def test_written_files_contain_not_implemented(self, tmp_path: Path):
        """Written upstream stub files should contain NotImplementedError.

        DATA ASSUMPTION: The mock files generated from valid contracts
        should have function bodies replaced with raise NotImplementedError().
        """
        result = write_upstream_stubs(
            upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
            output_dir=tmp_path,
        )
        for p in result:
            content = p.read_text(encoding="utf-8")
            assert "NotImplementedError" in content

    def test_written_files_contain_function_names(self, tmp_path: Path):
        """Written upstream stub files should contain the function names
        from the contract signatures."""
        result = write_upstream_stubs(
            upstream_contracts=SINGLE_UPSTREAM_CONTRACT,
            output_dir=tmp_path,
        )
        all_content = " ".join(p.read_text(encoding="utf-8") for p in result)
        assert "gamma_func" in all_content


# ---------------------------------------------------------------------------
# Gap 5: write_stub_file output path is in output_dir
# ---------------------------------------------------------------------------

class TestWriteStubFileOutputLocation:
    """Verify write_stub_file produces the stub in the correct directory."""

    def test_stub_file_parent_is_output_dir(self, tmp_path: Path):
        """The returned path's parent directory should be the output_dir.

        Blueprint: stub file at {output_dir}/stub.py.
        """
        result = write_stub_file(
            unit_number=1,
            signature_block=MINIMAL_SIGNATURE_BLOCK,
            output_dir=tmp_path,
        )
        assert result.parent == tmp_path


# ---------------------------------------------------------------------------
# Gap 6: main() CLI wrapper behavioral contract with mocked dependencies
# ---------------------------------------------------------------------------

class TestMainCLIWrapper:
    """Verify main() CLI wrapper delegates to the correct functions.

    Blueprint: 'The CLI wrapper uses extract_unit for the current unit's
    signatures' and 'Uses extract_upstream_contracts to obtain upstream
    contract signatures for mock generation.'
    """

    def test_main_calls_extract_unit_and_write_stub(self, tmp_path: Path):
        """main() should call extract_unit from Unit 5 and write_stub_file.

        DATA ASSUMPTION: We mock sys.argv, extract_unit, and
        extract_upstream_contracts to isolate the CLI wrapper behavior.
        The local import inside main() targets svp.scripts.blueprint_extractor, so we
        patch there.
        """
        mock_unit_def = MagicMock()
        mock_unit_def.signatures = MINIMAL_SIGNATURE_BLOCK

        blueprint_path = tmp_path / "blueprint.md"
        blueprint_path.write_text("# fake blueprint", encoding="utf-8")

        with patch("sys.argv", [
            "generate_stubs.py",
            "--blueprint", str(blueprint_path),
            "--unit", "1",
            "--output-dir", str(tmp_path),
        ]), patch(
            "svp.scripts.blueprint_extractor.extract_unit", return_value=mock_unit_def
        ) as mock_extract, patch(
            "svp.scripts.blueprint_extractor.extract_upstream_contracts"
        ):
            main()

        mock_extract.assert_called_once_with(blueprint_path, 1)

        # Verify the stub file was actually written
        stub_path = tmp_path / "stub.py"
        assert stub_path.exists()

    def test_main_with_upstream_flag(self, tmp_path: Path):
        """main() with --upstream flag should also call extract_upstream_contracts
        and write_upstream_stubs.

        DATA ASSUMPTION: The --upstream flag triggers upstream mock generation.
        """
        mock_unit_def = MagicMock()
        mock_unit_def.signatures = MINIMAL_SIGNATURE_BLOCK

        blueprint_path = tmp_path / "blueprint.md"
        blueprint_path.write_text("# fake blueprint", encoding="utf-8")

        with patch("sys.argv", [
            "generate_stubs.py",
            "--blueprint", str(blueprint_path),
            "--unit", "1",
            "--output-dir", str(tmp_path),
            "--upstream",
        ]), patch(
            "svp.scripts.blueprint_extractor.extract_unit", return_value=mock_unit_def
        ), patch(
            "svp.scripts.blueprint_extractor.extract_upstream_contracts",
            return_value=SINGLE_UPSTREAM_CONTRACT,
        ) as mock_upstream:
            main()

        mock_upstream.assert_called_once_with(blueprint_path, 1)

        # Verify the stub file was written
        stub_path = tmp_path / "stub.py"
        assert stub_path.exists()


# ---------------------------------------------------------------------------
# Gap 7: generate_upstream_mocks keys map to expected module names
# ---------------------------------------------------------------------------

class TestUpstreamMockKeys:
    """Verify generate_upstream_mocks uses correct module naming."""

    def test_mock_keys_use_unit_number(self):
        """The dict keys returned by generate_upstream_mocks should
        identify each upstream dependency by unit number.

        DATA ASSUMPTION: The implementation names mocks using the unit_number
        from the contract (e.g., 'unit_1', 'unit_2').
        """
        result = generate_upstream_mocks(SAMPLE_UPSTREAM_CONTRACTS)
        # Each upstream contract should have a corresponding key
        for contract in SAMPLE_UPSTREAM_CONTRACTS:
            unit_num = contract["unit_number"]
            expected_key = f"unit_{unit_num}"
            assert expected_key in result, (
                f"Expected key '{expected_key}' not found in mock keys: "
                f"{list(result.keys())}"
            )
