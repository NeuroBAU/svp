"""Action builders and formatting for SVP routing."""

from typing import Optional, Dict, List, Any, Callable


ACTION_TYPES: tuple = (
    "invoke_agent",
    "run_command",
    "human_gate",
    "session_boundary",
    "pipeline_complete",
)


REMINDER_TEXT: str = (
    "REMINDER:\n"
    "- Execute the ACTION above exactly as specified.\n"
    "- When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt verbatim. "
    "Do not summarize, annotate, or rephrase.\n"
    "- Wait for the agent to produce its terminal status line before proceeding.\n"
    "- Write the agent's terminal status line to .svp/last_status.txt.\n"
    "- Run the POST command if one was specified.\n"
    "- Then re-run the routing script for the next action.\n"
    "- Do not improvise pipeline flow. Do not skip steps. Do not add steps.\n"
    "- If the human types during an autonomous sequence, acknowledge and defer: "
    "complete the current action first."
)


def _invoke_agent_action(
    agent: str,
    message: str,
    unit: Optional[int] = None,
    prepare: Optional[str] = None,
    post: Optional[str] = None,
    task_prompt_file: str = ".svp/task_prompt.md",
    prepare_cmd_builder: Optional[Callable[..., str]] = None,
) -> Dict[str, Any]:
    """Build an invoke_agent action dict."""
    if prepare is None and prepare_cmd_builder is not None:
        prepare = prepare_cmd_builder(agent, unit=unit)
    return {
        "ACTION": "invoke_agent",
        "AGENT": agent,
        "PREPARE": prepare,
        "TASK_PROMPT_FILE": task_prompt_file,
        "POST": post,
        "COMMAND": None,
        "GATE": None,
        "UNIT": unit,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def _run_command_action(
    command: str,
    message: str,
    post: Optional[str] = None,
    unit: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a run_command action dict."""
    return {
        "ACTION": "run_command",
        "AGENT": None,
        "PREPARE": None,
        "TASK_PROMPT_FILE": None,
        "POST": post,
        "COMMAND": command,
        "GATE": None,
        "UNIT": unit,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def _human_gate_action(
    gate_id: str,
    message: str,
    unit: Optional[int] = None,
    prepare: Optional[str] = None,
    post: Optional[str] = None,
    prompt_file: str = ".svp/gate_prompt.md",
    gate_vocabulary: Optional[Dict[str, List[str]]] = None,
    gate_prepare_cmd_builder: Optional[Callable[..., str]] = None,
) -> Dict[str, Any]:
    """Build a human_gate action dict.

    The OPTIONS field is populated from GATE_VOCABULARY using the gate_id.
    This is the Bug 1 invariant: OPTIONS lists exactly the valid status strings.
    """
    if gate_vocabulary is None:
        gate_vocabulary = {}
    options_list = list(gate_vocabulary.get(gate_id, []))
    if post is not None:
        post = f"{post} --gate {gate_id}"
    if prepare is None and gate_prepare_cmd_builder is not None:
        prepare = gate_prepare_cmd_builder(gate_id, unit=unit)
    return {
        "ACTION": "human_gate",
        "AGENT": None,
        "PREPARE": prepare,
        "TASK_PROMPT_FILE": None,
        "POST": post,
        "COMMAND": None,
        "GATE": gate_id,
        "UNIT": unit,
        "OPTIONS": options_list,
        "PROMPT_FILE": prompt_file,
        "MESSAGE": message,
    }


def _session_boundary_action(message: str) -> Dict[str, Any]:
    """Build a session_boundary action dict."""
    return {
        "ACTION": "session_boundary",
        "AGENT": None,
        "PREPARE": None,
        "TASK_PROMPT_FILE": None,
        "POST": None,
        "COMMAND": None,
        "GATE": None,
        "UNIT": None,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def _pipeline_complete_action(message: str) -> Dict[str, Any]:
    """Build a pipeline_complete action dict."""
    return {
        "ACTION": "pipeline_complete",
        "AGENT": None,
        "PREPARE": None,
        "TASK_PROMPT_FILE": None,
        "POST": None,
        "COMMAND": None,
        "GATE": None,
        "UNIT": None,
        "OPTIONS": None,
        "PROMPT_FILE": None,
        "MESSAGE": message,
    }


def format_action_block(
    action: Dict[str, Any],
    reminder_text: Optional[str] = None,
) -> str:
    """Convert the action dict to the structured text format (spec Section 17).

    Includes the REMINDER block for invoke_agent, run_command, and human_gate.
    Omits REMINDER for session_boundary and pipeline_complete.
    """
    if reminder_text is None:
        reminder_text = REMINDER_TEXT

    lines: List[str] = []
    action_type = action.get("ACTION", "")

    lines.append(f"ACTION: {action_type}")

    if action.get("AGENT") is not None:
        lines.append(f"AGENT: {action['AGENT']}")
    if action.get("PREPARE") is not None:
        lines.append(f"PREPARE: {action['PREPARE']}")
    if action.get("TASK_PROMPT_FILE") is not None:
        lines.append(f"TASK_PROMPT_FILE: {action['TASK_PROMPT_FILE']}")
    if action.get("COMMAND") is not None:
        lines.append(f"COMMAND: {action['COMMAND']}")
    if action.get("POST") is not None:
        lines.append(f"POST: {action['POST']}")
    if action.get("GATE") is not None:
        lines.append(f"GATE: {action['GATE']}")
    if action.get("UNIT") is not None:
        lines.append(f"UNIT: {action['UNIT']}")
    if action.get("PROMPT_FILE") is not None:
        lines.append(f"PROMPT_FILE: {action['PROMPT_FILE']}")
    if action.get("OPTIONS") is not None:
        opts = action["OPTIONS"]
        if isinstance(opts, list):
            lines.append(f"OPTIONS: {', '.join(opts)}")
        else:
            lines.append(f"OPTIONS: {opts}")

    lines.append(f"MESSAGE: {action.get('MESSAGE', '')}")

    if action_type in ("invoke_agent", "run_command", "human_gate"):
        lines.append(reminder_text)

    result = "\n".join(lines)

    assert (
        "REMINDER:" in result
        or "session_boundary" in action_type
        or "pipeline_complete" in action_type
    ), "Non-terminal actions must include REMINDER block"

    return result
