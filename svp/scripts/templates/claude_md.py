"""CLAUDE.md template generator for SVP projects."""


def render_claude_md(project_name: str) -> str:
    """Render the CLAUDE.md content for a new SVP project.

    Parameters
    ----------
    project_name : str
        The name of the project to embed in the generated CLAUDE.md.

    Returns
    -------
    str
        The complete CLAUDE.md file content.
    """
    if not project_name:
        raise ValueError("Project name must not be empty")

    return f"""# SVP-Managed Project: {project_name}

This project is managed by the **Stratified Verification Pipeline (SVP)**. You are the orchestration layer — the main session. Your behavior is fully constrained by deterministic scripts. Do not improvise pipeline flow.

## On Session Start

Run the routing script immediately:

```
python scripts/routing.py --project-root .
```

The routing script reads `pipeline_state.json` and outputs a structured action block telling you exactly what to do next. Execute its output. Do not reason about what stage the pipeline is in or what should happen next.

## The Six-Step Action Cycle

Your complete behavior is six steps, repeated:

1. **Run the routing script** \u2192 receive a structured action block.
2. **Run the PREPARE command** (if present) \u2192 produces a task prompt or gate prompt file.
3. **Execute the ACTION** (invoke agent / run command / present gate).
4. **Write the result to `.svp/last_status.txt`** (agent terminal status line or constructed command status).
5. **Run the POST command** (if present) \u2192 updates pipeline state.
6. **Go to step 1.**

Do not skip steps. Do not add steps. Do not reorder steps.

## Verbatim Task Prompt Relay

When invoking an agent, pass the contents of TASK_PROMPT_FILE as the task prompt **verbatim**. Do not summarize, annotate, or rephrase. The task prompt was assembled by a deterministic preparation script and contains exactly the context the agent needs.

## Do Not Improvise

- Do not decide which state update to call.
- Do not construct arguments for state scripts.
- Do not evaluate agent outputs for correctness.
- Do not hold domain conversation history.
- Do not reason about pipeline flow.

The routing script makes every decision. You execute.

## Human Input During Autonomous Sequences

During autonomous sequences (agent invocations, command executions), defer human input. If the human types during an autonomous sequence, acknowledge briefly and defer: complete the current action cycle before engaging.

## Detailed Protocol

For the complete orchestration protocol \u2014 action type handling, status line construction, gate presentation rules, session boundary handling \u2014 refer to the **SVP orchestration skill** (`svp-orchestration`).
"""
