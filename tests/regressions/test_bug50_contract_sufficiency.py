"""Bug 50 regression test: contract sufficiency and boundary
violations in blueprint.

Verifies that implementations contain the critical data values
and behavioral details that the contracts should specify.

Adapted for SVP 2.2 API:
- PipelineState is a dataclass from src.unit_5.stub
- State transition functions in src.unit_6.stub (no project_root arg)
- dispatch_agent_status(state, agent_type, status_line, project_root) -- 4 args
- route() reads state from disk (no state arg)
- Action block keys: action_type, agent_type, gate_id (lowercase)
- Tests referencing SVP 2.1-only internals (svp_config, stub_generator,
  svp_launcher, prepare_task) are skipped.
"""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from pipeline_state import PipelineState, save_state
from state_transitions import (
    advance_stage,
    advance_sub_stage,
    rollback_to_unit,
)
from routing import (
    dispatch_agent_status,
    GATE_VOCABULARY,
)


# ======================================================= #
# Unit 3 tests                                            #
# ======================================================= #


class TestUnit3Rollback:
    """Verify rollback removes later verified units."""

    def test_rollback_removes_verified_units(self) -> None:
        """Rollback removes verified_units >= target unit."""
        state = PipelineState(
            stage="3",
            sub_stage="stub_generation",
            current_unit=3,
            total_units=3,
            verified_units=[
                {"unit": 1, "timestamp": "t1"},
                {"unit": 2, "timestamp": "t2"},
            ],
        )
        result = rollback_to_unit(state, 1)
        # Only units < 1 remain (i.e., none)
        assert len(result.verified_units) == 0
        assert result.current_unit == 1
        assert result.stage == "3"
        assert result.sub_stage == "stub_generation"


class TestUnit3Immutability:
    """Verify transition functions don't mutate input."""

    def test_transitions_do_not_mutate_input(self) -> None:
        state = PipelineState(
            stage="0",
            sub_stage="hook_activation",
        )
        original_stage = state.stage
        original_sub = state.sub_stage

        # advance_stage returns new state, does not mutate
        new = advance_stage(state, "1")
        assert state.stage == original_stage, "advance_stage mutated input"
        assert state.sub_stage == original_sub, "advance_stage mutated input"
        assert new.stage == "1"

        # advance_sub_stage returns new state, does not mutate
        state2 = PipelineState(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
            total_units=3,
        )
        orig2_sub = state2.sub_stage
        new2 = advance_sub_stage(state2, "test_generation")
        assert state2.sub_stage == orig2_sub, "advance_sub_stage mutated input"
        assert new2.sub_stage == "test_generation"


# ======================================================= #
# Unit 10 tests (dispatch)                                #
# ======================================================= #


class TestUnit10Dispatch:
    """Verify dispatch_agent_status transitions."""

    def _make_state(self, **kwargs: Any) -> PipelineState:
        defaults = {
            "stage": "3",
            "sub_stage": None,
            "current_unit": 1,
            "total_units": 3,
        }
        defaults.update(kwargs)
        return PipelineState(**defaults)

    def test_dispatch_test_agent_returns_state(self) -> None:
        """test_agent TEST_GENERATION_COMPLETE returns state (two-branch in route)."""
        state = self._make_state(
            sub_stage="test_generation",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new = dispatch_agent_status(
                state, "test_agent", "TEST_GENERATION_COMPLETE", root,
            )
            # In SVP 2.2, dispatch returns copy of state; route handles advancement
            assert new is not state

    def test_dispatch_impl_agent_returns_state(self) -> None:
        """implementation_agent IMPLEMENTATION_COMPLETE returns state."""
        state = self._make_state(
            sub_stage="implementation",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new = dispatch_agent_status(
                state, "implementation_agent", "IMPLEMENTATION_COMPLETE", root,
            )
            assert new is not state

    def test_dispatch_coverage_returns_state(self) -> None:
        """coverage_review_agent returns state (two-branch in route)."""
        state = self._make_state(
            sub_stage="coverage_review",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new = dispatch_agent_status(
                state, "coverage_review_agent", "COVERAGE_COMPLETE: no gaps", root,
            )
            # dispatch returns state unchanged; route() uses two-branch
            assert new.sub_stage == "coverage_review"

    def test_dispatch_reference_indexing_returns_state(self) -> None:
        """reference_indexing INDEXING_COMPLETE returns state."""
        state = self._make_state(
            stage="pre_stage_3",
            sub_stage=None,
            current_unit=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "svp_config.json").write_text(
                json.dumps({"iteration_limit": 3}), encoding="utf-8"
            )
            new = dispatch_agent_status(
                state, "reference_indexing", "INDEXING_COMPLETE", root,
            )
            # In SVP 2.2, dispatch returns copy; route handles stage advancement
            assert new is not state


