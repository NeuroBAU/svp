"""Regression tests for Bug S3-97: Mixed archetype two-phase assembly and dual compliance scan.

Verifies that:
- PROJECT_ASSEMBLERS has a "mixed" entry
- assemble_mixed_project creates secondary language subdirectory
- compliance_scan_main runs secondary scanner for mixed archetype
- _prepare_integration_test_author injects bridge test requirement for mixed archetype
- GIT_REPO_AGENT_DEFINITION contains mixed archetype instructions
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from generate_assembly_map import (
    PROJECT_ASSEMBLERS,
    GIT_REPO_AGENT_DEFINITION,
    assemble_mixed_project,
)


class TestProjectAssemblersMixedKey:
    """Bug S3-97: PROJECT_ASSEMBLERS must have 'mixed' entry."""

    def test_mixed_key_exists(self):
        """The 'mixed' key must be present in PROJECT_ASSEMBLERS."""
        assert "mixed" in PROJECT_ASSEMBLERS

    def test_mixed_key_is_callable(self):
        """The 'mixed' entry must be a callable."""
        assert callable(PROJECT_ASSEMBLERS["mixed"])

    def test_mixed_key_is_assemble_mixed_project(self):
        """The 'mixed' entry must point to assemble_mixed_project."""
        assert PROJECT_ASSEMBLERS["mixed"] is assemble_mixed_project


class TestAssembleMixedProject:
    """Bug S3-97: assemble_mixed_project two-phase composition."""

    def _make_profile(self, primary="python", secondary="r"):
        return {
            "project_name": "test-mixed",
            "archetype": "mixed",
            "language": {
                "primary": primary,
                "secondary": secondary,
            },
            "delivery": {
                "python": {"source_layout": "conventional"},
            },
        }

    def test_creates_secondary_subdirectory(self, tmp_path):
        """Phase 2 must create <secondary_language>/ subdirectory."""
        project_root = tmp_path / "test-mixed"
        project_root.mkdir()
        profile = self._make_profile(secondary="r")
        repo_dir = assemble_mixed_project(project_root, profile, {})
        assert (repo_dir / "r").is_dir()

    def test_creates_secondary_tests_dir(self, tmp_path):
        """Phase 2 must create <secondary_language>/tests/ subdirectory."""
        project_root = tmp_path / "test-mixed"
        project_root.mkdir()
        profile = self._make_profile(secondary="r")
        repo_dir = assemble_mixed_project(project_root, profile, {})
        assert (repo_dir / "r" / "tests").is_dir()

    def test_primary_structure_created(self, tmp_path):
        """Phase 1 must create primary language root structure."""
        project_root = tmp_path / "test-mixed"
        project_root.mkdir()
        profile = self._make_profile(primary="python", secondary="r")
        repo_dir = assemble_mixed_project(project_root, profile, {})
        assert (repo_dir / "pyproject.toml").exists()

    def test_raises_without_secondary(self, tmp_path):
        """Must raise ValueError if secondary language is not set."""
        project_root = tmp_path / "test-mixed"
        project_root.mkdir()
        profile = {
            "project_name": "test-mixed",
            "archetype": "mixed",
            "language": {"primary": "python"},
        }
        with pytest.raises(ValueError, match="secondary"):
            assemble_mixed_project(project_root, profile, {})

    def test_r_primary_python_secondary(self, tmp_path):
        """Mixed project with R primary and Python secondary."""
        project_root = tmp_path / "test-mixed"
        project_root.mkdir()
        profile = self._make_profile(primary="r", secondary="python")
        repo_dir = assemble_mixed_project(project_root, profile, {})
        # R primary creates DESCRIPTION
        assert (repo_dir / "DESCRIPTION").exists()
        # Python secondary subdirectory
        assert (repo_dir / "python").is_dir()
        assert (repo_dir / "python" / "tests").is_dir()


class TestComplianceScanDual:
    """Bug S3-97: compliance_scan_main must run secondary scanner for mixed archetype."""

    def test_secondary_scanner_invoked_for_mixed(self):
        """compliance_scan_main must invoke secondary scanner when archetype is mixed."""
        from structural_check import compliance_scan_main, COMPLIANCE_SCANNERS

        mock_profile = {
            "archetype": "mixed",
            "language": {"primary": "python", "secondary": "r"},
        }

        py_scan = MagicMock(return_value=[])
        r_scan = MagicMock(return_value=[])

        with (
            patch("profile_schema.load_profile", return_value=mock_profile),
            patch.dict(COMPLIANCE_SCANNERS, {"python": py_scan, "r": r_scan}),
        ):
            compliance_scan_main(
                [
                    "--project-root", "/tmp/test",
                    "--src-dir", "/tmp/test/src",
                    "--tests-dir", "/tmp/test/tests",
                    "--format", "json",
                ]
            )
            py_scan.assert_called_once()
            r_scan.assert_called_once()

    def test_secondary_scanner_not_invoked_for_single(self):
        """compliance_scan_main must NOT invoke secondary scanner for non-mixed."""
        from structural_check import compliance_scan_main, COMPLIANCE_SCANNERS

        mock_profile = {
            "archetype": "python",
            "language": {"primary": "python"},
        }

        py_scan = MagicMock(return_value=[])
        r_scan = MagicMock(return_value=[])

        with (
            patch("profile_schema.load_profile", return_value=mock_profile),
            patch.dict(COMPLIANCE_SCANNERS, {"python": py_scan, "r": r_scan}),
        ):
            compliance_scan_main(
                [
                    "--project-root", "/tmp/test",
                    "--src-dir", "/tmp/test/src",
                    "--tests-dir", "/tmp/test/tests",
                    "--format", "json",
                ]
            )
            py_scan.assert_called_once()
            r_scan.assert_not_called()

    def test_findings_aggregated(self):
        """Findings from both scanners must be aggregated."""
        from structural_check import compliance_scan_main, COMPLIANCE_SCANNERS
        import io

        mock_profile = {
            "archetype": "mixed",
            "language": {"primary": "python", "secondary": "r"},
        }

        py_findings = [{"file": "main.py", "line": 1, "message": "py issue"}]
        r_findings = [{"file": "engine.R", "line": 2, "message": "r issue"}]

        py_scan = MagicMock(return_value=py_findings)
        r_scan = MagicMock(return_value=r_findings)

        with (
            patch("profile_schema.load_profile", return_value=mock_profile),
            patch.dict(COMPLIANCE_SCANNERS, {"python": py_scan, "r": r_scan}),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            compliance_scan_main(
                [
                    "--project-root", "/tmp/test",
                    "--src-dir", "/tmp/test/src",
                    "--tests-dir", "/tmp/test/tests",
                    "--format", "json",
                ]
            )
            output = json.loads(mock_stdout.getvalue())
            assert len(output) == 2
            files = [f["file"] for f in output]
            assert "main.py" in files
            assert "engine.R" in files


class TestIntegrationTestBridgeInjection:
    """Bug S3-97: _prepare_integration_test_author bridge test injection."""

    def test_bridge_requirement_injected_for_mixed(self, tmp_path):
        """Must inject bridge test requirement for mixed archetype."""
        from prepare_task import _prepare_integration_test_author

        # Create minimal project structure
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        svp_dir = project_root / ".svp"
        svp_dir.mkdir()

        profile = {
            "archetype": "mixed",
            "language": {
                "primary": "python",
                "secondary": "r",
                "communication": {
                    "python_r": {"library": "rpy2", "conda_package": "rpy2"},
                },
            },
        }
        profile_path = project_root / "project_profile.json"
        profile_path.write_text(json.dumps(profile))

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()

        result = _prepare_integration_test_author(
            project_root, None, None, None, blueprint_dir
        )

        assert "Bridge Test Requirement" in result
        assert "AC-92" in result
        assert "python_r" in result
        assert "rpy2" in result

    def test_no_bridge_requirement_for_python_only(self, tmp_path):
        """Must NOT inject bridge test requirement for non-mixed archetype."""
        from prepare_task import _prepare_integration_test_author

        project_root = tmp_path / "test-project"
        project_root.mkdir()
        svp_dir = project_root / ".svp"
        svp_dir.mkdir()

        profile = {
            "archetype": "python",
            "language": {"primary": "python"},
        }
        profile_path = project_root / "project_profile.json"
        profile_path.write_text(json.dumps(profile))

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()

        result = _prepare_integration_test_author(
            project_root, None, None, None, blueprint_dir
        )

        assert "Bridge Test Requirement" not in result


class TestGitRepoAgentDefinitionMixed:
    """Bug S3-97: GIT_REPO_AGENT_DEFINITION must contain mixed archetype instructions."""

    def test_contains_mixed_archetype_section(self):
        """Agent definition must mention mixed archetype."""
        assert "Mixed Archetype Assembly" in GIT_REPO_AGENT_DEFINITION

    def test_contains_two_phase(self):
        """Agent definition must describe two-phase composition."""
        assert "Phase 1" in GIT_REPO_AGENT_DEFINITION
        assert "Phase 2" in GIT_REPO_AGENT_DEFINITION

    def test_contains_secondary_subdirectory(self):
        """Agent definition must mention secondary language subdirectory."""
        assert "secondary_language" in GIT_REPO_AGENT_DEFINITION

    def test_contains_dual_quality_configs(self):
        """Agent definition must mention quality configs for both languages."""
        assert "both languages" in GIT_REPO_AGENT_DEFINITION.lower()
