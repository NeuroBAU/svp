"""Regression tests for Bug S3-95: Oracle agent must be read-only during green_run.

Three-layer defense-in-depth:
1. PreToolUse hook blocks writes during oracle green_run (except oracle artifacts)
2. Oracle agent definition includes Read-Only Constraint section
3. prepare_task.py green_run includes constraint reminder

Hook behavioral tests use content-based assertions on the generated script
(matching the existing test pattern in TestWriteAuthorizationPathRules).
The hook runs in the Claude Code harness which handles stdin/quoting differently
than pytest subprocess invocation.
"""

import json
from pathlib import Path

import pytest

from hooks import generate_write_authorization_sh


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestWriteAuthorizationOracleGreenRunBlock:
    """Hook must contain oracle green_run read-only enforcement logic."""

    def test_extracts_oracle_phase(self):
        """Script must extract ORACLE_PHASE from pipeline_state.json."""
        script = generate_write_authorization_sh()
        assert "ORACLE_PHASE" in script
        assert "oracle_phase" in script

    def test_green_run_block_present(self):
        """Script must contain green_run read-only block with exit 2."""
        script = generate_write_authorization_sh()
        assert "green_run" in script
        # Must reference the block condition
        assert 'ORACLE_PHASE' in script
        assert 'ORACLE_SESSION_ACTIVE' in script

    def test_green_run_block_checks_debug_session(self):
        """Oracle green_run block must check DEBUG_AUTHORIZED to allow /svp:bug writes."""
        script = generate_write_authorization_sh()
        # Find the green_run block — it must check DEBUG_AUTHORIZED
        lines = script.split("\n")
        green_run_lines = [
            l for l in lines
            if "green_run" in l and "ORACLE" in l
        ]
        assert len(green_run_lines) > 0, "No oracle green_run condition found"
        # The condition must include DEBUG_AUTHORIZED check
        condition_line = green_run_lines[0]
        assert "DEBUG_AUTHORIZED" in condition_line, (
            f"Oracle green_run block must check DEBUG_AUTHORIZED for false-positive "
            f"prevention. Line: {condition_line}"
        )

    def test_green_run_block_exit_2(self):
        """Oracle green_run block must use exit 2 to hard-block writes."""
        script = generate_write_authorization_sh()
        # Find the BLOCKED message for oracle green_run
        assert "Oracle is read-only during green_run" in script
        # Verify exit 2 follows the block message
        lines = script.split("\n")
        for i, line in enumerate(lines):
            if "Oracle is read-only during green_run" in line:
                # The exit 2 should be nearby (within 2 lines)
                nearby = "\n".join(lines[max(0, i - 1):i + 3])
                assert "exit 2" in nearby, (
                    f"exit 2 must follow the oracle green_run block message. "
                    f"Nearby lines: {nearby}"
                )
                break

    def test_oracle_artifacts_allowed_before_block(self):
        """Oracle artifacts must be allowed BEFORE the green_run block fires."""
        script = generate_write_authorization_sh()
        # oracle_run_ledger, diagnostic_map, trajectory must appear in allowlist
        assert "oracle_run_ledger.json" in script
        assert "oracle_diagnostic_map.json" in script
        assert "oracle_trajectory.json" in script
        # The allowlist must appear BEFORE the green_run block
        ledger_pos = script.index("oracle_run_ledger.json")
        block_pos = script.index("Oracle is read-only during green_run")
        assert ledger_pos < block_pos, (
            "Oracle artifact allowlist must appear before the green_run block"
        )

    def test_debug_session_rules_after_oracle_block(self):
        """Debug session handling must appear AFTER oracle green_run block."""
        script = generate_write_authorization_sh()
        block_pos = script.index("Oracle is read-only during green_run")
        debug_pos = script.index("Debug session handling")
        assert debug_pos > block_pos, (
            "Debug session handling must be after oracle green_run block "
            "(the block has a DEBUG_AUTHORIZED bypass that skips to debug rules)"
        )


class TestOracleAgentDefinitionHasReadOnlySection:
    """Oracle agent definition must include Read-Only Constraint section."""

    def test_definition_contains_readonly_section(self):
        from hooks import generate_write_authorization_sh  # ensure module loads
        # Import the definition from unit_23
        import importlib
        import sys
        stub_path = PROJECT_ROOT / "src" / "unit_23"
        if str(stub_path) not in sys.path:
            sys.path.insert(0, str(stub_path))
        # Reload to get fresh version
        if "stub" in sys.modules:
            del sys.modules["stub"]
        import stub as unit_23_stub
        definition = unit_23_stub.ORACLE_AGENT_DEFINITION
        assert "Read-Only Constraint" in definition, (
            "Oracle agent definition must contain '## Read-Only Constraint' section"
        )
        assert "MUST NOT use Edit" in definition or "MUST NOT" in definition
        assert "ORACLE_FIX_APPLIED" in definition


class TestPrepareTaskGreenRunHasConstraints:
    """prepare_task.py oracle green_run must include read-only constraints."""

    def test_green_run_prompt_contains_constraints(self, tmp_path):
        from routing import save_state
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="5",
            sub_stage="pass_transition",
            current_unit=None,
            total_units=10,
            verified_units=[],
            alignment_iterations=0,
            fix_ladder_position=None,
            red_run_retries=0,
            pass_history=[],
            debug_session=None,
            debug_history=[],
            redo_triggered_from=None,
            delivered_repo_path=None,
            primary_language="python",
            component_languages=[],
            secondary_language=None,
            oracle_session_active=True,
            oracle_test_project="examples/game-of-life/",
            oracle_phase="green_run",
            oracle_run_count=1,
            oracle_nested_session_path=None,
            oracle_modification_count=0,
            state_hash=None,
            spec_revision_count=0,
            pass_=None,
            pass2_nested_session_path=None,
            deferred_broken_units=[],
        )
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        # Create minimal blueprint dir
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir(exist_ok=True)

        from prepare_task import _prepare_oracle_agent
        result = _prepare_oracle_agent(
            tmp_path, state, mode=None, context=None, blueprint_dir=bp_dir,
        )
        assert "READ-ONLY" in result, (
            "Oracle green_run task prompt must contain 'READ-ONLY' constraint"
        )
        assert "ORACLE_FIX_APPLIED" in result
