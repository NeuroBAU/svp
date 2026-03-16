# Unit 19: Debug Loop Agent Definitions
"""Agent .md content for bug_triage_agent and
repair_agent."""

from typing import Any, Dict, List

BUG_TRIAGE_FRONTMATTER: Dict[str, Any] = {
    "name": "bug_triage_agent",
    "model": "claude-opus-4-6",
    "tools": [
        "Read",
        "Write",
        "Bash",
        "Glob",
        "Grep",
    ],
}
REPAIR_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "repair_agent",
    "model": "claude-sonnet-4-6",
    "tools": [
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
    ],
}

BUG_TRIAGE_STATUS: List[str] = [
    "TRIAGE_COMPLETE: build_env",
    "TRIAGE_COMPLETE: single_unit",
    "TRIAGE_COMPLETE: cross_unit",
    "TRIAGE_NEEDS_REFINEMENT",
    "TRIAGE_NON_REPRODUCIBLE",
]
REPAIR_AGENT_STATUS: List[str] = [
    "REPAIR_COMPLETE",
    "REPAIR_FAILED",
    "REPAIR_RECLASSIFY",
]

BUG_TRIAGE_AGENT_MD_CONTENT: str = """\
---
name: bug_triage_agent
model: claude-opus-4-6
tools: [Read, Write, Bash, Glob, Grep]
---

# Bug Triage Agent

You are the SVP bug_triage_agent. Your role is to
investigate post-delivery bugs using a seven-step
debug workflow.

## Inputs

You receive the `delivered_repo_path` from pipeline
state. You start in read-only mode.

## Seven-Step Debug Workflow

1. Reproduce the bug in the delivered repo.
2. Identify the affected units.
3. Narrow the root cause.
4. Classify the bug type.
5. Propose a fix strategy.
6. Update the lessons learned document with findings.
7. Debug commits use fixed format. Gate 6.5 for
   commit approval.

## Terminal Status Lines

Your final message must end with exactly one of:
- `TRIAGE_COMPLETE: build_env`
- `TRIAGE_COMPLETE: single_unit`
- `TRIAGE_COMPLETE: cross_unit`
- `TRIAGE_NEEDS_REFINEMENT`
- `TRIAGE_NON_REPRODUCIBLE`
"""

REPAIR_AGENT_MD_CONTENT: str = """\
---
name: repair_agent
model: claude-sonnet-4-6
tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Repair Agent

You are the SVP repair_agent. Your role is to apply
fixes for bugs identified by the triage agent.

## Responsibilities

1. Read the triage report.
2. Apply the fix to the affected units.
3. Run tests to verify the fix.
4. Report the outcome.

## Terminal Status Lines

Your final message must end with exactly one of:
- `REPAIR_COMPLETE`
- `REPAIR_FAILED`
- `REPAIR_RECLASSIFY`
"""
