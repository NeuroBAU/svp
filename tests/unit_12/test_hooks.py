"""
Tests for Unit 12: Hook Configurations.

Verifies JSON hook schema, shell script string constants,
and Python hook-logic functions. The stub exposes:
- HOOKS_JSON_SCHEMA (dict)
- HOOKS_JSON_CONTENT (str)
- WRITE_AUTHORIZATION_SH_CONTENT (str)
- NON_SVP_PROTECTION_SH_CONTENT (str)
- STUB_SENTINEL_CHECK_SH_CONTENT (str)
- SVP_ENV_VAR (str)
- check_write_authorization(tool, path, state_path)
- check_svp_session(env_var_name)
- check_stub_sentinel(file_path)
"""

import json

from src.unit_12.stub import (
    HOOKS_JSON_CONTENT,
    HOOKS_JSON_SCHEMA,
    NON_SVP_PROTECTION_SH_CONTENT,
    STUB_SENTINEL_CHECK_SH_CONTENT,
    SVP_ENV_VAR,
    WRITE_AUTHORIZATION_SH_CONTENT,
    check_stub_sentinel,
    check_svp_session,
    check_write_authorization,
)

# -------------------------------------------------------
# SVP_ENV_VAR constant
# -------------------------------------------------------


class TestSvpEnvVar:
    """SVP_PLUGIN_ACTIVE is the canonical env var name."""

    def test_env_var_value(self):
        assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"


# -------------------------------------------------------
# HOOKS_JSON_SCHEMA structure
# -------------------------------------------------------


class TestHooksJsonSchema:
    """Schema dict has top-level 'hooks' key."""

    def test_top_level_hooks_key(self):
        assert "hooks" in HOOKS_JSON_SCHEMA

    def test_pre_tool_use_exists(self):
        hooks = HOOKS_JSON_SCHEMA["hooks"]
        assert "PreToolUse" in hooks

    def test_post_tool_use_exists(self):
        hooks = HOOKS_JSON_SCHEMA["hooks"]
        assert "PostToolUse" in hooks

    def test_write_matcher_in_pre(self):
        pre = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
        matchers = [h["matcher"] for h in pre]
        assert "Write" in matchers

    def test_bash_matcher_in_pre(self):
        pre = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
        matchers = [h["matcher"] for h in pre]
        assert "Bash" in matchers

    def test_write_matcher_in_post(self):
        post = HOOKS_JSON_SCHEMA["hooks"]["PostToolUse"]
        matchers = [h["matcher"] for h in post]
        assert "Write" in matchers

    def test_hook_command_paths_use_claude_scripts(self):
        pre = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
        for entry in pre:
            for h in entry["hooks"]:
                cmd = h["command"]
                assert cmd.startswith(".claude/scripts/")


# -------------------------------------------------------
# HOOKS_JSON_CONTENT string
# -------------------------------------------------------


class TestHooksJsonContent:
    """HOOKS_JSON_CONTENT is valid JSON matching schema."""

    def test_is_nonempty_string(self):
        assert isinstance(HOOKS_JSON_CONTENT, str)
        assert len(HOOKS_JSON_CONTENT) > 0

    def test_valid_json(self):
        data = json.loads(HOOKS_JSON_CONTENT)
        assert isinstance(data, dict)

    def test_has_top_level_hooks_key(self):
        data = json.loads(HOOKS_JSON_CONTENT)
        assert "hooks" in data

    def test_pre_tool_use_present(self):
        data = json.loads(HOOKS_JSON_CONTENT)
        assert "PreToolUse" in data["hooks"]

    def test_post_tool_use_present(self):
        data = json.loads(HOOKS_JSON_CONTENT)
        assert "PostToolUse" in data["hooks"]

    def test_write_authorization_hook(self):
        data = json.loads(HOOKS_JSON_CONTENT)
        pre = data["hooks"]["PreToolUse"]
        write_hooks = [h for h in pre if h["matcher"] == "Write"]
        assert len(write_hooks) >= 1
        cmds = []
        for wh in write_hooks:
            for h in wh["hooks"]:
                cmds.append(h["command"])
        assert any("write_authorization" in c for c in cmds)

    def test_stub_sentinel_post_hook(self):
        data = json.loads(HOOKS_JSON_CONTENT)
        post = data["hooks"]["PostToolUse"]
        write_posts = [h for h in post if h["matcher"] == "Write"]
        assert len(write_posts) >= 1
        cmds = []
        for wp in write_posts:
            for h in wp["hooks"]:
                cmds.append(h["command"])
        assert any("stub_sentinel_check" in c for c in cmds)


# -------------------------------------------------------
# WRITE_AUTHORIZATION_SH_CONTENT
# -------------------------------------------------------


class TestWriteAuthorizationSh:
    """Shell script content for write authorization."""

    def test_is_nonempty_string(self):
        assert isinstance(WRITE_AUTHORIZATION_SH_CONTENT, str)
        assert len(WRITE_AUTHORIZATION_SH_CONTENT) > 0

    def test_starts_with_shebang(self):
        assert WRITE_AUTHORIZATION_SH_CONTENT.startswith("#!/")

    def test_mentions_pipeline_state(self):
        assert "pipeline_state" in WRITE_AUTHORIZATION_SH_CONTENT

    def test_mentions_toolchain_readonly(self):
        content = WRITE_AUTHORIZATION_SH_CONTENT
        assert "toolchain" in content.lower()

    def test_mentions_ruff_toml_readonly(self):
        content = WRITE_AUTHORIZATION_SH_CONTENT
        assert "ruff.toml" in content or "ruff" in content


# -------------------------------------------------------
# NON_SVP_PROTECTION_SH_CONTENT
# -------------------------------------------------------


class TestNonSvpProtectionSh:
    """Shell script for non-SVP session protection."""

    def test_is_nonempty_string(self):
        assert isinstance(NON_SVP_PROTECTION_SH_CONTENT, str)
        assert len(NON_SVP_PROTECTION_SH_CONTENT) > 0

    def test_starts_with_shebang(self):
        assert NON_SVP_PROTECTION_SH_CONTENT.startswith("#!/")

    def test_references_svp_env_var(self):
        assert "SVP_PLUGIN_ACTIVE" in NON_SVP_PROTECTION_SH_CONTENT


# -------------------------------------------------------
# STUB_SENTINEL_CHECK_SH_CONTENT
# -------------------------------------------------------


class TestStubSentinelCheckSh:
    """PostToolUse handler for stub sentinel detection."""

    def test_is_nonempty_string(self):
        assert isinstance(STUB_SENTINEL_CHECK_SH_CONTENT, str)
        assert len(STUB_SENTINEL_CHECK_SH_CONTENT) > 0

    def test_starts_with_shebang(self):
        assert STUB_SENTINEL_CHECK_SH_CONTENT.startswith("#!/")

    def test_checks_svp_stub(self):
        assert "__SVP_STUB__" in STUB_SENTINEL_CHECK_SH_CONTENT

    def test_checks_src_unit_path(self):
        content = STUB_SENTINEL_CHECK_SH_CONTENT
        assert "src/unit_" in content or "src" in content

    def test_exit_code_2_on_match(self):
        content = STUB_SENTINEL_CHECK_SH_CONTENT
        assert "exit 2" in content


# -------------------------------------------------------
# check_write_authorization function
# -------------------------------------------------------


class TestCheckWriteAuthorization:
    """Python logic for write authorization."""

    def test_callable(self):
        assert callable(check_write_authorization)

    def test_returns_int(self, tmp_path):
        state_file = tmp_path / "pipeline_state.json"
        state_file.write_text("{}")
        result = check_write_authorization(
            "Write",
            str(tmp_path / "scripts" / "foo.py"),
            str(state_file),
        )
        assert isinstance(result, int)


# -------------------------------------------------------
# check_svp_session function
# -------------------------------------------------------


class TestCheckSvpSession:
    """Python logic for SVP session check."""

    def test_callable(self):
        assert callable(check_svp_session)

    def test_returns_int(self):
        result = check_svp_session("SVP_PLUGIN_ACTIVE")
        assert isinstance(result, int)


# -------------------------------------------------------
# check_stub_sentinel function
# -------------------------------------------------------


class TestCheckStubSentinel:
    """Python logic for stub sentinel check."""

    def test_callable(self):
        assert callable(check_stub_sentinel)

    def test_returns_int(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        result = check_stub_sentinel(str(f))
        assert isinstance(result, int)

    def test_returns_nonzero_for_stub(self, tmp_path):
        f = tmp_path / "stub.py"
        f.write_text("__SVP_STUB__ = True\n")
        result = check_stub_sentinel(str(f))
        assert result != 0

    def test_returns_zero_for_clean(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n")
        result = check_stub_sentinel(str(f))
        assert result == 0
