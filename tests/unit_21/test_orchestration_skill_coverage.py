"""
Additional coverage tests for Unit 21: Orchestration Skill.

These tests cover behavioral contracts and invariants from the blueprint
that are not fully exercised by the existing test suite.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: The full file path for status output is ".svp/last_status.txt",
matching the path used in ACTION_CYCLE_STEPS step 4.

DATA ASSUMPTION: Status line construction instructions include concrete format
patterns such as TESTS_PASSED, TESTS_FAILED, or similar structured status
indicators so the main session knows exactly how to construct them.

DATA ASSUMPTION: The content describes the routing script's output format
(structured action block) so the main session knows how to read it, as stated
in the behavioral contract "how to read routing script output."

DATA ASSUMPTION: The routing script is described as the "sole" decision-maker,
meaning the content must convey exclusivity (e.g., "sole", "every", "only").

DATA ASSUMPTION: Gate re-presentation instructions must prohibit interpreting
or translating the human's invalid response, not just re-presenting options.

DATA ASSUMPTION: The content must reference pipeline_state.json since it
describes how the routing script determines the next action from persisted state.

DATA ASSUMPTION: The content must instruct not to interrupt agent invocations,
as part of the human input deferral behavioral contract.

DATA ASSUMPTION: The content must instruct not to abandon a partially completed
action cycle, as part of enforcing the complete six-step cycle.
"""

import pytest


# ---------------------------------------------------------------------------
# Helper: safely import ORCHESTRATION_SKILL_MD_CONTENT
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name."""
    import svp.scripts.orchestration_skill as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.orchestration_skill")
    return val


# ===========================================================================
# Gap 1: Full .svp/last_status.txt Path
# ===========================================================================


class TestFullStatusPath:
    """Verify the content references the full .svp/last_status.txt path.

    The ACTION_CYCLE_STEPS step 4 says 'Write the result to .svp/last_status.txt'.
    The content must also use this full path, not just 'last_status.txt'.
    """

    def test_contains_dotsvp_last_status_path(self):
        """Content must reference the full .svp/last_status.txt path."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert ".svp/last_status.txt" in content, (
            "Content must reference the full path '.svp/last_status.txt', "
            "not just 'last_status.txt'"
        )


# ===========================================================================
# Gap 2: Status Line Construction Details
# ===========================================================================


class TestStatusLineConstructionDetails:
    """Verify the content provides concrete status line construction guidance.

    The blueprint says the content must describe 'how to construct status lines.'
    This means concrete format patterns must be present, not just the word 'status'.
    """

    def test_describes_agent_status_lines(self):
        """Content must describe how agent status lines are handled."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        # Agent status lines: the agent produces its own terminal status line
        assert "terminal status" in content_lower or "status line" in content_lower, (
            "Content must describe agent terminal status lines"
        )

    def test_describes_command_status_patterns(self):
        """Content must describe status patterns for command results."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        # Must include at least one concrete status pattern for commands
        assert ("TESTS_PASSED" in content
                or "TESTS_FAILED" in content
                or "COMMAND_SUCCEEDED" in content
                or "COMMAND_FAILED" in content), (
            "Content must include concrete status line patterns like "
            "TESTS_PASSED, TESTS_FAILED, COMMAND_SUCCEEDED, or COMMAND_FAILED"
        )

    def test_describes_gate_status_handling(self):
        """Content must describe how gate responses become status lines."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        # Gate status: the human's chosen option is written as-is
        assert ("chosen option" in content_lower
                or "exact option" in content_lower
                or "option text" in content_lower), (
            "Content must describe that the human's chosen gate option "
            "is written as the status line"
        )


# ===========================================================================
# Gap 3: Routing Script Output Format Description
# ===========================================================================


class TestRoutingScriptOutputFormat:
    """Verify the content describes the routing script's output format.

    The behavioral contract says the content defines 'how to read routing
    script output.' This means the content must describe the structured
    action block format.
    """

    def test_describes_action_block_format(self):
        """Content must describe the action block format from the routing script."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "action block" in content_lower or "structured" in content_lower, (
            "Content must describe the structured action block format"
        )

    def test_describes_action_field(self):
        """Content must reference the ACTION field in the action block."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        # The action block has an ACTION: field
        assert "ACTION:" in content, (
            "Content must reference the ACTION: field in the action block"
        )

    def test_describes_command_field(self):
        """Content must reference the COMMAND field for run_command actions."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "COMMAND:" in content, (
            "Content must reference the COMMAND: field in the action block"
        )


# ===========================================================================
# Gap 4: Routing Script Sole Decision-Maker Exclusivity
# ===========================================================================


class TestRoutingScriptExclusivity:
    """Verify the content conveys the routing script's exclusive authority.

    The blueprint says 'References the routing script as the sole
    decision-maker for pipeline flow.' The word 'sole' implies exclusivity.
    """

    def test_conveys_exclusivity(self):
        """Content must convey the routing script is the sole/only/every decision-maker."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("sole" in content_lower
                or "every decision" in content_lower
                or "only decision" in content_lower), (
            "Content must convey the routing script's exclusive authority "
            "(sole, every decision, or only decision-maker)"
        )


# ===========================================================================
# Gap 5: Gate Invalid Response Prohibition Details
# ===========================================================================


class TestGateInvalidResponseProhibitions:
    """Verify the content prohibits interpreting invalid gate responses.

    The behavioral contract says the main session must re-present gate
    options when the response does not match. The content should also
    prohibit interpreting or translating invalid responses.
    """

    def test_prohibits_interpreting_response(self):
        """Content must prohibit interpreting the human's invalid gate response."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("interpret" in content_lower
                or "translate" in content_lower
                or "guess" in content_lower), (
            "Content must prohibit interpreting/translating/guessing "
            "what the human meant in gate responses"
        )

    def test_requires_exact_match(self):
        """Content must require exact matching for gate options."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("exact" in content_lower
                or "exactly match" in content_lower
                or "partial match" in content_lower), (
            "Content must require exact matching of gate option strings"
        )


# ===========================================================================
# Gap 6: Pipeline State Reference
# ===========================================================================


class TestPipelineStateReference:
    """Verify the content references pipeline_state.json.

    The blueprint lists Unit 10 (Routing Script) as a dependency, and the
    content must describe how the routing script reads persisted state.
    """

    def test_references_pipeline_state_json(self):
        """Content must reference pipeline_state.json."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        assert "pipeline_state.json" in content, (
            "Content must reference pipeline_state.json as the persisted "
            "state file read by the routing script"
        )


# ===========================================================================
# Gap 7: Human Input Deferral -- No Interruption of Agent
# ===========================================================================


class TestHumanInputDeferralDetails:
    """Verify the content provides specific deferral instructions.

    The blueprint says to defer human input during autonomous sequences.
    The content should specifically mention not interrupting agent invocations.
    """

    def test_no_interrupt_agent(self):
        """Content must instruct not to interrupt agent invocations."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "interrupt" in content_lower, (
            "Content must instruct not to interrupt agent invocations "
            "during autonomous sequences"
        )

    def test_no_abandon_cycle(self):
        """Content must instruct not to abandon a partially completed action cycle."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "abandon" in content_lower, (
            "Content must instruct not to abandon a partially completed action cycle"
        )


# ===========================================================================
# Gap 8: Content Describes What Not To Do (Specific Prohibitions)
# ===========================================================================


class TestSpecificProhibitions:
    """Verify the content lists specific behaviors the main session must avoid.

    The blueprint's behavioral contract says the content must instruct
    the main session to avoid improvising. The content should list
    specific prohibited behaviors.
    """

    def test_prohibits_evaluating_agent_outputs(self):
        """Content must prohibit evaluating agent outputs for correctness."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("evaluate" in content_lower
                or "correctness" in content_lower), (
            "Content must prohibit evaluating agent outputs for correctness"
        )

    def test_prohibits_holding_conversation_history(self):
        """Content must prohibit holding domain conversation history."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("conversation history" in content_lower
                or "domain conversation" in content_lower
                or "hold" in content_lower), (
            "Content must prohibit holding domain conversation history"
        )

    def test_prohibits_reasoning_about_pipeline_flow(self):
        """Content must prohibit reasoning about pipeline flow."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("reason about pipeline" in content_lower
                or "predict" in content_lower
                or "reason about" in content_lower), (
            "Content must prohibit reasoning about or predicting pipeline flow"
        )


# ===========================================================================
# Gap 9: Session Boundary -- Resume from Routing Script
# ===========================================================================


class TestSessionBoundaryResumeDetails:
    """Verify the content instructs resuming from the routing script after
    a session boundary, not from memory.

    The blueprint says the content must describe session boundary handling,
    including that on resume the main session must run the routing script
    rather than attempting to resume from memory.
    """

    def test_resume_runs_routing_script(self):
        """Content must instruct running the routing script on session resume."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        # Must describe that on resume, you run the routing script
        assert ("resume" in content_lower or "reopen" in content_lower), (
            "Content must describe session resume behavior"
        )
        assert "routing script" in content_lower, (
            "Content must instruct running the routing script on session resume"
        )

    def test_no_resume_from_memory(self):
        """Content must instruct not to resume from memory."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("memory" in content_lower
                or "left off" in content_lower
                or "persisted" in content_lower), (
            "Content must instruct not to resume from memory but from persisted state"
        )


# ===========================================================================
# Gap 10: Content References prepare_task.py or Preparation Script
# ===========================================================================


class TestPreparationScriptReference:
    """Verify the content references the preparation script mechanism.

    The behavioral contract states the content must describe how the
    PREPARE command produces task prompt files. The content should
    reference the deterministic preparation process.
    """

    def test_describes_prepare_produces_task_prompt(self):
        """Content must describe that PREPARE produces the task prompt file."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert ("prepare" in content_lower
                and ("task prompt" in content_lower or "prompt file" in content_lower)), (
            "Content must describe that the PREPARE command produces "
            "a task prompt file or gate prompt file"
        )

    def test_describes_deterministic_preparation(self):
        """Content must reference deterministic preparation of task prompts."""
        content = _get_md_content("ORCHESTRATION_SKILL_MD_CONTENT")
        content_lower = content.lower()
        assert "deterministic" in content_lower, (
            "Content must reference that task prompt preparation is deterministic"
        )
