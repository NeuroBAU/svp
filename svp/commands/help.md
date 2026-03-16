# /svp:help

Pause the pipeline and launch the help agent.

## Availability

Available at any point during any stage, at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the help agent:
   ```bash
   python scripts/prepare_task.py --agent help_agent --project-root .
   ```
2. Spawn the help agent subagent with the assembled task prompt.
3. The help agent answers questions about code, error messages, technical concepts, SVP behavior, external libraries, Python syntax, and domain-adjacent topics.
4. The help agent is read-only: it never modifies documents, code, tests, or pipeline state.
5. Pipeline pauses while active. Resumes with no state change on dismissal.

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `HELP_SESSION_COMPLETE: no hint`
- `HELP_SESSION_COMPLETE: hint forwarded`
