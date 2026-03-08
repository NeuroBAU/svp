# /svp:help

## When to use
Use `/svp:help` to get assistance with SVP commands, pipeline concepts, or troubleshooting. Available at any time during the session.

## What it does
Invokes the help agent to provide contextual guidance. This is a Group B command -- it uses `prepare_task.py` to produce a task prompt and then spawns the help subagent. No dedicated command script exists for this command.

## Execution steps

1. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent help_agent --project-root . --output .svp/task_prompt.md
   ```
2. Read the task prompt file produced by the prepare command.
3. Spawn the help subagent, passing the task prompt content verbatim.
4. Present the subagent's response to the human.
5. Do NOT run any dedicated command script. This is a Group B command -- agent only.
