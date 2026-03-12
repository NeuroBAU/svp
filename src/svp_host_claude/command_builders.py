"""Claude-host command builders for SVP routing."""

from typing import Optional


def post_cmd(
    phase: str, unit: Optional[int] = None, gate_id: Optional[str] = None
) -> str:
    """Build the standard POST command string."""
    parts = ["python scripts/update_state.py"]
    if unit is not None:
        parts.append(f"--unit {unit}")
    if gate_id is not None:
        parts.append(f"--gate {gate_id}")
    parts.append(f"--phase {phase}")
    parts.append("--status-file .svp/last_status.txt")
    return " ".join(parts)


def prepare_cmd(
    agent_or_gate: str, unit: Optional[int] = None, extra: Optional[str] = None
) -> str:
    """Build a PREPARE command string."""
    parts = ["python scripts/prepare_task.py"]
    if unit is not None:
        parts.append(f"--unit {unit}")
    parts.append(f"--agent {agent_or_gate}")
    parts.append("--project-root .")
    parts.append("--output .svp/task_prompt.md")
    if extra:
        parts.append(extra)
    return " ".join(parts)


def gate_prepare_cmd(gate_id: str, unit: Optional[int] = None) -> str:
    """Build a PREPARE command for a gate prompt."""
    parts = ["python scripts/prepare_task.py"]
    if unit is not None:
        parts.append(f"--unit {unit}")
    parts.append(f"--gate {gate_id}")
    parts.append("--project-root .")
    parts.append("--output .svp/gate_prompt.md")
    return " ".join(parts)
