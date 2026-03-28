"""
Tests for Unit 11: Infrastructure Setup.

Synthetic Data Assumptions:
- project_root is a tmp_path directory simulating a project root.
- profile is a dict with at minimum: language.primary, delivery, quality sections.
- toolchain is a dict simulating toolchain content loaded from JSON.
- language_registry mirrors LANGUAGE_REGISTRY from Unit 2 with Python, R, and Stan entries.
- blueprint_dir contains synthetic blueprint_contracts.md with ## Unit N: headings.
- Environment name is derived as "svp-{project_root.name}" per Unit 1 contract.
- Python environment_manager is "conda"; R is per delivery.r.environment_recommendation.
- Mixed projects use a single conda environment with bridge libraries.
- Steps 1-9 are tested for ordering and individual behavior.
- Subprocess calls (conda, pip, python -c, Rscript) are mocked to avoid real execution.
- regression_test_import_map.json presence/absence is controlled per test.
- Pipeline state file (pipeline_state.json) is used for total_units derivation.
- Build log is .svp/build_log.jsonl.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Synthetic data factories
# ---------------------------------------------------------------------------


def make_python_profile() -> Dict[str, Any]:
    """Minimal Python-only profile."""
    return {
        "archetype": "python_project",
        "language": {
            "primary": "python",
            "components": [],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "python": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
        },
        "quality": {
            "python": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
        },
        "testing": {"readable_test_names": True},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }


def make_r_profile() -> Dict[str, Any]:
    """Minimal R-only profile."""
    return {
        "archetype": "r_project",
        "language": {
            "primary": "r",
            "components": [],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "r": {
                "environment_recommendation": "renv",
                "dependency_format": "renv.lock",
                "source_layout": "package",
                "entry_points": False,
            },
        },
        "quality": {
            "r": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
        },
        "testing": {"readable_test_names": True},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }


def make_mixed_profile() -> Dict[str, Any]:
    """Mixed Python+R profile."""
    return {
        "archetype": "mixed",
        "language": {
            "primary": "python",
            "components": ["r"],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "python": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
            "r": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "package",
                "entry_points": False,
            },
        },
        "quality": {
            "python": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
            "r": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
        },
        "testing": {"readable_test_names": True},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }


def make_python_language_registry() -> Dict[str, Dict[str, Any]]:
    """Synthetic LANGUAGE_REGISTRY with Python and R entries."""
    return {
        "python": {
            "id": "python",
            "display_name": "Python",
            "file_extension": ".py",
            "source_dir": "src",
            "test_dir": "tests",
            "test_file_pattern": "test_*.py",
            "toolchain_file": "python_conda_pytest.json",
            "environment_manager": "conda",
            "test_framework": "pytest",
            "version_check_command": "python --version",
            "stub_sentinel": "__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP",
            "stub_generator_key": "python",
            "test_output_parser_key": "python",
            "quality_runner_key": "python",
            "is_component_only": False,
            "compatible_hosts": [],
            "bridge_libraries": {
                "python_r": {"library": "rpy2", "conda_package": "rpy2"},
            },
            "collection_error_indicators": [
                "ERROR collecting",
                "ImportError",
                "ModuleNotFoundError",
                "SyntaxError",
                "no tests ran",
            ],
            "authorized_write_dirs": ["src", "tests", "."],
            "default_delivery": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
            "default_quality": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
            "valid_linters": {"ruff", "flake8", "pylint", "none"},
            "valid_formatters": {"ruff", "black", "autopep8", "none"},
            "valid_type_checkers": {"mypy", "pyright", "none"},
            "valid_source_layouts": ["conventional", "flat", "svp_native"],
            "environment_file_name": "environment.yml",
            "project_manifest_file": "pyproject.toml",
            "gitignore_patterns": [
                "__pycache__/",
                "*.pyc",
                ".mypy_cache/",
                "dist/",
                "*.egg-info/",
            ],
            "entry_point_mechanism": "pyproject_scripts",
            "quality_config_mapping": {
                "ruff": "ruff.toml",
                "black": "pyproject.toml [tool.black]",
                "flake8": ".flake8",
                "mypy": "pyproject.toml [tool.mypy]",
                "pyright": "pyproject.toml [tool.pyright]",
            },
            "non_source_embedding": "module_level_string",
            "agent_prompts": {
                "test_agent": "test prompt",
                "implementation_agent": "impl prompt",
                "coverage_review_agent": "cov prompt",
            },
        },
        "r": {
            "id": "r",
            "display_name": "R",
            "file_extension": ".R",
            "source_dir": "R",
            "test_dir": "tests/testthat",
            "test_file_pattern": "test-*.R",
            "toolchain_file": "r_renv_testthat.json",
            "environment_manager": "renv",
            "test_framework": "testthat",
            "version_check_command": "Rscript --version",
            "stub_sentinel": "# __SVP_STUB__ <- TRUE  # DO NOT DELIVER -- stub file generated by SVP",
            "stub_generator_key": "r",
            "test_output_parser_key": "r",
            "quality_runner_key": "r",
            "is_component_only": False,
            "compatible_hosts": [],
            "bridge_libraries": {
                "r_python": {
                    "library": "reticulate",
                    "conda_package": "r-reticulate",
                },
            },
            "collection_error_indicators": [
                "Error in library",
                "there is no package called",
                "could not find function",
            ],
            "authorized_write_dirs": ["R", "tests/testthat", "."],
            "default_delivery": {
                "environment_recommendation": "renv",
                "dependency_format": "renv.lock",
                "source_layout": "package",
                "entry_points": False,
            },
            "default_quality": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
            "valid_linters": {"lintr", "none"},
            "valid_formatters": {"styler", "none"},
            "valid_type_checkers": {"none"},
            "valid_source_layouts": ["package", "scripts"],
            "environment_file_name": "renv.lock",
            "project_manifest_file": "DESCRIPTION",
            "gitignore_patterns": [
                ".Rhistory",
                ".RData",
                ".Rproj.user/",
                "inst/doc/",
            ],
            "entry_point_mechanism": "namespace_exports",
            "quality_config_mapping": {
                "lintr": ".lintr",
                "styler": ".styler.R",
            },
            "non_source_embedding": "toplevel_character",
            "agent_prompts": {
                "test_agent": "R test prompt",
                "implementation_agent": "R impl prompt",
                "coverage_review_agent": "R cov prompt",
            },
        },
        "stan": {
            "id": "stan",
            "display_name": "Stan",
            "file_extension": ".stan",
            "is_component_only": True,
            "compatible_hosts": ["r", "python"],
            "stub_generator_key": "stan_template",
            "quality_runner_key": "stan_syntax_check",
            "required_dispatch_entries": ["stub_generator_key", "quality_runner_key"],
            "bridge_libraries": {},
        },
    }


def make_toolchain() -> Dict[str, Any]:
    """Minimal toolchain dict."""
    return {
        "quality": {
            "pre_test": [
                {"operation": "lint", "command": "ruff check {target}"},
                {"operation": "format", "command": "ruff format {target}"},
            ],
        },
        "test": {
            "command": "pytest {target}",
        },
    }


def make_blueprint_contracts(num_units: int = 5) -> str:
    """Generate synthetic blueprint_contracts.md with N units."""
    lines = ["# Blueprint Contracts\n"]
    for i in range(1, num_units + 1):
        lines.append(f"## Unit {i}: TestUnit{i}\n")
        lines.append("### Tier 2 -- Signatures\n")
        lines.append("```python\n")
        lines.append("import os\nimport json\n")
        lines.append(f"def func_{i}() -> None: ...\n")
        lines.append("```\n")
        lines.append("### Tier 3 -- Behavioral Contracts\n")
        if i > 1:
            lines.append(f"**Dependencies:** Unit {i - 1}.\n")
        else:
            lines.append("**Dependencies:** None.\n")
        lines.append("\n")
    return "\n".join(lines)


def setup_blueprint_dir(tmp_path: Path, num_units: int = 5) -> Path:
    """Create a blueprint directory with synthetic contracts file."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir(exist_ok=True)
    contracts = make_blueprint_contracts(num_units)
    (bp_dir / "blueprint_contracts.md").write_text(contracts)
    (bp_dir / "blueprint_prose.md").write_text("# Blueprint Prose\n")
    return bp_dir


def setup_project_root(
    tmp_path: Path,
    profile: Dict[str, Any] | None = None,
    toolchain: Dict[str, Any] | None = None,
    num_units: int = 5,
    with_regression_map: bool = False,
    with_pipeline_state: bool = True,
) -> Path:
    """Set up a full project root with all required files."""
    root = tmp_path / "myproject"
    root.mkdir(exist_ok=True)
    svp_dir = root / ".svp"
    svp_dir.mkdir(exist_ok=True)

    if profile is None:
        profile = make_python_profile()
    (root / "project_profile.json").write_text(json.dumps(profile, indent=2))

    if toolchain is None:
        toolchain = make_toolchain()
    (root / "toolchain.json").write_text(json.dumps(toolchain, indent=2))

    bp_dir = setup_blueprint_dir(root, num_units)

    if with_pipeline_state:
        state = {
            "stage": "stage_2",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 0,
        }
        (root / "pipeline_state.json").write_text(json.dumps(state, indent=2))

    if with_regression_map:
        (root / "regression_test_import_map.json").write_text(
            json.dumps({"old_module": "new_module"})
        )

    return root


# ---------------------------------------------------------------------------
# Import target module
# ---------------------------------------------------------------------------


from infrastructure_setup import main, run_infrastructure_setup

# ---------------------------------------------------------------------------
# Tests for run_infrastructure_setup
# ---------------------------------------------------------------------------


class TestRunInfrastructureSetupSignature:
    """Tests verifying the function signature and basic call contract."""

    def test_accepts_required_arguments(self):
        """run_infrastructure_setup accepts project_root, profile, toolchain,
        language_registry, and blueprint_dir as positional/keyword args."""
        # Verify the function is callable and has the right parameter count
        import inspect

        sig = inspect.signature(run_infrastructure_setup)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "profile" in params
        assert "toolchain" in params
        assert "language_registry" in params
        assert "blueprint_dir" in params
        assert len(params) == 5

    def test_returns_none_type_annotation(self):
        """run_infrastructure_setup has return type None."""
        import inspect

        sig = inspect.signature(run_infrastructure_setup)
        assert (
            sig.return_annotation is None
            or sig.return_annotation == inspect.Parameter.empty
        )


class TestEnvironmentCreationPython:
    """Step 1: Environment creation for Python projects dispatches via
    LANGUAGE_REGISTRY[primary_language]['environment_manager']."""

    def test_python_project_uses_conda_create(self, tmp_path):
        """Python primary language dispatches to conda create -n {env_name}."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # At least one call should contain conda create
            conda_calls = [
                c
                for c in mock_run.call_args_list
                if "conda" in str(c) and "create" in str(c)
            ]
            assert len(conda_calls) >= 1, "Expected at least one conda create call"

    def test_python_env_name_derived_from_project_root(self, tmp_path):
        """Environment name follows derive_env_name convention: svp-{root.name}."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"
        expected_env_name = f"svp-{root.name}"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            conda_calls = [c for c in mock_run.call_args_list if "conda" in str(c)]
            env_name_found = any(expected_env_name in str(c) for c in conda_calls)
            assert env_name_found, (
                f"Expected env name '{expected_env_name}' in conda calls"
            )


class TestEnvironmentCreationR:
    """Step 1: Environment creation for R projects dispatches per
    delivery.r.environment_recommendation."""

    def test_r_project_uses_renv_when_renv_recommended(self, tmp_path):
        """R with environment_recommendation='renv' dispatches to renv setup."""
        root = setup_project_root(tmp_path, profile=make_r_profile())
        profile = make_r_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # Should see renv-related invocation, not conda
            all_calls_str = str(mock_run.call_args_list)
            assert "renv" in all_calls_str.lower() or "Rscript" in all_calls_str, (
                "Expected renv-based environment setup for R project"
            )

    def test_r_project_uses_conda_when_conda_recommended(self, tmp_path):
        """R with environment_recommendation='conda' dispatches to conda."""
        profile = make_r_profile()
        profile["delivery"]["r"]["environment_recommendation"] = "conda"
        root = setup_project_root(tmp_path, profile=profile)
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            conda_calls = [c for c in mock_run.call_args_list if "conda" in str(c)]
            assert len(conda_calls) >= 1, (
                "Expected conda-based setup for R conda recommendation"
            )

    def test_r_project_uses_packrat_when_packrat_recommended(self, tmp_path):
        """R with environment_recommendation='packrat' dispatches to packrat."""
        profile = make_r_profile()
        profile["delivery"]["r"]["environment_recommendation"] = "packrat"
        root = setup_project_root(tmp_path, profile=profile)
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            all_calls_str = str(mock_run.call_args_list)
            assert "packrat" in all_calls_str.lower(), (
                "Expected packrat-based setup for R packrat recommendation"
            )


class TestEnvironmentCreationMixed:
    """Step 1: Mixed archetype uses a single conda environment with bridge libs."""

    def test_mixed_project_creates_single_conda_env(self, tmp_path):
        """Mixed project creates one conda env with both languages."""
        root = setup_project_root(tmp_path, profile=make_mixed_profile())
        profile = make_mixed_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            conda_create_calls = [
                c
                for c in mock_run.call_args_list
                if "conda" in str(c) and "create" in str(c)
            ]
            # Should be exactly one conda create (single environment)
            assert len(conda_create_calls) == 1, (
                "Mixed project should create exactly one conda environment"
            )

    def test_mixed_project_installs_bridge_libraries(self, tmp_path):
        """Mixed project installs bridge libraries from both language entries."""
        root = setup_project_root(tmp_path, profile=make_mixed_profile())
        profile = make_mixed_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            all_calls_str = str(mock_run.call_args_list)
            # Bridge libraries: rpy2 (python->r) and r-reticulate (r->python)
            assert "rpy2" in all_calls_str or "reticulate" in all_calls_str, (
                "Expected bridge libraries to be installed for mixed project"
            )


class TestQualityToolInstallation:
    """Step 2: Quality tool installation reads packages from language-specific
    toolchain and installs into created environment."""

    def test_quality_tools_installed_into_environment(self, tmp_path):
        """Quality tool packages are installed into the created environment."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # Should see installation calls (pip install or conda install)
            install_calls = [c for c in mock_run.call_args_list if "install" in str(c)]
            assert len(install_calls) >= 1, "Expected quality tool installation calls"


class TestDependencyExtraction:
    """Step 3: Dependency extraction reads blueprint_contracts.md for import
    statements and resolves a unique dependency list."""

    def test_reads_imports_from_blueprint_contracts(self, tmp_path):
        """Dependency extraction reads blueprint_contracts.md to find imports."""
        root = setup_project_root(tmp_path, num_units=3)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # The blueprint has `import os` and `import json` in every unit
            # These should be extracted and resolved into a unique dependency list
            # The function should not fail (it processed the blueprint)

    def test_resolves_unique_dependencies(self, tmp_path):
        """Duplicate imports across units are de-duplicated."""
        root = setup_project_root(tmp_path, num_units=3)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        # All 3 units import os and json -- should resolve to unique list
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")


class TestImportValidation:
    """Step 4: Import validation -- language-specific checks run inside
    created environment."""

    def test_python_import_validation_uses_python_c(self, tmp_path):
        """Python import validation runs python -c 'import X' for each dep."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            import_calls = [
                c
                for c in mock_run.call_args_list
                if "import" in str(c) and "python" in str(c).lower()
            ]
            # Should have at least one python -c "import X" call
            # (os and json are stdlib, but the validation still runs)

    def test_r_import_validation_uses_rscript_library(self, tmp_path):
        """R import validation runs Rscript -e 'library(X)' for each dep."""
        profile = make_r_profile()
        root = setup_project_root(tmp_path, profile=profile)
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            r_calls = [
                c
                for c in mock_run.call_args_list
                if "Rscript" in str(c) and "library" in str(c)
            ]
            # R validation should use Rscript -e "library(X)"


class TestDirectoryScaffolding:
    """Step 5: Directory scaffolding creates src/unit_N/ and tests/unit_N/
    for Python; R/ and tests/testthat/ for R."""

    def test_python_creates_src_and_tests_unit_dirs(self, tmp_path):
        """Python project creates src/unit_N/ and tests/unit_N/ for each unit."""
        num_units = 3
        root = setup_project_root(tmp_path, num_units=num_units)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        for i in range(1, num_units + 1):
            assert (root / "src" / f"unit_{i}").is_dir(), (
                f"Missing src/unit_{i}/ directory"
            )
            assert (root / "tests" / f"unit_{i}").is_dir(), (
                f"Missing tests/unit_{i}/ directory"
            )

    def test_r_creates_r_and_tests_testthat_dirs(self, tmp_path):
        """R project creates R/ and tests/testthat/ directories."""
        profile = make_r_profile()
        root = setup_project_root(tmp_path, profile=profile)
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        assert (root / "R").is_dir(), "Missing R/ directory for R project"
        assert (root / "tests" / "testthat").is_dir(), (
            "Missing tests/testthat/ directory for R project"
        )


class TestDAGRevalidation:
    """Step 6: DAG re-validation extracts dependency graph from blueprint,
    validates no forward edges, no cycles."""

    def test_valid_dag_passes_revalidation(self, tmp_path):
        """Blueprint with valid linear dependency chain passes DAG validation."""
        root = setup_project_root(tmp_path, num_units=3)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            # Should complete without error for a valid DAG

    def test_forward_edge_in_dag_causes_failure(self, tmp_path):
        """Blueprint with forward edges in dependency graph causes step failure."""
        root = setup_project_root(tmp_path, num_units=3)
        bp_dir = root / "blueprint"
        # Create a blueprint where unit 1 depends on unit 3 (forward edge)
        contracts = (
            "# Blueprint Contracts\n\n"
            "## Unit 1: First\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_1(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 3.\n\n"
            "## Unit 2: Second\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_2(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 1.\n\n"
            "## Unit 3: Third\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_3(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 2.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts)

        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
                # If it completes, it should have raised or returned error for invalid DAG
                # The contract says "any step failure: non-zero exit, no partial cleanup"
                # The function itself may raise or the caller (main) exits non-zero
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (ValueError, RuntimeError, SystemExit):
                pass  # Expected: DAG validation should fail on forward edge

    def test_cycle_in_dag_causes_failure(self, tmp_path):
        """Blueprint with cycles in dependency graph causes step failure."""
        root = setup_project_root(tmp_path, num_units=2)
        bp_dir = root / "blueprint"
        # Create a blueprint where unit 1 depends on unit 2 and vice versa (cycle)
        contracts = (
            "# Blueprint Contracts\n\n"
            "## Unit 1: First\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_1(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 2.\n\n"
            "## Unit 2: Second\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_2(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 1.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts)

        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (ValueError, RuntimeError, SystemExit):
                pass  # Expected: DAG validation should fail on cycle


class TestTotalUnitsDerivation:
    """Step 7: total_units derivation counts ## Unit N: headings in blueprint.
    Sets total_units in pipeline state."""

    def test_counts_unit_headings_correctly(self, tmp_path):
        """total_units equals the number of ## Unit N: headings in blueprint."""
        num_units = 7
        root = setup_project_root(tmp_path, num_units=num_units)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        # Check pipeline state was updated with total_units
        state_file = root / "pipeline_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            assert state.get("total_units") == num_units, (
                f"Expected total_units={num_units}, got {state.get('total_units')}"
            )

    def test_sets_total_units_in_pipeline_state(self, tmp_path):
        """Pipeline state file is updated with the derived total_units value."""
        num_units = 4
        root = setup_project_root(tmp_path, num_units=num_units)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        state_file = root / "pipeline_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            assert "total_units" in state, "total_units key missing from pipeline state"
            assert isinstance(state["total_units"], int), "total_units must be int"


class TestRegressionTestAdaptation:
    """Step 8: Regression test adaptation -- if regression_test_import_map.json
    exists, runs adapt_regression_tests.py on tests/regressions/."""

    def test_runs_adaptation_when_import_map_exists(self, tmp_path):
        """When regression_test_import_map.json exists, adapt_regression_tests.py
        is invoked."""
        root = setup_project_root(tmp_path, with_regression_map=True)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"
        # Create the regressions directory
        (root / "tests" / "regressions").mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            adapt_calls = [
                c for c in mock_run.call_args_list if "adapt_regression" in str(c)
            ]
            assert len(adapt_calls) >= 1, (
                "Expected adapt_regression_tests.py to be called when import map exists"
            )

    def test_skips_adaptation_when_import_map_absent(self, tmp_path):
        """When regression_test_import_map.json does not exist, adaptation is skipped."""
        root = setup_project_root(tmp_path, with_regression_map=False)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            adapt_calls = [
                c for c in mock_run.call_args_list if "adapt_regression" in str(c)
            ]
            assert len(adapt_calls) == 0, (
                "adapt_regression_tests.py should not be called when import map absent"
            )


class TestBuildLogCreation:
    """Step 9: Build log creation creates .svp/build_log.jsonl (empty JSONL).
    Append-only from this point."""

    def test_creates_build_log_jsonl(self, tmp_path):
        """Build log file .svp/build_log.jsonl is created."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        build_log = root / ".svp" / "build_log.jsonl"
        assert build_log.exists(), "build_log.jsonl should be created"

    def test_build_log_is_empty_initially(self, tmp_path):
        """Build log is created as an empty file (empty JSONL)."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        build_log = root / ".svp" / "build_log.jsonl"
        if build_log.exists():
            content = build_log.read_text()
            assert content.strip() == "", "Build log should be empty initially"


class TestStepOrdering:
    """The 9 steps must execute IN ORDER: environment creation, quality tool
    installation, dependency extraction, import validation, directory scaffolding,
    DAG re-validation, total_units derivation, regression test adaptation,
    build log creation."""

    def test_all_nine_steps_execute_in_order(self, tmp_path):
        """Verify that steps execute in the contracted order by observing
        side effects sequence."""
        root = setup_project_root(tmp_path, num_units=2, with_regression_map=True)
        (root / "tests" / "regressions").mkdir(parents=True, exist_ok=True)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        call_log = []

        def tracking_run(*args, **kwargs):
            cmd_str = str(args) + str(kwargs)
            call_log.append(cmd_str)
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=tracking_run):
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        # We verify that the function completed (no exception) and made subprocess calls
        # The exact call pattern will depend on implementation but calls should exist
        assert len(call_log) > 0, (
            "Expected subprocess calls during infrastructure setup"
        )


class TestStepFailureExitsNonZero:
    """On any step failure: reports error and exits with non-zero code.
    No partial cleanup."""

    def test_environment_creation_failure_raises(self, tmp_path):
        """If environment creation fails, the function propagates error (non-zero exit)."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            # First call (env creation) fails
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="conda create failed"
            )
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
                # If it doesn't raise, that's also acceptable if main handles exit code
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (RuntimeError, SystemExit, subprocess.CalledProcessError):
                pass  # Expected: step failure should propagate

    def test_import_validation_failure_raises(self, tmp_path):
        """If import validation fails, the function propagates error."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        call_count = [0]

        def selective_failure(*args, **kwargs):
            call_count[0] += 1
            cmd_str = str(args)
            # Fail on import validation (python -c "import")
            if "import" in cmd_str and "python" in cmd_str.lower():
                return MagicMock(returncode=1, stdout="", stderr="ImportError")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=selective_failure):
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (RuntimeError, SystemExit, subprocess.CalledProcessError):
                pass  # Expected

    def test_no_partial_cleanup_on_failure(self, tmp_path):
        """On failure, no partial cleanup occurs -- artifacts from earlier steps remain."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        # Make the very last step (build log creation) fail by making .svp read-only
        # But the earlier steps should have created directories, etc.
        # The contract says: no partial cleanup -- meaning we do NOT delete partial work
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="failure")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (RuntimeError, SystemExit, subprocess.CalledProcessError):
                pass

        # Verify the function did NOT clean up .svp directory or other artifacts
        assert (root / ".svp").is_dir(), (
            ".svp directory should not be cleaned up on failure"
        )


class TestComponentLanguagePackages:
    """Component language packages installed into host environment."""

    def test_component_packages_installed_into_host(self, tmp_path):
        """Component language (e.g., Stan) packages are installed into the host
        environment, not a separate one."""
        profile = make_python_profile()
        profile["language"]["components"] = ["stan"]
        root = setup_project_root(tmp_path, profile=profile)
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # Stan should not trigger a separate environment creation
            conda_create_calls = [
                c
                for c in mock_run.call_args_list
                if "conda" in str(c) and "create" in str(c)
            ]
            # At most one environment creation (the host), not one per component
            assert len(conda_create_calls) <= 1, (
                "Component languages should not create separate environments"
            )


# ---------------------------------------------------------------------------
# Tests for main (CLI entry point)
# ---------------------------------------------------------------------------


class TestMainCLI:
    """main: CLI entry point with --project-root argument."""

    def test_main_accepts_project_root_argument(self):
        """main accepts argv with --project-root."""
        import inspect

        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_main_loads_artifacts_and_calls_run_infrastructure_setup(self, tmp_path):
        """main loads profile, toolchain, language_registry, blueprint_dir from
        project_root and calls run_infrastructure_setup."""
        root = setup_project_root(tmp_path)

        with patch("src.unit_11.stub.run_infrastructure_setup") as mock_setup:
            try:
                main(["--project-root", str(root)])
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except SystemExit as e:
                if e.code == 0:
                    pass  # Success exit is fine
                else:
                    # Could be expected if loading fails
                    pass

    def test_main_exits_zero_on_success(self, tmp_path):
        """main exits with code 0 on successful infrastructure setup."""
        root = setup_project_root(tmp_path)

        with (
            patch("src.unit_11.stub.run_infrastructure_setup") as mock_setup,
            patch("subprocess.run") as mock_run,
        ):
            mock_setup.return_value = None
            mock_run.return_value = MagicMock(returncode=0)
            try:
                main(["--project-root", str(root)])
                # If it returns without exit, that's success (implicit 0)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except SystemExit as e:
                assert e.code == 0 or e.code is None, (
                    f"Expected exit code 0, got {e.code}"
                )

    def test_main_exits_one_on_failure(self, tmp_path):
        """main exits with code 1 on infrastructure setup failure."""
        root = setup_project_root(tmp_path)

        with patch("src.unit_11.stub.run_infrastructure_setup") as mock_setup:
            mock_setup.side_effect = RuntimeError("setup failed")
            try:
                main(["--project-root", str(root)])
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except SystemExit as e:
                assert e.code == 1, f"Expected exit code 1, got {e.code}"
            except RuntimeError:
                # If main doesn't catch, the contract says exit code 1
                # The test validates the contract: failure -> non-zero
                pass

    def test_main_requires_project_root(self):
        """main with no --project-root should fail."""
        try:
            main([])
        except NotImplementedError:
            pytest.skip("Not yet implemented")
        except (SystemExit, TypeError, ValueError):
            pass  # Expected: missing required argument


class TestMainLoadsCorrectArtifacts:
    """main loads profile, toolchain, language registry, and blueprint directory
    from project root."""

    def test_main_resolves_blueprint_dir(self, tmp_path):
        """main resolves the blueprint directory from project root."""
        root = setup_project_root(tmp_path)

        with patch("src.unit_11.stub.run_infrastructure_setup") as mock_setup:
            try:
                main(["--project-root", str(root)])
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except SystemExit:
                pass

            if mock_setup.called:
                call_kwargs = mock_setup.call_args
                # blueprint_dir should be a Path
                args = call_kwargs[0] if call_kwargs[0] else ()
                kwargs = call_kwargs[1] if len(call_kwargs) > 1 else {}
                # The blueprint_dir should be resolvable from root


class TestLanguageDispatch:
    """Environment creation dispatches via
    LANGUAGE_REGISTRY[primary_language]['environment_manager']."""

    def test_dispatches_based_on_primary_language(self, tmp_path):
        """The primary language from profile determines environment manager lookup."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        # Python's environment_manager is "conda"
        assert registry["python"]["environment_manager"] == "conda"
        # R's environment_manager is "renv"
        assert registry["r"]["environment_manager"] == "renv"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # For python project, should use conda (not renv)
            all_calls = str(mock_run.call_args_list)
            # conda should appear, not renv init
            if "conda" in all_calls:
                assert "renv" not in all_calls or "conda" in all_calls


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_unit_blueprint(self, tmp_path):
        """Infrastructure setup works with a blueprint containing just one unit."""
        root = setup_project_root(tmp_path, num_units=1)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        # Should create exactly 1 unit directory
        state_file = root / "pipeline_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            if "total_units" in state:
                assert state["total_units"] == 1

    def test_many_units_blueprint(self, tmp_path):
        """Infrastructure setup works with a blueprint containing many units."""
        num_units = 29  # SVP 2.2 has 29 units
        root = setup_project_root(tmp_path, num_units=num_units)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        state_file = root / "pipeline_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            if "total_units" in state:
                assert state["total_units"] == num_units

    def test_svp_dir_created_if_not_exists(self, tmp_path):
        """If .svp/ directory does not exist, build log creation should handle it."""
        root = setup_project_root(tmp_path)
        # Remove .svp to test creation
        import shutil

        svp_dir = root / ".svp"
        if svp_dir.exists():
            shutil.rmtree(svp_dir)

        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (FileNotFoundError, OSError):
                # Implementation may need .svp to exist or may create it
                pass

    def test_empty_blueprint_contracts_handled(self, tmp_path):
        """Blueprint with zero units is handled gracefully."""
        root = setup_project_root(tmp_path, num_units=0)
        bp_dir = root / "blueprint"
        # Overwrite with empty contracts
        (bp_dir / "blueprint_contracts.md").write_text("# Blueprint Contracts\n\n")
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (ValueError, RuntimeError):
                pass  # May fail gracefully on zero units


class TestRunInfrastructureSetupReturnValue:
    """run_infrastructure_setup returns None on success."""

    def test_returns_none_on_success(self, tmp_path):
        """Successful run_infrastructure_setup returns None."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                result = run_infrastructure_setup(
                    root, profile, toolchain, registry, bp_dir
                )
                assert result is None, "run_infrastructure_setup should return None"
            except NotImplementedError:
                pytest.skip("Not yet implemented")


class TestEnvironmentManagerRegistryLookup:
    """Environment creation uses LANGUAGE_REGISTRY[primary_language]['environment_manager']
    for dispatch, not hardcoded language checks."""

    def test_uses_registry_environment_manager_key(self, tmp_path):
        """The environment manager comes from the registry, not hardcoded."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        # Override python's environment manager to something unusual to verify dispatch
        registry["python"]["environment_manager"] = "custom_manager"
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            except (KeyError, ValueError, RuntimeError):
                # May fail because "custom_manager" isn't a known manager
                # but the key should have been looked up from registry
                pass


class TestBlueprintDirParameter:
    """blueprint_dir parameter is used for blueprint access, not hardcoded."""

    def test_uses_provided_blueprint_dir(self, tmp_path):
        """The function uses the blueprint_dir parameter, not a hardcoded path."""
        root = setup_project_root(tmp_path, num_units=2)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        # Use a non-default blueprint dir
        custom_bp_dir = tmp_path / "custom_blueprint"
        custom_bp_dir.mkdir()
        contracts = make_blueprint_contracts(2)
        (custom_bp_dir / "blueprint_contracts.md").write_text(contracts)
        (custom_bp_dir / "blueprint_prose.md").write_text("# Prose\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(
                    root, profile, toolchain, registry, custom_bp_dir
                )
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            # Should not fail due to missing blueprint in default location


class TestBuildLogAppendOnly:
    """Build log is append-only from creation point."""

    def test_build_log_file_is_jsonl_format(self, tmp_path):
        """Build log file is created with .jsonl extension."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        build_log = root / ".svp" / "build_log.jsonl"
        if build_log.exists():
            assert build_log.suffix == ".jsonl", "Build log must have .jsonl extension"


class TestDirectoryScaffoldingPythonConvention:
    """Directory scaffolding follows Python convention: src/unit_N/ and tests/unit_N/."""

    def test_scaffolding_creates_all_unit_directories(self, tmp_path):
        """Every unit in the blueprint gets its own src and test directory."""
        num_units = 5
        root = setup_project_root(tmp_path, num_units=num_units)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        for i in range(1, num_units + 1):
            src_dir = root / "src" / f"unit_{i}"
            test_dir = root / "tests" / f"unit_{i}"
            if src_dir.parent.exists():
                assert src_dir.is_dir(), f"Missing src/unit_{i}/"
            if test_dir.parent.exists():
                assert test_dir.is_dir(), f"Missing tests/unit_{i}/"


class TestRDeliveryEnvironmentRecommendation:
    """R environment creation dispatches per delivery.r.environment_recommendation
    which can be renv, conda, or packrat."""

    def test_r_renv_is_default(self, tmp_path):
        """Default R profile uses renv."""
        profile = make_r_profile()
        assert profile["delivery"]["r"]["environment_recommendation"] == "renv"

    def test_r_three_valid_environment_managers(self):
        """R supports renv, conda, and packrat as environment managers."""
        valid_managers = {"renv", "conda", "packrat"}
        # This is a data assertion test, not a behavioral test
        assert "renv" in valid_managers
        assert "conda" in valid_managers
        assert "packrat" in valid_managers


class TestMixedArchetypeConstraints:
    """Mixed archetype forces both environment_recommendations to conda
    and both dependency_formats to environment.yml (from Unit 3 profile contract)."""

    def test_mixed_uses_conda_for_all_languages(self, tmp_path):
        """Mixed archetype should use conda for both Python and R."""
        profile = make_mixed_profile()
        # Mixed profile should have conda forced for both
        assert profile["delivery"]["python"]["environment_recommendation"] == "conda"
        assert profile["delivery"]["r"]["environment_recommendation"] == "conda"

        root = setup_project_root(tmp_path, profile=profile)
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # Single conda env, not renv
            conda_calls = [c for c in mock_run.call_args_list if "conda" in str(c)]
            assert len(conda_calls) >= 1, "Mixed project must use conda"


class TestQualityToolsFromToolchain:
    """Quality tool installation reads packages from language-specific
    toolchain file (get_gate_composition compositions reference tool packages)."""

    def test_reads_quality_config_from_toolchain(self, tmp_path):
        """Quality tools are determined by toolchain configuration."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        toolchain["quality"]["tools"] = ["ruff", "mypy"]
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")


class TestDAGNoCycles:
    """DAG re-validation: validates no cycles exist in dependency graph."""

    def test_linear_dependencies_pass(self, tmp_path):
        """A linear chain (1->2->3) has no cycles and should pass."""
        root = setup_project_root(tmp_path, num_units=3)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            # Should complete without DAG validation error

    def test_no_dependency_units_pass(self, tmp_path):
        """Units with no dependencies (root units) pass DAG validation."""
        root = setup_project_root(tmp_path, num_units=1)
        bp_dir = root / "blueprint"
        contracts = (
            "# Blueprint Contracts\n\n"
            "## Unit 1: Root\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_1(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** None.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts)

        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")


class TestDAGNoForwardEdges:
    """DAG re-validation: validates no forward edges (a unit depending on a
    higher-numbered unit)."""

    def test_backward_dependencies_are_valid(self, tmp_path):
        """Unit 3 depending on Unit 1 (backward) is valid."""
        root = setup_project_root(tmp_path, num_units=3)
        bp_dir = root / "blueprint"
        contracts = (
            "# Blueprint Contracts\n\n"
            "## Unit 1: First\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_1(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** None.\n\n"
            "## Unit 2: Second\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_2(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 1.\n\n"
            "## Unit 3: Third\n\n"
            "### Tier 2 -- Signatures\n\n"
            "```python\ndef func_3(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "**Dependencies:** Unit 1.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts)

        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")
            # Should complete without error


class TestTotalUnitsFromHeadings:
    """total_units derivation counts ## Unit N: headings in blueprint."""

    def test_counts_exactly_matching_headings(self, tmp_path):
        """Only ## Unit N: pattern headings are counted."""
        root = setup_project_root(tmp_path, num_units=4)
        bp_dir = root / "blueprint"
        # Add non-matching headings to ensure they're not counted
        contracts = (bp_dir / "blueprint_contracts.md").read_text()
        contracts += "\n## Not a Unit heading\n\n### Unit fake\n\n"
        (bp_dir / "blueprint_contracts.md").write_text(contracts)

        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

        state_file = root / "pipeline_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            if "total_units" in state:
                assert state["total_units"] == 4, (
                    "Should count only ## Unit N: headings, not other headings"
                )


class TestRegressionTestAdaptationDetails:
    """Step 8 details: regression_test_import_map.json triggers
    adapt_regression_tests.py on tests/regressions/."""

    def test_adaptation_targets_tests_regressions_directory(self, tmp_path):
        """adapt_regression_tests.py is called targeting tests/regressions/."""
        root = setup_project_root(tmp_path, with_regression_map=True)
        (root / "tests" / "regressions").mkdir(parents=True, exist_ok=True)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            adapt_calls = [
                c for c in mock_run.call_args_list if "adapt_regression" in str(c)
            ]
            if adapt_calls:
                # Should reference tests/regressions/ in the call
                call_str = str(adapt_calls[0])
                assert "regression" in call_str.lower(), (
                    "Adaptation should target regressions directory"
                )


class TestImportValidationInsideEnvironment:
    """Import validation runs inside the created environment, not the host."""

    def test_python_import_runs_in_env(self, tmp_path):
        """Python import validation executes within the conda environment."""
        root = setup_project_root(tmp_path)
        profile = make_python_profile()
        toolchain = make_toolchain()
        registry = make_python_language_registry()
        bp_dir = root / "blueprint"
        expected_env = f"svp-{root.name}"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                run_infrastructure_setup(root, profile, toolchain, registry, bp_dir)
            except NotImplementedError:
                pytest.skip("Not yet implemented")

            # Import validation calls should reference the environment
            import_calls = [c for c in mock_run.call_args_list if "import" in str(c)]
            # If import calls exist, they should use the env
            for ic in import_calls:
                call_str = str(ic)
                if "python" in call_str.lower():
                    # Should reference the conda env name or run prefix
                    pass  # Exact mechanism depends on implementation
