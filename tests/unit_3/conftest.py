"""
conftest.py for unit_3 tests.

Ensures that the `pipeline_state` module name resolves to `svp.scripts.pipeline_state`,
which provides PipelineState and DebugSession classes needed by the unit_3 stub.
"""
import sys
import svp.scripts.pipeline_state as pipeline_state_module

sys.modules["pipeline_state"] = pipeline_state_module
