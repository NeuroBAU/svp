# /svp:redo

## When to use
Use `/svp:redo` to request a redo of a previous pipeline step. Available during Stages 2, 3, and 4.

## What it does
Invokes the redo agent to roll back and re-execute a prior step. This is a Group B command -- it uses `prepare_task.py` to produce a task prompt and then spawns the redo subagent. No dedicated command script exists for this command.

## Execution steps

1. Verify the pipeline is in Stage 2, 3, or 4. If outside this range, inform the human that `/svp:redo` is not available and do not proceed.
2. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent redo --project-root . --output .svp/task_prompt.md
   ```
3. Read the task prompt file produced by the prepare command.
4. Spawn the redo subagent, passing the task prompt content verbatim.
5. Present the subagent's response to the human.
6. Do NOT run any dedicated command script. This is a Group B command -- agent only.
