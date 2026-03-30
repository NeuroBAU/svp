"""
Regression test for Bug S3-7: cmd_clean tests must not mock load_config.
The cmd_clean function does not use load_config, so patching it causes
AttributeError failures.
"""
import re
from pathlib import Path


def test_cmd_clean_tests_do_not_mock_load_config():
    """S3-7: cmd_clean tests should not patch load_config (it doesn't exist in the module)."""
    test_file = Path(__file__).parent.parent / "unit_16" / "test_unit_16.py"
    source = test_file.read_text()
    # Find all patch targets referencing load_config for unit_16.stub
    matches = re.findall(r'patch\(["\']src\.unit_16\.stub\.load_config["\']\)', source)
    assert len(matches) == 0, (
        f"Bug S3-7 regression: found {len(matches)} patch(es) targeting "
        f"src.unit_16.stub.load_config in cmd_clean tests — "
        f"load_config does not exist in cmd_clean's module"
    )
