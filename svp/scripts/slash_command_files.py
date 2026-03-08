from typing import Dict, List

# Command file paths (relative to plugin commands/ directory)
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

# --- Group classification (SVP 1.1 hardening invariant) ---

GROUP_A_COMMANDS: List[str] = ["save", "quit", "status", "clean"]
# Group A: invoke dedicated cmd_*.py scripts directly. No subagent.

GROUP_B_COMMANDS: List[str] = ["help", "hint", "ref", "redo", "bug"]
# Group B: invoke prepare_task.py then spawn subagent. No cmd_*.py scripts.

# --- Prohibited scripts (SVP 1.1 hardening invariant) ---
PROHIBITED_SCRIPTS: List[str] = [
    "cmd_help.py",
    "cmd_hint.py",
    "cmd_ref.py",
    "cmd_redo.py",
    "cmd_bug.py",
]

# ---------------------------------------------------------------------------
# Group A command file contents
# ---------------------------------------------------------------------------

SAVE_MD_CONTENT: str = """\
# /svp:save

## When to use
Use `/svp:save` to persist the current pipeline state and any in-progress work \
to disk. This is a checkpoint command that ensures no progress is lost if the \
session ends unexpectedly.

## What it does
Runs the deterministic `cmd_save.py` script, which serializes the current \
`pipeline_state.json` and any associated session artifacts to disk.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_save.py --project-root .
   ```
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
"""

QUIT_MD_CONTENT: str = """\
# /svp:quit

## When to use
Use `/svp:quit` to gracefully end the current SVP session. This saves state \
and terminates the pipeline interaction.

## What it does
Runs the deterministic `cmd_quit.py` script, which persists final state and \
signals session termination.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_quit.py --project-root .
   ```
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
"""

STATUS_MD_CONTENT: str = """\
# /svp:status

## When to use
Use `/svp:status` to display the current pipeline stage, progress, and any \
pending actions. Available at any time during the session.

## What it does
Runs the deterministic `cmd_status.py` script, which reads `pipeline_state.json` \
and produces a human-readable status summary.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_status.py --project-root .
   ```
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
"""

CLEAN_MD_CONTENT: str = """\
# /svp:clean

## When to use
Use `/svp:clean` to remove temporary artifacts, caches, and intermediate files \
generated during the pipeline run (spec Section 12.5).

## What it does
Runs the deterministic `cmd_clean.py` script with `PYTHONPATH=scripts` so that \
library imports resolve correctly. Cleans up generated artifacts while preserving \
essential pipeline state.

## Execution steps

1. Run the following command exactly:
   ```
   PYTHONPATH=scripts python scripts/cmd_clean.py --project-root .
   ```
   NOTE: The `PYTHONPATH=scripts` prefix is required so that library imports \
resolve correctly (spec Section 12.5).
2. Present the script's stdout output to the human verbatim.
3. Do NOT spawn a subagent. This is a Group A command -- direct script execution only.
"""

# ---------------------------------------------------------------------------
# Group B command file contents
# ---------------------------------------------------------------------------

HELP_MD_CONTENT: str = """\
# /svp:help

## When to use
Use `/svp:help` to get assistance with SVP commands, pipeline concepts, or \
troubleshooting. Available at any time during the session.

## What it does
Invokes the help agent to provide contextual guidance. This is a Group B command \
-- it uses `prepare_task.py` to produce a task prompt and then spawns the help \
subagent. No dedicated command script exists for this command.

## Execution steps

1. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent help_agent --project-root . --output .svp/task_prompt.md
   ```
2. Read the task prompt file produced by the prepare command.
3. Spawn the help subagent, passing the task prompt content verbatim.
4. Present the subagent's response to the human.
5. Do NOT run any dedicated command script. This is a Group B command -- agent only.
"""

HINT_MD_CONTENT: str = """\
# /svp:hint

## When to use
Use `/svp:hint` to provide a domain-specific hint to the implementation agent. \
The hint is relayed through the help agent to inform the next implementation \
attempt.

## What it does
Invokes the hint agent to capture and relay the human's domain knowledge. This \
is a Group B command -- it uses `prepare_task.py` to produce a task prompt and \
then spawns the hint subagent. No dedicated command script exists for this command.

## Execution steps

1. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent hint_agent --project-root . --output .svp/task_prompt.md
   ```
2. Read the task prompt file produced by the prepare command.
3. Spawn the hint subagent, passing the task prompt content verbatim.
4. Present the subagent's response to the human.
5. Do NOT run any dedicated command script. This is a Group B command -- agent only.
"""

REF_MD_CONTENT: str = """\
# /svp:ref

## When to use
Use `/svp:ref` to consult or update reference materials during blueprint \
development. Available during Stages 0, 1, and 2 only. Locked from Stage 3 \
onward.

## What it does
Invokes the ref agent to manage reference material. This is a Group B command \
-- it uses `prepare_task.py` to produce a task prompt and then spawns the ref \
subagent. No dedicated command script exists for this command.

## Execution steps

1. Verify the pipeline is in Stage 0, 1, or 2. If Stage 3 or later, inform \
the human that `/svp:ref` is locked and do not proceed.
2. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent reference_indexing --project-root . --output .svp/task_prompt.md
   ```
3. Read the task prompt file produced by the prepare command.
4. Spawn the ref subagent, passing the task prompt content verbatim.
5. Present the subagent's response to the human.
6. Do NOT run any dedicated command script. This is a Group B command -- agent only.
"""

REDO_MD_CONTENT: str = """\
# /svp:redo

## When to use
Use `/svp:redo` to request a redo of a previous pipeline step. Available during \
Stages 2, 3, and 4.

## What it does
Invokes the redo agent to roll back and re-execute a prior step. This is a \
Group B command -- it uses `prepare_task.py` to produce a task prompt and then \
spawns the redo subagent. No dedicated command script exists for this command.

## Execution steps

1. Verify the pipeline is in Stage 2, 3, or 4. If outside this range, inform \
the human that `/svp:redo` is not available and do not proceed.
2. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent redo_agent --project-root . --output .svp/task_prompt.md
   ```
3. Read the task prompt file produced by the prepare command.
4. Spawn the redo subagent, passing the task prompt content verbatim.
5. Present the subagent's response to the human.
6. Do NOT run any dedicated command script. This is a Group B command -- agent only.
"""

BUG_MD_CONTENT: str = """\
# /svp:bug

## When to use
Use `/svp:bug` to report a bug discovered after Stage 5 completion. Supports \
the `--abandon` flag to abandon the current bug fix attempt.

## What it does
Invokes the bug triage agent to classify and route the bug report. This is a \
Group B command -- it uses `prepare_task.py` to produce a task prompt and then \
spawns the bug subagent. No dedicated command script exists for this command.

## Execution steps

1. Verify the pipeline has completed Stage 5. If Stage 5 is not complete, \
inform the human that `/svp:bug` is not available and do not proceed.
2. Run the following command to produce the task prompt:
   ```
   python scripts/prepare_task.py --agent bug_triage --project-root . --output .svp/task_prompt.md
   ```
   If the human specified `--abandon`, append the flag:
   ```
   python scripts/prepare_task.py --agent bug_triage --abandon --project-root . --output .svp/task_prompt.md
   ```
3. Read the task prompt file produced by the prepare command.
4. Spawn the bug subagent, passing the task prompt content verbatim.
5. Present the subagent's response to the human.
6. Do NOT run any dedicated command script. This is a Group B command -- agent only.
"""
