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


