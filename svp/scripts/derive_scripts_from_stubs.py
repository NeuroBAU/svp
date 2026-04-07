#!/usr/bin/env python3
"""Derive workspace scripts from unit stubs by rewriting imports.

The unit stubs (src/unit_N/stub.py) use `from src.unit_N.stub import ...`
style imports. The workspace scripts (scripts/<module>.py) use flat module
imports like `from module_name import ...`. This script rewrites imports
from stub style to script style, making the stub the single source of truth.

Usage:
    python3 derive_scripts_from_stubs.py [--dry-run] [--workspace DIR]

Bug S3-98: Permanent fix for stub/script desync that caused S3-90 and S3-97.
"""

import re
import sys
from pathlib import Path

# Map from stub import path to flat module name
IMPORT_REWRITE_MAP = {
    "src.unit_1.stub": "svp_config",
    "src.unit_2.stub": "language_registry",
    "src.unit_3.stub": "profile_schema",
    "src.unit_4.stub": "toolchain_reader",
    "src.unit_5.stub": "pipeline_state",
    "src.unit_6.stub": "state_transitions",
    "src.unit_7.stub": "ledger_manager",
    "src.unit_8.stub": "blueprint_extractor",
    "src.unit_9.stub": "signature_parser",
    "src.unit_10.stub": "stub_generator",
    "src.unit_11.stub": "infrastructure_setup",
    "src.unit_12.stub": "hint_prompt_assembler",
    "src.unit_13.stub": "prepare_task",
    "src.unit_14.stub": "routing",
    "src.unit_15.stub": "quality_gate",
    # Note: src.unit_16.stub is NOT in this map — handled specially below
    "src.unit_23.stub": "generate_assembly_map",
    "src.unit_28.stub": "structural_check",
    "src.unit_29.stub": "svp_launcher",
}

# Map from unit stub path to script filename(s)
# Some units produce multiple scripts (e.g., unit_14 → routing.py, run_tests.py, update_state.py)
# For derivation, we only handle the primary stub.py → primary script mapping.
STUB_TO_SCRIPT = {
    "src/unit_1/stub.py": "scripts/svp_config.py",
    "src/unit_2/stub.py": "scripts/language_registry.py",
    "src/unit_3/stub.py": "scripts/profile_schema.py",
    "src/unit_4/stub.py": "scripts/toolchain_reader.py",
    "src/unit_5/stub.py": "scripts/pipeline_state.py",
    "src/unit_6/stub.py": "scripts/state_transitions.py",
    "src/unit_7/stub.py": "scripts/ledger_manager.py",
    "src/unit_8/stub.py": "scripts/blueprint_extractor.py",
    "src/unit_9/stub.py": "scripts/signature_parser.py",
    "src/unit_10/stub.py": "scripts/stub_generator.py",
    "src/unit_11/stub.py": "scripts/infrastructure_setup.py",
    "src/unit_12/stub.py": "scripts/hint_prompt_assembler.py",
    "src/unit_13/stub.py": "scripts/prepare_task.py",
    "src/unit_14/stub.py": "scripts/routing.py",
    "src/unit_15/stub.py": "scripts/quality_gate.py",
    "src/unit_16/stub.py": "scripts/sync_debug_docs.py",
    "src/unit_23/stub.py": "scripts/generate_assembly_map.py",
    "src/unit_28/stub.py": "scripts/structural_check.py",
    "src/unit_29/stub.py": "scripts/svp_launcher.py",
}

# Unit 16 has multiple scripts. Map imported names to their correct module.
# sync_pass1_artifacts and sync_debug_docs live in sync_debug_docs.py;
# cmd_save, cmd_quit, cmd_status, cmd_clean live in both cmd_save.py and
# sync_debug_docs.py. Default to sync_debug_docs for all Unit 16 imports.
UNIT_16_IMPORT_TO_MODULE = {
    "sync_pass1_artifacts": "sync_debug_docs",
    "sync_debug_docs": "sync_debug_docs",
    "cmd_save": "sync_debug_docs",
    "cmd_quit": "sync_debug_docs",
    "cmd_status": "sync_debug_docs",
    "cmd_clean": "sync_debug_docs",
}


def rewrite_imports(content: str) -> str:
    """Rewrite stub-style imports to script-style flat imports.

    Handles:
    - `from src.unit_N.stub import X` → `from module_name import X`
    - `import src.unit_N.stub` → `import module_name`
    - Inside strings (patch targets): `"src.unit_N.stub.X"` → `"module_name.X"`
    """
    lines = content.split("\n")
    result = []

    for line in lines:
        rewritten = _rewrite_line(line)
        result.append(rewritten)

    return "\n".join(result)


def _rewrite_line(line: str) -> str:
    """Rewrite a single line's imports."""
    stripped = line.lstrip()

    # Handle: from src.unit_N.stub import X
    match = re.match(r"^(\s*)from (src\.unit_\d+\.stub) import (.+)$", line)
    if match:
        indent, stub_path, imports = match.groups()
        module = IMPORT_REWRITE_MAP.get(stub_path)
        if module:
            return f"{indent}from {module} import {imports}"

    # Handle: import src.unit_N.stub
    match = re.match(r"^(\s*)import (src\.unit_\d+\.stub)\s*$", line)
    if match:
        indent, stub_path = match.groups()
        module = IMPORT_REWRITE_MAP.get(stub_path)
        if module:
            return f"{indent}import {module}"

    # Handle: from src.unit_16.stub import X (special case - context-dependent)
    match = re.match(r"^(\s*)from src\.unit_16\.stub import (.+)$", line)
    if match:
        indent, imports = match.groups()
        # Determine target module from the first imported name
        first_import = imports.split(",")[0].strip().split(" ")[0]
        module = UNIT_16_IMPORT_TO_MODULE.get(first_import, "sync_debug_docs")
        return f"{indent}from {module} import {imports}"

    return line


def derive_script(workspace: Path, stub_path: str, script_path: str,
                  dry_run: bool = False) -> bool:
    """Derive a script from its stub by rewriting imports.

    Returns True if the script was updated (or would be in dry-run mode).
    """
    stub_file = workspace / stub_path
    script_file = workspace / script_path

    if not stub_file.exists():
        return False

    stub_content = stub_file.read_text()
    derived_content = rewrite_imports(stub_content)

    if script_file.exists():
        current_content = script_file.read_text()
        if current_content == derived_content:
            return False  # Already in sync

    if dry_run:
        print(f"  [dry-run] derive {script_path} from {stub_path}")
    else:
        script_file.write_text(derived_content)
        print(f"  derived: {script_path} from {stub_path}")

    return True


def derive_all(workspace: Path, dry_run: bool = False) -> int:
    """Derive all scripts from their stubs. Returns count of updated files."""
    updated = 0
    for stub_path, script_path in sorted(STUB_TO_SCRIPT.items()):
        if derive_script(workspace, stub_path, script_path, dry_run):
            updated += 1
    return updated


def main():
    dry_run = "--dry-run" in sys.argv
    workspace_arg = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--workspace" and i + 1 < len(sys.argv):
            workspace_arg = sys.argv[i + 1]

    workspace = Path(workspace_arg) if workspace_arg else Path(".")
    updated = derive_all(workspace, dry_run)

    if updated == 0:
        print("  All scripts already match their stubs.")
    else:
        mode = "would derive" if dry_run else "derived"
        print(f"  {mode} {updated} script(s) from stubs.")


if __name__ == "__main__":
    main()
