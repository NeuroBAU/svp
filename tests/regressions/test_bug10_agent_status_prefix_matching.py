"""Regression tests for Bug 10: Agent Status Line Handler Prefix Matching.

Root cause: dispatch_agent_status validation correctly used prefix matching
(startswith()) to accept agent status lines with trailing context, but several
internal handler functions used exact == matching. When an agent appended
trailing context (e.g., 'TEST_GENERATION_COMPLETE: 45 tests'), the status
passed validation but the handler silently fell through to 'return state'
without performing the intended state transition.

Fix: all handler functions use startswith() consistently with the validation
layer. This test verifies the behavioral fix by checking that status lines
with trailing context are handled correctly.
"""

from svp.scripts.dispatch import dispatch_agent_status
from svp.scripts.pipeline_state import PipelineState


def _make_state(**overrides) -> PipelineState:
    """Create a minimal PipelineState for testing."""
    defaults = dict(
        stage="3",
        sub_stage="test_generation",
        current_unit=1,
        total_units=3,
        fix_ladder_position=None,
        red_run_retries=0,
        alignment_iteration=0,
        project_name="test_project",
        pass_history=[],
        debug_session=None,
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestAgentStatusPrefixMatching:
    """Verify agent status handlers support trailing context."""

    def test_stakeholder_dialog_with_trailing_context(self, tmp_path):
        """SPEC_DRAFT_COMPLETE with trailing context should advance to approval."""
        state = _make_state(stage="1", sub_stage="stakeholder_dialog")
        result = dispatch_agent_status(
            state,
            "",
            "SPEC_DRAFT_COMPLETE: 45 specs written",
            None,
            "stakeholder_dialog",
            tmp_path,
        )
        assert result.sub_stage == "approval"

    def test_stakeholder_revision_with_trailing_context(self, tmp_path):
        """SPEC_REVISION_COMPLETE with trailing context should advance to approval."""
        state = _make_state(stage="1", sub_stage="stakeholder_dialog")
        result = dispatch_agent_status(
            state,
            "",
            "SPEC_REVISION_COMPLETE: 12 revisions made",
            None,
            "stakeholder_dialog",
            tmp_path,
        )
        assert result.sub_stage == "approval"

    def test_project_context_complete_with_trailing_context(self, tmp_path):
        """PROJECT_CONTEXT_COMPLETE with trailing context should advance stage."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = dispatch_agent_status(
            state,
            "",
            "PROJECT_CONTEXT_COMPLETE: /path/to/context.md",
            None,
            "project_context",
            tmp_path,
        )
        assert result.stage == "1"

    def test_alignment_confirmed_with_trailing_context(self, tmp_path):
        """ALIGNMENT_CONFIRMED with trailing context should advance to approval."""
        state = _make_state(stage="2", sub_stage="alignment_check")
        result = dispatch_agent_status(
            state,
            "",
            "ALIGNMENT_CONFIRMED: 95% alignment",
            None,
            "alignment_check",
            tmp_path,
        )
        assert result.sub_stage == "approval"

    def test_coverage_complete_with_trailing_context(self, tmp_path):
        """COVERAGE_COMPLETE with trailing context should route correctly."""
        state = _make_state(stage="3", sub_stage="coverage_review")
        result = dispatch_agent_status(
            state,
            "",
            "COVERAGE_COMPLETE: tests added (15 new tests)",
            None,
            "coverage_review",
            tmp_path,
        )
        assert result.sub_stage == "green_run"

    def test_triage_complete_build_env_with_trailing_context(self, tmp_path):
        """TRIAGE_COMPLETE: build_env with trailing context should work."""
        from svp.scripts.pipeline_state import DebugSession

        debug = DebugSession(
            bug_id=1,
            description="Test bug",
            classification="build_env",
            affected_units=[1],
            phase="regression_test",
            authorized=True,
        )
        state = _make_state(stage="5", debug_session=debug)
        result = dispatch_agent_status(
            state,
            "",
            "TRIAGE_COMPLETE: build_env: /path/to/log",
            None,
            "bug_triage",
            tmp_path,
        )
        assert result.debug_session is not None
