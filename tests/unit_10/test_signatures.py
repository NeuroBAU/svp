"""
Tests for Unit 10 function and data signatures.

Verifies that all public functions and data constants exist with the correct
parameter names, types, and structure as defined in the blueprint.

DATA ASSUMPTION: No domain-specific data -- these are pure signature checks
against the blueprint's Tier 2 specifications.
"""

import pytest
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional

from svp.scripts.routing import (
    # Data contracts
    GATE_VOCABULARY,
    AGENT_STATUS_LINES,
    CROSS_AGENT_STATUS,
    COMMAND_STATUS_PATTERNS,
    # Routing functions
    route,
    format_action_block,
    derive_env_name_from_state,
    # Dispatch functions
    dispatch_status,
    dispatch_gate_response,
    dispatch_agent_status,
    dispatch_command_status,
    # Run tests wrapper
    run_pytest,
    # CLI entry points
    routing_main,
    update_state_main,
    run_tests_main,
)


class TestDataContractSignatures:
    """Verify data constant types and structure."""

    def test_gate_vocabulary_type(self):
        assert isinstance(GATE_VOCABULARY, dict)

    def test_agent_status_lines_type(self):
        assert isinstance(AGENT_STATUS_LINES, dict)

    def test_cross_agent_status_type(self):
        assert isinstance(CROSS_AGENT_STATUS, str)

    def test_command_status_patterns_type(self):
        assert isinstance(COMMAND_STATUS_PATTERNS, list)


class TestRouteFunctionSignatures:
    """Verify routing function signatures match the blueprint."""

    def test_route_signature(self):
        sig = inspect.signature(route)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "project_root" in params

    def test_format_action_block_signature(self):
        sig = inspect.signature(format_action_block)
        params = list(sig.parameters.keys())
        assert "action" in params

    def test_derive_env_name_from_state_signature(self):
        sig = inspect.signature(derive_env_name_from_state)
        params = list(sig.parameters.keys())
        assert "state" in params


class TestDispatchFunctionSignatures:
    """Verify dispatch function signatures match the blueprint."""

    def test_dispatch_status_signature(self):
        sig = inspect.signature(dispatch_status)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "status_line" in params
        assert "gate_id" in params
        assert "unit" in params
        assert "phase" in params
        assert "project_root" in params

    def test_dispatch_gate_response_signature(self):
        sig = inspect.signature(dispatch_gate_response)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "gate_id" in params
        assert "response" in params
        assert "project_root" in params

    def test_dispatch_agent_status_signature(self):
        sig = inspect.signature(dispatch_agent_status)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "agent_type" in params
        assert "status_line" in params
        assert "unit" in params
        assert "phase" in params
        assert "project_root" in params

    def test_dispatch_command_status_signature(self):
        sig = inspect.signature(dispatch_command_status)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "status_line" in params
        assert "unit" in params
        assert "phase" in params
        assert "project_root" in params


class TestRunPytestSignature:
    """Verify run_pytest function signature."""

    def test_run_pytest_signature(self):
        sig = inspect.signature(run_pytest)
        params = list(sig.parameters.keys())
        assert "test_path" in params
        assert "env_name" in params
        assert "project_root" in params


class TestCLIEntryPointSignatures:
    """Verify CLI entry point signatures."""

    def test_routing_main_signature(self):
        sig = inspect.signature(routing_main)
        # No required parameters -- it's a CLI entry point
        params = sig.parameters
        required = [
            p for p in params.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required) == 0, "routing_main should take no required arguments"

    def test_update_state_main_signature(self):
        sig = inspect.signature(update_state_main)
        params = sig.parameters
        required = [
            p for p in params.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required) == 0, "update_state_main should take no required arguments"

    def test_run_tests_main_signature(self):
        sig = inspect.signature(run_tests_main)
        params = sig.parameters
        required = [
            p for p in params.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required) == 0, "run_tests_main should take no required arguments"


class TestAllFunctionsCallable:
    """Verify all expected functions are importable and callable."""

    def test_route_callable(self):
        assert callable(route)

    def test_format_action_block_callable(self):
        assert callable(format_action_block)

    def test_derive_env_name_from_state_callable(self):
        assert callable(derive_env_name_from_state)

    def test_dispatch_status_callable(self):
        assert callable(dispatch_status)

    def test_dispatch_gate_response_callable(self):
        assert callable(dispatch_gate_response)

    def test_dispatch_agent_status_callable(self):
        assert callable(dispatch_agent_status)

    def test_dispatch_command_status_callable(self):
        assert callable(dispatch_command_status)

    def test_run_pytest_callable(self):
        assert callable(run_pytest)

    def test_routing_main_callable(self):
        assert callable(routing_main)

    def test_update_state_main_callable(self):
        assert callable(update_state_main)

    def test_run_tests_main_callable(self):
        assert callable(run_tests_main)
