# /svp:bug

Report a post-delivery bug or abandon a fix attempt.

## Action Cycle

1. Run `prepare_task.py --agent bug_triage --project-root .` to assemble the task prompt.
2. Spawn the bug triage agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase bug_triage` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase bug_triage`

## Notes

- This is a Group B command: it follows the complete action cycle above.
- Available after Stage 5 completion.
- During an active `/svp:oracle` session, this command is blocked for the human (the oracle agent can call it internally).
