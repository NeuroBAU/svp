# /svp:bug

Report a post-delivery bug and enter a Stage 6 debug session.

## Action Cycle

1. Run `python scripts/update_state.py --command bug_entry --project-root .` to create the debug session (transitions `debug_session: null → {phase: "triage", authorized: false}`).
2. Run `python scripts/routing.py --project-root .` to receive the next action block (Gate 6.0 debug permission).
3. Follow the six-step action cycle from there (the routing script handles debug authorization, triage agent invocation, classification gates, and all subsequent Stage 6 phases).

## Notes

- Available after Stage 5 completion.
- During an active `/svp:oracle` session, this command is blocked for the human (the oracle agent enters debug sessions internally via Gate 7.B).
- Only one debug session may be active at a time. If a debug session is already active, `bug_entry` fails with an explanatory error.

## Scope

Use /svp:bug ONLY for narrow contract-bounded fixes:

- The bug is genuinely localized to a single unit.
- The relevant blueprint contract is well-specified.
- The fix is mechanical alignment of code to contract.

If during /svp:bug investigation you discover any of:
- Multiple units affected
- Spec questions arising (the spec may itself be wrong / silent / contradictory)
- Cross-layer interactions (spec + blueprint + code or beyond)
- Behavior intent unclear (this may be an enhancement, not a bug)

ABORT the /svp:bug flow and escalate to break-glass. Per CLAUDE.md
"Choosing the entry-point" guidance, break-glass is the canonical default
for human-initiated debug; /svp:bug is a narrow sub-tool.

Auto-dispatched /svp:bug (routing-detected red runs) follows the same
narrowness; the orchestrator MAY abort and escalate at any time.
