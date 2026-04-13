"""Unit 23: Utility Agent Definitions and Assembly Dispatch -- complete test suite.

Synthetic data assumptions:
- PROJECT_ASSEMBLERS is a Dict[str, Callable] mapping language IDs ("python", "r")
  to their respective assembler functions. Each assembler takes (project_root: Path,
  profile: Dict[str, Any], assembly_config: Dict[str, Any]) and returns a Path.
- GIT_REPO_AGENT_DEFINITION, CHECKLIST_GENERATION_AGENT_DEFINITION,
  REGRESSION_ADAPTATION_AGENT_DEFINITION, ORACLE_AGENT_DEFINITION are non-empty
  markdown strings containing structured agent definitions.
- assemble_python_project creates a directory at {project_root.parent}/{project_name}-repo
  with pyproject.toml, module paths, __init__.py files, and layout-specific structure.
  If the target already exists, it is renamed to .bak.YYYYMMDD-HHMMSS.
- assemble_r_project creates an R package directory with R/, man/, tests/testthat/,
  DESCRIPTION, and NAMESPACE files.
- generate_assembly_map reads blueprint_prose.md from blueprint_dir, extracts
  "<- Unit N" annotations, and produces a bidirectional mapping dict with keys
  single top-level "repo_to_workspace" key (Bug S3-111). Written to .svp/assembly_map.json.
  Staleness invariant: every value matches ^src/unit_\\d+/stub\\.py$ AND points
  at a file on disk. Relationship is many-to-one. Completeness: every annotation produces an entry; missing
  entries raise ValueError.
- adapt_regression_tests_main is a CLI entry point that accepts --map-file,
  --tests-dir, and --language. It reads an import map, applies text replacements
  for Python import patterns (from X import Y, import X, @patch("X.Y"),
  patch("X.Y")) and R source() path rewrites. It is idempotent.
- Profiles used in tests are synthetic dicts with fields drawn from Unit 3 schema:
  delivery.python.source_layout (one of "conventional", "flat", "svp_native"),
  delivery.python.entry_points (bool), project metadata fields.
- assembly_config dicts contain project_name (str), assembly_map (dict), and
  language-specific configuration.
- blueprint_prose.md contains indented file tree lines with "<- Unit N" annotations
  mapping workspace paths to repository paths.
- regression_test_import_map.json maps old import paths to new import paths.
- Tests use tmp_path for filesystem operations. No external dependencies.
"""

import json
import re
import textwrap
from pathlib import Path

import pytest

from generate_assembly_map import (
    CHECKLIST_GENERATION_AGENT_DEFINITION,
    GIT_REPO_AGENT_DEFINITION,
    ORACLE_AGENT_DEFINITION,
    PROJECT_ASSEMBLERS,
    REGRESSION_ADAPTATION_AGENT_DEFINITION,
    adapt_regression_tests_main,
    assemble_plugin_project,
    assemble_python_project,
    assemble_r_project,
    generate_assembly_map,
)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def definition_contains(
    definition: str, phrase: str, case_sensitive: bool = True
) -> bool:
    """Check whether a definition string contains the given phrase."""
    if case_sensitive:
        return phrase in definition
    return phrase.lower() in definition.lower()


def definition_matches(definition: str, pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in the definition string."""
    return re.findall(pattern, definition, flags)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def python_profile():
    """Synthetic Python profile with delivery configuration."""
    return {
        "archetype": "pure_python",
        "language": {
            "primary": "python",
            "secondary": None,
            "components": [],
            "communication": None,
            "notebooks": False,
        },
        "delivery": {
            "python": {
                "source_layout": "conventional",
                "entry_points": True,
            },
        },
        "quality": {},
        "testing": {},
        "readme": {},
        "license": "MIT",
        "vcs": {"provider": "github"},
        "pipeline": {},
    }


@pytest.fixture
def r_profile():
    """Synthetic R profile with delivery configuration."""
    return {
        "archetype": "pure_r",
        "language": {
            "primary": "r",
            "secondary": None,
            "components": [],
            "communication": None,
            "notebooks": False,
        },
        "delivery": {
            "r": {
                "roxygen2": True,
            },
        },
        "quality": {},
        "testing": {},
        "readme": {},
        "license": "GPL-3",
        "vcs": {"provider": "github"},
        "pipeline": {},
    }


@pytest.fixture
def assembly_config_python():
    """Synthetic assembly config for a Python project. (Bug S3-111 schema.)"""
    return {
        "project_name": "myproject",
        "assembly_map": {
            "repo_to_workspace": {
                "src/myproject/core.py": "src/unit_1/stub.py",
                "src/myproject/utils.py": "src/unit_2/stub.py",
            },
        },
    }


@pytest.fixture
def assembly_config_r():
    """Synthetic assembly config for an R project. (Bug S3-111 schema.)"""
    return {
        "project_name": "mypackage",
        "assembly_map": {
            "repo_to_workspace": {
                "R/core.R": "src/unit_1/stub.py",
                "R/utils.R": "src/unit_2/stub.py",
            },
        },
    }


@pytest.fixture
def blueprint_prose_content():
    """Synthetic blueprint_prose.md content with Unit annotations."""
    return textwrap.dedent("""\
        # Project File Tree

        ```
        svp/
          scripts/
            core.py          <- Unit 1
            utils.py         <- Unit 2
            helpers.py       <- Unit 3
          tests/
            test_core.py     <- Unit 10
        ```
    """)


@pytest.fixture
def blueprint_dir(tmp_path, blueprint_prose_content):
    """Create a blueprint directory with blueprint_prose.md."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_prose.md").write_text(blueprint_prose_content)
    return bp_dir


@pytest.fixture
def project_root(tmp_path):
    """Create a synthetic project root directory."""
    root = tmp_path / "myproject"
    root.mkdir()
    svp_dir = root / ".svp"
    svp_dir.mkdir()
    return root


@pytest.fixture
def regression_tests_dir(tmp_path):
    """Create a directory with synthetic regression test files."""
    tests_dir = tmp_path / "tests" / "regressions"
    tests_dir.mkdir(parents=True)

    python_test = tests_dir / "test_regression_001.py"
    python_test.write_text(
        textwrap.dedent("""\
        from src.unit_1.core import process_data
        import src.unit_2.utils as utils
        from unittest.mock import patch

        @patch("src.unit_1.core.process_data")
        def test_regression_patched(mock_proc):
            pass

        def test_regression_inline_patch():
            with patch("src.unit_2.utils.helper") as m:
                pass
    """)
    )

    r_test = tests_dir / "test_regression_002.R"
    r_test.write_text(
        textwrap.dedent("""\
        source("src/unit_1/core.R")
        source("src/unit_2/utils.R")

        test_that("regression test works", {
            expect_equal(1, 1)
        })
    """)
    )

    return tests_dir


@pytest.fixture
def import_map_file(tmp_path):
    """Create a synthetic regression_test_import_map.json."""
    map_data = {
        "src.unit_1.core": "myproject.core",
        "src.unit_2.utils": "myproject.utils",
        "src/unit_1/core.R": "R/core.R",
        "src/unit_2/utils.R": "R/utils.R",
    }
    map_path = tmp_path / "regression_test_import_map.json"
    map_path.write_text(json.dumps(map_data))
    return map_path


# ===========================================================================
# PROJECT_ASSEMBLERS dispatch table
# ===========================================================================


class TestProjectAssemblersStructure:
    """PROJECT_ASSEMBLERS must be a dict mapping language IDs to assembler callables."""

    def test_project_assemblers_is_dict(self):
        assert isinstance(PROJECT_ASSEMBLERS, dict)

    def test_project_assemblers_has_python_key(self):
        """Dispatch table must include 'python' key."""
        assert "python" in PROJECT_ASSEMBLERS

    def test_project_assemblers_has_r_key(self):
        """Dispatch table must include 'r' key."""
        assert "r" in PROJECT_ASSEMBLERS

    def test_python_assembler_is_callable(self):
        """The 'python' entry must be a callable."""
        assert callable(PROJECT_ASSEMBLERS["python"])

    def test_r_assembler_is_callable(self):
        """The 'r' entry must be a callable."""
        assert callable(PROJECT_ASSEMBLERS["r"])

    def test_python_key_maps_to_assemble_python_project(self):
        """The 'python' key must dispatch to assemble_python_project."""
        assert PROJECT_ASSEMBLERS["python"] is assemble_python_project

    def test_r_key_maps_to_assemble_r_project(self):
        """The 'r' key must dispatch to assemble_r_project."""
        assert PROJECT_ASSEMBLERS["r"] is assemble_r_project

    def test_keys_are_language_ids(self):
        """All keys in PROJECT_ASSEMBLERS should be lowercase language identifiers."""
        for key in PROJECT_ASSEMBLERS:
            assert isinstance(key, str)
            assert key == key.lower(), f"Key '{key}' should be lowercase language ID"

    def test_project_assemblers_has_claude_code_plugin_key(self):
        """Dispatch table must include 'claude_code_plugin' key (Bug S3-90).

        Spec Section 35.6 explicitly states the gol-plugin test project exercises
        PROJECT_ASSEMBLERS['claude_code_plugin']. This entry is required for E-mode
        oracle verification of the claude_code_plugin archetype.
        """
        assert "claude_code_plugin" in PROJECT_ASSEMBLERS, (
            "PROJECT_ASSEMBLERS missing 'claude_code_plugin' key -- "
            "spec Section 35.6 requires it for GoL plugin E-mode oracle verification"
        )

    def test_plugin_assembler_is_callable(self):
        """The 'claude_code_plugin' entry must be a callable (Bug S3-90)."""
        assert callable(PROJECT_ASSEMBLERS["claude_code_plugin"])

    def test_plugin_key_maps_to_assemble_plugin_project(self):
        """The 'claude_code_plugin' key must dispatch to assemble_plugin_project (Bug S3-90)."""
        assert PROJECT_ASSEMBLERS["claude_code_plugin"] is assemble_plugin_project


class TestAssemblePluginProject:
    """assemble_plugin_project creates a Claude Code plugin repository structure (Bug S3-90)."""

    @pytest.fixture
    def plugin_profile(self):
        return {
            "name": "gol-plugin",
            "archetype": "claude_code_plugin",
            "language": {"primary": "python"},
            "delivery": {"python": {"source_layout": "flat", "entry_points": False}},
            "quality": {"python": {}},
        }

    @pytest.fixture
    def plugin_assembly_config(self):
        return {
            "project_name": "gol-plugin",
            "description": "GoL plugin",
        }

    def test_returns_path(self, tmp_path, plugin_profile, plugin_assembly_config):
        """assemble_plugin_project returns a Path object."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert isinstance(result, Path)

    def test_creates_repo_directory(self, tmp_path, plugin_profile, plugin_assembly_config):
        """assemble_plugin_project creates the repo directory at parent/{project_name}-repo."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert result.exists()
        assert result.name == "gol-plugin-repo"

    def test_creates_root_claude_plugin_dir(
        self, tmp_path, plugin_profile, plugin_assembly_config
    ):
        """Repo root must have .claude-plugin/ directory for marketplace.json."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert (result / ".claude-plugin").is_dir()

    def test_creates_plugin_subdirectory(
        self, tmp_path, plugin_profile, plugin_assembly_config
    ):
        """Plugin subdirectory (plugin-name/) must be created inside repo root."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        plugin_dir = result / "gol-plugin"
        assert plugin_dir.is_dir()

    def test_creates_plugin_manifest_dir(
        self, tmp_path, plugin_profile, plugin_assembly_config
    ):
        """Plugin subdirectory must have .claude-plugin/ for plugin.json."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert (result / "gol-plugin" / ".claude-plugin").is_dir()

    def test_creates_agents_directory(
        self, tmp_path, plugin_profile, plugin_assembly_config
    ):
        """Plugin subdirectory must have agents/ directory."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert (result / "gol-plugin" / "agents").is_dir()

    def test_creates_commands_directory(
        self, tmp_path, plugin_profile, plugin_assembly_config
    ):
        """Plugin subdirectory must have commands/ directory."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert (result / "gol-plugin" / "commands").is_dir()

    def test_creates_skills_directory(
        self, tmp_path, plugin_profile, plugin_assembly_config
    ):
        """Plugin subdirectory must have skills/ directory."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        result = assemble_plugin_project(
            project_root, plugin_profile, plugin_assembly_config
        )
        assert (result / "gol-plugin" / "skills").is_dir()


# ===========================================================================
# assemble_python_project
# ===========================================================================


class TestAssemblePythonProjectBasic:
    """assemble_python_project creates a Python project repository structure."""

    def test_returns_path(self, project_root, python_profile, assembly_config_python):
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        assert isinstance(result, Path)

    def test_target_directory_name(
        self, project_root, python_profile, assembly_config_python
    ):
        """Target directory is at {project_root.parent}/{project_name}-repo."""
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        expected_name = f"{assembly_config_python['project_name']}-repo"
        assert result.name == expected_name
        assert result.parent == project_root.parent

    def test_target_directory_exists(
        self, project_root, python_profile, assembly_config_python
    ):
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        assert result.exists()
        assert result.is_dir()

    def test_creates_pyproject_toml(
        self, project_root, python_profile, assembly_config_python
    ):
        """Must generate pyproject.toml in the created repository."""
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        assert (result / "pyproject.toml").exists()

    def test_creates_init_files(
        self, project_root, python_profile, assembly_config_python
    ):
        """Must create __init__.py files for Python package structure."""
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        # At least one __init__.py should exist in the repository
        init_files = list(result.rglob("__init__.py"))
        assert len(init_files) > 0, "No __init__.py files found in assembled project"


class TestAssemblePythonProjectLayouts:
    """Source layout must match profile.delivery.python.source_layout."""

    def test_conventional_layout_creates_src_dir(
        self, project_root, python_profile, assembly_config_python
    ):
        """conventional layout: src/packagename/ structure."""
        python_profile["delivery"]["python"]["source_layout"] = "conventional"
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        src_dir = result / "src"
        assert src_dir.exists(), "Conventional layout must have src/ directory"

    def test_flat_layout_creates_package_dir(
        self, project_root, python_profile, assembly_config_python
    ):
        """flat layout: packagename/ structure (no src/ wrapper)."""
        python_profile["delivery"]["python"]["source_layout"] = "flat"
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        pkg_name = assembly_config_python["project_name"]
        pkg_dir = result / pkg_name
        assert pkg_dir.exists(), f"Flat layout must have {pkg_name}/ directory"

    def test_svp_native_layout_creates_scripts_dir(
        self, project_root, python_profile, assembly_config_python
    ):
        """svp_native layout: scripts/ structure."""
        python_profile["delivery"]["python"]["source_layout"] = "svp_native"
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        scripts_dir = result / "scripts"
        assert scripts_dir.exists(), "svp_native layout must have scripts/ directory"


class TestAssemblePythonProjectEntryPoints:
    """Entry points in pyproject.toml when configured."""

    def test_entry_points_when_enabled(
        self, project_root, python_profile, assembly_config_python
    ):
        """pyproject.toml should contain entry points when profile enables them."""
        python_profile["delivery"]["python"]["entry_points"] = True
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        toml_content = (result / "pyproject.toml").read_text()
        assert "entry" in toml_content.lower() or "scripts" in toml_content.lower(), (
            "pyproject.toml should declare entry points when entry_points is True"
        )

    def test_no_entry_points_when_disabled(
        self, project_root, python_profile, assembly_config_python
    ):
        """pyproject.toml should not contain entry points when profile disables them."""
        python_profile["delivery"]["python"]["entry_points"] = False
        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )
        toml_content = (result / "pyproject.toml").read_text()
        # No [project.scripts] or [project.gui-scripts] section
        assert "[project.scripts]" not in toml_content, (
            "pyproject.toml should not have [project.scripts] when entry_points is False"
        )


class TestAssemblePythonProjectBackup:
    """Existing target directory is renamed to .bak.YYYYMMDD-HHMMSS."""

    def test_renames_existing_target_to_bak(
        self, project_root, python_profile, assembly_config_python
    ):
        """If target exists, rename it to .bak.YYYYMMDD-HHMMSS before creating new."""
        target_name = f"{assembly_config_python['project_name']}-repo"
        existing_target = project_root.parent / target_name
        existing_target.mkdir()
        sentinel = existing_target / "sentinel.txt"
        sentinel.write_text("existing content")

        assemble_python_project(project_root, python_profile, assembly_config_python)

        # The new target should exist
        assert existing_target.exists()
        # The backup should exist with .bak.YYYYMMDD-HHMMSS pattern
        bak_dirs = [
            d
            for d in project_root.parent.iterdir()
            if d.name.startswith(f"{target_name}.bak.")
        ]
        assert len(bak_dirs) == 1, "Exactly one backup directory should be created"
        assert re.match(
            rf"^{re.escape(target_name)}\.bak\.\d{{8}}-\d{{6}}$",
            bak_dirs[0].name,
        ), (
            f"Backup dir name '{bak_dirs[0].name}' does not match .bak.YYYYMMDD-HHMMSS pattern"
        )

    def test_backup_preserves_original_content(
        self, project_root, python_profile, assembly_config_python
    ):
        """Backup directory should contain the original files."""
        target_name = f"{assembly_config_python['project_name']}-repo"
        existing_target = project_root.parent / target_name
        existing_target.mkdir()
        sentinel = existing_target / "sentinel.txt"
        sentinel.write_text("original content")

        assemble_python_project(project_root, python_profile, assembly_config_python)

        bak_dirs = [
            d
            for d in project_root.parent.iterdir()
            if d.name.startswith(f"{target_name}.bak.")
        ]
        assert (bak_dirs[0] / "sentinel.txt").read_text() == "original content"


class TestAssemblePythonProjectAssemblyMap:
    """assemble_python_project reads assembly_map.json for path mapping."""

    def test_uses_assembly_map_for_file_placement(
        self, project_root, python_profile, assembly_config_python
    ):
        """Files should be placed according to the assembly map. (Bug S3-111 schema:
        source stubs are referenced via `repo_to_workspace` values.)"""
        # Create source stub files that the assembly map references
        for ws_path in set(assembly_config_python["assembly_map"]["repo_to_workspace"].values()):
            src_file = project_root / ws_path
            src_file.parent.mkdir(parents=True, exist_ok=True)
            src_file.write_text(f"# content for {ws_path}")

        result = assemble_python_project(
            project_root, python_profile, assembly_config_python
        )

        # Verify that at least the repo structure was created
        assert result.exists()


# ===========================================================================
# assemble_r_project
# ===========================================================================


class TestAssembleRProjectBasic:
    """assemble_r_project creates an R package repository structure."""

    def test_returns_path(self, project_root, r_profile, assembly_config_r):
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert isinstance(result, Path)

    def test_target_directory_exists(self, project_root, r_profile, assembly_config_r):
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert result.exists()
        assert result.is_dir()

    def test_creates_r_directory(self, project_root, r_profile, assembly_config_r):
        """Must create R/ directory for R source files."""
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert (result / "R").exists()
        assert (result / "R").is_dir()

    def test_creates_man_directory(self, project_root, r_profile, assembly_config_r):
        """Must create man/ directory for documentation."""
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert (result / "man").exists()
        assert (result / "man").is_dir()

    def test_creates_testthat_directory(
        self, project_root, r_profile, assembly_config_r
    ):
        """Must create tests/testthat/ directory for tests."""
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert (result / "tests" / "testthat").exists()
        assert (result / "tests" / "testthat").is_dir()

    def test_creates_description_file(self, project_root, r_profile, assembly_config_r):
        """Must generate DESCRIPTION file."""
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert (result / "DESCRIPTION").exists()

    def test_creates_namespace_file(self, project_root, r_profile, assembly_config_r):
        """Must generate NAMESPACE file."""
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        assert (result / "NAMESPACE").exists()


class TestAssembleRProjectRoxygen:
    """Roxygen2 documentation when configured."""

    def test_roxygen_when_configured(self, project_root, r_profile, assembly_config_r):
        """When roxygen2 is True, roxygen documentation artifacts should be present."""
        r_profile["delivery"]["r"]["roxygen2"] = True
        result = assemble_r_project(project_root, r_profile, assembly_config_r)
        # NAMESPACE should reference roxygen or man/ should have .Rd files
        namespace_content = (result / "NAMESPACE").read_text()
        man_files = list((result / "man").rglob("*.Rd"))
        assert "roxygen" in namespace_content.lower() or len(man_files) > 0, (
            "Roxygen2 documentation should be present when configured"
        )


# ===========================================================================
# generate_assembly_map
# ===========================================================================


class TestGenerateAssemblyMapBasic:
    """generate_assembly_map parses blueprint_prose.md and produces bidirectional mapping."""

    def test_returns_dict(self, blueprint_dir, project_root):
        result = generate_assembly_map(blueprint_dir, project_root)
        assert isinstance(result, dict)

    def test_has_repo_to_workspace_key(self, blueprint_dir, project_root):
        result = generate_assembly_map(blueprint_dir, project_root)
        assert "repo_to_workspace" in result

    def test_no_workspace_to_repo_key(self, blueprint_dir, project_root):
        """Bug S3-111: the legacy forward direction must not reappear."""
        result = generate_assembly_map(blueprint_dir, project_root)
        assert "workspace_to_repo" not in result

    def test_only_one_top_level_key(self, blueprint_dir, project_root):
        """Bug S3-111: the map has exactly one top-level key."""
        result = generate_assembly_map(blueprint_dir, project_root)
        assert list(result.keys()) == ["repo_to_workspace"]

    def test_repo_to_workspace_is_dict(self, blueprint_dir, project_root):
        result = generate_assembly_map(blueprint_dir, project_root)
        assert isinstance(result["repo_to_workspace"], dict)

    def test_extracts_unit_annotations(self, blueprint_dir, project_root):
        """Every '<- Unit N' annotation line should produce a mapping entry."""
        result = generate_assembly_map(blueprint_dir, project_root)
        # The blueprint_prose fixture has 4 annotations (Units 1, 2, 3, 10)
        assert len(result["repo_to_workspace"]) == 4, (
            f"Expected 4 repo_to_workspace entries, got {len(result['repo_to_workspace'])}"
        )

    def test_extracts_correct_unit_numbers(self, blueprint_dir, project_root):
        """Mapping values (source stubs) should reference the correct unit numbers."""
        result = generate_assembly_map(blueprint_dir, project_root)
        ws_values = list(result["repo_to_workspace"].values())
        # Should contain stubs for units 1, 2, 3, 10
        unit_refs = []
        for value in ws_values:
            match = re.search(r"unit_(\d+)", value)
            if match:
                unit_refs.append(int(match.group(1)))
        for expected_unit in [1, 2, 3, 10]:
            assert expected_unit in unit_refs, (
                f"Unit {expected_unit} annotation not found in repo_to_workspace values"
            )


class TestGenerateAssemblyMapStalenessInvariant:
    """Bug S3-111: every value in repo_to_workspace must match the stub.py
    naming convention and the relationship is many-to-one. Replaces the
    pre-S3-111 bijectivity tests (which were meaningless post-S3-98 because
    the forward direction could not represent the many-to-one layout)."""

    def test_every_value_matches_stub_py_pattern(self, blueprint_dir, project_root):
        """Every value must match ^src/unit_\\d+/stub\\.py$ (Bug S3-111)."""
        result = generate_assembly_map(blueprint_dir, project_root)
        stub_re = re.compile(r"^src/unit_\d+/stub\.py$")
        bad = [v for v in result["repo_to_workspace"].values() if not stub_re.match(v)]
        assert not bad, f"Non-stub source paths in repo_to_workspace: {bad}"

    def test_relationship_can_be_many_to_one(self, tmp_path):
        """Multiple deployed files from one unit share one stub (Bug S3-111)."""
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text(textwrap.dedent("""\
            # File Tree

            ```
            svp/
              agents/
                git_repo_agent.md      <- Unit 23
                oracle_agent.md        <- Unit 23
              scripts/
                generate_assembly_map.py <- Unit 23
            ```
        """))
        proj = tmp_path / "project"
        proj.mkdir()
        (proj / ".svp").mkdir()

        result = generate_assembly_map(bp_dir, proj)
        r2w = result["repo_to_workspace"]
        # All three deployed files point at src/unit_23/stub.py.
        assert len(r2w) == 3
        assert set(r2w.values()) == {"src/unit_23/stub.py"}


class TestGenerateAssemblyMapCompleteness:
    """Completeness invariant: missing annotations raise ValueError."""

    def test_raises_valueerror_for_missing_annotation(self, tmp_path):
        """If an annotation references a unit with no resolvable path, raise ValueError."""
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        # Write a malformed blueprint with an annotation but no parseable path
        (bp_dir / "blueprint_prose.md").write_text(
            textwrap.dedent("""\
            # File Tree

            ```
                         <- Unit 99
            ```
        """)
        )
        proj_root = tmp_path / "project"
        proj_root.mkdir()
        (proj_root / ".svp").mkdir()

        with pytest.raises(ValueError):
            generate_assembly_map(bp_dir, proj_root)


class TestGenerateAssemblyMapDiskWrite:
    """Mapping dict is also written to .svp/assembly_map.json."""

    def test_writes_assembly_map_json(self, blueprint_dir, project_root):
        result = generate_assembly_map(blueprint_dir, project_root)
        map_path = project_root / ".svp" / "assembly_map.json"
        assert map_path.exists(), "assembly_map.json should be written to .svp/"

    def test_written_json_matches_return_value(self, blueprint_dir, project_root):
        result = generate_assembly_map(blueprint_dir, project_root)
        map_path = project_root / ".svp" / "assembly_map.json"
        written = json.loads(map_path.read_text())
        assert written == result, "Written JSON should match the returned dict"

    def test_written_json_has_correct_structure(self, blueprint_dir, project_root):
        """Bug S3-111: the written JSON has exactly one top-level key."""
        generate_assembly_map(blueprint_dir, project_root)
        map_path = project_root / ".svp" / "assembly_map.json"
        written = json.loads(map_path.read_text())
        assert list(written.keys()) == ["repo_to_workspace"]
        assert isinstance(written["repo_to_workspace"], dict)
        assert "workspace_to_repo" not in written


# ===========================================================================
# GIT_REPO_AGENT_DEFINITION
# ===========================================================================


class TestGitRepoAgentDefinitionStructure:
    """GIT_REPO_AGENT_DEFINITION must be a non-empty markdown string."""

    def test_is_string(self):
        assert isinstance(GIT_REPO_AGENT_DEFINITION, str)

    def test_is_nonempty(self):
        assert len(GIT_REPO_AGENT_DEFINITION.strip()) > 0

    def test_contains_markdown_headings(self):
        assert re.search(r"^#+\s+", GIT_REPO_AGENT_DEFINITION, re.MULTILINE)


class TestGitRepoAgentDefinitionContent:
    """GIT_REPO_AGENT_DEFINITION references assembly mapping, commit order, and delivery."""

    def test_mentions_assembly_mapping(self):
        """Definition must reference assembly mapping rules."""
        assert definition_contains(
            GIT_REPO_AGENT_DEFINITION, "assembly", case_sensitive=False
        )

    # --- Bug S3-112: Delivered Repo Location binding ---

    def test_mentions_canonical_path_convention(self):
        """Definition must state the {project_root.parent}/{project_name}-repo convention."""
        assert "Delivered Repo Location" in GIT_REPO_AGENT_DEFINITION
        assert "{project_root.parent}/{project_name}-repo" in GIT_REPO_AGENT_DEFINITION

    def test_mentions_all_four_assembler_helpers_by_name(self):
        """All four language-specific assembler helpers must be named."""
        assert "assemble_python_project" in GIT_REPO_AGENT_DEFINITION
        assert "assemble_r_project" in GIT_REPO_AGENT_DEFINITION
        assert "assemble_plugin_project" in GIT_REPO_AGENT_DEFINITION
        assert "assemble_mixed_project" in GIT_REPO_AGENT_DEFINITION

    def test_forbids_delivered_directory_as_destination(self):
        """Definition must forbid the anti-pattern `./delivered/` and related names."""
        # The prohibition block mentions the forbidden names.
        assert "`delivered/`" in GIT_REPO_AGENT_DEFINITION
        assert "`delivered_repo/`" in GIT_REPO_AGENT_DEFINITION
        # And it must say MUST NOT somewhere in proximity.
        assert "MUST NOT" in GIT_REPO_AGENT_DEFINITION

    def test_forbids_manual_pipeline_state_edit(self):
        """Definition must forbid direct edits to .svp/pipeline_state.json."""
        assert ".svp/pipeline_state.json" in GIT_REPO_AGENT_DEFINITION
        # The prohibition section must mention dispatch-step auto-update.
        assert "dispatch" in GIT_REPO_AGENT_DEFINITION.lower()

    def test_references_bug_s3_112(self):
        """Definition must reference Bug S3-112 for traceability."""
        assert "S3-112" in GIT_REPO_AGENT_DEFINITION

    def test_mentions_conventional_commits(self):
        """Definition must reference conventional commits for commit order."""
        assert definition_contains(
            GIT_REPO_AGENT_DEFINITION, "conventional commit", case_sensitive=False
        ) or definition_contains(
            GIT_REPO_AGENT_DEFINITION, "commit", case_sensitive=False
        )

    def test_mentions_delivery_compliance(self):
        """Definition must reference delivery compliance awareness."""
        assert definition_contains(
            GIT_REPO_AGENT_DEFINITION, "delivery", case_sensitive=False
        )

    def test_mentions_readme_generation(self):
        """Definition must reference README generation."""
        assert definition_contains(
            GIT_REPO_AGENT_DEFINITION, "readme", case_sensitive=False
        )

    def test_mentions_quality_config_generation(self):
        """Definition must reference quality config generation."""
        assert definition_contains(
            GIT_REPO_AGENT_DEFINITION, "quality", case_sensitive=False
        )

    def test_mentions_iteration_limit(self):
        """Definition must reference bounded fix cycle with iteration_limit."""
        assert (
            definition_contains(
                GIT_REPO_AGENT_DEFINITION, "iteration", case_sensitive=False
            )
            or definition_contains(
                GIT_REPO_AGENT_DEFINITION, "bound", case_sensitive=False
            )
            or definition_contains(
                GIT_REPO_AGENT_DEFINITION, "limit", case_sensitive=False
            )
        )

    def test_status_repo_assembly_complete(self):
        """Definition must reference REPO_ASSEMBLY_COMPLETE status."""
        assert definition_contains(GIT_REPO_AGENT_DEFINITION, "REPO_ASSEMBLY_COMPLETE")


# ===========================================================================
# CHECKLIST_GENERATION_AGENT_DEFINITION
# ===========================================================================


class TestChecklistGenerationAgentDefinitionStructure:
    """CHECKLIST_GENERATION_AGENT_DEFINITION must be a non-empty markdown string."""

    def test_is_string(self):
        assert isinstance(CHECKLIST_GENERATION_AGENT_DEFINITION, str)

    def test_is_nonempty(self):
        assert len(CHECKLIST_GENERATION_AGENT_DEFINITION.strip()) > 0

    def test_contains_markdown_headings(self):
        assert re.search(r"^#+\s+", CHECKLIST_GENERATION_AGENT_DEFINITION, re.MULTILINE)


class TestChecklistGenerationAgentDefinitionContent:
    """CHECKLIST_GENERATION_AGENT_DEFINITION produces two checklists for Stage 2."""

    def test_mentions_alignment_checker_checklist(self):
        """Definition must reference alignment_checker_checklist.md."""
        assert definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            "alignment_checker_checklist",
            case_sensitive=False,
        ) or definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            "alignment checker checklist",
            case_sensitive=False,
        )

    def test_mentions_blueprint_author_checklist(self):
        """Definition must reference blueprint_author_checklist.md."""
        assert definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            "blueprint_author_checklist",
            case_sensitive=False,
        ) or definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            "blueprint author checklist",
            case_sensitive=False,
        )

    def test_mentions_stage_2(self):
        """Definition must reference Stage 2 agents as consumers."""
        assert definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            "stage 2",
            case_sensitive=False,
        ) or definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            "Stage 2",
        )

    def test_status_checklists_complete(self):
        """Definition must reference CHECKLISTS_COMPLETE status."""
        assert definition_contains(
            CHECKLIST_GENERATION_AGENT_DEFINITION, "CHECKLISTS_COMPLETE"
        )

    def test_produces_exactly_two_checklists(self):
        """Both checklist filenames must appear in the definition."""
        text = CHECKLIST_GENERATION_AGENT_DEFINITION.lower()
        has_alignment = "alignment" in text and "checklist" in text
        has_blueprint = "blueprint" in text and (
            "author" in text or "checklist" in text
        )
        assert has_alignment and has_blueprint, (
            "Both alignment_checker and blueprint_author checklists must be referenced"
        )


# ===========================================================================
# REGRESSION_ADAPTATION_AGENT_DEFINITION
# ===========================================================================


class TestRegressionAdaptationAgentDefinitionStructure:
    """REGRESSION_ADAPTATION_AGENT_DEFINITION must be a non-empty markdown string."""

    def test_is_string(self):
        assert isinstance(REGRESSION_ADAPTATION_AGENT_DEFINITION, str)

    def test_is_nonempty(self):
        assert len(REGRESSION_ADAPTATION_AGENT_DEFINITION.strip()) > 0

    def test_contains_markdown_headings(self):
        assert re.search(
            r"^#+\s+", REGRESSION_ADAPTATION_AGENT_DEFINITION, re.MULTILINE
        )


class TestRegressionAdaptationAgentDefinitionContent:
    """REGRESSION_ADAPTATION_AGENT_DEFINITION covers import rewrites and change flagging."""

    def test_mentions_import_rewrites(self):
        """Definition must reference import rewriting."""
        assert definition_contains(
            REGRESSION_ADAPTATION_AGENT_DEFINITION,
            "import",
            case_sensitive=False,
        ) and definition_contains(
            REGRESSION_ADAPTATION_AGENT_DEFINITION,
            "rewrite",
            case_sensitive=False,
        )

    def test_mentions_behavioral_change_flagging(self):
        """Definition must reference behavioral change flagging."""
        assert (
            definition_contains(
                REGRESSION_ADAPTATION_AGENT_DEFINITION,
                "behavioral",
                case_sensitive=False,
            )
            or definition_contains(
                REGRESSION_ADAPTATION_AGENT_DEFINITION,
                "change",
                case_sensitive=False,
            )
            and definition_contains(
                REGRESSION_ADAPTATION_AGENT_DEFINITION,
                "flag",
                case_sensitive=False,
            )
        )

    def test_status_adaptation_complete(self):
        """Definition must reference ADAPTATION_COMPLETE status."""
        assert definition_contains(
            REGRESSION_ADAPTATION_AGENT_DEFINITION, "ADAPTATION_COMPLETE"
        )

    def test_status_adaptation_needs_review(self):
        """Definition must reference ADAPTATION_NEEDS_REVIEW status."""
        assert definition_contains(
            REGRESSION_ADAPTATION_AGENT_DEFINITION, "ADAPTATION_NEEDS_REVIEW"
        )


# ===========================================================================
# ORACLE_AGENT_DEFINITION
# ===========================================================================


class TestOracleAgentDefinitionStructure:
    """ORACLE_AGENT_DEFINITION must be a non-empty markdown string."""

    def test_is_string(self):
        assert isinstance(ORACLE_AGENT_DEFINITION, str)

    def test_is_nonempty(self):
        assert len(ORACLE_AGENT_DEFINITION.strip()) > 0

    def test_contains_markdown_headings(self):
        assert re.search(r"^#+\s+", ORACLE_AGENT_DEFINITION, re.MULTILINE)


class TestOracleAgentDefinitionDualMode:
    """Oracle operates in dual mode: E-mode (product testing), F-mode (machinery testing)."""

    def test_mentions_e_mode(self):
        """Definition must reference E-mode or product testing."""
        assert (
            definition_contains(ORACLE_AGENT_DEFINITION, "E-mode", case_sensitive=False)
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "e mode", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "product", case_sensitive=False
            )
        )

    def test_mentions_f_mode(self):
        """Definition must reference F-mode or machinery testing."""
        assert (
            definition_contains(ORACLE_AGENT_DEFINITION, "F-mode", case_sensitive=False)
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "f mode", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "machinery", case_sensitive=False
            )
        )


class TestOracleAgentDefinitionFourPhases:
    """Oracle has four-phase structure: dry_run, gate_a, green_run, gate_b/exit."""

    def test_mentions_dry_run_phase(self):
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "dry_run", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "dry run", case_sensitive=False
        )

    def test_mentions_gate_a_phase(self):
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "gate_a", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "gate a", case_sensitive=False
        )

    def test_mentions_green_run_phase(self):
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "green_run", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "green run", case_sensitive=False
        )

    def test_mentions_gate_b_phase(self):
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "gate_b", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "gate b", case_sensitive=False
        )


class TestOracleAgentDefinitionPhaseTransitions:
    """Oracle phase transitions are driven by routing dispatch."""

    def test_dry_run_to_gate_a_transition(self):
        """dry_run -> gate_a on ORACLE_DRY_RUN_COMPLETE."""
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ORACLE_DRY_RUN_COMPLETE")

    def test_gate_a_to_green_run_transition(self):
        """gate_a -> green_run on APPROVE TRAJECTORY."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "APPROVE TRAJECTORY", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "approve trajectory", case_sensitive=False
        )

    def test_green_run_to_gate_b_transition(self):
        """green_run -> gate_b when oracle signals fix plan."""
        text_lower = ORACLE_AGENT_DEFINITION.lower()
        assert "fix plan" in text_lower or "gate_b" in text_lower

    def test_gate_b_to_exit_on_approve_fix(self):
        """gate_b -> exit on APPROVE FIX."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "APPROVE FIX", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "approve fix", case_sensitive=False
        )

    def test_gate_b_to_exit_on_abort(self):
        """gate_b -> exit on ABORT."""
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ABORT")

    def test_green_run_to_exit_on_all_clear(self):
        """green_run -> exit on ORACLE_ALL_CLEAR (no bugs found)."""
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ORACLE_ALL_CLEAR")


class TestOracleAgentDefinitionMultiTurnSession:
    """Oracle green_run + Gate B is a multi-turn session maintaining state."""

    def test_mentions_multi_turn_or_session(self):
        """Definition must reference multi-turn session or session state."""
        text_lower = ORACLE_AGENT_DEFINITION.lower()
        assert (
            "multi-turn" in text_lower
            or "multi turn" in text_lower
            or "session" in text_lower
        )


class TestOracleAgentDefinitionSurrogateHuman:
    """Surrogate human protocol for internal /svp:bug calls."""

    def test_mentions_surrogate_human(self):
        """Definition must reference surrogate human protocol."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "surrogate", case_sensitive=False
        )

    def test_mentions_auto_responds_at_gates(self):
        """Definition must reference auto-responding at Gates 6.0, 6.1, 6.2."""
        text = ORACLE_AGENT_DEFINITION
        assert (
            "6.0" in text
            or "6.1" in text
            or "6.2" in text
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "auto-respond", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "auto respond", case_sensitive=False
            )
        )


class TestOracleAgentDefinitionContextBudget:
    """Context budget management with selective analysis."""

    def test_mentions_context_budget(self):
        """Definition must reference context budget management."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "context", case_sensitive=False
        ) and (
            definition_contains(ORACLE_AGENT_DEFINITION, "budget", case_sensitive=False)
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "selective", case_sensitive=False
            )
        )


class TestOracleAgentDefinitionRunLedger:
    """Run ledger as cross-invocation memory."""

    def test_mentions_run_ledger(self):
        """Definition must reference run ledger."""
        assert (
            definition_contains(
                ORACLE_AGENT_DEFINITION, "run ledger", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "run_ledger", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "ledger", case_sensitive=False
            )
        )


class TestOracleAgentDefinitionFixVerification:
    """Fix verification: 2 attempts max per bug."""

    def test_mentions_fix_verification_bound(self):
        """Definition must reference 2 attempts max per bug."""
        assert (
            definition_contains(
                ORACLE_AGENT_DEFINITION, "2 attempt", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "two attempt", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "2 max", case_sensitive=False
            )
            or re.search(
                r"(?:2|two)\s+(?:attempt|tries|max)",
                ORACLE_AGENT_DEFINITION,
                re.IGNORECASE,
            )
        )


class TestOracleAgentDefinitionModifyTrajectoryBound:
    """MODIFY TRAJECTORY bound: 3 per invocation."""

    def test_mentions_modify_trajectory_bound(self):
        """Definition must reference MODIFY TRAJECTORY with a bound of 3."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "MODIFY TRAJECTORY", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "modify trajectory", case_sensitive=False
        )

    def test_modify_trajectory_bound_is_three(self):
        """MODIFY TRAJECTORY bound should be 3."""
        text_lower = ORACLE_AGENT_DEFINITION.lower()
        # Look for "3" near "modify trajectory"
        assert (
            re.search(
                r"modify.{0,30}trajectory.{0,30}3|3.{0,30}modify.{0,30}trajectory",
                text_lower,
            )
            or "3 per invocation" in text_lower
            or "three per invocation" in text_lower
        )


class TestOracleAgentDefinitionDiagnosticMap:
    """Diagnostic map entry schema at .svp/oracle_diagnostic_map.json."""

    def test_mentions_diagnostic_map(self):
        """Definition must reference diagnostic map."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "diagnostic_map", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "diagnostic map", case_sensitive=False
        )

    def test_diagnostic_map_event_id_field(self):
        """Definition must reference event_id field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "event_id", case_sensitive=False
        )

    def test_diagnostic_map_classification_field(self):
        """Definition must reference classification field with PASS/FAIL/WARN values."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "classification", case_sensitive=False
        )

    def test_diagnostic_map_observation_field(self):
        """Definition must reference observation field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "observation", case_sensitive=False
        )

    def test_diagnostic_map_expected_field(self):
        """Definition must reference expected field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "expected", case_sensitive=False
        )

    def test_diagnostic_map_affected_artifact_field(self):
        """Definition must reference affected_artifact field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "affected_artifact", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "affected artifact", case_sensitive=False
        )

    def test_diagnostic_map_classification_values(self):
        """Definition must reference PASS, FAIL, WARN classification values."""
        for value in ["PASS", "FAIL", "WARN"]:
            assert definition_contains(ORACLE_AGENT_DEFINITION, value), (
                f"Diagnostic map classification value '{value}' not found in definition"
            )


class TestOracleAgentDefinitionRunLedgerSchema:
    """Run ledger entry schema at .svp/oracle_run_ledger.json."""

    def test_mentions_run_ledger_file(self):
        """Definition must reference oracle_run_ledger.json."""
        assert (
            definition_contains(
                ORACLE_AGENT_DEFINITION, "oracle_run_ledger", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "run_ledger", case_sensitive=False
            )
            or definition_contains(
                ORACLE_AGENT_DEFINITION, "run ledger", case_sensitive=False
            )
        )

    def test_run_ledger_run_number_field(self):
        """Definition must reference run_number field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "run_number", case_sensitive=False
        )

    def test_run_ledger_exit_reason_field(self):
        """Definition must reference exit_reason field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "exit_reason", case_sensitive=False
        )

    def test_run_ledger_exit_reason_values(self):
        """Definition must reference exit reason values: all_clear, fix_applied, human_abort."""
        for value in ["all_clear", "fix_applied", "human_abort"]:
            assert definition_contains(
                ORACLE_AGENT_DEFINITION, value, case_sensitive=False
            ), f"Run ledger exit_reason value '{value}' not found in definition"

    def test_run_ledger_trajectory_summary_field(self):
        """Definition must reference trajectory_summary field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "trajectory_summary", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "trajectory summary", case_sensitive=False
        )

    def test_run_ledger_discoveries_field(self):
        """Definition must reference discoveries field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "discoveries", case_sensitive=False
        )

    def test_run_ledger_fix_targets_field(self):
        """Definition must reference fix_targets field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "fix_targets", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "fix targets", case_sensitive=False
        )

    def test_run_ledger_root_causes_found_field(self):
        """Definition must reference root_causes_found field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "root_causes_found", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "root causes found", case_sensitive=False
        )

    def test_run_ledger_root_causes_resolved_field(self):
        """Definition must reference root_causes_resolved field."""
        assert definition_contains(
            ORACLE_AGENT_DEFINITION, "root_causes_resolved", case_sensitive=False
        ) or definition_contains(
            ORACLE_AGENT_DEFINITION, "root causes resolved", case_sensitive=False
        )


class TestOracleAgentDefinitionStatuses:
    """Oracle status values in the definition."""

    def test_status_oracle_dry_run_complete(self):
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ORACLE_DRY_RUN_COMPLETE")

    def test_status_oracle_fix_applied(self):
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ORACLE_FIX_APPLIED")

    def test_status_oracle_all_clear(self):
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ORACLE_ALL_CLEAR")

    def test_status_oracle_human_abort(self):
        assert definition_contains(ORACLE_AGENT_DEFINITION, "ORACLE_HUMAN_ABORT")


# ===========================================================================
# adapt_regression_tests_main (CLI)
# ===========================================================================


class TestAdaptRegressionTestsMainInterface:
    """adapt_regression_tests_main accepts CLI arguments for regression test adaptation."""

    def test_callable(self):
        """adapt_regression_tests_main must be callable."""
        assert callable(adapt_regression_tests_main)

    def test_accepts_argv_parameter(self):
        """adapt_regression_tests_main accepts an argv parameter defaulting to None."""
        import inspect

        sig = inspect.signature(adapt_regression_tests_main)
        assert "argv" in sig.parameters
        assert sig.parameters["argv"].default is None

    def test_returns_none(self, import_map_file, regression_tests_dir):
        """adapt_regression_tests_main returns None."""
        result = adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        assert result is None


class TestAdaptRegressionTestsMainCliArgs:
    """CLI argument parsing: --map-file, --tests-dir, --language."""

    def test_accepts_map_file_and_tests_dir(
        self, import_map_file, regression_tests_dir
    ):
        """Must accept --map-file and --tests-dir arguments without error."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )

    def test_accepts_language_argument(self, import_map_file, regression_tests_dir):
        """Must accept optional --language argument."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
                "--language",
                "python",
            ]
        )


class TestAdaptRegressionTestsPythonImportRewrites:
    """Python import pattern rewrites: from X import Y, import X, @patch, patch()."""

    def test_rewrites_from_import(self, import_map_file, regression_tests_dir):
        """'from src.unit_1.core import process_data' should be rewritten."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_001.py").read_text()
        assert "from src.unit_1.core import" not in content, (
            "Old 'from src.unit_1.core import' should be rewritten"
        )
        assert "from myproject.core import" in content, (
            "Should be rewritten to 'from myproject.core import'"
        )

    def test_rewrites_import_statement(self, import_map_file, regression_tests_dir):
        """'import src.unit_2.utils' should be rewritten."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_001.py").read_text()
        assert "import src.unit_2.utils" not in content, (
            "Old 'import src.unit_2.utils' should be rewritten"
        )

    def test_rewrites_decorator_patch(self, import_map_file, regression_tests_dir):
        """'@patch("src.unit_1.core.process_data")' should be rewritten."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_001.py").read_text()
        assert 'patch("src.unit_1.core.process_data")' not in content, (
            "Old @patch decorator target should be rewritten"
        )
        assert 'patch("myproject.core.process_data")' in content, (
            'Should be rewritten to patch("myproject.core.process_data")'
        )

    def test_rewrites_inline_patch(self, import_map_file, regression_tests_dir):
        """'patch("src.unit_2.utils.helper")' in context manager should be rewritten."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_001.py").read_text()
        assert 'patch("src.unit_2.utils.helper")' not in content, (
            "Old inline patch target should be rewritten"
        )
        assert 'patch("myproject.utils.helper")' in content, (
            'Should be rewritten to patch("myproject.utils.helper")'
        )


class TestAdaptRegressionTestsRSourceRewrites:
    """R source() path rewrites."""

    def test_rewrites_r_source_paths(self, import_map_file, regression_tests_dir):
        """R source() calls should have paths rewritten."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_002.R").read_text()
        assert 'source("src/unit_1/core.R")' not in content, (
            "Old R source() path should be rewritten"
        )
        assert 'source("src/unit_2/utils.R")' not in content, (
            "Old R source() path should be rewritten"
        )


class TestAdaptRegressionTestsPerLanguageDispatch:
    """Per-language replacements based on file extension."""

    def test_python_rules_applied_to_py_files_only(
        self, import_map_file, regression_tests_dir
    ):
        """Python import rules should only be applied to .py files."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        # R file should NOT have Python-style import rewrites
        r_content = (regression_tests_dir / "test_regression_002.R").read_text()
        assert "from myproject" not in r_content, (
            "Python import syntax should not appear in .R files"
        )

    def test_r_rules_applied_to_r_files_only(
        self, import_map_file, regression_tests_dir
    ):
        """R source() rules should only be applied to .R files."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        # Python file should NOT have R-style source() rewrites
        py_content = (regression_tests_dir / "test_regression_001.py").read_text()
        assert "source(" not in py_content, (
            "R source() syntax should not appear in .py files"
        )


class TestAdaptRegressionTestsIdempotent:
    """Running adapt_regression_tests_main twice produces the same result."""

    def test_idempotent_python(self, import_map_file, regression_tests_dir):
        """Running twice on Python files produces identical output."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        first_pass = (regression_tests_dir / "test_regression_001.py").read_text()

        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        second_pass = (regression_tests_dir / "test_regression_001.py").read_text()

        assert first_pass == second_pass, (
            "Running adapt_regression_tests_main twice should produce identical output"
        )

    def test_idempotent_r(self, import_map_file, regression_tests_dir):
        """Running twice on R files produces identical output."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        first_pass = (regression_tests_dir / "test_regression_002.R").read_text()

        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        second_pass = (regression_tests_dir / "test_regression_002.R").read_text()

        assert first_pass == second_pass, (
            "Running adapt_regression_tests_main twice should produce identical output for R files"
        )


class TestAdaptRegressionTestsMapFileReading:
    """adapt_regression_tests_main reads the import map from the specified file."""

    def test_reads_valid_json_map(self, tmp_path):
        """Must read a valid JSON import map file without error."""
        map_data = {"old.module": "new.module"}
        map_file = tmp_path / "import_map.json"
        map_file.write_text(json.dumps(map_data))
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Create an empty test file so there's something to process
        (tests_dir / "test_empty.py").write_text("# empty test\n")

        adapt_regression_tests_main(
            [
                "--map-file",
                str(map_file),
                "--tests-dir",
                str(tests_dir),
            ]
        )

    def test_preserves_non_matched_content(self, import_map_file, regression_tests_dir):
        """Content that does not match any import pattern should be preserved."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_001.py").read_text()
        # The function/test definitions should be preserved
        assert "def test_regression_patched" in content
        assert "def test_regression_inline_patch" in content

    def test_preserves_r_non_matched_content(
        self, import_map_file, regression_tests_dir
    ):
        """R content that does not match any source() pattern should be preserved."""
        adapt_regression_tests_main(
            [
                "--map-file",
                str(import_map_file),
                "--tests-dir",
                str(regression_tests_dir),
            ]
        )
        content = (regression_tests_dir / "test_regression_002.R").read_text()
        assert "test_that" in content
        assert "expect_equal" in content
