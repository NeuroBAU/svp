"""Regression test for Bug 60: _get_unit_context uses wrong blueprint path.

Verifies:
1. Fallback ARTIFACT_FILENAMES has "blueprint_dir" (not "blueprint")
2. _get_unit_context passes a directory path (not a file path) to build_unit_context
3. _get_unit_context calls build_unit_context with correct blueprint dir
"""

import sys
import inspect
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path for imports -- support both workspace and delivered repo layouts
_project_root = Path(__file__).resolve().parent.parent.parent
_scripts_dir = _project_root / "scripts"
if not _scripts_dir.is_dir():
    _scripts_dir = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts_dir))
sys.path.insert(0, str(_project_root / "src" / "unit_1"))


def _find_prepare_task_path() -> Path:
    """Locate prepare_task.py in either workspace or delivered repo layout."""
    candidates = [
        _project_root / "scripts" / "prepare_task.py",
        _project_root / "svp" / "scripts" / "prepare_task.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Cannot find prepare_task.py in any known location")


def test_fallback_artifact_filenames_has_blueprint_dir():
    """Fallback ARTIFACT_FILENAMES must use 'blueprint_dir', not 'blueprint'."""
    prepare_task_path = _find_prepare_task_path()
    source = prepare_task_path.read_text(encoding="utf-8")

    # The fallback dict must NOT have "blueprint": "blueprint.md"
    assert '"blueprint": "blueprint.md"' not in source, (
        "Fallback ARTIFACT_FILENAMES still has stale 'blueprint' key "
        "(should be 'blueprint_dir': 'blueprint')"
    )
    # It MUST have "blueprint_dir": "blueprint"
    assert '"blueprint_dir": "blueprint"' in source, (
        "Fallback ARTIFACT_FILENAMES missing 'blueprint_dir' key"
    )


def test_get_unit_context_uses_directory_path():
    """_get_unit_context must pass a directory path to build_unit_context."""
    from prepare_task import _get_unit_context

    source = inspect.getsource(_get_unit_context)
    # Must NOT contain the old broken pattern
    assert 'ARTIFACT_FILENAMES["blueprint"]' not in source, (
        "_get_unit_context still uses ARTIFACT_FILENAMES['blueprint'] "
        "(should use blueprint_dir)"
    )
    # Must reference blueprint_dir
    assert "blueprint_dir" in source, (
        "_get_unit_context does not reference 'blueprint_dir'"
    )


def test_get_unit_context_passes_directory_to_build_unit_context(tmp_path):
    """_get_unit_context must call build_unit_context with a directory, not a file."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()

    mock_build = MagicMock(return_value="Unit 1 context here")

    with patch.dict("sys.modules", {"blueprint_extractor": MagicMock()}):
        sys.modules["blueprint_extractor"].build_unit_context = mock_build

        from prepare_task import _get_unit_context

        result = _get_unit_context(tmp_path, 1)

    # Verify build_unit_context was called with the directory path
    mock_build.assert_called_once()
    call_args = mock_build.call_args
    bp_path_arg = call_args[0][0]

    # The path should be a directory (blueprint/), not a file (blueprint/blueprint.md)
    assert str(bp_path_arg).endswith("blueprint"), (
        f"Expected path ending with 'blueprint' directory, got: {bp_path_arg}"
    )
    assert not str(bp_path_arg).endswith(".md"), (
        f"Path should be a directory, not a .md file: {bp_path_arg}"
    )
    assert result == "Unit 1 context here"
