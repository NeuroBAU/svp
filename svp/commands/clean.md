# /svp:clean

## When to use
Use `/svp:clean` to remove temporary artifacts, caches, and intermediate files generated during the pipeline run (spec Section 12.5).

## What it does
Runs the deterministic `cmd_clean.py` script with `PYTHONPATH=scripts` so that library imports resolve correctly. Cleans up generated artifacts while preserving essential pipeline state.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_clean.py --project-root .
   ```
   NOTE: The `PYTHONPATH=scripts` prefix is required so that library imports resolve correctly (spec Section 12.5).
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
