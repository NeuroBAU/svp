"""
setup_infrastructure.py — CLI wrapper for pre-Stage-3 infrastructure setup.

Reads the blueprint, extracts dependencies, creates the Conda environment,
validates imports, and scaffolds the project directory structure.

Usage:
    python scripts/setup_infrastructure.py [--project-root PATH]
"""

from pathlib import Path
import argparse
import re
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SVP Infrastructure Setup — pre-Stage-3 environment and directory scaffolding."
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Path to the project workspace root (defaults to current directory).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    project_root = Path(args.project_root) if args.project_root else Path.cwd()

    # Ensure scripts/ is on the import path
    scripts_dir = project_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from dependency_extractor import run_infrastructure_setup
        from svp.scripts.pipeline_state import load_state
    except ImportError as e:
        print(f"ERROR: Failed to import SVP modules: {e}", file=sys.stderr)
        return 1

    try:
        state = load_state(project_root)
        project_name = state.project_name or project_root.name
    except Exception as e:
        print(f"ERROR: Failed to load pipeline state: {e}", file=sys.stderr)
        return 1

    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if not blueprint_path.exists():
        print(f"ERROR: Blueprint not found: {blueprint_path}", file=sys.stderr)
        return 1

    print(f"Setting up infrastructure for project: {project_name}")
    print(f"Blueprint: {blueprint_path}")
    print()

    try:
        success, errors = run_infrastructure_setup(
            blueprint_path=blueprint_path,
            project_name=project_name,
            project_root=project_root,
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: Blueprint parse error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"ERROR: Infrastructure setup failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return 1

    if not success:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    # Set total_units in pipeline state so unit_completion logic works correctly
    try:
        import json
        text = blueprint_path.read_text(encoding="utf-8")
        unit_nums = re.findall(r"^## Unit (\d+)\b", text, re.MULTILINE)
        total_units = max(int(n) for n in unit_nums) if unit_nums else 0
        if total_units:
            state_path = project_root / ".svp" / "pipeline_state.json"
            if not state_path.exists():
                state_path = project_root / "pipeline_state.json"
            if state_path.exists():
                state_data = json.loads(state_path.read_text(encoding="utf-8"))
                state_data["total_units"] = total_units
                state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
                print(f"  Total units set to {total_units}")
    except Exception as e:
        print(f"  Warning: Could not set total_units: {e}", file=sys.stderr)

    print("INFRASTRUCTURE_SETUP_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
