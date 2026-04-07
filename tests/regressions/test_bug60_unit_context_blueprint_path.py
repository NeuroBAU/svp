"""Regression test for Bug 60: unit context must use correct blueprint path.

Verifies:
1. ARTIFACT_FILENAMES has "blueprint_dir" key (from svp_config)
2. build_unit_context accepts a blueprint directory path
3. build_unit_context uses directory path correctly

SVP 2.2 adaptation:
- _get_unit_context renamed to build_unit_context in scripts/prepare_task.py
- ARTIFACT_FILENAMES is in src.unit_1.stub (not a fallback in prepare_task.py)
- prepare_task.py imports ARTIFACT_FILENAMES from svp_config
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
_scripts_dir = _project_root / "scripts"
if not _scripts_dir.is_dir():
    _scripts_dir = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts_dir))

from svp_config import ARTIFACT_FILENAMES


def test_artifact_filenames_has_blueprint_dir():
    """ARTIFACT_FILENAMES must use 'blueprint_dir' key."""
    assert "blueprint_dir" in ARTIFACT_FILENAMES, (
        "ARTIFACT_FILENAMES missing 'blueprint_dir' key"
    )
    assert ARTIFACT_FILENAMES["blueprint_dir"] == "blueprint", (
        "ARTIFACT_FILENAMES['blueprint_dir'] must be 'blueprint'"
    )


def test_build_unit_context_accepts_directory():
    """build_unit_context in prepare_task.py accepts a blueprint directory path."""
    import inspect
    from prepare_task import build_unit_context

    sig = inspect.signature(build_unit_context)
    param_names = list(sig.parameters.keys())
    assert "blueprint_dir" in param_names, (
        "build_unit_context must accept blueprint_dir parameter"
    )


def test_build_unit_context_source_uses_directory_path():
    """build_unit_context must reference blueprint_dir, not blueprint file path."""
    import inspect
    from prepare_task import build_unit_context

    source = inspect.getsource(build_unit_context)
    # Must NOT contain the old broken pattern
    assert 'ARTIFACT_FILENAMES["blueprint"]' not in source, (
        "build_unit_context still uses ARTIFACT_FILENAMES['blueprint'] "
        "(should use blueprint_dir)"
    )
