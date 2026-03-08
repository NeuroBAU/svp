# /svp:hint

## When to use
Use `/svp:hint` to provide a domain-specific hint to the implementation agent. The hint is relayed through the help agent to inform the next implementation attempt.

## What it does
Invokes the hint agent to capture and relay the human's domain knowledge. This is a Group B command -- it uses `prepare_task.py` to produce a task prompt and then spawns the hint subagent. No dedicated command script exists for this command.

## Execution steps

1. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent hint_agent --project-root . --output .svp/task_prompt.md
   ```
2. Read the task prompt file produced by the prepare command.
3. Spawn the hint subagent, passing the task prompt content verbatim.
4. Present the subagent's response to the human.
5. Do NOT run any dedicated command script. This is a Group B command -- agent only.
