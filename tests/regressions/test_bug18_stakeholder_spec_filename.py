"""Bug 18 (2.1) regression: stakeholder_spec filename must be correct.

ARTIFACT_FILENAMES["stakeholder_spec"] must equal "stakeholder_spec.md",
not any other variant.
"""

from svp_config import ARTIFACT_FILENAMES


def test_stakeholder_spec_filename():
    """ARTIFACT_FILENAMES['stakeholder_spec'] must be 'stakeholder_spec.md'."""
    assert ARTIFACT_FILENAMES["stakeholder_spec"] == "stakeholder_spec.md"


def test_blueprint_filename():
    """ARTIFACT_FILENAMES['blueprint_dir'] must be 'blueprint' (SVP 2.1 split)."""
    assert ARTIFACT_FILENAMES["blueprint_dir"] == "blueprint"


def test_all_artifact_filenames_are_strings():
    """Every value in ARTIFACT_FILENAMES must be a non-empty string."""
    for key, value in ARTIFACT_FILENAMES.items():
        assert isinstance(value, str) and len(value) > 0, (
            f"ARTIFACT_FILENAMES['{key}'] must be a non-empty string"
        )
