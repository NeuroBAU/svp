# /svp:ref

## When to use
Use `/svp:ref` to consult or update reference materials during blueprint development. Available during Stages 0, 1, and 2 only. Locked from Stage 3 onward.

## What it does
Invokes the ref agent to manage reference material. This is a Group B command -- it uses `prepare_task.py` to produce a task prompt and then spawns the ref subagent. No dedicated command script exists for this command.

## Execution steps

1. Verify the pipeline is in Stage 0, 1, or 2. If Stage 3 or later, inform the human that `/svp:ref` is locked and do not proceed.
2. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent ref --project-root . --output .svp/task_prompt.md
   ```
3. Read the task prompt file produced by the prepare command.
4. Spawn the ref subagent, passing the task prompt content verbatim.
5. Present the subagent's response to the human.
6. Do NOT run any dedicated command script. This is a Group B command -- agent only.
