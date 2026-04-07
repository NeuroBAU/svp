"""Regression test for Bug 90: Setup agent output schema misaligned with
DEFAULT_PROFILE (packaging vs delivery+license sections) and missing
conditional follow-up questions for GitHub URL and existing README path.

SVP 2.2: DEFAULT_PROFILE, validate_profile, load_profile, _deep_merge
moved to src.unit_3.stub. validate_profile now takes (profile,
language_registry) and checks registry-based constraints rather than
packaging/repo_url rules. Tests for removed validations are skipped.
"""

import json
import sys
from pathlib import Path

import pytest

from profile_schema import DEFAULT_PROFILE, _deep_merge, load_profile


_project_root = Path(__file__).resolve().parents[2]


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
        # SVP 2.2: delivery is language-keyed; check python sub-key
        delivery = DEFAULT_PROFILE["delivery"]
        python_delivery = delivery.get("python", delivery)
        required = {"environment_recommendation", "dependency_format",
                     "source_layout", "entry_points"}
        assert required.issubset(python_delivery.keys()), (
            f"delivery section missing keys: {required - python_delivery.keys()}"
        )

    def test_license_has_required_keys(self):
        license_section = DEFAULT_PROFILE["license"]
        required = {"type", "holder", "author", "year", "spdx_headers"}
        assert required.issubset(license_section.keys()), (
            f"license section missing keys: {required - license_section.keys()}"
        )


class TestDeepMergePreservesCorrectSections:
    """When a properly structured profile is merged, delivery and license
    sections reflect the file values, not the defaults."""

    def test_delivery_values_override_defaults(self):
        file_profile = {
            "delivery": {
                "python": {
                    "environment_recommendation": "venv",
                    "source_layout": "flat",
                    "entry_points": True,
                }
            }
        }
        merged = _deep_merge(DEFAULT_PROFILE, file_profile)
        assert merged["delivery"]["python"]["environment_recommendation"] == "venv"
        assert merged["delivery"]["python"]["source_layout"] == "flat"
        assert merged["delivery"]["python"]["entry_points"] is True

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
        assert merged["delivery"]["python"]["source_layout"] == "conventional"
        assert merged["license"]["type"] == "Apache-2.0"  # from DEFAULT_PROFILE
        # packaging should be present but orphaned
        assert "packaging" in merged


class TestSetupAgentDefinitionHasSchemaTemplates:
    """The setup agent definition must contain delivery and license guidance.

    SVP 2.2: agent definitions are in setup_agent. The agent definition
    uses delivery.<lang>.environment_recommendation notation (not JSON templates
    with quoted keys). Packaging warning and MANDATORY FOLLOW-UP text patterns
    from SVP 2.1 are replaced by structured area-based dialog flow.
    """

    @pytest.fixture
    def agent_definition(self):
        from setup_agent import SETUP_AGENT_DEFINITION
        return SETUP_AGENT_DEFINITION

    def test_delivery_environment_recommendation_present(self, agent_definition):
        assert "environment_recommendation" in agent_definition, (
            "Setup agent definition must reference "
            "'environment_recommendation' for the delivery section"
        )

    def test_license_or_licensing_present(self, agent_definition):
        assert "licens" in agent_definition.lower(), (
            "Setup agent definition must mention licensing"
        )

    def test_packaging_mentioned(self, agent_definition):
        # The agent definition should mention packaging context
        assert "packaging" in agent_definition.lower(), (
            "Setup agent definition must mention 'packaging'"
        )

    def test_github_or_repo_url_mentioned(self, agent_definition):
        assert "github" in agent_definition.lower() or "repo" in agent_definition.lower(), (
            "Setup agent definition must mention GitHub or repo configuration"
        )

    def test_area_based_dialog_structure(self, agent_definition):
        # SVP 2.2 uses area-based dialog (Area 0-5)
        assert "Area" in agent_definition, (
            "Setup agent definition must contain area-based dialog structure"
        )
