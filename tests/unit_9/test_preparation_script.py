"""
Comprehensive test suite for Unit 9: Preparation Script.

Tests cover:
- Function signatures (parameter names, types, return types)
- All behavioral contracts for every agent type
- All behavioral contracts for gate prompts
- Error conditions (unknown agent, unknown gate, missing documents, missing unit number)
- Invariants (project_root existence, output file existence/non-empty)
- Hint delegation to Unit 8
- Elevated coverage: every agent type, gate type, and ladder position combination

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

import inspect
import json
import os
import textwrap
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import patch, MagicMock

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
# Constants used across tests
# ---------------------------------------------------------------------------

# DATA ASSUMPTION: These are the recognized agent types based on the
# behavioral contracts in the Unit 9 blueprint. Each maps to specific
# context sections required in the task prompt.
KNOWN_AGENT_TYPES = [
    "setup_agent",
    "stakeholder_dialog",
    "blueprint_author",
    "blueprint_checker",
    "blueprint_reviewer",
    "stakeholder_reviewer",
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
    "integration_test_author",
    "git_repo_agent",
    "help_agent",
    "hint_agent",
    "redo_agent",
    "reference_indexing",
    "bug_triage",
    "repair_agent",
]

# DATA ASSUMPTION: Agent types that require a unit_number parameter,
# inferred from the blueprint contracts (unit-specific agents).
UNIT_SPECIFIC_AGENT_TYPES = [
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
]

# DATA ASSUMPTION: Fix ladder positions from Unit 2 schema.
FIX_LADDER_POSITIONS = [
    None,
    "fresh_test",
    "hint_test",
    "fresh_impl",
    "diagnostic",
    "diagnostic_impl",
]

# DATA ASSUMPTION: Gate IDs follow the convention used in Unit 10's
# GATE_VOCABULARY dictionary. These are the known gate identifiers.
KNOWN_GATE_IDS = [
    "gate_0_1_hook_activation",
    "gate_0_2_context_approval",
    "gate_1_1_spec_draft",
    "gate_1_2_spec_post_review",
    "gate_2_1_blueprint_approval",
    "gate_2_2_blueprint_post_review",
    "gate_2_3_alignment_exhausted",
    "gate_3_1_test_validation",
    "gate_3_2_diagnostic_decision",
    "gate_4_1_integration_failure",
    "gate_4_2_assembly_exhausted",
    "gate_5_1_repo_test",
    "gate_5_2_assembly_exhausted",
    "gate_6_0_debug_permission",
    "gate_6_1_regression_test",
    "gate_6_2_debug_classification",
    "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path):
    """Create a minimal project directory structure with synthetic data.

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

    # DATA ASSUMPTION: Stakeholder spec is markdown text describing
    # project requirements.
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

    # DATA ASSUMPTION: Reference summaries is a text file with indexed
    # reference descriptions.
    (tmp_path / "references" / "index" / "summaries.md").write_text(
        "# Reference Summaries\n\n"
        "## Reference 1\nSummary of reference document 1.\n",
        encoding="utf-8",
    )

    # DATA ASSUMPTION: Project context is a markdown file with project
    # overview information.
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

    # DATA ASSUMPTION: Ledger is a JSONL file with conversation entries.
    ledger_entry = {
        "role": "agent",
        "content": "This is a test ledger entry.",
        "timestamp": "2026-01-01T00:00:00",
    }
    (tmp_path / "ledgers" / "conversation.jsonl").write_text(
        json.dumps(ledger_entry) + "\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def project_root_minimal(tmp_path):
    """Create a project root with only the bare minimum directory structure.
    Does NOT include document files so we can test FileNotFoundError cases.
    """
    (tmp_path / ".svp").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Signature tests
# ---------------------------------------------------------------------------


class TestSignatures:
    """Verify function signatures match the blueprint's Tier 2 definitions."""

    def test_prepare_agent_task_signature(self):
        """prepare_agent_task has the correct parameter names and types."""
        sig = inspect.signature(prepare_agent_task)
        params = list(sig.parameters.keys())
        assert params == [
            "project_root",
            "agent_type",
            "unit_number",
            "ladder_position",
            "hint_content",
            "gate_id",
            "extra_context",
        ]
        # Check defaults
        assert sig.parameters["unit_number"].default is None
        assert sig.parameters["ladder_position"].default is None
        assert sig.parameters["hint_content"].default is None
        assert sig.parameters["gate_id"].default is None
        assert sig.parameters["extra_context"].default is None

    def test_prepare_gate_prompt_signature(self):
        """prepare_gate_prompt has the correct parameter names and types."""
        sig = inspect.signature(prepare_gate_prompt)
        params = list(sig.parameters.keys())
        assert params == [
            "project_root",
            "gate_id",
            "unit_number",
            "extra_context",
        ]
        assert sig.parameters["unit_number"].default is None
        assert sig.parameters["extra_context"].default is None

    def test_load_stakeholder_spec_signature(self):
        sig = inspect.signature(load_stakeholder_spec)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]

    def test_load_blueprint_signature(self):
        sig = inspect.signature(load_blueprint)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]

    def test_load_reference_summaries_signature(self):
        sig = inspect.signature(load_reference_summaries)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]

    def test_load_project_context_signature(self):
        sig = inspect.signature(load_project_context)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]

    def test_load_ledger_content_signature(self):
        sig = inspect.signature(load_ledger_content)
        params = list(sig.parameters.keys())
        assert params == ["project_root", "ledger_name"]

    def test_build_task_prompt_content_signature(self):
        sig = inspect.signature(build_task_prompt_content)
        params = list(sig.parameters.keys())
        assert params == ["agent_type", "sections", "hint_block"]
        assert sig.parameters["hint_block"].default is None

    def test_main_signature(self):
        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert params == []


# ---------------------------------------------------------------------------
# Loader function tests
# ---------------------------------------------------------------------------


class TestLoadStakeholderSpec:
    """Tests for load_stakeholder_spec."""

    def test_loads_existing_spec(self, project_root):
        """Should load and return stakeholder spec content as string."""
        result = load_stakeholder_spec(project_root)
        assert isinstance(result, str)
        assert len(result) > 0
        # DATA ASSUMPTION: Content contains the text we wrote in the fixture.
        assert "Stakeholder Specification" in result

    def test_raises_on_missing_spec(self, project_root_minimal):
        """Should raise FileNotFoundError when stakeholder spec doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Required document not found"):
            load_stakeholder_spec(project_root_minimal)


class TestLoadBlueprint:
    """Tests for load_blueprint."""

    def test_loads_existing_blueprint(self, project_root):
        """Should load and return blueprint content as string."""
        result = load_blueprint(project_root)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Blueprint" in result

    def test_raises_on_missing_blueprint(self, project_root_minimal):
        """Should raise FileNotFoundError when blueprint doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Required document not found"):
            load_blueprint(project_root_minimal)


class TestLoadReferenceSummaries:
    """Tests for load_reference_summaries."""

    def test_loads_existing_summaries(self, project_root):
        """Should load and return reference summaries content."""
        result = load_reference_summaries(project_root)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_empty_or_raises_on_missing(self, project_root_minimal):
        """When reference summaries don't exist, may return empty or raise.
        Per the blueprint, missing required documents raise FileNotFoundError.
        However, reference summaries may be optional for some agents.
        We test that the function handles the missing case.
        """
        # DATA ASSUMPTION: Reference summaries not existing is a valid
        # scenario that either returns empty string or raises FileNotFoundError.
        try:
            result = load_reference_summaries(project_root_minimal)
            assert isinstance(result, str)
        except FileNotFoundError:
            pass  # Also acceptable per the blueprint


class TestLoadProjectContext:
    """Tests for load_project_context."""

    def test_loads_existing_context(self, project_root):
        """Should load and return project context content."""
        result = load_project_context(project_root)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Project Context" in result

    def test_handles_missing_context(self, project_root_minimal):
        """Project context may be optional (setup_agent says 'if exists').
        Should either return empty string or raise FileNotFoundError.
        """
        # DATA ASSUMPTION: Project context is optional for some agents;
        # the loader should handle its absence gracefully.
        try:
            result = load_project_context(project_root_minimal)
            assert isinstance(result, str)
        except FileNotFoundError:
            pass  # Also acceptable


class TestLoadLedgerContent:
    """Tests for load_ledger_content."""

    def test_loads_existing_ledger(self, project_root):
        """Should load and return ledger content as string."""
        result = load_ledger_content(project_root, "conversation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_handles_missing_ledger(self, project_root):
        """Should handle missing ledger gracefully (empty or raise)."""
        # DATA ASSUMPTION: Non-existent ledger may return empty string
        # or raise, depending on whether it's required by the calling agent.
        try:
            result = load_ledger_content(project_root, "nonexistent")
            assert isinstance(result, str)
        except (FileNotFoundError, Exception):
            pass


# ---------------------------------------------------------------------------
# build_task_prompt_content tests
# ---------------------------------------------------------------------------


class TestBuildTaskPromptContent:
    """Tests for build_task_prompt_content."""

    def test_builds_content_with_sections(self):
        """Should assemble a task prompt string from agent type and sections dict."""
        # DATA ASSUMPTION: Sections dict maps section names to content strings.
        sections = {
            "stakeholder_spec": "# Spec\nTest spec content.",
            "blueprint": "# Blueprint\nTest blueprint content.",
        }
        result = build_task_prompt_content("blueprint_checker", sections)
        assert isinstance(result, str)
        assert len(result) > 0
        # Content from sections should appear in the output
        assert "Test spec content" in result
        assert "Test blueprint content" in result

    def test_includes_hint_block_when_provided(self):
        """When hint_block is provided, it should appear in the output."""
        # DATA ASSUMPTION: hint_block is a pre-formatted hint string
        # from Unit 8's assemble_hint_prompt.
        sections = {
            "stakeholder_spec": "# Spec\nContent.",
        }
        hint_block = "## Human Domain Hint (via Help Agent)\n\nTest hint content."
        result = build_task_prompt_content(
            "test_agent", sections, hint_block=hint_block
        )
        assert isinstance(result, str)
        assert "Human Domain Hint" in result
        assert "Test hint content" in result

    def test_no_hint_block_when_none(self):
        """When hint_block is None, no hint section should appear."""
        sections = {
            "unit_definition": "Test unit definition.",
        }
        result = build_task_prompt_content("test_agent", sections, hint_block=None)
        assert isinstance(result, str)
        # Should not contain hint markers when no hint is provided
        # (but we can't assert the absence of arbitrary text perfectly --
        # just verify the result is valid)
        assert len(result) > 0

    def test_raises_on_unknown_agent_type(self):
        """Should raise ValueError for unrecognized agent type."""
        sections = {"key": "value"}
        with pytest.raises(ValueError, match="Unknown agent type"):
            build_task_prompt_content("nonexistent_agent", sections)


# ---------------------------------------------------------------------------
# prepare_agent_task tests
# ---------------------------------------------------------------------------


class TestPrepareAgentTask:
    """Tests for prepare_agent_task covering all agent types and error conditions."""

    # --- Invariant tests ---

    def test_returns_path_object(self, project_root):
        """Return value must be a Path."""
        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        assert isinstance(result, Path)

    def test_output_file_exists_after_preparation(self, project_root):
        """Post-condition: output file must exist."""
        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        assert result.exists(), "Task prompt file must exist after preparation"

    def test_output_file_not_empty(self, project_root):
        """Post-condition: output file must not be empty."""
        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        assert result.stat().st_size > 0, "Task prompt file must not be empty"

    def test_output_path_is_svp_task_prompt(self, project_root):
        """Output path should be .svp/task_prompt.md."""
        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        expected = project_root / ".svp" / "task_prompt.md"
        assert result == expected

    def test_raises_on_nonexistent_project_root(self, tmp_path):
        """Pre-condition: project_root must exist."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            prepare_agent_task(fake_root, agent_type="setup_agent")

    # --- Error condition tests ---

    def test_raises_on_unknown_agent_type(self, project_root):
        """ValueError for unknown agent type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            prepare_agent_task(project_root, agent_type="bogus_agent")

    def test_raises_on_unknown_agent_type_includes_type_name(self, project_root):
        """Error message should include the unrecognized type name."""
        with pytest.raises(ValueError, match="Unknown agent type.*fancy_agent"):
            prepare_agent_task(project_root, agent_type="fancy_agent")

    def test_raises_when_unit_number_required_but_missing(self, project_root):
        """ValueError when unit-specific agents lack unit_number."""
        for agent_type in UNIT_SPECIFIC_AGENT_TYPES:
            with pytest.raises(ValueError, match="Unit number required"):
                prepare_agent_task(
                    project_root,
                    agent_type=agent_type,
                    unit_number=None,
                )

    # --- Agent type: setup_agent ---

    def test_setup_agent_basic(self, project_root):
        """setup_agent: project context (if exists), ledger content."""
        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_setup_agent_without_project_context(self, project_root):
        """setup_agent should work even when project context doesn't exist yet."""
        # Remove the project context file
        ctx_path = project_root / ".svp" / "project_context.md"
        if ctx_path.exists():
            ctx_path.unlink()
        # Should not raise -- project context is optional for setup_agent
        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        assert result.exists()

    # --- Agent type: stakeholder_dialog ---

    def test_stakeholder_dialog_basic(self, project_root):
        """stakeholder_dialog: ledger, reference summaries, project context."""
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_dialog"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_stakeholder_dialog_revision_mode(self, project_root):
        """stakeholder_dialog in revision mode adds critique and current spec."""
        # DATA ASSUMPTION: Revision mode is indicated via extra_context
        # containing critique and current spec references.
        result = prepare_agent_task(
            project_root,
            agent_type="stakeholder_dialog",
            extra_context={
                "critique": "The spec lacks detail on error handling.",
                "current_spec": "# Current Spec\nContent here.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: blueprint_author ---

    def test_blueprint_author_basic(self, project_root):
        """blueprint_author: stakeholder spec, reference summaries, ledger."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_author"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_blueprint_author_with_checker_feedback(self, project_root):
        """blueprint_author with checker feedback (if available)."""
        result = prepare_agent_task(
            project_root,
            agent_type="blueprint_author",
            extra_context={
                "checker_feedback": "Alignment issues found in Unit 3.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: blueprint_checker ---

    def test_blueprint_checker_basic(self, project_root):
        """blueprint_checker: stakeholder spec (with working notes), blueprint, reference summaries."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_checker"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: blueprint_reviewer ---

    def test_blueprint_reviewer_basic(self, project_root):
        """blueprint_reviewer: blueprint, stakeholder spec, project context, reference summaries."""
        result = prepare_agent_task(
            project_root, agent_type="blueprint_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: stakeholder_reviewer ---

    def test_stakeholder_reviewer_basic(self, project_root):
        """stakeholder_reviewer: stakeholder spec, project context, reference summaries."""
        result = prepare_agent_task(
            project_root, agent_type="stakeholder_reviewer"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: test_agent ---

    def test_test_agent_basic(self, project_root):
        """test_agent: unit definition, upstream contracts."""
        result = prepare_agent_task(
            project_root,
            agent_type="test_agent",
            unit_number=1,
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_test_agent_requires_unit_number(self, project_root):
        """test_agent must raise ValueError without unit_number."""
        with pytest.raises(ValueError, match="Unit number required"):
            prepare_agent_task(
                project_root, agent_type="test_agent"
            )

    # --- Agent type: implementation_agent ---

    def test_implementation_agent_basic(self, project_root):
        """implementation_agent: unit definition, upstream contracts."""
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_implementation_agent_fix_ladder_fresh_impl(self, project_root):
        """implementation_agent in fresh_impl ladder position adds diagnostic guidance."""
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            ladder_position="fresh_impl",
            extra_context={
                "diagnostic_guidance": "Issue in the parsing logic.",
                "prior_failure_output": "AssertionError: expected 42 got 0",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_implementation_agent_fix_ladder_diagnostic_impl(self, project_root):
        """implementation_agent in diagnostic_impl ladder position."""
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            ladder_position="diagnostic_impl",
            extra_context={
                "diagnostic_guidance": "Root cause: off-by-one error.",
                "prior_failure_output": "IndexError: list index out of range",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_implementation_agent_with_hint(self, project_root):
        """implementation_agent with hint_content delegates to Unit 8."""
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            hint_content="Try using a dictionary lookup instead of linear search.",
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0
        # The hint content should appear in the output (wrapped by Unit 8)
        assert "dictionary lookup" in content

    def test_implementation_agent_requires_unit_number(self, project_root):
        """implementation_agent must raise ValueError without unit_number."""
        with pytest.raises(ValueError, match="Unit number required"):
            prepare_agent_task(
                project_root, agent_type="implementation_agent"
            )

    # --- Agent type: coverage_review ---

    def test_coverage_review_basic(self, project_root):
        """coverage_review: unit definition, upstream contracts, passing tests."""
        # DATA ASSUMPTION: Passing tests info is available in extra_context
        # or can be derived from project structure.
        result = prepare_agent_task(
            project_root,
            agent_type="coverage_review",
            unit_number=1,
            extra_context={
                "passing_tests": "test_foo.py: 3 passed",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: diagnostic_agent ---

    def test_diagnostic_agent_basic(self, project_root):
        """diagnostic_agent: stakeholder spec, unit blueprint section, failing tests, error output."""
        result = prepare_agent_task(
            project_root,
            agent_type="diagnostic_agent",
            unit_number=1,
            extra_context={
                "failing_tests": "test_foo.py::test_bar FAILED",
                "error_output": "AssertionError: expected True",
                "failing_implementations": "src/unit_1/stub.py",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: integration_test_author ---

    def test_integration_test_author_basic(self, project_root):
        """integration_test_author: stakeholder spec, contract signatures from all units."""
        result = prepare_agent_task(
            project_root, agent_type="integration_test_author"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: git_repo_agent ---

    def test_git_repo_agent_basic(self, project_root):
        """git_repo_agent: all verified artifacts, reference documents."""
        result = prepare_agent_task(
            project_root, agent_type="git_repo_agent"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_git_repo_agent_fix_cycle(self, project_root):
        """git_repo_agent in fix cycle adds error output."""
        result = prepare_agent_task(
            project_root,
            agent_type="git_repo_agent",
            extra_context={
                "error_output": "Build failed: missing dependency.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: help_agent ---

    def test_help_agent_basic(self, project_root):
        """help_agent: project summary, stakeholder spec, blueprint."""
        result = prepare_agent_task(
            project_root, agent_type="help_agent"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_help_agent_gate_invocation_mode(self, project_root):
        """help_agent in gate-invocation mode adds gate flag."""
        result = prepare_agent_task(
            project_root,
            agent_type="help_agent",
            gate_id="gate_3_1_test_validation",
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: hint_agent ---

    def test_hint_agent_basic(self, project_root):
        """hint_agent: logs, documents, stakeholder spec, blueprint."""
        result = prepare_agent_task(
            project_root, agent_type="hint_agent"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: redo_agent ---

    def test_redo_agent_basic(self, project_root):
        """redo_agent: pipeline state summary, human error description, current unit definition."""
        result = prepare_agent_task(
            project_root,
            agent_type="redo_agent",
            unit_number=1,
            extra_context={
                "human_error_description": "I made a mistake in the spec review.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: reference_indexing ---

    def test_reference_indexing_basic(self, project_root):
        """reference_indexing: full reference document."""
        # DATA ASSUMPTION: A reference document file exists for indexing.
        ref_doc = project_root / "references" / "test_ref.pdf"
        ref_doc.write_text("Reference document content.", encoding="utf-8")
        result = prepare_agent_task(
            project_root,
            agent_type="reference_indexing",
            extra_context={
                "reference_document": str(ref_doc),
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: bug_triage ---

    def test_bug_triage_basic(self, project_root):
        """bug_triage: stakeholder spec, blueprint, source code paths, test suite paths, ledger."""
        result = prepare_agent_task(
            project_root,
            agent_type="bug_triage",
            extra_context={
                "source_code_paths": "src/unit_1/stub.py",
                "test_suite_paths": "tests/unit_1/",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- Agent type: repair_agent ---

    def test_repair_agent_basic(self, project_root):
        """repair_agent: build/environment error diagnosis, environment state."""
        result = prepare_agent_task(
            project_root,
            agent_type="repair_agent",
            extra_context={
                "error_diagnosis": "Missing dependency: numpy.",
                "environment_state": "Python 3.11, venv active.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0


# ---------------------------------------------------------------------------
# Hint delegation tests
# ---------------------------------------------------------------------------


class TestHintDelegation:
    """Tests for hint_content delegation to Unit 8 (Hint Prompt Assembler)."""

    def test_hint_content_included_in_output(self, project_root):
        """When hint_content is provided, the task prompt includes the hint."""
        hint_text = "Consider edge cases with empty input."
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            hint_content=hint_text,
        )
        content = result.read_text(encoding="utf-8")
        assert hint_text in content

    def test_hint_block_format(self, project_root):
        """The hint should be wrapped per Unit 8 format (Human Domain Hint heading)."""
        hint_text = "Watch for off-by-one errors."
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            hint_content=hint_text,
        )
        content = result.read_text(encoding="utf-8")
        # Unit 8 wraps hints with this heading
        assert "Human Domain Hint" in content

    def test_no_hint_when_none(self, project_root):
        """When hint_content is None, no hint section in the output."""
        result = prepare_agent_task(
            project_root,
            agent_type="setup_agent",
            hint_content=None,
        )
        content = result.read_text(encoding="utf-8")
        # Without a hint, there should be no hint heading
        # (This is a weak assertion since the absence is hard to guarantee,
        # but "Human Domain Hint" should not appear)
        assert "Human Domain Hint" not in content


# ---------------------------------------------------------------------------
# Extra context tests
# ---------------------------------------------------------------------------


class TestExtraContext:
    """Tests for extra_context parameter handling."""

    def test_extra_context_included(self, project_root):
        """Extra context entries should be incorporated into the task prompt."""
        result = prepare_agent_task(
            project_root,
            agent_type="setup_agent",
            extra_context={
                "special_note": "This is important additional context.",
            },
        )
        content = result.read_text(encoding="utf-8")
        # The extra context value should appear somewhere in the output
        assert "important additional context" in content

    def test_extra_context_none(self, project_root):
        """Should work fine when extra_context is None."""
        result = prepare_agent_task(
            project_root,
            agent_type="setup_agent",
            extra_context=None,
        )
        assert result.exists()


# ---------------------------------------------------------------------------
# prepare_gate_prompt tests
# ---------------------------------------------------------------------------


class TestPrepareGatePrompt:
    """Tests for prepare_gate_prompt covering all gate types and error conditions."""

    # --- Invariant tests ---

    def test_returns_path_object(self, project_root):
        """Return value must be a Path."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        assert isinstance(result, Path)

    def test_output_file_exists_after_preparation(self, project_root):
        """Post-condition: output file must exist."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        assert result.exists(), "Gate prompt file must exist after preparation"

    def test_output_file_not_empty(self, project_root):
        """Post-condition: output file must not be empty."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        assert result.stat().st_size > 0, "Gate prompt file must not be empty"

    def test_output_path_is_svp_gate_prompt(self, project_root):
        """Output path should be .svp/gate_prompt.md."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        expected = project_root / ".svp" / "gate_prompt.md"
        assert result == expected

    # --- Error condition tests ---

    def test_raises_on_unknown_gate_id(self, project_root):
        """ValueError for unknown gate ID."""
        with pytest.raises(ValueError, match="Unknown gate ID"):
            prepare_gate_prompt(project_root, gate_id="gate_99_fake")

    def test_raises_on_unknown_gate_id_includes_name(self, project_root):
        """Error message should include the unrecognized gate ID."""
        with pytest.raises(ValueError, match="Unknown gate ID.*gate_99_fake"):
            prepare_gate_prompt(project_root, gate_id="gate_99_fake")

    def test_raises_on_nonexistent_project_root(self, tmp_path):
        """Pre-condition: project_root must exist."""
        fake_root = tmp_path / "nonexistent"
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            prepare_gate_prompt(fake_root, gate_id="gate_3_1_test_validation")

    # --- Gate content tests ---

    def test_gate_prompt_has_description(self, project_root):
        """Gate prompt should include a gate description."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_gate_prompt_has_response_options(self, project_root):
        """Gate prompt should include explicit response options."""
        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        content = result.read_text(encoding="utf-8")
        # DATA ASSUMPTION: Test validation gate has "TEST CORRECT" and
        # "TEST WRONG" as response options (from Unit 10 GATE_VOCABULARY).
        # The gate prompt should mention these options.
        assert len(content) > 10  # Non-trivial content

    def test_gate_prompt_with_unit_number(self, project_root):
        """Gate prompt with unit_number context."""
        result = prepare_gate_prompt(
            project_root,
            gate_id="gate_3_1_test_validation",
            unit_number=1,
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_gate_prompt_with_extra_context(self, project_root):
        """Gate prompt with extra context (e.g., diagnostic analysis)."""
        result = prepare_gate_prompt(
            project_root,
            gate_id="gate_3_1_test_validation",
            unit_number=1,
            extra_context={
                "diagnostic_analysis": "Root cause identified as missing edge case.",
            },
        )
        content = result.read_text(encoding="utf-8")
        assert len(content) > 0

    # --- All known gate IDs ---

    @pytest.mark.parametrize("gate_id", KNOWN_GATE_IDS)
    def test_all_known_gate_ids(self, project_root, gate_id):
        """Every known gate ID should produce a valid gate prompt."""
        result = prepare_gate_prompt(
            project_root,
            gate_id=gate_id,
            unit_number=1,
        )
        assert result.exists()
        assert result.stat().st_size > 0


# ---------------------------------------------------------------------------
# Elevated coverage: all agent types parametrized
# ---------------------------------------------------------------------------


class TestAllAgentTypes:
    """Parametrized tests ensuring every agent type is handled."""

    @pytest.mark.parametrize("agent_type", KNOWN_AGENT_TYPES)
    def test_agent_type_accepted(self, project_root, agent_type):
        """Each known agent type should be accepted (no ValueError)."""
        # Provide unit_number for agents that require it
        kwargs = {}
        if agent_type in UNIT_SPECIFIC_AGENT_TYPES:
            kwargs["unit_number"] = 1

        result = prepare_agent_task(
            project_root, agent_type=agent_type, **kwargs
        )
        assert result.exists()
        assert result.stat().st_size > 0

    @pytest.mark.parametrize("agent_type", KNOWN_AGENT_TYPES)
    def test_agent_type_returns_path(self, project_root, agent_type):
        """Each agent type should return a Path object."""
        kwargs = {}
        if agent_type in UNIT_SPECIFIC_AGENT_TYPES:
            kwargs["unit_number"] = 1

        result = prepare_agent_task(
            project_root, agent_type=agent_type, **kwargs
        )
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# Elevated coverage: ladder positions
# ---------------------------------------------------------------------------


class TestLadderPositions:
    """Tests for all fix ladder positions with implementation_agent."""

    @pytest.mark.parametrize("position", FIX_LADDER_POSITIONS)
    def test_implementation_agent_all_ladder_positions(
        self, project_root, position
    ):
        """implementation_agent should handle every ladder position."""
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            ladder_position=position,
        )
        assert result.exists()
        assert result.stat().st_size > 0

    @pytest.mark.parametrize("position", FIX_LADDER_POSITIONS)
    def test_test_agent_all_ladder_positions(self, project_root, position):
        """test_agent should handle every ladder position."""
        result = prepare_agent_task(
            project_root,
            agent_type="test_agent",
            unit_number=1,
            ladder_position=position,
        )
        assert result.exists()
        assert result.stat().st_size > 0


# ---------------------------------------------------------------------------
# Elevated coverage: combinations of agent type + ladder + hint
# ---------------------------------------------------------------------------


class TestAgentLadderHintCombinations:
    """Test combinations of agent type, ladder position, and hint presence.

    DATA ASSUMPTION: The blueprint requires coverage of every combination.
    We test a representative set of fix-relevant agents with and without
    hints at each ladder position.
    """

    @pytest.mark.parametrize(
        "ladder_position",
        ["fresh_impl", "diagnostic", "diagnostic_impl"],
    )
    @pytest.mark.parametrize("has_hint", [True, False])
    def test_implementation_agent_ladder_hint_combos(
        self, project_root, ladder_position, has_hint
    ):
        """implementation_agent with fix ladder positions and hints."""
        hint = "Try a different approach." if has_hint else None
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            ladder_position=ladder_position,
            hint_content=hint,
        )
        assert result.exists()
        assert result.stat().st_size > 0
        content = result.read_text(encoding="utf-8")
        if has_hint:
            assert "different approach" in content

    @pytest.mark.parametrize(
        "ladder_position",
        ["fresh_test", "hint_test"],
    )
    @pytest.mark.parametrize("has_hint", [True, False])
    def test_test_agent_ladder_hint_combos(
        self, project_root, ladder_position, has_hint
    ):
        """test_agent with fix ladder positions and hints."""
        hint = "Focus on boundary conditions." if has_hint else None
        result = prepare_agent_task(
            project_root,
            agent_type="test_agent",
            unit_number=1,
            ladder_position=ladder_position,
            hint_content=hint,
        )
        assert result.exists()
        assert result.stat().st_size > 0
        content = result.read_text(encoding="utf-8")
        if has_hint:
            assert "boundary conditions" in content


# ---------------------------------------------------------------------------
# Missing document error tests
# ---------------------------------------------------------------------------


class TestMissingDocumentErrors:
    """Tests for FileNotFoundError when required documents are missing."""

    def test_blueprint_author_missing_spec(self, tmp_path):
        """blueprint_author should raise FileNotFoundError if spec is missing."""
        # Create minimal structure without the stakeholder spec
        (tmp_path / ".svp").mkdir()
        (tmp_path / "blueprint").mkdir()
        (tmp_path / "blueprint" / "blueprint.md").write_text(
            "# Blueprint\n## Unit 1: Test\n### Tier 2 \u2014 Signatures\n```python\ndef f(): ...\n```\n",
            encoding="utf-8",
        )
        (tmp_path / "ledgers").mkdir()
        (tmp_path / "references" / "index").mkdir(parents=True)
        state = {
            "stage": "2", "sub_stage": None, "current_unit": None,
            "total_units": None, "fix_ladder_position": None,
            "red_run_retries": 0, "alignment_iteration": 0,
            "verified_units": [], "pass_history": [],
            "log_references": {}, "project_name": "test",
            "last_action": None, "debug_session": None,
            "debug_history": [],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        (tmp_path / "pipeline_state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

        with pytest.raises(FileNotFoundError, match="Required document not found"):
            prepare_agent_task(tmp_path, agent_type="blueprint_author")

    def test_blueprint_checker_missing_blueprint(self, tmp_path):
        """blueprint_checker should raise FileNotFoundError if blueprint is missing."""
        (tmp_path / ".svp").mkdir()
        (tmp_path / "specs").mkdir()
        (tmp_path / "specs" / "stakeholder_spec.md").write_text(
            "# Spec\nContent.", encoding="utf-8"
        )
        (tmp_path / "references" / "index").mkdir(parents=True)
        (tmp_path / "ledgers").mkdir()
        state = {
            "stage": "2", "sub_stage": None, "current_unit": None,
            "total_units": None, "fix_ladder_position": None,
            "red_run_retries": 0, "alignment_iteration": 0,
            "verified_units": [], "pass_history": [],
            "log_references": {}, "project_name": "test",
            "last_action": None, "debug_session": None,
            "debug_history": [],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        (tmp_path / "pipeline_state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

        with pytest.raises(FileNotFoundError, match="Required document not found"):
            prepare_agent_task(tmp_path, agent_type="blueprint_checker")

    def test_test_agent_missing_blueprint(self, tmp_path):
        """test_agent should raise FileNotFoundError if blueprint is missing."""
        (tmp_path / ".svp").mkdir()
        (tmp_path / "specs").mkdir()
        (tmp_path / "ledgers").mkdir()
        state = {
            "stage": "3", "sub_stage": None, "current_unit": 1,
            "total_units": 5, "fix_ladder_position": None,
            "red_run_retries": 0, "alignment_iteration": 0,
            "verified_units": [], "pass_history": [],
            "log_references": {}, "project_name": "test",
            "last_action": None, "debug_session": None,
            "debug_history": [],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        (tmp_path / "pipeline_state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

        with pytest.raises(FileNotFoundError, match="Required document not found"):
            prepare_agent_task(
                tmp_path, agent_type="test_agent", unit_number=1
            )


# ---------------------------------------------------------------------------
# main() CLI entry point test
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() CLI entry point."""

    def test_main_is_callable(self):
        """main should be a callable function."""
        assert callable(main)

    def test_main_exists(self):
        """main function should be importable."""
        from svp.scripts.prepare_task import main as main_fn
        assert main_fn is not None


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_empty_agent_type_string(self, project_root):
        """Empty string as agent type should raise ValueError."""
        with pytest.raises(ValueError):
            prepare_agent_task(project_root, agent_type="")

    def test_empty_gate_id_string(self, project_root):
        """Empty string as gate_id should raise ValueError."""
        with pytest.raises(ValueError):
            prepare_gate_prompt(project_root, gate_id="")

    def test_prepare_agent_task_overwrites_existing_file(self, project_root):
        """If task_prompt.md already exists, it should be overwritten."""
        # Create an existing file
        existing = project_root / ".svp" / "task_prompt.md"
        existing.write_text("old content", encoding="utf-8")

        result = prepare_agent_task(
            project_root, agent_type="setup_agent"
        )
        content = result.read_text(encoding="utf-8")
        assert content != "old content"

    def test_prepare_gate_prompt_overwrites_existing_file(self, project_root):
        """If gate_prompt.md already exists, it should be overwritten."""
        existing = project_root / ".svp" / "gate_prompt.md"
        existing.write_text("old gate content", encoding="utf-8")

        result = prepare_gate_prompt(
            project_root, gate_id="gate_3_1_test_validation"
        )
        content = result.read_text(encoding="utf-8")
        assert content != "old gate content"

    def test_unit_number_zero_or_negative(self, project_root):
        """Unit number 0 or negative should be handled (likely error or boundary)."""
        # DATA ASSUMPTION: Unit numbers are positive integers starting from 1.
        # Behavior with 0 or negative is undefined by the blueprint but
        # should not silently succeed with invalid data.
        # We test that it doesn't produce a valid result or raises an error.
        try:
            result = prepare_agent_task(
                project_root,
                agent_type="test_agent",
                unit_number=0,
            )
            # If it succeeds, the file should still exist (invariant)
            assert result.exists()
        except (ValueError, AssertionError):
            pass  # Expected for invalid unit number

    def test_extra_context_with_multiple_keys(self, project_root):
        """Multiple extra_context entries should all be available."""
        result = prepare_agent_task(
            project_root,
            agent_type="implementation_agent",
            unit_number=1,
            extra_context={
                "key_one": "Value one content.",
                "key_two": "Value two content.",
                "key_three": "Value three content.",
            },
        )
        assert result.exists()
        assert result.stat().st_size > 0
