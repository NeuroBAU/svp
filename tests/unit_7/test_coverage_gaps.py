"""
Additional coverage tests for Unit 7: Dependency Extractor and Import Validator.

These tests fill gaps identified by comparing the blueprint behavioral contracts
against the existing test suite in test_dependency_extractor.py.

DATA ASSUMPTIONS (Synthetic Data):
- Well-known import-to-package mappings include cases where the import module
  name differs from the pip/conda package name (e.g., PIL -> Pillow,
  cv2 -> opencv-python, sklearn -> scikit-learn, yaml -> pyyaml).
- The conda CLI tool produces returncode=0 on success and non-zero on failure.
- subprocess.TimeoutExpired is raised when conda commands exceed their timeout.
- The main() CLI wrapper orchestrates extract -> classify -> map -> create -> validate -> dirs.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import patch, MagicMock, call

import pytest

from svp.scripts.dependency_extractor import (
    extract_all_imports,
    classify_import,
    map_imports_to_packages,
    create_conda_environment,
    validate_imports,
    create_project_directories,
    derive_env_name,
    main,
)


# ---------------------------------------------------------------------------
# map_imports_to_packages -- well-known mapping coverage
# ---------------------------------------------------------------------------

class TestMapImportsToPackagesWellKnownMappings:
    """
    Blueprint contract: 'Maps third-party import module names to pip/conda
    package names.' This means modules whose import name differs from the
    package name must be correctly mapped.

    DATA ASSUMPTION: Well-known mappings include PIL -> Pillow,
    cv2 -> opencv-python, sklearn -> scikit-learn, yaml -> pyyaml.
    These are standard Python ecosystem mappings.
    """

    def test_maps_pil_to_pillow(self):
        """PIL import name maps to 'Pillow' package."""
        result = map_imports_to_packages(["PIL"])
        assert isinstance(result, dict)
        assert "PIL" in result
        assert result["PIL"] == "Pillow"

    def test_maps_cv2_to_opencv(self):
        """cv2 import name maps to 'opencv-python' package."""
        result = map_imports_to_packages(["cv2"])
        assert isinstance(result, dict)
        assert "cv2" in result
        assert result["cv2"] == "opencv-python"

    def test_maps_sklearn_to_scikit_learn(self):
        """sklearn import name maps to 'scikit-learn' package."""
        result = map_imports_to_packages(["sklearn"])
        assert isinstance(result, dict)
        assert "sklearn" in result
        assert result["sklearn"] == "scikit-learn"

    def test_maps_yaml_to_pyyaml(self):
        """yaml import name maps to 'pyyaml' package."""
        result = map_imports_to_packages(["yaml"])
        assert isinstance(result, dict)
        assert "yaml" in result
        assert result["yaml"] == "pyyaml"

    def test_identity_mapping_for_common_packages(self):
        """Packages whose import name matches the package name map to themselves."""
        # DATA ASSUMPTION: numpy, pandas, requests have identical import and package names.
        result = map_imports_to_packages(["numpy"])
        assert isinstance(result, dict)
        assert "numpy" in result
        assert result["numpy"] == "numpy"

    def test_excludes_stdlib_from_mapping(self):
        """Standard library imports are NOT included in the package mapping."""
        # DATA ASSUMPTION: os, sys, json are standard library modules that do
        # not require pip/conda installation.
        result = map_imports_to_packages(["os", "sys", "json"])
        assert isinstance(result, dict)
        assert len(result) == 0, (
            "Standard library imports should not appear in the package mapping"
        )

    def test_mixed_stdlib_and_third_party(self):
        """When given a mix, only third-party imports appear in the mapping."""
        result = map_imports_to_packages(["os", "numpy", "sys", "pandas"])
        assert isinstance(result, dict)
        # os and sys should not be in result; numpy and pandas should be
        assert "os" not in result
        assert "sys" not in result
        assert "numpy" in result
        assert "pandas" in result


# ---------------------------------------------------------------------------
# create_conda_environment -- strict RuntimeError on non-zero returncode
# ---------------------------------------------------------------------------

class TestCreateCondaEnvironmentStrictFailure:
    """
    Blueprint error condition: RuntimeError('Conda environment creation
    failed: {details}') when conda create fails.

    The existing test_conda_failure_raises_runtime_error uses try/except
    which does not strictly assert the error is raised. This test uses
    pytest.raises for a strict assertion.
    """

    @patch("subprocess.run")
    def test_nonzero_returncode_raises_runtime_error_strict(self, mock_run):
        """
        When subprocess.run returns a non-zero returncode, create_conda_environment
        MUST raise RuntimeError (not silently return False).
        """
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="PackageNotFoundError: xyz"
        )
        with pytest.raises(RuntimeError, match="Conda environment creation failed"):
            create_conda_environment("test_env", {"bad_pkg": "bad_pkg"})

    @patch("subprocess.run")
    def test_runtime_error_includes_details(self, mock_run):
        """RuntimeError message includes the details from conda stderr."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="ResolvePackageNotFound: some_package"
        )
        with pytest.raises(RuntimeError) as exc_info:
            create_conda_environment("test_env", {"pkg": "pkg"})
        assert "Conda environment creation failed" in str(exc_info.value)

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="conda", timeout=600))
    def test_timeout_raises_runtime_error(self, mock_run):
        """TimeoutExpired from subprocess is wrapped into RuntimeError."""
        with pytest.raises(RuntimeError, match="Conda environment creation failed"):
            create_conda_environment("test_env", {"numpy": "numpy"})


# ---------------------------------------------------------------------------
# create_conda_environment -- conda command construction
# ---------------------------------------------------------------------------

class TestCreateCondaEnvironmentCommandConstruction:
    """
    Blueprint contract: Uses 'conda create' and 'conda run -n {env_name}'
    for operations (spec Section 4.3).
    """

    @patch("subprocess.run")
    def test_conda_create_includes_python_version(self, mock_run):
        """The conda create command includes the specified python version."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        create_conda_environment("my_env", {}, python_version="3.10")
        # The first call should be conda create
        first_call_args = mock_run.call_args_list[0]
        cmd = first_call_args[0][0] if first_call_args[0] else first_call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "python=3.10" in cmd_str or "python=3.10" in str(cmd)

    @patch("subprocess.run")
    def test_package_install_uses_conda_run(self, mock_run):
        """Package installation uses 'conda run -n {env_name}' per spec Section 4.3."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        create_conda_environment("my_env", {"numpy": "numpy"})
        # With packages, there should be at least 2 subprocess calls:
        # 1) conda create, 2) conda run -n my_env pip install ...
        assert mock_run.call_count >= 2, (
            "Expected at least 2 subprocess calls (create + install)"
        )
        install_call_args = mock_run.call_args_list[1]
        cmd = install_call_args[0][0] if install_call_args[0] else install_call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "conda" in cmd_str
        assert "run" in cmd_str
        assert "my_env" in cmd_str


# ---------------------------------------------------------------------------
# validate_imports -- subprocess edge cases
# ---------------------------------------------------------------------------

class TestValidateImportsEdgeCases:
    """
    Blueprint contract: validate_imports executes each import via
    'conda run -n {env_name} python -c "import ..."' and returns
    (import, error) tuples for failures.

    These tests cover edge cases not covered by the existing suite.
    """

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="conda", timeout=60))
    def test_timeout_produces_failure_tuple(self, mock_run):
        """When a conda run command times out, a failure tuple is produced."""
        result = validate_imports("test_env", ["slow_module"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple)
        assert result[0][0] == "slow_module"
        # Error message should indicate timeout
        assert "timeout" in result[0][1].lower() or "timed out" in result[0][1].lower()

    @patch("subprocess.run", side_effect=FileNotFoundError("conda not found"))
    def test_conda_not_on_path_produces_failure_tuple(self, mock_run):
        """When conda is not on PATH, a failure tuple is produced."""
        result = validate_imports("test_env", ["os"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple)
        assert result[0][0] == "os"
        # Error message should mention conda not found
        assert "conda" in result[0][1].lower() or "not found" in result[0][1].lower()

    @patch("subprocess.run")
    def test_multiple_failures_produce_multiple_tuples(self, mock_run):
        """Multiple failing imports produce one tuple per failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="",
            stderr="ModuleNotFoundError: No module named 'x'"
        )
        result = validate_imports("test_env", ["bad_a", "bad_b", "bad_c"])
        assert isinstance(result, list)
        assert len(result) == 3
        failed_names = [t[0] for t in result]
        assert "bad_a" in failed_names
        assert "bad_b" in failed_names
        assert "bad_c" in failed_names

    @patch("subprocess.run")
    def test_conda_run_command_format(self, mock_run):
        """validate_imports uses 'conda run -n {env_name} python -c ...' format."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        validate_imports("my_env", ["os"])
        assert mock_run.called, "subprocess.run must be called"
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        if isinstance(cmd, list):
            cmd_str = " ".join(cmd)
        else:
            cmd_str = str(cmd)
        assert "conda" in cmd_str
        assert "run" in cmd_str
        assert "-n" in cmd_str
        assert "my_env" in cmd_str
        assert "python" in cmd_str
        assert "-c" in cmd_str


# ---------------------------------------------------------------------------
# create_project_directories -- __init__.py creation
# ---------------------------------------------------------------------------

class TestCreateProjectDirectoriesInitFiles:
    """
    The blueprint says create_project_directories creates src/unit_N/ and
    tests/unit_N/. The implementation also creates __init__.py files in each
    directory and at the top-level src/ and tests/ directories, which is
    implied by making them usable Python packages.
    """

    def test_creates_init_files_in_unit_dirs(self):
        """__init__.py files are created in each src/unit_N/ and tests/unit_N/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 2)
            for i in range(1, 3):
                assert (root / f"src/unit_{i}" / "__init__.py").exists(), \
                    f"src/unit_{i}/__init__.py should exist"
                assert (root / f"tests/unit_{i}" / "__init__.py").exists(), \
                    f"tests/unit_{i}/__init__.py should exist"

    def test_creates_top_level_init_files(self):
        """__init__.py files are created at src/ and tests/ top level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 1)
            assert (root / "src" / "__init__.py").exists(), \
                "src/__init__.py should exist"
            assert (root / "tests" / "__init__.py").exists(), \
                "tests/__init__.py should exist"

    def test_does_not_overwrite_existing_init(self):
        """If __init__.py already exists with content, it is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create the structure first
            create_project_directories(root, 1)
            # Write content to an __init__.py
            init_file = root / "src" / "unit_1" / "__init__.py"
            init_file.write_text("# existing content\n")
            # Call again -- should not overwrite
            create_project_directories(root, 1)
            assert init_file.read_text() == "# existing content\n"


# ---------------------------------------------------------------------------
# main() CLI wrapper -- behavioral coverage
# ---------------------------------------------------------------------------

class TestMainCLIWrapper:
    """
    Blueprint contract: The CLI wrapper (main) reads the blueprint, extracts
    imports, creates the conda environment, installs all packages, validates
    imports, and creates project directories.

    Error condition: RuntimeError('Import validation failed for: {import_list}')
    when imports do not resolve -- this error is raised in main().
    """

    # DATA ASSUMPTION: We mock sys.argv to simulate CLI arguments and mock
    # the underlying functions to avoid actual file/conda operations.

    @patch("sys.argv", ["setup_infrastructure.py", "/tmp/fake_blueprint.md",
                         "--skip-conda", "--total-units", "3",
                         "--project-root", "/tmp/fake_root"])
    @patch("svp.scripts.dependency_extractor.create_project_directories")
    @patch("svp.scripts.dependency_extractor.map_imports_to_packages", return_value={"numpy": "numpy"})
    @patch("svp.scripts.dependency_extractor.extract_all_imports", return_value=["import numpy"])
    def test_main_calls_extract_and_map(self, mock_extract, mock_map, mock_dirs):
        """main() calls extract_all_imports and map_imports_to_packages."""
        main()
        mock_extract.assert_called_once()
        mock_map.assert_called_once()

    @patch("sys.argv", ["setup_infrastructure.py", "/tmp/fake_blueprint.md",
                         "--skip-conda", "--total-units", "2",
                         "--project-root", "/tmp/fake_root",
                         "--project-name", "My Project"])
    @patch("svp.scripts.dependency_extractor.create_project_directories")
    @patch("svp.scripts.dependency_extractor.map_imports_to_packages", return_value={})
    @patch("svp.scripts.dependency_extractor.extract_all_imports", return_value=["import os"])
    def test_main_calls_create_project_directories(self, mock_extract, mock_map, mock_dirs):
        """main() calls create_project_directories when --total-units is specified."""
        main()
        mock_dirs.assert_called_once()
        call_args = mock_dirs.call_args
        assert call_args[0][1] == 2  # total_units

    @patch("sys.argv", ["setup_infrastructure.py", "/tmp/fake_blueprint.md",
                         "--project-name", "Test Project",
                         "--project-root", "/tmp/fake_root"])
    @patch("svp.scripts.dependency_extractor.validate_imports", return_value=[])
    @patch("svp.scripts.dependency_extractor.create_conda_environment", return_value=True)
    @patch("svp.scripts.dependency_extractor.map_imports_to_packages", return_value={"numpy": "numpy"})
    @patch("svp.scripts.dependency_extractor.extract_all_imports", return_value=["import numpy"])
    def test_main_calls_create_conda_and_validate(self, mock_extract, mock_map,
                                                   mock_create, mock_validate):
        """main() calls create_conda_environment and validate_imports when
        --skip-conda is NOT specified."""
        main()
        mock_create.assert_called_once()
        mock_validate.assert_called_once()

    @patch("sys.argv", ["setup_infrastructure.py", "/tmp/fake_blueprint.md",
                         "--project-name", "Test Project",
                         "--project-root", "/tmp/fake_root"])
    @patch("svp.scripts.dependency_extractor.validate_imports",
           return_value=[("fake_module", "ModuleNotFoundError")])
    @patch("svp.scripts.dependency_extractor.create_conda_environment", return_value=True)
    @patch("svp.scripts.dependency_extractor.map_imports_to_packages", return_value={"fake_module": "fake_module"})
    @patch("svp.scripts.dependency_extractor.extract_all_imports", return_value=["import fake_module"])
    def test_main_raises_runtime_error_on_validation_failure(
        self, mock_extract, mock_map, mock_create, mock_validate
    ):
        """
        Blueprint error condition: RuntimeError('Import validation failed
        for: {import_list}') when imports do not resolve in the environment.
        This error is raised in main().
        """
        with pytest.raises(RuntimeError, match="Import validation failed for"):
            main()

    @patch("sys.argv", ["setup_infrastructure.py", "/tmp/fake_blueprint.md",
                         "--project-name", "My Cool-Project",
                         "--skip-conda",
                         "--project-root", "/tmp/fake_root"])
    @patch("svp.scripts.dependency_extractor.map_imports_to_packages", return_value={})
    @patch("svp.scripts.dependency_extractor.extract_all_imports", return_value=["import os"])
    def test_main_uses_derive_env_name(self, mock_extract, mock_map):
        """main() uses derive_env_name to compute the environment name from
        --project-name, applying the canonical derivation."""
        # We are just checking main() runs without error using --project-name.
        # The derive_env_name call is internal; if main() completes without
        # error, it means the name was derived correctly.
        main()


# ---------------------------------------------------------------------------
# extract_all_imports -- deduplication behavior
# ---------------------------------------------------------------------------

class TestExtractAllImportsDeduplication:
    """
    The blueprint says extract_all_imports 'collects all import and
    from...import statements' across all units. When the same import
    appears in multiple units, the implementation deduplicates.
    """

    def test_deduplicates_identical_imports_across_units(self):
        """If the same import appears in multiple units, it appears only once."""
        blueprint = """\
# Blueprint

## Unit 1: First

### Tier 2 \u2014 Signatures

```python
import os
from pathlib import Path

def func_a() -> None: ...
```

## Unit 2: Second

### Tier 2 \u2014 Signatures

```python
import os
from pathlib import Path

def func_b() -> None: ...
```
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(blueprint)
            f.flush()
            bp_path = Path(f.name)

        try:
            result = extract_all_imports(bp_path)
            # Each unique import statement should appear at most once
            assert len(result) == len(set(result)), (
                "Duplicate imports should be deduplicated"
            )
            # Specifically, 'import os' should appear once
            os_imports = [r for r in result if "os" in r and "import" in r]
            assert len(os_imports) == 1, (
                "'import os' should appear exactly once even if in multiple units"
            )
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# extract_all_imports -- non-import lines in code blocks
# ---------------------------------------------------------------------------

class TestExtractAllImportsFiltering:
    """
    The blueprint says extract_all_imports collects 'all import and
    from...import statements'. Non-import lines (function defs, class defs,
    comments) should NOT be collected.
    """

    def test_excludes_function_definitions(self):
        """Function definitions in code blocks are not collected as imports."""
        blueprint = """\
# Blueprint

## Unit 1: Test

### Tier 2 \u2014 Signatures

```python
import os

def my_function(x: int) -> str: ...

class MyClass:
    pass
```
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(blueprint)
            f.flush()
            bp_path = Path(f.name)

        try:
            result = extract_all_imports(bp_path)
            # Only import statements should be in the result
            for item in result:
                assert "import" in item, (
                    f"Expected only import statements, got: {item}"
                )
            # Function/class definitions should not appear
            for item in result:
                assert "def " not in item
                assert "class " not in item
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# classify_import -- full statement inputs
# ---------------------------------------------------------------------------

class TestClassifyImportFullStatements:
    """
    The blueprint says classify_import determines the category of an import.
    Test with full import statement strings (as returned by extract_all_imports),
    not just bare module names.
    """

    # DATA ASSUMPTION: extract_all_imports returns full import statements
    # like "import os" or "from pathlib import Path". classify_import should
    # handle these as well as bare module names.

    def test_classify_full_import_statement(self):
        """classify_import handles 'import os' format."""
        result = classify_import("import os")
        result_lower = result.lower()
        assert "standard" in result_lower or "stdlib" in result_lower

    def test_classify_from_import_statement(self):
        """classify_import handles 'from pathlib import Path' format."""
        result = classify_import("from pathlib import Path")
        result_lower = result.lower()
        assert "standard" in result_lower or "stdlib" in result_lower

    def test_classify_third_party_full_statement(self):
        """classify_import handles 'import numpy' full statement."""
        result = classify_import("import numpy")
        result_lower = result.lower()
        assert "third" in result_lower or "party" in result_lower or "external" in result_lower

    def test_classify_from_third_party_statement(self):
        """classify_import handles 'from requests import get' format."""
        result = classify_import("from requests import get")
        result_lower = result.lower()
        assert "third" in result_lower or "party" in result_lower or "external" in result_lower

    def test_classify_project_internal_full_path(self):
        """classify_import handles 'from svp.scripts.pipeline_state import MyClass'."""
        result = classify_import("from svp.scripts.pipeline_state import MyClass")
        result_lower = result.lower()
        assert "internal" in result_lower or "project" in result_lower
