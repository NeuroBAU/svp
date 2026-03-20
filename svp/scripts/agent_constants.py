"""Agent definition constants used by tests and scripts.

Provides frontmatter schemas and terminal status line vocabularies
for all SVP agents. These are the same constants embedded in agent .md files.
"""
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Unit 13: Dialog Agents
# ---------------------------------------------------------------------------

SETUP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "setup_agent",
    "description": "Creates project_context.md and project_profile.json through Socratic dialog",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

STAKEHOLDER_DIALOG_FRONTMATTER: Dict[str, Any] = {
    "name": "stakeholder_dialog",
    "description": "Conducts Socratic dialog to produce stakeholder specification",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Glob", "Grep"],
}

BLUEPRINT_AUTHOR_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_author",
    "description": "Writes and revises the technical blueprint",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Glob", "Grep"],
}

# ---------------------------------------------------------------------------
# Unit 14: Review and Checker Agents
# ---------------------------------------------------------------------------

STAKEHOLDER_REVIEWER_FRONTMATTER: Dict[str, Any] = {
    "name": "stakeholder_reviewer",
    "description": "Reviews stakeholder spec cold, produces structured critique",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

BLUEPRINT_CHECKER_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_checker",
    "description": "Verifies blueprint alignment with stakeholder spec and project profile",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}

BLUEPRINT_REVIEWER_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_reviewer",
    "description": "Reviews blueprint cold, produces structured critique",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

STAKEHOLDER_REVIEWER_STATUS: List[str] = ["REVIEW_COMPLETE"]
BLUEPRINT_CHECKER_STATUS: List[str] = [
    "ALIGNMENT_CONFIRMED",
    "ALIGNMENT_FAILED: spec",
    "ALIGNMENT_FAILED: blueprint",
]
BLUEPRINT_REVIEWER_STATUS: List[str] = ["REVIEW_COMPLETE"]

# ---------------------------------------------------------------------------
# Unit 15: Construction Agents
# ---------------------------------------------------------------------------

TEST_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "test_agent",
    "description": "Generates pytest test suite for a single unit",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Glob", "Grep"],
}

IMPLEMENTATION_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "implementation_agent",
    "description": "Implements a single unit to make tests pass",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

COVERAGE_REVIEW_FRONTMATTER: Dict[str, Any] = {
    "name": "coverage_review",
    "description": "Reviews test coverage and adds tests for uncovered paths",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

TEST_AGENT_STATUS: List[str] = ["TEST_GENERATION_COMPLETE"]
IMPLEMENTATION_AGENT_STATUS: List[str] = ["IMPLEMENTATION_COMPLETE"]
COVERAGE_REVIEW_STATUS: List[str] = [
    "COVERAGE_COMPLETE: no gaps",
    "COVERAGE_COMPLETE: tests added",
]

# ---------------------------------------------------------------------------
# Unit 16: Diagnostic and Classification Agents
# ---------------------------------------------------------------------------

DIAGNOSTIC_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "diagnostic_agent",
    "description": "Diagnoses test failures and produces structured fix recommendations",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}

REDO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "redo_agent",
    "description": "Classifies /svp:redo requests into spec, blueprint, gate, or profile categories",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

DIAGNOSTIC_AGENT_STATUS: List[str] = [
    "DIAGNOSIS_COMPLETE: implementation",
    "DIAGNOSIS_COMPLETE: blueprint",
    "DIAGNOSIS_COMPLETE: spec",
]

REDO_AGENT_STATUS: List[str] = [
    "REDO_CLASSIFIED: spec",
    "REDO_CLASSIFIED: blueprint",
    "REDO_CLASSIFIED: gate",
    "REDO_CLASSIFIED: profile_delivery",
    "REDO_CLASSIFIED: profile_blueprint",
]

# ---------------------------------------------------------------------------
# Unit 17: Support Agents
# ---------------------------------------------------------------------------

HELP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "help_agent",
    "description": "Provides contextual help for the current pipeline stage",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

HINT_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "hint_agent",
    "description": "Analyzes hint requests and forwards qualified hints to the blueprint",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Glob", "Grep"],
}

HELP_AGENT_STATUS: List[str] = [
    "HELP_SESSION_COMPLETE: no hint",
    "HELP_SESSION_COMPLETE: hint forwarded",
]
HINT_AGENT_STATUS: List[str] = ["HINT_ANALYSIS_COMPLETE"]

# ---------------------------------------------------------------------------
# Unit 18: Utility Agents
# ---------------------------------------------------------------------------

REFERENCE_INDEXING_FRONTMATTER: Dict[str, Any] = {
    "name": "reference_indexing_agent",
    "description": "Reads reference documents and produces structured summaries",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Glob", "Grep"],
}

INTEGRATION_TEST_AUTHOR_FRONTMATTER: Dict[str, Any] = {
    "name": "integration_test_author",
    "description": "Generates integration tests covering cross-unit interactions",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

GIT_REPO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "git_repo_agent",
    "description": "Creates clean git repository from verified artifacts with profile-driven delivery",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

REFERENCE_INDEXING_STATUS: List[str] = ["INDEXING_COMPLETE"]
INTEGRATION_TEST_AUTHOR_STATUS: List[str] = ["INTEGRATION_TESTS_COMPLETE"]
GIT_REPO_AGENT_STATUS: List[str] = ["REPO_ASSEMBLY_COMPLETE"]

# ---------------------------------------------------------------------------
# Unit 19: Debug Loop Agents
# ---------------------------------------------------------------------------

BUG_TRIAGE_FRONTMATTER: Dict[str, Any] = {
    "name": "bug_triage",
    "description": "Triages post-delivery bugs and produces structured diagnosis",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Bash", "Glob", "Grep"],
}

REPAIR_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "repair_agent",
    "description": "Repairs post-delivery bugs in the delivered repository",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

BUG_TRIAGE_STATUS: List[str] = [
    "TRIAGE_COMPLETE: build_env",
    "TRIAGE_COMPLETE: single_unit",
    "TRIAGE_COMPLETE: cross_unit",
    "TRIAGE_NEEDS_REFINEMENT",
    "TRIAGE_NON_REPRODUCIBLE",
]
REPAIR_AGENT_STATUS: List[str] = ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"]
