# /svp:quit

Save pipeline state and exit the session.

## Action

Run the quit script directly:

```
PYTHONPATH=scripts python scripts/cmd_quit.py
```

This runs the save script first (flushing all pending state), then exits the session cleanly. Save confirmation is displayed before exit.

## Notes

- No agent is spawned. No routing cycle is triggered.
