# /svp:quit

Save and exit the SVP session.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_quit.py` to save the current state and exit cleanly.

```bash
python scripts/cmd_quit.py --project-root .
```

The quit command runs save first, then exits. Save confirmation before exit.

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
