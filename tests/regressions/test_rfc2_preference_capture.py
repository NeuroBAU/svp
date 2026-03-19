"""
RFC-2: Unit-Level Preference Capture in Blueprint Dialog

Structural tests verifying that:
1. Blueprint author agent definition contains Rules P1-P4 text
2. Blueprint checker agent definition contains preference consistency rule
3. When Tier 1 includes a Preferences subsection, build_unit_context includes it
4. When Tier 1 has no Preferences subsection, nothing extra appears
"""

import textwrap
from pathlib import Path

import pytest


# -------------------------------------------------------
# Test 1: Blueprint author agent contains Rules P1-P4
# -------------------------------------------------------


class TestBlueprintAuthorRulesP1P4:
    """Verify blueprint author agent definition includes RFC-2 rules."""

    def _get_content(self):
        """Load from workspace scripts (primary) or stub."""
        try:
            from scripts.dialog_agent_definitions import (
                BLUEPRINT_AUTHOR_AGENT_MD_CONTENT,
            )
        except ImportError:
            from src.unit_13.stub import BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
        return BLUEPRINT_AUTHOR_AGENT_MD_CONTENT

    def test_has_rule_p1(self):
        content = self._get_content()
        assert "P1" in content or "Rule P1" in content
        assert "unit level" in content.lower()

    def test_has_rule_p2(self):
        content = self._get_content()
        assert "P2" in content or "Rule P2" in content
        assert "domain language" in content.lower() or "domain vocabulary" in content.lower()

    def test_has_rule_p3(self):
        content = self._get_content()
        assert "P3" in content or "Rule P3" in content
        assert "progressive disclosure" in content.lower() or "one open question" in content.lower()

    def test_has_rule_p4(self):
        content = self._get_content()
        assert "P4" in content or "Rule P4" in content
        assert "conflict" in content.lower()

    def test_mentions_preferences_subsection(self):
        content = self._get_content()
        assert "Preferences" in content

    def test_mentions_authority_hierarchy(self):
        content = self._get_content()
        lower = content.lower()
        assert "spec" in lower and "contracts" in lower and "preferences" in lower


# -------------------------------------------------------
# Test 2: Blueprint checker agent contains preference
#          consistency rule
# -------------------------------------------------------


class TestBlueprintCheckerPreferenceConsistency:
    """Verify blueprint checker includes preference-contract consistency."""

    def _get_content(self):
        try:
            from scripts.agent_definitions import BLUEPRINT_CHECKER_MD_CONTENT
        except ImportError:
            from src.unit_14.stub import BLUEPRINT_CHECKER_MD_CONTENT
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
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(blueprint_with_preferences, 1, include_tier1=True)
        assert "Preferences" in result
        assert "CSV format" in result
        assert "snake_case" in result

    def test_preferences_excluded_when_tier1_false(self, blueprint_with_preferences):
        from src.unit_5.stub import build_unit_context

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
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            blueprint_without_preferences, 1, include_tier1=True
        )
        assert "Preferences" not in result
        # Verify the normal content is still there
        assert "Widget Manager" in result
        assert "create_widget" in result
