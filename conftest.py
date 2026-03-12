"""
Root conftest.py for the SVP repository test suite.

Adds svp/scripts/ to sys.path so that the internal script modules
can use bare imports (e.g., from pipeline_state import ...) as they
do at runtime when invoked via PYTHONPATH=svp/scripts.

Also adds src/ to sys.path for svp_core imports.
"""

import sys
from pathlib import Path

# Add svp/scripts to path for bare imports used within scripts
SCRIPTS_DIR = Path(__file__).resolve().parent / "svp" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Also add the repo root for svp package imports
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Add src/ to path for svp_core imports
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
