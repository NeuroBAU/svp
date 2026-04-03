# /svp:oracle

Launch the oracle agent for pipeline acceptance testing.

## Action Cycle

1. Run `prepare_task.py --agent oracle --project-root .` to assemble the task prompt.
2. Spawn the oracle agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase oracle` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase oracle`

## Test Project Selection

Before launching the oracle, select a test project. The oracle presents a numbered list of available test projects from the `docs/` and `examples/` directories:

- **GoL test projects** (from `examples/`): E-mode (product testing). Verifies that the pipeline-built product works correctly.
- **SVP docs** (from `docs/`): F-mode (machinery testing). Verifies that the pipeline machinery itself functions correctly.

The human selects the test project by number to determine the oracle mode.

## Availability

- Available only when `is_svp_build` is true in the project profile.
- Available only after Stage 5 completion (Pass 2 for E/F self-builds).

## Notes

- This is a Group B command: it follows the complete action cycle above.
- The oracle creates a nested pipeline session for verification purposes only. No production deliverables are produced.
- The run ledger provides cross-invocation memory for trajectory prioritization.
