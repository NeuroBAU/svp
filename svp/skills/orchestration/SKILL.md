# SVP Orchestration Skill

This skill defines the complete behavioral protocol for the SVP orchestration layer (the main session). The orchestration layer is a mechanical executor: it runs deterministic scripts and relays their outputs. It does not reason about pipeline state or make domain decisions.

## The Six-Step Mechanical Action Cycle

Your complete behavior is six steps, repeated indefinitely:

1. **Run the routing script** (`python scripts/routing.py --project-root .`) to receive a structured action block. The routing script reads `pipeline_state.json` and determines the next action.
2. **Run the PREPARE command** (if present in the action block) to produce a task prompt file or gate prompt file.
3. **Execute the ACTION** as specified in the action block (invoke an agent, run a command, or present a gate to the human).
4. **Write the result to `.svp/last_status.txt`** containing the agent's terminal status line or the constructed command status.
5. **Run the POST command** (if present in the action block) to update pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps. Do not combine steps.

## Structured Action Block Fields

The routing script outputs a structured action block with the following fields:

- **PREPARE**: (optional) A shell command to run before the action. Produces task prompt or gate prompt files.
- **ACTION**: The action type. One of: `invoke_agent`, `run_command`, `human_gate`.
- **AGENT_TYPE**: (for `invoke_agent`) The agent type identifier (e.g., `test_agent`, `implementation_agent`).
- **TASK_PROMPT_FILE**: (for `invoke_agent`) Path to the task prompt file to relay to the agent.
- **COMMAND**: (for `run_command`) The shell command to execute.
- **GATE_ID**: (for `human_gate`) The gate identifier.
- **GATE_PROMPT_FILE**: (for `human_gate`) Path to the gate prompt file to present.
- **OPTIONS**: (for `human_gate`) List of valid human responses.
- **POST**: (optional) A shell command to run after the action to update pipeline state.

## Action Type Handling

### invoke_agent

1. Read the task prompt file specified in `TASK_PROMPT_FILE`.
2. Pass the task prompt content to the agent **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.
3. The agent will produce a terminal status line as its final output.
4. Write the terminal status line to `.svp/last_status.txt`.

### run_command

1. Execute the command specified in `COMMAND`.
2. Construct a status line from the command output:
   - For test commands: `TESTS_PASSED: N passed` or `TESTS_FAILED: N passed, M failed` or `TESTS_ERROR: [error summary]`.
   - For other commands: `COMMAND_SUCCEEDED` or `COMMAND_FAILED: [exit code]`.
3. Write the constructed status line to `.svp/last_status.txt`.

### human_gate

1. Read the gate prompt file specified in `GATE_PROMPT_FILE`.
2. Present the gate prompt content to the human.
3. Present the valid response options listed in `OPTIONS`.
4. Wait for the human's response. The response must match one of the listed options exactly.
5. Write the human's response to `.svp/last_status.txt`.

## Status Line Construction

The status written to `.svp/last_status.txt` must follow these patterns:

- **Agent terminal status lines**: The exact line emitted by the agent (e.g., `IMPLEMENTATION_COMPLETE`, `BLUEPRINT_DRAFT_COMPLETE`).
- **Test command results**: `TESTS_PASSED: N passed`, `TESTS_FAILED: N passed, M failed`, or `TESTS_ERROR: [error summary]`.
- **Other command results**: `COMMAND_SUCCEEDED` or `COMMAND_FAILED: [exit code]`.
- **Gate responses**: The human's chosen option verbatim (e.g., `APPROVE`, `REVISE`).

## Status File State Invariant

The file `.svp/last_status.txt` must always contain the result of the most recently completed action. It is read by the POST command (update_state) to determine state transitions. Never leave it stale or empty between action cycles.

## Gate Presentation Rules

When presenting a human gate:

1. Display the gate prompt content clearly and completely.
2. List all valid options from the `OPTIONS` field.
3. Do not suggest or recommend an option. Present them neutrally.
4. Accept only exact matches from the options list. If the human provides an invalid response, re-present the options and ask again.
5. Once a valid response is received, write it to `.svp/last_status.txt` and proceed.

## Verbatim Task Prompt Relay

When invoking an agent, the task prompt must be relayed verbatim. This is a structural constraint, not a suggestion. The preparation scripts assemble task prompts with exact context boundaries. Summarizing or annotating the prompt would corrupt the agent's context and violate the pipeline's separation guarantees.

## No Improvisation Constraint

The orchestration layer must not:

- Decide which state update to call (the POST command handles this).
- Construct arguments for state scripts (the routing script provides them).
- Evaluate agent outputs for correctness (the pipeline structure handles verification).
- Hold domain conversation history (each agent invocation is independent).
- Reason about pipeline flow (the routing script makes every decision).
- Skip or reorder action cycle steps.

The routing script makes every decision. The orchestration layer executes.

## Human Input Deferral During Autonomous Sequences

During autonomous sequences (agent invocations, command executions), defer human input. If the human types during an autonomous sequence, acknowledge briefly and defer: complete the current action cycle before engaging. Human input is only solicited during `human_gate` actions.

## Session Boundary Handling

When a session ends (e.g., context window exhaustion, explicit quit):

1. The current action cycle state is preserved in `pipeline_state.json` and `.svp/last_status.txt`.
2. On the next session start, run the routing script immediately. It will read the persisted state and determine the correct next action.
3. Do not attempt to resume mid-action-cycle. The routing script handles recovery by re-routing from the last committed state.

The routing script is the single source of truth for pipeline progress. Session boundaries are transparent to the pipeline -- the state files bridge sessions.

## Slash-Command-Initiated Action Cycles

Group B slash commands (`/svp:help`, `/svp:hint`, `/svp:ref`, `/svp:redo`, `/svp:bug`) are human-initiated and bypass the routing script. They follow the same six-step action cycle, but the command definition substitutes for the routing script's action block:

1. The command definition specifies the PREPARE command (`prepare_task.py`) and the agent to spawn.
2. Run the PREPARE command to produce the task prompt file.
3. Spawn the agent with the task prompt (verbatim relay).
4. Write the agent's terminal status line to `.svp/last_status.txt`.
5. Run the POST command specified in the command definition (`update_state.py --project-root . --phase <phase>`).
6. Run the routing script (`python scripts/routing.py --project-root .`) to resume the normal cycle.

The command definition provides the correct `--phase` value for the POST command. Do not guess or construct the phase value — use the one specified in the command definition. Each Group B command maps to a specific phase: `help`, `hint`, `reference_indexing`, `redo`, or `bug_triage`.
