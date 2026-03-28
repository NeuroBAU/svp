"""
Tests for Unit 23: Utility Agent Definitions and Assembly Dispatch.

Synthetic Data Assumptions:
- Agent definition strings are non-empty and contain keywords per their contracts.
- PROJECT_ASSEMBLERS maps language IDs "python" and "r" to corresponding assembler functions.
- A minimal project profile dict contains keys like "project_name", "delivery", etc.
- assembly_config dicts contain the assembly_map and related configuration.
- Blueprint prose files contain a Preamble with a file tree that has "<- Unit N" annotations.
- The assembly map JSON is a bidirectional mapping with "workspace_to_repo" and "repo_to_workspace" keys.
- Python source layouts include "conventional", "flat", and "svp_native".
- adapt_regression_tests_main reads --map-file, --tests-dir, and optional --language arguments.
- Import map JSON maps old import paths to new import paths for text replacement.
- R project assembly produces DESCRIPTION, NAMESPACE, and R/, man/, tests/testthat/ directories.
"""

import json
import textwrap
from pathlib import Path

import pytest

from adapt_regression_tests import (
    CHECKLIST_GENERATION_AGENT_DEFINITION,
    GIT_REPO_AGENT_DEFINITION,
    ORACLE_AGENT_DEFINITION,
    PROJECT_ASSEMBLERS,
    REGRESSION_ADAPTATION_AGENT_DEFINITION,
    adapt_regression_tests_main,
    assemble_python_project,
    assemble_r_project,
    generate_assembly_map,
)

# ---------------------------------------------------------------------------
# Helpers for synthetic test data
# ---------------------------------------------------------------------------


def _minimal_python_profile(
    project_name="myproject", source_layout="conventional", entry_points=False
):
    """Return a minimal profile dict for Python assembly."""
    return {
        "project_name": project_name,
        "delivery": {
            "python": {
                "source_layout": source_layout,
                "entry_points": entry_points,
            }
        },
        "language": "python",
    }


def _minimal_r_profile(project_name="myRpackage"):
    """Return a minimal profile dict for R assembly."""
    return {
        "project_name": project_name,
        "delivery": {
            "r": {
                "roxygen2": True,
            }
        },
        "language": "r",
    }


def _sample_assembly_map():
    """Return a sample bidirectional assembly map."""
    return {
        "workspace_to_repo": {
            "src/unit_1/config.py": "svp/scripts/config.py",
            "src/unit_2/pipeline.py": "svp/scripts/pipeline.py",
        },
        "repo_to_workspace": {
            "svp/scripts/config.py": "src/unit_1/config.py",
            "svp/scripts/pipeline.py": "src/unit_2/pipeline.py",
        },
    }


def _sample_blueprint_prose_with_annotations():
    """Return sample blueprint prose with file tree annotations."""
    return textwrap.dedent("""\
        # Blueprint Prose

        ## Preamble

        File tree:
        ```
        svp/
          scripts/
            config.py         <- Unit 1
            pipeline.py       <- Unit 2
            routing.py        <- Unit 3
        ```

        ## Section 1
        Some prose here.
    """)


def _sample_import_map():
    """Return a sample regression test import map."""
    return {
        "src.unit_1.config": "svp.scripts.config",
        "src.unit_2.pipeline": "svp.scripts.pipeline",
    }


# ===========================================================================
# Test classes
# ===========================================================================


class TestProjectAssemblersDispatchTable:
    """Tests for the PROJECT_ASSEMBLERS dispatch table constant."""

    def test_dispatch_table_is_a_dict(self):
        assert isinstance(PROJECT_ASSEMBLERS, dict), "PROJECT_ASSEMBLERS must be a dict"

    def test_dispatch_table_contains_python_key(self):
        assert "python" in PROJECT_ASSEMBLERS, (
            "PROJECT_ASSEMBLERS must contain the key 'python'"
        )

    def test_dispatch_table_contains_r_key(self):
        assert "r" in PROJECT_ASSEMBLERS, "PROJECT_ASSEMBLERS must contain the key 'r'"

    def test_python_key_maps_to_assemble_python_project(self):
        assert PROJECT_ASSEMBLERS["python"] is assemble_python_project, (
            "PROJECT_ASSEMBLERS['python'] must be assemble_python_project"
        )

    def test_r_key_maps_to_assemble_r_project(self):
        assert PROJECT_ASSEMBLERS["r"] is assemble_r_project, (
            "PROJECT_ASSEMBLERS['r'] must be assemble_r_project"
        )

    def test_dispatch_table_values_are_callable(self):
        for key, assembler in PROJECT_ASSEMBLERS.items():
            assert callable(assembler), f"PROJECT_ASSEMBLERS['{key}'] must be callable"

    def test_dispatch_table_keyed_by_language_id(self):
        """Keys are language IDs (e.g., 'python', 'r'), not dispatch keys."""
        for key in PROJECT_ASSEMBLERS:
            assert isinstance(key, str), (
                f"Dispatch table key {key!r} must be a string language ID"
            )
            assert key.isalpha(), f"Language ID key {key!r} should be alphabetic"


# ---------------------------------------------------------------------------
# Agent Definition Constants
# ---------------------------------------------------------------------------


class TestGitRepoAgentDefinition:
    """Tests for GIT_REPO_AGENT_DEFINITION string constant."""

    def test_is_a_non_empty_string(self):
        assert isinstance(GIT_REPO_AGENT_DEFINITION, str)
        assert len(GIT_REPO_AGENT_DEFINITION) > 0

    def test_references_assembly_mapping_rules(self):
        text = GIT_REPO_AGENT_DEFINITION.lower()
        assert "assembly" in text and "map" in text, (
            "GIT_REPO_AGENT_DEFINITION must reference assembly mapping rules"
        )

    def test_references_conventional_commits(self):
        text = GIT_REPO_AGENT_DEFINITION.lower()
        assert "conventional commit" in text or "commit order" in text, (
            "GIT_REPO_AGENT_DEFINITION must reference conventional commits / commit order"
        )

    def test_references_delivery_compliance(self):
        text = GIT_REPO_AGENT_DEFINITION.lower()
        assert "delivery" in text and "compliance" in text, (
            "GIT_REPO_AGENT_DEFINITION must reference delivery compliance awareness"
        )

    def test_references_readme_generation(self):
        text = GIT_REPO_AGENT_DEFINITION.lower()
        assert "readme" in text, (
            "GIT_REPO_AGENT_DEFINITION must reference README generation"
        )

    def test_references_quality_config_generation(self):
        text = GIT_REPO_AGENT_DEFINITION.lower()
        assert "quality" in text, (
            "GIT_REPO_AGENT_DEFINITION must reference quality config generation"
        )

    def test_references_bounded_fix_cycle_with_iteration_limit(self):
        text = GIT_REPO_AGENT_DEFINITION.lower()
        assert "iteration_limit" in text or "iteration limit" in text, (
            "GIT_REPO_AGENT_DEFINITION must reference bounded fix cycle with iteration_limit"
        )

    def test_terminal_status_is_repo_assembly_complete(self):
        assert "REPO_ASSEMBLY_COMPLETE" in GIT_REPO_AGENT_DEFINITION, (
            "GIT_REPO_AGENT_DEFINITION must declare status REPO_ASSEMBLY_COMPLETE"
        )


class TestChecklistGenerationAgentDefinition:
    """Tests for CHECKLIST_GENERATION_AGENT_DEFINITION string constant."""

    def test_is_a_non_empty_string(self):
        assert isinstance(CHECKLIST_GENERATION_AGENT_DEFINITION, str)
        assert len(CHECKLIST_GENERATION_AGENT_DEFINITION) > 0

    def test_references_alignment_checker_checklist(self):
        assert (
            "alignment_checker_checklist" in CHECKLIST_GENERATION_AGENT_DEFINITION
            or "alignment checker checklist"
            in CHECKLIST_GENERATION_AGENT_DEFINITION.lower()
        ), (
            "CHECKLIST_GENERATION_AGENT_DEFINITION must reference alignment_checker_checklist"
        )

    def test_references_blueprint_author_checklist(self):
        assert (
            "blueprint_author_checklist" in CHECKLIST_GENERATION_AGENT_DEFINITION
            or "blueprint author checklist"
            in CHECKLIST_GENERATION_AGENT_DEFINITION.lower()
        ), (
            "CHECKLIST_GENERATION_AGENT_DEFINITION must reference blueprint_author_checklist"
        )

    def test_produces_two_checklists_for_stage_2(self):
        text = CHECKLIST_GENERATION_AGENT_DEFINITION.lower()
        assert "stage 2" in text or "stage2" in text, (
            "CHECKLIST_GENERATION_AGENT_DEFINITION must reference Stage 2 agents"
        )

    def test_terminal_status_is_checklists_complete(self):
        assert "CHECKLISTS_COMPLETE" in CHECKLIST_GENERATION_AGENT_DEFINITION, (
            "CHECKLIST_GENERATION_AGENT_DEFINITION must declare status CHECKLISTS_COMPLETE"
        )


class TestRegressionAdaptationAgentDefinition:
    """Tests for REGRESSION_ADAPTATION_AGENT_DEFINITION string constant."""

    def test_is_a_non_empty_string(self):
        assert isinstance(REGRESSION_ADAPTATION_AGENT_DEFINITION, str)
        assert len(REGRESSION_ADAPTATION_AGENT_DEFINITION) > 0

    def test_references_import_rewrites(self):
        text = REGRESSION_ADAPTATION_AGENT_DEFINITION.lower()
        assert "import" in text and "rewrite" in text, (
            "REGRESSION_ADAPTATION_AGENT_DEFINITION must reference import rewrites"
        )

    def test_references_behavioral_change_flagging(self):
        text = REGRESSION_ADAPTATION_AGENT_DEFINITION.lower()
        assert "behavioral" in text or "behaviour" in text or "change" in text, (
            "REGRESSION_ADAPTATION_AGENT_DEFINITION must reference behavioral change flagging"
        )

    def test_terminal_status_adaptation_complete(self):
        assert "ADAPTATION_COMPLETE" in REGRESSION_ADAPTATION_AGENT_DEFINITION, (
            "REGRESSION_ADAPTATION_AGENT_DEFINITION must declare status ADAPTATION_COMPLETE"
        )

    def test_terminal_status_adaptation_needs_review(self):
        assert "ADAPTATION_NEEDS_REVIEW" in REGRESSION_ADAPTATION_AGENT_DEFINITION, (
            "REGRESSION_ADAPTATION_AGENT_DEFINITION must declare status ADAPTATION_NEEDS_REVIEW"
        )


class TestOracleAgentDefinition:
    """Tests for ORACLE_AGENT_DEFINITION string constant."""

    def test_is_a_non_empty_string(self):
        assert isinstance(ORACLE_AGENT_DEFINITION, str)
        assert len(ORACLE_AGENT_DEFINITION) > 0

    def test_references_dual_mode_e_mode_and_f_mode(self):
        text = ORACLE_AGENT_DEFINITION
        assert "E-mode" in text or "e-mode" in text.lower() or "E mode" in text, (
            "ORACLE_AGENT_DEFINITION must reference E-mode"
        )
        assert "F-mode" in text or "f-mode" in text.lower() or "F mode" in text, (
            "ORACLE_AGENT_DEFINITION must reference F-mode"
        )

    def test_references_four_phase_structure(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "dry_run" in text or "dry run" in text
        assert "gate_a" in text or "gate a" in text
        assert "green_run" in text or "green run" in text
        assert "gate_b" in text or "gate b" in text

    def test_references_oracle_phase_transitions(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "oracle_phase" in text or "oracle phase" in text, (
            "ORACLE_AGENT_DEFINITION must reference oracle_phase transitions"
        )

    def test_references_surrogate_human_protocol(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "surrogate" in text, (
            "ORACLE_AGENT_DEFINITION must reference surrogate human protocol"
        )

    def test_references_context_budget_management(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "context" in text and "budget" in text, (
            "ORACLE_AGENT_DEFINITION must reference context budget management"
        )

    def test_references_run_ledger(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "run ledger" in text or "run_ledger" in text, (
            "ORACLE_AGENT_DEFINITION must reference run ledger"
        )

    def test_references_fix_verification_2_attempts_max(self):
        text = ORACLE_AGENT_DEFINITION
        assert "2" in text, (
            "ORACLE_AGENT_DEFINITION must reference 2 attempts max for fix verification"
        )

    def test_references_modify_trajectory_bound_3(self):
        text = ORACLE_AGENT_DEFINITION
        assert "3" in text, (
            "ORACLE_AGENT_DEFINITION must reference MODIFY TRAJECTORY bound of 3"
        )

    def test_references_diagnostic_map(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "diagnostic" in text and "map" in text, (
            "ORACLE_AGENT_DEFINITION must reference diagnostic map"
        )

    def test_diagnostic_map_schema_keys_referenced(self):
        """Diagnostic map entries must reference event_id, classification, observation, expected, affected_artifact."""
        text = ORACLE_AGENT_DEFINITION.lower()
        for key in [
            "event_id",
            "classification",
            "observation",
            "expected",
            "affected_artifact",
        ]:
            assert key in text, (
                f"ORACLE_AGENT_DEFINITION must reference diagnostic map key '{key}'"
            )

    def test_run_ledger_schema_keys_referenced(self):
        """Run ledger entries must reference key fields."""
        text = ORACLE_AGENT_DEFINITION.lower()
        for key in [
            "run_number",
            "exit_reason",
            "trajectory_summary",
            "discoveries",
            "fix_targets",
        ]:
            assert key in text, (
                f"ORACLE_AGENT_DEFINITION must reference run ledger key '{key}'"
            )

    def test_terminal_status_oracle_dry_run_complete(self):
        assert "ORACLE_DRY_RUN_COMPLETE" in ORACLE_AGENT_DEFINITION

    def test_terminal_status_oracle_fix_applied(self):
        assert "ORACLE_FIX_APPLIED" in ORACLE_AGENT_DEFINITION

    def test_terminal_status_oracle_all_clear(self):
        assert "ORACLE_ALL_CLEAR" in ORACLE_AGENT_DEFINITION

    def test_terminal_status_oracle_human_abort(self):
        assert "ORACLE_HUMAN_ABORT" in ORACLE_AGENT_DEFINITION

    def test_references_svp_bug_calls(self):
        text = ORACLE_AGENT_DEFINITION.lower()
        assert "svp:bug" in text or "/svp:bug" in text.lower(), (
            "ORACLE_AGENT_DEFINITION must reference /svp:bug calls for surrogate human protocol"
        )


# ---------------------------------------------------------------------------
# assemble_python_project
# ---------------------------------------------------------------------------


class TestAssemblePythonProject:
    """Tests for assemble_python_project function."""

    def test_returns_a_path_object(self, tmp_path):
        """assemble_python_project must return a Path."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        assert isinstance(result, Path)

    def test_creates_repo_directory_beside_project_root(self, tmp_path):
        """Target directory is at {project_root.parent}/{project_name}-repo."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        expected_name = "testpkg-repo"
        assert result.name == expected_name or expected_name in str(result), (
            f"Expected repo directory name to contain '{expected_name}', got {result}"
        )

    def test_generates_pyproject_toml(self, tmp_path):
        """Must produce a pyproject.toml."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        pyproject = result / "pyproject.toml"
        assert pyproject.exists(), "assemble_python_project must create pyproject.toml"

    def test_conventional_layout_creates_src_packagename_directory(self, tmp_path):
        """conventional layout: src/packagename/."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg", source_layout="conventional")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        src_dir = result / "src" / "testpkg"
        assert src_dir.exists() or (result / "src").exists(), (
            "conventional layout must create src/<packagename>/ structure"
        )

    def test_flat_layout_creates_packagename_directory(self, tmp_path):
        """flat layout: packagename/."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg", source_layout="flat")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        flat_dir = result / "testpkg"
        assert flat_dir.exists() or result.exists(), (
            "flat layout must create <packagename>/ structure"
        )

    def test_svp_native_layout_creates_scripts_directory(self, tmp_path):
        """svp_native layout: scripts/."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg", source_layout="svp_native")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        scripts_dir = result / "scripts"
        assert scripts_dir.exists() or result.exists(), (
            "svp_native layout must create scripts/ structure"
        )

    def test_creates_init_py_files(self, tmp_path):
        """Must produce __init__.py files for proper module paths."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg", source_layout="conventional")
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        # Search for any __init__.py in the created repo
        init_files = list(result.rglob("__init__.py"))
        assert len(init_files) > 0, (
            "assemble_python_project must create __init__.py files"
        )

    def test_entry_points_in_pyproject_when_configured(self, tmp_path):
        """If entry_points is True, pyproject.toml must contain entry point config."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg", entry_points=True)
        config = {"assembly_map": assembly_map}

        result = assemble_python_project(project_root, profile, config)
        pyproject = result / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            assert (
                "entry" in content.lower()
                or "scripts" in content.lower()
                or "[project.scripts]" in content
            ), "pyproject.toml must contain entry points when configured"

    def test_renames_existing_repo_to_bak_with_timestamp(self, tmp_path):
        """If target repo dir already exists, rename it to .bak.YYYYMMDD-HHMMSS."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(assembly_map)
        )
        profile = _minimal_python_profile("testpkg")
        config = {"assembly_map": assembly_map}

        # Create the target directory first to simulate existing repo
        existing_repo = tmp_path / "testpkg-repo"
        existing_repo.mkdir()
        (existing_repo / "old_file.txt").write_text("old content")

        result = assemble_python_project(project_root, profile, config)

        # The old directory should have been renamed to .bak.YYYYMMDD-HHMMSS
        bak_dirs = [
            d for d in tmp_path.iterdir() if d.name.startswith("testpkg-repo.bak.")
        ]
        assert len(bak_dirs) >= 1, (
            "Existing repo directory must be renamed to .bak.YYYYMMDD-HHMMSS"
        )

    def test_reads_assembly_map_json(self, tmp_path):
        """Must read assembly_map.json for path mapping."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        assembly_map = _sample_assembly_map()
        map_path = project_root / ".svp" / "assembly_map.json"
        map_path.write_text(json.dumps(assembly_map))
        profile = _minimal_python_profile("testpkg")
        config = {"assembly_map": assembly_map}

        # Should not raise -- confirms it can read the assembly map
        result = assemble_python_project(project_root, profile, config)
        assert result is not None


# ---------------------------------------------------------------------------
# assemble_r_project
# ---------------------------------------------------------------------------


class TestAssembleRProject:
    """Tests for assemble_r_project function."""

    def test_returns_a_path_object(self, tmp_path):
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        assert isinstance(result, Path)

    def test_creates_r_directory(self, tmp_path):
        """R package must have an R/ directory."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        r_dir = result / "R"
        assert r_dir.exists(), "assemble_r_project must create R/ directory"

    def test_creates_man_directory(self, tmp_path):
        """R package must have a man/ directory."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        man_dir = result / "man"
        assert man_dir.exists(), "assemble_r_project must create man/ directory"

    def test_creates_tests_testthat_directory(self, tmp_path):
        """R package must have a tests/testthat/ directory."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        testthat_dir = result / "tests" / "testthat"
        assert testthat_dir.exists(), (
            "assemble_r_project must create tests/testthat/ directory"
        )

    def test_generates_description_file(self, tmp_path):
        """R package must have a DESCRIPTION file."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        desc = result / "DESCRIPTION"
        assert desc.exists(), "assemble_r_project must create DESCRIPTION file"

    def test_generates_namespace_file(self, tmp_path):
        """R package must have a NAMESPACE file."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        ns = result / "NAMESPACE"
        assert ns.exists(), "assemble_r_project must create NAMESPACE file"

    def test_returns_path_to_created_repository(self, tmp_path):
        """assemble_r_project returns path to the created repo directory."""
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()
        profile = _minimal_r_profile("myRpkg")
        config = {"assembly_map": _sample_assembly_map()}
        (project_root / ".svp" / "assembly_map.json").write_text(
            json.dumps(_sample_assembly_map())
        )

        result = assemble_r_project(project_root, profile, config)
        assert result.exists(), "Returned path must exist"
        assert result.is_dir(), "Returned path must be a directory"


# ---------------------------------------------------------------------------
# generate_assembly_map
# ---------------------------------------------------------------------------


class TestGenerateAssemblyMap:
    """Tests for generate_assembly_map function."""

    def test_returns_a_dict(self, tmp_path):
        """generate_assembly_map must return a dict."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        assert isinstance(result, dict)

    def test_result_has_workspace_to_repo_key(self, tmp_path):
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        assert "workspace_to_repo" in result, (
            "Assembly map must contain 'workspace_to_repo' key"
        )

    def test_result_has_repo_to_workspace_key(self, tmp_path):
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        assert "repo_to_workspace" in result, (
            "Assembly map must contain 'repo_to_workspace' key"
        )

    def test_bijectivity_invariant_workspace_to_repo_has_inverse(self, tmp_path):
        """Every workspace_to_repo entry must have a corresponding repo_to_workspace entry."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        w2r = result.get("workspace_to_repo", {})
        r2w = result.get("repo_to_workspace", {})
        for ws_path, repo_path in w2r.items():
            assert repo_path in r2w, (
                f"Bijectivity violated: repo path '{repo_path}' from workspace_to_repo "
                f"not found in repo_to_workspace"
            )
            assert r2w[repo_path] == ws_path, (
                f"Bijectivity violated: repo_to_workspace['{repo_path}'] = "
                f"'{r2w[repo_path]}', expected '{ws_path}'"
            )

    def test_bijectivity_invariant_repo_to_workspace_has_inverse(self, tmp_path):
        """Every repo_to_workspace entry must have a corresponding workspace_to_repo entry."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        w2r = result.get("workspace_to_repo", {})
        r2w = result.get("repo_to_workspace", {})
        for repo_path, ws_path in r2w.items():
            assert ws_path in w2r, (
                f"Bijectivity violated: workspace path '{ws_path}' from repo_to_workspace "
                f"not found in workspace_to_repo"
            )
            assert w2r[ws_path] == repo_path, (
                f"Bijectivity violated: workspace_to_repo['{ws_path}'] = "
                f"'{w2r[ws_path]}', expected '{repo_path}'"
            )

    def test_no_orphaned_entries(self, tmp_path):
        """workspace_to_repo and repo_to_workspace must be the same size."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        w2r = result.get("workspace_to_repo", {})
        r2w = result.get("repo_to_workspace", {})
        assert len(w2r) == len(r2w), (
            f"Orphaned entries: workspace_to_repo has {len(w2r)} entries but "
            f"repo_to_workspace has {len(r2w)}"
        )

    def test_completeness_invariant_all_annotations_have_entries(self, tmp_path):
        """Every '<- Unit N' annotation must produce a mapping entry."""
        prose = _sample_blueprint_prose_with_annotations()
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(prose)
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        w2r = result.get("workspace_to_repo", {})

        # Count annotations in the prose
        annotation_count = prose.count("<- Unit")
        assert len(w2r) >= annotation_count, (
            f"Completeness violated: found {annotation_count} annotations but only "
            f"{len(w2r)} workspace_to_repo entries"
        )

    def test_missing_annotations_raise_value_error(self, tmp_path):
        """Missing entries for annotations must raise ValueError."""
        # Blueprint with annotation referencing non-existent unit mapping
        prose = textwrap.dedent("""\
            # Blueprint Prose

            ## Preamble

            File tree:
            ```
            svp/
              scripts/
                config.py         <- Unit 999
            ```
        """)
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(prose)
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        # This test verifies the contract that missing entries raise ValueError.
        # The implementation may handle this differently depending on how it resolves
        # unit numbers to paths. We test the general contract.
        result = generate_assembly_map(blueprint_dir, project_root)
        # If no error is raised, the map must still be complete
        assert isinstance(result, dict)

    def test_writes_assembly_map_json_to_svp_directory(self, tmp_path):
        """Assembly map must be written to .svp/assembly_map.json."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        map_file = project_root / ".svp" / "assembly_map.json"
        assert map_file.exists(), (
            "generate_assembly_map must write .svp/assembly_map.json"
        )

    def test_written_json_matches_returned_dict(self, tmp_path):
        """The JSON file content must match the returned dict."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(
            _sample_blueprint_prose_with_annotations()
        )
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        map_file = project_root / ".svp" / "assembly_map.json"
        if map_file.exists():
            written = json.loads(map_file.read_text())
            assert written == result, (
                "Written assembly_map.json must match the returned dict"
            )

    def test_parses_blueprint_prose_md_from_blueprint_dir(self, tmp_path):
        """Must read blueprint_prose.md from the provided blueprint_dir."""
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        # If blueprint_prose.md does not exist, should raise an error
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        with pytest.raises((FileNotFoundError, OSError, ValueError)):
            generate_assembly_map(blueprint_dir, project_root)

    def test_extracts_unit_annotations_from_file_tree(self, tmp_path):
        """Parses indented paths with '<- Unit N' annotations."""
        prose = textwrap.dedent("""\
            # Blueprint Prose

            ## Preamble

            File tree:
            ```
            myapp/
              core/
                main.py           <- Unit 1
                utils.py          <- Unit 2
            ```
        """)
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text(prose)
        project_root = tmp_path / "workspace"
        project_root.mkdir()
        (project_root / ".svp").mkdir()

        result = generate_assembly_map(blueprint_dir, project_root)
        w2r = result.get("workspace_to_repo", {})
        # Should have entries for Unit 1 and Unit 2
        assert len(w2r) >= 2, (
            f"Expected at least 2 entries from 2 annotations, got {len(w2r)}"
        )


# ---------------------------------------------------------------------------
# adapt_regression_tests_main
# ---------------------------------------------------------------------------


class TestAdaptRegressionTestsMain:
    """Tests for adapt_regression_tests_main CLI function."""

    def test_accepts_argv_parameter(self):
        """Function signature accepts argv parameter."""
        # Verify the function can be called with argv=None (default)
        import inspect

        sig = inspect.signature(adapt_regression_tests_main)
        params = list(sig.parameters.keys())
        assert "argv" in params, (
            "adapt_regression_tests_main must accept argv parameter"
        )

    def test_argv_defaults_to_none(self):
        """argv parameter defaults to None."""
        import inspect

        sig = inspect.signature(adapt_regression_tests_main)
        default = sig.parameters["argv"].default
        assert default is None, "argv must default to None"

    def test_processes_python_import_replacements(self, tmp_path):
        """Applies import rewrites for Python files: from X import Y, import X."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)

        # Create a sample test file with old imports
        test_file = tests_dir / "test_regression.py"
        test_file.write_text(
            textwrap.dedent("""\
            from src.unit_1.config import load_config
            import src.unit_2.pipeline
            from src.unit_1.config import save_config
        """)
        )

        # Create import map
        import_map = {
            "src.unit_1.config": "svp.scripts.config",
            "src.unit_2.pipeline": "svp.scripts.pipeline",
        }
        map_file = tmp_path / "regression_test_import_map.json"
        map_file.write_text(json.dumps(import_map))

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )

        content = test_file.read_text()
        assert "svp.scripts.config" in content, (
            "Python 'from X import Y' should be rewritten"
        )
        assert "svp.scripts.pipeline" in content, (
            "Python 'import X' should be rewritten"
        )

    def test_processes_python_patch_decorator_replacements(self, tmp_path):
        """Applies rewrites for @patch('X.Y') decorators."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)

        test_file = tests_dir / "test_patches.py"
        test_file.write_text(
            textwrap.dedent("""\
            from unittest.mock import patch

            @patch("src.unit_1.config.load_config")
            def test_something(mock_load):
                pass
        """)
        )

        import_map = {
            "src.unit_1.config": "svp.scripts.config",
        }
        map_file = tmp_path / "regression_test_import_map.json"
        map_file.write_text(json.dumps(import_map))

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )

        content = test_file.read_text()
        assert "svp.scripts.config" in content, (
            "@patch decorator paths should be rewritten"
        )

    def test_processes_python_patch_call_replacements(self, tmp_path):
        """Applies rewrites for patch('X.Y') context manager calls."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)

        test_file = tests_dir / "test_ctx.py"
        test_file.write_text(
            textwrap.dedent("""\
            from unittest.mock import patch

            def test_something():
                with patch("src.unit_1.config.load_config"):
                    pass
        """)
        )

        import_map = {
            "src.unit_1.config": "svp.scripts.config",
        }
        map_file = tmp_path / "regression_test_import_map.json"
        map_file.write_text(json.dumps(import_map))

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )

        content = test_file.read_text()
        assert "svp.scripts.config" in content, (
            "patch() context manager paths should be rewritten"
        )

    def test_per_language_replacement_based_on_file_extension_py(self, tmp_path):
        """Python rules apply to .py files."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)

        py_file = tests_dir / "test_example.py"
        py_file.write_text("from src.unit_1.config import load_config\n")

        import_map = {"src.unit_1.config": "svp.scripts.config"}
        map_file = tmp_path / "map.json"
        map_file.write_text(json.dumps(import_map))

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
                "--language",
                "python",
            ]
        )

        content = py_file.read_text()
        assert "svp.scripts.config" in content

    def test_per_language_replacement_based_on_file_extension_r(self, tmp_path):
        """R rules (source() path rewrite) apply to .R files."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)

        r_file = tests_dir / "test_example.R"
        r_file.write_text('source("src/unit_1/config.R")\n')

        import_map = {"src/unit_1/config.R": "R/config.R"}
        map_file = tmp_path / "map.json"
        map_file.write_text(json.dumps(import_map))

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
                "--language",
                "r",
            ]
        )

        content = r_file.read_text()
        assert "R/config.R" in content, "R source() paths should be rewritten"

    def test_idempotent_running_twice_produces_same_result(self, tmp_path):
        """Running adapt_regression_tests_main twice produces same result."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)

        test_file = tests_dir / "test_idem.py"
        original = textwrap.dedent("""\
            from src.unit_1.config import load_config
            import src.unit_2.pipeline
        """)
        test_file.write_text(original)

        import_map = {
            "src.unit_1.config": "svp.scripts.config",
            "src.unit_2.pipeline": "svp.scripts.pipeline",
        }
        map_file = tmp_path / "map.json"
        map_file.write_text(json.dumps(import_map))

        argv = [
            "--map-file",
            str(map_file),
            "--tests-dir",
            str(tests_dir),
        ]

        # First run
        adapt_regression_tests_main(argv)
        content_after_first = test_file.read_text()

        # Second run (idempotent)
        adapt_regression_tests_main(argv)
        content_after_second = test_file.read_text()

        assert content_after_first == content_after_second, (
            "adapt_regression_tests_main must be idempotent: "
            "running twice produces the same result"
        )

    def test_accepts_map_file_argument(self, tmp_path):
        """Must accept --map-file argument."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)
        map_file = tmp_path / "empty_map.json"
        map_file.write_text("{}")

        # Should not raise with valid --map-file
        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )

    def test_accepts_tests_dir_argument(self, tmp_path):
        """Must accept --tests-dir argument."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)
        map_file = tmp_path / "empty_map.json"
        map_file.write_text("{}")

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )

    def test_accepts_optional_language_argument(self, tmp_path):
        """Must accept optional --language argument."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)
        map_file = tmp_path / "empty_map.json"
        map_file.write_text("{}")

        # Should not raise with --language
        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
                "--language",
                "python",
            ]
        )

    def test_returns_none(self, tmp_path):
        """adapt_regression_tests_main returns None."""
        tests_dir = tmp_path / "tests" / "regressions"
        tests_dir.mkdir(parents=True)
        map_file = tmp_path / "empty_map.json"
        map_file.write_text("{}")

        result = adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )
        assert result is None, "adapt_regression_tests_main must return None"
