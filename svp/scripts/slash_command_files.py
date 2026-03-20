# Unit 20: Slash Command Files
# Defines the slash command files for all SVP commands.
# Implements spec Section 13.

from typing import Dict, Any, List

COMMAND_FILES: Dict[str, str] = {
    "save": "save.md",
    "quit": "quit.md",
    "help": "help.md",
    "hint": "hint.md",
    "status": "status.md",
    "ref": "ref.md",
    "redo": "redo.md",
    "bug": "bug.md",
    "clean": "clean.md",
}

# ---------------------------------------------------------------------------
# Group A commands: invoke dedicated cmd_*.py scripts directly
# ---------------------------------------------------------------------------

SAVE_MD_CONTENT: str = """\
# /svp:save

Save the current pipeline state.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_save.py` to flush pending state, verify file integrity, and confirm to the human.

```bash
python scripts/cmd_save.py --project-root .
```

Auto-save runs after every significant transition; this command is primarily a confirmation mechanism.

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
"""

QUIT_MD_CONTENT: str = """\
# /svp:quit

Save and exit the SVP session.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_quit.py` to save the current state and exit cleanly.

```bash
python scripts/cmd_quit.py --project-root .
```

The quit command runs save first, then exits. Save confirmation before exit.

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
"""

STATUS_MD_CONTENT: str = """\
# /svp:status

Report the current pipeline state.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_status.py` to display the current pipeline state including:
- Current stage and sub-stage
- Verified units
- Alignment iterations
- Next expected action
- Pass history and pipeline toolchain summary
- One-line profile summary
- Active quality gate status

```bash
python scripts/cmd_status.py --project-root .
```

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
"""

CLEAN_MD_CONTENT: str = """\
# /svp:clean

Clean up the SVP workspace after delivery.

## Availability

Available after Stage 5 completion, at gates and between units, not during autonomous execution.

## Behavior

Run `cmd_clean.py` to archive, delete, or keep the workspace. The delivered repository is never touched.

```bash
python scripts/cmd_clean.py --project-root . --mode [archive|delete|keep]
```

Three modes:
- **archive**: Create a compressed archive of the workspace
- **delete**: Remove the workspace entirely
- **keep**: Leave the workspace as-is

## Status

Write the result to `.svp/last_status.txt`:
- `COMMAND_SUCCEEDED` on success
- `COMMAND_FAILED: [exit code]` on failure
"""

# ---------------------------------------------------------------------------
# Group B commands: invoke prepare_task.py then spawn the appropriate subagent
# ---------------------------------------------------------------------------

HELP_MD_CONTENT: str = """\
# /svp:help

Pause the pipeline and launch the help agent.

## Availability

Available at any point during any stage, at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the help agent:
   ```bash
   python scripts/prepare_task.py --agent help_agent --project-root .
   ```
2. Spawn the help agent subagent with the assembled task prompt.
3. The help agent answers questions about code, error messages, technical concepts, SVP behavior, external libraries, Python syntax, and domain-adjacent topics.
4. The help agent is read-only: it never modifies documents, code, tests, or pipeline state.
5. Pipeline pauses while active. Resumes with no state change on dismissal.

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `HELP_SESSION_COMPLETE: no hint`
- `HELP_SESSION_COMPLETE: hint forwarded`
"""

HINT_MD_CONTENT: str = """\
# /svp:hint

Request diagnostic analysis from the hint agent.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the hint agent:
   ```bash
   python scripts/prepare_task.py --agent hint_agent --project-root .
   ```
2. Spawn the hint agent subagent with the assembled task prompt.
3. Two modes:
   - **Reactive**: During failure conditions -- reads accumulated failures, identifies patterns.
   - **Proactive**: During normal flow -- human acts on intuition.

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `HINT_ANALYSIS_COMPLETE`
"""

REF_MD_CONTENT: str = """\
# /svp:ref

Add a reference document or repository.

## Availability

Available during Stages 0-2 only, at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the reference indexing agent:
   ```bash
   python scripts/prepare_task.py --agent reference_indexing --project-root .
   ```
2. Spawn the reference indexing agent subagent with the assembled task prompt.
3. Handles document references (file copy + indexing) and repository references (GitHub MCP exploration + summary).

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `INDEXING_COMPLETE`
"""

REDO_MD_CONTENT: str = """\
# /svp:redo

Roll back to redo a previously completed step.

## Availability

Available at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the redo agent:
   ```bash
   python scripts/prepare_task.py --agent redo_agent --project-root .
   ```
2. Spawn the redo agent subagent with the assembled task prompt.
3. The redo agent traces the relevant term through the document hierarchy and classifies:
   - `REDO_CLASSIFIED: spec` -- spec says the wrong thing
   - `REDO_CLASSIFIED: blueprint` -- blueprint translated incorrectly
   - `REDO_CLASSIFIED: gate` -- documents correct, human approved wrong thing
   - `REDO_CLASSIFIED: profile_delivery` -- delivery-only profile change
   - `REDO_CLASSIFIED: profile_blueprint` -- blueprint-influencing profile change

## Status

Write the agent's terminal status line to `.svp/last_status.txt`.
"""

BUG_MD_CONTENT: str = """\
# /svp:bug

Post-delivery bug report or abandon an active debug session.

## Availability

Available after Stage 5 completion, at gates and between units, not during autonomous execution.

## Behavior

1. Run `prepare_task.py` to assemble the task prompt for the bug triage agent:
   ```bash
   python scripts/prepare_task.py --agent bug_triage --project-root .
   ```
2. Spawn the bug triage agent subagent with the assembled task prompt.
3. The bug triage agent classifies the bug and guides the debug loop.
4. Use `/svp:bug --abandon` to clean up and return to Stage 5 complete.

## Status

Write the agent's terminal status line to `.svp/last_status.txt`:
- `TRIAGE_COMPLETE: build_env`
- `TRIAGE_COMPLETE: single_unit`
- `TRIAGE_COMPLETE: cross_unit`
- `TRIAGE_NEEDS_REFINEMENT`
- `TRIAGE_NON_REPRODUCIBLE`
"""
