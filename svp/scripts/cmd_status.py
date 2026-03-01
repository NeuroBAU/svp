"""
cmd_status.py — Command logic for /svp:status.

Produces a human-readable pipeline state report including project name,
current stage/sub-stage, verified units, alignment iterations, and pass
history. Implements spec Section 13 (/svp:status).

Dependencies (coded against contract interfaces):
  - Unit 2 (pipeline_state): load_state, PipelineState, get_stage_display
"""

from pathlib import Path


def run_status(project_root: Path) -> str:
    """Read pipeline state and format a human-readable status report.

    The report includes:
      - Project name
      - Current stage and sub-stage (via get_stage_display)
      - Which units are verified
      - How many alignment iterations have been used
      - Pass history (via format_pass_history)

    Args:
        project_root: Path to the SVP project root directory.

    Returns:
        A non-empty string containing the formatted status report.

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
    from svp.scripts.pipeline_state import load_state, get_stage_display

    state = load_state(project_root)

    lines: list[str] = []

    # Project name
    project_name = state.project_name or "Unnamed Project"
    lines.append(f"Project: {project_name}")

    # Current stage display (e.g., "Stage 3, Unit 4 of 11 (pass 2)")
    stage_display = get_stage_display(state)
    lines.append(f"Current: {stage_display}")

    # Verified units
    if state.verified_units:
        verified_nums = [str(vu["unit"]) for vu in state.verified_units]
        lines.append(f"Verified units: {', '.join(verified_nums)}")
    else:
        if state.stage == "3":
            lines.append("Verified units: none yet")

    # Alignment iterations (relevant in Stage 2)
    if state.alignment_iteration > 0 or state.stage == "2":
        lines.append(f"Alignment iterations: {state.alignment_iteration}")

    # Sub-stage if present and not already captured by get_stage_display
    if state.sub_stage and state.stage in ("0", "1", "2"):
        lines.append(f"Sub-stage: {state.sub_stage}")

    # Fix ladder position if active
    if state.fix_ladder_position:
        lines.append(f"Fix ladder: {state.fix_ladder_position}")

    # Last action
    if state.last_action:
        lines.append(f"Last action: {state.last_action}")

    # Pass history
    if state.pass_history:
        lines.append("")
        lines.append(format_pass_history(state.pass_history))

    result = "\n".join(lines)
    assert len(result) > 0, "Status output must not be empty"
    return result


def format_pass_history(pass_history: list) -> str:
    """Produce tabular pass history per spec Section 13.

    Each pass entry shows what unit it reached and why it ended.
    The format matches the spec example:
        Pass 1: Reached Unit 7, spec revision triggered
                (electrode boundary handling was underspecified)
        Pass 2: In progress, Unit 1 verified

    Args:
        pass_history: List of dicts, each with keys:
            - pass_number (int)
            - reached_unit (int)
            - ended_reason (str)
            - timestamp (str)

    Returns:
        A formatted multi-line string with the pass history table.
    """
    if not pass_history:
        return ""

    lines: list[str] = []
    for entry in pass_history:
        pass_num = entry.get("pass_number", "?")
        reached = entry.get("reached_unit", "?")
        reason = entry.get("ended_reason", "unknown")

        header = f"Pass {pass_num}: Reached Unit {reached}, {reason}"
        lines.append(header)

    return "\n".join(lines)
