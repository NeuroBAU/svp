"""Bug S3-107 regression: Systemic Config-Code Path Divergence.

Three sub-issues:
(a) stakeholder_spec canonical path must use specs/ (plural, real directory)
(b) lessons_learned key must exist in ARTIFACT_FILENAMES
(c) blueprint filenames must be derivable from ARTIFACT_FILENAMES
"""

from pathlib import Path

from svp_config import ARTIFACT_FILENAMES


class TestCanonicalPaths:
    """Verify ARTIFACT_FILENAMES contains correct canonical paths."""

    def test_canonical_spec_path_uses_specs_plural(self):
        """stakeholder_spec must use specs/ (real directory, not spec/ symlink)."""
        assert ARTIFACT_FILENAMES["stakeholder_spec"].startswith("specs/")

    def test_lessons_learned_in_registry(self):
        """lessons_learned key must exist in ARTIFACT_FILENAMES."""
        assert "lessons_learned" in ARTIFACT_FILENAMES
        assert ARTIFACT_FILENAMES["lessons_learned"] == "references/svp_2_1_lessons_learned.md"

    def test_blueprint_filenames_derivable_from_registry(self):
        """Blueprint filenames must be derivable via Path(...).name."""
        assert Path(ARTIFACT_FILENAMES["blueprint_prose"]).name == "blueprint_prose.md"
        assert Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name == "blueprint_contracts.md"


class TestGuardrail:
    """Verify task prompt injects canonical output path."""

    def test_task_prompt_contains_canonical_output_path(self, tmp_path):
        """_prepare_stakeholder_dialog output must contain the canonical spec path."""
        from prepare_task import _prepare_stakeholder_dialog

        # Create minimal project structure
        spec_path = tmp_path / ARTIFACT_FILENAMES["stakeholder_spec"]
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("# Test Spec")
        bp_dir = tmp_path / ARTIFACT_FILENAMES["blueprint_dir"]
        bp_dir.mkdir(parents=True, exist_ok=True)

        result = _prepare_stakeholder_dialog(
            project_root=tmp_path,
            state=None,
            mode=None,
            context=None,
            blueprint_dir=bp_dir,
        )

        canonical = ARTIFACT_FILENAMES["stakeholder_spec"]
        assert canonical in result, (
            f"Task prompt must contain canonical output path '{canonical}'"
        )


class TestAgentDefinitionAlignment:
    """Verify agent definition text matches canonical paths."""

    def test_construction_agent_paths_match_canonical(self):
        """Instruction text in agent definitions must match ARTIFACT_FILENAMES."""
        from construction_agents import STAKEHOLDER_DIALOG_DEFINITION

        canonical = ARTIFACT_FILENAMES["stakeholder_spec"]
        assert canonical in STAKEHOLDER_DIALOG_DEFINITION, (
            f"STAKEHOLDER_DIALOG_DEFINITION must reference '{canonical}'"
        )
