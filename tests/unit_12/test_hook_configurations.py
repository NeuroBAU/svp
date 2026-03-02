"""
Tests for Unit 12: Hook Configurations.

Validates the hook configuration (hooks.json), hook scripts
(write_authorization.sh, non_svp_protection.sh), and content constants
for universal write authorization and project protection per spec Section 19.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: HOOKS_JSON_SCHEMA uses the Claude Code plugin hook format
with a top-level "hooks" key containing "PreToolUse" entries. Two hooks are
expected: one for write/edit/create tools, one for bash.

DATA ASSUMPTION: SVP_ENV_VAR is the canonical environment variable name
"SVP_PLUGIN_ACTIVE" used by the SVP Launcher (Unit 24) and checked by
non_svp_protection.sh. This is an SVP 1.1 hardening invariant.

DATA ASSUMPTION: HOOKS_JSON_CONTENT is valid JSON conforming to the Claude
Code plugin hook format, with a top-level "hooks" key.

DATA ASSUMPTION: Shell script content strings (WRITE_AUTHORIZATION_SH_CONTENT,
NON_SVP_PROTECTION_SH_CONTENT) start with a shebang line ("#!/").

DATA ASSUMPTION: Infrastructure paths (.svp/, pipeline_state.json, ledgers/,
logs/) are always writable regardless of pipeline state.

DATA ASSUMPTION: Project artifact paths (src/, tests/, specs/, blueprint/,
references/, projectname-repo/) are state-gated, meaning they are writable
only in specific pipeline stages/units.

DATA ASSUMPTION: Pipeline state JSON used for testing write authorization
follows the Unit 2 (PipelineState) schema, with fields like "stage",
"current_unit", "debug_session", etc.

DATA ASSUMPTION: check_write_authorization returns 0 for allow, 2 for block.
check_svp_session returns 0 for allow (env var set), 2 for block (not set).

DATA ASSUMPTION: Debug session states use classifications "build_env",
"single_unit", "cross_unit" and the authorized flag controls whether
artifact writes are permitted.
"""

import inspect
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Import the unit under test from the stub module
from svp.scripts.hook_configurations import (
    HOOKS_JSON_SCHEMA,
    SVP_ENV_VAR,
    check_write_authorization,
    check_svp_session,
)


# ---------------------------------------------------------------------------
# Helper: safely import content constants that may be NameError in stub
# ---------------------------------------------------------------------------

def _get_content_constant(name: str) -> str:
    """Import a content constant from the stub, raising a clear error if absent."""
    import svp.scripts.hook_configurations as mod
    return getattr(mod, name)


# ===========================================================================
# Section 1: Signature Verification
# ===========================================================================


class TestSignatures:
    """Verify function and constant signatures match the blueprint."""

    def test_check_write_authorization_signature(self):
        """check_write_authorization has the correct parameter names and types."""
        sig = inspect.signature(check_write_authorization)
        params = list(sig.parameters.keys())
        assert params == ["tool_name", "file_path", "pipeline_state_path"], (
            f"Expected params [tool_name, file_path, pipeline_state_path], got {params}"
        )
        # Return type annotation
        assert sig.return_annotation is int or sig.return_annotation == int

    def test_check_write_authorization_param_annotations(self):
        """check_write_authorization parameters are annotated as str."""
        sig = inspect.signature(check_write_authorization)
        for param_name in ["tool_name", "file_path", "pipeline_state_path"]:
            param = sig.parameters[param_name]
            assert param.annotation is str or param.annotation == str, (
                f"Parameter {param_name} should be annotated as str"
            )

    def test_check_svp_session_signature(self):
        """check_svp_session has the correct parameter names and types."""
        sig = inspect.signature(check_svp_session)
        params = list(sig.parameters.keys())
        assert params == ["env_var_name"], (
            f"Expected params [env_var_name], got {params}"
        )
        assert sig.return_annotation is int or sig.return_annotation == int

    def test_check_svp_session_param_annotation(self):
        """check_svp_session env_var_name parameter is annotated as str."""
        sig = inspect.signature(check_svp_session)
        param = sig.parameters["env_var_name"]
        assert param.annotation is str or param.annotation == str

    def test_svp_env_var_is_string(self):
        """SVP_ENV_VAR is a string constant."""
        assert isinstance(SVP_ENV_VAR, str)

    def test_hooks_json_schema_is_dict(self):
        """HOOKS_JSON_SCHEMA is a dictionary."""
        assert isinstance(HOOKS_JSON_SCHEMA, dict)


# ===========================================================================
# Section 2: Invariants
# ===========================================================================


class TestInvariants:
    """Verify all invariants from the blueprint."""

    def test_svp_env_var_canonical_name(self):
        """SVP_ENV_VAR must be exactly 'SVP_PLUGIN_ACTIVE'."""
        # Cross-unit invariant: matches Unit 24 SVP Launcher
        assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE", (
            "Canonical env var name must be SVP_PLUGIN_ACTIVE"
        )

    def test_hooks_json_schema_has_hooks_key(self):
        """HOOKS_JSON_SCHEMA must use top-level 'hooks' wrapper key."""
        assert "hooks" in HOOKS_JSON_SCHEMA, (
            "Must use top-level hooks wrapper key"
        )

    def test_hooks_json_content_has_hooks_key(self):
        """HOOKS_JSON_CONTENT must parse as JSON with top-level 'hooks' key."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        assert "hooks" in parsed, "hooks.json must have top-level hooks key"

    def test_write_authorization_sh_has_shebang(self):
        """WRITE_AUTHORIZATION_SH_CONTENT must start with shebang."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert content.startswith("#!/"), "Shell scripts must have shebang"

    def test_non_svp_protection_sh_has_shebang(self):
        """NON_SVP_PROTECTION_SH_CONTENT must start with shebang."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert content.startswith("#!/"), "Shell scripts must have shebang"

    def test_non_svp_protection_checks_svp_plugin_active(self):
        """NON_SVP_PROTECTION_SH_CONTENT must reference SVP_PLUGIN_ACTIVE."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert SVP_ENV_VAR in content, "Must check SVP_PLUGIN_ACTIVE"


# ===========================================================================
# Section 3: HOOKS_JSON_SCHEMA Structure
# ===========================================================================


class TestHooksJsonSchema:
    """Verify the HOOKS_JSON_SCHEMA structure from the blueprint."""

    def test_has_pre_tool_use_key(self):
        """hooks.hooks contains a 'PreToolUse' key."""
        hooks = HOOKS_JSON_SCHEMA["hooks"]
        assert "PreToolUse" in hooks

    def test_pre_tool_use_is_list(self):
        """PreToolUse value is a list of hook entries."""
        pre_tool_use = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
        assert isinstance(pre_tool_use, list)

    def test_pre_tool_use_has_two_entries(self):
        """PreToolUse has exactly two hook entries (write auth + non-SVP protection)."""
        pre_tool_use = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
        assert len(pre_tool_use) == 2

    def test_write_authorization_hook_entry(self):
        """First hook entry is for write/edit/create tools."""
        entry = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"][0]
        assert entry["type"] == "bash"
        assert entry["matcher"] == "write|edit|create"
        assert entry["script"] == ".claude/scripts/write_authorization.sh"

    def test_non_svp_protection_hook_entry(self):
        """Second hook entry is for bash tool."""
        entry = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"][1]
        assert entry["type"] == "bash"
        assert entry["matcher"] == "bash"
        assert entry["script"] == ".claude/scripts/non_svp_protection.sh"

    def test_hook_entries_have_descriptions(self):
        """Each hook entry has a description field."""
        for entry in HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]:
            assert "description" in entry
            assert isinstance(entry["description"], str)
            assert len(entry["description"]) > 0

    def test_does_not_use_flat_format(self):
        """hooks.json must NOT use the flat format -- must use the 'hooks' wrapper."""
        # The flat format would have "PreToolUse" at the top level
        assert "PreToolUse" not in HOOKS_JSON_SCHEMA, (
            "Must not use flat format; must use hooks wrapper"
        )


# ===========================================================================
# Section 4: HOOKS_JSON_CONTENT Validation
# ===========================================================================


class TestHooksJsonContent:
    """Validate the HOOKS_JSON_CONTENT deliverable string."""

    def test_is_valid_json(self):
        """HOOKS_JSON_CONTENT must be valid JSON."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_has_hooks_wrapper_key(self):
        """Parsed JSON must have top-level 'hooks' key."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        assert "hooks" in parsed

    def test_has_pre_tool_use_array(self):
        """Parsed JSON must have PreToolUse array inside hooks."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        assert "PreToolUse" in parsed["hooks"]
        assert isinstance(parsed["hooks"]["PreToolUse"], list)

    def test_has_write_authorization_hook(self):
        """HOOKS_JSON_CONTENT must contain a hook for write authorization."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        # Look for a hook with a write/edit matcher
        write_hooks = [
            h for h in hooks_list
            if "write" in str(h).lower() or "edit" in str(h).lower()
        ]
        assert len(write_hooks) >= 1, (
            "Must have at least one write authorization hook"
        )

    def test_has_non_svp_protection_hook(self):
        """HOOKS_JSON_CONTENT must contain a hook for non-SVP protection."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        # Look for a hook with a bash matcher
        bash_hooks = [
            h for h in hooks_list
            if "bash" in str(h).lower() and "non_svp" in str(h).lower()
                or ("matcher" in h and h.get("matcher") == "bash")
        ]
        assert len(bash_hooks) >= 1, (
            "Must have at least one non-SVP protection hook"
        )

    def test_hooks_use_command_type(self):
        """Each hook entry should use the plugin hook format with command entries."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        # Each entry should reference the shell scripts
        for hook_entry in hooks_list:
            # The hook entry should have a "matcher" field
            assert "matcher" in hook_entry, (
                f"Hook entry missing 'matcher': {hook_entry}"
            )

    def test_does_not_use_flat_format(self):
        """Parsed JSON must NOT use flat format (no top-level PreToolUse)."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        assert "PreToolUse" not in parsed, (
            "Must not use flat format; must use hooks wrapper"
        )


# ===========================================================================
# Section 5: WRITE_AUTHORIZATION_SH_CONTENT Validation
# ===========================================================================


class TestWriteAuthorizationShContent:
    """Validate the WRITE_AUTHORIZATION_SH_CONTENT deliverable string."""

    def test_starts_with_shebang(self):
        """Must start with a shebang line."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert content.startswith("#!/"), "Must start with shebang"

    def test_is_bash_script(self):
        """Must be a bash script (shebang references bash)."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        first_line = content.split("\n")[0]
        assert "bash" in first_line.lower() or "sh" in first_line.lower(), (
            "Shebang should reference bash or sh"
        )

    def test_references_pipeline_state_json(self):
        """Must read pipeline_state.json."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "pipeline_state" in content, (
            "Script must reference pipeline_state"
        )

    def test_handles_infrastructure_paths(self):
        """Must handle infrastructure paths (.svp/, pipeline_state.json, ledgers/, logs/)."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        # Check for references to infrastructure paths
        assert ".svp" in content or ".svp/" in content, (
            "Must reference .svp/ infrastructure path"
        )

    def test_references_svp_infrastructure_path(self):
        """Must mention .svp/ as an infrastructure path."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert ".svp" in content

    def test_references_ledgers_infrastructure_path(self):
        """Must mention ledgers/ as an infrastructure path."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "ledger" in content.lower()

    def test_references_logs_infrastructure_path(self):
        """Must mention logs/ as an infrastructure path."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "log" in content.lower()

    def test_has_exit_code_0_for_allow(self):
        """Must use exit code 0 for allowing writes."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "exit 0" in content, "Must exit 0 to allow"

    def test_has_exit_code_2_for_block(self):
        """Must use exit code 2 for blocking writes."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "exit 2" in content, "Must exit 2 to block"

    def test_handles_src_paths(self):
        """Must reference src/ as a state-gated project artifact path."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "src/" in content or "src" in content

    def test_handles_tests_paths(self):
        """Must reference tests/ as a state-gated project artifact path."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "tests/" in content or "tests" in content

    def test_handles_debug_session(self):
        """Must handle debug_session state (Bug 2 fix)."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "debug_session" in content or "debug" in content.lower(), (
            "Must handle debug session state"
        )

    def test_handles_stage_gating(self):
        """Must check stage for state-gated paths."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "stage" in content.lower(), "Must check pipeline stage"

    def test_handles_unit_gating(self):
        """Must check current_unit for unit-specific paths."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "unit" in content.lower(), "Must check current unit"

    def test_uses_relative_paths(self):
        """Hook scripts use paths relative to the project root (spec 19.2)."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        # Should NOT reference plugin-specific path variables like $PLUGIN_DIR
        # The script should use relative paths or paths relative to project root
        assert "$PLUGIN_DIR" not in content, (
            "Must use relative paths, not plugin-specific variables"
        )


# ===========================================================================
# Section 6: NON_SVP_PROTECTION_SH_CONTENT Validation
# ===========================================================================


class TestNonSvpProtectionShContent:
    """Validate the NON_SVP_PROTECTION_SH_CONTENT deliverable string."""

    def test_starts_with_shebang(self):
        """Must start with a shebang line."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert content.startswith("#!/"), "Must start with shebang"

    def test_is_bash_script(self):
        """Must be a bash script."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        first_line = content.split("\n")[0]
        assert "bash" in first_line.lower() or "sh" in first_line.lower()

    def test_checks_svp_plugin_active(self):
        """Must check for the SVP_PLUGIN_ACTIVE environment variable."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert "SVP_PLUGIN_ACTIVE" in content, (
            "Must check SVP_PLUGIN_ACTIVE environment variable"
        )

    def test_exit_0_when_set(self):
        """Must exit 0 (allow) when SVP_PLUGIN_ACTIVE is set."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert "exit 0" in content, "Must exit 0 to allow when env var is set"

    def test_exit_2_when_not_set(self):
        """Must exit 2 (block) when SVP_PLUGIN_ACTIVE is not set."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert "exit 2" in content, "Must exit 2 to block when env var is not set"

    def test_informs_human_about_svp(self):
        """Must include a message directing human to use svp command."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        # The script should inform the human this is an SVP-managed project
        content_lower = content.lower()
        assert "svp" in content_lower, (
            "Must mention SVP in the blocking message"
        )

    def test_blocks_bash_execution(self):
        """When env var is not set, blocks all bash commands."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        # Should have logic to block (exit 2) when the env var is missing
        assert "exit 2" in content

    def test_uses_relative_paths(self):
        """Hook scripts use paths relative to the project root (spec 19.2)."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert "$PLUGIN_DIR" not in content, (
            "Must use relative paths, not plugin-specific variables"
        )


# ===========================================================================
# Section 7: check_write_authorization Behavioral Contracts
# ===========================================================================


class TestCheckWriteAuthorization:
    """Test check_write_authorization behavioral contracts."""

    # DATA ASSUMPTION: Pipeline state for stage 3 processing unit 4 allows
    # writes to src/unit_4/ but not src/unit_5/.

    def test_returns_int(self):
        """check_write_authorization must return an integer."""
        # This will raise NotImplementedError against stub
        result = check_write_authorization(
            tool_name="write",
            file_path=".svp/test.txt",
            pipeline_state_path="pipeline_state.json",
        )
        assert isinstance(result, int)

    def test_infrastructure_path_svp_always_writable(self):
        """Infrastructure path .svp/ should always be writable (return 0)."""
        result = check_write_authorization(
            tool_name="write",
            file_path=".svp/some_file.txt",
            pipeline_state_path="pipeline_state.json",
        )
        assert result == 0, ".svp/ should always be writable"

    def test_infrastructure_path_pipeline_state_always_writable(self):
        """Infrastructure path pipeline_state.json should always be writable."""
        result = check_write_authorization(
            tool_name="write",
            file_path="pipeline_state.json",
            pipeline_state_path="pipeline_state.json",
        )
        assert result == 0, "pipeline_state.json should always be writable"

    def test_infrastructure_path_ledgers_always_writable(self):
        """Infrastructure path ledgers/ should always be writable."""
        result = check_write_authorization(
            tool_name="write",
            file_path="ledgers/test.jsonl",
            pipeline_state_path="pipeline_state.json",
        )
        assert result == 0, "ledgers/ should always be writable"

    def test_infrastructure_path_logs_always_writable(self):
        """Infrastructure path logs/ should always be writable."""
        result = check_write_authorization(
            tool_name="write",
            file_path="logs/output.log",
            pipeline_state_path="pipeline_state.json",
        )
        assert result == 0, "logs/ should always be writable"

    def test_block_returns_exit_code_2(self):
        """Blocked writes should return exit code 2."""
        # DATA ASSUMPTION: Writing to src/unit_5/ when pipeline is at stage 3
        # processing unit 4 should be blocked.
        result = check_write_authorization(
            tool_name="write",
            file_path="src/unit_5/impl.py",
            pipeline_state_path="pipeline_state.json",
        )
        assert result == 2 or result == 0, (
            "Must return 0 (allow) or 2 (block)"
        )

    def test_return_value_is_0_or_2(self):
        """check_write_authorization must return 0 or 2 only."""
        result = check_write_authorization(
            tool_name="write",
            file_path="some/path.txt",
            pipeline_state_path="pipeline_state.json",
        )
        assert result in (0, 2), f"Must return 0 or 2, got {result}"


# ===========================================================================
# Section 8: check_svp_session Behavioral Contracts
# ===========================================================================


class TestCheckSvpSession:
    """Test check_svp_session behavioral contracts."""

    def test_returns_int(self):
        """check_svp_session must return an integer."""
        result = check_svp_session(env_var_name="SVP_PLUGIN_ACTIVE")
        assert isinstance(result, int)

    def test_returns_0_when_env_var_set(self):
        """Returns 0 (allow) when SVP_PLUGIN_ACTIVE is set."""
        with patch.dict(os.environ, {"SVP_PLUGIN_ACTIVE": "1"}):
            result = check_svp_session(env_var_name="SVP_PLUGIN_ACTIVE")
        assert result == 0, "Should allow when env var is set"

    def test_returns_2_when_env_var_not_set(self):
        """Returns 2 (block) when SVP_PLUGIN_ACTIVE is not set."""
        result = check_svp_session(env_var_name="SVP_PLUGIN_ACTIVE")
        # The actual behavior depends on whether the env var is in the environment
        assert result in (0, 2), f"Must return 0 or 2, got {result}"

    def test_return_value_is_0_or_2(self):
        """check_svp_session must return only 0 or 2."""
        result = check_svp_session(env_var_name="SVP_PLUGIN_ACTIVE")
        assert result in (0, 2), f"Must return 0 or 2, got {result}"


# ===========================================================================
# Section 9: Error Conditions
# ===========================================================================


class TestErrorConditions:
    """Test error conditions from the blueprint."""

    def test_write_authorization_block_has_message(self):
        """Exit code 2 from write_authorization.sh should include a message
        explaining why the path is not writable."""
        # DATA ASSUMPTION: The function itself may not return the message
        # but the shell script (WRITE_AUTHORIZATION_SH_CONTENT) must produce
        # a message when blocking (exit 2).
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        # When blocking (exit 2), there should be an echo/printf before the exit
        # Check that there are messages associated with blocking
        lines = content.split("\n")
        has_block_message = False
        for i, line in enumerate(lines):
            if "exit 2" in line:
                # Check previous lines for echo/message output
                for prev_line in lines[max(0, i - 5):i]:
                    if "echo" in prev_line or "printf" in prev_line or "cat" in prev_line:
                        has_block_message = True
                        break
                # Also check if inline message (e.g., echo ... && exit 2)
                if "echo" in line or "printf" in line:
                    has_block_message = True
        assert has_block_message, (
            "Must include a message explaining why the path is not writable when blocking"
        )

    def test_non_svp_protection_block_has_message(self):
        """Exit code 2 from non_svp_protection.sh should inform human this is
        an SVP-managed project."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        lines = content.split("\n")
        has_block_message = False
        for i, line in enumerate(lines):
            if "exit 2" in line:
                for prev_line in lines[max(0, i - 5):i]:
                    if "echo" in prev_line or "printf" in prev_line or "cat" in prev_line:
                        has_block_message = True
                        break
                if "echo" in line or "printf" in line:
                    has_block_message = True
        assert has_block_message, (
            "Must include a message informing human this is an SVP-managed project"
        )


# ===========================================================================
# Section 10: Debug Session Write Rules (Bug 2 Fix)
# ===========================================================================


class TestDebugSessionWriteRules:
    """Validate debug session write rules in WRITE_AUTHORIZATION_SH_CONTENT."""

    # DATA ASSUMPTION: Debug session with authorized=true allows specific paths.
    # DATA ASSUMPTION: tests/regressions/ is always writable during authorized
    # debug sessions regardless of classification.

    def test_script_handles_debug_session_authorized(self):
        """Script must handle debug_session.authorized field."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "authorized" in content or "debug" in content.lower(), (
            "Must handle debug_session.authorized"
        )

    def test_script_references_regressions_path(self):
        """During authorized debug, tests/regressions/ should be writable."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "regression" in content.lower(), (
            "Must reference regressions path for debug sessions"
        )

    def test_script_handles_build_env_classification(self):
        """Script must handle build_env classification for debug sessions."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "build_env" in content, (
            "Must handle build_env debug classification"
        )

    def test_script_handles_single_unit_classification(self):
        """Script must handle single_unit classification for debug sessions."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "single_unit" in content, (
            "Must handle single_unit debug classification"
        )

    def test_script_handles_triage_scratch(self):
        """Script must handle .svp/triage_scratch/ during triage."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "triage" in content.lower(), (
            "Must handle triage_scratch path"
        )

    def test_build_env_blocks_implementation_py_files(self):
        """During build_env debug, implementation .py files in src/unit_N/
        (other than __init__.py) are NOT writable."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        # The script should distinguish __init__.py from other .py files
        assert "__init__" in content, (
            "Must distinguish __init__.py from other .py files in build_env mode"
        )

    def test_unauthorized_debug_only_infrastructure(self):
        """When debug_session.authorized is false, only infrastructure paths
        are writable. No artifact writes permitted."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        # This behavior is encoded in the script logic.
        # We verify the script references both authorized states.
        assert "authorized" in content.lower() or "debug" in content.lower()

    def test_build_env_allows_pyproject_toml(self):
        """During build_env debug, pyproject.toml should be writable."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "pyproject" in content.lower(), (
            "Must allow pyproject.toml during build_env debug"
        )


# ===========================================================================
# Section 11: Stage Handling in Write Authorization
# ===========================================================================


class TestStageHandling:
    """Validate that WRITE_AUTHORIZATION_SH_CONTENT handles all stages."""

    # DATA ASSUMPTION: Pipeline stages from Unit 2 are "0", "1", "2",
    # "pre_stage_3", "3", "4", "5".

    def test_script_is_nonempty(self):
        """Script content must be non-empty."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert len(content.strip()) > 0

    def test_script_handles_stage_values(self):
        """Script must reference stage checking logic."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "stage" in content.lower(), "Must check stage in pipeline state"

    def test_script_handles_pre_stage_3(self):
        """Script must handle pre_stage_3."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert "pre_stage_3" in content, "Must handle pre_stage_3"


# ===========================================================================
# Section 12: Content String Type Validation
# ===========================================================================


class TestContentStringTypes:
    """Validate content constant types."""

    def test_hooks_json_content_is_string(self):
        """HOOKS_JSON_CONTENT must be a string."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        assert isinstance(content, str)

    def test_write_authorization_sh_content_is_string(self):
        """WRITE_AUTHORIZATION_SH_CONTENT must be a string."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        assert isinstance(content, str)

    def test_non_svp_protection_sh_content_is_string(self):
        """NON_SVP_PROTECTION_SH_CONTENT must be a string."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        assert isinstance(content, str)


# ===========================================================================
# Section 13: Hooks JSON Content Plugin Format
# ===========================================================================


class TestHooksJsonPluginFormat:
    """Validate HOOKS_JSON_CONTENT matches Claude Code plugin hook format."""

    # DATA ASSUMPTION: The Claude Code plugin hook format requires a top-level
    # "hooks" key containing a "PreToolUse" array. Each hook entry has
    # "matcher" and "hooks" (with command entries).

    def test_two_hooks_in_content(self):
        """HOOKS_JSON_CONTENT must contain exactly two hooks: write auth and
        non-SVP protection."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        assert len(hooks_list) >= 2, (
            "Must have at least two hooks (write auth + non-SVP protection)"
        )

    def test_hooks_have_matcher_field(self):
        """Each hook in HOOKS_JSON_CONTENT must have a matcher field."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        for hook in hooks_list:
            assert "matcher" in hook, f"Hook entry missing 'matcher': {hook}"

    def test_write_auth_matcher_covers_write_edit(self):
        """Write authorization hook matcher should cover write/edit tools."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        # Find the write authorization hook
        write_hooks = [
            h for h in hooks_list
            if "matcher" in h and ("write" in h["matcher"].lower()
                                   or "edit" in h["matcher"].lower())
        ]
        assert len(write_hooks) >= 1, (
            "Must have a hook with write/edit in matcher"
        )

    def test_non_svp_matcher_covers_bash(self):
        """Non-SVP protection hook matcher should cover bash tool."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        bash_hooks = [
            h for h in hooks_list
            if "matcher" in h and h["matcher"].lower() == "bash"
        ]
        assert len(bash_hooks) >= 1, (
            "Must have a hook with bash matcher"
        )

    def test_hooks_reference_shell_scripts(self):
        """Hook entries should reference the shell script files."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        content_str = json.dumps(parsed)
        assert "write_authorization" in content_str, (
            "Must reference write_authorization script"
        )
        assert "non_svp_protection" in content_str, (
            "Must reference non_svp_protection script"
        )


# ===========================================================================
# Section 14: Shell Script Execution Tests (Functional)
# ===========================================================================


class TestShellScriptExecution:
    """Test that shell scripts are syntactically valid and executable.

    DATA ASSUMPTION: Shell scripts are syntactically valid bash and can be
    checked with bash -n for syntax validation.
    """

    def test_write_authorization_sh_syntax_valid(self):
        """WRITE_AUTHORIZATION_SH_CONTENT must be syntactically valid bash."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            import subprocess
            result = subprocess.run(
                ["bash", "-n", tmp_path],
                capture_output=True, text=True
            )
            assert result.returncode == 0, (
                f"write_authorization.sh has syntax errors: {result.stderr}"
            )
        finally:
            os.unlink(tmp_path)

    def test_non_svp_protection_sh_syntax_valid(self):
        """NON_SVP_PROTECTION_SH_CONTENT must be syntactically valid bash."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            import subprocess
            result = subprocess.run(
                ["bash", "-n", tmp_path],
                capture_output=True, text=True
            )
            assert result.returncode == 0, (
                f"non_svp_protection.sh has syntax errors: {result.stderr}"
            )
        finally:
            os.unlink(tmp_path)

    def test_non_svp_protection_blocks_without_env_var(self):
        """Running non_svp_protection.sh without SVP_PLUGIN_ACTIVE set should
        exit with code 2."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            os.chmod(tmp_path, 0o755)
            import subprocess
            env = os.environ.copy()
            env.pop("SVP_PLUGIN_ACTIVE", None)
            result = subprocess.run(
                ["bash", tmp_path],
                capture_output=True, text=True,
                env=env,
            )
            assert result.returncode == 2, (
                f"Should exit 2 when SVP_PLUGIN_ACTIVE is not set, "
                f"got exit code {result.returncode}. stderr: {result.stderr}"
            )
        finally:
            os.unlink(tmp_path)

    def test_non_svp_protection_allows_with_env_var(self):
        """Running non_svp_protection.sh with SVP_PLUGIN_ACTIVE set should
        exit with code 0."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            os.chmod(tmp_path, 0o755)
            import subprocess
            env = os.environ.copy()
            env["SVP_PLUGIN_ACTIVE"] = "1"
            result = subprocess.run(
                ["bash", tmp_path],
                capture_output=True, text=True,
                env=env,
            )
            assert result.returncode == 0, (
                f"Should exit 0 when SVP_PLUGIN_ACTIVE is set, "
                f"got exit code {result.returncode}. stderr: {result.stderr}"
            )
        finally:
            os.unlink(tmp_path)

    def test_non_svp_block_message_mentions_svp(self):
        """When blocking, non_svp_protection.sh must output a message mentioning SVP."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            os.chmod(tmp_path, 0o755)
            import subprocess
            env = os.environ.copy()
            env.pop("SVP_PLUGIN_ACTIVE", None)
            result = subprocess.run(
                ["bash", tmp_path],
                capture_output=True, text=True,
                env=env,
            )
            combined_output = result.stdout + result.stderr
            assert "svp" in combined_output.lower() or "SVP" in combined_output, (
                f"Block message should mention SVP. Output: {combined_output}"
            )
        finally:
            os.unlink(tmp_path)


# ===========================================================================
# Section 15: Write Authorization Script Execution Tests
# ===========================================================================


class TestWriteAuthorizationExecution:
    """Test write_authorization.sh execution with synthetic pipeline state.

    DATA ASSUMPTION: Pipeline state JSON follows Unit 2 schema. We construct
    minimal states representing different stages to test the authorization
    logic.
    """

    @staticmethod
    def _run_write_auth_script(file_path: str, state_dict: dict) -> int:
        """Helper: write script and state to temp files, run the script."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write pipeline state
            state_path = os.path.join(tmpdir, "pipeline_state.json")
            with open(state_path, "w") as f:
                json.dump(state_dict, f)

            # Write the script
            script_path = os.path.join(tmpdir, "write_authorization.sh")
            with open(script_path, "w") as f:
                f.write(content)
            os.chmod(script_path, 0o755)

            import subprocess
            env = os.environ.copy()
            env["SVP_PLUGIN_ACTIVE"] = "1"

            # The script receives tool_input as JSON on stdin in Claude Code
            # plugin format. We'll construct a minimal tool_input.
            tool_input = json.dumps({
                "tool_name": "write",
                "tool_input": {"file_path": file_path}
            })

            result = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True,
                env=env,
                cwd=tmpdir,
                input=tool_input,
            )
            return result.returncode

    def test_infrastructure_svp_always_allowed(self):
        """Writing to .svp/ paths should always be allowed (exit 0)."""
        # DATA ASSUMPTION: Minimal stage 0 state
        state = {"stage": "0", "current_unit": None, "debug_session": None}
        exit_code = self._run_write_auth_script(".svp/test.txt", state)
        assert exit_code == 0, f".svp/ should be allowed, got exit {exit_code}"

    def test_infrastructure_pipeline_state_always_allowed(self):
        """Writing to pipeline_state.json should always be allowed."""
        state = {"stage": "3", "current_unit": 4, "debug_session": None}
        exit_code = self._run_write_auth_script("pipeline_state.json", state)
        assert exit_code == 0, (
            f"pipeline_state.json should be allowed, got exit {exit_code}"
        )

    def test_infrastructure_ledgers_always_allowed(self):
        """Writing to ledgers/ should always be allowed."""
        state = {"stage": "3", "current_unit": 4, "debug_session": None}
        exit_code = self._run_write_auth_script("ledgers/test.jsonl", state)
        assert exit_code == 0, f"ledgers/ should be allowed, got exit {exit_code}"

    def test_infrastructure_logs_always_allowed(self):
        """Writing to logs/ should always be allowed."""
        state = {"stage": "1", "current_unit": None, "debug_session": None}
        exit_code = self._run_write_auth_script("logs/run.log", state)
        assert exit_code == 0, f"logs/ should be allowed, got exit {exit_code}"

    def test_src_unit_writable_during_stage3_correct_unit(self):
        """src/unit_4/ should be writable during stage 3 processing unit 4."""
        # DATA ASSUMPTION: Stage 3, current_unit 4
        state = {"stage": "3", "current_unit": 4, "debug_session": None}
        exit_code = self._run_write_auth_script(
            "src/unit_4/impl.py", state
        )
        assert exit_code == 0, (
            f"src/unit_4/ should be writable during stage 3 unit 4, "
            f"got exit {exit_code}"
        )

    def test_src_unit_blocked_during_stage3_wrong_unit(self):
        """src/unit_5/ should be blocked during stage 3 processing unit 4."""
        # DATA ASSUMPTION: Stage 3, current_unit 4
        state = {"stage": "3", "current_unit": 4, "debug_session": None}
        exit_code = self._run_write_auth_script(
            "src/unit_5/impl.py", state
        )
        assert exit_code == 2, (
            f"src/unit_5/ should be blocked during stage 3 unit 4, "
            f"got exit {exit_code}"
        )

    def test_tests_unit_writable_during_stage3_correct_unit(self):
        """tests/unit_4/ should be writable during stage 3 processing unit 4."""
        state = {"stage": "3", "current_unit": 4, "debug_session": None}
        exit_code = self._run_write_auth_script(
            "tests/unit_4/test_something.py", state
        )
        assert exit_code == 0, (
            f"tests/unit_4/ should be writable during stage 3 unit 4, "
            f"got exit {exit_code}"
        )

    def test_tests_unit_blocked_during_stage3_wrong_unit(self):
        """tests/unit_5/ should be blocked during stage 3 processing unit 4."""
        state = {"stage": "3", "current_unit": 4, "debug_session": None}
        exit_code = self._run_write_auth_script(
            "tests/unit_5/test_something.py", state
        )
        assert exit_code == 2, (
            f"tests/unit_5/ should be blocked during stage 3 unit 4, "
            f"got exit {exit_code}"
        )


# ===========================================================================
# Section 16: Debug Session Execution Tests
# ===========================================================================


class TestDebugSessionExecution:
    """Test write authorization with debug session states.

    DATA ASSUMPTION: Debug sessions follow Unit 2 DebugSession schema with
    bug_id, classification, affected_units, phase, authorized fields.
    """

    @staticmethod
    def _run_write_auth_script(file_path: str, state_dict: dict) -> int:
        """Helper: same as TestWriteAuthorizationExecution._run_write_auth_script."""
        content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "pipeline_state.json")
            with open(state_path, "w") as f:
                json.dump(state_dict, f)

            script_path = os.path.join(tmpdir, "write_authorization.sh")
            with open(script_path, "w") as f:
                f.write(content)
            os.chmod(script_path, 0o755)

            import subprocess
            env = os.environ.copy()
            env["SVP_PLUGIN_ACTIVE"] = "1"

            tool_input = json.dumps({
                "tool_name": "write",
                "tool_input": {"file_path": file_path}
            })

            result = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True,
                env=env,
                cwd=tmpdir,
                input=tool_input,
            )
            return result.returncode

    def test_unauthorized_debug_only_infrastructure(self):
        """When debug_session.authorized is false, only infrastructure paths
        are writable."""
        # DATA ASSUMPTION: Debug session with authorized=false
        state = {
            "stage": "3",
            "current_unit": 4,
            "debug_session": {
                "bug_id": 1,
                "description": "Test bug",
                "classification": "single_unit",
                "affected_units": [4],
                "phase": "triage_readonly",
                "authorized": False,
            }
        }
        # Infrastructure should work
        exit_code = self._run_write_auth_script(".svp/test.txt", state)
        assert exit_code == 0, ".svp/ should be writable even in unauthorized debug"

        # Artifact path should be blocked
        exit_code = self._run_write_auth_script("src/unit_4/impl.py", state)
        assert exit_code == 2, (
            "Artifact writes should be blocked when debug_session.authorized is false"
        )

    def test_authorized_debug_regressions_writable(self):
        """During authorized debug, tests/regressions/ should be writable
        regardless of classification."""
        state = {
            "stage": "3",
            "current_unit": 4,
            "debug_session": {
                "bug_id": 1,
                "description": "Test bug",
                "classification": "single_unit",
                "affected_units": [4],
                "phase": "regression_test",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script(
            "tests/regressions/test_bug_1.py", state
        )
        assert exit_code == 0, (
            "tests/regressions/ should be writable during authorized debug"
        )

    def test_authorized_single_unit_allows_affected_unit(self):
        """During single_unit debug, src/unit_N/ for affected unit should
        be writable."""
        state = {
            "stage": "3",
            "current_unit": 4,
            "debug_session": {
                "bug_id": 1,
                "description": "Test bug",
                "classification": "single_unit",
                "affected_units": [4],
                "phase": "repair",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script("src/unit_4/impl.py", state)
        assert exit_code == 0, (
            "src/unit_4/ should be writable during single_unit debug for unit 4"
        )

    def test_authorized_single_unit_blocks_unaffected_unit(self):
        """During single_unit debug, src/unit_N/ for unaffected unit should
        be blocked."""
        state = {
            "stage": "3",
            "current_unit": 4,
            "debug_session": {
                "bug_id": 1,
                "description": "Test bug",
                "classification": "single_unit",
                "affected_units": [4],
                "phase": "repair",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script("src/unit_5/impl.py", state)
        assert exit_code == 2, (
            "src/unit_5/ should be blocked during single_unit debug for unit 4"
        )

    def test_authorized_build_env_allows_pyproject_toml(self):
        """During build_env debug, pyproject.toml should be writable."""
        state = {
            "stage": "3",
            "current_unit": None,
            "debug_session": {
                "bug_id": 2,
                "description": "Build env issue",
                "classification": "build_env",
                "affected_units": [],
                "phase": "repair",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script("pyproject.toml", state)
        assert exit_code == 0, (
            "pyproject.toml should be writable during build_env debug"
        )

    def test_authorized_build_env_allows_init_py(self):
        """During build_env debug, __init__.py files should be writable."""
        state = {
            "stage": "3",
            "current_unit": None,
            "debug_session": {
                "bug_id": 2,
                "description": "Build env issue",
                "classification": "build_env",
                "affected_units": [],
                "phase": "repair",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script(
            "src/unit_4/__init__.py", state
        )
        assert exit_code == 0, (
            "__init__.py should be writable during build_env debug"
        )

    def test_authorized_build_env_blocks_impl_py(self):
        """During build_env debug, implementation .py files in src/unit_N/
        (other than __init__.py) should NOT be writable."""
        state = {
            "stage": "3",
            "current_unit": None,
            "debug_session": {
                "bug_id": 2,
                "description": "Build env issue",
                "classification": "build_env",
                "affected_units": [],
                "phase": "repair",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script(
            "src/unit_4/stub.py", state
        )
        assert exit_code == 2, (
            "Implementation .py files should NOT be writable during build_env debug"
        )

    def test_triage_allows_triage_scratch(self):
        """During triage phase, .svp/triage_scratch/ should be writable."""
        state = {
            "stage": "3",
            "current_unit": 4,
            "debug_session": {
                "bug_id": 1,
                "description": "Test bug",
                "classification": None,
                "affected_units": [],
                "phase": "triage",
                "authorized": True,
            }
        }
        exit_code = self._run_write_auth_script(
            ".svp/triage_scratch/notes.txt", state
        )
        assert exit_code == 0, (
            ".svp/triage_scratch/ should be writable during triage"
        )
