# /svp:ref

Add a reference document or repository.

## Availability

Available during Stages 0-2 only, at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the reference indexing agent:
   ```bash
   python scripts/prepare_task.py --agent reference_indexing --project-root .
   ```
2. Spawn the reference indexing agent subagent with the assembled task prompt.
3. Handles document references (file copy + indexing) and repository references (GitHub MCP exploration + summary).

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `INDEXING_COMPLETE`
