# /svp:bug

Report a post-delivery bug and enter a Stage 6 debug session.

## Action Cycle

1. Run `python scripts/update_state.py --command svp_bug_entry --project-root .` to create the debug session (transitions `debug_session: null → {phase: "triage", authorized: false}`).
2. Run `python scripts/routing.py --project-root .` to receive the next action block (Gate 6.0 debug permission).
3. Follow the six-step action cycle from there (the routing script handles debug authorization, triage agent invocation, classification gates, and all subsequent Stage 6 phases).

## Notes

- Available after Stage 5 completion.
- During an active `/svp:oracle` session, this command is blocked for the human (the oracle agent enters debug sessions internally via Gate 7.B).
- Only one debug session may be active at a time. If a debug session is already active, `svp_bug_entry` fails with an explanatory error.
