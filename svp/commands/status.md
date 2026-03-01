# /svp:status

## When to use
Use `/svp:status` to display the current pipeline stage, progress, and any pending actions. Available at any time during the session.

## What it does
Runs the deterministic `cmd_status.py` script, which reads `pipeline_state.json` and produces a human-readable status summary.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_status.py --project-root .
   ```
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
