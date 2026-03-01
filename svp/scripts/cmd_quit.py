"""
cmd_quit.py — Command logic for /svp:quit.

Runs save first, then returns a message for the main session to present
before exiting. Implements spec Section 13 (/svp:quit).

Dependencies (coded against contract interfaces):
  - Unit 11 (cmd_save): run_save
"""

from pathlib import Path

from cmd_save import run_save


def run_quit(project_root: Path) -> str:
    """Save the project and return an exit message.

    Calls run_save first to flush state and verify integrity, then returns
    a message confirming the save was successful and that the human can
    safely close the terminal.

    Args:
        project_root: Path to the SVP project root directory.

    Returns:
        A message string for the main session to present before exiting.
        Confirms the save was successful and the human can safely close
        the terminal.

    Raises:
        FileNotFoundError: If pipeline_state.json is not found.
    """
    assert project_root.is_dir(), "Project root must exist"

    state_path = project_root / "pipeline_state.json"
    if not state_path.exists():
        raise FileNotFoundError(
            "State file not found — is this an SVP project?"
        )

    success, save_message = run_save(project_root)

    if success:
        return (
            f"{save_message}\n\n"
            "Pipeline state saved. You can safely close the terminal.\n"
            "To resume, run `svp` from the project directory."
        )
    else:
        return (
            f"Warning: {save_message}\n\n"
            "The pipeline state may not be fully saved. "
            "You can try `/svp:save` again or close the terminal. "
            "On next launch, SVP will attempt state recovery from markers."
        )
