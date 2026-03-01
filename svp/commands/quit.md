# /svp:quit

## When to use
Use `/svp:quit` to gracefully end the current SVP session. This saves state and terminates the pipeline interaction.

## What it does
Runs the deterministic `cmd_quit.py` script, which persists final state and signals session termination.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_quit.py --project-root .
   ```
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
