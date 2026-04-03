# /svp:save

Flush pending pipeline state and verify file integrity.

## Action

Run the save script directly:

```
PYTHONPATH=scripts python scripts/cmd_save.py
```

This flushes all pending state to disk, verifies file integrity of pipeline artifacts, and confirms to the human that the save completed successfully.

## Notes

- Auto-save runs after every significant pipeline transition; this command is primarily a manual confirmation mechanism.
- No agent is spawned. No routing cycle is triggered.
