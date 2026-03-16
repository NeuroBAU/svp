# /svp:hint

Request diagnostic analysis from the hint agent.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the hint agent:
   ```bash
   python scripts/prepare_task.py --agent hint_agent --project-root .
   ```
2. Spawn the hint agent subagent with the assembled task prompt.
3. Two modes:
   - **Reactive**: During failure conditions -- reads accumulated failures, identifies patterns.
   - **Proactive**: During normal flow -- human acts on intuition.

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `HINT_ANALYSIS_COMPLETE`
