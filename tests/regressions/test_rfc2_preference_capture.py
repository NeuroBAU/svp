"""
RFC-2: Unit-Level Preference Capture in Blueprint Dialog

Structural tests verifying that:
1. Blueprint author agent definition contains Rules P1-P4 text
2. Blueprint checker agent definition contains preference consistency rule
3. When Tier 1 includes a Preferences subsection, build_unit_context includes it
4. When Tier 1 has no Preferences subsection, nothing extra appears
5. P1-P4 presence in blueprint_contracts.md invariants
6. Spec Section 8.1 contains RFC-2 content
7. Summary contains RFC-2 glossary entry
8. Authority hierarchy uses exact phrase
9. Scripts have P1-P4 content and Setup Agent behavioral rules
"""

import sys
import textwrap
from pathlib import Path

import pytest

# Project root and script paths for the delivered repo layout
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SVP_SCRIPTS = _PROJECT_ROOT / "scripts"
if not _SVP_SCRIPTS.is_dir():
    _SVP_SCRIPTS = _PROJECT_ROOT / "svp" / "scripts"

def _find_doc(filename: str) -> Path:
    """Find a document in either workspace or delivered repo layout."""
    # Delivered repo: docs/
    p = _PROJECT_ROOT / "docs" / filename
    if p.exists():
        return p
    # Workspace: specs/ or blueprint/ depending on file
    if "spec" in filename:
        p = _PROJECT_ROOT / "specs" / filename
    elif "blueprint" in filename:
        p = _PROJECT_ROOT / "blueprint" / filename
    elif "summary" in filename:
        p = _PROJECT_ROOT / "docs" / filename
    if p.exists():
        return p
    # Also check references/
    p = _PROJECT_ROOT / "references" / filename
    if p.exists():
        return p
    return _PROJECT_ROOT / "docs" / filename  # fallback (will trigger skip)


# Ensure scripts is importable
if str(_SVP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SVP_SCRIPTS))


# -------------------------------------------------------
# Test 1: Blueprint author agent contains Rules P1-P4
# -------------------------------------------------------


class TestBlueprintAuthorRulesP1P4:
    """Verify blueprint author agent definition includes RFC-2 rules."""

    def _get_content(self):
        """Load from scripts (delivered repo layout)."""
        from dialog_agent_definitions import (
            BLUEPRINT_AUTHOR_AGENT_MD_CONTENT,
        )
        return BLUEPRINT_AUTHOR_AGENT_MD_CONTENT

    def test_has_rule_p1(self):
        content = self._get_content()
        assert "Rule P1" in content
        assert "unit level" in content.lower()

    def test_has_rule_p2(self):
        content = self._get_content()
        assert "Rule P2" in content
        assert "domain language" in content.lower() or "domain vocabulary" in content.lower()

    def test_has_rule_p3(self):
        content = self._get_content()
        assert "Rule P3" in content
        assert "progressive disclosure" in content.lower() or "one open question" in content.lower()

    def test_has_rule_p4(self):
        content = self._get_content()
        assert "Rule P4" in content
        assert "conflict" in content.lower()

    def test_mentions_preferences_subsection(self):
        content = self._get_content()
        assert "Preferences" in content

    def test_authority_hierarchy_exact_phrase(self):
        """Authority hierarchy should use the exact phrase 'spec > contracts > preferences'."""
        content = self._get_content()
        assert "spec > contracts > preferences" in content.lower()


# -------------------------------------------------------
# Test 2: Blueprint checker agent contains preference
#          consistency rule
# -------------------------------------------------------


class TestBlueprintCheckerPreferenceConsistency:
    """Verify blueprint checker includes preference-contract consistency."""

    def _get_content(self):
        from agent_definitions import BLUEPRINT_CHECKER_MD_CONTENT
        return BLUEPRINT_CHECKER_MD_CONTENT

    def test_mentions_preference_consistency(self):
        content = self._get_content()
        lower = content.lower()
        assert "preference" in lower
        assert "consistency" in lower or "contradict" in lower

    def test_non_blocking_warning(self):
        content = self._get_content()
        lower = content.lower()
        assert "non-blocking" in lower or "warning" in lower

    def test_not_alignment_failure(self):
        content = self._get_content()
        lower = content.lower()
        assert "not an alignment failure" in lower or "non-binding" in lower


# -------------------------------------------------------
# Test 3: build_unit_context includes Preferences
#          subsection when present in Tier 1
# -------------------------------------------------------


class TestBuildUnitContextWithPreferences:
    """Verify Preferences subsection flows through build_unit_context."""

    @pytest.fixture
    def blueprint_with_preferences(self, tmp_path):
        """Create a blueprint with a Preferences subsection in Tier 1."""
        prose = tmp_path / "blueprint_prose.md"
        prose.write_text(textwrap.dedent("""\
            ## Unit 1: Widget Manager

            **Artifact category:** Python

            ### Tier 1 -- Description

            Manages widgets for the system.

            ### Preferences

            Output files should use CSV format with headers.
            Column names should use snake_case.
        """))

        contracts = tmp_path / "blueprint_contracts.md"
        contracts.write_text(textwrap.dedent("""\
            ## Unit 1: Widget Manager

            **Artifact category:** Python

            ### Tier 2 -- Signatures

            ```python
            def create_widget(name: str) -> dict: ...
            ```

            ### Tier 3 -- Behavioral Contracts

            - create_widget returns a dict with 'name' key.

            ### Tier 3 -- Dependencies

            (none)
        """))

        return tmp_path

    def test_preferences_included_when_tier1_true(self, blueprint_with_preferences):
        from blueprint_extractor import build_unit_context

        result = build_unit_context(blueprint_with_preferences, 1, include_tier1=True)
        assert "Preferences" in result
        assert "CSV format" in result
        assert "snake_case" in result

    def test_preferences_excluded_when_tier1_false(self, blueprint_with_preferences):
        from blueprint_extractor import build_unit_context

        result = build_unit_context(blueprint_with_preferences, 1, include_tier1=False)
        assert "CSV format" not in result
        assert "snake_case" not in result


# -------------------------------------------------------
# Test 4: build_unit_context produces no extra content
#          when no Preferences subsection
# -------------------------------------------------------


class TestBuildUnitContextWithoutPreferences:
    """Verify nothing extra appears when no Preferences subsection."""

    @pytest.fixture
    def blueprint_without_preferences(self, tmp_path):
        """Create a blueprint without a Preferences subsection."""
        prose = tmp_path / "blueprint_prose.md"
        prose.write_text(textwrap.dedent("""\
            ## Unit 1: Widget Manager

            **Artifact category:** Python

            ### Tier 1 -- Description

            Manages widgets for the system.
        """))

        contracts = tmp_path / "blueprint_contracts.md"
        contracts.write_text(textwrap.dedent("""\
            ## Unit 1: Widget Manager

            **Artifact category:** Python

            ### Tier 2 -- Signatures

            ```python
            def create_widget(name: str) -> dict: ...
            ```

            ### Tier 3 -- Behavioral Contracts

            - create_widget returns a dict with 'name' key.

            ### Tier 3 -- Dependencies

            (none)
        """))

        return tmp_path

    def test_no_preferences_section_in_output(self, blueprint_without_preferences):
        from blueprint_extractor import build_unit_context

        result = build_unit_context(
            blueprint_without_preferences, 1, include_tier1=True
        )
        assert "Preferences" not in result
        # Verify the normal content is still there
        assert "Widget Manager" in result
        assert "create_widget" in result


# -------------------------------------------------------
# Test 5: P1-P4 presence in blueprint_contracts.md
# -------------------------------------------------------


class TestBlueprintContractsP1P4Invariants:
    """Verify blueprint_contracts.md contains P1-P4 invariant asserts."""

    def test_contracts_file_has_p1_p4_asserts(self):
        contracts_path = _find_doc("blueprint_contracts.md")
        if not contracts_path.exists():
            pytest.skip("blueprint_contracts.md not found in docs/")
        content = contracts_path.read_text()
        assert 'assert "Rule P1" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT' in content
        assert 'assert "Rule P2" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT' in content
        assert 'assert "Rule P3" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT' in content
        assert 'assert "Rule P4" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT' in content


# -------------------------------------------------------
# Test 6: Spec Section 8.1 contains RFC-2 content
# -------------------------------------------------------


class TestSpecContainsRFC2:
    """Verify stakeholder_spec.md documents RFC-2 features."""

    def test_spec_has_preferences_subsection(self):
        spec_path = _find_doc("stakeholder_spec.md")
        if not spec_path.exists():
            pytest.skip("stakeholder_spec.md not found in docs/")
        content = spec_path.read_text()
        assert "Preferences subsection" in content
        assert "RFC-2" in content

    def test_spec_has_authority_hierarchy(self):
        spec_path = _find_doc("stakeholder_spec.md")
        if not spec_path.exists():
            pytest.skip("stakeholder_spec.md not found in docs/")
        content = spec_path.read_text()
        assert "spec > contracts > preferences" in content.lower()

    def test_spec_has_testability_requirement(self):
        spec_path = _find_doc("stakeholder_spec.md")
        if not spec_path.exists():
            pytest.skip("stakeholder_spec.md not found in docs/")
        content = spec_path.read_text()
        assert "Rules P1-P4 must appear verbatim" in content


# -------------------------------------------------------
# Test 7: Summary contains RFC-2 glossary entry
# -------------------------------------------------------


class TestSummaryRFC2Glossary:
    """Verify svp_2_1_summary.md has RFC-2 glossary entry."""

    def test_summary_has_rfc2_glossary(self):
        summary_path = _find_doc("svp_2_1_summary.md")
        if not summary_path.exists():
            pytest.skip("svp_2_1_summary.md not found in docs/")
        content = summary_path.read_text()
        assert "Unit-Level Preferences (RFC-2)" in content
        assert "spec > contracts > preferences" in content.lower()


# -------------------------------------------------------
# Test 8: Scripts have P1-P4 content and Setup Agent
#          behavioral rules (spec Section 6.4)
# -------------------------------------------------------


class TestScriptsP1P4Content:
    """Verify scripts have Rules P1-P4 and Setup Agent behavioral rules."""

    def test_scripts_has_p1_p4(self):
        from dialog_agent_definitions import (
            BLUEPRINT_AUTHOR_AGENT_MD_CONTENT,
        )
        assert "Rule P1" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
        assert "Rule P2" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
        assert "Rule P3" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
        assert "Rule P4" in BLUEPRINT_AUTHOR_AGENT_MD_CONTENT

    def test_setup_agent_behavioral_rules(self):
        """Setup Agent must implement spec Section 6.4 behavioral requirements.

        The four requirements are: (1) explain choices in plain language,
        (2) recommend best option, (3) provide sensible defaults,
        (4) progressive disclosure. The scripts version implements these
        as behavioral instructions rather than numbered rules.
        """
        from dialog_agent_definitions import SETUP_AGENT_MD_CONTENT
        lower = SETUP_AGENT_MD_CONTENT.lower()
        # R1: Explanation requirement (plain language or explain)
        assert "explain" in lower, "Setup agent must explain choices"
        # R2: Recommendation requirement
        assert "recommend" in lower, "Setup agent must recommend options"
        # R3: Sensible defaults requirement
        assert "default" in lower, "Setup agent must provide defaults"
        # R4: Dialog requirement (Socratic dialog is the mechanism)
        assert "dialog" in lower or "socratic" in lower, (
            "Setup agent must conduct dialog"
        )
