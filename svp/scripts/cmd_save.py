# Unit 11: Command Logic Scripts
# Implements /svp:save, /svp:quit, /svp:status, /svp:clean commands.

from typing import Optional, Dict, Any
from pathlib import Path
import json
import os
import shutil
import stat
import subprocess
import tarfile
from datetime import datetime


# ===========================================================================
# cmd_save.py -- save_project
# ===========================================================================


def save_project(project_root: Path) -> str:
    """Verify file integrity of state file and key documents, confirm save is complete."""
    assert project_root.is_dir(), "Project root must exist"

    state_path = project_root / "pipeline_state.json"
    files_checked = []

    # Verify state file integrity if it exists
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        files_checked.append("pipeline_state.json")

    # Verify profile if it exists
    profile_path = project_root / "project_profile.json"
    if profile_path.exists():
        profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
        assert isinstance(profile_data, dict)
        files_checked.append("project_profile.json")

    if files_checked:
        return f"Save complete. Verified: {', '.join(files_checked)}."
    else:
        return "Save complete. No state files found to verify."


# ===========================================================================
# cmd_quit.py -- quit_project
# ===========================================================================


def quit_project(project_root: Path) -> str:
    """Call save_project first, then return exit confirmation with save status."""
    assert project_root.is_dir(), "Project root must exist"

    save_msg = save_project(project_root)
    return f"Quit confirmed. Save status: {save_msg} Exiting SVP session."


# ===========================================================================
# cmd_status.py -- get_status, format_pass_history, format_debug_history,
#                  format_profile_summary, format_quality_summary
# ===========================================================================


def get_status(project_root: Path) -> str:
    """Read pipeline state and produce a human-readable status report."""
    assert project_root.is_dir(), "Project root must exist"

    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError("Pipeline state file not found")

    state_data = json.loads(state_path.read_text(encoding="utf-8"))

    stage = state_data.get("stage", "unknown")
    sub_stage = state_data.get("sub_stage")
    current_unit = state_data.get("current_unit")
    total_units = state_data.get("total_units")
    fix_ladder_position = state_data.get("fix_ladder_position")
    alignment_iteration = state_data.get("alignment_iteration", 0)
    verified_units = state_data.get("verified_units", [])
    pass_history = state_data.get("pass_history", [])
    debug_history = state_data.get("debug_history", [])
    project_name = state_data.get("project_name", "unknown")
    last_action = state_data.get("last_action")

    lines = []
    lines.append(f"=== SVP Status Report ===")
    lines.append(f"Project: {project_name}")
    lines.append(f"Stage: {stage}")
    if sub_stage:
        lines.append(f"Sub-stage: {sub_stage}")
    if current_unit is not None:
        unit_str = f"Unit: {current_unit}"
        if total_units is not None:
            unit_str += f" / {total_units}"
        lines.append(unit_str)
    if fix_ladder_position:
        lines.append(f"Fix ladder position: {fix_ladder_position}")

    lines.append(f"Alignment iteration: {alignment_iteration}")

    # Verified units
    if verified_units:
        unit_nums = [str(v["unit"]) for v in verified_units]
        lines.append(f"Verified units: [{', '.join(unit_nums)}]")
    else:
        lines.append("Verified units: none")

    # Pass history
    if pass_history:
        lines.append("Pass history:")
        lines.append(format_pass_history(pass_history))
    else:
        lines.append("Pass history: none")

    # Debug history
    if debug_history:
        lines.append("Debug history:")
        lines.append(format_debug_history(debug_history))
    else:
        lines.append("Debug history: none")

    # Pipeline toolchain
    profile_path = project_root / "project_profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            toolchain = profile.get("pipeline_toolchain", "python_conda_pytest")
            lines.append(f"Pipeline: {toolchain}")
        except (json.JSONDecodeError, KeyError):
            lines.append("Pipeline: python_conda_pytest")
    else:
        lines.append("Pipeline: python_conda_pytest")

    # Profile summary
    profile_summary = format_profile_summary(project_root)
    lines.append(f"Profile: {profile_summary}")

    # Quality summary (NEW IN 2.1)
    quality_summary = format_quality_summary(project_root)
    lines.append(f"Quality: {quality_summary}")

    # Next expected action
    if last_action:
        lines.append(f"Last action: {last_action}")

    # Determine next action
    next_action = _determine_next_action(stage, sub_stage, current_unit, fix_ladder_position)
    lines.append(f"Next expected action: {next_action}")

    return "\n".join(lines)


def _determine_next_action(
    stage: str,
    sub_stage: Optional[str],
    current_unit: Optional[int],
    fix_ladder_position: Optional[str],
) -> str:
    """Determine the next expected action based on pipeline state."""
    if stage == "0":
        if sub_stage:
            return f"Complete {sub_stage}"
        return "Complete Stage 0 setup"
    elif stage == "1":
        return "Project context gathering"
    elif stage == "2":
        return "Blueprint alignment"
    elif stage == "pre_stage_3":
        return "Pre-Stage 3 preparation"
    elif stage == "3":
        if fix_ladder_position:
            return f"Fix ladder: {fix_ladder_position}"
        if current_unit is not None:
            return f"Implement unit {current_unit}"
        return "Continue Stage 3 implementation"
    elif stage == "4":
        return "Assembly integration testing"
    elif stage == "5":
        return "Delivery complete"
    return "Unknown"


def format_pass_history(pass_history: list) -> str:
    """Format pass history entries as a brief numbered list."""
    if not pass_history:
        return "No passes recorded."

    lines = []
    for entry in pass_history:
        num = entry.get("pass_number", "?")
        reached = entry.get("reached_unit", "?")
        reason = entry.get("ended_reason", "unknown")
        lines.append(f"  {num}. Reached unit {reached}, ended: {reason}")
    return "\n".join(lines)


def format_debug_history(debug_history: list) -> str:
    """Format debug history entries as a brief numbered list."""
    if not debug_history:
        return "No debug sessions recorded."

    lines = []
    for entry in debug_history:
        bug_id = entry.get("bug_id", "?")
        resolution = entry.get("resolution", "unknown")
        description = entry.get("description", "")
        lines.append(f"  {bug_id}. {description} [{resolution}]")
    return "\n".join(lines)


def format_profile_summary(project_root: Path) -> str:
    """Read project_profile.json and return a one-line summary of key delivery preferences."""
    profile_path = project_root / "project_profile.json"
    if not profile_path.exists():
        return "Profile not yet created"

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "Profile not yet created"

    # Extract key fields
    delivery = profile.get("delivery", {})
    env_rec = delivery.get("environment_recommendation", "unknown")

    vcs = profile.get("vcs", {})
    commit_style = vcs.get("commit_style", "unknown")

    readme = profile.get("readme", {})
    readme_depth = readme.get("depth", "standard")

    license_info = profile.get("license", {})
    license_type = license_info.get("type", "unknown")

    return f"{env_rec}, {commit_style} commits, {readme_depth} README, {license_type}"


def format_quality_summary(project_root: Path) -> str:
    """Read project_profile.json and return a one-line quality tools summary.

    Returns a string like: "ruff + mypy (pipeline), ruff + none (delivery)"
    Returns "Quality tools not yet configured" if profile does not exist or is malformed.
    """
    profile_path = project_root / "project_profile.json"
    if not profile_path.exists():
        return "Quality tools not yet configured"

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "Quality tools not yet configured"

    if not isinstance(profile, dict):
        return "Quality tools not yet configured"

    # Pipeline quality tools from fixed section
    fixed = profile.get("fixed", {})
    pipeline_tools_key = fixed.get("pipeline_quality_tools", "ruff_mypy")
    # Parse pipeline tools: "ruff_mypy" -> "ruff + mypy"
    pipeline_parts = pipeline_tools_key.split("_")
    if len(pipeline_parts) >= 2:
        pipeline_linter = pipeline_parts[0]
        pipeline_checker = "_".join(pipeline_parts[1:])
    else:
        pipeline_linter = pipeline_tools_key
        pipeline_checker = "none"
    pipeline_str = f"{pipeline_linter} + {pipeline_checker}"

    # Delivery quality tools from quality section
    quality = profile.get("quality", {})
    delivery_linter = quality.get("linter", "ruff")
    delivery_checker = quality.get("type_checker", "none")
    delivery_str = f"{delivery_linter} + {delivery_checker}"

    return f"{pipeline_str} (pipeline), {delivery_str} (delivery)"


# ===========================================================================
# cmd_clean.py -- clean_workspace, archive_workspace, delete_workspace,
#                 remove_conda_env
# ===========================================================================


def clean_workspace(project_root: Path, mode: str) -> str:
    """Clean workspace after Stage 5 delivery."""
    assert mode in ("archive", "delete", "keep"), "Clean mode must be archive, delete, or keep"

    # If the workspace directory no longer exists (e.g., already cleaned),
    # return a descriptive message for non-destructive scenarios.
    if not project_root.is_dir():
        # Check if it's a path that never existed vs one that was already cleaned
        # by looking for an archive in the parent directory
        archive_candidate = project_root.parent / f"{project_root.name}.tar.gz"
        if archive_candidate.exists():
            if mode == "delete":
                return "Workspace already removed (archived)."
            elif mode == "keep":
                return "Workspace already removed (archived). Nothing to keep."
        # Truly nonexistent project root
        assert project_root.is_dir(), "Project root must exist"

    # Check if we're at Stage 5
    state_path = project_root / "pipeline_state.json"
    if state_path.exists():
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        stage = state_data.get("stage", "0")
        if stage != "5":
            return f"Error: clean_workspace is only available after Stage 5 delivery. Current stage: {stage}"
    else:
        return "Error: Pipeline state not found. Cannot determine delivery status."

    if mode == "archive":
        archive_path = archive_workspace(project_root)
        return f"Workspace archived to {archive_path}"
    elif mode == "delete":
        delete_workspace(project_root)
        return "Workspace deleted."
    elif mode == "keep":
        return "Workspace kept as-is. No cleanup performed."

    return "Unknown mode."


def archive_workspace(project_root: Path) -> Path:
    """Compress workspace into a .tar.gz file alongside the repo, then delete workspace."""
    project_name = project_root.name
    archive_name = f"{project_name}.tar.gz"
    archive_path = project_root.parent / archive_name

    with tarfile.open(str(archive_path), "w:gz") as tar:
        tar.add(str(project_root), arcname=project_name)

    # Delete the workspace directory after archiving
    shutil.rmtree(str(project_root), onerror=_permission_error_handler)

    return archive_path


def _permission_error_handler(func, path, exc_info):
    """Handle permission errors during rmtree by chmod-ing and retrying."""
    try:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        func(path)
    except OSError:
        raise PermissionError(f"Cannot delete workspace: permission denied on {path}")


def delete_workspace(project_root: Path) -> None:
    """Remove workspace with permission-aware handler."""
    if project_root.exists():
        shutil.rmtree(str(project_root), onerror=_permission_error_handler)


def remove_conda_env(env_name: str) -> bool:
    """Run conda env remove -n {env_name} --yes."""
    result = subprocess.run(
        ["conda", "env", "remove", "-n", env_name, "--yes"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Conda environment removal failed: {env_name}")
    return True


# ===========================================================================
# cmd_*_main entry points (Unit 11 public API)
# ===========================================================================


def cmd_save_main(project_root: Path) -> None:
    """Entry point for /save command."""
    if not project_root.is_dir():
        raise RuntimeError(f"Project root not found: {project_root}")
    msg = save_project(project_root)
    print(msg)


def cmd_quit_main(project_root: Path) -> None:
    """Entry point for /quit command: save then exit."""
    if not project_root.is_dir():
        raise RuntimeError(f"Project root not found: {project_root}")
    msg = quit_project(project_root)
    print(msg)
    raise SystemExit(0)


def cmd_status_main(project_root: Path) -> None:
    """Entry point for /status command."""
    if not project_root.is_dir():
        raise RuntimeError(f"Project root not found: {project_root}")
    print(get_status(project_root))


def cmd_clean_main(project_root: Path) -> None:
    """Entry point for /clean command.

    Checks Stage 5 completion and presents clean options.
    """
    if not project_root.is_dir():
        raise RuntimeError("Cannot clean: workspace not found")
    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        print("Cannot clean: no pipeline state found.")
        return
    try:
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("Cannot clean: failed to read pipeline state.")
        return
    if state_data.get("stage") != "5":
        stage = state_data.get("stage", "unknown")
        print(
            f"Cannot clean: Stage 5 not complete "
            f"(currently at stage {stage})."
        )
        return
    print("Workspace cleanup options:")
    print("  1. archive - Zip and remove workspace")
    print("  2. delete  - Remove workspace")
    print("  3. keep    - Keep workspace, remove env")
    print()
    print("Use: cmd_clean --mode <archive|delete|keep>")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Save Command")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    result = save_project(project_root)
    print(result)
    print("COMMAND_SUCCEEDED")
