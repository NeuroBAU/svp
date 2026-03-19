"""Bug 5 regression: pytest framework packages must be in toolchain.

The toolchain must list pytest and pytest-cov as framework_packages
so they are installed in the pipeline environment.
"""

import json
from pathlib import Path

from svp_config import get_framework_packages


def _get_toolchain_defaults_dir() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    d = root / "svp" / "scripts" / "toolchain_defaults"
    if d.is_dir():
        return d
    return root / "scripts" / "toolchain_defaults"


def test_framework_packages_include_pytest():
    """Toolchain framework_packages must include pytest."""
    tc_path = _get_toolchain_defaults_dir() / "python_conda_pytest.json"
    tc = json.loads(tc_path.read_text())
    packages = get_framework_packages(tc)
    assert "pytest" in packages


def test_framework_packages_include_pytest_cov():
    """Toolchain framework_packages must include pytest-cov."""
    tc_path = _get_toolchain_defaults_dir() / "python_conda_pytest.json"
    tc = json.loads(tc_path.read_text())
    packages = get_framework_packages(tc)
    assert "pytest-cov" in packages
