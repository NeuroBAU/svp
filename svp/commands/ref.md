# /svp:ref

Add a reference document or repository to the project context.

## Action Cycle

1. Run `prepare_task.py --agent reference_indexing --project-root .` to assemble the task prompt.
2. Spawn the reference indexing agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase reference_indexing` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase reference_indexing`

## Notes

- This is a Group B command: it follows the complete action cycle above.
- Available during Stages 0-2 only.
- Handles document references (file copy + indexing) and repository references (GitHub MCP exploration + summary).
- If GitHub MCP is not configured, offers to configure it.
