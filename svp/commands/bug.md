# /svp:bug

## When to use
Use `/svp:bug` to report a bug discovered after Stage 5 completion. Supports the `--abandon` flag to abandon the current bug fix attempt.

## What it does
Invokes the bug triage agent to classify and route the bug report. This is a Group B command -- it uses `prepare_task.py` to produce a task prompt and then spawns the bug subagent. No dedicated command script exists for this command.

## Execution steps

1. Verify the pipeline has completed Stage 5. If Stage 5 is not complete, inform the human that `/svp:bug` is not available and do not proceed.
2. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent bug_triage --project-root . --output .svp/task_prompt.md
   ```
   If the human specified `--abandon`, append the flag:
   ```
   python scripts/prepare_task.py --agent bug_triage --abandon --project-root . --output .svp/task_prompt.md
   ```
3. Read the task prompt file produced by the prepare command.
4. Spawn the bug subagent, passing the task prompt content verbatim.
5. Present the subagent's response to the human.
6. Do NOT run any dedicated command script. This is a Group B command -- agent only.
