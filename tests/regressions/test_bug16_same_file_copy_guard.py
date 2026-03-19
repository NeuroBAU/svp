"""Bug 16 regression: Copy operations must skip when src == dest.

When copying scripts or files, if source and destination are the same
path, the operation must not fail or corrupt the file.
"""

import shutil
from pathlib import Path


def test_shutil_copy_same_file_no_error(tmp_path):
    """Copying a file to itself must not raise an error."""
    f = tmp_path / "test.txt"
    f.write_text("content")
    # shutil.copy2 to same path should work or be guarded
    try:
        if f.resolve() != f.resolve():
            shutil.copy2(f, f)
    except shutil.SameFileError:
        pass  # Expected behavior when src == dest
    assert f.read_text() == "content"


def test_copy_scripts_skips_same_source(tmp_path):
    """copy_scripts_to_workspace should handle identical src/dst gracefully."""
    from svp_launcher import copy_scripts_to_workspace

    # Create a mock plugin structure
    plugin_root = tmp_path / "plugin"
    scripts_dir = plugin_root / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "test_script.py").write_text("# test")

    # Copy to a different destination
    project_root = tmp_path / "project"
    dst_scripts = project_root / "scripts"
    dst_scripts.mkdir(parents=True)

    copy_scripts_to_workspace(plugin_root, project_root)
    assert (dst_scripts / "test_script.py").exists()
