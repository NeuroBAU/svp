"""Stub Generator -- Unit 6 of the SVP pipeline.

Parses machine-readable signatures from the blueprint using Python's ast module
and produces Python stub files with NotImplementedError bodies. Also generates
stubs or mocks for upstream dependencies based on their contract signatures.
Implements spec Section 10.2, including the importability invariant
(module-level assert statements are stripped).
"""

import ast
import copy
import sys
import argparse
from typing import Optional, Dict, Any, List
from pathlib import Path


def parse_signatures(signature_block: str) -> ast.Module:
    """Parse a signature block string into an AST Module.

    Calls ast.parse() on the signature block and returns the AST.
    Raises SyntaxError if the block is not valid Python.
    """
    assert len(signature_block.strip()) > 0, "Signature block must not be empty"

    try:
        tree = ast.parse(signature_block)
    except SyntaxError as e:
        raise SyntaxError(f"Blueprint signature block is not valid Python: {e}") from e

    assert isinstance(tree, ast.Module), "Parse result must be an ast.Module"
    return tree


def strip_module_level_asserts(tree: ast.Module) -> ast.Module:
    """Remove all ast.Assert nodes at the module level of the AST.

    Does not affect asserts inside function or class bodies.
    Returns the modified AST (modifies in place and returns).
    """
    tree = copy.deepcopy(tree)
    tree.body = [node for node in tree.body if not isinstance(node, ast.Assert)]
    ast.fix_missing_locations(tree)
    return tree


def _make_not_implemented_body() -> List[ast.stmt]:
    """Create a function body consisting of: raise NotImplementedError()"""
    raise_node = ast.Raise(
        exc=ast.Call(
            func=ast.Name(id="NotImplementedError", ctx=ast.Load()),
            args=[],
            keywords=[],
        ),
        cause=None,
    )
    return [raise_node]


def _replace_function_bodies(node: ast.AST) -> None:
    """Recursively replace all function bodies with raise NotImplementedError().

    For functions inside classes, also replaces their bodies.
    Preserves decorators, arguments, return annotations, etc.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.body = _make_not_implemented_body()
    elif isinstance(node, ast.ClassDef):
        new_body: List[ast.stmt] = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                child.body = _make_not_implemented_body()
                new_body.append(child)
            elif isinstance(child, ast.ClassDef):
                # Recurse into nested classes
                _replace_function_bodies(child)
                new_body.append(child)
            else:
                # Keep class-level assignments, type annotations, pass, etc.
                new_body.append(child)
        node.body = new_body if new_body else [ast.Pass()]


def generate_stub_source(parsed_ast: ast.Module) -> str:
    """Transform the AST into stub source code.

    - Replaces all function bodies with raise NotImplementedError()
    - Preserves import statements and class definitions
    - Strips module-level assert statements (importability invariant)
    """
    # Deep copy to avoid mutating the input
    tree = copy.deepcopy(parsed_ast)

    # Strip module-level asserts
    tree = strip_module_level_asserts(tree)

    # Replace function bodies
    for node in tree.body:
        _replace_function_bodies(node)

    ast.fix_missing_locations(tree)
    result = ast.unparse(tree)

    # Post-conditions
    assert "NotImplementedError" in result, "Stub source must contain NotImplementedError"
    # No module-level asserts in stub
    if "def " in result:
        assert "assert" not in result.split("def ")[0], "No module-level asserts in stub"

    return result


def generate_upstream_mocks(
    upstream_contracts: List[Dict[str, str]]
) -> Dict[str, str]:
    """Produce mock module source code for each upstream dependency.

    Each entry in upstream_contracts is a dict with keys:
      - unit_number: str
      - unit_name: str
      - signatures: str (Python code block)

    Returns a dict mapping module name (e.g. 'unit_1') to the mock source code.
    Each mock has functions that raise NotImplementedError, with module-level
    asserts stripped.
    """
    mocks: Dict[str, str] = {}

    for contract in upstream_contracts:
        unit_num = contract["unit_number"]
        signatures = contract.get("signatures", "")
        module_name = f"unit_{unit_num}"

        if not signatures or not signatures.strip():
            # No signatures -- produce an empty module
            mocks[module_name] = f"# Mock for {contract.get('unit_name', module_name)}\n"
            continue

        try:
            tree = parse_signatures(signatures)
        except (SyntaxError, AssertionError):
            # If signatures can't be parsed, produce a comment-only stub
            mocks[module_name] = (
                f"# Mock for {contract.get('unit_name', module_name)}\n"
                f"# Could not parse signatures\n"
            )
            continue

        source = generate_stub_source(tree)
        header = f"# Mock for {contract.get('unit_name', module_name)}\n"
        mocks[module_name] = header + source + "\n"

    return mocks


def write_stub_file(
    unit_number: int,
    signature_block: str,
    output_dir: Path,
) -> Path:
    """Combine parse_signatures, strip_module_level_asserts, and
    generate_stub_source to produce a stub file at {output_dir}/stub.py.

    Args:
        unit_number: The unit number (used for header comment).
        signature_block: The raw Python signature block from the blueprint.
        output_dir: The directory to write the stub file into.

    Returns:
        Path to the written stub file.

    Raises:
        SyntaxError: If the signature block is not valid Python.
        FileNotFoundError: If the output directory does not exist.
    """
    assert len(signature_block.strip()) > 0, "Signature block must not be empty"

    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    tree = parse_signatures(signature_block)
    stub_source = generate_stub_source(tree)

    header = f"# Auto-generated stub for unit {unit_number}\n"
    content = header + stub_source + "\n"

    output_path = output_dir / "stub.py"
    output_path.write_text(content, encoding="utf-8")

    # Post-conditions
    assert output_path.exists(), "Stub file must exist after write"
    assert output_path.suffix == ".py", "Stub file must be a Python file"

    return output_path


def write_upstream_stubs(
    upstream_contracts: List[Dict[str, str]],
    output_dir: Path,
) -> List[Path]:
    """Generate and write mock files for all upstream dependencies.

    Each upstream contract produces a file named 'unit_N_mock.py' in the
    output directory.

    Args:
        upstream_contracts: List of contract dicts with unit_number, unit_name,
            and signatures keys.
        output_dir: The directory to write the mock files into.

    Returns:
        List of Paths to the written mock files.

    Raises:
        FileNotFoundError: If the output directory does not exist.
    """
    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    mocks = generate_upstream_mocks(upstream_contracts)

    written_paths: List[Path] = []
    for module_name, source in mocks.items():
        file_path = output_dir / f"{module_name}_mock.py"
        file_path.write_text(source, encoding="utf-8")
        written_paths.append(file_path)

    return written_paths


def main() -> None:
    """CLI wrapper for stub generation.

    Uses extract_unit from Unit 5 to get the current unit's signatures,
    and extract_upstream_contracts for upstream mock generation.
    """
    parser = argparse.ArgumentParser(
        description="Generate Python stub files from blueprint signatures."
    )
    parser.add_argument(
        "--blueprint",
        type=Path,
        required=True,
        help="Path to the blueprint markdown file.",
    )
    parser.add_argument(
        "--unit",
        type=int,
        required=True,
        help="Unit number to generate stubs for.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write stub files into.",
    )
    parser.add_argument(
        "--upstream",
        action="store_true",
        default=False,
        help="Also generate upstream mock stubs.",
    )

    args = parser.parse_args()

    from blueprint_extractor import extract_unit, extract_upstream_contracts

    unit_def = extract_unit(args.blueprint, args.unit)
    result_path = write_stub_file(args.unit, unit_def.signatures, args.output_dir)
    print(f"Wrote stub: {result_path}")

    if args.upstream:
        upstream = extract_upstream_contracts(args.blueprint, args.unit)
        mock_paths = write_upstream_stubs(upstream, args.output_dir)
        for p in mock_paths:
            print(f"Wrote upstream mock: {p}")
