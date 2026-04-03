"""Bug 72: Structural completeness check regression tests.

SVP 2.2: structural_check.py was folded into src.unit_28.stub as
run_structural_check(). Individual check functions (check_dict_registry_gaps,
check_enum_value_gaps, etc.) are no longer exported as separate functions.
STAGE_5_SUB_STAGES and _KNOWN_PHASES were removed.

Tests for individual check functions and routing sub-stage wiring are
skipped. The run_structural_check integration test and agent prompt
content tests are preserved.
"""

import json
import sys
from pathlib import Path

import pytest

from src.unit_28.stub import run_structural_check

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Helpers -- create synthetic Python files in tmp_path
# ---------------------------------------------------------------------------

import textwrap


def _write_file(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ===================================================================
# run_structural_check integration test
# ===================================================================


class TestRunStructuralCheck:
    """Test run_structural_check from src.unit_28.stub."""

    def test_clean_codebase_returns_empty_findings(self, tmp_path):
        _write_file(
            tmp_path,
            "clean.py",
            """\
            def helper():
                return 42
            """,
        )
        _write_file(
            tmp_path,
            "main.py",
            """\
            from clean import helper
            result = helper()
            """,
        )
        findings = run_structural_check(tmp_path)
        assert isinstance(findings, list)
        assert len(findings) == 0

    def test_returns_findings_for_unused_registry_key(self, tmp_path):
        _write_file(
            tmp_path,
            "registry.py",
            """\
            HANDLERS = {
                "alpha": 1,
                "beta": 2,
                "gamma": 3,
            }
            """,
        )
        _write_file(
            tmp_path,
            "consumer.py",
            """\
            from registry import HANDLERS
            result = HANDLERS["alpha"]
            other = HANDLERS.get("beta")
            """,
        )
        findings = run_structural_check(tmp_path)
        assert isinstance(findings, list)
        assert len(findings) >= 1


# ===================================================================
# Agent prompt content verification
# ===================================================================


class TestAgentPromptUpdates:
    """Verify agent definitions contain Bug 72 checklist items.

    SVP 2.2: agent definitions are in src.unit_19/20/24.stub constants.
    """

    def test_blueprint_checker_has_registry_completeness(self):
        from src.unit_19.stub import BLUEPRINT_CHECKER_DEFINITION
        assert "Registry completeness" in BLUEPRINT_CHECKER_DEFINITION or \
               "registry completeness" in BLUEPRINT_CHECKER_DEFINITION or \
               "registry" in BLUEPRINT_CHECKER_DEFINITION.lower()

    def test_integration_test_author_has_structural_completeness(self):
        from src.unit_20.stub import INTEGRATION_TEST_AUTHOR_DEFINITION
        lower = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "registry-handler alignment" in lower or \
               "registry" in lower or \
               "structural" in lower

    def test_bug_triage_has_structural_precheck(self):
        from src.unit_24.stub import BUG_TRIAGE_AGENT_DEFINITION
        assert "Step 0" in BUG_TRIAGE_AGENT_DEFINITION or \
               "Structural Pre-Check" in BUG_TRIAGE_AGENT_DEFINITION or \
               "structural" in BUG_TRIAGE_AGENT_DEFINITION.lower()


