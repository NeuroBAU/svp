"""Command Logic Scripts -- Group A utility commands.

Implements /svp:save, /svp:quit, /svp:status, /svp:clean commands.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import json
import os
import shutil
import stat
import subprocess
import tarfile


def save_project(project_root: Path) -> str:
    """Verify file integrity of state file and key documents, confirm save.

    Returns a human-readable confirmation message.
    """
    assert project_root.is_dir(), "Project root must exist"

    issues: list[str] = []
    verified: list[str] = []

    # Check pipeline_state.json integrity
    state_path = project_root / "pipeline_state.json"
    if state_path.exists():
        try:
            text = state_path.read_text(encoding="utf-8")
            json.loads(text)
            verified.append("pipeline_state.json")
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"pipeline_state.json: {e}")
    else:
        issues.append("pipeline_state.json: not found")

    # Check svp_config.json if it exists
    config_path = project_root / "svp_config.json"
    if config_path.exists():
        try:
            text = config_path.read_text(encoding="utf-8")
            json.loads(text)
            verified.append("svp_config.json")
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"svp_config.json: {e}")

    # Check key documents: stakeholder spec, blueprint
    for doc_rel in ["specs/stakeholder.md", "blueprint/blueprint.md"]:
        doc_path = project_root / doc_rel
        if doc_path.exists():
            try:
                doc_path.read_text(encoding="utf-8")
                verified.append(doc_rel)
            except OSError as e:
                issues.append(f"{doc_rel}: {e}")

    # Check ledger files in .svp directory
    svp_dir = project_root / ".svp"
    if svp_dir.exists() and svp_dir.is_dir():
        for ledger_file in svp_dir.glob("*.jsonl"):
            try:
                text = ledger_file.read_text(encoding="utf-8")
                for line_num, line in enumerate(text.splitlines(), start=1):
                    stripped = line.strip()
                    if stripped:
                        json.loads(stripped)
                verified.append(f".svp/{ledger_file.name}")
            except (json.JSONDecodeError, OSError) as e:
                issues.append(f".svp/{ledger_file.name}: {e}")

    # Build confirmation message
    parts: list[str] = []
    parts.append("Save verification complete.")

    if verified:
        parts.append(f"Verified files: {', '.join(verified)}.")

    if issues:
        parts.append(f"Issues found: {'; '.join(issues)}.")
    else:
        parts.append("All files OK.")

    result = " ".join(parts)
    assert len(result) > 0, "Save confirmation message must be non-empty"
    return result


def quit_project(project_root: Path) -> str:
    """Call save_project first, then return an exit confirmation message with save status."""
    assert project_root.is_dir(), "Project root must exist"

    save_msg = save_project(project_root)
    return f"Project saved and ready to exit. {save_msg}"


def get_status(project_root: Path) -> str:
    """Read pipeline state and produce a human-readable status report.

    Raises FileNotFoundError if pipeline_state.json is not found.
    """
    assert project_root.is_dir(), "Project root must exist"

    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError("Pipeline state file not found")

    try:
        raw_text = state_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        raise FileNotFoundError("Pipeline state file not found")

    # Extract fields from state data
    stage = data.get("stage", "unknown")
    sub_stage = data.get("sub_stage", None)
    current_unit = data.get("current_unit", None)
    total_units = data.get("total_units", None)
    alignment_iteration = data.get("alignment_iteration", 0)
    verified_units = data.get("verified_units", [])
    pass_history = data.get("pass_history", [])
    debug_history = data.get("debug_history", [])
    fix_ladder_position = data.get("fix_ladder_position", None)
    project_name = data.get("project_name", None)
    debug_session = data.get("debug_session", None)

    lines: list[str] = []
    lines.append("=== SVP Pipeline Status ===")

    if project_name:
        lines.append(f"Project: {project_name}")

    # Current stage display
    stage_display = _format_stage_display(stage, sub_stage, current_unit, total_units, pass_history)
    lines.append(f"Current stage: {stage_display}")

    # Sub-stage
    if sub_stage is not None:
        lines.append(f"Sub-stage: {sub_stage}")

    # Current unit info
    if current_unit is not None:
        unit_str = f"Current unit: {current_unit}"
        if total_units is not None:
            unit_str += f" of {total_units}"
        lines.append(unit_str)

    # Fix ladder position
    if fix_ladder_position is not None:
        lines.append(f"Fix ladder position: {fix_ladder_position}")

    # Alignment iterations
    lines.append(f"Alignment iterations used: {alignment_iteration}")

    # Verified units
    if verified_units:
        unit_nums = [str(vu.get("unit", "?")) for vu in verified_units]
        lines.append(f"Verified units: {', '.join(unit_nums)}")
    else:
        lines.append("Verified units: none")

    # Pass history summary
    if pass_history:
        lines.append("")
        lines.append("Pass history:")
        lines.append(format_pass_history(pass_history))
    else:
        lines.append("Pass history: none")

    # Debug history summary
    if debug_history:
        lines.append("")
        lines.append("Debug history:")
        lines.append(format_debug_history(debug_history))
    else:
        lines.append("Debug history: none")

    # Active debug session
    if debug_session is not None:
        lines.append("")
        lines.append("Active debug session:")
        lines.append(f"  Bug ID: {debug_session.get('bug_id', '?')}")
        lines.append(f"  Phase: {debug_session.get('phase', '?')}")
        classification = debug_session.get('classification', None)
        if classification:
            lines.append(f"  Classification: {classification}")

    # Next expected action
    next_action = _determine_next_action(stage, sub_stage, current_unit, fix_ladder_position, debug_session)
    lines.append("")
    lines.append(f"Next expected action: {next_action}")

    return "\n".join(lines)


def _format_stage_display(
    stage: str,
    sub_stage: Optional[str],
    current_unit: Optional[int],
    total_units: Optional[int],
    pass_history: list,
) -> str:
    """Return a human-readable string for the current stage."""
    if stage == "pre_stage_3":
        return "Pre-Stage 3"

    label = f"Stage {stage}"

    if stage == "0" and sub_stage is not None:
        return f"{label} ({sub_stage})"

    if stage == "3" and current_unit is not None:
        unit_part = f"Unit {current_unit}"
        if total_units is not None:
            unit_part += f" of {total_units}"
        pass_number = len(pass_history) + 1
        return f"{label}, {unit_part} (pass {pass_number})"

    return label


def _determine_next_action(
    stage: str,
    sub_stage: Optional[str],
    current_unit: Optional[int],
    fix_ladder_position: Optional[str],
    debug_session: Optional[Dict[str, Any]],
) -> str:
    """Determine the next expected action based on pipeline state."""
    if stage == "0":
        if sub_stage == "hook_activation":
            return "Activate CLAUDE.md hook"
        elif sub_stage == "project_context":
            return "Gather project context"
        return "Complete Stage 0 setup"

    if stage == "1":
        return "Draft or revise stakeholder specification"

    if stage == "2":
        return "Draft or revise blueprint"

    if stage == "pre_stage_3":
        return "Generate stubs and test harnesses"

    if stage == "3":
        if fix_ladder_position is not None:
            return f"Continue fix ladder ({fix_ladder_position})"
        if current_unit is not None:
            return f"Implement and verify Unit {current_unit}"
        return "Begin unit implementation"

    if stage == "4":
        return "Run assembly integration tests"

    if stage == "5":
        if debug_session is not None:
            phase = debug_session.get("phase", "unknown")
            return f"Debug session in progress (phase: {phase})"
        return "Project delivered -- post-delivery maintenance"

    return "Unknown stage"


def format_pass_history(pass_history: list) -> str:
    """Format pass history entries as a brief numbered list.

    Each entry shows how far the pass reached and why it ended.
    """
    if not pass_history:
        return "No pass history."

    lines: list[str] = []
    for entry in pass_history:
        pass_num = entry.get("pass_number", "?")
        reached_unit = entry.get("reached_unit", "?")
        ended_reason = entry.get("ended_reason", "unknown")
        line = f"  {pass_num}. Reached unit {reached_unit} -- {ended_reason}"
        lines.append(line)

    return "\n".join(lines)


def format_debug_history(debug_history: list) -> str:
    """Format debug history entries as a brief numbered list."""
    if not debug_history:
        return "No debug history."

    lines: list[str] = []
    for i, entry in enumerate(debug_history, start=1):
        bug_id = entry.get("bug_id", "?")
        description = entry.get("description", "")
        classification = entry.get("classification", "")
        phase = entry.get("phase", "")

        parts = [f"  {i}. Bug #{bug_id}"]
        if description:
            parts.append(f" -- {description}")
        if classification:
            parts.append(f" [{classification}]")
        if phase:
            parts.append(f" (phase: {phase})")

        lines.append("".join(parts))

    return "\n".join(lines)


def clean_workspace(project_root: Path, mode: str) -> str:
    """Clean the workspace. Only functional after Stage 5 delivery.

    Returns an error message if invoked before delivery.
    """
    assert project_root.is_dir(), "Project root must exist"
    assert mode in ("archive", "delete", "keep"), "Clean mode must be archive, delete, or keep"

    # Check if we are at Stage 5 (delivery complete)
    state_path = project_root / "pipeline_state.json"
    if state_path.exists():
        try:
            raw_text = state_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            stage = data.get("stage", "0")
            if stage != "5":
                return f"Cannot clean workspace: project is at Stage {stage}, not Stage 5 (delivery). Clean is only available after delivery."
        except (json.JSONDecodeError, OSError):
            return "Cannot clean workspace: unable to read pipeline state."
    else:
        return "Cannot clean workspace: pipeline state file not found."

    project_name = data.get("project_name", None)

    if mode == "keep":
        return "Workspace kept as-is. No cleanup performed."

    if mode == "archive":
        archive_path = archive_workspace(project_root)
        return f"Workspace archived to {archive_path} and original directory removed."

    if mode == "delete":
        # Attempt conda env removal if project_name is known
        conda_msg = ""
        if project_name:
            try:
                removed = remove_conda_env(project_name)
                if removed:
                    conda_msg = f" Conda environment '{project_name}' removed."
                else:
                    conda_msg = f" Conda environment '{project_name}' removal skipped or not found."
            except RuntimeError as e:
                conda_msg = f" Warning: {e}"

        delete_workspace(project_root)
        return f"Workspace deleted.{conda_msg}"

    # Should not reach here
    return "Unknown mode."


def archive_workspace(project_root: Path) -> Path:
    """Compress the workspace into a .tar.gz file alongside the repo, then delete the workspace directory.

    Returns the Path to the created archive.
    """
    assert project_root.is_dir(), "Project root must exist"

    parent_dir = project_root.parent
    workspace_name = project_root.name
    archive_name = f"{workspace_name}.tar.gz"
    archive_path = parent_dir / archive_name

    # Create tar.gz archive
    with tarfile.open(str(archive_path), "w:gz") as tar:
        tar.add(str(project_root), arcname=workspace_name)

    # Delete the workspace directory after archiving
    _remove_directory_with_permission_handler(project_root)

    return archive_path


def _permission_error_handler(func, path, exc_info):
    """Handle permission errors during shutil.rmtree by chmod and retry."""
    # Extract the exception
    exc_type = exc_info[1] if isinstance(exc_info, tuple) else exc_info
    if isinstance(exc_type, PermissionError) or (isinstance(exc_info, tuple) and issubclass(exc_info[0], PermissionError)):
        # Attempt to make the path and its parent writable, then retry
        try:
            parent = os.path.dirname(path)
            os.chmod(parent, stat.S_IRWXU)
            os.chmod(path, stat.S_IRWXU)
            func(path)
        except PermissionError:
            raise PermissionError(f"Cannot delete workspace: permission denied on {path}")
    else:
        # Re-raise for non-permission errors
        if isinstance(exc_info, tuple):
            raise exc_info[1]
        raise exc_type


def _remove_directory_with_permission_handler(target_dir: Path) -> None:
    """Remove a directory with a permission-aware error handler.

    On PermissionError, chmod the path and retry. If still failing, raise PermissionError.
    """
    try:
        shutil.rmtree(str(target_dir), onerror=_permission_error_handler)
    except PermissionError:
        raise


def delete_workspace(project_root: Path) -> None:
    """Remove the workspace with a permission-aware handler.

    The delivered repository (projectname-repo/) is never touched.
    chmod read-only paths and retry on PermissionError.
    """
    assert project_root.is_dir(), "Project root must exist"

    parent_dir = project_root.parent
    workspace_name = project_root.name

    # Identify the delivered repo directory (projectname-repo/)
    # The repo directory pattern is typically {projectname}-repo
    # We need to check for any *-repo directory as a sibling
    repo_dir_name = f"{workspace_name}-repo"
    repo_dir = parent_dir / repo_dir_name

    # Walk through the workspace and delete everything
    # The delivered repository is a sibling, not inside the workspace,
    # so we can safely delete the entire workspace directory
    _remove_directory_with_permission_handler(project_root)


def remove_conda_env(env_name: str) -> bool:
    """Run conda env remove -n {env_name} --yes.

    Returns True if successful.
    Raises RuntimeError if the removal fails.
    """
    try:
        result = subprocess.run(
            ["conda", "env", "remove", "-n", env_name, "--yes"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Conda environment removal failed: {env_name}")
        return True
    except FileNotFoundError:
        # conda command not found
        raise RuntimeError(f"Conda environment removal failed: {env_name}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Conda environment removal failed: {env_name}")
