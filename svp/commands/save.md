# /svp:save

Save the current pipeline state.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_save.py` to flush pending state, verify file integrity, and confirm to the human.

```bash
python scripts/cmd_save.py --project-root .
```

Auto-save runs after every significant transition; this command is primarily a confirmation mechanism.

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
