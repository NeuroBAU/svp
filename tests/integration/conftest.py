"""
conftest.py for integration tests.

Ensures that cross-unit imports resolve correctly by aliasing the
src.unit_N.stub modules to their short module names as expected by
inter-unit import statements.

Integration tests should be run with:
    python -m pytest tests/integration/ tests/regressions/ -v

This ensures that any regression tests in tests/regressions/ are also
executed as part of the integration test run.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so src.* imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Alias short module names that units import with bare names
import svp.scripts.pipeline_state as pipeline_state_module
sys.modules["pipeline_state"] = pipeline_state_module

import svp.scripts.state_transitions as state_transitions_module
sys.modules["state_transitions"] = state_transitions_module
