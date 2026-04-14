# /svp:clean

Clean up the build workspace.

## Action

Run the clean script directly:

```
PYTHONPATH=scripts python scripts/cmd_clean.py
```

This removes:
- The build environment (via the language-specific cleanup command)
- Workspace directories (with permission-aware handler for read-only files like __pycache__)

The delivered repository is never touched by this command.

## Notes

- No agent is spawned. No routing cycle is triggered.
