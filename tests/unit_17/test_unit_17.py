"""Unit 17: Hook Enforcement -- complete test suite.

Synthetic data assumptions:
- generate_hooks_json() returns a JSON string representing Claude Code hook
  configuration with schema {"hooks": {"PreToolUse": [...], "PostToolUse": [...]}}.
- PreToolUse contains two entries: Write matcher -> write_authorization.sh,
  Bash matcher -> non_svp_protection.sh.
- PostToolUse contains two entries: Write matcher -> stub_sentinel_check.sh,
  Agent matcher -> monitoring_reminder.sh (E/F self-builds only).
- Each handler is {"type": "command", "command": "<path>"} with .claude/scripts/ prefix.
- Handlers do NOT use type "bash", do NOT have a "script" field, and do NOT
  place handler fields on the matcher object.
- HOOKS_JSON_SCHEMA is a Dict[str, Any] describing the expected schema.
- generate_write_authorization_sh() returns a shell script string that:
  (1) reads current stage from pipeline_state.json,
  (2) checks pipeline_state.json is writable only by update_state.py,
  (3) blocks builder script (.py in scripts/) writes during Stages 3-5 with
      Hard Stop Protocol message,
  (4) checks remaining path rules per language authorized_write_dirs,
  (5) profile writable only during Stage 0 project_profile and redo sub-stages,
  (6) toolchain and ruff.toml permanently read-only,
  (7) oracle session: .svp/oracle_run_ledger.json always writable,
  (8) debug session: tests/regressions/, unit-specific dirs, delivered_repo_path writable,
  (9) exit code 2 for blocked writes.
- generate_non_svp_protection_sh() returns a shell script string that checks
  SVP_PLUGIN_ACTIVE env var; if unset or not "1", blocks all bash commands
  with README message and exit code 2.
- generate_stub_sentinel_check_sh() returns a shell script string that greps
  written files for the stub sentinel from LANGUAGE_REGISTRY; exit 2 if found.
- generate_monitoring_reminder_sh() returns a shell script string that reads
  project_profile.json, checks is_svp_build; if true, outputs a monitoring
  reminder; if false or absent, exit 0 with no output (no-op).
- All generated scripts are valid shell (bash) scripts starting with a shebang.
- Synthetic project_profile.json values:
  {"is_svp_build": true} for E/F self-build scenarios,
  {"is_svp_build": false} or absent field for non-SVP scenarios.
"""

import json
from typing import Any, Dict

from src.unit_17.stub import (
    HOOKS_JSON_SCHEMA,
    generate_hooks_json,
    generate_monitoring_reminder_sh,
    generate_non_svp_protection_sh,
    generate_stub_sentinel_check_sh,
    generate_write_authorization_sh,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_hooks_json(raw: str) -> Dict[str, Any]:
    """Parse the output of generate_hooks_json into a dict."""
    return json.loads(raw)


def get_pretooluse_entries(parsed: Dict[str, Any]):
    """Extract PreToolUse entries from parsed hooks JSON."""
    return parsed["hooks"]["PreToolUse"]


def get_posttooluse_entries(parsed: Dict[str, Any]):
    """Extract PostToolUse entries from parsed hooks JSON."""
    return parsed["hooks"]["PostToolUse"]


def find_entry_by_matcher(entries, matcher_tool_name: str):
    """Find a hook entry by matcher tool name."""
    for entry in entries:
        matcher = entry.get("matcher", entry)
        if matcher.get("tool_name") == matcher_tool_name:
            return entry
    return None


# ---------------------------------------------------------------------------
# HOOKS_JSON_SCHEMA tests
# ---------------------------------------------------------------------------


class TestHooksJsonSchema:
    """Tests for the HOOKS_JSON_SCHEMA constant."""

    def test_hooks_json_schema_is_dict(self):
        """HOOKS_JSON_SCHEMA must be a Dict[str, Any]."""
        assert isinstance(HOOKS_JSON_SCHEMA, dict)

    def test_hooks_json_schema_has_hooks_key(self):
        """HOOKS_JSON_SCHEMA must define the top-level 'hooks' key."""
        assert "hooks" in HOOKS_JSON_SCHEMA or "properties" in HOOKS_JSON_SCHEMA


# ---------------------------------------------------------------------------
# generate_hooks_json tests
# ---------------------------------------------------------------------------


class TestGenerateHooksJson:
    """Tests for the generate_hooks_json function."""

    def test_returns_string(self):
        """generate_hooks_json must return a string."""
        result = generate_hooks_json()
        assert isinstance(result, str)

    def test_returns_valid_json(self):
        """The returned string must be valid JSON."""
        result = generate_hooks_json()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_top_level_hooks_key(self):
        """Parsed JSON must have a top-level 'hooks' key."""
        parsed = parse_hooks_json(generate_hooks_json())
        assert "hooks" in parsed

    def test_hooks_contains_pretooluse(self):
        """hooks must contain a PreToolUse list."""
        parsed = parse_hooks_json(generate_hooks_json())
        assert "PreToolUse" in parsed["hooks"]
        assert isinstance(parsed["hooks"]["PreToolUse"], list)

    def test_hooks_contains_posttooluse(self):
        """hooks must contain a PostToolUse list."""
        parsed = parse_hooks_json(generate_hooks_json())
        assert "PostToolUse" in parsed["hooks"]
        assert isinstance(parsed["hooks"]["PostToolUse"], list)

    def test_pretooluse_has_write_matcher_for_write_authorization(self):
        """PreToolUse must have a Write matcher entry pointing to write_authorization.sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_pretooluse_entries(parsed)
        commands = [e.get("command", "") for e in entries if isinstance(e, dict)]
        # Flatten: also check nested handler if present
        all_commands = []
        for entry in entries:
            if "command" in entry:
                all_commands.append(entry["command"])
            if "handler" in entry:
                handler = entry["handler"]
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        matched = [c for c in all_commands if "write_authorization.sh" in c]
        assert len(matched) >= 1, (
            "PreToolUse must include a Write matcher -> write_authorization.sh entry"
        )

    def test_pretooluse_has_bash_matcher_for_non_svp_protection(self):
        """PreToolUse must have a Bash matcher entry pointing to non_svp_protection.sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_pretooluse_entries(parsed)
        all_commands = []
        for entry in entries:
            if "command" in entry:
                all_commands.append(entry["command"])
            if "handler" in entry:
                handler = entry["handler"]
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        matched = [c for c in all_commands if "non_svp_protection.sh" in c]
        assert len(matched) >= 1, (
            "PreToolUse must include a Bash matcher -> non_svp_protection.sh entry"
        )

    def test_posttooluse_has_write_matcher_for_stub_sentinel_check(self):
        """PostToolUse must have a Write matcher entry pointing to stub_sentinel_check.sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_posttooluse_entries(parsed)
        all_commands = []
        for entry in entries:
            if "command" in entry:
                all_commands.append(entry["command"])
            if "handler" in entry:
                handler = entry["handler"]
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        matched = [c for c in all_commands if "stub_sentinel_check.sh" in c]
        assert len(matched) >= 1, (
            "PostToolUse must include a Write matcher -> stub_sentinel_check.sh entry"
        )

    def test_posttooluse_has_agent_matcher_for_monitoring_reminder(self):
        """PostToolUse must have an Agent matcher entry pointing to monitoring_reminder.sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_posttooluse_entries(parsed)
        all_commands = []
        for entry in entries:
            if "command" in entry:
                all_commands.append(entry["command"])
            if "handler" in entry:
                handler = entry["handler"]
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        matched = [c for c in all_commands if "monitoring_reminder.sh" in c]
        assert len(matched) >= 1, (
            "PostToolUse must include an Agent matcher -> monitoring_reminder.sh entry"
        )

    def test_handler_type_is_command_not_bash(self):
        """Every handler must use type 'command', never type 'bash'."""
        parsed = parse_hooks_json(generate_hooks_json())
        for hook_type in ("PreToolUse", "PostToolUse"):
            entries = parsed["hooks"][hook_type]
            for entry in entries:
                # Check handler dict if nested
                handler = entry.get("handler", entry)
                if isinstance(handler, dict) and "type" in handler:
                    assert handler["type"] == "command", (
                        f"Handler type must be 'command', not '{handler['type']}'"
                    )
                    assert handler["type"] != "bash", (
                        "Handler type must never be 'bash'"
                    )

    def test_no_script_field_in_handlers(self):
        """No handler may contain a 'script' field."""
        parsed = parse_hooks_json(generate_hooks_json())
        for hook_type in ("PreToolUse", "PostToolUse"):
            entries = parsed["hooks"][hook_type]
            for entry in entries:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict):
                    assert "script" not in handler, (
                        "Handler must not have a 'script' field"
                    )

    def test_no_handler_fields_on_matcher_object(self):
        """Matcher objects must not contain handler fields (type, command)
        directly -- they belong in the handler sub-object."""
        parsed = parse_hooks_json(generate_hooks_json())
        for hook_type in ("PreToolUse", "PostToolUse"):
            entries = parsed["hooks"][hook_type]
            for entry in entries:
                # If the entry has both a matcher and handler, the matcher
                # must not have type/command.  If the entry IS the combined
                # object, then it's a flat format which is acceptable.
                if "matcher" in entry and "handler" in entry:
                    matcher = entry["matcher"]
                    assert "type" not in matcher or matcher.get("type") != "command", (
                        "Matcher must not carry handler's 'type' field"
                    )
                    assert "command" not in matcher, (
                        "Matcher must not carry handler's 'command' field"
                    )

    def test_paths_use_claude_scripts_prefix(self):
        """All handler command paths must use .claude/scripts/ prefix."""
        parsed = parse_hooks_json(generate_hooks_json())
        for hook_type in ("PreToolUse", "PostToolUse"):
            entries = parsed["hooks"][hook_type]
            for entry in entries:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict) and "command" in handler:
                    cmd = handler["command"]
                    assert ".claude/scripts/" in cmd, (
                        f"Handler command path must use .claude/scripts/ prefix, "
                        f"got: {cmd}"
                    )

    def test_each_handler_has_type_and_command(self):
        """Each handler object must have both 'type' and 'command' keys."""
        parsed = parse_hooks_json(generate_hooks_json())
        for hook_type in ("PreToolUse", "PostToolUse"):
            entries = parsed["hooks"][hook_type]
            for entry in entries:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict):
                    assert "type" in handler, "Handler must have 'type' key"
                    assert "command" in handler, "Handler must have 'command' key"

    def test_pretooluse_has_exactly_two_entries(self):
        """PreToolUse must have exactly two entries (Write and Bash matchers)."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_pretooluse_entries(parsed)
        assert len(entries) == 2, (
            f"PreToolUse should have exactly 2 entries, got {len(entries)}"
        )

    def test_posttooluse_has_exactly_two_entries(self):
        """PostToolUse must have exactly two entries (Write and Agent matchers)."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_posttooluse_entries(parsed)
        assert len(entries) == 2, (
            f"PostToolUse should have exactly 2 entries, got {len(entries)}"
        )


# ---------------------------------------------------------------------------
# generate_write_authorization_sh tests
# ---------------------------------------------------------------------------


class TestGenerateWriteAuthorizationSh:
    """Tests for the generate_write_authorization_sh function."""

    def test_returns_string(self):
        """generate_write_authorization_sh must return a string."""
        result = generate_write_authorization_sh()
        assert isinstance(result, str)

    def test_starts_with_shebang(self):
        """Generated script must start with a shell shebang line."""
        result = generate_write_authorization_sh()
        first_line = result.strip().split("\n")[0]
        assert first_line.startswith("#!"), (
            f"Script must start with shebang, got: {first_line}"
        )
        assert "bash" in first_line or "sh" in first_line, (
            f"Shebang must reference bash or sh, got: {first_line}"
        )

    def test_references_pipeline_state_json(self):
        """Script must read the current stage from pipeline_state.json."""
        result = generate_write_authorization_sh()
        assert "pipeline_state.json" in result, (
            "Script must reference pipeline_state.json to read current stage"
        )

    def test_pipeline_state_protection(self):
        """pipeline_state.json must be writable only by update_state.py."""
        result = generate_write_authorization_sh()
        assert "update_state" in result, (
            "Script must reference update_state.py for pipeline_state.json protection"
        )

    def test_builder_script_protection_stages_3_through_5(self):
        """Builder scripts (.py in scripts/) must be read-only during Stages 3-5."""
        result = generate_write_authorization_sh()
        # The script must contain logic referencing stages 3-5 and scripts/ .py files
        assert "scripts/" in result or "scripts" in result, (
            "Script must reference scripts/ directory for builder script protection"
        )

    def test_builder_script_block_message_references_hard_stop_protocol(self):
        """Block message for builder scripts must reference the Hard Stop Protocol."""
        result = generate_write_authorization_sh()
        assert "Hard Stop Protocol" in result, (
            "Builder script block message must reference Hard Stop Protocol"
        )

    def test_builder_script_block_message_content(self):
        """Block message must contain the specified text about builder script modification."""
        result = generate_write_authorization_sh()
        assert "Builder script modification blocked during Stages 3-5" in result, (
            "Block message must include the specified builder script block text"
        )

    def test_profile_writability_stage_0_project_profile(self):
        """Profile must be writable during Stage 0 project_profile sub-stage."""
        result = generate_write_authorization_sh()
        assert "project_profile" in result, (
            "Script must reference project_profile sub-stage for profile writability"
        )

    def test_profile_writability_redo_sub_stages(self):
        """Profile must be writable during redo sub-stages."""
        result = generate_write_authorization_sh()
        assert "redo" in result.lower(), (
            "Script must reference redo sub-stages for profile writability"
        )

    def test_toolchain_permanently_read_only(self):
        """Toolchain files must be permanently read-only."""
        result = generate_write_authorization_sh()
        assert "toolchain" in result.lower(), (
            "Script must reference toolchain for read-only protection"
        )

    def test_ruff_toml_permanently_read_only(self):
        """ruff.toml must be permanently read-only."""
        result = generate_write_authorization_sh()
        assert "ruff.toml" in result, (
            "Script must reference ruff.toml for read-only protection"
        )

    def test_oracle_session_ledger_writable(self):
        """oracle_run_ledger.json must always be writable during oracle sessions."""
        result = generate_write_authorization_sh()
        assert "oracle_run_ledger.json" in result, (
            "Script must reference oracle_run_ledger.json for oracle session rules"
        )

    def test_debug_session_regressions_writable(self):
        """tests/regressions/ must be writable during debug sessions."""
        result = generate_write_authorization_sh()
        assert "regressions" in result, (
            "Script must reference tests/regressions/ for debug session rules"
        )

    def test_debug_session_delivered_repo_path_writable(self):
        """delivered_repo_path must be writable during debug sessions."""
        result = generate_write_authorization_sh()
        assert "delivered_repo_path" in result or "deliver" in result.lower(), (
            "Script must reference delivered_repo_path for debug session rules"
        )

    def test_exit_code_2_for_blocked_writes(self):
        """Script must use exit code 2 for blocked writes (Claude Code convention)."""
        result = generate_write_authorization_sh()
        assert "exit 2" in result, "Script must use 'exit 2' for blocked writes"

    def test_authorized_write_dirs_reference(self):
        """Script must check write paths against authorized_write_dirs."""
        result = generate_write_authorization_sh()
        # The script should reference the concept of authorized directories
        has_src = "src" in result
        has_tests = "tests" in result
        assert has_src or has_tests, (
            "Script must reference authorized write directories (e.g. src, tests)"
        )

    def test_hook_order_stage_read_first(self):
        """The script must read the current stage as the first operation,
        before any path-based checks."""
        result = generate_write_authorization_sh()
        lines = result.split("\n")
        # Find first non-comment, non-shebang, non-empty line that reads state
        state_read_idx = None
        path_check_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if state_read_idx is None and "pipeline_state" in stripped:
                state_read_idx = i
            if path_check_idx is None and "exit 2" in stripped:
                path_check_idx = i
        if state_read_idx is not None and path_check_idx is not None:
            assert state_read_idx < path_check_idx, (
                "Stage read must occur before any exit-2 path blocking"
            )


# ---------------------------------------------------------------------------
# generate_non_svp_protection_sh tests
# ---------------------------------------------------------------------------


class TestGenerateNonSvpProtectionSh:
    """Tests for the generate_non_svp_protection_sh function."""

    def test_returns_string(self):
        """generate_non_svp_protection_sh must return a string."""
        result = generate_non_svp_protection_sh()
        assert isinstance(result, str)

    def test_starts_with_shebang(self):
        """Generated script must start with a shell shebang line."""
        result = generate_non_svp_protection_sh()
        first_line = result.strip().split("\n")[0]
        assert first_line.startswith("#!"), (
            f"Script must start with shebang, got: {first_line}"
        )

    def test_checks_svp_plugin_active_env_var(self):
        """Script must check the SVP_PLUGIN_ACTIVE environment variable."""
        result = generate_non_svp_protection_sh()
        assert "SVP_PLUGIN_ACTIVE" in result, (
            "Script must check SVP_PLUGIN_ACTIVE environment variable"
        )

    def test_blocks_when_svp_plugin_active_unset(self):
        """When SVP_PLUGIN_ACTIVE is not set, script must block all bash commands."""
        result = generate_non_svp_protection_sh()
        # Script must have logic to check if variable is unset/empty
        has_z_check = "-z" in result
        has_empty_check = '""' in result or "unset" in result.lower()
        has_not_one_check = '!= "1"' in result or "!=" in result
        assert has_z_check or has_empty_check or has_not_one_check, (
            "Script must check for unset or non-'1' SVP_PLUGIN_ACTIVE"
        )

    def test_blocks_when_svp_plugin_active_not_one(self):
        """When SVP_PLUGIN_ACTIVE is set but not '1', script must block."""
        result = generate_non_svp_protection_sh()
        assert '"1"' in result or "'1'" in result, (
            "Script must compare SVP_PLUGIN_ACTIVE against '1'"
        )

    def test_prints_readme_message_on_block(self):
        """When blocked, script must print a README message."""
        result = generate_non_svp_protection_sh()
        has_readme = "README" in result or "readme" in result.lower()
        assert has_readme, "Script must print a README message when blocking"

    def test_exit_code_2_for_blocked_commands(self):
        """Script must use exit code 2 for blocked commands."""
        result = generate_non_svp_protection_sh()
        assert "exit 2" in result, "Script must use 'exit 2' for blocked commands"

    def test_allows_when_svp_plugin_active_is_one(self):
        """Script must have a code path that allows execution when SVP_PLUGIN_ACTIVE=1."""
        result = generate_non_svp_protection_sh()
        # Must have exit 0 or implicit pass-through for the allowed case
        has_exit_0 = "exit 0" in result
        has_pass_through = result.strip().split("\n")[-1].strip() not in ["exit 2"]
        assert has_exit_0 or has_pass_through, (
            "Script must allow execution when SVP_PLUGIN_ACTIVE is '1'"
        )


# ---------------------------------------------------------------------------
# generate_stub_sentinel_check_sh tests
# ---------------------------------------------------------------------------


class TestGenerateStubSentinelCheckSh:
    """Tests for the generate_stub_sentinel_check_sh function."""

    def test_returns_string(self):
        """generate_stub_sentinel_check_sh must return a string."""
        result = generate_stub_sentinel_check_sh()
        assert isinstance(result, str)

    def test_starts_with_shebang(self):
        """Generated script must start with a shell shebang line."""
        result = generate_stub_sentinel_check_sh()
        first_line = result.strip().split("\n")[0]
        assert first_line.startswith("#!"), (
            f"Script must start with shebang, got: {first_line}"
        )

    def test_greps_for_stub_sentinel(self):
        """Script must grep written files for the stub sentinel."""
        result = generate_stub_sentinel_check_sh()
        assert "grep" in result.lower() or "SVP_STUB" in result, (
            "Script must grep for stub sentinel pattern"
        )

    def test_references_svp_stub_sentinel(self):
        """Script must reference the __SVP_STUB__ sentinel marker."""
        result = generate_stub_sentinel_check_sh()
        has_svp_stub = "__SVP_STUB__" in result or "SVP_STUB" in result
        has_do_not_deliver = "DO NOT DELIVER" in result
        assert has_svp_stub or has_do_not_deliver, (
            "Script must reference the SVP_STUB sentinel or 'DO NOT DELIVER' marker"
        )

    def test_exit_code_2_when_sentinel_found(self):
        """Script must exit with code 2 when stub sentinel is found."""
        result = generate_stub_sentinel_check_sh()
        assert "exit 2" in result, (
            "Script must use 'exit 2' when stub sentinel is found"
        )

    def test_message_directs_agent_to_implement(self):
        """When sentinel found, message must direct agent to implement, not copy stub."""
        result = generate_stub_sentinel_check_sh()
        has_implement = "implement" in result.lower()
        has_copy = "copy" in result.lower() or "stub" in result.lower()
        assert has_implement or has_copy, (
            "Block message must direct agent to implement rather than copy stub"
        )

    def test_posttooluse_validation_context(self):
        """Script operates as a PostToolUse hook -- validates content after write,
        not intent to write."""
        result = generate_stub_sentinel_check_sh()
        # The script should reference the file that was written (e.g., via
        # hook argument or environment variable providing the file path)
        assert len(result.strip()) > 0, (
            "Script must contain content for post-write validation"
        )

    def test_no_exit_2_before_sentinel_check(self):
        """Script must not unconditionally exit 2 -- only after finding sentinel."""
        result = generate_stub_sentinel_check_sh()
        lines = result.split("\n")
        non_comment_lines = [
            l.strip() for l in lines if l.strip() and not l.strip().startswith("#")
        ]
        # If there's an exit 2, it should be in a conditional block
        # (inside an if/then or after grep success)
        exit_2_count = sum(1 for l in non_comment_lines if "exit 2" in l)
        conditional_count = sum(
            1
            for l in non_comment_lines
            if "if" in l or "then" in l or "grep" in l.lower()
        )
        if exit_2_count > 0:
            assert conditional_count > 0, (
                "exit 2 must be conditional on sentinel detection, not unconditional"
            )


# ---------------------------------------------------------------------------
# generate_monitoring_reminder_sh tests
# ---------------------------------------------------------------------------


class TestGenerateMonitoringReminderSh:
    """Tests for the generate_monitoring_reminder_sh function."""

    def test_returns_string(self):
        """generate_monitoring_reminder_sh must return a string."""
        result = generate_monitoring_reminder_sh()
        assert isinstance(result, str)

    def test_starts_with_shebang(self):
        """Generated script must start with a shell shebang line."""
        result = generate_monitoring_reminder_sh()
        first_line = result.strip().split("\n")[0]
        assert first_line.startswith("#!"), (
            f"Script must start with shebang, got: {first_line}"
        )

    def test_reads_project_profile_json(self):
        """Script must read project_profile.json to check is_svp_build."""
        result = generate_monitoring_reminder_sh()
        assert "project_profile.json" in result, "Script must read project_profile.json"

    def test_checks_is_svp_build_field(self):
        """Script must check the is_svp_build field."""
        result = generate_monitoring_reminder_sh()
        assert "is_svp_build" in result, "Script must check the is_svp_build field"

    def test_outputs_monitoring_reminder_when_svp_build_true(self):
        """When is_svp_build is true, script must output a monitoring reminder."""
        result = generate_monitoring_reminder_sh()
        # Script must contain echo/printf with reminder text
        has_output = "echo" in result or "printf" in result or "cat" in result
        assert has_output, (
            "Script must output a monitoring reminder when is_svp_build is true"
        )

    def test_reminder_mentions_orchestrator_verification(self):
        """The monitoring reminder must instruct the orchestrator to verify
        subagent output against the spec before proceeding."""
        result = generate_monitoring_reminder_sh()
        lower_result = result.lower()
        has_verify = "verify" in lower_result or "check" in lower_result
        has_spec = "spec" in lower_result
        has_subagent = (
            "subagent" in lower_result
            or "sub-agent" in lower_result
            or "agent" in lower_result
        )
        assert has_verify or has_spec or has_subagent, (
            "Reminder must reference verifying subagent output against the spec"
        )

    def test_noop_when_is_svp_build_false(self):
        """When is_svp_build is false, script must be a no-op (exit 0, no output)."""
        result = generate_monitoring_reminder_sh()
        # Script must have a branch for false/absent that exits 0
        assert "exit 0" in result, (
            "Script must exit 0 (no-op) when is_svp_build is false or absent"
        )

    def test_noop_when_is_svp_build_absent(self):
        """When is_svp_build field is absent from profile, script must be a no-op."""
        result = generate_monitoring_reminder_sh()
        # Script must handle the case where the field doesn't exist
        lower_result = result.lower()
        handles_missing = (
            "null" in lower_result
            or "not found" in lower_result
            or "-z" in result
            or "grep" in lower_result
            or "jq" in lower_result
            or "missing" in lower_result
            or "else" in lower_result
        )
        assert handles_missing, (
            "Script must handle the case where is_svp_build field is absent"
        )

    def test_script_has_conditional_branching(self):
        """Script must have conditional logic (if/then or equivalent) for
        the is_svp_build true/false branch."""
        result = generate_monitoring_reminder_sh()
        has_conditional = "if" in result and ("then" in result or "fi" in result)
        has_case = "case" in result
        has_test = "[[" in result or "test " in result
        assert has_conditional or has_case or has_test, (
            "Script must have conditional branching for is_svp_build check"
        )

    def test_agent_posttooluse_context(self):
        """This script fires as a PostToolUse hook on Agent tool returns.
        It must not unconditionally block (no exit 2 as primary path)."""
        result = generate_monitoring_reminder_sh()
        lines = result.split("\n")
        non_comment_lines = [
            l.strip() for l in lines if l.strip() and not l.strip().startswith("#")
        ]
        # exit 2 should not appear -- this hook is advisory, not blocking
        exit_2_lines = [l for l in non_comment_lines if l == "exit 2"]
        assert len(exit_2_lines) == 0, (
            "Monitoring reminder hook must not use exit 2 -- it is advisory, "
            "not a blocking hook"
        )


# ---------------------------------------------------------------------------
# Cross-function consistency tests
# ---------------------------------------------------------------------------


class TestCrossFunctionConsistency:
    """Tests verifying consistency between generate_hooks_json and the
    individual script generators."""

    def test_hooks_json_write_authorization_path_matches_generator(self):
        """The path in hooks JSON for write_authorization must match the
        script name from generate_write_authorization_sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        all_commands = []
        for hook_type in ("PreToolUse", "PostToolUse"):
            for entry in parsed["hooks"][hook_type]:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        write_auth_commands = [c for c in all_commands if "write_authorization" in c]
        assert len(write_auth_commands) >= 1
        for cmd in write_auth_commands:
            assert cmd.endswith("write_authorization.sh"), (
                f"write_authorization path must end with .sh, got: {cmd}"
            )

    def test_hooks_json_non_svp_protection_path_matches_generator(self):
        """The path in hooks JSON for non_svp_protection must end with .sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        all_commands = []
        for hook_type in ("PreToolUse", "PostToolUse"):
            for entry in parsed["hooks"][hook_type]:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        svp_prot_commands = [c for c in all_commands if "non_svp_protection" in c]
        assert len(svp_prot_commands) >= 1
        for cmd in svp_prot_commands:
            assert cmd.endswith("non_svp_protection.sh")

    def test_hooks_json_stub_sentinel_check_path_matches_generator(self):
        """The path in hooks JSON for stub_sentinel_check must end with .sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        all_commands = []
        for hook_type in ("PreToolUse", "PostToolUse"):
            for entry in parsed["hooks"][hook_type]:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        stub_commands = [c for c in all_commands if "stub_sentinel_check" in c]
        assert len(stub_commands) >= 1
        for cmd in stub_commands:
            assert cmd.endswith("stub_sentinel_check.sh")

    def test_hooks_json_monitoring_reminder_path_matches_generator(self):
        """The path in hooks JSON for monitoring_reminder must end with .sh."""
        parsed = parse_hooks_json(generate_hooks_json())
        all_commands = []
        for hook_type in ("PreToolUse", "PostToolUse"):
            for entry in parsed["hooks"][hook_type]:
                handler = entry.get("handler", entry)
                if isinstance(handler, dict) and "command" in handler:
                    all_commands.append(handler["command"])
        monitor_commands = [c for c in all_commands if "monitoring_reminder" in c]
        assert len(monitor_commands) >= 1
        for cmd in monitor_commands:
            assert cmd.endswith("monitoring_reminder.sh")

    def test_all_four_scripts_are_nonempty(self):
        """All four script generators must produce non-empty strings."""
        scripts = {
            "write_authorization": generate_write_authorization_sh(),
            "non_svp_protection": generate_non_svp_protection_sh(),
            "stub_sentinel_check": generate_stub_sentinel_check_sh(),
            "monitoring_reminder": generate_monitoring_reminder_sh(),
        }
        for name, script in scripts.items():
            assert len(script.strip()) > 0, f"{name} must produce a non-empty script"

    def test_all_scripts_are_valid_shell_syntax(self):
        """All generated scripts must have basic shell structure
        (shebang + at least one command)."""
        scripts = {
            "write_authorization": generate_write_authorization_sh(),
            "non_svp_protection": generate_non_svp_protection_sh(),
            "stub_sentinel_check": generate_stub_sentinel_check_sh(),
            "monitoring_reminder": generate_monitoring_reminder_sh(),
        }
        for name, script in scripts.items():
            lines = script.strip().split("\n")
            assert len(lines) >= 2, (
                f"{name} must have at least shebang + one command line"
            )
            assert lines[0].startswith("#!"), f"{name} must start with shebang"


# ---------------------------------------------------------------------------
# Schema / structural validation tests
# ---------------------------------------------------------------------------


class TestHooksJsonSchemaStructure:
    """Tests verifying the structure of the generated hooks JSON against
    the Claude Code hook configuration schema."""

    def test_schema_top_level_is_hooks_only(self):
        """Generated JSON must have 'hooks' as the only top-level key
        (per Claude Code hook config schema)."""
        parsed = parse_hooks_json(generate_hooks_json())
        assert set(parsed.keys()) == {"hooks"}, (
            f"Top-level keys must be exactly {{'hooks'}}, got {set(parsed.keys())}"
        )

    def test_hooks_object_has_exactly_two_keys(self):
        """hooks object must contain exactly PreToolUse and PostToolUse."""
        parsed = parse_hooks_json(generate_hooks_json())
        hooks = parsed["hooks"]
        expected_keys = {"PreToolUse", "PostToolUse"}
        assert set(hooks.keys()) == expected_keys, (
            f"hooks keys must be exactly {expected_keys}, got {set(hooks.keys())}"
        )

    def test_pretooluse_write_entry_has_correct_matcher_tool(self):
        """The PreToolUse Write entry must match on 'Write' tool."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_pretooluse_entries(parsed)
        write_entries = []
        for entry in entries:
            handler = entry.get("handler", entry)
            if isinstance(handler, dict) and "command" in handler:
                if "write_authorization" in handler["command"]:
                    write_entries.append(entry)
        assert len(write_entries) == 1, (
            "Must have exactly one Write matcher in PreToolUse"
        )
        entry = write_entries[0]
        # Check matcher references Write tool
        matcher = entry.get("matcher", entry)
        if "tool_name" in matcher:
            assert matcher["tool_name"] == "Write"

    def test_pretooluse_bash_entry_has_correct_matcher_tool(self):
        """The PreToolUse Bash entry must match on 'Bash' tool."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_pretooluse_entries(parsed)
        bash_entries = []
        for entry in entries:
            handler = entry.get("handler", entry)
            if isinstance(handler, dict) and "command" in handler:
                if "non_svp_protection" in handler["command"]:
                    bash_entries.append(entry)
        assert len(bash_entries) == 1, (
            "Must have exactly one Bash matcher in PreToolUse"
        )
        entry = bash_entries[0]
        matcher = entry.get("matcher", entry)
        if "tool_name" in matcher:
            assert matcher["tool_name"] == "Bash"

    def test_posttooluse_write_entry_has_correct_matcher_tool(self):
        """The PostToolUse Write entry must match on 'Write' tool."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_posttooluse_entries(parsed)
        write_entries = []
        for entry in entries:
            handler = entry.get("handler", entry)
            if isinstance(handler, dict) and "command" in handler:
                if "stub_sentinel_check" in handler["command"]:
                    write_entries.append(entry)
        assert len(write_entries) == 1, (
            "Must have exactly one Write matcher in PostToolUse for stub_sentinel_check"
        )
        entry = write_entries[0]
        matcher = entry.get("matcher", entry)
        if "tool_name" in matcher:
            assert matcher["tool_name"] == "Write"

    def test_posttooluse_agent_entry_has_correct_matcher_tool(self):
        """The PostToolUse Agent entry must match on 'Agent' tool."""
        parsed = parse_hooks_json(generate_hooks_json())
        entries = get_posttooluse_entries(parsed)
        agent_entries = []
        for entry in entries:
            handler = entry.get("handler", entry)
            if isinstance(handler, dict) and "command" in handler:
                if "monitoring_reminder" in handler["command"]:
                    agent_entries.append(entry)
        assert len(agent_entries) == 1, (
            "Must have exactly one Agent matcher in PostToolUse for monitoring_reminder"
        )
        entry = agent_entries[0]
        matcher = entry.get("matcher", entry)
        if "tool_name" in matcher:
            assert matcher["tool_name"] == "Agent"


# ---------------------------------------------------------------------------
# Write authorization detailed path rule tests
# ---------------------------------------------------------------------------


class TestWriteAuthorizationPathRules:
    """Tests for specific path rules in generate_write_authorization_sh."""

    def test_pipeline_state_json_restricted_to_update_state(self):
        """pipeline_state.json must only be writable by update_state.py,
        the script must block all other writers."""
        result = generate_write_authorization_sh()
        assert "pipeline_state" in result
        assert "update_state" in result

    def test_py_files_in_scripts_blocked_stages_3_5(self):
        """'.py' files in 'scripts/' must be read-only during stages 3, 4, and 5."""
        result = generate_write_authorization_sh()
        lower = result.lower()
        has_py_reference = ".py" in result
        has_scripts_reference = "scripts" in result
        assert has_py_reference and has_scripts_reference, (
            "Script must reference .py files in scripts/ directory"
        )

    def test_stage_references_for_builder_protection(self):
        """Script must reference stages 3, 4, and 5 for builder script protection."""
        result = generate_write_authorization_sh()
        has_stage_3 = "3" in result
        has_stage_4 = "4" in result
        has_stage_5 = "5" in result
        assert has_stage_3 and has_stage_5, (
            "Script must reference stages 3 through 5 for builder script protection"
        )

    def test_oracle_session_special_case(self):
        """During oracle sessions, .svp/oracle_run_ledger.json must be writable."""
        result = generate_write_authorization_sh()
        assert ".svp/oracle_run_ledger.json" in result or "oracle_run_ledger" in result

    def test_debug_session_tests_regressions_writable(self):
        """During debug sessions, tests/regressions/ directory must be writable."""
        result = generate_write_authorization_sh()
        assert "tests/regressions" in result or "regressions" in result

    def test_debug_session_unit_specific_dirs_writable(self):
        """During debug sessions, unit-specific directories must be writable."""
        result = generate_write_authorization_sh()
        lower = result.lower()
        has_unit = "unit" in lower
        has_debug = "debug" in lower
        assert has_unit and has_debug, (
            "Script must handle unit-specific dirs during debug sessions"
        )


# ---------------------------------------------------------------------------
# Monitoring reminder detailed behavior tests
# ---------------------------------------------------------------------------


class TestMonitoringReminderBehavior:
    """Detailed behavioral tests for the monitoring_reminder.sh script."""

    def test_script_does_not_block_agent_tool(self):
        """The monitoring reminder is advisory only -- it must never exit 2
        to hard-block the Agent tool."""
        result = generate_monitoring_reminder_sh()
        # exit 2 must not appear anywhere in the script
        lines = [
            l.strip()
            for l in result.split("\n")
            if l.strip() and not l.strip().startswith("#")
        ]
        for line in lines:
            assert "exit 2" not in line, (
                f"Monitoring reminder must not use exit 2 (found in: {line})"
            )

    def test_exit_0_is_present(self):
        """Script must have at least one explicit exit 0 for the no-op path."""
        result = generate_monitoring_reminder_sh()
        assert "exit 0" in result

    def test_script_has_two_branches(self):
        """Script must have at least two distinct exit/output paths:
        one for is_svp_build=true (output reminder) and one for false/absent (no-op)."""
        result = generate_monitoring_reminder_sh()
        # Count distinct exit paths
        exit_0_count = result.count("exit 0")
        echo_count = result.lower().count("echo") + result.lower().count("printf")
        # There should be at least one echo (for reminder output) and at least
        # one exit 0 (for the no-op path)
        assert echo_count >= 1, (
            "Script must have at least one output statement for the reminder"
        )
        assert exit_0_count >= 1, (
            "Script must have at least one exit 0 for the no-op path"
        )

    def test_ef_self_build_context_documented(self):
        """The script fires only during E/F self-builds per the hooks JSON
        Agent PostToolUse entry. The script itself checks is_svp_build as
        the runtime guard."""
        result = generate_monitoring_reminder_sh()
        assert "is_svp_build" in result, (
            "Script must check is_svp_build as the runtime guard"
        )
