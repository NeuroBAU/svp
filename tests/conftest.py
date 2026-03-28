"""conftest.py -- pytest configuration for SVP 2.2 test suite.

Adds svp/scripts to sys.path so bare module imports resolve correctly.
This supplements the pythonpath setting in pyproject.toml [tool.pytest.ini_options].
"""
import sys
from pathlib import Path

# Ensure svp/scripts is on the path for bare module imports
_scripts_path = str(Path(__file__).parent.parent / "svp" / "scripts")
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)
