# /svp:redo

Roll back to redo a previously completed step.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the redo agent:
   ```bash
   python scripts/prepare_task.py --agent redo_agent --project-root .
   ```
2. Spawn the redo agent subagent with the assembled task prompt.
3. The redo agent traces the relevant term through the document hierarchy and classifies:
   - `REDO_CLASSIFIED: spec` -- spec says the wrong thing
   - `REDO_CLASSIFIED: blueprint` -- blueprint translated incorrectly
   - `REDO_CLASSIFIED: gate` -- documents correct, human approved wrong thing
   - `REDO_CLASSIFIED: profile_delivery` -- delivery-only profile change
   - `REDO_CLASSIFIED: profile_blueprint` -- blueprint-influencing profile change

## Status

Write the agent's terminal status line to `.svp/last_status.txt`.
