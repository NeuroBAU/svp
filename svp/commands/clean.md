# /svp:clean

Clean up the SVP workspace after delivery.

## Availability

Available after Stage 5 completion, at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_clean.py` to archive, delete, or keep the workspace. The delivered repository is never touched.

```bash
python scripts/cmd_clean.py --project-root . --mode [archive|delete|keep]
```

Three modes:
- **archive**: Create a compressed archive of the workspace
- **delete**: Remove the workspace entirely
- **keep**: Leave the workspace as-is

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
