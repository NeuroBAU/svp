# /svp:status

Report current pipeline state.

## Action

Run the status script directly:

```
PYTHONPATH=scripts python scripts/cmd_status.py
```

This displays:
- Project name
- Pipeline toolchain (e.g., python_conda_pytest)
- Quality configuration (pipeline and delivery)
- Delivery preferences summary
- Current stage, sub-stage, and unit progress
- Pass history (if multi-pass)
- Active quality gate status

## Notes

- No agent is spawned. No routing cycle is triggered.
