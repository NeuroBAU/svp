"""
Coverage gap tests for Unit 9: Preparation Script.

These tests address gaps identified between the blueprint behavioral contracts
and the existing test suite (test_preparation_script.py). They verify:

1. Content presence: agent-specific sections contain the documents the
   blueprint specifies (not just non-empty checks).
2. stakeholder_dialog revision mode: triggered by extra_context["revision_mode"]
   flag, verifying critique and current spec actually appear.
3. Gate prompt response options: explicit response options appear in output.
4. Gate prompt diagnostic context: relevant context included for diagnostic gates.
5. load_ledger_content with .jsonl extension: auto-extension logic.
6. build_task_prompt_content with empty sections dict: edge case.
7. load_reference_summaries with empty index directory.
8. main() CLI entry point invocation.
9. Hint delegation for agents beyond implementation_agent.
10. Loader function pre-conditions (project_root must be a dir).
11. diagnostic_agent without extra_context.

DATA ASSUMPTIONS:
- Stakeholder spec content is plain text / markdown content.
- Blueprint content is markdown with ## Unit N: headings and ### Tier sections.
- Reference summaries content is plain text / markdown.
- Project context is plain text / markdown.
- Ledger content is a JSONL file with role/content/timestamp fields.
- Gate IDs follow the naming convention gate_N_N_description.
- Agent types are a known set enumerated in the behavioral contracts.
- Ladder positions include None, "fresh_test", "hint_test", "fresh_impl",
  "diagnostic", "diagnostic_impl" per Unit 2 FIX_LADDER_POSITIONS.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from svp.scripts.prepare_task import (
    prepare_agent_task,
    prepare_gate_prompt,
    load_stakeholder_spec,
    load_blueprint,
    load_reference_summaries,
    load_project_context,
    load_ledger_content,
    build_task_prompt_content,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path):
    """Create a project directory structure with synthetic data.

    DATA ASSUMPTION: Project structure follows SVP conventions with
    specs/, blueprint/, references/index/, .svp/, and ledgers/ directories.
    Content is minimal placeholder text sufficient for testing.
    """
    # Create directory structure
    (tmp_path / "specs").mkdir()
    (tmp_path / "blueprint").mkdir()
    (tmp_path / "references" / "index").mkdir(parents=True)
    (tmp_path / ".svp").mkdir()
    (tmp_path / ".svp" / "markers").mkdir()
    (tmp_path / "ledgers").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "logs").mkdir()

    # DATA ASSUMPTION: Stakeholder spec is markdown text.
    (tmp_path / "specs" / "stakeholder_spec.md").write_text(
        "# Stakeholder Specification\n\n"
        "This is a test stakeholder specification document.\n"
        "## Requirements\n\n- Requirement 1\n- Requirement 2\n",
        encoding="utf-8",
    )

    # DATA ASSUMPTION: Blueprint is markdown with unit headings.
    (tmp_path / "blueprint" / "blueprint.md").write_text(
        "# Blueprint\n\n"
        "## Unit 1: Test Unit\n\n"
        "### Tier 1 -- Description\n\nA test unit.\n\n"
        "### Tier 2 \u2014 Signatures\n\n"
        "```python\ndef foo() -> str: ...\n```\n\n"
        "### Tier 2 \u2014 Invariants\n\n"
        "```python\nassert True\n```\n\n"
        "### Tier 3 -- Error Conditions\n\nNone.\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n- foo returns 'bar'.\n\n"
        "### Tier 3 -- Dependencies\n\nNone.\n\n"
        "---\n\n"
        "## Unit 2: Another Unit\n\n"
        "### Tier 1 -- Description\n\nAnother test unit.\n\n"
        "### Tier 2 \u2014 Signatures\n\n"
        "```python\ndef bar() -> int: ...\n```\n\n"
        "### Tier 2 \u2014 Invariants\n\n"
        "```python\nassert True\n```\n\n"
        "### Tier 3 -- Error Conditions\n\nNone.\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n- bar returns 42.\n\n"
        "### Tier 3 -- Dependencies\n\n- **Unit 1 (Test Unit):** uses foo.\n\n",
        encoding="utf-8",
    )

    # DATA ASSUMPTION: Reference summaries is a text file.
    (tmp_path / "references" / "index" / "summaries.md").write_text(
        "# Reference Summaries\n\n"
        "## Reference 1\nSummary of reference document 1.\n",
        encoding="utf-8",
    )

    # DATA ASSUMPTION: Project context is a markdown file.
    (tmp_path / ".svp" / "project_context.md").write_text(
        "# Project Context\n\n"
        "This is a test project for SVP pipeline verification.\n",
        encoding="utf-8",
    )

    # DATA ASSUMPTION: Pipeline state is a valid JSON file per Unit 2 schema.
    pipeline_state = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 1,
        "total_units": 2,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test_project",
        "last_action": None,
        "debug_session": None,
        "debug_history": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    (tmp_path / "pipeline_state.json").write_text(
        json.dumps(pipeline_state, indent=2),
        encoding="utf-8",
    )

    # DATA ASSUMPTION: Ledger files are JSONL with conversation entries.
    ledger_entry = {
        "role": "agent",
        "content": "This is a test ledger entry.",
        "timestamp": "2026-01-01T00:00:00",
    }
    # Create multiple named ledgers used by different agents
    for ledger_name in [
        "conversation",
        "setup_dialog",
        "stakeholder_dialog",
        "blueprint_dialog",
        "hint_session",
        "bug_triage",
    ]:
        (tmp_path / "ledgers" / f"{ledger_name}.jsonl").write_text(
            json.dumps(ledger_entry) + "\n",
            encoding="utf-8",
        )

    return tmp_path


# ---------------------------------------------------------------------------
# Gap 1: Content verification for agent-specific sections
# ---------------------------------------------------------------------------


class TestAgentContentPresence:
    """Verify that agent-specific task prompts contain the documents
    the blueprint says they should contain, not just non-empty checks.
    """

    def test_setup_agent_includes_project_context_when_exists(self, project_root):
        """Blueprint: setup_agent includes project context (if exists).
        Verify the project context text actually appears in the output.
        """
        result = prepare_agent_task(project_root, agent_type="setup_agent")
        content = result.read_text(encoding="utf-8")
        # DATA ASSUMPTION: project_context.md contains "SVP pipeline verification"
        assert "SVP pipeline verification" in content

    def test_stakeholder_dialog_includes_reference_summaries(self, project_root):
        """Blueprint: stakeholder_dialog includes reference summaries.
        Verify reference summary text appears in the output.
        """
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_dialog"
        )
        content = result.read_text(encoding="utf-8")
        # DATA ASSUMPTION: summaries.md contains "Summary of reference document 1"
        assert "Summary of reference document 1" in content

    def test_stakeholder_dialog_includes_project_context(self, project_root):
        """Blueprint: stakeholder_dialog includes project context.
        Verify the project context text appears in the output.
        """
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_dialog"
        )
        content = result.read_text(encoding="utf-8")
        assert "SVP pipeline verification" in content

    def test_blueprint_author_includes_stakeholder_spec(self, project_root):
        """Blueprint: blueprint_author includes stakeholder spec.
        Verify the stakeholder spec text appears in the output.
        """
        result = prepare_agent_task(
            project_root, agent_type="blueprint_author"
        )
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_blueprint_author_includes_reference_summaries(self, project_root):
        """Blueprint: blueprint_author includes reference summaries.
        Verify reference summary text appears in the output.
        """
        result = prepare_agent_task(
            project_root, agent_type="blueprint_author"
        )
        content = result.read_text(encoding="utf-8")
        assert "Summary of reference document 1" in content

    def test_blueprint_checker_includes_stakeholder_spec(self, project_root):
        """Blueprint: blueprint_checker includes stakeholder spec.
        Verify the stakeholder spec text appears.
        """
        result = prepare_agent_task(
            project_root, agent_type="blueprint_checker"
        )
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_blueprint_checker_includes_blueprint(self, project_root):
        """Blueprint: blueprint_checker includes blueprint.
        Verify the blueprint text appears.
        """
        result = prepare_agent_task(
            project_root, agent_type="blueprint_checker"
        )
        content = result.read_text(encoding="utf-8")
        # DATA ASSUMPTION: Blueprint contains "Unit 1: Test Unit"
        assert "Unit 1: Test Unit" in content

    def test_blueprint_checker_includes_reference_summaries(self, project_root):
        """Blueprint: blueprint_checker includes reference summaries."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_checker"
        )
        content = result.read_text(encoding="utf-8")
        assert "Summary of reference document 1" in content

    def test_blueprint_reviewer_includes_blueprint(self, project_root):
        """Blueprint: blueprint_reviewer includes blueprint."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "Unit 1: Test Unit" in content

    def test_blueprint_reviewer_includes_stakeholder_spec(self, project_root):
        """Blueprint: blueprint_reviewer includes stakeholder spec."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_blueprint_reviewer_includes_project_context(self, project_root):
        """Blueprint: blueprint_reviewer includes project context."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "SVP pipeline verification" in content

    def test_blueprint_reviewer_includes_reference_summaries(self, project_root):
        """Blueprint: blueprint_reviewer includes reference summaries."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "Summary of reference document 1" in content

    def test_stakeholder_reviewer_includes_stakeholder_spec(self, project_root):
        """Blueprint: stakeholder_reviewer includes stakeholder spec."""
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_stakeholder_reviewer_includes_project_context(self, project_root):
        """Blueprint: stakeholder_reviewer includes project context."""
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "SVP pipeline verification" in content

    def test_stakeholder_reviewer_includes_reference_summaries(self, project_root):
        """Blueprint: stakeholder_reviewer includes reference summaries."""
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert "Summary of reference document 1" in content

    def test_help_agent_includes_stakeholder_spec(self, project_root):
        """Blueprint: help_agent includes stakeholder spec."""
        result = prepare_agent_task(project_root, agent_type="help_agent")
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_help_agent_includes_blueprint(self, project_root):
        """Blueprint: help_agent includes blueprint."""
        result = prepare_agent_task(project_root, agent_type="help_agent")
        content = result.read_text(encoding="utf-8")
        assert "Unit 1: Test Unit" in content

    def test_hint_agent_includes_stakeholder_spec(self, project_root):
        """Blueprint: hint_agent includes stakeholder spec."""
        result = prepare_agent_task(project_root, agent_type="hint_agent")
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_hint_agent_includes_blueprint(self, project_root):
        """Blueprint: hint_agent includes blueprint."""
        result = prepare_agent_task(project_root, agent_type="hint_agent")
        content = result.read_text(encoding="utf-8")
        assert "Unit 1: Test Unit" in content

    def test_diagnostic_agent_includes_stakeholder_spec(self, project_root):
        """Blueprint: diagnostic_agent includes stakeholder spec."""
        result = prepare_agent_task(
            project_root,
            agent_type="diagnostic_agent",
            unit_number=1,
            extra_context={
                "failing_tests": "test_foo FAILED",
                "error_output": "AssertionError",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_integration_test_author_includes_stakeholder_spec(self, project_root):
        """Blueprint: integration_test_author includes stakeholder spec."""
        result = prepare_agent_task(
            project_root, agent_type="integration_test_author"
        )
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_bug_triage_includes_stakeholder_spec(self, project_root):
        """Blueprint: bug_triage includes stakeholder spec."""
        result = prepare_agent_task(project_root, agent_type="bug_triage")
        content = result.read_text(encoding="utf-8")
        assert "Stakeholder Specification" in content

    def test_bug_triage_includes_blueprint(self, project_root):
        """Blueprint: bug_triage includes blueprint."""
        result = prepare_agent_task(project_root, agent_type="bug_triage")
        content = result.read_text(encoding="utf-8")
        assert "Unit 1: Test Unit" in content

    def test_git_repo_agent_includes_reference_summaries(self, project_root):
        """Blueprint: git_repo_agent includes reference documents."""
        result = prepare_agent_task(
            project_root, agent_type="git_repo_agent"
        )
        content = result.read_text(encoding="utf-8")
        assert "Summary of reference document 1" in content

    def test_implementation_agent_includes_ladder_position_in_content(
        self, project_root
    ):
        """Blueprint: implementation_agent in fix ladder shows diagnostic guidance.
        Verify actual diagnostic guidance text appears when provided.
        """
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            ladder_position="fresh_impl",
            extra_context={
                "diagnostic_guidance": "Root cause is off-by-one error in loop.",
                "prior_failure_output": "IndexError at line 42",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "off-by-one error" in content
        assert "IndexError at line 42" in content

    def test_repair_agent_includes_error_diagnosis(self, project_root):
        """Blueprint: repair_agent includes build/environment error diagnosis."""
        result = prepare_agent_task(
            project_root,
            agent_type="repair_agent",
            extra_context={
                "error_diagnosis": "Missing numpy dependency.",
                "environment_state": "Python 3.11 venv.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "Missing numpy dependency" in content

    def test_repair_agent_includes_environment_state(self, project_root):
        """Blueprint: repair_agent includes environment state."""
        result = prepare_agent_task(
            project_root,
            agent_type="repair_agent",
            extra_context={
                "error_diagnosis": "Build error.",
                "environment_state": "Python 3.11, venv active, Linux x86.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "Python 3.11" in content

    def test_redo_agent_includes_human_error_description(self, project_root):
        """Blueprint: redo_agent includes human error description."""
        result = prepare_agent_task(
            project_root,
            agent_type="redo_agent",
            unit_number=1,
            extra_context={
                "human_error_description": "Accidentally approved wrong spec.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "Accidentally approved wrong spec" in content


# ---------------------------------------------------------------------------
# Gap 2: stakeholder_dialog revision mode with revision_mode flag
# ---------------------------------------------------------------------------


class TestStakeholderDialogRevisionMode:
    """Tests for stakeholder_dialog revision mode, which is triggered by
    extra_context containing a 'revision_mode' flag.
    """

    def test_revision_mode_includes_critique(self, project_root):
        """In revision mode, the critique text should appear in the output."""
        result = prepare_agent_task(
            project_root,
            agent_type="stakeholder_dialog",
            extra_context={
                "revision_mode": "true",
                "critique": "The spec lacks error handling detail.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "lacks error handling detail" in content

    def test_revision_mode_includes_current_spec(self, project_root):
        """In revision mode, the current stakeholder spec should be included."""
        result = prepare_agent_task(
            project_root,
            agent_type="stakeholder_dialog",
            extra_context={
                "revision_mode": "true",
                "critique": "Needs more detail.",
            },
        )
        content = result.read_text(encoding="utf-8")
        # The current spec text should appear since revision_mode triggers
        # loading the existing stakeholder spec
        assert "Stakeholder Specification" in content

    def test_revision_mode_flag_false_omits_revision_content(self, project_root):
        """When revision_mode is not set, revision-specific content should
        not be added (no critique heading, no current spec heading).
        """
        result = prepare_agent_task(
            project_root,
            agent_type="stakeholder_dialog",
        )
        content = result.read_text(encoding="utf-8")
        # Without revision mode, these headings should not appear
        assert "Critique Triggering" not in content


# ---------------------------------------------------------------------------
# Gap 3: Gate prompt response options
# ---------------------------------------------------------------------------


class TestGatePromptResponseOptions:
    """Verify that gate prompts contain explicit response options
    as specified by the blueprint.
    """

    def test_test_validation_gate_has_response_options(self, project_root):
        """test_validation gate should present TEST CORRECT / TEST WRONG options."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation", unit_number=1
        )
        content = result.read_text(encoding="utf-8")
        assert "TEST CORRECT" in content
        assert "TEST WRONG" in content

    def test_spec_approval_gate_has_response_options(self, project_root):
        """spec_approval gate should present APPROVE / REVISE options."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_1_1_spec_draft"
        )
        content = result.read_text(encoding="utf-8")
        assert "APPROVE" in content
        assert "REVISE" in content

    def test_blueprint_approval_gate_has_response_options(self, project_root):
        """blueprint_approval gate should present APPROVE / REVISE options."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_2_1_blueprint_approval"
        )
        content = result.read_text(encoding="utf-8")
        assert "APPROVE" in content
        assert "REVISE" in content

    def test_hook_activation_gate_has_response_options(self, project_root):
        """hook_activation gate should present HOOKS ACTIVATED option."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_0_1_hook_activation"
        )
        content = result.read_text(encoding="utf-8")
        assert "HOOKS ACTIVATED" in content

    def test_diagnostic_gate_has_response_options(self, project_root):
        """diagnostic escalation gate should present FIX IMPLEMENTATION / FIX DOCUMENT."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_2_diagnostic_decision"
        )
        content = result.read_text(encoding="utf-8")
        assert "FIX IMPLEMENTATION" in content
        assert "FIX DOCUMENT" in content

    def test_integration_failure_gate_has_response_options(self, project_root):
        """integration_failure gate should present ASSEMBLY FIX / DOCUMENT FIX."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_4_1_integration_failure"
        )
        content = result.read_text(encoding="utf-8")
        assert "ASSEMBLY FIX" in content
        assert "DOCUMENT FIX" in content

    def test_repo_test_gate_has_response_options(self, project_root):
        """repo_test gate should present TESTS PASSED / TESTS FAILED."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_5_1_repo_test"
        )
        content = result.read_text(encoding="utf-8")
        assert "TESTS PASSED" in content
        assert "TESTS FAILED" in content

    def test_debug_permission_gate_has_response_options(self, project_root):
        """debug_permission gate should present AUTHORIZE DEBUG / DENY."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_6_0_debug_permission"
        )
        content = result.read_text(encoding="utf-8")
        assert "AUTHORIZE DEBUG" in content
        assert "DENY" in content

    def test_context_approval_gate_has_response_options(self, project_root):
        """context_approval gate should present APPROVE / REVISE options."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_0_2_context_approval"
        )
        content = result.read_text(encoding="utf-8")
        assert "APPROVE" in content
        assert "REVISE" in content

    def test_regression_test_gate_has_response_options(self, project_root):
        """regression_test gate should present APPROVE / REVISE options."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_6_1_regression_test"
        )
        content = result.read_text(encoding="utf-8")
        assert "APPROVE" in content
        assert "REVISE" in content

    def test_debug_classification_gate_has_response_options(self, project_root):
        """debug_classification gate should present ACCEPT CLASSIFICATION / RECLASSIFY."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_6_2_debug_classification"
        )
        content = result.read_text(encoding="utf-8")
        assert "ACCEPT CLASSIFICATION" in content
        assert "RECLASSIFY" in content


# ---------------------------------------------------------------------------
# Gap 4: Gate prompt diagnostic context
# ---------------------------------------------------------------------------


class TestGatePromptDiagnosticContext:
    """Verify that gate prompts include relevant context such as
    diagnostic analysis when provided via extra_context.
    """

    def test_test_validation_gate_includes_diagnostic_analysis(self, project_root):
        """test_validation gate should include diagnostic analysis content."""
        result = prepare_gate_prompt(
            project_root,
            gate_id="gate_3_1_test_validation",
            unit_number=1,
            extra_context={
                "diagnostic_analysis": "The test expects UTC timestamps but impl uses local.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "UTC timestamps" in content

    def test_diagnostic_decision_gate_includes_diagnostic_analysis(self, project_root):
        """diagnostic decision gate should include diagnostic analysis content."""
        result = prepare_gate_prompt(
            project_root,
            gate_id="gate_3_2_diagnostic_decision",
            unit_number=1,
            extra_context={
                "diagnostic_analysis": "Three-hypothesis analysis: off-by-one.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "off-by-one" in content

    def test_integration_failure_gate_includes_diagnostic_analysis(self, project_root):
        """integration_failure gate should include diagnostic analysis."""
        result = prepare_gate_prompt(
            project_root,
            gate_id="gate_4_1_integration_failure",
            extra_context={
                "diagnostic_analysis": "Contract mismatch between Unit 3 and Unit 4.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "Contract mismatch" in content


# ---------------------------------------------------------------------------
# Gap 5: load_ledger_content with .jsonl extension already present
# ---------------------------------------------------------------------------


class TestLoadLedgerContentExtension:
    """Test that load_ledger_content handles both bare names and names
    with .jsonl extension.
    """

    def test_ledger_name_with_jsonl_extension(self, project_root):
        """When ledger_name already ends in .jsonl, it should still load correctly."""
        result = load_ledger_content(project_root, "conversation.jsonl")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ledger_name_without_extension(self, project_root):
        """Bare ledger name (no .jsonl) should also work."""
        result = load_ledger_content(project_root, "conversation")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Gap 6: build_task_prompt_content with empty sections dict
# ---------------------------------------------------------------------------


class TestBuildTaskPromptEdgeCases:
    """Edge case tests for build_task_prompt_content."""

    def test_empty_sections_dict(self):
        """build_task_prompt_content with empty sections dict should still produce
        valid (non-empty) content with at least the agent type heading.
        """
        result = build_task_prompt_content("setup_agent", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_sections_with_empty_values(self):
        """Sections with empty string values may be skipped in the output."""
        sections = {
            "stakeholder_spec": "",
            "blueprint": "Some blueprint content.",
        }
        result = build_task_prompt_content("blueprint_checker", sections)
        assert isinstance(result, str)
        assert "Some blueprint content" in result


# ---------------------------------------------------------------------------
# Gap 7: load_reference_summaries with empty index directory
# ---------------------------------------------------------------------------


class TestLoadReferenceSummariesEmpty:
    """Test load_reference_summaries when index directory exists but is empty."""

    def test_empty_index_directory(self, tmp_path):
        """When references/index/ exists but contains no files, should return
        empty string (no summaries to load).
        """
        (tmp_path / "references" / "index").mkdir(parents=True)
        result = load_reference_summaries(tmp_path)
        assert isinstance(result, str)
        assert result == ""


# ---------------------------------------------------------------------------
# Gap 8: main() CLI entry point invocation
# ---------------------------------------------------------------------------


class TestMainCLI:
    """Tests for the main() CLI entry point beyond just callable checks."""

    def test_main_with_agent_arg(self, project_root):
        """main() with --agent and --project-root should write a task prompt."""
        test_args = [
            "scripts/prepare.py",
            "--agent", "setup_agent",
            "--project-root", str(project_root),
        ]
        with patch("sys.argv", test_args):
            main()
        output_path = project_root / ".svp" / "task_prompt.md"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_main_with_gate_arg(self, project_root):
        """main() with --gate and --project-root should write a gate prompt."""
        test_args = [
            "scripts/prepare.py",
            "--gate", "gate_3_1_test_validation",
            "--project-root", str(project_root),
        ]
        with patch("sys.argv", test_args):
            main()
        output_path = project_root / ".svp" / "gate_prompt.md"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_main_with_unknown_agent_exits(self, project_root):
        """main() with unknown agent type should exit with error."""
        test_args = [
            "scripts/prepare.py",
            "--agent", "nonexistent_agent",
            "--project-root", str(project_root),
        ]
        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_main_with_nonexistent_project_root(self, tmp_path):
        """main() with nonexistent project root should exit with error."""
        fake_root = tmp_path / "does_not_exist"
        test_args = [
            "scripts/prepare.py",
            "--agent", "setup_agent",
            "--project-root", str(fake_root),
        ]
        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_main_with_unit_number(self, project_root):
        """main() with --unit should pass unit_number to prepare_agent_task."""
        test_args = [
            "scripts/prepare.py",
            "--agent", "test_agent",
            "--project-root", str(project_root),
            "--unit", "1",
        ]
        with patch("sys.argv", test_args):
            main()
        output_path = project_root / ".svp" / "task_prompt.md"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_main_with_hint(self, project_root):
        """main() with --hint should pass hint_content to prepare_agent_task."""
        test_args = [
            "scripts/prepare.py",
            "--agent", "implementation_agent",
            "--project-root", str(project_root),
            "--unit", "1",
            "--hint", "Try a recursive approach.",
        ]
        with patch("sys.argv", test_args):
            main()
        output_path = project_root / ".svp" / "task_prompt.md"
        content = output_path.read_text(encoding="utf-8")
        assert "recursive approach" in content

    def test_main_with_ladder_position(self, project_root):
        """main() with --ladder-position should pass ladder_position."""
        test_args = [
            "scripts/prepare.py",
            "--agent", "implementation_agent",
            "--project-root", str(project_root),
            "--unit", "1",
            "--ladder-position", "fresh_impl",
        ]
        with patch("sys.argv", test_args):
            main()
        output_path = project_root / ".svp" / "task_prompt.md"
        assert output_path.exists()


# ---------------------------------------------------------------------------
# Gap 9: Hint delegation for agents other than implementation_agent
# ---------------------------------------------------------------------------


class TestHintDelegationMultipleAgents:
    """Blueprint: 'When hint_content is provided, delegates to Unit 8.'
    Verify hint delegation works for agents beyond implementation_agent.
    """

    def test_test_agent_hint_delegation(self, project_root):
        """test_agent with hint_content should include hint in output."""
        hint_text = "Focus on boundary conditions for empty lists."
        result = prepare_agent_task(
            project_root,
            agent_type="test_agent",
            unit_number=1,
            hint_content=hint_text,
        )
        content = result.read_text(encoding="utf-8")
        assert "boundary conditions for empty lists" in content

    def test_stakeholder_dialog_hint_delegation(self, project_root):
        """stakeholder_dialog with hint_content should include hint in output."""
        hint_text = "Ask about authentication requirements."
        result = prepare_agent_task(
            project_root,
            agent_type="stakeholder_dialog",
            hint_content=hint_text,
        )
        content = result.read_text(encoding="utf-8")
        assert "authentication requirements" in content

    def test_blueprint_author_hint_delegation(self, project_root):
        """blueprint_author with hint_content should include hint in output."""
        hint_text = "Consider adding a caching layer to Unit 5."
        result = prepare_agent_task(
            project_root,
            agent_type="blueprint_author",
            hint_content=hint_text,
        )
        content = result.read_text(encoding="utf-8")
        assert "caching layer" in content


# ---------------------------------------------------------------------------
# Gap 10: Loader function pre-conditions
# ---------------------------------------------------------------------------


class TestLoaderPreConditions:
    """Verify that loader functions enforce the project_root.is_dir()
    pre-condition from the blueprint invariants.
    """

    def test_load_stakeholder_spec_nonexistent_root(self, tmp_path):
        """load_stakeholder_spec should fail on non-existent project root."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_stakeholder_spec(fake_root)

    def test_load_blueprint_nonexistent_root(self, tmp_path):
        """load_blueprint should fail on non-existent project root."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_blueprint(fake_root)

    def test_load_project_context_nonexistent_root(self, tmp_path):
        """load_project_context should fail on non-existent project root."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_project_context(fake_root)

    def test_load_ledger_content_nonexistent_root(self, tmp_path):
        """load_ledger_content should fail on non-existent project root."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_ledger_content(fake_root, "conversation")

    def test_load_reference_summaries_nonexistent_root(self, tmp_path):
        """load_reference_summaries should fail on non-existent project root."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_reference_summaries(fake_root)


# ---------------------------------------------------------------------------
# Gap 11: diagnostic_agent without extra_context
# ---------------------------------------------------------------------------


class TestDiagnosticAgentMinimal:
    """Test diagnostic_agent with just unit_number, no extra_context."""

    def test_diagnostic_agent_no_extra_context(self, project_root):
        """diagnostic_agent with only unit_number and no extra_context
        should still produce a valid prompt with unit definition and spec.
        """
        result = prepare_agent_task(
            project_root,
            agent_type="diagnostic_agent",
            unit_number=1,
        )
        assert result.exists()
        assert result.stat().st_size > 0
        content = result.read_text(encoding="utf-8")
        # Should still include unit definition from blueprint
        assert "Unit 1" in content


# ---------------------------------------------------------------------------
# Gap 12: help_agent gate_id via parameter (not just extra_context)
# ---------------------------------------------------------------------------


class TestHelpAgentGateIdParameter:
    """Test help_agent gate-invocation mode uses the gate_id parameter directly
    (not just extra_context).
    """

    def test_help_agent_gate_id_appears_in_content(self, project_root):
        """When gate_id parameter is provided, the gate ID should appear
        in the gate invocation context section.
        """
        result = prepare_agent_task(
            project_root,
            agent_type="help_agent",
            gate_id="gate_3_1_test_validation",
        )
        content = result.read_text(encoding="utf-8")
        assert "gate_3_1_test_validation" in content

    def test_help_agent_gate_invocation_section_present(self, project_root):
        """When gate_id parameter is provided, the gate invocation context
        section should be present.
        """
        result = prepare_agent_task(
            project_root,
            agent_type="help_agent",
            gate_id="gate_2_1_blueprint_approval",
        )
        content = result.read_text(encoding="utf-8")
        assert "Gate Invocation" in content or "decision gate" in content.lower()


# ---------------------------------------------------------------------------
# Gap 13: Gate prompt includes gate_id in content
# ---------------------------------------------------------------------------


class TestGatePromptGateIdInContent:
    """Verify the gate ID appears in the gate prompt output file."""

    def test_gate_prompt_contains_gate_id(self, project_root):
        """The gate prompt content should reference the gate_id."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation", unit_number=1
        )
        content = result.read_text(encoding="utf-8")
        assert "gate_3_1_test_validation" in content

    def test_gate_prompt_for_spec_contains_gate_id(self, project_root):
        """Spec approval gate prompt should reference the gate_id."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_1_1_spec_draft"
        )
        content = result.read_text(encoding="utf-8")
        assert "gate_1_1_spec_draft" in content


# ---------------------------------------------------------------------------
# Gap 14: blueprint_author checker_feedback appears in content
# ---------------------------------------------------------------------------


class TestBlueprintAuthorCheckerFeedback:
    """Verify blueprint_author includes checker feedback content
    when provided (not just a non-empty check).
    """

    def test_checker_feedback_text_in_output(self, project_root):
        """The checker feedback text should appear in the assembled prompt."""
        result = prepare_agent_task(
            project_root,
            agent_type="blueprint_author",
            extra_context={
                "checker_feedback": "Unit 3 signature mismatch with spec requirements.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "Unit 3 signature mismatch" in content


# ---------------------------------------------------------------------------
# Gap 15: git_repo_agent error_output appears in fix cycle content
# ---------------------------------------------------------------------------


class TestGitRepoAgentFixCycleContent:
    """Verify git_repo_agent error output actually appears in content."""

    def test_error_output_text_in_fix_cycle(self, project_root):
        """The error output text should appear in the assembled prompt."""
        result = prepare_agent_task(
            project_root,
            agent_type="git_repo_agent",
            extra_context={
                "error_output": "ModuleNotFoundError: No module named 'custom_lib'.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert "ModuleNotFoundError" in content
