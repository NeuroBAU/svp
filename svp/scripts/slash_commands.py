"""Unit 25: Slash Command Files.

Defines markdown command definitions for all SVP slash commands.

Group A (utility): svp_save, svp_quit, svp_status, svp_clean
  - Invoke dedicated cmd_*.py scripts directly. No agent. No routing cycle.

Group B (agent-driven): svp_help, svp_hint, svp_ref, svp_redo, svp_bug, svp_oracle
  - Full action cycle: prepare_task.py -> spawn agent -> last_status.txt -> update_state.py -> routing.py

Standalone: svp_visual_verify
  - Visual verification utility. Not a routed command.
"""

from typing import List

# ---------------------------------------------------------------------------
# COMMAND_NAMES — exactly 11 commands
# ---------------------------------------------------------------------------

COMMAND_NAMES: List[str] = [
    "svp_help",
    "svp_hint",
    "svp_ref",
    "svp_redo",
    "svp_bug",
    "svp_oracle",
    "svp_save",
    "svp_quit",
    "svp_status",
    "svp_clean",
    "svp_visual_verify",
]

# ---------------------------------------------------------------------------
# Group A commands — direct action, no agent spawning
# ---------------------------------------------------------------------------

_SVP_SAVE_DEFINITION: str = """\
# /svp:save

Flush pending pipeline state and verify file integrity.

## Action

Run the save script directly:

```
PYTHONPATH=scripts python scripts/cmd_save.py
```

This flushes all pending state to disk, verifies file integrity of pipeline \
artifacts, and confirms to the human that the save completed successfully.

## Notes

- Auto-save runs after every significant pipeline transition; this command is \
primarily a manual confirmation mechanism.
- No agent is spawned. No routing cycle is triggered.
"""

_SVP_QUIT_DEFINITION: str = """\
# /svp:quit

Save pipeline state and exit the session.

## Action

Run the quit script directly:

```
PYTHONPATH=scripts python scripts/cmd_quit.py
```

This runs the save script first (flushing all pending state), then exits \
the session cleanly. Save confirmation is displayed before exit.

## Notes

- No agent is spawned. No routing cycle is triggered.
"""

_SVP_STATUS_DEFINITION: str = """\
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
"""

_SVP_CLEAN_DEFINITION: str = """\
# /svp:clean

Clean up the build workspace.

## Action

Run the clean script directly:

```
PYTHONPATH=scripts python scripts/cmd_clean.py
```

This removes:
- The build environment (via the language-specific cleanup command)
- Workspace directories (with permission-aware handler for read-only files \
like __pycache__)

The delivered repository is never touched by this command.

## Notes

- No agent is spawned. No routing cycle is triggered.
"""

# ---------------------------------------------------------------------------
# Group B commands — agent-driven workflow with full action cycle
# ---------------------------------------------------------------------------

_SVP_HELP_DEFINITION: str = """\
# /svp:help

Pause the pipeline and launch the help agent for interactive assistance.

## Action Cycle

1. Run `prepare_task.py --agent help --project-root .` to assemble the task prompt.
2. Spawn the help agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase help` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase help`

## Notes

- This is a Group B command: it follows the complete action cycle above.
- The help agent provides interactive assistance with pipeline usage, \
command explanations, and troubleshooting guidance.
"""

_SVP_HINT_DEFINITION: str = """\
# /svp:hint

Request diagnostic analysis from the hint agent.

## Action Cycle

1. Run `prepare_task.py --agent hint --project-root .` to assemble the task prompt.
2. Spawn the hint agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase hint` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase hint`

## Modes

- **Reactive mode:** Invoked during failure conditions. The routing script \
detects the failure context and assembles the task prompt with accumulated \
failure logs. Single-shot interaction.
- **Proactive mode:** Invoked during normal flow when the human acts on \
intuition. Ledger-based multi-turn interaction.

## Notes

- This is a Group B command: it follows the complete action cycle above.
- Gate options after hint analysis: CONTINUE or RESTART.
"""

_SVP_REF_DEFINITION: str = """\
# /svp:ref

Add a reference document or repository to the project context.

## Action Cycle

1. Run `prepare_task.py --agent reference_indexing --project-root .` to assemble \
the task prompt.
2. Spawn the reference indexing agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase reference_indexing` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase reference_indexing`

## Notes

- This is a Group B command: it follows the complete action cycle above.
- Available during Stages 0-2 only.
- Handles document references (file copy + indexing) and repository references \
(GitHub MCP exploration + summary).
- If GitHub MCP is not configured, offers to configure it.
"""

_SVP_REDO_DEFINITION: str = """\
# /svp:redo

Roll back to redo a previously completed step.

## Action Cycle

1. Run `prepare_task.py --agent redo --project-root .` to assemble the task prompt.
2. Spawn the redo agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase redo` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase redo`

## Classification

The redo agent classifies the request into one of five categories:
- `REDO_CLASSIFIED: spec` — spec says the wrong thing
- `REDO_CLASSIFIED: blueprint` — blueprint translated incorrectly
- `REDO_CLASSIFIED: gate` — human approved wrong thing
- `REDO_CLASSIFIED: profile_delivery` — delivery-only profile change
- `REDO_CLASSIFIED: profile_blueprint` — blueprint-influencing profile change

## Notes

- This is a Group B command: it follows the complete action cycle above.
- The redo agent is invoked exclusively through this slash command.
"""

_SVP_BUG_DEFINITION: str = """\
# /svp:bug

Report a post-delivery bug or abandon a fix attempt.

## Action Cycle

1. Run `prepare_task.py --agent bug_triage --project-root .` to assemble the task prompt.
2. Spawn the bug triage agent with the assembled task prompt.
3. Write the agent's terminal status line to `.svp/last_status.txt`.
4. Run `update_state.py --phase bug_triage` to update pipeline state.
5. Re-run the routing script (`python scripts/routing.py --project-root .`).

## Phase Value

`--phase bug_triage`

## Notes

- This is a Group B command: it follows the complete action cycle above.
- Available after Stage 5 completion.
- During an active `/svp:oracle` session, this command is blocked for the \
human (the oracle agent can call it internally).
"""

_SVP_ORACLE_DEFINITION: str = """\
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

Before launching the oracle, select a test project. The oracle presents a \
numbered list of available test projects from the `docs/` and `examples/` \
directories:

- **GoL test projects** (from `examples/`): E-mode (product testing). Verifies \
that the pipeline-built product works correctly.
- **SVP docs** (from `docs/`): F-mode (machinery testing). Verifies that the \
pipeline machinery itself functions correctly.

The human selects the test project by number to determine the oracle mode.

## Availability

- Available only when `is_svp_build` is true in the project profile.
- Available only after Stage 5 completion (Pass 2 for E/F self-builds).

## Notes

- This is a Group B command: it follows the complete action cycle above.
- The oracle creates a nested pipeline session for verification purposes only. \
No production deliverables are produced.
- The run ledger provides cross-invocation memory for trajectory prioritization.
"""

# ---------------------------------------------------------------------------
# Standalone command — not routed
# ---------------------------------------------------------------------------

_SVP_VISUAL_VERIFY_DEFINITION: str = """\
# /svp:visual-verify

Visual verification utility for GUI-based test projects.

## Purpose

Launches a target program, captures visual output (screenshots) at defined \
intervals or interaction points, and returns captured images for evaluation.

## Arguments

- `--target` — Path to the executable or project to launch.
- `--interval` — (Optional) Capture interval in seconds for periodic screenshots.
- `--interactions` — (Optional) List of interaction steps to execute before \
capturing screenshots.

## Usage

Invocable by:
- The oracle agent during E-mode green runs (after primary test suite verification).
- The human independently on persisted test projects.

## Visual Verification

This command captures screenshots of the running application for visual \
inspection. The oracle or human can examine the captured images to verify:
- GUI renders correctly
- Visual elements match spec requirements
- Interactive elements function as expected

## Screenshot Capture

Screenshots are captured either at regular intervals (via `--interval`) or \
after executing specified interaction steps (via `--interactions`). Captured \
images are returned for evaluation.

## Important

This is supplementary, not authoritative. The test suite is the authoritative \
verification mechanism. Visual verification provides an additional layer of \
confidence but does not replace deterministic test results.

## Notes

- This is a standalone utility command. It is not a routed command.
- No phase flag is used. No routing cycle is triggered.
"""

# ---------------------------------------------------------------------------
# COMMAND_DEFINITIONS — maps each command name to its markdown content
# ---------------------------------------------------------------------------

COMMAND_DEFINITIONS: dict = {
    "svp_save": _SVP_SAVE_DEFINITION,
    "svp_quit": _SVP_QUIT_DEFINITION,
    "svp_status": _SVP_STATUS_DEFINITION,
    "svp_clean": _SVP_CLEAN_DEFINITION,
    "svp_help": _SVP_HELP_DEFINITION,
    "svp_hint": _SVP_HINT_DEFINITION,
    "svp_ref": _SVP_REF_DEFINITION,
    "svp_redo": _SVP_REDO_DEFINITION,
    "svp_bug": _SVP_BUG_DEFINITION,
    "svp_oracle": _SVP_ORACLE_DEFINITION,
    "svp_visual_verify": _SVP_VISUAL_VERIFY_DEFINITION,
}
