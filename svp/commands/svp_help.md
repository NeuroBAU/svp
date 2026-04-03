# /svp:help

Pause the pipeline and launch the help agent for interactive assistance.

## Action Cycle

1. Run `prepare_task.py --agent help --project-root .` to assemble the task prompt.
2. Spawn the help agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase help` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase help`

## Notes

- This is a Group B command: it follows the complete action cycle above.
- The help agent provides interactive assistance with pipeline usage, command explanations, and troubleshooting guidance.
