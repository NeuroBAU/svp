# SVP-G: Stratified Verification Protocol

## The Invariants
1. **Separation of Concerns:** Never write implementation and tests in the same turn.
2. **Red/Green Requirement:** A test MUST fail (Red) before implementation begins.
3. **Ledger Integrity:** Every transition must be logged in `ledgers/pipeline_state.json`.

## The Pipeline Stages
- **Stage 1 (Spec):** Use Socratic dialog to fill `docs/spec/stakeholder.md`.
- **Stage 2 (Blueprint):** Decompose spec into `docs/blueprint/units.md`.
- **Stage 3 (Unit Loop):**
    a. **Test Generation:**
        - Load `docs/blueprint/units.md`.
        - Switch to **Test Agent** role.
        - Generate `tests/test_<unit_name>.py`.
        - Sub-tasks MUST NOT involve files in `src/`.
        - Run `scripts/verify_cycle.py <unit_name> red`.
    b. **Implementation Generation:**
        - Load failing test results from step (a).
        - Switch to **Implementation Agent** role.
        - Do NOT read `tests/test_<unit_name>.py`. Only read the logs.
        - Write code in `src/<unit_name>.py`.
        - Run `scripts/verify_cycle.py <unit_name> green`.
    c. **Human Gate:**
        - Ask for approval before moving to the next unit.
- **Stage 4 (Ledger Update):** Log the transition in `ledgers/pipeline_state.json`.
