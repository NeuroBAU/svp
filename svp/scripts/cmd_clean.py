"""
cmd_clean.py — Command logic for /svp:clean.

Manages workspace cleanup after Stage 5 delivery is complete. Three modes:
archive (compress then delete), delete (remove), keep (no-op).
Implements spec Section 13 (/svp:clean).

Dependencies (coded against contract interfaces):
  - Unit 2 (pipeline_state): load_state, PipelineState
"""

from pathlib import Path
from typing import Tuple
import shutil
import subprocess
import sys
import tarfile




def _force_remove(func, path, exc_info):
    """Error handler for shutil.rmtree — chmod and retry on permission errors."""
    import os
    import stat
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        func(path)
    except Exception:
        pass  # Best effort — ignore if still fails


def _remove_conda_env(project_name: str) -> str:
    """Remove the project conda environment if it exists.

    Returns a short status message. Never raises — failure is reported
    in the message so the workspace deletion can still proceed.
    """
    import subprocess
    import platform

    env_name = project_name.lower().replace(" ", "_").replace("-", "_")

    # Check if the env exists via conda env list --json
    try:
        result = subprocess.run(
            ["conda", "env", "list", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            import json as _json
            data = _json.loads(result.stdout)
            env_exists = any(
                Path(p).name == env_name for p in data.get("envs", [])
            )
            if not env_exists:
                return f"Conda environment '{env_name}' not found — nothing to remove."
    except Exception:
        pass  # If we can't check, try removal anyway

    try:
        result = subprocess.run(
            ["conda", "env", "remove", "-n", env_name, "--yes"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return f"Conda environment '{env_name}' removed."
        else:
            return f"Conda environment '{env_name}' removal failed: {result.stderr.strip()}"
    except Exception as e:
        return f"Conda environment '{env_name}' removal failed: {e}"


def run_clean(project_root: Path, mode: str) -> Tuple[bool, str]:
    """Clean the workspace after successful Stage 5 delivery.

    Only functional when pipeline state shows Stage 5 is complete.
    Refuses to operate otherwise.

    Args:
        project_root: Path to the SVP project root directory.
        mode: One of "archive", "delete", or "keep".
            - "archive": compress workspace to {project_name}_workspace.tar.gz
              alongside the repo directory, then delete the workspace.
            - "delete": remove the workspace directory entirely.
            - "keep": do nothing; leave everything as-is.

    Returns:
        A tuple of (success: bool, message: str).

    Raises:
        FileNotFoundError: If pipeline_state.json is not found.
        RuntimeError: "Archive creation failed: {error}" if archiving fails.
    """
    assert project_root.is_dir(), "Project root must exist"
    assert mode in ("archive", "delete", "keep"), \
        "Clean mode must be one of archive, delete, keep"

    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError(
            "State file not found — is this an SVP project?"
        )

    # Import Unit 2 contract interfaces
    from svp.scripts.pipeline_state import load_state

    state = load_state(project_root)

    # Stage 5 completion check: stage must be "5" and we consider it complete
    # when there are no remaining sub-stages (delivery is done).
    # The definitive check is that stage == "5" and the delivery has been
    # finalized (indicated by stage being "5" with no pending sub_stage work).
    if state.stage != "5":
        return (False, "Clean is only available after successful delivery")

    # Determine project name for archive naming
    project_name = state.project_name or "project"

    if mode == "keep":
        return (True, "Workspace kept as-is. No files were modified.")

    if mode == "archive":
        # Create archive alongside the project root (in the parent directory)
        archive_name = f"{project_name}_workspace.tar.gz"
        archive_path = project_root.parent / archive_name

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(project_root, arcname=project_root.name)
        except Exception as e:
            raise RuntimeError(f"Archive creation failed: {e}")

        # Remove conda environment, then delete the workspace
        env_msg = _remove_conda_env(project_name)

        # Move cwd out of the workspace before deleting it — if the shell's
        # working directory IS the workspace, rmtree succeeds but the shell
        # can't resolve pwd afterward, causing a spurious exit code 1.
        import os
        os.chdir(project_root.parent)

        try:
            shutil.rmtree(project_root, onerror=_force_remove)
        except Exception as e:
            return (False, f"Archive created at {archive_path}, but workspace deletion failed: {e}")

        return (True, f"Workspace archived to {archive_path} and deleted. {env_msg}")

    if mode == "delete":
        # Remove conda environment first
        env_msg = _remove_conda_env(project_name)

        # Move cwd out of the workspace before deleting it (same reason as archive mode)
        import os
        os.chdir(project_root.parent)

        try:
            shutil.rmtree(project_root, onerror=_force_remove)
        except Exception as e:
            return (False, f"Workspace deletion failed: {e}")

        return (True, f"Workspace deleted. {env_msg}")

    # Should never reach here due to assertion, but for safety
    return (False, f"Unknown mode: {mode}")


if __name__ == "__main__":
    import argparse
    import sys

    # Ensure scripts/ is on path for pipeline_state import
    _scripts_dir = str(Path(__file__).parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    parser = argparse.ArgumentParser(description="SVP workspace cleanup")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=["archive", "delete", "keep"])
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    try:
        success, message = run_clean(project_root, args.mode)
        print(message)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
