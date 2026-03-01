"""
conftest.py for unit_10 tests.

Ensures that the `pipeline_state` module name resolves to `svp.scripts.pipeline_state`
and `state_transitions` resolves to `svp.scripts.state_transitions`, which provide
PipelineState, DebugSession, and TransitionError needed by the unit_10 stub.
"""
import sys
import svp.scripts.pipeline_state as pipeline_state_module
sys.modules["pipeline_state"] = pipeline_state_module

import svp.scripts.state_transitions as state_transitions_module
sys.modules["state_transitions"] = state_transitions_module
