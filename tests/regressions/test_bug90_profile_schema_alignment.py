"""Regression test for Bug 90: Setup agent output schema misaligned with
DEFAULT_PROFILE (packaging vs delivery+license sections) and missing
conditional follow-up questions for GitHub URL and existing README path.

Bug A: The setup agent writes a consolidated 'packaging' section instead of
the separate 'delivery' and 'license' sections expected by DEFAULT_PROFILE.
When load_profile() deep-merges the file profile with DEFAULT_PROFILE, the
'delivery' and 'license' sections retain their defaults (MIT, conventional
layout) while the 'packaging' data is orphaned.

Bug B: When the human selects GitHub mode 'existing_branch' or 'existing_force',
the agent must ask for the repo URL. When the human selects README mode
'update', the agent must ask for the existing README path. Missing follow-ups
leave null values that break Stage 5 delivery.

Fix: Added explicit JSON templates for 'license' and 'delivery' sections to
the setup agent definition (Area 4). Added MANDATORY FOLLOW-UP instructions
for GitHub URL and README path. Added validate_profile() checks for orphaned
'packaging' section and missing repo_url with non-none GitHub modes.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable
_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root / "svp" / "scripts"))

from svp_config import DEFAULT_PROFILE, validate_profile, load_profile, _deep_merge


class TestDefaultProfileHasNoPackagingSection:
    """DEFAULT_PROFILE must use 'delivery' and 'license', not 'packaging'."""

    def test_no_packaging_key_in_default_profile(self):
        assert "packaging" not in DEFAULT_PROFILE, (
            "DEFAULT_PROFILE must not contain a 'packaging' key. "
            "Use 'delivery' and 'license' sections instead."
        )

    def test_delivery_section_exists(self):
        assert "delivery" in DEFAULT_PROFILE
        assert isinstance(DEFAULT_PROFILE["delivery"], dict)

    def test_license_section_exists(self):
        assert "license" in DEFAULT_PROFILE
        assert isinstance(DEFAULT_PROFILE["license"], dict)

    def test_delivery_has_required_keys(self):
        delivery = DEFAULT_PROFILE["delivery"]
        required = {"environment_recommendation", "dependency_format",
                     "source_layout", "entry_points"}
        assert required.issubset(delivery.keys()), (
            f"delivery section missing keys: {required - delivery.keys()}"
        )

    def test_license_has_required_keys(self):
        license_section = DEFAULT_PROFILE["license"]
        required = {"type", "holder", "author", "year", "spdx_headers"}
        assert required.issubset(license_section.keys()), (
            f"license section missing keys: {required - license_section.keys()}"
        )


class TestValidateProfileRejectsPackagingSection:
    """validate_profile() must flag orphaned 'packaging' section."""

    def _base_profile(self):
        """Return a minimal valid profile."""
        return _deep_merge(DEFAULT_PROFILE, {})

    def test_valid_profile_no_errors(self):
        profile = self._base_profile()
        errors = validate_profile(profile)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_packaging_section_produces_error(self):
        profile = self._base_profile()
        profile["packaging"] = {
            "license": "Apache-2.0",
            "environment": "conda",
            "source_layout": "flat",
        }
        errors = validate_profile(profile)
        packaging_errors = [e for e in errors if "packaging" in e.lower()]
        assert len(packaging_errors) >= 1, (
            "validate_profile() must flag a 'packaging' section as invalid"
        )


class TestValidateProfileGitHubUrlRequired:
    """validate_profile() must flag missing repo_url for non-none GitHub modes."""

    def _base_profile(self):
        return _deep_merge(DEFAULT_PROFILE, {})

    @pytest.mark.parametrize("mode", ["existing_force", "existing_branch", "new"])
    def test_github_mode_without_url_produces_error(self, mode):
        profile = self._base_profile()
        profile["vcs"]["github"] = {
            "mode": mode,
            "repo_url": None,
            "branch": "main",
        }
        errors = validate_profile(profile)
        url_errors = [e for e in errors if "repo_url" in e]
        assert len(url_errors) >= 1, (
            f"validate_profile() must flag missing repo_url for mode '{mode}'"
        )

    def test_github_mode_none_no_url_error(self):
        profile = self._base_profile()
        profile["vcs"]["github"] = {
            "mode": "none",
            "repo_url": None,
            "branch": "main",
        }
        errors = validate_profile(profile)
        url_errors = [e for e in errors if "repo_url" in e]
        assert len(url_errors) == 0, (
            "validate_profile() should not flag missing repo_url for mode 'none'"
        )

    def test_github_mode_existing_with_url_no_error(self):
        profile = self._base_profile()
        profile["vcs"]["github"] = {
            "mode": "existing_branch",
            "repo_url": "https://github.com/user/repo.git",
            "branch": "svp-delivery",
        }
        errors = validate_profile(profile)
        url_errors = [e for e in errors if "repo_url" in e]
        assert len(url_errors) == 0


class TestDeepMergePreservesCorrectSections:
    """When a properly structured profile is merged, delivery and license
    sections reflect the file values, not the defaults."""

    def test_delivery_values_override_defaults(self):
        file_profile = {
            "delivery": {
                "environment_recommendation": "venv",
                "source_layout": "flat",
                "entry_points": True,
            }
        }
        merged = _deep_merge(DEFAULT_PROFILE, file_profile)
        assert merged["delivery"]["environment_recommendation"] == "venv"
        assert merged["delivery"]["source_layout"] == "flat"
        assert merged["delivery"]["entry_points"] is True

    def test_license_values_override_defaults(self):
        file_profile = {
            "license": {
                "type": "Apache-2.0",
                "holder": "Test Corp",
                "spdx_headers": True,
            }
        }
        merged = _deep_merge(DEFAULT_PROFILE, file_profile)
        assert merged["license"]["type"] == "Apache-2.0"
        assert merged["license"]["holder"] == "Test Corp"
        assert merged["license"]["spdx_headers"] is True

    def test_packaging_section_does_not_populate_delivery_or_license(self):
        """A profile with only 'packaging' must NOT override delivery or license."""
        file_profile = {
            "packaging": {
                "license": "Apache-2.0",
                "environment": "conda",
                "source_layout": "flat",
            }
        }
        merged = _deep_merge(DEFAULT_PROFILE, file_profile)
        # delivery and license should still have defaults
        assert merged["delivery"]["source_layout"] == "conventional"
        assert merged["license"]["type"] == "MIT"
        # packaging should be present but orphaned
        assert "packaging" in merged


class TestSetupAgentDefinitionHasSchemaTemplates:
    """The setup agent definition must contain explicit JSON templates
    for 'license' and 'delivery' sections to prevent schema drift."""

    @pytest.fixture
    def agent_definition(self):
        agent_path = _project_root / "svp" / "agents" / "setup_agent.md"
        return agent_path.read_text(encoding="utf-8")

    def test_delivery_json_template_present(self, agent_definition):
        assert '"environment_recommendation"' in agent_definition, (
            "Setup agent definition must contain a JSON template with "
            "'environment_recommendation' for the delivery section"
        )

    def test_license_json_template_present(self, agent_definition):
        assert '"spdx_headers"' in agent_definition, (
            "Setup agent definition must contain a JSON template with "
            "'spdx_headers' for the license section"
        )

    def test_no_packaging_instruction(self, agent_definition):
        # The agent definition should explicitly warn against 'packaging'
        assert "packaging" in agent_definition.lower(), (
            "Setup agent definition must mention 'packaging' to warn against it"
        )
        assert "Do NOT create a" in agent_definition or "CRITICAL" in agent_definition, (
            "Setup agent definition must contain a warning against creating "
            "a 'packaging' section"
        )

    def test_mandatory_followup_github_url(self, agent_definition):
        assert "MANDATORY FOLLOW-UP" in agent_definition, (
            "Setup agent definition must contain MANDATORY FOLLOW-UP instructions "
            "for GitHub URL and README path"
        )

    def test_mandatory_followup_readme_path(self, agent_definition):
        # Check both follow-ups exist
        followup_count = agent_definition.count("MANDATORY FOLLOW-UP")
        assert followup_count >= 2, (
            f"Setup agent definition must have at least 2 MANDATORY FOLLOW-UP "
            f"sections (GitHub URL and README path), found {followup_count}"
        )
