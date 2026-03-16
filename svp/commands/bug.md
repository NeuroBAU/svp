# /svp:bug

Post-delivery bug report or abandon an active debug session.

## Availability

Available after Stage 5 completion, at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the bug triage agent:
   ```bash
   python scripts/prepare_task.py --agent bug_triage --project-root .
   ```
2. Spawn the bug triage agent subagent with the assembled task prompt.
3. The bug triage agent classifies the bug and guides the debug loop.
4. Use `/svp:bug --abandon` to clean up and return to Stage 5 complete.

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `TRIAGE_COMPLETE: build_env`
- `TRIAGE_COMPLETE: single_unit`
- `TRIAGE_COMPLETE: cross_unit`
- `TRIAGE_NEEDS_REFINEMENT`
- `TRIAGE_NON_REPRODUCIBLE`
