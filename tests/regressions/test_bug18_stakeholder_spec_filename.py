"""Bug 18 (2.1) regression: stakeholder_spec filename must be correct.

ARTIFACT_FILENAMES["stakeholder_spec"] must have the correct path.

SVP 2.2 adaptation:
- ARTIFACT_FILENAMES is in src.unit_1.stub
- stakeholder_spec path is "specs/stakeholder_spec.md" (plural directory — Bug S3-107 fix)
"""

from svp_config import ARTIFACT_FILENAMES


def test_stakeholder_spec_filename():
    """ARTIFACT_FILENAMES['stakeholder_spec'] must be 'specs/stakeholder_spec.md'."""
    assert ARTIFACT_FILENAMES["stakeholder_spec"] == "specs/stakeholder_spec.md"


def test_blueprint_filename():
    """ARTIFACT_FILENAMES['blueprint_dir'] must be 'blueprint'."""
    assert ARTIFACT_FILENAMES["blueprint_dir"] == "blueprint"


def test_all_artifact_filenames_are_strings():
    """Every value in ARTIFACT_FILENAMES must be a non-empty string."""
    for key, value in ARTIFACT_FILENAMES.items():
        assert isinstance(value, str) and len(value) > 0, (
            f"ARTIFACT_FILENAMES['{key}'] must be a non-empty string"
        )
