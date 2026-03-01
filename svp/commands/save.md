# /svp:save

## When to use
Use `/svp:save` to persist the current pipeline state and any in-progress work to disk. This is a checkpoint command that ensures no progress is lost if the session ends unexpectedly.

## What it does
Runs the deterministic `cmd_save.py` script, which serializes the current `pipeline_state.json` and any associated session artifacts to disk.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_save.py --project-root .
   ```
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
