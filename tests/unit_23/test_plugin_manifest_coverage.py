"""
Coverage gap tests for Unit 23: Plugin Manifest

These tests cover behavioral contracts and invariants from the blueprint
that are not exercised by the existing test_plugin_manifest.py suite.

Gaps identified:
1. MARKETPLACE_JSON owner.name value -- blueprint specifies {"name": "SVP"}
   but existing tests only check that "name" key exists, not its value.
2. MARKETPLACE_JSON plugin entry author.name value -- blueprint specifies
   {"name": "SVP"} but existing tests only check author is a dict.
3. MARKETPLACE_JSON_CONTENT owner and author name values -- the content
   deliverable should carry the same owner/author values as the dict.
4. MARKETPLACE_JSON_CONTENT top-level name value -- existing tests check
   it is a string but not that it equals "svp".
5. Content consistency for description field in marketplace -- existing
   consistency test checks name/source/version but not description/author.
6. validate_plugin_structure: empty directory violation count -- blueprint
   specifies checks for marketplace.json, plugin.json, and all 5 component
   dirs = at least 7 violations for a completely empty directory.
7. PLUGIN_JSON_CONTENT version value -- existing test checks version is a
   string but not that it equals "1.2.0".
8. MARKETPLACE_JSON_CONTENT plugin entry version value -- existing test
   checks required fields exist but not that version equals "1.2.0".
9. MARKETPLACE_JSON name field is a string -- blueprint specifies name (str)
   at top level of MARKETPLACE_JSON; existing tests check value but not type.
10. MARKETPLACE_JSON owner.name is a string -- blueprint specifies owner is
    an object with name field; value and type not checked.

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: The blueprint specifies exact values for MARKETPLACE_JSON
fields: owner is {"name": "SVP"}, author is {"name": "SVP"}, top-level
name is "svp". These are the authoritative expected values.

DATA ASSUMPTION: An empty directory has zero structural elements, so
validate_plugin_structure should report at least 7 violations: 1 for
missing marketplace.json, 1 for missing plugin.json, and 5 for missing
component directories.

DATA ASSUMPTION: PLUGIN_JSON_CONTENT version "1.2.0" and
MARKETPLACE_JSON_CONTENT version "1.2.0" match the blueprint's specified
schema values.
==========================================================================
"""

import json
import pytest

from svp.scripts.plugin_manifest import (
    PLUGIN_JSON,
    MARKETPLACE_JSON,
    validate_plugin_structure,
)


# ---------------------------------------------------------------------------
# Helper: safely access deliverable content constants
# ---------------------------------------------------------------------------

def _get_content(name: str) -> str:
    """Safely retrieve a content constant by name from the stub module."""
    import svp.scripts.plugin_manifest as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.plugin_manifest")
    return val


COMPONENT_DIRS = ["agents", "commands", "hooks", "scripts", "skills"]


def _create_valid_structure(repo_root):
    """Create a fully valid plugin directory structure under repo_root."""
    from pathlib import Path
    marketplace_dir = repo_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text("{}")
    plugin_dir = repo_root / "svp" / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text("{}")
    for component in COMPONENT_DIRS:
        (repo_root / "svp" / component).mkdir(parents=True, exist_ok=True)


# ===========================================================================
# Gap 1: MARKETPLACE_JSON owner.name value
# ===========================================================================


class TestMarketplaceJsonOwnerValue:
    """Verify MARKETPLACE_JSON owner object has the correct name value.

    Blueprint specifies: "owner": {"name": "SVP"}
    Existing tests check owner has a "name" key but not its value.
    """

    def test_owner_name_value_is_svp(self):
        """MARKETPLACE_JSON owner.name must be 'SVP' per blueprint schema."""
        assert MARKETPLACE_JSON["owner"]["name"] == "SVP"

    def test_owner_name_is_string(self):
        """MARKETPLACE_JSON owner.name must be a string."""
        assert isinstance(MARKETPLACE_JSON["owner"]["name"], str)


# ===========================================================================
# Gap 2: MARKETPLACE_JSON plugin entry author.name value
# ===========================================================================


class TestMarketplaceJsonAuthorValue:
    """Verify MARKETPLACE_JSON plugin entry author has the correct name value.

    Blueprint specifies: "author": {"name": "SVP"}
    Existing tests check author is a dict but not its contents.
    """

    def test_plugin_author_has_name_field(self):
        """MARKETPLACE_JSON plugin author must have a 'name' field."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert "name" in plugin["author"]

    def test_plugin_author_name_value_is_svp(self):
        """MARKETPLACE_JSON plugin author.name must be 'SVP' per blueprint."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert plugin["author"]["name"] == "SVP"


# ===========================================================================
# Gap 3: MARKETPLACE_JSON_CONTENT owner and author name values
# ===========================================================================


class TestMarketplaceJsonContentOwnerAuthor:
    """Verify MARKETPLACE_JSON_CONTENT parsed JSON has correct owner and
    author name values matching the blueprint schema."""

    def test_content_owner_has_name_field(self):
        """MARKETPLACE_JSON_CONTENT owner must have a 'name' field."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert "name" in parsed["owner"]

    def test_content_owner_name_value(self):
        """MARKETPLACE_JSON_CONTENT owner.name must be 'SVP'."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["owner"]["name"] == "SVP"

    def test_content_plugin_author_has_name_field(self):
        """MARKETPLACE_JSON_CONTENT plugin author must have a 'name' field."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        assert "name" in plugin["author"]

    def test_content_plugin_author_name_value(self):
        """MARKETPLACE_JSON_CONTENT plugin author.name must be 'SVP'."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        assert plugin["author"]["name"] == "SVP"


# ===========================================================================
# Gap 4: MARKETPLACE_JSON_CONTENT top-level name value
# ===========================================================================


class TestMarketplaceJsonContentNameValue:
    """Verify MARKETPLACE_JSON_CONTENT top-level name is 'svp'.

    Existing tests check name is a string but not its exact value.
    """

    def test_content_top_level_name_is_svp(self):
        """MARKETPLACE_JSON_CONTENT top-level name must be 'svp'."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["name"] == "svp"


# ===========================================================================
# Gap 5: Content consistency -- description and author fields
# ===========================================================================


class TestContentConsistencyExtended:
    """Verify consistency between MARKETPLACE_JSON dict and
    MARKETPLACE_JSON_CONTENT for description and author fields.

    Existing consistency tests check name/source/version but not
    description or author.
    """

    def test_marketplace_content_description_matches_dict(self):
        """MARKETPLACE_JSON_CONTENT plugin description must match
        MARKETPLACE_JSON dict plugin description.
        DATA ASSUMPTION: The deliverable content is the JSON serialization
        of the dict constant, so all fields should match."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin_parsed = parsed["plugins"][0]
        plugin_dict = MARKETPLACE_JSON["plugins"][0]
        assert plugin_parsed["description"] == plugin_dict["description"]

    def test_marketplace_content_author_matches_dict(self):
        """MARKETPLACE_JSON_CONTENT plugin author must match
        MARKETPLACE_JSON dict plugin author."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin_parsed = parsed["plugins"][0]
        plugin_dict = MARKETPLACE_JSON["plugins"][0]
        assert plugin_parsed["author"] == plugin_dict["author"]


# ===========================================================================
# Gap 6: validate_plugin_structure empty dir violation count
# ===========================================================================


class TestValidateEmptyDirViolationCount:
    """Verify validate_plugin_structure reports the expected number of
    violations for a completely empty directory.

    Blueprint invariants require checks for:
    - marketplace.json at repo root (1 violation)
    - plugin.json at plugin subdirectory (1 violation)
    - 5 component directories at svp/ level (5 violations)
    Total: at least 7 violations for an empty directory.

    DATA ASSUMPTION: An empty directory violates all 7 structural
    requirements (marketplace.json, plugin.json, agents/, commands/,
    hooks/, scripts/, skills/).
    """

    def test_empty_dir_reports_at_least_seven_violations(self, tmp_path):
        """An empty directory should produce at least 7 violations:
        1 marketplace.json + 1 plugin.json + 5 component dirs."""
        result = validate_plugin_structure(tmp_path)
        assert len(result) >= 7, \
            f"Expected at least 7 violations for empty dir, got {len(result)}: {result}"

    def test_empty_dir_violations_cover_all_components(self, tmp_path):
        """Violations for an empty directory should mention each of the
        five component directories."""
        result = validate_plugin_structure(tmp_path)
        violations_text = " ".join(result).lower()
        for component in COMPONENT_DIRS:
            assert component in violations_text, \
                f"Missing violation for component: {component}"

    def test_empty_dir_violations_mention_marketplace(self, tmp_path):
        """Violations for an empty directory should mention marketplace.json."""
        result = validate_plugin_structure(tmp_path)
        violations_text = " ".join(result).lower()
        assert "marketplace" in violations_text

    def test_empty_dir_violations_mention_plugin_json(self, tmp_path):
        """Violations for an empty directory should mention plugin.json."""
        result = validate_plugin_structure(tmp_path)
        violations_text = " ".join(result).lower()
        assert "plugin" in violations_text


# ===========================================================================
# Gap 7: PLUGIN_JSON_CONTENT version value
# ===========================================================================


class TestPluginJsonContentVersionValue:
    """Verify PLUGIN_JSON_CONTENT version field has the correct value.

    Existing tests check version is a string but not its exact value.
    Blueprint specifies version '1.2.0'.
    """

    def test_plugin_json_content_version_is_1_2_0(self):
        """PLUGIN_JSON_CONTENT version must be '1.2.0'."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["version"] == "1.2.0"


# ===========================================================================
# Gap 8: MARKETPLACE_JSON_CONTENT plugin entry version value
# ===========================================================================


class TestMarketplaceJsonContentVersionValue:
    """Verify MARKETPLACE_JSON_CONTENT plugin entry version has the correct
    value.

    Blueprint specifies version '1.2.0' in the plugin entry.
    Existing tests check the field exists but not its exact value in the
    content string deliverable.
    """

    def test_marketplace_content_plugin_version_is_1_2_0(self):
        """MARKETPLACE_JSON_CONTENT plugin version must be '1.2.0'."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        assert plugin["version"] == "1.2.0"


# ===========================================================================
# Gap 9: MARKETPLACE_JSON name field type
# ===========================================================================


class TestMarketplaceJsonNameType:
    """Verify MARKETPLACE_JSON top-level name is a string.

    Blueprint specifies: Required top-level fields: name (str).
    Existing tests check the value is 'svp' (which implies string) but
    do not explicitly verify the type.
    """

    def test_marketplace_json_name_is_string(self):
        """MARKETPLACE_JSON top-level name must be a string type."""
        assert isinstance(MARKETPLACE_JSON["name"], str)


# ===========================================================================
# Gap 10: Component dir at root AND at svp/ produces violation
# ===========================================================================


class TestComponentDirAtBothLevels:
    """Verify that having a component directory at both svp/ and repo root
    produces a violation for the root-level copy.

    Invariant: component directories must NOT be at repository root level,
    even if they also exist at the correct svp/ level. This is tested
    parametrically in the existing suite, but only one component at a time.
    This test verifies the scenario where ALL components exist at both
    levels simultaneously.

    DATA ASSUMPTION: Having all five component directories duplicated at
    repo root level while they also exist at svp/ level represents a
    deployment error where directories were copied to the wrong level.
    """

    def test_all_components_at_both_levels_reports_five_violations(self, tmp_path):
        """When all components exist at both svp/ and repo root, there
        should be exactly 5 root-level violations (one per component)."""
        _create_valid_structure(tmp_path)
        for component in COMPONENT_DIRS:
            (tmp_path / component).mkdir(parents=True, exist_ok=True)
        result = validate_plugin_structure(tmp_path)
        assert len(result) == 5, \
            f"Expected 5 violations for root-level components, got {len(result)}: {result}"
        violations_text = " ".join(result).lower()
        for component in COMPONENT_DIRS:
            assert component in violations_text
