"""Regression tests for Bug S3-124: prepare_task.py phase/agent_type dispatch mismatch.

Slash command bodies in src/unit_25/stub.py pass the phase-name form to
prepare_task.py (e.g., `prepare_task.py --agent help`). prepare_task.py's
dispatch historically matched only the agent_type-name form (`help_agent`),
so phase-form invocations fell through to the fallback:
    "# Task Prompt for help\n\nNo specific dispatch for agent type: help"

This was a pre-existing bug since the initial Pass 2 delivery commit
c75748d (2026-03-30). It was masked because the LLM orchestrator
compensated for the broken producer by recognizing the role from context
and answering anyway. Only manual empirical verification (typing
`/svp:help` in a Claude Code session and reading raw Bash output) surfaced
it on 2026-04-14.

The fix adds dual-form dispatch for the four affected Group B agents
(help, hint, redo, oracle) in src/unit_13/stub.py, following the existing
`bug_triage`/`bug_triage_agent` and `coverage_review`/`coverage_review_agent`
precedent that was already in the same function.

These tests lock the dispatch behavior by parameterizing over every
Group B phase name and asserting the returned content is NOT the fallback.
They import from the derived prepare_task module per the S3-103
stub-import discipline.
"""

from __future__ import annotations

import pytest

from prepare_task import prepare_task_prompt


FALLBACK_MARKER = "No specific dispatch for agent type"


# Group B phases that should dispatch to a real agent prompt.
# Each tuple is (phase_name, agent_type_name). Both forms must work.
GROUP_B_DISPATCH_PAIRS = [
    ("help", "help_agent"),
    ("hint", "hint_agent"),
    ("redo", "redo_agent"),
    ("oracle", "oracle_agent"),
    # bug_triage/bug_triage_agent: already dual-form pre-S3-124, lock it here
    # so a future refactor can't regress.
    ("bug_triage", "bug_triage_agent"),
]


# reference_indexing is single-form (phase == agent_type). Only one name to test.
SINGLE_FORM_DISPATCHES = ["reference_indexing"]


@pytest.fixture
def svp_project_root(tmp_path):
    """A minimally-valid SVP project directory for prepare_task invocation.

    prepare_task reads blueprint, profile, state, etc., from the project
    root. We create a sparse scaffold that is just complete enough for the
    dispatch to not error out before reaching the agent-specific handler.
    """
    (tmp_path / ".svp").mkdir()
    (tmp_path / ".svp" / "pipeline_state.json").write_text(
        '{"stage": "0", "sub_stage": "hook_activation", "primary_language": "python"}'
    )
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "stakeholder_spec.md").write_text("# Test Spec\n")
    (tmp_path / "blueprint").mkdir()
    (tmp_path / "blueprint" / "blueprint_prose.md").write_text("# Blueprint Prose\n")
    (tmp_path / "blueprint" / "blueprint_contracts.md").write_text(
        "# Blueprint Contracts\n"
    )
    (tmp_path / "project_context.md").write_text("# Context\n")
    (tmp_path / "project_profile.json").write_text(
        '{"project_name": "test", "primary_language": "python"}'
    )
    return tmp_path


class TestGroupBDispatchDualForm:
    """Group B agents must dispatch with either phase or agent_type form (Bug S3-124)."""

    @pytest.mark.parametrize("phase,agent_type", GROUP_B_DISPATCH_PAIRS)
    def test_phase_form_dispatches_correctly(self, phase, agent_type, svp_project_root):
        """Passing the phase-name form (e.g., 'help') must not hit the fallback."""
        try:
            content = prepare_task_prompt(
                project_root=svp_project_root,
                agent_type=phase,
            )
        except Exception as e:
            pytest.fail(
                f"prepare_task_prompt(agent_type={phase!r}) raised {type(e).__name__}: {e}. "
                f"Bug S3-124: phase-form dispatch must work without raising."
            )

        assert FALLBACK_MARKER not in content, (
            f"Bug S3-124: prepare_task_prompt dispatched {phase!r} to the "
            f"fallback handler. Expected a structured task prompt, got: "
            f"{content[:200]!r}"
        )

    @pytest.mark.parametrize("phase,agent_type", GROUP_B_DISPATCH_PAIRS)
    def test_agent_type_form_still_dispatches(self, phase, agent_type, svp_project_root):
        """Passing the agent_type form (e.g., 'help_agent') must remain backward-compatible."""
        try:
            content = prepare_task_prompt(
                project_root=svp_project_root,
                agent_type=agent_type,
            )
        except Exception as e:
            pytest.fail(
                f"prepare_task_prompt(agent_type={agent_type!r}) raised "
                f"{type(e).__name__}: {e}. Bug S3-124 fix must preserve "
                f"backward compatibility with the agent_type form."
            )

        assert FALLBACK_MARKER not in content, (
            f"Bug S3-124 regression: prepare_task_prompt dispatched {agent_type!r} "
            f"to the fallback handler. The agent_type form must remain working "
            f"after the dual-form fix. Got: {content[:200]!r}"
        )


class TestSingleFormDispatchStillWorks:
    """Single-form dispatches (phase == agent_type) must not regress (Bug S3-124)."""

    @pytest.mark.parametrize("name", SINGLE_FORM_DISPATCHES)
    def test_single_form_dispatches_correctly(self, name, svp_project_root):
        """reference_indexing (phase == agent_type) must dispatch without falling through."""
        try:
            content = prepare_task_prompt(
                project_root=svp_project_root,
                agent_type=name,
            )
        except Exception as e:
            pytest.fail(
                f"prepare_task_prompt(agent_type={name!r}) raised "
                f"{type(e).__name__}: {e}. Single-form dispatches must "
                f"continue to work after the S3-124 dual-form fix."
            )

        assert FALLBACK_MARKER not in content, (
            f"Bug S3-124: single-form dispatch for {name!r} fell through to "
            f"the fallback handler. Got: {content[:200]!r}"
        )


class TestUnknownAgentStillFallsThrough:
    """Unknown agent types must still hit the fallback — negative control (Bug S3-124)."""

    def test_unknown_agent_type_hits_fallback(self, svp_project_root):
        """Passing a genuinely unknown agent_type should still hit the fallback handler.

        This is a negative control: the S3-124 fix widens dispatch to accept
        both phase and agent_type forms for known agents, but it must not
        silently accept arbitrary strings. Unknown names should still fall
        through to the 'No specific dispatch' fallback so future typos or
        refactors are loud, not silent.
        """
        content = prepare_task_prompt(
            project_root=svp_project_root,
            agent_type="nonexistent_agent_xyz",
        )
        assert FALLBACK_MARKER in content, (
            "Unknown agent types must still hit the fallback. If this assertion "
            "fires, the S3-124 fix accidentally made the dispatch permissive."
        )
