"""
cmd_save.py — Command logic for /svp:save.

Flushes pipeline state to disk and verifies file integrity of all critical
SVP workspace files. Implements spec Section 13 (/svp:save).

Dependencies (coded against contract interfaces):
  - Unit 2 (pipeline_state): load_state, save_state
"""

from pathlib import Path
from typing import Tuple
import json


def run_save(project_root: Path) -> Tuple[bool, str]:
    """Trigger a state file write and verify file integrity.

    Reads the current pipeline state via Unit 2's load_state, writes it back
    via save_state (which updates the updated_at timestamp and writes atomically),
    then runs verify_file_integrity on all critical files.

    Args:
        project_root: Path to the SVP project root directory.

    Returns:
        A tuple of (success: bool, message: str). If success is True, all
        critical files (pipeline_state.json, svp_config.json, ledgers) exist
        and are valid JSON/JSONL. If False, the message describes what failed.

    Raises:
        FileNotFoundError: If pipeline_state.json is not found.
    """
    assert project_root.is_dir(), "Project root must exist"

    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError(
            "State file not found — is this an SVP project?"
        )

    # Import Unit 2 contract interfaces
    from pipeline_state import load_state, save_state

    # Load current state and write it back (triggers atomic write + timestamp update)
    state = load_state(project_root)
    save_state(state, project_root)

    # Run integrity verification
    # verify_file_integrity raises FileNotFoundError or RuntimeError on failure,
    # returns empty list on success. Catch to convert to (bool, str) return.
    try:
        issues = verify_file_integrity(project_root)
    except (FileNotFoundError, RuntimeError) as e:
        return (False, str(e))

    # If we reach here, issues is empty — all files verified
    return (True, "Save complete. All files verified — you are safe to close the terminal.")


def verify_file_integrity(project_root: Path) -> list[str]:
    """Check that all critical SVP files are present and parseable.

    Checks:
      - pipeline_state.json: exists and is valid JSON
      - svp_config.json: exists and is valid JSON
      - All .jsonl files in ledgers/: each line is valid JSON
      - All marker files in .svp/markers/: readable

    On success (all files intact), returns an empty list.
    On failure, raises the appropriate exception.

    Args:
        project_root: Path to the SVP project root directory.

    Returns:
        An empty list when all critical files are intact.

    Raises:
        FileNotFoundError: "State file not found — is this an SVP project?"
            when pipeline_state.json is missing.
        RuntimeError: "File integrity check failed: {files}" when any other
            critical files are corrupted or missing.
    """
    assert project_root.is_dir(), "Project root must exist"

    # Special case: missing pipeline_state.json means this isn't an SVP project
    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError(
            "State file not found — is this an SVP project?"
        )

    issues: list[str] = []

    # Check pipeline_state.json parsability
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError:
        issues.append("pipeline_state.json")

    # Check svp_config.json
    config_path = project_root / "svp_config.json"
    if not config_path.exists():
        issues.append("svp_config.json")
    else:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError:
            issues.append("svp_config.json")

    # Check all ledger files in ledgers/
    ledgers_dir = project_root / "ledgers"
    if ledgers_dir.is_dir():
        for ledger_file in sorted(ledgers_dir.glob("*.jsonl")):
            try:
                with open(ledger_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        stripped = line.strip()
                        if stripped:
                            json.loads(stripped)
            except json.JSONDecodeError:
                issues.append(f"ledgers/{ledger_file.name}")

    # Check marker files in .svp/markers/
    markers_dir = project_root / ".svp" / "markers"
    if markers_dir.is_dir():
        for marker_file in sorted(markers_dir.iterdir()):
            if marker_file.is_file():
                try:
                    marker_file.read_text(encoding="utf-8")
                except Exception:
                    issues.append(f".svp/markers/{marker_file.name}")

    # Raise RuntimeError if any issues were found
    if issues:
        raise RuntimeError(f"File integrity check failed: {issues}")

    return issues
