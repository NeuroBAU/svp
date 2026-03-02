"""
generate_stubs.py — CLI wrapper for stub generation (pre-red-run step).

Reads the blueprint for the given unit, extracts the Tier 2 signature block
and upstream contracts, then calls stub_generator.generate_unit_stubs() to
produce stub files with NotImplementedError bodies in src/unit_N/ and
upstream mocks in tests/unit_N/mocks/.

Usage:
    python scripts/generate_stubs.py --unit N [--project-root PATH]
"""

from pathlib import Path
import argparse
import sys
import re


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SVP Stub Generator CLI — wraps stub_generator.py."
    )
    parser.add_argument("--unit", type=int, required=True,
                        help="Unit number to generate stubs for.")
    parser.add_argument("--project-root", type=str, default=None,
                        help="Path to the project workspace root (defaults to cwd).")
    return parser.parse_args(argv)


def _extract_from_blueprint(blueprint_path, unit_number):
    """Extract signature block and upstream contracts from blueprint markdown."""
    text = blueprint_path.read_text(encoding="utf-8")

    # Find unit section
    unit_match = re.search(r'^## Unit ' + str(unit_number) + r'\b', text, re.MULTILINE)
    if not unit_match:
        raise ValueError(f"Unit {unit_number} not found in blueprint")

    next_unit = re.search(r'^## Unit \d+', text[unit_match.end():], re.MULTILINE)
    unit_section = (text[unit_match.start(): unit_match.start() + next_unit.start()]
                    if next_unit else text[unit_match.start():])

    # Find Tier 2 Signatures block
    tier2 = re.search(
        r'^### Tier 2\s*[-\u2014\u2013]+\s*(?:Machine-Readable\s+)?Signatures',
        unit_section, re.MULTILINE
    )
    if not tier2:
        # Check for Structural Schema (non-Python unit)
        structural = re.search(
            r'^### Tier 2\s*[-\u2014\u2013]+\s*Structural\s+Schema',
            unit_section, re.MULTILINE
        )
        if structural:
            # Non-Python unit — return empty sig_block and no upstream contracts
            return "", []
        raise ValueError(f"No Tier 2 Signatures section for Unit {unit_number}")

    code_match = re.search(r'```python\n(.*?)```', unit_section[tier2.end():], re.DOTALL)
    if not code_match:
        raise ValueError(f"No Python code block in Tier 2 Signatures for Unit {unit_number}")

    sig_block = code_match.group(1)

    # Extract upstream contracts from Dependencies section
    upstream_contracts = []
    deps_match = re.search(
        r'### Tier 3.*?Dependencies(.*?)(?=^##|\Z)',
        unit_section, re.DOTALL | re.MULTILINE
    )
    if deps_match:
        dep_units = re.findall(r'Unit (\d+)', deps_match.group(1))
        for dep_num_str in dep_units:
            dep_num = int(dep_num_str)
            dep_match = re.search(r'^## Unit ' + str(dep_num) + r'\b', text, re.MULTILINE)
            if not dep_match:
                continue
            next_dep = re.search(r'^## Unit \d+', text[dep_match.end():], re.MULTILINE)
            dep_section = (text[dep_match.start(): dep_match.start() + next_dep.start()]
                           if next_dep else text[dep_match.start():])
            name_match = re.match(r'## Unit \d+: (.+)', dep_section)
            dep_name = name_match.group(1).strip() if name_match else f"Unit {dep_num}"
            dep_tier2 = re.search(
                r'^### Tier 2\s*[-\u2014\u2013]+\s*(?:Machine-Readable\s+)?Signatures',
                dep_section, re.MULTILINE
            )
            if dep_tier2:
                dep_code = re.search(
                    r'```python\n(.*?)```', dep_section[dep_tier2.end():], re.DOTALL
                )
                if dep_code:
                    upstream_contracts.append({
                        "unit_number": dep_num,
                        "unit_name": dep_name,
                        "signature_block": dep_code.group(1),
                    })

    return sig_block, upstream_contracts


def main(argv=None) -> int:
    args = parse_args(argv)
    project_root = Path(args.project_root) if args.project_root else Path.cwd()
    unit = args.unit

    # Ensure scripts/ is on the import path
    scripts_dir = project_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from stub_generator import write_stub_file, write_upstream_stubs
    except ImportError as e:
        print(f"ERROR: Failed to import stub_generator: {e}", file=sys.stderr)
        return 1

    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if not blueprint_path.exists():
        print(f"ERROR: Blueprint not found: {blueprint_path}", file=sys.stderr)
        return 1

    try:
        sig_block, upstream_contracts = _extract_from_blueprint(blueprint_path, unit)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Set up output directories
    unit_dir = project_root / "src" / f"unit_{unit}"
    test_dir = project_root / "tests" / f"unit_{unit}"
    unit_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # Write __init__.py files to make directories importable
    (project_root / "src" / "__init__.py").touch()
    (unit_dir / "__init__.py").touch()
    (project_root / "tests" / "__init__.py").touch()
    (test_dir / "__init__.py").touch()

    # Handle non-Python units (empty signature block)
    if not sig_block.strip():
        stub_path = unit_dir / "stub.py"
        stub_path.write_text(
            "# Auto-generated stub — non-Python artifact unit\n"
            "# This unit produces non-Python artifacts (config files, agent definitions, etc.)\n"
            "# Any function call will raise NotImplementedError until implemented.\n"
            "\n"
            "def __getattr__(name):\n"
            "    def _stub(*args, **kwargs):\n"
            "        raise NotImplementedError(\n"
            "            f\"Non-Python artifact unit: {name} not yet implemented\")\n"
            "    return _stub\n",
            encoding="utf-8",
        )
        print(f"  Stub written: {stub_path.relative_to(project_root)} (non-Python placeholder)")
        print("STUB_GENERATION_COMPLETE")
        return 0

    try:
        stub_path = write_stub_file(unit, sig_block, unit_dir)
        print(f"  Stub written: {stub_path.relative_to(project_root)}")

        if upstream_contracts:
            # Create mocks directory
            mocks_dir = test_dir / "mocks"
            mocks_dir.mkdir(parents=True, exist_ok=True)
            mock_paths = write_upstream_stubs(upstream_contracts, mocks_dir)
            for p in mock_paths:
                print(f"  Mock written: {p.relative_to(project_root)}")
    except SyntaxError as e:
        print(f"ERROR: Stub generation failed (invalid signatures): {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return 1

    print("STUB_GENERATION_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
