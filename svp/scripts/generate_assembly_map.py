"""generate_assembly_map.py -- Assembly map generator.

Parses the blueprint file tree annotations and produces assembly_map.json,
a bidirectional mapping between workspace paths and delivered repo paths.

Part of Unit 23: Utility Agent Definitions and Assembly Dispatch.
"""

from pathlib import Path

from adapt_regression_tests import generate_assembly_map

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate assembly map from blueprint."
    )
    parser.add_argument(
        "--blueprint-dir",
        type=str,
        required=True,
        help="Path to the blueprint directory.",
    )
    parser.add_argument(
        "--project-root", type=str, required=True, help="Path to the project root."
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Output path for assembly_map.json."
    )
    args = parser.parse_args()

    blueprint_dir = Path(args.blueprint_dir)
    project_root = Path(args.project_root)
    assembly_map = generate_assembly_map(blueprint_dir, project_root)

    import json

    output_path = (
        Path(args.output)
        if args.output
        else project_root / ".svp" / "assembly_map.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(assembly_map, f, indent=2)
    print(f"Assembly map written to {output_path}")
