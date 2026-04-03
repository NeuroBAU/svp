# /svp:hint

Request diagnostic analysis from the hint agent.

## Action Cycle

1. Run `prepare_task.py --agent hint --project-root .` to assemble the task prompt.
2. Spawn the hint agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase hint` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase hint`

## Modes

- **Reactive mode:** Invoked during failure conditions. The routing script detects the failure context and assembles the task prompt with accumulated failure logs. Single-shot interaction.
- **Proactive mode:** Invoked during normal flow when the human acts on intuition. Ledger-based multi-turn interaction.

## Notes

- This is a Group B command: it follows the complete action cycle above.
- Gate options after hint analysis: CONTINUE or RESTART.
