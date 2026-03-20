"""adapt_regression_tests.py -- Adapt carry-forward regression test imports.

When SVP N builds SVP N+1, carry-forward regression tests import from SVP N's
module names. If SVP N+1 reorganizes modules, these imports break. This script
reads a JSON mapping file and applies text replacements to all .py files in a
target directory.

Handles:
- from old_module import X -> from new_module import X
- import old_module -> import new_module
- @patch("old_module.X") -> @patch("new_module.X")
- patch("old_module.X") -> patch("new_module.X") (context manager form)

Usage:
    python scripts/adapt_regression_tests.py --target tests/regressions/ --map regression_test_import_map.json [--dry-run]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_mapping(map_path: Path) -> Dict[str, Dict[str, str]]:
    """Load the import mapping JSON file."""
    with open(map_path, encoding="utf-8") as f:
        return json.load(f)


def build_replacements(mapping: Dict[str, Dict[str, str]]) -> List[Tuple[re.Pattern, str]]:
    """Build ordered list of (pattern, replacement) from the mapping.

    Processes longer matches first to avoid partial replacements.
    """
    replacements: List[Tuple[re.Pattern, str]] = []

    # module_renames: "old_module.func" -> "new_module.func"
    renames = mapping.get("module_renames", {})
    # Sort by length descending so "svp_config.get_framework_packages" matches before "svp_config"
    for old, new in sorted(renames.items(), key=lambda x: len(x[0]), reverse=True):
        old_escaped = re.escape(old)
        # Handle dotted paths in import statements: from old_module import func
        if "." in old:
            old_module, old_name = old.rsplit(".", 1)
            new_module, new_name = new.rsplit(".", 1)
            old_mod_escaped = re.escape(old_module)
            new_mod_escaped = new_module
            # from old_module import ... old_name ...
            replacements.append((
                re.compile(rf"(from\s+){old_mod_escaped}(\s+import\s+)"),
                rf"\g<1>{new_mod_escaped}\g<2>",
            ))
        # patch("old.path") and @patch("old.path")
        replacements.append((
            re.compile(rf'(patch\(["\']){old_escaped}(["\'])'),
            rf"\g<1>{re.escape(new)}\g<2>",
        ))
        # Direct string references in patch targets
        replacements.append((
            re.compile(rf'"{old_escaped}"'),
            f'"{new}"',
        ))

    # module_aliases: "old_module_name" -> "new_module_name"
    aliases = mapping.get("module_aliases", {})
    for old, new in sorted(aliases.items(), key=lambda x: len(x[0]), reverse=True):
        old_escaped = re.escape(old)
        # from old_module import ...
        replacements.append((
            re.compile(rf"(from\s+){old_escaped}(\s+import)"),
            rf"\g<1>{new}\g<2>",
        ))
        # import old_module
        replacements.append((
            re.compile(rf"(^import\s+){old_escaped}(\s*$)", re.MULTILINE),
            rf"\g<1>{new}\g<2>",
        ))
        # import old_module as ...
        replacements.append((
            re.compile(rf"(import\s+){old_escaped}(\s+as\s+)"),
            rf"\g<1>{new}\g<2>",
        ))
        # patch("old_module.anything")
        replacements.append((
            re.compile(rf'(patch\(["\']){old_escaped}\.'),
            rf"\g<1>{new}.",
        ))

    return replacements


def adapt_file(file_path: Path, replacements: List[Tuple[re.Pattern, str]]) -> Tuple[bool, int]:
    """Apply replacements to a single file. Returns (changed, replacement_count)."""
    content = file_path.read_text(encoding="utf-8")
    original = content
    count = 0

    for pattern, repl in replacements:
        new_content, n = pattern.subn(repl, content)
        if n > 0:
            content = new_content
            count += n

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return True, count
    return False, 0


def adapt_directory(
    target_dir: Path,
    mapping: Dict[str, Dict[str, str]],
    dry_run: bool = False,
) -> Dict[str, int]:
    """Adapt all .py files in the target directory. Returns {filename: replacement_count}."""
    replacements = build_replacements(mapping)
    results: Dict[str, int] = {}

    py_files = sorted(target_dir.glob("*.py"))
    for fpath in py_files:
        if fpath.name.startswith("__"):
            continue
        if dry_run:
            content = fpath.read_text(encoding="utf-8")
            count = 0
            for pattern, _ in replacements:
                count += len(pattern.findall(content))
            if count > 0:
                results[fpath.name] = count
        else:
            changed, count = adapt_file(fpath, replacements)
            if changed:
                results[fpath.name] = count

    return results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Adapt carry-forward regression test imports for module reorganization"
    )
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Directory containing regression test files",
    )
    parser.add_argument(
        "--map",
        type=str,
        required=True,
        help="Path to regression_test_import_map.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    args = parser.parse_args()

    target_dir = Path(args.target)
    map_path = Path(args.map)

    if not target_dir.is_dir():
        print(f"Error: target directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)
    if not map_path.exists():
        # No mapping file = no adaptations needed
        print("No import mapping file found. Skipping regression test adaptation.")
        sys.exit(0)

    mapping = load_mapping(map_path)
    if not mapping.get("module_renames") and not mapping.get("module_aliases"):
        print("Import mapping is empty. No adaptations needed.")
        sys.exit(0)

    results = adapt_directory(target_dir, mapping, dry_run=args.dry_run)

    if results:
        action = "Would adapt" if args.dry_run else "Adapted"
        print(f"{action} {len(results)} files:")
        for fname, count in sorted(results.items()):
            print(f"  {fname}: {count} replacements")
    else:
        print("No adaptations needed.")

    sys.exit(0)


if __name__ == "__main__":
    main()
