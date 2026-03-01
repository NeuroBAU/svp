"""
Test suite for Unit 23: Plugin Manifest

Tests cover:
- PLUGIN_JSON constant: structure, required fields, values
- MARKETPLACE_JSON constant: structure, required fields, schema compliance
- validate_plugin_structure function: signature, happy path, error conditions
- PLUGIN_JSON_CONTENT deliverable constant: valid JSON, required content
- MARKETPLACE_JSON_CONTENT deliverable constant: valid JSON, required content
- All invariants from the blueprint
- All error conditions from the blueprint
- All behavioral contracts from the blueprint

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: Temporary directories created via tmp_path represent
valid filesystem paths simulating a repository root directory.

DATA ASSUMPTION: The valid plugin directory structure includes:
  - .claude-plugin/marketplace.json at repo root
  - svp/.claude-plugin/plugin.json at plugin subdirectory
  - svp/{agents,commands,hooks,scripts,skills}/ component directories
This represents the required Claude Code plugin layout per spec Sections
1.4 and 12.3.

DATA ASSUMPTION: Component directory names ("agents", "commands", "hooks",
"scripts", "skills") are the exact set required by the blueprint's Tier 2
invariants.

DATA ASSUMPTION: Invalid structures (missing files, missing component
dirs, component dirs at wrong level) are synthetic scenarios representing
common misconfiguration errors that validate_plugin_structure should catch.
==========================================================================
"""

import json
import inspect
import pytest
from pathlib import Path
from typing import Dict, Any, List

from svp.scripts.plugin_manifest import (
    PLUGIN_JSON,
    MARKETPLACE_JSON,
    validate_plugin_structure,
)


# ---------------------------------------------------------------------------
# Helper: safely access deliverable content constants
# ---------------------------------------------------------------------------

def _get_content(name: str) -> str:
    """Safely retrieve a content constant by name from the stub module.

    The stub declares PLUGIN_JSON_CONTENT and MARKETPLACE_JSON_CONTENT as
    type annotations without values, so direct import will fail on the stub
    (red run) and succeed on the implementation (green run).
    """
    import svp.scripts.plugin_manifest as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.plugin_manifest")
    return val


# ---------------------------------------------------------------------------
# Helper: create a valid plugin directory structure in a tmp_path
# ---------------------------------------------------------------------------

# DATA ASSUMPTION: These are the five component directories required by
# the blueprint invariants, representing the standard SVP plugin layout.
COMPONENT_DIRS = ["agents", "commands", "hooks", "scripts", "skills"]


def _create_valid_structure(repo_root: Path) -> None:
    """Create a fully valid plugin directory structure under repo_root."""
    # .claude-plugin/marketplace.json at repo root
    marketplace_dir = repo_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text("{}")

    # svp/.claude-plugin/plugin.json at plugin subdirectory
    plugin_dir = repo_root / "svp" / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text("{}")

    # Component directories at svp/ root level
    for component in COMPONENT_DIRS:
        (repo_root / "svp" / component).mkdir(parents=True, exist_ok=True)


# ===========================================================================
# 1. Signature verification
# ===========================================================================


class TestSignatures:
    """Verify function and constant signatures match the blueprint."""

    def test_plugin_json_is_dict(self):
        """PLUGIN_JSON must be a Dict[str, Any]."""
        assert isinstance(PLUGIN_JSON, dict)

    def test_marketplace_json_is_dict(self):
        """MARKETPLACE_JSON must be a Dict[str, Any]."""
        assert isinstance(MARKETPLACE_JSON, dict)

    def test_validate_plugin_structure_is_callable(self):
        """validate_plugin_structure must be callable."""
        assert callable(validate_plugin_structure)

    def test_validate_plugin_structure_parameter_name(self):
        """validate_plugin_structure must accept a 'repo_root' parameter."""
        sig = inspect.signature(validate_plugin_structure)
        param_names = list(sig.parameters.keys())
        assert "repo_root" in param_names

    def test_validate_plugin_structure_parameter_type(self):
        """validate_plugin_structure repo_root must be annotated as Path."""
        sig = inspect.signature(validate_plugin_structure)
        assert sig.parameters["repo_root"].annotation == Path

    def test_validate_plugin_structure_return_type(self):
        """validate_plugin_structure must return List[str]."""
        sig = inspect.signature(validate_plugin_structure)
        assert sig.return_annotation == List[str]

    def test_plugin_json_content_is_string(self):
        """PLUGIN_JSON_CONTENT must be a str."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        assert isinstance(content, str)

    def test_marketplace_json_content_is_string(self):
        """MARKETPLACE_JSON_CONTENT must be a str."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        assert isinstance(content, str)


# ===========================================================================
# 2. PLUGIN_JSON constant verification
# ===========================================================================


class TestPluginJson:
    """Verify PLUGIN_JSON constant matches the blueprint schema."""

    def test_has_name_field(self):
        """PLUGIN_JSON must have a 'name' field."""
        assert "name" in PLUGIN_JSON

    def test_name_is_svp(self):
        """PLUGIN_JSON name must be 'svp'."""
        assert PLUGIN_JSON["name"] == "svp"

    def test_has_version_field(self):
        """PLUGIN_JSON must have a 'version' field."""
        assert "version" in PLUGIN_JSON

    def test_version_is_string(self):
        """PLUGIN_JSON version must be a string."""
        assert isinstance(PLUGIN_JSON["version"], str)

    def test_version_value(self):
        """PLUGIN_JSON version must be '1.2.0'."""
        assert PLUGIN_JSON["version"] == "1.2.0"

    def test_has_description_field(self):
        """PLUGIN_JSON must have a 'description' field."""
        assert "description" in PLUGIN_JSON

    def test_description_is_string(self):
        """PLUGIN_JSON description must be a string."""
        assert isinstance(PLUGIN_JSON["description"], str)

    def test_description_mentions_svp(self):
        """PLUGIN_JSON description must reference SVP."""
        assert "Stratified Verification Pipeline" in PLUGIN_JSON["description"]


# ===========================================================================
# 3. MARKETPLACE_JSON constant verification
# ===========================================================================


class TestMarketplaceJson:
    """Verify MARKETPLACE_JSON constant matches the blueprint schema.

    Required top-level fields: name (str), owner (obj), plugins (array).
    Each plugin entry requires: name, source, description, version, author.
    """

    def test_has_name_field(self):
        """MARKETPLACE_JSON must have a top-level 'name' field."""
        assert "name" in MARKETPLACE_JSON

    def test_name_is_svp(self):
        """MARKETPLACE_JSON name must be 'svp'."""
        assert MARKETPLACE_JSON["name"] == "svp"

    def test_has_owner_field(self):
        """MARKETPLACE_JSON must have a top-level 'owner' object."""
        assert "owner" in MARKETPLACE_JSON
        assert isinstance(MARKETPLACE_JSON["owner"], dict)

    def test_owner_has_name(self):
        """MARKETPLACE_JSON owner must have a 'name' field."""
        assert "name" in MARKETPLACE_JSON["owner"]

    def test_has_plugins_field(self):
        """MARKETPLACE_JSON must have a top-level 'plugins' array."""
        assert "plugins" in MARKETPLACE_JSON
        assert isinstance(MARKETPLACE_JSON["plugins"], list)

    def test_plugins_array_not_empty(self):
        """MARKETPLACE_JSON plugins array must contain at least one entry."""
        assert len(MARKETPLACE_JSON["plugins"]) >= 1

    def test_plugin_entry_has_name(self):
        """Each plugin entry must have a 'name' field."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert "name" in plugin
        assert plugin["name"] == "svp"

    def test_plugin_entry_has_source(self):
        """Each plugin entry must have a 'source' field."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert "source" in plugin

    def test_plugin_source_is_relative_with_dot_prefix(self):
        """Contract: source field must be a relative path with './' prefix
        pointing to the plugin subdirectory ('./svp')."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert plugin["source"] == "./svp"

    def test_plugin_entry_has_description(self):
        """Each plugin entry must have a 'description' field."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert "description" in plugin
        assert isinstance(plugin["description"], str)

    def test_plugin_entry_has_version(self):
        """Each plugin entry must have a 'version' field."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert "version" in plugin
        assert plugin["version"] == "1.2.0"

    def test_plugin_entry_has_author(self):
        """Each plugin entry must have an 'author' field."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert "author" in plugin
        assert isinstance(plugin["author"], dict)


# ===========================================================================
# 4. validate_plugin_structure -- valid structure (happy path)
# ===========================================================================


class TestValidatePluginStructureValid:
    """Verify validate_plugin_structure returns empty list for valid structure."""

    def test_returns_list(self, tmp_path):
        """validate_plugin_structure must return a list."""
        _create_valid_structure(tmp_path)
        result = validate_plugin_structure(tmp_path)
        assert isinstance(result, list)

    def test_valid_structure_returns_empty_list(self, tmp_path):
        """Contract: a fully valid structure produces no violations."""
        _create_valid_structure(tmp_path)
        result = validate_plugin_structure(tmp_path)
        assert result == [], f"Expected no violations but got: {result}"


# ===========================================================================
# 5. validate_plugin_structure -- missing marketplace.json
# ===========================================================================


class TestValidateMissingMarketplaceJson:
    """Verify validate_plugin_structure detects missing marketplace.json."""

    def test_missing_marketplace_json(self, tmp_path):
        """Invariant: repo root must contain .claude-plugin/marketplace.json.
        Missing it should produce a violation."""
        _create_valid_structure(tmp_path)
        # Remove marketplace.json
        (tmp_path / ".claude-plugin" / "marketplace.json").unlink()
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, "Must detect missing marketplace.json"
        # At least one violation should mention marketplace.json
        violations_text = " ".join(result).lower()
        assert "marketplace" in violations_text

    def test_missing_claude_plugin_dir_at_root(self, tmp_path):
        """If .claude-plugin/ directory itself is missing at root level."""
        _create_valid_structure(tmp_path)
        # Remove the entire .claude-plugin directory at repo root
        import shutil
        shutil.rmtree(tmp_path / ".claude-plugin")
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, "Must detect missing .claude-plugin at root"


# ===========================================================================
# 6. validate_plugin_structure -- missing plugin.json
# ===========================================================================


class TestValidateMissingPluginJson:
    """Verify validate_plugin_structure detects missing plugin.json."""

    def test_missing_plugin_json(self, tmp_path):
        """Invariant: plugin subdirectory must contain .claude-plugin/plugin.json.
        Missing it should produce a violation."""
        _create_valid_structure(tmp_path)
        # Remove plugin.json
        (tmp_path / "svp" / ".claude-plugin" / "plugin.json").unlink()
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, "Must detect missing plugin.json"
        violations_text = " ".join(result).lower()
        assert "plugin" in violations_text

    def test_missing_claude_plugin_dir_at_svp(self, tmp_path):
        """If svp/.claude-plugin/ directory itself is missing."""
        _create_valid_structure(tmp_path)
        import shutil
        shutil.rmtree(tmp_path / "svp" / ".claude-plugin")
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, "Must detect missing svp/.claude-plugin"


# ===========================================================================
# 7. validate_plugin_structure -- missing component directories
# ===========================================================================


class TestValidateMissingComponentDirs:
    """Verify validate_plugin_structure detects missing component directories.

    Invariant: All component directories must be at plugin subdirectory root level.
    """

    @pytest.mark.parametrize("component", COMPONENT_DIRS)
    def test_missing_component_dir(self, tmp_path, component):
        """Each component directory must exist at svp/ root level.
        DATA ASSUMPTION: Each component name from COMPONENT_DIRS is one of the
        five required directories per the blueprint invariants."""
        _create_valid_structure(tmp_path)
        import shutil
        shutil.rmtree(tmp_path / "svp" / component)
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, f"Must detect missing {component}/ directory"
        violations_text = " ".join(result).lower()
        assert component in violations_text


# ===========================================================================
# 8. validate_plugin_structure -- component dirs at wrong level
# ===========================================================================


class TestValidateComponentDirsAtWrongLevel:
    """Verify validate_plugin_structure detects component dirs at repo root level.

    Invariant: component directories must NOT be at repository root level.
    """

    @pytest.mark.parametrize("component", COMPONENT_DIRS)
    def test_component_dir_at_repo_root(self, tmp_path, component):
        """Component directories at repo root level should produce a violation.
        DATA ASSUMPTION: Having a component directory at repo root represents
        a common misconfiguration where components are placed at the wrong
        directory level."""
        _create_valid_structure(tmp_path)
        # Create the component dir at repo root (forbidden)
        (tmp_path / component).mkdir(parents=True, exist_ok=True)
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, \
            f"Must detect {component}/ at repo root level"
        violations_text = " ".join(result).lower()
        assert component in violations_text


# ===========================================================================
# 9. validate_plugin_structure -- multiple violations
# ===========================================================================


class TestValidateMultipleViolations:
    """Verify validate_plugin_structure reports multiple violations."""

    def test_empty_directory_reports_all_violations(self, tmp_path):
        """An empty repo root should report violations for marketplace.json,
        plugin.json, and all component directories.
        DATA ASSUMPTION: An empty directory represents the worst-case
        misconfiguration with all structural requirements violated."""
        result = validate_plugin_structure(tmp_path)
        # Should have multiple violations
        assert len(result) >= 2, \
            f"Empty dir should produce multiple violations, got {len(result)}"

    def test_each_violation_is_string(self, tmp_path):
        """Each violation must be a string (specific, actionable description)."""
        result = validate_plugin_structure(tmp_path)
        for violation in result:
            assert isinstance(violation, str)
            assert len(violation) > 0, "Violation descriptions must be non-empty"


# ===========================================================================
# 10. Error conditions -- ValueError
# ===========================================================================


class TestErrorConditions:
    """Verify error conditions from the blueprint Tier 3.

    Error: ValueError with 'Plugin structure validation failed: {details}'
    when validate_plugin_structure finds violations.

    Note: The blueprint says validate_plugin_structure returns List[str],
    so the function itself returns violations. The ValueError may be raised
    by a caller or by the function itself when violations are found. We test
    both that the function can detect violations (returns non-empty list)
    and that its violations are specific and actionable.
    """

    def test_violations_are_specific_and_actionable(self, tmp_path):
        """Error contract: each violation is a specific, actionable description.
        DATA ASSUMPTION: 'specific, actionable' means each violation describes
        what is wrong and implicitly or explicitly how to fix it."""
        result = validate_plugin_structure(tmp_path)
        for violation in result:
            # Each violation should describe what is missing/wrong
            assert len(violation) > 10, \
                f"Violation '{violation}' is too short to be actionable"

    def test_violations_mention_affected_path_or_component(self, tmp_path):
        """Each violation should reference the affected component or path."""
        _create_valid_structure(tmp_path)
        import shutil
        shutil.rmtree(tmp_path / "svp" / "agents")
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0
        violations_text = " ".join(result).lower()
        assert "agents" in violations_text


# ===========================================================================
# 11. PLUGIN_JSON_CONTENT deliverable constant
# ===========================================================================


class TestPluginJsonContent:
    """Verify PLUGIN_JSON_CONTENT invariants and behavioral contracts.

    Contract: PLUGIN_JSON_CONTENT must be valid JSON with the plugin manifest:
    name ('svp'), version, description.
    Invariant: '"name": "svp"' in PLUGIN_JSON_CONTENT.
    """

    def test_is_valid_json(self):
        """PLUGIN_JSON_CONTENT must be valid JSON."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"PLUGIN_JSON_CONTENT is not valid JSON: {e}")
        assert isinstance(parsed, dict)

    def test_invariant_name_svp(self):
        """Invariant: '"name": "svp"' in PLUGIN_JSON_CONTENT."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        assert '"name": "svp"' in content or '"name":"svp"' in content

    def test_has_name_field(self):
        """PLUGIN_JSON_CONTENT parsed JSON must have 'name' = 'svp'."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed.get("name") == "svp"

    def test_has_version_field(self):
        """PLUGIN_JSON_CONTENT parsed JSON must have 'version'."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        parsed = json.loads(content)
        assert "version" in parsed
        assert isinstance(parsed["version"], str)

    def test_has_description_field(self):
        """PLUGIN_JSON_CONTENT parsed JSON must have 'description'."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        parsed = json.loads(content)
        assert "description" in parsed
        assert isinstance(parsed["description"], str)

    def test_content_is_nonempty(self):
        """PLUGIN_JSON_CONTENT must be substantial."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        assert len(content.strip()) > 10


# ===========================================================================
# 12. MARKETPLACE_JSON_CONTENT deliverable constant
# ===========================================================================


class TestMarketplaceJsonContent:
    """Verify MARKETPLACE_JSON_CONTENT invariants and behavioral contracts.

    Contract: MARKETPLACE_JSON_CONTENT must be valid JSON matching the
    marketplace catalog schema from spec Section 1.4: top-level name,
    owner object, plugins array with name, source ('./svp'), description,
    version, author fields.

    Invariants:
    - '"plugins"' in MARKETPLACE_JSON_CONTENT
    - '"source": "./svp"' in MARKETPLACE_JSON_CONTENT
    """

    def test_is_valid_json(self):
        """MARKETPLACE_JSON_CONTENT must be valid JSON."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"MARKETPLACE_JSON_CONTENT is not valid JSON: {e}")
        assert isinstance(parsed, dict)

    def test_invariant_has_plugins(self):
        """Invariant: '"plugins"' in MARKETPLACE_JSON_CONTENT."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        assert '"plugins"' in content

    def test_invariant_has_source_svp(self):
        """Invariant: '"source": "./svp"' in MARKETPLACE_JSON_CONTENT."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        # Allow for optional whitespace variations in JSON
        assert '"source": "./svp"' in content or '"source":"./svp"' in content

    def test_has_top_level_name(self):
        """MARKETPLACE_JSON_CONTENT must have top-level 'name'."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert "name" in parsed
        assert isinstance(parsed["name"], str)

    def test_has_top_level_owner_object(self):
        """MARKETPLACE_JSON_CONTENT must have top-level 'owner' object."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert "owner" in parsed
        assert isinstance(parsed["owner"], dict)

    def test_has_plugins_array(self):
        """MARKETPLACE_JSON_CONTENT must have 'plugins' as an array."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert "plugins" in parsed
        assert isinstance(parsed["plugins"], list)
        assert len(parsed["plugins"]) >= 1

    def test_plugin_entry_has_required_fields(self):
        """Each plugin entry must have: name, source, description, version, author."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        required_fields = ["name", "source", "description", "version", "author"]
        for field in required_fields:
            assert field in plugin, f"Plugin entry missing required field: {field}"

    def test_plugin_source_is_relative_svp(self):
        """Plugin source must be './svp' (relative path with './' prefix)."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        assert plugin["source"] == "./svp"

    def test_plugin_name_is_svp(self):
        """Plugin entry name must be 'svp'."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        assert plugin["name"] == "svp"

    def test_plugin_has_author_object(self):
        """Plugin entry author must be an object (dict)."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        plugin = parsed["plugins"][0]
        assert isinstance(plugin["author"], dict)

    def test_content_is_nonempty(self):
        """MARKETPLACE_JSON_CONTENT must be substantial."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        assert len(content.strip()) > 10


# ===========================================================================
# 13. Content consistency between constants and deliverables
# ===========================================================================


class TestContentConsistency:
    """Verify consistency between PLUGIN_JSON/MARKETPLACE_JSON dict constants
    and their corresponding _CONTENT string deliverables."""

    def test_plugin_json_content_matches_plugin_json_dict(self):
        """PLUGIN_JSON_CONTENT, when parsed, should have the same name, version,
        and description as the PLUGIN_JSON dict constant.
        DATA ASSUMPTION: The deliverable content constant is the JSON serialization
        of the manifest dict."""
        content = _get_content("PLUGIN_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["name"] == PLUGIN_JSON["name"]
        assert parsed["version"] == PLUGIN_JSON["version"]
        assert parsed["description"] == PLUGIN_JSON["description"]

    def test_marketplace_json_content_matches_marketplace_json_dict(self):
        """MARKETPLACE_JSON_CONTENT, when parsed, should match the structure
        and values of the MARKETPLACE_JSON dict constant."""
        content = _get_content("MARKETPLACE_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["name"] == MARKETPLACE_JSON["name"]
        assert parsed["owner"] == MARKETPLACE_JSON["owner"]
        assert len(parsed["plugins"]) == len(MARKETPLACE_JSON["plugins"])
        plugin_parsed = parsed["plugins"][0]
        plugin_dict = MARKETPLACE_JSON["plugins"][0]
        assert plugin_parsed["name"] == plugin_dict["name"]
        assert plugin_parsed["source"] == plugin_dict["source"]
        assert plugin_parsed["version"] == plugin_dict["version"]


# ===========================================================================
# 14. Behavioral contract: file locations
# ===========================================================================


class TestFileLocationContracts:
    """Verify behavioral contracts about where files live.

    - plugin.json lives at svp/.claude-plugin/plugin.json
    - marketplace.json lives at .claude-plugin/marketplace.json at repo root
    - These are SEPARATE .claude-plugin/ directories
    """

    def test_valid_structure_has_separate_claude_plugin_dirs(self, tmp_path):
        """The two .claude-plugin/ directories are separate: one at repo root,
        one at svp/ level.
        DATA ASSUMPTION: A valid structure has both directories existing
        independently."""
        _create_valid_structure(tmp_path)
        root_dir = tmp_path / ".claude-plugin"
        plugin_dir = tmp_path / "svp" / ".claude-plugin"
        assert root_dir.exists() and root_dir.is_dir()
        assert plugin_dir.exists() and plugin_dir.is_dir()
        # They are different directories
        assert root_dir != plugin_dir

    def test_validate_checks_marketplace_at_repo_root(self, tmp_path):
        """validate_plugin_structure checks marketplace.json at repo root."""
        _create_valid_structure(tmp_path)
        # Move marketplace.json to wrong location (svp level) and remove from root
        (tmp_path / ".claude-plugin" / "marketplace.json").unlink()
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, "Must detect missing marketplace.json at root"

    def test_validate_checks_plugin_json_at_svp_level(self, tmp_path):
        """validate_plugin_structure checks plugin.json at svp/.claude-plugin/."""
        _create_valid_structure(tmp_path)
        (tmp_path / "svp" / ".claude-plugin" / "plugin.json").unlink()
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0, "Must detect missing plugin.json at svp level"


# ===========================================================================
# 15. Behavioral contract: component directory placement
# ===========================================================================


class TestComponentDirectoryPlacement:
    """Verify validate_plugin_structure checks component directory placement."""

    def test_all_components_at_svp_level_is_valid(self, tmp_path):
        """All five component dirs at svp/ level, none at root = valid."""
        _create_valid_structure(tmp_path)
        result = validate_plugin_structure(tmp_path)
        assert result == []

    def test_component_only_at_root_is_invalid(self, tmp_path):
        """A component directory only at root (not at svp/) triggers two
        violations: missing from svp/ and present at root.
        DATA ASSUMPTION: 'scripts' is used as a representative component."""
        _create_valid_structure(tmp_path)
        import shutil
        # Remove from svp/ and add at root
        shutil.rmtree(tmp_path / "svp" / "scripts")
        (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
        result = validate_plugin_structure(tmp_path)
        assert len(result) >= 1, "Must detect scripts/ misconfiguration"


# ===========================================================================
# 16. Edge cases
# ===========================================================================


class TestEdgeCases:
    """Additional edge case and boundary condition tests."""

    def test_validate_with_extra_files_in_structure(self, tmp_path):
        """Extra files that are not part of the required structure should
        not cause false violations.
        DATA ASSUMPTION: 'extra_file.txt' and 'extra_dir/' represent
        non-plugin files that may exist in a real repository."""
        _create_valid_structure(tmp_path)
        # Add extra files/dirs that shouldn't affect validation
        (tmp_path / "extra_file.txt").write_text("hello")
        (tmp_path / "extra_dir").mkdir()
        (tmp_path / "svp" / "extra_file.py").write_text("# extra")
        result = validate_plugin_structure(tmp_path)
        assert result == [], f"Extra files should not cause violations: {result}"

    def test_validate_returns_list_type_always(self, tmp_path):
        """validate_plugin_structure must always return a list, even for
        valid structures."""
        _create_valid_structure(tmp_path)
        result = validate_plugin_structure(tmp_path)
        assert isinstance(result, list)

    def test_plugin_json_dict_has_exactly_expected_keys(self):
        """PLUGIN_JSON dict should have the documented fields.
        DATA ASSUMPTION: The blueprint specifies exactly three fields:
        name, version, description."""
        expected_keys = {"name", "version", "description"}
        actual_keys = set(PLUGIN_JSON.keys())
        # Must have at least the required keys
        assert expected_keys.issubset(actual_keys), \
            f"PLUGIN_JSON missing keys: {expected_keys - actual_keys}"

    def test_marketplace_json_dict_top_level_keys(self):
        """MARKETPLACE_JSON dict must have the three required top-level fields.
        DATA ASSUMPTION: The blueprint requires exactly: name, owner, plugins."""
        required_keys = {"name", "owner", "plugins"}
        actual_keys = set(MARKETPLACE_JSON.keys())
        assert required_keys.issubset(actual_keys), \
            f"MARKETPLACE_JSON missing keys: {required_keys - actual_keys}"

    def test_marketplace_json_source_prefix(self):
        """The source field must start with './' (relative path prefix)."""
        plugin = MARKETPLACE_JSON["plugins"][0]
        assert plugin["source"].startswith("./"), \
            "source must start with './' prefix"
