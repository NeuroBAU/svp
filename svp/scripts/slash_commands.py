# Unit 20: Slash Command Files
"""Command .md content for all nine slash commands."""

from typing import Dict, List

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

GROUP_A_COMMANDS: List[str] = [
    "save",
    "quit",
    "status",
    "clean",
]
GROUP_B_COMMANDS: List[str] = [
    "help",
    "hint",
    "ref",
    "redo",
    "bug",
]

PROHIBITED_SCRIPTS: List[str] = [
    "cmd_help.py",
    "cmd_hint.py",
    "cmd_ref.py",
    "cmd_redo.py",
    "cmd_bug.py",
]

# -------------------------------------------------------
# Group A: Direct script invocations
# -------------------------------------------------------

SAVE_MD_CONTENT: str = """\
# /save

Run the save command to flush pipeline state.

```
python scripts/cmd_save.py --project-root .
```

Print confirmation when complete.
"""

QUIT_MD_CONTENT: str = """\
# /quit

Run the quit command to save and exit.

```
python scripts/cmd_quit.py --project-root .
```

This will save state and terminate the session.
"""

STATUS_MD_CONTENT: str = """\
# /status

Run the status command to display pipeline status.

```
python scripts/cmd_status.py --project-root .
```

Display the output to the user.
"""

CLEAN_MD_CONTENT: str = """\
# /clean

Run the clean command to clean up the workspace.

```
python scripts/cmd_clean.py --project-root .
```

Follow the prompts for archive/delete/keep options.
"""

# -------------------------------------------------------
# Group B: Agent-mediated with action cycle
# -------------------------------------------------------

HELP_MD_CONTENT: str = """\
# /help

## Action Cycle

1. Run prepare_task.py:
   ```
   python scripts/prepare_task.py \\
     --agent help_agent --project-root . \\
     --output .svp/task_prompt.md
   ```
2. Read `.svp/task_prompt.md` and spawn help_agent
   with the task prompt verbatim.
3. Write the agent's terminal status line to
   `.svp/last_status.txt`.
4. Run update_state.py:
   ```
   python scripts/update_state.py \\
     --project-root . --phase help
   ```
5. Re-run the routing script:
   ```
   python scripts/routing.py --project-root .
   ```
"""

HINT_MD_CONTENT: str = """\
# /hint

## Action Cycle

1. Run prepare_task.py:
   ```
   python scripts/prepare_task.py \\
     --agent hint_agent --project-root . \\
     --output .svp/task_prompt.md
   ```
2. Read `.svp/task_prompt.md` and spawn hint_agent
   with the task prompt verbatim.
3. Write the agent's terminal status line to
   `.svp/last_status.txt`.
4. Run update_state.py:
   ```
   python scripts/update_state.py \\
     --project-root . --phase hint
   ```
5. Re-run the routing script:
   ```
   python scripts/routing.py --project-root .
   ```
"""

REF_MD_CONTENT: str = """\
# /ref

## Action Cycle

1. Run prepare_task.py:
   ```
   python scripts/prepare_task.py \\
     --agent reference_indexing_agent \\
     --project-root . \\
     --output .svp/task_prompt.md
   ```
2. Read `.svp/task_prompt.md` and spawn
   reference_indexing_agent with the task prompt
   verbatim.
3. Write the agent's terminal status line to
   `.svp/last_status.txt`.
4. Run update_state.py:
   ```
   python scripts/update_state.py \\
     --project-root . --phase reference_indexing
   ```
5. Re-run the routing script:
   ```
   python scripts/routing.py --project-root .
   ```
"""

REDO_MD_CONTENT: str = """\
# /redo

## Action Cycle

1. Run prepare_task.py:
   ```
   python scripts/prepare_task.py \\
     --agent redo_agent --project-root . \\
     --output .svp/task_prompt.md
   ```
2. Read `.svp/task_prompt.md` and spawn redo_agent
   with the task prompt verbatim.
3. Write the agent's terminal status line to
   `.svp/last_status.txt`.
4. Run update_state.py:
   ```
   python scripts/update_state.py \\
     --project-root . --phase redo
   ```
5. Re-run the routing script:
   ```
   python scripts/routing.py --project-root .
   ```
"""

BUG_MD_CONTENT: str = """\
# /bug

## Action Cycle

1. Run prepare_task.py:
   ```
   python scripts/prepare_task.py \\
     --agent bug_triage_agent --project-root . \\
     --output .svp/task_prompt.md
   ```
2. Read `.svp/task_prompt.md` and spawn
   bug_triage_agent with the task prompt verbatim.
3. Write the agent's terminal status line to
   `.svp/last_status.txt`.
4. Run update_state.py:
   ```
   python scripts/update_state.py \\
     --project-root . --phase bug_triage
   ```
5. Re-run the routing script:
   ```
   python scripts/routing.py --project-root .
   ```
"""
