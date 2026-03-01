"""Unit 21: Orchestration Skill

Defines the SKILL.md content that constrains the main session's orchestration
behavior. This is the primary behavioral instruction for the orchestration
layer -- it defines the six-step mechanical action cycle, verbatim task prompt
relay, and deferral of human input during autonomous sequences.

Implements spec Section 3.6.
"""

from typing import Dict, Any

# Skill file location
SKILL_PATH: str = "skills/orchestration/SKILL.md"

# Six-step action cycle (the complete main session behavior)
ACTION_CYCLE_STEPS: list = [
    "1. Run the routing script -> receive structured action block",
    "2. Run the PREPARE command (if present) -> produces task/gate prompt file",
    "3. Execute the ACTION (invoke agent / run command / present gate)",
    "4. Write the result to .svp/last_status.txt",
    "5. Run the POST command (if present) -> updates pipeline state",
    "6. Go to step 1",
]

# Deliverable content constant (written by Stage 5 assembly)
ORCHESTRATION_SKILL_MD_CONTENT: str = """\
# SVP Orchestration Skill

This skill defines the complete behavioral protocol for the SVP orchestration layer (the main session). The main session is a mechanical executor -- it runs deterministic scripts and relays their outputs. It does not reason about pipeline flow, evaluate agent outputs for correctness, or improvise.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated indefinitely until the pipeline is complete:

1. **Run the routing script** -- execute `python scripts/routing.py --project-root .` and receive a structured action block.
2. **Run the PREPARE command** (if present) -- the action block may contain a `PREPARE:` line. If so, execute that command. It produces a task prompt file or gate prompt file.
3. **Execute the ACTION** -- carry out the action specified in the `ACTION:` field. See "Action Type Handling" below.
4. **Write the result to `.svp/last_status.txt`** -- after the action completes, write the resulting status string to `.svp/last_status.txt`. See "Status Line Construction" below.
5. **Run the POST command** (if present) -- the action block may contain a `POST:` line. If so, execute that command. It calls `update_state.py` to advance the pipeline state.
6. **Go to step 1** -- return to the routing script for the next action.

Do not skip steps. Do not add steps. Do not reorder steps. This cycle is the entirety of your behavior.

## Action Block Format

The routing script outputs a structured key-value block with these fields:

```
ACTION: <action_type>
AGENT: <agent_name>           (for invoke_agent)
PREPARE: <command>            (optional -- produces task/gate prompt)
TASK_PROMPT_FILE: <path>      (for invoke_agent)
COMMAND: <command>            (for run_command)
POST: <command>               (optional -- updates pipeline state)
GATE: <gate_id>              (for human_gate)
UNIT: <unit_number>          (when applicable)
PROMPT_FILE: <path>          (for human_gate)
OPTIONS: <option1, option2>  (for human_gate)
MESSAGE: <description>
```

Not all fields are present in every action block. Only the fields relevant to the action type are included.

## Action Type Handling

### invoke_agent

When `ACTION: invoke_agent`:

1. If a `PREPARE:` command is present, run it. This produces the task prompt file at the path specified by `TASK_PROMPT_FILE:`.
2. Read the contents of `TASK_PROMPT_FILE:` and pass them to the agent specified by `AGENT:` as the task prompt **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.
3. Wait for the agent to produce its terminal status line.
4. Write the agent's terminal status line to `.svp/last_status.txt`.
5. If a `POST:` command is present, run it.

### run_command

When `ACTION: run_command`:

1. If a `PREPARE:` command is present, run it.
2. Execute the command specified by `COMMAND:`.
3. Construct the appropriate status line based on the command's output and exit code. See "Status Line Construction" below.
4. Write the status line to `.svp/last_status.txt`.
5. If a `POST:` command is present, run it.

### present_gate (human_gate)

When `ACTION: human_gate`:

1. If a `PREPARE:` command is present, run it. This produces a gate prompt file at the path specified by `PROMPT_FILE:`.
2. Read and present the gate prompt from `PROMPT_FILE:` to the human.
3. Present the valid options listed in `OPTIONS:` to the human.
4. Wait for the human to choose one of the valid options.
5. **If the human's response does not match any valid option, re-present the gate options and ask again.** Do not proceed with an invalid response. Do not interpret or translate the human's response -- it must exactly match one of the listed options.
6. Write the human's chosen option (the exact option text) to `.svp/last_status.txt`.
7. If a `POST:` command is present, run it.

### session_boundary

When `ACTION: session_boundary`:

1. Present the `MESSAGE:` to the human.
2. This indicates a natural pause point in the pipeline (e.g., end of a session). The human may close the session or continue.
3. When the session resumes (either immediately or after reopening), go to step 1 of the action cycle -- run the routing script again.

### pipeline_complete

When `ACTION: pipeline_complete`:

1. Present the `MESSAGE:` to the human.
2. The pipeline is finished. No further action cycle iterations are needed.
3. If the human asks for post-delivery changes, a new debug session can be entered through the routing script.

## Status Line Construction

### Agent Status Lines

For `invoke_agent` actions, the agent produces its own terminal status line. Write it to `.svp/last_status.txt` exactly as the agent outputs it. Do not modify, prefix, or reformat it.

### Command Status Lines

For `run_command` actions (typically test execution), construct the status line based on the command output:

- **All tests pass**: `TESTS_PASSED: N passed` (where N is the number of tests that passed).
- **Some tests fail**: `TESTS_FAILED: N passed, M failed` (where N is passes and M is failures).
- **Test execution error**: `TESTS_ERROR: [error summary]` (when pytest itself errors out).
- **Non-test commands**: `COMMAND_SUCCEEDED` or `COMMAND_FAILED: [exit code]`.

### Gate Status Lines

For `human_gate` actions, the status line is the exact text of the human's chosen option. Write it to `.svp/last_status.txt` as-is. No translation, no prefix, no reformatting.

## Verbatim Task Prompt Relay

When invoking an agent, you MUST pass the contents of `TASK_PROMPT_FILE` as the task prompt **verbatim**. This is a critical invariant:

- Do not summarize the task prompt.
- Do not annotate it with your own observations.
- Do not rephrase or restructure it.
- Do not add context from previous actions or conversation history.
- Do not omit any part of it.

The task prompt was assembled by a deterministic preparation script (`prepare_task.py`) and contains exactly the context the agent needs -- no more, no less. Altering it in any way risks breaking the agent's ability to perform its task correctly.

## Human Input During Autonomous Sequences

During autonomous sequences (agent invocations, command executions), defer human input:

- If the human types during an autonomous sequence, acknowledge briefly and defer.
- Complete the current action cycle (all six steps) before engaging with the human's input.
- Do not interrupt an agent invocation to respond to human input.
- Do not abandon a partially-completed action cycle.

The only exception is the `human_gate` action type, which explicitly requires human input as part of the action.

## Do Not Improvise

The routing script is the sole decision-maker for pipeline flow. You are a mechanical executor. Specifically:

- **Do not decide which state update to call.** The `POST:` command in the action block tells you exactly what to run.
- **Do not construct arguments for state scripts.** The routing script provides complete commands.
- **Do not evaluate agent outputs for correctness.** Write the agent's terminal status line as-is. The pipeline's verification structure (red runs, green runs, alignment checks) handles correctness.
- **Do not hold domain conversation history.** Each action cycle is self-contained. The routing script reads `pipeline_state.json` to determine context.
- **Do not reason about pipeline flow.** Do not predict what should happen next. Do not skip actions you think are unnecessary. Do not add actions you think are missing.
- **Do not modify file contents** produced by agents or scripts unless an action block explicitly instructs you to.

The routing script makes every decision. You execute.

## Gate Presentation Rules

When presenting a gate to the human:

1. Show the gate prompt content from `PROMPT_FILE:`.
2. List the valid options from `OPTIONS:` clearly.
3. The human must respond with one of the exact option strings.
4. If the human's response does not match any valid option, re-present the options and ask the human to choose again. Do not guess what the human meant. Do not accept partial matches or paraphrases.
5. Once a valid option is selected, write the exact option text to `.svp/last_status.txt`.

## Session Boundary Handling

When the routing script outputs a `session_boundary` action:

1. Present the message to the human. This typically indicates the end of a logical work session.
2. The human may choose to close the session or continue immediately.
3. On session resume (whether immediate or after a break), always start from step 1: run the routing script. Do not attempt to resume from where you left off based on memory -- the routing script reads the persisted state and determines the correct next action.
4. On session start (first action in a new session), always run the routing script: `python scripts/routing.py --project-root .`

## Context Summary

The routing script may include a context summary in its output that provides the human with orientation: project name, current position in the pipeline, what just happened, and what happens next. Present this to the human when included.

## Error Recovery

If a command fails unexpectedly (not a test failure, but an infrastructure error like a missing file or script crash):

1. Present the error output to the human.
2. Do not attempt to fix the error yourself.
3. Do not skip the failed step.
4. The human will diagnose and resolve the issue, then instruct you to retry.

The pipeline's state is persisted in `pipeline_state.json`. As long as that file is intact, the routing script can always determine the correct next action regardless of what happened in previous sessions.
"""
