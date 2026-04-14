# /svp:redo

Roll back to redo a previously completed step.

## Action Cycle

1. Run `prepare_task.py --agent redo --project-root .` to assemble the task prompt.
2. Spawn the redo agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase redo` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase redo`

## Classification

The redo agent classifies the request into one of five categories:
- `REDO_CLASSIFIED: spec` -- spec says the wrong thing
- `REDO_CLASSIFIED: blueprint` -- blueprint translated incorrectly
- `REDO_CLASSIFIED: gate` -- human approved wrong thing
- `REDO_CLASSIFIED: profile_delivery` -- delivery-only profile change
- `REDO_CLASSIFIED: profile_blueprint` -- blueprint-influencing profile change

## Notes

- This is a Group B command: it follows the complete action cycle above.
- The redo agent is invoked exclusively through this slash command.
