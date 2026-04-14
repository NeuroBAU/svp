# /svp:oracle

Launch the oracle agent for pipeline acceptance testing.

## Action Cycle

1. Write `ORACLE_REQUESTED` to `.svp/last_status.txt`.
2. Run `python scripts/update_state.py --command oracle_start --project-root .` to enter the oracle session.
3. Run `python scripts/routing.py --project-root .` to receive the next action block.
4. Follow the six-step action cycle from there (the routing script handles test project selection, agent invocation, and all oracle phases).

## Availability

- Available only when `is_svp_build` is true in the project profile.
- Available only after Stage 5 completion (Pass 2 for E/F self-builds).

## Notes

- This is a Group B command: after the initial state transition, it follows the standard routing-driven action cycle.
- The routing script handles test project selection deterministically. Do NOT scan directories or build test project lists.
- The oracle creates a nested pipeline session for verification purposes only. No production deliverables are produced.
- The run ledger provides cross-invocation memory for trajectory prioritization.
