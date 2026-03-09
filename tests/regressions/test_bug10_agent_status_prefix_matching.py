"""Regression tests for Bug 10: Agent Status Line Handler Exact Matching.

Root cause: dispatch_agent_status validation correctly used prefix matching
(startswith()) to accept agent status lines with trailing context, but several
internal handler functions (_handle_stakeholder_dialog, _handle_project_context,
_handle_bug_triage, _handle_repair) used exact == matching. When an agent
appended trailing context (e.g., 'TEST_GENERATION_COMPLETE: 45 tests'), the
status passed validation but the handler silently fell through to 'return state'
without performing the intended state transition.

Fix: all handler functions use startswith() consistently with the validation
layer. The spec (Section 18.1) now explicitly documents that agent status lines
use prefix matching, distinct from gate status strings (Section 18.4) which use
exact matching.
"""

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTING_PY = REPO_ROOT / "svp" / "scripts" / "routing.py"


# Handler functions that dispatch on agent status lines.
# These must use startswith(), never ==, to match status lines.
AGENT_HANDLER_FUNCTIONS = [
    "_handle_test_generation",
    "_handle_implementation",
    "_handle_coverage_review",
    "_handle_diagnostic",
    "_handle_alignment_check",
    "_handle_stakeholder_dialog",
    "_handle_project_context",
    "_handle_bug_triage",
    "_handle_repair",
]

# Known agent status prefixes that appear in handler conditionals
AGENT_STATUS_PREFIXES = [
    "SPEC_DRAFT_COMPLETE",
    "SPEC_REVISION_COMPLETE",
    "PROJECT_CONTEXT_COMPLETE",
    "PROJECT_CONTEXT_REJECTED",
    "TRIAGE_NEEDS_REFINEMENT",
    "TRIAGE_NON_REPRODUCIBLE",
    "REPAIR_COMPLETE",
    "REPAIR_FAILED",
    "REPAIR_RECLASSIFY",
    "ALIGNMENT_CONFIRMED",
    "ALIGNMENT_FAILED",
    "COVERAGE_COMPLETE",
    "TRIAGE_COMPLETE",
]


def _extract_handler_comparisons(source: str) -> list[dict]:
    """Extract all string comparisons in agent handler functions.

    Returns a list of dicts with keys: function, line, comparison_type, value.
    comparison_type is 'exact' for == and 'prefix' for startswith().
    """
    tree = ast.parse(source)
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in AGENT_HANDLER_FUNCTIONS:
            continue

        for child in ast.walk(node):
            # Check for exact == comparisons: status == "SOME_STATUS"
            if isinstance(child, ast.Compare):
                for op, comparator in zip(child.ops, child.comparators):
                    if isinstance(op, ast.Eq) and isinstance(comparator, ast.Constant):
                        val = comparator.value
                        if isinstance(val, str) and val in AGENT_STATUS_PREFIXES:
                            results.append({
                                "function": node.name,
                                "line": child.lineno,
                                "comparison_type": "exact",
                                "value": val,
                            })

            # Check for startswith() calls
            if isinstance(child, ast.Call):
                if (isinstance(child.func, ast.Attribute)
                        and child.func.attr == "startswith"
                        and child.args
                        and isinstance(child.args[0], ast.Constant)):
                    val = child.args[0].value
                    if isinstance(val, str) and any(
                        val.startswith(prefix) for prefix in AGENT_STATUS_PREFIXES
                    ):
                        results.append({
                            "function": node.name,
                            "line": child.lineno,
                            "comparison_type": "prefix",
                            "value": val,
                        })

    return results


def test_no_exact_matching_in_agent_handlers():
    """Agent status handler functions must not use exact == matching.

    All status line comparisons in _handle_* functions must use
    startswith() to support agents appending trailing context.
    """
    source = ROUTING_PY.read_text(encoding="utf-8")
    comparisons = _extract_handler_comparisons(source)

    exact_matches = [c for c in comparisons if c["comparison_type"] == "exact"]
    assert not exact_matches, (
        f"Agent handler functions use exact == matching for status lines "
        f"(must use startswith()): {exact_matches}"
    )


def test_handler_functions_use_startswith_for_status_checks():
    """Verify that handlers checking agent status prefixes use startswith()."""
    source = ROUTING_PY.read_text(encoding="utf-8")
    comparisons = _extract_handler_comparisons(source)

    prefix_matches = [c for c in comparisons if c["comparison_type"] == "prefix"]
    # There should be at least one startswith() call for the handlers
    # that branch on status values
    assert len(prefix_matches) > 0, (
        "No startswith() calls found in agent handler functions -- "
        "handlers must use prefix matching for agent status lines"
    )
