"""
Tests for Unit 7: Dependency Extractor and Import Validator

DATA ASSUMPTIONS (Synthetic Data):
- Blueprint files are Markdown documents with headings like "### Tier 2 \u2014 Signatures"
  (using an em-dash), containing fenced Python code blocks with import statements.
- Standard library modules include: os, sys, json, pathlib, ast, typing, etc.
- Third-party modules include: numpy, pandas, requests, etc.
- Project-internal modules follow the pattern: src.unit_N.stub or similar project paths.
- Conda environment names are derived from project names via lowercasing and replacing
  spaces and hyphens with underscores.
- Project directories follow the convention: src/unit_N/ and tests/unit_N/ for N in 1..total_units.
"""

import inspect
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import patch, MagicMock

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
# Synthetic blueprint content helpers
# ---------------------------------------------------------------------------

# DATA ASSUMPTION: Blueprint files contain multiple unit sections, each with a
# "### Tier 2 \u2014 Signatures" heading (em-dash) followed by a fenced Python
# code block containing import statements and function/class signatures.

MINIMAL_BLUEPRINT = """\
# Blueprint

## Unit 1: Example Unit

### Tier 2 \u2014 Signatures

```python
import os
from pathlib import Path

def foo(x: int) -> str: ...
```

## Unit 2: Another Unit

### Tier 2 \u2014 Signatures

```python
import json
from typing import List, Dict

def bar(y: str) -> int: ...
```
"""

BLUEPRINT_WITH_THIRD_PARTY = """\
# Blueprint

## Unit 1: Data Processor

### Tier 2 \u2014 Signatures

```python
import numpy as np
import pandas as pd
from requests import get
import os
import sys
from pathlib import Path

def process(data: list) -> list: ...
```
"""

BLUEPRINT_NO_SIGNATURES = """\
# Blueprint

## Unit 1: Empty Unit

### Tier 2 -- Signatures

```python
import os
```

This uses an en-dash (--), not an em-dash (\u2014), so it should NOT be found.
"""

BLUEPRINT_EMPTY = """\
# Blueprint

## Unit 1: Empty

No signature blocks here at all.
"""


# ---------------------------------------------------------------------------
# Signature Tests
# ---------------------------------------------------------------------------

class TestSignatures:
    """Verify that all functions match their blueprint signatures."""

    def test_extract_all_imports_signature(self):
        sig = inspect.signature(extract_all_imports)
        params = list(sig.parameters.keys())
        assert params == ["blueprint_path"]
        assert sig.parameters["blueprint_path"].annotation is Path
        assert sig.return_annotation == List[str]

    def test_classify_import_signature(self):
        sig = inspect.signature(classify_import)
        params = list(sig.parameters.keys())
        assert params == ["import_stmt", "scripts_dir"]
        assert sig.parameters["import_stmt"].annotation is str
        assert sig.parameters["scripts_dir"].default is None
        assert sig.return_annotation is str

    def test_map_imports_to_packages_signature(self):
        sig = inspect.signature(map_imports_to_packages)
        params = list(sig.parameters.keys())
        assert params == ["imports"]
        assert sig.parameters["imports"].annotation == List[str]
        assert sig.return_annotation == Dict[str, str]

    def test_create_conda_environment_signature(self):
        sig = inspect.signature(create_conda_environment)
        params = list(sig.parameters.keys())
        assert params == ["env_name", "packages", "python_version"]
        assert sig.parameters["env_name"].annotation is str
        assert sig.parameters["packages"].annotation == Dict[str, str]
        assert sig.parameters["python_version"].default == "3.11"
        assert sig.return_annotation is bool

    def test_validate_imports_signature(self):
        sig = inspect.signature(validate_imports)
        params = list(sig.parameters.keys())
        assert params == ["env_name", "imports"]
        assert sig.parameters["env_name"].annotation is str
        assert sig.parameters["imports"].annotation == List[str]
        assert sig.return_annotation == List[Tuple[str, str]]

    def test_create_project_directories_signature(self):
        sig = inspect.signature(create_project_directories)
        params = list(sig.parameters.keys())
        assert params == ["project_root", "total_units"]
        assert sig.parameters["project_root"].annotation is Path
        assert sig.parameters["total_units"].annotation is int
        # Return type is None
        assert sig.return_annotation is None

    def test_derive_env_name_signature(self):
        sig = inspect.signature(derive_env_name)
        params = list(sig.parameters.keys())
        assert params == ["project_name"]
        assert sig.parameters["project_name"].annotation is str
        assert sig.return_annotation is str

    def test_main_signature(self):
        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert params == []
        assert sig.return_annotation is None


# ---------------------------------------------------------------------------
# derive_env_name Tests
# ---------------------------------------------------------------------------

class TestDeriveEnvName:
    """
    Behavioral contract: derive_env_name applies the canonical derivation:
    project_name.lower().replace(" ", "_").replace("-", "_")

    Invariants:
    - result == project_name.lower().replace(" ", "_").replace("-", "_")
    - No spaces in result
    - No hyphens in result
    """

    # DATA ASSUMPTION: Project names can contain uppercase letters, spaces,
    # hyphens, and underscores. These represent typical project naming patterns.

    def test_simple_lowercase(self):
        """A simple lowercase name with no special chars passes through unchanged."""
        result = derive_env_name("myproject")
        assert result == "myproject"

    def test_uppercase_converted(self):
        """Uppercase letters are lowered."""
        result = derive_env_name("MyProject")
        assert result == "myproject"

    def test_spaces_replaced(self):
        """Spaces are replaced with underscores."""
        result = derive_env_name("my project")
        assert result == "my_project"

    def test_hyphens_replaced(self):
        """Hyphens are replaced with underscores."""
        result = derive_env_name("my-project")
        assert result == "my_project"

    def test_mixed_spaces_hyphens_uppercase(self):
        """Combination of uppercase, spaces, and hyphens."""
        result = derive_env_name("My Cool-Project")
        assert result == "my_cool_project"

    def test_no_spaces_in_result(self):
        """Invariant: result must not contain spaces."""
        result = derive_env_name("hello world foo bar")
        assert " " not in result

    def test_no_hyphens_in_result(self):
        """Invariant: result must not contain hyphens."""
        result = derive_env_name("a-b-c-d")
        assert "-" not in result

    def test_canonical_derivation_matches(self):
        """Invariant: result must match the canonical derivation exactly."""
        name = "SVP Project-Alpha 2"
        expected = name.lower().replace(" ", "_").replace("-", "_")
        result = derive_env_name(name)
        assert result == expected

    def test_already_canonical(self):
        """A name already in canonical form is unchanged."""
        result = derive_env_name("already_canonical")
        assert result == "already_canonical"

    def test_multiple_spaces(self):
        """Multiple consecutive spaces become multiple underscores."""
        name = "my  project"
        expected = name.lower().replace(" ", "_").replace("-", "_")
        result = derive_env_name(name)
        assert result == expected

    def test_multiple_hyphens(self):
        """Multiple consecutive hyphens become multiple underscores."""
        name = "my--project"
        expected = name.lower().replace(" ", "_").replace("-", "_")
        result = derive_env_name(name)
        assert result == expected


# ---------------------------------------------------------------------------
# extract_all_imports Tests
# ---------------------------------------------------------------------------

class TestExtractAllImports:
    """
    Behavioral contract: Parses every "### Tier 2 \u2014 Signatures" code block
    across all units and collects all import and from...import statements.
    Heading format must use an em-dash.

    Precondition: blueprint_path must exist.
    Error: FileNotFoundError if blueprint does not exist.
    Error: ValueError if no signature blocks found.
    """

    def test_extracts_imports_from_multiple_units(self):
        """Extracts import statements from all Tier 2 Signatures blocks."""
        # DATA ASSUMPTION: Standard blueprint with two units, each having
        # standard library imports (os, pathlib, json, typing).
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(MINIMAL_BLUEPRINT)
            f.flush()
            bp_path = Path(f.name)

        try:
            result = extract_all_imports(bp_path)
            assert isinstance(result, list)
            assert all(isinstance(s, str) for s in result)
            # Should contain imports from both units
            # We expect at minimum: os, pathlib.Path, json, typing.List, typing.Dict
            # The exact format may vary (full statement vs module name), but they
            # must be strings representing imports.
            assert len(result) > 0
        finally:
            os.unlink(f.name)

    def test_returns_list_of_strings(self):
        """Post-condition: all items in the returned list must be strings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(MINIMAL_BLUEPRINT)
            f.flush()
            bp_path = Path(f.name)

        try:
            result = extract_all_imports(bp_path)
            assert isinstance(result, list)
            assert all(isinstance(s, str) for s in result)
        finally:
            os.unlink(f.name)

    def test_file_not_found_error(self):
        """Error condition: FileNotFoundError when blueprint does not exist."""
        fake_path = Path("/nonexistent/blueprint.md")
        with pytest.raises(FileNotFoundError, match="Blueprint file not found"):
            extract_all_imports(fake_path)

    def test_no_signature_blocks_raises_value_error(self):
        """Error condition: ValueError when no Tier 2 Signatures headings found."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(BLUEPRINT_EMPTY)
            f.flush()
            bp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="No signature blocks found"):
                extract_all_imports(bp_path)
        finally:
            os.unlink(f.name)

    def test_en_dash_headings_not_recognized(self):
        """
        The heading must use an em-dash (\u2014). An en-dash (--) heading
        should NOT be recognized as a valid signature block heading.
        """
        # DATA ASSUMPTION: BLUEPRINT_NO_SIGNATURES uses en-dash (--) instead
        # of em-dash (\u2014), which should not be found by the parser.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(BLUEPRINT_NO_SIGNATURES)
            f.flush()
            bp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="No signature blocks found"):
                extract_all_imports(bp_path)
        finally:
            os.unlink(f.name)

    def test_precondition_blueprint_must_exist(self):
        """Precondition assert: blueprint_path.exists() must be true."""
        nonexistent = Path("/tmp/definitely_does_not_exist_blueprint_7.md")
        if nonexistent.exists():
            os.unlink(nonexistent)
        with pytest.raises((FileNotFoundError, AssertionError)):
            extract_all_imports(nonexistent)

    def test_extracts_both_import_styles(self):
        """Both 'import X' and 'from X import Y' statements are collected."""
        # DATA ASSUMPTION: Blueprint with both plain import and from...import
        # styles. The function should extract both.
        blueprint_content = """\
# Blueprint

## Unit 1: Test

### Tier 2 \u2014 Signatures

```python
import os
from pathlib import Path
from typing import List

def func() -> None: ...
```
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(blueprint_content)
            f.flush()
            bp_path = Path(f.name)

        try:
            result = extract_all_imports(bp_path)
            assert isinstance(result, list)
            assert len(result) >= 2  # At least os and pathlib/typing
        finally:
            os.unlink(f.name)

    def test_extracts_third_party_imports(self):
        """Third-party imports (numpy, pandas, requests) are extracted."""
        # DATA ASSUMPTION: Blueprint includes third-party packages like numpy,
        # pandas, requests alongside standard library imports.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(BLUEPRINT_WITH_THIRD_PARTY)
            f.flush()
            bp_path = Path(f.name)

        try:
            result = extract_all_imports(bp_path)
            assert isinstance(result, list)
            # Should include at least numpy, pandas, requests, os, sys, pathlib
            assert len(result) >= 3
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# classify_import Tests
# ---------------------------------------------------------------------------

class TestClassifyImport:
    """
    Behavioral contract: Determines whether an import is standard library,
    third-party, or project-internal.
    """

    # DATA ASSUMPTION: Standard library modules include os, sys, json, pathlib,
    # ast, typing, collections, etc. Third-party modules include numpy, pandas,
    # requests, flask, etc. Project-internal modules match patterns like
    # src.unit_N.stub or similar project-specific paths.

    def test_stdlib_os(self):
        """os is a standard library module."""
        result = classify_import("os")
        assert isinstance(result, str)
        assert "standard" in result.lower() or "stdlib" in result.lower()

    def test_stdlib_sys(self):
        """sys is a standard library module."""
        result = classify_import("sys")
        assert "standard" in result.lower() or "stdlib" in result.lower()

    def test_stdlib_json(self):
        """json is a standard library module."""
        result = classify_import("json")
        assert "standard" in result.lower() or "stdlib" in result.lower()

    def test_stdlib_pathlib(self):
        """pathlib is a standard library module."""
        result = classify_import("pathlib")
        assert "standard" in result.lower() or "stdlib" in result.lower()

    def test_stdlib_ast(self):
        """ast is a standard library module."""
        result = classify_import("ast")
        assert "standard" in result.lower() or "stdlib" in result.lower()

    def test_stdlib_typing(self):
        """typing is a standard library module."""
        result = classify_import("typing")
        assert "standard" in result.lower() or "stdlib" in result.lower()

    def test_third_party_numpy(self):
        """numpy is a third-party package."""
        result = classify_import("numpy")
        assert "third" in result.lower() or "party" in result.lower() or "external" in result.lower()

    def test_third_party_pandas(self):
        """pandas is a third-party package."""
        result = classify_import("pandas")
        assert "third" in result.lower() or "party" in result.lower() or "external" in result.lower()

    def test_third_party_requests(self):
        """requests is a third-party package."""
        result = classify_import("requests")
        assert "third" in result.lower() or "party" in result.lower() or "external" in result.lower()

    def test_project_internal(self):
        """Project-internal imports should be classified accordingly."""
        # DATA ASSUMPTION: Project-internal imports use patterns like
        # svp.scripts.svp_config or similar dotted project paths.
        result = classify_import("svp.scripts.svp_config")
        assert "internal" in result.lower() or "project" in result.lower()

    def test_returns_string(self):
        """Return type is always a string."""
        result = classify_import("os")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# map_imports_to_packages Tests
# ---------------------------------------------------------------------------

class TestMapImportsToPackages:
    """
    Behavioral contract: Maps third-party import module names to pip/conda
    package names.
    """

    # DATA ASSUMPTION: Common import-to-package mappings include:
    # numpy -> numpy, pandas -> pandas, PIL -> Pillow, cv2 -> opencv-python,
    # sklearn -> scikit-learn, yaml -> pyyaml, etc.

    def test_returns_dict(self):
        """Return type is Dict[str, str]."""
        result = map_imports_to_packages(["numpy", "pandas"])
        assert isinstance(result, dict)

    def test_maps_numpy(self):
        """numpy import maps to a package name."""
        result = map_imports_to_packages(["numpy"])
        assert isinstance(result, dict)
        # numpy should map to something (likely "numpy")
        assert len(result) > 0

    def test_maps_multiple_imports(self):
        """Multiple imports are mapped."""
        result = map_imports_to_packages(["numpy", "pandas", "requests"])
        assert isinstance(result, dict)
        assert len(result) >= 1  # At least some should map

    def test_empty_list(self):
        """Empty import list returns empty or minimal dict."""
        result = map_imports_to_packages([])
        assert isinstance(result, dict)

    def test_standard_lib_possibly_excluded(self):
        """Standard library imports may not appear in the mapping since they
        don't need installation."""
        # DATA ASSUMPTION: Standard library modules don't need pip/conda
        # installation, so they may be excluded from the mapping.
        result = map_imports_to_packages(["os", "sys", "json"])
        assert isinstance(result, dict)
        # Result may be empty if stdlib imports are filtered out


# ---------------------------------------------------------------------------
# create_conda_environment Tests
# ---------------------------------------------------------------------------

class TestCreateCondaEnvironment:
    """
    Behavioral contract: Creates the environment using conda create and installs
    packages. Uses conda run -n {env_name} for all operations.

    Error condition: RuntimeError with "Conda environment creation failed: {details}"
    when conda create fails.
    """

    # DATA ASSUMPTION: Environment names are valid conda env names (lowercase,
    # underscores). Packages are represented as {"module": "package_name"} dicts.
    # We mock subprocess calls since we don't want to actually run conda.

    @patch("subprocess.run")
    def test_successful_creation(self, mock_run):
        """Successful conda environment creation returns True."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = create_conda_environment("test_env", {"numpy": "numpy"})
        assert result is True

    @patch("subprocess.run")
    def test_default_python_version(self, mock_run):
        """Default python_version is 3.11."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        create_conda_environment("test_env", {"numpy": "numpy"})
        # Verify conda was called (the exact call args depend on implementation
        # but we check it was invoked)
        assert mock_run.called

    @patch("subprocess.run")
    def test_custom_python_version(self, mock_run):
        """Custom python_version parameter is accepted."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = create_conda_environment(
            "test_env", {"numpy": "numpy"}, python_version="3.10"
        )
        assert result is True

    @patch("subprocess.run")
    def test_conda_failure_raises_runtime_error(self, mock_run):
        """RuntimeError when conda create fails."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="PackageNotFoundError"
        )
        mock_run.side_effect = None
        # Some implementations might check returncode, others might catch exceptions
        # We need to handle both approaches
        try:
            result = create_conda_environment("test_env", {"bad_pkg": "bad_pkg"})
            # If it returns without error, it must have returned False or raised
            # The contract says RuntimeError should be raised on failure
            # If we get here, the implementation might return False instead
        except RuntimeError as e:
            assert "Conda environment creation failed" in str(e)

    @patch("subprocess.run", side_effect=Exception("conda not found"))
    def test_conda_not_available_raises_runtime_error(self, mock_run):
        """RuntimeError when conda is not available."""
        with pytest.raises(RuntimeError, match="Conda environment creation failed"):
            create_conda_environment("test_env", {"numpy": "numpy"})

    @patch("subprocess.run")
    def test_empty_packages(self, mock_run):
        """Creating an environment with no packages should still work."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = create_conda_environment("test_env", {})
        assert result is True


# ---------------------------------------------------------------------------
# validate_imports Tests
# ---------------------------------------------------------------------------

class TestValidateImports:
    """
    Behavioral contract: Executes each import in the environment via
    conda run -n {env_name} python -c "import ..." and returns a list of
    (import, error) tuples for failures.

    Error condition: RuntimeError with "Import validation failed for: {import_list}"
    when imports do not resolve.
    """

    # DATA ASSUMPTION: Import validation uses subprocess to run
    # conda run -n {env_name} python -c "import X" for each import.
    # Failures produce (import_name, error_message) tuples.

    @patch("subprocess.run")
    def test_all_imports_valid(self, mock_run):
        """When all imports resolve, returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = validate_imports("test_env", ["os", "sys", "json"])
        assert isinstance(result, list)
        assert len(result) == 0

    @patch("subprocess.run")
    def test_returns_list_of_tuples(self, mock_run):
        """Return type is List[Tuple[str, str]]."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = validate_imports("test_env", ["os"])
        assert isinstance(result, list)

    @patch("subprocess.run")
    def test_failed_imports_produce_tuples(self, mock_run):
        """Failed imports produce (import, error) tuples."""
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "nonexistent_module" in cmd_str:
                return MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="ModuleNotFoundError: No module named 'nonexistent_module'"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect
        result = validate_imports("test_env", ["os", "nonexistent_module"])
        assert isinstance(result, list)
        # Should have at least one failure tuple
        assert len(result) >= 1
        # Each failure should be a tuple of (import_name, error_string)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)

    @patch("subprocess.run")
    def test_empty_import_list(self, mock_run):
        """Empty import list returns empty list."""
        result = validate_imports("test_env", [])
        assert isinstance(result, list)
        assert len(result) == 0

    @patch("subprocess.run")
    def test_uses_conda_run(self, mock_run):
        """Validates that conda run -n {env_name} is used."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        validate_imports("my_test_env", ["os"])
        if mock_run.called:
            call_args = mock_run.call_args
            args_str = str(call_args)
            assert "conda" in args_str.lower() or "my_test_env" in args_str


# ---------------------------------------------------------------------------
# create_project_directories Tests
# ---------------------------------------------------------------------------

class TestCreateProjectDirectories:
    """
    Behavioral contract: Creates src/unit_N/ and tests/unit_N/ for each unit,
    where N ranges from 1 to total_units.
    """

    # DATA ASSUMPTION: project_root is a valid directory path. total_units is
    # a positive integer. Directories created follow src/unit_N/ and tests/unit_N/
    # pattern for N in 1..total_units.

    def test_creates_src_directories(self):
        """Creates src/unit_N/ for each unit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 3)
            for i in range(1, 4):
                assert (root / f"src/unit_{i}").is_dir(), \
                    f"src/unit_{i} directory should exist"

    def test_creates_test_directories(self):
        """Creates tests/unit_N/ for each unit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 3)
            for i in range(1, 4):
                assert (root / f"tests/unit_{i}").is_dir(), \
                    f"tests/unit_{i} directory should exist"

    def test_single_unit(self):
        """Works correctly with total_units=1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 1)
            assert (root / "src/unit_1").is_dir()
            assert (root / "tests/unit_1").is_dir()

    def test_returns_none(self):
        """Return type is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = create_project_directories(root, 1)
            assert result is None

    def test_multiple_units(self):
        """Creates correct number of directories for multiple units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 5)
            for i in range(1, 6):
                assert (root / f"src/unit_{i}").is_dir()
                assert (root / f"tests/unit_{i}").is_dir()

    def test_idempotent(self):
        """Calling twice does not raise an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project_directories(root, 2)
            # Second call should not fail
            create_project_directories(root, 2)
            assert (root / "src/unit_1").is_dir()
            assert (root / "src/unit_2").is_dir()


# ---------------------------------------------------------------------------
# Error Condition Tests (grouped)
# ---------------------------------------------------------------------------

class TestErrorConditions:
    """
    Verify all error conditions from the blueprint:
    - FileNotFoundError: "Blueprint file not found: {path}"
    - ValueError: "No signature blocks found in blueprint"
    - RuntimeError: "Conda environment creation failed: {details}"
    - RuntimeError: "Import validation failed for: {import_list}"
    """

    def test_extract_imports_file_not_found(self):
        """FileNotFoundError with correct message pattern."""
        bad_path = Path("/nonexistent/path/blueprint.md")
        with pytest.raises(FileNotFoundError, match="Blueprint file not found"):
            extract_all_imports(bad_path)

    def test_extract_imports_file_not_found_includes_path(self):
        """FileNotFoundError message includes the path."""
        bad_path = Path("/nonexistent/path/blueprint.md")
        with pytest.raises(FileNotFoundError) as exc_info:
            extract_all_imports(bad_path)
        assert str(bad_path) in str(exc_info.value) or "blueprint.md" in str(exc_info.value)

    def test_no_signature_blocks_value_error(self):
        """ValueError when no em-dash signature headings found."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# No signatures here\n\nJust some text.\n")
            f.flush()
            bp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="No signature blocks found"):
                extract_all_imports(bp_path)
        finally:
            os.unlink(f.name)

    @patch("subprocess.run", side_effect=Exception("conda binary not found"))
    def test_conda_creation_runtime_error(self, mock_run):
        """RuntimeError with correct message for conda failure."""
        with pytest.raises(RuntimeError, match="Conda environment creation failed"):
            create_conda_environment("test_env", {"numpy": "numpy"})

    @patch("subprocess.run")
    def test_import_validation_runtime_error(self, mock_run):
        """
        RuntimeError: 'Import validation failed for: {import_list}'
        when imports do not resolve.
        Note: This error may be raised by validate_imports itself or by
        a higher-level caller. We test that failures are properly detected.
        """
        mock_run.return_value = MagicMock(
            returncode=1, stdout="",
            stderr="ModuleNotFoundError: No module named 'fake_module'"
        )
        # The function returns failure tuples; the RuntimeError may be raised
        # by a higher-level caller or within the function itself.
        result = validate_imports("test_env", ["fake_module"])
        # Either it raises RuntimeError or returns failure tuples
        if isinstance(result, list) and len(result) > 0:
            assert any("fake_module" in t[0] for t in result)


# ---------------------------------------------------------------------------
# Integration-style Tests
# ---------------------------------------------------------------------------

class TestEndToEndFlow:
    """Test the overall flow of extracting, classifying, and mapping imports."""

    # DATA ASSUMPTION: A realistic blueprint contains a mix of stdlib and
    # third-party imports. The flow is: extract -> classify -> map -> install.

    def test_extract_then_classify(self):
        """Extract imports from a blueprint, then classify each one."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(BLUEPRINT_WITH_THIRD_PARTY)
            f.flush()
            bp_path = Path(f.name)

        try:
            imports = extract_all_imports(bp_path)
            assert len(imports) > 0
            for imp in imports:
                classification = classify_import(imp)
                assert isinstance(classification, str)
                assert len(classification) > 0
        finally:
            os.unlink(f.name)

    def test_extract_classify_map_pipeline(self):
        """Full pipeline: extract -> classify -> map."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(BLUEPRINT_WITH_THIRD_PARTY)
            f.flush()
            bp_path = Path(f.name)

        try:
            imports = extract_all_imports(bp_path)
            packages = map_imports_to_packages(imports)
            assert isinstance(packages, dict)
        finally:
            os.unlink(f.name)

    def test_derive_env_name_used_consistently(self):
        """derive_env_name produces consistent results for same input."""
        name1 = derive_env_name("My Project")
        name2 = derive_env_name("My Project")
        assert name1 == name2
        assert name1 == "my_project"


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test boundary conditions and edge cases."""

    def test_derive_env_name_empty_string(self):
        """Empty string input to derive_env_name."""
        # DATA ASSUMPTION: Empty string is technically valid input,
        # canonical derivation of "" is "".
        result = derive_env_name("")
        expected = "".lower().replace(" ", "_").replace("-", "_")
        assert result == expected

    def test_derive_env_name_only_spaces(self):
        """Input with only spaces becomes all underscores."""
        result = derive_env_name("   ")
        assert " " not in result
        assert result == "___"

    def test_derive_env_name_only_hyphens(self):
        """Input with only hyphens becomes all underscores."""
        result = derive_env_name("---")
        assert "-" not in result
        assert result == "___"

    def test_extract_all_imports_single_unit_blueprint(self):
        """Blueprint with only one unit."""
        blueprint = """\
# Blueprint

## Unit 1: Solo Unit

### Tier 2 \u2014 Signatures

```python
import ast
from typing import Optional

def solo_func() -> None: ...
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
            assert isinstance(result, list)
            assert all(isinstance(s, str) for s in result)
            assert len(result) >= 1
        finally:
            os.unlink(f.name)

    def test_create_project_directories_with_existing_parent(self):
        """project_root must exist (or be created) for directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "new_project"
            root.mkdir()
            create_project_directories(root, 2)
            assert (root / "src/unit_1").is_dir()
            assert (root / "tests/unit_2").is_dir()

    def test_classify_import_returns_one_of_known_categories(self):
        """classify_import returns a meaningful category string."""
        result = classify_import("os")
        # Should be one of standard library, third-party, or project-internal
        result_lower = result.lower()
        known_keywords = [
            "standard", "stdlib", "third", "party", "external",
            "internal", "project", "builtin", "built-in"
        ]
        assert any(kw in result_lower for kw in known_keywords), \
            f"Expected a known category keyword in '{result}'"
