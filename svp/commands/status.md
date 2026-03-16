# /svp:status

Report the current pipeline state.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_status.py` to display the current pipeline state including:
- Current stage and sub-stage
- Verified units
- Alignment iterations
- Next expected action
- Pass history and pipeline toolchain summary
- One-line profile summary
- Active quality gate status

```bash
python scripts/cmd_status.py --project-root .
```

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
