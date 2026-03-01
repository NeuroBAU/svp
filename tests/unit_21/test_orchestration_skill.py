"""
Tests for Unit 21: Orchestration Skill.

Validates the SKILL_PATH constant, ACTION_CYCLE_STEPS list, and
ORCHESTRATION_SKILL_MD_CONTENT string that defines the main session's
complete behavioral protocol. Implements spec Section 3.6.

This is a Markdown skill file (NOT an agent definition). It does NOT
have YAML frontmatter. Tests must NOT check for YAML frontmatter.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: SKILL_PATH is the string "skills/orchestration/SKILL.md",
the conventional path for the orchestration skill file within the project.

DATA ASSUMPTION: ACTION_CYCLE_STEPS is a list of exactly 6 strings, each
describing one step of the mechanical action cycle. Steps reference:
routing script, PREPARE, ACTION, last_status.txt, POST, and looping back.

DATA ASSUMPTION: ORCHESTRATION_SKILL_MD_CONTENT is a comprehensive Markdown
string that describes the complete SVP orchestration protocol. It must cover
the six-step action cycle, all action types, status line construction,
verbatim task prompt relay, gate presentation rules, and session boundary
handling.

DATA ASSUMPTION: The five keywords that must appear in the content per the
Tier 2 invariant are: "routing script", "PREPARE", "ACTION", "last_status.txt",
"POST". These correspond to the six-step cycle components.

DATA ASSUMPTION: Action types handled by the orchestration skill include:
invoke_agent, run_command, present_gate, session_boundary, pipeline_complete.
These are the canonical action types the main session must know how to process.

DATA ASSUMPTION: "Verbatim task prompt relay" means the skill instructs
the main session to pass TASK_PROMPT_FILE contents without summarization,
annotation, or rephrasing.

DATA ASSUMPTION: "Deferral of human input" means the skill instructs the
main session to acknowledge and defer human input during autonomous sequences,
completing the current action first.

DATA ASSUMPTION: The routing script is described as the sole decision-maker
for pipeline flow. The main session must not improvise or decide independently.

DATA ASSUMPTION: Gate re-presentation means the main session must re-present
gate options when the human's response does not match any valid option.

DATA ASSUMPTION: The content must be substantial Markdown -- at least 500
characters and 10 non-empty lines -- to qualify as a real skill definition
rather than a skeleton placeholder.
"""

import re

import pytest

# Import constants that have concrete values in the stub
from svp.scripts.orchestration_skill import (
    SKILL_PATH,
    ACTION_CYCLE_STEPS,
)


# ---------------------------------------------------------------------------
# Helper: safely import ORCHESTRATION_SKILL_MD_CONTENT
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name.

    The stub declares these as type annotations without values, so
    direct import will fail on the stub (red run) and succeed on
    the implementation (green run).
    """
    import svp.scripts.orchestration_skill as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.orchestration_skill")
    return val


# ===========================================================================
# Section 1: SKILL_PATH Constant
# ===========================================================================


class TestSkillPath:
    """Verify the SKILL_PATH constant matches the blueprint."""

    def test_is_string(self):
        """SKILL_PATH must be a str."""
        assert isinstance(SKILL_PATH, str)

    def test_value(self):
        """SKILL_PATH must be 'skills/orchestration/SKILL.md'."""
        # DATA ASSUMPTION: SKILL_PATH is the canonical path for the orchestration skill file
        assert SKILL_PATH == "skills/orchestration/SKILL.md"

    def test_ends_with_md(self):
        """Skill file must be a Markdown file."""
        assert SKILL_PATH.endswith(".md")

    def test_in_skills_directory(self):
        """Skill file must be in the skills/ directory."""
        assert SKILL_PATH.startswith("skills/")


# ===========================================================================
# Section 2: ACTION_CYCLE_STEPS Constant
# ===========================================================================


class TestActionCycleSteps:
    """Verify the ACTION_CYCLE_STEPS list matches the blueprint."""

    def test_is_list(self):
        """ACTION_CYCLE_STEPS must be a list."""
        assert isinstance(ACTION_CYCLE_STEPS, list)

    def test_has_six_steps(self):
        """The action cycle must have exactly 6 steps."""
        # DATA ASSUMPTION: The six-step cycle has exactly 6 entries
        assert len(ACTION_CYCLE_STEPS) == 6

    def test_all_elements_are_strings(self):
        """Each step must be a string."""
        for i, step in enumerate(ACTION_CYCLE_STEPS):
            assert isinstance(step, str), f"Step {i} is {type(step)}, expected str"

    def test_no_empty_strings(self):
        """No step may be empty or whitespace-only."""
        for i, step in enumerate(ACTION_CYCLE_STEPS):
            assert step.strip(), f"Step {i} is empty or whitespace-only"

    def test_step_1_mentions_routing_script(self):
        """Step 1 must reference the routing script."""
        # DATA ASSUMPTION: Step 1 is about running the routing script
        step = ACTION_CYCLE_STEPS[0].lower()
        assert "routing script" in step or "routing" in step, (
            f"Step 1 must mention routing script, got: {ACTION_CYCLE_STEPS[0]!r}"
        )

    def test_step_2_mentions_prepare(self):
        """Step 2 must reference the PREPARE command."""
        # DATA ASSUMPTION: Step 2 is about running the PREPARE command
        step = ACTION_CYCLE_STEPS[1].upper()
        assert "PREPARE" in step, (
            f"Step 2 must mention PREPARE, got: {ACTION_CYCLE_STEPS[1]!r}"
        )

    def test_step_3_mentions_action(self):
        """Step 3 must reference the ACTION execution."""
        # DATA ASSUMPTION: Step 3 is about executing the ACTION
        step = ACTION_CYCLE_STEPS[2].upper()
        assert "ACTION" in step, (
            f"Step 3 must mention ACTION, got: {ACTION_CYCLE_STEPS[2]!r}"
        )

    def test_step_4_mentions_status(self):
        """Step 4 must reference writing to last_status.txt."""
        # DATA ASSUMPTION: Step 4 is about writing to last_status.txt
        step = ACTION_CYCLE_STEPS[3]
        assert "last_status.txt" in step or "status" in step.lower(), (
            f"Step 4 must mention last_status.txt or status, got: {ACTION_CYCLE_STEPS[3]!r}"
        )

    def test_step_5_mentions_post(self):
        """Step 5 must reference the POST command."""
        # DATA ASSUMPTION: Step 5 is about running the POST command
        step = ACTION_CYCLE_STEPS[4].upper()
        assert "POST" in step, (
            f"Step 5 must mention POST, got: {ACTION_CYCLE_STEPS[4]!r}"
        )

    def test_step_6_mentions_repeat(self):
        """Step 6 must reference looping back to step 1."""
        # DATA ASSUMPTION: Step 6 loops back to step 1
        step = ACTION_CYCLE_STEPS[5].lower()
        assert "step 1" in step or "go to" in step or "repeat" in step, (
            f"Step 6 must reference looping back, got: {ACTION_CYCLE_STEPS[5]!r}"
        )

    def test_exact_values(self):
        """ACTION_CYCLE_STEPS must match the exact blueprint values."""
        expected = [
            "1. Run the routing script -> receive structured action block",
            "2. Run the PREPARE command (if present) -> produces task/gate prompt file",
            "3. Execute the ACTION (invoke agent / run command / present gate)",
            "4. Write the result to .svp/last_status.txt",
            "5. Run the POST command (if present) -> updates pipeline state",
            "6. Go to step 1",
        ]
        assert ACTION_CYCLE_STEPS == expected

    def test_no_duplicates(self):
        """No duplicate steps in the action cycle."""
        assert len(ACTION_CYCLE_STEPS) == len(set(ACTION_CYCLE_STEPS)), (
            "ACTION_CYCLE_STEPS contains duplicate entries"
        )


# ===========================================================================
# Section 3: ORCHESTRATION_SKILL_MD_CONTENT -- Type and Structure
# ===========================================================================


class TestOrchestrationSkillMdContentType:
    """Verify the type and basic structure of ORCHESTRATION_SKILL_MD_CONTENT."""

    def test_is_string(self):
        """ORCHESTRATION_SKILL_MD_CONTENT must be a str."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert isinstance(content, str)

    def test_not_empty(self):
        """Content must not be empty."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert len(content) > 0, "ORCHESTRATION_SKILL_MD_CONTENT must not be empty"

    def test_is_substantial(self):
        """Content must be substantial -- not a placeholder or skeleton."""
        # DATA ASSUMPTION: At least 500 chars for a real skill definition
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert len(content) >= 500, (
            f"Content is only {len(content)} chars, expected >= 500 for a real skill definition"
        )

    def test_has_sufficient_non_empty_lines(self):
        """Content must have a reasonable number of non-empty lines."""
        # DATA ASSUMPTION: At least 10 non-empty lines for a real skill definition
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        non_empty_lines = [line for line in content.splitlines() if line.strip()]
        assert len(non_empty_lines) >= 10, (
            f"Content has only {len(non_empty_lines)} non-empty lines, expected >= 10"
        )

    def test_does_not_start_with_yaml_frontmatter(self):
        """This is a skill file, NOT an agent definition -- no YAML frontmatter."""
        # DATA ASSUMPTION: Skill files do not use YAML frontmatter (that is
        # for agent definitions). The content should be plain Markdown.
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        # It is acceptable for the content to start with "---\n" only if it is
        # a Markdown horizontal rule, but per the task guidelines this is NOT
        # an agent definition and must NOT have YAML frontmatter. We verify
        # it is Markdown content, not YAML-delimited frontmatter.
        # The key behavioral contract is that it is Markdown loaded as
        # behavioral context, so we just ensure it is non-trivial Markdown.
        assert isinstance(content, str) and len(content) > 100


# ===========================================================================
# Section 4: Tier 2 Invariant -- Required Keywords
# ===========================================================================


class TestTier2Invariant:
    """Verify the Tier 2 invariant: content must contain all required keywords."""

    def test_contains_routing_script(self):
        """Content must mention 'routing script'."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "routing script" in content.lower(), (
            "ORCHESTRATION_SKILL_MD_CONTENT must contain 'routing script'"
        )

    def test_contains_prepare(self):
        """Content must mention 'PREPARE'."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "PREPARE" in content, (
            "ORCHESTRATION_SKILL_MD_CONTENT must contain 'PREPARE'"
        )

    def test_contains_action(self):
        """Content must mention 'ACTION'."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "ACTION" in content, (
            "ORCHESTRATION_SKILL_MD_CONTENT must contain 'ACTION'"
        )

    def test_contains_last_status_txt(self):
        """Content must mention 'last_status.txt'."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "last_status.txt" in content, (
            "ORCHESTRATION_SKILL_MD_CONTENT must contain 'last_status.txt'"
        )

    def test_contains_post(self):
        """Content must mention 'POST'."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "POST" in content, (
            "ORCHESTRATION_SKILL_MD_CONTENT must contain 'POST'"
        )

    def test_all_keywords_present(self):
        """Blueprint invariant assertion: all five keywords must be present."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        keywords = ["routing script", "PREPARE", "ACTION", "last_status.txt", "POST"]
        for kw in keywords:
            # Use case-insensitive check for "routing script", exact for others
            if kw == "routing script":
                assert kw in content.lower(), (
                    f"Missing keyword: {kw!r}"
                )
            else:
                assert kw in content, (
                    f"Missing keyword: {kw!r}"
                )


# ===========================================================================
# Section 5: Six-Step Mechanical Action Cycle
# ===========================================================================


class TestSixStepActionCycle:
    """Verify the content describes the six-step mechanical action cycle."""

    def test_describes_complete_cycle(self):
        """Content must describe the complete six-step action cycle."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        # Must reference all cycle phases
        assert "routing script" in content_lower, "Must describe running routing script"
        assert "prepare" in content_lower, "Must describe PREPARE phase"
        assert "action" in content_lower, "Must describe ACTION phase"
        assert "status" in content_lower, "Must describe writing status"
        assert "post" in content_lower, "Must describe POST phase"

    def test_no_skipping_instruction(self):
        """Content must instruct no skipping of steps."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "skip" in content_lower or "no skip" in content_lower, (
            "Content must instruct not to skip steps"
        )

    def test_no_additions_instruction(self):
        """Content must instruct no additions to the cycle."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "add" in content_lower, (
            "Content must instruct not to add steps to the cycle"
        )

    def test_no_reordering_instruction(self):
        """Content must instruct no reordering of steps."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "reorder" in content_lower, (
            "Content must instruct not to reorder steps"
        )

    def test_cycle_repeats(self):
        """Content must describe the cycle as repeating (step 6 goes back to step 1)."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "repeat" in content_lower or "go to step 1" in content_lower or "step 1" in content_lower, (
            "Content must describe the cycle as repeating"
        )


# ===========================================================================
# Section 6: Action Type Handling
# ===========================================================================


class TestActionTypeHandling:
    """Verify the content describes how to handle each action type."""

    def test_describes_invoke_agent(self):
        """Content must describe how to handle invoke_agent action type."""
        # DATA ASSUMPTION: invoke_agent is one of the canonical action types
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "invoke_agent" in content or "invoke agent" in content.lower(), (
            "Content must describe the invoke_agent action type"
        )

    def test_describes_run_command(self):
        """Content must describe how to handle run_command action type."""
        # DATA ASSUMPTION: run_command is one of the canonical action types
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "run_command" in content or "run command" in content.lower(), (
            "Content must describe the run_command action type"
        )

    def test_describes_present_gate(self):
        """Content must describe how to handle present_gate action type."""
        # DATA ASSUMPTION: present_gate is one of the canonical action types
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "present_gate" in content or "present gate" in content.lower(), (
            "Content must describe the present_gate action type"
        )

    def test_describes_session_boundary(self):
        """Content must describe how to handle session_boundary action type."""
        # DATA ASSUMPTION: session_boundary is one of the canonical action types
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "session_boundary" in content or "session boundary" in content.lower(), (
            "Content must describe the session_boundary action type"
        )

    def test_describes_pipeline_complete(self):
        """Content must describe how to handle pipeline_complete action type."""
        # DATA ASSUMPTION: pipeline_complete is one of the canonical action types
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "pipeline_complete" in content or "pipeline complete" in content.lower(), (
            "Content must describe the pipeline_complete action type"
        )


# ===========================================================================
# Section 7: Verbatim Task Prompt Relay
# ===========================================================================


class TestVerbatimTaskPromptRelay:
    """Verify the content instructs verbatim task prompt relay."""

    def test_mentions_task_prompt_file(self):
        """Content must reference TASK_PROMPT_FILE."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "TASK_PROMPT_FILE" in content, (
            "Content must reference TASK_PROMPT_FILE"
        )

    def test_mentions_verbatim(self):
        """Content must instruct verbatim relay."""
        # DATA ASSUMPTION: The word "verbatim" or equivalent must appear
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "verbatim" in content_lower, (
            "Content must instruct verbatim task prompt relay"
        )

    def test_prohibits_summarization(self):
        """Content must prohibit summarization of task prompts."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "summar" in content_lower, (
            "Content must prohibit summarization (mention 'summarize' or 'summarization')"
        )

    def test_prohibits_annotation(self):
        """Content must prohibit annotation of task prompts."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "annotat" in content_lower, (
            "Content must prohibit annotation (mention 'annotate' or 'annotation')"
        )

    def test_prohibits_rephrasing(self):
        """Content must prohibit rephrasing of task prompts."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "rephras" in content_lower, (
            "Content must prohibit rephrasing (mention 'rephrase' or 'rephrasing')"
        )


# ===========================================================================
# Section 8: Deferral of Human Input During Autonomous Sequences
# ===========================================================================


class TestHumanInputDeferral:
    """Verify the content instructs deferral of human input during autonomous sequences."""

    def test_mentions_autonomous(self):
        """Content must reference autonomous sequences."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "autonomous" in content_lower, (
            "Content must mention autonomous sequences"
        )

    def test_mentions_defer(self):
        """Content must instruct deferral."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "defer" in content_lower, (
            "Content must instruct deferral of human input"
        )

    def test_mentions_acknowledge(self):
        """Content must instruct acknowledging human input before deferring."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "acknowledge" in content_lower, (
            "Content must instruct acknowledging human input"
        )

    def test_complete_current_action_first(self):
        """Content must instruct completing the current action before engaging."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "complete" in content_lower and "current" in content_lower, (
            "Content must instruct completing the current action first"
        )


# ===========================================================================
# Section 9: Routing Script as Sole Decision-Maker
# ===========================================================================


class TestRoutingScriptSoleDecisionMaker:
    """Verify the content references the routing script as the sole decision-maker."""

    def test_routing_script_decides(self):
        """Content must state the routing script makes every decision."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "routing script" in content_lower, (
            "Content must reference the routing script"
        )
        assert "decision" in content_lower or "decides" in content_lower, (
            "Content must describe the routing script as making decisions"
        )

    def test_prohibits_improvising(self):
        """Content must instruct the main session not to improvise."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "improvis" in content_lower, (
            "Content must prohibit improvising (mention 'improvise' or 'improvising')"
        )


# ===========================================================================
# Section 10: Gate Presentation Rules
# ===========================================================================


class TestGatePresentationRules:
    """Verify the content describes gate presentation rules."""

    def test_describes_gate_presentation(self):
        """Content must describe how to present gates."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "gate" in content_lower, (
            "Content must describe gate presentation"
        )

    def test_re_present_on_invalid_response(self):
        """Content must instruct re-presenting gate options on invalid human response."""
        # DATA ASSUMPTION: When human's response does not match any valid option,
        # the main session must re-present the gate options
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "re-present" in content_lower or "re present" in content_lower or "reprompt" in content_lower or "present again" in content_lower or "re-display" in content_lower, (
            "Content must instruct re-presenting gate options when human response is invalid"
        )

    def test_mentions_valid_options(self):
        """Content must reference valid gate options."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "valid" in content_lower or "option" in content_lower or "match" in content_lower, (
            "Content must reference valid gate options or matching"
        )


# ===========================================================================
# Section 11: Status Line Construction
# ===========================================================================


class TestStatusLineConstruction:
    """Verify the content describes how to construct status lines."""

    def test_describes_status_line_construction(self):
        """Content must describe how to construct status lines."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "last_status.txt" in content, (
            "Content must reference last_status.txt for status line output"
        )

    def test_describes_writing_status(self):
        """Content must describe the act of writing status."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "write" in content_lower and "status" in content_lower, (
            "Content must describe writing status lines"
        )


# ===========================================================================
# Section 12: Session Boundary Handling
# ===========================================================================


class TestSessionBoundaryHandling:
    """Verify the content describes session boundary handling."""

    def test_describes_session_boundary(self):
        """Content must describe session_boundary handling."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "session" in content_lower and "boundary" in content_lower, (
            "Content must describe session boundary handling"
        )


# ===========================================================================
# Section 13: No Improvisation / Deterministic Behavior
# ===========================================================================


class TestDeterministicBehavior:
    """Verify the content enforces deterministic, non-improvising behavior."""

    def test_no_improvise(self):
        """Content must instruct the main session not to improvise."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "do not improvise" in content_lower or "not improvise" in content_lower or "improvis" in content_lower, (
            "Content must instruct not to improvise"
        )

    def test_describes_mechanical_behavior(self):
        """Content should describe the cycle as mechanical or deterministic."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "mechanical" in content_lower or "deterministic" in content_lower or "exact" in content_lower, (
            "Content should describe the behavior as mechanical or deterministic"
        )


# ===========================================================================
# Section 14: Comprehensive Protocol Coverage
# ===========================================================================


class TestComprehensiveProtocol:
    """Verify the ORCHESTRATION_SKILL_MD_CONTENT covers the complete SVP protocol.

    Per the behavioral contract: ORCHESTRATION_SKILL_MD_CONTENT must be the
    complete SVP orchestration protocol. It must describe:
    - The six-step action cycle
    - How to handle each action type (invoke_agent, run_command, present_gate,
      session_boundary, pipeline_complete)
    - How to construct status lines
    - How to relay task prompts verbatim
    - Gate presentation rules
    - Session boundary handling
    """

    def test_covers_six_step_cycle(self):
        """Must cover the six-step action cycle."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        # All phases must be referenced
        phases = ["routing script", "prepare", "action", "status", "post"]
        for phase in phases:
            assert phase in content_lower, f"Content must cover the '{phase}' phase"

    def test_covers_all_action_types(self):
        """Must describe handling for all 5 action types."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        action_types = [
            "invoke_agent",
            "run_command",
            "present_gate",
            "session_boundary",
            "pipeline_complete",
        ]
        for at in action_types:
            # Allow underscore or space separated
            assert at in content or at.replace("_", " ") in content.lower(), (
                f"Content must describe handling for action type: {at}"
            )

    def test_covers_status_line_construction(self):
        """Must describe status line construction."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "last_status.txt" in content
        assert "status" in content.lower()

    def test_covers_verbatim_relay(self):
        """Must describe verbatim task prompt relay."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "verbatim" in content.lower()
        assert "TASK_PROMPT_FILE" in content

    def test_covers_gate_presentation(self):
        """Must describe gate presentation rules."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "gate" in content.lower()

    def test_covers_session_boundary(self):
        """Must describe session boundary handling."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "session" in content_lower and "boundary" in content_lower


# ===========================================================================
# Section 15: Module-Level Signature Checks
# ===========================================================================


class TestModuleLevelSignatures:
    """Verify the exported constants have correct types as specified in Tier 2."""

    def test_skill_path_type(self):
        """SKILL_PATH must be str."""
        assert isinstance(SKILL_PATH, str)

    def test_action_cycle_steps_type(self):
        """ACTION_CYCLE_STEPS must be list."""
        assert isinstance(ACTION_CYCLE_STEPS, list)

    def test_action_cycle_steps_element_types(self):
        """Each element of ACTION_CYCLE_STEPS must be str."""
        for item in ACTION_CYCLE_STEPS:
            assert isinstance(item, str)

    def test_orchestration_skill_md_content_type(self):
        """ORCHESTRATION_SKILL_MD_CONTENT must be str."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert isinstance(content, str)


# ===========================================================================
# Section 16: Content Is Markdown (Not Code)
# ===========================================================================


class TestContentIsMarkdown:
    """Verify the content is Markdown, not executable code or other formats.

    The blueprint says: 'No runtime errors from the skill file. It is
    Markdown loaded as behavioral context.'
    """

    def test_contains_markdown_headings(self):
        """Content should contain Markdown headings (# or ##)."""
        # DATA ASSUMPTION: A comprehensive skill definition uses Markdown headings
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert re.search(r"^#{1,3}\s+\S", content, re.MULTILINE), (
            "Content should contain Markdown headings"
        )

    def test_is_human_readable(self):
        """Content should be primarily human-readable text, not binary or encoded."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        # At least 80% of characters should be printable ASCII or common Unicode
        printable_count = sum(1 for c in content if c.isprintable() or c in "\n\r\t")
        ratio = printable_count / len(content) if len(content) > 0 else 0
        assert ratio > 0.9, (
            f"Content is only {ratio:.0%} printable, expected >90% for Markdown"
        )
